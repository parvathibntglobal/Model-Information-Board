"""The blog's live pages (judge/blog_live.py), against a throwaway schema.

What each test pins is a rule the page states in words, so a refactor that
breaks one breaks a sentence a reader was told:

- public sources only, whatever view the deployment runs, and what that
  leaves out is counted (rule 4);
- an engineer is counted once per side; a quote is shown once;
- an empty side is returned empty, never filled or dropped;
- the disagreement order is made of the two counts every row shows (rule 3);
- reports are dated by when the post was WRITTEN, not stored (rule 7);
- a price change needs a predecessor - a first sighting is not a change;
- the quiz asks general questions, each answered by a published figure that
  every choice shows, and an unknown figure never makes a choice (rule 6).
"""

from __future__ import annotations

import pathlib
from datetime import date

import psycopg
import pytest

from judge import blog_live
from judge.config import blog_live_settings

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"
TODAY = date(2026, 10, 15)  # a Thursday; its week starts Monday 2026-10-12


@pytest.fixture
def conn(test_dsn, monkeypatch):
    # THE PUBLIC FILTER MUST NOT DEPEND ON THE DEPLOYMENT'S VIEW.
    monkeypatch.setenv("PUBLICATION_VIEW", "internal")
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.execute(SCHEMA.read_text(encoding="utf-8"))
        _seed(c)
        c.commit()
        yield c


#: Per model: context, price in, price out, listed, reads, supported parameters.
#: Distinct, so every kind of question can be built; Foxtrot publishes no
#: context window, so it must never be a choice in a context question (rule 6).
_SPECS = {
    "mv_a": (1_000_000, 0.2, 1.0, "2026-10-13", "{text,image}", "{tools,structured_outputs}"),
    "mv_b": (200_000, 3.0, 15.0, "2026-06-01", "{text}", "{tools}"),
    "mv_c": (128_000, 1.0, 4.0, "2026-03-01", "{text}", "{tools,structured_outputs}"),
    "mv_d": (32_000, 0.05, 0.1, "2025-12-01", "{text}", "{tools,structured_outputs}"),
    "mv_e": (64_000, 8.0, 40.0, "2026-08-01", "{text,audio}", "{structured_outputs}"),
    "mv_f": (None, 0.5, 2.0, "2026-01-01", "{text}", "{}"),
}


def _model(c, mv, cid, name, family, provider):
    c.execute(
        "INSERT INTO model_version (id, canonical_id, display_name, family, provider, "
        " sources, provenance) "
        "VALUES (%s, %s, %s, %s, %s, '{}', 'polled')",
        (mv, cid, name, family, provider),
    )
    ctx, pin, pout, listed, reads, params = _SPECS[mv]
    c.execute(
        "INSERT INTO model_catalog (canonical_id, provider, name, input_modalities, "
        " output_modalities, pricing, last_seen_at, listed_at, price_in, price_out, "
        " context_length, supported_parameters) "
        "VALUES (%s, %s, %s, %s, '{text}', '{}', '2026-10-15', %s, %s, %s, %s, %s)",
        (cid, provider, name, reads, listed, pin, pout, ctx, params),
    )


_doc_n = 0


def _entry(
    c,
    mv,
    slug,
    polarity,
    quote,
    *,
    author,
    source="devto",
    written="2026-10-13",
    section="capability",
    ruling=None,
    target=None,
):
    global _doc_n
    _doc_n += 1
    doc = f"d{_doc_n}"
    if author:
        c.execute(
            "INSERT INTO author (id, source, external_id) VALUES (%s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (author, source, author),
        )
    c.execute(
        "INSERT INTO document (id, source, external_id, url, text_ref, content_hash, "
        " author_id, created_at) "
        "VALUES (%s, %s, %s, %s, 'r', %s, %s, %s)",
        (doc, source, doc, f"https://example.test/{doc}", doc, author, written),
    )
    c.execute(
        "INSERT INTO board_entry (id, section, slug, name, definition, document_id, quote, "
        " quote_verified, polarity, proposer_model, pipeline_version, model_version_id, "
        " ruling, ruling_target, reviewed_at) "
        "VALUES (%s, %s, %s, %s, 'd', %s, %s, true, %s, 'm', 'v1', %s, %s, %s, %s)",
        (
            f"be{_doc_n}",
            section,
            slug,
            slug.title(),
            doc,
            quote,
            polarity,
            mv,
            ruling,
            target,
            "2026-10-14" if ruling else None,
        ),
    )


def _seed(c):
    _model(c, "mv_a", "acme/alpha-1", "Acme: Alpha 1", "alpha", "acme")
    _model(c, "mv_b", "beta/bravo-2", "Beta: Bravo 2", "bravo", "beta")
    _model(c, "mv_c", "gamma/charlie-3", "Gamma: Charlie 3", "charlie", "gamma")
    _model(c, "mv_d", "delta/delta-4", "Delta: Delta 4", "deltaco", "delta")
    long = "it kept the whole plan straight across many steps without losing track at all"
    # alpha on tool-use: 2 working (one engineer twice), 2 problems, a withheld one
    _entry(c, "mv_a", "tool-use", "positive", long, author="u1")
    _entry(c, "mv_a", "tool-use", "positive", "and again " + long, author="u1")
    _entry(c, "mv_a", "tool-use", "positive", "a third angle: " + long, author="u2")
    _entry(
        c,
        "mv_a",
        "tool-use",
        "negative",
        "the calls silently dropped arguments on every long run we tried",
        author="u3",
    )
    _entry(
        c,
        "mv_a",
        "tool-use",
        "negative",
        "Alpha 1 forgot the schema halfway through each session we ran",
        author="u4",
    )
    _entry(
        c,
        "mv_a",
        "tool-use",
        "negative",
        "withheld text that must never appear on a public page at all",
        author="r1",
        source="reddit",
    )
    # bravo on tool-use: one side only
    _entry(
        c,
        "mv_b",
        "tool-use",
        "positive",
        "it handled every tool call we threw at it in the eval harness",
        author="u5",
    )
    # a merged slug counts under its target; a declined row counts nowhere
    _entry(
        c,
        "mv_b",
        "tool-calls",
        "negative",
        "the second call always came back malformed for our runner",
        author="u6",
        ruling="merged",
        target="tool-use",
    )
    _entry(
        c,
        "mv_c",
        "tool-use",
        "negative",
        "declined row text that should never be counted anywhere",
        author="u7",
        ruling="declined",
    )
    # an old post, written weeks before the page's week
    _entry(
        c,
        "mv_d",
        "summaries",
        "positive",
        "short summaries of long incident threads were accurate for us",
        author="u8",
        written="2026-09-01",
    )
    # two more models, so a question can offer four choices
    _model(c, "mv_e", "echo/echo-5", "Echo: Echo 5", "echo", "echo")
    _model(c, "mv_f", "fox/foxtrot-6", "Fox: Foxtrot 6", "foxtrot", "fox")
    _entry(
        c,
        "mv_e",
        "tool-use",
        "positive",
        "the agent loop held up for a full day of unattended runs here",
        author="u9",
    )
    _entry(
        c,
        "mv_f",
        "summaries",
        "negative",
        "summaries dropped the one number that mattered in each report",
        author="u10",
    )
    c.execute(
        "INSERT INTO pricing_history (model_version_id, price_in, price_out, observed_at) VALUES "
        "('mv_a', 1, 2, '2026-08-20'), ('mv_a', 0.5, 2, '2026-10-13'), ('mv_b', 3, 4, '2026-10-13')"
    )


def test_settings_have_no_defaults():
    s = blog_live_settings()
    assert s["quiz"]["options"] >= 2 and s["quiz"]["margin_percent"] > 0


def test_disagreement_is_public_only_ruled_and_ordered_by_its_counts(conn):
    out = blog_live.contested(conn)
    rows = {(r["model"]["id"], r["slug"]): r for r in out["pairs"]}
    alpha = rows[("acme/alpha-1", "tool-use")]
    assert (alpha["working"], alpha["problems"]) == (2, 2)  # u1 once; reddit left out
    bravo = rows[("beta/bravo-2", "tool-use")]
    assert (bravo["working"], bravo["problems"]) == (1, 1)  # the merged row joined it
    assert ("gamma/charlie-3", "tool-use") not in rows  # declined, and one-sided
    assert [r["model"]["id"] for r in out["pairs"]] == ["acme/alpha-1", "beta/bravo-2"]
    assert out["withheld_entries"] == 1


def test_a_wall_shows_each_quote_once_and_an_empty_side_empty(conn):
    w = blog_live.wall(conn, "capability", "tool-use", "acme/alpha-1")
    assert (w["working"], w["problems"]) == (2, 2)
    assert len(w["quotes"]["positive"]) == 3 and len(w["quotes"]["negative"]) == 2
    assert all("withheld" not in q["quote"] for side in w["quotes"].values() for q in side)
    assert w["withheld_entries"] == 1
    assert [r["model"]["id"] for r in w["same_topic"]] == ["beta/bravo-2", "echo/echo-5"]
    d = blog_live.wall(conn, "capability", "summaries", "delta/delta-4")
    assert d["quotes"]["negative"] == [] and d["problems"] == 0
    assert blog_live.wall(conn, "metric", "tool-use", "acme/alpha-1") is None
    assert blog_live.wall(conn, "capability", "tool-use", "nobody/none") is None


def test_the_week_counts_posts_by_when_they_were_written(conn):
    w = blog_live.week(conn, today=TODAY)
    assert w["week"] == "2026-10-12" and w["in_progress"]
    assert w["reports"]["voices"] == 8  # u1..u6, u9, u10; u8 wrote in September
    assert [m["id"] for m in w["listings"]] == ["acme/alpha-1"]  # the one listed that week
    assert blog_live.week(conn, "2026-10-13", today=TODAY) is None  # not a Monday
    assert blog_live.week(conn, "2025-01-06", today=TODAY) is None  # not offered


def test_a_price_change_needs_a_predecessor(conn):
    w = blog_live.week(conn, today=TODAY)
    assert [(p["model"]["id"], p["was_in"], p["now_in"]) for p in w["prices"]] == [
        ("acme/alpha-1", 1.0, 0.5)
    ]
    assert w["price_history"]["last_change"] == "2026-10-13"


def test_the_quiz_asks_general_questions_with_a_clear_published_answer(conn):
    """Reworked 2026-10-15: no quotes. Each answer is a published figure, every
    choice carries its own, and an unknown figure never makes a choice."""
    cfg = blog_live_settings()["quiz"]
    seen = set()
    for n in range(1, 15):
        day = f"2026-10-{n:02d}"
        q = blog_live.quiz(conn, day, today=TODAY)
        assert q["questions"], f"no questions on {day}"
        for x in q["questions"]:
            seen.add(x["kind"])
            assert "quote" not in x
            ids = [o["id"] for o in x["options"]]
            assert x["answer"] in ids and len(set(ids)) == len(ids) == cfg["options"]
            if x["kind"] == "maker":
                continue
            assert all(o["value"] is not None for o in x["options"]), x
            values = {o["id"]: o["value"] for o in x["options"]}
            if x["kind"] in ("longest_input", "dearest_output", "most_discussed"):
                assert values[x["answer"]] == max(values.values())
            if x["kind"] == "cheapest_input":
                assert values[x["answer"]] == min(values.values())
            if x["kind"] == "longest_input":
                assert "fox/foxtrot-6" not in ids  # no published context window
    assert {"longest_input", "cheapest_input", "maker"} <= seen
    assert blog_live.quiz(conn, "2026-10-15", today=TODAY) == blog_live.quiz(
        conn, "2026-10-15", today=TODAY
    )  # same day, same quiz
    assert blog_live.quiz(conn, "2026-10-16", today=TODAY) is None  # no peeking ahead


def test_only_approved_general_questions_reach_the_quiz_and_a_shortfall_is_said(conn):
    cfg = blog_live_settings()["quiz"]
    empty = blog_live.quiz(conn, "2026-10-15", today=TODAY)
    assert empty["approved_in_bank"] == 0
    assert empty["general_shortfall"] == cfg["general_per_day"]
    assert all(q["kind"] != "general" for q in empty["questions"])

    from judge.config import quiz_drafter_settings

    topic = quiz_drafter_settings()["topics"][0]
    for i, state in enumerate(("approved", "approved", "pending", "rejected")):
        conn.execute(
            "INSERT INTO quiz_question (id, topic, difficulty, question, options, answer_index, "
            " explanation, state, proposer_model, run_id, reviewed_at) "
            'VALUES (%s, %s, \'easy\', %s, \'["a", "b", "c", "d"]\', 1, \'because\', %s, '
            " 'm', 'r', CASE WHEN %s = 'pending' THEN NULL ELSE now() END)",
            (f"qq_{i}", topic, f"Question {state} {i}?", state, state),
        )
    q = blog_live.quiz(conn, "2026-10-15", today=TODAY)
    general = [x for x in q["questions"] if x["kind"] == "general"]
    assert sorted(x["id"] for x in general) == ["qq_0", "qq_1"]  # never a draft
    assert q["general_shortfall"] == cfg["general_per_day"] - 2
    for x in general:
        assert x["answer"] in {o["id"] for o in x["options"]}
        right = next(o for o in x["options"] if o["id"] == x["answer"])
        assert right["name"] == "b"  # answer_index 1, whatever the shuffle


def test_a_preview_counts_public_reports_only(conn):
    m = blog_live.preview(conn, "model", "acme/alpha-1")
    assert (m["working"], m["problems"]) == (2, 2)
    t = blog_live.preview(conn, "cap", "tool-use")
    assert t["models"] == 3 and t["sample_problems"] is not None
    assert blog_live.preview(conn, "cap", "no-such-slug") is None
    assert blog_live.preview(conn, "metric", "tool-use") is None


# ── the reference formats (judge/blog_reference.py) ─────────────────────────


def test_the_glossary_is_every_written_description_with_public_counts(conn):
    from judge import blog_reference
    from judge.config import capability_about, job_about

    entries = blog_reference.glossary_index(conn)["entries"]
    assert len(entries) == len(capability_about()) + len(job_about())
    tool = next(e for e in entries if e["section"] == "capability" and e["slug"] == "tool-use")
    assert (tool["models"], tool["engineers"]) == (3, 7)  # merged row in, reddit and declined out
    e = blog_reference.glossary_entry(conn, "capability", "tool-use")
    assert e["about"] == capability_about()["tool-use"]
    assert [m["model"]["id"] for m in e["models"]][0] == "acme/alpha-1"
    assert e["withheld_entries"] == 1
    assert blog_reference.glossary_entry(conn, "capability", "summaries") is None  # no description


def test_an_issue_needs_enough_engineers_and_says_when_it_was_last_reported(conn):
    from judge import blog_reference

    idx = blog_reference.issues_index(conn)
    assert [(m["model"]["id"], m["issues"]) for m in idx["models"]] == [("acme/alpha-1", 1)]
    a = blog_reference.issues_for(conn, "acme/alpha-1")
    [issue] = a["issues"]
    assert (issue["slug"], issue["problems"], issue["working"]) == ("tool-use", 2, 2)
    assert issue["latest"] == "2026-10-13" and "fixed" not in issue
    assert all("withheld" not in q["quote"] for q in issue["quotes"])
    # reports, but none reaching the threshold: an empty list, said in words
    assert blog_reference.issues_for(conn, "beta/bravo-2")["issues"] == []
    assert blog_reference.issues_for(conn, "nobody/none") is None


def test_an_answer_keeps_not_published_apart_from_no(conn):
    from judge import blog_reference

    a = {x["key"]: x for x in blog_reference.answers_for(conn, "acme/alpha-1")["answers"]}
    assert a["tools"]["advertised"] is True
    assert (a["tools"]["working"], a["tools"]["problems"]) == (2, 2)
    assert a["vision_input"]["advertised"] is True
    assert a["prompt_caching"]["advertised"] is None  # no cached-read price published
    assert a["reasoning"]["mapped"] is False  # no board topic ruled to mean it
    b = {x["key"]: x for x in blog_reference.answers_for(conn, "beta/bravo-2")["answers"]}
    assert b["structured_output"]["advertised"] is False  # it lists params, not this one
    f = {x["key"]: x for x in blog_reference.answers_for(conn, "fox/foxtrot-6")["answers"]}
    assert f["tools"]["advertised"] is None  # it lists no params at all: unknown, not "no"
