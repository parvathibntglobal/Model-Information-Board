"""One measurement is one row, and every colour on it is a token that exists.

TWO DEFECTS A READER FOUND ON THE RENDERED PAGE, both of which passed the
suite, passed the linter and built clean.

1 · ONE PRICE, FOUR ROWS. DeepSeek V4 Flash, cost per token:

       output   $0.25/M                            10 reports
       output   $0.25 per million output tokens     3 reports
       output   $0.25/M output tokens               1 report
       output   $0.25                               stated and reported

   One price, one unit, one axis. `groupFigures` keyed on the VERBATIM
   string, so a writer's choice of abbreviation split a figure fifteen
   reports agree on into four findings - burying the corroboration, which is
   the exact defect that function was written to fix one level down.

2 · THE COLUMN WAS INVISIBLE. `What was measured` rendered with
   `color: var(--fg, #1f2328)`. There is no `--fg` in `tokens.css`, so every
   cell fell through to a light-theme fallback and printed near-black text on
   this board's near-black background (`--bg: #0C0C0E`). The markup was
   right, the class was right, the text was in the DOM, and nobody could read
   it.

   A `var()` fallback is not a safety net. It is the branch that runs when the
   name is wrong, and it makes the mistake silent.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "web" / "src" / "board" / "db.js"
VIEWS = ROOT / "web" / "src" / "board" / "views.js"
STYLES = ROOT / "web" / "src" / "styles"


def _css(name: str) -> str:
    return (STYLES / name).read_text(encoding="utf-8")


def _strip_css_comments(text: str) -> str:
    """Rules only. A comment EXPLAINING the bad token names must not fail the
    check that forbids them - the same mention-versus-use trap this repo has
    now written down four times, and the better the comment the likelier it
    is to trip a naive grep."""
    return re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)


#: ⚠ FIVE THAT ALREADY FAIL, NAMED SO THAT A SIXTH CANNOT ARRIVE QUIETLY.
#:
#: Found by this check on 2026-09-21, all in `app.css`, none introduced by the
#: change that prompted it. They are recorded rather than fixed because each
#: needs a look at what the rule was trying to do - `--line` most likely wanted
#: `--border` and `--text-1` wanted `--text`, but "most likely" is not a thing
#: to guess at in a stylesheet that renders evidence.
#:
#: This is `tests/test_cli_write_gate.py`'s `READ_ONLY` idiom: an explicit set,
#: so retiring one is a visible diff and adding one is a failure.
#: ⚠ EMPTY, AND IT HELD SEVEN. Found when a reader asked why a panel looked
#: crowded and the file turned out to be setting
#: `borderLeft: '2px solid var(--line)'` - a token nothing defines, so the
#: declaration was dropped and the border never drew.
#:
#: All seven are fixed. Kept as an empty set rather than deleted, because the
#: check below is what makes an eighth impossible to add quietly, and a reader
#: wondering whether this was ever a problem should find the answer here.
KNOWN_UNDEFINED_INLINE: set[str] = set()

KNOWN_UNDEFINED = {
    "app.css": {"--adm-nav", "--line", "--r2", "--t-fast", "--text-1"},
}


class TestEveryColourNamesATokenThatExists:
    def test_no_rule_uses_an_undefined_custom_property(self):
        # ⚠ NOT LINE-ANCHORED. The first version of this regex was
        #   `^\s*(--x)\s*:` and `tokens.css` declares four spacing steps on one
        #   line - `--s1: 8px;  --s2: 16px; --s3: 24px; --s4: 32px;` - so three
        #   of every four came back undefined and the check reported ten
        #   defects that were not there. A check whose failures are mostly
        #   false gets switched off, which is worse than not having it.
        defined: set[str] = set()
        for f in sorted(STYLES.glob("*.css")):
            defined |= set(re.findall(
                r"(--[a-z0-9-]+)\s*:", _strip_css_comments(f.read_text(encoding="utf-8"))
            ))
        assert "--text-2" in defined and "--s4" in defined, (
            "the definition scan is not finding tokens that plainly exist"
        )

        missing: dict[str, set[str]] = {}
        for f in sorted(STYLES.glob("*.css")):
            rules = _strip_css_comments(f.read_text(encoding="utf-8"))
            used = {u for u in re.findall(r"var\(\s*(--[a-z0-9-]+)", rules)}
            gap = used - defined - KNOWN_UNDEFINED.get(f.name, set())
            if gap:
                missing[f.name] = gap

        assert not missing, (
            "these rules name a custom property nothing defines, so each falls "
            f"through to its literal fallback: {missing}. On a dark board a "
            "light-theme fallback is invisible text - which is how `What was "
            "measured` shipped unreadable."
        )

    def test_no_inline_style_uses_an_undefined_custom_property(self):
        """⚠ THE GAP THAT LET SEVEN THROUGH. The check above reads
        stylesheets. Components set colours inline too - `style={{ color:
        'var(--text-1)' }}` - and nothing looked there, so `--text-1` reached
        nine files, `--line` three and `--r2` three. An invalid property is
        dropped, so text meant to be bright simply stays dim: plausible, not
        broken, and invisible to the linter and the build.

        Recorded rather than swept, because each needs a look at what the rule
        was for. `--text-1` almost certainly wanted `--text` - the scale is
        `--text`, `--text-2`, `--text-3` and somebody read it as 1/2/3 - but
        "almost certainly" is the guess this repository has just written down
        that it does not make in a stylesheet.
        """
        src = ROOT / "web" / "src"
        defined: set[str] = set()
        for f in sorted(STYLES.glob("*.css")):
            defined |= set(re.findall(
                r"(--[a-z0-9-]+)\s*:", _strip_css_comments(f.read_text(encoding="utf-8"))
            ))

        found: dict[str, set[str]] = {}
        for f in sorted([*src.rglob("*.jsx"), *src.rglob("*.js")]):
            for used in set(re.findall(r"var\(\s*(--[a-z0-9-]+)", f.read_text(encoding="utf-8"))):
                if used not in defined:
                    found.setdefault(used, set()).add(f.relative_to(src).as_posix())

        new = {k: sorted(v) for k, v in found.items() if k not in KNOWN_UNDEFINED_INLINE}
        assert not new, (
            "these inline styles name a custom property nothing defines, so "
            f"the declaration is dropped and the element keeps what it "
            f"inherited: {new}"
        )

    def test_the_recorded_debt_is_still_real(self):
        """A known-failure list that has quietly become correct is a lie in the
        other direction, and it stops the next reader trusting the set."""
        defined: set[str] = set()
        for f in sorted(STYLES.glob("*.css")):
            defined |= set(re.findall(
                r"(--[a-z0-9-]+)\s*:", _strip_css_comments(f.read_text(encoding="utf-8"))
            ))
        for name, names in KNOWN_UNDEFINED.items():
            fixed = {n for n in names if n in defined}
            assert not fixed, (
                f"{fixed} in {name} are defined now; take them out of "
                "KNOWN_UNDEFINED so the set keeps meaning what it says"
            )

    def test_the_tokens_this_board_actually_has_are_the_dark_ones(self):
        # Pins the premise of the test above. If the palette ever flips, the
        # fallbacks that were wrong become right and this file should be
        # re-read rather than silently keep passing.
        tokens = _css("tokens.css")
        assert "--bg:" in tokens and "#0C0C0E" in tokens
        assert "--text:" in tokens and "#FFFFFF" in tokens


class TestOneMeasurementIsOneRow:
    """`canonicalFigure` - the key that stopped four wordings being four
    findings."""

    def test_it_exists_and_is_used_as_the_group_key(self):
        js = DB.read_text(encoding="utf-8")
        assert "export function canonicalFigure(value)" in js
        assert "const canon = canonicalFigure(f.value)" in js
        assert "const figureKey = canon === null ? 'v:' + f.value : 'n:' + canon" in js

    def test_more_than_one_number_refuses_to_canonicalise(self):
        """`$10/1M input and $50/1M output` and `$0.66 off-peak or $1.32 at
        peak` are not single figures, and merging either would invent a price
        nobody quoted. Refusing is always available and is what makes the
        merge safe."""
        js = DB.read_text(encoding="utf-8")
        fn = js[js.index("export function canonicalFigure(value)"):]
        fn = fn[:fn.index(chr(10) + "}")]
        assert "if (nums.length !== 1) return null" in fn

    def test_the_unit_stays_in_the_key(self):
        # So `8.7c per task` never meets `$8.70`. The magnitude alone is not
        # the figure.
        js = DB.read_text(encoding="utf-8")
        assert "const key = [modelKey || model, figureKey, unit].join(" in js

    def test_the_row_shows_a_wording_that_was_actually_written(self):
        """The page promises the figure verbatim. Where several texts wrote it
        differently the row shows the one most of them used - never a string
        reformatted into a house style, which is not a quote of anything."""
        js = DB.read_text(encoding="utf-8")
        assert "const spelled = [...g.spellings.entries()].sort((a, b) => b[1] - a[1]);" in js
        assert "value: spelled.length ? spelled[0][0] : g.value," in js

    def test_the_merge_is_declared_on_the_row(self):
        # Silently collapsing four wordings would look like a figure that had
        # been tidied up. The count of the others is what says it was not.
        js = VIEWS.read_text(encoding="utf-8")
        assert "g.otherSpellings" in js
        assert "same figure" in js


class TestTheEvidenceOutranksTheNavigation:
    """The quote is what makes a figure checkable; `open the source` is a
    link. They were rendered the other way round."""

    def test_the_quote_is_emitted_before_the_link(self):
        js = VIEWS.read_text(encoding="utf-8")
        fn = js[js.index("function figureRows(groups){"):]
        fn = fn[:fn.index(chr(10) + "}")]
        assert "return tag + q + link;" in fn, (
            "the link is still above the quote; the brightest thing in the "
            "cell would be the least informative"
        )

    def test_the_quote_is_the_readable_colour_and_the_link_is_dimmed(self):
        css = _strip_css_comments(_css("board.css"))
        quote = css[css.index(".bv .figsrc .figq{"):]
        quote = quote[:quote.index("}")]
        assert "color:var(--text)" in quote

        link = css[css.index(".bv .figsrc .srclink{"):]
        link = link[:link.index("}")]
        assert "color:var(--text-3)" in link
