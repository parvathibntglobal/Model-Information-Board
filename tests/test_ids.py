"""Ids are pure functions of what they name (NFR-4)."""

from __future__ import annotations

import pytest

from collect.ids import content_hash, model_alias_id, model_version_id, stable_id


def test_stable_id_is_deterministic():
    assert stable_id("mv", "a/b") == stable_id("mv", "a/b")


def test_stable_id_parts_cannot_be_confused():
    """('a','bc') and ('ab','c') must not collide."""
    assert stable_id("x", "a", "bc") != stable_id("x", "ab", "c")


def test_stable_id_requires_a_part():
    with pytest.raises(ValueError):
        stable_id("mv")


def test_model_version_id_tracks_canonical_id():
    assert model_version_id("anthropic/claude-opus-5") != model_version_id("anthropic/opus-5")


def test_alias_id_covers_validity_window():
    """FR-4: a re-pointed alias is a new row, never an edit to the old one."""
    mv = model_version_id("anthropic/claude-opus-5")
    march = model_alias_id("opus", mv, "2026-03-01")
    june = model_alias_id("opus", mv, "2026-06-01")
    assert march != june


def test_content_hash_accepts_str_and_bytes():
    assert content_hash("hello") == content_hash(b"hello")
    assert len(content_hash("hello")) == 64
