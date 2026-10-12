"""#460: the version-surface reader counts only CURRENT alias rows.

`collect/assemble/reddit.py` ran its own copy of the query with no `valid_until`
filter, so closed rows (`astra`, `gpt6`, `claude fable 51`, `fable5` on
staging, 2026-09-24) still counted as a comment naming a specific version. Both
assemblers now read `ranking.version_surfaces`, and this pins its predicate:
`valid_until IS NULL OR valid_until > now()`.

TEST_DATABASE_URL only: every test drops and rebuilds the schema.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from collect.assemble.ranking import version_surfaces
from tests.conftest import assert_disposable, assert_safe_target

MV = "mv_currency_test"


@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema, connect

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.execute(
            "INSERT INTO model_version (id, canonical_id, provider, sources, provenance) "
            "VALUES (%s, 'x/astra-1', 'x', '{}', 'polled')",
            (MV,),
        )
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _alias(conn, normalized: str, *, valid_until: date | None,
           specificity: str = "version") -> None:
    conn.execute(
        "INSERT INTO model_alias (id, surface, normalized, variants, model_version_id, "
        "specificity, valid_until) VALUES (%s, %s, %s, '{}', %s, %s, %s)",
        (f"ma_{normalized}", normalized, normalized, MV, specificity, valid_until),
    )
    conn.commit()


def test_a_closed_row_is_not_a_current_surface(conn):
    _alias(conn, "astra", valid_until=date(2026, 9, 17))
    _alias(conn, "astra1", valid_until=None)

    assert version_surfaces(conn) == {"astra1"}


def test_a_window_closing_in_the_future_is_still_current(conn):
    _alias(conn, "astra1", valid_until=date.today() + timedelta(days=30))

    assert version_surfaces(conn) == {"astra1"}


def test_family_surfaces_stay_out(conn):
    _alias(conn, "astrafamily", valid_until=None, specificity="family")

    assert version_surfaces(conn) == set()


def test_the_reddit_assembler_reads_the_same_function():
    """One reader, so the two assemblers cannot drift again."""
    import inspect

    from collect.assemble import reddit

    source = inspect.getsource(reddit)
    assert "version_surfaces(conn)" in source
    assert "FROM model_alias" not in source, "reddit.py grew its own alias query again"
