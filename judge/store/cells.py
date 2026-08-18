"""Aggregate claims into cells, apply the gate, write what may be said.

This is where evidence stops being a pile of claims and becomes a sentence. It
is the last stage before anything is readable: everything upstream produces
rows, this produces the one thing a page renders.

THE ORDER IS THE DESIGN

    read claims  ->  count voices  ->  gate  ->  classify  ->  phrase  ->  write

Counting is of PEOPLE, not claims. The gate decides whether anything may be
said at all. Only then is a phrase assembled, from the counts, by template. No
model runs here and none may — rule 2 names counting, weighting, gating,
ranking and phrase assembly, and this module does four of those five.

A CELL IS WRITTEN EVEN WHEN THE GATE REFUSES

`insufficient` is a finding. A cell saying "two voices, one platform, not yet
corroborated" is what makes silence visible, and it is the distinction rule 4
turns on: "nobody has discussed this" and "engineers report problems" are
opposite states, and a missing row renders as neither.

So the gate decides the STATUS. It never decides whether to write.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

from judge.curate.gate import (
    CellCounts,
    CellStatus,
    GateResult,
    WeightedClaim,
    check_gate,
    classify,
    count,
)
from judge.curate.phrases import Consensus, describe
from judge.store.claims import PIPELINE_VERSION

log = logging.getLogger(__name__)

#: Claims with no author collapse to ONE voice per platform, not one each. An
#: unknown author is not a known distinct author, and counting each as its own
#: manufactures exactly the independence the author cap exists to prevent. Same
#: ruling as team-bylined blogs: an organisation is a stable identity, and one.
ANONYMOUS_VOICE = "anonymous"


@dataclass(frozen=True)
class CellKey:
    """The three dimensions that define a cell."""

    model_version_id: str
    capability_key: str
    condition_bucket: str

    def __str__(self) -> str:  # pragma: no cover - logging only
        return f"{self.model_version_id}/{self.capability_key}@{self.condition_bucket}"


@dataclass(frozen=True)
class CellOutcome:
    """Everything computed for one cell, before any of it is written."""

    key: CellKey
    counts: CellCounts
    gate: GateResult
    status: CellStatus
    consensus: Consensus

    @property
    def publishes(self) -> bool:
        return self.status is CellStatus.PUBLISHED


class CellStore:
    """Reads `claim` and `claim_weight`. Writes `cell`. Nothing else."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def keys_with_claims(self) -> list[CellKey]:
        """Every cell that has any evidence at all.

        Cells with no claims are deliberately not enumerated. A capability
        nobody has discussed is real and has to render, but that absence is a
        fact about the capability list rather than about this table — the
        coverage page derives it by subtracting these from the vocabulary,
        which keeps the two kinds of silence distinguishable.
        """
        rows = self._conn.execute(
            """
            SELECT DISTINCT model_version_id, capability_key, condition_bucket
            FROM claim
            ORDER BY model_version_id, capability_key, condition_bucket
            """
        ).fetchall()
        return [CellKey(*row) for row in rows]

    def weighted_claims_for(self, key: CellKey) -> list[WeightedClaim]:
        """One cell's claims, with their weights and their voices.

        An unweighted claim is EXCLUDED rather than defaulted. It is not a
        zero-weight claim, and giving it one would quietly move `n_eff` — rule
        6 on the single number the gate turns on. The inner join does that.
        """
        rows = self._conn.execute(
            """
            SELECT c.id, c.author_id, d.source, w.w_final, c.polarity,
                   c.severity, c.created_at, c.condition_bucket
            FROM claim c
            JOIN claim_weight w ON w.claim_id = c.id
            JOIN document d ON d.id = c.document_id
            WHERE c.model_version_id = %s
              AND c.capability_key = %s
              AND c.condition_bucket = %s
            """,
            (key.model_version_id, key.capability_key, key.condition_bucket),
        ).fetchall()

        claims: list[WeightedClaim] = []
        for row in rows:
            claim_id, author_id, platform, w_final, polarity, severity, created, bucket = row
            claims.append(
                WeightedClaim(
                    claim_id=claim_id,
                    voice_id=author_id or f"{ANONYMOUS_VOICE}:{platform}",
                    platform=platform,
                    weight=float(w_final),
                    polarity=polarity,
                    severity=severity,
                    quote_id=claim_id,
                    created_at=created.date() if hasattr(created, "date") else created,
                    condition_bucket=bucket,
                )
            )
        return claims

    def compute(self, key: CellKey, *, as_of: date | None = None) -> CellOutcome:
        """Count, gate, classify, phrase. No writing and no judgement."""
        claims = self.weighted_claims_for(key)
        counts = count(claims, as_of=as_of)
        gate = check_gate(counts)
        status = classify(counts) if gate.passed else CellStatus.INSUFFICIENT
        consensus = describe(counts, capability_key=key.capability_key, status=status)
        return CellOutcome(key=key, counts=counts, gate=gate, status=status, consensus=consensus)

    def write(self, outcome: CellOutcome, *, pipeline_version: str = PIPELINE_VERSION) -> None:
        """Upsert one cell, whether or not the gate passed."""
        counts, key = outcome.counts, outcome.key
        self._conn.execute(
            """
            INSERT INTO cell (
                model_version_id, capability_key, condition_bucket, n_eff,
                independent_voices, platform_count, max_author_share, positive,
                negative, status, provenance, consensus_phrase, conditional_note,
                quote_ids, freshest_at, median_age, pipeline_version
            ) VALUES (
                %(model_version_id)s, %(capability_key)s, %(condition_bucket)s,
                %(n_eff)s, %(independent_voices)s, %(platform_count)s,
                %(max_author_share)s, %(positive)s, %(negative)s, %(status)s,
                'harvested', %(consensus_phrase)s, %(conditional_note)s,
                %(quote_ids)s, %(freshest_at)s, %(median_age)s, %(pipeline_version)s
            )
            ON CONFLICT (model_version_id, capability_key, condition_bucket)
            DO UPDATE SET
                n_eff = EXCLUDED.n_eff,
                independent_voices = EXCLUDED.independent_voices,
                platform_count = EXCLUDED.platform_count,
                max_author_share = EXCLUDED.max_author_share,
                positive = EXCLUDED.positive,
                negative = EXCLUDED.negative,
                status = EXCLUDED.status,
                consensus_phrase = EXCLUDED.consensus_phrase,
                conditional_note = EXCLUDED.conditional_note,
                quote_ids = EXCLUDED.quote_ids,
                freshest_at = EXCLUDED.freshest_at,
                median_age = EXCLUDED.median_age,
                computed_at = now(),
                pipeline_version = EXCLUDED.pipeline_version
            """,
            {
                "model_version_id": key.model_version_id,
                "capability_key": key.capability_key,
                "condition_bucket": key.condition_bucket,
                "n_eff": counts.n_eff,
                "independent_voices": counts.independent_voices,
                "platform_count": counts.platform_count,
                "max_author_share": counts.max_author_share,
                "positive": counts.positive,
                "negative": counts.negative,
                "status": outcome.status.value,
                "consensus_phrase": outcome.consensus.phrase,
                "conditional_note": outcome.consensus.conditional_note,
                "quote_ids": list(counts.quote_ids),
                "freshest_at": counts.freshest_at,
                "median_age": counts.median_age_days,
                "pipeline_version": pipeline_version,
            },
        )

    def rebuild_all(self, *, as_of: date | None = None) -> list[CellOutcome]:
        """Recompute every cell that has evidence.

        Whole-table rather than incremental, deliberately. Recomputation is
        cheap at any claim count this project will reach, and an incremental
        path would be a second description of the aggregation that can disagree
        with the first — which is the defect this repo keeps finding in prose
        and would find again in code.
        """
        outcomes: list[CellOutcome] = []
        for key in self.keys_with_claims():
            outcome = self.compute(key, as_of=as_of)
            self.write(outcome)
            outcomes.append(outcome)
        log.info(
            "rebuilt %d cells, %d published",
            len(outcomes),
            sum(1 for outcome in outcomes if outcome.publishes),
        )
        return outcomes
