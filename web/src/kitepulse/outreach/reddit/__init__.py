"""Kite Pulse outreach: the Reddit Finder.

Finds this week's posts in chosen subreddits where people raise problems Kite
Pulse solves, for a person to read and answer by hand.

    py -3.12 web/src/kitepulse/outreach/reddit/find.py
    py -3.12 web/src/kitepulse/outreach/reddit/find.py --subreddit ClaudeCode
    py -3.12 web/src/kitepulse/outreach/reddit/find.py --phrase "usage limit"

    find.py      command line; writes var/outreach/*.jsonl and prints a list
    finder.py    list each subreddit's week -> match phrases -> filter
    client.py    GET-only calls to the RapidAPI service that fronts Reddit
    parse.py     a listing post -> a Thread
    config/      queries.yaml, communities.yaml (one entry per subreddit), pace.yaml

Phrases are matched by `common/match.py`, shared with Discourse and dev.to.

HOW IT REACHES REDDIT. Through RapidAPI (the `reddit34` provider), with the
same RAPIDAPI_KEY the Model Information Board's Reddit sweep uses. ONE
SUBSCRIPTION, so this Finder spends the board's monthly quota and shares its
per-minute limit (429 at the 32nd rapid call, measured by MIB 2026-08-14).
The client paces at 20 calls a minute to leave the board room. Decided
2026-11-10 by aloysiuspellissery; ARCHITECTURE.md had skipped Reddit on
2026-11-06 for exactly this shared key.

WHY NO SEARCH. Measured 2026-11-10, one phrase, `claude code usage limit`:
`/getSearchPosts` sort NEW returned 22 posts of which 1 held every word of the
phrase (Costco, OrcaSlicer, a referral-link sub); sort TOP with `time=week`
returned 22 of which 0 did (formula1, AITA). The search has no phrase
operator - MIB measured the same in `collect/adapters/reddit.py` - and
`time` is refused with any sort but TOP. So the Finder reads what it can bound:
each subreddit's newest posts (`/getPostsBySubreddit?sort=new`, 25 a page) back
to the age window, and matches phrases in code.

WHAT IS MATCHED: THE TITLE ONLY. Neither the listing nor the search result
carries `selftext` (checked 2026-11-10, r/ClaudeCode, 25 posts: no such key).
The run says so per subreddit. Replies are not read.

'DATA NOT FOUND' IS NOT ZERO POSTS. The provider answers HTTP 200 with
`success: false, data: "data not found"` both for a genuine empty and as a
transient decline (MIB measured a query returning 175 results, then this, then
25 posts on five retries; it happened again on the first listing call here,
2026-11-10, and one retry recovered it). The client retries twice and then
FAILS the subreddit, which the run reports; it never reads as "nothing there".

THIS FOLDER ONLY READS. It holds no Reddit login and calls no posting
endpoint; `tests/test_kp_outreach_guards.py` fails if a write request appears.
A person posts every reply from their own account, with disclosure.

Not reused from `collect/adapters/reddit.py`: importing it also imports MIB's
raw store and quota writer, and outreach imports nothing from `collect/`
except `collect.config` (guard test).

TERMS, OPEN. MIB's `reddit-via-rapidapi` ruling permits internal development
and testing. Outreach is marketing, which is a different use; Reddit's
commercial-use approval (ARCHITECTURE.md section 11, item 2) is still not
held. Recorded here so the gap is visible, not settled.
"""

SOURCE = "reddit"
