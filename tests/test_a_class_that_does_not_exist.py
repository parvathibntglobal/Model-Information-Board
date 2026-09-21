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
