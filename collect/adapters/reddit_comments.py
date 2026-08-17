"""Reddit comment trees: fetch, parse, store. **No assembly.**

WHY THIS EXISTS AND WHAT IT DELIBERATELY DOES NOT DO
-----------------------------------------------------
`offset_map` was designed for this platform: GitHub issues are nearly flat and
blogs have no children at all, so a Reddit thread is the only place the flattened
-span-to-raw-span problem is real. This module is the fetch half.

**It does not assemble.** `RedditHarvester.assemble_thread` still refuses, on the
reason that has always been the binding one: the selection cannot be bounded.
Wiring fetching to child selection would make `thread_context` record "the top 5
children" while meaning "the top 5 of the 4% we happened to fetch", and once that
is a row the two are indistinguishable. Storage is unblocked today; selection is
not, and this module exists so the bounding question can be answered from a
corpus rather than argued.

V1 (`getPostComments`) RATHER THAN V2, AND THE REASON IS TRUNCATION
-------------------------------------------------------------------
V2 returns a flat list with `parent_id`, which is easier to assemble from. It
also reports **no truncation markers at all**. V1 returns a nested tree to depth
9 and carries `kind: "more"` nodes saying how much it withheld.

Silent truncation is the failure this project keeps finding. An easier parse that
cannot tell you what is missing is the worse trade, so V1.

THE COVERAGE NUMBERS, AND WHAT THEY ARE FOR
--------------------------------------------
Engineer 2's framing, carried here because the numbers are meaningless without
it and someone will otherwise reach for them as a weight:

    **Coverage does not discount the claim. It discounts inference from
    absence.**

Somebody said the thing. Seeing 200 of 4,833 comments does not make them not
have said it, and the quote is verified against the text either way. What a 4%
view destroys is *"and nobody contradicted them"* — which is exactly what a
consensus count rests on.

So these numbers **must never enter `f_*` weighting**. They do not describe
evidence quality; they bound what may be concluded from silence, and they belong
at the cell, annotating conclusions drawn from what is not there.

`hidden_children_min` IS A FLOOR, AND THE OBVIOUS FORM MAKES IT A WEAK ONE
--------------------------------------------------------------------------
    hidden_children_min = sum(reported counts) + count(unsized markers)

The `+ count(unsized markers)` term is the refinement and it is free. A `more`
marker with no count still guarantees **at least one** hidden comment, so the
earlier form had 126 branches on the measured thread contributing zero to a
number whose whole job is to be a floor.

`hidden_branches_unsized` STAYS SEPARATE. Folding it in would produce one number
that reads as a measurement while half of it is a floor of one. Two numbers let a
cell say the true thing:

    "at least 340 hidden across 126 branches, plus 126 branches of unknown size"

rather than "at least 340 hidden", which sounds like arithmetic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger(__name__)

#: Reddit's fullname prefixes. `t1_` comment, `t3_` post, `t2_` account.
COMMENT_PREFIX = "t1_"
POST_PREFIX = "t3_"

#: Bodies Reddit substitutes when a comment is gone. They are NOT absent text —
#: the comment exists, occupies a position in the tree, and has these four
#: characters as its body. An offset map has to survive that, which is why they
#: are recognised rather than filtered.
DELETED_BODY = "[deleted]"
REMOVED_BODY = "[removed]"


def _int(value: Any) -> int | None:
    """Reddit returns numerics as strings about half the time. None stays None."""
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class RedditComment:
    """One comment, flattened out of the `kind`/`data` envelope.

    `parent_id` is a fullname and may be either `t1_` (a reply) or `t3_` (a
    top-level comment on the post). Keeping the prefix rather than stripping it
    is what makes "is this a root child" answerable without consulting the tree.
    """

    external_id: str            # t1_… — the fullname, never the bare id
    parent_id: str              # t1_… or t3_…
    thread_root_id: str         # t3_… — from link_id, not inferred
    url: str
    body: str
    author: str | None
    author_fullname: str | None  # t2_… — canonicalised by author_external_id
    subreddit: str
    created_utc: float | None
    score: int | None
    depth: int | None
    controversiality: int | None
    distinguished: str | None
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def created_at(self) -> datetime | None:
        """A real UTC timestamp, or None. Never the fetch time (rule 6)."""
        if self.created_utc is None:
            return None
        return datetime.fromtimestamp(self.created_utc, tz=UTC)

    @property
    def engagement(self) -> dict[str, Any]:
        """`document.engagement`'s shape for a comment.

        `upvote_ratio` is a post-level field and Reddit does not report it per
        comment, so it is absent rather than invented. `controversiality` is
        carried because a 1 there is the platform saying the score is a poor
        summary of reception — which is the case child ranking by engagement
        alone gets wrong.
        """
        return {
            "score": self.score,
            "controversiality": self.controversiality,
            "distinguished": self.distinguished,
        }

    @property
    def is_deleted(self) -> bool:
        """The AUTHOR removed it. Body is literally `[deleted]`."""
        return self.body.strip() == DELETED_BODY

    @property
    def is_removed(self) -> bool:
        """A MODERATOR removed it. Body is literally `[removed]`."""
        return self.body.strip() == REMOVED_BODY

    @property
    def is_top_level(self) -> bool:
        return self.parent_id.startswith(POST_PREFIX)

    @property
    def sieve_text(self) -> str:
        """What the sieve reads. A comment has no title."""
        return self.body


@dataclass(frozen=True)
class ThreadCoverage:
    """How much of the tree was seen, and how much provably was not.

    FOUR NUMBERS, and #5 proposed three. The fourth is
    `hidden_branches_unsized`, kept separate on purpose — see the module
    docstring. Flagged on #5 rather than added to `contract/tables.sql` here.

    NONE OF THESE MAY REACH `f_*`. They annotate inference from absence at the
    cell, not evidence quality on a claim.
    """

    observed_children: int
    hidden_children_min: int
    hidden_branches_unsized: int
    #: Reddit's own `num_comments` on the post. A SECOND, INDEPENDENT figure that
    #: can disagree with `observed + hidden_children_min` — it counts deleted
    #: comments, goes stale, and is not derived from the markers. Recorded rather
    #: than reconciled, because forcing them to agree would hide whichever one is
    #: wrong. None when the post listing did not carry it.
    reported_total: int | None
    markers_total: int
    markers_sized: int

    @property
    def known_minimum_size(self) -> int:
        """A floor on the tree's true size, from the markers alone."""
        return self.observed_children + self.hidden_children_min

    @property
    def coverage_ratio(self) -> float | None:
        """Observed share of the smallest tree consistent with the markers.

        AN UPPER BOUND ON COVERAGE, not an estimate of it: the denominator uses
        a FLOOR on hidden comments, so the true ratio can only be lower. Reading
        it as a measurement is the mistake `hidden_branches_unsized` exists to
        make visible — with 126 unsized branches, this number is as optimistic as
        the data allows.

        None when the tree is empty, because 0/0 is not 100% coverage (rule 6).
        """
        total = self.known_minimum_size
        if not total:
            return None
        return self.observed_children / total

    @property
    def fully_observed(self) -> bool:
        """No markers at all. The only case where coverage is certain."""
        return self.markers_total == 0

    def as_row(self) -> dict[str, Any]:
        """The four proposed `thread_context` columns, plus the two witnesses."""
        return {
            "observed_children": self.observed_children,
            "hidden_children_min": self.hidden_children_min,
            "hidden_branches_unsized": self.hidden_branches_unsized,
            "coverage_ratio": self.coverage_ratio,
            # not columns; recorded so a row can be re-derived and disputed
            "reported_total": self.reported_total,
            "markers_total": self.markers_total,
        }

    def describe(self) -> str:
        """The sentence a cell may honestly print. Never a bare percentage."""
        if self.fully_observed:
            return f"all {self.observed_children} comments observed"
        parts = [f"{self.observed_children} of at least {self.known_minimum_size} observed"]
        if self.hidden_children_min:
            parts.append(
                f"at least {self.hidden_children_min} hidden across "
                f"{self.markers_total} branches"
            )
        if self.hidden_branches_unsized:
            parts.append(
                f"{self.hidden_branches_unsized} of those branches report no size"
            )
        return "; ".join(parts)


def _children_of(listing: Any) -> list[dict[str, Any]]:
    """The `children` array inside a Listing envelope, or an empty list."""
    if isinstance(listing, dict):
        inner = listing.get("data")
        if isinstance(inner, dict) and isinstance(inner.get("children"), list):
            return inner["children"]
        if isinstance(listing.get("children"), list):
            return listing["children"]
    if isinstance(listing, list):
        return [node for node in listing if isinstance(node, dict)]
    return []


def _comment_of(inner: dict[str, Any], *, url: str, root_id: str) -> RedditComment:
    return RedditComment(
        external_id=str(inner.get("name") or f"{COMMENT_PREFIX}{inner.get('id')}"),
        parent_id=str(inner.get("parent_id") or root_id),
        # link_id names the thread. Inferring it from the first parent would be
        # wrong for every comment below depth 1.
        thread_root_id=str(inner.get("link_id") or root_id),
        url=url,
        body=str(inner.get("body") or ""),
        author=inner.get("author"),
        author_fullname=inner.get("author_fullname"),
        subreddit=str(inner.get("subreddit") or ""),
        created_utc=(lambda v: float(v) if v not in (None, "") else None)(
            inner.get("created_utc")
        ),
        score=_int(inner.get("score")),
        depth=_int(inner.get("depth")),
        controversiality=_int(inner.get("controversiality")),
        distinguished=inner.get("distinguished"),
        raw=inner,
    )


@dataclass(frozen=True)
class ParsedThread:
    """What one `getPostComments` call yielded."""

    root_post_id: str | None
    comments: tuple[RedditComment, ...]
    coverage: ThreadCoverage

    @property
    def max_depth(self) -> int:
        return max((c.depth or 0) for c in self.comments) if self.comments else 0

    @property
    def deleted(self) -> tuple[RedditComment, ...]:
        return tuple(c for c in self.comments if c.is_deleted)

    @property
    def removed(self) -> tuple[RedditComment, ...]:
        return tuple(c for c in self.comments if c.is_removed)


def parse_thread(payload: Any, *, url: str) -> ParsedThread:
    """Walk a V1 `getPostComments` payload into comments plus coverage.

    The payload is `[post_listing, comment_listing]`. Both are Listing
    envelopes; comments are `kind: "t1"` and truncation markers are
    `kind: "more"`, nested under each comment's `replies`.

    A `more` marker's `count` is the number of comments below it that were
    withheld. **`count: 0` is unsized, not empty** — Reddit uses it for the
    "continue this thread" case, where there is provably something there and no
    figure for it. Treating it as zero is what made the old bound weak.
    """
    listings = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(listings, list) or not listings:
        return ParsedThread(None, (), ThreadCoverage(0, 0, 0, None, 0, 0))

    post_children = _children_of(listings[0])
    root_inner = (post_children[0].get("data") or {}) if post_children else {}
    root_id = str(root_inner.get("name") or "")
    reported_total = _int(root_inner.get("num_comments"))

    comment_children = _children_of(listings[1]) if len(listings) > 1 else []

    comments: list[RedditComment] = []
    marker_counts: list[int | None] = []

    def walk(node: dict[str, Any]) -> None:
        kind = node.get("kind")
        inner = node.get("data")
        if not isinstance(inner, dict):
            return
        if kind == "more":
            marker_counts.append(_int(inner.get("count")))
            return
        if kind != "t1":
            # Listings can nest; anything else is not a comment and not a marker.
            return
        comments.append(_comment_of(inner, url=url, root_id=root_id))
        for child in _children_of(inner.get("replies")):
            walk(child)

    for node in comment_children:
        walk(node)

    sized = [c for c in marker_counts if c]
    unsized = len(marker_counts) - len(sized)
    coverage = ThreadCoverage(
        observed_children=len(comments),
        # sum of what was reported, PLUS one per branch that reported nothing:
        # an unsized marker still guarantees at least one hidden comment.
        hidden_children_min=sum(sized) + unsized,
        hidden_branches_unsized=unsized,
        reported_total=reported_total,
        markers_total=len(marker_counts),
        markers_sized=len(sized),
    )
    return ParsedThread(root_id or None, tuple(comments), coverage)


def permalink_of(post: Any) -> str | None:
    """The thread URL to fetch comments for, which is NOT `post.url`.

    `document.url` for a link post is the LINKED CONTENT — an `i.redd.it` image
    or a `reddit.com/gallery/…` page. Passing that to `getPostComments` asks for
    the comments of something that is not a thread. Measured on a live search:
    5 of the 8 busiest results for one query had a non-permalink `url`.

    `raw["permalink"]` is the thread path and is present on every post.
    """
    raw = getattr(post, "raw", None) or {}
    path = raw.get("permalink")
    if path:
        return f"https://www.reddit.com{path}"
    url = getattr(post, "url", None)
    if url and "/comments/" in url:
        return url
    return None
