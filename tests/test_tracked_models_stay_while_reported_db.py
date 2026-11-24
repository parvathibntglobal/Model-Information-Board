"""An admitted model stays on the page while people still post about it (2026-11-24).

`contract/tracked_models.yaml` `auto_track.stays_while_reported`. Kimi K3.1 Pro
left the page - and the scheduler's due list - on 2026-11-23, its 30th day,
holding 870 board entries from documents posted in the previous 30 days. These
run the real `ELIGIBLE` query, because the clause is SQL and a fake connection
would only check that parameters were passed.

Disposable Postgres only (`TEST_DATABASE_URL`).
"""
from __future__ import annotations

from datetime import date

import pytest

import judge.config as config
from judge import tracked
from judge.config import TrackedModel
from tests.conftest import assert_disposable, assert_safe_target

TODAY = date(2026, 11, 24)
STAYS = config.StaysWhileReported(released_on_or_after=date(2026, 9, 6), posted_within_days=30,
                                  entries=3, distinct_authors=2)
RULE = config.AutoTrackRule(enabled=True, released_within_days=30, include_pro_tier=True,
                            exclude_name_terms=(), stays=STAYS)
RECENT, OLD = "2026-11-15T12:00:00Z", "2026-10-01T12:00:00Z"


@pytest.fixture
def conn(test_dsn, monkeypatch):
    from collect.db import apply_schema, connect

    monkeypatch.setattr(tracked, "tracked_models",
                        lambda: (TrackedModel("Acme 1", "acme/acme-1", "text"),))
    monkeypatch.setattr(tracked, "auto_track_rule", lambda: RULE)
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


def _model(conn, cid, released):
    conn.execute(
        "INSERT INTO model_catalog (canonical_id, provider, name, input_modalities, "
        "output_modalities, pricing, last_seen_at) VALUES (%s, 'acme', %s, '{text}', '{text}', "
        "'{}'::jsonb, now())", (cid, cid))
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, display_name, sources, provenance, "
        "release_date, in_window) VALUES (%s, %s, 'acme', %s, '{}'::jsonb, 'polled', %s, true)",
        ("mv_" + cid, cid, cid, released))


def _reports(conn, cid, posted, authors):
    """One document and one board entry per item of `authors` (None = no author)."""
    for author in authors:
        n = conn.execute("SELECT count(*) FROM document").fetchone()[0]
        if author is not None:
            conn.execute("INSERT INTO author (id, source, external_id) VALUES (%s, 'reddit', %s) "
                         "ON CONFLICT DO NOTHING", (author, author))
        doc = f"d{n}"
        conn.execute(
            "INSERT INTO document (id, source, external_id, url, text_ref, content_hash, status, "
            "created_at, author_id) VALUES (%s, 'reddit', %s, %s, %s, %s, 'kept', %s, %s)",
            (doc, doc, f"https://example.test/{doc}", f"r{doc}", f"h{doc}", posted, author))
        conn.execute(
            "INSERT INTO board_entry (id, section, slug, name, definition, model_version_id, "
            "document_id, quote, quote_verified, polarity, proposer_model, pipeline_version) "
            "VALUES (%s, 'capability', 'coding', 'Coding', 'Def.', %s, %s, %s, true, "
            "'positive', 'm', 'v1')", (f"be{n}", "mv_" + cid, doc, f"words from {doc}"))


def test_an_admitted_model_stays_only_while_still_reported(conn):
    _model(conn, "acme/arrival-1", date(2026, 11, 10))      # inside 30 days: an arrival
    _model(conn, "acme/reported-1", date(2026, 10, 23))     # Kimi K3.1 Pro's shape
    _reports(conn, "acme/reported-1", RECENT, ["a", "b", "a"])
    _model(conn, "acme/one-voice-1", date(2026, 10, 20))    # entries, but one author
    _reports(conn, "acme/one-voice-1", RECENT, ["a", "a", "a", "a"])
    _model(conn, "acme/old-posts-1", date(2026, 10, 20))    # reported, but not lately
    _reports(conn, "acme/old-posts-1", OLD, ["a", "b", "c"])
    _model(conn, "acme/pre-rule-1", date(2026, 8, 1))       # the rule never admitted it
    _reports(conn, "acme/pre-rule-1", RECENT, ["a", "b", "c"])
    _model(conn, "acme/anon-1", date(2026, 10, 20))         # a missing author adds none
    _reports(conn, "acme/anon-1", RECENT, ["a", None, None])
    conn.commit()

    got = [m.registry for m in tracked.auto_tracked(conn, today=TODAY)]
    assert got == ["acme/arrival-1", "acme/reported-1"]


def test_the_bar_is_inclusive_and_both_halves_are_needed(conn):
    _model(conn, "acme/at-bar-1", date(2026, 10, 1))
    _reports(conn, "acme/at-bar-1", RECENT, ["a", "b", "b"])  # 3 entries, 2 authors: stays
    _model(conn, "acme/two-entries-1", date(2026, 10, 1))
    _reports(conn, "acme/two-entries-1", RECENT, ["a", "b"])  # 2 authors, 2 entries: goes
    conn.commit()
    assert [m.registry for m in tracked.auto_tracked(conn, today=TODAY)] == ["acme/at-bar-1"]


def test_the_contract_clause_runs_against_the_schema(conn, monkeypatch):
    """The live contract's numbers, not the test's, through the real query."""
    config.auto_track_rule.cache_clear()
    try:
        rule = config.auto_track_rule()
    finally:
        config.auto_track_rule.cache_clear()
    monkeypatch.setattr(tracked, "auto_track_rule", lambda: rule)
    _model(conn, "acme/reported-1", date(2026, 10, 23))
    _reports(conn, "acme/reported-1", RECENT, ["a", "b", "c", "d", "e"])
    conn.commit()
    assert [m.registry for m in tracked.auto_tracked(conn, today=TODAY)] == ["acme/reported-1"]
