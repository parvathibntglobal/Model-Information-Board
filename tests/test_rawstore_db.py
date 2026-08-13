"""The raw store against the real `document` table.

`document.text_ref` and `content_hash` are both NOT NULL, so this is the pair
of columns the store exists to fill. NFR-6's acceptance is a statement about
this combination, not about either alone: tombstone a document and *only the
content hash remains*.

Requires a database. See docs/dev-database.md.
"""

from __future__ import annotations

import pytest

from collect.rawstore import (
    FLATTENED,
    PayloadMissing,
    PayloadTombstoned,
    RawStore,
    parse_ref,
)
from tests.conftest import assert_disposable, assert_safe_target

ISSUE = (
    b'{"number": 8842, "title": "tool_choice ignored past 6 tools", '
    b'"body": "repro: register 7 tools, the 7th call 400s"}'
)


@pytest.fixture
def conn(test_dsn):
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


@pytest.fixture
def store(tmp_path):
    return RawStore(tmp_path / "raw_store")


def _insert_document(connection, stored, *, doc_id="gh_8842") -> str:
    # external_id derives from doc_id: `document` is UNIQUE (source, external_id),
    # so a fixed literal collides the moment a test inserts two rows.
    connection.execute(
        "INSERT INTO document (id, source, external_id, url, text_ref, content_hash, status) "
        "VALUES (%s, 'github', %s, %s, %s, %s, 'kept')",
        (
            doc_id,
            doc_id,
            f"https://github.com/x/y/issues/{doc_id}",
            stored.ref,
            stored.content_hash,
        ),
    )
    connection.commit()
    return doc_id


def _column(connection, doc_id, column):
    row = connection.execute(
        f"SELECT {column} FROM document WHERE id = %s",  # noqa: S608 - fixed set
        (doc_id,),
    ).fetchone()
    return row[0] if row else None


# ── the round trip ────────────────────────────────────────────────────────


def test_a_stored_payload_fills_both_not_null_columns(conn, store):
    stored = store.put(ISSUE)
    doc_id = _insert_document(conn, stored)

    assert _column(conn, doc_id, "text_ref") == stored.ref
    assert _column(conn, doc_id, "content_hash") == stored.content_hash


def test_the_document_row_can_fetch_its_own_text_back(conn, store):
    """The whole point: judge/ reads text_ref to get the bytes to verify against."""
    stored = store.put(ISSUE)
    doc_id = _insert_document(conn, stored)

    assert store.get(_column(conn, doc_id, "text_ref")) == ISSUE


def test_the_stored_hash_matches_the_column(conn, store):
    stored = store.put(ISSUE)
    doc_id = _insert_document(conn, stored)

    _, hash_from_ref = parse_ref(_column(conn, doc_id, "text_ref"))
    assert hash_from_ref == _column(conn, doc_id, "content_hash")


def test_two_documents_of_identical_bytes_share_one_payload(conn, store):
    """Content addressing: a syndicated copy costs one blob, not two.

    Dedup is E3's job and counts people rather than posts, but the store
    should not multiply the bytes in the meantime.
    """
    first = store.put(ISSUE)
    second = store.put(ISSUE)
    assert first.ref == second.ref

    _insert_document(conn, first, doc_id="gh_8842")
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, text_ref, content_hash, status) "
        "VALUES ('rd_abc', 'reddit', 'abc', 'https://reddit.com/x', %s, %s, 'kept')",
        (second.ref, second.content_hash),
    )
    conn.commit()

    assert len(list((store.root / "raw").rglob("*"))) == 4  # sha256/aa/bb/<blob>


# ── NFR-6 across the boundary ─────────────────────────────────────────────


def test_tombstoning_leaves_the_row_with_only_its_hash(conn, store):
    """NFR-6, executed against the table it is a statement about."""
    stored = store.put(ISSUE)
    doc_id = _insert_document(conn, stored)

    store.tombstone(stored.ref, reason="takedown-request", detail="ticket 4471")
    conn.execute("UPDATE document SET status = 'tombstoned' WHERE id = %s", (doc_id,))
    conn.commit()

    assert _column(conn, doc_id, "status") == "tombstoned"
    assert _column(conn, doc_id, "content_hash") == stored.content_hash

    with pytest.raises(PayloadTombstoned):
        store.get(_column(conn, doc_id, "text_ref"))


def test_the_row_is_not_deleted_and_text_ref_is_not_rewritten(conn, store):
    """Immutability means not silently rewriting history, not refusing a
    deletion. Only `status` changes."""
    stored = store.put(ISSUE)
    doc_id = _insert_document(conn, stored)
    store.tombstone(stored.ref, reason="upstream-deleted")
    conn.execute("UPDATE document SET status = 'tombstoned' WHERE id = %s", (doc_id,))
    conn.commit()

    assert _column(conn, doc_id, "text_ref") == stored.ref
    assert conn.execute("SELECT count(*) FROM document").fetchone()[0] == 1


def test_a_tombstone_is_distinguishable_from_data_loss(conn, store):
    """Two rows, two absences, two different exceptions."""
    tombstoned = store.put(ISSUE)
    lost = store.put(b"a different payload entirely")
    _insert_document(conn, tombstoned, doc_id="gh_tombstoned")
    _insert_document(conn, lost, doc_id="gh_lost")

    store.tombstone(tombstoned.ref, reason="takedown-request")
    (store.root / lost.ref).unlink()  # corruption, not a takedown

    with pytest.raises(PayloadTombstoned):
        store.get(_column(conn, "gh_tombstoned", "text_ref"))
    with pytest.raises(PayloadMissing):
        store.get(_column(conn, "gh_lost", "text_ref"))


# ── thread_context uses the same store, different namespace ───────────────


def test_flattened_text_fills_thread_context_from_the_same_store(conn, store):
    """One store, two prefixes. `judge/` reads both through one interface."""
    doc = store.put(ISSUE)
    doc_id = _insert_document(conn, doc)

    flattened = store.put(
        "ROOT: tool_choice ignored past 6 tools\nREPLY: you had tool_choice misconfigured",
        namespace=FLATTENED,
    )
    conn.execute(
        "INSERT INTO thread_context (id, thread_root_id, member_document_ids, "
        "flattened_text_ref, offset_map, child_count, pipeline_version) "
        "VALUES ('tc_1', %s, %s, %s, %s, 1, 'collect-0.1.0')",
        (doc_id, [doc_id], flattened.ref, "[]"),
    )
    conn.commit()

    ref = conn.execute("SELECT flattened_text_ref FROM thread_context").fetchone()[0]
    assert ref.startswith("flattened/")
    assert "REPLY" in store.get_text(ref)


def test_the_two_namespaces_do_not_collide_on_identical_bytes(conn, store):
    """A one-comment thread flattens to bytes identical to its own payload."""
    same = b"a single comment with no replies"
    raw = store.put(same)
    flat = store.put(same, namespace=FLATTENED)

    assert raw.content_hash == flat.content_hash
    assert raw.ref != flat.ref
    store.evict(flat.ref)
    assert store.exists(raw.ref)  # evicting the cache must not touch raw/
