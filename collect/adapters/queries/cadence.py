"""Which queries run nightly, which run weekly, and what each is allowed to cost.

PR #8 gave every capability both stances, which is right for the product and
took the sweep 49% over its budget: 24 entries where there were 16, 1,344
requests against a cap of 900. Raising the cap would have been the cheap
answer and the wrong one, because the two halves of the sweep are not buying
the same thing.

    THE GATE reads negative queries, and positive queries for the four
    SILENT-failure capabilities. Without the latter the advisor can never
    approve a cheaper model at all — for a silent failure, "nobody
    complained" is not evidence, because you would not find out. Stale is not
    an option here, so these run nightly.

    THE MODEL PAGE reads positive queries for the eight LOUD-failure
    capabilities. `contract/queries.yaml` says so itself: "These exist for
    the MODEL PAGE, not for the gate." Positive evidence up to six days old
    is indistinguishable, on a page, from positive evidence gathered last
    night. These run weekly.

A cadence is not a priority ranking. queries.yaml is emphatic that dropping
the loud positives produces a page built from a corpus only ever searched for
complaints, on two-thirds of the board, with GitHub's 0.95 trust behind it.
They are less URGENT, not less important, and urgency is the axis a budget
can actually spend.

WHY THE SPLIT IS DERIVED RATHER THAN DECLARED

`stance` lives in queries.yaml and `failure_mode` lives in capabilities.yaml.
Both are Engineer 2's, both already exist, and between them they answer the
question exactly. A list of entry names in a config file would be a second
place to edit when a capability is added — and the kind that goes stale
without anything failing, which is the defect class this repo keeps finding.
Add a capability and its cadence follows from what it is.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from collect.adapters.queries.contract import QueryEntry
from collect.config import CAPABILITIES_YAML, CONTRACT_DIR

HARVEST_YAML = CONTRACT_DIR / "harvest.yaml"

DAILY = "daily"
WEEKLY = "weekly"

#: A capability whose failure you notice in seconds. Its positive queries
#: serve the page; the gate never reads them.
LOUD = "loud"
#: A capability whose failure you do not notice. Its positive queries are the
#: only way the gate can ever pass, so they cannot be allowed to go stale.
SILENT = "silent"


#: Said the same way everywhere a budget is reported, because whoever reads it
#: is part-way through adding a capability and is looking for the cheapest way
#: out. Naming the three moves that ARE decisions, next to the one that is not,
#: is the difference between a constraint and an obstacle.
THE_MOVES = (
    "The options that are decisions: reduce the searchable alias variants "
    "(contract/registry.yaml:alias_search), move an entry to a longer cadence, "
    "or partition the models across nights. NOT a narrower sweep scope — that "
    "was listed here and measured to move the budget by exactly zero, because "
    "scope is a qualifier inside a query rather than a multiplier of queries. "
    "Rotation is the only one that closes a registry-scale gap, and it trades "
    "freshness rather than breadth: see contract/harvest.yaml. Raising the "
    "ceiling is the option that is not a decision — the cap is the whole "
    "reason the cost of a capability is visible before it is paid."
)


class HarvestBudgetError(RuntimeError):
    """A sweep would cost more than `contract/harvest.yaml` permits."""


@dataclass(frozen=True)
class CadenceBudget:
    """What one cadence may spend."""

    cadence: str
    max_requests: int
    max_minutes: float
    every_days: int


@lru_cache(maxsize=1)
def load_failure_modes(path: Path | None = None) -> Mapping[str, str]:
    """capability key -> `loud` | `silent`, from `contract/capabilities.yaml`.

    collect/ reads this file directly rather than through `judge/config.py`,
    which has its own loader: `judge/` may never be imported from this lane.
    """
    raw = yaml.safe_load((path or CAPABILITIES_YAML).read_text(encoding="utf-8"))
    return {c["key"]: c["failure_mode"] for c in raw["capabilities"]}


@lru_cache(maxsize=1)
def load_budgets(path: Path | None = None) -> Mapping[str, CadenceBudget]:
    """The per-cadence ceilings from `contract/harvest.yaml`."""
    raw = yaml.safe_load((path or HARVEST_YAML).read_text(encoding="utf-8"))
    every = raw["cadence_days"]
    return {
        cadence: CadenceBudget(
            cadence=cadence,
            max_requests=int(limits["max_requests"]),
            max_minutes=float(limits["max_minutes"]),
            every_days=int(every[cadence]),
        )
        for cadence, limits in raw["sweep_budget"].items()
    }


def cadence_of(entry: QueryEntry, failure_modes: Mapping[str, str] | None = None) -> str:
    """`daily` if the gate reads this entry, `weekly` if only the page does.

    Substitution entries carry no capability. They are cross-capability
    migration reports — the only pattern that records a decision rather than
    an impression — and `queries.yaml` calls a revert "worth more per instance
    than any other document in the corpus". They are gate evidence, so daily.
    """
    if failure_modes is None:
        failure_modes = load_failure_modes()

    if entry.stance == "negative":
        return DAILY
    if entry.capability is None:
        return DAILY

    mode = failure_modes.get(entry.capability)
    if mode is None:
        # Rule 6: an unknown failure mode is not a licence to run it less
        # often. A capability missing from capabilities.yaml is a contract
        # error that `tests/test_queries_contract.py` fails on; until then the
        # safe reading is that the gate might need it.
        return DAILY
    return WEEKLY if mode == LOUD else DAILY


def split_by_cadence(
    entries: Iterable[QueryEntry],
    failure_modes: Mapping[str, str] | None = None,
) -> dict[str, tuple[QueryEntry, ...]]:
    """Partition entries into `daily` and `weekly`. Both keys always present."""
    if failure_modes is None:
        failure_modes = load_failure_modes()

    grouped: dict[str, list[QueryEntry]] = {DAILY: [], WEEKLY: []}
    for entry in entries:
        grouped[cadence_of(entry, failure_modes)].append(entry)
    return {cadence: tuple(group) for cadence, group in grouped.items()}


def assert_within_budget(cadence: str, plan, *, budgets=None, per_minute: int = 30) -> None:
    """Refuse a sweep that costs more than the contract permits.

    Both the request count and the wall-clock minutes are checked. The count
    is what the contract argues about; the minutes are what the rate limit
    actually constrains, and they stop agreeing the moment GitHub changes
    30/minute — at which point a request-count cap alone would silently mean
    something different.

    Raises:
        HarvestBudgetError: naming the cadence, the cost and the ceiling.
    """
    budgets = budgets or load_budgets()
    budget = budgets.get(cadence)
    if budget is None:
        raise HarvestBudgetError(
            f"no budget declared for cadence {cadence!r} in contract/harvest.yaml. "
            f"Declared: {', '.join(sorted(budgets))}."
        )

    minutes = plan.minutes_at(per_minute)
    over = []
    if plan.request_count > budget.max_requests:
        over.append(
            f"{plan.request_count} requests against a ceiling of "
            f"{budget.max_requests}"
        )
    if minutes > budget.max_minutes:
        over.append(f"{minutes:.1f} minutes against a ceiling of {budget.max_minutes}")

    if over:
        raise HarvestBudgetError(
            f"The {cadence} sweep is over budget: {'; and '.join(over)}. "
            f"{THE_MOVES}"
        )


class StalenessBoundError(RuntimeError):
    """A tracked set whose rotation would refresh evidence slower than it decays.

    Separate from `HarvestBudgetError` because it is a different ceiling: the
    budget caps ONE night's spend, this caps how many nights a full pass takes.
    A set can be within budget every night and still take 31 nights to come
    round, which is the failure #33's decay argument named.
    """


def _load_rotation(path: Path | None = None) -> tuple[float, float]:
    """`(staleness_bound_days, requests_per_model)` from `contract/harvest.yaml`."""
    raw = yaml.safe_load((path or HARVEST_YAML).read_text(encoding="utf-8"))
    rotation = raw.get("rotation")
    if not rotation:
        raise StalenessBoundError(
            "no `rotation` block in contract/harvest.yaml, so the staleness bound "
            "is unset. That is a missing decision, not a licence to track any "
            "number of models (#33, rule 6)."
        )
    return float(rotation["staleness_bound_days"]), float(rotation["requests_per_model"])


def implied_staleness_days(
    tracked_count: int, *, daily_request_cap: int, requests_per_model: float
) -> int:
    """Nights for a full pass over `tracked_count` models = its staleness.

    `models_per_night` floors, because a night that can afford 11.04 models
    sweeps 11 — a partial model is not swept. Zero tracked models has zero
    staleness. A `requests_per_model` larger than a whole night's cap means a
    single model cannot be swept in one night, which is a budget error rather
    than a staleness one and is raised as such.
    """
    if tracked_count <= 0:
        return 0
    models_per_night = int(daily_request_cap // requests_per_model)
    if models_per_night <= 0:
        raise StalenessBoundError(
            f"one model costs {requests_per_model} requests, more than the daily "
            f"cap of {daily_request_cap}: no model fits in a night. That is a "
            f"budget ceiling, not a rotation one."
        )
    return -(-tracked_count // models_per_night)  # ceil division


def assert_staleness_within_bound(
    tracked_count: int, *, budgets=None, rotation: tuple[float, float] | None = None
) -> None:
    """Refuse a tracked set whose rotation would exceed the staleness bound.

    Structural, like `assert_within_budget`: the model count is not chosen, it
    falls out of the bound, and adding a model either fits or fails loudly. The
    daily request cap is read from the same `sweep_budget` the nightly spend
    check uses, so the two ceilings cannot drift apart.

    Raises:
        StalenessBoundError: naming the count, the implied staleness and the bound.
    """
    budgets = budgets or load_budgets()
    daily = budgets.get(DAILY)
    if daily is None:
        raise StalenessBoundError("no `daily` sweep_budget to derive rotation against.")
    bound_days, requests_per_model = rotation or _load_rotation()

    staleness = implied_staleness_days(
        tracked_count,
        daily_request_cap=daily.max_requests,
        requests_per_model=requests_per_model,
    )
    if staleness > bound_days:
        models_per_night = int(daily.max_requests // requests_per_model)
        fits = int(bound_days) * models_per_night
        raise StalenessBoundError(
            f"tracking {tracked_count} models implies a {staleness}-night rotation, "
            f"over the {bound_days:.0f}-day staleness bound. At {requests_per_model} "
            f"requests/model against a {daily.max_requests}/night cap, the bound "
            f"fits {fits} models. Track fewer, or raise `rotation.staleness_bound_days` "
            f"in contract/harvest.yaml as a deliberate decision — but a bound above "
            f"the 30-day fast half-life means a full pass never catches the decay."
        )


def headroom(cadence: str, plan, *, budgets=None) -> int:
    """Requests still available in this cadence's budget. Negative when over.

    Reported rather than only asserted: the number that matters when somebody
    is deciding whether a capability fits is how much is left, and finding
    that out by breaching the cap is the expensive way round.
    """
    budgets = budgets or load_budgets()
    budget = budgets[cadence]
    return budget.max_requests - plan.request_count
