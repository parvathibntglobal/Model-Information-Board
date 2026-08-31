"""`_document_facts` carries the document's author onto the facts.

The publish blocker (#9): claims were stored with `author_id = NULL` because the
pipeline never read it, so `cells.py` collapsed every claim into one anonymous
voice per platform and `independent_voices` could not exceed 1 — below the gate,
always. The fix reads `document.author_id` here and threads it to the claim.

DB-free on purpose: this checks the READ half (cli builds DocumentFacts from a
row) with a fake cursor. The write half — the claim row carrying it — belongs
with the DB-backed pipeline tests.
"""

from __future__ import annotations

from datetime import date

from judge.cli import _document_facts


class _Cur:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=()):
        self.sql = sql

    def fetchall(self):
        return self._rows


class _Conn:
    def __init__(self, rows):
        self._rows = rows

    def cursor(self):
        return _Cur(self._rows)


def test_a_known_author_reaches_the_facts():
    conn = _Conn([("doc1", "reddit", date(2026, 8, 1), "auth_42", True, False)])
    facts, undatable = _document_facts(conn, {"doc1"})
    assert not undatable
    assert facts["doc1"].author_id == "auth_42"


def test_a_null_author_stays_none_not_invented():
    # rule 6: an unknown author is the anonymous fallback downstream, never a
    # fabricated identity — so NULL in the row must arrive as None, not "".
    conn = _Conn([("doc1", "blog", date(2026, 8, 1), None, True, False)])
    facts, _ = _document_facts(conn, {"doc1"})
    assert facts["doc1"].author_id is None


def test_the_author_is_read_from_the_row_not_defaulted_away():
    # The query must actually SELECT author_id; if it fell back to a default the
    # two documents below would look identical, which is the bug this guards.
    conn = _Conn([
        ("doc1", "reddit", date(2026, 8, 1), "alice", True, False),
        ("doc2", "reddit", date(2026, 8, 1), "bob", True, False),
    ])
    facts, _ = _document_facts(conn, {"doc1", "doc2"})
    assert {facts["doc1"].author_id, facts["doc2"].author_id} == {"alice", "bob"}


def test_the_document_booleans_are_read_and_not_a_sentinel():
    """The 2026-08-30 repair, guarded here because this is the READ half.

    `has_conditions` and `has_numbers` were literal `None` in this function for
    the life of the project. `compute()`'s refusal tested `is UNSUPPLIED` and
    let `None` through, so `specificity_factor` scored every claim in the corpus
    as though both were False. Two documents that differ only in these columns
    must produce facts that differ.
    """
    conn = _Conn([
        ("doc1", "reddit", date(2026, 8, 1), "alice", True, True),
        ("doc2", "reddit", date(2026, 8, 1), "bob", False, False),
    ])
    facts, _ = _document_facts(conn, {"doc1", "doc2"})
    assert (facts["doc1"].has_numbers, facts["doc1"].has_conditions) == (True, True)
    assert (facts["doc2"].has_numbers, facts["doc2"].has_conditions) == (False, False)


def test_a_null_column_arrives_as_none_and_is_not_coerced():
    """NULL must reach `compute()` as NULL so the repaired check can refuse it.

    Coercing it here would move the silent default one layer up rather than
    removing it - and this is the layer where it would be hardest to see,
    because the refusal would never fire and the weight would look computed.
    """
    conn = _Conn([("doc1", "reddit", date(2026, 8, 1), "alice", None, None)])
    facts, _ = _document_facts(conn, {"doc1"})
    assert facts["doc1"].has_numbers is None
    assert facts["doc1"].has_conditions is None
