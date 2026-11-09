"""Kite Pulse outreach: the dev.to Finder.

Finds this week's dev.to articles, in chosen tags, that touch problems Kite
Pulse solves, for a person to read and answer by hand.

    py -3.12 web/src/kitepulse/outreach/devto/find.py
    py -3.12 web/src/kitepulse/outreach/devto/find.py --tag claudecode
    py -3.12 web/src/kitepulse/outreach/devto/find.py --phrase "usage limit"

    find.py      command line; writes var/outreach/*.jsonl and prints a list
    finder.py    list each tag's week -> deduplicate -> match phrases -> filter
    client.py    GET-only calls to the Forem API, checked against robots.txt
    parse.py     an article from the listing -> a Thread
    config/      queries.yaml, tags.yaml, communities.yaml, pace.yaml

HOW THE WEEK IS READ, measured 2026-11-06. dev.to's robots.txt disallows
`/search?q=*`, and its API has no text search, so phrases are matched in code
(`common/match.py`) against each article's title and description.

The listing is `/api/articles?tag=<tag>&top=7&per_page=1000`: every article in
the tag published in the last 7 days, most-reacted first, zero-reaction ones
included. Checked against the full newest-first feed (2,000 articles, 7.6
hours): it returned 19 of 19 `claude`, 12 of 12 `claudecode` and, with page 2,
61 of 61 `agents` articles. A tag fills a page at 1,000 and is read to the next
page until a page comes back short; `productivity` read one page only missed 159
of 200, which is why the paging is not optional.

NOT `/api/articles/latest?tag=`: with a tag it returns the same popularity
order, not newest-first (44 date inversions in 100), so stopping at the first
old article would silently miss the rest of the week.

The client checks that every article it gets carries the tag it asked for and
falls in the window. If dev.to ever ignores either filter, the run fails rather
than returning a list that looks considered (CLAUDE.md rule 6).

THIS FOLDER ONLY READS. It holds no API key and no posting credential;
`tests/test_kp_outreach_guards.py` fails if a write request appears. A person
posts every comment from their own account, with disclosure.
"""

SOURCE = "devto"
