"""An article from the dev.to listing -> a `Thread`."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from common.thread import Thread

from . import SOURCE
from .client import published_at

COMMUNITY = "dev.to"


def thread_of(article: dict[str, Any], *, fetched_at: datetime) -> Thread:
    article_id = str(article["id"])
    return Thread(
        source=SOURCE,
        ext_id=article_id,
        kind="article",
        community=COMMUNITY,
        url=article.get("url") or f"https://dev.to{article.get('path') or ''}",
        root_id=article_id,
        title=(article.get("title") or "").strip() or None,
        # The listing's description: the author's own summary, or the first
        # ~150 characters of the article. Never the whole article.
        body=(article.get("description") or "").strip() or None,
        author=(article.get("user") or {}).get("username") or None,
        created_at=published_at(article),
        fetched_at=fetched_at,
    )
