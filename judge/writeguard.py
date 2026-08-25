"""Refuse the one combination that can put fixture data in the shared database.

THE HAZARD, IN ONE LINE. `ENVIRONMENT=development` switches OFF the
build-fixture guard - `collect/registry/assertions.py` returns early on it in
three places - and a write command pointed at the shared AWS database while
that flag is set can write seeded and hand-curated rows into production.

Neither half is wrong on its own, which is what makes the pair dangerous:

    development + local database      correct, and the normal way to work
    staging/production + remote       correct, the guard is on
    development + REMOTE database     the fixture guard is off and the target
                                      is shared. This is the one.

WHY THIS IS CODE RATHER THAN A LINE IN THE HANDOVER. The flag is set for a
reason that has nothing to do with writing: `ENVIRONMENT=development` is also
what makes sign-in accept the credentials published in `.env.example`, so
anyone running the UI locally against staging has it set, correctly, and then
`judge extract` is one command away. A rule that has to be remembered at
exactly the moment somebody is thinking about something else is not a rule, it
is a hope.

WHAT IS PROTECTING US TODAY, AND WHY IT IS NOT ENOUGH. `run-backend.py
--staging` appends `default_transaction_read_only=on`, so the API cannot write
whatever it tries - the guarantee is in Postgres rather than in a promise. But
that flag is on the API's connection string. `judge/cli.py` builds its own
connection from a bare DATABASE_URL and never had a gate of ANY kind: no
preflight, no environment check, nothing. `collect/cli.py` gates its write
commands through `_gate()`; the judge side simply did not.

THIS DOES NOT REPLACE THE PREFLIGHT CHECKS. It refuses one specific pairing
that the preflight cannot see, because the preflight is what the flag turns
off. Wiring `preflight()` into judge's write path is the larger fix and is
E2's to make.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse

#: Hosts that cannot be somebody else's database.
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0", ""})

DEV = "development"


class UnsafeWriteRefused(RuntimeError):
    """Raised instead of writing. Carries what to change, not just what is wrong."""


#: What a postgres DSN starts with. Checked because "no host" is ambiguous.
POSTGRES_SCHEMES = frozenset({"postgresql", "postgres"})


def is_local(url: str) -> bool:
    """True when the DSN points at this machine.

    A MISSING HOST MEANS TWO DIFFERENT THINGS and they must not collapse.
    `postgresql:///modelboard` is a unix socket on this box - genuinely local.
    `not a url at all` also parses to `hostname=None`, and calling that local
    would let the guard pass on input it could not read.

    The scheme separates them. Anything that is not recognisably a postgres DSN
    is treated as REMOTE, because the safe direction for an unknown target is to
    refuse. (Written the other way round first, with a comment claiming this
    behaviour; `urlparse` returns None rather than raising on junk, so the
    comment was true and the code was not. Found by the test for it.)
    """
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").strip().lower()
        scheme = (parsed.scheme or "").strip().lower()
    except ValueError:
        return False

    if scheme not in POSTGRES_SCHEMES:
        return False
    return host in LOCAL_HOSTS


def environment() -> str:
    return (os.getenv("ENVIRONMENT") or DEV).strip().lower()


def check(url: str | None, *, command: str) -> None:
    """Raise `UnsafeWriteRefused` for development-flag-plus-remote-database.

    Called before a write command opens its transaction. Every other
    combination passes untouched - this refuses one pairing, not a category.
    """
    if not url:
        return                      # no target; the caller's own error is clearer
    if environment() != DEV:
        return                      # the fixture guard is on, which is the point
    if is_local(url):
        return                      # your own machine, write whatever you like

    host = urlparse(url).hostname or "an unnamed host"
    raise UnsafeWriteRefused(
        f"refusing `{command}`: ENVIRONMENT=development and the database is {host}, "
        f"which is not this machine.\n\n"
        f"ENVIRONMENT=development switches OFF the build-fixture guard, so this "
        f"command could write seeded or hand-curated rows into a shared database. "
        f"Reading the board that way is fine and is why the flag is set; writing "
        f"is not.\n\n"
        f"Either point DATABASE_URL at your own Postgres, or set ENVIRONMENT to "
        f"match the target so the fixture checks actually run. Nothing was written."
    )
