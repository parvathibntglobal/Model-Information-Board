"""Make the repo importable without an install step.

pytest inserts this file's directory at the front of sys.path, so `collect`
and `judge` import from the working tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ── the use-basis undertaking ─────────────────────────────────────────────
#
# `collect/adapters/basis.py` reads `contract/sources.yaml:use_basis_undertaking`
# instead of `ENVIRONMENT` (proposed 2026-09-15), and the block ships UNSIGNED so
# a proposal cannot be mistaken for an assertion. Every ruling resting on a basis
# therefore refuses by default - which is the correct default and makes any test
# that exercises a real harvest path refuse too.
#
# OPT-IN, NEVER AUTOUSE. An autouse fixture would sign it for the tests that
# exist to WATCH it refuse, and those are the ones that matter most.

import pytest  # noqa: E402


@pytest.fixture
def signed_undertaking(monkeypatch):
    """A signed, unexpired, self-consistent undertaking for this test."""
    import dataclasses
    from datetime import date

    import collect.registry.sources as sources_module

    sources_module.load_sources.cache_clear()
    real = sources_module.load_sources()
    block = {
        "asserts": "internal-development-only",
        "asserted_by": "tester",
        "asserted_on": date.today(),
        "review_valid_days": 30,
        "conditions": {"auth_walled": True, "external_users": False,
                       "publicly_linked": False, "monetized": False},
    }
    monkeypatch.setattr(
        sources_module, "load_sources",
        lambda: dataclasses.replace(real, use_basis_undertaking=block),
    )
    return block
