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

WHAT HAPPENS TO CORRUPTION, WHICH HAS NO OUTCOME
------------------------------------------------
`PayloadCorrupt` exists in the store and **cannot reach here**: it is raised by
`put()` on a size mismatch against an existing key, and this class only reads.
Checked rather than assumed, because the reverse would have been an argument for
adding a fourth outcome to a contract that does not need one.

What CAN happen on a read is bytes that are present and not valid UTF-8.
`get_text` decodes, so that surfaces as `UnicodeDecodeError`, and there is no
outcome for it: `MISSING` says the store has nothing, and the store has
something. **It propagates deliberately.** A caller crashing on a corrupt blob
is recoverable; a corrupt blob reported as `MISSING` sends somebody to look for
a payload that is sitting right there. This is the one place where raising
rather than returning is correct, and it is the case her `Outcome` deliberately
does not cover.

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

from collect.rawstore import PayloadMissing, PayloadTombstoned, RawStore


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


@dataclass(frozen=True)
class StoreText:
    """One read attempt. Structurally `judge`'s `ResolvedText`; see the module docstring.

    THE REF IS ON EVERY OUTCOME, failures included, because a `MISSING` that
    does not say which ref is missing cannot be investigated.
    """

    ref: str
    outcome: ReadOutcome
    text: str | None = None

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
        except PayloadTombstoned:
            # Deliberate removal. Not a failure, and reporting it as one would
            # send somebody looking for a payload we deleted on purpose.
            return StoreText(ref=ref, outcome=ReadOutcome.TOMBSTONED)
        except PayloadMissing:
            # Absent with no tombstone. This one IS a failure.
            return StoreText(ref=ref, outcome=ReadOutcome.MISSING)
        return StoreText(ref=ref, outcome=ReadOutcome.FOUND, text=text)
