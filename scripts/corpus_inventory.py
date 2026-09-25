"""What we collected, and how we found it. One markdown file, read not queried.

Usage:
    py -3 scripts/corpus_inventory.py --out docs/corpus-inventory.md

WHO THIS IS FOR
---------------
Somebody at a presentation asking *"what did you actually collect, and how did
you find it"*, with nobody querying a database live. So: one row per document,
grouped by platform, with enough text to recognise each one and the triage
verdict beside it.

THREE THINGS IT REFUSES TO DO, EACH BECAUSE THE HONEST ANSWER IS SHORTER
-----------------------------------------------------------------------

**1. It does not present the three platforms as one retrieval story.** GitHub and
Reddit are QUERY-RETRIEVED: a term list produced them, and "we searched for these
and got these" is true. Blogs are FEED-FETCHED and unfiltered — every article in
the feed is taken, no query decided anything. A single undifferentiated table
invites *"so which search found this blog post?"*, which has no answer.

**2. It does not reconstruct the retrieval path.** `document` has no
`harvest_run` reference and no query column; nothing in the schema joins a
document to the query that found it. `harvest_run` holds `query_key` and 153
rows, and there is no key between them. So the per-document query is recorded as
**not recoverable** rather than inferred from timestamps or term overlap. A
plausible provenance is worse than an absent one.

**3. It does not print usernames, because we do not store them.** `author` holds
`external_id` (`t2_…`, a numeric GitHub id, or a feed id) and `handle_hash`. The
handle is deliberately never stored — data minimisation — so "author" in this
file is a stable opaque identity, not a name. For Reddit that is also an
unresolved Developer Terms 5.2 question at publication time.

TRIAGE VERDICTS ARE COMPUTED HERE, NOT READ
-------------------------------------------
`document.triage_verdict` is NULL on all 254 rows because **nothing in the
repository writes it** — the stage runs and its output has nowhere to go. So this
file computes the verdict at render time and says it did. A row whose text cannot
be read from the raw store gets `unavailable`, never `dropped`: a gate that could
not run has not rejected anything.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT =Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from collect.db import connect  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.rawstore_reader import RawStoreReader, ReadOutcome  # noqa: E402
from collect.registry.aliases import alias_rows  # noqa: E402
from collect.registry.seed import seed_models  # noqa: E402
from collect.triage.entity import build_population  # noqa: E402
from collect.triage.gates import Document, Verdict, triage  # noqa: E402

#: How each platform's documents came to be here. The distinction the file exists
#: to keep visible; see the module docstring.
RETRIEVAL = {
    "github": ("query-retrieved",
               "GitHub Search API. A term list from `contract/queries.yaml` "
               "produced these; the sieve then rejected what did not carry a "
               "subject, topic and signal term."),
    "reddit": ("query-retrieved, then thread-expanded",
               "Reddit search via RapidAPI found the ROOT POST. Its comments "
               "were then fetched wholesale by `getPostComments` — so the "
               "comments were not themselves retrieved by any query, and a "
               "term list does not describe them."),
    "blog": ("feed-fetched, UNFILTERED",
             "RSS. Every article in the feed is taken and no query decided "
             "anything, so nothing was searched for and nothing was excluded "
             "at retrieval. This is the only positive-evidence channel."),
}


def population():
    conn = connect()
    rows = conn.execute(
        "SELECT mv.id, ma.surface FROM model_version mv "
        "LEFT JOIN model_alias ma ON ma.model_version_id = mv.id"
    ).fetchall()
    conn.close()
    declared: list[str] = []
    for model in seed_models():
        for row in alias_rows(model):
            declared.append(row.surface)
            declared.extend(row.variants)
    return build_population([(r[0], r[1]) for r in rows], declared)


def first_line(text: str, limit: int = 110) -> str:
    """Enough to recognise the document. A title or opening, never the body.

    Prefers a line the flattener marked as a title with `**…**`, because a blog
    article's first line is the feed's own section header — *"18th August 2026 -
    Link Blog"* — which recognises the feed rather than the document.
    """
    candidates = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("#").strip()
        if line:
            candidates.append(line)
        if len(candidates) >= 5:
            break
    if not candidates:
        return ""
    titled = next((c for c in candidates if c.startswith("**")), None)
    line = (titled or candidates[0]).replace("**", "").strip()
    return (line[: limit - 1] + "…") if len(line) > limit else line


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "corpus-inventory.md")
    args = ap.parse_args(argv)

    # THE DATABASE NAME, NEVER THE HOST. This wrote `host:port/db` into a
    # committed doc, so regenerating it re-published the staging address after
    # the tree had been redacted. The name says which database; where it lives
    # is not this file's to publish.
    parts = urlsplit(os.environ.get("DATABASE_URL", ""))
    local = parts.hostname in ("localhost", "127.0.0.1", "::1")
    where = "this machine" if local else "a remote host"
    host = f"{parts.path.strip('/')} on {where}" if parts.path.strip("/") else "(unset)"

    conn = connect()
    rows = conn.execute(
        "SELECT d.id, d.source, d.external_id, d.url, d.created_at, d.text_ref, "
        "       a.external_id, d.triage_verdict, d.status "
        "FROM document d LEFT JOIN author a ON a.id = d.author_id "
        "ORDER BY d.source, d.created_at NULLS LAST, d.id"
    ).fetchall()
    # THE FLATTENED TEXT, NOT THE RAW BYTES. `document.text_ref` for a blog
    # points at the original HTTP response, so its first line is `<!DOCTYPE
    # html>` and triage would run the entity gate over markup. The first draft
    # of this script did exactly that and reported a blog survival figure
    # computed on HTML. `thread_context.flattened_text_ref` is what the
    # extractor reads and therefore what triage should be judged on.
    # ONLY FOR SINGLE-MEMBER CONTEXTS, and the qualifier is the whole point.
    # A thread context's flattened text is the WHOLE THREAD — root plus selected
    # children. Mapping it onto each member document makes a comment inherit the
    # root's text, so the entity gate sees a model name the comment never wrote
    # and the comment is kept. Measured while writing this: doing it unqualified
    # moved reddit from 18 kept to 20, an inflation of exactly the kind this file
    # exists to avoid. A blog or GitHub context has one member, so there the
    # flattened text IS the document's text.
    flat_ref: dict[str, str] = {}
    for members, ref in conn.execute(
        "SELECT member_document_ids, flattened_text_ref FROM thread_context "
        "WHERE flattened_text_ref IS NOT NULL"
    ).fetchall():
        members = list(members or ())
        if len(members) == 1:
            flat_ref.setdefault(members[0], ref)
    total_in_db = conn.execute("SELECT count(*) FROM document").fetchone()[0]
    stored_verdicts = conn.execute(
        "SELECT count(triage_verdict) FROM document"
    ).fetchone()[0]
    harvest_runs = conn.execute("SELECT count(*) FROM harvest_run").fetchone()[0]
    conn.close()

    store = RawStoreReader(RawStore())
    pop = population()

    by_source: dict[str, list[dict]] = {}
    tallies: dict[str, Counter] = {}
    for doc_id, source, external, url, created, ref, author, stored_v, status in rows:
        text = None
        source_of_text = None
        for candidate, label in ((flat_ref.get(doc_id), "flattened"), (ref, "raw")):
            if not candidate:
                continue
            try:
                got = store.resolve(candidate)
            except ValueError:
                continue
            if got.outcome is ReadOutcome.FOUND:
                text, source_of_text = got.text, label
                break

        if text is None:
            verdict, reasons = "unavailable", ("payload not in this raw store",)
        else:
            result = triage(
                Document(text=text, created_at=created.date() if created else None,
                         author=author, body=text),
                population=pop,
            )
            verdict = "kept" if result.verdict is Verdict.KEPT else "dropped"
            reasons = result.reasons

        by_source.setdefault(source, []).append({
            "id": doc_id,
            "external_id": external,
            "url": url,
            "created": created.date().isoformat() if created else None,
            "author": author,
            "recognise": first_line(text) if text else None,
            "verdict": verdict,
            "reasons": list(reasons),
            "status": status,
            "stored_verdict": stored_v,
            "text_from": source_of_text,
        })
        tallies.setdefault(source, Counter())[verdict] += 1

    rendered = sum(len(v) for v in by_source.values())
    lines: list[str] = []
    w = lines.append

    w("# Corpus inventory")
    w("")
    w("**What we collected, and how we found it.** One row per document, grouped "
      "by platform. Nothing here needs a database to read.")
    w("")
    w(f"*Generated {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')} "
      f"from `{host}`*")
    w("")
    w("---")
    w("")
    w("## Counts")
    w("")
    w("| platform | documents | kept | dropped | text unavailable |")
    w("|---|---:|---:|---:|---:|")
    for source in sorted(by_source):
        t = tallies[source]
        w(f"| {source} | {len(by_source[source])} | {t['kept']} | "
          f"{t['dropped']} | {t['unavailable']} |")
    grand = Counter()
    for t in tallies.values():
        grand.update(t)
    w(f"| **total** | **{rendered}** | **{grand['kept']}** | "
      f"**{grand['dropped']}** | **{grand['unavailable']}** |")
    w("")
    if rendered == total_in_db:
        w(f"**{rendered} of {total_in_db} documents in the database are in this "
          f"file.** Nothing is omitted.")
    else:
        w(f"⚠ **{rendered} rendered against {total_in_db} in the database — "
          f"{total_in_db - rendered} MISSING FROM THIS FILE.** That is a defect "
          f"in this script, not a fact about the corpus.")
    w("")

    w("## Two things to read before the tables")
    w("")
    w("**1. The three platforms did not arrive the same way, and only two were "
      "searched for.**")
    w("")
    w("| platform | how it arrived | |")
    w("|---|---|---|")
    for source in sorted(by_source):
        kind, detail = RETRIEVAL.get(source, ("unknown", "not recorded"))
        w(f"| {source} | **{kind}** | {detail} |")
    w("")
    w('So *"we searched for these terms and got these documents"* is true of '
      "GitHub, half-true of Reddit — the root posts were searched for and the "
      "comments were not — and **false of blogs**, where the feed is taken whole "
      "and no query decided anything.")
    w("")
    w("**2. The query that found any given document is NOT RECOVERABLE, and this "
      "file does not guess it.**")
    w("")
    w("```")
    w("document       has no harvest_run reference and no query column")
    w(f"harvest_run    {harvest_runs} rows, each with a query_key")
    w("between them   nothing")
    w("```")
    w("")
    w("Term overlap or fetch timestamps could produce a plausible mapping. They "
      "are not recorded here: a provenance that looks derived and is inferred is "
      "worse than an absent one, because only the second invites the question.")
    w("")

    w("## Two limits of the columns below")
    w("")
    w(f"**Triage verdicts are computed by this script, not read from the "
      f"database.** `document.triage_verdict` is NULL on **{total_in_db - stored_verdicts} "
      f"of {total_in_db}** rows — nothing in the repository writes it. The verdicts "
      "here are from `collect/triage/gates.py` at render time, against population "
      f"`{pop.fingerprint}`. `unavailable` means the payload could not be read "
      "and therefore **no gate ran** — it is not a rejection.")
    w("")
    w("**\"Author\" is a stable opaque id, not a name.** Handles are deliberately "
      "never stored (data minimisation), so `t2_…`, a numeric GitHub id, or a "
      "feed id is all there is. Recovering a display name means re-reading the "
      "raw payload at render time, and for Reddit that is an open Developer Terms "
      "5.2 question rather than a lookup.")
    w("")

    for source in sorted(by_source):
        docs = by_source[source]
        kind, detail = RETRIEVAL.get(source, ("unknown", ""))
        w("---")
        w("")
        w(f"## {source} — {len(docs)} documents")
        w("")
        w(f"*{kind}. {detail}*")
        w("")
        t = tallies[source]
        w(f"Triage at render time: **{t['kept']} kept, {t['dropped']} dropped, "
          f"{t['unavailable']} text unavailable.**")
        stub = sum(1 for d in docs if d["url"] and "/x/" in d["url"])
        if stub:
            w("")
            w(f"⚠ **{stub} of these carry a placeholder URL** (`/r/…/x/`) written "
              f"by `scripts/export_thread_contexts.py`, so they link to nothing. "
              f"The documents are real; the URL is a stub and is marked as one "
              f"rather than rendered as a working link.")
        w("")
        w("| # | date | author | recognise it by | triage | url |")
        w("|---:|---|---|---|---|---|")
        for i, d in enumerate(docs, 1):
            rec = (d["recognise"] or "*(text not readable here)*").replace("|", "\\|")
            verdict = d["verdict"]
            if verdict == "dropped" and d["reasons"]:
                verdict = f"dropped — {', '.join(d['reasons'])}"
            url = f"[link]({d['url']})" if d["url"] else "—"
            if d["url"] and "/x/" in d["url"]:
                # A PLACEHOLDER, NOT A LINK. `export_thread_contexts.py` passed
                # a stub thread url, so these rows point at nothing. Marked
                # rather than rendered as a working link, because a dead link in
                # an inventory is worse than an admitted gap.
                url = "⚠ placeholder url"
            w(f"| {i} | {d['created'] or '—'} | `{d['author'] or '—'}` | "
              f"{rec} | {verdict} | {url} |")
        w("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"DSN          {host}")
    print(f"documents    {rendered} rendered / {total_in_db} in the database")
    for source in sorted(by_source):
        t = tallies[source]
        print(f"  {source:<8} {len(by_source[source]):>4}  kept={t['kept']:<4} "
              f"dropped={t['dropped']:<4} unavailable={t['unavailable']}")
    print(f"stored triage_verdicts  {stored_verdicts} of {total_in_db}")
    print(f"population              {pop.fingerprint}")
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
