"""The local relevance filter. Identical on all three platforms.

WHY THIS EXISTS AT ALL
----------------------
`contract/queries.yaml` says it plainly: *terms are written for the sieve.* An
index cannot do what these terms need —

    "should have been null"   GitHub reads four required tokens and returns
                              1,836 unrelated results. A local substring match
                              reads the phrase, and no index can.
    "moralis"                 a deliberate stem. In a query it matches exactly
                              one document on GitHub (issue #4 of this repo,
                              which quotes the wildcard). In a sieve it matches
                              moralising and moralised.
    "truncate"                the index does no stemming at all: `truncate`
                              2,136, `truncates` 180, `truncated` 1,334 are
                              three separate tokens. Locally that is one term.

So retrieval is broad and cheap, and precision happens here.

WHAT IT DOES NOT DO
-------------------
**It never decides whether a document is evidence.** It answers "is this
document about the thing the query was about", which is a relevance question.
Whether the text supports a claim is extraction's, in the other lane, and a
regex deciding it would be an LLM's job done badly by a filter (rule 2).

Used two ways, and the second one matters more:

    FILTER   blogs, pre-fetch, where the feed handed us the body already. An
             entry that cannot pass the sieve need not cost an article request.
    COUNT    every platform, as a per-query yield figure. A query whose
             documents never pass is burning budget and producing nothing,
             which is invisible from this lane because the documents look like
             hits. That is Engineer 2's `yields_claim_when` argument one step
             earlier, and it is a counter, never a gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

#: Below this length a word is too ambiguous to extend: `code` would reach
#: `codebase`, `slow` would reach `slowdown`. The contract's deliberate stems —
#: `moralis`, `moraliz`, `hallucinat` — are all comfortably longer.
MIN_STEM_LENGTH = 5

#: How far past a term a word may run and still match: `moralis` + `ing`,
#: `truncate` + `d`, `degrade` + `s`. Four keeps `moralisation` and stops well
#: short of a different word.
MAX_STEM_SUFFIX = 4

#: Typographic apostrophes are what people actually type. The contract writes
#: `didn't follow`; a real post writes `didn’t follow`. Without this the term
#: silently never matches, which is the failure mode this whole project is
#: about.
_APOSTROPHES = str.maketrans({"’": "'", "ʼ": "'", "‘": "'"})


def normalize(text: str) -> str:
    """Casefold, unify apostrophes, collapse whitespace.

    Collapsing whitespace is what lets a phrase match across a line break,
    which is where multi-word terms would otherwise fail on real HTML.
    """
    return " ".join(text.translate(_APOSTROPHES).casefold().split())


@lru_cache(maxsize=4096)
def _pattern_for(term: str) -> re.Pattern[str]:
    """One term to one regex, cached because a sweep reuses the same few hundred.

    Multi-word terms match exactly, word-bounded. Single words match with a
    bounded stem expansion, because the index has no stemming and the contract
    writes deliberate stems.
    """
    normalized = normalize(term)
    if not normalized:
        raise ValueError("empty term")

    if " " in normalized:
        pattern = r"\b" + r"\s+".join(re.escape(word) for word in normalized.split()) + r"\b"
        return re.compile(pattern)

    escaped = re.escape(normalized)
    if len(normalized) >= MIN_STEM_LENGTH:
        return re.compile(rf"\b{escaped}\w{{0,{MAX_STEM_SUFFIX}}}\b")
    return re.compile(rf"\b{escaped}\b")


def matches(term: str, text: str) -> bool:
    """Does one term appear in already-normalised text?"""
    return bool(_pattern_for(term).search(text))


@dataclass(frozen=True)
class SieveVerdict:
    """Why a document passed or did not. Auditable, not just a boolean.

    The matched terms are kept because a yield counter that cannot say *which*
    term carried a document is a number nobody can act on — and because
    `missing` names the group that failed, which is the difference between "the
    query is wrong" and "this document is off-topic".
    """

    passed: bool
    subject: tuple[str, ...] = ()
    topic: tuple[str, ...] = ()
    signal: tuple[str, ...] = ()
    missing: tuple[str, ...] = field(default=())

    @property
    def matched_terms(self) -> tuple[str, ...]:
        return self.subject + self.topic + self.signal


def sieve(terms, text: str) -> SieveVerdict:
    """Apply one rendered term set to one document.

    `subject` is ALL-OF, `topic` and `signal` are ANY-OF — the contract's
    semantics, not this module's choice.

    An empty `topic` or `signal` group would make that group vacuously true and
    turn the query into its subject alone, which is the collapsed state issue #4
    documents. The contract's own test forbids empty groups; this treats an
    empty group as a failed one rather than trusting that.
    """
    haystack = normalize(text)

    subject_hits = tuple(t for t in terms.subject if matches(t, haystack))
    topic_hits = tuple(t for t in terms.topic if matches(t, haystack))
    signal_hits = tuple(t for t in terms.signal if matches(t, haystack))

    missing = []
    if len(subject_hits) != len(terms.subject):
        missing.append("subject")
    if not terms.topic or not topic_hits:
        missing.append("topic")
    if not terms.signal or not signal_hits:
        missing.append("signal")

    return SieveVerdict(
        passed=not missing,
        subject=subject_hits,
        topic=topic_hits,
        signal=signal_hits,
        missing=tuple(missing),
    )


def sieve_any(variants, text: str) -> SieveVerdict:
    """Pass if ANY alias spelling's term set passes.

    The form a query was ISSUED in and the form a document is WRITTEN in are
    different questions. Retrieval hyphenates `claude sonnet 5` so its numeral
    cannot match an issue number; the post itself says `claude sonnet 5` in
    prose. Sieving against one spelling drops the other silently, so the caller
    is given a function that cannot be used that way by accident.

    Returns the first passing verdict, or the last failing one — which carries a
    `missing` group worth logging.
    """
    verdict = SieveVerdict(passed=False, missing=("subject",))
    for terms in variants:
        verdict = sieve(terms, text)
        if verdict.passed:
            return verdict
    return verdict


@dataclass(frozen=True)
class SieveYield:
    """Per-query yield: how many candidates the sieve kept, and why not.

    The figure `yields_claim_when` needs one layer earlier. A query whose
    candidates never pass is costing rate limit and producing nothing, and
    nothing in `harvest_run` can currently say so.
    """

    query_key: str
    candidates: int = 0
    kept: int = 0
    missing_subject: int = 0
    missing_topic: int = 0
    missing_signal: int = 0

    @property
    def pass_rate(self) -> float:
        return self.kept / self.candidates if self.candidates else 0.0


def tally(query_key: str, verdicts) -> SieveYield:
    """Fold verdicts into one row. Counting only — nothing is dropped here."""
    verdicts = list(verdicts)
    return SieveYield(
        query_key=query_key,
        candidates=len(verdicts),
        kept=sum(1 for v in verdicts if v.passed),
        missing_subject=sum(1 for v in verdicts if "subject" in v.missing),
        missing_topic=sum(1 for v in verdicts if "topic" in v.missing),
        missing_signal=sum(1 for v in verdicts if "signal" in v.missing),
    )
