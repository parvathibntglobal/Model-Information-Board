"""Re-weight stored claims under a new pipeline version. No model is called.

WHY THIS EXISTS AND WHY IT IS NOT `rebuild-cells`

`rebuild-cells` recomputes `cell` from `claim_weight`. It re-aggregates; it
never re-weights. So a change to `contract/harvest.yaml` — the tier ladder, the
specificity weights, a half-life — moved nothing at all, because the only code
path that has ever called `weight.compute()` is `judge/pipeline.py`, and that
path runs the extractor. Until this module there was no way to price a stored
claim differently without paying to extract it again.

    extract      text  -> claims + weights        costs money, nondeterministic
    reweight     claims -> claims + weights       costs nothing, deterministic
    rebuild-cells weights -> cells                costs nothing, deterministic

THE INPUTS ARE READ BACK, NEVER RE-DERIVED

Every input `compute()` needs is already a column. `speaking`, `relevance`,
`specificity`, `has_repro_steps` and `has_numbers` are on `claim`; `source`,
`created_at` and the counted `has_numbers`/`has_conditions` are on `document`;
the release date is on `model_version`. So a re-weight is arithmetic over stored
values, and it is reproducible in a way the extraction that produced them is
not — the same document has yielded 8, 28 and 36 claims across three runs.

⚠ A NEW PIPELINE VERSION FORKS THE TABLE. IT DOES NOT UPDATE IT.

`claim_id_for` hashes `pipeline_version`, so the e5.2 rows are new rows and the
e5.1 rows stay exactly as they were. That is the whole reason a version bump is
the right instrument here and re-tiering in place was not: the before-state
survives, so the diff is a query rather than a snapshot somebody remembered to
take. Everything else follows from it:

    `CellStore` filters on `pipeline_version`, because a voice present at both
    versions would otherwise contribute its BEST weight across the two — an
    `n_eff` belonging to neither version, wrong by the most on exactly the
    claims the re-tier moved.

    `cell` is keyed on (model, capability, bucket) with no version, so the CELL
    side is genuinely overwritten by the next rebuild. This module therefore
    computes both sides ITSELF, from `claim` and `claim_weight`, rather than
    trusting a rebuild to have happened in the right order.

WHAT IT COUNTS BESIDE THE WEIGHTS

Three things, and all three are absences or risks rather than results:

    unconfirmed signals    a promotion withheld because an input was NULL, not
                           because it was false. Rule 6 — say so.
    provider-domain lifts  claims promoted whose document is hosted on a model
                           provider's own domain. E6 does NOT detect a vendor
                           announcement (its five triggers are affiliate links,
                           sponsored disclosures, discount codes, syndication
                           and predates-model), so a launch post the extractor
                           filed as `own-experience` promotes like anyone's
                           build report. A COUNT, not a gate — rule 8.
    refusals               claims `compute()` refused, by input. A claim that
                           cannot be weighted is not carried forward at the new
                           version, and saying which ones and why is the
                           difference between a fork and a silent truncation.

No language model participates in this file.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit

from judge.store.claims import PIPELINE_VERSION, claim_id_for

#: Hosts whose posts about their own models are vendor speech whatever the
#: `speaking` field says. Used to COUNT promotions for review, never to change
#: one - see the module docstring. Imported rather than re-listed so this and
#: `judge/vet/reject.py`'s affiliate-link rule cannot drift into disagreeing
#: about who a provider is.
from judge.vet.reject import _PROVIDER_DOMAINS
from judge.vet.weight import (
    LEGACY_SPECIFICITY_WEIGHTS,
    SPECIFICITY_WEIGHTS,
    TIER_WEIGHT,
    UNSUPPLIED,
    UnsuppliedWeightInput,
    WeightFactors,
    compute,
    evidence_tier_for,
    promotable_numbers,
)

log = logging.getLogger(__name__)

#: What `has_numbers` and `has_conditions` are worth to `f_specificity`.
#:
#:   frozen  the values e5.1 EFFECTIVELY used - both False. `_document_facts`
#:           passed a literal `None`, `compute()`'s refusal tested
#:           `is UNSUPPLIED` and missed it, and `specificity_factor` read it as
#:           falsy. So False is not a guess about those rows, it is what they
#:           were priced at. Passing it explicitly reproduces e5.1's arithmetic
#:           without relying on the hole, and lets the tier diff move one factor.
#:
#:   read    the columns. What the ruling asks for, and what `_document_facts`
#:           now does. A NULL column is a REFUSAL under the repaired check, not
#:           a False, so this mode drops claims and counts them.
#:
#: TWO MODES RATHER THAN TWO COMMITS, because both rulings landed the same day
#: and a single diff carrying both measures neither.
FROZEN = "frozen"
READ = "read"

#: Which generation of `f_specificity` a run prices with.
#:
#:   legacy   the four-signal form, in force from the start of the project until
#:            Option 1 landed on 2026-08-30. Needed to reproduce the BEFORE side
#:            of e5.1/e5.2/e5.3 - a diff against a formula that never applied is
#:            a diff about nothing.
#:   current  Option 1's two-signal form. What `judge extract` writes today.
#:
#: A run that changes BOTH this and `document_facts` measures neither, which is
#: why the run order gives each ruling its own version.
LEGACY = "legacy"
CURRENT = "current"


@dataclass
class ClaimDelta:
    """One claim, priced at both versions."""

    claim_id_before: str
    claim_id_after: str
    model_version_id: str
    capability_key: str
    condition_bucket: str
    platform: str
    speaking: str | None
    tier_before: str
    tier_after: str
    w_before: float
    w_after: float
    unconfirmed: tuple[str, ...]
    provider_host: str | None
    #: What `f_specificity` was at `from_version`. Carried so the READ-mode run
    #: can report how many claims the document columns actually moved, which is
    #: the number the whole `None`-slipping-past-the-refusal finding turns on.
    f_specificity_before: float | None
    #: The seven factors behind `w_after`. Carried on the delta rather than in a
    #: module-level cache so `plan()` stays a pure function of the connection -
    #: a cache keyed on claim id would survive between runs and hand `apply()`
    #: the factors from whichever plan ran last.
    factors: WeightFactors

    @property
    def heavier(self) -> bool:
        """Strictly heavier than before, outside float noise.

        THE TOLERANCE IS NOT COSMETIC. `claim_weight.w_final` is `real`, a
        four-byte float, so a weight read back is never bit-identical to the
        eight-byte one that produced it. A bare `>` reported a claim whose tier
        had not moved as promoted — including a vendor claim, which is the one
        row this whole change is being checked against.
        """
        return self.w_after - self.w_before > 1e-6 * max(self.w_before, 1e-6)

    @property
    def promoted(self) -> bool:
        """The TIER moved up. Not the same question as `heavier`, and the
        difference is what the provider-domain flag is about.

        A claim can get heavier without being promoted - in READ mode a vendor
        claim whose document carries numbers gains `f_specificity` while staying
        at F. Reading `heavier` as `promoted` put a CORRECTLY-filed announcement
        under a warning that says `speaking` had misfiled it, which is a false
        accusation about the one row this change is checked against. Both are
        reported; they are just not the same row set.
        """
        return TIER_WEIGHT.get(self.tier_after, 0.0) > TIER_WEIGHT.get(
            self.tier_before, 0.0
        )


@dataclass
class ReweightReport:
    """What the re-weight did, and what it declined to do."""

    from_version: str
    to_version: str
    #: LEGACY or CURRENT - which generation of `f_specificity` was priced.
    specificity: str = CURRENT
    #: FROZEN or READ - which of the two 2026-08-30 rulings this run measures.
    #: On the report rather than only in the caller, because a set of numbers
    #: whose cause is not attached to them is the thing this whole exercise is
    #: trying to stop producing.
    document_facts: str = READ
    deltas: list[ClaimDelta] = field(default_factory=list)
    #: input name -> claims `compute()` refused on it. Refusals are NOT written
    #: at the new version, so this is a truncation and has to be visible.
    refusals: Counter[str] = field(default_factory=Counter)
    #: signal name -> promotions withheld because the input was absent.
    unconfirmed: Counter[str] = field(default_factory=Counter)
    #: factor name -> claims where a factor OTHER than f_evidence moved. Should
    #: be empty. A non-zero count means this re-weight changed something besides
    #: the tier, so the before/after cannot be attributed to the tier ruling -
    #: which is the failure that would make the whole measurement worthless
    #: while every individual number still looked right.
    factor_drift: Counter[str] = field(default_factory=Counter)
    #: claims read at `from_version`, before any refusal.
    read: int = 0

    @property
    def written(self) -> int:
        return len(self.deltas)

    def tier_moves(self) -> Counter[str]:
        """"D->B" -> how many. The one table a reviewer asks for first."""
        return Counter(f"{d.tier_before}->{d.tier_after}" for d in self.deltas)

    def specificity_moves(self) -> list[ClaimDelta]:
        """Claims whose `f_specificity` changed once the columns reached it.

        Empty by construction in FROZEN mode - the drift check refuses to let it
        be anything else. In READ mode it is the answer to "how many stored
        claims change when both fields actually reach the path", counted rather
        than reasoned about from the NULL rates.
        """
        return [
            d
            for d in self.deltas
            if d.f_specificity_before is not None
            and abs(d.f_specificity_before - d.factors.f_specificity) > 1e-4
        ]

    def provider_domain_promotions(self) -> list[ClaimDelta]:
        """TIER-promoted claims hosted on a provider's own domain. For review.

        Keyed on `promoted` and not on `heavier`: the thing worth a human's time
        is an announcement the extractor filed as first-hand and the ladder then
        lifted. A vendor claim that merely got heavier is on the next list.
        """
        return [d for d in self.deltas if d.promoted and d.provider_host]

    def provider_domain_heavier_without_promotion(self) -> list[ClaimDelta]:
        """Vendor-domain claims that gained weight without moving tier.

        Separate because the cause is different and so is the remedy. These are
        not misfiled - they are correctly at F and got heavier through
        `f_specificity`, which reads the document's numbers. An announcement is
        full of numbers by construction, so this is the OTHER door into E2's
        worry and it opens in READ mode rather than in the tier ruling.
        """
        return [
            d for d in self.deltas
            if d.heavier and not d.promoted and d.provider_host
        ]


def _provider_host(url: str | None) -> str | None:
    """The provider domain this url is on, or None. Registrable-suffix match.

    `anthropic.com` must match `www.anthropic.com` and `news.anthropic.com` and
    must NOT match `notanthropic.com`, so this is a suffix test on a dot
    boundary rather than a substring test. The substring version is the exact
    error `docs/measurements/control-and-reshape.md` records — `free` matching
    inside `freeze` — and it is worth not repeating on a different string.
    """
    if not url:
        return None
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    if not host:
        return None
    for domain in _PROVIDER_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return domain
    return None


_READ_SQL = """
SELECT c.id, c.thread_context_id, c.source_comment_id, c.capability_key,
       lower(c.quote_flat_offset), upper(c.quote_flat_offset),
       c.model_version_id, c.condition_bucket, c.speaking, c.relevance,
       c.specificity, c.has_repro_steps, c.has_numbers, c.evidence_tier,
       w.w_final, w.f_platform, w.f_specificity, w.f_relevance, w.f_launch,
       w.f_fuzziness,
       d.source, d.created_at, d.url, d.has_numbers, d.has_conditions,
       mv.release_date, mv.canonical_id
FROM claim c
JOIN claim_weight w ON w.claim_id = c.id
JOIN document d ON d.id = c.document_id
LEFT JOIN model_version mv ON mv.id = c.model_version_id
WHERE c.pipeline_version = %s
ORDER BY c.id
"""




def plan(
    conn: Any,
    *,
    from_version: str,
    to_version: str = PIPELINE_VERSION,
    document_facts: str = READ,
    specificity: str = CURRENT,
    as_of: date | None = None,
) -> ReweightReport:
    """Price every claim at both versions. READS ONLY — nothing is written.

    Separated from `apply` so the delta can be reported, argued about and
    reviewed before a row exists. A re-weight is cheap to run and expensive to
    explain after the fact, which is the wrong way round for a change that
    moves every number on the board.

    `document_facts` picks which of the two 2026-08-30 rulings this run is
    measuring - see `FROZEN` and `READ`. Run them in that order, one version
    each, and each diff has exactly one cause.
    """
    if document_facts not in (FROZEN, READ):
        raise ValueError(f"document_facts must be {FROZEN!r} or {READ!r}")
    if specificity not in (LEGACY, CURRENT):
        raise ValueError(f"specificity must be {LEGACY!r} or {CURRENT!r}")
    specificity_weights = (
        LEGACY_SPECIFICITY_WEIGHTS if specificity == LEGACY else SPECIFICITY_WEIGHTS
    )
    if from_version == to_version:
        raise ValueError(
            f"from_version and to_version are both {to_version!r}. A re-weight "
            "into the same version would upsert over the rows it is measuring "
            "against and destroy the before-state — bump PIPELINE_VERSION first."
        )

    as_of = as_of or datetime.now().date()
    report = ReweightReport(
        from_version=from_version,
        to_version=to_version,
        document_facts=document_facts,
        specificity=specificity,
    )

    for row in conn.execute(_READ_SQL, (from_version,)).fetchall():
        (
            old_id, thread_context_id, source_comment_id, capability_key,
            span_lo, span_hi, model_version_id, condition_bucket, speaking,
            relevance, specificity, claim_repro, claim_numbers, tier_before,
            w_before, was_platform, was_specificity, was_relevance, was_launch,
            was_fuzziness, platform, created_at, url, doc_numbers, doc_conditions,
            release_date, canonical_id,
        ) = row
        report.read += 1

        # `speaking` is NULL on the four rows written before the column existed.
        # Not defaulted — `evidence_tier_for` will return UNSUPPLIED for it and
        # the refusal names the input, which is the whole point of the sentinel.
        verdict = evidence_tier_for(
            speaking if speaking is not None else "",
            has_repro_steps=claim_repro,
            has_numbers=promotable_numbers(claim_numbers, doc_numbers),
        )
        for signal in verdict.unconfirmed:
            report.unconfirmed[signal] += 1

        try:
            weights: WeightFactors = compute(
                evidence_tier=verdict.tier,
                platform=platform,
                capability_key=capability_key,
                relevance=relevance,
                specificity=specificity,
                claim_date=created_at.date() if hasattr(created_at, "date") else created_at,
                release_date=release_date,
                as_of=as_of,
                # ── THE SIX FACTORS THAT ARE NOT CHANGING ──────────────────
                #
                # These reproduce `judge/pipeline.py`'s inputs EXACTLY, so the
                # only difference between the two versions of a claim is
                # `f_evidence`. One ruling, one moving factor, an attributable
                # diff. `_factor_drift` below asserts it rather than trusting
                # this comment.
                version_named=specificity in ("snapshot", "version"),
                # ⚠ `False` IN FROZEN MODE, AND IT IS NOT A GUESS. It is what
                #   e5.1 priced these rows at: `_document_facts` passed a
                #   literal `None`, the refusal tested `is UNSUPPLIED` and let it
                #   through, and `specificity_factor` read it as falsy. Passing
                #   False explicitly reproduces that arithmetic exactly while
                #   the repaired check refuses `None` - the reproduction no
                #   longer depends on the bug being present.
                #
                #   In READ mode these are the columns, and a NULL refuses.
                has_conditions=(
                    False if document_facts == FROZEN
                    else (doc_conditions if doc_conditions is not None else UNSUPPLIED)
                ),
                has_numbers=(
                    False if document_facts == FROZEN
                    else (doc_numbers if doc_numbers is not None else UNSUPPLIED)
                ),
                has_repro_steps=claim_repro if claim_repro is not None else UNSUPPLIED,
                specificity_weights=specificity_weights,
            )
        except UnsuppliedWeightInput as gap:
            for name in gap.missing:
                report.refusals[name] += 1
            log.warning("claim %s not carried to %s: %s", old_id, to_version, gap.missing)
            continue

        # ONE RULING, ONE MOVING FACTOR. Asserted per claim rather than stated
        # in a comment, because "I meant to change only the tier" is exactly the
        # kind of belief that survives a review and not a re-run. f_recency is
        # excluded and only that one: it decays with the calendar, so it moves
        # between any two runs and its movement says nothing about the ruling.
        #
        # In READ mode `f_specificity` is the factor the ruling is ABOUT, so it
        # is expected to move and is excluded from drift there. Excluding it in
        # FROZEN mode would defeat the check entirely, which is why the
        # exclusion is keyed on the mode rather than left as a constant.
        checks = [
            ("f_platform", was_platform, weights.f_platform),
            ("f_specificity", was_specificity, weights.f_specificity),
            ("f_relevance", was_relevance, weights.f_relevance),
            ("f_launch", was_launch, weights.f_launch),
            ("f_fuzziness", was_fuzziness, weights.f_fuzziness),
        ]
        # `f_specificity` is EXPECTED to move in any run whose ruling is about
        # it, so it is excluded from drift there and counted as a result
        # instead. Excluded on the mode rather than always, because in the
        # tier-only run (frozen + legacy) an f_specificity move means the run is
        # not measuring what it says it is - which is the whole reason the
        # check exists.
        if document_facts == READ or specificity == CURRENT:
            checks = [c for c in checks if c[0] != "f_specificity"]
        for name, was, now in checks:
            if was is not None and abs(float(was) - now) > 1e-4:
                report.factor_drift[name] += 1
                log.warning(
                    "claim %s: %s moved %.4f -> %.4f, and this ruling should not "
                    "have moved it. The diff is no longer attributable to the "
                    "tier alone.", old_id, name, float(was), now,
                )

        report.deltas.append(
            ClaimDelta(
                claim_id_before=old_id,
                claim_id_after=claim_id_for(
                    thread_context_id=thread_context_id,
                    source_comment_id=source_comment_id,
                    capability_key=capability_key,
                    quote_flat_offset=(span_lo, span_hi),
                    pipeline_version=to_version,
                ),
                model_version_id=canonical_id or model_version_id,
                capability_key=capability_key,
                condition_bucket=condition_bucket,
                platform=platform,
                speaking=speaking,
                tier_before=tier_before,
                tier_after=str(verdict.tier),
                w_before=float(w_before),
                w_after=weights.w_final,
                unconfirmed=verdict.unconfirmed,
                provider_host=_provider_host(url),
                f_specificity_before=(
                    float(was_specificity) if was_specificity is not None else None
                ),
                factors=weights,
            )
        )

    return report


def apply(conn: Any, report: ReweightReport) -> int:
    """Write the planned rows. The caller owns the transaction.

    A COPY WITH TWO COLUMNS CHANGED, and the column list is read from the
    database rather than typed here. `claim` has 29 columns and this module
    knows the meaning of three of them; enumerating the rest would be a second
    description of the schema that goes stale the next time somebody adds a
    field — which is how `speaking` spent two days missing from `tables.sql`.
    """
    if not report.deltas:
        return 0

    columns = [
        r[0]
        for r in conn.execute(
            # `table_schema = current_schema()` IS LOAD-BEARING, not tidiness.
            # Without it this returns one row per schema that happens to hold a
            # `claim` table, and the column list came back as
            # `(id, id, id, id, document_id, ...)` - a DuplicateColumn error on
            # the INSERT. The search path is what decides which table is being
            # copied, so it has to decide which columns are being read too.
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'claim' AND table_schema = current_schema() "
            "ORDER BY ordinal_position"
        ).fetchall()
    ]
    for required in ("id", "pipeline_version", "evidence_tier"):
        if required not in columns:
            raise RuntimeError(f"`claim` has no {required} column; refusing to copy")

    projected = ", ".join(
        {
            "id": "m.new_id",
            "pipeline_version": "%(to_version)s",
            "evidence_tier": "m.tier",
        }.get(name, f"c.{name}")
        for name in columns
    )
    conn.execute(
        f"""
        INSERT INTO claim ({", ".join(columns)})
        SELECT {projected}
        FROM claim c
        JOIN (
            SELECT * FROM unnest(
                %(old_ids)s::text[], %(new_ids)s::text[], %(tiers)s::text[]
            ) AS t(old_id, new_id, tier)
        ) m ON m.old_id = c.id
        WHERE c.pipeline_version = %(from_version)s
        ON CONFLICT (id) DO UPDATE SET evidence_tier = EXCLUDED.evidence_tier
        """,
        {
            "old_ids": [d.claim_id_before for d in report.deltas],
            "new_ids": [d.claim_id_after for d in report.deltas],
            "tiers": [d.tier_after for d in report.deltas],
            "from_version": report.from_version,
            "to_version": report.to_version,
        },
    )

    rows = []
    for delta in report.deltas:
        rows.append({**delta.factors.as_row(), "claim_id": delta.claim_id_after,
                     "pipeline_version": report.to_version})
    conn.cursor().executemany(
        """
        INSERT INTO claim_weight (
            claim_id, w_final, f_evidence, f_platform, f_specificity,
            f_relevance, f_recency, f_launch, f_fuzziness, pipeline_version
        ) VALUES (
            %(claim_id)s, %(w_final)s, %(f_evidence)s, %(f_platform)s,
            %(f_specificity)s, %(f_relevance)s, %(f_recency)s, %(f_launch)s,
            %(f_fuzziness)s, %(pipeline_version)s
        )
        ON CONFLICT (claim_id) DO UPDATE SET
            w_final = EXCLUDED.w_final,
            f_evidence = EXCLUDED.f_evidence,
            f_platform = EXCLUDED.f_platform,
            f_specificity = EXCLUDED.f_specificity,
            f_relevance = EXCLUDED.f_relevance,
            f_recency = EXCLUDED.f_recency,
            f_launch = EXCLUDED.f_launch,
            f_fuzziness = EXCLUDED.f_fuzziness,
            pipeline_version = EXCLUDED.pipeline_version
        """,
        rows,
    )
    return len(report.deltas)


def cell_deltas(
    conn: Any, report: ReweightReport, *, as_of: date | None = None
) -> list[tuple[Any, Any]]:
    """(before, after) for every cell, both computed from `claim` directly.

    NOT from the `cell` table. That table is keyed without `pipeline_version`,
    so a rebuild overwrites the before-state — the same reason
    `scripts/report_rollup_delta.py` needs a snapshot file. Reading `claim`
    twice needs no snapshot and cannot be taken in the wrong order.
    """
    from judge.store.cells import CellStore

    before_store = CellStore(conn, pipeline_version=report.from_version)
    after_store = CellStore(conn, pipeline_version=report.to_version)

    before = {k: before_store.compute(k, as_of=as_of) for k in before_store.keys_with_claims()}
    after = {k: after_store.compute(k, as_of=as_of) for k in after_store.keys_with_claims()}

    pairs = []
    # Sorted on the FIELDS, not the key. `CellKey` is a frozen dataclass with no
    # ordering, so `sorted()` over the keys raises - and it raises only once
    # there is more than one cell, which is never in a unit test and always in a
    # real run.
    for key in sorted(
        set(before) | set(after),
        key=lambda k: (k.model_version_id, k.capability_key, k.condition_bucket),
    ):
        pairs.append((before.get(key), after.get(key)))
    return pairs


@dataclass(frozen=True)
class CellLoss:
    """A cell that lost voices, lost platforms, or stopped existing.

    ⚠ THIS IS A RESULT, NOT A SIDE EFFECT, and that is why it has a type rather
      than a suffix on a print line.

    Voices and platforms only ever go DOWN because a claim was refused, and a
    refusal is a claim we dropped. A cell that falls from two platforms to one
    has stopped being publishable — `PLATFORM_MINIMUM = 2` — and nothing in the
    `n_eff` column says so, because `n_eff` can rise on the same run that costs
    the cell its second platform.

    THE DIRECTION NOBODY CHECKS. Every report this project writes is built to
    notice the board getting louder; a re-weight that quietly makes it quieter
    produces an absence WE CAUSED, rendering identically to one we found. That
    is rule 4 one stage before the page and rule 8's whole argument about what a
    wrong gate costs.
    """

    model_version_id: str
    capability_key: str
    condition_bucket: str
    voices_before: int
    voices_after: int
    platforms_before: int
    platforms_after: int

    @property
    def gone(self) -> bool:
        return self.voices_after == 0

    @property
    def lost_publishability(self) -> bool:
        """Had two platforms and now has fewer. The gate condition it breaks."""
        return self.platforms_before >= 2 > self.platforms_after


def quieter_cells(pairs: Sequence[tuple[Any, Any]]) -> list[CellLoss]:
    """Every cell that lost voices or platforms, worst first.

    Computed from the (before, after) pairs rather than from the claim deltas,
    because the loss is a property of the AGGREGATE: a refused claim costs a
    cell a platform only if it was that cell's only claim on it, which no
    per-claim count can see.
    """
    losses: list[CellLoss] = []
    for before, after in pairs:
        if before is None:
            continue
        vb = before.counts.independent_voices
        pb = before.counts.platform_count
        va = after.counts.independent_voices if after is not None else 0
        pa = after.counts.platform_count if after is not None else 0
        if va < vb or pa < pb:
            losses.append(
                CellLoss(
                    model_version_id=before.key.model_version_id,
                    capability_key=before.key.capability_key,
                    condition_bucket=before.key.condition_bucket,
                    voices_before=vb,
                    voices_after=va,
                    platforms_before=pb,
                    platforms_after=pa,
                )
            )
    return sorted(losses, key=lambda c: (c.voices_after - c.voices_before,
                                         c.platforms_after - c.platforms_before))


def summarise_losses(
    losses: Sequence[CellLoss], names: dict[str, str] | None = None
) -> str:
    """The quieter-board report. Printed even when empty, and that is the point.

    "0 cells lost voices" is a result somebody can rely on. A section that
    appears only when something is wrong teaches the reader that its absence
    means nothing was checked.
    """
    names = names or {}
    if not losses:
        return "  THE BOARD GOT NO QUIETER. 0 cells lost voices or platforms."

    gone = [c for c in losses if c.gone]
    unpublishable = [c for c in losses if c.lost_publishability]
    lines = [
        "  !! THE BOARD GOT QUIETER. This is a result, not a side effect - every",
        "     voice below was DROPPED by a refusal, and an absence we caused",
        "     renders exactly like one we found (rule 4).",
        f"     {len(losses)} cells lost evidence, {len(gone)} lost all of it, "
        f"{len(unpublishable)} fell below PLATFORM_MINIMUM",
    ]
    for c in losses:
        model = names.get(c.model_version_id, c.model_version_id)
        marks = []
        if c.gone:
            marks.append("GONE")
        if c.lost_publishability:
            marks.append("NO LONGER PUBLISHABLE - one platform")
        lines.append(
            f"     {model:32s} {c.capability_key:26s} "
            f"voices {c.voices_before}->{c.voices_after}  "
            f"platforms {c.platforms_before}->{c.platforms_after}"
            + (f"   {' | '.join(marks)}" if marks else "")
        )
    return "\n".join(lines)


def summarise(report: ReweightReport) -> str:
    """The report a human reads. Counts only — nothing here is a score."""
    lines: list[str] = []
    lines.append(
        f"{report.from_version} -> {report.to_version}   "
        f"document facts: {report.document_facts}   "
        f"f_specificity: {report.specificity}"
    )
    lines.append(f"  read {report.read} claims, wrote {report.written}")

    if report.factor_drift:
        lines.append(
            "  !! A FACTOR OTHER THAN f_evidence MOVED. This diff is NOT "
            "attributable to the tier ruling:"
        )
        for name, n in report.factor_drift.most_common():
            lines.append(f"    {n:5d}  {name}")
    else:
        lines.append(
            "  only f_evidence moved"
            if report.document_facts == FROZEN and report.specificity == LEGACY
            else "  only f_evidence and f_specificity moved (f_specificity is "
            "what this run is FOR)"
        )
        lines.append("    f_recency is excluded either way - it decays with the calendar")

    if report.refusals:
        lines.append("  REFUSED (not carried to the new version):")
        for name, n in report.refusals.most_common():
            lines.append(f"    {n:5d}  {name}")

    if report.unconfirmed:
        lines.append("  promotions WITHHELD because the input was absent, not false:")
        for name, n in report.unconfirmed.most_common():
            lines.append(f"    {n:5d}  {name}")

    moved = report.specificity_moves()
    if report.document_facts == READ or report.specificity == CURRENT:
        # NAMED BY CAUSE, not by symptom. The same count means two different
        # things in the two runs that produce it, and a line that says only
        # "f_specificity moved" leaves the reader to guess which ruling they are
        # looking at from the flags they scrolled past.
        because = (
            "the document columns reaching the path"
            if report.document_facts == READ and report.specificity == LEGACY
            else "has_numbers and has_repro_steps leaving f_specificity"
            if report.specificity == CURRENT
            else "the formula and the columns both changing - THIS RUN MEASURES "
            "NEITHER, split it"
        )
        lines.append(
            f"  f_specificity moved on {len(moved)} of {report.written} written "
            f"claims ({because})"
        )
        by_pair: Counter = Counter()
        for d in moved:
            by_pair[f"{d.f_specificity_before:.2f} -> {d.factors.f_specificity:.2f}"] += 1
        for pair, n in by_pair.most_common():
            lines.append(f"    {n:5d}  {pair}")

    lines.append("  tier moves:")
    for move, n in sorted(report.tier_moves().items(), key=lambda kv: -kv[1]):
        lines.append(f"    {n:5d}  {move}")

    by_model: dict[str, list[ClaimDelta]] = defaultdict(list)
    for delta in report.provider_domain_promotions():
        by_model[delta.model_version_id].append(delta)
    if by_model:
        lines.append(
            "  !! PROMOTED ON A PROVIDER'S OWN DOMAIN. E6 does not detect a vendor"
        )
        lines.append(
            "    announcement, so `speaking` is the only thing that filed these as"
        )
        lines.append(
            "    first-hand. Counted for review, not blocked (rule 8):"
        )
        for model, deltas in sorted(by_model.items(), key=lambda kv: -len(kv[1])):
            hosts = ", ".join(sorted({d.provider_host or "?" for d in deltas}))
            lines.append(f"    {len(deltas):5d}  {model:34s} {hosts}")
    else:
        lines.append(
            "  no TIER promotion on a provider's own domain (the misfiling case)"
        )

    heavier = report.provider_domain_heavier_without_promotion()
    if heavier:
        by_model_h: dict[str, list[ClaimDelta]] = defaultdict(list)
        for delta in heavier:
            by_model_h[delta.model_version_id].append(delta)
        lines.append(
            "  !! HEAVIER ON A PROVIDER'S OWN DOMAIN WITHOUT A TIER MOVE. Correctly"
        )
        lines.append(
            "    filed as vendor and still gaining weight - f_specificity reads the"
        )
        lines.append(
            "    document's numbers, and an announcement carries numbers by"
        )
        lines.append("    construction. The other door into the same worry:")
        for model, deltas in sorted(by_model_h.items(), key=lambda kv: -len(kv[1])):
            gained = sum(d.w_after - d.w_before for d in deltas)
            lines.append(
                f"    {len(deltas):5d}  {model:34s} +{gained:.4f} total w_final"
            )
    return "\n".join(lines)
