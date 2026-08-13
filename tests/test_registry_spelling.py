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


def test_no_model_is_missing_a_spelling():
    """Sign-off item 10, applied.

    `deepseek/deepseek-v4-flash` used to declare no concatenated form, so
    `deepseekv4flash` was unsearchable on the one fixture whose whole purpose
    is exercising the just-launched path. It also repeated its own surface in
    `variants`, declaring four distinct spellings rather than five.
    """
    assert spelling_gaps(_models()) == []


def test_all_ten_models_declare_all_three():
    complete = [
        m for m in _models() if spelling_styles(declared_surfaces(m)) == set(SPELLING_STYLES)
    ]
    assert len(complete) == 10


def test_the_seed_file_passes_the_check():
    check_spelling_coverage(_models())  # must not raise


def test_the_previously_missing_spelling_is_now_declared():
    """The specific string that was unfindable."""
    v4 = next(m for m in _models() if m.canonical_id == "deepseek/deepseek-v4-flash")
    assert "deepseekv4flash" in declared_surfaces(v4)


def test_a_model_missing_a_rendering_still_fails(monkeypatch):
    """The gate must keep working now that the real file passes it.

    Built from a model with its concatenated form removed, so the check is
    exercised rather than merely satisfied.
    """
    v4 = next(m for m in _models() if m.canonical_id == "deepseek/deepseek-v4-flash")
    crippled = v4.model_copy(
        update={
            "aliases": v4.aliases.model_copy(
                update={"variants": [s for s in v4.aliases.variants if s != "deepseekv4flash"]}
            )
        }
    )
    with pytest.raises(SpellingCoverageError, match="no concatenated form"):
        check_spelling_coverage([crippled])


def test_declared_surfaces_deduplicates():
    """Five distinct spellings now: the duplicated surface was replaced."""
    v4 = next(m for m in _models() if m.canonical_id == "deepseek/deepseek-v4-flash")
    surfaces = declared_surfaces(v4)
    assert len(surfaces) == len(set(surfaces))
    assert len(surfaces) == 5
