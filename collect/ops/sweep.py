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
from datetime import UTC, datetime

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

    #: Seated models that never entered the plan, with the reason. Distinct from
    #: `unreached`, which is a budget outcome: these are excluded before a budget
    #: is consulted, and a sweep that conflates them reports a cap problem where
    #: the truth is a data one.
    excluded: list[tuple[str, str]] = field(default_factory=list)

    #: Models whose whole plan went out, and which therefore carry a
    #: `last_swept_at`. Reported rather than inferred from `models`, because a
    #: seat can appear there with a failed stamp — and the rotation reads the
    #: column, not this list, so the two must be separately visible.
    marked_swept: list[str] = field(default_factory=list)
    requests_planned: int = 0
    requests_issued: int = 0
    candidates: int = 0
    group_hits: dict[str, int] = field(default_factory=dict)
    kept: int = 0
    stored: int = 0
    max_minutes: int = 0

    #: Set when the sweep stopped on wall clock rather than on request count.
    #: Named separately because "ran out of requests" and "ran out of time" want
    #: opposite repairs — one narrows the plan, the other is a throttle.
    stopped_on_time: bool = False

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
            f"issued against a cap of {self.cap} request(s) / "
            f"{self.max_minutes} minute(s)"
            + (" — STOPPED ON WALL CLOCK" if self.stopped_on_time else ""),
            f"           {self.candidates} candidate(s), {self.kept} kept, "
            f"{self.stored} document(s) stored",
            f"           harvest_run: {self.harvest_runs_opened} opened, "
            f"{self.harvest_runs_closed} closed",
            # THE LINE A BASELINE IS READ FROM. "swept" above counts seats this
            # run touched; this counts seats that now carry a date, which is
            # what a fortnight comparison joins on. They differ when a stamp
            # fails, and a reader who cannot see both cannot tell a covered
            # model from an uncovered one with documents.
            f"           last_swept_at set on {len(self.marked_swept)} model(s)",
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
        if self.excluded:
            lines.append(
                f"EXCLUDED : {len(self.excluded)} seated model(s) never entered the "
                f"plan — {self.excluded[0][0]}: {self.excluded[0][1]}"
                + (f" (+{len(self.excluded) - 1} more)" if len(self.excluded) > 1 else "")
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
        # LEAST-RECENTLY-SWEPT FIRST, NULLS FIRST — never swept outranks
        # swept-a-week-ago. This was `ORDER BY mv.canonical_id`, and the order
        # is not cosmetic: `run_sweep` walks this mapping and stops when the
        # budget runs out, so whatever comes first is what gets covered.
        #
        # Alphabetically, 3,216 daily requests against a 900-request cap covers
        # roughly the first 11 of 40 models and `anthropic/*` consumes the
        # night. `z-ai/*` was not merely late, it was UNREACHABLE — every night,
        # for the same reason, because a restart re-issues the same prefix.
        # The 2026-08-20 record shows exactly this: the three models it swept
        # are the three alphabetically-earliest seats it had.
        #
        # `canonical_id` remains the tiebreak so a run is still deterministic
        # among models with equal (or absent) timestamps.
        "ORDER BY MIN(mv.last_swept_at) ASC NULLS FIRST, mv.canonical_id"
    ).fetchall()
    return {row[0]: tuple(sorted(row[1])) for row in rows}


def mark_swept(conn, canonical_id: str, when: datetime) -> None:
    """Record that this model's whole plan was issued, at `when`.

    WRITTEN ONLY FOR A SEAT WHOSE EVERY REQUEST WENT OUT. A model the budget
    stopped short of keeps `last_swept_at` NULL, because the column answers
    "when was this model last covered" and a half-covered model has no honest
    answer to give. Rule 6: absent stays absent rather than becoming a definite
    date that the rotation would then trust.

    This is the column `contract/harvest.yaml` named as the precondition for a
    rotation — *"a rotation changes what daily MEANS for a given model … that is
    rule 4 with a date on it"* — and the one `assert_no_phantom_sweeps` joins
    against `harvest_run`. It is written after the seat's `harvest_run` rows
    exist, so the pair can never contradict.
    """
    conn.execute(
        "UPDATE model_version SET last_swept_at = %(when)s "
        "WHERE canonical_id = %(canonical_id)s",
        {"when": when, "canonical_id": canonical_id},
    )


def excluded_seats(conn) -> list[tuple[str, str]]:
    """Seated models `seated_variants` drops, and why. Two silent exclusions.

    **BOTH WERE MINE AND BOTH WERE SILENT.** `seated_variants` filters
    `valid_until IS NULL` and unnests `variants`, so a seat disappears from a
    sweep when either condition removes all of its rows — and the sweep reported
    "40 seated models" with no line saying that 41 were seated and one was
    dropped.

    A count that shrinks without saying so is this project's most-repeated
    defect, and here it hides the two cases most worth seeing: a retired model,
    and a model seated with nothing searchable.
    """
    rows = conn.execute(
        "SELECT mv.canonical_id, "
        "       count(*) FILTER (WHERE a.valid_until IS NULL) AS live, "
        "       count(*) FILTER (WHERE a.valid_until IS NULL "
        "                        AND a.variants <> '{}') AS searchable "
        "FROM model_alias a JOIN model_version mv ON mv.id = a.model_version_id "
        "GROUP BY mv.canonical_id ORDER BY mv.canonical_id"
    ).fetchall()
    out = []
    for canonical_id, live, searchable in rows:
        if live == 0:
            out.append((
                canonical_id,
                "every alias row's validity window is closed — a retired model is "
                "correctly not swept, and correctly not silent about it",
            ))
        elif searchable == 0:
            out.append((
                canonical_id,
                "seated, live, and no row carries a search string: the canonical id "
                "and its local part earn no query, so this model is in the registry "
                "and unreachable by any sweep",
            ))
    return out


def sweep_budget(cadence: str = "daily", path: str | None = None) -> tuple[int, int]:
    """`(max_requests, max_minutes)` for one cadence, from `contract/harvest.yaml`.

    **CORRECTED. This was `request_cap()`, and it was wrong twice.**

    It walked the contract and returned the FIRST `max_requests` it found, which
    is `daily`'s 900 whatever cadence was asked for — so a weekly sweep would
    have run against the daily ceiling, 900 instead of 600. And it read only half
    the budget: `harvest.yaml` sets `max_minutes` beside `max_requests` for each
    cadence, and says why — *"the minute figure is the one that survives a
    rate-limit change, so it is checked too rather than left implied by the
    request count."* The first real sweep proved that comment right: three 403s
    with 16–22s backoffs inside 32 requests, so wall clock and request count came
    apart immediately.

    **What the cap governs, stated because I had it wrong:** requests per SWEEP,
    per CADENCE — not per model. `harvest.yaml` says "Requests per sweep, per
    cadence. The ceiling, not the target." A per-model reading makes 900 no
    constraint at all, since one model's daily plan is ~53 requests.
    """
    from pathlib import Path

    import yaml

    from collect.config import REPO_ROOT

    target = Path(path) if path else REPO_ROOT / _HARVEST_CONTRACT
    raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    budget = (raw.get("sweep_budget") or {}).get(cadence)
    if not budget:
        raise RuntimeError(
            f"no `sweep_budget: {cadence}:` in {target}. A sweep without a budget "
            f"the contract set is a sweep with a budget this code invented, and "
            f"the whole point of the cap is that it is not ours to choose."
        )
    missing = [k for k in ("max_requests", "max_minutes") if k not in budget]
    if missing:
        raise RuntimeError(
            f"`sweep_budget: {cadence}` is missing {', '.join(missing)}. Both halves "
            f"are the budget: the request count is what a plan can check in advance "
            f"and the minute figure is what survives a rate-limit change."
        )
    return int(budget["max_requests"]), int(budget["max_minutes"])


def sweep_github(
    conn,
    harvester,
    *,
    entries,
    scope: tuple[str, ...] = (),
    cap: int | None = None,
    max_minutes: int | None = None,
    cadence: str = "daily",
    source_id: str = "github",
    now=None,
) -> SweepReport:
    """Sweep every seated model until the budget runs out, recording each query.

    TWO PHASES PER QUERY, not per sweep. `open_harvest_run` writes the row before
    the fetch and `close_harvest_run` fills it in afterwards, so a process killed
    mid-query leaves `finished_at IS NULL` — the only carrier of "started and
    never came back". Committed per query for the same reason: a run held open in
    one transaction and rolled back would take every record of the night with it.
    """
    import time

    from collect.adapters.github import QueryRun
    from collect.adapters.queries import plan_searches
    from collect.ops.ledger import close_harvest_run, open_harvest_run

    contract_cap, contract_minutes = sweep_budget(cadence)
    cap = contract_cap if cap is None else cap
    minutes = contract_minutes if max_minutes is None else max_minutes
    clock = now or time.monotonic
    started = clock()
    report = SweepReport(cap=cap, max_minutes=minutes)

    by_model = seated_variants(conn)
    report.excluded = excluded_seats(conn)
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
        elapsed_minutes = (clock() - started) / 60
        if elapsed_minutes >= minutes:
            report.stopped_on_time = True
            report.unreached.append(canonical_id)
            continue
        if report.requests_issued + plan.request_count > cap:
            report.unreached.append(canonical_id)
            continue

        seat = ModelSweep(canonical_id=canonical_id, variants=variants)
        overran = False
        for request in plan.requests:
            # THE CEILING IS CHECKED HERE TOO, NOT ONLY AT THE MODEL BOUNDARY.
            # It was checked once per model, and a model carries 32-64 requests
            # — so a sweep that passed the check with one minute left ran the
            # whole plan anyway. Measured on 2026-08-24: 41m51s against a
            # 35-minute contract ceiling, because throttle backoffs of 15-22s
            # stretched a single model's plan far past it.
            #
            # A ceiling a model can overrun by 64 requests is not a ceiling,
            # and `contract/harvest.yaml` states the minutes are what the rate
            # limit actually constrains — so overrunning them is not a
            # bookkeeping slip, it is spending a budget the contract denied.
            if (clock() - started) / 60 >= minutes:
                report.stopped_on_time = True
                overran = True
                break
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
            # THE RUN ID REACHES THE DOCUMENTS. `opened` is minted before the
            # fetch by the two-phase ledger, so it is already in scope here —
            # which is why this is one call site and not a redesign. `None` when
            # the ledger write failed above, and the writer records that as
            # `not_recorded` rather than inventing provenance.
            wrote = harvester.write_documents(
                conn, run, harvest_run_id=opened.id if opened is not None else None
            )
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

        # A SEAT THE CLOCK CUT SHORT IS NOT COVERED, so it is not stamped and
        # it is reported as unreached. Rule 6: `last_swept_at` answers "when was
        # this last covered", and a model that got 12 of its 64 requests has no
        # honest answer — stamping it would deprioritise it next night in favour
        # of models actually swept, which is the ordering working backwards.
        if overran:
            report.unreached.append(canonical_id)
            report.models.append(seat)
            report.candidates += seat.candidates
            report.kept += seat.kept
            report.stored += seat.stored
            continue

        # EVERY REQUEST IN THIS SEAT'S PLAN WENT OUT. Only here is that true.
        try:
            mark_swept(conn, canonical_id, datetime.now(UTC))
            conn.commit()
            report.marked_swept.append(canonical_id)
        except Exception as error:  # noqa: BLE001
            # A failed stamp is NOT a failed sweep. The documents are written
            # and committed above; this is the rotation's bookkeeping, and
            # losing it must not roll back retrieval that succeeded.
            log.warning("last_swept_at could not be set for %s: %s", canonical_id, error)
            report.ledger_failures.append(
                f"mark_swept {canonical_id}: {type(error).__name__}: {error}"
            )
            conn.rollback()

        report.models.append(seat)
        report.candidates += seat.candidates
        report.kept += seat.kept
        report.stored += seat.stored

    return report
