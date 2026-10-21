"""The compare page can change the comparison, and marks rows that do not differ.

Three things asked for after reading the page as shipped.

⚠ 1 · THE COMPARISON COULD NOT BE CHANGED FROM THE COMPARISON. `?ids=` was read
  once and never written, so swapping one model meant going back to `/models`,
  re-ticking two or three, and submitting again. The page you land on to answer
  *"which of these"* was the one page that could not answer *"what about that
  one instead"*.

  The picker writes the URL rather than local state, because **the URL IS the
  comparison** — this page's value is that it can be sent to somebody, and a
  picker holding its own list would put a different comparison on screen from
  the one the link describes.

⚠ 2 · A ROW THAT DOES NOT DIFFER IS MARKED, NOT HIDDEN — AND THE FIRST
  VERSION HID IT. I generalised the hand-removed *"Reports — nobody has
  discussed this"* row into a rule that dropped any row whose cells were all
  equal. On a real comparison that hid **three of six rows**, so the table lost
  half its content and gained a sentence about the table. @parvathibntglobal
  read it and said the page looked weaker; it did.

  **"Both show none" is content.** On a board whose whole subject is what
  engineers wrote, *neither of these has a reported metric* is a finding
  somebody came here for. The row that started this differed only in being the
  ENTIRE table — one sentence repeated three times — and `anyReports` already
  handles that case.

⚠ 3 · A LIST IS LISTED. Three versions here, and the first two were both
  wrong. `mets.slice(0, 3)` showed three of nine and read as three — a count
  with no denominator (rule 7). Replacing it with `+6 more` in a `title`
  attribute fixed the honesty and not the usefulness: **a tooltip is not
  openable**, it is invisible on touch, and on a comparison page the list is
  the content, so hiding it behind a hover hides the thing somebody came for.

  Semicolon-joined prose was the other half. `reasoning; code generation; long
  context` beside the same shape in the next cell cannot be read across,
  because the eye has no line to follow. Now: the count first, because that is
  what makes two columns comparable at a glance, then every item on its own
  line. Nothing cut, nothing to open.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "web" / "src" / "routes" / "Compare.jsx"
APP = ROOT / "judge" / "app.py"


def app() -> str:
    return APP.read_text(encoding="utf-8")


def source() -> str:
    return PAGE.read_text(encoding="utf-8")


def code() -> str:
    """The page with comments stripped.

    ⚠ EVERY ASSERTION BELOW NAMES SOMETHING THE COMMENTS ALSO DISCUSS — the
      picker explains why it writes the URL, the row rule explains the special
      case it replaced. A plain substring search would read those explanations
      as the behaviour they describe. Fourteenth instance of mention-versus-use
      in this repository.
    """
    text = re.sub(r"/\*[\s\S]*?\*/", "", source())
    return "\n".join(
        ln for ln in text.splitlines() if not ln.strip().startswith(("//", "*", "//:"))
    )


class TestTheComparisonWritesTheUrl:
    def test_the_picker_sets_search_params_rather_than_local_state(self):
        """The URL is the comparison. A link that describes a different page
        from the one on screen is worse than no picker."""
        # Since 2026-10-14 a comparison opened from Models also carries
        # `from=reports` (it hides "In their words"). Since 2026-10-21 the
        # models are the path itself (/compare/<a>-vs-<b>, compare/path.js),
        # so changing them navigates to that address, `from` kept.
        src = code()
        assert "navigate(comparePath(trimmed, { from }))" in src
        assert "useState(trimmed" not in src

    def test_it_refuses_above_the_cap_before_the_request(self):
        """The endpoint answers 422 above three. A reader who clicks a fourth
        should be told by the control, not by an error."""
        assert "next.slice(0, COMPARE_MAX)" in code()

    def test_it_refuses_below_two_rather_than_sending_one(self):
        """One model is not a comparison, and the endpoint says so with a 422.
        Dropping to one is refused where the reader can see why."""
        assert "if (trimmed.length < 2) return" in code()

    def test_the_cap_matches_the_endpoint(self):
        """⚠ TWO CONSTANTS FOR ONE RULE DRIFT SILENTLY, so this reads the
        server's. If they part, the picker either blocks a comparison the API
        would serve or offers one it refuses."""
        server = re.search(r"^COMPARE_MAX = (\d+)", APP.read_text(encoding="utf-8"), re.M)
        page = re.search(r"^const COMPARE_MAX = (\d+)", source(), re.M)
        assert server and page, "COMPARE_MAX moved on one side"
        assert server.group(1) == page.group(1)

    def test_the_last_two_chips_say_why_they_are_disabled(self):
        """A control that goes dead with no reason reads as broken."""
        assert "A comparison needs two models" in source()

    def test_the_roster_is_loaded_only_when_the_picker_opens(self):
        """A reader who never opens it never pays for it, and a comparison
        that renders matters more than a list nobody asked for."""
        assert "if (open && !roster) onLoad()" in code()


# ⚠ SEVEN CLASSES CAME OUT 2026-10-15 with the table they tested: "What
#   engineers said, counted" - posts and comments, how each was phrased, the
#   entry counts, and every job, capability and metric listed per model. It was
#   removed from the page at the product owner's request; see
#   test_the_shared_axes_are_their_own_table.py:TestTheOriginalViewIsGone for
#   what that trades away. The guards that still apply to what remains - no
#   score from the polarity counts, no internal id at the reader - moved to
#   test_a_comparison_names_its_models.py.
