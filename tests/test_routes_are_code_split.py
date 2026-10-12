"""Route-level code splitting (SEO item 10, 2026-10-09).

The whole app was one 544.6 kB script (159.3 kB gzipped) every visitor fetched
before the first paint, the admin console included. After splitting, the first
download was 300.4 kB (96.9 kB gzipped) and each other page is its own chunk -
measured with `vite build` on 2026-10-09; the figures are a record, recount
with a build (rule 11).

A size budget would need a build, and CI installs no frontend dependencies (it
lints with `npx oxlint` only), so this pins the STRUCTURE that produces the
split instead - the way the repo's other routing tests pin App.jsx.
"""
from __future__ import annotations

import re
from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "web" / "src" / "App.jsx").read_text(encoding="utf-8")

#: The front door: what a visitor sees first, kept in the first download.
EAGER = ("Landing", "Login")
#: Every other page: fetched on first visit. Admin carries the big panels.
LAZY = ("Board", "Blogs", "ModelDetail", "Models", "Compare", "Admin", "BlogLogs")


def test_the_front_door_is_in_the_first_download():
    for name in EAGER:
        assert re.search(rf"^import {name} from './routes/{name}'$", APP, re.M), name


def test_every_other_page_is_its_own_chunk():
    for name in LAZY:
        assert f"const {name} = page(() => import('./routes/{name}'))" in APP, name
        assert not re.search(rf"^import {name} from ", APP, re.M), f"{name} is imported eagerly"


def test_the_routes_wait_for_their_chunk():
    assert "<Suspense fallback={PAGE_LOADING}>" in APP


def test_a_stale_chunk_reloads_once_and_then_fails_loudly():
    # After a deploy an open tab names chunks that no longer exist. One reload
    # picks up the new build; a second failure is thrown, not swallowed (rule 12).
    assert "sessionStorage.getItem('chunk-reload') === '1'" in APP
    assert "window.location.reload()" in APP
    assert "throw err" in APP
