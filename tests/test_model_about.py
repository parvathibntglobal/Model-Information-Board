"""Our wording of a model's OpenRouter description (judge/model_about.py): a
prototype, 2026-11-03.

The check that let each text in is re-run here on every entry, so a hand edit
to model_about.json that copies the listing or adds a number fails the suite
(rule 2: the model proposed, code checks, a person approves). An unapproved
entry says it is a draft; a model with no entry has no wording of ours.
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


def test_an_unapproved_entry_says_it_is_a_draft():
    first = ENTRIES[0]
    got = model_about.get(first["id"])
    assert got["text"] == first["about"]
    assert got["approved"] is (first["approved_by"] is not None)


def test_a_model_with_no_entry_has_no_wording_of_ours():
    assert model_about.get("nobody/no-such-model") is None
