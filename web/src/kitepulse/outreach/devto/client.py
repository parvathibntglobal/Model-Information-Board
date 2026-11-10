"""HTTP calls to the dev.to (Forem) API. GET only, no key, robots.txt obeyed
(`common/http.py`)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from common.http import FetchError, ReadOnlyClient

BASE_URL = "https://dev.to"
ARTICLES = "/api/articles"
COMMENTS = "/api/comments"

PER_PAGE = 1000          # the API's maximum
MIN_INTERVAL_SECONDS = 1.0

# A small margin on the age check: the server's "last N days" and our clock
# need not agree to the second.
WINDOW_SLACK = timedelta(hours=1)

DevtoError = FetchError


def published_at(article: dict[str, Any]) -> datetime:
    value = article.get("published_at")
    if not isinstance(value, str):
        raise DevtoError(f"dev.to article {article.get('id')} has no published_at")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class DevtoClient(ReadOnlyClient):
    def __init__(self, user_agent: str, **kwargs: Any) -> None:
        super().__init__(BASE_URL, user_agent, min_interval=MIN_INTERVAL_SECONDS, **kwargs)

    def tag_week(
        self, tag: str, *, days: int, now: datetime, max_pages: int
    ) -> tuple[list[dict[str, Any]], bool]:
        """Every article in `tag` published in the last `days` days, and whether
        the listing was read to its end (False: stopped at `max_pages`)."""
        out: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            data = self.get_json(
                ARTICLES, {"tag": tag, "top": days, "per_page": PER_PAGE, "page": page}
            )
            if not isinstance(data, list):
                raise DevtoError(f"dev.to {ARTICLES}?tag={tag}: expected a JSON list")
            for article in data:
                # The two filters were applied, or the run stops. A listing
                # that ignored them would look like an answer and be wrong.
                if tag not in (article.get("tag_list") or ()):
                    raise DevtoError(
                        f"dev.to returned article {article.get('id')} without tag "
                        f"{tag!r}: the tag filter was not applied"
                    )
                if published_at(article) < now - timedelta(days=days) - WINDOW_SLACK:
                    raise DevtoError(
                        f"dev.to returned article {article.get('id')} published "
                        f"{article.get('published_at')}, outside top={days}: the "
                        "date filter was not applied"
                    )
            out.extend(data)
            if len(data) < PER_PAGE:
                return out, True
        return out, False

    def comment_authors(self, article_id: int) -> set[str]:
        """Every username in an article's comment tree."""
        data = self.get_json(COMMENTS, {"a_id": article_id})
        if not isinstance(data, list):
            raise DevtoError(f"dev.to {COMMENTS}?a_id={article_id}: expected a JSON list")
        names: set[str] = set()
        stack = list(data)
        while stack:
            node = stack.pop()
            username = (node.get("user") or {}).get("username")
            if username:
                names.add(username)
            stack.extend(node.get("children") or ())
        return names
