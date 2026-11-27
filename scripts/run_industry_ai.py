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
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collect.config import settings  # noqa: E402
from collect.industry_ai import config as iai_config  # noqa: E402
from collect.industry_ai.config import PLATFORMS, WATCH_PLATFORMS  # noqa: E402

#: Every platform a run can touch: the keyword platforms, then any the observer
#: alone reads (Instagram, 2026-11-25), which get watch lists and no keyword queries.
ALL_PLATFORMS = (*PLATFORMS, *(p for p in WATCH_PLATFORMS if p not in PLATFORMS))

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


def raw_store():
    """This lane's raw store: LOCAL ONLY, never mirrored to the shared database.

    A harvested search page carries the full text of every post it returned -
    Personal posts and spam included - and the shared store (`raw_blob`, with
    RAW_STORE_REMOTE=postgres) keeps it for good. Text retention clears that text
    from `iai_item` after 30 days, which would mean nothing if the same words sat
    in `raw_blob` (#656 review; anooj chose this, 2026-11-24). So `remote=None`,
    whatever the environment says: on a GitHub runner the pages go when the run
    ends. Nothing reads them - every run re-labels from `iai_item`.
    """
    from collect.rawstore import RawStore

    return RawStore(Path(settings().raw_store_path), remote=None)


#: The two no-domain buckets are different absences (rule 4) and are named apart:
#: "general" = a watched post naming no industry; "unconfirmed" = a keyword query's
#: own domain not confirmed.
BUCKETS = {"general": "General AI", "unconfirmed": "Domain unconfirmed"}


def bucket_name(d: str, cfg) -> str:
    """A domain's name, or one of the two named buckets. ONE lookup for the run log
    AND the issue summary: the summary had its own, which called General AI
    "Unconfirmed" (found 2026-11-24, before the first real run). An unknown bucket
    raises rather than being relabelled (rule 12)."""
    if d in cfg.domains:
        return cfg.domains[d].name
    if d in BUCKETS:
        return BUCKETS[d]
    raise ValueError(f"counts name an unknown bucket {d!r}")


def print_counts(counts: dict, cfg) -> None:
    say(f"  items {counts['items']}, kept {counts['kept']}")
    if counts["dropped"]:
        say("  dropped, by stage and reason:")
        for k, n in counts["dropped"].items():
            say(f"    {k:<32} {n}")
    for d, c in counts["domains"].items():
        name = bucket_name(d, cfg)
        types =", ".join(f"{t} {n}" for t, n in sorted(c["by_type"].items(), key=lambda x: -x[1]))
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
        "| Domain | Kept | Use cases | How-to | Tools | Research | News | Discussion | Authors "
        "| From watch lists |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for d, c in counts["domains"].items():
        t = c["by_type"]
        # `From watch lists`: posts a watch list filed here by their terms, counted
        # APART from the domain's own kept posts (anooj, 2026-11-20, option (a)).
        lines.append(
            f"| {bucket_name(d, cfg)} | {c['kept']} | {t.get('use_case', 0)} | "
            f"{t.get('how_to', 0)} | {t.get('tool_or_product', 0)} | {t.get('research', 0)} | "
            f"{t.get('news', 0)} | {t.get('discussion', 0)} | {c['authors']} | "
            f"{c.get('from_watch', 0)} |"
        )
    capped = [q for q in queries if q["status"] == "capped"]
    failed = [q for q in queries if q["status"] == "error"]
    # NOT ASKED (2026-11-27): a platform refused before it started, or a watch list
    # stopped after `watch.stop_after_failures` failures in a row. Said here, never
    # left to read as accounts that posted nothing (rule 4).
    skipped = [q for q in queries if q["status"] == "skipped"]
    prune = [q for q in queries if q["status"] == "ok" and q["items"] == 0]
    if capped:
        lines += ["", f"{len(capped)} query(ies) not run: request cap reached."]
    if failed:
        # A failed search is not a prune candidate, so without this line it would
        # appear nowhere in the issue (rule 4; #648 review).
        lines += ["", f"{len(failed)} query(ies) failed - see the run log."]
    if skipped:
        by = sorted({q.get("platform") or "?" for q in skipped})
        lines += ["", f"{len(skipped)} query(ies) not asked ({', '.join(by)}): the platform "
                  "was refused, or its provider failed several in a row - see the run log."]
    if prune:
        lines += ["", f"{len(prune)} query(ies) returned nothing - prune?"]
    return "\n".join(lines) + "\n"


def post_summary(body: str) -> None:
    issue = os.getenv("INDUSTRY_AI_ISSUE")
    if not issue:
        say("INDUSTRY_AI_ISSUE not set; summary not posted")
        return
    subprocess.run(["gh", "issue", "comment", issue, "--body", body], cwd=ROOT, check=False)


def read_picture_text(conn, cfg, fresh, items, results, say) -> str:
    """STEP 6b: the text in the first picture of THIS run's "not readable" posts, in
    shadow mode (#679 step 3; CLAUDE.md's fourth fetch exception, #683). Only this
    run's posts carry a picture link (`Item.picture_url`, never stored). The labels are
    committed before this is called; the connection holds no transaction while the
    pictures are fetched. Returns one line for the run's detail."""
    from collections import Counter

    from collect.adapters.blog.robots import RobotsGate
    from collect.http import build_client
    from collect.industry_ai import ocr
    from collect.industry_ai import store as iai_store
    from collect.industry_ai.rules import (
        PICTURE_TEXT_AI_ONLY_FLAG,
        PICTURE_TEXT_FLAG,
        picture_text_flags,
    )

    t0 = time.perf_counter()
    linked = [it for it in fresh if it.picture_url]
    stored = iai_store.ocr_status_of(conn, [it.id for it in linked]) if linked else {}
    conn.commit()  # the status read is done; nothing is held across the downloads
    # A post first stored before the retention cutoff would be read and then cleared
    # in this same run (#687 review), so it is not a candidate.
    loaded = {it.id: it for it in items}
    not_before = datetime.now(UTC) - timedelta(days=int(cfg.retention["clear_text_after_days"]))
    wanted = ocr.candidates(
        linked, results, stored, not_before=not_before,
        first_seen={i: (loaded[i].first_seen_at if i in loaded else None)
                    for i in (it.id for it in linked)})
    with build_client(timeout=float(cfg.ocr["timeout_seconds"])) as client:
        gate = RobotsGate(client, user_agent=settings().user_agent)
        reads = ocr.read_pictures(wanted, cfg.ocr, client=client, gate=gate)
    # THE SHADOW FLAGS, computed on the stored item (its media text and labels) with the
    # text just read - the same function `evaluate` uses on every later run.
    by_id = {it.id: it for it in items}
    flags = {}
    for item_id, read in reads.items():
        base = by_id.get(item_id)
        if read.status == "ok" and base is not None:
            flags[item_id] = picture_text_flags(
                dataclasses.replace(base, ocr_text=read.text, ocr_confidence=read.confidence),
                cfg)
    iai_store.write_picture_reads(conn, reads, flags)
    secs = time.perf_counter() - t0
    status = Counter(r.status for r in reads.values())
    by_platform = Counter(i.split(":", 1)[0] for i, r in reads.items() if r.status == "ok")
    would = sum(PICTURE_TEXT_FLAG in f for f in flags.values())
    ai_only = sum(PICTURE_TEXT_AI_ONLY_FLAG in f for f in flags.values())
    # EVERY STATUS SAID, including refused and over the cap (rules 4 and 7): the shadow
    # week's counts come from these lines.
    say(f"\n6b Picture text (shadow mode, decides no label): {len(wanted)} not-readable "
        f"picture post(s) of this run with a link, of {len(linked)} with one; "
        + (", ".join(f"{k} {n}" for k, n in sorted(status.items())) or "none read")
        + f"; read by platform: {dict(sorted(by_platform.items())) or '-'}; "
        f"would pass {would} (of which `ai` alone {ai_only}); "
        f"min confidence {cfg.ocr['min_confidence']}; {secs:.1f}s")
    failed = Counter(r.detail.split(":")[0] for r in reads.values() if r.status == "failed")
    if failed:
        say(f"  failed, by cause: {dict(failed.most_common(8))}")
    return (f"picture text: {len(wanted)} candidate(s), "
            + ", ".join(f"{k} {n}" for k, n in sorted(status.items()))
            + f", would pass {would} (ai alone {ai_only}), {secs:.0f}s")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="list queries and caps; no network")
    mode.add_argument("--dry-run", action="store_true", help="harvest and count; write nothing")
    mode.add_argument(
        "--relabel", action="store_true", help="re-apply the rules to every stored item; no network"
    )
    which = ap.add_mutually_exclusive_group()
    which.add_argument("--domains", nargs="+", help="default: every active domain in the contract")
    # THE ROTATION (2026-11-25): a scheduled run harvests one of `run.rotation`'s two
    # groups, chosen by the UTC day (`auto`), so twenty domains run ten a day.
    which.add_argument(
        "--group", choices=("auto", *iai_config.ROTATION_GROUPS),
        help="one rotation group's active domains; `auto` = today's group (UTC)",
    )
    ap.add_argument("--platforms", nargs="+", choices=ALL_PLATFORMS, help="default: all")
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
    # THE OBSERVER IN ITS OWN RUN (2026-11-25): with `watch.enabled` true, a keyword
    # run would also read the watch lists; the daily schedule runs the keyword group
    # with --no-watch and the observer after it with --watch-only, each its own
    # `iai_run` row and summary.
    watch.add_argument(
        "--no-watch", action="store_true",
        help="keyword queries only, even while `watch.enabled` is true",
    )
    args = ap.parse_args(argv)

    cfg = iai_config.load()
    # THE CONTRACT CHOOSES WHICH DOMAINS RUN (`active`, #644 review, point 6);
    # --domains and --group narrow within them and never widen past them.
    active = cfg.active_domains
    group = None
    if args.group:
        group = cfg.group_for(datetime.now(UTC).date()) if args.group == "auto" else args.group
        # A group's `active: false` domain is skipped and SAID, not harvested: the
        # switch stays a domain's own, inside or outside the rotation.
        off = [d for d in cfg.group_domains(group) if d not in active]
        if off:
            say(f"  group {group}: {', '.join(off)} `active: false`, skipped")
    domains = (args.domains or ([d for d in cfg.group_domains(group) if d in active]
                                if group else active))
    if group and not domains:
        say(f"group {group}: no active domain - no keyword query runs.")
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
    platforms = args.platforms or list(ALL_PLATFORMS)
    run_id = f"iai-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    since = datetime.now(UTC) - timedelta(days=int(cfg.run["window_days"]))
    # THE OBSERVER'S WATCH LISTS run when the contract switches them on, or by hand
    # (`--watch`, `--watch-only`) for their own dry runs; never otherwise.
    watching = bool(args.watch or args.watch_only or (cfg.watch["enabled"] and not args.no_watch))
    watch_since = (datetime.now(UTC) - timedelta(days=int(cfg.watch["lookback_days"]))
                   if watching else None)
    keyword_domains = [] if args.watch_only else domains

    say(f"Industry AI agent | run {run_id} | pipeline {cfg.pipeline_version}"
        + (f" | group {group}" if group else ""))
    say(
        f"  domains: {', '.join(keyword_domains) or '(none: watch lists only)'} | "
        f"platforms: {', '.join(platforms)} | window {cfg.run['window_days']} days"
        + (f" | watch lists back {cfg.watch['lookback_days']} days" if watching else "")
    )

    from collect.industry_ai.harvest import plan, round_robin

    if args.plan:
        kw_platforms = [p for p in platforms if p in PLATFORMS]
        planned = plan(cfg, domains=keyword_domains, platforms=kw_platforms)
        say(f"\n1 Harvest (plan only; nothing is requested): {len(planned)} query(ies)")
        for p in kw_platforms:
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
        # BEFORE ANY REQUEST (#676 review): a database missing a column this
        # writer stores refuses here, not after the harvest has spent its caps.
        with psycopg.connect(dsn, connect_timeout=20) as conn:
            missing = iai_store.missing_columns(conn)
        if missing:
            raise SystemExit(
                f"iai_item has no column(s) {', '.join(missing)}: a migration has not been "
                "applied to this database. Run `python -m collect.cli db migrate` first. "
                "Nothing was requested."
            )
    cfg = dataclasses.replace(cfg, extra_ai_terms=_registry_names(dsn))
    is_bot = _bot_check()

    requests: dict = {}
    quota: dict = {}
    queries: list[dict] = []
    fresh = []
    if not args.relabel:
        from collect.http import build_client
        from collect.industry_ai.harvest import harvest
        from collect.registry.sources import load_sources

        say("\n1 Harvest")
        got = harvest(
            cfg,
            domains=keyword_domains,
            platforms=platforms,
            contract=load_sources(),
            store=raw_store(),
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
        saved = None  # new items COMMITTED before labelling; None until then
        labelled = False  # labels COMMITTED before the picture text is read
        try:
            t_store = time.perf_counter()
            new = iai_store.upsert_items(conn, fresh, run_id=run_id) if fresh else 0
            # THE HARVEST IS SAVED BEFORE ANYTHING IS LABELLED (#659 review): the
            # requests are spent by now, so a labelling failure must not roll the posts
            # back with it. A new row waits as verdict 'dropped' / drop_stage 'pending'
            # (store._UPSERT) until the next run or a --relabel labels it.
            conn.commit()
            saved = new
            store_s = time.perf_counter() - t_store
            items = iai_store.load_items(conn)
            # `items` leaves out rows whose text retention cleared: they keep their
            # labels and are not re-judged, so they are not "stored in all".
            say(f"\n6 Store: {new} new item(s), saved in {store_s:.1f}s; {len(items)} stored "
                "with their text (rows whose text was cleared keep their labels)")
            # LABELLED OVER THE WHOLE COLLECTION, so dedupe sees every copy and a
            # rule change applies to old items as well as new ones.
            t_label = time.perf_counter()
            results, counts = evaluate(items, cfg, since=since, is_bot=is_bot)
            iai_store.write_labels(conn, results, pipeline_version=cfg.pipeline_version)
            label_s = time.perf_counter() - t_label
            # OVER ROWS WITH THEIR TEXT (#656 review): cleared rows are not loaded,
            # so these counts shrink as rows age while the page counts every row.
            say("\n2-5 Sieve | Dedupe | Filter | Label (over rows with their text; rows "
                "whose text was cleared keep their labels and are counted on the page, "
                "not here)")
            print_counts(counts, cfg)
            # THE TIMES, so a slowdown shows in the log before it reaches the job's
            # limit (#659 review, rule 11: measured on every run, never written down).
            say(f"  labelled {len(results)} item(s) in {label_s:.1f}s")
            # THE LABELS ARE COMMITTED BEFORE ANY PICTURE IS FETCHED: the downloads are
            # network work, and the shared database closes a transaction left idle for
            # 15 minutes (2026-11-26, #678); a picture failure must not cost the labels.
            conn.commit()
            labelled = True
            pictures = ""
            if cfg.ocr["enabled"] and not args.relabel:
                pictures = read_picture_text(conn, cfg, fresh, items, results, say)
                conn.commit()
            # TEXT RETENTION (contract `retention:`, anooj 2026-11-24): after the
            # labels, so a row is cleared with the labels its text earned.
            cleared = iai_store.clear_text(conn, cfg.retention)
            # Picture text is cleared at the same age WHATEVER the post's label (CLAUDE.md
            # fourth fetch exception, condition 3; #683).
            cleared_pictures = iai_store.clear_picture_text(conn, cfg.retention)
            r = cfg.retention
            say(f"\n7 Retention: text cleared on {cleared} row(s) first stored over "
                f"{r['clear_text_after_days']} days ago ("
                + ("dropped, and " if r["dropped"] else "")
                + f"kept under {', '.join(r['kept_domains']) or 'no domain'}); rows kept. "
                f"Picture text cleared on {cleared_pictures} row(s), whatever their label")
            iai_store.finish_run(
                conn,
                run_id,
                status="ok",
                requests=requests,
                quota=quota,
                queries=queries,
                counts=counts,
                detail=(f"{new} new item(s); text cleared on {cleared} row(s), picture "
                        f"text on {cleared_pictures}; store {store_s:.1f}s, label "
                        f"{label_s:.1f}s" + (f"; {pictures}" if pictures else "")),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            # Rolled back: the labels and the text clearing. NOT the harvest, if it was
            # saved - so the run says which, and how to finish the job.
            kept = (
                f"{saved} new item(s) and their labels SAVED before the error (it came "
                "while reading picture text or clearing text). "
                if labelled else
                f"{saved} new item(s) SAVED before the error; labels not written (new rows "
                "wait as 'pending' for the next run or --relabel). "
                if saved is not None else "nothing saved. "
            )
            iai_store.finish_run(
                conn,
                run_id,
                status="error",
                requests=requests,
                quota=quota,
                queries=queries,
                counts={},
                detail=(kept + f"{type(e).__name__}: {e}")[:500],
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
