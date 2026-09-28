"""The extractor prompt names the defects a reviewer actually found.

A reviewer read every quote that had produced two or more entries in ONE board
section - 56 of them, on 2026-09-22 - and ruled on each. Forty were sound. The
other sixteen are five distinct bugs, and this file is the record that the
prompt now names all five with the case that produced them.

⚠ WHY A TEST AND NOT JUST A BETTER PROMPT. The prompt is the only place these
  rules live; nothing in code can read whose clause a comma introduces, or
  whether "cybersecurity" was a fourth item somebody skipped. A description
  edited for length loses them silently, and the next 56-quote review is how
  anybody would find out. This is the same reason
  `docs/measurements/a-constraint-not-in-the-description-is-invisible.md`
  exists: the description is necessary and it is not sufficient, so where code
  CAN check - the unit against the figure - it does, in
  `test_a_unit_that_cannot_hold_its_figure.py`. These five are the remainder.

THE FIVE, WITH THE QUOTE THAT SHOWED EACH ONE:

  1  an entry the quote does not support
     "DeepSeek V4 Flash at $0.25/M output is the real story"
      -> best_for/extraction + best_for/rag. It names a price and no task.

  2  a quote about several models, credited to one
     "Haiku for routing, Sonnet for reasoning, Opus for long chains."
      -> three capabilities on Haiku, two of them said about other models.

  3  a list read short
     "significant advance in reasoning, coding, cybersecurity and professional
      work" -> two entries from four named things.

  4  an axis chosen by vocabulary rather than by measurement
     "90 tasks, 10.59M tokens, 118K per task, 10h 37m"
      -> a token total as cost-per-token, a per-task average as
         tokens-per-second.

  5  a quote cut before the figure it is offered as evidence for
     "$0.544 blended … scoring 71.5 on the Vellum leaderboard"
      -> cost-per-benchmark-point, "$0.0076 per point".

⚠ THE FIFTH ONE IS HERE BECAUSE I READ IT WRONG FIRST. I filed it as an axis
  invented to hold a division the extractor had performed, wrote that into the
  prompt, and declined the row. Then I opened the source document, which says:
  "Normalize that to cost per benchmark point and DeepSeek costs **$0.0076 per
  point** versus an index average of $0.0637." The writer did the division and
  published it. The figure is sound, the axis is sound, and the only thing
  wrong is that the quote stops before the sentence that states them. The
  decline is undone and the prompt now says to quote both sentences.

  Recorded rather than quietly corrected, because the wrong version was
  plausible - it explained the data, it matched an existing rule, and nothing
  in the row disagreed with it. What disagreed with it was the source, which I
  had not opened.
"""

from __future__ import annotations

from judge.extract.schema import _BOARD_ENTRIES_DESC, BoardEntry


def field(name: str) -> str:
    return BoardEntry.model_fields[name].description or ""


class TestEveryEntryStandsOnItsOwnQuote:
    def test_the_entries_field_says_the_rest_of_the_document_is_not_evidence(self):
        assert "READ BACK AGAINST THIS QUOTE ALONE" in _BOARD_ENTRIES_DESC

    def test_several_entries_in_one_section_are_allowed_by_name(self):
        """⚠ THE OPENING LINE USED TO SAY "One entry per section", and the most
        common shape in the review is a quote that correctly produces three -
        "classification, short summaries, and simple extraction". A rule that
        forbids the right answer is worse than no rule, because the parts of it
        that are right get discounted with it."""
        assert "One entry per section" not in _BOARD_ENTRIES_DESC
        assert "three in one section" in _BOARD_ENTRIES_DESC

    def test_it_carries_the_measurement_rather_than_an_assertion(self):
        """Rule 11: a count in prose is a measurement with a date, or it is a
        defect. The prompt is prose the extractor reads, and an unsourced "this
        often goes wrong" is exactly the sentence a model discounts."""
        assert "Measured 2026-09-22" in _BOARD_ENTRIES_DESC
        assert "56 quotes" in _BOARD_ENTRIES_DESC


class TestAQuoteAboutSeveralModelsIsSplitBetweenThem:
    def test_the_haiku_case_is_named(self):
        assert "Haiku for routing, Sonnet for reasoning" in _BOARD_ENTRIES_DESC

    def test_it_says_to_read_whose_clause_each_one_is(self):
        assert "whose clause each one is" in _BOARD_ENTRIES_DESC


class TestAListIsReadWhole:
    def test_the_under_extraction_case_is_named(self):
        assert "NAME EVERY ITEM IN A LIST" in _BOARD_ENTRIES_DESC
        assert "cybersecurity" in _BOARD_ENTRIES_DESC

    def test_it_says_why_the_quiet_defect_is_the_dangerous_one(self):
        """Rule 4 pointed one stage earlier: nothing on the page is wrong, so
        nothing prompts anybody to look."""
        assert "quieter defect" in _BOARD_ENTRIES_DESC


class TestTheAxisIsWhatWasMeasured:
    def test_the_slug_field_says_so_in_those_words(self):
        text = field("slug")
        assert "THE AXIS IS WHAT WAS MEASURED" in text
        assert "NEVER WHICH WORDS SIT BESIDE THE FIGURE" in text

    def test_it_gives_all_four_worked_cases(self):
        text = field("slug")
        for case in ("10.59M tokens", "118K per task", "about 75 minutes",
                     "$0.013880"):
            assert case in text, case

    def test_it_offers_the_axis_to_use_instead_of_the_wrong_familiar_one(self):
        """⚠ A RULE THAT ONLY FORBIDS LEAVES THE MODEL WITH THE WRONG ANSWER
        AND NO RIGHT ONE, and the wrong answer here is the familiar slug that
        already has a page. Naming `task-duration` is what makes declining
        `time-to-first-token` an available move."""
        text = field("slug")
        assert "task-duration" in text
        assert "cost-per-task" in text

    def test_the_unit_is_the_one_the_figure_is_written_in(self):
        text = field("unit")
        assert "THE UNIT THE FIGURE IS ACTUALLY WRITTEN IN" in text
        assert "40 minutes per task" in text

    def test_the_unit_field_says_code_now_checks_it(self):
        """The claim in the prompt has to be true, or it is the next thing
        somebody finds out is not. `metric_withholding` compares the two, and
        `test_a_unit_that_cannot_hold_its_figure.py` holds it to that."""
        assert "withholds the row when they disagree" in field("unit")


class TestTheQuoteIsCutToContainItsFigure:
    def test_the_value_field_says_to_choose_the_quote_that_carries_it(self):
        text = field("value_verbatim")
        assert "CHOOSE THE QUOTE THAT DOES" in text
        assert "cost-per-benchmark-point" in text

    def test_it_says_to_quote_both_sentences_where_they_split(self):
        assert "QUOTE BOTH" in field("value_verbatim")

    def test_the_older_rule_against_computing_a_value_is_still_there(self):
        """The new text replaced a wrong example, not this rule."""
        assert "COPY IT, NEVER COMPUTE IT" in field("value_verbatim")

    def test_the_entries_field_carries_the_verified_two_sentence_case(self):
        """From the source document, not from the row: the `reasoning` entry on
        "targeted enhancements for code generation, debugging…" was supported
        by a different paragraph of the same post."""
        assert "multi-step reasoning" in _BOARD_ENTRIES_DESC
        assert "two entries with two quotes" in _BOARD_ENTRIES_DESC


class TestAnExperimentIsNotThePublishedFigure:
    def test_basis_distinguishes_a_persons_run_from_a_spec_sheet_axis(self):
        """The reviewer's closing instruction: "for ttft, tps etc some quotes
        will be like for a particular experiment task they carried on and its
        score is mentioned while some other will be the exact one published so
        treat them the way they are expressed". The distinction is not only
        `reported` vs `stated` - the AXIS differs too, which is what the old
        text left out."""
        text = field("basis")
        assert "THE AXIS DIFFERS, NOT ONLY THE BASIS" in text
        assert "8.566" in text

    def test_a_figure_is_a_quantity(self):
        """"much cheaper", "much faster", "Blazing Fast" and "token burn
        remained low" were all stored as metric figures."""
        text = field("section")
        assert "A FIGURE IS A QUANTITY" in text
        assert "Blazing Fast" in text
