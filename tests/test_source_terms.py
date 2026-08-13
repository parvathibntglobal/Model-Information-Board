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


def test_the_shipped_placeholders_block_harvest():
    """The current state: three sources, none reviewed, harvest refused."""
    contract = _contract()
    with pytest.raises(TermsNotReviewedError) as excinfo:
        assert_terms_reviewed(contract["sources"], marker=contract["review_marker"])

    message = str(excinfo.value)
    for source_id in ("github", "blogs", "reddit"):
        assert source_id in message


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
