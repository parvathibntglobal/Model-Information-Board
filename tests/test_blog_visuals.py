"""Longer posts with tables, charts and diagrams, and no skim lines (2026-10-13).

The team read the skim view as an incomplete post and asked for an 8 to 15
minute read with visuals used where a topic needs them. Pinned here:
- the generator asks for 2 to 5 visuals, at most one per section, and a chart
  plots only figures the sources, fact sheet or our notes state (rule 3);
- every format runs 1,850 to 3,450 words (8 to 15 minutes at 230 a minute);
- skim lines are gone from the prompt, the tool and the export, and the page
  shows every paragraph in full with no skim/full toggle;
- views.js draws each visual kind from the post's own data.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import generate_sample_blogs as g

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "js" / "blog_visuals.mjs"
CTX = g.norm("Alpha costs $0.042 per million input tokens and Beta costs 0.6. "
             "Alpha took 73 seconds.")


def _essay(*visuals):
    secs = [{"heading": f"h{i}", "paragraphs": ["p"]} for i in range(6)]
    return {"sections": secs,
            "visuals": [dict(vis, section=vis.get("section", i)) for i, vis in enumerate(visuals)]}


TABLE = {"kind": "table", "caption": "Side by side.", "columns": ["Model", "Price"],
         "rows": [["Alpha", "$0.042"], ["Beta", "0.6"]]}
CHART = {"kind": "chart", "caption": "Input price.", "unit": "USD per 1M input tokens",
         "bars": [{"label": "Alpha", "value": 0.042}, {"label": "Beta", "value": 0.6}]}
FLOW = {"kind": "diagram", "caption": "Path.",
        "steps": ["Client sends", "Router picks", "Provider answers"]}


def test_well_formed_visuals_pass():
    assert g.visual_violations(_essay(TABLE, CHART, FLOW), (2, 5), CTX) == []


def test_too_few_visuals_are_refused():
    assert any(v.startswith("visuals:") for v in g.visual_violations(_essay(TABLE), (2, 5), CTX))


def test_a_chart_plots_only_stated_figures():
    bars = [{"label": "Alpha", "value": 0.042}, {"label": "Beta", "value": 0.55}]
    made_up = dict(CHART, bars=bars)
    v = g.visual_violations(_essay(TABLE, made_up), (2, 5), CTX)
    assert any("0.55 appears in no discussion" in x for x in v)


def test_a_chart_needs_a_unit_and_a_table_needs_even_rows():
    no_unit = dict(CHART, unit="")
    ragged = dict(TABLE, rows=[["Alpha"], ["Beta", "0.6"]])
    v = g.visual_violations(_essay(ragged, no_unit), (2, 5), CTX)
    assert any("names the unit" in x for x in v)
    assert any("one cell per column" in x for x in v)


def test_a_diagram_has_short_steps():
    words = "one two three four five six seven eight nine ten eleven twelve thirteen"
    long = dict(FLOW, steps=[words, "b", "c"])
    v = g.visual_violations(_essay(TABLE, long), (2, 5), CTX)
    assert any("at most 12 words" in x for x in v)


def test_chart_values_read_as_the_sources_write_them():
    assert g._num_text(16384.0) == "16384" and g._num_text(0.0205) == "0.0205"


def test_visual_text_is_checked_as_prose():
    paths = [p for p, _t in g.prose_fields(_essay(TABLE, CHART, FLOW))]
    assert "visuals[0].rows[0][1]" in paths
    assert "visuals[1].bars[0].label" in paths
    assert "visuals[2].steps[0]" in paths


def test_one_visual_per_section_and_a_real_section():
    essay = _essay(TABLE, dict(CHART, section=0), dict(FLOW, section=9))
    v = g.visual_violations(essay, (2, 5), CTX)
    assert any("already has a visual" in x for x in v)
    assert any("must be a section index" in x for x in v)


def test_too_many_visuals_says_which_to_remove():
    v = g.visual_violations(_essay(*[dict(TABLE, section=i) for i in range(6)]), (2, 5), CTX)
    assert any("REMOVE 1" in x and "visuals[5]" in x for x in v)


def test_length_counts_what_the_reader_reads():
    body = {"sections": [{"heading": "h", "paragraphs": ["word " * 100]}], "tldr": "one two three",
            "faq": [{"question": "q one?", "answer": "a " * 50}]}
    with_visual = dict(body, visuals=[dict(TABLE, section=0)])
    assert g.reading_words(body) == 100 + 3 + 52
    assert g.reading_words(with_visual) > g.reading_words(body)


def test_every_format_is_an_8_to_15_minute_read_with_visuals():
    for f in g.load_formats()["formats"]:
        assert f["words"] == [1850, 3450], f["key"]
        assert f["blocks"]["visuals"] == [2, 5], f["key"]


def test_skim_lines_are_gone_from_prompt_tool_and_formats():
    params = g.TOOL["function"]["parameters"]["properties"]
    sec = params["sections"]["items"]
    assert "skim" not in sec["properties"] and "skim" not in sec["required"]
    assert "visual" not in sec["properties"] and "visuals" in params
    fmts = g.load_formats()
    sys_text = g.system_for(dict(fmts["formats"][0], prose=fmts["prose"]))
    assert "SKIM" not in sys_text and "VISUALS" in sys_text
    assert "skim_words" not in fmts["prose"]
    assert not hasattr(g, "_skim_lines")


@pytest.fixture(scope="module")
def page() -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is required to render web/src/board/views.js")
    run = subprocess.run([node, str(PROBE)], capture_output=True, text=True, encoding="utf-8",
                         cwd=ROOT, check=False)
    if run.returncode != 0:
        pytest.fail(f"blog_visuals.mjs failed:\n{run.stderr}")
    return json.loads(run.stdout)


def test_the_page_shows_every_paragraph_in_full(page):
    assert not page["hasToggle"]
    assert "FULL PARAGRAPH TEXT" in page["html"] and "SKIM LINE" not in page["html"]
    assert "Its second sentence must render too." in page["html"]
    assert page["readTime"]


def test_the_page_draws_each_visual(page):
    html = page["html"]
    assert "es-fig-table" in html and "1,048,576" in html
    assert "es-fig-chart" in html and "<svg" in html and "USD per 1M input tokens" in html
    assert "es-fig-flow" in html and "Router picks a provider" in html


# ── AI-generated illustrations ─────────────────────────────────────────────────

SCENE = ("A developer at a desk watches a long queue of glowing request packets stall at a "
         "single narrow gate while other gates stand empty, in a dim server room.")
ILL = {"section": 0, "scene": SCENE, "alt": "Requests stalling at one gate",
       "caption": "One route holds."}
#: Four pictures from one call since 2026-10-14; the first opens the post.
ILLS = [ILL] + [dict(ILL, section=n) for n in (1, 2, 3)]


def test_four_well_formed_pictures_pass():
    assert g.illustration_violations({"illustrations": ILLS}, 6) == []


def test_a_post_needs_exactly_four_pictures():
    for ills in ([], ILLS[:3], ILLS + [ILL]):
        v = g.illustration_violations({"illustrations": ills}, 6)
        assert any("propose exactly 4" in x for x in v)


def test_the_first_picture_opens_the_post():
    v = g.illustration_violations({"illustrations": [dict(ILL, section=2)] + ILLS[1:]}, 6)
    assert any(x.startswith("illustrations[0].section: the first picture opens") for x in v)


def test_the_other_three_pictures_go_to_three_sections():
    v = g.illustration_violations({"illustrations": ILLS[:2] + [dict(ILL, section=1)] * 2}, 6)
    assert any("three different sections" in x for x in v)


def test_a_picture_shows_no_data_brand_or_text():
    for bad in ("a dashboard showing latency", "the OpenAI logo on a wall",
                "a chart rising sharply", "a sign that reads ERROR 500 on a screen",
                "Claude and GPT robots shaking hands"):
        scene = f"{bad} in a quiet office at night with soft blue light on the desk and shelves"
        v = g.illustration_violations({"illustrations": [dict(ILL, scene=scene)] + ILLS[1:]}, 6)
        assert any(".scene:" in x and "no text, numbers, brands" in x for x in v), bad


def test_a_picture_points_at_a_real_section_and_has_alt_text():
    v = g.illustration_violations({"illustrations": ILLS[:3] + [dict(ILL, section=9, alt="")]}, 6)
    assert any(".section:" in x for x in v) and any(".alt:" in x for x in v)


def test_captions_and_alt_text_are_checked_as_prose():
    paths = [p for p, _t in g.prose_fields({"illustrations": [ILL]})]
    assert "illustrations[0].caption" in paths and "illustrations[0].alt" in paths


def test_one_call_asks_for_a_wide_grid_of_four_scenes(monkeypatch):
    import base64
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (2400, 1350), (20, 30, 60)).save(buf, "PNG")
    png = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"images": [{"image_url": {"url": png}}]}}],
                    "usage": {"prompt_tokens": 50, "completion_tokens": 1290, "cost": 0.039}}

    seen = {}

    def fake_post(url, **kw):
        seen.update(kw["json"])
        return Resp()

    monkeypatch.setattr(g.httpx, "post", fake_post)
    img, usage = g.draw_grid([SCENE] * 4, "k", "https://openrouter.example/api/v1")
    assert img.size == (2400, 1350) and usage["cost"] == 0.039
    assert seen["modalities"] == ["image", "text"]
    assert seen["image_config"] == {"aspect_ratio": "16:9"}
    prompt = seen["messages"][0]["content"]
    assert "no text" in prompt and "2x2 grid" in prompt and "Panel 4 (bottom right)" in prompt
    src = g.jpeg_data_url(img)
    out = Image.open(io.BytesIO(base64.b64decode(src.split(",", 1)[1])))
    assert src.startswith("data:image/jpeg;base64,") and out.width == g.IMAGE_MAX_WIDTH


def test_a_reply_without_an_image_raises_never_blanks(monkeypatch):
    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "I cannot draw that."}}]}

    monkeypatch.setattr(g.httpx, "post", lambda url, **kw: Resp())
    with pytest.raises(g.BuildError):
        g.draw_grid([SCENE] * 4, "k", "https://openrouter.example/api/v1")


def test_the_page_labels_a_generated_picture_and_draws_only_inline_ones(page):
    html = page["html"]
    assert "es-fig-image" in html and "AI-generated illustration" in html
    assert 'alt="Requests queueing at one gate"' in html
    assert "evil.example" not in html and "REMOTE IMAGE" not in html


def test_a_word_over_its_cap_is_named_in_its_sentences():
    """The refusal quotes the sentences to rewrite. It once printed none: the
    regex's word boundaries had become literal control characters (2026-10-13)."""
    para = ("Ask whether the patch passed. Then ask whether review held. "
            "Finally check whether it shipped.")
    lens = [len(s.split()) for s in g.sentences(para)]
    out = [v for v in g._lively([para], lens, g.load_formats()["prose"]) if "'whether'" in v]
    assert out and "Ask whether the patch passed" in out[0]


def test_a_stock_phrase_is_named_in_its_sentence():
    """The refusal quotes the sentence holding the phrase. A bare 'say it
    another way' held a draft for four repairs (2026-10-13)."""
    prose = g.load_formats()["prose"]
    phrase = prose["avoid_phrases"][0]
    para = f"The loop is grounded. That run is {phrase} anything else at all. It shipped."
    lens = [len(s.split()) for s in g.sentences(para)]
    out = [v for v in g._lively([para], lens, prose) if "stock phrase" in v]
    assert out and f"That run is {phrase}" in out[0]


def test_a_draft_with_visuals_and_pictures_loads_and_stores():
    """The draft loader and the store validate block types. They did not know
    `visual` or `image`, so the first illustrated post was skipped and never
    reached Admin (2026-10-13)."""
    from judge import blog_posts

    doc = {"slug": "s", "title": "t", "dek": "d", "tag": "x", "by": "b", "lead": "l", "meta": [],
           "provenance": {}, "body": [["h2", "h"], ["p", "p"],
                                      ["visual", {"kind": "diagram", "caption": "c",
                                                  "steps": ["a", "b", "c"]}],
                                      ["image", {"src": "data:image/jpeg;base64,AA==",
                                                 "alt": "a"}]]}
    assert blog_posts._problem(doc) is None


def test_an_engineers_quote_counts_as_one_word_in_sentence_length():
    """A quote cannot be split, so the length limits apply to our words only."""
    quote = " ".join(["word"] * 28)
    para = f"The engineer described the setup: «{quote}». We agree. It held. Then it failed."
    out = g._pace({"tldr": ""}, [], [para], g.load_formats()["prose"])
    assert not [v for v in out if v.startswith("a sentence of")]


def test_the_post_opens_on_its_picture(page):
    """Every post opens on a picture (2026-10-14). A post written before covers
    has its first generated picture lifted to the top; the remote one in the
    fixture is still never drawn."""
    html = page["html"]
    assert 0 <= html.find("es-cover") < html.find("<h2")
    assert html.count("es-fig-image") == 1 and "REMOTE IMAGE" not in html


@pytest.mark.parametrize("scene, refused", [
    # 2026-10-14: a field report failed all 5 repairs on this shape - the
    # writer listed what the picture leaves out, and the list was read as shown.
    ("A reviewer studies a long scroll of requests, without any numerals, brand marks, or "
     "recognizable logos, in soft blue light at a quiet desk.", None),
    ("Two diverging paths in a forest at dusk with no people or text anywhere in the frame, "
     "only fog and a single lantern.", None),
    # A negation stops at the first word that is not part of the list.
    ("A robot without a logo, holding a chart that rises sharply above a quiet city at "
     "night.", "chart"),
    ("A quiet desk with no text on the screen while a dashboard glows beside an empty "
     "chair.", "dashboard"),
])
def test_what_a_scene_leaves_out_is_not_what_it_shows(scene, refused):
    ills = [dict(ILL, scene=scene)] + ILLS[1:]
    v = [x for x in g.illustration_violations({"illustrations": ills}, 6)
         if ".scene:" in x and "no text, numbers" in x]
    assert (v[0].split("'")[1] if v else None) == refused
