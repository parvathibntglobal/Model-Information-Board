"""`collect/`'s side of `judge/`'s `SurfaceResolver`. A written surface to a model id.

The second code interface across the lane boundary, after
`collect/rawstore_reader.py`, and it exists for the same reason: `judge/` names
what it needs and cannot import this lane to get it.

WHAT WAS ACTUALLY BROKEN, WHICH WAS NOTHING
-------------------------------------------
`ModelRef.resolved_version_id` is a schema field with a `None` default that
**nothing ever wrote**. It occurs in exactly two non-test places in the
repository - the field in `judge/extract/schema.py`, and the read in
`judge/pipeline.py`. The extraction prompt never mentions it, so the model
correctly left it null; the pipeline then logged "resolves to no tracked model"
and skipped every claim.

So this was not a defect and not a registry problem. `entity.resolve()` has
worked the whole time and resolves the seven's text against 1,224 surfaces; it
was simply never called on the path that stores a claim, because that path had
never been walked end to end. Three unrelated blockers on one path is what an
unexercised path looks like.

RESOLUTION IS CODE'S (rule 2)
-----------------------------
The alternative was to ask the extractor for a canonical id and check it. That
would make an LLM decide identity rather than propose it, and it is strictly
worse than resolving here: the model would need the whole surface population in
its context, and a lucky guess at an id we happen to hold would be indistinguishable
from knowledge. The model proposes a surface exactly as the human wrote it, and
this maps it.

RESOLUTION IS BY NORMALISED KEY, AND THAT WAS A NONDETERMINISM
--------------------------------------------------------------
This looked up the surface by scanning `population.surfaces` for the first
member whose normalised form matched, and breaking. `surfaces` is a frozenset,
so "first" is iteration order, so it is PYTHONHASHSEED. That would not matter if
every spelling of one key agreed about its owner - and three of the 414 keys do
not, because `build_population` records owners per SPELLING and a declared
surface has no owner:

    gpt41mini     gpt 4.1 mini -> openai/gpt-4.1-mini    gpt-4.1 mini -> ()
                  gpt-4.1-mini -> openai/gpt-4.1-mini    gpt41mini    -> ()
                  gpt4.1mini   -> openai/gpt-4.1-mini
    gemini25pro   three spellings owned, `gemini 2.5pro` declared-only
    claudehaiku45 three spellings owned, `claude-haiku-4-5` declared-only

Measured: `RegistrySurfaceResolver("gpt-4.1 mini")` returned
`mv_ebd5240e5f207506` at PYTHONHASHSEED=3 and `None` at 1, 2, 4 and 5. Same
registry, same input, same fingerprint, different answer - a claim stored or
counted absent depending on the process. That is the reproducibility the whole
fingerprint apparatus exists to give, defeated inside the function it protects.

**Found by a measurement disagreeing with itself**, not by a test: three runs of
the same pool scoring script gave 50.0%, 52.5% and 55.0%, and one row flipped
between `no-owner` and `one-owner`.

So the lookup is now by normalised key, with owners UNIONED over the spellings
that share it. The union is the honest read rather than a convenience: an
unowned spelling is a declared surface whose owner `build_population` DECLINED
TO GUESS (rule 6), which is absence of information about the owner and not
evidence that there is none. Three spellings naming `openai/gpt-4.1-mini` and
two saying nothing is one owner, not a disagreement.

It also makes ambiguity reachable for the first time. Unioned, 414 keys are 396
one-owner, 17 zero-owner and **1 with two owners**: `commandr082024`, because
`normalize` strips `+` and collapses `command-r+ (08-2024)` onto
`command-r (08-2024)`. Two different Cohere models, one key. Zero occurrences in
the 1,297-post corpus, so it is rare and not impossible - and per-spelling it
was unreachable, which is why the corpus measured 0 multi-owner occurrences and
why that 0 was a property of the indexing rather than of the world.

AMBIGUITY COMES BACK None, AND THAT IS THE LOAD-BEARING PART
------------------------------------------------------------
A surface can be owned by several models - the substitution corpus found 49 with
between 2 and 25 candidates. Resolving one of those to whichever id sorts first
would attach a real quote to an arbitrary model, which is worse than dropping it:
an unresolved claim is a counted absence, and a mis-resolved one is evidence
against the wrong model. So a surface with more than one owner returns None and
is counted (rule 6).

BARE FAMILY WORDS ARE NOT REACHABLE FROM HERE, ON PURPOSE
---------------------------------------------------------
`fable`, `opus`, `sonnet` and the other 23 `FAMILY_WORDS` are excluded from the
population by `entity._admissible`, so they resolve to nothing and no seating
changes that. That exclusion costs real evidence - the only first-hand capability
observation in the seven is `oqocfjv`, *"Fable uses up more tokens than a old
Porsche gas"*, and it is invisible for exactly this reason. It is also what keeps
`pro` out of "problem" and `free` out of "freeze". This module does not relitigate
the trade; it makes the cost visible by counting what it refuses.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from collect.triage.entity import (
    SurfacePopulation,
    build_population,
    normalize,
    resolve,
    resolve_with_near_misses,
)


@dataclass
class ResolutionReport:
    """Every surface this resolver was asked about, and what happened.

    Kept because the interesting number is not how many resolved. A run that
    resolves 8 of 8 and a run that resolves 8 of 40 are different runs, and the
    32 are invisible in a claim count.
    """

    resolved: dict[str, str] = field(default_factory=dict)
    #: Asked about, matched nothing in the population at all. Usually a bare
    #: family word, a router, or a model we do not track.
    unmatched: list[str] = field(default_factory=list)
    #: Matched a surface owned by more than one model. Refused, not guessed.
    ambiguous: dict[str, tuple[str, ...]] = field(default_factory=dict)
    #: Matched a surface the population holds with NO owner at all - a declared
    #: surface from `seed_models.yaml` that no registry id derives. There are 23
    #: of them and they are common: 1,103 occurrences over the 1,297-post
    #: substitution corpus, `claude opus` 274 and `claude sonnet` 193.
    #:
    #: SPLIT OUT 2026-08-21, AND IT WAS COUNTED AS `ambiguous` BEFORE. Both
    #: return None, so nothing downstream was wrong - but this report exists to
    #: say what happened, and it was saying "several models answer to this
    #: spelling" about a surface no model answers to, with an empty candidate
    #: tuple beside it. Two opposite facts under one name is rule 6 in the
    #: counting rather than in the data: a reader tuning ambiguity would have
    #: been reading mostly this.
    no_owner: list[str] = field(default_factory=list)
    #: Matched an owner the registry holds no `model_version` row for. Should be
    #: impossible, since owners come from the registry; counted because
    #: "impossible" is how the last few defects in this repo described themselves.
    owner_without_row: dict[str, str] = field(default_factory=dict)
    #: The surface names a MORE SPECIFIC version than any alias we hold, so the
    #: longest containment match is a proper prefix of it and continues with a
    #: digit. `GPT-5.6 Sol Ultra` against a registry seating `gpt-5`, or
    #: `Claude 3.7 Sonnet` against one seating `claude 3`.
    #:
    #: REFUSED RATHER THAN ROUNDED DOWN, and this is the whole point: the
    #: previous behaviour resolved it to the shorter version with ONE owner and
    #: full confidence, so a claim about GPT-5.6 was filed against GPT-5 and
    #: nothing could see it. Not ambiguity - there was exactly one owner and the
    #: check for several was correct. Rounding an unknown-specific down to a
    #: known-general is rule 6 in the resolver.
    more_specific_than_seated: dict[str, str] = field(default_factory=dict)

    @property
    def asked(self) -> int:
        return (
            len(self.resolved)
            + len(self.unmatched)
            + len(self.ambiguous)
            + len(self.no_owner)
            + len(self.owner_without_row)
        )

    def summary(self) -> str:
        return (
            f"surface resolution: {len(self.resolved)} of {self.asked} resolved, "
            f"{len(self.unmatched)} matched no surface, "
            f"{len(self.ambiguous)} ambiguous, "
            f"{len(self.no_owner)} matched a surface no model derives, "
            f"{len(self.owner_without_row)} owned by a model with no row"
        )


class RegistrySurfaceResolver:
    """Satisfies `judge.pipeline.SurfaceResolver`. Reads the registry, once.

    Built from `model_version` rather than from `seed_models.yaml`, so the gate
    tracks what the poller actually holds. Declared surfaces are deliberately
    NOT folded in here: a declared surface with no derivation has no owner, and
    an owner is the whole output of this function.
    """

    def __init__(
        self,
        population: SurfacePopulation,
        model_version_id_of: Mapping[str, str],
    ) -> None:
        self._population = population
        self._id_of = model_version_id_of
        self.report = ResolutionReport()
        # OWNERS BY NORMALISED KEY, UNIONED ACROSS SPELLINGS. Built once here
        # rather than looked up per call, and it is a CORRECTNESS fix and not a
        # cache - see `__call__`.
        by_key: dict[str, set[str]] = {}
        for surface in population.surfaces:
            key = normalize(surface)
            if key:
                by_key.setdefault(key, set()).update(population.owners.get(surface, ()))
        self._owners_by_key = {k: tuple(sorted(v)) for k, v in by_key.items()}

    @classmethod
    def from_connection(cls, conn) -> RegistrySurfaceResolver:
        """The live registry. One query, no joins into `judge/`'s tables."""
        rows = conn.execute(
            "SELECT canonical_id, display_name, id FROM model_version"
        ).fetchall()
        population = build_population([(r[0], r[1]) for r in rows])
        return cls(population, {r[0]: r[2] for r in rows})

    def __call__(self, surface: str) -> str | None:
        """The written surface to a `model_version.id`, or None.

        EXACT NORMALISED MATCH FIRST, then containment. `normalize` folds
        `Fable 5`, `fable-5` and `fable5` together, so the surface a human wrote
        usually lands on a population member directly. Containment is the
        fallback for a surface carrying extra words - `Claude Opus 4.8 (xhigh)`
        - and takes the LONGEST match, because `entity.resolve` sorts longest
        first and the longest match is the most specific claim about identity.
        """
        cleaned = (surface or "").strip()
        if not cleaned:
            self.report.unmatched.append(surface)
            return None

        needle = normalize(cleaned)
        key: str | None = needle if needle in self._owners_by_key else None
        exact = key is not None
        if key is None:
            hits = resolve(cleaned, self._population)
            key = normalize(hits[0]) if hits else None
        if key is None:
            self.report.unmatched.append(cleaned)
            return None

        # ── THE SURFACE MAY BE MORE SPECIFIC THAN ANYTHING WE HOLD ──────────
        #
        # Containment only. An exact normalised match consumed the whole surface
        # and cannot be a prefix of it.
        #
        # `gpt-5` is the longest alias matching `GPT-5.6 Sol Ultra`, has exactly
        # ONE owner, and resolved with full confidence to a different model.
        # That is not ambiguity - the `len(owners) != 1` check below is correct
        # and its input was wrong. The tell is the character after the match: a
        # DIGIT means the version continues past everything we know about.
        #
        #   gpt56solultra    match gpt5          next `6`  -> refuse
        #   claude37sonnet   match claude3       next `7`  -> refuse
        #   claudeopus48xhigh match claudeopus48 next `x`  -> resolve, as before
        #
        # Refusing rounds nothing down. `Opus 4.8` against a registry holding
        # only `opus-4` is a claim about a model we do not track, and a counted
        # drop is what that is. Silently filing it under `opus-4` was the defect.
        #
        # ⚠ THE FIRST EXAMPLE STOPPED BEING TRUE ON 2026-09-16, AND NO CODE
        # CHANGED. `GPT-5.6 Sol Ultra` now resolves to `openai/gpt-5.6-sol`:
        #
        #   gpt56solultra    match gpt56sol      next `u`  -> RESOLVE
        #
        # The registry grew. When this was written the longest match was `gpt5`
        # and the next character was the `6` that fires the guard. The 5.6 family
        # arrived in `model_version`, `build_population` derives from it, so the
        # match got longer and the character after it is now a letter. The guard
        # is unchanged and correct on its own terms; its INPUT moved.
        #
        # Worth naming as its own failure mode: a comment made false by DATA
        # rather than by an edit. Nothing in a diff, a review or a test suite
        # looks at it - the example is prose, the population is a query, and the
        # two are only compared by a person reading both. That is also why the
        # example is kept above rather than rewritten into something currently
        # true: the next model to land re-breaks whatever we put there.
        #
        # It costs nothing TODAY - no `gpt-5.6-sol-ultra` is in the registry, so
        # the string is hypothetical. It stops costing nothing the moment a
        # vendor ships a suffix that is not a digit onto a name we already seat.
        # The durable fix is a boundary test rather than a digit test, and that
        # is a re-measurement (the 1,641-document rule in `entity.py`), not a
        # one-line change - so it is named here and not taken.
        if not exact:
            at = needle.find(key)
            if at >= 0 and needle[at + len(key):at + len(key) + 1].isdigit():
                self.report.more_specific_than_seated[cleaned] = key
                return None

        owners = self._owners_by_key.get(key, ())
        if not owners:
            # In the population and owned by nothing: a declared surface no
            # derivation produces. `build_population` refuses to guess which
            # model a human meant, so the owner is absent here and stays absent
            # (rule 6). NOT the same fact as ambiguity, and counted separately.
            self.report.no_owner.append(cleaned)
            return None
        if len(owners) != 1:
            # Several models answer to this spelling. An arbitrary pick would
            # attach a real quote to the wrong model, which is worse than
            # dropping it.
            self.report.ambiguous[cleaned] = tuple(owners)
            return None

        model_version_id = self._id_of.get(owners[0])
        if model_version_id is None:
            self.report.owner_without_row[cleaned] = owners[0]
            return None

        self.report.resolved[cleaned] = model_version_id
        return model_version_id


class RegistrySurfaceFinder:
    """Satisfies `judge.pipeline.SurfaceFinder`. Every surface in a text.

    The other direction from `RegistrySurfaceResolver`: that one is asked what a
    surface means, this one is asked whether a text names anything. `judge/`
    needs it to derive `subject_inherited` without importing this lane, and it
    is a thin wrapper over `entity.resolve` because the population and the
    boundary map already answer the question exactly.

    WHY judge/ CANNOT DO THIS ITSELF, and it is not a rule for its own sake: the
    answer depends on the surface population, which changes nightly as the
    registry polls. A copy in the other lane would be a second population with
    its own fingerprint, and a verdict is only reproducible against the one it
    was computed with.
    """

    def __init__(self, population: SurfacePopulation) -> None:
        self._population = population

    @classmethod
    def from_connection(cls, conn) -> RegistrySurfaceFinder:
        rows = conn.execute(
            "SELECT canonical_id, display_name FROM model_version"
        ).fetchall()
        return cls(build_population([(r[0], r[1]) for r in rows]))

    def __call__(self, text: str) -> tuple[str, ...]:
        """Surfaces this text names, with near misses SUBTRACTED (#441).

        ⚠ THIS WAS `resolve`, WHICH MATCHES A MODEL INSIDE A LONGER NAME.
          #341 fixed exactly this shape on 2026-09-17 and the fix reached E4's
          gate and not this path, so one lane held two resolutions of one text:

              "I switched to GPT-5.2-Codex."  ->  gpt-5, gpt-5.2, gpt-5.2-codex
              "GPT-5.5 was slower."           ->  gpt-5, gpt-5.5
              "Opus 4.8 wrote the migration." ->  claude-opus-4, claude-opus-4.8

          `quote_subject_verdict`'s docstring argues for ONE resolution
          precisely so two consumers cannot disagree, and across the lane they
          did: E4 said a document named X, this said the same text named X and
          a prefix of X.

        ⚠ AND THE STORED DAMAGE IS ONE CLAIM OF 1,781, WHICH IS NOT THE REASON
          TO FIX IT. @anoojntglobal-sudo measured before filing: 290 quotes
          carry a prefix artefact, 1,780 verdicts are unchanged because the
          longer correct name matches too, and the feared false agreement — a
          "GPT-5.6 Luna" quote filed under `gpt-5` reading as "names the
          model" — occurs ZERO times.

          The reason is that it biases every "names exactly one model"
          measurement DOWNWARD, because a sentence naming only "GPT-5.5"
          counts as naming two. Recomputed with the longest-match rule on the
          same text, the blog probe's seating criterion moves a long way:

              lucumr.pocoo.org   0.40 -> 0.80      antirez.com      0.81 -> 0.93
              timdettmers.com    0.64 -> 0.82      sh-reya.com      0.82 -> 1.00

          The 2026-09-21 six-host figures read through the same finder, so
          their "resolves to exactly one" is low by this mechanism.

        `.hits` rather than the whole `Resolution`: callers of this finder ask
        "what does this text name", and the near misses are the answer to a
        different question that E4's gate is the one to act on.
        """
        return resolve_with_near_misses(text or "", self._population).hits
