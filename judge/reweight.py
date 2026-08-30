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
    UNSUPPLIED,
    UnsuppliedWeightInput,
    WeightFactors,
    compute,
    evidence_tier_for,
    promotable_numbers,
)

log = logging.getLogger(__name__)

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
    #: The seven factors behind `w_after`. Carried on the delta rather than in a
    #: module-level cache so `plan()` stays a pure function of the connection -
    #: a cache keyed on claim id would survive between runs and hand `apply()`
    #: the factors from whichever plan ran last.
    factors: WeightFactors

    @property
    def promoted(self) -> bool:
        """Strictly heavier than before, outside float noise.

        THE TOLERANCE IS NOT COSMETIC. `claim_weight.w_final` is `real`, a
        four-byte float, so a weight read back is never bit-identical to the
        eight-byte one that produced it. A bare `>` therefore reported a claim
        whose tier did not move as PROMOTED — including a vendor claim, which is
        the one row this whole change is being checked against.
        """
        return self.w_after - self.w_before > 1e-6 * max(self.w_before, 1e-6)


@dataclass
class ReweightReport:
    """What the re-weight did, and what it declined to do."""

    from_version: str
    to_version: str
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

    def provider_domain_promotions(self) -> list[ClaimDelta]:
        """Promoted claims hosted on a provider's own domain. For review."""
        return [d for d in self.deltas if d.promoted and d.provider_host]


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
    as_of: date | None = None,
) -> ReweightReport:
    """Price every claim at both versions. READS ONLY — nothing is written.

    Separated from `apply` so the delta can be reported, argued about and
    reviewed before a row exists. A re-weight is cheap to run and expensive to
    explain after the fact, which is the wrong way round for a change that
    moves every number on the board.
    """
    if from_version == to_version:
        raise ValueError(
            f"from_version and to_version are both {to_version!r}. A re-weight "
            "into the same version would upsert over the rows it is measuring "
            "against and destroy the before-state — bump PIPELINE_VERSION first."
        )

    as_of = as_of or datetime.now().date()
    report = ReweightReport(from_version=from_version, to_version=to_version)

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
                # ⚠ `None`, AND DELIBERATELY NOT THE COLUMN, THOUGH THE COLUMN
                #   IS RIGHT THERE IN `_READ_SQL`.
                #
                #   `judge/cli.py:_document_facts` passes a literal `None` for
                #   both of these - it does not read them - so EVERY claim in
                #   the table was weighted as though both were False, whatever
                #   `document.has_numbers` actually says. `compute()`'s refusal
                #   tests `is UNSUPPLIED`, so `None` slips past it and
                #   `specificity_factor` reads it as falsy. That is the
                #   2026-08-21 ruling's own hole, still open on the only path
                #   that has ever produced a claim.
                #
                #   Reading the columns here would fix it AND move
                #   `f_specificity` on most of the corpus in the same commit as
                #   the tier ruling, leaving neither measurable. So this
                #   reproduces the defect on purpose, the drift check proves it
                #   reproduced it, and the fix is filed separately. A silent
                #   improvement inside a measurement is still a confounder.
                has_conditions=None,
                has_numbers=None,
                has_repro_steps=claim_repro if claim_repro is not None else UNSUPPLIED,
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
        for name, was, now in (
            ("f_platform", was_platform, weights.f_platform),
            ("f_specificity", was_specificity, weights.f_specificity),
            ("f_relevance", was_relevance, weights.f_relevance),
            ("f_launch", was_launch, weights.f_launch),
            ("f_fuzziness", was_fuzziness, weights.f_fuzziness),
        ):
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


def summarise(report: ReweightReport) -> str:
    """The report a human reads. Counts only — nothing here is a score."""
    lines: list[str] = []
    lines.append(f"{report.from_version} -> {report.to_version}")
    lines.append(f"  read {report.read} claims, wrote {report.written}")

    if report.factor_drift:
        lines.append(
            "  !! A FACTOR OTHER THAN f_evidence MOVED. This diff is NOT "
            "attributable to the tier ruling:"
        )
        for name, n in report.factor_drift.most_common():
            lines.append(f"    {n:5d}  {name}")
    else:
        lines.append("  only f_evidence moved (f_recency excluded - it decays)")

    if report.refusals:
        lines.append("  REFUSED (not carried to the new version):")
        for name, n in report.refusals.most_common():
            lines.append(f"    {n:5d}  {name}")

    if report.unconfirmed:
        lines.append("  promotions WITHHELD because the input was absent, not false:")
        for name, n in report.unconfirmed.most_common():
            lines.append(f"    {n:5d}  {name}")

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
            "  no promotion on a provider's own domain (the vendor-misfiling case)"
        )
    return "\n".join(lines)
