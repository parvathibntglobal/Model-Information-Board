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
from dataclasses import dataclass
from datetime import UTC, datetime

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

    def summary(self) -> str:
        return (
            f"blog assemble: {self.articles_seen} article(s), "
            f"{self.documents_inserted} document(s), "
            f"{self.contexts_inserted} thread_context(s), "
            f"{self.already_present} already present, "
            f"{self.nothing_extracted} with nothing extracted"
        )


def write_blog_run(conn, run, *, store: RawStore) -> BlogAssembleReport:
    """Assemble and write every stored article in one `FeedRun`.

    `run` is a `collect.adapters.blog.fetch.FeedRun`. Takes the run rather than a
    list of texts so the caller cannot accidentally pass articles from a feed
    whose terms gate refused — the gate fires in `fetcher_for_source`, upstream
    of anything this sees.
    """
    report = BlogAssembleReport()

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
        assembled = assemble_article(article, store=store, pipeline_version=run.pipeline_version)

        document = document_row(
            article,
            text_ref=article_fetch.artifact.ref,
            content_hash=article_fetch.artifact.content_hash,
            published_at=article_fetch.entry.published_at,
        )
        cursor = conn.execute(_DOCUMENT_SQL, document)
        inserted = max(0, cursor.rowcount)
        report.documents_inserted += inserted
        if not inserted:
            report.already_present += 1

        row = assembled.as_row()
        row["offset_map"] = json.dumps(row["offset_map"])
        row["assembled_at"] = datetime.now(UTC)
        cursor = conn.execute(_CONTEXT_SQL, row)
        report.contexts_inserted += max(0, cursor.rowcount)

    return report
