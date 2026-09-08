"""The Reddit path and the NFR-5 terms gate it never used to call.

Until 2026-08-18 `assert_terms_reviewed` was called from `blog/fetch.py` and
`scripts/harvest_github.py` and from nowhere on the Reddit path. The gate was
working correctly and refusing Reddit the whole time; nothing consulted it.

The load-bearing tests here are the ones that fail when the ruling stops
applying — an expired review, a deployment that is no longer internal, a
`recorded_evidence` value that no longer matches. A gate that only passes is
indistinguishable from no gate.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
import yaml

from collect.adapters.reddit import (
    INTERNAL_DEVELOPMENT_ONLY,
    RedditHarvester,
    harvester_for_source,
    observe_reddit_use,
)
from collect.config import CONTRACT_DIR
from collect.registry.assertions import TermsNotReviewedError
from collect.registry.sources import load_sources

RULING_ID = "reddit-via-rapidapi"


@pytest.fixture(scope="module")
def document() -> dict:
    return yaml.safe_load((CONTRACT_DIR / "sources.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def reddit_row(document) -> dict:
    return next(r for r in document["sources"] if r["id"] == "reddit")


def _observations(basis: str = INTERNAL_DEVELOPMENT_ONLY) -> dict:
    return {"reddit": {"use_basis": basis}}


# ── the ruling exists and says what it is supposed to say ────────────────


def test_the_reddit_row_names_the_ruling():
    """Before 2026-08-18 it named none, which is what blocked every fetch."""
    document = yaml.safe_load(
        (CONTRACT_DIR / "sources.yaml").read_text(encoding="utf-8")
    )
    row = next(r for r in document["sources"] if r["id"] == "reddit")
    assert row["terms_ruling"] == RULING_ID


def test_the_ruling_records_who_read_the_terms():
    """A ruling is a person's reading. "Somebody reviewed this" is not
    a fact anyone can follow up."""
    ruling = load_sources().rulings[RULING_ID]
    assert ruling.reviewed_by
    assert ruling.reviewed_on == date(2026, 8, 18)


def test_the_ruling_names_the_basis_it_rests_on():
    """`internal-development-only` is a shorter fuse than review_valid_days,
    and it is only a fuse if something reads it."""
    ruling = load_sources().rulings[RULING_ID]
    assert ruling.basis == INTERNAL_DEVELOPMENT_ONLY
    assert ruling.live_preconditions["use_basis"] == [INTERNAL_DEVELOPMENT_ONLY]


def test_the_four_unresolved_conditions_are_named_in_the_summary():
    """They are the reason this is a permission and not a clearance.

    Asserted by content rather than by presence: a summary that stops naming
    them has quietly become a clearance, and nothing else would catch that.
    """
    summary = load_sources().rulings[RULING_ID].summary
    for clause in ("4.1", "2.8", "5.2", "3.2"):
        assert clause in summary, clause
    assert "UNRESOLVED" in summary


def test_the_two_publish_time_conflicts_are_recorded_where_they_bite():
    """A condition recorded only in a ruling is read by whoever writes rulings.

    These have to be read by whoever writes the publisher, so they are also in
    the two files that publisher will touch. If someone moves them, this fails.
    """
    from collect import rawstore
    from collect.assemble import authors

    assert "5.2" in (authors.__doc__ or "")
    assert "3.2" in (rawstore.RawStore.evict.__doc__ or "")


# ── the gate passes on the ruling, and only on it ────────────────────────


#: Supplied by every test here rather than read from the environment. These
#: test the terms gate and where it fires; none of them is about whether
#: RapidAPI is configured, and until 2026-08-18 all of them could fail for that
#: reason — which is what CI caught and a laptop with a `.env` could not.
TEST_HOST = "reddit-test.invalid"


def test_the_harvester_factory_passes_with_the_ruling_in_place(reddit_row):
    harvester = harvester_for_source(
        reddit_row, client=None, store=None, host=TEST_HOST
    )
    assert isinstance(harvester, RedditHarvester)


def test_a_non_internal_deployment_is_refused(reddit_row):
    """The basis is enforced, not remembered.

    This is the case the live precondition exists for: a production deployment
    silently inheriting a development-only ruling.
    """
    from collect.registry.assertions import assert_terms_reviewed

    with pytest.raises(TermsNotReviewedError, match="use_basis"):
        assert_terms_reviewed(
            [reddit_row], observations=_observations("not-internal (ENVIRONMENT=production)")
        )


def test_a_run_that_supplies_no_observation_is_refused(reddit_row):
    """An observation the caller did not supply refuses the source. A live
    precondition nobody checked is not a precondition that passed."""
    from collect.registry.assertions import assert_terms_reviewed

    with pytest.raises(TermsNotReviewedError):
        assert_terms_reviewed([reddit_row], observations={})


def test_an_expired_review_is_refused(reddit_row):
    """90 days from 2026-08-18. The ruling is a reading with a shelf life."""
    from collect.registry.assertions import assert_terms_reviewed

    ruling = load_sources().rulings[RULING_ID]
    with pytest.raises(TermsNotReviewedError):
        assert_terms_reviewed(
            [reddit_row],
            observations=_observations(),
            today=ruling.expires_on() + timedelta(days=1),
        )


def test_the_gate_is_not_in_the_constructor(reddit_row):
    """Deliberate, and the same arrangement blog uses.

    A constructor check forces every test to fabricate a reviewed source row,
    and a fixture that fakes a ruling is worse than no gate because it reads as
    one. Tests construct directly and get no gate; anything reaching the network
    comes through the factory.
    """
    assert RedditHarvester(client=None, store=None, host=TEST_HOST) is not None


# ── the observation, and the limits it admits to ─────────────────────────


def test_the_observation_reports_the_basis_outside_production(monkeypatch):
    """PATCHED ON `collect.adapters.basis`, WHICH IS WHERE THE READ MOVED.

    `observe_reddit_use` delegated to `collect/adapters/basis.py` on 2026-09-08,
    when `arxiv-api-terms` and `x-via-rapidapi-scraper` were ratified on the
    same basis and three adapters needed the same observation. Patching
    `collect.adapters.reddit.settings` no longer reaches the read - and the
    failure was one-sided, which is the part worth recording: the staging case
    still PASSED, because an unpatched read in a development checkout returns
    the same answer. Only the production case failed. A test that patches the
    wrong module and still passes is the shape this repository keeps finding.
    """
    monkeypatch.setattr("collect.adapters.basis.settings", lambda: _settings("staging"))
    assert observe_reddit_use()["use_basis"] == INTERNAL_DEVELOPMENT_ONLY


def test_the_observation_reports_production_as_not_internal(monkeypatch):
    monkeypatch.setattr(
        "collect.adapters.basis.settings", lambda: _settings("production")
    )
    basis = observe_reddit_use()["use_basis"]
    assert basis != INTERNAL_DEVELOPMENT_ONLY
    # NAMED, not merely different. The gate's refusal quotes the observed value,
    # so it has to say which deployment it refused.
    assert "production" in basis


def test_all_three_platforms_on_this_basis_observe_it_identically(monkeypatch):
    """The property `collect/adapters/basis.py` exists for.

    Three rulings rest on `internal-development-only` - Reddit's, arXiv's and
    X's - and three copies of one check drift. A basis read as internal by two
    adapters and not by the third would refuse one platform and pass two on the
    SAME deployment, which reads as a platform problem rather than as a config
    one. So this asserts they agree, in both directions, rather than asserting
    each separately.
    """
    from collect.adapters.arxiv import observe_arxiv_use
    from collect.adapters.x import observe_x_use

    for environment, expected_internal in (("staging", True), ("production", False)):
        monkeypatch.setattr(
            "collect.adapters.basis.settings", lambda e=environment: _settings(e)
        )
        observed = {
            "reddit": observe_reddit_use()["use_basis"],
            "arxiv": observe_arxiv_use()["use_basis"],
            "x": observe_x_use()["use_basis"],
        }
        assert len(set(observed.values())) == 1, observed
        internal = next(iter(observed.values())) == INTERNAL_DEVELOPMENT_ONLY
        assert internal is expected_internal, observed


def _settings(environment: str):
    from collect.config import Settings

    return Settings(
        environment=environment,
        database_url=None,
        raw_store_path=CONTRACT_DIR,
        user_agent="test/0 (+https://example.invalid)",
        github_token=None,
        reddit_client_id=None,
        reddit_client_secret=None,
        rapidapi_key=None,
        rapidapi_host=None,
        # Added 2026-09-07 with the X adapter. LISTED RATHER THAN DEFAULTED:
        # `Settings` has no defaults, deliberately, so a new setting shows up in
        # every construction of it and nobody inherits an empty string that
        # reads as "configured with nothing" (rule 6, on our own config).
        #
        # The X route is a RapidAPI provider, so the CREDENTIAL is
        # `rapidapi_key` above - already listed - and this only names which
        # provider fronts it.
        scraper_provider=None,
        pipeline_version="test",
    )
