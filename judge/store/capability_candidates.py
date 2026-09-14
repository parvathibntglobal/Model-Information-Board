"""Persist capability-discovery proposals for a human to rule on.

The extractor PROPOSES a key; nothing here decides one. Rows land in
`capability_candidate`, which deliberately has no foreign key to `capability` —
adoption is a PR against `contract/capabilities.yaml`, not an INSERT (see the
table comment). This module only accumulates the evidence.

IDEMPOTENT, and that is the count's integrity. `id` is the content hash of the
natural key (document, proposed_key, prompt_label, pipeline_version), written
`ON CONFLICT DO NOTHING`, so re-running the extractor over the same corpus
cannot double the number the review page reads. The count is still a FLOOR —
free-text keys fragment one capability across phrasings — so any figure shown
from it reads ">= N" until clustering lands (see the table comment).

⚠ THE FRAGMENTATION NOW HAS NUMBERS, AND THEY ARE LARGER THAN THE WORD
  "floor" SUGGESTS. Measured 2026-09-11 on the withheld-keys discovery run
  (774 Reddit documents): **528 distinct proposed keys from 552 proposals** —
  1.045 proposals per key, 20 keys used more than once — against the twelve
  in `contract/capabilities.yaml`. 20.5% of proposals share a final segment
  with a differently-prefixed key, and **15.4% name a MODEL inside the key**
  (`claude_haiku.instruction_following`, `gpt_5_2.response_time`), which is
  not a clustering problem at all: a key naming a model has folded the subject
  into the axis and has to be rejected or rewritten, not merged.

  READ BEFORE SIZING THE REVIEW QUEUE. The row count is not the candidate
  count, and the work is merging rather than ruling.
  `docs/capability-key-normalisation-2026-09-11.md`.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from judge.store.claims import PIPELINE_VERSION

if TYPE_CHECKING:
    from judge.extract.runner import ProposedCapability


def candidate_id(
    *, document_id: str, proposed_key: str, prompt_label: str, pipeline_version: str
) -> str:
    """Content hash of the natural key, so a re-run produces the same id."""
    digest = hashlib.sha256(
        "\x1f".join([document_id, proposed_key, prompt_label, pipeline_version]).encode("utf-8")
    ).hexdigest()
    return f"cc_{digest[:24]}"


def store_proposals(
    conn: Any,
    proposals: list[ProposedCapability],
    *,
    proposer_model: str,
    prompt_label: str,
    pipeline_version: str = PIPELINE_VERSION,
) -> dict[str, int]:
    """Append the attributable proposals. Returns {proposed, stored, unattributed}.

    A proposal whose quote did not resolve to a document is NOT stored —
    `capability_candidate.document_id` is NOT NULL and a proposal with no
    document behind it is an opinion — but it IS counted, so an unattributed
    proposal is visible rather than silently gone.
    """
    proposed = len(proposals)
    unattributed = sum(1 for p in proposals if p.document_id is None)
    stored = 0
    with conn.cursor() as cur:
        for p in proposals:
            if p.document_id is None:
                continue
            cur.execute(
                "INSERT INTO capability_candidate "
                "(id, proposed_key, definition, document_id, quote, quote_verified,"
                " proposer_model, prompt_label, pipeline_version) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING",
                (
                    candidate_id(
                        document_id=p.document_id, proposed_key=p.proposed_key,
                        prompt_label=prompt_label, pipeline_version=pipeline_version,
                    ),
                    p.proposed_key, p.definition, p.document_id, p.quote, p.quote_verified,
                    proposer_model, prompt_label, pipeline_version,
                ),
            )
            stored += cur.rowcount  # 1 on insert, 0 on conflict
    return {"proposed": proposed, "stored": stored, "unattributed": unattributed}


# ── the admin review surface ────────────────────────────────────────────────
#
# An admin rules on the VOCABULARY, so these operate on a proposed_key (all its
# rows) rather than a single row: adopting "output.verbosity" is one decision
# about a word, not nine about nine quotes. The count of documents that proposed
# it is the evidence, so it is shown; it is a FLOOR (free-text keys fragment) and
# labelled so wherever it is read.

RULINGS = ("adopted", "declined", "merged")


def list_candidates(conn: Any) -> list[dict]:
    """Proposals grouped by key, newest evidence first, for the review page.

    One group per `proposed_key`: how many documents proposed it (the floor
    count), the distinct definitions offered, a few example quotes with their
    document, and the ruling if one has been made.
    """
    rows = conn.execute(
        "SELECT id, proposed_key, definition, document_id, quote, quote_verified, "
        "proposer_model, created_at, reviewed_at, ruling, ruling_target "
        "FROM capability_candidate ORDER BY created_at DESC"
    ).fetchall()

    groups: dict[str, dict] = {}
    for row in rows:
        (id_, key, defn, doc, quote, verified, model, created,
         reviewed, ruling, target) = row
        g = groups.setdefault(key, {
            "proposed_key": key, "count": 0, "verified": 0,
            "definitions": [], "examples": [], "proposer_models": set(),
            "ruling": ruling, "ruling_target": target, "reviewed_at": reviewed,
        })
        g["count"] += 1
        g["verified"] += 1 if verified else 0
        g["proposer_models"].add(model)
        if defn not in g["definitions"]:
            g["definitions"].append(defn)
        if len(g["examples"]) < 5:
            g["examples"].append({
                "id": id_, "quote": quote, "document_id": doc,
                "quote_verified": verified,
            })
        # A ruling on any row is the group's ruling (they are ruled together).
        if ruling is not None:
            g["ruling"], g["ruling_target"], g["reviewed_at"] = ruling, target, reviewed

    out = []
    for g in groups.values():
        g["proposer_models"] = sorted(g["proposer_models"])
        g["count_is_a_floor"] = (
            "distinct proposed_key strings; near-duplicate phrasings are not yet "
            "clustered, so this under-counts a capability proposed several ways"
        )
        out.append(g)
    # Unruled first (they need attention), then by evidence count.
    out.sort(key=lambda g: (g["ruling"] is not None, -g["count"]))
    return out


def rule_candidates(
    conn: Any, *, proposed_key: str, ruling: str, ruling_target: str | None
) -> int:
    """Adopt / decline / merge every row for one proposed key. Returns rows ruled.

    Adoption is recorded here; the vocabulary itself changes in a
    `contract/capabilities.yaml` PR, not by this write (the table has no FK to
    `capability` precisely so a ruling cannot grow the vocabulary sideways).
    """
    if ruling not in RULINGS:
        raise ValueError(f"ruling must be one of {RULINGS}, not {ruling!r}")
    # The table's CHECK constraints: adopted/merged require a target, declined
    # forbids one; a ruling and its date travel together.
    if ruling in ("adopted", "merged") and not ruling_target:
        raise ValueError(f"{ruling} requires a ruling_target (what it became)")
    target = ruling_target if ruling in ("adopted", "merged") else None
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE capability_candidate SET ruling = %s, ruling_target = %s, "
            "reviewed_at = now() WHERE proposed_key = %s",
            (ruling, target, proposed_key),
        )
        return cur.rowcount


def edit_candidates(
    conn: Any, *, proposed_key: str, new_key: str | None = None,
    new_definition: str | None = None,
) -> int:
    """Fix a proposed key's name and/or definition across all its rows."""
    sets, params = [], []
    if new_key:
        sets.append("proposed_key = %s")
        params.append(new_key)
    if new_definition is not None:
        sets.append("definition = %s")
        params.append(new_definition)
    if not sets:
        return 0
    params.append(proposed_key)
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE capability_candidate SET {', '.join(sets)} WHERE proposed_key = %s",
            params,
        )
        return cur.rowcount


def delete_candidates(conn: Any, *, proposed_key: str) -> int:
    """Remove every row for a proposed key — for a proposal that is noise.

    A hard delete, because an admin declaring a proposal spurious is different
    from declining a real one; `ruling = 'declined'` keeps the evidence, this
    discards it. The caller chooses which the proposal deserves.
    """
    with conn.cursor() as cur:
        cur.execute("DELETE FROM capability_candidate WHERE proposed_key = %s", (proposed_key,))
        return cur.rowcount
