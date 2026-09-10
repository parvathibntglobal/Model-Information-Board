"""The ancestry check, and the open-PR check that exists because it fires too late.

WHY THIS FILE EXISTS AT ALL, HAVING NOT EXISTED FOR THE CHECK'S FIRST WEEK.
`scripts/check_merged_prs_reached_main.py` shipped untested, on the reasoning
that its two halves are `git merge-base` and the GitHub API and neither is ours
to test. That was right about the halves and wrong about the JOIN: the
classification between them - which pair of (state, ancestry) is a defect - is
entirely ours, and it is the part that decides whether a build goes red.

The check earned its keep on 2026-09-10 by catching #243 in 25 seconds. The
`--open-prs` half added the same day has never fired in anger, and a reporter
that has never produced output is indistinguishable from one that cannot.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_merged_prs_reached_main.py"


def _load():
    spec = importlib.util.spec_from_file_location("_ancestry_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def mod():
    return _load()


class TestStackedOpenPrs:
    """The 15-second window. #243 lived in it and nothing was watching."""

    def _wire(self, mod, monkeypatch, *, rows, merged_bases):
        monkeypatch.setattr(mod, "open_prs", lambda limit: rows)
        # `origin/<base>` resolves to a fake tip; a base in `merged_bases` is an
        # ancestor of main.
        monkeypatch.setattr(
            mod, "_git",
            lambda *args: f"tip-{args[-1]}" if args[0] == "rev-parse" else "")
        monkeypatch.setattr(
            mod, "_is_ancestor",
            lambda commit, of: commit.removeprefix("tip-origin/") in merged_bases)

    def test_a_pr_based_on_main_is_not_reported(self, mod, monkeypatch):
        self._wire(mod, monkeypatch,
                   rows=[{"number": 1, "title": "t", "headRefName": "h",
                          "baseRefName": "main"}],
                   merged_bases=set())
        assert mod.stacked(main="origin/main", limit=100) == []

    def test_a_stack_whose_base_is_unmerged_is_reported_but_not_as_stranding(
        self, mod, monkeypatch
    ):
        # A legitimate stack. It is worth a notice - merging the base into main
        # without merging this first leaves it behind - and it is NOT the defect.
        self._wire(mod, monkeypatch,
                   rows=[{"number": 2, "title": "t", "headRefName": "top",
                          "baseRefName": "bottom"}],
                   merged_bases=set())
        rows = mod.stacked(main="origin/main", limit=100)
        assert len(rows) == 1
        assert rows[0]["_base_merged"] is False

    def test_a_base_already_on_main_is_flagged_as_the_sharp_case(
        self, mod, monkeypatch
    ):
        """THE #243 STATE, reconstructed.

        #242 merged to main at 06:48:51Z; #243's base was #242's branch and it
        was still open. Merging it then put its commits on a branch nothing
        would carry - which is what happened 15 seconds later.
        """
        self._wire(mod, monkeypatch,
                   rows=[{"number": 243, "title": "one record per meter",
                          "headRefName": "fix/rapidapi-quota-per-meter",
                          "baseRefName": "fix/x-credential-named-and-the-premise-corrected"}],
                   merged_bases={"fix/x-credential-named-and-the-premise-corrected"})
        rows = mod.stacked(main="origin/main", limit=100)
        assert len(rows) == 1
        assert rows[0]["_base_merged"] is True

    def test_the_sharp_case_sorts_first(self, mod, monkeypatch):
        # Worst first, because the report is read from the top and one of these
        # needs acting on today.
        self._wire(mod, monkeypatch,
                   rows=[{"number": 10, "title": "t", "headRefName": "a",
                          "baseRefName": "unmerged-base"},
                         {"number": 11, "title": "t", "headRefName": "b",
                          "baseRefName": "landed-base"}],
                   merged_bases={"landed-base"})
        rows = mod.stacked(main="origin/main", limit=100)
        assert [p["number"] for p in rows] == [11, 10]

    def test_a_missing_base_branch_is_named_rather_than_skipped(
        self, mod, monkeypatch
    ):
        # An unknown ref must not read as "not merged" - that is a definite
        # answer from an absent one (rule 6). It is reported with the base
        # marked unknown.
        monkeypatch.setattr(mod, "open_prs", lambda limit: [
            {"number": 12, "title": "t", "headRefName": "h", "baseRefName": "gone"}])
        monkeypatch.setattr(mod, "_git", lambda *args: "")
        rows = mod.stacked(main="origin/main", limit=100)
        assert len(rows) == 1
        assert rows[0]["_base_known"] is False
        assert rows[0]["_base_merged"] is False

    def test_the_report_never_fails_the_build(self, mod, monkeypatch, capsys):
        """Rule 8, and it is load-bearing rather than formal.

        `_base_merged` is not by itself a defect: #245 resolved exactly this
        state by re-merging the base branch. So the condition is "needs a
        follow-up action", not "is wrong", and it ships as a warning until its
        false-positive rate against real stacks is measured.
        """
        self._wire(mod, monkeypatch,
                   rows=[{"number": 243, "title": "t", "headRefName": "top",
                          "baseRefName": "landed"}],
                   merged_bases={"landed"})
        assert mod._report_stacked(main="origin/main", limit=100) == 0
        out = capsys.readouterr().out
        assert "::warning" in out, "it must annotate the PR, not only the log"
        assert "NEVER FAILS THE BUILD" in out


class TestThePopulationIsStated:
    """Rule 7 on the check itself. `checked 60` stood for `checked` for a week."""

    def test_a_run_at_its_limit_says_it_may_be_truncated(self, mod, monkeypatch, capsys):
        monkeypatch.setattr(mod, "merged_prs",
                            lambda limit: [{"number": i, "title": "t",
                                            "headRefName": "h", "baseRefName": "main",
                                            "headRefOid": "sha"} for i in range(5)])
        monkeypatch.setattr(mod, "_is_ancestor", lambda commit, of: True)
        monkeypatch.setattr(mod, "_git", lambda *args: "commit")
        assert mod.main(["--main", "origin/main", "--limit", "5"]) == 0
        out = capsys.readouterr().out
        assert "NOT ALL OF THEM" in out
        assert "--limit 0" in out

    def test_a_run_under_its_limit_makes_no_such_claim(self, mod, monkeypatch, capsys):
        monkeypatch.setattr(mod, "merged_prs",
                            lambda limit: [{"number": 1, "title": "t",
                                            "headRefName": "h", "baseRefName": "main",
                                            "headRefOid": "sha"}])
        monkeypatch.setattr(mod, "_is_ancestor", lambda commit, of: True)
        monkeypatch.setattr(mod, "_git", lambda *args: "commit")
        assert mod.main(["--main", "origin/main", "--limit", "50"]) == 0
        assert "NOT ALL OF THEM" not in capsys.readouterr().out

    def test_limit_zero_asks_for_every_merged_pr(self, mod, monkeypatch):
        seen = {}

        def fake(limit):
            seen["limit"] = limit
            return []

        monkeypatch.setattr(mod, "merged_prs", fake)
        monkeypatch.setattr(mod, "_git", lambda *args: "commit")
        mod.main(["--main", "origin/main", "--limit", "0"])
        assert seen["limit"] == mod.ALL_LIMIT


class TestMergedPrsStillGate:
    """The half that already works must keep failing the build."""

    def test_a_pr_merged_into_a_branch_not_on_main_fails(self, mod, monkeypatch):
        monkeypatch.setattr(mod, "merged_prs", lambda limit: [{
            "number": 243, "title": "one record per meter",
            "headRefName": "fix/rapidapi-quota-per-meter",
            "headRefOid": "3d13b63f68",
            "baseRefName": "fix/x-credential-named-and-the-premise-corrected",
            "mergeCommit": {"oid": "5127ee5647"},
            "mergedAt": "2026-09-10T06:49:06Z",
        }])
        monkeypatch.setattr(mod, "_is_ancestor", lambda commit, of: False)
        monkeypatch.setattr(mod, "_git", lambda *args: "commit")
        assert mod.main(["--main", "origin/main", "--limit", "0"]) == 1
