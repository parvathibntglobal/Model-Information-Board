"""Read-only: the five pains from the web research, counted in OUR corpus.

Population: documents behind at least one published (not declined) board_entry,
by source. Text = the stored raw payload (zlib), searched whole. A count is
documents whose text matches a word pattern - collocation, not meaning (rule 7).
Snippets are for internal reading only; Reddit/X text is never published as
quotes (contract/publication.yaml)."""
import json
import re
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import psycopg

env = Path(r".env").read_text(encoding="utf-8")
dsn = re.search(r"^RAILWAY_DATABASE_URL=(.+)$", env, re.M).group(1).strip().strip('"')
dsn += ("&" if "?" in dsn else "?") + "options=-c%20default_transaction_read_only%3Don"

PAINS = {
    "1 overwhelm": r"too many models|model fatigue|can'?t keep up|hard to keep up|so many models|new model every|which model (should|to|do) (i |you )?(use|pick|choose)",
    "2 price vs real cost": r"per task|cost per|more tokens|token[- ]hungry|burn(s|ed|ing)? through|so chatty|too chatty|ate (my|all|through)|tokens? (usage|burn)",
    "3 not knowing / drift": r"nerf|got worse|gotten worse|dumber|lobotom|degraded|feels? different|silently (changed|swapped|quantiz)|quantized (it|the model)",
    "4 rationing": r"rate[- ]limit|usage limit|weekly limit|5[- ]?h(ou)?r (limit|window)|quota|hit (the|my|a) limit|ran out of (credits|tokens|quota)",
    "5 exhaustion": r"burn(ed|t)?[- ]?out|exhausted|exhausting|tired of|fatigue",
    "6 staying put": r"stick(ing)? with|stay(ing)? with|went back to|switched back|used to its|default model|not switching",
}
RX = {k: re.compile(v, re.I) for k, v in PAINS.items()}


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


with psycopg.connect(dsn) as c:
    rows = c.execute(
        "SELECT DISTINCT d.id, d.source, d.url, d.created_at::date, d.text_ref "
        "FROM board_entry be JOIN document d ON d.id = be.document_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined' AND d.text_ref IS NOT NULL").fetchall()
    per_source = Counter(r[1] for r in rows)
    hits = defaultdict(Counter)
    samples = defaultdict(list)
    missing = 0
    missing_by = Counter()
    refs = [r[4] for r in rows]
    blobs = {}
    for i in range(0, len(refs), 500):
        for k, data in c.execute("SELECT key, data FROM raw_blob WHERE key = ANY(%s)", (refs[i:i + 500],)):
            blobs[k] = bytes(data)
    # Fallback: the flattened thread text the extractor was given.
    flat = dict(c.execute(
        "SELECT d.id, tc.flattened_text_ref FROM document d "
        "JOIN thread_context tc ON tc.thread_root_id = d.thread_root_id "
        "WHERE d.id = ANY(%s) AND tc.flattened_text_ref IS NOT NULL",
        ([r[0] for r in rows],)).fetchall())
    frefs = list(set(flat.values()))
    for i in range(0, len(frefs), 500):
        for k, data in c.execute("SELECT key, data FROM raw_blob WHERE key = ANY(%s)", (frefs[i:i + 500],)):
            blobs[k] = bytes(data)
    for doc_id, source, url, day, ref in rows:
        raw = blobs.get(ref)
        if raw is None and doc_id in flat:
            raw = blobs.get(flat[doc_id])
            if raw is None:
                local = Path(r"C:\Users\anooj\Model-Information-Board") / flat[doc_id]
                if local.exists():
                    raw = local.read_bytes()
        if raw is None:
            local = Path(r"C:\Users\anooj\Model-Information-Board") / ref
            if local.exists():
                raw = local.read_bytes()
        if raw is None:
            missing_by[source] += 1
            missing += 1
            continue
        t = text_of(raw)
        for k, rx in RX.items():
            m = rx.search(t)
            if m:
                hits[k][source] += 1
                if source in ("reddit", "x", "hackernews") and len(samples[k]) < 4:
                    a, b = max(0, m.start() - 160), min(len(t), m.end() + 160)
                    samples[k].append((source, str(day), url, re.sub(r"\s+", " ", t[a:b])))

print(f"documents behind published evidence: {len(rows)} ({missing} without a stored text)")
print("by source:", dict(per_source.most_common()))
print("no stored text, by source:", dict(missing_by.most_common()))
for k in PAINS:
    tot = sum(hits[k].values())
    srcs = ", ".join(f"{s} {n}/{per_source[s]}" for s, n in hits[k].most_common(5))
    print(f"\n{k}: {tot} of {len(rows)} documents | {srcs}")
    for s, day, url, snip in samples[k]:
        print(f"   [{s} {day}] {url}\n     ...{snip}...")
