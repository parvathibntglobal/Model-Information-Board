"""The AI assistants page (`/assistants`, judge/assistants.py, 2026-11-12, PROPOSED).

What the page promises and these pin:

* ABSENCE IS NOT A VERDICT. An assistant nobody reported on is `no_reports`,
  never "problems"; a member the registry does not hold is COUNTED in
  `not_in_registry`, never rendered or silently dropped.
* NOTHING UNGROUPED IS GUESSED INTO A GROUP. A registry agent in no group is
  listed under `unclassified`.
* THE BOARD'S RULES, NOT OURS. `declined` rows add nothing.
* COUNTS ONLY: no score, rank, quote, URL or document id anywhere in a payload.

Disposable Postgres only (`TEST_DATABASE_URL`).
"""

from __future__ import annotations

import contextlib
import json
import pathlib

import psycopg
import pytest
from fastapi.testclient import TestClient

from judge import app as app_module
from judge import assistants as assistants_module
from judge import publication
from judge.config import assistant_groups

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"
FORBIDDEN_KEYS = {"score", "rank", "ranking", "wilson", "weight", "consensus", "quote", "quotes",
                  "url", "document_id", "author_id", "handle"}


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    publication.withheld_sources.cache_clear()
    monkeypatch.delenv("PUBLICATION_VIEW", raising=False)
    monkeypatch.delenv("API_TOKEN", raising=False)
    yield
    publication.withheld_sources.cache_clear()


def _model(conn, mid, cid, name):
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, display_name, sources, provenance) "
        "VALUES (%s, %s, %s, %s, '{}', 'unpolled')",
        (mid, cid, cid.split("/")[0], name),
    )


def _report(conn, n, model_id, *, source, author, section, slug, name, polarity, ruling=None):
    conn.execute(
        "INSERT INTO author (id, source, external_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        (author, source, author),
    )
    doc = f"d{n}"
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, text_ref, content_hash, status, "
        "created_at, author_id) VALUES (%s, %s, %s, %s, %s, %s, 'kept', %s, %s)",
        (doc, source, doc, f"https://example.test/{doc}", f"r{doc}", f"h{doc}",
         f"2026-10-0{n}T00:00:00Z", author),
    )
    conn.execute(
        "INSERT INTO board_entry (id, section, slug, name, definition, model_version_id, "
        "document_id, quote, quote_verified, polarity, proposer_model, pipeline_version, "
        "ruling, reviewed_at) "
        "VALUES (%s, %s, %s, %s, 'Def.', %s, %s, %s, true, %s, 'm', 'v1', %s, %s)",
        (f"be{n}", section, slug, name, model_id, doc, f"words from {doc}", polarity,
         ruling, "2026-10-09T00:00:00Z" if ruling else None),
    )


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        # in the registry and the grouping: one with reports, one without
        _model(connection, "mv_muse", "meta/meta-muse", "Meta Muse")
        _model(connection, "mv_code", "anthropic/claude-code", "Claude Code")
        # an agent no group names (anthropic/claude-cowork is NOT seated: counted)
        _model(connection, "mv_stray", "acme/stray-agent", "Stray Agent")
        _report(connection, 1, "mv_muse", source="devto", author="a1", section="best_for",
                slug="daily-planning", name="Daily planning", polarity="positive")
        _report(connection, 2, "mv_muse", source="hackernews", author="a2", section="capability",
                slug="reliability", name="Reliability", polarity="negative")
        _report(connection, 3, "mv_muse", source="reddit", author="a3", section="capability",
                slug="reliability", name="Reliability", polarity="negative")
        # declined: adds nothing
        _report(connection, 4, "mv_muse", source="devto", author="a4", section="capability",
                slug="reliability", name="Reliability", polarity="negative", ruling="declined")
        # a registry-only row whose maker is unknown, with no reports
        _model(connection, "mv_hark", "unknown/hark-pro", "Hark")
        # one job, four sources: embed-only (x, reddit), withheld (bluesky), shown (hackernews)
        _model(connection, "mv_cli", "google/gemini-cli", "Gemini CLI")
        for n, source in ((5, "x"), (6, "bluesky"), (7, "hackernews"), (8, "reddit")):
            _report(connection, n, "mv_cli", source=source, author=f"b{n}", section="best_for",
                    slug="debugging", name="Debugging", polarity="positive")
        connection.execute(
            "INSERT INTO feed_embed (document_id, platform, outcome, url) VALUES "
            "('d5', 'x', 'embeddable', 'https://x.com/i/status/1234567890'), "
            "('d8', 'reddit', 'embeddable', 'https://www.reddit.com/comments/abc123/')"
        )
        connection.commit()
        yield connection


@pytest.fixture
def client(conn, monkeypatch):
    @contextlib.contextmanager
    def fake():
        yield conn

    monkeypatch.setattr(app_module, "_conn", fake)
    monkeypatch.setattr(assistants_module, "agent_canonical_ids",
                        lambda: ("meta/meta-muse", "acme/stray-agent"))
    return TestClient(app_module.app)


def _walk(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _group(body, key):
    return next(g for g in body["groups"] if g["key"] == key)


def test_the_groups_come_in_the_files_order(client):
    body = client.get("/assistants").json()
    assert [g["key"] for g in body["groups"]] == ["works-for-you", "workspaces", "coding-builders"]


def test_an_assistant_with_reports_has_counts_and_declined_rows_do_not_count(client):
    card = next(a for a in _group(client.get("/assistants").json(), "works-for-you")["assistants"]
                if a["canonical_id"] == "meta/meta-muse")
    assert card["state"] == "reports"
    # a1, a2, a3 - the declined fourth author adds neither a person nor a report
    assert (card["people"], card["reports"]) == (3, 3)
    assert card["newest"] == "2026-10-03"
    assert card["top_jobs"][0]["slug"] == "daily-planning"


def test_an_assistant_nobody_discussed_is_no_reports_not_problems(client):
    card = next(a for a in _group(client.get("/assistants").json(), "coding-builders")["assistants"]
                if a["canonical_id"] == "anthropic/claude-code")
    assert card["state"] == "no_reports"
    assert (card["people"], card["reports"], card["newest"], card["top_jobs"]) == (0, 0, None, [])
    detail = client.get("/assistants/anthropic/claude-code").json()
    assert detail["state"] == "no_reports"
    assert detail["problems"] == []
    assert detail["evidence"]["reports"] == 0


def test_a_member_missing_from_the_registry_is_counted_not_rendered(client):
    body = client.get("/assistants").json()
    ws = _group(body, "workspaces")
    assert ws["assistants"] == []
    assert ws["not_in_registry"] == ws["members"] == 2
    works = _group(body, "works-for-you")
    assert works["not_in_registry"] == works["members"] - 2  # meta-muse and hark-pro are seated
    assert [c["canonical_id"] for c in works["assistants"]] == [
        "meta/meta-muse", "unknown/hark-pro"]


def test_an_agent_in_no_group_is_unclassified_never_guessed(client):
    body = client.get("/assistants").json()
    assert [u["canonical_id"] for u in body["unclassified"]] == ["acme/stray-agent"]
    placed = {a["canonical_id"] for g in body["groups"] for a in g["assistants"]}
    assert "acme/stray-agent" not in placed
    assert client.get("/assistants/acme/stray-agent").status_code == 404


def test_the_comparison_table_is_counts_of_reports_per_member(client):
    body = client.get("/assistants").json()
    rows = {(r["kind"], r["slug"]): r for r in _group(body, "works-for-you")["compare"]}
    cell = rows[("capability", "reliability")]["cells"][0]
    assert cell["canonical_id"] == "meta/meta-muse"
    assert (cell["working"], cell["neutral"], cell["problems"], cell["reports"]) == (0, 0, 2, 2)
    assert cell["people"] == 2
    silent = rows[("job", "agentic-tasks")]["cells"][0]
    assert (silent["reports"], silent["working"], silent["problems"]) == (0, 0, 0)


def test_the_detail_page_carries_counts_problems_and_no_guides(client):
    d = client.get("/assistants/meta/meta-muse").json()
    assert d["group"]["key"] == "works-for-you"
    assert d["evidence"] == {"people": 3, "reports": 3, "platforms": 2, "newest": "2026-10-03"}
    assert [p["slug"] for p in d["problems"]] == ["reliability"]
    assert d["problems"][0]["people_with_problems"] == 2
    assert d["guides"] == [] and d["guides_note"]
    # the registry id resolves too
    assert client.get("/assistants/mv_muse").json()["assistant"]["canonical_id"] == "meta/meta-muse"


def test_an_id_that_is_not_an_assistant_is_a_404(client):
    assert client.get("/assistants/nobody/nothing").status_code == 404


def test_no_score_or_rank_in_any_payload_and_the_list_carries_no_quote(client):
    for path in ("/assistants", "/assistants/meta/meta-muse", "/assistants/google/gemini-cli"):
        assert not {"score", "rank", "ranking", "wilson", "weight", "consensus"} & set(
            _walk(client.get(path).json())), path
    listing = client.get("/assistants").json()
    text = json.dumps(listing)
    assert "words from" not in text and "example.test" not in text
    assert not FORBIDDEN_KEYS & set(_walk(listing))


def _job(detail, slug):
    return next(r for r in detail["best_for"] if r["slug"] == slug)


def test_a_reports_text_follows_the_publication_rules_by_source(client):
    """THE PUBLIC PAYLOAD HOLDS NO TEXT FOR AN EMBED-ONLY OR A WITHHELD SOURCE."""
    detail = client.get("/assistants/google/gemini-cli").json()
    text = json.dumps(detail)
    for doc in ("d5", "d6", "d8"):  # x, bluesky, reddit
        assert f"words from {doc}" not in text, doc
        assert f"example.test/{doc}" not in text, doc
    ev = _job(detail, "debugging")["evidence"]
    assert ev["total"] == 4 and ev["omitted"] == 1  # bluesky: counted, never shown
    by_kind = {i["source"]["kind"]: i for i in ev["items"]}
    # hackernews: the verified quote, its platform and a link
    hn = by_kind["link"]
    assert hn["text"] == "words from d7"
    assert hn["source"]["platform"] == "Hacker News"
    assert hn["source"]["url"] == "https://example.test/d7"
    # x and reddit: the ids the official embed needs, and no text
    embeds = [i for i in ev["items"] if i["source"]["kind"] == "embed"]
    assert {i["source"]["platform"] for i in embeds} == {"x", "reddit"}
    assert all(i["text"] is None for i in embeds)
    ids = {i["source"]["platform"]: i["source"] for i in embeds}
    assert ids["x"]["status_id"] == "1234567890" and ids["reddit"]["post_id"] == "abc123"
    assert len(ev["items"]) == 3
    assert detail["paraphrases_note"]


def test_a_problem_carries_its_negative_reports_with_the_same_rules(client):
    problem = client.get("/assistants/meta/meta-muse").json()["problems"][0]
    ev = problem["evidence"]
    assert ev["total"] == 2
    kinds = sorted(i["source"]["kind"] for i in ev["items"])
    assert kinds == ["link", "pending"]  # hackernews quote; reddit embed not resolved yet
    assert [i["text"] for i in ev["items"] if i["source"]["kind"] == "pending"] == [None]
    assert "words from d3" not in json.dumps(problem)


def test_an_unknown_maker_is_not_shown(client):
    body = client.get("/assistants").json()
    silent = next(a for a in _group(body, "works-for-you")["assistants"]
                  if a["canonical_id"] == "unknown/hark-pro")
    assert silent["provider"] is None and silent["state"] == "no_reports"
    assert client.get("/assistants/unknown/hark-pro").json()["assistant"]["provider"] is None
    assert "unknown" not in json.dumps(
        [a["provider"] for g in body["groups"] for a in g["assistants"]]).lower()


def test_assistants_without_reports_are_not_in_the_comparison_table(client):
    works = _group(client.get("/assistants").json(), "works-for-you")
    for row in works["compare"]:
        assert [c["canonical_id"] for c in row["cells"]] == ["meta/meta-muse"]


def test_both_endpoints_are_public(client, monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secret")
    assert client.get("/admin/settings").status_code == 401  # the control: a token IS required
    assert client.get("/assistants").status_code == 200
    assert client.get("/assistants/meta/meta-muse").status_code == 200


def test_the_grouping_file_loads_with_unique_members():
    cfg = assistant_groups()
    members = [m for g in cfg["groups"] for m in g["members"]]
    assert len(members) == len(set(members))
    assert len(_group({"groups": cfg["groups"]}, "works-for-you")["members"]) == 31
    assert not {"unknown/instinct", "nozomio-labs/folk", "unknown/del"} & set(members)  # held
    assert all("/" in m for m in members)
