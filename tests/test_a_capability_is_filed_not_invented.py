"""A capability is reused or filed under a heading - never invented and left loose.

Found 2026-10-14 on the local copy: 736 capability leaves, 581 of them with one
report, 170 under a heading. The extractor named a new capability for most
quotes, because it was shown a dozen exemplars and told that naming something
absent from them was the expected outcome.

It is now shown THE BOARD'S CAPABILITY VOCABULARY under ten headings
(`contract/board_vocabulary.yaml`), told to reuse a listed name whenever one
fits, and to file every capability entry under a heading (`BoardEntry.parent`).

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


class TestTheVocabularyAgreesWithTheMap:
    def test_every_heading_is_a_capability_heading(self):
        assert set(board_vocabulary()["capability"]) <= section_headings("capability")

    def test_every_listed_slug_is_filed_under_the_heading_it_is_listed_under(self):
        mapping = slug_parents()["capability"]
        for heading, items in board_vocabulary()["capability"].items():
            for item in items:
                assert mapping.get(item["slug"]) == heading, item["slug"]

    def test_no_slug_is_listed_twice(self):
        slugs = [i["slug"] for items in board_vocabulary()["capability"].values() for i in items]
        assert len(slugs) == len(set(slugs))

    def test_every_listed_slug_has_a_name(self):
        for items in board_vocabulary()["capability"].values():
            assert all(i.get("name") for i in items)


class TestThePromptCarriesTheVocabulary:
    @pytest.fixture(scope="class")
    def prompt(self):
        return build_system_prompt([], legacy=False)

    def test_every_heading_key_is_in_brackets(self, prompt):
        for heading in board_vocabulary()["capability"]:
            assert f"[{heading}]" in prompt

    def test_every_listed_slug_is_offered(self, prompt):
        section = prompt[prompt.index("SECTION 2 - CAPABILITIES"):]
        for items in board_vocabulary()["capability"].values():
            for item in items:
                assert item["slug"] in section, item["slug"]

    def test_reuse_comes_first_and_a_wrong_reuse_is_still_refused(self, prompt):
        """The open-vocabulary rule is not repealed: the nearest wrong name is
        still worse than a new one."""
        assert "REUSE A LISTED SLUG" in prompt
        assert "NEVER FORCE A QUOTE INTO A LISTED SLUG" in prompt

    def test_jobs_and_metrics_keep_their_exemplars(self, prompt):
        assert "SECTION 1 - BEST FOR" in prompt
        assert "SECTION 3 - METRICS" in prompt

    def test_an_empty_vocabulary_reproduces_the_exemplar_prompt(self):
        """How a run before 2026-10-14 can be reproduced."""
        old = build_system_prompt([], legacy=False, vocabulary={})
        assert "THE VOCABULARY, REUSE FIRST" not in old
        assert "SECTION 2 - CAPABILITIES (one named behaviour)" in old


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
        assert out["stored"] == 1 and out["capability_unfiled"] == 0
        got = conn.execute("SELECT parent_proposed FROM board_entry").fetchone()
        assert got == ("agentic",)

    @pytest.mark.parametrize("parent", [None, "", "misc", "Agents and tool use"])
    def test_a_missing_or_unknown_heading_is_stored_as_null_and_counted(self, conn, parent):
        from judge.store.board_entries import store_entries

        out = store_entries(conn, [_row("a-new-one", parent, "q2")], proposer_model="m")
        assert out["stored"] == 1, "the report must be kept whatever the heading says"
        assert out["capability_unfiled"] == 1
        got = conn.execute("SELECT parent_proposed FROM board_entry").fetchone()
        assert got == (None,)

    def test_the_board_carries_the_commonest_heading_per_leaf(self, conn):
        from judge.store.board_entries import board_sections, store_entries

        store_entries(conn, [_row("a-new-one", "agentic", "q3"), _row("a-new-one", "agentic", "q4"),
                             _row("a-new-one", "safety-and-honesty", "q5")], proposer_model="m")
        conn.commit()
        [item] = [i for i in board_sections(conn)["capability"] if i["slug"] == "a-new-one"]
        assert item["parent_proposed"] == "agentic"
