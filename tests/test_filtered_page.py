"""/filtered, and the three things it must not do.

No database. The interesting behaviour is what the page refuses to render and
what it refuses to hide.
"""

from __future__ import annotations

from datetime import UTC, datetime

from judge.pages.filtered import (
    DISPLAYABLE,
    NEVER_DISPLAYED,
    FilteredDocument,
    FilteredPage,
    FilteredReport,
)
from judge.vet.reject import RejectionTrigger

NOW = datetime(2026, 8, 18, tzinfo=UTC)


def doc(doc_id="d1", status="rejected", reasons=(), url="https://example.test/a"):
    return FilteredDocument(
        document_id=doc_id,
        url=url,
        source="blog",
        status=status,
        reasons=tuple(reasons),
        filtered_at=NOW,
    )


class Conn:
    def __init__(self, rows, total=1297):
        self._rows, self._total, self.sql, self.params = rows, total, [], []

    def execute(self, sql, params=()):
        self.sql.append(sql)
        self.params.append(params)
        rows, total = self._rows, self._total

        class R:
            @staticmethod
            def fetchall():
                return rows

            @staticmethod
            def fetchone():
                return (total,)

        return R()


class TestTombstonedIsNeverRendered:
    """NFR-6. A tombstone is a deletion honoured.

    Rendering one would republish what somebody asked us to delete, on the page
    whose whole argument is that we are being transparent. The exclusion lives
    in the query, and this is what stops a later "show everything we filtered"
    refactor from quietly undoing it.
    """

    def test_the_query_asks_only_for_displayable_statuses(self):
        conn = Conn(rows=[])
        FilteredPage(conn).report()

        statuses = conn.params[0][0]
        assert NEVER_DISPLAYED not in statuses
        assert set(statuses) == set(DISPLAYABLE)

    def test_tombstoned_is_not_in_the_displayable_set_at_all(self):
        """Asserted against the constant rather than the string, so a rename
        cannot satisfy this test while changing the query."""
        assert NEVER_DISPLAYED not in DISPLAYABLE
        assert NEVER_DISPLAYED == "tombstoned"

    def test_kept_documents_are_not_shown_either(self):
        """They are not filtered. A page listing them would misreport the rate."""
        assert "kept" not in DISPLAYABLE


class TestAnUnexplainedRejectionIsShown:
    """The row it is most tempting to omit, on the page that exists to show it."""

    def test_a_document_with_no_reasons_still_appears(self):
        report = FilteredReport(documents=(doc(reasons=()),), total_documents=100)
        assert len(report.documents) == 1
        assert report.unexplained

    def test_it_is_labelled_as_our_defect_not_the_document_s_fault(self):
        headline = doc(reasons=()).headline
        assert "no reason recorded" in headline
        assert "defect in our pipeline" in headline
        assert "not a judgement about the document" in headline

    def test_the_summary_names_how_many_are_unexplained(self):
        report = FilteredReport(
            documents=(doc("d1", reasons=()), doc("d2", reasons=("affiliate_link",))),
            total_documents=100,
        )
        assert "1 carries no reason at all" in report.summary
        assert "defect in the filter" in report.summary


class TestAnUnknownRuleIsSurfaced:
    """A filter firing under a name nobody has written down is the most
    important thing on this page: it is a rule running unreviewed."""

    def test_it_is_not_dropped_from_the_document(self):
        triggers = doc(reasons=("some_new_rule",)).triggers
        assert len(triggers) == 1
        assert triggers[0][0] == "some_new_rule"
        assert "nobody has written down what it means" in triggers[0][1]

    def test_a_document_is_not_made_to_look_explained_by_its_other_reasons(self):
        """Dropping the unknown one would leave a document that looks fully
        accounted for by the rule that happens to be recognised."""
        triggers = doc(reasons=("affiliate_link", "some_new_rule")).triggers
        assert [t[0] for t in triggers] == ["affiliate_link", "some_new_rule"]

    def test_the_summary_names_the_unknown_rules(self):
        report = FilteredReport(documents=(doc(reasons=("some_new_rule",)),), total_documents=100)
        assert "this page does not recognise" in report.summary
        assert "some_new_rule" in report.summary

    def test_a_known_trigger_gets_its_real_explanation(self):
        triggers = doc(reasons=(RejectionTrigger.AFFILIATE_LINK.value,)).triggers
        assert "paid on conversion" in triggers[0][1]


class TestTheRateCarriesItsPopulation:
    """Rule 7. "12 rejected" invites the reader to supply a denominator, and
    every one they might guess is wrong."""

    def test_the_summary_states_the_population(self):
        report = FilteredReport(
            documents=tuple(doc(f"d{i}", reasons=("affiliate_link",)) for i in range(12)),
            total_documents=1297,
            total_filtered=12,
        )
        assert "12 of 1297 documents" in report.summary
        assert "0.9%" in report.summary

    def test_an_uncounted_population_produces_no_rate(self):
        """Better to say we did not count than to quote a share of an assumed
        total (rules 6 and 7 together)."""
        report = FilteredReport(documents=(doc(),), total_documents=None, total_filtered=1)
        summary = report.summary
        assert "not a rate" in summary
        assert "%" not in summary


class TestItNeverWrites:
    def test_only_selects_reach_the_connection(self):
        conn = Conn(rows=[])
        FilteredPage(conn).report()
        assert conn.sql
        for sql in conn.sql:
            assert sql.strip().upper().startswith("SELECT"), sql

    def test_rows_become_documents_with_their_reasons(self):
        conn = Conn(rows=[("d1", "https://x.test/a", "blog", "rejected", ["affiliate_link"], NOW)])
        report = FilteredPage(conn).report()

        assert report.documents[0].document_id == "d1"
        assert report.documents[0].reasons == ("affiliate_link",)
        assert report.documents[0].explained is True

    def test_a_null_reasons_array_becomes_empty_not_a_crash(self):
        """Postgres returns NULL for an unset text[], and an unexplained
        rejection is precisely the row most likely to have one."""
        conn = Conn(rows=[("d1", "https://x.test/a", "blog", "rejected", None, NOW)])
        report = FilteredPage(conn).report()

        assert report.documents[0].reasons == ()
        assert report.documents[0].explained is False


class TestTheCapIsDisclosed:
    """`report(limit=...)` truncates, and a page showing 200 of 900 while
    saying "200 filtered" under-reports its own filter fourfold.

    The coverage page had this defect and it was fixed there first. Finding it
    twice in two modules is the argument for asserting it in both.
    """

    def test_a_truncated_list_reports_the_full_count_not_the_page_size(self):
        report = FilteredReport(
            documents=tuple(doc(f"d{i}", reasons=("affiliate_link",)) for i in range(200)),
            total_documents=1297,
            total_filtered=900,
        )
        assert report.truncated is True
        assert "900 of 1297 documents" in report.summary
        assert "Showing the 200 most recent" in report.summary

    def test_an_untruncated_list_does_not_claim_to_be_showing_a_subset(self):
        report = FilteredReport(
            documents=(doc(reasons=("affiliate_link",)),),
            total_documents=100,
            total_filtered=1,
        )
        assert report.truncated is False
        assert "Showing the" not in report.summary


class TestPageFiguresAreNotReportedAsPopulationFigures:
    """`unexplained` counts the SHOWN rows. Under "900 filtered", an
    unqualified "1 carry no reason" states a fact about 200 rows in a sentence
    about 900 - rule 7 with the denominator silently swapped."""

    def test_a_truncated_page_names_the_scope_of_its_sub_counts(self):
        shown = [doc(f"d{i}", reasons=("affiliate_link",)) for i in range(199)]
        shown.append(doc("d199", reasons=()))
        report = FilteredReport(documents=tuple(shown), total_documents=1297, total_filtered=900)
        summary = report.summary

        assert "900 of 1297 documents" in summary
        assert "Of the 200 shown, 1 carries no reason" in summary

    def test_an_untruncated_page_does_not_add_a_scope_it_does_not_need(self):
        report = FilteredReport(documents=(doc(reasons=()),), total_documents=100, total_filtered=1)
        assert "shown" not in report.summary
        assert "1 carries no reason at all" in report.summary
