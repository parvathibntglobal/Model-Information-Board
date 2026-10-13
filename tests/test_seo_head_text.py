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
            if isinstance(v, dict) and k not in ("noindex", "structured")}


def test_every_page_has_its_own_title(out):
    # Pairs that are the SAME page by design are left out: A-vs-B and B-vs-A,
    # and a missing post (which falls back to the index head).
    titles = [h["title"] for k, h in _heads(out).items()
              if k not in ("compareBA", "postMissing", "hubDefault") and h]
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
