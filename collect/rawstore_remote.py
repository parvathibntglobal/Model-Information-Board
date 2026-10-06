"""The shared half of the raw store: an S3-compatible bucket behind the local one.

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

CONFIGURED BY FOUR VARIABLES, ALL OR NONE (rule 12):

    RAW_STORE_S3_ENDPOINT          e.g. https://<account>.r2.cloudflarestorage.com
    RAW_STORE_S3_BUCKET
    RAW_STORE_S3_ACCESS_KEY_ID
    RAW_STORE_S3_SECRET_ACCESS_KEY

None set: local only, exactly as before. Some set: refuse - a half-configured
remote would write locally and look shared.
"""
from __future__ import annotations

import os

ENV_KEYS = (
    "RAW_STORE_S3_ENDPOINT",
    "RAW_STORE_S3_BUCKET",
    "RAW_STORE_S3_ACCESS_KEY_ID",
    "RAW_STORE_S3_SECRET_ACCESS_KEY",
)


class RemoteConfigError(RuntimeError):
    """Some, not all, of the RAW_STORE_S3_* variables are set."""


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


def remote_from_env() -> S3Blobs | None:
    """The configured bucket, None when none is configured. Partial config raises."""
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
    if not present:
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
