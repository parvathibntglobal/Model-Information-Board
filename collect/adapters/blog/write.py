"""Blog documents and `thread_context` rows, written. The path's last mile.

WHY THIS MODULE EXISTS AT ALL
----------------------------
`assemble_article` landed with no production caller — only a script and tests.
That is the same defect as `assert_no_fixtures` having no caller (issue #27,
closed 2026-08-18) and it is worth naming rather than repeating quietly: a
component that is correct and uncalled is indistinguishable, from outside, from
one that is absent. `judge/` reading zero blog rows cannot tell the difference
between "the assembler is broken" and "nothing runs it".

So this is the caller, and `scripts/harvest_blogs.py` calls this.

WHAT IT WRITES, AND IN WHICH ORDER
----------------------------------
    document          one per fetched article, `source = 'blog'`
    thread_context    one per article, a thread of ONE

Documents first, because `claim` references both and a `thread_context` whose
members do not exist as documents gives `raw_text_of` nothing to resolve. There
is no FK between the two tables — `member_document_ids` is a `text[]` — so
nothing enforces this order and it is a decision rather than a constraint.

**And the document is READ BACK before assembly runs.** The order alone is not
the point: assembly used to be handed the same in-memory object the document row
was built from, so the two ids agreed because one function computed both. The
database is now the carrier between them, and `member_document_ids` is checked
against `document` after the write. Both are cheap, and together they are the
difference between a verification and a restatement.

WHAT IT DOES NOT DO
-------------------
It does not triage, score or extract. `document.status` stays `'kept'`, which is
the schema default and means *this stage did not filter*, not *this passed*.
Triage sets it later; a stage that has not run must not look like a stage that
passed (rule 4).

It does not write `author`. A blog's byline resolves through
`collect/assemble/authors.py`, whose `resolves_to_voices` measurement is per
feed, and a per-article author row invented here would create a voice the
identity clustering never agreed to. `document.author_id` stays NULL, which is
honest: unknown, not anonymous.

`ON CONFLICT DO NOTHING` on both, for the reason `github.write_documents` gives:
re-fetching an unchanged article is legitimate and not an error. For
`thread_context` it is stronger — `offset_map` is what every stored quote
resolves against, so replacing one in place would silently invalidate claims
already written against it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from collect.adapters.blog.parse import extract_article_text
from collect.assemble.article import ArticleInput, assemble_article, document_row
from collect.rawstore import RawStore

_DOCUMENT_SQL = (
    "INSERT INTO document (id, source, external_id, url, created_at, fetched_at, "
    "text_ref, content_hash, author_id, status) "
    "VALUES (%(id)s, %(source)s, %(external_id)s, %(url)s, %(created_at)s, now(), "
    "%(text_ref)s, %(content_hash)s, %(author_id)s, %(status)s) "
    "ON CONFLICT (source, external_id) DO NOTHING"
)

#: Read the row back by the key the INSERT used, not by the id we computed.
#: See `write_blog_run` — this is the whole point of the two-step.
_DOCUMENT_READ_SQL = (
    "SELECT id, text_ref FROM document WHERE source = %(source)s "
    "AND external_id = %(external_id)s"
)

#: Every member of a written `thread_context` must be a row in `document`.
#: `member_document_ids` is a text[] with no FK, so nothing enforces it.
_MEMBERS_RESOLVE_SQL = (
    "SELECT m FROM unnest(%(members)s::text[]) AS m "
    "LEFT JOIN document d ON d.id = m WHERE d.id IS NULL"
)

_CONTEXT_SQL = (
    "INSERT INTO thread_context (id, thread_root_id, member_document_ids, "
    "flattened_text_ref, offset_map, child_count, selection_method, "
    "observed_children, hidden_children_min, hidden_branches_unsized, "
    "assembled_at, pipeline_version) "
    "VALUES (%(id)s, %(thread_root_id)s, %(member_document_ids)s, "
    "%(flattened_text_ref)s, %(offset_map)s, %(child_count)s, "
    "%(selection_method)s, %(observed_children)s, %(hidden_children_min)s, "
    "%(hidden_branches_unsized)s, %(assembled_at)s, %(pipeline_version)s) "
    "ON CONFLICT (id) DO NOTHING"
)


@dataclass
class BlogAssembleReport:
    """What was written, and what was skipped and why. Never a bare total."""

    articles_seen: int = 0
    #: `extract_article_text` returned None — a nav page, a paywall stub, a JS
    #: shell. NOT an empty article, and never written as a document with no body.
    nothing_extracted: int = 0
    documents_inserted: int = 0
    contexts_inserted: int = 0
    #: Already present. A re-fetch of an unchanged article, not a failure.
    already_present: int = 0
    #: The document was written or found, and reading it back returned nothing.
    #: Should be impossible; counted because "impossible" is how the last two
    #: defects in this lane described themselves.
    unreadable_after_write: int = 0

    #: Author rows written for this feed. 1 for a `feed_declared` or `team`
    #: byline, which is the voice count the contract measured.
    author_rows: int = 0
    #: An `entry`-byline feed produced several authors and no per-document
    #: mapping exists yet, so those documents keep `author_id` NULL. Counted
    #: rather than attributed to the first one.
    authors_per_entry_unwired: int = 0
    #: `thread_context` rows whose `member_document_ids` did not all resolve to
    #: a `document` row. THE CHECK THE LAST VERIFICATION COULD NOT MAKE, because
    #: it supplied both sides itself.
    members_unresolved: int = 0

    def summary(self) -> str:
        return (
            f"blog assemble: {self.articles_seen} article(s), "
            f"{self.documents_inserted} document(s), "
            f"{self.contexts_inserted} thread_context(s), "
            f"{self.already_present} already present, "
            f"{self.nothing_extracted} with nothing extracted, "
            f"{self.members_unresolved} with unresolved members, "
            f"{self.unreadable_after_write} unreadable after write"
        )


def write_blog_run(
    conn, run, *, store: RawStore, feed: Mapping[str, Any] | None = None
) -> BlogAssembleReport:
    """Assemble and write every stored article in one `FeedRun`.

    `feed` IS THE CONTRACT ENTRY, AND SUPPLYING IT IS WHAT GIVES A DOCUMENT AN
    AUTHOR. This function wrote none for weeks, on the reason recorded below:
    a per-article author row would create a voice nobody agreed to. That is right
    about per-ARTICLE rows and the unit is the FEED — `contract/sources.yaml`
    carries `byline_source` and `resolves_to_voices` per feed, so a
    `feed_declared` blog with thirty articles is ONE voice with thirty documents.
    See `assemble.authors.from_blog` for the four cases the contract rules.

    Omitting `feed` keeps the old behaviour — `author_id` NULL, honestly unknown
    — so no existing caller changes meaning by not being updated.

    `run` is a `collect.adapters.blog.fetch.FeedRun`. Takes the run rather than a
    list of texts so the caller cannot accidentally pass articles from a feed
    whose terms gate refused — the gate fires in `fetcher_for_source`, upstream
    of anything this sees.
    """
    report = BlogAssembleReport()

    # ── the author, once per run, because the run IS one feed ─────────────
    #
    # Written before the documents that reference it: `document.author_id` is a
    # foreign key, so the order is not a preference.
    author_id: str | None = None
    if feed is not None:
        from collect.assemble.authors import from_blog, write_authors

        extraction = from_blog(feed, [a.entry for a in run.articles if a.stored])
        if len(extraction.rows) == 1:
            write_authors(conn, extraction.rows)
            author_id = extraction.rows[0].id
            report.author_rows = 1
        elif len(extraction.rows) > 1:
            # An `entry`-byline feed: several voices in one run, and a document
            # gets whichever wrote it. Not this run's shape yet — the nine feeds
            # in the contract that do this have no stored articles — so it is
            # counted and left NULL rather than guessed at.
            write_authors(conn, extraction.rows)
            report.author_rows = len(extraction.rows)
            report.authors_per_entry_unwired = len(extraction.rows)

    for article_fetch in run.articles:
        if not article_fetch.stored:
            continue
        report.articles_seen += 1

        payload = store.get(article_fetch.artifact.ref)
        text = extract_article_text(payload, url=article_fetch.entry.url)
        if not text:
            # Rule 4 and rule 6 together: nothing extracted is not an empty
            # article. Counted and named, never written as a document with an
            # empty body — that would verify every quote against nothing and
            # read as a fabricating extractor.
            report.nothing_extracted += 1
            continue

        article = ArticleInput(
            entry_id=article_fetch.entry.entry_id,
            text=text,
            url=article_fetch.entry.url,
        )

        # ── DOCUMENT FIRST, THEN READ IT BACK, THEN ASSEMBLE ──────────────
        #
        # This used to assemble from `article` and build the document row from
        # the same `article`, so `thread_context.member_document_ids` and
        # `document.id` agreed BECAUSE ONE FUNCTION COMPUTED BOTH. That is
        # `tests/conftest.py`'s shape #57 exactly: a variable the caller
        # supplies to both sides is a variable neither side can check, and the
        # last time it went wrong it surfaced as `RAW_TEXT_MISSING` for every
        # quote in a thread — a naming failure wearing a storage failure's
        # clothes.
        #
        # Now the database is the carrier. The document is written, read back by
        # `(source, external_id)` — the key the INSERT used, not the id we
        # computed — and assembly is handed the id THE DATABASE HOLDS. If the
        # two conventions ever disagree, the read returns a different id and the
        # member list is wrong in a way the check below can see.
        document = document_row(
            article,
            text_ref=article_fetch.artifact.ref,
            content_hash=article_fetch.artifact.content_hash,
            published_at=article_fetch.entry.published_at,
            author_id=author_id,
        )
        cursor = conn.execute(_DOCUMENT_SQL, document)
        inserted = max(0, cursor.rowcount)
        report.documents_inserted += inserted
        if not inserted:
            report.already_present += 1

        stored_row = conn.execute(
            _DOCUMENT_READ_SQL,
            {"source": document["source"], "external_id": document["external_id"]},
        ).fetchone()
        if stored_row is None:
            # Written or already present, and not readable. Never seen; counted
            # rather than assumed away, and the article is skipped rather than
            # assembled against an id nothing holds.
            report.unreadable_after_write += 1
            continue
        stored_document_id = stored_row[0]

        assembled = assemble_article(
            article,
            store=store,
            pipeline_version=run.pipeline_version,
            document_id=stored_document_id,
        )

        row = assembled.as_row()
        row["offset_map"] = json.dumps(row["offset_map"])
        row["assembled_at"] = datetime.now(UTC)
        cursor = conn.execute(_CONTEXT_SQL, row)
        report.contexts_inserted += max(0, cursor.rowcount)

        # `member_document_ids` is a text[] and carries no FK, so this is the
        # only thing that makes "the members exist" a fact rather than a hope.
        missing = conn.execute(
            _MEMBERS_RESOLVE_SQL, {"members": list(assembled.member_document_ids)}
        ).fetchall()
        if missing:
            report.members_unresolved += 1

    return report
