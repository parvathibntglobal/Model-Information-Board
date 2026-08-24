"""A digit-free surface must be matched correctly, not incidentally.

**THE PROPERTY UNDER TEST IS NOT "THE CURRENT SURFACES WORK".** All 105 surfaces
in `model_alias` carry a digit — `gpt-4`, `opus 4.8`, `haiku-4.5` — so none of
them can hide inside an English word, and every containment matcher in this repo
would pass a test built from them. That is a property of today's data reading as a
property of the code, and it survives exactly until one reviewer accepts one
`family_surface`.

So every case here uses a **digit-free** surface, which is the shape the seated
population happens not to contain:

    pro     inside "problem", "process"      the golden-set sampler, 41 of 43 candidates
    free    inside "freeze"                  resolve(), found by the movie-post control
    fusion  inside "confusion"               resolve(), same control
    saba    inside "was a bad"               resolve(), same control

Two call sites, one rule, and the rule lives in `normalize_with_boundaries` so
that fixing it once reaches both. The first fix did not reach the second caller,
which is the reason this file covers both rather than one.
"""

from __future__ import annotations

import pytest

from collect.triage.entity import normalize_with_boundaries, resolve
from scripts.labelling_pools import snippet_around


class _Population:
    """The smallest thing `resolve` needs: a surface list."""

    def __init__(self, *surfaces: str) -> None:
        self.surfaces = tuple(surfaces)


# ── the sampler: snippet_around ──────────────────────────────────────────────

@pytest.mark.parametrize(
    ("surface", "text"),
    [
        ("pro", "this is a problem with the tool loop"),
        # The plural, named explicitly: it is the case that started the thread,
        # and a matcher keyed on a trailing boundary could pass the singular by
        # accident of what follows it.
        ("pro", "two problems showed up in the same run"),
        ("pro", "the process hung after two calls"),
        ("free", "it would freeze on the third request"),
        ("fusion", "there was some confusion about the schema"),
        ("saba", "that was a bad idea in retrospect"),
    ],
)
def test_the_sampler_does_not_match_a_digit_free_surface_inside_a_word(surface, text):
    """The 43-versus-2 defect, pinned per instance.

    A candidate selected this way is not merely a wrong row — it is a row a
    labeller will work through before anyone asks what matched.
    """
    assert snippet_around(text, surface) is None, (
        f"{surface!r} matched inside a word in {text!r}"
    )


@pytest.mark.parametrize(
    "text",
    [
        "pro was the tier they used",
        "we switched to pro and it held",
        "pro, then back again",
        "(pro)",
    ],
)
def test_the_sampler_still_matches_a_digit_free_surface_standing_alone(text):
    """The other half, and the half a stricter regex would break.

    A boundary check that also rejected the real mentions would trade a noisy
    stratum for an empty one and look like the same fix.
    """
    found = snippet_around(text, "pro")
    assert found is not None, f"'pro' standing alone was not matched in {text!r}"
    snippet, start = found
    assert "pro" in snippet.lower()
    assert start >= 0


def test_the_sampler_still_matches_across_separator_spellings():
    """Stripping separators is load-bearing and must survive the boundary check.

    `gpt 5`, `gpt-5` and `gpt5` are one surface; a boundary check applied to the
    RAW text rather than to the normalised one would lose two of the three.
    """
    for written in ("GPT 5 was slower", "gpt-5 was slower", "gpt5 was slower"):
        assert snippet_around(written, "gpt 5") is not None, written


# ── the gate: resolve ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("surface", "text"),
    [
        ("pro", "this is a problem with the tool loop"),
        ("pro", "two problems showed up in the same run"),
        ("free", "it would freeze on the third request"),
        ("fusion", "there was some confusion about the schema"),
        # MEASURED LIVE on the stored corpus, 2026-08-20: a boundary-blind
        # matcher claims these and a bounded one claims none. `saba` is the
        # surface the movie-post control found inside "wa[s a ba]d" and it is
        # still in the population — 4 documents today.
        ("saba", "that was a bad idea in retrospect"),
        ("sonar", "the sonarqube report was clean"),
        ("command a", "the command and its arguments were wrong"),
    ],
)
def test_resolve_does_not_match_a_digit_free_surface_inside_a_word(surface, text):
    assert resolve(text, _Population(surface)) == ()


def test_resolve_matches_the_same_surface_standing_alone():
    """So the test above is about boundaries and not about the surface being short."""
    assert resolve("free tier was enough", _Population("free")) == ("free",)


def test_both_call_sites_agree_on_every_case():
    """One rule, two callers, and the first fix reached only one of them.

    This is the check that would have failed on 2026-08-20: `resolve` had the
    boundary logic and the sampler did not, and nothing compared them.
    """
    cases = [
        ("pro", "a problem appeared", False),
        ("pro", "pro was fine", True),
        ("free", "freeze", False),
        ("free", "free tier", True),
    ]
    for surface, text, expected in cases:
        by_gate = bool(resolve(text, _Population(surface)))
        by_sampler = snippet_around(text, surface) is not None
        assert by_gate == by_sampler == expected, (
            f"{surface!r} in {text!r}: gate={by_gate} sampler={by_sampler} "
            f"expected={expected}"
        )


def test_the_boundary_helper_is_what_both_use():
    """Guards the reuse, so a future caller cannot re-derive the rule quietly."""
    import inspect

    import scripts.labelling_pools as pools

    source = inspect.getsource(pools.snippet_around)
    assert "normalize_with_boundaries" in source, (
        "the sampler must use the shared helper rather than its own boundary logic"
    )

    # THIRD CALL SITE, ADDED 2026-08-21. The `ambiguous-in-context` stratum used
    # `normalize(surface) in normalize(text)` with no boundary map at all - the
    # same defect this file exists for, at a site written after the fix landed.
    # `occurs_bounded` must delegate rather than re-derive, which is the whole
    # point of the assertion above.
    assert "snippet_around" in inspect.getsource(pools.occurs_bounded), (
        "occurs_bounded must delegate to the bounded matcher, not re-derive it"
    )
    assert pools.occurs_bounded("a problem here", "pro") is False
    assert pools.occurs_bounded("gpt 4o mini is fast", "gpt-4o") is True
    # And the mechanism itself, on the case the whole file is about. `pro` sits at
    # positions 1..3 of `aproblem`: it STARTS a word and does not END one, and it
    # is `ends` that rejects it. Asserted this way round because `starts[1]` is
    # True — "problem" does begin there — so a check reading only `starts` would
    # admit every prefix of every word and look like it was doing something.
    key, starts, ends = normalize_with_boundaries("a problem")
    assert key == "aproblem"
    assert starts[1], "'problem' begins at position 1"
    assert not ends[3], "'pro' does not end a word, which is what rejects the match"
    assert ends[7], "'problem' ends at position 7"


# ── a version surface inside a LONGER version surface ────────────────────────
#
# THE CASE THIS MODULE'S OPENING ARGUMENT DOES NOT COVER, and the argument is
# what hid it. The docstring says every seated surface carries a digit, "so none
# of them can hide inside an English word" — true, and it reasons about English
# words. A digit does not stop a surface hiding inside ANOTHER SURFACE:
#
#     opus 4   inside   opus 4.8      `.` is a boundary character
#     gpt-5    inside   gpt-5.6
#
# Measured 2026-08-21 on the one Reddit thread held in full: a single mention of
# "Claude Opus 4.8" resolved to TWO model_versions, `anthropic/claude-opus-4.8`
# and `anthropic/claude-opus-4`. On the blog corpus, three first-hand reports
# about GPT-5.6 resolved to `openai/gpt-5`.
#
# This is worse than the English-word case rather than milder. `free` inside
# "freeze" produces an obviously junk row somebody notices. `opus 4` inside
# `opus 4.8` produces a plausible row about a real model that nobody notices,
# and quote verification cannot catch it — the quote is verbatim and the
# attribution is wrong.
#
# `resolve` already sorts longest-first and documents why: "a caller taking the
# first match should get the one that names the most". Nothing takes the first
# match. The fix is therefore a caller change or a longest-match-wins result,
# and it is PROPOSED rather than taken — it alters attribution corpus-wide.
# docs/measurements/the-rollup-refused-and-why.md §1.

@pytest.mark.parametrize(
    ("text", "longer", "shorter"),
    [
        ("the response is handled by Claude Opus 4.8", "opus 4.8", "opus 4"),
        ("I had GPT-5.6 Sol Ultra run the comparison", "gpt-5", "gpt-5"),
        ("we moved to claude-opus-4.8 last week", "claude-opus-4.8", "claude-opus-4"),
    ],
)
def test_a_shorter_version_surface_matches_inside_a_longer_one(text, longer, shorter):
    """CHARACTERISES THE DEFECT. Both surfaces match; only one is meant.

    Asserted as the CURRENT behaviour rather than as the desired behaviour, so
    the test states what the matcher does today and a fix has to come back here
    and say so deliberately. An xfail would let the fix land silently.
    """
    hits = resolve(text, _Population(longer, shorter))
    assert shorter in hits, "the shorter surface matches — this is the defect"
    if longer != shorter:
        assert longer in hits
        assert hits.index(longer) < hits.index(shorter), (
            "longest-first ordering is the property a fix would rely on"
        )


def test_the_digit_argument_does_not_extend_to_surface_in_surface():
    """The reasoning in this module's docstring, held to its actual scope.

    "Every surface carries a digit, so none can hide inside an English word" is
    sound. It says nothing about hiding inside another surface, and the two were
    conflated for as long as no measurement distinguished them.
    """
    # digit-carrying, cannot hide in prose:
    assert resolve("this is a problem with the loop", _Population("opus 4")) == ()
    # and yet hides perfectly inside a longer version of itself:
    assert "opus 4" in resolve("Claude Opus 4.8 handled it", _Population("opus 4"))
