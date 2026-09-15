"""Seconds per extracted thread, measured from every fetch log on this machine.

The gap between consecutive `reading thread N/M` lines. That interval is one
thread's whole E5 - the LLM call, verification and the store write - because
`_on_thread` is called immediately before each thread is read, so line N is the
start of thread N and line N+1 is its end.
"""
import datetime
import json
import pathlib
import re
import statistics

LOGS = pathlib.Path(r"C:\Users\anooj\Model-Information-Board\var\fetch")
gaps = []
per_run = {}
for path in sorted(LOGS.glob("*.jsonl")):
    prev = prevn = None
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("id") != "E5":
            continue
        m = re.search(r"reading thread (\d+)/(\d+)", str(r.get("detail") or ""))
        if not m:
            continue
        n = int(m.group(1))
        t = datetime.datetime.strptime(r["at"], "%Y-%m-%dT%H:%M:%SZ")
        if prev is not None and n == prevn + 1:
            gaps.append((t - prev).total_seconds())
            per_run.setdefault(path.name, []).append((t - prev).total_seconds())
        prev, prevn = t, n

print(f"logs on this machine            : {len(list(LOGS.glob('*.jsonl')))}")
print(f"logs carrying per-thread lines  : {len(per_run)}")
print(f"thread intervals measured       : {len(gaps)}")
if gaps:
    g = sorted(gaps)
    print(f"  min {min(g):.0f}s   p50 {statistics.median(g):.0f}s   "
          f"mean {statistics.mean(g):.0f}s   p90 {g[int(len(g) * 0.9)]:.0f}s   max {max(g):.0f}s")
    print()
    for name, vals in per_run.items():
        v = sorted(vals)
        print(f"  {name[:46]:48} n={len(v):>3}  p50 {statistics.median(v):>4.0f}s  "
              f"mean {statistics.mean(v):>4.0f}s  max {max(v):>4.0f}s")
