"""The only way this lane makes an HTTP request.

NFR-5 requires an identifying User-Agent with a contact URL, on every
request, to every platform, and calls it not optional. `Settings.user_agent`
defaults to the empty string and `.env.example` ships a placeholder, so
"required" needs enforcing rather than documenting.

**The check fires in the client constructor, not at startup.** A startup
assertion is bypassed by any code path that builds a client later, and the
first adapter written in a hurry is exactly such a path. There is no way to
obtain a client from this module without passing it.

Same shape as `assert_no_fixtures` and `assert_terms_reviewed`: a rule with
no enforcement is a comment.
"""

from __future__ import annotations

from typing import Any

import httpx

from collect.config import settings

#: Substrings that mean somebody shipped the template rather than a value.
#: A contact URL that does not resolve is worse than none at all, because it
#: looks like diligence.
PLACEHOLDER_MARKERS: tuple[str, ...] = (
    "your-contact-url.example",
    "example.com",
    "example.org",
    "localhost",
    "todo",
    "changeme",
)


class UserAgentError(RuntimeError):
    """No identifying User-Agent, so no request may be made (NFR-5)."""


def assert_identifying_user_agent(user_agent: str) -> None:
    """Refuse to build a client without a real, contactable User-Agent.

    Three ways to fail, and the message says which:

      empty        nothing was configured
      no contact   identifies software but gives nobody to reach
      placeholder  the template shipped instead of a value

    The last is the one worth guarding hardest. `.env.example` carries
    `+https://your-contact-url.example`, and a URL that 404s reads as
    diligence to whoever is rate-limiting us while telling them nothing.
    """
    if not user_agent or not user_agent.strip():
        raise UserAgentError(
            "Refusing to build an HTTP client: USER_AGENT is empty. NFR-5 requires "
            "an identifying User-Agent with a contact URL on every request, to "
            "every platform. Set it in .env; see .env.example."
        )

    if "http://" not in user_agent and "https://" not in user_agent:
        raise UserAgentError(
            f"Refusing to build an HTTP client: USER_AGENT {user_agent!r} carries no "
            "contact URL. NFR-5 wants somebody reachable, not just software named. "
            "Use the form: modelboard/0.1 (+https://example.invalid/project)"
        )

    lowered = user_agent.lower()
    found = [marker for marker in PLACEHOLDER_MARKERS if marker in lowered]
    if found:
        raise UserAgentError(
            f"Refusing to build an HTTP client: USER_AGENT {user_agent!r} still "
            f"contains the placeholder {found[0]!r}. A contact URL that does not "
            "resolve is worse than none, because it looks like diligence to "
            "whoever is deciding whether to rate-limit us."
        )


def build_client(
    *,
    user_agent: str | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    **kwargs: Any,
) -> httpx.Client:
    """An httpx client that cannot exist without an identifying User-Agent.

    Every adapter goes through here. Constructing `httpx.Client` directly
    anywhere in this lane is the bug this function exists to make visible,
    and `tests/test_lane_boundary.py` checks for it.
    """
    agent = user_agent if user_agent is not None else settings().user_agent
    assert_identifying_user_agent(agent)

    merged = {"User-Agent": agent}
    if headers:
        merged.update(headers)
    return httpx.Client(headers=merged, timeout=timeout, **kwargs)
