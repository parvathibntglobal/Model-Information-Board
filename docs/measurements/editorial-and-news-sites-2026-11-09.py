# ruff: noqa: E501
"""Editorial tech sites like InfoQ: which carry REVIEWS (evidence) and which carry daily NEWS.

READ-ONLY AND STORES NOTHING: no raw store, no database write, no article kept.

    DATABASE_URL=<any registry database> python docs/measurements/editorial-and-news-sites-2026-11-09.py OUT.json

The registry is read with `default_transaction_read_only=on` and used only to resolve names.

PER SITE, ON THE DAY IT RUNS
  robots          robots.txt status; `robots_allows_us_*` from urllib.robotparser for our
                  User-Agent, on the feed URL and on a sample article path.
  feed            the first candidate URL that parses as RSS/Atom; its `generator`.
  items           what the feed served that day. EVERY RATE BELOW IS OVER THAT WINDOW,
                  never over the publication.
  feed_full_text  items whose feed body is >= 1,500 characters after markup is removed.
  bylines         items carrying an author in the feed, and how many distinct.
  titles_with_release_verb   announces / launches / unveils / releases / introduces /
                  now available / rolls out / debuts, in the title. A cue for release
                  reporting, not a verdict.
  ai_items        items whose title or summary matches an AI word list (AI, LLM, model,
                  agent, chatbot, a model family, Copilot, Codex).

SHAPE, ON UP TO 10 AI ITEMS (the first 10 in feed order)
  Text is the feed body when it is full, otherwise ONE read of the article page
  (trafilatura). `article_chars` is the median length read; `paywall_marker_pages` counts
  pages carrying a subscribe/paywall phrase.
  articles_naming_a_model    articles with at least one sentence naming a REGISTRY model
                             (RegistrySurfaceFinder over registry_population: versioned
                             names; a bare family or a product name counts as nothing).
  articles_naming_a_family   articles naming one of 13 families, case-sensitive whole word
                             (the measure the seated newsletter rows use).
  naming_sentences / naming_exactly_one   the sentence-level measure of
                             local-attributability-2026-09-22.py: of sentences naming a
                             registry model, how many name exactly one owner.
  eval_cue_sentences         naming sentences carrying a first-hand or evaluative word.
                             A cue count, never a verdict.

THE BROADER SCOPE (anooj, 2026-11-09: "cover everything coming up daily related to LLM
models"). Registry naming undercounts a site that writes about agents and tools, so:
  tool_items      over ALL feed items' title + summary (no extra request), items naming one
                  of TOOLS below, case-sensitive whole word, and which names.
TOOLS is a list chosen for this probe on 2026-11-09, not a registry: coding tools, agent
products (the nine on #610), protocols and serving tools. `Muse`, `Dots`, `Duet` and
`Cursor` are also English words; case-sensitive matching narrows that and does not remove
it, so those counts are a ceiling.

LIMITS: one day, at most 10 articles per site; §3a of contract/sources.yaml notes that a
ten-entry sample overstates naming on any feed deeper than ten entries. Regex sentence split.
Sites that refuse this client (429, a non-feed answer, 405 on pages) are recorded as refusing,
and read no further.
"""
import json
import os
import re
import statistics
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse

import httpx
import psycopg
import trafilatura

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from collect.registry.aliases import normalize  # noqa: E402
from collect.surface_resolver import RegistrySurfaceFinder  # noqa: E402
from collect.triage.store import registry_population  # noqa: E402

UA = "ModelInformationBoard/1.0 (+https://github.com/parvathibntglobal/Model-Information-Board)"
SAMPLE = 10
SITES = {
    "Every (Vibe Check)": ["https://every.to/vibe-check/feed"],
    "InfoQ": ["https://feed.infoq.com/ai-ml-data-eng/"],
    "The New Stack": ["https://thenewstack.io/feed/"],
    "IEEE Spectrum": ["https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss"],
    "Ars Technica": ["https://arstechnica.com/ai/feed/"],
    "VentureBeat": ["https://venturebeat.com/category/ai/feed/"],
    "The Register": ["https://www.theregister.com/software/ai_ml/headlines.atom"],
    "DevClass": ["https://devclass.com/feed/"],
    "HackerNoon": ["https://hackernoon.com/feed"],
    "TechCrunch": ["https://techcrunch.com/category/artificial-intelligence/feed/"],
    "InfoWorld": ["https://www.infoworld.com/artificial-intelligence/feed/"],
    "SD Times": ["https://sdtimes.com/feed/"],
    "MIT Technology Review": ["https://www.technologyreview.com/topic/artificial-intelligence/feed/"],
    "Tom's Guide": ["https://www.tomsguide.com/feeds/tag/ai"],
    "ZDNET": ["https://www.zdnet.com/topic/artificial-intelligence/rss.xml"],
    "The Verge": ["https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"],
    "The Pragmatic Engineer": ["https://newsletter.pragmaticengineer.com/feed"],
}
TOOLS = ["Claude Code", "Codex", "Cursor", "Copilot", "Kiro", "Devin", "Windsurf", "Replit", "Lovable",
         "MCP", "Model Context Protocol", "Duet", "Dots", "Muse", "OpenClaw", "Hermes Agent", "Cowork",
         "ChatGPT Work", "Gemini Spark", "Grok Bot", "LangChain", "LlamaIndex", "vLLM", "Ollama",
         "llama.cpp", "Hugging Face"]
TOOL_RE = re.compile(r"(?<![\w.])(" + "|".join(re.escape(t) for t in sorted(TOOLS, key=len, reverse=True)) + r")(?![\w])")
FAM = re.compile(r"\b(GPT|Claude|Gemini|Llama|Qwen|DeepSeek|Mistral|Grok|Kimi|GLM|MiniMax|Gemma|Phi)\b")
AI = re.compile(r"\b(AI|LLM|model|GPT|Claude|Gemini|Llama|Qwen|DeepSeek|Mistral|Grok|Kimi|agent|chatbot|Copilot|Codex)\b")
EVAL = re.compile(r"\b(tested|testing|in my (?:test|experience|use)|I (?:tried|used|asked|found)|we (?:tried|found|tested)|"
                  r"fail(?:s|ed)?|struggl\w+|better than|worse|outperform\w*|impressive|disappoint\w*|hallucinat\w*|"
                  r"weak(?:er|ness)?|strong(?:er)?|faster|slower|accurate|inaccurate|mistake\w*|wrong|reliable|unreliable|"
                  r"excellent|poor(?:ly)?|surpris\w+|frustrat\w+)\b", re.I)
PR = re.compile(r"\b(announc\w+|launch\w*|unveil\w*|releas\w+|introduc\w+|now available|rolls? out|debuts?)\b", re.I)
PAYWALL = re.compile(r"(?i)\b(subscribe to (?:read|continue)|paid subscribers|members only|this post is for paid|upgrade to read|create a free account to continue)\b")
C = "{http://purl.org/rss/1.0/modules/content/}encoded"
DC = "{http://purl.org/dc/elements/1.1/}creator"
A = "{http://www.w3.org/2005/Atom}"
SENT = re.compile(r"(?<=[.!?])\s+|\n+")
TAG = re.compile(r"<[^>]+>")


def get(client, url):
    try:
        return client.get(url, timeout=25, follow_redirects=True)
    except httpx.HTTPError as e:
        return e


def status(r):
    return str(r.status_code) if isinstance(r, httpx.Response) else type(r).__name__


def text_of(html):
    return re.sub(r"\s+", " ", TAG.sub(" ", html or "")).strip()


def parse_feed(body):
    root = ET.fromstring(body)
    items = []
    if root.tag == f"{A}feed":
        gen = (root.findtext(f"{A}generator") or "").strip()
        for e in root.findall(f"{A}entry"):
            link = next((li.get("href") for li in e.findall(f"{A}link") if li.get("rel", "alternate") == "alternate"), None)
            items.append({"title": (e.findtext(f"{A}title") or "").strip(), "link": link,
                          "author": (e.findtext(f"{A}author/{A}name") or "").strip(),
                          "full": e.findtext(f"{A}content") or "", "summary": e.findtext(f"{A}summary") or ""})
    else:
        ch = root.find("channel")
        gen = (ch.findtext("generator") or "").strip() if ch is not None else ""
        for e in root.iter("item"):
            items.append({"title": (e.findtext("title") or "").strip(), "link": (e.findtext("link") or "").strip(),
                          "author": (e.findtext(DC) or e.findtext("author") or "").strip(),
                          "full": e.findtext(C) or "", "summary": e.findtext("description") or ""})
    return gen, items


def main(out_path):
    dsn = os.environ["DATABASE_URL"]
    dsn += ("&" if "?" in dsn else "?") + "options=-c%20default_transaction_read_only%3Don"
    with psycopg.connect(dsn, connect_timeout=20) as conn:
        pop = registry_population(conn)
    find = RegistrySurfaceFinder(pop)
    owners_by_key = {}
    for s, o in pop.owners.items():
        owners_by_key.setdefault(normalize(s), set()).update(o)

    def owners(sentence):
        return {o for s in find(sentence) for o in owners_by_key.get(normalize(s), ())}

    out = {"measured_on": time.strftime("%Y-%m-%d"), "population_fingerprint": pop.fingerprint,
           "sample_per_site": SAMPLE, "tools_list": TOOLS, "sites": {}}
    with httpx.Client(headers={"User-Agent": UA}) as client:
        for name, feeds in SITES.items():
            row = {"feed_candidates": feeds}
            host = urlparse(feeds[0]).netloc
            site_host = "www.infoq.com" if host == "feed.infoq.com" else host
            r = get(client, f"https://{site_host}/robots.txt")
            row["robots"] = status(r)
            if isinstance(r, httpx.Response) and r.status_code == 200:
                rp = robotparser.RobotFileParser()
                rp.parse(r.text.splitlines())
                row["robots_allows_us_feed"] = rp.can_fetch(UA, feeds[0])
                row["robots_allows_us_articles"] = rp.can_fetch(UA, f"https://{site_host}/some-article/")
            gen, items, used = "", [], None
            for f in feeds:
                time.sleep(1)
                fr = get(client, f)
                if not isinstance(fr, httpx.Response) or fr.status_code != 200:
                    row.setdefault("feed_refusals", []).append(f"{f} -> {status(fr)}")
                    continue
                try:
                    gen, items = parse_feed(fr.content)
                    used = f
                    break
                except ET.ParseError:
                    row.setdefault("feed_refusals", []).append(f"{f} -> 200 but not a feed")
            row.update({"feed": used, "generator": gen or None, "items": len(items)})
            if not items:
                out["sites"][name] = row
                print(name, json.dumps(row), flush=True)
                continue
            full_lens = sorted(len(text_of(i["full"])) for i in items)
            authors = [i["author"] for i in items if i["author"]]
            tools = Counter()
            tool_items = 0
            for i in items:
                found = set(TOOL_RE.findall(i["title"] + " " + text_of(i["summary"]) + " " + text_of(i["full"])[:600]))
                tool_items += bool(found)
                tools.update(found)
            ai_items = [i for i in items if AI.search(i["title"] + " " + text_of(i["summary"])[:400])]
            row.update({
                "feed_full_text": sum(1 for x in full_lens if x >= 1500),
                "items_with_byline": len(authors), "distinct_bylines": len(set(authors)),
                "titles_with_release_verb": sum(1 for i in items if PR.search(i["title"])),
                "ai_items": len(ai_items), "tool_items": tool_items, "tools_named": dict(tools.most_common()),
            })
            naming = one = ev = docs_naming = fam_docs = sampled = paywalled = 0
            lengths, page_status = [], Counter()
            widest = Counter()
            for i in ai_items[:SAMPLE]:
                text = text_of(i["full"])
                if len(text) < 1500 and i["link"]:
                    time.sleep(1)
                    pr = get(client, i["link"])
                    page_status[status(pr)] += 1
                    if isinstance(pr, httpx.Response) and pr.status_code == 200:
                        text = trafilatura.extract(pr.text) or ""
                        paywalled += bool(PAYWALL.search(pr.text))
                if len(text) < 300:
                    continue
                sampled += 1
                lengths.append(len(text))
                fam_docs += bool(FAM.search(text))
                here = 0
                for s in SENT.split(text):
                    s = s.strip()
                    if len(s) < 15:
                        continue
                    o = owners(s)
                    if not o:
                        continue
                    naming += 1
                    here += 1
                    one += len(o) == 1
                    if len(o) > 1:
                        widest[len(o)] += 1
                    ev += bool(EVAL.search(s))
                docs_naming += bool(here)
            row.update({
                "article_pages_read": dict(page_status), "paywall_marker_pages": paywalled,
                "articles_sampled": sampled,
                "article_chars_median": int(statistics.median(lengths)) if lengths else None,
                "articles_naming_a_family": fam_docs, "articles_naming_a_model": docs_naming,
                "naming_sentences": naming, "naming_exactly_one": one,
                "multi_model_widths": dict(widest), "eval_cue_sentences": ev,
                "sample_titles": [i["title"][:100] for i in ai_items[:SAMPLE]],
            })
            out["sites"][name] = row
            print(name, json.dumps({k: v for k, v in row.items() if k not in ("sample_titles", "feed_candidates")}), flush=True)
    Path(out_path).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
