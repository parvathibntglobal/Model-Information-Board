"""How much agent discussion uses only the short name ("Muse", not "Meta Muse").

READ-ONLY, run 2026-11-09; output agent-short-names-2026-11-09.out.json.

Population: the same 10,578 flattened thread texts in the shared raw store as
agent-discussion-2026-11-09.py. Each thread that uses the bare capitalised word
is put in one of four groups:

    caught            it also uses a compound form, so the compound rule finds it
    model name only   every bare match is a model's name (Muse Spark, Wonder,
                      Glimmer; dots.llm, dots.ocr, dots-3)
    giveaway nearby   some bare match has a giveaway word within 200 characters
                      (Meta, WhatsApp, Instagram, Zuckerberg, agent, assistant /
                      OpenAI, ChatGPT, Altman / Claude, Anthropic): probably the
                      agent, and missed by the compound rule
    no giveaway       none of the above: other senses, or the agent unmarked

The giveaway test is ROUGH: a nearby "agent" or "Meta" does not prove the
agent is meant, and an unmarked mention can still be it. The third group is
an estimate of what the compound rule misses, not a count of agent threads.
No thread text is written out.

    READONLY_DATABASE_URL=... python docs/measurements/agent-short-names-2026-11-09.py OUT.json
"""
import json
import os
import re
import sys
import zlib
from collections import Counter

import psycopg

IC = re.IGNORECASE
SUF = r"(?:\s+(?:ai|agent|assistant|app|bot))"
CASES = {
    # name: (compound pattern, bare pattern, giveaway pattern, model-name pattern or None)
    "Muse": (re.compile(r"\bmeta(?:'s)?\s+muse\b|\bmuse" + SUF + r"\b|\bmuse\s+by\s+meta\b", IC),
             re.compile(r"\bMuse\b"),
             re.compile(r"\b(?:meta|whatsapp|instagram|zuckerberg|agent|assistant)\b", IC),
             re.compile(r"\bMuse\s+(?:Spark|Wonder|Glimmer)\b")),
    "Dots": (re.compile(r"\b(?:openai|chatgpt)(?:'s)?\s+dots\b|\bdots" + SUF + r"\b", IC),
             re.compile(r"\bDots\b"),
             re.compile(r"\b(?:openai|chatgpt|altman|agent|assistant)\b", IC),
             re.compile(r"\bdots[.\-]?(?:llm|ocr|\d)", IC)),
    "Duet": (re.compile(r"\bclaude\s+duet\b|\banthropic(?:'s)?\s+duet\b", IC),
             re.compile(r"\bDuet\b"),
             re.compile(r"\b(?:claude|anthropic|agent|assistant)\b", IC),
             None),
}
GROUPS = ("caught", "model name only", "giveaway nearby", "no giveaway")


def classify(text: str, compound, bare, near, model_name) -> str | None:
    if not bare.search(text):
        return None
    if compound.search(text):
        return "caught"
    hits = [m for m in bare.finditer(text)
            if not (model_name and model_name.match(text, m.start()))]
    if not hits:
        return "model name only"
    if any(near.search(text[max(0, m.start() - 200): m.end() + 200]) for m in hits):
        return "giveaway nearby"
    return "no giveaway"


def main(dsn: str) -> dict:
    res = {name: Counter() for name in CASES}
    with psycopg.connect(dsn + ("&" if "?" in dsn else "?")
                         + "options=-c%20default_transaction_read_only%3Don") as c:
        keys = {r[0] for r in c.execute(
            "SELECT flattened_text_ref FROM thread_context WHERE flattened_text_ref IS NOT NULL")}
        cur = c.cursor(name="short_names")
        cur.itersize = 500
        cur.execute("SELECT key, data FROM raw_blob WHERE key LIKE 'flattened/%'")
        for key, data in cur:
            if key not in keys:
                continue
            text = zlib.decompress(bytes(data)).decode("utf-8", "replace")
            for name, patterns in CASES.items():
                group = classify(text, *patterns)
                if group:
                    res[name][group] += 1
    return {name: {g: res[name][g] for g in GROUPS} for name in CASES}


if __name__ == "__main__":
    threads = main(os.environ["READONLY_DATABASE_URL"])
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        json.dump({"measured_on": "2026-11-09", "threads": threads}, f, indent=1)
