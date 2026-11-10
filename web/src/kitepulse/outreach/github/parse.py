"""A GitHub discussion search node -> the common Thread record."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from common.thread import Thread

from . import SOURCE
from .client import created_at

# communities.yaml key: GitHub's own rules apply to every repo. Each repo can
# add its own code of conduct on top, which the reviewer reads per thread.
COMMUNITY = "github"


def repo_of(node: dict[str, Any]) -> str:
    return (node.get("repository") or {}).get("nameWithOwner") or ""


def thread_of(node: dict[str, Any], *, fetched_at: datetime) -> Thread:
    repo = repo_of(node)
    return Thread(
        source=SOURCE,
        ext_id=f"{repo}#{node['number']}",
        kind="discussion",
        community=repo,
        url=node["url"],
        root_id=None,
        title=node.get("title") or None,
        body=(node.get("bodyText") or "").strip() or None,
        author=(node.get("author") or {}).get("login"),   # None: a deleted account
        created_at=created_at(node),
        fetched_at=fetched_at,
    )
