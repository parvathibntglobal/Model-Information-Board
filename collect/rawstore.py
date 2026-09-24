"""The raw store: immutable, content-hash addressed payloads.

`document.text_ref` and `thread_context.flattened_text_ref` are both NOT NULL
and both point in here, so nothing in this lane can write a row until this
exists.

WHAT A REF IS
-------------
`text_ref` is a **location**; `content_hash` is **identity**. They are
separate columns because they answer different questions, and NFR-6 is what
forces the split: *"tombstone a document; its quotes vanish next run, only the
content hash remains."* That only parses if the hash and the stored bytes are
separable things. Keeping identity in the row means storage can move —
filesystem today, an object store later — without rewriting what anything is.

    ref  = "raw/sha256/ab/cd/abcd...ef"      -> document.text_ref
    hash = "abcd...ef"                        -> document.content_hash

The convention is not stated in `contract/tables.sql`, which gives both
columns and never says how they differ. It is sign-off item 15, and it needs
a comment rather than DDL. The public surface here is hash-first so that if
Engineer 2 prefers `text_ref` to *be* the hash, the change is one column
write rather than a redesign.

TWO NAMESPACES, DIFFERENT DURABILITY
------------------------------------
    raw/         fetched payloads. Irreplaceable. Never evictable.
    flattened/   derived thread text. A cache: regenerable from raw/.

NFR-4 requires a full rebuild from raw to always be possible, so `raw/` can
never be cleaned up and `flattened/` always can. That distinction is enforced
in code rather than left to a comment, because someone will eventually write
a cleanup script.

NO OBJECT STORE YET
-------------------
`BUILD-PLAN.md` specifies Postgres plus an object store, and that is right
eventually. Eight weeks on one machine does not need S3, and `boto3` bought
now is a dependency bought before it is used. Content addressing is what
makes this a deferral rather than a shortcut: migrating is a file copy plus a
`text_ref` rewrite. The surface is deliberately five verbs so an S3 backend
has a small target.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from collect.config import settings
from collect.ids import content_hash

log = logging.getLogger(__name__)

ALGO = "sha256"

#: NFR-6 covers two distinct events, and an audit six months later cannot
#: reconstruct which one happened from a bare deletion.
TombstoneReason = Literal["takedown-request", "upstream-deleted"]
TOMBSTONE_REASONS: tuple[str, ...] = ("takedown-request", "upstream-deleted")


class RawStoreError(RuntimeError):
    """Base for every raw-store failure."""


class PayloadTombstoned(RawStoreError):
    """The payload was deliberately removed. Not an error in the store.

    Distinct from `PayloadMissing` on purpose: a takedown and a corrupted
    store demand opposite responses, and a single not-found makes them
    indistinguishable.
    """

    def __init__(self, ref: str, marker: TombstoneMarker) -> None:
        self.ref = ref
        self.marker = marker
        super().__init__(
            f"{ref} was tombstoned at {marker.tombstoned_at.isoformat()} "
            f"({marker.reason}). Only the content hash remains: {marker.content_hash}"
        )


class PayloadMissing(RawStoreError):
    """A payload this store should be able to read, it cannot.

    **This is an ops alert, not a routine condition.** NFR-4 guarantees a full
    rebuild from the raw store; that guarantee is void *here* the moment a blob
    is unreadable without a tombstone, and it is void silently unless somebody
    is told. Raised loudly and logged at ERROR.

    ⚠ IT USED TO SAY "CORRUPTION OR A BUG", AND THE STORE CANNOT KNOW THAT
      (#303). Two very different states present as the same absent file:

          the blob was corrupted or deleted here      a broken guarantee
          the blob was written on another machine      a sync gap, and the
            and never synced to this one               store is intact

      And the second demonstrably exists: the 2026-09-15 dedupe stage reported
      **465 payloads not on this machine**, and `fetch_model.py`'s selection
      already treats an unreadable payload as "not this fetch's thread" rather
      than as damage. Measured the same day: 151 of 4,144 `thread_context`
      rows (3.6%) had unreadable flattened text on one laptop.

      There is no manifest to check against — no `raw_object`, `blob` or
      `tombstone` table exists, and nothing records which machine wrote which
      blob. So the store has no way to tell the two apart, and rule 6 says an
      absence it cannot explain must not be reported as a definite finding.

      What it CAN say is what it did: this store could not read this ref, and
      there is no tombstone, so the removal was not deliberate. That is true
      in both states and is what the message now says.
    """


class PayloadCorrupt(RawStoreError):
    """Stored bytes disagree with the key they are filed under."""


class EvictionRefused(RawStoreError):
    """Something tried to evict from `raw/`, which is not regenerable."""


class TombstoneRefused(RawStoreError):
    """Something tried to tombstone derived text rather than the original.

    A takedown recorded in the wrong namespace is worse than one refused: it
    reads as honoured while the words it was meant to remove are still in
    `raw/`, and the marker sits on a blob that could legitimately be
    regenerated tomorrow.
    """


@dataclass(frozen=True)
class Namespace:
    """A durability class, and the two removal verbs that follow from it.

    Exactly one applies to each namespace, which is the whole distinction:
    **irreplaceable things get tombstoned, regenerable things get evicted.**
    Nothing is both.
    """

    prefix: str
    evictable: bool
    tombstonable: bool


#: Fetched payloads. Reprocessing reads from here rather than re-fetching, so
#: losing one is unrecoverable — and it is the only place a deletion request
#: means anything, because it is the only place the original words live.
RAW = Namespace("raw", evictable=False, tombstonable=True)

#: The exact byte string sent to the extractor. Derived, so it can be dropped
#: and rebuilt; quote verification depends on it being byte-stable while it
#: exists.
FLATTENED = Namespace("flattened", evictable=True, tombstonable=False)

_NAMESPACES = {ns.prefix: ns for ns in (RAW, FLATTENED)}


@dataclass(frozen=True)
class StoredPayload:
    """What a caller needs to write a `document` or `thread_context` row."""

    ref: str  # -> text_ref / flattened_text_ref
    content_hash: str  # -> content_hash
    size: int
    already_present: bool


@dataclass(frozen=True)
class TombstoneMarker:
    content_hash: str
    tombstoned_at: datetime
    reason: str
    detail: str | None = None


@dataclass(frozen=True)
class PayloadStat:
    ref: str
    content_hash: str
    size: int | None
    tombstoned: TombstoneMarker | None

    @property
    def present(self) -> bool:
        return self.size is not None and self.tombstoned is None


def build_ref(hash_hex: str, namespace: Namespace = RAW) -> str:
    """`raw/sha256/ab/cd/abcd...` — sharded so no directory grows unbounded."""
    return f"{namespace.prefix}/{ALGO}/{hash_hex[:2]}/{hash_hex[2:4]}/{hash_hex}"


def parse_ref(ref: str) -> tuple[Namespace, str]:
    """Recover the namespace and content hash from a ref."""
    parts = ref.split("/")
    if len(parts) != 5 or parts[1] != ALGO:
        raise ValueError(f"not a raw-store ref: {ref!r}")
    namespace = _NAMESPACES.get(parts[0])
    if namespace is None:
        raise ValueError(f"unknown namespace in ref: {ref!r}")
    hash_hex = parts[4]
    if parts[2] != hash_hex[:2] or parts[3] != hash_hex[2:4]:
        raise ValueError(f"ref shards do not match its hash: {ref!r}")
    return namespace, hash_hex


class RawStore:
    """Content-addressed blobs on the filesystem."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else settings().raw_store_path

    # ── write ────────────────────────────────────────────────────────────

    def put(self, data: bytes | str, *, namespace: Namespace = RAW) -> StoredPayload:
        """Store a payload and return its ref and hash.

        **The caller never supplies the key.** The store derives it from the
        bytes, which is what makes "a bug writes different bytes under an
        existing key" unreachable rather than merely unlikely: there is no
        parameter through which a wrong key could arrive.

        On an existing key this is a **no-op**, so re-fetching an unchanged
        page costs nothing and stays idempotent, which NFR-4's rebuild needs.
        It is not a blind no-op: the stored size is compared to the incoming
        size first, and a mismatch raises `PayloadCorrupt` rather than
        silently trusting the key. Re-hashing every blob on every put would
        turn each write into a full read for a case that atomic writes
        already prevent; `verify()` exists for the sweep that genuinely
        checks.

        Never overwrites. Never refuses a legitimate re-put.
        """
        if isinstance(data, str):
            data = data.encode("utf-8")

        hash_hex = content_hash(data)
        ref = build_ref(hash_hex, namespace)
        path = self._path(ref)

        marker = self._read_marker(path)
        if marker is not None:
            raise PayloadTombstoned(ref, marker)

        if path.exists():
            existing = path.stat().st_size
            if existing != len(data):
                raise PayloadCorrupt(
                    f"{ref} holds {existing} bytes but the payload hashing to that "
                    f"key is {len(data)} bytes. The stored blob is corrupt."
                )
            return StoredPayload(ref, hash_hex, len(data), already_present=True)

        self._write_atomic(path, data)
        return StoredPayload(ref, hash_hex, len(data), already_present=False)

    def _write_atomic(self, path: Path, data: bytes) -> None:
        """Write via a temp file and rename.

        A partially written blob must never become visible under its key. The
        rename is atomic on POSIX and on Windows via `os.replace`, so a
        crash mid-write leaves a stray temp file rather than a truncated
        payload that would pass a size check forever after.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    # ── read ─────────────────────────────────────────────────────────────

    def get(self, ref: str) -> bytes:
        """The stored bytes.

        Raises `PayloadTombstoned` when removal was deliberate and
        `PayloadMissing` when it was not. Callers need to tell those apart:
        the first is honouring a request, the second is a broken guarantee.
        """
        path = self._path(ref)

        marker = self._read_marker(path)
        if marker is not None:
            raise PayloadTombstoned(ref, marker)

        if not path.exists():
            # NFR-4's rebuild-from-raw guarantee is void the moment this
            # happens, and void silently unless it is said out loud.
            # The requirement id is in the message on purpose: it is the one
            # token here that will not be rephrased, so monitoring and tests
            # can key on it without breaking every time the prose improves.
            # THE REQUIREMENT ID STAYS IN THE MESSAGE on purpose: it is the
            # one token here that will not be rephrased, so monitoring and
            # tests can key on it without breaking every time the prose
            # improves.
            log.error(
                "raw store: %s is not readable on this machine and carries no "
                "tombstone, so NFR-4 rebuild-from-raw is not available here. "
                "This store cannot tell a lost blob from one written on "
                "another machine and never synced (#303).",
                ref,
            )
            raise PayloadMissing(
                f"{ref} is not readable in this raw store and carries no "
                f"tombstone, so its removal was not deliberate. This store "
                f"cannot tell whether it was lost or was written elsewhere "
                f"and never synced here (#303)."
            )

        return path.read_bytes()

    def get_text(self, ref: str) -> str:
        return self.get(ref).decode("utf-8")

    def exists(self, ref: str) -> bool:
        """True only for a payload that is present and not tombstoned."""
        path = self._path(ref)
        return path.exists() and self._read_marker(path) is None

    def stat(self, ref: str) -> PayloadStat:
        """Everything known about a ref, without reading the payload."""
        _, hash_hex = parse_ref(ref)
        path = self._path(ref)
        marker = self._read_marker(path)
        size = path.stat().st_size if path.exists() else None
        return PayloadStat(ref=ref, content_hash=hash_hex, size=size, tombstoned=marker)

    def verify(self, ref: str) -> bool:
        """Re-hash a stored payload and confirm it matches its key.

        The real corruption detector, kept out of `put` so the write path is
        not a full read. An ops sweep calls this; nothing on the hot path
        does.
        """
        _, hash_hex = parse_ref(ref)
        return content_hash(self.get(ref)) == hash_hex

    # ── removal ──────────────────────────────────────────────────────────

    def tombstone(
        self,
        ref: str,
        *,
        reason: TombstoneReason,
        detail: str | None = None,
    ) -> TombstoneMarker:
        """Honour a deletion (NFR-6), keeping only the content hash.

        Immutability means not silently rewriting history, not refusing a
        deletion. The bytes go; a marker stays, so a later read can say
        *tombstoned on this date for this reason* rather than *not found*.

        `reason` is constrained because NFR-6 covers two different events. A
        takedown request and an upstream deletion look identical once the
        bytes are gone, and an audit six months later cannot tell them apart
        from an absence.

        **Only `raw/` can be tombstoned.** Derived text is regenerable, so
        there is nothing there to take down, and a marker on a blob that
        could legitimately be rebuilt tomorrow records nothing true.

        This does not finish the job on its own: a tombstoned document's
        flattened contexts still contain its words, and the caller must
        `evict()` those. The record lives on the original; the derivative is
        just dropped.
        """
        if reason not in TOMBSTONE_REASONS:
            raise ValueError(f"reason must be one of {TOMBSTONE_REASONS}: {reason!r}")

        namespace, hash_hex = parse_ref(ref)
        if not namespace.tombstonable:
            raise TombstoneRefused(
                f"refusing to tombstone {ref}: the {namespace.prefix!r} namespace holds "
                "derived text, which is regenerable and carries no deletion request of "
                "its own. Tombstone the raw payload and evict() this."
            )
        path = self._path(ref)
        marker = TombstoneMarker(
            content_hash=hash_hex,
            tombstoned_at=datetime.now(UTC),
            reason=reason,
            detail=detail,
        )

        self._marker_path(path).parent.mkdir(parents=True, exist_ok=True)
        self._write_atomic(
            self._marker_path(path),
            json.dumps(
                {
                    "content_hash": marker.content_hash,
                    "tombstoned_at": marker.tombstoned_at.isoformat(),
                    "reason": marker.reason,
                    "detail": marker.detail,
                },
                indent=2,
            ).encode("utf-8"),
        )
        path.unlink(missing_ok=True)
        return marker

    def evict(self, ref: str) -> bool:
        """Drop a regenerable payload. Refuses anything under `raw/`.

        Enforced here rather than documented, because a cleanup script that
        walks the store and deletes old files is a thing somebody writes
        eventually, and `raw/` is the one place that cannot survive it.

        ⚠  REDDIT DATA API TERMS 3.2 IS UNRESOLVED AGAINST THIS REFUSAL, and
        this is the file where somebody would try to resolve it.

        3.2 requires deleting data not required for the approved use case.
        `tombstone()` does not satisfy it: that honours a REQUEST — a takedown,
        or an upstream deletion we observed — and 3.2 asks for PROACTIVE
        retention limits on data nobody has asked about. This store has no
        retention policy at all, deliberately, because NFR-4 makes "reprocess
        from raw/ rather than re-fetch" the recovery path for the whole
        pipeline.

        So the conflict is narrow and real: not "we cannot delete", but "we
        never delete unprompted, by design". It is recorded on the
        `reddit-via-rapidapi` ruling in `contract/sources.yaml` and escalated
        to the MD on 2026-08-18. It is repeated here because a condition
        recorded only in a ruling is read by whoever writes rulings, and this
        is where whoever writes a retention sweep will be standing.

        **Do not add a Reddit retention path here without reopening that
        ruling.** Either it permits an exception to NFR-4 for one platform's
        payloads — which needs a story for how a rebuild works with a hole in
        it — or the approved use case is narrowed until 3.2 is satisfied by
        what we already keep.
        """
        namespace, _ = parse_ref(ref)
        if not namespace.evictable:
            raise EvictionRefused(
                f"refusing to evict {ref}: the {namespace.prefix!r} namespace is not "
                "regenerable, and NFR-4 requires a full rebuild from it to remain "
                "possible. Use tombstone() to honour a deletion."
            )
        path = self._path(ref)
        if not path.exists():
            return False
        path.unlink()
        return True

    # ── paths ────────────────────────────────────────────────────────────

    def _path(self, ref: str) -> Path:
        parse_ref(ref)  # reject anything malformed before touching the filesystem
        return self.root / ref

    @staticmethod
    def _marker_path(path: Path) -> Path:
        return path.with_name(path.name + ".tombstone")

    def _read_marker(self, path: Path) -> TombstoneMarker | None:
        marker_path = self._marker_path(path)
        if not marker_path.exists():
            return None
        raw = json.loads(marker_path.read_text(encoding="utf-8"))
        return TombstoneMarker(
            content_hash=raw["content_hash"],
            tombstoned_at=datetime.fromisoformat(raw["tombstoned_at"]),
            reason=raw["reason"],
            detail=raw.get("detail"),
        )
