"""Registry rows for catalogue models (#616): evidence filed, no daily fetch.

Disposable Postgres only (`TEST_DATABASE_URL`).
"""
from __future__ import annotations

import json

import pytest

from collect.ops import catalogue_seat
from tests.conftest import assert_disposable, assert_safe_target


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


def _catalogue(conn, cid, name, outputs):
    conn.execute(
        "INSERT INTO model_catalog (canonical_id, provider, name, input_modalities, "
        "output_modalities, pricing, last_seen_at) VALUES (%s, %s, %s, '{text}', %s, %s, now())",
        (cid, cid.lstrip("~").split("/")[0], name, outputs, json.dumps({})))


def _registry(conn, cid, display, provenance):
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, display_name, sources, provenance) "
        "VALUES (%s, %s, %s, %s, '{}'::jsonb, %s)",
        ("mv_" + cid.replace("/", "_"), cid, cid.split("/")[0], display, provenance))


@pytest.fixture
def catalogue(conn):
    _catalogue(conn, "elevenlabs/eleven-v4", "ElevenLabs: Eleven v4", ["speech"])
    _catalogue(conn, "openai/gpt-image-2.6-flare", "OpenAI: GPT Image 2.6 Flare", ["image", "text"])
    _catalogue(conn, "acme/acme-2:free", "Acme: Acme 2 (free)", ["text"])
    _catalogue(conn, "acme/acme-2:batch", "Acme: Acme 2 (batch)", ["text"])
    _catalogue(conn, "openrouter/auto", "Auto Router", ["text"])
    _catalogue(conn, "~acme/acme-latest", "Acme Latest", ["text"])
    _catalogue(conn, "acme/embed-3", "Acme: Embed 3", ["embeddings"])
    _catalogue(conn, "perplexity/sonar", "Perplexity: Sonar", ["text"])  # 1 word, no digit
    _catalogue(conn, "mancer/weaver", "Mancer: Weaver Alpha", ["text"])  # family
    _catalogue(conn, "anthropic/claude-opus-5", "Anthropic: Claude Opus 5", ["text"])  # has a row
    _registry(conn, "anthropic/claude-opus-5", "Anthropic: Claude Opus 5", "polled")
    conn.commit()
    return conn


def test_the_plan_seats_what_it_may_and_names_why_the_rest_is_set_aside(catalogue):
    p = catalogue_seat.plan(catalogue)
    assert {s.canonical_id for s in p.seats} == {"elevenlabs/eleven-v4",
                                                 "openai/gpt-image-2.6-flare"}
    why = p.set_aside
    assert why["acme/acme-2:free"].startswith("listing variant")
    assert why["acme/acme-2:batch"].startswith("listing variant")
    assert why["openrouter/auto"].startswith("router")
    assert why["~acme/acme-latest"].startswith("latest pointer")
    assert why["acme/embed-3"].startswith("out of scope")
    assert why["perplexity/sonar"].startswith("no usable name form")
    assert why["mancer/weaver"].startswith("family specificity")
    assert "anthropic/claude-opus-5" not in why  # it has a row: not even a candidate
    assert p.candidates == 9


def test_a_name_another_model_owns_is_set_aside_not_seated(catalogue):
    _catalogue(catalogue, "acme/opus-5", "Acme: Claude Opus 5", ["text"])
    catalogue.commit()
    p = catalogue_seat.plan(catalogue)
    assert p.set_aside["acme/opus-5"].startswith("name already owned: anthropic/claude-opus-5")


def test_apply_writes_catalogued_rows_with_no_figures_and_no_events(catalogue):
    out = catalogue_seat.apply(catalogue, catalogue_seat.plan(catalogue))
    catalogue.commit()
    assert out["inserted"] == 2 and out["skipped_existing"] == 0
    rows = catalogue.execute(
        "SELECT canonical_id, provenance, release_date, in_window, price_in, price_out "
        "FROM model_version WHERE provenance = 'catalogued' ORDER BY 1").fetchall()
    assert [r[0] for r in rows] == ["elevenlabs/eleven-v4", "openai/gpt-image-2.6-flare"]
    assert all(r[2] is None and r[3] is True and r[4] is None and r[5] is None for r in rows)
    # 'eleven v4' and 'eleven-v4' are one key; alias_rows keeps one row per key.
    keys = {r[0] for r in catalogue.execute(
        "SELECT a.normalized FROM model_alias a "
        "JOIN model_version mv ON mv.id = a.model_version_id "
        "WHERE mv.canonical_id = 'elevenlabs/eleven-v4'").fetchall()}
    assert "elevenv4" in keys
    # A catalogue row is not a release: no `new-model` event floods the updates feed.
    assert catalogue.execute("SELECT count(*) FROM model_event").fetchone()[0] == 0


@pytest.mark.parametrize("provenance", ["polled", "unpolled"])
def test_a_row_that_appears_before_the_write_is_never_touched(catalogue, provenance):
    """The poll racing the writer in one workflow: polled > seed/unpolled > catalogued."""
    plan = catalogue_seat.plan(catalogue)
    _registry(catalogue, "elevenlabs/eleven-v4", "ElevenLabs v4 (hand)", provenance)
    catalogue.commit()
    out = catalogue_seat.apply(catalogue, plan)
    catalogue.commit()
    assert out["skipped_existing"] == 1 and "elevenlabs/eleven-v4" in out["skipped_ids"]
    row = catalogue.execute("SELECT provenance, display_name FROM model_version "
                            "WHERE canonical_id = 'elevenlabs/eleven-v4'").fetchone()
    assert row == (provenance, "ElevenLabs v4 (hand)")


def test_auto_track_never_admits_a_catalogued_row(catalogue):
    """`auto_track`'s query requires `polled`; a catalogued row never starts a daily fetch,
    even with a release date and a tracked provider."""
    from datetime import date, timedelta

    from judge.tracked import ELIGIBLE

    catalogue_seat.apply(catalogue, catalogue_seat.plan(catalogue))
    catalogue.execute("UPDATE model_version SET release_date = %s, in_window = true "
                      "WHERE provenance = 'catalogued'", (date.today(),))
    catalogue.commit()
    rows = catalogue.execute(ELIGIBLE, (["elevenlabs", "openai"], date.today() - timedelta(days=30),
                                        [], [])).fetchall()
    assert rows == []


def test_the_check_takes_catalogued_and_still_refuses_an_unknown_value(conn):
    import psycopg

    _registry(conn, "acme/one-1", "Acme One 1", "catalogued")
    conn.commit()
    with pytest.raises(psycopg.errors.CheckViolation):
        _registry(conn, "acme/two-2", "Acme Two 2", "guessed")
    conn.rollback()


def test_kind_is_read_from_the_published_outputs():
    assert catalogue_seat.kind_of(["speech"]) == "speech"
    assert catalogue_seat.kind_of(["image", "text"]) == "image"
    assert catalogue_seat.kind_of(["text"]) == "text"
    assert catalogue_seat.kind_of([]) == "unknown"


def test_the_script_says_nothing_written_on_a_second_apply(catalogue, test_dsn, monkeypatch,
                                                             tmp_path):
    """The registry-poll workflow posts the report only when this line is absent."""
    import importlib.util
    import pathlib

    path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "seat_catalogue_models.py"
    spec = importlib.util.spec_from_file_location("seat_catalogue_models", path)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    from collect.config import settings

    monkeypatch.setenv("DATABASE_URL", test_dsn)
    settings.cache_clear()  # cached by any earlier test; this one must read test_dsn
    first, second = tmp_path / "1.md", tmp_path / "2.md"
    try:
        assert script.main(["--apply", "--out", str(first)]) == 0
        assert script.main(["--apply", "--out", str(second)]) == 0
    finally:
        settings.cache_clear()
    assert "written: 2 row(s)" in first.read_text(encoding="utf-8")
    assert script.NOTHING_WRITTEN in second.read_text(encoding="utf-8")
    assert "set aside for a person" not in second.read_text(encoding="utf-8")
