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

#: Distinguishes "caller did not mention window" from "caller passed None",
#: which means *disable locality* and is what the measurements used.
_UNSET: int | None = -1


@lru_cache(maxsize=1)
def default_locality_window() -> int | None:
    """`contract/harvest.yaml:sieve.locality_window`, or None if absent.

    Rule 5: a threshold lives in versioned YAML. Absent means no window, which
    is the pre-locality behaviour and is what a contract predating this reads
    as — an absent setting must not silently become a definite one (rule 6).
    """
    import yaml

    from collect.config import CONTRACT_DIR

    path = CONTRACT_DIR / "harvest.yaml"
    if not path.exists():  # pragma: no cover - contract is always present
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return (raw.get("sieve") or {}).get("locality_window")


def normalize(text: str) -> str:
    """Casefold, unify apostrophes, collapse whitespace.

    Collapsing whitespace is what lets a phrase match across a line break,
    which is where multi-word terms would otherwise fail on real HTML.
    """
    return " ".join(text.translate(_APOSTROPHES).casefold().split())


def _stemmed(word: str) -> str:
    """One word, allowed to inflect. How far depends on how long it is.

    A word at or past `MIN_STEM_LENGTH` gets the general stem: any suffix up to
    `MAX_STEM_SUFFIX`, which covers plurals, tense and `moralis` → `moralising`.

    A SHORTER WORD GETS PLURALS ONLY, and that distinction is load-bearing.
    Measured against `contract/queries.yaml`, 20-odd genuine noun-final terms
    end in a three- or four-letter noun — `function call`, `agent loop`,
    `unified diff`, `wrong type`, `response time`, `json mode`, `apply the
    edit` — and a general stem cannot be used on those: `code` would reach
    `codebase`, `key` would reach `keyword`, `slow` would reach `slowdown`,
    and `mode` would reach `model`. That is why `MIN_STEM_LENGTH` exists.

    But "cannot take any suffix" and "cannot take an S" are different claims,
    and only the first was ever argued for. `call` → `calls` is the plural the
    contract's noun-final rule is about, and `calls` is not a different word
    the way `callback` is. So short words get `s` / `es` and nothing else,
    which reaches every one of those twenty and reaches no new word: none of
    `codebase`, `keyword`, `slowdown`, `model` or `user` is formed by adding
    an S.
    """
    escaped = re.escape(word)
    if len(word) >= MIN_STEM_LENGTH:
        return rf"{escaped}\w{{0,{MAX_STEM_SUFFIX}}}"
    return rf"{escaped}(?:e?s)?"


@lru_cache(maxsize=4096)
def _pattern_for(term: str) -> re.Pattern[str]:
    """One term to one regex, cached because a sweep reuses the same few hundred.

    Single words match with a bounded stem expansion, because the index does no
    stemming and the contract writes deliberate stems.

    **Multi-word terms stem their FINAL word and match the rest exactly.**
    `contract/queries.yaml` requires this in as many words — "NOUN-FINAL TERMS
    ARE WRITTEN SINGULAR, AND THE SIEVE IS REQUIRED TO STEM THE FINAL WORD" —
    and states the cost of not doing it: 275 of 275 multi-word terms in that
    file failed to match their own plural, so `invalid argument` never reached
    "invalid arguments". 82% of the vocabulary is multi-word, so exact matching
    was silently discarding most of the sieve's reach.

    Only the final word, because that is where English inflects a noun phrase.
    Stemming every word would let `extra key` reach `extras keyword` and
    `no complaint from` reach `nothing complaints fromage` — the interior words
    of these terms are function words and adjectives whose form is fixed, and
    widening them buys nothing while costing precision.

    `MIN_STEM_LENGTH` guards the short-word case exactly as it does for a
    single term: `code fence` does not become `code fencepost`, because
    `fence` is stemmed but bounded, and `extra key` does not reach `keyword`
    because `key` is three letters and left alone. That guard is why the
    contract could ask for this without also asking for a stop-list.

    WHAT THIS DOES NOT REACH, so nobody deletes the paired forms believing it
    does. Two classes, both real, both still needing BOTH forms in
    `contract/queries.yaml`:

      A PLURAL THAT IS NOT FINAL. `no complaint from` pluralises in the
      middle — "no complaints from" — and only the final word is stemmed, so
      this term cannot reach its own plural however long `from` is. The
      contract carries `no complaint from` and `no complaints from` as
      separate terms and must keep doing so. Stemming every word instead
      would let it reach "nothing complaints fromage", which is the trade
      that was rejected.

      A PLURAL THAT REWRITES THE STEM. `y` to `ies` is not a suffix, so no
      suffix rule reaches it: `consistent latency` cannot match "consistent
      latencies". Eight terms are in this class as of 2026-08-14 and seven are
      verbs or adverbs whose "plural" nobody types; that one is a real noun
      and a real gap.

    `tests/test_sieve_stemming.py` pins both classes against the live
    contract, so a term landing in either is a vocabulary decision somebody
    makes rather than a silent narrowing.
    """
    normalized = normalize(term)
    if not normalized:
        raise ValueError("empty term")

    words = normalized.split()
    if len(words) > 1:
        exact = [re.escape(word) for word in words[:-1]]
        pattern = r"\b" + r"\s+".join([*exact, _stemmed(words[-1])]) + r"\b"
        return re.compile(pattern)

    return re.compile(rf"\b{_stemmed(normalized)}\b")


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


def strip_container(text: str, name: str) -> str:
    """Remove ONE named container, leaving every other kind of span intact.

    `author_prose` removes all of `_EXCLUSIONS` because it is answering "did the
    author assert this". A signature is a different question and wants a
    different subset: `collect/CLAUDE.md` says to exclude blockquoted spans from
    the dedupe signature so commentary ABOUT a post is not merged into it, and
    says nothing about code — because a pasted traceback is content that
    distinguishes documents rather than borrowed words that conflate them.

    So this exists to give `assemble/signature.py` the blockquote pattern without
    a second definition of what a blockquote is. Three call sites now read one
    set of patterns: `author_prose` for the sieve, `triage.specificity.has_code`
    for their presence, and this for one member.

    Raises:
        KeyError: on an unknown container, rather than silently stripping nothing
            and returning text that looks filtered.
    """
    for container, pattern in _EXCLUSIONS:
        if container == name:
            return pattern.sub(" ", text)
    raise KeyError(
        f"{name!r} is not a container. Known: {list(EXCLUDED_CONTAINERS)}"
    )


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


def author_prose_aligned(text: str) -> str:
    """`author_prose`, but every offset still refers to the original text.

    Same exclusions, each replaced by spaces of ITS OWN LENGTH rather than one
    space. That is the only difference, and it exists so a topic match found in
    the whole text and a signal match found in the author's prose can be
    measured against each other — see `_within_window`. Two strings of
    different lengths have no shared coordinate system, and a distance computed
    across them would be a number with no meaning.
    """
    for _, pattern in _EXCLUSIONS:
        text = pattern.sub(lambda m: " " * len(m.group(0)), text)
    return text


def _aligned(text: str) -> str:
    """Casefold and unify apostrophes without moving a single character.

    `normalize` also collapses whitespace, which is what makes a phrase match
    across a line break — but it destroys offsets. Nothing is lost by skipping
    it here: `_pattern_for` already joins the words of a multi-word term with
    `\\s+`, so those terms match across line breaks either way.
    """
    return text.translate(_APOSTROPHES).casefold()


def _spans(terms, haystack: str) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for term in terms:
        found.extend((m.start(), m.end()) for m in _pattern_for(term).finditer(haystack))
    return found


def _within_window(terms, text: str, window: int) -> bool:
    """Do a topic match and a signal match come within `window` characters?

    Subject is deliberately not part of this. Naming the model once is how a
    post establishes what it is about, and a blog post that names it in the
    introduction and reports the failure in the conclusion is the ordinary
    shape rather than the exception. Topic and signal together ARE the claim,
    so those are the two that have to be near each other.
    """
    topic_spans = _spans(terms.topic, _aligned(text))
    signal_spans = _spans(terms.signal, _aligned(author_prose_aligned(text)))
    if not topic_spans or not signal_spans:
        return False

    for t_start, t_end in topic_spans:
        for s_start, s_end in signal_spans:
            gap = s_start - t_end if t_start <= s_start else t_start - s_end
            if max(0, gap) <= window:
                return True
    return False


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


def sieve(terms, text: str, *, window: int | None = _UNSET) -> SieveVerdict:
    """Apply one rendered term set to one document.

    `subject` is ALL-OF, `topic` and `signal` are ANY-OF — the contract's
    semantics, not this module's choice.

    An empty `topic` or `signal` group would make that group vacuously true and
    turn the query into its subject alone, which is the collapsed state issue #4
    documents. The contract's own test forbids empty groups; this treats an
    empty group as a failed one rather than trusting that.

    LOCALITY. `window` is the number of characters topic and signal may be
    apart. Defaults to `contract/harvest.yaml:sieve.locality_window`; pass
    `None` to disable it, which is what the pre-locality measurements did.

    The first blog harvest kept one document, and it was
    `vickiboykis.com/2026/04/20/build-yourself-flowers/` — 41,956 characters,
    filed `extraction.faithfulness:positive`, with `flash 2.5` in a sentence
    about breaking a transcript into paragraphs, `extract` in a sentence about
    a museum API, and `held up` meaning *delayed*, 3,899 characters away. Three
    unrelated passages counted as one claim, because nothing required them to
    be near each other. Blog articles have a median of 8,191 characters against
    GitHub's 2,228, so the same sieve was quietly stricter on one platform than
    the other and had no way to know.
    """
    if window is _UNSET:
        window = default_locality_window()

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

    # Checked only when both groups matched: "topic and signal are too far
    # apart" is a different statement from "one of them is absent", and
    # collapsing them would lose the distinction `missing` exists to carry.
    if not missing and window is not None and not _within_window(terms, text, window):
        missing.append("locality")

    return SieveVerdict(
        passed=not missing,
        subject=subject_hits,
        topic=topic_hits,
        signal=signal_hits,
        missing=tuple(missing),
        signal_in_excluded=quoted_only,
    )


def sieve_any(variants, text: str, *, window: int | None = _UNSET) -> SieveVerdict:
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
        # `window` is threaded rather than defaulted per call: this is the
        # entry point callers are steered towards, so an option it silently
        # dropped would be an option that does not exist.
        verdict = sieve(terms, text, window=window)
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

    #: THE THIRD NUMBER. How many candidates actually contain the phrase the
    #: query quoted.
    #:
    #: `candidates` and `kept` alone cannot distinguish two very different
    #: queries. Measured 2026-08-17: `"rolled back"` returned 75 posts with the
    #: phrase present in 24%, so a `candidates` of 75 reads as healthy retrieval
    #: while the usable count is 18. Phrase binding is a property of the phrase
    #: and not of the platform (see collect/adapters/reddit.py), so the gap is
    #: per query and nothing downstream can reconstruct it.
    #:
    #: None means NOT MEASURED — the query quoted nothing, or the caller had no
    #: texts to check. It is never 0 for that case: 0 asserts "no candidate
    #: contained the phrase", which is a finding, and "we did not look" is not
    #: (rule 6).
    phrase_present: int | None = None

    @property
    def pass_rate(self) -> float:
        return self.kept / self.candidates if self.candidates else 0.0

    @property
    def phrase_rate(self) -> float | None:
        """Containment, or None where it was not measured. Never 0.0 for absent.

        ⚠ DIAGNOSES THE TERM, NOT RETRIEVAL. DO NOT OPTIMISE IT.

        Engineer 2's warning, on #18, and it is the sharper reading of the
        measurement: no index we have measured BINDS a phrase. Reddit degrades
        to OR over the tokens; GitHub ranks. So containment is not compliance
        with an operator — it is **how common the phrase is**, because a common
        collocation is returned by relevance ranking whether or not anything
        honoured the quotes.

        Which makes this metric Goodhart-shaped. It improves by choosing MORE
        COMMON phrases, and a more common phrase is a less specific one, so the
        number rises while the evidence falls. `"context window"` at 96% is
        exactly that: collocation frequency read as operator behaviour. Wiring
        it in as a metric to maximise would institutionalise the same mistake
        one layer down, where it would look like progress.

        Read it as a property of the TERM: a low rate says this phrase is rare
        and retrieval cannot find it, which is a vocabulary fact worth acting
        on. **`usable_rate` is the one to watch** — it is the share of
        phrase-carrying candidates the sieve kept, so it cannot be moved by
        making the query vaguer.

        They are NOT interchangeable and can rank two queries in opposite
        orders. `tests/test_sieve_yield.py` pins that, the same way the two
        specificity floors are pinned at 0.3 and 0.0.
        """
        if self.phrase_present is None or not self.candidates:
            return None
        return self.phrase_present / self.candidates

    @property
    def usable_rate(self) -> float | None:
        """Kept as a share of candidates that CARRIED the phrase.

        The honest denominator when retrieval did not honour the phrase: a
        document that never contained it was never a candidate for this query in
        any meaningful sense. None where containment was not measured.
        """
        if self.phrase_present is None or not self.phrase_present:
            return None
        return self.kept / self.phrase_present


def tally(query_key: str, verdicts, *, phrase_present: int | None = None) -> SieveYield:
    """Fold verdicts into one row. Counting only — nothing is dropped here.

    `phrase_present` is passed in rather than computed: a verdict knows nothing
    about the query string that retrieved it, and the caller already holds both.
    Leaving it None records "not measured" rather than claiming zero.
    """
    verdicts = list(verdicts)
    return SieveYield(
        query_key=query_key,
        candidates=len(verdicts),
        kept=sum(1 for v in verdicts if v.passed),
        missing_subject=sum(1 for v in verdicts if "subject" in v.missing),
        missing_topic=sum(1 for v in verdicts if "topic" in v.missing),
        missing_signal=sum(1 for v in verdicts if "signal" in v.missing),
        phrase_present=phrase_present,
    )


def quoted_phrases(query: str) -> tuple[str, ...]:
    """Every double-quoted phrase in a query string, in order.

    Retrieval syntax, not matching: this is what the query ASKED for, which is
    the thing `SieveYield.phrase_present` measures compliance with.

    PAIRED IN ORDER, not matched by regex. `re.finditer(r'"([^"]+)"')` looks
    right and is not: on `"" "real phrase"` it pairs the closing quote of the
    empty phrase with the opening quote of the real one, captures the space
    between them, and loses the phrase entirely. Splitting takes the quotes in
    the order they were typed, which is how a search box reads them too.
    """
    segments = query.split('"')
    return tuple(seg for seg in segments[1::2] if seg.strip())


def count_phrase_present(phrase: str, texts) -> int:
    """How many of `texts` contain `phrase`, by the sieve's own matching rules.

    One definition, shared by every adapter that wants the third number. Uses
    `matches` over `normalize`d text, so containment is adjacency modulo
    whitespace and stemming — the same standard the sieve holds a term to, which
    is what makes the figure comparable to `kept`.
    """
    return sum(1 for text in texts if matches(phrase, normalize(text)))
