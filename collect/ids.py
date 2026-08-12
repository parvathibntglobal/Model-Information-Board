"""Deterministic identifiers.

Every id this lane mints is a pure function of the thing it names. Reloading
the same seed file, or reprocessing the same raw payload, produces the same
ids — which is what makes "drop all derived rows and rebuild" (NFR-4) a real
operation rather than an aspiration.
"""

from __future__ import annotations

import hashlib

_ID_LEN = 16


def content_hash(data: bytes | str) -> str:
    """SHA-256 of a payload, hex. The address of a raw document."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def stable_id(prefix: str, *parts: str) -> str:
    """A short deterministic id: ``prefix_<hash of parts>``.

    Parts are joined with a NUL byte, which cannot appear in any of the
    values we hash, so ("a", "bc") and ("ab", "c") never collide.
    """
    if not parts:
        raise ValueError("stable_id needs at least one part")
    joined = "\x00".join(parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(joined).hexdigest()[:_ID_LEN]}"


def model_version_id(canonical_id: str) -> str:
    return stable_id("mv", canonical_id)


def model_alias_id(normalized: str, model_version_id_: str, valid_from: str) -> str:
    """FR-4: `model_alias` is append-only.

    The id covers everything that makes an alias row distinct, so re-running
    the loader collides on the primary key and does nothing, rather than
    updating a row that history depends on.
    """
    return stable_id("ma", normalized, model_version_id_, valid_from)


def model_event_id(model_version_id_: str, event_type: str, detail: str) -> str:
    return stable_id("ev", model_version_id_, event_type, detail)
