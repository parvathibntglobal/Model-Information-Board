"""Two Admin read-outs built from what each fetch already records per thread.

Both read `fetch_log` rows of kind `thread`, which a fetch writes once per
thread it sends to the model. Nothing here writes, and nothing calls a model.

1. BILLED COST PER RUN (Admin -> API usage). `usd` on a thread record is our
   estimate: tokens times a configured price. `reported_costs` is what the
   provider said it billed, per call (#381). They differ, because the price
   depends on which upstream served the call and how much of the prompt was
   cached. Shown side by side, per run, with the upstreams that served it - a
   run that moved between upstreams cannot have kept a warm prompt cache.

   CACHED TOKENS ARE NOT IN THESE RECORDS. `cached_input_tokens` is read per
   call (judge/extract/client.py) but was never written to the thread record,
   so a cache hit rate for past runs cannot be computed. Said, not estimated
   (rule 6).

2. LOST CLAIMS PER RUN (Admin -> Runs). `unsalvaged_by_error` is written per
   thread since 2026-09-23 (3003341): each validation error a proposed claim
   failed, folded to its shape, with a count. Runs from before then carry only
   the total, and are labelled so rather than shown as clean.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

#: How many recent runs each read-out lists.
RUNS = 20


def _model_names(conn: Any, ids: set[str]) -> dict[str, str]:
    if not ids:
        return {}
    rows = conn.execute(
        "SELECT id, coalesce(display_name, canonical_id, id) FROM model_version "
        "WHERE id = ANY(%s) OR canonical_id = ANY(%s)",
        (list(ids), list(ids)),
    ).fetchall()
    names = {}
    for row_id, name in rows:
        names[row_id] = name
    return names


def billed_cost(conn: Any, *, runs: int = RUNS) -> dict:
    """Billed against estimated cost, per recent run, from the thread records."""
    rows = conn.execute(
        """
        SELECT run_id, model_version_id, min(at), count(*),
               sum((SELECT coalesce(sum(x::numeric), 0)
                    FROM jsonb_array_elements_text(
                        CASE WHEN jsonb_typeof(payload->'reported_costs') = 'array'
                             THEN payload->'reported_costs' ELSE '[]'::jsonb END) x)),
               count(*) FILTER (WHERE jsonb_typeof(payload->'reported_costs') <> 'array'
                                 OR jsonb_array_length(payload->'reported_costs') = 0),
               sum((payload->>'usd')::numeric),
               sum((payload->>'tokens_in')::bigint),
               sum((payload->>'tokens_out')::bigint),
               array_agg(payload->'upstreams' ORDER BY seq)
        FROM fetch_log
        WHERE kind = 'thread'
        GROUP BY run_id, model_version_id
        ORDER BY min(at) DESC
        LIMIT %s
        """,
        (runs,),
    ).fetchall()
    names = _model_names(conn, {r[1] for r in rows if r[1]})
    out = []
    for (run_id, mv, started, threads, billed, unbilled, est, tin, tout, ups) in rows:
        served: list[str] = []
        switches = 0
        last = None
        for u in ups or []:
            for name in (u or []):
                if name not in served:
                    served.append(name)
                if last is not None and name != last:
                    switches += 1
                last = name
        out.append({
            "run_id": run_id,
            "model": names.get(mv, mv),
            "started_at": started.isoformat() if started else None,
            "threads": threads,
            "billed_usd": float(billed) if billed is not None else None,
            "threads_without_billed_cost": unbilled,
            "estimated_usd": float(est) if est is not None else None,
            "tokens_in": int(tin) if tin is not None else None,
            "tokens_out": int(tout) if tout is not None else None,
            "upstreams": served,
            "upstream_switches": switches,
        })
    total_billed = sum(r["billed_usd"] or 0 for r in out)
    total_est = sum(r["estimated_usd"] or 0 for r in out)
    return {
        "runs": out,
        "totals": {"billed_usd": total_billed, "estimated_usd": total_est, "runs": len(out)},
        "cache": {
            "recorded": False,
            "why": "cached input tokens are read per call but were never written to the "
                   "thread records, so a cache hit rate for these runs cannot be computed",
        },
    }


def lost_claims(conn: Any, *, runs: int = RUNS) -> dict:
    """Claims a run's model proposed but that failed validation, by error shape."""
    rows = conn.execute(
        """
        SELECT run_id, model_version_id, min(at), count(*),
               sum(coalesce((payload->>'verified')::int, 0)),
               sum(coalesce((payload->>'rejected')::int, 0)),
               sum(coalesce((payload->>'unsalvaged')::int, 0)),
               bool_or(payload ? 'unsalvaged_by_error'),
               array_agg(payload->'unsalvaged_by_error')
                   FILTER (WHERE payload ? 'unsalvaged_by_error')
        FROM fetch_log
        WHERE kind = 'thread'
        GROUP BY run_id, model_version_id
        ORDER BY min(at) DESC
        LIMIT %s
        """,
        (runs,),
    ).fetchall()
    names = _model_names(conn, {r[1] for r in rows if r[1]})
    out = []
    overall: Counter = Counter()
    for (run_id, mv, started, threads, verified, rejected, lost, has_shapes, shapes) in rows:
        by_error: Counter = Counter()
        for s in shapes or []:
            for k, v in (s or {}).items():
                by_error[k] += int(v)
        overall.update(by_error)
        out.append({
            "run_id": run_id,
            "model": names.get(mv, mv),
            "started_at": started.isoformat() if started else None,
            "threads": threads,
            "verified": verified,
            "rejected": rejected,
            "lost": lost,
            "reasons_recorded": bool(has_shapes) or lost == 0,
            "by_error": dict(by_error.most_common()),
        })
    return {"runs": out, "by_error": dict(overall.most_common())}
