"""The token counter (web/src/routes/TokenCounter.jsx), 2026-10-12.

Its arithmetic is web/src/tokens/cost.js, rendered through node
(tests/js/token_cost.mjs) like the other frontend probes. The tokenizer itself
is a frontend dependency CI does not install, so it is pinned by STRUCTURE:
loaded lazily, never in the first download, and the page sends no text.

What is pinned: a missing rate is listed apart, never priced at $0 (rule 6); a
real charge never prints as "$0"; "exact" only where the library names the
model's encoding (unknown stays an estimate, rule 12); name order unless the
reader asks for cost order.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "js" / "token_cost.mjs"
WEB = ROOT / "web" / "src"


@pytest.fixture(scope="module")
def out() -> dict:
    node = shutil.which("node")
    if node is None:
        # NOT A SKIP, as in test_seo_head_text: CI runs node.
        pytest.fail("node is required to run web/src/tokens/cost.js")
    run = subprocess.run([node, str(PROBE)], capture_output=True, text=True, encoding="utf-8",
                         cwd=ROOT, check=False)
    if run.returncode != 0:
        pytest.fail(f"token_cost.mjs failed:\n{run.stderr}")
    return json.loads(run.stdout)


def _names(rows):
    return [r["name"] for r in rows]


def test_a_cost_is_tokens_times_the_rate_per_million(out):
    c = out["costOf"]
    assert c["basic"] == pytest.approx(0.51)
    assert c["one"] == pytest.approx(0.00051)
    assert c["freeRate"] == 0


def test_an_unknown_rate_or_count_is_no_cost_not_zero(out):
    c = out["costOf"]
    assert c["nullRate"] is None
    assert c["nullTokens"] is None
    assert all(r["one"] is None and r["many"] is None for r in out["noTokenizer"])


def test_a_real_charge_never_prints_as_zero(out):
    f = out["fmtUsd"]
    assert f["nul"] == "—"
    assert f["zero"] == "$0"
    assert f["tiny"] == "<$0.000001"
    assert f["small"] == "$0.000510"
    assert f["sub"] == "$0.510"
    assert f["big"] == "$1,234.50"


def test_a_model_without_a_rate_is_listed_apart_not_dropped(out):
    i = out["input"]
    assert "Auto Router" in _names(i["unpriced"])
    assert "Auto Router" not in _names(i["priced"])
    assert "Free Model" in _names(i["priced"])          # 0 is a rate; null is not
    # per direction: Claude X has an input rate and no output rate
    assert "Claude X" in _names(i["priced"])
    assert "Claude X" in _names(out["output"]["unpriced"])


def test_exact_only_where_the_library_names_the_encoding(out):
    by = {r["name"]: r["exactness"] for r in out["input"]["priced"]}
    assert by["GPT-4o"] == "exact"
    assert by["GPT-4"] == "estimate"       # listed, different encoding
    assert by["GPT-9"] == "estimate"       # not listed: unknown is never exact
    assert by["Claude X"] == "estimate"
    assert by["Mirror 4o"] == "estimate"   # same name, not the provider's own model


def test_name_order_unless_the_reader_asks_for_cost(out):
    names = _names(out["input"]["priced"])
    assert names == sorted(names, key=str.lower)
    assert out["byCost"][0] == "Free Model"
    assert out["byCost"][-1] == "GPT-4"


def test_search_ignores_spacing(out):
    assert set(out["search"]) == {"GPT-4o", "GPT-4", "Mirror 4o"}


def test_words_and_lines(out):
    assert out["words"] == [0, 3, 0, 2]


# ── structure: the tokenizer is lazy, and the page sends no text ──────────


def test_the_tokenizer_is_only_a_dynamic_import():
    src = (WEB / "tokens" / "tokenizer.js").read_text(encoding="utf-8")
    assert "import('js-tiktoken/lite')" in src
    assert "import('js-tiktoken/ranks/o200k_base')" in src
    for f in [*WEB.rglob("*.js"), *WEB.rglob("*.jsx")]:
        text = f.read_text(encoding="utf-8")
        eager = re.search(r"^import .* from 'js-tiktoken", text, re.M)
        assert not eager, f"{f} imports the tokenizer eagerly"


def test_the_page_sends_no_text():
    page = (WEB / "routes" / "TokenCounter.jsx").read_text(encoding="utf-8")
    assert "fetch(" not in page.replace("fetchAll(", "")
    assert "request(" not in page
    # the one call it makes is the roster
    assert re.findall(r"\b(list[A-Z]\w*)\(", page) == ["listRegistry"]


def test_the_tools_live_on_the_public_pages_not_the_signed_in_list():
    """Since 2026-10-21 the cost calculator and the pricing table are reached
    from the public Tools page, menu and footer; the signed-in models list no
    longer carries its own buttons for them."""
    models = (WEB / "routes" / "Models.jsx").read_text(encoding="utf-8")
    assert 'to="/token-counter"' not in models and 'to="/ai-model-pricing"' not in models
    for f in ("routes/Tools.jsx", "components/Nav.jsx", "components/Footer.jsx"):
        src = (WEB / f).read_text(encoding="utf-8")
        assert "'/token-counter'" in src and "'/ai-model-pricing'" in src, f


# ── will it fit, and a workload per month ─────────────────────────────────


def test_fit_against_the_context_window_and_the_output_limit(out):
    f = out["fit"]
    assert f["fits"] == {"state": "fits", "limit": 100, "room": 49}
    assert f["over"] == {"state": "over", "limit": 100, "by": 1}
    assert f["outOver"]["state"] == "over"
    assert f["notCounted"] is None


def test_an_unpublished_limit_is_unknown_never_fits(out):
    assert out["fit"]["unknown"] == {"state": "unknown", "limit": None}


def test_a_workload_is_priced_per_call_day_and_month(out):
    w = out["workload"]["plain"]
    assert w["perCall"] == pytest.approx((1000 * 2.5 + 100 * 10) / 1e6)
    assert w["perDay"] == pytest.approx(w["perCall"] * 10)
    assert w["perMonth"] == pytest.approx(w["perDay"] * 30)
    assert w["cache"] == "off"


def test_the_cached_share_uses_the_cached_rate(out):
    w = out["workload"]["cached"]
    assert w["perCall"] == pytest.approx(1000 * (0.5 * 2.5 + 0.5 * 1.25) / 1e6)
    assert w["cache"] == "applied"


def test_no_cached_rate_is_priced_uncached_and_says_so(out):
    w = out["workload"]["noCacheRate"]
    assert w["cache"] == "none"
    assert w["perCall"] == pytest.approx(1000 * 1 / 1e6)


def test_a_workload_needing_a_missing_rate_is_unpriced(out):
    w = out["workload"]
    assert w["needsOut"] is None          # Claude X has no output rate
    assert w["inOnly"] is not None        # ...and needs none when nothing comes out
    rows = w["rows"]
    assert "Auto Router" in _names(rows["unpriced"])
    assert "Claude X" in _names(rows["unpriced"])


def test_workload_fit_counts_input_and_output_together(out):
    by = {r["name"]: r["fit"] for r in out["workload"]["rows"]["priced"]}
    assert by["GPT-4o"] == "fits"          # 50 + 30 <= 100, 30 <= 40
    assert by["GPT-4"] == "unknown"        # publishes no limit
