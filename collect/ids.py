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


def model_alias_id(normalized: str, model_version_id_: str, content_key: str) -> str:
    """FR-4: `model_alias` is append-only.

    The id covers what the row *asserts* - this surface means this model
    version, at this specificity - and deliberately **not** the window it
    asserts it over.

    Folding `valid_from` in here was a real defect. Correcting a
    `release_date` minted fresh ids for every alias of that model, they all
    inserted against `ON CONFLICT DO NOTHING`, the old rows kept
    `valid_until = NULL`, and two live rows ended up sharing a `normalized`
    over overlapping windows. That is the exact ambiguity `find_collisions`
    exists to catch, and it could not see it because it only ever read the
    YAML.

    Keying on content instead means a date correction is a no-op, while a
    genuine change to what the alias claims mints a new id, so the old row
    can be closed out and the new one appended.
    """
    return stable_id("ma", normalized, model_version_id_, content_key)


# `model_event_id` used to live here and was deliberately removed.
#
# Events are occurrences, not facts. Two identical price transitions on
# different days are two events, and any id derived only from what changed
# collapses them into one. Making it unique needs a timestamp, at which point
# it is a UUID with extra steps and no longer offers the re-run idempotency
# that determinism was for. `collect.registry.load._record_event` mints a
# random id and takes idempotency from the change condition instead.
