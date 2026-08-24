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

# ── the length guard, and why it is here rather than in the schema ────────


def test_stable_id_is_prefix_plus_sixteen_hex():
    """The guard for `_ID_LEN`, asserted where it can fail.

    A width guard on the schema would assert against nothing: **every id column
    in `contract/` is `text`** — checked for `varchar`, `char(` and
    `character varying`, zero matches — so no column length constrains this and
    a migration proposing one would be a change made for a constraint that does
    not exist.

    What CAN change is this function. `_ID_LEN` is 16, so `stable_id` returns
    `prefix` + `_` + 16 hex characters: 19 for `mv`, 31 for `thread_context`.
    Nothing outside this module reads `_ID_LEN`, so shortening it would move
    every id the lane mints and no test would notice.

    16 hex is 64 bits: **2.7e-08 collision probability at a million ids**, which
    is sufficient at any size this project reaches. The number is here so that a
    change to it has to argue with a figure.
    """
    import re

    for prefix, expected in (("mv", 19), ("ma", 19), ("thread_context", 31), ("job_run", 24)):
        minted = stable_id(prefix, "some", "parts")
        assert len(minted) == expected, f"{prefix}: {minted}"
        assert minted.startswith(f"{prefix}_")
        digest = minted[len(prefix) + 1 :]
        assert len(digest) == 16
        assert re.fullmatch(r"[0-9a-f]{16}", digest), digest


def test_no_id_column_in_the_contract_is_width_constrained():
    """The other half of the same statement, asserted rather than remembered.

    This is what makes the test above the right place for the guard. If a
    `varchar` ever lands on an id column, the constraint becomes real and this
    fails — which is the moment to have the width conversation, rather than
    before it.
    """
    from pathlib import Path

    contract = Path(__file__).resolve().parents[1] / "contract"
    offenders = []
    for path in list(contract.glob("*.sql")) + list((contract / "migrations").glob("*.sql")):
        text = path.read_text(encoding="utf-8").lower()
        for needle in ("varchar", "character varying", "char("):
            if needle in text:
                offenders.append(f"{path.name}: {needle}")

    assert not offenders, (
        "a width-constrained column type appeared in contract/. Every column was "
        f"`text`, which is what makes the id-length guard a test rather than a "
        f"schema change: {offenders}"
    )
