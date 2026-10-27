"""Stage 9: previous cells vs new cells -> changelog entries (doc 12).

    empty -> value                      added
    value -> empty                      removed
    value -> other value, same source   updated  (score/rating diff >= 0.01, any rank change)
    value -> value from another source  source_changed
    same value, same source             nothing

`direction` is worked out here so the page never has to know that a lower
rank is better: better | worse | same.
"""

from __future__ import annotations

from typing import Any

from collect.benchmarks.config import Config
from collect.benchmarks.store import StoredCell


def direction(
    config: Config, benchmark_key: str, metric: str, old: float | None, new: float | None
) -> str | None:
    if old is None or new is None:
        return None
    if old == new:
        return "same"
    if metric == "rank":
        return "better" if new < old else "worse"
    higher = config.benchmarks[benchmark_key].higher_is_better
    return "better" if (new > old) == higher else "worse"


def diff(
    config: Config,
    previous: dict[tuple[str, str, str], StoredCell],
    current: dict[tuple[str, str, str], StoredCell],
    *,
    reason: str,
    actor: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key in sorted(set(previous) | set(current)):
        old, new = previous.get(key), current.get(key)
        row_id, benchmark_key, metric = key
        base = {
            "row_id": row_id,
            "benchmark_key": benchmark_key,
            "metric": metric,
            "reason": reason,
            "actor": actor,
        }
        if old is None and new is not None:
            out.append(
                {
                    **base,
                    "change_type": "added",
                    "new_value": new.value,
                    "new_raw": new.raw_text,
                    "new_source": new.source_key,
                    "rank_out_of_new": new.rank_out_of,
                    "source_date": new.source_date,
                    "needs_review": new.needs_review,
                }
            )
        elif old is not None and new is None:
            out.append(
                {
                    **base,
                    "change_type": "removed",
                    "old_value": old.value,
                    "old_raw": old.raw_text,
                    "old_source": old.source_key,
                    "rank_out_of_old": old.rank_out_of,
                }
            )
        elif old is not None and new is not None:
            moved = (
                (old.value != new.value) if metric == "rank" else abs(old.value - new.value) >= 0.01
            )
            if old.source_key != new.source_key:
                change_type = "source_changed"
            elif moved:
                change_type = "updated"
            else:
                continue
            out.append(
                {
                    **base,
                    "change_type": change_type,
                    "old_value": old.value,
                    "new_value": new.value,
                    "old_raw": old.raw_text,
                    "new_raw": new.raw_text,
                    "old_source": old.source_key,
                    "new_source": new.source_key,
                    "rank_out_of_old": old.rank_out_of,
                    "rank_out_of_new": new.rank_out_of,
                    "source_date": new.source_date,
                    "direction": direction(config, benchmark_key, metric, old.value, new.value),
                    "needs_review": new.needs_review,
                }
            )
    return out
