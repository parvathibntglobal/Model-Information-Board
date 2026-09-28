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
identity clustering never agreed to. `document.author_id` stays NULL where no
byline resolved, which is honest: unknown, not anonymous.

WAS THE ONLY MODULE IN THE REPOSITORY THAT SET `document.author_id` UNTIL
2026-08-21 - `collect/adapters/reddit_write.py` and `github.py` now do too.
The sentence below is kept because its reasoning about the blog UNIT is
unchanged and is the part that gets re-litigated. AND
THAT IS READ AS GENERAL. Measured 2026-08-21: the column is set on 30 of 31
blog rows and on **0 of 6 reddit rows and 0 of 27 github rows**; `author` holds
one row, `blog:simonwillison.net`. So a reader who finds `author_id` populated
here reasonably assumes documents carry authorship, and two of three platforms
do not.

It matters downstream rather than here. `judge/curate/gate.py:count` dedups
voices off `claim.author_id`, which comes from `document.author_id` - so the
four Reddit claims on staging collapse to `independent_voices = 1` in a thread
with 152 distinct commenters. The Reddit and GitHub paths need to write it
before anything counts voices from those platforms.

**Third column this week populated by one adapter and read as general** - the
others were `document.specificity_score` (no writer at all) and
`document.has_conditions` (never True on any populated row). The shape is worth
naming: a column that one path fills looks like a column the schema fills.

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

from collect.adapters.blog.parse import (
    extract_article_text,
    strip_template_block,
    template_block_for,
)
from collect.assemble.article import ArticleInput, assemble_article, document_row
from collect.rawstore import RawStore

#: THE LITERAL BECAME A PARAMETER, WHICH IS THE MIGRATION IT WAS WRITTEN FOR.
#:
#: This SQL carried `'no_run_for_source'` hardcoded, with a comment saying a feed
#: fetch "could become a run row later and move these documents to
#: `run_recorded` — this literal is what makes that a VISIBLE migration rather
#: than a silent reinterpretation of NULLs". `harvest_blogs.py` opens a
#: `harvest_run` row as of 2026-09-17, so that is what this is.
#:
#: BOTH VALUES STAY REACHABLE, and that is deliberate rather than transitional.
#: A caller with no run — `write_blog_run` called directly, as the tests do —
#: still writes `no_run_for_source`, which remains TRUE for it. Replacing the
#: literal with the other literal would have made every such caller assert a run
#: that did not happen.
#:
#: `document_retrieval_provenance_agrees_ck` forbids the two columns
#: disagreeing, so they are computed together in `_provenance` and never passed
#: separately.
_DOCUMENT_SQL = (
    "INSERT INTO document (id, source, external_id, url, created_at, fetched_at, "
    "text_ref, content_hash, author_id, status, retrieval_provenance, "
    "harvest_run_id) "
    "VALUES (%(id)s, %(source)s, %(external_id)s, %(url)s, %(created_at)s, now(), "
    "%(text_ref)s, %(content_hash)s, %(author_id)s, %(status)s, "
    "%(retrieval_provenance)s, %(harvest_run_id)s) "
    "ON CONFLICT (source, external_id) DO NOTHING"
)


def _provenance(harvest_run_id: str | None) -> dict[str, object]:
    """The two columns the schema refuses to let disagree, decided once.

    `document_retrieval_provenance_agrees_ck` asserts
    `(retrieval_provenance = 'run_recorded') = (harvest_run_id IS NOT NULL)`,
    so a caller that set one and forgot the other would be refused by the
    database. Computing both here means no call site can reach that refusal.

    `not_recorded` is NOT produced here. It is the column DEFAULT and means
    "written before anybody recorded provenance" — a state about the past that
    a live writer must never claim.
    """
    if harvest_run_id is None:
        return {"retrieval_provenance": "no_run_for_source", "harvest_run_id": None}
    return {"retrieval_provenance": "run_recorded", "harvest_run_id": harvest_run_id}

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
    #: Documents that already existed and had no author until this run. Reported
    #: apart from `documents_inserted` because a re-run that attributes 89 old
    #: rows and inserts none is doing real work, and one "written" counter would
    #: show it as a no-op.
    authors_attached_to_existing: int = 0
    #: `thread_context` rows whose `member_document_ids` did not all resolve to
    #: a `document` row. THE CHECK THE LAST VERIFICATION COULD NOT MAKE, because
    #: it supplied both sides itself.
    members_unresolved: int = 0

    #: ── THE TEMPLATE-BLOCK RULE, AND WHETHER IT DID ANYTHING ──────────────
    #:
    #: Reported because a content rule that fires on some feeds and not others
    #: is invisible in a total. `template_block_rule` is the contract's status
    #: for THIS feed and `template_blocks_stripped` is how many of
    #: `articles_seen` actually shrank — so "stripped 0 of 12 because this feed
    #: is verified clean" and "stripped 0 of 12 because nobody has looked" are
    #: different lines in the summary rather than the same silence.
    template_block_rule: str = "unverified: no feed supplied"
    template_blocks_stripped: int = 0

    def summary(self) -> str:
        return (
            f"blog assemble: {self.articles_seen} article(s), "
            f"{self.documents_inserted} document(s), "
            f"{self.contexts_inserted} thread_context(s), "
            f"{self.already_present} already present, "
            f"{self.nothing_extracted} with nothing extracted, "
            f"{self.members_unresolved} with unresolved members, "
            f"{self.unreadable_after_write} unreadable after write; "
            f"template block: {self.template_blocks_stripped} stripped "
            f"({self.template_block_rule})"
        )


def write_blog_run(
    conn,
    run,
    *,
    store: RawStore,
    feed: Mapping[str, Any] | None = None,
    harvest_run_id: str | None = None,
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

    # ── the template-block rule, resolved ONCE from the contract ──────────
    #
    # Per feed, because it demonstrably cannot be general: two of the nine feeds
    # carry a boilerplate tail, three are examined and clean, four have never
    # had a page stored. `template_block_for` returns all three states, and the
    # inert ones are reported rather than behaving like an absent argument.
    rule = template_block_for(feed.get("id") if feed is not None else None)
    report.template_block_rule = rule.inert_reason or (
        f"stripping {list(rule.headings)} for {rule.source_id}"
    )

    for article_fetch in run.articles:
        if not article_fetch.stored:
            continue
        report.articles_seen += 1

        payload = store.get(article_fetch.artifact.ref)
        # Extracted once and stripped here rather than passing the rule down, so
        # the count is MEASURED against the same extraction instead of trusting
        # that the rule fired. A heading the contract names and this page does
        # not carry has to read as 0 stripped, not as 1.
        text = extract_article_text(payload, url=article_fetch.entry.url)
        if text and rule.strips:
            stripped = strip_template_block(text, rule.headings)
            if len(stripped) < len(text):
                report.template_blocks_stripped += 1
            text = stripped or None
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
        document = {
            **document_row(
                article,
                text_ref=article_fetch.artifact.ref,
                content_hash=article_fetch.artifact.content_hash,
                published_at=article_fetch.entry.published_at,
                author_id=author_id,
            ),
            # Both columns or neither - see `_provenance`.
            **_provenance(harvest_run_id),
        }
        cursor = conn.execute(_DOCUMENT_SQL, document)
        inserted = max(0, cursor.rowcount)
        report.documents_inserted += inserted
        if not inserted:
            report.already_present += 1
            # AND STILL GIVE IT ITS AUTHOR. `ON CONFLICT DO NOTHING` is right
            # for every other column and wrong for this one: an article stored
            # before `feed` was passed conflicts away and keeps `author_id`
            # NULL forever, however often the sweep re-runs, because a silent
            # conflict looks exactly like a successful write. Measured on the
            # nine-feed sweep: 89 documents landed with 0 authors.
            # Guarded by `author_id IS NULL`, so a real attribution is never
            # replaced. Same fix as `reddit_write` and `github.write_documents`.
            if author_id is not None:
                attached = conn.execute(
                    "UPDATE document SET author_id = %(author_id)s "
                    "WHERE source = %(source)s AND external_id = %(external_id)s "
                    "AND author_id IS NULL",
                    {"author_id": author_id, "source": document["source"],
                     "external_id": document["external_id"]},
                )
                report.authors_attached_to_existing += max(0, attached.rowcount)

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
