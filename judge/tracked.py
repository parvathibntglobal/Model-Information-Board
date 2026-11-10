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

import logging
import re
from datetime import date, timedelta

from judge.catalog import TYPES as CATALOG_TYPES
from judge.config import TrackedModel, auto_track_rule, tracked_models

log = logging.getLogger(__name__)

# `output_modalities` comes from `model_catalog` (OpenRouter's all-modalities
# list, collect/registry/catalog.py) and decides `kind`. LEFT JOIN, so a model
# the catalogue has not listed yet comes back with NULL rather than vanishing in
# the join - `auto_tracked` then leaves it off and says so (rule 6).
ELIGIBLE = """
    SELECT mv.canonical_id, mv.display_name, mv.release_date, mc.output_modalities
      FROM model_version mv
      LEFT JOIN model_catalog mc ON mc.canonical_id = mv.canonical_id
     WHERE mv.provenance = 'polled'
       AND mv.in_window
       AND mv.provider = ANY(%s)
       AND mv.release_date IS NOT NULL
       AND mv.release_date >= %s
       AND NOT (mv.canonical_id = ANY(%s) OR mv.id = ANY(%s))
     ORDER BY mv.release_date DESC, mv.canonical_id
"""

#: Every output modality OpenRouter publishes: the page's types plus the two it
#: does not offer as types (judge/catalog.py). A value outside this set is a
#: modality nobody has decided a kind for, and it raises rather than reading as
#: text (rule 12).
KNOWN_MODALITIES = frozenset(CATALOG_TYPES) | {"embeddings", "rerank"}

#: THE KIND EACH OUTPUT IS TRACKED AS, decided rather than fallen into (#602,
#: Anooj's review). The tracked list's kinds are text, image, video, speech
#: (text to voice), transcription (voice to text) and decision.
#:   transcription is ITS OWN KIND, not speech: the two read different
#:   evidence and search different repos (#602 review - whisper repos cannot
#:   mention a text-to-speech model), so folding them would mix both.
#: Kept off, so an auto-admitted model with one of these is left off and logged:
#:   audio       mixes music (Lyria) and voice chat (gpt-audio) under one word,
#:               so either kind would be a guess for half of them
#:   embeddings, rerank, decisions   not a kind the board reports on
KIND_OF_OUTPUT = {
    "text": "text",
    "image": "image",
    "video": "video",
    "speech": "speech",
    "transcription": "transcription",
}
KEPT_OFF_OUTPUTS = frozenset({"audio", "embeddings", "rerank", "decisions"})


class UnknownOutputModality(ValueError):
    """The catalogue lists an output modality this module has no kind for."""


def kind_from_modalities(canonical_id: str, modalities) -> str:
    """The `kind` an auto-admitted model gets, from what it OUTPUTS.

    Any non-text output decides it: `google/gemini-nano-banana-2.1` outputs
    `['image', 'text']` and is an image model, which "is text in the list?"
    got wrong. Only an all-text output is `text`.

    Raises on a modality outside `KNOWN_MODALITIES`, and on more than one
    non-text output - two candidate kinds is a choice, not a lookup.
    """
    mods = [str(m) for m in modalities]
    unknown = sorted(set(mods) - KNOWN_MODALITIES)
    if unknown:
        raise UnknownOutputModality(
            f"{canonical_id}: output modality {unknown} has no kind; add it to "
            "judge/tracked.py KNOWN_MODALITIES once someone decides what it is")
    other = sorted(set(mods) - {"text"})
    if len(other) > 1:
        raise UnknownOutputModality(
            f"{canonical_id}: outputs {other}, more than one non-text kind")
    if not other and "text" not in mods:
        raise UnknownOutputModality(f"{canonical_id}: lists no output modality")
    output = other[0] if other else "text"
    if output in KEPT_OFF_OUTPUTS:
        raise UnknownOutputModality(
            f"{canonical_id}: outputs {output!r}, which is kept off the tracked list")
    return KIND_OF_OUTPUT[output]


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
    named = [m.registry for m in hand if m.registry]
    rows = conn.execute(ELIGIBLE, (page_providers(hand), cutoff, named, named)).fetchall()
    out = []
    for canonical_id, display, _released, modalities in rows:
        if not rule.include_pro_tier and canonical_id.endswith("-pro"):
            continue
        if _excluded(canonical_id, display, rule.exclude_name_terms):
            continue
        if modalities is None:
            # NOT IN THE CATALOGUE YET, so what it outputs is unknown. Leaving
            # it off until the catalogue lists it is the NULL-release-date
            # treatment; calling it text would be the guess this replaced.
            log.warning("auto_track: %s left off - no model_catalog row, so its "
                        "output kind is unknown", canonical_id)
            continue
        # ONE MODEL'S ODD OUTPUT MUST NOT STOP THE LIST. `all_tracked` feeds
        # the Models page and the scheduler's due rows, so a raise here would
        # take both down for one row. Refused per model and logged with its
        # outputs instead - still loud (rule 12), never defaulted to text.
        try:
            kind = kind_from_modalities(canonical_id, modalities)
        except UnknownOutputModality as exc:
            # THE MESSAGE, NOT THE EXCEPTION. A logged exception object keeps its
            # traceback, and so this frame and the caller's connection, for as
            # long as a handler holds the record. Under pytest's log capture
            # that left a connection idle in a transaction, and the next test's
            # schema reset waited on it forever (the full suite hung at 4%).
            log.warning("auto_track: %s left off - %s (outputs %s)",
                        canonical_id, str(exc), list(modalities))
            continue
        out.append(TrackedModel(name=_label(display, canonical_id),
                                registry=canonical_id, kind=kind, auto=True))
    return tuple(out)


def all_tracked(conn, *, today: date | None = None) -> tuple[TrackedModel, ...]:
    """Hand-written entries in file order, then the rule's admissions."""
    return (*tracked_models(), *auto_tracked(conn, today=today))


def tracked_keys(conn, *, today: date | None = None) -> set[str]:
    """Every id of every tracked model, in BOTH shapes: row `id` and `canonical_id`.

    A tracked `registry` value may name either column, as the models page reads
    it, and the two differ on almost every row. Comparing one shape against the
    other is a silent miss, not an error. Claude Fable 5.1's entry names its row
    id `anthropic/claude-fable-5-1`; its canonical id is
    `anthropic/claude-fable-5.1`. Matching one shape put it on the discussed
    list as untracked and kept it out of the scheduler's due list, and two
    callers had already repaired the same miss locally (judge/feed/items.py,
    scripts/promotion_report.py). Ask this set instead.

    A tracked value with no row is kept as it is, so it still counts as tracked
    wherever something carries that id.
    """
    names = [t.registry for t in all_tracked(conn, today=today) if t.registry]
    return set(names) | row_keys(conn, names)


def row_keys(conn, names: list[str]) -> set[str]:
    """Both ids of every `model_version` row that `names` matches in either shape.

    Rows only: a name that matches no row contributes nothing here.
    """
    rows = conn.execute(
        "SELECT id, canonical_id FROM model_version WHERE id = ANY(%s) OR canonical_id = ANY(%s)",
        (names, names),
    ).fetchall()
    return {key for row in rows for key in row if key}
