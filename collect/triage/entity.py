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
specific enough to file a claim against - and `classify_specificity` would rank
the resulting claim `family`, which never counts as independent corroboration.
The gate would pass a document that cannot lift a cell.

`mechanical_variants` and `rule_variants` already refuse them; the declared list
does not, so this module filters. Three of the 27 declared-only surfaces are
exactly `opus`, `sonnet` and `haiku`, and they are dropped here on purpose.

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
    key: list[str] = []
    starts: list[bool] = []
    ends: list[bool] = []
    at_start = True
    for char in text.casefold():
        if _NON_ALNUM.match(char):
            at_start = True
            if ends:
                ends[-1] = True
            continue
        key.append(char)
        starts.append(at_start)
        ends.append(False)
        at_start = False
    if ends:
        ends[-1] = True
    return "".join(key), starts, ends


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


def names_a_model(text: str, population: SurfacePopulation) -> bool:
    """The gate itself. True keeps the document."""
    return bool(resolve(text, population))
