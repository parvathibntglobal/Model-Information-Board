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
