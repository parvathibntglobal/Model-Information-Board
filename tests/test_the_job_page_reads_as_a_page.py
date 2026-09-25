"""The Jobs page: what a job IS, what the evidence says, and the rules - apart.

2026-09-25. The per-job "description" was the extractor's `definition` from the
NEWEST row, which is a counting rule (the test a report has to meet), and it
changed as reports arrived: 13 of 98 job pages had rows carrying more than one.
Above the list sat an ~800-character ordering paragraph, identical on every page
but for the numbers, capped at 64ch - half the width of the list below it.

Now:
  the job        a hand-written `about` (contract/job_about.yaml), or no lead line
  the evidence   one stat line, the group headings, each row's counts
  the rules      a side column; the extractor's text labelled "What counts here"
"""

from __future__ import annotations

import pathlib
import re

import yaml

from tests.test_the_board_drills_down import build, row

ROOT = pathlib.Path(__file__).resolve().parents[1]
VIEWS = ROOT / "web" / "src" / "board" / "views.js"
DB = ROOT / "web" / "src" / "board" / "db.js"
CSS = ROOT / "web" / "src" / "styles" / "board.css"
ABOUT = ROOT / "contract" / "job_about.yaml"


def _row(definition, created_at, doc):
    r = list(row(section="best_for", slug="coding-agent", doc=doc, author=f"au_{doc}"))
    r[3], r[11] = definition, created_at
    return tuple(r)


def _js():
    return VIEWS.read_text(encoding="utf-8")


class TestTheDefinitionShownIsStable:
    def test_the_most_common_definition_wins_over_the_newest(self):
        rows = [_row("newest, said once", "2026-09-25", "d9"),       # arrives first
                _row("common", "2026-09-10", "d1"),
                _row("common", "2026-09-11", "d2")]
        assert build(rows)["best_for"][0]["definition"] == "common"

    def test_a_tie_goes_to_the_text_written_first(self):
        rows = [_row("later", "2026-09-20", "d2"), _row("earlier", "2026-09-01", "d1")]
        assert build(rows)["best_for"][0]["definition"] == "earlier"

    def test_a_new_row_cannot_flip_a_tie(self):
        base = [_row("a", "2026-09-01", "d1"), _row("b", "2026-09-02", "d2")]
        before = build(base)["best_for"][0]["definition"]
        after = build([_row("b", "2026-09-25", "d3"), *base])["best_for"][0]["definition"]
        assert before == "a" and after == "b", "b now has more rows - a count, not an arrival"


class TestTheAboutTextIsAContract:
    def _about(self):
        return yaml.safe_load(ABOUT.read_text(encoding="utf-8"))["about"]

    def test_it_loads_through_config_with_whitespace_folded(self):
        from judge.config import job_about
        about = job_about()
        assert about and all("\n" not in v and "  " not in v for v in about.values())
        assert set(about) == {k.lower() for k in self._about()}

    def test_it_describes_the_subject_and_names_no_model_and_no_evidence(self):
        # A description readable with no report existing: no model names, no
        # claims about what reports say.
        banned = re.compile(
            r"\b(claude|gpt|gemini|deepseek|qwen|kimi|grok|llama|mistral|opus|sonnet"
            r"|reported|reports? (say|show|of)|(engineers|people|users) (say|report)"
            r"|best|better than)\b",
            re.I,
        )
        for slug, text in self._about().items():
            assert not banned.search(text), f"{slug}: {banned.search(text).group(0)!r}"

    def test_the_two_non_jobs_are_left_out_on_purpose(self):
        about = self._about()
        assert "reasoning" not in about and "general-purpose" not in about


class TestThePageKeepsTheThreeKindsApart:
    def test_the_lead_renders_only_when_there_is_an_about(self):
        js = _js()
        assert "${j.about ? `<p class=\"lead\">${esc(j.about)}</p>` : ''}" in js
        assert "<p class=\"sub\">${esc(j.sub)}</p>" not in js

    def test_the_extractor_text_is_labelled_as_a_counting_rule(self):
        js = _js()
        assert "<h3>What counts here</h3>" in js
        assert "It is not a description of the job." in js
        db = DB.read_text(encoding="utf-8")
        assert "rule: j.definition || ''" in db
        assert "card: j.about || ''" in db, "the Jobs-tab card describes the job or says nothing"

    def test_every_load_bearing_rule_is_still_on_the_page(self):
        aside = _js()[_js().index("function jobAside(j)"):_js().index("function vJob(slug)")]
        for clause in ("Three groups", "more consistently say it worked come",
                       "counts for less than the same record on many",
                       "No score is shown: each row shows its counts.",
                       "single positive report, however many problem reports it also has",
                       "extractor’s reading of each quote", "counted under each", "floors (≥)"):
            assert clause in " ".join(aside.split()), clause

    def test_the_rules_are_beside_the_list_not_hidden(self):
        js = _js()
        assert "<aside class=\"jobaside\">" in js
        assert "<details" not in js[js.index("function jobAside"):], "stated, not tucked away"
        css = CSS.read_text(encoding="utf-8")
        assert ".jobbody{display:grid;grid-template-columns:minmax(0,1fr) 300px" in css
        assert ".jobhead .lead{" in css and "max-width:110ch" in css
