"""The Updates page (judge/updates.py, contract/updates.yaml, /updates).

Every update is rebuilt from data the board holds; only people's decisions are
stored. These pin the contract, the words each kind of update gets, and the
Manage decisions - approve, decline, style, edit with its numbers check, undo,
approve all - on a small hand-made registry.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

from judge import gate, updates
from judge.app import app
from tests.conftest import assert_disposable, assert_safe_target

NOW = datetime.now(UTC).replace(microsecond=0)


@pytest.fixture(autouse=True)
def _a_fresh_home_page_cache():
    """The home page's read is kept between requests; never between tests."""
    updates.clear_published_cache()
    yield
    updates.clear_published_cache()


TODAY = NOW.date()


# ── the contract ─────────────────────────────────────────────────────────────


def test_the_contract_is_complete_and_every_set_has_styles():
    r = updates.rules()
    assert set(r["templates"]) == set(updates.FACTS)
    assert set(r["kinds"]) == set(updates.KINDS)
    for name, styles in r["templates"].items():
        assert 2 <= len(styles) <= 4, f"{name}: 2 to 4 styles to pick from"


def test_a_template_naming_an_unknown_fact_is_refused(monkeypatch):
    import judge.config

    real = judge.config._read("updates.yaml")
    bad = json.loads(json.dumps(real))
    bad["templates"]["launch"][0]["headline"] = "{name} is {adjective}"
    monkeypatch.setattr(judge.config, "_read", lambda name: bad)
    with pytest.raises(updates.UpdatesContractError, match="adjective"):
        updates.rules()


def test_a_missing_key_is_refused_not_defaulted(monkeypatch):
    import judge.config

    monkeypatch.setattr(judge.config, "_read", lambda name: {"window_days": 30})
    with pytest.raises(updates.UpdatesContractError):
        updates.rules()


# ── how facts are written ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "shown"),
    [
        (0.25, "$0.25"),
        (1, "$1.00"),
        (0.888966, "$0.889"),
        (0.0616, "$0.0616"),
        (0.005, "$0.005"),
        (0, "free"),
        (None, None),
    ],
)
def test_money(value, shown):
    assert updates.money(value) == shown


@pytest.mark.parametrize(
    ("n", "shown"),
    [(1048576, "1M"), (262144, "256K"), (1050000, "1.05M"), (200000, "200K"), (None, None)],
)
def test_context(n, shown):
    assert updates.context(n) == shown


def test_when_and_names():
    assert updates.when(TODAY, TODAY) == "today"
    assert updates.when(TODAY + timedelta(days=13), TODAY) == "in 13 days"
    assert updates.when(TODAY - timedelta(days=3), TODAY) == "3 days ago"
    assert updates.names(["A"], 3) == "A"
    assert updates.names(["A", "B", "C"], 3) == "A, B and C"
    assert updates.names(["A", "B", "C", "D", "E"], 3) == "A, B, C and 2 more"


def test_a_style_whose_facts_are_missing_is_not_offered():
    r = updates.rules()
    facts = {"name": "Solo", "provider": "Acme", "date": "1 Oct", "context": "1M"}
    unpriced = {**facts, "unlisted": updates._unlisted(None, "1M")}
    offered = [s["id"] for s in updates.render({"template": "launch", "facts": unpriced}, r)]
    assert offered == ["name"], "every other launch style names a price this launch has not got"
    (only,) = updates.render({"template": "launch", "facts": unpriced}, r)
    assert only["detail"] == "An early listing for Acme's newest model: no price listed yet."
    priced = {**facts, "price": updates.launch_pricing(0.25, 1)}
    offered = [s["id"] for s in updates.render({"template": "launch", "facts": priced}, r)]
    assert "name" not in offered, "a listing with a price never says it has none"


def test_a_free_launch_says_so():
    assert updates.launch_pricing(0, 0) == "It is free to use"


# ── benchmarks, from changelog entries ───────────────────────────────────────


def entry(
    i,
    news,
    *,
    row="Model A",
    row_id="acme/a:max",
    column="Board",
    old=None,
    new=None,
    old_out_of=None,
    new_out_of=None,
    run_id=7,
    source_date=None,
):
    return {
        "id": i,
        "run_id": run_id,
        "changed_at": NOW.isoformat(),
        "row": row,
        "row_id": row_id,
        "column": column,
        "type": "added",
        "old": old,
        "new": new,
        "old_out_of": old_out_of,
        "new_out_of": new_out_of,
        "source_date": source_date,
        "news": news,
    }


def test_a_models_debuts_in_one_run_are_one_update():
    r = updates.rules()
    out = updates._benchmarks(
        [
            entry(1, "debut", column="SciCode", new="56.8"),
            entry(2, "debut", column="HLE", new="43.5"),
        ],
        {"acme/a": TODAY - timedelta(days=4)},
        {},
        r,
    )
    assert len(out) == 1
    (u,) = out
    assert u["template"] == "bench_debut_group"
    assert u["facts"]["count"] == 2 and u["facts"]["timing"] == "4 days after release"
    assert u["facts"]["boards"] == "HLE 43.5, SciCode 56.8"


def test_rank_one_is_its_own_headline_and_a_rank_column_never_doubles_a_score():
    r = updates.rules()
    out = updates._benchmarks(
        [
            entry(1, "mover", old="#3", new="#1", old_out_of=30, new_out_of=30),
            entry(2, "debut", column="Other", new="70", row_id="acme/b:max", row="Model B"),
            entry(
                3,
                "debut",
                column="Other",
                new="#9",
                new_out_of=30,
                row_id="acme/b:max",
                row="Model B",
            ),
        ],
        {},
        {},
        r,
    )
    assert sorted(u["template"] for u in out) == ["bench_debut", "bench_top"]
    top = next(u for u in out if u["template"] == "bench_top")
    assert updates.render(top, r)[0]["headline"] == "Model A takes the top spot on Board"


def test_a_place_change_below_first_is_not_an_update():
    """One model entering at #2 moves every model below it down a place."""
    r = updates.rules()
    moves = [
        entry(1, "mover", old="#2", new="#3", old_out_of=30, new_out_of=31),
        entry(2, "mover", old="#5", new="#4", old_out_of=30, new_out_of=30),
        entry(3, "mover", old="#1", new="#1", old_out_of=30, new_out_of=31),
    ]
    assert updates._benchmarks(moves, {}, {}, r) == []


def test_a_score_move_is_an_update():
    r = updates.rules()
    (u,) = updates._benchmarks([entry(1, "mover", old="71.2", new="74.0")], {}, {}, r)
    assert updates.render(u, r)[0]["headline"] == "Model A rises to 74.0 on Board"


def test_a_model_leaving_a_board_is_never_an_update():
    """A board stops listing a model for page, filter or matching reasons; a
    real retirement comes from the registry's retirement date instead."""
    r = updates.rules()
    gone = [
        entry(i, "dropped", column="LiveBench", old="60.7", row=f"M{i}", row_id=f"acme/m{i}:max")
        for i in range(1, 5)
    ]
    assert updates._benchmarks(gone, {}, {}, r) == []


def test_a_row_with_no_label_reads_as_the_registry_name_and_setting():
    e = entry(1, "fresh", row="x-ai/grok-4.5:xhigh", row_id="x-ai/grok-4.5:xhigh")
    assert updates._row_name(e, {"x-ai/grok-4.5": "xAI: Grok 4.5"}) == "Grok 4.5 (xhigh)"
    assert updates._row_name(e, {}) == "grok-4.5 (xhigh)"


# ── built from a registry ────────────────────────────────────────────────────


@pytest.fixture
def conn(test_dsn, monkeypatch):
    from collect.db import apply_schema

    assert_safe_target(test_dsn)
    monkeypatch.setenv("DATABASE_URL", test_dsn)
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        assert_disposable(c, test_dsn)
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        apply_schema(c)
        c.commit()
        yield c


def model(
    c, cid, display, *, released=None, ctx=None, p_in=None, p_out=None, retires=None, launched=False
):
    c.execute(
        "INSERT INTO model_version (id, canonical_id, provider, display_name, release_date, "
        "advertised_context, price_in, price_out, retirement_date, sources, provenance) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, '{}', 'polled')",
        (cid, cid, cid.split("/")[0], display, released, ctx, p_in, p_out, retires),
    )
    if launched:
        c.execute(
            "INSERT INTO model_event (id, model_version_id, type, occurred_at, detected_at) "
            "VALUES (%s, %s, 'new-model', %s, %s)",
            (f"ev-{cid}", cid, released, NOW - timedelta(hours=1)),
        )


def price(c, cid, hours_ago, p_in, p_out):
    c.execute(
        "INSERT INTO pricing_history (model_version_id, price_in, price_out, observed_at) "
        "VALUES (%s, %s, %s, %s)",
        (cid, p_in, p_out, NOW - timedelta(hours=hours_ago)),
    )


@pytest.fixture
def registry(conn):
    d = TODAY - timedelta(days=2)
    model(
        conn, "acme/solo", "Acme: Solo", released=d, ctx=1048576, p_in=0.25, p_out=1, launched=True
    )
    model(conn, "beta/one", "Beta: One", released=d, launched=True)
    model(conn, "beta/two", "Beta: Two", released=d, launched=True)
    model(conn, "gamma/old", "Gamma: Old", retires=TODAY + timedelta(days=10))
    model(conn, "delta/x", "Delta: X", retires=TODAY - timedelta(days=3))
    model(conn, "delta/y", "Delta: Y", retires=TODAY - timedelta(days=3))
    model(conn, "eps/cheap", "Eps: Cheap", p_in=0.5, p_out=1)
    price(conn, "eps/cheap", 200, 1, 2)
    price(conn, "eps/cheap", 72, 0.4, 1)  # down 60%, held three days
    conn.commit()
    return conn


def by_template(conn, data):
    """The listed updates by template set, which the page is not sent."""
    sets = {u["key"]: u["template"] for u in updates.build(conn, days=30, now=NOW)["updates"]}
    return {sets[u["key"]]: u for u in data["updates"]}


def test_every_kind_is_built_with_its_words(registry):
    data = updates.listing(registry, days=30, now=NOW)
    got = by_template(registry, data)
    assert got["launch"]["headline"] == "Acme launches Solo"
    assert got["launch"]["detail"] == (
        "The new model reads up to 1M tokens at once. It costs $0.25 per million input tokens "
        "and $1.00 per million output tokens."
    )
    assert got["launch_group"]["headline"] == "Beta launches 2 models at once"
    assert got["retiring"]["headline"] == "Old to be retired in 10 days"
    assert got["retiring"]["upcoming"] is True
    assert got["retired_group"]["headline"] == "Delta retires 2 models"
    assert got["retired_group"]["why"] == "Retirement date passed"  # why_by_set wins
    assert got["retiring"]["why"] == "Retirement date listed"
    cut = got["price_cut"]
    assert cut["headline"] == "Cheap gets cheaper: input $1.00 → $0.40"
    assert "%" not in cut["headline"] + cut["detail"], "prices, never percentages"
    assert cut["second_check"] is True, "a 60% move is past second_check_pct"
    assert data["saving"] is True and all(u["status"] == "pending" for u in data["updates"])
    for internal in ("facts", "models", "seen_at", "template"):
        assert internal not in cut, f"{internal} is not read by the page"
    assert any("Benchmark" in n for n in data["notes"])


def test_a_launch_outside_the_window_is_not_news(registry):
    model(registry, "acme/older", "Acme: Older", released=TODAY - timedelta(days=40), launched=True)
    keys = {u["key"] for u in updates.listing(registry, days=30, now=NOW)["updates"]}
    assert "launch:acme/older" not in keys


def built(conn, template):
    return next(
        u for u in updates.build(conn, days=30, now=NOW)["updates"] if u["template"] == template
    )


def listed(conn, key):
    return next(u for u in updates.listing(conn, days=30, now=NOW)["updates"] if u["key"] == key)


def test_approve_decline_and_undo(registry):
    u = built(registry, "launch")
    updates.review(registry, u, action="approve", by="parvathi.b@example.com")
    assert listed(registry, u["key"])["status"] == "approved"
    assert listed(registry, u["key"])["reviewed_by"] == "parvathi.b"
    updates.review(registry, u, action="decline", by="anooj@example.com")
    shown = listed(registry, u["key"])
    assert shown["status"] == "declined" and shown["undo"]["action"] == "decline"
    updates.undo(registry, u["key"], by="anooj@example.com")
    assert listed(registry, u["key"])["status"] == "approved"
    updates.undo(registry, u["key"], by="anooj@example.com")
    back = listed(registry, u["key"])
    assert back["status"] == "pending" and back["undo"] is None
    with pytest.raises(updates.ReviewRefused):
        updates.undo(registry, u["key"], by="anooj@example.com")


def test_a_style_change_is_kept_and_replaces_an_edit(registry):
    u = built(registry, "launch")
    updates.review(registry, u, action="edit", by="p@example.com", headline="Acme ships Solo")
    assert listed(registry, u["key"])["headline"] == "Acme ships Solo"
    updates.review(registry, u, action="style", by="p@example.com", style="context")
    shown = listed(registry, u["key"])
    assert (shown["style"], shown["headline"], shown["edited"]) == (
        "context",
        "Solo debuts with a 1M-token context window",
        False,
    )
    with pytest.raises(updates.ReviewRefused):
        updates.review(registry, u, action="style", by="p@example.com", style="nope")


def test_an_edit_with_a_new_number_needs_confirming(registry):
    u = built(registry, "price_cut")
    with pytest.raises(updates.EditNeedsConfirm) as refused:
        updates.review(
            registry, u, action="edit", by="p@example.com", headline="Cheap price cut 70%"
        )
    assert refused.value.numbers == ["70"]
    # Numbers the facts hold are fine without confirming.
    updates.review(
        registry,
        u,
        action="edit",
        by="p@example.com",
        headline="Cheap now $0.4 per million input tokens",
    )
    updates.review(
        registry, u, action="edit", by="p@example.com", headline="Cheap price cut 70%", confirm=True
    )
    assert listed(registry, u["key"])["headline"] == "Cheap price cut 70%"


def test_approve_all_leaves_a_declined_update_hidden(registry):
    every = updates.build(registry, days=30, now=NOW)["updates"]
    updates.review(registry, every[0], action="decline", by="p@example.com")
    done = updates.approve_all(registry, every, by="p@example.com")
    assert done["approved"] == len(every) - 1
    assert listed(registry, every[0]["key"])["status"] == "declined"


def test_without_the_review_tables_the_page_still_lists_and_says_saving_is_off(registry):
    registry.execute("DROP TABLE update_review_log, update_review")
    registry.commit()
    data = updates.listing(registry, days=30, now=NOW)
    assert data["updates"] and data["saving"] is False
    with pytest.raises(updates.SavingUnavailable):
        updates.review(
            registry, data["updates"][0] | {"facts": {}}, action="approve", by="p@example.com"
        )


def test_a_development_backend_on_a_shared_database_refuses_to_save(registry, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u@db.example.com:5432/shared")
    with pytest.raises(updates.SavingUnavailable):
        updates.review(registry, built(registry, "launch"), action="approve", by="p@example.com")


# ── the endpoints ────────────────────────────────────────────────────────────


def test_the_updates_page_is_not_a_public_read():
    from starlette.requests import Request

    for path in ("/updates", "/updates/review", "/updates/undo", "/updates/approve-all"):
        req = Request(
            {"type": "http", "method": "GET", "path": path, "query_string": b"", "headers": []}
        )
        assert not gate.is_public_read(req)
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        assert TestClient(app).get("/updates").status_code == 401


def test_an_unconfirmed_number_is_a_409_naming_it(registry, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    client = TestClient(app)
    listing = client.get("/updates?days=30")
    assert listing.status_code == 200, listing.text
    key = next(u["key"] for u in listing.json()["updates"] if u["key"].startswith("price:"))
    body = {"key": key, "action": "edit", "headline": "Cheap price cut 70%", "days": 30}
    refused = client.post("/updates/review", json=body)
    assert refused.status_code == 409
    assert refused.json()["detail"]["numbers"] == ["70"]
    assert client.post("/updates/review", json=body | {"confirm": True}).status_code == 200
    assert client.post("/updates/undo", json={"key": key}).json()["undid"] == "edit"


# ── weekly round-ups ─────────────────────────────────────────────────────────


def test_a_completed_week_with_enough_launches_gets_a_round_up_held_for_approval(conn):
    monday = TODAY - timedelta(days=TODAY.weekday() + 7)  # last week's Monday
    for i, ctx in enumerate((1048576, 200000, 2000000)):
        model(
            conn,
            f"acme/w{i}",
            f"Acme: W{i}",
            released=monday + timedelta(days=i),
            ctx=ctx,
            launched=True,
        )
    model(conn, "beta/w", "Beta: W", released=monday + timedelta(days=1), launched=True)
    conn.commit()
    data = updates.listing(conn, days=30, now=NOW)
    (roundup,) = [u for u in data["updates"] if u["kind"] == "roundup"]
    assert roundup["key"] == f"roundup:launch:{monday}"
    assert roundup["headline"] == "Week in launches: 4 new models"
    assert (
        roundup["detail"] == "The busiest makers were Acme (3) and Beta (1); "
        "2 of the new models read 1M+ tokens at once."
    )
    assert roundup["published"] is False, "a summary waits for a person"
    updates.review(conn, built_key(conn, roundup["key"]), action="approve", by="p@example.com")
    assert listed(conn, roundup["key"])["published"] is True


def test_the_week_in_progress_and_a_quiet_week_get_no_round_up(conn):
    this_monday = TODAY - timedelta(days=TODAY.weekday())
    for i in range(3):
        model(conn, f"acme/n{i}", f"Acme: N{i}", released=this_monday, launched=True)
    model(conn, "acme/q", "Acme: Q", released=this_monday - timedelta(days=3), launched=True)
    conn.commit()
    kinds = [u["kind"] for u in updates.listing(conn, days=30, now=NOW)["updates"]]
    assert "roundup" not in kinds


def built_key(conn, key):
    return next(u for u in updates.build(conn, days=30, now=NOW)["updates"] if u["key"] == key)


# ── publishing to the home page ──────────────────────────────────────────────


def test_only_an_approved_update_can_be_published(registry):
    u = built(registry, "launch")
    with pytest.raises(updates.ReviewRefused, match="approve it in Manage first"):
        updates.review(registry, u, action="publish", by="p@example.com")
    assert listed(registry, u["key"])["home"] is None


def test_publish_keeps_the_words_fixed_until_republished(registry):
    u = built(registry, "launch")
    updates.review(registry, u, action="approve", by="parvathi.b@example.com")
    updates.review(registry, u, action="publish", by="parvathi.b@example.com")
    shown = listed(registry, u["key"])
    assert shown["home"]["headline"] == "Acme launches Solo" and shown["home"]["current"] is True
    assert shown["home"]["by"] == "parvathi.b"
    updates.review(registry, u, action="style", by="p@example.com", style="context")
    changed = listed(registry, u["key"])
    assert changed["home"]["headline"] == "Acme launches Solo", "the home page keeps the old words"
    assert changed["home"]["current"] is False
    updates.review(registry, u, action="publish", by="p@example.com")
    assert listed(registry, u["key"])["home"]["headline"] == changed["headline"]
    updates.review(registry, u, action="unpublish", by="p@example.com")
    assert listed(registry, u["key"])["home"] is None


def test_declining_takes_it_off_the_home_page_and_undo_puts_it_back(registry):
    u = built(registry, "launch")
    updates.review(registry, u, action="approve", by="p@example.com")
    updates.review(registry, u, action="publish", by="p@example.com")
    updates.review(registry, u, action="decline", by="p@example.com")
    assert listed(registry, u["key"])["home"] is None
    with pytest.raises(updates.ReviewRefused, match="approve it in Manage first"):
        updates.review(registry, u, action="publish", by="p@example.com")
    updates.undo(registry, u["key"], by="p@example.com")
    back = listed(registry, u["key"])
    assert back["status"] == "approved" and back["home"]["headline"] == "Acme launches Solo"


def test_a_round_up_is_published_only_once_approved(conn):
    monday = TODAY - timedelta(days=TODAY.weekday() + 7)
    for i in range(3):
        model(conn, f"acme/r{i}", f"Acme: R{i}", released=monday, launched=True)
    conn.commit()
    roundup = built_key(conn, f"roundup:launch:{monday}")
    with pytest.raises(updates.ReviewRefused, match="approve it in Manage first"):
        updates.review(conn, roundup, action="publish", by="p@example.com")
    updates.review(conn, roundup, action="approve", by="p@example.com")
    updates.review(conn, roundup, action="publish", by="p@example.com")
    assert listed(conn, roundup["key"])["home"] is not None


def test_every_price_shape_offers_an_on_openrouter_style():
    """The other styles keep the model as the subject; this one names where the
    price was seen, for the cases that need it (Parvathi, 2026-10-29)."""
    r = updates.rules()
    for name, styles in r["templates"].items():
        if name.startswith("price_") or name == "roundup_price":
            ours = [s for s in styles if s["id"] == "openrouter"]
            assert ours, f"{name} has no On OpenRouter style"
            assert "OpenRouter" in ours[0]["headline"] + ours[0]["detail"]


# ── the home page's public read ──────────────────────────────────────────────


def test_the_home_strip_sends_only_published_words(registry):
    u = built(registry, "launch")
    other = built(registry, "launch_group")
    updates.review(registry, u, action="approve", by="parvathi.b@example.com")
    updates.review(registry, u, action="publish", by="parvathi.b@example.com")
    updates.review(registry, other, action="approve", by="p@example.com")  # approved, not published
    updates.review(registry, u, action="style", by="p@example.com", style="context")
    (item,) = updates.published(registry)["updates"]
    assert set(item) == {"key", "kind", "label", "headline", "detail", "published_at", "verify"}
    assert item["headline"] == "Acme launches Solo", "the published words, not the restyled ones"
    assert "parvathi" not in str(item), "no reviewer reaches the public strip"
    updates.review(registry, u, action="decline", by="p@example.com")
    assert updates.published(registry)["updates"] == []


def test_the_home_strip_is_a_public_read(registry, monkeypatch):
    from starlette.requests import Request

    req = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/updates/published",
            "query_string": b"",
            "headers": [],
        }
    )
    assert gate.is_public_read(req)
    monkeypatch.setenv("API_TOKEN", "s3cret")
    client = TestClient(app)
    assert client.get("/updates/published").status_code == 200
    assert client.get("/updates").status_code == 401, "Manage's data stays signed-in"


# ── prices measured from the settled price ───────────────────────────────────


def price_keys(conn):
    return [
        u for u in updates.build(conn, days=30, now=NOW)["updates"] if u["kind"].startswith("price")
    ]


def test_a_rebound_to_the_usual_price_is_not_news(conn):
    """$0.15 -> $0.045 -> $0.15: the last step is "+233%" from the step before,
    and nothing over the week."""
    model(conn, "z/glm", "Z: GLM", p_in=0.15, p_out=0.5)
    price(conn, "z/glm", 400, 0.15, 0.5)
    price(conn, "z/glm", 120, 0.045, 0.14)
    price(conn, "z/glm", 48, 0.15, 0.5)
    conn.commit()
    assert price_keys(conn) == [], "a cut that came back inside the week, and its rebound"


def test_a_price_that_keeps_flipping_gets_no_headline(conn):
    model(conn, "z/flip", "Z: Flip", p_in=0.1, p_out=0.4)
    for hours, p_in in ((400, 0.3), (300, 0.1), (200, 0.3), (100, 0.1)):
        price(conn, "z/flip", hours, p_in, 0.4)
    conn.commit()
    assert price_keys(conn) == []


def test_one_move_in_two_steps_is_one_update_measured_from_the_settled_price(conn):
    model(conn, "d/v4", "DeepSeek: V4", p_in=0.021, p_out=0.28)
    price(conn, "d/v4", 600, 0.14, 0.28)
    price(conn, "d/v4", 150, 0.03, 0.28)
    price(conn, "d/v4", 60, 0.021, 0.28)
    conn.commit()
    (u,) = price_keys(conn)
    assert u["styles"][0]["headline"] == "V4 gets cheaper: input $0.14 → $0.021"


def test_one_price_down_and_the_other_up_is_a_price_change_never_cheaper(conn):
    model(conn, "d/pro", "DeepSeek: Pro", p_in=0.3995, p_out=4.2)
    price(conn, "d/pro", 600, 1.188, 3.564)
    price(conn, "d/pro", 60, 0.3995, 4.2)
    conn.commit()
    (u,) = price_keys(conn)
    assert u["kind"] == "price_change"
    assert u["styles"][0]["headline"] == (
        "Pro changes price: input down to $0.3995, output up to $4.20"
    )
    assert "cheaper" not in u["styles"][0]["headline"]


# ── the home page after publishing (#585 review) ──────────────────────────────


def publish(conn, update):
    updates.review(conn, update, action="approve", by="p@example.com")
    updates.review(conn, update, action="publish", by="p@example.com")


def test_a_headline_leaves_the_home_page_after_home_days_and_is_listed_as_removed(registry):
    u = built(registry, "launch")
    publish(registry, u)
    days = updates.rules()["home_days"]
    assert [i["key"] for i in updates.published(registry)["updates"]] == [u["key"]]
    later = NOW + timedelta(days=days, hours=1)
    assert updates.published(registry, now=later)["updates"] == []
    shown = next(
        i for i in updates.listing(registry, days=90, now=later)["updates"] if i["key"] == u["key"]
    )
    assert shown["home"]["on_home"] is False and shown["home"]["removed"] == "expired"


def test_a_published_update_no_longer_in_the_data_can_still_be_unpublished(registry):
    """A published price cut that later did not last stops being built; it is
    still listed, comes off the home page by itself, and can be unpublished."""
    u = built(registry, "price_cut")
    publish(registry, u)
    price(registry, "eps/cheap", 24, 1, 2)  # back to the settled price: the cut did not last
    registry.commit()
    assert updates.published(registry)["updates"] == [], "a reverted cut leaves the home page"
    gone = next(
        i for i in updates.listing(registry, days=30, now=NOW)["updates"] if i["key"] == u["key"]
    )
    assert gone["gone"] is True and gone["home"]["removed"] == "not_in_data"
    assert gone["headline"] == u["styles"][0]["headline"], "shown in its published words"
    stored = updates.stored_update(registry, u["key"])
    with pytest.raises(updates.ReviewRefused, match="no longer in the data"):
        updates.review(registry, stored, action="publish", by="p@example.com")
    updates.review(registry, stored, action="unpublish", by="p@example.com")
    assert all(i["key"] != u["key"] for i in updates.listing(registry, days=30, now=NOW)["updates"])


def test_the_home_page_shows_at_most_home_limit(registry, monkeypatch):
    every = updates.build(registry, days=30, now=NOW)["updates"]
    for u in every[:3]:
        publish(registry, u)
    real = updates.rules

    def two():
        r = real()
        return {**r, "home_limit": 2}

    monkeypatch.setattr(updates, "rules", two)
    assert len(updates.published(registry)["updates"]) == 2


# ── #585 follow-ups ───────────────────────────────────────────────────────────


def test_a_retirement_whose_date_changed_leaves_the_home_page(registry):
    u = built(registry, "retiring")
    publish(registry, u)
    assert [i["key"] for i in updates.published(registry)["updates"]] == [u["key"]]
    registry.execute(
        "UPDATE model_version SET retirement_date = %s WHERE canonical_id = 'gamma/old'",
        (TODAY + timedelta(days=40),),
    )
    registry.commit()
    updates.clear_published_cache()
    assert updates.published(registry)["updates"] == [], "the old date is no longer true"
    gone = next(
        i for i in updates.listing(registry, days=30, now=NOW)["updates"] if i["key"] == u["key"]
    )
    assert gone["gone"] is True and gone["home"]["removed"] == "not_in_data"


def test_undo_never_puts_an_update_no_longer_in_the_data_back_on_the_home_page(registry):
    u = built(registry, "retiring")
    publish(registry, u)
    registry.execute(
        "UPDATE model_version SET retirement_date = %s WHERE canonical_id = 'gamma/old'",
        (TODAY + timedelta(days=40),),
    )
    registry.commit()
    updates.review(
        registry, updates.stored_update(registry, u["key"]), action="unpublish", by="p@example.com"
    )
    assert updates.is_gone(registry, u["key"])
    with pytest.raises(updates.ReviewRefused, match="old words"):
        updates.undo(registry, u["key"], by="p@example.com", gone=True)


def test_the_home_page_read_is_kept_and_a_save_clears_it(registry):
    u = built(registry, "launch")
    updates.review(registry, u, action="approve", by="p@example.com")
    assert updates.published(registry)["updates"] == []
    registry.execute(
        "UPDATE update_review SET home_headline = 'x', home_detail = 'y', home_published_by = 'p', "
        "home_published_at = now() WHERE update_key = %s",
        (u["key"],),
    )
    registry.commit()
    assert updates.published(registry)["updates"] == [], "kept for home_cache_seconds"
    updates.review(registry, u, action="publish", by="p@example.com")
    assert [i["key"] for i in updates.published(registry)["updates"]] == [u["key"]]
