"""The shared raw store as a table: `raw_blob`, behind RawStore (PgBlobs).

Chosen 2026-10-07 instead of a bucket, because a bucket needs an external
storage account the team does not have and every machine already reaches the
shared database (migration 20261007T1200). These pin what the bucket tests pin
(tests/test_the_raw_store_is_shared.py), against a real disposable database:
  1. a put reaches the table, compressed, and reads back byte for byte;
  2. a machine without the payload fetches it from the table and caches it;
  3. a takedown reaches the table, and a remote tombstone beats a download;
  4. storing twice is a no-op - content addressing;
  5. RAW_STORE_REMOTE=postgres is chosen explicitly, and refuses when it
     cannot be honoured.
Requires a database. See docs/dev-database.md.
"""
from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from collect import rawstore_remote
from collect.rawstore import PayloadTombstoned, RawStore
from collect.rawstore_remote import PgBlobs

SCHEMA = Path(__file__).resolve().parents[1] / "contract" / "tables.sql"
PAYLOAD = b'{"title": "a thread", "body": "' + b"words " * 400 + b'"}'


@pytest.fixture
def blobs(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.execute(SCHEMA.read_text(encoding="utf-8"))
        c.commit()
    store = PgBlobs(test_dsn)
    yield store
    if store._conn is not None:
        store._conn.close()


def test_a_put_reaches_the_table_compressed_and_reads_back_exactly(tmp_path, blobs, test_dsn):
    stored = RawStore(tmp_path / "a", remote=blobs).put(PAYLOAD)
    assert blobs.get(stored.ref) == PAYLOAD
    assert blobs.size(stored.ref) == len(PAYLOAD)  # the UNCOMPRESSED length
    with psycopg.connect(test_dsn) as c:
        held = c.execute("SELECT octet_length(data) FROM raw_blob WHERE key = %s",
                         (stored.ref,)).fetchone()[0]
    assert held < len(PAYLOAD)


def test_another_machine_reads_it_and_caches_it(tmp_path, blobs):
    ref = RawStore(tmp_path / "laptop", remote=blobs).put(PAYLOAD).ref
    runner = RawStore(tmp_path / "runner", remote=blobs)  # an empty machine
    assert runner.get(ref) == PAYLOAD
    assert (tmp_path / "runner" / ref).exists()  # cached locally


def test_storing_twice_is_a_no_op(blobs):
    assert blobs.put_if_absent("raw/sha256/aa/bb/x", PAYLOAD) is True
    assert blobs.put_if_absent("raw/sha256/aa/bb/x", PAYLOAD) is False


def test_absent_is_none_not_an_error(blobs):
    assert blobs.get("raw/sha256/00/00/none") is None
    assert blobs.size("raw/sha256/00/00/none") is None
    assert blobs.exists("raw/sha256/00/00/none") is False


def test_a_takedown_reaches_the_table_and_cannot_be_downloaded_back(tmp_path, blobs):
    laptop = RawStore(tmp_path / "laptop", remote=blobs)
    ref = laptop.put(PAYLOAD).ref
    laptop.tombstone(ref, reason="takedown-request")
    assert blobs.exists(ref + ".tombstone")
    runner = RawStore(tmp_path / "runner", remote=blobs)
    with pytest.raises(PayloadTombstoned):
        runner.get(ref)


class TestChoosingTheStore:
    @pytest.fixture(autouse=True)
    def _clean(self, monkeypatch):
        monkeypatch.setenv("MODELBOARD_ALLOW_TEST_RAW_REMOTE", "1")
        for k in rawstore_remote.ENV_KEYS:
            monkeypatch.setenv(k, "")

    def test_postgres_uses_the_database_url(self, monkeypatch):
        monkeypatch.setenv(rawstore_remote.REMOTE_ENV, "postgres")
        monkeypatch.setenv("DATABASE_URL", "postgresql://u@shared-host/db")
        remote = rawstore_remote.remote_from_env()
        assert isinstance(remote, PgBlobs) and remote.dsn == "postgresql://u@shared-host/db"

    def test_postgres_without_a_database_refuses(self, monkeypatch):
        monkeypatch.setenv(rawstore_remote.REMOTE_ENV, "postgres")
        monkeypatch.setenv("DATABASE_URL", "")
        with pytest.raises(rawstore_remote.RemoteConfigError, match="DATABASE_URL"):
            rawstore_remote.remote_from_env()

    def test_two_named_stores_refuse(self, monkeypatch):
        monkeypatch.setenv(rawstore_remote.REMOTE_ENV, "postgres")
        monkeypatch.setenv("DATABASE_URL", "postgresql://u@h/db")
        monkeypatch.setenv("RAW_STORE_S3_BUCKET", "b")
        with pytest.raises(rawstore_remote.RemoteConfigError, match="name one store"):
            rawstore_remote.remote_from_env()

    def test_an_unknown_store_refuses(self, monkeypatch):
        monkeypatch.setenv(rawstore_remote.REMOTE_ENV, "dropbox")
        with pytest.raises(rawstore_remote.RemoteConfigError):
            rawstore_remote.remote_from_env()

    def test_a_test_never_reaches_the_real_database_store(self, monkeypatch):
        monkeypatch.delenv("MODELBOARD_ALLOW_TEST_RAW_REMOTE", raising=False)
        monkeypatch.setenv(rawstore_remote.REMOTE_ENV, "postgres")
        monkeypatch.setenv("DATABASE_URL", "postgresql://u@shared-host/db")
        assert rawstore_remote.remote_from_env() is None
