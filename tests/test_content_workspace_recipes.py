"""Topic recipes: each topic kind's look and, per platform, its format and media.

The real table must be sound against the seed (every listed pair has a recipe,
every format exists on its platform, every media kind is one the workspace
stores), and each way of getting it wrong must be caught by name.
"""

from __future__ import annotations

import copy

import pytest

from judge.content_workspace import recipes, settings


@pytest.fixture()
def real():
    return copy.deepcopy(settings.load()), copy.deepcopy(settings.seed())


def test_the_real_table_is_sound(real):
    s, seed = real
    assert recipes.problems(s, seed) == []


def test_a_format_the_platform_does_not_have_is_caught(real):
    s, seed = real
    s["topic_recipes"]["price_change"]["platforms"]["reddit"]["format"] = "carousel_text"
    assert any("price_change: reddit format 'carousel_text'" in p
               for p in recipes.problems(s, seed))


def test_a_listed_pair_without_a_recipe_is_caught(real):
    s, seed = real
    del s["topic_recipes"]["price_change"]["platforms"]["bluesky"]
    assert "bluesky lists 'price_change' but there is no recipe for it" in recipes.problems(s, seed)


def test_text_only_needs_a_reason_and_makes_no_media(real):
    s, seed = real
    r = s["topic_recipes"]["news_digest"]
    r.pop("why")
    r["platforms"]["x"]["media"] = ["card_png"]
    found = recipes.problems(s, seed)
    assert "news_digest: look none needs a why" in found
    assert "news_digest: x makes media but the kind's look is none" in found


def test_an_unknown_look_or_media_kind_is_caught(real):
    s, seed = real
    s["topic_recipes"]["price_change"]["look"] = "site_tokens"
    s["topic_recipes"]["price_change"]["platforms"]["x"]["media"] = ["gif"]
    found = recipes.problems(s, seed)
    assert any(p.startswith("price_change: look 'site_tokens'") for p in found)
    assert any("price_change: x media 'gif'" in p for p in found)


def test_a_block_shows_its_look_and_recipe(real):
    s, _seed = real
    r = recipes.for_block(s, "reddit", "price_change")
    assert r["missing"] is False and r["format"] == "image_post"
    assert r["look"]["key"] == "data_card" and r["media"] == ["card_png"]


def test_a_pair_with_no_recipe_says_so_rather_than_guessing(real):
    s, _seed = real
    r = recipes.for_block(s, "facebook", "price_change")
    assert r["missing"] is True and "No recipe yet" in r["note"]
