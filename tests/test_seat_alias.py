"""Seating a reviewed model from the tracked-set artifact.

The artifact had no consumer: the only writer of `model_alias` was `load_seed`
over `contract/seed_models.yaml`, a build fixture `assert_no_fixtures` refuses
outside development. So the reviewed list had no path into the database.

Mostly no database — what is under test is which entries the loader ACCEPTS and
which of five reasons it refuses on. `tests/test_registry_load_db.py` covers the
alias write path against a real Postgres. The exception is the last section
(#460): whether `seat-alias` reports what was WRITTEN needs a second seat
against a real table, on TEST_DATABASE_URL only.
"""

from __future__ import annotations

import pytest

from collect.registry.seat import (
    PERMANENT_INCOMPLETE,
    SeatRefused,
    read_entry,
)


def test_a_reviewed_entry_reads_back_with_its_surfaces():
    """Against the live artifact, not a fixture.

    A loader tested only on a hand-built document is tested against the shape
    its author had in mind — and this one parses prose, so the live file is the
    only honest input.
    """
    entry = read_entry("anthropic/claude-opus-4.8")

    assert entry.surface == "opus 4.8"
    assert "opus-4.8" in entry.variants
    assert "claudeopus4.8" in entry.variants
    assert len(entry.variants) >= 5
    assert entry.incomplete == (PERMANENT_INCOMPLETE,)
    assert entry.blocking_incomplete == (), (
        "family_surface is permanent by design and must not block a seat"
    )


def test_the_parse_still_finds_its_inputs():
    """Habit 4: a parse that silently matches nothing seats nothing and says OK.

    `to_yaml` writes mention counts into trailing comments, so this file is not
    round-trippable through yaml.safe_load and the patterns are anchored regexes.
    If the generator's format changes, this fails rather than every seat
    quietly finding no variants.
    """
    entry = read_entry("anthropic/claude-opus-4.8")
    assert entry.surface and not entry.surface.startswith("#")
    assert all(v and "#" not in v for v in entry.variants), entry.variants


def test_a_model_outside_the_tracked_set_is_refused_not_invented():
    """`openai/gpt-6-sol-pro` is in the FEED and not in the artifact.

    The registry poll inserted it on 2026-09-24 (#463) and nobody reviewed its
    surfaces, so seating it would mean inventing them - what the artifact exists
    to prevent.

    ⚠ THIS EXAMPLE WAS `anthropic/claude-fable-5` UNTIL #461, which seated it.
      An example of "not in the artifact" goes stale the day the artifact grows;
      if this one is ever seated, pick another the artifact does not list.
    """
    with pytest.raises(SeatRefused, match="not in alias-surfaces-tracked-set"):
        read_entry("openai/gpt-6-sol-pro")


def test_a_nonexistent_id_names_the_artifact_size_rather_than_shrugging():
    """A refusal that says "63 entries" tells the reader where to look."""
    with pytest.raises(SeatRefused) as refusal:
        read_entry("nobody/nothing-at-all")
    assert "entries" in str(refusal.value)
    assert "inventing them" in str(refusal.value)


def test_a_missing_artifact_refuses_with_the_command_that_writes_it(tmp_path):
    from pathlib import Path

    with pytest.raises(SeatRefused, match="propose-aliases"):
        read_entry("anthropic/claude-opus-4.8", Path(tmp_path / "absent.yaml"))


def test_an_incomplete_primary_surface_refuses(tmp_path):
    """`surface: INCOMPLETE` means nothing was observed naming the model.

    Every form under such an entry is a derivation, so the reviewer is supplying
    judgement rather than checking it — and the loader must not take that
    silently.
    """
    from pathlib import Path

    artifact = Path(tmp_path / "a.yaml")
    artifact.write_text(
        "proposals:\n"
        "  - canonical_id: x/y\n"
        "    status: mechanical-only\n"
        "    surface: INCOMPLETE   # no attested surface\n"
        "    variants:\n"
        "      - x-y\n"
        "    incomplete: [family_surface, attested_surfaces]\n",
        encoding="utf-8",
    )
    with pytest.raises(SeatRefused, match="no reviewed primary surface"):
        read_entry("x/y", artifact)


def test_a_blocking_incomplete_slot_refuses_the_seat(tmp_path):
    """Anything other than family_surface means the review is unfinished."""
    from pathlib import Path

    from collect.registry.seat import seat

    artifact = Path(tmp_path / "a.yaml")
    artifact.write_text(
        "proposals:\n"
        "  - canonical_id: x/y\n"
        "    surface: why 5\n"
        "    variants:\n"
        "      - why-5\n"
        "    incomplete: [family_surface, mechanical_variants]\n",
        encoding="utf-8",
    )

    class Conn:
        def execute(self, *a, **k):  # pragma: no cover - never reached
            raise AssertionError("refused before touching the database")

    with pytest.raises(SeatRefused, match="incomplete slot"):
        seat(Conn(), "x/y", path=artifact)


def test_a_model_absent_from_the_registry_refuses_before_writing(tmp_path):
    """An alias pointing at no model version is a foreign key waiting to happen."""
    from pathlib import Path

    from collect.registry.seat import seat

    artifact = Path(tmp_path / "a.yaml")
    artifact.write_text(
        "proposals:\n"
        "  - canonical_id: x/y\n"
        "    surface: why 5\n"
        "    variants:\n"
        "      - why-5\n"
        "    incomplete: [family_surface]\n",
        encoding="utf-8",
    )

    class Result:
        def fetchone(self):
            return None

    class Conn:
        def execute(self, *a, **k):
            return Result()

    with pytest.raises(SeatRefused, match="not in `model_version`"):
        seat(Conn(), "x/y", path=artifact)


# ── #460: seat-alias reports verdicts, not rows built ───────────────────────


def _report(verdicts):
    return {"canonical_id": "x/y", "surface": "why 5", "rows": len(verdicts),
            "searchable": len(verdicts), "verdicts": verdicts}


def test_all_unchanged_says_nothing_written_and_fails(capsys):
    from collect.cli import _report_seat

    assert _report_seat(_report(["unchanged", "unchanged"])) == 1
    out = capsys.readouterr().out
    assert "nothing written" in out
    assert "seated" not in out


def test_a_write_is_counted_per_verdict(capsys):
    from collect.cli import _report_seat

    assert _report_seat(_report(["inserted", "replaced", "unchanged"])) == 0
    out = capsys.readouterr().out
    assert "1 inserted, 1 replaced, 1 unchanged of 3" in out


def test_an_unknown_verdict_is_a_defect_not_a_count():
    from collect.cli import _report_seat

    with pytest.raises(RuntimeError, match="unknown verdict"):
        _report_seat(_report(["inserted", "skipped"]))


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


def test_a_second_seat_reports_nothing_written(conn, tmp_path, capsys):
    """GLM-5.3's shape: re-seating an already-seated model writes nothing, and
    the CLI said `seated ... 2 alias row(s)`."""
    from pathlib import Path

    from collect.cli import _report_seat
    from collect.ids import model_version_id
    from collect.registry.seat import seat

    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, sources, provenance) "
        "VALUES (%s, 'x/why-5', 'x', '{}', 'polled')",
        (model_version_id("x/why-5"),),
    )
    conn.commit()
    artifact = Path(tmp_path / "a.yaml")
    artifact.write_text(
        "proposals:\n"
        "  - canonical_id: x/why-5\n"
        "    surface: why 5\n"
        "    variants:\n"
        "      - why-5\n"
        "      - why5\n"
        "    incomplete: [family_surface]\n",
        encoding="utf-8",
    )

    first = seat(conn, "x/why-5", path=artifact)
    conn.commit()
    assert _report_seat(first) == 0
    assert "seated x/why-5" in capsys.readouterr().out

    second = seat(conn, "x/why-5", path=artifact)
    conn.commit()
    assert set(second["verdicts"]) == {"unchanged"}
    assert _report_seat(second) == 1
    assert "nothing written" in capsys.readouterr().out
