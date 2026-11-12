"""`contract/assistantbenchmark_models.yaml`: registry rows only, and they stay that way.

anooj, 2026-11-12: the assistants assistantbenchmark.com scores get registry rows
so the board and the benchmark section share one canonical id each, but no
nightly fetch. These tests pin what makes that safe. No database.
"""
from __future__ import annotations

from pathlib import Path

from collect.registry.aliases import normalize
from collect.registry.seed import load_seed_file
from judge import config

ROOT = Path(__file__).resolve().parent.parent
AB = ROOT / "contract" / "assistantbenchmark_models.yaml"
AGENTS = ROOT / "contract" / "agent_models.yaml"

#: The ordinary-word names in the file (rule 10): none may be an alias on its own.
ORDINARY = {"hark", "town", "tomo", "pally", "catch", "tab", "shuffle", "dazzle", "kicker",
            "orchid", "caddy", "boba", "poke", "del", "orbits", "folk", "brea", "instinct"}


def _keys(seed) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in seed.models:
        for v in [m.aliases.surface, *m.aliases.variants]:
            out[normalize(v)] = m.canonical_id
    return out


def test_the_file_loads_with_unique_ids():
    ids = [m.canonical_id for m in load_seed_file(AB).models]
    assert ids and len(ids) == len(set(ids))


def test_registry_only_never_fetched_never_a_model():
    ab = {m.canonical_id for m in load_seed_file(AB).models}
    assert not ab & {a.registry for a in config.tracked_agents()}
    assert not ab & {m.registry for m in config.tracked_models() if m.registry}


def test_no_id_or_alias_collides_with_the_agents():
    ab, agents = load_seed_file(AB), load_seed_file(AGENTS)
    assert not {m.canonical_id for m in ab.models} & {m.canonical_id for m in agents.models}
    clash = set(_keys(ab)) & set(_keys(agents))
    assert not clash, clash


def test_an_ordinary_word_is_never_an_alias_on_its_own():
    """Rule 10: a bare ordinary word would file every sentence using it."""
    bare = ORDINARY & set(_keys(load_seed_file(AB)))
    assert not bare, bare


def test_instinct_is_held_until_it_has_an_alias():
    """No source-backed alias exists for it (2026-11-12); a row is added only with one."""
    assert "unknown/instinct" not in {m.canonical_id for m in load_seed_file(AB).models}
