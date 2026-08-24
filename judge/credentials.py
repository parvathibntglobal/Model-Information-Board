"""Generate the three sign-in variables, ready to paste into .env.

    python -m judge.credentials                       random password
    python -m judge.credentials --email me@x.dev      choose the address
    python -m judge.credentials --password "..."      choose the password

WHY A COMMAND RATHER THAN INSTRUCTIONS. A PBKDF2 hash is only checkable by
something using the same algorithm, iteration count and format. Told to
"generate a hash", a person reaches for `sha256sum`, gets a plausible-looking
64 hex characters, pastes it in, and sign-in fails with a wrong-password error
that is really a wrong-format error. This produces the hash with the same
function `login.verify_password` reads it with, so the two cannot drift.

IT PRINTS THE PASSWORD ONCE AND STORES ONLY THE HASH. Nothing recovers it
afterwards - that is the property being bought. Losing it means running this
again, which costs nothing.
"""
from __future__ import annotations

import argparse
import secrets

from judge.login import hash_password

#: Ambiguous glyphs removed. A password that has to be read off a screen and
#: typed by hand is a password where `l`/`1` and `O`/`0` cost real minutes.
_ALPHABET = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_password(length: int = 20) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default="demo@modelboard.dev")
    parser.add_argument("--password", default=None, help="omit for a random one")
    args = parser.parse_args()

    password = args.password or generate_password()

    print("\n  Paste into backend/.env  (gitignored - never commit it)\n")
    print(f"AUTH_EMAIL={args.email}")
    print(f"AUTH_PASSWORD_HASH={hash_password(password)}")
    print(f"SESSION_SECRET={secrets.token_urlsafe(48)}")
    print("\n  Sign in with\n")
    print(f"    email     {args.email}")
    print(f"    password  {password}")
    print(
        "\n  This is the only time the password is shown. Only the hash is stored,"
        "\n  so nothing here or in .env can recover it - run this again if it is lost.\n"
    )


if __name__ == "__main__":
    main()
