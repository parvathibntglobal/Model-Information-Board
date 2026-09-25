"""E3 child ranking: additive score, first-hand term, relevance tiers, cap of 25.

    score = specificity + w x log1p(votes) + first_hand + relevance[tier]

No database: the lexicon is built from rows in memory, and the weights are the
real ones from `contract/harvest.yaml:child_ranking`.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from collect.assemble import ranking
from collect.assemble.ranking import (
    OTHER_MODEL,
    SUBJECT,
    TOPIC_ONLY,
    UNKNOWN,
    UNRELATED,
    is_first_hand,
    lexicon_from_rows,
    rank_children,
    ranking_config,
    relevance_of,
    select_children,
    selection_lines,
    thread_subjects,
)

LEXICON = lexicon_from_rows([
    ("Claude Opus 5", "claude opus 5", "claude"),
    ("Opus 4.8", "opus 4.8", "claude"),
    ("Claude", "claude", "claude"),
    ("GPT-5", "gpt-5", "gpt"),
])
ROOT = "Claude Opus 5 capability thread: how does it hold up on long tasks?"


def _c(external_id: str, body: str, score: int | None = None):
    return SimpleNamespace(external_id=external_id, body=body, score=score)


class TestTheContract:
    def test_every_weight_is_read_from_the_contract(self):
        config = ranking_config()
        assert config.max_children == 25
        assert set(config.relevance) == set(ranking.TIERS)
        assert config.relevance[UNRELATED] < 0 < config.relevance[SUBJECT]
        assert config.relevance[UNKNOWN] == 0, "an absent subject is not a penalty"

    def test_the_thread_cap_follows_the_contract(self):
        from collect.assemble.thread import MAX_CHILDREN

        assert ranking_config().max_children == MAX_CHILDREN


class TestASumNotAProduct:
    def test_zero_votes_no_longer_zeroes_a_specific_comment(self):
        (child,) = rank_children(
            [_c("a", "It fails with `TypeError: bad arg` after 3 calls.", score=0)],
            version_aliases=set(),
        )
        assert child.specificity > 0
        assert child.score == pytest.approx(child.specificity), "no votes, no penalty"

    def test_a_platform_with_no_scores_ranks_by_content_not_by_id(self):
        """Hacker News and GitHub publish no comment score. Under the product
        every child was 0 and the id tie-break chose."""
        ranked = rank_children(
            [_c("a_first", "Nice.", None),
             _c("z_last", "Timeout: 504 after 30s at 128k tokens.", None)],
            version_aliases=set(),
        )
        assert ranked[0].external_id == "z_last"
        assert ranked[0].upvotes is None

    def test_popularity_cannot_carry_an_unspecific_comment_past_a_specific_one(self):
        ranked = rank_children(
            [_c("joke", "lol same", score=900),
             _c("fix", "You had `tool_choice` misconfigured, it returns error 400.", score=2)],
            version_aliases=set(),
        )
        assert ranked[0].external_id == "fix"


class TestFirstHand:
    @pytest.mark.parametrize("text", [
        "I tried it on our repo and it stalled.",
        "We switched to it last week.",
        "My experience: it drops the schema after a while.",
        "Our testing showed 40% fewer retries.",
        "I used it for a month.",
    ])
    def test_the_authors_own_words_count(self, text):
        assert is_first_hand(text)

    def test_a_quoted_report_is_somebody_elses_sentence(self):
        assert not is_first_hand("> I tried it and it was great\n\nSource: their blog.")

    def test_code_is_not_prose(self):
        assert not is_first_hand("```\n# I tried this config\nmodel: x\n```")

    def test_a_relay_is_not_first_hand(self):
        assert not is_first_hand("The model card says it scores 90.9 on GPQA.")

    def test_it_adds_the_bonus(self):
        plain, told = rank_children(
            [_c("a", "It is slow."), _c("b", "I tried it. It is slow.")],
            version_aliases=set(),
        )[::-1]
        assert told.first_hand and not plain.first_hand
        assert told.score - plain.score == pytest.approx(ranking_config().first_hand_bonus)


class TestRelevance:
    """The user's example: a Claude capability thread."""

    def setup_method(self):
        self.subjects = thread_subjects(ROOT, LEXICON)

    def test_the_root_names_the_subject(self):
        assert self.subjects == frozenset({"claude"})

    def test_a_comment_about_the_subject_model_is_relevant(self):
        tier = relevance_of("Opus 4.8 did this better, honestly.", self.subjects, LEXICON)
        assert tier == SUBJECT

    def test_a_comment_about_another_model_is_less_relevant(self):
        assert relevance_of("GPT-5 pricing is $20 a month.", self.subjects, LEXICON) == OTHER_MODEL

    def test_naming_both_is_about_the_subject(self):
        assert relevance_of("Claude beat GPT-5 on this.", self.subjects, LEXICON) == SUBJECT

    def test_a_comment_with_no_model_and_no_capability_is_unrelated(self):
        assert relevance_of("Got a CUDA driver crash on boot.", self.subjects, LEXICON) == UNRELATED

    def test_a_capability_reply_that_does_not_rename_the_model_is_kept_close(self):
        assert relevance_of(
            "The context window falls apart past 100k.", self.subjects, LEXICON
        ) == TOPIC_ONLY

    def test_a_root_naming_no_model_leaves_every_child_unknown_not_unrelated(self):
        assert thread_subjects("What do people use for coding?", LEXICON) is None
        assert relevance_of("CUDA crash", None, LEXICON) == UNKNOWN

    def test_no_lexicon_means_unknown(self):
        assert relevance_of("Claude is great", frozenset({"claude"}), None) == UNKNOWN

    def test_the_tiers_order_the_example(self):
        a, b, c = _c("c1", "Claude handles this fine."), _c("c2", "GPT-5 is cheaper."), \
            _c("c3", "Got a CUDA driver crash on boot.")
        order = [r.external_id for r in rank_children(
            [c, b, a], version_aliases=set(), root_text=ROOT, lexicon=LEXICON
        )]
        assert order == ["c1", "c2", "c3"]


class TestTheCap:
    def test_the_top_25_are_kept_of_30(self):
        comments = [_c(f"c{i:02d}", f"Comment {i}.", score=i) for i in range(30)]
        selection = select_children(comments, version_aliases=set())
        assert len(selection.ranked) == 30
        assert len(selection.selected) == 25

    def test_an_explicit_limit_still_wins(self):
        comments = [_c(f"c{i}", "x") for i in range(10)]
        assert len(select_children(comments, version_aliases=set(), limit=3).selected) == 3


class TestTheLogLines:
    def test_every_kept_child_prints_its_four_terms(self):
        selection = select_children(
            [_c("t1_a", "I tried Claude on this: error 500.", score=4),
             _c("t1_b", "GPT-5 is cheaper.", score=None)],
            version_aliases=set(), root_text=ROOT, lexicon=LEXICON,
        )
        lines = selection_lines("reddit:t3_x", selection)

        assert lines[0].startswith("    reddit:t3_x: kept 2 of 2 comment(s)")
        assert "first-hand 1 kept / 1 seen" in lines[0]
        assert "subject: claude" in lines[0]
        assert "[subject]" in lines[1] and "t1_a" in lines[1]
        assert "votes 4" in lines[1]
        assert lines[2].strip() == '"I tried Claude on this: error 500."', "the comment itself"
        assert "votes n/a" in lines[3], "a missing score prints n/a, not 0"
        assert lines[4].strip() == '"GPT-5 is cheaper."'
        assert all(line.isascii() for line in lines)

    def test_a_long_comment_is_cut_to_one_line(self):
        from collect.assemble.ranking import EXCERPT_CHARS, excerpt

        text = "line one\n\n" + "word " * 100
        cut = excerpt(text)
        assert "\n" not in cut
        assert len(cut) == EXCERPT_CHARS and cut.endswith("...")

    def test_the_comments_below_the_cut_are_shown_as_dropped(self):
        comments = [_c(f"c{i:02d}", f"Comment number {i}.", score=i) for i in range(30)]
        lines = selection_lines("t", select_children(comments, version_aliases=set()))

        assert "-- dropped: showing 5 of 5 below the cut --" in [line.strip() for line in lines]
        dropped = [line for line in lines if line.endswith("dropped")]
        assert len(dropped) == 5
        assert dropped[0].lstrip().startswith("#26")
