"""The two rulings ratified 2026-09-08, and the condition they rest on.

WHY THIS FILE EXISTS SEPARATELY FROM `tests/test_source_terms.py`. That file
tests the GATE - a known unexpired ruling, evidence that has not gone stale,
preconditions re-verified. This one tests the two RULINGS, on the same
arrangement as `tests/test_reddit_terms_gate.py`: arXiv and X are permissions
on an internal-development-only basis rather than clearances, and every clause
that makes them narrow is a clause somebody can widen with a one-line edit and
no test noticing.

⚠  WHAT NO TEST HERE CAN CHECK, STATED SO ITS ABSENCE IS NOT READ AS COVERAGE.
   Both rulings hold only while nothing is published externally - a quote shown
   with a link to somebody outside the team. NOTHING IN THE PIPELINE OBSERVES
   THAT, and so nothing here asserts it. `contract/sources.yaml`'s ENFORCEMENT
   block says why in full: the gate is on the fetch path and publication is on
   the serve path, `use_basis` observes `ENVIRONMENT` rather than who is
   looking, and the Articles data is static and already built. What IS tested
   below is that the condition is written down where a reader will find it, and
   that the `ENVIRONMENT` fuse fires - which is a smaller claim than the ruling
   makes, deliberately.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from collect.registry.assertions import TermsNotReviewedError, assert_terms_reviewed
from collect.registry.sources import load_sources

RULED_ON = date(2026, 9, 8)

#: The day the robots measurement was taken, which is the EVIDENCE date and is
#: deliberately not the ruling date - one is a measurement, the other a reading.
MEASURED_ON = date(2026, 9, 7)

PLATFORMS = {"arxiv": "arxiv-api-terms", "x": "x-via-rapidapi-scraper"}


def _contract():
    return load_sources()


def _row(source_id: str):
    return next(p for p in _contract().platforms if p["id"] == source_id)


def _observations(source_id: str) -> dict:
    """What a healthy internal-development run observes for one source."""
    if source_id == "arxiv":
        return {"access_path": "api", "use_basis": "internal-development-only"}
    return {
        "access_path": "rapidapi-reseller",
        "scraper_provider": "twitter241",
        "credential_present": True,
        "use_basis": "internal-development-only",
    }


# ── the rulings exist and are signed by a person ─────────────────────────


@pytest.mark.parametrize(("source_id", "ruling_id"), sorted(PLATFORMS.items()))
def test_the_ruling_is_declared_and_named_by_its_source(source_id, ruling_id):
    contract = _contract()
    assert ruling_id in contract.rulings
    assert _row(source_id)["terms_ruling"] == ruling_id


@pytest.mark.parametrize("ruling_id", sorted(PLATFORMS.values()))
def test_a_person_read_it_and_is_named(ruling_id):
    """`reviewed_by: UNRATIFIED-DRAFT` was the marker, and it is gone.

    "Somebody reviewed this" is not a fact anyone can follow up, which is why
    the field exists at all.
    """
    ruling = _contract().rulings[ruling_id]
    assert ruling.reviewed_by == "anooj"
    assert "UNRATIFIED" not in (ruling.summary or "")
    assert "NOT RATIFIED" not in (ruling.summary or "")


@pytest.mark.parametrize("ruling_id", sorted(PLATFORMS.values()))
def test_it_is_dated_and_expires(ruling_id):
    ruling = _contract().rulings[ruling_id]
    assert ruling.reviewed_on == RULED_ON
    assert ruling.expires_on() == RULED_ON + timedelta(days=90)


# ── the basis, and the fuse ──────────────────────────────────────────────


@pytest.mark.parametrize("ruling_id", sorted(PLATFORMS.values()))
def test_the_basis_is_also_a_live_precondition(ruling_id):
    """`TermsRuling.basis`'s own requirement: the fuse is CHECKED, not remembered.

    A basis named in prose and absent from `live_preconditions` stops applying
    when somebody remembers to revisit it, which is never. This is the same
    assertion `tests/test_reddit_terms_gate.py` makes about Reddit's, and it is
    made here because two more rulings now rest on the same basis.
    """
    ruling = _contract().rulings[ruling_id]
    assert ruling.basis == "internal-development-only"
    assert ruling.live_preconditions["use_basis"] == ["internal-development-only"]


@pytest.mark.parametrize(("source_id", "ruling_id"), sorted(PLATFORMS.items()))
def test_a_healthy_internal_run_passes(source_id, ruling_id):
    assert_terms_reviewed(
        [_row(source_id)],
        rulings=_contract().rulings,
        observations={source_id: _observations(source_id)},
        today=RULED_ON,
    )


@pytest.mark.parametrize("source_id", sorted(PLATFORMS))
def test_production_refuses_the_source(source_id):
    """The one condition that is actually enforced, and it fires."""
    observations = _observations(source_id) | {"use_basis": "not-internal (production)"}
    with pytest.raises(TermsNotReviewedError, match=source_id):
        assert_terms_reviewed(
            [_row(source_id)],
            rulings=_contract().rulings,
            observations={source_id: observations},
            today=RULED_ON,
        )


@pytest.mark.parametrize("source_id", sorted(PLATFORMS))
def test_an_unobserved_basis_refuses_rather_than_passing(source_id):
    """Rule 6 at the gate: an observation not made is not one that passed.

    The direction that matters. A precondition the run forgot to supply must
    refuse, or adding a precondition to a ruling would be decorative on every
    caller that had not been updated.
    """
    observations = {k: v for k, v in _observations(source_id).items() if k != "use_basis"}
    with pytest.raises(TermsNotReviewedError, match="use_basis"):
        assert_terms_reviewed(
            [_row(source_id)],
            rulings=_contract().rulings,
            observations={source_id: observations},
            today=RULED_ON,
        )


# ── what the rulings refuse to claim ─────────────────────────────────────


def test_the_publication_trigger_is_defined_in_the_file():
    """An untriggered trigger and an undefined one look identical from inside.

    `reddit-via-rapidapi` said "before any external publication" for three
    weeks without saying what publication meant. The definition is now in the
    file, once, and all three rulings point at it.
    """
    from collect.config import CONTRACT_DIR

    text = (CONTRACT_DIR / "sources.yaml").read_text(encoding="utf-8")
    assert "WHAT COUNTS AS PUBLICATION" in text
    # The three parts of the definition, each of which is doing work.
    assert "shown with a link" in text.lower() or "SHOWN WITH A LINK" in text
    assert "outside the team" in text
    # And the part that makes it a trigger rather than a launch.
    assert "one reader who is not one of us is enough" in text


def test_the_file_states_that_nothing_enforces_the_condition():
    """The clause this whole ratification turns on being honest.

    An internal-only ruling that nothing enforces is a NOTE, not a control, and
    a file that listed what it checks without listing what it does not would
    read as a guarantee. This asserts the disclaimer is present, because the
    disclaimer is the load-bearing part.
    """
    from collect.config import CONTRACT_DIR

    text = (CONTRACT_DIR / "sources.yaml").read_text(encoding="utf-8")
    assert "ENFORCEMENT" in text
    assert "NOTHING IN THE PIPELINE WOULD NOTICE" in text


@pytest.mark.parametrize("ruling_id", sorted(PLATFORMS.values()))
def test_no_terms_document_is_claimed_to_have_been_read(ruling_id):
    """Ratified is not read. Neither platform's terms have been opened.

    `terms_document_read: [false]` is recorded evidence rather than an omission,
    so a later reader cannot mistake the silence for a clearance - and cannot
    flip the source row's evidence to `true` without the diff saying so.
    """
    ruling = _contract().rulings[ruling_id]
    assert ruling.recorded_evidence["terms_document_read"] == [False]
    assert "NO TERMS DOCUMENT HAS BEEN READ" in ruling.summary


def test_the_arxiv_robots_reading_is_recorded_as_measured():
    """The measurement stays the evidence; the ruling did not resolve it.

    `export.arxiv.org` answers `Disallow: /` on the host serving the documented
    API. Recording that as `true` rather than dropping it is what keeps the
    ruling a CONDITION rather than a reading of robots in our own favour.
    """
    ruling = _contract().rulings["arxiv-api-terms"]
    assert ruling.recorded_evidence["robots_api_host_disallows"] == [True]
    assert _row("arxiv")["terms_evidence"]["robots_api_host_disallows"] is True
    assert _row("arxiv")["terms_evidence"]["checked_on"] == MEASURED_ON
    assert "UNANSWERED" in ruling.summary


def test_the_x_ruling_pins_the_provider_and_says_why():
    """A swap is a different party's terms AND a different response envelope.

    Without the pin, a provider change parses nothing and reports X as quiet,
    which is rule 4 one stage earlier: an absence we caused reading as one we
    found.
    """
    ruling = _contract().rulings["x-via-rapidapi-scraper"]
    assert ruling.live_preconditions["scraper_provider"] == ["twitter241"]
    assert ruling.live_preconditions["credential_present"] == [True]


def test_a_swapped_provider_refuses():
    observations = _observations("x") | {"scraper_provider": "someone-else"}
    with pytest.raises(TermsNotReviewedError, match="scraper_provider"):
        assert_terms_reviewed(
            [_row("x")],
            rulings=_contract().rulings,
            observations={"x": observations},
            today=RULED_ON,
        )


def test_the_x_ruling_records_reddits_conditions_rather_than_clearing_them():
    """It inherits the precedent AND the four unresolved conditions with it.

    An inherited precedent that quietly dropped the conditions would be the
    worst of both: the permission without the record of what it does not cover.
    """
    ruling = _contract().rulings["x-via-rapidapi-scraper"]
    assert ruling.recorded_evidence["credentials_issued_by_platform"] == [False]
    assert ruling.recorded_evidence["legal_review_completed"] == [False]
    assert "PERMISSION, NOT A CLEARANCE" in ruling.summary
    # The three Reddit clauses, by the mechanism each one breaks against.
    assert "handle_hash" in ruling.summary
    assert "NFR-4" in ruling.summary


@pytest.mark.parametrize("ruling_id", sorted(PLATFORMS.values()))
def test_the_condition_is_stated_on_the_ruling_and_not_only_in_the_banner(ruling_id):
    """A reader who greps for one ruling must find the condition on it.

    The banner defines the trigger once; each ruling still has to SAY it rests
    on that trigger, or the definition is a paragraph nobody's grep reaches.
    """
    summary = _contract().rulings[ruling_id].summary
    assert "NOTHING IS PUBLISHED EXTERNALLY" in summary
    assert "RE-REVIEW REQUIRED BEFORE" in summary


@pytest.mark.parametrize("source_id", sorted(PLATFORMS))
def test_the_source_row_repeats_the_condition_where_an_operator_will_read_it(source_id):
    """`tos_notes` is what lands in the `source` table and what a person reads.

    A condition recorded only in the ruling is read by whoever writes rulings.
    """
    notes = _row(source_id)["tos_notes"]
    assert "internal development and testing only" in notes
    assert "HOLDS ONLY WHILE NOTHING IS PUBLISHED EXTERNALLY" in notes
