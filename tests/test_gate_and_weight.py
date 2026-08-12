"""The publication gate arithmetic, and the weight factors that feed it.

The gate is where fake precision would enter if anywhere. These tests pin the
arithmetic that makes `n_eff >= 3.0` mean what the spec says it means.
"""

from __future__ import annotations

from datetime import date, timedelta

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
