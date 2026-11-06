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

## The one rule

Agents find threads and draft replies. **A person approves every reply and posts
it from their own account, with disclosure.** Nothing is posted automatically.
