"""`unpolled` is the third provenance, and only `seed` means fixture. #382.

WHAT THESE PROTECT, AND WHY THE CLASS IS WORTH ITS OWN FILE

Four real models — Recraft V4.1 Pro, ElevenLabs v3, Qwen3.5 Omni Flash and
Gemini 3.8 Flash — sat in the shared database labelled `provenance='seed'`
carrying 65 claims and 11 cells between them. Nothing was broken: the loader
wrote the only hand-written value the column allowed, and `assert_no_fixtures`
refused them exactly as written. The column could not express the distinction,
so a guard against fixtures was aimed at models that were not fixtures.

The failure mode to protect against now is the OPPOSITE one, and it is worse:
a change that makes `assert_no_fixtures` stop refusing real build fixtures.
`seed_models.yaml`'s eleven ARE fixtures and must still be refused outside
development. So the tests below assert both directions rather than only that
`unpolled` is accepted.

    pwsh scripts/dev-postgres.ps1        # writes .env.test
    .venv\\Scripts\\python.exe -m pytest tests/test_unpolled_provenance.py -q
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from collect.registry.assertions import FixtureLeakError, assert_no_fixtures
from collect.registry.load import (
    HAND_WRITTEN_PROVENANCE,
    ProvenanceDowngradeError,
    load_seed,
    model_row,
)
from collect.registry.seed import load_seed_file

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contract"
MIGRATION = (
    CONTRACT / "migrations" / "20260923T0500_model_version_unpolled_provenance.sql"
)

#: The four rows the migration converts, named here so a change to either list
#: fails rather than drifting. These are the models in `unpolled_models.yaml`
#: and `awaiting_poll_models.yaml` as of 2026-09-23.
THE_FOUR = {
    "recraft/recraft-v4.1-pro",
    "elevenlabs/eleven-v3",
    "qwen/qwen3.5-omni-flash",
    "google/gemini-3.8-flash",
}

AS_OF = date(2026, 8, 12)


# ── the vocabulary itself ───────────────────────────────────────────────────


def test_polled_is_not_a_value_a_contract_file_may_write():
    """`polled` is the poller's. A YAML claiming it would be a lie about origin."""
    assert "polled" not in HAND_WRITTEN_PROVENANCE
    assert frozenset({"seed", "unpolled"}) == HAND_WRITTEN_PROVENANCE


def test_load_seed_refuses_a_provenance_it_has_no_business_writing():
    with pytest.raises(ValueError, match="cannot write provenance"):
        load_seed(None, provenance="polled")  # refuses before touching `conn`


def test_model_row_still_defaults_to_the_fixture_value():
    """The default caller IS the fixture file.

    A default of `unpolled` would exempt eleven genuine build fixtures from
    `assert_no_fixtures` without anybody choosing that.
    """
    model = load_seed_file().models[0]
    assert model_row(model, as_of=AS_OF)["provenance"] == "seed"


# ── the two contract files this value exists for ────────────────────────────


@pytest.mark.parametrize(
    "filename", ["unpolled_models.yaml", "awaiting_poll_models.yaml"]
)
def test_the_non_fixture_contracts_hold_exactly_the_models_the_migration_names(
    filename,
):
    """The migration lists four `canonical_id`s literally; these are the files.

    A migration cannot import the repository, so the list in the SQL is a copy.
    This is the test that makes the copy checkable — if a fifth model is seated
    in either file and the migration is not the thing that seats it, this fails
    and says so.
    """
    models = load_seed_file(CONTRACT / filename).models
    assert models, f"{filename} declares no models"
    for model in models:
        assert model.canonical_id in THE_FOUR, (
            f"{model.canonical_id} is in {filename} and is not one of the four "
            "the migration converts. A newly seated model must be loaded as "
            "`unpolled` directly — do not add it to the migration, which has "
            "already run."
        )


def test_the_migration_converts_only_the_named_four():
    sql = MIGRATION.read_text(encoding="utf-8")
    named = set(re.findall(r"'([a-z0-9.\-]+/[a-z0-9.\-]+)'", sql))
    assert named == THE_FOUR


def test_the_migration_is_scoped_to_seed_rows():
    """Without `WHERE provenance = 'seed'` this would relabel a polled row."""
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "WHERE provenance = 'seed'" in sql


# NO TRANSACTION-CONTROL TEST HERE ON PURPOSE. `tests/test_migrations.py`
# already asserts it over EVERY migration, and it draws the line correctly: it
# matches whole STATEMENTS rather than the bare word, because `BEGIN` inside a
# `DO $$ ... END $$` block opens a PL/pgSQL block and is legitimate. This
# migration uses such a block for its post-condition, and a naive version of
# the check written here flagged it — which is how the duplicate was found and
# deleted rather than fixed.


def test_the_loader_script_writes_unpolled():
    """The writer, so nothing new arrives mislabelled after the migration."""
    src = (ROOT / "scripts" / "load_unpolled_models.py").read_text(encoding="utf-8")
    assert 'provenance="unpolled"' in src


# ── against a real database ─────────────────────────────────────────────────


@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema, connect
    from tests.conftest import assert_disposable, assert_safe_target

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


def _seat(connection, canonical_id: str, provenance: str) -> None:
    """One `model_version` row, the smallest that satisfies the schema."""
    model = load_seed_file(CONTRACT / "unpolled_models.yaml").models[0]
    row = model_row(model, provenance=provenance, as_of=AS_OF)
    row["canonical_id"] = canonical_id
    from psycopg.types.json import Json

    from collect.registry.load import _MODEL_COLUMNS

    row["sources"] = Json(row["sources"])
    columns = ", ".join(_MODEL_COLUMNS)
    placeholders = ", ".join(f"%({c})s" for c in _MODEL_COLUMNS)
    connection.execute(
        f"INSERT INTO model_version ({columns}) VALUES ({placeholders})",  # noqa: S608
        row,
    )


def test_the_check_constraint_accepts_unpolled(conn):
    _seat(conn, "vendor/only-hand-entered", "unpolled")
    got = conn.execute(
        "SELECT provenance FROM model_version WHERE canonical_id = %s",
        ("vendor/only-hand-entered",),
    ).fetchone()[0]
    assert got == "unpolled"


def test_the_check_constraint_still_refuses_a_typo(conn):
    """The CHECK widened by one value, not into free text."""
    import psycopg

    with pytest.raises(psycopg.errors.CheckViolation):
        _seat(conn, "vendor/typo", "unpoled")


def test_assert_no_fixtures_ignores_unpolled(conn):
    """The whole point. A real model no poll carries must not block staging."""
    _seat(conn, "vendor/real-but-unpolled", "unpolled")
    conn.commit()
    assert_no_fixtures(conn, environment="production")  # does not raise


def test_assert_no_fixtures_still_refuses_seed(conn):
    """⚠ THE REGRESSION THAT WOULD MATTER.

    Widening the vocabulary must not widen the guard. `seed_models.yaml`'s
    eleven are genuine build fixtures and are still refused outside
    development — that is what `assert_no_fixtures` was written for and it is
    unchanged by #382.
    """
    _seat(conn, "vendor/actual-fixture", "seed")
    conn.commit()
    with pytest.raises(FixtureLeakError, match="1 seeded model"):
        assert_no_fixtures(conn, environment="production")


def test_a_load_may_not_flip_a_polled_row_to_unpolled(conn):
    """The downgrade guard covers the new value, not only `seed`.

    Before #382 the guard named `seed` inline at both sites, which was exact
    when `seed` was the only hand-written value. A load that turned a polled
    row into `unpolled` would be the identical defect wearing the new word.
    """
    seed = load_seed_file(CONTRACT / "unpolled_models.yaml")
    _seat(conn, seed.models[0].canonical_id, "polled")
    conn.commit()
    with pytest.raises(ProvenanceDowngradeError):
        load_seed(
            conn,
            path=CONTRACT / "unpolled_models.yaml",
            provenance="unpolled",
            as_of=AS_OF,
            strict_sources=False,
            strict_spelling=False,
        )
