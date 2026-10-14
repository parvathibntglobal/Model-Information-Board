"""Every post gets a title no other post has already written.

Team ask, 2026-10-14: the post headings read alike. Measured over the 21 titles
on disk that day: 4 opened "<Model> review:", 3 of 3 head-to-heads closed on
"Route/Choose by Work(load)", 2 of 2 migration guides on "A Safe Migration
Guide". The checker refuses a worn shape and an echo of a title in use; the
title must name the subject, and the full keyword phrase moves to the
description and opening.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import generate_sample_blogs as g  # noqa: E402

TITLES = g.load_formats()["formats"][0]["titles"]


def refused(title, taken=(), names=()):
    return g.title_violations(title, {"titles": TITLES, "taken_titles": list(taken),
                                      "title_names": list(names)})


def test_a_worn_shape_is_refused_and_says_which_titles_wore_it():
    [v] = refused("Kimi K3 review: fast drafts, slow fixes", names=["Kimi K3"])
    assert "worn title shape" in v and "opened 4 titles" in v


def test_the_head_to_head_closer_is_refused():
    assert refused("Kimi K3 vs GLM 5: Choose by Workload", names=["Kimi K3", "GLM 5"])


def test_an_echo_of_a_title_in_use_is_refused():
    v = refused("Kimi K3 to GLM 5: Your Migration Guide, Made Safe",
                taken=["GPT-5.6 Sol vs GPT-6 Astra: A Safe Migration Guide"],
                names=["Kimi K3", "GLM 5"])
    assert any("echoes another post's title" in x and "guide, migration, safe" in x for x in v)


def test_shared_model_names_are_not_an_echo():
    """Two posts about one model share its name; that is not the same title."""
    assert not refused("Claude Opus 5.5 burns quota on overthinking",
                       taken=["Claude Opus 5.5 handles long refactors without drift"],
                       names=["Claude Opus 5.5"])


def test_one_shared_word_is_not_an_echo():
    assert not refused("Kimi K3 writes tests before it writes code",
                       taken=["DeepSeek V4 Flash trims cost on long code reviews"],
                       names=["Kimi K3"])


def test_a_distinct_title_passes():
    assert refused("Why Kimi K3 stalls on its 40th tool call", names=["Kimi K3"],
                   taken=["Claude Opus 5.5 review: fast coding, costly overthinking"]) == []


def test_the_title_names_the_subject_and_the_keyword_phrase_moves_out():
    seo = {"primary": "Kimi K3 review", "subject": ["Kimi K3"]}
    named = g.seo_violations({"title": "Why Kimi K3 stalls on its 40th tool call"}, seo)
    unnamed = g.seo_violations({"title": "Why agents stall on the 40th tool call"}, seo)
    assert not [v for v in named if v.startswith("title:")]
    assert "title: must name 'Kimi K3'" in unnamed


def test_a_title_problem_is_never_waved_through_as_style():
    assert not g.is_style("title: 'x' uses a worn title shape (y); write a title only this post "
                          "could have")
    assert not g.is_style("title: 'x' echoes another post's title 'y' (shares a, b); say it in "
                          "different words")


def test_the_prompt_no_longer_asks_for_the_keyword_in_the_title():
    rule = next(line for line in g.SYSTEM.splitlines()
                if line.startswith("- The brief names a PRIMARY KEYWORD"))
    assert "in the title" not in rule and "TITLE must name the subject" in rule
