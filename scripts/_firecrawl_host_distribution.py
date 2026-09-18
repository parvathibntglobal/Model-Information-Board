"""Which hosts does a model-name search actually land on? SEARCH ONLY.

RUN TWICE, 2026-09-18. Both draws are committed beside it - re-running costs
credits and cannot reproduce the same draw, because the index moves.

    _firecrawl_probe/            20 queries `<model> <topic term>`, 200 results,
                                 40 credits, 100 hosts, 71 with one result
    _firecrawl_probe_substack/   13 queries `<model> substack`, 130 results,
                                 26 credits,  79 hosts, 63 with one result

Thirteen and not twenty on the second: `--suffix` over 13 tracked models yields
13 distinct strings, and the other seven would have been byte-identical repeats
returning the same results. 14 credits unspent rather than spent on repeats.

⚠ THE HOST NAMES IN THESE SUMMARIES ARE NOT CLASSIFIED AND MUST NOT BE READ AS
  IF THEY WERE. Two of `_firecrawl_probe_substack`'s hosts that look self-hosted
  are custom-domain Substacks - `lennysnewsletter.com` and `interconnects.ai`.
  See `docs/host-classification-needs-a-probe.md`.

WHAT THIS DOES AND DELIBERATELY DOES NOT DO

It calls Firecrawl `/v2/search` with NO `scrapeOptions`, so the response carries
`url`, `title` and `description` and nothing else. **No publisher page is
fetched, by us or on our behalf**, so no host needs a terms ruling for this to
run. That is the whole reason this probe is separable from the ruling queue it
exists to size.

Cost is 2 credits per 10 results, rounded up. The script reports `creditsUsed`
as the API returns it rather than computing an estimate, because an estimate of
a number the response already carries is a figure nobody can check.

WHAT IT MEASURES, AND ITS DENOMINATOR

    population   the top N web results for each rendered query below
    gathered by  Firecrawl's index, whatever that is - NOT a sample of the web,
                 and not a sample of engineering blogs
    reports      distinct hosts, overlap with the nine seated feeds, and the
                 shape of the tail (hosts contributing exactly one result)

THE QUESTION IT ANSWERS is how many NEW HOSTS a model-name search produces,
because every novel self-hosted host is one class A re-review
(`contract/sources.yaml`, `blog-class-a-self-hosted`: "RE-REVIEW REQUIRED
BEFORE ... adding a feed outside the nine assessed"). A long one-post tail means
the review queue is the project; concentration means a handful of re-reviews.

THE QUESTION IT CANNOT ANSWER is the model-naming rate. `nine-feeds-and-one-
writer.md` measured 23 of 119 (19%) over FULL ARTICLE TEXT of everything nine
feeds published. A rate computed over the results of a query that contains the
model name is circular - the index matched on the name, so the rate approaches
100% by construction and measures the search engine rather than the corpus.
Rule 7: it would be a real value answering a question nobody asked. Settling it
needs article text, which needs a fetch, which needs the ruling.

QUERY RENDERING IS A CHOICE AND IT IS NOT THE CONTRACT'S

`contract/queries.yaml` carries TERM SETS and no query strings, on purpose:
"a rendered query string in a platform-neutral file is a string that is true for
no platform." Nobody has measured what Firecrawl's index honours - phrases,
operators, `site:` - so the rendering below is the plainest thing that could
work (alias plus one topic term, no quoting, no operators) and is a variable of
this measurement rather than a finding of it.

    python scripts/_firecrawl_host_distribution.py --queries 20 --limit 10
    python scripts/_firecrawl_host_distribution.py --suffix substack --out DIR
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys
import time
import urllib.parse

import httpx
import yaml
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

ENDPOINT = "https://api.firecrawl.dev/v2/search"


def _seated_hosts() -> set[str]:
    """The nine. Hosts, not feed urls - a result links an article, not a feed."""
    doc = yaml.safe_load((ROOT / "contract" / "sources.yaml").read_text(encoding="utf-8"))
    hosts = set()
    for feed in doc.get("feeds") or []:
        endpoint = feed.get("endpoint") or ""
        host = urllib.parse.urlparse(endpoint).hostname
        if host:
            hosts.add(host.lower().removeprefix("www."))
    return hosts


def _suffix_queries(suffix: str) -> list[str]:
    """`<model name> <suffix>`, ONE PER MODEL AND DEDUPED.

    A fixed suffix over 13 models yields 13 distinct strings and no more. Asking
    for 20 would send 7 byte-identical repeats, which return the same results
    and spend credits measuring nothing - so the count is the model list's
    length, and the shortfall is reported rather than padded.
    """
    models = [
        m["name"]
        for m in yaml.safe_load(
            (ROOT / "contract" / "tracked_models.yaml").read_text(encoding="utf-8")
        )["models"]
    ]
    seen, out = set(), []
    for name in models:
        query = f"{name} {suffix}".strip()
        if query not in seen:
            seen.add(query)
            out.append(query)
    return out


def _queries(n: int) -> list[str]:
    """`<model name> <topic term>`, round-robin over models then capabilities.

    Round-robin rather than all-of-one-model-first so that truncating at `n`
    still covers a spread of both, instead of measuring one model's hosts.
    """
    models = [
        m["name"]
        for m in yaml.safe_load(
            (ROOT / "contract" / "tracked_models.yaml").read_text(encoding="utf-8")
        )["models"]
    ]
    query_sets = yaml.safe_load(
        (ROOT / "contract" / "queries.yaml").read_text(encoding="utf-8")
    )["queries"]
    topics = []
    for entry in query_sets:
        for term in (entry.get("terms") or {}).get("topic") or []:
            if term not in topics:
                topics.append(term)

    out = []
    for i in range(n):
        out.append(f"{models[i % len(models)]} {topics[i % len(topics)]}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=int, default=20)
    parser.add_argument("--limit", type=int, default=10, help="results per query")
    parser.add_argument("--out", default="_firecrawl_probe")
    parser.add_argument(
        "--suffix", default=None,
        help="second query shape: `<model name> <suffix>`, one query per "
             "tracked model, deduped. Overrides --queries.",
    )
    args = parser.parse_args()

    key = os.getenv("FIRECRAWL_API_KEY")
    if not key:
        raise SystemExit(
            "FIRECRAWL_API_KEY is unset. Refusing to run: there is no default "
            "and no anonymous mode, and a probe that silently measured nothing "
            "would be worse than one that did not run."
        )

    out_dir = ROOT / args.out
    out_dir.mkdir(exist_ok=True)

    queries = _suffix_queries(args.suffix) if args.suffix else _queries(args.queries)
    seated = _seated_hosts()
    print(f"  {len(seated)} seated hosts: {', '.join(sorted(seated))}")
    print(f"  {len(queries)} queries, limit {args.limit}, search only (no scrape)\n")

    hosts: collections.Counter[str] = collections.Counter()
    host_queries: dict[str, set[str]] = collections.defaultdict(set)
    credits = 0
    results_total = 0
    failures: list[tuple[str, str]] = []

    with httpx.Client(timeout=60) as client:
        for i, query in enumerate(queries, 1):
            try:
                response = client.post(
                    ENDPOINT,
                    headers={"Authorization": f"Bearer {key}"},
                    json={"query": query, "limit": args.limit,
                          "sources": [{"type": "web"}]},
                )
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:                      # noqa: BLE001
                # NAMED AND COUNTED, never silently skipped: a query that
                # errored is not a query that found nothing.
                failures.append((query, f"{type(exc).__name__}: {exc}"))
                print(f"  {i:3d}. FAILED  {query}  ({type(exc).__name__})")
                continue

            # EVERY RESPONSE PERSISTED. A draw that enters an argument and was
            # not saved is a draw nobody can re-read.
            (out_dir / f"q{i:03d}.json").write_text(
                json.dumps({"query": query, "response": payload}, indent=1),
                encoding="utf-8",
            )

            credits += payload.get("creditsUsed") or 0
            rows = (payload.get("data") or {}).get("web") or []
            results_total += len(rows)
            for row in rows:
                host = (urllib.parse.urlparse(row.get("url") or "").hostname or "")
                host = host.lower().removeprefix("www.")
                if host:
                    hosts[host] += 1
                    host_queries[host].add(query)
            print(f"  {i:3d}. {len(rows):2d} results  {query}")
            time.sleep(6.5)        # free tier is 10/min on search

    # ── the report ──────────────────────────────────────────────────────────
    one_post = [h for h, c in hosts.items() if c == 1]
    already = {h for h in hosts if h in seated}

    print(f"\n  {results_total} results over {len(queries) - len(failures)} "
          f"successful queries, {credits} credits used (API-reported)")
    if failures:
        print(f"  {len(failures)} queries FAILED and are excluded from the "
              f"denominator above:")
        for query, why in failures:
            print(f"      {query}: {why}")

    print(f"\n  {len(hosts)} distinct hosts")
    print(f"  {len(already)} of them already seated "
          f"({', '.join(sorted(already)) or 'none'})")
    print(f"  {len(hosts) - len(already)} would each be a new class A re-review")
    print(f"\n  TAIL: {len(one_post)} hosts contributed exactly one result "
          f"({len(one_post) / len(hosts):.0%} of hosts)" if hosts else "  no hosts")

    print("\n  hosts by result count")
    for host, count in hosts.most_common():
        mark = "  (seated)" if host in seated else ""
        print(f"    {count:3d}  {host}{mark}")

    summary = {
        "queries": len(queries),
        "queries_ok": len(queries) - len(failures),
        "failures": failures,
        "limit": args.limit,
        "results_total": results_total,
        "credits_used": credits,
        "seated_hosts": sorted(seated),
        "distinct_hosts": len(hosts),
        "already_seated": sorted(already),
        "one_result_hosts": sorted(one_post),
        "hosts": dict(hosts.most_common()),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"\n  -> {out_dir}/summary.json  and one file per query")
    return 0


if __name__ == "__main__":
    sys.exit(main())
