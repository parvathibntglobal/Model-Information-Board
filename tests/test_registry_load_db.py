"""Registry load against a real Postgres.

Skipped unless TEST_DATABASE_URL is set. It is deliberately *not*
DATABASE_URL: these tests drop and recreate the public schema, and a helper
that can wipe a working database on a typo eventually will.

    $env:TEST_DATABASE_URL = "postgresql://localhost:5432/modelboard_test"
    py -3 -m pytest tests/test_registry_load_db.py -q
"""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
import yaml

from collect.config import SEED_MODELS_YAML
from collect.ids import model_alias_id
from collect.registry.aliases import AliasRow, intervals_overlap
from collect.registry.assertions import FixtureLeakError, assert_no_fixtures
from collect.registry.load import ProvenanceDowngradeError, _sync_alias, recompute_window
from collect.registry.seed import load_seed_file

#: Pinned so window verdicts do not drift with the calendar.
AS_OF = date(2026, 8, 12)

TEST_DSN = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DSN, reason="set TEST_DATABASE_URL to run registry database tests"
)


@pytest.fixture
def conn():
    from collect.db import apply_schema, connect

    connection = connect(TEST_DSN)
    try:
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _load(connection, **kwargs):
    """Load the seed with both known contract gaps waived.

    `strict_sources` and `strict_spelling` are off because the seed file
    ships with a documented FR-2 gap and a missing concatenated form for
    `deepseek-v4-flash`, both of which are sign-off items on a contract PR
    this lane must not write. The gaps are still recorded in the report.
    """
    from collect.registry.load import load_seed

    report = load_seed(connection, strict_sources=False, strict_spelling=False, **kwargs)
    connection.commit()
    return report


def _scalar(connection, sql, params=()):
    row = connection.execute(sql, params).fetchone()
    return row[0] if row else None


def test_schema_applies_and_seeds_ten_models(conn):
    report = _load(conn)
    assert report.models_inserted == 10
    assert _scalar(conn, "SELECT count(*) FROM model_version") == 10
    assert _scalar(conn, "SELECT count(*) FROM model_version WHERE provenance='seed'") == 10


def test_reloading_changes_nothing(conn):
    _load(conn)
    second = _load(conn)
    assert second.models_inserted == 0
    assert second.models_updated == 0
    assert second.models_unchanged == 10
    assert second.aliases_inserted == 0


def test_aliases_are_append_only(conn):
    """FR-4: a second load must not rewrite a single alias row."""
    _load(conn)
    before = conn.execute("SELECT id, model_version_id, created_at FROM model_alias").fetchall()
    _load(conn)
    after = conn.execute("SELECT id, model_version_id, created_at FROM model_alias").fetchall()
    assert sorted(before) == sorted(after)


# ── FR-4: one live alias per surface per model, across corrections ────────


def _live_duplicates(connection) -> list[tuple[str, str, int]]:
    """Surfaces claimed by more than one live row for the same model."""
    return connection.execute(
        "SELECT normalized, model_version_id, count(*) FROM model_alias "
        "WHERE valid_until IS NULL GROUP BY normalized, model_version_id HAVING count(*) > 1"
    ).fetchall()


def _bump_release_date(connection, canonical_id: str, new_date: date) -> None:
    connection.execute(
        "UPDATE model_version SET release_date = %s WHERE canonical_id = %s",
        (new_date, canonical_id),
    )
    connection.commit()


def test_no_duplicate_live_aliases_after_a_plain_reload(conn):
    _load(conn)
    _load(conn)
    assert _live_duplicates(conn) == []


def test_a_corrected_release_date_leaves_one_live_row_per_surface(conn):
    """THE ACCEPTANCE TEST.

    Load, change a release date, load again. Before the fix this minted a
    fresh id for every alias of that model, inserted them all, and left the
    old rows open, so two live rows shared a `normalized`.
    """
    _load(conn, as_of=AS_OF)
    live_before = _scalar(conn, "SELECT count(*) FROM model_alias WHERE valid_until IS NULL")

    _bump_release_date(conn, "anthropic/claude-opus-5", date(2026, 7, 1))
    _load(conn, as_of=AS_OF)

    assert _live_duplicates(conn) == []
    assert _scalar(conn, "SELECT count(*) FROM model_alias WHERE valid_until IS NULL") == (
        live_before
    )


def test_a_corrected_release_date_does_not_rewrite_alias_ids(conn):
    """A date correction is not a change to what the alias claims.

    The id keys on content, so the rows are untouched rather than rotated.
    """
    _load(conn, as_of=AS_OF)
    before = sorted(r[0] for r in conn.execute("SELECT id FROM model_alias").fetchall())
    _bump_release_date(conn, "anthropic/claude-opus-5", date(2026, 7, 1))
    _load(conn, as_of=AS_OF)
    after = sorted(r[0] for r in conn.execute("SELECT id FROM model_alias").fetchall())
    assert before == after


def test_a_changed_alias_closes_the_old_row_and_appends(conn):
    """A genuine content change: one live row, and the old one preserved."""
    _load(conn, as_of=AS_OF)
    row = conn.execute(
        "SELECT id, model_version_id, normalized, valid_from FROM model_alias "
        "WHERE normalized = 'opus' AND valid_until IS NULL"
    ).fetchone()
    assert row is not None
    old_id, mv_id, normalized, valid_from = row

    changed = AliasRow(
        id="",
        surface="opus",
        normalized=normalized,
        variants=["opus", "opus model"],  # content differs
        provider_hint="anthropic",
        model_version_id=mv_id,
        family="claude",
        specificity="family",
        valid_from=date(2026, 8, 1),
    )
    changed = replace(changed, id=model_alias_id(normalized, mv_id, changed.content_key()))
    assert changed.id != old_id

    assert _sync_alias(conn, changed) == "replaced"
    conn.commit()

    assert _live_duplicates(conn) == []
    closed = conn.execute(
        "SELECT valid_until FROM model_alias WHERE id = %s", (old_id,)
    ).fetchone()
    assert closed[0] == date(2026, 8, 1)  # closed exactly where the new one opens


def test_the_handover_is_half_open_so_it_is_not_a_collision(conn):
    """Task 5's interval rule is what makes Task 5 and Task 1 compatible.

    The old row closes on the same day the new one opens. Half-open windows
    mean that is a handover, not two rows claiming one surface at once.
    """
    _load(conn, as_of=AS_OF)
    row = conn.execute(
        "SELECT id, model_version_id, normalized FROM model_alias "
        "WHERE normalized = 'sonnet' AND valid_until IS NULL"
    ).fetchone()
    old_id, mv_id, normalized = row

    changed = AliasRow(
        id="",
        surface="sonnet",
        normalized=normalized,
        variants=["sonnet", "the sonnet one"],
        provider_hint="anthropic",
        model_version_id=mv_id,
        family="claude",
        specificity="family",
        valid_from=date(2026, 8, 1),
    )
    changed = replace(changed, id=model_alias_id(normalized, mv_id, changed.content_key()))
    _sync_alias(conn, changed)
    conn.commit()

    rows = conn.execute(
        "SELECT valid_from, valid_until FROM model_alias WHERE normalized = %s "
        "AND model_version_id = %s ORDER BY valid_from",
        (normalized, mv_id),
    ).fetchall()
    assert len(rows) == 2
    assert not intervals_overlap(rows[0][0], rows[0][1], rows[1][0], rows[1][1])


def test_a_backwards_date_correction_never_inverts_an_interval(conn):
    """valid_until can never land before valid_from."""
    _load(conn, as_of=AS_OF)
    row = conn.execute(
        "SELECT id, model_version_id, normalized, valid_from FROM model_alias "
        "WHERE normalized = 'haiku' AND valid_until IS NULL"
    ).fetchone()
    _, mv_id, normalized, existing_from = row

    changed = AliasRow(
        id="",
        surface="haiku",
        normalized=normalized,
        variants=["haiku", "something else"],
        provider_hint="anthropic",
        model_version_id=mv_id,
        family="claude",
        specificity="family",
        valid_from=date(2020, 1, 1),  # earlier than the row it supersedes
    )
    changed = replace(changed, id=model_alias_id(normalized, mv_id, changed.content_key()))
    _sync_alias(conn, changed)
    conn.commit()

    for valid_from, valid_until in conn.execute(
        "SELECT valid_from, valid_until FROM model_alias WHERE normalized = %s "
        "AND model_version_id = %s",
        (normalized, mv_id),
    ).fetchall():
        if valid_from and valid_until:
            assert valid_until >= valid_from


def test_no_alias_row_is_ever_deleted(conn):
    """FR-4 in the direction that is easy to break by accident."""
    _load(conn, as_of=AS_OF)
    ids_before = {r[0] for r in conn.execute("SELECT id FROM model_alias").fetchall()}
    _bump_release_date(conn, "anthropic/claude-opus-5", date(2026, 7, 1))
    _load(conn, as_of=AS_OF)
    ids_after = {r[0] for r in conn.execute("SELECT id FROM model_alias").fetchall()}
    assert ids_before <= ids_after


def test_a_bare_family_alias_resolves_at_family_specificity(conn):
    _load(conn)
    specificity = _scalar(
        conn, "SELECT specificity FROM model_alias WHERE normalized = 'sonnet'"
    )
    assert specificity == "family"


def test_new_models_raise_an_event(conn):
    _load(conn)
    assert _scalar(conn, "SELECT count(*) FROM model_event WHERE type='new-model'") == 10


def test_first_load_records_a_price_baseline(conn):
    _load(conn)
    assert _scalar(conn, "SELECT count(*) FROM pricing_history") == 10
    # a baseline is not a change
    assert _scalar(conn, "SELECT count(*) FROM model_event WHERE type='price-change'") == 0


# ── FR-3: every price move raises its own event ───────────────────────────

FLASH = "google/gemini-2.5-flash"


def _seed_priced_at(tmp_path, price: str, tag: str):
    """A copy of the real seed file with one price moved.

    The provider changes the price; the change arrives in the *incoming*
    data, which is what the week-5 poller will see. Editing `model_version`
    directly would simulate it backwards and leave `pricing_history` holding
    a value the loader never wrote.
    """
    raw = yaml.safe_load(SEED_MODELS_YAML.read_text(encoding="utf-8"))
    for entry in raw["models"]:
        if entry["canonical_id"] == FLASH:
            entry["price_in"] = float(price)
    path = tmp_path / f"seed_{tag}.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def test_an_oscillating_price_produces_one_event_per_move(conn, tmp_path):
    """THE ACCEPTANCE TEST.

    A to B to A to B. Before the fix the id was a hash of a constant string
    carrying no values and no timestamp, so every move after the first
    collided and was discarded by ON CONFLICT DO NOTHING. `pricing_history`
    recorded them, `model_event` did not, and alerting reads events.
    """
    _load(conn, as_of=AS_OF)  # baseline at 0.30, no price event
    assert _scalar(conn, "SELECT count(*) FROM model_event WHERE type='price-change'") == 0

    for index, price in enumerate(("9.99", "0.30", "9.99", "0.30")):
        _load(conn, path=_seed_priced_at(tmp_path, price, str(index)), as_of=AS_OF)

    assert _scalar(conn, "SELECT count(*) FROM model_event WHERE type='price-change'") == 4
    assert _scalar(conn, "SELECT count(*) FROM pricing_history") == 14  # 10 baseline + 4


def test_a_price_that_does_not_move_raises_nothing(conn, tmp_path):
    """Reloading the same values is not four events, or any."""
    _load(conn, as_of=AS_OF)
    for index in range(3):
        _load(conn, path=_seed_priced_at(tmp_path, "0.30", f"same{index}"), as_of=AS_OF)
    assert _scalar(conn, "SELECT count(*) FROM model_event WHERE type='price-change'") == 0


def test_every_event_has_a_distinct_id(conn, tmp_path):
    _load(conn, as_of=AS_OF)
    for index, price in enumerate(("9.99", "0.30", "9.99", "0.30")):
        _load(conn, path=_seed_priced_at(tmp_path, price, str(index)), as_of=AS_OF)

    ids = [r[0] for r in conn.execute("SELECT id FROM model_event").fetchall()]
    assert len(ids) == len(set(ids))
    assert len(ids) == 14  # 10 new-model + 4 price-change


def test_every_event_carries_an_occurred_at(conn, tmp_path):
    _load(conn, as_of=AS_OF)
    _load(conn, path=_seed_priced_at(tmp_path, "9.99", "x"), as_of=AS_OF)
    assert _scalar(conn, "SELECT count(*) FROM model_event WHERE occurred_at IS NULL") == 0


def test_a_price_events_occurred_at_is_the_observation_that_revealed_it(conn, tmp_path):
    """Not a restatement of when this code ran: it ties to the audit row."""
    _load(conn, as_of=AS_OF)
    _load(conn, path=_seed_priced_at(tmp_path, "9.99", "x"), as_of=AS_OF)

    row = conn.execute(
        "SELECT e.occurred_at, h.observed_at FROM model_event e "
        "JOIN model_version m ON m.id = e.model_version_id "
        "JOIN pricing_history h ON h.model_version_id = m.id "
        "WHERE e.type = 'price-change' AND m.canonical_id = %s "
        "ORDER BY h.observed_at DESC LIMIT 1",
        (FLASH,),
    ).fetchone()
    assert row is not None
    assert row[0] == row[1]


def test_a_new_model_event_occurred_when_the_model_was_released(conn):
    _load(conn, as_of=AS_OF)
    occurred = _scalar(
        conn,
        "SELECT e.occurred_at::date FROM model_event e JOIN model_version m "
        "ON m.id = e.model_version_id WHERE e.type='new-model' AND m.canonical_id=%s",
        (FLASH,),
    )
    assert occurred == date(2025, 5, 19)


def test_the_event_payload_carries_the_values(conn, tmp_path):
    """Alerting reads events, so an event that says only 'something moved'
    forces a second query to be actionable."""
    _load(conn, as_of=AS_OF)
    _load(conn, path=_seed_priced_at(tmp_path, "9.99", "x"), as_of=AS_OF)

    payload = _scalar(conn, "SELECT payload FROM model_event WHERE type='price-change' LIMIT 1")
    assert payload["changed"] == ["price_in"]
    assert payload["to"]["price_in"].startswith("9.99")
    assert payload["canonical_id"] == FLASH


# ── the two smaller defects ───────────────────────────────────────────────


def test_a_missing_history_row_is_not_reported_as_a_price_change(conn):
    """A backfill is not a movement.

    `_record_prices` used to decide this by asking `pricing_history`, so a
    model whose history row was absent reported a change for a price that
    had never moved.
    """
    _load(conn, as_of=AS_OF)
    conn.execute("DELETE FROM pricing_history")
    conn.commit()

    report = _load(conn, as_of=AS_OF)

    assert [e for e in report.events if e[0] == "price-change"] == []
    assert _scalar(conn, "SELECT count(*) FROM model_event WHERE type='price-change'") == 0
    # the baseline is still rebuilt, so the audit trail recovers
    assert _scalar(conn, "SELECT count(*) FROM pricing_history") == 10


def test_a_model_with_no_prices_gets_no_all_null_history_row(conn):
    """Three NULLs assert nothing, and would accumulate one row per run."""
    _load(conn, as_of=AS_OF)
    conn.execute(
        "UPDATE model_version SET price_in=NULL, price_out=NULL, price_cached_read=NULL "
        "WHERE canonical_id = %s",
        (FLASH,),
    )
    conn.execute(
        "DELETE FROM pricing_history WHERE model_version_id = "
        "(SELECT id FROM model_version WHERE canonical_id = %s)",
        (FLASH,),
    )
    conn.commit()

    from collect.registry.load import _record_prices

    row = {
        "id": _scalar(conn, "SELECT id FROM model_version WHERE canonical_id = %s", (FLASH,)),
        "price_in": None,
        "price_out": None,
        "price_cached_read": None,
    }
    assert _record_prices(conn, row) is None
    assert _scalar(conn, "SELECT count(*) FROM pricing_history") == 9


def test_a_moved_price_is_detected_and_recorded(conn):
    """FR-3, in the shape week 5's daily API diff will use."""
    _load(conn)
    conn.execute(
        "UPDATE model_version SET price_in = %s WHERE canonical_id = %s",
        (Decimal("0.01"), "google/gemini-2.5-flash"),
    )
    conn.execute(
        "INSERT INTO pricing_history (model_version_id, price_in, price_out, "
        "price_cached_read) SELECT id, %s, price_out, price_cached_read "
        "FROM model_version WHERE canonical_id = %s",
        (Decimal("0.01"), "google/gemini-2.5-flash"),
    )
    conn.commit()

    report = _load(conn)
    assert report.models_updated == 1
    assert any(event == "price-change" for event, _ in report.events)
    assert _scalar(conn, "SELECT count(*) FROM model_event WHERE type='price-change'") == 1
    assert _scalar(conn, "SELECT count(*) FROM pricing_history") == 12


# ── provenance: polling is never downgraded back to seed ──────────────────


def _set_polled(connection, canonical_id: str) -> None:
    connection.execute(
        "UPDATE model_version SET provenance = 'polled' WHERE canonical_id = %s",
        (canonical_id,),
    )
    connection.commit()


def test_a_polled_row_is_never_downgraded_to_seed(conn):
    """THE ACCEPTANCE TEST.

    Once week 5's poller owns a row, one stray `registry load-seed` used to
    flip it back to `provenance = 'seed'`, after which `assert_no_fixtures`
    refuses to boot production over a model that is perfectly real.
    """
    _load(conn, as_of=AS_OF)
    _set_polled(conn, "google/gemini-2.5-flash")

    with pytest.raises(ProvenanceDowngradeError, match="gemini-2.5-flash"):
        _load(conn, as_of=AS_OF)

    conn.rollback()
    assert (
        _scalar(
            conn,
            "SELECT provenance FROM model_version WHERE canonical_id = 'google/gemini-2.5-flash'",
        )
        == "polled"
    )


def test_the_refusal_names_every_affected_row_not_just_the_first(conn):
    """A pre-flight, so the message is actionable in one pass."""
    _load(conn, as_of=AS_OF)
    for canonical_id in ("google/gemini-2.5-flash", "openai/gpt-4.1-mini"):
        _set_polled(conn, canonical_id)

    with pytest.raises(ProvenanceDowngradeError) as excinfo:
        _load(conn, as_of=AS_OF)
    conn.rollback()

    assert set(excinfo.value.canonical_ids) == {
        "google/gemini-2.5-flash",
        "openai/gpt-4.1-mini",
    }


def test_nothing_is_written_when_the_load_is_refused(conn):
    """Pre-flight means the refusal happens before the first UPDATE."""
    _load(conn, as_of=AS_OF)
    _set_polled(conn, "google/gemini-2.5-flash")
    conn.execute(
        "UPDATE model_version SET price_in = 999 WHERE canonical_id = 'anthropic/claude-opus-5'"
    )
    conn.commit()

    with pytest.raises(ProvenanceDowngradeError):
        _load(conn, as_of=AS_OF)
    conn.rollback()

    assert _scalar(
        conn, "SELECT price_in FROM model_version WHERE canonical_id = 'anthropic/claude-opus-5'"
    ) == Decimal("999.000000")


def test_a_seed_row_still_upserts_normally(conn):
    """The guard is directional; it must not freeze ordinary seed reloads."""
    _load(conn, as_of=AS_OF)
    conn.execute(
        "UPDATE model_version SET price_in = 42 WHERE canonical_id = 'anthropic/claude-opus-5'"
    )
    conn.commit()

    report = _load(conn, as_of=AS_OF)
    assert report.models_updated == 1
    assert _scalar(
        conn, "SELECT price_in FROM model_version WHERE canonical_id = 'anthropic/claude-opus-5'"
    ) == Decimal("5.000000")


def test_promotion_from_seed_to_polled_is_allowed(conn):
    """Week 5 must be able to take ownership of a seeded row."""
    from collect.registry.load import _upsert_model, model_row

    _load(conn, as_of=AS_OF)
    model = next(
        m for m in load_seed_file().models if m.canonical_id == "anthropic/claude-opus-5"
    )
    verdict, _ = _upsert_model(conn, model_row(model, provenance="polled", as_of=AS_OF))
    conn.commit()

    assert verdict == "updated"
    assert (
        _scalar(
            conn,
            "SELECT provenance FROM model_version WHERE canonical_id = 'anthropic/claude-opus-5'",
        )
        == "polled"
    )


# ── in_window has exactly one writer ──────────────────────────────────────


def test_the_loader_never_updates_in_window(conn):
    """Ownership: the nightly recompute job writes this column, not the load."""
    _load(conn, as_of=AS_OF)
    conn.execute("UPDATE model_version SET in_window = false")
    conn.commit()

    _load(conn, as_of=AS_OF)
    assert _scalar(conn, "SELECT count(*) FROM model_version WHERE in_window") == 0


def test_the_loader_still_seeds_in_window_on_insert(conn):
    """The column is NOT NULL, so a fresh row needs a value immediately."""
    _load(conn, as_of=AS_OF)
    assert _scalar(conn, "SELECT count(*) FROM model_version WHERE NOT in_window") == 3


def test_recompute_window_is_the_writer(conn):
    _load(conn, as_of=AS_OF)
    conn.execute("UPDATE model_version SET in_window = true")
    conn.commit()

    counts = recompute_window(conn, as_of=AS_OF)
    conn.commit()

    assert counts["changed"] == 3
    assert counts["out_of_window"] == 3
    assert counts["in_window"] == 7


def test_recompute_window_is_idempotent(conn):
    _load(conn, as_of=AS_OF)
    recompute_window(conn, as_of=AS_OF)
    conn.commit()
    assert recompute_window(conn, as_of=AS_OF)["changed"] == 0


def test_recompute_window_moves_with_the_date(conn):
    """The reason it is a job and not a one-off: the answer changes daily."""
    _load(conn, as_of=AS_OF)
    recompute_window(conn, as_of=date(2026, 7, 1))
    conn.commit()
    assert _scalar(conn, "SELECT count(*) FROM model_version WHERE NOT in_window") == 2

    recompute_window(conn, as_of=AS_OF)
    conn.commit()
    assert _scalar(conn, "SELECT count(*) FROM model_version WHERE NOT in_window") == 3


def test_production_refuses_to_start_on_seeded_rows(conn):
    _load(conn)
    with pytest.raises(FixtureLeakError):
        assert_no_fixtures(conn, environment="production")


def test_development_starts_anyway(conn):
    _load(conn)
    assert_no_fixtures(conn, environment="development")
