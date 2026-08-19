"""FR-3's producer on the polled path, against a real Postgres.

`model_event` held 0 rows against 340 polled models, because `_record_event` and
`_record_prices` were called from `load_seed()` only — the 11-model seed path.
The poller wrote prices nightly and nothing recorded that they moved, so FR-3's
acceptance had nothing to fire on and the registry could change silently.

THE TEST THAT MATTERS MOST IS THE ONE ABOUT NOT FIRING. A producer that emits a
price-change on a first observation would fire 340 times on its first night
against the current registry — 340 models, zero history rows — and every one of
them would be wrong in the way that is expensive: a real alert, on a real model,
for a price that never moved.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from collect.registry.events import observe_prices
from collect.registry.openrouter import parse_models, write_model_versions
from tests.conftest import assert_disposable, assert_safe_target

RETRIEVED = datetime(2026, 8, 18, 3, 0, tzinfo=UTC)


@pytest.fixture
def conn(test_dsn):
    """A schema-fresh connection to a database proven safe to destroy."""
    from collect.db import apply_schema, connect

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture
def feed():
    payload = json.loads(
        Path("fixtures/openrouter/models-slice.json").read_text(encoding="utf-8")
    )
    return parse_models(payload, retrieved_at=RETRIEVED)


def _scalar(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def _counts(conn):
    return {
        "models": _scalar(conn, "SELECT count(*) FROM model_version"),
        "history": _scalar(conn, "SELECT count(*) FROM pricing_history"),
        "new_model": _scalar(conn, "SELECT count(*) FROM model_event WHERE type='new-model'"),
        "price_change": _scalar(
            conn, "SELECT count(*) FROM model_event WHERE type='price-change'"
        ),
    }


# ── night one, and the two shapes it can take ─────────────────────────────


def test_a_first_poll_records_every_model_and_no_price_change(conn, feed):
    """340 new models on night one is 340 new-model events and zero movements.

    Recorded per model rather than collapsed into one bulk event: `occurred_at`
    is the release date and differs per model, and FR-3's alert is per model.
    Collapsing them would trade information a query can filter for noise a
    display can group.
    """
    result = write_model_versions(conn, feed)
    conn.commit()

    counts = _counts(conn)
    assert counts["models"] == len(feed.models)
    assert counts["new_model"] == len(feed.models)
    assert counts["price_change"] == 0, "a first observation is a baseline"
    assert result["inserted"] == len(feed.models)
    assert result["updated"] == 0
    assert result["price_changes"] == 0


def test_a_registry_with_rows_and_no_history_fires_nothing(conn, feed):
    """TONIGHT'S ACTUAL STATE: 340 polled rows, 0 pricing_history rows.

    The models already exist, so nothing is an insert, and every one of them is
    being priced for the first time. A producer that read "wrote a history row"
    as "the price moved" would fire on all of them. A backfill is not a
    movement — the same defect the seed path paid for once, arriving by the
    other door.
    """
    write_model_versions(conn, feed, record_changes=False)
    conn.commit()
    assert _counts(conn)["history"] == 0

    result = write_model_versions(conn, feed)
    conn.commit()

    counts = _counts(conn)
    assert result["updated"] == len(feed.models), "existing rows, so no inserts"
    assert counts["price_change"] == 0
    assert counts["new_model"] == 0
    assert counts["history"] > 0, "the baseline is still written"


# ── the second night, and the one after that ──────────────────────────────


def test_an_unchanged_second_poll_writes_nothing_new(conn, feed):
    """Idempotency lives in the CONDITION, which is why the ids can be random."""
    write_model_versions(conn, feed)
    conn.commit()
    before = _counts(conn)

    result = write_model_versions(conn, feed)
    conn.commit()

    assert _counts(conn) == before
    assert result["prices_recorded"] == 0
    assert result["events"] == 0
    assert result["price_changes"] == 0


def test_a_moved_price_is_recorded_with_what_it_moved_from(conn, feed):
    """FR-3 on the path that actually populates the registry."""
    write_model_versions(conn, feed)
    conn.commit()

    moved = feed.models[0]
    from dataclasses import replace

    dearer = replace(moved, price_in=(moved.price_in or 0) + 7.5)
    from collect.registry.openrouter import PollResult

    write_model_versions(conn, PollResult(RETRIEVED, 1, (dearer,), 0))
    conn.commit()

    assert _counts(conn)["price_change"] == 1
    payload = _scalar(
        conn, "SELECT payload FROM model_event WHERE type='price-change' LIMIT 1"
    )
    assert payload["canonical_id"] == moved.canonical_id
    assert payload["changed"] == ["price_in"]
    assert payload["from"]["price_in"] != payload["to"]["price_in"]
    assert Decimal(payload["to"]["price_in"]) > Decimal(payload["from"]["price_in"])


def test_the_event_points_at_the_observation_that_revealed_it(conn, feed):
    """`occurred_at` is the history row's timestamp, not when this code ran."""
    from dataclasses import replace

    from collect.registry.openrouter import PollResult

    write_model_versions(conn, feed)
    conn.commit()
    moved = replace(feed.models[0], price_in=(feed.models[0].price_in or 0) + 1)
    write_model_versions(conn, PollResult(RETRIEVED, 1, (moved,), 0))
    conn.commit()

    row = conn.execute(
        "SELECT e.occurred_at, h.observed_at FROM model_event e "
        "JOIN pricing_history h ON h.model_version_id = e.model_version_id "
        "WHERE e.type = 'price-change' ORDER BY h.observed_at DESC LIMIT 1"
    ).fetchone()
    assert row[0] == row[1]


def test_two_identical_moves_are_two_occurrences(conn, feed):
    """The ruling from #39: an event is an occurrence, not a fact.

    A deterministic id would collapse the second into the first, which is how
    `model_event` once missed every price move after the opening one while
    `pricing_history` recorded them all.
    """
    from dataclasses import replace

    from collect.registry.openrouter import PollResult

    base = feed.models[0]
    write_model_versions(conn, feed)
    for price in ((base.price_in or 0) + 1, base.price_in, (base.price_in or 0) + 1):
        write_model_versions(
            conn, PollResult(RETRIEVED, 1, (replace(base, price_in=price),), 0)
        )
    conn.commit()

    assert _counts(conn)["price_change"] == 3
    ids = [r[0] for r in conn.execute("SELECT id FROM model_event").fetchall()]
    assert len(ids) == len(set(ids))


# ── the properties the batching work bought, still standing ───────────────


def test_inserts_and_updates_stay_separable_after_batching(conn, feed):
    """`RETURNING id, (xmax = 0)` — and the id travels with the verdict.

    Attribution by position would put an event on the wrong model, which reads
    as a real price change on a real model rather than as a bug.
    """
    from collect.registry.openrouter import PollResult

    half = len(feed.models) // 2
    first = write_model_versions(conn, PollResult(RETRIEVED, half, feed.models[:half], 0))
    second = write_model_versions(conn, feed, batch=3)
    conn.commit()

    assert first["inserted"] == half and first["updated"] == 0
    assert second["inserted"] == len(feed.models) - half
    assert second["updated"] == half


def test_a_model_with_no_prices_gets_no_history_row(conn, feed):
    """Three NULLs assert nothing, and would otherwise accumulate one a night."""
    from dataclasses import replace

    from collect.registry.openrouter import PollResult

    priceless = replace(
        feed.models[0], price_in=None, price_out=None, price_cached_read=None
    )
    write_model_versions(conn, PollResult(RETRIEVED, 1, (priceless,), 0))
    conn.commit()

    assert _counts(conn)["history"] == 0
    assert _counts(conn)["new_model"] == 1


# ── the pure decision, without a database ─────────────────────────────────


@pytest.mark.parametrize(
    ("previous", "incoming", "append", "moved"),
    [
        (None, {"price_in": 1.0}, True, False),               # first observation
        ({"price_in": 1.0}, {"price_in": 1.0}, False, False),  # unchanged
        ({"price_in": 1.0}, {"price_in": 2.0}, True, True),    # moved
        (None, {"price_in": None}, False, False),              # nothing to record
        ({"price_in": 1.0}, {"price_in": None}, False, False),  # withdrawn: neither
    ],
)
def test_the_shared_definition_of_a_move(previous, incoming, append, moved):
    observation = observe_prices(previous, incoming)
    assert observation.append is append
    assert observation.moved is moved


def test_a_withdrawn_price_is_not_a_change_and_not_a_zero():
    """The feed stops publishing a price. It became UNKNOWN, which is rule 6.

    No all-NULL history row, no event — an event with no observation to point at
    has no `occurred_at` that means anything — and a count, so it is not lost
    between the two things it is not.
    """
    observation = observe_prices({"price_in": 1.0}, {"price_in": None})
    assert observation.withdrawn
    assert not observation.append and not observation.moved


def test_a_float_that_lost_precision_on_the_way_in_is_not_a_price_change():
    """`4.5e-07 * 1_000_000` is `0.44999999999999996`; Postgres stores `0.450000`.

    Compared verbatim, `qwen/qwen3.8-27b` reports a price change every night
    forever — an alert firing on our own arithmetic. Found by the unchanged
    second poll below, which is why that test exists.
    """
    from_db = {"price_in": Decimal("0.450000")}
    from_feed = {"price_in": 4.5e-07 * 1_000_000}
    assert from_feed["price_in"] != float(from_db["price_in"])
    assert not observe_prices(from_db, from_feed).moved


def test_float_and_decimal_are_the_same_price():
    """The feed gives floats; the database gives Decimals. One is not a move."""
    assert not observe_prices({"price_in": Decimal("0.30")}, {"price_in": 0.3}).moved
