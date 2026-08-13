"""Item 18: tiered pricing, and the lowest-tier trap it exists to avoid.

`model_version.price_in` is NULL when tiers exist. It is NOT the lowest tier.
A lowest-tier fallback prices a frontier model at half its real long-context
rate, which §9 names as a false qualification: it wins recommendations it
should lose and nothing surfaces why.

No database needed except in the marked section.
"""

from __future__ import annotations

import textwrap
from decimal import Decimal

import pytest
import yaml
from pydantic import ValidationError

from collect.registry.models import PriceTier, SeedFile
from collect.registry.seed import load_seed_file, source_gaps, sourced_field_total

PRO = "google/gemini-2.5-pro"


def _models():
    return load_seed_file().models


def _pro():
    return next(m for m in _models() if m.canonical_id == PRO)


# ── the seed file ─────────────────────────────────────────────────────────


def test_the_tiered_model_declares_four_bands():
    tiers = _pro().price_tiers
    assert len(tiers) == 4
    assert {t.dimension for t in tiers} == {"input_tokens", "output_tokens"}


def test_the_tiered_model_carries_no_flat_price():
    """The whole point. A flat price beside tiers is the trap by the back door."""
    pro = _pro()
    assert pro.price_in is None
    assert pro.price_out is None


def test_the_bands_match_googles_published_figures():
    by_key = {(t.dimension, t.min_tokens): t for t in _pro().price_tiers}
    assert by_key[("input_tokens", 0)].price == Decimal("1.25")
    assert by_key[("input_tokens", 200000)].price == Decimal("2.50")
    assert by_key[("output_tokens", 0)].price == Decimal("10.00")
    assert by_key[("output_tokens", 200000)].price == Decimal("15.00")


def test_the_expensive_band_is_twice_the_cheap_one():
    """The 2x that makes a lowest-tier fallback a false qualification."""
    by_key = {(t.dimension, t.min_tokens): t for t in _pro().price_tiers}
    assert by_key[("input_tokens", 200000)].price == 2 * by_key[("input_tokens", 0)].price


def test_only_one_model_is_tiered_so_far():
    tiered = [m.canonical_id for m in _models() if m.price_tiers]
    assert tiered == [PRO]


# ── FR-2 reaches tier rows ────────────────────────────────────────────────


def test_tier_prices_count_toward_fr2():
    """A sourced value invisible to the provenance check is rule 6 in costume."""
    seed = load_seed_file()
    flat = sum(len(m.populated_sourced_fields()) for m in seed.models)
    total = sourced_field_total(seed)
    assert flat == 82
    assert total == 88  # 82 model_version fields + 6 tier fields
    assert source_gaps(seed) == []


def test_an_unsourced_tier_price_is_a_gap():
    """Otherwise tier rows would be a place provenance could hide."""
    seed = load_seed_file()
    pro = next(m for m in seed.models if m.canonical_id == PRO)
    pro.price_tiers[0].sources.pop("price")

    gaps = source_gaps(seed)
    assert len(gaps) == 1
    assert gaps[0].canonical_id == PRO
    assert gaps[0].field == "input_tokens[0-200000].price"


def test_the_gap_label_identifies_which_band():
    tier = PriceTier(dimension="input_tokens", min_tokens=200000, price=Decimal("2.50"))
    assert tier.label() == "input_tokens[200000+]"
    bounded = PriceTier(
        dimension="output_tokens", min_tokens=0, max_tokens=200000, price=Decimal("10")
    )
    assert bounded.label() == "output_tokens[0-200000]"


# ── validation refuses the ways this goes wrong ───────────────────────────


def _seed_with(tier_yaml: str, extra: str = "") -> SeedFile:
    text = textwrap.dedent(
        f"""
        version: "1.0"
        provenance: seed
        models:
          - canonical_id: acme/widget-1
            provider: acme
            {extra}
            aliases:
              surface: "widget 1"
              variants: ["widget-1", "widget1"]
            price_tiers:
        {textwrap.indent(textwrap.dedent(tier_yaml), " " * 14)}
        """
    )
    return SeedFile.model_validate(yaml.safe_load(text))


BOTH_DIMENSIONS = """
- dimension: input_tokens
  price: 1.0
  sources:
    price: {url: "https://acme.example/p", retrieved_at: "2026-08-13"}
- dimension: output_tokens
  price: 2.0
  sources:
    price: {url: "https://acme.example/p", retrieved_at: "2026-08-13"}
"""


def test_a_valid_tier_set_parses():
    seed = _seed_with(BOTH_DIMENSIONS)
    assert len(seed.models[0].price_tiers) == 2


def test_a_flat_price_beside_tiers_is_refused():
    with pytest.raises(ValidationError, match="not the lowest tier"):
        _seed_with(BOTH_DIMENSIONS, extra="price_in: 1.0")


def test_covering_only_one_dimension_is_refused():
    """A workload priced on input alone is half priced, which is worse than unpriced."""
    with pytest.raises(ValidationError, match="both input_tokens"):
        _seed_with(
            """
            - dimension: input_tokens
              price: 1.0
            """
        )


def test_a_duplicate_band_is_refused():
    with pytest.raises(ValidationError, match="duplicate price tier band"):
        _seed_with(
            """
            - dimension: input_tokens
              price: 1.0
            - dimension: input_tokens
              price: 2.0
            - dimension: output_tokens
              price: 3.0
            """
        )


def test_an_inverted_band_is_refused():
    with pytest.raises(ValidationError, match="band is empty"):
        PriceTier(
            dimension="input_tokens", min_tokens=200000, max_tokens=1000, price=Decimal("1")
        )


def test_a_negative_tier_price_is_refused():
    with pytest.raises(ValidationError):
        PriceTier(dimension="input_tokens", price=Decimal("-1"))


def test_an_unknown_dimension_is_refused():
    with pytest.raises(ValidationError):
        PriceTier(dimension="thinking_tokens", price=Decimal("1"))
