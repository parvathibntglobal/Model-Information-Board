#!/usr/bin/env python
"""Run the Industry AI agent: harvest AI-in-industry data, label it, store it.

    python scripts/run_industry_ai.py --plan        # list queries and caps; no network
    python scripts/run_industry_ai.py --dry-run     # harvest and count; write nothing
    python scripts/run_industry_ai.py               # harvest, label, store
    python scripts/run_industry_ai.py --relabel     # re-apply the rules to stored items;
                                                    # no network
    ... --domains finance healthcare --platforms hackernews devto

Everything tunable lives in contract/industry_ai.yaml. A separate lane: this
writes `iai_item` and `iai_run` only, and calls no language model.

STAGES, IN RUN ORDER (the numbers ARE the order):
  1 Harvest   the contract's queries per domain and platform, each platform
              through its own gated entry point, within `run.max_requests`
  2 Sieve     posted inside `run.window_days` (an undated item is kept), and
              an AI term and a domain term outside the excluded phrases
  3 Dedupe    a shared article link, a repeated post, near-duplicate text
  4 Filter    too short, bot, language, spam, promo, hiring, sign-up ad
  5 Label     confirmed domain(s), content type, a use case's stage
  6 Store     every item with its verdict; counts for the page and the log

SPEND: Reddit and X are metered (RapidAPI). Every platform has a request cap
per run, checked before each query. `--plan` and `--relabel` make no request.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collect.config import settings  # noqa: E402
from collect.industry_ai import config as iai_config  # noqa: E402
from collect.industry_ai.config import PLATFORMS  # noqa: E402

#: The bot list's source name per platform (contract/bots.yaml).
BOT_SOURCES = {
    "reddit": "reddit",
    "x": "x",
    "github": "github",
    "hackernews": "hackernews",
    "devto": "devto",
    "bluesky": "bluesky",
}


def say(line: str = "") -> None:
    print(line, flush=True)


def _registry_names(dsn: str | None) -> tuple[str, ...]:
    """Registry model names as extra AI terms, read-only. Empty when the
    database cannot be read - the contract's own terms still apply."""
    if not dsn:
        return ()
    import psycopg

    try:
        with psycopg.connect(
            dsn, connect_timeout=10, options="-c default_transaction_read_only=on"
        ) as conn:
            rows = conn.execute(
                "SELECT display_name FROM model_version WHERE display_name IS NOT NULL"
            ).fetchall()
    except Exception as e:  # noqa: BLE001 - the contract's terms still apply
        say(f"  registry names not read ({type(e).__name__}); contract ai_terms only")
        return ()
    names = set()
    for (name,) in rows:
        short = name.split(": ", 1)[-1].strip()
        if len(short) >= 4 and any(ch.isdigit() for ch in short):
            names.add(short)
    return tuple(sorted(names))


def _bot_check():
    from collect.triage.bots import load_bot_list

    bots = load_bot_list()
    if bots is None:
        return lambda item: False

    # ONLY WHERE THE LIST DECLARES THE PLATFORM: elsewhere "is this a bot" is
    # unanswered, not "no" (collect/triage/bots.py), and the item is kept.
    def is_bot(item) -> bool:
        source = BOT_SOURCES.get(item.platform)
        return bool(
            item.author_id
            and source
            and bots.declares(source)
            and bots.contains(source, item.author_id)
        )

    return is_bot


def print_counts(counts: dict, cfg) -> None:
    say(f"  items {counts['items']}, kept {counts['kept']}")
    if counts["dropped"]:
        say("  dropped, by stage and reason:")
        for k, n in counts["dropped"].items():
            say(f"    {k:<32} {n}")
    # The two no-domain buckets are different absences (rule 4) and are named apart:
    # "general" = a watched post naming no industry; "unconfirmed" = a keyword query's
    # own domain not confirmed.
    buckets = {"general": "General AI", "unconfirmed": "Domain unconfirmed"}
    for d, c in counts["domains"].items():
        if d in cfg.domains:
            name = cfg.domains[d].name
        elif d in buckets:
            name = buckets[d]
        else:
            raise ValueError(f"counts name an unknown bucket {d!r}")  # rule 12: never relabel
        types = ", ".join(f"{t} {n}" for t, n in sorted(c["by_type"].items(), key=lambda x: -x[1]))
        plats = ", ".join(
            f"{p} {n}" for p, n in sorted(c["by_platform"].items(), key=lambda x: -x[1])
        )
        watch_note = (f"  (+ {c['from_watch']} from watch lists, counted apart)"
                      if c.get("from_watch") else "")
        say(f"  {name:<20} kept {c['kept']:<5} authors {c['authors']:<5} reach {c['reach']}"
            + watch_note)
        say(f"    types: {types or '-'}")
        if c.get("by_group"):
            groups = ", ".join(
                f"{g} {n}" for g, n in sorted(c["by_group"].items(), key=lambda x: -x[1])
            )
            say(f"    groups: {groups}")
        say(f"    platforms: {plats or '-'}")


def _summary(run_id: str, mode: str, requests: dict, counts: dict, queries: list, cfg) -> str:
    """The issue comment: counts only, no text, no author, no host."""
    lines = [
        f"**Industry AI run `{run_id}` ({mode})**",
        "",
        f"Items {counts['items']}, kept {counts['kept']}. "
        f"Requests: {', '.join(f'{p} {n}' for p, n in requests.items() if n) or 'none'}.",
        "",
        "| Domain | Kept | Use cases | How-to | Tools | Research | News | Discussion | Authors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for d, c in counts["domains"].items():
        t = c["by_type"]
        name = cfg.domains[d].name if d in cfg.domains else "Unconfirmed"
        lines.append(
            f"| {name} | {c['kept']} | {t.get('use_case', 0)} | {t.get('how_to', 0)} | "
            f"{t.get('tool_or_product', 0)} | {t.get('research', 0)} | "
            f"{t.get('news', 0)} | {t.get('discussion', 0)} | {c['authors']} |"
        )
    capped = [q for q in queries if q["status"] == "capped"]
    failed = [q for q in queries if q["status"] == "error"]
    prune = [q for q in queries if q["status"] == "ok" and q["items"] == 0]
    if capped:
        lines += ["", f"{len(capped)} query(ies) not run: request cap reached."]
    if failed:
        # A failed search is not a prune candidate, so without this line it would
        # appear nowhere in the issue (rule 4; #648 review).
        lines += ["", f"{len(failed)} query(ies) failed - see the run log."]
    if prune:
        lines += ["", f"{len(prune)} query(ies) returned nothing - prune?"]
    return "\n".join(lines) + "\n"


def post_summary(body: str) -> None:
    issue = os.getenv("INDUSTRY_AI_ISSUE")
    if not issue:
        say("INDUSTRY_AI_ISSUE not set; summary not posted")
        return
    subprocess.run(["gh", "issue", "comment", issue, "--body", body], cwd=ROOT, check=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="list queries and caps; no network")
    mode.add_argument("--dry-run", action="store_true", help="harvest and count; write nothing")
    mode.add_argument(
        "--relabel", action="store_true", help="re-apply the rules to every stored item; no network"
    )
    ap.add_argument("--domains", nargs="+", help="default: every domain in the contract")
    ap.add_argument("--platforms", nargs="+", choices=PLATFORMS, help="default: all")
    ap.add_argument(
        "--post-summary",
        action="store_true",
        help="comment the run's counts on INDUSTRY_AI_ISSUE (the workflow)",
    )
    watch = ap.add_mutually_exclusive_group()
    watch.add_argument(
        "--watch",
        action="store_true",
        help="also run the observer's watch lists, even while `watch.enabled` is false",
    )
    watch.add_argument(
        "--watch-only",
        action="store_true",
        help="run ONLY the observer's watch lists (its own dry run), no keyword queries",
    )
    args = ap.parse_args(argv)

    cfg = iai_config.load()
    # THE CONTRACT CHOOSES WHICH DOMAINS RUN (`active`, #644 review, point 6);
    # --domains narrows within them and never widens past them.
    active = cfg.active_domains
    domains = args.domains or active
    unknown = [d for d in domains if d not in cfg.domains]
    if unknown:
        raise SystemExit(f"unknown domain(s) {unknown}; the contract has {list(cfg.domains)}")
    inactive = [d for d in domains if d not in active]
    if inactive:
        raise SystemExit(
            f"domain(s) {inactive} are `active: false` in contract/industry_ai.yaml; "
            f"active: {active}"
        )
    # `run.enabled: false` REFUSES A HARVEST (#644 review, point 9). Plan, dry
    # run and relabel make no stored request, so they still run.
    harvesting = not (args.plan or args.dry_run or args.relabel)
    if harvesting and not cfg.run["enabled"]:
        say(
            "run.enabled is false in contract/industry_ai.yaml - nothing harvested. "
            "This is the switch, not a failure."
        )
        return 0
    platforms = args.platforms or list(PLATFORMS)
    run_id = f"iai-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    since = datetime.now(UTC) - timedelta(days=int(cfg.run["window_days"]))
    # THE OBSERVER'S WATCH LISTS run when the contract switches them on, or by hand
    # (`--watch`, `--watch-only`) for their own dry runs; never otherwise.
    watching = bool(args.watch or args.watch_only or cfg.watch["enabled"])
    watch_since = (datetime.now(UTC) - timedelta(days=int(cfg.watch["lookback_days"]))
                   if watching else None)
    keyword_domains = [] if args.watch_only else domains

    say(f"Industry AI agent | run {run_id} | pipeline {cfg.pipeline_version}")
    say(
        f"  domains: {', '.join(keyword_domains) or '(none: watch lists only)'} | "
        f"platforms: {', '.join(platforms)} | window {cfg.run['window_days']} days"
        + (f" | watch lists back {cfg.watch['lookback_days']} days" if watching else "")
    )

    from collect.industry_ai.harvest import plan, round_robin

    if args.plan:
        planned = plan(cfg, domains=keyword_domains, platforms=platforms)
        say(f"\n1 Harvest (plan only; nothing is requested): {len(planned)} query(ies)")
        for p in platforms:
            qs = [(d, q) for d, pp, q in planned if pp == p]
            qs = round_robin(qs)
            if not qs:
                continue
            say(f"  {p}: {len(qs)} query(ies), cap {cfg.run['max_requests'][p]} request(s)")
            for d, q in qs:
                extra = f"  [{cfg.x_pages(q)} page(s)]" if p == "x" else ""
                say(f"    {d:<24} {q}{extra}")
        if watching:
            wq = [(p, q) for p, q in cfg.watch_queries() if p in platforms]
            say(f"\n  WATCH LISTS (the observer): {len(wq)} source(s)")
            for p in sorted({p for p, _ in wq}):
                qs = [q for pp, q in wq if pp == p]
                cap = cfg.watch["max_requests"][p]
                say(f"  watch {p}: {len(qs)} source(s), cap {cap} request(s)")
                for q in qs:
                    extra = f"  [{cfg.x_pages(q)} page(s)]" if p == "x" else ""
                    say(f"    {q}{extra}")
        return 0

    import psycopg

    from collect.industry_ai import store as iai_store
    from collect.industry_ai.pipeline import evaluate

    dsn = settings().database_url
    if not args.dry_run:
        if not dsn:
            raise SystemExit("DATABASE_URL is not set; nothing to write to")
        from judge.writeguard import check as writeguard_check

        writeguard_check(dsn, command="run_industry_ai.py")
    cfg = dataclasses.replace(cfg, extra_ai_terms=_registry_names(dsn))
    is_bot = _bot_check()

    requests: dict = {}
    quota: dict = {}
    queries: list[dict] = []
    fresh = []
    if not args.relabel:
        from collect.http import build_client
        from collect.industry_ai.harvest import harvest
        from collect.rawstore import RawStore
        from collect.registry.sources import load_sources

        say("\n1 Harvest")
        got = harvest(
            cfg,
            domains=keyword_domains,
            platforms=platforms,
            contract=load_sources(),
            store=RawStore(Path(settings().raw_store_path)),
            client_factory=build_client,
            since=since,
            log=say,
            watch_since=watch_since,
        )
        for n in got.notes:
            say(f"  {n}")
        requests, quota = got.requests, got.quota
        queries = [q.__dict__ for q in got.queries]
        fresh = list(got.items.values())
        for s in got.queries:
            if s.status != "ok":
                say(f"    [{s.status}] {s.domain}/{s.platform}: {s.query} - {s.detail}")
        watched = [s for s in got.queries if s.domain == "watch" and s.status == "ok"]
        if watched:
            # EVERY WATCH SOURCE'S YIELD, so a community or account that brings nothing
            # is seen on the first run, not after weeks (prune by yield, never by guess).
            say("  watch sources, items returned (before any rule):")
            for s in sorted(watched, key=lambda s: (s.platform, -s.items)):
                say(f"    {s.platform:<11} {s.items:>4}  {s.query}")
        say(f"  {len(fresh)} distinct item(s) from {sum(requests.values())} request(s)")
        if quota:
            say(f"  quota: {quota}")

    if args.dry_run:
        results, counts = evaluate(fresh, cfg, since=since, is_bot=is_bot)
        say("\n2-5 Sieve | Dedupe | Filter | Label (this run's items only; nothing written)")
        print_counts(counts, cfg)
        return 0

    with psycopg.connect(dsn, connect_timeout=20) as conn:
        iai_store.start_run(
            conn,
            run_id,
            mode="relabel" if args.relabel else "harvest",
            domains=domains,
            platforms=platforms,
            pipeline_version=cfg.pipeline_version,
        )
        conn.commit()
        try:
            new = iai_store.upsert_items(conn, fresh, run_id=run_id) if fresh else 0
            items = iai_store.load_items(conn)
            say(f"\n6 Store: {new} new item(s); {len(items)} stored in all")
            # LABELLED OVER THE WHOLE COLLECTION, so dedupe sees every copy and a
            # rule change applies to old items as well as new ones.
            results, counts = evaluate(items, cfg, since=since, is_bot=is_bot)
            iai_store.write_labels(conn, results, pipeline_version=cfg.pipeline_version)
            say("\n2-5 Sieve | Dedupe | Filter | Label (whole collection)")
            print_counts(counts, cfg)
            iai_store.finish_run(
                conn,
                run_id,
                status="ok",
                requests=requests,
                quota=quota,
                queries=queries,
                counts=counts,
                detail=f"{new} new item(s)",
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            iai_store.finish_run(
                conn,
                run_id,
                status="error",
                requests=requests,
                quota=quota,
                queries=queries,
                counts={},
                detail=f"{type(e).__name__}: {e}"[:500],
            )
            conn.commit()
            raise
    if args.post_summary:
        post_summary(
            _summary(
                run_id, "relabel" if args.relabel else "harvest", requests, counts, queries, cfg
            )
        )
    say(f"\nrun {run_id} ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
