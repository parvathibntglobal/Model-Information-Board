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
    {
        "model_id": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "platform": "reddit",
        "kind": "reddit",
        "source": "Reddit via RapidAPI (reddit34) — brand sweep",
        "scraped_at": "2026-09-01T06:36:39Z",
        "note": (
            "1,601 posts collected across 87 queries and 40 subreddit listings; "
            "727 matched the keyword literally in the text. 150 were hand-read "
            "and labelled by content type. Comments were fetched but excluded "
            "from this report by instruction. Posts-only: removed/deleted posts "
            "are filtered upstream by the API, so their absence is a retrieval "
            "property, not a finding."
        ),
        "sweep": {
            "records": 1601,
            "literal_matches": 727,
            "labelled": 150,
            "subreddits": 149,
            "authors": 530,
            "external_links": 4535,
        },
        "md": ROOT / "articles" / "deepseek-v4-pro" / "DeepSeek-V4-Pro-Reddit-Report.md",
        "out": ROOT / "web" / "src" / "data" / "deepseek-v4-pro-reddit.json",
    },
    {
        "model_id": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "platform": "hn",
        "kind": "hn",
        "source": "Hacker News via Algolia — subject-thread sweep",
        "scraped_at": "2026-09-01T11:05:05Z",
        "note": (
            "Instead of matching the literal phrase, this run finds threads whose "
            "own title is about the model and reads every comment. 167 subject "
            "threads (75 with discussion), 4,917 comments; 34 were hand-picked as "
            "new analytical cases, none of which the phrase sweep had caught."
        ),
        "sweep": {
            "subject_threads": 167,
            "threads_with_discussion": 75,
            "comments_fetched": 4917,
            "cases": 34,
        },
        "md": ROOT / "articles" / "deepseek-v4-pro" / "DeepSeek-V4-Pro_HN_SubjectThreads_Report.md",
        "out": ROOT / "web" / "src" / "data" / "deepseek-v4-pro-hn.json",
    },
]

# HN §3 case categories -> content-type keys.
HN_TYPE = {
    "Benchmark results and evaluation methodology": "benchmark",
    "Cost, caching and self-hosting economics": "cost",
    "Local inference, quantization and hardware": "hardware",
    "First-hand production evaluation and dissent": "production",
}
HN_CASE = re.compile(
    r"^\*\*\[(\d+)\]\((https?://[^)]+)\)\*\*\s*-\s*(\d{4}-\d{2}-\d{2})\s*\|\s*"
    r"by\s+(.+?)\s*\|\s*in\s*\*(.+?)\*\s*\((\d+)\s*pts?\)"
)

# Reddit content-type sections (§6 full entries, §7 compact tables).
REDDIT_TYPE = {
    "Deep Analysis": "deep_analysis",
    "Benchmark": "benchmark",
    "Usage Demo": "usage_demo",
    "Workflow/Setup": "workflow",
    "Tutorial": "tutorial",
    "Comparison": "comparison",
    "Opinion": "opinion",
    "Announcement": "announcement",
    "Promo": "promo",
    "News Roundup": "news_roundup",
    "Question": "question",
}
REDDIT_TITLE = re.compile(r"^\*\*(\d+)\.\s+(.*?)\*\*\s*$")
REDDIT_META = re.compile(
    r"r/(\S+)\s*·\s*u/(\S+)\s*·\s*`(t2_\w+)`\s*·\s*score\s*(-?\d+)\s*·\s*"
    r"(\d+)\s*comments\s*·\s*(\d{4}-\d{2}-\d{2})\s*·\s*substance\s*([\d.]+)\s*·\s*(subject|mention)"
)

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


def _split_cells(line: str) -> list[str]:
    return [c.strip() for c in line.replace(r"\|", "\x00").strip().strip("|").split("|")]


def _reddit_table_row(by_col: dict, content_type: str) -> dict | None:
    """A §7 compact-table row, keyed by header column so both table shapes work.

    The Question table drops author-id / cmts / substance; everything is looked
    up by column name and missing columns come back None.
    """
    title_cell = by_col.get("title / thread") or by_col.get("title") or ""
    tm = re.match(r"\[(.*?)\]\((https?://[^)]+)\)", title_cell)
    sub = by_col.get("subreddit", "")
    author = by_col.get("author", "")
    subj = (by_col.get("subj?") or "").lower()
    substance = by_col.get("substance") or ""
    return {
        "rank": int(by_col.get("#") or 0),
        "title": tm.group(1).strip() if tm else title_cell,
        "url": tm.group(2) if tm else None,
        "subreddit": sub[2:] if sub.startswith("r/") else sub,
        "author": author[2:] if author.startswith("u/") else author,
        "author_id": (by_col.get("author id") or "").strip("`") or None,
        "score": _num(r"(-?\d+)", by_col.get("score", "")),
        "comments": _num(r"(\d+)", by_col.get("cmts", "")),
        "date": None,
        "substance": float(substance) if re.match(r"[\d.]+$", substance) else None,
        "subject": subj == "subject",
        "content_type": content_type,
        "why_label": None,
        "excerpt": (by_col.get("excerpt") or "").replace("\x00", "|").strip(),
    }


def parse_reddit(text: str) -> list[dict]:
    """§6 full entries + §7 compact tables, tagged with the section's content type."""
    lines = text.splitlines()
    posts: list[dict] = []
    cur_type: str | None = None
    table_cols: list[str] | None = None

    for i, line in enumerate(lines):
        if line.startswith("### "):
            head = re.sub(r"^###\s*\d+\.\d+\s+", "", line)
            name = re.sub(r"\s*—.*$", "", head).strip()
            cur_type = REDDIT_TYPE.get(name)
            table_cols = None
            continue
        if line.startswith("|"):
            cells = _split_cells(line)
            low = [c.lower() for c in cells]
            if "subreddit" in low:
                table_cols = low  # header row
                continue
            if all(set(c) <= {"-", ":"} for c in cells if c):
                continue  # separator row
            if cur_type and table_cols and cells and cells[0].isdigit():
                row = _reddit_table_row(dict(zip(table_cols, cells, strict=False)), cur_type)
                if row:
                    posts.append(row)
            continue

        m = REDDIT_TITLE.match(line)
        if not m or cur_type is None:
            continue
        url = None
        for j in range(i + 1, min(i + 4, len(lines))):
            um = re.search(r"\]\((https?://[^)]+)\)", lines[j])
            if um:
                url = um.group(1)
                break
        meta = None
        for k in range(i + 1, min(i + 6, len(lines))):
            mm = REDDIT_META.search(lines[k])
            if mm:
                meta, meta_at = mm, k
                break
        if not meta:
            continue
        why_label, excerpt = None, None
        for q in range(meta_at + 1, min(meta_at + 12, len(lines))):
            body = lines[q].lstrip()
            if body.startswith(">"):
                text_q = body[1:].strip()
                wl = re.match(r"\*\*Why this label:\*\*\s*(.*)", text_q)
                if wl:
                    why_label = wl.group(1).strip()
                elif excerpt is None:
                    excerpt = text_q
            elif re.match(r"\*\*\d+\.", body):
                break
        posts.append({
            "rank": int(m.group(1)),
            "title": m.group(2).strip(),
            "url": url,
            "subreddit": meta.group(1),
            "author": meta.group(2),
            "author_id": meta.group(3),
            "score": int(meta.group(4)),
            "comments": int(meta.group(5)),
            "date": meta.group(6),
            "substance": float(meta.group(7)),
            "subject": meta.group(8) == "subject",
            "content_type": cur_type,
            "why_label": why_label,
            "excerpt": excerpt,
        })
    return posts


def summarise_reddit(posts: list[dict], sweep: dict) -> dict:
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


def parse_hn(text: str) -> list[dict]:
    """The §3 analysis cases — a comment per entry, tagged with its category."""
    lines = text.splitlines()
    posts: list[dict] = []
    cur_type: str | None = None

    for i, line in enumerate(lines):
        if line.startswith("### "):
            name = re.sub(r"\s*\(\d+\)\s*$", "", line[4:]).strip()
            cur_type = HN_TYPE.get(name)
            continue
        m = HN_CASE.match(line)
        if not m or cur_type is None:
            continue
        hn_id, url, date, author, thread, pts = m.groups()
        note, quote = None, None
        for j in range(i + 1, min(i + 8, len(lines))):
            s = lines[j].strip()
            qm = re.match(r"-\s*>\s*(.+)", s)
            if qm:
                quote = qm.group(1).strip()
                continue
            nm = re.match(r"-\s+(.+)", s)
            if nm and note is None:
                note = nm.group(1).strip()
                continue
            if s.startswith("**[") or s.startswith("#"):
                break
        posts.append({
            "rank": len(posts) + 1,
            "hn_id": hn_id,
            "url": url,
            "date": date,
            "author": author.strip(),
            "thread": thread.strip(),
            "points": int(pts),
            "content_type": cur_type,
            "note": note,
            "quote": quote,
        })
    return posts


def summarise_hn(posts: list[dict], sweep: dict) -> dict:
    by_type = collections.Counter(p["content_type"] for p in posts if p["content_type"])
    dates = sorted(p["date"] for p in posts if p["date"])
    return {
        "count": len(posts),
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
        elif src.get("kind") == "reddit":
            items = parse_reddit(text)
            payload["summary"] = summarise_reddit(items, src["sweep"])
            payload["posts"] = items
            label = "posts"
        elif src.get("kind") == "hn":
            items = parse_hn(text)
            payload["summary"] = summarise_hn(items, src["sweep"])
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
