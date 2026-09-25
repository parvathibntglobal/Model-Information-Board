"""The category page lists models; a model's page holds every report it has.

WHAT THE CAPABILITY PAGE SHOWED ON 2026-09-18, and why it was a slice nobody
had chosen:

    Board / Capabilities / Reasoning
    MODELS WITH EVIDENCE            20 rows, every one badged "contested"
    REPORTS                         9 quote blocks

Two independent numbers multiplied into that 9. `board_sections` capped the
quote list at 12 for payload size, and `quotes()` in views.js groups those 12
BY DOCUMENT - so the page showed however many documents twelve newest quotes
happened to span, out of the 43 reports the section holds. Measured the same
day, over every discovered section:

    best_for/coding-agent        6 blocks shown, 64 documents held
    capability/instruction-…     6 blocks shown, 31 documents held
    capability/reasoning         9 blocks shown, 43 documents held

Neither number was wrong on its own and nothing on the page said a slice was
being shown, which is rule 7's shape exactly: a real value answering a question
it was not asked.

AND EVERY BADGE ON THAT LIST WAS THE SECTION'S. `commonFields` computed one
evidence state per section and stamped it onto every model row (`s: st`). Over
the 414 model rows the best-for and capability pages render, 173 (42%) carried
a state that was not their own and 48 said "corroborated" above a single voice
- the one word this board must not be wrong about, and the same failure as the
one `test_one_voice_is_not_three_reports` is named for, one level down.

THE THIRD THING, which is the one with no number in it. `best_for` filters out
negative reports, correctly - a surface promising suitability cannot be filled
by evidence of the opposite. But a model page headed "every report the board
holds" while that filter silently dropped four of them is an absence we CAUSED
reading as one we FOUND, which is rule 4. 19 negative best-for rows across 12
(slug, model) pairs; 8 of those pairs have a row for this to appear on, and 4
do not - those four models are named nowhere on the best-for surface, which
this change does not fix and does not hide.

METRICS IS NOW PART OF THIS, AND IT WAS THE SECTION THAT NEEDED IT MOST.
This file used to end: *"METRICS IS NOT PART OF THIS. Its page is a figure
table rather than a model list."* That was true and it was the defect. On
2026-09-21 a reader met this, on one axis, in one column, under one unit:

    Claude Fable 5.1   $0.25 / MTok   stated   USD per 1M tokens
    Claude Fable 5.1   $50   / MTok   stated   USD per 1M tokens

They do not disagree. One is a cache read price and the other an output price,
and only the quote said which. Measured the same day over the 269 published
figures, **34 (axis, model) cells hold two or more DIFFERENT figures** like
that, the worst being six values over nineteen rows.

The cause was one line in `db.js`: `commonFields` builds `rows` from
`item.models` for every section, and `DB.mets` overwrote it with the figure
table - so metrics discarded the model level rather than merely not using it,
which is why `vJobModel` and `vCapModel` had no `vMetModel` beside them.

AND 62 OF 84 AXES HOLD EXACTLY ONE MODEL. A table is a claim that its rows are
comparable; on three quarters of these pages there was nothing to compare.
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
STORE = ROOT / "judge" / "store" / "board_entries.py"
DB = ROOT / "web" / "src" / "board" / "db.js"
VIEWS = ROOT / "web" / "src" / "board" / "views.js"
BOARDVIEW = ROOT / "web" / "src" / "board" / "BoardView.jsx"
ROUTE = ROOT / "web" / "src" / "routes" / "Board.jsx"


def _store() -> str:
    return STORE.read_text(encoding="utf-8")


def _store_code() -> str:
    """`board_entries.py` with every comment and string literal removed.

    THE MENTION-VERSUS-USE TRAP, and this is the third time this repository has
    written it down - `test_best_for_needs_a_positive_report` says it about
    `sec(` lines and `TestTheQuoteCapIsGone` says it below about the cap. A
    check that greps a whole file fails on its own documentation, and the
    documentation is where a rule is EXPLAINED, so the better the comment the
    more likely the check.

    Dropping `#` lines is not enough here: `board_sections`' docstring argues
    at length about corroboration, and a docstring is not a comment token.
    `tokenize` knows the difference; a line-prefix test does not.
    """
    import io
    import tokenize

    out = []
    for tok in tokenize.generate_tokens(io.StringIO(_store()).readline):
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        out.append(tok.string)
    return "\n".join(out)


def _db() -> str:
    return DB.read_text(encoding="utf-8")


def _views() -> str:
    return VIEWS.read_text(encoding="utf-8")


# ── a fake connection, so these run without a database ───────────────────────
#
# Two queries now: the main read, and the count of best-for negatives the main
# read filters out. They are told apart by a fragment of their SQL rather than
# by call order, because an order-dependent fake passes for the wrong reason
# the moment somebody reorders the function.
class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class FakeConn:
    """`hidden` rows are (slug, model_key, model_label, report_count)."""

    def __init__(self, rows, hidden=()):
        self._rows, self._hidden = rows, hidden

    def execute(self, sql, params=None):
        if "polarity = 'negative'" in sql and "count(DISTINCT" in sql:
            return _Rows(list(self._hidden))
        return _Rows(list(self._rows))


def row(section="capability", slug="reasoning", *, mv="mv_a", doc="d1",
        author="au_1", polarity="positive", quote=None, value=None,
        registry="mv_a", label="Model A"):
    """One `board_entry` row in the column order `board_sections` selects.

    ⚠ A METRIC ROW'S DEFAULT QUOTE CONTAINS ITS FIGURE, and that is a fixture
      correction rather than a convenience. The default used to be the literal
      `"q"` for every row, so a metric fixture asserted things about a figure
      whose quote did not contain it - a row the read path now withholds and
      which `quote_verified` never described in the first place. A test whose
      fixture cannot occur in the database proves nothing about the database.

      Pass `quote=` explicitly to build the unsupported case on purpose; the
      gate's own tests do exactly that.
    """
    if quote is None:
        quote = f"measured {value} on this axis" if value else "q"
    return (section, slug, "Reasoning", "def", None, value, None,
            mv, doc, quote, polarity, "2026-09-18", "https://e.com/1", author,
            "vendor/model-a", label, registry)


def build(rows, hidden=()):
    from judge.store.board_entries import board_sections
    return board_sections(FakeConn(rows, hidden))


class TestTheModelRowCarriesItsOwnNumbers:
    def test_reports_and_voices_are_both_emitted_and_can_differ(self):
        # Two documents by one author: two reports, one voice. The row has to
        # be able to say both, because on 22 of 636 groups they differ and a
        # reader choosing between models is told the wrong thing by either
        # number standing alone.
        out = build([
            row(doc="d1", author="au_1"),
            row(doc="d2", author="au_1"),
        ])
        model = out["capability"][0]["models"][0]
        assert model["reports"] == 2
        assert model["voices"] == 1

    def test_two_comments_by_one_person_are_one_voice(self):
        out = build([
            row(doc="d1", author="au_1"),
            row(doc="d2", author="au_2"),
            row(doc="d3", author="au_2"),
        ])
        model = out["capability"][0]["models"][0]
        assert (model["reports"], model["voices"]) == (3, 2)

    def test_the_polarity_set_is_the_models_own_not_the_sections(self):
        # The input to the badge. Model B is reported only positively; the
        # SECTION holds both polarities, which is what used to decide B's
        # label.
        out = build([
            row(mv="mv_a", registry="mv_a", label="A", doc="d1",
                author="au_1", polarity="negative"),
            row(mv="mv_b", registry="mv_b", label="B", doc="d2",
                author="au_2", polarity="positive"),
        ])
        models = {m["model_label"]: m for m in out["capability"][0]["models"]}
        assert models["A"]["polarities"] == ["negative"]
        assert models["B"]["polarities"] == ["positive"]

    def test_polarities_arrive_sorted_so_two_identical_rows_render_alike(self):
        out = build([
            row(doc="d1", author="au_1", polarity="positive"),
            row(doc="d2", author="au_2", polarity="negative"),
        ])
        assert out["capability"][0]["models"][0]["polarities"] == [
            "negative", "positive"]


class TestOneModelIsOneRow:
    def test_a_model_named_under_both_id_shapes_groups_once(self):
        # `board_entry.model_version_id` holds the canonical id when a run
        # names its own subject and the internal key when a model was resolved
        # out of a thread. Grouping on the raw column made that two rows for
        # one model - 0 of 640 groups today, which is why this is a test and
        # not an incident.
        out = build([
            row(mv="vendor/model-a", registry="mv_a", doc="d1", author="au_1"),
            row(mv="mv_a", registry="mv_a", doc="d2", author="au_2"),
        ])
        models = out["capability"][0]["models"]
        assert len(models) == 1
        assert models[0]["reports"] == 2
        assert models[0]["model_key"] == "mv_a"

    def test_the_raw_id_is_still_sent_under_its_own_name(self):
        # `modelName()` in db.js falls back to splitting `model_version_id` on
        # "/" when no label arrives. Quietly replacing it with the internal key
        # would print `mv_a2b4f7fc…` exactly where a model name belongs, which
        # is the substitution #278 was about.
        out = build([row(mv="vendor/model-a", registry="mv_a")])
        model = out["capability"][0]["models"][0]
        assert model["model_version_id"] == "vendor/model-a"
        assert model["model_key"] == "mv_a"

    def test_an_unresolvable_id_keys_on_itself_rather_than_on_nothing(self):
        # Rule 6: a missing registry row does not make the model disappear.
        out = build([row(mv="mv_ghost", registry=None)])
        model = out["capability"][0]["models"][0]
        assert model["model_key"] == "mv_ghost"

    def test_every_quote_carries_the_key_its_model_row_groups_on(self):
        # The drill-down page is made by partitioning the quote list with this
        # field. Matching on `model_version_id` instead would lose the quotes
        # of any model named under both shapes.
        out = build([
            row(mv="vendor/model-a", registry="mv_a", doc="d1"),
            row(mv="mv_a", registry="mv_a", doc="d2"),
        ])
        assert {q["model_key"] for q in out["capability"][0]["quotes"]} == {"mv_a"}


class TestTheQuoteCapIsGone:
    def test_every_quote_reaches_the_payload(self):
        # 20 rows, one per document, all of them returned. The cap was 12 and
        # it bit on 8 of 222 best-for and capability sections - the whole top
        # of the board.
        out = build([row(doc=f"d{i}", author=f"au_{i}") for i in range(20)])
        item = out["capability"][0]
        assert len(item["quotes"]) == 20
        assert item["quote_count"] == 20
        assert item["reports"] == 20

    def test_the_literal_cap_is_not_in_the_source(self):
        # CODE LINES ONLY. The comment where the cap used to be quotes it, to
        # explain what it did and what removing it cost - and a check that
        # cannot tell a mention from a use fails on its own documentation.
        # Third time that trap has been written down here.
        assert 'len(bucket["quotes"])<12' not in _store_code().replace("\n", "")

    def test_the_section_badge_now_sees_every_polarity(self):
        # The cap truncated the list `evidenceState` reads polarity off, so a
        # section whose only negative report was the 13th newest was labelled
        # from an incomplete set. Not a separate fix - it falls out of this one.
        rows = [row(doc=f"d{i}", author=f"au_{i}") for i in range(14)]
        rows[-1] = row(doc="d99", author="au_99", polarity="negative")
        quotes = build(rows)["capability"][0]["quotes"]
        assert "negative" in {q["polarity"] for q in quotes}


class TestNothingIsHiddenSoNothingIsCountedAsHidden:
    """`best_for` filtered problem reports out until 2026-09-25 and counted what
    it hid (`hidden_negative_reports`, `suppressed_models`). Nothing is hidden
    now - those models are the third group - so both fields are gone rather
    than left emitting zeros nobody reads (rule 9)."""

    def test_the_payload_carries_neither_field(self):
        out = build([row(section="best_for", slug="coding-agent", polarity="negative")])
        item = out["best_for"][0]
        assert "suppressed_models" not in item
        assert "hidden_negative_reports" not in item["models"][0]

    def test_no_code_still_reads_them(self):
        for src in (_store_code(), _db(), _views()):
            assert "hidden_negative_reports" not in src
            assert "suppressed_models" not in src
        assert "function suppressedNote(" not in _views()
        assert "hiddenNote" not in _views()


class TestTheBadgeIsTheModelsOwn:
    def test_the_section_state_is_no_longer_stamped_on_every_row(self):
        js = _db()
        assert "\n      s: st,\n" not in js, (
            "the section's evidence state on every model row is the defect: "
            "173 of 414 rows carried a state that was not their own"
        )

    def test_each_row_computes_its_state_from_its_own_numbers(self):
        js = _db()
        assert "s: evidenceState(" in js
        assert "m.voices ?? m.reports" in js
        assert "(m.polarities || []).map((polarity) => ({ polarity }))" in js

    def test_there_is_still_exactly_one_definition_of_the_state(self):
        # A second copy of the rule in Python would be two definitions of
        # "corroborated" that can drift. `board_sections` sends the INPUT.
        js = _db()
        assert js.count("function evidenceState(") == 1
        # Code only. The store's comments and docstring discuss the verdict at
        # length, precisely because they explain why it is NOT computed there.
        code = _store_code()
        for word in ("corroborated", "contested", "one voice"):
            assert word not in code, (
                f"{word!r} in the store's CODE means the verdict was "
                f"reimplemented server-side; only its inputs belong there"
            )

    def test_a_payload_without_polarities_degrades_to_voices_not_to_none(self):
        # Rule 6 on a display: a missing value must not become a definite
        # claim that nobody discussed this model.
        assert "(m.polarities || [])" in _db()
        assert "(m.polarities).map" not in _db()


class TestTheRowSaysWhatItCounted:
    def test_both_numbers_are_on_the_row(self):
        js = _db()
        assert "report${m.reports === 1 ? '' : 's'}" in js
        assert "voice${(m.voices ?? m.reports) === 1 ? '' : 's'}" in js

    def test_the_report_count_carries_its_floor_marker(self):
        # An open vocabulary can name one section twice, so every report count
        # on this board is ">= N" until somebody merges the duplicates.
        assert "≥${m.reports}" in _db()

    def test_the_list_states_the_population_it_was_drawn_from(self):
        # Rule 7 on a page: "20 models" answers nothing without saying 20 of
        # what, counted how.
        js = _views()
        assert "function listIntro(item)" in js
        assert "model${n===1?'':'s'}, named in" in js
        assert "voice${voi===1?'':'s'}" in js

    def test_the_ordering_is_named_as_a_count(self):
        assert "which is a count" in _views()
        assert "and not a score" in _views()


class TestTheDrillDownExistsAndIsReachable:
    def test_the_category_page_no_longer_renders_a_quote_block(self):
        js = _views()
        for line in js.splitlines():
            if line.lstrip().startswith("//"):
                continue
            assert "quotes(c.qs)" not in line
            assert "quotes(j.qs)" not in line

    def test_both_category_pages_link_their_rows_to_a_model_page(self):
        js = _views()
        assert "ranked(c.rows,'capmodel:'+c.slug)" in js
        assert "ranked(j.rows,'jobmodel:'+j.slug)" in js

    def test_a_list_with_no_route_stays_inert(self):
        # A pointer over something that does nothing is the worse half of the
        # bug this fixes, so the affordance is conditional on the link.
        js = _views()
        assert "const go = route && r.key ?" in js
        assert "${go?' open':''}" in js

    def test_the_router_understands_both_drill_down_kinds(self):
        js = BOARDVIEW.read_text(encoding="utf-8")
        assert "kind === 'jobmodel' || kind === 'capmodel'" in js
        assert "kind === 'model'" in js

    def test_the_model_key_is_read_as_the_rest_of_the_path(self):
        # `model_version.id` is canonical for 166 of 1,249 board rows, so
        # `anthropic/claude-fable-5-1` is one key and two segments. Reading
        # `parts[2]` truncates it to `anthropic`, finds no model, and sends the
        # visitor back to the category page - which looks like a model nobody
        # discussed rather than a broken link.
        js = ROUTE.read_text(encoding="utf-8")
        assert "parts.slice(2).join('/')" in js
        js2 = BOARDVIEW.read_text(encoding="utf-8")
        assert "arg.indexOf(':')" in js2
        assert "arg.slice(j + 1)" in js2

    def test_an_unknown_model_key_returns_the_category_page(self):
        js = _views()
        assert "if(!row) return kind === 'job' ? vJob(item.slug) : vCap(item.slug)" in js

    def test_the_page_links_out_to_the_models_whole_corpus(self):
        # This page is scoped to one category. Saying "every report" without
        # naming that scope would be the page meaning one thing and saying
        # another.
        js = _views()
        assert "across every job, capability and metric" in js

    def test_a_model_with_no_readable_quote_renders_the_absence(self):
        js = _views()
        assert "The board holds no readable report" in js
        assert "not a page" in js


class TestThePolaritySplitOnTheCapabilityRow:
    """How many of a model's reports said good things, and how many bad.

    The badge says "contested"; it does not say whether that is 10 positive
    against 2 negative or the reverse, and those are different findings about
    the same model. Counted in REPORTS, the same unit as the count beside it.
    """

    def test_the_split_counts_reports_not_quotes(self):
        # Two quotes in ONE document is one positive report. Counting quotes
        # would put the inflation this suite's sibling is named for back on
        # the row, one column along.
        out = build([
            row(doc="d1", author="au_1", polarity="positive"),
            row(doc="d1", author="au_1", polarity="positive"),
            row(doc="d2", author="au_2", polarity="negative"),
        ])
        model = out["capability"][0]["models"][0]
        assert model["reports"] == 2
        assert model["report_split"]["positive"] == 1
        assert model["report_split"]["negative"] == 1

    def test_a_report_that_says_both_is_counted_under_each_and_named(self):
        out = build([
            row(doc="d1", author="au_1", polarity="positive"),
            row(doc="d1", author="au_1", polarity="negative"),
        ])
        model = out["capability"][0]["models"][0]
        assert model["reports"] == 1
        assert model["report_split"] == {
            "positive": 1, "negative": 1, "both": 1, "neutral": 0}

    def test_the_identity_a_reader_can_check_holds(self):
        # positive + negative - both + neutral == reports. It is the only
        # reason the row is allowed to show two numbers that exceed a third.
        out = build([
            row(doc="d1", author="au_1", polarity="positive"),
            row(doc="d1", author="au_1", polarity="negative"),
            row(doc="d2", author="au_2", polarity="positive"),
            row(doc="d3", author="au_3", polarity="neutral"),
        ])
        m = out["capability"][0]["models"][0]
        sp = m["report_split"]
        assert sp["positive"] + sp["negative"] - sp["both"] + sp["neutral"] == m["reports"]

    def test_neutral_is_carried_so_a_neutral_only_row_says_something(self):
        # 24 of 297 groups are neutral-only. Without this they would render
        # "0 positive, 0 negative" over two real reports.
        out = build([
            row(doc="d1", author="au_1", polarity="neutral"),
            row(doc="d2", author="au_2", polarity="neutral"),
        ])
        assert out["capability"][0]["models"][0]["report_split"] == {
            "positive": 0, "negative": 0, "both": 0, "neutral": 2}

    def test_positive_and_negative_are_always_named_zero_included(self):
        # The list is ORDERED on these two numbers now, so "0 negative" is the
        # evidence for where a row sits rather than noise. Neutral stays
        # conditional.
        js = _db()
        assert "`${sp.positive || 0} positive`, `${sp.negative || 0} negative`" in js
        assert "if (sp.neutral) parts.push(" in js

    def test_both_is_appended_only_where_it_applies(self):
        js = _db()
        assert "if (sp.both) parts.push(" in js

    def test_the_split_is_its_own_line_rather_than_more_words_in_the_state(self):
        # `.right` is white-space:nowrap and `.st` already carries two counts
        # and a label; a fourth clause in it pushes the row past a phone.
        js = _views()
        assert 'r.sp ? `<span class="split">${esc(r.sp)}</span>` : \'\'' in js
        css = (ROOT / "web" / "src" / "styles" / "board.css").read_text(encoding="utf-8")
        assert ".rank .split{display:block" in css

    def test_the_split_is_not_colour_coded(self):
        # Green for positive and red for negative would make the row a
        # verdict. Capability is deliberately not polarity-filtered because a
        # bad result is evidence of the same standing as a good one.
        css = (ROOT / "web" / "src" / "styles" / "board.css").read_text(encoding="utf-8")
        rule = css[css.index(".rank .split{"):]
        rule = rule[: rule.index("}")]
        for token in ("--pass", "--fail", "green", "red"):
            assert token not in rule

    def test_what_both_means_is_explained_once_and_only_where_there_is_one(self):
        js = _views()
        assert "const anySplit = (item.rows || []).some(r => r.sp)" in js
        assert "counts a report under every polarity it states" in js


class TestTheOrderingIsThreeGroups:
    """At least one positive, then neutral-only, then negatives and none
    positive. Within each group, report count; ties keep their position.
    Ordering by POSITIVE COUNT is still refused - see `listIntro`."""

    @staticmethod
    def _order(section, rows):
        return [m["model_label"] for m in build(rows)[section][0]["models"]]

    @staticmethod
    def _r(mv, doc, author, polarity):
        """One capability row for model `mv`, labelled with its own id."""
        return row(mv=mv, registry=mv, label=mv, doc=doc, author=author, polarity=polarity)

    def test_one_positive_goes_above_any_number_of_negatives(self):
        rows = [row(mv="mv_a", registry="mv_a", label="A", doc=f"d{i}",
                    author=f"au_{i}", polarity="negative") for i in range(5)]
        rows.append(row(mv="mv_b", registry="mv_b", label="B", doc="d9",
                        author="au_9", polarity="positive"))
        assert self._order("capability", rows) == ["B", "A"]

    def test_neutral_only_goes_above_negatives_whatever_the_count(self):
        # capability/vision on 2026-09-25: under a two-group split, 8 negatives
        # sat above five neutral-only models. An absence of praise is not a
        # verdict worse than a complaint.
        rows = [row(mv="mv_a", registry="mv_a", label="EightNegatives", doc=f"d{i}",
                    author=f"au_{i}", polarity="negative") for i in range(8)]
        rows.append(row(mv="mv_b", registry="mv_b", label="OneNeutral", doc="d9",
                        author="au_9", polarity="neutral"))
        assert self._order("capability", rows) == ["OneNeutral", "EightNegatives"]

    def test_a_single_positive_is_enough_however_many_problems(self):
        # Claude Opus 5 on instruction-following: +1 and -11, first group.
        rows = [row(mv="mv_a", registry="mv_a", label="OnePlusElevenMinus", doc=f"d{i}",
                    author=f"au_{i}", polarity="negative") for i in range(11)]
        rows.append(row(mv="mv_a", registry="mv_a", label="OnePlusElevenMinus", doc="d99",
                        author="au_99", polarity="positive"))
        rows += [row(mv="mv_b", registry="mv_b", label="TwoNeutral", doc=f"n{i}",
                     author=f"au_n{i}", polarity="neutral") for i in range(2)]
        out = build(rows)["capability"][0]["models"]
        assert [m["model_label"] for m in out] == ["OnePlusElevenMinus", "TwoNeutral"]
        assert out[0]["group"] == "working"

    def test_within_a_group_the_order_is_still_report_count(self):
        # Not positive count: A has 1 positive in 3 reports, B 2 positives in 2.
        r = self._r
        rows = [r("A", "a1", "au_1", "positive"), r("A", "a2", "au_2", "negative"),
                r("A", "a3", "au_3", "negative"),
                r("B", "b1", "au_4", "positive"), r("B", "b2", "au_5", "positive")]
        assert self._order("capability", rows) == ["A", "B"]

    def test_a_tie_keeps_the_position_it_arrived_in(self):
        r = self._r
        rows = [r("Z", "z1", "au_1", "positive"), r("A", "a1", "au_2", "positive")]
        assert self._order("capability", rows) == ["Z", "A"]

    def test_best_for_follows_the_same_rule(self):
        rows = [row(section="best_for", slug="coding-agent", mv="mv_a", registry="mv_a",
                    label="Neg", doc="d1", author="au_1", polarity="negative"),
                row(section="best_for", slug="coding-agent", mv="mv_b", registry="mv_b",
                    label="Neu", doc="d2", author="au_2", polarity="neutral"),
                row(section="best_for", slug="coding-agent", mv="mv_c", registry="mv_c",
                    label="Pos", doc="d3", author="au_3", polarity="positive")]
        models = build(rows)["best_for"][0]["models"]
        assert [m["model_label"] for m in models] == ["Pos", "Neu", "Neg"]
        assert [m["group"] for m in models] == ["working", "neutral", "problems"]

    def test_metric_rows_carry_no_group(self):
        out = build([row(section="metric", slug="swe-bench", value="38.8%")])
        assert "group" not in out["metric"][0]["models"][0]

    def test_the_intro_states_the_rule_rather_than_calling_it_a_count(self):
        js = _views()
        assert "Listed in three groups" in js
        assert "a model enters the first group on a single positive report" in js
        assert "however many problem reports it also has" in js
        assert "extractor\u2019s reading of each quote" in js

    def test_the_boundary_is_drawn_on_the_page(self):
        js = _views()
        assert "function groupHead(g, n)" in js
        for title in ("Reported working", "Only neutral reports", "Reported problems"):
            assert title in js
        css = (ROOT / "web" / "src" / "styles" / "board.css").read_text(encoding="utf-8")
        assert ".rank-group{" in css

    def test_no_rendered_section_calls_any_of_this_a_ranking(self):
        rendered = [ln for ln in _views().splitlines()
                    if "sec(" in ln and not ln.lstrip().startswith("//")]
        assert rendered
        for line in rendered:
            assert "ranking" not in line


class TestBestForNowCarriesItsSplit:
    """`best_for` shows its problem reports since 2026-09-25, so its rows carry
    the same split as capability's. Metric still carries none."""

    def test_a_split_is_emitted_for_best_for(self):
        out = build([row(section="best_for", slug="coding-agent", polarity="negative")])
        assert out["best_for"][0]["models"][0]["report_split"]["negative"] == 1

    def test_no_split_is_emitted_for_metric(self):
        out = build([row(section="metric", slug="swe-bench", value="38.8%")])
        assert "report_split" not in out["metric"][0]["models"][0]

    def test_a_negative_reaches_a_best_for_row(self):
        out = build([row(section="best_for", slug="coding-agent", polarity="negative")])
        assert "negative" in out["best_for"][0]["models"][0]["polarities"]


class TestNothingIsLostOnTheWayDown:
    def test_a_quote_naming_no_model_is_counted_rather_than_dropped(self):
        # `board_entry.model_version_id` is nullable. Such a quote belongs to
        # no model row and so has no page to appear on; 0 of 1,249 rows are in
        # that state today, and losing them silently would be an absence of our
        # own making.
        js = _db()
        assert "orphans" in js
        assert "if (!key) { orphans.push(q); continue }" in js

    def test_the_page_says_so_only_when_there_are_some(self):
        js = _views()
        assert "function orphanNote(item)" in js
        assert "if(!n) return '';" in js


class TestTheMetricPathCarriesItsEvidence:
    """⚠ THIS REPLACED `TestMetricsDidNotMove`, ON ITS AUTHOR'S INSTRUCTION.

    That class pinned `vMet`, `mcard` and `groupFigures` byte-identical against
    HEAD, to show that #369 and #371 had not disturbed the metric page while
    changing the capability and best-for ones. It did that job. Grouping has now
    changed on purpose (#368), so the pin had become a test that the defect
    stays — and @anoojntglobal-sudo said in #370 to delete or rewrite it rather
    than work around it.

    ⚠ IT ALSO COULD NOT FAIL IN CI, WHICH IS WHY THIS DOES NOT COPY ITS METHOD.
      It compared the working tree against `git show HEAD:…`, so it caught an
      UNCOMMITTED edit and passed on every committed one — green in CI by
      construction. Same shape as #357, flagged by its own author in the same
      week. It caught this branch's edit locally, correctly, and would have said
      nothing about it once pushed.

    What replaces it is a property rather than a hash: a figure on the metric
    page must reach the reader with the sentence it came from. That is what #368
    is about — `43.5%` is indefensible alone and self-evidently wrong beside
    "the hard biology set from 43.5% to 56.5%" — and unlike a byte comparison it
    holds however the functions are rewritten, and fails wherever it runs.
    """

    def test_a_figure_reaches_the_page_with_its_quote(self):
        """The backend selected the quote and dropped it before the payload, so
        the page had a figure and no way to check it."""
        py = (ROOT / "judge" / "store" / "board_entries.py").read_text(encoding="utf-8")
        # A generous window rather than "to the next `)`": the block carries a
        # comment explaining why the quote is there, and the first `)` in it
        # belongs to that prose.
        figures = py[py.index('bucket["figures"].append'):][:2000]
        assert '"quote": quote' in figures, (
            "the figure payload no longer carries its quote; a metric page "
            "cannot be checked by a reader without it (#368)"
        )

    def test_the_grouping_keeps_the_quote_with_its_report(self):
        """One row groups several reports of one figure, so the quote belongs to
        the source rather than to the row — two reports can word it differently
        and which words are whose is the checkable part."""
        js = _db()
        group = js[js.index("function groupFigures(m) {"):]
        group = group[:group.index(chr(10) + "}")]
        assert "quote: f.quote" in group

    def test_the_page_prints_the_quote_rather_than_hiding_it(self):
        """⚠ NOT A `title` ATTRIBUTE. Invisible on a phone, absent to a screen
        reader in most settings, and it requires knowing there is something to
        hover. The board review prints its quotes for the same reason."""
        js = (ROOT / "web" / "src" / "board" / "views.js").read_text(encoding="utf-8")
        assert 'class="figq"' in js

    def test_the_metric_page_keeps_both_the_figures_and_the_models(self):
        """⚠ THIS COMMENT USED TO SAY THE OPPOSITE, and the code moved under it.

        It read: *"`DB.mets` overwrites `rows` with the figure table. If that
        overwrite ever went away, the metric page would silently start
        rendering model rows."* Rendering model rows is now the point - the
        overwrite is what discarded the level `vJobModel` and `vCapModel` both
        have, and its absence is why a metric page repeated one model once per
        figure. Measured 2026-09-21: 34 (axis, model) cells held two or more
        DIFFERENT figures that way.

        The figure table still exists and is still what the leaf renders. What
        must not come back is the *discarding*: both levels are kept.
        """
        js = _db()
        mets = js[js.index("DB.mets = (d.mets || []).map"):]
        assert "rows: groups.map((g) => [" in mets, "the figure table is still built"
        assert "srcs: groups.map((g) => g.sources)" in mets
        assert "mrows: base.rows || []" in mets, (
            "the model level is discarded again; a metric axis page cannot "
            "list its models and the drill-down has nothing to key on"
        )
        assert "groups," in mets, "the leaf page filters these by model"


class TestTheMetricAxisListsModelsAndDrillsDown:
    """The level metrics never had, and the collision it resolves."""

    def test_the_axis_page_lists_models_rather_than_figures(self):
        js = _views()
        met = js[js.index("function vMet(slug){"):js.index("function vMetModel(")]
        assert "ranked(rows, 'metmodel:' + m.slug)" in met, (
            "the axis page must list each model once and link to its own page; "
            "a flat figure table repeats the model name once per figure"
        )

    def test_a_model_page_exists_for_metrics_like_the_other_two_sections(self):
        js = _views()
        assert "function vMetModel(slug, key){" in js
        assert "vMetModel" in js[js.index("export {"):]

    def test_the_leaf_filters_on_the_model_key_not_the_label(self):
        # Two spellings of one model share no label, and two models can share a
        # display name. `model_key` is what the model rows are grouped on.
        js = _views()
        leaf = js[js.index("function vMetModel(slug, key){"):]
        assert "g.modelKey || '') === key" in leaf

    def test_the_figure_payload_carries_that_key(self):
        assert '"model_key": model_key,' in _store(), (
            "without it the leaf cannot match a figure to its model row"
        )

    def test_the_route_reaches_the_leaf(self):
        assert "kind === 'metmodel'" in BOARDVIEW.read_text(encoding="utf-8")
        route = ROUTE.read_text(encoding="utf-8")
        assert "modelKey ? vMetModel(slug, modelKey) : vMet(slug)" in route


class TestWhatAFigureMeasuredIsCopiedNeverInferred:
    """The column that tells $0.25 from $50, and the state it must be able to
    express when the evidence does not say."""

    def test_the_sub_axis_comes_from_the_quote(self):
        import re as _re
        js = _db()
        block = js[js.index("export function subAxisOf(quote)"):]
        block = block[:block.index(chr(10) + "}")]
        assert "quote || ''" in block and ".toLowerCase()" in block
        # It must read the QUOTE and nothing else - not the slug, not the unit.
        assert "slug" not in block and "unit" not in block
        assert _re.search(r"return hit \? hit\[0\] : null", block)

    def test_an_unnamed_axis_returns_null_rather_than_a_guess(self):
        js = _db()
        block = js[js.index("export function subAxisOf(quote)"):]
        block = block[:block.index(chr(10) + "}")]
        assert "if (!q) return null" in block

    def test_the_word_boundaries_are_real_escapes(self):
        # ⚠ THEY WERE NOT, FOR ONE COMMIT. A patch wrote the regexes with a
        #   literal 0x08 byte where a word-boundary escape belonged, so it
        #   matched nothing and every figure read "not stated" - including
        #   "Official output price | $50 / MTok". The page still rendered and
        #   still looked plausible, which is what makes it worth pinning.
        raw = DB.read_bytes()
        assert bytes([8]) not in raw, (
            "a control byte is standing in for a regex escape"
        )
        js = _db()
        wb = chr(92) + "b"   # the two characters a regex needs, not one control byte
        assert f"/{wb}output{wb}|{wb}completion{wb}|{wb}generated{wb}/" in js

    def test_reports_that_disagree_about_what_was_measured_claim_neither(self):
        js = _db()
        assert "subAxisDisputed: named.length > 1" in js
        assert "subAxis: named.length === 1 ? named[0] : null" in js

    def test_not_stated_is_rendered_as_a_value(self):
        # Rule 6. A blank cell reads as an oversight and invites the reader to
        # assume the common case; 69 of 113 cost figures name no side.
        js = _views()
        assert 'class="subax none">not stated<' in js


class TestTheTabSaysWhatIsBehindEachCard:
    def test_the_card_carries_its_model_count(self):
        js = _views()
        card = js[js.index("function mcard(x){"):]
        card = card[:card.index(chr(10) + "}")]
        assert "(x.mrows || []).length" in card

    def test_a_single_model_axis_is_named_as_a_recording_not_a_failed_comparison(self):
        """⚠ THIS TEST USED TO PIN `function metGrid(){`, WHICH IS A SPELLING.

        It asserted that one FUNCTION existed and that a sentence lived inside
        it. When parents replaced that function's split (#416 renders them; the
        divider and the headings cannot both own one grid), the test failed
        while the thing it was protecting was intact and had simply moved.

        That is #408's class pointed at a test: a check on the SHAPE OF THE
        CODE defends an implementation rather than a behaviour. The sentence is
        what matters and it is rule 4 content - an axis holding one model is a
        real recorded figure, and a reader must not read it as a comparison
        that failed. So this asserts the sentence reaches the METRICS TAB,
        wherever it is written.

        The SPLIT it used to describe is gone on purpose and nothing is lost:
        `mcard` has printed "1 model" / "N models" on every card since
        2026-09-21, which is the same fact per card and is checked above.
        """
        js = _views()
        met = js[js.index("met: {intro:"):]
        met = met[:met.index("grid:")]
        assert "single model" in met, "the metrics tab no longer says it"
        assert "none of them is a comparison" in met
