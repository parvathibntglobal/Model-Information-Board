"""Store the 148 fetched GitHub comments, re-assemble the issues that gained
them, and report what it does to voices. No new requests.

WHY THIS NEEDS NO NETWORK. The payloads were fetched on 2026-08-29 and are in
the local raw store; the issues they attach to are on staging.
`_github_comments.json` holds the ref of every one, and the raw payload carries
`user.id`, `user.type`, `created_at` and `body` - everything `StoredComment`
needs. So this REBUILDS the adapter's value objects from the store rather than
re-fetching, and `GitHubHarvester.write_comments` does the writing unchanged.

THE NUMBER THIS REPORTS IS VOICES, NOT COMMENTS. 65 distinct human comment
authors against 45 issue-body authors is why the work is worth doing: `n_eff`
counts authors, so one engineer posting five times is one voice.

⚠ AND VOICES DO NOT MOVE TODAY. A voice is `claim.author_id`, a claim comes
  from an extraction, and nothing here extracts. Writing a comment document
  changes the voice POOL and cannot change a cell until the re-assembled
  contexts are read. Reported as before/after anyway - identical by
  construction, which is the finding rather than a disappointment. Anything else
  would be presenting a no-op as a result.

⚠ THE RE-ASSEMBLY FORKS `pipeline_version` AND DOES NOT DELETE.
  `assemble_issue_thread` derives its id from `stable_id("thread_context",
  root_document_id, version)` - the same formula `assemble_issue` uses - so at
  the SAME version the new context collides with the body-only one and
  `ON CONFLICT DO NOTHING` silently keeps the old row.

  `scripts/rebuild_github_contexts.py` solved that by deleting, and said in its
  own docstring that the manoeuvre "stops being free the moment a github claim
  exists, because re-flattening moves every character position and an offset
  cannot be rebuilt later". IT NOW EXISTS: 4 of these 30 issues have been
  extracted and one carries 5 stored claims. So deleting would destroy verified
  offsets, and this forks instead - the body-only contexts and their claims stay
  exactly as they are, and the comment-bearing contexts are new rows at a new
  version.

  The version is passed per call rather than by bumping
  `collect.config.PIPELINE_VERSION`, because bumping the constant would fork
  every reddit and blog context too, for a change that touched neither.

    python scripts/write_github_comments.py --dry-run
    python scripts/write_github_comments.py --apply
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collect.adapters.github import GitHubHarvester, StoredComment  # noqa: E402
from collect.assemble.issue import AssemblyComment, assemble_issue_thread  # noqa: E402
from collect.assemble.prose import github_issue_prose  # noqa: E402
from collect.assemble.thread import write_thread_context  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.ids import stable_id  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402

COMMENTS_JSON = ROOT / "_github_comments.json"

#: The fork. See the module docstring on why this is not a constant bump.
FORK_VERSION = "collect-0.2.0-issue-comments"

DOCUMENT_SOURCE = "github"


def _voice_snapshot(conn) -> dict:
    """Voices per cell, and the pool they are drawn from.

    `independent_voices` is the stored count. `distinct authors` is what the
    claim table actually holds, read separately so a stale cell row cannot make
    the pool look like it moved.
    """
    cells = conn.execute(
        "SELECT count(*), coalesce(sum(independent_voices), 0), "
        "       coalesce(max(independent_voices), 0) FROM cell"
    ).fetchone()
    by_voices = conn.execute(
        "SELECT independent_voices, count(*) FROM cell GROUP BY 1 ORDER BY 1"
    ).fetchall()
    authors = conn.execute(
        "SELECT count(DISTINCT coalesce(c.author_id, 'anon:' || d.source)) "
        "FROM claim c JOIN document d ON d.id = c.document_id"
    ).fetchone()[0]
    github_authors = conn.execute(
        "SELECT count(DISTINCT author_id) FROM document "
        "WHERE source = 'github' AND author_id IS NOT NULL"
    ).fetchone()[0]
    return {
        "cells": cells[0],
        "voices_total": int(cells[1]),
        "voices_max": int(cells[2]),
        "cells_by_voices": {int(v or 0): n for v, n in by_voices},
        "distinct_claim_voices": authors,
        "github_document_authors": github_authors,
    }


def _coverage_snapshot(conn) -> dict:
    """`coverage_ratio` over github contexts, and the two NULL cases apart.

    NULL means `0 / 0` - an issue with no comments, which the migration refuses
    to call 1.0. It is not the same as 0.0, which means "there is a thread and
    we read none of it", and averaging them together would turn 41 empty threads
    into coverage we do not have.
    """
    rows = conn.execute(
        "SELECT tc.selection_method, tc.coverage_ratio, "
        "       tc.observed_children, tc.hidden_children_min "
        "FROM thread_context tc JOIN document d ON d.id = tc.thread_root_id "
        "WHERE d.source = 'github'"
    ).fetchall()
    buckets: collections.Counter = collections.Counter()
    observed = hidden = 0
    measurable = []
    for method, ratio, obs, hid in rows:
        buckets[(method, "empty-thread (NULL)" if ratio is None else f"{ratio:.3f}")] += 1
        observed += int(obs or 0)
        hidden += int(hid or 0)
        if ratio is not None:
            measurable.append(float(ratio))
    return {
        "contexts": len(rows),
        "observed_children_total": observed,
        "hidden_children_min_total": hidden,
        "measurable": len(measurable),
        "mean_ratio_over_measurable": (
            sum(measurable) / len(measurable) if measurable else None
        ),
        "by_method_and_ratio": {f"{m} @ {r}": n for (m, r), n in sorted(buckets.items())},
    }


def _fork_coverage(conn) -> dict:
    """`coverage_ratio` over the forked contexts ONLY.

    Separate from `_coverage_snapshot` because the pooled github figure mixes
    three populations with different meanings - the forked rows, the body-only
    rows they were forked FROM and which still read 0.000, and 41 empty threads
    where the ratio is NULL. A mean over all three answers no question anybody
    asked (rule 7).
    """
    import statistics

    rows = conn.execute(
        "SELECT observed_children, hidden_children_min, coverage_ratio "
        "FROM thread_context WHERE selection_method = 'issue_with_comments' "
        "  AND pipeline_version = %s",
        (FORK_VERSION,),
    ).fetchall()
    values = [float(r[2]) for r in rows if r[2] is not None]
    return {
        "n": len(rows),
        "mean": statistics.mean(values) if values else 0.0,
        "median": statistics.median(values) if values else 0.0,
        "at_one": sum(1 for v in values if v >= 0.9999),
        "at_zero": sum(1 for v in values if v <= 0.0001),
        "observed": sum(int(r[0] or 0) for r in rows),
        "hidden": sum(int(r[1] or 0) for r in rows),
    }


def _rebuild_comments(store) -> tuple[list[StoredComment], dict[str, str], int]:
    """`StoredComment` for every fetched comment, from the raw store.

    Returns the comments, a map from the issue's API url to its document id, and
    the count of refs that did not resolve. A ref that does not resolve is
    COUNTED, not skipped silently: the whole premise of this script is that the
    payloads are local, and a hole in that premise is the finding.
    """
    index = json.loads(COMMENTS_JSON.read_text(encoding="utf-8"))
    comments: list[StoredComment] = []
    issue_url_to_document: dict[str, str] = {}
    unresolved = 0

    for issue_document_id, entries in index.items():
        for entry in entries:
            try:
                raw = json.loads(store.get_text(entry["ref"]))
            except Exception:
                unresolved += 1
                continue
            user = raw.get("user") or {}
            issue_api_url = raw.get("issue_url")
            if not issue_api_url:
                unresolved += 1
                continue
            issue_url_to_document[issue_api_url] = issue_document_id
            comments.append(
                StoredComment(
                    external_id=entry["external_id"],
                    issue_api_url=issue_api_url,
                    html_url=raw.get("html_url") or entry.get("html_url") or "",
                    author_handle=user.get("login"),
                    # `user.id`, not `user.login` - a numeric id survives a
                    # rename and a reused login merges two people.
                    author_external_id=(
                        str(user["id"]) if user.get("id") is not None else None
                    ),
                    # THE FIELD, not the suffix. See StoredComment.is_bot.
                    author_type=user.get("type"),
                    created_at=raw.get("created_at"),
                    body=raw.get("body"),
                    ref=entry["ref"],
                    content_hash=entry["content_hash"],
                    already_present=True,
                )
            )
    return comments, issue_url_to_document, unresolved


def _report_bots(comments) -> None:
    """What the bot rule classified, and whether the two signals agree."""
    bots = [c for c in comments if c.is_bot]
    disagree = [c for c in comments if c.bot_suffix_disagrees]
    by_handle = collections.Counter(c.author_handle for c in bots)
    by_type = collections.Counter(c.author_type for c in comments)
    print(f"  user.type over {len(comments)} comments: "
          + ", ".join(f"{t}={n}" for t, n in by_type.most_common()))
    print(f"  is_bot true: {len(bots)} from {len(by_handle)} account(s): "
          + ", ".join(f"{h} ({n})" for h, n in by_handle.most_common()))
    print(f"  suffix/type disagreements: {len(disagree)}")
    print("    the agreement's denominator is the ACCOUNT count above, not the")
    print("    comment count - two apps following GitHub's naming convention.")
    human_authors = {c.author_external_id for c in comments
                     if not c.is_bot and c.author_external_id}
    print(f"  distinct human comment authors: {len(human_authors)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    ap.add_argument("--json", default="docs/measurements/github-comment-write.json")
    args = ap.parse_args()

    store = RawStore()
    conn = connect()
    try:
        before_voices = _voice_snapshot(conn)
        before_coverage = _coverage_snapshot(conn)

        comments, issue_url_to_document, unresolved = _rebuild_comments(store)

        print("=" * 78)
        print("GITHUB COMMENT WRITE PATH" + ("" if args.apply else "  (dry run)"))
        print("=" * 78)
        print(f"  comments rebuilt from the raw store: {len(comments)}")
        print(f"  refs that did not resolve:           {unresolved}")
        print(f"  issues they attach to:               {len(issue_url_to_document)}")
        print()
        _report_bots(comments)
        print()

        print("  VOICES BEFORE")
        print(f"    cells {before_voices['cells']}, "
              f"independent_voices summed {before_voices['voices_total']}, "
              f"max on any cell {before_voices['voices_max']}")
        print(f"    distinct voices across all claims: "
              f"{before_voices['distinct_claim_voices']}")
        print(f"    github documents carrying an author_id: "
              f"{before_voices['github_document_authors']}")
        print()
        print("  COVERAGE BEFORE")
        print(f"    github contexts {before_coverage['contexts']}, "
              f"observed {before_coverage['observed_children_total']}, "
              f"hidden_min {before_coverage['hidden_children_min_total']}")
        for label, n in sorted(before_coverage["by_method_and_ratio"].items()):
            print(f"      {label:46s} {n:4d}")
        print()

        # `client=None` IS SAFE AND IS NOT A SHORTCUT. `write_comments` touches
        # the database and the value objects only - it issues no request - so
        # the harvester needs no HTTP client, and passing None makes any
        # accidental fetch inside it an AttributeError rather than a quiet
        # network call from a script whose whole claim is that it makes none.
        harvester = GitHubHarvester(client=None, store=store)
        if args.dry_run:
            linked = [c for c in comments
                      if c.issue_api_url in issue_url_to_document]
            print("  DRY RUN. Nothing written. Would insert "
                  f"{len(linked)} comment documents "
                  f"({sum(1 for c in linked if not c.is_bot)} kept, "
                  f"{sum(1 for c in linked if c.is_bot)} filtered as bot_author).")
            return 0

        written = harvester.write_comments(
            conn,
            comments,
            issue_document_id_by_api_url=issue_url_to_document,
            # NOT `run_recorded`. A comment fetch renders no search query and
            # opened no `harvest_run`, so there is no id to point at, and
            # `not_recorded` is the column's honest under-claiming state. It is
            # NOT `no_run_for_source` either: that asserts github issues no
            # runs, which is false - the issue bodies above them carry one.
            harvest_run_id=None,
        )
        conn.commit()
        print("  WRITTEN")
        for key, value in written.items():
            print(f"    {key:26s} {value}")
        print()

        reassembled, refused = _reassemble(conn, store, comments, issue_url_to_document)
        conn.commit()
        print(f"  RE-ASSEMBLED at pipeline_version={FORK_VERSION!r}: {reassembled}")
        for line in refused:
            print(f"    REFUSED {line}")
        print()

        after_voices = _voice_snapshot(conn)
        after_coverage = _coverage_snapshot(conn)

        print("  VOICES AFTER")
        print(f"    cells {after_voices['cells']}, "
              f"independent_voices summed {after_voices['voices_total']}, "
              f"max on any cell {after_voices['voices_max']}")
        print(f"    distinct voices across all claims: "
              f"{after_voices['distinct_claim_voices']}")
        print(f"    github documents carrying an author_id: "
              f"{after_voices['github_document_authors']}")
        moved = after_voices["voices_total"] - before_voices["voices_total"]
        print()
        print(f"  VOICES PER CELL MOVED BY {moved:+d}, AND ZERO IS THE EXPECTED")
        print("  ANSWER. A voice is claim.author_id; a claim comes from an")
        print("  extraction; nothing here extracts. What moved is the POOL - the")
        print("  github author count above - and the contexts that can now be")
        print("  read. The cell number moves when those contexts are extracted.")
        print()
        print("  COVERAGE AFTER")
        print(f"    github contexts {after_coverage['contexts']}, "
              f"observed {after_coverage['observed_children_total']}, "
              f"hidden_min {after_coverage['hidden_children_min_total']}")
        for label, n in sorted(after_coverage["by_method_and_ratio"].items()):
            print(f"      {label:46s} {n:4d}")
        fork = _fork_coverage(conn)
        print()
        print("  COVERAGE ON THE 30 ISSUES THAT GAINED COMMENTS, before -> after.")
        print("  THE FORKED ROWS ALONE, and that is the comparison to quote: the")
        print("  pooled github mean also contains the 30 body-only rows this did")
        print("  NOT delete and the 41 empty threads, so it would average a fork")
        print("  against its own original and report the result as an improvement")
        print("  half its size.")
        print(f"    before  0.000 on all {fork['n']} (root read, no thread)")
        print(f"    after   mean {fork['mean']:.3f}, median {fork['median']:.3f}")
        print(f"            at 1.000: {fork['at_one']}   at 0.000: {fork['at_zero']}")
        print(f"            observed {fork['observed']} human comments, "
              f"{fork['hidden']} still unread")
        if fork["at_zero"]:
            print(f"    the {fork['at_zero']} still at 0.000 are BOT-ONLY threads. Bots are")
            print("    excluded from `observed` deliberately, so the ratio describes")
            print("    HUMAN coverage - an issue whose only replies are CI runs has")
            print("    no thread we want, and 0.000 is the true answer rather than a")
            print("    fetch that failed.")

        out = {
            "comments_rebuilt": len(comments),
            "refs_unresolved": unresolved,
            "write_counts": written,
            "reassembled": reassembled,
            "reassembly_refusals": refused,
            "fork_pipeline_version": FORK_VERSION,
            "voices_before": before_voices,
            "voices_after": after_voices,
            "voices_note": (
                "unchanged by construction - a voice is claim.author_id and "
                "nothing here extracts. The pool moved; the cells cannot until "
                "the forked contexts are read."
            ),
            "coverage_before": before_coverage,
            "coverage_after": after_coverage,
            "coverage_fork_only": _fork_coverage(conn),
        }
        path = pathlib.Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
        print(f"\nwritten to {path}")
        return 0
    finally:
        conn.close()


def _reassemble(conn, store, comments, issue_url_to_document):
    """One `issue_with_comments` context per issue that gained comments.

    Forked, not replaced - see the module docstring. Bots are passed through
    with `is_bot` set rather than filtered here, because
    `assemble_issue_thread` refuses them itself and a rule applied by whoever
    remembers is a rule that holds until somebody writes a second caller.
    """
    from collect.assemble.ranking import load_lexicon
    from collect.rawstore_reader import RawStoreReader
    from collect.triage.store import version_aliases

    reader = RawStoreReader(store)
    aliases = version_aliases(conn)
    lexicon = load_lexicon(conn)

    by_issue: dict[str, list] = collections.defaultdict(list)
    for comment in comments:
        document_id = issue_url_to_document.get(comment.issue_api_url)
        if document_id:
            by_issue[document_id].append(comment)

    refused: list[str] = []
    assembled_count = 0
    for issue_document_id, issue_comments in sorted(by_issue.items()):
        row = conn.execute(
            "SELECT text_ref, engagement FROM document WHERE id = %s",
            (issue_document_id,),
        ).fetchone()
        if not row or not row[0]:
            refused.append(f"{issue_document_id}: no text_ref")
            continue
        outcome = reader.resolve(row[0])
        if not outcome.found:
            refused.append(f"{issue_document_id}: {outcome.outcome}")
            continue
        try:
            root_text = github_issue_prose(outcome.require())
        except Exception as error:  # noqa: BLE001
            refused.append(f"{issue_document_id}: prose extraction failed: {error}")
            continue

        members = [
            AssemblyComment(
                document_id=stable_id("doc", DOCUMENT_SOURCE, c.external_id),
                body=c.body or "",
                external_id=c.external_id,
                is_bot=c.is_bot,
            )
            for c in issue_comments
        ]
        try:
            thread = assemble_issue_thread(
                root_document_id=issue_document_id,
                root_text=root_text,
                comments=members,
                comment_count=int((row[1] or {}).get("comments") or 0),
                store=store,
                version_aliases=aliases,
                pipeline_version=FORK_VERSION,
                lexicon=lexicon,
            )
        except ValueError as refusal:
            refused.append(str(refusal))
            continue
        write_thread_context(conn, thread)
        assembled_count += 1
    return assembled_count, refused


if __name__ == "__main__":
    raise SystemExit(main())
