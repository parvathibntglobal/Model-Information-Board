"""Labels, and the changelog entry every change to one has to produce.

FR-27. `judge/pages/changelog.py` reads `label_change` and NOTHING WROTE IT -
the page would have reported "no labels changed" forever, honestly and
uselessly, which is the coverage_gap shape in my own lane. This is the writer.

A LABEL IS A CELL'S STATUS, MADE DURABLE

Cells are recomputed nightly and hold only the present. A label is the same
finding with a history: when it appeared, when it was last confirmed, and what
quotes earned it. The changelog is the difference between two nights, and it
cannot be derived after the fact - once tonight's cells overwrite last
night's, the transition is gone. So it is computed AT WRITE TIME or not at all.

THE DRIVER IS DECIDED HERE, AND IT IS THE PART THAT MATTERS

`label_change.driver` is a closed set, and `config-change` is the one the
changelog page exists to keep separate: a label lost because we moved a
threshold is not a fact about the model. Nothing downstream can recover which
happened, because a cell that stopped publishing looks identical either way.

So the driver is passed IN by whoever ran the pipeline, defaulting to nothing
rather than to `new-evidence`. Defaulting to `new-evidence` would silently
attribute every threshold edit to the world, in the direction that flatters
us - the same conversion rule 6 refuses everywhere else.

STATE IS NOT STATUS

`cell.status` is what the evidence supports now. `label.state` is how settled
it is: `provisional` on first publication, `established` once it has survived
a re-run. A label that appears and vanishes nightly is a different object from
one that has held for a month, and a page showing only the current status
cannot tell them apart.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class LabelKind(StrEnum):
    PRAISED_FOR = "praised-for"
    CRITICISED_FOR = "criticised-for"
    CONTESTED = "contested"


class LabelState(StrEnum):
    PENDING = "pending"
    PROVISIONAL = "provisional"
    ESTABLISHED = "established"


class Driver(StrEnum):
    """Why a label changed. `label_change.driver`'s CHECK set."""

    NEW_EVIDENCE = "new-evidence"
    PRICE_CHANGE = "price-change"
    VERSION_CHANGE = "version-change"
    CONFIG_CHANGE = "config-change"


def label_id_for(model_version_id: str, capability_key: str, kind: str) -> str:
    """Derived, so the same finding is the same label across runs.

    A clock-based id would make every night's labels new ones, and every
    changelog entry would read `gained` forever.
    """
    digest = hashlib.sha256(
        "\x1f".join((model_version_id, capability_key, kind)).encode("utf-8")
    ).hexdigest()[:24]
    return f"lbl_{digest}"


@dataclass(frozen=True)
class Label:
    """One durable finding about one model."""

    label_id: str
    model_version_id: str
    capability_key: str
    kind: LabelKind
    state: LabelState
    earned_by_quote_ids: tuple[str, ...]

    @classmethod
    def from_cell(
        cls,
        *,
        model_version_id: str,
        capability_key: str,
        status: str,
        positive: int,
        negative: int,
        quote_ids: tuple[str, ...],
        state: LabelState = LabelState.PROVISIONAL,
    ) -> Label | None:
        """The label a published cell earns, or None if it earns none.

        `contested` is its own kind rather than a weaker `criticised-for`.
        Engineers disagreeing is a finding a reader can act on - usually by
        looking at the conditions - and collapsing it into criticism would
        publish one side of a disagreement as the answer.
        """
        if status == "contested":
            kind = LabelKind.CONTESTED
        elif status != "published":
            return None
        elif negative > positive:
            kind = LabelKind.CRITICISED_FOR
        elif positive > negative:
            kind = LabelKind.PRAISED_FOR
        else:
            # Equal counts under a published status. Not praise and not
            # criticism, and inventing a tiebreak here would put a coin flip
            # on a page.
            kind = LabelKind.CONTESTED

        return cls(
            label_id=label_id_for(model_version_id, capability_key, kind),
            model_version_id=model_version_id,
            capability_key=capability_key,
            kind=kind,
            state=state,
            earned_by_quote_ids=quote_ids,
        )


@dataclass(frozen=True)
class Change:
    """One transition, ready to be written."""

    label: Label
    direction: str  # gained | lost
    driver: Driver
    quote_ids: tuple[str, ...] = ()

    @property
    def change_id(self) -> str:
        stamp = "gained" if self.direction == "gained" else "lost"
        digest = hashlib.sha256(
            f"{self.label.label_id}\x1f{stamp}\x1f{self.driver}".encode()
        ).hexdigest()[:16]
        return f"lch_{digest}"


def diff(*, before: dict[str, Label], after: dict[str, Label], driver: Driver) -> list[Change]:
    """What changed between two runs, keyed by label id.

    THE DRIVER IS REQUIRED, with no default. A default of `new-evidence` would
    quietly attribute a threshold edit to the world, and nothing downstream
    could recover the difference - a cell that stopped publishing looks the
    same whichever caused it.

    A label present in both is NOT a change, even if its quotes moved. The
    changelog records what the board SAYS, not every recomputation behind it;
    an entry per nightly re-derivation would bury the four real transitions in
    a list nobody reads.
    """
    changes: list[Change] = []
    for label_id, label in sorted(after.items()):
        if label_id not in before:
            changes.append(
                Change(
                    label=label,
                    direction="gained",
                    driver=driver,
                    quote_ids=label.earned_by_quote_ids,
                )
            )
    for label_id, label in sorted(before.items()):
        if label_id not in after:
            # A loss carries the quotes that USED to earn it, so the changelog
            # can say whether the evidence was contradicted or merely aged.
            changes.append(
                Change(
                    label=label,
                    direction="lost",
                    driver=driver,
                    quote_ids=label.earned_by_quote_ids if driver is Driver.NEW_EVIDENCE else (),
                )
            )
    return changes


class LabelStore:
    """Writes `label` and `label_change`. Never commits - the caller owns that."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def current(self) -> dict[str, Label]:
        rows = self._conn.execute(
            "SELECT id, model_version_id, capability_key, kind, state, "
            "earned_by_quote_ids FROM label"
        ).fetchall()
        return {
            r[0]: Label(
                label_id=r[0],
                model_version_id=r[1],
                capability_key=r[2],
                kind=LabelKind(r[3]),
                state=LabelState(r[4]),
                earned_by_quote_ids=tuple(r[5] or ()),
            )
            for r in rows
        }

    def write(self, label: Label, *, now: datetime | None = None) -> None:
        """Upsert. `first_seen_at` survives, `last_confirmed_at` moves.

        Those are different questions - "how long has the board said this" and
        "is it still saying it" - and one column cannot answer both.
        """
        stamp = now or datetime.now(UTC)
        self._conn.execute(
            """
            INSERT INTO label (id, model_version_id, capability_key, kind, state,
                               earned_by_quote_ids, first_seen_at, last_confirmed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                state               = EXCLUDED.state,
                earned_by_quote_ids = EXCLUDED.earned_by_quote_ids,
                last_confirmed_at   = EXCLUDED.last_confirmed_at
            """,
            (
                label.label_id,
                label.model_version_id,
                label.capability_key,
                str(label.kind),
                str(label.state),
                list(label.earned_by_quote_ids),
                stamp,
                stamp,
            ),
        )

    def record(self, change: Change) -> None:
        self._conn.execute(
            """
            INSERT INTO label_change (id, label_id, direction, driver, quote_ids)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                change.change_id,
                change.label.label_id,
                change.direction,
                str(change.driver),
                list(change.quote_ids),
            ),
        )

    def drop(self, label_id: str) -> None:
        """A lost label leaves the table; its `label_change` row is the record.

        Deleting the label and keeping the change is the point: the board no
        longer says it, and the changelog says it used to.
        """
        self._conn.execute("DELETE FROM label WHERE id = %s", (label_id,))
