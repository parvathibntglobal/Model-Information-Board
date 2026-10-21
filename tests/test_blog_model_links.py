"""A model named in a blog post links where a reader can follow it.

2026-10-19. Rendered over the 150 published posts, the blog's model links went
to `/models/<id>` - 1,102 of them - which is behind the sign-in, so every reader
who clicked one landed on the login screen. Only the 31 tracked models were
known, and only by their full display name, so "Opus 5.5" (219 mentions) and
"Fable 5.1" (110) never linked, and no "A vs B" reached the comparison.

Rendered through node from the real views and the real name module
(tests/js/blog_model_links.mjs), as test_board_links_are_real_links does.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from collect.registry.propose import FAMILY_WORDS

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "js" / "blog_model_links.mjs"


def _model(canonical: str | None, display: str, mv: str) -> dict:
    return {"model_version_id": mv, "canonical_id": canonical, "display_name": display}


MODELS = [
    _model("anthropic/claude-opus-5.5", "Anthropic: Claude Opus 5.5", "mv_a"),
    _model("anthropic/claude-opus-5", "Anthropic: Claude Opus 5", "mv_b"),
    _model("openai/gpt-6-astra", "OpenAI: GPT-6 Astra", "mv_c"),
    _model("z-ai/glm-5.3", "Z.ai: GLM 5.3", "mv_d"),
    # Two models one shorter name could mean: "DeepSeek V4 Pro" is neither.
    _model("deepseek/deepseek-v4-pro", "DeepSeek: DeepSeek V4 Pro 0423", "mv_e"),
    _model("deepseek/deepseek-v4-pro-0813", "DeepSeek: DeepSeek V4 Pro 0813", "mv_f"),
    # A vendor word followed by a tier word, not a family word: no "Large 3".
    _model("mistralai/mistral-large-3", "Mistral: Mistral Large 3", "mv_g"),
    # In the registry, with no public catalog page.
    _model("qwen/qwen3.8-max", "Qwen: Qwen3.8 Max", "mv_h"),
    # No canonical id at all: the catalog has no page for an internal key.
    _model(None, "Acme: Widget 9", "mv_i"),
]
CATALOG = [m["canonical_id"] for m in MODELS
           if m["canonical_id"] not in (None, "qwen/qwen3.8-max")]

BODY = [
    ["p", "Opus 5.5 vs GPT-6 Astra on one task."],
    ["p", "Opus 5 was slower than Opus 5.5."],
    ["p", "GLM-5.3 and GLM 5.3 and DeepSeek V4 Pro."],
    ["p", "Large 3 was not tried. Qwen3.8 Max and Widget 9 were."],
    ["p", "Opus 5 vs Opus 5 is no comparison."],
]
POSTS = [
    {"slug": "pair", "title": "Claude Opus 5.5 vs GPT-6 Astra: a test", "tag": "Head-to-head",
     "body": BODY},
    {"slug": "topic", "title": "Humans vs Machines: a test", "tag": "Topic explainer",
     "body": [["p", "Nothing here names a model."]]},
]


def _render(tmp_path: Path, *, catalog: list[str] | None) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is required to render the blog; install it or fix PATH")
    fx = tmp_path / "fx.json"
    fx.write_text(json.dumps({"models": MODELS, "catalog_ids": catalog, "posts": POSTS}),
                  encoding="utf-8")
    run = subprocess.run([node, str(PROBE), str(fx)], capture_output=True, text=True,
                         encoding="utf-8", cwd=ROOT, check=False)
    if run.returncode != 0:
        pytest.fail(f"blog_model_links.mjs failed:\n{run.stderr}")
    return json.loads(run.stdout)


@pytest.fixture(scope="module")
def out(tmp_path_factory) -> dict:
    return _render(tmp_path_factory.mktemp("blog"), catalog=CATALOG)


def _by_text(out, slug="pair"):
    return {a["text"]: a for a in out["posts"][slug]["links"]}


def test_the_family_words_are_the_fetchs_own(out):
    """The JS copy of `rule_variants`' vocabulary must not drift from Python's."""
    assert set(out["family_words"]) == set(FAMILY_WORDS)


def test_no_blog_link_goes_behind_the_sign_in(out):
    hrefs = [a["href"] for p in out["posts"].values() for a in p["links"]]
    assert hrefs and not [h for h in hrefs if h.startswith("/models")]


def test_a_vendor_dropped_name_links_to_the_public_page(out):
    links = _by_text(out)
    assert links["Opus 5"]["href"] == "/ai-models/anthropic/claude-opus-5"
    assert links["Opus 5.5"]["href"] == "/ai-models/anthropic/claude-opus-5.5"


def test_a_separator_is_not_part_of_the_name(out):
    """Rule 10: "GLM-5.3" and "GLM 5.3" are one model. Only the first in a
    paragraph is linked, which is the existing first-mention rule."""
    links = _by_text(out)
    assert links["GLM-5.3"]["href"] == "/ai-models/z-ai/glm-5.3"


def test_a_name_that_fits_two_models_links_to_neither(out):
    texts = [a["text"] for a in out["posts"]["pair"]["links"]]
    assert not [t for t in texts if "DeepSeek" in t]
    assert "DeepSeek V4 Pro" not in out["posts"]["pair"]["cards"]


def test_a_tier_word_is_not_a_name(out):
    texts = [a["text"] for a in out["posts"]["pair"]["links"]] + out["posts"]["pair"]["cards"]
    assert "Large 3" not in texts


def test_a_model_without_a_public_page_keeps_its_card_and_no_link(out):
    texts = [a["text"] for a in out["posts"]["pair"]["links"]]
    assert "Qwen3.8 Max" not in texts and "Widget 9" not in texts
    assert {"Qwen3.8 Max", "Widget 9"} <= set(out["posts"]["pair"]["cards"])


def test_a_vs_b_in_the_text_opens_the_comparison(out):
    link = _by_text(out)["Opus 5.5 vs GPT-6 Astra"]
    assert link["cls"] == "es-vs"
    assert link["href"] == "/compare/claude-opus-5.5-vs-gpt-6-astra"


def test_one_model_against_itself_is_not_a_comparison(out):
    assert not [a for a in out["posts"]["pair"]["links"]
                if a["cls"] == "es-vs" and a["text"].startswith("Opus 5 vs Opus 5")]


def test_a_two_model_post_links_its_comparison(out):
    head = [a for a in out["posts"]["pair"]["links"] if a["text"].startswith("Compare ")]
    assert [a["href"] for a in head] == [
        "/compare/claude-opus-5.5-vs-gpt-6-astra"]


def test_a_vs_title_that_names_no_model_gets_no_comparison(out):
    assert not [a for a in out["posts"]["topic"]["links"] if "/compare" in a["href"]]


def test_without_the_catalog_list_no_model_page_is_linked(tmp_path):
    """Rule 12: until the page knows which models have a page, it draws no link
    that might 404. Comparisons need no catalog page and still link."""
    out = _render(tmp_path, catalog=None)
    links = out["posts"]["pair"]["links"]
    assert not [a for a in links if a["href"].startswith("/ai-models")]
    assert [a for a in links if a["cls"] == "es-vs"]
