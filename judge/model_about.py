"""Our own wording of a model's OpenRouter description (model_about.json).

A PROTOTYPE (feat/hooks-prototype, 2026-11-03, anooj). OpenRouter cuts most
descriptions mid-sentence ("... code...": 591 of the 685 in its list of
2026-11-02 ended in "..."), and the same words appeared twice on a model's page.
So the header can show our own sentences with the same meaning.

RULE 2, AS THE SUMMARIES DO IT (#597 review): a language model PROPOSED each
text; code CHECKS it against the words it paraphrases
(judge/feed/checks.paraphrase_problem: copied runs, numbers, length); and a
person APPROVES it. Until `approved_by` is set NOTHING here reaches a page -
the header shows OpenRouter's own words, labelled as theirs.

A TEXT GOES STALE WITH ITS SOURCE (#597 review): an approved text is shown only
while OpenRouter's current description still begins with the words it was
written from (`source`, less a trailing "..."). When OpenRouter rewrites its
description, our wording drops out by itself and theirs shows again.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

PATH = Path(__file__).with_name("model_about.json")


@lru_cache(maxsize=1)
def _all() -> dict[str, dict[str, Any]]:
    doc = json.loads(PATH.read_text(encoding="utf-8"))
    return {m["id"]: {**m, "checked_on": doc["checked_on"]} for m in doc["models"]}


def _stem(text: str) -> str:
    """The words a text was written from, without OpenRouter's cut-off marker."""
    t = " ".join((text or "").split())
    return t[:-3].rstrip() if t.endswith("...") else t


def still_matches(source: str, current: str | None) -> bool:
    """Is OpenRouter's description now still the one this text paraphrases?"""
    stem = _stem(source)
    return bool(stem) and current is not None and _stem(current).startswith(stem)


def get(model_id: str, current_description: str | None) -> dict[str, Any] | None:
    """{"text", "approved_by", "checked_on"} for the page, or None: no entry, not
    approved yet, or written from a description OpenRouter no longer shows."""
    m = _all().get(model_id)
    if m is None or not m["about"] or m["approved_by"] is None:
        return None
    if not still_matches(m["source"], current_description):
        return None
    return {"text": m["about"], "approved_by": m["approved_by"], "checked_on": m["checked_on"]}
