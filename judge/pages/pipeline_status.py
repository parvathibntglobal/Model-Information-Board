"""Admin: the evidence pipeline, stage by stage.

Two questions, answered only from things that can be COUNTED:

1. WHAT IS IN EACH STAGE now — row counts grouped by the status column that
   partitions that stage's output (`document.status`, `cell.status`, …).
2. WHAT HAPPENED ON THE LAST RUN — the `job_run` ledger, one row per stage,
   carrying when it ran, whether it finished, and its outcome.

The rules this panel exists inside, and the exact shape each takes here:

- Rule 3 — nothing synthesised. Every figure is `COUNT(*) FILTER (…)` over a
  closed status vocabulary from `contract/tables.sql`. No score, no average, no
  ratio presented as a measurement.
- Rule 7 — a figure travels with its denominator. Each stage carries the
  population it counted (`unit`/`total`); a bucket without its total is not
  shown.
- Rule 4 — silence is not criticism. A stage with no rows renders as
  NOT-YET-RUN, never as an all-clear zero. `measured` is the flag that draws
  that line.
- Rule 6 — NULL is a third state, not `0`/`false`. `document.retrieval_provenance`
  three ways, `model_version.last_swept_at` NULL = never swept, `thread_context`
  coverage NULL = not measured: each gets its own bucket.

What this panel deliberately CANNOT show, and says so rather than implying zero:

- Attrition at extract and vet. A failed quote verification, a sarcastic claim,
  a promotional rejection are LOGGED and never written as rows —
  `CONSTRAINT claim_verified_ck CHECK (quote_verified = true)` forbids the row.
  So those stages show survivors and carry a caveat naming the discards they
  cannot count, instead of a green "0 dropped".

This lane reads `collect/`'s tables (`model_version`, `document`,
`thread_context`, `job_run`) exactly as `filtered.py` reads `document.status`
and `model.py` reads `model_version` — a SQL read across the boundary, never an
import. It writes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: The staleness bound from `contract/harvest.yaml` (rotation.staleness_bound_days).
#: A model swept longer ago than this has aged past the fast half-life, so E9
#: partitions the registry against it rather than against an arbitrary number.
STALENESS_BOUND_DAYS = 7


@dataclass(frozen=True)
class Bucket:
    """One counted slice of a stage's rows. `n` is a COUNT, never a rate."""

    key: str
    label: str
    n: int
    tone: str  # pass | warn | fail | mute — how the UI colours it, not a judgement


@dataclass(frozen=True)
class StageView:
    """One pipeline stage: what is in it, partitioned by a real status column."""

    id: str
    name: str
    lane: str
    flow: str  # "input → output.column", so a reader sees where the rows came from
    unit: str  # the denominator's noun: "documents", "threads", "cells"
    total: int
    buckets: tuple[Bucket, ...] = ()
    caveat: str | None = None
    unreadable: str | None = None  # this stage's query failed; the rest still render

    @property
    def measured(self) -> bool:
        """Did this stage produce any rows at all?

        `total == 0` is NOT-YET-RUN, which rule 4 says must render distinctly
        from a stage that ran and kept everything. The UI reads this flag to
        decide between a bar and a "not yet run" line.
        """
        return self.unreadable is None and self.total > 0


@dataclass(frozen=True)
class RunView:
    """The last `job_run` for one stage. The 'what happened' half.

    `finished_at IS NULL` is still-running-or-killed, NOT failed — `outcome`
    carries the failure and the two are kept apart (schema comment at job_run).
    """

    stage: str
    started_at: str | None
    finished_at: str | None
    outcome: str | None  # ok | refused | error | None(=running/killed)
    items_in: int | None
    items_out: int | None

    @property
    def running(self) -> bool:
        return self.finished_at is None and self.outcome is None


@dataclass(frozen=True)
class PipelineReport:
    summary: str
    pipeline_version: str | None
    stages: tuple[StageView, ...] = ()
    runs: tuple[RunView, ...] = ()
    runs_measured: bool = False
    caveats: tuple[str, ...] = field(default_factory=tuple)


def _one(conn: Any, sql: str) -> tuple:
    row = conn.execute(sql).fetchone()
    return row if row is not None else ()


class PipelineStatus:
    """Reads counts and the run ledger. Writes nothing."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def report(self) -> PipelineReport:
        stages = tuple(self._stage(spec) for spec in self._specs())
        runs, runs_measured = self._runs()
        version = self._latest_version()
        return PipelineReport(
            summary=self._summary(stages),
            pipeline_version=version,
            stages=stages,
            runs=runs,
            runs_measured=runs_measured,
            caveats=(
                "Extract and vet drop evidence that is never written as a row — a "
                "failed quote check, a sarcastic claim, a promotional rejection are "
                "logged, not stored. Those stages show survivors; the discards are "
                "not countable from the database, which is why no stage claims "
                "'0 dropped'.",
            ),
        )

    # ── per-stage counts ────────────────────────────────────────────────────

    def _stage(self, spec: dict) -> StageView:
        try:
            row = _one(self._conn, spec["sql"])
            buckets, total, caveat = spec["map"](row)
        except Exception as exc:  # one unreadable stage must not blank the rest
            return StageView(
                id=spec["id"], name=spec["name"], lane=spec["lane"],
                flow=spec["flow"], unit=spec["unit"], total=0,
                unreadable=str(exc).splitlines()[0][:200],
            )
        return StageView(
            id=spec["id"], name=spec["name"], lane=spec["lane"],
            flow=spec["flow"], unit=spec["unit"],
            total=total, buckets=tuple(buckets),
            # a discard/denominator caveat is noise on a stage that has not run
            caveat=caveat if total else None,
        )

    def _specs(self) -> list[dict]:
        b = Bucket
        return [
            {
                "id": "E1", "name": "Registry", "lane": "collect",
                "flow": "OpenRouter poll / seed → model_version", "unit": "models",
                "sql": """
                    SELECT count(*),
                      count(*) FILTER (WHERE in_window),
                      count(*) FILTER (WHERE NOT in_window),
                      count(*) FILTER (WHERE provenance = 'seed'),
                      count(*) FILTER (WHERE provenance = 'polled')
                    FROM model_version
                """,
                "map": lambda r: (
                    [
                        b("in_window", "in window", r[1], "pass"),
                        b("out_window", "out of window", r[2], "mute"),
                    ],
                    r[0],
                    (f"{r[3]} seeded, {r[4]} polled — seeded rows are refused outside "
                     "development." if r[3] else None),
                ),
            },
            {
                "id": "E2", "name": "Harvest", "lane": "collect",
                "flow": "registry + query set → document", "unit": "documents",
                "sql": """
                    SELECT count(*),
                      count(*) FILTER (WHERE retrieval_provenance = 'run_recorded'),
                      count(*) FILTER (WHERE retrieval_provenance = 'no_run_for_source'),
                      count(*) FILTER (WHERE retrieval_provenance = 'not_recorded')
                    FROM document
                """,
                "map": lambda r: (
                    [
                        b("run_recorded", "run recorded", r[1], "pass"),
                        b("no_run", "no run for source", r[2], "warn"),
                        b("not_recorded", "not recorded", r[3], "warn"),
                    ],
                    r[0],
                    ("'no run for source' and 'not recorded' are different findings, "
                     "not a shared gap — kept apart on purpose."),
                ),
            },
            {
                "id": "E3", "name": "Assemble", "lane": "collect",
                "flow": "document → thread_context (flattened)", "unit": "threads",
                "sql": """
                    SELECT count(*),
                      count(*) FILTER (WHERE observed_children IS NOT NULL),
                      count(*) FILTER (WHERE observed_children IS NULL)
                    FROM thread_context
                """,
                "map": lambda r: (
                    [
                        b("measured", "coverage measured", r[1], "pass"),
                        b("unmeasured", "coverage not measured", r[2], "mute"),
                    ],
                    r[0],
                    "coverage_ratio is an upper bound on what we saw, never a measurement.",
                ),
            },
            {
                "id": "E4", "name": "Triage", "lane": "collect",
                "flow": "document → document.status", "unit": "documents",
                "sql": """
                    SELECT count(*),
                      count(*) FILTER (WHERE status = 'kept'),
                      count(*) FILTER (WHERE status = 'filtered'),
                      count(*) FILTER (WHERE status = 'rejected'),
                      count(*) FILTER (WHERE status = 'tombstoned')
                    FROM document
                """,
                "map": lambda r: (
                    [
                        b("kept", "kept", r[1], "pass"),
                        b("filtered", "filtered", r[2], "warn"),
                        b("rejected", "rejected", r[3], "fail"),
                        b("tombstoned", "tombstoned", r[4], "mute"),
                    ],
                    r[0],
                    "Filtered content is stored, never deleted — see the Filtered panel.",
                ),
            },
            {
                "id": "E5", "name": "Extract (LLM)", "lane": "judge",
                "flow": "thread_context → claim", "unit": "threads",
                "sql": """
                    SELECT
                      (SELECT count(*) FROM thread_context),
                      (SELECT count(DISTINCT thread_context_id) FROM thread_extraction),
                      (SELECT count(*) FROM thread_extraction WHERE claims_written > 0),
                      (SELECT count(*) FROM thread_extraction WHERE claims_written = 0),
                      (SELECT coalesce(sum(claims_written), 0) FROM thread_extraction)
                """,
                "map": lambda r: (
                    [
                        b("productive", "read, claims found", r[2], "pass"),
                        b("empty", "read, nothing in it", r[3], "mute"),
                        b("unread", "not read yet", max(0, r[0] - r[1]), "warn"),
                    ],
                    r[0],
                    (f"{r[4]} claims written. 'read, nothing in it' is a finding, not "
                     "an absence. Failed verifications and sarcasm are discarded and "
                     "logged, never stored — this stage cannot count its own drops."),
                ),
            },
            {
                "id": "E6", "name": "Vet", "lane": "judge",
                "flow": "claim → claim_weight", "unit": "claims",
                "sql": """
                    SELECT
                      (SELECT count(*) FROM claim),
                      (SELECT count(*) FROM claim_weight)
                """,
                "map": lambda r: (
                    [
                        b("weighted", "weighted", r[1], "pass"),
                        b("unweighted", "not weighted", max(0, r[0] - r[1]), "mute"),
                    ],
                    r[0],
                    ("Promotional rejections are logged per run, not flagged on the row, "
                     "so 'not weighted' means awaiting weight OR rejected — the two are "
                     "not separable here."),
                ),
            },
            {
                "id": "E7", "name": "Curate", "lane": "judge",
                "flow": "claim + claim_weight → cell.status", "unit": "cells",
                "sql": """
                    SELECT count(*),
                      count(*) FILTER (WHERE status = 'published'),
                      count(*) FILTER (WHERE status = 'contested'),
                      count(*) FILTER (WHERE status = 'insufficient')
                    FROM cell
                """,
                "map": lambda r: (
                    [
                        b("published", "published", r[1], "pass"),
                        b("contested", "contested", r[2], "warn"),
                        b("insufficient", "insufficient", r[3], "mute"),
                    ],
                    r[0],
                    ("The answer path reads published + contested; insufficient stays "
                     "off the board."),
                ),
            },
            {
                "id": "E8", "name": "Publish", "lane": "judge",
                "flow": "cell → label_change", "unit": "label changes",
                "sql": """
                    SELECT count(*),
                      count(*) FILTER (WHERE direction = 'gained'),
                      count(*) FILTER (WHERE direction = 'lost')
                    FROM label_change
                """,
                "map": lambda r: (
                    [
                        b("gained", "gained", r[1], "pass"),
                        b("lost", "lost", r[2], "fail"),
                    ],
                    r[0],
                    "Whether a change was us or the world is in the Changelog panel.",
                ),
            },
            {
                "id": "E9", "name": "Stay current", "lane": "judge",
                "flow": "model_version.last_swept_at (decay & drift)", "unit": "models",
                "sql": f"""
                    SELECT count(*),
                      count(*) FILTER (
                        WHERE last_swept_at IS NOT NULL
                          AND last_swept_at >= now() - interval '{STALENESS_BOUND_DAYS} days'),
                      count(*) FILTER (
                        WHERE last_swept_at IS NOT NULL
                          AND last_swept_at <  now() - interval '{STALENESS_BOUND_DAYS} days'),
                      count(*) FILTER (WHERE last_swept_at IS NULL)
                    FROM model_version
                """,
                "map": lambda r: (
                    [
                        b("fresh", f"swept <= {STALENESS_BOUND_DAYS}d", r[1], "pass"),
                        b("stale", f"swept > {STALENESS_BOUND_DAYS}d", r[2], "warn"),
                        b("never", "never swept", r[3], "mute"),
                    ],
                    r[0],
                    (f"{STALENESS_BOUND_DAYS} days is the staleness bound from "
                     "contract/harvest.yaml. 'never swept' is not 'no problems found' — "
                     "it is a model nobody has looked at."),
                ),
            },
        ]

    # ── the run ledger ──────────────────────────────────────────────────────

    def _runs(self) -> tuple[tuple[RunView, ...], bool]:
        try:
            rows = self._conn.execute(
                """
                SELECT DISTINCT ON (stage)
                  stage, started_at, finished_at, outcome, items_in, items_out
                FROM job_run
                ORDER BY stage, started_at DESC
                """
            ).fetchall()
        except Exception:
            return (), False
        runs = tuple(
            RunView(
                stage=r[0],
                started_at=str(r[1]) if r[1] else None,
                finished_at=str(r[2]) if r[2] else None,
                outcome=r[3],
                items_in=r[4],
                items_out=r[5],
            )
            for r in rows
        )
        return runs, True

    def _latest_version(self) -> str | None:
        try:
            row = self._conn.execute(
                "SELECT pipeline_version FROM job_run ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        except Exception:
            return None
        return row[0] if row else None

    # ── summary ─────────────────────────────────────────────────────────────

    def _summary(self, stages: tuple[StageView, ...]) -> str:
        by_id = {s.id: s for s in stages}

        def bucket(stage_id: str, key: str) -> int | None:
            s = by_id.get(stage_id)
            if not s or not s.measured:
                return None
            for bk in s.buckets:
                if bk.key == key:
                    return bk.n
            return None

        docs = by_id["E2"].total if by_id.get("E2") and by_id["E2"].measured else None
        kept = bucket("E4", "kept")
        published = bucket("E7", "published")
        unrun = sum(1 for s in stages if not s.measured and s.unreadable is None)

        if docs is None:
            head = "No documents harvested yet — the pipeline has not run."
        else:
            parts = [f"{docs} documents harvested"]
            if kept is not None:
                parts.append(f"{kept} survived triage")
            if published is not None:
                parts.append(f"{published} cells published")
            head = "; ".join(parts) + "."
        if unrun:
            head += (
                f" {unrun} of {len(stages)} stages have no rows yet — not run, "
                "which is not the same as run-and-empty."
            )
        return head
