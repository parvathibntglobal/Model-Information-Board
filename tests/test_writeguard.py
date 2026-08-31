"""The one combination that can put fixture data in the shared database.

`ENVIRONMENT=development` switches OFF the build-fixture guard —
`collect/registry/assertions.py` returns early on it in three places. It is
also, separately, what makes sign-in accept the credentials published in
`.env.example`, so anyone running the UI locally against staging has it set,
correctly. `judge extract` is then one command away, and `judge/cli.py` had no
gate of any kind: no preflight, no environment check, nothing.

What protects the API today is `run-backend.py --staging` forcing
`default_transaction_read_only=on`. That is on the API's connection string.
The CLI builds its own from a bare DATABASE_URL and never saw it.
"""
from __future__ import annotations

import pytest

from judge.writeguard import LOCAL_HOSTS, UnsafeWriteRefused, check, is_local

# TEST-NET-1, reserved for documentation, so this file adds no occurrence of the
# real infrastructure address. What matters to the guard is only that the host is
# not this machine.
SHARED = "postgresql://user:pw@192.0.2.10:5432/Model-information-Board"
LOCAL = "postgresql://user:pw@localhost:5432/modelboard"


@pytest.fixture(autouse=True)
def _dev(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")


# ── the pairing this exists for ─────────────────────────────────────────────


def test_development_plus_a_remote_database_is_refused():
    with pytest.raises(UnsafeWriteRefused) as raised:
        check(SHARED, command="judge extract")

    message = str(raised.value)
    assert "192.0.2.10" in message           # says which host
    assert "judge extract" in message        # says which command
    assert "Nothing was written" in message  # says what did not happen


def test_the_refusal_says_how_to_proceed_rather_than_only_what_is_wrong():
    with pytest.raises(UnsafeWriteRefused) as raised:
        check(SHARED, command="judge extract")

    message = str(raised.value)
    assert "DATABASE_URL" in message
    assert "ENVIRONMENT" in message


def test_the_remedy_does_not_offer_staging_as_a_safe_alternative():
    """#189: ENVIRONMENT=staging satisfies this check but runs NO fixture check
    on judge's path (preflight is uncalled), so the message must not present it
    as an equal remedy to changing the target. The safe remedy is the target."""
    with pytest.raises(UnsafeWriteRefused) as raised:
        check(SHARED, command="judge extract")

    message = str(raised.value)
    assert "your own Postgres" in message            # the remedy that is actually safe
    assert "not a substitute" in message.lower()     # staging named as NOT one
    assert "preflight" in message                     # and why: no check runs here


# ── and the three combinations that are fine ────────────────────────────────


def test_development_against_your_own_machine_is_fine():
    """The normal way to work. Refusing this would make the guard useless."""
    check(LOCAL, command="judge extract")


@pytest.mark.parametrize("host", sorted(LOCAL_HOSTS - {""}))
def test_every_local_spelling_is_recognised(host, monkeypatch):
    check(f"postgresql://u:p@{host}:5432/db", command="judge extract")


def test_a_unix_socket_dsn_with_no_host_is_local():
    """`postgresql:///name` is a socket on this box, not somebody else's server."""
    assert is_local("postgresql:///modelboard") is True
    check("postgresql:///modelboard", command="judge extract")


@pytest.mark.parametrize("environment", ["staging", "production", "STAGING"])
def test_a_remote_database_is_fine_when_the_flag_is_not_development(
    environment, monkeypatch
):
    """A non-development flag is not the pairing this guard refuses, so it passes.

    NOT because a fixture check runs here — on judge's path none does (preflight
    is uncalled, #189). This asserts the guard does not OVER-refuse; it must not
    become "never write to staging", which would be a different and wrong rule.
    """
    monkeypatch.setenv("ENVIRONMENT", environment)
    check(SHARED, command="judge extract")


# ── how it behaves on input it cannot read ──────────────────────────────────


@pytest.mark.parametrize("junk", ["://://not-a-url", "not a url at all", "http://example.com/db"])
def test_anything_that_is_not_a_postgres_dsn_is_treated_as_remote(junk):
    """The safe direction for a target we cannot read is to refuse it.

    `urlparse` returns `hostname=None` for junk rather than raising, so the
    first version of this read garbage as "no host" and therefore as local -
    the guard passing on exactly the input it could not understand. The scheme
    is what separates a unix socket from a string nobody can parse.
    """
    assert is_local(junk) is False


def test_no_url_at_all_passes_through():
    """`_connect` raises its own, clearer error for a missing DATABASE_URL.

    Refusing here would replace that message with one about environments,
    which is not what went wrong.
    """
    check(None, command="judge extract")
    check("", command="judge extract")


def test_an_unset_environment_counts_as_development():
    """Absent is not "some other environment" — it is the default the app uses.

    Reading it as non-development would silently disable this check for anyone
    who never set the variable, which is most people the first time.
    """
    import os

    os.environ.pop("ENVIRONMENT", None)
    with pytest.raises(UnsafeWriteRefused):
        check(SHARED, command="judge extract")
