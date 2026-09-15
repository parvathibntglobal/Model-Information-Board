"""The registry as a list, with what the provider advertises about each model.

WHY THIS IS SEPARATE FROM EVERY OTHER PAGE IN THIS PACKAGE.

Nothing here is evidence. Price, context window and feature flags are what a
vendor publishes about itself. They pass through no gate, they have no voices
behind them, and no amount of them makes a model recommendable. A capability
page answers "what have people found out"; this answers "what is on the tin",
and the two must never be shown as though they were the same kind of claim.

It exists because the board had no way to list models at all - `/models/{id}`
answers about one model you already know the id of, so the frontend was
reconstructing the roster from a capability page and taking twelve round trips
to do it.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# Ordered by display_name rather than by price. A default sort by cost would
# be this module quietly making the recommendation the rest of the system
# refuses to make without evidence.
SQL = """
    SELECT mv.id,
           mv.display_name,
           mv.provider,
           mv.canonical_id,
           mv.price_in,
           mv.price_out,
           mv.price_cached_read,
           mv.advertised_context,
           mv.max_output_tokens,
           mv.supports_tools,
           mv.supports_vision,
           mv.supports_structured_output,
           mv.supports_caching,
           mv.lifecycle,
           -- E7 STATE, JOINED HERE RATHER THAN COUNTED IN THE CLIENT.
           --
           -- The frontend used to learn this by folding twelve capability
           -- pages together: 12 requests, 656 KB and 26 SECONDS against
           -- staging, during which a filter built on it gives confidently
           -- wrong answers - a model whose only cell sits under the ninth
           -- capability reads as unreported until the ninth page lands. And a
           -- capability page that FAILS makes it wrong permanently, with no
           -- way for a filter to be half-right about a row.
           --
           -- This is one join. 360ms, and correct the moment it returns.
           (SELECT count(*) FROM cell c
             WHERE c.model_version_id = mv.id)                      AS cells,
           (SELECT count(*) FROM cell c
             WHERE c.model_version_id = mv.id
               AND c.status = 'published')                          AS published_cells,
           -- WHICH capability, not just how many. A count answers "is there
           -- anything here"; the board's actual question is "who is good at
           -- THIS", and a roster that cannot say which capability a model has
           -- been discussed under cannot be filtered by the thing people came
           -- to filter by. Claude Haiku 4.5 has exactly one cell and it is
           -- instruction.adherence; "1 cell" does not tell you that.
           (SELECT array_agg(DISTINCT c.capability_key ORDER BY c.capability_key)
              FROM cell c
             WHERE c.model_version_id = mv.id)                      AS capability_keys,
           -- ── BOARD ENTRIES, WHICH ARE NOT CELLS AND MUST NOT READ AS THEM ──
           --
           -- A cell is COUNTED AND GATED: `insufficient` means we counted and
           -- it was not enough. A board_entry is UNGATED: it means somebody
           -- said this, with no claim about corroboration. `/board` already
           -- renders them that way; this only carries the same fact onto the
           -- roster.
           --
           -- WHY BOTH, rather than replacing the capability chips. They answer
           -- different questions and collapsing them breaks rule 4 in whichever
           -- direction you collapse. Measured on DeepSeek V4 Pro, 2026-09-15:
           --
           --   entries only  23 reports  -> reads as 23 findings, when ZERO
           --                                cleared the publication bar
           --   cells only     6 cells    -> reads as a near-empty model, while
           --                                22 entries about it sit unread
           --
           -- The second is what the page did until now, which is why a run that
           -- produced 50 board entries changed nothing a reader could see.
           --
           -- COUNTS AND SECTIONS, not the entries themselves. The roster is one
           -- query for the whole registry; carrying every entry's quote would
           -- put the board's full text in a list view. `/board` is where an
           -- entry is read.
           (SELECT count(*) FROM board_entry b
             WHERE b.model_version_id = mv.id)                      AS board_entries,
           -- COUNTS PER SECTION, not just which sections. "23 reports" does
           -- not tell a reader where they are, and "12 capability, 8 metric,
           -- 3 best-for" is the sentence the row actually needs.
           (SELECT jsonb_object_agg(s, n)
              FROM (SELECT b.section AS s, count(*) AS n FROM board_entry b
                     WHERE b.model_version_id = mv.id
                     GROUP BY b.section) q)                         AS board_sections
      FROM model_version mv
     ORDER BY mv.display_name
"""

PRICED_AT_SQL = "SELECT max(observed_at) FROM pricing_history"


def _num(v: Decimal | None) -> float | None:
    """NULL survives as None. It is not zero.

    Five models in the registry are routers - Auto Router, OpenRouter: Fusion -
    which dispatch to other models and therefore have no rate of their own.
    Ten others are genuinely free. Collapsing NULL to 0.0 here would tell a
    reader those fifteen are the same thing, and would put the word "free" on
    five models that will bill them.
    """
    return None if v is None else float(v)


def _evidence(*, cells: int, published: int, capability_keys) -> dict:
    """Three states, and the middle one is why this is not a boolean.

    "Has evidence" sounds like a yes/no and is not. Right now 3 of 342 models
    have a cell and NONE has a published one - every cell is `insufficient`,
    n_eff 0.012 against a gate of 3.0. A checkbox would have to pick:

        "has evidence" = has a cell     shows 3 models that did not clear the
                                        gate, to a reader who asked for
                                        evidence. That is rule 4 inverted -
                                        presenting below-threshold as proven.
        "has evidence" = published      shows 0, and an empty list reads as a
                                        broken filter rather than as a finding.

    So the state travels instead, using the same three names the model page
    already renders badges for. `unreported` beside a populated `insufficient`
    bucket is legible; on its own it is not.
    """
    # array_agg over no rows is NULL, not an empty array.
    keys = list(capability_keys or ())

    if published:
        return {
            "state": "published", "cells": cells,
            "published": published, "capabilities": keys,
        }
    if cells:
        return {
            "state": "insufficient", "cells": cells,
            "published": 0, "capabilities": keys,
        }
    return {"state": "unreported", "cells": 0, "published": 0, "capabilities": []}


def _board(*, entries: int, sections: dict | None) -> dict:
    """What the board holds for this model. NOT evidence in the cell sense.

    `_evidence` above carries a `state` because a cell has been through the
    gate and the state is the gate's answer. THIS CARRIES NO STATE, and the
    absence is the point: an entry has not been through anything. Giving it one
    would invite a reader to compare `insufficient` against some board word as
    if they were the same scale.

    `entries = 0` is returned as 0 with an empty section map rather than as an
    absent key, so a page can tell "no entries" from "the roster did not say".

    The map is section -> count, because "23 reports" does not tell a reader
    where they are. Ordered biggest first, which is the order the row reads
    them in.
    """
    by_section = dict(sections or {})
    return {
        "entries": entries,
        "sections": dict(sorted(by_section.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


@dataclass(frozen=True)
class Roster:
    models: list[dict]
    priced_at: str | None
    summary: str


class RosterReader:
    def __init__(self, conn) -> None:
        self._conn = conn

    def all(self) -> Roster:
        rows = self._conn.execute(SQL).fetchall()
        models = [
            {
                "model_version_id": r[0],
                "display_name": r[1],
                "provider": r[2],
                "canonical_id": r[3],
                "price_in": _num(r[4]),
                "price_out": _num(r[5]),
                "price_cached_read": _num(r[6]),
                "advertised_context": r[7],
                "max_output_tokens": r[8],
                "supports_tools": r[9],
                "supports_vision": r[10],
                "supports_structured_output": r[11],
                "supports_caching": r[12],
                "lifecycle": r[13],
                "evidence": _evidence(cells=r[14], published=r[15], capability_keys=r[16]),
                "board": _board(entries=r[17], sections=r[18]),
            }
            for r in rows
        ]

        observed = self._conn.execute(PRICED_AT_SQL).fetchone()[0]
        priced_at = observed.isoformat() if observed else None

        unpriced = sum(1 for m in models if m["price_in"] is None)
        summary = (
            f"{len(models)} models in the registry. Price and context are advertised "
            f"by the provider, not measured by us, and are not evidence of anything."
        )
        if unpriced:
            summary += (
                f" {unpriced} publish no rate at all - routers, which dispatch to "
                f"other models - and are shown as unpriced rather than as free."
            )

        return Roster(models=models, priced_at=priced_at, summary=summary)
