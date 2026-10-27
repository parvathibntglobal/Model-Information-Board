"""The evidence feed's upkeep agent (2026-10-27, PROPOSED): judge/feed/revise.py,
the refusal memory in paraphrase.py and summary.py, and the spend cap in llm.py.

What these hold, in the order a reader would worry about them:

    NOTHING IS PAID FOR TWICE. A paraphrase or a summary the checks refused is
    remembered, and asked for again only when its input changes (Parvathi's
    #558 condition for any schedule).

    A CAP STOPS THE RUN, AND IS NOT A VERDICT. Reports the cap left unasked are
    pending next run, never stored as refused.

    A REVISION EDITS POINTS, NEVER THE PAGE. Code splices the edits in, so an
    untouched paragraph is the approved text byte for byte; every edit cites a
    new report; the page stays inside the same limits; a person approves it.

    NO CHANGE IS AN ANSWER. It is stored, and the model is not asked again until
    a newer report arrives and a week has passed.

Requires a database. See docs/dev-database.md.
"""

# The shared fixtures are imported by name, which is how pytest finds them;
# a test taking `conn` therefore "redefines" it as far as ruff can see.
# ruff: noqa: F811

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from judge.feed import llm, paraphrase, revise, summary
from tests.test_evidence_feed import (  # noqa: F401 - fixtures, used by name
    P_SETTINGS,
    S_SETTINGS,
    FakeModel,
    _paraphrase_all,
    _public_view,
    _seated,
    conn,
)

R_SETTINGS = {
    "prompt_version": "r1",
    "every_days": 7,
    "min_new_reports": 1,
    "max_changes": 2,
    "max_point_sentences": 2,
    "attempts": 2,
}

FIRST = "Tool selection is described as strong."
SECOND = "Others describe broken arguments on 4.1."


@pytest.fixture(autouse=True)
def _fresh_spend():
    llm.reset_spent()
    yield
    llm.reset_spent()


def _approved(conn, *, newest="2026-10-18"):
    """An approved two-paragraph summary written from the reports up to
    `newest`, so d1 (10-20) and d2 (10-19) are newer than it."""
    _paraphrase_all(conn)
    page = {"paragraphs": [{"text": FIRST, "cites": ["R3"]}, {"text": SECOND, "cites": ["R2"]}]}
    out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(page))
    summary.review(conn, out["id"], "approve")
    conn.execute(
        "UPDATE feed_summary SET newest_report_at = %s",
        (datetime.fromisoformat(newest + "T00:00:00+00:00"),),
    )
    conn.execute("DELETE FROM feed_summary_attempt")
    conn.commit()
    return out["id"]


def _revise(conn, *answers):
    return revise.revise(
        conn, "acme/text-a", S_SETTINGS, R_SETTINGS, "p1", call=FakeModel(*answers)
    )


# ── paraphrase refusals are remembered ─────────────────────────────────────


def test_a_refused_paraphrase_is_not_asked_again_until_its_excerpts_change(conn):
    units = [u for u in paraphrase.pending(conn, "p1")[0] if u["document_id"] == "d2"]
    bad = {"paraphrases": [{"id": "R1", "text": "Broken JSON in 40% of calls."}]}
    paraphrase.run(conn, units, P_SETTINGS, call=FakeModel(bad, bad))
    assert "d2" not in {u["document_id"] for u in paraphrase.pending(conn, "p1")[0]}
    assert paraphrase.refusals(conn, "p1") == {"adds a number not in the excerpts": 1}
    # New excerpts: a different report, asked for again.
    conn.execute("UPDATE board_entry SET quote = quote || ' Also slow.' WHERE document_id = 'd2'")
    assert "d2" in {u["document_id"] for u in paraphrase.pending(conn, "p1")[0]}
    # A new prompt version asks again too.
    assert "d2" in {u["document_id"] for u in paraphrase.pending(conn, "p2")[0]}


def test_a_stored_paraphrase_clears_its_old_refusal(conn):
    units = [u for u in paraphrase.pending(conn, "p1")[0] if u["document_id"] == "d2"]
    bad = {"paraphrases": [{"id": "R1", "text": "Broken JSON in 40% of calls."}]}
    paraphrase.run(conn, units, P_SETTINGS, call=FakeModel(bad, bad))
    conn.execute("UPDATE board_entry SET quote = quote || ' Also slow.' WHERE document_id = 'd2'")
    units = [u for u in paraphrase.pending(conn, "p1")[0] if u["document_id"] == "d2"]
    ok = {"paraphrases": [{"id": "R1", "text": "Describes broken JSON arguments, and slowness."}]}
    paraphrase.run(conn, units, P_SETTINGS, call=FakeModel(ok))
    assert paraphrase.refusals(conn, "p1") == {}


# ── the spend cap ──────────────────────────────────────────────────────────


def _costing(model, cost):
    """A fake model whose calls are counted as `call_tool`'s are."""

    def call(**kw):
        out = model(**kw)
        llm.count_spend(cost)
        return out

    return call


def test_the_cap_stops_a_paraphrase_run_and_refuses_nothing(conn):
    units, _ = paraphrase.pending(conn, "p1")
    assert len(units) == 5
    one_each = {**P_SETTINGS, "per_call": 1}
    first = {
        "paraphrases": [{"id": "R1", "text": "Reports an agent loop where tool use never failed."}]
    }
    model = FakeModel(first)
    report = paraphrase.run(conn, units, one_each, call=llm.capped(0.01, _costing(model, 0.02)))
    assert report["stored"] == 1 and report["calls"] == 1
    assert report["stopped"] and "cap is spent" in report["stopped"]
    assert report["left_for_next_run"] == 4
    assert report["refused"] == {} and paraphrase.refusals(conn, "p1") == {}
    assert len(paraphrase.pending(conn, "p1")[0]) == 4


def test_an_unreported_cost_is_counted_as_a_floor_not_a_zero():
    llm.count_spend(None)
    llm.count_spend(0.5)
    assert llm.spent() == {"usd": 0.5, "calls": 2, "unreported": 1}


# ── draft attempts ─────────────────────────────────────────────────────────


def test_a_refused_draft_is_remembered_and_not_redrafted(conn):
    _paraphrase_all(conn)
    uncited = {"paragraphs": [{"text": "Tool use is mixed.", "cites": []}]}
    out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(uncited, uncited))
    assert out["stored"] is False
    assert summary.attempts(conn)[0]["outcome"] == "refused"
    assert summary.models_due(conn, "p1", 1) == []


def test_a_draft_that_never_reached_the_model_is_not_remembered(conn):
    _paraphrase_all(conn)
    out = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=llm.capped(0.0))
    assert out["stored"] is False and "cap is spent" in out["refused"]
    assert summary.attempts(conn) == []
    assert [d["model_key"] for d in summary.models_due(conn, "p1", 1)] == ["mv_a"]


def test_an_approved_or_waiting_summary_is_never_redrafted_by_the_schedule(conn):
    _approved(conn)
    assert summary.models_due(conn, "p1", 1) == []


# ── revisions ──────────────────────────────────────────────────────────────


def test_a_revision_edits_one_point_and_leaves_the_rest_byte_for_byte(conn):
    parent = _approved(conn)
    edit = {
        "changes": [
            {
                "op": "add",
                "at": "P1.1",
                "text": "Some say tool use never failed in an agent loop.",
                "cites": ["N1"],
                "reason": "a newer report adds a reliable loop",
            }
        ]
    }
    out = _revise(conn, edit)
    assert out["outcome"] == "stored" and out["new_reports"] == 2
    row = summary.listing(conn, "pending")[0]
    assert row["parent_id"] == parent
    assert (
        row["paragraphs"][0]["text"] == FIRST + " Some say tool use never failed in an agent loop."
    )
    assert row["paragraphs"][0]["cites"] == ["d3", "d1"]
    assert row["paragraphs"][1] == {"text": SECOND, "cites": ["d2"]}
    assert row["changes"] == [
        {
            "op": "add",
            "at": "P1.1",
            "before": None,
            "after": "Some say tool use never failed in an agent loop.",
            "cites": ["d1"],
            "reason": "a newer report adds a reliable loop",
        }
    ]
    # Approved, it replaces the live summary, and the page says it was revised.
    summary.review(conn, out["id"], "approve")
    live = summary.current(conn, "acme/text-a")["summary"]
    assert live["revised"] is True and "parent_id" not in live and "changes" not in live


def test_a_replace_swaps_one_sentence_and_records_what_it_was(conn):
    _approved(conn)
    edit = {
        "changes": [
            {
                "op": "replace",
                "at": "P2.1",
                "text": "Others describe broken JSON arguments on 4.1.",
                "cites": ["2"],
                "reason": "the newer report names the JSON",
            }
        ]
    }
    out = _revise(conn, edit)
    assert out["outcome"] == "stored"
    assert out["changes"][0]["before"] == SECOND
    row = summary.listing(conn, "pending")[0]
    assert row["paragraphs"][1]["text"] == "Others describe broken JSON arguments on 4.1."
    assert row["paragraphs"][0] == {"text": FIRST, "cites": ["d3"]}


def test_no_change_against_its_own_uncovered_list_is_asked_again(conn):
    """The first live runs answered no change for a summary missing whole
    themes. A theme the model itself lists as uncovered, raised by more than
    one new report, must be added; one raised once may be left."""
    _approved(conn)
    lazy = {
        "uncovered": [{"theme": "tool loops that never fail", "reports": ["N1", "N2"]}],
        "changes": [],
        "no_change_reason": "covered",
    }
    edit = {
        "uncovered": [{"theme": "tool loops that never fail", "reports": ["N1", "N2"]}],
        "changes": [
            {
                "op": "add",
                "at": "P1.1",
                "text": "Some say tool use never failed in an agent loop.",
                "cites": ["N1"],
                "reason": "an uncovered theme",
            }
        ],
    }
    model = FakeModel(lazy, edit)
    out = revise.revise(conn, "acme/text-a", S_SETTINGS, R_SETTINGS, "p1", call=model)
    assert out["outcome"] == "stored"
    assert "proposed no change" in model.asked[1]["user"]
    # Raised by one report only: no change stands.
    conn.execute("DELETE FROM feed_summary_attempt")
    conn.execute("DELETE FROM feed_summary WHERE state = 'pending'")
    once = {"uncovered": [{"theme": "x", "reports": ["N1"]}], "changes": []}
    assert _revise(conn, once)["outcome"] == "no_change"


def test_no_change_is_stored_and_not_asked_again(conn):
    _approved(conn)
    out = _revise(conn, {"changes": [], "no_change_reason": "the new reports repeat the page"})
    assert out["outcome"] == "no_change"
    assert summary.attempts(conn)[0]["detail"] == "the new reports repeat the page"
    assert summary.counts(conn) == {"approved": 1}
    # Within the week: not due. After it: still not due, nothing newer arrived.
    due, skipped = revise.revisions_due(conn, "p1", R_SETTINGS)
    assert due == [] and "within the last 7 days" in skipped[0]["why"]
    later = datetime.now(UTC) + timedelta(days=8)
    due, skipped = revise.revisions_due(conn, "p1", R_SETTINGS, now=later)
    assert due == [] and "0 new paraphrased reports" in skipped[0]["why"]


@pytest.mark.parametrize(
    "change, why",
    [
        (
            {
                "op": "add",
                "at": "P1.1",
                "text": "Strong tool picking.",
                "cites": ["N9"],
                "reason": "r",
            },
            "N9, which is not a new report",
        ),
        (
            {"op": "add", "at": "P1.1", "text": "Strong tool picking.", "cites": [], "reason": "r"},
            "cites no new report",
        ),
        (
            {
                "op": "replace",
                "at": "P3.1",
                "text": "Strong tool picking.",
                "cites": ["N1"],
                "reason": "r",
            },
            "there is no P3.1",
        ),
        (
            {"op": "add", "at": "P1.1", "text": "One. Two. Three.", "cites": ["N1"], "reason": "r"},
            "a point is at most 2",
        ),
        (
            {"op": "rewrite", "at": "P1", "text": "All new.", "cites": ["N1"], "reason": "r"},
            "not replace, add or new_paragraph",
        ),
        (
            {
                "op": "add",
                "at": "P1.1",
                "text": "It failed in 40% of calls.",
                "cites": ["N1"],
                "reason": "r",
            },
            "paragraph 1",
        ),
    ],
)
def test_a_bad_edit_is_refused_and_remembered(conn, change, why):
    _approved(conn)
    out = _revise(conn, {"changes": [change]}, {"changes": [change]})
    assert out["outcome"] == "refused" and why in out["refused"]
    assert summary.attempts(conn)[0]["outcome"] == "refused"
    assert summary.counts(conn) == {"approved": 1}


def test_more_changes_than_the_budget_are_refused(conn):
    _approved(conn)
    c = {"op": "add", "at": "P1.1", "text": "Tool use held up.", "cites": ["N1"], "reason": "r"}
    out = _revise(conn, {"changes": [c, c, c]}, {"changes": [c, c, c]})
    assert out["outcome"] == "refused" and "at most 2" in out["refused"]


def test_a_revision_of_a_replaced_summary_cannot_be_approved(conn):
    _approved(conn)
    edit = {
        "changes": [
            {
                "op": "add",
                "at": "P1.1",
                "text": "Tool use held up in a loop.",
                "cites": ["N1"],
                "reason": "r",
            }
        ]
    }
    rev = _revise(conn, edit)
    # A person approves a full redraft in the meantime.
    page = {"paragraphs": [{"text": FIRST, "cites": ["R1"]}]}
    redraft = summary.draft(conn, "acme/text-a", S_SETTINGS, "p1", call=FakeModel(page))
    conn.execute(
        "UPDATE feed_summary SET state = 'pending', reviewed_at = NULL WHERE id = %s", (rev["id"],)
    )
    summary.review(conn, redraft["id"], "approve")
    with pytest.raises(ValueError, match="no longer the live one"):
        summary.review(conn, rev["id"], "approve")


def test_a_model_with_a_waiting_summary_is_not_revised(conn):
    _approved(conn)
    edit = {
        "changes": [
            {
                "op": "add",
                "at": "P1.1",
                "text": "Tool use held up in a loop.",
                "cites": ["N1"],
                "reason": "r",
            }
        ]
    }
    _revise(conn, edit)
    out = _revise(conn)
    assert out["outcome"] == "not_due" and "waiting for review" in out["why"]


def test_a_summary_with_no_newest_date_is_skipped_and_says_why(conn):
    _approved(conn)
    conn.execute("UPDATE feed_summary SET newest_report_at = NULL")
    due, skipped = revise.revisions_due(conn, "p1", R_SETTINGS)
    assert due == [] and "no newest report date" in skipped[0]["why"]


def test_the_weekly_cadence_has_half_a_day_of_slack(conn):
    _approved(conn)
    _revise(conn, {"changes": [], "no_change_reason": "nothing new"})
    conn.execute("UPDATE feed_summary_attempt SET newest_report_at = '2026-10-18'")
    last = summary.attempts(conn)[0]["attempted_at"]
    almost = datetime.fromisoformat(last) + timedelta(days=6, hours=13)
    due, _ = revise.revisions_due(conn, "p1", R_SETTINGS, now=almost)
    assert [d["model_key"] for d in due] == ["mv_a"]


def test_the_shipped_settings_are_the_agreed_ones():
    """anooj, 2026-10-27: weekly, point-level, $1 a night and $1 a week."""
    from judge.config import evidence_feed_settings

    cfg = evidence_feed_settings()
    assert cfg["revision"]["every_days"] == 7
    assert cfg["revision"]["max_changes"] == 2
    assert cfg["schedule"] == {"nightly_feed_usd": 1.0, "weekly_summary_usd": 1.0}


def test_sentences_split_like_the_glossary():
    assert revise.sentences("It handles v1.5 well. Then e.g. a tool fails! Next?") == [
        "It handles v1.5 well.",
        "Then e.g. a tool fails!",
        "Next?",
    ]
