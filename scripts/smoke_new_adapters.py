"""Prove the five new adapters connect, store, and write provenance. Not a sweep.

    py -3 scripts/smoke_new_adapters.py --query "Fable 5.1" --max 2

WHAT THIS IS FOR
----------------
One or two documents per platform, end to end: the terms gate runs, the request
is made, the payload lands in the raw store, a `harvest_run` row opens and
closes around it, `document` rows are written with `retrieval_provenance`, and
every `text_ref` is resolved back and checked against its `content_hash`.

It reports four figures per platform, and they are four rather than one because
each answers a different question:

    requests issued     what it cost
    candidates          what the platform returned
    documents stored    what reached the store and the database
    text_ref resolves   whether the row means anything

⚠  `candidates == 0` AND `requests_issued == 0` ARE DIFFERENT FINDINGS.
   A platform that returned nothing for a keyword and an adapter that never
   asked look identical in a "0 documents" summary, and only one of them is a
   bug. Several of these platforms have a lookback window - X's recent search
   is seven days, Hacker News's index is relevance-ranked over everything, arXiv
   is all of arXiv - so an empty result is a fact about the platform far more
   often than about the code. The report says which.

⚠  IT REFUSES ANY DATABASE THAT IS NOT ON THIS MACHINE, and that is the whole
   reason this is a script rather than a chain stage.

   Writing here means creating `source` rows for platforms whose terms rulings
   are UNRATIFIED DRAFTS - THREE OF THE FIVE since 2026-09-08, dev.to, Hacker
   News and Hugging Face (`docs/proposals/new-platform-sources.draft.yaml`). A
   seeded `source` row is what `assert_terms_reviewed` consults to decide
   whether we may fetch at all, so putting an unratified one on the shared
   database would make the draft look like a decision to every later run -
   which is item 20's shape exactly: a value indistinguishable from a reviewed
   one, gating behaviour.

   ⚠  THE GUARD DOES NOT RELAX FOR THE TWO THAT WERE RATIFIED. arXiv and X now
      have real rulings in contract/, and `registry load-sources` is the
      command that seeds those rows properly. This script still refuses
      anything but localhost for all five, because the rows it writes are
      whatever THIS FILE's merge produced, and a run that wrote two legitimate
      rows and three draft ones to staging would leave nothing on the row
      saying which was which.

   So: localhost only, checked against the OPEN CONNECTION's host rather than
   against the DSN passed in, which is the property that makes it a guard
   rather than a courtesy (`collect/db.py:reset_schema` establishes both the
   check and the reason).

THE GATE IS NOT BYPASSED
------------------------
Every harvester is built through `harvester_for_source()`, so
`assert_terms_reviewed` runs with this run's own live observations - as opposed
to skipping the gate, which is how a 1,297-post Reddit corpus was gathered with
the gate never asked (`collect/adapters/reddit.py:harvester_for_source`).

THE RULINGS NOW COME FROM TWO FILES, AND THE REPORT SAYS WHICH PER PLATFORM.
arXiv and X were ratified 2026-09-08 and live in `contract/sources.yaml`; the
other three are still drafts. `_load_draft` merges them and REFUSES an id
declared in both, because two files declaring one ruling makes the gate's
answer depend on which file a caller loaded. `payload["rulings"]` is a mapping
rather than one string for exactly this reason.

A platform whose ruling cannot be satisfied is reported as REFUSED with the
reason, and no request is made. X is the standing case: `credential_present` is
a live precondition and no `RAPIDAPI_KEY` is configured, so a run refuses at
the gate. That refusal is now about the CREDENTIAL and no longer about the
terms - which is the whole difference ratification made, and the reason string
says so.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collect.config import CONTRACT_DIR, settings  # noqa: E402
from collect.db import LOCAL_HOSTS, connect  # noqa: E402
from collect.http import build_client  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.registry.sources import parse_sources  # noqa: E402

DRAFT = ROOT / "docs" / "proposals" / "new-platform-sources.draft.yaml"

#: The five, in the order the report prints them.
PLATFORMS = ("arxiv", "devto", "hackernews", "huggingface", "x")


class NotLocal(RuntimeError):
    """The target database is not on this machine. See the module docstring."""


def assert_local(conn) -> None:
    """Refuse anything but localhost, read from the open connection.

    Reading `conn.info.host` rather than the DSN is what makes this
    undefeatable by argument: it describes the socket that is actually open.
    """
    host = conn.info.host
    local = not host or host.startswith("/") or host in LOCAL_HOSTS
    if not local:
        raise NotLocal(
            f"refusing to write to host {host!r}: this script creates `source` "
            "rows for five platforms, three of whose terms rulings are "
            "UNRATIFIED DRAFTS (dev.to, Hacker News, Hugging Face). "
            "A seeded source row is what the terms gate reads to decide whether "
            "we may fetch, so an unratified one on a shared database reads as a "
            "decision to every later run. Use the disposable local instance "
            "(scripts/dev-postgres.ps1) — the host is read from the open "
            "connection, so this cannot be overridden by passing a different "
            "DSN."
        )


def ensure_sources(conn, platforms) -> dict[str, int]:
    """Create the five draft `source` rows. Append-only, localhost only.

    `harvest_run.source_id` references `source(id)`, so without these rows
    `open_harvest_run` refuses upstream of the foreign key - which is the
    correct refusal and not something to work around on a shared database.
    """
    from psycopg.types.json import Json

    inserted = 0
    for row in platforms:
        evidence = dict(row.get("terms_evidence") or {})
        checked_on = evidence.get("checked_on")
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO source (id, platform, endpoint, base_trust, tos_notes, "
                "provenance, terms_ruling, terms_checked_on, terms_evidence) "
                "VALUES (%s, %s, %s, %s, %s, 'seed', %s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING",
                (
                    row["id"],
                    row["platform"],
                    row.get("endpoint"),
                    row["base_trust"],
                    row["tos_notes"],
                    row.get("terms_ruling"),
                    checked_on,
                    Json({k: str(v) for k, v in evidence.items()}),
                ),
            )
            inserted += max(0, cur.rowcount)
    conn.commit()
    return {"seen": len(platforms), "inserted": inserted}


def surface_present(texts, surface: str) -> int:
    """How many of these texts contain the surface, by exact substring.

    Reported beside `candidates` because on three of these platforms retrieval
    is looser than a mention: Algolia prefix-matches every token, and dev.to's
    search matches body text. A candidate count quoted as a mention count is
    rule 7's failure, so both numbers travel together.

    Plain Python, case-insensitive, no model and no regex over the surface -
    the same shape as rule 1's quote verification.
    """
    needle = surface.casefold()
    return sum(1 for t in texts if t and needle in t.casefold())


def prose_check(store, drafts, extractor) -> dict:
    """Does each stored payload yield prose, and is it not a container?

    The invariant check (`content_hash(resolve(text_ref)) == content_hash`) is
    NECESSARY AND NOT SUFFICIENT - it catches a mismatch between the two
    columns and cannot catch a wrong CHOICE of artifact, which is the failure
    that actually happened twice on two platforms. The check that catches the
    wrong choice is this one: derive the prose and confirm it does not parse as
    a container. See docs/engineer-1/ruling-what-content-hash-identifies.md.
    """
    from collect.assemble.prose import NotAPayload

    derived = refused = still_a_container = 0
    samples: list[str] = []
    failures: list[str] = []
    for draft in drafts:
        try:
            blob = store.get_text(draft.text_ref)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{draft.external_id}: unreadable ({type(exc).__name__})")
            continue
        try:
            text = extractor(blob)
        except NotAPayload as exc:
            refused += 1
            failures.append(f"{draft.external_id}: {exc}")
            continue
        derived += 1
        stripped = text.lstrip()
        if stripped.startswith(("{", "[", "<")):
            still_a_container += 1
            failures.append(f"{draft.external_id}: prose still looks like a container")
        if len(samples) < 2:
            samples.append(" ".join(text.split())[:220])
    return {
        "prose_derived": derived,
        "prose_refused": refused,
        "prose_still_a_container": still_a_container,
        "prose_samples": samples,
        "prose_failures": failures,
    }


def run_platform(name: str, *, contract, conn, store, client, query: str, limit: int):
    """One platform, end to end. Never raises — a refusal is a finding."""
    from collect.adapters.documents import verify_text_refs
    from collect.ops.ledger import OK, close_harvest_run, open_harvest_run

    source = next((s for s in contract.platforms if s["id"] == name), None)
    result: dict = {
        "platform": name,
        "query": query,
        "requests_issued": 0,
        "candidates": 0,
        "documents_stored": 0,
        "documents_inserted": 0,
        "text_refs_resolved": 0,
        "http_errors": 0,
        "outcome": "not-run",
        "notes": [],
    }
    if source is None:
        result["outcome"] = "no-draft-source-row"
        return result

    modules = {
        "arxiv": ("collect.adapters.arxiv", "arxiv_paper_prose"),
        "devto": ("collect.adapters.devto", "devto_article_prose"),
        "hackernews": ("collect.adapters.hackernews", "hackernews_prose"),
        "huggingface": ("collect.adapters.huggingface", "huggingface_prose"),
        "x": ("collect.adapters.x", "x_post_prose"),
    }
    module_name, prose_name = modules[name]
    module = __import__(module_name, fromlist=["harvester_for_source"])
    from collect.assemble import prose as prose_module

    extractor = getattr(prose_module, prose_name)

    # ── the gate, and the credential ─────────────────────────────────────
    try:
        harvester = module.harvester_for_source(
            source, rulings=contract.rulings, client=client, store=store
        )
    except Exception as exc:  # noqa: BLE001 - a refusal is the finding
        result["outcome"] = "refused"
        result["notes"].append(f"{type(exc).__name__}: {str(exc).splitlines()[0]}")
        # NAMED IN FULL, because a refusal's reason is the deliverable here.
        result["refusal"] = str(exc)
        return result

    # ── the fetch ────────────────────────────────────────────────────────
    if name == "arxiv":
        # arXiv's own query syntax. `all:` searches title, abstract and authors.
        run = harvester.harvest(f'all:"{query}"', max_fetch=limit)
        texts = [p.sieve_text for p in run.papers]
    elif name == "devto":
        run = harvester.harvest(query, max_fetch=limit)
        texts = [h.sieve_text for h in run.hits]
    elif name == "hackernews":
        run = harvester.harvest(query, max_fetch=limit)
        texts = [c.sieve_text for c in run.comments]
    elif name == "huggingface":
        run = harvester.harvest(query, max_repos=2, max_discussions=2)
        texts = [c.sieve_text for d in run.discussions for c in d.comments]
    else:
        run = harvester.harvest(query, max_store=limit)
        texts = [p.sieve_text for p in run.posts]

    counts = harvester.counts(run)
    result.update(
        requests_issued=counts.requests_issued,
        candidates=counts.candidates,
        http_errors=counts.http_errors,
        notes=list(counts.notes),
    )
    result["surface_present_in_candidates"] = surface_present(texts, query)

    drafts = (
        harvester.drafts(run)
        if hasattr(harvester, "drafts")
        else [s.draft() for s in run.stored]
    )
    result["documents_stored"] = len(drafts)

    # ── the ledger, two-phase ────────────────────────────────────────────
    fields = run.harvest_run_fields()
    opened = open_harvest_run(conn, fields)
    conn.commit()

    report = harvester.write_documents(
        conn, run, retrieval_provenance="run_recorded", harvest_run_id=opened.id
    )
    conn.commit()
    close_harvest_run(conn, opened, fields, outcome=OK)
    conn.commit()

    result["harvest_run_id"] = opened.id
    result["documents_inserted"] = report.inserted
    result["write_report"] = report.describe()
    result["distinct_authors"] = report.distinct_authors
    result["documents_without_author"] = report.without_author
    result["documents_without_created_at"] = report.without_created_at
    result["lang_declared_by_platform"] = report.lang_declared_by_platform

    verified = verify_text_refs(store, drafts)
    result["text_refs_resolved"] = verified["resolved"]
    result["text_ref_missing"] = verified["missing"]
    result["content_hash_mismatched"] = verified["hash_mismatched"]
    result["resolved_to_a_container"] = verified["resolved_to_a_container"]
    result.update(prose_check(store, drafts, extractor))
    result["outcome"] = "ok"
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="Fable 5.1")
    parser.add_argument("--max", type=int, default=2, dest="limit")
    parser.add_argument("--database-url", default=None)
    parser.add_argument(
        "--platforms", default=",".join(PLATFORMS),
        help="comma-separated subset, for re-running one platform",
    )
    parser.add_argument(
        "--out", default="docs/measurements/new-adapter-smoke-2026-09-07.json"
    )
    args = parser.parse_args(argv)

    # `parse_sources` takes the parsed YAML as-is, dates included — the same
    # input `load_sources()` hands it from contract/sources.yaml.
    contract = parse_sources(_load_draft())
    wanted = [p.strip() for p in args.platforms.split(",") if p.strip()]

    store = RawStore(Path(settings().raw_store_path))
    conn = connect(args.database_url)
    try:
        assert_local(conn)
        source_counts = ensure_sources(
            conn, [s for s in contract.platforms if s["id"] in wanted]
        )
        results = []
        with build_client(timeout=45.0, follow_redirects=True) as client:
            for name in wanted:
                print(f"-- {name} …", flush=True)
                results.append(
                    run_platform(
                        name,
                        contract=contract,
                        conn=conn,
                        store=store,
                        client=client,
                        query=args.query,
                        limit=args.limit,
                    )
                )
    finally:
        conn.close()

    payload = {
        "ran_at": datetime.now(UTC).isoformat(),
        "query": args.query,
        "max_per_platform": args.limit,
        "database": "disposable local instance (localhost)",
        # WHICH FILE EACH PLATFORM'S RULING CAME FROM. One string for all five
        # was true until 2026-09-08 and is not any more, and a report that said
        # "UNRATIFIED DRAFT" over a ratified arXiv row would be exactly the
        # provenance confusion the merge above refuses.
        "rulings": _ruling_provenance(),
        "source_rows": source_counts,
        "platforms": results,
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    print()
    header = (
        f"{'platform':<13}{'reqs':>6}{'cands':>7}{'surf':>6}{'stored':>8}"
        f"{'ins':>5}{'refs':>6}{'prose':>7}  outcome"
    )
    print(header)
    print("-" * len(header))
    for row in results:
        print(
            f"{row['platform']:<13}{row['requests_issued']:>6}{row['candidates']:>7}"
            f"{row.get('surface_present_in_candidates', 0):>6}"
            f"{row['documents_stored']:>8}{row['documents_inserted']:>5}"
            f"{row['text_refs_resolved']:>6}{row.get('prose_derived', 0):>7}"
            f"  {row['outcome']}"
        )
    print(f"\nwritten: {args.out}")
    return 0


def _ruling_provenance() -> dict[str, str]:
    """Per platform, which file its ruling was read from."""
    from collect.registry.sources import load_sources

    ratified = set(load_sources().rulings)
    draft = {
        r["id"] for r in (_raw_draft().get("terms_rulings") or [])
    }
    out = {}
    for row in _load_draft()["sources"]:
        named = row.get("terms_ruling")
        if named in ratified:
            out[row["id"]] = f"RATIFIED — contract/sources.yaml ({named})"
        elif named in draft:
            out[row["id"]] = (
                f"UNRATIFIED DRAFT — {DRAFT.relative_to(ROOT).as_posix()} ({named})"
            )
        else:
            out[row["id"]] = f"NO RULING DECLARED ANYWHERE ({named})"
    return out


def _raw_draft() -> dict:
    import yaml

    return yaml.safe_load(DRAFT.read_text(encoding="utf-8"))


def _load_draft() -> dict:
    """The draft's YAML, with anything already RATIFIED taken from contract/.

    ⚠  TWO FILES MUST NOT DECLARE ONE RULING ID. arXiv and X were ratified on
       2026-09-08 and MOVED out of the draft into `contract/sources.yaml`, so
       this merges rather than choosing: the three still-draft platforms come
       from the draft file, and the two ratified ones come from contract/,
       which is now their only home. A copy left behind would be the defect
       `docs/defect-two-names-for-one-database.md` records - and the stale
       half is always the one nobody is reading.

    contract/ WINS ON A COLLISION, and the collision is reported rather than
    resolved silently: an id in both files means somebody copied instead of
    moving, and this run is the place that notices.
    """
    import yaml

    from collect.registry.sources import load_sources

    draft = yaml.safe_load(DRAFT.read_text(encoding="utf-8"))
    ratified = load_sources()

    draft_ruling_ids = {r["id"] for r in draft.get("terms_rulings") or []}
    draft_source_ids = {r["id"] for r in draft.get("sources") or []}
    collisions = sorted(
        (draft_ruling_ids & set(ratified.rulings))
        | (draft_source_ids & {p["id"] for p in ratified.platforms})
    )
    if collisions:
        raise SystemExit(
            f"{', '.join(collisions)} is declared in BOTH "
            f"{DRAFT.relative_to(ROOT)} and contract/sources.yaml. A ratified "
            "ruling is MOVED, not copied - two files declaring one id means the "
            "gate's answer depends on which one a caller happened to load. "
            "Delete the draft copy."
        )

    raw_contract = yaml.safe_load(
        (CONTRACT_DIR / "sources.yaml").read_text(encoding="utf-8")
    )
    wanted = set(PLATFORMS)
    draft["terms_rulings"] = list(draft.get("terms_rulings") or []) + [
        r
        for r in raw_contract["terms_rulings"]
        if r["id"] in {p.get("terms_ruling") for p in raw_contract["sources"]
                       if p["id"] in wanted}
    ]
    draft["sources"] = list(draft.get("sources") or []) + [
        p for p in raw_contract["sources"] if p["id"] in wanted
    ]
    return draft


if __name__ == "__main__":
    raise SystemExit(main())
