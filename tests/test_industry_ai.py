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


def test_the_real_contract_loads_with_the_umbrellas_and_their_rotation(cfg):
    # The 20 persona umbrellas (anooj, 2026-11-20); Parvathi's first five are among them.
    assert {"finance", "healthcare", "hospitality", "engineering", "governance"} <= set(cfg.domains)
    assert len(cfg.domains) == 20
    # 2026-11-25 (anooj): every domain on except the six whose keywords still name an
    # AI term by themselves (test below); those follow once their keywords are fixed.
    assert set(cfg.domains) - set(cfg.active_domains) == {
        "governance", "engineering", "hospitality", "film", "automotive", "sales_support",
    }
    # Two groups of ten, each domain in one, alternating by UTC day.
    a, b = cfg.group_domains("a"), cfg.group_domains("b")
    assert len(a) == len(b) == 10 and not set(a) & set(b) and set(a) | set(b) == set(cfg.domains)
    assert cfg.run["cadence"] == "daily"
    assert cfg.type_order[-1] == "discussion"


def test_the_groups_alternate_every_utc_day_across_a_year_end(cfg):
    from datetime import date

    start = date(2026, 12, 29)
    days = [cfg.group_for(start + timedelta(days=i)) for i in range(6)]
    assert days == ["a", "b", "a", "b", "a", "b"] or days == ["b", "a", "b", "a", "b", "a"]


@pytest.mark.parametrize("mutate, says", [
    (lambda g: g["a"].append(g["b"][0]), "one only"),
    (lambda g: g["b"].pop(), "in no group"),
    (lambda g: g["a"].append("no_such_domain"), "no domain"),
    (lambda g: g.update(c=["finance"]), "exactly"),
])
def test_the_rotation_is_refused_unless_every_domain_is_in_one_group(mutate, says):
    raw = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    mutate(raw["run"]["rotation"]["groups"])
    with pytest.raises(IndustryAIConfigError, match=says):
        iai_config.parse(copy.deepcopy(raw))


def test_no_active_domain_term_is_an_ai_term_by_itself(cfg):
    """A domain term that names an AI term ("AI adoption") passes the AI test and the domain
    test with one phrase, so general AI talk is filed under that domain (#645 review, point 1).
    In an ACTIVE domain such a phrase belongs in `ambiguous_terms`, with a context. Inactive
    domains (governance's ai_policy group) are fixed before they are switched on."""
    from collect.industry_ai.rules import ai_terms_found

    found = []
    for dk in cfg.active_domains:
        d = cfg.domains[dk]
        blocks = [(dk, d.terms)] + [(f"{dk}/{gk}", g.terms) for gk, g in d.groups.items()]
        for where, t in blocks:
            found += [f"{where}: {term!r}" for term in t.domain_terms if ai_terms_found(term, cfg)]
    assert not found, "AI-term domain terms in active domains: " + "; ".join(found)


def test_every_x_query_in_the_contract_gets_its_clubbed_pages(cfg):
    """Each grouped X query clubs at least `x_clubbed_min_keywords` keywords, so none of
    them silently falls back to one page (the generator balances the lists)."""
    lists = [d.terms for d in cfg.domains.values()] + [
        g.terms for d in cfg.domains.values() for g in d.groups.values()
    ]
    for t in lists:
        for q in t.queries["x"]["search"]:
            if q.count('" OR "'):
                assert cfg.x_pages(q) == cfg.run["pages_per_query"]["x_clubbed"], q


def test_no_term_is_deleted_by_its_own_exclusions(cfg):
    """A domain or group term that its own `exclude_phrases` (or the global ones) remove can
    never confirm a post: the exclusions run before the terms are matched. Found on #645:
    `software_ai` excluded "prompt engineering" while listing it as a keyword."""
    dead = []
    for dk, d in cfg.domains.items():
        blocks = [(dk, d.terms)] + [(f"{dk}/{gk}", g.terms) for gk, g in d.groups.items()]
        for where, t in blocks:
            patterns = list(t.exclude_phrases) + list(cfg.global_exclude)
            for term in t.domain_terms:
                if any(p.search(term) for p in patterns):
                    dead.append(f"{where}: {term!r}")
    assert not dead, "terms their own exclusions delete: " + "; ".join(dead)


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


def test_prompt_engineering_is_software_ai_not_physical(cfg):
    # Changed 2026-11-20 (anooj, #645): prompt engineering is software and AI work, so it
    # counts for engineering/software_ai. It must still never count for engineering/physical,
    # which keeps the exclusion - the flood the plan's risk table was about.
    r = one(
        cfg,
        item(
            "Mastering prompt engineering for beginners with ChatGPT and other LLM tools.",
            hints=("engineering",),
        ),
    )
    assert r.verdict == "kept"
    assert r.domains == ["engineering"]
    assert "engineering/software_ai" in r.groups
    assert "engineering/physical" not in r.groups


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


def test_ai_policy_is_in_governance_scope(cfg):
    """anooj's decision, #644 review point 5: Governance covers AI policy and
    governance practice too. Data and corporate governance stay out."""
    r = one(
        cfg,
        item(
            "Our AI governance framework for LLM risk reviews, under the AI Act.",
            hints=("governance",),
        ),
    )
    assert r.verdict == "kept" and r.domains == ["governance"]
    out = one(
        cfg, item("Our data governance team adopted an LLM catalogue tool.", hints=("governance",))
    )
    assert out.reason == "no_domain_term"


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
    why, matched, ai = sieve(item("ChatGPT wrote my poem."), cfg)
    assert why == "no_domain_term" and matched == {} and ai == ["ChatGPT"]


# ── the request cap ──────────────────────────────────────────────────────────


def test_a_query_past_the_cap_is_not_run_and_says_so(cfg, monkeypatch):
    from collect.industry_ai import harvest as h

    calls = []

    class Fake(h._Runner):
        def __init__(self, *a, **k):
            pass

        def run(self, query):
            calls.append(query)
            return [], 1, "", None

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
    # As many HN queries as the contract gives finance: the first two run, every one after
    # the cap is named "capped", never silently skipped. Counted from the contract, so adding
    # queries there does not break this test.
    n = len(cfg.domains["finance"].terms.queries["hackernews"]["search"])
    assert n > 2
    assert statuses == ["ok", "ok"] + ["capped"] * (n - 2)


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


def test_batched_writes_count_new_rows_and_label_every_one(conn, cfg):
    """2026-11-24: upsert and labels are one batched `executemany` each (the first real
    run spent over 30 minutes on a round trip per item). At a realistic size, a batch
    mixing known and new posts still counts only the new, and every row is labelled."""
    from collect.industry_ai import store

    store.start_run(conn, "iai-batch", mode="harvest", domains=["finance"],
                    platforms=["reddit"], pipeline_version=cfg.pipeline_version)
    body = "Our bank rolled out an AI fraud detection model in production for loan customers."
    first = [item(body, iid=f"reddit:b{i}", author=f"t2_{i}") for i in range(300)]
    assert store.upsert_items(conn, first, run_id="iai-batch") == 300
    second = [item(body, iid=f"reddit:b{i}", author=f"t2_{i}") for i in range(200, 400)]
    assert store.upsert_items(conn, second, run_id="iai-batch") == 100, "only 300..399 are new"
    assert store.upsert_items(conn, [], run_id="iai-batch") == 0
    items = store.load_items(conn)
    results, _ = evaluate(items, cfg, since=SINCE)
    assert store.write_labels(conn, results, pipeline_version=cfg.pipeline_version) == 400
    assert store.write_labels(conn, {}, pipeline_version=cfg.pipeline_version) == 0
    pending = conn.execute(
        "SELECT count(*) FROM iai_item WHERE drop_stage = 'pending'").fetchone()[0]
    assert pending == 0, "every row got its labels"


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
    engineering = next(d for d in view["domains"] if d["key"] == "engineering")
    assert [g["key"] for g in engineering["groups"]] == ["software_ai", "physical"]
    row = conn.execute(
        "SELECT matched_terms, ai_terms FROM iai_item WHERE id = 'reddit:1'"
    ).fetchone()
    assert "finance" in row[0] and row[1]
    assert view["last_run"]["status"] == "ok"
    # COUNTS ONLY: no post text, link or author anywhere in the payload.
    blob = repr(view)
    for leak in ("fraud detection model", "signals group", "https://e.x", "t2_a", "t2_b"):
        assert leak not in blob


# ── #644 review: structure, matched terms, fairness, switches, X ─────────────


def _raw():
    return copy.deepcopy(yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "mutate, says",
    [
        (lambda r: r["domains"]["finance"].update(accounts=["@x"]), "unknown key"),
        (lambda r: r["domains"]["finance"]["queries"]["x"].update(accounts=["@x"]), "unknown key"),
        (lambda r: r["run"].update(observer=True), "unknown key"),
        (lambda r: r.update(subcategories={}), "unknown key"),
        (lambda r: r["domains"]["finance"].update(kind="sector"), "kind"),
        (lambda r: r["domains"]["finance"].pop("active"), "active"),
        (lambda r: [d.update(active=False) for d in r["domains"].values()], "active: true"),
        (
            lambda r: r["domains"]["finance"]["queries"]["x"]["search"].append(
                " OR ".join(f'"keyword number {i}"' for i in range(30))
            ),
            "480",
        ),
    ],
)
def test_the_contract_refuses_what_the_code_does_not_read(mutate, says):
    """#644 review, points 3, 6 and 8: an unimplemented block (say X accounts
    before the observer exists) is refused, not ignored, and so is an X query X
    would cut off (point 10)."""
    raw = _raw()
    mutate(raw)
    with pytest.raises(IndustryAIConfigError, match=says):
        iai_config.parse(raw)


def test_engineering_has_two_groups_and_software_is_in_scope(cfg):
    """#644 review, point 4: Software & AI is a group of Engineering, and the
    software exclusions apply to the Physical group only."""
    sw = one(
        cfg,
        item(
            "Our team rolled out an AI code review step for every pull request.",
            hints=("engineering",),
        ),
    )
    assert sw.verdict == "kept" and sw.domains == ["engineering"]
    assert sw.groups == ["engineering/software_ai"]
    ph = one(
        cfg,
        item(
            "Our plant uses an LLM to plan predictive maintenance on the factory floor.",
            hints=("engineering",),
        ),
    )
    assert ph.groups == ["engineering/physical"]


def test_the_matched_terms_are_kept(cfg):
    """#644 review, point 2: which terms matched is stored, per domain and group."""
    r = one(cfg, item("Our accounting firm uses ChatGPT for invoice reconciliation every week."))
    assert set(r.matched_terms["finance"]["terms"]) >= {"accounting", "reconciliation", "invoice"}
    assert "ChatGPT" in r.ai_terms


def test_an_airline_pilot_is_not_a_pilot_programme(cfg):
    """#644 review, point 13."""
    r = one(
        cfg, item("Airline pilots now use an AI tool to brief flights.", hints=("hospitality",))
    )
    assert r.content_type != "use_case" or r.stage_guess != "pilot"
    prog = one(
        cfg,
        item(
            "The hotel ran a pilot program with an AI concierge for guests at the front desk.",
            hints=("hospitality",),
        ),
    )
    assert prog.content_type == "use_case" and prog.stage_guess == "pilot"


def test_x_pages_follow_the_number_of_keywords(cfg):
    six = " OR ".join(
        f'"{k}"'
        for k in (
            "invoice reconciliation",
            "bank reconciliation",
            "month-end close",
            "accounts payable",
            "accounts receivable",
            "expense categorization",
        )
    )
    assert cfg.x_pages(f"({six}) (AI OR LLM)") == cfg.run["pages_per_query"]["x_clubbed"]
    assert cfg.x_pages('"AI" accounting firm') == cfg.run["pages_per_query"]["x"]


def test_round_robin_gives_every_domain_its_first_query_first():
    """#644 review, point 7: under one cap per platform, file order no longer
    decides which domains get anything."""
    from collect.industry_ai.harvest import round_robin

    wanted = [
        ("finance", "f1"),
        ("finance", "f2"),
        ("finance", "f3"),
        ("healthcare", "h1"),
        ("governance", "g1"),
        ("governance", "g2"),
    ]
    assert round_robin(wanted)[:3] == [
        ("finance", "f1"),
        ("healthcare", "h1"),
        ("governance", "g1"),
    ]


def test_run_enabled_false_refuses_a_harvest(cfg, monkeypatch, capsys):
    """#644 review, point 9: the switch in the contract is read."""
    import dataclasses

    import scripts.run_industry_ai as script
    from collect.industry_ai import harvest

    off = dataclasses.replace(cfg, run={**cfg.run, "enabled": False})
    monkeypatch.setattr(iai_config, "load", lambda path=None: off)
    monkeypatch.setattr(harvest, "harvest", lambda *a, **k: pytest.fail("harvested while off"))
    assert script.main([]) == 0
    assert "run.enabled is false" in capsys.readouterr().out


def test_an_inactive_domain_is_not_run(cfg, monkeypatch):
    """#644 review, point 6: --domains narrows within the active domains."""
    import dataclasses

    import scripts.run_industry_ai as script

    domains = dict(cfg.domains)
    domains["hospitality"] = dataclasses.replace(domains["hospitality"], active=False)
    monkeypatch.setattr(
        iai_config, "load", lambda path=None: dataclasses.replace(cfg, domains=domains)
    )
    with pytest.raises(SystemExit, match="active: false"):
        script.main(["--plan", "--domains", "hospitality"])


# ── a failed search is an error, never "found nothing" (rule 4) ──────────────


def test_failure_of_reads_what_each_adapter_records():
    """The first dry run (#646): GitHub's 401s and dev.to's 429s showed as `ok`
    with 0 items, because nothing read the adapters' own failure records."""
    from types import SimpleNamespace

    from collect.industry_ai.harvest import failure_of

    assert failure_of(SimpleNamespace(http_errors=0)) is None
    assert failure_of(SimpleNamespace(http_errors=1, failures=["HTTP 429"])) == (
        "1 request(s) failed (HTTP 429)"
    )
    assert "rate-limited" in failure_of(SimpleNamespace(http_errors=1, rate_limited=True))
    assert "empty" in failure_of(SimpleNamespace(http_errors=0, empty_response=2))
    # A record without `http_errors` is a wrong input, not "nothing failed" (rule 12).
    with pytest.raises(AttributeError):
        failure_of(SimpleNamespace())


def test_a_failed_search_is_logged_as_error_and_keeps_partial_items(cfg, monkeypatch):
    import dataclasses

    from collect.industry_ai import harvest as h

    partial = item(
        "Our bank uses an LLM for loan customers.", platform="hackernews", iid="hackernews:9"
    )

    class Failing(h._Runner):
        def __init__(self, *a, **k):
            pass

        def run(self, query):
            return [partial], 1, "", "1 request(s) failed (HTTP 401)"

    monkeypatch.setitem(h._RUNNERS, "hackernews", Failing)
    run = {**cfg.run, "max_requests": {**cfg.run["max_requests"], "hackernews": 1}}

    class Contract:
        platforms = [{"id": "hackernews"}]
        feeds = []
        rulings = {}

    out = h.harvest(
        dataclasses.replace(cfg, run=run),
        domains=["finance"],
        platforms=["hackernews"],
        contract=Contract(),
        store=None,
        client_factory=lambda **k: None,
        since=SINCE,
        log=lambda s: None,
    )
    first = out.queries[0]
    assert first.status == "error" and "HTTP 401" in first.detail
    assert "hackernews:9" in out.items  # what did come back is kept

    # A runner written on the old three-value shape is an error, never "ok, 0 items".
    class OldShape(h._Runner):
        def __init__(self, *a, **k):
            pass

        def run(self, query):
            return [], 1, ""

    monkeypatch.setitem(h._RUNNERS, "hackernews", OldShape)
    out = h.harvest(
        dataclasses.replace(cfg, run=run),
        domains=["finance"],
        platforms=["hackernews"],
        contract=Contract(),
        store=None,
        client_factory=lambda **k: None,
        since=SINCE,
        log=lambda s: None,
    )
    assert out.queries[0].status == "error" and "ValueError" in out.queries[0].detail


def test_the_issue_summary_counts_failed_searches(cfg):
    """#648 review: a failed search is not a prune candidate, so the summary must
    name it, or the issue shows it nowhere."""
    import scripts.run_industry_ai as script

    queries = [
        {"status": "error", "items": 0},
        {"status": "error", "items": 3},
        {"status": "ok", "items": 0},
    ]
    body = script._summary(
        "r1", "dry-run", {}, {"items": 3, "kept": 0, "domains": {}}, queries, cfg
    )
    assert "2 query(ies) failed - see the run log." in body
    assert "1 query(ies) returned nothing - prune?" in body


def test_the_issue_summary_names_general_ai_apart_from_unconfirmed(cfg):
    """2026-11-24: the summary had its own bucket lookup, which called the observer's
    General AI bucket "Unconfirmed" - two different absences (rule 4). It now shares
    the run log's, shows posts the watch lists filed under a domain, and refuses a
    bucket it does not know."""
    import scripts.run_industry_ai as script

    row = {"kept": 2, "by_type": {"news": 2}, "authors": 2, "from_watch": 0}
    counts = {"items": 9, "kept": 6, "domains": {
        "general": row, "unconfirmed": row, "marketing": {**row, "from_watch": 3}}}
    body = script._summary("r1", "harvest", {}, counts, [], cfg)
    assert "| General AI | 2 |" in body and "| Domain unconfirmed | 2 |" in body
    assert "| Unconfirmed |" not in body
    assert body.rstrip().splitlines()[-1].endswith("| 3 |"), "from watch lists, counted apart"
    with pytest.raises(ValueError, match="unknown bucket"):
        script._summary("r1", "harvest", {}, {**counts, "domains": {"mystery": row}}, [], cfg)


def test_the_workflow_runs_the_group_then_the_observer_apart():
    """2026-11-25: a daily keyword run of today's group with no watch lists, then the
    observer in its own run - when the contract has it on, or the hand-start box is
    ticked - so each is its own `iai_run` row and summary."""
    from pathlib import Path

    wf = (Path(__file__).resolve().parents[1] / ".github" / "workflows"
          / "industry-ai-harvest.yml").read_text(encoding="utf-8")
    parsed = yaml.safe_load(wf)
    assert parsed[True]["schedule"] == [{"cron": "0 9 * * *"}], "daily"
    steps = parsed["jobs"]["harvest"]["steps"]
    keyword = next(s for s in steps if (s.get("name") or "").startswith("Keyword run"))
    observer = next(s for s in steps if (s.get("name") or "").startswith("Observer run"))
    assert 'args="--no-watch"' in keyword["run"] and "--group $GROUP" in keyword["run"]
    assert 'args="--watch-only"' in observer["run"]
    assert steps.index(keyword) < steps.index(observer)
    # A scheduled run takes today's group; the observer runs even if the keyword run failed.
    assert "github.event_name == 'schedule' && 'auto'" in wf
    assert observer["if"].startswith("${{ !cancelled()")
    assert "WATCH: ${{ inputs.watch }}" in wf
