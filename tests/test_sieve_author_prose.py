"""Signal must come from the author's own prose. Subject and topic need not.

The first live GitHub harvest stored two documents as
`summarization.fidelity: positive` evidence for `gemini-2.5-flash`:

    Aider-AI/aider#4438    an issue about diff application. `accurate` matched
                           inside a Google marketing sentence someone pasted —
                           a blockquote nested inside a fenced block
    crewAIInc/crewAI#2685  an issue about a tool signature. `accurate` matched
                           inside a prompt string in a Python snippet

Two config lines and somebody else's copy would have contributed voices toward
publishing "Flash summarises faithfully". These are the regression tests, and
the entries come from `contract/queries.yaml` rather than being hand-written
here, so the test exercises Engineer 2's actual vocabulary.

The pair pattern from `test_github_harvest.py` applies again: where the bug is
"two states record identically", the test asserts both in one place and compares
them. Here the states are *a signal nobody asserted* and *no signal at all*.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from collect.adapters.queries.contract import TermSet, load_queries
from collect.adapters.queries.sieve import (
    EXCLUDED_CONTAINERS,
    author_prose,
    normalize,
    sieve,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "github"
ALIAS = "gemini-2.5-flash"


def positive_terms():
    """The real `summarization.fidelity: positive` entry, from the contract."""
    entry = next(
        e
        for e in load_queries().for_capability("summarization.fidelity")
        if e.stance == "positive"
    )
    return entry.terms.substitute(ALIAS)


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ── the two documents that wrote this file ────────────────────────────────


@pytest.mark.parametrize(
    "name",
    ["aider-4438-excerpt.md", "crewai-2685-excerpt.md"],
    ids=["aider-4438", "crewai-2685"],
)
def test_neither_false_positive_yields_a_positive_summarisation_claim(name):
    """The failing assertion this fix exists for."""
    verdict = sieve(positive_terms(), fixture(name))
    assert not verdict.passed
    assert "signal" in verdict.missing


@pytest.mark.parametrize(
    "name",
    ["aider-4438-excerpt.md", "crewai-2685-excerpt.md"],
    ids=["aider-4438", "crewai-2685"],
)
def test_they_are_rejected_for_the_right_reason(name):
    """Rejected on the claim, not on aboutness.

    Both genuinely involve the model — a config line and an `LLM(model=...)`
    call — so subject and topic must still match. A rejection that happened to
    come from the subject group would pass this file's other test while leaving
    the real defect in place.
    """
    verdict = sieve(positive_terms(), fixture(name))
    assert verdict.subject == (ALIAS,), "the model is named; that much is true"
    assert verdict.topic, "summarisation is mentioned; also true"
    assert verdict.signal == (), "nobody claimed it summarised well"
    assert "accurate" in verdict.signal_in_excluded


def test_a_quoted_signal_and_an_absent_signal_are_distinguishable():
    """The pair. Both rejected, and not for the same reason.

    Without `signal_in_excluded` these two are one state, and the vocabulary
    feedback — "your term is there, and only somebody else said it" — is lost.
    """
    quoted = sieve(positive_terms(), fixture("crewai-2685-excerpt.md"))
    absent = sieve(
        positive_terms(),
        f"We put {ALIAS} behind the digest job. It summarises tickets nightly.",
    )

    assert quoted.passed is absent.passed is False
    assert quoted.missing == absent.missing == ("signal",)
    assert quoted.signal_in_excluded == ("accurate",)
    assert absent.signal_in_excluded == ()


def test_a_real_positive_still_passes():
    """The exclusion must not reject the claim it was built to protect."""
    document = (
        f"We moved the nightly digest to {ALIAS} three months ago and it held up. "
        "Ran it over 40k tickets a week, no complaints from the team that reads them.\n"
        "```python\n"
        f'model = "{ALIAS}"  # accurate enough\n'
        "```\n"
    )
    verdict = sieve(positive_terms(), document)
    assert verdict.passed
    assert "held up" in verdict.signal


# ── the exclusion set, member by member ──────────────────────────────────


@pytest.mark.parametrize(
    ("container", "document"),
    [
        ("fenced-code", "```\nit was accurate\n```"),
        ("fenced-code-tilde", "~~~\nit was accurate\n~~~"),
        ("blockquote", "> it was accurate"),
        ("indented-code", "    log: it was accurate"),
        ("inline-code", "the `accurate` flag"),
        ("html-pre", "<pre>it was accurate</pre>"),
        ("html-comment", "<!-- was it accurate? -->"),
        ("url", "see https://x.invalid/more-accurate-models"),
        ("template-residue", "- [x] accurate"),
    ],
)
def test_each_container_hides_a_signal(container, document):
    """One term, nine containers. Named as a set, not fixed case by case.

    Both live false positives arrived through fences; the next one will not.
    """
    assert "accurate" not in normalize(author_prose(document)), container


def test_the_containers_are_named_for_anyone_auditing_a_rejection():
    assert "fenced-code" in EXCLUDED_CONTAINERS
    assert "blockquote" in EXCLUDED_CONTAINERS
    assert len(EXCLUDED_CONTAINERS) == 8


def test_a_blockquote_nested_in_a_fence_is_removed_once_and_completely():
    """`Aider-AI/aider#4438`'s exact shape: `>` lines inside a ``` block."""
    document = "```\nAider v0.86.0\n> These enable more accurate systems.\n```"
    assert "accurate" not in normalize(author_prose(document))


def test_the_authors_own_prose_survives():
    document = (
        "It held up over three months.\n"
        "```\nirrelevant = True\n```\n"
        "No complaints since."
    )
    prose = normalize(author_prose(document))
    assert "held up" in prose
    assert "no complaints" in prose
    assert "irrelevant" not in prose


def test_removed_spans_leave_a_gap_so_words_cannot_fuse():
    """`a`+`b` must not become `ab` and match a term neither word contains."""
    assert "held up" not in normalize(author_prose("hel`x`d up"))


# ── the deliberate half of the split ─────────────────────────────────────


def test_subject_and_topic_may_come_from_code():
    """A config line does show the model was in use, and that is worth keeping.

    This is the half of the split that is easy to get wrong in the other
    direction: excluding code everywhere would drop every document whose only
    mention of the model is a `model=` parameter, which is most of the corpus on
    this platform.
    """
    terms = TermSet(
        subject=("{alias}",), topic=("summarize",), signal=("held up",)
    ).substitute(ALIAS)
    document = (
        "```python\n"
        f'llm = LLM(model="{ALIAS}")\n'
        "rag = RagTool(summarize=True)\n"
        "```\n"
        "Ran this for a quarter and it held up."
    )
    verdict = sieve(terms, document)
    assert verdict.passed
    assert verdict.subject == (ALIAS,)
    assert verdict.topic == ("summarize",)
    assert verdict.signal == ("held up",)
