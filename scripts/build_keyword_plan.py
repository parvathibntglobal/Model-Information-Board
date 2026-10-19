#!/usr/bin/env python3
"""Build the keyword plan: which keywords to use on which public page.

Reads `seo/keyword_plan.yaml` (pages, value pools, and per-page phrasings, each
tagged with its combo code from the SEO workbook's Combinations sheet) and the
workbook's "Planner volumes (measured)" sheet; writes `seo/keyword_plan.json`
for the "Keyword plan" tab of /seo-keywords (judge/keyword_plan.py).

    py scripts/build_keyword_plan.py \\
        --board "docs/SEO keywords/Model Information Board —SEO keywords.xlsx" \\
        [--api http://127.0.0.1:8000]

`--api` reads the tracked models' catalog ids from the board's own /models, so
a model keyword links to that model's page and a pair to its comparison.

HOW A SECTION IS FILLED (`pick`). Each phrasing draws a different, repeatable
mix of values (seeded by page and phrasing), and the section takes ONE keyword
from each phrasing in turn until it holds `per_section`. So a section is many
phrasings with a few values each, not one phrasing with every model name - the
"claude latency, gpt latency, grok latency" list this replaced. A keyword is
used once, on the first section that claims it.

A KEYWORD'S VOLUME, where it has one:

  measured    the keyword is on the Planner sheet: its band.
  estimated   it is not, but its head is, and its phrasing is in a share
              class: the head's band midpoint x the share, which is MEASURED
              here from the workbook's own pairs (a head and its modified form
              both measured) - never typed.
  none        neither: "not measured". Most keywords here (CLAUDE.md rule 6).

ONE WORD IS A MODEL OR NOTHING (2026-10-19, anooj).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
import zlib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

PLAN = ROOT / "seo" / "keyword_plan.yaml"
OUT = ROOT / "seo" / "keyword_plan.json"
TOKEN = re.compile(r"[a-z0-9]+(?:[.'#+][a-z0-9]+)*[#+]*")
SLOT = re.compile(r"\{(\w+)\}")
#: A pair placeholder and the pool it shares with its first half.
PAIRS = {
    "model_b": "model",
    "casual_b": "casual",
    "vendor_b": "vendor",
    "concept_b": "concept",
    "benchmark_b": "benchmark",
}
#: Placeholders that name a model: a one-word keyword is kept only from these.
MODEL_SLOTS = {"model", "model_b", "casual", "casual_b"}
#: How many value mixes one phrasing may offer a section.
DRAWS = 40


def norm(text: str) -> str:
    """One spelling per keyword: lowercase, any separator one space."""
    return " ".join(TOKEN.findall(str(text or "").lower().replace("’", "'")))


def band(text) -> tuple[int, int] | None:
    """'10K – 100K' -> (10000, 100000); '0' -> (0, 0)."""
    if text is None:
        return None
    nums = re.findall(r"([\d.]+)\s*([KM]?)", str(text))
    if not nums:
        return None
    mult = {"": 1, "K": 1_000, "M": 1_000_000}
    vals = [int(float(n) * mult[u]) for n, u in nums]
    return (vals[0], vals[-1])


def midpoint(b: tuple[int, int]) -> float:
    lo, hi = b
    return math.sqrt(lo * hi) if lo > 0 else 0.0


def read_planner(path: Path) -> dict[str, dict]:
    import openpyxl  # only reading the workbook needs it; CI tests the rules

    ws = openpyxl.load_workbook(path, read_only=True, data_only=True)["Planner volumes (measured)"]
    rows = list(ws.iter_rows(values_only=True))
    at = next(i for i, r in enumerate(rows) if r and r[0] == "Keyword")
    head = [str(h).strip() if h else "" for h in rows[at]]
    out = {}
    for r in rows[at + 1 :]:
        if not r or not r[0]:
            continue
        d = dict(zip(head, r, strict=False))
        b = band(d.get("Volume / month"))
        if b is not None:
            out[norm(d["Keyword"])] = {
                "keyword": str(d["Keyword"]).strip(),
                "band": b,
                "label": str(d["Volume / month"]),
            }
    return out


def tracked_models(api: str | None) -> list[dict]:
    """Text models in contract/tracked_models.yaml, with catalog ids from /models when given."""
    spec = yaml.safe_load((ROOT / "contract" / "tracked_models.yaml").read_text(encoding="utf-8"))
    ids = {}
    if api:
        from urllib.request import urlopen

        with urlopen(f"{api}/models?tracked=1&limit=200", timeout=60) as r:  # noqa: S310 - our API
            for m in json.load(r).get("models", []):
                # The registry spells a version "5-1" where the catalog spells it "5.1".
                for field in ("model_version_id", "canonical_id"):
                    if m.get(field):
                        ids[m[field].replace(".", "-")] = m.get("canonical_id")
    return [
        {"name": m["name"].lower(), "id": ids.get(m["registry"].replace(".", "-"))}
        for m in spec.get("models") or []
        if m.get("kind", "text") == "text"
    ]


def pools_of(plan: dict, models: list[dict]) -> dict[str, list[dict]]:
    """The YAML pools as {name} values; tracked text models join `model` with their ids."""
    pools = {k: [{"name": str(v)} for v in vs] for k, vs in (plan.get("pools") or {}).items()}
    by_name = {norm(v["name"]): v for v in pools.get("model", [])}
    for m in models:
        if norm(m["name"]) in by_name:
            by_name[norm(m["name"])]["id"] = m["id"]
        else:
            pools.setdefault("model", []).append(dict(m))
    return pools


# ── filling a section ───────────────────────────────────────────────────────


def candidates(template: str, pools: dict[str, list[dict]], seed: str):
    """Up to DRAWS distinct (keyword, values) for one phrasing, in a repeatable
    random order: the same YAML always gives the same plan."""
    names = SLOT.findall(template)
    if not names:
        yield template, {}
        return
    if any(not pools.get(PAIRS.get(n, n)) for n in names):
        return
    rng = random.Random(zlib.crc32(seed.encode()))
    seen = set()
    for _ in range(DRAWS * 4):
        used = {}
        for n in names:
            base = PAIRS.get(n, n)
            taken = {norm(v["name"]) for k, v in used.items() if PAIRS.get(k, k) == base}
            choices = [v for v in pools[base] if norm(v["name"]) not in taken]
            if not choices:
                break
            used[n] = rng.choice(choices)
        if len(used) != len(names):
            continue
        kw = template
        for n, v in used.items():
            kw = kw.replace("{" + n + "}", v["name"])
        key = norm(kw)
        if key in seen:
            continue
        seen.add(key)
        yield kw, used
        if len(seen) >= DRAWS:
            return


def one_word_ok(keyword: str, used: dict) -> bool:
    return len(norm(keyword).split()) != 1 or bool(MODEL_SLOTS & set(used))


def pick(page: str, groups: list[dict], pools, want: int, taken: set[str]) -> list[dict]:
    """Round-robin over the section's phrasings, one keyword at a time."""
    queues = []
    for g in groups:
        for t in g["t"]:
            queues.append((g["combo"], t, iter(candidates(t, pools, f"{page}|{t}"))))
    out = []
    while queues and len(out) < want:
        alive = []
        for combo, t, q in queues:
            for kw, used in q:
                key = norm(kw)
                if key in taken or not one_word_ok(kw, used):
                    continue
                taken.add(key)
                out.append({"keyword": kw, "combo": combo, "pattern": t, "used": used})
                alive.append((combo, t, q))
                break
            if len(out) >= want:
                break
        queues = alive
    return out


# ── volumes ─────────────────────────────────────────────────────────────────


def measure_shares(classes, planner, pools) -> dict[str, dict]:
    """For each modifier class, the geometric mean of modified / head over every
    pair on the Planner sheet. THE HEAD IS A VALUE OF THAT PLACEHOLDER, never
    any measured phrase: "cheapest llm" -> "cheapest llm api" is not a model's
    API searches, and taking it made a first build's api share 316%."""
    out = {}
    for cls, templates in classes.items():
        samples, seen = [], set()
        for t in templates:
            names = SLOT.findall(t)
            if len(names) != 1:
                continue
            for v in pools.get(PAIRS.get(names[0], names[0])) or []:
                hk = norm(v["name"])
                h = planner.get(hk)
                if not h or h["band"][0] == 0:
                    continue
                full = norm(t.replace("{" + names[0] + "}", v["name"]))
                m = planner.get(full)
                if m and m["band"][0] > 0 and full != hk and (hk, full) not in seen:
                    seen.add((hk, full))
                    samples.append(
                        {
                            "head": h["keyword"],
                            "head_band": h["label"],
                            "keyword": m["keyword"],
                            "keyword_band": m["label"],
                            "ratio": midpoint(m["band"]) / midpoint(h["band"]),
                        }
                    )
        share = None
        if samples:
            share = math.exp(sum(math.log(s["ratio"]) for s in samples) / len(samples))
        out[cls] = {"share": share, "pairs": samples}
    return out


NO_VOLUME = {"volume_kind": None, "volume": None, "searches": None, "basis": None}


def volume(key, template, used, planner, shares, cls_of) -> dict:
    m = planner.get(key)
    if m:
        if m["band"][0] == 0:
            return {"volume_kind": "measured", "volume": "0", "searches": 0, "basis": None}
        return {
            "volume_kind": "measured",
            "volume": m["label"],
            "searches": int(midpoint(m["band"])),
            "basis": None,
        }
    cls = cls_of.get(template)
    share = (shares.get(cls) or {}).get("share") if cls else None
    if share is None or not used:
        return dict(NO_VOLUME)
    heads = []
    for v in used.values():
        h = planner.get(norm(v["name"]))
        if not h or h["band"][0] == 0:
            return dict(NO_VOLUME)
        heads.append(h)
    head = min(heads, key=lambda h: midpoint(h["band"]))
    est = int(round(midpoint(head["band"]) * share, -1))
    return {
        "volume_kind": "estimated",
        "volume": f"~{est:,}",
        "searches": est,
        "basis": f"'{head['keyword']}' {head['label']} x {cls} share {share:.1%}",
    }


# ── links ───────────────────────────────────────────────────────────────────


def base_url(url: str) -> str:
    """A page type's URL without its pattern part: /compare?ids=<a>,<b> -> /compare."""
    url = re.sub(r"\?[^?]*<[^>]+>.*$", "", url)
    return re.sub(r"/<[^>]+>.*$", "", url) or "/"


def link(page: dict, used: dict) -> str:
    url = page["url"]
    model, model_b = used.get("model"), used.get("model_b")
    if "<a>" in url:
        if model and model_b and model.get("id") and model_b.get("id"):
            return f"/compare?ids={model['id']},{model_b['id']}"
        return base_url(url)
    if "<model>" in url and model and model.get("id"):
        return url.replace("<model>", model["id"])
    for n, v in used.items():
        if f"<{n}>" in url:
            return url.replace(f"<{n}>", "-".join(norm(v["name"]).split()))
    return base_url(url)


def build(plan: dict, planner: dict[str, dict], models: list[dict]) -> dict:
    pools = pools_of(plan, models)
    pages = plan["pages"]
    want = int(plan["per_section"])
    cls_of = {t: c for c, ts in (plan.get("share_classes") or {}).items() for t in ts}
    shares = measure_shares(plan.get("share_classes") or {}, planner, pools)
    taken: set[str] = set()
    keywords, per_page = [], {}
    for key, groups in (plan.get("sections") or {}).items():
        if key not in pages:
            raise SystemExit(f"section {key!r} is not in `pages`")  # rule 12: say so
        rows = pick(key, groups, pools, want, taken)
        per_page[key] = {"keywords": len(rows), "phrasings": sum(len(g["t"]) for g in groups)}
        for r in rows:
            vol = volume(norm(r["keyword"]), r["pattern"], r["used"], planner, shares, cls_of)
            keywords.append(
                {
                    "keyword": r["keyword"],
                    "page": key,
                    "combo": r["combo"],
                    "pattern": r["pattern"],
                    "link": link(pages[key], r["used"]),
                    **vol,
                }
            )
    empty = {"keywords": 0, "phrasings": 0}
    counts = Counter(k["volume_kind"] or "none" for k in keywords)
    return {
        "built": datetime.now(UTC).date().isoformat(),
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "per_section": want,
        "pages": [{"key": k, **v, **per_page.get(k, empty)} for k, v in pages.items()],
        "keywords": keywords,
        "method": {
            "counts": {
                "keywords": len(keywords),
                "measured": counts["measured"],
                "estimated": counts["estimated"],
                "not_measured": counts["none"],
            },
            "short_sections": {
                k: v["keywords"] for k, v in per_page.items() if v["keywords"] < want
            },
            "shares": shares,
            "volume_source": "Google Keyword Planner bands, global, all languages, Jan-Jul 2026 "
            "(the workbook's 'Planner volumes (measured)' sheet)",
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--board", required=True, type=Path, help="the board SEO workbook (.xlsx)")
    ap.add_argument("--api", help="the board API, for tracked models' catalog ids")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    plan = yaml.safe_load(PLAN.read_text(encoding="utf-8"))
    api = args.api.rstrip("/") if args.api else None
    data = build(plan, read_planner(args.board), tracked_models(api))
    data["source"] = f"{args.board.name} + {PLAN.relative_to(ROOT).as_posix()}"
    args.out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    c = data["method"]["counts"]
    print(
        f"wrote {args.out}: {c['keywords']} keywords in {len(data['pages'])} sections "
        f"({c['measured']} measured, {c['estimated']} estimated, {c['not_measured']} not measured)"
    )
    for p in data["pages"]:
        flag = "" if p["keywords"] >= data["per_section"] else "   SHORT"
        print(f"  {p['key']:16} {p['keywords']:5} keywords from {p['phrasings']:3} phrasings{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
