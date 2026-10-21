"""Per-page <head> text (web/src/seo/pages.js), SEO item 1, 2026-10-08.

Rendered through `node` (tests/js/seo_pages.mjs), as test_every_leaf_reaches_the_grid
does for the board, because the templates are the frontend's own code. What is
pinned: every page gets its own title and a description that fits; a section's
canonical is its own path; A-vs-B and B-vs-A share one canonical; a description
never names a platform (the public view withholds some, contract/publication.yaml);
private pages are noindex.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "js" / "seo_pages.mjs"
PLATFORM = re.compile(r"\b(reddit|twitter|arxiv|hacker ?news|dev\.to|hugging ?face|github)\b", re.I)


@pytest.fixture(scope="module")
def out() -> dict:
    node = shutil.which("node")
    if node is None:
        # NOT A SKIP, as in test_every_leaf_reaches_the_grid: CI runs node.
        pytest.fail("node is required to run web/src/seo/pages.js")
    run = subprocess.run([node, str(PROBE)], capture_output=True, text=True, encoding="utf-8",
                         cwd=ROOT, check=False)
    if run.returncode != 0:
        pytest.fail(f"seo_pages.mjs failed:\n{run.stderr}")
    return json.loads(run.stdout)


def _heads(out):
    # `noindex` and `structured` hold other cases, not page heads.
    return {k: v for k, v in out.items()
            if isinstance(v, dict) and k not in ("noindex", "structured", "compare")}


def test_every_page_has_its_own_title(out):
    # Pairs that are the SAME page by design are left out: A-vs-B and B-vs-A,
    # a missing post (which falls back to the index head), and /reviews/models,
    # which is /reviews.
    titles = [h["title"] for k, h in _heads(out).items()
              if k not in ("compareBA", "postMissing", "hubDefault", "reportsModels",
                           "compareReadableBA") and h]
    assert all(titles)
    assert len(set(titles)) == len(titles)


def test_titles_and_descriptions_fit(out):
    for k, h in _heads(out).items():
        if not h:
            continue
        assert len(h["title"]) <= out["TITLE_MAX"], k
        if h.get("description"):
            assert len(h["description"]) <= out["DESCRIPTION_MAX"], k


def test_a_title_too_long_for_the_site_name_drops_it(out):
    assert "Model Information Board" not in out["longTitle"]
    assert out["job"]["title"].endswith("| Model Information Board")


def test_a_section_page_is_its_own_canonical(out):
    assert out["job"]["canonical"] == "/board/jobs/code-review"
    assert out["cap"]["canonical"] == "/board/capabilities/code-review"
    assert out["inSection"]["canonical"] == "/board/jobs/code-review/anthropic/claude-opus-5"
    assert out["model"]["canonical"] == "/models/anthropic/claude-opus-5"
    assert out["hub"]["canonical"] == "/board?tab=cap"
    assert out["hubDefault"]["canonical"] == "/board"


def test_a_comparison_has_one_canonical_whichever_order(out):
    assert out["compareAB"]["canonical"] == out["compareBA"]["canonical"] == "/compare?ids=a,b"
    assert out["compareOne"]["canonical"] == "/compare"


def test_a_description_never_names_a_platform(out):
    assert "Agents" in out["leaky"]["description"]
    for k, h in _heads(out).items():
        if h and h.get("description"):
            assert not PLATFORM.search(h["description"]), (k, h["description"])


def test_a_section_description_carries_its_definition(out):
    assert "Reviewing diffs for bugs" in out["job"]["description"]
    assert out["long"]["description"].endswith("…")


def test_no_head_for_an_unknown_section(out):
    assert out["unknownSeg"] is None


def test_a_post_reads_its_own_title_and_dek(out):
    assert out["post"]["title"].startswith("Moving to a new model")
    assert out["post"]["description"] == "A short dek."
    assert out["postNoDek"]["description"]
    assert out["postMissing"]["canonical"] == "/blogs"


def test_private_pages_are_noindex(out):
    assert out["login"]["noindex"] is True
    assert out["notFound"]["noindex"] is True
    assert out["notFound"]["title"].startswith("Page not found")


def test_a_page_is_noindex_unless_its_canonical_is_listed(out):
    n = out["noindex"]
    assert n["unknownList"] is True      # list not loaded / failed: never "index" (rule 6)
    assert n["onList"] is False
    assert n["offList"] is True
    assert n["askedFor"] is True         # a page's own noindex always wins
    assert n["noCanonical"] is False     # nothing to look up: index.html's robots stand
    assert n["noHead"] is False


# ── structured data (SEO items 6 and 11) ──────────────────────────────────


def test_breadcrumbs_are_absolute_and_ordered(out):
    c = out["structured"]["crumbs"]
    assert c["@type"] == "BreadcrumbList"
    items = c["itemListElement"]
    assert [i["position"] for i in items] == [1, 2, 3, 4]
    assert [i["name"] for i in items] == ["Board", "Jobs", "Code review", "Claude Opus 5"]
    assert items[-1]["item"] == "https://board.example/board/jobs/code-review/anthropic/claude-opus-5"


def test_no_structured_data_without_a_site(out):
    s = out["structured"]
    assert s["crumbsClosed"] is None
    assert s["closedAll"] == []
    assert s["crumbsTooShort"] is None   # one level is not a trail


def test_the_article_carries_only_what_the_post_has(out):
    a = out["structured"]["article"]
    assert len(a["headline"]) == 110
    assert a["datePublished"] == "2026-10-07T12:34:23+05:30"   # approval, not generation
    assert a["dateCreated"] == "2026-10-01T06:39:45+00:00"
    assert a["author"]["@type"] == "Organization"
    bare = out["structured"]["articleBare"]
    assert "datePublished" not in bare and "description" not in bare and "image" not in bare


def test_an_open_post_page_carries_breadcrumbs_and_an_article(out):
    assert out["structured"]["openPost"] == ["BreadcrumbList", "Article"]


def test_section_and_model_pages_carry_their_trail(out):
    s = out["structured"]
    assert [c["name"] for c in s["sectionCrumbs"]] == ["Board", "Capabilities", "Code review"]
    assert s["sectionCrumbs"][1]["path"] == "/board?tab=cap"
    assert [c["path"] for c in s["modelCrumbs"]] == ["/models", "/models/anthropic/claude-opus-5"]


def test_a_dated_page_says_when_it_last_changed(out):
    """dateModified from the freshness dates, on board and model pages - and only
    when the date exists, never the render time standing in for it."""
    s = out["structured"]
    assert s["pageDated"]["@type"] == "WebPage"
    assert s["pageDated"]["dateModified"] == "2026-10-06T13:00:39+05:30"
    assert s["pageDated"]["url"] == "https://board.example/board/jobs/code-review"
    assert s["pageUndated"] is None
    assert s["modelDated"]["dateModified"] == "2026-10-05T12:00:00+00:00"
    assert "WebPage" in s["inSectionDated"]


def test_reports_models_and_the_hub_are_one_page(out):
    """/reviews opens on the Models section, so /reviews/models names the hub as
    its canonical instead of competing with it (2026-10-20)."""
    assert out["reportsHub"]["canonical"] == "/reviews"
    assert out["reportsModels"]["canonical"] == "/reviews"
    assert out["reportsJobs"]["canonical"] == "/reviews/jobs"


def test_a_comparison_has_a_readable_path_and_one_canonical(out):
    """/compare/<a>-vs-<b> names the models the way people search them; either
    order is one canonical; internal ids keep the query form (2026-10-20)."""
    c = out["compare"]
    assert c["path"] == "/compare/grok-4.6-vs-gpt-6-sol"
    assert c["pathFrom"] == "/compare/grok-4.6-vs-gpt-6-sol?from=reports"
    assert c["pathInternal"] == "/compare?ids=mv_1%2Cmv_2"
    assert c["pathOne"] == "/compare?ids=x-ai%2Fgrok-4.6"
    assert c["canonAB"] == c["canonBA"] == "/compare/gpt-6-sol-vs-grok-4.6"
    heads = (out["compareReadableAB"], out["compareReadableBA"])
    assert [h["canonical"] for h in heads] == [c["canonAB"], c["canonAB"]]


def test_a_readable_comparison_resolves_back_to_its_models(out):
    c = out["compare"]
    assert c["parsed"] == ["grok-4.6", "gpt-6-sol"]
    assert c["resolved"] == {"ids": ["x-ai/grok-4.6", "openai/gpt-6-sol"], "unknown": []}
    # an unknown name, and a name two providers share, are not guessed
    assert c["unknown"] == {"ids": [], "unknown": ["grok-9", "twin"]}
    # the full id written with `--` names a shared name exactly
    assert c["fullId"] == {"ids": ["acme/twin"], "unknown": []}


def test_a_job_in_the_picker_is_a_page_of_its_own(out):
    """/best-ai-model/<job> (2026-10-21): its own canonical and a title that
    reads as the search does - "best AI model for coding agents" - with an
    acronym kept as written ("RAG", not "rAG")."""
    h = out["pickerJob"]
    assert h["canonical"] == "/best-ai-model/coding-agent"
    assert h["title"].startswith("Best AI model for coding agents")
    assert h["breadcrumbs"][-1] == {"name": "Coding agents", "path": "/best-ai-model/coding-agent"}
    assert out["pickerJobAcronym"]["title"].startswith("Best AI model for RAG:")


def test_a_tool_says_it_is_a_free_web_app_and_nothing_more(out):
    """The cost calculator, the pricing table, the picker and the bare
    comparison tool carry WebApplication markup (2026-10-21): their own name,
    address and description, free - and no rating or review count, which they
    do not have. A comparison of two named models is a page, not the tool."""
    s = out["structured"]
    app = next(x for x in s["tool"] if x["@type"] == "WebApplication")
    assert app["name"] == "LLM cost calculator & token counter"
    assert app["url"] == "https://board.example/token-counter"
    assert app["isAccessibleForFree"] is True and app["offers"]["price"] == "0"
    assert "aggregateRating" not in app and "review" not in app
    assert all("WebApplication" in types for types in s["toolTypes"])
    assert "WebApplication" in s["compareTool"] and "WebApplication" not in s["comparePair"]
    assert s["closedTool"] == []


def test_a_model_list_is_marked_up_in_the_pages_own_order(out):
    """ItemList (2026-10-21): the models the page shows, numbered in its order,
    with absolute links; an empty list writes no ItemList at all."""
    s = out["structured"]
    lst = next(x for x in s["typeList"] if x["@type"] == "ItemList")
    assert lst["numberOfItems"] == 2
    assert [(e["position"], e["name"], e["url"]) for e in lst["itemListElement"]] == [
        (1, "Flux 2", "https://board.example/ai-models/bfl/flux-2"),
        (2, "Nano Banana 2", "https://board.example/ai-models/google/nano-banana-2"),
    ]
    assert "BreadcrumbList" in [x["@type"] for x in s["typeList"]]
    assert "ItemList" not in s["emptyList"]
    assert s["reviewCrumbs"][0] == {"name": "AI model reviews", "path": "/reviews"}


def test_a_models_alternatives_are_a_page_of_their_own(out):
    """/alternatives/<model> (2026-10-21): "gpt-6 astra alternatives" is the
    search, so the title and canonical say it."""
    h = out["pickerAlternatives"]
    assert h["canonical"] == "/alternatives/gpt-6-astra"
    assert h["title"].startswith("GPT-6 Astra alternatives")
    assert h["breadcrumbs"][-1] == {"name": "GPT-6 Astra alternatives",
                                     "path": "/alternatives/gpt-6-astra"}
