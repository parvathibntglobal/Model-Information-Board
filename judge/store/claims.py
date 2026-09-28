"""Write verified claims and their itemised weights, in one transaction.

TWO PROPERTIES, AND BOTH ARE LOAD-BEARING

**A claim and its weight arrive together or not at all.** They go in one
transaction because a claim without a weight is invisible to every count that
matters — it would sit in the table contributing to nothing, and the failure
would present weeks later as a cell that will not publish rather than as a
write that half-succeeded.

⚠ SINCE 2026-09-22 THERE IS ONE DELIBERATE EXCEPTION, and it is the opposite
case rather than a hole in the rule. A claim whose `legacy_score_key` is empty
has no cell to be ranked within, so `StoredClaim.weights` is None and no
`claim_weight` row is written. That is not a half-succeeded write: it is
recorded, intended, and `write()` returns at a named early exit rather than
falling through. What the original property protects against is a weight that
was *supposed* to exist and did not — a claim with no key was supposed to be
dropped entirely, and used to be, which is what made 1,385 claims carry a key
that named the wrong thing in roughly two of three cases. See `StoredClaim.weights`.

**Re-running extraction over the same thread does not duplicate anything.**
The id is derived from what the claim IS, not from when it was written, so a
re-run under the same `pipeline_version` writes the same rows. This is not an
optimisation: `n_eff` counts weight, so a duplicated claim is a second voice
that never existed, and a gate crossed by re-running a batch is the worst
failure this table could have.

WHAT THE SCHEMA GUARANTEES THAT THIS MODULE DOES NOT HAVE TO

    CONSTRAINT claim_verified_ck CHECK (quote_verified = true)

The database refuses an unverified claim. So rule 1 is not a convention this
module is trusted to honour — an INSERT that tried would fail, and a future
caller that forgets cannot quietly succeed. The check exists because a
guarantee enforced only in the code that happens to write today is a guarantee
for exactly as long as nobody adds a second writer.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Any

import psycopg
from psycopg.types.json import Json
from psycopg.types.range import Range

from judge.extract.schema import ExtractedClaim
from judge.extract.verify import VerifiedQuote
from judge.vet.weight import WeightFactors

#: Bumped whenever anything that produces a claim changes — the prompt, the
#: extractor model, the verification, the weighting. Every derived row carries
#: it so a scoring change is re-runnable and diffable rather than archaeology.
#:
#: TWO RULINGS LANDED ON 2026-08-30 AND THEY GET TWO VERSIONS, NOT ONE.
#: Both are weighting changes, so `judge reweight` produces both from stored
#: inputs and no model is called for either. They are separated because a diff
#: with two causes measures neither.
#:
#:   e5.1 -> e5.2   `evidence_tier` keys on (speaking, has_repro_steps,
#:                  has_numbers) instead of `speaking` alone —
#:                  contract/harvest.yaml `evidence_tier_rules`. ONLY
#:                  `f_evidence` moves; `judge reweight --document-facts frozen`
#:                  holds the document booleans at the values e5.1 effectively
#:                  used, and the drift check proves it held them.
#:
#:   e5.2 -> e5.3   `compute()` refuses `None`, and `_document_facts` reads
#:                  `document.has_numbers` / `has_conditions` instead of passing
#:                  a literal `None` that the refusal did not catch. ONLY
#:                  `f_specificity` moves, plus refusals where the columns are
#:                  NULL. `judge reweight --document-facts read`.
#:
#:   e5.3 -> e5.4   Option 1 of the double-count proposal, taken on E1's
#:                  instruction: `has_numbers` and `has_repro_steps` leave
#:                  `specificity_factor` because `evidence_tier_rules` now
#:                  prices them. ONLY `f_specificity` moves.
#:                  `judge reweight --specificity current`.
#:
#:   e5.4 -> e5.5   `legacy_score_key` (was `capability`) became OPTIONAL and
#:                  the prompt stopped asking for the closest key. NOT a
#:                  weighting change and NOT reproducible by `judge reweight`:
#:                  it changes what the EXTRACTOR emits, so the only way to
#:                  produce e5.5 rows is to pay for extraction again.
#:
#:                  ⚠ THE FORK IS THE POINT AND IT IS NOT FREE. A claim whose
#:                  key goes from `extraction.faithfulness` to empty hashes to
#:                  a different id, so a re-run ADDS a row beside the e5.4 one
#:                  rather than correcting it - which is exactly what a version
#:                  fork is for (the old rows stay for the diff) and is also
#:                  why nothing here backfills. The e5.4 rows keep their wrong
#:                  keys; `CellStore` filters on this constant, so they stop
#:                  reaching cells the moment the constant moves.
#:                  `docs/measurements/the-key-that-takes-anything-2026-09-22.md`
#:
#: A plain `judge extract` writes e5.5. e5.2 and e5.3 exist only as the
#: intermediates each diff is measured against, which is what a version-stamped
#: fork is for - and each is reproducible from the one before it with no model
#: call, which is what makes three forks cheap rather than three runs.
#:
#: ⚠ THE VERSION IS IN `claim_id_for`, SO A BUMP FORKS THE TABLE RATHER THAN
#:   UPDATING IT. That is the point — the e5.1 rows stay for the diff — and it
#:   is also why `CellStore` filters on this constant. Before the bump the table
#:   held one version and no aggregation needed to say which; after it, an
#:   unfiltered `n_eff` would take each voice's best weight across BOTH versions
#:   and quietly report a mixture that is neither.
PIPELINE_VERSION = "e5.5"

CONNECT_TIMEOUT_SECONDS = 10


class DatabaseNotConfigured(RuntimeError):
    """No DSN. Raised rather than defaulted to localhost.

    A default that quietly connects somewhere is how a test suite writes to a
    real database once.
    """


def claim_id_for(
    *,
    thread_context_id: str,
    source_comment_id: str,
    capability_key: str | None,
    quote_flat_offset: tuple[int, int],
    pipeline_version: str,
) -> str:
    """A deterministic id, so a re-run is an upsert rather than a second voice.

    The span is in the id because one comment can carry two claims about
    different capabilities, or the same capability at two points — and those
    are genuinely different claims. The pipeline version is in it because a
    re-extraction under a changed prompt IS a different claim about the same
    text, and collapsing the two would silently discard whichever ran second.

    ⚠ SO A DELETE IS PERMANENT FOR THIS PIPELINE VERSION, AND "RE-RUN TO
    RESTORE" DOES NOT RESTORE.

    "A re-run is an upsert" is true only if the extractor picks the IDENTICAL
    span, and the extractor is nondeterministic — the same document has produced
    8, 28 and 36 claims across three runs, and a quote chosen one sentence longer
    hashes to a different id. So re-extraction after a delete produces a
    DIFFERENT row, not the same row again: same document, same capability,
    different id, and the deleted claim's id never recurs.

    That makes the determinism here a property of the INPUTS rather than a
    guarantee about re-runs, and the difference matters at exactly one moment:
    when somebody deletes a row believing it is recoverable. It is not. Six
    claims were deleted on 2026-08-21 for a defect that turned out to be in the
    measurement of them, and re-extraction restored equivalents rather than
    them.
    """
    start, end = quote_flat_offset
    # `capability_key` is OPTIONAL since 2026-09-22 and None hashes as the empty
    # string. Deliberately NOT a sentinel word: a literal like "none" could
    # collide with a future ratified key, and the separator is already \x1f so
    # an empty field is unambiguous in the joined digest.
    digest = hashlib.sha256(
        "\x1f".join(
            [
                thread_context_id,
                source_comment_id,
                capability_key or "",
                f"{start}:{end}",
                pipeline_version,
            ]
        ).encode("utf-8")
    ).hexdigest()
    return f"clm_{digest[:24]}"


@dataclass(frozen=True)
class StoredClaim:
    """One claim as it will be written. Assembled before any SQL runs.

    Built as a value rather than passed around as arguments so the caller can
    inspect what is about to be written — and so the id is computed once,
    where it can be asserted on, rather than inside an INSERT.
    """

    claim: ExtractedClaim
    quote: VerifiedQuote
    #: None when the claim carries no ratified `legacy_score_key`.
    #:
    #: ⚠ NOT A ZERO AND NOT A DEFAULT (rule 6). Every one of the seven factors
    #: exists to rank a claim WITHIN a cell, and a claim with no key has no
    #: cell — so there is nothing for a weight to order it against. Writing one
    #: anyway would mean picking a recency half-life, and `half_life_for`
    #: returns the SLOW default for any key it does not recognise: the most
    #: generous decay there is, handed to the claims we know least about, by a
    #: fallback that cannot fail. Rule 12.
    #:
    #: A number with no consumer is rule 9's defect, so the honest record is no
    #: row in `claim_weight` at all. The claim, its quote and its board entries
    #: are all still written.
    weights: WeightFactors | None
    document_id: str
    thread_context_id: str
    model_version_id: str
    condition_bucket: str
    evidence_tier: str
    claim_date: date
    #: The model that ACTUALLY ran, from the completion, not from the
    #: environment. It was `os.getenv("EXTRACTOR_MODEL", "...flash")` on a
    #: NOT NULL provenance column, so an unset variable wrote a confident
    #: guess into the one field whose job is to say what produced the row.
    #: Rule 6, on a provenance column, which is the worst place for it.
    extractor_model: str
    author_id: str | None = None
    family: str | None = None
    taxonomy_version: str = "1.0"
    pipeline_version: str = PIPELINE_VERSION

    @property
    def id(self) -> str:
        return claim_id_for(
            thread_context_id=self.thread_context_id,
            source_comment_id=self.claim.source_comment_id,
            capability_key=self.claim.legacy_score_key,
            quote_flat_offset=self.claim.quote_offset,
            pipeline_version=self.pipeline_version,
        )


@contextmanager
def transaction(dsn: str | None = None):
    """One connection, one transaction, committed or rolled back whole."""
    url = dsn or os.getenv("DATABASE_URL")
    if not url:
        raise DatabaseNotConfigured(
            "DATABASE_URL is unset. Refusing to guess at a connection: a default "
            "that quietly reaches localhost is how a suite writes to a real "
            "database once."
        )
    with (
        psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT_SECONDS) as conn,
        conn.transaction(),
    ):
        yield conn


class ClaimStore:
    """Writes `claim` and `claim_weight`. Reads nothing it does not write."""

    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        self._conn = conn

    def _ratified_or_none(self, key: str | None) -> str | None:
        """A key from `contract/capabilities.yaml`, or None when none fits.

        NULLABILITY ALONE DOES NOT FIX THE FK. `capability_key` became nullable
        on 2026-09-10 so the board's discovered vocabulary would stop being
        gated behind the ratified twelve - but a NON-NULL key that is not in
        `capability` still violates the foreign key, which is precisely how the
        2026-09-10 fetch died: `insert or update on table "claim" violates
        foreign key constraint "claim_capability_key_fkey"`.

        So a key this vocabulary does not contain is recorded as NULL. That is
        not data loss: the classifier's proposal is already on its way to
        `capability_candidate` through `proposed_capabilities`, where a person
        rules on it. What NULL says is "no ratified key fits", which is true and
        is the honest alternative to picking a neighbour.

        Read from the contract rather than the database on purpose. The file is
        the vocabulary; a table that has not been loaded is an empty table, and
        coercing every key to NULL because nobody ran the loader would hide a
        setup mistake as a modelling outcome.
        """
        if not key:
            return None
        from judge.config import capabilities

        return key if key in capabilities() else None

    def write(self, stored: StoredClaim) -> str:
        """One claim and its weight. Returns the id.

        Idempotent by id: a second write of the same claim updates it in place
        rather than adding a voice. `quote_verified` is hard-coded true because
        a `StoredClaim` cannot be constructed without a `VerifiedQuote`, and
        the schema's CHECK refuses the row if that ever stops being so.
        """
        claim = stored.claim
        start, end = claim.quote_offset

        self._conn.execute(
            """
            INSERT INTO claim (
                id, document_id, thread_context_id, source_comment_id, author_id,
                model_version_id, family, specificity, resolution_confidence,
                capability_key, taxonomy_version, condition_bucket, conditions,
                pain_points, polarity, severity, quote, quote_flat_offset,
                quote_raw_offset, quote_verified, relevance, has_repro_steps,
                has_numbers, is_sarcastic, evidence_tier, extractor_model,
                extractor_confidence, pipeline_version, speaking
            ) VALUES (
                %(id)s, %(document_id)s, %(thread_context_id)s, %(source_comment_id)s,
                %(author_id)s, %(model_version_id)s, %(family)s, %(specificity)s,
                %(resolution_confidence)s, %(capability_key)s, %(taxonomy_version)s,
                %(condition_bucket)s, %(conditions)s, %(pain_points)s, %(polarity)s,
                %(severity)s, %(quote)s, %(quote_flat_offset)s, %(quote_raw_offset)s,
                true, %(relevance)s, %(has_repro_steps)s, %(has_numbers)s, false,
                %(evidence_tier)s, %(extractor_model)s, %(extractor_confidence)s,
                %(pipeline_version)s, %(speaking)s
            )
            -- The offsets are updated with the quote. They cannot currently
            -- diverge, because claim_id_for hashes the offset so a changed span
            -- gets a different id and never conflicts - but that is the id
            -- function protecting the upsert, not the upsert protecting itself.
            -- Change the id inputs and the row silently keeps offsets pointing
            -- at the previous span. Safe by construction beats safe by accident.
            ON CONFLICT (id) DO UPDATE SET
                quote = EXCLUDED.quote,
                quote_flat_offset = EXCLUDED.quote_flat_offset,
                quote_raw_offset = EXCLUDED.quote_raw_offset,
                condition_bucket = EXCLUDED.condition_bucket,
                conditions = EXCLUDED.conditions,
                polarity = EXCLUDED.polarity,
                severity = EXCLUDED.severity
            """,
            {
                "id": stored.id,
                "document_id": stored.document_id,
                "thread_context_id": stored.thread_context_id,
                "source_comment_id": claim.source_comment_id,
                "author_id": stored.author_id,
                "model_version_id": stored.model_version_id,
                "family": stored.family,
                "specificity": claim.model_ref.specificity,
                # STORED THOUGH IT ONLY AFFECTS WEIGHTING. The field has never
                # run, so a mislabelling has to be recoverable - see the
                # migration 20260821T1600_claim_speaking.sql.
                "speaking": claim.model_ref.speaking,
                "resolution_confidence": claim.model_ref.resolution_confidence,
                "capability_key": self._ratified_or_none(claim.legacy_score_key),
                "taxonomy_version": stored.taxonomy_version,
                "condition_bucket": stored.condition_bucket,
                "conditions": Json(claim.conditions.model_dump(exclude_none=True)),
                "pain_points": list(claim.pain_points),
                "polarity": claim.polarity,
                "severity": claim.severity,
                # The RAW span, not the flattened one. `[upside_down_face]` is
                # an internal representation and must never reach a page.
                "quote": stored.quote.display_text,
                # int4range, not an array. Passing [start, end] sends a
                # smallint[] and Postgres refuses the cast - which CI caught and
                # nothing local could have, because the column type only exists
                # in the database.
                #
                # '[)' is the schema's half-open convention, the same one the
                # offset map uses. A closed upper bound here would silently
                # include one character more than the quote.
                "quote_flat_offset": Range(start, end, "[)"),
                "quote_raw_offset": Range(*stored.quote.raw_offset, "[)"),
                "relevance": claim.relevance,
                "has_repro_steps": claim.has_repro_steps,
                "has_numbers": claim.has_numbers,
                "evidence_tier": stored.evidence_tier,
                "extractor_model": stored.extractor_model,
                "extractor_confidence": claim.model_ref.resolution_confidence,
                "pipeline_version": stored.pipeline_version,
            },
        )

        # NO KEY, NO WEIGHT, AND THE CLAIM IS STILL WRITTEN. Returning before
        # `claim_weight` rather than writing zeros: see `StoredClaim.weights`.
        # The row above is already committed to this transaction, which is the
        # whole point - a claim the legacy scorer cannot rank is still evidence
        # and still reaches the board.
        if stored.weights is None:
            return stored.id

        # as_row() is the seven factors plus w_final, which is their product
        # and a property rather than a field. Using it here means the row and
        # the drill-down cannot disagree about what w_final was.
        weights = stored.weights.as_row()
        self._conn.execute(
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
            {
                "claim_id": stored.id,
                "w_final": weights["w_final"],
                "f_evidence": weights["f_evidence"],
                "f_platform": weights["f_platform"],
                "f_specificity": weights["f_specificity"],
                "f_relevance": weights["f_relevance"],
                "f_recency": weights["f_recency"],
                "f_launch": weights["f_launch"],
                "f_fuzziness": weights["f_fuzziness"],
                "pipeline_version": stored.pipeline_version,
            },
        )
        return stored.id

    def write_all(self, claims: Iterable[StoredClaim]) -> list[str]:
        """A thread's worth. One transaction is the caller's to open."""
        return [self.write(c) for c in claims]

    def count_for_thread(self, thread_context_id: str) -> int:
        row = self._conn.execute(
            "SELECT count(*) FROM claim WHERE thread_context_id = %s",
            (thread_context_id,),
        ).fetchone()
        return int(row[0]) if row else 0

    def weights_for(self, claim_id: str) -> dict[str, float] | None:
        """The itemised factors, for "why does this page say that?".

        FR-19 wants them individually rather than as a product, because a
        single number cannot answer that question and inviting somebody to
        average it later is the failure rule 3 forbids.
        """
        row = self._conn.execute(
            """
            SELECT w_final, f_evidence, f_platform, f_specificity,
                   f_relevance, f_recency, f_launch, f_fuzziness
            FROM claim_weight WHERE claim_id = %s
            """,
            (claim_id,),
        ).fetchone()
        if row is None:
            return None
        names = (
            "w_final",
            "f_evidence",
            "f_platform",
            "f_specificity",
            "f_relevance",
            "f_recency",
            "f_launch",
            "f_fuzziness",
        )
        return dict(zip(names, (float(v) for v in row), strict=True))
