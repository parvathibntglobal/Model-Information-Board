# ruff: noqa: E501
"""Instagram trial for blog ideas: one run a day for two weeks, from 2026-11-04.

Step 4 of docs/scoping-instagram-and-substack.md. Reads one page (about 41
posts: 32 recent and 9 top) from each hashtag below through RapidAPI's
"Instagram Looter" (instagram-looter2), a third-party provider; Instagram has
no official public-search route open to us. LOCAL ONLY: posts go to
`_instagram_trial/<date>/`, never to the database or the board. Feeding the
board would need a contract entry like X's `x-via-rapidapi-scraper`.

What a run measures, per hashtag and in total, so the two weeks end with a
rate measured on posts this script did not choose:
  posts        captions returned
  model        captions naming a model (pattern)
  first_hand   captions reading like first-hand use: I / we + used, tried,
               built, switched, tested (pattern; an upper bound - promotion
               says "I built" too)
  promo        captions with promotion markers (link in bio, comment X, ...)
  english      captions that look English (function words, few non-ASCII
               letters)
The patterns are rough and stated here so a reader can check them.

Run from the repo root:  python scripts/_instagram_trial.py
Costs 5 RapidAPI calls (plan: 15,000 a month). The key is read from .env and
never printed.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

import httpx

HASHTAGS = ["claudeai", "chatgpt", "aitools", "aiagents", "promptengineering"]
OUT = Path("_instagram_trial")

MODEL = re.compile(r"\b(claude|opus|sonnet|haiku|gpt[- ]?\d|chatgpt|gemini|llama|deepseek|qwen|grok|mistral|kimi|glm|copilot|cursor)\b", re.I)
FIRST = re.compile(r"\b(i|i've|i'm|we|we've|my|our)\b[^.!?\n]{0,80}\b(used|tried|built|switched|tested|use|using|shipped)\b", re.I)
PROMO = re.compile(r"(link in (my )?bio|follow (us|me|for)|comment ['\"“]?\w+|dm (me|us)|\bcourse\b|free guide|save this|giveaway|#ad\b|sponsored)", re.I)
ENGLISH = re.compile(r"\b(the|and|to|of|is|it|for|with|that|you|this)\b", re.I)


def env() -> dict[str, str]:
    vals: dict[str, str] = {}
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Z0-9_]+)=(.*)$", line.strip())
        if m:
            vals[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return vals


def is_english(text: str) -> bool:
    letters = sum(1 for ch in text if ch.isalpha())
    foreign = sum(1 for ch in text if ord(ch) > 127 and ch.isalpha())
    return bool(ENGLISH.search(text)) and letters > 0 and foreign / letters < 0.05


def posts_of(body: dict) -> list[dict]:
    tag = body["data"]["hashtag"]
    seen, out = set(), []
    for edge in tag["edge_hashtag_to_media"].get("edges", []) + tag["edge_hashtag_to_top_posts"].get("edges", []):
        n = edge["node"]
        if n["shortcode"] in seen:
            continue
        seen.add(n["shortcode"])
        caption = " ".join(e["node"]["text"] for e in n.get("edge_media_to_caption", {}).get("edges", []))
        out.append({
            "url": f"https://www.instagram.com/p/{n['shortcode']}/",
            "owner_id": n.get("owner", {}).get("id"),
            "taken_at": dt.datetime.fromtimestamp(n.get("taken_at_timestamp", 0), dt.UTC).isoformat(),
            "likes": n.get("edge_liked_by", {}).get("count"),
            "comments": n.get("edge_media_to_comment", {}).get("count"),
            "is_video": n.get("is_video"),
            "caption": caption,
            "model": bool(MODEL.search(caption)),
            "first_hand": bool(FIRST.search(caption)),
            "promo": bool(PROMO.search(caption)),
            "english": is_english(caption),
        })
    return out


def main() -> int:
    vals = env()
    key, host = vals.get("RAPIDAPI_KEY"), vals.get("RAPIDAPI_HOST")
    if not key or not host or "instagram" not in host:
        sys.exit("RAPIDAPI_KEY / RAPIDAPI_HOST for instagram-looter2 are not the last values in .env")
    today = dt.date.today().isoformat()
    day = OUT / today
    day.mkdir(parents=True, exist_ok=True)
    rows = []
    with httpx.Client(timeout=45, headers={"x-rapidapi-key": key, "x-rapidapi-host": host}) as c:
        for tag in HASHTAGS:
            r = c.get(f"https://{host}/tag-feeds", params={"query": tag})
            remaining = r.headers.get("x-ratelimit-requests-remaining")
            if r.status_code != 200:
                print(f"#{tag}: HTTP {r.status_code}, skipped (calls left: {remaining})")
                continue
            posts = posts_of(r.json())
            (day / f"{tag}.json").write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
            row = {"date": today, "hashtag": tag, "posts": len(posts)}
            for k in ("model", "first_hand", "promo", "english"):
                row[k] = sum(1 for p in posts if p[k])
            row["calls_left"] = remaining
            rows.append(row)
            print(f"#{tag}: {row['posts']} posts, {row['first_hand']} first-hand, {row['promo']} promo, {row['english']} English, {row['model']} name a model")
    summary = OUT / "summary.csv"
    new = not summary.exists()
    with summary.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "hashtag", "posts", "model", "first_hand", "promo", "english", "calls_left"])
        if new:
            w.writeheader()
        w.writerows(rows)
    total = {k: sum(r[k] for r in rows) for k in ("posts", "model", "first_hand", "promo", "english")}
    print(f"total {today}: {total} -> {day}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
