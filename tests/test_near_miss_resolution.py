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
    assert r.has_near_miss
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
    assert not r.has_near_miss


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
    assert not r.has_near_miss


# ── the subset trap, which cost a correction ─────────────────────────────


def test_near_misses_are_DISJOINT_from_hits_since_b_landed():
    """The relation INVERTED on 2026-09-17, and both directions cost a defect.

    Before (b), `near_misses` was a SUBSET of `hits` - the surfaces resolved
    and attributed the document, and `only_near_misses` had to compare the two
    SETS because a truthiness test on `hits` was never true.

    After (b) they are DISJOINT: a refused surface is removed from `hits`. The
    old subset assertion would now pass vacuously on any document with no near
    miss, so it is replaced rather than kept.
    """
    r = resolve_with_near_misses("Claude Code fable 5.1 is broken", population())
    assert r.near_misses, "the fixture must produce a near miss for this to test anything"
    assert not (set(r.near_misses) & set(r.hits)), "refused surfaces must not remain in hits"
    assert r.has_near_miss is True


def test_owners_answers_at_the_model_level_not_the_surface_level():
    """One model has several surfaces, so a surface count answers nothing.

    `fable 5`, `fable-5` and `fable5` are one model. Counting three would be a
    real value answering a question nobody asked (rule 7).
    """
    pop = population()
    r = resolve_with_near_misses("fable 5.1 is worse than claude opus 5", pop)
    clean, refused = r.owners(pop)
    assert clean == {"anthropic/claude-opus-5"}
    assert refused == {"anthropic/claude-fable-5"}
    # THE DOCUMENT IS KEPT - it names Opus 5 cleanly - AND THE FLAG FIRES.
    # Those two go together now, and under the old `only_near_misses` they
    # could not: a clean hit made the sets differ and the flag went silent on
    # exactly this shape, which is the 2,330-document class.
    assert r.has_near_miss is True
    assert "fable 5" not in r.hits, "the refused surface must not attribute"


# ── resolution is unchanged, which is the whole promise ──────────────────


def test_resolution_is_resolve_MINUS_the_near_misses():
    """(b) landed 2026-09-17. This test is the INVERSE of the one it replaces.

    It used to assert `hits == resolve(...)` byte for byte, and its docstring
    said: *"If this ever fails, somebody flipped (b) without the ruling."* The
    ruling was given, so the guard is rewritten rather than deleted - deleting
    it would leave nothing asserting the new relation, which is the same hole
    one direction later.
    """
    pop = population()
    for text in (
        "Claude Code fable 5.1 is seriously flawed",
        "fable 5 is fine",
        "we tried fable 5.1 and also fable 5",
        "fable 5-preview versus claude opus 5",
        "nothing about models here at all",
    ):
        r = resolve_with_near_misses(text, pop)
        refused = set(r.near_misses)
        expected = tuple(h for h in resolve(text, pop) if h not in refused)
        assert r.hits == expected, text


def test_a_document_whose_only_surface_is_refused_resolves_to_nothing():
    """The 47-document class: no clean surface left, so NO_ENTITY drops it.

    This is the loss (b) accepts, and it is the direction that is right: the
    document names a model we do not track, and `near-miss-not-registered`
    says which. Losing it is visible and carries its own fix; attributing it
    to Fable 5 was neither.
    """
    pop = population()
    r = resolve_with_near_misses("Claude Code fable 5.1 is seriously flawed", pop)
    clean, refused = r.owners(pop)
    assert "anthropic/claude-fable-5" in refused
    assert "anthropic/claude-fable-5" not in clean


def test_a_text_naming_nothing_reports_no_near_misses():
    r = resolve_with_near_misses("a document about cooking", population())
    assert r.hits == ()
    assert r.near_misses == ()
    assert not r.has_near_miss


# ── `X.0` is `X`, found by reading the documents (b) would drop ──────────


def test_a_dot_zero_is_the_SAME_model_and_not_a_near_miss():
    """`Sonnet 5.0` names Sonnet 5. The `.0` restates the version.

    The first version of (b) refused these, and it cost whole documents rather
    than a stray attribution: 14 of the 47 documents that lost every surface
    were a `.0`, so nearly a third of the drops were a model we do track.
    """
    pop = population()
    for text in (
        "opus 5.0 is out and it is a disaster",
        "claude fable 5.0 shipped last week",
        "we moved to opus 5.0 last month",
    ):
        r = resolve_with_near_misses(text, pop)
        assert r.near_misses == (), text
        assert r.hits, text


def test_a_dot_zero_followed_by_another_digit_is_still_a_near_miss():
    """`5.01` is not `5`. The lookahead is the whole difference, and a
    two-character window could not evaluate it."""
    r = resolve_with_near_misses("opus 5.01 broke our pipeline", population())
    assert "opus 5" in r.near_misses


def test_a_dated_snapshot_suffix_is_a_KNOWN_EXCLUSION_and_still_refuses():
    """22 documents (0.9%) - recorded rather than ruled on.

    Whether a dated build may speak for its line is a different question from
    whether `5.0` is `5`, and deciding it inside this rule would decide it
    silently.
    """
    pop = population()
    r = resolve_with_near_misses("fable 5-0731 on the bench", pop)
    assert "fable 5" in r.near_misses
