"""Reddit reassembly from stored documents, and the coverage it cannot recover.

`assemble_reddit_thread` is the pure core — no database, no fetching — so these
test the decisions that matter without a live Postgres:

  * the tree is real (root + ranked children), unlike the GitHub body-only path;
  * coverage the markers would have given is NULL, not zero (the fork the whole
    design turned on);
  * ids follow `reddit_document_id`, the convention a cross-lane fixture once
    disagreed with silently.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from collect.assemble.reddit import (
    POST_BODY_ONLY,
    StoredComment,
    _score_of,
    assemble_reddit_post,
    assemble_reddit_thread,
)
from collect.assemble.thread import SELECTION_METHOD
from collect.rawstore import RawStore

ROOT_ID = "reddit:t3_abc"
#: version/snapshot surfaces `names_version` counts; a bare family word is
#: deliberately absent so the low-specificity comment ranks last.
ALIASES = {"claude sonnet 4", "gpt-5"}


def _store() -> RawStore:
    return RawStore(Path(tempfile.mkdtemp()))


def _comment(cid: str, body: str, score: int | None = 1) -> StoredComment:
    return StoredComment(external_id=cid, body=body, score=score)


def _assemble(comments, root_text="A question about Claude Sonnet 4 and tools.", **kw):
    return assemble_reddit_thread(
        root_document_id=ROOT_ID,
        root_text=root_text,
        comments=list(comments),
        store=_store(),
        version_aliases=ALIASES,
        **kw,
    )


class TestItIsATreeNotABody:
    def test_root_plus_selected_children_are_the_members(self):
        assembled = _assemble([
            _comment("t1_1", "claude sonnet 4 fails at 6+ tools, schema breaks"),
            _comment("t1_2", "same here, tool_choice misconfigured"),
        ])
        # root is member 0; children follow as reddit: ids
        assert assembled.member_document_ids[0] == ROOT_ID
        assert all(m.startswith("reddit:") for m in assembled.member_document_ids)
        assert assembled.child_count >= 1

    def test_children_are_capped_at_max_children(self):
        many = [_comment(f"t1_{i}", f"comment {i} about gpt-5 tools") for i in range(12)]
        assembled = _assemble(many, max_children=5)
        assert assembled.child_count == 5, "only the top max_children are flattened"

    def test_observed_children_counts_every_held_comment_not_the_selected_five(self):
        many = [_comment(f"t1_{i}", f"comment {i}") for i in range(12)]
        assembled = _assemble(many, max_children=5)
        assert assembled.observed_children == 12, (
            "observed = voices we hold; child_count = what the extractor reads"
        )
        assert assembled.child_count == 5


class TestCoverageIsHonestlyNull:
    """The fork the whole design turned on: markers were never stored."""

    def test_hidden_children_min_is_null_not_zero(self):
        assembled = _assemble([_comment("t1_1", "gpt-5 is great at tools")])
        assert assembled.hidden_children_min is None, (
            "0 would assert the tree hid nothing; we cannot know that from "
            "stored documents"
        )

    def test_hidden_branches_unsized_is_null_not_zero(self):
        assembled = _assemble([_comment("t1_1", "gpt-5 is great at tools")])
        assert assembled.hidden_branches_unsized is None, (
            "unlike a blog, we did not 'look and find no markers' — we cannot look"
        )

    def test_coverage_ratio_is_null_because_the_floor_is_unknown(self):
        assembled = _assemble([_comment("t1_1", "gpt-5 tools")])
        row = assembled.as_row()
        assert "coverage_ratio" not in row, "generated column, never written"
        assert row["hidden_children_min"] is None


class TestRankingPrefersSpecificity:
    def test_a_version_and_error_comment_outranks_a_bare_reaction(self):
        specific = _comment(
            "t1_specific",
            "claude sonnet 4 throws JSONDecodeError at 6 tools, tool_choice=auto",
            score=1,
        )
        reaction = _comment("t1_reaction", "same lol", score=500)
        assembled = _assemble([reaction, specific], max_children=1)
        # the specific correction wins despite far less engagement
        assert "reddit:t1_specific" in assembled.member_document_ids
        assert "reddit:t1_reaction" not in assembled.member_document_ids


class TestIdsAndSelectionMethod:
    def test_child_ids_use_reddit_document_id_convention(self):
        assembled = _assemble([_comment("t1_xyz", "gpt-5 tool calling notes")])
        assert "reddit:t1_xyz" in assembled.member_document_ids

    def test_thread_root_id_is_the_root_document_id(self):
        assembled = _assemble([_comment("t1_1", "gpt-5 tools")])
        assert assembled.thread_root_id == ROOT_ID

    def test_selection_method_is_observed_because_ranking_did_happen(self):
        assembled = _assemble([_comment("t1_1", "gpt-5 tools")])
        assert assembled.selection_method == SELECTION_METHOD
        assert "@observed" in assembled.selection_method


class TestAnEmptyRootRefuses:
    def test_no_root_text_raises_rather_than_assembling_nothing(self):
        with pytest.raises(ValueError, match="no stored root text"):
            _assemble([_comment("t1_1", "gpt-5 tools")], root_text="")


class TestScoreParsing:
    def test_score_from_a_dict(self):
        assert _score_of({"score": 42}) == 42

    def test_score_from_a_json_string_column(self):
        assert _score_of('{"score": 7, "controversiality": 1}') == 7

    def test_a_missing_score_is_none_not_zero(self):
        assert _score_of({"controversiality": 1}) is None
        assert _score_of(None) is None
        assert _score_of("not json") is None


# ── the third shape: a post whose comments were never fetched ──────────────


class TestPostBodyOnly:
    """A search sweep returns posts, not threads. That is neither of the two.

    `assemble_reddit_documents` refused all 1,559 such posts until 2026-08-28 -
    correctly, because its only alternative was calling a childless post a Reddit
    thread. The refusal was right and the options were incomplete.
    """

    def test_it_is_not_whole_document(self):
        """The blog value would assert the post IS the whole document."""
        assembled = assemble_reddit_post(
            "reddit:t3_x", "Haiku 4.5 is fast. Much faster than Sonnet.",
            comment_count=47, store=_store(), pipeline_version="test-1",
        )
        assert assembled.selection_method == POST_BODY_ONLY
        assert assembled.selection_method != "whole_document"

    def test_hidden_children_min_is_the_platforms_count_not_zero(self):
        """0 would make a post with 47 comments read as a post with none.

        `coverage_ratio` is GENERATED from observed / (observed + hidden), so 0
        gives 0/0 -> NULL, the empty-tree case. 47 gives 0.0, which says we read
        the root and none of the thread. Low against wrong.
        """
        assembled = assemble_reddit_post(
            "reddit:t3_x", "title and body", comment_count=47,
            store=_store(), pipeline_version="test-1",
        )
        assert assembled.observed_children == 0
        assert assembled.hidden_children_min == 47
        assert assembled.hidden_branches_unsized == 0

    def test_a_post_with_no_comments_reports_zero_hidden(self):
        """The genuine empty-tree case, which is allowed to be NULL downstream."""
        assembled = assemble_reddit_post(
            "reddit:t3_x", "title and body", comment_count=0,
            store=_store(), pipeline_version="test-1",
        )
        assert assembled.hidden_children_min == 0

    def test_the_offset_map_falls_out_of_it(self):
        """The whole point: a quote needs a position, not only a string.

        `collect/CLAUDE.md`'s first rule is that the map cannot be rebuilt later,
        so a body-only assembly is what makes these documents' quotes verifiable
        against an offset rather than only against a substring.
        """
        assembled = assemble_reddit_post(
            "reddit:t3_x", "Haiku 4.5 is fast. Much faster.", comment_count=1,
            store=_store(), pipeline_version="test-1",
        )
        segments = assembled.flattened.as_offset_map()
        assert segments, "no offset map, no verifiable quote"
        assert tuple(assembled.member_document_ids) == ("reddit:t3_x",)

    def test_empty_text_refuses_rather_than_assembling_nothing(self):
        """Same refusal as `assemble_issue`, and for the same reason."""
        with pytest.raises(ValueError) as excinfo:
            assemble_reddit_post(
                "reddit:t3_x", "   ", comment_count=3,
                store=_store(), pipeline_version="test-1",
            )
        assert "fabricating extractor" in str(excinfo.value)

    def test_the_flattened_text_is_the_post_not_a_payload(self):
        """A JSON envelope here would make a quote verify against a field VALUE.

        `text_ref` pointed at `json.dumps(post.raw)` for 1,507 documents on
        2026-08-28 - the sweeps stored the payload where the text belongs. A
        substring check against that JSON passes, because `"selftext": "..."`
        contains the text, which is rule 1 returning true for the wrong reason.
        """
        assembled = assemble_reddit_post(
            "reddit:t3_x", "Haiku 4.5 is fast. Much faster.", comment_count=0,
            store=_store(), pipeline_version="test-1",
        )
        assert not assembled.flattened.text.lstrip().startswith("{")
        assert "Haiku 4.5 is fast" in assembled.flattened.text
