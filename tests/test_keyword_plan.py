"""The keyword plan behind /seo-keywords?tab=plan, by query type.

A query is an intent plus an entity, and the intent decides the page and the
answer format (seo/keyword_plan.yaml). scripts/build_keyword_plan.py runs by
hand (it reads the SEO workbook); its rules are pinned here, and the committed
plan is checked for what the page promises.
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


@pytest.mark.parametrize(
    "section, page",
    [
        ("definition", "glossary"),
        ("versus", "compare"),
        ("model_lookup", "model"),
        ("how_to_dev", "guides"),
        ("concept_depth", "post"),
        ("head", "home"),
    ],
)
def test_a_query_type_is_answered_where_its_format_lives(section, page):
    """The direction of 2026-10-19: versus on Compare, a model's name on its
    page, concepts in the glossary and blog posts, how-to as tutorials."""
    sec = next(s for s in _plan()["sections"] if s["key"] == section)
    assert sec["page"] == page
    assert all(k["page"] == page for k in _plan()["keywords"] if k["section"] == section)


def test_home_holds_only_the_brand_and_category_terms():
    """ "best model for X" on Home was the wrong dimension: selection queries
    are answered by the picker and the job pages."""
    home = [k["keyword"] for k in _plan()["keywords"] if k["page"] == "home"]
    assert home and len(home) < 20
    assert not [k for k in home if k.startswith("best ") and " for " in k]


def test_every_section_says_how_to_place_its_keywords():
    for s in _plan()["sections"]:
        assert s["format"] and s["place"].get("title") and s["place"].get("h1"), s["key"]


def test_a_keyword_is_listed_once():
    keys = [build.norm(k["keyword"]) for k in _plan()["keywords"]]
    assert len(keys) == len(set(keys))


def test_one_word_is_a_model_or_nothing():
    models = {build.norm(m["name"]) for m in build.tracked_models(None)}
    for k in _plan()["keywords"]:
        if len(build.norm(k["keyword"]).split()) == 1:
            assert build.norm(k["keyword"]) in models, k


def test_image_and_speech_models_stay_out_of_text_only_query_types():
    others = {build.norm(m["name"]) for m in build.tracked_models(None) if m["kind"] != "text"}
    allowed = {s["key"] for s in PLAN_YAML["sections"] if s.get("all_models")}
    for k in _plan()["keywords"]:
        if k["section"] not in allowed:
            assert not any(o in build.norm(k["keyword"]) for o in others), k


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


def test_every_section_names_a_declared_page():
    for s in PLAN_YAML["sections"]:
        assert s["page"] in PLAN_YAML["pages"], s["key"]
    assert len({s["key"] for s in PLAN_YAML["sections"]}) == len(PLAN_YAML["sections"])


# ── the rules ───────────────────────────────────────────────────────────────

ENTS = {
    "model": [
        {"name": "claude opus 5", "id": "anthropic/claude-opus-5"},
        {"name": "gpt 5", "id": "openai/gpt-5"},
        {"name": "nano banana 2", "kind": "image"},
    ],
    "job": [{"name": "coding", "link": "/reports/jobs/coding"}],
}


def test_a_pair_is_made_once_and_like_with_like():
    made = [kw for kw, _ in build.expand("{model} vs {model_b}", ENTS)]
    assert made == ["claude opus 5 vs gpt 5"]


def test_a_pair_with_a_third_entity_is_once_per_value():
    made = [kw for kw, _ in build.expand("{model} vs {model_b} for {job}", ENTS)]
    assert made == ["claude opus 5 vs gpt 5 for coding"]


def test_image_models_join_only_when_a_section_says_so():
    assert "nano banana 2 pricing" not in [k for k, _ in build.expand("{model} pricing", ENTS)]
    assert "nano banana 2 pricing" in [
        k for k, _ in build.expand("{model} pricing", ENTS, all_models=True)
    ]


def test_every_combination_is_made_nothing_sampled():
    ents = {"concept": [{"name": f"c{i}"} for i in range(50)]}
    assert len(list(build.expand("what is {concept}", ents))) == 50


def test_one_word_survives_only_as_a_model():
    assert build.one_word_ok("qwen3", {"model": {"name": "qwen3"}})
    assert not build.one_word_ok("rag", {"concept": {"name": "rag"}})


def test_a_comparison_links_to_the_pair():
    page = {"url": "/compare?ids=<a>,<b>", "kind": "page"}
    used = {"model": ENTS["model"][0], "model_b": ENTS["model"][1]}
    assert build.link("compare", page, used, {}) == (
        "/compare?ids=anthropic/claude-opus-5,openai/gpt-5",
        True,
    )


def test_a_concept_links_to_its_post_or_says_there_is_none():
    page = {"url": "/blogs/<slug>", "kind": "page"}
    written = {"rag": "topic-explainer-concept-rag"}
    assert build.link("post", page, {"concept": {"name": "rag"}}, written) == (
        "/blogs/topic-explainer-concept-rag",
        True,
    )
    assert build.link("post", page, {"concept": {"name": "lora"}}, written) == ("/blogs", False)


def test_a_job_picks_its_picker_view():
    page = {"url": "/model-picker", "kind": "page"}
    assert build.link("picker", page, {"job": ENTS["job"][0]}, {}) == (
        "/model-picker?job=coding",
        True,
    )


def test_a_band_is_read_as_a_range():
    assert build.band("10K – 100K") == (10_000, 100_000)
    assert build.band("0") == (0, 0)
    assert round(build.midpoint((10_000, 100_000))) == 31_623


PLANNER = {
    "gpt 5": {"keyword": "gpt 5", "band": (100_000, 1_000_000), "label": "100K – 1M"},
    "gpt 5 pricing": {"keyword": "gpt 5 pricing", "band": (1_000, 10_000), "label": "1K – 10K"},
    "cheapest llm": {"keyword": "cheapest llm", "band": (1_000, 10_000), "label": "1K – 10K"},
    "cheapest llm api": {
        "keyword": "cheapest llm api",
        "band": (1_000, 10_000),
        "label": "1K – 10K",
    },
}


def test_a_share_is_measured_from_a_heads_own_pair():
    shares = build.measure_shares(
        {"pricing": ["{model} pricing"]}, PLANNER, {"model": [{"name": "gpt 5"}]}
    )
    assert shares["pricing"]["share"] == pytest.approx(0.01)


def test_a_phrase_that_is_not_a_value_never_calibrates():
    shares = build.measure_shares({"api": ["{model} api"]}, PLANNER, {"model": [{"name": "gpt 5"}]})
    assert shares["api"] == {"share": None, "pairs": []}


def test_an_estimate_needs_a_measured_head_and_a_share():
    shares = {"pricing": {"share": 0.02, "pairs": [{}]}}
    cls_of = {"{model} price": "pricing"}
    est = build.volume(
        "gpt 5 price", "{model} price", {"model": {"name": "gpt 5"}}, PLANNER, shares, cls_of
    )
    assert est["volume_kind"] == "estimated" and est["searches"] == 6320
    none = build.volume(
        "x price", "{model} price", {"model": {"name": "grok 9"}}, PLANNER, shares, cls_of
    )
    assert none["volume_kind"] is None


def test_counts_in_the_plan_add_up():
    data = _plan()
    per = Counter(k["section"] for k in data["keywords"])
    for s in data["sections"]:
        assert per[s["key"]] == s["keywords"], s["key"]
