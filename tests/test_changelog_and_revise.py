"""The changelog, and FR-30's re-run.

Both exist so a reader can tell OUR changes from the world's.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from judge.app import app
from judge.pages.changelog import DRIVERS, Changelog, ChangelogReader, LabelChange

client = TestClient(app, raise_server_exceptions=False)


def change(driver="new-evidence", direction="lost", quotes=("q1",), cid="c1"):
    return LabelChange(
        change_id=cid,
        label_id="l1",
        direction=direction,
        driver=driver,
        quote_ids=tuple(quotes),
    )


class TestOurChangesAreDistinguishableFromTheWorlds:
    """A label lost to `config-change` is not a fact about the model at all.

    A reader who cannot tell it from `new-evidence` attributes our threshold
    edit to their model's behaviour - opposite conclusions from the same word.
    """

    def test_a_config_change_says_the_model_did_not_change(self):
        headline = change(driver="config-change").headline

        assert "our configuration" in headline
        assert "not in the model" in headline

    def test_a_new_evidence_change_does_not_borrow_that_wording(self):
        assert "our configuration" not in change(driver="new-evidence").headline

    def test_the_summary_counts_the_changes_that_are_ours(self):
        log = Changelog(
            changes=(change(driver="config-change"), change(driver="new-evidence", cid="c2")),
            total_labels=40,
        )
        assert "1 of 2 came from a change we made" in log.summary

    def test_changes_group_by_driver_rather_than_by_time(self):
        """A chronological list is exactly how a config-change sits between two
        new-evidence rows and reads as one of them."""
        log = Changelog(
            changes=(
                change(driver="new-evidence", cid="c1"),
                change(driver="config-change", cid="c2"),
                change(driver="new-evidence", cid="c3"),
            )
        )
        grouped = log.by_driver()

        assert set(grouped) == {"new-evidence", "config-change"}
        assert len(grouped["new-evidence"]) == 2


class TestALossIsNotAutomaticallyACriticism:
    """A label lost because evidence decayed is not one lost because engineers
    started reporting failures, and both render as "lost"."""

    def test_an_unevidenced_loss_says_the_evidence_aged(self):
        headline = change(driver="new-evidence", direction="lost", quotes=()).headline

        assert "No new criticism" in headline
        assert "aged below the publication bar" in headline

    def test_an_evidenced_loss_does_not_claim_that(self):
        assert "No new criticism" not in change(direction="lost", quotes=("q1",)).headline

    def test_a_gain_never_carries_the_decay_wording(self):
        assert "aged below" not in change(direction="gained", quotes=()).headline


class TestAnUnknownDriverIsSurfaced:
    """A change nobody can explain is worse on this page than anywhere else,
    because this page IS the explanation."""

    def test_it_is_flagged_rather_than_dropped(self):
        log = Changelog(changes=(change(driver="mystery"),), total_labels=1)

        assert len(log.unrecognised) == 1
        assert "does not recognise" in log.summary
        assert "mystery" in log.summary

    def test_its_headline_names_the_driver_verbatim(self):
        assert "mystery" in change(driver="mystery").headline

    def test_the_four_known_drivers_all_explain_themselves(self):
        assert set(DRIVERS) == {
            "new-evidence",
            "price-change",
            "version-change",
            "config-change",
        }
        assert len(set(DRIVERS.values())) == 4, "two drivers share an explanation"


class TestNoChangesIsNotAutomaticallyStability:
    def test_an_uncounted_label_total_refuses_to_call_it_stable(self):
        log = Changelog(changes=(), total_labels=None)
        assert "not yet a statement about stability" in log.summary

    def test_a_counted_total_makes_it_a_finding(self):
        log = Changelog(changes=(), total_labels=40)
        assert "across 40 tracked" in log.summary


class TestTheReaderOnlyReads:
    def test_no_write_reaches_the_connection(self):
        class Conn:
            def __init__(self):
                self.sql = []

            def execute(self, sql, params=()):
                self.sql.append(sql)

                class R:
                    @staticmethod
                    def fetchall():
                        return []

                    @staticmethod
                    def fetchone():
                        return (0,)

                return R()

        conn = Conn()
        ChangelogReader(conn).recent()
        for sql in conn.sql:
            assert sql.strip().upper().startswith("SELECT"), sql


# ── FR-30 ─────────────────────────────────────────────────────────────────


class TestEditingAnAssumptionRerunsTheRecommendation:
    """The editable field is what makes Q1 safe, and a field you can edit
    without anything changing is decoration."""

    def test_a_revised_profile_produces_a_requirement(self):
        response = client.post(
            "/ask/revise",
            json={"profile": {"raw_text": "summarise support tickets into themes"}},
        )
        assert response.status_code == 200
        assert response.json()["requirement"]

    def test_changing_an_assumption_changes_the_result(self):
        """Otherwise the endpoint is theatre."""
        without = client.post(
            "/ask/revise", json={"profile": {"raw_text": "summarise tickets"}}
        ).json()
        with_tools = client.post(
            "/ask/revise",
            json={"profile": {"raw_text": "summarise tickets", "tool_count": 12}},
        ).json()

        assert without["requirement"] != with_tools["requirement"]

    def test_no_model_runs_on_the_revision(self):
        """Re-reading the user's correction through a language model would let
        it overrule them - the exact failure the editable field prevents - and
        would make the same input differ between days."""
        import inspect

        import judge.app as app_module

        source = inspect.getsource(app_module.revise)
        for llm in ("understand(", "OpenRouterClient", "client.complete"):
            assert llm not in source, f"revise() reaches a model via {llm}"

    def test_an_empty_task_is_refused_rather_than_re_run(self):
        response = client.post("/ask/revise", json={"profile": {"raw_text": "  "}})
        assert response.status_code == 422
        assert "nobody's work" in response.json()["detail"]


class TestAnUnreviewedGuessIsNotAnApprovedOne:
    """Rule 6 on a review rather than on a value. A field nobody looked at is
    not a field somebody approved."""

    def test_fields_the_user_never_accepted_come_back_as_still_guessed(self):
        body = client.post(
            "/ask/revise",
            json={
                "profile": {"raw_text": "summarise tickets", "tool_count": 12},
                "accepted_assumptions": [],
            },
        ).json()
        assert "tool_count" in body["still_guessed"]

    def test_an_accepted_field_drops_out_of_still_guessed(self):
        body = client.post(
            "/ask/revise",
            json={
                "profile": {"raw_text": "summarise tickets", "tool_count": 12},
                "accepted_assumptions": ["tool_count"],
            },
        ).json()
        assert "tool_count" not in body["still_guessed"]

    def test_the_task_text_is_never_reported_as_a_guess(self):
        """The user wrote it. It is the one field that was never guessed."""
        body = client.post(
            "/ask/revise", json={"profile": {"raw_text": "summarise tickets"}}
        ).json()
        assert "raw_text" not in body["still_guessed"]
