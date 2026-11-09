"""A media model's GitHub search: its name, in its kind's repos (#602).

No network: the plan and the sieve only.
"""
from __future__ import annotations

import pytest

from collect.adapters.queries.github import (
    MediaReposError,
    load_media_repos,
    plan_mention_searches,
)

H3 = ["hailuo 3 max", "minimax h3 max", "minimax hailuo 3 max", "hailuo-3-max", "hailuo3max"]


def test_the_contract_loads_with_owners_and_speech_split_from_transcription():
    kinds, cap = load_media_repos()
    assert cap == 15
    assert {"image", "video", "speech", "transcription"} <= set(kinds)
    assert all(r.count("/") == 1 for repos in kinds.values() for r in repos)
    # Anooj's review: whisper repos cannot mention a text-to-speech model.
    assert not any("whisper" in r for r in kinds["speech"])
    assert all("whisper" in r for r in kinds["transcription"])


def test_names_go_first_then_spellings_and_the_cap_holds():
    repos = ("a/one", "b/two", "c/three", "d/four")
    plan = plan_mention_searches(H3, repos, max_requests=10)
    assert len(plan.requests) == 10
    assert plan.requests[0].query == '"hailuo 3 max" type:issue repo:a/one'
    assert [r.query.split('"')[1] for r in plan.requests[:8]] == (
        ["hailuo 3 max"] * 4 + ["minimax h3 max"] * 4)


def test_the_sieve_reads_the_name_alone_in_any_spelling():
    req = plan_mention_searches(H3, ("a/one",), max_requests=1).requests[0]
    assert req.sieve("Hailuo-3-Max node crashes on 2k output").passed
    assert not req.sieve("Wan 2.2 node crashes on 2k output").passed


def test_a_repo_without_an_owner_refuses(tmp_path):
    p = tmp_path / "repos.yaml"
    p.write_text("version: 1\nmax_requests_per_fetch: 15\nkinds:\n  image: [ComfyUI]\n",
                 encoding="utf-8")
    with pytest.raises(MediaReposError, match="owner/repo"):
        load_media_repos(p)


@pytest.mark.parametrize("name, text, named", [
    ("mai voice 2.1", "Tried MAI-Voice-2.1 for audiobooks", True),   # hyphens folded
    ("mai-voice-2.1", "mai voice 2.1 is good", True),                # either way round
    ("mai voice 2.1", "maivoice2.1 rocks", True),                    # joined
    ("kling 3 pro", "Kling-3-Pro clip", True),
    ("kling 3 pro", "Kling 3.0 Pro clip", False),                    # ".0" is not a separator
    ("mai voice 2.1", "mai voice 2.10", False),                      # the whole version
    ("kling 3 pro", "Inkling 3 pro", False),                         # the whole word
    ("mai voice 2.1", "Choose Mai2 or Mo Xu?", False),               # a voicebank
    ("mai voice 2.1", "dropped (MAI Voice-2)", False),               # the previous model
    ("seedance 2", "Seedance 2.5 is out", False),                    # not into a longer version
    ("seedance 2.0", "tried Seedance-2.0 today.", True),            # a full stop ends it
    ("mai voice 2", "MAI-Voice-2.1 sounds", False),
    # A VERSION WRITTEN WITHOUT A SEPARATOR (#602 review, rule 10: a prefix is a
    # different identifier). Folding drops separators, so these must still refuse.
    ("seedance 2", "Seedance 20 is out", False),
    ("mai voice 2", "MAI-Voice-21", False),
    ("seedance 2.0", "Seedance 2.05", False),
    ("seedance 2.0", "seedance20 test", True),                       # the same name, folded
])
def test_names_folded_reads_a_name_in_any_spelling_and_nothing_else(name, text, named):
    """#602: "mai voice 2.1" missed "MAI-Voice-2.1" before separators were folded."""
    from collect.adapters.queries.sieve import names_folded

    assert names_folded(name, text) is named


def test_every_excluded_search_subreddit_carries_its_reason():
    from collect.registry.sources import load_sources

    excluded = load_sources().sweep_subreddits.get("search_excluded") or []
    assert excluded, "the crack subreddit from the 2026-11-06 run is listed"
    assert all(e.get("id") and str(e.get("reason", "")).strip() for e in excluded)


@pytest.mark.parametrize(("name", "forms"), [
    # A second name in brackets is split off, so "Nano Banana 2" is known.
    ("Google: Nano Banana 2 (Gemini 3.1 Flash Image)",
     ("Nano Banana 2 (Gemini 3.1 Flash Image)", "Nano Banana 2", "Gemini 3.1 Flash Image")),
    # A one-word QUALIFIER is not: "(free)" made 18 of 403 media posts "name a model".
    ("Inception: Mercury Decide (free)", ("Mercury Decide (free)", "Mercury Decide")),
    # Too short to name anything in prose: "H3" matched 17 of 403 titles.
    ("MiniMax: H3", ()),
    # One ordinary word with no version: "Sonar" matched an ordinary sentence.
    ("Perplexity: Sonar", ()),
    ("Kwaivgi: Kling3", ("Kling3",)),
    ("Seedance 2.0", ("Seedance 2.0",)),
])
def test_name_forms_splits_a_second_name_but_not_a_qualifier(name, forms):
    from collect.adapters.queries.sieve import name_forms

    assert name_forms(name) == forms
