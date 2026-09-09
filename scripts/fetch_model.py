#!/usr/bin/env python
"""Per-model fresh fetch — the evidence pipeline for ONE model, on demand.

Composition root: harvest is `collect/`'s, extraction is `judge/`'s, and only a
script outside both lanes may import both. The backend invokes this as a
SUBPROCESS (never an import) when the user clicks Fetch, so neither lane imports
the other. Nothing runs on its own — a fetch happens only on a click.

APPEND-ONLY, AND THAT IS LOAD-BEARING. This runs against the shared database, so:
  - it NEVER drops the schema (the sibling probe `harvest_github.py` does, which
    is exactly why that one cannot be reused here),
  - every document write is `ON CONFLICT DO NOTHING` (github.py:612),
  - curation, when wired, is SCOPED to the fetched model — never `rebuild_all`,
    which would recompute every other model's cells.
Nothing that already exists is edited or removed; a fetch only adds this model's
rows.

PROGRESS is written per stage to `var/fetch/<run_id>.jsonl` (local, gitignored).
The model page's fetch log polls it, so "which stage, what counts" is visible as
it happens rather than reconstructed after.

    python scripts/fetch_model.py <model_version_id> [--run-id ID] [--fetch-cap N]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import time
import traceback
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collect.adapters.github import GitHubHarvester  # noqa: E402
from collect.adapters.queries import load_queries, plan_searches  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.http import build_client  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.registry.aliases import alias_rows  # noqa: E402
from collect.registry.assertions import assert_terms_reviewed  # noqa: E402
from collect.registry.seed import seed_models  # noqa: E402
from collect.registry.sources import load_sources  # noqa: E402

# The GitHub repos the sweep scopes to — the same set the probe uses, so the
# search space is the one that has actually returned model discussion before.
SCOPE = (
    "repo:langchain-ai/langchain",
    "repo:run-llama/llama_index",
    "repo:Aider-AI/aider",
    "repo:microsoft/autogen",
    "repo:crewAIInc/crewAI",
)
CAPABILITIES = (
    "tool_calling.schema_accuracy",
    "summarization.fidelity",
    "context.effective_window",
)

FETCH_DIR = ROOT / "var" / "fetch"

#: An on-demand fetch must stay responsive, and extraction is one LLM call per
#: thread whose latency scales with the prompt. A 45-comment thread produced a
#: ~13-minute E5 with no visible progress. Threads larger than this are DEFERRED
#: to the nightly batch (which is uncapped) rather than read on a click; the cap
#: is generous, so only pathologically large threads are held back.
MAX_FETCH_THREAD_CHARS = 30_000


class Progress:
    """One run's per-stage log. Append-only JSONL the fetch view tails."""

    def __init__(self, run_id: str, model_version_id: str) -> None:
        FETCH_DIR.mkdir(parents=True, exist_ok=True)
        self.path = FETCH_DIR / f"{run_id}.jsonl"
        self.run_id = run_id
        self._write({"kind": "run", "run_id": run_id,
                     "model_version_id": model_version_id, "at": _now()})

    def _write(self, rec: dict) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def stage(self, id_: str, name: str, status: str, **fields) -> None:
        # status: running | ok | skipped | error. Counts and detail ride along
        # so the log line is a finding, not just a heartbeat.
        self._write({"kind": "stage", "id": id_, "name": name,
                     "status": status, "at": _now(), **fields})

    def done(self, status: str, detail: str = "") -> None:
        self._write({"kind": "end", "status": status, "detail": detail, "at": _now()})


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _variants_for(conn, model_version_id: str, canonical_id: str) -> list[str]:
    """Search variants for this model, from the append-only `model_alias` table.

    Falls back to the seed model's computed aliases when the model is one of the
    seeds and carries no alias rows yet. Read-only.
    """
    # `search_eligible` is a Python field on AliasRow, not a DB column. In the
    # table, a variant is searchable when it names a version or snapshot (a bare
    # `family` form like "sonnet" names a line, not a model) and is still current
    # (`valid_until IS NULL`, since model_alias is append-only, FR-4).
    rows = conn.execute(
        "SELECT variants FROM model_alias "
        "WHERE model_version_id = %s "
        "AND specificity IN ('version', 'snapshot') "
        "AND valid_until IS NULL",
        (model_version_id,),
    ).fetchall()
    variants: set[str] = set()
    for (vs,) in rows:
        for v in (vs or []):
            variants.add(v)
    if not variants:
        seed = next((m for m in seed_models() if m.canonical_id == canonical_id), None)
        if seed is not None:
            for r in alias_rows(seed):
                if r.search_eligible:
                    variants.update(r.variants)
    return sorted(variants)


def _ensure_github_source(conn) -> None:
    """Make sure the `github` source row exists — WITHOUT touching it if it does.

    `ON CONFLICT DO NOTHING`, so a fetch on a database that already has the row
    (the shared one does) changes nothing; a fresh database gets it once.
    """
    from psycopg.types.json import Json

    contract = load_sources()
    gh = next(s for s in contract.platforms if s["id"] == "github")
    conn.execute(
        "INSERT INTO source (id, platform, endpoint, base_trust, tos_notes, provenance,"
        " terms_ruling, terms_checked_on, terms_evidence)"
        " VALUES ('github','github','https://api.github.com',0.95,%s,'seed',%s,%s,%s)"
        " ON CONFLICT (id) DO NOTHING",
        (gh["tos_notes"], gh["terms_ruling"], gh["terms_evidence"]["checked_on"],
         Json({k: str(v) for k, v in gh["terms_evidence"].items()})),
    )
    conn.commit()


def harvest_github(conn, prog: Progress, variants: list[str], *, fetch_cap: int) -> int:
    """E2 harvest — live GitHub search for this model, appended to `document`.

    The terms gate runs first (the same one the nightly path runs), then the
    proven adapter loop: plan, harvest, `write_documents` (ON CONFLICT). Bounded
    by `fetch_cap` so an on-demand click cannot run away against the rate limit.
    Returns the number of documents newly inserted.
    """
    from datetime import UTC, datetime

    contract = load_sources()
    gh = next(s for s in contract.platforms if s["id"] == "github")
    assert_terms_reviewed([gh], rulings=contract.rulings,
                          observations={"github": {"access_path": "api"}},
                          today=datetime.now(UTC).date())

    entries = [e for cap in CAPABILITIES for e in load_queries().for_capability(cap)]
    plan = plan_searches(entries, variants, scope=SCOPE)
    prog.stage("E2", "Harvest", "running",
               variants=len(variants), planned_requests=plan.request_count,
               detail=f"GitHub search for {len(variants)} name variants "
                      f"× {len(entries)} capability queries")

    client = build_client(timeout=30.0, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {settings().github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    harvester = GitHubHarvester(
        client=client, store=RawStore(Path(settings().raw_store_path)),
        max_pages=1, max_fetch_per_query=15,
    )
    _ensure_github_source(conn)

    fetched = inserted = kept = candidates = 0
    for req in plan.requests:
        if fetched >= fetch_cap:
            prog.stage("E2", "Harvest", "running",
                       detail=f"fetch cap of {fetch_cap} requests reached, stopping")
            break
        run = harvester.harvest(req)
        wrote = harvester.write_documents(conn, run)
        conn.commit()
        fetched += run.rest_calls
        inserted += wrote["inserted"]
        kept += run.sieve_yield.kept
        candidates += run.sieve_yield.candidates
    prog.stage("E2", "Harvest", "ok",
               requests_spent=fetched, sieve_kept=kept, sieve_candidates=candidates,
               documents_inserted=inserted,
               detail=f"{inserted} new document(s) appended; "
                      f"{kept} of {candidates} passed the sieve")
    return inserted


def _write_rapidapi_quota(remaining: int | None, limit: int | None, run_id: str) -> None:
    """Persist the latest RapidAPI quota HEADER reading for the admin page.

    RapidAPI bills the Reddit path as a request quota, and the remaining/limit
    arrive in `x-ratelimit-*` response headers. This writes the RAW reading, not
    a recompute, so the admin page shows the provider's OWN number cached with
    its date rather than a second source of truth. It is shown 'as of' that date,
    because the quota moves only when a fetch runs and a dated reading on a live
    dashboard would otherwise read as current.

    Written from this per-model fetch. The nightly Reddit sweep can write the
    same file with one line so the figure also moves without a manual fetch.
    """
    if remaining is None and limit is None:
        return  # nothing was read; do not overwrite a good reading with a blank
    path = ROOT / "var" / "rapidapi-quota.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"quota_remaining": remaining, "quota_limit": limit,
           "at": _now(), "source_run_id": run_id}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(rec), encoding="utf-8")
    tmp.replace(path)  # atomic, so a concurrent read never sees a half-written file


def harvest_reddit(conn, prog: Progress, variants: list[str], *, max_searches: int,
                   max_threads: int) -> int:
    """E2 harvest — live Reddit search (RapidAPI) for this model, WITH comments.

    A post with no comments is refused by the assembler ("the blog shape, not a
    Reddit thread"), so posts-only harvesting produces nothing usable. This
    searches the top `max_searches` variants, then fetches the comment tree for
    the top posts up to `max_threads` — writing `[post, *comments]` so a real
    thread assembles. Bounded on BOTH axes because Reddit 429s at ~32 rapid
    calls: roughly max_searches + max_threads requests total. Append-only.
    """
    from collect.adapters.reddit import build_client, harvester_for_source
    from collect.adapters.reddit_write import write_documents as reddit_write
    from collect.ids import content_hash

    contract = load_sources()
    reddit_src = next(s for s in contract.platforms if s.get("id") == "reddit")
    store = RawStore(Path(settings().raw_store_path))
    queries = variants[:max_searches]
    prog.stage("E2R", "Harvest · Reddit", "running", queries=len(queries),
               detail=f"RapidAPI search for {len(queries)} variant(s), then comments "
                      f"for up to {max_threads} thread(s)")

    inserted = hits = threads = 0
    q_remaining = q_limit = None  # latest RapidAPI quota header seen this fetch
    with build_client() as client:
        searcher = harvester_for_source(reddit_src, client=client, store=store)
        for variant in queries:
            if threads >= max_threads:
                break
            run = searcher.search(variant)
            if run.quota_remaining is not None:
                q_remaining = run.quota_remaining
            if run.quota_limit is not None:
                q_limit = run.quota_limit
            hits += len(run.posts)
            for post in run.posts:
                if threads >= max_threads:
                    break
                fetch = searcher.fetch_comments(post)
                # A comment fetch is a metered call, so its quota reading is as
                # fresh as a search's — take the latest either reports.
                if getattr(fetch, "quota_remaining", None) is not None:
                    q_remaining = fetch.quota_remaining
                if getattr(fetch, "quota_limit", None) is not None:
                    q_limit = fetch.quota_limit
                if getattr(fetch, "not_a_thread", False) or not getattr(fetch, "comments", None):
                    continue  # a post with no comments will not assemble
                items = [post, *fetch.comments]
                refs = {post.external_id:
                        (store.put(post.sieve_text).ref, content_hash(post.sieve_text))}
                for c in fetch.comments:
                    body = getattr(c, "body", "") or ""
                    refs[c.external_id] = (store.put(body).ref, content_hash(body))
                # This is the model-name SEARCH arm: a query was issued but no
                # harvest_run row was opened, so `not_recorded` is the honest
                # provenance — reddit_write.py:147 names this exact caller. The
                # argument became required when retrieval_provenance merged, and
                # this call site was not updated with it.
                wrote = reddit_write(
                    conn, items, refs=refs, retrieval_provenance="not_recorded"
                )
                conn.commit()
                inserted += int(wrote.get("documents_inserted", 0) or 0)
                threads += 1
    _write_rapidapi_quota(q_remaining, q_limit, prog.run_id)
    prog.stage("E2R", "Harvest · Reddit", "ok",
               search_hits=hits, threads_fetched=threads, documents_inserted=inserted,
               quota_remaining=q_remaining, quota_limit=q_limit,
               detail=f"{threads} thread(s) with comments fetched, {inserted} document(s) appended")
    return inserted


def _gated_harvester(platform_id: str, factory, **kwargs):
    """Build a harvester through the adapter's OWN gate. Returns (h, why-not).

    EVERY ADAPTER PUBLISHES `harvester_for_source`, and it is the entry point
    anything that fetches must use. This lane learned that the expensive way:
    the Reddit path once had no such entry point, a 1,297-post corpus was
    gathered without the gate ever being asked, and the gate had been refusing
    Reddit correctly the whole time — nothing consulted it.

    So this does NOT call `assert_terms_reviewed` itself. It cannot: each ruling
    names its own live preconditions — `use_basis` for arXiv, and for X also
    `scraper_provider`, `credential_present` and an `access_path` of
    `rapidapi-reseller` — and only the adapter can observe them. A generic
    observation passed from here would be an observation NOBODY MADE wearing the
    costume of one that passed, which is precisely what rule 6 refuses.

    A platform absent from `contract/sources.yaml` is UNASSESSED, not refused,
    and the two must not render alike.
    """
    contract = load_sources()
    source = next((s for s in contract.platforms if s.get("id") == platform_id), None)
    if source is None:
        return None, (
            f"{platform_id} has no entry in contract/sources.yaml, so its terms have "
            "never been reviewed. Not refused — unassessed. Adding one is a contract "
            "change (two eyes), never something a fetch may assume for itself."
        )
    try:
        return factory(source, rulings=contract.rulings, **kwargs), ""
    except Exception as exc:
        return None, str(exc).splitlines()[0][:180]


def harvest_arxiv(conn, prog: Progress, variants: list[str], *, max_queries: int) -> int:
    """E2 harvest — arXiv search for this model, appended to `document`.

    Papers are the one source here that is CITED rather than reported. An author
    writing about a model is not an engineer reporting their own run, so what
    lands extracts as `relayed-from-elsewhere` and is weighted accordingly. It is
    harvested anyway because a paper naming a measurement is exactly the figure
    the metric pages want, and it arrives with a citation attached.
    """
    from collect.adapters.arxiv import harvester_for_source

    harvester, why = _gated_harvester(
        "arxiv", harvester_for_source,
        client=build_client(timeout=30.0),
        store=RawStore(Path(settings().raw_store_path)),
        max_pages=1,
    )
    if harvester is None:
        prog.stage("E2A", "Harvest · arXiv", "skipped", detail=why)
        return 0

    queries = variants[:max_queries]
    prog.stage("E2A", "Harvest · arXiv", "running", queries=len(queries),
               detail=f"arXiv search for {len(queries)} name variant(s)")
    inserted = papers = 0
    for variant in queries:
        run = harvester.search(variant)
        for paper in list(getattr(run, "papers", []) or [])[:5]:
            harvester.fetch_paper(paper, run)
        papers += len(getattr(run, "stored", []) or [])
        wrote = harvester.write_documents(conn, run, retrieval_provenance="not_recorded")
        conn.commit()
        inserted += int(getattr(wrote, "inserted", 0) or 0)
    prog.stage("E2A", "Harvest · arXiv", "ok", papers=papers, documents_inserted=inserted,
               detail=f"{papers} paper(s) stored, {inserted} document(s) appended")
    return inserted


def harvest_x(conn, prog: Progress, variants: list[str], *, max_queries: int) -> int:
    """E2 harvest — X search for this model, appended to `document`.

    IT SHARES THE RAPIDAPI KEY, AND THEREFORE THE QUOTA, WITH REDDIT. Running
    both arms in one fetch spends one budget twice, which is why this is capped
    harder than the Reddit arm and why the admin usage panel shows the two paths
    against a single remaining figure rather than two independent ones.

    `harvester_for_source` runs the ToS gate and THEN the credential, so a
    missing `RAPIDAPI_KEY` arrives here as a refusal to build rather than as a
    request that fails midway. Both are reported as `skipped` with the reason:
    neither is a fault of this run, and an error badge would say it was.
    """
    from collect.adapters.x import harvester_for_source

    harvester, why = _gated_harvester(
        "x", harvester_for_source,
        client=build_client(timeout=30.0),
        store=RawStore(Path(settings().raw_store_path)),
        max_pages=1,
    )
    if harvester is None:
        prog.stage("E2X", "Harvest · X", "skipped", detail=why)
        return 0

    queries = variants[:max_queries]
    prog.stage("E2X", "Harvest · X", "running", queries=len(queries),
               detail=f"X search for {len(queries)} variant(s) — shares the Reddit quota")
    inserted = posts = 0
    for variant in queries:
        run = harvester.search(variant)
        posts += len(getattr(run, "posts", []) or [])
        wrote = harvester.write_documents(conn, run, retrieval_provenance="not_recorded")
        conn.commit()
        inserted += int(getattr(wrote, "inserted", 0) or 0)
    prog.stage("E2X", "Harvest · X", "ok", posts=posts, documents_inserted=inserted,
               detail=f"{posts} post(s) seen, {inserted} document(s) appended")
    return inserted


#: The platforms that share one harvest shape: gate through
#: `harvester_for_source`, run `harvest(query, terms)` end to end, then
#: `write_documents`. Kept as data because the loop below is identical for each,
#: and three copies of one loop is three places to apply the next change twice.
#:
#: `stage` ids are distinct so the fetch log reads as a list of sources rather
#: than one repeated line, and `cap` is per-platform because their costs differ:
#: a Hugging Face harvest walks repos then discussions then comments, so it is
#: bounded hardest.
UNIFORM_PLATFORMS = (
    ("devto",       "E2D", "Harvest · dev.to",       2),
    ("hackernews",  "E2H", "Harvest · Hacker News",  2),
    ("huggingface", "E2F", "Harvest · Hugging Face", 1),
)


def _harvester_factory(platform_id: str):
    """The adapter's own gate-and-build entry point, imported lazily.

    Lazy because importing every adapter costs a fetch that skips them nothing,
    and because an adapter that fails to import must not take the whole run down
    with it - it is one source, and the others are still readable.
    """
    if platform_id == "devto":
        from collect.adapters.devto import harvester_for_source
    elif platform_id == "hackernews":
        from collect.adapters.hackernews import harvester_for_source
    elif platform_id == "huggingface":
        from collect.adapters.huggingface import harvester_for_source
    else:
        raise ValueError(f"no uniform factory for {platform_id!r}")
    return harvester_for_source


def harvest_uniform(conn, prog: Progress, variants: list[str], *,
                    platform_id: str, stage_id: str, stage_name: str,
                    max_queries: int) -> int:
    """E2 harvest for one of the uniform platforms, appended to `document`.

    The terms gate is the ADAPTER'S, never this script's. Each ruling names its
    own live preconditions and only the adapter observes them; a guessed
    observation passed from here would be an observation nobody made wearing the
    costume of one that passed, which is what the check exists to refuse.

    A platform missing from `contract/sources.yaml` is UNASSESSED rather than
    refused, and says so - those are different states and must not render alike
    (rule 6).
    """
    harvester, why = _gated_harvester(
        platform_id, _harvester_factory(platform_id),
        client=build_client(timeout=30.0),
        store=RawStore(Path(settings().raw_store_path)),
    )
    if harvester is None:
        prog.stage(stage_id, stage_name, "skipped", detail=why)
        return 0

    queries = variants[:max_queries]
    prog.stage(stage_id, stage_name, "running", queries=len(queries),
               detail=f"{platform_id} search for {len(queries)} name variant(s)")
    inserted = 0
    for variant in queries:
        run = harvester.harvest(variant)
        wrote = harvester.write_documents(conn, run, retrieval_provenance="not_recorded")
        conn.commit()
        inserted += int(getattr(wrote, "inserted", 0) or 0)
    prog.stage(stage_id, stage_name, "ok", documents_inserted=inserted,
               detail=f"{inserted} document(s) appended from {len(queries)} query(ies)")
    return inserted


def assemble_stage(conn, prog: Progress) -> None:
    """E3 — flatten this fetch's new documents into thread_context rows.

    Runs the collect assemblers over unassembled documents. Documents whose raw
    payload is not in THIS machine's store (anything harvested elsewhere) are
    skipped by the assemblers; the ones this fetch just harvested are local, so
    they are what actually get flattened. Append-only.
    """
    from collect.assemble.issue import assemble_github_documents
    from collect.assemble.platforms import PLATFORMS, assemble_platform_documents
    from collect.assemble.reddit import assemble_reddit_documents

    store = RawStore(Path(settings().raw_store_path))
    prog.stage("E3", "Assemble", "running", detail="flattening new documents into threads")
    notes = []
    # GitHub and Reddit keep their own drivers; the five newer platforms share
    # one. Without this the newer harvests wrote `document` rows that never
    # became a `thread_context`, so extraction never saw them and every stage
    # still reported success — the harvest cost requests and could not reach
    # the board.
    stages = [("github", assemble_github_documents), ("reddit", assemble_reddit_documents)]
    stages += [
        (src, (lambda conn_, *, store, limit=None, _s=src:
               assemble_platform_documents(conn_, source=_s, store=store, limit=limit)))
        for src in PLATFORMS
    ]
    for name, fn in stages:
        try:
            report = fn(conn, store=store, limit=200)
            conn.commit()
            notes.append(f"{name}: {report.summary()}")
        except Exception as exc:
            conn.rollback()
            notes.append(f"{name}: skipped ({str(exc).splitlines()[0][:80]})")
    # WHAT ASSEMBLY DID NOT SEE, counted rather than inferred. A NULL verdict
    # excludes a document (unjudged is not passed), so a triage that failed
    # halfway would quietly shrink the corpus and the only visible symptom would
    # be a smaller number here. Naming it makes the cause readable.
    unjudged = conn.execute(
        "SELECT count(*) FROM document WHERE triage_verdict IS NULL"
    ).fetchone()[0]
    if unjudged:
        notes.append(
            f"{unjudged} document(s) NOT assembled: no triage verdict yet, and "
            "unjudged is not passed"
        )
    prog.stage("E3", "Assemble", "ok", unjudged_documents=unjudged,
               detail=" · ".join(notes))


def build_thread_inputs(conn, seen, *, limit: int):
    """ThreadInputs for threads this fetch can actually read — the E5 input.

    This is the composition-root stand-in for the deferred RawTextResolver (#6):
    the store reader lives in collect/, judge/ may not import it, but a script
    outside both lanes may. A thread whose flattened payload is not in the local
    store (harvested elsewhere) raises on read and is skipped — so this naturally
    scopes to the threads this fetch just harvested and assembled.
    """
    from judge.extract.runner import ThreadInput
    from judge.extract.verify import OffsetMapping

    store = RawStore(Path(settings().raw_store_path))
    # ── THE TRIAGE VERDICT HAS TO BITE HERE OR IT IS DECORATIVE ──────────────
    # This query used to read every thread_context regardless of what E4 decided,
    # so a document could be gated as a bot post, a bare link or too short, have
    # its verdict written to `document.status`, and still be handed to the LLM.
    # The gates ran and changed nothing.
    #
    # A thread survives if ANY member survived. Per-MEMBER exclusion - dropping
    # one filtered comment and keeping the thread - is deliberately not done
    # here: the offset_map is built over the whole flattening, so removing a
    # member means rebuilding it, and a stale map silently resolves quotes to the
    # wrong document. That is the same refinement the pre-LLM screen defers, and
    # it must be done in the assembler or not at all.
    rows = conn.execute(
        "SELECT tc.id, tc.flattened_text_ref, tc.offset_map, tc.member_document_ids "
        "FROM thread_context tc "
        "WHERE EXISTS (SELECT 1 FROM document d "
        "              WHERE d.id = ANY(tc.member_document_ids) "
        "                AND d.status = 'kept' AND d.triage_verdict = 'kept') "
        "ORDER BY tc.assembled_at DESC LIMIT %s",
        (limit,),
    ).fetchall()
    # What the verdict cost, counted rather than inferred: a thread with no
    # surviving member is one E4 removed, and a run that cannot say how many did
    # not survive cannot tell a strict gate from an empty harvest.
    gated_out = conn.execute(
        "SELECT count(*) FROM thread_context tc "
        "WHERE NOT EXISTS (SELECT 1 FROM document d "
        "                  WHERE d.id = ANY(tc.member_document_ids) "
        "                    AND d.status = 'kept' AND d.triage_verdict = 'kept')"
    ).fetchone()[0]

    inputs = []
    doc_ids: set[str] = set()
    for tc_id, flat_ref, omap, members in rows:
        if tc_id in seen:
            continue  # already extracted at this pipeline version
        try:
            flattened = store.get_text(flat_ref)
        except Exception:
            continue  # payload not on this machine — not this fetch's thread
        offset_map = tuple(OffsetMapping(**span) for span in (omap or ()))
        raw_text_of = {}
        drows = conn.execute(
            "SELECT id, text_ref FROM document WHERE id = ANY(%s)", (list(members),)
        ).fetchall()
        for did, tref in drows:
            if tref:
                with contextlib.suppress(Exception):
                    raw_text_of[did] = store.get_text(tref)
        if not raw_text_of:
            continue  # step 3 renders the raw span; without it, unrenderable
        inputs.append(ThreadInput(
            thread_context_id=tc_id, flattened_text=flattened,
            offset_map=offset_map, raw_text_of=raw_text_of,
        ))
        doc_ids.update(members)
    return inputs, doc_ids, gated_out


def _thread_latest_dates(conn, thread_ids: list[str]) -> dict:
    """thread_context_id -> the newest document date in it. For the release gate."""
    if not thread_ids:
        return {}
    rows = conn.execute(
        "SELECT tc.id, max(d.created_at) "
        "FROM thread_context tc JOIN document d ON d.id = ANY(tc.member_document_ids) "
        "WHERE tc.id = ANY(%s) GROUP BY tc.id",
        (thread_ids,),
    ).fetchall()
    return {tc_id: latest for tc_id, latest in rows}


def triage_stage(conn, prog: Progress) -> None:
    """E4 — the hard gates, over every platform this fetch harvested.

    THIS USED TO BE A NO-OP AND THAT WAS THE EXPENSIVE KIND. Every document went
    to the extractor whatever it was: a bot post, a bare link with no commentary,
    a forty-character "same here", a thread written before the model existed. The
    gates were built and tested and simply never asked, so nothing failed - the
    LLM read junk, and junk that survives extraction reaches the board carrying a
    verified quote, which is exactly the shape nobody catches downstream.

    All eight platforms are gated, not the original three: `_prose_by_source()`
    maps arXiv, dev.to, Hacker News, Hugging Face and X to their own prose
    extractors. That matters more than it looks - the alternative to a real
    extractor is flattening a raw payload, and a payload flattened verbatim lets
    a quote verify against a JSON FIELD VALUE while `quote_verified` says true.

    `dry_run=False`, said explicitly. The default is True because triage writes a
    verdict over thousands of rows on a shared database and the convention is
    that a caller wanting the write asks for it. A per-model fetch is scoped and
    user-initiated, so it asks.

    A GATE THAT COULD NOT RUN IS REPORTED AS UNAVAILABLE, never as a pass.
    `wrong_language` has no detector installed and `known_bot` needs a curated
    list; both come back UNAVAILABLE rather than silently counting as clean, and
    the stage line says which, because "no bots found" and "we cannot look for
    bots" are different facts about the corpus.
    """
    from collect.triage.run import gate_availability, triage_stored

    store = RawStore(Path(settings().raw_store_path))
    prog.stage("E4", "Triage", "running",
               detail="running the hard gates over every unjudged document")
    run = triage_stored(conn, store, dry_run=False)
    conn.commit()

    # The REAL fields off TriageStoreRun, and the denominators with them. A
    # triage that reports "412 dropped" without saying by which gate is a number
    # nobody can act on, and the usual cause of a sudden drop is a broken parser
    # rather than a quiet corpus.
    detail = f"{run.triaged} of {run.eligible} judged; {run.kept} kept, {run.dropped} dropped"
    if run.by_reason:
        detail += " - " + ", ".join(f"{n} {g}" for g, n in sorted(run.by_reason.items()))
    # COULD-NOT-READ IS NOT COULD-NOT-PASS. A payload that did not resolve, or
    # that its extractor refused as not-prose, was never gated at all - counting
    # those as clean would be the silent-absence failure one stage earlier.
    unread = run.unreadable + run.not_prose + run.unmapped_source
    if unread:
        detail += (f" | {unread} never gated ({run.unreadable} unreadable, "
                   f"{run.not_prose} not prose, {run.unmapped_source} unmapped source)")
    # A GATE THAT COULD NOT RUN REPORTS UNAVAILABLE, NEVER A PASS. `wrong_language`
    # has no detector installed and `known_bot` needs a curated list; "no bots
    # found" and "we cannot look for bots" are different facts about the corpus.
    if run.never_ran:
        detail += " | unavailable: " + ", ".join(sorted(run.never_ran))
    prog.stage("E4", "Triage", "ok", eligible=run.eligible, triaged=run.triaged,
               kept=run.kept, dropped=run.dropped, written=run.written,
               by_reason=dict(run.by_reason), by_source=dict(run.by_source),
               never_ran=dict(run.never_ran), not_prose=run.not_prose,
               unreadable=run.unreadable, availability=gate_availability(run),
               detail=detail)


def extract_and_curate(conn, prog: Progress, *, release_date=None) -> None:
    """E5–E7 — extract claims from this fetch's threads, vet, and curate cells.

    Spends (capped) OpenRouter money and writes claims + cells. Scoped to the
    threads this fetch produced (build_thread_inputs skips anything not local).
    The surface resolver is wired here — the composition root's job — so a
    claim's SURFACE ("gemini flash") maps to a model_version. Curation is the
    pipeline's own step; it runs inside one transaction, so it is atomic.

    `release_date` is the fetched model's release date. On a model-name harvest
    the model IS known, so the release gate (reject.py rule 5) runs here rather
    than in the generic text screen: a thread whose newest document predates the
    model cannot be about it — a coincidental name match or a fabrication.
    """
    from collect.surface_resolver import RegistrySurfaceResolver
    from judge import spend_ledger
    from judge.cli import _document_facts, _model_version_map
    from judge.config import capabilities
    from judge.curate.labels import Driver
    from judge.extract.budget import Budget
    from judge.extract.client import OpenRouterClient
    from judge.pipeline import Pipeline
    from judge.store.extractions import ExtractionLedger

    ledger = ExtractionLedger(conn)
    seen = ledger.already_extracted()
    threads, doc_ids, gated_out = build_thread_inputs(conn, seen, limit=200)
    if gated_out:
        # Said, not implied. A smaller corpus reaching the LLM because the gates
        # worked reads identically to a smaller corpus because the harvest was
        # thin, and only one of those is good news.
        prog.stage("E4b", "Screen · pre-LLM", "running",
                   threads_gated_out=gated_out,
                   detail=f"{gated_out} thread(s) held back by E4 - no member survived "
                          "the hard gates, so they never reach the model")

    # Defer pathologically large threads to the nightly batch so a click cannot
    # become a many-minute call. Generous cap: most threads still read now.
    oversized = [t for t in threads if len(t.flattened_text) > MAX_FETCH_THREAD_CHARS]
    threads = [t for t in threads if len(t.flattened_text) <= MAX_FETCH_THREAD_CHARS]
    if oversized:
        prog.stage("E5", "Extract", "running",
                   detail=f"{len(oversized)} oversized thread(s) deferred to the nightly "
                          f"batch (> {MAX_FETCH_THREAD_CHARS:,} chars, too slow on demand)")

    # PRE-LLM HARD GATES. The model reads only what survives them, so a
    # promotional/placeholder/too-short thread never costs a token. Reuses the
    # vet rules (judge/screen.py) on text the fetch already has - the funnel's
    # "gates before the LLM". Coarse by design: a thread drops if its flattened
    # text triggers a rule; per-DOCUMENT granularity (drop one comment, keep the
    # thread) would need to rewrite the assembled offset_map and is a later
    # refinement. Every drop is named on the stage line, not silent.
    from collections import Counter

    from judge.screen import screen as pre_llm_screen

    verdicts = [(t, pre_llm_screen(text=t.flattened_text)) for t in threads]
    dropped = [(t.thread_context_id, v.trigger) for t, v in verdicts if v.dropped]
    threads = [t for t, v in verdicts if not v.dropped]

    # RELEASE-DATE GATE (reject.py rule 5), here because the model is known: a
    # thread whose newest document predates the model's release cannot be about
    # it. Compared against the newest document so a thread that CONTINUED after
    # release is kept; only wholly-pre-release threads drop. Skipped when the
    # model has no release date on record (rule 6: absent is not "predates").
    if release_date is not None and threads:
        latest = _thread_latest_dates(conn, [t.thread_context_id for t in threads])
        predates = []
        kept = []
        for t in threads:
            newest = latest.get(t.thread_context_id)
            if newest is not None and newest.date() < release_date:
                predates.append(t.thread_context_id)
            else:
                kept.append(t)
        threads = kept
        dropped.extend((tc, "predates_model") for tc in predates)

    if dropped:
        by_trigger = Counter(trig for _, trig in dropped)
        summary = ", ".join(f"{n} {trig}" for trig, n in by_trigger.most_common())
        prog.stage("E4b", "Screen · pre-LLM", "ok", dropped=len(dropped),
                   by_trigger=dict(by_trigger),
                   detail=f"{len(dropped)} thread(s) dropped before the LLM ({summary}); "
                          f"{len(threads)} pass to extract")
    else:
        prog.stage("E4b", "Screen · pre-LLM", "ok",
                   detail=f"all {len(threads)} thread(s) passed the pre-LLM screen")

    prog.stage("E5", "Extract", "running",
               detail=f"{len(threads)} new thread(s) to read (LLM; capped spend)")
    if not threads:
        prog.stage("E5", "Extract", "skipped",
                   detail="no new readable threads to read now — "
                          "nothing local, or all deferred as oversized")
        for id_, name in [("E6", "Vet"), ("E7", "Curate")]:
            prog.stage(id_, name, "skipped", detail="no claims to curate")
        return

    budget = Budget.from_env()
    if budget is not None:
        budget.spent_usd = spend_ledger.spent_today()
    facts, _ = _document_facts(conn, doc_ids)
    mvo = _model_version_map(conn)
    resolver = RegistrySurfaceResolver.from_connection(conn)

    # Per-thread progress, so a slow E5 shows movement instead of looking hung -
    # the whole reason E6/E7 seemed never to arrive was E5 running in silence.
    total = len(threads)
    counter = {"n": 0}

    def _on_thread(tc_id: str) -> None:
        counter["n"] += 1
        prog.stage("E5", "Extract", "running",
                   detail=f"reading thread {counter['n']}/{total} (LLM) — {tc_id}")

    results = Pipeline(
        conn,
        client=OpenRouterClient.from_env(),
        capability_keys=list(capabilities().keys()),
        extractor_model=os.getenv("EXTRACTOR_MODEL", "deepseek/deepseek-v4-flash"),
    ).run_all(
        threads, facts=facts, model_version_of=mvo, budget=budget,
        already_extracted=seen, driver=Driver("new-evidence"), resolve_surface=resolver,
        on_thread=_on_thread,
    )
    conn.commit()

    verified = sum(len(r.extraction.verified) for r in results)
    stored = sum(len(r.stored_claim_ids) for r in results)
    cells = sum(len(r.cells) for r in results)
    prog.stage("E5", "Extract", "ok",
               detail=f"{verified} claim(s) verified, {stored} stored")

    # CAPABILITY DISCOVERY. Proposals the extractor made for keys none of the 12
    # named — appended to capability_candidate for an admin to rule on. The LLM
    # proposes; a person adopts (a capabilities.yaml PR). Idempotent, so a
    # re-fetch cannot inflate the count.
    from judge.store.capability_candidates import store_proposals
    proposals = [p for r in results for p in r.extraction.proposed_capabilities]
    # The store must never break a fetch. If the migration has not reached this
    # database yet, the proposals are named in the log and dropped for this run
    # rather than crashing extraction on a missing table.
    table_present = conn.execute(
        "SELECT to_regclass('public.capability_candidate')"
    ).fetchone()[0] is not None
    if proposals and table_present:
        outcome = store_proposals(
            conn, proposals,
            proposer_model=os.getenv("EXTRACTOR_MODEL", "deepseek/deepseek-v4-flash"),
            prompt_label="fetch-extract",
        )
        conn.commit()
        prog.stage("E5b", "Discover", "ok",
                   proposed=outcome["proposed"], stored=outcome["stored"],
                   unattributed=outcome["unattributed"],
                   detail=f"{outcome['proposed']} capability proposal(s); "
                          f"{outcome['stored']} new candidate(s) stored for review"
                          + (f", {outcome['unattributed']} unattributable"
                             if outcome["unattributed"] else ""))
    elif proposals and not table_present:
        prog.stage("E5b", "Discover", "skipped", proposed=len(proposals),
                   keys=sorted({p.proposed_key for p in proposals}),
                   detail=f"{len(proposals)} capability proposal(s) NOT stored: the "
                          "capability_candidate table is not on this database yet "
                          "(migration unapplied). Proposed keys: "
                          + ", ".join(sorted({p.proposed_key for p in proposals})[:8]))
    else:
        prog.stage("E5b", "Discover", "ok",
                   detail="no new capabilities proposed — every claim fit an existing key")

    prog.stage("E6", "Vet", "ok", detail="promotional/sarcastic/contradictory dropped in-run")
    prog.stage("E7", "Curate", "ok",
               detail=f"{cells} cell(s) computed — capability cards refresh from these")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model_version_id")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--fetch-cap", type=int, default=20,
                        help="max GitHub REST calls this fetch may spend (default 20)")
    args = parser.parse_args(argv)

    run_id = args.run_id or f"{args.model_version_id}-{uuid.uuid4().hex[:8]}"
    prog = Progress(run_id, args.model_version_id)
    print(run_id)  # the backend reads this to know which log to poll
    sys.stdout.flush()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        prog.stage("E1", "Registry", "error", detail="DATABASE_URL not set")
        prog.done("error", "no database configured")
        return 1

    try:
        conn = connect(dsn)  # NO drop, NO disposability wipe — append-only
        row = conn.execute(
            "SELECT canonical_id, display_name, release_date FROM model_version WHERE id = %s",
            (args.model_version_id,),
        ).fetchone()
        if row is None:
            prog.stage("E1", "Registry", "error",
                       detail=f"{args.model_version_id} is not in the registry")
            prog.done("error", "unknown model")
            return 1
        canonical_id, display_name, release_date = row
        variants = _variants_for(conn, args.model_version_id, canonical_id)
        prog.stage("E1", "Registry", "ok",
                   model=display_name or canonical_id, variants=len(variants),
                   detail=f"resolved {display_name or canonical_id} — "
                          f"{len(variants)} search-eligible name variant(s)")
        if not variants:
            prog.stage("E2", "Harvest", "skipped",
                       detail="no search variants for this model — nothing to search for")
            prog.done("ok", "nothing to harvest")
            return 0

        # Each platform in its own guard: a Reddit quota error or a stale terms
        # ruling must not throw away a GitHub harvest that already succeeded.
        try:
            harvest_github(conn, prog, variants, fetch_cap=args.fetch_cap)
        except Exception as exc:
            prog.stage("E2", "Harvest", "error", detail=str(exc).splitlines()[0][:200])
        try:
            harvest_reddit(conn, prog, variants, max_searches=3, max_threads=5)
        except Exception as exc:
            prog.stage("E2R", "Harvest · Reddit", "error",
                       detail=str(exc).splitlines()[0][:200])

        try:
            harvest_arxiv(conn, prog, variants, max_queries=2)
        except Exception as exc:
            prog.stage("E2A", "Harvest · arXiv", "error", detail=str(exc).splitlines()[0][:200])
        try:
            harvest_x(conn, prog, variants, max_queries=2)
        except Exception as exc:
            prog.stage("E2X", "Harvest · X", "error", detail=str(exc).splitlines()[0][:200])

        # Blogs have no per-model search — they are RSS/feed-based, harvested
        # wholesale, so a model-name query cannot target them (rule 7: say what
        # the run did NOT do rather than let its absence read as coverage).
        prog.stage("E2B", "Harvest · Blogs", "skipped",
                   detail="blogs are feed-based — no per-model search; not run for one model")

        # dev.to, Hacker News and Hugging Face. Ruled on 2026-09-09, so they run
        # now; each still gates itself, and a ruling that lapses or whose
        # preconditions stop holding turns the arm back into a named skip rather
        # than a silent absence.
        for _pid, _sid, _sname, _cap in UNIFORM_PLATFORMS:
            try:
                harvest_uniform(conn, prog, variants, platform_id=_pid,
                                stage_id=_sid, stage_name=_sname, max_queries=_cap)
            except Exception as exc:
                prog.stage(_sid, _sname, "error", detail=str(exc).splitlines()[0][:200])

        # ── TRIAGE BEFORE ASSEMBLE, and the order is the point ───────────────
        # A stage must only receive what the previous one passed. Triage judges
        # DOCUMENTS and needs no thread_context - it reads `document`, `author`
        # and the raw payload - so running it first means assembly never
        # flattens a bot post, a bare link or a pre-release thread. Running it
        # second worked, because the verdict still gated extraction, but it paid
        # to flatten rows it had already decided to drop and left `thread_context`
        # holding contexts for evidence that had failed.
        try:
            triage_stage(conn, prog)
        except Exception as exc:
            conn.rollback()
            prog.stage("E4", "Triage", "error", detail=str(exc).splitlines()[0][:200])

        try:
            assemble_stage(conn, prog)
        except Exception as exc:
            conn.rollback()
            prog.stage("E3", "Assemble", "error", detail=str(exc).splitlines()[0][:200])

        try:
            extract_and_curate(conn, prog, release_date=release_date)
        except Exception as exc:
            conn.rollback()
            prog.stage("E5", "Extract", "error", detail=str(exc).splitlines()[0][:200])

        prog.done("ok", "fetch complete")
        return 0
    except Exception as exc:  # a failed stage is a finding, logged, not a silent crash
        prog.stage("?", "fetch", "error", detail=str(exc).splitlines()[0][:200])
        prog.done("error", traceback.format_exc().splitlines()[-1][:200])
        return 1


if __name__ == "__main__":
    sys.exit(main())
