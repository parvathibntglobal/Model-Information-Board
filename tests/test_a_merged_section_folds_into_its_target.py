"""A merged section folds into the section it merged into, and cannot merge back.

⚠ THE REVIEW LIST KEPT A MERGED SECTION AS ITS OWN ROW, AND THAT MADE CYCLES.
  After merging `exploitgym` into `exploit-gym` the reviewer still saw both, so
  merging again from the other side looked like the fix - and the second merge
  pointed the pair at each other. Each then deferred to the other and neither
  showed on the board.

  Measured on the shared database, 2026-09-28: of 9 merges, 2 were clean.

      cycles   3   overthinking <-> over-thinking
                   exploitgym   <-> exploit-gym
                   osworld-2    <-> osworld-2-0
      chain    1   osworld -> osworld-2-0 -> osworld-2

  The display bug caused the data bug, so both halves are fixed and tested
  here: the list folds a wholly merged section under its target, and a merge
  that would point two sections at each other is refused.

⚠ THE EXISTING CYCLES ARE NOT REPAIRED. Which name survives is a ruling for a
  person, and the shared database is not this change's to edit. The list flags
  them instead, and one undo resolves each - which the last class checks.
"""

from __future__ import annotations

import pathlib

import psycopg
import pytest

from judge.store.board_entries import (
    MergeCycle,
    list_for_review,
    resolve_merge_target,
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


def _seed(conn, rows):
    """`rows` is [(id, slug, doc)]; every row a capability with a verified quote.

    CAPABILITY, NOT METRIC, although the real cycles were metrics. A metric row
    must carry a unit, a value and a basis (`board_entry_metric_complete_ck`),
    and none of that bears on merging - the resolver and the fold are per
    section and never look at a figure. Seeding the simpler section keeps the
    fixture about the thing under test.
    """
    docs = sorted({d for _, _, d in rows})
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, text_ref, content_hash, status) "
        "VALUES " + ",".join(
            f"('{d}','devto','{d}','https://dev.to/{d}','r{d}','h{d}','kept')" for d in docs)
    )
    for rid, slug, doc in rows:
        conn.execute(
            "INSERT INTO board_entry (id, section, slug, name, definition, document_id, "
            "quote, quote_verified, polarity, proposer_model, pipeline_version) VALUES "
            "(%s,'capability',%s,%s,'A behaviour.',%s,'it scored well',true,'positive','m','v1')",
            (rid, slug, slug, doc),
        )
    conn.commit()


@pytest.fixture
def twins(conn):
    """One benchmark under two spellings - the exact shape that became a cycle."""
    _seed(conn, [("a1", "exploit-gym", "d1"), ("a2", "exploit-gym", "d2"),
                 ("b1", "exploitgym", "d3")])


def _row(groups, slug):
    return next((g for g in groups if g["slug"] == slug), None)


class TestTheListFoldsAMergeUnderItsTarget:
    def test_the_merged_section_is_no_longer_its_own_row(self, conn, twins):
        rule_entries(conn, section="capability", slug="exploitgym",
                     ruling="merged", ruling_target="exploit-gym")
        groups = list_for_review(conn)
        assert _row(groups, "exploitgym") is None, (
            "the merged section is still listed on its own, which is what "
            "invited merging it back the other way"
        )

    def test_it_appears_under_the_target_with_its_own_counts(self, conn, twins):
        rule_entries(conn, section="capability", slug="exploitgym",
                     ruling="merged", ruling_target="exploit-gym")
        host = _row(list_for_review(conn), "exploit-gym")
        assert [m["slug"] for m in host["merged_in"]] == ["exploitgym"]
        assert host["merged_in"][0]["entries"] == 1
        assert host["merged_in_entries"] == 1

    def test_the_targets_own_counts_are_not_inflated(self, conn, twins):
        """⚠ RULE 7. `documents` and `models` are DISTINCT counts; one document
        can sit under both names, and adding them would count it twice. The
        merged-in figures travel separately and say whose they are."""
        rule_entries(conn, section="capability", slug="exploitgym",
                     ruling="merged", ruling_target="exploit-gym")
        host = _row(list_for_review(conn), "exploit-gym")
        assert host["entries"] == 2 and host["documents"] == 2

    def test_a_partly_merged_section_stays_listed(self, conn, twins):
        """Rulings are per row. Moving one quote out of a section leaves the
        rest under its own name, still on the board, still with a queue."""
        _seed(conn, [("b2", "exploitgym", "d4")])
        rule_entry_ids(conn, ids=["b1"], ruling="merged", ruling_target="exploit-gym")
        assert _row(list_for_review(conn), "exploitgym") is not None


class TestAMergeCannotPointBack:
    def test_merging_back_the_other_way_is_refused(self, conn, twins):
        """⚠ THE CLICK THAT MADE ALL THREE CYCLES, refused."""
        rule_entries(conn, section="capability", slug="exploitgym",
                     ruling="merged", ruling_target="exploit-gym")
        with pytest.raises(MergeCycle) as caught:
            rule_entries(conn, section="capability", slug="exploit-gym",
                         ruling="merged", ruling_target="exploitgym")
        assert "each other" in str(caught.value)
        assert "Undo" in str(caught.value), (
            "the refusal does not say how to get where the reviewer wanted"
        )

    def test_a_per_quote_merge_back_is_refused_too(self, conn, twins):
        rule_entries(conn, section="capability", slug="exploitgym",
                     ruling="merged", ruling_target="exploit-gym")
        with pytest.raises(MergeCycle):
            rule_entry_ids(conn, ids=["a1", "a2"], ruling="merged",
                           ruling_target="exploitgym")

    def test_nothing_is_written_when_it_is_refused(self, conn, twins):
        rule_entries(conn, section="capability", slug="exploitgym",
                     ruling="merged", ruling_target="exploit-gym")
        with pytest.raises(MergeCycle):
            rule_entries(conn, section="capability", slug="exploit-gym",
                         ruling="merged", ruling_target="exploitgym")
        conn.rollback()
        left = conn.execute(
            "SELECT count(*) FROM board_entry WHERE slug='exploit-gym' AND ruling IS NULL"
        ).fetchone()[0]
        assert left == 2


class TestAMergeIntoAMergedSectionFollowsIt:
    def test_the_hop_is_followed_to_where_it_lands(self, conn):
        """The chain on the board: `osworld` merged into `osworld-2-0`, which was
        already merged into `osworld-2`. Pointing at a hop that renders nothing
        is how evidence disappears quietly."""
        _seed(conn, [("o1", "osworld", "d1"), ("o2", "osworld-2-0", "d2"),
                     ("o3", "osworld-2", "d3")])
        rule_entries(conn, section="capability", slug="osworld-2-0",
                     ruling="merged", ruling_target="osworld-2")
        rule_entries(conn, section="capability", slug="osworld",
                     ruling="merged", ruling_target="osworld-2-0")
        target = conn.execute(
            "SELECT ruling_target FROM board_entry WHERE id='o1'").fetchone()[0]
        assert target == "osworld-2", (
            f"the merge was left pointing at {target!r}, itself merged away"
        )

    def test_a_partly_merged_target_is_a_real_landing_place(self, conn):
        """⚠ `bool_and` IGNORES NULLS. A section with one merged row and one
        unruled row is still on the board, and must not be skipped past."""
        _seed(conn, [("p1", "arc", "d1"), ("p2", "arc", "d2"), ("q1", "arc-agi", "d3"),
                     ("r1", "arc-x", "d4")])
        rule_entry_ids(conn, ids=["p1"], ruling="merged", ruling_target="arc-agi")
        assert resolve_merge_target(conn, section="capability", target="arc",
                                    leaving={"arc-x"}) == "arc"


class TestAnExistingCycleIsFlaggedAndOneUndoFixesIt:
    """⚠ THE SHARED DATABASE ALREADY HOLDS THREE, written before the guard
    existed. They are reproduced here by writing the rows directly - the way
    they got there - rather than through `rule_entries`, which now refuses."""

    @pytest.fixture
    def cycle(self, conn, twins):
        merge = ("UPDATE board_entry SET ruling='merged', ruling_target=%s, "
                 "reviewed_at=now() WHERE slug=%s")
        conn.execute(merge, ("exploit-gym", "exploitgym"))
        conn.execute(merge, ("exploitgym", "exploit-gym"))
        conn.commit()

    def test_both_ends_are_flagged_not_hidden(self, conn, cycle):
        groups = list_for_review(conn)
        for slug in ("exploit-gym", "exploitgym"):
            g = _row(groups, slug)
            assert g is not None, f"{slug} vanished from the list; a cycle needs a person"
            assert g["merge_cycle"], f"{slug} is in a cycle and is not flagged"

    def test_one_undo_breaks_it(self, conn, cycle):
        ids = [r[0] for r in conn.execute(
            "SELECT id FROM board_entry WHERE slug='exploit-gym'").fetchall()]
        unrule_entry_ids(conn, ids=ids)
        conn.commit()
        groups = list_for_review(conn)
        host = _row(groups, "exploit-gym")
        assert host is not None and not host["merge_cycle"]
        assert [m["slug"] for m in host["merged_in"]] == ["exploitgym"], (
            "undoing one side should leave the other folded cleanly under it"
        )
