"""E4 — the hard gates. Deterministic, cheap, and run before any paid call.

`docs/logic-and-workflow.md` §8 names five, plus a bot list. Three can be built
today. **Two cannot, and this module refuses to pretend otherwise.**

THE THIRD STATE, WHICH IS THE WHOLE DESIGN
-------------------------------------------
A gate that cannot run has not passed the document. `triage_verdict` is
`kept | dropped`, and a document kept by three gates out of five is not in the
same condition as one kept by five - but it writes the same row, and a survival
rate computed over the two together is a number about our coverage wearing the
clothes of a number about the corpus.

So every verdict carries `unavailable`, naming the gates that did not run. A
survival figure quoted without it is rule 7's exact failure: a real value
answering a question it was not asked.

    KEPT        every implemented gate passed it
    DROPPED     at least one gate rejected it, and `reasons` says which
    unavailable the gates that could not run, named

WHAT IS NOT BUILT, AND WHY IT IS NOT A STUB
--------------------------------------------
    wrong language   No detector is installed and none is declared in
                     `pyproject.toml`. Adding one is a dependency decision, not
                     a line of code, and a `lang == "en"` check against a NULL
                     column would silently pass every document.
    known-bot list   Rule 5 puts a filter rule in `contract/`, and the list does
                     not exist there. `ClaudeAI-mod-bot` is already in the top
                     five authors of the 1,297-post corpus, so this is a real
                     gap and not a theoretical one.
    out of window    Implemented, but only where a surface resolves to exactly
                     one model. See `out_of_window`.

A stub returning True for any of these would be indistinguishable from a gate
that ran, which is the class of defect this lane has now produced nine times.

MEASURED, SO THE ORDER IS NOT GUESSED
--------------------------------------
Over the 1,297-post substitution corpus, cumulative, entity gate on the union
population:

    pure link post            drops 144
    <15 tokens, no artifact   drops   1
    no resolvable entity      drops  78
    --------------------------------------
    survival                  1,074 / 1,297 = 82.8%

**That 82.8% CANNOT be compared to the 10-15% target.** Every post in that
corpus was retrieved by a query containing a model name, so it is pre-filtered
for exactly what the entity gate tests, and two of the six gates did not run.
It ranks the gates against each other and calibrates nothing. Calibration needs
an unfiltered sweep, which nobody has fetched.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from collect.triage.entity import SurfacePopulation, resolve
from collect.triage.specificity import (
    has_code,
    has_conditions,
    has_error_strings,
    has_numbers,
)

#: Gate names, used as `filter_reasons` values and as `unavailable` entries.
LANGUAGE = "wrong-language"
TOO_SHORT = "too-short-no-artifact"
NO_ENTITY = "no-resolvable-entity"
OUT_OF_WINDOW = "out-of-window"
PURE_LINK = "pure-link-post"
KNOWN_BOT = "known-bot"

#: Every gate §8 names. An ORDER FOR REPORTING, not for execution - `triage`
#: runs all six on every document, so this fixes how they are listed and nothing
#: about what they cost.
GATE_ORDER = (LANGUAGE, PURE_LINK, TOO_SHORT, NO_ENTITY, OUT_OF_WINDOW, KNOWN_BOT)

#: Below this a document is a reaction rather than a report - UNLESS it carries
#: an artifact, because `TypeError: 'NoneType'` is eleven tokens and is the
#: highest-signal thing in the corpus.
MIN_TOKENS = 15

_TOKEN = re.compile(r"\S+")


def has_artifact(text: str) -> bool:
    """Does this document carry anything machine-emitted or measured?

    **Reuses `specificity`'s four text-only components rather than defining
    "artifact" a second time.** They are contract-backed
    (`contract/harvest.yaml`), already tested, and already the answer to "does
    this look like experience rather than opinion" — which is the same question
    the length gate is asking about a short document.

    A first version of this was a private regex, and it got `TypeError` wrong:
    `\\bError\\b` does not match inside `TypeError`, so the single most common
    artifact in the corpus read as absent. Two definitions of one concept drift,
    and this is what drifting looks like.

    `names_version` is deliberately NOT among them. A short document that only
    names a model is not a report, and the entity gate already asks that
    question - counting it here would let `opus 5 lol` through on the strength
    of the thing every document in a model-name-retrieved corpus has.
    """
    return (
        has_numbers(text)
        or has_error_strings(text)
        or has_code(text)
        or has_conditions(text)
    )


class Verdict(StrEnum):
    KEPT = "kept"
    DROPPED = "dropped"


@dataclass(frozen=True)
class Document:
    """What the gates need. A projection, not the `document` row.

    Every field but `text` is optional, and an absent field makes the gate that
    reads it UNAVAILABLE rather than passing. A missing `created_at` is not a
    recent document and a missing `author` is not a human (rule 6).
    """

    text: str
    created_at: date | None = None
    author: str | None = None
    lang: str | None = None
    #: False for a link post. None where the platform did not say - blogs and
    #: GitHub issues have no such notion, and guessing False would drop them all.
    is_self_post: bool | None = None
    #: Commentary the poster wrote themselves, where the platform separates it.
    body: str | None = None


@dataclass(frozen=True)
class TriageResult:
    """One document's verdict, with what did not run named beside it."""

    verdict: Verdict
    reasons: tuple[str, ...] = ()
    unavailable: tuple[str, ...] = ()
    #: Surfaces the entity gate matched, most specific first. Empty when the gate
    #: dropped it, and empty when the gate did not run - `unavailable` separates
    #: those two, never this field.
    matched_surfaces: tuple[str, ...] = ()
    #: Rule 7 and reproducibility: which surface population produced the above.
    population_fingerprint: str | None = None

    @property
    def kept(self) -> bool:
        return self.verdict is Verdict.KEPT

    @property
    def fully_gated(self) -> bool:
        """Did every gate actually run?

        A survival rate over documents where this is False is a statement about
        our coverage, not about the corpus.
        """
        return not self.unavailable


def wrong_language(doc: Document, *, allowed: frozenset[str] | None) -> bool | None:
    """True drops. **None means the gate could not run.**

    Returns None whenever there is no allow-list or the document carries no
    detected language. `document.lang` is nullable and nothing populates it: no
    language detector is installed, and none is declared in `pyproject.toml`.
    Treating NULL as English would pass every document while looking like a gate.
    """
    if allowed is None or doc.lang is None:
        return None
    return doc.lang.split("-", 1)[0].casefold() not in allowed


def too_short(doc: Document) -> bool:
    """True drops. Under `MIN_TOKENS` tokens AND carrying no artifact.

    The conjunction is the point. `TypeError: 'NoneType' object is not
    subscriptable` is a complete bug report in eleven tokens; "this is amazing"
    is four and is nothing. Length alone cannot tell them apart.
    """
    text = doc.text
    return len(_TOKEN.findall(text)) < MIN_TOKENS and not has_artifact(text)


def pure_link_post(doc: Document) -> bool | None:
    """True drops. A link with no commentary of the poster's own.

    **A link post WITH commentary is kept**, and that is not a detail: of 536
    link posts in the substitution corpus, 392 carry `selftext`. Dropping all
    536 would discard the commentary, which is the part an engineer wrote.

    None where the platform has no notion of a link post, so a blog article does
    not get dropped by a Reddit-shaped rule.
    """
    if doc.is_self_post is None:
        return None
    if doc.is_self_post:
        return False
    return not (doc.body or "").strip()


def out_of_window(
    matched: tuple[str, ...],
    *,
    population: SurfacePopulation,
    in_window: Mapping[str, bool],
) -> bool | None:
    """True drops. Every model this document names is outside the release window.

    Takes the surfaces the entity gate already matched rather than the document,
    so the population is applied once per document and both gates are guaranteed
    to be reasoning about the same match set.

    **UNAVAILABLE, not False, in three cases**, because each is a place where a
    definite answer would be invented:

    1. no surface matched - the entity gate owns that document, not this one.
    2. no matched surface has a known owner. A declared-only surface carries no
       owner (see `build_population`), so a document naming `deepseek r1` and
       nothing else cannot be placed in or out of the window here.
    3. an owned surface resolves to several models with disagreeing window
       flags. `in_window` is per model; a surface owned by 25 of them answers
       nothing, and picking one would be the ambiguity the extract refuses.

    Only where every named model is known AND all of them are out does this
    drop. Absence of a model from `in_window` is unknown, never out.
    """
    if not matched:
        return None

    verdicts: list[bool] = []
    for surface in matched:
        owners = population.owners.get(surface, ())
        for owner in owners:
            if owner in in_window:
                verdicts.append(in_window[owner])
    if not verdicts:
        return None
    # Any in-window model keeps the document. `all(out)` is the only drop.
    return not any(verdicts)


def known_bot(doc: Document, *, bots: frozenset[str] | None) -> bool | None:
    """True drops. **None means no list exists**, which is the state today.

    Rule 5 puts a filter rule in `contract/`, and there is no bot list there. An
    empty frozenset is a different statement - "the list exists and is empty" -
    so the two are not merged.
    """
    if bots is None:
        return None
    if doc.author is None:
        return None
    return doc.author.casefold() in bots


def triage(
    doc: Document,
    *,
    population: SurfacePopulation,
    allowed_languages: frozenset[str] | None = None,
    bots: frozenset[str] | None = None,
    in_window: Mapping[str, bool] | None = None,
) -> TriageResult:
    """Run EVERY gate. No short-circuit, and that is deliberate.

    Stopping at the first rejection would make `unavailable` mean two things at
    once - "this gate cannot run" and "this gate was not reached" - and the whole
    value of the field is that it means only the first. The gates are a regex and
    a set lookup; running all six costs nothing worth having an ambiguity for.

    It also gives `/filtered` every trigger a document hit rather than the
    earliest one, which is what "sorted by how close it came to passing" needs.
    """
    matched = resolve(doc.text, population)

    outcomes: list[tuple[str, bool | None]] = [
        (LANGUAGE, wrong_language(doc, allowed=allowed_languages)),
        (PURE_LINK, pure_link_post(doc)),
        (TOO_SHORT, too_short(doc)),
        (NO_ENTITY, not matched),
        (
            OUT_OF_WINDOW,
            out_of_window(matched, population=population, in_window=in_window or {}),
        ),
        (KNOWN_BOT, known_bot(doc, bots=bots)),
    ]

    reasons = tuple(name for name, out in outcomes if out is True)
    unavailable = tuple(name for name, out in outcomes if out is None)

    return TriageResult(
        verdict=Verdict.DROPPED if reasons else Verdict.KEPT,
        reasons=reasons,
        unavailable=unavailable,
        matched_surfaces=matched,
        population_fingerprint=population.fingerprint,
    )


@dataclass
class TriageRun:
    """Counts over a batch, and the caveat that must travel with them."""

    kept: int = 0
    dropped: int = 0
    by_reason: dict[str, int] = field(default_factory=dict)
    never_ran: dict[str, int] = field(default_factory=dict)
    population_fingerprint: str | None = None

    @property
    def total(self) -> int:
        return self.kept + self.dropped

    @property
    def survival(self) -> float | None:
        """Kept over total, or None where nothing was triaged.

        None rather than 0.0: a rate over an empty batch is not zero survival.
        """
        return self.kept / self.total if self.total else None

    def describe(self) -> str:
        """The figure with its denominator and its holes (rule 7)."""
        if self.survival is None:
            return "nothing triaged; survival is not measured"
        lines = [
            f"survival {self.kept}/{self.total} = {100 * self.survival:.1f}%"
            f"  (population {self.population_fingerprint})",
        ]
        for reason, count in sorted(self.by_reason.items(), key=lambda kv: -kv[1]):
            lines.append(f"  dropped {reason:<24} {count:>6}")
        if self.never_ran:
            missing = ", ".join(
                f"{g} ({n})" for g, n in sorted(self.never_ran.items(), key=lambda kv: -kv[1])
            )
            lines.append(
                f"  GATES THAT DID NOT RUN: {missing}. This survival rate is an "
                "UPPER BOUND - documents these gates would have dropped are "
                "counted as kept."
            )
        return "\n".join(lines)


def triage_all(documents, **kwargs) -> tuple[list[TriageResult], TriageRun]:
    """Triage a batch and summarise it. The summary states what did not run."""
    results = [triage(d, **kwargs) for d in documents]
    run = TriageRun(population_fingerprint=kwargs["population"].fingerprint)
    for r in results:
        if r.kept:
            run.kept += 1
        else:
            run.dropped += 1
        for reason in r.reasons:
            run.by_reason[reason] = run.by_reason.get(reason, 0) + 1
        for gate in r.unavailable:
            run.never_ran[gate] = run.never_ran.get(gate, 0) + 1
    return results, run
