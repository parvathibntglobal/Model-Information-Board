"""One candidate thread, the same shape for every source.

The fields mirror the planned `kp_outreach_thread` table
(ARCHITECTURE.md section 6), so the file output today becomes database rows
later without a reshape.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

STATUS_FOUND = "found"
STATUS_DROPPED = "dropped"

# Drop reasons. One spelling each, used by the filters and the summary.
TOO_OLD = "too_old"
NO_TEXT = "no_text"
COMMUNITY_NOT_ALLOWED = "community_not_allowed"
ALREADY_ANSWERED = "already_answered"
CLOSED = "closed"                 # closed or archived: nobody can reply

# Flags: the thread is kept, and the reviewer should know this.
COMMUNITY_PENDING_REVIEW = "community_pending_review"
# The team check read only the first posts of a long thread and found no team
# account there. Not "nobody on the team replied".
TEAM_CHECK_PARTIAL = "team_check_partial"
# GitHub: the asker has marked a reply as the answer. Someone may still add
# something useful, so this is a flag and not a drop.
ANSWERED = "answered"
# GitHub: the repo's owner started the discussion, which on 2026-11-06 was
# mostly a maintainer announcing or planning a feature, not someone asking.
# Unmeasured, so a flag and not a drop (CLAUDE.md rule 8).
POSTED_BY_REPO_OWNER = "posted_by_repo_owner"


@dataclass
class Thread:
    source: str
    ext_id: str
    kind: str                     # hackernews: story | comment; discourse: topic;
                                  # devto: article; github: discussion
    community: str                # hackernews, a forum's host, dev.to, or a GitHub
                                  # repo (owner/name)
    url: str
    root_id: str | None           # the story or topic this item belongs to
    title: str | None
    body: str | None              # plain text, for a person to read
    author: str | None
    created_at: datetime
    fetched_at: datetime
    matched_problems: list[str] = field(default_factory=list)
    matched_phrases: list[str] = field(default_factory=list)
    status: str = STATUS_FOUND
    drop_reason: str | None = None
    flags: list[str] = field(default_factory=list)

    def drop(self, reason: str) -> None:
        self.status = STATUS_DROPPED
        self.drop_reason = reason

    def record(self) -> dict:
        out = asdict(self)
        out["created_at"] = self.created_at.isoformat()
        out["fetched_at"] = self.fetched_at.isoformat()
        return out
