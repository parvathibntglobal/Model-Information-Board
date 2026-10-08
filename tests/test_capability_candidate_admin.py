"""The store behind proposed capabilities — rule / edit / delete.

The store tests use a fake connection to pin the SQL the ruling
constraints require: adopted/merged carry a target, declined forbids one, delete
is a hard delete.
"""

from __future__ import annotations

import pytest

from judge.app import app
from judge.store.capability_candidates import (
    delete_candidates,
    edit_candidates,
    rule_candidates,
)


class TestRoutes:
    def test_only_the_read_route_remains(self):
        """The rule / edit / delete ROUTES were removed 2026-10-08: nothing
        called them after the review panel went (#434). The store functions
        below stay, because `test_the_removed_queue_stopped_filling.py` keeps
        the 223 proposed rows readable and rulable from a shell."""
        paths = {getattr(r, "path", "") for r in app.routes}
        assert "/admin/capability-candidates" in paths
        for gone in ("rule", "edit", "delete"):
            assert f"/admin/capability-candidates/{gone}" not in paths


class _Cur:
    def __init__(self):
        self.calls = []
        self.rowcount = 3

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Conn:
    def __init__(self):
        self.cur = _Cur()

    def cursor(self):
        return self.cur


class TestRulingConstraints:
    def test_adopted_carries_its_target(self):
        c = _Conn()
        rule_candidates(c, proposed_key="k", ruling="adopted", ruling_target="tool_calling.par")
        _, params = c.cur.calls[-1]
        assert params[0] == "adopted" and params[1] == "tool_calling.par"

    def test_declined_forbids_a_target_even_if_one_is_passed(self):
        c = _Conn()
        rule_candidates(c, proposed_key="k", ruling="declined", ruling_target="ignored")
        _, params = c.cur.calls[-1]
        assert params[0] == "declined" and params[1] is None

    def test_adopt_without_a_target_is_refused(self):
        with pytest.raises(ValueError):
            rule_candidates(_Conn(), proposed_key="k", ruling="adopted", ruling_target=None)

    def test_an_unknown_ruling_is_refused(self):
        with pytest.raises(ValueError):
            rule_candidates(_Conn(), proposed_key="k", ruling="whatever", ruling_target=None)


class TestEditAndDelete:
    def test_edit_updates_the_definition(self):
        c = _Conn()
        edit_candidates(c, proposed_key="k", new_definition="a clearer definition")
        sql, params = c.cur.calls[-1]
        assert "definition = %s" in sql and "a clearer definition" in params

    def test_edit_with_nothing_to_change_is_a_no_op(self):
        c = _Conn()
        assert edit_candidates(c, proposed_key="k") == 0
        assert c.cur.calls == []

    def test_delete_is_a_hard_delete_by_key(self):
        c = _Conn()
        n = delete_candidates(c, proposed_key="k")
        assert "DELETE FROM capability_candidate" in c.cur.calls[-1][0]
        assert n == 3
