"""Seating a reviewed model from the tracked-set artifact.

The artifact had no consumer: the only writer of `model_alias` was `load_seed`
over `contract/seed_models.yaml`, a build fixture `assert_no_fixtures` refuses
outside development. So the reviewed list had no path into the database.

No database here — what is under test is which entries the loader ACCEPTS and
which of five reasons it refuses on. `tests/test_registry_load_db.py` covers the
alias write path against a real Postgres.
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
