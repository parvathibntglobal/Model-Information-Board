"""The seed file parses, validates, and reports its own FR-2 gaps."""

from __future__ import annotations

import textwrap
from datetime import date

import pytest
import yaml
from pydantic import ValidationError

from collect.registry.models import SOURCED_FIELDS, SeedFile
from collect.registry.seed import (
    SourceCoverageError,
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
    assert len(seed.models) == 10


def test_every_model_has_aliases():
    for model in load_seed_file().models:
        assert model.aliases.surface.strip()
        assert model.aliases.variants


def test_month_precision_cutoffs_become_dates():
    """`knowledge_cutoff: 2026-04` is a month; the column is a date."""
    by_id = {m.canonical_id: m for m in load_seed_file().models}
    assert by_id["anthropic/claude-opus-5"].knowledge_cutoff == date(2026, 4, 1)


def test_same_family_group_is_present():
    """Three tiers of one line — the case that breaks entity resolution."""
    claude = [m for m in load_seed_file().models if m.family == "claude"]
    assert len(claude) >= 3


def test_source_gaps_are_reported_not_hidden():
    """FR-2 is checkable without interpretation, and it currently fails.

    The seed file sources prices, context and release dates but not feature
    flags, cutoffs or lifecycle. That is a real gap, and this test pins it so
    it can only shrink.
    """
    seed = load_seed_file()
    gaps = source_gaps(seed)
    assert gaps, "if this passes, FR-2 is satisfied — tighten load_seed to strict"
    assert set(gaps_by_model(seed)) <= {m.canonical_id for m in seed.models}


def test_strict_loading_refuses_the_current_seed_file():
    with pytest.raises(SourceCoverageError):
        seed_models(strict=True)


def test_permissive_loading_still_returns_every_model():
    assert len(seed_models(strict=False)) == 10


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
