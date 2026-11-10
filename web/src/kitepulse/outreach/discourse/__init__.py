"""Kite Pulse outreach: the Discourse forum Finder.

Finds this week's topics on developer forums (Cursor, OpenAI, Google AI) where
people raise problems Kite Pulse solves, for a person to read and answer by hand.

    py -3.12 web/src/kitepulse/outreach/discourse/find.py
    py -3.12 web/src/kitepulse/outreach/discourse/find.py --forum forum.cursor.com
    py -3.12 web/src/kitepulse/outreach/discourse/find.py --phrase "usage limit"

    find.py      command line; writes var/outreach/*.jsonl and prints a list
    finder.py    list this week's topics -> match phrases -> filter
    client.py    GET-only calls to one forum, checked against its robots.txt
                 (the robots.txt handling is common/http.py)
    parse.py     a topic from the listing -> a Thread

Phrases are matched by `common/match.py`, shared with dev.to.
    config/      queries.yaml, communities.yaml (one entry per forum), pace.yaml

WHY NO SEARCH. Discourse's robots.txt disallows `/search` for every generic
bot (checked 2026-11-06 on forum.cursor.com and community.openai.com, and by
MIB on discuss.ai.google.dev, `contract/sources.yaml`). So the Finder reads
what robots.txt allows: the newest-created topic listing
(`/latest.json?order=created`, 30 topics a page), and matches phrases in code.
The client re-reads robots.txt on every run and refuses any path it disallows.

WHAT IS MATCHED. A topic's title, plus the listing's excerpt of its opening post
where the forum sends one (forum.cursor.com does; community.openai.com and
discuss.ai.google.dev sent none on 2026-11-06). Where there is no excerpt the
match is on the title alone, and the run says so per forum. Replies are not read.

THIS FOLDER ONLY READS. It holds no posting credential and calls no posting
endpoint; `tests/test_kp_outreach_guards.py` fails if a write request appears.
A person posts every reply from their own account, with disclosure. Imports
nothing from `collect/` except `collect.config` (for the User-Agent).
"""

SOURCE = "discourse"
