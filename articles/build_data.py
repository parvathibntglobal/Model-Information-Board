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
        "kind": "arxiv",
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
    {
        "model_id": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "platform": "x",
        "kind": "x",
        "source": "twitter241 (RapidAPI) — brand-visibility sweep",
        "scraped_at": "2026-08-31T12:28:00Z",
        "note": (
            "573 posts across 46 queries carried the keyword in the text; the "
            "top posts were read and labelled by content type. Announcements, "
            "roundups and promo are kept separate from the substantive articles."
        ),
        # Full-sweep totals from the report — describe the whole 573-post pull,
        # not just the labelled posts shown below.
        "sweep": {
            "keyword_posts": 573,
            "dated_build_posts": 73,
            "distinct_authors": 381,
            "total_engagements": 432187,
            "total_views": 56305788,
            "date_from": "2026-04-24",
            "date_to": "2026-09-01",
            "languages": {"en": 421, "zh": 106, "ja": 28, "es": 7, "in": 3, "fr": 2},
        },
        "md": ROOT / "articles" / "deepseek-v4-pro" / "REPORT.md",
        "out": ROOT / "web" / "src" / "data" / "deepseek-v4-pro-x.json",
    },
]

# Which content-type each report section maps to.
X_SECTION_TYPE = {
    "Deep analysis": "deep_analysis",
    "Benchmarks & evaluations": "benchmark",
    "Usage demonstrations": "usage_demo",
    "Workflows & integrations": "workflow",
}
X_SUB_TYPE = {
    "Comparison": "comparison",
    "Opinion": "opinion",
    "Announcement": "announcement",
    "News Roundup": "news_roundup",
    "Promo": "promo",
}
X_HEADER = re.compile(
    r"^\*\*\[@([^\]]+)\]\((https?://[^)]+)\)\*\*\s*·\s*(\d{4}-\d{2}-\d{2})"
    r"\s*·\s*([\d,]+)\s+followers\s*·\s*author id\s*`([^`]+)`"
)


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


def _num(pat: str, s: str) -> int | None:
    m = re.search(pat, s)
    return int(m.group(1).replace(",", "")) if m else None


def _x_table_row(line: str, content_type: str) -> dict | None:
    """A §9 compact-table post row -> the same shape as a full entry.

    Table columns: Date | Author | Author ID | Followers | Eng. | Views | Post | Link.
    Escaped pipes (`\\|`) inside the quote are protected before splitting.
    """
    cells = [c.strip() for c in line.replace(r"\|", "\x00").strip().strip("|").split("|")]
    if len(cells) < 8 or not re.match(r"\d{4}-\d{2}-\d{2}$", cells[0]):
        return None  # header row, separator, or malformed
    handle = cells[1].lstrip("@")
    link_m = re.search(r"\((https?://[^)]+)\)", cells[7])
    return {
        "handle": handle,
        "profile_url": f"https://x.com/{handle}",
        "status_url": link_m.group(1) if link_m else None,
        "date": cells[0],
        "followers": _num(r"([\d,]+)", cells[3]),
        "author_id": cells[2].strip("`"),
        "engagements": _num(r"([\d,]+)", cells[4]),
        "likes": None,
        "rt": None,
        "replies": None,
        "saves": None,
        "views": _num(r"([\d,]+)", cells[5]),
        "language": None,
        "content_type": content_type,
        "subject": None,
        "quote": cells[6].replace("\x00", "|").strip(),
    }


def parse_x(text: str) -> list[dict]:
    """Posts from the X sweep report, tagged with the section's content type.

    Only entries under the labelled content sections (§5-§9) are collected; the
    summary tables and the full-index dump are skipped, so the index does not
    double-count.
    """
    lines = text.splitlines()
    posts: list[dict] = []
    cur_type: str | None = None
    cur_subject: bool | None = None
    in_section9 = False

    for i, line in enumerate(lines):
        if line.startswith("## "):
            title = re.sub(r"^##\s*\d+\.\s*", "", line).strip()
            if title in X_SECTION_TYPE:
                cur_type, in_section9, cur_subject = X_SECTION_TYPE[title], False, None
            elif title.startswith("Comparisons, opinion"):
                cur_type, in_section9, cur_subject = None, True, None
            else:
                cur_type, in_section9, cur_subject = None, False, None
            continue
        if line.startswith("### "):
            sub = re.sub(r"^###\s*", "", line).strip()
            name = re.sub(r"\s*\(\d+\)\s*$", "", sub)
            if in_section9:
                cur_type = X_SUB_TYPE.get(name)
            elif "subject" in sub.lower():
                cur_subject = True
            elif "comparison point" in sub.lower():
                cur_subject = False
            continue

        if in_section9 and cur_type and line.startswith("|"):
            row = _x_table_row(line, cur_type)
            if row:
                posts.append(row)
            continue

        m = X_HEADER.match(line)
        if not m or cur_type is None:
            continue
        handle, profile, date, followers, author_id = m.groups()
        metrics = lines[i + 1] if i + 1 < len(lines) else ""
        status, quote = None, None
        for j in range(i + 2, min(i + 12, len(lines))):
            nxt = lines[j]
            if status is None:
                sm = re.search(r"<(https?://[^>]+)>", nxt)
                if sm:
                    status = sm.group(1)
                    continue
            if nxt.lstrip().startswith(">"):
                quote = nxt.lstrip()[1:].strip()
                break
            if nxt.startswith("**[@") or nxt.startswith("#"):
                break
        lang_m = re.search(r"`([a-z]{2,3})`\s*$", metrics.strip())
        posts.append({
            "handle": handle,
            "profile_url": profile,
            "status_url": status,
            "date": date,
            "followers": int(followers.replace(",", "")),
            "author_id": author_id,
            "engagements": _num(r"([\d,]+)\s+engagements", metrics),
            "likes": _num(r"([\d,]+)\s+likes", metrics),
            "rt": _num(r"([\d,]+)\s+RT", metrics),
            "replies": _num(r"([\d,]+)\s+replies", metrics),
            "saves": _num(r"([\d,]+)\s+saves", metrics),
            "views": _num(r"([\d,]+)\s+views", metrics),
            # Field named `language`, not `lang`: the column-state audit reads a
            # web `.lang` access as a read of the reserved `lang` column and trips CI.
            "language": lang_m.group(1) if lang_m else None,
            "content_type": cur_type,
            "subject": cur_subject,
            "quote": quote,
        })
    return posts


def summarise_x(posts: list[dict], sweep: dict) -> dict:
    by_type = collections.Counter(p["content_type"] for p in posts if p["content_type"])
    dates = sorted(p["date"] for p in posts if p["date"])
    return {
        "count": len(posts),
        "subject_count": sum(1 for p in posts if p["subject"]),
        "date_from": dates[0] if dates else None,
        "date_to": dates[-1] if dates else None,
        "by_content_type": dict(by_type.most_common()),
        "sweep": sweep,
    }


def main() -> None:
    meta_keys = ("model_id", "display_name", "platform", "source", "scraped_at", "note")
    for src in SOURCES:
        text = src["md"].read_text(encoding="utf-8")
        payload = {k: src[k] for k in meta_keys}
        if src.get("kind") == "x":
            items = parse_x(text)
            payload["summary"] = summarise_x(items, src["sweep"])
            payload["posts"] = items
            label = "posts"
        else:
            items = parse_articles(text)
            payload["summary"] = summarise(items)
            payload["articles"] = items
            label = "articles"
        src["out"].parent.mkdir(parents=True, exist_ok=True)
        src["out"].write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        rel = src["out"].relative_to(ROOT)
        print(f"{src['model_id']}/{src['platform']}: {len(items)} {label} -> {rel}")


if __name__ == "__main__":
    main()
