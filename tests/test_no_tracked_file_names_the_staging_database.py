"""No tracked file names where the shared database lives, or who it lets in.

The staging host and its username were written into 34 docs, scripts and tests
as provenance lines (`measured against postgresql://<user>@<host>/...`). They
were replaced on 2026-09-25 with `203.0.113.5` (TEST-NET-3, RFC 5737: reserved
for documentation, never routed) and `example_user`, ahead of publishing a
snapshot of this tree.

⚠ THE REAL VALUES ARE NOT IN THIS FILE, AND NOT AS HASHES EITHER. A test that
  holds the string it guards republishes it, and a hash does not hide it: an
  IPv4 address is one of 2^32 and a short username falls to a laptop in
  minutes. So these checks are structural, and would catch a DIFFERENT real
  host or user as well as the one that was removed:

      every IPv4 literal is in a documentation, private or loopback range
      every connection string's user is a known placeholder

⚠ WHAT THEY DO NOT SEE. A bare username in prose, outside a DSN, passes. So
  does a hostname rather than an address. The DSN form is the one every one of
  the 20 removed occurrences took, which is why it is the one checked; a new
  shape needs a new check, not a looser pattern here.

⚠ AND THIS IS THE WORKING TREE, NOT HISTORY. The old values remain in every
  commit before the change. That is accepted on purpose: the public copy is a
  snapshot, and history stays in the private repository.
"""

from __future__ import annotations

import ipaddress
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: The documentation address every provenance line now uses.
PLACEHOLDER_HOST = "203.0.113.5"

#: Third-party content harvested verbatim. Its addresses and connection strings
#: belong to other people's systems, not ours, and whether it is published at
#: all is a separate decision (the snapshot exclusion list). Named file by file
#: so anything else that starts carrying one still fails.
HARVESTED = ("_github_shape_experiment.json", "articles/")

#: Users a reader cannot mistake for a real account: placeholders and the
#: test fixtures' own inventions. `$USER` is a shell variable in
#: `scripts/dev-postgres.ps1`, expanded at run time on the developer's machine.
PLACEHOLDER_USERS = frozenset({
    "example_user", "postgres", "user", "dbuser", "u", "x", "someone",
    "nobody", "$USER", "\u2026",
})

_SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".woff2", ".woff", ".ico", ".pdf"}
_IPV4 = re.compile(r"(?<![\d.])(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?![\d.])")
_DSN_USER = re.compile(r"postgres(?:ql)?://([^\s:/@\"'`<>]+)(?::[^\s@\"'`]*)?@")


def _tracked_text() -> list[tuple[str, str]]:
    """`git ls-files`, not a walk: the question is what would be published."""
    names = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True,
    ).stdout.decode("utf-8", "replace").split("\0")
    out = []
    for name in names:
        if not name or pathlib.Path(name).suffix.lower() in _SKIP_SUFFIXES:
            continue
        if name.startswith(HARVESTED):
            continue
        try:
            out.append((name, (ROOT / name).read_text(encoding="utf-8")))
        except (UnicodeDecodeError, OSError):
            continue
    return out


def test_no_tracked_file_carries_a_routable_ipv4_address():
    offenders = []
    for name, text in _tracked_text():
        for literal in _IPV4.findall(text):
            try:
                address = ipaddress.ip_address(literal)
            except ValueError:
                continue  # 999.1.2.3 and version strings are not addresses
            if address.is_global:
                offenders.append(f"{name}: a routable address")
    assert not offenders, (
        "tracked files name a real, routable host:\n  " + "\n  ".join(offenders)
        + f"\nUse {PLACEHOLDER_HOST} (TEST-NET-3) where a document needs one."
    )


def test_every_connection_string_user_is_a_placeholder():
    offenders = sorted({
        f"{name}: user of {len(user)} chars"
        for name, text in _tracked_text()
        for user in _DSN_USER.findall(text)
        if user not in PLACEHOLDER_USERS
    })
    assert not offenders, (
        "a connection string names what looks like a real database user:\n  "
        + "\n  ".join(offenders)
        + "\nUse `example_user`. A username is half a credential, and it is the "
        "half that does not rotate."
    )


def test_the_placeholder_is_what_the_remote_host_example_uses():
    """⚠ THE CONTROL. `test_reset_guards.py` needs a remote host to prove the
    guard refuses one. If the placeholder ever left it, the checks above would
    still pass while the guard lost its example."""
    source = (ROOT / "tests" / "test_reset_guards.py").read_text(encoding="utf-8")
    assert f'"{PLACEHOLDER_HOST}"' in source
    assert not ipaddress.ip_address(PLACEHOLDER_HOST).is_global
