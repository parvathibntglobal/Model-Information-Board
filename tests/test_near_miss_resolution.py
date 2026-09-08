"""A registered surface matched inside a longer version string.

`fable 5` is a surface of `anthropic/claude-fable-5`. `fable 5.1` is not
registered at all, and the resolver matches the former inside the latter — so a
document about Fable 5.1 is FILED AGAINST Fable 5, with nothing on the row to
disagree with. Not a miss; a wrong answer.

Measured 2026-09-08 over 5,010 readable staging documents: **20** resolve to a
model only through such a surface, and **1,621 more** name a real model and pick
up a wrong one as well. `anthropic/claude-opus-4` collects 763 documents whose
text discusses 4.1, 4.6 or 4.8.
`docs/measurements/staging-misattributions-2026-09-08.json`.

WHY THE MECHANISM IS NOT THE BOUNDARY MAP. `normalize` strips punctuation, so
`fable 5.1` and `fable 51` both become `fable51`. The masks separate them
correctly — the dot is a separator, so `ends[]` is True after the `5` in the
first and False in the second. **A version dot is a word boundary and is not a
version boundary**, and the character that would say so was discarded.

RESOLUTION IS UNCHANGED BY ANY OF THIS, deliberately. Rule 8's direction is
one-way: the near miss ships as a recorded field, and becomes a refusal later on
the evidence the field produces.
"""

from __future__ import annotations

from collect.triage.entity import (
    build_population,
    normalize_with_boundaries,
    normalize_with_offsets,
    resolve,
    resolve_with_near_misses,
)

MODELS = [
    ("anthropic/claude-fable-5", "Anthropic: Claude Fable 5"),
    ("anthropic/claude-opus-5", "Claude Opus 5"),
]


def population():
    return build_population(MODELS, [])


# ── the offsets, which nothing could see before ──────────────────────────


def test_the_three_tuple_shape_is_unchanged():
    """Four callers unpack three values, so the old shape had to survive.

    One implementation, two shapes: a mask and an offset map that disagreed
    about where a character came from would place a match at a position it
    never occupied.
    """
    text = "we ran fable 5.1 today"
    key, starts, ends = normalize_with_boundaries(text)
    key2, starts2, ends2, _sources = normalize_with_offsets(text)
    assert (key, starts, ends) == (key2, starts2, ends2)


def test_the_offsets_point_at_the_original_characters():
    text = "we ran fable 5.1 today"
    key, _starts, _ends, sources = normalize_with_offsets(text)
    assert key == "weranfable51today"
    # The normalised run `fable5` ends on the `5` that precedes `.1`.
    at = key.find("fable5")
    end_index = sources[at + len("fable5") - 1]
    assert text[end_index] == "5"
    assert text[end_index + 1 : end_index + 3] == ".1"


def test_offsets_survive_a_stripped_separator_run():
    """Several separators in a row must not shift the map."""
    text = "claude   ---   opus 5"
    key, _s, _e, sources = normalize_with_offsets(text)
    assert key == "claudeopus5"
    assert text[sources[key.find("opus5")]] == "o"


# ── what is a near miss, and what is not ─────────────────────────────────


def test_a_version_continuation_is_a_near_miss():
    r = resolve_with_near_misses("Claude Code fable 5.1 is seriously flawed", population())
    assert r.only_near_misses
    assert "fable 5" in r.near_misses


def test_a_hyphen_followed_by_a_digit_is_a_near_miss():
    r = resolve_with_near_misses("we pinned fable 5-1 last week", population())
    assert "fable 5" in r.near_misses


def test_a_WORD_suffix_is_NOT_a_near_miss_and_that_is_deliberate():
    """`fable 5-preview` still resolves to Fable 5, and I am not sure that is
    right - but it is what was MEASURED.

    The rule requires a DIGIT after the separator. `-preview` is a strong hint
    of a variant, and widening to any word would also have to defend
    `gpt-4-turbo` and `opus-5-thinking`, where the suffix sometimes names a
    different model and sometimes names a mode of the same one. The 1,641-
    document figure in the proposal was measured on the narrow rule, so
    widening it means re-measuring rather than re-reasoning.

    Recorded as a known exclusion rather than an oversight: an earlier draft of
    the proposal claimed this case refused, and it does not.
    """
    r = resolve_with_near_misses("we pinned fable 5-preview last week", population())
    assert r.near_misses == ()


def test_a_bare_mention_is_not_a_near_miss():
    r = resolve_with_near_misses("fable 5 is fine for this", population())
    assert r.near_misses == ()
    assert not r.only_near_misses


def test_a_non_version_suffix_is_not_a_near_miss():
    """Deliberately narrow. `turbo` may be somebody's adjective, and refusing
    on it would trade a measured defect for a guess."""
    r = resolve_with_near_misses("opus 5 turbo was slower for us", population())
    assert r.near_misses == ()


def test_one_bare_occurrence_makes_it_a_real_mention():
    """EVERY admissible occurrence must be continued, not any.

    A document saying `fable 5.1` once and `fable 5` once names Fable 5, and
    calling that a near miss would refuse a document that does name it.
    """
    r = resolve_with_near_misses("we tried fable 5.1 and also fable 5 alone", population())
    assert r.near_misses == ()
    assert not r.only_near_misses


# ── the subset trap, which cost a correction ─────────────────────────────


def test_near_misses_are_a_subset_of_hits_and_only_near_compares_sets():
    """`only_near_misses` tested `not self.hits` once, which is never true.

    `near_misses` is a SUBSET of `hits` - those surfaces did resolve and did
    attribute the document - so a truthiness test on `hits` returned False
    always, including on the document that motivated the whole change.
    """
    r = resolve_with_near_misses("Claude Code fable 5.1 is broken", population())
    assert set(r.near_misses) <= set(r.hits)
    assert r.only_near_misses is True


def test_owners_answers_at_the_model_level_not_the_surface_level():
    """One model has several surfaces, so a surface count answers nothing.

    `fable 5`, `fable-5` and `fable5` are one model. Counting three would be a
    real value answering a question nobody asked (rule 7).
    """
    pop = population()
    r = resolve_with_near_misses("fable 5.1 is worse than claude opus 5", pop)
    clean, misattributed = r.owners(pop)
    assert clean == {"anthropic/claude-opus-5"}
    assert misattributed == {"anthropic/claude-fable-5"}
    # The document DOES name a model, so it is not certainly-wrong...
    assert not r.only_near_misses
    # ...and is still misattributed, which is the 1,621-document class.
    assert misattributed


# ── resolution is unchanged, which is the whole promise ──────────────────


def test_resolution_is_byte_for_byte_what_resolve_returns():
    """Rule 8: the near miss is a RECORDED field, not yet a refusal.

    If this ever fails, somebody flipped (b) without the ruling.
    """
    pop = population()
    for text in (
        "Claude Code fable 5.1 is seriously flawed",
        "fable 5 is fine",
        "we tried fable 5.1 and also fable 5",
        "fable 5-preview versus claude opus 5",
        "nothing about models here at all",
    ):
        assert resolve_with_near_misses(text, pop).hits == resolve(text, pop), text


def test_a_text_naming_nothing_reports_no_near_misses():
    r = resolve_with_near_misses("a document about cooking", population())
    assert r.hits == ()
    assert r.near_misses == ()
    assert not r.only_near_misses
