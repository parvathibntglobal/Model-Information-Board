"""Final-word stemming, and the contract requirement it satisfies.

`contract/queries.yaml` states it as a requirement rather than a preference:

    "NOUN-FINAL TERMS ARE WRITTEN SINGULAR, AND THE SIEVE IS REQUIRED TO STEM
     THE FINAL WORD. Stated as a requirement because it is not free: the sieve
     stems single words and matches multi-word terms exactly, so `invalid
     argument` does not currently reach 'invalid arguments' ... measured
     against the sieve as it stands, 275 of 275 multi-word terms in this file
     fail to match their own plural."

This file is the cross-lane check: Engineer 2's vocabulary against Engineer 1's
matcher. It reads `contract/queries.yaml` and asserts the sieve can actually
reach the forms her terms are written to catch. Neither lane owns it and it
breaks for both — the contract can break it by writing a term the sieve cannot
reach, and the sieve can break it by narrowing.

82% of the signal terms are multi-word, so this is most of the sieve's reach,
not an edge.
"""

from __future__ import annotations

import pytest

from collect.adapters.queries.contract import load_queries
from collect.adapters.queries.sieve import (
    MAX_STEM_SUFFIX,
    MIN_STEM_LENGTH,
    matches,
    normalize,
)


def all_terms() -> list[str]:
    """Every subject, topic and signal term in the contract, deduplicated."""
    seen = []
    for entry in load_queries().all_entries:
        for group in (entry.terms.subject, entry.terms.topic, entry.terms.signal):
            for term in group:
                if "{" not in term and term not in seen:  # skip placeholders
                    seen.append(term)
    return seen


def multi_word_terms() -> list[str]:
    return [t for t in all_terms() if " " in normalize(t)]


#: Terms whose plural changes the stem — `y` to `ies` — which no suffix rule
#: can reach. Measured 2026-08-14 against the contract; pinned so the list
#: cannot grow without somebody deciding it should.
#:
#: Seven of the eight are verbs or adverbs where the "plural" is not a word
#: anybody would type (`applies`, `cleanlies`, `ordinaries`). **One is a real
#: noun plural and a real gap**: `consistent latency` cannot reach "consistent
#: latencies", and the contract's own instruction covers it — "a term whose
#: plural or singular differs materially should carry BOTH forms rather than
#: rely on the stem".
IRREGULAR_PLURALS = {
    "failed to apply",
    "refuses ordinary",
    "declined a perfectly",
    "parsed cleanly",
    "applied cleanly",
    "compiled first try",
    "compiled cleanly",
    "consistent latency",  # the one that is a genuine noun
}


# ── the requirement ───────────────────────────────────────────────────────


def test_the_contract_is_mostly_multi_word_so_this_is_not_an_edge_case():
    terms = all_terms()
    multi = multi_word_terms()
    share = len(multi) / len(terms)
    assert share > 0.5, (
        f"only {share:.0%} of terms are multi-word; if this has dropped a long "
        "way the contract changed shape and this file's premise needs re-reading"
    )


def test_every_multi_word_term_reaches_its_simple_plural():
    """The 275-of-275 failure, as a gate.

    A term that cannot match its own plural silently matches less than the
    contract believes, and silence is the failure mode this project is
    arranged against.

    The simple `+s` is asserted for every term rather than a
    part-of-speech-aware plural, because guessing whether `cleanly` is a noun
    is a worse test than checking the one inflection that is universal.
    """
    unreachable = [
        term for term in multi_word_terms()
        if not matches(term, normalize(term) + "s")
    ]
    assert not unreachable, (
        f"{len(unreachable)} multi-word term(s) cannot match their own plural: "
        f"{unreachable[:5]}. contract/queries.yaml requires the sieve to stem "
        "the final word."
    )


def test_the_only_unreachable_plurals_are_the_stem_changing_ones():
    """`y` to `ies` rewrites the stem, so no suffix rule reaches it.

    Pinned as a set rather than a count: a new term landing in here is a
    vocabulary decision somebody should make on purpose, and the fix is the
    contract's own — carry both forms.
    """
    found = set()
    for term in multi_word_terms():
        words = normalize(term).split()
        last = words[-1]
        if len(last) > 2 and last.endswith("y") and last[-2] not in "aeiou":
            target = " ".join([*words[:-1], last[:-1] + "ies"])
            if not matches(term, target):
                found.add(term)

    assert found == IRREGULAR_PLURALS, (
        f"the y->ies gap changed. New: {sorted(found - IRREGULAR_PLURALS)}. "
        f"Fixed: {sorted(IRREGULAR_PLURALS - found)}."
    )


def test_every_term_still_matches_itself():
    """The obvious one, and worth having: stemming must not narrow anything."""
    for term in all_terms():
        assert matches(term, normalize(term)), term


# ── only the final word ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("term", "text", "should_match", "why"),
    [
        ("invalid argument", "invalid arguments", True, "the contract's own example"),
        ("extra key", "extra keys", True, "plural of a three-letter final noun"),
        ("function call", "function calls", True, "four-letter final noun"),
        ("agent loop", "agent loops", True, "four-letter final noun"),
        ("missing required field", "missing required fields", True, "three words"),
        ("dropped the", "dropped theatre", False, "short final word takes only a plural"),
        ("invalid argument", "invalids argument", False, "interior words are exact"),
        ("code fence", "code fences", True, "final word stemmed"),
        ("code fence", "codes fence", False, "leading word not stemmed"),
        ("no complaint from", "no complaints from", False,
         "the plural is interior here, so the contract must carry both forms"),
    ],
)
def test_stemming_reaches_the_final_word_and_no_further(term, text, should_match, why):
    assert matches(term, normalize(text)) is should_match, why


@pytest.mark.parametrize(
    ("term", "wider_word"),
    [
        ("extra key", "extra keyword"),
        ("wrote the code", "wrote the codebase"),
        ("too slow", "too slowdown"),
        ("json mode", "json model"),
        ("tool use", "tool user"),
        ("agent loop", "agent loophole"),
        ("unified diff", "unified different"),
    ],
)
def test_a_short_final_word_takes_a_plural_and_nothing_else(term, wider_word):
    """The distinction the short-word rule turns on.

    `MIN_STEM_LENGTH` exists because a general stem on a four-letter word
    reaches a different word — `code`/`codebase`, `mode`/`model`,
    `use`/`user`. None of those is formed by adding an S, so allowing the
    plural costs nothing and reaches the twenty-odd genuine noun-final terms
    that a general stem could not be used for.
    """
    assert len(normalize(term).split()[-1]) < MIN_STEM_LENGTH
    assert matches(term, normalize(term)) is True
    assert matches(term, normalize(term) + "s") is True
    assert matches(term, normalize(wider_word)) is False


def test_the_stem_is_bounded():
    """`MAX_STEM_SUFFIX` stops a term running into a different word."""
    long_tail = "x" * (MAX_STEM_SUFFIX + 1)
    assert matches("json schema", normalize("json schemas")) is True
    assert matches("json schema", normalize(f"json schema{long_tail}")) is False


def test_single_word_stemming_is_unchanged():
    """The behaviour that already existed must not have moved."""
    assert matches("truncate", normalize("truncated")) is True
    assert matches("moralis", normalize("moralising")) is True
    assert matches("code", normalize("codebase")) is False, "short words unstemmed"


# ── it must not have widened into a false positive ────────────────────────


def test_the_two_live_false_positives_are_still_rejected():
    """Stemming widens reach, and the incident documents are the check on that.

    `accurate` is gone from the vocabulary, so these are pinned against the
    terms as they stood — see tests/test_sieve_author_prose.py, which owns the
    reasoning. Here the question is narrower: does a wider matcher reach into
    an excluded container? It must not.
    """
    from pathlib import Path

    from collect.adapters.queries.sieve import author_prose
    from tests.test_sieve_author_prose import INCIDENT_TERMS

    fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "github"
    for name in ("aider-4438-excerpt.md", "crewai-2685-excerpt.md"):
        document = (fixtures / name).read_text(encoding="utf-8")
        prose = normalize(author_prose(document))
        for term in INCIDENT_TERMS.signal:
            assert not matches(term, prose), (
                f"{term!r} reached the author's prose in {name} after stemming"
            )
