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
        assert "setSp({ ids: trimmed.join(',') })" in code()

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


class TestEveryRowRenders:
    """⚠ TWO VERSIONS BEFORE THIS ONE, BOTH REJECTED ON SIGHT.

    First I hid any row whose cells were all equal and printed a footnote
    naming them. On a real comparison that hid three of six rows: the table
    lost half its content and gained a sentence ABOUT the table.

    Then I marked those rows `same` instead. That was still chrome on a page
    about evidence — @parvathibntglobal read `Discussed undersame  nothing yet
    nothing yet` and asked why the tag was there at all. The honest answer was
    that the tag was labelling a row which should never have said "nothing
    yet" in the first place (see below), so it was decoration drawing
    attention to a bug.

    A reader comparing two columns can see they match. The page does not need
    to say so.
    """

    def test_every_row_is_rendered(self):
        assert "rendered.map((r) => (" in code()

    def test_no_row_is_filtered_out(self):
        assert "differing" not in code()

    def test_there_is_no_marker_on_the_row_label(self):
        assert "r.same" not in code()
        assert "cellText" not in code()

    def test_there_is_no_footnote_about_the_table(self):
        """⚠ A PAGE ABOUT EVIDENCE MUST NOT SPEND A PARAGRAPH ON ITS OWN
        LAYOUT."""
        assert "not shown because every" not in source()
        assert "Every row came back the same for all" not in source()


class TestDiscussedUnderReadsTheBoardAndNotTheDeadChain:
    """⚠ THE ROW SAID "nothing yet" FOR EVERY MODEL, ALWAYS, AND IT WAS NOT
    ABOUT THE MODELS.

    `reported.capabilities` carried `cell.capability_key` — the CLOSED twelve
    from the first plan. Every cell on the board is `insufficient` and e5.5
    writes none at all, so the row was structurally empty:

        Claude Opus 5   evidence.capabilities   []       <- what it read
        Claude Opus 5   discovered.capabilities 63 items <- what was there

    That is #438's defect on a second page: a row sourced from a chain that
    produces nothing, rendering as a fact about the models rather than about
    our own machinery.
    """

    def test_the_row_reads_the_discovered_vocabulary(self):
        assert "m.reported?.discovered?.capabilities" in code()

    def test_it_no_longer_reads_the_closed_twelve(self):
        assert "m.reported?.capabilities" not in code()

    def test_the_dead_key_is_removed_from_the_payload(self):
        """⚠ REMOVED RATHER THAN LEFT UNREAD (rule 9). A payload key nothing
        consumes is the same orphan one layer down, and it looks wired from
        either end."""
        assert '"capabilities": list((m.get("evidence")' not in app()

    def test_each_capability_carries_its_report_count(self):
        """A list of names says which things were discussed; the counts say
        how much, and on a comparison that is the difference."""
        assert "reports: c.reports" in code()


class TestAListIsListedRatherThanTruncated:
    """⚠ THREE VERSIONS, AND THE FIRST TWO WERE BOTH WRONG.

    `mets.slice(0, 3)` showed three of nine and read as three — a count with no
    denominator (rule 7). Replacing it with `+6 more` in a `title` attribute
    fixed the honesty and not the usefulness: **a tooltip is not openable**, it
    is invisible on touch, and on a comparison page the list IS the content.

    Semicolon-joined prose was the other half: `reasoning; code generation;
    long context` beside the same shape in the next cell cannot be read across,
    because the eye has no line to follow. A comparison of lists wants lists.
    """

    def test_nothing_is_cut(self):
        assert "slice(0, max)" not in code()
        assert "+{rest} more" not in source()

    def test_no_list_hides_itself_in_a_title_attribute(self):
        """A hover is not a control. It does not exist on touch, it cannot be
        linked to, and it cannot be read beside the column next to it."""
        assert "title={items.slice" not in code()

    def test_every_item_gets_its_own_line(self):
        assert "shown.map(line)" in code()
        assert "<li key={i}" in code()

    def test_the_overflow_is_a_control_a_reader_can_press(self):
        """⚠ THE THIRD VERSION, AND THE SECOND WAS THE ONE @parvathibntglobal
        rejected. `+4 more` in a `title` is not openable - invisible on touch,
        unreachable by keyboard. `<details>` is a button, and the rest of the
        list renders in the cell where it belongs.

        The cut is about HEIGHT, not importance: Claude Opus 5 carries 63
        discovered capabilities, and rendering all of them inline makes one
        table row 63 lines tall and buries every row under it."""
        assert "<details>" in code()
        assert "show the other {rest.length}" in code()
        assert "{rest.map((x, i) => line(x, i + upTo))}" in code()

    def test_the_count_counts_all_of_them_not_the_shown_ones(self):
        """Rule 7. A count that shrank to match what is displayed would make
        the one comparable number on the cell describe the layout."""
        assert "{items.length} {plural}" in code()

    def test_the_count_leads_the_cell(self):
        """⚠ THE COMPARABLE PART. Two cells of ten lines look alike until you
        count them; "12 capabilities" against "3 capabilities" is the
        difference a reader is looking for before reading either list."""
        assert "{items.length} {plural}" in code()

    def test_the_unit_is_named_per_row_rather_than_generic(self):
        """"6 items" says nothing. Jobs, capabilities and metrics are three
        different things and the row already knows which."""
        for unit in ('unit="job"', 'unit="capability"', 'unit="metric"'):
            assert unit in code(), unit

    def test_an_empty_list_renders_nothing_and_the_row_says_so_itself(self):
        """Each row already has its own empty sentence — "no job named yet",
        "nothing yet", "none". A second empty state inside the helper would
        make two of them disagree."""
        assert "if (!items.length) return null" in code()


class TestTheEntryCountsTravelWithTheAxisCounts:
    """⚠ THE LIST LENGTHS ARE AXES AND THE PAGE SHOWED ONLY THOSE (rule 7).

    "63 capabilities" is 63 different things people discussed. It says nothing
    about how much was said, and the two numbers pull in opposite directions:

        Claude Opus 5   capability   156 entries over  64 axes
        GPT 6 Astra     capability    83 entries over  33 axes
        Claude Opus 5   metric        38 entries over  24 axes
        GPT 6 Astra     metric        61 entries over  40 axes

    63 axes from 70 entries is a broad, thinly-evidenced picture; 12 from 70 is
    narrow and heavily discussed. With only the axis count on screen, the
    broader model reads as the better-covered one whatever sits behind it.
    """

    def test_the_payload_carries_the_total_and_the_split(self):
        assert '"entries": (m.get("board") or {}).get("entries", 0)' in app()
        assert '"entries_by_section"' in app()

    def test_it_reads_the_rosters_own_counts_rather_than_recomputing(self):
        """⚠ TWO QUERIES FOR ONE FACT DRIFT, and the drift is invisible because
        both look right alone. The models list and this page must not disagree
        about the same model."""
        assert '(m.get("board") or {}).get("sections")' in app()

    def test_the_row_is_on_the_page(self):
        assert "'Entries on the board'" in code()

    def test_it_names_the_sections_rather_than_only_totalling(self):
        """"210 entries" does not say where they are. "156 capability, 38
        metric, 29 best-for" is the sentence the row exists for."""
        assert "order = ['capability', 'metric', 'best_for']" in code()

    def test_an_unknown_section_is_still_counted(self):
        """⚠ A NEW SECTION WOULD OTHERWISE VANISH FROM A BREAKDOWN whose total
        still counts it, so the two numbers on one line would disagree."""
        assert "Object.keys(by).filter((k) => !order.includes(k))" in code()

    def test_no_entries_says_none_rather_than_zero_parts(self):
        assert "if (!total) return" in code()


class TestTheFirstRowNamesWhatTheEvidenceIs:
    """⚠ IT SAID "DOCUMENTS" AND MEANT SOMETHING ELSE, which @parvathibntglobal
    caught by asking whether evidence does not also come from threads and
    comments. It does. Measured for Claude Opus 5:

        hackernews   26 replies      devto   21 articles
        reddit       16 posts        github  10 posts + 3 replies
        blog          2 articles

    29 of 92 are replies. "92 documents" reads as 92 articles - jargon, and an
    overstatement in the direction that flatters the board's coverage.
    """

    def test_the_row_is_not_called_documents(self):
        assert "['Documents'," not in code()
        assert "['Posts and comments'," in code()

    def test_replies_are_counted_apart_from_posts(self):
        """A comment under somebody else's post and a post somebody wrote are
        not the same act - the board's own `is_self_post` exists for it."""
        assert '"replies": replies' in app()
        assert "p.replies || 0" in code()

    def test_the_platform_split_is_carried(self):
        """⚠ THE COMPARATIVE FACT. One model discussed across five platforms
        and another across one are different kinds of evidence, and
        `cell.platform_count` already treats that as load-bearing for
        `n_eff`."""
        assert '"platforms": [{"source": src, "documents": n} for src, n in platforms]' in app()
        assert "p.platforms || []" in code()

    def test_the_denominator_row_uses_the_same_words(self):
        """⚠ TWO NAMES FOR ONE POPULATION ON ADJACENT ROWS is how a reader
        concludes they are two populations. The "out of" row said "documents"
        while the row above it said something else."""
        assert "posts and comments</span>" in code()

    def test_the_declined_entries_are_excluded_from_both_new_queries(self):
        """A declined entry is not evidence, and the polarity counts beside
        these already exclude it. Two figures on one row counting different
        populations is the defect this whole page keeps guarding against."""
        block = app()[app().index('"WHERE b.model_version_id = %s "'):]
        assert block.count("ruling IS DISTINCT FROM 'declined'") >= 2


class TestTheListIsColumnsAndAMarkRatherThanProse:
    """⚠ THREE WORDS PER ROW ON UP TO 33 ROWS IN THREE COLUMNS.

    Each line read `Reasoning — 5 reports  3 of 5 positive`. "reports" and
    "positive" repeated on every line of every column, line lengths varied
    with the name so the eye had no edge to run down, and the numbers being
    compared were buried in the sentence.

    Per the visualization guidance, positive/neutral/negative is an
    ordered-scale share and its default form is a stacked bar with a neutral
    midpoint — not a number, and not words. The repeated words moved to a
    header said once, the counts became a column, and the split became a mark.
    """

    def test_the_repeated_words_are_in_a_header_not_on_each_row(self):
        assert '<span className="cmp-line-n">reports</span>' in code()
        assert "how it went" in code()

    def test_the_polarity_is_a_bar(self):
        assert "function PolarityBar({ counts })" in code()
        assert "(x.n / total) * 100" in code()

    def test_the_segments_are_separated_by_a_gap(self):
        """⚠ IDENTITY MUST NOT REST ON HUE ALONE. A reader who cannot tell the
        two poles apart still sees three segments, because the guidance asks
        for a 2px surface gap between stacked fills."""
        block = code()[code().index("function PolarityBar("):]
        block = block[:block.index("function axisPolarity(")]
        assert "gap: 2" in block

    def test_the_bar_has_a_text_alternative(self):
        """A mark with no label is color-alone. `aria-label` carries the same
        split the title does, so a screen reader gets the numbers."""
        assert 'role="img"' in code()
        assert "aria-label={segments.map(" in code()

    def test_the_exact_counts_and_their_denominator_are_on_the_title(self):
        """Rule 7, kept off the line: `reports` counts documents and the split
        counts entries, and one document can carry nine. A proportion has no
        denominator to contradict the number beside it."""
        assert "board entr${total === 1 ? 'y' : 'ies'}" in code()

    def test_zero_counts_are_not_drawn(self):
        assert "filter(([key]) => counts[key] > 0)" in code()

    def test_the_bar_uses_the_repositorys_own_polarity_tokens(self):
        """`--fail` and `--pass` with a neutral grey between them: a diverging
        pair with a grey midpoint, which is the rule for polarity. Validated
        against the dark surface — CVD ΔE 8.5 protan, normal-vision 16.7,
        contrast ≥ 3:1 on all three."""
        assert "['negative', 'var(--fail)']" in code()
        assert "['positive', 'var(--pass)']" in code()
        assert "['neutral', 'var(--text-3)']" in code()

    def test_unrecorded_is_drawn_as_neutral_but_named_apart(self):
        """Rule 6. It shares the grey because a reader cannot act on the
        difference in a 64px bar, and it keeps its own word in the title where
        they can."""
        assert "['unrecorded', 'var(--text-3)']" in code()


class TestThePluralIsNotStringConcatenation:
    def test_the_two_units_that_break_are_mapped(self):
        """⚠ "15 capabilitys" WAS ON THE PAGE. `unit + "s"` is not English,
        and the unit it breaks on is the one with the most rows."""
        assert "capability: 'capabilities'" in code()

    def test_a_single_item_keeps_the_singular(self):
        assert "items.length === 1 ? unit :" in code()

    def test_an_unmapped_unit_still_gets_something(self):
        """A missing key must not render `undefined`; the naive plural is a
        worse answer than the map and a better one than nothing."""
        assert "PLURALS[unit] || `${unit}s`" in code()
