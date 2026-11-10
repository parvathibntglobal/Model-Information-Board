"""HTTP calls to one Discourse forum. GET only, and only where robots.txt allows
(`common/http.py` says how robots.txt is read and what counts as a failure)."""

from __future__ import annotations

from typing import Any

from common.http import FetchError, ReadOnlyClient, RobotsDisallowed

LATEST = "/latest.json"
TOPIC = "/t/{id}.json"
MIN_INTERVAL_SECONDS = 1.0

# The names this folder used before the client moved to common/.
DiscourseError = FetchError
__all__ = ["DiscourseClient", "DiscourseError", "RobotsDisallowed"]


class DiscourseClient(ReadOnlyClient):
    def __init__(self, base_url: str, user_agent: str, **kwargs: Any) -> None:
        super().__init__(base_url, user_agent, min_interval=MIN_INTERVAL_SECONDS, **kwargs)

    def _object(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        data = self.get_json(path, params)
        if not isinstance(data, dict):
            raise DiscourseError(f"{self.base}{path}: expected a JSON object")
        return data

    def latest_topics(self, page: int) -> dict[str, Any]:
        """One page (30 topics) of the newest-created listing. Page 0 is newest."""
        params: dict[str, Any] = {"order": "created"}
        if page:
            params["page"] = page
        data = self._object(LATEST, params)
        if not isinstance(data.get("topic_list"), dict):
            raise DiscourseError(f"{self.base}{LATEST}: no topic_list in the response")
        return data

    def topic_authors(self, topic_id: int) -> tuple[set[str], bool]:
        """Usernames seen in a topic, and whether that covers every post.

        `/t/<id>.json` carries only the first posts (about 20) plus a list of
        frequent participants, so for a long topic the answer can be partial.
        """
        data = self._object(TOPIC.format(id=topic_id))
        posts = (data.get("post_stream") or {}).get("posts") or []
        names = {p["username"] for p in posts if p.get("username")}
        participants = (data.get("details") or {}).get("participants") or []
        names |= {p["username"] for p in participants if p.get("username")}
        complete = len(posts) >= int(data.get("posts_count") or 0)
        return names, complete
