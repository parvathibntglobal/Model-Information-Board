"""The legacy capability-card path, switched off by default since 2026-09-24.

WHAT "LEGACY" COVERS. Everything keyed to the ratified twelve in
`contract/capabilities.yaml`, which fed the old per-model capability cards:

    extraction   the closed `capability` field and `proposed_capabilities`
                 (both removed from the prompt and the tool schema when off)
    E5b          capability_candidate proposals against the twelve
    E6 weights   claim_weight - tier, n_eff, recency - which price cells only
    claim rows   `claim` needs a condition bucket and an evidence tier, both
                 legacy concepts, so no claim row is written when off
    E7           cell rebuild, and `close_the_night` (labels, changelog), which
                 reads cells

WHAT STAYS ON. The board. `board_entry` is written from every verified quote
exactly as before - it never read `claim` or `cell` - and E6's HARD rejection
(affiliate, sponsored, pre-release) still runs, because it protects the board.

WHY A SWITCH AND NOT DELETED CODE. The board replaced the cards as the product
(`web/src/routes/ModelDetail.jsx` stopped rendering them); the code, the tables
and the rows already written stay, so turning it back on is `LEGACY_CELLS=on`
and nothing has to be restored from history.

⚠ OFF MEANS THE CELLS STOP MOVING, NOT THAT THEY VANISH. Rows written before
the switch are still in `cell`. Any reader that shows them as current would be
showing a frozen verdict as live - so the readers check this flag too.
"""

from __future__ import annotations

import os

LEGACY_CELLS_ENV = "LEGACY_CELLS"
_ON = {"1", "on", "true", "yes"}


def legacy_cells_enabled() -> bool:
    """True only when `LEGACY_CELLS` is explicitly on. Read at call time."""
    return (os.getenv(LEGACY_CELLS_ENV) or "").strip().lower() in _ON
