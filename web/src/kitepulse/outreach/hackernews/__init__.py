"""Kite Pulse outreach: the Hacker News Finder.

Finds recent Hacker News stories and comments where people ask about problems
Kite Pulse solves, and filters them, for a person to read and answer by hand.

    py -3.12 web/src/kitepulse/outreach/hackernews/find.py
    py -3.12 web/src/kitepulse/outreach/hackernews/find.py --problem claude-limits

    find.py      command line; writes var/outreach/*.jsonl and prints a list
    finder.py    search -> deduplicate -> filter
    client.py    GET-only calls to the Algolia HN Search API
    parse.py     an API hit -> a Thread
    thread.py    the Thread record, statuses, drop reasons
    filters.py   the code filters (no model)
    config.py    loads config/*.yaml; a missing key is an error, never a default
    config/      queries.yaml, communities.yaml, pace.yaml - edited by people

Design: `../docs/ARCHITECTURE.md`.

THIS FOLDER ONLY READS FROM HACKER NEWS. It holds no posting credential and
calls no posting endpoint; `tests/test_kp_outreach_hackernews.py` fails if a
write request appears in it. A person posts every reply from their own account,
with disclosure.

It shares nothing with the Model Information Board's evidence pipeline: it
never writes `document`, `claim` or `thread_context`, and imports nothing from
`collect/` except `collect.config` (for the identifying User-Agent). Not reused
from `collect/adapters/hackernews.py`, because importing that module also
imports MIB's document writer.

API: https://hn.algolia.com/api - free, no key, no published rate limit. We
wait one second between requests anyway.
"""

SOURCE = "hackernews"
