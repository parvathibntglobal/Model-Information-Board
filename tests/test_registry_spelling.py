"""Declared spelling coverage.

Search APIs have no fuzzy operator, so `gpt-4.1-mini` and `gpt 4.1 mini` are
different literal queries that match different posts. Breadth used to come
from mechanical expansion; Task 6 moved it to the hand-written variant list
in `contract/`. This is what stops that being an unchecked promise.

A missing spelling produces no error at harvest. It produces silence, which
renders identically to nobody having discussed the model.
"""

from __future__ import annotations

import pytest

from collect.registry.aliases import (
    SPELLING_STYLES,
    SpellingCoverageError,
    check_spelling_coverage,
    declared_surfaces,
    spelling_gaps,
    spelling_styles,
)
from collect.registry.seed import load_seed_file


def _models():
    return load_seed_file().models


# ── the style detector ────────────────────────────────────────────────────


def test_all_three_styles_detected():
    assert spelling_styles(["claude opus 5", "claude-opus-5", "claudeopus5"]) == set(
        SPELLING_STYLES
    )


def test_a_bare_family_name_is_not_a_concatenated_form():
    """`opus` is a family name, not `opus 5` run together.

    Counting it would mean a model passes the check while `claudeopus5`
    remains unsearchable, which is the exact failure this guards against.
    """
    assert "concatenated" not in spelling_styles(["claude opus 5", "claude-opus-5", "opus"])


def test_concatenation_is_matched_against_a_separated_form():
    assert "concatenated" in spelling_styles(["opus 5", "opus5"])


def test_a_dot_does_not_count_as_a_separator():
    """`haiku4.5` is the concatenation of `haiku 4.5`; people write it."""
    assert "concatenated" in spelling_styles(["haiku 4.5", "haiku4.5"])


def test_hyphen_and_space_are_detected_independently():
    assert spelling_styles(["gemini 2.5 pro"]) == {"spaced"}
    assert spelling_styles(["gemini-2.5-pro"]) == {"hyphenated"}


# ── against the real seed file ────────────────────────────────────────────


def test_exactly_one_model_is_missing_a_spelling():
    """Sign-off item 10, pinned.

    `deepseek/deepseek-v4-flash` declares no concatenated form, so
    `deepseekv4flash` is unsearchable on the one fixture whose whole purpose
    is exercising the just-launched path. This is a contract fix, not a code
    one, and it must not be closed by editing the seed file from this lane.
    """
    gaps = spelling_gaps(_models())
    assert [g.canonical_id for g in gaps] == ["deepseek/deepseek-v4-flash"]
    assert gaps[0].missing == ("concatenated",)


def test_nine_of_ten_models_declare_all_three():
    complete = [
        m for m in _models() if spelling_styles(declared_surfaces(m)) == set(SPELLING_STYLES)
    ]
    assert len(complete) == 9


def test_the_seed_file_currently_fails_the_check():
    with pytest.raises(SpellingCoverageError, match="deepseek-v4-flash"):
        check_spelling_coverage(_models())


def test_the_error_says_which_rendering_is_missing():
    with pytest.raises(SpellingCoverageError, match="no concatenated form"):
        check_spelling_coverage(_models())


def test_a_complete_seed_file_passes():
    models = [m for m in _models() if m.canonical_id != "deepseek/deepseek-v4-flash"]
    check_spelling_coverage(models)


def test_declared_surfaces_deduplicates():
    """`deepseek v4 flash` is declared twice: once as surface, once as variant."""
    v4 = next(m for m in _models() if m.canonical_id == "deepseek/deepseek-v4-flash")
    surfaces = declared_surfaces(v4)
    assert len(surfaces) == len(set(surfaces))
    assert len(surfaces) == 4  # five declared, one a duplicate of the surface
