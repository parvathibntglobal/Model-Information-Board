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
            "contract/harvest.yaml is the place to argue about this, and the "
            "options that are decisions are a narrower sweep scope, fewer "
            "searchable alias variants (registry.yaml:alias_search), or moving "
            "an entry to a longer cadence. Raising the number is the option "
            "that is not one."
        )
