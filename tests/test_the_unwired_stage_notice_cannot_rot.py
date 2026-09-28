"""The Usage panel says the Ask box is not built. That stops being true the day
somebody builds it.

⚠ THE NOTICE USED TO SAY SOMETHING FALSE, WITH CERTAINTY:

      "One stage has never recorded a call: ask. That is a stage NOT WIRED TO
       THE LEDGER, not a stage that has cost nothing."

  Checked 2026-09-28. `/ask/understand` is the only route in the ask flow that
  calls a model — `/ask/recommend` and `/ask/revise` run no LLM — and it charges
  the ledger through `judge/ask/spend.py`, which records STAGE_ASK
  unconditionally, ahead of the budget branch. The wiring is present and
  correct.

  The stage reads zero because the Ask box does not exist on the site. No
  component calls `askUnderstand`; there is no /ask route in the app.

  So the panel took an absence and converted it into a definite mechanical
  claim — rule 6, aimed at ourselves, by the very notice that exists to stop
  a zero being read as good news.

⚠ AND THE REPLACEMENT HAS ITS OWN EXPIRY. The new copy says, for `ask`
  specifically, that nothing calls it. That sentence is TRUE TODAY AND IS A
  CLAIM ABOUT THE FRONTEND, so the moment an Ask surface ships it becomes the
  same class of false statement, pointing the other way: a real wiring fault
  reported as "not built yet" is the reassuring reading of an alarm.

  This file is the interlock. It fails when a caller appears, which is the
  moment the words have to change.
"""

from __future__ import annotations

import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "src"
PANEL = WEB / "components" / "UsagePanel.jsx"
SPEND = ROOT / "judge" / "ask" / "spend.py"


def _jsx_without_comments(text: str) -> str:
    """`//` and `/* */` stripped.

    The panel now explains the old false claim at length, quoting it, so a
    search over the raw file finds the wording it was written to remove.
    """
    text = re.sub(r"/\*[\s\S]*?\*/", " ", text)
    return re.sub(r"//[^\n]*", " ", text)


class TestTheClaimMatchesTheCode:
    def test_no_component_calls_the_ask_endpoint(self):
        """The load-bearing fact. When this fails, the panel is lying.

        `api/index.js` is excluded because DEFINING `askUnderstand` is not
        calling it — the export has been there the whole time, which is
        precisely why its presence proves nothing about whether a surface
        exists.
        """
        callers = []
        for path in sorted(WEB.rglob("*.jsx")) + sorted(WEB.rglob("*.js")):
            if path.name == "index.js" and path.parent.name == "api":
                continue
            if re.search(r"\baskUnderstand\s*\(", _jsx_without_comments(
                    path.read_text(encoding="utf-8"))):
                callers.append(str(path.relative_to(ROOT)).replace("\\", "/"))
        assert not callers, (
            f"{callers} now calls the Ask box, so the Usage panel's sentence "
            f"'the Ask box is not built, no page calls it' is false. A real "
            f"wiring fault would now be reported as an unbuilt feature, which "
            f"is the reassuring reading of an alarm. Update the copy in "
            f"web/src/components/UsagePanel.jsx."
        )

    def test_the_ask_path_really_does_charge_the_ledger(self):
        """The other half of the sentence, and the half that was wrong before.

        Asserted against the code rather than trusted, because 'it is wired'
        is exactly the claim the old notice got backwards.
        """
        tree = ast.parse(SPEND.read_text(encoding="utf-8"))
        charge = next(
            (n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and n.name == "charge"),
            None,
        )
        assert charge is not None, "judge/ask/spend.py has no charge()"
        records = [
            n for n in ast.walk(charge)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "record"
        ]
        assert records, (
            "charge() no longer records to the shared ledger, so the panel's "
            "claim that the ask route is wired is now false"
        )


class TestTheNoticeStatesBothReadingsAndAssertsNeither:
    def test_it_no_longer_asserts_a_wiring_fault(self):
        code = _jsx_without_comments(PANEL.read_text(encoding="utf-8"))
        assert "not wired to the ledger, not a stage" not in code, (
            "the notice is asserting a wiring fault again from an absence "
            "alone; the ledger cannot distinguish 'no caller' from 'wired "
            "wrong'"
        )

    def test_it_still_warns_about_the_case_that_matters(self):
        """⚠ THE CONTROL. Softening the notice into harmlessness would pass
        the test above. A stage that spends and records nothing is a real
        alarm and the words must keep it."""
        code = _jsx_without_comments(PANEL.read_text(encoding="utf-8"))
        assert "missing from every number here" in code, (
            "the notice no longer says what an unwired stage would cost you"
        )

    def test_never_ran_is_a_named_set_and_not_the_default(self):
        """⚠ "(never ran)" MUST BE EARNED, ONE STAGE AT A TIME.

        The short label is right for `ask` and is a guess about anything else.
        Applied to every unwired stage it would read as reassurance over the
        top of a real wiring fault - which is the failure this whole file
        exists for, in its cheapest possible form: a two-word phrase that
        looks like a tidy-up.

        So the set is asserted to be a set, `ask` is asserted to be in it, and
        the warning branch is asserted to still exist for everything else.
        """
        code = _jsx_without_comments(PANEL.read_text(encoding="utf-8"))
        assert re.search(r"NEVER_RAN\s*=\s*new Set\(\[", code), (
            "NEVER_RAN is no longer an explicit set; '(never ran)' must name "
            "the stages it has been checked for, never default on"
        )
        assert re.search(r"NEVER_RAN\s*=\s*new Set\(\[\s*'ask'\s*\]\)", code), (
            "the NEVER_RAN set no longer holds exactly ['ask']. If a stage was "
            "added, check the same way `ask` was checked: no component calls "
            "it, and the route that spends does reach the ledger."
        )
        assert "!NEVER_RAN.has(s)" in code, (
            "the warning branch for stages OUTSIDE the set is gone, so an "
            "unwired stage would render as harmlessly as an unbuilt one"
        )
