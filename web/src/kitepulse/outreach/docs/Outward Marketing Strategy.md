# Kite Pulse — Outward Marketing Plan

*Prepared 4 November 2026. This is a proposal; nothing has been built yet.*

---

## In one paragraph

Developers and engineering managers are already asking online about problems
Kite Pulse solves: hitting Claude Code limits, tracking AI cost per developer,
seeing where agents get stuck. We propose a small set of AI agents that
**find these conversations every day and draft a helpful reply** linking to the
right Kite Pulse article. **A team member reviews each draft and posts it
themselves**, saying openly that they work on Kite Pulse.

---

## The ground rule: helpful first, always disclosed

Every reply must:

1. **Answer the question properly**, as if Kite Pulse did not exist.
2. **Mention Kite Pulse once at most**, and only when it really solves the
   person's problem.
3. **Say who we are**, e.g. *"Disclosure: I work on Kite Pulse."*
4. **Be posted by a real person** from their own account. Agents never post
   anything themselves.

**Why:** Reddit, Hacker News and Stack Overflow, and most developer
communities, ban hidden self-promotion. Accounts that do it get banned, and the
product gets a bad name in exactly the communities we want to reach. Advertising
without disclosure also breaks consumer-protection rules (FTC in the US, ASCI in
India).

---

## How it works

```
 1. FIND            2. SHORTLIST         3. DRAFT            4. REVIEW & POST      5. MEASURE
 Search forums  ──► Keep the best   ──►  AI writes a    ──►  A team member    ──►  Count clicks and
 for problems       threads              helpful reply       edits and posts       replies
```

---

## The agents

| # | Agent | What it does | AI model |
|---|---|---|---|
| 1 | **Finder** | Every few hours, searches Reddit, Hacker News, dev.to, GitHub Discussions, developer forums and X for phrases like *"hit my Claude limit"*, *"AI cost per developer"* or *"Claude Code stuck"*. Uses each site's official API only. | None (plain code) |
| 2 | **Shortlister** | Keeps threads that are recent, still open, in communities that allow vendor replies, and not already answered by us. Ranks them by how closely they match a problem Kite Pulse solves, and picks the Kite Pulse article that best answers each one. | **DeepSeek V4 Flash** to judge relevance |
| 3 | **Reply Writer** | Drafts a reply that follows the ground rule above. Before a person sees the draft, an automatic check rejects any reply that has no disclosure line, mentions the product more than once, or makes a claim not on our approved list. | **DeepSeek V4 Flash** |
| 4 | **Review screen** | An admin page that shows the thread and the draft, with an edit box and *Approve* / *Skip* buttons. The reviewer posts approved replies by hand. | — (a person decides) |
| 5 | **Article Sharer** | Turns published Kite Pulse articles into posts for dev.to, Hashnode and Medium (each linking back to the original), "Show HN" drafts for real releases, and pitches to developer newsletters. Everything goes through the review screen. | **DeepSeek V4 Flash** |
| 6 | **Reporter** | Weekly summary: replies posted, clicks, replies received, and the problems people raise most often. | None (plain code) |

### Why these models: keeping cost low

- **One budget model for every AI step: DeepSeek V4 Flash.** It is one of the
  lowest-cost capable models available, and our team already uses it to read
  developer posts on the Model Information Board. As a reference point, reading
  one forum thread with it cost about **$0.002**. That figure comes from 3 calls
  on one thread, measured on 19 August 2026, for a similar but longer reading
  task.
- **Low volume keeps the bill small.** Only the shortlisted threads get a
  drafted reply (a few a day). Most of the work, searching and counting, is
  plain code and costs nothing in AI fees.
- **A person checks every draft**, so a budget model's occasional weak draft is
  fixed or skipped before anyone sees it.
- **Upgrade only if needed.** If reviewers find they rewrite most drafts, switch
  the Reply Writer alone to **Claude Haiku 5.5**, Anthropic's low-cost model,
  and compare the two for a week before deciding.
- All calls go through **OpenRouter**, the service the team already uses, so
  every call is logged and costed in the existing spending report, and the
  model can be changed without changing the agents.

---

## Rollout

| Phase | What runs | What the team does |
|---|---|---|
| **1** | Finder + Shortlister send a daily list of threads | Reply by hand; learn which communities and topics work |
| **2** | Reply Writer + review screen added | Edit, approve and post drafts |
| **3** | Article Sharer + Reporter added | Approve shared posts; review weekly results |

**Pace:** a few good replies a day, not dozens. Most of each account's activity
should be ordinary participation in the community, not links to Kite Pulse.
