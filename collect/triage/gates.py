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

So every verdict names the gates that did not run - and since 2026-08-19 it
names them in TWO fields rather than one, because "could not run" and "nothing
to run it on" behave in opposite directions as the corpus grows. See `NotRun`. A
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

                     ⚠ RULED 2026-09-08: THIS STAYS A RECORDED FIELD, AND A
                     GATE IS NOT PROPOSED UNTIL A DISTRIBUTION IS PUBLISHED.
                     Measured that day: NO PLATFORM IN THE STORED CORPUS
                     DECLARES A LANGUAGE - no `lang`, `language`, `locale` or
                     `content_language` in any reddit or github payload - so
                     `document.lang` is NULL on 6,502 of 6,502 rows and there
                     is nothing to backfill FROM. `document.lang` was
                     un-reserved the same day and helps only NEW documents on
                     the two platforms that do declare one (dev.to's
                     `language`, X's `lang`), neither of which has a stored
                     corpus.

                     So on this corpus the value could only come from a
                     DETECTOR, which is an inference - and rule 8 makes an
                     inference a weight, a flag or a recorded field, never a
                     gate, until its error rate is measured against a
                     population it did not choose. A wrong language gate is the
                     worst of the three to get wrong, because its false
                     positives are invisible: it drops the document, and
                     code-switched English is the register most of this corpus
                     is written in and the one a detector misreads.

                     THE ORDER IS FIXED, NOT PREFERRED: install a detector,
                     write its output as a recorded field, run it over the
                     corpus, PUBLISH THE DISTRIBUTION. Only then is a gate a
                     proposal anybody can argue with. Nobody should put a
                     number on this gate's effect before that, and this
                     docstring deliberately does not.
                     See `docs/the-three-dead-gates-2026-09-08.md`.
    known-bot list   Rule 5 puts a filter rule in `contract/`, and the list does
                     not exist there. `ClaudeAI-mod-bot` is already in the top
                     five authors of the 1,297-post corpus, so this is a real
                     gap and not a theoretical one.

                     ⚠ THE DETECTOR IS BUILT, AS OF 2026-09-07. This gate now
                     loads `contract/bots.yaml` through
                     `collect/triage/bots.py` and reports UNAVAILABLE
                     PER SOURCE until that file declares one - so the count
                     shrinks platform by platform instead of being all-or-
                     nothing. What is still missing is the LIST, which is a
                     `contract/` change and is proposed in
                     `docs/proposals/for-engineer-2-the-bot-list.md`.
                     Measured there: 7 GitHub accounts carry `bot` in the login
                     with NO `[bot]` suffix, the busiest at 33 comments - joint
                     top voice in a 2,016-comment export.
    out of window    Implemented, but only where a surface resolves to exactly
                     one model. See `out_of_window`.

THE SUBJECT GATE READS THE THREAD ROOT WHERE THE PLATFORM PUTS IT THERE
------------------------------------------------------------------------
RULED 2026-09-08. Every platform in this corpus but one carries its subject
INSIDE the document the gate reads:

    Reddit post    `title` + `selftext`      the title, in the document
    GitHub issue   `title` + `body`          the title, in the document
    blog article   the extracted article     headline and lede, in the document
    HN comment     the comment body alone    THE STORY, IN A DIFFERENT RECORD

So Hacker News was being asked a question the other three are never asked, and
it answered the way you would expect: the entity gate resolved **11 of 511
comments - 2.2% - across the two HN subject threads the 2026-09-07 smoke run
stored** (`docs/measurements/entity-gate-on-hn-threads-2026-09-07.json`; two
threads, from stored payloads, and NOT a sample of Hacker News). The standalone
sweep found a thread that was a bare GitHub link at 678 points whose evidence -
a quoted price, the pricing URL, an expiry date - was entirely in comments that
never repeat the model's name.

`Document.thread_subject_text` carries the root's text. **`collect/triage/run.py`
is what supplies it**, by joining `document.thread_root_id` to the root's own row
and reading that row's `text_ref` - so no new column and no new storage - and it
does so only for the platforms in `run.SUBJECT_FROM_THREAD_ROOT`, which is
Hacker News. A caller that builds `Document`s by hand (every script in
`scripts/`) passes None and gates exactly as it did before.

Three constraints make this a reading rule rather than inheritance by another
name, and all three are enforced in `triage` rather than remembered:

  1. the document's own text is resolved FIRST and wins;
  2. the root is consulted only where the document resolved NOTHING;
  3. `out_of_window` is given the document's OWN matches and never the union -
     an inherited subject may KEEP a document and may never DROP one.

`TriageResult.subject_was_inherited` is set on every inherited document and
`TriageRun.subject_inherited` counts them, so a survival figure can never pool
two reading units silently. Resolution is a separate question at a later stage:
`judge/pipeline.py:subject_was_inherited` answers it, and subject inheritance as
a RESOLUTION rule remains refused.

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

⚠  AND IT IS NOT A FIGURE ABOUT THE STORED CORPUS EITHER, which is the part
   this docstring did not say until 2026-09-08. That population was BUILT BY A
   SCRIPT off a JSONL export - `scripts/labelling_pools.py` - and nothing had
   ever run these gates against the database: `Stage('triage')` was `run=None`
   and `document.triage_verdict` was NULL on all 6,502 rows.

   The first run against the corpus is `docs/triage-first-run-2026-09-08.md`:
   **2,860 kept of 5,010 triaged = 57.1%**, per source github 42.9% / reddit
   89.8% / blog 42.5%, with 1,492 of 6,502 rows NEVER GATED because their
   payload is absent from that host's raw store or is not prose. That figure is
   also an upper bound and for the same reason as this one - `wrong-language`
   and `known-bot` ran on nothing - so the two are comparable in their caveat
   and in nothing else. Quote whichever one answers the question being asked,
   and say which population it came from.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from collect.triage.bots import BotList
from collect.triage.entity import (
    SurfacePopulation,
    resolve,
    resolve_with_near_misses,
)
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

#: NOT A GATE, AND NOT IN `GATE_ORDER`. A flag on `TriageResult.flags`: the
#: document is KEPT and the hit is recorded. Rule 8's one-way direction in one
#: name - the 26 GitHub accounts the platform itself declares `user.type ==
#: "Bot"` are gated under `KNOWN_BOT`; the 7 that merely carry `bot` in the
#: login are counted under this, because that judgement's error rate was
#: measured on a population we chose by grepping our own corpus.
KNOWN_BOT_COUNTED = "known-bot-counted"

#: NOT A GATE EITHER. A flag: every surface this document resolved through was
#: matched inside a longer VERSION string, so the model it will be filed against
#: is not the model it discusses - `fable 5` inside `fable 5.1`.
#:
#: RECORDED AND NOT ACTED ON, which is rule 8's direction. Resolution is
#: unchanged: the document is still attributed, still wrongly, and now COUNTED.
#: The count is what a refusal would be promoted on, and it is also the registry
#: work-list - N documents flagged on `fable 5` is the signal that says register
#: Fable 5.1, arriving without anybody going looking.
NEAR_MISS = "near-miss-not-registered"

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


class NotRun(StrEnum):
    """Why a gate produced no verdict. TWO states, and they are not the same.

    `unavailable` used to carry both, and from outside they look identical: a
    gate name in a list. They behave in opposite directions.

        UNAVAILABLE      the gate CANNOT RUN. No allow-list, no bot list, no
                         detector. A build defect, fixed once for everyone, and
                         the count falls to zero when it is fixed.

        NOT_APPLICABLE   there is NOTHING TO RUN IT ON. This document has no
                         author, or its platform has no notion of a link post.
                         A property of the document, and permanent.

    Collapsing them means the count GROWS as coverage improves - every blog
    article added is another `pure-link-post` that cannot apply - which reads
    as the gates getting worse while they are getting better. That is the wrong
    direction, and it is why this is an enum rather than a bool.
    """

    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not-applicable"


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
    #: The handle. FOR A HUMAN READING A POOL ROW, and no gate matches on it -
    #: see `author_external_id`. Kept because a filter row showing a bare
    #: account id is a row nobody can review.
    author: str | None = None
    lang: str | None = None
    #: False for a link post. None where the platform did not say - blogs and
    #: GitHub issues have no such notion, and guessing False would drop them all.
    is_self_post: bool | None = None
    #: Commentary the poster wrote themselves, where the platform separates it.
    body: str | None = None

    #: `document.source`, and `author.external_id`. BOTH ARE NEEDED TOGETHER
    #: and neither is optional for the bot gate: `author` is `UNIQUE (source,
    #: external_id)`, so an id without its platform is ambiguous - two
    #: platforms can legitimately issue the same numeric id, and a bot list
    #: matched without the source would filter a human on the other platform.
    #:
    #: Added 2026-09-07 with the bot list. `known_bot` used to match on
    #: `author`, the handle, which is mutable on every platform that has
    #: renames - so a list keyed on it stops matching the day an account is
    #: renamed, silently, which is the failure this gate exists to prevent.
    source: str | None = None
    author_external_id: str | None = None

    #: THE THREAD ROOT'S TEXT, FOR THE SUBJECT GATE AND NOTHING ELSE.
    #:
    #: Ruled 2026-09-08. Hacker News is the first platform in this corpus that
    #: puts the subject line in a SEPARATE RECORD: on Reddit the subject is in
    #: the post's own `title`, on GitHub in the issue's own `title`, in a blog
    #: in its own headline - and in an HN comment it is the story, 12 bytes away
    #: in another row. That is a platform-shape fact, not a claim about
    #: aboutness, and it was costing the platform almost everything: the entity
    #: gate resolved 11 of 511 comments, 2.2%, across the two HN subject threads
    #: the 2026-09-07 smoke run stored
    #: (`docs/measurements/entity-gate-on-hn-threads-2026-09-07.json`; that
    #: population is 2 threads read from stored payloads and is NOT a sample of
    #: Hacker News).
    #:
    #: ⚠ THIS IS A READING RULE AND NOT A RESOLUTION RULE, and the distinction
    #:   is the whole permission. It changes what text the SUBJECT GATE reads.
    #:   It does not license a claim to be filed against a model named outside
    #:   its own quote - subject inheritance as a RESOLUTION rule was refused
    #:   (`docs/proposals/for-engineer-2-inherited-subjects-and-family-claims
    #:   .md`) and that ruling stands. `judge/pipeline.py:subject_was_inherited`
    #:   derives the resolution answer separately, in code, and
    #:   `quote_subject_verdict` returns QUOTE_NAMES_NOTHING for exactly this
    #:   case.
    #:
    #: ⚠ SCOPED TO THE SUBJECT GATE. `out_of_window` is given the document's
    #:   OWN matches only and never the inherited ones - see `triage`. An
    #:   inherited subject may KEEP a document and may never DROP one.
    #:
    #: None on every platform whose subject is inside the document, which is
    #: every platform but Hacker News today. Hugging Face discussions are the
    #: next on the same argument and are not wired.
    thread_subject_text: str | None = None


@dataclass(frozen=True)
class TriageResult:
    """One document's verdict, with what did not run named beside it."""

    verdict: Verdict
    reasons: tuple[str, ...] = ()
    #: Gates that COULD NOT RUN - a missing detector or an unwritten list.
    #: Shrinks to empty when the build catches up. See `NotRun`.
    unavailable: tuple[str, ...] = ()
    #: Gates with NOTHING TO RUN ON for this document. Permanent, and not a
    #: defect: a blog article has no link-post flag and never will.
    not_applicable: tuple[str, ...] = ()
    #: Surfaces the entity gate matched IN THE DOCUMENT'S OWN TEXT, most
    #: specific first. Empty when the gate dropped it, empty when the gate did
    #: not run - `unavailable` separates those two, never this field - and, since
    #: 2026-09-08, EMPTY ON A DOCUMENT KEPT BY AN INHERITED SUBJECT. That third
    #: case is named here because a reader who assumes `kept implies
    #: matched_surfaces` was right until that date: check
    #: `subject_was_inherited`, or read `all_surfaces` for the union.
    matched_surfaces: tuple[str, ...] = ()
    #: Surfaces matched ONLY inside a longer version string - `fable 5` in
    #: `fable 5.1`. A SUBSET of `matched_surfaces`, never disjoint from it, which
    #: is the reading three separate counts have now got wrong: these surfaces
    #: DID resolve and DID attribute the document. The flag `NEAR_MISS` fires
    #: only when every matched surface is one of these.
    near_miss_surfaces: tuple[str, ...] = ()
    #: Surfaces matched in the THREAD ROOT'S text and not in this document's.
    #: Empty unless the platform supplied a root (Hacker News alone today) and
    #: the document's own text resolved nothing.
    inherited_surfaces: tuple[str, ...] = ()
    #: NON-DROPPING OBSERVATIONS, by name. A check that KEPT the document and
    #: recorded something about it - rule 8's "weight, flag or recorded field",
    #: which is what an unmeasured check ships as.
    #:
    #: DELIBERATELY NOT `reasons`. A reader of `filter_reasons` is reading why a
    #: document was dropped, and putting a non-dropping observation there would
    #: make a kept document carry a drop reason - unfalsifiable from the row,
    #: and the exact confusion the two-field split in `unavailable` /
    #: `not_applicable` exists to prevent one field over.
    flags: tuple[str, ...] = ()
    #: Rule 7 and reproducibility: which surface population produced the above.
    population_fingerprint: str | None = None

    @property
    def subject_was_inherited(self) -> bool:
        """Did this document reach the subject gate on its THREAD'S subject?

        SET ON EVERY INHERITED DOCUMENT, which is the condition the 2026-09-08
        ruling attaches to the permission. A survival figure that pools
        inherited and own-text keeps is a figure about two different reading
        units, so this is what lets a caller separate them - and
        `TriageRun.subject_inherited` counts it for exactly that reason.

        DERIVED, never stored as a flag anybody can set independently: it is
        true when the root resolved and the document itself did not. Same shape
        as `judge/pipeline.py:subject_was_inherited`, which answers the
        RESOLUTION question about a claim - a different question at a later
        stage, deliberately named the same so the two are found together.
        """
        return bool(self.inherited_surfaces) and not self.matched_surfaces

    @property
    def all_surfaces(self) -> tuple[str, ...]:
        """Own matches then inherited ones. For a caller that wants the union.

        Ordered own-first so the more specific evidence about THIS document
        comes first, which is what `matched_surfaces`'s own ordering promises.
        """
        return self.matched_surfaces + self.inherited_surfaces

    @property
    def kept(self) -> bool:
        return self.verdict is Verdict.KEPT

    @property
    def no_verdict(self) -> tuple[str, ...]:
        """Every gate that returned no opinion, of either kind.

        For a caller that only needs "which gates said nothing" and does not
        act on why - `scripts/labelling_pools.py` is the one that exists.
        """
        return self.unavailable + self.not_applicable

    @property
    def fully_gated(self) -> bool:
        """Did every gate that COULD run, run?

        A survival rate over documents where this is False is a statement about
        our coverage, not about the corpus - and it is a statement that a fix
        would change, which is what makes it worth acting on.

        **`not_applicable` is deliberately not counted here.** A document with
        no author has been gated as fully as it ever can be; waiting for that
        to resolve waits forever. It still makes the survival figure an upper
        bound, and `TriageRun.describe` says so separately, because the two
        caveats have different remedies: one is "build the detector", the other
        is "this is the corpus you have".
        """
        return not self.unavailable


def wrong_language(doc: Document, *, allowed: frozenset[str] | None) -> bool | NotRun:
    """True drops. Two ways to produce no verdict, and they are different.

    No allow-list is `UNAVAILABLE`: nothing is configured, and configuring it
    fixes every document at once. No detected language is `NOT_APPLICABLE`:
    this document has no `lang` to test.

    Treating NULL as English would pass every document while looking like a gate.

    **THE ORDER MATTERS AND IT IS NOT ARBITRARY.** `allowed is None` is checked
    first, so while no allow-list exists this reports `UNAVAILABLE` for the whole
    corpus rather than `NOT_APPLICABLE` for every document. Today that is the
    truthful answer twice over: `document.lang` is nullable and nothing
    populates it - no detector is installed, and none is declared in
    `pyproject.toml` - so the per-document absence is itself systemic. Reporting
    it as permanent would be wrong in the direction that hides a build defect.
    """
    if allowed is None:
        return NotRun.UNAVAILABLE
    if doc.lang is None:
        return NotRun.NOT_APPLICABLE
    return doc.lang.split("-", 1)[0].casefold() not in allowed


def too_short(doc: Document) -> bool:
    """True drops. Under `MIN_TOKENS` tokens AND carrying no artifact.

    The conjunction is the point. `TypeError: 'NoneType' object is not
    subscriptable` is a complete bug report in eleven tokens; "this is amazing"
    is four and is nothing. Length alone cannot tell them apart.
    """
    text = doc.text
    return len(_TOKEN.findall(text)) < MIN_TOKENS and not has_artifact(text)


def pure_link_post(doc: Document) -> bool | NotRun:
    """True drops. A link with no commentary of the poster's own.

    **A link post WITH commentary is kept**, and that is not a detail: of 536
    link posts in the substitution corpus, 392 carry `selftext`. Dropping all
    536 would discard the commentary, which is the part an engineer wrote.

    `NOT_APPLICABLE` where the platform has no notion of a link post, so a blog
    article does not get dropped by a Reddit-shaped rule. Permanent by nature:
    no amount of building gives a blog article a link-post flag, and this is the
    gate that made the old single `unavailable` count grow as coverage improved.
    """
    if doc.is_self_post is None:
        return NotRun.NOT_APPLICABLE
    if doc.is_self_post:
        return False
    return not (doc.body or "").strip()


def out_of_window(
    matched: tuple[str, ...],
    *,
    population: SurfacePopulation,
    in_window: Mapping[str, bool],
) -> bool | NotRun:
    """True drops. Every model this document names is outside the release window.

    Takes the surfaces the entity gate already matched rather than the document,
    so the population is applied once per document and both gates are guaranteed
    to be reasoning about the same match set.

    **NOT_APPLICABLE, not False, in three cases**, because each is a place where
    a definite answer would be invented. All three are properties of the
    document rather than of the build - nothing is missing from `collect/`, the
    document simply cannot be placed - so none of them is `UNAVAILABLE`:

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
        return NotRun.NOT_APPLICABLE

    verdicts: list[bool] = []
    for surface in matched:
        owners = population.owners.get(surface, ())
        for owner in owners:
            if owner in in_window:
                verdicts.append(in_window[owner])
    if not verdicts:
        return NotRun.NOT_APPLICABLE
    # Any in-window model keeps the document. `all(out)` is the only drop.
    return not any(verdicts)


def known_bot(doc: Document, *, bots: BotList | None) -> bool | NotRun:
    """True drops. FOUR answers, and three of them are not `False`.

        bots is None            UNAVAILABLE. Rule 5 puts a filter rule in
                                `contract/` and there is no bot list there.
                                `collect/triage/bots.py:load_bot_list` returns
                                None for an absent file rather than an empty
                                list, because "nothing is curated" and "the
                                list declares no bots" are different claims.

        the source is not
        declared in the list    UNAVAILABLE, for THIS document. A platform
                                nobody has read is a curation gap - fixable
                                once, for everyone - so the count SHRINKS as
                                each platform is curated. That is what makes it
                                UNAVAILABLE and not NOT_APPLICABLE, which is
                                permanent.

        no source or no
        author id on the row    NOT_APPLICABLE. A deleted account has no
                                identity to test against any list, and never
                                will.

        otherwise               a real verdict, and `accounts: []` on a
                                declared source makes it `False` - somebody
                                looked and found none, which is a measurement.

    ⚠  MATCHED ON THE STABLE ACCOUNT ID, NOT THE HANDLE, and the handle is not
       consulted at all. This changed on 2026-09-07 and the old behaviour was
       not equivalent: a login is mutable wherever renames exist, so a list
       keyed on one stops matching after a rename with no error and no count.
       `author.external_id` is what `document.author_id` resolves through, so
       the list is keyed on the same thing the voice count is.

       The one platform where the id IS a username is Hacker News, which has no
       rename feature - declared as an `id_space` in the list rather than left
       to look like a mistake.
    """
    if bots is None:
        return NotRun.UNAVAILABLE
    if doc.source is None or doc.author_external_id is None:
        return NotRun.NOT_APPLICABLE
    if not bots.declares(doc.source):
        return NotRun.UNAVAILABLE
    return bots.contains(doc.source, doc.author_external_id)


def counted_bot(doc: Document, *, bots: BotList | None) -> bool | NotRun:
    """True FLAGS, and never drops. The weight half of the bot list.

    Same four answers as `known_bot` and the same inputs, and the difference is
    entirely in what the caller does with True: `triage` puts this on
    `TriageResult.flags` and leaves the verdict alone.

    WHY IT IS A SEPARATE LIST AND NOT A SEVERITY ON ONE. Rule 8's reviewer
    question is *what population was this filter's error rate measured on, and
    did the filter, or anything upstream of it, choose that population?* For the
    26 accounts under `known_bot` the answer is the platform's own: `user.type
    == "Bot"` is GitHub declaring it, and we chose nothing. For the 7 here the
    answer is that we grepped `bot` out of the logins in an export we gathered -
    which is the trap the rule names, and `FacultativeObligatoryBotContract` is
    what it looks like when it fires: almost certainly a person with a joke
    name, and one comment.

    So these are counted where somebody can see the cost of acting on them, and
    they are promoted by MOVING the id from `counted` to `accounts` in
    `contract/bots.yaml` - which changes the list's fingerprint, so a verdict
    that moved cannot be mistaken for one that did not.
    """
    if bots is None:
        return NotRun.UNAVAILABLE
    if doc.source is None or doc.author_external_id is None:
        return NotRun.NOT_APPLICABLE
    if not bots.declares(doc.source):
        return NotRun.UNAVAILABLE
    return bots.counts(doc.source, doc.author_external_id)


def triage(
    doc: Document,
    *,
    population: SurfacePopulation,
    allowed_languages: frozenset[str] | None = None,
    bots: BotList | None = None,
    in_window: Mapping[str, bool] | None = None,
) -> TriageResult:
    """Run EVERY gate. No short-circuit, and that is deliberate.

    Stopping at the first rejection would make `unavailable` mean two things at
    once - "this gate cannot run" and "this gate was not reached" - and the whole
    value of the field is that it means only the first. The gates are a regex and
    a set lookup; running all six costs nothing worth having an ambiguity for.

    That argument is why `NotRun` has two members rather than one: it was made
    about reachability and it applies just as well to the reason a gate declined,
    which the single `unavailable` tuple went on conflating anyway.

    It also gives `/filtered` every trigger a document hit rather than the
    earliest one, which is what "sorted by how close it came to passing" needs.

    THE SUBJECT GATE READS THE THREAD ROOT WHERE ONE IS SUPPLIED (2026-09-08).
    `doc.thread_subject_text` carries it, and only for a platform whose subject
    line is a separate record - Hacker News alone today. The order below is the
    permission's whole scope, so it is worth reading as three separate facts:

      1. THE DOCUMENT'S OWN TEXT IS RESOLVED FIRST and wins. A comment that
         names a model itself is not an inherited document and is not counted
         as one, however clearly its thread root also names one.
      2. THE ROOT IS RESOLVED ONLY IF THE DOCUMENT RESOLVED NOTHING. This is
         what makes it a fallback rather than an expansion of the match set,
         and it is why `inherited_surfaces` and `matched_surfaces` can never
         both be populated.
      3. `out_of_window` IS GIVEN `matched` AND NEVER THE UNION. An inherited
         subject may KEEP a document and may never DROP one - a comment placed
         outside a release window on the strength of a model named only in a
         title three replies up is precisely the invented definite answer rule
         6 forbids, and it would be invisible, because the document would be
         gone. Where the document's own text names nothing, `out_of_window`
         still returns NOT_APPLICABLE, exactly as it did before this change.
    """
    resolution = resolve_with_near_misses(doc.text, population)
    matched = resolution.hits
    inherited = (
        resolve(doc.thread_subject_text, population)
        if not matched and doc.thread_subject_text
        else ()
    )

    outcomes: list[tuple[str, bool | NotRun]] = [
        (LANGUAGE, wrong_language(doc, allowed=allowed_languages)),
        (PURE_LINK, pure_link_post(doc)),
        (TOO_SHORT, too_short(doc)),
        (NO_ENTITY, not (matched or inherited)),
        (
            # `matched`, NOT the union. See point 3 above.
            OUT_OF_WINDOW,
            out_of_window(matched, population=population, in_window=in_window or {}),
        ),
        (KNOWN_BOT, known_bot(doc, bots=bots)),
    ]
    # NOT IN `outcomes`, because everything in that list can drop the document.
    # A flag is computed beside the gates and cannot reach `reasons`.
    counted = counted_bot(doc, bots=bots)

    reasons = tuple(name for name, out in outcomes if out is True)
    unavailable = tuple(name for name, out in outcomes if out is NotRun.UNAVAILABLE)
    not_applicable = tuple(
        name for name, out in outcomes if out is NotRun.NOT_APPLICABLE
    )

    return TriageResult(
        verdict=Verdict.DROPPED if reasons else Verdict.KEPT,
        reasons=reasons,
        unavailable=unavailable,
        not_applicable=not_applicable,
        matched_surfaces=matched,
        inherited_surfaces=inherited,
        flags=(
            (KNOWN_BOT_COUNTED,) if counted is True else ()
        ) + ((NEAR_MISS,) if resolution.only_near_misses else ()),
        near_miss_surfaces=resolution.near_misses,
        population_fingerprint=population.fingerprint,
    )


@dataclass
class TriageRun:
    """Counts over a batch, and the caveat that must travel with them."""

    kept: int = 0
    dropped: int = 0
    by_reason: dict[str, int] = field(default_factory=dict)
    #: Gates that could not run, by name. Falls to empty when the build catches
    #: up - so a shrinking figure here is progress.
    never_ran: dict[str, int] = field(default_factory=dict)
    #: Gates with nothing to run on, by name. GROWS with the corpus and that is
    #: not a regression: every blog article adds one. Kept apart from
    #: `never_ran` for exactly that reason.
    not_applicable: dict[str, int] = field(default_factory=dict)
    #: Non-dropping observations, by name. THE NUMBER THAT DECIDES WHETHER A
    #: JUDGEMENT SHOULD BECOME A GATE: it is what the check WOULD have dropped,
    #: measured on documents it did not drop. Rule 8's evidence, in a counter.
    by_flag: dict[str, int] = field(default_factory=dict)
    #: Documents the subject gate kept on their THREAD'S subject rather than
    #: their own text. Counted separately because they were triaged at a
    #: DIFFERENT READING UNIT, and a survival rate that pools two units is a
    #: figure about our reading rather than about the corpus (rule 7). Zero on
    #: every platform whose subject sits inside the document.
    subject_inherited: int = 0
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
                f"  GATES THAT COULD NOT RUN: {missing}. This survival rate is an "
                "UPPER BOUND - documents these gates would have dropped are "
                "counted as kept. BUILDING THEM RESOLVES IT."
            )
        if self.not_applicable:
            na = ", ".join(
                f"{g} ({n})"
                for g, n in sorted(self.not_applicable.items(), key=lambda kv: -kv[1])
            )
            lines.append(
                f"  GATES WITH NOTHING TO RUN ON: {na}. Also an upper bound, and "
                "a PERMANENT one - these documents lack the input, so no amount "
                "of building changes the figure."
            )
        for flag, count in sorted(self.by_flag.items(), key=lambda kv: -kv[1]):
            lines.append(
                f"  FLAGGED, NOT DROPPED: {flag} on {count} of {self.total} "
                f"triaged ({100 * count / self.total:.1f}%). These documents "
                "were KEPT. This is what promoting the check to a gate would "
                "cost, measured on the documents it did not drop - which is "
                "the evidence rule 8 asks for before a weight becomes a gate."
            )
        if self.subject_inherited:
            share = 100 * self.subject_inherited / self.total
            lines.append(
                f"  SUBJECT INHERITED FROM THE THREAD ROOT: "
                f"{self.subject_inherited} of {self.total} triaged "
                f"({share:.1f}%), which is {self.subject_inherited} of "
                f"{self.kept} kept. THESE WERE TRIAGED AT A DIFFERENT READING "
                "UNIT - the subject came from the thread root and not from the "
                "document - so this survival figure is over a MIXED "
                "population. Quote the two apart, or say they are pooled."
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
        for gate in r.not_applicable:
            run.not_applicable[gate] = run.not_applicable.get(gate, 0) + 1
        for flag in r.flags:
            run.by_flag[flag] = run.by_flag.get(flag, 0) + 1
        if r.subject_was_inherited:
            run.subject_inherited += 1
    return results, run
