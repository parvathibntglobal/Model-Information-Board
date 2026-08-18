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

from dataclasses import dataclass
from typing import Any

from judge.store.claims import PIPELINE_VERSION


@dataclass(frozen=True)
class ExtractionRecord:
    """One thread, read once, at one pipeline version."""

    thread_context_id: str
    claims_written: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    schema_retries: int = 0

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

    def already_extracted(self, *, pipeline_version: str = PIPELINE_VERSION) -> frozenset[str]:
        """Every thread read at this version, INCLUDING the ones that yielded nothing.

        Scoped to one version deliberately. A re-extraction under a changed
        prompt is new work on old text, so a version bump must re-read
        everything rather than skip it - the same reason `claim_id` hashes the
        version.
        """
        rows = self._conn.execute(
            "SELECT thread_context_id FROM thread_extraction WHERE pipeline_version = %s",
            (pipeline_version,),
        ).fetchall()
        return frozenset(r[0] for r in rows)

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
                input_tokens, output_tokens, schema_retries
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (thread_context_id, pipeline_version) DO UPDATE SET
                claims_written = EXCLUDED.claims_written,
                input_tokens   = EXCLUDED.input_tokens,
                output_tokens  = EXCLUDED.output_tokens,
                schema_retries = EXCLUDED.schema_retries,
                extracted_at   = now()
            """,
            (
                record.thread_context_id,
                pipeline_version,
                record.claims_written,
                record.input_tokens,
                record.output_tokens,
                record.schema_retries,
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
