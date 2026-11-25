"""The harvest is saved before it is labelled (#659 review, 2026-11-24).

A run spends its RapidAPI requests before it writes anything, and used to write the
posts and their labels in one transaction: a labelling failure rolled the posts back
too, so the requests were spent for nothing. Now the new posts are committed first and
a labelling failure leaves them as 'pending' for the next run or a --relabel. These
drive scripts/run_industry_ai.py's main() against the disposable test database, with
the harvest faked (no network) and labelling made to fail.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from collect.industry_ai.rules import Item


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


def _item(iid):
    return Item(id=f"reddit:{iid}", platform="reddit", external_id=iid,
                url=f"https://www.reddit.com/{iid}", title=f"title {iid}",
                body="Our accounting team uses ChatGPT to draft month-end close notes.",
                created_at=datetime.now(UTC) - timedelta(days=2), author_id="t2_a",
                domain_hints={"marketing"}, query_keys={"iai:marketing:reddit:q"})


@pytest.fixture
def wired(monkeypatch, conn, test_dsn, tmp_path):
    """main() with the test database, no network, no registry and no bot list."""
    import collect.industry_ai.harvest as harvest_mod
    import judge.writeguard as writeguard
    import scripts.run_industry_ai as script

    monkeypatch.setattr(script, "settings", lambda: SimpleNamespace(
        database_url=test_dsn, raw_store_path=str(tmp_path)))
    monkeypatch.setattr(writeguard, "check", lambda dsn, command: None)
    monkeypatch.setattr(script, "_registry_names", lambda dsn: ())
    monkeypatch.setattr(script, "_bot_check", lambda: (lambda item: False))
    items = {i.id: i for i in (_item("a1"), _item("a2"))}
    monkeypatch.setattr(harvest_mod, "harvest", lambda cfg, **kw: SimpleNamespace(
        notes=[], requests={"reddit": 2}, quota={}, queries=[], items=items))
    return script


def _rows(conn):
    return conn.execute(
        "SELECT id, drop_stage FROM iai_item ORDER BY id").fetchall()


def test_a_labelling_failure_keeps_the_harvest_and_says_so(wired, conn, monkeypatch):
    from collect.industry_ai import store

    def boom(*a, **k):
        raise RuntimeError("labelling broke")

    monkeypatch.setattr(store, "write_labels", boom)
    with pytest.raises(RuntimeError, match="labelling broke"):
        wired.main(["--domains", "marketing", "--platforms", "reddit"])
    conn.rollback()
    assert _rows(conn) == [("reddit:a1", "pending"), ("reddit:a2", "pending")]
    status, detail = conn.execute(
        "SELECT status, detail FROM iai_run ORDER BY started_at DESC LIMIT 1").fetchone()
    assert status == "error"
    assert detail.startswith("2 new item(s) SAVED before the error")
    assert "labelling broke" in detail

    # THE PAGE: the two unjudged posts are waiting, not "filtered out" (#663 review).
    from judge.industry_ai.view import industry_ai_view

    page = industry_ai_view(conn)
    assert page["pending"] == 2
    assert page["dropped"] == []
    assert page["kept"] == 0
    assert page["collected"] == page["kept"] + page["pending"] + sum(
        r["items"] for r in page["dropped"])


def test_a_clean_run_labels_and_records_its_times(wired, conn):
    assert wired.main(["--domains", "marketing", "--platforms", "reddit"]) == 0
    conn.rollback()
    assert all(stage != "pending" for _, stage in _rows(conn))
    status, detail = conn.execute(
        "SELECT status, detail FROM iai_run ORDER BY started_at DESC LIMIT 1").fetchone()
    assert status == "ok"
    assert "2 new item(s)" in detail and "store " in detail and "label " in detail
