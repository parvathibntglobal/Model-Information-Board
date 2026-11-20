"""Summarise profile_rows.json per source: shape, kinds, and top vs bottom quarter by engagement."""

import collections
import json
import os
import statistics as st

OUT = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(OUT, "profile_rows.json"), encoding="utf-8") as fh:
    rows = json.load(fh)
by = collections.defaultdict(list)
for r in rows:
    by[r["source"]].append(r)

NUM = (
    "chars",
    "words",
    "lines",
    "paras",
    "first_line_chars",
    "t_chars",
    "t_words",
    "hashtags",
    "links",
)
SHARE = {
    "bullets": lambda r: r["bullets"] > 0,
    "headings": lambda r: r["headings"] > 0,
    "code": lambda r: r["code_blocks"] > 0,
    "table": lambda r: r["table"],
    "link_in_text": lambda r: r["links"] > 0,
    "hashtag": lambda r: r["hashtags"] > 0,
    "mention": lambda r: r["mentions"] > 0,
    "emoji": lambda r: r["emoji"] > 0,
    "any_question": lambda r: r["questions"] > 0,
    "ends_question": lambda r: r["ends_question"],
    "has_number": lambda r: r["numbers"] > 0,
    "empty_body": lambda r: r["chars"] == 0,
    "t_question": lambda r: r.get("t_question"),
    "t_digit": lambda r: r.get("t_digit"),
    "t_colon": lambda r: r.get("t_colon"),
    "t_tag": lambda r: r.get("t_tag"),
    "t_excl": lambda r: r.get("t_excl"),
}


def q(vals, p):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(p * len(vals)))] if vals else None


def shape(rs):
    out = {}
    for k in NUM:
        v = [r[k] for r in rs if k in r]
        if v:
            out[k] = f"{q(v, 0.25)}/{st.median(v):g}/{q(v, 0.75)}"
    for k, f in SHARE.items():
        if k.startswith("t_") and "t_chars" not in rs[0]:
            continue
        out[k] = f"{sum(1 for r in rs if f(r))}/{len(rs)}"
    return out


report = {}
for src, rs in by.items():
    rs_sorted = sorted(rs, key=lambda r: r["eng"])
    k = len(rs) // 4
    bottom, top = rs_sorted[:k], rs_sorted[-k:]
    kinds = collections.Counter(r.get("x_kind") for r in rs)
    rep = {
        "n": len(rs),
        "pool": rs[0]["pool"],
        "engagement_median": st.median(r["eng"] for r in rs),
        "engagement_top_quarter_min": top[0]["eng"] if top else None,
        "kinds": kinds.most_common(12),
        "kinds_top_quarter": collections.Counter(r.get("x_kind") for r in top).most_common(8),
        "kinds_bottom_quarter": collections.Counter(r.get("x_kind") for r in bottom).most_common(8),
        "all": shape(rs),
        "top_quarter": shape(top),
        "bottom_quarter": shape(bottom),
    }
    if any("x_group" in r for r in rs):
        rep["groups"] = collections.Counter(r.get("x_group") for r in rs).most_common(12)
    if src == "reddit":
        rep["flair"] = collections.Counter(r.get("x_flair") for r in rs).most_common(12)
    if src == "x":
        rep["long_post"] = f"{sum(r['x_long_post'] for r in rs)}/{len(rs)}"
        rep["long_post_top"] = f"{sum(r['x_long_post'] for r in top)}/{len(top)}"
        rep["quote"] = f"{sum(r['x_quote'] for r in rs)}/{len(rs)}"
        rep["bookmarks_per_like_median_top"] = (
            st.median(r["bookmarks"] / r["eng"] for r in top if r["eng"]) if top else None
        )
    if src == "devto":
        mins = [r["x_reading_min"] or 0 for r in rs]
        rep["reading_min"] = f"{q(mins, 0.25)}/{st.median(mins)}/{q(mins, 0.75)}"
        rep["reading_min_top"] = st.median(r["x_reading_min"] or 0 for r in top)
        rep["cover"] = f"{sum(r['x_cover'] for r in rs)}/{len(rs)}"
        rep["cover_top"] = f"{sum(r['x_cover'] for r in top)}/{len(top)}"
        rep["ai_disclosure"] = collections.Counter(r["x_ai_disclosure"] for r in rs).most_common()
        tags = collections.Counter(
            t.strip() for r in rs for t in (r["x_tags"] or "").split(",") if t.strip()
        )
        rep["tags"] = tags.most_common(15)
        rep["tags_per_post"] = st.median(
            len([t for t in (r["x_tags"] or "").split(",") if t.strip()]) for r in rs
        )
    if src == "hackernews":
        rep["domains"] = collections.Counter(r.get("x_domain") for r in rs).most_common(12)
    report[src] = rep

with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1, default=str)
for src, rep in report.items():
    print(
        f"\n==== {src}  n={rep['n']} of pool {rep['pool']}  eng median {rep['engagement_median']}"
        f"  top-quarter from {rep['engagement_top_quarter_min']}"
    )
    for k, v in rep.items():
        if k in ("all", "top_quarter", "bottom_quarter"):
            continue
        if k not in ("n", "pool", "engagement_median", "engagement_top_quarter_min"):
            print(f"  {k}: {v}")
    print("  feature: all | top quarter | bottom quarter   (numbers are p25/median/p75)")
    for f in rep["all"]:
        top_f = rep["top_quarter"].get(f, "")
        bottom_f = rep["bottom_quarter"].get(f, "")
        print(f"    {f:16} {rep['all'][f]:>18} | {top_f:>18} | {bottom_f:>18}")
