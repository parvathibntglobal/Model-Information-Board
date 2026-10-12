"""#457: alias rows key on the registry row's OWN id, not the computed one.

`alias_rows` used to set `model_version_id = stable_id("mv", canonical_id)`.
Two staging rows were hand-entered under another id (2 of 242 on 2026-09-24:
`anthropic/claude-fable-5-1` with canonical `anthropic/claude-fable-5.1`, and
`openai/gpt-6-astra`), so seating or re-loading either wrote aliases pointing
at no row - the foreign-key failure #454 fixed in the poll, one table over.

Both writers are run here against a row whose id is not the computation:
`seat()` (via `rows_for`, which `tracked_load` and `auto_seat` share) and
`load_seed`. TEST_DATABASE_URL only: every test drops and rebuilds the schema.
"""

from __future__ import annotations

import textwrap
from datetime import date

import pytest
from psycopg.types.json import Json

from collect.ids import stable_id
from collect.registry.load import load_seed
from collect.registry.seat import seat
from tests.conftest import assert_disposable, assert_safe_target

HAND_ID = "anthropic/claude-fable-5-1"
CANONICAL = "anthropic/claude-fable-5.1"
AS_OF = date(2026, 10, 1)


@pytest.fixture
def conn(test_dsn):
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


def _hand_entered(conn) -> None:
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, family, display_name, "
        "provenance, sources) VALUES (%s, %s, 'anthropic', 'claude', 'Claude Fable 5.1', "
        "'unpolled', %s)",
        (HAND_ID, CANONICAL, Json({})),
    )
    conn.commit()


def _alias_owners(conn) -> set[str]:
    return {r[0] for r in conn.execute("SELECT model_version_id FROM model_alias").fetchall()}


def test_the_case_this_file_exists_for():
    assert stable_id("mv", CANONICAL) != HAND_ID


def test_seat_keys_aliases_on_the_rows_own_id(conn, tmp_path):
    _hand_entered(conn)
    artifact = tmp_path / "artifact.yaml"
    artifact.write_text(
        "proposals:\n"
        f"  - canonical_id: {CANONICAL}\n"
        "    surface: claude fable 5.1\n"
        "    variants:\n"
        "      - claude-fable-5.1\n"
        "      - claudefable5.1\n"
        "    incomplete: [family_surface]\n",
        encoding="utf-8",
    )

    report = seat(conn, CANONICAL, path=artifact)  # an FK violation raises here
    conn.commit()

    assert report["rows"] > 0
    assert _alias_owners(conn) == {HAND_ID}


def test_load_seed_keys_aliases_prices_and_events_on_the_rows_own_id(conn, tmp_path):
    _hand_entered(conn)
    seed = tmp_path / "seed.yaml"
    seed.write_text(
        textwrap.dedent(
            f"""\
            version: "1.0"
            provenance: seed
            models:
              - canonical_id: '{CANONICAL}'
                provider: 'anthropic'
                family: 'claude'
                display_name: 'Claude Fable 5.1'
                price_in: 1.00
                price_out: 2.00
                aliases:
                  surface: 'claude fable 5.1'
                  variants: ['claude-fable-5.1', 'claudefable5.1']
            """
        ),
        encoding="utf-8",
    )

    report = load_seed(
        conn, path=seed, provenance="unpolled", as_of=AS_OF,
        strict_sources=False, strict_spelling=False,
    )
    conn.commit()

    assert report.models_inserted == 0, "the hand-entered row is updated, not duplicated"
    ids = {r[0] for r in conn.execute("SELECT id FROM model_version").fetchall()}
    assert ids == {HAND_ID}
    assert report.aliases_inserted > 0
    assert _alias_owners(conn) == {HAND_ID}
    history = conn.execute("SELECT model_version_id FROM pricing_history").fetchall()
    assert history == [(HAND_ID,)]


def test_a_reload_is_a_no_op_rather_than_a_second_set(conn, tmp_path):
    """The alias id folds in the model id, so a reload on the same id must
    reproduce it - a reload on a DIFFERENT id would append a duplicate set."""
    _hand_entered(conn)
    seed = tmp_path / "seed.yaml"
    seed.write_text(
        textwrap.dedent(
            f"""\
            version: "1.0"
            provenance: seed
            models:
              - canonical_id: '{CANONICAL}'
                provider: 'anthropic'
                family: 'claude'
                display_name: 'Claude Fable 5.1'
                aliases:
                  surface: 'claude fable 5.1'
                  variants: ['claude-fable-5.1', 'claudefable5.1']
            """
        ),
        encoding="utf-8",
    )
    kwargs = dict(path=seed, provenance="unpolled", as_of=AS_OF,
                  strict_sources=False, strict_spelling=False)
    first = load_seed(conn, **kwargs)
    conn.commit()
    second = load_seed(conn, **kwargs)
    conn.commit()

    assert first.aliases_inserted > 0
    assert (second.aliases_inserted, second.aliases_existing) == (0, first.aliases_inserted)


# ── scripts/propose_model.py: the same shape, read side ─────────────────────


def _hand_alias(conn, normalized: str) -> None:
    conn.execute(
        "INSERT INTO model_alias (id, surface, normalized, variants, model_version_id, "
        "specificity) VALUES (%s, %s, %s, '{}', %s, 'version')",
        (f"ma_hand_{normalized}", normalized, normalized, HAND_ID),
    )
    conn.commit()


def test_propose_finds_the_hand_row_by_its_canonical_id(conn):
    from scripts.propose_model import _add

    _hand_entered(conn)
    out = _add(conn, "Claude Fable 5.1", CANONICAL, "text")

    assert out["in_registry"] is True
    assert out["model_version_id"] == HAND_ID


def test_propose_finds_a_hand_row_named_by_its_typed_id(conn):
    from scripts.propose_model import _add

    _hand_entered(conn)
    out = _add(conn, "Claude Fable 5.1", HAND_ID, "text")

    assert out["in_registry"] is True
    assert out["registry_row"]["canonical_id"] == CANONICAL


def test_a_models_own_aliases_are_not_reported_as_a_collision(conn):
    """Excluding only the computed id reported the model's own row as 'held by'."""
    from scripts.propose_model import _add

    _hand_entered(conn)
    _hand_alias(conn, "claudefable51")
    out = _add(conn, "Claude Fable 5.1", CANONICAL, "text")

    assert out["collisions"] == []


def test_another_models_alias_is_still_a_collision(conn):
    from scripts.propose_model import _add

    _hand_entered(conn)
    _hand_alias(conn, "claudefable51")
    out = _add(conn, "Claude Fable 5.1", "anthropic/claude-fable-5.2", "text")

    assert {c["held_by"] for c in out["collisions"]} == {HAND_ID}
