"""`collect/triage/run.py` against a real database. The join, and what it refuses.

WHY A DATABASE TEST AND NOT A FAKE CONNECTION. Every property here is a
property of the JOIN - a root that resolves, a root that does not, a root that
is its own document, a source outside the ruling's scope. A fake `conn`
returning hand-built tuples would test my tuple-building, which is the half
that cannot be wrong: the SELECT is the part that silently returns NULL.

**AND HACKER NEWS HAS NO STORED CORPUS TO PROVE IT ON.** Staging holds github
3,382, reddit 2,999, blog 121 and NOT ONE hackernews row - the 2026-09-07 smoke
run wrote to the disposable local instance, which has since been reset. So the
subject-gate join is exercised here, on rows this file inserts, or it is not
exercised at all. That is the whole reason this file exists rather than a
paragraph saying the join looks right.

    pwsh scripts/dev-postgres.ps1
    .venv\\Scripts\\python.exe -m pytest tests/test_triage_stored.py -q
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from collect.triage.run import SUBJECT_FROM_THREAD_ROOT, triage_stored
from tests.conftest import assert_disposable, assert_safe_target


@pytest.fixture
def conn(test_dsn):
    """A schema-fresh connection to a database proven safe to destroy.

    Same three-layer guard as `tests/test_source_load_db.py`: the target is
    checked, the OPEN CONNECTION is checked against it, and only then is the
    schema dropped. Not a courtesy - this file inserts and updates `document`,
    and `DATABASE_URL` is the shared staging database.
    """
    from collect.db import apply_schema, connect

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()

#: A story whose TITLE names a model. The shape the ruling exists for: the
#: subject is in this record and the evidence is in the children.
#:
#: ⚠ IT CARRIES A BODY, AND THE FIRST DRAFT DID NOT. With a title alone the
#:   story is eleven tokens and `too-short-no-artifact` drops the ROOT ROW -
#:   which is correct behaviour and made three tests here assert the wrong
#:   thing, because a dropped root still supplies a subject and the tests were
#:   really measuring the length gate. A body isolates the subject gate.
#:
#:   That is also a real state worth naming rather than only working around: an
#:   HN LINK submission has a title and no text, so its anchor row is genuinely
#:   short and genuinely dropped, while still being the subject its children
#:   inherit. The two facts are independent - `SUBJECT_FROM_THREAD_ROOT` reads
#:   the root's TEXT and never its verdict - and
#:   `test_a_dropped_root_still_supplies_its_subject` pins that.
STORY = {
    "objectID": "49587217",
    "title": "DeepClaude - Claude Opus 5 agent loop, and what it costs",
    "text": (
        "wrapper script that points an agent loop at a cheaper endpoint, with "
        "the pricing we measured over a fortnight and the two places it fell "
        "over on long tool chains"
    ),
}

#: The same story as a LINK submission: title, no body. Eleven tokens, so the
#: anchor row itself is dropped - and its children still inherit its subject.
STORY_LINK_ONLY = {
    "objectID": "49587217",
    "title": "DeepClaude - Claude Opus 5 agent loop, and what it costs",
    "text": "",
}

#: A comment that names nothing itself. Long enough to clear MIN_TOKENS, so the
#: only gate that can drop it is the subject gate - which is the gate under test.
CHILD_NAMES_NOTHING = {
    "objectID": "49591625",
    "text": (
        "we switched the router over last week and our monthly bill for the "
        "same traffic fell by roughly a third, which nobody on the team had "
        "expected going in"
    ),
}

#: A comment that names the model itself. Must NOT be counted as inherited.
CHILD_NAMES_MODEL = {
    "objectID": "49591626",
    "text": (
        "claude opus 5 dropped a tool call for us after about forty turns and "
        "the logs said nothing at all about why it had happened"
    ),
}


class _Store:
    """A raw store over a dict. `get_text` and `get` both, because blog wants bytes."""

    def __init__(self, payloads: dict[str, str]) -> None:
        self._payloads = payloads

    def get_text(self, ref: str) -> str:
        return self._payloads[ref]

    def get(self, ref: str) -> bytes:
        return self._payloads[ref].encode()


def _insert(conn, doc_id, source, *, ref, root=None, parent=None, external=None):
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, text_ref, "
        "content_hash, thread_root_id, parent_id, created_at, "
        "retrieval_provenance) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'not_recorded')",
        (
            doc_id,
            source,
            external or doc_id,
            f"https://news.ycombinator.com/item?id={external or doc_id}",
            ref,
            ref.rsplit("/", 1)[-1],
            root,
            parent,
            datetime.now(UTC),
        ),
    )


def _hn_thread(
    conn, *, root_stored: bool = True, root_id: str | None = None, story=None
):
    """One HN story and two comments. Returns the store the run should read.

    `root_stored=False` inserts the comments with a `thread_root_id` pointing at
    a row that does not exist - the Reddit-shaped state, which must be COUNTED
    rather than read as "this platform has no subject line".
    """
    payloads = {
        "raw/sha256/aa/aa/story": json.dumps(story or STORY),
        "raw/sha256/bb/bb/child1": json.dumps(CHILD_NAMES_NOTHING),
        "raw/sha256/cc/cc/child2": json.dumps(CHILD_NAMES_MODEL),
    }
    root = root_id or "hackernews:49587217"
    if root_stored:
        _insert(
            conn,
            "hackernews:49587217",
            "hackernews",
            ref="raw/sha256/aa/aa/story",
            root="hackernews:49587217",
            external="49587217",
        )
    _insert(
        conn,
        "hackernews:49591625",
        "hackernews",
        ref="raw/sha256/bb/bb/child1",
        root=root,
        parent="hackernews:49587217",
        external="49591625",
    )
    _insert(
        conn,
        "hackernews:49591626",
        "hackernews",
        ref="raw/sha256/cc/cc/child2",
        root=root,
        parent="hackernews:49587217",
        external="49591626",
    )
    conn.commit()
    return _Store(payloads)


def _run(conn, store, **kwargs):
    return triage_stored(conn, store, dry_run=True, sources=("hackernews",), **kwargs)


# ── the join supplies the subject, which is the whole point ──────────────


def test_a_comment_naming_nothing_is_kept_on_its_storys_subject(conn):
    """The 2.2% problem, end to end through the database.

    Without the join this comment is dropped by `no-resolvable-entity`, unread,
    and the drop is invisible - it looks like Hacker News having nothing to say.
    """
    store = _hn_thread(conn)
    run = _run(conn, store)

    assert run.triaged == 3
    assert run.subject_inherited == 1
    assert run.by_source["hackernews"]["subject_inherited"] == 1
    # The story itself and the model-naming comment resolved on their own text;
    # the third was kept on the story's title.
    assert run.kept == 3
    assert run.dropped == 0
    assert run.root_unresolvable == 0


def test_a_comment_naming_the_model_is_not_counted_as_inherited(conn):
    """`subject_was_inherited` must mean what it says on every kept row."""
    store = _hn_thread(conn)
    run = _run(conn, store)
    # Two of the three (the story, and the comment that names the model) reached
    # the gate on their own text. Exactly one inherited.
    assert run.subject_inherited == 1


def test_without_the_join_the_same_comment_is_dropped(conn):
    """THE CONTROL, and without it the test above proves nothing.

    Same rows, same store, and the ruling's scope narrowed to a platform these
    documents are not on. If the comment survives here too, the join is not what
    kept it.
    """
    store = _hn_thread(conn)
    run = _run(conn, store, subject_sources=frozenset())

    assert run.triaged == 3
    assert run.subject_inherited == 0
    assert run.dropped == 1
    assert run.by_reason["no-resolvable-entity"] == 1


# ── what the join refuses to guess ───────────────────────────────────────


def test_a_thread_root_that_resolves_to_nothing_is_counted_not_ignored(conn):
    """The Reddit-shaped state, and rule 6 at the join.

    All 1,420 stored Reddit children carry a `thread_root_id` that resolves to
    no row, because two writers use two conventions for one column
    (`t3_1v6a104` against `reddit:t3_1v6a104`). A join that read that as "this
    document has no subject line" would report an absence WE caused as one we
    found - on the platform where the count is largest.
    """
    store = _hn_thread(conn, root_stored=False, root_id="hackernews:does-not-exist")
    run = _run(conn, store)

    assert run.triaged == 2
    # Both comments wanted a root and neither got one. NAMED.
    assert run.root_unresolvable == 2
    assert run.by_source["hackernews"]["root_unresolvable"] == 2
    assert run.subject_inherited == 0
    # And the consequence is visible: the comment that named nothing is dropped,
    # so the count above is what says the drop is ours.
    assert run.dropped == 1
    assert "⚠ THREAD ROOT WANTED AND NOT AVAILABLE" in run.describe()


def test_a_root_is_not_handed_its_own_text_as_its_subject(conn):
    """A story anchor is its own root by convention (`hackernews.drafts`).

    Without `d.thread_root_id <> d.id` in the join, every root would inherit
    from itself, `subject_was_inherited` would be true on documents that named
    the model in their own text, and the flag would stop separating the two
    reading units it exists to separate.
    """
    store = _hn_thread(conn)
    run = _run(conn, store)
    # The story's own row: `thread_root_id = id`. It resolved on its own title,
    # so it must not appear as inherited.
    assert run.subject_inherited == 1  # the one comment, and not the story


def test_a_root_whose_payload_will_not_read_is_counted_separately(conn):
    """Unreadable root and unresolvable root are DIFFERENT findings.

    One is a raw store this host does not have; the other is a reference that
    points at nothing. Only the second is a defect in our own data, and folding
    them would hide which.
    """
    store = _hn_thread(conn)
    # The story's payload disappears; the comments' stay.
    del store._payloads["raw/sha256/aa/aa/story"]
    run = _run(conn, store)

    assert run.root_unreadable == 1  # read once, cached, counted once
    assert run.root_unresolvable == 0
    assert run.subject_inherited == 0
    # The story's own document is unreadable too, so it was never gated.
    assert run.unreadable == 1
    assert run.triaged == 2


def test_the_root_is_read_once_per_thread_and_not_once_per_child(conn):
    """The cost claim in the module docstring, asserted rather than asserted-in-prose.

    584 distinct roots behind GitHub's 2,016 children is a 1:3.45 ratio, and it
    only holds if the cache is real.
    """
    store = _hn_thread(conn)
    reads: list[str] = []
    original = store.get_text

    def counting(ref: str) -> str:
        reads.append(ref)
        return original(ref)

    store.get_text = counting  # type: ignore[method-assign]
    _run(conn, store)

    # Two children want the same root. The story's own row reads it once as its
    # own document; the root cache reads it once more, not twice.
    assert reads.count("raw/sha256/aa/aa/story") == 2


# ── scope ────────────────────────────────────────────────────────────────


def test_the_ruling_scope_is_hacker_news_alone(conn):
    """A test on the constant, so widening it is a visible decision.

    GitHub's 2,016 comments are in the same position - a comment's payload is
    its `body` and the issue title lives in the parent row - and the ruling was
    scoped to Hacker News. Adding a platform here changes what the pipeline
    keeps, so it should fail a test rather than pass silently.

    ⚠  GITHUB IS HELD DELIBERATELY, NOT PENDING. Measured 2026-09-08: widening
       moves GitHub from 42.9% to 74.0% and inherits on 1,388 documents. THE
       ARGUMENT FOR IT IS IDENTICAL IN FORM TO THE HACKER NEWS ONE, WHICH IS
       WHY IT MUST NOT CARRY AUTOMATICALLY - the HN ruling was made on 511
       comments in 2 threads, and this would apply to 3,382 documents. A change
       four times larger than its own evidence gets its own decision.

       Put up in `docs/proposals/for-the-team-github-thread-subject-widening.md`
       with three answers and a recommendation. **If you are here because this
       test failed, that document is what you are supposed to have read** - and
       if the answer was option 3 (widen only where the root resolves to exactly
       one model), the change is a predicate in `run.py` and NOT an entry here,
       so this test should still pass.
    """
    assert set(SUBJECT_FROM_THREAD_ROOT) == {"hackernews"}


def test_a_source_outside_the_scope_gets_no_subject_even_with_a_stored_root(conn):
    """The scope is enforced at the join, not just documented.

    These are the same rows under a different source label, and the root is
    stored and readable. Nothing may inherit.
    """
    payloads = {
        "raw/sha256/dd/dd/issue": json.dumps(
            {
                "title": "Claude Opus 5 agent loop costs",
                "body": (
                    "opening this to collect the pricing we measured over a "
                    "fortnight, plus the two places the loop fell over on long "
                    "tool chains"
                ),
            }
        ),
        "raw/sha256/ee/ee/comment": json.dumps(
            {
                "body": (
                    "we switched the router over last week and our monthly bill "
                    "for the same traffic fell by roughly a third, which nobody "
                    "on the team had expected going in"
                )
            }
        ),
    }
    _insert(conn, "gh-issue-1", "github", ref="raw/sha256/dd/dd/issue",
            root="gh-issue-1")
    _insert(conn, "gh-comment-1", "github", ref="raw/sha256/ee/ee/comment",
            root="gh-issue-1", parent="gh-issue-1")
    conn.commit()

    run = triage_stored(
        conn, _Store(payloads), dry_run=True, sources=("github",)
    )
    assert run.triaged == 2
    assert run.subject_inherited == 0
    assert run.dropped == 1
    assert run.by_reason["no-resolvable-entity"] == 1


# ── what it writes, and what it refuses to write ─────────────────────────


def test_a_dry_run_writes_nothing(conn):
    store = _hn_thread(conn)
    run = _run(conn, store)
    assert run.written == 0
    remaining = conn.execute(
        "SELECT count(*) FROM document WHERE source='hackernews' "
        "AND triage_verdict IS NOT NULL"
    ).fetchone()[0]
    assert remaining == 0


def test_a_write_sets_the_verdict_and_reasons_and_never_status(conn):
    """Rule 8, asserted on the column.

    Two of six gates cannot run, so this is a recorded field. `status` is what
    `judge/` filters on (`status = 'kept'`, with an index for that predicate),
    and writing it here would drop rows out of `judge/`'s view on four gates of
    six - a false positive nobody could see.
    """
    store = _hn_thread(conn)
    run = triage_stored(
        conn, store, dry_run=False, sources=("hackernews",)
    )
    assert run.written == 3

    rows = conn.execute(
        "SELECT id, triage_verdict, filter_reasons, status FROM document "
        "WHERE source='hackernews' ORDER BY id"
    ).fetchall()
    assert [r[1] for r in rows] == ["kept", "kept", "kept"]
    # NULL, not `{}` - an empty array asserts "gated and nothing fired".
    assert all(r[2] is None for r in rows)
    # THE ASSERTION THAT MATTERS: every row keeps the schema default.
    assert {r[3] for r in rows} == {"kept"}


def test_a_second_run_is_a_no_op(conn):
    """Idempotent by construction: the WHERE and the UPDATE both re-check NULL."""
    store = _hn_thread(conn)
    first = triage_stored(conn, store, dry_run=False, sources=("hackernews",))
    assert first.written == 3

    second = triage_stored(conn, store, dry_run=False, sources=("hackernews",))
    assert second.eligible == 0
    assert second.triaged == 0
    assert second.written == 0
    assert "NOTHING WAS GATED" in second.describe()


def test_a_dropped_row_records_which_gates_fired(conn):
    store = _hn_thread(conn, root_stored=False, root_id="hackernews:missing")
    triage_stored(conn, store, dry_run=False, sources=("hackernews",))
    reasons = conn.execute(
        "SELECT filter_reasons FROM document "
        "WHERE id = 'hackernews:49591625'"
    ).fetchone()[0]
    assert reasons == ["no-resolvable-entity"]


# ── denominators ─────────────────────────────────────────────────────────


def test_survival_is_over_triaged_and_never_over_eligible(conn):
    """Rule 7. An ungated document in the denominator reports OUR COVERAGE as
    the corpus's quality - and on the first real run that gap was 1,492 of
    6,502 rows, so it is not a rounding difference.
    """
    store = _hn_thread(conn)
    del store._payloads["raw/sha256/bb/bb/child1"]
    run = _run(conn, store)

    assert run.eligible == 3
    assert run.triaged == 2
    assert run.unreadable == 1
    assert run.survival == run.kept / run.triaged
    assert "OUTSIDE the denominator" in run.describe()


def test_a_dropped_root_still_supplies_its_subject(conn):
    """A LINK submission's anchor is eleven tokens and is dropped. Its children
    still inherit its title.

    FOUND BY A FIXTURE, NOT BY REVIEW. The first draft of `STORY` had a title
    and no body, so the anchor row was dropped by `too-short-no-artifact` - and
    three tests here quietly asserted the length gate's behaviour while claiming
    to test the subject gate.

    The two facts are independent and must stay that way: the join reads the
    root's TEXT and never its VERDICT. Reading the verdict would be a much worse
    rule than it looks - on Hacker News the highest-signal thread in the
    measured corpus was a bare GitHub link at 678 points, whose anchor carries a
    title and nothing else, and whose evidence was entirely in the comments. A
    subject gate that refused to inherit from a dropped root would discard
    exactly that thread.
    """
    store = _hn_thread(conn, story=STORY_LINK_ONLY)
    run = _run(conn, store)

    assert run.triaged == 3
    # The anchor is dropped on length...
    assert run.dropped == 1
    assert run.by_reason["too-short-no-artifact"] == 1
    # ...and its subject still reached the child that named nothing.
    assert run.subject_inherited == 1
    assert run.kept == 2
