"""Four small pictures from one image call; the first opens the post.

Team ask, 2026-10-14: smaller pictures, more of them for the same cost, and
every post opening on one. A picture is billed per call, not per pixel (19
calls on 2026-10-13: $0.0387-$0.0390 each), so one call draws four scenes as a
16:9 2x2 grid and code cuts the panels out. The two fixtures are the real
probe draws of that day. No model is called here.
"""
import base64
import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import generate_sample_blogs as g  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
GROUND = (32, 34, 52)


def grid(size=(1344, 768), panel=(0.8, 0.8), drop=None):
    """A synthetic 2x2 picture: four distinct panels on a flat ground, with a
    faint divider cross at the centre like the model draws."""
    w, h = size
    img = Image.new("RGB", size, GROUND)
    d = ImageDraw.Draw(img)
    for k, (x0, y0) in enumerate([(0, 0), (w // 2, 0), (0, h // 2), (w // 2, h // 2)]):
        if k == drop:
            continue
        pw, ph = round(w / 2 * panel[0]), round(h / 2 * panel[1])
        ox, oy = x0 + (w // 2 - pw) // 2, y0 + (h // 2 - ph) // 2
        d.rectangle((ox, oy, ox + pw, oy + ph), fill=(60 + 40 * k, 80, 160))
    d.line((w // 2, 0, w // 2, h), fill=(70, 72, 90), width=2)
    d.line((0, h // 2, w, h // 2), fill=(70, 72, 90), width=2)
    return img


@pytest.mark.parametrize("name", ["blog_grid_probe_2026-10-14.jpg",
                                  "blog_grid_probe2_2026-10-14.jpg"])
def test_both_real_draws_cut_into_four_wide_pictures(name):
    cut = g.split_panels(Image.open(FIX / name).convert("RGB"))
    assert [how for _p, how in cut] == ["trimmed"] * 4
    for p, _how in cut:
        assert 300 <= p.width <= 672 and 180 <= p.height <= 384 and p.width > p.height


def test_a_synthetic_grid_is_cut_to_its_panels_not_its_quarters():
    cut = g.split_panels(grid())
    assert [abs(p.width - 538) <= 4 and abs(p.height - 307) <= 4 for p, _ in cut] == [True] * 4


# A PAID PICTURE IS NEVER THROWN AWAY (2026-10-14). The cutter used to raise
# on each of these, and refused 5 of 10 real grids that day. Now each quarter
# whose edges are not found cleanly is cut whole, and says so.

def test_one_scene_across_the_canvas_is_cut_into_quarters_and_said():
    img = Image.new("RGB", (1344, 768), GROUND)
    ImageDraw.Draw(img).rectangle((60, 40, 1284, 728), fill=(90, 100, 170))
    cut = g.split_panels(img)
    assert [how for _p, how in cut] == ["quarter"] * 4
    assert all(p.width < 672 and p.height < 384 for p, _ in cut)


def test_an_empty_quarter_leaves_only_that_picture_out():
    cut = g.split_panels(grid(drop=2))
    assert [how for _p, how in cut] == ["trimmed", "trimmed", "empty", "trimmed"]
    assert cut[2][0] is None


def test_a_panel_too_small_to_trust_is_cut_as_its_quarter():
    assert [how for _p, how in g.split_panels(grid(panel=(0.3, 0.3)))] == ["quarter"] * 4


def test_a_stray_line_at_the_edge_is_not_taken_for_the_panel():
    img = grid()
    ImageDraw.Draw(img).line((0, 1, 1344, 1), fill=(200, 200, 220), width=2)
    assert all(p.height < 340 for p, _ in g.split_panels(img))


# ── one call, one ledger row, four pictures, the first a cover ───────────────

ILLS = [{"section": n, "scene": f"scene {n}", "alt": f"alt {n}", "caption": f"cap {n}"}
        for n in (0, 1, 2, 3)]
POST = {"key": "field-report-x"}
STARTED = "2026-10-14T05:00:00+00:00"


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    from judge import spend_ledger

    path = tmp_path / "ledger.jsonl"
    monkeypatch.setenv(spend_ledger.LEDGER_PATH_ENV, str(path))
    monkeypatch.setattr(g, "env", lambda: {})
    return path


def rows(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_four_pictures_cost_one_call_recorded_once(ledger, monkeypatch, tmp_path):
    monkeypatch.setattr(g, "RUNS", tmp_path / "runs")
    usage = {"prompt_tokens": 228, "completion_tokens": 1290, "cost": 0.0388}
    monkeypatch.setattr(g, "draw_grid", lambda *a: (grid(), usage))
    pics, calls = g.illustrate(POST, {"illustrations": ILLS}, "k", "b", STARTED)
    assert len(pics) == 4 and [p["cover"] for p in pics] == [True, False, False, False]
    assert calls == [{"model": g.IMAGE_MODEL, "usd": 0.0388}]  # once, not once per picture
    [row] = rows(ledger)
    assert row["usd"] == pytest.approx(0.0388) and row["run_id"].endswith("#grid")
    img = Image.open(io.BytesIO(base64.b64decode(pics[1]["src"].split(",", 1)[1])))
    assert img.width < 700  # small: a panel, not the whole canvas


def test_a_draw_that_is_not_a_clean_grid_still_gives_its_pictures(ledger, monkeypatch, tmp_path):
    one_scene = Image.new("RGB", (1344, 768), GROUND)
    ImageDraw.Draw(one_scene).rectangle((60, 40, 1284, 728), fill=(90, 100, 170))
    monkeypatch.setattr(g, "draw_grid", lambda *a: (one_scene, {"cost": 0.0388}))
    monkeypatch.setattr(g, "RUNS", tmp_path / "runs")
    pics, calls = g.illustrate(POST, {"illustrations": ILLS}, "k", "b", STARTED)
    assert [p["cut"] for p in pics] == ["quarter"] * 4 and calls[0]["usd"] == 0.0388
    assert len(rows(ledger)) == 1


def test_every_paid_grid_is_saved_so_it_can_be_cut_again(ledger, monkeypatch, tmp_path):
    monkeypatch.setattr(g, "draw_grid", lambda *a: (grid(), {"cost": 0.0388}))
    monkeypatch.setattr(g, "RUNS", tmp_path / "runs")
    g.illustrate(POST, {"illustrations": ILLS}, "k", "b", STARTED)
    [saved] = (tmp_path / "runs" / POST["key"]).glob("grid-*.jpg")
    assert Image.open(saved).size == (1344, 768)


def test_no_picture_back_means_no_row_and_no_cost(ledger, monkeypatch):
    def none(*a):
        raise g.BuildError("the image model returned no image")
    monkeypatch.setattr(g, "draw_grid", none)
    assert g.illustrate(POST, {"illustrations": ILLS}, "k", "b", STARTED) == ([], [])
    assert not ledger.exists()
