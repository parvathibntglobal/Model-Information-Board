"""The E1 line counts every provenance, and says so when they do not add up.

#404 added a third value to `model_version.provenance` on 2026-09-23 —
`unpolled`, a real model no poll will ever carry, hand-entered, and **not** a
fixture. Four rows took it. `judge/pages/pipeline_status.py` counted `seed` and
`polled` and nothing else.

TWO THINGS WENT WRONG, AND THE SECOND IS THE WORSE ONE.

    r[3] + r[4] stopped equalling r[0]   four rows in the total and in no bucket

    the caveat was `... if r[3] else None`, so once the migration took `seed`
    to 0 on staging THE WHOLE LINE DISAPPEARED — polled count included. The
    page went from "4 seeded, 344 polled" to nothing, on a database that had
    just gained a state rather than lost one.

⚠ A READER COULD NOT TELL "no unpolled models" FROM "this page cannot see
  unpolled models", which is rule 4 exactly — and it is the same defect #404
  was repairing in the data, reappearing one layer up because the data got a
  state the page did not.

Found reviewing #404 before it merged, confirmed by @anoojntglobal-sudo, and
left to this side of the boundary deliberately: a page repair inside a
migration PR is something a reviewer looking for schema risk has to read past.
"""

from __future__ import annotations

import pathlib
import re

from judge.pages.pipeline_status import _provenance_caveat

SPEC = pathlib.Path(__file__).resolve().parents[1] / "judge" / "pages" / "pipeline_status.py"


def e1_sql() -> str:
    src = SPEC.read_text(encoding="utf-8")
    start = src.index('"id": "E1"')
    return src[start:src.index('"id": "E2"')]


class TestEveryProvenanceIsCounted:
    def test_the_query_asks_for_all_three(self):
        sql = e1_sql()
        for value in ("'seed'", "'polled'", "'unpolled'"):
            assert f"provenance = {value}" in sql, value

    def test_it_counts_as_many_as_the_check_allows(self):
        """⚠ TIED TO THE CONSTRAINT, NOT TO A NUMBER I TYPED. If a fourth value
        is added to the CHECK and not to this query, the counts stop summing
        and this test says so at the point the schema changed — which is the
        only moment anybody is looking."""
        allowed = set(re.findall(
            r"provenance IN \(([^)]*)\)",
            (SPEC.parents[2] / "contract" / "tables.sql").read_text(encoding="utf-8"),
        )[0].replace("'", "").split(", "))
        counted = set(re.findall(r"provenance = '(\w+)'", e1_sql()))
        assert counted == allowed, (
            f"the CHECK allows {sorted(allowed)} and the page counts "
            f"{sorted(counted)}"
        )


class TestTheBreakdownIsAlwaysSaid:
    def test_it_speaks_when_no_fixture_is_present(self):
        """The exact state staging entered at 06:58 on 2026-09-23, and the one
        the old gate rendered as silence."""
        said = _provenance_caveat(total=348, seed=0, polled=344, unpolled=4)
        assert "344 polled" in said
        assert "4 unpolled" in said

    def test_the_fixture_warning_appears_only_with_fixtures(self):
        """Unconditional breakdown, conditional warning — the warning is about
        fixtures and there are none to warn about at zero."""
        assert "refused outside development" not in _provenance_caveat(
            total=348, seed=0, polled=344, unpolled=4)
        assert "refused outside development" in _provenance_caveat(
            total=359, seed=11, polled=344, unpolled=4)

    def test_it_is_not_gated_on_any_single_count(self):
        """⚠ THE DEFECT ITSELF. `... if r[3] else None` made the whole line
        conditional on the count most likely to be zero."""
        assert "if r[3] else None" not in e1_sql()
        assert "_provenance_caveat(" in e1_sql()


class TestItAdmitsWhenTheNumbersDoNotAddUp:
    def test_an_uncounted_provenance_is_named_rather_than_hidden(self):
        """Rule 6 pointed forwards. A fourth value would arrive exactly as the
        third did, and three numbers that quietly fail to sum are worse than a
        sentence saying they do not."""
        said = _provenance_caveat(total=350, seed=0, polled=344, unpolled=4)
        assert "2 row(s) carry a provenance this page does not name" in said

    def test_it_stays_quiet_when_they_do_add_up(self):
        said = _provenance_caveat(total=348, seed=0, polled=344, unpolled=4)
        assert "does not sum" not in said
