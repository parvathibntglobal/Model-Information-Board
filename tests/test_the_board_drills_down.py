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

METRICS IS NOT PART OF THIS. Its page is a figure table rather than a model
list, and the last class here checks that the code producing it did not move.
"""

from __future__ import annotations

import pathlib

import pytest

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
        author="au_1", polarity="positive", quote="q", value=None,
        registry="mv_a", label="Model A"):
    """One `board_entry` row in the column order `board_sections` selects."""
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


class TestBestForSaysWhatItDropped:
    def test_the_hidden_count_travels_with_the_model_row(self):
        out = build(
            [row(section="best_for", slug="coding-agent", doc="d1")],
            hidden=[("coding-agent", "mv_a", "Model A", 3)],
        )
        assert out["best_for"][0]["models"][0]["hidden_negative_reports"] == 3

    def test_zero_is_written_rather_than_left_absent(self):
        # A reader of this payload cannot otherwise tell "no complaints were
        # filtered" from "nobody counted", and keeping those apart is the whole
        # job of this board.
        out = build([row(section="best_for", slug="coding-agent")], hidden=[])
        assert out["best_for"][0]["models"][0]["hidden_negative_reports"] == 0

    def test_the_filter_itself_is_unchanged(self):
        # The count is a second query precisely so this clause stays readable
        # and stays the only place the rule is expressed.
        assert (
            "AND NOT (be.section = 'best_for' AND be.polarity = 'negative')"
            in _store()
        )

    def test_the_page_names_the_count_and_links_to_where_they_are(self):
        js = _views()
        assert "row.hidden || 0" in js
        assert "report${hidden===1?'':'s'} of a problem" in js
        assert 'data-go="model:${esc(key)}"' in js

    def test_capability_rows_are_never_given_a_hidden_count(self):
        # Nothing is filtered there, and a caveat about nothing is noise.
        out = build([row(section="capability")],
                    hidden=[("reasoning", "mv_a", "Model A", 2)])
        assert "hidden_negative_reports" not in out["capability"][0]["models"][0]


class TestAModelDroppedEntirelyIsStillNamed:
    """The worse half of the same absence, and the half a row cannot carry.

    A model with SOME positive reports gets a row and a shortened list, and the
    drill-down page says how many are missing. A model whose every report on
    this job is a problem report gets NO ROW - it is not on the page, and a
    reader cannot tell that from a model nobody has discussed. 4 of the 12
    (slug, model) pairs are in that state.
    """

    def test_a_model_with_only_negatives_is_named_on_the_category_page(self):
        out = build(
            [row(section="best_for", slug="coding-agent", mv="mv_a",
                 registry="mv_a", label="Model A")],
            hidden=[("coding-agent", "mv_a", "Model A", 2),
                    ("coding-agent", "mv_b", "Model B", 4)],
        )
        item = out["best_for"][0]
        assert [m["model_key"] for m in item["models"]] == ["mv_a"]
        assert item["suppressed_models"] == [
            {"model_key": "mv_b", "model_label": "Model B", "reports": 4}
        ]

    def test_a_model_that_has_a_row_is_not_also_listed_as_suppressed(self):
        # It is already carrying `hidden_negative_reports`; saying it twice
        # would double-count the same absence in two different words.
        out = build(
            [row(section="best_for", slug="coding-agent", mv="mv_a",
                 registry="mv_a")],
            hidden=[("coding-agent", "mv_a", "Model A", 2)],
        )
        assert out["best_for"][0]["suppressed_models"] == []
        assert out["best_for"][0]["models"][0]["hidden_negative_reports"] == 2

    def test_the_list_is_empty_rather_than_absent(self):
        out = build([row(section="best_for", slug="coding-agent")])
        assert out["best_for"][0]["suppressed_models"] == []

    def test_it_is_sorted_by_name_so_the_line_does_not_reshuffle(self):
        out = build(
            [row(section="best_for", slug="coding-agent", mv="mv_z",
                 registry="mv_z", label="Z")],
            hidden=[("coding-agent", "mv_b", "Beta", 1),
                    ("coding-agent", "mv_a", "Alpha", 1)],
        )
        assert [m["model_label"] for m in out["best_for"][0]["suppressed_models"]] == [
            "Alpha", "Beta"]

    def test_capability_sections_never_get_one(self):
        out = build([row(section="capability")],
                    hidden=[("reasoning", "mv_b", "Model B", 2)])
        assert "suppressed_models" not in out["capability"][0]

    def test_the_page_names_each_model_and_links_it(self):
        # A count alone is not something a reader can act on. The link goes to
        # the model page, where the reports it does have are shown.
        js = _views()
        assert "function suppressedNote(item)" in js
        assert "not listed above" in js
        assert 'data-go="model:${esc(x.key)}"' in js
        assert "esc(x.m)" in js

    def test_it_renders_on_both_category_pages_or_neither(self):
        # It is wired to `vJob` and `vCap` alike and stays empty on capability
        # by the data rather than by the caller - so the day a second section
        # learns to filter, the line is already there.
        js = _views()
        assert "orphanNote(j) + suppressedNote(j)" in js
        assert "orphanNote(c) + suppressedNote(c)" in js

    def test_it_says_nothing_when_there_is_nothing_to_say(self):
        js = _views()
        block = js[js.index("function suppressedNote(item)"):js.index("function conds(")]
        assert "if(!list.length) return '';" in block

    def test_a_suppressed_model_still_gets_a_name_rather_than_an_id(self):
        # The label is fetched in the second query precisely because these
        # models have no row in `models[]` to carry one - and printing
        # `mv_4247e801b57d22e3` where a model name belongs is #278 by a third
        # route.
        assert "COALESCE(v.display_name, v.canonical_id, be.model_version_id)," in _store()
        assert "String(m.model_key || '').split('/').pop()" in _db()


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


class TestMetricsDidNotMove:
    """The three functions that make a metric page, unchanged from HEAD~.

    Scoped to what actually renders that page rather than to the file: `db.js`
    and `views.js` both changed, and a whole-file hash would only prove that.
    """

    @pytest.mark.parametrize(
        "path,start,end",
        [
            ("web/src/board/views.js", "function vMet(slug){", "function vBlogs()"),
            ("web/src/board/views.js", "function mcard(x){", "/* ---------- views"),
            ("web/src/board/db.js", "function groupFigures(m) {",
             "/** Populate `DB` from the `/board` payload."),
        ],
    )
    def test_the_metric_path_is_byte_identical(self, path, start, end):
        import subprocess

        now = (ROOT / path).read_text(encoding="utf-8")
        was = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout
        assert now[now.index(start):now.index(end)] == was[was.index(start):was.index(end)]

    def test_the_metric_page_still_reads_its_own_row_shape(self):
        # `commonFields` is shared, and `DB.mets` overwrites `rows` with the
        # figure table. If that overwrite ever went away, the metric page would
        # silently start rendering model rows.
        js = _db()
        mets = js[js.index("DB.mets = (d.mets || []).map"):]
        assert "rows: groups.map((g) => [" in mets
        assert "srcs: groups.map((g) => g.sources)" in mets
