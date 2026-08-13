"""NFR-5: terms reviewed and recorded per source, enforced rather than hoped.

`contract/sources.yaml` ships `tos_notes` placeholders so the `source` rows
can exist, which unblocks the foreign key `watermark` needs. The placeholder
says in its own value that the review has not happened.

A placeholder a human has to notice is a lie you will forget. These are the
tests that make it a gate instead.
"""

from __future__ import annotations

import pytest
import yaml

from collect.config import CONTRACT_DIR
from collect.registry.assertions import TermsNotReviewedError, assert_terms_reviewed

SOURCES_YAML = CONTRACT_DIR / "sources.yaml"


def _contract():
    return yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))


# ── the file itself ───────────────────────────────────────────────────────


def test_the_contract_file_exists():
    """Sign-off item 13. Without it, watermark.source_id has nothing to point at."""
    assert SOURCES_YAML.exists()


def test_all_three_platforms_are_declared():
    ids = {s["id"] for s in _contract()["sources"]}
    assert ids == {"github", "blogs", "reddit"}


def test_base_trust_matches_the_documented_weights():
    """github 0.95 / blog 0.90 / reddit 0.85 — weights, so rule 5 puts them here."""
    trust = {s["id"]: s["base_trust"] for s in _contract()["sources"]}
    assert trust == {"github": 0.95, "blogs": 0.90, "reddit": 0.85}


def test_every_source_has_tos_notes():
    """`source.tos_notes` is NOT NULL precisely so this cannot be skipped."""
    assert all(s.get("tos_notes") for s in _contract()["sources"])


# ── the gate ──────────────────────────────────────────────────────────────


def test_the_remaining_placeholders_block_harvest():
    """The current state: github reviewed 2026-08-13, blogs and reddit not.

    This test tracks reality rather than asserting a fixed number, and it should
    keep failing every time a source is reviewed — that is the point. When the
    blog source ruling lands, `blogs` leaves this list; reddit leaves it when
    access is granted and its limits are observed rather than trusted.
    """
    contract = _contract()
    with pytest.raises(TermsNotReviewedError) as excinfo:
        assert_terms_reviewed(contract["sources"], marker=contract["review_marker"])

    message = str(excinfo.value)
    for source_id in ("blogs", "reddit"):
        assert source_id in message
    assert "github" not in message, "github was reviewed and recorded on 2026-08-13"


def test_the_github_review_records_what_the_placeholder_asked_for():
    """Four things, and the fourth is the one that does not reduce to a yes.

    A note that said "republication permitted" would be wrong: §D.5's licence
    grant is scoped "through the Service", so it grants GitHub's own product,
    not us. Recording the reason is what stops the next reader assuming it.
    """
    github = next(s for s in _contract()["sources"] if s["id"] == "github")
    notes = github["tos_notes"]

    assert "Reviewed 2026-08-13" in notes
    assert "github-terms-of-service" in notes and "acceptable-use-policies" in notes
    assert "30/minute" in notes and "5,000/hour" in notes
    assert "not granted by the terms" in notes
    assert "REVIEW REQUIRED" not in notes


def test_the_refusal_cites_the_requirement():
    with pytest.raises(TermsNotReviewedError, match="NFR-5"):
        assert_terms_reviewed(_contract()["sources"])


def test_a_reviewed_source_passes():
    reviewed = [{"id": "github", "tos_notes": "Reviewed 2026-08-14, terms at ..., 30 req/min"}]
    assert_terms_reviewed(reviewed)  # must not raise


def test_one_unreviewed_source_blocks_the_run():
    """Fails closed. Two good sources do not excuse the third."""
    mixed = [
        {"id": "github", "tos_notes": "Reviewed 2026-08-14"},
        {"id": "blogs", "tos_notes": "Reviewed 2026-08-14"},
        {"id": "reddit", "tos_notes": "REVIEW REQUIRED before first harvest"},
    ]
    with pytest.raises(TermsNotReviewedError, match="reddit") as excinfo:
        assert_terms_reviewed(mixed)
    assert "github" not in str(excinfo.value)


def test_it_accepts_objects_as_well_as_mappings():
    """The loader may hand it rows or dataclasses; neither should surprise it."""

    class Row:
        id = "blogs"
        tos_notes = "REVIEW REQUIRED"

    with pytest.raises(TermsNotReviewedError, match="blogs"):
        assert_terms_reviewed([Row()])


def test_no_sources_is_not_a_failure():
    assert_terms_reviewed([])


def test_the_marker_lives_in_the_contract_file():
    """The assertion default and the YAML must not drift apart."""
    assert _contract()["review_marker"] == "REVIEW REQUIRED"
