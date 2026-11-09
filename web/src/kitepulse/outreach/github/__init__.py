"""Phase 1 Finder for GitHub Discussions (ARCHITECTURE.md 5.1). Reads only.

HOW IT SEARCHES. GitHub's GraphQL `search(type: DISCUSSION)`, one query per
phrase, across all of GitHub:

    "<phrase>" in:title,body created:>=<date> sort:created-desc

The phrase is QUOTED. Measured 2026-11-06, discussions created since
2026-10-30: unquoted `usage limit` returned 268, quoted 73; unquoted words
match anywhere in long bodies ("Welcome! Tell us where your agent gets
stuck"). Every hit is then checked in code with the same matcher the other
sources use (`common/match.py`) against its title and body; a hit GitHub
returned that the matcher does not confirm is counted, not kept.

PAGES OF 25. Asking for `bodyText` on 100 discussions at once returned
`RESOURCE_LIMITS_EXCEEDED` errors beside partial data (measured 2026-11-06).
Any response with `errors` fails the phrase: partial data is never read as the
answer. A 502 from search was also seen that day; it is retried once.

THE TOKEN IS KITE PULSE'S OWN: `KP_GITHUB_TOKEN`, never MIB's `GITHUB_TOKEN`
and never a fallback to it. GraphQL refuses anonymous requests. A
fine-grained token with "Public repositories (read-only)" and no permissions
is enough. NOTE: GitHub counts a personal token's rate limit per ACCOUNT, so a
second token on the same account as MIB's shares MIB's 5,000 points an hour.
A run costs one point per page (about 15 for the shipped phrases).

WHAT THE HITS LOOKED LIKE (2026-11-06). Mostly tool maintainers announcing or
discussing features in their own repos, not people asking for help. Those are
kept and flagged `posted_by_repo_owner`, so a reviewer can skip them (a flag,
not a drop: the rule has not been measured, CLAUDE.md rule 8).

READ-ONLY. GraphQL takes reads as POSTs, so this is the one outreach folder
with a POST; `client.py` refuses any document that does not start with
`query`, and `tests/test_kp_outreach_guards.py` allows the POST in that file
only.
"""

SOURCE = "github"
