"""A complaint must never read as a recommendation.

WHAT THE BOARD SAID ON 2026-09-11, from one Hacker News comment:

    Board / Best for / Coding agents
    EVERY MODEL WITH REPORTS FOR THIS JOB
    What engineers actually ran        01   claude-fable-5-1
    THE QUOTES BEHIND THE RANKING
    What they said, verbatim           "it has created 20+ bugs"

One person's bug report, rendered as the top recommendation for the job.

TWO FIXES, FOURTEEN DAYS APART, AND THIS FILE HOLDS BOTH.

  2026-09-11   the read surface FILTERED negatives out of `best_for`. It fixed
               the page by hiding the evidence: 25 rows, 6 models dropped from
               their job entirely, 3 jobs with no page at all.
  2026-09-25   the filter is gone and the SURFACE changed instead. The tab is
               "Jobs", not "Best for"; every category page lists models in
               three named groups (reported working / only neutral / reported
               problems, none working) with both counts on every row. A
               complaint cannot read as a recommendation when it sits under
               "Reported problems" with its count beside it.

`judge/extract/prompt.py` still declines to PROPOSE a negative best_for entry
(tested below, unchanged). That is a separate decision about a paid model call.

WHAT IS DELIBERATELY NOT DONE: the rows are not deleted and the write is not
refused, exactly as before.
"""

from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STORE = ROOT / "judge" / "store" / "board_entries.py"
PROMPT = ROOT / "judge" / "extract" / "prompt.py"
VIEWS = ROOT / "web" / "src" / "board" / "views.js"


class TestTheBoardQueryFiltersNothing:
    @staticmethod
    def _sql() -> str:
        return STORE.read_text(encoding="utf-8")

    def test_no_section_is_polarity_filtered(self):
        sql = self._sql()
        assert "AND NOT (be.section = 'best_for' AND be.polarity = 'negative')" not in sql
        for section in ("best_for", "capability", "metric"):
            assert f"be.section = '{section}' AND be.polarity" not in sql

    def test_the_docstring_records_what_the_filter_was_and_what_replaced_it(self):
        doc = self._sql()
        assert "NO SECTION IS POLARITY-FILTERED ANY MORE" in doc
        assert "3d-art" in doc and "proof-based-programming" in doc

    def test_the_write_path_is_untouched(self):
        # The row must still be stored, and the writer must not learn a rule
        # about sections - a refused write loses the finding.
        src = self._sql()
        store_fn = src[src.index("def store_entries("):src.index("def board_sections")]
        assert "polarity" in store_fn
        assert "best_for" not in store_fn


class TestTheSurfaceNoLongerPromisesSuitability:
    @staticmethod
    def _js() -> str:
        return VIEWS.read_text(encoding="utf-8")

    def test_the_tab_is_named_for_what_it_holds(self):
        js = self._js()
        assert 'data-tab="best">Jobs</button>' in js
        assert ">Best for</button>" not in js

    def test_no_visible_label_says_best_for(self):
        # Comments may quote the old heading to explain why it went; rendered
        # strings may not.
        for path in (VIEWS, ROOT / "web" / "src" / "components" / "ModelEvidence.jsx",
                     ROOT / "web" / "src" / "routes" / "Compare.jsx"):
            for line in path.read_text(encoding="utf-8").splitlines():
                code = line.strip()
                if code.startswith(("//", "*", "/*")):
                    continue
                assert "Best for" not in code, f"{path.name}: {code[:90]}"

    def test_the_tab_intro_no_longer_promises_a_pick(self):
        js = self._js()
        assert "names the cheapest model" not in js
        assert "criticisms that did not disqualify it" not in js
        assert "Problem reports are shown, not filtered." in js


class TestThePromptStopsProposingIt:
    @staticmethod
    def _text() -> str:
        return PROMPT.read_text(encoding="utf-8")

    def test_best_for_now_requires_two_things(self):
        t = self._text()
        assert "TWO THINGS MUST BOTH BE TRUE" in t
        assert "THE MODEL ACTUALLY WORKED" in t

    def test_it_says_where_a_negative_report_goes_instead(self):
        # A rule that only forbids leaves the model guessing, and a guess here
        # loses the finding entirely.
        t = self._text()
        assert "capability" in t
        assert "DO NOT emit a best_for entry" in t

    def test_the_polarity_section_repeats_the_rule(self):
        # The two instructions are far apart in the prompt, and the one a model
        # is reading when it sets `negative` is the polarity one.
        t = self._text()
        tail = t[t.index("If the writer names a PAIN POINT"):]
        assert "MUST NOT carry a `best_for` entry" in tail

    def test_it_carries_the_measurement_that_forced_the_change(self):
        # The prompt is the place this is most likely to be softened by someone
        # who has not seen what it produced.
        t = self._text()
        assert "20+ bugs" in t


class TestThePageStopsClaimingARanking:
    @staticmethod
    def _js() -> str:
        return VIEWS.read_text(encoding="utf-8")

    def test_no_surface_calls_it_a_ranking(self):
        # THE RENDERED STRINGS ONLY. The comment above `ranked()` quotes the old
        # heading to explain why it went, and a check that cannot tell a mention
        # from a use fails on its own documentation - which is the second time
        # that has caught me, so it is written down here.
        rendered = [
            line for line in self._js().splitlines()
            if "sec(" in line and not line.lstrip().startswith("//")
        ]
        assert rendered, "no section calls found - the check would pass vacuously"
        for line in rendered:
            assert "ranking" not in line, (
                f"there is no score anywhere in this path - board_sections "
                f"sorts by COUNT and says so: {line.strip()[:90]}"
            )

    def test_the_rank_numeral_is_gone(self):
        # `01`, `02` came from the array index. A list ordered by report count
        # printed as a numbered rank is a synthesised figure on a page (rule 3).
        js = self._js()
        assert "String(i+1).padStart(2,'0')" not in js

    def test_the_heading_no_longer_claims_usage_it_cannot_see(self):
        # "What engineers actually ran" is a claim about deployment; a report is
        # a claim about what somebody said.
        assert "What engineers actually ran" not in self._js()

    def test_a_negative_quote_is_labelled_in_words(self):
        # It used to be marked only by switching a 3px left border from green
        # to amber, with no legend - so the marker was invisible, and green by
        # default read as approval.
        js = self._js()
        assert "reported as a problem" in js

    def test_the_fourth_tuple_slot_is_named_for_what_it_holds(self):
        # It was called `contested` while db.js filled it with
        # `polarity === 'negative'`, and `evidenceState` used 'c' for genuinely
        # contested. One letter, two meanings.
        js = self._js()
        assert "isNegative" in js
        db = (ROOT / "web" / "src" / "board" / "db.js").read_text(encoding="utf-8")
        assert "isNegative, url]" in db


@pytest.mark.parametrize("section", ["best_for", "capability", "metric"])
@pytest.mark.parametrize("polarity", ["negative", "positive", "neutral", None])
def test_every_polarity_reaches_every_section(section, polarity):
    """The whole rule in one place: nothing is excluded by polarity anywhere.
    The ORDER is where polarity acts now - see `_group_of`."""
    sql = STORE.read_text(encoding="utf-8")
    query = sql[sql.index("def board_sections("):sql.index("def _group_of(")]
    assert "be.polarity =" not in query.split('"""', 2)[-1]
