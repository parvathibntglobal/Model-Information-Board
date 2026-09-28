"""Every `className` the app uses is a class some stylesheet defines.

⚠ RULE 12, AND IT HAS NOW SHIPPED TWICE.

`className="input"` appeared exactly once in the tree — the board review's
"merge into slug…" box — and **no `.input` rule was ever written**. The
element took the browser default white background while `app.css:16` handed
it `color:inherit` from this board's white text. **White on white: a reviewer
could not see what they were typing**, and nothing else about the control
looked wrong.

The same week, `What was measured` shipped unreadable because it was styled
`var(--fg, #1f2328)` and there is no `--fg` — a light-theme fallback on a
`#0C0C0E` board. Different mechanism, same shape: **the markup names
something that is not there, and the result is plausible rather than
broken.**

A class that does not exist cannot warn you. The linter does not know about
CSS, the build does not resolve class names, and a screenshot review catches
it only if somebody looks at that one control.

⚠ WHY THIS IS A TEST AND THE TOKEN CHECK IN
  `test_a_figure_is_one_measurement.py` IS TOO, RATHER THAN ONE FILE. That one
  asks whether a `var(--x)` names a token that exists. This asks whether a
  `className` names a rule that exists. They fail on different mistakes and a
  reader hitting either wants the specific sentence, not a shared one.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "web" / "src"
STYLES = SRC / "styles"

#: Classes that are deliberately not in a stylesheet.
#:
#: Each needs a reason, and "it looked unused" is not one — this is the
#: `READ_ONLY` idiom from `tests/test_cli_write_gate.py`, so adding a name
#: here is a visible diff somebody has to justify in review.
NOT_STYLED_ON_PURPOSE: set[str] = set()

#: ⚠ ONE THAT ALREADY FAILS, NAMED SO A SECOND CANNOT ARRIVE QUIETLY.
#:
#: Found by this check on 2026-09-21, pre-existing, and not introduced by the
#: change that prompted the check. `mb-link` is on an `<a href>` in
#: `ModelEvidence.jsx` and a `<Link>` in `Compare.jsx`, so those links render
#: as body text - a real defect, and a small one.
#:
#: RECORDED RATHER THAN FIXED, because what it should look like is a question
#: with more than one defensible answer and this repository has just written
#: down that a stylesheet rendering evidence is not a place to guess (rule 12's
#: argument, and `KNOWN_UNDEFINED` in `test_a_figure_is_one_measurement.py`
#: does the same with five undefined tokens in `app.css`).
KNOWN_UNSTYLED = {"mb-link"}

_CLASS_ATTR = re.compile(r'className="([^"{}]+)"')
_CLASS_IN_JS = re.compile(r'class="([^"{}$]+)"')


def _declared() -> set[str]:
    """Every class selector any stylesheet defines, comments stripped."""
    out: set[str] = set()
    for f in STYLES.glob("*.css"):
        text = re.sub(r"/\*.*?\*/", " ", f.read_text(encoding="utf-8"), flags=re.DOTALL)
        # Selectors only: everything before a `{`, so a class named inside a
        # declaration value cannot count as a definition.
        for block in text.split("{")[:-1]:
            selector = block.rsplit("}", 1)[-1]
            out.update(re.findall(r"\.(-?[_a-zA-Z][\w-]*)", selector))
    return out


def _used() -> dict[str, set[str]]:
    """Every class the app asks for, and the files asking."""
    used: dict[str, set[str]] = {}
    for f in list(SRC.rglob("*.jsx")) + list(SRC.rglob("*.js")):
        text = f.read_text(encoding="utf-8")
        names: set[str] = set()
        for m in _CLASS_ATTR.finditer(text):
            names.update(m.group(1).split())
        # views.js builds HTML strings, so its classes are in `class="..."`.
        for m in _CLASS_IN_JS.finditer(text):
            names.update(m.group(1).split())
        for n in names:
            used.setdefault(n, set()).add(f.relative_to(ROOT).as_posix())
    return used


class TestEveryClassNameIsDefined:
    def test_no_element_asks_for_a_class_nothing_defines(self):
        declared = _declared()
        assert "card" in declared and "chip" in declared, (
            "the selector scan is not finding classes that plainly exist"
        )

        missing = {
            name: sorted(where)
            for name, where in sorted(_used().items())
            if name not in declared
            and name not in NOT_STYLED_ON_PURPOSE
            and name not in KNOWN_UNSTYLED
        }
        assert not missing, (
            "these elements name a class no stylesheet defines, so each takes "
            f"the browser default and looks merely unfinished: {missing}. "
            "`className=\"input\"` shipped that way and rendered white text on "
            "a white input in the board review."
        )

    def test_the_exemptions_are_still_unstyled(self):
        """An exemption that has quietly become styled is a lie in the other
        direction, and it stops the next reader trusting the set."""
        declared = _declared()
        now_styled = sorted(
            n for n in (NOT_STYLED_ON_PURPOSE | KNOWN_UNSTYLED) if n in declared
        )
        assert not now_styled, (
            f"{now_styled} are styled now; take them out of "
            "NOT_STYLED_ON_PURPOSE / KNOWN_UNSTYLED so each set keeps meaning "
            "what it says"
        )

    def test_the_two_that_taught_this_are_covered(self):
        # Pins the specific regressions rather than trusting the sweep.
        declared = _declared()
        assert "input" in declared, "the merge box is unreadable again"
        assert "fold" in declared, "the settings contract rows are unstyled"


class TestAModelIsShownByName:
    """⚠ TWO RENDER SITES, ONE FIXED, AND THE READER FOUND THE OTHER.

    The board review printed `mv_9a8f4a62b182ff64` where a model name belongs
    (#278). The quote list was fixed by resolving the label in
    `list_for_review`; the "already ruled" receipt below it printed
    `q.model_version_id` directly and was missed — so the defect survived its
    own fix, in the same file, forty lines down.

    Measured 2026-09-21: 0 of 719 review quotes fail to resolve server-side,
    so an id on this panel means a render site that forgot to ask for the
    name, not a model the registry does not know.
    """

    def test_no_render_site_prints_a_raw_model_id_without_trying_the_name(self):
        src = (ROOT / "web" / "src" / "components" / "BoardReview.jsx").read_text(encoding="utf-8")
        # ⚠ BLOCK STATE, NOT A PREFIX TEST. The first version skipped lines
        #   STARTING with a comment marker, and a JSX block comment explaining
        #   this very rule wraps onto lines that start with a backtick — so
        #   the check failed on its own documentation. Fourth time this
        #   repository has hit mention-versus-use, and the first three are
        #   written down in `test_the_board_drills_down.py`.
        in_block = False
        for i, line in enumerate(src.splitlines(), 1):
            stripped = line.strip()
            if not in_block and ("{/*" in line or "/*" in line) and "*/" not in line:
                in_block = True
                continue
            if in_block:
                if "*/" in line:
                    in_block = False
                continue
            if stripped.startswith("//"):
                continue
            if "model_version_id" not in line:
                continue
            assert "model_label" in line, (
                f"BoardReview.jsx:{i} renders a model id without preferring "
                f"`model_label` first: {stripped}"
            )

    def test_the_backend_resolves_the_name_for_every_review_quote(self):
        # Structural: the query must do the join, because a frontend cannot
        # resolve an id it was never sent.
        store = (ROOT / "judge" / "store" / "board_entries.py").read_text(encoding="utf-8")
        block = store[store.index("def list_for_review"):]
        block = block[:block.index(chr(10) + "def ")]
        assert "coalesce(v.display_name, v.canonical_id, r.model_version_id)" in block
        assert '"model_label": label or mv,' in block
