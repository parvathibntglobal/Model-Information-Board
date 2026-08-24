"""The two questions every report naming a write has to answer, asked mechanically.

    Which database did this touch, and is the code that touched it on origin?

Both were answered from memory for a fortnight and both went wrong in the same
report — one said "committed on main" while the shell sat on an unmerged branch.
A remembered check is a check that is right until somebody is busy, so this is a
command:

    python -m scripts.write_report --path collect/migrate.py --commit ee5b702

**It prints the DSN with the password removed and never anything else from
`.env`.** The point is to make the identifying half quotable in a report without
making the secret half quotable anywhere.

`--against` names the ref that counts as published, defaulting to `origin/main`.
It is compared as an ANCESTOR relation rather than by branch name, because
"my branch is called main" and "this commit is on origin/main" are different
claims and only the second one is the one a reader cares about.

Read-only: no database connection is opened, and `git fetch` is not run — a stale
`origin/main` would make a NO into a YES, so the age of the last fetch is printed
rather than silently corrected.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import urllib.parse
from pathlib import Path

ENV_FILE = Path(".env")


def git(*args: str) -> str:
    """Run git and return stripped stdout, or "" on any failure."""
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def on_ref(commitish: str, ref: str) -> bool:
    """Is `commitish` an ancestor of `ref`? The published-or-not question."""
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commitish, ref],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def env_value(key: str) -> str | None:
    """One key out of `.env`, without reading the file to anywhere else."""
    if not ENV_FILE.exists():
        return None
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{key}="):
            return stripped.split("=", 1)[1].strip()
    return None


def redacted_dsn() -> str:
    """The DSN with the password gone and everything identifying kept.

    Host, port, database and user identify which database a write landed in, and
    a report that omits them is unauditable. The password identifies nothing and
    is the one part that must never reach a report, a terminal or a commit.
    """
    raw = env_value("DATABASE_URL")
    if not raw:
        return "DATABASE_URL not set"
    try:
        parsed = urllib.parse.urlparse(raw)
    except ValueError:
        return "DATABASE_URL is set and did not parse"
    if not parsed.hostname:
        return "DATABASE_URL is set and carries no host"
    user = f"{parsed.username}@" if parsed.username else ""
    port = f":{parsed.port}" if parsed.port else ""
    database = (parsed.path or "").lstrip("/")
    return f"{parsed.scheme}://{user}{parsed.hostname}{port}/{database}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", action="append", default=[],
                        help="a file whose publication state to report; repeatable")
    parser.add_argument("--commit", action="append", default=[],
                        help="a commit whose publication state to report; repeatable")
    parser.add_argument("--against", default="origin/main",
                        help="the ref that counts as published (default origin/main)")
    args = parser.parse_args(argv)

    ref = args.against
    head = git("rev-parse", "--short", "HEAD")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")

    print("WRITE REPORT")
    print(f"  DSN            {redacted_dsn()}")
    print(f"  ENVIRONMENT    {env_value('ENVIRONMENT') or '(unset)'}")
    print(f"  branch         {branch}  HEAD {head}")

    if not git("rev-parse", "--verify", ref):
        print(f"  {ref}    NOT PRESENT — cannot answer the on-origin question")
        return 2

    ahead_behind = git("rev-list", "--left-right", "--count", f"{ref}...HEAD")
    behind, ahead = (ahead_behind.split() + ["?", "?"])[:2]
    verdict = "YES" if on_ref("HEAD", ref) else "NO"
    print(f"  HEAD on {ref}?  {verdict}   (ahead {ahead}, behind {behind})")
    print(f"  {ref}    {git('rev-parse', '--short', ref)}"
          f"   last fetched {git('log', '-1', '--format=%cr', 'FETCH_HEAD') or 'unknown'}")

    # A path is reported by whether its LAST COMMIT is published, not by whether
    # the file exists on the ref: an edited file that exists on origin reads as
    # published when the edit is not.
    for path in args.path:
        last = git("log", "-1", "--format=%h", "--", path)
        if not last:
            print(f"  path  {path:<44} NO COMMIT TOUCHES IT")
            continue
        state = "on " + ref if on_ref(last, ref) else f"NOT on {ref}"
        dirty = git("status", "--porcelain", "--", path)
        print(f"  path  {path:<44} {state} (last {last})"
              f"{'  UNCOMMITTED CHANGES' if dirty else ''}")

    for commit in args.commit:
        full = git("rev-parse", "--short", commit)
        if not full:
            print(f"  commit {commit:<43} DOES NOT EXIST IN THIS REPOSITORY")
            continue
        state = "on " + ref if on_ref(commit, ref) else f"NOT on {ref}"
        subject = git("log", "-1", "--format=%s", commit)
        print(f"  commit {full:<43} {state}  {subject[:48]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
