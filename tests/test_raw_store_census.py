"""#321: the census says where each payload is, per source, and writes nothing.

Against the disposable test database (a seeded `raw_blob`) and a tmp raw store:
every state the census distinguishes is seeded once, so each column is checked
against a known answer rather than against itself.
"""

from __future__ import annotations

import sys
import zlib
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Json

from collect.ids import content_hash
from collect.rawstore import FLATTENED, RawStore, build_ref
from tests.conftest import assert_disposable, assert_safe_target

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import raw_store_census as census_mod  # noqa: E402

SENTINEL = "flattened/inline-see-json"


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


def _shared(conn, key: str, data: bytes) -> None:
    conn.execute("INSERT INTO raw_blob (key, data, size) VALUES (%s, %s, %s)",
                 (key, zlib.compress(data), len(data)))


def _doc(conn, doc_id: str, source: str, ref: str) -> None:
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, text_ref, content_hash, status) "
        "VALUES (%s, %s, %s, %s, %s, %s, 'kept')",
        (doc_id, source, doc_id, f"https://example.test/{doc_id}", ref, "0" * 64),
    )


def _context(conn, tc_id: str, members: list[str], ref: str) -> None:
    conn.execute(
        "INSERT INTO thread_context (id, thread_root_id, member_document_ids, "
        "flattened_text_ref, offset_map, child_count, pipeline_version) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (tc_id, members[0], members, ref, Json([]), 0, "e3.test"),
    )


@pytest.fixture
def seeded(conn, tmp_path):
    """One of each state. Returns the store root."""
    root = tmp_path / "raw_store"
    store = RawStore(root, remote=None)

    disk_only = store.put(b"on disk only").ref
    both = store.put(b"on disk and shared").ref
    _shared(conn, both, b"on disk and shared")
    shared_only = build_ref(content_hash(b"shared only"))
    _shared(conn, shared_only, b"shared only")
    missing = build_ref(content_hash(b"nowhere"))
    tomb_local = store.put(b"taken down here").ref
    store.tombstone(tomb_local, reason="takedown-request")
    tomb_shared = build_ref(content_hash(b"taken down elsewhere"))
    _shared(conn, tomb_shared + ".tombstone", b"{}")

    _doc(conn, "r1", "reddit", disk_only)
    _doc(conn, "r2", "reddit", shared_only)
    _doc(conn, "r3", "reddit", both)
    _doc(conn, "g1", "github", missing)
    _doc(conn, "g2", "github", tomb_local)
    _doc(conn, "b1", "blog", tomb_shared)
    _doc(conn, "b2", "blog", SENTINEL)

    flat = store.put(b"flattened thread", namespace=FLATTENED).ref
    _context(conn, "tc1", ["r1", "r3"], flat)
    _context(conn, "tc2", ["no_such_doc"], build_ref(content_hash(b"gone"), FLATTENED))
    _context(conn, "tc3", ["b2"], SENTINEL)
    conn.commit()
    return root


def _snapshot(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


class TestEachStateIsCounted:
    def test_documents_by_source(self, conn, seeded):
        result = census_mod.census(conn, seeded)
        d = result["document"]
        assert dict(d["reddit"]) == {"rows": 3, "readable": 3, "on_disk": 2, "in_raw_blob": 2}
        assert d["github"]["missing"] == 1 and d["github"]["tombstoned"] == 1
        assert d["blog"]["tombstoned"] == 1, "a marker in raw_blob is a tombstone"
        assert d["blog"]["malformed"] == 1, "the #303 sentinel is malformed, not missing"
        assert result["document_rows"] == 7
        assert result["raw_blob_measured"] is True

    def test_every_line_sums_to_its_rows(self, conn, seeded):
        result = census_mod.census(conn, seeded)
        for table in ("document", "thread_context"):
            for source, c in result[table].items():
                assert sum(c[s] for s in census_mod.STATES) == c["rows"], (table, source)

    def test_thread_contexts_by_member_source(self, conn, seeded):
        t = census_mod.census(conn, seeded)["thread_context"]
        assert t["reddit"]["readable"] == 1
        # Members that resolve to no document are named, not dropped (rule 6).
        assert t[census_mod.UNRESOLVED]["missing"] == 1
        assert t["blog"]["malformed"] == 1


class TestItWritesNothing:
    def test_the_store_and_the_tables_are_unchanged(self, conn, seeded):
        before_disk = _snapshot(seeded)
        before_blobs = conn.execute("SELECT count(*) FROM raw_blob").fetchone()[0]
        census_mod.census(conn, seeded)
        # RawStore.get would have downloaded and cached the shared-only blob.
        assert _snapshot(seeded) == before_disk
        assert conn.execute("SELECT count(*) FROM raw_blob").fetchone()[0] == before_blobs

    def test_the_connection_refuses_a_write(self, conn, test_dsn):
        ro = census_mod.connect_read_only(test_dsn)
        try:
            with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
                ro.execute("CREATE TABLE census_must_not_write (x int)")
        finally:
            ro.close()


class TestAnAbsentTableIsNotMeasured:
    def test_no_raw_blob_table_is_not_zero(self, conn, seeded):
        conn.execute("DROP TABLE raw_blob")
        conn.commit()
        result = census_mod.census(conn, seeded)
        assert result["raw_blob_measured"] is False
        assert "NOT MEASURED" in census_mod.render(result)


class TestTheOutput:
    def test_it_is_dated_and_denominated(self, conn, seeded, test_dsn, capsys):
        assert census_mod.main(["--dsn", test_dsn, "--store", str(seeded)]) == 0
        out = capsys.readouterr().out
        assert out.startswith("raw-store census  20")
        assert "7 of 7 document rows carry a ref" in out
        assert "Nothing was written." in out
        assert "ALL" in out
