"""The shape of `contract/seed_models.yaml`.

Strict on purpose. `extra="forbid"` means a typo in the seed file is a loud
parse error rather than a silently-ignored field — which for a `sources`
block would silently disable the FR-2 guarantee it exists to provide.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

#: Fields on `model_version` that are assertions about a provider's product,
#: and therefore need a source URL and a retrieval date (FR-2). Identity and
#: bookkeeping fields — canonical_id, provider, family, provenance — are not
#: claims about the world and are excluded.
SOURCED_FIELDS: tuple[str, ...] = (
    "release_date",
    "deprecation_date",
    "retirement_date",
    "lifecycle",
    "advertised_context",
    "max_output_tokens",
    "knowledge_cutoff",
    "price_in",
    "price_out",
    "price_cached_read",
    "batch_discount",
    "supports_tools",
    "supports_structured_output",
    "supports_vision",
    "supports_caching",
    "supports_batch",
    "regions",
)

LIFECYCLES = ("preview", "ga", "deprecated", "retired")

_CANONICAL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9.\-]*/[a-z0-9][a-z0-9.\-]*$")
_YEAR_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


def _coerce_partial_date(value: Any) -> Any:
    """Accept ``2026-04`` where a date is wanted, meaning the 1st of April.

    Knowledge cutoffs are published to the month. The column is a `date`, so
    the day has to come from somewhere; the first of the month is the only
    non-arbitrary choice, and it never overstates recency.
    """
    if isinstance(value, str):
        match = _YEAR_MONTH_RE.match(value.strip())
        if match:
            return date(int(match.group(1)), int(match.group(2)), 1)
    return value


class SourceRef(BaseModel):
    """Where a field came from and when it was read (FR-2)."""

    model_config = ConfigDict(extra="forbid")

    url: str
    retrieved_at: date

    #: False when the value was read off a third party rather than the
    #: provider's own page. Third-party prices go stale silently, so a cost
    #: estimate built on one decays without any signal.
    #:
    #: Replaces a bare `#` at end of line in the YAML, which carried the same
    #: meaning but which no loader could read — and which had already drifted
    #: out of agreement with the URLs it annotated.
    provider_page: bool = True

    @field_validator("url")
    @classmethod
    def _http_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"source url must be http(s): {v!r}")
        return v


class AliasSpec(BaseModel):
    """How humans write this model's name."""

    model_config = ConfigDict(extra="forbid")

    surface: str
    variants: list[str] = Field(default_factory=list)

    @field_validator("surface")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("alias surface must not be blank")
        return v

    @field_validator("variants")
    @classmethod
    def _no_blank_variants(cls, v: list[str]) -> list[str]:
        if any(not item.strip() for item in v):
            raise ValueError("alias variants must not contain blanks")
        return v


class PriceTier(BaseModel):
    """One band of a tiered price (item 18).

    Providers that charge by input length cannot be expressed by a single
    numeric. Gemini 2.5 Pro is $1.25/$10.00 at or below 200k input tokens and
    $2.50/$15.00 above it.

    `model_version.price_in` / `price_out` are NULL when tiers exist. They are
    not the lowest tier: a lowest-tier fallback prices a frontier model at half
    its real long-context rate, which is a false qualification that reads as
    plausible.
    """

    model_config = ConfigDict(extra="forbid")

    dimension: Literal["input_tokens", "output_tokens"]
    min_tokens: int = 0
    max_tokens: int | None = None
    price: Decimal
    price_cached_read: Decimal | None = None
    sources: dict[str, SourceRef] = Field(default_factory=dict)

    @field_validator("price", "price_cached_read")
    @classmethod
    def _non_negative(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("tier prices must not be negative")
        return v

    @model_validator(mode="after")
    def _band_is_ordered(self) -> PriceTier:
        if self.max_tokens is not None and self.max_tokens <= self.min_tokens:
            raise ValueError(
                f"tier band is empty: max_tokens {self.max_tokens} "
                f"must exceed min_tokens {self.min_tokens}"
            )
        return self

    def populated_sourced_fields(self) -> list[str]:
        """Sourceable fields this tier asserts a value for.

        FR-2's wording covers "every populated field on any `model_version`
        row", so a tier row sits outside the requirement as written. It is
        checked anyway: the alternative is provenance with a second place to
        hide, which is rule 6 in a different costume.
        """
        return [
            name
            for name in ("price", "price_cached_read")
            if getattr(self, name, None) is not None
        ]

    def label(self) -> str:
        """Identifies this tier in a coverage report."""
        upper = "+" if self.max_tokens is None else f"-{self.max_tokens}"
        return f"{self.dimension}[{self.min_tokens}{upper}]"


class SeedModel(BaseModel):
    """One row of `contract/seed_models.yaml`."""

    model_config = ConfigDict(extra="forbid")

    canonical_id: str
    provider: str
    family: str | None = None
    display_name: str | None = None

    #: Seed-file bookkeeping only — records why this model is in the ten.
    #: Not a `model_version` column and never written to the database.
    slot: str | None = None

    lifecycle: str | None = None
    release_date: date | None = None
    deprecation_date: date | None = None
    retirement_date: date | None = None

    advertised_context: int | None = None
    max_output_tokens: int | None = None
    knowledge_cutoff: date | None = None

    price_in: Decimal | None = None
    price_out: Decimal | None = None
    price_cached_read: Decimal | None = None
    batch_discount: Decimal | None = None

    supports_tools: bool | None = None
    supports_structured_output: bool | None = None
    supports_vision: bool | None = None
    supports_caching: bool | None = None
    supports_batch: bool | None = None
    regions: list[str] | None = None

    #: Item 18. When present, `price_in` and `price_out` MUST be absent: they
    #: are not the lowest tier. Enforced below.
    price_tiers: list[PriceTier] = Field(default_factory=list)

    aliases: AliasSpec
    sources: dict[str, SourceRef] = Field(default_factory=dict)

    @field_validator("knowledge_cutoff", "release_date", "deprecation_date", mode="before")
    @classmethod
    def _month_precision(cls, v: Any) -> Any:
        return _coerce_partial_date(v)

    @field_validator("canonical_id")
    @classmethod
    def _canonical_shape(cls, v: str) -> str:
        if not _CANONICAL_ID_RE.match(v):
            raise ValueError(f"canonical_id must look like 'provider/model': {v!r}")
        return v

    @field_validator("lifecycle")
    @classmethod
    def _known_lifecycle(cls, v: str | None) -> str | None:
        if v is not None and v not in LIFECYCLES:
            raise ValueError(f"lifecycle must be one of {LIFECYCLES}: {v!r}")
        return v

    @field_validator("price_in", "price_out", "price_cached_read")
    @classmethod
    def _non_negative(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("prices must not be negative")
        return v

    @field_validator("advertised_context", "max_output_tokens")
    @classmethod
    def _positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("token counts must be positive")
        return v

    @field_validator("sources")
    @classmethod
    def _sources_name_real_fields(cls, v: dict[str, SourceRef]) -> dict[str, SourceRef]:
        unknown = sorted(set(v) - set(SOURCED_FIELDS))
        if unknown:
            raise ValueError(
                f"sources names fields that carry no provenance requirement: {unknown}. "
                f"Sourceable fields are {list(SOURCED_FIELDS)}"
            )
        return v

    @model_validator(mode="after")
    def _tiers_replace_flat_prices(self) -> SeedModel:
        """A tiered model must not also carry a flat price.

        Carrying both is how the lowest-tier trap gets in by the back door:
        one of the two values is wrong, and the flat one is the one every
        caller reads by default.
        """
        if not self.price_tiers:
            return self
        clashing = [
            name
            for name in ("price_in", "price_out")
            if getattr(self, name, None) is not None
        ]
        if clashing:
            raise ValueError(
                f"{self.canonical_id}: {clashing} must be absent when price_tiers "
                "are declared. They are not the lowest tier, and a caller that "
                "reads them instead of the tiers prices the model wrongly."
            )
        dimensions = [t.dimension for t in self.price_tiers]
        bands = [(t.dimension, t.min_tokens) for t in self.price_tiers]
        if len(bands) != len(set(bands)):
            raise ValueError(f"{self.canonical_id}: duplicate price tier band")
        if "input_tokens" not in dimensions or "output_tokens" not in dimensions:
            raise ValueError(
                f"{self.canonical_id}: price_tiers must cover both input_tokens "
                "and output_tokens, or a workload can only be half priced"
            )
        return self

    @model_validator(mode="after")
    def _release_before_deprecation(self) -> SeedModel:
        if (
            self.release_date
            and self.deprecation_date
            and self.deprecation_date < self.release_date
        ):
            raise ValueError(f"{self.canonical_id}: deprecated before it was released")
        return self

    def populated_sourced_fields(self) -> list[str]:
        """Sourceable fields this row actually asserts a value for."""
        return [f for f in SOURCED_FIELDS if getattr(self, f, None) is not None]


class SeedFile(BaseModel):
    """The whole of `contract/seed_models.yaml`."""

    model_config = ConfigDict(extra="forbid")

    version: str
    provenance: Literal["seed"]
    models: list[SeedModel]

    @model_validator(mode="after")
    def _canonical_ids_unique(self) -> SeedFile:
        seen: dict[str, int] = {}
        for model in self.models:
            seen[model.canonical_id] = seen.get(model.canonical_id, 0) + 1
        duplicates = sorted(cid for cid, n in seen.items() if n > 1)
        if duplicates:
            raise ValueError(f"duplicate canonical_id in seed file: {duplicates}")
        return self
