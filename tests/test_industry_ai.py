"""The Industry AI agent (2026-11-20): rules, pipeline, cap, store and page.

The fixture cases are the plan's (§12): each says what the real contract,
contract/industry_ai.yaml, must make of one post. A change to the contract that
breaks one of them is a change in what the agent collects, and should be seen.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import pytest
import yaml

from collect.industry_ai import config as iai_config
from collect.industry_ai.config import CONTRACT, IndustryAIConfigError
from collect.industry_ai.pipeline import evaluate
from collect.industry_ai.rules import Item, canonical_url, filter_reason, sieve

NOW = datetime(2026, 11, 20, tzinfo=UTC)
SINCE = NOW - timedelta(days=365)


@pytest.fixture(scope="module")
def cfg():
    return iai_config.load()


def item(
    text,
    *,
    title="",
    platform="reddit",
    hints=("finance",),
    iid=None,
    author="t2_a",
    created=None,
    link=None,
    lang=None,
    engagement=None,
):
    iid = iid or f"{platform}:{abs(hash((title, text, platform))) % 10**8}"
    return Item(
        id=iid,
        platform=platform,
        external_id=iid.split(":", 1)[1],
        url=f"https://e.x/{iid}",
        title=title,
        body=text,
        created_at=created or NOW - timedelta(days=3),
        author_id=author,
        lang=lang,
        engagement=engagement or {"score": 5},
        link=link,
        domain_hints=set(hints),
        query_keys={f"iai:{hints[0]}:{platform}:q"},
    )


def one(cfg, it):
    results, _ = evaluate([it], cfg, since=SINCE)
    return results[it.id]


# ── the contract ─────────────────────────────────────────────────────────────


def test_the_real_contract_loads_with_five_domains(cfg):
    assert list(cfg.domains) == [
        "finance",
        "healthcare",
        "hospitality",
        "engineering",
        "governance",
    ]
    assert cfg.type_order[-1] == "discussion"


@pytest.mark.parametrize(
    "mutate, says",
    [
        (lambda r: r["run"].pop("window_days"), "window_days"),
        (lambda r: r["run"]["max_requests"].pop("x"), "max_requests"),
        (lambda r: r["domains"]["finance"]["queries"].pop("bluesky"), "queries"),
        (lambda r: r["spam_patterns"].append("(unclosed"), "not a valid pattern"),
        (lambda r: r.pop("type_order"), "type_order"),
    ],
)
def test_a_missing_key_or_bad_pattern_is_refused(mutate, says):
    raw = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    raw = copy.deepcopy(raw)
    mutate(raw)
    with pytest.raises(IndustryAIConfigError, match=says):
        iai_config.parse(raw)


# ── the plan's fixture cases (§12) ───────────────────────────────────────────


def test_prompt_tips_are_kept_as_how_to(cfg):
    r = one(
        cfg,
        item(
            "Here are my favourite ChatGPT prompts for month-end close.",
            title="10 helpful prompts for accountants",
        ),
    )
    assert r.verdict == "kept" and r.domains == ["finance"] and r.content_type == "how_to"


def test_a_deployment_is_a_use_case_with_its_stage(cfg):
    r = one(
        cfg,
        item(
            "Our bank rolled out an AI fraud detection step in production this year; "
            "false positives fell 20% and the team reviews fewer alerts."
        ),
    )
    assert r.verdict == "kept" and r.domains == ["finance"]
    assert r.content_type == "use_case" and r.stage_guess == "deployed"


def test_a_pilot_is_a_use_case_pilot(cfg):
    r = one(
        cfg,
        item(
            "Two clinics piloted AI ambient scribe tools for six weeks with their physicians.",
            hints=("healthcare",),
        ),
    )
    assert r.content_type == "use_case" and r.stage_guess == "pilot" and r.domains == ["healthcare"]


def test_prompt_engineering_is_not_engineering(cfg):
    r = one(
        cfg,
        item(
            "Mastering prompt engineering for beginners with ChatGPT and other LLM tools.",
            hints=("engineering",),
        ),
    )
    assert r.verdict == "dropped" and r.reason == "no_domain_term"


def test_an_ai_file_is_not_an_ai_term(cfg):
    r = one(
        cfg, item("Export your bank logo as .ai and send the file to the accounting team today.")
    )
    assert r.verdict == "dropped" and r.reason == "no_ai_term"


def test_artificial_insemination_is_not_ai(cfg):
    r = one(
        cfg,
        item(
            "Artificial insemination outcomes at the clinic improved for our patients "
            "and the hospital staff.",
            hints=("healthcare",),
        ),
    )
    assert r.reason == "no_ai_term"


def test_trading_bot_spam_is_dropped(cfg):
    r = one(
        cfg,
        item("AI trading bot, 1000% returns for our banking clients, join my signals group now!"),
    )
    assert r.verdict == "dropped" and r.reason == "spam"


def test_a_signup_ad_is_dropped_but_a_teaching_course_is_kept(cfg):
    ad = one(
        cfg,
        item(
            "Register now: free AI webinar for hoteliers, limited seats for hotel managers.",
            hints=("hospitality",),
        ),
    )
    assert ad.reason == "signup_ad"
    course = one(
        cfg,
        item(
            "Register now for our course: here is how hotels use AI tools to answer "
            "guest booking questions, step by step.",
            hints=("hospitality",),
        ),
    )
    assert course.verdict == "kept" and course.content_type == "how_to"


def test_a_hiring_post_is_dropped(cfg):
    r = one(cfg, item("We're hiring an ML engineer for our fintech team to build LLM tools."))
    assert r.reason == "hiring"


def test_ai_governance_is_out_of_governance_scope(cfg):
    r = one(cfg, item("Our AI governance framework for LLM risk reviews.", hints=("governance",)))
    assert r.reason == "no_domain_term"


def test_an_ambiguous_term_needs_its_context(cfg):
    plain = one(cfg, item("I used ChatGPT on the river bank last weekend, lovely day."))
    assert plain.reason == "no_domain_term"
    banked = one(cfg, item("Our bank uses an LLM to answer customer loan account questions."))
    assert banked.verdict == "kept"


# ── dedupe and domains ───────────────────────────────────────────────────────


def test_the_same_article_on_three_platforms_is_one_item_with_two_shares(cfg):
    link = "https://news.example.com/banks-ai-underwriting?utm_source=x&utm_medium=social"
    a = item(
        "How banks use AI underwriting tools for loans, a long read on lending teams.",
        platform="hackernews",
        iid="hackernews:1",
        link=link,
        created=NOW - timedelta(days=5),
    )
    b = item(
        "Banks and AI underwriting: lending teams describe their LLM workflow in detail.",
        platform="x",
        iid="x:2",
        link="https://news.example.com/banks-ai-underwriting",
        author="x_b",
        created=NOW - timedelta(days=4),
    )
    c = item(
        "Worth reading on AI in banking underwriting and loan decisions by lending teams.",
        platform="reddit",
        iid="reddit:3",
        link=link + "&ref=hn",
        author="t2_c",
        created=NOW - timedelta(days=3),
    )
    results, counts = evaluate([a, b, c], cfg, since=SINCE)
    assert results["hackernews:1"].verdict == "kept" and results["hackernews:1"].share_count == 2
    assert results["x:2"].reason == "shared_link" and results["reddit:3"].reason == "shared_link"
    assert counts["domains"]["finance"]["kept"] == 1


def test_canonical_url_drops_tracking_and_www():
    assert (
        canonical_url("https://www.Example.com/a/?utm_source=x&id=7#top")
        == "https://example.com/a?id=7"
    )
    assert canonical_url("not a url") is None


def test_a_post_confirmed_for_two_domains_counts_in_both(cfg):
    r = one(
        cfg,
        item(
            "Government agencies and banks both piloted LLM tools for loan and benefits "
            "claims processing in the public sector.",
            hints=("finance", "governance"),
        ),
    )
    assert r.domains == ["finance", "governance"]


def test_an_unconfirmed_domain_is_its_own_bucket(cfg):
    it = item(
        "Our hospital rolled out an LLM for discharge notes for clinicians.", hints=("finance",)
    )
    results, counts = evaluate([it], cfg, since=SINCE)
    r = results[it.id]
    assert r.verdict == "kept" and r.domains == [] and "also_matches:healthcare" in r.flags
    assert counts["domains"]["unconfirmed"]["kept"] == 1 and "finance" not in counts["domains"]


def test_an_old_item_is_outside_the_window_and_an_undated_one_is_not(cfg):
    old = item(
        "Our bank rolled out an AI fraud detection model.", created=NOW - timedelta(days=900)
    )
    assert one(cfg, old).reason == "outside_window"
    undated = item("Our bank rolled out an AI fraud detection model for loan customers.")
    undated.created_at = None
    assert one(cfg, undated).verdict == "kept"


def test_a_repeated_post_by_one_author_is_kept_once(cfg):
    text = "Our accounting firm uses ChatGPT to draft invoice reminders every week for clients."
    a = item(text, iid="reddit:10", created=NOW - timedelta(days=6))
    b = item(text, iid="reddit:11", created=NOW - timedelta(days=2))
    results, _ = evaluate([a, b], cfg, since=SINCE)
    assert results["reddit:11"].reason == "repeat_post"
    assert "repeat_author" in results["reddit:10"].flags


def test_low_engagement_is_a_flag_not_a_drop(cfg):
    _, flags = filter_reason(
        item("Our bank uses an LLM for loan customer emails every day.", engagement={"score": 0}),
        cfg,
    )
    assert "low_engagement" in flags


def test_github_items_are_tools_unless_they_state_a_use(cfg):
    r = one(
        cfg,
        item(
            "An LLM toolkit for accounting reconciliation workflows.",
            platform="github",
            title="fintech-llm-recon",
        ),
    )
    assert r.content_type == "tool_or_product"


def test_a_dropped_item_is_never_labelled(cfg):
    r = one(cfg, item("AI trading bot 1000% returns for banking, guaranteed profit, signals group"))
    assert r.verdict == "dropped" and r.content_type is None and r.domains == []


def test_sieve_needs_any_domains_terms(cfg):
    why, matched = sieve(item("ChatGPT wrote my poem."), cfg)
    assert why == "no_domain_term" and matched == {}


# ── the request cap ──────────────────────────────────────────────────────────


def test_a_query_past_the_cap_is_not_run_and_says_so(cfg, monkeypatch):
    from collect.industry_ai import harvest as h

    calls = []

    class Fake(h._Runner):
        def __init__(self, *a, **k):
            pass

        def run(self, query):
            calls.append(query)
            return [], 1, ""

    monkeypatch.setitem(h._RUNNERS, "hackernews", Fake)
    import dataclasses

    run = dict(cfg.run)
    run["max_requests"] = {**cfg.run["max_requests"], "hackernews": 2}
    small = dataclasses.replace(cfg, run=run)

    class Contract:
        platforms = [{"id": "hackernews"}]
        feeds = []
        rulings = {}

    out = h.harvest(
        small,
        domains=["finance"],
        platforms=["hackernews"],
        contract=Contract(),
        store=None,
        client_factory=lambda **k: None,
        since=SINCE,
        log=lambda s: None,
    )
    assert len(calls) == 2 and out.requests["hackernews"] == 2
    statuses = [q.status for q in out.queries]
    assert statuses == ["ok", "ok", "capped"]


def test_the_plan_lists_every_query_without_a_request(cfg):
    from collect.industry_ai.harvest import plan

    planned = plan(cfg, domains=["finance"], platforms=["reddit", "x"])
    assert ("finance", "reddit", "r/Accounting") in planned
    assert all(p in ("reddit", "x") for _, p, _ in planned)


# ── the store and the page ───────────────────────────────────────────────────


@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema, connect
    from tests.conftest import assert_disposable, assert_safe_target

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_store_label_and_the_page_counts_only(conn, cfg):
    from collect.industry_ai import store
    from judge.industry_ai.view import industry_ai_view

    store.start_run(
        conn,
        "iai-test",
        mode="harvest",
        domains=["finance"],
        platforms=["reddit"],
        pipeline_version=cfg.pipeline_version,
    )
    kept = item(
        "Our bank rolled out an AI fraud detection model in production for loan customers.",
        iid="reddit:1",
    )
    spam = item(
        "AI trading bot 1000% returns for banking, join my signals group",
        iid="reddit:2",
        author="t2_b",
    )
    assert store.upsert_items(conn, [kept, spam], run_id="iai-test") == 2
    # Found again by another query: no new row, the hint widens.
    again = item(kept.body, iid="reddit:1", hints=("governance",))
    assert store.upsert_items(conn, [again], run_id="iai-test") == 0
    items = store.load_items(conn)
    assert {i.id: sorted(i.domain_hints) for i in items}["reddit:1"] == ["finance", "governance"]
    results, counts = evaluate(items, cfg, since=SINCE)
    store.write_labels(conn, results, pipeline_version=cfg.pipeline_version)
    store.finish_run(
        conn,
        "iai-test",
        status="ok",
        requests={"reddit": 2},
        quota={},
        queries=[],
        counts=counts,
        detail="test",
    )
    conn.commit()

    view = industry_ai_view(conn)
    finance = next(d for d in view["domains"] if d["key"] == "finance")
    assert view["collected"] == 2 and view["kept"] == 1
    assert finance["kept"] == 1 and finance["by_type"] == {"use_case": 1}
    assert {r["reason"] for r in view["dropped"]} == {"spam"}
    assert view["last_run"]["status"] == "ok"
    # COUNTS ONLY: no post text, link or author anywhere in the payload.
    blob = repr(view)
    for leak in ("fraud detection model", "signals group", "https://e.x", "t2_a", "t2_b"):
        assert leak not in blob
