"""What the proposed category score would show, measured before it is allowed.

Read-only. Reads the board the way `board_sections` does (declined rulings
out, ruling_target over slug), files each leaf under its parent the way
`board_grouping` does (contract first, then a valid `parent_proposed`), and
files each parent under one of the eight categories in
`contract/category_scores.yaml`. Then counts, per (model, category):

    reports   distinct documents          positive / negative / both / neutral
    sided     positive + negative - both  (the `_working_key` identity)

and the proposed score (formula B, below): 100 x Wilson lower bound of positive / sided, at the
z in `contract/board_ordering.yaml`, shown only at sided >= each threshold
being compared.

Run:  python docs/measurements/category-score-preview-2026-10-19.py  <DB URL env var name>
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

import psycopg
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from judge.config import slug_parents  # noqa: E402
from judge.store.board_entries import _wilson_lower  # noqa: E402

CONTRACT = ROOT / "contract"
cats = yaml.safe_load((CONTRACT / "category_scores.yaml").read_text(encoding="utf-8"))
z = yaml.safe_load((CONTRACT / "board_ordering.yaml").read_text(encoding="utf-8"))["wilson_z"]

# (section, parent) -> category
where: dict[tuple[str, str], str] = {}
for key, c in cats["categories"].items():
    for section, parents in c["parents"].items():
        for p in parents:
            where[(section, p)] = key

leaf_parent = slug_parents()
headings = {s: set(m.values()) for s, m in leaf_parent.items()}

url = os.environ[sys.argv[1] if len(sys.argv) > 1 else "DATABASE_URL"]
with psycopg.connect(url) as conn:
    conn.execute("SET TRANSACTION READ ONLY")
    rows = conn.execute(
        "SELECT be.section, COALESCE(be.ruling_target, be.slug), be.parent_proposed,"
        "       COALESCE(v.display_name, be.model_version_id), be.document_id, be.polarity "
        "FROM board_entry be LEFT JOIN model_version v "
        "  ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined'"
    ).fetchall()

docs: dict[tuple[str, str], dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
unfiled = defaultdict(int)
metric_polarity = defaultdict(int)
for section, slug, proposed, model, doc, pol in rows:
    if section == "metric":
        metric_polarity[pol] += 1
    parent = leaf_parent.get(section, {}).get((slug or "").strip().lower())
    if parent is None and proposed in headings.get(section, ()):
        parent = proposed
    cat = where.get((section, parent)) if parent else None
    if cat is None:
        unfiled[section] += 1
        continue
    # Formula B (proposed): a metric row is a report, shown, never scored.
    docs[(model, cat)][doc].add("neutral" if section == "metric" else pol)

print(f"board_entry rows read (declined excluded): {len(rows)}")
print(f"rows filed under no category, by section: {dict(unfiled)}")
print(f"metric rows by polarity: {dict(metric_polarity)}")
print(f"(model, category) pairs with any report: {len(docs)}")

stats = []
for (model, cat), d in docs.items():
    pos = sum("positive" in s for s in d.values())
    neg = sum("negative" in s for s in d.values())
    both = sum("positive" in s and "negative" in s for s in d.values())
    neu = sum(not ({"positive", "negative"} & s) for s in d.values())
    sided = pos + neg - both
    lb = _wilson_lower(pos, sided, z)
    stats.append((model, cat, len(d), pos, neg, both, neu, sided, lb))

print()
print("pairs that would show a score, by minimum sided reports:")
for m in (1, 3, 5, 10):
    shown = [s for s in stats if s[7] >= m]
    models = {s[0] for s in shown}
    print(f"  sided >= {m:>2}: {len(shown):>4} of {len(stats)} pairs, {len(models)} models")

print()
print("per category (sided >= 3): pairs shown / pairs with any report")
for key in cats["categories"]:
    allp = [s for s in stats if s[1] == key]
    shown = [s for s in allp if s[7] >= 3]
    print(f"  {key:<22} {len(shown):>4} / {len(allp):<4}")

print()
print("score distribution where shown (sided >= 3), 100 x Wilson lower bound:")
bins = defaultdict(int)
for s in stats:
    if s[7] >= 3:
        bins[int(s[8] * 100) // 10 * 10] += 1
for b in sorted(bins):
    print(f"  {b:>3}-{b + 9:<3} {bins[b]}")

print()
print("ten models with the most reports, all eight categories (score at sided >= 3):")
by_model = defaultdict(int)
for s in stats:
    by_model[s[0]] += s[2]
for model in sorted(by_model, key=lambda m: -by_model[m])[:10]:
    cells = []
    for key in cats["categories"]:
        s = next((x for x in stats if x[0] == model and x[1] == key), None)
        if s is None:
            cells.append(f"{key[:8]}: -")
        elif s[7] < 3:
            cells.append(f"{key[:8]}: n/a({s[3]}+/{s[4]}-/{s[6]}~)")
        else:
            cells.append(f"{key[:8]}: {round(s[8] * 100)}({s[3]}+/{s[4]}-/{s[6]}~)")
    print(f"  {model}")
    print("     " + " | ".join(cells))


# ---------------------------------------------------------------------------
# WHICH SECTIONS' POLARITY SHOULD SCORE. Added after the first run found that
# metric rows DO carry polarity, and that `best_for` is mostly positive by
# construction (judge/extract/prompt.py declines a negative best_for). Three
# candidate formulas, same reports, same z, same threshold (sided >= 3):
#
#   A  capability only
#   B  capability + best_for                    (proposed)
#   C  capability + best_for + metric
# ---------------------------------------------------------------------------
print()
print("polarity by section (declined excluded):")
by_sec = defaultdict(lambda: defaultdict(int))
for section, _slug, _p, _m, _d, pol in rows:
    by_sec[section][pol] += 1
for section in sorted(by_sec):
    print(f"  {section:<11} {dict(sorted(by_sec[section].items()))}")

variants = {"A": {"capability"}, "B": {"capability", "best_for"},
            "C": {"capability", "best_for", "metric"}}
per = {v: defaultdict(lambda: defaultdict(set)) for v in variants}
figures = defaultdict(set)
for section, slug, proposed, model, doc, pol in rows:
    parent = leaf_parent.get(section, {}).get((slug or "").strip().lower())
    if parent is None and proposed in headings.get(section, ()):
        parent = proposed
    cat = where.get((section, parent)) if parent else None
    if cat is None:
        continue
    if section == "metric":
        figures[(model, cat)].add(doc)
    for v, secs in variants.items():
        # A section outside the variant still contributes its reports, as
        # neutral: shown, never scored.
        per[v][(model, cat)][doc].add(pol if section in secs else "neutral")


def score(d):
    pos = sum("positive" in s for s in d.values())
    neg = sum("negative" in s for s in d.values())
    both = sum("positive" in s and "negative" in s for s in d.values())
    sided = pos + neg - both
    return (None if sided < 3 else round(100 * _wilson_lower(pos, sided, z))), sided


res = {v: {k: score(d) for k, d in per[v].items()} for v in variants}
print()
print("pairs scored (sided >= 3) and median score, per category:")
print(f"  {'category':<12} " + "  ".join(f"{v}: n / median" for v in variants))
for key in cats["categories"]:
    cells = []
    for v in variants:
        s = sorted(x[0] for k, x in res[v].items() if k[1] == key and x[0] is not None)
        cells.append(f"{v}: {len(s):>3} / {s[len(s) // 2] if s else '-':>3}  ")
    print(f"  {key:<12} " + "  ".join(cells))

for a, b in (("A", "B"), ("B", "C")):
    both_scored = [k for k in res[a] if res[a][k][0] is not None and res[b][k][0] is not None]
    moved = [k for k in both_scored if abs(res[a][k][0] - res[b][k][0]) >= 10]
    gained = [k for k in res[b] if res[b][k][0] is not None and res[a][k][0] is None]
    print(f"\n{a} -> {b}: {len(both_scored)} pairs scored under both; {len(moved)} move by 10+;"
          f" {len(gained)} gain a score")
print(f"\n(model, category) pairs with at least one metric figure: {len(figures)}")
