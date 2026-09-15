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


def test_the_harvester_factory_passes_with_the_ruling_in_place(reddit_row, monkeypatch):
    """NEEDS A SIGNED UNDERTAKING NOW, and that is the change working.

    This passed unconditionally while the basis came from `ENVIRONMENT`, because
    a development checkout observes as internal. It now needs somebody to have
    asserted that the deployment is internal - which is the whole point, and it
    means the factory refuses by DEFAULT rather than by configuration.
    """
    _undertaking(monkeypatch)
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


def _real_contract():
    """The parsed contract, read ONCE and before any patching.

    Captured at first use rather than inside `_undertaking`: a test that calls
    the helper twice finds `load_sources` already replaced by the first call's
    lambda, which has no `cache_clear`.
    """
    global _REAL
    if _REAL is None:
        from collect.registry.sources import load_sources as _load
        _load.cache_clear()
        _REAL = _load()
    return _REAL


_REAL = None


def _undertaking(monkeypatch, **overrides):
    """Point `observe_use_basis` at an undertaking built for this test.

    PATCHED ON `collect.registry.sources.load_sources`, WHICH IS WHERE THE READ
    MOVED on 2026-09-15. It used to read `collect.adapters.basis.settings` and
    infer the basis from `ENVIRONMENT` - a DEPLOYMENT MODE standing in for a
    fact about who can reach the site. The undertaking is the fact itself,
    asserted by a person.
    """
    import dataclasses

    import collect.registry.sources as sources_module

    block = {
        "asserts": INTERNAL_DEVELOPMENT_ONLY,
        "asserted_by": "tester",
        "asserted_on": date.today(),
        "review_valid_days": 30,
        "conditions": {"auth_walled": True, "external_users": False,
                       "publicly_linked": False, "monetized": False},
    }
    block.update(overrides)
    if overrides.get("conditions"):
        block["conditions"] = {**{"auth_walled": True, "external_users": False,
                                  "publicly_linked": False, "monetized": False},
                               **overrides["conditions"]}
    # REPLACE ONLY THE UNDERTAKING. `assert_terms_reviewed` reads `.rulings`
    # off the same object, so a bare namespace makes the gate raise
    # AttributeError instead of exercising the basis.
    real = _real_contract()
    monkeypatch.setattr(
        sources_module, "load_sources",
        lambda: dataclasses.replace(real, use_basis_undertaking=block),
    )
    return block


def test_a_signed_undertaking_reports_the_basis(monkeypatch):
    _undertaking(monkeypatch)
    assert observe_reddit_use()["use_basis"] == INTERNAL_DEVELOPMENT_ONLY


def test_an_unsigned_undertaking_is_not_a_basis(monkeypatch):
    """The state the proposal SHIPS in, and it must not read as asserted.

    A block somebody wrote and nobody signed is a proposal. Treating it as an
    assertion would make writing the file the same act as standing behind it.
    """
    _undertaking(monkeypatch, asserted_by=None)
    basis = observe_reddit_use()["use_basis"]
    assert basis != INTERNAL_DEVELOPMENT_ONLY
    assert "unsigned" in basis


def test_an_absent_undertaking_refuses_rather_than_permits(monkeypatch):
    """Rule 6, and the DEFAULT FLIPS relative to what `ENVIRONMENT` did.

    `ENVIRONMENT` unset observed as internal, so a misconfigured container
    harvested under a basis nobody had asserted. Absent now refuses.
    """
    import dataclasses

    import collect.registry.sources as sources_module

    real = _real_contract()
    monkeypatch.setattr(
        sources_module, "load_sources",
        lambda: dataclasses.replace(real, use_basis_undertaking=None),
    )
    basis = observe_reddit_use()["use_basis"]
    assert basis != INTERNAL_DEVELOPMENT_ONLY
    assert "no-undertaking" in basis


def test_an_expired_undertaking_is_not_a_basis(monkeypatch):
    """An undertaking with no expiry is a thing nobody revisits."""
    _undertaking(monkeypatch, asserted_on=date.today() - timedelta(days=400))
    basis = observe_reddit_use()["use_basis"]
    assert basis != INTERNAL_DEVELOPMENT_ONLY
    assert "expired" in basis
    # NAMED, not merely different. The gate quotes the observed value, so the
    # refusal has to say WHICH check failed.
    assert str(date.today() - timedelta(days=400)) in basis


def test_conditions_beat_the_asserts_line(monkeypatch):
    """A self-contradicting undertaking is broken, not weaker.

    Letting `asserts:` win over `conditions:` would make the conditions
    decorative - and they are the only part a person can actually check.
    """
    _undertaking(monkeypatch, conditions={"external_users": True})
    basis = observe_reddit_use()["use_basis"]
    assert basis != INTERNAL_DEVELOPMENT_ONLY
    assert "void" in basis
    assert "external_users" in basis


def test_all_platforms_on_this_basis_observe_it_identically(monkeypatch):
    """The property `collect/adapters/basis.py` exists for.

    EIGHT rulings name this basis now, not three. Until 2026-09-15 only three
    listed `use_basis` as a live precondition, so one container refused Reddit
    and harvested 60 dev.to items under the identical sentence.
    """
    from collect.adapters.arxiv import observe_arxiv_use
    from collect.adapters.x import observe_x_use

    for kwargs, expect_internal in (({}, True), ({"asserted_by": None}, False)):
        _undertaking(monkeypatch, **kwargs)
        observed = {
            "reddit": observe_reddit_use()["use_basis"],
            "arxiv": observe_arxiv_use()["use_basis"],
            "x": observe_x_use()["use_basis"],
        }
        assert len(set(observed.values())) == 1, observed
        internal = next(iter(observed.values())) == INTERNAL_DEVELOPMENT_ONLY
        assert internal is expect_internal, observed


def test_every_ruling_that_names_a_basis_enforces_it():
    """The should that became a must, measured before it did.

    2026-09-14: eight rulings named `internal-development-only` and three
    listed it as a live precondition. `_ruling_from` now raises at LOAD time
    rather than leaving it to a reviewer, because the next ruling somebody adds
    is the one that reopens the gap.
    """
    from collect.registry.sources import load_sources

    load_sources.cache_clear()
    unenforced = [
        r.id for r in load_sources().rulings.values()
        if r.basis and r.basis not in (r.live_preconditions.get("use_basis") or ())
    ]
    assert not unenforced, (
        f"rulings naming a basis without enforcing it: {unenforced}. The loader "
        "should have refused these."
    )


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
        # Added 2026-09-09, for the same reason and after the failure that
        # reason predicts. Reddit and X both read `rapidapi_host`, .env declared
        # it twice, and the last declaration won - so Reddit's paths went to X's
        # host and RapidAPI answered 404 to every search. One variable cannot
        # address two vendors, so Reddit derives its host from this instead.
        reddit_provider=None,
        # Added 2026-09-10, and it is the HOST defect one variable over. The
        # comment above on `scraper_provider` says the X credential "is
        # `rapidapi_key` above - already listed". That was an assumption, and
        # measuring it settled it the other way: this project's two RapidAPI
        # keys are different subscriptions, each 403 on the other's provider.
        # X gets its own variable for the same reason it got its own host.
        x_rapidapi_key=None,
        pipeline_version="test",
    )
