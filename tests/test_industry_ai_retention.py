"""Text retention for the Industry AI agent (anooj, 2026-11-24).

A ROW IS NEVER DELETED; ITS TEXT IS. After `retention.clear_text_after_days`, a
dropped row's title and body - and a kept row's in a `kept_domains` domain
(Personal) - are emptied and `text_cleared_at` stamped. These pin:
  * the `retention:` block is read strictly;
  * exactly which rows are cleared, and that rows, labels and counts stay;
  * a cleared row is never re-labelled on its empty text (it would turn from
    "spam" into "no AI term" and shift the drop counts);
  * a re-harvested post does not bring its text back.
The contract tests are pure; the rest use the disposable test database.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import pytest
import yaml

from collect.industry_ai import config as iai_config
from collect.industry_ai.config import CONTRACT, IndustryAIConfigError
from collect.industry_ai.rules import Item

NOW = datetime(2026, 12, 30, tzinfo=UTC)
OLD, YOUNG = NOW - timedelta(days=31), NOW - timedelta(days=29)


@pytest.fixture(scope="module")
def raw():
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cfg(raw):
    return iai_config.parse(copy.deepcopy(raw))


# ── the contract ─────────────────────────────────────────────────────────────


def test_the_contract_retention_loads(cfg):
    assert cfg.retention == {"clear_text_after_days": 30, "dropped": True, "unread": False,
                             "kept_domains": ("personal",)}


@pytest.mark.parametrize("mutate, says", [
    (lambda r: r.pop("retention"), "retention"),
    (lambda r: r["retention"].pop("dropped"), "dropped"),
    (lambda r: r["retention"].update(keep_forever=True), "unknown key"),
    (lambda r: r["retention"].update(clear_text_after_days=0), "whole number"),
    (lambda r: r["retention"].update(dropped="yes"), "true or false"),
    (lambda r: r["retention"].pop("unread"), "unread"),
    (lambda r: r["retention"].update(unread="no"), "true or false"),
    # A misspelt domain would silently keep that domain's text.
    (lambda r: r["retention"].update(kept_domains=["persnal"]), "unknown domain"),
])
def test_the_retention_block_is_read_strictly(raw, mutate, says):
    bad = copy.deepcopy(raw)
    mutate(bad)
    with pytest.raises(IndustryAIConfigError, match=says):
        iai_config.parse(bad)


# ── raw pages: not in the shared store (#656 review) ─────────────────────────


def test_the_raw_store_is_local_even_when_the_environment_says_shared(monkeypatch, tmp_path):
    """A search page carries every post's full text; the shared `raw_blob` keeps it
    for good. Clearing `iai_item` would mean nothing with the words left there."""
    import scripts.run_industry_ai as script

    monkeypatch.setenv("RAW_STORE_REMOTE", "postgres")
    monkeypatch.setattr(script, "settings",
                        lambda: type("S", (), {"raw_store_path": str(tmp_path)})())
    assert script.raw_store()._remote is None


def test_the_workflow_does_not_ask_for_the_shared_raw_store():
    from pathlib import Path

    wf = (Path(__file__).resolve().parents[1] / ".github" / "workflows"
          / "industry-ai-harvest.yml").read_text(encoding="utf-8")
    assert "RAW_STORE_REMOTE:" not in wf


# ── through the store ────────────────────────────────────────────────────────


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


def _item(iid, body="A post about using an LLM at work, with enough words to read."):
    return Item(id=f"reddit:{iid}", platform="reddit", external_id=iid,
                url=f"https://www.reddit.com/{iid}", title=f"title {iid}", body=body,
                created_at=OLD, author_id="t2_a")


#: id -> (verdict, drop_reason, domains, first stored)
ROWS = {
    "spam_old": ("dropped", "spam", [], OLD),
    "spam_young": ("dropped", "spam", [], YOUNG),
    "personal_old": ("kept", None, ["personal"], OLD),
    "personal_young": ("kept", None, ["personal"], YOUNG),
    "marketing_old": ("kept", None, ["marketing"], OLD),
    "both_old": ("kept", None, ["marketing", "personal"], OLD),
}


@pytest.fixture
def stored(conn, cfg):
    from collect.industry_ai import store

    store.start_run(conn, "iai-ret", mode="harvest", domains=[], platforms=["reddit"],
                    pipeline_version=cfg.pipeline_version)
    store.upsert_items(conn, [_item(i) for i in ROWS], run_id="iai-ret")
    for iid, (verdict, reason, domains, seen) in ROWS.items():
        conn.execute(
            "UPDATE iai_item SET verdict = %s, drop_stage = %s, drop_reason = %s, "
            "domains = %s, first_seen_at = %s WHERE id = %s",
            (verdict, "filter" if reason else None, reason, domains, seen, f"reddit:{iid}"))
    conn.commit()
    return conn


def _row(conn, iid):
    return conn.execute(
        "SELECT title, body, text_cleared_at, verdict, drop_reason, domains "
        "FROM iai_item WHERE id = %s", (f"reddit:{iid}",)).fetchone()


def test_exactly_the_due_rows_lose_their_text_and_keep_their_row(stored, cfg):
    from collect.industry_ai import store

    assert store.clear_text(stored, cfg.retention, now=NOW) == 3
    stored.commit()
    for iid in ("spam_old", "personal_old", "both_old"):
        title, body, cleared, verdict, reason, domains = _row(stored, iid)
        assert (title, body, cleared) == ("", "", NOW), iid
        assert (verdict, reason, domains) == ROWS[iid][:3], f"{iid}: labels kept"
    for iid in ("spam_young", "personal_young", "marketing_old"):
        title, body, cleared, *_ = _row(stored, iid)
        assert cleared is None and body and title == f"title {iid}", iid
    assert stored.execute("SELECT count(*) FROM iai_item").fetchone()[0] == len(ROWS)
    assert store.clear_text(stored, cfg.retention, now=NOW) == 0, "cleared once"


def test_a_not_readable_post_keeps_its_text_until_the_contract_says(stored, cfg):
    """#676 review (anooj, 2026-11-26): "not readable" is stored as dropped, stage
    `unread`; `retention.unread: false` keeps its text, so the threshold review and
    the media-text rules can re-judge it. Admin's "due" count reads the same rows."""
    from collect.industry_ai import store
    from judge.industry_ai.view import industry_ai_admin

    store.upsert_items(stored, [_item("unread_old")], run_id="iai-ret")
    stored.execute("UPDATE iai_item SET verdict = 'dropped', drop_stage = 'unread', "
                   "drop_reason = 'media_unread', first_seen_at = %s "
                   "WHERE id = 'reddit:unread_old'", (OLD,))
    # Admin counts against the database's own clock, so the ages move to it here.
    stored.execute("UPDATE iai_item SET first_seen_at = now() - (%s - first_seen_at)", (NOW,))
    stored.commit()
    assert cfg.retention["unread"] is False
    due_on_admin = industry_ai_admin(stored)["items"]["text_due"]
    assert store.clear_text(stored, cfg.retention) == due_on_admin == 3
    assert _row(stored, "unread_old")[2] is None, "kept its text"

    assert store.clear_text(stored, {**cfg.retention, "unread": True}) == 1
    title, body, cleared, *_ = _row(stored, "unread_old")
    assert (title, body) == ("", "") and cleared is not None


def test_a_cleared_row_is_not_relabelled_on_its_empty_text(stored, cfg):
    """Every run re-labels the collection. A cleared spam row must stay `spam`, not
    turn into `no_ai_term` because its text is gone."""
    from collect.industry_ai import store
    from collect.industry_ai.pipeline import evaluate

    store.clear_text(stored, cfg.retention, now=NOW)
    loaded = {it.id for it in store.load_items(stored)}
    assert "reddit:spam_old" not in loaded and "reddit:spam_young" in loaded
    results, _ = evaluate(store.load_items(stored), cfg, since=NOW - timedelta(days=365), now=NOW)
    store.write_labels(stored, results, pipeline_version=cfg.pipeline_version)
    stored.commit()
    assert _row(stored, "spam_old")[3:5] == ("dropped", "spam")


def test_a_reharvested_post_does_not_bring_its_text_back(stored, cfg):
    from collect.industry_ai import store

    store.clear_text(stored, cfg.retention, now=NOW)
    store.upsert_items(stored, [_item("spam_old")], run_id="iai-ret")
    stored.commit()
    title, body, cleared, *_ = _row(stored, "spam_old")
    assert (title, body) == ("", "") and cleared == NOW
