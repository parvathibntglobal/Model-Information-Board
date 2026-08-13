"""The raw store: addressing, immutability, tombstones, eviction.

No database needed. The integration with `document` lives in
`test_rawstore_db.py`, because that is where a write is involved.
"""

from __future__ import annotations

import json

import pytest

from collect.ids import content_hash
from collect.rawstore import (
    FLATTENED,
    RAW,
    EvictionRefused,
    PayloadCorrupt,
    PayloadMissing,
    PayloadTombstoned,
    RawStore,
    TombstoneRefused,
    build_ref,
    parse_ref,
)

PAYLOAD = b'{"title": "tool calling fails at the 7th call", "body": "..."}'


@pytest.fixture
def store(tmp_path):
    return RawStore(tmp_path / "raw_store")


# ── addressing ────────────────────────────────────────────────────────────


def test_a_ref_is_a_location_and_the_hash_is_identity():
    """Reading B. text_ref locates, content_hash identifies (NFR-6)."""
    hash_hex = content_hash(PAYLOAD)
    ref = build_ref(hash_hex)
    assert ref == f"raw/sha256/{hash_hex[:2]}/{hash_hex[2:4]}/{hash_hex}"
    assert ref != hash_hex


def test_refs_shard_so_no_directory_grows_unbounded(store):
    stored = store.put(PAYLOAD)
    path = store.root / stored.ref
    assert path.parent.name == stored.content_hash[2:4]
    assert path.parent.parent.name == stored.content_hash[:2]


def test_parse_ref_round_trips():
    hash_hex = content_hash(PAYLOAD)
    namespace, parsed = parse_ref(build_ref(hash_hex, FLATTENED))
    assert namespace is FLATTENED
    assert parsed == hash_hex


@pytest.mark.parametrize(
    "bad",
    [
        "not-a-ref",
        "raw/md5/ab/cd/abcd",  # wrong algorithm
        "nowhere/sha256/ab/cd/abcd",  # unknown namespace
        "raw/sha256/zz/cd/abcdef",  # shards disagree with the hash
    ],
)
def test_a_malformed_ref_is_rejected(bad: str):
    with pytest.raises(ValueError):
        parse_ref(bad)


def test_a_malformed_ref_never_touches_the_filesystem(store):
    with pytest.raises(ValueError):
        store.get("../../etc/passwd")


# ── put ───────────────────────────────────────────────────────────────────


def test_put_returns_what_a_document_row_needs(store):
    stored = store.put(PAYLOAD)
    assert stored.content_hash == content_hash(PAYLOAD)
    assert stored.size == len(PAYLOAD)
    assert stored.already_present is False
    assert store.get(stored.ref) == PAYLOAD


def test_text_is_stored_as_utf8(store):
    stored = store.put("engineers report [fire] tool calling")
    assert store.get_text(stored.ref) == "engineers report [fire] tool calling"


def test_re_putting_identical_bytes_is_a_no_op(store):
    """Re-fetching an unchanged page must cost nothing and stay idempotent."""
    first = store.put(PAYLOAD)
    second = store.put(PAYLOAD)
    assert second.ref == first.ref
    assert second.already_present is True


def test_the_caller_cannot_supply_a_key(store):
    """The bug class is unreachable by construction, not merely unlikely.

    `put` derives the key from the bytes, so there is no parameter through
    which a wrong key could arrive.
    """
    import inspect

    params = set(inspect.signature(store.put).parameters)
    assert params == {"data", "namespace"}


def test_a_corrupt_blob_is_caught_rather_than_trusted(store):
    """Same key, different size: the stored blob is wrong, so say so."""
    stored = store.put(PAYLOAD)
    (store.root / stored.ref).write_bytes(b"truncated")

    with pytest.raises(PayloadCorrupt, match="corrupt"):
        store.put(PAYLOAD)


def test_different_payloads_get_different_refs(store):
    assert store.put(b"one").ref != store.put(b"two").ref


def test_a_partial_write_never_becomes_visible(store, monkeypatch):
    """Atomic rename: a crash mid-write leaves a temp file, not a blob."""
    import collect.rawstore as rawstore

    real_replace = rawstore.os.replace

    def explode(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(rawstore.os, "replace", explode)
    with pytest.raises(OSError):
        store.put(PAYLOAD)

    monkeypatch.setattr(rawstore.os, "replace", real_replace)
    assert not store.exists(build_ref(content_hash(PAYLOAD)))
    # and no temp files survive the failure
    assert list(store.root.rglob("*.tmp")) == []


# ── the read path tells deliberate from broken ────────────────────────────


def test_a_missing_payload_is_not_a_tombstone(store):
    """The distinction that would have been expensive to retrofit."""
    stored = store.put(PAYLOAD)
    (store.root / stored.ref).unlink()

    with pytest.raises(PayloadMissing):
        store.get(stored.ref)


def test_a_missing_payload_is_logged_as_an_ops_problem(store, caplog):
    """NFR-4's rebuild guarantee is void once this happens, and void silently
    unless somebody is told.

    Asserts the load-bearing parts only: the severity, which ref, and the
    requirement it voids. Deliberately not the sentence — the first person to
    improve the wording should not break a test.
    """
    import logging

    stored = store.put(PAYLOAD)
    (store.root / stored.ref).unlink()

    with (
        caplog.at_level(logging.ERROR, logger="collect.rawstore"),
        pytest.raises(PayloadMissing),
    ):
        store.get(stored.ref)

    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1
    message = errors[0].getMessage()
    assert stored.ref in message  # which blob
    assert "NFR-4" in message  # what it voids


def test_a_tombstoned_payload_raises_its_own_exception(store):
    stored = store.put(PAYLOAD)
    store.tombstone(stored.ref, reason="takedown-request")

    with pytest.raises(PayloadTombstoned) as excinfo:
        store.get(stored.ref)
    assert not isinstance(excinfo.value, PayloadMissing)


# ── NFR-6 ─────────────────────────────────────────────────────────────────


def test_tombstoning_leaves_only_the_content_hash(store):
    """NFR-6's acceptance, executed."""
    stored = store.put(PAYLOAD)
    marker = store.tombstone(stored.ref, reason="upstream-deleted")

    assert not (store.root / stored.ref).exists()  # bytes gone
    assert marker.content_hash == stored.content_hash  # hash remains
    assert store.stat(stored.ref).content_hash == stored.content_hash


def test_the_marker_records_which_event_it_was(store):
    """A takedown and an upstream deletion look identical once bytes are gone."""
    stored = store.put(PAYLOAD)
    store.tombstone(stored.ref, reason="takedown-request", detail="ticket 4471")

    marker = store.stat(stored.ref).tombstoned
    assert marker.reason == "takedown-request"
    assert marker.detail == "ticket 4471"
    assert marker.tombstoned_at is not None


def test_the_marker_survives_on_disk_as_readable_json(store):
    stored = store.put(PAYLOAD)
    store.tombstone(stored.ref, reason="upstream-deleted")

    raw = json.loads((store.root / (stored.ref + ".tombstone")).read_text(encoding="utf-8"))
    assert raw["content_hash"] == stored.content_hash
    assert raw["reason"] == "upstream-deleted"


def test_an_unrecognised_reason_is_refused(store):
    stored = store.put(PAYLOAD)
    with pytest.raises(ValueError, match="reason must be one of"):
        store.tombstone(stored.ref, reason="felt-like-it")


def test_re_putting_a_tombstoned_payload_does_not_resurrect_it(store):
    """Honouring a deletion has to survive the next harvest run."""
    stored = store.put(PAYLOAD)
    store.tombstone(stored.ref, reason="takedown-request")

    with pytest.raises(PayloadTombstoned):
        store.put(PAYLOAD)


def test_exists_is_false_for_a_tombstoned_payload(store):
    stored = store.put(PAYLOAD)
    assert store.exists(stored.ref)
    store.tombstone(stored.ref, reason="upstream-deleted")
    assert not store.exists(stored.ref)


# ── namespaces and eviction ───────────────────────────────────────────────


def test_the_two_namespaces_are_separate(store):
    raw = store.put(PAYLOAD, namespace=RAW)
    flat = store.put(PAYLOAD, namespace=FLATTENED)
    assert raw.content_hash == flat.content_hash  # same identity
    assert raw.ref != flat.ref  # different location


def test_flattened_text_is_evictable(store):
    stored = store.put(b"root post\n> reply", namespace=FLATTENED)
    assert store.evict(stored.ref) is True
    assert not store.exists(stored.ref)


def test_raw_payloads_cannot_be_evicted(store):
    """A cleanup script walking the store is a thing somebody writes."""
    stored = store.put(PAYLOAD, namespace=RAW)
    with pytest.raises(EvictionRefused, match="NFR-4"):
        store.evict(stored.ref)
    assert store.exists(stored.ref)


def test_derived_text_cannot_be_tombstoned(store):
    """A takedown recorded in the wrong namespace is worse than one refused.

    It reads as honoured while the words are still in `raw/`, and it marks a
    blob that could legitimately be regenerated tomorrow.
    """
    stored = store.put(b"ROOT: ...\nREPLY: ...", namespace=FLATTENED)
    with pytest.raises(TombstoneRefused, match="regenerable"):
        store.tombstone(stored.ref, reason="takedown-request")
    assert store.exists(stored.ref)


def test_each_namespace_supports_exactly_one_removal_verb(store):
    """Irreplaceable things get tombstoned; regenerable things get evicted."""
    assert RAW.tombstonable and not RAW.evictable
    assert FLATTENED.evictable and not FLATTENED.tombstonable


def test_honouring_a_takedown_takes_two_calls(store):
    """The record lives on the original; the derivative is just dropped.

    A tombstoned document's flattened context still contains its words, so
    tombstone() alone does not finish the job.
    """
    original = store.put(PAYLOAD, namespace=RAW)
    derived = store.put(PAYLOAD, namespace=FLATTENED)

    store.tombstone(original.ref, reason="takedown-request")
    assert store.exists(derived.ref)  # still there, still readable

    store.evict(derived.ref)
    assert not store.exists(derived.ref)


def test_evicting_an_absent_payload_is_not_an_error(store):
    assert store.evict(build_ref(content_hash(b"never stored"), FLATTENED)) is False


def test_eviction_is_refused_by_namespace_not_by_path(store):
    """The guard reads the ref, so it cannot be sidestepped by a crafted path."""
    with pytest.raises(EvictionRefused):
        store.evict(build_ref(content_hash(b"anything"), RAW))


# ── verify ────────────────────────────────────────────────────────────────


def test_verify_confirms_a_good_payload(store):
    assert store.verify(store.put(PAYLOAD).ref) is True


def test_verify_catches_a_silently_altered_payload(store):
    """The real corruption detector, kept off the write path."""
    stored = store.put(PAYLOAD)
    (store.root / stored.ref).write_bytes(PAYLOAD + b"tampered")
    assert store.verify(stored.ref) is False


def test_stat_reports_presence_without_reading_the_payload(store):
    stored = store.put(PAYLOAD)
    info = store.stat(stored.ref)
    assert info.present is True
    assert info.size == len(PAYLOAD)
    assert info.tombstoned is None


def test_stat_of_an_absent_ref_is_not_an_error(store):
    info = store.stat(build_ref(content_hash(b"never stored")))
    assert info.present is False
    assert info.size is None
