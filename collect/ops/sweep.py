"""The GitHub sweep as a stage: plans from the database, records what it did.

`chain.py` has carried `Stage("sweep-github", run=None, …)` since `ops/` was
built, and its own `starves=` text names what was missing: *"the harvester and
`write_documents` exist; what does not is the stage that plans the queries and
writes `harvest_run`."* This is that stage.

THREE GAPS IT CLOSES, AND THEY WERE SEPARATE
--------------------------------------------
**1 · Query planning reads `model_alias`.** `scripts/harvest_github.py` builds its
query strings with `alias_rows(next(m for m in seed_models() …))` — computed in
memory from the build fixture — so it can sweep one of eleven models and no
amount of seating changes what it does. The 105 rows the tracked-set loader wrote
had no reader. Now the plan comes from the table, which means seating a model is
what puts it in a sweep.

**2 · `harvest_run` gets a caller.** Three adapters build `harvest_run_fields()`,
`ops/ledger.py` writes it, and until now *nothing called both* — `ledger.py`
said so in its own comment and `alerts.py` repeated it. The foreign key was
proven satisfiable inside a rolled-back transaction and never exercised by a run.

**3 · The budget binds.** `contract/harvest.yaml` sets `max_requests: 900`, a
figure computed against eleven models. At 41 seated models the daily plan is
2,176 requests, so a sweep that ignored the cap would exceed a contract number by
2.4×. This stops at the cap and **names the models it did not reach** — a silent
truncation reads as "we swept everything", which is rule 4 at the point where
nobody is looking.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
No `apply_schema`, and no disposability assertion. `scripts/harvest_github.py`
carries both because it is a local harness that builds its own schema, and its
`assert_safe_target` guard exists for `DROP SCHEMA public CASCADE`. This stage
issues `INSERT`s and an `UPDATE` to a row it opened, destroys nothing, and takes
the connection the chain hands it — so importing that guard here would refuse
every real database while protecting nothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

#: Where the cap comes from. Read, never defaulted: a budget the code invents is
#: not a budget the contract set.
_HARVEST_CONTRACT = "contract/harvest.yaml"


@dataclass
class ModelSweep:
    """One model's share of a sweep."""

    canonical_id: str
    variants: tuple[str, ...]
    requests: int = 0
    candidates: int = 0
    kept: int = 0
    stored: int = 0
    harvest_runs: int = 0


@dataclass
class SweepReport:
    """What the sweep issued, kept, wrote and recorded — and what it skipped.

    `unreached` is the load-bearing field. A sweep that stops at a budget and
    reports only what it did looks identical to a sweep that covered the whole
    population, which is the shape this project has now met in four places.
    """

    models: list[ModelSweep] = field(default_factory=list)
    unreached: list[str] = field(default_factory=list)
    requests_planned: int = 0
    requests_issued: int = 0
    candidates: int = 0
    group_hits: dict[str, int] = field(default_factory=dict)
    kept: int = 0
    stored: int = 0
    harvest_runs_opened: int = 0
    harvest_runs_closed: int = 0

    #: Ledger writes that failed, with the reason. A ledger failure must not fail
    #: the sweep it describes — `chain.py` settled that — but it must not be a log
    #: line either. The first real sweep opened 121 rows, closed none, and
    #: reported success, because the failure lived in `log.warning` and the report
    #: counted only what worked.
    ledger_failures: list[str] = field(default_factory=list)
    http_errors: int = 0
    rate_limited: int = 0
    cap: int = 0

    @property
    def sieve_rates(self) -> dict[str, float]:
        """Per-group pass rate, over candidates seen. Empty when nothing was seen.

        Rule 7: the denominator is `candidates`, and a rate with no candidates is
        absent rather than 0.0 — zero-of-zero and zero-of-many are different
        findings and only one of them is about the sieve.
        """
        if not self.candidates:
            return {}
        return {
            group: hits / self.candidates for group, hits in sorted(self.group_hits.items())
        }

    def summary(self) -> str:
        lines = [
            f"sweep    : {len(self.models)} model(s) swept, "
            f"{len(self.unreached)} unreached, "
            f"{self.requests_issued} of {self.requests_planned} planned request(s) "
            f"issued against a cap of {self.cap}",
            f"           {self.candidates} candidate(s), {self.kept} kept, "
            f"{self.stored} document(s) stored",
            f"           harvest_run: {self.harvest_runs_opened} opened, "
            f"{self.harvest_runs_closed} closed",
        ]
        if self.candidates:
            rates = "  ".join(
                f"{group} {hits}/{self.candidates} ({hits / self.candidates:.1%})"
                for group, hits in sorted(self.group_hits.items())
            )
            lines.append(f"           sieve: {rates}")
        else:
            lines.append(
                "           sieve: no candidates retrieved, so there are no rates — "
                "not 0%, which would say the sieve rejected them"
            )
        if self.ledger_failures:
            lines.append(
                f"LEDGER   : {len(self.ledger_failures)} harvest_run write(s) failed — "
                f"{self.ledger_failures[0]}"
                + (f" (+{len(self.ledger_failures) - 1} more)"
                   if len(self.ledger_failures) > 1 else "")
                + ". An unclosed row reads as `started and never came back`, so a "
                  "failed close makes a completed query indistinguishable from a "
                  "killed one."
            )
        if self.unreached:
            lines.append(
                f"UNREACHED: {len(self.unreached)} seated model(s) the budget did not "
                f"cover: {', '.join(self.unreached[:8])}"
                + ("…" if len(self.unreached) > 8 else "")
            )
        return "\n".join(lines)


def seated_variants(conn) -> dict[str, tuple[str, ...]]:
    """Every search string in `model_alias`, per model. The reader that was missing.

    `search_eligible` is not a column — it is expressed as a non-empty
    `variants` array, which is what `alias_rows` writes and what
    `search_queries()` filters on. So the query says so rather than inventing a
    predicate.
    """
    rows = conn.execute(
        "SELECT mv.canonical_id, array_agg(DISTINCT v) "
        "FROM model_alias a "
        "JOIN model_version mv ON mv.id = a.model_version_id, "
        "     unnest(a.variants) v "
        "WHERE a.valid_until IS NULL "
        "GROUP BY mv.canonical_id "
        "ORDER BY mv.canonical_id"
    ).fetchall()
    return {row[0]: tuple(sorted(row[1])) for row in rows}


def request_cap(path: str | None = None) -> int:
    """The cap from `contract/harvest.yaml`. Refuses rather than defaulting."""
    from pathlib import Path

    import yaml

    from collect.config import REPO_ROOT

    target = Path(path) if path else REPO_ROOT / _HARVEST_CONTRACT
    raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}

    def find(node: Any) -> int | None:
        if isinstance(node, dict):
            if "max_requests" in node:
                return int(node["max_requests"])
            for value in node.values():
                found = find(value)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for value in node:
                found = find(value)
                if found is not None:
                    return found
        return None

    cap = find(raw)
    if cap is None:
        raise RuntimeError(
            f"no `max_requests` in {target}. A sweep without a budget the contract "
            f"set is a sweep with a budget this code invented, and the whole point "
            f"of the cap is that it is not ours to choose."
        )
    return cap


def sweep_github(
    conn,
    harvester,
    *,
    entries,
    scope: tuple[str, ...] = (),
    cap: int | None = None,
    source_id: str = "github",
) -> SweepReport:
    """Sweep every seated model until the budget runs out, recording each query.

    TWO PHASES PER QUERY, not per sweep. `open_harvest_run` writes the row before
    the fetch and `close_harvest_run` fills it in afterwards, so a process killed
    mid-query leaves `finished_at IS NULL` — the only carrier of "started and
    never came back". Committed per query for the same reason: a run held open in
    one transaction and rolled back would take every record of the night with it.
    """
    from collect.adapters.github import QueryRun
    from collect.adapters.queries import plan_searches
    from collect.ops.ledger import close_harvest_run, open_harvest_run

    cap = request_cap() if cap is None else cap
    report = SweepReport(cap=cap)

    by_model = seated_variants(conn)
    if not by_model:
        raise RuntimeError(
            "no rows in `model_alias`, so there is nothing to search for. "
            "A sweep over an empty alias table retrieves nothing and would report "
            "it as nobody discussing anything — run `registry load-tracked-set`."
        )

    plans = {
        canonical_id: plan_searches(entries, list(variants), scope=scope)
        for canonical_id, variants in by_model.items()
    }
    report.requests_planned = sum(p.request_count for p in plans.values())

    for canonical_id, variants in by_model.items():
        plan = plans[canonical_id]
        if report.requests_issued + plan.request_count > cap:
            report.unreached.append(canonical_id)
            continue

        seat = ModelSweep(canonical_id=canonical_id, variants=variants)
        for request in plan.requests:
            # The row exists before the first HTTP call. See the docstring.
            run = QueryRun(request=request)
            fields = harvester.harvest_run_fields(run)
            opened = None
            try:
                opened = open_harvest_run(conn, {**fields, "source_id": source_id})
                conn.commit()
                report.harvest_runs_opened += 1
            except Exception as error:  # noqa: BLE001
                log.warning("harvest_run could not be opened for %s: %s",
                            request.query_key, error)
                report.ledger_failures.append(
                    f"open {request.query_key}: {type(error).__name__}: {error}"
                )
                conn.rollback()

            harvester.harvest(request, run=run)
            wrote = harvester.write_documents(conn, run)
            conn.commit()

            seat.requests += 1
            report.requests_issued += 1
            yields = run.sieve_yield
            seat.candidates += yields.candidates
            seat.kept += yields.kept
            seat.stored += wrote["inserted"]
            report.http_errors += run.http_errors

            for verdict in run.verdicts:
                for group in ("subject", "topic", "signal"):
                    if getattr(verdict, group):
                        report.group_hits[group] = report.group_hits.get(group, 0) + 1

            if opened is not None:
                try:
                    close_harvest_run(
                        conn, opened,
                        {**harvester.harvest_run_fields(run), "source_id": source_id},
                        outcome=harvester.outcome_of(run),
                    )
                    conn.commit()
                    report.harvest_runs_closed += 1
                    seat.harvest_runs += 1
                except Exception as error:  # noqa: BLE001
                    log.warning("harvest_run could not be closed for %s: %s",
                                request.query_key, error)
                    report.ledger_failures.append(
                        f"close {request.query_key}: {type(error).__name__}: {error}"
                    )
                    conn.rollback()

        report.models.append(seat)
        report.candidates += seat.candidates
        report.kept += seat.kept
        report.stored += seat.stored

    return report
