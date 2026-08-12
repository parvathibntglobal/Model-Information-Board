"""Alias normalisation, specificity and collisions.

The load-bearing case: a bare `sonnet` must resolve at family specificity.
If it ever resolves at snapshot, an engineer's comment lands on a tier they
never used, and a claim on the wrong snapshot is worse than no claim.
"""

from __future__ import annotations

from collect.registry.aliases import (
    alias_rows,
    all_alias_rows,
    classify_specificity,
    find_collisions,
    local_part,
    normalize,
    query_variants,
    tokenize,
)
from collect.registry.seed import load_seed_file


def _models():
    return load_seed_file().models


def _by_id():
    return {m.canonical_id: m for m in _models()}


# ── normalisation ─────────────────────────────────────────────────────────


def test_spelling_differences_normalise_together():
    assert normalize("GPT-4.1 mini") == normalize("gpt 4.1 mini") == normalize("gpt4.1mini")


def test_normalize_strips_punctuation_and_case():
    assert normalize("Claude-Opus-5") == "claudeopus5"


def test_tokenize_keeps_version_numbers_intact():
    assert tokenize("gpt-4.1 mini") == ["gpt", "4.1", "mini"]
    assert tokenize("claude opus 5") == ["claude", "opus", "5"]


def test_query_variants_are_mechanical_and_deduplicated():
    variants = query_variants("claude opus 5")
    assert variants == ["claude opus 5", "claude-opus-5", "claudeopus5"]


def test_query_variants_are_deterministic():
    assert query_variants("gemini 2.5 flash") == query_variants("gemini 2.5 flash")


def test_local_part():
    assert local_part("anthropic/claude-opus-5") == "claude-opus-5"


# ── specificity ───────────────────────────────────────────────────────────


def test_bare_family_name_is_family_specificity():
    sonnet = _by_id()["anthropic/claude-sonnet-5"]
    assert classify_specificity("sonnet", sonnet) == "family"
    assert classify_specificity("claude sonnet", sonnet) == "family"


def test_versioned_surface_is_version_specificity():
    sonnet = _by_id()["anthropic/claude-sonnet-5"]
    assert classify_specificity("sonnet 5", sonnet) == "version"


def test_canonical_id_is_snapshot_specificity():
    sonnet = _by_id()["anthropic/claude-sonnet-5"]
    assert classify_specificity("anthropic/claude-sonnet-5", sonnet) == "snapshot"
    assert classify_specificity("claude-sonnet-5", sonnet) == "snapshot"


def test_dated_snapshot_beats_the_bare_version():
    """`claude haiku 4.5` names a version; only the dated id names a snapshot."""
    haiku = _by_id()["anthropic/claude-haiku-4-5-20251001"]
    assert classify_specificity("claude haiku 4.5", haiku) == "version"
    assert classify_specificity("claude-haiku-4-5-20251001", haiku) == "snapshot"
    assert classify_specificity("haiku", haiku) == "family"


# ── rows ──────────────────────────────────────────────────────────────────


def test_canonical_id_always_gets_an_alias_row():
    """An exact mention must resolve even if the hand-written list omits it."""
    haiku = _by_id()["anthropic/claude-haiku-4-5-20251001"]
    keys = {row.normalized for row in alias_rows(haiku)}
    assert normalize(haiku.canonical_id) in keys
    assert normalize(local_part(haiku.canonical_id)) in keys


def test_alias_rows_are_deduplicated_by_normalised_form():
    for model in _models():
        keys = [row.normalized for row in alias_rows(model)]
        assert len(keys) == len(set(keys)), model.canonical_id


def test_alias_rows_are_deterministic():
    model = _models()[0]
    assert [r.id for r in alias_rows(model)] == [r.id for r in alias_rows(model)]


def test_alias_validity_starts_at_release():
    for model in _models():
        for row in alias_rows(model):
            assert row.valid_from == model.release_date
            assert row.valid_until is None  # still current


def test_every_seeded_model_carries_a_family_level_alias():
    """Rule 5 of resolution — a version-less reply inherits from its thread —
    only pays off if the family surface exists to match in the first place."""
    for model in _models():
        specificities = {row.specificity for row in alias_rows(model)}
        assert "snapshot" in specificities, model.canonical_id


def test_the_seed_file_has_no_ambiguous_aliases():
    """§5 rule 4: ambiguous across models is dropped, not guessed at.

    In a hand-written contract file, an ambiguity is a mistake — so it must
    fail here, where someone can fix it.
    """
    assert find_collisions(all_alias_rows(_models())) == {}


def test_alias_count_stays_inside_the_query_budget():
    """10 models x ~5 surfaces x 12 capabilities = 600 queries per platform."""
    for model in _models():
        assert len(alias_rows(model)) <= 9, model.canonical_id
