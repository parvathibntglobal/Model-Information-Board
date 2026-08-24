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

from judge import spend_ledger
from judge.config import bucket_for
from judge.curate.labels import Driver
from judge.curate.nightly import close_the_night
from judge.extract.budget import Budget
from judge.extract.client import Completion, ExtractionClient
from judge.extract.runner import ExtractionRefused, ExtractionRun, ThreadInput, extract
from judge.store.cells import CellOutcome, CellStore
from judge.store.claims import ClaimStore, StoredClaim
from judge.store.extractions import (
    ExtractionLedger,
    ExtractionRecord,
    fingerprint_of,
)
from judge.vet.reject import check as reject_check
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

    #: E6 REJECTION INPUTS. `vet.reject.check()` needs the text and the links,
    #: which the four fields above do not carry - and that is precisely why the
    #: reject stage had no caller while `vet.weight.compute()` had one. A
    #: document reaching here with `text=None` is UNVETTED, which is recorded
    #: as its own outcome rather than allowed to look like "passed": absent
    #: input is not a clean bill of health (rule 6).
    text: str | None = None
    links: tuple[str, ...] = ()
    own_domain: str | None = None
    dedup_cluster_id: str | None = None
    is_canonical_in_cluster: bool = True
    canonical_domain: str | None = None


@dataclass
class PipelineResult:
    """What one thread produced, all the way through."""

    extraction: ExtractionRun
    stored_claim_ids: list[str] = field(default_factory=list)
    cells: list[CellOutcome] = field(default_factory=list)
    extractor_disagreements: list[str] = field(default_factory=list)

    #: document_id -> (trigger, detail) for documents E6 hard-rejected. Their
    #: claims are dropped rather than weighted; kept here so a rejection is
    #: reportable instead of showing up as a thread that happened to say nothing.
    rejected_documents: dict[str, tuple[str, str]] = field(default_factory=dict)

    #: Documents that reached weighting with no text to vet. NOT the same as
    #: passing, and separated so a caller cannot read one as the other.
    unvetted_documents: list[str] = field(default_factory=list)

    #: Non-fatal observations from E6 - "free_api_credits_acknowledged" and the
    #: like. Shown beside a document rather than hiding it.
    document_flags: dict[str, tuple[str, ...]] = field(default_factory=dict)

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
        self._ledger = ExtractionLedger(conn)
        self._cells = CellStore(conn)

    def _vet(
        self,
        result: PipelineResult,
        facts: dict[str, DocumentFacts],
        release_dates: dict[str, date],
    ) -> set[str]:
        """Hard rejection, per document. Returns the ids whose claims are dropped.

        Three outcomes, kept apart on purpose:

            rejected   a rule fired. Claims dropped, trigger recorded.
            unvetted   no text was supplied, so no rule could run. Recorded as
                       its own state - reading it as "kept" would be a missing
                       value becoming a definite one.
            kept       every rule ran and none fired.

        This module still decides nothing: `reject.check()` decides, and this
        moves values into it and its verdict out.
        """
        rejected: set[str] = set()

        mentions: dict[str, list[str]] = {}
        for claim, quote in result.extraction.verified:
            resolved = claim.model_ref.resolved_version_id
            if resolved:
                mentions.setdefault(quote.document_id, []).append(resolved)

        for document_id in {q.document_id for _, q in result.extraction.verified}:
            document = facts.get(document_id)
            if document is None or document.text is None:
                result.unvetted_documents.append(document_id)
                log.warning(
                    "no text for %s, so E6 rejection could not run on it; "
                    "recorded as unvetted rather than counted as kept",
                    document_id,
                )
                continue

            verdict = reject_check(
                text=document.text,
                links=list(document.links),
                published_at=document.created_at,
                model_release_dates=release_dates,
                mentioned_models=mentions.get(document_id, []),
                dedup_cluster_id=document.dedup_cluster_id,
                is_canonical_in_cluster=document.is_canonical_in_cluster,
                canonical_domain=document.canonical_domain,
                own_domain=document.own_domain,
            )

            if verdict.flags:
                result.document_flags[document_id] = verdict.flags

            if verdict.rejected:
                rejected.add(document_id)
                trigger = getattr(verdict.trigger, "value", str(verdict.trigger))
                result.rejected_documents[document_id] = (trigger, verdict.detail)
                log.info("E6 rejected %s: %s - %s", document_id, trigger, verdict.detail)

        return rejected

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
            extraction=extract(thread, client=self._client, capability_keys=self._capabilities)
        )

        # ── E6 REJECT, which had no caller until now ────────────────────────
        #
        # `vet/reject.py` defines the affiliate-link, sponsored-disclosure and
        # discount-code rules and `pipeline.py` imported only `vet.weight`, so
        # the reject stage ran on nothing. That is not hypothetical: the four
        # claims currently on staging are quotes from a product ANNOUNCEMENT -
        # "exceptional performance in software engineering", polarity positive -
        # promotional text read as engineer opinion, which is the exact thing
        # these rules exist to stop.
        #
        # It runs per DOCUMENT and after extraction rather than before. Before
        # would be cheaper and is where `placeholder.py` sits, but rejection
        # needs the resolved model mentions, and those do not exist until the
        # extractor has proposed them. Cost is one call on a document whose
        # claims are then discarded; correctness is the whole reason the stage
        # exists. Moving it earlier is a real optimisation and a separate change.
        rejected = self._vet(result, facts, release_dates or {})

        for claim, quote in result.extraction.verified:
            if quote.document_id in rejected:
                continue

            document = facts.get(quote.document_id)
            if document is None:
                # A verified quote whose document we know nothing about cannot
                # be weighted honestly. Skipped and named, never weighted with
                # defaults: an invented platform silently changes f_platform.
                log.warning(
                    "no document facts for %s; claim skipped rather than weighted from defaults",
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
        budget: Budget | None = None,
        already_extracted: dict[str, str | None] | None = None,
        driver: Driver | None = None,
    ) -> list[PipelineResult]:
        """A batch. A refused thread is skipped, never fatal.

        `budget` stops the batch rather than the thread. A cap that skipped the
        expensive thread and carried on would spend the whole night's money on
        whatever happened to be cheap, and report a full run.

        `already_extracted` is supplied by the CALLER rather than derived here -
        see the note on the parameter. Passing nothing extracts everything,
        which is today's behaviour and is stated rather than defaulted into.
        """
        results: list[PipelineResult] = []
        # DERIVED, not defaulted. `already_extracted=None` used to mean "extract
        # everything" because nothing could work the set out; the ledger can, so
        # the default is now the correct answer rather than the safe one. An
        # explicit frozenset() still forces a full re-extraction.
        seen = self._ledger.already_extracted() if already_extracted is None else already_extracted
        for thread in threads:
            if ExtractionLedger.should_skip(seen, thread.thread_context_id, thread.flattened_text):
                log.info(
                    "thread %s already extracted at this pipeline_version; skipped",
                    thread.thread_context_id,
                )
                continue
            if budget is not None:
                # BEFORE the call. Spend cannot be undone, so a check after it
                # is a report rather than a cap.
                budget.check_before_call()
            try:
                result = self.run(
                    thread,
                    facts=facts,
                    model_version_of=model_version_of,
                    release_dates=release_dates,
                    as_of=as_of,
                )
            except ExtractionRefused as exc:
                log.error("thread %s refused: %s", thread.thread_context_id, exc)
                continue
            results.append(result)
            # Same transaction as the claims. A ledger row that survived a
            # rolled-back extraction would mark a thread read that produced
            # nothing readable, and the next run would skip it - evidence lost
            # silently and permanently.
            self._ledger.record(
                ExtractionRecord(
                    thread_context_id=thread.thread_context_id,
                    claims_written=len(result.stored_claim_ids),
                    input_tokens=result.extraction.input_tokens or None,
                    output_tokens=result.extraction.output_tokens or None,
                    schema_retries=result.extraction.schema_retries,
                    content_fingerprint=fingerprint_of(thread.flattened_text),
                )
            )
            if budget is not None:
                # Charged from what the run REPORTED, retries included, rather
                # than from the estimate the check used.
                budget.charge(
                    Completion(
                        raw_arguments="",
                        input_tokens=result.extraction.input_tokens,
                        output_tokens=result.extraction.output_tokens,
                        model=self._extractor_model,
                    )
                )
            # AND to the shared ledger, unconditionally - not inside the
            # `budget is not None` branch above. The $1/day cap is shared with
            # the ask box, so a run without a Budget object still spends from
            # the same pot, and a call this file declined to record is a call
            # the ask box is then allowed to make on top of it.
            spend_ledger.record(
                stage=spend_ledger.STAGE_EXTRACT,
                model=self._extractor_model,
                input_tokens=result.extraction.input_tokens or 0,
                output_tokens=result.extraction.output_tokens or 0,
            )
        if driver is not None:
            # THE CALLER, and the reason this parameter exists. Labels, the
            # changelog and reported context all had a writer and none had
            # anything calling it, so the changelog page would have reported
            # "no labels changed" forever - honestly, and about nothing.
            #
            # `driver=None` skips it rather than defaulting, because attributing
            # a run to `new-evidence` when the caller did not say so is the one
            # thing `close_the_night` refuses to do.
            close_the_night(
                self._conn, driver=driver, as_of_cells=[cell for r in results for cell in r.cells]
            )

        return results
