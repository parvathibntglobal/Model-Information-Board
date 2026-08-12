"""Alias rows: how a human's words become a model_version.

Two jobs, deliberately separated (§5, "broad on retrieval, strict on
attribution"):

  RETRIEVAL   search must find `claude-opus-5`, `claude opus 5` and
              `claudeopus5`. Neither the GitHub nor the Reddit search API has
              a fuzzy operator, so breadth comes from precomputing spelling
              variants and issuing each as its own query.

  ATTRIBUTION strict, time-aware matching against the canonical table. A
              claim filed against the wrong snapshot is worse than no claim.

Specificity is the field that keeps attribution honest. A bare "sonnet"
resolves at `family` and never counts as independent corroboration, because
it does not say which tier the engineer was using.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from collect.ids import model_alias_id, model_version_id
from collect.registry.models import SeedModel

#: Splits a surface into meaningful tokens. Dots survive, because `4.1` is
#: one version token and splitting it into `4` and `1` invents two.
_TOKEN_SPLIT = re.compile(r"[^0-9a-z.]+")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")
_HAS_DIGIT = re.compile(r"\d")

SPECIFICITIES = ("snapshot", "version", "family")


def normalize(surface: str) -> str:
    """Lowercase, punctuation stripped — the matching key.

    `GPT-4.1 mini`, `gpt 4.1 mini` and `gpt4.1mini` all normalise to
    `gpt41mini`, so they are one alias rather than three.
    """
    return _NON_ALNUM.sub("", surface.casefold())


def tokenize(surface: str) -> list[str]:
    """Version-preserving tokens: `gpt-4.1 mini` → ['gpt', '4.1', 'mini']."""
    return [tok for tok in _TOKEN_SPLIT.split(surface.casefold()) if tok]


def query_variants(surface: str) -> list[str]:
    """Deterministic spelling variants of one surface, for search queries.

    Mechanical only — spacing, hyphenation, concatenation. No invented
    misspellings: everything a human might plausibly type that is *not*
    derivable this way belongs in `contract/seed_models.yaml`, where it is
    versioned and reviewable (rule 5).
    """
    tokens = tokenize(surface)
    if not tokens:
        return []
    forms = [
        surface.strip(),
        " ".join(tokens),
        "-".join(tokens),
        "".join(tokens),
        normalize(surface),
    ]
    return _dedupe(forms)


def _dedupe(items: list[str]) -> list[str]:
    """Order-preserving deduplication."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def local_part(canonical_id: str) -> str:
    """`anthropic/claude-opus-5` → `claude-opus-5`."""
    return canonical_id.split("/")[-1]


def classify_specificity(surface: str, model: SeedModel) -> str:
    """How precisely this surface names a model.

        snapshot  it is the canonical id, or the model id inside it
        version   it carries a version token — `sonnet 5`, `flash 2.5`
        family    it carries none — a bare `sonnet` names a line, not a tier

    The family case is the one that matters. `sonnet` is deliberately in the
    seed file: it must resolve at family specificity, never snapshot, or an
    engineer's comment lands on a tier they never used.
    """
    key = normalize(surface)
    if key in {normalize(model.canonical_id), normalize(local_part(model.canonical_id))}:
        return "snapshot"
    if _HAS_DIGIT.search(key):
        return "version"
    return "family"


@dataclass(frozen=True)
class AliasRow:
    """One `model_alias` row. Append-only once written (FR-4)."""

    id: str
    surface: str
    normalized: str
    variants: list[str]
    provider_hint: str | None
    model_version_id: str
    family: str | None
    specificity: str
    valid_from: date | None
    valid_until: date | None = None
    confidence: float = 1.0
    canonical_id: str = field(default="", compare=False)


def alias_rows(model: SeedModel) -> list[AliasRow]:
    """Every alias for one seeded model, deduplicated by normalised form.

    The canonical id and its local part are always included, so an exact
    mention always resolves at snapshot specificity even when the hand-written
    surface list omits it.
    """
    mv_id = model_version_id(model.canonical_id)
    valid_from = model.release_date
    surfaces = [
        model.canonical_id,
        local_part(model.canonical_id),
        model.aliases.surface,
        *model.aliases.variants,
    ]

    rows: list[AliasRow] = []
    seen: set[str] = set()
    for surface in surfaces:
        surface = surface.strip()
        key = normalize(surface)
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(
            AliasRow(
                id=model_alias_id(key, mv_id, valid_from.isoformat() if valid_from else ""),
                surface=surface,
                normalized=key,
                variants=query_variants(surface),
                provider_hint=model.provider,
                model_version_id=mv_id,
                family=model.family,
                specificity=classify_specificity(surface, model),
                valid_from=valid_from,
                valid_until=None,
                confidence=1.0,
                canonical_id=model.canonical_id,
            )
        )
    return rows


def all_alias_rows(models: list[SeedModel]) -> list[AliasRow]:
    return [row for model in models for row in alias_rows(model)]


class AliasCollisionError(ValueError):
    """One surface points at more than one model.

    §5 rule 4: a mention ambiguous across models is dropped, not guessed at.
    In a hand-written contract file an ambiguous alias is a mistake, so it
    fails at load time where someone can fix it — rather than at resolution
    time, where it would quietly drop evidence.
    """

    def __init__(self, collisions: dict[str, list[str]]) -> None:
        self.collisions = collisions
        listed = "; ".join(f"{key!r} → {sorted(ids)}" for key, ids in sorted(collisions.items()))
        super().__init__(f"alias surfaces resolve to more than one model: {listed}")


def find_collisions(rows: list[AliasRow]) -> dict[str, list[str]]:
    """Normalised surfaces claimed by more than one model."""
    owners: dict[str, set[str]] = {}
    for row in rows:
        owners.setdefault(row.normalized, set()).add(row.canonical_id)
    return {key: sorted(ids) for key, ids in owners.items() if len(ids) > 1}


def check_no_collisions(rows: list[AliasRow]) -> None:
    collisions = find_collisions(rows)
    if collisions:
        raise AliasCollisionError(collisions)
