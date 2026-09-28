"""#441: one lane held two resolutions of the same text, and they disagreed.

`RegistrySurfaceFinder.__call__` was a one-line wrapper over plain
`entity.resolve`, which matches a model inside a longer version string. #341
fixed exactly this shape on 2026-09-17 — and reached E4's gate, not this path:

    collect/triage/gates.py:745       E4 gate   near misses SUBTRACTED since #341
    collect/surface_resolver.py:328   the finder near misses KEPT

Demonstrated on `main` by @anoojntglobal-sudo:

    "I switched to GPT-5.2-Codex for refactors."  -> gpt-5, gpt-5.2, gpt-5.2-codex
    "GPT-5.5 was slower than I hoped."            -> gpt-5, gpt-5.5
    "Opus 4.8 wrote the migration."               -> claude-opus-4, claude-opus-4.8

⚠ THE STORED DAMAGE IS ONE CLAIM OF 1,781, AND IS NOT THE REASON TO FIX IT.
  Measured before filing: 290 quotes carry a prefix artefact, 1,780 verdicts
  are unchanged because the longer correct name matches too, and the feared
  false agreement — a "GPT-5.6 Luna" quote filed under `gpt-5` reading as
  "names the model" — occurs ZERO times. The one change is a false positive
  going away.

⚠ THE REASON IS THAT IT BIASES EVERY "NAMES EXACTLY ONE MODEL" MEASUREMENT
  DOWNWARD. A sentence naming only "GPT-5.5" counts as naming two. Recomputed
  with the longest-match rule on the same text, the blog probe's seating
  criterion moves a long way:

      lucumr.pocoo.org   0.40 -> 0.80      antirez.com      0.81 -> 0.93
      timdettmers.com    0.64 -> 0.82      sh-reya.com      0.82 -> 1.00

  The 2026-09-21 six-host figures read through the same finder, so their
  "resolves to exactly one" is low by this mechanism. A defect that only
  corrupts measurement is still a defect, and this one corrupts the
  measurement a seating decision is made on.

⚠ AND `quote_subject_verdict`'s DOCSTRING ARGUES FOR ONE RESOLUTION precisely
  so two consumers cannot disagree. Across the lane, they did.
"""

from __future__ import annotations

from collect.surface_resolver import RegistrySurfaceFinder
from collect.triage.entity import build_population, resolve

REGISTRY = [
    ("openai/gpt-5", "GPT-5"),
    ("openai/gpt-5.2", "GPT-5.2"),
    ("openai/gpt-5.2-codex", "GPT-5.2-Codex"),
    ("openai/gpt-5.5", "GPT-5.5"),
    ("anthropic/claude-opus-4", "Claude Opus 4"),
    ("anthropic/claude-opus-4.8", "Claude Opus 4.8"),
    ("deepseek/deepseek-v4-flash", "DeepSeek V4 Flash"),
]

POPULATION = build_population(REGISTRY)
FINDER = RegistrySurfaceFinder(POPULATION)


def _names(text: str) -> set[str]:
    """The distinct models named, ignoring which spelling matched.

    `resolve` returns every surface spelling, so `gpt-5.5`, `gpt 5.5` and
    `gpt5.5` are three entries for one model. The question this finder is
    asked is WHICH MODELS a text names, so the spellings are collapsed —
    otherwise "named two models" would be untestable on any real registry.
    """
    return {s.replace(" ", "-").replace("--", "-") for s in FINDER(text)}


class TestTheThreeDemonstratedCases:
    def test_a_longer_version_no_longer_drags_its_prefix_in(self):
        assert "gpt-5" not in _names("GPT-5.5 was slower than I hoped.")

    def test_the_model_actually_named_is_still_found(self):
        """⚠ THE HALF THAT MUST NOT BREAK. Subtracting near misses could have
        been implemented as "drop anything with a longer neighbour", which
        would take the correct answer with it."""
        assert "gpt-5.5" in _names("GPT-5.5 was slower than I hoped.")

    def test_a_suffixed_variant_keeps_its_own_base_version(self):
        """`GPT-5.2-Codex` contains `GPT-5.2`, and that is NOT a near miss
        under #341's rule — the rule is about a prefix continuing with a
        DIGIT, which is what distinguishes a different version from a
        differently-named build of the same one. Both are seated models here,
        and a text naming the Codex build does name 5.2."""
        named = _names("I switched to GPT-5.2-Codex for refactors.")
        assert "gpt-5.2-codex" in named
        assert "gpt-5.2" in named
        assert "gpt-5" not in named

    def test_the_anthropic_case_behaves_the_same_way(self):
        named = _names("Opus 4.8 wrote the migration.")
        assert "opus-4.8" in named
        assert "claude-opus-4" not in named
        assert "opus-4" not in named

    def test_a_name_no_longer_name_contains_is_untouched(self):
        """The control from the issue: correct before and correct after, so a
        green result here is not evidence the change did anything."""
        assert "deepseek-v4-flash" in _names("DeepSeek V4 Flash handled it fine.")


class TestItUsesTheRuleTheOtherPathAlreadyUses:
    def test_the_raw_resolver_still_carries_the_prefix(self):
        """⚠ THE CONTROL WITHOUT WHICH THE TESTS ABOVE PROVE NOTHING. If
        `resolve` had stopped returning the prefix for some unrelated reason,
        every assertion above would pass against an unchanged finder."""
        raw = {s.replace(" ", "-") for s in resolve("GPT-5.5 was slower.", POPULATION)}
        assert "gpt-5" in raw, "the underlying defect is gone; re-read this issue"

    def test_the_finder_returns_fewer_than_the_raw_resolver(self):
        raw = set(resolve("GPT-5.5 was slower.", POPULATION))
        assert set(FINDER("GPT-5.5 was slower.")) < raw

    def test_it_returns_the_hits_rather_than_the_whole_resolution(self):
        """A tuple of surfaces, the same shape it always returned. Callers of
        this finder ask what a text names; near misses answer a different
        question, and E4's gate is the one that acts on them."""
        result = FINDER("GPT-5.5 was slower.")
        assert isinstance(result, tuple)
        assert all(isinstance(s, str) for s in result)


class TestTheEmptyAndAbsentCases:
    def test_empty_text_names_nothing(self):
        assert FINDER("") == ()

    def test_none_is_treated_as_empty_rather_than_raising(self):
        """The `text or ""` was there before this change and stays: a caller
        with no text is asking about nothing, not making an error."""
        assert FINDER(None) == ()

    def test_text_naming_no_tracked_model_names_nothing(self):
        assert FINDER("the new model is fine") == ()
