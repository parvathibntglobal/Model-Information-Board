# Kite Pulse — Outreach (outward marketing)

The outward marketing module: finding people who are already asking about
problems Kite Pulse solves, and answering them helpfully, with the answer
disclosed as coming from the Kite Pulse team.

**Status (2026-11-04): plan only.** Nothing here runs yet.

## What is here

| File | What it is |
|---|---|
| `docs/Outward Marketing Strategy.md` | The strategy: the disclosure rule, the agents, the rollout and the open questions |
| `docs/ARCHITECTURE.md` | The technical design: components, tables, the reply check, review screen, model use and cost, rollout, decisions needed |
| `hackernews/` | Phase 1 Finder for Hacker News (built 2026-11-06): searches, filters, writes `var/outreach/*.jsonl`. Reads only, no model. Run `py -3.12 web/src/kitepulse/outreach/hackernews/find.py`; details in its `__init__.py` |
| `discourse/` | Phase 1 Finder for Discourse forums: Cursor, OpenAI, Google AI (built 2026-11-06). Reads each forum's newest topics for the week (search is disallowed by robots.txt) and matches phrases in code. Run `py -3.12 web/src/kitepulse/outreach/discourse/find.py`; details in its `__init__.py` |
| `devto/` | Phase 1 Finder for dev.to (built 2026-11-06). Reads a week of articles in chosen tags (`config/tags.yaml`) and matches phrases in code. Run `py -3.12 web/src/kitepulse/outreach/devto/find.py`; details in its `__init__.py` |
| `github/` | Phase 1 Finder for GitHub Discussions (built 2026-11-06). Searches each phrase, quoted, across GitHub and confirms every hit in code. Needs `KP_GITHUB_TOKEN` in `.env` (Kite Pulse's own, not MIB's). Run `py -3.12 web/src/kitepulse/outreach/github/find.py`; details in its `__init__.py` |
| `reddit/` | Phase 1 Finder for Reddit (built 2026-11-10). Lists each subreddit in `config/communities.yaml` back 7 days through RapidAPI and matches phrases against titles (the API sends no post body). Uses MIB's `RAPIDAPI_KEY` and `REDDIT_PROVIDER`/`RAPIDAPI_HOST`, so it spends the board's RapidAPI quota. Run `py -3.12 web/src/kitepulse/outreach/reddit/find.py`; details in its `__init__.py` |
| `common/` | What every platform folder shares: the Thread record, the filters, the config loader, phrase matching, the robots.txt-obeying HTTP client, the database connection and the thread writer |
| `setup_db.py`, `migrations/` | Outreach's own Postgres database (`KP_OUTREACH_DATABASE_URL`, never MIB's). `py -3.12 web/src/kitepulse/outreach/setup_db.py` creates it and applies the migrations. Every Finder run then adds its new threads to `kp_outreach_thread` as well as writing its JSONL |

## The one rule

Agents find threads and draft replies. **A person approves every reply and posts
it from their own account, with disclosure.** Nothing is posted automatically.
