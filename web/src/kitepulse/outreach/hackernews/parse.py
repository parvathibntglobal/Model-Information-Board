"""An Algolia HN hit -> a `Thread`."""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from typing import Any

from . import SOURCE
from .thread import Thread

ITEM_URL = "https://news.ycombinator.com/item?id={id}"

_PARAGRAPH = re.compile(r"<p>|<br\s*/?>", re.I)
_TAG = re.compile(r"<[^>]+>")


def plain_text(value: str | None) -> str | None:
    """HN's HTML (`<p>`, `&#x27;`, links) as plain text for a person to read."""
    if not value or not value.strip():
        return None
    text = html.unescape(_TAG.sub("", _PARAGRAPH.sub("\n\n", value))).strip()
    return text or None


def _kind(hit: dict[str, Any]) -> str:
    tags = hit.get("_tags") or ()
    if "comment" in tags:
        return "comment"
    if "story" in tags:
        return "story"
    raise ValueError(f"HN hit {hit.get('objectID')} is neither story nor comment: {tags}")


def thread_of(hit: dict[str, Any], *, fetched_at: datetime) -> Thread:
    ext_id = str(hit["objectID"])
    kind = _kind(hit)
    created_i = hit.get("created_at_i")
    if not isinstance(created_i, int | float):
        raise ValueError(f"HN hit {ext_id} has no created_at_i")

    if kind == "comment":
        root = hit.get("story_id")
        title = hit.get("story_title")
        body = plain_text(hit.get("comment_text"))
    else:
        root = ext_id
        title = hit.get("title")
        body = plain_text(hit.get("story_text"))

    return Thread(
        source=SOURCE,
        ext_id=ext_id,
        kind=kind,
        community=SOURCE,
        url=ITEM_URL.format(id=ext_id),
        root_id=str(root) if root is not None else None,
        title=title or None,
        body=body,
        author=hit.get("author") or None,
        created_at=datetime.fromtimestamp(int(created_i), tz=UTC),
        fetched_at=fetched_at,
    )
