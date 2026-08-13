"""Registry policy comes from versioned config, and that is enforced (NFR-10).

Built-in defaults exist so the lane could be developed before
`contract/registry.yaml` was approved. They are a hazard with a hard expiry,
not a fallback anyone should rely on: a default that silently applies is a
second source of truth, and editing one instead of the YAML ships a
threshold change as a code deploy with no version diff.
"""

from __future__ import annotations

import logging
import textwrap

import pytest
import yaml

from collect.config import CONTRACT_DIR
from collect.registry.assertions import UnversionedConfigError, assert_contract_backed
from collect.registry.policy import (
    CONTRACT,
    DEFAULT_POLICY,
    DEFAULTS,
    REGISTRY_YAML,
    AliasSearchPolicy,
    RegistryPolicy,
    load_registry_policy,
)

# ── the contract file exists and says what the code assumes ───────────────


def test_the_contract_file_is_present():
    assert REGISTRY_YAML.exists(), f"{REGISTRY_YAML} is the source of truth for NFR-10"
    assert REGISTRY_YAML.parent == CONTRACT_DIR


def test_the_real_policy_is_contract_backed():
    policy = load_registry_policy()
    assert policy.source == CONTRACT
    assert policy.source_path == str(REGISTRY_YAML)


def test_the_contract_file_agrees_with_the_built_in_defaults():
    """They must not disagree while both exist.

    A silent divergence is exactly the failure the assertion guards against,
    so it is worth catching in the window where defaults are still present.
    """
    policy = load_registry_policy()
    assert policy.in_window_months == DEFAULT_POLICY.in_window_months
    assert policy.alias_search == DEFAULT_POLICY.alias_search


def test_the_contract_file_is_versioned():
    raw = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    assert raw["version"] == "1.0"


# ── part 1: the source field ──────────────────────────────────────────────


def test_defaults_are_labelled_as_defaults(tmp_path):
    policy = load_registry_policy(tmp_path / "absent.yaml")
    assert policy.source == DEFAULTS
    assert policy.source_path is None


def test_contract_load_is_labelled_and_records_the_path(tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text("in_window_months: 24\n", encoding="utf-8")
    policy = load_registry_policy(path)
    assert policy.source == CONTRACT
    assert policy.source_path == str(path)


# ── part 2: load-time logging ─────────────────────────────────────────────


def test_a_defaults_load_warns_loudly(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger="collect.registry.policy"):
        load_registry_policy(tmp_path / "absent.yaml")
    assert "built-in defaults" in caplog.text
    assert "refuses to start" in caplog.text


def test_a_contract_load_says_where_it_came_from(tmp_path, caplog):
    path = tmp_path / "registry.yaml"
    path.write_text('version: "9.9"\nin_window_months: 24\n', encoding="utf-8")
    with caplog.at_level(logging.INFO, logger="collect.registry.policy"):
        load_registry_policy(path)
    assert str(path) in caplog.text
    assert "9.9" in caplog.text


# ── part 3: the refusal ───────────────────────────────────────────────────


def test_development_starts_on_defaults():
    """The whole point of the fallback: development keeps working."""
    assert_contract_backed(DEFAULT_POLICY, environment="development")


def test_production_refuses_on_defaults():
    with pytest.raises(UnversionedConfigError, match="built-in defaults"):
        assert_contract_backed(DEFAULT_POLICY, environment="production")


@pytest.mark.parametrize("environment", ["production", "staging", "ci", ""])
def test_every_non_development_environment_refuses(environment: str):
    with pytest.raises(UnversionedConfigError):
        assert_contract_backed(DEFAULT_POLICY, environment=environment)


def test_production_starts_when_the_policy_is_contract_backed():
    assert_contract_backed(load_registry_policy(), environment="production")


def test_the_refusal_names_the_file_it_wanted():
    with pytest.raises(UnversionedConfigError, match="registry.yaml"):
        assert_contract_backed(DEFAULT_POLICY, environment="production")


def test_the_refusal_cites_the_requirement():
    with pytest.raises(UnversionedConfigError, match="NFR-10"):
        assert_contract_backed(DEFAULT_POLICY, environment="production")


def test_a_hand_built_policy_claiming_contract_is_accepted():
    """The check is on provenance, not on values.

    Faking `source` is possible and deliberately not defended against: this
    guards a mistake, not an adversary.
    """
    faked = RegistryPolicy(source=CONTRACT, source_path="/wherever")
    assert_contract_backed(faked, environment="production")


# ── the contract file actually drives behaviour ───────────────────────────


def test_editing_the_yaml_changes_behaviour_with_no_code_change(tmp_path):
    """NFR-10's acceptance criterion, executed."""
    path = tmp_path / "registry.yaml"
    path.write_text(
        textwrap.dedent(
            """
            in_window_months: 1
            alias_search:
              declared_surfaces_only: false
              expand_mechanically: true
            """
        ),
        encoding="utf-8",
    )
    policy = load_registry_policy(path)
    assert policy.in_window_months == 1
    assert policy.alias_search == AliasSearchPolicy(
        declared_surfaces_only=False, expand_mechanically=True
    )
