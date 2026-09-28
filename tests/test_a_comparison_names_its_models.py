"""The comparison URL, and its page, name the models rather than the database.

Three things a reader met on `/compare` that were about us rather than about
the models they picked:

    /compare?ids=mv_de3e701e07b8bfa9,mv_9a53a616c98d9f6b
        an internal key in a link people send each other, which cannot be
        typed, read or checked, and says nothing about what is being compared

    "Advertised — the provider's claim about itself"
        a provider's published numbers, in a table beside counted reports. The
        whole block is gone: this board's evidence comes from engineers, and a
        heading cannot stop a spec sheet reading as a finding when it is laid
        out like one.

    "Rows the landing demo had that this cannot"
        the landing demo is a thing in OUR project history. No reader of this
        page has heard of it, and the heading framed an honest limit as an
        apology to ourselves.

⚠ AND THE PAGE NOW SHOWS HOW A REPORT WAS PHRASED. "12 reports" is the same
  sentence for twelve complaints and twelve recommendations. `polarity` was on
  every entry and reaching no page — three counts and their denominator, never
  a ratio.
"""

from __future__ import annotations

import os
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPARE = ROOT / "web" / "src" / "routes" / "Compare.jsx"
MODELS = ROOT / "web" / "src" / "routes" / "Models.jsx"
APP = ROOT / "judge" / "app.py"


def jsx(path: pathlib.Path) -> str:
    """Source with comments stripped — the comments discuss what was removed."""
    text = re.sub(r"/\*[\s\S]*?\*/", "", path.read_text(encoding="utf-8"))
    return "\n".join(
        ln for ln in text.splitlines() if not ln.strip().startswith("//")
    )


class TestTheUrlCarriesTheProvidersName:
    def test_the_models_list_picks_by_canonical_id(self):
        src = jsx(MODELS)
        assert "const compareId = (m) => m.canonical_id || m.model_version_id" in src
        assert "onPick(compareId(m))" in src

    def test_it_falls_back_rather_than_dropping_a_model(self):
        """A row whose canonical id never loaded is still comparable. The
        endpoint takes both forms, so the fallback costs a reader nothing."""
        src = jsx(MODELS)
        assert "m.canonical_id || m.model_version_id" in src

    def test_the_endpoint_accepts_both_forms(self):
        """⚠ ACCEPTED, NOT SWAPPED. Links already sent and bookmarks already
        saved keep working — a URL that 404s because we improved it is a URL
        we broke."""
        src = APP.read_text(encoding="utf-8")
        body = src[src.index("def compare_page("):]
        body = body[:body.index("\n@app.")]
        assert 'roster[m["model_version_id"]] = m' in body
        assert 'roster.setdefault(m["canonical_id"], m)' in body

    def test_asking_for_one_model_twice_is_one_column(self):
        """Both of a model's ids in one URL is one model, not two identical
        columns — de-duplicated on the model, never on the string."""
        src = APP.read_text(encoding="utf-8")
        body = src[src.index("def compare_page("):]
        assert 'x["model_version_id"] == m["model_version_id"] for x in found' in body


class TestThePageDoesNotPrintADatabaseIdAtTheReader:
    def test_the_column_header_shows_the_canonical_id(self):
        src = jsx(COMPARE)
        assert "{m.canonical_id}" in src

    def test_it_omits_the_line_rather_than_falling_back_to_the_internal_id(self):
        """⚠ THE FALLBACK IS THE DEFECT HERE, not the safety net it is
        elsewhere. A reader cannot look up `mv_de3e701e07b8bfa9`, check it, or
        use it anywhere — showing it is worse than showing nothing."""
        src = jsx(COMPARE)
        head = src[src.index("<thead>"):src.index("</thead>")]
        assert "m.canonical_id &&" in head
        assert "m.model_version_id}\n" not in head

    def test_the_payload_carries_it(self):
        src = APP.read_text(encoding="utf-8")
        assert '"canonical_id": m.get("canonical_id"),' in src


class TestTheProvidersSpecSheetIsNotOnThisPage:
    def test_the_spec_block_is_gone_entirely(self):
        """⚠ RENAMING IT WAS MY SECOND WRONG ANSWER. First I reworded the
        heading, then I made the block conditional, and both kept a provider's
        published numbers in a table beside counted reports.

        This board's evidence comes from engineers writing about models they
        used. A spec sheet is the one thing on the page nobody reported, and a
        heading cannot hold that line — a table is a table, and the two halves
        looked equally like findings."""
        src = jsx(COMPARE)
        assert "the provider's claim about itself" not in src
        assert "Specification" not in src
        for row in ("Cost per Mtok", "Context window", "Max output", "Cached read"):
            assert row not in src, f"the spec row {row!r} is still rendered"

    def test_the_advertised_data_is_still_in_the_payload(self):
        """Removed from the page, not from the API. The model pages still
        describe price and context, and anything else that wants them has
        them."""
        src = APP.read_text(encoding="utf-8")
        assert '"advertised": {' in src

    def test_the_landing_demo_is_not_mentioned_to_a_reader(self):
        src = jsx(COMPARE)
        assert "landing demo" not in src

    def test_the_whole_section_is_gone_rather_than_reworded(self):
        """⚠ REWORDING IT WAS MY FIRST ANSWER AND IT WAS THE WRONG ONE. The
        heading read better and the section still explained the board's own
        history to somebody who came to compare two models.

        The argument for keeping it was rule 4's - a shorter table with no
        explanation reads as "everything comparable has been compared" - and
        rule 4 does not reach this far. It is about an absence WE CAUSED, which
        a reader would otherwise take for an absence in the world. `licence`,
        `benchmark_standing` and `one_line` were never collected, so there is
        no caused absence to disclose."""
        src = jsx(COMPARE)
        assert "Not compared here" not in src
        assert "benchmark_standing" not in src
        assert "u.why" not in src

    def test_the_payload_still_carries_the_reasons(self):
        """Removed from the page, not from the API. If one of these ever
        becomes an absence we cause rather than one we never filled, it goes
        back — and the data is there for whoever does that."""
        src = APP.read_text(encoding="utf-8")
        assert '"unsourced"' in src


class TestARowWhereEveryCellIsIdenticalIsNotARow:
    def test_nobody_has_discussed_this_is_said_once_and_not_per_column(self):
        """It rendered as a table row reading "nobody has discussed this" in
        every column — the same sentence three times, under a heading, in a
        grid built for differences. A row where every cell is identical
        carries no comparison, and three of them is not three facts."""
        src = jsx(COMPARE)
        assert "nobody has discussed this" not in src
        assert "Nobody has written about" in src

    def test_the_whole_table_is_skipped_when_there_is_nothing_to_compare(self):
        src = jsx(COMPARE)
        assert "{!anyReports ? (" in src

    def test_the_gate_is_not_the_legacy_reports_counter(self):
        """⚠ THIS BLANKED THE PAGE FOR EVERY PAIR AND THE SUITE STAYED GREEN.

        `reported.reports` comes from the legacy `cell` table and is **0 on all
        348 models in the registry** (#194: `cell.status` is `insufficient` on
        311 of 311), while 79 models carry real board entries. Gating a
        paragraph on it was harmless; gating the TABLE on it meant every
        comparison rendered empty.

        My tests asserted source strings and never rendered the page, so
        nothing caught it — @parvathibntglobal did, by opening it."""
        src = jsx(COMPARE)
        gate = src[src.index("const hasEvidence"):src.index("const anyReports")]
        assert "r.polarity?.entries" in gate
        assert "reports" not in gate, (
            "the gate is reading a counter that is zero on every model"
        )

    def test_the_gate_asks_whether_anybody_wrote_anything(self):
        """Entries, or any discovered section. The question is "did anybody
        write about these", and the answer is in the evidence rather than in a
        score nothing has ever populated."""
        src = jsx(COMPARE)
        gate = src[src.index("const hasEvidence"):src.index("const anyReports")]
        for field in ("best_for", "capabilities", "metrics"):
            assert field in gate, f"the gate ignores {field}"


class TestHowAReportWasPhrasedIsCountedSeparately:
    def test_the_three_counts_are_rendered(self):
        src = jsx(COMPARE)
        assert "How it was phrased" in src
        for word in ("negative", "positive", "neutral"):
            assert word in src

    def test_no_ratio_net_or_score_is_computed(self):
        """⚠ RULE 3, AND THIS IS EXACTLY WHERE IT WOULD BREAK. A net score, a
        percentage positive or a "sentiment" figure is the 0-100 capability
        number this board refuses to compute — and it would pick a winner from
        a count of sentences."""
        src = jsx(COMPARE)
        block = src[src.index("How it was phrased"):src.index("— out of")]
        # ⚠ ARITHMETIC ON THE COUNTS, NOT RAW CHARACTERS. The first version of
        #   this test banned "/" and failed on every JSX closing tag, which is
        #   mention-versus-use in a new costume: it searched for the shape of
        #   the defect instead of the defect.
        for banned in ("Math.round", "toFixed", "* 100", "reduce("):
            assert banned not in block, f"a figure is being derived with {banned!r}"
        for field in ("positive", "negative", "neutral", "entries"):
            for op in ("/", "*", "+", "-"):
                assert f"p.{field} {op}" not in block, (
                    f"p.{field} is being combined with {op!r} — that is a score"
                )

    def test_the_denominator_travels_with_the_counts(self):
        """Rule 7. Entries are not people — one document can produce several,
        so "74 negative" means nothing without both numbers."""
        src = jsx(COMPARE)
        assert "entries, from " in src
        assert "documents}" in src

    def test_declined_entries_are_not_counted(self):
        """A reviewer has ruled them off the board; counting them would put
        them back through an arithmetic side door."""
        src = APP.read_text(encoding="utf-8")
        body = src[src.index("polarity = {}"):]
        body = body[:body.index("models = []")]
        assert "ruling IS DISTINCT FROM 'declined'" in body


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs the shared board")
class TestItResolvesAgainstTheRealRegistry:
    def test_two_canonical_ids_produce_two_columns(self):
        from judge.app import compare_page

        d = compare_page(ids="anthropic/claude-opus-5,openai/gpt-5.6-sol")
        assert len(d["models"]) == 2
        assert all(m["canonical_id"] for m in d["models"])
