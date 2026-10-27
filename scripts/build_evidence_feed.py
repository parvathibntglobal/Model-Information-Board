"""Fill the evidence feed: embeds, paraphrases and summary drafts (PROPOSED).

    python scripts/build_evidence_feed.py                      # what is pending, writes nothing
    python scripts/build_evidence_feed.py --embeds --apply     # resolve Reddit/X embeds
    python scripts/build_evidence_feed.py --paraphrase --apply [--model ID] [--limit N]
    python scripts/build_evidence_feed.py --summaries --apply [--model ID]

Run after extraction: a report extracted tonight is paraphrased tonight, so
the feed's newest items are the newest reports. Order matters only for
summaries, which are written from paraphrases.

A SCRIPT, NOT judge/, BECAUSE IT COMPOSES THE TWO LANES. A Reddit link post's
`document.url` is the LINKED content, not the thread, so the post address an
embed needs is read from the raw payload through collect's reader - which
judge/ may not import (tests/test_lane_boundary.py). The paraphrases and
summaries are judge/feed/'s; this only supplies them a connection.

WRITES GO TO `DATABASE_URL`, which is the SHARED staging DB on this team's
machines. The host is printed before anything is written, and nothing is
written without `--apply`. Writes are upserts of derived rows, never evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REDDIT_POST = re.compile(r"^https://www\.reddit\.com/r/(\w+)/comments/\w+")
X_POST = re.compile(r"^https://(?:x|twitter)\.com/\w+/status/\d+")
#: Reddit's oEmbed is asked at most this often.
OEMBED_INTERVAL_S = 1.1


def _env() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")


def _connect(*, writing: bool):
    import psycopg

    from judge import writeguard

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is not set")
    # WRITES ONLY. ENVIRONMENT=development against a remote database is refused
    # here, so writing to shared staging takes ENVIRONMENT=staging, said on
    # purpose. A dry run only reads and is allowed from anywhere.
    if writing:
        writeguard.check(dsn, command="build_evidence_feed --apply")
    print(f"database: {dsn.split('@')[-1].split('/')[0]}")
    return psycopg.connect(dsn, connect_timeout=20)


def _post_address(source: str, url: str | None, text_ref: str | None, reader) -> str | None:
    """The post itself, which an official embed needs; None, never a guess."""
    if source == "x":
        return url if url and X_POST.match(url) else None
    if url and REDDIT_POST.match(url):
        return url
    if not text_ref:
        return None
    got = reader.resolve(text_ref)
    try:
        path = (json.loads(got.text) or {}).get("permalink") if got.text else None
    except (json.JSONDecodeError, AttributeError):
        path = None
    full = f"https://www.reddit.com{path}" if isinstance(path, str) else None
    return full if full and REDDIT_POST.match(full) else None


#: Reddit's oEmbed answers that mean the post itself is gone or hidden. Only
#: these are stored as `unavailable`: the row is permanent (it is never
#: retried), and the page tells readers the post was deleted or removed.
GONE = (403, 404)


def embeds(conn, *, apply: bool, limit: int | None, client=None, reader=None,
           sleep=time.sleep) -> dict:
    """One `feed_embed` row per Reddit/X document behind a board entry.

    A FAILURE TO ASK IS NOT AN ANSWER (2026-10-23, #558 second review). A 429,
    a 5xx, a blocked User-Agent or a dropped connection says nothing about the
    post, so nothing is stored for it: the document stays pending and the next
    run asks again, and the report counts it under `retry_later` by reason.
    Storing those as `unavailable` - as this did - labelled live posts "deleted"
    for good after one rate-limited stretch (rules 6 and 12).

    WHAT IS STORED IS THE ID-ONLY ADDRESS (`judge.feed.items.canonical_embed_url`):
    no subreddit, no title slug, no handle. The full permalink is used only to
    ask Reddit's oEmbed, and kept nowhere."""
    import httpx

    from collect.rawstore import RawStore
    from collect.rawstore_reader import RawStoreReader
    from judge import publication
    from judge.feed.items import canonical_embed_url, embed_ids

    embed_only = list(publication.evidence_feed_terms()["embed_only"])
    rows = conn.execute(
        "SELECT DISTINCT d.id, d.source, d.url, d.text_ref FROM board_entry be "
        "JOIN document d ON d.id = be.document_id "
        "LEFT JOIN feed_embed fe ON fe.document_id = d.id "
        "WHERE d.source = ANY(%s) AND fe.document_id IS NULL "
        "  AND be.ruling IS DISTINCT FROM 'declined'",
        (embed_only,),
    ).fetchall()
    rows = rows[:limit] if limit else rows
    report = {"pending": len(rows), "embeddable": 0, "no_post_address": 0, "unavailable": 0,
              "retry_later": {}}
    if not apply:
        return report
    own_client = client is None
    if own_client:
        ua = os.environ.get("USER_AGENT")
        if not ua:
            raise SystemExit(
                "USER_AGENT is not set; Reddit's oEmbed needs an identifying User-Agent")
        client = httpx.Client(headers={"User-Agent": ua}, timeout=20, follow_redirects=True)
    if reader is None:
        reader = RawStoreReader(RawStore(os.environ.get("RAW_STORE_PATH") or "./raw_store"))
    last = 0.0
    try:
        for doc, source, url, text_ref in rows:
            address = _post_address(source, url, text_ref, reader)
            ids = embed_ids(source, address) if address else None
            outcome = "embeddable" if ids else "no_post_address"
            if ids and source == "reddit":
                wait = OEMBED_INTERVAL_S - (time.monotonic() - last)
                if wait > 0:
                    sleep(wait)
                last = time.monotonic()
                try:
                    r = client.get("https://www.reddit.com/oembed", params={"url": address})
                except httpx.HTTPError as e:
                    reason = type(e).__name__
                    report["retry_later"][reason] = report["retry_later"].get(reason, 0) + 1
                    continue
                if r.status_code in GONE:
                    # Deleted or removed: said on the page, never an embed of nothing.
                    outcome = "unavailable"
                elif r.status_code != 200:
                    reason = f"HTTP {r.status_code}"
                    report["retry_later"][reason] = report["retry_later"].get(reason, 0) + 1
                    continue
            conn.execute(
                "INSERT INTO feed_embed (document_id, platform, outcome, url) "
                "VALUES (%s,%s,%s,%s) ON CONFLICT (document_id) DO NOTHING",
                (doc, source, outcome,
                 canonical_embed_url(source, ids) if outcome == "embeddable" else None),
            )
            report[outcome] += 1
            conn.commit()
    finally:
        if own_client:
            client.close()
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--embeds", action="store_true")
    ap.add_argument("--paraphrase", action="store_true")
    ap.add_argument("--summaries", action="store_true")
    ap.add_argument("--model", help="one model, by canonical or registry id")
    ap.add_argument("--limit", type=int, help="at most this many reports or documents")
    ap.add_argument("--apply", action="store_true", help="write; without it, report only")
    args = ap.parse_args(argv)
    _env()

    from judge.config import evidence_feed_settings
    from judge.feed import paraphrase, summary
    from judge.feed.items import resolve_model
    from judge.feed.llm import FeedModelUnavailable

    cfg = evidence_feed_settings()
    p_cfg = cfg["paraphrase"]
    s_cfg = cfg["summary"]
    with _connect(writing=args.apply) as conn:
        model_key = resolve_model(conn, args.model)["key"] if args.model else None
        nothing = not (args.embeds or args.paraphrase or args.summaries)

        if args.embeds or nothing:
            print("embeds:", embeds(conn, apply=args.apply and args.embeds, limit=args.limit))

        if args.paraphrase or nothing:
            units, not_allowed = paraphrase.pending(
                conn, p_cfg["prompt_version"], model_key=model_key
            )
            units = units[: args.limit] if args.limit else units
            calls = sum(-(-n // p_cfg["per_call"]) for n in _per_model(units).values())
            print(
                f"paraphrase: {len(units)} reports pending, about {calls} calls"
                + (f"; {not_allowed} left out by the publication terms" if not_allowed else "")
            )
            if args.apply and args.paraphrase and units:
                report = paraphrase.run(conn, units, p_cfg, log=print)
                print("paraphrase:", json.dumps(report, indent=2))

        if args.summaries or nothing:
            due = (
                [{"model_key": model_key}]
                if model_key
                else summary.models_due(conn, p_cfg["prompt_version"], s_cfg["min_reports"])
            )
            print(f"summaries: {len(due)} models due for a draft")
            if args.apply and args.summaries:
                for d in due:
                    try:
                        out = summary.draft(conn, d["model_key"], s_cfg, p_cfg["prompt_version"])
                    except (summary.NotEnoughReports, FeedModelUnavailable) as e:
                        out = {"stored": False, "refused": str(e)}
                    print(
                        f"  {d['model_key']}: "
                        + (
                            f"stored {out['id']} ({len(out['flags'])} flags)"
                            if out["stored"]
                            else f"not stored - {out['refused']}"
                        )
                    )
    return _flush_spend() if args.apply else 0


def _flush_spend() -> int:
    """Send the calls the shared spend table missed during the run (2026-10-26).

    Every call is in this machine's spend file; the shared table is what every
    machine's daily cap reads, and a slow connection mid-run skips it. One
    patient attempt here, and if rows still did not get there the run SAYS SO
    and exits 1 - spend the cap cannot see is not a quiet success.
    """
    from judge import spend_ledger

    sent = spend_ledger.flush_unmirrored()
    if sent.written:
        print(f"spend: {sent.written} call(s) the shared ledger missed during the run, now sent")
    left = spend_ledger.unmirrored_count()
    if left:
        print(f"spend: {left} call(s) are NOT in the shared ledger ({sent.reason or sent.status}); "
              f"they are in {spend_ledger.ledger_path()} - run "
              "`python scripts/backfill_telemetry.py --apply`", file=sys.stderr)
        return 1
    return 0


def _per_model(units: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for u in units:
        out[u["model_key"]] = out.get(u["model_key"], 0) + 1
    return out


if __name__ == "__main__":
    sys.exit(main())
