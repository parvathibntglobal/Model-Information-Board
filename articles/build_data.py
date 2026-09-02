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
    {
        "model_id": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "platform": "devto",
        "kind": "devto",
        "source": "dev.to (Forem API) — retrieval sweep",
        "scraped_at": "2026-09-01T12:00:00Z",
        "note": (
            "725 posts fetched, 620 distinct after dedupe, from 146 authors. Most "
            "are the same launch announcement reworded. The usable set shown here "
            "is the stricter cut: 53 articles carrying at least two non-inheritable "
            "artifacts (a benchmark number, an error output, a conditioned "
            "comparison), excluding probable-generated accounts."
        ),
        "sweep": {
            "posts": 725,
            "distinct": 620,
            "authors": 146,
            "usable": 53,
        },
        "md": ROOT / "articles" / "deepseek-v4-pro" / "devto-deepseek-v4-pro.md.md",
        "out": ROOT / "web" / "src" / "data" / "deepseek-v4-pro-devto.json",
    },
    {
        "model_id": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "platform": "tiktok",
        "kind": "tiktok",
        "source": "TikTok — social tracking sweep",
        "scraped_at": "2026-09-02T00:00:00Z",
        "note": (
            "137 on-target V4 Pro videos, 1,719,640 views. Reach is extremely "
            "top-heavy — the single most-viewed video is 43.7% of all on-target "
            "TikTok reach by itself, and the median video draws 687.5 views. The "
            "top 30 by views are shown; aggregate counts describe a handful of "
            "breakout videos, not typical performance."
        ),
        "sweep": {
            "posts": 137,
            "views": 1719640,
            "likes": 77302,
            "comments": 2442,
            "shares": 6706,
        },
        "md": ROOT / "articles" / "deepseek-v4-pro" / "DeepSeek_V4_Pro_Report_2026-09-02.md",
        "out": ROOT / "web" / "src" / "data" / "deepseek-v4-pro-tiktok.json",
    },
    {
        "model_id": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "platform": "instagram",
        "kind": "instagram",
        "source": "Instagram hashtag feed — social tracking sweep",
        "scraped_at": "2026-09-02T00:00:00Z",
        "note": (
            "377 on-target V4 Pro posts. Instagram's hashtag feed exposes no view, "
            "share or save count, and a like count on only 48.8% of returned posts "
            "(hidden, not absent, on the rest), so like totals are a floor, not a "
            "total. The top 30 by likes + comments are shown, ranked on that "
            "visible engagement."
        ),
        "sweep": {
            "posts": 377,
            "likes": 10943,
            "comments": 2038,
            "likes_visible_pct": 48.8,
        },
        "md": ROOT / "articles" / "deepseek-v4-pro" / "DeepSeek_V4_Pro_Report_2026-09-02.md",
        "out": ROOT / "web" / "src" / "data" / "deepseek-v4-pro-instagram.json",
    },
    {
        "model_id": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "platform": "hf",
        "kind": "hf",
        "source": "Hugging Face (Hub API) — retrieval sweep across four surfaces",
        "scraped_at": "2026-09-01T09:00:00Z",
        "note": (
            "Three surfaces, shown together under a surface filter: 295 model "
            "repos (4 official, 291 community re-uploads, 1.4M downloads), 281 "
            "discussion threads, and 32 papers. Repos are vendor artefacts whose "
            "cards are announcements — the only first-hand surface is discussions, "
            "of which 22 carry >=2 artifacts. Repos are the 30 most-downloaded; "
            "discussions and papers are the >=2-artifact set with their text."
        ),
        "sweep": {
            "repos_found": 295,
            "repos_official": 4,
            "downloads_total": 1404100,
            "discussions": 281,
            "discussions_nonpr": 230,
            "disc_authors": 257,
            "papers": 32,
            "papers_v4pro": 16,
        },
        "md": ROOT / "articles" / "deepseek-v4-pro" / "hf-deepseek-v4-pro-sweep.md",
        "out": ROOT / "web" / "src" / "data" / "deepseek-v4-pro-hf.json",
    },
    {
        "model_id": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "platform": "hashnode",
        "kind": "hashnode",
        "source": "Hashnode (GraphQL search) — tag + keyword sweep",
        "scraped_at": "2026-09-02T00:00:00Z",
        "note": (
            "A thin surface: 11 in-window posts (one more excluded as out-of-window), "
            "8 authors, 8 publications. Only 6 are actually about DeepSeek V4 Pro and "
            "only 2 are first-hand; 5 are cross-posted from a company blog. Filter by "
            "relevance — core, adjacent (Flash/vision), or passing mention. Each card "
            "carries the sweep's own provenance read and evidence note."
        ),
        "sweep": {
            "posts": 11,
            "authors": 8,
            "publications": 8,
            "core": 6,
            "first_hand": 2,
            "cross_posted": 5,
            "strong_artifacts": 6,
        },
        "md": ROOT / "articles" / "deepseek-v4-pro"
        / "Hashnode_DeepSeek_V4_Pro_Sweep_2026-09-02.md",
        "out": ROOT / "web" / "src" / "data" / "deepseek-v4-pro-hashnode.json",
    },
]

# The social report's top-post tables (§4.1 TikTok, §4.2 Instagram). Each cell's
# post link is `[open](url)`; there is no per-post content type, so these panels
# rank by engagement rather than filter by category.
SOCIAL_LINK = re.compile(r"\[open\]\((https?://[^)]+)\)")

# Hugging Face: one panel over three surfaces, filtered by `content_type`
# (repo / discussion / paper). Repos are capped at the most-downloaded few;
# discussions and papers are the >=2-artifact cut, joined to their full text.
HF_REPO_LIMIT = 30

# Hashnode filters by relevance rather than post type — the type column is too
# freeform for clean chips, so it rides along as a display field. The §3 table
# is joined to §4 (provenance) by URL for the full title, provenance read and
# evidence note.
HASHNODE_RELEVANCE = (
    ("out of window", "out_of_window"),
    ("anomaly", "out_of_window"),
    ("core", "core"),
    ("adjacent", "adjacent"),
    ("passing", "passing"),
)

# dev.to §"usable set" Type column -> content-type keys.
DEVTO_TYPE = {
    "benchmark": "benchmark",
    "tutorial": "tutorial",
    "first-hand analysis": "first_hand",
    "news summary": "news_summary",
    "announcement": "announcement",
}
DEVTO_LINK = re.compile(r"\[(.*?)\]\((https?://[^)]+)\)")

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


def _devto_num(cell: str) -> int | None:
    m = re.search(r"\d+", cell)
    return int(m.group()) if m else None


def parse_devto(text: str) -> list[dict]:
    """The §"usable set" table — 53 articles, with a body excerpt matched by rank.

    Metadata comes from the compact table (author, date, type, provenance,
    artifact counts, reactions); the full title and a short excerpt come from
    the §"Full text" section, keyed on the same `### N.` rank.
    """
    lines = text.splitlines()

    # Pass 1: full titles + first substantive body line, keyed by rank.
    titles: dict[int, str] = {}
    excerpts: dict[int, str] = {}
    cur: int | None = None
    for line in lines:
        hm = re.match(r"^###\s+(\d+)\.\s+(.+)", line)
        if hm:
            cur = int(hm.group(1))
            titles[cur] = hm.group(2).strip()
            continue
        if cur is None or cur in excerpts or not line.startswith("    "):
            continue
        s = re.sub(r"^\s*>\s*", "", line.strip())  # drop blockquote marker
        s = s.replace("**", "").strip()
        if len(s) < 40 or s.startswith("|") or s.startswith("#"):
            continue
        if "originally published on" in s.lower():
            continue
        excerpts[cur] = s[:320]

    # Pass 2: the usable-set table.
    posts: list[dict] = []
    in_table = False
    for line in lines:
        if line.startswith("## The usable set"):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 11 or not cells[0].isdigit():
            continue
        rank = int(cells[0])
        link = DEVTO_LINK.match(cells[3])
        content_type = DEVTO_TYPE.get(
            cells[7].lower(), cells[7].lower().replace(" ", "_").replace("-", "_")
        )
        posts.append({
            "rank": rank,
            "title": titles.get(rank) or (link.group(1).strip() if link else cells[3]),
            "url": link.group(2) if link else None,
            "author": cells[4].strip("`"),
            "stratum": "independent" if cells[5] == "ind" else "syndicated",
            "date": cells[6],
            "content_type": content_type,
            "provenance": cells[8],
            "cross_posted": cells[9],
            "reactions": _devto_num(cells[10]) or 0,
            "distinct_artifacts": _devto_num(cells[1]) or 0,
            "all_artifacts": _devto_num(cells[2]) or 0,
            "excerpt": excerpts.get(rank),
        })
    return posts


def summarise_devto(posts: list[dict], sweep: dict) -> dict:
    by_type = collections.Counter(p["content_type"] for p in posts if p["content_type"])
    dates = sorted(p["date"] for p in posts if p["date"])
    return {
        "count": len(posts),
        "date_from": dates[0] if dates else None,
        "date_to": dates[-1] if dates else None,
        "by_content_type": dict(by_type.most_common()),
        "sweep": sweep,
    }


def _social_rows(text: str, header: str) -> list[list[str]]:
    """Cell lists of the markdown table under the §4.x heading containing `header`."""
    rows: list[list[str]] = []
    in_sec = False
    for line in text.splitlines():
        if not in_sec:
            if line.startswith("### ") and header in line:
                in_sec = True
            continue
        if line.startswith("#"):
            break
        if line.startswith("|"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def _social_int(cell: str) -> int | None:
    m = re.search(r"-?[\d,]+", cell)
    return int(m.group().replace(",", "")) if m else None


def parse_tiktok(text: str) -> list[dict]:
    """§4.1 — top videos ranked by views. Columns: # Creator Date Views Likes
    Comments Shares ER Post Caption."""
    posts: list[dict] = []
    for c in _social_rows(text, "TikTok (ranked by views)"):
        if len(c) < 10 or not c[0].isdigit():
            continue
        link = SOCIAL_LINK.search(c[8])
        posts.append({
            "rank": int(c[0]),
            "creator": c[1],
            "date": c[2],
            "views": _social_int(c[3]),
            "likes": _social_int(c[4]),
            "comments": _social_int(c[5]),
            "shares": _social_int(c[6]),
            "engagement_rate": c[7] or None,
            "url": link.group(1) if link else None,
            "caption": c[9].strip() or None,
        })
    return posts


def parse_instagram(text: str) -> list[dict]:
    """§4.2 — top posts ranked by likes + comments. Columns: # Creator Date Likes
    Comments Post Caption. No view/share/save counts on Instagram's feed."""
    posts: list[dict] = []
    for c in _social_rows(text, "Instagram (ranked by likes + comments)"):
        if len(c) < 7 or not c[0].isdigit():
            continue
        link = SOCIAL_LINK.search(c[5])
        posts.append({
            "rank": int(c[0]),
            "creator": c[1],
            "date": c[2],
            "likes": _social_int(c[3]),
            "comments": _social_int(c[4]),
            "url": link.group(1) if link else None,
            "caption": c[6].strip() or None,
        })
    return posts


def summarise_social(posts: list[dict], sweep: dict) -> dict:
    dates = sorted(p["date"] for p in posts if p["date"])
    return {
        "count": len(posts),
        "date_from": dates[0] if dates else None,
        "date_to": dates[-1] if dates else None,
        "sweep": sweep,
    }


def _hf_clean(s: str | None) -> str | None:
    """Undo the report's LaTeX-style escapes so `\\$15` / `52.2\\%` read plainly."""
    return re.sub(r"\\([$%_&#()])", r"\1", s) if s else s


def _hf_licence(cell: str) -> str | None:
    v = cell.replace("*", "").strip()
    return None if v in ("—", "", "none") else v


def _hf_rows(text: str, heading: str) -> list[list[str]]:
    """Cell lists of the markdown table under an exact `## ` heading."""
    rows: list[list[str]] = []
    in_sec = False
    for line in text.splitlines():
        if not in_sec:
            if line.strip() == heading:
                in_sec = True
            continue
        if line.startswith("#"):
            break
        if line.startswith("|"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def _hf_fulltext_excerpts(text: str, start: str, end: str, key: re.Pattern) -> dict:
    """Map an entry key (URL or paper id) to its first substantive body line, over
    the `### N.` entries between the `start` and `end` (h2) headings."""
    out: dict[str, str] = {}
    in_sec = False
    cur: str | None = None
    for line in text.splitlines():
        if not in_sec:
            if line.startswith(start):
                in_sec = True
            continue
        if line.startswith(end):
            break
        if re.match(r"^###\s+\d+\.", line):
            cur = None
            continue
        km = key.match(line)
        if km:
            cur = km.group(1)
            continue
        if cur and cur not in out and line.startswith("    "):
            s = line.strip()
            if len(s) >= 12 and not s.startswith("|") and not s.startswith(">"):
                out[cur] = s[:360]
    return out


def parse_hf(text: str) -> list[dict]:
    """Three surfaces merged into one list, each tagged with its `content_type`:
    the top model repos by downloads, the >=2-artifact discussions (with body
    text), and the >=2-artifact papers (with abstract)."""
    disc_ex = _hf_fulltext_excerpts(
        text, "## Full text — the 22 discussions", "## Abstracts",
        re.compile(r"\s*-\s*\*\*URL:\*\*\s*(\S+)"),
    )
    paper_ex = _hf_fulltext_excerpts(
        text, "## Abstracts — the 15 papers", "\x00never",
        re.compile(r"\s*-\s*\*\*Paper:\*\*\s*`([^`]+)`"),
    )
    items: list[dict] = []

    for c in _hf_rows(text, "## Model repos"):
        if len(c) < 11 or not c[0].isdigit() or int(c[0]) > HF_REPO_LIMIT:
            continue
        link = DEVTO_LINK.match(c[1])
        items.append({
            "rank": int(c[0]),
            "content_type": "repo",
            "title": link.group(1) if link else c[1],
            "url": link.group(2) if link else None,
            "official": "Y" in c[2],
            "downloads": _social_int(c[3]),
            "likes": _social_int(c[4]),
            "modified": c[5],
            "licence": _hf_licence(c[6]),
            "discussions": _social_int(c[10]),
        })

    for c in _hf_rows(text, "## Discussions"):
        if len(c) < 14 or not c[0].isdigit():
            continue
        artifacts = _social_int(c[1]) or 0
        if artifacts < 2:
            continue
        link = DEVTO_LINK.match(c[2])
        url = link.group(2) if link else None
        items.append({
            "rank": int(c[0]),
            "content_type": "discussion",
            "title": _hf_clean(link.group(1) if link else c[2]),
            "url": url,
            "author": c[3].strip("`"),
            "repo": c[4],
            "date": c[5],
            "status": c[6],
            "disc_type": c[7],
            "provenance": c[8],
            "lang": c[9],
            "is_pr": "Y" in c[10],
            "vendor_reply": "Y" in c[11],
            "comments": _social_int(c[12]),
            "artifacts": artifacts,
            "excerpt": _hf_clean(disc_ex.get(url)),
        })

    for c in _hf_rows(text, "## Papers"):
        if len(c) < 9 or not c[0].isdigit():
            continue
        artifacts = _social_int(c[1]) or 0
        if artifacts < 2:
            continue
        link = DEVTO_LINK.match(c[2])
        paper_id = c[3].strip("`")
        items.append({
            "rank": int(c[0]),
            "content_type": "paper",
            "title": _hf_clean(link.group(1) if link else c[2]),
            "url": link.group(2) if link else None,
            "paper_id": paper_id,
            "date": c[4],
            "upvotes": _social_int(c[5]),
            "comments": _social_int(c[6]),
            "authors": _social_int(c[7]),
            "names_v4pro": "Y" in c[8],
            "artifacts": artifacts,
            "excerpt": _hf_clean(paper_ex.get(paper_id)),
        })
    return items


def summarise_hf(items: list[dict], sweep: dict) -> dict:
    by_type = collections.Counter(i["content_type"] for i in items)
    dates = sorted(i["date"] for i in items if i.get("date"))
    return {
        "count": len(items),
        "date_from": dates[0] if dates else None,
        "date_to": dates[-1] if dates else None,
        "by_content_type": dict(by_type.most_common()),
        "sweep": sweep,
    }


def _hashnode_author(cell: str) -> tuple[str | None, str | None]:
    name = cell.split("<br>")[0].strip()
    if name in ("—", "-", ""):
        name = None
    hm = re.search(r"`@?([^`]+)`", cell)
    return name, (hm.group(1).strip() if hm else None)


def _hashnode_relevance(cell: str) -> str:
    low = cell.lower()
    for needle, key in HASHNODE_RELEVANCE:
        if needle in low:
            return key
    return low.split()[0] if low.split() else "other"


def _hashnode_provenance(text: str) -> dict:
    """§4 keyed by URL: the full title, the sweep's provenance read, its evidence."""
    out: dict[str, dict] = {}
    in_sec = False
    cur: dict | None = None
    for line in text.splitlines():
        if not in_sec:
            if line.strip().startswith("## 4."):
                in_sec = True
            continue
        if line.startswith("## "):
            break
        hm = re.match(r"^###\s+(.+)", line)
        if hm:
            cur = {"title": hm.group(1).strip()}
            continue
        if cur is None:
            continue
        um = re.match(r"\s*-\s*\*\*URL:\*\*\s*(\S+)", line)
        if um:
            out[um.group(1)] = cur
            continue
        wm = re.match(r"\s*-\s*\*\*Whose result:\*\*\s*(.+)", line)
        if wm:
            cur["whose_result"] = wm.group(1).replace("**", "").strip()
            continue
        em = re.match(r"\s*-\s*\*\*Evidence:\*\*\s*(.+)", line)
        if em:
            cur["evidence"] = em.group(1).strip().strip('"')
    return out


def parse_hashnode(text: str) -> list[dict]:
    """§3 (every post returned) joined to §4 (provenance) by URL. Filtered in the
    UI by relevance; the freeform post type rides along as a display field."""
    prov = _hashnode_provenance(text)
    posts: list[dict] = []
    for c in _hf_rows(text, "## 3. Every post returned"):
        if len(c) < 14 or not c[0].isdigit():
            continue
        link = DEVTO_LINK.match(c[1])
        url = link.group(2) if link else None
        p = prov.get(url, {})
        name, handle = _hashnode_author(c[2])
        cross = c[13].replace("`", "").strip()
        posts.append({
            "rank": int(c[0]),
            "title": _hf_clean(p.get("title") or (link.group(1) if link else c[1])),
            "url": url,
            "author": name,
            "handle": handle,
            "publication": c[3].replace("`", "").strip() or None,
            "date": None if c[4].strip() in ("—", "") else c[4].strip(),
            "read_time": c[5].strip() if re.search(r"\d", c[5]) else None,
            "upvotes": _social_int(c[6]),
            "comments": _social_int(c[7]),
            "views": _social_int(c[8]),
            "post_type": c[9].strip() or None,
            "content_type": _hashnode_relevance(c[10]),
            "relevance": c[10].strip(),
            "artifacts": _social_int(c[11]),
            "strong_artifacts": _social_int(c[12]),
            "cross_posted": None if cross.lower() in ("no", "", "—") else cross,
            "whose_result": p.get("whose_result"),
            "excerpt": _hf_clean((p.get("evidence") or "")[:360]) or None,
        })
    return posts


def summarise_hashnode(posts: list[dict], sweep: dict) -> dict:
    by_type = collections.Counter(p["content_type"] for p in posts if p["content_type"])
    dates = sorted(p["date"] for p in posts if p.get("date"))
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
        elif src.get("kind") == "devto":
            items = parse_devto(text)
            payload["summary"] = summarise_devto(items, src["sweep"])
            payload["posts"] = items
            label = "posts"
        elif src.get("kind") == "tiktok":
            items = parse_tiktok(text)
            payload["summary"] = summarise_social(items, src["sweep"])
            payload["posts"] = items
            label = "posts"
        elif src.get("kind") == "instagram":
            items = parse_instagram(text)
            payload["summary"] = summarise_social(items, src["sweep"])
            payload["posts"] = items
            label = "posts"
        elif src.get("kind") == "hf":
            items = parse_hf(text)
            payload["summary"] = summarise_hf(items, src["sweep"])
            payload["posts"] = items
            label = "posts"
        elif src.get("kind") == "hashnode":
            items = parse_hashnode(text)
            payload["summary"] = summarise_hashnode(items, src["sweep"])
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
