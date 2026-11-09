"""The Shortlister's code filters (ARCHITECTURE.md 5.2a). No model.

Each filter is a rule a person wrote, not a measured classifier. A dropped
thread keeps its reason and stays in the output, so an absence we caused never
reads as one we found (CLAUDE.md rule 6).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from . import thread as t
from .config import Community


def too_old(th: t.Thread, *, now: datetime, max_age_days: int) -> str | None:
    return t.TOO_OLD if th.created_at < now - timedelta(days=max_age_days) else None


def no_text(th: t.Thread) -> str | None:
    """A comment with no text, or a story or topic with neither title nor text.

    Hacker News blanks the text of dead and flagged comments but keeps the
    record, so this is a real state and not a parse failure.
    """
    if th.kind == "comment":
        return None if th.body else t.NO_TEXT
    return None if (th.title or th.body) else t.NO_TEXT


def closed(is_closed: bool) -> str | None:
    return t.CLOSED if is_closed else None


def community_not_allowed(c: Community) -> str | None:
    return t.COMMUNITY_NOT_ALLOWED if c.vendor_replies == "not_allowed" else None


def community_flag(c: Community) -> str | None:
    return t.COMMUNITY_PENDING_REVIEW if c.vendor_replies == "pending_review" else None


def already_answered(authors: Iterable[str], team_accounts: Iterable[str]) -> str | None:
    team = {a.lower() for a in team_accounts}
    return t.ALREADY_ANSWERED if any(a.lower() in team for a in authors) else None
