"""GET /models - the registry as a list, with advertised price.

The test worth having here is not "does it return rows". It is rule 6: a NULL
price must still be NULL by the time it reaches the caller. Five models in the
registry are routers with no rate of their own, and the cheapest thing a
serialiser can do to a missing number is turn it into 0.0 - which would put the
word "free" on five models that bill.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from judge.app import app
from judge.pages.roster import RosterReader


class _FakeConn:
    """Two queries, in the order RosterReader issues them."""

    def __init__(self, rows, observed_at=None):
        self._rows = rows
        self._observed_at = observed_at
        self.queries = []
        #: The parameters each query was given. #302 scoped the roster to one
        #: `pipeline_version`, and a fake that swallowed the parameters would
        #: let a future unscoped query pass every test in this file.
        self.params = []

    def execute(self, sql, params=None):
        self.queries.append(sql)
        self.params.append(params)
        if "pricing_history" in sql:
            return _Result([(self._observed_at,)])
        return _Result(self._rows)


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0]


def _row(name, price_in, price_out, *, cells=0, published=0, capabilities=None,
         entries=0, sections=None, stale=0, stale_versions=None):
    return (
        f"mv_{name}", name, "vendor", f"vendor/{name}",
        price_in, price_out, None,
        128000, 4096,
        True, False, True, None, None,
        # ⚠ `stale` AND `stale_versions` SIT BETWEEN THE CELL COUNTS AND THE
        #   CAPABILITY KEYS, because that is where #302 put them in the SQL.
        #   Appending them at the end here instead would pass this file and
        #   read a version array as a capability list against the real query.
        cells, published, stale, stale_versions, capabilities,
        # BOARD ENTRIES, and they are the last two on purpose: the SQL appends
        # them, so a row built here that forgets them fails loudly on an
        # IndexError rather than shifting a cell count into a board count.
        entries, sections,
    )


def test_null_price_stays_null_and_zero_stays_zero():
    """Rule 6. The router and the free model must not arrive identical."""
    conn = _FakeConn([_row("router", None, None), _row("free", 0, 0)])

    models = {m["display_name"]: m for m in RosterReader(conn).all().models}

    assert models["router"]["price_in"] is None
    assert models["router"]["price_out"] is None
    assert models["free"]["price_in"] == 0.0
    assert models["free"]["price_out"] == 0.0
    # The distinction is the whole point: if these compared equal, a UI could
    # not tell "no published rate" from "costs nothing".
    assert models["router"]["price_in"] != models["free"]["price_in"]


def test_summary_counts_the_unpriced_rather_than_hiding_them():
    conn = _FakeConn([_row("router", None, None), _row("paid", 1, 2)])
    assert "1 publish no rate at all" in RosterReader(conn).all().summary


def test_summary_omits_the_caveat_when_everything_is_priced():
    conn = _FakeConn([_row("paid", 1, 2)])
    assert "no rate at all" not in RosterReader(conn).all().summary


def test_ordered_by_name_not_by_price():
    """A default sort by cost would be a recommendation made without evidence."""
    conn = _FakeConn([])
    RosterReader(conn).all()
    assert "ORDER BY mv.display_name" in conn.queries[0]
    assert "price" not in conn.queries[0].split("ORDER BY")[1]


def test_roster_503s_without_a_database(monkeypatch):
    """Same operational-state distinction every other read surface draws."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    response = TestClient(app).get("/models")

    assert response.status_code == 503
    assert "not the same as a board with nothing on it" in response.json()["detail"]


@pytest.mark.parametrize(
    "path",
    ["/models/mv1", "/models/google/gemini-2.5-flash"],
)
def test_the_detail_route_still_wins_for_ids(monkeypatch, path):
    """The literal /models must not swallow /models/{id:path}.

    A 503 proves the request reached the detail handler and stopped at the
    database; a 200 with a roster in it would mean the new route had eaten
    every model page.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)

    response = TestClient(app).get(path)

    assert response.status_code == 503


# ── the evidence state, which is three-valued on purpose ────────────────────


def test_no_cells_is_unreported():
    conn = _FakeConn([_row("quiet", 1, 2)])
    m = RosterReader(conn).all().models[0]
    assert m["evidence"] == {
        "state": "unreported", "cells": 0, "published": 0, "capabilities": [],
        # ⚠ CARRIED ON `unreported` TOO, AND ZERO IS A MEASUREMENT HERE (#302).
        #   0 says we looked at every other generation and found nothing. The
        #   state that needs this most is exactly this one: a model whose only
        #   cells are older reads `unreported`, and without the count that says
        #   "nobody has discussed this" about a model we have not re-fetched.
        "not_recounted": 0, "not_recounted_since": [],
    }


def test_cells_that_did_not_clear_the_gate_are_insufficient_not_evidenced():
    """The state that makes a boolean filter wrong.

    3 of 342 models have a cell today and none has a published one. Calling
    that "has evidence" would show a reader who asked for evidence three models
    sitting at n_eff 0.012 against a gate of 3.0.
    """
    conn = _FakeConn([_row("partial", 1, 2, cells=2, published=0)])
    m = RosterReader(conn).all().models[0]
    assert m["evidence"]["state"] == "insufficient"
    assert m["evidence"]["cells"] == 2
    assert m["evidence"]["published"] == 0


def test_a_published_cell_is_published():
    conn = _FakeConn([_row("proven", 1, 2, cells=3, published=1)])
    assert RosterReader(conn).all().models[0]["evidence"]["state"] == "published"


def test_the_three_states_never_compare_equal():
    """Rule 4 as an assertion: silence must not render as criticism, and
    below-the-gate must not render as proven."""
    conn = _FakeConn([
        _row("quiet", 1, 2),
        _row("partial", 1, 2, cells=1),
        _row("proven", 1, 2, cells=1, published=1),
    ])
    states = {m["display_name"]: m["evidence"]["state"] for m in RosterReader(conn).all().models}
    assert len(set(states.values())) == 3, states


# ── which capability, not just how many ─────────────────────────────────────


def test_the_capability_keys_travel_with_the_row():
    """Claude Haiku 4.5 has one cell and it is instruction.adherence.

    "1 cell" cannot answer "who has been discussed for following instructions",
    which is the question the board exists for.
    """
    conn = _FakeConn([_row("haiku", 1, 5, cells=1, capabilities=["instruction.adherence"])])
    m = RosterReader(conn).all().models[0]
    assert m["evidence"]["capabilities"] == ["instruction.adherence"]


def test_no_cells_means_an_empty_list_not_a_missing_key():
    """A caller doing `.includes(...)` must not have to guard for undefined."""
    conn = _FakeConn([_row("quiet", 1, 2)])
    assert RosterReader(conn).all().models[0]["evidence"]["capabilities"] == []


def test_a_null_from_array_agg_becomes_an_empty_list():
    """array_agg over zero rows is NULL in postgres, not an empty array.

    Passing that straight through would put `None` where the client expects a
    list, and `null.includes` is a crash rather than a miss.
    """
    conn = _FakeConn([_row("quiet", 1, 2, cells=0, published=0, capabilities=None)])
    assert RosterReader(conn).all().models[0]["evidence"]["capabilities"] == []


class TestTheBoardTravelsBesideTheCells:
    """Two counts, never one. The page showed only cells until 2026-09-15.

    A cell is COUNTED AND GATED - `insufficient` means we counted and it was
    not enough. A `board_entry` is UNGATED - somebody said this, with no claim
    about corroboration. Collapsing them misreads in whichever direction you
    collapse, measured on DeepSeek V4 Pro:

        entries only   23 reports  -> reads as 23 findings, when ZERO cleared
                                      the publication bar
        cells only      6 cells    -> reads as a near-empty model, while 22
                                      entries about it sit unread

    The second is what the page did, which is why a fetch that produced 50
    board entries changed nothing a reader could see.
    """

    def test_the_counts_travel_with_the_row(self):
        conn = _FakeConn([_row("d", 1, 2, cells=6, published=0,
                               capabilities=["code.generation"],
                               entries=23,
                               sections={"capability": 12, "metric": 8, "best_for": 3})])
        m = RosterReader(conn).all().models[0]

        assert m["evidence"]["state"] == "insufficient"
        assert m["evidence"]["cells"] == 6
        assert m["board"]["entries"] == 23

    def test_sections_are_counted_and_ordered_biggest_first(self):
        conn = _FakeConn([_row("d", 1, 2, entries=23,
                               sections={"best_for": 3, "capability": 12, "metric": 8})])
        board = RosterReader(conn).all().models[0]["board"]

        assert list(board["sections"].items()) == [
            ("capability", 12), ("metric", 8), ("best_for", 3)
        ], "the row reads them biggest first; a count alone does not say where"

    def test_the_board_carries_no_state_word(self):
        """An entry has been through no gate, so it gets no gate vocabulary.

        `evidence` has a `state` because a cell has a verdict behind it. Giving
        the board one would invite comparing `insufficient` against some board
        word as if they were the same scale.
        """
        conn = _FakeConn([_row("d", 1, 2, cells=6, entries=23,
                               sections={"capability": 23})])
        board = RosterReader(conn).all().models[0]["board"]

        assert "state" not in board
        assert "published" not in board

    def test_no_entries_is_zero_rather_than_a_missing_key(self):
        """Rule 6 at the page boundary: a page must tell "none" from "unsaid"."""
        conn = _FakeConn([_row("d", 1, 2, cells=6, entries=0, sections=None)])
        board = RosterReader(conn).all().models[0]["board"]

        assert board == {"entries": 0, "sections": {}}

    def test_entries_without_cells_and_cells_without_entries_both_survive(self):
        """Neither is a subset of the other, which is the reason both are shown."""
        conn = _FakeConn([
            _row("cells_only", 1, 2, cells=4, capabilities=["code.generation"]),
            _row("board_only", 1, 2, cells=0, entries=7, sections={"metric": 7}),
        ])
        cells_only, board_only = RosterReader(conn).all().models

        assert cells_only["evidence"]["state"] == "insufficient"
        assert cells_only["board"]["entries"] == 0
        assert board_only["evidence"]["state"] == "unreported"
        assert board_only["board"]["entries"] == 7, (
            "a model with board reports and no cell reads as `unreported` on the "
            "gate and must still show its reports - that combination is exactly "
            "what the old page could not express"
        )
