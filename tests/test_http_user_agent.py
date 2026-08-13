"""NFR-5: an identifying User-Agent, enforced rather than documented.

No network. Every test builds or refuses to build a client.
"""

from __future__ import annotations

import pytest

from collect.http import (
    PLACEHOLDER_MARKERS,
    UserAgentError,
    assert_identifying_user_agent,
    build_client,
)

GOOD = "modelboard/0.1 (+https://github.com/parvathibntglobal/Model-Information-Board)"


# ── the three ways to fail ────────────────────────────────────────────────


@pytest.mark.parametrize("agent", ["", "   ", None])
def test_an_empty_user_agent_is_refused(agent):
    with pytest.raises(UserAgentError, match="empty"):
        assert_identifying_user_agent(agent or "")


def test_software_without_a_contact_url_is_refused():
    """NFR-5 wants somebody reachable, not just software named."""
    with pytest.raises(UserAgentError, match="no contact URL"):
        assert_identifying_user_agent("modelboard/0.1")


def test_the_shipped_placeholder_is_refused():
    """.env.example carries this exact string today."""
    with pytest.raises(UserAgentError, match="placeholder"):
        assert_identifying_user_agent("modelboard/0.1 (+https://your-contact-url.example)")


@pytest.mark.parametrize("marker", PLACEHOLDER_MARKERS)
def test_every_placeholder_marker_is_caught(marker: str):
    with pytest.raises(UserAgentError):
        assert_identifying_user_agent(f"modelboard/0.1 (+https://{marker}/x)")


def test_the_refusal_explains_why_a_dead_url_is_worse_than_none():
    """The reasoning belongs in the message, not only in a doc."""
    with pytest.raises(UserAgentError) as excinfo:
        assert_identifying_user_agent("modelboard/0.1 (+https://your-contact-url.example)")
    assert "looks like diligence" in str(excinfo.value)


# ── the good case ─────────────────────────────────────────────────────────


def test_a_real_user_agent_passes():
    assert_identifying_user_agent(GOOD)


def test_http_is_accepted_as_well_as_https():
    assert_identifying_user_agent("modelboard/0.1 (+http://reachable.invalid/project)")


# ── the constructor is the gate ───────────────────────────────────────────


def test_a_client_cannot_be_built_without_one():
    """Constructor rather than startup: a startup check is bypassed by any
    path that builds a client later, and the first adapter written in a
    hurry is exactly such a path."""
    with pytest.raises(UserAgentError):
        build_client(user_agent="")


def test_a_built_client_carries_the_user_agent():
    with build_client(user_agent=GOOD) as client:
        assert client.headers["User-Agent"] == GOOD


def test_extra_headers_cannot_displace_the_user_agent_by_accident():
    with build_client(user_agent=GOOD, headers={"Accept": "application/json"}) as client:
        assert client.headers["User-Agent"] == GOOD
        assert client.headers["Accept"] == "application/json"


def test_a_caller_may_override_the_user_agent_but_not_omit_it():
    other = "modelboard-test/0.1 (+https://reachable.invalid/x)"
    with build_client(user_agent=other) as client:
        assert client.headers["User-Agent"] == other
    with pytest.raises(UserAgentError):
        build_client(user_agent="modelboard-test/0.1")
