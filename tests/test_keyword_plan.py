"""The keyword plan behind /seo-keywords?tab=plan, and the rules that build it.

scripts/build_keyword_plan.py runs by hand (it reads the SEO workbook); its
rules are pure and pinned here, and the committed plan is checked for what the
page promises: public pages only, every section full, one word only for a
model, no phrasing crowding out the rest, and no volume without a measurement.
"""

from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from judge import gate, keyword_plan
from judge.app import app

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "build_keyword_plan", ROOT / "scripts" / "build_keyword_plan.py"
)
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

SIGNED_IN = ("/board", "/models", "/admin", "/seo-keywords", "/keywords", "/login")
PLAN_YAML = yaml.safe_load((ROOT / "seo" / "keyword_plan.yaml").read_text(encoding="utf-8"))


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


def test_every_section_holds_at_least_its_minimum():
    data = _plan()
    per = Counter(k["page"] for k in data["keywords"])
    for p in data["pages"]:
        assert per[p["key"]] >= data["per_section"], (p["key"], per[p["key"]])


def test_the_suggestions_that_were_turned_down_stay_out():
    """Ruled 2026-10-19 (anooj): Glossary, What changed and Developer guides
    stay; these went, and a new suggestion must be a different idea."""
    gone = {
        "Benchmarks",
        "Provider pages",
        "Run models locally",
        "Data, privacy and compliance",
        "Best model by industry or team",
        "LLM price tracker",
        "Hardware and VRAM calculator",
        "Model selection checklist",
        "Comparison download",
    }
    names = {p["name"] for p in _plan()["pages"]}
    assert not gone & names
    assert {"Glossary", "What changed", "Developer guides"} <= names


def test_no_phrasing_crowds_out_a_section():
    """The point of the round-robin: a section is many phrasings, not one
    phrasing with every model name. No phrasing holds more than a tenth."""
    data = _plan()
    by = {}
    for k in data["keywords"]:
        by.setdefault(k["page"], Counter())[k["pattern"]] += 1
    for page, pats in by.items():
        assert pats.most_common(1)[0][1] <= sum(pats.values()) // 10, (page, pats.most_common(1))


def test_a_keyword_is_on_one_section_only():
    keys = [build.norm(k["keyword"]) for k in _plan()["keywords"]]
    assert len(keys) == len(set(keys))


def test_one_word_is_a_model_or_nothing():
    names = {build.norm(v) for k in ("model", "casual") for v in PLAN_YAML["pools"][k]}
    names |= {build.norm(m["name"]) for m in build.tracked_models(None)}
    for k in _plan()["keywords"]:
        key = build.norm(k["keyword"])
        if len(key.split()) == 1:
            assert key in names, k


def test_every_volume_has_a_measurement_behind_it():
    data = _plan()
    shares = data["method"]["shares"]
    for k in data["keywords"]:
        assert k["volume_kind"] in ("measured", "estimated", None)
        if k["volume_kind"] == "estimated":
            cls = k["basis"].split(" x ")[1].split(" share")[0]
            assert shares[cls]["share"] is not None and shares[cls]["pairs"], k
        if k["volume_kind"] is None:
            assert k["volume"] is None and k["searches"] is None, k


def test_every_section_names_a_page():
    for key in PLAN_YAML["sections"]:
        assert key in PLAN_YAML["pages"], key


# ── the rules ───────────────────────────────────────────────────────────────


def test_a_band_is_read_as_a_range():
    assert build.band("10K – 100K") == (10_000, 100_000)
    assert build.band("100K – 1M") == (100_000, 1_000_000)
    assert build.band("0") == (0, 0)
    assert round(build.midpoint((10_000, 100_000))) == 31_623
    assert build.midpoint((0, 0)) == 0


POOLS = {
    "model": [{"name": "claude opus 5"}, {"name": "gpt 5"}, {"name": "kimi k3"}],
    "job": [{"name": "coding"}, {"name": "rag"}],
}


def test_a_phrasing_draws_the_same_values_every_build():
    a = list(build.candidates("{model} for {job}", POOLS, "page|t"))
    b = list(build.candidates("{model} for {job}", POOLS, "page|t"))
    assert [k for k, _ in a] == [k for k, _ in b] and len(a) == 6


def test_a_pair_never_meets_itself():
    for kw, used in build.candidates("{model} vs {model_b}", POOLS, "s"):
        assert used["model"]["name"] != used["model_b"]["name"], kw


def test_a_phrasing_with_no_values_makes_nothing():
    assert list(build.candidates("{benchmark} leaderboard", POOLS, "s")) == []


def test_a_section_takes_its_phrasings_in_turn():
    groups = [{"combo": "E20", "t": ["{model} pricing", "{model} review"]}]
    rows = build.pick("model", groups, POOLS, 4, set())
    assert [r["pattern"] for r in rows] == ["{model} pricing", "{model} review"] * 2


def test_a_keyword_already_taken_is_skipped():
    groups = [{"combo": "E1", "t": ["llm leaderboard"]}]
    assert build.pick("home", groups, POOLS, 5, {"llm leaderboard"}) == []


def test_one_word_survives_only_as_a_model():
    assert build.one_word_ok("qwen3", {"model": {"name": "qwen3"}})
    assert not build.one_word_ok("rag", {"job": {"name": "rag"}})
    assert build.one_word_ok("coding agents", {"job": {"name": "coding agents"}})


def _planner(*rows):
    return {k: {"keyword": k, "band": b, "label": lab} for k, b, lab in rows}


PLANNER = _planner(
    ("gpt 5", (100_000, 1_000_000), "100K – 1M"),
    ("gpt 5 pricing", (1_000, 10_000), "1K – 10K"),
    ("cheapest llm", (1_000, 10_000), "1K – 10K"),
    ("cheapest llm api", (1_000, 10_000), "1K – 10K"),
)


def test_a_share_is_measured_from_a_heads_own_pair():
    shares = build.measure_shares(
        {"pricing": ["{model} pricing"]}, PLANNER, {"model": [{"name": "gpt 5"}]}
    )
    assert shares["pricing"]["pairs"][0]["keyword"] == "gpt 5 pricing"
    assert shares["pricing"]["share"] == pytest.approx(0.01)


def test_a_phrase_that_is_not_a_value_never_calibrates():
    """ "cheapest llm" -> "cheapest llm api" is not a model's API searches; taking
    it made a first build's api share 316% (2026-10-19)."""
    shares = build.measure_shares({"api": ["{model} api"]}, PLANNER, {"model": [{"name": "gpt 5"}]})
    assert shares["api"] == {"share": None, "pairs": []}


def test_an_estimate_needs_a_measured_head_and_a_share():
    shares = {"pricing": {"share": 0.02, "pairs": [{}]}}
    cls_of = {"{model} price": "pricing"}
    est = build.volume(
        "gpt 5 price", "{model} price", {"model": {"name": "gpt 5"}}, PLANNER, shares, cls_of
    )
    assert est["volume_kind"] == "estimated" and est["searches"] == 6320
    unknown = {"model": {"name": "grok 9"}}
    none = build.volume("grok 9 price", "{model} price", unknown, PLANNER, shares, cls_of)
    assert none["volume_kind"] is None and none["searches"] is None


def test_a_page_type_url_loses_its_pattern():
    assert build.base_url("/compare?ids=<a>,<b>") == "/compare"
    assert build.base_url("/glossary/<concept>") == "/glossary"
    assert build.base_url("/model-finder") == "/model-finder"
