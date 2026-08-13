"""The seed file parses, validates, and reports its own FR-2 gaps."""

from __future__ import annotations

import textwrap
from datetime import date

import pytest
import yaml
from pydantic import ValidationError

from collect.registry.models import SOURCED_FIELDS, SeedFile
from collect.registry.seed import (
    check_source_coverage,
    gaps_by_model,
    load_seed_file,
    seed_models,
    source_gaps,
)

MINIMAL = textwrap.dedent(
    """
    version: "1.0"
    provenance: seed
    models:
      - canonical_id: acme/widget-1
        provider: acme
        family: widget
        price_in: 1.0
        aliases:
          surface: "widget 1"
          variants: ["widget-1"]
        sources:
          price_in: {url: "https://acme.example/pricing", retrieved_at: "2026-08-12"}
    """
)


def _parse(text: str) -> SeedFile:
    return SeedFile.model_validate(yaml.safe_load(text))


# ── the real contract file ────────────────────────────────────────────────


def test_contract_seed_file_parses():
    seed = load_seed_file()
    assert seed.provenance == "seed"
    assert len(seed.models) == 11  # ten, plus mistral-large-3 for item 8


def test_every_model_has_aliases():
    for model in load_seed_file().models:
        assert model.aliases.surface.strip()
        assert model.aliases.variants


def test_month_precision_cutoffs_become_dates():
    """`knowledge_cutoff: 2026-05` is a month; the column is a date."""
    by_id = {m.canonical_id: m for m in load_seed_file().models}
    assert by_id["anthropic/claude-opus-5"].knowledge_cutoff == date(2026, 5, 1)


def test_same_family_group_is_present():
    """Three tiers of one line — the case that breaks entity resolution."""
    claude = [m for m in load_seed_file().models if m.family == "claude"]
    assert len(claude) >= 3


def test_fr2_is_satisfied():
    """Sign-off item 16, applied. Every populated field cites a provider page.

    This test used to assert the opposite: 90 fields were populated with no
    source at all. The 2026-08-13 sourcing pass either sourced a value or
    removed it, because a claim with no source is worse than an absence.
    """
    seed = load_seed_file()
    assert source_gaps(seed) == []
    assert gaps_by_model(seed) == {}


def test_every_source_is_a_provider_page():
    """Item 6's point. An aggregator citation is not progress over a blog."""
    for model in load_seed_file().models:
        for field, ref in model.sources.items():
            assert ref.provider_page, f"{model.canonical_id}.{field} cites a third party"


def test_strict_loading_now_succeeds():
    assert len(seed_models(strict=True)) == 11


def test_permissive_loading_returns_every_model():
    assert len(seed_models(strict=False)) == 11


# ── validation is strict on purpose ───────────────────────────────────────


def test_minimal_file_is_fully_sourced():
    check_source_coverage(_parse(MINIMAL))


def test_unknown_field_is_a_loud_error():
    """A typo must not be silently ignored — least of all in `sources`."""
    with pytest.raises(ValidationError):
        _parse(MINIMAL.replace("provider: acme", "provider: acme\n    colour: red"))


def test_sources_naming_a_non_field_is_rejected():
    broken = MINIMAL.replace("price_in: {url", "prince_in: {url")
    with pytest.raises(ValidationError):
        _parse(broken)


def test_duplicate_canonical_ids_are_rejected():
    doubled = _parse(MINIMAL).model_dump()
    doubled["models"].append(doubled["models"][0])
    with pytest.raises(ValidationError):
        SeedFile.model_validate(doubled)


def test_canonical_id_must_be_provider_slash_model():
    with pytest.raises(ValidationError):
        _parse(MINIMAL.replace("acme/widget-1", "widget-1"))


def test_unknown_lifecycle_is_rejected():
    with pytest.raises(ValidationError):
        _parse(MINIMAL.replace("provider: acme", "provider: acme\n    lifecycle: beta"))


def test_source_url_must_be_http():
    with pytest.raises(ValidationError):
        _parse(MINIMAL.replace("https://acme.example/pricing", "acme.example/pricing"))


def test_negative_price_is_rejected():
    with pytest.raises(ValidationError):
        _parse(MINIMAL.replace("price_in: 1.0", "price_in: -1.0"))


def test_populated_sourced_fields_ignores_identity_fields():
    model = _parse(MINIMAL).models[0]
    populated = model.populated_sourced_fields()
    assert populated == ["price_in"]
    assert "provider" not in SOURCED_FIELDS
