"""What `assemble_github_documents` selects, against a real Postgres.

WHY THIS EXISTS AND WHY IT DID NOT BEFORE. The query selected every github
document with no `thread_context`, and that was CORRECT for as long as
`document` held nothing but issue bodies - which was true until
`write_comments` landed 148 comment rows on 2026-08-31. Nothing about the
function changed; its premise expired.

So the property under test is not "the query is right today". It is that the
query still says what it means when the table holds a shape it did not hold when
the query was written. A behavioural test over issue bodies alone would have
passed on both sides of the defect, which is exactly the failure
`tests/conftest.py` records four times.

FAILS rather than skips with no database, like the other `_db` suites.
"""

from __future__ import annotations

import json
from pathlib import Path

import psycopg
import pytest

from collect.assemble.issue import assemble_github_documents
from collect.rawstore import RawStore

SCHEMA = Path(__file__).resolve().parent.parent / "contract" / "tables.sql"

ISSUE_PAYLOAD = {
    "url": "https://api.github.com/repos/o/r/issues/1",
    "html_url": "https://github.com/o/r/issues/1",
    "title": "claude sonnet 4.5 truncates at 12 tools",
    "body": "We hit this with 12 tools configured. p95 went to 420ms.",
    "user": {"id": 1, "login": "someone", "type": "User"},
}

COMMENT_PAYLOAD = {
    "url": "https://api.github.com/repos/o/r/issues/comments/9",
    "html_url": "https://github.com/o/r/issues/1#issuecomment-9",
    "body": "same here on 4.8, also 12 tools",
    "issue_url": "https://api.github.com/repos/o/r/issues/1",
    "user": {"id": 2, "login": "other", "type": "User"},
}

BOT_PAYLOAD = {
    "url": "https://api.github.com/repos/o/r/issues/comments/10",
    "html_url": "https://github.com/o/r/issues/1#issuecomment-10",
    "body": "This issue was automatically closed by a workflow run.",
    "issue_url": "https://api.github.com/repos/o/r/issues/1",
    "user": {"id": 3, "login": "github-actions[bot]", "type": "Bot"},
}


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.commit()
        yield connection


@pytest.fixture
def store(tmp_path):
    return RawStore(tmp_path / "raw")


def _insert(conn, store, doc_id, payload, *, parent_id=None, status="kept"):
    stored = store.put(json.dumps(payload))
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, text_ref, "
        "content_hash, parent_id, thread_root_id, status) "
        "VALUES (%s, 'github', %s, %s, %s, %s, %s, %s, %s)",
        (doc_id, doc_id, payload["html_url"], stored.ref, stored.content_hash,
         parent_id, parent_id, status),
    )
    conn.commit()
    return doc_id


class TestItAssemblesIssueBodies:
    def test_an_issue_body_with_no_context_is_assembled(self, conn, store):
        _insert(conn, store, "doc_issue", ISSUE_PAYLOAD)
        report = assemble_github_documents(conn, store=store)
        assert report.candidates == 1
        assert report.assembled == 1
        assert report.refusals == []

    def test_a_second_run_is_a_no_op(self, conn, store):
        _insert(conn, store, "doc_issue", ISSUE_PAYLOAD)
        assemble_github_documents(conn, store=store)
        conn.commit()
        again = assemble_github_documents(conn, store=store)
        assert again.candidates == 0, (
            "selection is by ABSENCE of a context, so an assembled document must "
            "not be a candidate again"
        )


class TestItRefusesToRootAComment:
    """THE DEFECT. A comment is a member of its issue's thread, never a root."""

    def test_a_comment_is_not_a_candidate(self, conn, store):
        _insert(conn, store, "doc_issue", ISSUE_PAYLOAD)
        _insert(conn, store, "doc_comment", COMMENT_PAYLOAD, parent_id="doc_issue")

        report = assemble_github_documents(conn, store=store)

        assert report.candidates == 1, (
            "the comment was selected as a root. It would become a "
            "single-comment thread_context, and where that comment is already a "
            "member of its issue's thread the same text reaches the extractor "
            "twice under two ids - one author counted as two voices."
        )
        assert report.assembled == 1

    def test_a_filtered_bot_comment_is_not_a_candidate(self, conn, store):
        """`assemble_issue_thread` refuses bots as MEMBERS. This is the other side.

        Excluding a bot from a thread and then assembling it as its own root
        would walk around that refusal rather than enforcing it, and
        `judge/store/cells.py` maps the NULL author to `ANONYMOUS_VOICE:github`
        - one shared voice a CI account could contribute to.
        """
        _insert(conn, store, "doc_issue", ISSUE_PAYLOAD)
        _insert(conn, store, "doc_bot", BOT_PAYLOAD,
                parent_id="doc_issue", status="filtered")

        report = assemble_github_documents(conn, store=store)

        assert report.candidates == 1
        roots = [
            row[0] for row in conn.execute(
                "SELECT thread_root_id FROM thread_context"
            ).fetchall()
        ]
        assert "doc_bot" not in roots

    def test_a_filtered_issue_body_is_not_a_candidate_either(self, conn, store):
        """⚠ THIS IS THE TEST THAT LOOKS REDUNDANT AND IS NOT.

        Every one of the 148 comments that prompted the fix is a non-root, and
        23 of them are also filtered - so on the real corpus either check alone
        caught the whole incident, and a reviewer reasonably reads the second as
        belt-and-braces.

        The overlap is a property of that corpus on that day. Each check has a
        case the other misses, and the two tests are built on exactly those:

            test_a_comment_is_not_a_candidate      a KEPT comment. The status
                                                   check passes it through.
            this test                              a filtered ISSUE BODY. The
                                                   parent check passes it through.

        A filtered root does not exist today because the only writer setting
        `status='filtered'` is the comment path, which only writes non-roots.
        `triage` will set it on roots the moment that stage is wired, and it is
        `run=None` right now - so the redundancy expires in the direction that
        matters, and the check that "does nothing" is the one that starts doing
        something first.

        Same reason `document.has_numbers` is a falsifier and not a confirmer:
        the value of a check is what it refuses, not what it happens to agree
        with today.
        """
        _insert(conn, store, "doc_filtered", ISSUE_PAYLOAD, status="filtered")
        report = assemble_github_documents(conn, store=store)
        assert report.candidates == 0, (
            "a filtered ROOT was selected. `parent_id IS NULL` cannot see this "
            "one - it IS a root - so removing the status check as redundant "
            "would leave the gate open to every document triage rejects."
        )
