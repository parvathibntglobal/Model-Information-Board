"""The seed models, from the host. The only place this module reads host data.

The seeds are the tracked TEXT models in `contract/tracked_models.yaml`
(Parvathi, 2026-10-22): image, audio and video models have no rows on the
Benchmarks page because none of its benchmarks measure them. The module never
creates, edits or deletes a host model (doc 0.3 rule 1); a model added to that
file shows up on the next run as a row with empty cells.
"""

from __future__ import annotations

from dataclasses import dataclass

import yaml

from collect.config import CONTRACT_DIR

TRACKED_MODELS = CONTRACT_DIR / "tracked_models.yaml"


@dataclass(frozen=True)
class SeedModel:
    id: str  # the registry id, e.g. "anthropic/claude-opus-5.5"
    name: str  # the display name, e.g. "Claude Opus 5.5"


def get_registry_aliases(conn, seeds: list[SeedModel]) -> dict[str, list[str]]:
    """The aliases the registry already holds for each seed (`model_alias`).

    Each alias's surface and its spelled-out variants, joined to the seed by its
    model_version's canonical id. An alias past its `valid_until` (e.g. "Astra"
    once a second Astra shipped) or before its `valid_from` is left out. A
    database without the registry tables gives no aliases, not an error.
    """
    ids = [s.id for s in seeds]
    try:
        rows = conn.execute(
            "SELECT mv.canonical_id, ma.surface, ma.variants FROM model_alias ma "
            "JOIN model_version mv ON mv.id = ma.model_version_id "
            "WHERE mv.canonical_id = ANY(%s) "
            "AND (ma.valid_until IS NULL OR ma.valid_until >= current_date) "
            "AND (ma.valid_from IS NULL OR ma.valid_from <= current_date)",
            (ids,),
        ).fetchall()
    except Exception:  # noqa: BLE001 - no registry here: the config aliases still apply
        conn.rollback() if not conn.autocommit else None
        return {}
    out: dict[str, list[str]] = {}
    for model_id, surface, variants in rows:
        names = out.setdefault(model_id, [])
        for name in [surface, *(variants or [])]:
            if name and name not in names:
                names.append(name)
    return out


def get_registry_models(conn) -> list[SeedModel]:
    """Every registry model that is NOT tracked (Parvathi, 2026-10-22 / 10-23).

    They get rows below the tracked models - only when a source lists them, never
    as empty rows - matched exactly like the tracked ones: by canonical id and
    display name, which already name one exact model and version, plus current
    aliases where the registry has them (48 of 247 models on 2026-10-22).

    The display name drops the "Provider: " prefix the router adds
    ("Anthropic: Claude Fable 5" -> "Claude Fable 5"). A database without the
    registry tables gives none.
    """
    raw = yaml.safe_load(TRACKED_MODELS.read_text(encoding="utf-8"))
    tracked = {entry["registry"] for entry in raw["models"] if entry.get("registry")}
    try:
        rows = conn.execute(
            "SELECT DISTINCT canonical_id, display_name FROM model_version ORDER BY canonical_id"
        ).fetchall()
    except Exception:  # noqa: BLE001 - no registry here: tracked models only
        conn.rollback() if not conn.autocommit else None
        return []
    out = []
    seen: set[str] = set()
    for canonical_id, display_name in rows:
        if canonical_id in tracked or not canonical_id or canonical_id in seen:
            continue
        seen.add(canonical_id)
        name = (display_name or canonical_id).split(": ", 1)[-1]
        out.append(SeedModel(id=canonical_id, name=name))
    return out


def get_seed_models() -> list[SeedModel]:
    """The tracked text models, in the file's order."""
    raw = yaml.safe_load(TRACKED_MODELS.read_text(encoding="utf-8"))
    seeds = []
    for entry in raw["models"]:
        if entry.get("kind") != "text" or not entry.get("registry"):
            continue
        seeds.append(SeedModel(id=entry["registry"], name=entry["name"]))
    return seeds
