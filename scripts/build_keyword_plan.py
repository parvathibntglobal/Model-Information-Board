#!/usr/bin/env python3
"""Build the keyword plan, by query type: which keywords to use on which page.

Reads `seo/keyword_plan.yaml` (pages, entities, and one section per query
type) and the SEO workbook's "Planner volumes (measured)" sheet; writes
`seo/keyword_plan.json` for the "Keyword plan" tab of /seo-keywords.

    py scripts/build_keyword_plan.py \\
        --board "docs/SEO keywords/Model Information Board —SEO keywords.xlsx" \\
        [--api http://127.0.0.1:8000]

`--api` reads the tracked models' catalog ids (/models) and the published
blog posts (/blog-posts), so a keyword links to the exact page that answers
it - a model's page, a pair's comparison, the post already written on a
concept - and a concept with no post yet says so.

A QUERY IS AN INTENT PLUS AN ENTITY ("what is" + "system 1 model"). Each
section is one intent, combined with the entity types it makes sense for, and
EVERY such combination is made: nothing is sampled and nothing padded. A pair
("a vs b") is made once and only between models of one kind. A keyword is
listed once, under the first section that makes it.

A KEYWORD'S VOLUME, where it has one: the Planner band where Google measured
it; an estimate where only its head was measured and a modifier share was
measured from the workbook's own pairs; otherwise none - "not measured".

ONE WORD IS A MODEL OR NOTHING (2026-10-19, anooj).
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
TOPICS = ROOT / "blog_topics.yaml"
TOKEN = re.compile(r"[a-z0-9]+(?:[.'#+][a-z0-9]+)*[#+]*")
SLOT = re.compile(r"\{(\w+)\}")
#: A pair placeholder and the entity it pairs with.
PAIRS = {"model_b": "model", "vendor_b": "vendor"}
MODEL_SLOTS = {"model", "model_b"}


def norm(text: str) -> str:
    """One spelling per keyword: lowercase, any separator one space."""
    return " ".join(TOKEN.findall(str(text or "").lower().replace("’", "'")))


def slug(text: str) -> str:
    return "-".join(norm(text).split())


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


def _get(api: str, path: str):
    from urllib.request import urlopen

    with urlopen(api + path, timeout=120) as r:  # noqa: S310 - our own API
        return json.load(r)


def tracked_models(api: str | None) -> list[dict]:
    """contract/tracked_models.yaml, with catalog ids from /models when given."""
    spec = yaml.safe_load((ROOT / "contract" / "tracked_models.yaml").read_text(encoding="utf-8"))
    ids = {}
    if api:
        for m in _get(api, "/models?tracked=1&limit=200").get("models", []):
            # The registry spells a version "5-1" where the catalog spells it "5.1".
            for field in ("model_version_id", "canonical_id"):
                if m.get(field):
                    ids[m[field].replace(".", "-")] = m.get("canonical_id")
    return [
        {
            "name": m["name"].lower(),
            "kind": m.get("kind", "text"),
            "id": ids.get(m["registry"].replace(".", "-")),
        }
        for m in spec.get("models") or []
    ]


def blog_concepts(api: str | None) -> tuple[list[dict], dict[str, str]]:
    """Each blog topic's SHORT NAME as a concept, and, when the API is given,
    concept -> the published post already written on it.

    Not the topics' search terms: those are phrases a harvest matches on
    ("run locally", "on device", "self improving"), not things a definition
    can be written for - they made "what is run locally" (2026-10-19)."""
    if not TOPICS.exists():
        return [], {}
    topics = (yaml.safe_load(TOPICS.read_text(encoding="utf-8")) or {}).get("topics") or []
    posts = []
    if api:
        posts = [p.get("slug", "") for p in _get(api, "/blog-posts").get("posts", [])]
    concepts, written = [], {}
    for t in topics:
        names = [t.get("short") or ""]
        post = next((s for s in posts if s.endswith(f"-concept-{t.get('key')}")), None)
        for n in names:
            if n and len(norm(n)) > 2:
                concepts.append({"name": norm(n)})
                if post:
                    written[norm(n)] = post
    return concepts, written


def entities_of(plan: dict, models: list[dict], concepts: list[dict]) -> dict[str, list[dict]]:
    ents = {}
    for k, vs in (plan.get("entities") or {}).items():
        ents[k] = [v if isinstance(v, dict) else {"name": str(v)} for v in (vs or [])]
    ents["model"] = [dict(m) for m in models] + [m for m in ents.get("model", [])]
    seen, merged = set(), []
    for c in ents.get("concept", []) + concepts:
        if norm(c["name"]) not in seen:
            seen.add(norm(c["name"]))
            merged.append(c)
    ents["concept"] = merged
    return ents


# ── expansion: every sensible combination ───────────────────────────────────


def expand(template: str, ents: dict[str, list[dict]], all_models: bool = False):
    """Every (keyword, values) a template makes. A pair is made once, and only
    between two models of the same kind (text with text). Image and speech
    models join only sections that say `all_models`: "prompt caching with
    elevenlabs v3" is not a search (2026-10-19)."""
    names = SLOT.findall(template)
    if not names:
        yield template, {}
        return
    pools = []
    for n in names:
        base = PAIRS.get(n, n)
        pool = ents.get(base) or []
        pair = any(PAIRS.get(m) == base for m in names) or n in PAIRS
        if base == "model" and (pair or not all_models):
            pool = [v for v in pool if v.get("kind", "text") == "text"]
        if not pool:
            return
        pools.append(pool)
    seen_pairs = set()
    for combo in itertools.product(*pools):
        used = dict(zip(names, combo, strict=True))
        skip = False
        for b, a in PAIRS.items():
            if a in used and b in used:
                pa, pb = norm(used[a]["name"]), norm(used[b]["name"])
                key = (
                    a,
                    *sorted((pa, pb)),
                    tuple(sorted(n for n in names if n not in (a, b))),
                    tuple(norm(used[n]["name"]) for n in names if n not in (a, b)),
                )
                if pa == pb or key in seen_pairs:
                    skip = True
                seen_pairs.add(key)
        if skip:
            continue
        kw = template
        for n, v in used.items():
            kw = kw.replace("{" + n + "}", v["name"])
        yield kw, used


def one_word_ok(keyword: str, used: dict) -> bool:
    return len(norm(keyword).split()) != 1 or bool(MODEL_SLOTS & set(used))


# ── volumes ─────────────────────────────────────────────────────────────────


def measure_shares(classes, planner, ents) -> dict[str, dict]:
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
            for v in ents.get(PAIRS.get(names[0], names[0])) or []:
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


# ── the page a keyword points at ────────────────────────────────────────────


def base_url(url: str) -> str:
    """A page type's URL without its pattern part: /compare?ids=<a>,<b> -> /compare."""
    url = re.sub(r"\?[^?]*<[^>]+>.*$", "", url)
    return re.sub(r"/<[^>]+>.*$", "", url) or "/"


def link(page_key: str, page: dict, used: dict, written: dict[str, str]) -> tuple[str, bool]:
    """(the URL, whether that exact page exists today)."""
    url = page["url"]
    model, model_b = used.get("model"), used.get("model_b")
    exists = page["kind"] == "page"
    if page_key == "compare":
        if model and model_b and model.get("id") and model_b.get("id"):
            return f"/compare?ids={model['id']},{model_b['id']}", True
        return "/compare", exists
    if page_key in ("model", "reports"):
        if model and model.get("id"):
            return url.replace("<model>", model["id"]), True
        return base_url(url), exists
    if page_key == "post":
        concept = used.get("concept") or used.get("concept_pair")
        if concept and norm(concept["name"]) in written:
            return f"/blogs/{written[norm(concept['name'])]}", True
        return "/blogs", False  # no post on this yet: one to write
    if page_key == "picker":
        job = used.get("job")
        if job and job.get("link"):
            return f"/model-picker?job={job['link'].rsplit('/', 1)[-1]}", True
        return url, True
    for n in ("job", "capability", "benchmark"):
        v = used.get(n)
        if v and v.get("link") and url.startswith("/reports"):
            return v["link"], True
    for n, v in used.items():
        if f"<{PAIRS.get(n, n)}>" in url:
            return url.replace(f"<{PAIRS.get(n, n)}>", slug(v["name"])), exists
    fill = next(iter(used.values()), None)
    if fill and "<" in url:
        return re.sub(r"<[^>]+>", slug(fill["name"]), url), exists
    return base_url(url), exists


def build(plan, planner, models, concepts, written) -> dict:
    ents = entities_of(plan, models, concepts)
    pages = plan["pages"]
    cls_of = {t: c for c, ts in (plan.get("share_classes") or {}).items() for t in ts}
    shares = measure_shares(plan.get("share_classes") or {}, planner, ents)
    taken: set[str] = set()
    keywords, sections = [], []
    for sec in plan["sections"]:
        if sec["page"] not in pages:
            raise SystemExit(f"section {sec['key']!r}: page {sec['page']!r} is not in `pages`")
        made = Counter()
        for t in sec["t"]:
            for kw, used in expand(t, ents, bool(sec.get("all_models"))):
                key = norm(kw)
                if key in taken or not one_word_ok(kw, used):
                    continue
                taken.add(key)
                made[t] += 1
                url, exists = link(sec["page"], pages[sec["page"]], used, written)
                keywords.append(
                    {
                        "keyword": kw,
                        "section": sec["key"],
                        "page": sec["page"],
                        "pattern": t,
                        "entity": " + ".join(v["name"] for v in used.values()),
                        "link": url,
                        "page_exists": exists,
                        **volume(key, t, used, planner, shares, cls_of),
                    }
                )
        sections.append(
            {
                **{k: v for k, v in sec.items() if k != "t"},
                "patterns": sec["t"],
                "keywords": sum(made.values()),
            }
        )
    counts = Counter(k["volume_kind"] or "none" for k in keywords)
    return {
        "built": datetime.now(UTC).date().isoformat(),
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pages": [{"key": k, **v} for k, v in pages.items()],
        "sections": sections,
        "keywords": keywords,
        "method": {
            "counts": {
                "keywords": len(keywords),
                "measured": counts["measured"],
                "estimated": counts["estimated"],
                "not_measured": counts["none"],
                "concepts": len(ents["concept"]),
                "models": len(ents["model"]),
                "posts_written": sum(
                    1 for k in keywords if k["page"] == "post" and k["page_exists"]
                ),
                "posts_to_write": sum(
                    1 for k in keywords if k["page"] == "post" and not k["page_exists"]
                ),
            },
            "shares": shares,
            "volume_source": "Google Keyword Planner bands, global, all languages, Jan-Jul 2026 "
            "(the workbook's 'Planner volumes (measured)' sheet)",
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--board", required=True, type=Path, help="the board SEO workbook (.xlsx)")
    ap.add_argument("--api", help="the board API, for catalog ids and published posts")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    plan = yaml.safe_load(PLAN.read_text(encoding="utf-8"))
    api = args.api.rstrip("/") if args.api else None
    concepts, written = blog_concepts(api)
    data = build(plan, read_planner(args.board), tracked_models(api), concepts, written)
    data["source"] = f"{args.board.name} + {PLAN.relative_to(ROOT).as_posix()}"
    args.out.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    c = data["method"]["counts"]
    print(
        f"wrote {args.out}: {c['keywords']} keywords in {len(data['sections'])} query types "
        f"({c['measured']} measured, {c['estimated']} estimated, "
        f"{c['not_measured']} not measured); "
        f"{c['concepts']} concepts, {c['models']} models"
    )
    for s in data["sections"]:
        print(f"  {s['key']:18} {s['keywords']:6}  -> {s['page']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
