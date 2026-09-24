"""Tombstoned models: canonical ids the registry must not re-create.

A deleted `provenance='polled'` model does not stay deleted on its own. The
OpenRouter poll upserts every model the catalogue lists, so the next poll
re-inserts it as a new row with no history. `contract/tombstoned_models.yaml`
names the ids that were deleted on purpose, and this module is the one reader.

LOUD ON A BAD FILE, rule 12. A tombstone list that fails to load and quietly
becomes empty is the exact failure it exists to prevent - the deletion would
undo itself and nothing would say so. So a missing file, a malformed entry or a
duplicate raises; only a file that exists and lists nothing is an empty set.

REPORTED, NEVER SILENT. `apply_tombstones` returns what it dropped, and the
poll stage puts the count on its line. A poll that skipped models without
saying so would read as a catalogue that had stopped listing them.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TOMBSTONES = ROOT / "contract" / "tombstoned_models.yaml"


class TombstoneFileError(ValueError):
    """The tombstone file is missing or malformed. Never read as empty."""


class TombstonedModel(ValueError):
    """A write path was asked to create a model that was deleted on purpose."""


def load_tombstones(path: Path | None = None) -> frozenset[str]:
    """The tombstoned canonical ids. Raises rather than returning an empty set."""
    target = path or TOMBSTONES
    if not target.exists():
        raise TombstoneFileError(
            f"{target} does not exist. A missing tombstone file would let the "
            f"poll re-create every deliberately deleted model, so this refuses."
        )
    doc = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    entries = doc.get("tombstoned")
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        raise TombstoneFileError(f"`tombstoned` in {target} is not a list")
    ids: list[str] = []
    for i, entry in enumerate(entries):
        cid = entry.get("canonical_id") if isinstance(entry, dict) else None
        if not isinstance(cid, str) or not cid.strip():
            raise TombstoneFileError(f"entry {i} in {target} has no canonical_id")
        ids.append(cid.strip())
    dupes = sorted({c for c in ids if ids.count(c) > 1})
    if dupes:
        raise TombstoneFileError(f"duplicate tombstones in {target}: {dupes}")
    return frozenset(ids)


def apply_tombstones(result, tombstoned: frozenset[str]):
    """`(PollResult without tombstoned models, the canonical ids dropped)`.

    Matching is on `PolledModel.canonical_id`, which `parse_models` has already
    reduced to the base id, so a tombstone covers the model's service tiers.
    """
    kept = tuple(m for m in result.models if m.canonical_id not in tombstoned)
    dropped = tuple(sorted(m.canonical_id for m in result.models
                           if m.canonical_id in tombstoned))
    return replace(result, models=kept), dropped


def refuse_if_tombstoned(canonical_id: str, tombstoned: frozenset[str] | None = None) -> None:
    """For hand-insert paths: raise if `canonical_id` was deleted on purpose."""
    stones = load_tombstones() if tombstoned is None else tombstoned
    if canonical_id in stones:
        raise TombstonedModel(
            f"{canonical_id} is tombstoned in contract/tombstoned_models.yaml: it "
            f"was deleted on purpose. Remove its entry there (a PR) before "
            f"re-creating it; the re-created row will carry no history."
        )
