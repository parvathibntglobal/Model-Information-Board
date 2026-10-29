"""Probe the candidate news sources for the Admin News section (2026-10-28).

ONE READ PER SOURCE, NOTHING STORED IN ANY DATABASE. For each source this asks
robots.txt first (collect/adapters/blog/robots.py, which matches `*` and `$`
rules - the stdlib parser does not, and missed GitHub's `/*.atom$` on
2026-10-22), fetches once through the identifying client, and measures what a
News section would get: how many items, how fresh, which fields each carries,
and how many are about LLMs.

    python scripts/probe_news_sources.py [--out probe.json]

THE LLM SHARE IS A KEYWORD COUNT, NOT A CLASSIFIER. It is the share of items
whose title or summary contains one of `LLM_WORDS` - a measurement of how much
filtering a source would need, never a filter (rule 8).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collect.adapters.blog.robots import RobotsGate  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.http import build_client  # noqa: E402

#: (key, group, label, kind, url). Groups are the 2026-10-22 shortlist's.
SOURCES = [
    # SELECTED: fresh, free, and the terms allow it.
    ("aiwire", "selected", "AIWire", "feed", "https://aiwire.dev/feed.xml"),
    ("techcrunch_ai", "selected", "TechCrunch AI", "feed",
     "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("gdelt", "selected", "GDELT (keyword search, 48 h)", "gdelt",
     "https://api.gdeltproject.org/api/v2/doc/doc?query=%28%22large%20language%20model%22%20OR%20LLM%20OR%20OpenAI%20OR%20Anthropic%20OR%20%22Gemini%22%29%20sourcelang%3Aeng&mode=artlist&format=json&maxrecords=75&timespan=48h&sort=datedesc"),
    # PROBABLY FINE: official feeds, no rule against headline + link.
    ("openai", "lab", "OpenAI News", "feed", "https://openai.com/news/rss.xml"),
    ("google_deepmind", "lab", "Google DeepMind blog", "feed", "https://deepmind.google/blog/rss.xml"),
    ("google_ai", "lab", "Google AI (The Keyword)", "feed", "https://blog.google/technology/ai/rss/"),
    ("google_research", "lab", "Google Research blog", "feed", "https://research.google/blog/rss/"),
    ("google_developers", "lab", "Google Developers blog", "feed",
     "https://developers.googleblog.com/feeds/posts/default"),
    ("mistral", "lab", "Mistral AI news", "feed", "https://mistral.ai/news/rss"),
    ("openrouter_blog", "lab", "OpenRouter blog", "feed", "https://openrouter.ai/blog/feed.xml"),
    ("simonwillison", "writer", "Simon Willison", "feed", "https://simonwillison.net/atom/everything/"),
    ("latent_space", "writer", "Latent Space (incl. AINews)", "feed", "https://www.latent.space/feed"),
    ("tldr_ai", "writer", "TLDR AI", "feed", "https://tldr.tech/api/rss/ai"),
    ("interconnects", "writer", "Interconnects", "feed", "https://www.interconnects.ai/feed"),
    # Release news through the API: GitHub's robots.txt disallows `*.atom`.
    ("gh_vllm", "release", "vLLM releases", "github", "https://api.github.com/repos/vllm-project/vllm/releases?per_page=30"),
    ("gh_llamacpp", "release", "llama.cpp releases", "github", "https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=30"),
    ("gh_ollama", "release", "Ollama releases", "github", "https://api.github.com/repos/ollama/ollama/releases?per_page=30"),
    ("gh_transformers", "release", "transformers releases", "github", "https://api.github.com/repos/huggingface/transformers/releases?per_page=30"),
]

LLM_WORDS = re.compile(
    r"\b(llms?|language models?|gpt[- ]?\d|chatgpt|claude|gemini|llama|mistral|qwen|deepseek|"
    r"grok|kimi|glm|minimax|openai|anthropic|reasoning model|fine-?tun|inference|tokens?|"
    r"agents?|agentic|transformer|rag|embeddings?|open[- ]weights?)\b", re.I)


def _when(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=UTC)
    return None


def _measure(items: list[dict], now: datetime) -> dict:
    dated = [i["at"] for i in items if i["at"]]
    text = [f"{i['title']} {i['summary']}" for i in items]
    return {
        "items": len(items),
        "undated": len(items) - len(dated),
        "newest": max(dated).isoformat() if dated else None,
        "oldest": min(dated).isoformat() if dated else None,
        "last_48h": sum(d >= now - timedelta(hours=48) for d in dated),
        "last_7d": sum(d >= now - timedelta(days=7) for d in dated),
        "llm_keyword_items": sum(bool(LLM_WORDS.search(t)) for t in text),
        "with_summary": sum(bool(i["summary"].strip()) for i in items),
        "with_author": sum(bool(i["author"]) for i in items),
        "with_image": sum(bool(i["image"]) for i in items),
        "with_categories": sum(bool(i["categories"]) for i in items),
        "sample": [{"title": i["title"][:120], "at": i["at"].isoformat() if i["at"] else None,
                    "link": i["link"]} for i in items[:3]],
    }


def _feed_items(body: bytes) -> tuple[list[dict], str | None]:
    parsed = feedparser.parse(body)
    items = []
    for e in parsed.entries:
        links = e.get("links", [])
        image = bool(e.get("media_content") or e.get("media_thumbnail")
                     or any(link.get("type", "").startswith("image") for link in links))
        items.append({
            "title": (e.get("title") or "").strip(), "link": e.get("link"),
            "summary": re.sub(r"<[^>]+>", " ", e.get("summary") or ""),
            "author": e.get("author"), "image": image,
            "categories": [t.get("term") for t in e.get("tags", []) if t.get("term")],
            "at": _when(e),
        })
    return items, (str(parsed.bozo_exception)[:120] if parsed.bozo and not parsed.entries else None)


def _github_items(data: list) -> list[dict]:
    return [{
        "title": f"{r.get('name') or r.get('tag_name')}", "link": r.get("html_url"),
        "summary": (r.get("body") or "")[:400], "author": (r.get("author") or {}).get("login"),
        "image": False, "categories": ["prerelease"] if r.get("prerelease") else [],
        "at": (datetime.fromisoformat(r["published_at"].replace("Z", "+00:00"))
               if r.get("published_at") else None),
    } for r in data if isinstance(r, dict)]


def _gdelt_items(data: dict) -> list[dict]:
    out = []
    for a in data.get("articles") or []:
        seen = a.get("seendate")  # 20261028T081500Z
        at = datetime.strptime(seen, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC) if seen else None
        out.append({"title": a.get("title") or "", "link": a.get("url"), "summary": "",
                    "author": a.get("domain"), "image": bool(a.get("socialimage")),
                    "categories": [a.get("sourcecountry")] if a.get("sourcecountry") else [],
                    "at": at})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="news_probe.json")
    args = ap.parse_args()
    agent = settings().user_agent
    now = datetime.now(UTC)
    results = []
    with build_client(user_agent=agent, follow_redirects=False, timeout=30.0) as client:
        gate = RobotsGate(client, user_agent=agent)
        last_at: dict[str, float] = {}
        for key, group, label, kind, url in SOURCES:
            row = {"key": key, "group": group, "label": label, "kind": kind, "url": url}
            decision = gate.allows(url)
            row["robots"] = {"allowed": decision.allowed, "reason": decision.reason}
            if not decision.allowed:
                row["outcome"] = "robots refused"
                results.append(row)
                print(f"{key:18s} ROBOTS REFUSED: {decision.reason}", flush=True)
                continue
            host = url.split("/")[2]
            wait = gate.min_interval(url) - (time.monotonic() - last_at.get(host, 0))
            if wait > 0:
                time.sleep(wait)
            try:
                hops, response = 0, client.get(url)
                # Every redirect hop is asked of robots.txt too.
                while response.is_redirect and hops < 5:
                    nxt = str(response.next_request.url)
                    if not gate.allows(nxt).allowed:
                        raise RuntimeError(f"redirect to {nxt} refused by robots.txt")
                    response, hops = client.get(nxt), hops + 1
            except Exception as exc:  # noqa: BLE001 - a probe reports, it does not stop
                row["outcome"] = f"error: {type(exc).__name__}: {str(exc)[:120]}"
                results.append(row)
                print(f"{key:18s} {row['outcome']}", flush=True)
                continue
            last_at[host] = time.monotonic()
            row["http"] = response.status_code
            row["bytes"] = len(response.content)
            row["content_type"] = response.headers.get("content-type", "")[:60]
            if response.status_code != 200:
                row["outcome"] = f"HTTP {response.status_code}"
                results.append(row)
                print(f"{key:18s} HTTP {response.status_code}", flush=True)
                continue
            problem = None
            try:
                if kind == "feed":
                    items, problem = _feed_items(response.content)
                elif kind == "github":
                    items = _github_items(response.json())
                else:
                    items = _gdelt_items(response.json())
            except ValueError as exc:
                items, problem = [], f"unparseable: {str(exc)[:100]} | {response.text[:80]!r}"
            row.update(_measure(items, now))
            row["outcome"] = problem or ("ok" if items else "ok, but no items")
            results.append(row)
            print(f"{key:18s} {row['outcome']:16s} items={row.get('items')} "
                  f"48h={row.get('last_48h')} 7d={row.get('last_7d')} "
                  f"llm={row.get('llm_keyword_items')}", flush=True)
    Path(args.out).write_text(json.dumps({"probed_at": now.isoformat(), "user_agent": agent,
                                          "sources": results}, indent=1), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
