"""The condition dimensions, and the field that stopped a bool taking strings.

`reasoning_effort` was added 2026-08-21 after `structured_mode` — a
`bool | None` — received `'xhigh'` twice and `'auto mode'` once. The last cost
four claims. These tests hold the three properties that make the new field a fix
rather than a wider hole:

  1. the bands in the contract and the values the extractor may emit agree,
     except for `unknown`, which is deliberately unsayable in the schema;
  2. an unrecognised effort is LOUD, not folded into `unknown` — that would
     convert a value somebody reported into missing data (rule 6);
  3. every band a claim can carry has a phrase, so no raw bucket key reaches a
     page.
"""

from __future__ import annotations

import typing

import pytest
import yaml

from judge.config import CONTRACT_DIR, band_for, conditions
from judge.curate.phrases import CONDITION_LABELS, condition_label
from judge.extract.schema import Conditions, ReasoningEffort


@pytest.fixture(scope="module")
def raw() -> dict:
    return yaml.safe_load((CONTRACT_DIR / "conditions.yaml").read_text(encoding="utf-8"))


class TestTheDimensionExists:
    def test_reasoning_effort_is_a_dimension(self, raw):
        assert "reasoning_effort" in {d["key"] for d in raw["dimensions"]}
        assert "reasoning_effort" in conditions()

    def test_the_claim_schema_can_carry_it(self):
        assert "reasoning_effort" in Conditions.model_fields

    def test_it_is_optional_because_absent_stays_absent(self):
        """A condition nobody stated is not a condition with a default."""
        assert Conditions().reasoning_effort is None


class TestTheContractAndTheSchemaAgree:
    def test_every_value_the_extractor_may_emit_is_a_band(self, raw):
        """The whole point of the field is that the value lands somewhere real.

        A Literal value with no band would be accepted by extraction and then
        raise in `band_for` — a validation error moved one stage later.
        """
        bands = set(conditions()["reasoning_effort"].bands)
        emittable = set(typing.get_args(ReasoningEffort))
        assert emittable <= bands, f"emittable but not a band: {emittable - bands}"

    def test_unknown_is_a_band_and_is_not_emittable(self):
        """Two ways to say "the document did not say" would lose the distinction.

        `unknown` is what an ABSENT value produces. If the model could also
        choose it, "nobody stated the effort" and "the model decided it could
        not tell" would be the same string, and rule 6 turns on keeping those
        apart.
        """
        assert "unknown" in conditions()["reasoning_effort"].bands
        assert "unknown" not in typing.get_args(ReasoningEffort)
        assert band_for("reasoning_effort", None) == "unknown"

    def test_auto_is_a_band_rather_than_an_omission(self):
        """`'auto mode'` is the value that cost four claims, so it must land."""
        assert "auto" in typing.get_args(ReasoningEffort)
        assert band_for("reasoning_effort", "auto") == "auto"
        assert band_for("reasoning_effort", "auto mode") == "auto"


class TestVendorSpellingsFold:
    @pytest.mark.parametrize(
        "value,band",
        [
            ("xhigh", "max"),  # the string that started this
            ("XHigh", "max"),
            ("  max  ", "max"),
            ("minimal", "off"),
            ("none", "off"),
            ("default", "medium"),
            ("dynamic", "auto"),
        ],
    )
    def test_known_aliases(self, value, band):
        assert band_for("reasoning_effort", value) == band


class TestAnUnrecognisedEffortIsLoud:
    def test_it_raises_rather_than_becoming_unknown(self):
        """The failure this file exists to prevent, one level up.

        Folding an unrecognised tier into `unknown` would be the same defect as
        the bool taking a string: a real value quietly filed as something it is
        not. Here it would be filed as ABSENCE, which is worse — nobody audits
        a bucket that reads as missing data.
        """
        with pytest.raises(ValueError) as exc:
            band_for("reasoning_effort", "ultrathink")
        assert "ultrathink" in str(exc.value)
        assert "unknown" in str(exc.value)  # names what must not happen


class TestNoRawBucketKeyReachesAPage:
    def test_every_emittable_band_has_a_phrase(self):
        """`condition_label` falls back to the raw bucket string.

        No capability is reasoning_effort-dominant today, so these are
        unreachable — which is exactly when a missing phrase goes unnoticed
        until the day the dominance moves.
        """
        for value in typing.get_args(ReasoningEffort):
            bucket = f"reasoning_effort:{value}"
            assert bucket in CONDITION_LABELS, bucket
            assert condition_label(bucket) != bucket


class TestTheFieldThatTookThreeWrongValues:
    def test_it_is_no_longer_named_after_a_word_the_corpus_uses(self):
        """`structured_mode` captured "auto mode" three draws out of three.

        Renaming it to `schema_enforced` stopped that dead — measured, three
        arms, three draws, in `docs/measurements/the-effort-dimension.md`. The
        old name must not come back, and a rename reads as tidying, so this is
        the test that says it was load-bearing.
        """
        assert "structured_mode" not in Conditions.model_fields
        assert "schema_enforced" in Conditions.model_fields
        assert not any(f.endswith("_mode") for f in Conditions.model_fields), (
            "no conditions field may be named after 'mode' — that word appears "
            "in the corpus meaning something else, and the name wins over "
            "every description"
        )

    def test_its_description_points_at_the_right_field(self):
        text = Conditions.model_fields["schema_enforced"].description or ""
        assert "reasoning_effort" in text
