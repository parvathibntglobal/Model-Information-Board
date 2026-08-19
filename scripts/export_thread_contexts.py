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

A FIRST DIAGNOSIS OF THIS THAT WAS WRONG, RECORDED SO IT IS NOT REPEATED:
`version_aliases`. `rank_children` scores through `names_version`, so an alias
set looked like the obvious input. Measured, it is not: `()` and the full
registry surface set produce IDENTICAL members and identical scores
(2.521, 1.2459, 1.1437, 1.1331, 1.0978) on this thread. The aliases are still
inlined in `provenance` below, because recording a scoring input costs nothing
and this export should be reproducible whatever the cause turns out to be — but
they are not the cause.

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
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.adapters.blog.parse import extract_article_text  # noqa: E402
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
from collect.rawstore import RawStore  # noqa: E402
from collect.registry.aliases import all_alias_rows  # noqa: E402
from collect.registry.seed import seed_models  # noqa: E402

REDDIT_PAYLOAD = Path("fixtures/reddit/thread-1u1b22l-getPostComments.json")


def version_aliases() -> tuple[str, ...]:
    """Version- and snapshot-specificity surfaces from the registry seed.

    `family` surfaces are EXCLUDED, per `names_version`'s own docstring: a bare
    `sonnet` names a line rather than a tier, and counting it would credit a
    document that never said which model it meant.

    Derived rather than hardcoded, and inlined into the export's provenance,
    because this is the input that made the staging row irreproducible.
    """
    rows = all_alias_rows(seed_models())
    return tuple(sorted(
        {r.normalized for r in rows if r.specificity in ("version", "snapshot")}
    ))


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
        documents.append({
            "id": member,
            "source": "reddit",
            "external_id": member.split(":", 1)[1],
            "url": (comment.url if comment else
                    f"https://www.reddit.com{root.get('permalink', '/')}"),
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
            "version_aliases_source": "collect.registry.aliases.all_alias_rows("
                                      "seed_models()), specificity in "
                                      "(version, snapshot)",
        },
    }
    return export, documents, assembled.id


def build_blog(store: RawStore) -> tuple[dict, list[dict], str] | None:
    """The first stored article that extracts, so the blog row is real text."""
    for path in sorted(p for p in Path("raw_store").rglob("*") if p.is_file()):
        data = path.read_bytes()
        if b"<html" not in data[:4000].lower() and b"<!doctype" not in data[:200].lower():
            continue
        text = extract_article_text(data, url="https://example.invalid/article")
        if not text or len(text) < 1200:
            continue

        entry_id = f"sha256:{content_hash(data)[:16]}"
        article = ArticleInput(entry_id, text, url="https://example.invalid/article")
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
                "source": "a harvested article, url withheld: the census corpus "
                          "carries a delete_after date and this file does not",
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
        return export, [document], assembled.id
    return None


def main(out_dir: Path) -> int:
    store = RawStore(Path(tempfile.mkdtemp()))
    (out_dir / "threads").mkdir(parents=True, exist_ok=True)

    statements: list[str] = []
    written: list[str] = []
    incomplete: list[dict] = []

    reddit_export, reddit_docs, reddit_id = build_reddit(store)
    blog = build_blog(store)

    bundles = [(reddit_export, reddit_docs)]
    if blog is None:
        incomplete.append({
            "thread": "blog",
            "why": "no stored article in raw_store extracted to >=1200 chars. "
                   "Run scripts/blog_so_sweep.py first.",
        })
    else:
        bundles.append((blog[0], blog[1]))

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


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "_handoff")))
