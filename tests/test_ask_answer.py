"""Q4-Q7 over real cells, and the last orphan wired.

`gate()`, `rank()` and `AnswerStore` were each built, tested and correct.
Nothing joined them, so the ranking logic had no evidence and the store had no
caller. This is the join.
"""

from __future__ import annotations

from judge.ask.answer import BAND_TO_STORED, CellReader, answer_for
from judge.ask.rank import Band
from judge.ask.requirements import infer


class Conn:
    def __init__(self, rows=()):
        self._rows, self.sql, self.params = list(rows), [], []

    @property
    def writes(self):
        return [s for s in self.sql if s.strip().upper().startswith("INSERT")]

    def execute(self, sql, params=()):
        self.sql.append(sql)
        self.params.append(params)
        rows = self._rows if not sql.strip().upper().startswith("INSERT") else []

        class R:
            @staticmethod
            def fetchall():
                return rows

        return R()


def a_cell_row(
    mv="mv1",
    cap="format.structured_output",
    bucket="any",
    status="published",
    voices=4,
    pos=4,
    neg=0,
    phrase="holds up",
):
    return (mv, cap, bucket, status, voices, pos, neg, phrase, ["q1", "q2"])


REQ = infer("emit valid JSON for an internal tool")


class TestEveryModelAskedAboutComesBack:
    """A candidate filtered out here is a question FR-36 can no longer answer."""

    def test_a_model_with_no_cells_is_returned_as_no_evidence(self):
        answer = answer_for(
            Conn(rows=[]), role_id="rl1", requirement=REQ, model_version_ids=["mv1", "mv2"]
        )
        assert {c.model_version_id for c in answer.candidates} == {"mv1", "mv2"}
        assert all(c.band == "no_evidence" for c in answer.candidates)

    def test_asking_about_nothing_reads_no_cells_but_still_records_the_answer(self):
        """This asserted `conn.sql == []` and broke once answers were
        persisted - correctly. Reading no cells and writing nothing at all are
        different claims, and only the first was ever the point: an abstention
        over zero models is still an answer somebody may ask about later.
        """
        conn = Conn()
        result = answer_for(conn, role_id="rl1", requirement=REQ, model_version_ids=[])

        assert not any("cell_current" in s for s in conn.sql)
        assert result.abstained
        assert any("INSERT INTO answer" in s for s in conn.writes)


class TestItReadsOnlyPublishedCells:
    def test_the_view_is_cell_current_not_cell(self):
        """`insufficient` must not reach a recommendation. A cell that did not
        clear the gate is evidence something was said, not evidence of what."""
        conn = Conn(rows=[])
        answer_for(conn, role_id="rl1", requirement=REQ, model_version_ids=["mv1"])
        assert "cell_current" in conn.sql[0]

    def test_one_models_cell_cannot_answer_for_another(self):
        """`gate` keys on (capability, bucket) and reads one model at a time.
        A flattened dict shared across models would let mv1's evidence qualify
        mv2, which is the worst thing this function could do quietly."""
        cells = CellReader(Conn(rows=[a_cell_row("mv1"), a_cell_row("mv2")])).cells_for(
            ["mv1", "mv2"]
        )
        assert set(cells) == {"mv1", "mv2"}
        assert all(isinstance(v, dict) for v in cells.values())


class TestAbstainingNamesWhatIsMissing:
    """FR-35. An empty ranked list and a refusal to answer look identical to a
    caller and mean different things."""

    def test_no_qualifying_model_abstains_rather_than_returning_nothing(self):
        answer = answer_for(
            Conn(rows=[]), role_id="rl1", requirement=REQ, model_version_ids=["mv1"]
        )
        assert answer.abstained
        assert answer.reason

    def test_the_reason_names_the_capability(self):
        answer = answer_for(
            Conn(rows=[]), role_id="rl1", requirement=REQ, model_version_ids=["mv1"]
        )
        assert any(need.key in answer.reason for need in REQ.capabilities)

    def test_it_says_absence_of_reports_rather_than_reported_failure(self):
        """Rule 4 at the point a user actually reads it."""
        answer = answer_for(
            Conn(rows=[]), role_id="rl1", requirement=REQ, model_version_ids=["mv1"]
        )
        assert "absence of reports rather than a report of failure" in answer.reason

    def test_the_rejected_candidates_are_still_stored_on_an_abstention(self):
        """Abstaining is not a reason to forget what was considered."""
        answer = answer_for(
            Conn(rows=[]), role_id="rl1", requirement=REQ, model_version_ids=["mv1", "mv2"]
        )
        assert len(answer.candidates) == 2
        assert answer.why_not("mv2") is not None


class TestTheJustificationIsAssembledNotWritten:
    """Rules 2 and 3. This is exactly where a model would invent a persuasive
    sentence nobody can check."""

    def test_nothing_in_the_module_calls_a_model(self):
        import inspect

        import judge.ask.answer as mod

        source = inspect.getsource(mod)
        for llm in ("OpenRouterClient", "client.complete", "understand("):
            assert llm not in source, f"the answer path reaches a model via {llm}"

    def test_a_no_evidence_candidate_says_nobody_reported(self):
        answer = answer_for(
            Conn(rows=[]), role_id="rl1", requirement=REQ, model_version_ids=["mv1"]
        )
        assert "Nobody has reported" in answer.candidates[0].reason


class TestTheBandVocabularyIsExplicit:
    def test_every_band_maps_to_a_stored_value(self):
        """A rename in one vocabulary must not silently change what a stored
        answer means to a page reading it a month later."""
        assert set(BAND_TO_STORED) == set(Band)

    def test_the_stored_values_are_the_ones_the_store_understands(self):
        assert set(BAND_TO_STORED.values()) == {
            "recommended",
            "qualified",
            "rejected",
            "no_evidence",
        }


class TestTheAnswerIsStoredBeforeItIsReturned:
    """The last orphan, and I nearly declared it fixed on a docstring.

    `grep -rl AnswerStore judge` returned this module because the module
    docstring MENTIONS it. That is the fourth time in one session a substring
    check matched my own prose - after "complete" in "completeness", "commit"
    in "never commits", and "localhost" in a comment about not defaulting to
    localhost. So this test asserts on the CALL.
    """

    def test_answer_for_writes_the_answer(self):
        conn = Conn(rows=[])
        answer_for(conn, role_id="rl1", requirement=REQ, model_version_ids=["mv1"])

        assert any("INSERT INTO answer" in s for s in conn.writes), (
            "the answer was returned and never stored, so 'why not X?' has nothing to read"
        )

    def test_an_abstention_is_stored_too(self):
        """Abstaining is an answer. A question about it is as legitimate as a
        question about a recommendation."""
        conn = Conn(rows=[])
        result = answer_for(conn, role_id="rl1", requirement=REQ, model_version_ids=["mv1"])

        assert result.abstained
        assert any("INSERT INTO answer" in s for s in conn.writes)

    def test_the_store_is_reached_by_call_not_by_mention(self):
        import inspect

        import judge.ask.answer as mod

        code = inspect.getsource(mod.answer_for)
        assert "AnswerStore(conn).write_answer(" in inspect.getsource(mod)
        assert "persisted(" in code

    def test_nothing_here_commits(self):
        """The caller owns the transaction, so a stored answer and whatever
        else the request wrote land together or not at all."""
        import inspect

        import judge.ask.answer as mod

        assert ".commit()" not in inspect.getsource(mod)
