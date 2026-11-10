"""Kite Pulse outreach claims.yaml: the approved sentences and refused phrases.

The REPLY CHECK that will read this file is not built; until it is, these tests
are its only reader, and they hold the file to the shape that check will need.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

OUTREACH = Path(__file__).resolve().parent.parent / "web" / "src" / "kitepulse" / "outreach"
CLAIMS = yaml.safe_load((OUTREACH / "config" / "claims.yaml").read_text(encoding="utf-8"))
FINDERS = ("hackernews", "devto", "discourse", "github", "reddit")


def _problems() -> set[str]:
    keys: set[str] = set()
    for finder in FINDERS:
        q = yaml.safe_load((OUTREACH / finder / "config" / "queries.yaml").read_text(
            encoding="utf-8"))
        keys |= set(q["problems"])
    return keys


def _has_phrase(text: str, phrase: str) -> bool:
    """Whole words, case-insensitive: how the REPLY CHECK is to match `refused`."""
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text, re.I) is not None


def test_the_source_document_exists_and_the_review_is_recorded_honestly():
    assert (Path(__file__).resolve().parent.parent / CLAIMS["source"]["document"]).is_file()
    # null until the product owner has read every sentence; never a placeholder name
    assert ("reviewed_by" in CLAIMS) and ("reviewed_on" in CLAIMS)
    assert (CLAIMS["reviewed_by"] is None) == (CLAIMS["reviewed_on"] is None)


def test_the_disclosure_line_is_the_decided_one():
    assert CLAIMS["disclosure"]["line"] == "Disclosure: I work on Kite Pulse"


def test_every_approved_claim_has_an_id_a_source_and_names_kite_pulse():
    ids = [c["id"] for c in CLAIMS["approved"]]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for c in CLAIMS["approved"]:
        assert c["source"].strip(), c["id"]
        assert "Kite Pulse" in c["text"], c["id"]
        assert c["text"].rstrip().endswith("."), c["id"]


def test_every_claim_is_tagged_with_a_real_problem():
    known = _problems() | {"any"}
    for c in CLAIMS["approved"]:
        assert c["problems"] and set(c["problems"]) <= known, (c["id"], c["problems"])


def test_every_problem_has_at_least_one_claim_of_its_own():
    tagged = {p for c in CLAIMS["approved"] for p in c["problems"]}
    assert _problems() <= tagged, f"no claim for: {_problems() - tagged}"


@pytest.mark.parametrize("claim", CLAIMS["approved"], ids=lambda c: c["id"])
def test_no_approved_claim_contains_a_refused_phrase(claim):
    hits = [r["phrase"] for r in CLAIMS["refused"] if _has_phrase(claim["text"], r["phrase"])]
    assert not hits, f"{claim['id']} would be refused for {hits}"


def test_the_disclosure_line_contains_no_refused_phrase():
    line = CLAIMS["disclosure"]["line"]
    assert not [r for r in CLAIMS["refused"] if _has_phrase(line, r["phrase"])]


def test_every_refused_phrase_says_why_and_where():
    phrases = [r["phrase"].lower() for r in CLAIMS["refused"]]
    assert len(phrases) == len(set(phrases)), "duplicate refused phrases"
    for r in CLAIMS["refused"]:
        assert r["phrase"].strip() and r["why"].strip() and r["source"].strip(), r


def test_whole_word_matching_does_not_refuse_inside_another_word():
    assert _has_phrase("Do you have 2FA?", "2FA")
    assert not _has_phrase("a remarkup of the page", "markup")
    assert not _has_phrase("the macro is broken", "ROI")
