"""Reddit's thread links must name rows that exist. The forward half of the repair.

WHAT THIS IS ABOUT. `document.id` for a Reddit row is `reddit:<fullname>`, and
`reddit_write.document_row` wrote `thread_root_id` and `parent_id` as the BARE
fullname — so every linkage it produced named no row. Measured on staging
2026-09-08: **1,420 `thread_root_id` and 1,420 `parent_id`, 2,840 references,
all dangling, and prefixing every one resolved with zero left over.**

Repaired in `contract/migrations/20260908T1100_reddit_thread_link_prefix.sql`
(applied to staging the same day). **This file is the forward half**: without it
the next sweep re-breaks what the migration repaired, and a backfill that keeps
being needed is one nobody can explain.

WHY IT SURVIVED SO LONG, WHICH IS THE PROPERTY THESE TESTS ENCODE.
`thread_root_id` carries no foreign key, deliberately — a comment must be
storable before its root is fetched. So nothing rejected the first bad row, and
nothing joined on the column until `collect/triage/run.py` did. A column with no
reader and no constraint is a column whose contents nobody has checked, which is
why the check belongs in a test rather than in the schema.
"""

from __future__ import annotations

from dataclasses import dataclass

from collect.adapters.reddit import reddit_document_id
from collect.adapters.reddit_write import _document_ref, document_row

#: A subreddit LISTING renders no query, so a NULL harvest_run_id is complete.
LISTING = "no_run_for_source"


@dataclass(frozen=True)
class FakeComment:
    """Enough of `RedditComment` to write a row. Fullnames as Reddit sends them."""

    external_id: str = "t1_ozoym09"
    parent_id: str = "t3_1v6a104"
    thread_root_id: str = "t3_1v6a104"
    url: str = "https://reddit.com/r/x/comments/1v6a104/_/ozoym09"
    author: str = "someone"
    author_fullname: str = "t2_abc"


@dataclass(frozen=True)
class FakePost:
    """A post. Its own root, so both link columns are absent."""

    external_id: str = "t3_1v6a104"
    url: str = "https://reddit.com/r/x/comments/1v6a104/title"
    author: str = "someone"
    author_fullname: str = "t2_abc"


def _row(item):
    return document_row(item, retrieval_provenance=LISTING)


# ── the property the 2,840 rows violated ─────────────────────────────────


def test_a_comments_links_name_the_ids_the_target_rows_carry():
    """THE regression. The bug was that these three did not agree.

    `id` had the prefix and the two link columns did not, so a self-join found
    nothing — silently, because there is no constraint to fail.
    """
    row = _row(FakeComment())
    assert row["id"] == "reddit:t1_ozoym09"
    assert row["thread_root_id"] == "reddit:t3_1v6a104"
    assert row["parent_id"] == "reddit:t3_1v6a104"


def test_the_link_columns_use_the_same_function_as_the_id():
    """One named convention, not three f-strings.

    `reddit_document_id` exists so a disagreement is a diff against a named
    function. The bug was that two of the three call sites were not call sites.
    """
    comment = FakeComment(thread_root_id="t3_root", parent_id="t1_parent")
    row = _row(comment)
    assert row["thread_root_id"] == reddit_document_id("t3_root")
    assert row["parent_id"] == reddit_document_id("t1_parent")


def test_a_reply_points_at_a_comment_and_a_top_level_comment_at_the_post():
    """Both kinds of parent get the prefix. `t1_` and `t3_` are not special-cased.

    Worth pinning because a fix that only handled `t3_` would repair the root
    link and leave 1,420 parent links dangling — half a repair, and the half
    that survives is the one nobody notices.
    """
    top_level = _row(FakeComment(external_id="t1_a", parent_id="t3_post"))
    reply = _row(FakeComment(external_id="t1_b", parent_id="t1_a"))
    assert top_level["parent_id"] == "reddit:t3_post"
    assert reply["parent_id"] == "reddit:t1_a"


# ── what must NOT be prefixed ────────────────────────────────────────────


def test_a_post_keeps_both_links_null_rather_than_gaining_a_string():
    """Rule 6 at the writer. NULL must not become `"reddit:None"`.

    A post is its own root and `document_row` writes both columns NULL for one -
    `document_row`'s docstring says inventing a self-reference would make "is
    this a root" unanswerable. A prefix applied blindly would turn that absence
    into a definite value that can never resolve, because no row can carry that
    id.
    """
    row = _row(FakePost())
    assert row["thread_root_id"] is None
    assert row["parent_id"] is None
    assert "reddit:None" not in repr(row)


def test_an_already_prefixed_value_passes_through_unchanged():
    """Idempotent, which is what made the migration's recovery a re-run.

    A double prefix (`reddit:reddit:t3_…`) is worse than the original bug: it
    still dangles, and it no longer looks like a convention mismatch, so the
    next person has to work out what happened rather than recognising it.
    """
    assert _document_ref("reddit:t3_x") == "reddit:t3_x"
    row = _row(FakeComment(thread_root_id="reddit:t3_x", parent_id="reddit:t1_y"))
    assert row["thread_root_id"] == "reddit:t3_x"
    assert row["parent_id"] == "reddit:t1_y"


def test_none_stays_none():
    assert _document_ref(None) is None


# ── the shape, stated as an invariant ────────────────────────────────────


def test_every_link_a_row_carries_is_shaped_like_a_document_id():
    """The invariant the missing foreign key cannot express.

    Not "is prefixed" - `github` ids legitimately carry no `<source>:` prefix at
    all, and a rule written as "every thread_root_id starts with its source"
    would be false there. The invariant is narrower and is about THIS writer:
    whatever it puts in a link column must be the same shape as what it puts in
    `id`, because those are the rows it is pointing at.
    """
    for item in (FakeComment(), FakePost()):
        row = _row(item)
        for column in ("thread_root_id", "parent_id"):
            value = row[column]
            if value is None:
                continue
            assert value.startswith("reddit:"), (column, value)
            # And it is an id this writer could have produced for a real row.
            assert value == reddit_document_id(value.removeprefix("reddit:"))
