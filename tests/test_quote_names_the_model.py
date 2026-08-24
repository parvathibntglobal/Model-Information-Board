"""The third check: does the quote name the model the claim is filed against?

Verification proves the quote is real. Resolution proves the model exists.
NOTHING proved the quote mentions the model — so a claim could be verified,
attributed, and about a different model than the page it renders on. Measured:
`"I'm now generating my summaries using GPT-5.6 Luna."` was filed against
`openai/gpt-5` and displayed there with a working permalink.

No model call. The extractor proposes an attribution; code checks whether the
quote supports it — quote verification's own argument applied to the subject.
"""

from __future__ import annotations

import pytest

from judge.pipeline import (
    QUOTE_NAMES_ANOTHER,
    QUOTE_NAMES_NOTHING,
    QUOTE_NAMES_SOMETHING_UNCOMPARED,
    QUOTE_NAMES_THE_MODEL,
    quote_subject_verdict,
    subject_was_inherited,
)

FINDER = {"names luna": ("GPT-5.6 Luna",), "names both": ("GPT-5.6 Luna", "GPT-5"),
          "names none": ()}
OWNER = {"GPT-5.6 Luna": "mv_luna", "GPT-5": "mv_gpt5", "Unseated 9": None}


def _find(text):
    return FINDER.get(text, ())


def _resolve(surface):
    return OWNER.get(surface)


class TestTheThreeStates:
    def test_the_quote_names_a_different_model(self):
        assert quote_subject_verdict(
            "names luna", model_version_id="mv_gpt5",
            find_surfaces=_find, resolve_surface=_resolve,
        ) is QUOTE_NAMES_ANOTHER

    def test_the_quote_names_the_model(self):
        assert quote_subject_verdict(
            "names luna", model_version_id="mv_luna",
            find_surfaces=_find, resolve_surface=_resolve,
        ) is QUOTE_NAMES_THE_MODEL

    def test_the_claims_model_among_several_named_is_agreement(self):
        """A quote comparing two models still supports a claim about either."""
        assert quote_subject_verdict(
            "names both", model_version_id="mv_gpt5",
            find_surfaces=_find, resolve_surface=_resolve,
        ) is QUOTE_NAMES_THE_MODEL


class TestTheLegitimateCase:
    """A comment inheriting a thread root's subject MUST NOT be flagged."""

    def test_a_quote_naming_no_model_is_not_a_disagreement(self):
        assert quote_subject_verdict(
            "names none", model_version_id="mv_gpt5",
            find_surfaces=_find, resolve_surface=_resolve,
        ) is QUOTE_NAMES_NOTHING

    def test_surfaces_that_resolve_to_nothing_are_the_same_state(self):
        """An unseated model, a family word or a product name names nothing
        WE TRACK, and this check cannot say a claim disagrees with a subject it
        could not identify."""
        assert quote_subject_verdict(
            "unseated", model_version_id="mv_gpt5",
            find_surfaces=lambda t: ("Unseated 9",), resolve_surface=_resolve,
        ) is QUOTE_NAMES_NOTHING


class TestItComposesWithSubjectInherited:
    """One resolution, two questions, and they cannot disagree."""

    @pytest.mark.parametrize(
        ("text", "expected"), [("names none", True), ("names luna", False)]
    )
    def test_inherited_is_a_projection_of_the_verdict(self, text, expected):
        assert subject_was_inherited(
            text, model_version_id="mv_gpt5", find_surfaces=_find
        ) is expected

    def test_inherited_answers_without_a_resolver(self):
        """Its question — did the quote name a model — needs no comparison, so
        the missing resolver must not turn a settled False into None."""
        assert quote_subject_verdict(
            "names luna", model_version_id="mv_gpt5", find_surfaces=_find,
        ) is QUOTE_NAMES_SOMETHING_UNCOMPARED
        assert subject_was_inherited(
            "names luna", model_version_id="mv_gpt5", find_surfaces=_find
        ) is False


class TestItRefusesRatherThanGuessing:
    @pytest.mark.parametrize("kwargs", [
        {"model_version_id": None, "find_surfaces": _find},
        {"model_version_id": "mv_gpt5", "find_surfaces": None},
    ])
    def test_no_input_means_no_answer(self, kwargs):
        """Rule 6: "nobody checked" is not "checked and agreed"."""
        assert quote_subject_verdict("names luna", **kwargs) is None

    def test_a_missing_resolver_is_not_reported_as_agreement(self):
        """The failure this guards: a check that says "fine" when it could not
        run is worse than one that visibly did not run."""
        got = quote_subject_verdict(
            "names luna", model_version_id="mv_gpt5", find_surfaces=_find
        )
        assert got is not QUOTE_NAMES_THE_MODEL
        assert got is not QUOTE_NAMES_ANOTHER
