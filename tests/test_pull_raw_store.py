"""scripts/pull_raw_store.py: brings missing raw payloads back from the shared
`raw_blob` table - and refuses what does not match its name, never overwrites,
and honours a takedown. Run against a throwaway schema; no network."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import zlib

import psycopg
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contract" / "tables.sql"
spec = importlib.util.spec_from_file_location(
    "pull_raw_store", ROOT / "scripts" / "pull_raw_store.py"
)
pull_raw_store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pull_raw_store)


def key_for(data: bytes, ns: str = "raw") -> str:
    h = hashlib.sha256(data).hexdigest()
    return f"{ns}/sha256/{h[:2]}/{h[2:4]}/{h}"


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.execute(SCHEMA.read_text(encoding="utf-8"))
        c.commit()
        yield c


def _blob(c, key: str, data: bytes):
    c.execute(
        "INSERT INTO raw_blob (key, data, size) VALUES (%s, %s, %s)",
        (key, zlib.compress(data), len(data)),
    )


def test_it_pulls_what_matches_and_refuses_what_does_not(conn, tmp_path):
    good, bad, gone, kept = b"good payload", b"tampered", b"taken down", b"already here"
    k_good, k_gone, k_kept = key_for(good), key_for(gone), key_for(kept, "flattened")
    k_bad = key_for(b"what the name says")
    _blob(conn, k_good, good)
    _blob(conn, k_bad, bad)  # bytes do not hash to the name
    _blob(conn, k_gone, gone)
    _blob(conn, k_gone + ".tombstone", b"")
    (tmp_path / k_kept).parent.mkdir(parents=True)
    (tmp_path / k_kept).write_bytes(b"local copy wins")

    refs = [k_good, k_bad, k_gone, k_kept, key_for(b"nowhere")]
    dry = pull_raw_store.pull(conn, tmp_path, refs, apply=False)
    assert dry["written"] == 0 and not (tmp_path / k_good).exists()

    out = pull_raw_store.pull(conn, tmp_path, refs, apply=True)
    assert (out["written"], out["refused_hash"], out["taken_down"]) == (1, 1, 1)
    assert (tmp_path / k_good).read_bytes() == good
    assert not (tmp_path / k_bad).exists()
    assert not (tmp_path / k_gone).exists()
    assert (tmp_path / k_kept).read_bytes() == b"local copy wins"  # never overwritten


def test_missing_refs_skips_what_is_here_or_taken_down_here(conn, tmp_path):
    here, down, absent = key_for(b"a"), key_for(b"b"), key_for(b"c")
    for k in (here, down + ".tombstone"):
        (tmp_path / k).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / k).write_bytes(b"x")
    for i, ref in enumerate((here, down, absent)):
        conn.execute(
            "INSERT INTO document (id, source, external_id, url, text_ref, content_hash) "
            "VALUES (%s, 'devto', %s, 'https://example.test', %s, %s)",
            (f"d{i}", f"d{i}", ref, f"h{i}"),
        )
    assert pull_raw_store.missing_refs(conn, tmp_path) == [absent]
