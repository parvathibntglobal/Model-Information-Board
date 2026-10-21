"""The "Where a model is used" overview says only what the code can back.

It sits at the top of the admin Prompts section and explains, in plain words,
where an AI model is called and what it is told. Every sentence on it is a claim
about code that changes, so none of it is typed in:

    the stages allowed to call a model    read from `spend_ledger.STAGES`
    how long each prompt is               measured from the built prompt
    each plain-language point             carries the phrase it summarises
    the fields left over                  looked for in the schema actually sent

⚠ THIS ADMIN PAGE HAS ALREADY SHIPPED TWO CAPTIONS THAT WENT STALE. A cap read
  "the 'x of 50' on the button" while production ran 25, and a card on the
  models page explained a column that had been removed. Prose that restates what
  the code says has two ways to be right, and one of them goes stale first.

⚠ A SUMMARY OF A PROMPT IS A CLAIM ABOUT A PROMPT. The page flags a point whose
  phrase has left the prompt; the first test here makes that a CI failure too,
  so a prompt change and its summary land together rather than the page quietly
  describing a rule the model is no longer told.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "judge" / "app.py"
CARD = ROOT / "web" / "src" / "components" / "WhereAModelIsUsed.jsx"
WEB = ROOT / "web" / "src"


def _app():
    import sys
    sys.path.insert(0, str(ROOT))
    import judge.app as app
    return app


class TestEverySummaryPointIsStillInThePrompt:
    def test_extraction_points_match_the_live_prompt(self):
        """⚠ THE LOAD-BEARING TEST. Change the prompt and a summary point stops
        matching - which is the moment the summary has to change with it."""
        callers = _app()._where_a_model_is_used()
        missing = [p["title"] for p in callers["extract"]["points"] if not p["found"]]
        assert not missing, (
            f"these plain-language points no longer appear in the extraction "
            f"prompt: {missing}. Update `_EXTRACT_POINTS` in judge/app.py "
            f"alongside the prompt change, or the admin page will describe a "
            f"rule the model is not told any more."
        )

    def test_ask_points_match_the_live_prompt(self):
        callers = _app()._where_a_model_is_used()
        missing = [p["title"] for p in callers["ask"]["points"] if not p["found"]]
        assert not missing, f"Ask box points no longer in its prompt: {missing}"

    def test_every_point_has_an_anchor_long_enough_to_mean_something(self):
        """A three-letter anchor would match almost any prompt and prove
        nothing. The check is only as strong as the phrase it looks for."""
        app = _app()
        for title, _plain, anchor in (*app._EXTRACT_POINTS, *app._ASK_POINTS):
            assert len(anchor) >= 15, f"{title!r}: anchor {anchor!r} is too short to check"


class TestTheFactsAreReadNotTyped:
    def test_the_stages_come_from_the_ledger(self):
        # Every stage the ledger accepts - which stages MAY call a model, the
        # blog generator included - not `STAGES`, the daily cap's two.
        from judge import spend_ledger
        assert _app()._where_a_model_is_used()["stages"] == list(spend_ledger.RECORDED_STAGES)

    def test_the_prompt_size_is_measured(self):
        from judge.config import capabilities
        from judge.extract.prompt import build_system_prompt
        built = len(build_system_prompt(sorted(capabilities().keys())))
        assert _app()._where_a_model_is_used()["extract"]["prompt_chars"] == built

    def test_the_left_over_fields_come_from_the_schema_actually_sent(self):
        """⚠ NOT FROM THE CLAIM-LEVEL FIELD LIST. `proposed_capabilities` is on
        the top-level result, not on a claim, so the panel's own field reader
        does not see it. The check has to be the schema the model receives."""
        from judge.config import capabilities
        from judge.extract.client import tool_schema_for
        from judge.extract.schema import ExtractionResult
        sent = json.dumps(tool_schema_for(ExtractionResult,
                                          capability_keys=sorted(capabilities().keys())))
        expected = [f for f in _app()._CLOSED_TWELVE_FIELDS if f'"{f}"' in sent]
        assert _app()._where_a_model_is_used()["extract"]["closed_twelve_fields"] == expected

    def test_the_card_types_no_prompt_size(self):
        """"About 22,000 characters" was true in a chat answer. On the page it
        is the count of the prompt built a moment ago."""
        card = CARD.read_text(encoding="utf-8")
        code = re.sub(r"/\*[\s\S]*?\*/", " ", card)
        assert not re.search(r"\b22[,.]?\d{3}\b", code), "a prompt size is typed into the card"
        assert "part.prompt_chars" in code


class TestTheAskBoxIsDescribedAsWhatItIs:
    def test_it_is_still_not_reachable_from_the_site(self):
        """⚠ THE CARD SAYS "not reachable from the site yet". That stops being
        true the day a component calls it, and then the card is the reassuring
        reading of a surface that exists. Same interlock as the usage panel's
        `ask (not built yet)`."""
        callers = []
        for path in sorted(WEB.rglob("*.jsx")) + sorted(WEB.rglob("*.js")):
            if path.name == "index.js" and path.parent.name == "api":
                continue
            text = re.sub(r"/\*[\s\S]*?\*/", " ", path.read_text(encoding="utf-8"))
            text = re.sub(r"//[^\n]*", " ", text)
            if re.search(r"\baskUnderstand\s*\(", text):
                callers.append(path.name)
        assert not callers, (
            f"{callers} calls the Ask box now, so 'not reachable from the site "
            f"yet' in WhereAModelIsUsed.jsx is false. Update it with the usage "
            f"panel's notice."
        )

    def test_the_not_shown_entry_no_longer_calls_it_retired(self):
        """It is a plan, not a surface that was taken down. Two parts of one
        admin page must not describe one feature as both."""
        src = APP.read_text(encoding="utf-8")
        block = src[src.index('"not_shown": ['):]
        block = block[:block.index("],\n    }")]
        code = re.sub(r"#[^\n]*", "", block)
        assert "retired" not in code
        assert "not built" in code


class TestTheRouteStillServesThePrompts:
    def test_the_decorator_is_on_admin_prompts(self):
        """⚠ A HELPER INSERTED ABOVE AN ENDPOINT CAN TAKE ITS DECORATOR. That
        happened to `/compare` this week and only a contract gate noticed, so the
        helper added here is checked for the same shape."""
        tree = ast.parse(APP.read_text(encoding="utf-8"))
        owners = [
            n.name for n in tree.body if isinstance(n, ast.FunctionDef)
            for d in n.decorator_list
            if isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "get"
            and d.args and getattr(d.args[0], "value", None) == "/admin/prompts"
        ]
        assert owners == ["admin_prompts"], f"/admin/prompts decorates {owners}"


PANEL = ROOT / "web" / "src" / "components" / "PromptsPanel.jsx"


def _panel() -> str:
    text = re.sub(r"/\*[\s\S]*?\*/", " ", PANEL.read_text(encoding="utf-8"))
    return re.sub(r"//[^\n]*", " ", text)


class TestThePanelIsTwoTabs:
    """"Model uses" and "Prompts" as two tabs rather than one long stack. The
    overview sat above a long prompt list and read as a preamble to scroll past;
    as a tab it is a thing you open."""

    def test_both_tabs_exist_with_their_labels(self):
        panel = _panel()
        assert "['uses', 'Model uses'," in panel
        assert "['prompts', 'Prompts'," in panel
        assert 'role="tablist"' in panel and 'role="tab"' in panel

    def test_each_tab_carries_its_count(self):
        """The same rule as the model page's tabs: what is behind a tab is
        visible before the click."""
        panel = _panel()
        assert "(data.model_callers?.stages || []).length" in panel
        assert "data.count]" in panel
        assert '<span className="x">{n}</span>' in panel

    def test_it_opens_on_prompts_and_lists_it_first(self):
        """This is the Prompts section, and the exact text sent is what it is
        named for; "Model uses" is its plain-words companion one tab across."""
        panel = _panel()
        assert "useState('prompts')" in panel
        assert panel.index("['prompts', 'Prompts',") < panel.index("['uses', 'Model uses',")

    def test_the_prompt_material_is_all_inside_the_prompts_tab(self):
        """The rules and the not-shown list describe the prompts, so they belong
        behind that tab rather than under both."""
        panel = _panel()
        opens = panel.index("tab === 'prompts'")
        for marker in ("Sent to the model", "data?.not_shown"):
            assert panel.index(marker) > opens, f"{marker!r} renders outside the Prompts tab"
