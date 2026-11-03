# ruff: noqa: E501 - long regex patterns are kept whole so they can be read and checked.
"""Read-only: is there enough "moved from model A to model B" in our corpus for a
monthly Field Index? (2026-11-03)

Population: documents behind at least one published (not declined) board_entry.
Two texts per document: its published quotes (every document), and its stored
post text where this machine can read it (raw_blob or the local raw store).

A SWITCH SENTENCE = one sentence with a switching verb AND at least two distinct
model names from a fixed list. A word match, not a reading of meaning (rule 7):
it counts candidates, and a sample is printed to judge how many are real.
"""
import json
import re
import zlib
from collections import Counter
from pathlib import Path

import psycopg

env = Path(r".env").read_text(encoding="utf-8")
dsn = re.search(r"^RAILWAY_DATABASE_URL=(.+)$", env, re.M).group(1).strip().strip('"')
dsn += ("&" if "?" in dsn else "?") + "options=-c%20default_transaction_read_only%3Don"

VERB = re.compile(
    r"\b(switch(ed|ing)?( back)? (from|to)|moved (over )?(from|to)|went back to|going back to|"
    r"replac(ed|ing) \S+( \S+)? with|migrat(ed|ing) (from|to)|dropped \S+( \S+)? for|"
    r"ditched|instead of|swapped)\b", re.I)
# Model names as people write them: families and the in-world product names.
NAMES = ["gpt", "claude", "opus", "sonnet", "haiku", "fable", "gemini", "grok", "deepseek",
         "qwen", "kimi", "glm", "minimax", "llama", "mistral", "codex", "sol", "luna", "astra",
         "terra", "argon", "gemma", "nemotron", "devstral", "muse"]
NAME_RX = re.compile(r"\b(" + "|".join(NAMES) + r")\b", re.I)
SENT = re.compile(r"(?<=[.!?\n])\s+")


def text_of(raw: bytes) -> str:
    try:
        s = zlib.decompress(raw).decode("utf-8", "replace")
    except zlib.error:
        s = raw.decode("utf-8", "replace")
    try:
        obj = json.loads(s)
    except ValueError:
        return s
    parts = []

    def walk(o):
        if isinstance(o, str):
            if len(o) > 40 and " " in o:
                parts.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return "\n".join(parts)


def switch_sentences(t: str) -> list[tuple[str, list[str]]]:
    out = []
    for s in SENT.split(re.sub(r"<[^>]+>", " ", t)):
        if not VERB.search(s):
            continue
        names = list(dict.fromkeys(n.lower() for n in NAME_RX.findall(s)))
        if len(names) >= 2:
            out.append((re.sub(r"\s+", " ", s).strip()[:260], names))
    return out


with psycopg.connect(dsn) as c:
    docs = c.execute(
        "SELECT d.id, d.source, d.author_id, d.created_at, d.text_ref, "
        "       array_agg(DISTINCT be.quote) "
        "FROM board_entry be JOIN document d ON d.id = be.document_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined' GROUP BY 1, 2, 3, 4, 5").fetchall()
    refs = [r[4] for r in docs if r[4]]
    blobs = {}
    for i in range(0, len(refs), 500):
        for k, data in c.execute("SELECT key, data FROM raw_blob WHERE key = ANY(%s)", (refs[i:i + 500],)):
            blobs[k] = bytes(data)

readable = 0
hit_q, hit_t = set(), set()
people, by_source, by_month, pairs = set(), Counter(), Counter(), Counter()
samples = []
for doc_id, source, author, at, ref, quotes in docs:
    qs = switch_sentences("\n".join(q for q in quotes if q))
    raw = blobs.get(ref) if ref else None
    if raw is None and ref:
        local = Path(r"C:\Users\anooj\Model-Information-Board") / ref
        raw = local.read_bytes() if local.exists() else None
    ts = []
    if raw is not None:
        readable += 1
        ts = switch_sentences(text_of(raw))
    if qs:
        hit_q.add(doc_id)
    if ts:
        hit_t.add(doc_id)
    if qs or ts:
        if author:
            people.add(author)
        by_source[source] += 1
        by_month[at.strftime("%Y-%m") if at else "undated"] += 1
        for _, names in (qs or ts)[:1]:
            pairs[" / ".join(sorted(names[:2]))] += 1
        if len(samples) < 14 and (qs or ts):
            samples.append((source, at.date() if at else None, (qs or ts)[0][0]))

docs_n = len(docs)
any_hit = hit_q | hit_t
print(f"documents behind published evidence: {docs_n}; post text readable for {readable}")
print(f"switch sentence in a published QUOTE: {len(hit_q)} of {docs_n} documents")
print(f"switch sentence in the POST TEXT: {len(hit_t)} of {readable} readable documents")
print(f"either: {len(any_hit)} documents, {len(people)} distinct people")
print("by source:", dict(by_source.most_common()))
print("by month of the post:", dict(sorted(by_month.items())))
print("most common name pairs:", pairs.most_common(12))
print("\nsample sentences (to judge how many are real switches):")
for s, d, t in samples:
    print(f" [{s} {d}] {t}")
