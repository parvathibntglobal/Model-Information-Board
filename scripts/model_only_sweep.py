"""A MODEL-ONLY Reddit sweep: subject in the query, nothing else.

WHAT THIS MEASURES, AND WHY THE THREE NUMBERS ARE THE POINT

`/getSearchPosts` with a bare alias. No topic token, no signal term — so the
query asks only *"who is talking about this model"*, and the sieve's three groups
are then RECORDED PER CANDIDATE WITHOUT GATING on topic or signal. Those three
counts on a model-only corpus are the output of this run regardless of what any
later stage does with the documents.

That is the opposite arrangement to `collect/ops/sweep.py`, which appends a
narrowing token, and to `collect/ops/sweep_reddit.py`, which issues no query at
all. Three shapes, one platform, and the comparison between them is the reason
this exists as a separate instrument rather than a flag on either.

WHAT IT STORES, AND THE ONE GATE IT DOES APPLY

Subject. A bare-alias query on Reddit is loose — there is no phrase operator and
it degrades to OR over tokens — so a post can come back without naming the model
at all. Storing those would put documents in the corpus that no model claim can
ever attach to. So: **candidates are every post returned; stored are the posts
whose subject verifies locally**, and both numbers are reported. Topic and signal
are recorded on every candidate and gate nothing.

SIX OF THE ELEVEN MODELS HAVE NO REGISTRY ALIASES

`model_alias` holds 105 rows over 41 of 342 models. For a model with no alias row
this derives a RUN-LOCAL surface from `model_version.display_name`, which is the
provider's own name as polled — `Claude Fable 5`, `GPT-5.6 Sol Pro`. It is not
written to `model_alias`: the registry does not gain unprovenanced rows because a
measurement needed a string. The report says which models were queried from the
registry and which from a run-local surface, because a yield figure that mixes
them silently is a figure about two different things.

    python scripts/model_only_sweep.py --pages 7 --out run.jsonl
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re

from collect.adapters.queries import load_queries
from collect.adapters.queries.sieve import author_prose, matches, normalize
from collect.adapters.reddit import build_client, harvester_for_source
from collect.adapters.reddit_write import write_documents
from collect.config import settings
from collect.ops.ledger import close_harvest_run, open_harvest_run
from collect.rawstore import RAW, RawStore
from collect.registry.sources import load_sources

#: The eleven, by canonical id. A LIST RATHER THAN A QUERY, because this run is
#: about these models and a filter that silently returned ten would be
#: indistinguishable from a sweep that found nothing for one of them.
MODELS = (
    "anthropic/claude-fable-5",
    "anthropic/claude-haiku-4.5",
    "anthropic/claude-opus-4.6",
    "anthropic/claude-opus-4.8",
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-sonnet-5",
    "google/gemini-3.7-flash",
    "openai/gpt-5.6-luna",
    "openai/gpt-5.6-sol",
    "openai/gpt-5.6-sol-pro",
    "qwen/qwen3.8-27b",
)

#: Vendor prefix in `display_name`. Stripped for the run-local surface: nobody
#: writes "Anthropic: Claude Fable 5" in a Reddit post.
_VENDOR = re.compile(r"^[A-Za-z][A-Za-z0-9 .]*:\s*")

#: `run_recorded` requires the id on the row and
#: `document_retrieval_provenance_agrees_ck` enforces it. A query-issuing sweep
#: that opens a `harvest_run` row is exactly that case.
PROVENANCE = "run_recorded"

#: Where a surface's documents land when the LEDGER WRITE FAILED. A query was
#: rendered, its id never reached the writer: `not_recorded`, not
#: `no_run_for_source`, which would claim there had been nothing to record.
PROVENANCE_WITHOUT_LEDGER = "not_recorded"


def all_derived_forms(conn) -> list[tuple[str, str, str]]:
    """Every form `propose.py` derives, for all eleven. The CORRECTED surface set.

    Run-local again, and deliberately: seating these needs a reviewed manifest
    with a content hash per seat, and `tracked_load.read_manifest` requires
    `reviewed_by` — a person. Adding forms to an already-seated model changes its
    artifact and therefore invalidates the hash its existing review is bound to,
    which is the guard working rather than an obstacle. So the MEASUREMENT runs on
    derived surfaces and the registry write waits for the review.
    """
    from collect.registry.propose import mechanical_variants, rule_variants

    cur = conn.cursor()
    cur.execute(
        "SELECT canonical_id, display_name FROM model_version "
        "WHERE canonical_id = ANY(%s)",
        (list(MODELS),),
    )
    display = dict(cur.fetchall())
    cur.execute(
        "SELECT mv.canonical_id, a.surface FROM model_version mv "
        "JOIN model_alias a ON a.model_version_id = mv.id "
        "WHERE mv.canonical_id = ANY(%s)",
        (list(MODELS),),
    )
    seated: dict[str, set[str]] = {}
    for canonical, surface in cur.fetchall():
        seated.setdefault(canonical, set()).add(surface)

    out: list[tuple[str, str, str]] = []
    for canonical in MODELS:
        name = display.get(canonical) or ""
        forms = sorted(set(mechanical_variants(canonical, name)
                           + rule_variants(canonical, name)))
        for form in forms:
            # A canonical id is not something a person types. Dropped for the
            # same reason `surfaces_for` drops it: it costs a request and returns
            # the corpus or nothing.
            if "/" in form:
                continue
            origin = "seated" if form in seated.get(canonical, ()) else "derived-new"
            out.append((canonical, form, origin))
    return out


def surfaces_for(conn) -> list[tuple[str, str, str]]:
    """`[(canonical_id, surface, origin)]` for the eleven. Registry first."""
    cur = conn.cursor()
    cur.execute(
        "SELECT mv.canonical_id, mv.display_name, a.surface "
        "FROM model_version mv "
        "LEFT JOIN model_alias a ON a.model_version_id = mv.id "
        "WHERE mv.canonical_id = ANY(%s) ORDER BY 1, 3",
        (list(MODELS),),
    )
    by_model: dict[str, dict] = {}
    for canonical, display, surface in cur.fetchall():
        entry = by_model.setdefault(canonical, {"display": display, "surfaces": []})
        if surface:
            entry["surfaces"].append(surface)

    out: list[tuple[str, str, str]] = []
    for canonical in MODELS:
        entry = by_model.get(canonical)
        if entry is None:
            out.append((canonical, canonical.split("/")[-1], "MISSING-FROM-REGISTRY"))
            continue
        if entry["surfaces"]:
            # `anthropic/claude-haiku-4.5` as a SURFACE is a canonical id, not
            # something a person types. Dropped: it costs a request and returns
            # the corpus or nothing.
            for surface in entry["surfaces"]:
                if "/" in surface:
                    continue
                out.append((canonical, surface, "registry"))
        else:
            display = _VENDOR.sub("", entry["display"] or "").strip()
            if display:
                out.append((canonical, display, "run-local"))
    return out


def _term_sets(conn):
    """Every renderable entry rendered against every surface, per surface."""
    entries = [
        e for e in load_queries().all_entries if not e.direction_from_extraction
    ]
    return entries


def verdicts_for(text: str, subject_terms, entries, surface):
    """`(subject, topic, signal)` booleans. RECORDED, never used to gate here."""
    haystack = normalize(text)
    prose = normalize(author_prose(text))
    subject = all(matches(t, haystack) for t in subject_terms)
    topic = signal = False
    for entry in entries:
        rendered = entry.terms.substitute(surface)
        if any(matches(t, haystack) for t in rendered.topic):
            topic = True
        if any(matches(t, prose) for t in rendered.signal):
            signal = True
    return subject, topic, signal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=7)
    parser.add_argument("--sort", default="RELEVANCE")
    parser.add_argument("--out", default="model_only_sweep.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--all-forms", action="store_true",
        help="query EVERY form propose.py derives, not just the seated surface. "
             "This is the corrected surface set — see all_derived_forms.",
    )
    args = parser.parse_args()

    contract = load_sources()
    reddit = next((s for s in contract.platforms if s["id"] == "reddit"), None)
    if reddit is None:
        raise SystemExit("contract/sources.yaml has no reddit source row")

    from collect.db import transaction

    with transaction() as conn:
        plan = all_derived_forms(conn) if args.all_forms else surfaces_for(conn)
        entries = _term_sets(conn)

    per_minute = 25
    print(f"plan     : {len(plan)} surface(s) x {args.pages} page(s) "
          f"= {len(plan) * args.pages} request(s)")
    print(f"           wall clock ~{len(plan) * args.pages * 60 / per_minute / 60:.1f} "
          f"minutes at {per_minute}/min, against a 35-minute contract ceiling")
    print(f"           quota {len(plan) * args.pages} of 1,000,000 "
          f"({100 * len(plan) * args.pages / 1_000_000:.3f}%)")
    print(f"           candidates offered: up to {len(plan) * args.pages * 25}")
    origins: dict[str, int] = {}
    for _, _, origin in plan:
        origins[origin] = origins.get(origin, 0) + 1
    print(f"           surfaces by origin: {origins}")
    for canonical, surface, origin in plan:
        print(f"             {canonical:<32} {surface:<26} {origin}")
    if args.dry_run:
        print("           (plan only - no terms gate, no writes)")
        return 0

    store = RawStore(settings().raw_store_path)
    rows: list[dict] = []
    totals = {"candidates": 0, "subject": 0, "topic": 0, "signal": 0,
              "stored": 0, "requests": 0, "opened": 0, "closed": 0}
    quota_remaining = None

    with build_client() as client, transaction() as conn:
        from collect.cli import _gate

        _gate(conn)
        harvester = harvester_for_source(
            reddit, rulings=contract.rulings, client=client,
            store=store, max_pages=args.pages,
        )
        print("gate     : reddit terms reviewed and re-verified, harvest permitted")

        for canonical, surface, origin in plan:
            run = harvester.search(surface, sort=args.sort)
            totals["requests"] += run.pages_fetched
            if run.quota_remaining is not None:
                quota_remaining = run.quota_remaining

            opened = None
            try:
                opened = open_harvest_run(
                    conn, {**run.harvest_run_fields(), "source_id": "reddit"}
                )
                conn.commit()
                totals["opened"] += 1
            except Exception as error:  # noqa: BLE001
                print(f"  ledger open failed for {surface!r}: {error}")
                conn.rollback()

            subject_terms = entries[0].terms.substitute(surface).subject
            keep = []
            for post in run.posts:
                text = post.sieve_text
                subj, top, sig = verdicts_for(text, subject_terms, entries, surface)
                totals["candidates"] += 1
                totals["subject"] += subj
                totals["topic"] += top
                totals["signal"] += sig
                rows.append({
                    "canonical_id": canonical, "surface": surface, "origin": origin,
                    "external_id": post.external_id, "subreddit": post.subreddit,
                    "url": post.url, "title": post.title,
                    "subject": subj, "topic": top, "signal": sig,
                })
                if subj:
                    keep.append(post)

            refs = {}
            for post in keep:
                # THE DOCUMENT'S TEXT, NOT ITS PAYLOAD. `document.text_ref` is
                # where the document's TEXT lives; the API payload lives in the
                # `raw` namespace and the search page already holds it, so
                # nothing is lost by not storing it twice.
                #
                # This stored `json.dumps(post.raw)` until 2026-08-28, which made
                # `text_ref` point at a JSON envelope. `assemble_*` passes that
                # straight to `flatten`, so the thread_context would have held
                # JSON - and a quote would then verify against a field VALUE,
                # which is worse than failing to verify: it is rule 1 returning
                # true for the wrong reason.
                text = (post.title or "") + chr(10) * 2 + (post.selftext or "")
                stored = store.put(text.encode("utf-8"), namespace=RAW)
                refs[post.external_id] = (stored.ref, stored.content_hash)
            wrote = write_documents(
                conn, keep,
                retrieval_provenance=(
                    PROVENANCE if opened is not None else PROVENANCE_WITHOUT_LEDGER
                ),
                harvest_run_id=opened.id if opened is not None else None,
                refs=refs,
            )
            conn.commit()
            totals["stored"] += wrote["documents_inserted"]

            if opened is not None:
                try:
                    close_harvest_run(
                        conn, opened,
                        {**run.harvest_run_fields(), "source_id": "reddit"},
                        outcome="error" if run.http_errors else "ok",
                    )
                    conn.commit()
                    totals["closed"] += 1
                except Exception as error:  # noqa: BLE001
                    print(f"  ledger close failed for {surface!r}: {error}")
                    conn.rollback()
            print(f"  {surface:<26} {len(run.posts):4d} candidates  "
                  f"{len(keep):4d} subject  {wrote['documents_inserted']:4d} stored")

    out = pathlib.Path(args.out)
    with out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    n = totals["candidates"] or 1
    print("\nsweep    : MODEL-ONLY. Subject in the query; no topic, no signal.")
    print(f"           {totals['requests']} requests over {len(plan)} surfaces")
    print(f"           {totals['candidates']} candidates, {totals['stored']} stored "
          f"(subject-verified only)")
    print("           THE THREE NUMBERS, over "
          f"{totals['candidates']} candidates - topic and signal gated NOTHING:")
    print(f"             subject  {totals['subject']:5d}  ({100 * totals['subject'] / n:5.1f}%)")
    print(f"             topic    {totals['topic']:5d}  ({100 * totals['topic'] / n:5.1f}%)")
    print(f"             signal   {totals['signal']:5d}  ({100 * totals['signal'] / n:5.1f}%)")
    print(f"           harvest_run: {totals['opened']} opened, {totals['closed']} closed")
    if quota_remaining is not None:
        print(f"           quota remaining: {quota_remaining}")
    print(f"           per-candidate verdicts: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
