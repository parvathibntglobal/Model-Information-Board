#!/usr/bin/env python3
"""Build the keyword plan: which keywords to use on which public page.

Reads `seo/keyword_plan.yaml` (pages, combinations, values) and the board SEO
workbook's "Planner volumes (measured)" sheet; writes `seo/keyword_plan.json`
for the "Keyword plan" tab of /seo-keywords (judge/keyword_plan.py).

    py scripts/build_keyword_plan.py \\
        --board "docs/SEO keywords/Model Information Board —SEO keywords.xlsx" \\
        [--api http://127.0.0.1:8000]

`--api` reads the tracked models' catalog ids from the board's own /models,
so a model keyword links to that model's page and a pair to its comparison.
Without it, those keywords point at the page type rather than one URL.

WHAT A KEYWORD'S VOLUME IS, in the order tried:

  measured    the keyword itself is on the Planner sheet: its band.
  estimated   it is not, but its head is ("claude opus" for "claude opus
              pricing"): the head's band midpoint x the share of a head's
              searches that add that modifier. SHARES ARE MEASURED HERE, from
              the sheet's own pairs (a head and its modified form both
              measured), never typed - a modifier with no pair has no share.
  none        neither: the keyword is counted, not listed (CLAUDE.md rule 6).

A band is a range, so its GEOMETRIC midpoint stands for it in arithmetic
(10K-100K -> 31,623). The page shows the band, or "~N (estimated)".

ONE WORD IS A MODEL OR NOTHING (2026-10-19, anooj): a keyword of one word is
kept only when it is a model or model family name ("qwen3", "claude"). "rag",
"classification", "local" alone say nothing about which page answers them.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

PLAN = ROOT / "seo" / "keyword_plan.yaml"
OUT = ROOT / "seo" / "keyword_plan.json"
TOKEN = re.compile(r"[a-z0-9]+(?:[.'][a-z0-9]+)*")
SLOT = re.compile(r"\{(\w+)\}")
#: A pair placeholder and the one it pairs with.
PAIRS = {"model_b": "model", "vendor_b": "vendor", "benchmark_b": "benchmark"}


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
                "combo": d.get("Combo code"),
            }
    return out


def tracked_models(api: str | None) -> list[dict]:
    """contract/tracked_models.yaml, with catalog ids from the board's /models when given."""
    spec = yaml.safe_load((ROOT / "contract" / "tracked_models.yaml").read_text(encoding="utf-8"))
    ids = {}
    if api:
        from urllib.request import urlopen

        with urlopen(f"{api}/models?tracked=1&limit=200", timeout=60) as r:  # noqa: S310 - our API
            for m in json.load(r).get("models", []):
                # The registry spells a version "5-1" where the catalog spells
                # it "5.1"; one key for both.
                for field in ("model_version_id", "canonical_id"):
                    if m.get(field):
                        ids[m[field].replace(".", "-")] = m.get("canonical_id")
    return [
        {
            "name": m["name"],
            "kind": m.get("kind", "text"),
            "id": ids.get(m["registry"].replace(".", "-")),
        }
        for m in spec.get("models") or []
    ]


# ── expansion ───────────────────────────────────────────────────────────────


def expand(template: str, values: dict[str, list[dict]]):
    """Every (keyword, {placeholder: value}) a template makes."""
    names = SLOT.findall(template)
    pools = []
    for n in names:
        base = PAIRS.get(n, n)
        pool = values.get(base)
        if not pool:
            return
        if any(PAIRS.get(m) == base for m in names):
            # a pair compares like with like: text models with text models
            pool = [v for v in pool if v.get("kind", "text") == "text"]
        pools.append(pool)
    seen_pairs = set()
    for combo in itertools.product(*pools):
        used = dict(zip(names, combo, strict=True))
        pair_ok = True
        for b, a in PAIRS.items():
            if a in used and b in used:
                if norm(used[a]["name"]) == norm(used[b]["name"]):
                    pair_ok = False
                key = (a,) + tuple(sorted((norm(used[a]["name"]), norm(used[b]["name"]))))
                if key in seen_pairs:
                    pair_ok = False  # "a vs b" once, not "b vs a" too
                seen_pairs.add(key)
        if not pair_ok:
            continue
        kw = template
        for n, v in used.items():
            kw = kw.replace("{" + n + "}", v["name"])
        yield kw, used


def one_word_ok(keyword: str, used: dict) -> bool:
    if len(norm(keyword).split()) != 1:
        return True
    return any(n in ("model", "model_b") for n in used)


# ── shares, measured from the workbook's own pairs ──────────────────────────


def measure_shares(
    classes: dict[str, list[str]], planner: dict[str, dict], values: dict[str, list[dict]]
) -> dict[str, dict]:
    """For each modifier class: the geometric mean of modified / head over every
    pair where both are on the Planner sheet with a non-zero band."""
    out = {}
    for cls, templates in classes.items():
        samples, seen = [], set()
        for t in templates:
            names = SLOT.findall(t)
            if len(names) != 1:
                continue  # a pair keyword has two heads; calibrate on singles
            # THE HEAD IS A VALUE OF THAT PLACEHOLDER, never any measured phrase:
            # "cheapest llm" -> "cheapest llm api" is not a model's API searches,
            # and taking it made the first build's api share 316% (2026-10-19).
            for v in values.get(PAIRS.get(names[0], names[0])) or []:
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
                            "band": m["label"],
                            "ratio": midpoint(m["band"]) / midpoint(h["band"]),
                        }
                    )
        if samples:
            share = math.exp(sum(math.log(s["ratio"]) for s in samples) / len(samples))
            out[cls] = {"share": share, "pairs": samples}
        else:
            out[cls] = {"share": None, "pairs": []}
    return out


def build(plan: dict, planner: dict[str, dict], models: list[dict]) -> dict:
    values = {k: [dict(v) for v in vs] for k, vs in (plan.get("values") or {}).items()}
    for m in models:  # the tracked models, first
        values.setdefault("model", [])
        if not any(norm(v["name"]) == norm(m["name"]) for v in values["model"]):
            values["model"].insert(0, {"name": m["name"], "kind": m["kind"], "id": m["id"]})
    values["year"] = [{"name": str(plan.get("year", ""))}]
    pages = plan["pages"]
    cls_of = {t: c for c, ts in (plan.get("share_classes") or {}).items() for t in ts}
    shares = measure_shares(plan.get("share_classes") or {}, planner, values)

    keywords: dict[str, dict] = {}
    counts = Counter()
    skipped = {}
    for code, spec in (plan.get("combinations") or {}).items():
        if spec.get("skip"):
            skipped[code] = spec["skip"]
            continue
        page = spec["page"]
        if page not in pages:
            raise SystemExit(f"{code}: page {page!r} is not in `pages`")  # rule 12: say so
        for template in spec.get("keywords") or []:
            for kw, used in expand(template, values):
                key = norm(kw)
                counts["generated"] += 1
                if not one_word_ok(kw, used):
                    counts["one_word_dropped"] += 1
                    continue
                if key in keywords:
                    keywords[key]["combos"].append(code)
                    continue
                vol = volume(key, template, used, planner, shares, cls_of)
                # A measured keyword is shown as Planner spelled it.
                shown = planner[key]["keyword"] if key in planner else kw
                keywords[key] = {
                    "keyword": shown,
                    "combo": code,
                    "combos": [code],
                    "pattern": template,
                    "page": page,
                    "link": link(pages[page], used),
                    **vol,
                }
    # MEASURED KEYWORDS NO TEMPLATE MADE ("opus vs sonnet"), on the page
    # their own combo points at; the one-word rule applies to them too.
    combos = plan.get("combinations") or {}
    for key, m in planner.items():
        if key in keywords or not m["combo"]:
            continue
        spec = combos.get(str(m["combo"]).strip()) or {}
        if spec.get("skip") or "page" not in spec:
            continue
        if len(key.split()) == 1 and not str(m["combo"]).startswith("E20"):
            counts["one_word_dropped"] += 1
            continue
        keywords[key] = {
            "keyword": m["keyword"],
            "combo": str(m["combo"]),
            "combos": [str(m["combo"])],
            "pattern": "(measured keyword)",
            "page": spec["page"],
            "link": base_url(pages[spec["page"]]["url"]),
            **volume(key, "", {}, planner, shares, cls_of),
        }
    counts["keywords"] = len(keywords)
    counts["measured"] = sum(1 for k in keywords.values() if k["volume_kind"] == "measured")
    counts["estimated"] = sum(1 for k in keywords.values() if k["volume_kind"] == "estimated")
    counts["no_volume"] = sum(1 for k in keywords.values() if k["volume_kind"] is None)
    floor = int(plan.get("min_monthly_searches", 0))
    listed = [k for k in keywords.values() if k["volume_kind"] is not None]
    listed.sort(key=lambda k: (-k["searches"], k["keyword"].lower()))
    counts["at_or_above_threshold"] = sum(1 for k in listed if k["searches"] >= floor)
    return {
        "built": datetime.now(UTC).date().isoformat(),
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "min_monthly_searches": floor,
        "pages": [{"key": k, **v} for k, v in pages.items()],
        "keywords": listed,
        "method": {
            "counts": dict(counts),
            "shares": {c: {"share": s["share"], "pairs": s["pairs"]} for c, s in shares.items()},
            "skipped_combinations": skipped,
            "volume_source": "Google Keyword Planner bands, global, all languages, Jan-Jul 2026 "
            "(the workbook's 'Planner volumes (measured)' sheet)",
        },
    }


def volume(key, template, used, planner, shares, cls_of) -> dict:
    m = planner.get(key)
    if m:
        return {
            "volume_kind": "measured",
            "volume": m["label"],
            "searches": int(midpoint(m["band"])),
            "band_floor": m["band"][0],
            "basis": None,
        }
    cls = cls_of.get(template)
    share = (shares.get(cls) or {}).get("share") if cls else None
    if share is None or not used:
        return {
            "volume_kind": None,
            "volume": None,
            "searches": 0,
            "band_floor": None,
            "basis": None,
        }
    heads = []
    for v in used.values():
        h = planner.get(norm(v["name"]))
        if not h or h["band"][0] == 0:
            return {
                "volume_kind": None,
                "volume": None,
                "searches": 0,
                "band_floor": None,
                "basis": None,
            }
        heads.append(h)
    head = min(heads, key=lambda h: midpoint(h["band"]))
    est = int(round(midpoint(head["band"]) * share, -2))
    return {
        "volume_kind": "estimated",
        "volume": f"~{est:,}",
        "searches": est,
        "band_floor": None,
        "basis": f"'{head['keyword']}' {head['label']} x {cls} share {share:.1%}",
    }


def base_url(url: str) -> str:
    """A page type's URL without its pattern part: /compare?ids=<a>,<b> -> /compare."""
    url = re.sub(r"\?[^?]*<[^>]+>.*$", "", url)
    return re.sub(r"/<[^>]+>.*$", "", url) or "/"


def link(page: dict, used: dict) -> str:
    url = page["url"]
    model, model_b = used.get("model"), used.get("model_b")
    if "<a>" in url:  # a comparison
        if model and model_b and model.get("id") and model_b.get("id"):
            return f"/compare?ids={model['id']},{model_b['id']}"
        return "/compare"
    if "<model>" in url and model:
        if model.get("id"):
            return f"/catalog/model/{model['id']}"
        return model.get("link") or "/catalog"
    for n in ("job", "capability", "benchmark", "metric"):
        if used.get(n) and used[n].get("link") and url.startswith("/reports"):
            return used[n]["link"]
    for n, v in used.items():
        if f"<{n}>" in url:
            return url.replace(f"<{n}>", "-".join(norm(v["name"]).split()))
    return base_url(url)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--board", required=True, type=Path, help="the board SEO workbook (.xlsx)")
    ap.add_argument("--api", help="the board API, for tracked models' catalog ids")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    plan = yaml.safe_load(PLAN.read_text(encoding="utf-8"))
    data = build(
        plan, read_planner(args.board), tracked_models(args.api.rstrip("/") if args.api else None)
    )
    data["source"] = f"{args.board.name} + {PLAN.relative_to(ROOT).as_posix()}"
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    c = data["method"]["counts"]
    print(
        f"wrote {args.out}: {c['keywords']} keywords ({c['measured']} measured, {c['estimated']} "
        f"estimated, {c['no_volume']} with no volume); {c['at_or_above_threshold']} at "
        f"{data['min_monthly_searches']:,}+ a month"
    )
    for cls, s in data["method"]["shares"].items():
        print(
            f"  share {cls:13} {('%.1f%%' % (100 * s['share'])) if s['share'] else 'none':>7}  "
            f"from {len(s['pairs'])} pair(s)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
