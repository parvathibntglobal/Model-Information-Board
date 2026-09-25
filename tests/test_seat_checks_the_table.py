"""#455: seating checks a new alias against the rows OTHER models already hold.

`seat()`'s docstring promised to refuse "a collision with an alias already live
for a different model", and it compared the new model's rows with each other
only. The collision that surfaced it was `fable5`, claimed by Claude Fable 5.1's
CLOSED row (NULL `valid_from`, so open-ended before 2026-09-17) and Claude Fable
5's new row from 2026-06-09. A check against live rows only, in code or by hand,
saw nothing.

So the check compares against the whole table for the new rows' keys, closed
rows included, over overlapping windows - with NULL `valid_from` read as
open-ended, never as "no claim". A same-day handover does not overlap, and a
model re-seated against its own rows is not a collision.

TEST_DATABASE_URL, never DATABASE_URL: every test drops and rebuilds the schema.
"""

from __future__ import annotations

import textwrap
from datetime import date

import pytest

from collect.ids import model_version_id
from collect.registry.aliases import AliasCollisionError
from collect.registry.seat import seat, table_claims
from tests.conftest import assert_disposable, assert_safe_target

MODEL = "anthropic/claude-fable-5"
OTHER = "anthropic/claude-fable-5.1"


@pytest.fixture
def conn(test_dsn):
    """A schema-fresh connection to a database proven safe to destroy."""
    from collect.db import apply_schema, connect

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.commit()
        apply_schema(connection)
        yield connection
    finally:
        connection.close()


def _registry_row(conn, canonical_id: str, *, release: date | None = None) -> None:
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, sources, provenance, release_date) "
        "VALUES (%s, %s, 'anthropic', '{}', 'polled', %s)",
        (model_version_id(canonical_id), canonical_id, release),
    )
    conn.commit()


def _held(conn, canonical_id: str, normalized: str, *,
          valid_from: date | None, valid_until: date | None) -> None:
    """An alias row another model already holds, with the window given."""
    conn.execute(
        "INSERT INTO model_alias (id, surface, normalized, variants, model_version_id, "
        "  specificity, valid_from, valid_until) "
        "VALUES (%s, %s, %s, '{}', %s, 'version', %s, %s)",
        (f"ma_held_{normalized}_{valid_until}", normalized, normalized,
         model_version_id(canonical_id), valid_from, valid_until),
    )
    conn.commit()


def _artifact(tmp_path, canonical_id: str, surface: str, variants: list[str]):
    body = textwrap.dedent(
        """\
        policy:
          mention_floor: 20
          launch_window_days: 30
        proposals:
        """
    ) + "\n".join([
        f"  - canonical_id: {canonical_id}",
        "    status: attested",
        "    seated_by: reviewed",
        f"    surface: {surface}",
        "    variants:",
        *[f"      - {v}" for v in variants],
        "    incomplete: [family_surface]",
    ]) + "\n"
    path = tmp_path / "artifact.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def _mine(conn, canonical_id: str) -> int:
    return conn.execute(
        "SELECT count(*) FROM model_alias WHERE model_version_id = %s",
        (model_version_id(canonical_id),),
    ).fetchone()[0]


def _fable5(tmp_path):
    return _artifact(tmp_path, MODEL, "fable 5", ["fable-5", "fable5"])


def test_a_key_another_model_holds_live_is_refused(conn, tmp_path):
    _registry_row(conn, MODEL, release=date(2026, 6, 9))
    _registry_row(conn, OTHER)
    _held(conn, OTHER, "fable5", valid_from=date(2026, 6, 1), valid_until=None)
    with pytest.raises(AliasCollisionError, match="fable5"):
        seat(conn, MODEL, path=_fable5(tmp_path))
    assert _mine(conn, MODEL) == 0, "the refusal comes before any write"


def test_a_closed_row_still_claims_the_window_it_covered(conn, tmp_path):
    """The shape that surfaced #455: NULL start, closed 2026-09-17, against a
    new seat from 2026-06-09. Invisible to a live-rows-only check."""
    _registry_row(conn, MODEL, release=date(2026, 6, 9))
    _registry_row(conn, OTHER)
    _held(conn, OTHER, "fable5", valid_from=None, valid_until=date(2026, 9, 17))
    with pytest.raises(AliasCollisionError, match="fable5"):
        seat(conn, MODEL, path=_fable5(tmp_path))
    assert _mine(conn, MODEL) == 0


def test_a_handover_on_the_closing_day_is_not_a_collision(conn, tmp_path):
    """Half-open windows: the old row ends the day the new one starts."""
    _registry_row(conn, MODEL, release=date(2026, 9, 17))
    _registry_row(conn, OTHER)
    _held(conn, OTHER, "fable5", valid_from=None, valid_until=date(2026, 9, 17))
    result = seat(conn, MODEL, path=_fable5(tmp_path))
    conn.commit()
    assert result["rows"] > 0 and _mine(conn, MODEL) == result["rows"]


def test_a_key_nobody_else_holds_seats(conn, tmp_path):
    _registry_row(conn, MODEL, release=date(2026, 6, 9))
    _registry_row(conn, OTHER)
    _held(conn, OTHER, "fable51", valid_from=None, valid_until=None)
    result = seat(conn, MODEL, path=_fable5(tmp_path))
    conn.commit()
    assert _mine(conn, MODEL) == result["rows"]


def test_reseating_a_model_does_not_collide_with_its_own_rows(conn, tmp_path):
    _registry_row(conn, MODEL, release=date(2026, 6, 9))
    artifact = _fable5(tmp_path)
    first = seat(conn, MODEL, path=artifact)
    conn.commit()
    again = seat(conn, MODEL, path=artifact)
    conn.commit()
    assert again["rows"] == first["rows"]


def test_the_table_is_read_with_null_start_as_open_ended(conn):
    _registry_row(conn, OTHER)
    _held(conn, OTHER, "fable5", valid_from=None, valid_until=date(2026, 9, 17))
    (row,) = table_claims(conn, ["fable5", "", None])
    assert row.canonical_id == OTHER
    assert row.valid_from is None and row.valid_until == date(2026, 9, 17)
    assert table_claims(conn, []) == []


def test_a_tracked_load_plan_refuses_an_entry_that_collides_with_the_table(conn, tmp_path):
    """`plan()` checked the manifest's own union; it now checks the table too."""
    from collect.registry.tracked_load import plan, read_manifest
    from tests.test_load_tracked_set import _artifact as tracked_artifact
    from tests.test_load_tracked_set import _entry_block, _manifest

    _registry_row(conn, MODEL, release=date(2026, 6, 9))
    _registry_row(conn, OTHER)
    _held(conn, OTHER, "fable5", valid_from=None, valid_until=date(2026, 9, 17))
    artifact = tracked_artifact(tmp_path, _entry_block(MODEL, "fable 5", ["fable-5", "fable5"]))
    prepared = plan(conn, read_manifest(_manifest(tmp_path, artifact, [MODEL])),
                    artifact_path=artifact)
    assert prepared.refusals, "a key another model's closed row covers must refuse"
    assert any("fable5" in r for r in prepared.refusals)
