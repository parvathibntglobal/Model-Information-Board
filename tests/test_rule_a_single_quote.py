"""A reviewer can rule one quote, and an empty selection is never "all of them".

WHY THIS EXISTS. `board_entry.ruling` has always been a per-ROW column; only the
writer was per-slug. That gap had a measured cost on #279: six of twenty-one
slugs held broken AND good rows, so declining the bad quotes would have taken
twenty-one sound ones off the board with them. The tombstone route was rejected
for exactly that and the rows were repaired instead - a script, two hosts and a
day, where ticking four boxes would have done.

THE TEST THAT MATTERS IS `TestAnEmptySelectionIsNotEverything`. The rest cover
the write; that one covers the only way this feature can be dangerous. "Nothing
ticked" means both "I want all of them" and "I have not ticked anything yet",
and reading the second as the first declines a whole capability on a misclick.
"""
from __future__ import annotations

import pathlib

import psycopg
import pytest

from judge.store.board_entries import (
    board_sections,
    list_for_review,
    rule_entries,
    rule_entry_ids,
    unrule_entry_ids,
)

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.commit()
        yield connection


@pytest.fixture
def board(conn):
    """One capability with three quotes: two sound, one we will decline."""
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, text_ref, "
        "content_hash, status) VALUES "
        "('doc1','devto','1','https://dev.to/a','ref1','h1','kept'),"
        "('doc2','devto','2','https://dev.to/b','ref2','h2','kept')"
    )
    for i, (doc, quote) in enumerate(
        [("doc1", "it handles tools well"),
         ("doc2", "tool calling is solid"),
         ("doc1", '{"author":"x","children":[]')],
        start=1,
    ):
        conn.execute(
            "INSERT INTO board_entry (id, section, slug, name, definition, "
            "document_id, quote, quote_verified, polarity, proposer_model, "
            "pipeline_version) VALUES "
            "(%s,'capability','tool-use','Tool use','Calls tools correctly.',"
            "%s,%s,true,'positive','m','v1')",
            (f"be{i}", doc, quote),
        )
    conn.commit()
    return ["be1", "be2", "be3"]


def _rulings(conn):
    return dict(conn.execute("SELECT id, ruling FROM board_entry ORDER BY id").fetchall())


class TestAnEmptySelectionIsNotEverything:
    """The one way this feature can do real damage."""

    def test_an_empty_list_is_refused_not_widened(self, conn, board):
        with pytest.raises(ValueError) as caught:
            rule_entry_ids(conn, ids=[], ruling="declined")

        assert "rule_entries" in str(caught.value), (
            "the refusal should name the thing that DOES rule a whole section, "
            "so a caller who genuinely meant that is not left guessing"
        )
        assert set(_rulings(conn).values()) == {None}, "nothing may be ruled"

    def test_unrule_refuses_an_empty_list_too(self, conn, board):
        rule_entry_ids(conn, ids=["be1"], ruling="declined")
        conn.commit()

        with pytest.raises(ValueError):
            unrule_entry_ids(conn, ids=[])

        assert _rulings(conn)["be1"] == "declined", "the ruling stands"


class TestRulingOneQuote:
    def test_it_rules_only_the_named_row(self, conn, board):
        ruled = rule_entry_ids(conn, ids=["be3"], ruling="declined")
        conn.commit()

        assert ruled == 1
        assert _rulings(conn) == {"be1": None, "be2": None, "be3": "declined"}

    def test_the_declined_quote_leaves_the_board_and_the_others_stay(self, conn, board):
        """#279's case, which the slug-level ruling could not express."""
        rule_entry_ids(conn, ids=["be3"], ruling="declined")
        conn.commit()

        sections = board_sections(conn)
        quotes = [q["quote"] for s in sections["capability"] for q in s["quotes"]]
        assert "it handles tools well" in quotes
        assert "tool calling is solid" in quotes
        assert not any(q.startswith('{"author"') for q in quotes)

    def test_reviewed_at_moves_with_the_ruling(self, conn, board):
        """The table CHECKs the two together; a writer that set one would fail."""
        rule_entry_ids(conn, ids=["be1"], ruling="adopted")
        conn.commit()

        row = conn.execute(
            "SELECT ruling, reviewed_at FROM board_entry WHERE id='be1'"
        ).fetchone()
        assert row[0] == "adopted"
        assert row[1] is not None

    def test_undo_clears_only_that_quote(self, conn, board):
        rule_entry_ids(conn, ids=["be1", "be3"], ruling="declined")
        conn.commit()
        unrule_entry_ids(conn, ids=["be3"])
        conn.commit()

        assert _rulings(conn) == {"be1": "declined", "be2": None, "be3": None}

    def test_a_merge_still_needs_a_target(self, conn, board):
        with pytest.raises(ValueError) as caught:
            rule_entry_ids(conn, ids=["be1"], ruling="merged")

        assert "ruling_target" in str(caught.value)

    def test_an_unknown_ruling_is_refused(self, conn, board):
        with pytest.raises(ValueError):
            rule_entry_ids(conn, ids=["be1"], ruling="deleted")


class TestTheReviewListCanAddressAQuote:
    def test_every_quote_carries_its_id(self, conn, board):
        [item] = list_for_review(conn)

        assert [q["id"] for q in item["quotes"]] == ["be3", "be2", "be1"] or set(
            q["id"] for q in item["quotes"]
        ) == {"be1", "be2", "be3"}

    def test_a_quote_shows_its_own_ruling(self, conn, board):
        rule_entry_ids(conn, ids=["be3"], ruling="declined")
        conn.commit()

        [item] = list_for_review(conn)
        by_id = {q["id"]: q["ruling"] for q in item["quotes"]}
        assert by_id["be3"] == "declined"
        assert by_id["be1"] is None


class TestAMixedSlugDoesNotClaimOneRuling:
    """`max(ruling)` stops meaning anything once two quotes can differ."""

    def test_a_partly_declined_slug_reports_no_section_ruling(self, conn, board):
        rule_entry_ids(conn, ids=["be3"], ruling="declined")
        conn.commit()

        [item] = list_for_review(conn)
        assert item["ruling"] is None, (
            "one declined quote out of three must not read as a declined section"
        )
        assert item["ruling_counts"] == {"declined": 1, "unruled": 2}

    def test_a_wholly_ruled_slug_still_reports_its_ruling(self, conn, board):
        rule_entries(conn, section="capability", slug="tool-use", ruling="adopted")
        conn.commit()

        [item] = list_for_review(conn)
        assert item["ruling"] == "adopted"
        assert item["ruling_counts"] == {"adopted": 3}

    def test_max_ruling_would_have_lied(self, conn, board):
        """The specific misreport this replaced, pinned.

        'merged' sorts above 'declined' above 'adopted', so a slug with two
        adopted quotes and one merged used to report 'merged' for the group.
        """
        rule_entry_ids(conn, ids=["be1", "be2"], ruling="adopted")
        rule_entry_ids(conn, ids=["be3"], ruling="merged", ruling_target="function-calling")
        conn.commit()

        [item] = list_for_review(conn)
        assert item["ruling"] is None
        assert item["ruling_counts"] == {"adopted": 2, "merged": 1}
