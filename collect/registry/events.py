"""What changed in the registry, and the rows that record it.

FR-3 says a price change is caught within 24 hours. Until now nothing on the
polled path could catch one: `_record_event` and `_record_prices` were called
from `load_seed()` only — the 11-model seed path — while `write_model_versions`,
which is what actually populates the 340-model registry, upserted and emitted
nothing. `model_event` held 0 rows against 340 models. The registry could change
silently, which is the one thing the registry exists not to do.

ONE DEFINITION OF "THE PRICE MOVED"
-----------------------------------
`observe_prices` is that definition and it is pure: previous observation in,
verdict out. Both writers call it — the seed loader one model at a time, the
poller three hundred and forty at a time — so there is no second opinion to
drift from the first.

    no incoming prices       nothing. Three NULLs assert nothing, and an
                             open-weight model priced by its host would
                             otherwise accumulate one empty row per night.
    no previous observation  APPEND, and do NOT call it a move. This is the
                             defect the seed path already paid for once: a
                             model whose history row was missing reported a
                             price change for a price that had never moved.
                             A backfill is not a movement (rule 6 — an absent
                             prior observation is not evidence of change).
    previous, equal          nothing.
    previous, different      APPEND and emit. This is the only case that is
                             a price change.

The seed loader used to reach a second answer by way of `_changed_fields` on
`model_version` and AND it with this one. It no longer does. Where the two
could disagree — the registry row unchanged tonight but our last *observation*
different — the observation wins, because "changed since we last looked" is
what a poll can honestly detect and what FR-3's 24 hours is measured against.

EVENT IDS ARE NOT DETERMINISTIC, AND THAT IS THE RULING
-------------------------------------------------------
An event is an occurrence, not a fact. Two identical transitions on different
days are two occurrences, and a deterministic id collapses the second into the
first — which is how `model_event` missed every price move after the first one
while `pricing_history` recorded them all. Idempotency lives in the CONDITION
above, which is a comparison against stored state and is directly testable.

BATCHED, BECAUSE THIS RUNS AT 340 A NIGHT
------------------------------------------
The per-model shape `load.py` uses is two round trips per model. At 340 models
and the 130ms measured against the remote instance that is 88 seconds of pure
latency, which is the hazard #45's writer audit named for this exact table on
the day something started recording prices for the polled registry. So the
poller path reads every prior observation in one query and writes history and
events with `executemany`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

#: The three columns a price observation is made of. `batch_discount` is not
#: one: it is a ratio derived from a sibling entry, not an observed price.
PRICE_COLUMNS: tuple[str, ...] = ("price_in", "price_out", "price_cached_read")

NEW_MODEL = "new-model"
PRICE_CHANGE = "price-change"


def new_event_id() -> str:
    """A name for one occurrence. See the module docstring for why it is random."""
    return f"ev_{uuid4().hex[:16]}"


#: `pricing_history.price_in` is `numeric(12,6)`, so six decimal places is all
#: the database can hold. Comparing at any finer precision compares a number
#: with a rounded copy of itself.
PRICE_SCALE = "0.000001"


def _comparable(value: Any) -> Any:
    """A price at the precision the column stores it in.

    Prices arrive as float from the feed and Decimal from the database, and the
    float has been through a multiplication: `_per_million` turns a per-token
    price into a per-million one, and `4.5e-07 * 1_000_000` is
    `0.44999999999999996`. Postgres stores `0.450000`. Compared verbatim, that
    model reports a price change EVERY NIGHT, forever, on arithmetic rather than
    on a price — an alert firing on our own rounding, which is the tenth
    instance of the defect class this producer exists to detect.

    Measured on the captured feed slice: `qwen/qwen3.8-27b`, all three columns.
    """
    if value is None:
        return None
    from decimal import Decimal

    return Decimal(str(value)).quantize(Decimal(PRICE_SCALE))


@dataclass(frozen=True)
class PriceObservation:
    """Tonight's prices for one model, against the last ones we recorded."""

    incoming: dict[str, Any]
    previous: dict[str, Any] | None
    changed: tuple[str, ...]

    @property
    def has_prices(self) -> bool:
        return any(self.incoming.get(column) is not None for column in PRICE_COLUMNS)

    @property
    def append(self) -> bool:
        """Should a `pricing_history` row be written?"""
        if not self.has_prices:
            return False
        return self.previous is None or bool(self.changed)

    @property
    def withdrawn(self) -> bool:
        """We had a price and the feed has stopped publishing one.

        NOT a price change and NOT a price of zero — the price became UNKNOWN,
        which is rule 6's case exactly. No all-NULL history row is written (three
        NULLs assert nothing) and no event is emitted, because an event with no
        observation to point at has no `occurred_at` that means anything.

        It is still information, so it is COUNTED and returned to the caller
        rather than dropped: `prices_withdrawn` in the poller's result. A
        coverage kind would be the better home, and `coverage_gap`'s CHECK is
        closed and shared, so that is a proposal rather than a change.
        """
        return self.previous is not None and not self.has_prices

    @property
    def moved(self) -> bool:
        """Should a `price-change` event be emitted?

        Requires an observation to have been written: an event points at the
        `pricing_history` row that revealed it, so a move with nothing to point
        at is not one this table can honestly record.

        A first observation is not a movement either, however different it looks
        from the nothing that preceded it.
        """
        return self.append and self.previous is not None and bool(self.changed)


def observe_prices(previous: dict[str, Any] | None, incoming: dict[str, Any]) -> PriceObservation:
    """The one definition. Pure — no connection, no clock, no side effect."""
    if previous is None:
        return PriceObservation(incoming=incoming, previous=None, changed=())
    changed = tuple(
        column
        for column in PRICE_COLUMNS
        if _comparable(previous.get(column)) != _comparable(incoming.get(column))
    )
    return PriceObservation(incoming=incoming, previous=previous, changed=changed)


# ── the batched read and the batched writes ───────────────────────────────


def latest_prices(conn, model_version_ids) -> dict[str, dict[str, Any]]:
    """The most recent observation per model, for a whole batch, in one query.

    A model with no history is ABSENT from the result rather than present with
    NULLs — the two mean different things here, and `observe_prices` reads the
    difference as "first observation" versus "priced at nothing".
    """
    ids = list(model_version_ids)
    if not ids:
        return {}
    rows = conn.execute(
        """
        SELECT DISTINCT ON (model_version_id)
               model_version_id, price_in, price_out, price_cached_read
        FROM pricing_history
        WHERE model_version_id = ANY(%s)
        ORDER BY model_version_id, observed_at DESC
        """,
        (ids,),
    ).fetchall()
    return {
        row[0]: dict(zip(PRICE_COLUMNS, row[1:], strict=True))
        for row in rows
    }


def append_prices(conn, rows, *, batch: int = 200) -> dict[str, datetime]:
    """Write `pricing_history` rows and return each one's `observed_at`.

    The timestamp is the event's `occurred_at`: an event points at the
    observation that revealed it rather than at the moment this code ran.

    `RETURNING` per row survives the batching, the same way the poller's
    `(xmax = 0)` does — see `write_model_versions`.
    """
    rows = list(rows)
    written: dict[str, datetime] = {}
    if not rows:
        return written

    statement = (
        "INSERT INTO pricing_history (model_version_id, price_in, price_out, "
        "price_cached_read, observed_at) VALUES (%(model_version_id)s, "
        "%(price_in)s, %(price_out)s, %(price_cached_read)s, clock_timestamp()) "
        "RETURNING model_version_id, observed_at"
    )
    with conn.cursor() as cur:
        for start in range(0, len(rows), batch):
            cur.executemany(statement, rows[start:start + batch], returning=True)
            while True:
                record = cur.fetchone() if cur.pgresult is not None else None
                if record is not None:
                    written[record[0]] = record[1]
                if not cur.nextset():
                    break
    return written


def write_events(conn, events, *, batch: int = 200) -> int:
    """Append `model_event` rows. Ids are per-occurrence: see the docstring."""
    from psycopg.types.json import Json

    rows = [
        {
            "id": new_event_id(),
            "model_version_id": event["model_version_id"],
            "type": event["type"],
            "occurred_at": event.get("occurred_at"),
            "payload": Json(event.get("payload") or {}),
        }
        for event in events
    ]
    if not rows:
        return 0

    statement = (
        "INSERT INTO model_event (id, model_version_id, type, occurred_at, payload) "
        "VALUES (%(id)s, %(model_version_id)s, %(type)s, %(occurred_at)s, %(payload)s)"
    )
    written = 0
    with conn.cursor() as cur:
        for start in range(0, len(rows), batch):
            chunk = rows[start:start + batch]
            cur.executemany(statement, chunk)
            written += len(chunk)
    return written
