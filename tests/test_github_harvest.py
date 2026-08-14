"""The GitHub adapter: a throttle is not an empty result set.

The first live run reported `total=0, retrieved=0` for a query that had returned
7 results four minutes earlier. It had been rate-limited, and the code recorded
that as "nothing matched". Third instance of one class in this project, after a
304 read as a dead feed and a non-XML page read as an empty one: **a definite
negative answer and an absence recorded identically.**

So the tests come in pairs. Each pair issues a throttle and a genuine zero and
asserts they are distinguishable, because a single test of either one passes
whichever way the code conflates them.
"""

from __future__ import annotations

import httpx

from collect.adapters.github import (
    MAX_BACKOFF_SECONDS,
    SEARCH_INTERVAL,
    SEARCH_LIMIT_PER_MINUTE,
    GitHubHarvester,
    QueryRun,
)
from collect.adapters.queries.contract import QueryEntry, TermSet
from collect.adapters.queries.github import render_search
from collect.http import build_client
from collect.rawstore import RawStore

UA = "modelboard/0.1 (+https://modelboard.invalid/about)"
SWEEP = ("repo:langchain-ai/langchain",)


def entry() -> QueryEntry:
    return QueryEntry(
        kind="capability",
        capability="summarization.fidelity",
        stance="negative",
        terms=TermSet(subject=("{alias}",), topic=("summarize",), signal=("dropped",)),
        records_condition="context_size",
    )


def request():
    return render_search(entry(), "gemini flash", scope=SWEEP)


class Recorder:
    """A recorded GitHub. Serves whatever the test queued, in order."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.calls += 1
        response = self.responses[min(self.calls - 1, len(self.responses) - 1)]
        return response() if callable(response) else response


def harvester(recorder, tmp_path, **kwargs):
    client = build_client(user_agent=UA, transport=httpx.MockTransport(recorder))
    slept: list[float] = []
    h = GitHubHarvester(
        client=client,
        store=RawStore(tmp_path / "raw"),
        search_limiter=_no_wait(),
        rest_limiter=_no_wait(),
        pipeline_version="collect-test",
        sleeper=slept.append,
        epoch=lambda: 1_000_000.0,
        **kwargs,
    )
    return h, slept


def _no_wait():
    from collect.limiter import HostLimiter

    return HostLimiter(min_interval=0.0, clock=lambda: 0.0, sleeper=lambda _s: None)


def ok(items, total=None):
    payload = {"total_count": total if total is not None else len(items), "items": items}
    return httpx.Response(200, json=payload)


def throttled(
    *, status=403, remaining="0", reset=None, retry_after=None, body="API rate limit exceeded"
):
    headers = {}
    if remaining is not None:
        headers["x-ratelimit-remaining"] = remaining
    if reset is not None:
        headers["x-ratelimit-reset"] = str(reset)
    if retry_after is not None:
        headers["retry-after"] = str(retry_after)
    return httpx.Response(status, json={"message": body}, headers=headers)


def hit(number=1, title="t", body="b"):
    return {
        "url": f"https://api.github.com/repos/o/r/issues/{number}",
        "html_url": f"https://github.com/o/r/issues/{number}",
        "number": number,
        "title": title,
        "body": body,
        "created_at": "2026-08-01T00:00:00Z",
        "user": {"login": "someone"},
        "comments": 0,
        "reactions": {"total_count": 0},
    }


# ── the pair that matters ────────────────────────────────────────────────


def test_a_genuine_zero_is_a_known_zero(tmp_path):
    h, _ = harvester(Recorder([ok([], total=0)]), tmp_path)
    run = QueryRun(request=request())
    hits = h.search(run.request, run)

    assert hits == []
    assert run.total_count == 0, "the platform answered: nothing matches"
    assert run.retrieved == 0
    assert run.rate_limited is False
    assert run.truncated_by is None
    assert h.outcome_of(run) == "fetched"


def test_a_throttled_query_is_not_a_zero(tmp_path):
    """The live defect. `total_count` stays None: we were not told."""
    h, _ = harvester(Recorder([throttled(), throttled()]), tmp_path)
    run = QueryRun(request=request())
    hits = h.search(run.request, run)

    assert hits == []
    assert run.total_count is None, "unknown must not be recorded as zero"
    assert run.rate_limited is True
    assert run.truncated_by == "rate-limit"
    assert run.http_errors == 1
    assert h.outcome_of(run) == "error"


def test_the_two_are_distinguishable_in_the_harvest_run_row(tmp_path):
    """Whatever the schema gains, these two rows must not be equal."""
    zero_h, _ = harvester(Recorder([ok([], total=0)]), tmp_path / "a")
    zero = QueryRun(request=request())
    zero_h.search(zero.request, zero)

    throttle_h, _ = harvester(Recorder([throttled(), throttled()]), tmp_path / "b")
    limited = QueryRun(request=request())
    throttle_h.search(limited.request, limited)

    zero_row = zero_h.harvest_run_fields(zero)
    limited_row = throttle_h.harvest_run_fields(limited)

    assert zero_row["items_fetched"] == limited_row["items_fetched"] == 0
    assert zero_row["truncated_by"] is None
    assert limited_row["truncated_by"] == "rate-limit"
    assert zero_row["exhausted"] is True
    assert limited_row["exhausted"] is None, "neither finished nor unfinished — unknown"
    assert zero_row["outcome"] != limited_row["outcome"]


# ── backoff ──────────────────────────────────────────────────────────────


def test_a_throttle_is_retried_once_and_succeeds(tmp_path):
    h, slept = harvester(Recorder([throttled(retry_after=7), ok([hit()])]), tmp_path)
    run = QueryRun(request=request())
    hits = h.search(run.request, run)

    assert len(hits) == 1
    assert slept == [7.0], "honoured retry-after"
    assert run.rate_limited is False, "it recovered; the run is not truncated"
    assert run.truncated_by is None
    assert run.search_calls == 2


def test_x_ratelimit_reset_is_honoured_as_an_absolute_time(tmp_path):
    """`reset` is an epoch, not a duration — a subtraction, not a sleep value."""
    h, slept = harvester(
        Recorder([throttled(reset=1_000_045), ok([hit()])]), tmp_path
    )
    run = QueryRun(request=request())
    h.search(run.request, run)
    assert slept and 45.0 < slept[0] <= 47.0, slept


def test_backoff_is_bounded(tmp_path):
    """A reset an hour out must not park the sweep for an hour."""
    h, slept = harvester(Recorder([throttled(reset=1_003_600), ok([hit()])]), tmp_path)
    run = QueryRun(request=request())
    h.search(run.request, run)
    assert slept[0] == MAX_BACKOFF_SECONDS


def test_429_is_a_throttle_too(tmp_path):
    responses = [throttled(status=429, remaining=None) for _ in range(2)]
    h, _ = harvester(Recorder(responses), tmp_path)
    run = QueryRun(request=request())
    h.search(run.request, run)
    assert run.rate_limited is True


def test_a_403_that_is_not_a_rate_limit_is_an_error_not_a_throttle(tmp_path):
    """A permission failure must not be retried as though waiting would help."""
    forbidden = httpx.Response(403, json={"message": "Resource not accessible by integration"})
    h, slept = harvester(Recorder([forbidden]), tmp_path)
    run = QueryRun(request=request())
    h.search(run.request, run)

    assert run.rate_limited is False
    assert run.truncated_by is None
    assert run.http_errors == 1
    assert slept == [], "no backoff for a permission error"
    assert run.search_calls == 1, "not retried"


# ── the instrument must not lie about the instrument ─────────────────────


def test_the_ledger_counts_a_run_the_caller_never_kept(tmp_path):
    """The live report showed `http_errors: 0` while a query had been throttled.

    The totals were summed over the list the caller happened to hold, and the
    probe run was not in it. The ledger belongs to the harvester so a call site
    cannot forget it.
    """
    h, _ = harvester(Recorder([ok([hit()]), throttled(), throttled()]), tmp_path)

    kept = h.harvest(request())           # the caller keeps this one
    forgotten = QueryRun(request=request())
    h.search(forgotten.request, forgotten)  # and not this one

    totals = h.totals()
    assert totals["queries"] == 2
    assert totals["http_errors"] == 1, "the forgotten run's throttle is counted"
    assert totals["rate_limited_queries"] == 1
    assert totals["unknown_total_count"] == 1
    assert kept.rate_limited is False


def test_totals_are_not_taken_from_a_caller_supplied_list(tmp_path):
    h, _ = harvester(Recorder([throttled(), throttled()]), tmp_path)
    run = QueryRun(request=request())
    h.search(run.request, run)
    assert h.totals()["rate_limited_queries"] == 1


# ── pacing ───────────────────────────────────────────────────────────────


def test_the_search_interval_leaves_headroom_below_the_ceiling():
    """Pacing at exactly 30/min spent the whole window and the next call 403'd."""
    per_minute = 60.0 / SEARCH_INTERVAL
    assert per_minute < SEARCH_LIMIT_PER_MINUTE
    assert per_minute >= SEARCH_LIMIT_PER_MINUTE * 0.85, "headroom, not a crawl"
