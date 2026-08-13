"""Alias normalisation, specificity and collisions.

The load-bearing case: a bare `sonnet` must resolve at family specificity.
If it ever resolves at snapshot, an engineer's comment lands on a tier they
never used, and a claim on the wrong snapshot is worse than no claim.
"""

from __future__ import annotations

from datetime import date

import pytest

from collect.registry.aliases import (
    AliasCollisionError,
    AliasRow,
    alias_rows,
    all_alias_rows,
    check_no_collisions,
    classify_specificity,
    find_collisions,
    intervals_overlap,
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


def test_alias_validity_tracks_the_model_lifecycle():
    """An alias is current for exactly as long as its model is.

    `valid_until` is the model's retirement date, which is what FR-4's
    time-awareness is for: `mistral large` meant mistral-large-2411 until it
    retired and means mistral-large-3 after. Without it the two windows
    overlap and the collision check correctly refuses the whole seed file.
    """
    for model in _models():
        for row in alias_rows(model):
            assert row.valid_from == model.release_date
            assert row.valid_until == model.retirement_date


def test_a_retired_models_aliases_are_closed():
    retired = next(m for m in _models() if m.lifecycle == "retired")
    assert all(row.valid_until is not None for row in alias_rows(retired))


def test_a_live_models_aliases_stay_open():
    live = next(m for m in _models() if m.lifecycle == "ga")
    assert all(row.valid_until is None for row in alias_rows(live))


def test_every_seeded_model_carries_a_family_level_alias():
    """Rule 5 of resolution — a version-less reply inherits from its thread —
    only pays off if the family surface exists to match in the first place."""
    for model in _models():
        specificities = {row.specificity for row in alias_rows(model)}
        assert "snapshot" in specificities, model.canonical_id


def test_the_seed_file_has_no_ambiguous_aliases():
    """§5 rule 4: ambiguous across models is dropped, not guessed at.

    In a hand-written contract file, an ambiguity is a mistake, so it must
    fail here, where someone can fix it.
    """
    assert find_collisions(all_alias_rows(_models())) == {}


# ── collisions are time-aware (FR-4) ──────────────────────────────────────


def _row(canonical_id: str, valid_from: date | None, valid_until: date | None) -> AliasRow:
    """A `-latest` alias row pointing at one model over one window."""
    return AliasRow(
        id=f"ma_{canonical_id}_{valid_from}",
        surface="gpt-latest",
        normalized="gptlatest",
        variants=["gpt-latest"],
        provider_hint="openai",
        model_version_id=f"mv_{canonical_id}",
        family="gpt",
        specificity="version",
        valid_from=valid_from,
        valid_until=valid_until,
        canonical_id=canonical_id,
    )


def test_disjoint_windows_are_not_a_collision():
    """The case FR-4 exists for: `latest` in March is not `latest` in June."""
    rows = [
        _row("openai/gpt-a", date(2026, 3, 1), date(2026, 6, 1)),
        _row("openai/gpt-b", date(2026, 6, 1), None),
    ]
    assert find_collisions(rows) == {}
    check_no_collisions(rows)  # must not raise


def test_overlapping_windows_still_raise():
    rows = [
        _row("openai/gpt-a", date(2026, 3, 1), date(2026, 7, 1)),
        _row("openai/gpt-b", date(2026, 6, 1), None),
    ]
    assert find_collisions(rows) == {"gptlatest": ["openai/gpt-a", "openai/gpt-b"]}
    with pytest.raises(AliasCollisionError, match="overlapping"):
        check_no_collisions(rows)


def test_two_open_ended_rows_collide():
    """Both still current is the ambiguity a naive append would create."""
    rows = [
        _row("openai/gpt-a", date(2026, 3, 1), None),
        _row("openai/gpt-b", date(2026, 6, 1), None),
    ]
    assert find_collisions(rows)


def test_one_model_across_two_windows_is_not_a_collision():
    """Append-only handover for a single model is not an ambiguity."""
    rows = [
        _row("openai/gpt-a", date(2026, 3, 1), date(2026, 6, 1)),
        _row("openai/gpt-a", date(2026, 6, 1), None),
    ]
    assert find_collisions(rows) == {}


@pytest.mark.parametrize(
    "a_from,a_until,b_from,b_until,expected",
    [
        # adjacent: one closes exactly as the next opens
        (date(2026, 1, 1), date(2026, 6, 1), date(2026, 6, 1), None, False),
        # overlapping by a day
        (date(2026, 1, 1), date(2026, 6, 2), date(2026, 6, 1), None, True),
        # contained
        (date(2026, 1, 1), date(2026, 12, 1), date(2026, 6, 1), date(2026, 7, 1), True),
        # both unbounded
        (None, None, None, None, True),
        # unknown start still overlaps a later open-ended window
        (None, date(2026, 6, 1), date(2026, 1, 1), None, True),
        # unknown start closed before the other opens
        (None, date(2026, 1, 1), date(2026, 6, 1), None, False),
    ],
)
def test_interval_overlap_rules(a_from, a_until, b_from, b_until, expected):
    assert intervals_overlap(a_from, a_until, b_from, b_until) is expected
    assert intervals_overlap(b_from, b_until, a_from, a_until) is expected  # symmetric


def test_alias_count_stays_inside_the_query_budget():
    """10 models x ~5 surfaces x 12 capabilities = 600 queries per platform."""
    for model in _models():
        assert len(alias_rows(model)) <= 9, model.canonical_id
