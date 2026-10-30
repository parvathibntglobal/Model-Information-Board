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

SCORES IN ONE STYLE (Parvathi, 2026-10-27). Every score is a percentage, so a
score shows as its stored percent value with up to two decimals and no "%":
"0.876878612716763" -> 87.69, "75.80%" -> 75.8, "69.0" -> 69. Nothing else is
converted: ranks and ratings show as printed. The hover keeps the source's own
text whenever it differs. See shown().

SOURCE TIERS (2026-10-27). Each cell shows the value of the highest-tier source
that has one (collect/benchmarks/merge.py); its hover names the tier and what
the other sources say for the same cell.

WHICH DATABASE. `BENCHMARKS_DATABASE_URL` when set, else `DATABASE_URL`.
The Run button and the name decisions write wherever the board may write
(judge/writeguard.check): the local database, or any database when ENVIRONMENT
is not development - so they work on the production site. A run there reads
the sources that need no browser; the scheduled runs (.github/workflows/
benchmarks.yml) read all of them.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from psycopg import errors

from judge import writeguard
from judge.writeguard import is_local as writeguard_is_local

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "contract" / "benchmarks"
TRACKED_MODELS = REPO_ROOT / "contract" / "tracked_models.yaml"

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
# What each tier means, for the page (collect/benchmarks/config.py TIERS -
# the same words; the judge does not import collect).
TIERS = {
    1: "the benchmark's own leaderboard",
    2: "a reputed independent evaluator",
    3: "another third party",
}
LOG_TAIL_BYTES = 200_000


class BenchmarksUnavailable(RuntimeError):
    """No database, or the bench_ tables are not migrated there."""


class RunRefused(RuntimeError):
    pass


def database_url() -> str | None:
    return os.environ.get("BENCHMARKS_DATABASE_URL") or os.environ.get("DATABASE_URL")


def is_local(dsn: str | None) -> bool:
    """The board's own check (judge/writeguard.py): only a postgres URL naming
    this machine is local. A keyword DSN ("host=... dbname=...") or anything
    else unreadable counts as REMOTE - it used to count as local when it had no
    URL hostname, which unlocked runs against Railway (PR #573 review)."""
    return bool(dsn) and writeguard_is_local(dsn)


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
        raw["benchmarks"],
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
                    "better": "lower"
                    if metric == "rank"
                    else ("higher" if b["higher_is_better"] else "lower"),
                    "volatility": b["volatility"],
                    "benchmark_version": b.get("benchmark_version"),
                    # What a reader must know before comparing the column's values,
                    # e.g. that each was run in its own agent (PR #580 review).
                    "setup_note": b.get("setup_note"),
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
        value,
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
        "SELECT row_id, benchmark_key, metric, value, tied, rank_out_of, rank_board, "
        "variant, benchmark_version, source_key, url, raw_text, raw_model_name, source_date, "
        "setting_not_stated, collected_at, needs_review FROM bench_cell"
    ).fetchall():
        key = f"{benchmark_key}_{metric}"
        if key not in columns:
            continue
        used_sources.add(source_key)
        source = sources.get(source_key, {})
        display = shown(raw_text, value, metric)
        cells.setdefault(row_id, {})[key] = {
            "display": display,
            # The source's own text when `display` is not exactly it (shown()).
            "rounded_from": raw_text if display != raw_text else None,
            "tier": source.get("tier"),
            "tier_label": TIERS.get(source.get("tier")),
            # The value in one unit (0.912 and 91.2% are both 91.2): for SORTING a
            # column only - the page always shows `display` (2026-10-26).
            "sort": value,
            "tied": tied,
            "source": source_key,
            "source_label": source.get("label", source_key),
            "url": url,
            "variant": variant,
            "benchmark_version": benchmark_version,
            "raw_name": raw_model_name,
            "source_date": source_date,
            "collected_at": collected_at.isoformat() if collected_at else None,
            "rank_out_of": rank_out_of,
            "rank_board": rank_board,
            "setting_not_stated": setting_not_stated,
            "needs_review": needs_review,
            "badges": [],
            "others": [],
            "tied_with": [],
        }

    # What every other source says for the same cell: its own latest read
    # (stale values excluded), lower tiers included, so nothing is hidden.
    for row_id, benchmark_key, metric, source_key, value, raw_text, variant in conn.execute(
        "SELECT row_id, benchmark_key, metric, source_key, value, raw_text, variant "
        "FROM bench_observation WHERE NOT stale ORDER BY source_key"
    ).fetchall():
        cell = cells.get(row_id, {}).get(f"{benchmark_key}_{metric}")
        if cell is None or cell["source"] == source_key:
            continue
        other = sources.get(source_key, {})
        cell["others"].append(
            {
                "source_label": other.get("label", source_key),
                "tier": other.get("tier"),
                "display": shown(raw_text, value, metric),
                "variant": variant,
            }
        )

    # A tie is the same rank on the same board, so it is read from the ranks
    # themselves - values stored before the run marked ties (2026-10-27), and a
    # board that prints "25" twice, are ties too - naming the models it ties with.
    labels = {r[0]: r[4] for r in rows}
    rank_groups: dict[tuple[str, str, str, float], list[str]] = {}
    for row_id, by_key in cells.items():
        for key, cell in by_key.items():
            if key.endswith("_rank"):
                # The same source too: two boards without a board name are
                # still two boards.
                group = (key, cell["source"], cell["rank_board"] or "", cell["sort"])
                rank_groups.setdefault(group, []).append(row_id)
    for (key, _, _, _), members in rank_groups.items():
        # One board entry filling two rows (a model and its setting row) is
        # one entry, not a tie: only different names on the board count.
        names = {cells[m][key]["raw_name"] for m in members}
        if len(names) < 2:
            continue
        for row_id in members:
            own = cells[row_id][key]["raw_name"]
            cells[row_id][key]["tied"] = True
            cells[row_id][key]["tied_with"] = sorted(
                labels.get(m) or m for m in members if cells[m][key]["raw_name"] != own
            )

    # The badges. "new" is only an addition that is news - a recently released
    # model's debut, or a value its source dates as recent (_news). A cell filled
    # because we started reading a source or a column, or because a board listed
    # an old model, is not new (Parvathi, 2026-10-28): run #2's whole first
    # import carried "new" because the first-run check fell on the failed run #1.
    since = datetime.now(UTC) - timedelta(days=RECENT_DAYS)
    released = _release_dates(conn)
    baseline = _baselines(conn)
    rules = news_rules()
    for (
        row_id,
        benchmark_key,
        metric,
        change_type,
        direction,
        run_id,
        new_source,
        changed_at,
        source_date,
    ) in conn.execute(
        "SELECT row_id, benchmark_key, metric, change_type, direction, run_id, new_source, "
        "changed_at, source_date FROM bench_change "
        "WHERE changed_at >= %s AND change_type IN ('added', 'updated', 'source_changed') "
        "ORDER BY id",
        (since,),
    ).fetchall():
        cell = cells.get(row_id, {}).get(f"{benchmark_key}_{metric}")
        if cell is None:
            continue
        if change_type == "added":
            news = _news(
                {
                    "type": "added",
                    "run_id": run_id,
                    "new_source": new_source,
                    "row_id": row_id,
                    "benchmark_key": benchmark_key,
                    "metric": metric,
                    "changed_at": changed_at,
                    "source_date": source_date,
                },
                released,
                baseline,
                rules,
            )
            if news not in ("debut", "fresh"):
                continue
        badge = {"added": "new", "source_changed": "source"}.get(change_type, "changed")
        cell["badges"] = [b for b in cell["badges"] if b not in ("new", "changed", "source")] + [
            badge
        ]
        # Another source taking the cell over is not the model moving (2026-10-27):
        # no arrow, even on entries a run wrote with one before that rule.
        cell.pop("direction", None)
        if change_type == "updated" and direction in ("better", "worse"):
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

    # Cells the benchmark's own board dropped (PR #581 review): blank, like a
    # cell never measured, so the page says which board dropped the model, when,
    # and its last value. From each cell's latest changelog entry.
    tier_of = _read_tiers()
    dropped: dict[str, dict[str, dict[str, Any]]] = {}
    for (
        row_id,
        benchmark_key,
        metric,
        change_type,
        old_source,
        old_raw,
        old_value,
        at,
    ) in conn.execute(
        "SELECT DISTINCT ON (row_id, benchmark_key, metric) row_id, benchmark_key, metric, "
        "change_type, old_source, old_raw, old_value, changed_at FROM bench_change "
        "WHERE benchmark_key IS NOT NULL ORDER BY row_id, benchmark_key, metric, id DESC"
    ).fetchall():
        key = f"{benchmark_key}_{metric}"
        if (
            change_type == "removed"
            and tier_of.get(old_source) == 1
            and key in columns
            and key not in cells.get(row_id, {})
        ):
            dropped.setdefault(row_id, {})[key] = {
                "source_label": sources.get(old_source, {}).get("label", old_source),
                "on": _iso(at),
                "last": shown(old_raw, old_value, metric),
            }

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
                "dropped": dropped.get(row_id, {}),
            }
            for row_id, setting, label, dated in ordered(settings_by_model.get(model_id, []))
            if cells.get(row_id) or dropped.get(row_id)
        ]
        return {
            "row_id": model_id,
            "label": label,
            "group": group,
            "cells": cells.get(model_id, {}),
            "dropped": dropped.get(model_id, {}),
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
        # Shown while it has a value, or a value its board dropped: the drop
        # is what the reader should see (PR #581 review).
        if (
            row["cells"]
            or row["dropped"]
            or any(child["cells"] or child["dropped"] for child in row["children"])
        ):
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
}
READERS = {
    "html_table": "HTML table (BeautifulSoup + lxml)",
    "embedded_json": "Data block inside the page (<script> JSON)",
    "next_flight": "Data inside the page (Next.js page data)",
}


def _sources_view(
    conn,
    sources: dict[str, dict[str, Any]],
    columns: dict[str, dict[str, Any]],
    used: set[str],
):
    """Every configured source: its link, how it is fetched and read, what it fills,
    and what the last published run got from it."""
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
                "tier": s.get("tier"),
                "tier_label": TIERS.get(s.get("tier")),
                "tier_note": s.get("tier_note"),
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


#: The Changelog's filter pills (2026-10-26). "score"/"rank": a value that moved
#: on the same source; "up"/"down": the same, by direction - another source
#: taking the cell over is "source_changed", never up or down (2026-10-27).
#: Fixed SQL only - never user text.
CHANGE_KINDS = {
    "score": "c.change_type = 'updated' AND c.metric <> 'rank'",
    "rank": "c.change_type = 'updated' AND c.metric = 'rank'",
    "up": "c.change_type = 'updated' AND c.direction = 'better'",
    "down": "c.change_type = 'updated' AND c.direction = 'worse'",
    "added": "c.change_type = 'added'",
    "removed": "c.change_type = 'removed'",
    "source_changed": "c.change_type = 'source_changed'",
    "variant_added": "c.change_type = 'variant_added'",
}


#: NEWS-WORTHY (Parvathi, 2026-10-26). A changelog entry is news when it says
#: something happened, not just that the board learned a value:
#:   debut  a value for a model released in the last debut_days (registry
#:          release date) - a new model showing up on a benchmark
#:   fresh  a new value the source itself dates within fresh_days of the run
#:          (an older model's new result, not a backfill)
#:   mover  a value that moved on the same source and the same release: any
#:          rank move, a score by mover_points or more, a rating by mover_rating
#:   dropped  a value removed because the benchmark's own (tier-1) board no
#:          longer lists the model - often retired or withdrawn (2026-10-28)
#: The numbers are contract/benchmarks/validation.yaml `news` (news_rules()).
#: Everything else - a source's FIRST read (its baseline: every value is new to
#: the board then), a value the board only now read, a source taking a cell
#: over, a new release resetting a board - is not news.
NEWS_KINDS = ("news", "debut", "fresh", "mover", "dropped")


def _read_tiers() -> dict[str, int]:
    """The tier of each source we still read. A value removed because we stopped
    reading a source is not a board dropping a model."""
    return {k: s.get("tier") for k, s in _sources().items() if s.get("enabled")}


def news_rules() -> dict[str, float]:
    """The thresholds, from contract/benchmarks/validation.yaml `news` (rule 5)."""
    rules = _yaml("validation.yaml")["news"]
    return {
        k: float(rules[k]) for k in ("debut_days", "fresh_days", "mover_points", "mover_rating")
    }


def _day(text: Any) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10])
    except (TypeError, ValueError):
        return None


def _release_dates(conn) -> dict[str, date]:
    try:
        rows = conn.execute(
            "SELECT canonical_id, release_date FROM model_version WHERE release_date IS NOT NULL"
        ).fetchall()
    except errors.UndefinedTable:  # no registry here: no debuts. Other errors raise.
        conn.rollback()
        return {}
    return {model_id: released for model_id, released in rows}


def _baselines(conn) -> dict[tuple[str, str, str], int]:
    """Each source's first run that wrote a value to each column: everything it
    added then is a first read, not news - a source new to the board, or a new
    column read from a source we already had. Per source only, ARC Prize's new
    ARC-AGI-3 column made 41 "debut" items on its first read (run #4,
    2026-10-28)."""
    return {
        (source, benchmark_key, metric): run_id
        for source, benchmark_key, metric, run_id in conn.execute(
            "SELECT new_source, benchmark_key, metric, min(run_id) FROM bench_change "
            "WHERE new_source IS NOT NULL AND benchmark_key IS NOT NULL GROUP BY 1, 2, 3"
        ).fetchall()
    }


def _news(
    change: dict[str, Any],
    released: dict[str, date],
    baseline: dict[tuple[str, str, str], int],
    rules: dict[str, float],
) -> str | None:
    """Which kind of news one change is, or None."""
    on = _day(change["changed_at"])
    first_read = (change["new_source"], change["benchmark_key"], change["metric"])
    if change["type"] == "added" and baseline.get(first_read) == change["run_id"]:
        return None
    if change["type"] == "added" and on:
        model = change["row_id"].split(":")[0].split("@")[0]
        if model in released and 0 <= (on - released[model]).days <= rules["debut_days"]:
            return "debut"
        dated = _day(change["source_date"])
        if dated and 0 <= (on - dated).days <= rules["fresh_days"]:
            return "fresh"
        return None
    if change["type"] == "removed":
        # The benchmark's own board no longer lists the model (merge.py: its
        # value is not replaced by a lower tier) - often a retired model.
        return "dropped" if change.get("old_tier") == 1 else None
    if change["type"] == "updated" and not (change["note"] or "").startswith("new release"):
        if change["metric"] == "rank":
            return "mover"
        if change["old_value"] is None or change["new_value"] is None:
            return None
        step = abs(change["new_value"] - change["old_value"])
        return (
            "mover"
            if step >= rules["mover_rating" if change["metric"] == "rating" else "mover_points"]
            else None
        )
    return None


# ── the public charts ────────────────────────────────────────────────────────

# BUILT ONCE PER CHANGE TO THE TABLE (2026-10-30). `table()` took about 7 s a call
# on the shared data from a laptop, and a public page asks twice on first open.
# The build is kept until this fingerprint moves: every cell write sets
# `bench_cell.updated_at` (collect/benchmarks/store.py), a removed cell lowers
# the count, and a renamed row changes the labels' hash. So the charts still
# change on the first load after anything changes the signed-in table.
_CHARTS_FINGERPRINT_SQL = (
    "SELECT (SELECT count(*) FROM bench_cell), (SELECT max(updated_at) FROM bench_cell), "
    "(SELECT md5(coalesce(string_agg(row_id || '=' || display_label, ',' ORDER BY row_id), '')) "
    "FROM bench_row)"
)
_charts_cache: dict[str, Any] = {"key": None, "built": None, "checked": None}


def charts_recheck_seconds() -> int:
    """module_settings.yaml `charts.recheck_seconds`; refused when absent (rule 12)."""
    value = (_yaml("module_settings.yaml").get("charts") or {}).get("recheck_seconds")
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(
            "contract/benchmarks/module_settings.yaml: charts.recheck_seconds must be a "
            "positive integer"
        )
    return value


def charts_if_fresh(
    model_id: str | None = None, *, now: float | None = None
) -> dict[str, Any] | None:
    """The kept charts, with NO database call, when the table was checked less than
    `charts.recheck_seconds` ago; None when it is time to ask again."""
    checked = _charts_cache["checked"]
    now = time.monotonic() if now is None else now
    if (
        _charts_cache["built"] is None
        or checked is None
        or _charts_cache["key"] is None
        or _charts_cache["key"][0] != database_url()
        or now - checked >= charts_recheck_seconds()
    ):
        return None
    return _serve_charts(_charts_cache["built"], model_id)


def charts_kept(model_id: str | None = None) -> dict[str, Any] | None:
    """The kept charts whatever their age, for this database; None before the first
    build. Served while `refresh_charts_in_background` asks whether the table
    changed, so no reader waits on that check."""
    if _charts_cache["built"] is None or (_charts_cache["key"] or (None,))[0] != database_url():
        return None
    return _serve_charts(_charts_cache["built"], model_id)


_charts_refreshing = threading.Lock()


def refresh_charts_in_background() -> None:
    """Re-check the table on a thread of its own - one at a time; a check already
    running is not doubled. A failure leaves the kept copy as it was."""
    if not _charts_refreshing.acquire(blocking=False):
        return

    def run():
        try:
            with connection() as conn:
                charts(conn)
        except Exception:  # noqa: BLE001 - the kept copy stays; the next read tries again
            logging.getLogger(__name__).warning("benchmark charts refresh failed", exc_info=True)
        finally:
            _charts_refreshing.release()

    threading.Thread(target=run, name="benchmark-charts-refresh", daemon=True).start()


def _serve_charts(built: dict[str, Any], model_id: str | None) -> dict[str, Any]:
    chosen = next((m for m in built["models"] if m["id"] == model_id), None)
    return {
        **built,
        "models": [{**{k: m[k] for k in ("id", "label", "tracked", "benchmarks_scored")},
                    "series_count": len(m["series"])} for m in built["models"]],
        # None when no model was asked for, or the one asked for has no public value.
        "model": chosen,
    }


def charts(conn, model_id: str | None = None) -> dict[str, Any]:
    """The public AI benchmarks page (/ai-benchmarks, Parvathi, 2026-10-30).

    THE LIST, THEN ONE MODEL. Every model's values together were 1.27 MB on the
    shared data (391 models, 2026-10-30), so the list carries names and counts
    only, and `model_id` asks for one model's values.

    BUILT FROM `table()`, so the charts always show what the signed-in table
    shows - the same cells, the same source tiers, after the same run - and
    change when it does. Nothing is computed here: no average, rank or combined
    score (rule 3).

    WHAT LEAVES THE GATE. Per value: the shown figure, its benchmark, the board's
    own rank and "out of", the source's name, link and date (CLAUDE.md, the
    Benchmarks exception, condition 4). Not sent: the source's own spelling of the
    model, the other sources' values, the badges and tie lists.

    A VALUE WAITING FOR A PERSON IS NOT PUBLISHED. A cell marked `needs_review`
    stays on the signed-in table only; the page says how many were held back.

    CHART OR CARD is decided by the contract, never by how a number looks: a score
    whose benchmark is `score_unit: percent` and lies within 0-100 is a bar; a
    rank, or any other unit, is a card."""
    # The day is in the key too: a move's arrow leaves after RECENT_DAYS even
    # when no run has written anything since.
    fingerprint = conn.execute(_CHARTS_FINGERPRINT_SQL).fetchone()
    key = (database_url(), datetime.now(UTC).date(), *fingerprint)
    if _charts_cache["key"] != key:
        _charts_cache["built"] = _build_charts(conn)
        _charts_cache["key"] = key
    _charts_cache["checked"] = time.monotonic()
    return _serve_charts(_charts_cache["built"], model_id)


# A POSITION THAT MOVED (2026-10-30): the latest same-board change of a rank in
# the last RECENT_DAYS - the window the signed-in table's badges use. Another
# source taking a cell over is "source_changed", never a move.
_RANK_MOVES_SQL = (
    "SELECT DISTINCT ON (row_id, benchmark_key) row_id, benchmark_key, old_raw, new_raw, "
    "rank_out_of_old, direction, changed_at, new_source FROM bench_change "
    "WHERE metric = 'rank' AND change_type = 'updated' AND direction IN ('better', 'worse') "
    "AND changed_at >= %s ORDER BY row_id, benchmark_key, id DESC"
)


def _rank_moves(conn) -> dict[tuple[str, str], dict[str, Any]]:
    since = datetime.now(UTC) - timedelta(days=RECENT_DAYS)
    return {
        (row_id, bench): {"old": old, "new": new, "old_out_of": out_of, "direction": direction,
                          "on": _iso(at), "source": source}
        for row_id, bench, old, new, out_of, direction, at, source
        in conn.execute(_RANK_MOVES_SQL, (since,)).fetchall()
    }


def _bare_rank(raw: str | None) -> str | None:
    return raw.strip().lstrip("#").strip() if raw else raw


def _moved(moves, row_id: str, meta: dict[str, Any], cell: dict[str, Any]) -> dict[str, Any] | None:
    if meta["metric"] != "rank":
        return None
    move = moves.get((row_id, meta["benchmark"]))
    if (
        move is None
        or move["source"] != cell["source"]
        or _bare_rank(move["new"]) != _bare_rank(cell["display"])
    ):
        return None
    return {
        "direction": "up" if move["direction"] == "better" else "down",
        "was": _bare_rank(move["old"]),
        "was_out_of": move["old_out_of"],
        "on": move["on"],
    }


def _build_charts(conn) -> dict[str, Any]:
    """Every model's public values (charts() serves the list, or one of them)."""
    t = table(conn)
    moves = _rank_moves(conn)
    units = {b["key"]: b.get("score_unit") for b in _yaml("benchmarks.yaml")["benchmarks"]}
    meta: dict[str, dict[str, Any]] = {}
    order: dict[str, int] = {}
    for section in t["sections"]:
        for col in section["columns"]:
            order[col["key"]] = len(order)
            meta[col["key"]] = {
                "section": section["key"],
                "section_label": section["label"],
                "benchmark": col["benchmark"],
                "label": col["label"],
                "metric": col["metric"],
                "better": col["better"],
                "setup_note": col["setup_note"],
            }

    withheld = 0
    models = []
    # ONE MODEL, ITS SETTING ROWS AS SERIES (Parvathi, 2026-10-30): the page shows
    # a model's own row and each setting or dated row the table lists under it
    # ("GPT 6 Astra (max)") side by side in one chart. A series with no public
    # value is left out; a model with none at all is not listed.
    for row in t["rows"]:
        series = []
        for r in [row, *row["children"]]:
            values = []
            for key, cell in sorted(r["cells"].items(), key=lambda kv: order[kv[0]]):
                if cell["needs_review"]:
                    withheld += 1
                    continue
                m = meta[key]
                charted = (
                    m["metric"] == "score"
                    and units.get(m["benchmark"]) == "percent"
                    and cell["sort"] is not None
                    and 0 <= cell["sort"] <= 100
                )
                values.append(
                    {
                        **m,
                        "key": key,
                        # The column's place in the signed-in table, so the page
                        # lists across a model's rows in the table's own order.
                        "order": order[key],
                        "display": cell["display"],
                        # The bar's height: the stored percent the figure is shown
                        # from. None for a card.
                        "percent": cell["sort"] if charted else None,
                        "chart": charted,
                        "rank_out_of": cell["rank_out_of"] if m["metric"] == "rank" else None,
                        "tied": bool(cell["tied"]) if m["metric"] == "rank" else False,
                        "source_label": cell["source_label"],
                        "tier_label": cell["tier_label"],
                        "url": cell["url"],
                        "source_date": cell["source_date"],
                        "collected_at": cell["collected_at"],
                        "variant": cell["variant"],
                        "setting_not_stated": cell["setting_not_stated"],
                        # Where the board placed it before, as the board printed it -
                        # never a difference of ours (rule 3). Only while the board
                        # still shows the position it moved to.
                        "moved": _moved(moves, r["row_id"], m, cell),
                    }
                )
            if not values:
                continue
            setting, dated = r.get("setting"), r.get("dated")
            series.append(
                {
                    "id": r["row_id"],
                    "label": r["label"],
                    # The legend's name: the setting, the dated release, or "Base"
                    # for the model's own row (no setting named by the board).
                    "short": " ".join(x for x in (dated, setting) if x) or "Base",
                    "values": values,
                }
            )
        if series:
            models.append(
                {
                    "id": row["row_id"],
                    "label": row["label"],
                    "tracked": row["group"] == "tracked",
                    "series": series,
                    # Rule 7: benchmarks with a score in any of its series, out of
                    # `benchmarks_listed`.
                    "benchmarks_scored": len(
                        {v["benchmark"] for s_ in series for v in s_["values"]
                         if v["metric"] == "score"}
                    ),
                }
            )

    return {
        "models": models,
        # Rule 7: what "N of M benchmarks" is counted over.
        "benchmarks_listed": t["counts"]["benchmarks"],
        "withheld_for_review": withheld,
        "last_run": (
            {"finished_at": t["last_run"]["finished_at"], "status": t["last_run"]["status"]}
            if t["last_run"]
            else None
        ),
    }


def shown(raw: str | None, value: float | None, metric: str | None) -> str | None:
    """What the page prints for a value the source printed as `raw`.

    A score is a percentage, shown in one style: the stored percent value (the
    run's reading of `raw`, rounded to 2 decimals) with trailing zeros and no
    "%" - "0.876878612716763" -> "87.69", "75.80%" -> "75.8", "69.0" -> "69",
    "0.8%, $0.040/task" -> "0.8". A rank or a rating is shown as printed.
    """
    if raw is None or value is None or metric != "score":
        return raw
    return f"{value:.2f}".rstrip("0").rstrip(".")


def page_limits() -> dict[str, int]:
    """How many runs the page lists at a time (module_settings.yaml `page`)."""
    page = _yaml("module_settings.yaml")["page"]
    return {k: int(page[k]) for k in ("runs_shown", "changelog_runs_shown")}


def _side(
    sources: dict[str, dict[str, Any]], source_key: str | None, raw: str | None, display: str | None
) -> dict[str, Any] | None:
    """One side (old or new) of a changelog entry, for its hover."""
    if source_key is None and raw is None:
        return None
    source = sources.get(source_key or "", {})
    return {
        "source_label": source.get("label", source_key),
        "tier": source.get("tier"),
        "tier_label": TIERS.get(source.get("tier")),
        "printed": raw if raw is not None and raw != display else None,
    }


def changelog(
    conn,
    *,
    limit: int = 5000,
    run_id: int | None = None,
    kind: str | None = None,
    before_run: int | None = None,
) -> dict[str, Any]:
    """The changelog, newest first, with each entry's news tag. `kind` is one of
    CHANGE_KINDS (filtered in SQL) or NEWS_KINDS (tagged, then filtered).

    Without `run_id` it lists the changes of the newest `changelog_runs_shown`
    runs that have any (older than `before_run` when given); `more` says older
    runs exist and `older_than` is the `before_run` that lists them. `limit` is
    only a safety cap on entries."""
    _, columns = _columns()
    sources = _sources()
    read_tiers = _read_tiers()
    labels = {
        r[0]: r[1] for r in conn.execute("SELECT row_id, display_label FROM bench_row").fetchall()
    }
    names = {s["id"]: s["name"] for s in _seeds()}
    released = _release_dates(conn)
    baseline = _baselines(conn)
    rules = news_rules()
    conditions, params = [], []
    more, older_than = False, None
    if run_id is not None:
        conditions.append("c.run_id = %s")
        params.append(run_id)
    else:
        shown_runs = page_limits()["changelog_runs_shown"]
        window = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT run_id FROM bench_change WHERE %s::bigint IS NULL OR run_id < %s "
                "ORDER BY run_id DESC LIMIT %s",
                (before_run, before_run, shown_runs + 1),
            ).fetchall()
        ]
        more = len(window) > shown_runs
        window = window[:shown_runs]
        older_than = window[-1] if window else None
        conditions.append("c.run_id = ANY(%s)")
        params.append(window)
    if kind in CHANGE_KINDS:
        conditions.append(f"({CHANGE_KINDS[kind]})")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    # A news filter is decided per entry, so it reads the whole log and keeps
    # the newest `limit` that match; the SQL kinds are cut by the database.
    cap = "" if kind in NEWS_KINDS else "LIMIT %s"
    rows = conn.execute(
        "SELECT c.id, c.run_id, c.changed_at, c.row_id, c.benchmark_key, c.metric, c.change_type, "
        "c.old_value, c.new_value, c.old_raw, c.new_raw, c.old_source, c.new_source, "
        "c.rank_out_of_old, c.rank_out_of_new, c.source_date, "
        "c.direction, c.reason, c.actor, c.note, c.needs_review "
        f"FROM bench_change c {where} ORDER BY c.id DESC {cap}",  # noqa: S608
        (*params, limit) if cap else tuple(params),
    ).fetchall()
    entries = []
    for (
        cid,
        rid,
        at,
        row_id,
        bench,
        metric,
        change_type,
        old_value,
        new_value,
        old,
        new,
        old_src,
        new_src,
        out_of_old,
        out_of_new,
        source_date,
        direction,
        reason,
        actor,
        note,
        needs_review,
    ) in rows:
        column = columns.get(f"{bench}_{metric}") if bench else None
        old_shown, new_shown = shown(old, old_value, metric), shown(new, new_value, metric)
        entry = {
            "id": cid,
            "run_id": rid,
            "changed_at": _iso(at),
            "row_id": row_id,
            "row": labels.get(row_id) or names.get(row_id) or row_id,
            "column": column["label"] if column else None,
            "benchmark_key": bench,  # with metric: which first read a value belongs to
            "metric": metric,  # score | rank | rating: the Changelog filters on it
            "type": change_type,
            "old": old_shown,
            "new": new_shown,
            "old_value": old_value,
            "new_value": new_value,
            # A rank is a place among the models the board lists: "16 of 30".
            "old_out_of": out_of_old,
            "new_out_of": out_of_new,
            "source_date": source_date,
            "old_source": old_src,
            "new_source": new_src,
            # A source switch has no direction (2026-10-27), whatever an older
            # run stored for it.
            "direction": None if change_type == "source_changed" else direction,
            "reason": reason,
            "actor": actor,
            "note": note,
            "needs_review": needs_review,
            # For the Old / New hover, as a table cell has (2026-10-27): the
            # source's own text when it differs from what is shown, and the
            # source with its tier.
            "old_detail": _side(sources, old_src, old, old_shown),
            "new_detail": _side(sources, new_src, new, new_shown),
            "old_tier": read_tiers.get(old_src),
        }
        entry["news"] = _news(entry, released, baseline, rules)
        # Read by the tagging above, not by the page (rule 9).
        for internal in ("benchmark_key", "metric", "old_value", "new_value", "old_tier"):
            del entry[internal]
        if kind in NEWS_KINDS and (entry["news"] is None or kind not in ("news", entry["news"])):
            continue
        entries.append(entry)
        if len(entries) >= limit:
            break
    total = conn.execute("SELECT count(*) FROM bench_change").fetchone()[0]
    counts = {
        key: conn.execute(f"SELECT count(*) FROM bench_change c WHERE {sql}").fetchone()[0]  # noqa: S608
        for key, sql in CHANGE_KINDS.items()
    }
    counts.update(_news_counts(conn, released, baseline, rules))
    return {
        "entries": entries,
        "total": total,
        "counts": counts,
        "kind": kind or "all",
        "more": more,
        "older_than": older_than,
        "news_rules": rules,
        # Runs that were some source's first read (all their values new to the
        # board): the page labels them "first import" (PR #573 review).
        "baseline_runs": sorted(set(baseline.values())),
    }


def _news_counts(
    conn,
    released: dict[str, date],
    baseline: dict[tuple[str, str, str], int],
    rules: dict[str, float],
) -> dict[str, int]:
    found = {k: 0 for k in NEWS_KINDS}
    read_tiers = _read_tiers()
    for (
        run_id,
        source,
        old_source,
        row_id,
        benchmark_key,
        metric,
        change_type,
        old_value,
        new_value,
        at,
        source_date,
        note,
    ) in conn.execute(
        "SELECT run_id, new_source, old_source, row_id, benchmark_key, metric, change_type, "
        "old_value, new_value, changed_at, source_date, note FROM bench_change "
        "WHERE change_type IN ('added', 'updated', 'removed')"
    ).fetchall():
        tag = _news(
            {
                "run_id": run_id,
                "new_source": source,
                "old_tier": read_tiers.get(old_source),
                "row_id": row_id,
                "benchmark_key": benchmark_key,
                "metric": metric,
                "type": change_type,
                "old_value": old_value,
                "new_value": new_value,
                "changed_at": at,
                "source_date": source_date,
                "note": note,
            },
            released,
            baseline,
            rules,
        )
        if tag:
            found[tag] += 1
            found["news"] += 1
    return found


def runs(conn, *, limit: int | None = None, before: int | None = None) -> dict[str, Any]:
    """Run history, newest first: `runs_shown` runs (older than `before` when
    given); `more` says older runs exist."""
    limit = limit or page_limits()["runs_shown"]
    rows = conn.execute(
        "SELECT id, request_id, trigger, scope, dry_run, status, started_at, finished_at, report "
        "FROM bench_run WHERE %s::bigint IS NULL OR id < %s ORDER BY id DESC LIMIT %s",
        (before, before, limit + 1),
    ).fetchall()
    return {"runs": [_run_summary(r) for r in rows[:limit]], "more": len(rows) > limit}


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
            k: {"status": v.get("status"), "errors": v.get("errors")}
            for k, v in (report.get("sources") or {}).items()
        },
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
    except errors.UndefinedTable:  # no registry here: tracked models only. Others raise.
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


def refuse_unsafe_write(command: str) -> str | None:
    """Why the page may not write here, or None when it may.

    The board's own rule (judge/writeguard.py): every combination writes EXCEPT
    ENVIRONMENT=development pointed at a database that is not this machine -
    development switches the fixture guard off, so a laptop must not write the
    shared database. So the Run button and name decisions work on the local
    database and in production (Parvathi, 2026-10-27; they were local-only).
    In production the run itself goes through the CLI's preflight, fixture
    checks included, before it writes anything.
    """
    try:
        writeguard.check(database_url(), command=command)
    except writeguard.UnsafeWriteRefused:
        return (
            f"{command} is refused here: this backend runs with ENVIRONMENT=development "
            "and the benchmarks database is not on this machine. Use your local "
            "database, or do it on the production site."
        )
    return None


def refuse_unsafe_decision() -> None:
    """Name decisions (decide/undo): refused only where a write is unsafe."""
    why = refuse_unsafe_write("a name decision")
    if why:
        raise DecisionRefused(why)


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
    why = refuse_unsafe_write("a benchmark run")
    if why:
        raise RunRefused(why)
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
