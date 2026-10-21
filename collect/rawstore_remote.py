"""The shared half of the raw store, behind the local one: a table or a bucket.

WHY IT EXISTS (2026-10-06). The raw store was a folder on whichever machine ran
a fetch. Rows reached the shared database; the bytes they point at did not. The
first scheduled GitHub Action proved what that costs: a fresh runner read 0 of
2,217 waiting documents and 0 of 6,087 unread threads, because every payload was
on a laptop. The stack decision was always "Postgres plus an object store"; this
is the object store.

HOW IT SITS UNDER `RawStore` - the local folder stays, as a cache:

    put     local write as before, then the bucket if the key is not there yet
    get     local if present; else the bucket, and the bytes are cached locally
    marker  a tombstone is written to the bucket as `<ref>.tombstone` and the
            object deleted, so a takedown on one machine cannot be undone by
            another machine's download

Keys are refs verbatim (`raw/sha256/ab/cd/<hash>`), so a bucket listing reads
like the folder it mirrors, and content addressing makes every upload
idempotent.

WHICH SHARED STORE - `RAW_STORE_REMOTE`, said explicitly (rule 12):

    postgres   the `raw_blob` table in the database DATABASE_URL names (PgBlobs).
               No new service: every machine and the scheduled runner already
               reach that database. Chosen 2026-10-07 - the team has no
               external storage account (migration 20261007T1200).
    s3         an S3-compatible bucket (S3Blobs), from four variables, all
               required: RAW_STORE_S3_ENDPOINT, _BUCKET, _ACCESS_KEY_ID,
               _SECRET_ACCESS_KEY.
    unset      local only - unless all four S3 variables are set, which is how
               the bucket was configured before this variable existed.

A half-configured bucket refuses, and so does `postgres` with no DATABASE_URL
or `postgres` beside S3 variables: a store that writes locally while looking
shared, or that picks one of two named stores, is the defect, not a fallback.
"""
from __future__ import annotations

import os

ENV_KEYS = (
    "RAW_STORE_S3_ENDPOINT",
    "RAW_STORE_S3_BUCKET",
    "RAW_STORE_S3_ACCESS_KEY_ID",
    "RAW_STORE_S3_SECRET_ACCESS_KEY",
)


REMOTE_ENV = "RAW_STORE_REMOTE"
REMOTES = ("postgres", "s3")


class RemoteConfigError(RuntimeError):
    """The shared raw store is half-configured or named ambiguously."""


class PgBlobs:
    """The `raw_blob` table as a blob store. Same methods and keys as S3Blobs.

    Payloads are stored zlib-compressed (4.2x on this corpus, measured
    2026-10-07); `size` is the uncompressed length, which is what callers mean.
    One connection, opened on first use and reused - a fetch reads thousands of
    payloads - in autocommit, so each write stands alone and a failed one cannot
    poison the next. A lock makes it safe across the fetch's threads.
    """

    def __init__(self, dsn: str, *, connect=None) -> None:
        import threading

        self.dsn = dsn
        self._connect = connect
        self._conn = None
        self._lock = threading.Lock()

    def _run(self, sql: str, params: tuple):
        import psycopg

        with self._lock:
            for attempt in (1, 2):
                if self._conn is None or self._conn.closed:
                    connect = self._connect or (lambda d: psycopg.connect(d, connect_timeout=15))
                    self._conn = connect(self.dsn)
                    self._conn.autocommit = True
                try:
                    cur = self._conn.execute(sql, params)
                    return cur.fetchone() if cur.description else None
                except psycopg.OperationalError:
                    # A dropped connection: one reconnect, then the error stands.
                    self._conn = None
                    if attempt == 2:
                        raise

    def exists(self, key: str) -> bool:
        return self._run("SELECT 1 FROM raw_blob WHERE key = %s", (key,)) is not None

    def size(self, key: str) -> int | None:
        row = self._run("SELECT size FROM raw_blob WHERE key = %s", (key,))
        return int(row[0]) if row else None

    def get(self, key: str) -> bytes | None:
        """The bytes, or None when the key is not stored. Other errors raise."""
        import zlib

        row = self._run("SELECT data FROM raw_blob WHERE key = %s", (key,))
        return zlib.decompress(bytes(row[0])) if row else None

    def upload(self, key: str, data: bytes) -> None:
        self.put_if_absent(key, data)

    def put_if_absent(self, key: str, data: bytes) -> bool:
        """Store unless present. True when it stored. Content-addressed keys make
        "present" mean "identical", so the conflict is the compare."""
        import zlib

        row = self._run(
            "INSERT INTO raw_blob (key, data, size) VALUES (%s, %s, %s) "
            "ON CONFLICT (key) DO NOTHING RETURNING key",
            (key, zlib.compress(data, 6), len(data)),
        )
        return row is not None

    def delete(self, key: str) -> None:
        self._run("DELETE FROM raw_blob WHERE key = %s", (key,))


class S3Blobs:
    """A thin client over one bucket. Every method takes a ref as the key."""

    def __init__(self, *, endpoint: str, bucket: str, key_id: str, secret: str,
                 client=None) -> None:
        self.bucket = bucket
        self.endpoint = endpoint
        if client is None:
            import boto3
            from botocore.config import Config

            client = boto3.client(
                "s3", endpoint_url=endpoint, aws_access_key_id=key_id,
                aws_secret_access_key=secret, region_name="auto",
                config=Config(retries={"max_attempts": 5, "mode": "standard"},
                              connect_timeout=10, read_timeout=60),
            )
        self._s3 = client

    @staticmethod
    def _absent(error) -> bool:
        code = str(getattr(error, "response", {}).get("Error", {}).get("Code", ""))
        return code in ("404", "NoSuchKey", "NotFound")

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as error:
            if self._absent(error):
                return False
            raise

    def size(self, key: str) -> int | None:
        from botocore.exceptions import ClientError

        try:
            return int(self._s3.head_object(Bucket=self.bucket, Key=key)["ContentLength"])
        except ClientError as error:
            if self._absent(error):
                return None
            raise

    def get(self, key: str) -> bytes | None:
        """The bytes, or None when the object does not exist. Other errors raise."""
        from botocore.exceptions import ClientError

        try:
            return self._s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except ClientError as error:
            if self._absent(error):
                return None
            raise

    def upload(self, key: str, data: bytes) -> None:
        self._s3.put_object(Bucket=self.bucket, Key=key, Body=data)

    def put_if_absent(self, key: str, data: bytes) -> bool:
        """Upload unless present. True when it uploaded. Content-addressed keys
        make "present" mean "identical", so a HEAD replaces a compare."""
        if self.exists(key):
            return False
        self.upload(key, data)
        return True

    def delete(self, key: str) -> None:
        self._s3.delete_object(Bucket=self.bucket, Key=key)


def remote_from_env() -> S3Blobs | PgBlobs | None:
    """The configured shared store, None when none is. Ambiguity or partial
    config raises (see the module docstring)."""
    import sys

    from collect.config import settings

    # ⚠ NEVER THE SHARED BUCKET FROM A TEST, the guard every telemetry mirror
    #   carries (collect/usage.py). Once a developer's .env names the bucket,
    #   every RawStore a test builds would upload its fixtures to it. A test
    #   that means to exercise the bucket passes its own `remote=`.
    if (os.getenv("PYTEST_CURRENT_TEST") or "_pytest" in sys.modules) and not os.getenv(
            "MODELBOARD_ALLOW_TEST_RAW_REMOTE"):
        return None

    settings()  # loads .env into the environment, as every other setting does
    values = {k: (os.getenv(k) or "").strip() for k in ENV_KEYS}
    present = [k for k, v in values.items() if v]
    chosen = (os.getenv(REMOTE_ENV) or "").strip().lower()
    if chosen and chosen not in REMOTES:
        raise RemoteConfigError(f"{REMOTE_ENV}={chosen!r} is not one of {REMOTES}")
    if chosen == "postgres":
        if present:
            raise RemoteConfigError(
                f"{REMOTE_ENV}=postgres and RAW_STORE_S3_* are both set; name one store, "
                "not two")
        dsn = (os.getenv("DATABASE_URL") or "").strip()
        if not dsn:
            raise RemoteConfigError(
                f"{REMOTE_ENV}=postgres but DATABASE_URL is not set; refusing rather "
                "than writing locally while looking shared")
        return PgBlobs(dsn)
    if not present:
        if chosen == "s3":
            raise RemoteConfigError(f"{REMOTE_ENV}=s3 but no RAW_STORE_S3_* variable is set")
        return None
    if len(present) != len(ENV_KEYS):
        missing = [k for k in ENV_KEYS if k not in present]
        raise RemoteConfigError(
            f"the shared raw store is half-configured: {missing} not set. Refusing "
            "rather than writing locally while looking shared - set all four, or none."
        )
    return S3Blobs(endpoint=values["RAW_STORE_S3_ENDPOINT"],
                   bucket=values["RAW_STORE_S3_BUCKET"],
                   key_id=values["RAW_STORE_S3_ACCESS_KEY_ID"],
                   secret=values["RAW_STORE_S3_SECRET_ACCESS_KEY"])
