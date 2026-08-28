"""The flattened text of a thread_context must not be a container format.

WHY THIS TEST EXISTS AND WHY IT IS TWO LINES OF ASSERTION

Three sweeps stored a container where prose belonged and nothing objected:

    reddit   `json.dumps(post.raw)` in both sweeps, caught before assembly ran
             over 1,512 threads
    github   `text_ref = issue.ref` (correct - it IS the payload) and
             `assemble_issue` flattened it verbatim. All 80 github
             thread_contexts hold `{"url":"https://api.github.com/repos/...`
             and nobody had looked

The failure mode is why a test is worth having: the prose is PRESENT inside the
JSON as `"body": "..."`, so a quote of it verifies by exact substring match and
`quote_verified` reports **true**. Rule 1 returning true for the wrong reason,
`claim_verified_ck` satisfied, offsets pointing into an API envelope, and no
symptom anywhere in the pipeline or on the page.

**The check needs no suspicion and costs one line: resolve the text and look at
the first character.** `{` means an envelope is about to be treated as a
document. I only thought to write it after finding the bug in my own code, which
is the honest order of events, and it is the cheapest item on the repair list.

WHAT THIS DOES NOT COVER, stated because I got it wrong once already

The ruling also proposes `content_hash(resolve(text_ref)) == content_hash` as an
invariant. That is worth having and **it would not have caught this**: the reddit
repoint updated both columns consistently, so the hash always matched its
artifact - it was simply the WRONG artifact. The invariant catches a mismatch,
not a wrong choice. This test catches the wrong choice.
"""

from __future__ import annotations

import json

import pytest

from collect.assemble.issue import assemble_issue
from collect.assemble.prose import (
    TITLE_SEPARATOR,
    NotAPayload,
    github_issue_prose,
    reddit_prose,
)
from collect.assemble.reddit import assemble_reddit_post


class _Store:
    """Enough of the store to assemble. Records what was flattened."""

    def __init__(self) -> None:
        self.written: list[str] = []

    def put(self, data, *, namespace=None):  # noqa: ANN001, ARG002
        text = data if isinstance(data, str) else data.decode("utf-8")
        self.written.append(text)

        class _Stored:
            ref = "flattened/sha256/aa/bb/" + "a" * 64
            content_hash = "a" * 64

        return _Stored()


def _looks_like_a_container(text: str) -> str | None:
    """The whole check. Returns what it looks like, or None for prose."""
    head = text.lstrip()[:1]
    if head == "{" or head == "[":
        return "JSON"
    if head == "<":
        return "markup"
    return None


REDDIT_POST = json.dumps(
    {
        "id": "abc",
        "name": "t3_abc",
        "title": "Opus 4.8 truncates at 8k",
        "selftext": "Reproduced three times with the same prompt.",
    }
)

GITHUB_ISSUE = json.dumps(
    {
        "url": "https://api.github.com/repos/o/r/issues/1",
        "number": 1,
        "title": "Context window shorter than documented",
        "body": "The model truncated at 8k despite a 200k window.",
        "state": "open",
    }
)


class TestTheFlattenedTextIsNotAContainer:
    """The assertion that was missing for a week, on both body-only paths."""

    def test_reddit_post_flattens_prose_not_json(self) -> None:
        store = _Store()
        assemble_reddit_post(
            "reddit:t3_abc", REDDIT_POST, comment_count=47, store=store,
            pipeline_version="test",
        )
        assert store.written, "nothing was flattened"
        for text in store.written:
            assert _looks_like_a_container(text) is None, (
                f"flattened text begins as {_looks_like_a_container(text)}: "
                f"{text[:70]!r}. A quote would verify against a field value."
            )
        assert "Opus 4.8 truncates at 8k" in store.written[0]
        assert '"selftext"' not in store.written[0]

    def test_github_issue_flattens_prose_not_json(self) -> None:
        store = _Store()
        assemble_issue(
            "github:o/r#1", GITHUB_ISSUE, comment_count=3, store=store,
            pipeline_version="test",
        )
        assert store.written, "nothing was flattened"
        for text in store.written:
            assert _looks_like_a_container(text) is None, (
                f"flattened text begins as {_looks_like_a_container(text)}: "
                f"{text[:70]!r}. This is the defect that hid in 80 rows."
            )
        assert "truncated at 8k" in store.written[0]
        assert "api.github.com" not in store.written[0], (
            "the API url reached the flattened text, so the envelope is still there"
        )


class TestTheSeparatorIsFrozen:
    """`title + "\\n\\n" + selftext`, because 1,512 contexts hold offsets into it."""

    def test_reddit_reproduces_the_repoint_formula(self) -> None:
        # The exact string `scripts/repoint_reddit_text_refs.py` stored. A
        # different separator shifts every offset in every offset_map, and
        # offsets cannot be rebuilt later.
        expected = "Opus 4.8 truncates at 8k\n\nReproduced three times with the same prompt."
        assert reddit_prose(REDDIT_POST) == expected
        assert TITLE_SEPARATOR == "\n\n"

    def test_a_comment_is_its_body_alone(self) -> None:
        assert reddit_prose(json.dumps({"body": "a comment"})) == "a comment"


class TestItRefusesRatherThanFallingBack:
    """Every refusal is named. A fallback to the raw string IS the defect."""

    @pytest.mark.parametrize(
        ("blob", "because"),
        [
            ("not json at all", "not JSON"),
            (json.dumps({"data": {"posts": []}}), "no `selftext`"),
            (json.dumps({"title": "", "selftext": ""}), "every text field is empty"),
            ("", "empty input"),
            (json.dumps([1, 2, 3]), "not an object"),
        ],
    )
    def test_reddit_refusals_are_named(self, blob: str, because: str) -> None:
        with pytest.raises(NotAPayload) as exc:
            reddit_prose(blob)
        assert because in str(exc.value)

    def test_github_refuses_a_search_response(self) -> None:
        # One search response covers a hundred issues. Extracting from it would
        # make `content_hash` stop identifying one document.
        with pytest.raises(NotAPayload) as exc:
            github_issue_prose(json.dumps({"total_count": 100, "items": []}))
        assert "no `title` or `body`" in str(exc.value)

    def test_preextracted_prose_is_refused_not_passed_through(self) -> None:
        """The 246 reddit rows whose payload was never stored.

        They hold real text with broken provenance. Refusing is correct: a
        caller that wants them must say so deliberately rather than have the
        extractor guess that a non-JSON string is safe to treat as a document.
        """
        with pytest.raises(NotAPayload):
            reddit_prose("This is real prose but we cannot say where it came from.")
