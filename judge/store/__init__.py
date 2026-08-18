"""Where `judge/` writes. The first rows this lane has ever produced.

Everything upstream of here has run in memory and forgotten itself. That is
affordable for verification, which is pure, and unaffordable for extraction,
which is paid: without a write path every night pays again for the claims the
previous night already extracted.

It is also why consensus cannot exist yet. "Six engineers said this" is six
claims gathered over weeks, and nothing counts to six from a standing start.

WHAT THIS LANE MAY WRITE

`claim`, `claim_weight`, `cell`, and nothing else. `document` and
`thread_context` are the interface and belong to `collect/` — this lane reads
them and never writes them, which is the one-directional rule that lets two
people work without coordinating.

It also never imports from `collect/`, so the connection handling here is
deliberately its own rather than shared with `collect/db.py`. Slight
duplication, in exchange for a boundary that cannot erode by accident.
"""

from judge.store.claims import (
    ClaimStore,
    StoredClaim,
    claim_id_for,
)

__all__ = ["ClaimStore", "StoredClaim", "claim_id_for"]
