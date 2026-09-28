"""The promotion report: every untracked model with a claim, ranked by the
people who reported it, with nothing cut and both caveats on the report.

Claims about untracked models arrive as a side effect of other models' runs -
Fable 5 and Qwen3.8 27B both did - and nothing surfaced them. This report does,
on the registry poll's schedule. It proposes; a person seats and tracks.
"""

from __future__ import annotations

import pathlib
from datetime import date

from scripts.promotion_report import render, untracked_ranked

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _row(mv, can, name, *, claims, authors, docs, no_author=0, searchable=True):
    return {"model_version_id": mv, "canonical_id": can, "display_name": name,
            "claims": claims, "authors": authors, "claims_without_author": no_author,
            "documents": docs, "platforms": 2, "first_claim": date(2026, 9, 1),
            "last_claim": date(2026, 9, 24), "searchable": searchable}


class TestTheRanking:
    def test_authors_outrank_claims(self):
        """50 claims from 3 people and 50 from 27 are different facts."""
        rows = [_row("a", "x/prolific", "Prolific", claims=50, authors=3, docs=4),
                _row("b", "x/broad", "Broad", claims=50, authors=27, docs=29)]
        assert [r["display_name"] for r in untracked_ranked(rows, set())] == ["Broad", "Prolific"]

    def test_documents_break_an_author_tie_then_claims(self):
        rows = [_row("a", "x/a", "A", claims=9, authors=5, docs=5),
                _row("b", "x/b", "B", claims=3, authors=5, docs=7),
                _row("c", "x/c", "C", claims=12, authors=5, docs=5)]
        assert [r["display_name"] for r in untracked_ranked(rows, set())] == ["B", "C", "A"]

    def test_tracked_matches_either_id_as_the_models_page_does(self):
        """Fable 5.1 is tracked as `anthropic/claude-fable-5-1`, which is its ROW
        id; its canonical id is `anthropic/claude-fable-5.1`."""
        rows = [_row("anthropic/claude-fable-5-1", "anthropic/claude-fable-5.1", "Fable 5.1",
                     claims=68, authors=26, docs=27),
                _row("mv_f5", "anthropic/claude-fable-5", "Fable 5",
                     claims=52, authors=27, docs=29)]
        out = untracked_ranked(rows, {"anthropic/claude-fable-5-1"})
        assert [r["display_name"] for r in out] == ["Fable 5"]


class TestTheReport:
    def _report(self, rows):
        return render(untracked_ranked(rows, set()), tracked_count=16)

    def test_every_model_is_listed_and_nothing_is_cut(self):
        rows = [_row(f"m{i}", f"x/m{i}", f"M{i}", claims=1, authors=1, docs=1) for i in range(40)]
        report = self._report(rows)
        assert all(f"| M{i} (`x/m{i}`)" in report for i in range(40))

    def test_both_caveats_are_on_the_report_and_the_count_is_computed(self):
        rows = [_row("a", "x/a", "A", claims=10, authors=4, docs=4, no_author=3),
                _row("b", "x/b", "B", claims=5, authors=2, docs=2, no_author=4)]
        report = self._report(rows)
        assert "`author_id` is per platform" in report and "counts as two authors" in report
        assert "7 of these 15 claim(s) carry no author" in report

    def test_there_is_no_threshold_and_no_candidates_cut(self):
        report = self._report([_row("a", "x/a", "A", claims=1, authors=1, docs=1)])
        assert "there is no threshold" in report
        for cut in ("strong candidate", "recommended", "promote these"):
            assert cut not in report.lower()

    def test_a_model_with_no_searchable_alias_says_seat_first(self):
        row = _row("a", "x/a", "A", claims=5, authors=5, docs=5, searchable=False)
        report = self._report([row])
        assert "**no - seat first**" in report
        assert "1 of 1 have no searchable alias" in report

    def test_claims_sit_beside_authors_and_documents_with_no_ratio(self):
        """Every figure is a count (rule 3). A claims-per-author figure would be
        synthesised, so the report carries the three counts side by side."""
        report = self._report([_row("a", "x/a", "A", claims=39, authors=3, docs=3)])
        assert "| A (`x/a`) | 3 | 3 | 39 |" in report
        assert "/author" not in report and "per author" not in report


class TestItIsReadOnlyAndPosted:
    def test_the_connection_is_read_only(self):
        src = (ROOT / "scripts" / "promotion_report.py").read_text(encoding="utf-8")
        assert "default_transaction_read_only%3Don" in src

    def test_an_oversized_report_fails_rather_than_being_cut(self):
        src = (ROOT / "scripts" / "promotion_report.py").read_text(encoding="utf-8")
        assert "Not posted rather than cut" in src

    def test_the_poll_posts_it_and_refuses_loudly_without_an_issue(self):
        wf = (ROOT / ".github" / "workflows" / "registry-poll.yml").read_text(encoding="utf-8")
        assert "PROMOTION_ISSUE: ${{ vars.PROMOTION_ISSUE }}" in wf
        assert "python scripts/promotion_report.py --out promotion.md" in wf
        assert 'gh issue comment "$PROMOTION_ISSUE" --body-file promotion.md' in wf
        assert "promotion report not posted: vars.PROMOTION_ISSUE is not set" in wf
        poll = wf.index("Poll the registry and refresh the window")
        assert poll < wf.index("python scripts/promotion_report.py --out")
