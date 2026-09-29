"""The stage after cells, and the ordering that cannot be got wrong twice.

`LabelStore` and `ReportedContextStore` were both built, tested, and called by
nothing. These are the assertions that they are reached, and that the one piece
of ordering the changelog depends on is the way round it has to be.
"""

from __future__ import annotations

import pytest

from judge.curate.labels import Driver, LabelKind, LabelState, label_id_for
from judge.curate.nightly import NightlyResult, close_the_night


class Conn:
    """Remembers labels, and answers the cell and claim queries separately."""

    def __init__(self, cells=(), existing_labels=(), context_row=None):
        self.cells = list(cells)
        self.labels = {row[0]: row for row in existing_labels}
        self.context_row = context_row
        self.sql: list[str] = []
        self.changes: list[tuple] = []
        self.context_writes: list[tuple] = []
        self.deleted: list[str] = []

    def execute(self, sql, params=()):
        self.sql.append(sql)
        s = sql.strip().upper()
        outer = self

        if s.startswith("INSERT INTO LABEL_CHANGE"):
            outer.changes.append(params)
        elif s.startswith("INSERT INTO LABEL"):
            outer.labels[params[0]] = params
        elif s.startswith("DELETE FROM LABEL"):
            outer.deleted.append(params[0])
            outer.labels.pop(params[0], None)
        elif s.startswith("INSERT INTO REPORTED_CONTEXT"):
            outer.context_writes.append(params)

        class R:
            @staticmethod
            def fetchall():
                if "FROM LABEL" in s and s.startswith("SELECT"):
                    return [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in outer.labels.values()]
                if "FROM CELL" in s:
                    return outer.cells
                return []

            @staticmethod
            def fetchone():
                if "FROM CLAIM" in s:
                    return outer.context_row
                return None

        return R()


def a_cell(mv="mv1", cap="tool_calling.schema_accuracy", status="published", pos=0, neg=4):
    return (mv, cap, status, pos, neg, ["q1", "q2"])


def an_existing_label(mv="mv1", cap="tool_calling.schema_accuracy", kind=LabelKind.CRITICISED_FOR):
    return (
        label_id_for(mv, cap, str(kind)),
        mv,
        cap,
        str(kind),
        str(LabelState.PROVISIONAL),
        ["q1"],
    )


class TestItIsActuallyCalled:
    """LabelStore and ReportedContextStore each had a module and no caller -
    the eleventh and twelfth instance of that shape here, both mine."""

    def test_the_pipeline_calls_the_closing_stage(self):
        import inspect

        from judge.pipeline import Pipeline

        source = inspect.getsource(Pipeline.run_all)
        assert "close_the_night(" in source

    def test_the_pipeline_skips_it_rather_than_guessing_a_driver(self):
        """Attributing a run to `new-evidence` when the caller did not say so
        is the one thing the closing stage refuses to do."""
        import inspect

        from judge.pipeline import Pipeline

        source = inspect.getsource(Pipeline.run_all)
        # `and self._legacy` since 2026-09-24: the stage reads cells, which are
        # not written with the legacy capability cards off (`judge/legacy.py`).
        assert "if driver is not None and self._legacy:" in source

    def test_labels_are_written_from_cells(self):
        conn = Conn(cells=[a_cell()])
        result = close_the_night(conn, driver=Driver.NEW_EVIDENCE)

        assert result.labels_after == 1
        assert len(result.gained) == 1


class TestTheOrderingTheChangelogDependsOn:
    """Cells hold only the present. Once tonight's overwrite last night's the
    transition is gone, and no query can recover it."""

    def test_current_labels_are_read_before_any_are_written(self):
        conn = Conn(cells=[a_cell()], existing_labels=[an_existing_label("mv2")])
        close_the_night(conn, driver=Driver.NEW_EVIDENCE)

        first_select = next(
            i for i, s in enumerate(conn.sql) if s.strip().upper().startswith("SELECT")
        )
        first_write = next(
            i for i, s in enumerate(conn.sql) if s.strip().upper().startswith("INSERT INTO LABEL")
        )
        assert first_select < first_write, (
            "labels were written before the previous set was read, so the diff "
            "compares a set against itself and the board never changes its mind"
        )

    def test_a_label_no_longer_earned_is_recorded_as_lost_then_dropped(self):
        """The change row is what says the board used to carry it, so it is
        written before the label goes."""
        gone = an_existing_label("mv9")
        conn = Conn(cells=[a_cell()], existing_labels=[gone])
        result = close_the_night(conn, driver=Driver.NEW_EVIDENCE)

        assert len(result.lost) == 1
        assert gone[0] in conn.deleted
        change_at = next(
            i
            for i, s in enumerate(conn.sql)
            if s.strip().upper().startswith("INSERT INTO LABEL_CHANGE")
        )
        delete_at = next(
            i for i, s in enumerate(conn.sql) if s.strip().upper().startswith("DELETE FROM LABEL")
        )
        assert change_at < delete_at, "the loss was deleted before it was recorded"

    def test_an_unchanged_label_produces_no_changelog_entry(self):
        """The changelog records what the board SAYS, not every recomputation."""
        conn = Conn(cells=[a_cell()], existing_labels=[an_existing_label()])
        result = close_the_night(conn, driver=Driver.NEW_EVIDENCE)

        assert result.changes == []


class TestTheDriverIsNeverGuessed:
    def test_it_is_required(self):
        with pytest.raises(TypeError):
            close_the_night(Conn())  # type: ignore[call-arg]

    def test_it_reaches_every_change(self):
        conn = Conn(cells=[a_cell()])
        result = close_the_night(conn, driver=Driver.CONFIG_CHANGE)

        assert all(c.driver is Driver.CONFIG_CHANGE for c in result.changes)


class TestReportedContextIsLeftUnsetRatherThanZeroed:
    """The column that removes candidates without a reader seeing it happen."""

    def test_an_uncorroborated_limit_writes_no_row(self):
        """A limit two people reported, written as a row, is a threshold nobody
        corroborated doing hard filtering."""
        conn = Conn(cells=[a_cell()], context_row=(30_000, 200_000, 2, ["q1", "q2"]))
        result = close_the_night(conn, driver=Driver.NEW_EVIDENCE)

        assert result.context_rows_written == 0
        assert result.context_rows_skipped == 1
        assert conn.context_writes == []

    def test_a_corroborated_limit_is_written(self):
        conn = Conn(cells=[a_cell()], context_row=(30_000, 200_000, 3, ["q1", "q2", "q3"]))
        result = close_the_night(conn, driver=Driver.NEW_EVIDENCE)

        assert result.context_rows_written == 1
        assert conn.context_writes

    def test_the_summary_says_unset_rather_than_no_limit(self):
        result = NightlyResult(context_rows_written=1, context_rows_skipped=4)
        assert "left unset rather than set to no-limit" in result.summary()
