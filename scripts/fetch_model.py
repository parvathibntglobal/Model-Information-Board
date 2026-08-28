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


def assemble_stage(conn, prog: Progress) -> None:
    """E3 — flatten this fetch's new documents into thread_context rows.

    Runs the collect assemblers over unassembled documents. Documents whose raw
    payload is not in THIS machine's store (anything harvested elsewhere) are
    skipped by the assemblers; the ones this fetch just harvested are local, so
    they are what actually get flattened. Append-only.
    """
    from collect.assemble.issue import assemble_github_documents
    from collect.assemble.reddit import assemble_reddit_documents

    store = RawStore(Path(settings().raw_store_path))
    prog.stage("E3", "Assemble", "running", detail="flattening new documents into threads")
    notes = []
    for name, fn in (("github", assemble_github_documents), ("reddit", assemble_reddit_documents)):
        try:
            report = fn(conn, store=store, limit=200)
            conn.commit()
            notes.append(f"{name}: {report.summary()}")
        except Exception as exc:
            conn.rollback()
            notes.append(f"{name}: skipped ({str(exc).splitlines()[0][:80]})")
    prog.stage("E3", "Assemble", "ok", detail=" · ".join(notes))


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
    rows = conn.execute(
        "SELECT id, flattened_text_ref, offset_map, member_document_ids "
        "FROM thread_context ORDER BY assembled_at DESC LIMIT %s",
        (limit,),
    ).fetchall()

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
    return inputs, doc_ids


def extract_and_curate(conn, prog: Progress) -> None:
    """E5–E7 — extract claims from this fetch's threads, vet, and curate cells.

    Spends (capped) OpenRouter money and writes claims + cells. Scoped to the
    threads this fetch produced (build_thread_inputs skips anything not local).
    The surface resolver is wired here — the composition root's job — so a
    claim's SURFACE ("gemini flash") maps to a model_version. Curation is the
    pipeline's own step; it runs inside one transaction, so it is atomic.
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
    threads, doc_ids = build_thread_inputs(conn, seen, limit=200)

    # Defer pathologically large threads to the nightly batch so a click cannot
    # become a many-minute call. Generous cap: most threads still read now.
    oversized = [t for t in threads if len(t.flattened_text) > MAX_FETCH_THREAD_CHARS]
    threads = [t for t in threads if len(t.flattened_text) <= MAX_FETCH_THREAD_CHARS]
    if oversized:
        prog.stage("E5", "Extract", "running",
                   detail=f"{len(oversized)} oversized thread(s) deferred to the nightly "
                          f"batch (> {MAX_FETCH_THREAD_CHARS:,} chars, too slow on demand)")
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
        extractor_model=os.getenv("EXTRACTOR_MODEL", "google/gemini-2.5-flash"),
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
            "SELECT canonical_id, display_name FROM model_version WHERE id = %s",
            (args.model_version_id,),
        ).fetchone()
        if row is None:
            prog.stage("E1", "Registry", "error",
                       detail=f"{args.model_version_id} is not in the registry")
            prog.done("error", "unknown model")
            return 1
        canonical_id, display_name = row
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

        # Blogs have no per-model search — they are RSS/feed-based, harvested
        # wholesale, so a model-name query cannot target them (rule 7: say what
        # the run did NOT do rather than let its absence read as coverage).
        prog.stage("E2B", "Harvest · Blogs", "skipped",
                   detail="blogs are feed-based — no per-model search; not run for one model")

        try:
            assemble_stage(conn, prog)
        except Exception as exc:
            conn.rollback()
            prog.stage("E3", "Assemble", "error", detail=str(exc).splitlines()[0][:200])

        # E4 triage: harvested documents default to status 'kept', and the
        # filter-persist path is not wired, so nothing is downgraded here (rule 4:
        # said, not silently implied to have run).
        prog.stage("E4", "Triage", "skipped",
                   detail="documents default to 'kept'; filter-persist not wired")

        try:
            extract_and_curate(conn, prog)
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
