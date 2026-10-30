"""The public AI benchmarks page, /ai-benchmarks (judge/benchmarks.py charts, 2026-10-30).

It is built from `table()`, so these tests hand it a table and check what leaves
the gate: the shown figure with its source, link and date; never a value
waiting for review, the source's own spelling of a model, or another source's
value. Bars only for a percent score, by the contract.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from judge import benchmarks
from judge.app import app


def _cell(display, sort, **kw):
    cell = {
        "display": display, "rounded_from": None, "tier": 1,
        "tier_label": "the benchmark's own leaderboard", "sort": sort, "tied": False,
        "source": "swebench", "source_label": "SWE-bench leaderboard",
        "url": "https://www.swebench.com/", "variant": None, "benchmark_version": None,
        "raw_name": "the board's own spelling", "source_date": "2026-10-28",
        "collected_at": "2026-10-28T01:30:00+00:00", "rank_out_of": None, "rank_board": None,
        "setting_not_stated": False, "needs_review": False, "badges": ["new"],
        "others": [{"source_label": "Vals AI", "tier": 2, "display": "70", "variant": None}],
        "tied_with": ["Another model"],
    }
    cell.update(kw)
    return cell


SECTIONS = [
    {"key": "knowledge", "label": "Knowledge & Reasoning", "columns": [
        {"key": "gpqa_diamond_score", "benchmark": "gpqa_diamond", "label": "GPQA Diamond",
         "metric": "score", "better": "higher", "setup_note": None},
    ]},
    {"key": "coding", "label": "Coding", "columns": [
        {"key": "swe_bench_verified_score", "benchmark": "swe_bench_verified",
         "label": "SWE-bench Verified", "metric": "score", "better": "higher",
         "setup_note": None},
        {"key": "swe_bench_verified_rank", "benchmark": "swe_bench_verified",
         "label": "SWE-bench Verified rank", "metric": "rank", "better": "lower",
         "setup_note": None},
    ]},
]


def _table(rows):
    return {
        "sections": SECTIONS, "rows": rows,
        "last_run": {"id": 9, "status": "ok", "started_at": "2026-10-28T01:30:00+00:00",
                     "finished_at": "2026-10-28T01:40:00+00:00"},
        "sources": [], "counts": {"benchmarks": 21},
    }


def _row(row_id, label, cells, children=(), group="tracked"):
    return {"row_id": row_id, "label": label, "group": group, "cells": cells,
            "dropped": {}, "children": list(children)}


class _Conn:
    """Answers the two queries charts() makes itself: the table's fingerprint
    (fetchone) and the recent rank moves (fetchall)."""

    def __init__(self, key=("1", "t0", "h0"), moves=()):
        self.key = key
        self.moves = list(moves)

    def execute(self, sql, *args):
        return self

    def fetchone(self):
        return self.key

    def fetchall(self):
        return self.moves


@pytest.fixture(autouse=True)
def _fresh_cache(monkeypatch):
    monkeypatch.setattr(benchmarks, "_charts_kept", None)
    benchmarks.charts_recheck_seconds.cache_clear()
    yield
    benchmarks.charts_recheck_seconds.cache_clear()


def _charts(monkeypatch, rows):
    """Every series of every model, flattened: the tests below read
    `out["models"][i]["values"]` for the i-th series."""
    monkeypatch.setattr(benchmarks, "table", lambda conn: _table(rows))
    listed = benchmarks.charts(_Conn())
    out = dict(listed)
    out["models"] = [
        {**s, "benchmarks_scored": model["benchmarks_scored"]}
        for m in listed["models"]
        for model in [benchmarks.charts(_Conn(), m["id"])["model"]]
        for s in model["series"]
    ]
    return out


def test_the_list_carries_names_and_counts_only(monkeypatch):
    monkeypatch.setattr(benchmarks, "table", lambda conn: _table([_row("m/a", "Model A", {
        "gpqa_diamond_score": _cell("81", 81.0)})]))
    listed = benchmarks.charts(_Conn())
    assert listed["model"] is None
    assert listed["models"] == [{"id": "m/a", "label": "Model A", "tracked": True,
                                 "benchmarks_scored": 1, "series_count": 1}]
    assert benchmarks.charts(_Conn(), "m/a")["model"]["series"][0]["values"][0]["display"] == "81"
    assert benchmarks.charts(_Conn(), "no/such")["model"] is None


def test_a_score_is_a_bar_and_a_rank_is_a_card(monkeypatch):
    out = _charts(monkeypatch, [_row("m/a", "Model A", {
        "swe_bench_verified_score": _cell("72.4", 72.4),
        "swe_bench_verified_rank": _cell("3", 3.0, rank_out_of=80),
    })])
    score, rank = out["models"][0]["values"]
    assert score["chart"] and score["percent"] == 72.4 and score["display"] == "72.4"
    assert not rank["chart"] and rank["percent"] is None
    assert rank["display"] == "3" and rank["rank_out_of"] == 80


def test_every_value_carries_its_source_link_and_date(monkeypatch):
    out = _charts(monkeypatch, [_row("m/a", "Model A", {
        "gpqa_diamond_score": _cell("81", 81.0)})])
    v = out["models"][0]["values"][0]
    assert v["source_label"] == "SWE-bench leaderboard"
    assert v["url"].startswith("https://")
    assert v["source_date"] == "2026-10-28"


def test_nothing_else_from_the_cell_leaves_the_gate(monkeypatch):
    out = _charts(monkeypatch, [_row("m/a", "Model A", {
        "gpqa_diamond_score": _cell("81", 81.0)})])
    v = out["models"][0]["values"][0]
    for private in ("raw_name", "others", "badges", "tied_with", "needs_review", "sort"):
        assert private not in v
    assert set(out["last_run"]) == {"finished_at", "status"}


def test_a_value_waiting_for_review_is_held_back_and_counted(monkeypatch):
    out = _charts(monkeypatch, [_row("m/a", "Model A", {
        "gpqa_diamond_score": _cell("81", 81.0, needs_review=True),
        "swe_bench_verified_score": _cell("60", 60.0)})])
    assert [v["key"] for v in out["models"][0]["values"]] == ["swe_bench_verified_score"]
    assert out["withheld_for_review"] == 1


def test_a_model_with_nothing_public_is_not_listed(monkeypatch):
    out = _charts(monkeypatch, [_row("m/a", "Model A", {
        "gpqa_diamond_score": _cell("81", 81.0, needs_review=True)})])
    assert out["models"] == []


def test_a_models_setting_rows_are_its_series(monkeypatch):
    child = {"row_id": "m/a:max", "label": "Model A (max)", "setting": "max", "dated": None,
             "cells": {"gpqa_diamond_score": _cell("85", 85.0)}, "dropped": {}}
    dated = {"row_id": "m/a@20251101", "label": "Model A (20251101)", "setting": None,
             "dated": "20251101", "cells": {"gpqa_diamond_score": _cell("80", 80.0)},
             "dropped": {}}
    monkeypatch.setattr(benchmarks, "table", lambda conn: _table([_row("m/a", "Model A", {
        "gpqa_diamond_score": _cell("81", 81.0)}, children=[child, dated])]))
    listed = benchmarks.charts(_Conn())
    assert [(m["label"], m["series_count"]) for m in listed["models"]] == [("Model A", 3)]
    model = benchmarks.charts(_Conn(), "m/a")["model"]
    assert [(s["label"], s["short"]) for s in model["series"]] == [
        ("Model A", "Base"), ("Model A (max)", "max"), ("Model A (20251101)", "20251101")]
    assert [s["values"][0]["display"] for s in model["series"]] == ["81", "85", "80"]


def test_a_model_listed_only_through_its_settings_opens_on_them(monkeypatch):
    child = {"row_id": "m/a:high", "label": "Model A (high)", "setting": "high", "dated": None,
             "cells": {"gpqa_diamond_score": _cell("85", 85.0)}, "dropped": {}}
    monkeypatch.setattr(benchmarks, "table", lambda conn: _table([_row("m/a", "Model A", {},
                                                                         children=[child])]))
    model = benchmarks.charts(_Conn(), "m/a")["model"]
    assert [s["short"] for s in model["series"]] == ["high"]


def test_values_follow_the_tables_section_order(monkeypatch):
    out = _charts(monkeypatch, [_row("m/a", "Model A", {
        "swe_bench_verified_score": _cell("60", 60.0),
        "gpqa_diamond_score": _cell("81", 81.0)})])
    assert [v["section"] for v in out["models"][0]["values"]] == ["knowledge", "coding"]


def test_the_count_says_what_it_is_counted_over(monkeypatch):
    out = _charts(monkeypatch, [_row("m/a", "Model A", {
        "swe_bench_verified_score": _cell("60", 60.0),
        "swe_bench_verified_rank": _cell("3", 3.0)})])
    assert out["models"][0]["benchmarks_scored"] == 1
    assert out["benchmarks_listed"] == 21


def test_a_score_outside_the_percent_unit_is_a_card(monkeypatch):
    real = benchmarks._yaml

    def units(name):
        raw = real(name)
        if name == "benchmarks.yaml":
            for b in raw["benchmarks"]:
                if b["key"] == "gpqa_diamond":
                    b["score_unit"] = "elo"
        return raw

    monkeypatch.setattr(benchmarks, "_yaml", units)
    out = _charts(monkeypatch, [_row("m/a", "Model A", {
        "gpqa_diamond_score": _cell("1450", 1450.0)})])
    v = out["models"][0]["values"][0]
    assert not v["chart"] and v["display"] == "1450"


def test_it_is_served_without_a_token(monkeypatch):
    @contextmanager
    def fake_connection():
        yield _Conn()

    monkeypatch.setenv("API_TOKEN", "s3cret")
    monkeypatch.setattr(benchmarks, "connection", fake_connection)
    monkeypatch.setattr(benchmarks, "table", lambda conn: _table([]))
    got = TestClient(app).get("/ai-benchmarks")
    assert got.status_code == 200
    assert got.json()["models"] == []


def test_the_signed_in_table_stays_behind_the_gate(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "s3cret")
    assert TestClient(app).get("/benchmarks/table").status_code == 401


def test_the_build_is_reused_until_the_table_changes(monkeypatch):
    calls = []

    def counted(conn):
        calls.append(1)
        return _table([_row("m/a", "Model A", {"gpqa_diamond_score": _cell("81", 81.0)})])

    monkeypatch.setattr(benchmarks, "table", counted)
    benchmarks.charts(_Conn(("1", "t0", "h0")))
    benchmarks.charts(_Conn(("1", "t0", "h0")), "m/a")
    assert len(calls) == 1
    # A cell written (newer updated_at), a cell removed, a row renamed: each rebuilds.
    benchmarks.charts(_Conn(("1", "t1", "h0")))
    benchmarks.charts(_Conn(("0", "t1", "h0")))
    benchmarks.charts(_Conn(("0", "t1", "h1")))
    assert len(calls) == 4


def test_a_recent_check_is_served_with_no_database_call(monkeypatch):
    monkeypatch.setattr(benchmarks, "table", lambda conn: _table([_row("m/a", "Model A", {
        "gpqa_diamond_score": _cell("81", 81.0)})]))
    assert benchmarks.charts_if_fresh("m/a") is None  # nothing kept yet
    benchmarks.charts(_Conn())
    checked = benchmarks._charts_kept.checked
    kept = benchmarks.charts_if_fresh("m/a", now=checked + 1)
    assert kept["model"]["series"][0]["values"][0]["display"] == "81"
    assert kept["models"][0] == {"id": "m/a", "label": "Model A", "tracked": True,
                                 "benchmarks_scored": 1, "series_count": 1}
    window = benchmarks.charts_recheck_seconds()
    # Past the window, not on it: `checked + window - checked` can land a hair
    # under `window` when the clock reads high (it did on CI, #589).
    assert benchmarks.charts_if_fresh("m/a", now=checked + window + 0.5) is None


def test_the_recheck_window_is_the_contracts_and_has_no_default(monkeypatch):
    assert benchmarks.charts_recheck_seconds() > 0
    real = benchmarks._yaml
    monkeypatch.setattr(benchmarks, "_yaml", lambda name: (
        {k: v for k, v in real(name).items() if k != "charts"} if name == "module_settings.yaml"
        else real(name)))
    benchmarks.charts_recheck_seconds.cache_clear()
    with pytest.raises(ValueError, match="charts.recheck_seconds"):
        benchmarks.charts_recheck_seconds()


def test_an_old_copy_is_served_while_the_check_runs_behind_it(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "s3cret")
    monkeypatch.setattr(benchmarks, "table", lambda conn: _table([_row("m/a", "Model A", {
        "gpqa_diamond_score": _cell("81", 81.0)})]))
    benchmarks.charts(_Conn())
    kept = benchmarks._charts_kept
    window = benchmarks.charts_recheck_seconds()
    benchmarks._charts_kept = kept._replace(checked=kept.checked - window - 1)
    started = []
    monkeypatch.setattr(benchmarks, "refresh_charts_in_background", lambda: started.append(1))

    @contextmanager
    def no_database():
        raise AssertionError("an old copy is served without waiting on the database")
        yield  # pragma: no cover

    monkeypatch.setattr(benchmarks, "connection", no_database)
    got = TestClient(app).get("/ai-benchmarks", params={"model": "m/a"})
    assert got.status_code == 200
    assert got.json()["model"]["series"][0]["values"][0]["display"] == "81"
    assert started == [1]


def test_a_copy_kept_for_another_database_is_never_served(monkeypatch):
    monkeypatch.setattr(benchmarks, "table", lambda conn: _table([_row("m/a", "Model A", {
        "gpqa_diamond_score": _cell("81", 81.0)})]))
    monkeypatch.setenv("BENCHMARKS_DATABASE_URL", "postgresql://one/db")
    benchmarks.charts(_Conn())
    monkeypatch.setenv("BENCHMARKS_DATABASE_URL", "postgresql://two/db")
    assert benchmarks.charts_kept("m/a") is None
    assert benchmarks.charts_if_fresh("m/a") is None


def _move(old="5", new="3", direction="better", source="swebench", out_of=34):
    from datetime import UTC, datetime

    return ("m/a", "swe_bench_verified", old, new, out_of, direction,
            datetime(2026, 10, 28, tzinfo=UTC), source)


def _ranked(monkeypatch, moves, display="3"):
    # A fresh build each case: in use, a moved rank rewrites its cell, which moves
    # the fingerprint; here every case shares one, so the kept build is dropped.
    monkeypatch.setattr(benchmarks, "_charts_kept", None)
    monkeypatch.setattr(benchmarks, "table", lambda conn: _table([_row("m/a", "Model A", {
        "swe_bench_verified_rank": _cell(display, float(display), rank_out_of=35)})]))
    return benchmarks.charts(_Conn(moves=moves), "m/a")["model"]["series"][0]["values"][0]


def test_a_position_that_moved_says_where_the_board_had_it(monkeypatch):
    v = _ranked(monkeypatch, [_move()])
    assert v["moved"] == {"direction": "up", "was": "5", "was_out_of": 34,
                          "on": "2026-10-28T00:00:00+00:00"}
    assert _ranked(monkeypatch, [_move(old="2", direction="worse")])["moved"]["direction"] == "down"


def test_no_arrow_when_another_board_or_an_older_position_is_shown(monkeypatch):
    # Another source's move is not this board's.
    assert _ranked(monkeypatch, [_move(source="vals")])["moved"] is None
    # The board has moved again since: the arrow would describe a position not shown.
    assert _ranked(monkeypatch, [_move(new="4")])["moved"] is None
    assert _ranked(monkeypatch, [])["moved"] is None


def test_a_score_never_carries_an_arrow(monkeypatch):
    out = _charts(monkeypatch, [_row("m/a", "Model A", {
        "swe_bench_verified_score": _cell("60", 60.0)})])
    assert out["models"][0]["values"][0]["moved"] is None


def test_the_fresh_path_reads_no_file(monkeypatch):
    """#589 review: serving from memory must not parse module_settings.yaml per hit."""
    monkeypatch.setattr(benchmarks, "table", lambda conn: _table([_row("m/a", "Model A", {
        "gpqa_diamond_score": _cell("81", 81.0)})]))
    benchmarks.charts(_Conn())
    benchmarks.charts_recheck_seconds()  # the first read, as the first request makes it
    reads = []
    real = benchmarks._yaml
    monkeypatch.setattr(benchmarks, "_yaml", lambda name: reads.append(name) or real(name))
    for _ in range(3):
        assert benchmarks.charts_if_fresh("m/a") is not None
    assert reads == []
