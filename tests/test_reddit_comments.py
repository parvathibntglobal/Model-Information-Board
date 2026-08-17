"""Reddit comment trees: parsing, coverage arithmetic, and what must not happen.

The coverage tests are the load-bearing ones. `hidden_children_min` exists to be
a FLOOR, and the obvious implementation — sum the reported counts — makes it a
weak one, because a marker reporting no count still guarantees at least one
hidden comment. On the measured thread that left 126 branches contributing zero
to a lower bound.
"""

from __future__ import annotations

import pytest

from collect.adapters.reddit_comments import (
    ThreadCoverage,
    parse_thread,
    permalink_of,
)


def comment(cid, *, parent, body="a body", replies=(), depth=0, **extra):
    inner = {
        "id": cid,
        "name": f"t1_{cid}",
        "parent_id": parent,
        "link_id": "t3_root",
        "subreddit": "ClaudeAI",
        "author": "someone",
        "author_fullname": "t2_abc",
        "body": body,
        "created_utc": "1781037764.0",
        "score": "7",
        "depth": str(depth),
        "controversiality": "0",
        **extra,
    }
    if replies:
        inner["replies"] = {"kind": "Listing", "data": {"children": list(replies)}}
    return {"kind": "t1", "data": inner}


def more(count=None, parent="t1_x"):
    inner = {"id": "m", "name": "t1_m", "parent_id": parent, "children": []}
    if count is not None:
        inner["count"] = str(count)
    return {"kind": "more", "data": inner}


def payload(children, *, num_comments="100"):
    return {
        "success": True,
        "data": [
            {"kind": "Listing", "data": {"children": [
                {"kind": "t3", "data": {
                    "id": "root", "name": "t3_root", "num_comments": num_comments,
                    "permalink": "/r/ClaudeAI/comments/root/slug/",
                }},
            ]}},
            {"kind": "Listing", "data": {"children": list(children)}},
        ],
    }


URL = "https://www.reddit.com/r/ClaudeAI/comments/root/slug/"


# ── the tree ─────────────────────────────────────────────────────────────


def test_nested_replies_are_walked_to_full_depth():
    tree = comment("a", parent="t3_root", replies=[
        comment("b", parent="t1_a", depth=1, replies=[
            comment("c", parent="t1_b", depth=2),
        ]),
    ])
    parsed = parse_thread(payload([tree]), url=URL)
    assert [c.external_id for c in parsed.comments] == ["t1_a", "t1_b", "t1_c"]
    assert parsed.max_depth == 2


def test_thread_root_comes_from_link_id_not_from_the_parent():
    """A depth-3 comment's parent is another comment, not the post.

    Inferring the root from `parent_id` would be right only at depth 0 and
    silently wrong everywhere below it — and `thread_root_id` is what groups a
    tree, so getting it wrong scatters one thread across many.
    """
    tree = comment("a", parent="t3_root", replies=[
        comment("b", parent="t1_a", depth=1),
    ])
    parsed = parse_thread(payload([tree]), url=URL)
    assert {c.thread_root_id for c in parsed.comments} == {"t3_root"}
    assert parsed.comments[1].parent_id == "t1_a"


def test_top_level_is_read_from_the_parent_prefix():
    tree = comment("a", parent="t3_root", replies=[comment("b", parent="t1_a", depth=1)])
    parsed = parse_thread(payload([tree]), url=URL)
    assert parsed.comments[0].is_top_level
    assert not parsed.comments[1].is_top_level


def test_numeric_fields_arrive_as_strings_and_are_coerced():
    """Reddit sends `score`, `depth` and `num_comments` as strings about half
    the time. A string score would sort lexically wherever it is ranked."""
    parsed = parse_thread(payload([comment("a", parent="t3_root")]), url=URL)
    assert parsed.comments[0].score == 7
    assert parsed.comments[0].depth == 0
    assert parsed.coverage.reported_total == 100


def test_an_empty_payload_yields_no_comments_and_no_false_coverage():
    parsed = parse_thread({"success": False, "data": {"error": 404}}, url=URL)
    assert parsed.comments == ()
    assert parsed.coverage.observed_children == 0
    assert parsed.coverage.coverage_ratio is None, "0/0 is not full coverage"


# ── deleted and removed are PRESENT, not absent ──────────────────────────


def test_a_deleted_body_is_a_body():
    """The comment exists and occupies a position. Its body is nine characters.

    An offset map has to survive that, so these are recognised rather than
    dropped — dropping them would renumber every sibling after them.
    """
    parsed = parse_thread(payload([comment("a", parent="t3_root", body="[deleted]")]),
                          url=URL)
    c = parsed.comments[0]
    assert c.is_deleted and not c.is_removed
    assert c.body == "[deleted]"
    assert parsed.coverage.observed_children == 1, "it counts toward what was seen"


def test_removed_is_distinguished_from_deleted():
    """Author removal and moderator removal are different facts."""
    parsed = parse_thread(payload([comment("a", parent="t3_root", body="[removed]")]),
                          url=URL)
    assert parsed.comments[0].is_removed and not parsed.comments[0].is_deleted


# ── coverage: the floor, and why the obvious form is too weak ────────────


def test_reported_counts_are_summed():
    parsed = parse_thread(payload([
        comment("a", parent="t3_root", replies=[more(19), more(14)]),
    ]), url=URL)
    assert parsed.coverage.hidden_children_min == 33
    assert parsed.coverage.hidden_branches_unsized == 0


def test_an_unsized_marker_contributes_one_not_zero():
    """THE REFINEMENT, and the reason the old bound was weak.

    A `more` marker with no count still guarantees at least one hidden comment.
    Summing only reported counts left 126 branches on the measured thread
    contributing zero to a number whose whole job is to be a floor.
    """
    parsed = parse_thread(payload([
        comment("a", parent="t3_root", replies=[more(None), more(None), more(None)]),
    ]), url=URL)
    assert parsed.coverage.hidden_children_min == 3
    assert parsed.coverage.hidden_branches_unsized == 3


def test_count_zero_is_unsized_not_empty():
    """Reddit uses `count: 0` for "continue this thread".

    There is provably something below it and no figure for it, so treating the
    zero as zero hidden is the same mistake as reading NULL as false.
    """
    parsed = parse_thread(payload([
        comment("a", parent="t3_root", replies=[more(0)]),
    ]), url=URL)
    assert parsed.coverage.hidden_children_min == 1
    assert parsed.coverage.hidden_branches_unsized == 1
    assert parsed.coverage.markers_sized == 0


def test_the_measured_thread_shape():
    """252 markers, 126 sized totalling 4,730, 126 unsized. From the refusal."""
    coverage = ThreadCoverage(
        observed_children=200, hidden_children_min=4730 + 126,
        hidden_branches_unsized=126, reported_total=4833,
        markers_total=252, markers_sized=126,
    )
    assert coverage.hidden_children_min == 4856
    assert coverage.known_minimum_size == 5056
    assert coverage.coverage_ratio == pytest.approx(200 / 5056)


def test_the_unsized_count_is_not_folded_into_the_bound():
    """Two numbers, because one would read as a measurement.

    "at least 340 hidden" sounds like arithmetic. "at least 340 hidden across
    126 branches, plus 126 branches of unknown size" is what the data supports.
    """
    coverage = ThreadCoverage(
        observed_children=10, hidden_children_min=340, hidden_branches_unsized=126,
        reported_total=None, markers_total=126, markers_sized=0,
    )
    described = coverage.describe()
    assert "at least 340 hidden" in described
    assert "126 of those branches report no size" in described


def test_coverage_ratio_is_an_upper_bound_not_an_estimate():
    """Its denominator is a floor on the tree, so the true ratio is lower."""
    coverage = ThreadCoverage(
        observed_children=200, hidden_children_min=800, hidden_branches_unsized=100,
        reported_total=None, markers_total=100, markers_sized=0,
    )
    assert coverage.coverage_ratio == 0.2
    # Every unsized branch could hold thousands, so 20% is the best case.
    worse = ThreadCoverage(
        observed_children=200, hidden_children_min=8000, hidden_branches_unsized=100,
        reported_total=None, markers_total=100, markers_sized=100,
    )
    assert worse.coverage_ratio < coverage.coverage_ratio


def test_no_markers_is_the_only_certain_case():
    parsed = parse_thread(payload([comment("a", parent="t3_root")]), url=URL)
    assert parsed.coverage.fully_observed
    assert parsed.coverage.coverage_ratio == 1.0
    assert parsed.coverage.describe() == "all 1 comments observed"


def test_reported_total_is_kept_beside_the_bound_rather_than_reconciled():
    """The two disagree on real data and forcing agreement hides which is wrong.

    Measured: 194 observed plus 860 min-hidden is 1,054 against a reported
    `num_comments` of 1,005. `num_comments` counts deleted comments and goes
    stale; the markers are a floor. Both are recorded.
    """
    parsed = parse_thread(payload([
        comment("a", parent="t3_root", replies=[more(860)]),
    ], num_comments="1005"), url=URL)
    assert parsed.coverage.reported_total == 1005
    assert parsed.coverage.known_minimum_size == 861
    assert parsed.coverage.reported_total != parsed.coverage.known_minimum_size


# ── the permalink trap ───────────────────────────────────────────────────


def test_permalink_is_preferred_over_url():
    """`document.url` for a link post is the LINKED CONTENT, not the thread.

    Measured on a live search: 5 of the 8 busiest results for one query had a
    non-permalink `url` — `i.redd.it` images and `reddit.com/gallery/…`. Fetching
    comments for those asks about something that is not a thread.
    """
    class Post:
        url = "https://i.redd.it/abc123.jpeg"
        raw = {"permalink": "/r/ClaudeAI/comments/1u1fsdi/slug/"}

    assert permalink_of(Post()) == "https://www.reddit.com/r/ClaudeAI/comments/1u1fsdi/slug/"


def test_a_url_without_a_permalink_is_accepted_only_if_it_is_a_thread():
    class Threadish:
        url = "https://www.reddit.com/r/ClaudeAI/comments/xyz/slug/"
        raw = {}

    class Imageish:
        url = "https://i.redd.it/abc123.jpeg"
        raw = {}

    assert permalink_of(Threadish()) is not None
    assert permalink_of(Imageish()) is None, "refuse rather than fetch the wrong thing"


# ── the boundary this module must not cross ──────────────────────────────


def test_nothing_here_assembles_a_thread():
    """Storage only. `assemble_thread` still refuses on the bounding problem.

    `ParsedThread` has no `flattened_text`, no `offset_map`, and no child
    selection. If any of those appear here, `thread_context` can be written
    without the four coverage columns and "the top 5 children" becomes
    indistinguishable from "the top 5 of the 4% we fetched".
    """
    parsed = parse_thread(payload([comment("a", parent="t3_root")]), url=URL)
    for forbidden in ("flattened_text", "offset_map", "selected", "children_ranked"):
        assert not hasattr(parsed, forbidden), f"{forbidden} belongs to E3, not here"


def test_coverage_exposes_no_weight_and_no_score():
    """These annotate inference from absence, never evidence quality.

    Engineer 2's framing: coverage does not discount the claim, it discounts
    inference from absence. Somebody said the thing; a 4% view does not make them
    not have said it. What it destroys is "and nobody contradicted them".

    So nothing here may look like an `f_*` factor. A property named `weight` or
    `factor` would be picked up by the next person wiring claim weights.
    """
    coverage = ThreadCoverage(1, 1, 1, None, 1, 0)
    for forbidden in ("weight", "factor", "f_coverage", "score", "confidence"):
        assert not hasattr(coverage, forbidden), (
            f"{forbidden} would invite coverage into weighting, which it must "
            "never enter"
        )
