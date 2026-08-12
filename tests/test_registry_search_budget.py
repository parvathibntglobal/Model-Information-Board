"""Search eligibility and the harvest query budget (FR-7, FR-11).

Search-eligible and attribution-eligible are separate. Every alias resolves a
mention; only some are worth spending a rate-limited request on.
"""

from __future__ import annotations

import textwrap

from collect.registry.aliases import alias_rows, all_alias_rows, normalize, search_queries
from collect.registry.policy import (
    CONTRACT,
    DEFAULT_POLICY,
    AliasSearchPolicy,
    RegistryPolicy,
    load_registry_policy,
)
from collect.registry.seed import load_seed_file

CAPABILITIES = 12
GITHUB_REQ_PER_MIN = 30


def _models():
    return load_seed_file().models


def _rows(policy: AliasSearchPolicy | None = None):
    return all_alias_rows(_models(), policy)


# ── the budget, pinned ────────────────────────────────────────────────────


def test_query_budget_is_pinned_not_capped():
    """54 strings x 12 capabilities = 648 queries, about 22 minutes on GitHub.

    Pinned rather than bounded on purpose. Widening the alias list is a
    legitimate thing to do, and when somebody does it this test fails with
    the new number instead of silently absorbing it. A budget that quietly
    absorbs growth is how a harvest ends up truncated (FR-11).
    """
    queries = search_queries(_rows())
    assert len(queries) == 54
    assert len(queries) * CAPABILITIES == 648
    assert round(len(queries) * CAPABILITIES / GITHUB_REQ_PER_MIN) == 22


def test_no_query_string_is_issued_twice():
    queries = search_queries(_rows())
    assert len(queries) == len(set(queries))


# ── the two eligibilities are independent ─────────────────────────────────


def test_every_alias_stays_attribution_eligible():
    """Trimming search must not cost a single resolvable mention."""
    permissive = AliasSearchPolicy(declared_surfaces_only=False, expand_mechanically=True)
    assert {r.normalized for r in _rows()} == {r.normalized for r in _rows(permissive)}


def test_ineligible_rows_carry_no_query_strings():
    """The persisted consequence of ineligibility, with no schema change."""
    for row in _rows():
        assert bool(row.variants) is row.search_eligible


def test_provider_prefixed_form_resolves_but_is_never_searched():
    """`anthropic/claude-opus-5` appears in configs, not in prose."""
    by_key = {r.normalized: r for r in _rows()}
    row = by_key[normalize("anthropic/claude-opus-5")]
    assert row.specificity == "snapshot"  # still attributes
    assert row.search_eligible is False
    assert row.variants == []


def test_dated_snapshot_id_resolves_but_is_never_searched():
    """The other dead-weight form, and a different case to the prefixed one.

    `claude-haiku-4-5-20251001` carries no provider prefix, so it is excluded
    by being auto-added rather than hand-declared.
    """
    by_key = {r.normalized: r for r in _rows()}
    row = by_key[normalize("claude-haiku-4-5-20251001")]
    assert "/" not in row.surface
    assert row.specificity == "snapshot"
    assert row.search_eligible is False


def test_exactly_eleven_rows_lose_search():
    """Ten provider-prefixed forms plus one dated snapshot id."""
    ineligible = [r for r in _rows() if not r.search_eligible]
    assert len(ineligible) == 11
    prefixed = [r for r in ineligible if "/" in r.surface]
    assert len(prefixed) == 10


def test_every_model_keeps_at_least_four_query_strings():
    for model in _models():
        assert len(search_queries(alias_rows(model))) >= 4, model.canonical_id


def test_hand_written_variants_are_what_gets_searched():
    """What somebody wrote in contract/ is what gets issued, verbatim."""
    opus = next(m for m in _models() if m.canonical_id == "anthropic/claude-opus-5")
    queries = set(search_queries(alias_rows(opus)))
    assert {opus.aliases.surface, *opus.aliases.variants} <= queries
    assert "anthropic/claude-opus-5" not in queries


# ── the policy is config, not code ────────────────────────────────────────


def test_permissive_policy_restores_the_old_budget():
    """The pre-fix behaviour, pinned so the saving stays visible.

    151 strings is 1812 queries and about 60 minutes on GitHub, against 54
    strings, 648 queries and 22 minutes now.
    """
    permissive = AliasSearchPolicy(declared_surfaces_only=False, expand_mechanically=True)
    assert len(search_queries(_rows(permissive))) == 151


def test_mechanical_expansion_only_widens_search():
    expanded = AliasSearchPolicy(expand_mechanically=True)
    assert len(search_queries(_rows(expanded))) > len(search_queries(_rows()))


def test_defaults_apply_when_the_contract_file_is_absent(tmp_path):
    assert load_registry_policy(tmp_path / "nothing.yaml") == DEFAULT_POLICY


def test_contract_file_overrides_the_defaults(tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text(
        textwrap.dedent(
            """
            in_window_months: 24
            alias_search:
              declared_surfaces_only: false
              expand_mechanically: true
            """
        ),
        encoding="utf-8",
    )
    policy = load_registry_policy(path)
    assert policy == RegistryPolicy(
        in_window_months=24,
        alias_search=AliasSearchPolicy(declared_surfaces_only=False, expand_mechanically=True),
        source=CONTRACT,
        source_path=str(path),
    )
