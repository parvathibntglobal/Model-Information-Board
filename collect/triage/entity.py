"""E4 — the resolvable-model-entity gate, and the population it resolves against.

A document naming no model we hold is not evidence about any model, so it never
reaches a paid call. That is the cheapest gate in the stage and, since the
registry went from 11 models to 340, the one whose verdict moved most.

WHY THIS GATE NEEDS A POPULATION OBJECT AND NOT A LIST OF STRINGS
------------------------------------------------------------------
Measured over the 1,297-post substitution corpus, changing ONLY the surfaces and
not a single document:

    hand-written (11 seeded models, 59 surfaces)   drops 20.4%
    registry mechanical (340 models, 1,263)        drops 16.8%
    + vendor-drop rule (1,314)                     drops  9.1%

**225 documents - 17.3% of that corpus - flip verdict between the first and the
third.** A gate whose answer depends on a file that changes weekly, against a
registry that changes nightly, is not reproducible from the document alone. It
is reproducible from (document, population), so the population has to be a thing
with an identity that can be written down beside the verdict.

Hence `SurfacePopulation.fingerprint`. `pipeline_version` does not cover this: it
tracks what `collect/` DOES, and this gate's answer changes when the registry
grows without a line of code changing. Two runs at the same `pipeline_version`
can legitimately disagree, and only the fingerprint makes that visible instead of
silent.

THE POPULATION IS A UNION, AND EACH PART EARNS ITS PLACE
--------------------------------------------------------
    MECHANICAL   spacing/hyphenation/concatenation over all 340 registry ids.
                 This is what makes the gate track releases: `qwen3.8-27b` is
                 resolvable the night it is polled, not the week somebody writes
                 an alias for it. Measured: a `qwen 3.8 27b` document is DROPPED
                 by the hand-written list and KEPT by this one.
    VENDOR-DROP  the rule the corpus supplied - people write `opus 5`, not
                 `claude opus 5`. Largest single gain: 16.8% -> 9.1%.
    DECLARED     the hand-written surfaces from `contract/seed_models.yaml`.
                 NOT redundant. 27 of them are reachable by no derivation:

                     reorderings the rule refuses   flash 2.5 - pro 2.5
                     letter-prefixed versions       r1 - deepseek reasoner
                     tier vocabulary nothing derives mistral large 3 - v4 flash

                 A registry-only population rejects a document naming
                 `deepseek r1`. That is 39 documents in the corpus above, and
                 dropping them would be losing human judgement the corpus has
                 already corroborated.

FAMILY WORDS ARE EXCLUDED FROM ALL THREE
-----------------------------------------
A bare `opus` names a line, not a tier. 62% of family-word mentions carry no
version at all, so admitting them would keep documents that name nothing
specific enough to file a claim against - and `classify_specificity` ranks the
resulting claim `family`, which `judge/vet/weight.py` weights at 0.3 against
1.0 for a snapshot. The gate would pass a document that cannot lift a cell.

`mechanical_variants` and `rule_variants` already refuse them; the declared list
does not, so this module filters. Three of the 27 declared-only surfaces are
exactly `opus`, `sonnet` and `haiku`, and they are dropped here on purpose.

THIS EXCLUSION IS A SPECIFICITY RULING, NOT A MATCHER RULE
----------------------------------------------------------
**Ruled 2026-08-21 after a version-adjacency rule was proposed, measured and
refused. Recorded here rather than only in the report, because the report is
where a reason goes to be re-litigated.**

The proposal was reasonable: the exclusion is right on an isolated `air` and
wrong on a family word standing next to a version, so admit the word when a
version is adjacent. `docs/measurements/family-words-and-a-nondeterminism.md`
has the four-arm run. Two facts killed it, and only the second is interesting.

FIRST, MECHANICALLY, IT BUYS NOTHING. Admitting all three surfaces recovers 0 of
40 labelled rows and costs 0 of 750 control documents; Tier 2 stays at exactly
0.0%. `build_population` records no owner for a declared surface no derivation
produces (rule 6 - it will not guess which model a human meant), so an admitted
`opus` resolves to *nothing*, and the best any adjacency rule achieves is moving
a row from "no surface matched" to "matched, owned by nobody".

SECOND, AND THIS IS THE REASON: the recovery it appears to offer is a
misattribution. `contract/seed_models.yaml` DOES name a model for each bare word,
deliberately and with a comment saying so - and this is what it names:

    opus   -> anthropic/claude-opus-5      specificity=family
    sonnet -> anthropic/claude-sonnet-5    specificity=family
    haiku  -> anthropic/claude-haiku-4-5   specificity=family

Now take the row the proposal was built to recover. `sonnet` in *"LLM
Comparison/Test: New API Edition (Claude 3 Opus & Sonnet + Mistral Large)"*,
posted **2024-03-11**, about Claude 3. Resolving through the family word attaches
that engineer's comparison to **Claude Sonnet 5**, which did not exist when they
wrote it. Not a vague claim about a line - a definite claim about the wrong
model, which is the thing `collect/surface_resolver.py` refuses ambiguity for:
*"an unresolved claim is a counted absence, and a mis-resolved one is evidence
against the wrong model."*

A version being ADJACENT is not the same as the version being the one the surface
means, and no window size closes that gap. `Claude 3` next to `Sonnet` tells you
the writer meant Claude 3 Sonnet, and the population's answer for `sonnet` is
Sonnet 5. The rule would read the context correctly and resolve incorrectly.

SO THE COST IS REAL AND IT IS NOT PAID HERE. Measured over the 1,297-post
substitution corpus, counting each (document, bare word) pair once: **1,026 of
23,044 mentions - 4.45%** - are bare `opus`, `sonnet` or `haiku` that the seed
file could attribute, over 692 documents, of which 48 would newly pass the gate.
Denominator is 18,090 matched surface occurrences plus 4,954 bare family words
declined; the corpus is Reddit-only and every post in it was retrieved by a query
naming a model, so this is not a rate about a platform. 4.45% is not negligible -
which is exactly why the answer is a ruling and not a threshold.

`oqocfjv` IS SETTLED, FROM FOUR DIRECTIONS - 2026-08-21
-------------------------------------------------------
*"Fable uses up more tokens than a old Porsche gas"* - the only first-hand
capability observation in the seven documents. It stays invisible, and the reason
is now closed rather than open:

    NOT by inheritance          a thread-subject rule was measured and ruled out.
                                32 of 53 candidates name a second model and the 21
                                survivors are all in announcement threads. And it
                                would not have reached this comment anyway.
    NOT by the word list        an adjacency rule recovers 0 of 40 labelled rows
                                and costs 0 of 750 control documents.
    NOT by any change to        there is NO DIGIT ANYWHERE in the text. Every rule
    this file                   proposed tests for a version token, and there is
                                none to find, at any window size.
    ONLY as a family claim,     and nothing declines to count them. Measured:
    if something declined       `judge/curate/gate.py:count` never reads
    to count it                 specificity, so twelve family claims reach
                                `N_EFF_MINIMUM` and clear `WIDELY_PRAISED_VOICES`
                                on the way.

THE PROTECTION IS THIS FILE REFUSING TO PRODUCE FAMILY CLAIMS, NOT THE GATE
REFUSING TO COUNT THEM. That is a different sentence from the one this ruling
was first written with, and it is the true one. `_admissible` excluding the bare
words is the only thing standing between a family-specificity claim and a
published cell - there is no second line of defence downstream, and the sentence
in `propose.py` that said there was has been corrected.

Which sharpens what this exclusion is for. It is not a hint to be relaxed once
somebody handles families properly downstream; it is currently load-bearing on
its own. **Anything that admits family words has to arrive together with the
counting rule, not before it.** Reversing that order makes the only first-hand
observation we have the first family claim to lift a cell.

WHAT WOULD ACTUALLY RECOVER `oqocfjv`
-------------------------------------
*"Fable uses up more tokens than a old Porsche gas"* is the only first-hand
capability observation in the seven, and `fable` is bare with **no digit anywhere
in the text**. An adjacency rule tests for a version token that is not there, so
it cannot reach this at any window size. Every arm measured returns NO MATCH.

Recovering it needs a ruling on **whether a family-specificity claim may be
stored and displayed at all**, and on what a page says when it holds one - not a
change to this word list.

MEASURED SINCE, and it changes the shape of that ruling. `family` is a permitted
`Specificity` value and the gate does NOT refuse it: `judge/curate/gate.py:count`
never reads specificity, so a family claim is one `independent_voices` like any
other, and 0.3 enters only through `n_eff`. Best single family claim is 0.255 on
Reddit and 0.285 on GitHub against `N_EFF_MINIMUM = 3.0`, so **twelve family
claims publish a cell**. The weight is a 3x higher bar, not a refusal - and the
cell would land on `anthropic/claude-opus-5`, which is the misattribution above
arriving through the weighting instead of through resolution.

Two mechanisms currently prevent it anyway, both incidental: `model_alias` holds
**0 family rows** (82 snapshot, 23 version), and every `model_version` row is
`provenance='polled'`, so the seed file's 13 family aliases have never been
loaded. A family claim has no owner to resolve to today by accident rather than
by rule. `docs/measurements/inherited-subjects-and-family-claims.md`.
That is a shared decision touching
`judge/vet/weight.py`'s 0.3, `judge/curate/gate.py` (which counts a family claim
as an independent voice today, so `propose.py`'s "never counts as independent
corroboration" overstates what the code does), and rule 4's display side. It is
not E1's to take alone and it is not a matcher change.

**Until that ruling exists, do not touch FAMILY_WORDS.** Anyone arriving here
with the adjacency idea should read the run above first: it is measured, it is
zero, and the zero is not the argument.

REOPENED 2026-08-21 ON A CORPUS WHERE FAMILY WORDS ARE HOW PEOPLE WRITE, AND
THE MEASUREMENT MOVED THE QUESTION OFF THIS FILE
---------------------------------------------------------------------------
Reopened because the exclusion had been the binding constraint four times and
each measurement had called the cost small separately. Correct reasoning. The
numbers, on 140 blog claims from six feeds:

    133 of 140 resolve to no model
     26 are a BARE family mention   Codex 11 - Claude 6 - Gemini 4 -
                                    ChatGPT 3 - Mistral 1 - Deepseek 1
     80 contain no family word AT ALL   LLM 15 - AI 6 - model 4 - agents 4

So 60% of the loss is unreachable by any ruling about this constant: those
authors wrote a category noun, not a family.

**AND THE OTHER 26 ARE NOT BLOCKED HERE EITHER.** `claim.model_version_id` is
NOT NULL, and a family is a COLUMN on `model_version`, not a ROW - there is no
row meaning "the Claude family". Emptying FAMILY_WORDS would make `resolve()`
return version surfaces, and `judge/pipeline.py:372` would drop the claim one
line later for having no destination. Same zero, further down.

So this file is not the binding constraint and changing it does not help. The
question is whether a family-shaped destination should exist, which is a
contract and `judge/` ruling:
`docs/proposals/for-engineer-2-reopening-the-family-word-ruling.md`.

The instruction above stands, now for a better reason: **not "the cost is small"
but "the cost is not paid here".**

NO MODEL PARTICIPATES. Substring matching over a normalised string.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from collect.registry.propose import (
    FAMILY_WORDS,
    MIN_SURFACE_CHARS,
    is_route,
    mechanical_variants,
    rule_variants,
)

#: Where a surface came from. Carried into the population so a reviewer reading a
#: verdict can tell a derivation from a human's judgement.
MECHANICAL = "mechanical"
VENDOR_DROP = "vendor-drop"
DECLARED = "declared"

_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def normalize(text: str) -> str:
    """Casefold and strip everything that is not alphanumeric.

    The matching key, deliberately the same shape as
    `registry.aliases.normalize`: `GPT-4.1 mini`, `gpt 4.1 mini` and `gpt4.1mini`
    all become `gpt41mini`, so a document is matched however the writer spaced
    it. Duplicated rather than imported because that function takes a SURFACE and
    this takes a DOCUMENT, and the two will diverge the moment either grows a
    rule about its own input.
    """
    return _NON_ALNUM.sub("", text.casefold())


def normalize_with_boundaries(text: str) -> tuple[str, list[bool], list[bool]]:
    """`normalize`, plus which normalised positions began and ended a word.

    THE REASON THIS EXISTS IS A DEFECT THE TIER-2 CONTROL FOUND. Matching a
    surface as a plain substring of the space-stripped text is wrong in a way
    that is invisible on an AI corpus and obvious on a corpus about cooking:

        `saba`   matched inside "wa[s a ba]d"     -> mistralai/mistral-saba
        `fusion` matched inside "con[fusion]"     -> openrouter/fusion
        `free`   matched inside "[free]ze"        -> openrouter/free

    Stripping spaces is LOAD-BEARING and cannot simply be dropped: it is what
    makes `gpt-4.1 mini`, `gpt 4.1 mini` and `gpt4.1mini` one surface. So the
    separators are removed for matching and remembered for bounding.

    Returns the key, plus two parallel masks: `starts[i]` is True when
    normalised character `i` was the first character of a word in the original,
    and `ends[i]` is True when it was the last. A match from `i` to `j` is
    admissible only when `starts[i]` and `ends[j - 1]`.

    `claude opus 5` still matches `claudeopus5` because the run begins at a word
    start and ends at a word end in both spellings. `saba` inside `was a bad`
    does not, because it begins mid-word.
    """
    key, starts, ends, _sources = normalize_with_offsets(text)
    return key, starts, ends


def normalize_with_offsets(text: str) -> tuple[str, list[bool], list[bool], list[int]]:
    """`normalize_with_boundaries`, plus WHERE each kept character came from.

    THE ONE IMPLEMENTATION. `normalize_with_boundaries` delegates here and drops
    the fourth value, so the two cannot describe the string differently - which
    matters more than the duplication it saves, because a boundary mask and an
    offset map that disagree would place a match at a position it did not occupy.

    `sources[i]` is the index in the ORIGINAL `text` of normalised character
    `i`. So a match spanning normalised `[i..j]` occupied original
    `[sources[i] .. sources[j]]`, and `text[sources[j] + 1:]` is what FOLLOWED
    it - the thing the caller could not previously see.

    WHY THIS EXISTS, AND IT IS THE SAME REASON `offset_map` DOES
    -------------------------------------------------------------
    `normalize` strips every non-alphanumeric, so `fable 5.1` and `fable 51`
    both become `fable51`. The boundary masks separate them correctly - the dot
    is a separator, so `ends[]` is True after the `5` in the first and False in
    the second - and that is exactly the problem: **a version dot is a word
    boundary and is not a version boundary.** `fable 5` is therefore an
    admissible match inside `fable 5.1`, and the resolver has no way to tell,
    because the character that would tell it was discarded.

    Measured 2026-09-08: **36 of 192** documents in a new-platform corpus and
    **20 of 5,010** on staging resolve to a model ONLY through a surface the
    original text continues as a version - 35 of them filed against
    `anthropic/claude-fable-5` when the text said `Fable 5.1`. That is not a
    miss, it is a wrong answer with nothing on the row to disagree with.
    `docs/measurements/near-miss-misattribution-2026-09-08.json`.

    **Those figures are a FLOOR and this function is why.** They were measured
    from outside the resolver by re-locating each surface in the original with a
    separator-flexible regex, and that cannot locate a surface which matched
    only in normalised space - `fable5` against `"fable 5.1"`. 126 of 192 and
    3,035 of 5,010 documents had at least one such surface and were skipped
    rather than judged. With these offsets the question is answerable exactly,
    inside `resolve`, for every match.

    Ten lines while the string is already being walked, and impossible to
    reconstruct afterwards - `collect/CLAUDE.md`'s first rule, about a different
    artifact, for the same reason.
    """
    key: list[str] = []
    starts: list[bool] = []
    ends: list[bool] = []
    sources: list[int] = []
    at_start = True
    for index, char in enumerate(text.casefold()):
        if _NON_ALNUM.match(char):
            at_start = True
            if ends:
                ends[-1] = True
            continue
        key.append(char)
        starts.append(at_start)
        ends.append(False)
        # THE ORIGINAL INDEX, not the normalised one. `casefold()` can change a
        # string's LENGTH - German eszett becomes `ss` - so this is indexed
        # against the casefolded text and the caller must casefold before using
        # it. `_version_continues` does, and says so.
        sources.append(index)
        at_start = False
    if ends:
        ends[-1] = True
    return "".join(key), starts, ends, sources


@dataclass(frozen=True)
class SurfacePopulation:
    """The surfaces a triage run resolves against, and its identity.

    `fingerprint` is what makes a verdict re-runnable. Record it beside the
    verdict and a later disagreement is explicable; omit it and the same document
    silently changes answer as the registry grows.
    """

    surfaces: frozenset[str]
    #: source -> how many surfaces it contributed uniquely to the union.
    contributions: dict[str, int] = field(default_factory=dict)
    #: How many registry models the derived surfaces came from. Rule 7: the
    #: population's own denominator.
    model_count: int = 0
    declared_model_count: int = 0

    #: surface -> the canonical ids that produced it. USUALLY ONE, NOT ALWAYS:
    #: `gemini flash latest` is derivable from more than one id, and the
    #: substitution-corpus extract found 49 surfaces with 2 to 25 candidate
    #: models. A surface owned by several models resolves the ENTITY gate (a
    #: model is named) and cannot resolve attribution, so the two questions read
    #: this differently and neither may collapse it to `owners[0]`.
    owners: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        """Stable digest of the surface set. Sorted, so order cannot change it."""
        joined = "\n".join(sorted(self.surfaces))
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]

    @property
    def basis(self) -> str:
        """One line stating what this population is, for a log or a report."""
        parts = ", ".join(
            f"{name} {count}" for name, count in sorted(self.contributions.items())
        )
        return (
            f"{len(self.surfaces)} surfaces ({parts}) over {self.model_count} "
            f"registry models and {self.declared_model_count} declared, "
            f"fingerprint {self.fingerprint}"
        )


def _admissible(surface: str) -> bool:
    """Long enough to not collide with prose, and not a bare family word."""
    cleaned = surface.strip().casefold()
    return len(cleaned) >= MIN_SURFACE_CHARS and cleaned not in FAMILY_WORDS


def build_population(
    models: Sequence[tuple[str, str | None]],
    declared: Iterable[str] = (),
) -> SurfacePopulation:
    """The union, with family words excluded from every part.

    Args:
        models: (canonical_id, display_name) from `model_version`. Drives the two
            derived halves, so the gate tracks the registry rather than a file.
        declared: hand-written surfaces from `contract/seed_models.yaml`. Kept
            because 27 of them are reachable by no derivation - see the module
            docstring. Absent is allowed and means the gate runs on derivations
            only, which is a narrower population and not a broken one.
    """
    mechanical: set[str] = set()
    by_rule: set[str] = set()
    owners: dict[str, set[str]] = {}
    routes = 0
    for canonical_id, display_name in models:
        # ROUTES ARE NOT MODELS (ruled 2026-08-18, see `is_route`). A claim
        # about `free` resolves to a pointer, so the model that served the
        # request is unknown - unattributable by construction, which is what
        # FR-4 exists to prevent. They were also the largest source of false
        # entity matches: `openrouter/free` derives the surface `free`.
        if is_route(canonical_id):
            routes += 1
            continue
        derived = mechanical_variants(canonical_id, display_name)
        ruled = rule_variants(canonical_id, display_name)
        mechanical.update(derived)
        by_rule.update(ruled)
        for surface in (*derived, *ruled):
            owners.setdefault(surface, set()).add(canonical_id)

    hand = {s.strip().casefold() for s in declared if s and s.strip()}

    mechanical = {s for s in mechanical if _admissible(s)}
    by_rule = {s for s in by_rule if _admissible(s)}
    hand = {s for s in hand if _admissible(s)}

    union = mechanical | by_rule | hand
    # Attribution is by precedence, not overlap: a surface both derived and
    # declared is counted once, under the derivation, because that is the half
    # that will keep producing it as the registry grows.
    contributions = {
        MECHANICAL: len(mechanical),
        VENDOR_DROP: len(by_rule - mechanical),
        DECLARED: len(hand - mechanical - by_rule),
    }

    # A declared surface no derivation produced has no owner here. That is not a
    # gap to fill by guessing which model a human meant: `contract/seed_models.yaml`
    # knows, this function was not given it, and an absent owner stays absent
    # rather than becoming a plausible one (rule 6).
    return SurfacePopulation(
        surfaces=frozenset(union),
        contributions=contributions,
        # Routes are excluded, so the denominator is models and not feed rows.
        model_count=len(models) - routes,
        declared_model_count=len(hand),
        owners={s: tuple(sorted(o)) for s, o in owners.items() if s in union},
    )


def resolve(text: str, population: SurfacePopulation) -> tuple[str, ...]:
    """Every surface in `population` that appears in `text`. Sorted, longest first.

    Longest first because the useful answer is the most specific one: a document
    containing `claude opus 5` matches `opus 5` as well, and a caller taking the
    first match should get the one that names the most.

    Returns an empty tuple where nothing matches, which is what the gate drops
    on. That empty tuple is a MEASUREMENT - the population was applied and found
    nothing - and it is only meaningful beside `population.fingerprint`.
    """
    haystack, starts, ends = normalize_with_boundaries(text)
    if not haystack:
        return ()

    hits = []
    for surface in population.surfaces:
        needle = normalize(surface)
        if not needle:
            continue
        # Every occurrence, not just the first: `free` may appear inside
        # `freeze` earlier in the document and standing alone later, and only
        # the second is a mention.
        at = haystack.find(needle)
        while at >= 0:
            if starts[at] and ends[at + len(needle) - 1]:
                hits.append(surface)
                break
            at = haystack.find(needle, at + 1)
    return tuple(sorted(hits, key=lambda s: (-len(normalize(s)), s)))


#: A match is a NEAR MISS when the original text continues it as a VERSION.
#: `.1` and `-preview` after `fable 5`; a bare digit for the same reason.
#:
#: DELIBERATELY NARROW, AND A DIGIT IS REQUIRED. `fable 5-preview` therefore
#: still resolves to `fable 5`, which is a known exclusion rather than an
#: oversight: widening to any word suffix would have to defend `gpt-4-turbo` and
#: `opus-5-thinking`, where the suffix sometimes names a different model and
#: sometimes a mode of the same one. The 1,641-document measurement was taken on
#: this rule, so widening it means re-measuring rather than re-reasoning.
#: `opus 5 turbo` also still resolves - `turbo` may be somebody's adjective.
_VERSION_CONTINUES = re.compile(r"[.\-]\d|\d")


def _version_continues(text: str, after: int) -> bool:
    """Does `text` continue a version immediately after index `after`?

    `after` is an index into the CASEFOLDED text, because that is what
    `normalize_with_offsets` indexes against - `casefold()` can change a
    string's length, so the two must agree on which string they mean.
    """
    return bool(_VERSION_CONTINUES.match(text[after + 1 : after + 3]))


@dataclass(frozen=True)
class Resolution:
    """What the surfaces in a text resolve to, and what they nearly resolved to.

    TWO FIELDS BECAUSE THEY HAVE OPPOSITE CONSEQUENCES. `hits` keeps a document
    and attributes it; `near_misses` is a surface that matched only because the
    text continues it as a version, and attributing on one is silent
    misattribution.
    """

    hits: tuple[str, ...]
    #: Surfaces whose EVERY occurrence in this text is continued as a version.
    #: A surface appearing once as `fable 5.1` and once as `fable 5` is a HIT
    #: and is absent here: one real mention is a mention, and this field must
    #: never be read as "this surface is unreliable in general".
    near_misses: tuple[str, ...] = ()

    @property
    def only_near_misses(self) -> bool:
        """Did EVERY surface that matched do so inside a longer version string?

        The condition under which attribution is certainly wrong: the model this
        document would be filed against is not the model it discusses.

        ⚠  `near_misses` IS A SUBSET OF `hits`, WHICH THE FIRST VERSION OF THIS
           PROPERTY GOT WRONG. It read `bool(self.near_misses) and not
           self.hits`, and `hits` is never empty when `near_misses` is not - so
           it returned False always, including on the `Fable 5.1` document that
           motivated the whole change. The comparison has to be between the two
           sets, not a truthiness test on one.

           Third instance in three days of the same slip: reading a SUBSET as a
           DISJOINT SET. The other two were counting surfaces where the question
           was models. Worth the sentence, because a property that silently
           answers False is exactly the shape rule 4 is about.
        """
        return bool(self.near_misses) and set(self.near_misses) == set(self.hits)

    def owners(self, population: SurfacePopulation) -> tuple[set[str], set[str]]:
        """The models reached CLEANLY, and the models reached only by near miss.

        AT THE OWNER LEVEL, because that is the level attribution happens at and
        the level the surface counts keep getting mistaken for. One model has
        several surfaces - `fable 5`, `fable-5`, `fable5` are one model - so a
        count of surfaces answers a question nobody asked (rule 7).

        The second set minus the first is the actionable one: models this
        document would be filed against and should not be.
        """
        clean: set[str] = set()
        near: set[str] = set()
        near_set = set(self.near_misses)
        for surface in self.hits:
            target = near if surface in near_set else clean
            target |= set(population.owners.get(surface, ()))
        return clean, near - clean


def resolve_with_near_misses(
    text: str, population: SurfacePopulation
) -> Resolution:
    """`resolve`, plus the near misses it silently accepted.

    ⚠  `hits` IS EXACTLY WHAT `resolve` RETURNS, INCLUDING THE NEAR MISSES.
       Resolution is UNCHANGED by this function existing, deliberately: rule 8's
       direction is one-way, so the near miss ships as a RECORDED field first
       and becomes a refusal later on the evidence this field produces. Flipping
       both at once would replace a measured defect (misattribution) with an
       unmeasured one (documents refused for naming a model we do not track),
       and only the first of those is currently counted.

       When it is flipped, the change is one line here - subtract `near_misses`
       from `hits` - and nothing else moves, because every caller that cares
       already reads the two apart.

    THE TWO WRONGS ARE NOT SYMMETRICAL, which is the argument for flipping
    eventually. Refusing loses the document and `near-miss-not-registered`
    counts it, so the loss is visible and carries its own fix - register the
    model. Misattributing files the evidence on another model's cell with no
    counter and no signal. That asymmetry, not caution, is why the destination
    is a refusal.
    """
    hits = resolve(text, population)
    if not hits:
        return Resolution(hits=())

    folded = text.casefold()
    _key, starts, ends, sources = normalize_with_offsets(text)
    haystack = _key

    near: list[str] = []
    for surface in hits:
        needle = normalize(surface)
        if not needle:
            continue
        occurrences = 0
        continued = 0
        at = haystack.find(needle)
        while at >= 0:
            if starts[at] and ends[at + len(needle) - 1]:
                occurrences += 1
                if _version_continues(folded, sources[at + len(needle) - 1]):
                    continued += 1
            at = haystack.find(needle, at + 1)
        # EVERY admissible occurrence, not the first. A surface that appears
        # once continued and once bare is a real mention of the shorter model,
        # and calling that a near miss would refuse a document that names it.
        if occurrences and continued == occurrences:
            near.append(surface)
    return Resolution(hits=hits, near_misses=tuple(near))


def names_a_model(text: str, population: SurfacePopulation) -> bool:
    """The gate itself. True keeps the document."""
    return bool(resolve(text, population))
