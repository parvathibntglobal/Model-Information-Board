"""E3 — run the clustering and persist it. The writer `dedupe.py` never had.

WHAT WAS MISSING, AND IT WAS ONLY THE WRITER. `collect/assemble/dedupe.py`
(clustering, three mechanisms, sentinel trap) and `collect/assemble/signature.py`
(MinHash, blockquotes excluded, the measured 200-token floor) are both complete
and both correct. Nothing called them. `collect/ops/chain.py` declares
`Stage("assemble-dedupe", run=None)`, and `contract/column_states.yaml` says
`known_gap: E1's lane - dedupe is unwired` against the very columns this fills.

Measured on staging before this existed: `dedup_cluster_id`,
`is_canonical_in_cluster`, `minhash` and `simhash` were populated on **0 of
7,479** documents.

WHY THAT MATTERS MORE THAN AN EMPTY COLUMN. `judge/vet/reject.py:check` already
TAKES `dedup_cluster_id` and `is_canonical_in_cluster`, defaulting to "not
clustered, is canonical". With nothing written, every syndicated copy of one
post is canonical, so one blog quoted on Reddit and linked from a GitHub issue
counts as three voices — which is exactly the condition the publication gate
exists to test, inverted. The consumer was starved, not absent.

THE SIGNATURE IS COMPUTED OVER PROSE, NEVER OVER THE STORED PAYLOAD. This is
the same mistake that cost the board its quotes on 2026-09-10: a raw JSON
envelope shingled character-wise would cluster on `{"author":"…","children":`,
which every document from a platform shares. Every text here goes through
`collect/assemble/prose.py` first, and a source with no extractor is REFUSED
rather than signed raw.

WHAT IT CANNOT SEE, STATED RATHER THAN HIDDEN. A document whose payload is not
in this machine's store cannot be read, so it cannot be signed, so it stays a
singleton. Clustering is therefore partial and biased toward UNDER-merging,
which is the direction `dedupe.py` already argues for: "over-clustering is worse
than under-clustering. Merging two genuinely independent reports destroys
corroboration." The report says how many were unreadable rather than implying
they were checked.

`minhash` AND `simhash` STAY NULL, AND BOTH FOR REASONS.
  simhash  measured and dropped - `signature.py` found MinHash separates better
           at EVERY length, including the long bands simhash was meant for, and
           its margin there is one bit in 64. "absent rather than
           unimplemented".
  minhash  this pass re-reads text and clusters in memory, so it never needs a
           stored signature. Persisting one is for INCREMENTAL matching - a new
           document against old signatures without re-reading the corpus - which
           this does not do. Writing it now would store a value nothing reads.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from collect.assemble.dedupe import DedupeInput, cluster
from collect.ids import stable_id

log = logging.getLogger(__name__)


@dataclass
class DedupeWriteReport:
    """What a run saw and what it changed. Counts, never a score."""

    source: str
    considered: int = 0
    #: Payload not in this machine's store, so no signature could be computed.
    unreadable: int = 0
    #: Source has no prose extractor. Refused rather than signed raw.
    refused: int = 0
    signed: int = 0
    clusters_written: int = 0
    documents_marked: int = 0
    amplifications: int = 0
    notes: list[str] = field(default_factory=list)

    def describe(self) -> str:
        return (
            f"{self.source}: {self.considered} considered, {self.signed} signed, "
            f"{self.clusters_written} multi-member cluster(s), "
            f"{self.amplifications} amplification(s); "
            f"{self.unreadable} unreadable, {self.refused} refused"
        )


#: `dedup_cluster.id`. Derived from the CANONICAL document so a re-run over the
#: same corpus reuses the row rather than minting a second one for the same
#: grouping. Membership can grow; the identity of the grouping is its original.
def cluster_id_for(canonical_document_id: str) -> str:
    return stable_id("dedup_cluster", canonical_document_id)


def _texts(
    conn, source: str, *, store, limit: int | None
) -> tuple[dict[str, str], dict[str, Any], DedupeWriteReport]:
    """Document id -> prose. Unreadable and unmapped sources are counted, not guessed."""
    from collect.assemble import prose
    from collect.rawstore_reader import RawStoreReader

    report = DedupeWriteReport(source=source)
    reader = RawStoreReader(store)
    extract = prose.for_source(source)

    # ── A MISSING PAYLOAD IS EXPECTED HERE, AND ONLY HERE ────────────────────
    #
    # `rawstore` logs a missing ref at ERROR with NFR-4 in the text, because on
    # a single machine a missing payload IS corruption - the store is the only
    # copy and rebuild-from-raw is void without it. That reasoning is right and
    # the message stays.
    #
    # It stops being right for THIS pass. The database is shared and the raw
    # store is not: 5,210 of 7,479 documents were harvested on somebody else's
    # machine, so their payloads are legitimately absent here. Rehearsed
    # against staging, this pass produced 815 NFR-4 errors in 15 seconds and
    # would have buried the fetch log under them.
    #
    # So the CALLER declares that it expects misses, rather than the store
    # being taught to doubt itself. They are not swallowed: every one is
    # counted into `report.unreadable` and reported on the stage line, which is
    # what stops "0 clusters" reading as "nothing was duplicated" when it means
    # "most of the corpus was not on this disk".
    store_log = logging.getLogger("collect.rawstore")
    previous = store_log.level
    store_log.setLevel(logging.CRITICAL)
    try:
        return _read_texts(conn, source, reader, extract, report, limit)
    finally:
        store_log.setLevel(previous)


def _read_texts(conn, source, reader, extract, report, limit):
    """The read itself. Split out so the log level is restored on every path."""

    rows = conn.execute(
        "SELECT id, text_ref, created_at FROM document "
        "WHERE source = %s AND text_ref IS NOT NULL "
        "ORDER BY created_at NULLS LAST" + (" LIMIT %s" if limit else ""),
        (source, limit) if limit else (source,),
    ).fetchall()
    report.considered = len(rows)

    if extract is None:
        report.refused = len(rows)
        report.notes.append(
            f"no prose extractor is mapped for {source!r}; refused rather than "
            "signing the stored payload, which would cluster on its envelope"
        )
        return {}, {}, report

    texts: dict[str, str] = {}
    created: dict[str, Any] = {}
    for doc_id, ref, created_at in rows:
        outcome = reader.resolve(ref)
        if outcome is None or not outcome.found:
            report.unreadable += 1
            continue
        try:
            texts[doc_id] = extract(outcome.require())
            created[doc_id] = created_at
        except Exception:
            # A payload the extractor cannot read is not a duplicate of
            # anything; it is a document we could not sign.
            report.refused += 1
    report.signed = len(texts)
    return texts, created, report


def run_for_source(conn, *, source: str, store, limit: int | None = None) -> DedupeWriteReport:
    """Cluster one source's documents and persist the grouping.

    APPEND AND MARK, NEVER DELETE. A duplicate keeps its row, its payload and
    its author; what changes is that it is recorded as an amplification of an
    earlier document rather than as an independent voice. `dedupe.py`: "nothing
    is deleted ... this reports a grouping, it does not filter".
    """
    texts, created, report = _texts(conn, source, store=store, limit=limit)
    if len(texts) < 2:
        report.notes.append("fewer than two signable documents; nothing to compare")
        return report

    result = cluster(
        DedupeInput(external_id=doc_id, text=text, created_at=created.get(doc_id))
        for doc_id, text in texts.items()
    )
    log.info("dedupe %s: %s", source, result.describe())
    report.notes.append(result.describe())

    for group in result.clusters:
        if group.is_singleton:
            continue
        cid = cluster_id_for(group.canonical_id)
        conn.execute(
            "INSERT INTO dedup_cluster (id, canonical_document_id, size, reach) "
            "VALUES (%s, %s, %s, %s) "
            # The grouping can GROW as more of the corpus becomes readable, so a
            # re-run updates the counts. The canonical does not move: it is the
            # earliest original and the id is derived from it.
            "ON CONFLICT (id) DO UPDATE SET size = EXCLUDED.size, reach = EXCLUDED.reach",
            (cid, group.canonical_id, group.size, group.reach),
        )
        report.clusters_written += 1
        for member in group.member_ids:
            conn.execute(
                "UPDATE document SET dedup_cluster_id = %s, is_canonical_in_cluster = %s "
                "WHERE id = %s",
                (cid, member == group.canonical_id, member),
            )
            report.documents_marked += 1
            if member != group.canonical_id:
                report.amplifications += 1
    return report


def run(conn, *, store, sources, limit: int | None = None) -> list[DedupeWriteReport]:
    """Every source in turn. One report each, so a silent source is visible."""
    return [run_for_source(conn, source=s, store=store, limit=limit) for s in sources]
