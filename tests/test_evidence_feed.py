"""The evidence feed (PROPOSED 2026-10-21): judge/feed/.

What these hold, in the order a reader would worry about them:

    THE FEED IS THE COUNT'S POPULATION. A reader arrives from a number; the
    list must be exactly the reports that number counted, or it is not
    evidence for it. Asserted against `board_sections` itself, not against a
    copy of its rules.

    NO QUOTE LEAVES. Our paraphrase, tags, dates and sources - never the words
    of a report, from any source.

    THE CHECKS DECIDE, THE MODEL PROPOSES. A paraphrase that copies the
    source or adds a number is refused, asked again once, and if refused again
    the report stays in the feed without text - never dropped (rule 4).

    A SUMMARY IS SEEN ONLY ONCE A PERSON APPROVED IT.

Requires a database for the middle sections. See docs/dev-database.md.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime

import psycopg
import pytest

from judge import publication
from judge.feed import checks, items, paraphrase, summary

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contract" / "tables.sql"

P_SETTINGS = {
    "model": "deepseek/deepseek-v4-flash",
    "reasoning_effort": "none",
    "prompt_version": "p1",
    "per_call": 20,
    "max_chars": 320,
    "max_copied_words": 6,
    "attempts": 2,
    "many_excerpts": 6,
    "max_chars_many_excerpts": 480,
}
S_SETTINGS = {
    "model": "deepseek/deepseek-v4-flash",
    "reasoning_effort": "none",
    "prompt_version": "s1",
    "max_reports": 400,
    "min_reports": 2,
    "max_words": 450,
    "max_paragraphs": 7,
    "max_copied_words": 8,
    "attempts": 2,
    "quantity_words": ["most", "many", "few", "everyone"],
}

QUOTES = {
    "d1": "It handled every tool call in my agent loop without a single failure over two days.",
    "d2": "Tool calls kept coming back with malformed JSON arguments on version 4.1.",
    "d3": "Great at picking tools, but it looped forever when a tool returned an error.",
    "d4": "Its reasoning on the 97.1% benchmark claim seemed fine to me, nothing special.",
    "d5": "Declined row that must never reach the feed.",
    "d6": "The paper measures tool-use accuracy at 82.5 on our suite.",
}


# ── checks, no database ───────────────────────────────────────────────────


class TestParaphraseChecks:
    excerpts = [QUOTES["d2"]]

    def _problem(self, text):
        return checks.paraphrase_problem(
            text, self.excerpts, "Acme A 4.1", max_chars=320, max_copied_words=6
        )

    def test_own_words_with_the_same_numbers_pass(self):
        assert self._problem("Reports that tool arguments came back as broken JSON on 4.1.") is None

    def test_copying_a_long_run_is_a_quote_in_disguise(self):
        problem = self._problem(
            "The author says tool calls kept coming back with malformed JSON arguments."
        )
        assert problem and "consecutive words" in problem

    def test_a_number_not_in_the_excerpts_is_refused(self):
        problem = self._problem("Reports broken JSON in 40% of tool calls.")
        assert problem and "40" in problem

    def test_the_models_own_version_may_be_named(self):
        excerpts = ["Tool calls kept failing for me."]
        assert (
            checks.paraphrase_problem(
                "Acme A 4.1 kept failing tool calls, the author says.",
                excerpts,
                "Acme A 4.1",
                max_chars=320,
                max_copied_words=6,
            )
            is None
        )

    @pytest.mark.parametrize(
        "text",
        [
            "Posted on r/LocalLLaMA: tool calls broke.",
            "u/someone reports broken tool calls.",
            "See https://example.com for the broken calls.",
            "A Reddit user reports broken tool calls.",
            "In a tweet, the author reports broken tool calls.",
        ],
    )
    def test_no_link_handle_or_embed_only_platform(self, text):
        assert self._problem(text) is not None

    def test_a_platform_that_is_the_subject_is_allowed(self):
        excerpts = ["Using it inside GitHub Actions it failed every build step."]
        assert (
            checks.paraphrase_problem(
                "Inside GitHub Actions it reportedly broke each build.",
                excerpts,
                "Acme A",
                max_chars=320,
                max_copied_words=6,
            )
            is None
        )

    def test_empty_and_overlong_are_refused(self):
        assert self._problem("  ") == "empty"
        assert "longer than" in self._problem("word " * 100)


class TestSummaryChecks:
    sources = {"R1": ["Says tool arguments broke on 4.1."], "R2": ["Found tool picking strong."]}
    excerpts = {"R1": [QUOTES["d2"]], "R2": [QUOTES["d3"]]}

    def _check(self, paragraphs):
        return checks.summary_problems(
            paragraphs,
            self.sources,
            "Acme A",
            excerpts=self.excerpts,
            max_words=450,
            max_paragraphs=7,
            max_copied_words=6,
            quantity_words=["most", "many"],
        )

    def test_a_cited_page_passes(self):
        reason, flags = self._check(
            [
                {
                    "text": "Tool selection is described as strong, while arguments broke on 4.1.",
                    "cites": ["R1", "R2"],
                }
            ]
        )
        assert reason is None and flags == []

    def test_every_paragraph_must_cite(self):
        reason, _ = self._check([{"text": "Tool use is mixed.", "cites": []}])
        assert reason == "paragraph 1 cites no report"

    def test_only_reports_it_was_given(self):
        reason, _ = self._check([{"text": "Tool use is mixed.", "cites": ["R9"]}])
        assert "not given" in reason

    def test_a_count_is_refused_because_no_citation_carries_it(self):
        reason, _ = self._check(
            [{"text": "Three engineers, 3 in all, found it mixed.", "cites": ["R2"]}]
        )
        assert reason and "3" in reason

    def test_a_number_must_be_in_what_the_paragraph_cites(self):
        reason, _ = self._check([{"text": "Arguments broke on 4.1.", "cites": ["R2"]}])
        assert reason and "4.1" in reason

    def test_quantity_words_are_flagged_not_refused(self):
        reason, flags = self._check([{"text": "Most found tool picking strong.", "cites": ["R2"]}])
        assert reason is None
        assert flags and flags[0]["check"] == "quantity word"


# ── the database ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _public_view(monkeypatch):
    publication.withheld_sources.cache_clear()
    publication.evidence_feed_terms.cache_clear()
    monkeypatch.delenv("PUBLICATION_VIEW", raising=False)
    yield
    publication.withheld_sources.cache_clear()
    publication.evidence_feed_terms.cache_clear()


ROWS = [
    # doc, source, author, posted, section, slug, polarity, ruling
    (
        "d1",
        "devto",
        "au1",
        datetime(2026, 10, 20, tzinfo=UTC),
        "capability",
        "tool-use",
        "positive",
        None,
    ),
    (
        "d1",
        "devto",
        "au1",
        datetime(2026, 10, 20, tzinfo=UTC),
        "best_for",
        "coding-agent",
        "positive",
        None,
    ),
    (
        "d2",
        "reddit",
        "au2",
        datetime(2026, 10, 19, tzinfo=UTC),
        "capability",
        "tool-use",
        "negative",
        None,
    ),
    (
        "d3",
        "hackernews",
        "au3",
        datetime(2026, 10, 18, tzinfo=UTC),
        "capability",
        "tool-use",
        "positive",
        None,
    ),
    (
        "d3",
        "hackernews",
        "au3",
        datetime(2026, 10, 18, tzinfo=UTC),
        "capability",
        "tool_use",
        "negative",
        None,
    ),
    ("d4", "devto", "au1", None, "capability", "reasoning", "neutral", None),
    (
        "d5",
        "x",
        "au4",
        datetime(2026, 10, 21, tzinfo=UTC),
        "capability",
        "tool-use",
        "negative",
        "declined",
    ),
    (
        "d6",
        "arxiv",
        None,
        datetime(2026, 10, 1, tzinfo=UTC),
        "capability",
        "tool-use",
        "neutral",
        None,
    ),
]


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.execute(SCHEMA.read_text(encoding="utf-8"))
        c.execute(
            "INSERT INTO model_version "
            "(id, canonical_id, provider, display_name, sources, provenance) "
            "VALUES ('mv_a', 'acme/text-a', 'acme', 'Acme A 4.1', '{}', 'polled')"
        )
        for author, source in (
            ("au1", "devto"),
            ("au2", "reddit"),
            ("au3", "hackernews"),
            ("au4", "x"),
        ):
            c.execute(
                "INSERT INTO author (id, source, external_id) VALUES (%s, %s, %s)",
                (author, source, author),
            )
        seen = set()
        for i, (doc, source, author, posted, section, slug, pol, ruling) in enumerate(ROWS):
            if doc not in seen:
                seen.add(doc)
                url = (
                    "https://www.reddit.com/r/test/comments/abc/t/"
                    if source == "reddit"
                    else f"https://example.test/{doc}"
                )
                c.execute(
                    "INSERT INTO document (id, source, external_id, url, text_ref, content_hash, "
                    "status, author_id, created_at) VALUES (%s,%s,%s,%s,%s,%s,'kept',%s,%s)",
                    (doc, source, doc, url, f"r{doc}", f"h{doc}", author, posted),
                )
            mv = "mv_a"
            c.execute(
                "INSERT INTO board_entry (id, section, slug, name, definition, model_version_id, "
                "document_id, quote, quote_verified, polarity, proposer_model, pipeline_version, "
                "ruling, "
                "reviewed_at) VALUES (%s,%s,%s,%s,'Def.',%s,%s,%s,true,%s,'m','v1',%s,"
                "CASE WHEN %s::text IS NULL THEN NULL ELSE now() END)",
                (
                    f"be{i}",
                    section,
                    slug,
                    slug.replace("-", " ").replace("_", " ").title(),
                    mv,
                    doc,
                    QUOTES[doc] if section != "best_for" else QUOTES[doc] + " ",
                    pol,
                    ruling,
                    ruling,
                ),
            )
        c.commit()
        yield c


def _feed(conn, **kw):
    return items.feed(conn, "acme/text-a", per_page=30, prompt_version="p1", **kw)


class TestThePopulationIsTheCounts:
    def test_model_wide_is_every_non_declined_report_and_voice(self, conn):
        out = _feed(conn)
        assert out["counts"]["reports"] == 5  # d1 d2 d3 d4 d6; d5 declined
        assert out["counts"]["voices"] == 3  # au1 twice; d6 has no author
        assert {i["id"] for i in out["items"]} == {"d1", "d2", "d3", "d4", "d6"}

    def test_a_section_page_and_the_feed_agree(self, conn):
        """The number on the capability page IS the feed's number."""
        from judge.store.board_entries import board_sections

        sections = board_sections(conn, hide_source=lambda s: False)
        page = next(i for i in sections["capability"] if i["slug"] in ("tool-use", "tool_use"))
        row = next(m for m in page["models"] if m["model_key"] == "mv_a")

        out = _feed(conn, section="capability", slug="tool-use")
        assert out["counts"]["reports"] == row["reports"] == 4
        assert out["counts"]["voices"] == row["voices"]
        assert out["counts"]["reports_by_polarity"] == row["report_split"]

    def test_a_polarity_link_opens_the_reports_it_counted(self, conn):
        out = _feed(conn, section="capability", slug="tool-use", polarity="negative")
        # d3 is positive AND negative: counted in both, listed in both.
        assert {i["id"] for i in out["items"]} == {"d2", "d3"}
        assert out["counts"]["reports_by_polarity"]["negative"] == len(out["items"])

    def test_newest_posted_first_and_an_unknown_date_last(self, conn):
        out = _feed(conn)
        assert [i["id"] for i in out["items"]] == ["d1", "d2", "d3", "d6", "d4"]
        assert out["items"][-1]["posted_at"] is None


class TestWhatReachesThePage:
    def test_no_quote_from_any_source(self, conn):
        text = str(_feed(conn)) + str(_feed(conn, section="capability", slug="tool-use"))
        for quote in QUOTES.values():
            assert quote.strip() not in text

    def test_reddit_is_an_embed_and_never_its_document_link(self, conn):
        by_id = {i["id"]: i for i in _feed(conn)["items"]}
        assert by_id["d2"]["source"] == {"kind": "pending", "platform": "Reddit"}
        conn.execute(
            "INSERT INTO feed_embed "
            "(document_id, platform, outcome, url, title, author, community) "
            "VALUES ('d2', 'reddit', 'embeddable', "
            "'https://www.reddit.com/r/test/comments/abc/t/', "
            "'A title', 'someone', 'test')"
        )
        src = {i["id"]: i for i in _feed(conn)["items"]}["d2"]["source"]
        assert src["kind"] == "embed" and src["platform"] == "reddit"

    def test_other_sources_link_and_arxiv_is_acknowledged(self, conn):
        by_id = {i["id"]: i for i in _feed(conn)["items"]}
        assert by_id["d1"]["source"] == {
            "kind": "link",
            "platform": "dev.to",
            "url": "https://example.test/d1",
        }
        assert by_id["d6"]["source"]["acknowledgement"] == publication.arxiv_acknowledgement()


class FakeModel:
    """Answers per call from a script; records what it was asked."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.asked = []

    def __call__(self, **kw):
        self.asked.append(kw)
        return self.answers.pop(0), "deepseek/deepseek-v4-flash-0731"


class TestParaphrases:
    def test_a_refused_paraphrase_is_asked_again_once(self, conn):
        units, _ = paraphrase.pending(conn, "p1")
        units = [u for u in units if u["document_id"] in ("d1", "d2")]
        model = FakeModel(
            {
                "paraphrases": [
                    {
                        "id": "R1",
                        "text": "It handled every tool call in my agent loop without fail.",
                    },
                    {"id": "R2", "text": "Describes broken JSON arguments on version 4.1."},
                ]
            },
            {
                "paraphrases": [
                    {"id": "R1", "text": "Reports an agent loop where tool use never failed."}
                ]
            },
        )
        report = paraphrase.run(conn, units, P_SETTINGS, call=model)
        assert report["stored"] == 2 and report["calls"] == 2 and report["refused"] == {}
        assert report["asked_again"] == 1
        assert "was refused" in model.asked[1]["user"]
        texts = {i["id"]: i["paraphrase"] for i in _feed(conn)["items"]}
        assert texts["d1"] == "Reports an agent loop where tool use never failed."
        assert texts["d3"] is None  # not asked: listed, without text (rule 4)

    def test_refused_twice_is_counted_and_the_report_stays(self, conn):
        units = [u for u in paraphrase.pending(conn, "p1")[0] if u["document_id"] == "d2"]
        bad = {"paraphrases": [{"id": "R1", "text": "Broken JSON in 40% of calls."}]}
        report = paraphrase.run(conn, units, P_SETTINGS, call=FakeModel(bad, bad))
        assert report["stored"] == 0
        assert report["refused"] == {"adds a number not in the excerpts": 1}
        assert {i["id"]: i["paraphrase"] for i in _feed(conn)["items"]}["d2"] is None

    def test_a_changed_report_makes_its_paraphrase_stale(self, conn):
        units = [u for u in paraphrase.pending(conn, "p1")[0] if u["document_id"] == "d2"]
        ok = {"paraphrases": [{"id": "R1", "text": "Describes broken JSON arguments on 4.1."}]}
        paraphrase.run(conn, units, P_SETTINGS, call=FakeModel(ok))
        assert "d2" not in {u["document_id"] for u in paraphrase.pending(conn, "p1")[0]}
        conn.execute(
            "UPDATE board_entry SET quote = quote || ' Also slow.' WHERE document_id = 'd2'"
        )
        assert "d2" in {u["document_id"] for u in paraphrase.pending(conn, "p1")[0]}
        assert {i["id"]: i["paraphrase"] for i in _feed(conn)["items"]}["d2"] is None


def _paraphrase_all(conn):
    units, _ = paraphrase.pending(conn, "p1")
    texts = {
        "d1": "Reports an agent loop where tool use never failed.",
        "d2": "Describes broken JSON arguments on 4.1.",
        "d3": "Strong tool picking, but loops when a tool errors.",
        "d4": "Found its reasoning unremarkable.",
        "d6": "A paper measuring tool-use accuracy at 82.5.",
    }
    answer = {
        "paraphrases": [
            {"id": f"R{i}", "text": texts[u["document_id"]]} for i, u in enumerate(units, 1)
        ]
    }
    paraphrase.run(conn, units, P_SETTINGS, call=FakeModel(answer))


class TestSummaries:
    def test_a_draft_is_invisible_until_a_person_approves_it(self, conn):
        _paraphrase_all(conn)
        model = FakeModel(
            {
                "paragraphs": [
                    {"text": "Tool selection is described as strong.", "cites": ["R1", "R3"]},
                    {"text": "Others describe broken arguments on 4.1.", "cites": ["R2"]},
                ]
            }
        )
        out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=model)
        assert out["stored"] and out["reports_used"] == 5
        assert summary.current(conn, "acme/text-a") == {
            "model": items.resolve_model(conn, "acme/text-a"),
            "summary": None,
            "state": "awaiting_review",
        }

        summary.review(conn, out["id"], "approve")
        live = summary.current(conn, "acme/text-a")
        assert live["state"] == "approved"
        assert set(live["summary"]["cited"]) == {"d1", "d2", "d3"}
        assert live["reports_since"] == 0

    def test_a_new_approval_supersedes_the_last(self, conn):
        _paraphrase_all(conn)
        page = {"paragraphs": [{"text": "Tool selection is described as strong.", "cites": ["R1"]}]}
        first = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(page))
        summary.review(conn, first["id"], "approve")
        second = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(page))
        summary.review(conn, second["id"], "approve")
        assert summary.counts(conn) == {"approved": 1, "superseded": 1}
        assert summary.current(conn, "acme/text-a")["summary"]["id"] == second["id"]

    def test_refused_twice_is_not_stored(self, conn):
        _paraphrase_all(conn)
        uncited = {"paragraphs": [{"text": "Tool use is mixed.", "cites": []}]}
        out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(uncited, uncited))
        assert out == {
            "stored": False,
            "model": out["model"],
            "refused": "paragraph 1 cites no report; then paragraph 1 cites no report",
            "run_id": out["run_id"],
        }
        assert summary.counts(conn) == {}

    def test_too_few_paraphrased_reports(self, conn):
        with pytest.raises(summary.NotEnoughReports):
            summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel())


# ── the call and the gate, no database ────────────────────────────────────


def test_a_substituted_model_is_refused_after_its_spend_is_recorded(monkeypatch):
    from judge.feed import llm

    recorded = []
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.test/api/v1")
    monkeypatch.setattr(llm.spend_ledger, "record", lambda **kw: recorded.append(kw))

    class Resp:
        status_code = 200

        def json(self):
            return {
                "model": "some/other-model",
                "usage": {"prompt_tokens": 10, "cost": 0.001},
                "choices": [{"message": {"tool_calls": []}}],
            }

    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: Resp())
    with pytest.raises(llm.FeedModelUnavailable, match="served"):
        llm.call_tool(
            model="deepseek/deepseek-v4-flash",
            system="s",
            user="u",
            tool=paraphrase.TOOL,
            run_id="r",
            max_tokens=10,
            reasoning_effort="none",
        )
    assert recorded and recorded[0]["stage"] == "feed"


def test_drafts_and_review_stay_behind_the_token(monkeypatch):
    from fastapi.testclient import TestClient

    from judge.app import app

    monkeypatch.setenv("API_TOKEN", "s3cret")
    client = TestClient(app)
    assert client.get("/feed/summaries").status_code == 401
    assert client.post("/feed/summaries/draft", json={"model": "x"}).status_code == 401
    assert (
        client.post("/feed/summaries/review", json={"id": "x", "decision": "approve"}).status_code
        == 401
    )


def test_the_settings_and_terms_are_read_strictly():
    from judge.config import evidence_feed_settings

    cfg = evidence_feed_settings()
    assert cfg["paraphrase"]["model"] == "deepseek/deepseek-v4-flash"
    terms = publication.evidence_feed_terms()
    assert terms["embed_only"] == ("reddit", "x")


def test_a_measured_figure_is_flagged_and_a_version_is_not():
    sources = {"R1": ["Reports 60 tokens per second and 82.02% on agentic coding with 4.6."]}
    reason, flags = checks.summary_problems(
        [
            {
                "text": "Throughput near 60 tokens per second, 82.02% on agentic coding, "
                "better than 4.6.",
                "cites": ["R1"],
            }
        ],
        sources,
        "Acme A",
        excerpts={"R1": ["unrelated words"]},
        max_words=450,
        max_paragraphs=7,
        max_copied_words=8,
        quantity_words=["most"],
    )
    assert reason is None
    assert [f["detail"].split("”")[0].strip("“") for f in flags] == [
        "60 tokens per second",
        "82.02%",
    ]


def test_a_re_ask_carries_the_refused_text_and_the_copied_phrase(conn):
    """Told only "copies 7 words", the model guessed which seven and often
    wrote them again. The re-ask names the phrase and shows what was refused."""
    units = [u for u in paraphrase.pending(conn, "p1")[0] if u["document_id"] == "d2"]
    copy = "Tool calls kept coming back with malformed JSON arguments."
    copied = {"paraphrases": [{"id": "R1", "text": copy}]}
    fixed = {"paraphrases": [{"id": "R1", "text": "Describes broken JSON arguments on 4.1."}]}
    model = FakeModel(copied, copied, fixed)
    report = paraphrase.run(conn, units, {**P_SETTINGS, "attempts": 3}, call=model)
    assert report["stored"] == 1 and report["calls"] == 3 and report["asked_again"] == 1
    second = model.asked[1]["user"]
    assert "Tool calls kept coming back with malformed JSON arguments." in second
    assert "“tool calls kept coming back with malformed json arguments”" in second
    assert "different words" in second


def test_the_copy_refusal_names_the_phrase():
    problem = checks.paraphrase_problem(
        "The author says tool calls kept coming back with malformed JSON arguments.",
        [QUOTES["d2"]], "Acme A 4.1", max_chars=320, max_copied_words=6)
    assert problem.endswith("“tool calls kept coming back with malformed json arguments”")


def test_a_compare_category_and_the_feed_agree(conn):
    """Compare's category score and the feed's category filter count the same
    reports with the same polarity: same filing (`filer`), same metric-is-
    neutral rule (`counted_polarity`). An entry filed nowhere (`tool_use`, d3's
    second row) counts in no category on either side."""
    from judge.category_scores import scores_for

    scores = {c["key"]: c for c in scores_for(conn, ["mv_a", "acme/text-a"])}
    for key in ("agents", "reasoning"):
        out = _feed(conn, category=key)
        c = scores[key]
        assert out["counts"]["reports"] == c["reports"], key
        split = out["counts"]["reports_by_polarity"]
        assert (split["positive"], split["negative"], split["both"], split["neutral"]) == (
            c["positive"], c["negative"], c["both"], c["neutral"]), key
        assert out["filter"]["name"] == c["name"]


def test_a_category_is_its_own_filter(conn):
    with pytest.raises(ValueError):
        _feed(conn, category="agents", section="capability")
    with pytest.raises(ValueError):
        _feed(conn, category="no-such-category")


def test_the_last_attempt_asks_for_the_gist_under_the_same_checks(conn):
    """After the re-asks, the last try asks for one short sentence with no
    number and no name - and it is checked exactly like the others."""
    units = [u for u in paraphrase.pending(conn, "p1")[0] if u["document_id"] == "d2"]
    bad = {"paraphrases": [{"id": "R1", "text": "Broken JSON in 40% of calls."}]}
    gist = {"paraphrases": [{"id": "R1", "text": "Reports broken tool arguments, a complaint."}]}
    model = FakeModel(bad, bad, gist)
    report = paraphrase.run(conn, units, {**P_SETTINGS, "attempts": 3}, call=model)
    assert report["stored"] == 1
    assert "Last try for R1" in model.asked[2]["user"]
    assert "Last try" not in model.asked[1]["user"]


def test_a_number_in_the_reports_own_topic_may_be_repeated():
    """The prompt shows the topic each excerpt is filed under; "3D modeling"
    is not an invented figure. Copying is still judged on the excerpts."""
    excerpts = ["Fable 5.1 one shotted this"]
    text = "Reports that Fable 5.1 finished a 3D modeling task in one attempt."
    assert checks.paraphrase_problem(text, excerpts, "Claude Fable 5.1", max_chars=320,
                                     max_copied_words=6) is not None
    assert checks.paraphrase_problem(text, excerpts, "Claude Fable 5.1", max_chars=320,
                                     max_copied_words=6, topics=["3D modeling"]) is None


def test_a_bare_number_citation_is_its_report_id(conn):
    """`19` is `R19`; an id naming no report given is still refused."""
    _paraphrase_all(conn)
    page = {"paragraphs": [{"text": "Tool selection is described as strong.", "cites": ["1", "r3"]}]}
    out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(page))
    assert out["stored"]
    bad = {"paragraphs": [{"text": "Tool selection is described as strong.", "cites": ["99"]}]}
    out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(bad, bad))
    assert not out["stored"] and "not given" in out["refused"]
