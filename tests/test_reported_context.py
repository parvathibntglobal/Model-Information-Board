"""FR-31, and the defect this lane has already shipped once.

A hard filter read an absent `supports_tools` as "cannot" and took a candidate
list from eleven models to one. Rule 6 was written from that. `reported_low` is
the same hazard on a different column, so these tests are about what happens
when nobody has reported.
"""

from __future__ import annotations

import pytest

from judge.curate.reported_context import (
    MIN_VOICES_FOR_LIMIT,
    ReportedContext,
    ReportedContextStore,
    Verdict,
)


class Conn:
    def __init__(self, row=None):
        self._row, self.sql, self.params = row, [], []

    def execute(self, sql, params=()):
        self.sql.append(sql)
        self.params.append(params)
        row = self._row

        class R:
            @staticmethod
            def fetchone():
                return row

            @staticmethod
            def fetchall():
                return [row] if row else []

        return R()


def reported(low=30_000, voices=3, **kw):
    defaults = dict(
        model_version_id="mv1",
        reported_low=low,
        voices=voices,
        quote_ids=tuple(f"q{i}" for i in range(voices)),
    )
    defaults.update(kw)
    return ReportedContext(**defaults)


class TestUnknownNeverExcludes:
    """The specific repair for a defect this lane shipped.

    An absent figure removing candidates surfaces as an absence with nothing on
    the page to disagree with, which is what makes this class of bug expensive.
    """

    def test_a_model_nobody_has_reported_on_is_unknown_not_failing(self):
        assert ReportedContext(model_version_id="mv1").check(100_000) is Verdict.UNKNOWN

    def test_a_missing_row_returns_an_answer_rather_than_None(self):
        """Returning None would make every caller write the absent case
        themselves, and one of them would get it wrong in the direction that
        excludes."""
        result = ReportedContextStore(Conn(row=None)).for_model("mv1")

        assert isinstance(result, ReportedContext)
        assert result.check(100_000) is Verdict.UNKNOWN

    def test_the_caveat_says_it_is_not_excluded(self):
        caveat = ReportedContext(model_version_id="mv1").caveat(100_000)

        assert caveat is not None
        assert "not excluded" in caveat
        assert "absence of reports is not a reported failure" in caveat

    def test_the_verdict_is_not_a_boolean(self):
        """A bool forces every caller to choose which way "we do not know"
        collapses, and the incident behind rule 6 was that collapse made
        silently."""
        assert not isinstance(ReportedContext(model_version_id="mv1").check(1), bool)
        assert set(Verdict) == {Verdict.MEETS, Verdict.FAILS, Verdict.UNKNOWN}


class TestOneVoiceIsNotALimit:
    """A single bad afternoon must not remove a model from every long-context
    recommendation."""

    def test_below_the_floor_is_unknown_rather_than_a_limit(self):
        assert (
            reported(low=30_000, voices=MIN_VOICES_FOR_LIMIT - 1).check(100_000) is Verdict.UNKNOWN
        )

    def test_at_the_floor_it_filters(self):
        assert reported(low=30_000, voices=MIN_VOICES_FOR_LIMIT).check(100_000) is Verdict.FAILS

    def test_the_uncorroborated_caveat_says_it_is_neither_confirmed_nor_excluded(self):
        caveat = reported(low=30_000, voices=1).caveat(100_000)

        assert caveat is not None
        assert "fewer than the 3 needed" in caveat
        assert "Not excluded, and not confirmed" in caveat


class TestTheFilterItself:
    def test_a_corroborated_limit_below_the_requirement_fails(self):
        assert reported(low=30_000).check(100_000) is Verdict.FAILS

    def test_a_corroborated_limit_at_or_above_the_requirement_meets(self):
        assert reported(low=128_000).check(128_000) is Verdict.MEETS

    def test_the_failure_caveat_carries_both_numbers(self):
        """Rule 7. "Fails" without the figures is not something a reader can
        disagree with."""
        caveat = reported(low=30_000, advertised=200_000).caveat(100_000)

        assert caveat is not None
        assert "30,000" in caveat and "100,000" in caveat
        assert "advertised window is 200,000" in caveat

    def test_a_passing_model_needs_no_caveat(self):
        assert reported(low=200_000).caveat(100_000) is None


class TestNoSynthesisedNumber:
    """Rule 3, at the place it would be most tempting."""

    def test_the_gap_is_None_rather_than_zero_when_a_figure_is_missing(self):
        assert reported(low=30_000, advertised=None).gap_to_advertised is None
        assert ReportedContext(model_version_id="mv1", advertised=200_000).gap_to_advertised is None

    def test_derive_takes_the_minimum_not_the_mean(self):
        """Averaging "worked at 200k" with "broke at 30k" gives 115k - a number
        nobody reported, which would pass a task the 30k report says fails."""
        import inspect

        source = inspect.getsource(ReportedContextStore.derive)
        assert "min(" in source
        assert "avg(" not in source.lower()

    def test_voices_are_counted_per_author_not_per_claim(self):
        """One person posting three times is one voice - the same rule the
        publication gate applies."""
        import inspect

        assert "count(DISTINCT" in inspect.getsource(ReportedContextStore.derive)


class TestProvenanceStopsProductionBooting:
    """`assert_no_fixtures` refuses startup outside development while any row
    here is hand_seeded - wired in collect/ops/preflight.py and verified
    firing."""

    def test_this_module_refuses_to_write_a_hand_seeded_row(self):
        with pytest.raises(ValueError, match="refusing to write provenance"):
            ReportedContextStore(Conn()).write(reported(provenance="hand_seeded"))

    def test_a_derived_row_is_harvested(self):
        store = ReportedContextStore(Conn(row=(30_000, 200_000, 2, ["q1", "q2"])))
        assert store.derive("mv1").provenance == "harvested"

    def test_the_insert_hardcodes_harvested(self):
        conn = Conn()
        ReportedContextStore(conn).write(reported())
        assert "'harvested'" in conn.sql[0]

    def test_a_hand_seeded_row_that_passes_still_carries_a_caveat(self):
        """It is a development value, not evidence, and a page that renders it
        silently would present a typed number as a finding."""
        caveat = reported(low=200_000, provenance="hand_seeded").caveat(100_000)

        assert caveat is not None
        assert "hand-seeded" in caveat
        assert "not evidence" in caveat


class TestOnlyVerifiedNegativeClaimsBecomeLimits:
    def test_the_derivation_requires_a_verified_quote(self):
        import inspect

        source = inspect.getsource(ReportedContextStore.derive)
        assert "quote_verified" in source

    def test_it_reads_negative_claims_only(self):
        """A reported limit is a report of something BREAKING. "Worked fine at
        200k" says nothing about where it stops."""
        import inspect

        assert "polarity = 'negative'" in inspect.getsource(ReportedContextStore.derive)
