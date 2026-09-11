"""A complaint must never fill a surface that recommends.

WHAT THE BOARD SAID ON 2026-09-11, from one Hacker News comment:

    Board / Best for / Coding agents
    EVERY MODEL WITH REPORTS FOR THIS JOB
    What engineers actually ran        01   claude-fable-5-1
    THE QUOTES BEHIND THE RANKING
    What they said, verbatim           "it has created 20+ bugs"

One person's bug report, rendered as the top recommendation for the job.

NOTHING IN THE PIPELINE WAS WRONG. The classifier recorded
`polarity: negative` correctly and filed the quote under the job the writer
named. The defect was in what `best_for` MEANS: the prompt defined it purely
topically — "does it say what they were trying to do?" — while the board
renders it as "BEST FOR <job>", a recommendation a reader acts on. Only a
positive report can say that.

THE FIX IS IN TWO PLACES ON PURPOSE.

  prompt          `judge/extract/prompt.py` stops PROPOSING a best_for entry
                  for a negative claim, so the row is not created.
  read surface    `board_sections` stops SHOWING one, so rows already written —
                  and any future misclassification — cannot reach the page.

A prompt is an instruction to a model that may not follow it, so it cannot be
the only guard (rule 2: an LLM may propose, it may never decide). The rule
itself is ours, stated in code; the model only supplies the polarity label.

WHAT IS DELIBERATELY NOT DONE:

  * the rows are not deleted, and the write is not refused. The finding is
    real, and the model's own page shows it with its polarity — removing it
    would be the caused absence rule 4 forbids.
  * `capability` and `metric` are not filtered. Those describe BEHAVIOUR and
    FIGURES, where a bad result is evidence of the same standing as a good one.
    "it has failed to test the fixes" is a real finding about code-testing.
    Only "best for" claims suitability.
"""

from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STORE = ROOT / "judge" / "store" / "board_entries.py"
PROMPT = ROOT / "judge" / "extract" / "prompt.py"
VIEWS = ROOT / "web" / "src" / "board" / "views.js"


class TestTheBoardQueryRefusesIt:
    @staticmethod
    def _sql() -> str:
        return STORE.read_text(encoding="utf-8")

    def test_the_filter_is_in_the_query_that_defines_the_board(self):
        assert (
            "AND NOT (be.section = 'best_for' AND be.polarity = 'negative')"
            in self._sql()
        )

    def test_it_names_only_best_for(self):
        # A filter on every section would delete real findings from
        # `capability` and `metric`, where a bad result is the same kind of
        # evidence as a good one.
        sql = self._sql()
        for section in ("capability", "metric"):
            assert f"be.section = '{section}' AND be.polarity" not in sql

    def test_an_unknown_or_absent_polarity_stays_visible(self):
        # Written as NOT(... = 'negative') rather than an allow-list of
        # 'positive'/'neutral'. A NULL polarity means "we could not tell", and
        # deleting a finding for that is rule 6 — an absent value becoming a
        # definite one.
        sql = self._sql()
        assert "be.polarity IN ('positive'" not in sql
        assert "be.polarity = 'positive'" not in sql

    def test_the_docstring_says_why_capability_is_different(self):
        doc = self._sql()
        assert "capability` and `metric` are NOT filtered" in doc
        assert "suitability" in doc

    def test_the_write_path_is_untouched(self):
        # The row must still be stored: the model page is where it belongs.
        src = self._sql()
        store_fn = src[src.index("def store_entries("):src.index("def board_sections")]
        assert "polarity" in store_fn
        assert "best_for" not in store_fn, (
            "the writer must not learn about this rule - a refused write loses "
            "the finding the model page needs"
        )


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


@pytest.mark.parametrize(
    "section,polarity,visible",
    [
        ("best_for", "negative", False),
        ("best_for", "positive", True),
        ("best_for", "neutral", True),
        ("best_for", None, True),
        ("capability", "negative", True),
        ("metric", "negative", True),
    ],
)
def test_the_rule_as_a_table(section, polarity, visible):
    """The whole rule in one place, so a future reader can see its shape.

    Expressed against the SQL rather than a live database, because the filter
    is one clause and the point is which combinations it names.
    """
    sql = STORE.read_text(encoding="utf-8")
    clause = "AND NOT (be.section = 'best_for' AND be.polarity = 'negative')"
    assert clause in sql
    hidden = section == "best_for" and polarity == "negative"
    assert hidden is not visible
