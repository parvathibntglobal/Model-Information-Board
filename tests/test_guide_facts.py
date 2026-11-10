"""The verified-facts box inside a migration guide (Blogs -> Guides), 2026-10-30.

A migration guide is a written post; this box is the part written by code: the
registry's published facts for the guide's two models and a checklist worded by
contract/migrations.yaml (judge/migrations.py). What is pinned: an unpublished
value stays unpublished (rule 6), nothing is computed beyond "higher or lower"
(rule 3), retirement is news on either side and never compared, and the
direction is the title's when it says "A to B", else older to newer - and the
payload says which. No database: the registry rows are fixed here.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from judge import gate, migrations

R = migrations.rules()


def _m(**kw):
    base = dict(id="mv_a", canonical_id="anthropic/claude-a", provider="anthropic",
                display_name="Anthropic: Claude A", release_date=date(2026, 1, 1),
                retirement_date=None, knowledge_cutoff=None, advertised_context=1_000_000,
                max_output_tokens=128_000, price_in=Decimal("5"), price_out=Decimal("25"),
                price_cached_read=Decimal("0.5"), batch_discount=Decimal("0.5"),
                supports_tools=True, supports_structured_output=True, supports_vision=True,
                supports_caching=True, supports_batch=True)
    return base | kw


def _rows(a, b):
    return {r["field"]: r for r in migrations.diff(a, b, R)}


def test_the_contract_loads_and_every_row_is_a_column():
    assert [r["field"] for r in R["rows"]][:2] == ["price_in", "price_out"]
    assert set(R["checklist"]) <= {r["field"] for r in R["rows"]}


def test_an_unpublished_value_is_unknown_never_same_or_no():
    rows = _rows(_m(supports_batch=None), _m(id="mv_b", supports_batch=None))
    assert rows["supports_batch"]["change"] == "unknown"
    assert rows["supports_batch"]["from"] is None and rows["supports_batch"]["to"] is None
    assert rows["knowledge_cutoff"]["change"] == "unknown"


def test_a_flag_published_false_is_lost_and_null_is_unknown():
    a = _m()
    assert _rows(a, _m(id="mv_b", supports_tools=False))["supports_tools"]["change"] == "lost"
    assert _rows(a, _m(id="mv_b", supports_tools=None))["supports_tools"]["change"] == "unknown"
    assert _rows(_m(supports_tools=False), _m(id="mv_b"))["supports_tools"]["change"] == "gained"


def test_prices_are_shown_as_published_and_only_named_higher_or_lower():
    rows = _rows(_m(), _m(id="mv_b", price_in=Decimal("4"), price_cached_read=Decimal("0.2")))
    p = rows["price_in"]
    assert (p["from"], p["to"], p["change"]) == ("$5.00", "$4.00", "down")
    assert rows["price_cached_read"]["to"] == "$0.20"
    assert migrations.show("price", Decimal("0.0375")) == "$0.0375"
    assert migrations.show("share", Decimal("0.5")) == "50%"


def test_retirement_is_news_on_either_side_and_never_compared():
    old, new = _m(retirement_date=date(2026, 11, 11)), _m(id="mv_b")
    assert _rows(old, new)["retirement_date"]["change"] == "from_set"
    late = _m(id="mv_b", retirement_date=date(2027, 1, 1))
    assert _rows(_m(), late)["retirement_date"]["change"] == "to_set"
    lines = migrations.checklist(old, new, migrations.diff(old, new, R), R)
    assert any("Claude A is set to retire on 2026-11-11" in x for x in lines)


def test_the_checklist_says_what_breaks_and_always_ends_on_testing():
    a = _m()
    b = _m(id="mv_b", display_name="Anthropic: Claude B", advertised_context=200_000,
           supports_tools=None)
    lines = migrations.checklist(a, b, migrations.diff(a, b, R), R)
    assert any("Claude B reads at most 200,000 tokens per request" in x for x in lines)
    assert any("Whether Claude B supports tool calling is not published" in x for x in lines)
    assert lines[-1].startswith("Run your own test set on Claude B")


def test_another_provider_is_said_once_with_its_name():
    a, b = _m(), _m(id="mv_b", canonical_id="openai/gpt-x", display_name="OpenAI: GPT X")
    lines = migrations.checklist(a, b, migrations.diff(a, b, R), R)
    assert sum("different providers" in x for x in lines) == 1
    assert any("check OpenAI's own documentation" in x for x in lines)


def test_the_direction_is_the_titles_when_it_says_a_to_b():
    old = _m(display_name="Anthropic: Claude Opus 5.5", release_date=date(2026, 9, 22))
    new = _m(id="mv_b", display_name="Anthropic: Claude Haiku 5.5", release_date=date(2026, 10, 7))
    f, t, how = migrations.direction("Claude Haiku 5.5 to Claude Opus 5.5: Pay More", old, new)
    assert (f["id"], t["id"], how) == ("mv_b", "mv_a", "title")
    # A short form of the name counts: "Opus 5.5" for "Claude Opus 5.5".
    f, t, how = migrations.direction("Haiku 5.5 to Opus 5.5", old, new)
    assert (f["id"], how) == ("mv_b", "title")


def test_without_a_to_b_title_it_is_older_to_newer_and_says_so():
    old = _m(display_name="Anthropic: Claude Opus 5.5", release_date=date(2026, 9, 22))
    new = _m(id="mv_b", display_name="Anthropic: Claude Haiku 5.5", release_date=date(2026, 10, 7))
    f, t, how = migrations.direction("Claude Haiku 5.5 vs Claude Opus 5.5: Split", new, old)
    assert (f["id"], t["id"], how) == ("mv_a", "mv_b", "release")


def test_an_address_name_resolves_and_a_shared_one_does_not():
    models = [_m(), _m(id="mv_b", canonical_id="openai/claude-a")]
    assert migrations._resolve(models, "anthropic/claude-a")["id"] == "mv_a"
    assert migrations._resolve(models, "openai--claude-a")["id"] == "mv_b"
    assert migrations._resolve(models, "claude-a") is None   # two providers share it


def test_the_facts_endpoint_is_a_public_read():
    from starlette.requests import Request

    req = Request({"type": "http", "method": "GET", "path": "/guide-facts", "query_string": b"",
                   "headers": []})
    assert gate.is_public_read(req)


# ── #590 review ─────────────────────────────────────────────────────────────


def test_a_to_outside_the_two_names_names_no_order():
    old = _m(display_name="Anthropic: Claude Opus 5.5", release_date=date(2026, 9, 22))
    new = _m(id="mv_b", display_name="OpenAI: GPT-6.1 Sol", release_date=date(2026, 9, 29))
    for title in ("Claude Opus 5.5 vs GPT-6.1 Sol: which to pick",
                  "How to move between GPT-6.1 Sol and Claude Opus 5.5"):
        f, t, how = migrations.direction(title, new, old)
        assert (f["id"], t["id"], how) == ("mv_a", "mv_b", "release"), title


def test_a_name_inside_a_longer_name_is_not_found_there():
    five = _m(display_name="Anthropic: Claude Opus 5", release_date=date(2026, 7, 24))
    five5 = _m(id="mv_b", display_name="Anthropic: Claude Opus 5.5", release_date=date(2026, 9, 22))
    f, t, how = migrations.direction("Claude Opus 5.5 to Claude Opus 5: Pay Less", five, five5)
    assert (f["id"], t["id"], how) == ("mv_b", "mv_a", "title")


def test_both_models_retiring_says_both():
    a = _m(retirement_date=date(2026, 11, 11))
    b = _m(id="mv_b", display_name="Anthropic: Claude B", retirement_date=date(2027, 1, 1))
    rows = migrations.diff(a, b, R)
    assert {r["field"]: r for r in rows}["retirement_date"]["change"] == "both_set"
    lines = migrations.checklist(a, b, rows, R)
    assert any("Claude A is set to retire on 2026-11-11" in x for x in lines)
    assert any("Claude B itself is set to retire on 2027-01-01" in x for x in lines)


def test_a_price_keeps_its_published_decimals_at_every_size():
    assert migrations.show("price", Decimal("2.625")) == "$2.625"
    assert migrations.show("price", Decimal("15")) == "$15.00"
    assert migrations.show("price", Decimal("0")) == "$0.00"
