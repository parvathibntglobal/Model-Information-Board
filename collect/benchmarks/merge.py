"""Stage 7: one published value per cell (doc 10).

Within one source (10.1) duplicates are chosen by what makes them different,
never by which value is higher:

    match_variant  the value whose test setup is earliest in the column's accept list
    latest         the newest by the source's own date (re-runs of one setup)
    identical      any one, because they are all equal

Two candidates that the rule cannot separate and that differ are AMBIGUOUS:
nothing is guessed, no value is taken from that source for that cell, and a
review item lists the candidates.

Across sources (10.2) the first rule that decides wins:

    2  drop stale values; only setups in the accept list
    3  the highest TIER (sources.yaml `tier`: 1 the benchmark's own board,
       2 a reputed evaluator, 3 another third party) - a lower tier fills a cell
       only when no higher tier has a value (Parvathi, 2026-10-27)
    4  earlier in the accept list beats later
    5  highest source priority (the order within a tier)
    6  most recent (the source's own date, then when it was collected)
    7  source key, alphabetical - arbitrary, but always the same

Disagreements are still checked across every tier: a lower tier that differs
from the shown value flags it for review.

THE BENCHMARK'S OWN BOARD HAS THE FINAL WORD (Parvathi, 2026-10-28). A model a
tier-1 board listed and no longer lists - the board read correctly and we still
read it - is not filled from a lower tier: the cell goes blank, and the
changelog records it as dropped from that board (a retired or withdrawn model
is news). A lower tier fills only models the board has never listed. A board
that failed to load, or looked broken, keeps its previous values as before, so
it never blanks anything; nor does a source we no longer read.

Agreement margin: two values further apart than the column's
`agreement_margin` (benchmarks.yaml), or validation.yaml `tolerance` when the
column sets none, are a disagreement.

Pinned and fill overrides (rules 1 and 7) arrive with the phase-2 admin edits.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from collect.benchmarks.config import TIERS, Benchmark, Config
from collect.benchmarks.store import StoredCell, StoredObservation


@dataclass
class Decision:
    cell: StoredCell
    rule: str
    candidates: int
    flags: list[dict] = field(default_factory=list)


def accept_position(variant: str | None, accept: tuple[str | None, ...]) -> int | None:
    """Where this setup sits in the column's accept list; None = not accepted.

    "*" accepts any stated setup, for a column defined as "as the board ran it"
    (SWE-Bench Pro: each model under its own agent, recorded on the value).
    """
    for i, wanted in enumerate(accept):
        if wanted is None and variant is None:
            return i
        if wanted is not None and variant is not None and wanted.lower() == variant.lower():
            return i
    if "*" in accept and variant is not None:
        return accept.index("*")
    return None


def dedupe_source(
    observations: list[StoredObservation],
    benchmarks: dict[str, Benchmark],
    policies: dict[tuple[str, str, str], str],
) -> tuple[list[StoredObservation], list[dict], dict[str, int]]:
    """One observation per (row, benchmark, metric) for one source.

    `policies` carries a table's own `duplicates:` override per key.
    Returns kept observations, review items, and counts of how each key was decided.
    """
    groups: dict[tuple[str, str, str], list[StoredObservation]] = {}
    for o in observations:
        groups.setdefault(o.key, []).append(o)
    kept: list[StoredObservation] = []
    reviews: list[dict] = []
    counts = {
        "single": 0,
        "match_variant": 0,
        "latest": 0,
        "identical": 0,
        "ambiguous": 0,
        "setup_not_accepted": 0,
    }
    for key, group in groups.items():
        bench = benchmarks[key[1]]
        accepted = [o for o in group if accept_position(o.variant, bench.accept) is not None]
        if not accepted:
            counts["setup_not_accepted"] += 1
            continue
        best = min(accept_position(o.variant, bench.accept) for o in accepted)
        accepted = [o for o in accepted if accept_position(o.variant, bench.accept) == best]
        if len(accepted) == 1:
            kept.append(accepted[0])
            counts["single" if len(group) == 1 else "match_variant"] += 1
            continue
        values = {o.value for o in accepted}
        policy = policies.get(key) or bench.duplicates
        if len(values) == 1:
            kept.append(accepted[0])
            counts["identical"] += 1
            continue
        if policy == "latest":
            dated = sorted(accepted, key=lambda o: o.source_date or "", reverse=True)
            if dated[0].source_date and dated[0].source_date != (dated[1].source_date or ""):
                kept.append(dated[0])
                counts["latest"] += 1
                continue
        counts["ambiguous"] += 1
        listing = ", ".join(
            f"{o.raw_model_name}={o.raw_text}" + (f" [{o.variant}]" if o.variant else "")
            for o in accepted
        )
        reviews.append(
            {
                "check": "ambiguous_duplicate",
                "source_key": group[0].source_key,
                "row_id": key[0],
                "benchmark_key": key[1],
                "metric": key[2],
                "message": (
                    f"{len(accepted)} values for one cell and the {policy} rule "
                    f"cannot choose: {listing}"
                ),
            }
        )
    return kept, reviews, counts


def _tolerance(config: Config, bench: Benchmark, metric: str) -> float:
    tol = config.validation["tolerance"]
    if metric == "rank":
        return float(tol["rank"])
    if metric == "rating":
        return float(tol["rating"])
    if bench.agreement_margin is not None:
        return bench.agreement_margin
    return float(tol["percent"])


def merge(
    config: Config, observations: list[StoredObservation], *, run_id: int
) -> dict[tuple[str, str, str], Decision]:
    by_cell: dict[tuple[str, str, str], list[StoredObservation]] = {}
    for o in observations:
        bench = config.benchmarks.get(o.benchmark_key)
        if bench is None:
            continue  # a column no longer configured publishes nothing
        by_cell.setdefault(o.key, []).append(o)
    # A source no longer configured has only stale values; if one ever competes
    # it counts as the lowest tier, so it can never outrank a known source.
    tiers = {s.key: s.tier for s in config.sources}
    read = {s.key for s in config.sources if s.enabled}
    decisions: dict[tuple[str, str, str], Decision] = {}
    for key, group in by_cell.items():
        bench = config.benchmarks[key[1]]
        live = [o for o in group if not o.stale]  # rule 2
        positions = {id(o): accept_position(o.variant, bench.accept) for o in live}
        accepted = [o for o in live if positions[id(o)] is not None]  # rule 2
        if not accepted:
            continue
        if not any(tiers.get(o.source_key) == 1 for o in accepted) and dropped_by_board(
            group, bench, tiers, read
        ):
            continue  # the board's own word: blank, not a lower tier's value
        tier_of = {id(o): tiers.get(o.source_key, max(TIERS)) for o in accepted}
        top = min(tier_of.values())
        cands = [o for o in accepted if tier_of[id(o)] == top]  # rule 3
        best = min(positions[id(o)] for o in cands)
        by_setup = [o for o in cands if positions[id(o)] == best]  # rule 4
        winner, rule = _choose(by_setup)
        if rule == "single source":
            if len(cands) < len(accepted):
                rule = "rule 3 tier"
            elif len(by_setup) < len(cands):
                rule = "rule 4 setup"
        flags = []
        tolerance = _tolerance(config, bench, key[2])
        for o in accepted:
            # The same setup, however a board capitalises it ("Mini-SWE-agent" on
            # Vals, "mini-SWE-agent" on SWE-bench), as accept_position reads it.
            if o is winner or (o.variant or "").lower() != (winner.variant or "").lower():
                continue
            if key[2] == "rank" and (o.rank_board != winner.rank_board):
                continue
            # Rounded as the values are (2 decimals): 63.4 - 60.2 is not exactly
            # 3.2 in binary, and a gap at the margin must not hang on that.
            if round(abs(o.value - winner.value), 2) > tolerance:
                flags.append(
                    {
                        "check": "disagreement",
                        "row_id": key[0],
                        "benchmark_key": key[1],
                        "metric": key[2],
                        "source_key": o.source_key,
                        # Raw text as each source printed it, and the same value in
                        # one unit - the two are compared in that unit (0.587 = 58.7%).
                        "message": f"{winner.source_key} says {_both(winner)}, "
                        f"{o.source_key} says {_both(o)} "
                        f"(more than {tolerance:g} apart)",
                    }
                )
        decisions[key] = Decision(
            cell=StoredCell(
                row_id=key[0],
                benchmark_key=key[1],
                metric=key[2],
                value=winner.value,
                rank_high=winner.rank_high,
                tied=winner.tied,
                rank_out_of=winner.rank_out_of,
                rank_board=winner.rank_board,
                variant=winner.variant,
                benchmark_version=bench.benchmark_version,
                source_key=winner.source_key,
                url=winner.url,
                raw_text=winner.raw_text,
                raw_model_name=winner.raw_model_name,
                source_date=winner.source_date,
                setting_not_stated=winner.setting_not_stated,
                collected_at=winner.collected_at,
                needs_review=bool(flags),
                run_id=run_id,
            ),
            rule=rule,
            candidates=len(group),
            flags=flags,
        )
    return decisions


def dropped_by_board(
    group: list[StoredObservation],
    bench: Benchmark,
    tiers: dict[str, int],
    read: set[str],
) -> bool:
    """A tier-1 board listed this cell and no longer does: its value is stale
    (the board was read correctly and the model was gone), the board is still
    one we read, and the value was one the column accepts."""
    return any(
        o.stale
        and tiers.get(o.source_key) == 1
        and o.source_key in read
        and accept_position(o.variant, bench.accept) is not None
        for o in group
    )


def _choose(cands: list[StoredObservation]) -> tuple[StoredObservation, str]:
    """Rules 5-7, each applied only to what the one before left tied."""
    if len(cands) == 1:
        return cands[0], "single source"
    top = max(o.priority for o in cands)
    left = [o for o in cands if o.priority == top]
    if len(left) == 1:
        return left[0], "rule 5 priority"
    newest = max((o.source_date or "", o.collected_at) for o in left)
    recent = [o for o in left if (o.source_date or "", o.collected_at) == newest]
    if len(recent) == 1:
        return recent[0], "rule 6 recency"
    return min(recent, key=lambda o: o.source_key), "rule 7 tie-break"


def _both(o: StoredObservation) -> str:
    """'0.587 (= 58.7)' when the raw text is not already the compared number."""
    shown = f"{o.value:g}"
    raw = (o.raw_text or "").strip()
    return raw if raw.rstrip("%") == shown else f"{raw} (= {shown})"
