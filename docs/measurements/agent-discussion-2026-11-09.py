"""How much discussion of personal agents exists, in what we hold and on Hacker News.

READ-ONLY. Two parts, both run on 2026-11-09; the output is
agent-discussion-2026-11-09.out.json beside this file.

1. STORED THREADS. Every flattened thread text in the shared raw store
   (`raw_blob`, keys `flattened/`, zlib), joined to its thread_context and root
   document, is searched for each agent. Population: thread_context rows whose
   flattened text is in `raw_blob` - 10,578 of 15,405 on the day; the rest are
   held only on the machine that assembled them. These threads were collected
   by MODEL searches, so every mention here is incidental: nothing was searched
   for by agent name.

   Two patterns where an agent's name is an ordinary word (rule 10):
     precise  a compound form ("Meta Muse", "OpenAI Dots") - a lower bound;
     bare     the capitalised word alone - an upper bound, and noisy.

2. LIVE HACKER NEWS. Algolia's exact-phrase search, stories and comments
   created since 2026-08-01, one count per phrase.

   GitHub issue-search totals were also requested on the day and are kept in
   the output, but NOT used: "meta muse" returned 31,560, which reads as the
   two words matched separately, not the phrase (CLAUDE.md, rule 6's GitHub
   note).

Thread text is never written out: the output holds counts only, because some of
the text is Reddit or X content, which is never republished verbatim.

    READONLY_DATABASE_URL=... python docs/measurements/agent-discussion-2026-11-09.py OUT.json
"""
import json
import os
import re
import sys
import time
import zlib
from collections import Counter, defaultdict

import httpx
import psycopg

IC = re.IGNORECASE
SUF = r"(?:\s+(?:ai|agent|assistant|app|bot))"
AGENTS = {
    # name: (maker, precise pattern, bare pattern or None)
    "Muse": ("Meta", re.compile(r"\bmeta(?:'s)?\s+muse\b|\bmuse" + SUF + r"\b", IC),
             re.compile(r"\bMuse\b")),
    "Dots": ("OpenAI", re.compile(r"\b(?:openai|chatgpt)(?:'s)?\s+dots\b|\bdots" + SUF + r"\b", IC),
             re.compile(r"\bDots\b")),
    "Claude Duet": ("Anthropic", re.compile(r"\bclaude\s+duet\b|\banthropic(?:'s)?\s+duet\b", IC),
                    re.compile(r"\bDuet\b")),
    "Grok Bot": ("xAI / SpaceXAI", re.compile(r"\bgrok\s*bot\b", IC), None),
    "Gemini Spark": ("Google", re.compile(r"\bgemini\s+spark\b", IC), None),
    "Claude Cowork": ("Anthropic", re.compile(r"\bcowork\b", IC), None),
    "ChatGPT Agent": ("OpenAI", re.compile(r"\bchatgpt\s+agent\b", IC), None),
    "ChatGPT Work": ("OpenAI", re.compile(r"\bchatgpt\s+work\b", IC), None),
    "Perplexity Comet": ("Perplexity",
                         re.compile(r"\bperplexity\s+comet\b"
                                    r"|\bcomet\s+(?:browser|assistant|agent)\b", IC),
                         re.compile(r"\bComet\b")),
    "Manus": ("Manus", re.compile(r"\bmanus\b", IC), None),
    "OpenClaw": ("open source", re.compile(r"\bopen\s?claw\b", IC), None),
    "NanoClaw / ZeroClaw": ("open source", re.compile(r"\b(?:nano|zero)claw\b", IC), None),
    "Hermes Agent": ("Nous Research", re.compile(r"\bhermes\s+agent\b", IC), None),
    "Lindy": ("Lindy", re.compile(r"\blindy(?:\.ai)?" + SUF + r"?\b", IC), None),
    "Letta": ("Letta", re.compile(r"\bletta\b", IC), None),
    "Doubao": ("ByteDance", re.compile(r"\bdoubao\b", IC), None),
    "Vellum": ("Vellum", re.compile(r"\bvellum\b", IC), None),
    "Poke": ("The Interaction Company", re.compile(r"\bpoke(?:\.com)?" + SUF + r"\b", IC), None),
    "Siri AI": ("Apple", re.compile(r"\bsiri\s+ai\b|\bnew\s+siri\b", IC), None),
    "Hark": ("", re.compile(r"\bhark" + SUF + r"\b", IC), None),
    "Instinct": ("", re.compile(r"\binstinct" + SUF + r"\b", IC), None),
    "Tomo": ("", re.compile(r"\btomo" + SUF + r"\b", IC), None),
    "Pally": ("", re.compile(r"\bpally" + SUF + r"\b", IC), None),
    "Zapia": ("", re.compile(r"\bzapia\b", IC), None),
    "Joshu": ("", re.compile(r"\bjoshu\b", IC), None),
}
HN_SINCE = 1785542400  # 2026-08-01T00:00:00Z
HN_PHRASES = ["meta muse", "openai dots", "chatgpt dots", "claude duet", "grok bot", "gemini spark",
              "claude cowork", "chatgpt agent", "chatgpt work", "perplexity comet", "manus agent",
              "openclaw", "hermes agent", "lindy ai", "letta", "doubao", "poke ai", "siri ai"]
UA = "ModelInformationBoard/1.0 (+https://github.com/parvathibntglobal/Model-Information-Board)"


def stored_threads(dsn: str) -> dict:
    with psycopg.connect(dsn + ("&" if "?" in dsn else "?")
                         + "options=-c%20default_transaction_read_only%3Don") as c:
        meta = {r[0]: (r[1], r[2]) for r in c.execute(
            "SELECT tc.flattened_text_ref, d.source, d.created_at::date FROM thread_context tc "
            "JOIN document d ON d.id = tc.thread_root_id WHERE tc.flattened_text_ref IS NOT NULL")}
        precise, bare, recent = defaultdict(Counter), Counter(), Counter()
        scanned = unreadable = 0
        cur = c.cursor(name="flat_scan")
        cur.itersize = 500
        cur.execute("SELECT key, data FROM raw_blob WHERE key LIKE 'flattened/%'")
        for key, data in cur:
            if key not in meta:
                continue
            try:
                text = zlib.decompress(bytes(data)).decode("utf-8", "replace")
            except zlib.error:
                unreadable += 1
                continue
            scanned += 1
            src, created = meta[key]
            for name, (_maker, pat, bare_pat) in AGENTS.items():
                if pat.search(text):
                    precise[name][src] += 1
                    if created and str(created) >= "2026-08-01":
                        recent[name] += 1
                if bare_pat and bare_pat.search(text):
                    bare[name] += 1
    return {"scanned": scanned, "unreadable": unreadable, "agents": {
        name: {"maker": maker, "precise_threads": sum(precise[name].values()),
               "since_2026_08_01": recent[name], "bare_threads": bare[name] if bp else None,
               "by_source": dict(precise[name])}
        for name, (maker, _p, bp) in AGENTS.items()}}


def live_hn() -> dict:
    out = {}
    with httpx.Client(headers={"User-Agent": UA}, timeout=30) as c:
        for p in HN_PHRASES:
            row = {}
            for tag in ("story", "comment"):
                r = c.get("https://hn.algolia.com/api/v1/search", params={
                    "query": f'"{p}"', "tags": tag,
                    "numericFilters": f"created_at_i>{HN_SINCE}", "hitsPerPage": 0})
                row[f"hn_{tag}s"] = r.json().get("nbHits") if r.status_code == 200 else None
                time.sleep(0.5)
            out[p] = row
    return out


if __name__ == "__main__":
    result = {"stored_threads": stored_threads(os.environ["READONLY_DATABASE_URL"]),
              "live": {"phrases": live_hn()}}
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
