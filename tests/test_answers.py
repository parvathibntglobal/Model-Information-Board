"""The answer path's memory, and the query it exists to make answerable.

"Why not X?" is answerable only if the answer remembered X. Storing the winner
alone turns every such question into a re-computation against today's cells -
which have moved - so the honest reply becomes "here is what I would say now"
rather than "here is why I said that". Only the second is accountable.
"""

from __future__ import annotations

import json

import pytest

from judge.store.answers import Answer, AnswerStore, Candidate


class Conn:
    def __init__(self, row=None):
        self._row, self.sql, self.params = row, [], []

    def execute(self, sql, params=()):
        self.sql.append(sql)
        self.params.append(params)
        row = self._row

        class R:
            @staticmethod
            def fetchone():
                return row

        return R()


def candidate(mv="mv1", band="recommended", reason="four engineers report it holds", **kw):
    defaults = dict(
        model_version_id=mv,
        band=band,
        reason=reason,
        cost_per_task=0.002,
        quote_ids=("q1", "q2"),
    )
    defaults.update(kw)
    return Candidate(**defaults)


class TestWhyNotIsAnswerable:
    """FR-36. The whole reason rejected candidates are stored."""

    def test_a_rejected_model_is_kept_with_its_reason(self):
        answer = Answer(
            role_id="rl1",
            candidates=(
                candidate("mv1"),
                candidate("mv2", band="rejected", reason="schema failures above 6 tools"),
            ),
        )
        rejected = answer.why_not("mv2")

        assert rejected is not None
        assert rejected.reason == "schema failures above 6 tools"
        assert rejected.quote_ids

    def test_never_considered_is_a_different_answer_from_rejected(self):
        """The caller must be able to tell them apart. "We looked and said no"
        and "it was never in the list" need opposite follow-ups."""
        answer = Answer(role_id="rl1", candidates=(candidate("mv1"),))

        assert answer.why_not("mv9") is None
        assert answer.why_not("mv1") is not None

    def test_unevidenced_candidates_are_kept_out_of_the_ranking_but_not_hidden(self):
        """Hiding unproven models makes the board conservative in a way that
        quietly costs money - they are disproportionately the cheap ones."""
        answer = Answer(
            role_id="rl1",
            candidates=(
                candidate("mv1"),
                candidate("mv2", band="no_evidence", reason="nobody has reported", quote_ids=()),
            ),
        )
        assert [c.model_version_id for c in answer.recommended] == ["mv1"]
        assert [c.model_version_id for c in answer.unevidenced] == ["mv2"]


class TestAnAbstentionIsAResult:
    """FR-35. Declining is an answer; declining without saying why is a bug."""

    def test_abstaining_without_a_reason_is_refused(self):
        with pytest.raises(ValueError, match="must name what is missing"):
            Answer(role_id="rl1", abstained=True)

    def test_abstaining_with_a_reason_is_valid_and_needs_no_candidates(self):
        answer = Answer(
            role_id="rl1",
            abstained=True,
            reason="no model has reported evidence on summarization.fidelity",
        )
        assert answer.abstained
        assert answer.candidates == ()

    def test_answering_with_no_candidates_and_no_abstention_is_refused(self):
        """Says nothing while claiming to have answered."""
        with pytest.raises(ValueError, match="says nothing"):
            Answer(role_id="rl1")


class TestEveryJustificationIsBoundToAQuote:
    """FR-34, and the place a model would otherwise invent a rationale."""

    def test_a_reasoned_rejection_without_quotes_is_refused_at_write(self):
        answer = Answer(
            role_id="rl1",
            candidates=(candidate("mv2", band="rejected", reason="it is bad", quote_ids=()),),
        )
        with pytest.raises(ValueError, match="no quote behind it"):
            AnswerStore(Conn()).write_answer(answer)

    def test_a_no_evidence_band_needs_no_quotes(self):
        """ "Engineers report it failing" and "nobody has reported on it" are
        opposite rejections, and only the first has anything to cite."""
        answer = Answer(
            role_id="rl1",
            candidates=(
                candidate("mv2", band="no_evidence", reason="nobody has reported", quote_ids=()),
            ),
        )
        assert AnswerStore(Conn()).write_answer(answer)

    def test_the_quote_ids_are_stored_beside_the_reason(self):
        conn = Conn()
        AnswerStore(conn).write_answer(Answer(role_id="rl1", candidates=(candidate(),)))

        stored = json.loads(conn.params[0][2])[0]
        assert stored["reason"]
        assert stored["quote_ids"] == ["q1", "q2"]


class TestTheOutcomeIsTheOnlyThingThatMatters:
    def test_an_unreported_outcome_is_not_a_failure(self):
        """Rule 6 on the figure the project is judged on. Counting an
        unmeasured outcome as either result manufactures the number."""
        conn = Conn(row=(3, 5, 40))
        held, measured, adopted = AnswerStore(conn).held_rate()

        assert (held, measured, adopted) == (3, 5, 40)

    def test_the_rate_is_three_numbers_rather_than_a_percentage(self):
        """ "90% held" over ten measured out of four hundred adopted has said
        almost nothing, and one figure hides which of those it is."""
        result = AnswerStore(Conn(row=(9, 10, 400))).held_rate()
        assert len(result) == 3

    def test_naming_a_model_on_an_unadopted_recommendation_is_refused(self):
        """Which model they did NOT use is a different fact from which they
        used, and storing it here would inflate the adoption count."""
        with pytest.raises(ValueError, match="did not use"):
            AnswerStore(Conn()).record_outcome(
                answer_id="ans1", adopted=False, model_version_id="mv1"
            )

    def test_an_adopted_outcome_records_what_happened(self):
        conn = Conn()
        AnswerStore(conn).record_outcome(
            answer_id="ans1", adopted=True, model_version_id="mv1", success=True
        )
        assert "INSERT INTO outcome" in conn.sql[0]
        assert "ON CONFLICT" in conn.sql[0]


class TestWhatWasGuessedIsRecorded:
    def test_inferred_fields_are_stored_rather_than_derived_later(self):
        """Which fields the USER stated and which we filled in is not
        recoverable from the finished profile, and it is the difference
        between a recommendation they confirmed and one we assembled."""
        conn = Conn()
        AnswerStore(conn).write_profile(
            raw_text="summarise tickets",
            profile={"raw_text": "summarise tickets"},
            inferred_fields=("requests_per_month", "tool_count"),
        )
        assert conn.params[0][-1] == ["requests_per_month", "tool_count"]

    def test_the_profile_id_is_derived_not_clocked(self):
        conn = Conn()
        store = AnswerStore(conn)
        first = store.write_profile(raw_text="x", profile={"a": 1}, inferred_fields=())
        second = store.write_profile(raw_text="x", profile={"a": 1}, inferred_fields=())
        assert first == second


class TestTheStoreNeverCommits:
    def test_the_caller_owns_the_transaction(self):
        import inspect

        assert ".commit()" not in inspect.getsource(AnswerStore)
