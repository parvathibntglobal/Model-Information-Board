"""A post from a subreddit listing -> a `Thread`."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from common.thread import Thread

from . import SOURCE

SITE = "https://www.reddit.com"

# What Reddit shows in place of an account that no longer exists.
_NO_AUTHOR = {"[deleted]", ""}


def created_at(post: dict[str, Any]) -> datetime:
    """The post's creation time. A post without one is an error, never "now"."""
    value = post.get("created_utc")
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"reddit post {post.get('name') or post.get('id')} has no created_utc")
    return datetime.fromtimestamp(float(value), tz=UTC)


def thread_of(post: dict[str, Any], *, fetched_at: datetime) -> Thread:
    post_id = post.get("id")
    permalink = post.get("permalink")
    subreddit = post.get("subreddit")
    if not post_id or not permalink or not subreddit:
        raise ValueError(f"reddit post is missing id, permalink or subreddit: "
                         f"{ {k: post.get(k) for k in ('id', 'permalink', 'subreddit')} }")
    author = post.get("author")
    return Thread(
        source=SOURCE,
        # The fullname (t3_...), which is how every Reddit endpoint names a post.
        ext_id=post.get("name") or f"t3_{post_id}",
        kind="post",
        community=f"r/{subreddit}",
        # `url` on a link post is the linked page, not the thread: build the
        # thread's own address from `permalink`.
        url=SITE + permalink,
        root_id=str(post_id),
        title=post.get("title") or None,
        # The listing sends no selftext (2026-11-10); kept for when it does.
        # Markdown, not HTML, so it is NOT passed through plain_text, which
        # would strip anything shaped like a tag ("a<b>c").
        body=(post.get("selftext") or "").strip() or None,
        author=None if author in _NO_AUTHOR or author is None else author,
        created_at=created_at(post),
        fetched_at=fetched_at,
    )
