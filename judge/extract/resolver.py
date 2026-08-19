"""What this lane needs in order to read text it does not store.

Option (a), taken 2026-08-19. `judge/` NAMES what it needs; whoever composes
the application provides something that satisfies it. The dependency runs the
right way - this file mentions no store, no path, no bucket and no `collect/`
symbol - and it is the same shape as `ExtractionClient`, which has worked for
the same reason since E5 was built.

WHY NOT THE OTHER TWO

(b) resolution inside `ThreadInput` would make the interface type carry a
strategy, which is the thing `text_ref` being a location was meant to avoid.
(c) `raw_text_of` doing the resolution breaks two contracts at once - the
tuple says `str` and would get bytes, and a reader that takes a `resolve`
argument is a reader that can be told where to read from, so get-only stops
being structural.

THREE OUTCOMES, RETURNED RATHER THAN RAISED ACROSS THE BOUNDARY

The store distinguishes found, tombstoned and missing, and collapsing any two
would be rule 6 at the one place both lanes read: a TOMBSTONE is a deletion we
honoured and a MISSING blob is a bug, and the repair for the first is nothing
while the repair for the second is urgent.

They come back as a value rather than an exception because **neither lane may
import the other** - the AST test asserts both directions - so an exception
type raised by one and caught by the other has nowhere to live that both can
see. A result object needs no shared type at all: the adapter that knows about
the store maps its exceptions onto this, and it is the only thing that needs
to know both vocabularies.

That adapter is NOT in this file and must not be. It belongs wherever the
shared reader lands, which is the one place allowed to know both.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


class Outcome(StrEnum):
    """What happened. Never collapsed to a boolean."""

    FOUND = "found"

    #: A deletion we honoured. NFR-6: the quotes vanish and the content hash
    #: remains. Nothing is broken and nothing needs repairing.
    TOMBSTONED = "tombstoned"

    #: The ref points at nothing. A bug, and the repair is UPSTREAM - either
    #: the store lost it or the row was written against a different store.
    MISSING = "missing"

    #: Something is there and it does not match its hash. E1's finding: the
    #: adapter's `except Exception` folded this into MISSING, so a blob that
    #: had been ALTERED and one that was never written came back identically.
    #:
    #: The distinction is not fussiness. MISSING says nothing is there and the
    #: repair is upstream; CORRUPT says something is there and WE CANNOT TRUST
    #: WHAT WE STORED. A batch can reasonably skip a missing payload and carry
    #: on; carrying on past a corrupt one writes claims sourced from a store
    #: that has just been shown to be unreliable.
    #:
    #: Returned rather than raised, like the others. A resolver that sometimes
    #: raises and sometimes returns is two contracts wearing one signature -
    #: E1's argument, and it is the same reason exceptions do not cross this
    #: boundary at all.
    CORRUPT = "corrupt"


@dataclass(frozen=True)
class ResolvedText:
    """One resolution attempt, carrying the ref whatever happened.

    THE REF IS ON EVERY OUTCOME, including the failures. A `MISSING` that does
    not say which ref sends whoever reads it back to the database to find out,
    and that is the moment they start guessing.
    """

    ref: str
    outcome: Outcome
    text: str | None = None

    def __post_init__(self) -> None:
        # NORMALISE A MIRRORED ENUM MEMBER TO OURS, and this is not defensive
        # habit - it is the specific hazard of a type duplicated across a lane
        # boundary that no compiler checks.
        #
        # `collect/rawstore_reader.py` defines `ReadOutcome` mirroring this,
        # deliberately, because neither lane may import the other. StrEnum
        # members of DIFFERENT classes compare equal by value and are never
        # identical:
        #
        #     ReadOutcome.MISSING == Outcome.MISSING   -> True
        #     ReadOutcome.MISSING is Outcome.MISSING   -> False
        #
        # Every comparison below and in `store_is_untrustworthy` uses `is`, so
        # a foreign member would make a FOUND payload read as not-found and a
        # CORRUPT one read as trustworthy - silently, and in the safe-looking
        # direction. Measured, not supposed.
        #
        # `Outcome(...)` resolves by VALUE, so it accepts our own member, the
        # mirrored one, and the bare string, and rejects anything else loudly.
        object.__setattr__(self, "outcome", Outcome(self.outcome))

        if self.outcome is Outcome.FOUND and self.text is None:
            raise ValueError(
                f"{self.ref}: FOUND with no text. A found payload that carries "
                f"nothing is the case a boolean would have hidden."
            )
        if self.outcome is not Outcome.FOUND and self.text is not None:
            raise ValueError(
                f"{self.ref}: {self.outcome} with text attached. A tombstoned "
                f"or missing payload has no text, and returning one anyway "
                f"would let a caller read past the outcome it was given."
            )

    @property
    def found(self) -> bool:
        return self.outcome is Outcome.FOUND

    @property
    def store_is_untrustworthy(self) -> bool:
        """CORRUPT only, and the reason it is not merged into `found is False`.

        A caller deciding what to do next needs three answers, not two:
        proceed, skip this thread, or STOP. Missing and tombstoned are both
        "skip this one" - the first is a bug to chase and the second is not,
        but neither says anything about the next payload. Corrupt does: the
        store returned bytes that fail their own hash, so nothing it returns
        afterwards has been shown to be trustworthy either.
        """
        return self.outcome is Outcome.CORRUPT

    def require(self) -> str:
        """The text, or a refusal naming the ref and which failure it was.

        For callers that genuinely cannot proceed. A caller that CAN proceed -
        one skipping a thread rather than failing a batch - should read
        `outcome` instead, because a raised exception makes "skip this one"
        and "stop everything" the same code path.
        """
        if self.text is None:
            raise LookupError(f"{self.ref}: {self.outcome}. " + _WHY[self.outcome])
        return self.text


#: What each failure means for whoever reads it, in the terms that decide what
#: they do next. Kept as a mapping rather than a chain of branches so a new
#: outcome cannot be added without a reader being written for it.
_WHY: dict[Outcome, str] = {
    Outcome.TOMBSTONED: (
        "The payload was deleted and its hash retained (NFR-6); nothing is "
        "broken and nothing needs repairing."
    ),
    Outcome.MISSING: (
        "The store has no payload for this ref, which means either the store "
        "lost it or the row was written against a different store. The repair "
        "is upstream."
    ),
    Outcome.CORRUPT: (
        "The payload is present and does not match its hash, so it has been "
        "altered since it was written. This is not a missing blob: something "
        "is there and cannot be trusted, and neither can anything else the "
        "store returns until that is understood."
    ),
}


@runtime_checkable
class RawTextResolver(Protocol):
    """Turn a `text_ref` or `flattened_text_ref` into text, or say why not.

    GET AND NOTHING ELSE. No write, no delete, no list, and no argument saying
    where to read from - a resolver that can be told where to look is one a
    caller can point at the wrong store, and read-only stops being structural.

    Deliberately not an ABC. A Protocol means the implementation does not
    import this file either, so neither lane depends on the other in either
    direction - which is what the AST test asserts and what a base class would
    quietly break.
    """

    def resolve(self, ref: str) -> ResolvedText: ...


class RefusingResolver:
    """The default, and it refuses rather than returning nothing.

    A `None` default would let a caller that forgot to wire a resolver run to
    completion having read no text, extract no claims, and report a clean batch
    - which is the failure this project has now found fourteen times. This
    fails at the first ref instead.
    """

    def resolve(self, ref: str) -> ResolvedText:
        raise LookupError(
            f"no resolver is wired, so {ref!r} cannot be read. This is a "
            f"missing dependency rather than a missing payload: the batch would "
            f"otherwise complete having read nothing and report success."
        )
