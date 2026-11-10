"""A tracked entry names its model by row `id` OR `canonical_id`; both must match.

Claude Fable 5.1 is tracked as `anthropic/claude-fable-5-1`, its row id, and its
canonical id is `anthropic/claude-fable-5.1`. The scheduler's `due_rows` found
that row in SQL (it queried both columns), then keyed the result by
`canonical_id` alone and dropped the model without a word. The discussed list
compared `canonical_id` alone and called the board's most-reported model
untracked. These tests pin both shapes, and that a tracked entry with no row is
named rather than dropped (rule 4).
"""
from __future__ import annotations

import scripts.run_scheduled_fetches as runner
from judge import tracked as tracked_mod
from judge.config import TrackedModel

FABLE = TrackedModel(name="Claude Fable 5.1", registry="anthropic/claude-fable-5-1", kind="text")
GONE = TrackedModel(name="Not Polled Yet", registry="acme/not-polled-yet", kind="text")

# (canonical_id, id, display_name, in_window), as model_version holds Fable 5.1.
FABLE_ROW = ("anthropic/claude-fable-5.1", "anthropic/claude-fable-5-1",
             "Anthropic: Claude Fable 5.1", True)


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return list(self._rows)


class _Conn:
    """Answers the two queries `due_rows` makes and the one `row_keys` makes."""

    def __init__(self, rows):
        self.rows = rows
        self.seen = []

    def execute(self, sql, params=None):
        self.seen.append((sql, params))
        if "FROM fetch_log" in sql:
            return _Result([])
        if sql.startswith("SELECT id, canonical_id"):
            names = set(params[0])
            return _Result([(r[1], r[0]) for r in self.rows if r[0] in names or r[1] in names])
        names = set(params[0])
        return _Result([r for r in self.rows if r[0] in names or r[1] in names])


class TestTheSchedulerFindsARowByEitherId:
    def test_an_entry_naming_the_row_id_is_due(self, monkeypatch):
        monkeypatch.setattr(tracked_mod, "all_tracked", lambda conn, **k: (FABLE,))
        (row,) = runner.due_rows(_Conn([FABLE_ROW]))
        assert row["model_version_id"] == "anthropic/claude-fable-5-1"
        assert not row.get("registry_row_missing")

    def test_an_entry_naming_the_canonical_id_is_due(self, monkeypatch):
        by_canonical = TrackedModel(name="Claude Fable 5.1",
                                    registry="anthropic/claude-fable-5.1", kind="text")
        monkeypatch.setattr(tracked_mod, "all_tracked", lambda conn, **k: (by_canonical,))
        (row,) = runner.due_rows(_Conn([FABLE_ROW]))
        assert row["model_version_id"] == "anthropic/claude-fable-5-1"

    def test_an_entry_with_no_row_comes_back_marked_not_dropped(self, monkeypatch):
        monkeypatch.setattr(tracked_mod, "all_tracked", lambda conn, **k: (FABLE, GONE))
        rows = runner.due_rows(_Conn([FABLE_ROW]))
        missing = [r for r in rows if r.get("registry_row_missing")]
        assert missing == [{"display_name": "Not Polled Yet", "registry": "acme/not-polled-yet",
                            "registry_row_missing": True}]


class TestTheRunNamesAModelItCannotFind:
    def _setup(self, monkeypatch, rows):
        monkeypatch.setenv("SCHEDULER_ENABLED", "1")
        monkeypatch.setenv("FETCH_EXTRACT", "off")
        monkeypatch.setattr(runner, "_read_only_dsn", lambda: "postgresql://x@h/db")

        class _Ctx:
            def __enter__(self): return self
            def __exit__(self, *a): return False
        monkeypatch.setattr("psycopg.connect", lambda *a, **k: _Ctx())
        monkeypatch.setattr(runner, "due_rows", lambda conn: rows)
        monkeypatch.setattr(runner, "in_progress", lambda conn, now: set())
        launched, posted = [], []
        monkeypatch.setattr(runner, "run_one", lambda d, **k: launched.append(d.display_name)
                            or {"_end": {"kind": "end", "status": "ok", "extract_skipped": True}})
        monkeypatch.setattr(runner, "post_summary", lambda recs: posted.extend(recs))
        return launched, posted

    MISSING = {"display_name": "Not Polled Yet", "registry": "acme/not-polled-yet",
               "registry_row_missing": True}
    DUE = {"model_version_id": "a", "display_name": "A", "tracked": True,
           "in_window": True, "last_success": None}

    def test_it_is_in_the_summary_and_is_not_launched(self, monkeypatch):
        launched, posted = self._setup(monkeypatch, [self.DUE, self.MISSING])
        assert runner.main([]) == 0
        assert launched == ["A"]
        named = [r for r in posted if r["model"] == "Not Polled Yet"]
        assert len(named) == 1
        assert "acme/not-polled-yet" in named[0]["status"]
        assert named[0]["status"].startswith("not run:")

    def test_it_is_posted_even_when_nothing_else_is_due(self, monkeypatch):
        launched, posted = self._setup(monkeypatch, [self.MISSING])
        assert runner.main([]) == 0
        assert launched == []
        assert [r["model"] for r in posted] == ["Not Polled Yet"]


class TestTrackedKeys:
    def test_both_shapes_of_a_matched_row_and_an_unmatched_name(self, monkeypatch):
        monkeypatch.setattr(tracked_mod, "all_tracked", lambda conn, **k: (FABLE, GONE))
        keys = tracked_mod.tracked_keys(_Conn([FABLE_ROW]))
        assert keys == {"anthropic/claude-fable-5-1", "anthropic/claude-fable-5.1",
                        "acme/not-polled-yet"}

    def test_row_keys_holds_rows_only(self):
        keys = tracked_mod.row_keys(_Conn([FABLE_ROW]),
                                    ["anthropic/claude-fable-5-1", "acme/not-polled-yet"])
        assert keys == {"anthropic/claude-fable-5-1", "anthropic/claude-fable-5.1"}


def test_auto_track_excludes_a_hand_entry_by_either_id():
    """ELIGIBLE must not re-admit Fable 5.1 by its canonical id while the hand
    entry names its row id."""
    # `mv.` since the query joins `model_catalog` for the kind (#602, item 6).
    assert "mv.canonical_id = ANY(%s) OR mv.id = ANY(%s)" in tracked_mod.ELIGIBLE
