"""`collect/`'s side of `judge/`'s `RawTextResolver`. Store exceptions to outcomes.

`judge/extract/resolver.py` (hers, main via #90) defines the contract: a `resolve`
method returning a value carrying `ref`, `outcome` and `text`, where the outcome
is one of three states and never a boolean. It says the mapping is ours:

    "the store maps its exceptions onto this, and it is the only thing that
     needs to know both vocabularies"

This is that mapping, and it is the FIRST code interface across the lane
boundary — everything before it crossed through tables.

TWO EXCEPT CLAUSES, BOTH NAMED, AND THAT IS THE POINT
-----------------------------------------------------
`RawStore.get` raises exactly two things, and they mean opposite things:

    PayloadTombstoned   a deletion we honoured. NFR-6: the quotes vanish and
                        the content hash remains. NOTHING IS BROKEN.
    PayloadMissing      the ref points at nothing. A bug, and an urgent one -
                        either the store lost it or the row was written
                        against a different store.

`except RawStoreError` catches both, and `except Exception` catches those plus
everything else. Either one folds a deletion we performed on purpose into an
urgent data-loss alarm — and the payload is gone in both cases, so there is
nothing left to disagree with the wrong answer. The whole value of her
three-state enum is destroyed by one clause that is shorter to write.

So: one clause per exception, named, and no base class.

WHAT HAPPENS TO CORRUPTION, AND WHY IT IS UNDETECTED RATHER THAN MISHANDLED
--------------------------------------------------------------------------
**A fourth outcome is coming and it is right.** `MISSING` means nothing is there
and the repair is upstream; `CORRUPT` means something is there and does not match
its hash, and the repair is that we cannot trust what we stored. Different
urgency, and only one of them is a reason to stop. Engineer 2's enum, so this
file waits for her to add it rather than mapping onto a member that does not
exist.

**And nothing produces the state today.** Verified 2026-08-19:

    RawStore.get      reads the marker, checks existence, returns read_bytes().
                      NO HASH IS COMPUTED on any read path.
    RawStore.verify   the method that does hash, and it has NO production
                      caller - two test call sites and nothing else.
    PayloadCorrupt    raised only by `put()`, on a SIZE mismatch against an
                      existing key. A write-path event, and size only.

So corruption is **undetected rather than mishandled**, which is worth stating
plainly: a fourth value for a state nothing currently produces is still worth
having - the distinction is real and the mapping should exist before the detector
does, not after - and it is worth knowing it will read zero until something
computes a hash on read.

The route to reachability is NOT a check inside `get()`. `put()`'s own docstring
already made that trade for writes - "re-hashing every blob on every put would
turn each write into a full read for a case that atomic writes already prevent;
`verify()` exists for the sweep that genuinely checks" - and the same arithmetic
applies to reads. It is a sweep that calls `verify()` and tombstones or
quarantines what fails.

ONE SCOPING NOTE FOR THE ENUM MEMBER, because `get()` invites the mistake: its
`PayloadMissing` log says "This is corruption or a bug, not a takedown". That
message is about absence CAUSED by corruption, and absence is still `MISSING`.
`CORRUPT` should mean present-and-wrong, or the two collapse again from the other
direction.

What CAN happen on a read is bytes that are present and not valid UTF-8.
`get_text` decodes, so that surfaces as `UnicodeDecodeError`, and there is no
outcome for it: `MISSING` says the store has nothing, and the store has
something. **It propagates deliberately.** A caller crashing on a corrupt blob
is recoverable; a corrupt blob reported as `MISSING` sends somebody to look for
a payload that is sitting right there. This is the one place where raising
rather than returning is correct, and it is the case her `Outcome` deliberately
does not cover.

EVERY WAY THIS CAN RAISE, WHICH IS MORE THAN THE TWO I FIRST WROTE DOWN
-----------------------------------------------------------------------
Audited 2026-08-19 after the ruling that **a resolver which sometimes raises and
sometimes returns is two contracts in one signature.** By that standard this file
currently is two contracts, and the list is the evidence rather than a defence:

    UnicodeDecodeError        bytes present, not valid UTF-8 (`get_text` decodes)
    ValueError                a ref `build_ref` never produced (`parse_ref`)
    JSONDecodeError, KeyError, ValueError
                              a tombstone marker that is present and unreadable
                              (`_read_marker` parses JSON and indexes three keys)

The third was not in the original list and is the one worth having found: it
means a corrupt MARKER cannot silently become `MISSING`, because nothing swallows
it — good — but it also means this method raises from a path its docstring did
not mention. `RawStore._read_marker` is not permissive; the omission was mine.

**The decode failure stops being a raise the moment `Outcome.CORRUPT` lands.**
Non-UTF-8 bytes are the definition of present-and-wrong, so under a fourth
outcome it maps there rather than escaping the signature. That retires the
argument the current docstring makes for raising, and it should be retired: it
was the best available answer while three outcomes were all there were.

The malformed ref is a different case and stays open: it is a claim about the
CALLER rather than about the store, and no outcome describing a payload can carry
it. Flagged rather than settled.

`ResolvedText` IS DUPLICATED HERE, AND THAT IS NOT A CHOICE I CAN MAKE ALONE
----------------------------------------------------------------------------
`tests/test_lane_boundary.py::test_collect_never_imports_judge` asserts this
package never imports hers, so this file cannot import `ResolvedText` or
`Outcome`. Her `RawTextResolver` is a `Protocol` precisely so the implementation
does not have to — but a Protocol constrains the METHOD, not the return value's
type, so satisfying it means constructing something with the same surface.

**That leaves three options and none of them is free:**

    duplicate the value type here      the drift shape, and this file is it
    move the shared type to contract/  contract/ holds SQL and YAML, not
                                       Python, so this would be a new kind of
                                       shared artefact
    let judge/ construct it            then this returns a pair and is not a
                                       RawTextResolver at all

I have taken the first because it is the only one available without changing
the contract, and it is FLAGGED RATHER THAN SETTLED: `contract/` changes on
purpose, about five times in eight weeks, and this is a decision for both of us.
The duplication is real today — two enums with the same three members, two value
types with the same three fields — and `tests/test_rawstore_reader.py` asserts
they agree, so a change to one that is not made to the other fails rather than
drifts.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from collect.rawstore import (
    PayloadCorrupt,
    PayloadMissing,
    PayloadTombstoned,
    RawStore,
)


class ReadOutcome(StrEnum):
    """Mirrors `judge.extract.resolver.Outcome`. Same three values, by contract.

    The VALUES are what cross the boundary — this is a `StrEnum` so
    `outcome == "tombstoned"` holds whichever enum a reader is holding. The
    names match hers deliberately; a rename on either side is a break and the
    test says so.
    """

    FOUND = "found"

    #: A deletion we honoured (NFR-6). Nothing is broken and nothing needs
    #: repairing. NOT an error, and the reason there are two except clauses.
    TOMBSTONED = "tombstoned"

    #: The ref points at nothing, with no tombstone beside it. A bug: either
    #: the store lost the payload or the row was written against a different
    #: store. Both need investigating.
    MISSING = "missing"

    #: Something IS there and does not match what we recorded, so we cannot
    #: trust what we stored. Distinct from MISSING in urgency and in repair: a
    #: batch can reasonably skip an absent payload and carry on, and carrying on
    #: past a corrupt one writes claims sourced from a store just shown to be
    #: unreliable.
    #:
    #: Value matches `judge.extract.resolver.Outcome.CORRUPT` exactly, which is
    #: the whole of the contract between the two enums. See the drift tests.
    CORRUPT = "corrupt"


@dataclass(frozen=True)
class StoreText:
    """One read attempt. Structurally `judge`'s `ResolvedText`; see the module docstring.

    THE REF IS ON EVERY OUTCOME, failures included, because a `MISSING` that
    does not say which ref is missing cannot be investigated.
    """

    ref: str
    outcome: ReadOutcome
    text: str | None = None

    def __post_init__(self) -> None:
        """Coerce the outcome BY VALUE, so identity is safe everywhere below.

        `ReadOutcome.MISSING == Outcome.MISSING` is True and `is` is False, so a
        member that crossed the boundary compares equal and fails every identity
        check. Engineer 2 found it, and both directions of the failure lean the
        wrong way silently: a FOUND payload reads as not-found, and a CORRUPT one
        reads as trustworthy.

        `ReadOutcome(...)` resolves by VALUE, so it accepts our own member, hers,
        or the bare string, and returns ours. Every `is` comparison in this file
        is downstream of this line, which is what makes them safe rather than
        lucky. Mirrors her `__post_init__` on `ResolvedText`.
        """
        object.__setattr__(self, "outcome", ReadOutcome(self.outcome))

    @property
    def found(self) -> bool:
        return self.outcome is ReadOutcome.FOUND

    def require(self) -> str:
        """The text, or a refusal naming the ref and which failure it was.

        For callers that cannot proceed. One that CAN — skipping a thread
        rather than failing a batch — should read `outcome`, because raising
        makes "skip this one" and "stop everything" the same code path.
        """
        if self.text is None:
            raise LookupError(
                f"{self.ref}: {self.outcome}. "
                + (
                    "The payload was deleted and its hash retained (NFR-6); "
                    "nothing is broken."
                    if self.outcome is ReadOutcome.TOMBSTONED
                    else "The store has no payload for this ref, which means "
                    "either the store lost it or the row was written against a "
                    "different store. Both need investigating."
                )
            )
        return self.text


class RawStoreReader:
    """A `RawTextResolver` over a `RawStore`. Reads, and does nothing else.

    Takes the store rather than a path, so a caller cannot point this at a
    different store than the one the rows were written against — which is one
    of the two things a `MISSING` outcome means, and the one worth making
    unreachable rather than reportable.

    No `put`, no `tombstone`, no `evict`, no list. Her Protocol asks for
    `resolve` and this offers `resolve`; the read-only property is structural
    rather than promised.
    """

    def __init__(self, store: RawStore) -> None:
        self._store = store

    def resolve(self, ref: str) -> StoreText:
        """`ref` to text, or to the outcome that says why not.

        The two `except` clauses are the whole substance of this file. See the
        module docstring for what a single one would cost.
        """
        try:
            text = self._store.get_text(ref)
        except UnicodeDecodeError:
            # PRESENT AND WRONG, which is the definition of CORRUPT. This used to
            # escape as an exception because three outcomes had nowhere to put it
            # — the argument for raising was never good, it was the best answer
            # available while the vocabulary was short. It is retired now.
            return StoreText(ref=ref, outcome=ReadOutcome.CORRUPT)
        except PayloadCorrupt:
            # Unreachable from a read today: the store raises this from `put()`
            # on a size mismatch, and nothing hashes on read. Mapped anyway, so
            # the day a verify sweep exists this needs no change — and so the
            # mapping is complete rather than complete-for-now.
            return StoreText(ref=ref, outcome=ReadOutcome.CORRUPT)
        except PayloadTombstoned:
            # Deliberate removal. Not a failure, and reporting it as one would
            # send somebody looking for a payload we deleted on purpose.
            return StoreText(ref=ref, outcome=ReadOutcome.TOMBSTONED)
        except PayloadMissing:
            # Absent with no tombstone. This one IS a failure.
            return StoreText(ref=ref, outcome=ReadOutcome.MISSING)
        return StoreText(ref=ref, outcome=ReadOutcome.FOUND, text=text)
