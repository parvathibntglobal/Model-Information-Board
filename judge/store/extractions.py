"""The extraction ledger: that a thread was read, apart from what it said.

WHAT THIS EXISTS TO MAKE SAYABLE

    row absent          nobody has read this thread     -> a job
    claims_written = 0  we read it and found nothing    -> a finding

`claim` can only express the first two thirds of that. A thread that yielded
nothing has no row there and is indistinguishable from one nobody has touched,
so a nightly batch re-extracts it every night forever - and those are exactly
the threads that cost the most and return the least. At $0.00164 a thread that
is 96% of the monthly bill buying rows that already exist.

Rule 6, landing on the one signal the whole saving depends on.

WRITTEN IN THE SAME TRANSACTION AS THE CLAIMS

A ledger row that commits while the claims roll back would mark a thread read
that produced nothing readable, and the next run would skip it - evidence lost
silently and permanently, which is the worst failure available here. So
`record` takes the caller's connection and never commits: it is one statement
inside whatever transaction wrote the claims, exactly as `ClaimStore.write`
keeps a claim and its weight together.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from judge.store.claims import PIPELINE_VERSION


def fingerprint_of(flattened_text: str) -> str:
    """What was read, because `thread_context.id` does not say.

    `stable_id("thread_context", root_id, version)` ignores content, so a
    thread re-assembled with different children keeps its id. E1 found it
    through `specificity.py` changing the child scorer while PIPELINE_VERSION
    stayed put - the path the "over-identifies, never under-identifies"
    proviso does not cover, because it is about the scorer rather than the
    flattener.

    Hashing the flattened text is the narrowest thing that is actually true:
    these are the exact bytes the extractor was given, so a match means
    re-running would send the same prompt.
    """
    return hashlib.sha256(flattened_text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExtractionRecord:
    """One thread, read once, at one pipeline version."""

    thread_context_id: str
    claims_written: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    schema_retries: int = 0

    #: sha256 of the flattened text this run was given. See `fingerprint_of`.
    content_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if self.claims_written < 0:
            raise ValueError(
                f"claims_written={self.claims_written}: a count cannot be negative, "
                f"and 0 already means 'read it, found nothing'"
            )


class ExtractionLedger:
    """Reads and writes `thread_extraction`. Nothing else."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def already_extracted(
        self, *, pipeline_version: str = PIPELINE_VERSION
    ) -> dict[str, str | None]:
        """Threads read at this version, mapped to WHAT was read.

        Returns `{thread_context_id: content_fingerprint}` rather than a set of
        ids, because the id alone does not identify the text. A NULL
        fingerprint - a row written before the column existed - maps to None,
        and `should_skip` treats None as "unknown, re-read it" rather than as a
        match. Rule 6: not measured is not the same as measured and equal.

        Scoped to one version deliberately. A re-extraction under a changed
        prompt is new work on old text, so a version bump must re-read
        everything - the same reason `claim_id` hashes the version.
        """
        rows = self._conn.execute(
            "SELECT thread_context_id, content_fingerprint FROM thread_extraction "
            "WHERE pipeline_version = %s",
            (pipeline_version,),
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    @staticmethod
    def should_skip(
        seen: dict[str, str | None], thread_context_id: str, flattened_text: str
    ) -> bool:
        """Skip only when we read THIS thread AND this text.

        Three states, and only the first is a skip:

            id present, fingerprint matches   we have read exactly this
            id present, fingerprint differs   the children changed under a
                                              stable id - RE-READ
            id present, fingerprint is NULL   written before the column - we
                                              do not know - RE-READ

        The second is the case E1 found and the one that costs most to get
        wrong: skipping it means evidence silently never extracted, which is
        worse than paying for a thread twice.
        """
        if thread_context_id not in seen:
            return False
        recorded = seen[thread_context_id]
        if recorded is None:
            return False
        return recorded == fingerprint_of(flattened_text)

    def record(self, record: ExtractionRecord, *, pipeline_version: str = PIPELINE_VERSION) -> None:
        """One row. Does not commit - see the module docstring.

        Upsert rather than insert, because a re-run at the same version after a
        crash must not fail on the primary key. The counts are REPLACED rather
        than added: the second read is the one that happened, and summing would
        invent a thread that produced twice what it did.
        """
        self._conn.execute(
            """
            INSERT INTO thread_extraction (
                thread_context_id, pipeline_version, claims_written,
                input_tokens, output_tokens, schema_retries, content_fingerprint
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (thread_context_id, pipeline_version) DO UPDATE SET
                claims_written = EXCLUDED.claims_written,
                input_tokens   = EXCLUDED.input_tokens,
                output_tokens  = EXCLUDED.output_tokens,
                schema_retries = EXCLUDED.schema_retries,
                content_fingerprint = EXCLUDED.content_fingerprint,
                extracted_at   = now()
            """,
            (
                record.thread_context_id,
                pipeline_version,
                record.claims_written,
                record.input_tokens,
                record.output_tokens,
                record.schema_retries,
                record.content_fingerprint,
            ),
        )

    def yield_rate(self, *, pipeline_version: str = PIPELINE_VERSION) -> tuple[int, int]:
        """`(threads that produced nothing, threads read)` - the figure with its
        denominator (rule 7).

        This is the number nobody has: how much the skip is actually worth
        depends entirely on the zero-yield rate, and until a run happens it is
        unmeasured. Returned as a pair rather than a percentage so a caller
        cannot quote a rate without the population it came from.
        """
        row = self._conn.execute(
            "SELECT count(*) FILTER (WHERE claims_written = 0), count(*) "
            "FROM thread_extraction WHERE pipeline_version = %s",
            (pipeline_version,),
        ).fetchone()
        return (int(row[0]), int(row[1])) if row else (0, 0)

    def token_totals(self, *, pipeline_version: str = PIPELINE_VERSION) -> tuple[int, int, int]:
        """`(input, output, threads that reported neither)`.

        The third number is not decoration. A provider that stops reporting
        usage makes the totals a floor rather than a measurement, and the
        symptom is a low number that reads as good news - the same reason
        `Budget` counts unmetered calls.
        """
        row = self._conn.execute(
            "SELECT coalesce(sum(input_tokens), 0), coalesce(sum(output_tokens), 0), "
            "count(*) FILTER (WHERE input_tokens IS NULL AND output_tokens IS NULL) "
            "FROM thread_extraction WHERE pipeline_version = %s",
            (pipeline_version,),
        ).fetchone()
        return (int(row[0]), int(row[1]), int(row[2])) if row else (0, 0, 0)
