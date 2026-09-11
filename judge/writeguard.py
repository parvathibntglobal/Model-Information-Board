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
from urllib.parse import unquote, urlparse

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
        # This guard refuses only the DEV+remote pairing. It does NOT assert a
        # fixture check runs here: judge/ does not call preflight(), so on a
        # non-dev flag NO fixture check runs on this path - returning here only
        # declines to over-refuse, it does not hand off to another guard.
        return
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
        f"Point DATABASE_URL at your own Postgres. Nothing was written.\n\n"
        f"Setting ENVIRONMENT=staging will also satisfy this check and is NOT a "
        f"substitute: no fixture check runs on this path yet (judge/ does not "
        f"call preflight()), so it turns this guard off without turning another "
        f"one on."
    )


def describe(url: str | None) -> str:
    """`host:port/dbname` for a log line. NEVER the credentials, NEVER raises.

    A DSN carries a password, so the string itself may not be logged — and
    "connected to the database" is not checkable by a reader without the host,
    the port and the name, which is why all three are here and nothing else is.

    THE THREE UNHAPPY ANSWERS ARE DISTINCT, because collapsing them is the
    defect this exists to prevent. `unset` means nothing was configured,
    `unparseable` means something was and it is not a postgres DSN, and a
    missing hostname means a unix socket on this box. A single "unknown" for
    all three would reproduce, in the log, exactly the ambiguity that made the
    original failure invisible.
    """
    if not url or not url.strip():
        return "unset"
    try:
        parsed = urlparse(url)
        if (parsed.scheme or "").strip().lower() not in POSTGRES_SCHEMES:
            return "unparseable (not a postgresql:// DSN)"
        # `.port` is a property and raises ValueError on a non-numeric port,
        # which is why it is inside the try rather than beside the return.
        host = parsed.hostname or "(unix socket, this machine)"
        port = parsed.port or 5432
        name = (parsed.path or "").lstrip("/") or "(no database named)"
    except ValueError:
        return "unparseable"
    return f"{host}:{port}/{name}"


#: What `run-backend.py --staging` appends to the DSN, after unquoting. Named
#: here rather than spelled inline at each reader: it is written in one place
#: (that script) and read in two (the startup log, and any future guard), and a
#: typo in a substring test fails OPEN — it would report a read-write session as
#: read-only, which is the direction that matters.
READ_ONLY_MARKER = "default_transaction_read_only=on"


def is_read_only_dsn(url: str | None) -> bool:
    """True when the DSN itself forces the session read-only.

    A STATEMENT ABOUT THE DSN, NOT ABOUT THE SERVER. The connection options are
    what this can see; a server-side default, a role setting or a later `SET`
    are not, and none of them is claimed. It answers "did we ask for read-only",
    which is the half a log line can honestly report.
    """
    if not url:
        return False
    return READ_ONLY_MARKER in unquote(url)
