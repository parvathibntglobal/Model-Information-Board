"""Load and validate the seed registry.

`contract/seed_models.yaml` is a build fixture: ten hardcoded models so the
rest of the lane can be built before the OpenRouter poller exists. It is
replaced in week 5 by polling that writes into the same `model_version`
table, and `assert_no_fixtures()` refuses to start production while any
seeded row remains.

FR-2 applies to seeded rows exactly as it applies to polled ones: every
populated field that asserts something about a provider's product carries a
source URL and the date it was read.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from collect.config import SEED_MODELS_YAML
from collect.registry.models import SeedFile, SeedModel


@dataclass(frozen=True, order=True)
class SourceGap:
    """A populated field with no recorded provenance — an FR-2 violation."""

    canonical_id: str
    field: str

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.canonical_id}.{self.field}"


class SourceCoverageError(ValueError):
    """Fields assert a value without saying where it came from (FR-2)."""

    def __init__(self, gaps: list[SourceGap]) -> None:
        self.gaps = gaps
        listed = ", ".join(str(gap) for gap in gaps[:8])
        more = f" (+{len(gaps) - 8} more)" if len(gaps) > 8 else ""
        super().__init__(
            f"{len(gaps)} field(s) populated with no source: {listed}{more}. "
            "FR-2 requires a URL and a retrieval date for every registry field, "
            "and it applies to seeded rows too."
        )


def load_seed_file(path: Path | None = None) -> SeedFile:
    """Parse and validate the seed YAML. Raises on any malformed row."""
    path = path or SEED_MODELS_YAML
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} does not contain a YAML mapping")
    return SeedFile.model_validate(raw)


def source_gaps(seed: SeedFile) -> list[SourceGap]:
    """Every populated-but-unsourced field across the file, sorted.

    Walks `price_tier` rows as well as `model_version` fields. FR-2's wording
    is "every populated field on any `model_version` row", so tier rows sit
    outside the requirement as written — a gap in the requirement rather than
    in the data. Checking them anyway is the only option that leaves
    provenance one place to live: a sourced tier price the checker cannot see
    is a value that exists and is invisible to the thing auditing it.
    """
    gaps = [
        SourceGap(model.canonical_id, field)
        for model in seed.models
        for field in model.populated_sourced_fields()
        if field not in model.sources
    ]
    gaps += [
        SourceGap(model.canonical_id, f"{tier.label()}.{field}")
        for model in seed.models
        for tier in model.price_tiers
        for field in tier.populated_sourced_fields()
        if field not in tier.sources
    ]
    return sorted(gaps)


def sourced_field_total(seed: SeedFile) -> int:
    """How many populated sourceable fields exist, tiers included.

    The denominator of the FR-2 figure. Exposed so the CLI and the docs quote
    the same number from the same place.
    """
    return sum(
        len(model.populated_sourced_fields())
        + sum(len(tier.populated_sourced_fields()) for tier in model.price_tiers)
        for model in seed.models
    )


def check_source_coverage(seed: SeedFile) -> None:
    """Raise unless every populated sourceable field cites a source."""
    gaps = source_gaps(seed)
    if gaps:
        raise SourceCoverageError(gaps)


def gaps_by_model(seed: SeedFile) -> dict[str, list[str]]:
    """Source gaps grouped for reporting on the coverage surface."""
    grouped: dict[str, list[str]] = {}
    for gap in source_gaps(seed):
        grouped.setdefault(gap.canonical_id, []).append(gap.field)
    return grouped


def seed_models(path: Path | None = None, *, strict: bool = True) -> list[SeedModel]:
    """The seeded models, optionally without enforcing FR-2.

    `strict=False` exists for one reason: the seed file ships with known
    provenance gaps, and blocking every other stage on filling them by hand
    would be worse than carrying a visible, reported gap. It is never a
    default, and `collect.registry.load` records the gaps it loaded under.
    """
    seed = load_seed_file(path)
    if strict:
        check_source_coverage(seed)
    return seed.models
