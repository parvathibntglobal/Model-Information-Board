"""`document` rows for the five platforms added 2026-09-07. One writer, not five.

WHY ONE WRITER WHEN THE CONVENTION IS ONE ADAPTER PER PLATFORM
--------------------------------------------------------------
The convention is about **fetching**: auth, rate limits, pagination and response
shape differ per platform and nothing shared can hold them. The `document` row
does not differ per platform, and the repository has already measured what
happens when each adapter writes its own INSERT.

`collect/triage/store.py`'s docstring names the incident. Four INSERTs, all
naming the same columns, and **the same six columns missing from all four**:

    collect/adapters/blog/write.py:89
    collect/adapters/github.py:814, :971
    collect/adapters/reddit_write.py:72

The specificity components had been computed, tested and contract-backed for
weeks and nothing stored them, because storing them meant editing four files
that nobody edits together. Five more copies would make that seven, so the five
new platforms share this one - and when a column is added here, it is added for
all five at once or for none.

THE THREE EXISTING WRITERS ARE NOT TOUCHED. Folding them in would be a refactor
of the only paths that have ever written a real corpus, for a benefit that
arrives on the next column rather than today. The duplication that remains is
3-plus-1 rather than 8, and it is visible from here.

WHAT THIS WRITER DOES NOT WRITE, DELIBERATELY
---------------------------------------------
`has_numbers`, `has_error_strings`, `has_code`, `has_conditions`,
`names_version` and `specificity_score` are **not written here**, and that is
`collect/triage/store.py`'s ruling rather than an omission:

    ONE REGISTRY READ, NOT FIVE. `score_document` needs the version-alias
    population, which belongs once per run. Five adapters each building it is
    five chances to diverge, and a `names_version` computed against a different
    surface set is not comparable to one that was not.

So a row written here carries NULL in all six until `score-documents` runs, the
same as every row the other three writers produce. **That is a real consequence
and it is reported rather than hidden**: `judge/`'s numbers rung is withheld and
`f_specificity` prices both as absent while they are NULL, and nothing in
`collect/` schedules the chain today. See `docs/triage-assessment-2026-09-07.md`.

`lang` IS WRITTEN AS OF 2026-09-08, AND THE SUITE IS WHY IT WAS NOT BEFORE
--------------------------------------------------------------------------
`document.lang` was NULL on all 6,502 stored rows, so `triage.gates
.wrong_language` reported UNAVAILABLE for the whole corpus. Two of these five
platforms declare a language per document - dev.to's `language` and X's `lang` -
and that is the platform's own field rather than an inference, so it looked like
a free win: capture it and the gate has an input.

**It was still a contract change, and the suite said so.** The INSERT below
used to omit the column, because `contract/column_states.yaml` declared
`document.lang: {state: reserved}` - *neither written nor read, deliberately,
awaiting a stage* - and adding the write moved the discovered state to
`write_only`, which
`tests/test_column_states.py::test_discovered_state_matches_declared` failed on
by name. That test did exactly its job: the state is DECLARED rather than
discovered, and a writer that changes what a column means is a contract change,
not an implementation detail. The column was UN-RESERVED on 2026-09-08 -
`write_only`, `reviewed: true`, with the `why` on the YAML entry - and the write
follows the declaration rather than preceding it.

WHAT THIS DOES NOT DO, AND THE DISTINCTION IS RULE 8'S. It does not make the
language gate runnable: no detector is installed, no allow-list is configured,
and `wrong_language` still reports UNAVAILABLE. The value is a RECORDED FIELD,
which is what rule 8 permits for a check whose error rate nobody has measured -
and this one has no error rate at all, because it is the platform's own
declaration rather than our guess about it.

WHY NOW RATHER THAN AFTER THE NEXT SWEEP. The write is free at collection time
and expensive afterwards: the input cannot be back-filled without re-reading
every stored payload. `WriteReport.lang_declared_by_platform` counts what lands
and is the figure that says how much it is worth - 2 of 2 dev.to documents in
the 2026-09-07 smoke run, which is a denominator of two and is quoted with it.

The 6,502 existing rows keep their NULLs. A platform that declares no language
still gets none (rule 6).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from collect.assemble.authors import AuthorRow, hash_handle, write_authors

log = logging.getLogger(__name__)

#: Every value `document.retrieval_provenance` may take, and what each claims.
#: `document_retrieval_provenance_ck` is the constraint; this is the list
#: mirrored so a wrong value raises at the call site rather than arriving as a
#: 23514 naming a constraint instead of a caller.
#:
#: The three are NOT interchangeable and the middle one is the trap:
#:
#:   run_recorded       a `harvest_run` row exists and its id is on this row.
#:   no_run_for_source  THIS RUN issued no per-query run, so a NULL id is
#:                      COMPLETE. Every one of these five platforms issues
#:                      queries, so this value is reachable here only for a
#:                      caller that fetched a known document by id without
#:                      searching for it.
#:   not_recorded       a run existed, or might have, and nobody wrote it down.
#:
#: `reddit_write.py` records what it cost to learn the difference: 853 rows
#: landed claiming `no_run_for_source` from a writer that had typed it into the
#: SQL, on rows produced by model-name queries. A positive claim that nothing
#: was missing, on rows where something was.
PROVENANCE_VALUES: tuple[str, ...] = (
    "run_recorded",
    "no_run_for_source",
    "not_recorded",
)

#: `document.status` values this writer will set. `rejected` and `tombstoned`
#: belong to paths that are not a harvest.
STATUS_VALUES: tuple[str, ...] = ("kept", "filtered")

#: `filter_reasons` for a document the platform kept and blanked: a dead or
#: flagged Hacker News comment, a Hugging Face comment event with no `raw`.
#:
#: ONE STRING, SHARED, for the reason `github.BOT_AUTHOR_REASON` is a named
#: constant: `/filtered` and the write paths must not disagree about the
#: spelling, and a grep has to find every producer. Two platforms reached the
#: same condition independently, which is exactly when two spellings appear.
#:
#: FOUND BY THE SMOKE RUN, NOT BY REVIEW. The Hugging Face adapter marked only
#: `hidden` comments and wrote an empty-text one as `kept`; it then refused at
#: `huggingface_prose`, which is the right refusal in the wrong place - a row
#: that looks like evidence and has no text.
NO_TEXT_REASON = "no_comment_text"

#: ⚠ `lang` IS IN THIS STATEMENT SINCE 2026-09-08, AND IT WAS DELIBERATELY OUT
#: OF IT BEFORE THAT. `column_states.yaml` declared the column `reserved` -
#: neither written nor read - so writing it moved the discovered state and
#: `tests/test_column_states.py::test_discovered_state_matches_declared` failed
#: by name. That was the guard working, not an obstacle: a writer that changes
#: what a column means is a contract change. The contract line was ruled on
#: 2026-09-08 (`document.lang` -> `write_only`, `reviewed: true`), so the write
#: is now declared before it is made rather than after.
#:
#: IT IS THE PLATFORM'S OWN FIELD AND NEVER AN INFERENCE - dev.to's `language`
#: and X's `lang`. NULL where the platform declares none, and NULL is not "en"
#: (rule 6): `triage.gates.wrong_language` returns NOT_APPLICABLE for a NULL
#: and would pass every document if this guessed.
_INSERT = (
    "INSERT INTO document (id, source, external_id, url, created_at, fetched_at, "
    "thread_root_id, parent_id, text_ref, content_hash, engagement, "
    "author_id, status, filter_reasons, harvest_run_id, retrieval_provenance, "
    "lang, is_self_post) "
    "VALUES (%(id)s, %(source)s, %(external_id)s, %(url)s, %(created_at)s, now(), "
    "%(thread_root_id)s, %(parent_id)s, %(text_ref)s, %(content_hash)s, "
    "%(engagement)s, %(author_id)s, %(status)s, %(filter_reasons)s, "
    "%(harvest_run_id)s, %(retrieval_provenance)s, %(lang)s, %(is_self_post)s) "
    "ON CONFLICT (source, external_id) DO NOTHING"
)

#: `ON CONFLICT DO NOTHING` is right for every other column and wrong for this
#: one. A document written before its author was resolvable conflicts away and
#: keeps `author_id` NULL permanently, however many times the sweep runs,
#: because the conflict is silent and the row looks written. Both existing
#: writers carry the same statement for the same reason - measured on Reddit's
#: first real run: 196 items, 190 inserted, and the 6 that conflicted stayed
#: anonymous while the other 190 got authors.
_SET_AUTHOR = (
    "UPDATE document SET author_id = %(author_id)s "
    "WHERE id = %(id)s AND author_id IS NULL"
)


class ProvenanceDisagreement(ValueError):
    """`retrieval_provenance` and `harvest_run_id` cannot both be right."""


def document_id(source: str, external_id: str) -> str:
    """`document.id` for these five platforms. THE convention, one place.

    `<source>:<external_id>`, which is `reddit_document_id` and
    `blog_document_id`'s form and NOT `github.py`'s `stable_id("doc", ...)`.
    Two conventions already exist in this repository; picking the readable one
    for the five new platforms means a disagreement is a diff against a named
    function rather than against an f-string, which is the argument both of
    those docstrings make.

    The external id is kept WHOLE and is always the publisher's own identity for
    the document - `hn:49593453`, `devto:4589859`, `arxiv:2609.03450v1`. Never
    derived from content: an edited article would otherwise become a second
    document and a second voice.
    """
    return f"{source}:{external_id}"


def _as_timestamp(value: Any) -> datetime | None:
    """A platform's own date, or None. NEVER the fetch time (rule 6).

    Accepts what these five platforms actually send: an ISO-8601 string
    (arXiv, dev.to, Hugging Face, X), an epoch integer (Hacker News's
    `created_at_i`), or a `datetime`. Anything else returns None and is counted
    by the caller - a document with no date sends its claim down the "no
    document facts" path rather than being dated from a default, which is what
    `weight.recency_factor` reading a fetch time would do.
    """
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, int | float):
        return datetime.fromtimestamp(float(value), tz=UTC)
    if isinstance(value, str) and value.strip():
        text = value.strip()
        # `2026-09-07T03:13:15Z` and `2026-09-06T22:49:59.000Z` both appear.
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


@dataclass(frozen=True)
class DocumentDraft:
    """One document, as the adapter that fetched it understands it.

    A draft rather than a row: `thread_root_external_id` and
    `parent_external_id` are the PLATFORM's ids, and this class turns them into
    `document.id`s. An adapter that built those ids itself would be a second
    implementation of `document_id`.

    Every optional field absent means ABSENT. There is no field here whose
    default asserts anything: no date is not "today", no author is not
    anonymous, no language is not English.
    """

    source: str
    external_id: str
    url: str
    #: The location of the bytes the platform gave us for THIS document, and
    #: their hash. Never prose, never a page covering many documents - see
    #: `docs/engineer-1/ruling-what-content-hash-identifies.md`.
    text_ref: str
    content_hash: str
    created_at: Any = None
    #: The platform's stable account id, and the handle, which is used to
    #: compute `handle_hash` and retained nowhere.
    author_external_id: str | None = None
    author_handle: str | None = None
    #: The platform's own language field, where it has one. Not detected.
    lang: str | None = None
    #: The platform's own link-post flag, where it has one. THREE STATES, and
    #: None is permanent rather than missing: only Hacker News among these five
    #: has a self/link distinction at all, and no comment on any platform has
    #: one. See `hackernews.is_self_post_of`.
    is_self_post: bool | None = None
    thread_root_external_id: str | None = None
    parent_external_id: str | None = None
    engagement: dict[str, Any] | None = None
    status: str = "kept"
    filter_reasons: tuple[str, ...] | None = None

    @property
    def id(self) -> str:
        return document_id(self.source, self.external_id)

    @property
    def author_row(self) -> AuthorRow | None:
        """The `author` row this document attributes to, or None.

        None means NO STABLE IDENTITY, and it stays None all the way to the
        column. Every fallback available here - the handle, a sentinel, the
        document id - either splits one person across renames or merges many
        people into one voice, and `judge/store/cells.py` maps a NULL author to
        one shared `ANONYMOUS_VOICE:platform` per platform, so a sentinel would
        be a voice that corroborates itself.
        """
        if not self.author_external_id:
            return None
        return AuthorRow(
            source=self.source,
            external_id=str(self.author_external_id),
            handle_hash=hash_handle(self.author_handle),
        )

    def as_row(
        self, *, retrieval_provenance: str, harvest_run_id: str | None
    ) -> dict[str, Any]:
        """The INSERT's parameters. `lang` IS ONE OF THEM SINCE 2026-09-08.

        `scripts/audit_columns.py` credits a dict key in a module that INSERTs
        as write evidence for that column, so this key and the column in
        `_INSERT` have to move together - a `"lang"` key without the column
        would declare a write the statement does not make, and
        `tests/test_column_states.py` would fail on the mismatch it correctly
        detected once already. Both moved with the contract line.
        """
        author = self.author_row
        return {
            "id": self.id,
            "source": self.source,
            "external_id": self.external_id,
            "url": self.url,
            "created_at": _as_timestamp(self.created_at),
            "thread_root_id": (
                document_id(self.source, self.thread_root_external_id)
                if self.thread_root_external_id
                else None
            ),
            "parent_id": (
                document_id(self.source, self.parent_external_id)
                if self.parent_external_id
                else None
            ),
            "text_ref": self.text_ref,
            "content_hash": self.content_hash,
            "engagement": (
                json.dumps(self.engagement) if self.engagement is not None else None
            ),
            "author_id": author.id if author else None,
            "status": self.status,
            "filter_reasons": list(self.filter_reasons) if self.filter_reasons else None,
            "harvest_run_id": harvest_run_id,
            "retrieval_provenance": retrieval_provenance,
            # NOT COERCED. The platform's declared value or None - no default,
            # no lowercasing, no "en". `X` says `qme` for "no language
            # detected" and that is the platform's answer, not ours to
            # translate.
            "lang": self.lang,
            # NULL FOR EVERY PLATFORM THAT HAS NO SUCH NOTION, which is four of
            # these five: arXiv, dev.to, Hugging Face and X have no self/link
            # distinction, and a comment does not have one anywhere. Hacker
            # News is the one that answers - `hackernews.is_self_post_of` - so
            # its drafts set this and the other four leave it None.
            "is_self_post": self.is_self_post,
        }


@dataclass
class WriteReport:
    """What one write did. Every count says what population it is over."""

    source: str = ""
    seen: int = 0
    inserted: int = 0
    #: Rows that already existed and had no author until now. Reported apart
    #: from `inserted` because a re-run that attributes 6 old rows and inserts 0
    #: is doing real work, and one "written" counter would show it as a no-op.
    authors_attached_to_existing: int = 0
    authors_inserted: int = 0
    distinct_authors: int = 0
    #: NAMED, NOT DROPPED. A document whose account has no stable id has no
    #: voice, and the count is the difference between "few voices" and "few
    #: ATTRIBUTABLE voices" - two different findings about the same corpus.
    without_author: int = 0
    without_created_at: int = 0
    #: Documents whose platform DECLARED a language, which this writer NOW
    #: stores (2026-09-08). Kept as a separate count rather than folded into
    #: `inserted`, because it is the one figure that separates "this platform
    #: declares no language" from "the write dropped it" - and those look
    #: identical in the column. Zero means the platform declares none.
    lang_declared_by_platform: int = 0
    filtered: int = 0

    def describe(self) -> str:
        return (
            f"{self.source}: {self.inserted} inserted of {self.seen} seen; "
            f"{self.distinct_authors} distinct authors, "
            f"{self.without_author} document(s) with no stable author id, "
            f"{self.without_created_at} with no platform date, "
            f"{self.lang_declared_by_platform} carrying a platform-declared "
            f"language, stored in document.lang, "
            f"{self.filtered} written as status='filtered'"
        )


def assert_provenance(retrieval_provenance: str, harvest_run_id: str | None) -> None:
    """The two columns cannot disagree, and the error names the caller.

    `document_retrieval_provenance_agrees_ck` enforces exactly this, and a
    violation there arrives as a 23514 naming a constraint - which tells whoever
    reads the traceback nothing about which argument was wrong. Mirrored here
    for the same reason `reddit_write.document_row` mirrors it.
    """
    if retrieval_provenance not in PROVENANCE_VALUES:
        raise ValueError(
            f"retrieval_provenance={retrieval_provenance!r} is not one of "
            f"{PROVENANCE_VALUES}. It is a claim about the RUN that produced this "
            "row - whether a run exists, and whether its id reached the writer - "
            "so it cannot be defaulted or guessed here."
        )
    if (retrieval_provenance == "run_recorded") != (harvest_run_id is not None):
        raise ProvenanceDisagreement(
            f"retrieval_provenance={retrieval_provenance!r} and "
            f"harvest_run_id={harvest_run_id!r} disagree. 'run_recorded' means the "
            "id is on the row and every other value means it is not - "
            "document_retrieval_provenance_agrees_ck refuses any other pairing, "
            "because a provenance claim with nothing behind it is worse than an "
            "absent one."
        )


def write_documents(
    conn,
    drafts: Sequence[DocumentDraft],
    *,
    retrieval_provenance: str,
    harvest_run_id: str | None = None,
    batch: int = 500,
) -> WriteReport:
    """Authors first, then documents. Append-only. Returns counts.

    **ORDER IS A FOREIGN KEY, NOT A PREFERENCE.** `document.author_id`
    references `author.id`, so author rows go first - the ordering
    `blog/write.py` and both other document writers record.

    BATCHED, for the reason `write_authors` measured: one statement per row cost
    ten minutes for 4,391 rows against the remote instance, roughly 130ms of
    latency each and almost no work.

    `ON CONFLICT (source, external_id) DO NOTHING`: two queries in one sweep
    legitimately return the same document, and the second is not an error.
    Shared-database writes in this project are append-only by rule
    (`CLAUDE.md`), and this statement is the only shape that satisfies it.
    """
    drafts = list(drafts)
    assert_provenance(retrieval_provenance, harvest_run_id)

    report = WriteReport(source=drafts[0].source if drafts else "", seen=len(drafts))
    if not drafts:
        return report

    sources = {d.source for d in drafts}
    if len(sources) > 1:
        # One call, one platform. A mixed batch would make every count in the
        # report a pooled figure over two populations, which is rule 7's exact
        # failure - and `report.source` could then only name one of them.
        raise ValueError(
            f"write_documents got drafts from {sorted(sources)}. One call writes "
            "one platform, so the returned counts have a single denominator."
        )

    author_rows = [d.author_row for d in drafts]
    unique_authors = {(r.source, r.external_id): r for r in author_rows if r}
    author_counts = write_authors(conn, list(unique_authors.values()), batch=batch)

    rows = [
        d.as_row(
            retrieval_provenance=retrieval_provenance, harvest_run_id=harvest_run_id
        )
        for d in drafts
    ]

    inserted = 0
    with conn.cursor() as cur:
        for start in range(0, len(rows), batch):
            cur.executemany(_INSERT, rows[start : start + batch])
            inserted += max(0, cur.rowcount)

    attributions = [
        {"id": r["id"], "author_id": r["author_id"]}
        for r in rows
        if r["author_id"] is not None
    ]
    attributed = 0
    if attributions:
        with conn.cursor() as cur:
            for start in range(0, len(attributions), batch):
                cur.executemany(_SET_AUTHOR, attributions[start : start + batch])
                attributed += max(0, cur.rowcount)

    report.inserted = inserted
    report.authors_attached_to_existing = max(0, attributed - inserted)
    report.authors_inserted = author_counts["inserted"]
    report.distinct_authors = len(unique_authors)
    report.without_author = sum(1 for r in rows if r["author_id"] is None)
    report.without_created_at = sum(1 for r in rows if r["created_at"] is None)
    report.lang_declared_by_platform = sum(1 for d in drafts if d.lang)
    report.filtered = sum(1 for r in rows if r["status"] != "kept")
    return report


def verify_text_refs(store, drafts: Iterable[DocumentDraft]) -> dict[str, Any]:
    """Does every draft's `text_ref` resolve, and to the bytes its hash names?

    THE INVARIANT, CHECKED WHERE THE ROW IS BUILT:

        content_hash(resolve(text_ref)) == content_hash

    `docs/engineer-1/ruling-what-content-hash-identifies.md` records that this
    invariant is **necessary and not sufficient**: it catches a mismatch between
    the two columns and cannot catch a wrong CHOICE of artifact, which is the
    failure that actually happened twice. So this also reports whether the
    resolved bytes PARSE as a container, which is the check that catches the
    wrong choice - and for these five platforms the answer must be YES, because
    the payload is a container by ruling and the prose is derived at assembly.

    Returns counts rather than raising: a sweep that stored 200 documents and
    cannot resolve one of them has a finding, not an exception.
    """
    from collect.ids import content_hash

    resolved = mismatched = missing = 0
    containers = 0
    failures: list[str] = []
    for draft in drafts:
        try:
            payload = store.get(draft.text_ref)
        except Exception as exc:  # noqa: BLE001 - every failure is the same finding
            missing += 1
            failures.append(f"{draft.external_id}: {type(exc).__name__}: {exc}")
            continue
        resolved += 1
        if content_hash(payload) != draft.content_hash:
            mismatched += 1
            failures.append(
                f"{draft.external_id}: stored bytes hash to "
                f"{content_hash(payload)[:12]}…, row says "
                f"{draft.content_hash[:12]}…"
            )
        text = payload.decode("utf-8", errors="replace").lstrip()
        if text.startswith(("{", "[", "<")):
            containers += 1
    return {
        "resolved": resolved,
        "missing": missing,
        "hash_mismatched": mismatched,
        "resolved_to_a_container": containers,
        "failures": failures,
    }


@dataclass
class SweepCounts:
    """The four figures a per-platform test run has to report, with denominators.

    Named as a type rather than a dict because the report they feed is the
    deliverable: `requests_issued` is the cost, `candidates` is what the
    platform returned, `stored` is what survived the sieve and reached the
    store, and `text_refs_resolved` is whether the row means anything.

    `candidates == 0` and `requests_issued == 0` are DIFFERENT findings and both
    are recorded: the first is the platform answering "nothing matches", the
    second is a refusal, a missing credential or a gate.
    """

    platform: str
    requests_issued: int = 0
    candidates: int = 0
    stored: int = 0
    text_refs_resolved: int = 0
    http_errors: int = 0
    notes: list[str] = field(default_factory=list)
