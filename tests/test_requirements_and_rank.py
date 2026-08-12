"""Q3 requirement inference, Q5 gating, Q6 cost, Q7 ranking.

The behaviours pinned here are the ones the spec is emphatic about: silent vs
loud failure, dropping requirements you do not have, capability before cost,
and never mixing "no evidence" into the ranked list.
"""

from __future__ import annotations

from judge.ask import requirements
from judge.ask.cost import CostEstimate, Pricing, Workload, estimate, monthly_saving
from judge.ask.profile import Role, TaskProfile
from judge.ask.rank import Band, Candidate, CellView, DisqualifyReason, band_for, gate, guard_for, rank
from judge.curate.gate import CellStatus

SUMMARISE = (
    "summarize incoming support tickets into weekly themes, "
    "20k tickets a day, output must be valid JSON, internal tool"
)


class TestCapabilityInference:
    def test_summarise_gates_on_summarisation(self):
        req = requirements.infer(SUMMARISE)
        keys = {c.key for c in req.capabilities}
        assert "summarization.fidelity" in keys
        assert "format.structured_output" in keys

    def test_edit_gates_on_diff_fidelity_not_generation(self):
        """Cheap models write fine code and cannot emit a clean diff."""
        req = requirements.infer("refactor the file and apply the patch")
        keys = {c.key for c in req.capabilities}
        assert "code.editing_diff_fidelity" in keys
        assert "code.generation" not in keys

    def test_classification_is_the_cheapest_role(self):
        req = requirements.infer("classify each ticket into one of six buckets")
        assert {c.key for c in req.capabilities} == {"instruction.adherence"}

    def test_internal_tool_is_not_a_tool_call(self):
        """"an internal tool" describes the product, not a role that calls anything.

        Gating on tool calling here would exclude models over a requirement the
        task does not have — the exact overpayment we are trying to avoid.
        """
        req = requirements.infer(SUMMARISE)
        assert not any(c.key.startswith("tool_calling") for c in req.capabilities)
        assert not req.hard.needs_tools
        assert any("tool calling" in d for d in req.dropped_constraints)

    def test_real_tool_use_still_triggers(self):
        for phrase in (
            "calls the API to fetch order status",
            "uses tools to look up the customer",
            "function calling against 4 endpoints",
            "the agent has 12 tools",
        ):
            req = requirements.infer(phrase)
            assert any(
                c.key.startswith("tool_calling") for c in req.capabilities
            ), f"{phrase!r} should gate on tool calling"

    def test_many_tools_raises_long_chain_reliability(self):
        req = requirements.infer("call the API to look things up", tool_count=12)
        keys = {c.key for c in req.capabilities}
        assert "tool_calling.long_chain_reliability" in keys
        need = next(c for c in req.capabilities if c.key.startswith("tool_calling"))
        assert need.condition_bucket == "tool_count:6-15"

    def test_condition_bucket_uses_the_dominant_dimension(self):
        req = requirements.infer(SUMMARISE, input_tokens=20_000)
        need = next(c for c in req.capabilities if c.key == "summarization.fidelity")
        assert need.condition_bucket == "context_size:8k-32k"


class TestFailureMode:
    def test_summarisation_is_silent_and_needs_positive_consensus(self):
        req = requirements.infer(SUMMARISE)
        assert "summarization.fidelity" in req.silent_failure_capabilities

    def test_structured_output_is_loud(self):
        req = requirements.infer("return valid JSON matching this schema")
        need = next(c for c in req.capabilities if c.key == "format.structured_output")
        assert not need.requires_positive_consensus


class TestErrorCost:
    def test_a_write_is_irreversible(self):
        req = requirements.infer("reads the ticket then places the order")
        assert req.error_cost == "irreversible"
        assert req.suppress_unevidenced

    def test_customer_facing_is_detected(self):
        req = requirements.infer("draft a reply that is sent to customers")
        assert req.error_cost == "customer-facing"

    def test_default_is_internal_and_stated_as_an_assumption(self):
        req = requirements.infer("summarize the tickets")
        assert req.error_cost == "internal"
        assert any(a.field == "error_cost" for a in req.assumptions)


class TestDroppedConstraints:
    def test_small_input_drops_the_context_requirement(self):
        """The most common way to overpay is carrying a requirement you don't have."""
        req = requirements.infer(SUMMARISE, input_tokens=20_000)
        assert any("long context" in d for d in req.dropped_constraints)

    def test_no_tools_is_named_explicitly(self):
        req = requirements.infer("summarize the tickets")
        assert any("tool calling" in d for d in req.dropped_constraints)

    def test_batch_work_drops_latency(self):
        req = requirements.infer("nightly batch job that summarizes tickets")
        assert any("latency" in d for d in req.dropped_constraints)
        assert req.cost_dominates


class TestAssumptionsAreVisible:
    def test_unstated_input_size_becomes_an_editable_assumption(self):
        req = requirements.infer("summarize the tickets")
        guess = next(a for a in req.assumptions if a.field == "input_tokens")
        assert guess.editable


class TestComplexityTier:
    def test_fixed_label_output_is_cheap_leaning(self):
        assert requirements.complexity_tier(
            "classify into one of six labels", input_tokens=800,
            output_tokens=10, tool_count=None
        ) <= 2

    def test_specialist_multi_step_is_expensive_leaning(self):
        assert requirements.complexity_tier(
            "plan a multi-step clinical review with judgement about tone",
            input_tokens=150_000, output_tokens=4_000, tool_count=8,
        ) >= 4


def cell(cap: str, bucket: str, direction: str, *, voices=6, positive=6, negative=0,
         status=CellStatus.PUBLISHED, pessimistic=None) -> CellView:
    return CellView(
        capability_key=cap,
        condition_bucket=bucket,
        status=status,
        direction=direction,
        consensus_phrase=f"{'Widely praised' if direction == 'positive' else 'Repeatedly criticised'} for {cap}",
        voices=voices,
        positive=positive,
        negative=negative,
        quote_ids=[f"q_{cap}_{i}" for i in range(voices)],
        pessimistic_direction=pessimistic,
    )


class TestEvidenceGate:
    def test_absence_of_criticism_does_not_clear_a_silent_capability(self):
        """The rule that stops "nobody complained" being read as evidence."""
        req = requirements.infer(SUMMARISE, input_tokens=20_000)
        cells = {
            ("summarization.fidelity", "context_size:8k-32k"):
                cell("summarization.fidelity", "context_size:8k-32k", "positive",
                     voices=6, positive=0, negative=0),
        }
        verdicts = gate(req, cells)
        summ = next(v for v in verdicts if v.need.key == "summarization.fidelity")
        assert not summ.passed
        assert "fails silently" in summ.reason

    def test_contested_qualifies_only_on_the_pessimistic_branch(self):
        req = requirements.infer("classify each ticket", input_tokens=1_000)
        key = ("instruction.adherence", "context_size:<8k")
        optimistic = {key: cell(*key, "positive", status=CellStatus.CONTESTED,
                                pessimistic="negative")}
        assert not gate(req, optimistic)[0].passed

    def test_possibly_changed_drops_every_capability(self):
        req = requirements.infer(SUMMARISE, input_tokens=20_000)
        verdicts = gate(req, {}, possibly_changed=True)
        assert all(not v.passed for v in verdicts)
        assert "may have changed" in verdicts[0].reason


class TestBanding:
    def _req(self):
        return requirements.infer("classify each ticket", input_tokens=1_000)

    def test_unevidenced_is_not_rejected(self):
        req = self._req()
        c = Candidate("m", "M", verdicts=gate(req, {}))
        band, reason = band_for(c, req)
        assert band is Band.NO_EVIDENCE
        assert reason is None

    def test_unevidenced_is_suppressed_when_irreversible(self):
        req = requirements.infer("classify then delete the record", input_tokens=1_000)
        c = Candidate("m", "M", verdicts=gate(req, {}))
        band, reason = band_for(c, req)
        assert band is Band.DOESNT_QUALIFY
        assert reason is DisqualifyReason.SILENT_CAPABILITY_UNPROVEN

    def test_criticised_is_rejected(self):
        req = self._req()
        key = ("instruction.adherence", "context_size:<8k")
        cells = {key: cell(*key, "negative", positive=0, negative=6)}
        c = Candidate("m", "M", verdicts=gate(req, cells))
        assert band_for(c, req)[0] is Band.DOESNT_QUALIFY


class TestRanking:
    def _qualified(self, name: str, cost: float, voices: int) -> Candidate:
        req = requirements.infer("classify each ticket", input_tokens=1_000)
        key = ("instruction.adherence", "context_size:<8k")
        cells = {key: cell(*key, "positive", voices=voices, positive=voices)}
        c = Candidate(
            name, name,
            cost=CostEstimate(per_call=cost, per_request=cost, monthly=cost * 1000),
            verdicts=gate(req, cells),
        )
        c.band = band_for(c, req)[0]
        return c

    def test_cheapest_qualified_is_recommended(self):
        ranked = rank([self._qualified("pricey", 0.01, 6), self._qualified("cheap", 0.001, 6)])
        assert ranked[0].model_version_id == "cheap"
        assert ranked[0].band is Band.RECOMMENDED
        assert ranked[1].band is Band.ALSO_WORKS

    def test_cost_never_promotes_a_rejected_model(self):
        """Capability filters; cost only breaks ties among survivors."""
        req = requirements.infer("classify each ticket", input_tokens=1_000)
        key = ("instruction.adherence", "context_size:<8k")
        cheap_bad = Candidate(
            "cheap_bad", "Cheap but criticised",
            cost=CostEstimate(0.0001, 0.0001, 0.1),
            verdicts=gate(req, {key: cell(*key, "negative", positive=0, negative=6)}),
        )
        cheap_bad.band = band_for(cheap_bad, req)[0]

        ranked = rank([cheap_bad, self._qualified("good", 0.05, 6)])
        assert ranked[0].model_version_id == "good"
        assert ranked[-1].model_version_id == "cheap_bad"

    def test_unevidenced_never_lands_above_a_qualified_model(self):
        req = requirements.infer("classify each ticket", input_tokens=1_000)
        unknown = Candidate("unknown", "Unknown",
                            cost=CostEstimate(0.00001, 0.00001, 0.01),
                            verdicts=gate(req, {}))
        unknown.band = band_for(unknown, req)[0]

        ranked = rank([unknown, self._qualified("known", 0.05, 6)])
        assert ranked[0].band is Band.RECOMMENDED
        assert ranked[1].band is Band.NO_EVIDENCE


class TestCost:
    PRICING = Pricing(price_in=0.075, price_out=0.30)

    def test_runs_per_request_multiplies_exactly_once(self):
        """A role-scoped volume arriving here would report 10x at 100x."""
        w = Workload(input_tokens=20_000, output_tokens=1_000,
                     runs_per_request=10, requests_per_month=600_000)
        e = estimate(pricing=self.PRICING, workload=w)
        assert e.per_request == e.per_call * 10
        assert e.monthly == e.per_request * 600_000

    def test_verbosity_can_reverse_the_ordering(self):
        cheap_wordy = estimate(
            pricing=Pricing(price_in=0.05, price_out=0.20),
            workload=Workload(input_tokens=1_000, output_tokens=1_000),
            verbosity_multiplier=4.0,
        )
        dearer_terse = estimate(
            pricing=Pricing(price_in=0.10, price_out=0.40),
            workload=Workload(input_tokens=1_000, output_tokens=1_000),
            verbosity_multiplier=1.0,
        )
        assert cheap_wordy.per_call > dearer_terse.per_call

    def test_unknown_multipliers_are_declared_not_hidden(self):
        e = estimate(pricing=self.PRICING,
                     workload=Workload(input_tokens=1_000, output_tokens=100))
        assert any("verbosity" in c for c in e.caveats)
        assert any("retry" in c for c in e.caveats)

    def test_saving_is_never_negative(self):
        cheap = CostEstimate(0.001, 0.001, 100.0)
        dear = CostEstimate(0.01, 0.01, 1000.0)
        assert monthly_saving(current=cheap, candidate=dear) == 0.0


class TestLeverageOrdering:
    def test_high_frequency_role_sorts_first(self):
        """Where the money is, and invisible without decomposing the brief."""
        profile = TaskProfile(
            raw_text="research assistant",
            roles=[
                Role(name="synthesizer", runs_per_request=1),
                Role(name="page-summarizer", runs_per_request=10),
            ],
            requests_per_month=100_000,
        )
        ordered = profile.ordered_by_leverage(
            {"synthesizer": 50.0, "page-summarizer": 400.0}
        )
        assert ordered[0].name == "page-summarizer"


class TestGuards:
    def test_silent_failure_gets_a_sampling_queue_not_a_retry(self):
        """A validation retry catches nothing when a summary quietly omits a fact."""
        guard = guard_for(requirements.infer(SUMMARISE, input_tokens=20_000))
        assert guard and "review queue" in guard

    def test_loud_failure_gets_validation_and_retry(self):
        guard = guard_for(requirements.infer("return valid JSON", input_tokens=1_000))
        assert guard and "retry" in guard
