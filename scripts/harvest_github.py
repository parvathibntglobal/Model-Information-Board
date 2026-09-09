"""A measured GitHub harvest. Not the nightly pipeline — the instrument.

The nightly chain will run adapters and write rows. This runs one narrow slice
and reports what the seam did, which is a different job: pass rate per query
and per group, what the sieve caught that retrieval let through, what retrieval
missed that the sieve would have kept, and rate limit consumed against
prediction.

Kept in `scripts/` rather than thrown away after each run because the numbers
only mean anything as a series. Two runs so far:

    2026-08-13   16-entry vocabulary    149 candidates,   0 kept
    2026-08-14   24-entry vocabulary,   636 candidates,   5 keeps of ONE
                 final-word stemming,                     distinct document
                 containment split

WHY IT WRITES TO ITS OWN DATABASE
---------------------------------
The first run's rows were destroyed by the next `pytest`, because the DB
fixtures `DROP SCHEMA public CASCADE` on whatever `TEST_DATABASE_URL` names.
"Inspect before running the suite" holds until somebody runs the suite without
thinking, and the failure is the silent destruction of the thing being
measured. So this writes to `modelboard_harvest_test`, and it reuses the
suite's own three-layer disposability guard rather than reimplementing it — a
runner that drops a schema deserves the same checks a test does.

COUNT DISTINCT DOCUMENTS, NOT KEEPS
-----------------------------------
One issue found by five alias variants is five keeps and one voice. The
2026-08-14 run kept 5 and stored 1, and reporting the 5 would have counted one
engineer five times — which is the over-clustering `collect/CLAUDE.md` says is
worse than under-clustering. The report carries both and the summary leads
with distinct.

    python scripts/harvest_github.py --out run.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

# THE REPO ROOT, BECAUSE `checked_dsn` IMPORTS `tests.conftest` FOR THE
# DISPOSABLE-DATABASE GUARD. `collect` resolves from the installed package, so
# every import below worked and this script still could not run:
# `python scripts/harvest_github.py` died on `No module named 'tests'` at the
# first database call, AFTER the terms gate passed and the plan printed — which
# reads like a database problem and is a path problem.
#
# `harvest_blogs.py` and `unfiltered_sweep.py` have carried this line since they
# were written; this script did not, and nothing noticed because the two people
# who ran it both had the repo root on their path. Two of three scripts
# self-bootstrapping is worse than none doing it, because the exception names
# the wrong layer.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.adapters.github import GitHubHarvester, QueryRun  # noqa: E402
from collect.adapters.queries import load_queries, plan_searches, render_search
from collect.adapters.queries.cadence import split_by_cadence
from collect.adapters.queries.github import SearchRequest
from collect.config import settings
from collect.db import apply_schema, connect
from collect.http import build_client
from collect.rawstore import RawStore
from collect.registry.aliases import alias_rows
from collect.registry.assertions import assert_terms_reviewed
from collect.registry.seed import seed_models
from collect.registry.sources import load_sources
from collect.triage.specificity import alias_match_count

#: WHICH MODEL TO HARVEST EVIDENCE **ABOUT** - a seed model's `canonical_id`,
#: resolved through `seed_models()` below to get its search aliases. It is NOT
#: the extractor, and harvesting calls no language model at all: NFR-8 allows
#: exactly two stages to do that and `tests/test_lane_boundary.py` enforces that
#: `collect/` never imports a model client.
#:
#: ⚠ I POINTED THIS AT `EXTRACTOR_MODEL` ON 2026-09-09 AND THAT WAS WRONG. The
#: name collision is the trap: `--model` here is the SUBJECT of the research,
#: while `EXTRACTOR_MODEL` is the tool doing the reading. Reading the extractor
#: setting into it would crash on `StopIteration` the moment somebody set the
#: extractor to something that is not a seed model - `…-v4-flash:free`, say.
DEFAULT_MODEL = "google/gemini-2.5-flash"
DEFAULT_CAPABILITIES = (
    "tool_calling.schema_accuracy",
    "summarization.fidelity",
    "context.effective_window",
)
DEFAULT_SCOPE = (
    "repo:langchain-ai/langchain",
    "repo:run-llama/llama_index",
    "repo:Aider-AI/aider",
    "repo:microsoft/autogen",
    "repo:crewAIInc/crewAI",
)
#: NOT TEST_DATABASE_URL. See the module docstring.
DEFAULT_DSN = "postgresql://postgres@localhost:5433/modelboard_harvest_test"


def checked_dsn(dsn: str) -> str:
    """All three disposability layers, borrowed from the suite."""
    from tests.conftest import assert_disposable, assert_safe_target

    assert_safe_target(dsn)
    with connect(dsn) as probe:
        assert_disposable(probe, dsn)
    return dsn


def kept_document(run: QueryRun, stored) -> dict:
    """One kept document, with the terms that actually carried it.

    Re-sieved rather than looked up: `sieve()` is pure and the text is the
    same text, so this costs nothing and says which terms matched — the
    difference between "signal moved off zero" and knowing why.
    """
    verdict = run.request.sieve(stored.hit.sieve_text)
    return {
        "entry": run.request.entry_label,
        "url": stored.html_url,
        "title": stored.hit.title[:120],
        "external_id": stored.external_id,
        "already_present": stored.already_present,
        "subject": list(verdict.subject),
        "topic": list(verdict.topic),
        "signal": list(verdict.signal),
        "signal_in_excluded": list(verdict.signal_in_excluded),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--capability", action="append", dest="capabilities")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    # ── THE CANONICAL STORE, not a scratch directory ──────────────────────
    #
    # Was `./_harvest_store`, which is gitignored and machine-local, so the 27
    # documents this script wrote to staging have `text_ref` values that resolve
    # NOWHERE — 0 of 27, checked. The adapter was never missing a store call
    # (`GitHubHarvester.fetch_issue` puts every payload, github.py:485); the
    # DESTINATION was disposable, which is the same outcome by a different route
    # and reads as an adapter gap in a report.
    #
    # `scripts/harvest_blogs.py` already used `settings().raw_store_path`, which
    # is why 30 of 30 blog payloads resolve and none of the GitHub ones do. Two
    # sibling harvest scripts, two stores, one of them a temp folder.
    #
    # Costs nothing extra to carry: the `put` already happens, so only where it
    # lands changes. Re-fetching the existing 27 is 27 API requests; the next
    # sweep persisting its own is free.
    parser.add_argument("--store", default=None)
    parser.add_argument("--out", default="github-run-report.json")
    parser.add_argument("--max-fetch-per-query", type=int, default=15)
    parser.add_argument("--fetch-cap", type=int, default=160)
    args = parser.parse_args(argv)
    capabilities = tuple(args.capabilities or DEFAULT_CAPABILITIES)

    contract = load_sources()
    github = next(s for s in contract.platforms if s["id"] == "github")
    # The gate, for real: a known unexpired ruling, evidence that has not gone
    # stale, and this run's own observation of the access path.
    assert_terms_reviewed(
        [github],
        rulings=contract.rulings,
        observations={"github": {"access_path": "api"}},
        today=datetime.now(UTC).date(),
    )
    print("gate: github terms reviewed and re-verified, harvest permitted\n")

    queries = load_queries()
    entries = [e for cap in capabilities for e in queries.for_capability(cap)]
    cadence = split_by_cadence(entries)
    model = next(m for m in seed_models() if m.canonical_id == args.model)
    variants = sorted({v for r in alias_rows(model) if r.search_eligible for v in r.variants})
    plan = plan_searches(entries, variants, scope=DEFAULT_SCOPE)

    print(f"model    : {args.model}")
    print(f"entries  : {len(entries)} "
          f"(daily {len(cadence['daily'])}, weekly {len(cadence['weekly'])})")
    # A LENGTH, NOT A MATCH COUNT — and the length is the figure that failed.
    # 35 aliases matching nothing printed identically to 35 matching everything
    # for weeks. The real number needs documents to match against, so it is
    # reported after the sweep (see `alias_match_count` below) and the declared
    # count is labelled as declared rather than left to read as a measurement.
    print(f"aliases  : {len(variants)} declared  {variants}")
    print(f"requests : {plan.request_count} planned, {plan.distinct_queries} distinct")
    print(f"predicted: {plan.minutes_at(30):.1f} min at 30 search req/min\n")

    client = build_client(
        timeout=30.0,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {settings().github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    before = client.get("https://api.github.com/rate_limit").json()["resources"]
    harvester = GitHubHarvester(
        client=client,
        store=RawStore(Path(args.store or settings().raw_store_path)),
        max_pages=1,
        max_fetch_per_query=args.max_fetch_per_query,
    )

    conn = connect(checked_dsn(args.dsn))
    conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    apply_schema(conn)
    from psycopg.types.json import Json

    conn.execute(
        "INSERT INTO source (id, platform, endpoint, base_trust, tos_notes, provenance, "
        "                    terms_ruling, terms_checked_on, terms_evidence) "
        "VALUES ('github','github','https://api.github.com',0.95,%s,'seed',%s,%s,%s)",
        (
            github["tos_notes"],
            github["terms_ruling"],
            github["terms_evidence"]["checked_on"],
            Json({k: str(v) for k, v in github["terms_evidence"].items()}),
        ),
    )
    conn.commit()

    started = time.monotonic()
    runs, fetched = [], 0
    for index, request in enumerate(plan.requests, 1):
        if fetched >= args.fetch_cap:
            print(f"  [{index:2}] global fetch cap reached, stopping")
            break
        run = harvester.harvest(request)
        wrote = harvester.write_documents(conn, run)
        conn.commit()
        fetched += run.rest_calls
        runs.append(run)
        y = run.sieve_yield
        print(
            f"  [{index:2}/{plan.request_count}] {run.request.entry_label:44} "
            f"total={str(run.total_count):>5} got={run.retrieved:3} "
            f"sieve={y.kept:3}/{y.candidates:3} ({y.pass_rate:5.1%}) "
            # inserted, not seen: a sweep legitimately returns the same issue
            # from two queries, and the old counter reported writing it twice.
            f"wrote={wrote['inserted']:3}/{wrote['seen']:<3} "
            f"trunc={run.truncated_by or '-'}"
        )
    wall = time.monotonic() - started

    # ── DID THE ALIASES ACTUALLY MATCH ANYTHING? ─────────────────────────
    #
    # THE SECOND INSTANCE OF THIS DEFECT IN TWO PLACES. `scripts/
    # export_thread_contexts.py` recorded a non-empty alias tuple in provenance
    # and read it as a scoring input while it matched zero documents; this
    # script printed `len(variants)`. Both report that a list EXISTS. Neither
    # reported that it HITS, and those diverge silently — a sweep retrieving on
    # dead variants looks exactly like a healthy one, because the aliases are
    # in the query string either way and the query still returns results.
    #
    # ITS POPULATION IS THE STORED DOCUMENTS, AND THAT IS STATED RATHER THAN
    # GLOSSED. `QueryRun` retains `verdicts` (which carry matched TERMS, not
    # bodies) and `stored` (which carries the hit). So the bodies available here
    # are the ones the sieve KEPT — not every candidate. Reporting this figure
    # as "of candidates" would be the very error being fixed: a number computed
    # over one population answering a question about another.
    #
    # Counted with the same `alias_match_count` the export uses, so the two are
    # comparable. If it is 0 the variants contributed nothing to what came back.
    bodies = [issue.hit.sieve_text for run in runs for issue in run.stored]
    alias_hits = alias_match_count(variants, bodies) if bodies else None

    # ── each group counted over ALL candidates, independently ────────────
    #
    # The first run reported "77% topic", which counted topic matches only
    # among documents where subject ALSO matched. That is bounded by the
    # subject rate and cannot measure topic at all. Counted independently on
    # 2026-08-14 the real figure was 19.5%, and the defect-4 recommendation
    # had been resting on a number that never existed.
    groups: Counter[str] = Counter()
    candidates = quoted_only = 0
    for run in runs:
        for verdict in run.verdicts:
            candidates += 1
            for name in ("subject", "topic", "signal"):
                if getattr(verdict, name):
                    groups[name] += 1
            if verdict.signal_in_excluded:
                quoted_only += 1

    # ── what the narrowing token costs, measured not assumed ─────────────
    probe = entries[0]
    narrow = render_search(probe, variants[0], scope=DEFAULT_SCOPE)
    narrow_run = QueryRun(request=narrow)
    narrow_hits = harvester.search(narrow, narrow_run)
    narrow_urls = {hit.html_url for hit in narrow_hits}

    broad = SearchRequest(
        query=" ".join([f'"{variants[0]}"', "type:issue", *DEFAULT_SCOPE]),
        entry_label=probe.label + ":unnarrowed",
        variants=narrow.variants,
        narrowing_token=None,
        scope=DEFAULT_SCOPE,
    )
    broad_run = QueryRun(request=broad)
    broad_hits = harvester.search(broad, broad_run)
    missed = [
        hit for hit in broad_hits
        if hit.html_url not in narrow_urls and broad.sieve(hit.sieve_text).passed
    ]

    rows = conn.execute(
        "SELECT count(*), count(distinct external_id) FROM document"
    ).fetchone()
    after = client.get("https://api.github.com/rate_limit").json()["resources"]
    kept = [kept_document(r, s) for r in runs for s in r.stored]

    report = {
        "model": args.model,
        "capabilities": list(capabilities),
        "entries": len(entries),
        "entries_daily": len(cadence["daily"]),
        "entries_weekly": len(cadence["weekly"]),
        "aliases": variants,
        "aliases_declared": len(variants),
        # A COUNT OF MATCHES, WITH ITS POPULATION NAMED IN THE KEY. `aliases`
        # above is the list; a non-empty list is not evidence that any of it
        # matched, which is exactly how 35 dead variants passed for weeks.
        "aliases_matched_stored_documents": alias_hits,
        "aliases_matched_of": len(bodies),
        **harvester.totals(),
        "queries_in_main_loop": len(runs),
        "wall_clock_seconds": round(wall, 1),
        "predicted_minutes_at_30": round(plan.minutes_at(30), 1),
        "document_rows": rows[0],
        "distinct_documents": rows[1],
        "candidates_seen": candidates,
        "group_hits": dict(groups),
        "signal_in_excluded_docs": quoted_only,
        "search_before": before["search"], "search_after": after["search"],
        "core_before": before["core"], "core_after": after["core"],
        "retrieval_vs_sieve": {
            "narrowed_total": narrow_run.total_count,
            "narrowed_retrieved": len(narrow_hits),
            "unnarrowed_total": broad_run.total_count,
            "unnarrowed_retrieved": len(broad_hits),
            "excluded_by_narrowing_that_would_pass": len(missed),
        },
        "per_query": [
            {
                "entry": r.request.entry_label,
                "query": r.request.query,
                "total_count": r.total_count,
                "retrieved": r.retrieved,
                "sieve_candidates": r.sieve_yield.candidates,
                "sieve_kept": r.sieve_yield.kept,
                "pass_rate": round(r.sieve_yield.pass_rate, 3),
                "missing_subject": r.sieve_yield.missing_subject,
                "missing_topic": r.sieve_yield.missing_topic,
                "missing_signal": r.sieve_yield.missing_signal,
                "signal_in_excluded_docs": sum(
                    1 for v in r.verdicts if v.signal_in_excluded
                ),
                "stored": len(r.stored),
                "truncated_by": r.truncated_by,
            }
            for r in runs
        ],
        "kept_documents": kept,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    Path(args.out).write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")

    print("\n=== totals ===")
    print(f"search calls   : {report['search_calls']}   rest calls: {report['rest_calls']}")
    print(f"rate limited   : {report['rate_limited_queries']} quer(ies), "
          f"{report['backoff_seconds']}s backoff, "
          f"{report['unknown_total_count']} unknown total(s)")
    print(f"wall clock     : {report['wall_clock_seconds']}s "
          f"(predicted {report['predicted_minutes_at_30']} min at 30/min)")
    print(f"http errors    : {report['http_errors']}")
    print(f"kept           : {len(kept)} query-document pair(s)")
    print(f"DISTINCT DOCS  : {report['distinct_documents']}   <- the real number")

    print(f"\n=== group membership over all {candidates} candidates ===")
    for name in ("subject", "topic", "signal"):
        n = groups[name]
        print(f"  {name:<8} {n:4}/{candidates}  {n / candidates:6.1%}" if candidates
              else f"  {name:<8} no candidates")
    print(f"  signal only in quoted/fenced text: {quoted_only}")

    # THE FIGURE THAT USED TO BE A LIST LENGTH. Printed with its population, so
    # "35 aliases" can no longer stand in for "35 aliases that matched
    # something" — they were the same string for weeks and are different facts.
    if alias_hits is None:
        print(f"\n=== aliases: {len(variants)} declared, MATCH COUNT UNKNOWN ===")
        print("  no stored document bodies to match against, so this sweep")
        print("  cannot say whether the variants hit. Not 0 — unknown.")
    else:
        share = alias_hits / len(bodies) if bodies else 0.0
        print(f"\n=== aliases: {len(variants)} declared, "
              f"{alias_hits} matched {len(bodies)} stored docs ({share:.1%}) ===")
        if alias_hits == 0:
            print("  ZERO. The variants contributed nothing to what came back;")
            print("  `names_version` scored False on every stored document and")
            print("  any ranking that read it ran on a dead input.")

    rv = report["retrieval_vs_sieve"]
    print("\n=== retrieval versus sieve ===")
    print(f"  narrowed   total={rv['narrowed_total']} retrieved={rv['narrowed_retrieved']}")
    print(f"  unnarrowed total={rv['unnarrowed_total']} retrieved={rv['unnarrowed_retrieved']}")
    print(f"  excluded by the narrowing token that would have passed: "
          f"{rv['excluded_by_narrowing_that_would_pass']}")

    for document in kept:
        print(f"\n  {document['entry']}  {document['url']}")
        print(f"    {document['title']}")
        print(f"    subject={document['subject']} topic={document['topic']} "
              f"signal={document['signal']}")

    print(f"\nwrote {args.out}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
