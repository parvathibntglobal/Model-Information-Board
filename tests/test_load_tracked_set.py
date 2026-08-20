"""The tracked-set loader, against a real Postgres.

**The question this file exists to answer** is the one that was worth confirming
rather than assuming: `model_alias` is append-only and the loader ships without
family surfaces, so *does a later load add the family surfaces, or does it need a
separate path?* The additive-on-conflict shape suggests the first. Suggesting is
not knowing — `test_a_second_load_adds_a_family_surface_and_disturbs_nothing`
makes it a fact.

TEST_DATABASE_URL is deliberately not DATABASE_URL. Every test here runs
DROP SCHEMA public CASCADE; see `tests/conftest.py` for the three layers that
enforce it.
"""

from __future__ import annotations

import textwrap

import pytest
import yaml

from collect.ids import model_version_id
from collect.registry.seat import read_entry
from collect.registry.tracked_load import (
    LoadRefused,
    entry_fingerprint,
    load,
    plan,
    provisional_violations,
    read_manifest,
)
from tests.conftest import assert_disposable, assert_safe_target

MODEL = "anthropic/claude-opus-4.8"
OTHER = "anthropic/claude-opus-5"


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


def _registry_row(conn, canonical_id: str, *, provider: str = "anthropic") -> None:
    """One `model_version` row. Facts come from the registry, so it has to exist."""
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, sources, provenance) "
        "VALUES (%s, %s, %s, %s, 'polled')",
        (model_version_id(canonical_id), canonical_id, provider, "{}"),
    )
    conn.commit()


def _artifact(tmp_path, entries: str, *, floor: int = 20):
    path = tmp_path / "artifact.yaml"
    path.write_text(
        textwrap.dedent(
            f"""\
            policy:
              mention_floor: {floor}
              launch_window_days: 30
            proposals:
            """
        )
        + entries,
        encoding="utf-8",
    )
    return path


def _entry_block(canonical_id: str, surface: str, variants: list[str], *,
                 seated_by: str = "attested", incomplete: str = "family_surface",
                 mentions: int | None = None) -> str:
    note = f"        # attested {mentions} mentions [slice {mentions}]" if mentions else ""
    lines = [
        f"  - canonical_id: {canonical_id}",
        "    status: attested",
        f"    seated_by: {seated_by}",
        f"    surface: {surface}" + (f"{note}" if mentions else ""),
        "    variants:",
    ]
    lines += [f"      - {v}" for v in variants]
    lines.append(f"    incomplete: [{incomplete}]")
    return "\n".join(lines) + "\n"


def _manifest(tmp_path, artifact, ids: list[str], *, population: int | None = None,
              fingerprints: dict[str, str] | None = None):
    seats = {}
    for canonical_id in ids:
        seats[canonical_id] = (fingerprints or {}).get(
            canonical_id, entry_fingerprint(read_entry(canonical_id, artifact))
        )
    path = tmp_path / "reviewed-seats.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "artifact": artifact.name,
                "reviewed_at": "2026-08-20",
                "reviewed_by": "engineer-1",
                "population": population if population is not None else len(seats),
                "finding": "judgement group came back empty",
                "seats": seats,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_a_second_load_adds_a_family_surface_and_disturbs_nothing(conn, tmp_path):
    """**The confirmation, not the assumption.**

    The loader ships without family surfaces because `model_version.family` is
    NULL on every polled row and no derivation rule reproduces our own eleven. The
    question that decides whether that is a deferral or a dead end is whether the
    family surfaces can arrive LATER by the same path.

    They can, and the reason is the same append-only property that makes an undo
    impossible: `_sync_alias` closes a live row only when the same `normalized`
    resolves to a DIFFERENT row id. A brand-new surface shares no normalised form
    with an existing row, so it inserts beside them and nothing is touched.

    Asserted three ways, because "it worked" and "it did not damage anything" are
    different claims: the new row exists, the original row ids are unchanged, and
    every original row is still live (`valid_until IS NULL`).
    """
    _registry_row(conn, MODEL)

    first = _artifact(tmp_path, _entry_block(MODEL, "opus 4.8", ["opus-4.8", "claude 4.8"]))
    manifest = read_manifest(_manifest(tmp_path, first, [MODEL]))
    before = load(conn, manifest, artifact_path=first)
    conn.commit()

    original = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT id, valid_until FROM model_alias WHERE model_version_id = %s",
            (model_version_id(MODEL),),
        ).fetchall()
    }
    assert before.inserted == len(original) >= 3
    assert all(v is None for v in original.values())

    # The family surface arrives. Same entry, one more variant — so the review is
    # re-attested, which is the fingerprint working as designed rather than a
    # nuisance: the content changed.
    later = tmp_path / "later"
    later.mkdir()
    second = _artifact(
        later, _entry_block(MODEL, "opus 4.8", ["opus-4.8", "claude 4.8", "opus"])
    )
    reattested = read_manifest(_manifest(later, second, [MODEL]))

    after = load(conn, reattested, artifact_path=second)
    conn.commit()

    assert after.inserted == 1, "only the new surface should be written"
    assert after.replaced == 0, "an added surface must supersede nothing"
    assert after.unchanged == len(original), "every previously loaded row is unchanged"

    now = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT id, valid_until FROM model_alias WHERE model_version_id = %s",
            (model_version_id(MODEL),),
        ).fetchall()
    }
    assert set(original) < set(now), "the original rows must still be present by id"
    assert all(now[row_id] is None for row_id in original), (
        "adding a family surface must not close any existing row's window — a "
        "closed window asserts a surface stopped meaning a model"
    )
    families = conn.execute(
        "SELECT surface FROM model_alias WHERE model_version_id = %s AND specificity = 'family'",
        (model_version_id(MODEL),),
    ).fetchall()
    assert [r[0] for r in families] == ["opus"], "the new row is the family-specificity one"


def test_a_blocking_incomplete_slot_refuses_and_family_surface_does_not(conn, tmp_path):
    """`family_surface` is permanent by design; anything else means unfinished."""
    _registry_row(conn, MODEL)

    permitted = _artifact(tmp_path, _entry_block(MODEL, "opus 4.8", ["opus-4.8"]))
    assert not plan(conn, read_manifest(_manifest(tmp_path, permitted, [MODEL])),
                    artifact_path=permitted).refusals

    blocked_dir = tmp_path / "blocked"
    blocked_dir.mkdir()
    blocked = _artifact(
        blocked_dir,
        _entry_block(MODEL, "opus 4.8", ["opus-4.8"],
                     incomplete="family_surface, attested_surfaces"),
    )
    refusals = plan(
        conn, read_manifest(_manifest(blocked_dir, blocked, [MODEL])), artifact_path=blocked
    ).refusals
    assert any("attested_surfaces" in r for r in refusals)
    assert not any(r.strip().startswith("family_surface") for r in refusals)


def test_a_changed_entry_revokes_only_its_own_review(conn, tmp_path):
    """The fingerprint is per entry, so a drifted one does not invalidate the rest."""
    _registry_row(conn, MODEL)
    _registry_row(conn, OTHER)

    artifact = _artifact(
        tmp_path,
        _entry_block(MODEL, "opus 4.8", ["opus-4.8"])
        + _entry_block(OTHER, "opus 5", ["opus-5"]),
    )
    stale = entry_fingerprint(read_entry(MODEL, artifact)).replace("sha256:", "sha256:0")
    prepared = plan(
        conn,
        read_manifest(_manifest(tmp_path, artifact, [MODEL, OTHER],
                                fingerprints={MODEL: stale})),
        artifact_path=artifact,
    )

    assert len(prepared.refusals) == 1
    assert MODEL in prepared.refusals[0]
    assert "changed since it was reviewed" in prepared.refusals[0]
    assert [e.canonical_id for e in prepared.entries] == [OTHER], (
        "the entry that did not move is still planned"
    )


def test_two_entries_claiming_one_surface_refuse_before_any_write(conn, tmp_path):
    """The union collision check — the guard per-entry seating could never have."""
    _registry_row(conn, MODEL)
    _registry_row(conn, OTHER)

    artifact = _artifact(
        tmp_path,
        _entry_block(MODEL, "opus 4.8", ["opus"])
        + _entry_block(OTHER, "opus 5", ["opus"]),
    )
    prepared = plan(
        conn, read_manifest(_manifest(tmp_path, artifact, [MODEL, OTHER])),
        artifact_path=artifact,
    )

    assert any("claim one surface" in r for r in prepared.refusals)
    with pytest.raises(LoadRefused):
        load(conn, read_manifest(_manifest(tmp_path, artifact, [MODEL, OTHER])),
             artifact_path=artifact)
    assert conn.execute("SELECT count(*) FROM model_alias").fetchone()[0] == 0


def test_a_population_that_disagrees_with_itself_refuses(conn, tmp_path):
    """Rule 7 as a guard: a manifest edited by hand after the review."""
    _registry_row(conn, MODEL)
    artifact = _artifact(tmp_path, _entry_block(MODEL, "opus 4.8", ["opus-4.8"]))
    prepared = plan(
        conn, read_manifest(_manifest(tmp_path, artifact, [MODEL], population=41)),
        artifact_path=artifact,
    )
    assert any("declares population 41" in r for r in prepared.refusals)


def test_the_provisional_condition_fires_on_a_below_floor_seat_that_now_qualifies(tmp_path):
    """Engineer 2's condition, in library code rather than only in a test.

    No database: the condition reads the artifact. It is vacuous for entries
    seated by attestation, which is exactly why it is built now rather than on
    the day the launch-window entries are ruled on.
    """
    artifact = _artifact(
        tmp_path,
        _entry_block(MODEL, "opus 4.8", ["opus-4.8"], seated_by="launch-window",
                     mentions=38),
    )
    caught = provisional_violations(artifact)
    assert caught == [(MODEL, "opus 4.8", 38)]

    below_dir = tmp_path / "below"
    below_dir.mkdir()
    below = _artifact(
        below_dir,
        _entry_block(MODEL, "opus 4.8", ["opus-4.8"], seated_by="launch-window",
                     mentions=13),
    )
    assert provisional_violations(below) == [], (
        "13 mentions against a floor of 20 is seated exactly as the policy "
        "intends — a check that fires on a correct state gets muted"
    )
