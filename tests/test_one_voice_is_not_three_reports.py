"""Three figures in one comment are one report, and not "verified".

WHAT THE ETHICAL-REASONING PAGE SAID ON 2026-09-11:

    Board / Capabilities / Ethical reasoning
    MODELS WITH EVIDENCE
    Who has been reported doing this
      claude-fable-5-1                        3 reports · verified
    REPORTS
    What breaks it
      "it revived both men in 10 out of 20 rounds (50%)"
      "When people are watching, Fable 5.1 never shot, and it revived both
       men in 19 out of 20 rounds (95%)"
      "Fable 5.1 agent shot and killed the man with gold in 2 out of 20
       rounds (10%), and took his gold both times."

Every one of those three quotes is the SAME document by the SAME author
(`hackernews:49610874`, `au_ef68cc64b3130e13`). Four things were wrong:

  1. `reports` was incremented once per ROW, and a row is one quote. Nothing on
     the board read path had ever selected `document_id` or `author_id`.
  2. That inflated count crossed `evidenceState`'s `reports >= 2` threshold, so
     one person was labelled **verified** - the one word this board cannot be
     wrong about. The function's own docstring already said "one voice is not
     corroboration"; it just had no way to count voices.
  3. The three quotes were rendered as three separate cards, reading as three
     independent observations. None of them stands alone: read singly, none
     says what the scenario was or which condition its figure belongs to.
  4. "What breaks it" was hardcoded. One of the three is `positive`.

AND THE FLOOR ARGUMENT DID NOT COVER IT. The docstring justified `reports` as a
FLOOR because an open vocabulary fragments sections and undercounts. Counting
quotes as reports made it too HIGH, and no amount of ">= N" rescues a number
that overstates corroboration.

WHAT IS DELIBERATELY NOT DONE: the three quotes are not merged into one
readable sentence. They describe DIFFERENT conditions - 50% unobserved, 95%
observed, 10% shot-and-robbed - so composing them into prose would be writing a
summary of somebody else's experiment, which is rule 3 and rule 1 together. The
context comes from the source link, not from us.
"""

from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STORE = ROOT / "judge" / "store" / "board_entries.py"
DB = ROOT / "web" / "src" / "board" / "db.js"
VIEWS = ROOT / "web" / "src" / "board" / "views.js"


class TestTheCountIsSourcesNotRows:
    @staticmethod
    def _src() -> str:
        return STORE.read_text(encoding="utf-8")

    def test_the_row_increment_is_gone(self):
        assert 'bucket["reports"] += 1' not in self._src(), (
            "one row is one quote; incrementing per row is what produced "
            '"3 reports" from a single comment'
        )

    def test_both_readers_select_the_author(self):
        # `board_sections` AND `evidence_for_model`. The model page inherited
        # exactly the same inflation.
        assert self._src().count("d.author_id") == 2

    def test_reports_counts_distinct_documents(self):
        src = self._src()
        assert 'item["reports"] = len(item.pop("_docs"))' in src
        assert 'bucket["_docs"].add(doc_id)' in src

    def test_voices_counts_distinct_authors(self):
        src = self._src()
        assert 'item["voices"] = len(item.pop("_voices"))' in src
        assert 'bucket["_voices"].add(author_id)' in src

    def test_the_quote_count_stays_separate(self):
        # So a page can say "1 report · 3 figures" instead of having to choose
        # which of those two numbers to show as one.
        assert 'item["quote_count"] = len(item["quotes"])' in self._src()

    def test_per_model_counts_are_also_distinct_documents(self):
        # Otherwise the models list inherits the same inflation one level down.
        src = self._src()
        assert 'bucket["_models"].setdefault(mv_id, set()).add(doc_id)' in src
        assert '{"model_version_id": m, "reports": len(docs)}' in src

    def test_the_docstring_corrects_the_floor_claim(self):
        # The floor argument is about undercounting. This bug overcounted, and
        # the docstring now says so rather than leaving a justification that
        # points the wrong way.
        doc = self._src()
        assert "ONE REPORT IS ONE SOURCE DOCUMENT" in doc
        assert "too HIGH" in doc


class TestCorroborationIsJudgedOnVoices:
    @staticmethod
    def _js() -> str:
        return DB.read_text(encoding="utf-8")

    def test_evidence_state_takes_voices(self):
        js = self._js()
        assert "function evidenceState(voices, quotes)" in js
        assert "return voices >= 2 ? 'v' : 's'" in js

    def test_it_is_fed_voices_rather_than_reports(self):
        assert "evidenceState(item.voices ?? item.reports, item.quotes)" in self._js()

    def test_an_older_payload_degrades_to_the_old_behaviour_not_to_none(self):
        # `?? item.reports`, not `?? 0`. A payload without `voices` should read
        # as it used to, not as "nothing discussed" - an absence must not
        # become a definite claim of no evidence.
        js = self._js()
        assert "item.voices ?? item.reports" in js
        assert "item.voices ?? 0" not in js

    def test_the_label_separates_reports_from_figures(self):
        js = self._js()
        assert "function evidenceLabel(item)" in js
        assert "figures" in js

    def test_one_report_one_figure_does_not_say_it_twice(self):
        # "1 report · 1 figure" is noise; the second number is only worth
        # saying when it differs.
        assert "quotes > reports" in self._js()


class TestTheLabelsStopOverloadingVerified:
    @staticmethod
    def _js() -> str:
        return VIEWS.read_text(encoding="utf-8")

    def test_verified_is_no_longer_an_evidence_state(self):
        # `verified` is already this codebase's word for `quote_verified` - a
        # span that matched its source text. Reusing it for "two or more people
        # said so" overloads the one term that has to stay precise.
        js = self._js()
        st = js[js.index("const ST = {"):]
        st = st[: st.index("};")]
        assert "'verified'" not in st
        assert "'corroborated'" in st
        assert "'one voice'" in st


class TestQuotesAreGroupedBySource:
    @staticmethod
    def _js() -> str:
        return VIEWS.read_text(encoding="utf-8")

    def test_the_renderer_groups_before_it_renders(self):
        js = self._js()
        block = js[js.index("function quotes(qs){"):js.index("function reportsHeading")]
        assert "const groups = []" in block
        assert "groups[seen.get(key)].items.push(row)" in block

    def test_the_citation_appears_once_per_source(self):
        # It used to repeat under every quote, which is part of what made three
        # fragments look like three findings.
        js = self._js()
        block = js[js.index("function quotes(qs){"):js.index("function reportsHeading")]
        assert block.count("open the source</a>") == 1

    def test_a_multi_figure_group_says_how_many(self):
        js = self._js()
        assert "figures from this one report" in js

    def test_it_does_not_compose_the_quotes_into_prose(self):
        # The guard against the tempting fix. Each quote is still rendered in
        # its own <q>, verbatim, escaped.
        js = self._js()
        block = js[js.index("function quotes(qs){"):js.index("function reportsHeading")]
        assert "<q>${esc(row[0])}</q>" in block
        assert ".join(' ')" not in block, "joining quote TEXT would synthesise a claim"


class TestTheReportsHeadingFollowsThePolarity:
    @staticmethod
    def _heading_source() -> str:
        js = VIEWS.read_text(encoding="utf-8")
        return js[js.index("function reportsHeading"):]

    def test_the_hardcoded_heading_is_gone_from_the_page(self):
        js = VIEWS.read_text(encoding="utf-8")
        assert "sec('Reports','What breaks it'" not in js

    def test_the_page_calls_the_derived_heading(self):
        js = VIEWS.read_text(encoding="utf-8")
        assert "sec('Reports',reportsHeading(c.qs)" in js

    @pytest.mark.parametrize(
        "negatives,total,expected",
        [
            (0, 3, "What was reported"),
            (1, 3, "What was reported, good and bad"),
            (3, 3, "What breaks it"),
            (0, 0, ""),
        ],
    )
    def test_the_three_cases_are_all_expressed(self, negatives, total, expected):
        """Read off the source rather than executed — there is no JS runner in
        this suite, and the point is that all three branches exist and say
        something different."""
        src = self._heading_source()
        if expected:
            assert f"'{expected}'" in src
        else:
            assert "if(!qs || !qs.length) return ''" in src
        del negatives, total
