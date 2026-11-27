"""A watch-list provider that is down stops costing the run (2026-11-27).

On 26 Nov Instagram's provider failed for 64 accounts (the last 62 one after
another), ~95 s each, and the observer was cancelled at the job's 180-minute limit
before labelling. These pin:
  * after `watch.stop_after_failures` queries IN A ROW fail on one platform, the rest
    of its list is not asked: each is `skipped` with why ("not asked"), never "ok, 0";
  * the run says so in a note, and the skipped queries spend no request;
  * scattered failures stop nothing: one answered query resets the count;
  * ONLY THE PROVIDER FAILING COUNTS (#688 review, point 1): a failure the provider
    answered ("that account is gone": `collect.http.ANSWERED_STATUSES`) resets the
    count, and each watch adapter records those in `answered_errors`;
  * the setting is required and a whole number above 0 (rule 12).
"""

from __future__ import annotations

import copy
import dataclasses
from datetime import UTC, datetime, timedelta

import pytest
import yaml

from collect.industry_ai import config as iai_config
from collect.industry_ai.config import CONTRACT, IndustryAIConfigError
from collect.industry_ai.rules import Item

NOW = datetime.now(UTC)


@pytest.fixture(scope="module")
def raw():
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cfg(raw):
    return iai_config.parse(raw)


class _Contract:
    platforms = [{"id": "hackernews"}]
    feeds = []
    rulings = {}


def _harvest(cfg, monkeypatch, fails, *, stop_after=2, answered=lambda n: False):
    """Run the Hacker News watch list with a fake runner; `fails(n)` says whether the
    n-th query asked (0-based) fails, and `answered(n)` whether that failure was the
    provider answering (a gone account) rather than failing. Returns (out, asked)."""
    from collect.industry_ai import harvest as h

    asked = []

    class Fake(h._Runner):
        def __init__(self, *a, **k):
            pass

        def run(self, query):
            n = len(asked)
            asked.append(query)
            if fails(n):
                if answered(n):
                    return [], 1, "", "1 request(s) failed (HTTP 404)", False
                return [], 2, "", "ReadTimeout", True
            it = Item(id=f"hackernews:{n}", platform="hackernews", external_id=str(n),
                      url="u", title="t", body="b", created_at=NOW)
            return [it], 1, "", None, False

    monkeypatch.setitem(h._RUNNERS, "hackernews", Fake)
    w = {**cfg.watch, "stop_after_failures": stop_after,
         "max_requests": {**cfg.watch["max_requests"], "hackernews": 1000}}
    out = h.harvest(dataclasses.replace(cfg, watch=w), domains=[], platforms=["hackernews"],
                    contract=_Contract(), store=None, client_factory=lambda **k: None,
                    since=NOW - timedelta(days=90), log=lambda s: None,
                    watch_since=NOW - timedelta(days=7))
    return out, asked


def _watch(out):
    return [s for s in out.queries if s.domain == "watch"]


def test_a_failing_provider_stops_after_the_set_number_in_a_row(cfg, monkeypatch):
    out, asked = _harvest(cfg, monkeypatch, fails=lambda n: n >= 1, stop_after=2)
    stats = _watch(out)
    assert len(stats) >= 4, "the watch list needs at least 4 sources for this test"
    assert len(asked) == 3, "one ok, then two failures in a row, then nothing more asked"
    assert [s.status for s in stats[:3]] == ["ok", "error", "error"]
    rest = stats[3:]
    assert {s.status for s in rest} == {"skipped"}
    assert all(s.detail.startswith("not asked:") and s.requests == 0 for s in rest)
    assert out.requests["hackernews"] == 1 + 2 + 2
    assert any("stopped after the provider failed 2 queries in a row" in n
               and f"{len(rest)} not asked" in n for n in out.notes)


def test_scattered_failures_stop_nothing(cfg, monkeypatch):
    out, asked = _harvest(cfg, monkeypatch, fails=lambda n: n % 2 == 1, stop_after=2)
    stats = _watch(out)
    assert len(asked) == len(stats)
    assert "skipped" not in {s.status for s in stats}
    assert not any("stopped after" in n for n in out.notes)


def test_gone_accounts_side_by_side_stop_nothing(cfg, monkeypatch):
    """#688 review, point 1: every query after the first fails, but the provider
    ANSWERED each (a gone account), so the list is asked to the end; each stays an
    `error` that says the provider answered."""
    out, asked = _harvest(cfg, monkeypatch, fails=lambda n: n >= 1, answered=lambda n: True,
                          stop_after=2)
    stats = _watch(out)
    assert len(asked) == len(stats)
    assert {s.status for s in stats[1:]} == {"error"}
    assert all("the provider answered" in s.detail for s in stats[1:])
    assert not any("stopped after" in n for n in out.notes)


def test_an_answered_failure_resets_the_count(cfg, monkeypatch):
    # provider failing, answered (gone account), provider failing, ... never 2 in a row.
    out, asked = _harvest(cfg, monkeypatch, fails=lambda n: True,
                          answered=lambda n: n % 2 == 1, stop_after=2)
    assert len(asked) == len(_watch(out))
    assert not any("stopped after" in n for n in out.notes)


def test_a_runner_that_raises_counts_as_the_provider_failing(cfg, monkeypatch):
    from collect.industry_ai import harvest as h

    asked = []

    class Raising(h._Runner):
        def __init__(self, *a, **k):
            pass

        def run(self, query):
            asked.append(query)
            raise TimeoutError("read timed out")

    monkeypatch.setitem(h._RUNNERS, "hackernews", Raising)
    w = {**cfg.watch, "stop_after_failures": 2,
         "max_requests": {**cfg.watch["max_requests"], "hackernews": 1000}}
    out = h.harvest(dataclasses.replace(cfg, watch=w), domains=[], platforms=["hackernews"],
                    contract=_Contract(), store=None, client_factory=lambda **k: None,
                    since=NOW - timedelta(days=90), log=lambda s: None,
                    watch_since=NOW - timedelta(days=7))
    assert len(asked) == 2
    assert any("stopped after the provider failed 2" in n for n in out.notes)


class _Run:
    """A run record with the fields `provider_failed` reads."""

    def __init__(self, http_errors=0, answered_errors=0, recovered=0, rate_limited=0,
                 empty_response=0):
        self.http_errors, self.answered_errors, self.recovered = (
            http_errors, answered_errors, recovered)
        self.rate_limited, self.empty_response = rate_limited, empty_response


@pytest.mark.parametrize("run, failed", [
    (_Run(http_errors=1, answered_errors=1), False),          # a gone account
    (_Run(http_errors=2, answered_errors=1), True),           # and one the provider failed
    (_Run(http_errors=2, answered_errors=0, recovered=2), False),  # retries answered
    (_Run(rate_limited=1), True),
    (_Run(empty_response=1), True),
    (_Run(), False),
])
def test_provider_failed_reads_the_run_record(run, failed):
    from collect.industry_ai.harvest import provider_failed

    assert provider_failed(run) is failed


def test_a_run_record_without_answered_errors_raises():
    from collect.industry_ai.harvest import provider_failed

    class Old:
        http_errors = 1

    with pytest.raises(AttributeError):
        provider_failed(Old())


def test_the_issue_summary_says_what_was_not_asked(cfg):
    """A skipped query is neither failed nor a prune candidate, so without its own
    line the issue would show it nowhere (rule 4)."""
    import scripts.run_industry_ai as script

    queries = [{"status": "skipped", "items": 0, "platform": "instagram"},
               {"status": "skipped", "items": 0, "platform": "instagram"},
               {"status": "error", "items": 0, "platform": "instagram"}]
    body = script._summary("r1", "harvest", {}, {"items": 0, "kept": 0, "domains": {}},
                           queries, cfg)
    assert "2 query(ies) not asked (instagram)" in body
    assert "1 query(ies) failed - see the run log." in body
    assert "prune?" not in body


def test_the_contract_sets_it(cfg):
    assert cfg.watch["stop_after_failures"] == 5


@pytest.mark.parametrize("value", [None, 0, "5", True])
def test_the_setting_is_required_and_whole(raw, value):
    bad = copy.deepcopy(raw)
    if value is None:
        del bad["watch"]["stop_after_failures"]
    else:
        bad["watch"]["stop_after_failures"] = value
    with pytest.raises(IndustryAIConfigError):
        iai_config.parse(bad)
