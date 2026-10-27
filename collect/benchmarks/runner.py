"""One run, end to end, one at a time (doc 15, 23, 24).

    run(trigger, scope, dry_run, use_snapshot)

Each source is isolated: a source that fails or is blocked is recorded with
its reason and keeps its previous values, and the other sources go on
(golden rules 1 and 5). Publishing - observations, cells, changelog, review
items - is one transaction, so the page never shows half a run.

    dry_run       fetch, parse, match and merge; print what WOULD change; publish
                  nothing. Snapshots and the run row are still written, so the
                  preview is on the page and can be re-parsed.
    use_snapshot  re-parse each source's last saved copy instead of fetching
                  (after a mapping or alias fix; the site is not asked again).

Started by `python -m collect.cli benchmarks run`, which the page's Run button
spawns as a background process (judge/benchmarks.py). Never inside a web request.
"""

from __future__ import annotations

import contextlib
import time
import traceback
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from psycopg import pq

from collect.benchmarks import store
from collect.benchmarks.changes import diff
from collect.benchmarks.config import Config, ConfigError, Source, load
from collect.benchmarks.console import SUMMARY, Console
from collect.benchmarks.fetch import Fetched, Fetcher
from collect.benchmarks.host_adapter import (
    SeedModel,
    get_registry_aliases,
    get_registry_models,
    get_seed_models,
)
from collect.benchmarks.match import Resolver, base_row, normalize_name
from collect.benchmarks.merge import dedupe_source, merge
from collect.benchmarks.parse import Parsed, RawObservation, parse
from collect.benchmarks.store import StoredObservation
from collect.benchmarks.values import parse_rank, parse_rating, parse_score
from collect.config import REPO_ROOT

#: How many reasons of one kind are printed at the default verbosity before
#: the rest are counted. Every one is in the log file (verbose).
SHOW_AT_NORMAL = 5


class RunRefused(RuntimeError):
    pass


@dataclass
class SourceResult:
    key: str
    method: str
    status: str = "OK"  # OK | BLOCK | FAIL | SKIP
    http_status: int | None = None
    size_bytes: int | None = None
    content_changed: bool | None = None
    rows_parsed: int = 0
    release: str | None = None
    observations: int = 0
    matched_names: int = 0
    unmatched_names: int = 0
    rejected: int = 0
    kept_previous: int = 0  # refused cells that kept their previous value
    flagged: int = 0
    changes: int = 0
    errors: list[str] = field(default_factory=list)
    new: list[StoredObservation] = field(default_factory=list)

    def report(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "status": self.status,
            "http_status": self.http_status,
            "size_bytes": self.size_bytes,
            "content_changed": self.content_changed,
            "rows_parsed": self.rows_parsed,
            "release": self.release,
            "observations": self.observations,
            "matched_names": self.matched_names,
            "unmatched_names": self.unmatched_names,
            "rejected": self.rejected,
            "flagged": self.flagged,
            "changes": self.changes,
            "errors": self.errors,
        }


class Run:
    def __init__(
        self,
        conn,
        config: Config,
        console: Console,
        *,
        run_id: int,
        dry_run: bool,
        use_snapshot: bool,
        trigger: str,
        actor: str,
        fetcher: Fetcher | None = None,
    ):
        self.conn = conn
        self.config = config
        self.c = console
        self.run_id = run_id
        self.dry_run = dry_run
        self.use_snapshot = use_snapshot
        self.trigger = trigger
        self.actor = actor
        self.fetcher = fetcher
        self.now = datetime.now(UTC)
        self.reviews: list[dict[str, Any]] = []
        self.unmatched: dict[tuple[str, str], dict[str, Any]] = {}
        #: Names a person chose to leave out of the Unmatched list (bench_name_decision).
        self.ignored: set[str] = set()
        self.new_rows: dict[str, tuple[Any, str]] = {}  # row_id -> (Row, first source)
        #: source -> (release the last published run read, this run's release)
        self.new_releases: dict[str, tuple[str, str]] = {}
        self.known_rows = store.existing_rows(conn)
        self.previous_reports = store.previous_source_reports(conn)
        self.previous_obs = {(o.source_key, *o.key): o for o in store.load_observations(conn)}

    # ── per source ───────────────────────────────────────────────────────

    def source(self, source: Source, position: int, total: int, resolver: Resolver) -> SourceResult:
        method = "snapshot" if self.use_snapshot else source.method
        result = SourceResult(key=source.key, method=method)
        columns = sorted(
            {
                f"{t['benchmark']}_{t['metric']}"
                for tb in source.tables
                for t in tb.benchmark_map.values()
            }
            | {f"{tb.rank['benchmark']}_rank" for tb in source.tables if tb.rank}
        )
        self.c.rule(thin=True)
        self.c.line(
            "SOURCE", "IN", f"{source.key} ({position}/{total})  columns: {', '.join(columns)}"
        )

        content, url = self._content(source, result)
        if content is None:
            return result

        parsed = parse(source, content, url=source.page_url or source.url)
        if parsed.blocked:
            for code, message in parsed.problems:
                result.errors.append(f"{code}: {message}")
                self.c.line("PARSE", "BLOCK", f"{code}: {message}")
            result.status = "BLOCK"
            self.c.line("SOURCE", "DONE", f"{source.key} -> blocked; previous values kept")
            return result
        for code, message in parsed.problems:
            result.errors.append(f"{code}: {message}")
            self.c.line("PARSE", "WARN", f"{code}: {message}")
        result.rows_parsed = parsed.rows_parsed
        result.release = parsed.release
        where = (
            f"must_contain={source.tables[0].locate['must_contain']!r}"
            if source.tables[0].locate["type"] == "html_table"
            else source.tables[0].locate["type"]
        )
        self.c.line(
            "PARSE",
            "OK",
            f"{parsed.tables_found} table(s) found ({where}) · {parsed.rows_parsed} rows",
        )
        for note in parsed.notes if len(parsed.notes) > 1 else []:
            self.c.detail("PARSE", "OK", note)

        new_release = self._new_release(source.key, parsed.release)
        observations = self._match_and_value(source, parsed, resolver, result)
        policies = {(o.row_id, o.benchmark_key, o.metric): pol for o, pol in observations if pol}
        kept, reviews, counts = dedupe_source(
            [o for o, _ in observations], self.config.benchmarks, policies
        )
        if self._row_count_jumped(source.key, parsed.rows_parsed, kept, new_release, result):
            self._forget(source.key)
            return result
        if new_release:
            self.new_releases[source.key] = (new_release, parsed.release)
        for item in reviews:
            result.flagged += 1
            self.reviews.append(item)
            self.c.line(
                "CHECK",
                "FLAG",
                f"ambiguous_duplicate: {item['row_id']} · "
                f"{item['benchmark_key']}_{item['metric']} · {item['message']}",
            )
        flags = self._over_time(source, kept, result) if not new_release else []
        if new_release:
            changed = sum(
                1
                for o in kept
                if (b := self.previous_obs.get((o.source_key, *o.key))) and b.value != o.value
            )
            self.c.line(
                "CHECK",
                "OK",
                f"new release {parsed.release} (last published run read {new_release}): "
                f"{changed} changed value(s) are the new release's, not flagged as jumps",
            )
        if self._mass_disappearance(source.key, kept, parsed.rows_parsed, new_release, result):
            self._forget(source.key)
            self.new_releases.pop(source.key, None)
            return result
        decided = ", ".join(f"{k} {v}" for k, v in counts.items() if v and k != "single") or "none"
        self.c.line(
            "CHECK",
            "OK",
            f"{result.rejected} rejected"
            + (
                f" ({result.kept_previous} kept their previous value)"
                if result.kept_previous
                else ""
            )
            + f" · {result.flagged} flagged · duplicates: {decided}",
        )
        if counts["setup_not_accepted"]:
            self.c.detail(
                "CHECK",
                "SKIP",
                f"{counts['setup_not_accepted']} cell(s) only had test setups the "
                "column does not accept (variant_rule)",
            )
        self.reviews.extend(flags)
        result.new = kept
        result.observations = len(kept)
        self.c.line("SOURCE", "DONE", f"{source.key} -> {len(kept)} observations")
        return result

    def _content(self, source: Source, result: SourceResult) -> tuple[bytes | None, str]:
        if self.use_snapshot:
            snap = store.last_snapshot(self.conn, source.key)
            if snap is None:
                result.status = "FAIL"
                result.errors.append("no_snapshot: nothing saved for this source yet")
                self.c.line(
                    "FETCH",
                    "FAIL",
                    "no_snapshot: nothing saved for this source yet - "
                    "run without --use-snapshot first",
                )
                return None, source.url
            self.c.line(
                "FETCH",
                "IN",
                f"snapshot from run #{snap['run_id']} ({snap['fetched_at']:%Y-%m-%d %H:%M} UTC)",
            )
            self.c.line(
                "FETCH", "OK", f"{len(snap['content']) // 1024} KB re-read; the site was not asked"
            )
            result.size_bytes = len(snap["content"])
            return snap["content"], snap["url"]

        self.c.line("FETCH", "IN", f"{source.url}   method={source.method}")
        got: Fetched = self.fetcher.fetch(source, wait_for=_wait_text(source))
        result.http_status = got.http_status
        if not got.ok:
            status = "BLOCK" if got.error in ("blocked_page", "robots_denied") else "FAIL"
            result.status = status
            result.errors.append(f"{got.error}: {got.detail}")
            self.c.line("FETCH", status, f"{got.error}: {got.detail}")
            self.c.line("SOURCE", "DONE", f"{source.key} -> nothing read; previous values kept")
            return None, source.url
        previous_hash = store.last_snapshot_hash(self.conn, source.key)
        result.size_bytes = got.size
        result.content_changed = previous_hash != got.content_hash
        # Fetched live. The page saved last run is only COMPARED (by hash), never
        # read - only "Re-parse saved pages" (--use-snapshot) reads saved pages.
        changed = (
            "fetched live · first copy saved"
            if previous_hash is None
            else "fetched live · content CHANGED vs the page saved last run"
            if result.content_changed
            else "fetched live · content unchanged vs the page saved last run"
        )
        tries = f" · {got.attempts} attempts" if got.attempts > 1 else ""
        self.c.line("FETCH", "OK", f"HTTP {got.http_status} · {_size(got.size)} · {changed}{tries}")
        if got.redirected:
            self.c.line("FETCH", "WARN", f"redirected to {got.final_url} - update sources.yaml")
            self.reviews.append(
                {
                    "check": "redirected",
                    "source_key": source.key,
                    "message": f"{source.url} redirected to {got.final_url}",
                }
            )
        with self.conn.transaction():
            store.save_snapshot(
                self.conn,
                run_id=self.run_id,
                source_key=source.key,
                method=got.method,
                url=got.url,
                final_url=got.final_url,
                http_status=got.http_status,
                content=got.content,
                content_hash=got.content_hash,
                keep=int(self.config.settings["snapshots_kept_per_source"]),
            )
        return got.content, got.url

    def _forget(self, key: str) -> None:
        """A blocked source adds no rows and no unmatched names."""
        for row_id in [r for r, (_, first) in self.new_rows.items() if first == key]:
            del self.new_rows[row_id]
        for name in [n for n in self.unmatched if n[0] == key]:
            del self.unmatched[name]

    def _new_release(self, key: str, release: str | None) -> str | None:
        """The release the last published run read, when this read is a newer one."""
        before = (self.previous_reports.get(key) or {}).get("release")
        return before if release and before and release != before else None

    def _row_count_jumped(
        self,
        key: str,
        rows: int,
        kept: list[StoredObservation],
        new_release: str | None,
        result: SourceResult,
    ) -> bool:
        """L3: a big change in row count is a suspected layout change.

        GROWTH is taken when the values read both times agree: AA's GPQA page
        went from 16 to 27 models with the 16 values unchanged (2026-10-26) -
        a longer list, not a broken page. A SHRINK is never judged that way: a
        page that renders only part of its table shows the same values for the
        part it does render (PR #573 review). A shrink is taken only as a new
        release, or as the board's new size once read `stable_reads` times."""
        before = (self.previous_reports.get(key) or {}).get("rows_parsed")
        rules = self.config.validation["structure"]
        if not before or rows == before:
            return False
        shrink = rows < before
        limit = float(rules["max_row_shrink"] if shrink else rules["max_row_growth"])
        if abs(rows - before) / before > limit:
            change = (
                f"{rows} rows, last taken read had {before} "
                f"(more than {limit:.0%} {'fewer' if shrink else 'more'})"
            )
            if new_release:
                self.c.line("CHECK", "OK", f"{change} - a new release, taken")
                return False
            if shrink:
                if self._stable_size(key, rows):
                    self.c.line(
                        "CHECK",
                        "OK",
                        f"{change} - the same size on {rules['stable_reads']} reads in a "
                        "row: the board's new size, taken",
                    )
                    return False
                return self._block(f"suspected_layout_change: {change}", result)
            both = [
                (o.value, b.value)
                for o in kept
                if o.metric != "rank" and (b := self.previous_obs.get((o.source_key, *o.key)))
            ]
            same = sum(1 for now, then in both if abs(now - then) < 1e-9)
            if len(both) >= 3 and same / len(both) >= 0.9:
                self.c.line(
                    "CHECK",
                    "OK",
                    f"{change} - the list changed: {same} of {len(both)} values listed "
                    "both times are unchanged, so the page reads as before; taken",
                )
                return False
            return self._block(
                f"suspected_layout_change: {change}; {same} of {len(both)} values listed "
                "both times are unchanged",
                result,
            )
        return False

    def _stable_size(self, key: str, rows: int) -> bool:
        """This size was also read on the source's last `stable_reads - 1` reads."""
        need = int(self.config.validation["structure"]["stable_reads"]) - 1
        reads = store.recent_source_reads(self.conn, key, need)
        return len(reads) == need and all((r or {}).get("rows_parsed") == rows for r in reads)

    def _block(self, message: str, result: SourceResult) -> bool:
        result.status = "BLOCK"
        result.errors.append(message)
        self.c.line("CHECK", "BLOCK", message + "; previous values kept")
        return True

    def _mass_disappearance(
        self,
        key: str,
        kept: list[StoredObservation],
        rows: int,
        new_release: str | None,
        result: SourceResult,
    ) -> bool:
        before = (self.previous_reports.get(key) or {}).get("observations")
        floor = float(self.config.validation["mass_disappearance"])
        if not before or len(kept) >= before * floor:
            return False
        change = f"{len(kept)} values, last taken read had {before} (fewer than {floor:.0%})"
        if new_release or self._stable_size(key, rows):
            self.c.line("CHECK", "OK", f"{change} - a new release or the board's new size, taken")
            return False
        return self._block(f"suspected_layout_change: {change}", result)

    def _match_and_value(
        self, source: Source, parsed: Parsed, resolver: Resolver, result: SourceResult
    ) -> list[tuple[StoredObservation, str | None]]:
        matches: dict[tuple[str, str | None], Any] = {}
        out: list[tuple[StoredObservation, str | None]] = []
        rejects: list[str] = []
        by_metric: Counter[str] = Counter()
        examples: list[str] = []
        for raw in parsed.observations:
            mkey = (raw.raw_model_name, raw.raw_setting)
            if mkey not in matches:
                matches[mkey] = resolver.match(raw.raw_model_name, raw.raw_setting)
            m = matches[mkey]
            if m.row is None:
                continue
            value = self._value(raw)
            if value.empty:
                continue
            if value.error:
                result.rejected += 1
                rejects.append(
                    f"{value.error} · {raw.raw_model_name} · {raw.benchmark}_{raw.metric}"
                )
                # A cell that cannot be read keeps the value this source gave it
                # last time, as a failed fetch does (PR #573 review): one bad
                # read must not take a correct figure off the page.
                before = self.previous_obs.get(
                    (source.key, m.row.row_id, raw.benchmark, raw.metric)
                )
                if before is not None and not before.stale:
                    out.append((before, raw.duplicates))
                    result.kept_previous += 1
                continue
            if m.row.row_id not in self.known_rows and m.row.row_id not in self.new_rows:
                self.new_rows[m.row.row_id] = (m.row, source.key)
                if m.row.setting or m.row.dated:
                    kind = (
                        "dated release row" if m.row.dated and not m.row.setting else "setting row"
                    )
                    self.c.line(
                        "MATCH", "NEW", f"{kind}: {m.row.label}   <- {raw.raw_model_name!r}"
                    )
            by_metric[raw.metric] += 1
            if len(examples) < 3:
                examples.append(f"{raw.raw_model_name}: {raw.raw_text!r}")
            out.append(
                (
                    StoredObservation(
                        source_key=source.key,
                        row_id=m.row.row_id,
                        benchmark_key=raw.benchmark,
                        metric=raw.metric,
                        value=value.value,
                        rank_high=value.rank_high if raw.metric == "rank" else None,
                        tied=value.tied,
                        rank_out_of=raw.rank_out_of if raw.metric == "rank" else None,
                        rank_board=raw.rank_board if raw.metric == "rank" else None,
                        variant=raw.variant,
                        raw_text=raw.raw_text,
                        raw_model_name=raw.raw_model_name,
                        url=raw.url,
                        source_date=raw.collected_on,
                        setting_not_stated=m.setting_not_stated,
                        priority=raw.priority or source.priority,
                        run_id=self.run_id,
                        collected_at=self.now,
                    ),
                    raw.duplicates,
                )
            )

        names = {k: m for k, m in matches.items()}
        matched = [k for k, m in names.items() if m.row is not None]
        unmatched = [(k, m) for k, m in names.items() if m.row is None]
        result.matched_names = len(matched)
        result.unmatched_names = len(unmatched)
        self.c.line(
            "MATCH",
            "OK",
            f"{len(matched)} names matched tracked or registry models · "
            f"{sum(m.reason == 'unmatched' for _, m in unmatched)} not in the registry "
            f"(not listed) · {sum(m.reason == 'similar_to_registry' for _, m in unmatched)} "
            "very close to a registry name (listed) · "
            f"{sum(m.reason not in ('unmatched', 'similar_to_registry') for _, m in unmatched)} "
            "with a setting or date not read (listed)",
        )
        for (name, setting), m in unmatched:
            shown = name + (f" ({setting})" if setting else "")
            base = m.base_name or name
            if normalize_name(base) in self.ignored:
                continue  # a person chose to leave it out of the list
            # ONLY REGISTRY MODELS ARE LISTED (Parvathi, 2026-10-26). A name whose
            # model is neither tracked nor in the registry is not recorded; the
            # MATCH line above still counts it. What is listed is a known model
            # whose setting or date could not be read (reason unknown_setting...),
            # or a name very close to a registry name (similar_to_registry) for a
            # person to confirm - never matched automatically.
            if m.reason == "unmatched":
                continue
            self.unmatched[(source.key, shown)] = {
                "reason": m.reason,
                "base_name": base,
                "base_key": normalize_name(base),
                "similar_to": m.similar_to,
            }
            if m.reason == "unknown_setting":
                self.c.line(
                    "MATCH",
                    "WARN",
                    f"unknown setting word {m.setting_word!r} in {shown!r} "
                    f"(model {m.model_id}) -> review",
                )
                self.reviews.append(
                    {
                        "check": "unknown_setting",
                        "source_key": source.key,
                        "message": (
                            f"{shown!r}: {m.setting_word!r} is not in settings_vocabulary.yaml"
                        ),
                    }
                )
            elif m.reason == "similar_to_registry":
                self.c.line(
                    "MATCH",
                    "WARN",
                    f"{shown!r} looks like {', '.join(m.similar_to)} -> Unmatched names",
                )
            else:
                self.c.detail("MATCH", "SKIP", f"unmatched {shown!r}")
        kinds = (
            " · ".join(f"{n} {metric}s" for metric, n in sorted(by_metric.items())) or "no values"
        )
        self.c.line("VALUE", "OK", f"{kinds}" + (f"  ({'; '.join(examples)})" if examples else ""))
        for i, reject in enumerate(rejects):
            if i < SHOW_AT_NORMAL:
                self.c.line("CHECK", "FAIL", f"REJECT {reject}")
            else:
                self.c.detail("CHECK", "FAIL", f"REJECT {reject}")
        if len(rejects) > SHOW_AT_NORMAL:
            self.c.line(
                "CHECK",
                "FAIL",
                f"... and {len(rejects) - SHOW_AT_NORMAL} more rejected (all in the log file)",
            )
        return out

    def _value(self, raw: RawObservation):
        if raw.metric == "score":
            return parse_score(raw.raw_text, raw.scale or "percent")
        if raw.metric == "rating":
            return parse_rating(raw.raw_text, self.config.benchmarks[raw.benchmark].rating_range)
        return parse_rank(raw.raw_text, raw.rank_out_of)

    def _over_time(
        self, source: Source, kept: list[StoredObservation], result: SourceResult
    ) -> list[dict]:
        """L7: each value against this source's previous value for the same cell.

        A RANK moving is never flagged (Parvathi, 2026-10-26): a rank is a place
        among the models the board lists, so it moves whenever the board adds,
        drops or re-runs models. It is counted on one line and goes to the
        changelog like any change.
        """
        jump = self.config.validation["jump"]
        flags = []
        ranks_moved = 0
        for o in kept:
            before = self.previous_obs.get((o.source_key, *o.key))
            if before is None or before.value == o.value:
                continue
            if o.metric == "rank":
                ranks_moved += 1
                continue
            bench = self.config.benchmarks[o.benchmark_key]
            reason = None
            if bench.volatility == "static":
                reason = "possible_correction"
            elif o.metric == "rating":
                if abs(o.value - before.value) > float(jump["rating"]):
                    reason = "large_jump"
            elif abs(o.value - before.value) > float(jump["percent"]):
                reason = "large_jump"
            if reason:
                result.flagged += 1
                message = (
                    f"{o.row_id} · {o.benchmark_key}_{o.metric} {before.value:g} -> {o.value:g} "
                    f"({source.key}, {bench.volatility})"
                )
                self.c.line("CHECK", "FLAG", f"{reason}: {message}")
                flags.append(
                    {
                        "check": reason,
                        "source_key": source.key,
                        "row_id": o.row_id,
                        "benchmark_key": o.benchmark_key,
                        "metric": o.metric,
                        "message": message,
                    }
                )
        if ranks_moved:
            self.c.line(
                "CHECK",
                "OK",
                f"{ranks_moved} rank(s) moved - the board's list changed; not flagged (changelog)",
            )
        return flags


def _wait_text(source: Source) -> str | None:
    for table in source.tables:
        if table.locate.get("type") == "html_table":
            return table.locate.get("must_contain")
    return None


def _size(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB" if n >= 1024 * 1024 else f"{max(1, n // 1024)} KB"


def _scope(config: Config, scope: str) -> list[Source]:
    enabled = [s for s in config.sources if s.enabled]
    if scope == "all":
        return enabled
    by_key = [s for s in config.sources if s.key == scope]
    if by_key:
        return by_key
    by_bench = [
        s
        for s in enabled
        if any(t["benchmark"] == scope for tb in s.tables for t in tb.benchmark_map.values())
    ]
    if by_bench:
        return by_bench
    raise RunRefused(f"scope {scope!r} is not 'all', a source key or a benchmark key")


# ── the entry point ──────────────────────────────────────────────────────────


def run(
    *,
    conn,
    trigger: str = "manual_run",
    scope: str = "all",
    dry_run: bool = False,
    use_snapshot: bool = False,
    verbosity: str | None = None,
    request_id: str | None = None,
    actor: str = "admin",
    fetcher: Fetcher | None = None,
    stream=None,
    seeds: list[SeedModel] | None = None,
    registry_aliases: dict[str, list[str]] | None = None,
    registry_models: list[SeedModel] | None = None,
) -> int:
    """Returns the process exit code: 0 ok / partial / dry run, 1 error, 3 refused."""
    started = time.monotonic()
    # The CLI's startup checks (preflight) read inside a transaction and leave it
    # open; autocommit cannot be switched on mid-transaction (PR #573 review).
    # Whatever they did is theirs to keep, so it is committed, not rolled back.
    if not conn.autocommit and conn.info.transaction_status != pq.TransactionStatus.IDLE:
        conn.commit()
    conn.autocommit = True
    try:
        config = load()
    except ConfigError as error:
        console = Console(verbosity=verbosity or "normal", log_path=None, stream=stream)
        console.line(
            "SETUP",
            "FAIL",
            "CONFIG: contract/benchmarks/ failed its checks; the run does not start",
            level=SUMMARY,
        )
        for problem in error.problems:
            console.line("SETUP", "FAIL", problem, level=SUMMARY)
        console.close()
        return 1

    if not store.try_lock(conn):
        console = Console(verbosity="normal", log_path=None, stream=stream)
        console.line(
            "SETUP",
            "FAIL",
            "another benchmark run is in progress (one run at a time)",
            level=SUMMARY,
        )
        console.close()
        return 3
    console = None
    run_id = None
    try:
        abandoned = store.close_abandoned_runs(
            conn, older_than_minutes=2 * int(config.settings["timeouts"]["run_minutes"])
        )
        run_id = store.start_run(
            conn, trigger=trigger, scope=scope, dry_run=dry_run, request_id=request_id
        )
        log_path = config.log_dir / store.log_file_name(conn, run_id)
        console = Console(
            verbosity=verbosity or config.settings["verbosity"], log_path=log_path, stream=stream
        )
        console.header(run_id, trigger, scope, dry_run)
        status, report = _run_body(
            conn,
            config,
            console,
            run_id=run_id,
            scope=scope,
            dry_run=dry_run,
            use_snapshot=use_snapshot,
            trigger=trigger,
            actor=actor,
            fetcher=fetcher,
            seeds=seeds,
            registry_aliases=registry_aliases,
            registry_models=registry_models,
            abandoned=abandoned,
            started=started,
        )
    except Exception as error:  # noqa: BLE001 - a run that breaks says so and records it
        status = "error"
        report = {"error": f"{type(error).__name__}: {error}"}
        if console is not None:
            console.line(
                "SUMMARY", "FAIL", f"RUN FAILED: {type(error).__name__}: {error}", level=SUMMARY
            )
            console.text(traceback.format_exc(), level=10)
    finally:
        if console is not None:
            console.close()
        if run_id is not None:
            log_text = ""
            with contextlib.suppress(OSError):
                log_text = (config.log_dir / store.log_file_name(conn, run_id)).read_text(
                    encoding="utf-8"
                )
            store.finish_run(conn, run_id, status=status, report=report, log_text=log_text)
        store.unlock(conn)
    return 1 if status == "error" else 0


def _run_body(
    conn,
    config: Config,
    c: Console,
    *,
    run_id: int,
    scope: str,
    dry_run: bool,
    use_snapshot: bool,
    trigger: str,
    actor: str,
    fetcher: Fetcher | None,
    seeds: list[SeedModel] | None,
    registry_aliases: dict[str, list[str]] | None,
    registry_models: list[SeedModel] | None,
    abandoned: list[int],
    started: float,
) -> tuple[str, dict]:
    seeds = seeds if seeds is not None else get_seed_models()
    c.line(
        "SETUP",
        "OK",
        f"seed models from the host: {len(seeds)} tracked text models "
        "(contract/tracked_models.yaml)",
    )
    decisions = store.load_name_decisions(conn)
    if registry_models is None:
        registry_models = get_registry_models(conn)
    # ONLY REGISTRY MODELS GET ROWS (Parvathi, 2026-10-26): an "Add as new row"
    # decision for a model outside the registry is no longer applied. The page no
    # longer offers it; one left in the table is skipped and named here.
    skipped_rows = [name for _key, name, action, _ in decisions if action == "new_row"]
    if registry_aliases is None:
        registry_aliases = get_registry_aliases(conn, [*seeds, *registry_models])
    resolver = Resolver(config, seeds, registry_aliases, registry_models)
    # "Same model as ..." decisions: the name becomes an exact alias of that model.
    for _key, name, action, target in decisions:
        if action == "alias":
            warning = resolver.add_decided_alias(name, target)
            if warning:
                resolver.warnings.append(warning)
    # Compared on the name normalised NOW, not the stored key, so a change to
    # normalize_name never silently un-ignores a name.
    ignored = {normalize_name(name) for _key, name, action, _ in decisions if action == "ignore"}
    if resolver.problems:
        for problem in resolver.problems:
            c.line("SETUP", "FAIL", f"CONFIG: {problem}", level=SUMMARY)
        return "error", {"error": "alias collision", "problems": resolver.problems}
    c.line(
        "SETUP",
        "OK",
        f"config: {len(config.files)} files loaded from contract/benchmarks/, L1 checks passed",
    )
    c.line(
        "SETUP",
        "OK",
        f"aliases: {resolver.registry_alias_count} more names from the registry (model_alias)"
        " on top of each model's id, name and model_extras.yaml",
    )
    c.line(
        "SETUP",
        "OK",
        f"registry models: {len(resolver.registry_ids)} untracked models are matched too, by "
        "id, name and alias; they get rows below the tracked ones only when a source lists them",
    )
    if decisions:
        counts = Counter(action for _, _, action, _ in decisions)
        c.line(
            "SETUP",
            "OK",
            "decisions from the Unmatched list: "
            + ", ".join(f"{n} {a.replace('_', ' ')}" for a, n in sorted(counts.items())),
        )
    if skipped_rows:
        c.line(
            "SETUP",
            "WARN",
            f"'add as new row' decisions not applied - only registry models get rows: "
            f"{', '.join(skipped_rows)}",
        )
    for warning in resolver.warnings:
        c.line("SETUP", "WARN", warning)
    if abandoned:
        c.line(
            "SETUP",
            "WARN",
            f"closed abandoned run(s) {abandoned}: their process stopped without finishing",
        )
    c.line(
        "SETUP", "OK", "scraping only · robots.txt respected · no data files, no API keys, no LLM"
    )
    sources = _scope(config, scope)
    c.line(
        "SETUP", "OK", f"sources in scope: {len(sources)}  ({', '.join(s.key for s in sources)})"
    )
    for s in config.sources:
        if not s.enabled and scope == "all":
            c.line("SETUP", "SKIP", f"{s.key}: disabled - {s.why_disabled}")

    run = Run(
        conn,
        config,
        c,
        run_id=run_id,
        dry_run=dry_run,
        use_snapshot=use_snapshot,
        trigger=trigger,
        actor=actor,
        fetcher=None,
    )
    run.ignored = ignored
    own_fetcher = False
    if not use_snapshot:
        run.fetcher = fetcher or Fetcher(config)
        own_fetcher = fetcher is None
    results: list[SourceResult] = []
    deadline = started + 60 * float(config.settings["timeouts"]["run_minutes"])
    try:
        for i, source in enumerate(sources, start=1):
            if time.monotonic() > deadline:
                c.line("SOURCE", "SKIP", f"{source.key}: the run's time limit was reached")
                results.append(
                    SourceResult(
                        key=source.key,
                        method=source.method,
                        status="SKIP",
                        errors=["run time limit reached"],
                    )
                )
                continue
            try:
                results.append(run.source(source, i, len(sources), resolver))
            except Exception as error:  # noqa: BLE001 - golden rule 1
                c.line("SOURCE", "FAIL", f"{source.key}: {type(error).__name__}: {error}")
                c.text(traceback.format_exc(), level=10)
                results.append(
                    SourceResult(
                        key=source.key,
                        method=source.method,
                        status="FAIL",
                        errors=[f"{type(error).__name__}: {error}"],
                    )
                )
    finally:
        if own_fetcher:
            run.fetcher.close()

    c.rule(thin=True)
    refreshed = {r.key: r for r in results if r.status == "OK"}
    seed_rows = [base_row(s) for s in seeds]

    # Every observation that competes: this run's, for the sources that were read,
    # and the stored ones for every source that was not (they keep their values).
    previous_obs = store.load_observations(conn)
    # A source no longer read (disabled, renamed, removed, or a data file while
    # those are off) keeps its stored values as stale: they stop competing, so a
    # renamed source's old values cannot linger in the table (2026-10-26).
    readable = {s.key for s in config.sources if s.enabled}
    # Sources no longer read whose values are not stale yet: said once, on the run
    # that marks them stale - not on every run after (2026-10-26).
    unread_sources = sorted({o.source_key for o in previous_obs if not o.stale} - readable)
    combined = [
        o
        for o in previous_obs
        if o.source_key not in refreshed and (o.source_key in readable or _mark_stale(o))
    ]
    for result in refreshed.values():
        fresh = {o.key for o in result.new}
        combined.extend(result.new)
        combined.extend(
            o
            for o in previous_obs
            if o.source_key == result.key and o.key not in fresh and _mark_stale(o)
        )
    if unread_sources:
        c.line(
            "MERGE",
            "SKIP",
            f"values from sources no longer read are kept as stale and not published: "
            f"{', '.join(unread_sources)}",
        )
    decisions = merge(config, combined, run_id=run_id)
    cells = {k: d.cell for k, d in decisions.items()}
    rules = Counter(d.rule for d in decisions.values() if d.rule != "single source")
    flags = [f for d in decisions.values() for f in d.flags]
    for f in flags:
        c.line(
            "MERGE",
            "FLAG",
            f"disagreement: {f['row_id']} · {f['benchmark_key']}_{f['metric']} · {f['message']}",
        )
    conflicts = ", ".join(f"{rule}: {n}" for rule, n in sorted(rules.items())) or "none"
    c.line(
        "MERGE", "OK", f"{len(cells)} cells · decided by {conflicts} · {len(flags)} disagreement(s)"
    )
    c.line("DERIVE", "SKIP", "nothing derived - values are shown as the sources publish them")

    previous_cells = store.load_cells(conn)
    reason = (
        "backfill"
        if not previous_cells
        else ("scheduled_run" if trigger == "scheduled" else "manual_run")
    )
    changes = diff(config, previous_cells, cells, reason=reason, actor=actor)
    for row_id, (row, first_source) in run.new_rows.items():
        if row.setting or row.dated:
            changes.insert(
                0,
                {
                    "row_id": row_id,
                    "change_type": "variant_added",
                    "reason": reason,
                    "actor": actor,
                    "note": f"New row: {row.label}, first seen on {first_source}",
                },
            )
    for ch in changes:
        if ch.get("new_source") in run.new_releases and not ch.get("note"):
            old, new = run.new_releases[ch["new_source"]]
            ch["note"] = f"new release {new} (was {old})"
    _print_changes(c, changes, config, previous_cells)
    per_source = Counter(ch.get("new_source") or ch.get("old_source") for ch in changes)
    for r in results:
        r.changes = per_source.get(r.key, 0)
    reviews = run.reviews + flags
    new_reviews = len(reviews)

    if dry_run:
        c.line(
            "PUBLISH",
            "SKIP",
            f"dry run: {len(cells)} cells, {len(changes)} changes and "
            f"{len(reviews)} review items NOT written",
        )
    else:
        with conn.transaction():
            for row in seed_rows:
                store.ensure_row(
                    conn,
                    row_id=row.row_id,
                    host_model_id=row.host_model_id,
                    setting=None,
                    label=row.label,
                    auto_created=False,
                    source_key=None,
                )
            for row, first_source in run.new_rows.values():
                if row.host_model_id in resolver.registry_ids:
                    # A registry model's own row, first time a source lists it.
                    store.ensure_row(
                        conn,
                        row_id=row.host_model_id,
                        host_model_id=row.host_model_id,
                        setting=None,
                        label=resolver.seeds[row.host_model_id].name,
                        auto_created=True,
                        source_key=first_source,
                    )
                if row.setting or row.dated:
                    store.ensure_row(
                        conn,
                        row_id=row.row_id,
                        host_model_id=row.host_model_id,
                        setting=row.setting,
                        label=row.label,
                        auto_created=True,
                        source_key=first_source,
                        dated=row.dated,
                    )
            for result in refreshed.values():
                store.replace_source_observations(conn, result.key, result.new)
            store.mark_sources_stale(conn, unread_sources)
            store.publish_cells(conn, cells)
            pruned = store.prune_rows(conn)
            store.write_changes(conn, run_id, changes)
            new_reviews = store.write_review_items(conn, run_id, reviews)
            resolved_reviews = store.resolve_review_items(conn, reviews, sorted(refreshed))
            if resolved_reviews:
                c.line(
                    "PUBLISH",
                    "OK",
                    f"{resolved_reviews} review item(s) resolved: this run read their source "
                    "and the problem did not come back",
                )
            # Each source read this run: its unmatched list is exactly what it listed now.
            for source_key in refreshed:
                store.replace_source_unmatched(
                    conn,
                    source_key,
                    {raw: u for (key, raw), u in run.unmatched.items() if key == source_key},
                )
        if pruned:
            shown = ", ".join(pruned[:8]) + (
                f" and {len(pruned) - 8} more" if len(pruned) > 8 else ""
            )
            c.line(
                "PUBLISH",
                "OK",
                f"{len(pruned)} row(s) no source lists any more removed: {shown}",
            )
        c.line(
            "PUBLISH",
            "OK",
            f"{len(cells)} cells written · {len(changes)} changelog entries · "
            f"{new_reviews} new review items"
            + (
                f" ({len(reviews) - new_reviews} already open)"
                if len(reviews) > new_reviews
                else ""
            ),
        )

    statuses = Counter(r.status for r in results)
    if dry_run:
        status = "dry_run"
    elif results and statuses.get("OK", 0) == 0:
        status = "error"
    elif statuses.get("OK", 0) < len(results):
        status = "partial"
    else:
        status = "ok"
    open_items = store.count_open_review_items(conn)
    rows_total = (
        len(store.existing_rows(conn)) if not dry_run else len(seed_rows) + len(run.new_rows)
    )
    report = {
        "sources": {r.key: r.report() for r in results},
        "totals": {
            "cells": len(cells),
            "changes": len(changes),
            "review_items": new_reviews,
            "open_review_items": open_items,
            "rows": rows_total,
        },
        "seed_models": len(seeds),
        "coverage": _coverage(config, seeds, cells),
    }
    _summary(c, run_id, status, results, started, new_reviews, open_items, report)
    return status, report


def _mark_stale(o: StoredObservation) -> bool:
    o.stale = True
    return True


def _coverage(config: Config, seeds: list[SeedModel], cells: dict) -> dict[str, Any]:
    models_with_any = {k[0].split(":", 1)[0] for k in cells}
    per_column: dict[str, int] = {}
    for _row_id, bench, metric in cells:
        per_column[f"{bench}_{metric}"] = per_column.get(f"{bench}_{metric}", 0) + 1
    columns = [f"{b.key}_{m}" for b in config.benchmarks.values() for m in b.metrics]
    return {
        "models_with_any_value": len(models_with_any),
        "models_without_any_value": sorted(s.name for s in seeds if s.id not in models_with_any),
        "filled_cells_per_column": {col: per_column.get(col, 0) for col in columns},
        "empty_columns": [col for col in columns if not per_column.get(col)],
    }


def _print_changes(c: Console, changes: list[dict], config: Config, previous: dict) -> None:
    c.line(
        "CHANGE",
        "OK",
        f"{len(changes)} changes"
        + ("  (first run: every value is new)" if not previous and changes else ""),
    )
    for ch in changes:
        if ch["change_type"] == "variant_added":
            c.text(f"           variant_added  {ch['note']}")
            continue
        col = f"{ch['benchmark_key']}_{ch['metric']}"
        old = "—" if ch.get("old_value") is None else f"{ch['old_value']:g}"
        new = "—" if ch.get("new_value") is None else f"{ch['new_value']:g}"
        extra = f"  ({ch['direction']})" if ch.get("direction") in ("better", "worse") else ""
        review = "  [needs review]" if ch.get("needs_review") else ""
        c.text(
            f"           {ch['change_type']:<14} {ch['row_id']:<34} {col:<26} {old:>7} -> {new:<7} "
            f"{ch.get('new_source') or ch.get('old_source')}{extra}{review}"
        )


def _summary(
    c: Console,
    run_id: int,
    status: str,
    results: list[SourceResult],
    started: float,
    new_reviews: int,
    open_items: int,
    report: dict,
) -> None:
    seconds = int(time.monotonic() - started)
    c.rule(level=SUMMARY)
    c.text(
        f" SUMMARY  run #{run_id}   status={status.upper()}   "
        f"duration {seconds // 60}m {seconds % 60:02d}s",
        level=SUMMARY,
    )
    c.text(
        f" {'source':<26} {'method':<10} {'status':<6} {'rows':>5} {'obs':>5} {'matched':>8} "
        f"{'rejected':>9} {'flagged':>8} {'changes':>8}",
        level=SUMMARY,
    )
    for r in results:
        c.text(
            f" {r.key:<26} {r.method:<10} {r.status:<6} {r.rows_parsed:>5} {r.observations:>5} "
            f"{r.matched_names:>8} {r.rejected:>9} {r.flagged:>8} {r.changes:>8}",
            level=SUMMARY,
        )
    alerts = []
    if status == "error":
        alerts.append("RUN FAILED: no source could be read")
    broken = [r.key for r in results if r.status in ("BLOCK", "FAIL")]
    if broken:
        alerts.append(
            f"SOURCE PROBLEM: {', '.join(broken)} - see the lines above; previous values kept"
        )
    if new_reviews or open_items:
        alerts.append(f"REVIEW QUEUE: {new_reviews} new, {open_items} open")
    missing = report["coverage"]["models_without_any_value"]
    if missing:
        alerts.append(f"NO VALUES YET for {len(missing)} tracked model(s): {', '.join(missing)}")
    if alerts:
        c.text(" ALERTS", level=SUMMARY)
        for a in alerts:
            c.text(f"  ! {a}", level=SUMMARY)
    if c.log_path is not None:
        try:
            shown = c.log_path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            shown = c.log_path.name
        c.text(f" Log file: {shown}", level=SUMMARY)
    c.rule(level=SUMMARY)
