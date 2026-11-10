"""Show outreach's model spend: today against the cap, and the last 14 days.

    py -3.12 web/src/kitepulse/outreach/spend_report.py
    py -3.12 web/src/kitepulse/outreach/spend_report.py --days 30

Reads kp_outreach_spend in outreach's own database (common/spend.py). Changes
nothing. Before phase 2's model steps exist, it says that nothing is recorded,
which is the truth and not a $0.00.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]

for _p in (str(HERE), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import db, spend  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="spend_report.py", description=__doc__.split("\n")[0])
    parser.add_argument("--days", type=int, default=14, help="how many UTC days to list")
    args = parser.parse_args(argv)

    from collect.config import settings  # loads .env; the only collect/ import

    settings()
    import psycopg

    try:
        budget = spend.daily_budget()
    except spend.SpendError as exc:
        budget = None
        print(f"cap: NOT SET ({exc})")
    try:
        with db.connect() as conn:
            t = spend.today(conn)
            rows = spend.by_day(conn, days=args.days)
    except psycopg.errors.UndefinedTable:
        print("kp_outreach_spend does not exist. Run "
              "py -3.12 web/src/kitepulse/outreach/setup_db.py first.", file=sys.stderr)
        return 2
    except (db.OutreachDbError, psycopg.Error) as exc:
        print(f"could not read the outreach database: {exc}", file=sys.stderr)
        return 2

    floor = f" (a FLOOR: {t.unpriced_calls} call(s) had no reported cost)" if t.is_floor else ""
    cap = f" of ${budget:.2f}" if budget is not None else ""
    print(f"today since {t.starts_at:%Y-%m-%d %H:%M} UTC: ${t.spent_usd:.4f}{cap} "
          f"in {t.calls} call(s){floor}")
    if not rows:
        print(f"no model calls recorded in the last {args.days} day(s)")
        return 0
    print(f"\n{'day':<11}{'step':<10}{'model':<36}{'calls':>6}{'in tok':>9}"
          f"{'out tok':>9}{'usd':>11}  notes")
    for r in rows:
        notes = []
        if r.unpriced_calls:
            notes.append(f"{r.unpriced_calls} unpriced, usd is a floor")
        if r.unmetered_calls:
            notes.append(f"{r.unmetered_calls} reported no tokens")
        notes.append("on " + ", ".join(r.machines))
        print(f"{r.day:<11}{r.step:<10}{r.model[:35]:<36}{r.calls:>6}{r.input_tokens:>9}"
              f"{r.output_tokens:>9}{r.usd:>11.4f}  {'; '.join(notes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
