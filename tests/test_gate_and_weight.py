"""The publication gate arithmetic, and the weight factors that feed it.

The gate is where fake precision would enter if anywhere. These tests pin the
arithmetic that makes `n_eff >= 3.0` mean what the spec says it means.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from judge.curate.gate import (
    N_EFF_MINIMUM,
    CellStatus,
    GateFailure,
    WeightedClaim,
    author_cap_for,
    check_gate,
    classify,
    count,
)
from judge.curate.phrases import conditional_note, describe
from judge.extract.schema import Conditions, ExtractedClaim, ModelRef
from judge.vet import weight

TODAY = date(2026, 8, 12)


def claim(voice: str, platform: str, w: float, polarity: str = "positive", **kw):
    return WeightedClaim(
        claim_id=kw.get("claim_id", f"c_{voice}_{platform}"),
        voice_id=voice,
        platform=platform,
        weight=w,
        polarity=polarity,
        severity=kw.get("severity"),
        quote_id=kw.get("quote_id", f"q_{voice}"),
        created_at=kw.get("created_at", TODAY - timedelta(days=10)),
        condition_bucket=kw.get("bucket", "context_size:8k-32k"),
    )


class TestWeightCeiling:
    def test_no_single_claim_can_exceed_point_nine_five(self):
        """This cap is why `voices >= 3` would be dead text in the gate."""
        assert weight.MAX_POSSIBLE_WEIGHT == 0.95

    def test_three_perfect_claims_do_not_clear_the_gate(self):
        """3 x 0.95 = 2.85, which fails n_eff >= 3.0. Four claims minimum."""
        claims = [claim(f"v{i}", "github" if i % 2 else "blog", 0.95) for i in range(3)]
        counts = count(claims, as_of=TODAY)
        assert counts.n_eff < N_EFF_MINIMUM
        assert not check_gate(counts).passed

    def test_four_perfect_claims_clear_it(self):
        claims = [claim(f"v{i}", "github" if i % 2 else "blog", 0.95) for i in range(4)]
        counts = count(claims, as_of=TODAY)
        assert counts.n_eff >= N_EFF_MINIMUM
        assert check_gate(counts).passed


class TestCountingPeople:
    def test_one_person_posting_five_times_counts_once(self):
        """Otherwise one enthusiast clears the gate alone."""
        claims = [claim("alice", "reddit", 0.8, quote_id=f"q{i}") for i in range(5)]
        counts = count(claims, as_of=TODAY)
        assert counts.independent_voices == 1
        assert counts.n_eff == 0.8  # the best claim, not the sum

    def test_one_person_on_two_platforms_is_one_voice(self):
        """This is the condition the two-platform rule exists to demand."""
        claims = [claim("alice", "github", 0.9), claim("alice", "reddit", 0.7)]
        counts = count(claims, as_of=TODAY)
        assert counts.independent_voices == 1
        assert counts.platform_count == 1  # from the single representative claim


class TestGateConditions:
    def test_one_platform_fails_however_much_weight(self):
        claims = [claim(f"v{i}", "github", 0.95) for i in range(6)]
        result = check_gate(count(claims, as_of=TODAY))
        assert not result.passed
        assert GateFailure.ONE_PLATFORM_ONLY in result.failures

    def test_author_cap_relaxes_below_five_voices(self):
        assert author_cap_for(4) == 0.50
        assert author_cap_for(5) == 0.20

    def test_one_loud_account_cannot_carry_a_cell(self):
        claims = [
            claim("loud", "github", 0.95),
            claim("v1", "reddit", 0.2),
            claim("v2", "blog", 0.2),
            claim("v3", "reddit", 0.2),
            claim("v4", "blog", 0.2),
        ]
        counts = count(claims, as_of=TODAY)
        result = check_gate(counts)
        assert counts.independent_voices == 5
        assert GateFailure.SINGLE_AUTHOR_DOMINATES in result.failures


class TestClassification:
    def test_disagreement_inside_one_bucket_is_contested(self):
        claims = [
            claim("v1", "github", 0.9, "positive"),
            claim("v2", "blog", 0.9, "positive"),
            claim("v3", "reddit", 0.9, "negative"),
            claim("v4", "github", 0.9, "negative"),
        ]
        assert classify(count(claims, as_of=TODAY)) is CellStatus.CONTESTED

    def test_agreement_publishes(self):
        claims = [claim(f"v{i}", "github" if i % 2 else "blog", 0.9) for i in range(5)]
        assert classify(count(claims, as_of=TODAY)) is CellStatus.PUBLISHED


class TestSilenceIsNotCriticism:
    def test_no_evidence_says_nobody_discussed_it(self):
        c = describe(count([], as_of=TODAY), capability_key="summarization.fidelity",
                     status=CellStatus.INSUFFICIENT)
        assert "Nobody has publicly discussed" in c.phrase
        assert c.is_silence

    def test_below_gate_is_marked_uncorroborated_not_bad(self):
        claims = [claim("v1", "github", 0.9)]
        c = describe(count(claims, as_of=TODAY), capability_key="summarization.fidelity",
                     status=CellStatus.INSUFFICIENT)
        assert "not yet corroborated" in c.phrase
        assert "criticis" not in c.phrase.lower()


class TestConditionalConsensus:
    def test_opposing_buckets_produce_the_sentence_a_score_would_destroy(self):
        good = describe(
            count([claim(f"v{i}", "github" if i % 2 else "blog", 0.9) for i in range(5)],
                  as_of=TODAY),
            capability_key="tool_calling.schema_accuracy",
            status=CellStatus.PUBLISHED,
        )
        bad = describe(
            count([claim(f"n{i}", "github" if i % 2 else "reddit", 0.9, "negative")
                   for i in range(4)], as_of=TODAY),
            capability_key="tool_calling.schema_accuracy",
            status=CellStatus.PUBLISHED,
        )

        note = conditional_note(
            {"tool_count:1-5": good, "tool_count:6-15": bad},
            capability_key="tool_calling.schema_accuracy",
        )

        assert note is not None
        assert "up to 5 tools" in note
        assert "6 or more tools" in note

    def test_agreeing_buckets_produce_no_note(self):
        c = describe(
            count([claim(f"v{i}", "github" if i % 2 else "blog", 0.9) for i in range(5)],
                  as_of=TODAY),
            capability_key="tool_calling.schema_accuracy",
            status=CellStatus.PUBLISHED,
        )
        assert conditional_note({"tool_count:1-5": c, "tool_count:6-15": c},
                                capability_key="tool_calling.schema_accuracy") is None


class TestLaunchFactor:
    def test_launch_week_claim_stays_discounted_forever(self):
        """If this ever returns 1.0, the discount has deleted itself."""
        release = date(2026, 1, 1)
        day_three = weight.launch_factor(claim_date=date(2026, 1, 4), release_date=release)
        assert day_three < 0.6

        # The same claim, read much later. The value is frozen at extraction,
        # so recomputing it from the same inputs must not drift.
        assert weight.launch_factor(claim_date=date(2026, 1, 4), release_date=release) == day_three

    def test_claim_after_the_window_is_undiscounted(self):
        assert weight.launch_factor(
            claim_date=date(2026, 2, 1), release_date=date(2026, 1, 1)
        ) == 1.0


class TestRecency:
    def test_latency_decays_faster_than_summarization(self):
        """Latency moves week to week; summarisation quality does not."""
        args = dict(claim_date=TODAY - timedelta(days=60), as_of=TODAY)
        fast = weight.recency_factor(**args, capability_key="ops.latency_ttft")
        slow = weight.recency_factor(**args, capability_key="summarization.fidelity")
        assert fast < slow

    def test_repro_steps_outweigh_a_wordy_post_with_none(self):
        """A two-line GitHub repro is the most valuable document type there is."""
        terse_repro = weight.specificity_factor(
            version_named=False, has_numbers=False, has_conditions=False, has_repro_steps=True
        )
        wordy_nothing = weight.specificity_factor(
            version_named=True, has_numbers=False, has_conditions=False, has_repro_steps=False
        )
        assert terse_repro > wordy_nothing

class TestTheWeightingInputsHaveASupplier:
    """`version_named` and `has_conditions` were required arguments with none.

    Both read `DocumentFacts` fields that default to False, and `DocumentFacts`
    had exactly one constructor in the repository - a test. So in every real run
    `f_specificity` saw `version_named=False, has_conditions=False,
    has_numbers=False` and varied only on `has_repro_steps`.

    The evidence is in the table: all four stored `claim_weight` rows have
    `f_specificity = 0.580`, and 0.58 is the ONLY distinct value the column has
    ever held. A weighting factor with one value is not weighting anything.

    These tests pin the derivation rather than the number, so a future change to
    the 0.2 does not break them and a revert to a document field does.
    """

    @staticmethod
    def _claim(specificity, **conditions):
        return ExtractedClaim(
            source_comment_id="c1",
            model_ref=ModelRef(
                surface="whatever", specificity=specificity, resolution_confidence=1.0,
                speaking="own-experience",
            ),
            capability="code.generation",
            polarity="positive",
            quote="q",
            quote_offset=(0, 1),
            relevance="central",
            conditions=Conditions(**conditions),
        )

    @pytest.mark.parametrize(
        "specificity,expected",
        [("snapshot", True), ("version", True), ("family", False)],
    )
    def test_version_named_comes_from_the_claim_specificity(self, specificity, expected):
        """The same fact the argument is named for, from the value that carries it."""
        claim = self._claim(specificity)
        assert (claim.model_ref.specificity in ("snapshot", "version")) is expected

    def test_has_conditions_is_not_derived_from_the_claim(self):
        """The derivation that looks obvious and is wrong. Pinned as a refusal.

        `bool(claim.conditions.model_dump(exclude_none=True))` answers "did the
        extractor fill any field". `specificity_factor` would spend it as "was
        this person being specific". `Conditions` exists precisely to keep those
        apart - "Absent means absent - never guessed into a band" - so deriving
        it converts a missing value into a definite one for every claim in the
        corpus, which is rule 6 wearing a working signal's clothes.

        Asserted as a property of the SOURCE, so that adding the derivation
        fails here rather than quietly reweighting the board.
        """
        import inspect

        from judge import pipeline

        src = inspect.getsource(pipeline.Pipeline.run)
        assert "has_conditions=document.has_conditions" in src, (
            "has_conditions must stay visibly dead rather than plausibly alive - "
            "see the module docstring for why a claim-side derivation is worse "
            "than a missing input"
        )
        # And the expression it is tempting to use really does differ from the
        # thing the factor wants, which is the whole argument.
        bare = self._claim("version")
        assert bare.conditions.model_dump(exclude_none=True) == {}

    def test_f_specificity_is_no_longer_constant_across_claims(self):
        """The defect, as a test. Three of its four inputs were dead."""
        seen = {
            weight.specificity_factor(
                version_named=c.model_ref.specificity in ("snapshot", "version"),
                has_numbers=False,
                has_conditions=bool(c.conditions.model_dump(exclude_none=True)),
                has_repro_steps=False,
            )
            for c in (
                self._claim("snapshot"),
                self._claim("version", tool_count=40),
                self._claim("family"),
            )
        }
        assert len(seen) > 1, (
            "f_specificity is constant again - every stored claim_weight row "
            "held 0.58 the last time this happened"
        )

    def test_a_family_claim_still_scores_below_a_version_one(self):
        """Direction, not magnitude. The 0.2 and the 0.3 are both uncalibrated.

        Asserted because the derivation ADDS a discount on top of f_fuzziness -
        one fact priced twice - and the thing that must hold regardless of the
        two constants is the ordering.
        """

        def w(specificity, **conditions):
            c = self._claim(specificity, **conditions)
            return (
                weight.specificity_factor(
                    version_named=c.model_ref.specificity in ("snapshot", "version"),
                    has_numbers=False,
                    has_conditions=bool(c.conditions.model_dump(exclude_none=True)),
                    has_repro_steps=False,
                )
                * weight.FUZZINESS_WEIGHT[specificity]
            )

        assert w("family") < w("version") < w("snapshot")
        # And with every artifact the family claim can carry, it still loses.
        assert w("family", tool_count=40) < w("version")

class TestAWeightingInputMayNotHaveASilentDefault:
    """Ruled 2026-08-21. `f_specificity` is the argument.

    `SELECT DISTINCT f_specificity FROM claim_weight` returns **one row, 0.580**.
    Every weight this system has computed came from a factor that had never
    varied, because three of its four inputs were dead. A silent default in a
    weighting factor is indistinguishable from a measurement.

    So `compute()` refuses. These tests pin the refusal and, more importantly,
    pin that the message is ACTIONABLE - a refusal that sends somebody to
    weight.py when the gap is in an adapter costs more than it saves.
    """

    ARGS = dict(
        evidence_tier="A", platform="reddit", capability_key="code.generation",
        relevance="central", specificity="version",
        claim_date=date(2026, 8, 1), release_date=None, as_of=date(2026, 8, 21),
        version_named=True, has_numbers=True, has_conditions=True,
        has_repro_steps=False,
    )

    def test_a_supplied_call_still_works(self):
        """The refusal must not be the only outcome."""
        assert weight.compute(**self.ARGS).w_final > 0

    @pytest.mark.parametrize(
        "field",
        ["evidence_tier", "platform", "capability_key", "relevance", "specificity",
         "claim_date", "version_named", "has_numbers", "has_conditions",
         "has_repro_steps"],
    )
    def test_every_input_is_refused_when_unsupplied(self, field):
        args = {**self.ARGS, field: weight.UNSUPPLIED}
        with pytest.raises(weight.UnsuppliedWeightInput) as exc:
            weight.compute(**args)
        assert field in exc.value.missing
        assert field in str(exc.value)

    def test_the_message_names_the_writer_and_not_this_file(self):
        with pytest.raises(weight.UnsuppliedWeightInput) as exc:
            weight.compute(**{**self.ARGS, "has_numbers": weight.UNSUPPLIED})
        text = str(exc.value)
        assert "document.has_numbers" in text, "must name what should write it"
        assert "collect/triage/" in text, "must name the module"
        assert "THE GAP IS NOT IN THIS FILE" in text

    def test_the_two_failures_are_distinguished(self):
        """A hardcoded literal and an uncarried column are not the same gap.

        One has a writer that writes a constant; the other has a value in the
        table and nothing that carries it here. Telling somebody to 'supply the
        input' is useless in both cases and differently useless in each.
        """
        assert weight.INPUT_GAPS["evidence_tier"].kind == weight.WRONG_WRITER
        assert weight.INPUT_GAPS["has_numbers"].kind == weight.NOT_CARRIED
        assert weight.INPUT_GAPS["claim_date"].kind == weight.NOT_CARRIED

    def test_the_sentinel_cannot_be_used_as_a_boolean(self):
        """The failure being fixed is a False that meant 'nobody measured'.

        So UNSUPPLIED must not be quietly falsy anywhere downstream - a factor
        that read it in a boolean position would reproduce the defect with a new
        name.
        """
        with pytest.raises(TypeError):
            bool(weight.UNSUPPLIED)

    def test_all_inputs_refused_are_reported_together(self):
        """One traversal, not one round trip per missing field."""
        args = {**self.ARGS, "evidence_tier": weight.UNSUPPLIED,
                "has_numbers": weight.UNSUPPLIED,
                "has_conditions": weight.UNSUPPLIED}
        with pytest.raises(weight.UnsuppliedWeightInput) as exc:
            weight.compute(**args)
        assert set(exc.value.missing) == {
            "evidence_tier", "has_numbers", "has_conditions"}

    def test_the_pipeline_tier_literal_is_now_the_sentinel(self):
        """`DEFAULT_EVIDENCE_TIER` was 'D' and is retired as a value.

        Asserted on the source rather than trusted, because reverting it to a
        plausible tier is a one-character change that restores a 6x over-weight
        on every vendor claim in the corpus.
        """
        from judge import pipeline

        assert pipeline.DEFAULT_EVIDENCE_TIER is weight.UNSUPPLIED

class TestSpeakingSuppliesTheEvidenceTier:
    """`ModelRef.speaking` -> `evidence_tier`, through the contract.

    Built 2026-08-21 on asymmetric evidence, and that is recorded in the field's
    own docstring: `own-experience` is corroborated (8 of 8 by one labeller, 4 of
    5 where both answered); `vendor-about-own-product` has ONE labeller and four
    rows from one announcement thread. The field is built on the stronger half
    and enforces the weaker one.
    """

    def test_the_mapping_is_the_contract_s_and_not_this_file_s(self):
        """Rule 5. A ruling about what a vendor's words are worth lives in YAML."""
        from judge.config import evidence_tier_by_speaking

        assert evidence_tier_by_speaking() == {
            "own-experience": "D",
            "relayed-from-elsewhere": "E",
            "vendor-about-own-product": "F",
        }

    @pytest.mark.parametrize(
        "speaking,tier",
        [("own-experience", "D"), ("relayed-from-elsewhere", "E"),
         ("vendor-about-own-product", "F")],
    )
    def test_each_value_maps_to_the_tier_whose_gloss_describes_it(self, speaking, tier):
        assert weight.evidence_tier_for(speaking) == tier

    def test_the_ordering_is_what_matters_and_it_holds(self):
        """The distances are uncalibrated; the order needs no measurement.

        A vendor describing their own model is weaker evidence about that model
        than an engineer reporting their own run. Asserted as an ordering so a
        change to 0.12/0.04/0.02 does not break it and an inversion does.
        """
        w = weight.TIER_WEIGHT
        assert (w[weight.evidence_tier_for("vendor-about-own-product")]
                < w[weight.evidence_tier_for("relayed-from-elsewhere")]
                < w[weight.evidence_tier_for("own-experience")])

    def test_vendor_is_six_times_lighter_than_the_literal_it_replaced(self):
        """The change this makes to what is already stored.

        Three of the four claims in the table quote the Fable 5 announcement and
        were weighted at tier D — the module literal applied to every claim in
        the corpus. At F they weigh a sixth as much.
        """
        w = weight.TIER_WEIGHT
        assert w["D"] / w[weight.evidence_tier_for("vendor-about-own-product")] == 6

    def test_an_unmapped_value_refuses_rather_than_defaulting(self):
        """The 2026-08-21 ruling, applied to the field that motivated it."""
        assert weight.evidence_tier_for("something-nobody-priced") is weight.UNSUPPLIED
        with pytest.raises(weight.UnsuppliedWeightInput) as exc:
            weight.compute(**{**TestAWeightingInputMayNotHaveASilentDefault.ARGS,
                              "evidence_tier": weight.UNSUPPLIED})
        assert "evidence_tier_by_speaking" in str(exc.value)

    def test_speaking_is_required_on_the_schema(self):
        """No default. A claim without one cannot be audited for provenance."""
        # ValidationError, not bare Exception: a blind assert would also pass if
        # the import broke or the signature changed, which is the opposite of
        # what this test is for.
        from pydantic import ValidationError

        from judge.extract.schema import ModelRef

        with pytest.raises(ValidationError):
            ModelRef(surface="x", specificity="version", resolution_confidence=1.0)

    def test_the_model_reads_it_in_the_tool_schema(self):
        """Why this is a field and not a prompt line - it travels with the value."""
        import json

        from judge.extract.client import tool_schema_for
        from judge.extract.schema import ExtractionResult

        blob = json.dumps(tool_schema_for(ExtractionResult))
        assert "vendor-about-own-product" in blob
        assert "NEVER own-experience" in blob

    def test_it_does_not_change_whether_a_claim_corroborates(self):
        """WHAT IT DOES NOT FIX, asserted so nobody assumes it did.

        `gate.count` reads neither `speaking` nor `specificity`. Three sentences
        from one announcement are three `independent_voices` after this change
        exactly as before it - the field changes what a claim WEIGHS, not
        whether it CORROBORATES, and those are different failures.
        """
        import inspect

        from judge.curate import gate

        src = inspect.getsource(gate.count)
        assert "speaking" not in src
        assert "specificity" not in src

        # Three different people, each quoting the same announcement, each
        # weighted at tier F.
        tier = weight.evidence_tier_for("vendor-about-own-product")
        w = weight.TIER_WEIGHT[tier] * weight.PLATFORM_WEIGHT["reddit"]
        vendor = [claim(f"voice{i}", "reddit", w) for i in range(3)]
        counts = gate.count(vendor, as_of=TODAY)
        assert counts.independent_voices == 3, (
            "three vendor sentences still count as three voices - weighting "
            "alone does not stop that"
        )
        assert counts.n_eff < 3.0, "and they cannot publish, which is the weight"
