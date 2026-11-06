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

# Flags: the thread is kept, and the reviewer should know this.
COMMUNITY_PENDING_REVIEW = "community_pending_review"


@dataclass
class Thread:
    source: str
    ext_id: str
    kind: str                     # story | comment
    community: str
    url: str
    root_id: str | None           # the story this item belongs to
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
