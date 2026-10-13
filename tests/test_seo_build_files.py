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
    assert {"Disallow: /admin", "Disallow: /login", "Disallow: /compare"} <= set(robots)
    assert "Sitemap: https://board.example/sitemap.xml" in robots
    assert "Disallow: /" not in robots


def test_the_sitemap_is_valid_xml_with_structural_and_indexable_pages(out):
    root = ET.fromstring(out["sitemap"])
    locs = [u.find(f"{NS}loc").text for u in root.findall(f"{NS}url")]
    assert len(locs) == len(set(locs))                       # each once
    for p in out["structural"]:
        assert f"https://board.example{p}" in locs
    assert "https://board.example/board/jobs/code-review" in locs
    assert "https://board.example/models/anthropic/claude-opus-4.6" in locs
    assert "https://board.example/board?tab=cap&x=1" in locs   # escaped in XML, intact once parsed


def test_the_sitemap_never_lists_a_private_page_or_a_non_path(out):
    root = ET.fromstring(out["sitemap"])
    locs = [u.find(f"{NS}loc").text for u in root.findall(f"{NS}url")]
    assert not any(x.endswith(("/compare", "/admin", "/login")) for x in locs)
    assert not any("not-a-path" in x for x in locs)


def test_no_lastmod_is_invented(out):
    assert "lastmod" not in out["sitemap"]


def test_a_malformed_paths_file_raises(out):
    r = out["readPaths"]
    assert r["good"] == "ok"
    assert r["noDate"] != "ok" and r["noPaths"] != "ok" and r["notJson"] != "ok"
