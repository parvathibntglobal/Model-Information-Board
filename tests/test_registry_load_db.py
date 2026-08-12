"""Registry load against a real Postgres.

Skipped unless TEST_DATABASE_URL is set. It is deliberately *not*
DATABASE_URL: these tests drop and recreate the public schema, and a helper
that can wipe a working database on a typo eventually will.

    $env:TEST_DATABASE_URL = "postgresql://localhost:5432/modelboard_test"
    py -3 -m pytest tests/test_registry_load_db.py -q
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

from collect.registry.assertions import FixtureLeakError, assert_no_fixtures

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
    from collect.registry.load import load_seed

    report = load_seed(connection, strict_sources=False, **kwargs)
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


def test_production_refuses_to_start_on_seeded_rows(conn):
    _load(conn)
    with pytest.raises(FixtureLeakError):
        assert_no_fixtures(conn, environment="production")


def test_development_starts_anyway(conn):
    _load(conn)
    assert_no_fixtures(conn, environment="development")
