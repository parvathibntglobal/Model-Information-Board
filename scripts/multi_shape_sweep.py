"""The multi-shape GitHub sweep: `title` then `repro`, shape-major.

WHAT THIS BUYS, AND IT IS SMALLER THAN IT LOOKS. It is a CORPUS operation, not a
claims one. Say it before the numbers rather than after:

    Four shapes across the 18-request experiment returned **zero signal hits and
    zero kept documents** - `title` 0/300, `repro` 0/600, `signal` 0/251,
    `label` 0/300. The shape ranking is entirely about SUBJECT PRECISION: 31.0%
    on-subject per request for `title` against 17.0% for `repro`. So this
    roughly triples the share of retrieved documents that are actually ABOUT the
    model, and it moves NOTHING downstream on its own - no claim, no voice, no
    cell. The comment write path is the part that touches voices.

    A document stored here becomes evidence only if a later extraction finds a
    claim in it. This buys the pool that extraction reads from.

SUBJECT IS THE GATE, AND THE FULL SIEVE CANNOT BE. `sieve()` treats an empty
`topic` or `signal` group as a FAILED group, deliberately - an empty group would
be vacuously true and collapse the query to its subject alone. A shape query has
no capability entry and therefore no topic or signal terms, so running the full
sieve as the store gate would keep exactly zero documents, which is what the
experiment measured. This gates on SUBJECT and RECORDS topic and signal as
counts, which is rule 8's shape: the unmeasured thing is a field, not a gate.

SHAPE-MAJOR. `sweep_requests` orders every `title` request before any `repro`
one, so a run truncated at request 134 of 268 has issued `title` for every
model rather than both arms for the first half. Truncation is the expected case
at 30 requests per minute. `label` raises rather than being filtered - asking
for it is a decision somebody made.

PROVENANCE IS TYPED, NOT DEFAULTED. Every row carries `harvest_run_id` and
`retrieval_provenance = 'run_recorded'`, because this sweep DOES issue a query
per request and opens a `harvest_run` row before each fetch. That is the state
the column exists to distinguish from `no_run_for_source` - which would be a
false claim here - and from `not_recorded`, which would be true only if nobody
had instrumented it.

    python scripts/multi_shape_sweep.py --plan
    python scripts/multi_shape_sweep.py --apply [--budget N] [--max-minutes M]
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import time
from datetime import UTC, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from collect.adapters.queries.contract import RenderedTerms  # noqa: E402
from collect.adapters.queries.github import (  # noqa: E402
    SWEEP_SHAPES,
    SearchRequest,
    sweep_requests,
)
from collect.config import settings  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.ops.sweep import seated_variants  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402

#: GitHub search is 30 requests/minute. The contract's daily ceiling is 900, and
#: this plan is 268 - so the binding constraint is wall clock, not the cap.
DEFAULT_MAX_MINUTES = 20


def _subject_only_request(query: str, surface: str, variants) -> SearchRequest:
    """A `SearchRequest` whose sieve asks only "is this document about the model".

    `topic` and `signal` are EMPTY ON PURPOSE and the verdict is read for its
    `missing` list rather than its `passed` flag - see the module docstring on
    why `passed` is necessarily False here. Every spelling of the model is
    carried, not the one that retrieved the document: measured on the first live
    run, checking only the retrieving spelling put the subject-miss rate at
    88.6% against 66.9% for all six forms, recovering 28 of 136 documents for no
    extra request.
    """
    return SearchRequest(
        query=query,
        entry_label=f"shape:{surface}",
        variants=tuple(
            RenderedTerms(subject=(v,), topic=(), signal=(), alias=v) for v in variants
        ),
        narrowing_token=None,
    )


def _prose_request(query: str, surface: str, variants) -> SearchRequest:
    """The SAME check restricted to the spellings a human writes in prose.

    ⚠ WHY TWO SUBJECT FIGURES, AND WHY THE LOOSE ONE MUST NOT BE QUOTED ALONE.
      A `title` query asks GitHub for documents whose TITLE contains
      `claude-sonnet-4.5`, and `sieve.normalize` casefolds and collapses
      whitespace WITHOUT stripping hyphens - so the retrieval form is present in
      the text by construction and an any-form subject check passes on nearly
      everything. The first slice measured 96.2%, and that figure is GitHub
      confirming it honoured the query rather than evidence about the corpus.
      Rule 7 exactly: a real value answering a question it was not asked.

      The shape experiment's 31.0% is a DIFFERENT and harder question - it
      sieved on `claude sonnet 4.5`, the spaced form, which a document only
      contains if somebody wrote the model's name out. That is the figure the
      ranking rests on, so it is the one reproduced here.

      Both are reported. The loose one is labelled `any-form` and is a check on
      the query; the strict one is labelled `prose` and is the comparable
      number. Storing gates on the loose one, because a document naming the
      model only in its hyphenated form is still about that model.
    """
    prose = tuple(v for v in variants if " " in v) or tuple(variants)
    return SearchRequest(
        query=query,
        entry_label=f"shape-prose:{surface}",
        variants=tuple(
            RenderedTerms(subject=(v,), topic=(), signal=(), alias=v) for v in prose
        ),
        narrowing_token=None,
    )


def _plan(conn):
    """The requests, and the surface-to-model map the sieve needs."""
    by_model = seated_variants(conn)
    if not by_model:
        raise RuntimeError(
            "no rows in `model_alias`. A sweep over an empty alias table "
            "retrieves nothing and would report it as nobody discussing "
            "anything - run `registry load-tracked-set`."
        )
    surfaces: list[str] = []
    model_of: dict[str, str] = {}
    variants_of: dict[str, tuple[str, ...]] = {}
    for canonical_id, variants in by_model.items():
        for surface in variants:
            if surface not in model_of:
                surfaces.append(surface)
                model_of[surface] = canonical_id
                variants_of[surface] = tuple(variants)
    return by_model, surfaces, model_of, variants_of


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true", help="print the plan, issue nothing")
    mode.add_argument("--apply", action="store_true")
    ap.add_argument("--budget", type=int, default=None, help="cap on requests issued")
    ap.add_argument("--max-minutes", type=float, default=DEFAULT_MAX_MINUTES)
    ap.add_argument("--shapes", default=",".join(SWEEP_SHAPES))
    ap.add_argument("--json", default="docs/measurements/multi-shape-sweep.json")
    args = ap.parse_args()

    shapes = tuple(s.strip() for s in args.shapes.split(",") if s.strip())

    conn = connect()
    try:
        by_model, surfaces, model_of, variants_of = _plan(conn)
        # RAISES on `label`. Not filtered - see sweep_requests.
        planned = sweep_requests(tuple(surfaces), shapes=shapes, budget=args.budget)

        print("=" * 78)
        print("MULTI-SHAPE GITHUB SWEEP" + ("  (plan only)" if args.plan else ""))
        print("=" * 78)
        print(f"  seated models        {len(by_model)}")
        print(f"  distinct surfaces    {len(surfaces)}")
        print(f"  requests planned     {len(planned)}   "
              + ", ".join(f"{s}={n}" for s, n in
                          collections.Counter(r.shape for r in planned).items()))
        print(f"  shape order          {' then '.join(shapes)}  (shape-major)")
        print(f"  wall-clock ceiling   {args.max_minutes} min at 30 search req/min")
        print()
        print("  WHAT THIS DOES NOT BUY, stated first:")
        print("    the 18-request shape experiment returned ZERO signal hits and")
        print("    ZERO kept documents on all four shapes. This raises SUBJECT")
        print("    PRECISION - 31.0%/request on title against 17.0% on repro -")
        print("    and moves no claim, no voice and no cell. It is corpus.")
        print()

        if args.plan:
            for request in planned[:6]:
                print(f"    {request.rank:4d} {request.shape:6s} {request.query}")
            print(f"    ... {max(0, len(planned) - 6)} more")
            return 0

        return _run(conn, planned, model_of, variants_of, args)
    finally:
        conn.close()


def _run(conn, planned, model_of, variants_of, args) -> int:
    import httpx

    from collect.adapters.github import GitHubHarvester, QueryRun
    from collect.ops.ledger import close_harvest_run, open_harvest_run

    store = RawStore(settings().raw_store_path)
    token = settings().github_token
    if not token:
        print("  NO GITHUB_TOKEN. Refusing rather than issuing unauthenticated")
        print("  requests at 10/minute against a plan costed at 30.")
        return 1

    client = httpx.Client(
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": settings().user_agent,
        },
        timeout=30.0,
    )
    harvester = GitHubHarvester(client=client, store=store)

    started = time.monotonic()
    per_shape: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    ids_by_shape: dict[str, set[str]] = collections.defaultdict(set)
    stored_by_shape: dict[str, set[str]] = collections.defaultdict(set)
    new_to_corpus: dict[str, set[str]] = collections.defaultdict(set)
    issued = 0
    stopped_on_time = False
    errors: list[str] = []

    existing = {
        row[0]
        for row in conn.execute(
            "SELECT external_id FROM document WHERE source = 'github'"
        ).fetchall()
    }
    documents_before = conn.execute(
        "SELECT count(*) FROM document WHERE source = 'github'"
    ).fetchone()[0]

    for request in planned:
        if (time.monotonic() - started) / 60 >= args.max_minutes:
            stopped_on_time = True
            break

        variants = variants_of[request.surface]
        search_request = _subject_only_request(request.query, request.surface, variants)
        prose_request = _prose_request(request.query, request.surface, variants)
        run = QueryRun(request=search_request)

        opened = open_harvest_run(conn, harvester.harvest_run_fields(run))
        conn.commit()

        try:
            hits = harvester.search(search_request, run)
        except Exception as error:  # noqa: BLE001
            errors.append(f"{request.query}: {type(error).__name__}: {error}")
            run.finished_at = datetime.now(UTC)
            close_harvest_run(
                conn, opened, harvester.harvest_run_fields(run), outcome="error"
            )
            conn.commit()
            issued += 1
            continue

        issued += 1
        counts = per_shape[request.shape]
        counts["requests"] += 1
        counts["candidates"] += len(hits)

        survivors = []
        for hit in hits:
            verdict = search_request.sieve(hit.sieve_text)
            run.verdicts.append(verdict)
            ids_by_shape[request.shape].add(str(hit.external_id))
            # SUBJECT IS THE GATE. `verdict.passed` is necessarily False with
            # empty topic/signal groups, so the flag would drop everything; what
            # is asked is whether "subject" is among the groups that MISSED.
            on_subject = "subject" not in verdict.missing
            if on_subject:
                counts["subject_any_form"] += 1
                survivors.append(hit)
            # The comparable figure. Same document, spaced spellings only.
            if "subject" not in prose_request.sieve(hit.sieve_text).missing:
                counts["subject_prose"] += 1
            if "topic" not in verdict.missing:
                counts["topic"] += 1
            if "signal" not in verdict.missing:
                counts["signal"] += 1
            if not on_subject:
                run.rejected.append((hit.html_url, hit.title, verdict.missing))

        for hit in survivors:
            stored = harvester.fetch_issue(hit, run)
            if stored is not None:
                run.stored.append(stored)
                stored_by_shape[request.shape].add(str(hit.external_id))
                # A SET, NOT A COUNTER, AND THE COUNTER WAS WRONG. This read
                # `counts["new_to_corpus"] += 1`, which fires once per FETCH -
                # so a document retrieved by `claude-sonnet-4.5` and again by
                # `sonnet-4.5` counted twice. The first full run reported
                # `new 1,881` beside `unique 1,410` and `stored 1,145`, and a
                # count of documents cannot exceed the distinct documents it is
                # counting. The real figure is 1,145, which is what the
                # `document` table moved by.
                #
                # It is the same shape as everything else this sweep measures:
                # a per-request tally read as a per-document one. Caught only
                # because two numbers in one row contradicted each other.
                if str(hit.external_id) not in existing:
                    new_to_corpus[request.shape].add(str(hit.external_id))

        run.finished_at = datetime.now(UTC)
        written = harvester.write_documents(
            conn, run, harvest_run_id=opened.id
        )
        counts["inserted"] += written.get("inserted", 0)
        close_harvest_run(
            conn, opened, harvester.harvest_run_fields(run), outcome="ok"
        )
        conn.commit()

    client.close()

    documents_after = conn.execute(
        "SELECT count(*) FROM document WHERE source = 'github'"
    ).fetchone()[0]
    provenance = conn.execute(
        "SELECT retrieval_provenance, count(*) FROM document "
        "WHERE source = 'github' GROUP BY 1"
    ).fetchall()

    print(f"  requests issued      {issued} of {len(planned)}"
          + ("   STOPPED ON TIME" if stopped_on_time else ""))
    if errors:
        print(f"  errors               {len(errors)}")
        for line in errors[:5]:
            print(f"    {line}")
    print()
    print("  PER SHAPE. `unique` is documents this shape retrieved that no")
    print("  EARLIER shape did - the figure that decides an arm, because a shape")
    print("  that only re-finds what we have is worth nothing however well it")
    print("  scores. `label` was refused on exactly this: 21.7 on-subject per")
    print("  request against 9.7 unique.")
    print()
    print(f"    {'shape':8s} {'reqs':>5s} {'cands':>6s} {'any%':>6s} {'prose%':>7s} "
          f"{'topic':>5s} {'signal':>6s} {'stored':>6s} {'unique':>6s} {'new':>5s}")
    seen_earlier: set[str] = set()
    unique_by_shape: dict[str, int] = {}
    for shape in [s for s in SWEEP_SHAPES if s in per_shape]:
        c = per_shape[shape]
        unique = len(ids_by_shape[shape] - seen_earlier)
        unique_by_shape[shape] = unique
        seen_earlier |= ids_by_shape[shape]
        cands = max(c["candidates"], 1)
        print(f"    {shape:8s} {c['requests']:5d} {c['candidates']:6d} "
              f"{c['subject_any_form'] / cands:6.1%} {c['subject_prose'] / cands:7.1%} "
              f"{c['topic']:5d} {c['signal']:6d} {c['inserted']:6d} "
              f"{unique:6d} {len(new_to_corpus[shape]):5d}")
    print()
    print("  any%   = ANY spelling of the model appears. This is the STORE GATE")
    print("           and it is near-tautological on `title`: the query put the")
    print("           hyphenated surface in the title and the sieve does not")
    print("           strip hyphens, so it mostly confirms GitHub honoured the")
    print("           query. DO NOT quote it as precision.")
    print("  prose% = a SPACED spelling appears - somebody wrote the name out.")
    print("           This is the figure the shape ranking rests on and the one")
    print("           comparable to the experiment's title 31.0% / repro 17.0%.")
    print()
    print(f"  github documents  {documents_before} -> {documents_after}"
          f"   ({documents_after - documents_before:+d})")
    print("  retrieval_provenance on github rows:")
    for value, n in provenance:
        print(f"    {value:20s} {n:5d}")
    print()
    total_signal = sum(c["signal"] for c in per_shape.values())
    print(f"  SIGNAL HITS ACROSS THE WHOLE SWEEP: {total_signal}")
    print("  That is the number that decides what this bought. Signal is what")
    print("  the full sieve needs to KEEP a document, so a sweep with no signal")
    print("  hits enlarges the pool and produces no claim by itself.")

    out = {
        "requests_planned": len(planned),
        "requests_issued": issued,
        "stopped_on_time": stopped_on_time,
        "errors": errors,
        "shape_order": list(SWEEP_SHAPES),
        "per_shape": {s: dict(c) for s, c in per_shape.items()},
        "unique_documents_by_shape": unique_by_shape,
        "new_to_corpus_by_shape": {s: len(v) for s, v in new_to_corpus.items()},
        "new_to_corpus_note": (
            "DISTINCT documents not already in `document` when the run started. "
            "Was a per-fetch counter and double-counted a document retrieved by "
            "two surfaces - it reported 1,881 beside unique 1,410 and stored "
            "1,145, which cannot all be document counts. Cross-check it against "
            "github_documents_after - github_documents_before."
        ),
        "unique_note": (
            "documents this shape retrieved that no EARLIER shape did, in "
            "shape-major order. Not kept-per-shape: the sweep keeps on subject "
            "and the full sieve keeps nothing here."
        ),
        "signal_hits_total": total_signal,
        "github_documents_before": documents_before,
        "github_documents_after": documents_after,
        "retrieval_provenance": {v: n for v, n in provenance},
        "what_it_does_not_buy": (
            "zero signal hits means zero claims from this sweep alone. It "
            "raises subject precision and enlarges the extraction pool."
        ),
    }
    path = pathlib.Path(args.json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"\nwritten to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
