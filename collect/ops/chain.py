"""The nightly chain: stages, refusals, and a record written as it goes.

THE PREMISE, WHICH IS NOT THAT STAGES SUCCEED
----------------------------------------------
Nine silent-failure defects were found in this lane in one fortnight, every one
of them caught by a person reading a number that was wrong in a way that read as
an answer. Under cron there is no person. So the property this module exists to
provide is that **a stage which did not run is distinguishable from a stage that
ran and found nothing.**

    A STAGE WRITES ITS LINE BEFORE IT DOES ITS WORK. `started` goes to the
    journal, then the work, then `finished`. A killed process leaves
    "started 03:00, never finished", which is a fact. A record written only on
    success leaves nothing, which reads as a night with no work to do.

    A HOLE IS A REFUSAL, NOT A SKIP, AND IT NAMES WHAT IT STARVES.
    "flattening: not built" is a skip with better manners. "flattening: not
    built, so thread_context gets 0 rows and judge/ has nothing to extract
    tonight" is a refusal — it says what the rest of the night is missing
    because of it. Same shape as `assemble_thread`, which raises
    `AssemblyNotBuilt` rather than returning an empty tree.

    COUNTS ARE ABSENT WHERE UNKNOWN. A stage that never ran reports no counts,
    not zeroes. Rule 6, at the reporting layer.

THE UNIT OF REFUSAL IS THE WRITER, NOT THE STAGE
-------------------------------------------------
`assemble` is three writers and only one of them is missing: authors and dedupe
work today, flattening does not. A stage that refused wholesale would discard
two working writers to report one missing one, and the coverage it lost would be
invisible. So the stages below are as small as the thing that can independently
succeed or refuse.

WHERE THE RECORD LIVES, AND WHY IT IS NOT A TABLE YET
------------------------------------------------------
`job_run` does not exist in `contract/tables.sql`, and that file is shared. The
journal is therefore a JSONL artifact beside the raw store — append-only, one
line per stage transition — which needs no contract change and gives the
before-the-work property immediately. `job_run` is proposed to Engineer 2; when
it lands the journal keeps its shape and gains a row.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

OK = "ok"
ERROR = "error"
REFUSED = "refused"


@dataclass
class StageResult:
    """What one stage did. `counts` is empty where a stage never got to look."""

    outcome: str
    detail: str = ""
    counts: dict[str, Any] = field(default_factory=dict)
    #: What the rest of the night does not get because this stage did not run.
    #: Only meaningful on a refusal, and required there.
    starves: str = ""


class NotBuilt(StageResult):
    """A stage with no implementation. Refuses, and says what it starves."""

    def __init__(self, detail: str, starves: str) -> None:
        super().__init__(outcome=REFUSED, detail=f"not built: {detail}", starves=starves)


@dataclass(frozen=True)
class Stage:
    """One step. `run` is None where nothing has been written to call."""

    name: str
    run: Callable[[dict], StageResult] | None
    #: Stages whose failure makes this one meaningless rather than merely empty.
    #: A stage whose need failed is not run, and says so — it does not report a
    #: zero it never measured.
    needs: tuple[str, ...] = ()
    #: Filled in for `run=None` stages, so the refusal is never bare.
    starves: str = ""

    def refusal(self) -> StageResult:
        return NotBuilt(self.name, self.starves)


class Journal:
    """Append-only, one line per transition, flushed immediately.

    Flushed on every write because the failure this is for is the process
    disappearing. A buffered journal describes runs that completed, which are
    the runs that needed it least.
    """

    def __init__(self, path: Path | None) -> None:
        self.path = Path(path) if path else None
        self.lines: list[dict] = []
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, **entry) -> None:
        entry.setdefault("at", datetime.now(UTC).isoformat())
        self.lines.append(entry)
        if self.path:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + "\n")
                handle.flush()


class UnknownStage(ValueError):
    """`--only` named a stage the chain does not have.

    RAISES rather than selecting nothing, for the reason `sweep_requests` raises
    on a refused shape: asking for a stage is a decision somebody made, and a
    run that quietly selected zero stages would print a clean summary of nothing
    and read as a night with no work to do.
    """

    def __init__(self, name: str, known) -> None:
        super().__init__(
            f"no stage named {name!r}. The chain has: {', '.join(sorted(known))}"
        )


def select_stages(stages, only):
    """The named stages plus everything they depend on, in chain order.

    WHY DEPENDENCIES COME TOO, RATHER THAN BEING SKIPPED. `score-documents`
    needs `preflight`, and `preflight` is the build-fixture guard - the check
    that refuses to write outside `development` when seeded rows are present.
    A `--only score-documents` that skipped it would run a WRITE stage with the
    guard bypassed, which is exactly what `cli.py`'s AST test exists to prevent
    one layer down. So `--only` narrows what is ATTEMPTED, never what is
    CHECKED.

    Order is the chain's own, not the order the caller typed. The chain's
    ordering is a dependency statement; letting a command-line reorder it would
    make `--only a,b` and `--only b,a` different runs.

    Returns the sublist. Raises `UnknownStage` on a name the chain does not
    have - a typo that silently selected nothing is the failure mode here.
    """
    by_name = {stage.name: stage for stage in stages}
    wanted = list(only)
    for name in wanted:
        if name not in by_name:
            raise UnknownStage(name, by_name)

    needed: set[str] = set()

    def _pull(name: str) -> None:
        if name in needed:
            return
        needed.add(name)
        for need in by_name[name].needs:
            # A `needs` entry naming a stage the chain does not have is a
            # defect in the stage list rather than in the caller's request, so
            # it raises here too rather than being dropped.
            if need not in by_name:
                raise UnknownStage(need, by_name)
            _pull(need)

    for name in wanted:
        _pull(name)
    return [stage for stage in stages if stage.name in needed]


@dataclass
class ChainRun:
    """Every stage's outcome, and the summary a person reads in the morning."""

    results: dict[str, StageResult] = field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    #: How many stages the full chain has, when this run was a `--only` subset.
    #: THE DENOMINATOR, and it is here rather than left to the caller because a
    #: summary reading "2 of 2 stages ran" after `--only score-documents` is
    #: true and reads as a complete night (rule 7). None means the whole chain.
    selected_of: int | None = None
    #: What was asked for, so the summary can say why the rest is absent.
    selection: tuple[str, ...] = ()

    @property
    def refused(self) -> list[str]:
        return [name for name, r in self.results.items() if r.outcome == REFUSED]

    @property
    def errored(self) -> list[str]:
        return [name for name, r in self.results.items() if r.outcome == ERROR]

    @property
    def ok(self) -> bool:
        return not self.errored

    def summary(self) -> str:
        lines = []
        for name, result in self.results.items():
            counts = " ".join(f"{k}={v}" for k, v in result.counts.items())
            line = f"  {result.outcome.upper():<8} {name:<22} {counts}".rstrip()
            if result.detail:
                line += f"  {result.detail}" if not counts else f"\n           {result.detail}"
            if result.starves:
                line += f"\n           starves: {result.starves}"
            lines.append(line)
        ran = len(self.results) - len(self.refused)
        head = (
            f"nightly chain: {ran} of {len(self.results)} stages ran, "
            f"{len(self.refused)} refused, {len(self.errored)} errored"
        )
        if self.selected_of is not None:
            # THE POPULATION, BEFORE THE COUNTS. Without this line a `--only`
            # run reads "1 of 2 stages ran" and a reader has no way to know the
            # chain has fourteen. The stages that were not selected are NOT
            # refusals - nobody looked at them - so they are named here rather
            # than given a fourth outcome, which is the mistake
            # `retrieval_provenance` made and withdrew.
            head = (
                f"nightly chain, PARTIAL RUN: --only "
                f"{','.join(self.selection)} selected "
                f"{len(self.results)} of {self.selected_of} stages "
                f"(the named ones and what they depend on). The other "
                f"{self.selected_of - len(self.results)} were NOT ATTEMPTED and "
                f"are not refusals.\n" + head
            )
        return "\n".join([head, *lines])




def _record_unrun(context, stage_name: str, result) -> None:
    """One `job_run` row for a stage that never got to run.

    Opened and closed together, because there was no work between the two. The
    row still carries `started_at` and `finished_at`, so it is distinguishable
    from a killed process — which leaves `finished_at` NULL and is the state
    this whole table is arranged around.
    """
    opened = _open_ledger_row(context, stage_name)
    if opened is not None:
        _close_ledger_row(context, opened, result)


def _open_ledger_row(context, stage_name: str):
    """Write the `job_run` row, or return None where there is no database.

    A chain run with `--no-database` is legitimate — it is how the refusals are
    read without a server — and it must not become a failure. The absence is
    reported by the row simply not existing, which is the honest record: nothing
    was written because nothing could be.
    """
    conn = (context or {}).get("conn")
    if conn is None:
        return None
    from collect.ops.ledger import open_run

    try:
        return open_run(conn, stage_name)
    except Exception as error:  # noqa: BLE001
        log.warning("job_run: could not open a row for %s: %s", stage_name, error)
        return None


def _close_ledger_row(context, opened, result) -> None:
    """Conclude the row. A ledger failure never fails the stage it describes."""
    if opened is None:
        return
    conn = (context or {}).get("conn")
    if conn is None:
        return
    from collect.ops.ledger import close_run

    try:
        close_run(
            conn, opened,
            outcome=result.outcome, detail=result.detail, counts=result.counts,
        )
    except Exception as error:  # noqa: BLE001
        log.warning("job_run: could not close %s: %s", opened.id, error)


def run_chain(stages, context: dict | None = None, journal: Journal | None = None) -> ChainRun:
    """Run every stage in order. A failure stops only what depends on it.

    Independence is the whole point of the ordering: the three sweeps share only
    the registry they both read, and the publication gate needs two platforms —
    so losing the blog sweep because GitHub was rate-limited is the expensive
    outcome, and nothing here encodes it.
    """
    context = context if context is not None else {}
    journal = journal or Journal(None)
    run = ChainRun(started_at=datetime.now(UTC))
    journal.write(event="chain-started")

    for stage in stages:
        blocked = [need for need in stage.needs
                   if run.results.get(need, StageResult(REFUSED)).outcome != OK]
        if blocked:
            # NOT a zero. This stage never looked, and a count of 0 would claim
            # it did.
            result = StageResult(
                outcome=REFUSED,
                detail=f"needs {', '.join(blocked)}, which did not succeed",
                starves=stage.starves,
            )
            run.results[stage.name] = result
            journal.write(event="stage-skipped", stage=stage.name, detail=result.detail)
            # A ROW EVEN THOUGH IT DID NOT RUN. A stage refused by the chain is
            # a refusal exactly as much as one refused by its own code, and the
            # first version of this wiring recorded only the second — so
            # `assemble-flatten` had no row at all while `poll-registry` had one
            # saying `refused`. Both are "we looked at this stage tonight and it
            # produced nothing", and the reason differs, which is what `detail`
            # is for.
            _record_unrun(context, stage.name, result)
            continue

        if stage.run is None:
            result = stage.refusal()
            run.results[stage.name] = result
            journal.write(event="stage-refused", stage=stage.name,
                          detail=result.detail, starves=result.starves)
            _record_unrun(context, stage.name, result)
            continue

        # BEFORE the work, not after it — in the journal AND in `job_run`.
        # The row is committed on its own so a stage that rolls back still
        # leaves evidence that it ran, and a killed process leaves "started
        # 03:00, never finished" rather than nothing at all.
        journal.write(event="stage-started", stage=stage.name)
        opened = _open_ledger_row(context, stage.name)
        try:
            result = stage.run(context)
        except Exception as error:  # noqa: BLE001 - the chain records, it does not judge
            result = StageResult(outcome=ERROR, detail=f"{type(error).__name__}: {error}")
        run.results[stage.name] = result
        journal.write(event="stage-finished", stage=stage.name,
                      outcome=result.outcome, counts=result.counts, detail=result.detail)
        _close_ledger_row(context, opened, result)

    run.finished_at = datetime.now(UTC)
    journal.write(event="chain-finished", refused=run.refused, errored=run.errored)
    return run


# ── the stages, and the four that have nothing to call ────────────────────
#
# Each `run=None` entry is a to-do list item with tonight's cost attached. They
# are listed here rather than omitted, because a chain that quietly covers five
# stages of eight is the failure this module was built to prevent.


def _preflight_stage(context) -> StageResult:
    from collect.ops.preflight import preflight

    report = preflight(
        context.get("conn"),
        environment=context["environment"],
        policy=context.get("policy"),
        sources=context.get("sources"),
        raise_on_failure=False,
    )
    return StageResult(
        outcome=OK if report.ok else ERROR,
        detail=report.summary() if report.ok else "; ".join(report.failed),
        counts={"passed": len(report.passed), "failed": len(report.failed),
                "skipped": len(report.skipped)},
    )


def _poll_registry_stage(context) -> StageResult:
    """Poll, upsert, and record what moved. FR-3's producer runs here."""
    from collect.registry.openrouter import fetch_models, parse_models, write_model_versions

    conn = context.get("conn")
    if conn is None:
        return StageResult(REFUSED, "no database connection",
                           starves="the registry is not refreshed")
    response = fetch_models(context["client"]) if context.get("client") else None
    if response is None:
        return StageResult(REFUSED, "no HTTP client supplied",
                           starves="the registry is not refreshed")

    # `.json()`, WHICH THIS LINE DID NOT DO. `fetch_models` returns the
    # RESPONSE on purpose — its docstring says so, "so the caller can store the
    # bytes before parsing" — and this stage passed the response object straight
    # into `parse_models`, which read it as neither a dict nor a list and
    # returned an empty result. Every poll the chain has ever run reported
    # `OK models=0`, and the registry's rows came from a hand-run instead.
    #
    # `parse_models` now RAISES on a payload it cannot read, so this can never
    # fail silently again — but the fix belongs on both sides: a guard that
    # turns a type error into a legible failure does not excuse the caller.
    result = parse_models(response.json(), retrieved_at=datetime.now(UTC))

    # A ZERO IS NOW WORTH REFUSING ON. A feed that parses to no models is not a
    # world with no models — it is a feed we could not read, or an endpoint that
    # changed shape. Reported as an error rather than an OK with counts=0,
    # because the whole reason this stage was broken for its entire life is that
    # zero models read as a successful night.
    if not result.models:
        return StageResult(
            ERROR,
            f"the feed parsed to 0 models from {result.raw_entries} entries",
            starves="the registry is not refreshed, and 340 models is the "
                    "expected order of magnitude",
        )

    # TOMBSTONES, BEFORE THE WRITE. A deleted polled model is re-inserted by
    # the very next poll unless it is named here; `load_tombstones` raises on a
    # missing or malformed file rather than returning an empty set, because an
    # empty set is exactly the silent failure this exists to prevent. The count
    # goes on the stage line: skipped models must not read as a catalogue that
    # stopped listing them.
    from collect.registry.tombstones import apply_tombstones, load_tombstones

    result, tombstoned = apply_tombstones(result, load_tombstones())
    counts = write_model_versions(conn, result)
    return StageResult(OK, counts={"models": len(result.models),
                                   "tombstoned_skipped": len(tombstoned), **counts})


def _recompute_window_stage(context) -> StageResult:
    """FR-1's trailing window. The sole writer of `model_version.in_window`."""
    from collect.registry.load import recompute_window

    conn = context.get("conn")
    if conn is None:
        return StageResult(REFUSED, "no database connection",
                           starves="in_window keeps yesterday's verdict")
    counts = recompute_window(conn)
    return StageResult(OK, counts=counts)


def _load_capabilities_stage(context) -> StageResult:
    """`contract/capabilities.yaml` into `capability`. THE TABLE `claim` FKs TO.

    Wired here because it had no automated caller. `collect/registry/capabilities.py`
    has existed and worked the whole time; its only caller was
    `collect/cli.py registry load-capabilities`, which is a person with a
    terminal. Nobody had typed it against staging, so `capability` held 0 rows,
    and `claim.capability_key text NOT NULL REFERENCES capability(key)` meant
    **no claim could insert in any run** — a foreign key nothing had reached.

    Same shape as issue #27: not a broken check, a check with no caller. The
    difference is that #27's absence was silent, and this one presents as an
    extractor producing claims that vanish.

    Idempotent, so running it nightly is a no-op once loaded.
    """
    from collect.registry.capabilities import load_capabilities

    conn = context.get("conn")
    if conn is None:
        return StageResult(REFUSED, "no database connection",
                           starves="capability stays as it is, and claim's "
                                   "foreign key refuses every insert if it is empty")
    report = load_capabilities(conn)
    return StageResult(OK, counts={
        "inserted": report.inserted,
        "updated": report.updated,
        "unchanged": report.unchanged,
    })


def _sweep_reddit_stage(context) -> StageResult:
    """The Reddit LISTING sweep. `collect/ops/sweep_reddit.py`.

    WIRED 2026-08-28, AND IT WAS BUILT THREE HOURS BEFORE IT WAS WIRED. The stage
    function and the `ops sweep-reddit` command landed in PR #173 and this entry
    stayed `run=None`, so the chain reported nine refusing stages when it had
    eight, and this one's `starves=` text still said *"no document writer for them
    either"* — a writer that had existed since 2026-08-21. **A stale refusal is
    worse than a missing stage: it names a blocker that is gone, so the next
    person costs the wrong work.** Exactly the shape `collect/CLAUDE.md`'s
    uncalled-writer entries keep recording, produced by me in one sitting.

    IT BUILDS ITS OWN CLIENT. `context["client"]` is the OpenRouter/registry
    client and carries no RapidAPI headers, so a Reddit request through it would
    404 at the gateway. Refusing on a missing key rather than raising: no
    `RAPIDAPI_KEY` is a configuration state the night should report and survive,
    not a crash that takes the rollup with it.

    The terms gate fires in `harvester_for_source`, before a single request.
    """
    from collect.adapters.reddit import RedditConfigError, build_client, harvester_for_source
    from collect.config import settings
    from collect.ops.sweep_reddit import LISTING, sweep_reddit
    from collect.rawstore import RawStore
    from collect.registry.sources import load_sources

    conn = context.get("conn")
    if conn is None:
        return StageResult(REFUSED, "no database connection",
                           starves="no Reddit documents, and the listing's "
                                   "harvest_run rows are not opened either")

    contract = load_sources()
    reddit = next((s for s in contract.platforms if s["id"] == "reddit"), None)
    if reddit is None:
        return StageResult(REFUSED, "contract/sources.yaml has no reddit source row",
                           starves="no Reddit documents; the terms gate cannot even "
                                   "be asked without a source row to ask about")
    if not contract.sweep_subreddits:
        return StageResult(
            REFUSED, "contract/sources.yaml has no sweep_subreddits block",
            starves="no Reddit documents. NOT the same as a sweep that found "
                    "nothing: nobody has chosen a subreddit list, and sweeping an "
                    "empty one would report as nobody discussing anything",
        )

    # ⚠ `--no-network` MEANT NOTHING HERE UNTIL 2026-08-31, AND THAT IS A HAZARD
    #   WELL BEYOND ANY ONE USE. `_cmd_ops_run` withholds `context["client"]` for
    #   `--no-network`, and this stage never read it - it builds its own, because
    #   the registry client carries no RapidAPI headers and a Reddit request
    #   through it would 404 at the gateway. That reasoning is correct and the
    #   consequence was not: a flag documented as "run without an HTTP client"
    #   left this stage issuing live requests and writing documents.
    #
    #   A flag that silently does not apply is worse than an absent flag,
    #   because the caller has already decided. `--no-network` is how the
    #   refusals get read without a server; anyone using it to inspect the chain
    #   would have harvested Reddit as a side effect of looking.
    #
    #   So the CONTEXT carries the intent and every stage honours it, rather
    #   than the intent living in one client the stages happen to share.
    #   Checked AFTER the contract and subreddit checks above so that a
    #   `--no-network` run still reports a missing source row or an unchosen
    #   subreddit list - those are build defects and are worth surfacing when
    #   somebody is reading the chain offline, which is exactly when they look.
    if context.get("offline"):
        return StageResult(
            REFUSED, "--no-network: refusing to open a Reddit client",
            starves="no Reddit documents this run. Nothing is broken - the run "
                    "was asked not to touch the network, and this stage builds "
                    "its own client rather than sharing the registry's",
        )

    try:
        client = build_client()
    except RedditConfigError as error:
        return StageResult(REFUSED, str(error),
                           starves="no Reddit documents tonight. Reddit is the only "
                                   "source that is structurally many voices, so the "
                                   "voice count stays at whatever blog can reach")

    with client:
        harvester = harvester_for_source(
            reddit,
            rulings=contract.rulings,
            client=client,
            store=RawStore(settings().raw_store_path),
        )
        report = sweep_reddit(conn, harvester, contract=contract, provenance=LISTING)

    return StageResult(OK, counts={
        "subreddits": len(report.subreddits),
        "unreached": len(report.unreached),
        "requests": report.requests_issued,
        "candidates": report.candidates,
        # THE DENOMINATOR TRAVELS WITH THE COUNTS. A candidate figure without the
        # population it was drawn from is the failure rule 7 is about, and the
        # journal is read long after the run.
        "offered": report.offered,
        "population_per_subreddit": report.population_per_subreddit,
        "kept": report.kept,
        "stored": report.stored,
        # The result, not `stored`. See RedditSweepReport.
        "distinct_threads": report.distinct_threads,
        "harvest_runs_closed": report.harvest_runs_closed,
        "documents_with_run_id": report.documents_with_run_id,
        "quota_exhausted": report.quota_exhausted,
    })



def _triage_stage(context) -> StageResult:
    """E4's six gates over the stored corpus. `collect/triage/run.py`.

    WIRED 2026-09-08, AND THE GATES PREDATED IT BY WEEKS. `collect/triage/
    gates.py` ran six gates, was tested and was measured the whole time;
    nothing ever ran it against the database. `document.triage_verdict` was
    NULL on all 6,502 stored rows, and every survival figure this project has
    quoted - the 82.8% in that module's own docstring included - came from a
    script building `Document`s by hand off a JSONL export. Third instance of
    the shape: `load-capabilities`, `score-documents`, and now this.

    IT WRITES `triage_verdict` AND `filter_reasons` AND NOT `status`, WHICH IS
    WHY IT CAN BE WIRED AT ALL. Two of the six gates cannot run - no language
    detector, and `contract/bots.yaml` does not exist - so rule 8 makes this a
    RECORDED FIELD rather than a gate: `status` is what `judge/` filters on
    (`status = 'kept'`, with an index for that predicate), and dropping 6,502
    rows out of its view on four gates of six would make a false positive
    invisible. The verdict is recorded where somebody can measure its error
    rate against the labelling pool, and promotion to `status` goes on that
    evidence.

    `dry_run=False` HERE AND `True` IN THE FUNCTION'S DEFAULT. A stage that has
    to be asked twice does not run at night, and the default protects a person
    at a prompt on a shared database - `score-documents` above makes the same
    split for the same reason.

    NEEDS `assemble-flatten` STILL, unchanged: triage reads the prose a
    document's payload yields, and the flatten stage is what proves that
    payload is assemblable. It is worth knowing that this would otherwise run
    fine without it - the dependency is about the corpus being coherent, not
    about a column.

    IDEMPOTENT: selects `triage_verdict IS NULL` and the UPDATE re-checks it.
    """
    from collect.rawstore import RawStore
    from collect.triage.run import triage_stored

    conn = context.get("conn")
    if conn is None:
        return StageResult(REFUSED, "no database connection",
                           starves="document.triage_verdict and filter_reasons "
                                   "stay NULL, so triage survival has neither a "
                                   "numerator nor a denominator and alert 2's "
                                   "14-night burn-in cannot start counting")
    store = context.get("raw_store") or RawStore()
    run = triage_stored(conn, store, dry_run=False)
    return StageResult(OK, detail=run.describe(), counts={
        "eligible": run.eligible,
        # THE DENOMINATOR, and it is not `eligible`. A document whose payload
        # this host cannot read was never gated, and counting it in a survival
        # rate reports our coverage as the corpus's quality (rule 7).
        "triaged": run.triaged,
        "kept": run.kept,
        "dropped": run.dropped,
        "written": run.written,
        # NAMED, not folded into a failure count - and the two are DIFFERENT
        # findings with different repairs: an absent payload may be on another
        # machine, a present-but-not-prose payload is a provenance defect here.
        "unreadable": run.unreadable,
        "not_prose": run.not_prose,
        "subject_inherited": run.subject_inherited,
        # A thread root that resolves to nothing leaves its children facing the
        # subject gate alone, so a drop among them is an absence WE caused.
        "root_unresolvable": run.root_unresolvable,
        **{f"dropped_{k}": v for k, v in run.by_reason.items()},
        **{f"could_not_run_{k}": v for k, v in run.never_ran.items()},
    })

def _score_documents_stage(context) -> StageResult:
    """The five specificity components onto `document`. `collect/triage/store.py`.

    WIRED 2026-08-31, AND THE COMPUTING CODE PREDATES IT BY WEEKS.
    `collect/triage/specificity.py` counted the components, was tested and was
    contract-backed the whole time; no path stored what it computed. Seven rows
    of 3,061 carried values, and all seven came from
    `scripts/export_thread_contexts.py` hand-building INSERT text for one thread
    and one article. Same shape as `load-capabilities` above and as issue #27:
    not a broken writer, a writer that was never called.

    THIS IS A RECORDED FIELD, NOT A GATE - which is why it can be wired without
    the ruling the rest of `triage` still needs. It writes six columns and drops
    nothing. `document.status` and `filter_reasons` are the gating half and stay
    with the `triage` stage below, where the missing bot list and the missing
    language detector are decisions rather than code (rule 8: a check whose
    error rate is unmeasured ships as a field, never as a gate).

    NEEDS ONLY `preflight`. It scores STORED rows, so it is worth running on a
    night when every sweep failed - there are 3,054 unscored documents behind it
    - and making it depend on a sweep would skip it in exactly the state where
    it has most to do.

    IDEMPOTENT: selects rows with all six columns NULL. A second run is a no-op.
    """
    from collect.rawstore import RawStore
    from collect.triage.store import score_unscored

    conn = context.get("conn")
    if conn is None:
        return StageResult(REFUSED, "no database connection",
                           starves="document.has_numbers and has_conditions stay "
                                   "NULL, so judge/'s numbers rung is withheld on "
                                   "every claim and f_specificity prices both as "
                                   "absent")
    store = context.get("raw_store") or RawStore()
    run = score_unscored(conn, store)
    return StageResult(OK, detail=run.describe(), counts={
        "eligible": run.eligible,
        "scored": run.scored,
        # NAMED, not folded into a failure count. A payload absent from this
        # machine is left NULL rather than written False, and the number is the
        # finding: it says how much of the corpus this host cannot score.
        "unreadable": run.unreadable,
        "written": run.written,
        **{f"true_{k}": v for k, v in run.true_counts.items()},
    })


def default_stages() -> list[Stage]:
    """Tonight's chain: SIX stages that run, and eight that say why they cannot.

    THIS COUNT HAS BEEN STALE TWICE AND BOTH TIMES BY ONE. It said four-and-nine
    while `sweep-reddit` was wired, which is the same defect as that stage's own
    `starves=` text naming a writer that already existed. A number in a docstring
    beside a list the reader can count is a number nobody re-derives — so if this
    disagrees with the list below, the list is right.

    Every `run=None` below is a to-do item with tonight's cost attached. They are
    listed rather than omitted, because a chain that quietly covers three stages
    of eleven is the failure this module was built to prevent.

    THE REFUSALS ARE AT WRITER GRANULARITY, and two of them are finer than the
    stage names in the proposal. `assemble` is three writers, only one of which
    is missing; `refresh-coverage` is a window recompute that exists and a
    `coverage_gap` writer that does not. Refusing either wholesale would discard
    working coverage to report a missing writer.

    AND ONE REFUSAL IS NOW LOUDER THAN THE OTHERS. `sweep-github` still reads
    `run=None` while `collect/ops/sweep.py:sweep_github` exists and has a CLI
    command — the same gap `sweep-reddit` had until this change. It is left as a
    refusal rather than quietly wired because the GitHub sweep spends a 900-request
    budget and overran its 35-minute ceiling on 2026-08-24, so putting it in the
    nightly chain is a scheduling decision rather than a wiring one.
    """
    return [
        Stage("preflight", run=_preflight_stage),
        Stage("poll-registry", run=_poll_registry_stage, needs=("preflight",)),
        Stage("recompute-window", run=_recompute_window_stage, needs=("preflight",)),
        # BEFORE anything that could produce a claim. An empty `capability`
        # table does not degrade extraction, it refuses every insert at the
        # foreign key — so this belongs upstream of the sweeps rather than
        # beside the rollup.
        Stage("load-capabilities", run=_load_capabilities_stage, needs=("preflight",)),
        Stage("write-coverage-gaps", run=None, needs=("recompute-window",),
              starves="coverage_gap stays empty, so the four kinds "
                      "LoadReport already builds — 0 unsourced, 0 missing-spelling, "
                      "0 unknown-release-date, 60 out-of-window tonight — reach "
                      "nobody"),
        Stage("sweep-github", run=None, needs=("poll-registry",),
              starves="no new GitHub documents. The harvester and write_documents "
                      "exist; what does not is the stage that plans the queries "
                      "and writes harvest_run"),
        Stage("sweep-blogs", run=None, needs=("poll-registry",),
              starves="no blog documents, and no document writer for them at all "
                      "— blogs are the only positive-evidence channel, so the "
                      "silent-failure capabilities cannot reach positive consensus"),
        # NEEDS `recompute-window` RATHER THAN `poll-registry`, and the change is
        # not cosmetic. The sieve narrows on seated aliases — a listing renders no
        # query, so the terms do all the work — and `seated_variants` reads
        # `model_alias` for models the window admits. Depending on the poll alone
        # would let a night with a stale window sieve against yesterday's seats
        # and report the result as a yield.
        Stage("sweep-reddit", run=_sweep_reddit_stage, needs=("recompute-window",)),
        Stage("assemble-authors", run=None, needs=("sweep-github",),
              starves="author rows. NOTE: `from_github` and `from_reddit` read the "
                      "adapter's in-memory hits, not stored documents, so this "
                      "belongs INSIDE the sweep rather than after it — a chain "
                      "stage over stored rows cannot produce it without re-parsing "
                      "the raw payloads"),
        Stage("assemble-dedupe", run=None, needs=("sweep-github",),
              starves="dedup_cluster, so syndicated copies would count as "
                      "independent voices the moment anything counts them"),
        Stage("assemble-flatten", run=None, needs=("sweep-github",),
              starves="thread_context and offset_map — judge/ has nothing to "
                      "extract from, and offset_map cannot be built later"),
        # THE SPECIFICITY COLUMNS, SPLIT OFF FROM `triage` 2026-08-31. They are
        # recorded fields and the rest of triage is a gate, so they were being
        # held back by rulings they do not need — the bot list and the language
        # detector. `needs=("preflight",)` and not a sweep: it scores stored
        # rows, and the night every sweep fails is the night it has most to do.
        Stage("score-documents", run=_score_documents_stage, needs=("preflight",)),
        # WIRED 2026-09-08. It writes `triage_verdict` and `filter_reasons`,
        # and deliberately NOT `document.status` — two of the six gates cannot
        # run, so rule 8 keeps this a recorded field rather than the gate that
        # drops rows out of `judge/`'s view. `document.status` therefore still
        # has no writer, which is the honest state and is said so below rather
        # than left to look wired.
        Stage("triage", run=_triage_stage, needs=("assemble-flatten",),
              starves="document.status, which STILL has no writer — the gate "
                      "half of triage waits on the bot list and a language "
                      "detector (rule 8). `triage_verdict` and `filter_reasons` "
                      "are written as of 2026-09-08, so triage survival now has "
                      "a numerator and a denominator and alert 2's 14-night "
                      "burn-in can start counting"),
        Stage("rollup", run=None,
              starves="the alert report and the coverage numbers, which "
                      "`ops.alerts` can already produce"),
    ]
