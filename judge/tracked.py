"""The models the page lists: the hand-written ones, plus new arrivals the rule admits.

`contract/tracked_models.yaml` holds two things since 2026-10-06:

    models       hand-written entries, in the order the page shows them;
    auto_track   a RULE admitting new registry models from providers that
                 already have a hand-written entry (see the block's comments).

This module applies the rule at read time against `model_version`, so a model
the registry poll inserts is on the page - and due for the scheduler - from the
next load, with no per-model PR. The rule is what was reviewed.

Hand-written entries come first, in file order. Auto-admitted ones follow,
newest release first, each marked `auto=True` so a page or report can say how
it got there.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from judge.config import TrackedModel, auto_track_rule, tracked_models

ELIGIBLE = """
    SELECT canonical_id, display_name, release_date
      FROM model_version
     WHERE provenance = 'polled'
       AND in_window
       AND provider = ANY(%s)
       AND release_date IS NOT NULL
       AND release_date >= %s
       AND NOT (canonical_id = ANY(%s))
     ORDER BY release_date DESC, canonical_id
"""


def page_providers(hand: tuple[TrackedModel, ...]) -> list[str]:
    """Providers with at least one hand-written registry entry."""
    return sorted({m.registry.split("/", 1)[0] for m in hand if m.registry and "/" in m.registry})


def _excluded(canonical_id: str, display: str | None, terms: tuple[str, ...]) -> str | None:
    """The term that marks this model non-text, or None. Whole words only, so
    `embed` does not catch `embedded` and `voice` does not catch `invoice`."""
    words = set(re.split(r"[^a-z0-9]+", f"{canonical_id} {display or ''}".lower()))
    return next((t for t in terms if t in words), None)


def _label(display: str | None, canonical_id: str) -> str:
    """`OpenAI: GPT-6.1 Sol` -> `GPT-6.1 Sol`, matching the hand-written names."""
    if not display:
        return canonical_id
    return display.split(": ", 1)[1] if ": " in display else display


def auto_tracked(conn, *, today: date | None = None) -> tuple[TrackedModel, ...]:
    """New registry models the rule admits, newest first. Empty when disabled."""
    rule = auto_track_rule()
    if not rule.enabled:
        return ()
    hand = tracked_models()
    cutoff = (today or date.today()) - timedelta(days=rule.released_within_days)
    rows = conn.execute(
        ELIGIBLE,
        (page_providers(hand), cutoff, [m.registry for m in hand if m.registry]),
    ).fetchall()
    out = []
    for canonical_id, display, _released in rows:
        if not rule.include_pro_tier and canonical_id.endswith("-pro"):
            continue
        if _excluded(canonical_id, display, rule.exclude_name_terms):
            continue
        out.append(TrackedModel(name=_label(display, canonical_id),
                                registry=canonical_id, kind="text", auto=True))
    return tuple(out)


def all_tracked(conn, *, today: date | None = None) -> tuple[TrackedModel, ...]:
    """Hand-written entries in file order, then the rule's admissions."""
    return (*tracked_models(), *auto_tracked(conn, today=today))
