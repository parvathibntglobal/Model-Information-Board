"""Which SHAPE of GitHub query yields per request. Retrieval only, no extraction.

WHAT IS ALREADY MEASURED AND IS NOT RE-DERIVED HERE

    capability vs model-name    ~3x on precision, pooled. CORRECTED 2026-08-31;
                                this line read "3.4% kept against 0.15% - 23x"
                                and both halves were wrong. The 3.4% is an order
                                of magnitude high - no slice of `harvest_run`
                                produces it, and the closest value is
                                avg(sieve_pass_rate) = 0.36%. Quote the POOLED
                                ratio, not the mean of per-run ratios: that is
                                the same mean-of-ratios error the extraction
                                cost model made once already.
                                docs/measurements/model-name-versus-capability-
                                retrieval.md carries the corrected reading and
                                has since it was written; this docstring is
                                where the stale copy survived.
    the diagnosis               signal fails, not topic: 2,239 candidates gave
                                63 topic hits and 3 signal hits
    structural qualifiers       `is:issue state:open` shrinks the reported corpus
                                3.65x and returns the IDENTICAL 100 ids in the
                                same order at max_pages = 1
    query productivity          88 of 591 queries have ever kept anything
    topic token                 43x spread. SEARCH/REPLACE and json_schema
                                produced 42% of all documents from 9% of
                                candidates; `extraction` and `boilerplate`
                                fetched 8,066 and kept ZERO
    alias form                  concatenated fetches NOTHING on 57.9% of queries

WHAT THIS TESTS. Four shapes nobody has issued, ordered by what the free
measurement predicts rather than by the order they were proposed:

    1  REPRO      alias + a repro artifact word (traceback, "steps to reproduce")
    2  SIGNAL     alias + a signal phrase, NO topic term ("returns empty")
    3  TITLE      alias in `in:title` only
    4  LABEL      alias + a label qualifier

1 and 2 go first because the topic-token measurement says the productive tokens
are LITERAL ARTIFACTS - `SEARCH/REPLACE`, `json_schema` - and the barren ones are
conceptual English - `extraction`, `boilerplate`. Repro words and signal phrases
are literal. 4 goes last because structural qualifiers already measured as doing
nothing at this depth; `label:` is a different qualifier from `is:`/`state:` so
it is not strictly covered, but it is the arm most likely to reproduce a known
null.

WHY UNIQUE DOCUMENTS PER SHAPE, NOT KEPT PER SHAPE. The hyphenated-versus-
concatenated result found 4 documents unique to one form, 48 to the other and
**0 to both** - disjoint sets. A shape that keeps less but keeps DIFFERENT things
is worth more than its kept count suggests, and a shape that only re-finds what
we have is worth nothing however well it scores.

    python scripts/github_query_shape_experiment.py --dry-run
    python scripts/github_query_shape_experiment.py --apply
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

SEARCH_URL = "https://api.github.com/search/issues"

#: (RETRIEVAL form, SIEVE form). They are different on purpose and
#: `render_search` says why in the codebase already:
#:
#:   "SIEVE uses the alias EXACTLY as a human writes it, because that is what
#:    the document contains. Sieving with the hyphenated form would drop every
#:    post written in prose - most of them - and drop them silently."
#:
#: Retrieval is hyphenated because 57.9% of concatenated queries fetch nothing.
#: Sieving with that same form is the documented trap, and the first version of
#: this script walked into it.
ALIASES = (
    ("claude-sonnet-4.5", "claude sonnet 4.5"),
    ("gpt-5.2", "gpt 5.2"),
    ("qwen3.8-27b", "qwen3.8 27b"),
)

#: Literal artifacts a tier-A issue carries. NONE of these is in the topic
#: vocabulary, which is the point - the productive topic tokens are artifacts
#: and the barren ones are concepts.
REPRO_WORDS = ("traceback", '"steps to reproduce"')

#: Signal phrases with NO topic term, attacking the diagnosed constraint
#: directly: signal was 3 hits in 2,239 candidates.
SIGNAL_PHRASES = ('"returns empty"', '"silently truncat"')

LABELS = ("label:bug",)


def _doc_text(item: dict) -> str:
    """Title plus a bounded body, the same text the sieve is given."""
    title = item.get("title") or ""
    body = (item.get("body") or "")[:4000]
    return f"{title}{chr(10)}{chr(10)}{body}"


def arms() -> list[tuple[str, str, str]]:
    """(shape, alias, query). Ordered: repro, signal, title, label."""
    plan: list[tuple[str, str, str, str]] = []
    for retrieval, sieve_form in ALIASES:
        for word in REPRO_WORDS:
            plan.append(("repro", retrieval, sieve_form,
                         f'"{retrieval}" {word} type:issue'))
    for retrieval, sieve_form in ALIASES:
        for phrase in SIGNAL_PHRASES:
            plan.append(("signal", retrieval, sieve_form,
                         f'"{retrieval}" {phrase} type:issue'))
    for retrieval, sieve_form in ALIASES:
        plan.append(("title", retrieval, sieve_form,
                     f'"{retrieval}" in:title type:issue'))
    for retrieval, sieve_form in ALIASES:
        for label in LABELS:
            plan.append(("label", retrieval, sieve_form,
                         f'"{retrieval}" {label} type:issue'))
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    plan = arms()
    by_shape = collections.Counter(shape for shape, _r, _s, _q in plan)
    print("REQUEST COST PER ARM (search bucket, 30/minute):")
    for shape in ("repro", "signal", "title", "label"):
        print(f"  {shape:8s} {by_shape[shape]:3d} requests")
    print(f"  {'TOTAL':8s} {len(plan):3d} requests"
          f"  ~{len(plan) / 30:.1f} minutes at the search limit")
    print()
    for shape, _r, _s, query in plan:
        print(f"  [{shape:6s}] {query}")

    if args.dry_run:
        print("\n--dry-run: no requests issued.")
        return 0

    import time

    import httpx

    from collect.adapters.queries import load_queries, sieve
    from collect.db import connect

    # Terms come from the CONTRACT, not invented here: the sieve is identical on
    # all three platforms and this experiment changes RETRIEVAL only.
    querysets = load_queries()
    # `all_entries`, NOT `entries`. The first run of this script used
    # `getattr(qs, "entries", [])`, which turned a missing attribute into an
    # empty list, so the sieve loop never executed and every subject/topic/
    # signal/kept column came back 0 across 1,451 candidates. A definite answer
    # about something never evaluated - the same defect class this project keeps
    # finding, this time in the measuring instrument.
    entries = list(querysets.all_entries)
    if not entries:
        raise SystemExit(
            "no query entries loaded; refusing to run a sieve that would report "
            "zero for every shape and look like a result."
        )
    print(f"query entries loaded for the sieve: {len(entries)}")

    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": os.getenv("USER_AGENT", "modelboard/0.1"),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    client = httpx.Client(headers=headers, timeout=30.0)

    conn = connect()
    known = {
        r[0]
        for r in conn.execute(
            "SELECT external_id FROM document WHERE source = 'github'"
        ).fetchall()
    }
    print(f"\ngithub documents already held: {len(known)}")

    results: list[dict] = []
    ids_by_shape: dict[str, set[str]] = collections.defaultdict(set)

    for shape, alias, sieve_alias, query in plan:
        response = client.get(
            SEARCH_URL, params={"q": query, "per_page": 100, "page": 1}
        )
        if response.status_code != 200:
            print(f"  [{shape}] HTTP {response.status_code} on {query!r}")
            results.append(
                {"shape": shape, "alias": alias, "query": query,
                 "status": response.status_code, "candidates": 0}
            )
            time.sleep(2.1)
            continue
        payload = response.json()
        items = payload.get("items") or []

        subject = topic = signal = kept = 0
        for item in items:
            text = f"{item.get('title') or ''}\n\n{item.get('body') or ''}"
            best = None
            for entry in entries:
                if entry.needs_second_model:
                    # A substitution entry ("replaced X with Y") needs a second
                    # alias. `contract.py` REFUSES to render without one rather
                    # than searching for the literal `{alias_b}` - "which reads
                    # as an absence of discussion rather than as a bug". This
                    # experiment supplies one alias, so those entries are not
                    # applicable and are skipped rather than half-rendered.
                    continue
                terms = entry.terms.substitute(sieve_alias)
                verdict = sieve(terms, text)
                if verdict.subject:
                    subject += 1
                    if verdict.topic:
                        topic += 1
                    if verdict.signal:
                        signal += 1
                    if verdict.passed:
                        kept += 1
                        best = verdict
                    break
            if best is not None:
                ids_by_shape[shape].add(str(item.get("id")))

        results.append(
            {
                "shape": shape, "alias": alias, "query": query,
                "total_count": payload.get("total_count"),
                "candidates": len(items),
                "subject": subject, "topic": topic, "signal": signal, "kept": kept,
                "ids": [str(i.get("id")) for i in items],
                # STORED so a re-sieve is free. The first run could not be
                # re-analysed after the bug was found, and cost 18 requests to
                # repeat.
                "texts": [
                    _doc_text(i)
                    for i in items
                ],
            }
        )
        print(f"  [{shape:6s}] {alias:18s} candidates={len(items):3d} "
              f"subject={subject:3d} topic={topic:3d} signal={signal:3d} kept={kept:3d}")
        # 30/minute. Two seconds is under it with headroom.
        time.sleep(2.1)

    client.close()
    conn.close()

    print()
    print("=" * 74)
    print(f"{'shape':8s} {'reqs':>5} {'cands':>6} {'subj':>5} {'topic':>6} "
          f"{'signal':>7} {'kept':>5} {'UNIQUE':>7}")
    agg: dict[str, list] = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    for r in results:
        a = agg[r["shape"]]
        a[0] += 1
        a[1] += r.get("candidates", 0)
        a[2] += r.get("subject", 0)
        a[3] += r.get("topic", 0)
        a[4] += r.get("signal", 0)
        a[5] += r.get("kept", 0)
    for shape in ("repro", "signal", "title", "label"):
        n, c, su, t, si, k = agg[shape]
        # UNIQUE = kept ids this shape found that NO OTHER shape found.
        others: set[str] = set()
        for other, ids in ids_by_shape.items():
            if other != shape:
                others |= ids
        unique = len(ids_by_shape[shape] - others)
        print(f"{shape:8s} {n:5d} {c:6d} {su:5d} {t:6d} {si:7d} {k:5d} {unique:7d}")

    all_kept = set().union(*ids_by_shape.values()) if ids_by_shape else set()
    print()
    print(f"documents kept across all shapes : {len(all_kept)}")
    print("NOTE: 'unique' is unique AMONG THESE SHAPES, not unique against the "
          "corpus. Both are reported because they answer different questions.")

    out = pathlib.Path("_github_shape_experiment.json")
    out.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"per-query rows written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
