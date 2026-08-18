"""Write verified claims and their itemised weights, in one transaction.

TWO PROPERTIES, AND BOTH ARE LOAD-BEARING

**A claim and its weight arrive together or not at all.** They go in one
transaction because a claim without a weight is invisible to every count that
matters — it would sit in the table contributing to nothing, and the failure
would present weeks later as a cell that will not publish rather than as a
write that half-succeeded.

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
PIPELINE_VERSION = "e5.1"

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
    capability_key: str,
    quote_flat_offset: tuple[int, int],
    pipeline_version: str,
) -> str:
    """A deterministic id, so a re-run is an upsert rather than a second voice.

    The span is in the id because one comment can carry two claims about
    different capabilities, or the same capability at two points — and those
    are genuinely different claims. The pipeline version is in it because a
    re-extraction under a changed prompt IS a different claim about the same
    text, and collapsing the two would silently discard whichever ran second.
    """
    start, end = quote_flat_offset
    digest = hashlib.sha256(
        "\x1f".join(
            [
                thread_context_id,
                source_comment_id,
                capability_key,
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
    weights: WeightFactors
    document_id: str
    thread_context_id: str
    model_version_id: str
    condition_bucket: str
    evidence_tier: str
    claim_date: date
    author_id: str | None = None
    family: str | None = None
    taxonomy_version: str = "1.0"
    pipeline_version: str = PIPELINE_VERSION

    @property
    def id(self) -> str:
        return claim_id_for(
            thread_context_id=self.thread_context_id,
            source_comment_id=self.claim.source_comment_id,
            capability_key=self.claim.capability,
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
                extractor_confidence, pipeline_version
            ) VALUES (
                %(id)s, %(document_id)s, %(thread_context_id)s, %(source_comment_id)s,
                %(author_id)s, %(model_version_id)s, %(family)s, %(specificity)s,
                %(resolution_confidence)s, %(capability_key)s, %(taxonomy_version)s,
                %(condition_bucket)s, %(conditions)s, %(pain_points)s, %(polarity)s,
                %(severity)s, %(quote)s, %(quote_flat_offset)s, %(quote_raw_offset)s,
                true, %(relevance)s, %(has_repro_steps)s, %(has_numbers)s, false,
                %(evidence_tier)s, %(extractor_model)s, %(extractor_confidence)s,
                %(pipeline_version)s
            )
            ON CONFLICT (id) DO UPDATE SET
                quote = EXCLUDED.quote,
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
                "resolution_confidence": claim.model_ref.resolution_confidence,
                "capability_key": claim.capability,
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
                "extractor_model": os.getenv("EXTRACTOR_MODEL", "google/gemini-2.5-flash"),
                "extractor_confidence": claim.model_ref.resolution_confidence,
                "pipeline_version": stored.pipeline_version,
            },
        )

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
