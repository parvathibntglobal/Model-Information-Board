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


def test_every_model_declares_all_three():
    models = _models()
    complete = [
        m for m in models if spelling_styles(declared_surfaces(m)) == set(SPELLING_STYLES)
    ]
    assert len(complete) == len(models) == 11


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


# ── #33: three, counted as renderings ─────────────────────────────────────


def _renderings(local_part: str) -> list[str]:
    """The three renderings of an id, with no filtering of any kind.

    Deliberately not `propose.mechanical_variants`: that drops forms under four
    characters, and this test is about what the FLOOR can ask for, not about what
    the proposer offers.
    """
    spaced = local_part.replace("-", " ").replace("_", " ")
    return [spaced, spaced.replace(" ", "-"), spaced.replace(" ", "")]


@pytest.mark.parametrize(
    "canonical_id",
    [
        "anthropic/claude-opus-5",
        "openai/gpt-4.1-mini",
        "deepseek/deepseek-v4-flash",
        "anthropic/claude-haiku-4-5-20251001",
        "openai/gpt-5",  # two tokens is enough
        "z-ai/glm-5v-turbo",  # nobody has been observed discussing it
    ],
)
def test_the_floor_is_always_satisfiable_from_the_id_alone(canonical_id):
    """The property that makes it fair to fail a load over.

    A model failing this gate is fixed by rendering its own id three ways. Never
    by inventing a spelling somebody might type — which is what a floor counting
    attested surfaces would have demanded of 55 of the 72 models the corpus
    discusses, and why #33 refused it.
    """
    local_part = canonical_id.split("/")[-1]
    assert spelling_styles(_renderings(local_part)) == set(SPELLING_STYLES)


def test_a_single_token_id_is_the_one_shape_the_floor_cannot_derive():
    """The boundary on "always satisfiable", stated rather than assumed.

    A single-token local part has no separator to vary, so it has no spaced or
    hyphenated rendering and satisfying the floor would mean choosing where to
    break the word — judgement, which is what the ruling relies on not needing.

    Counted against the registry slice: **1 of the 155 ids**, and it is
    `openrouter/auto`, which names a router rather than a model. So the ruling
    holds for every real model in the slice, and the exception is a shape the
    alias floor should never see.
    """
    assert spelling_styles(_renderings("auto")) == set()


def test_the_floor_counts_renderings_and_not_attestations():
    """`claude opus 5` is measured at 0 mentions over 5,546 documents.

    It still satisfies the spaced rendering, because findability and usage are
    different questions. The gate reads string shape; it has no route to a
    mention count, and this is the test that says so on purpose.
    """
    opus = next(m for m in _models() if m.canonical_id == "anthropic/claude-opus-5")
    unattested_only = opus.model_copy(
        update={
            "aliases": opus.aliases.model_copy(
                update={
                    "surface": "claude opus 5",  # 0 mentions, measured
                    "variants": ["claude-opus-5", "claudeopus5"],  # also unattested
                }
            )
        }
    )
    check_spelling_coverage([unattested_only])  # must not raise
    assert spelling_gaps([unattested_only]) == []


def test_the_family_surface_does_not_gate():
    """Required-but-INCOMPLETE-able, not a condition of load.

    A bare `opus` is attested constantly and attributable to no single model, so a
    gate demanding one could only be satisfied by asserting an attribution the
    data refuses. `propose.py` keeps it as a permanent INCOMPLETE slot instead.
    """
    opus = next(m for m in _models() if m.canonical_id == "anthropic/claude-opus-5")
    assert "opus" in declared_surfaces(opus), "the seed file does declare it"
    without_family = opus.model_copy(
        update={
            "aliases": opus.aliases.model_copy(
                update={
                    "variants": [
                        s for s in opus.aliases.variants if s not in ("opus", "claude opus")
                    ]
                }
            )
        }
    )
    check_spelling_coverage([without_family])  # must not raise


def test_declared_surfaces_deduplicates():
    """Five distinct spellings now: the duplicated surface was replaced."""
    v4 = next(m for m in _models() if m.canonical_id == "deepseek/deepseek-v4-flash")
    surfaces = declared_surfaces(v4)
    assert len(surfaces) == len(set(surfaces))
    assert len(surfaces) == 5
