"""Alias rows: how a human's words become a model_version.

Two jobs, deliberately separated (§5, "broad on retrieval, strict on
attribution"):

  RETRIEVAL   search must find `claude-opus-5`, `claude opus 5` and
              `claudeopus5`. Neither the GitHub nor the Reddit search API has
              a fuzzy operator, so every spelling has to be issued as its own
              query, and breadth is not optional.

              **Breadth comes from the hand-written variant list in
              `contract/seed_models.yaml`, not from mechanical expansion.**
              Expanding each declared surface again cost 1752 queries per
              platform against a 600-query budget, and added forms nobody
              types. But moving the guarantee from code to a human leaves
              nothing checking it, so `check_spelling_coverage` checks it:
              every model must declare a spaced, a hyphenated and a
              concatenated form, and the seed load fails where someone can
              fix it. Human-supplied is fine; human-supplied and unverified
              is not.

  ATTRIBUTION strict, time-aware matching against the canonical table. A
              claim filed against the wrong snapshot is worse than no claim.
              Every alias row is attribution-eligible regardless of whether
              it is worth a search query.

Specificity is the field that keeps attribution honest. A bare "sonnet"
resolves at `family` and never counts as independent corroboration, because
it does not say which tier the engineer was using.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date

from collect.ids import model_alias_id, model_version_id
from collect.registry.models import SeedModel
from collect.registry.policy import DEFAULT_POLICY, AliasSearchPolicy

#: Splits a surface into meaningful tokens. Dots survive, because `4.1` is
#: one version token and splitting it into `4` and `1` invents two.
_TOKEN_SPLIT = re.compile(r"[^0-9a-z.]+")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")
_HAS_DIGIT = re.compile(r"\d")

SPECIFICITIES = ("snapshot", "version", "family")


def normalize(surface: str) -> str:
    """Lowercase, punctuation stripped — the matching key.

    `GPT-4.1 mini`, `gpt 4.1 mini` and `gpt4.1mini` all normalise to
    `gpt41mini`, so they are one alias rather than three.
    """
    return _NON_ALNUM.sub("", surface.casefold())


def tokenize(surface: str) -> list[str]:
    """Version-preserving tokens: `gpt-4.1 mini` → ['gpt', '4.1', 'mini']."""
    return [tok for tok in _TOKEN_SPLIT.split(surface.casefold()) if tok]


def query_variants(surface: str) -> list[str]:
    """Deterministic spelling variants of one surface, for search queries.

    Mechanical only — spacing, hyphenation, concatenation. No invented
    misspellings: everything a human might plausibly type that is *not*
    derivable this way belongs in `contract/seed_models.yaml`, where it is
    versioned and reviewable (rule 5).
    """
    tokens = tokenize(surface)
    if not tokens:
        return []
    forms = [
        surface.strip(),
        " ".join(tokens),
        "-".join(tokens),
        "".join(tokens),
        normalize(surface),
    ]
    return _dedupe(forms)


def _dedupe(items: list[str]) -> list[str]:
    """Order-preserving deduplication."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def local_part(canonical_id: str) -> str:
    """`anthropic/claude-opus-5` → `claude-opus-5`."""
    return canonical_id.split("/")[-1]


def classify_specificity(surface: str, model: SeedModel) -> str:
    """How precisely this surface names a model.

        snapshot  it is the canonical id, or the model id inside it
        version   it carries a version token — `sonnet 5`, `flash 2.5`
        family    it carries none — a bare `sonnet` names a line, not a tier

    The family case is the one that matters. `sonnet` is deliberately in the
    seed file: it must resolve at family specificity, never snapshot, or an
    engineer's comment lands on a tier they never used.
    """
    key = normalize(surface)
    if key in {normalize(model.canonical_id), normalize(local_part(model.canonical_id))}:
        return "snapshot"
    if _HAS_DIGIT.search(key):
        return "version"
    return "family"


@dataclass(frozen=True)
class AliasRow:
    """One `model_alias` row. Append-only once written (FR-4).

    Two eligibilities, deliberately separate:

    ATTRIBUTION  every row, always. Resolution matches a mention's normalised
                 form against `normalized`, so a row costs nothing to keep and
                 dropping one loses claims.

    SEARCH       `search_eligible`, and only those rows carry query strings in
                 `variants`. Harvest is the expensive side, and a string no
                 human types is a wasted request against a rate limit.

    The distinction needs no schema change: an ineligible row persists with an
    empty `variants` array, and the harvester reads rows that have one.
    """

    id: str
    surface: str
    normalized: str
    variants: list[str]
    provider_hint: str | None
    model_version_id: str
    family: str | None
    specificity: str
    valid_from: date | None
    valid_until: date | None = None
    confidence: float = 1.0
    search_eligible: bool = True
    canonical_id: str = field(default="", compare=False)

    def content_key(self) -> str:
        """What this row asserts, excluding the window it asserts it over.

        Two rows with the same content key are the same claim about the
        world and share an id, so reloading is a no-op. A different key is a
        different claim, which closes the old row and appends a new one.

        `valid_from` is excluded on purpose: a corrected release date does
        not change what the alias means, and folding it in here is what let
        two live rows share a `normalized`.
        """
        return "|".join(
            [
                self.surface,
                ",".join(self.variants),
                self.provider_hint or "",
                self.family or "",
                self.specificity,
                f"{self.confidence:.4f}",
            ]
        )


def alias_rows(model: SeedModel, policy: AliasSearchPolicy | None = None) -> list[AliasRow]:
    """Every alias for one seeded model, deduplicated by normalised form.

    The canonical id and its local part are always added, so an exact mention
    resolves at snapshot specificity even when the hand-written surface list
    omits it. Neither earns a search query: `anthropic/claude-opus-5` and
    `claude-haiku-4-5-20251001` are strings that appear in configs and API
    logs, not in the prose this lane harvests.
    """
    policy = policy or DEFAULT_POLICY.alias_search
    mv_id = model_version_id(model.canonical_id)
    valid_from = model.release_date

    #: An alias stops being CURRENT when its model retires, which is exactly
    #: what FR-4's time-awareness is for. `mistral large` meant
    #: mistral-large-2411 until it retired on 2025-03-30 and means
    #: mistral-large-3 from 2025-12-01; without this the two windows overlap
    #: and the collision check correctly refuses the whole seed file.
    #:
    #: A March 2025 post saying "mistral large" must still resolve to 2411.
    #: Closing the window preserves that and stops it resolving to a model
    #: that did not exist yet.
    valid_until = model.retirement_date

    declared = [model.aliases.surface, *model.aliases.variants]
    #: normalised key -> the hand-written spellings that reduce to it. These
    #: are the query strings: what somebody wrote in `contract/` is what gets
    #: searched, which makes the harvest budget auditable from the YAML alone.
    declared_by_key: dict[str, list[str]] = {}
    for surface in declared:
        declared_by_key.setdefault(normalize(surface), []).append(surface.strip())

    rows: list[AliasRow] = []
    seen: set[str] = set()
    for surface in [model.canonical_id, local_part(model.canonical_id), *declared]:
        surface = surface.strip()
        key = normalize(surface)
        if not key or key in seen:
            continue
        seen.add(key)

        spellings = _dedupe(declared_by_key.get(key, []))
        eligible = bool(spellings) or not policy.declared_surfaces_only
        if not eligible:
            search_strings: list[str] = []
        elif policy.expand_mechanically:
            search_strings = _dedupe(
                [form for s in (spellings or [surface]) for form in query_variants(s)]
            )
        else:
            search_strings = spellings or [surface]

        # The id is a function of the row's own content, so build it first
        # with a placeholder and stamp the id from what came out.
        row = AliasRow(
                id="",
                surface=surface,
                normalized=key,
                variants=search_strings,
                provider_hint=model.provider,
                model_version_id=mv_id,
                family=model.family,
                specificity=classify_specificity(surface, model),
                valid_from=valid_from,
                valid_until=valid_until,
                confidence=1.0,
                search_eligible=eligible,
                canonical_id=model.canonical_id,
        )
        rows.append(replace(row, id=model_alias_id(key, mv_id, row.content_key())))
    return rows


def all_alias_rows(
    models: list[SeedModel], policy: AliasSearchPolicy | None = None
) -> list[AliasRow]:
    return [row for model in models for row in alias_rows(model, policy)]


def search_queries(rows: list[AliasRow]) -> list[str]:
    """Every distinct string harvest will issue, across all models.

    The harvest budget is this list times the capability count, so it is the
    number to look at before widening the alias list.
    """
    return _dedupe([form for row in rows if row.search_eligible for form in row.variants])


class AliasCollisionError(ValueError):
    """One surface points at more than one model at the same moment.

    §5 rule 4: a mention ambiguous across models is dropped, not guessed at.
    In a hand-written contract file an ambiguity is a mistake, so it fails at
    load time where someone can fix it, rather than at resolution time where
    it would quietly drop evidence.
    """

    def __init__(self, collisions: dict[str, list[str]]) -> None:
        self.collisions = collisions
        listed = "; ".join(f"{key!r} -> {sorted(ids)}" for key, ids in sorted(collisions.items()))
        super().__init__(
            f"alias surfaces resolve to more than one model over overlapping "
            f"validity windows: {listed}"
        )


#: Substituted for a NULL bound. Both widen the window, which is the safe
#: direction: an unknown bound should make us raise rather than quietly
#: permit an ambiguity.
_OPEN_START = date.min
_OPEN_END = date.max


def intervals_overlap(
    a_from: date | None,
    a_until: date | None,
    b_from: date | None,
    b_until: date | None,
) -> bool:
    """Do two half-open ``[valid_from, valid_until)`` windows overlap?

    NULL `valid_from` means open at the start; NULL `valid_until` means still
    current.

    Half-open is the load-bearing part. When one alias is closed out and its
    replacement opens on the same day, ``a.valid_until == b.valid_from`` and
    the two do not overlap. That handover is the whole reason FR-4 makes the
    table append-only, so it must not read as a collision.
    """
    a_start, a_end = a_from or _OPEN_START, a_until or _OPEN_END
    b_start, b_end = b_from or _OPEN_START, b_until or _OPEN_END
    return a_start < b_end and b_start < a_end


def find_collisions(rows: list[AliasRow]) -> dict[str, list[str]]:
    """Normalised surfaces claimed by two models over overlapping windows.

    Grouping on `normalized` alone is wrong, and it breaks on the exact case
    FR-4 exists for. A `-latest` alias legitimately points at one snapshot in
    March and a different one in June; those are disjoint windows and one
    unambiguous answer at any instant. Flagging that would make the seed load
    fail the moment somebody adds the alias the requirement was written for.

    Same-model rows are not compared. A model holding one surface across two
    windows is the append-only handover, not an ambiguity. Whether a model
    has more than one *live* row for a surface is a property of the table,
    not of this list, and is enforced where the rows are written.
    """
    by_key: dict[str, list[AliasRow]] = {}
    for row in rows:
        by_key.setdefault(row.normalized, []).append(row)

    collisions: dict[str, list[str]] = {}
    for key, group in by_key.items():
        clashing: set[str] = set()
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                if left.canonical_id == right.canonical_id:
                    continue
                if intervals_overlap(
                    left.valid_from, left.valid_until, right.valid_from, right.valid_until
                ):
                    clashing.update((left.canonical_id, right.canonical_id))
        if clashing:
            collisions[key] = sorted(clashing)
    return collisions


#: The three renderings a search API cannot bridge on its own. `gpt-4.1-mini`
#: and `gpt 4.1 mini` are different literal queries and match different posts.
SPELLING_STYLES = ("spaced", "hyphenated", "concatenated")

# THE FLOOR STAYS AT THREE, AND IT COUNTS RENDERINGS — #33, ruled.
#
# The surface extract measured what the corpus attests: a median of 2 distinct
# surfaces per discussed model, 17 of 72 reaching three, 18 appearing under
# exactly one (docs/measurements/alias-surfaces.md §2). Read as usage, a floor of
# three looks unmet by 55 of 72 models — which invited replacing it with a floor
# of three ATTESTED surfaces. That is refused, for two reasons:
#
#   * the remedy would be fabrication. 55 models would each be fixed by somebody
#     inventing a spelling to satisfy a gate, and a check that produces invented
#     data is worse than no check.
#   * spaced, hyphenated and concatenated are always derivable FROM THE ID. So
#     the floor as written is always satisfiable without judgement, which is the
#     property that makes it fair to fail a load over.
#
#     "Always" has one exception, counted rather than waved at: a SINGLE-TOKEN
#     local part has no separator to vary, so it has no spaced or hyphenated
#     rendering and satisfying the floor would mean choosing where to break the
#     word. That is 1 of the 155 ids in the registry slice — `openrouter/auto`,
#     which names a router and not a model. Pinned in
#     tests/test_registry_spelling.py so the next single-token id arrives as a
#     failing test rather than as a demand for judgement.
#
# So this gate reads STRING SHAPE and never mention counts: `spelling_styles`
# takes surfaces, `spelling_gaps` takes models, and neither has a route to the
# corpus. An unattested rendering costs a query and misses nothing — it is waste
# against the budget, never an error, which is the retrieval argument at the top
# of this module rather than a claim about how people write.
#
# The family surface is NOT part of the floor and must not become part of it.
# `collect/registry/propose.py` keeps it as a permanent INCOMPLETE slot for a
# reviewer to fill: required-but-INCOMPLETE-able. A gate would demand it, and a
# bare `opus` is attested constantly and attributable to no single model, so the
# only way to satisfy such a gate is to assert an attribution the data refuses.


@dataclass(frozen=True, order=True)
class SpellingGap:
    """A model whose declared surfaces omit a rendering people write."""

    canonical_id: str
    missing: tuple[str, ...]

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.canonical_id} (no {', '.join(self.missing)} form)"


class SpellingCoverageError(ValueError):
    """A model cannot be found by one of the three ways people write it.

    Raised at load, not at harvest. A missing spelling produces no error at
    query time: it produces silence, which is indistinguishable from nobody
    having discussed the model.
    """

    def __init__(self, gaps: list[SpellingGap]) -> None:
        self.gaps = gaps
        listed = "; ".join(str(gap) for gap in gaps)
        super().__init__(
            f"{len(gaps)} model(s) missing a declared spelling: {listed}. "
            "Search APIs have no fuzzy operator, so every rendering must be "
            "declared in contract/seed_models.yaml to be findable."
        )


def declared_surfaces(model: SeedModel) -> list[str]:
    """The hand-written spellings for one model, deduplicated."""
    return _dedupe([model.aliases.surface.strip(), *(v.strip() for v in model.aliases.variants)])


def spelling_styles(surfaces: list[str]) -> set[str]:
    """Which of the three renderings these surfaces cover.

    A concatenated form only counts when some separated surface reduces to
    the same normalised key. That is what distinguishes `opus5`, which is
    `opus 5` run together, from a bare `opus`, which is a family name and
    tells us nothing about whether `claudeopus5` would be found.
    """
    present: set[str] = set()
    separated: set[str] = set()
    for surface in surfaces:
        if " " in surface:
            present.add("spaced")
            separated.add(normalize(surface))
        if "-" in surface:
            present.add("hyphenated")
            separated.add(normalize(surface))
    for surface in surfaces:
        if " " not in surface and "-" not in surface and normalize(surface) in separated:
            present.add("concatenated")
    return present


def spelling_gaps(models: list[SeedModel]) -> list[SpellingGap]:
    """Every model missing one of the three renderings."""
    gaps = []
    for model in models:
        present = spelling_styles(declared_surfaces(model))
        missing = tuple(style for style in SPELLING_STYLES if style not in present)
        if missing:
            gaps.append(SpellingGap(model.canonical_id, missing))
    return sorted(gaps)


def check_spelling_coverage(models: list[SeedModel]) -> None:
    """Fail the load where a model cannot be found by one of the three renderings.

    Three, counted as renderings and never as attestations — see the ruling
    beside `SPELLING_STYLES`. The argument for the number is retrieval, not
    usage: the corpus attests a median of 2 surfaces per model, and that is a
    reason to expect an unattested rendering to return nothing, not a reason to
    make the model unfindable by it.
    """
    gaps = spelling_gaps(models)
    if gaps:
        raise SpellingCoverageError(gaps)


def check_no_collisions(rows: list[AliasRow]) -> None:
    collisions = find_collisions(rows)
    if collisions:
        raise AliasCollisionError(collisions)
