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

    evidence_tier    (claim.model_ref.speaking, claim.has_repro_steps,
                     claim.has_numbers vetoed by document.has_numbers), through
                     contract/harvest.yaml evidence_tier_rules
    version_named    claim.model_ref.specificity — snapshot or version is true
    has_conditions   document.has_conditions — UNRESOLVED, see below
    has_numbers      document.has_numbers — the COUNTED one, not the extractor's
    condition_bucket judge/config.bucket_for(), from the claim's conditions

`has_numbers` is the interesting one. `ExtractedClaim` carries the extractor's
opinion of it, and rule 2 forbids a model participating in weighting — so the
document-level count is authoritative and the extractor's boolean is recorded
as a proposal. Where they disagree it is logged, which is the cheapest
extractor-quality signal available and needs no labelling.

TWO OF THOSE FOUR WERE REQUIRED ARGUMENTS WITH NO SUPPLIER — FIXED 2026-08-21
----------------------------------------------------------------------------
`version_named` and `has_conditions` used to read `document.names_version` and
`document.has_conditions`. Both are fields on `DocumentFacts` with a `False`
default, and **`DocumentFacts` has exactly one constructor in the repository:
`tests/test_pipeline_db.py:190`.** There is no production caller, because
`run_all` takes `facts` as a parameter and the nightly job that would build it
does not exist yet. So in every real run both arrived as the dataclass default,
and `specificity_factor` was scoring `version_named=False` for every claim in
the corpus — including claims that named a snapshot.

The database has the columns and they are barely populated either:
`document.names_version` is True on 4 rows, False on 3, NULL on 57;
`document.has_conditions` is **False on all 7 populated rows and NULL on 57 —
never True, not once**. So wiring `DocumentFacts` to the table would have
replaced a hardcoded False with a mostly-NULL False, which is rule 6's shape:
absent silently becoming definite.

`version_named` is now derived from the claim, which is the granularity
`specificity_factor` is evaluated at: `specificity in ("snapshot", "version")`
is the same fact the field was named for, taken from the value that actually
carries it.

`has_conditions` IS LEFT UNRESOLVED, AND THAT IS THE DECISION RATHER THAN THE
TODO. It was derived from `claim.conditions` for about an hour and reverted.

The derivation looks obvious — any non-None field on `claim.conditions`, the
same expression used two lines below for `condition_bucket` — and it is wrong
for the reason `Conditions` exists. Its own docstring: *"Every field is
optional, because a human writing a forum post owes us nothing. Absent means
absent — never guessed into a band."* An empty `Conditions` means the writer did
not state their conditions. It does not mean the DOCUMENT stated none, and it
certainly does not mean the claim was made without conditions.

So `bool(claim.conditions...)` answers "did the extractor fill any field",
which is a fact about extraction, and `specificity_factor` would spend it as
"was this person being specific" — a fact about the writer. Weighting a claim
down because a field is absent converts a missing value into a definite one,
which is rule 6, and it does it silently across every claim in the corpus.
**A wrong derivation here is worse than a missing input**: a missing input is
visibly constant, and this would look like a working signal while ranking claims
on a distinction nobody made.

The document column is no better and the numbers say so: `document.has_conditions`
is **False on all 7 populated rows and NULL on 57** — never True, not once. So
wiring `DocumentFacts` to the table replaces a hardcoded False with a mostly-NULL
False, which is the same rule-6 conversion one layer down.

What it actually needs is a source that can say "not stated" distinctly from
"stated as absent" — a three-valued input, or removing the signal from
`specificity_factor`. Both are decisions about what the factor measures. Until
one is made this argument stays visibly dead rather than plausibly alive, which
is the honest state for an input nobody can supply.

WHAT THIS COSTS, STATED RATHER THAN HIDDEN. `f_specificity` now gives +0.2 for
a fact `f_fuzziness` already prices at 1.0/0.6/0.3, so one fact is priced twice
and the compounded discount was chosen by nobody: a family claim carrying only
`version_named` falls from 0.1122 to 0.0765, a 32% cut. That is a real
objection and it is smaller than the alternative, which was a required argument
supplied from a dataclass default. **The clean version is to drop
`version_named` from `specificity_factor` entirely** — attribution is
`f_fuzziness`'s job and it already does it, leaving `f_specificity` as three
artifact signals with one meaning. That is a decision about what the factor is
for rather than a wiring fix, so it is not taken here.
`docs/measurements/f-specificity-double-counting.txt` has the arithmetic.

`document.has_numbers` is deliberately NOT derived from the claim. Rule 2 —
`ExtractedClaim.has_numbers` is the extractor's opinion, and a model may not
participate in weighting. That one needs `DocumentFacts` wired to the table,
which is a different fix with a different reason.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol, runtime_checkable

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
from judge.vet.weight import (
    UNSUPPLIED,
    _Unsupplied,
    compute,
    evidence_tier_for,
    promotable_numbers,
)

log = logging.getLogger(__name__)

#: Until E4's tier assignment lands, every claim is weighted as a bare
#: first-hand opinion. D is the LOWEST first-hand tier, chosen deliberately:
#: guessing high would publish cells on evidence that has not earned it, and
#: this default exists to be replaced rather than to be right.
#: RETIRED AS A VALUE 2026-08-21. It was `"D"` — tier D, 0.12, "bare first-hand
#: opinion" — passed to every claim in the corpus by both call sites below,
#: including three that quote a vendor announcement and should be F at 0.02. A
#: 6x over-weight, applied uniformly, by a module literal.
#:
#: Its docstring said "this default exists to be replaced rather than to be
#: right", which was true and was not enforceable while it was a plausible
#: tier. It is now the sentinel, so `compute()` refuses and names it as a
#: WRONG_WRITER gap rather than weighting on it.
#:
#: What closes it: a real tier per claim. The proposed source is a `speaking`
#: enum on `ModelRef` —
#: `docs/proposals/for-engineer-2-a-speaking-field-on-modelref.md`.
DEFAULT_EVIDENCE_TIER = UNSUPPLIED


@dataclass
class DocumentFacts:
    """What `collect/` computed about the document, read not recomputed.

    `judge/` reads `document`; it never writes it.

    THREE OF THESE SIX ARE STILL UNSUPPLIED, AND THIS CLASS HAS NO PRODUCTION
    CONSTRUCTOR. The only one in the repository is
    `tests/test_pipeline_db.py:190`; `run_all` takes `facts` as a parameter and
    the nightly job that would build it from the `document` table is not
    written. So the three booleans below arrive as their defaults in any real
    run.

    `names_version` was removed from the weighting path on 2026-08-21 — see the
    module docstring — and is kept here because the column exists and a caller
    wiring this up should carry it rather than rediscover it.

    **`has_conditions` and `has_numbers` are both still read by `compute()` and
    both still default**, for two different reasons that are each deliberate:
    `has_numbers` cannot come from the claim because rule 2 forbids weighting on
    the extractor's boolean, and `has_conditions` has no honest source on either
    side — an absent condition is not a stated absence. Module docstring.
    """

    document_id: str
    platform: str
    created_at: date
    #: The document's author (`document.author_id`), carried so it can be written
    #: onto the claim. WITHOUT IT NO CELL CAN EVER PUBLISH: `cells.py` derives a
    #: voice from `claim.author_id or f"anon:{platform}"`, so a NULL author on
    #: every claim collapses all of a platform's claims into ONE voice, capping
    #: `independent_voices` at 1 where the gate needs several. NULL here stays
    #: NULL (rule 6) — an unknown author is the anonymous fallback, not an
    #: invented identity — but a KNOWN author must reach the claim.
    author_id: str | None = None
    #: Retained for a future caller; NOT read by the weighting path any more.
    names_version: bool | _Unsupplied = UNSUPPLIED
    #: READ BY `compute()`, AND NO LONGER DEFAULTING TO `False`. An absent
    #: condition is not a stated absence, so the absence is now carried as
    #: `UNSUPPLIED` and `compute()` refuses rather than weighting on it.
    has_conditions: bool | _Unsupplied = UNSUPPLIED
    #: READ BY `compute()`, AND NO LONGER DEFAULTING TO `False`. Same ruling.
    has_numbers: bool | _Unsupplied = UNSUPPLIED

    # ── THE FIELDS `judge/vet/reject.py` READS, restored at the merge ────────
    #
    # `main` added these while this branch was 304 commits behind, and the
    # auto-merge kept THIS side of the class wholesale - so they vanished
    # without a conflict marker. `reject_check` calls `document.text`,
    # `.links`, `.dedup_cluster_id` and `.is_canonical_in_cluster`, and the
    # only thing that noticed was `tests/test_pipeline_vets.py` failing with
    # `unexpected keyword argument 'text'`.
    #
    # Worth the comment because of HOW it hid: two sides edited one dataclass in
    # different regions, git merged both cleanly, and the result was a class
    # missing half of what one caller needs. A clean merge is not a working one,
    # and the suite is what said so.
    #
    # These keep `main`'s defaults rather than UNSUPPLIED: they feed the REJECT
    # path, not the weighting path, and the 2026-08-21 ruling is about
    # weighting inputs. An absent link list genuinely is an empty one.
    text: str | None = None
    links: tuple[str, ...] = ()
    own_domain: str | None = None
    dedup_cluster_id: str | None = None
    is_canonical_in_cluster: bool = True
    canonical_domain: str | None = None


@runtime_checkable
class SurfaceFinder(Protocol):
    """Text -> every model surface that appears in it. For inheritance only.

    WHY THIS IS A SECOND PROTOCOL AND NOT A METHOD ON `SurfaceResolver`.
    `SurfaceResolver` answers "what model is this string?" and is asked about a
    surface. This answers "does this text name any model?" and is asked about a
    quote. Same population, opposite direction, and folding them would give the
    resolver a method the store path never calls.

    Injected the same way and for the same reason: the population lives in
    `collect/` and this lane may not import it. `collect.surface_resolver`
    supplies an implementation.
    """

    def __call__(self, text: str) -> tuple[str, ...]: ...


def subject_was_inherited(
    quote: str,
    *,
    model_version_id: str | None,
    find_surfaces: SurfaceFinder | None,
) -> bool | None:
    """Did this claim's subject come from outside its own quote?

    DERIVED IN CODE, NEVER ASKED OF THE MODEL, and that is the point. A field
    the extractor filled could assert `false` about a quote naming nothing, and
    nothing would catch it - the same shape as asking for a canonical id
    instead of resolving one. Here the model proposes the attribution and code
    checks whether the quote supports it, which is quote verification's own
    argument applied to the subject.

    Measured on the four claims in the table:

        STATED     13 surfaces in the quote   "So when Fable's classifiers…"
        INHERITED   0 surfaces in the quote   "We'll keep refining the safeguards…"
        INHERITED   0                         "exceptional performance in software engineering"
        INHERITED   0                         "gives 10%+ better results on SWE-Bench"

    **Three of four, and all four record `specificity=version`.** `claim` has no
    `surface` column, so the string that justified `version` is not in the row
    and is not recoverable from it. The row asserts a precision its quote does
    not have, and that is on rows already rendered.

    Returns None when no finder was supplied - absent rather than False, because
    "nobody checked" and "checked and the quote names a model" are different
    facts and rule 6 keeps them apart.
    """
    verdict = quote_subject_verdict(
        quote, model_version_id=model_version_id, find_surfaces=find_surfaces
    )
    if verdict is None:
        return None
    # `QUOTE_NAMES_SOMETHING_UNCOMPARED` is False here and that is not a
    # shortcut: this question is only "did the quote name a model", which the
    # surface list answers without a resolver. The comparison is the OTHER
    # question, and its absence must not turn this one into None.
    return verdict is QUOTE_NAMES_NOTHING


#: The quote names no model at all. The LEGITIMATE case, and the common one: a
#: comment inheriting its subject from a thread root is not a defect, and this
#: check must never call it one.
QUOTE_NAMES_NOTHING = "names-nothing"
#: The quote names the model the claim is filed against. Agreement.
QUOTE_NAMES_THE_MODEL = "names-the-model"
#: The quote names a model, and NOT the one the claim is filed against.
#: The defect. See `quote_subject_verdict`.
QUOTE_NAMES_ANOTHER = "names-another-model"
#: The quote names at least one model and no `resolve_surface` was supplied, so
#: WHICH model could not be compared. Distinct from agreement and from
#: disagreement, because a check that could not run must not report either.
QUOTE_NAMES_SOMETHING_UNCOMPARED = "names-something-uncompared"


def quote_subject_verdict(
    quote: str,
    *,
    model_version_id: str | None,
    find_surfaces: SurfaceFinder | None,
    resolve_surface: SurfaceResolver | None = None,
) -> str | None:
    """Does the quote name the model the claim is filed against?

    THE THIRD CHECK, AND THE GAP THE GPT-5.6 CASE FOUND. Verification proves the
    quote is real; resolution proves the model exists; **nothing proved the
    quote mentions the model.** A claim could be verified, attributed, and about
    a different model than the one whose page it renders on - which is exactly
    what happened: `"I'm now generating my summaries using GPT-5.6 Luna."` filed
    against `openai/gpt-5` and displayed there with a working permalink.

    No model call. Same shape as `subject_was_inherited`: the extractor proposes
    an attribution and code checks whether the quote supports it.

    THREE STATES FROM ONE RESOLUTION, which is why this and
    `subject_was_inherited` are one function rather than two:

        QUOTE_NAMES_NOTHING    the quote names no model. LEGITIMATE - a comment
                               inheriting a thread root's subject lands here, and
                               so does every blog sentence saying "it". This is
                               what `subject_was_inherited` reports as True.
        QUOTE_NAMES_THE_MODEL  agreement. Nothing to say.
        QUOTE_NAMES_ANOTHER    the quote names a DIFFERENT model. The defect.
        QUOTE_NAMES_SOMETHING_UNCOMPARED
                               a model is named and no resolver was supplied, so
                               which one is unknown. `subject_was_inherited`
                               still answers False here, because its question is
                               settled by the surface list alone.

    **They compose rather than conflict, and they had to be one function to do
    it.** Written separately, each would call `find_surfaces(quote)` and reach
    its own conclusion, and the day one changed how it resolved the two would
    disagree about the same quote - `subject_inherited=False` beside
    "the quote names nothing" is a contradiction nobody would see, because the
    two are reported in different places. One resolution, three outcomes, and
    `subject_was_inherited` is now a projection of this rather than a sibling.

    `resolve_surface` is OPTIONAL and the reason is rule 6: without it the
    surfaces in a quote cannot be turned into model ids, so the comparison
    cannot be made and the answer is None - *not* agreement. A check that
    reports "fine" when it could not run is worse than one that does not run.

    THE RATIO IS THE FINDING, NOT THE COUNT
    ---------------------------------------
    Measured on `/models/openai/gpt-5` before those rows were deleted:
    **3 of the page's 5 rendered quotes were mis-attributed.** Not 3 of 176
    claims - 3 of the 5 a reader could actually see.

    ⚠ AND THE MECHANISM I ATTACHED TO THAT RATIO WAS OVERSTATED. Corrected
    2026-08-21.

    I wrote that the board surfaces mis-attribution PREFERENTIALLY, because a
    wrong-but-confident resolution reaches a cell at the same rate a right one
    does while an unresolvable claim is dropped. That reasoning is sound and its
    only evidence was not: the 3-of-5 on the GPT-5 page came from a population I
    had built wrong, not from a property of the pipeline. On the claims that
    remain the flagged share is **1 of 6 stored, 1 of the 2 quotes in its own
    cell** - no over-representation at all.

    So the honest statement is narrower: **a mis-attributed claim renders exactly
    as readily as a correct one**, which is enough reason to check, and is NOT
    evidence that the board is enriched for them. The urgency the stronger
    reading would have justified is not supported.

    KNOWN FALSE-POSITIVE CLASS, and it is governed by `FAMILY_WORDS`
    ---------------------------------------------------------------
    A quote whose only reference to its true subject is a bare family word gets
    flagged, because family words are excluded from the surface population. The
    live instance: *"So when Fable's classifiers detect a request ... the
    response is handled by Claude Opus 4.8"*, filed against `claude-fable-5`.
    The quote names Opus 4.8 and refers to Fable only possessively, so the
    finder sees one model and not the other - and the attribution is defensible.

    So this is a REVIEW signal, not a gate. Its accuracy on exactly the decision
    it would be making has never been measured, which is the same argument that
    kept `speaking` to weighting rather than storage.
    """
    if find_surfaces is None or model_version_id is None:
        return None

    surfaces = find_surfaces(quote)
    if not surfaces:
        return QUOTE_NAMES_NOTHING

    if resolve_surface is None:
        # Surfaces found and no way to compare them. Its own state: NOT
        # agreement, NOT disagreement, and not None either - "the quote names a
        # model" is settled even when "which one" is not.
        return QUOTE_NAMES_SOMETHING_UNCOMPARED

    named = {resolve_surface(surface) for surface in surfaces}
    named.discard(None)
    if not named:
        # Every surface in the quote resolved to nothing - an unseated model, a
        # family word, a product name. The quote names no model WE TRACK, which
        # for this check is the same state as naming none.
        return QUOTE_NAMES_NOTHING
    if model_version_id in named:
        return QUOTE_NAMES_THE_MODEL
    return QUOTE_NAMES_ANOTHER


@runtime_checkable
class SurfaceResolver(Protocol):
    """Surface as a human wrote it -> `model_version.id`, or None.

    WHY THIS EXISTS, AND IT IS NOT A NEW IDEA. `ModelRef.resolved_version_id`
    is a schema field with a `None` default that **nothing ever wrote**. It
    appears in exactly two non-test places: the field, and the read at the
    bottom of `run()`. The prompt never mentions it, so the model correctly
    leaves it null, and every claim was then dropped for referencing no tracked
    model. Nothing was broken — the path had never been walked end to end.

    RESOLUTION IS CODE'S, NOT THE MODEL'S. Asking the extractor for a canonical
    id would make an LLM decide identity, which rule 2 forbids: it may propose,
    it may never decide. So the model proposes a SURFACE, exactly as written,
    and something outside this lane maps it.

    Option (a), the same shape as `ExtractionClient` and for the reason
    `judge/extract/resolver.py` gives: this lane NAMES what it needs and
    whoever composes the application provides it. `collect/triage/entity.py`
    owns the surface population and the normalisation; a dict passed in here
    would have to agree with that normalisation and would silently rot when it
    changed, so the callable goes across the boundary rather than its output.

    RETURNING None IS A RESULT. An ambiguous surface — one owned by several
    models, of which the substitution corpus found 49 — must come back None so
    the claim is skipped and counted, never resolved to whichever model sorted
    first (rule 6).
    """

    def __call__(self, surface: str) -> str | None: ...

    # NOTE: six `DocumentFacts` fields from `origin/main` were merged INTO this
    # protocol here, after `__call__`, and git reported no conflict. They belong
    # to `DocumentFacts` and now live there. Left as a comment because the
    # failure mode is worth a line at the scene: a runtime_checkable Protocol
    # with data members stops matching a plain callable, so
    # `isinstance(resolver, SurfaceResolver)` went False and one test caught what
    # a clean merge and a passing import did not.


class _CellRefused(Exception):
    """The cell half already refused this claim and recorded why.

    A sentinel rather than a flag check, so the claim write and the "nothing was
    attempted" case leave through the same door and the board write below is
    reached by exactly one path. Never raised outside this module.
    """


@dataclass
class PipelineResult:
    """What one thread produced, all the way through."""

    extraction: ExtractionRun
    stored_claim_ids: list[str] = field(default_factory=list)

    #: (document_id, error) for claims that could not be written. NOT silent:
    #: a claim lost to a schema constraint is a finding about our own
    #: machinery, and the board entries for that quote still landed - so a run
    #: with failures here is NOT a run that produced nothing.
    claim_write_failures: list[tuple[str, str]] = field(default_factory=list)

    #: (document_id, capability_key, error) for claims the LEGACY CELL PATH
    #: refused before anything was attempted against the database.
    #:
    #: DISTINCT FROM `claim_write_failures` ON PURPOSE. That one is "the write
    #: was attempted and the database said no". This is "the cell could not be
    #: built at all" - `compute()` or `bucket_for()` rejecting a capability key
    #: outside the ratified twelve. Folding them together would hide which of
    #: the two is happening, and they have different fixes: one is a schema
    #: constraint, the other is a vocabulary the extractor did not honour.
    #:
    #: A NON-EMPTY LIST HERE IS NOT A LOST BATCH. Before 2026-09-14 either
    #: refusal escaped the loop and took every remaining claim AND every
    #: remaining board entry with it. Now the board entry for the same quote is
    #: still written, so a run reporting cell refusals still produced evidence.
    cell_refusals: list[tuple[str, str, str]] = field(default_factory=list)
    #: How many `board_entry` rows this thread produced. Counted rather
    #: than inferred from the claims: one claim can inform three board
    #: sections, so the two numbers are legitimately different and a
    #: reader comparing them should see why.
    board_entries_stored: int = 0
    cells: list[CellOutcome] = field(default_factory=list)
    extractor_disagreements: list[str] = field(default_factory=list)
    #: Claims whose subject came from outside their own quote. DERIVED in code,
    #: never asked of the model - see `subject_was_inherited`. Counted rather
    #: than stored per claim, because the column is proposed and not signed off.
    subjects_inherited: int = 0
    #: Claims whose quote names a model that is NOT the one the claim is filed
    #: against. Verified, attributed, and wrong - the gap the GPT-5.6 case found.
    #: Same standing as `subjects_inherited`: counted, logged, not stored.
    quote_names_another_model: int = 0
    #: Surfaces the extractor proposed that resolve to no tracked model, in the
    #: order they were dropped. NOT a count: the SURFACE is the finding - it says
    #: whether the drop was a family name, an ambiguous codename or a range, and
    #: a count says only that something went missing. Every one is a deliberate
    #: refusal to invent specificity; this is the record of what was refused.
    unresolved_surfaces: list[str] = field(default_factory=list)

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

    #: signal name -> how many claims could NOT be promoted on it because the
    #: input was absent rather than false. The tier ladder withholds rather than
    #: refuses (see `evidence_tier_for`), so without this counter a claim that
    #: stayed at D because nobody counted its numbers is indistinguishable from
    #: one that stayed at D because it is a bare opinion. Rule 4, one stage
    #: before the page: the absence has to be reportable.
    tier_signals_unconfirmed: Counter[str] = field(default_factory=Counter)

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
        # WHICH MODEL THIS RUN IS FOR, so a board entry can say whether
        # its model was SEARCHED FOR or merely MENTIONED in a thread
        # retrieved for a different one. Optional and defaulting to None
        # on purpose: a caller that does not know must produce NULL
        # rather than a guess, and the nightly chain (which sweeps rather
        # than fetching one model) genuinely has no subject to name.
        searched_model_version_id: str | None = None,
    ) -> None:
        self._conn = conn
        self._client = client
        self._capabilities = capability_keys
        self._extractor_model = extractor_model
        self._searched_model_version_id = searched_model_version_id
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
        resolve_surface: SurfaceResolver | None = None,
        find_surfaces: SurfaceFinder | None = None,
        rebuild_cells: bool = True,
    ) -> PipelineResult:
        """One thread, end to end.

        `rebuild_cells=False` is for `run_all`, which rebuilds ONCE after the
        batch instead of once per thread. See the measurement in
        `docs/measurements/the-twenty-seconds-is-a-full-board-rebuild-per-thread.md`
        - per-thread it made a batch quadratic in cells. The default stays True
        so a single `run()` still leaves a consistent board.

        `facts` and `model_version_of` are passed in rather than queried, so
        this module reads no table it does not write. `collect/` owns
        `document`, and a join here would put the lane boundary inside a
        function that is meant to be plumbing.

        `resolve_surface` is the same arrangement for model identity — see
        `SurfaceResolver`. Omitting it keeps the previous behaviour exactly:
        claims resolve only through `resolved_version_id`, which nothing
        populates, so every claim is skipped. That is stated rather than
        defaulted into, because it was the behaviour for the whole of the
        pipeline's life and it looked like a registry problem.
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

        board_rows: list[dict] = []
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

            # TWO ROUTES, TRIED IN THAT ORDER.
            #
            # `resolved_version_id` first, so a future extractor that does
            # populate it is not overridden. Then the surface, resolved by code
            # outside this lane. Before this, only the first route existed and
            # nothing drove it.
            model_version_id = model_version_of.get(claim.model_ref.resolved_version_id or "")
            if model_version_id is None and resolve_surface is not None:
                model_version_id = resolve_surface(claim.model_ref.surface)
            if model_version_id is None:
                # Unresolvable is a real state and a counted one. Dropping it
                # silently is how "nobody discusses this model" and "we could
                # not resolve the name" become the same absence.
                #
                # RECORDED ON THE RESULT, not only logged. This comment described
                # the hazard for months while the only trace was a `log.info`
                # the default level does not emit - so 347 of 450 verified claims
                # vanished on 2026-08-28 with nothing to read afterwards, and
                # `judge/cli.py` said of them: "Neither is recorded anywhere but
                # this output."
                #
                # MEASURED, and every observed drop was a CORRECT refusal:
                # '5.0' (a version with no family), 'Qwen' (family only), 'Terra'
                # and 'Sol' (each ambiguous between a base and a -pro variant),
                # 'Opus 4.2-4.7' (a range). Resolving any of them would invent
                # specificity. So this records what we declined to guess, which is
                # rule 4's absence problem at the largest scale in the pipeline.
                result.unresolved_surfaces.append(claim.model_ref.surface)
                log.info(
                    "claim references %r which resolves to no tracked model",
                    claim.model_ref.surface,
                )
                continue

            if claim.has_numbers != document.has_numbers:
                # The extractor proposed; the count decides. Recorded because
                # a disagreement is a free signal about extraction quality.
                result.extractor_disagreements.append(claim.source_comment_id)

            # DERIVED, NOT ASKED FOR. See `subject_was_inherited`: the model
            # proposes the attribution and code checks whether the quote
            # supports it. Computed and logged rather than stored, because the
            # column is proposed and not signed off -
            # docs/proposals/for-engineer-2-subject-inheritance-and-the-thread-cap.md
            # ONE RESOLUTION, BOTH QUESTIONS. `subject_was_inherited` is a
            # projection of this verdict, so the two cannot disagree about the
            # same quote.
            verdict = quote_subject_verdict(
                claim.quote,
                model_version_id=model_version_id,
                find_surfaces=find_surfaces,
                resolve_surface=resolve_surface,
            )
            if verdict is QUOTE_NAMES_ANOTHER:
                # THE THIRD CHECK. Verified, attributed, and about a different
                # model than the page it will render on. Counted and logged, not
                # stored: the column is proposed and unsigned, same standing as
                # `subject_inherited`.
                result.quote_names_another_model += 1
                log.warning(
                    "thread %s: claim filed against %s quotes %r, which names a "
                    "DIFFERENT model. Verification passed, resolution passed, "
                    "and the quote is about something else.",
                    thread.thread_context_id,
                    model_version_id,
                    claim.quote[:80],
                )
            inherited = verdict is QUOTE_NAMES_NOTHING if verdict else None
            if inherited:
                log.info(
                    "thread %s: claim quoting %r names no model in its own "
                    "quote; subject inherited from elsewhere in the document, "
                    "and the row will record specificity=%s regardless",
                    thread.thread_context_id,
                    claim.quote[:60],
                    claim.model_ref.specificity,
                )
            result.subjects_inherited += 1 if inherited else 0

            # THE TIER COMES FROM WHAT THE EVIDENCE CARRIES, not from a literal
            # and, since 2026-08-30, not from `speaking` alone. `speaking` said
            # WHOSE claim it is; the tier grades HOW CHECKABLE it is, so keying
            # one on the other floored every first-hand report at D whether it
            # carried a harness or a hunch. `evidence_tier_for` still returns
            # UNSUPPLIED for a `speaking` value the contract does not price, and
            # `compute()` refuses, so that stays a named gap rather than a
            # silent tier.
            #
            # `promotable_numbers` is the falsifier: the extractor proposes
            # `has_numbers` and `document.has_numbers` - counted by code in
            # collect/triage/ - may veto it. It can only veto. A promotion the
            # code cannot confirm is withheld and NAMED, never silently taken
            # and never turned into a dropped claim.
            verdict = evidence_tier_for(
                claim.model_ref.speaking,
                has_repro_steps=claim.has_repro_steps,
                has_numbers=promotable_numbers(
                    claim.has_numbers, document.has_numbers
                ),
            )
            evidence_tier = verdict.tier
            for signal in verdict.unconfirmed:
                result.tier_signals_unconfirmed[signal] += 1

            # ── THE CELL HALF, GUARDED AS ONE REGION ─────────────────────────
            #
            # TWO SITES READ THE LEGACY CLOSED KEY AND BOTH RAISE ON ONE IT DOES
            # NOT KNOW, and until 2026-09-14 neither was guarded:
            #
            #   compute()     ValueError "unknown capability 'vision' - it must
            #                 exist in contract/capabilities.yaml"
            #   bucket_for()  KeyError 'vision', from a bare dict lookup on
            #                 `dominant_dimension()`. The worse of the two: its
            #                 message is the key and nothing else.
            #
            # `capability` is a closed vocabulary enforced in the tool schema
            # since 2026-09-14 (`tool_schema_for(..., capability_keys=...)`), so
            # a non-compliant key should no longer arrive. Should is not a
            # guarantee - providers differ on whether they validate an enum, the
            # lesson `prefixItems` already taught this codebase - so the
            # assertion stays and is now survivable.
            #
            # WRAPPING `compute()` ALONE WOULD NOT HAVE BEEN ENOUGH, and neither
            # would `try: ... continue`. `continue` skips the board write below,
            # which is exactly what the 2026-09-10 fix exists to prevent: "A
            # CLAIM FAILING MUST NOT COST THE BOARD." So this sets the cell
            # aside and falls THROUGH to the board, which is the same shape that
            # fix chose one statement later.
            stored: StoredClaim | None = None
            try:
                weights = compute(
                    evidence_tier=evidence_tier,
                    platform=document.platform,
                    capability_key=claim.capability,
                    relevance=claim.relevance,
                    specificity=claim.model_ref.specificity,
                    claim_date=document.created_at,
                    release_date=(release_dates or {}).get(model_version_id),
                    as_of=as_of,
                    # DERIVED FROM THE CLAIM, not read from the document.
                    # `DocumentFacts` has exactly one constructor in the repository
                    # and it is a test, so this was a required argument supplied
                    # from a dataclass default. See the module docstring.
                    version_named=claim.model_ref.specificity in ("snapshot", "version"),
                    # NOT DERIVED, DELIBERATELY. See the module docstring: there is
                    # no honest claim-side source for this one, and a wrong
                    # derivation is worse than a missing input.
                    has_conditions=document.has_conditions,
                    has_numbers=document.has_numbers,
                    has_repro_steps=claim.has_repro_steps,
                )

                stored = StoredClaim(
                    claim=claim,
                    quote=quote,
                    weights=weights,
                    document_id=quote.document_id,
                    # From the RESOLVED document (verify step 2 picked which comment),
                    # so a Reddit thread's claims carry the author of the comment the
                    # quote came from — distinct people, distinct voices. Without this
                    # every claim was one anonymous voice and no cell could publish.
                    author_id=document.author_id,
                    thread_context_id=thread.thread_context_id,
                    model_version_id=model_version_id,
                    condition_bucket=bucket_for(
                        claim.capability, claim.conditions.model_dump(exclude_none=True)
                    ),
                    evidence_tier=evidence_tier,
                    claim_date=document.created_at,
                    extractor_model=self._extractor_model,
                )
            except (ValueError, KeyError, LookupError) as exc:
                # NAMED, NOT COUNTED. A bare tally would say "3 claims lost" and
                # leave nobody able to tell an unratified capability from a
                # missing tier - rule 4 on what the pipeline discards. `KeyError`
                # stringifies to just the key, so the type is carried too.
                result.cell_refusals.append(
                    (quote.document_id, claim.capability,
                     f"{type(exc).__name__}: {str(exc).splitlines()[0][:160]}")
                )
                log.warning(
                    "claim on %r refused by the legacy cell path (%s: %s); the "
                    "board entry is still written",
                    claim.capability, type(exc).__name__,
                    str(exc).splitlines()[0][:120],
                )
            # CAPTURED PER ITERATION, not read back off the tail of the list.
            # The board rows below used `stored_claim_ids[-1]`, which is the
            # LAST id written by any iteration - so a quote whose own claim
            # failed would have attached the PREVIOUS quote's claim id, quietly
            # mis-attributing the evidence. `None` is the honest value, and
            # `board_entry.claim_id` is nullable for exactly this.
            _claim_id: str | None = None
            # `None` MEANS THE CELL HALF ALREADY REFUSED, above, and said why.
            # Not an error here and not silence either: it is recorded in
            # `cell_refusals`, and falling through to the board is the point.
            try:
                if stored is None:
                    raise _CellRefused
                # A SAVEPOINT, NOT JUST A try/except. A failed INSERT ABORTS THE
                # WHOLE TRANSACTION in Postgres - every later statement on this
                # connection then fails with `InFailedSqlTransaction`, including
                # the board_entry insert this fix exists to protect. Catching
                # the exception without rolling back to a savepoint would move
                # the failure one statement later and lose the board anyway.
                #
                # `conn.transaction()` opens a SAVEPOINT when a transaction is
                # already open, which it is: the caller owns the outer one and
                # commits after the loop.
                with self._conn.transaction():
                    _claim_id = self._claims.write(stored)
                result.stored_claim_ids.append(_claim_id)
            except _CellRefused:
                # Already recorded in `cell_refusals` with its reason. Not added
                # to `claim_write_failures` as well, because nothing was
                # attempted and double-counting one loss in two tallies is how a
                # denominator stops meaning anything (rule 7).
                _claim_id = None
            except Exception as exc:
                _claim_id = None
                # A CLAIM FAILING MUST NOT COST THE BOARD. `board_entry` was
                # built to stand alone - its `claim_id` is nullable - and the
                # 2026-09-10 run lost every board entry in the batch to one FK
                # violation on the legacy capability column. The cell is lost;
                # the discovered section is not.
                result.claim_write_failures.append(
                    (quote.document_id, str(exc).splitlines()[0][:180])
                )

            # ── THE BOARD ────────────────────────────────────────────────────
            # What the classifier DISCOVERED about this quote, written where the
            # claim is written so the two can never disagree about provenance.
            #
            # A claim can be stored and produce NO board entry: `board_entries`
            # is required by the schema, so an empty list cannot arrive, but a
            # claim whose model did not resolve has no `model_version_id` and its
            # section would be unattributable. That is recorded as an entry with
            # a NULL model rather than dropped - the section was discussed, and
            # which model it was about is a separate fact that may be absent
            # (rule 6: absent stays absent, it does not become false).
            #
            # `quote_verified=True` is not optimism: this loop runs over
            # `extraction.verified`, which is what survived the substring check
            # against the text the model was shown. The table CHECKs it true, so
            # an unverified quote could not be written here even by mistake.
            for _entry in claim.board_entries:
                board_rows.append({
                    "section": _entry.section,
                    "slug": _entry.slug,
                    "name": _entry.name,
                    "definition": _entry.definition,
                    "unit": _entry.unit,
                    "value_verbatim": _entry.value_verbatim,
                    "basis": _entry.basis,
                    "model_version_id": model_version_id,
                    "document_id": quote.document_id,
                    "claim_id": _claim_id,
                    "quote": quote.display_text,
                    "quote_verified": True,
                    "polarity": claim.polarity,
                })

        if board_rows:
            # Append-only and idempotent (`ON CONFLICT DO NOTHING` on a content
            # hash), so re-running the pipeline over the same corpus cannot
            # inflate the report count the board shows.
            from judge.store.board_entries import store_entries

            outcome = store_entries(
                self._conn, board_rows,
                proposer_model=self._extractor_model,
                searched_model_version_id=self._searched_model_version_id,
            )
            result.board_entries_stored = outcome["stored"]
            log.info(
                "thread %s: %d board entr(ies) proposed, %d stored, %d skipped",
                thread.thread_context_id, outcome["proposed"],
                outcome["stored"], outcome["skipped_unverified"],
            )

        if result.stored_claim_ids and rebuild_cells:
            # Whole-table, for the reason in cells.py: a cell is a view of the
            # claims, weights decay daily, and an incremental path is a second
            # description of the aggregation that can disagree with the first.
            #
            # WHOLE-TABLE IS RIGHT AND PER-THREAD WAS NOT. `rebuild_all` walks
            # every cell with evidence, at 3 sequential statements each, so a
            # BATCH paid for every cell its earlier threads had created - 16.35s
            # of a 21.70s thread, measured, and growing with the board. That is
            # quadratic in cells at any latency, which is why `run_all` passes
            # `rebuild_cells=False` and rebuilds once at the end.
            #
            # The cells.py argument is untouched: still whole-table, still one
            # description of the aggregation. Only the FREQUENCY changed.
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
        resolve_surface: SurfaceResolver | None = None,
        find_surfaces: SurfaceFinder | None = None,
        on_thread: Callable[[str], None] | None = None,
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
            # A progress hook for callers that want to SEE a long batch move -
            # the on-demand fetch's E5 was silent for the whole extraction, so a
            # slow run and a hung one looked identical. Fired before the call it
            # is about to make; a no-op for the nightly batch, which passes none.
            if on_thread is not None:
                on_thread(thread.thread_context_id)
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
                    resolve_surface=resolve_surface,
                    find_surfaces=find_surfaces,
                    # ONCE AFTER THE BATCH, not once per thread. See below.
                    rebuild_cells=False,
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
        # ── ONE board rebuild for the whole batch ───────────────────────────
        #
        # Was inside `run`, so a batch rebuilt every cell once per claim-bearing
        # thread: 16.35s of a 21.70s thread against staging, and rising with the
        # board, which is quadratic in cells at any latency. Measured in
        # `docs/measurements/the-twenty-seconds-is-a-full-board-rebuild-per-thread.md`.
        #
        # ATTACHED TO THE LAST RESULT, and that is a compromise worth naming.
        # A whole-board rebuild is a BATCH event and belongs to no single thread,
        # but two readers want it through `results`: `close_the_night` below, and
        # `cli.py`'s `sum(len(r.cells) for r in results)`. Putting the outcomes
        # on one result keeps both totals right; per-result attribution is
        # meaningless afterwards and nothing reads it that way.
        #
        # This also fixes a quieter bug: `as_of_cells` below used to receive the
        # same cells once per claim-bearing thread - the whole board, duplicated
        # up to a thousand times - and now receives each cell once.
        if any(r.stored_claim_ids for r in results):
            outcomes = self._cells.rebuild_all(as_of=as_of)
            if results:
                results[-1].cells = outcomes

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
