"""The changelog: every label gained or lost, and what drove it.

FR-27. A board that changes its answers without explaining why does not get
trusted twice, and this is the page that makes a change auditable rather than
mysterious.

THE DRIVER IS THE POINT, NOT THE CHANGE

`label_change.driver` is a closed set of four, and they are not
interchangeable:

    new-evidence     people said something. The board learned.
    price-change     nobody said anything. The MONEY moved.
    version-change   the model changed under a stable name.
    config-change    WE changed - a threshold, a weight, a rule.

The last is the one this page exists for. A label lost to `config-change` is
not a fact about the model at all; it is a fact about us, and a reader who
cannot tell it from `new-evidence` will attribute our threshold edit to their
model's behaviour. Opposite conclusions from the same words on the page.

So changes are GROUPED BY DRIVER rather than listed by time alone. A
chronological list is how `config-change` hides among real findings.

A LOSS IS NOT A CRITICISM

A label lost because evidence decayed below the gate is not the same as one
lost because engineers started reporting failures, and both render as "lost".
`quote_ids` is what separates them: a loss with quotes behind it has evidence,
a loss with none is arithmetic - recency weighting doing its job. Rule 4's
shape, on a transition rather than on a state.

RULE 7

"14 changes this week" is not a claim without the population. Fourteen out of
how many labels, over what window, at which pipeline version - a board with
forty labels and one with four hundred are different stories behind the same
number.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

#: `label_change.driver`'s CHECK set, and what each means for a reader.
#:
#: The second half is what makes the page a report rather than a log. Two of
#: these are facts about the world, one is a fact about a provider, and one is
#: a fact about US - and the last is the one most likely to be misread.
DRIVERS: dict[str, str] = {
    "new-evidence": "engineers reported something new",
    "price-change": "the price moved; nobody said anything about the model",
    "version-change": "the model changed behind a stable name",
    "config-change": "we changed a threshold or a rule; the model did not change",
}

#: Drivers that are facts about OUR configuration rather than about the model.
#: Called out separately because a reader cannot otherwise tell them apart.
OURS = frozenset({"config-change"})


@dataclass(frozen=True)
class LabelChange:
    """One label gained or lost."""

    change_id: str
    label_id: str
    direction: str
    driver: str
    quote_ids: tuple[str, ...] = ()
    occurred_at: datetime | None = None

    @property
    def is_about_us(self) -> bool:
        return self.driver in OURS

    @property
    def recognised(self) -> bool:
        """A driver this page has never heard of.

        Surfaced rather than dropped, as the coverage page does with an
        unknown gap kind. A change nobody can explain is worse on this page
        than anywhere else, because this page IS the explanation.
        """
        return self.driver in DRIVERS

    @property
    def evidenced(self) -> bool:
        """Whether quotes stand behind this change.

        A loss with no quotes is arithmetic - recency weighting dropping a cell
        below the gate - and a loss with quotes is people reporting failures.
        Both read as "lost" and they mean different things.
        """
        return bool(self.quote_ids)

    @property
    def headline(self) -> str:
        verb = "gained" if self.direction == "gained" else "lost"
        why = DRIVERS.get(self.driver, f"an unrecognised driver: {self.driver}")
        line = f"{verb} — {why}"
        if self.is_about_us:
            line += ". This is a change in our configuration, not in the model."
        elif verb == "lost" and not self.evidenced:
            line += (
                ". No new criticism: the evidence aged below the publication "
                "bar rather than being contradicted."
            )
        return line


@dataclass(frozen=True)
class Changelog:
    """What changed, grouped so a configuration edit cannot hide in the list."""

    changes: tuple[LabelChange, ...] = ()
    total_labels: int | None = None
    window_days: int | None = None

    @property
    def about_us(self) -> tuple[LabelChange, ...]:
        return tuple(c for c in self.changes if c.is_about_us)

    @property
    def unrecognised(self) -> tuple[LabelChange, ...]:
        return tuple(c for c in self.changes if not c.recognised)

    def by_driver(self) -> dict[str, tuple[LabelChange, ...]]:
        """Grouped rather than chronological.

        A time-ordered list is exactly how a `config-change` sits between two
        `new-evidence` rows and reads as one of them.
        """
        out: dict[str, list[LabelChange]] = {}
        for change in self.changes:
            out.setdefault(change.driver, []).append(change)
        return {k: tuple(v) for k, v in sorted(out.items())}

    @property
    def summary(self) -> str:
        n = len(self.changes)
        if not n:
            if self.total_labels is None:
                return (
                    "No changes recorded, and the number of labels was not "
                    "counted - so this is not yet a statement about stability."
                )
            return (
                f"No labels changed across {self.total_labels} tracked. The "
                f"board said the same thing this run as last."
            )

        parts = [f"{n} label {'change' if n == 1 else 'changes'}"]
        if self.total_labels is not None:
            parts.append(f"across {self.total_labels} tracked labels")
        if self.window_days is not None:
            parts.append(f"in {self.window_days} days")
        body = " ".join(parts) + "."

        ours = len(self.about_us)
        if ours:
            body += (
                f" {ours} of {n} came from a change we made rather than anything anyone reported."
            )
        if self.unrecognised:
            drivers = ", ".join(sorted({c.driver for c in self.unrecognised}))
            body += (
                f" {len(self.unrecognised)} carry a driver this page does not recognise: {drivers}."
            )
        return body


class ChangelogReader:
    """Reads `label_change`. Writes nothing."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def recent(self, *, days: int = 30, limit: int = 200) -> Changelog:
        rows = self._conn.execute(
            """
            SELECT id, label_id, direction, driver, quote_ids, occurred_at
            FROM label_change
            WHERE occurred_at > now() - make_interval(days => %s)
            ORDER BY occurred_at DESC
            LIMIT %s
            """,
            (days, limit),
        ).fetchall()

        total = self._conn.execute("SELECT count(*) FROM label").fetchone()

        return Changelog(
            changes=tuple(
                LabelChange(
                    change_id=r[0],
                    label_id=r[1],
                    direction=r[2],
                    driver=r[3],
                    quote_ids=tuple(r[4] or ()),
                    occurred_at=r[5],
                )
                for r in rows
            ),
            total_labels=total[0] if total else None,
            window_days=days,
        )
