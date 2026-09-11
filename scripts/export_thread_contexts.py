"""Export `thread_context` rows plus everything the extractor path reads.

FOR ENGINEER 2, TO LOAD INTO A LOCAL POSTGRES
---------------------------------------------
Two artifacts per thread, because the extract path and the cell path need
different things and only one of them is a database:

    threads/<id>.json   what `judge/extract/runner.ThreadInput` needs, INLINE:
                        flattened_text, offset_map, raw_text_of. No object store
                        required. This is the shape `fixtures/threads/*.json`
                        already has, so an existing loader reads it unchanged.

    load.sql            the `document`, `author` and `thread_context` rows, for
                        the cell path — `judge/store/cells.py` joins `document`
                        to read `d.source` AS the platform, so `platform_count`
                        cannot be computed from the JSON alone.

WHY THE TEXT IS INLINE RATHER THAN A `text_ref`
-----------------------------------------------
`raw_text_of` resolves `document_id -> untouched source text`, and the refs in
`document.text_ref` point into an object store that is gitignored and lives on
whichever machine ran the harvest. Exporting refs would export a promise. The
bytes are small; the coordination cost of a missing payload is not.

WHY THIS SUPERSEDES `fixtures/threads/thread-1u1b22l.json`
----------------------------------------------------------
That file is Engineer 2's own fixture tooling (`fixtures/threads/build.py`) and
its docstring says: *"If the two disagree when E3 lands, E3 is right and this
regenerates."* They disagree. The fixture strips the `t1_`/`t3_` prefixes
(`reddit:1u1b22l`), selects children by score alone, and produces 7 members and
22 segments. E3 keeps the fullnames, ranks by
`specificity_score x log(1 + engagement)`, and produces 6 and 6.

STAGING IS NOT THE SOURCE, AND CANNOT BE
----------------------------------------
Staging holds 2 `thread_context` rows and **0 `document` rows** — there is no
Reddit document writer yet (`collect/CLAUDE.md`), so the table `raw_text_of`
resolves against was never populated. Its `flattened_text_ref` values also point
at payloads absent from any local store. So the Reddit thread here is
REGENERATED from the stored API payload, and the document rows are constructed
here because they exist nowhere to be copied from.

SAME ID, DIFFERENT CONTENT: THE ID GUARANTEE HAS ALREADY FAILED ONCE
--------------------------------------------------------------------
Regenerating the staging row selected DIFFERENT CHILDREN under the SAME id.

    id       thread_context_eacc17c8af367044   <- identical
    staging  t1_oqoc844  t1_oqocu7n  t1_oqorjbe  t1_oqozyx5  t1_oqoehi3
    here     t1_oqoc844  t1_oqodw1j  t1_oqocfjv  t1_oqorjbe  t1_oqocu7n

The flattening is not in question: the root segment is byte-identical,
`flat(0,1739) raw(0,1739)`. The divergence is `rank_children`, and the cause is
dated. `collect/triage/specificity.py` changed in `4f960ac` at 2026-08-18 11:57;
the staging row was written at 09:58. **`PIPELINE_VERSION` was not bumped** — it
has been `collect-0.1.0` since the baseline commit.

`assemble` computes `id = stable_id("thread_context", root_id, version)`, which
depends on the root and the version and NOT on the content. So a scoring change
without a version bump produces the same id carrying different members and a
different `offset_map`, and `write_thread_context` uses
`ON CONFLICT (id) DO NOTHING` — a re-run silently keeps the stale row.

`collect/assemble/thread.py` states the guarantee as holding *"provided
`PIPELINE_VERSION` is bumped when the flattener changes"* and calls it *"a
convention rather than a check"*. The convention failed, and not even where the
proviso was looking: the change was to the SCORER that picks children, which
that sentence does not mention. Over-identification was the documented risk;
this is under-identification, which is the direction the docstring says never
happens.

WHY THE FIRST DIAGNOSIS WAS WRONG, AND THE ALIASES WERE THE CAUSE AFTER ALL
---------------------------------------------------------------------------
This said: *"Measured, it is not: `()` and the full registry surface set produce
IDENTICAL members and identical scores (2.521, 1.2459, 1.1437, 1.1331, 1.0978)
on this thread. The aliases are still inlined in `provenance` below ... but they
are not the cause."*

**The control was broken and the two arms were the same arm.** `version_aliases()`
returned `r.normalized` — `registry.aliases.normalize` output, which strips every
non-alphanumeric and produces `anthropicclaudeopus5`. `names_version` normalises
the text with `sieve.normalize`, which keeps spaces, dots and hyphens. So the
"full registry surface set" arm matched **0 of this thread's 195 comment bodies**,
which is what `()` matches, which is why the scores were identical.

Corrected, with the real surface set:

    aliases matching  0 of 195   oqoc844 oqodw1j oqocfjv oqorjbe oqocu7n
                                 scores 2.5210 1.2459 1.1437 1.1331 1.0978
    aliases matching 27 of 195   oqoc844 oqocu7n oqorjbe oqozyx5 oqoehi3
                                 scores 3.3613 1.9211 1.8130 1.5648 1.5508
    staging row                  oqoc844 oqocu7n oqorjbe oqozyx5 oqoehi3

**The staging row is reproducible and this file said it was not.** Today's code
reproduces it exactly, in order, when the aliases can match. So the divergence
was never a dated code change and `PIPELINE_VERSION` not being bumped is a
separate (real) hazard rather than the explanation.

The lesson is the one that keeps recurring here: a non-empty list recorded in
provenance looked like a scoring input. `alias_match_count` now counts matches
rather than checking presence, because presence is what passed.

The staging row cannot be reconstructed: the code that produced it is two
commits back and nothing in the row identifies which. That belongs on the
`extraction_version` conversation (#5, item A4).

The second staging row (`t3_1vozb95`) has no stored payload in `fixtures/` and
CANNOT be exported at all — see the manifest's `incomplete` list. Recorded
rather than half-exported: an offset_map with no text to resolve against is
worse than an absent thread, because it verifies as nothing rather than failing.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.adapters.reddit import reddit_document_id  # noqa: E402
from collect.adapters.reddit_comments import parse_thread  # noqa: E402
from collect.assemble.article import (  # noqa: E402
    ArticleInput,
    assemble_article,
    blog_document_id,
)
from collect.assemble.article import document_row as blog_document_row  # noqa: E402
from collect.assemble.thread import assemble  # noqa: E402
from collect.ids import content_hash  # noqa: E402
from collect.rawstore import RawStore
from collect.registry.seed import seed_models  # noqa: E402
from collect.triage.specificity import alias_match_count  # noqa: E402

REDDIT_PAYLOAD = Path("fixtures/reddit/thread-1u1b22l-getPostComments.json")

#: How many thread_context rows to export. One is Reddit - there is exactly one
#: stored API payload - and the rest are blog articles from `raw_store`.
DEFAULT_THREADS = 12

#: WHERE THE BLOG URL COMES FROM, and why it is no longer withheld.
#:
#: It is read from the STORED PAYLOAD's own `rel=canonical` or `og:url` - the
#: publisher's declaration, in the bytes we already hold. Not from the census
#: index, so this needs no join and inherits no index of its own.
#:
#: **THE RETENTION QUESTION IS NOT SETTLED BY THIS.** `judge/CLAUDE.md` records
#: it: a document with no URL can be extracted, weighted, counted and gated, and
#: then cannot be RENDERED, so E2 could exercise every stage but the page. The
#: objection to carrying the URL was that a `delete_after` date in a file that
#: cannot enforce it is decorative. That objection stands. What changes here is
#: narrower: the date and the basis now TRAVEL with the URL in the manifest
#: instead of being dropped, so a reader of this bundle can see the constraint
#: rather than having to know it. Whether such a URL may be PUBLISHED is still
#: the open ruling, and this bundle is not the place it gets answered - it is
#: gitignored, and `use_basis` is internal-development-only either way.
_CANONICAL = re.compile(rb'<link[^>]+rel=["\']canonical["\'][^>]*>', re.I)
_HREF = re.compile(rb'href=["\']([^"\']+)["\']', re.I)
_OG_URL = (
    re.compile(rb'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(rb'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:url["\']', re.I),
)

#: Inherited from `_blog_so_sweep/manifest.json`. Stated rather than recomputed:
#: this bundle does not re-derive a retention date, it carries the one the
#: corpus it draws from already declared.
CENSUS_BASIS = {
    "use_basis": "internal-development-only",
    "collected_on": "2026-08-18",
    "delete_after": "2026-11-16",
    "source_corpus": "_blog_so_sweep/ (docs/measurements/blog-symbol-census.md)",
    "not_evidence": (
        "The census corpus declares 'Nothing here is quoted, published, or "
        "merged as evidence.' These rows exist to exercise the extract and cell "
        "paths. They must not become published claims."
    ),
}


def declared_url(data: bytes) -> str | None:
    """The URL the document declares about itself, or None."""
    found = _CANONICAL.search(data)
    if found:
        href = _HREF.search(found.group(0))
        if href:
            return href.group(1).decode("utf-8", "replace")
    for pattern in _OG_URL:
        found = pattern.search(data)
        if found:
            return found.group(1).decode("utf-8", "replace")
    return None


def version_aliases(conn=None) -> tuple[str, ...]:
    """Surfaces `names_version` can actually match. Registry-derived.

    `family` surfaces are EXCLUDED, per `names_version`'s own docstring: a bare
    `sonnet` names a line rather than a tier, and counting it would credit a
    document that never said which model it meant. `build_population` excludes
    them already, via `_admissible`.

    THIS RETURNED `r.normalized` AND MATCHED NOTHING — FIXED 2026-08-21.
    `registry.aliases.normalize` strips every non-alphanumeric, so it produced
    `anthropicclaudeopus5`. `names_version` normalises the TEXT with
    `sieve.normalize`, which lowercases and collapses whitespace and keeps dots,
    hyphens and spaces — `'fable 5 on med is cheaper than opus 4.8'`. The two
    normal forms are different, so an alias in the first can never appear in the
    second.

    Measured on this thread's 195 comment bodies:

        r.normalized (what this returned)        0 of 195 match
        the same rows' raw `surface`             0 of 195   (seed holds 10 models)
        build_population surfaces (1247)        27 of 195

    That is what made the docstring above wrong. See `WHY THE FIRST DIAGNOSIS
    WAS WRONG` at the top of this file.

    Sourced from `model_version` rather than the seed file, because that is what
    the production assembler is handed and the seed file holds ten models.
    """
    from collect.triage.entity import build_population

    if conn is None:
        from collect.db import connect

        conn = connect()
        close = True
    else:
        close = False
    try:
        rows = conn.execute(
            "SELECT canonical_id, display_name FROM model_version "
            "ORDER BY canonical_id"
        ).fetchall()
    finally:
        if close:
            conn.close()

    declared: list[str] = []
    for model in seed_models():
        declared.append(model.aliases.surface)
        declared.extend(model.aliases.variants)
    population = build_population([(r[0], r[1]) for r in rows], declared)
    return tuple(sorted(population.surfaces))


def _sql_literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple)):
        inner = ",".join(str(v).replace("\\", "\\\\").replace('"', '\\"') for v in value)
        return "'{" + inner + "}'"
    return "'" + str(value).replace("'", "''") + "'"


def _insert(table: str, row: dict) -> str:
    cols = ", ".join(row)
    vals = ", ".join(_sql_literal(v) for v in row.values())
    conflict = "(source, external_id)" if table == "document" else "(id)"
    return f"INSERT INTO {table} ({cols})\nVALUES ({vals})\nON CONFLICT {conflict} DO NOTHING;"


def build_reddit(store: RawStore) -> tuple[dict, list[dict], str]:
    payload = json.loads(REDDIT_PAYLOAD.read_text(encoding="utf-8"))
    thread = parse_thread(payload, url="https://www.reddit.com/r/ClaudeAI/x/")
    root = payload["data"][0]["data"]["children"][0]["data"]
    root_text = (root.get("title", "") + "\n\n" + (root.get("selftext") or "")).strip()
    root_id = reddit_document_id(root.get("name"))

    aliases = version_aliases()
    assembled = assemble(
        thread,
        root_text=root_text,
        root_document_id=root_id,
        child_document_id=lambda c: reddit_document_id(c.external_id),
        store=store,
        # NOT `()`. An empty tuple scores every `names_version` signal False,
        # which silently changes which children rank highest — that is exactly
        # how this export first diverged from the staging row.
        version_aliases=aliases,
    )

    assembled_aliases = aliases
    raw_text_of = {root_id: root_text}
    by_id = {reddit_document_id(c.external_id): c for c in thread.comments}
    for member in assembled.member_document_ids:
        if member in by_id:
            raw_text_of[member] = by_id[member].body

    documents = []
    for member in assembled.member_document_ids:
        text = raw_text_of[member]
        comment = by_id.get(member)
        # `created_at` FROM THE PAYLOAD, and it was omitted here rather than
        # absent from the source. Every Reddit body carries `created_utc`, the
        # adapter already turns it into a UTC datetime, and this loop dropped
        # it — so the seven landed in staging with `created_at IS NULL` and
        # `Pipeline.run` skipped every claim built on them rather than
        # weighting from a default. The production writers all populate it
        # (27 of 27 GitHub, 30 of 30 blog); the gap was this export alone.
        #
        # Read through the adapter's own property so there is one definition of
        # what a Reddit timestamp is. None stays None (rule 6) — the root
        # falls back to the post's own `created_utc`, not to now().
        when = comment.created_at if comment else None
        if when is None and root.get("created_utc") is not None:
            when = datetime.fromtimestamp(float(root["created_utc"]), tz=UTC)
        documents.append({
            "id": member,
            "source": "reddit",
            "external_id": member.split(":", 1)[1],
            "url": (comment.url if comment else
                    f"https://www.reddit.com{root.get('permalink', '/')}"),
            "created_at": when,
            "text_ref": store.put(text).ref,
            "content_hash": content_hash(text),
            "author_id": None,
            "status": "kept",
        })

    export = {
        "thread_context_id": assembled.id,
        "thread_root_id": assembled.thread_root_id,
        "member_document_ids": list(assembled.member_document_ids),
        "flattened_text": assembled.flattened.text,
        "offset_map": assembled.flattened.as_offset_map(),
        "raw_text_of": raw_text_of,
        "provenance": {
            "platform": "reddit",
            "source": str(REDDIT_PAYLOAD).replace("\\", "/"),
            "built_by": "scripts/export_thread_contexts.py",
            "authoritative": "collect/assemble/ (E3). Supersedes "
                             "fixtures/threads/thread-1u1b22l.json per that "
                             "file's own build.py docstring.",
            "selection_method": assembled.selection_method,
            "pipeline_version": assembled.pipeline_version,
            # THE INPUT THAT MADE THE STAGING ROW IRREPRODUCIBLE. Recorded so
            # this file can be regenerated exactly; see the module docstring.
            "version_aliases": list(assembled_aliases),
            # A COUNT, NOT A PRESENCE CHECK. 35 aliases matching 0 documents
            # recorded identically to 1247 matching 27 for weeks. If this is 0,
            # `names_version` contributed nothing to the ranking and
            # `selection_method` is overstating what ran.
            "version_aliases_matched_documents": alias_match_count(
                assembled_aliases, [t for t in raw_text_of.values()]
            ),
            "version_aliases_of": len(raw_text_of),
            "version_aliases_source": "collect.registry.aliases.all_alias_rows("
                                      "seed_models()), specificity in "
                                      "(version, snapshot)",
        },
    }
    return export, documents, assembled.id


def build_blogs(store: RawStore, limit: int) -> list[tuple[dict, list[dict], str]]:
    """Stored articles that extract AND declare their own URL, up to `limit`.

    Was `build_blog`, returning the first match only, which is why the handoff
    carried two threads. An article with no declared URL is SKIPPED rather than
    exported with a placeholder: `https://example.invalid/article` in a url
    column is indistinguishable from a real one to everything downstream, and
    that is rule 6 - a missing value silently becoming a definite one.
    """
    out: list[tuple[dict, list[dict], str]] = []
    skipped_no_url = 0
    for path in sorted(p for p in Path("raw_store").rglob("*") if p.is_file()):
        if len(out) >= limit:
            break
        data = path.read_bytes()
        if b"<html" not in data[:4000].lower() and b"<!doctype" not in data[:200].lower():
            continue
        url = declared_url(data)
        if url is None:
            skipped_no_url += 1
            continue
        # IMPORTED AT THE POINT OF USE, for the reason triage's `_blog` is:
        # this call sits behind an HTML-only branch, so a run over a corpus
        # with no article payloads never needs trafilatura - but a
        # module-level import made every run need it.
        from collect.adapters.blog.parse import extract_article_text

        text = extract_article_text(data, url=url)
        if not text or len(text) < 1200:
            continue

        entry_id = f"sha256:{content_hash(data)[:16]}"
        article = ArticleInput(entry_id, text, url=url)
        assembled = assemble_article(article, store=store)
        document_id = blog_document_id(entry_id)

        document = blog_document_row(
            article, text_ref=path.as_posix(), content_hash=content_hash(data)
        )
        document["text_ref"] = store.put(text).ref

        export = {
            "thread_context_id": assembled.id,
            "thread_root_id": assembled.thread_root_id,
            "member_document_ids": list(assembled.member_document_ids),
            "flattened_text": assembled.flattened.text,
            "offset_map": assembled.flattened.as_offset_map(),
            # ONE member. `SPAN_CROSSES_COMMENTS` is unreachable here.
            "raw_text_of": {document_id: text},
            "provenance": {
                "platform": "blog",
                "source": url,
                "url_from": "the payload's own rel=canonical or og:url",
                "retention": CENSUS_BASIS,
                "built_by": "scripts/export_thread_contexts.py",
                "rulings": {
                    "selection_method": assembled.selection_method,
                    "hidden_children_min": assembled.hidden_children_min,
                    "entity_decoding": "off (BLOG_RULES) - trafilatura decodes twice",
                    "symbol_substitution": "on, and known-wrong; see "
                                           "docs/measurements/blog-symbol-census.md",
                },
                "pipeline_version": assembled.pipeline_version,
            },
        }
        out.append((export, [document], assembled.id))
    if skipped_no_url:
        print(f"  (skipped {skipped_no_url} stored articles with no declared URL)")
    return out


def main(out_dir: Path, *, limit: int | None = DEFAULT_THREADS) -> int:
    store = RawStore(Path(tempfile.mkdtemp()))
    (out_dir / "threads").mkdir(parents=True, exist_ok=True)

    statements: list[str] = []
    written: list[str] = []
    incomplete: list[dict] = []

    reddit_export, reddit_docs, reddit_id = build_reddit(store)
    asked = limit if limit is not None else 10**6
    blogs = build_blogs(store, limit=asked - 1)

    bundles = [(reddit_export, reddit_docs)]
    bundles.extend((export, documents) for export, documents, _ in blogs)

    if limit is not None and len(bundles) < limit:
        incomplete.append({
            "asked_for": limit,
            "produced": len(bundles),
            "why": (
                f"only {len(blogs)} stored articles both extracted to >=1200 "
                "chars AND declared their own URL, and there is exactly ONE "
                "stored Reddit payload (fixtures/reddit/"
                "thread-1u1b22l-getPostComments.json), so the Reddit side "
                "cannot contribute a second row. Nothing was padded."
            ),
        })

    for export, documents in bundles:
        name = export["thread_context_id"] + ".json"
        (out_dir / "threads" / name).write_text(
            json.dumps(export, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        written.append(name)
        for document in documents:
            statements.append(_insert("document", document))
        statements.append(_insert("thread_context", {
            "id": export["thread_context_id"],
            "thread_root_id": export["thread_root_id"],
            "member_document_ids": export["member_document_ids"],
            "flattened_text_ref": "flattened/inline-see-json",
            "offset_map": json.dumps(export["offset_map"]),
            "child_count": len(export["member_document_ids"]) - 1,
            "selection_method": export["provenance"].get(
                "selection_method",
                export["provenance"].get("rulings", {}).get("selection_method"),
            ),
            "observed_children": 0 if export["provenance"]["platform"] == "blog" else None,
            "hidden_children_min": None,
            "hidden_branches_unsized": 0 if export["provenance"]["platform"] == "blog" else None,
            "pipeline_version": export["provenance"]["pipeline_version"],
        }))

    incomplete.append({
        "thread": "thread_context_a32b878fb67b4bfa (t3_1vozb95)",
        "why": "present in staging, but no stored API payload exists in "
               "fixtures/ and its flattened_text_ref resolves in no local "
               "store. offset_map alone cannot be verified against anything, "
               "so it is omitted rather than half-exported.",
    })

    header = (
        "-- Generated by scripts/export_thread_contexts.py\n"
        "-- Load into a LOCAL Postgres. Order matters: document before\n"
        "-- thread_context is not an FK requirement (there is none between them)\n"
        "-- but claim references both, so load this whole file.\n"
        "--\n"
        "-- flattened_text_ref is a PLACEHOLDER. The real flattened text is\n"
        "-- inline in threads/*.json, because the object store it would point\n"
        "-- into is gitignored and machine-local. Nothing in judge/extract\n"
        "-- reads the column; ThreadInput takes the text directly.\n\n"
    )
    (out_dir / "load.sql").write_text(header + "\n\n".join(statements) + "\n",
                                     encoding="utf-8")

    manifest = {
        "purpose": "thread_context handoff for judge/ - extract path and cell path",
        "generated_by": "scripts/export_thread_contexts.py",
        "threads": written,
        "load_order": ["load.sql", "then read threads/*.json from judge/"],
        "document_id_scheme": {
            "note": (
                "ASKED FOR EXPLICITLY, because its absence took a message to "
                "surface last time. Two schemes, one per platform, and both are "
                "single-sourced functions rather than f-strings."
            ),
            "reddit": (
                "collect.adapters.reddit.reddit_document_id -> 'reddit:{fullname}'. "
                "THE FULLNAME IS KEPT WHOLE: 'reddit:t3_1u1b22l', not "
                "'reddit:1u1b22l'. fixtures/threads/build.py strips the t1_/t3_ "
                "prefixes and is NOT authoritative - E3 is."
            ),
            "blog": (
                "collect.assemble.article.blog_document_id -> 'blog:{entry_id}', "
                "where entry_id here is 'sha256:{content_hash[:16]}'. Normally "
                "entry_id is the publisher's own guid or link and is never "
                "derived from content; these rows come from raw_store, which is "
                "content-addressed and carries no guid, so the hash stands in. "
                "That is a property OF THIS EXPORT, not of the blog adapter."
            ),
            "why_it_matters": (
                "raw_text_of is keyed by document_id, so a scheme mismatch "
                "returns RAW_TEXT_MISSING for every quote in the thread - a "
                "naming failure that presents as a storage failure. That is how "
                "#57 was found."
            ),
        },
        "retention": CENSUS_BASIS,
        "url_coverage": (
            "BLOG URLS ARE REAL - every blog document.url is the publisher's own "
            "rel=canonical or og:url, read from the stored payload, and an article "
            "declaring neither was skipped rather than given a placeholder. "
            "REDDIT COMMENT URLS ARE NOT: the 5 t1_ rows carry "
            "'https://www.reddit.com/r/ClaudeAI/x/', a stand-in, because the "
            "getPostComments payload does not include per-comment permalinks and "
            "the root post's URL is the only real one on that side. Named because "
            "a synthetic URL in a url column is indistinguishable from a real one "
            "downstream, which is exactly the confusion the blog placeholder "
            "caused. The root post row IS real."
        ),
        "open_ruling": (
            "judge/CLAUDE.md: whether a URL under a delete_after date may be "
            "PUBLISHED is unresolved. Blog URLs are populated here so the "
            "render path can be exercised, and the date and basis travel with "
            "them - but this bundle does not answer that question and must not "
            "be treated as having answered it."
        ),
        "platform_count_note": (
            "document.source is the PLATFORM (reddit | blog | github), which "
            "judge/store/cells.py reads as `platform`. Two rows with different "
            "source values are what makes platform_count reach 2."
        ),
        "supersedes": "fixtures/threads/thread-1u1b22l.json (Engineer 2's "
                      "fixture tooling; disagrees on id convention, member "
                      "count and segment count - E3 is authoritative)",
        "incomplete": incomplete,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                           encoding="utf-8")

    print(f"wrote {out_dir}/")
    for name in written:
        export = json.loads((out_dir / "threads" / name).read_text(encoding="utf-8"))
        print(f"  threads/{name}")
        print(f"      platform  {export['provenance']['platform']}")
        print(f"      members   {len(export['member_document_ids'])}")
        print(f"      segments  {len(export['offset_map'])}")
        print(f"      flattened {len(export['flattened_text'])} chars")
        print(f"      raw_text  {len(export['raw_text_of'])} documents")
    print(f"  load.sql        {len(statements)} statements")
    print(f"  manifest.json   {len(incomplete)} incomplete thread(s) recorded")
    return 0


def _cli(argv: list[str] | None = None) -> int:
    """A command rather than a script with a positional path.

    `_handoff/` proved the shape and the objection to it was that a manual bundle
    is not an interface. So: `--out`, `--limit`, `--all`, and a size line — the
    manual step goes and no object-store decision is needed to remove it.

    WHERE THIS SHAPE STOPS WORKING, measured rather than left to be found
    (2026-08-20, staging):

        30 of 59 thread_contexts are exportable      19,046 bytes each inline
        29 are NOT — their flattened_text_ref resolves in no store this
           process can see, because the GitHub sweep wrote its payloads to a
           different directory than RAW_STORE_PATH
        0.54 MB for 30 threads · 16.1 MB projected at the 887-thread corpus

    **Size is not the ceiling. Resolvability is.** 16 MB of JSON is nothing; a
    bundle that silently contains 30 of 59 threads is the whole problem, which is
    why the count below is printed and not inferred. And a bundle structurally
    cannot carry `MISSING`, `CORRUPT` or `TOMBSTONED` — an unresolvable payload
    becomes an absent key, so the extractor sees a shorter thread rather than a
    read failure. However many bundles ship, the four read outcomes stay
    untested until both lanes address one store.
    """
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="_handoff", help="output directory")
    parser.add_argument(
        "--limit", type=int, default=DEFAULT_THREADS,
        help=f"threads to emit (default {DEFAULT_THREADS})")
    parser.add_argument(
        "--all", action="store_true",
        help="emit every exportable thread, and report what could not be read")
    args = parser.parse_args(argv)
    return main(Path(args.out), limit=None if args.all else args.limit)


if __name__ == "__main__":
    raise SystemExit(_cli())
