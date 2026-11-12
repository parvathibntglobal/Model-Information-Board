"""`contract/assistantbenchmark_models.yaml`: registry rows only, and they stay that way.

anooj, 2026-11-12: the assistants assistantbenchmark.com scores get registry rows
so the board and the benchmark section share one canonical id each, but no
nightly fetch. These tests pin what makes that safe. No database.
"""
from __future__ import annotations

from pathlib import Path

from collect.registry.aliases import alias_rows, local_part, normalize
from collect.registry.seed import load_seed_file
from judge import config

ROOT = Path(__file__).resolve().parent.parent
AB = ROOT / "contract" / "assistantbenchmark_models.yaml"
AGENTS = ROOT / "contract" / "agent_models.yaml"

#: The ordinary-word names in the file (rule 10): none may be an alias on its own.
ORDINARY = {"hark", "town", "tomo", "pally", "catch", "tab", "shuffle", "dazzle", "kicker",
            "orchid", "caddy", "boba", "poke", "del", "orbits", "folk", "brea", "instinct"}


#: Ordinary PHRASES that matching folds to one key with a name (#624 review): held.
ORDINARY_PHRASES = {"with del"}


def _keys(seed) -> dict[str, str]:
    """Every normalised key the LOADER would write for these rows - the declared
    aliases AND the rows it builds from the canonical id and its local part
    (#624 review: reading only the declared aliases missed the id-built ones)."""
    out: dict[str, str] = {}
    for m in seed.models:
        for row in alias_rows(m):
            out[row.normalized] = m.canonical_id
    return out


def test_no_local_part_is_an_ordinary_word():
    """The loader turns each id's local part into a snapshot alias, so `town/town`
    would put the bare word "town" in the alias table. The local part is the
    compound alias instead (`town/town-com`)."""
    bad = [m.canonical_id for m in load_seed_file(AB).models
           if normalize(local_part(m.canonical_id)) in ORDINARY]
    assert not bad, bad


def test_no_alias_is_an_ordinary_phrase():
    keys = set(_keys(load_seed_file(AB)))
    assert not {normalize(p) for p in ORDINARY_PHRASES} & keys


def test_no_alias_key_is_three_characters_or_fewer():
    """STRUCTURAL, not a word list. A list only catches the words someone thought
    of: `wajo/fo` and `unknown/szn` passed it and would have filed every "FO" and
    every "summer szn" (slang for season). Any key this short is a token prose
    produces by accident, so it is refused whatever it spells."""
    short = sorted(k for k in _keys(load_seed_file(AB)) if len(k) <= 3)
    assert not short, short


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


def test_the_three_held_assistants_stay_out():
    """Instinct: no source-backed alias. Folk: "folk app" is also the folk CRM.
    Del: "withdel" needs the spaced form "with del", an ordinary phrase. Each is
    added only with an alias that is neither an ordinary word nor phrase."""
    names = {m.display_name.lower() for m in load_seed_file(AB).models}
    assert not {"instinct", "folk", "del"} & names
