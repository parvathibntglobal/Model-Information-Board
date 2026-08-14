"""Which queries the gate needs nightly, and which only the page reads.

PR #8 gave every capability both stances — right for the product, and it took
the sweep from 896 requests to 1,344 against a cap of 900. The cadence split
is what pays for it, and this file is the check that the split is derived
from what an entry IS rather than from a list somebody has to maintain.

Nothing here asserts a count of entries. Counts are the contract's business
and `tests/test_queries_contract.py` owns them; a count here would be the
same defect the hardcoded 16 was.
"""

from __future__ import annotations

from collect.adapters.queries.cadence import (
    DAILY,
    WEEKLY,
    cadence_of,
    load_budgets,
    load_failure_modes,
    split_by_cadence,
)
from collect.adapters.queries.contract import QueryEntry, TermSet, load_queries

TERMS = TermSet(subject=("{alias}",), topic=("summary",), signal=("held up",))


def entry(**overrides) -> QueryEntry:
    base = {
        "kind": "capability",
        "capability": "summarization.fidelity",
        "stance": "positive",
        "terms": TERMS,
        "records_condition": "context_size",
    }
    base.update(overrides)
    return QueryEntry(**base)


# ── the rule ──────────────────────────────────────────────────────────────


def test_every_negative_query_is_daily_whatever_its_capability():
    """Negatives are gate evidence for loud and silent capabilities alike."""
    modes = load_failure_modes()
    for capability in modes:
        assert cadence_of(entry(capability=capability, stance="negative"), modes) == DAILY


def test_a_positive_for_a_silent_capability_is_daily():
    """The gate cannot pass without it, so it cannot be allowed to go stale.

    For a silent failure "nobody complained" is not evidence — you would not
    find out — so positive consensus is the only route to a recommendation.
    """
    modes = load_failure_modes()
    silent = [k for k, mode in modes.items() if mode == "silent"]
    assert silent, "capabilities.yaml declares no silent-failure capability"

    for capability in silent:
        assert cadence_of(entry(capability=capability), modes) == DAILY


def test_a_positive_for_a_loud_capability_is_weekly():
    """queries.yaml: they exist for the MODEL PAGE, not for the gate."""
    modes = load_failure_modes()
    loud = [k for k, mode in modes.items() if mode == "loud"]

    for capability in loud:
        assert cadence_of(entry(capability=capability), modes) == WEEKLY


def test_substitution_is_daily_because_the_gate_reads_it():
    """A migration that was reverted is the most valuable document in the corpus."""
    assert cadence_of(entry(kind="substitution", capability=None)) == DAILY


def test_an_unknown_capability_falls_to_daily_not_to_weekly():
    """Rule 6. An unknown failure mode is not a licence to run it less often.

    The contract test fails on a capability missing from capabilities.yaml, so
    this is the state between a bad edit and that failure — and the safe
    reading of "I do not know whether the gate needs this" is that it might.
    """
    assert cadence_of(entry(capability="nobody.declared.this"), {}) == DAILY


# ── against the real contract ─────────────────────────────────────────────


def test_the_split_covers_every_entry_exactly_once():
    """An entry that falls out of both groups is never searched for at all."""
    queries = load_queries()
    groups = split_by_cadence(queries.capability_queries)

    assigned = [e for group in groups.values() for e in group]
    assert len(assigned) == len(queries.capability_queries)
    assert set(assigned) == set(queries.capability_queries)


def test_the_gate_keeps_every_capability_nightly():
    """The split must not leave a capability with nothing current behind it.

    Weekly-only for some capability would mean the gate reading six-day-old
    evidence for it, which is not what the split traded away.
    """
    queries = load_queries()
    daily = split_by_cadence(queries.capability_queries)[DAILY]
    assert {e.capability for e in daily} == set(load_failure_modes())


def test_only_loud_positives_moved_to_weekly():
    """Precisely the eight PR #8 added, and nothing that was there before."""
    modes = load_failure_modes()
    queries = load_queries()
    weekly = split_by_cadence(queries.capability_queries)[WEEKLY]

    assert {e.stance for e in weekly} == {"positive"}
    assert {modes[e.capability] for e in weekly} == {"loud"}
    assert len(weekly) == sum(1 for mode in modes.values() if mode == "loud")


def test_the_budget_file_declares_both_cadences():
    budgets = load_budgets()
    assert set(budgets) == {DAILY, WEEKLY}
    assert budgets[DAILY].every_days == 1
    assert budgets[WEEKLY].every_days == 7
    assert budgets[DAILY].max_requests == 900, "the cap PR #8 overran, unraised"


def test_the_weekly_budget_is_not_a_second_daily_budget():
    """If weekly could cost as much as daily, the split has bought nothing."""
    budgets = load_budgets()
    assert budgets[WEEKLY].max_requests < budgets[DAILY].max_requests
