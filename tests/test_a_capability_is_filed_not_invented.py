"""A board name is reused or filed under a heading - never invented and left loose.

Found 2026-10-14 on the local copy: 736 capability leaves, 581 of them with one
report, 170 under a heading. The extractor named a new capability for most
quotes, because it was shown a dozen exemplars and told that naming something
absent from them was the expected outcome.

It is now shown THE BOARD'S VOCABULARY for all three sections under their
headings (`contract/board_vocabulary.yaml`), told to reuse a listed name
whenever one fits, and to file every entry under a heading (`BoardEntry.parent`).
Capabilities first; jobs and metrics the same day.

WHAT THESE KEEP TRUE

  - the vocabulary agrees with the heading map it is filed by;
  - the prompt carries every heading and every listed slug, and still says a
    wrong reuse is worse than a new name (the open-vocabulary rule stands);
  - a missing or unknown heading never costs a report: the row is stored,
    with NULL, and counted (rule 8 - a filing gap is a weight, not a gate);
  - the contract's filing always wins over the extractor's, and a leaf placed
    by the extractor says so.
"""

from __future__ import annotations

import pathlib

import psycopg
import pytest

from judge.board_grouping import group_section
from judge.config import board_vocabulary, section_headings, slug_parents
from judge.extract.prompt import build_system_prompt
from judge.extract.schema import BoardEntry

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"


SECTIONS = ("best_for", "capability", "metric")


class TestTheVocabularyAgreesWithTheMap:
    def test_every_section_has_a_vocabulary(self):
        assert set(board_vocabulary()) == set(SECTIONS)

    @pytest.mark.parametrize("section", SECTIONS)
    def test_every_heading_is_one_of_the_sections_headings(self, section):
        assert set(board_vocabulary()[section]) <= section_headings(section)

    @pytest.mark.parametrize("section", SECTIONS)
    def test_every_listed_slug_is_filed_under_the_heading_it_is_listed_under(self, section):
        mapping = slug_parents()[section]
        for heading, items in board_vocabulary()[section].items():
            for item in items:
                assert mapping.get(item["slug"]) == heading, item["slug"]

    @pytest.mark.parametrize("section", SECTIONS)
    def test_no_slug_is_listed_twice(self, section):
        slugs = [i["slug"] for items in board_vocabulary()[section].values() for i in items]
        assert len(slugs) == len(set(slugs))

    @pytest.mark.parametrize("section", SECTIONS)
    def test_every_listed_slug_has_a_name(self, section):
        for items in board_vocabulary()[section].values():
            assert all(i.get("name") for i in items)


class TestThePromptCarriesTheVocabulary:
    @pytest.fixture(scope="class")
    def prompt(self):
        return build_system_prompt([], legacy=False)

    @pytest.mark.parametrize("section", SECTIONS)
    def test_every_heading_key_is_in_brackets(self, prompt, section):
        for heading in board_vocabulary()[section]:
            assert f"[{heading}]" in prompt

    @pytest.mark.parametrize("section, title", [
        ("best_for", "SECTION 1 - BEST FOR"),
        ("capability", "SECTION 2 - CAPABILITIES"),
        ("metric", "SECTION 3 - METRICS"),
    ])
    def test_every_listed_slug_is_offered_in_its_own_section(self, prompt, section, title):
        start = prompt.index(title)
        titles = ("SECTION 2 - CAPABILITIES", "SECTION 3 - METRICS")
        nxt = [prompt.find(t, start + 1) for t in titles]
        end = min([i for i in nxt if i > start] or [len(prompt)])
        block = prompt[start:end]
        for items in board_vocabulary()[section].values():
            for item in items:
                assert item["slug"] in block, item["slug"]

    def test_a_metric_axis_is_reused_only_for_the_same_quantity_and_unit(self, prompt):
        """Rule 10 and the axis rule in the schema: a familiar wrong axis is a
        wrong number, and a benchmark version is not its shorter name."""
        assert "REUSE AN AXIS ONLY FOR THE SAME QUANTITY IN THE SAME UNIT" in prompt
        assert "`terminal-bench-2-1` is not" in prompt

    def test_a_listed_job_still_needs_a_named_task_that_worked(self, prompt):
        assert "A listed job is still a job only when BOTH tests above hold" in prompt

    def test_reuse_comes_first_and_a_wrong_reuse_is_still_refused(self, prompt):
        """The open-vocabulary rule is not repealed: the nearest wrong name is
        still worse than a new one."""
        assert "REUSE A LISTED SLUG" in prompt
        assert "NEVER FORCE A QUOTE INTO A LISTED SLUG" in prompt

    def test_an_empty_vocabulary_reproduces_the_exemplar_prompt(self):
        """How a run before 2026-10-14 can be reproduced."""
        old = build_system_prompt([], legacy=False, vocabulary={})
        assert "REUSE FIRST" not in old
        assert "EXEMPLARS FOR THE THREE BOARD SECTIONS" in old
        assert "SECTION 2 - CAPABILITIES (one named behaviour)" in old

    def test_a_section_without_a_vocabulary_falls_back_to_its_exemplars(self):
        only_caps = {"capability": board_vocabulary()["capability"]}
        p = build_system_prompt([], legacy=False, vocabulary=only_caps)
        assert "SECTION 2 - CAPABILITIES (one named behaviour) - THE VOCABULARY" in p
        assert "SECTION 1 - BEST FOR (jobs somebody runs) - THE VOCABULARY" not in p


class TestTheHeadingIsOptionalInTheSchema:
    def test_an_entry_without_a_heading_is_still_valid(self):
        """Required, a missing heading would fail validation and drop the
        report with it - a gate where a weight belongs (rule 8)."""
        e = BoardEntry(section="capability", slug="over-refusal", name="Over refusal",
                       definition="Whether harmless prompts are refused.")
        assert e.parent is None


def leaf(slug, parent_proposed=None):
    return {"slug": slug, "name": slug, "reports": 1, "parent_proposed": parent_proposed}


class TestTheExtractorsFilingIsAProposal:
    def test_an_unfiled_leaf_goes_under_the_heading_the_extractor_gave(self):
        rows = group_section([leaf("a-new-capability", "agentic")], section="capability")
        assert rows[0]["kind"] == "parent" and rows[0]["parent"] == "agentic"
        assert rows[0]["children"][0]["filed_by"] == "extractor"

    def test_a_heading_that_is_not_real_files_nothing(self):
        rows = group_section([leaf("a-new-capability", "misc")], section="capability")
        assert rows[0]["kind"] == "leaf" and rows[0]["parent"] is None

    def test_the_contract_wins_over_the_extractor(self):
        rows = group_section([leaf("code-review", "agentic")], section="capability")
        assert rows[0]["parent"] == "software-engineering"
        assert rows[0]["children"][0]["filed_by"] == "contract"


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO document (id, source, external_id, url, text_ref, content_hash, status) "
            "VALUES ('d1','devto','d1','https://dev.to/d1','r1','h1','kept')"
        )
        connection.commit()
        yield connection


def _row(slug, parent, quote):
    return {"section": "capability", "slug": slug, "name": slug, "definition": "A behaviour.",
            "parent": parent, "document_id": "d1", "quote": quote, "quote_verified": True,
            "polarity": "positive"}


class TestTheStoreKeepsEveryReport:
    def test_a_real_heading_is_stored(self, conn):
        from judge.store.board_entries import store_entries

        out = store_entries(conn, [_row("a-new-one", "agentic", "q1")], proposer_model="m")
        assert out["stored"] == 1 and out["unfiled_by_section"] == {}
        got = conn.execute("SELECT parent_proposed FROM board_entry").fetchone()
        assert got == ("agentic",)

    @pytest.mark.parametrize("parent", [None, "", "misc", "Agents and tool use"])
    def test_a_missing_or_unknown_heading_is_stored_as_null_and_counted(self, conn, parent):
        from judge.store.board_entries import store_entries

        out = store_entries(conn, [_row("a-new-one", parent, "q2")], proposer_model="m")
        assert out["stored"] == 1, "the report must be kept whatever the heading says"
        assert out["unfiled_by_section"] == {"capability": 1}
        got = conn.execute("SELECT parent_proposed FROM board_entry").fetchone()
        assert got == (None,)

    def test_the_board_carries_the_commonest_heading_per_leaf(self, conn):
        from judge.store.board_entries import board_sections, store_entries

        store_entries(conn, [_row("a-new-one", "agentic", "q3"), _row("a-new-one", "agentic", "q4"),
                             _row("a-new-one", "safety-and-honesty", "q5")], proposer_model="m")
        conn.commit()
        [item] = [i for i in board_sections(conn)["capability"] if i["slug"] == "a-new-one"]
        assert item["parent_proposed"] == "agentic"


class TestJobsAndMetricsAreFiledToo:
    def test_a_new_job_goes_under_the_job_heading_the_extractor_gave(self):
        rows = group_section([leaf("a-new-job", "media-generation")], section="best_for")
        assert rows[0]["parent"] == "media-generation"
        assert rows[0]["children"][0]["filed_by"] == "extractor"

    def test_a_heading_from_another_section_files_nothing(self):
        """`agentic` is a capability heading; on a metric it is not real."""
        rows = group_section([leaf("a-new-axis", "agentic")], section="metric")
        assert rows[0]["kind"] == "leaf"
