"""The Benchmarks page (signed in): read the `bench_` tables, start a run.

`collect/benchmarks/` writes these tables; this module only reads them, and
never imports collect (the lane rule) - a run is started as a background
process, `python -m collect.cli benchmarks run`, the way /fetch/start starts
scripts/fetch_model.py. The run never executes inside the web request.

Values are shown RAW (Parvathi, 2026-10-22): each cell is `raw_text`, exactly
as the source printed it ("88.0", "0.9577", "1"), with its source, link and
date. No unit is added, nothing is rounded, and nothing here computes a rank, a
percentile or a score. The one-unit `value` the run stores for its checks is
not sent to the page.

WHICH DATABASE. `BENCHMARKS_DATABASE_URL` when set, else `DATABASE_URL`.
While the page is a local build it reads and writes the local database, and
the Run button refuses a target that is not on this machine.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "contract" / "benchmarks"
TRACKED_MODELS = REPO_ROOT / "contract" / "tracked_models.yaml"
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")

#: The order setting rows are listed under their model.
SETTING_ORDER = (
    "max",
    "xhigh",
    "high",
    "medium",
    "low",
    "minimal",
    "none",
    "thinking",
    "120k-max",
    "120k-high",
    "120k-medium",
    "120k-low",
    "thinking-64k",
    "thinking-32k",
    "thinking-16k",
    "thinking-8k",
    "thinking-1k",
    "reasoning-beta",
    "refinement",
)
#: A change this recent carries the `new` / `changed` badge (doc 25.3).
RECENT_DAYS = 7
LOG_TAIL_BYTES = 200_000


class BenchmarksUnavailable(RuntimeError):
    """No database, or the bench_ tables are not migrated there."""


class RunRefused(RuntimeError):
    pass


def database_url() -> str | None:
    return os.environ.get("BENCHMARKS_DATABASE_URL") or os.environ.get("DATABASE_URL")


def is_local(dsn: str | None) -> bool:
    if not dsn:
        return False
    host = urlparse(dsn).hostname
    return host in LOCAL_HOSTS or host is None


@contextmanager
def connection():
    import psycopg

    dsn = database_url()
    if not dsn:
        raise BenchmarksUnavailable(
            "no database is configured (BENCHMARKS_DATABASE_URL / DATABASE_URL)"
        )
    try:
        conn = psycopg.connect(dsn, connect_timeout=5)
    except psycopg.Error as error:
        raise BenchmarksUnavailable(
            f"the benchmarks database is not reachable: {type(error).__name__}"
        ) from error
    try:
        exists = conn.execute("SELECT to_regclass('public.bench_cell') IS NOT NULL").fetchone()[0]
        if not exists:
            raise BenchmarksUnavailable(
                "the bench_ tables are not in this database yet - apply "
                "contract/migrations/20261022T1200_bench_tables.sql"
            )
        yield conn
        conn.commit()
    finally:
        conn.close()


def _yaml(name: str) -> Any:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def _seeds() -> list[dict[str, str]]:
    raw = yaml.safe_load(TRACKED_MODELS.read_text(encoding="utf-8"))
    return [
        {"id": m["registry"], "name": m["name"]}
        for m in raw["models"]
        if m.get("kind") == "text" and m.get("registry")
    ]


def _columns() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    raw = _yaml("benchmarks.yaml")
    benches = sorted(
        (b for b in raw["benchmarks"] if b.get("status", "active") == "active"),
        key=lambda b: (b["category"], b["order"]),
    )
    sections = []
    by_key: dict[str, dict[str, Any]] = {}
    for cat in sorted(raw["categories"], key=lambda c: c["order"]):
        columns = []
        for b in (x for x in benches if x["category"] == cat["key"]):
            for metric in b["metrics"]:
                column = {
                    "key": f"{b['key']}_{metric}",
                    "benchmark": b["key"],
                    "label": b["label"] if metric == "score" else f"{b['label']} {metric}",
                    "metric": metric,
                    "unit": "percent" if metric == "score" else None,
                    "better": "lower"
                    if metric == "rank"
                    else ("higher" if b["higher_is_better"] else "lower"),
                    "volatility": b["volatility"],
                    "benchmark_version": b.get("benchmark_version"),
                }
                columns.append(column)
                by_key[column["key"]] = column
        if columns:
            sections.append({"key": cat["key"], "label": cat["label"], "columns": columns})
    return sections, by_key


def _sources() -> dict[str, dict[str, Any]]:
    return {s["key"]: s for s in _yaml("sources.yaml")["sources"]}


# ── the table ────────────────────────────────────────────────────────────────


def table(conn) -> dict[str, Any]:
    sections, columns = _columns()
    sources = _sources()
    seeds = _seeds()
    rows = conn.execute(
        "SELECT row_id, host_model_id, setting, dated, display_label FROM bench_row"
    ).fetchall()
    # Under each model: its setting rows, then each dated release (with its own
    # setting rows after it). The model's own row is never a dated one.
    settings_by_model: dict[str, list[tuple[str, str | None, str, str | None]]] = {}
    base_labels: dict[str, str] = {}
    for row_id, model_id, setting, dated, label in rows:
        if setting or dated:
            settings_by_model.setdefault(model_id, []).append((row_id, setting, label, dated))
        else:
            base_labels[model_id] = label

    cells: dict[str, dict[str, Any]] = {}
    used_sources: set[str] = set()
    for (
        row_id,
        benchmark_key,
        metric,
        rank_high,
        tied,
        rank_out_of,
        rank_board,
        variant,
        benchmark_version,
        source_key,
        url,
        raw_text,
        raw_model_name,
        source_date,
        setting_not_stated,
        collected_at,
        needs_review,
    ) in conn.execute(
        "SELECT row_id, benchmark_key, metric, rank_high, tied, rank_out_of, rank_board, "
        "variant, benchmark_version, source_key, url, raw_text, raw_model_name, source_date, "
        "setting_not_stated, collected_at, needs_review FROM bench_cell"
    ).fetchall():
        key = f"{benchmark_key}_{metric}"
        if key not in columns:
            continue
        used_sources.add(source_key)
        source = sources.get(source_key, {})
        cells.setdefault(row_id, {})[key] = {
            "display": raw_text,
            "tied": tied,
            "rank_high": rank_high,
            "source": source_key,
            "source_label": source.get("label", source_key),
            "url": url,
            "variant": variant,
            "benchmark_version": benchmark_version,
            "raw_text": raw_text,
            "raw_name": raw_model_name,
            "source_date": source_date,
            "collected_at": collected_at.isoformat() if collected_at else None,
            "rank_out_of": rank_out_of,
            "rank_board": rank_board,
            "setting_not_stated": setting_not_stated,
            "needs_review": needs_review,
            "badges": [],
        }

    since = datetime.now(UTC) - timedelta(days=RECENT_DAYS)
    first_run = conn.execute(
        "SELECT min(id) FROM bench_run WHERE NOT dry_run AND status <> 'running'"
    ).fetchone()[0]
    for row_id, benchmark_key, metric, change_type, direction, run_id in conn.execute(
        "SELECT row_id, benchmark_key, metric, change_type, direction, run_id FROM bench_change "
        "WHERE changed_at >= %s AND change_type IN ('added', 'updated', 'source_changed') "
        "ORDER BY id",
        (since,),
    ).fetchall():
        cell = cells.get(row_id, {}).get(f"{benchmark_key}_{metric}")
        if cell is None or run_id == first_run:
            continue  # the first import is not "new" (doc 12: collapse it)
        badge = "new" if change_type == "added" else "changed"
        cell["badges"] = [b for b in cell["badges"] if b not in ("new", "changed")] + [badge]
        if direction in ("better", "worse"):
            cell["direction"] = direction

    def ordered(entries):
        def key(e):
            setting, dated = e[1], e[3]
            rank = (
                -1
                if setting is None
                else (SETTING_ORDER.index(setting) if setting in SETTING_ORDER else 99)
            )
            return (dated is not None, dated or "", rank)

        return sorted(entries, key=key)

    def model_row(model_id: str, label: str, group: str) -> dict[str, Any]:
        # A setting or dated row with no value is not shown (the run removes
        # such rows too; this keeps the page right between runs).
        children = [
            {
                "row_id": row_id,
                "label": label,
                "setting": setting,
                "dated": dated,
                "cells": cells.get(row_id, {}),
            }
            for row_id, setting, label, dated in ordered(settings_by_model.get(model_id, []))
            if cells.get(row_id)
        ]
        return {
            "row_id": model_id,
            "label": label,
            "model_id": model_id,
            "group": group,
            "cells": cells.get(model_id, {}),
            "children": children,
        }

    # The tracked models, in contract order, every one shown; then registry models
    # a source listed (rows exist only once matched), by name. A registry row with
    # no value left is not shown.
    out_rows = [model_row(seed["id"], seed["name"], "tracked") for seed in seeds]
    tracked_ids = {seed["id"] for seed in seeds}
    for model_id, label in sorted(base_labels.items(), key=lambda kv: kv[1].lower()):
        if model_id in tracked_ids:
            continue
        row = model_row(model_id, label, "registry")
        if row["cells"] or any(child["cells"] for child in row["children"]):
            out_rows.append(row)

    filled = sum(len(c) for c in cells.values())
    return {
        "sections": sections,
        "rows": out_rows,
        "last_run": _last_run(conn),
        # Attribution and licence live on the Sources tab only (2026-10-26);
        # `in_table` there marks the sources whose values the table shows.
        "sources": _sources_view(conn, sources, columns, used_sources),
        "counts": {
            "models": len(seeds),
            "registry_models": sum(r["group"] == "registry" for r in out_rows),
            "benchmarks": len({c["benchmark"] for c in columns.values()}),
            "setting_rows": sum(len(r["children"]) for r in out_rows),
            "filled_cells": filled,
            "columns": len(columns),
            # Sources with a saved copy: "Re-parse saved pages" needs at least one.
            "saved_pages": _saved_pages(conn),
        },
    }


def _saved_pages(conn) -> int:
    return conn.execute("SELECT count(DISTINCT source_key) FROM bench_snapshot").fetchone()[0]


#: How each method fetches, in words for the Sources tab. The libraries are the
#: ones collect/benchmarks/fetch.py and parse.py use.
FETCHERS = {
    "static": "Plain HTTP request (httpx, identifying User-Agent, robots.txt checked first)",
    "browser": "Headless browser (Playwright Chromium, same User-Agent, robots.txt checked first)",
    "data_file": "Download of a file the site offers (only while allow_data_files is on)",
}
READERS = {
    "html_table": "HTML table (BeautifulSoup + lxml)",
    "embedded_json": "Data block inside the page (<script> JSON)",
    "next_flight": "Data inside the page (Next.js page data)",
    "zip_csv": "CSV files inside a zip",
}


def _sources_view(
    conn,
    sources: dict[str, dict[str, Any]],
    columns: dict[str, dict[str, Any]],
    used: set[str],
):
    """Every configured source: its link, how it is fetched and read, what it fills,
    and what the last published run got from it."""
    allow_data_files = bool(_yaml("module_settings.yaml").get("allow_data_files"))
    last: dict[str, dict[str, Any]] = {}
    for run_id, finished, report in conn.execute(
        "SELECT id, finished_at, report FROM bench_run WHERE NOT dry_run AND status <> 'running' "
        "AND report IS NOT NULL ORDER BY id DESC LIMIT 30"
    ).fetchall():
        for key, entry in ((report or {}).get("sources") or {}).items():
            last.setdefault(key, {**entry, "run_id": run_id, "at": _iso(finished)})
    out = []
    for s in sources.values():
        fills, readers = [], []
        for table in s.get("tables") or []:
            readers.append(READERS.get(table["locate"]["type"], table["locate"]["type"]))
            targets = [f"{v['benchmark']}_{v['metric']}" for v in table["benchmark_map"].values()]
            if table.get("rank"):
                targets.append(f"{table['rank']['benchmark']}_rank")
            for c in targets:
                if c in columns and columns[c]["label"] not in fills:
                    fills.append(columns[c]["label"])
        if not s["enabled"]:
            state, why = "disabled", s.get("why_disabled")
        elif s["method"] == "data_file" and not allow_data_files:
            state, why = "skipped", "A data file, and allow_data_files is off (scraping only)."
        else:
            state, why = "enabled", None
        seen = last.get(s["key"])
        out.append(
            {
                "key": s["key"],
                "label": s["label"],
                "url": s.get("page_url") or s["url"],
                "state": state,
                "why": why,
                "kind": s["kind"],
                "priority": s["priority"],
                "fetcher": FETCHERS.get(s["method"], s["method"]),
                "readers": sorted(set(readers)),
                "fills": fills,
                "attribution": s.get("attribution"),
                "license": s.get("license"),
                "in_table": s["key"] in used,
                "last": None
                if seen is None
                else {
                    "run_id": seen["run_id"],
                    "at": seen["at"],
                    "status": seen.get("status"),
                    "http_status": seen.get("http_status"),
                    "rows": seen.get("rows_parsed"),
                    "values": seen.get("observations"),
                    "matched": seen.get("matched_names"),
                    "error": (seen.get("errors") or [None])[0],
                },
            }
        )
    return out


def _last_run(conn) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, status, started_at, finished_at FROM bench_run WHERE NOT dry_run "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return {"id": row[0], "status": row[1], "started_at": _iso(row[2]), "finished_at": _iso(row[3])}


def _iso(value) -> str | None:
    return value.isoformat() if value else None


# ── changelog and runs ───────────────────────────────────────────────────────


def changelog(conn, *, limit: int = 300, run_id: int | None = None) -> dict[str, Any]:
    _, columns = _columns()
    labels = {
        r[0]: r[1] for r in conn.execute("SELECT row_id, display_label FROM bench_row").fetchall()
    }
    names = {s["id"]: s["name"] for s in _seeds()}
    where, params = "", []
    if run_id is not None:
        where, params = "WHERE c.run_id = %s", [run_id]
    rows = conn.execute(
        "SELECT c.id, c.run_id, c.changed_at, c.row_id, c.benchmark_key, c.metric, c.change_type, "
        "c.old_raw, c.new_raw, c.old_source, c.new_source, "
        "c.direction, c.reason, c.actor, c.note, c.needs_review, r.dry_run "
        f"FROM bench_change c JOIN bench_run r ON r.id = c.run_id {where} "
        "ORDER BY c.id DESC LIMIT %s",
        (*params, limit),
    ).fetchall()
    entries = []
    for (
        cid,
        rid,
        at,
        row_id,
        bench,
        metric,
        kind,
        old,
        new,
        old_src,
        new_src,
        direction,
        reason,
        actor,
        note,
        needs_review,
        _dry,
    ) in rows:
        column = columns.get(f"{bench}_{metric}") if bench else None
        entries.append(
            {
                "id": cid,
                "run_id": rid,
                "changed_at": _iso(at),
                "row": labels.get(row_id) or names.get(row_id) or row_id,
                "column": column["label"] if column else None,
                "type": kind,
                "old": old,
                "new": new,
                "old_source": old_src,
                "new_source": new_src,
                "direction": direction,
                "reason": reason,
                "actor": actor,
                "note": note,
                "needs_review": needs_review,
            }
        )
    total = conn.execute("SELECT count(*) FROM bench_change").fetchone()[0]
    return {"entries": entries, "total": total}


def runs(conn, *, limit: int = 30) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT id, request_id, trigger, scope, dry_run, status, started_at, finished_at, report "
        "FROM bench_run ORDER BY id DESC LIMIT %s",
        (limit,),
    ).fetchall()
    return {"runs": [_run_summary(r) for r in rows], "running": _running(conn)}


def _run_summary(r) -> dict[str, Any]:
    rid, request_id, trigger, scope, dry_run, status, started, finished, report = r
    report = report or {}
    return {
        "id": rid,
        "request_id": request_id,
        "trigger": trigger,
        "scope": scope,
        "dry_run": dry_run,
        "status": status,
        "started_at": _iso(started),
        "finished_at": _iso(finished),
        "totals": report.get("totals"),
        "sources": {
            k: {
                "status": v.get("status"),
                "method": v.get("method"),
                "observations": v.get("observations"),
                "errors": v.get("errors"),
            }
            for k, v in (report.get("sources") or {}).items()
        },
        "coverage": report.get("coverage"),
        "error": report.get("error"),
    }


def _running(conn) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, request_id, started_at FROM bench_run WHERE status = 'running' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return {"id": row[0], "request_id": row[1], "started_at": _iso(row[2])} if row else None


def _log_dir() -> Path:
    return REPO_ROOT / _yaml("module_settings.yaml")["log_dir"]


def run_detail(conn, *, run_id: int | None = None, request_id: str | None = None) -> dict[str, Any]:
    """One run and its terminal output - live from the log file while it runs."""
    if run_id is not None:
        where, param = "id = %s", run_id
    else:
        where, param = "request_id = %s", request_id
    row = conn.execute(
        "SELECT id, request_id, trigger, scope, dry_run, status, started_at, finished_at, "
        "report, log_text "
        f"FROM bench_run WHERE {where} ORDER BY id DESC LIMIT 1",
        (param,),
    ).fetchone()
    if row is None:
        return {"found": False, "done": False, "log": "", "run": None}
    summary = _run_summary(row[:9])
    log_text = row[9] or ""
    # The same name collect/benchmarks/store.py log_file_name() gives the file.
    path = _log_dir() / f"run_{row[0]}_{row[6].astimezone(UTC):%Y%m%dT%H%M%S}.log"
    if row[5] == "running" and path.exists():
        data = path.read_bytes()[-LOG_TAIL_BYTES:]
        log_text = data.decode("utf-8", "replace")
    return {"found": True, "done": row[5] != "running", "run": summary, "log": log_text}


def unmatched(conn, *, limit: int = 300) -> dict[str, Any]:
    """Names of REGISTRY models the sources' latest reads listed and no row took.

    Only models in the registry are considered (Parvathi, 2026-10-26): a name
    whose model is not in the registry is not listed. So a group here is either
    a name very close to a registry name (similar_to: same numbers, only filler
    words like "Claude" or "Instruct" differ) for a person to confirm, or a known
    model whose setting or date could not be read - grouped by the name without
    its setting or date, with every source that listed it.
    """
    groups: dict[str, dict[str, Any]] = {}
    for source, raw, reason, base_name, base_key, similar_to, seen in conn.execute(
        "SELECT source_key, raw_name, reason, base_name, base_key, similar_to, seen_count "
        "FROM bench_unmatched WHERE reason <> 'unmatched'"
    ).fetchall():
        key = base_key or raw.lower()
        g = groups.setdefault(
            key,
            {
                "key": key,
                "name": base_name or raw,
                "raw_names": set(),
                "sources": set(),
                "reasons": set(),
                "similar_to": set(),
                "seen": 0,
            },
        )
        g["similar_to"].update(similar_to or ())
        g["raw_names"].add(raw)
        g["sources"].add(source)
        g["reasons"].add(reason)
        g["seen"] += seen
    decided = {
        key: {
            "key": key,
            "name": name,
            "action": action,
            "target": target,
            "actor": actor,
            "at": _iso(at),
        }
        for key, name, action, target, actor, at in conn.execute(
            "SELECT name_key, name, action, target_model_id, actor, created_at "
            "FROM bench_name_decision ORDER BY created_at DESC"
        ).fetchall()
    }
    targets = decision_targets(conn)
    names = {t["id"]: t["name"] for t in targets}
    ordered = sorted(
        (g for g in groups.values() if g["key"] not in decided),
        key=lambda g: (-len(g["sources"]), -g["seen"], g["name"].lower()),
    )
    return {
        "total": len(ordered),
        "groups": [
            {
                "key": g["key"],
                "name": g["name"],
                "raw_names": sorted(g["raw_names"])[:8],
                "sources": sorted(g["sources"]),
                "reasons": sorted(g["reasons"]),
                "similar_to": [{"id": i, "name": names.get(i, i)} for i in sorted(g["similar_to"])],
                # Only a name no model took can be decided; an unknown setting
                # word belongs to a known model and is a vocabulary question.
                "decidable": "similar_to_registry" in g["reasons"],
                "seen": g["seen"],
            }
            for g in ordered[:limit]
        ],
        "decisions": list(decided.values()),
        "targets": targets,
    }


def decision_targets(conn) -> list[dict[str, str]]:
    """The models "Same model as ..." may name: tracked first, then the registry."""
    out = [{"id": s["id"], "name": s["name"], "group": "tracked"} for s in _seeds()]
    tracked = {s["id"] for s in out}
    try:
        rows = conn.execute(
            "SELECT DISTINCT canonical_id, display_name FROM model_version ORDER BY 1"
        ).fetchall()
    except Exception:  # noqa: BLE001 - no registry table here: tracked models only
        conn.rollback()
        rows = []
    seen: set[str] = set()
    for model_id, name in rows:
        if model_id and model_id not in tracked and model_id not in seen:
            seen.add(model_id)
            out.append(
                {"id": model_id, "name": (name or model_id).split(": ", 1)[-1], "group": "registry"}
            )
    return out


#: "new_row" is no longer offered: only registry models get rows (2026-10-26).
ACTIONS = ("alias", "ignore")


class DecisionRefused(ValueError):
    pass


def decide(
    conn, *, key: str, name: str, action: str, target: str | None, actor: str = "admin"
) -> dict[str, Any]:
    """Record a person's decision about one unmatched name (replaces an earlier one)."""
    key, name = (key or "").strip(), (name or "").strip()
    if not key or not name:
        raise DecisionRefused("a name is required")
    if action not in ACTIONS:
        raise DecisionRefused(f"action must be one of {list(ACTIONS)}")
    if action == "alias":
        if not target or target not in {t["id"] for t in decision_targets(conn)}:
            raise DecisionRefused("choose a tracked or registry model this name is the same as")
    else:
        target = None
    conn.execute(
        "INSERT INTO bench_name_decision (name_key, name, action, target_model_id, actor) "
        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (name_key) DO UPDATE SET "
        "name = EXCLUDED.name, action = EXCLUDED.action, "
        "target_model_id = EXCLUDED.target_model_id, actor = EXCLUDED.actor, created_at = now()",
        (key, name, action, target, actor),
    )
    return {
        "key": key,
        "action": action,
        "target": target,
        "applies": "on the next run, or Re-parse saved pages",
    }


def undo_decision(conn, *, key: str) -> dict[str, Any]:
    gone = conn.execute(
        "DELETE FROM bench_name_decision WHERE name_key = %s RETURNING name_key", (key,)
    ).fetchone()
    return {"key": key, "undone": gone is not None}


def review_items(conn, *, limit: int = 200) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT id, run_id, check_code, severity, source_key, row_id, benchmark_key, metric, "
        "message, "
        "status, created_at FROM bench_review_item WHERE status = 'open' ORDER BY id DESC LIMIT %s",
        (limit,),
    ).fetchall()
    return {
        "items": [
            {
                "id": i,
                "run_id": r,
                "check": c,
                "severity": sev,
                "source": s,
                "row": row,
                "column": f"{b}_{m}" if b else None,
                "message": msg,
                "status": st,
                "created_at": _iso(at),
            }
            for i, r, c, sev, s, row, b, m, msg, st, at in rows
        ]
    }


# ── starting a run ───────────────────────────────────────────────────────────


def start_run(conn, *, dry_run: bool, use_snapshot: bool) -> dict[str, Any]:
    """Spawn the run in the background and return the id the page polls by."""
    dsn = database_url()
    if not is_local(dsn):
        raise RunRefused(
            "runs are local-only while the Benchmarks page is being built: "
            "the benchmarks database is not on this machine"
        )
    running = _running(conn)
    if running is not None:
        raise RunRefused(f"run #{running['id']} is still running (one run at a time)")
    if use_snapshot and not _saved_pages(conn):
        raise RunRefused(
            "no page has been saved yet, so there is nothing to re-parse - "
            "make a real run first (Run now)"
        )
    request_id = uuid.uuid4().hex[:12]
    command = [
        sys.executable,
        "-m",
        "collect.cli",
        "benchmarks",
        "run",
        "--trigger",
        "page_button",
        "--request-id",
        request_id,
        "--actor",
        "admin",
    ]
    if dry_run:
        command.append("--dry-run")
    if use_snapshot:
        command.append("--use-snapshot")
    env = os.environ.copy()
    env["DATABASE_URL"] = dsn
    env.setdefault("PYTHONIOENCODING", "utf-8")
    # Inherited streams, detached, nothing read back - the run prints to the
    # backend's console and to its own log file, as /fetch/start does.
    subprocess.Popen(command, cwd=str(REPO_ROOT), env=env)
    return {"request_id": request_id, "dry_run": dry_run, "use_snapshot": use_snapshot}
