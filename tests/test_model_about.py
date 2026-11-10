"""Our wording of a model's OpenRouter description (judge/model_about.py): a
prototype, 2026-11-03.

The check that let each text in is re-run here on every entry, so a hand edit
to model_about.json that copies the listing or adds a number fails the suite
(rule 2: the model proposed, code checks, a person approves). Nothing is
shown before a person approves it, and an approved text drops out when
OpenRouter rewrites the description it was written from (#597 review).
"""

from __future__ import annotations

import json

import pytest

from judge import model_about
from judge.feed import checks

ENTRIES = json.loads(model_about.PATH.read_text(encoding="utf-8"))["models"]


@pytest.mark.parametrize("entry", ENTRIES, ids=[e["id"] for e in ENTRIES])
def test_every_entry_passes_the_paraphrase_check_against_its_source(entry):
    label = entry["id"].split("/", 1)[1].replace("-", " ")
    problem = checks.paraphrase_problem(entry["about"], [entry["source"]], label,
                                        max_chars=320, max_copied_words=6)
    assert problem is None, f"{entry['id']}: {problem}"
    assert not entry["about"].rstrip().endswith("..."), "our wording is never cut off"


SOURCE = "Acme 2 is a fast model for agents. It is particularly strong at..."


def _entry(approved_by, source=SOURCE):
    return {"id": "acme/two", "about": "Built for agents, Acme 2 is quick.", "source": source,
            "approved_by": approved_by, "checked_on": "2026-11-03"}


def test_nothing_reaches_a_page_until_a_person_approves_it(monkeypatch):
    """As the evidence feed's summaries: drafted by a model, shown only once
    approved (#597 review). Until then the page shows OpenRouter's words."""
    monkeypatch.setattr(model_about, "_all", lambda: {"acme/two": _entry(None)})
    current = "Acme 2 is a fast model for agents. It is particularly strong at..."
    assert model_about.get("acme/two", current) is None
    monkeypatch.setattr(model_about, "_all", lambda: {"acme/two": _entry("parvathi")})
    assert model_about.get("acme/two", current)["text"] == "Built for agents, Acme 2 is quick."


def test_a_text_goes_stale_when_openrouter_rewrites_its_description(monkeypatch):
    monkeypatch.setattr(model_about, "_all", lambda: {"acme/two": _entry("parvathi")})
    # The same words, now longer (OpenRouter no longer cuts it): still ours.
    longer = "Acme 2 is a fast model for agents. It is particularly strong at tool calls."
    assert model_about.get("acme/two", longer) is not None
    # Rewritten: ours drops out by itself, and theirs shows again.
    assert model_about.get("acme/two", "Acme 2 is a slow model for chat.") is None
    assert model_about.get("acme/two", None) is None


def test_no_unapproved_entry_in_the_file_reaches_a_page():
    for e in ENTRIES:
        if e["approved_by"] is None:
            assert model_about.get(e["id"], e["source"]) is None, e["id"]


def test_a_model_with_no_entry_has_no_wording_of_ours():
    assert model_about.get("nobody/no-such-model", "anything") is None
