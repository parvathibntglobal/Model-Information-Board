# ruff: noqa: E501 - a measurement script: its report lines are kept whole so the printed output reads as one record.
"""Can our data carry the hooks? Three read-only measurements, 2026-11-02.

Run against the shared database with a read-only session:
    DATABASE_URL=<railway>?options=-c%20default_transaction_read_only%3Don \\
        python docs/measurements/hooks-feasibility-2026-11-02.py

Output is saved beside this file (.out.txt). Every count states its population
(rule 7). "When a report was made" is the DOCUMENT's own date (document.created_at),
never when we extracted it (board_entry.created_at) - a backlog extracted in one
night would otherwise look like a spike.

1. RADAR - "did it get worse?": problem reports per model per week. Are there
   weeks that stand out, and is there enough volume per model for a spike to
   mean anything?
2. PASTE YOUR ERROR - how many board entries come from a document flagged as
   carrying an error string, and how many quotes themselves name an error.
3. WATCH MY MODELS - for each tracked model, did anything change in the last
   30 days: a price or deprecation event, a retirement date, new reports?
"""

from __future__ import annotations

import os
import re
import statistics
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import psycopg

NOW = datetime.now(UTC)
WEEKS = 13
ERRORISH = re.compile(r"\b(error|exception|traceback|429|500|502|503|timeout|timed out|rate.?limit|"
                      r"invalid|refus\w*|overloaded|context length|max_tokens|404)\b", re.I)


def main() -> None:
    dsn = os.environ["DATABASE_URL"]
    assert "default_transaction_read_only" in dsn, "run with a read-only DSN"
    with psycopg.connect(dsn) as c:
        c.read_only = True
        names = dict(c.execute("SELECT id, display_name FROM model_version").fetchall())
        radar(c, names)
        errors(c, names)
        watch(c, names)


def radar(c, names) -> None:
    since = NOW - timedelta(weeks=WEEKS)
    rows = c.execute("""
        SELECT be.model_version_id, date_trunc('week', d.created_at)::date AS wk, be.polarity,
               count(DISTINCT d.id)
        FROM board_entry be JOIN document d ON d.id = be.document_id
        WHERE d.created_at >= %s AND be.model_version_id IS NOT NULL
        GROUP BY 1, 2, 3""", (since,)).fetchall()
    per: dict = defaultdict(lambda: defaultdict(lambda: {"negative": 0, "all": 0}))
    for mv, wk, pol, n in rows:
        per[mv][wk]["all"] += n
        if pol == "negative":
            per[mv][wk]["negative"] += n
    weeks = sorted({wk for m in per.values() for wk in m})
    print("=" * 100)
    print(f"1. RADAR. Population: board entries whose document is dated in the last {WEEKS} weeks "
          f"(since {since.date()}), counted as DISTINCT DOCUMENTS per model, week and polarity.")
    totals = sorted(((sum(w["all"] for w in m.values()), mv) for mv, m in per.items()), reverse=True)
    print(f"   models with any report: {len(totals)}; with >= 50 documents in {WEEKS} weeks: "
          f"{sum(1 for t, _ in totals if t >= 50)}; with >= 10 negative in one week ever: "
          f"{sum(1 for _, mv in totals if any(w['negative'] >= 10 for w in per[mv].values()))}")
    print(f"   weeks: {weeks[0]} .. {weeks[-1]}  (each column below is one week; NEG/ALL documents)")
    flagged = 0
    for total, mv in totals[:15]:
        series = [per[mv].get(wk, {"negative": 0, "all": 0}) for wk in weeks]
        negs = [w["negative"] for w in series]
        med = statistics.median(negs)
        marks = [f"{w['negative']}/{w['all']}" + ("*" if w["negative"] >= max(5, 2 * med) and med >= 1 else "")
                 for w in series]
        flagged += sum(1 for m in marks if m.endswith("*"))
        print(f"   {names.get(mv, mv)[:34]:34} total {total:4}  median neg/wk {med:4.1f}  " + " ".join(marks))
    print(f"   * = a week with >= 5 negative documents AND >= 2x that model's median weekly negatives "
          f"(an illustration of what a flag could look like - an UNMEASURED rule, never a gate). "
          f"{flagged} such weeks across the 15 busiest models.")


def errors(c, names) -> None:
    print("=" * 100)
    rows = c.execute("""
        SELECT be.model_version_id, be.quote, d.has_error_strings
        FROM board_entry be JOIN document d ON d.id = be.document_id
        WHERE be.model_version_id IS NOT NULL""").fetchall()
    total = len(rows)
    flagged = sum(1 for _, _, f in rows if f)
    quoting = [(mv, q) for mv, q, _ in rows if q and ERRORISH.search(q)]
    print(f"2. PASTE YOUR ERROR. Population: all {total} board entries with a model.")
    print(f"   entries from a document flagged has_error_strings: {flagged} ({flagged / total:.1%})")
    print(f"   entries whose QUOTE itself matches an error pattern (the text we would show): "
          f"{len(quoting)} ({len(quoting) / total:.1%}) - pattern: {ERRORISH.pattern[:90]}...")
    by = defaultdict(int)
    for mv, _ in quoting:
        by[mv] += 1
    print("   by model (top 10): " + "; ".join(f"{names.get(m, m)[:28]} {n}" for m, n in
                                             sorted(by.items(), key=lambda x: -x[1])[:10]))
    print("   sample quotes (first 6 by model order):")
    for mv, q in quoting[:6]:
        print(f"     [{names.get(mv, mv)[:24]}] {q[:150]}")


def watch(c, names) -> None:
    print("=" * 100)
    since = NOW - timedelta(days=30)
    tracked = [r[0] for r in c.execute("""
        SELECT DISTINCT model_version_id FROM board_entry WHERE model_version_id IS NOT NULL""").fetchall()]
    ev = defaultdict(list)
    for mv, typ in c.execute("""SELECT model_version_id, type FROM model_event
                                WHERE coalesce(occurred_at, detected_at) >= %s""", (since,)).fetchall():
        ev[mv].append(typ)
    retire = dict(c.execute("""SELECT id, retirement_date FROM model_version
                               WHERE retirement_date IS NOT NULL""").fetchall())
    reports = dict(c.execute("""
        SELECT be.model_version_id, count(DISTINCT d.id) FROM board_entry be
        JOIN document d ON d.id = be.document_id
        WHERE d.created_at >= %s AND be.model_version_id IS NOT NULL GROUP BY 1""", (since,)).fetchall())
    types = defaultdict(int)
    for v in ev.values():
        for t in v:
            types[t] += 1
    print(f"3. WATCH MY MODELS. Population: the {len(tracked)} models with at least one board entry; "
          f"window: the 30 days since {since.date()}.")
    print(f"   model_event rows in the window, by type (all models): {dict(types)}")
    upcoming = {m: d for m, d in retire.items() if d >= NOW.date()}
    print(f"   models with a retirement date: {len(retire)} (all models), of which still ahead: {len(upcoming)}; "
          f"of those, with board entries: {sum(1 for m in upcoming if m in tracked)}")
    any_change = [m for m in tracked if ev.get(m) or reports.get(m) or m in upcoming]
    print(f"   tracked models with SOMETHING to show in 30 days: {len(any_change)} of {len(tracked)} "
          f"(event: {sum(1 for m in tracked if ev.get(m))}, new reports: {sum(1 for m in tracked if reports.get(m))}, "
          f"retirement ahead: {sum(1 for m in tracked if m in upcoming)})")
    print("   example feed, the 5 tracked models with the most new reports:")
    for m in sorted(tracked, key=lambda m: -(reports.get(m) or 0))[:5]:
        print(f"     {names.get(m, m)[:34]:34} new report docs {reports.get(m, 0):4}  events {ev.get(m, [])}  "
              f"retires {retire.get(m) or '-'}")


if __name__ == "__main__":
    main()
