"""Our own wording of a model's OpenRouter description (model_about.json).

A PROTOTYPE (feat/hooks-prototype, 2026-11-03, anooj). OpenRouter cuts most
descriptions mid-sentence ("... code...": 591 of the 685 in its list of
2026-11-02 ended in "..."), and the same words appeared twice on a model's page.
So the header shows our own sentences with the same meaning.

RULE 2: a language model PROPOSED each text; code CHECKS it against the words
it paraphrases (judge/feed/checks.paraphrase_problem: copied runs, numbers,
length) and a person must APPROVE it. Until `approved_by` is set the page says
it is a draft. A model with no entry shows OpenRouter's own words, labelled as
OpenRouter's - never our wording invented on the spot.
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


def get(model_id: str) -> dict[str, Any] | None:
    """{"text", "approved", "checked_on"} for the page, or None with no entry."""
    m = _all().get(model_id)
    if m is None or not m["about"]:
        return None
    return {"text": m["about"], "approved": m["approved_by"] is not None,
            "checked_on": m["checked_on"]}
