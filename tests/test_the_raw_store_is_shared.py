"""The raw store has a shared bucket behind it, so another machine can read it.

The first scheduled GitHub Action (2026-10-06) read 0 of 2,217 waiting documents:
every payload lived on a laptop. These tests pin what the shared layer must do,
against a fake bucket - no network, no credentials:

  1. a put reaches the bucket, and a failed upload is counted, never fatal;
  2. a read on a machine without the payload fetches it and caches it locally;
  3. a takedown reaches the bucket, and a remote tombstone beats a download;
  4. configuration is all-or-none, and a test never reaches the real bucket.
"""
from __future__ import annotations

import pytest

from collect import rawstore_remote
from collect.rawstore import PayloadMissing, PayloadTombstoned, RawStore


class FakeBucket:
    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.fail_uploads = False

    def exists(self, key):
        return key in self.objects

    def size(self, key):
        return len(self.objects[key]) if key in self.objects else None

    def get(self, key):
        return self.objects.get(key)

    def upload(self, key, data):
        if self.fail_uploads:
            raise ConnectionError("bucket unreachable")
        self.objects[key] = data

    def put_if_absent(self, key, data):
        if key in self.objects:
            return False
        self.upload(key, data)
        return True

    def delete(self, key):
        self.objects.pop(key, None)


@pytest.fixture
def bucket():
    return FakeBucket()


def test_a_put_reaches_the_bucket(tmp_path, bucket):
    store = RawStore(tmp_path / "a", remote=bucket)
    stored = store.put(b'{"title": "x"}')
    assert bucket.objects[stored.ref] == b'{"title": "x"}'


def test_another_machine_reads_it_and_caches_it(tmp_path, bucket):
    ref = RawStore(tmp_path / "laptop", remote=bucket).put(b"payload").ref
    runner = RawStore(tmp_path / "runner", remote=bucket)
    assert runner.get(ref) == b"payload"
    bucket.objects.clear()                       # now only the local cache has it
    assert runner.get(ref) == b"payload"
    assert runner.exists(ref)


def test_absent_everywhere_is_still_missing(tmp_path, bucket):
    store = RawStore(tmp_path / "s", remote=bucket)
    ref = RawStore(tmp_path / "other", remote=None).put(b"never shared").ref
    with pytest.raises(PayloadMissing):
        store.get(ref)
    assert not store.exists(ref)


def test_a_failed_upload_is_counted_not_fatal(tmp_path, bucket):
    bucket.fail_uploads = True
    store = RawStore(tmp_path / "s", remote=bucket)
    stored = store.put(b"kept locally")
    assert store.get(stored.ref) == b"kept locally"
    assert store.remote_failures == 1


def test_a_takedown_reaches_the_bucket_and_cannot_be_downloaded_back(tmp_path, bucket):
    ref = RawStore(tmp_path / "laptop", remote=bucket).put(b"to remove").ref
    RawStore(tmp_path / "laptop", remote=bucket).tombstone(ref, reason="takedown-request")
    assert ref not in bucket.objects
    assert ref + ".tombstone" in bucket.objects
    elsewhere = RawStore(tmp_path / "runner", remote=bucket)
    with pytest.raises(PayloadTombstoned):
        elsewhere.get(ref)
    assert not elsewhere.exists(ref)


def test_no_remote_is_the_old_behaviour(tmp_path):
    store = RawStore(tmp_path / "s", remote=None)
    stored = store.put(b"local only")
    assert store.get(stored.ref) == b"local only"


class TestConfiguration:
    def test_a_test_never_reaches_the_real_bucket(self, monkeypatch):
        for k in rawstore_remote.ENV_KEYS:
            monkeypatch.setenv(k, "set")
        monkeypatch.delenv("MODELBOARD_ALLOW_TEST_RAW_REMOTE", raising=False)
        assert rawstore_remote.remote_from_env() is None

    def test_half_configured_refuses(self, monkeypatch):
        monkeypatch.setenv("MODELBOARD_ALLOW_TEST_RAW_REMOTE", "1")
        for k in rawstore_remote.ENV_KEYS:
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("RAW_STORE_S3_BUCKET", "b")
        with pytest.raises(rawstore_remote.RemoteConfigError):
            rawstore_remote.remote_from_env()

    def test_none_configured_is_local_only(self, monkeypatch):
        monkeypatch.setenv("MODELBOARD_ALLOW_TEST_RAW_REMOTE", "1")
        for k in rawstore_remote.ENV_KEYS:
            monkeypatch.setenv(k, "")
        assert rawstore_remote.remote_from_env() is None


class TestTheS3Client:
    """`S3Blobs` over a fake boto client: a 404 is an absence, anything else raises."""

    @staticmethod
    def _client(objects):
        from botocore.exceptions import ClientError

        def missing(key):
            return ClientError({"Error": {"Code": "404"}}, "HeadObject")

        class Body:
            def __init__(self, data):
                self.data = data

            def read(self):
                return self.data

        class Client:
            def head_object(self, Bucket, Key):
                if Key not in objects:
                    raise missing(Key)
                return {"ContentLength": len(objects[Key])}

            def get_object(self, Bucket, Key):
                if Key not in objects:
                    raise missing(Key)
                return {"Body": Body(objects[Key])}

            def put_object(self, Bucket, Key, Body):
                objects[Key] = Body

            def delete_object(self, Bucket, Key):
                objects.pop(Key, None)
        return Client()

    def test_round_trip_and_absence(self):
        objects = {}
        s3 = rawstore_remote.S3Blobs(endpoint="e", bucket="b", key_id="k", secret="s",
                                     client=self._client(objects))
        assert s3.get("raw/x") is None and not s3.exists("raw/x")
        assert s3.put_if_absent("raw/x", b"1") is True
        assert s3.put_if_absent("raw/x", b"1") is False
        assert s3.get("raw/x") == b"1" and s3.size("raw/x") == 1
        s3.delete("raw/x")
        assert not s3.exists("raw/x")
