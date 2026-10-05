"""`scripts/backfill_reddit_comments.py` against a real schema.

The property that matters is the swap: a body-only context on a never-extracted
root is replaced by one carrying replies, and a context that has been extracted
is left exactly as it was. `write_thread_context` is ON CONFLICT DO NOTHING and
the id does not hash members, so a backfill that skips the delete changes zero
rows while reporting success - the first test is the one that catches that.

Disposable Postgres only (`TEST_DATABASE_URL`); the harvester is a fake.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

import scripts.backfill_reddit_comments as backfill
from collect.adapters.reddit import ThreadFetch, _post_of
from collect.adapters.reddit_comments import _comment_of
from collect.adapters.reddit_write import write_documents
from collect.assemble.reddit import assemble_reddit_documents
from collect.rawstore import RAW, RawStore
from collect.rawstore_reader import RawStoreReader

SCHEMA = Path(__file__).resolve().parent.parent / "contract" / "tables.sql"
ROOT_ID = "reddit:t3_abc"
PERMALINK = "/r/LocalLLaMA/comments/abc/tool_calls/"

POST = {
    "name": "t3_abc",
    "id": "abc",
    "permalink": PERMALINK,
    "url": f"https://www.reddit.com{PERMALINK}",
    "title": "Tool calls failing",
    "selftext": "Anyone else seeing tool call failures with this model?",
    "author": "asker",
    "author_fullname": "t2_asker",
    "subreddit": "LocalLLaMA",
    "created_utc": 1759000000.0,
    "score": 40,
    "num_comments": 2,
}


def _comment(cid: str, body: str):
    return _comment_of(
        {"name": cid, "parent_id": "t3_abc", "link_id": "t3_abc", "body": body,
         "author": f"u_{cid}", "author_fullname": f"t2_{cid}",
         "subreddit": "LocalLLaMA", "created_utc": 1759000100.0, "score": 12,
         "depth": 0},
        url=f"https://www.reddit.com{PERMALINK}{cid}/", root_id="t3_abc",
    )


class Harvester:
    def __init__(self, comments=(), **kw) -> None:
        self.comments = tuple(comments)
        self.kw = kw
        self.asked = 0

    def fetch_comments(self, post):
        self.asked += 1
        assert post.raw["permalink"] == PERMALINK
        return ThreadFetch(thread_url="u", started_at=datetime.now(UTC),
                           comments=self.comments, **self.kw)


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


@pytest.fixture
def body_only(conn, store):
    """A post stored the way the listing sweep stored it: no comments under it."""
    post = _post_of(POST)
    blob = json.dumps(post.raw, ensure_ascii=False, sort_keys=True).encode("utf-8")
    stored = store.put(blob, namespace=RAW)
    write_documents(conn, [post], retrieval_provenance="not_recorded",
                    refs={post.external_id: (stored.ref, stored.content_hash)})
    conn.commit()
    assemble_reddit_documents(conn, store=store)
    conn.commit()
    row = conn.execute(
        "SELECT tc.id, tc.child_count, d.text_ref FROM thread_context tc "
        "JOIN document d ON d.id = tc.thread_root_id WHERE tc.thread_root_id = %s",
        (ROOT_ID,),
    ).fetchone()
    assert row is not None and row[1] == 0, "fixture should be body-only"
    return row[0], row[2]


def _context(conn):
    return conn.execute(
        "SELECT id, child_count, member_document_ids FROM thread_context "
        "WHERE thread_root_id = %s", (ROOT_ID,),
    ).fetchall()


def test_the_candidate_query_selects_a_body_only_never_extracted_root(conn, body_only):
    rows = conn.execute(backfill.CANDIDATES, ("reddit",)).fetchall()
    assert [r[1] for r in rows] == [ROOT_ID]


def test_a_body_only_context_is_replaced_by_one_with_replies(conn, store, body_only):
    tc_id, text_ref = body_only
    harvester = Harvester([_comment("t1_x", "Same here, tool calls drop the second argument."),
                           _comment("t1_y", "Fixed it by pinning the provider.")])

    rec = backfill.backfill_one(conn, harvester, store, RawStoreReader(store),
                                tc_id, ROOT_ID, text_ref)

    assert rec["outcome"] == "rebuilt with replies", rec
    rows = _context(conn)
    assert len(rows) == 1
    _id, child_count, members = rows[0]
    assert child_count == 2
    assert set(members) == {ROOT_ID, "reddit:t1_x", "reddit:t1_y"}
    # And it is no longer a candidate, so a re-run is a no-op.
    assert conn.execute(backfill.CANDIDATES, ("reddit",)).fetchall() == []


def test_an_extracted_context_is_left_exactly_as_it_was(conn, store, body_only):
    tc_id, text_ref = body_only
    conn.execute(
        "INSERT INTO thread_extraction (thread_context_id, pipeline_version, claims_written) "
        "VALUES (%s, 'test', 0)", (tc_id,),
    )
    conn.commit()
    before = _context(conn)

    rec = backfill.backfill_one(conn, Harvester([_comment("t1_x", "a reply")]), store,
                                RawStoreReader(store), tc_id, ROOT_ID, text_ref)

    assert rec["outcome"].startswith("left as it was"), rec
    assert _context(conn) == before


def test_no_comments_and_a_failed_fetch_touch_nothing(conn, store, body_only):
    tc_id, text_ref = body_only
    before = _context(conn)
    reader = RawStoreReader(store)

    empty = backfill.backfill_one(conn, Harvester(), store, reader, tc_id, ROOT_ID, text_ref)
    failed = backfill.backfill_one(conn, Harvester(http_errors=1), store, reader,
                                   tc_id, ROOT_ID, text_ref)

    assert empty["outcome"] == "platform returned no comments"
    assert failed["outcome"] == "FETCH FAILED"
    assert _context(conn) == before
