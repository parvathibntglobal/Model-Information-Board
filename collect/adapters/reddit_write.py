"""`document` rows for Reddit posts and comments — WITH `author_id`.

Until 2026-08-21 there was no Reddit document writer at all. The six `reddit`
rows on staging arrived through `_handoff/load.sql`, which sets `author_id` to
NULL, so **0 of 6 carried an author** against 30 of 31 for blog.

WHY THIS IS THE BLOCKER RATHER THAN A TIDY-UP
---------------------------------------------

`judge/curate/gate.py:count` dedups voices off `claim.author_id`, which comes
from `document.author_id`. A NULL author is not "an author we do not know" to
the gate - it is **no voice**. So:

    N_EFF_MINIMUM     = 3.0    weighted independent voices
    PLATFORM_MINIMUM  = 2      distinct platforms

    author rows in the database, 2026-08-21:   1
    documents with an author:                 30 of 64, all blog, ONE author

Blog is structurally one voice per feed - `from_blog` writes one row for a
`feed_declared` feed however many articles it has, correctly. **Reddit is the
only source in the corpus that is structurally many voices**, and it was the one
with no writer. Everything downstream reads `insufficient` and will keep doing so
however good extraction gets.

THREE THINGS THIS GETS RIGHT, ALL WITH PRECEDENT IN THIS REPOSITORY
-------------------------------------------------------------------

**1. Ids canonicalise through `author_external_id`.** `getProfile` returns
`id: '2ii4xgakc7'` where a post carries `author_fullname: 't2_2ii4xgakc7'` for
the same person, and `author` is `UNIQUE (source, external_id)` - so taking each
endpoint's spelling verbatim writes two rows for one engineer. That splits a
voice, and FR-17 then counts it twice while believing it counts once. Never the
username: Reddit allows renames, so a renamed account arrives as a new author and
a reused name merges two people.

**2. `handle_hash`, never the handle.** `hash_handle` casefolds, digests, and the
name goes out of scope. Data minimisation rather than secrecy - a digest of a
public username is reversible from a username list, and what it buys is that the
handle cannot be read out of a row, logged by accident, or published by a query
that forgot to exclude a column. It stays re-derivable from the raw store if the
publish path ever needs it (Developer Terms 5.2, unresolved and recorded).

**3. A comment with no author gets NO ROW, not a shared one.** `[deleted]` and
`[removed]` are markers rather than names, and `PLACEHOLDER_HANDLES` already
refuses them. The reason is arithmetic: a shared hash or a sentinel
`external_id` would merge every authorless comment into ONE author row, and the
gate would then read that single voice as corroborating itself. Corpus-wide there
are **115 Reddit documents with no `author_fullname`**; one shared row would turn
115 absences into one loud voice. They are counted as `unattributable` and
reported.

None of that is new work - `collect/assemble/authors.py` had all three. What was
missing was anything calling it.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence
from typing import Any

from collect.adapters.reddit import SOURCE_ID, author_external_id, reddit_document_id
from collect.assemble.authors import AuthorRow, from_reddit, hash_handle, write_authors

log = logging.getLogger(__name__)

DOCUMENT_SOURCE = SOURCE_ID

_INSERT = (
    "INSERT INTO document (id, source, external_id, url, created_at, fetched_at, "
    "thread_root_id, parent_id, text_ref, content_hash, engagement, author_id, status, "
    "harvest_run_id, retrieval_provenance) "
    "VALUES (%(id)s, %(source)s, %(external_id)s, %(url)s, %(created_at)s, now(), "
    "%(thread_root_id)s, %(parent_id)s, %(text_ref)s, %(content_hash)s, "
    # RETRIEVAL PROVENANCE IS THE CALLER'S CLAIM, NOT THIS STATEMENT'S.
    #
    # This read `'no_run_for_source'`, typed into the SQL, for every caller
    # whatever the caller did. The justification was a SUBREDDIT LISTING, which
    # renders no query and writes no `harvest_run` row — so a NULL
    # `harvest_run_id` there is COMPLETE rather than missing, and the column's
    # `not_recorded` default says the opposite.
    #
    # The reasoning was right and the placement was wrong. **It is a claim about
    # the RUN, not about the source**, and a hardcoded string cannot tell the two
    # apart: the per-model fetch's Reddit arm issues model-name QUERIES through
    # this same writer, and its 853 rows landed asserting that there had been
    # nothing to record. A positive claim that nothing is missing, on rows where
    # something was. That is worse than the absent value it was chosen over.
    #
    # So the caller types it, with no default — a caller that has not thought
    # about it must say so rather than inherit somebody else's claim. Rule 6 on
    # our own writer.
    "%(engagement)s, %(author_id)s, 'kept', %(harvest_run_id)s, "
    "%(retrieval_provenance)s) "
    "ON CONFLICT (source, external_id) DO NOTHING"
)

#: Sets the author on rows that already exist. Separate statement because the
#: insert conflicts away, and a backfill must not depend on having written the
#: document in the same call.
_SET_AUTHOR = (
    "UPDATE document SET author_id = %(author_id)s "
    "WHERE id = %(id)s AND author_id IS NULL"
)


def author_id_for(item: Any) -> str | None:
    """The `author.id` this post or comment attributes to, or None.

    None means "no stable identity", and it must stay None all the way to the
    column. Every fallback available here - the username, a sentinel, the
    document id - either splits one person across renames or merges many people
    into one voice.
    """
    external_id = author_external_id(getattr(item, "author_fullname", None))
    if not external_id:
        return None
    return AuthorRow(
        source=DOCUMENT_SOURCE,
        external_id=external_id,
        handle_hash=hash_handle(getattr(item, "author", None)),
    ).id


#: Every value `retrieval_provenance` may take from this writer, and what each
#: claims. `run_recorded` is absent deliberately: it requires a `harvest_run_id`
#: on the row, `document_retrieval_provenance_agrees_ck` enforces that, and this
#: statement does not write the id — so offering the value here would build a
#: row the database refuses.
REDDIT_PROVENANCE: tuple[str, ...] = (
    # A run exists and its id is on the row. THE LISTING SWEEP'S VALUE, and it
    # took a correction to get here.
    #
    # `no_run_for_source` was written for a listing on the grounds that no QUERY
    # is rendered, which is true. But the value does not say "no query" - it says
    # THIS SOURCE ISSUES NO PER-QUERY RUN, so a NULL `harvest_run_id` is complete.
    # The moment `ops/sweep_reddit.py` opens a `harvest_run` row per subreddit
    # that stops being true: a run exists, it is recordable, and
    # `document_retrieval_provenance_agrees_ck` then REQUIRES this value because
    # the id is set. Caught by wiring the id, not by reading the constraint.
    "run_recorded",
    # A subreddit listing that opened NO run row. Still reachable - a hand-run
    # fetch, or a sweep whose ledger write failed - and correct there.
    "no_run_for_source",
    # A run existed, or might have, and nobody wrote it down. This is where a
    # QUERY-shaped reddit run belongs - the per-model fetch's model-name arm, or
    # any future search sweep whose harvest_run id does not reach this writer.
    #
    # A fourth value `unreviewed_writer` was added on 2026-08-28 and withdrawn
    # the same day: it described the CODE that wrote the row rather than what
    # retrieved it, and a fourth value breaks `pipeline_status.py`, which counts
    # exactly three. See contract/tables.sql.
    "not_recorded",
)


def document_row(
    item: Any,
    *,
    retrieval_provenance: str,
    harvest_run_id: str | None = None,
    text_ref: str | None = None,
    content_hash: str | None = None,
) -> dict[str, Any]:
    """One `document` row for a post or a comment.

    Returns a dict rather than inserting, which is this lane's convention: a
    caller can see what is about to be stored. `thread_root_id` and `parent_id`
    are present for a comment and NULL for a post, because a post is its own root
    and inventing a self-reference would make "is this a root" unanswerable.

    **DISCRIMINATED ON THE FIELDS, NOT ON THE CLASS.** The first version asked
    `isinstance(item, RedditComment)`, and a test double caught what a real
    caller would have suffered in silence: anything carrying a thread and a
    parent but not that exact class — a backfill reading a stored payload, a
    re-parse, a later comment type — took the post branch and had its linkage
    written as NULL. `thread_root_id` NULL is already the state of all six
    reddit rows on staging, so this failure mode has a precedent and no alarm.
    A missing link must come from the data lacking it, never from a type check.

    `retrieval_provenance` is required and unvalidated-against-nothing: it must
    be one of `REDDIT_PROVENANCE`, and an unknown value raises here rather than
    reaching the CHECK as a 23514 that names a constraint instead of a caller.
    """
    if retrieval_provenance not in REDDIT_PROVENANCE:
        raise ValueError(
            f"retrieval_provenance={retrieval_provenance!r} is not one of "
            f"{REDDIT_PROVENANCE}. It is a claim about the RUN that produced this "
            f"row - whether a run exists, and whether its id reached the writer - "
            f"so it cannot be defaulted or guessed here."
        )
    # THE DATABASE CONSTRAINT, MIRRORED SO THE ERROR NAMES THE CALLER.
    # `document_retrieval_provenance_agrees_ck` enforces exactly this, and a
    # violation there arrives as a 23514 naming a constraint, which tells whoever
    # reads the traceback nothing about which argument was wrong.
    if (retrieval_provenance == "run_recorded") != (harvest_run_id is not None):
        raise ValueError(
            f"retrieval_provenance={retrieval_provenance!r} and "
            f"harvest_run_id={harvest_run_id!r} disagree. 'run_recorded' means the "
            f"id is on the row and every other value means it is not - "
            f"document_retrieval_provenance_agrees_ck refuses any other pairing, "
            f"because a provenance claim with nothing behind it is worse than an "
            f"absent one."
        )
    root = getattr(item, "thread_root_id", None)
    parent = getattr(item, "parent_id", None)
    created = getattr(item, "created_at", None)
    engagement = getattr(item, "engagement", None)
    return {
        "id": reddit_document_id(item.external_id),
        "source": DOCUMENT_SOURCE,
        "external_id": item.external_id,
        "url": getattr(item, "url", None),
        "created_at": created,
        "thread_root_id": root,
        "parent_id": parent,
        "text_ref": text_ref,
        "content_hash": content_hash,
        "engagement": json.dumps(engagement) if engagement is not None else None,
        "author_id": author_id_for(item),
        "harvest_run_id": harvest_run_id,
        "retrieval_provenance": retrieval_provenance,
    }


def write_documents(
    conn,
    items: Sequence[Any],
    *,
    retrieval_provenance: str,
    harvest_run_id: str | None = None,
    refs: dict[str, tuple[str | None, str | None]] | None = None,
    batch: int = 500,
) -> dict[str, int]:
    """Authors first, then documents. Returns counts, including what got no author.

    **ORDER IS A FOREIGN KEY, NOT A PREFERENCE.** `document.author_id` references
    `author.id`, so the author rows are written first - the same ordering
    `blog/write.py` records: *"written before the documents that reference it"*.

    BATCHED, for the reason `write_authors` and `github.write_documents` both
    record: one statement per row cost ten minutes for 4,391 rows against the
    remote instance, roughly 130ms of latency each and almost no work.

    `refs` maps `external_id -> (text_ref, content_hash)` for callers that have
    already stored payloads. Absent means both stay NULL, which is honest for a
    row whose bytes are not in this store - and NOT the same as a row whose
    payload is missing, which is `rawstore`'s alert to raise.
    """
    items = list(items)
    refs = refs or {}

    extraction = from_reddit(items)
    author_counts = write_authors(conn, extraction.rows, batch=batch)

    rows = []
    for item in items:
        ref, chash = refs.get(item.external_id, (None, None))
        rows.append(
            document_row(
                item,
                retrieval_provenance=retrieval_provenance,
                harvest_run_id=harvest_run_id,
                text_ref=ref,
                content_hash=chash,
            )
        )

    inserted = 0
    with conn.cursor() as cur:
        for start in range(0, len(rows), batch):
            cur.executemany(_INSERT, rows[start:start + batch])
            inserted += max(0, cur.rowcount)

    # ── AND THEN FILL THE AUTHOR ON ROWS THAT ALREADY EXISTED ────────────
    #
    # `ON CONFLICT DO NOTHING` is right for every other column and wrong for
    # this one. A document written before this writer existed conflicts away and
    # keeps `author_id` NULL — permanently, however many times the sweep runs,
    # because the conflict is silent and the row looks written. Measured on the
    # first real run: 196 items, 190 inserted, and the 6 that conflicted stayed
    # anonymous while the other 190 got authors.
    #
    # `author_id` is the one field where "already present, leave it" is the
    # wrong default, because NULL there was never a value anybody chose — it is
    # the absence this writer exists to close. `_SET_AUTHOR` is guarded by
    # `WHERE author_id IS NULL`, so a real attribution is never overwritten by a
    # later, possibly worse, parse.
    attributions = [
        {"id": r["id"], "author_id": r["author_id"]}
        for r in rows if r["author_id"] is not None
    ]
    attributed = 0
    with conn.cursor() as cur:
        for start in range(0, len(attributions), batch):
            cur.executemany(_SET_AUTHOR, attributions[start:start + batch])
            attributed += max(0, cur.rowcount)

    without_author = sum(1 for r in rows if r["author_id"] is None)
    return {
        "documents_seen": len(rows),
        "documents_inserted": inserted,
        # Rows that already existed and had no author until now. Reported
        # separately from `documents_inserted` because a re-run that attributes
        # 6 old rows and inserts 0 is doing real work, and a single "written"
        # counter would show it as a no-op.
        "authors_attached_to_existing": max(0, attributed - inserted),
        "authors_inserted": author_counts["inserted"],
        "authors_seen": author_counts["seen"],
        "distinct_authors": extraction.distinct_authors,
        # NAMED, NOT DROPPED. A comment whose account is gone has no voice, and
        # a count of them is the difference between "few voices" and "few
        # attributable voices" - two different findings about the same corpus.
        "documents_without_author": without_author,
        "unattributable": extraction.unattributable,
    }


def backfill_authors(conn, items: Iterable[Any], *, batch: int = 500) -> dict[str, int]:
    """Set `author_id` on Reddit documents that already exist without one.

    Only ever fills a NULL - `WHERE author_id IS NULL` - so re-running is safe
    and an author already attributed is never silently rewritten by a later,
    possibly worse, parse of the same payload.
    """
    items = list(items)
    extraction = from_reddit(items)
    author_counts = write_authors(conn, extraction.rows, batch=batch)

    updates = []
    no_identity = 0
    for item in items:
        author = author_id_for(item)
        if author is None:
            no_identity += 1
            continue
        updates.append({"id": reddit_document_id(item.external_id), "author_id": author})

    updated = 0
    with conn.cursor() as cur:
        for start in range(0, len(updates), batch):
            cur.executemany(_SET_AUTHOR, updates[start:start + batch])
            updated += max(0, cur.rowcount)

    return {
        "candidates": len(items),
        "documents_updated": updated,
        "authors_inserted": author_counts["inserted"],
        "distinct_authors": extraction.distinct_authors,
        "no_stable_identity": no_identity,
    }
