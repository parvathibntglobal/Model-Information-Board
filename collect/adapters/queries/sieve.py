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


# ── whose words are these? ────────────────────────────────────────────────
#
# `subject` and `topic` establish ABOUTNESS and may match anywhere: a config line
# naming a model is real evidence the model was in use, and worth retrieving.
# `signal` carries the CLAIM, and a claim has an author.
#
# The first live run stored two documents that passed because this distinction
# did not exist:
#
#   Aider-AI/aider#4438      `accurate` matched inside a Google marketing
#                            sentence someone pasted — a blockquote nested inside
#                            a fenced block. The issue is about diff application.
#   crewAIInc/crewAI#2685    `accurate` matched inside a prompt string in a
#                            Python snippet: goal=("answer questions accurately
#                            using only the provided knowledge tools")
#
# Both were filed as `summarization.fidelity: positive` — a positive claim about
# a silent-failure capability, on the strength of a config line and somebody
# else's copy. Rule 1 broken at the source rather than at the quote check.
#
# THE FULL EXCLUSION SET, and why each member is in it. Named as a set rather
# than fixed case by case, because both live false positives happened to arrive
# through fences and the next one will not.
#
#   fenced code        ``` and ~~~ — code, config dumps, logs, prompt strings.
#                      Both live false positives came through here
#   blockquotes        `>` lines — pasted model output, quoted docs, quoted other
#                      people. collect/CLAUDE.md already excludes blockquoted
#                      spans from dedupe signatures so commentary about a post is
#                      not merged into it; the reasoning applies harder to a
#                      stance term than to a signature
#   indented code      four spaces or a tab — markdown's older code form, and how
#                      a traceback arrives when nobody fenced it
#   inline code        `like this` — a term in backticks is being NAMED, not
#                      asserted. A docs list containing `accurate` claims nothing
#   html pre/code      GitHub renders HTML, and <pre> holds logs
#   html comments      <!-- --> is issue-template instruction text the author
#                      never wrote and usually never saw rendered
#   template residue   `_No response_`, and task-list labels `- [ ]` / `- [x]`.
#                      Written by whoever wrote the template, present in every
#                      issue in the repo, identical across all of them
#   urls               a word inside a slug asserts nothing:
#                      .../introducing-gemini-2-5-pro
#
# WHAT IS NOT EXCLUDED, ANYWHERE ELSE. Nothing is removed from the stored
# payload, the dedupe signature, subject or topic matching, or what extraction
# later reads. collect/CLAUDE.md requires code fences, error strings, diffs and
# numbers-with-units preserved verbatim, because they are the specificity signal
# triage depends on. This is a VIEW of the text, built for one question: did the
# author assert the stance?
#
# The set errs toward rejecting a signal. Admitting a quoted one produces a false
# positive that reads as a considered answer; excluding a real one produces a low
# pass rate somebody can act on. Rule 4's asymmetry applied to the matcher — and
# `SieveVerdict.signal_in_excluded` keeps the exclusion visible rather than
# silent.

_EXCLUSIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("fenced-code", re.compile(r"(?ms)^[ \t]*(```|~~~).*?(?:^[ \t]*\1|\Z)")),
    ("html-comment", re.compile(r"(?s)<!--.*?-->")),
    ("html-pre-code", re.compile(r"(?is)<(pre|code|script|style)\b.*?</\1>")),
    ("url", re.compile(r"https?://\S+|www\.\S+")),
    ("inline-code", re.compile(r"`[^`\n]+`")),
    ("blockquote", re.compile(r"(?m)^[ \t]*>.*$")),
    ("indented-code", re.compile(r"(?m)^(?: {4,}|\t+)\S.*$")),
    ("template-residue", re.compile(r"(?mi)^[ \t]*(?:_no response_|- \[[ xX]\].*)$")),
)

#: The container names, for logs and for anyone auditing a rejection.
EXCLUDED_CONTAINERS: tuple[str, ...] = tuple(name for name, _ in _EXCLUSIONS)


def author_prose(text: str) -> str:
    """The text with every container of somebody else's words removed.

    Order matters once: fenced blocks go first, so a blockquote or an indented
    line inside a fence is removed as part of the fence rather than surviving as
    a fragment. `Aider-AI/aider#4438` is exactly that shape.

    A removed span becomes a single space, never nothing, so two words either
    side of a code span cannot fuse into a third.
    """
    for _, pattern in _EXCLUSIONS:
        text = pattern.sub(" ", text)
    return text


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

    #: Signal terms present in the document but only inside quoted or fenced
    #: material. Not a pass, and not the same state as "no signal anywhere" —
    #: recording the difference stops the exclusion being invisible, and it is
    #: the vocabulary feedback Engineer 2 asked for: her term matched, and only
    #: somebody else said it.
    signal_in_excluded: tuple[str, ...] = field(default=())

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
    prose = normalize(author_prose(text))

    # Aboutness may come from anywhere; the claim may not. The exclusion set
    # above says why, and which two documents paid for the distinction.
    subject_hits = tuple(t for t in terms.subject if matches(t, haystack))
    topic_hits = tuple(t for t in terms.topic if matches(t, haystack))
    signal_hits = tuple(t for t in terms.signal if matches(t, prose))
    quoted_only = tuple(
        t for t in terms.signal if t not in signal_hits and matches(t, haystack)
    )

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
        signal_in_excluded=quoted_only,
    )


def sieve_any(variants, text: str) -> SieveVerdict:
    """Pass if ANY alias spelling's term set passes.

    The form a query was ISSUED in and the form a document is WRITTEN in are
    different questions. Retrieval hyphenates `claude sonnet 5` so its numeral
    cannot match an issue number; the post itself says `claude sonnet 5` in
    prose. Sieving against one spelling drops the other silently, so the caller
    is given a function that cannot be used that way by accident.

    Returns the first passing verdict, or — where none passes — the one that got
    FURTHEST, meaning fewest missing groups and then most terms matched.

    Not the last one. The last variant is an arbitrary choice, and the moment a
    request carries every spelling of a model, "missing subject" would be decided
    by whichever form happened to be ordered last. That is how a diagnostic
    degrades as coverage improves: attaching six spellings took the measured
    subject-miss rate from 67% to 100% on a fixed corpus, with no behaviour
    change at all. The rejection counts are what the defect-4 costing rests on,
    so the returned verdict has to be the tightest true statement about the
    document rather than a positional accident.
    """
    best: SieveVerdict | None = None
    for terms in variants:
        verdict = sieve(terms, text)
        if verdict.passed:
            return verdict
        if best is None or (
            len(verdict.missing),
            -len(verdict.matched_terms),
        ) < (len(best.missing), -len(best.matched_terms)):
            best = verdict
    return best or SieveVerdict(passed=False, missing=("subject", "topic", "signal"))


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
