# ruff: noqa: E501
"""Agent search probe, 2026-11-09. READ-ONLY: public search APIs, no DB, no model call.

For each agent and each query (compound aliases, and search pairs for Muse and
Dots), ask each platform once and sort what comes back:
  compound      the text names the agent by a compound alias (separators folded)
  pair-context  no compound, but the bare name sits within 200 chars of a
                giveaway (Meta/WhatsApp/agent... ; OpenAI/ChatGPT/agent...)
  muse-model    names a Muse MODEL (Spark, Wonder, Glimmer) and no compound
  unclear       none of the above
Raw responses go to RAW_DIR (they hold Reddit/X text: never committed); the
output JSON holds counts only. One page per query: Hacker News top 20 stories
and 20 comments since 2026-08-01; Bluesky latest 50; dev.to 30 (titles and
descriptions only, so its sort is not a usable precision signal); Reddit one
RELEVANCE page; X one Latest page. Reddit and X "sampled" counts text fields
(a post's title and body count separately), so read them as shares.

Keys and providers come from the environment: RAPIDAPI_KEY (Reddit's),
X_RAPIDAPI_KEY, REDDIT_PROVIDER, SCRAPER_PROVIDER. Note that the main
checkout's .env declares RAPIDAPI_KEY twice and dotenv keeps the last one;
Reddit's key is the first, so export it explicitly.

    RAW_DIR=... python docs/measurements/agent-search-probe-2026-11-09.py OUT.json
"""
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8")
RAW = Path(os.environ.get("RAW_DIR") or tempfile.mkdtemp(prefix="agent_probe_raw_"))
RAW.mkdir(parents=True, exist_ok=True)
UA = "ModelInformationBoard/1.0 (+https://github.com/parvathibntglobal/Model-Information-Board)"
SINCE = 1785542400  # 2026-08-01

REDDIT_KEY, X_KEY = os.environ["RAPIDAPI_KEY"], os.environ["X_RAPIDAPI_KEY"]
REDDIT_HOST = os.environ["REDDIT_PROVIDER"] + ".p.rapidapi.com"
X_HOST = os.environ["SCRAPER_PROVIDER"] + ".p.rapidapi.com"

IC = re.IGNORECASE
AGENTS = {
    "Grok Bot": {"aliases": ["grok bot", "grokbot"], "pairs": [], "bare": None, "near": None},
    "OpenClaw": {"aliases": ["openclaw"], "pairs": [], "bare": None, "near": None},
    "Hermes Agent": {"aliases": ["hermes agent"], "pairs": [], "bare": None, "near": None},
    "Muse": {"aliases": ["meta muse", "muse by meta"], "pairs": ["muse meta", "muse whatsapp"],
             "bare": r"\bMuse\b", "near": r"\b(?:meta|whatsapp|instagram|zuckerberg|agent|assistant)\b"},
    "ChatGPT Work": {"aliases": ["chatgpt work"], "pairs": [], "bare": None, "near": None},
    "Claude Cowork": {"aliases": ["claude cowork", "cowork"], "pairs": [], "bare": None, "near": None},
    "Claude Duet": {"aliases": ["claude duet", "anthropic duet"], "pairs": [], "bare": None, "near": None},
    "Dots": {"aliases": ["openai dots", "chatgpt dots"], "pairs": ["dots openai", "dots chatgpt"],
             "bare": r"\bDots\b", "near": r"\b(?:openai|chatgpt|altman|agent|assistant)\b"},
    "Gemini Spark": {"aliases": ["gemini spark"], "pairs": [], "bare": None, "near": None},
}
MUSE_MODEL = re.compile(r"\bmuse[\s\-]+(?:spark|wonder|glimmer)\b", IC)


def folded(phrase):
    parts = [re.escape(p) for p in re.split(r"[\s\-_]+", phrase)]
    return re.compile(r"\b" + r"[\s\-_]*".join(parts) + r"\b", IC)


def classify(agent, text):
    a = AGENTS[agent]
    if any(folded(al).search(text) for al in a["aliases"]):
        return "compound"
    if agent == "Muse" and MUSE_MODEL.search(text):
        return "muse-model"
    if a["bare"]:
        near = re.compile(a["near"], IC)
        for m in re.finditer(a["bare"], text):
            if near.search(text[max(0, m.start() - 200): m.end() + 200]):
                return "pair-context"
    return "unclear"


def strings_under(o, keys, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in keys and isinstance(v, str) and len(v) > 20:
                out.append(v)
            else:
                strings_under(v, keys, out)
    elif isinstance(o, list):
        for v in o:
            strings_under(v, keys, out)
    return out


def hn(c, q, phrase):
    query = f'"{q}"' if phrase else q
    total, texts = 0, []
    for tag in ("story", "comment"):
        r = c.get("https://hn.algolia.com/api/v1/search", params={
            "query": query, "tags": tag, "numericFilters": f"created_at_i>{SINCE}", "hitsPerPage": 20})
        if r.status_code != 200:
            return None, [], f"HTTP {r.status_code}"
        d = r.json()
        total += d.get("nbHits", 0)
        for h in d.get("hits", []):
            texts.append(" ".join(filter(None, [h.get("title"), h.get("story_text"), h.get("comment_text")])))
        time.sleep(0.4)
    return total, texts, None


def bluesky(c, q, phrase):
    r = c.get("https://api.bsky.app/xrpc/app.bsky.feed.searchPosts",
              params={"q": f'"{q}"' if phrase else q, "sort": "latest", "limit": 50})
    if r.status_code != 200:
        return None, [], f"HTTP {r.status_code}"
    posts = r.json().get("posts", [])
    return len(posts), [p.get("record", {}).get("text", "") for p in posts], None


def devto(c, q, phrase):
    r = c.get("https://dev.to/api/articles/search", params={"q": q, "per_page": 30, "page": 1})
    if r.status_code != 200:
        return None, [], f"HTTP {r.status_code}"
    arts = r.json() if isinstance(r.json(), list) else []
    return len(arts), [" ".join(filter(None, [a.get("title"), a.get("description")])) for a in arts], None


def reddit(c, q, phrase):
    r = c.get(f"https://{REDDIT_HOST}/getSearchPosts", params={"query": f'"{q}"' if phrase else q, "sort": "RELEVANCE"},
              headers={"x-rapidapi-key": REDDIT_KEY, "x-rapidapi-host": REDDIT_HOST})
    if r.status_code != 200:
        return None, [], f"HTTP {r.status_code}"
    body = r.json()
    (RAW / f"reddit_{q.replace(' ', '_')}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    texts = strings_under(body, {"title", "selftext"}, [])
    return len(texts), texts, None


def xsearch(c, q, phrase):
    r = c.get(f"https://{X_HOST}/search-v2", params={"query": f'"{q}"' if phrase else q, "type": "Latest", "count": 20},
              headers={"x-rapidapi-key": X_KEY, "x-rapidapi-host": X_HOST})
    if r.status_code != 200:
        return None, [], f"HTTP {r.status_code}"
    body = r.json()
    (RAW / f"x_{q.replace(' ', '_')}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    texts = strings_under(body, {"full_text"}, [])
    return len(texts), texts, None


PLATFORMS = {"hackernews": hn, "bluesky": bluesky, "devto": devto, "reddit": reddit, "x": xsearch}
out = []
with httpx.Client(headers={"User-Agent": UA}, timeout=45) as c:
    for agent, a in AGENTS.items():
        for q, phrase in [(al, True) for al in a["aliases"]] + [(p, False) for p in a["pairs"]]:
            for plat, fn in PLATFORMS.items():
                try:
                    total, texts, err = fn(c, q, phrase)
                except Exception as e:  # noqa: BLE001
                    total, texts, err = None, [], f"{type(e).__name__}"
                counts = {"compound": 0, "pair-context": 0, "muse-model": 0, "unclear": 0}
                for t in texts:
                    counts[classify(agent, t)] += 1
                row = {"agent": agent, "query": q, "kind": "alias" if phrase else "pair", "platform": plat,
                       "reported": total, "sampled": len(texts), **counts, "error": err}
                out.append(row)
                print(f"{agent:13} {q:16} {row['kind']:5} {plat:10} reported={str(total):>6} sampled={len(texts):>3} "
                      f"compound={counts['compound']:>3} pair={counts['pair-context']:>3} model={counts['muse-model']:>3} "
                      f"unclear={counts['unclear']:>3} {err or ''}")
                time.sleep(1.0 if plat in ("reddit", "x") else 0.3)
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
