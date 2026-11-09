"""Stale "no model" verdicts, re-triaged after a model is seated (#602, option b).

Disposable Postgres only (`TEST_DATABASE_URL`); the raw store is a dict.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from collect.triage.retriage import apply, plan
from tests.conftest import assert_disposable, assert_safe_target

LONG = (" - we rendered forty product shots over a week, and the camera moves held "
        "steady on every one of them, with the error log below")


@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema, connect

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


class _Store:
    def __init__(self, payloads):
        self._p = payloads

    def get_text(self, ref):
        return self._p[ref]

    def get(self, ref):
        return self._p[ref].encode()


def _doc(conn, doc_id, ref, *, root=None, parent=None, verdict="dropped"):
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, text_ref, content_hash, "
        "thread_root_id, parent_id, created_at, retrieval_provenance, triage_verdict, "
        "filter_reasons) VALUES (%s, 'reddit', %s, %s, %s, %s, %s, %s, %s, "
        "'not_recorded', %s, %s)",
        (doc_id, doc_id.split(":")[1], f"https://www.reddit.com/r/aivideo/comments/{doc_id}/",
         ref, ref, root, parent, datetime.now(UTC), verdict,
         ["no-resolvable-entity"] if verdict == "dropped" else None),
    )


def _setup(conn):
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, display_name, sources, "
        "provenance) VALUES ('mv_h3', 'minimax/hailuo-3-max', 'minimax', "
        "'MiniMax: Hailuo 3 Max', '{}'::jsonb, 'unpolled')")
    payloads = {
        "p/names": json.dumps({"title": "Hailuo 3 Max for product videos",
                               "selftext": "Trying Hailuo 3 Max" + LONG}),
        "p/nothing": json.dumps({"title": "Weekend render", "selftext": "Nothing named" + LONG}),
        "p/adult": json.dumps({"title": "Hailuo 3 Max test", "selftext": "x" + LONG,
                               "over_18": True}),
        "c/under-adult": json.dumps({"body": "Hailuo 3 Max did this well" + LONG}),
    }
    _doc(conn, "reddit:t3_names", "p/names")
    _doc(conn, "reddit:t3_nothing", "p/nothing")
    _doc(conn, "reddit:t3_adult", "p/adult")
    _doc(conn, "reddit:t1_c", "c/under-adult", root="reddit:t3_adult", parent="reddit:t3_adult")
    conn.commit()
    return _Store(payloads)


def test_plan_names_only_what_the_seated_model_appears_in(conn):
    store = _setup(conn)
    p = plan(conn, store, models=["minimax/hailuo-3-max"])
    assert p.candidates == 4
    assert p.ids == ["reddit:t3_names"]
    assert p.adult_left_dropped == 2, "the adult post and the comment under it stay dropped"
    assert p.by_subreddit == {"aivideo": 1}


def test_apply_rejudges_exactly_the_planned_ids(conn):
    store = _setup(conn)
    out = apply(conn, store, plan(conn, store, models=["minimax/hailuo-3-max"]))
    conn.commit()
    assert out["cleared"] == 1 and out["triaged"] == 1 and out["kept"] == 1
    verdicts = dict(conn.execute("SELECT id, triage_verdict FROM document").fetchall())
    assert verdicts == {"reddit:t3_names": "kept", "reddit:t3_nothing": "dropped",
                        "reddit:t3_adult": "dropped", "reddit:t1_c": "dropped"}


def test_an_unseated_model_refuses_rather_than_matching_nothing(conn):
    store = _setup(conn)
    with pytest.raises(ValueError, match="not in the registry"):
        plan(conn, store, models=["acme/never-seated"])
