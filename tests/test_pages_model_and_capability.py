"""The two evidence pages, and the state each is most likely to get wrong.

Both are built against an EMPTY database on purpose. Every one of these pages
will spend its first weeks with no cells at all, and "what does it say when it
knows nothing" is the question rule 4 exists to answer.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from judge.config import capabilities
from judge.pages.capability import CapabilityPage, CapabilityPageReader, ModelStanding
from judge.pages.model import (
    CapabilityView,
    ConditionSlice,
    ModelPage,
    ModelPageReader,
)


class Conn:
    def __init__(self, rows=(), total=None):
        self._rows, self._total, self.sql = list(rows), total, []

    def execute(self, sql, params=()):
        self.sql.append(sql)
        rows, total = self._rows, self._total

        class R:
            @staticmethod
            def fetchall():
                return rows

            @staticmethod
            def fetchone():
                return (total,) if total is not None else None

        return R()


def a_slice(capability="summarization.fidelity", bucket="any", status="published", **kw):
    defaults = dict(
        capability_key=capability,
        condition_bucket=bucket,
        status=status,
        consensus_phrase="two engineers report dropped clauses",
        conditional_note=None,
        independent_voices=3,
        platform_count=2,
        positive=0,
        negative=3,
        quote_ids=("q1",),
    )
    defaults.update(kw)
    return ConditionSlice(**defaults)


# ── the model page ────────────────────────────────────────────────────────


class TestSilenceRendersDistinctlyFromCriticism:
    """FR-24 and rule 4. The failure is invisible: a page listing only what it
    has evidence for shows "nobody looked" and "nobody complained" identically."""

    def test_every_tracked_capability_appears_even_with_no_cells(self):
        page = ModelPageReader(Conn()).build("mv1")

        assert len(page.capabilities) == len(capabilities()) == 14, (
            "the page enumerates the rows it got back rather than the contract, "
            "so a capability nobody discussed cannot appear at all"
        )
        assert len(page.unreported) == 14

    def test_unreported_and_insufficient_are_different_states(self):
        unreported = CapabilityView(key="k", failure_mode="loud")
        insufficient = CapabilityView(
            key="k", failure_mode="loud", slices=(a_slice(status="insufficient"),)
        )

        assert unreported.unreported and not unreported.insufficient
        assert insufficient.insufficient and not insufficient.unreported
        assert unreported.headline != insufficient.headline

    def test_a_silent_capability_with_no_evidence_says_absence_is_not_safety(self):
        """The most dangerous cell on the page, and it is an empty one."""
        view = CapabilityView(key="summarization.fidelity", failure_mode="silent")
        headline = view.headline

        assert "fails silently" in headline
        assert "not reassurance" in headline
        assert "no error for anyone to report" in headline

    def test_a_loud_capability_with_no_evidence_does_not_borrow_that_warning(self):
        """The warning has to mean something. On every empty capability it is
        furniture."""
        view = CapabilityView(key="format.structured_output", failure_mode="loud")
        assert "fails silently" not in view.headline

    def test_the_summary_names_the_silent_unreported_count(self):
        # A SWEPT model with no cells — we looked and found nothing, which is the
        # only state where "these fail silently, so absence is not safety" applies.
        # The stub's fetchone() is the `last_swept_at` read on the model page, so a
        # timestamp here makes the page tracked (#33 Q2). Without it the page is
        # NOT-TRACKED and leads with "we have not looked", a different silence.
        swept = datetime(2026, 8, 20, tzinfo=UTC)
        page = ModelPageReader(Conn(total=swept)).build("mv1")

        assert page.tracked
        assert "0 of 14 tracked capabilities" in page.summary
        assert "fail silently" in page.summary
        assert "not evidence of safety" in page.summary


class TestConditionsAreNotAveraged:
    """FR-25. Averaging publishes "mediocre", which is true-ish, useless, and
    buries the rule a reader would act on."""

    def test_two_buckets_stay_two_slices(self):
        view = CapabilityView(
            key="tool_calling.schema_accuracy",
            failure_mode="loud",
            slices=(
                a_slice(bucket="tools:1-5", consensus_phrase="praised in simple loops"),
                a_slice(bucket="tools:6-15", consensus_phrase="schema failures at 6+"),
            ),
        )
        assert len(view.slices) == 2
        assert "simple loops" in view.headline and "6+" in view.headline


class TestEveryPhraseIsBoundToItsQuotes:
    """FR-26. A phrase with no quote ids is an unfalsifiable claim, which is the
    one thing this product exists not to produce."""

    def test_a_published_phrase_without_quote_ids_is_reported(self):
        page = ModelPage(
            model_version_id="mv1",
            display_name="x",
            capabilities=(
                CapabilityView(key="k", failure_mode="loud", slices=(a_slice(quote_ids=()),)),
            ),
        )
        assert len(page.unbound_phrases()) == 1

    def test_a_phrase_with_quote_ids_is_not_reported(self):
        page = ModelPage(
            model_version_id="mv1",
            display_name="x",
            capabilities=(CapabilityView(key="k", failure_mode="loud", slices=(a_slice(),)),),
        )
        assert page.unbound_phrases() == ()

    def test_a_slice_with_no_phrase_at_all_is_not_an_unbound_phrase(self):
        """Nothing was claimed, so there is nothing to back up."""
        assert a_slice(consensus_phrase=None, quote_ids=()).is_bound_to_evidence


class TestQuotesAreReadUntransformed:
    def test_only_verified_quotes_are_selected(self):
        conn = Conn(rows=[])
        ModelPageReader(conn).quotes_for(("q1",))
        assert "quote_verified" in conn.sql[0]

    def test_no_query_runs_for_an_empty_id_list(self):
        conn = Conn(rows=[])
        assert ModelPageReader(conn).quotes_for(()) == {}
        assert conn.sql == []


# ── the capability page ───────────────────────────────────────────────────


class TestTheTransposeHasItsOwnFailure:
    """On a model page an unreported capability is a visible empty row. Here an
    unreported MODEL is invisible unless the registry is enumerated - and the
    missing ones are the new and the obscure, which are the cheap ones."""

    def test_models_with_no_cells_are_listed_rather_than_omitted(self):
        conn = Conn(
            rows=[
                ("mv1", "Gemini 2.5 Flash", None, None, None, None),
                ("mv2", "Claude Haiku 4.5", None, None, None, None),
            ]
        )
        page = CapabilityPageReader(conn).build("summarization.fidelity")

        assert len(page.models) == 2
        assert len(page.unreported) == 2

    def test_the_query_left_joins_so_a_model_without_a_cell_survives_it(self):
        """An inner join here IS the defect - it would silently produce a page
        about the models people post about."""
        conn = Conn(rows=[])
        CapabilityPageReader(conn).build("summarization.fidelity")

        sql = conn.sql[0].upper()
        assert "LEFT JOIN" in sql
        assert "FROM MODEL_VERSION" in sql

    def test_the_summary_says_why_the_unreported_are_listed(self):
        conn = Conn(rows=[("mv1", "A", None, None, None, None)])
        summary = CapabilityPageReader(conn).build("summarization.fidelity").summary

        assert "ranks popularity, not capability" in summary

    def test_an_unknown_capability_is_refused_rather_than_rendered_empty(self):
        """An unknown key would produce a page reading "nobody has reported on
        this", indistinguishable from a real capability nobody discussed."""
        with pytest.raises(KeyError, match="not in contract/capabilities.yaml"):
            CapabilityPageReader(Conn()).build("not.a.capability")

    def test_a_silent_capability_warns_across_the_whole_page(self):
        conn = Conn(rows=[("mv1", "A", None, None, None, None)])
        page = CapabilityPageReader(conn).build("summarization.fidelity")

        assert page.silent
        assert "not evidence that it works" in page.summary


class TestConditionalStandingIsAFinding:
    def test_a_model_published_in_one_bucket_and_not_another_is_conditional(self):
        standing = ModelStanding(
            model_version_id="mv1",
            display_name="A",
            buckets=(("tools:1-5", "published"), ("tools:6-15", "insufficient")),
        )
        assert standing.conditional
        assert standing.publishes

    def test_a_single_bucket_is_not_conditional(self):
        standing = ModelStanding(
            model_version_id="mv1", display_name="A", buckets=(("any", "published"),)
        )
        assert not standing.conditional


class TestNoRankingIsInvented:
    def test_the_page_exposes_no_score_or_ordering_member(self):
        """Rule 3. Two models with published cells are not thereby ordered, and
        any ordering invented here would be a synthesised number with a page to
        live on."""
        public = {n for n in dir(CapabilityPage) if not n.startswith("_")}
        for invented in ("score", "rank", "ranked", "best", "top", "ordering"):
            assert invented not in public, f"CapabilityPage.{invented} invents an order"
