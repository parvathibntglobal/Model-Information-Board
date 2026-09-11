"""Every text colour must be readable on every surface it can land on.

WHY THIS IS A TEST AND NOT A REVIEW NOTE. `--text-3` was `#71717A` and failed
on ALL FIVE backgrounds this palette defines — 4.04:1 on `--bg` down to 3.24:1
on `--surface-3`, against a 4.5:1 minimum for body text. It was used 43 times
across `app.css` and `board.css`: evidence citations, meta lines, table
headers, timestamps, the breadcrumb. Nobody chose an unreadable colour; one
token drifted and every surface using it inherited the problem.

A ratio is arithmetic over two hex values, so it can be checked rather than
argued about. This computes it the way WCAG defines it — sRGB relative
luminance, `(L1 + 0.05) / (L2 + 0.05)` — and fails with the numbers.

OPACITY IS CHECKED TOO, because it multiplies against the token and is
invisible in a colour picker. `--text-3` at `opacity: .55` on the hero computed
to `#444449` — 2.02:1, the worst on the site — and neither the colour nor the
opacity looks wrong on its own.

SIZE IS DELIBERATELY NOT CHECKED HERE. It is a real legibility question and a
separate one; this file is about colour, and mixing them would make a contrast
failure and a typography preference fail the same test.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STYLES = ROOT / "web" / "src" / "styles"
TOKENS = STYLES / "tokens.css"

#: WCAG 2.1 AA for body text. Large text (>=24px, or >=18.66px bold) may use
#: 3:1, but nothing in this palette is only ever used large, so the stricter
#: bar is the honest one to hold.
MINIMUM = 4.5

#: Every colour text is painted in.
TEXT_TOKENS = ("text", "text-2", "text-3", "pass", "warn", "fail", "info")
#: Every background text can land on.
SURFACE_TOKENS = ("bg", "bg-elev", "surface", "surface-2", "surface-3")


def _token(name: str) -> str:
    css = TOKENS.read_text(encoding="utf-8")
    m = re.search(rf"--{re.escape(name)}:\s*(#[0-9A-Fa-f]{{6}})", css)
    if not m:
        raise AssertionError(f"--{name} is not defined in tokens.css")
    return m.group(1)


def _luminance(hex_colour: str) -> float:
    parts = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in parts]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def test_the_formula_matches_known_values():
    """A checker nobody has checked is not a checker."""
    assert contrast("#FFFFFF", "#000000") == pytest.approx(21.0, abs=0.01)
    assert contrast("#FFFFFF", "#FFFFFF") == pytest.approx(1.0, abs=0.01)


@pytest.mark.parametrize("text", TEXT_TOKENS)
@pytest.mark.parametrize("surface", SURFACE_TOKENS)
def test_every_text_colour_is_readable_on_every_surface(text, surface):
    ratio = contrast(_token(text), _token(surface))
    assert ratio >= MINIMUM, (
        f"--{text} ({_token(text)}) on --{surface} ({_token(surface)}) is "
        f"{ratio:.2f}:1, below the {MINIMUM}:1 minimum for body text"
    )


def test_the_three_text_tiers_stay_distinguishable():
    """Otherwise the hierarchy collapses and a third tier earns nothing.

    Lifting `--text-3` until it passes is easy; lifting it until it is
    `--text-2` fixes contrast by deleting the distinction the token exists for.
    """
    assert contrast(_token("text"), _token("text-2")) > 1.5
    assert contrast(_token("text-2"), _token("text-3")) > 1.2


class TestNothingDimsTextTwice:
    def test_the_hero_hint_does_not_stack_opacity_on_the_dimmest_token(self):
        # --text-3 at .55 computed to #444449 — 2.02:1, and the opacity is
        # invisible in a colour picker.
        css = (STYLES / "app.css").read_text(encoding="utf-8")
        block = css[css.index(".hero-hint{"):]
        block = block[: block.index("}")]
        # COMMENTS STRIPPED FIRST. The rule's own comment explains why the
        # opacity was removed, and a check that cannot tell a mention from a
        # declaration fails on its own documentation - the fourth time that
        # has caught me in this codebase.
        block = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
        assert "opacity" not in block, (
            "the token already carries the dimming; a second one on top is how "
            "text becomes unreadable without anybody choosing an unreadable colour"
        )

    def test_no_rule_combines_text_3_with_an_opacity_below_one(self):
        for css_file in STYLES.glob("*.css"):
            css = css_file.read_text(encoding="utf-8")
            for block in re.findall(r"\{[^{}]*\}", css):
                if "var(--text-3)" in block and re.search(r"opacity:\s*0?\.\d", block):
                    raise AssertionError(
                        f"{css_file.name}: a rule dims --text-3 with opacity as "
                        f"well: {block.strip()[:120]}"
                    )
