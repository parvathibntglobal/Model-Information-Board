"""A topic from `/latest.json` -> a `Thread`."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from common.text import plain_text
from common.thread import Thread

from . import SOURCE


def created_at(topic: dict[str, Any]) -> datetime:
    value = topic.get("created_at")
    if not isinstance(value, str):
        raise ValueError(f"topic {topic.get('id')} has no created_at")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def original_poster(topic: dict[str, Any], usernames: dict[int, str]) -> str | None:
    """The username the listing names as "Original Poster", if it names one."""
    for poster in topic.get("posters") or ():
        if "Original Poster" in (poster.get("description") or ""):
            return usernames.get(poster.get("user_id"))
    return None


def thread_of(
    topic: dict[str, Any], *, base_url: str, host: str, usernames: dict[int, str],
    fetched_at: datetime,
) -> Thread:
    topic_id = int(topic["id"])
    slug = topic.get("slug") or "topic"
    return Thread(
        source=SOURCE,
        ext_id=f"{host}/t/{topic_id}",
        kind="topic",
        community=host,
        url=f"{base_url.rstrip('/')}/t/{slug}/{topic_id}",
        root_id=str(topic_id),
        # `title` is the plain title (`fancy_title` is the HTML-escaped one), so
        # it is NOT passed through plain_text: a title like "Error in <tool>"
        # would lose its tag-shaped words.
        title=(topic.get("title") or "").strip() or None,
        # The listing's excerpt of the opening post, about 200 characters, or
        # None where the forum sends none. Never the whole post.
        body=plain_text(topic.get("excerpt")),
        author=original_poster(topic, usernames),
        created_at=created_at(topic),
        fetched_at=fetched_at,
    )
