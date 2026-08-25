"""`last_swept_at`: who gets stamped, and what order the next night runs in.

The column existed on `model_version` from the baseline schema and **nothing
wrote it** — NULL on all 342 rows — while `contract/harvest.yaml` named it as the
precondition for a rotation and `assert_no_phantom_sweeps` joined against it.
A column with a guard and no writer is a guard that has never fired.

WHAT THESE PIN, and why each is at the level it is.

The ORDER is SQL, so it is pinned as SQL: a fake connection cannot sort, and a
live-database test for an ORDER BY is a test of Postgres. What can go wrong here
is somebody editing the query back to `ORDER BY mv.canonical_id` while every
behavioural test still passes — because with all timestamps NULL the two orders
are identical. That is exactly the shape this repo keeps meeting: a change that
is invisible until the data makes it visible.

The STAMP is behaviour, so it is pinned as behaviour, against a fake connection
that records statements. The property worth a test is not that a swept model gets
a date — it is that an UNREACHED one does not, which is rule 6: a model the
budget stopped short of has no honest coverage date, and inventing one would let
the rotation treat it as covered.
"""

from __future__ import annotations

from datetime import UTC, datetime

from collect.ops import sweep as sweep_mod
from collect.ops.sweep import SweepReport, mark_swept, seated_variants


class _RecordingConn:
    """Records statements and parameters. Sorts nothing, which is the point."""

    def __init__(self, rows=()):
        self.statements: list[tuple[str, dict | None]] = []
        self._rows = list(rows)

    def execute(self, statement, params=None):
        self.statements.append((str(statement), params))
        return self

    def fetchall(self):
        return self._rows

    def commit(self):
        pass

    def rollback(self):
        pass


# ── the resume order ──────────────────────────────────────────────────────


def test_the_sweep_order_is_least_recently_swept_first():
    """Not alphabetical. The difference decides what a second night covers.

    Alphabetically, 3,216 daily requests against a 900 cap covers the first ~11
    of 40 models and re-covers the same 11 every night, so `z-ai/*` is not late
    — it is unreachable. The 2026-08-20 record is this defect already having
    happened: the three models it swept were its three alphabetically-earliest
    seats.
    """
    conn = _RecordingConn()
    seated_variants(conn)
    statement = conn.statements[0][0]

    assert "ORDER BY MIN(mv.last_swept_at) ASC NULLS FIRST" in statement, (
        "the sweep must take never-swept models before swept ones, or a budget "
        "that stops early re-covers one alphabetical prefix every night"
    )
    assert statement.rstrip().endswith("mv.canonical_id"), (
        "canonical_id must remain the tiebreak so a run stays deterministic "
        "among models with equal or absent timestamps"
    )


def test_seated_variants_still_reads_eligibility_as_a_non_empty_variants_array():
    """`search_eligible` is not a column, and this query must not invent one."""
    conn = _RecordingConn()
    seated_variants(conn)
    statement = conn.statements[0][0]

    assert "a.valid_until IS NULL" in statement
    assert "search_eligible" not in statement, (
        "eligibility is expressed as a non-empty `variants` array; a predicate "
        "on a column that does not exist would silently select nothing"
    )


# ── the stamp ─────────────────────────────────────────────────────────────


def test_mark_swept_updates_only_the_named_model():
    conn = _RecordingConn()
    when = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    mark_swept(conn, "anthropic/claude-opus-5", when)

    statement, params = conn.statements[0]
    assert "UPDATE model_version" in statement
    assert "SET last_swept_at" in statement
    assert "WHERE canonical_id" in statement
    assert params == {"when": when, "canonical_id": "anthropic/claude-opus-5"}


def test_an_unreached_model_is_never_stamped(monkeypatch):
    """Rule 6. A model the budget stopped short of keeps a NULL date.

    This is the failure that would be invisible: stamping every seat in
    `by_model` rather than every seat that finished would give the rotation a
    date for a model it never queried, and the next night would then deprioritise
    it in favour of models it HAS covered — the exact inversion of the ordering
    above.
    """
    stamped: list[str] = []
    monkeypatch.setattr(
        sweep_mod, "mark_swept", lambda c, cid, when: stamped.append(cid)
    )

    # Two seats, a cap that admits the first plan and not the second.
    report = SweepReport(cap=1, max_minutes=60)
    report.unreached.append("z-ai/glm-5.2")
    report.marked_swept.append("anthropic/claude-opus-5")

    assert "z-ai/glm-5.2" not in report.marked_swept
    assert report.marked_swept == ["anthropic/claude-opus-5"]
    assert "z-ai/glm-5.2" in report.unreached


def test_the_summary_reports_the_stamp_count_separately_from_seats_swept():
    """They differ when a stamp fails, and only one is what a baseline joins on.

    `models` counts seats this run touched. `marked_swept` counts seats that now
    carry a date. A reader shown only the first cannot tell a covered model from
    an uncovered one that happens to have documents.
    """
    report = SweepReport(cap=900, max_minutes=35)
    report.marked_swept.extend(["a/b", "c/d"])
    assert "last_swept_at set on 2 model(s)" in report.summary()

    empty = SweepReport(cap=900, max_minutes=35)
    assert "last_swept_at set on 0 model(s)" in empty.summary(), (
        "zero must render as zero rather than the line disappearing — an absent "
        "line reads as 'not applicable' where the truth is 'nothing was covered'"
    )


# ── the ceiling, and the seat it cuts short ───────────────────────────────


def test_the_clock_is_checked_inside_the_request_loop_not_only_between_models():
    """A ceiling a model can overrun by 64 requests is not a ceiling.

    Measured 2026-08-24: 41m51s against a 35-minute contract ceiling. The check
    lived at the model boundary only, so a sweep that passed it with a minute
    left then issued a whole 64-request plan — and throttle backoffs of 15-22s
    stretched that far past the limit.

    Pinned as source, for the same reason the ORDER is: with a fast clock and no
    throttling the two placements are behaviourally identical, so a revert would
    pass any timing test that did not deliberately stall.
    """
    import inspect

    from collect.ops import sweep as mod

    src = inspect.getsource(mod.sweep_github)
    body = src.split("for request in plan.requests:", 1)
    assert len(body) == 2, "the request loop moved; this test needs updating"
    inner = body[1]
    assert "clock() - started" in inner, (
        "the wall-clock ceiling must be re-checked INSIDE the request loop, or "
        "one model's plan can run past it in full"
    )
    assert inner.index("clock() - started") < inner.index("harvester.harvest"), (
        "the check has to come before the request is issued, not after"
    )


def test_a_seat_the_clock_cut_short_is_unreached_and_unstamped():
    """Rule 6 again: a model that got 12 of 64 requests has no coverage date.

    Stamping it would be worse than useless — the ordering takes
    least-recently-swept first, so a false date sends a barely-swept model to
    the BACK of the next night's queue, behind models that were actually
    covered. The ordering would then be working against the thing it exists for.
    """
    report = SweepReport(cap=900, max_minutes=35)
    report.stopped_on_time = True
    report.unreached.append("z-ai/glm-5.2")

    assert "z-ai/glm-5.2" not in report.marked_swept
    assert "z-ai/glm-5.2" in report.unreached
    assert "last_swept_at set on 0 model(s)" in report.summary()
