"""E6 rejection, now that `pipeline.py` calls it.

`vet/reject.py` defined the affiliate-link, sponsored-disclosure and
discount-code rules from the start. `pipeline.py` imported only
`vet.weight.compute`, so the reject stage had no caller and ran on nothing -
which is not a hypothetical: the four claims on staging today are quotes from a
product announcement, extracted as though they were engineer opinion.

These tests need no database. `_vet` reads only what it is handed, which is the
property that makes the stage testable at all - and the reason the gap survived
so long is that nothing exercised the JOIN between the two modules, only each
side alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from judge.pipeline import DocumentFacts, Pipeline, PipelineResult


@dataclass
class _Ref:
    resolved_version_id: str | None = "openai/gpt-5"


@dataclass
class _Claim:
    model_ref: _Ref


@dataclass
class _Quote:
    document_id: str


@dataclass
class _Run:
    verified: list


def _pipeline() -> Pipeline:
    # `_vet` never touches the connection or the client; passing None proves it.
    return Pipeline(None, client=None, capability_keys=[], extractor_model="none")


def _result(*document_ids: str) -> PipelineResult:
    return PipelineResult(
        extraction=_Run(verified=[(_Claim(_Ref()), _Quote(d)) for d in document_ids])
    )


def _facts(document_id: str, *, text: str | None, links=()) -> dict:
    return {
        document_id: DocumentFacts(
            document_id=document_id,
            platform="reddit",
            created_at=date(2026, 6, 1),
            text=text,
            links=tuple(links),
        )
    }


def test_a_sponsored_post_is_rejected_and_its_claims_dropped():
    p, result = _pipeline(), _result("d1")

    dropped = p._vet(result, _facts("d1", text="This post is sponsored by Acme AI."), {})

    assert dropped == {"d1"}
    trigger, detail = result.rejected_documents["d1"]
    assert "sponsor" in trigger.lower() or "sponsor" in detail.lower()


def test_a_clean_document_survives():
    p, result = _pipeline(), _result("d1")
    text = "I ran it over 40 tickets and the JSON came back malformed twice."

    dropped = p._vet(result, _facts("d1", text=text), {})

    assert dropped == set()
    assert result.rejected_documents == {}
    assert result.unvetted_documents == []


def test_no_text_is_UNVETTED_and_never_counted_as_kept():
    """Rule 6. A rule that could not run has not passed.

    This is the whole reason `text` was added to DocumentFacts rather than the
    check being skipped quietly when it is missing: `rejected == set()` is the
    same value for "vetted and clean" and "never looked at", so the difference
    has to live somewhere a caller can read.
    """
    p, result = _pipeline(), _result("d1")

    dropped = p._vet(result, _facts("d1", text=None), {})

    assert dropped == set()
    assert result.unvetted_documents == ["d1"]
    assert result.rejected_documents == {}


def test_a_document_with_no_facts_at_all_is_unvetted_not_kept():
    p, result = _pipeline(), _result("ghost")

    p._vet(result, {}, {})

    assert result.unvetted_documents == ["ghost"]


def test_one_rejected_document_does_not_drop_another():
    p = _pipeline()
    result = _result("clean", "paid")
    facts = _facts("clean", text="It truncated the diff on a 900-line file.")
    facts.update(_facts("paid", text="Sponsored by Acme AI."))

    dropped = p._vet(result, facts, {})

    assert dropped == {"paid"}
    assert "clean" not in result.rejected_documents


def test_flags_are_recorded_without_hiding_the_document():
    """`free_api_credits_acknowledged` is a flag, not a rejection.

    reject.py is explicit that this "is not sponsorship, but it is not
    independence either. It is flagged and shown rather than filtered."
    """
    p, result = _pipeline(), _result("d1")
    text = "Thanks to Acme for the API credits. Anyway, it failed on nested JSON."

    dropped = p._vet(result, _facts("d1", text=text), {})

    assert dropped == set()
    assert "free_api_credits_acknowledged" in result.document_flags["d1"]
