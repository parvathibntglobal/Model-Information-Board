"""The keyword plan behind /seo-keywords?tab=plan, and the rules that build it.

scripts/build_keyword_plan.py runs by hand (it reads the SEO workbook); its
rules are pure and pinned here, and the committed plan is checked for what the
page promises: public pages only, one word only for a model, and no volume
without a measurement behind it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from judge import gate, keyword_plan
from judge.app import app

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "build_keyword_plan", ROOT / "scripts" / "build_keyword_plan.py"
)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

SIGNED_IN = ("/board", "/models", "/admin", "/seo-keywords", "/keywords", "/login")


# ── the endpoint ────────────────────────────────────────────────────────────


def test_a_missing_plan_says_so(tmp_path):
    data = keyword_plan.load(tmp_path / "absent.json")
    assert data["available"] is False and data["keywords"] == []


def test_the_plan_is_not_a_public_read():
    from starlette.requests import Request

    req = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/admin/seo-keyword-plan",
            "query_string": b"",
            "headers": [],
        }
    )
    assert not gate.is_public_read(req)
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        assert TestClient(app).get("/admin/seo-keyword-plan").status_code == 401


# ── the committed plan ──────────────────────────────────────────────────────


def _plan():
    if not keyword_plan.PATH.exists():
        pytest.skip("no plan in this checkout")
    return keyword_plan.load()


def test_every_target_is_a_public_page():
    data = _plan()
    pages = {p["key"]: p for p in data["pages"]}
    for p in pages.values():
        assert not p["url"].split("?")[0].startswith(SIGNED_IN), p
    for k in data["keywords"]:
        assert k["page"] in pages
        assert not k["link"].split("?")[0].startswith(SIGNED_IN), k


def test_one_word_is_a_model_or_nothing():
    for k in _plan()["keywords"]:
        if len(build.norm(k["keyword"]).split()) == 1:
            assert k["combo"].startswith("E20"), k


def test_every_volume_has_a_measurement_behind_it():
    data = _plan()
    shares = data["method"]["shares"]
    for k in data["keywords"]:
        assert k["volume_kind"] in ("measured", "estimated")
        if k["volume_kind"] == "estimated":
            cls = k["basis"].split(" x ")[1].split(" share")[0]
            assert shares[cls]["share"] is not None and shares[cls]["pairs"], k


def test_the_threshold_comes_from_the_plan_file():
    plan = yaml.safe_load((ROOT / "seo" / "keyword_plan.yaml").read_text(encoding="utf-8"))
    assert _plan()["min_monthly_searches"] == plan["min_monthly_searches"]


def test_every_combination_names_a_page_or_a_reason():
    plan = yaml.safe_load((ROOT / "seo" / "keyword_plan.yaml").read_text(encoding="utf-8"))
    for code, spec in plan["combinations"].items():
        assert spec.get("skip") or spec.get("page") in plan["pages"], code


# ── the rules ───────────────────────────────────────────────────────────────


def test_a_band_is_read_as_a_range():
    assert build.band("10K – 100K") == (10_000, 100_000)
    assert build.band("100K – 1M") == (100_000, 1_000_000)
    assert build.band("0") == (0, 0)
    assert round(build.midpoint((10_000, 100_000))) == 31_623
    assert build.midpoint((0, 0)) == 0


VALUES = {
    "model": [
        {"name": "Claude Opus 5"},
        {"name": "GPT 5"},
        {"name": "Nano Banana", "kind": "image"},
    ],
    "vendor": [{"name": "OpenAI"}],
}


def test_a_pair_is_made_once_and_like_with_like():
    made = [kw for kw, _ in build.expand("{model} vs {model_b}", VALUES)]
    assert made == ["Claude Opus 5 vs GPT 5"]


def test_a_template_with_no_values_makes_nothing():
    assert list(build.expand("{benchmark} leaderboard", VALUES)) == []


def test_one_word_survives_only_as_a_model():
    assert build.one_word_ok("qwen3", {"model": {"name": "qwen3"}})
    assert not build.one_word_ok("rag", {"job": {"name": "rag"}})
    assert build.one_word_ok("coding agents", {"job": {"name": "coding agents"}})


PLANNER = {
    "gpt 5": {
        "keyword": "gpt 5",
        "band": (100_000, 1_000_000),
        "label": "100K – 1M",
        "combo": "E20",
    },
    "gpt 5 pricing": {
        "keyword": "gpt 5 pricing",
        "band": (1_000, 10_000),
        "label": "1K – 10K",
        "combo": "E20",
    },
    "cheapest llm": {
        "keyword": "cheapest llm",
        "band": (1_000, 10_000),
        "label": "1K – 10K",
        "combo": "E12",
    },
    "cheapest llm api": {
        "keyword": "cheapest llm api",
        "band": (1_000, 10_000),
        "label": "1K – 10K",
        "combo": "E12",
    },
}


def test_a_share_is_measured_from_a_heads_own_pair():
    shares = build.measure_shares(
        {"pricing": ["{model} pricing"]}, PLANNER, {"model": [{"name": "gpt 5"}]}
    )
    assert shares["pricing"]["pairs"][0]["keyword"] == "gpt 5 pricing"
    assert shares["pricing"]["share"] == pytest.approx(0.01)


def test_a_phrase_that_is_not_a_value_never_calibrates():
    """ "cheapest llm" -> "cheapest llm api" is not a model's API searches; taking
    it made the first build's api share 316% (2026-10-19)."""
    shares = build.measure_shares({"api": ["{model} api"]}, PLANNER, {"model": [{"name": "gpt 5"}]})
    assert shares["api"] == {"share": None, "pairs": []}


def test_an_estimate_needs_a_measured_head_and_a_share():
    shares = {"pricing": {"share": 0.02, "pairs": [{}]}}
    cls_of = {"{model} price": "pricing"}
    est = build.volume(
        "gpt 5 price", "{model} price", {"model": {"name": "gpt 5"}}, PLANNER, shares, cls_of
    )
    assert est["volume_kind"] == "estimated" and est["searches"] == 6300
    none = build.volume(
        "grok 9 price", "{model} price", {"model": {"name": "grok 9"}}, PLANNER, shares, cls_of
    )
    assert none["volume_kind"] is None


def test_a_page_type_url_loses_its_pattern():
    assert build.base_url("/compare?ids=<a>,<b>") == "/compare"
    assert build.base_url("/benchmarks/<benchmark>") == "/benchmarks"
    assert build.base_url("/model-finder") == "/model-finder"
