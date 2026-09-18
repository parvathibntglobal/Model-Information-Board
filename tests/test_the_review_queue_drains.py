"""The board review shows a queue that empties, not a window that never moves.

⚠ WHAT THIS REPLACED, AND WHY IT COULD NOT BE WORKED THROUGH. `list_for_review`
  took the 5 newest quotes REGARDLESS of ruling. Every quote carries its own
  adopt/decline button, so a reviewer could rule all five — and then see exactly
  the same five again, because the window was pinned to `created_at` and ruling
  a row does not change when it was created.

  Measured on the shared database 2026-09-17: `metric/cost-per-token` holds 149
  entries and `best_for/coding-agent` holds 125, all unruled. 120 of those 125
  were unreachable by the per-quote buttons sitting on the page — only a
  section-wide ruling could touch them, which is the blunt instrument the
  per-quote buttons exist to avoid.

Two windows now, partitioned by whether a row is ruled: the QUEUE (up to 5
unruled, oldest first) and the RECEIPT (up to 5 ruled, newest first). These
tests are about the queue emptying and the receipt catching what left it.
"""

from __future__ import annotations

import pathlib

import psycopg
import pytest

from judge.store.board_entries import (
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
def twelve(conn):
    """One slug with twelve quotes, created a minute apart so order is total.

    Twelve rather than six: two full windows plus a remainder, so "the next five
    arrive" is distinguishable from "the last one arrives".
    """
    conn.execute(
        "INSERT INTO document (id, source, external_id, url, text_ref, "
        "content_hash, status) VALUES "
        "('doc1','devto','1','https://dev.to/a','ref1','h1','kept')"
    )
    for i in range(1, 13):
        conn.execute(
            "INSERT INTO board_entry (id, section, slug, name, definition, "
            "document_id, quote, quote_verified, polarity, proposer_model, "
            "pipeline_version, created_at) VALUES "
            "(%s,'capability','tool-use','Tool use','Calls tools correctly.',"
            "'doc1',%s,true,'positive','m','v1', "
            "timestamptz '2026-01-01 00:00:00+00' + (%s * interval '1 minute'))",
            (f"be{i:02d}", f"quote number {i}", i),
        )
    conn.commit()
    return [f"be{i:02d}" for i in range(1, 13)]


def _group(conn):
    groups = list_for_review(conn)
    assert len(groups) == 1
    return groups[0]


def test_the_queue_holds_only_unruled_quotes(conn, twelve):
    group = _group(conn)
    assert len(group["quotes"]) == 5
    assert all(q["ruling"] is None for q in group["quotes"])
    assert group["unruled"] == 12
    assert group["ruled"] == 0


def test_the_queue_starts_at_the_OLDEST_unruled(conn, twelve):
    """⚠ Oldest-first, and it is the one ordering choice here that is not free.

    Everything else in this file is newest-first. A queue worked newest-first
    never reaches its tail: fresh evidence keeps arriving at the head, so the
    oldest unruled quote would be the last thing anyone ever saw rather than
    the first. Newest-first is right for a sample and wrong for a backlog.
    """
    ids = [q["id"] for q in _group(conn)["quotes"]]
    assert ids == ["be01", "be02", "be03", "be04", "be05"]


def test_ruling_the_visible_five_reveals_the_next_five(conn, twelve):
    """THE WHOLE POINT. Before this, the same five came back forever."""
    first = [q["id"] for q in _group(conn)["quotes"]]
    rule_entry_ids(conn, ids=first, ruling="adopted")
    conn.commit()

    second = _group(conn)
    assert [q["id"] for q in second["quotes"]] == [
        "be06", "be07", "be08", "be09", "be10"
    ]
    assert not {q["id"] for q in second["quotes"]} & set(first), (
        "a ruled quote came back in the queue"
    )
    assert second["unruled"] == 7
    assert second["ruled"] == 5


def test_the_whole_slug_can_be_worked_through_five_at_a_time(conn, twelve):
    """Twelve quotes, five at a time, and the queue reaches empty.

    Asserted by DRAINING it rather than by trusting the arithmetic — the defect
    this replaces looked correct in exactly the same arithmetic and returned the
    same page each round.
    """
    seen: list[str] = []
    for _ in range(5):  # more rounds than needed; it must stop on its own
        batch = [q["id"] for q in _group(conn)["quotes"]]
        if not batch:
            break
        assert not set(batch) & set(seen), "a quote came back after being ruled"
        seen.extend(batch)
        rule_entry_ids(conn, ids=batch, ruling="adopted")
        conn.commit()

    assert sorted(seen) == twelve
    final = _group(conn)
    assert final["quotes"] == []
    assert final["unruled"] == 0
    assert final["ruled"] == 12


def test_a_ruled_quote_is_still_findable(conn, twelve):
    """⚠ Otherwise a misclick is invisible the moment it happens.

    A ruled quote leaves the queue and says nothing on its way out. Without a
    receipt, a wrong decline is unfindable: the row is simply gone from the
    page, and the reviewer has no way to see what they did, let alone undo it.
    """
    rule_entry_ids(conn, ids=["be01"], ruling="declined")
    conn.commit()

    group = _group(conn)
    assert [q["id"] for q in group["ruled_sample"]] == ["be01"]
    assert group["ruled_sample"][0]["ruling"] == "declined"
    assert "be01" not in [q["id"] for q in group["quotes"]]
    # ⚠ RULE 7. The receipt is a SAMPLE, so the count travels beside it.
    assert group["ruled"] == 1


def test_the_receipt_is_newest_first_and_capped(conn, twelve):
    """A sample, not a second queue — the most recent decisions are the ones
    a reviewer is checking, and all twelve would just rebuild the wall."""
    rule_entry_ids(conn, ids=[f"be{i:02d}" for i in range(1, 8)], ruling="adopted")
    conn.commit()

    group = _group(conn)
    assert len(group["ruled_sample"]) == 5
    assert [q["id"] for q in group["ruled_sample"]] == [
        "be07", "be06", "be05", "be04", "be03"
    ]
    assert group["ruled"] == 7


def test_undoing_a_ruling_puts_the_quote_back_in_the_queue(conn, twelve):
    """The queue is derived, not stored, so undo has to work without knowing
    about it. Asserted because a queue built on a status column is exactly the
    kind that gets out of step with the column it is built on."""
    rule_entry_ids(conn, ids=["be01"], ruling="declined")
    conn.commit()
    assert "be01" not in [q["id"] for q in _group(conn)["quotes"]]

    unrule_entry_ids(conn, ids=["be01"])
    conn.commit()

    group = _group(conn)
    assert group["quotes"][0]["id"] == "be01", "the restored quote is not at the head"
    assert group["unruled"] == 12
    assert group["ruled"] == 0
    assert group["ruled_sample"] == []


def test_a_section_wide_ruling_still_covers_everything(conn, twelve):
    """Both modes coexist. The per-quote queue is for reading them one at a
    time; the section-wide ruling is for a slug you have already decided about,
    and it must not have been narrowed to the five on screen."""
    rule_entries(conn, section="capability", slug="tool-use", ruling="declined")
    conn.commit()

    group = _group(conn)
    assert group["unruled"] == 0
    assert group["ruled"] == 12
    assert group["quotes"] == []
    assert group["ruling"] == "declined", "a wholly-ruled slug should say so"
