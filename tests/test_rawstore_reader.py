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


def test_bytes_that_are_not_utf8_are_CORRUPT_rather_than_MISSING(store, reader):
    """The state the fourth outcome exists for, and it is reachable today.

    Present and not decodable is the definition of *something is there and we
    cannot trust it*. It used to escape as `UnicodeDecodeError` because three
    outcomes had nowhere to put it — that was the best answer available while the
    vocabulary was short, not a good one, and a resolver that sometimes raises
    and sometimes returns is two contracts in one signature.

    MISSING would be the actively harmful answer: it says the store has nothing,
    so somebody goes looking for a payload sitting on disk.
    """
    stored = store.put(b"\xff\xfe not utf-8 at all", namespace=RAW)

    result = reader.resolve(stored.ref)

    assert result.outcome is ReadOutcome.CORRUPT
    assert result.outcome is not ReadOutcome.MISSING
    assert result.text is None
    assert not result.found
    assert result.ref == stored.ref


def test_payload_corrupt_from_the_store_maps_to_CORRUPT(store, reader, monkeypatch):
    """Unreachable on a read today, mapped anyway.

    `PayloadCorrupt` is raised by `put()` on a size mismatch and nothing hashes
    on read, so this is the one clause with no live producer. Mapping it now
    means the day a verify sweep exists, this file needs no change — and the
    mapping is complete rather than complete-for-now.
    """
    from collect.rawstore import PayloadCorrupt

    def boom(_ref):
        raise PayloadCorrupt("size on disk disagrees with the incoming payload")

    monkeypatch.setattr(store, "get_text", boom)

    assert reader.resolve("flattened/sha256/ab/ab/" + "ab" * 32).outcome is ReadOutcome.CORRUPT


def test_a_foreign_member_is_coerced_so_identity_stays_safe():
    """Her point, asserted rather than trusted to discipline.

    `ReadOutcome.MISSING == Outcome.MISSING` is True; `is` is False. So a member
    that crossed the boundary satisfies every equality check and fails every
    identity check — and both directions lean the wrong way silently: a FOUND
    payload reads as not-found, a CORRUPT one reads as trustworthy.

    `__post_init__` coerces by value, so every `is` in the module is downstream
    of it. This constructs `StoreText` with HER member on purpose.
    """
    assert ReadOutcome.MISSING == Outcome.MISSING
    assert ReadOutcome.MISSING is not Outcome.MISSING

    crossed = StoreText(ref="raw/x", outcome=Outcome.CORRUPT)
    assert crossed.outcome is ReadOutcome.CORRUPT
    assert not crossed.found

    found = StoreText(ref="raw/x", outcome=Outcome.FOUND, text="body")
    assert found.outcome is ReadOutcome.FOUND
    assert found.found, "a FOUND payload read by identity must not look not-found"

    # And a bare string, which is what a jsonb round trip or an API hands back.
    assert StoreText(ref="raw/x", outcome="tombstoned").outcome is ReadOutcome.TOMBSTONED


def test_nothing_in_the_lane_compares_a_crossable_value_by_identity():
    """The audit behind the fix, kept as a test so a new `is` has to justify itself.

    Every identity comparison against `ReadOutcome` in `collect/` must sit on a
    value that `__post_init__` has already coerced — that is, on
    `StoreText.outcome`. An `is` against a value taken straight from a caller,
    a database row or a JSON payload is the failure this class describes.
    """
    import re
    from pathlib import Path

    lane = Path(__file__).resolve().parents[1] / "collect"
    offenders = []
    for path in lane.rglob("*.py"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "#" in line and line.strip().startswith("#"):
                continue
            for match in re.finditer(r"(\S+)\s+is(?: not)?\s+ReadOutcome\.", line):
                subject = match.group(1)
                if not subject.endswith(".outcome"):
                    offenders.append(f"{path.name}:{number}: {line.strip()[:70]}")

    assert not offenders, (
        "an identity comparison against a value that did not come through "
        f"StoreText.__post_init__: {offenders}"
    )


def test_the_old_raising_behaviour_is_gone(store, reader):
    """Explicit, because a retired decision that leaves no trace gets re-made."""
    stored = store.put(b"\xff\xfe", namespace=RAW)
    reader.resolve(stored.ref)  # must not raise


def _unused_old_decode_test(store, reader):
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
    # PAIRS, not two independent sets. Equal names and equal values do not imply
    # an equal MAPPING: ours could read MISSING="corrupt" and CORRUPT="missing"
    # and satisfy both set comparisons while inverting the two states that matter
    # most — a corrupt payload reported as absent, and an absent one reported as
    # corrupt. Engineer 2 named this class; the set-wise version of this
    # assertion could not see it.
    assert {(o.name, o.value) for o in ReadOutcome} == {(o.name, o.value) for o in Outcome}
    assert len(list(ReadOutcome)) == len(list(Outcome)) == 4


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


def test_nothing_computes_a_hash_on_read_so_CORRUPT_is_unreachable():
    """The state a fourth outcome will describe, and nothing produces it yet.

    Worth asserting rather than asserting the absence of a clause: the reason
    `CORRUPT` will read zero is not that the adapter mishandles corruption, it is
    that **no read path hashes anything**. `get` returns `read_bytes()`;
    `verify` is the method that hashes and it has no production caller.

    This test fails the day either changes, which is the day the mapping starts
    producing values - so it is a reminder rather than a guard.
    """
    import inspect

    from collect import rawstore

    read_path = inspect.getsource(rawstore.RawStore.get) + inspect.getsource(
        rawstore.RawStore.get_text
    )
    assert "content_hash" not in read_path, "a read path now hashes; CORRUPT is reachable"
    assert "verify" not in read_path

    hashing = inspect.getsource(rawstore.RawStore.verify)
    assert "content_hash" in hashing, "verify() is where hashing lives"


def test_the_marker_reader_swallows_nothing(tmp_path):
    """A corrupt tombstone marker must not become MISSING, and does not.

    `_read_marker` parses JSON and indexes three keys, so an unreadable marker
    raises rather than reporting "no marker" — which would fold TOMBSTONED into
    MISSING one layer below this adapter, where no `except` clause of mine could
    see it. Asserted because the hazard was looked for deliberately: three of the
    defects in this file's history were a helper more permissive than the
    contract it serves.
    """
    import json

    from collect.rawstore import RAW, RawStore

    store = RawStore(tmp_path)
    stored = store.put("body", namespace=RAW)
    store.tombstone(stored.ref, reason="takedown-request")

    marker = next(tmp_path.rglob("*.tombstone*"))
    marker.write_text("{not json", encoding="utf-8")

    reader = RawStoreReader(store)
    with pytest.raises(json.JSONDecodeError):
        reader.resolve(stored.ref)


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
