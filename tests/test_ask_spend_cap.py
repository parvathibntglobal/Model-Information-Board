"""The ask-path cap, and the one test shape that could have caught it broken.

`/ask/understand` had a budget check, a 429 branch, a message and coverage, and
the cap could not bind. Every existing test made ONE request, and one request
is exactly the population in which the bug is invisible: the check compares a
freshly-zeroed total against the limit and passes correctly.

So the assertion that matters here is `test_the_cap_binds_ACROSS_requests`. The
rest guard the edges around it.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from judge.app import app
from judge.ask import spend
from judge.ask.profile import TaskProfile
from judge.ask.understand import Understanding

client = TestClient(app, raise_server_exceptions=False)

#: One call at the DeepSeek V4 Flash price: 2,010 in / 589 out -> $0.000213.
#: (Was $0.00208 at the Gemini 2.5 Flash price; the token means are unchanged.)
ONE_CALL_USD = 0.00021311


@pytest.fixture
def fake_model(monkeypatch):
    """Q1 without a network call. Reports the measured token counts so spend
    accumulates at the real rate rather than at a rate this test invented."""
    calls = []

    def _understand(text, *, client, shape):
        calls.append(text)
        return Understanding(
            profile=TaskProfile(raw_text=text, roles=[]),
            assumptions=[],
            input_tokens=2010,
            output_tokens=589,
        )

    monkeypatch.setattr("judge.app.understand", _understand)
    monkeypatch.setattr("judge.app.OpenRouterClient.from_env", staticmethod(lambda: _Client()))
    return calls


class _Client:
    model = "google/gemini-2.5-flash"


def ask(text: str = "summarise support tickets into weekly themes"):
    return client.post("/ask/understand", json={"text": text, "shape": "task"})


class TestTheCapBindsAcrossRequests:
    """THE TEST THE ORIGINAL VERSION WOULD HAVE FAILED."""

    def test_the_cap_binds_ACROSS_requests(self, fake_model):
        """Ten calls' worth of cap, and request eleven must be refused.

        The old handler built a new `Budget` per request, so `spent_usd` was
        0.0 every time and this loop would have run forever at any limit above
        one call. Asserted as a bound rather than an exact count because the
        per-call cost is a measured figure that may move.
        """
        spend.reset_for_test(limit_usd=ONE_CALL_USD * 10)

        allowed = 0
        for _ in range(60):
            if ask().status_code == 429:
                break
            allowed += 1
        else:
            pytest.fail("the cap never bound across 60 requests")

        assert 8 <= allowed <= 11, f"{allowed} calls allowed against a 10-call cap"
        assert len(fake_model) == allowed, "a refused request must not reach the model"

    def test_spend_accumulates_rather_than_resetting(self, fake_model):
        spend.reset_for_test(limit_usd=1.00)
        ask()
        after_one = spend.spent_usd()
        ask()
        after_two = spend.spent_usd()

        assert after_one > 0, "charge() never ran - the total is not being recorded"
        assert after_two > after_one, "the total reset between requests"

    def test_a_refused_request_never_reaches_the_model(self, fake_model):
        """Spend cannot be undone, so the guard runs first."""
        spend.reset_for_test(limit_usd=0.0001)
        assert ask().status_code == 429
        assert fake_model == []


class TestNoCapConfiguredIsRefusedRatherThanRunUncapped:
    """The two callers of `Budget.from_env()` must answer `None` differently.

    The CLI can read it as an operator's choice - a person typed the command.
    An anonymous request to an endpoint with no authentication cannot.
    """

    def test_an_unconfigured_cap_is_503_and_says_it_is_a_missing_decision(self, fake_model):
        spend.reset_for_test(limit_usd=None, configured=False)
        response = ask()

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert "no cap" in detail
        assert "refused rather than run uncapped" in detail
        assert fake_model == [], "an unconfigured cap must not spend money"

    def test_it_does_not_read_as_the_board_being_down(self, fake_model):
        """503 is also "cannot be read", so this one has to say which it is."""
        spend.reset_for_test(limit_usd=None, configured=False)
        assert "every other endpoint still answers" in ask().json()["detail"]

    def test_unconfigured_spend_is_None_rather_than_zero(self):
        """0.0 would render as "nothing spent", the most reassuring of the two
        readings, which is rule 6 on our own telemetry."""
        spend.reset_for_test(limit_usd=None, configured=False)
        assert spend.spent_usd() is None
        assert "nothing is counting" in spend.summary()


class TestTheRefusalIsAChoiceNotAFailure:
    def test_the_429_message_distinguishes_a_cap_from_an_error(self, fake_model):
        spend.reset_for_test(limit_usd=0.0001)
        detail = ask().json()["detail"]
        assert "not a failure" in detail
        assert "not an empty corpus" in detail


class TestTheDefectCannotBeReintroduced:
    """A structural guard, because the broken version looked like working code.

    Rebuilding a `Budget` inside the handler is a one-line change that reads as
    a tidy-up and silently unbinds the cap again.
    """

    def _handler_code(self) -> str:
        """COMMENTS AND DOCSTRINGS STRIPPED FIRST.

        The handler's own comment explains why it must not build a fresh
        `Budget` here, so a raw substring check matches the prose warning
        against the thing and fails. Fifth instance of that in this repo, and
        the first one caught before it was written rather than after.
        """
        import inspect

        from judge.app import understand_task

        source = inspect.getsource(understand_task)
        source = re.sub(r'"""[\s\S]*?"""', "", source)
        return re.sub(r"#.*", "", source)

    def test_the_handler_does_not_construct_its_own_budget(self):
        assert "Budget(" not in self._handler_code()
        assert "Budget.from_env" not in self._handler_code()

    def test_the_handler_charges_what_the_call_reported(self):
        code = self._handler_code()
        assert "spend.charge(" in code, "a check with no charge reads zero forever"
        assert "output_tokens=result.output_tokens" in code

    def test_the_charge_names_the_real_model(self):
        """Rule 7: `spend_by_model` cannot show a swap if every call is
        attributed to a constant."""
        assert "model=client.model" in self._handler_code()


class TestTheCapIsReadOnFirstUseNotAtImport:
    """An import-time read makes the cap depend on import ORDER.

    `run-backend.py` populates `os.environ` before importing uvicorn, so an
    import-time read happens to work there. `docs/frontend-handoff.md` also
    documents starting the service as plain `uvicorn judge.app:app`, and
    `collect/config.py` loads `.env` lazily from its own entry points - so
    whether the cap exists would depend on which module won the race.

    The failure is silent and points the wrong way: the endpoint answers 503
    forever on a machine where the cap IS configured, with a message saying the
    cap is missing. It fails closed, which is the right direction, and closed
    for a false reason is still a defect.
    """

    def test_an_env_var_set_after_import_is_still_seen(self, monkeypatch):
        import importlib

        monkeypatch.delenv("EXTRACTION_DAILY_BUDGET_USD", raising=False)
        module = importlib.reload(spend)          # imported with NO cap present
        monkeypatch.setenv("EXTRACTION_DAILY_BUDGET_USD", "2.50")

        assert module.is_configured() is True, "the cap was read at import, not on use"

    def test_an_absent_env_var_still_reads_as_unconfigured(self, monkeypatch):
        import importlib

        monkeypatch.delenv("EXTRACTION_DAILY_BUDGET_USD", raising=False)
        module = importlib.reload(spend)

        assert module.is_configured() is False
        assert module.spent_usd() is None
