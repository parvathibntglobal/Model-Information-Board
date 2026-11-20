"""READ-ONLY format profile of POSTS (no comments) per source, from raw payloads.

Population: documents with parent_id IS NULL that our fetches retrieved (so posts
that mention a tracked model or agent, never a platform-wide sample), created on or
after SINCE, at most N per source, random. Engagement is as of fetch time.

Writes:
  profile_rows.json   one feature row per post (no text)
  read_sample.txt     title + opening of the top and median posts per source, for
                      reading only (contains user text: never copy into a write-up,
                      and NEVER commit it)

Run from the repository root, with RAILWAY_DATABASE_URL in .env. Read-only.
"""

import json
import os
import random
import re
import statistics as st
import sys
import zlib
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[3]
load_dotenv(REPO / ".env")
os.environ["RAW_STORE_REMOTE"] = "postgres"
os.environ["DATABASE_URL"] = os.environ["RAILWAY_DATABASE_URL"]
sys.path.insert(0, str(REPO))
import psycopg  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
SINCE = "2026-08-01"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
SOURCES = ("reddit", "x", "bluesky", "hackernews", "devto", "github", "forum", "huggingface")

URL = re.compile(r"https?://\S+")
BULLET = re.compile(r"^\s*(?:[-*\u2022]|\d+[.)])\s+", re.M)
HEADING = re.compile(r"^\s*#{1,6}\s+\S", re.M)
HASHTAG = re.compile(r"(?<![\w&/])#[A-Za-z]\w*")
MENTION = re.compile(r"(?<![\w.])@[A-Za-z0-9_]{2,}")
EMOJI = re.compile("[\U0001f300-\U0001faff\u2600-\u27bf\u2b50\u2705]")
DIGIT = re.compile(r"\d")
NUMBER = re.compile(r"\d+(?:[.,]\d+)?%?")
TAGPREFIX = re.compile(r"^\s*[\[(][^\])]{1,30}[\])]")


def body_features(t: str) -> dict:
    t = t or ""
    lines = [ln for ln in t.splitlines() if ln.strip()]
    paras = [p for p in re.split(r"\n\s*\n", t) if p.strip()]
    first = lines[0] if lines else ""
    return {
        "chars": len(t),
        "words": len(t.split()),
        "lines": len(lines),
        "paras": len(paras),
        "bullets": len(BULLET.findall(t)),
        "headings": len(HEADING.findall(t)),
        "code_blocks": t.count("```") // 2 + t.count("<pre"),
        "table": bool(re.search(r"\|\s*-{3,}", t)),
        "links": len(URL.findall(t)),
        "hashtags": len(HASHTAG.findall(t)),
        "mentions": len(MENTION.findall(t)),
        "emoji": len(EMOJI.findall(t)),
        "questions": t.count("?"),
        "ends_question": t.rstrip().endswith("?"),
        "numbers": len(NUMBER.findall(URL.sub("", t))),
        "first_line_chars": len(first),
    }


def title_features(t: str) -> dict:
    t = (t or "").strip()
    return {
        "t_chars": len(t),
        "t_words": len(t.split()),
        "t_question": t.endswith("?"),
        "t_digit": bool(DIGIT.search(t)),
        "t_colon": ":" in t,
        "t_tag": bool(TAGPREFIX.match(t)),
        "t_excl": "!" in t,
        "t_caps_word": bool(re.search(r"\b[A-Z]{4,}\b", t)),
    }


def parse(src: str, p: dict) -> dict | None:
    """(title, body, extra, engagement) per platform; None for a payload that is not a post."""
    if src == "reddit":
        hint = p.get("post_hint") or ("gallery" if p.get("is_gallery") else None)
        extra = {
            "kind": "text"
            if p.get("is_self")
            else ("video" if p.get("is_video") else (hint or "link")),
            "group": p.get("subreddit"),
            "flair": p.get("link_flair_text"),
            "domain": p.get("domain"),
        }
        return {
            "title": p.get("title"),
            "body": p.get("selftext") or "",
            "extra": extra,
            "eng": p.get("score") or 0,
            "eng2": p.get("num_comments") or 0,
        }
    if src == "x":
        lg = p.get("legacy") or {}
        note = (
            ((p.get("note_tweet") or {}).get("note_tweet_results") or {}).get("result") or {}
        ).get("text")
        if lg.get("in_reply_to_status_id_str"):
            return None
        media = (lg.get("extended_entities") or lg.get("entities") or {}).get("media") or []
        kinds = sorted({m.get("type") for m in media})
        ext = [u for u in (lg.get("entities") or {}).get("urls") or []]
        extra = {
            "kind": "+".join(kinds) if kinds else ("link" if ext else "text"),
            "long_post": bool(note),
            "quote": bool(lg.get("is_quote_status")),
            "media_n": len(media),
        }
        body = note or lg.get("full_text") or ""
        body = re.sub(r"\s*https://t\.co/\w+$", "", body)  # trailing media/link stub
        return {
            "title": None,
            "body": body,
            "extra": extra,
            "eng": lg.get("favorite_count") or 0,
            "eng2": lg.get("reply_count") or 0,
            "views": int((p.get("views") or {}).get("count") or 0),
            "bookmarks": lg.get("bookmark_count") or 0,
            "reposts": lg.get("retweet_count") or 0,
        }
    if src == "bluesky":
        rec = p.get("record") or {}
        if rec.get("reply"):
            return None
        et = (
            ((p.get("embed") or rec.get("embed") or {}).get("$type") or "")
            .split(".")[-1]
            .replace("#view", "")
        )
        return {
            "title": None,
            "body": rec.get("text") or "",
            "extra": {"kind": et or "text"},
            "eng": p.get("likeCount") or 0,
            "eng2": p.get("replyCount") or 0,
            "reposts": p.get("repostCount") or 0,
        }
    if src == "hackernews":
        if p.get("parent_id") or p.get("type") not in (None, "story"):
            return None
        title = p.get("title") or ""
        kind = (
            "show_hn"
            if title.startswith("Show HN")
            else "ask_hn"
            if title.startswith("Ask HN")
            else "link"
            if p.get("url")
            else "text"
        )
        dom = re.sub(r"^https?://(www\.)?", "", p.get("url") or "").split("/")[0]
        return {
            "title": title,
            "body": re.sub(r"<[^>]+>", " ", p.get("text") or ""),
            "extra": {"kind": kind, "domain": dom},
            "eng": p.get("points") or 0,
            "eng2": len(p.get("children") or []),
        }
    if src == "devto":
        return {
            "title": p.get("title"),
            "body": p.get("body_markdown") or "",
            "extra": {
                "kind": "article",
                "tags": p.get("tag_list"),
                "cover": bool(p.get("cover_image")),
                "reading_min": p.get("reading_time_minutes"),
                "ai_disclosure": p.get("ai_disclosure_level"),
                "has_description": bool(p.get("description")),
            },
            "eng": p.get("public_reactions_count") or 0,
            "eng2": p.get("comments_count") or 0,
        }
    if src == "github":
        return {
            "title": p.get("title"),
            "body": p.get("body") or "",
            "extra": {"kind": p.get("kind"), "group": p.get("repository")},
            "eng": p.get("upvotes") or 0,
            "eng2": p.get("comments") or 0,
        }
    if src == "forum":
        return {
            "title": p.get("title"),
            "body": p.get("raw") or "",
            "extra": {"kind": "topic", "group": p.get("forum")},
            "eng": max((p.get("posts_count") or 1) - 1, 0),
            "eng2": max((p.get("posts_count") or 1) - 1, 0),
        }
    if src == "huggingface":
        ev = p.get("events") or []
        first = next((e for e in ev if e.get("type") == "comment"), None)
        if first is None:
            return None
        return {
            "title": p.get("title"),
            "body": ((first.get("data") or {}).get("latest") or {}).get("raw") or "",
            "extra": {
                "kind": "pull_request" if p.get("isPullRequest") else "discussion",
                "group": (p.get("repo") or {}).get("type"),
            },
            "eng": sum(1 for e in ev if e.get("type") == "comment") - 1,
            "eng2": sum(1 for e in ev if e.get("type") == "comment") - 1,
        }
    return None


def main() -> None:
    random.seed(20261118)
    c = psycopg.connect(os.environ["RAILWAY_DATABASE_URL"], connect_timeout=20)
    c.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
    rows, reading = [], []
    for src in SOURCES:
        ids = c.execute(
            "SELECT id, text_ref, created_at FROM document WHERE source=%s AND parent_id IS NULL"
            " AND text_ref IS NOT NULL AND created_at >= %s",
            (src, SINCE),
        ).fetchall()
        pool = len(ids)
        random.shuffle(ids)
        got, seen_err = [], 0
        want = ids[: int(N * 1.5) + 20]
        refs = [r[1] for r in want]
        tomb = {
            k[: -len(".tombstone")]
            for (k,) in c.execute(
                "SELECT key FROM raw_blob WHERE key = ANY(%s)", ([r + ".tombstone" for r in refs],)
            )
        }
        blobs = {
            k: zlib.decompress(bytes(d))
            for k, d in c.execute("SELECT key, data FROM raw_blob WHERE key = ANY(%s)", (refs,))
        }
        for did, ref, created in want:
            if len(got) >= N:
                break
            try:
                if ref in tomb:
                    raise KeyError("tombstoned")  # a takedown is honoured, never read
                p = json.loads(blobs[ref].decode("utf-8"))
            except Exception:  # unreadable payload: counted, not guessed at
                seen_err += 1
                continue
            r = parse(src, p)
            if r is None:
                continue
            f = {
                "source": src,
                "id": did,
                "created": created.date().isoformat(),
                "pool": pool,
                **body_features(r["body"]),
                **(title_features(r["title"]) if r["title"] is not None else {}),
                **{k: v for k, v in r.items() if k not in ("title", "body", "extra")},
                **{"x_" + k: v for k, v in r["extra"].items()},
            }
            got.append(f)
            reading.append((src, r["eng"], r["title"], r["body"]))
        print(
            f"{src}: pool {pool} posts since {SINCE}, profiled {len(got)}, unreadable {seen_err}",
            flush=True,
        )
        rows.extend(got)
    c.close()
    with open(os.path.join(OUT, "profile_rows.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, default=str)
    with open(os.path.join(OUT, "read_sample.txt"), "w", encoding="utf-8") as fh:
        for src in SOURCES:
            mine = sorted([r for r in reading if r[0] == src], key=lambda r: -r[1])
            if not mine:
                continue
            mid = len(mine) // 2
            for label, chunk in (("TOP", mine[:12]), ("MEDIAN", mine[mid : mid + 8])):
                fh.write(f"\n######## {src} {label}\n")
                for _s, eng, title, body in chunk:
                    fh.write(f"--- eng={eng} title={title!r}\n{(body or '')[:700]}\n")
    print("rows", len(rows), "median helper ok" if st.median([1, 2, 3]) == 2 else "")


if __name__ == "__main__":
    main()
