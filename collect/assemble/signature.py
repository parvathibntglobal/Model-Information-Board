"""E3 — near-duplicate signatures. One method, and a floor below which none works.

MEASURED BEFORE PICKING, over 79 ground-truth duplicate pairs and 951 stranger
pairs drawn from 3,767 Reddit documents. Full curve in
`docs/measurements/dedupe-threshold.md`.

    MinHash, Jaccard over 5-char shingles, 128 permutations
      tokens      true pairs (min/med/max)   strangers (min/med/max)   separated
      0-50        0.04 / 0.30 / 1.00         0.00 / 0.00 / 0.13        NO
      50-100      0.95 / 1.00 / 1.00         0.05 / 0.05 / 0.05        yes  n=2
      100-200     0.41 / 1.00 / 1.00         0.02 / 0.05 / 0.10        yes  n=4
      200-400     0.93 / 1.00 / 1.00         0.02 / 0.05 / 0.12        YES
      400-800     0.62 / 0.98 / 1.00         0.00 / 0.07 / 0.16        YES
      800+        0.77 / 0.99 / 1.00         0.01 / 0.09 / 0.24        YES

WHAT THE MEASUREMENT CHANGED, AND IT IS A DESIGN CHANGE
-------------------------------------------------------
`collect/CLAUDE.md` specified MinHash below ~200 tokens and simhash above, on the
reasoning that simhash is built for long documents. **The data does not support
the split.** MinHash separates better at every length INCLUDING the long bands
where simhash was to be used, and simhash's margin in 400-800 tokens is **one bit
out of 64** — true pairs up to 18, strangers from 19.

That is not an artefact of giving simhash character shingles to make the
comparison fair. Re-run in its conventional form — word 3-grams, tf-weighted —
its margins were 0 to 12 bits, still narrow, and still worse than MinHash's 0.46
on a 0-to-1 scale in the same band.

So there is ONE method here, not two. `simhash` is absent rather than
unimplemented, and the schema's `document.simhash bigint` column stays NULL —
which is a fact about what was measured, not a gap. Flagged for
`collect/CLAUDE.md` and for `docs/logic-and-workflow.md`, which says the same
thing.

THE 200 SURVIVED AND ITS MEANING CHANGED
-----------------------------------------
`min_tokens_for_signature: 200` is not the old threshold with new evidence. The
old 200 switched between two methods. This 200 is a FLOOR: below it, no signature
is computed at all, because neither method separates duplicates from strangers.

The band the data supports is **(50, 200)** — failure is demonstrated below 50,
success is demonstrated at 200, and the two bands between carry n=2 and n=4,
which is too thin to claim either way. Every value in that band is consistent
with the evidence, so the choice inside it is judgement:

  `collect/CLAUDE.md`: "Over-clustering is worse than under-clustering, which
  destroys corroboration - the only thing separating 'someone said this' from
  'this is probably true'."

A HIGHER floor merges fewer documents, so the conservative end is the high end,
and the lane's own rule says which direction conservative is. 200 is the top of
the band.

WHAT HAPPENS BELOW THE FLOOR
----------------------------
Exact normalised match, and platform-declared crossposts. Both are certainties
rather than similarities. `dedupe.py` handles that, and the one trap in it:
`[removed]` appears 57 times and `[deleted]` 38 times in one corpus as identical
bodies of DISTINCT comments, so exact-match merging has to exclude the sentinels
or it collapses a thread.

BLOCKQUOTES ONLY, AND FROM THE SIEVE'S PATTERN
-----------------------------------------------
`collect/CLAUDE.md` requires blockquoted spans excluded from the signature so
commentary about a post is not merged into it. Code is NOT excluded: a pasted
traceback is content that distinguishes documents rather than borrowed words that
conflate them.

The pattern comes from `sieve.strip_container(text, "blockquote")` rather than a
local regex. That is the third consumer of one definition — `author_prose` for
the sieve, `triage.specificity.has_code` for their presence, this for one member
— and `tests/test_dedupe.py` pins it so a fourth definition never appears.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from collect.adapters.queries.sieve import normalize, strip_container

#: Character shingle width. 5 is what the curve above was measured at; a
#: different width is a different measurement, not a tuning knob.
SHINGLE_CHARS = 5

#: MinHash permutations. 128 gives a Jaccard standard error near 0.09, which is
#: comfortably inside the 0.46 margin measured in the tightest passing band.
PERMUTATIONS = 128

#: Bodies Reddit substitutes for a comment that is gone. Identical text, distinct
#: comments — see the module docstring.
SENTINEL_BODIES = frozenset({"[deleted]", "[removed]", "[unavailable]"})

_WORD = re.compile(r"\S+")


def signature_text(text: str) -> str:
    """What the signature is computed over. Blockquotes out, everything else in."""
    return normalize(strip_container(text, "blockquote"))


def token_count(text: str) -> int:
    """Whitespace tokens of the signature text. The floor is measured in these."""
    return len(_WORD.findall(signature_text(text)))


def shingles(text: str, width: int = SHINGLE_CHARS) -> set[str]:
    """Character shingles of the signature text.

    Character rather than word shingles because that is what the curve was
    measured on, and because they survive the edits syndication actually makes —
    a changed sentence breaks every word shingle spanning it and only the
    character shingles inside it.
    """
    prepared = signature_text(text)
    if len(prepared) <= width:
        return {prepared} if prepared else set()
    return {prepared[i:i + width] for i in range(len(prepared) - width + 1)}


def minhash_of(text: str, *, permutations: int = PERMUTATIONS):
    """A MinHash over the shingles, or None for text with no shingles.

    None rather than an empty MinHash: an empty signature compares as identical
    to every other empty signature, which would merge every blank document into
    one cluster. Absent stays absent (rule 6).
    """
    from datasketch import MinHash

    grams = shingles(text)
    if not grams:
        return None
    sketch = MinHash(num_perm=permutations)
    for gram in grams:
        sketch.update(gram.encode("utf-8"))
    return sketch


def is_sentinel(text: str) -> bool:
    """A deleted or removed body. Identical text, and NOT the same document."""
    return signature_text(text).strip() in SENTINEL_BODIES


@dataclass(frozen=True)
class Signature:
    """One document's signature, and whether it has one at all."""

    external_id: str
    tokens: int
    #: None when the document is below the floor, empty, or a sentinel body. Three
    #: different reasons, and `reason` says which — a bare None would make "too
    #: short to compare" indistinguishable from "nothing to compare".
    minhash: Any | None
    reason: str | None = None

    @property
    def comparable(self) -> bool:
        return self.minhash is not None


def signature_of(external_id: str, text: str, *, min_tokens: int) -> Signature:
    """One document to one signature, with the reason when there is none."""
    tokens = token_count(text)
    if is_sentinel(text):
        return Signature(external_id, tokens, None, "sentinel-body")
    if not signature_text(text).strip():
        return Signature(external_id, tokens, None, "empty")
    if tokens < min_tokens:
        return Signature(external_id, tokens, None, "below-floor")
    return Signature(external_id, tokens, minhash_of(text), None)


@lru_cache(maxsize=1)
def _contract() -> dict:
    """`contract/harvest.yaml:dedupe`. Raises rather than defaulting (rule 5)."""
    import yaml

    from collect.config import CONTRACT_DIR

    path = CONTRACT_DIR / "harvest.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    block = raw.get("dedupe")
    if not block:
        raise DedupeContractError(
            "contract/harvest.yaml has no `dedupe` block. There is no built-in "
            "default: a second source of truth for a clustering threshold renders "
            "identically to the real one and diverges silently."
        )
    return block


class DedupeContractError(RuntimeError):
    """The contract is missing configuration this module refuses to default."""


def min_tokens_for_signature() -> int:
    value = _contract().get("min_tokens_for_signature")
    if value is None:
        raise DedupeContractError("`dedupe.min_tokens_for_signature` is missing")
    return int(value)


def similarity_threshold() -> float:
    value = _contract().get("similarity_threshold")
    if value is None:
        raise DedupeContractError("`dedupe.similarity_threshold` is missing")
    return float(value)
