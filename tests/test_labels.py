"""Labels, and the transition that cannot be recovered afterwards.

`judge/pages/changelog.py` read `label_change` and nothing wrote it. These are
the assertions for the writer, and the ones that matter are about the DRIVER -
because once tonight's cells overwrite last night's, no query can say whether
a label went because the world changed or because we did.
"""

from __future__ import annotations

import pytest

from judge.curate.labels import (
    Change,
    Driver,
    Label,
    LabelKind,
    LabelState,
    LabelStore,
    diff,
    label_id_for,
)


class Conn:
    def __init__(self, rows=()):
        self._rows, self.sql, self.params = list(rows), [], []

    def execute(self, sql, params=()):
        self.sql.append(sql)
        self.params.append(params)
        rows = self._rows

        class R:
            @staticmethod
            def fetchall():
                return rows

            @staticmethod
            def fetchone():
                return rows[0] if rows else None

        return R()


def a_label(capability="tool_calling.schema_accuracy", kind=LabelKind.CRITICISED_FOR):
    return Label(
        label_id=label_id_for("mv1", capability, str(kind)),
        model_version_id="mv1",
        capability_key=capability,
        kind=kind,
        state=LabelState.PROVISIONAL,
        earned_by_quote_ids=("q1", "q2"),
    )


class TestWhatACellEarns:
    def test_a_published_negative_cell_earns_criticism(self):
        label = Label.from_cell(
            model_version_id="mv1",
            capability_key="k",
            status="published",
            positive=0,
            negative=4,
            quote_ids=("q1",),
        )
        assert label is not None
        assert label.kind is LabelKind.CRITICISED_FOR

    def test_an_insufficient_cell_earns_nothing(self):
        """A cell that does not publish has no finding to make durable."""
        assert (
            Label.from_cell(
                model_version_id="mv1",
                capability_key="k",
                status="insufficient",
                positive=3,
                negative=0,
                quote_ids=(),
            )
            is None
        )

    def test_contested_is_its_own_kind_not_weak_criticism(self):
        """Engineers disagreeing is a finding a reader can act on. Collapsing it
        into criticism publishes one side of a disagreement as the answer."""
        label = Label.from_cell(
            model_version_id="mv1",
            capability_key="k",
            status="contested",
            positive=3,
            negative=3,
            quote_ids=("q1",),
        )
        assert label is not None
        assert label.kind is LabelKind.CONTESTED

    def test_equal_counts_under_published_do_not_invent_a_tiebreak(self):
        label = Label.from_cell(
            model_version_id="mv1",
            capability_key="k",
            status="published",
            positive=2,
            negative=2,
            quote_ids=("q1",),
        )
        assert label is not None
        assert label.kind is LabelKind.CONTESTED, "a coin flip reached a page"


class TestTheIdIsDerived:
    def test_the_same_finding_is_the_same_label_across_runs(self):
        """A clock-based id would make every night's labels new, and every
        changelog entry would read `gained` forever."""
        assert label_id_for("mv1", "k", "praised-for") == label_id_for("mv1", "k", "praised-for")

    def test_a_different_kind_is_a_different_label(self):
        """Praise turning into criticism is a loss and a gain, not an edit."""
        assert label_id_for("mv1", "k", "praised-for") != label_id_for("mv1", "k", "criticised-for")


class TestTheDriverIsNeverGuessed:
    """The whole reason the changelog page separates them.

    A label lost because we moved a threshold is not a fact about the model,
    and a cell that stopped publishing looks identical either way.
    """

    def test_diff_requires_a_driver(self):
        """No default. `new-evidence` as a default would silently attribute
        every threshold edit to the world, in the direction that flatters us."""
        with pytest.raises(TypeError):
            diff(before={}, after={})  # type: ignore[call-arg]

    def test_the_driver_reaches_every_change(self):
        label = a_label()
        changes = diff(before={}, after={label.label_id: label}, driver=Driver.CONFIG_CHANGE)

        assert len(changes) == 1
        assert changes[0].driver is Driver.CONFIG_CHANGE

    def test_a_config_change_loss_carries_no_quotes(self):
        """Nobody said anything. Attaching the old quotes would present our
        threshold edit as evidence somebody produced."""
        label = a_label()
        lost = diff(before={label.label_id: label}, after={}, driver=Driver.CONFIG_CHANGE)[0]
        assert lost.quote_ids == ()

    def test_a_new_evidence_loss_keeps_the_quotes_that_used_to_earn_it(self):
        """So the changelog can say whether the evidence was contradicted or
        merely aged."""
        label = a_label()
        lost = diff(before={label.label_id: label}, after={}, driver=Driver.NEW_EVIDENCE)[0]
        assert lost.quote_ids == ("q1", "q2")


class TestWhatCountsAsAChange:
    def test_a_label_in_both_runs_is_not_a_change(self):
        """The changelog records what the board SAYS, not every recomputation
        behind it. An entry per nightly re-derivation buries the real ones."""
        label = a_label()
        assert (
            diff(
                before={label.label_id: label},
                after={label.label_id: label},
                driver=Driver.NEW_EVIDENCE,
            )
            == []
        )

    def test_gained_and_lost_are_both_produced(self):
        old, new = a_label("cap.a"), a_label("cap.b")
        changes = diff(
            before={old.label_id: old},
            after={new.label_id: new},
            driver=Driver.NEW_EVIDENCE,
        )
        assert {c.direction for c in changes} == {"gained", "lost"}

    def test_a_change_id_is_derived_not_clocked(self):
        change = Change(label=a_label(), direction="gained", driver=Driver.NEW_EVIDENCE)
        assert (
            change.change_id
            == Change(label=a_label(), direction="gained", driver=Driver.NEW_EVIDENCE).change_id
        )


class TestTheStore:
    def test_writing_a_label_preserves_first_seen_and_moves_last_confirmed(self):
        """Different questions - how long has the board said this, and is it
        still saying it - and one column cannot answer both."""
        conn = Conn()
        LabelStore(conn).write(a_label())

        sql = conn.sql[0]
        assert "ON CONFLICT" in sql
        assert "first_seen_at" not in sql.split("DO UPDATE SET")[1]
        assert "last_confirmed_at" in sql.split("DO UPDATE SET")[1]

    def test_a_lost_label_is_deleted_while_its_change_row_remains(self):
        """The board no longer says it; the changelog says it used to."""
        conn = Conn()
        store = LabelStore(conn)
        store.record(Change(label=a_label(), direction="lost", driver=Driver.NEW_EVIDENCE))
        store.drop(a_label().label_id)

        assert "INSERT INTO label_change" in conn.sql[0]
        assert conn.sql[1].strip().upper().startswith("DELETE FROM LABEL WHERE")

    def test_recording_the_same_change_twice_writes_one_row(self):
        conn = Conn()
        LabelStore(conn).record(
            Change(label=a_label(), direction="gained", driver=Driver.NEW_EVIDENCE)
        )
        assert "ON CONFLICT" in conn.sql[0]

    def test_the_store_never_commits(self):
        """The caller owns the transaction, so a label and its change row land
        together or not at all.

        Asserted on the CALL rather than the word. The first version checked
        `"commit" not in source` and failed on the class's own docstring saying
        it never commits - the same substring-catching-prose mistake as the
        coverage page's ban on "complete" firing on "completeness".
        """
        import inspect

        conn = Conn()
        store = LabelStore(conn)
        store.write(a_label())
        store.record(Change(label=a_label(), direction="gained", driver=Driver.NEW_EVIDENCE))

        assert not hasattr(conn, "committed"), "the store committed"
        source = inspect.getsource(LabelStore)
        assert ".commit()" not in source, "the caller owns the transaction"
