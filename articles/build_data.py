"""Parse a scraped arXiv report (Markdown) into the JSON the Articles UI renders.

Source of truth is the Markdown scrape under `articles/<model>/arxiv-report.md`;
the JSON under `web/src/data/` is derived and re-buildable, so a re-scrape is a
re-run of this, never a hand-edit of the JSON.

    python articles/build_data.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]

# One entry per model+platform we have a scrape for.
SOURCES = [
    {
        "model_id": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "platform": "arxiv",
        "source": "arXiv API — export.arxiv.org",
        "scraped_at": "2026-08-31T11:02:15Z",
        "note": (
            "The phrase appears in 0 of 43 titles — every mention is in an "
            "abstract. No paper introduces DeepSeek V4 Pro; it appears as a "
            "model evaluated, benchmarked, or used as a baseline/judge."
        ),
        "md": ROOT / "articles" / "deepseek-v4-pro" / "arxiv-report.md",
        "out": ROOT / "web" / "src" / "data" / "deepseek-v4-pro-arxiv.json",
    },
]


def parse_articles(text: str) -> list[dict]:
    parts = re.split(r"\n### (\d+)\.\s+", text)
    articles = []
    for i in range(1, len(parts), 2):
        num = int(parts[i])
        body = parts[i + 1]
        title = body.splitlines()[0].strip()

        def grab(pat, flags=0, body=body):
            m = re.search(pat, body, flags)
            return m.group(1).strip() if m else None

        cats_raw = grab(r"\*\*Categories:\*\*\s*(.+)")
        primary, categories = None, []
        if cats_raw:
            pm = re.search(r"primary:\s*`([^`]+)`", cats_raw)
            primary = pm.group(1) if pm else None
            cats_only = re.sub(r"\(primary:.*?\)", "", cats_raw)
            categories = [c.strip() for c in cats_only.split(",") if c.strip()]

        authors_raw = grab(r"\*\*Authors:\*\*\s*(.+)")
        authors, authors_more = [], 0
        if authors_raw:
            mm = re.search(r"\(\+(\d+)\s+more\)", authors_raw)
            authors_more = int(mm.group(1)) if mm else 0
            cleaned = re.sub(r",?\s*\.\.\.\s*\(\+\d+\s+more\)", "", authors_raw).replace("...", "")
            authors = [a.strip() for a in cleaned.split(",") if a.strip()]

        forms_raw = grab(r"\*\*Form used:\*\*\s*(.+)")
        forms = re.findall(r"`([^`]+)`", forms_raw) if forms_raw else []
        mm = re.search(r"\*\*Mention:\*\*\s*\n\n\s*>\s*(.+)", body)
        am = re.search(r"<summary>Abstract</summary>\s*(.*?)\s*</details>", body, re.S)

        articles.append({
            "rank": num,
            "title": title,
            "arxiv_id": grab(r"\*\*arXiv ID:\*\*\s*`([^`]+)`"),
            "published": grab(r"\*\*Published:\*\*\s*([0-9-]+)"),
            "updated": grab(r"\*\*Updated:\*\*\s*([0-9-]+)"),
            "categories": categories,
            "primary_category": primary,
            "authors": authors,
            "authors_more": authors_more,
            "abs_url": grab(r"\[abs\]\(([^)]+)\)"),
            "pdf_url": grab(r"\[pdf\]\(([^)]+)\)"),
            "forms_used": forms,
            "mention": mm.group(1).strip() if mm else None,
            "abstract": am.group(1).strip() if am else None,
        })
    return articles


def summarise(articles: list[dict]) -> dict:
    by_cat = collections.Counter(a["primary_category"] for a in articles if a["primary_category"])
    by_month = collections.Counter(a["published"][:7] for a in articles if a["published"])
    by_form = collections.Counter(f for a in articles for f in a["forms_used"])
    dates = sorted(a["published"] for a in articles if a["published"])
    return {
        "count": len(articles),
        "date_from": dates[0] if dates else None,
        "date_to": dates[-1] if dates else None,
        "by_primary_category": dict(by_cat.most_common()),
        "by_month": dict(sorted(by_month.items())),
        "by_form": dict(by_form.most_common()),
    }


def main() -> None:
    for src in SOURCES:
        text = src["md"].read_text(encoding="utf-8")
        articles = parse_articles(text)
        meta_keys = ("model_id", "display_name", "platform", "source", "scraped_at", "note")
        payload = {k: src[k] for k in meta_keys}
        payload["summary"] = summarise(articles)
        payload["articles"] = articles
        src["out"].parent.mkdir(parents=True, exist_ok=True)
        src["out"].write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        rel = src["out"].relative_to(ROOT)
        print(f"{src['model_id']}/{src['platform']}: {len(articles)} articles -> {rel}")


if __name__ == "__main__":
    main()
