"""What happens after the cells are written, and cannot happen later.

`Pipeline.run_all` stops at cells. Everything downstream of them - labels, the
changelog, reported context limits - had a module and no caller, which is the
eleventh and twelfth instance of that shape on this project and both mine. A
writer class is not a writer. This is the caller.

THE DIFF IS WHY THIS IS A STAGE RATHER THAN A QUERY

Cells hold only the present and are overwritten every run. A label gained or
lost is the difference between two runs, so **once tonight's cells overwrite
last night's, the transition is gone**. It cannot be recovered afterwards by
any query, however clever, because the thing it would compare against no
longer exists.

That is the whole reason this runs inside the batch and in this order:

    read the labels the board currently carries   <- BEFORE anything is written
    derive the labels tonight's cells earn
    diff
    write the changes, then the labels

Reading current labels after writing new ones would diff a set against itself
and report that nothing ever changes. The order is load-bearing and a
comfortable-looking refactor would swap it.

THE DRIVER CANNOT BE INFERRED, SO IT IS AN ARGUMENT

A cell that stopped publishing looks identical whether people stopped saying
it, a price moved, the model changed, or **we edited a threshold**. Only the
caller knows which. There is no default: `new-evidence` as a fallback would
silently attribute every configuration change we make to the world, in the
direction that flatters us.

REPORTED CONTEXT IS DERIVED HERE TOO, and it is the one figure that removes
candidates without a reader seeing it happen. It is derived from claims rather
than from cells, so it does not depend on the gate - a limit three people
report is a limit whether or not the capability cell publishes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from judge.curate.labels import Change, Driver, Label, LabelStore, diff
from judge.curate.reported_context import ReportedContextStore

log = logging.getLogger(__name__)


@dataclass
class NightlyResult:
    """What the closing stage did, in numbers a caller can log or refuse on."""

    labels_before: int = 0
    labels_after: int = 0
    changes: list[Change] = field(default_factory=list)
    context_rows_written: int = 0
    context_rows_skipped: int = 0

    @property
    def gained(self) -> list[Change]:
        return [c for c in self.changes if c.direction == "gained"]

    @property
    def lost(self) -> list[Change]:
        return [c for c in self.changes if c.direction == "lost"]

    def summary(self) -> str:
        """Rule 7: the counts carry what they were drawn from."""
        body = (
            f"{len(self.gained)} labels gained, {len(self.lost)} lost, "
            f"{self.labels_after} standing (was {self.labels_before})."
        )
        if self.context_rows_written or self.context_rows_skipped:
            body += (
                f" {self.context_rows_written} reported-context rows written, "
                f"{self.context_rows_skipped} models had no corroborated limit "
                f"and were left unset rather than set to no-limit."
            )
        return body


def close_the_night(
    conn: Any,
    *,
    driver: Driver,
    as_of_cells: list[Any] | None = None,
) -> NightlyResult:
    """Derive labels and context limits from the cells just written.

    `driver` has no default on purpose - see the module docstring.

    `as_of_cells` lets a caller pass the outcomes it just computed rather than
    re-reading them. Omitted, the cells are read back from the table, which is
    the same answer by a slower route and the right default for a caller that
    did not compute them.
    """
    labels = LabelStore(conn)
    result = NightlyResult()

    # BEFORE anything is written. Reading this after would diff a set against
    # itself and report that the board never changes its mind.
    before = labels.current()
    result.labels_before = len(before)

    rows = (
        [
            (
                c.key.model_version_id,
                c.key.capability_key,
                c.status,
                c.counts.positive,
                c.counts.negative,
                tuple(c.counts.quote_ids),
            )
            for c in as_of_cells
        ]
        if as_of_cells is not None
        else [
            (r[0], r[1], r[2], r[3], r[4], tuple(r[5] or ()))
            for r in conn.execute(
                "SELECT model_version_id, capability_key, status, positive, "
                "negative, quote_ids FROM cell"
            ).fetchall()
        ]
    )

    after: dict[str, Label] = {}
    for model_version_id, capability_key, status, positive, negative, quote_ids in rows:
        label = Label.from_cell(
            model_version_id=model_version_id,
            capability_key=capability_key,
            status=status,
            positive=positive,
            negative=negative,
            quote_ids=quote_ids,
        )
        if label is not None:
            after[label.label_id] = label
    result.labels_after = len(after)

    result.changes = diff(before=before, after=after, driver=driver)
    for change in result.changes:
        labels.record(change)
    for label in after.values():
        labels.write(label)
    # A lost label leaves the table; its `label_change` row is what says the
    # board used to carry it. Dropped after the change is recorded, so a
    # failure between the two cannot lose the record of the loss.
    for label_id in set(before) - set(after):
        labels.drop(label_id)

    # ── reported context ──────────────────────────────────────────────────
    #
    # From CLAIMS rather than cells: a limit three people report is a limit
    # whether or not the capability cell publishes, and gating it behind the
    # cell would make a hard filter depend on a threshold it has nothing to do
    # with.
    context = ReportedContextStore(conn)
    for model_version_id in sorted({r[0] for r in rows}):
        derived = context.derive(model_version_id)
        if derived.is_corroborated:
            context.write(derived)
            result.context_rows_written += 1
        else:
            # LEFT UNSET, never written as "no limit". An uncorroborated limit
            # written as a row is a threshold nobody reported, and this is the
            # column that removes candidates silently.
            result.context_rows_skipped += 1

    log.info("nightly close: %s", result.summary())
    return result
