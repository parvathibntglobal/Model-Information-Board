"""One shared $1/day across both LLM stages, and the wiring that makes it true.

The requirement is a single daily cap covering extraction and the ask box
together. The code had two in-memory totals reading the same environment
variable, so each stage got its own dollar and the real ceiling was $2. The
first class here is the assertion that would have caught that; the rest guard
the honesty properties a spend chart needs.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta

import pytest

from judge import spend_ledger
from judge.ask import spend
from judge.extract.budget import BudgetExhausted

MODEL = "google/gemini-2.5-flash"
#: The measured call: 2,010 in / 589 out -> $0.00208.
CALL = dict(model=MODEL, input_tokens=2010, output_tokens=589)


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "spend-ledger.jsonl"
    monkeypatch.setenv(spend_ledger.LEDGER_PATH_ENV, str(path))
    return path


class TestTheDollarIsSharedNotPerStage:
    """THE REQUIREMENT, and the assertion the old design fails.

    Two in-memory totals reading one variable is indistinguishable from a shared
    cap until you spend from both, which is why no existing test saw it.
    """

    def test_extraction_spend_reduces_what_the_ask_box_may_spend(self, ledger):
        spend.reset_for_test(limit_usd=1.00)

        # A nightly batch burns almost the whole day's dollar. 481 calls at the
        # measured $0.002076 is $0.99856, so the batch itself fits and the NEXT
        # call - whichever stage makes it - does not.
        for _ in range(481):
            spend_ledger.record(stage=spend_ledger.STAGE_EXTRACT, **CALL)

        spent = spend_ledger.spent_today()
        assert 0.99 <= spent <= 1.00, spent

        # The ask box must now be refused, even though ITS OWN counter is zero.
        with pytest.raises(BudgetExhausted):
            spend.check_before_call()

    def test_the_ask_box_alone_can_still_exhaust_the_shared_cap(self, ledger):
        spend.reset_for_test(limit_usd=0.01)
        for _ in range(6):
            spend_ledger.record(stage=spend_ledger.STAGE_ASK, **CALL)

        with pytest.raises(BudgetExhausted):
            spend.check_before_call()

    def test_a_fresh_process_sees_spend_it_did_not_make(self, ledger):
        """What the in-memory total could never do: survive a restart.

        `reset_for_test` stands in for a new process - the module total is zero
        and the cap must still bind from the ledger alone.
        """
        for _ in range(400):
            spend_ledger.record(stage=spend_ledger.STAGE_EXTRACT, **CALL)

        spend.reset_for_test(limit_usd=0.50)          # a brand new process
        assert spend.spent_usd() > 0.49, "a restart zeroed the shared total"
        with pytest.raises(BudgetExhausted):
            spend.check_before_call()


class TestBothStagesActuallyRecord:
    """A chart with a series nothing writes to is worse than no chart.

    Structural, because the failure this repo produces most is a writer that
    exists and is never called - and a flat `ask` line looks exactly like a
    quiet day.
    """

    def _code(self, path: str) -> str:
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        # Comments and docstrings stripped: both files DISCUSS the other stage
        # while explaining the shared cap, and a raw substring check matches the
        # prose rather than the call.
        source = re.sub(r'"""[\s\S]*?"""', "", source)
        return re.sub(r"#.*", "", source)

    def test_the_extraction_path_records(self):
        code = self._code("judge/pipeline.py")
        assert "spend_ledger.record(" in code
        assert "STAGE_EXTRACT" in code

    def test_the_ask_path_records(self):
        code = self._code("judge/ask/spend.py")
        assert "spend_ledger.record(" in code
        assert "STAGE_ASK" in code

    def test_the_extraction_record_is_not_inside_the_budget_branch(self):
        """Recorded even with no `Budget`, because the pot is shared.

        A call the batch declined to record is a call the ask box is then
        allowed to make on top of it.
        """
        code = self._code("judge/pipeline.py")
        after = code.split("spend_ledger.record(")[0]
        tail = after.rstrip().splitlines()[-1]
        assert "if budget is not None" not in tail

    def test_a_third_stage_is_refused(self):
        """Rule 2 permits two. A third caller is a violation, not a new series."""
        with pytest.raises(ValueError, match="permitted to call a model"):
            spend_ledger.record(stage="curate", **CALL)


class TestZeroAndNeverAreDifferent:
    def test_a_stage_that_never_recorded_is_named_as_unwired(self, ledger):
        spend_ledger.record(stage=spend_ledger.STAGE_EXTRACT, **CALL)
        report = spend_ledger.report(daily_cap_usd=1.0, estimated_call_usd=0.00208)

        assert report.unwired_stages == (spend_ledger.STAGE_ASK,)
        assert report.by_stage_usd.get(spend_ledger.STAGE_ASK, 0.0) == 0.0

    def test_a_stage_that_recorded_and_spent_nothing_is_not_unwired(self, ledger):
        """An unmetered call still proves the wiring works."""
        spend_ledger.record(stage=spend_ledger.STAGE_EXTRACT, **CALL)
        spend_ledger.record(stage=spend_ledger.STAGE_ASK, model=MODEL,
                            input_tokens=0, output_tokens=0)
        report = spend_ledger.report(daily_cap_usd=1.0, estimated_call_usd=0.00208)

        assert report.unwired_stages == ()
        assert report.unmetered_today == 1

    def test_an_empty_ledger_reports_a_partial_window_rather_than_a_clean_bill(self, ledger):
        report = spend_ledger.report(daily_cap_usd=1.0, estimated_call_usd=0.00208)

        assert report.spent_today_usd == 0.0
        assert report.first_seen_at is None
        assert report.covers_whole_window is False, "no rows must not read as full coverage"

    def test_a_window_beginning_before_the_first_row_is_a_floor(self, ledger):
        now = datetime.now(UTC)
        spend_ledger.record(stage=spend_ledger.STAGE_ASK, at=now, **CALL)
        report = spend_ledger.report(daily_cap_usd=1.0, estimated_call_usd=0.00208, now=now)

        assert report.covers_whole_window is False

    def test_a_rate_with_no_window_is_None_rather_than_zero(self, ledger):
        report = spend_ledger.report(
            daily_cap_usd=1.0, estimated_call_usd=0.00208, hours=0
        )
        assert report.usd_per_hour_recent is None
        assert report.hours_to_cap is None


class TestTheArithmeticAndTheBoundary:
    def test_cost_comes_from_the_seeded_price(self, ledger):
        call = spend_ledger.record(stage=spend_ledger.STAGE_ASK, **CALL)
        assert round(call.usd, 5) == 0.00208

    def test_the_day_boundary_is_UTC_and_yesterday_is_excluded(self, ledger):
        now = datetime(2026, 8, 20, 0, 30, tzinfo=UTC)
        spend_ledger.record(stage=spend_ledger.STAGE_ASK, at=now - timedelta(hours=1), **CALL)
        spend_ledger.record(stage=spend_ledger.STAGE_ASK, at=now, **CALL)

        assert spend_ledger.day_start(now) == datetime(2026, 8, 20, tzinfo=UTC)
        assert round(spend_ledger.spent_today(now=now), 5) == 0.00208, "yesterday leaked in"

    def test_no_cap_configured_yields_None_remaining_not_zero(self, ledger):
        report = spend_ledger.report(daily_cap_usd=None, estimated_call_usd=0.00208)
        assert report.remaining_usd is None
        assert report.fraction_used is None
        assert report.calls_remaining is None

    def test_a_malformed_line_is_skipped_rather_than_fatal(self, ledger):
        spend_ledger.record(stage=spend_ledger.STAGE_ASK, **CALL)
        with open(ledger, "a", encoding="utf-8") as handle:
            handle.write("not json at all\n")
            handle.write(json.dumps({"at": "nonsense", "stage": "ask"}) + "\n")

        assert len(spend_ledger.read_all()) == 1

    def test_buckets_split_by_stage_so_one_bar_can_show_both(self, ledger):
        now = datetime.now(UTC).replace(minute=30, second=0, microsecond=0)
        spend_ledger.record(stage=spend_ledger.STAGE_EXTRACT, at=now, **CALL)
        spend_ledger.record(stage=spend_ledger.STAGE_ASK, at=now, **CALL)

        report = spend_ledger.report(daily_cap_usd=1.0, estimated_call_usd=0.00208, now=now)
        latest = report.hourly[-1]
        assert set(latest.by_stage) == {spend_ledger.STAGE_EXTRACT, spend_ledger.STAGE_ASK}
        assert latest.calls == 2


class TestTheEndpoint:
    def test_it_reports_one_cap_shared_by_both_stages(self, ledger, monkeypatch):
        from fastapi.testclient import TestClient

        from judge.app import app

        monkeypatch.setenv("EXTRACTION_DAILY_BUDGET_USD", "1.00")
        spend_ledger.record(stage=spend_ledger.STAGE_EXTRACT, **CALL)
        spend_ledger.record(stage=spend_ledger.STAGE_ASK, **CALL)

        body = TestClient(app).get("/admin/usage").json()

        assert body["cap"]["daily_usd"] == 1.00
        assert body["cap"]["shared_by"] == list(spend_ledger.STAGES)
        assert {s["stage"] for s in body["by_stage"]} == set(spend_ledger.STAGES)
        # One cap, and today's total is the SUM of the stages rather than a max.
        # `approx`, because each stage figure is rounded for display before it
        # is summed and the total is rounded once - a last-place drift that is
        # presentation, not a disagreement about what was spent.
        total = sum(s["spent_usd"] for s in body["by_stage"])
        assert body["today"]["spent_usd"] == pytest.approx(total, abs=1e-5)

    def test_an_unwired_stage_leads_the_summary(self, ledger, monkeypatch):
        """It changes what every other figure means, so it cannot be a footnote."""
        from fastapi.testclient import TestClient

        from judge.app import app

        monkeypatch.setenv("EXTRACTION_DAILY_BUDGET_USD", "1.00")
        spend_ledger.record(stage=spend_ledger.STAGE_EXTRACT, **CALL)

        body = TestClient(app).get("/admin/usage").json()
        assert "never recorded" in body["summary"]
        assert body["ledger"]["unwired_stages"] == [spend_ledger.STAGE_ASK]


class TestTheOtherPaidApiIsNotMeasuredInDollars:
    """RapidAPI bills requests per 23.9 days; the LLM bills dollars per day.

    Same page, separate tab, separate units. The assertions here are mostly
    about what the endpoint must NOT do - putting a dated observation on a live
    dashboard is the failure, not the absence of a number.
    """

    def _rapid(self):
        from fastapi.testclient import TestClient

        from judge.app import app

        return TestClient(app).get("/admin/usage").json()["rapidapi"]

    def test_it_reports_requests_rather_than_dollars(self, ledger):
        assert self._rapid()["unit"] == "requests"

    def test_it_says_it_is_not_instrumented_rather_than_showing_zero(self, ledger):
        """Zero requests used would be a lie; not-instrumented is the fact."""
        rapid = self._rapid()
        assert rapid["instrumented"] is False
        assert "Not instrumented" in rapid["headline"]

    def test_no_dated_observation_is_copied_onto_the_live_view(self, ledger):
        """The quota reading lives in `contract/sources.yaml` beside its read
        date. The same figure here would read as current, which is precisely the
        confusion this product exists to prevent."""
        body = json.dumps(self._rapid())
        for stale in ("998660", "1000000", "500000"):
            assert stale not in body, f"{stale} is a dated reading and must not appear live"

    def test_the_window_is_not_described_as_a_month(self, ledger):
        """23.9 days. Costing it as a monthly share is a third too low."""
        window = self._rapid()["window"]
        assert "23.9" in window
        assert "not a month" in window

    def test_both_open_questions_travel_with_it(self, ledger):
        """Each changes what a usage bar would mean, so neither is a footnote."""
        questions = " ".join(q["question"] + q["detail"] for q in self._rapid()["open_questions"])
        assert "tier" in questions
        assert "per-minute" in questions
        # The tier question's whole point: a healthy-looking bar may be a cliff.
        assert "looks healthy" in questions

    def test_it_names_what_would_make_it_live(self, ledger):
        """A gap with no repair attached is a complaint."""
        assert "x-ratelimit-requests-" in self._rapid()["what_would_make_it_live"]
