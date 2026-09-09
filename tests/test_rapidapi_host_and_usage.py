"""One env variable, two providers — and the 404 that looked like a moved API.

`.env` declared `RAPIDAPI_HOST` twice: `reddit34.p.rapidapi.com` for the Reddit
arm and `twitter241.p.rapidapi.com` for the X arm. dotenv keeps the last, so
`collect/adapters/reddit.py` built `https://twitter241.p.rapidapi.com` and asked
it for `/getSearchPosts`. RapidAPI answered **404 to every Reddit search**.

Nothing could have told us that from a response. Both hosts are real, both
answer, and a 404 from the wrong vendor is indistinguishable from a platform
that changed its API — which is exactly how it was diagnosed the first time.

These tests pin the fix and the refusal. They make no network calls: a host is
derived from configuration, so it is establishable without spending a request.
"""

from __future__ import annotations

import json

import pytest

from collect.adapters.reddit import (
    DEFAULT_REDDIT_PROVIDER,
    RedditConfigError,
    host_for,
)
from collect.usage import read_rapidapi_quota, record_rapidapi_quota


class _Settings:
    """Only the two fields `host_for` consults."""

    def __init__(self, reddit_provider=None, rapidapi_host=None):
        self.reddit_provider = reddit_provider
        self.rapidapi_host = rapidapi_host


@pytest.fixture
def configured(monkeypatch):
    """Inject settings rather than the environment.

    `settings()` re-reads `.env` on every call, so `monkeypatch.delenv` does not
    unset anything — dotenv puts it straight back. What is under test here is
    the RESOLUTION ORDER, not dotenv, so the settings object is the right seam.
    """
    import collect.adapters.reddit as mod

    def _set(**kw):
        monkeypatch.setattr(mod, "settings", lambda: _Settings(**kw))

    return _set


class TestEachArmDerivesItsOwnHost:
    def test_reddit_provider_becomes_the_host(self, configured):
        # The X host is present and WRONG for this arm. The dedicated variable
        # wins, which is the whole point: two arms, two settings.
        configured(reddit_provider="reddit34", rapidapi_host="twitter241.p.rapidapi.com")
        assert host_for() == "reddit34.p.rapidapi.com"

    def test_an_explicit_argument_still_wins(self, configured):
        configured(reddit_provider="reddit34")
        assert host_for("somethingelse") == "somethingelse.p.rapidapi.com"

    def test_the_shared_variable_is_honoured_when_it_names_reddit(self, configured):
        configured(reddit_provider=None, rapidapi_host="reddit34.p.rapidapi.com")
        assert host_for() == "reddit34.p.rapidapi.com"

    def test_it_refuses_the_shared_variable_when_it_names_another_vendor(self, configured):
        # THE ACTUAL BUG. Before this the value was used, and every Reddit
        # search 404'd against X's host.
        configured(reddit_provider=None, rapidapi_host="twitter241.p.rapidapi.com")
        with pytest.raises(RedditConfigError) as e:
            host_for()
        # The message has to name the collision, because the symptom (404)
        # points at the platform rather than at the configuration.
        assert "twitter241" in str(e.value)
        assert "REDDIT_PROVIDER" in str(e.value)
        assert "404" in str(e.value)

    def test_nothing_configured_raises_rather_than_defaulting(self, configured):
        configured(reddit_provider=None, rapidapi_host=None)
        with pytest.raises(RedditConfigError) as e:
            host_for()
        # Rule 6, and the same reasoning x.py gives: an unconfigured process
        # must not quietly call one particular vendor.
        assert DEFAULT_REDDIT_PROVIDER in str(e.value)


class TestEveryMeteredResponseRecordsItsReading:
    """The tracking gap: one writer, at the end of one arm."""

    def test_a_reading_is_written_with_its_reader_named(self, tmp_path):
        path = tmp_path / "q.json"
        assert record_rapidapi_quota(
            remaining=500, limit=1000, read_on="reddit", read_by="sweep", path=path
        )
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec["quota_remaining"] == 500 and rec["quota_limit"] == 1000
        # One key meters both arms, so the figure cannot be split by endpoint.
        # Naming the reader is the honest substitute.
        assert rec["read_on"] == "reddit"
        # A probe's reading is as real as a fetch's; saying which stops "a fetch
        # must have run" being inferred from a number that moved.
        assert rec["read_by"] == "sweep"
        assert rec["at"]

    def test_remaining_without_a_limit_is_recorded_and_does_not_inherit_one(self, tmp_path):
        # THE CURRENT CASE. The last two real readings are mutually
        # inconsistent — 998,076 of 1,000,000, then 99,870 nine days and ~130
        # requests later — so carrying the old denominator forward would put a
        # wrong limit on a right figure (rules 6 and 7).
        path = tmp_path / "q.json"
        record_rapidapi_quota(remaining=999, limit=1000, read_on="reddit", path=path)
        record_rapidapi_quota(remaining=99870, limit=None, read_on="x", path=path)
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec["quota_remaining"] == 99870
        assert rec["quota_limit"] is None

    def test_a_blank_reading_does_not_clobber_a_good_one(self, tmp_path):
        path = tmp_path / "q.json"
        record_rapidapi_quota(remaining=500, limit=1000, read_on="reddit", path=path)
        assert record_rapidapi_quota(
            remaining=None, limit=None, read_on="x", path=path
        ) is False
        assert json.loads(path.read_text(encoding="utf-8"))["quota_remaining"] == 500

    def test_an_unwritable_path_is_silent_rather_than_fatal(self, tmp_path):
        # It is called from inside a request path. The request is already spent
        # by then, so raising here would lose the harvest as well as the number.
        blocked = tmp_path / "file-not-a-dir"
        blocked.write_text("x", encoding="utf-8")
        assert record_rapidapi_quota(
            remaining=1, limit=2, read_on="x", path=blocked / "q.json"
        ) is False

    def test_a_corrupt_file_reads_as_absent_not_as_a_crash(self, tmp_path):
        path = tmp_path / "q.json"
        path.write_text("{not json", encoding="utf-8")
        assert read_rapidapi_quota(path) is None


class TestBothAdaptersRecordFromTheResponse:
    """The write must sit next to the response, not at the end of an arm."""

    @pytest.mark.parametrize("module", ["collect.adapters.reddit", "collect.adapters.x"])
    def test_the_adapter_calls_the_recorder(self, module):
        import importlib
        import inspect

        src = inspect.getsource(importlib.import_module(module))
        assert "record_rapidapi_quota(" in src, f"{module} spends quota and records nothing"
        # In `_get`, where the response is — the only place that cannot forget.
        get = src[src.index("def _get("):]
        assert "record_rapidapi_quota(" in get[:4000], f"{module} records outside _get"


class TestTheExtractorRecordsItsSpend:
    """E5 has called a paid model since August and written nothing."""

    def test_the_extract_client_records_every_completion(self):
        import inspect

        from judge.extract import client

        src = inspect.getsource(client)
        # The ledger's own STAGE_LABELS describes extraction as "one call per
        # thread, nightly batch", while the only caller of `record` was the Ask
        # box. That is why the panel showed one model and had to derive the
        # other from the provider's key total minus what it knew.
        assert "spend_ledger.record(" in src, "E5 spends money and records nothing"
        assert "STAGE_EXTRACT" in src

    def test_a_known_model_is_priced_at_its_own_rate(self, tmp_path):
        from judge import spend_ledger as sl

        path = tmp_path / "l.jsonl"
        call = sl.record(stage="extract", model="deepseek/deepseek-v4-flash",
                         input_tokens=1_000_000, output_tokens=0, path=path)
        # DeepSeek V4 Flash is $0.14/Mtok in. Gemini's constant is $0.065, and
        # recording DeepSeek tokens at Gemini's rate is the bug this replaces:
        # measured tokens, invented cost.
        assert round(call.usd, 4) == 0.14
        assert call.unpriced is False

    def test_an_unknown_model_records_tokens_and_no_dollars(self, tmp_path):
        from judge import spend_ledger as sl

        path = tmp_path / "l.jsonl"
        call = sl.record(stage="extract", model="somebody/unlisted-model",
                         input_tokens=1000, output_tokens=200, path=path)
        # The tokens are still true. The product is not available, and a default
        # rate would produce a plausible total nobody can audit (rule 3).
        assert call.input_tokens == 1000 and call.output_tokens == 200
        assert call.usd == 0.0
        assert call.unpriced is True

    def test_unpriced_survives_the_round_trip(self, tmp_path):
        from judge import spend_ledger as sl

        path = tmp_path / "l.jsonl"
        sl.record(stage="extract", model="somebody/unlisted-model",
                  input_tokens=5, output_tokens=5, path=path)
        assert sl.read_all(path)[0].unpriced is True

    def test_a_row_written_before_the_field_reads_as_priced(self, tmp_path):
        # Every row written before per-model pricing WAS priced, at the one rate
        # that then existed. False is the correct reading, not a guess.
        path = tmp_path / "l.jsonl"
        path.write_text(json.dumps({
            "at": "2026-08-20T10:00:00+00:00", "stage": "ask",
            "model": "google/gemini-2.5-flash", "in": 10, "out": 5, "usd": 0.0000135,
        }) + "\n", encoding="utf-8")
        from judge import spend_ledger as sl

        assert sl.read_all(path)[0].unpriced is False
