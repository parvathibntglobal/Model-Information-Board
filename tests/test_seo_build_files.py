"""robots.txt and sitemap.xml (web/seo-build.js) - SEO items 8 and 9, 2026-10-09.

What is pinned:
  1. CLOSED BY DEFAULT, in both places at once: every closed build writes
     `Disallow: /`, and web/index.html ships `noindex, nofollow`. Opening one
     without the other would either crawl pages told not to index, or index
     pages crawlers may not reach.
  2. Open needs BOTH `SITE_URL` and `PUBLIC_SITE=1` (review of #508, item 3).
  3. The sitemap lists the structural pages plus the indexable paths, once
     each, never a private page, with the URLs escaped as XML.
  4. The paths file is validated: a malformed one raises, so an open build
     cannot quietly ship a sitemap with only the structural pages (rule 12).

Rendered through node (tests/js/seo_build.mjs), as the other frontend tests do.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "js" / "seo_build.mjs"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


@pytest.fixture(scope="module")
def out() -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is required to run web/seo-build.js")
    run = subprocess.run([node, str(PROBE)], capture_output=True, text=True, encoding="utf-8",
                         cwd=ROOT, check=False)
    if run.returncode != 0:
        pytest.fail(f"seo_build.mjs failed:\n{run.stderr}")
    return json.loads(run.stdout)


def test_closed_is_closed_in_both_places(out):
    assert out["robotsClosed"] == "User-agent: *\nDisallow: /\n"
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert 'name="robots" content="noindex, nofollow"' in html


def test_open_needs_both_keys(out):
    s = out["sites"]
    assert not s["none"]["open"] and not s["urlOnly"]["open"] and not s["flagOnly"]["open"]
    assert s["both"] == {"site": "https://board.example", "open": True}


def test_open_robots_disallows_private_pages_and_names_the_sitemap(out):
    robots = out["robotsOpen"].splitlines()
    assert {"Disallow: /admin", "Disallow: /login", "Disallow: /board", "Disallow: /models",
            "Disallow: /seo-keywords"} <= set(robots)
    # Compare is a public tool since 2026-10-20: crawlable, noindex per comparison
    assert "Disallow: /compare" not in robots
    assert "Sitemap: https://board.example/sitemap.xml" in robots
    assert "Disallow: /" not in robots


def test_the_sitemap_is_valid_xml_with_structural_and_indexable_pages(out):
    root = ET.fromstring(out["sitemap"])
    locs = [u.find(f"{NS}loc").text for u in root.findall(f"{NS}url")]
    assert len(locs) == len(set(locs))                       # each once
    for p in out["structural"]:
        assert f"https://board.example{p}" in locs
    assert "https://board.example/reviews/jobs/code-review" in locs
    assert "https://board.example/ai-models/anthropic/claude-opus-4.6" in locs
    # escaped in XML, intact once parsed
    assert "https://board.example/ai-models?type=text&x=1" in locs
    assert "https://board.example/compare" in locs


def test_the_sitemap_never_lists_a_private_page_or_a_non_path(out):
    root = ET.fromstring(out["sitemap"])
    locs = [u.find(f"{NS}loc").text for u in root.findall(f"{NS}url")]
    # the signed-in pages, at any depth, never reach the sitemap
    assert not any(x.endswith(("/admin", "/login", "/seo-keywords")) for x in locs)
    paths = [x.replace("https://board.example", "", 1) for x in locs]
    for q in ("/board", "/models"):
        assert not any(p == q or p.startswith((q + "/", q + "?")) for p in paths)
    assert not any("not-a-path" in x for x in locs)


def test_no_lastmod_is_invented(out):
    assert "lastmod" not in out["sitemap"]


def test_a_malformed_paths_file_raises(out):
    r = out["readPaths"]
    assert r["good"] == "ok"
    assert r["noDate"] != "ok" and r["noPaths"] != "ok" and r["notJson"] != "ok"


def test_a_real_date_becomes_lastmod_and_nothing_else_does(out):
    """`lastmod` from judge/seo.py's dates, as a plain day - and only for a path
    that has one. A malformed value and an undated path get none (no build
    time standing in for a date nobody recorded)."""
    xml = out["sitemapDated"]
    dated = "<loc>https://board.example/reviews/jobs/code-review</loc><lastmod>2026-10-06</lastmod>"
    assert dated in xml
    assert "<loc>https://board.example/ai-models/acme/model-t</loc></url>" in xml
    assert "<loc>https://board.example/blogs</loc></url>" in xml
    assert xml.count("<lastmod>") == 1


def test_pre_rendering_saves_the_sitemap_pages_only(out):
    """The pre-render saves what the sitemap lists: never a private path, never
    a query-string or fragment address (one file with parameters), each once."""
    paths = out["prerenderPaths"]
    assert "/reviews/jobs/code-review" in paths and "/ai-models/acme/model-t" in paths
    assert paths.count("/reviews/jobs/code-review") == 1
    assert set(out["structural"]) <= set(paths)
    assert not [p for p in paths if "?" in p or "#" in p]
    assert not [p for p in paths if p.startswith(("/board", "/models", "/admin", "/login"))]


def test_a_pre_rendered_page_is_saved_as_its_path_dot_html(out):
    """`<path>.html`, not `<path>/index.html` (nginx would redirect `/reviews`
    to `/reviews/`); `/` is index.html; a path that could leave dist/ or is not
    a valid file name is refused."""
    files = out["prerenderFiles"]
    assert files["/"] == "index.html"
    assert files["/reviews/jobs"] == "reviews/jobs.html"
    assert files["/ai-models/openai/gpt-6-sol"] == "ai-models/openai/gpt-6-sol.html"
    assert files["/glossary/gpt-5.5"] == "glossary/gpt-5.5.html"
    for bad in ("/a/../b", "/a%2F..%2Fb", "/x/", "/a:b", "/%E0%A4", "/a%5Cb", "/a%00b"):
        assert files[bad] is None, bad


def test_the_shell_head_cannot_close_its_own_script(out):
    """The shell's head is carried as JSON in a <script>; a `</script>` in a
    title must not end it early."""
    s = out["shellScript"]
    assert s.startswith('<script type="application/json" id="shell-head">')
    assert s.count("</script>") == 1 and "\u003c/script>" in s
