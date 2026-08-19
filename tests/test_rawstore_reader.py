"""The store-to-outcome mapping, and the collapse it exists to prevent.

Every test here is about one of two things: that a deletion we honoured stays
distinguishable from a payload that vanished, and that the two vocabularies —
`collect`'s exceptions and `judge`'s outcomes — still agree.

This file may import both lanes. `tests/` is owned by neither
(`tests/conftest.py`), and the import rule
`test_collect_never_imports_judge` is scoped to `collect/`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from collect.rawstore import FLATTENED, RAW, RawStore, build_ref
from collect.rawstore_reader import RawStoreReader, ReadOutcome, StoreText
from judge.extract.resolver import Outcome, RawTextResolver, ResolvedText


@pytest.fixture
def store(tmp_path: Path) -> RawStore:
    return RawStore(tmp_path)


@pytest.fixture
def reader(store: RawStore) -> RawStoreReader:
    return RawStoreReader(store)


# ── the three outcomes ───────────────────────────────────────────────────


def test_a_present_payload_is_found_and_carries_its_text(store, reader):
    stored = store.put("the article body", namespace=FLATTENED)

    result = reader.resolve(stored.ref)

    assert result.outcome is ReadOutcome.FOUND
    assert result.found
    assert result.text == "the article body"
    assert result.ref == stored.ref
    assert result.require() == "the article body"


def test_a_tombstoned_payload_is_TOMBSTONED_and_not_missing(store, reader):
    """The collapse this file exists to prevent, in one assertion.

    `except RawStoreError` would return MISSING here, and MISSING means "the
    store lost it or the row was written against a different store — both need
    investigating". The payload is gone either way, so nothing downstream can
    contradict the wrong answer: somebody investigates a deletion we performed
    on purpose, finds no evidence, and concludes the store is unreliable.
    """
    stored = store.put("about to be taken down", namespace=RAW)
    store.tombstone(stored.ref, reason="takedown-request")

    result = reader.resolve(stored.ref)

    assert result.outcome is ReadOutcome.TOMBSTONED
    assert result.outcome is not ReadOutcome.MISSING
    assert result.text is None
    assert not result.found


def test_an_absent_payload_is_MISSING(store, reader):
    absent = build_ref("ab" * 32, FLATTENED)

    result = reader.resolve(absent)

    assert result.outcome is ReadOutcome.MISSING
    assert result.text is None
    assert result.ref == absent


def test_the_two_failures_do_not_share_a_message(store, reader):
    """`require()` has to say WHICH failure, or the distinction dies at the edge.

    Carrying two outcomes and then describing them identically would preserve
    the distinction in the type and lose it in the only place a person reads.
    """
    tombstoned = store.put("gone on purpose", namespace=RAW)
    store.tombstone(tombstoned.ref, reason="upstream-deleted")

    with pytest.raises(LookupError) as taken_down:
        reader.resolve(tombstoned.ref).require()
    with pytest.raises(LookupError) as vanished:
        reader.resolve(build_ref("ff" * 32, RAW)).require()

    assert "nothing is broken" in str(taken_down.value)
    assert "need investigating" in str(vanished.value)
    assert str(taken_down.value) != str(vanished.value)


# ── what must NOT be folded into an outcome ──────────────────────────────


def test_bytes_that_are_not_utf8_raise_rather_than_reporting_MISSING(store, reader):
    """Corruption has no outcome, so it must not borrow one.

    `MISSING` asserts the store has nothing. Here the store has something and it
    is wrong, which is a different repair — restore the blob, or re-fetch from
    source — and reporting MISSING sends somebody to look for a payload that is
    sitting on disk.

    Raising is correct precisely because it is loud: a caller crashing on a
    corrupt blob is recoverable, and a corrupt blob counted as absent is the
    silent kind of wrong this project keeps paying for.
    """
    stored = store.put(b"\xff\xfe not utf-8 at all", namespace=RAW)

    with pytest.raises(UnicodeDecodeError):
        reader.resolve(stored.ref)


def test_the_reader_writes_nothing(reader):
    """Read-only structurally, not by promise."""
    for verb in ("put", "tombstone", "evict", "delete", "verify"):
        assert not hasattr(reader, verb), f"the reader exposes {verb}"


# ── the two vocabularies must keep agreeing ──────────────────────────────


def test_the_reader_satisfies_judge_s_protocol(reader):
    """Structural conformance, checked rather than assumed.

    `collect/` cannot import `judge/`, so nothing in the implementation refers
    to her Protocol. This is the only place the two are put in a room together.
    """
    assert isinstance(reader, RawTextResolver)


def test_the_two_outcome_enums_have_the_same_members_and_values():
    """The duplication is flagged in the module docstring; this is its guard.

    `ReadOutcome` mirrors `judge`'s `Outcome` because the lane rule forbids
    importing it. A duplicated type is the drift shape, so the agreement is
    asserted: adding a fourth outcome on either side, or renaming one, fails
    here rather than silently producing a value the other side cannot read.
    """
    assert {o.name for o in ReadOutcome} == {o.name for o in Outcome}
    assert {o.value for o in ReadOutcome} == {o.value for o in Outcome}


def test_the_two_value_types_have_the_same_surface():
    """Same reason. Her `ResolvedText` and our `StoreText` must stay readable
    by the same consumer, so the fields and the derived members must match."""
    ours = {f for f in StoreText.__dataclass_fields__}
    theirs = {f for f in ResolvedText.__dataclass_fields__}
    assert ours == theirs

    for member in ("found", "require"):
        assert hasattr(StoreText, member) and hasattr(ResolvedText, member)


def test_a_string_comparison_works_across_both_enums(store, reader):
    """Both are `StrEnum`, so a consumer holding either compares to the value.

    This is what makes the duplication survivable in the meantime: the thing
    that crosses the boundary is the string, not the class.
    """
    stored = store.put("text", namespace=FLATTENED)

    assert reader.resolve(stored.ref).outcome == Outcome.FOUND.value
    assert reader.resolve(stored.ref).outcome == "found"


def test_payload_corrupt_cannot_reach_the_reader():
    """Checked, because the reverse would argue for a fourth outcome.

    `PayloadCorrupt` is raised by `put()` on a size mismatch against an existing
    key. Nothing on the read path raises it, so the reader has no clause for it
    and needs none.
    """
    import inspect

    from collect import rawstore

    read_path = inspect.getsource(rawstore.RawStore.get) + inspect.getsource(
        rawstore.RawStore.get_text
    )
    assert "PayloadCorrupt" not in read_path
    assert "PayloadTombstoned" in read_path
    assert "PayloadMissing" in read_path


def test_a_malformed_ref_raises_rather_than_reporting_MISSING(reader):
    """Found by a bug in this file's own fixtures, and worth keeping.

    `parse_ref` validates that the shard directories match the hash, so a ref
    that was never produced by `build_ref` raises `ValueError` before any
    filesystem access. That must not become `MISSING`: MISSING is a claim about
    the STORE, and this is a claim about the CALLER — a ref that no store could
    hold, most likely hand-built or truncated in transit.

    Same rule as the decode failure above: a state the outcomes cannot express
    must not borrow one that means something else.
    """
    with pytest.raises(ValueError, match="shards do not match"):
        reader.resolve("flattened/sha256/ab/cd/" + "ab" * 32)
