"""Blog generation's model calls in the spend ledger - stage 'blog', outside the cap.

Rule 2 names the blog generator as a third model caller (CLAUDE.md, 2026-10-06).
Its GPT-6 Luna calls are now ledger rows so Admin -> API usage can show them by
month, and they must never spend the extraction budget. What these pin down:
  * a blog call carries OpenRouter's REPORTED cost; a call with none is
    unpriced, never $0 and never priced at some other model's rate;
  * the daily cap - `spent_today` and every figure in `report` - ignores blog
    calls, so a blog run cannot stop extraction;
  * `monthly` groups every stage by UTC month, model and stage;
  * the generator's live row and the backfill's row for one call share an id,
    so a call recorded twice counts once.
No database: the shared table is stubbed unreadable and the local file is temp.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from judge import spend_ledger

LUNA = "openai/gpt-6-luna"
EXTRACTOR = "deepseek/deepseek-v4-flash"


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "spend-ledger.jsonl"
    monkeypatch.setenv(spend_ledger.LEDGER_PATH_ENV, str(path))
    # THIS FILE ONLY: never read or write the shared table from a unit test.
    monkeypatch.setattr(spend_ledger, "read_database", lambda dsn=None: None)
    return path


def _blog(usd, at=None, tin=1000, tout=500):
    return spend_ledger.record(stage=spend_ledger.STAGE_BLOG, model=LUNA, input_tokens=tin,
                               output_tokens=tout, at=at, to_database=False,
                               reported=True, reported_usd=usd)


def _extract(at=None):
    return spend_ledger.record(stage=spend_ledger.STAGE_EXTRACT, model=EXTRACTOR,
                               input_tokens=2010, output_tokens=589, at=at, to_database=False)


def test_a_blog_call_carries_the_reported_cost(ledger):
    call = _blog(0.0412)
    assert call.usd == pytest.approx(0.0412) and not call.unpriced
    [back] = spend_ledger.read_all()
    assert (back.stage, back.model, back.usd) == ("blog", LUNA, pytest.approx(0.0412))


def test_a_blog_call_with_no_reported_cost_is_unpriced_not_free(ledger):
    call = _blog(None)
    assert call.usd == 0.0 and call.unpriced


def test_blog_spend_never_counts_against_the_daily_cap(ledger):
    _extract()
    _blog(5.00)  # far over any cap on its own
    capped = spend_ledger.spent_today()
    assert capped == pytest.approx(_extract_cost())
    report = spend_ledger.report(daily_cap_usd=1.0, estimated_call_usd=0.001)
    assert report.spent_today_usd == pytest.approx(capped)
    assert report.remaining_usd > 0
    assert "blog" not in report.by_stage_usd and LUNA not in report.by_model_usd
    assert report.calls_today == 1


def _extract_cost():
    from judge.extract.budget import pricing_for
    return spend_ledger.cost_of(2010, 589, pricing_for(EXTRACTOR))


def test_an_unknown_caller_is_still_refused():
    with pytest.raises(ValueError, match="permitted to call a model"):
        spend_ledger.record(stage="curate", model=LUNA, input_tokens=1, output_tokens=1)


def test_monthly_groups_by_month_stage_and_model(ledger):
    sept = datetime(2026, 9, 30, 23, 0, tzinfo=UTC)
    octo = datetime(2026, 10, 1, 1, 0, tzinfo=UTC)
    _extract(at=sept)
    _blog(0.03, at=octo)
    _blog(0.02, at=octo, tin=10)
    _blog(None, at=octo, tin=20)
    rows = spend_ledger.monthly(spend_ledger.read_all())
    got = [(r.month, r.stage, r.model, r.calls, round(r.usd, 4), r.unpriced_calls) for r in rows]
    assert got == [
        ("2026-10", "blog", LUNA, 3, 0.05, 1),       # newest month first; a floor, said so
        ("2026-09", "extract", EXTRACTOR, 1, round(_extract_cost(), 4), 0),
    ]


def test_the_live_row_and_the_backfill_row_are_one_call(ledger):
    """`ledger_kwargs` is what both the generator and the backfill record with,
    so the same call gets the same id and is counted once."""
    import generate_sample_blogs as gen

    record = {"post": "field-report-x", "started": "2026-10-05T06:22:22+00:00",
              "requested_model": LUNA,
              "attempts": [{"served": LUNA, "usage": {"prompt_tokens": 18204,
                                                     "completion_tokens": 3100, "cost": 0.0412}},
                           {"served": LUNA, "usage": {"prompt_tokens": 19000,
                                                     "completion_tokens": 2900}}]}
    gen.record_spend(record, 0)
    gen.record_spend(record, 1)
    for i in range(2):  # the backfill's pass over the same record
        spend_ledger.record(**gen.ledger_kwargs(record, i), to_database=False)
    calls = spend_ledger.read_everywhere()[0]
    assert len({c.id for c in calls}) == 2
    first = next(c for c in calls if c.run_id.endswith("#1"))
    assert first.usd == pytest.approx(0.0412)
    assert first.run_id == "blog:field-report-x@2026-10-05T06:22:22+00:00#1"
    second = next(c for c in calls if c.run_id.endswith("#2"))
    assert second.unpriced  # no cost reported for it


def test_a_terminal_run_sends_its_rows_to_the_shared_table(ledger, monkeypatch):
    """`env()` reads .env into a dict and never sets os.environ, so the shared
    table must get the generator's own DATABASE_URL explicitly - not rely on an
    environment a terminal run does not have (found 2026-10-07)."""
    import generate_sample_blogs as gen

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(gen, "env", lambda: {"DATABASE_URL": "postgresql://from-dotenv/db"})
    sent = []
    monkeypatch.setattr(spend_ledger, "append_to_database",
                        lambda calls, dsn=None: sent.append((list(calls), dsn)) or 1)
    record = {"post": "p", "started": "2026-10-07T01:00:00+00:00", "requested_model": LUNA,
              "attempts": [{"served": LUNA, "usage": {"prompt_tokens": 5, "completion_tokens": 6,
                                                     "cost": 0.001}}]}
    gen.record_spend(record, 0)
    [(calls, dsn)] = sent
    assert dsn == "postgresql://from-dotenv/db" and calls[0].stage == "blog"
    assert len(spend_ledger.read_all()) == 1  # and the local file, once


# ── a call that was answered and is still unusable is spend too ─────────────
# 2026-10-13: three Gemma 4 calls failed - one crashed the checker, one made no
# tool call, one stopped at max_tokens - and none reached the ledger. No model
# is called here: the HTTP stream is a fake and the post is a stub.

class _Stream:
    status_code = 200
    headers = {"X-Generation-Id": "gen-test"}

    def __init__(self, chunks):
        import json
        self._lines = [f"data: {json.dumps(c)}" for c in chunks] + ["data: [DONE]"]

    def iter_lines(self):
        return iter(self._lines)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _served(gen):
    return next(iter(gen.GEN_MODELS[gen.GEN_MODEL]))


def _usage(cost=0.0123):
    return {"prompt_tokens": 9000, "completion_tokens": 4000, "cost": cost}


@pytest.fixture
def gen(ledger, tmp_path, monkeypatch):
    import generate_sample_blogs as g

    monkeypatch.setattr(g, "env", lambda: {})          # local ledger file only
    monkeypatch.setattr(g, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(g, "user_message", lambda *a: "brief")
    monkeypatch.setattr(g, "fact_lines", lambda facts: "")
    return g


@pytest.mark.parametrize("why, delta, finish, model", [
    ("max_tokens", {"tool_calls": [{"function": {"arguments": '{"tit'}}]}, "length", None),
    ("no tool call", {"content": "I will write it."}, "stop", None),
    ("wrong model", {"tool_calls": [{"function": {"arguments": "{}"}}]}, "stop", "someone/else"),
])
def test_an_answered_unusable_call_carries_its_usage(gen, monkeypatch, why, delta, finish, model):
    chunks = [{"model": model or _served(gen), "provider": "P",
               "choices": [{"delta": delta, "finish_reason": finish}]},
              {"model": model or _served(gen), "usage": _usage()}]
    monkeypatch.setattr(gen.httpx, "stream", lambda *a, **k: _Stream(chunks))
    with pytest.raises(gen.CallFailed) as e:
        gen.call_model("k", "https://router.invalid", [])
    assert e.value.got["usage"]["cost"] == pytest.approx(0.0123)
    assert e.value.got["generation_id"] == "gen-test"


def test_a_failed_call_reaches_the_ledger_and_still_fails(gen, monkeypatch):
    def failing(*a, **k):
        raise gen.CallFailed("no tool call (finish_reason='stop')",
                             {"served": _served(gen), "provider": "P", "usage": _usage(),
                              "generation_id": "gen-1"})
    monkeypatch.setattr(gen, "call_model", failing)
    with pytest.raises(gen.CallFailed):
        gen.synthesise({"key": "p"}, [], [], "k", "b")
    [row] = spend_ledger.read_all()
    assert row.stage == "blog" and row.usd == pytest.approx(0.0123) and not row.unpriced


def test_an_abandoned_call_with_no_usage_is_recorded_unpriced(gen, monkeypatch):
    def abandoned(*a, **k):
        raise gen.CallFailed("abandoned", {"served": None, "provider": None, "usage": None,
                                           "generation_id": "gen-2"})
    monkeypatch.setattr(gen, "call_model", abandoned)
    with pytest.raises(gen.CallFailed):
        gen.synthesise({"key": "p"}, [], [], "k", "b")
    [row] = spend_ledger.read_all()
    assert row.unpriced and row.usd == 0.0  # recorded, never read as free


def test_a_checker_crash_cannot_lose_the_row(gen, monkeypatch):
    got = {"message": {"role": "assistant", "content": ""},
           "call": {"id": "c", "type": "function",
                    "function": {"name": "publish_essay", "arguments": '{"sections": []}'}},
           "served": _served(gen), "provider": "P", "usage": _usage(0.02), "generation_id": "g"}
    monkeypatch.setattr(gen, "call_model", lambda *a, **k: got)

    def crash(*a, **k):
        raise AttributeError("'list' object has no attribute 'get'")
    monkeypatch.setattr(gen, "check", crash)
    with pytest.raises(AttributeError):
        gen.synthesise({"key": "p"}, [], [], "k", "b")
    [row] = spend_ledger.read_all()
    assert row.usd == pytest.approx(0.02)
