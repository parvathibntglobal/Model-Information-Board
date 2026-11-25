# ruff: noqa: E501
"""News-page candidates from daily.dev's "best AI news sources" list (anooj, 2026-11-25).

READ-ONLY AND STORES NOTHING: no raw store, no database, no article read. One robots.txt
ask and one feed read per candidate URL, through the board's identifying client.

    python docs/measurements/news-candidates-2026-11-25.py OUT.json

PER CANDIDATE, ON THE DAY IT RUNS
  robots      allowed / refused for the feed URL, by collect/adapters/blog/robots.py (the
              matcher the News harvest itself uses: `*` and `$` rules, every redirect hop).
  feed        the first candidate URL that answers 200 AND parses as RSS/Atom with items.
              Every URL tried is recorded with its outcome, so "no feed" names what was asked.
  items       what that feed served that day; `newest` and `items_7d` are over that window,
              never over the publication.
  summary     items carrying a summary/description of >= 8 words (the contract's
              `summary_min_words`), and items carrying a picture (Media RSS, an image
              enclosure, or an <img> in the item).
  llm_items   items whose title or summary contains one of the contract's `llm_keywords`
              (whole words, any case): a measure of how on-topic, never a filter.

LIMITS: one day. A feed URL guessed at the usual paths and refused is "no feed found at
these paths", not "no feed".
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import feedparser
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from collect.adapters.blog.robots import RobotsGate  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.http import build_client  # noqa: E402
from collect.news.harvest import _get  # noqa: E402 - the harvest's own robots-per-hop GET

#: key -> (label, [candidate feed URLs, tried in order]). Picked from the daily.dev list
#: on 2026-11-25; sources the News page already carries are not here.
CANDIDATES = {
    "the_batch": ("The Batch (DeepLearning.AI)", [
        "https://www.deeplearning.ai/the-batch/feed/",
        "https://www.deeplearning.ai/feed/",
        "https://www.deeplearning.ai/the-batch/rss.xml",
    ]),
    "import_ai": ("Import AI (Jack Clark)", [
        "https://importai.substack.com/feed",
        "https://jack-clark.net/feed/",
    ]),
    "bens_bites": ("Ben's Bites", [
        "https://www.bensbites.com/feed",
        "https://bensbites.beehiiv.com/feed",
    ]),
    "the_rundown": ("The Rundown AI", [
        "https://www.therundown.ai/feed",
        "https://rss.beehiiv.com/feeds/2R3C6Bt5wj.xml",
    ]),
    "anthropic": ("Anthropic news and research", [
        "https://www.anthropic.com/rss.xml",
        "https://www.anthropic.com/news/rss.xml",
        "https://www.anthropic.com/feed.xml",
    ]),
    "huggingface_blog": ("Hugging Face blog", [
        "https://huggingface.co/blog/feed.xml",
    ]),
    "marktechpost": ("MarkTechPost", [
        "https://www.marktechpost.com/feed/",
    ]),
    "ahead_of_ai": ("Ahead of AI (Sebastian Raschka)", [
        "https://magazine.sebastianraschka.com/feed",
    ]),
    "techpresso": ("Techpresso", [
        "https://dupple.com/techpresso/feed",
        "https://techpresso.beehiiv.com/feed",
    ]),
}

contract = yaml.safe_load((ROOT / "contract" / "news_sources.yaml").read_text(encoding="utf-8"))
LLM = re.compile(r"\b(" + "|".join(re.escape(w) for w in contract["llm_keywords"]) + r")\b", re.I)
MIN_WORDS = int(contract["summary_min_words"])
TAG = re.compile(r"<[^>]+>")


def has_picture(e) -> bool:
    if e.get("media_content") or e.get("media_thumbnail"):
        return True
    if any((x.get("type") or "").startswith("image/") for x in e.get("enclosures", [])):
        return True
    body = " ".join([e.get("summary", "")] + [c.get("value", "") for c in e.get("content", [])])
    return "<img" in body


def when(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime(*t[:6], tzinfo=UTC) if t else None


def main(out_path: str) -> None:
    now = datetime.now(UTC)
    client = build_client()
    gate = RobotsGate(client, user_agent=settings().user_agent)
    out = {"run_at": now.isoformat(timespec="seconds"), "candidates": {}}
    for key, (label, urls) in CANDIDATES.items():
        rec = {"label": label, "tried": [], "feed": None}
        for url in urls:
            try:
                r, refusal = _get(client, gate, url, {})
            except Exception as e:  # noqa: BLE001 - a failure is recorded, not raised
                rec["tried"].append({"url": url, "error": f"{type(e).__name__}: {str(e)[:120]}"})
                continue
            if refusal:
                rec["tried"].append({"url": url, "robots": refusal[:200]})
                continue
            f = feedparser.parse(r.content)
            n = len(f.entries)
            rec["tried"].append({"url": url, "robots": "allowed", "http": r.status_code,
                                 "final_url": str(r.url), "items": n})
            if r.status_code == 200 and n:
                dates = [d for d in (when(e) for e in f.entries) if d]
                summ = [TAG.sub(" ", e.get("summary", "")) for e in f.entries]
                rec["feed"] = {
                    "url": url,
                    "title": f.feed.get("title"),
                    "items": n,
                    "newest": max(dates).date().isoformat() if dates else None,
                    "oldest": min(dates).date().isoformat() if dates else None,
                    "items_7d": sum(d >= now - timedelta(days=7) for d in dates),
                    "undated": n - len(dates),
                    "with_summary": sum(len(s.split()) >= MIN_WORDS for s in summ),
                    "with_picture": sum(has_picture(e) for e in f.entries),
                    "llm_items": sum(bool(LLM.search(e.get("title", "") + " " + s))
                                     for e, s in zip(f.entries, summ, strict=True)),
                    "with_author": sum(bool(e.get("author")) for e in f.entries),
                }
                break
        out["candidates"][key] = rec
        fd = rec["feed"]
        print(key, "->", f"{fd['items']} items, newest {fd['newest']}, {fd['items_7d']} in 7d, "
              f"summary {fd['with_summary']}, picture {fd['with_picture']}, llm {fd['llm_items']}"
              if fd else "NO FEED " + json.dumps(rec["tried"]))
    Path(out_path).write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
