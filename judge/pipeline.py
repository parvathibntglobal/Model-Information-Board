"""One document to one sentence. The seam nobody had run.

    thread_context ─▶ E5 extract ─▶ verify ─▶ E6 weight ─▶ claim
                                                             │
                                        cell ◀─ E7 gate ◀────┘

Every stage here already existed and was tested alone. Nothing called them in
order, which meant five tested modules and four unrun joins — and an unrun join
is where this project has found most of its defects, because each side is
correct and the assumption between them is not written down anywhere.

WHAT THIS MODULE IS ALLOWED TO DECIDE: nothing.

It moves values between stages and derives what the schema needs from what the
stages produce. Every judgement is made elsewhere — the model proposes a claim,
`verify` decides whether the quote exists, `weight` decides what it is worth,
`gate` decides whether anything may be said. This is plumbing, and it is
written to be boring.

WHERE THE VALUES ACTUALLY COME FROM, since four of them are not obvious:

    version_named    document.names_version, computed at ingest by collect/
    has_conditions   document.has_conditions, same
    has_numbers      document.has_numbers — the COUNTED one, not the extractor's
    condition_bucket judge/config.bucket_for(), from the claim's conditions

`has_numbers` is the interesting one. `ExtractedClaim` carries the extractor's
opinion of it, and rule 2 forbids a model participating in weighting — so the
document-level count is authoritative and the extractor's boolean is recorded
as a proposal. Where they disagree it is logged, which is the cheapest
extractor-quality signal available and needs no labelling.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from judge.config import bucket_for
from judge.extract.client import ExtractionClient
from judge.extract.runner import ExtractionRefused, ExtractionRun, ThreadInput, extract
from judge.store.cells import CellOutcome, CellStore
from judge.store.claims import ClaimStore, StoredClaim
from judge.vet.weight import EvidenceTier, compute

log = logging.getLogger(__name__)

#: Until E4's tier assignment lands, every claim is weighted as a bare
#: first-hand opinion. D is the LOWEST first-hand tier, chosen deliberately:
#: guessing high would publish cells on evidence that has not earned it, and
#: this default exists to be replaced rather than to be right.
DEFAULT_EVIDENCE_TIER: EvidenceTier = "D"


@dataclass
class DocumentFacts:
    """What `collect/` computed about the document, read not recomputed.

    `judge/` reads `document`; it never writes it. These four are the ones
    weighting needs, and they had no supplier until `collect/triage/` started
    producing them — before that, `compute()` could not be called for a real
    claim at all.
    """

    document_id: str
    platform: str
    created_at: date
    names_version: bool = False
    has_conditions: bool = False
    has_numbers: bool = False


@dataclass
class PipelineResult:
    """What one thread produced, all the way through."""

    extraction: ExtractionRun
    stored_claim_ids: list[str] = field(default_factory=list)
    cells: list[CellOutcome] = field(default_factory=list)
    extractor_disagreements: list[str] = field(default_factory=list)

    @property
    def published(self) -> int:
        return sum(1 for cell in self.cells if cell.publishes)


class Pipeline:
    """E5 through E7 for one thread. Holds no state between calls."""

    def __init__(
        self,
        conn: Any,
        *,
        client: ExtractionClient,
        capability_keys: list[str],
        extractor_model: str,
    ) -> None:
        self._conn = conn
        self._client = client
        self._capabilities = capability_keys
        self._extractor_model = extractor_model
        self._claims = ClaimStore(conn)
        self._cells = CellStore(conn)

    def run(
        self,
        thread: ThreadInput,
        *,
        facts: dict[str, DocumentFacts],
        model_version_of: dict[str, str],
        release_dates: dict[str, date] | None = None,
        as_of: date | None = None,
    ) -> PipelineResult:
        """One thread, end to end.

        `facts` and `model_version_of` are passed in rather than queried, so
        this module reads no table it does not write. `collect/` owns
        `document`, and a join here would put the lane boundary inside a
        function that is meant to be plumbing.
        """
        as_of = as_of or date.today()
        result = PipelineResult(
            extraction=extract(
                thread, client=self._client, capability_keys=self._capabilities
            )
        )

        for claim, quote in result.extraction.verified:
            document = facts.get(quote.document_id)
            if document is None:
                # A verified quote whose document we know nothing about cannot
                # be weighted honestly. Skipped and named, never weighted with
                # defaults: an invented platform silently changes f_platform.
                log.warning(
                    "no document facts for %s; claim skipped rather than "
                    "weighted from defaults",
                    quote.document_id,
                )
                continue

            model_version_id = model_version_of.get(claim.model_ref.resolved_version_id or "")
            if model_version_id is None:
                # Unresolvable is a real state and a counted one. Dropping it
                # silently is how "nobody discusses this model" and "we could
                # not resolve the name" become the same absence.
                log.info(
                    "claim references %r which resolves to no tracked model",
                    claim.model_ref.surface,
                )
                continue

            if claim.has_numbers != document.has_numbers:
                # The extractor proposed; the count decides. Recorded because
                # a disagreement is a free signal about extraction quality.
                result.extractor_disagreements.append(claim.source_comment_id)

            weights = compute(
                evidence_tier=DEFAULT_EVIDENCE_TIER,
                platform=document.platform,
                capability_key=claim.capability,
                relevance=claim.relevance,
                specificity=claim.model_ref.specificity,
                claim_date=document.created_at,
                release_date=(release_dates or {}).get(model_version_id),
                as_of=as_of,
                version_named=document.names_version,
                has_conditions=document.has_conditions,
                has_numbers=document.has_numbers,
                has_repro_steps=claim.has_repro_steps,
            )

            stored = StoredClaim(
                claim=claim,
                quote=quote,
                weights=weights,
                document_id=quote.document_id,
                thread_context_id=thread.thread_context_id,
                model_version_id=model_version_id,
                condition_bucket=bucket_for(
                    claim.capability, claim.conditions.model_dump(exclude_none=True)
                ),
                evidence_tier=DEFAULT_EVIDENCE_TIER,
                claim_date=document.created_at,
                extractor_model=self._extractor_model,
            )
            result.stored_claim_ids.append(self._claims.write(stored))

        if result.stored_claim_ids:
            # Whole-table, for the reason in cells.py: a cell is a view of the
            # claims, weights decay daily, and an incremental path is a second
            # description of the aggregation that can disagree with the first.
            result.cells = self._cells.rebuild_all(as_of=as_of)

        log.info(
            "thread %s: %d proposed, %d verified, %d stored, %d cells, %d published",
            thread.thread_context_id,
            result.extraction.proposed,
            len(result.extraction.verified),
            len(result.stored_claim_ids),
            len(result.cells),
            result.published,
        )
        return result

    def run_all(
        self,
        threads: list[ThreadInput],
        *,
        facts: dict[str, DocumentFacts],
        model_version_of: dict[str, str],
        release_dates: dict[str, date] | None = None,
        as_of: date | None = None,
    ) -> list[PipelineResult]:
        """A batch. A refused thread is skipped, never fatal."""
        results: list[PipelineResult] = []
        for thread in threads:
            try:
                results.append(
                    self.run(
                        thread,
                        facts=facts,
                        model_version_of=model_version_of,
                        release_dates=release_dates,
                        as_of=as_of,
                    )
                )
            except ExtractionRefused as exc:
                log.error("thread %s refused: %s", thread.thread_context_id, exc)
        return results
