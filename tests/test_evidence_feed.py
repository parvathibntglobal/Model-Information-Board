"""The evidence feed (PROPOSED 2026-10-21): judge/feed/.

What these hold, in the order a reader would worry about them:

    THE FEED IS THE COUNT'S POPULATION. A reader arrives from a number; the
    list must be exactly the reports that number counted, or it is not
    evidence for it. Asserted against `board_sections` itself, not against a
    copy of its rules.

    NO QUOTE LEAVES. Our paraphrase, tags, dates and sources - never the words
    of a report, from any source.

    THE CHECKS DECIDE, THE MODEL PROPOSES. A paraphrase that copies the
    source or adds a number is refused and asked again, up to the contract's
    `attempts`; refused every time, the report stays in the feed without text -
    never dropped (rule 4).

    A SUMMARY IS SEEN ONLY ONCE A PERSON APPROVED IT.

    STORED FOR EVERY MODEL, SHOWN FOR THE SEATED ONES. The fixture model is
    seated by default (`_seated`); the tests at the end unseat it.

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
def _seated(monkeypatch):
    """The fixture model is on the models page unless a test says otherwise -
    contract/tracked_models.yaml names real models, not `acme/text-a`."""
    monkeypatch.setattr(items, "_seated_names", lambda conn: ["acme/text-a"])


@pytest.fixture(autouse=True)
def _public_view(monkeypatch):
    publication.withheld_sources.cache_clear()
    publication.evidence_feed_terms.cache_clear()
    monkeypatch.delenv("PUBLICATION_VIEW", raising=False)
    yield
    publication.withheld_sources.cache_clear()
    publication.evidence_feed_terms.cache_clear()


#: Real shapes, slug and handle included: neither may reach a public payload.
REDDIT_PERMALINK = "https://www.reddit.com/r/ClaudeCode/comments/1wdtrsa/im_done_with_opus_5/"
X_STATUS = "https://x.com/somehandle/status/1849000000000000001"
LEAKS = ("ClaudeCode", "im_done", "opus_5", "somehandle")

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
                    REDDIT_PERMALINK
                    if source == "reddit"
                    else X_STATUS
                    if source == "x"
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

    @pytest.mark.parametrize("hidden", [(), ("reddit",)])
    def test_a_section_page_and_the_feed_agree(self, conn, monkeypatch, hidden):
        """The number on the capability page IS the feed's number - with nothing
        left out of totals (today), and with a source left out, which is what
        `totals_include_withheld: false` would do. Both sides use the reports
        page's rule (judge/reports.py), not a copy (#558 review)."""
        from judge.store.board_entries import board_sections

        monkeypatch.setattr(publication, "hidden_from_counts", lambda: hidden)
        sections = board_sections(conn, hide_source=lambda s: s in set(hidden))
        page = next(i for i in sections["capability"] if i["slug"] in ("tool-use", "tool_use"))
        row = next(m for m in page["models"] if m["model_key"] == "mv_a")

        out = _feed(conn, section="capability", slug="tool-use")
        assert out["counts"]["reports"] == row["reports"] == (4 if not hidden else 3)
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
        # A row written before the id-only change still holds the slugged
        # permalink: the payload carries its ids and nothing else either way.
        conn.execute(
            "INSERT INTO feed_embed (document_id, platform, outcome, url) "
            "VALUES ('d2', 'reddit', 'embeddable', %s)",
            (REDDIT_PERMALINK,),
        )
        src = {i["id"]: i for i in _feed(conn)["items"]}["d2"]["source"]
        assert src == {"kind": "embed", "platform": "reddit", "post_id": "1wdtrsa"}

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
        assert [s["id"] for s in summary.listing(conn, "approved")] == [second["id"]]
        # The public tab carries no reviewer or Admin field (rule 9).
        public = summary.current(conn, "acme/text-a")["summary"]
        assert not {"id", "flags", "review_note", "proposer_model", "generated_at"} & set(public)

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
    strong = "Tool selection is described as strong."
    page = {"paragraphs": [{"text": strong, "cites": ["1", "r3"]}]}
    out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(page))
    assert out["stored"]
    bad = {"paragraphs": [{"text": "Tool selection is described as strong.", "cites": ["99"]}]}
    out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(bad, bad))
    assert not out["stored"] and "not given" in out["refused"]


# ── stored for every model, shown for the seated ones (2026-10-23) ───────────


def test_an_unseated_model_is_stored_but_not_shown(conn, monkeypatch):
    """A model off the models page keeps its rows; the feed and the public
    summary refuse it with a reason, never an empty list (rule 6)."""
    monkeypatch.setattr(items, "_seated_names", lambda conn: [])
    with pytest.raises(items.NotSeated):
        _feed(conn)
    with pytest.raises(items.NotSeated):
        summary.current(conn, "acme/text-a")


def test_seated_by_row_id_is_seated_by_canonical_id_too(conn, monkeypatch):
    """contract/tracked_models.yaml names Fable 5.1 by its row id
    (`claude-fable-5-1`) and links use its canonical id (`claude-fable-5.1`).
    Comparing one shape found it unseated with 194 paraphrased reports."""
    monkeypatch.setattr(items, "_seated_names", lambda conn: ["mv_a"])
    assert items.seated_keys(conn) == {"mv_a", "acme/text-a"}
    assert _feed(conn)["counts"]["reports"] == 5


def test_the_feed_api_says_why_an_unseated_model_is_withheld(conn, monkeypatch):
    import contextlib

    from fastapi.testclient import TestClient

    from judge import app as app_module

    monkeypatch.setattr(app_module, "_conn", lambda: contextlib.nullcontext(conn))
    client = TestClient(app_module.app)
    assert client.get("/feed/models").json() == {"ids": ["acme/text-a", "mv_a"]}

    monkeypatch.setattr(items, "_seated_names", lambda conn: [])
    for path in ("/feed?model=acme/text-a", "/feed/summary?model=acme/text-a"):
        r = client.get(path)
        assert r.status_code == 404, path
        assert r.json()["seated"] is False
        assert "not on the models page" in r.json()["detail"]
    # A bad address is still a bad address, and says so differently.
    r = client.get("/feed?model=nobody/none")
    assert r.status_code == 404 and "seated" not in r.json()
    assert client.get("/feed/models").json() == {"ids": []}


def test_the_seated_list_is_a_public_read():
    from judge.gate import PUBLIC_READ_PATHS

    assert "/feed/models" in PUBLIC_READ_PATHS


# ── the #558 review: what the checks catch, and what they do not (2026-10-23) ─


def _p(text, excerpts, label="Z.ai: GLM 5", topics=()):
    return checks.paraphrase_problem(text, excerpts, label, max_chars=320,
                                     max_copied_words=6, topics=list(topics))


class TestTheChecksCatchWhatTheAmendmentSays:
    """Parvathi's five cases, each of which passed before."""

    def test_a_number_written_as_words(self):
        assert "ninety" in _p("Roughly ninety percent faster than before.", ["much faster now"])

    def test_percent_needs_a_percentage_in_the_source(self):
        assert "percent" in _p("Faster by some percent.", ["much faster now"])
        assert _p("Faster by 40 percent.", ["it is 40% faster"]) is None

    def test_a_copied_sentence_in_a_script_without_spaces(self):
        """Each character is a word, so a copied Chinese sentence is a long run."""
        src = "这个模型在长上下文任务中表现非常好而且速度很快"
        assert "copies" in _p(src, [src])

    def test_a_bare_domain_is_a_link(self):
        assert "link" in _p("Found the weights via huggingface.co last week.", ["new weights"])

    def test_a_number_from_the_model_name_only_inside_the_name(self):
        assert _p("GLM 5 handled the task well.", ["handled the task well"]) is None
        assert "adds a number" in _p("GLM 5 costs 5 dollars.", ["it is cheap"])

    def test_a_decimal_shortened_where_the_short_form_is_not_in_the_source(self):
        assert "adds a number" in _p("Scored 4 on the test.", ["scored 4.1 on the test"])

    def test_the_vendor_domain_in_the_label_may_be_written(self):
        assert _p("Z.ai released GLM 5 for coding.", ["released for coding"]) is None


class TestWhatTheChecksDoNotCatch:
    """Pinned so the rule-2 text and the code cannot drift apart: each of these
    passes, and docs/proposals/evidence-feed.md says so."""

    def test_a_shortened_decimal_when_the_short_form_is_also_in_the_source(self):
        assert _p("Scored 4 on the test.", ["Scored 4.1 on GLM 4"]) is None

    def test_a_bare_x_and_a_community_without_r_slash(self):
        assert _p("Posted on X in LocalLLaMA about speed.", ["it is fast"]) is None

    def test_a_unit_word_after_per_is_not_a_count(self):
        assert _p("Costs $0.15 per million tokens.", ["$0.15/M tokens"]) is None

    def test_a_name_that_starts_with_a_number_word(self):
        assert _p("Built a game in three.js with it.", ["built a game with it"]) is None


def test_the_shipped_retry_setting_is_what_the_code_reads(conn):
    """contract/evidence_feed.yaml `paraphrase.attempts` (4 on 2026-10-23), not
    the tests' 2: a paraphrase refused every time is asked for that many times,
    then listed without text."""
    from judge.config import evidence_feed_settings

    shipped = evidence_feed_settings()["paraphrase"]["attempts"]
    assert shipped >= 2
    units = [u for u in paraphrase.pending(conn, "p1")[0] if u["document_id"] == "d1"]
    too_long = {"paraphrases": [{"id": "R1", "text": "x " * 400}]}
    model = FakeModel(*[too_long] * shipped)
    report = paraphrase.run(conn, units, {**P_SETTINGS, "attempts": shipped}, call=model)
    assert len(model.asked) == report["calls"] == shipped
    assert report["stored"] == 0


def test_a_rejected_draft_is_not_redrafted_until_a_newer_report(conn):
    """#558 review: a rejected model was drafted again on every run, from the
    same reports a person had just turned down."""
    _paraphrase_all(conn)
    assert [d["model_key"] for d in summary.models_due(conn, "p1", 1)] == ["mv_a"]
    page = {"paragraphs": [{"text": "Tool selection is described as strong.", "cites": ["R1"]}]}
    out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(page))
    summary.review(conn, out["id"], "reject")
    assert summary.models_due(conn, "p1", 1) == []
    # A report newer than the rejected draft was written from: due again.
    conn.execute("UPDATE feed_summary SET newest_report_at = newest_report_at - interval '1 day'")
    assert [d["model_key"] for d in summary.models_due(conn, "p1", 1)] == ["mv_a"]


def test_the_public_payloads_carry_only_fields_with_a_reader(conn):
    """Rule 9 for routes the API-field audit cannot analyse (/feed and
    /feed/summary return a call, so scripts/audit_api_fields.py waives them).
    Each key here has a reader, named; a new key fails until it is named too.

    Read by web/src/routes/Evidence.jsx and web/src/evidence/parts.jsx:
      item: id (list key), posted_at (Posted), polarity (PolarityChip), tags
      (section+slug as key, name shown), paraphrase, source (SourceLine).
      feed: model.label/.canonical, filter.name, counts.*, paraphrased,
      matching, page.pages, items.
      summary: paragraphs, cited, reports_used, reports_available,
      newest_report_at, reviewed_at, state; reports_since.
    DECLARED UNCONSUMED: model.key, filter.section/.slug/.category/.polarity,
    page.page/.per_page - the request echoed back, so a response names what it
    answers; no page reads them, none is costly, and none is a figure."""
    _paraphrase_all(conn)
    feed = _feed(conn)
    assert set(feed) == {"model", "filter", "counts", "paraphrased", "matching", "page", "items"}
    assert set(feed["items"][0]) == {"id", "posted_at", "polarity", "tags", "paraphrase", "source"}
    assert all(set(t) == {"section", "slug", "name"} for i in feed["items"] for t in i["tags"])
    page = {"paragraphs": [{"text": "Tool selection is described as strong.", "cites": ["R1"]}]}
    out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(page))
    summary.review(conn, out["id"], "approve")
    live = summary.current(conn, "acme/text-a")
    assert set(live) == {"model", "summary", "state", "reports_since"}
    assert set(live["summary"]) == {"state", "paragraphs", "reports_used", "reports_available",
                                    "newest_report_at", "reviewed_at", "cited"}


# ── embeds travel as ids (#558 second review) ────────────────────────────────


class TestEmbedIds:
    @pytest.mark.parametrize("url, ids", [
        (REDDIT_PERMALINK, {"post_id": "1wdtrsa"}),
        ("https://www.reddit.com/r/LocalLLaMA/comments/1abc2de/some_title/kx9y8z7/?context=3",
         {"post_id": "1abc2de", "comment_id": "kx9y8z7"}),
        ("https://www.reddit.com/comments/1wdtrsa/", {"post_id": "1wdtrsa"}),
        ("https://www.reddit.com/comments/1abc2de/_/kx9y8z7/",
         {"post_id": "1abc2de", "comment_id": "kx9y8z7"}),
    ])
    def test_reddit_ids_from_any_form(self, url, ids):
        assert items.embed_ids("reddit", url) == ids
        # The stored form round-trips, and carries no community or slug.
        canonical = items.canonical_embed_url("reddit", ids)
        assert items.embed_ids("reddit", canonical) == ids
        assert "/r/" not in canonical and "title" not in canonical

    def test_x_ids_and_no_handle(self):
        ids = items.embed_ids("x", X_STATUS)
        assert ids == {"status_id": "1849000000000000001"}
        assert items.canonical_embed_url("x", ids) == "https://x.com/i/status/1849000000000000001"

    @pytest.mark.parametrize("platform, url", [
        ("reddit", "https://example.test/r/x/comments/abc/"),
        ("reddit", "https://www.reddit.com/user/someone/"),
        ("x", "https://x.com/somehandle"),
        ("x", None),
    ])
    def test_an_unrecognised_address_is_no_embed(self, platform, url):
        assert items.embed_ids(platform, url) is None

    def test_an_x_item_sends_its_status_id_only(self):
        entry = {"source": "x", "url": X_STATUS}
        src = items.cite_source(entry, {"outcome": "embeddable", "url": X_STATUS})
        assert src == {"kind": "embed", "platform": "x", "status_id": "1849000000000000001"}


def test_no_community_slug_or_handle_reaches_either_payload(conn):
    conn.execute(
        "INSERT INTO feed_embed (document_id, platform, outcome, url) "
        "VALUES ('d2', 'reddit', 'embeddable', %s)", (REDDIT_PERMALINK,))
    _paraphrase_all(conn)
    page = {"paragraphs": [{"text": "Others describe broken arguments on 4.1.", "cites": ["R2"]}]}
    out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(page))
    summary.review(conn, out["id"], "approve")
    live = summary.current(conn, "acme/text-a")
    assert "d2" in live["summary"]["cited"]
    for payload in (str(_feed(conn)), str(live)):
        for leak in LEAKS:
            assert leak not in payload, leak


def _load_build_script():
    import importlib.util

    path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "build_evidence_feed.py"
    spec = importlib.util.spec_from_file_location("build_evidence_feed", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _oembed(status=None, raise_=None):
    import httpx

    def handler(request):
        assert request.url.host == "www.reddit.com" and request.url.path == "/oembed"
        if raise_ is not None:
            raise raise_
        return httpx.Response(status, json={"title": "t", "author_name": "a"})

    return httpx.Client(transport=httpx.MockTransport(handler))


class TestResolvingEmbeds:
    """#558 second review: only a post that is gone is stored as unavailable; a
    failure to ask leaves the document pending, counted by reason."""

    def _run(self, conn, client):
        build = _load_build_script()
        return build.embeds(conn, apply=True, limit=None, client=client, reader=object(),
                            sleep=lambda s: None)

    def _row(self, conn):
        return conn.execute(
            "SELECT outcome, url FROM feed_embed WHERE document_id = 'd2'").fetchone()

    @pytest.mark.parametrize("status", [429, 500, 503])
    def test_a_failure_to_ask_is_not_stored(self, conn, status):
        report = self._run(conn, _oembed(status))
        assert self._row(conn) is None
        assert report["retry_later"] == {f"HTTP {status}": 1}
        assert report["unavailable"] == 0

    def test_a_transport_error_is_not_stored(self, conn):
        import httpx

        report = self._run(conn, _oembed(raise_=httpx.ReadTimeout("slow")))
        assert self._row(conn) is None and report["retry_later"] == {"ReadTimeout": 1}

    @pytest.mark.parametrize("status", [403, 404])
    def test_a_gone_post_is_stored_as_unavailable(self, conn, status):
        report = self._run(conn, _oembed(status))
        assert self._row(conn) == ("unavailable", None) and report["unavailable"] == 1

    def test_a_live_post_is_stored_by_its_ids_alone(self, conn):
        self._run(conn, _oembed(200))
        assert self._row(conn) == ("embeddable", "https://www.reddit.com/comments/1wdtrsa/")

    def test_a_retried_document_is_asked_again(self, conn):
        self._run(conn, _oembed(429))
        self._run(conn, _oembed(200))
        assert self._row(conn)[0] == "embeddable"


def test_summaries_are_drafted_for_seated_models_only(conn, monkeypatch):
    """#558 second review: /feed/summary refuses an unseated model, so a draft
    for one could only be paid for and queued, never shown."""
    _paraphrase_all(conn)
    assert [d["model_key"] for d in summary.models_due(conn, "p1", 1)] == ["mv_a"]
    monkeypatch.setattr(items, "_seated_names", lambda conn: [])
    assert summary.models_due(conn, "p1", 1) == []


def test_a_summary_citation_follows_the_feeds_withheld_rule(conn, monkeypatch):
    """#558 second review: if the feed ever stops drawing on a withheld source,
    an approved summary's citation of it must stop too."""
    _paraphrase_all(conn)
    page = {"paragraphs": [{"text": "Others describe broken arguments on 4.1.", "cites": ["R2"]}]}
    out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(page))
    summary.review(conn, out["id"], "approve")
    shown = summary.current(conn, "acme/text-a")["summary"]["cited"]["d2"]
    assert shown["paraphrase"]
    terms = {**publication.evidence_feed_terms(), "may_draw_on_withheld": False}

    def stand_in():
        return terms

    stand_in.cache_clear = lambda: None  # the autouse fixture clears the real cache
    monkeypatch.setattr(publication, "evidence_feed_terms", stand_in)
    monkeypatch.setattr(publication, "withheld_publicly", lambda source: source == "reddit")
    cited = summary.current(conn, "acme/text-a")["summary"]["cited"]["d2"]
    assert cited["paraphrase"] is None and cited["source"] == {"kind": "withheld"}
    feed_item = {i["id"]: i for i in _feed(conn)["items"]}["d2"]
    assert feed_item["paraphrase"] is None and feed_item["source"] == {"kind": "withheld"}


def test_a_held_source_is_withheld_even_where_the_feed_may_draw_on_it(conn, monkeypatch):
    """#567 review: a HELD source (terms with a condition not yet met - Bluesky
    until its contact address is named) shows no paraphrase and no source on
    the feed, in its summaries' citations and to the paraphraser, while
    `may_draw_on_withheld` stays true. Still listed: it is in the count."""
    _paraphrase_all(conn)
    page = {"paragraphs": [{"text": "Others describe broken arguments on 4.1.", "cites": ["R2"]}]}
    out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(page))
    summary.review(conn, out["id"], "approve")
    real = publication.evidence_feed_terms()
    assert real["may_draw_on_withheld"] is True and "bluesky" in real["held"]
    terms = {**real, "held": ("reddit",)}  # d2's source, held for the test

    def stand_in():
        return terms

    stand_in.cache_clear = lambda: None
    monkeypatch.setattr(publication, "evidence_feed_terms", stand_in)
    feed_item = {i["id"]: i for i in _feed(conn)["items"]}["d2"]
    assert feed_item["paraphrase"] is None and feed_item["source"] == {"kind": "withheld"}
    cited = summary.current(conn, "acme/text-a")["summary"]["cited"]["d2"]
    assert cited["paraphrase"] is None and cited["source"] == {"kind": "withheld"}
    assert publication.feed_hides("reddit") and not publication.feed_hides("devto")


def test_a_missing_held_list_refuses(monkeypatch):
    """No `held` key is not "nothing held": it refuses (rule 6)."""
    import judge.config as config

    doc = {"evidence_feed": {"may_draw_on_withheld": True, "embed_only": ["reddit"]}}
    monkeypatch.setattr(config, "_read", lambda name: doc)
    publication.evidence_feed_terms.cache_clear()
    try:
        with pytest.raises(publication.PublicationConfigError):
            publication.evidence_feed_terms()
    finally:
        publication.evidence_feed_terms.cache_clear()
