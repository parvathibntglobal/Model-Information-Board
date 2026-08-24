"""E3 — clustering near-duplicates. FR-16.

**Deduplicate before anything is counted; syndicated copies contribute to REACH,
never to WEIGHT.** One blog syndicated four times and quoted twice is one person;
counted naively it looks like six-source consensus, and the publication gate
would pass on one voice.

THREE MECHANISMS, IN DESCENDING ORDER OF CERTAINTY
--------------------------------------------------
    1  crosspost      the platform declaring one document a copy of another.
                      Certain, and free.
    2  exact match    identical normalised signature text. Certain, EXCEPT for
                      the sentinel trap below.
    3  MinHash + LSH  similarity above the contract threshold, for documents at
                      or above the token floor. The only inferential one.

Ordered because a certainty should never be overridden by an inference, and
because 1 and 2 work on documents too short for 3 — which is most comments.

THE SENTINEL TRAP, AND IT IS REAL RATHER THAN HYPOTHETICAL
-----------------------------------------------------------
In one 14-thread Reddit corpus, `[removed]` appears as the body of **57 distinct
comments** and `[deleted]` of **38**. Exact-match merging on text would collapse
each set into a single document, destroying the tree those comments sit in and
the voice counts drawn from it.

So identical text is NOT identity. `signature.is_sentinel` names those bodies and
they are never merged with anything, by any mechanism.

UNDER-MERGING IS THE SAFE DIRECTION AND THIS CODE LEANS THAT WAY
----------------------------------------------------------------
`collect/CLAUDE.md`: "Over-clustering is worse than under-clustering. Merging two
genuinely independent reports destroys corroboration, which is the only thing
separating 'someone said this' from 'this is probably true'."

So: a high similarity threshold, a high token floor, sentinels excluded, and
`unresolved` documents left as singletons rather than guessed at. The cost is a
voice count that is an upper bound, which is stated in §20 of the architecture doc
and is the direction the gate can survive.

REACH IS NOT WEIGHT, AND NOTHING HERE COMPUTES A WEIGHT
--------------------------------------------------------
`dedup_cluster.reach` counts the copies. `claim_weight.f_*` never reads it. A
syndicated post reaching four subreddits is more READ and no better evidenced,
and the schema comment on `dedup_cluster.reach` says so — "amplifications
contribute to REACH, never to WEIGHT". A test asserts nothing in this module
exposes an attribute a weighting pass would pick up.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from collect.assemble.signature import (
    Signature,
    is_sentinel,
    min_tokens_for_signature,
    signature_of,
    signature_text,
    similarity_threshold,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DedupeInput:
    """What clustering needs from a document. Deliberately not the ORM row.

    `created_at` may be None — Reddit gives an epoch and blogs sometimes give
    nothing — and canonical selection has to cope rather than assume.
    """

    external_id: str
    text: str
    created_at: datetime | None = None
    #: The platform's own declaration, where it makes one. `crosspost_parent`.
    declared_copy_of: str | None = None


@dataclass
class Cluster:
    """One set of documents judged to be the same content.

    `canonical_id` is the EARLIEST original. The rest are amplifications.
    """

    canonical_id: str
    member_ids: list[str] = field(default_factory=list)
    #: How each member joined. A cluster formed by a platform declaration and one
    #: formed by a 0.93 Jaccard are different kinds of claim, and an audit six
    #: months later cannot tell them apart from a size alone.
    joined_by: dict[str, str] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.member_ids)

    @property
    def reach(self) -> int:
        """Copies beyond the canonical. Contributes to reach, never to weight."""
        return max(0, self.size - 1)

    @property
    def is_singleton(self) -> bool:
        return self.size == 1

    def as_row(self) -> dict[str, Any]:
        """`dedup_cluster`'s shape. No weight, no score, no confidence."""
        return {
            "canonical_document_id": self.canonical_id,
            "size": self.size,
            "reach": self.reach,
        }


@dataclass(frozen=True)
class DedupeResult:
    clusters: tuple[Cluster, ...]
    signatures: dict[str, Signature]
    min_tokens: int
    threshold: float

    @property
    def merged_clusters(self) -> tuple[Cluster, ...]:
        return tuple(c for c in self.clusters if not c.is_singleton)

    @property
    def documents(self) -> int:
        return sum(c.size for c in self.clusters)

    def cluster_of(self, external_id: str) -> Cluster | None:
        for cluster in self.clusters:
            if external_id in cluster.member_ids:
                return cluster
        return None

    def describe(self) -> str:
        merged = self.merged_clusters
        comparable = sum(1 for s in self.signatures.values() if s.comparable)
        reasons: dict[str, int] = {}
        for s in self.signatures.values():
            if not s.comparable:
                reasons[s.reason or "unknown"] = reasons.get(s.reason or "unknown", 0) + 1
        return (
            f"{self.documents} documents, {len(self.clusters)} clusters, "
            f"{len(merged)} with more than one member; "
            f"{comparable} had a signature, "
            f"{dict(sorted(reasons.items()))} did not"
        )


class _Union:
    """Union-find. Merging is transitive and the order documents arrive is not."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, key: str) -> None:
        self.parent.setdefault(key, key)

    def find(self, key: str) -> str:
        root = key
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[key] != root:
            self.parent[key], key = root, self.parent[key]
        return root

    def union(self, a: str, b: str) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        self.parent[rb] = ra
        return True


def cluster(documents, *, min_tokens: int | None = None,
            threshold: float | None = None) -> DedupeResult:
    """Cluster documents by the three mechanisms. Nothing is deleted.

    Every input appears in exactly one output cluster, including singletons and
    sentinels — this reports a grouping, it does not filter. Deletion is FR-16's
    consumer's business and NFR-6's tombstone path, not clustering's.
    """
    from datasketch import MinHashLSH

    docs = list(documents)
    min_tokens = min_tokens_for_signature() if min_tokens is None else min_tokens
    threshold = similarity_threshold() if threshold is None else threshold

    by_id = {d.external_id: d for d in docs}
    signatures = {
        d.external_id: signature_of(d.external_id, d.text, min_tokens=min_tokens)
        for d in docs
    }
    union = _Union()
    for d in docs:
        union.add(d.external_id)

    # EDGES, NOT A PER-MEMBER LABEL WRITTEN AT MERGE TIME. Recording the reason
    # only when `union` returns True loses it whenever the pair is ALREADY
    # connected by another path — merging is transitive and the arrival order is
    # not. A first version did that and left 26 of 172 absorbed documents labelled
    # "unknown" on the real corpus: an audit trail with holes in exactly the
    # cases that had the most evidence.
    edges: list[tuple[str, str, str]] = []

    # ── 1. platform declarations ─────────────────────────────────────────
    for d in docs:
        parent = d.declared_copy_of
        declared = parent and parent in by_id and not is_sentinel(d.text)
        if declared:
            union.union(parent, d.external_id)
            edges.append((parent, d.external_id, "crosspost"))

    # ── 2. exact normalised match, sentinels excluded ────────────────────
    by_text: dict[str, list[str]] = {}
    for d in docs:
        if is_sentinel(d.text):
            continue
        key = signature_text(d.text).strip()
        if key:
            by_text.setdefault(key, []).append(d.external_id)
    for group in by_text.values():
        first = group[0]
        for other in group[1:]:
            union.union(first, other)
            edges.append((first, other, "exact"))

    # ── 3. MinHash LSH, above the floor only ─────────────────────────────
    comparable = [s for s in signatures.values() if s.comparable]
    if comparable:
        lsh = MinHashLSH(threshold=threshold, num_perm=len(comparable[0].minhash))
        for sig in comparable:
            lsh.insert(sig.external_id, sig.minhash)
        for sig in comparable:
            for other_id in lsh.query(sig.minhash):
                if other_id == sig.external_id:
                    continue
                # LSH is approximate; confirm the estimate before merging, because
                # over-merging is the expensive direction.
                estimate = sig.minhash.jaccard(signatures[other_id].minhash)
                if estimate >= threshold:
                    union.union(sig.external_id, other_id)
                    edges.append((sig.external_id, other_id, f"minhash:{estimate:.2f}"))

    # ── canonical: the earliest original ─────────────────────────────────
    groups: dict[str, list[str]] = {}
    for d in docs:
        groups.setdefault(union.find(d.external_id), []).append(d.external_id)

    # Certainty order, so a member linked by both a declaration and a similarity
    # estimate is recorded as declared. `_RANK` is the order of the three
    # mechanisms in the module docstring.
    _RANK = {"crosspost": 0, "exact": 1}
    reason_for: dict[str, str] = {}
    for a, b, mechanism in edges:
        for node in (a, b):
            current = reason_for.get(node)
            rank = _RANK.get(mechanism.split(":")[0], 2)
            if current is None or rank < _RANK.get(current.split(":")[0], 2):
                reason_for[node] = mechanism

    clusters = []
    for members in groups.values():
        # A document with no timestamp cannot be shown to be earliest, so it does
        # not win the tie. Sorting None last, then by id, keeps this deterministic
        # without inventing an order (rule 6).
        ordered = sorted(
            members,
            key=lambda i: (by_id[i].created_at is None,
                           by_id[i].created_at or datetime.max.replace(tzinfo=None),
                           i),
        )
        canonical = ordered[0]
        clusters.append(Cluster(
            canonical_id=canonical,
            member_ids=ordered,
            joined_by={
                m: "canonical" if m == canonical else reason_for[m]
                for m in ordered
            },
        ))

    clusters.sort(key=lambda c: (-c.size, c.canonical_id))
    return DedupeResult(tuple(clusters), signatures, min_tokens, threshold)
