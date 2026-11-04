[Kite Pulse](#top)

[Basics](#basics) [Features](#features) [Since 12 Oct](#since) [Big picture](#picture) [3 programs](#programs) [Data journey](#journey) [Layers](#layers) [Agents](#agents) [Structure](#structure) [Numbers](#numbers) [Console](#console) [Run it](#run) [Rules](#rules) [Glossary](#glossary)

Product field guide · Kite Pulse 0.1.0 · as built on 28 Oct 2026

# A fitness tracker for AI-assisted coding.

Developers now spend their day directing AI coding agents like Claude Code and Cursor. Kite Pulse quietly reads those sessions, turns them into plain facts, shows every agent at work in a live 3D office, and gives developers, managers and administrators each the view they need. An optional company Brain answers questions with only what the asker may see.

**3**programs to run **11**AI tools it reads **69**console pages **419**API routes **129**MCP tools for agents **7**connectors **145**database tables

### It collects

A small program on each developer's computer finds the AI-coding session files, removes secrets, encrypts them and uploads them.

### It measures

A server turns the raw conversations into facts: session length, tools, files, languages, commits, tokens, stuck stretches, plan usage.

### It shows

A web console with a live 3D office as its home page, personal scorecards, team and project views, AI spend and alerts, each by access level.

### It connects

Agents ask it questions over an API or MCP, Jira and six other systems feed it, Slack and email carry its alerts, and SCIM keeps its accounts in step.

The idea

## What problem does it solve?

Companies spend a lot on AI coding tools but can't see what actually happens inside a coding session. Most measuring tools only look at the finished result. Kite Pulse looks at the work itself.

### What other tools look at

- Git commits and pull requests (the end result)
- Surveys (what people remember or believe)
- Ticket counts in Jira

### What Kite Pulse looks at

- The conversation between the developer and the AI
- Retries, dead ends, stuck stretches and sub-agents
- Active time, tools used, files touched, tokens, plan limits

"Historian, not critic."

The main rule of the product. It records what happened ("47 minutes went into three approaches that were dropped") and never grades a person. Team pages built on AI labels show pooled figures only, never a name or a ranking, and a figure that would describe too few people is withheld.

"The developer is the manager of the AI."

The AI types most of the code now. So the product looks at how well a person directs the AI, checks its work, and corrects it. In the Office the figure at each desk is the person's agent, and it moves only for what that agent really does.

**Where the product is today.** Phase 1 (monitoring and insights) is live. Everything a new install shows needs no AI key: facts, the Office, teams, projects, usage, alerts, the knowledge and session views. Three AI features are built in and off until an admin switches them on with a key and a budget: AI labelling of work (the label-based pages), the Enterprise Brain, and the chat assistant. The deeper analysis layers 2 to 5 stay built and off.

The product

## What Kite Pulse offers, by who you are

Every feature below is in the console menu or the collector today (branch `Sonia00_newfeature`, 28 Oct 2026). New marks what arrived since the first edition of this guide on 12 Oct. Off by default marks a feature an admin switches on. Access levels decide which pages appear; the detailed access table is under [Console](#console).

### Developers

Every account · 3 menu entries · own data only

A developer sees the Office, one Insights entry (Needs attention) and the Me section. Everything in Me is about their own work and nobody else's. The pages fill in on their own once the collector on their computer is set up.

#### Your agent, live Home › The Office

**Your desk in the 3D office**New

The figure at your desk is your AI agent. It types, reads or watches a command run as its latest step does, turns round and raises a hand when it waits for you, walks to the lounge when you are away or idle for 15 minutes, and walks out when you go offline.

/office · list view for keyboard and screen readers

**Sub-agents as light threads**New

Each working sub-agent is a badge tied to your screen by a thread of light. A click opens its holo card (title, step, file, model, elapsed). From the fourth onwards they stack and fan out on click.

Claude Code sub-agents, matched to their spawn call

**Waiting for you · Needs your approval**New

After two quiet minutes the agent shows "Waiting for you". With Claude Code's notification hook switched on, the Office says exactly when Claude Code asks for an approval. You can opt out of the hook.

Settings › Retention › Kite Pulse app reads · client 0.4.4

**Parcels and pages**New

A small parcel leaves your desk on a git push. A page flies into The Brain when your project's notes (CLAUDE.md, AGENTS.md, READMEs) change.

In scope only; never message text

**Plan headroom on your name tag**New

From 80 % of a Claude plan window a marker appears on your tag ("Weekly 85 %", "Limit · back 2:30 PM"). At the limit your agent rests until the window resets.

Same reading as Team AI Usage › Plan headroom

**Ask a teammate's agent**NewBrain on

Ask what a colleague's agent worked on in the last 14 days (project, branch, state, file names, stuck stretches) on projects you can also see. Never prompt text. The owner sees who asked and can pause it.

Desk card › Ask \<name>'s agent · Privacy › Who asked my agent

#### Your own numbers, private to you Me

**Workspace**

One question: is my work being collected? Status line, six stage tiles from Detected to Processed, upload problems, your projects, plan headroom and quick links. Refreshes every minute.

/me/overview · "!" badge when your sync needs you

**My Day**NewAI labelling

Your own day read off the labels on your work: what you worked on, started, left open, got stuck on, learned or decided. No cost, no tool usage.

/me/day

**Scorecard & Insights**

Your working-style archetype, productivity and quality-check signals, a "Top 3 to act on" list, every finding explained with what to try, coaching suggestions and private prompting-style stats.

/me · Overview and Insights tabs

**My Activity and My Sessions**

Sessions, active time, messages, commits, code changes, daily chart, tools used most, and a searchable list of every session with its tool, project, length and status.

/me/activity · /me/sessions

**What the agent did**New

A session's timeline step by step: which tool ran, on which file, how it went, with pauses, tasks and stuck stretches marked. Structure only, never message text. Routine results fold away.

Session page · also from your desk card

**Needs attention**New

Everything waiting for you in one list. For a developer that is their own data collection; managers and admins see more groups.

/insights/inbox

#### Your projects Me › My Projects

**Onboarding wizard**

A one-time step after the first sign-in: review the projects the collector found (folder names, paths and git remotes only), fix, add, remove, then Finish & start syncing. Nothing syncs before that.

Opens on its own · approval by an admin when required

**My Projects**

Every project linked to you with its folder, activity, sessions and contributors. Confirm, change folder, split, remove or add. Developers send a request; managers and admins change at once.

/me/projects

**Pending Requests and Project Detection**

Track your change requests (pending, needs info, approved, rejected) and answer a request for more information. Project Detection shows your setup status and what was found on your machine.

/me/requests · /me/detection

#### Your privacy and your account Me

**Privacy: what we collect about you**

Every data point the system records about your work, whether it is on, and who can see it (you, your manager, admins). New reads such as the Office presence, sub-agents, plan headroom and the Brain each have their own entry.

/me/transparency

**Account**

Profile, password (changing it signs out other devices), notification switches, and the agent API keys issued to you with their request log.

/me/settings

**Notices meant for you**New

"Plan limit reached" when a window of your Claude plan is used up, and "AI agent stuck" after 30 minutes on one problem. Sent to you and your manager, in the console only.

Bell · Settings › Notifications routes them

**Your data, exported or erased**

An admin can export everything held about a person, and erase an account. Every table with personal data has an erase rule, including the newer Brain, teammate-ask and notice tables.

Settings › Accounts & Roles › Actions

**Help and search**

Help / Glossary from the ? in the top bar for every role. Search (Ctrl K) finds a page, a developer, a project, a team, an alert or a session by number, only among what you may open.

Top bar

**Light or dark console**

A sun / moon switch in the top bar; the Office keeps its own light and dark looks (dark is the office in the evening).

Remembered in your browser

#### Work from your editor instead of a dashboard Agent API · MCP · The Brain

**Ask Kite Pulse from Claude Code, Cursor or VS Code**New

With an agent key (`kpk_…`) your AI tool calls Kite Pulse over the API or the MCP endpoint: 115 read tools plus 3 chat tools, and 11 write tools where the key's scope allows. Every call is logged and scoped to what the key's owner may see.

\<API base>/mcp · guide served at /guide

**Writes with a dry run**New

An agent may create or change teams, Brain documents and agents, project approvals, accounts and knowledge records when its key carries that scope. `dry_run` shows what would change and saves nothing. Every write is audited as "via key".

Scopes set when the admin issues the key

**Ask the Brain**NewBrain on + AI key

Plain-language questions about people, teams, projects, decisions and connected records. The server filters everything you may not read before the model sees it; answers list their sources; refusals say why.

Office › Brain tab · /brain · MCP brain_search

#### The collector on your computer Kite Pulse app 0.4.4

**Installs without admin rights**New

The installer checks the server and your code first, runs per user (no UAC on Windows), sets a logon trigger and a 5-minute timer, and ships its own uninstaller.

install.bat / install.ps1 · macOS launchd

**Tray icon that tells the truth**New

Green connected, blue setup or approval pending, yellow retrying or manifest not delivered, orange stalled, red code refused. Menu: Finish setup, Open dashboard, View log, Re-enter code, Run diagnostics, Restart.

Windows and macOS

**Doctor and verify**New

A diagnostics command (also a tray entry) and a verify script that say what is wrong in plain words: server unreachable, code refused, onboarding pending, nothing to upload yet.

kite-pulse-doctor · \_scripts/verify_client.py

**Secrets out, then encrypted**

Key and auth files are skipped, passwords and tokens scrubbed on your machine, every piece encrypted before upload, and the server scans again and rejects anything that still looks like a secret.

shared/client_report_redaction · server secret scanner

**Updates over the air**

The watchdog keeps the collector running and swaps in new versions the server releases, with a version check that refuses a mismatched build.

OTA-RELEASE.md

**Each extra read has a switch**New

Plan usage, agents' memory files, the skills scan, request timing, the status line, branch names and the waiting-for-you hook each ship off and are switched on by an admin. You can see each one on your Privacy page.

docs/CLIENT-DATA-ACCESS.md lists every read

### Managers

Own reporting line · 6 menu entries

A manager sees Home, Insights, Developers, Projects, AI Usage and Me, always for the people who report to them. Admins can grant more pages per role. Pages built on AI labels show pooled team figures and never a person.

#### How is it going? Insights

**Summary**New

One page before the detail: AI adoption, delivery, quality, friction (top recurring causes of the last 4 weeks), estimated cost at list price and system health, each linking to its page.

/insights/summary

**Needs attention**New

Critical alerts, approvals, failing uploads, developers to follow up, failed jobs, unchecked leaked credentials. Each count equals the badge on that page's menu entry.

/insights/inbox

**Activity Overview**New

When and on what the work happened: a day-by-hour heatmap, time per project, sessions per tool, session lengths, AI models used, most-edited files, for the scope you pick.

/insights/activity

**Trends**

Activity, sessions or cost over time, most-used tools and languages, and the label-based measures week by week for the organisation, a team or a project.

/org/trends

**Reports, scheduled or on demand**

Productivity figures and the verification signal for a period as CSV or PDF, scheduled by email. A Plan usage tab shows one month of Claude plan usage per developer and account, exportable to Excel.

/org/reports · every download audited

**Organisation Overview**

Active people, hours, sessions and commits with a daily chart, projects and people for the period, and closed sections for lines of code, project health, quality checks, work rhythm, tools and platform health.

/company · admins by default, can be granted

#### Where the team loses time Insights · built on AI labels · never names, never rankings

**Blocker Board**AI labelling

Over 28 days, each recurring cause that slowed the team with its counts and a suggested action, for the organisation, a team or a project. Session links for admins only.

/org/blockers

**Team Review**AI labelling

One declared team, one week: the middle value and middle range of each measure and the mix of work. A figure with too few people behind it is left out, with the reason.

/org/team-review

**Workflows & Pain Points**New

Common shapes of work, repeated prompts and commands, inefficient patterns, the longest sessions, hot files, being stuck week by week, and quality. Prompt text only for admins and for a developer's own work.

/insights/workflows

**AI Collaboration**AI labelling

Month by month per team: corrections of the AI and context given again per 100 messages, AI changes checked, AI file changes kept, who led the work. Pooled over a group's month.

/company/ai-collaboration

**Work Problems**

Plain-language problems found in sessions (failed actions, getting stuck, work left for later), a "who to look at first" list, finding cards with suggested actions, and the raw signals. No AI needed.

/company/errors

**Session Graph**New

Sessions from the last 90 days joined by how alike they look (words, tools, shape), coloured by community. Counting and statistics on your own server, no AI model.

/insights/knowledge/sessions · rebuilt nightly

#### People Developers

**Team Overview**

Today, live: coding now, online now, active time with the session count, people who need attention and why, and an attention strip for failed jobs, outdated apps, upload problems and backlog.

/org · badge counts the people you can act on

**All Developers and the person page**

A searchable list with access level, job role, manager by name, status and last activity. A person's page has overview, insights, activity, AI usage, projects and sessions. Export to Excel.

/org/developers

**Agents right now · Agents in parallel**New

How many of a person's agents work at this moment (main sessions and their sub-agents), which wait for them, and for any past day one lane per agent with the most at once. Admins and the person themselves.

Person page › top and Activity tab

**Collaboration**

Which teammates work on the same projects: a card per project with its contributors and their sessions.

/org/collaboration

**Leave & On-Call**

Record leave, holidays and on-call duty so a quiet week is not read as lost interest. Managers record for their own people; organisation-wide holidays are admin-only.

/org/leave

**Teams by function and by project**New

Function teams (Accounts, Development, …) are declared by hand. Project teams are suggested from who worked on the same projects in the last 30 days and created in one click; a person can be in several. The Office, Team Review and AI Collaboration follow them.

/admin/declared/teams · admins by default

#### Projects and the decisions around them Projects

**All Projects**

Every project found on the team's computers with review state, folder, confidence, activity, sessions, AI tokens, developers and last session. Review, restore, add, merge, split, move, remove or delete data.

/org/projects

**Project notes**New

On a project's page: the CLAUDE.md, AGENTS.md, READMEs and decision records its agents work from, with versions. Opening one shows its text (secrets removed) and what changed since the version before.

Project page · needs the memory-files read switched on

**Project Approvals and Onboarding Approvals**

Decide requests to add, remove, move or split a project before they change reports, and approve a new person's first project list before any data syncs. Approve, ask for more, or reject with a note.

/org/project-approvals · /org/onboarding-approvals

**Request History**

A read-only history of every project change request with the reviewer's note.

/org/project-requests

**Tidy up: duplicates, mapping, removed**

Likely duplicate projects and split suggestions with confidence, how folders map to the project list, and where disabled, pending-purge and purged projects went. Nothing changes until you confirm.

/org/duplicate-detection · /org/project-mapping · /org/removed-projects

**Jira issues on the project**NewConnector

With a Jira connection mapped to the project, its issues are visible to everyone who can see the project, and in the Brain. Issues with a Jira security level are never kept.

Settings › Connectors (admin)

#### AI spend, plans and outside agents AI Usage

**Team AI Usage**

Tokens and cache efficiency per person, tool, model and project, trends, and a Plan headroom tab showing who is close to a Claude plan limit. A pace line gives the last 14 days and where they lead in the next 30, and flags a day at twice the usual.

/org/usage · one developer's money is admin-only

**Tool Accounts**

Seat and licence questions: how many distinct logged-in accounts each AI tool is used under, logins shared by several people, plan per account.

/org/tool-accounts · admins by default

**Agent Activity**New

Every request an outside agent made with a key held by your people: when, whose key, what was asked, outcome, rows, speed, AI cost. Export to CSV.

/org/agent-logs · "Off" tag while the Agent API is off

**AI Budgets alerts**New

A monthly budget per team or project (never a person) in tokens or notional dollars raises an alert at 80 % and at 100 %, in the console and on Slack if alerts go there.

Set under Settings › AI Budgets

**Headroom view in the Office**New

The Office's Headroom board lists people in Team AI Usage's attention order only, and the whole-office counts show how many are near or at a limit. No other ranking of people exists anywhere.

Office › Headroom

**Plan usage history**New

Weekly peaks, weeks at 80 % or at the limit, 5-hour windows at the limit and per-model peaks per developer and Claude account, kept 365 days with 25 months of monthly summaries.

Reports › Plan usage

#### The Office for a manager Home

**Detail for your people, presence for everyone**

For your reporting line: the project on the monitor, what the agent does right now, syncing, unfinished setup, stuck AI, an Update badge. For colleagues outside your scope: name, team, tool and presence only.

Visibility rule D7

**Tasks, Activity and Office panel**New

Task status for the agents you may see (All, In progress, Stuck, Waiting, Paused, Failed, Done), a live feed of sessions, commits, stuck stretches and approvals, and the room's counts, notes, connectors and skills. A desk click adds the person as a tab.

One right-hand panel · » folds it away

**Project-team lens and suggested teams**New

Narrow the office to one project team's people with their live counts. Team editors see a "suggested teams" pill in the strip with one-click Create.

Filters over the office

**Map and List views**New

The company map draws people, teams and projects as one connected picture; the List shows the same information for keyboard users and narrow screens.

View switch · Full screen for a wall

**Governance for department leads**NewBrain on

A manager who leads a department reviews its members, holdings, agents and who read its items through the Brain, by name and never ranked.

Brain › Governance

**Notices about your people**New

"Plan limit reached" and "AI agent stuck" reach the person and their manager in the console; the bell groups what you can act on.

Bell · Needs attention

### Administrators

Whole organisation · 8 menu entries

An admin sees everything a manager sees for the whole organisation, plus Operations (is data arriving, is the server healthy) and Settings (how Kite Pulse behaves). Admin-only pages that name people across the host, such as Server Storage and Configuration, cannot be granted to other roles.

#### Setting the organisation up Settings › Setup checklist · Access · Organisation

**Setup checklist**New

The steps that make Kite Pulse useful after install, each with done or not and a link: teams, label lists, AI budget, insight rules, email, retention, agent keys.

/insights/setup

**Accounts & Roles**

Create accounts, set access level, job role and manager (picked by name), reset passwords, delegate user management, show or regenerate a person's client code, export their data, revoke or anonymise.

/admin/accounts · the client code shows once

**Login & Registration**

Admin-created users, domain-based self-registration (code emailed after confirmation) or open registration with approval. Warns when email is not configured.

/admin/settings/registration

**SCIM 2.0 user sync**New

Entra ID or Okta create, update and deactivate users through a bearer token made on Login & Registration. It never sets roles or managers, never touches admins, and reactivates only what it deactivated.

/scim/v2 · groups later

**Roles & Permissions**

Role by role, one switch per action over 122 resources grouped like the menu, and custom roles such as "Auditor". Switches apply to signed-in people at once. Preview as Admin, Manager or Developer from the top bar.

/admin/permissions

**Organisation Name**New

The name on the Office's reception wall and the Brain's card: typed here, else the Claude Code organisation most people are signed in to, else the product name.

/admin/settings/organisation

**Hourly Rates & Seat Prices**

Dated hourly rates per role level and seat prices per tool plan, each change a new dated version. Rates belong to role levels, never to people.

/admin/declared/rates

**AI Budgets**New

One monthly budget per team or project in tokens or notional US dollars, with what was used this month, a bar and a status. Unpriced tokens are reported, never counted as $0.

/admin/declared/budgets

**Teams**New

Function teams and project teams, members with dates, archive with an end date, history by past date, suggestions above the list.

Developers › Teams

#### What is collected and how long it is kept Settings › Collection Settings

**Tools**

Per AI tool: session sync, token consumption, generation rate (Claude Code) and account identification, plus the minimum app version. Apps pick the change up at their next check-in.

/admin/settings/tools

**Detection Rules**

When a repeated failure counts as a pattern, cut-offs for simple and complex work, whether projects need confirming, whether a new person's projects need approval (on by default) and the deletion grace period (7 days).

/admin/settings/detection

**Retention**

How long conversation text (90 days), summaries and the Audit Log (365 days) are kept, a report-only schedule, and plan usage history (365 days).

/admin/settings/retention

**Kite Pulse app reads, each with a switch**New

Plan usage, agents' memory files, the skills scan, request timing, the status line, branch names, Copilot plan, the waiting-for-you hook. Each ships off, has a client version floor, and shows on every developer's Privacy page.

Retention › Kite Pulse app reads

**Nothing uploaded before approval**

A new developer's first project list waits for an approver while admin approval is on; the collector shows "Onboarding pending" until then.

Projects › Onboarding Approvals

**Erase and export rules per table**

Every table holding personal data has an erase rule run from Accounts & Roles, and a data-subject export stays complete even where a page hides a figure.

docs/plan/RETENTION-AND-ERASURE-DESIGN.md

#### Is it working? Operations

**Data Collection**

Person by person: is each app finding and sending its data? Cards for reporting, setup unfinished, files waiting, uploads failing, projects waiting for analysis, and a table with last-seen times.

/company/ops/collection · badge = failing developers

**Processing**

The work queue that turns sessions into insights: figures, failed jobs, jobs by type, the queue, Resume after a credit pause, re-run failed jobs.

/company/ops/processing

**Machines**

Every computer running the app: up to date, outdated or unknown, owner, version, last check-in and upload, and its client log.

/company/ops/fleet

**Agent Setup**New

Which Claude Code skills, commands, agents, MCP servers and plugins are installed across the team's machines, how many people have each, how many sessions loaded it in 30 days, versions.

/company/ops/agent-assets · needs the skills scan on

**Infrastructure and Alerts**

Eight status tiles (processing, storage, database, host, ingest, security, email, fleet), open alerts with acknowledge / in progress / resolved, free disk, uploads waiting. Alerts never clear by themselves.

/company/ops/infrastructure · /company/ops/alerts

**Server Storage**

How much disk Kite Pulse uses and on what, what could be cleaned up, free space per disk, storage settings with secrets shown only as set or not set. Rescan every 5 minutes at most.

/company/ops/storage · admin-only, not grantable

**Maintenance**

Clean-up jobs by hand that fix how sessions group into projects, each with dry run, apply and a last-run record.

/admin/maintenance

**Configuration**

A read-only sheet of what this installation runs with: profile, server, database, storage, email, access, retention, features, tools, collectors. Secrets only as set or missing.

/admin/configuration · admin-only, not grantable

**Notifications routing**

Who is told about what and how: one routing grid per event (console, email, recipients, extra addresses), channels, delivery history with retry, advanced thresholds, a test email.

/admin/settings/alerts

#### Security and audit Settings › Security & Audit · Access

**Leaked Credentials**

Passwords, keys and tokens spotted inside people's AI chats, always partly hidden, with type, projects, people, tools and first / last seen. Mark each Rotated or False positive.

/admin/security/leaked-credentials

**Audit Log**

A permanent add-only record of sensitive actions and lookups: exports, key issues, permission changes, knowledge reads, Brain writes, connector changes, refused requests. Passwords and codes never appear.

/admin/audit

**Agent API Keys**New

Issue a key per person with a name, what it may read, write scopes, an expiry up to 365 days and optional limits; copy it once; rotate, revoke, export. A usage tab, a request log and a place to try a question.

/admin/api-keys · writes need an unlimited key

**Encrypted end to end**

Fernet encryption of every uploaded piece, bcrypt passwords, JWT logins, connector credentials and Slack webhooks wrapped with the server's master key and never shown again.

shared/crypto · KITE_PULSE_MASTER_KEY

**Permissions enforced on the server**New

Every console, agent and Brain read is filtered by the backend before data reaches a page or a model. Refused console requests leave an `access.denied` trace. A cross-department leakage test suite is a release gate.

tests/test_brain_leakage_gate.py

**Read-only off the live server**New

A non-live install cannot write to live storage, email or a remote database, so a copy of live data can be studied locally without risk.

KITE_PULSE_ENV guards

#### Optional AI, each behind its own switch, key and budget Settings › AI Labelling · The Brain

**Classification (AI labelling)**Off by default

One page with Overview, Settings (switch, model, confidence, monthly cap), Label Lists (about 70 questions the AI answers about a piece of work, approved before use) and Review Labels (a checking queue to confirm or correct). Feeds My Day, Trends, Blocker Board, Team Review and AI Collaboration.

/admin/classification · "JEV" on some screens

**AI Call Log**

Every AI call Kite Pulse made: request, response, reasoning, tokens and cost, by day, next to the job queue. Every read is audited.

/admin/classification/call-log

**The Enterprise Brain**NewOff by default

Switch, budget (20 USD default), model and retention in one settings panel. Declared profiles (role, department, manager, skills, projects), project context, documents per company / department / project, built-in and department agents, a graph of how everything connects, governance and compliance views.

/brain · Office › Brain tab · settings in Governance

**Brain graph**New

Departments, people, projects, teams, agents, documents and AI tools as one radial picture built per viewer: labels that never overlap, fly-to on click, search that frames its hits, full screen, a wall-screen mode.

Works without an AI key; chat needs one

**Insight Rules and Insights Catalog**

About 25 rules behind every scorecard: what each watches, why it matters, and per role whether it is on, its urgency and limits. The Catalog lists every insight each kind of user gets and who may see it.

/admin/rules

**Chat assistant and layers 2 to 5**Hidden

Ask Kite Pulse in plain English with a cost preview, session narratives, project summaries, company intelligence, developer profiles, knowledge base and tech-debt radar are built, hidden in this phase, and come back with a one-line change.

docs/LLM-FEATURES.md lists all 15

#### Connecting outside systems Settings › Notifications & Integrations · Agent API

**Connectors: Jira, Confluence, GitHub, Google Drive, Notion, HubSpot, Slack**New

Each maps an outside space (Jira project, Confluence space, repo, Drive folder, Notion database, HubSpot company, Slack channel) to a Kite Pulse project and syncs in bounded runs every couple of minutes. Restricted items are never stored. Test, map, sync now, pause, edit, delete.

/admin/connectors · needs the master key

**Alerts to Slack**New

Open, escalate and resolve messages plus the digest to a Slack webhook, with a minimum severity and an hourly limit; three failures raise their own alert.

Notifications › Channels › Slack

**Agent API and MCP for the whole organisation**New

151 agent routes behind keys, the MCP endpoint, a per-install guide and OpenAPI schema written for each key, and an Agent Activity log. Writes come in families (teams, Brain, projects, accounts, knowledge) that an admin grants scope by scope.

docs/AGENT-API-GUIDE.md

**Email**

SMTP for invitations, codes, password resets, scheduled reports, alert emails and the daily digest, with a test email and a delivery history.

Notifications › Channels

#### Organisation knowledge Insights › Knowledge

**Knowledge Records**Knowledge classification

Passages from messages and AI replies filed under a project's capability map and tied to the sessions and commits behind them, with a Coherence tab for duplicates, conflicts and out-of-date records. Every read audited.

/admin/classification/knowledge

**Capability Map**

Each project's tree of modules, capabilities, scenarios and elements in the names people use, with placement rules, history and an Ownership tab. Add, rename, move, merge, split, retire, approve.

/admin/classification/capability-map

**Skill Candidates**New

Repeated work in a project that could become a Claude Code skill: how often, in how many sessions, by how many developers (never who), a draft SKILL.md to edit, approve or reject.

/insights/knowledge/skills

#### Rules the whole product keeps Design floors

**No ranking of people**

Team pages on AI labels pool figures; the only ordered list of people anywhere is Team AI Usage's plan-headroom attention order.

**Presence for everyone, detail in scope**

Colleagues see name, team, tool and presence. Project, sync, stuck and plan detail is for yourself, your manager and admins.

**Facts, never fiction**

Nothing in the Office is animated on a timer. Every movement comes from a real step, session, push, notice or plan reading.

**One developer's money is admin-only**

Usage routes, session pages and exports show notional list-price cost per person only to admins; never a bill.

**The server decides**

Permissions, scopes and the Brain's gate run on the backend before any page or model sees data; prompts are never the control.

**Efficient on a shared 4 GB server**

Reads batched, caches bounded, short transactions, one facts build at a time, lazy-loaded 3D and graph chunks.

What changed

## Since the first edition on 12 October

351 commits landed on the product branch between 12 and 28 October 2026. This is what they added, in the order a user met them. Every item is live on the branch; items marked "awaiting release" need a client release or a server restart to reach every machine.

1. 12–13 Oct

   **An honest install and a collector that explains itself**

   Installer without admin rights, per-user watchdog task, tray colours for setup / stalled / refused, a doctor command, wizard fixes, Codex and Gemini CLI discovery, and a verify script that trusts facts over banners.

   Workstream A
2. 13–15 Oct

   **A console people can find their way around**

   Sidebar regrouped, one entry per section with its pages underneath, count badges on what needs action, density trims on the overview pages, manager names in Accounts & Roles, and a menu guide rewritten in plain English.

   Workstream B
3. 13–15 Oct

   **The Office becomes the home page**

   Every developer's agent at a desk in a professional 3D office, presence for everyone and detail in scope, then the realtime workspace: task status, live feed, side panels, a full-screen wall view, light and dark, teams as glass rooms inside one office.

   Workstreams C and F
4. 19–20 Oct

   **Teams by function and by project**

   Project teams suggested from who worked on the same projects, one-click create, overlaps allowed, a Teams page, and the project teams flowing through cost, statistics, weekly reports, the Office and Team Review.

   Workstream G
5. 20 Oct

   **A lively office built on facts**

   Desk postures from real steps, stuck agents, helpers, a company map view, each desk's "today" (sessions, tool calls, stuck stretches, tokens), the board's failed state, and a project-team lens. Nothing moves on a timer.

   Workstream I
6. 21 Oct

   **The Enterprise Brain, the first connector, agent writes**

   Declared profiles and project context, a permission gate every model call must pass, Brain chat with sources, documents per department, built-in and department agents, the Brain graph, governance and retention, a cross-department leakage test suite, Jira as the first connector, and agent keys that may change teams with a dry run.

   Workstreams J, H and G4
7. 22 Oct

   **Six more connectors, Slack both ways, SCIM, the organisation's name**

   HubSpot, Slack, GitHub, Confluence, Google Drive and Notion feed projects and the Brain; alerts go out to Slack; Entra ID and Okta sync users over SCIM 2.0; "Ask a teammate's agent"; the Office carries the organisation's name; plan headroom markers and a Headroom board; a readable, zoomable Brain graph; finished side panels and person card.

   D34, R43–R48
8. 23 Oct

   **Closing the gaps the market comparison found**

   Agent Setup (skills, commands, agents, MCP servers and plugins across machines), a session timeline from the desk, plan-limit and agent-stuck notices, a token pace line, AI Budgets with 80 % / 100 % alerts, Project notes with versions, no built-in S3 bucket, and sub-agents shown beside each person in the Office.

   Workstream M, R51
9. 26 Oct

   **An agent-centric office that gets the screen**

   Agents rest in a lounge when their person is away, typing / reading / watching / supervising / waiting postures, "Waiting for you", a parcel on a push and a page into the Brain, exact approvals from Claude Code's notification hook (client 0.4.4, awaiting release), an icon rail by default and one right-hand panel so the office fills the page.

   R52, R53
10. 27 Oct

    **Session analytics and the 8-section menu**

    Merged from Neenu's branch: Summary, Needs attention, Activity Overview, Workflows & Pain Points, Skill Candidates, Session Graph, My Day, plan usage history and its report, Agents right now and in parallel, API gaps closed, and the menu as Home · Insights · Developers · Projects · AI Usage · Operations · Settings · Me.

    Neenu02_34 merge
11. 28 Oct

    **Sub-agents as light threads**

    Each sub-agent a badge on a thread of light with packets travelling while it works, a holo card on click, and a stack that fans out for the fourth onwards.

    R56

**Built, not yet in the product.** A simpler console for first-time users (five sections, plain words, one bell, an admin home, a welcome tour) and a new visual design are complete on separate branches and wait for an approval to merge. Windsurf is listed as a tool but has no parser. An open-source release is deferred. Phase 2 (feeding knowledge back into the AI tools) has not started.

Architecture

## The big picture

Three places are involved: the developer's computer, the Kite Pulse server, and whoever opens the dashboard in a browser. The numbered boxes are the three programs that must be running.

Data only moves one way: from the developer's computer into the server. The collector never gets passwords to the storage; it can only hand encrypted pieces to the API server. The Office updates in the browser over a live stream from the API server. The dashed box is an outside AI service that only the optional AI features call.

Around the core. Outside systems only ever come in through a connector mapped to a project; an agent only ever asks through a key scoped to its owner; alerts only ever go out through channels an admin set. Each of these is off until an admin configures it.

| Part | Think of it as… | What it really does |
| --- | --- | --- |
| Collector | A courier who seals each letter before collecting it | Finds new lines in your AI session files, strips secrets, encrypts them, uploads them, and reports the extra reads an admin switched on. |
| Watchdog | The courier's supervisor | Restarts the collector if it crashes and installs updates sent from the server. |
| API server | The post-office counter | Checks who is sending, accepts the sealed pieces, answers the console and the agents, streams the Office, and runs the notice and SCIM doors. |
| Storage | The in-tray | Holds encrypted pieces until the watcher picks them up (local disk, or S3 when configured). |
| Watcher | The sorting room | Every 30 s: opens new pieces, joins them into whole sessions, works out the Layer 1 facts. |
| Worker + jobs | The back office with a to-do list | Every 5 s takes the next job; separate threads sync connectors, prune the Brain's access log, rebuild the session graph nightly, send alert emails and Slack messages. |
| Database | The filing cabinet | PostgreSQL, running in Docker. Everything the console shows comes from here. |
| Console | The reading room with a window onto the floor | A React web app at `/admin`: the Office, charts, lists, reports and settings. |

What "running" means

## Three programs, all required

An install is only complete when all three are running. Two out of three can look healthy and still show nothing, which is the most common beginner mistake.

1

### API server

Command

`python -m uvicorn server.api.app:app`

Job

Accepts uploads, handles logins, serves 419 web routes (151 of them for agents), the MCP endpoint, the Office's live stream and the console. Built with FastAPI.

Without it: nothing works at all.

2

### Orchestrator

Command

`python -m server.orchestrator.main`

Job

One program with several helpers: the watcher (new data in), the worker (job queue), the snapshot builder, the connectors thread, the session-graph builder and the retention jobs.

Without it: uploads pile up unread and the dashboards stay empty forever.

3

### Collector

Command

`python -m client.main`

Job

Runs where you code. Reads `~/.claude`, `~/.codex`, `~/.gemini`, `~/.cursor` and the VS Code family's storage, and uploads new activity.

Without it: no computer registers, no project is found, nothing is uploaded, and the server still reports "healthy".

You don't have to start these by hand. One **quickstart** script starts all three (plus the database) for you. See [Run it](#run).

Step by step

## The journey of one coding session

What happens between "a developer asks the AI something" and "a chart shows up in the console".

1. Your computer

   #### The AI tool saves the conversation

   Claude Code, Cursor and the others write each session to a file on disk, for example under `~/.claude/projects/`.
2. Collector

   #### It notices only the new part

   The collector remembers how far into each file it has already read, like a bookmark. On each pass it takes only what was added since.
3. Collector

   #### Secrets out, then encrypted

   Secret files (keys, auth files) are skipped and passwords or tokens are scrubbed. The new piece, called a *patch*, is encrypted before it leaves the machine.
4. API server

   #### Upload and safe-keeping

   The patch travels over HTTPS to the API server, which checks the device and puts the patch in storage. Big files go up in 5 MB pieces.
5. Watcher · every 30 seconds

   #### Unpack and translate

   The watcher decrypts new patches and joins them back into the full session. A *parser* for that tool translates its format into one common shape, so every later step works the same for every tool.
6. Watcher

   #### Cut into sessions and chunks

   A gap of 30 minutes starts a new session. Each session is cut into chunks of up to 40 messages (or at a 10-minute pause). Sub-agent sessions are matched to the call that started them.
7. Watcher

   #### Layer 1: count everything

   Duration, messages, tools used, files touched, git commits, languages, tokens, step kinds, stuck stretches. Plain code, no AI, done instantly and saved to the database. Follow-up jobs go on the queue.
8. Worker · every 5 seconds

   #### Work through the job queue

   The worker picks up queued jobs one at a time (or 10 in parallel for chunk jobs). Failed jobs are retried up to 3 times. AI labelling, if on, runs here under its budget.
9. The Office · seconds

   #### The desk moves

   The API server rebuilds the Office's facts and pushes a change over the live stream. The person's agent types, reads, waits or walks, and the task board and feed follow.
10. Console

    #### See it in the numbers

    The console asks the API server, which reads the database. The first figures can appear about 35 seconds after the first upload; 1–2 minutes is a realistic wait.

The pipeline

## Five layers, from facts to company knowledge

Raw data enters at the bottom and gets more refined on the way up. Each layer only reads the layer below it. Layers 1–3 are **permanent** (written once, never changed). Layers 4–5 are **snapshots** (rebuilt from time to time; older versions are kept). Two newer AI features run beside the tower rather than inside it.

Running on every install Optional, an admin switches it on with a key and a budget Built, switched off in this phase

L5

#### Intelligence: the story of the whole company

Rules that hold across all projects, a library of problems and their fixes, and a short executive brief.

All projects · snapshot\~$0.03 per rebuildOff

L4

#### Project: the story of one project

How the project changed, its tech stack, knowledge and rules, deferred work, and an overall health read. Rebuilt every 5 sessions, weekly, or on request.

One project · snapshot\~$0.50 per rebuildOff

L3

#### Session: the story of one session

Groups the chunks into work threads and writes a 6–10 paragraph narrative of the session.

One session · permanent\~$0.03 per sessionOff

L2

#### Extraction: the meaning of each chunk

Six AI passes per chunk: knowledge, friction, technical changes, deferred work, teamwork dynamics, and how the developer directed the AI. A no-AI version of some checks (tool failures, files changed, TODOs) already runs.

One chunk · permanent\~$0.08 per sessionOff

L1

#### Collection: the facts

The session's scoreboard: start, end, duration, messages, tools, files, commits, languages, tokens, steps, sub-agents, stuck stretches, and whether it ended cleanly. Everything in the Office and the Phase 1 pages comes from here.

One session · permanent$0, no AIOn

Prep

#### Session reader

Splits the raw log into sessions and chunks. Plain code.

No AIOn

↑ Data flows up · raw session log enters at the bottom

Beside the tower

### AI labelling ("JEV")

About 70 label lists, each one question the AI answers about a piece of work, approved by an admin before use. Fills My Day, Trends, Blocker Board, Team Review, AI Collaboration and the knowledge views. Fact rules (no AI) run every 6 hours even while it is off.

Optional · own switch, model and monthly cap

Beside the tower

### The Enterprise Brain

Answers questions from Kite Pulse data, declared profiles, documents and connected records. A gate filters everything the asker may not read before the model sees it. The graph works without a key; chat needs one.

Optional · switch, budget, retention

Side track

### Developer Profile

Observations from Layers 1–3 about how a person works with the AI, and a working-style label (builder, explorer, debugger, communicator, generalist) worked out by rules. Judges the person as a manager of AI, never as a coder.

Agents

## The AI agents it watches, and its own helpers

"Agent" means three things here. The AI coding agents whose sessions Kite Pulse reads. The outside agents that ask Kite Pulse questions through a key. And the small background programs inside Kite Pulse that each do one job on their own.

### AI coding agents it can read

Each tool saves its sessions differently, so each has its own *parser* on the server (in `server/parsers/`). An admin chooses which tools are collected under **Settings › Tools**.

**Claude Code**appendThe first one supported. Sub-agents, plan usage, hooks and skills are read here too.

**Codex**appendTested on real samples. Honours CODEX_HOME.

**Gemini CLI**appendAdded in October.

**Cursor**snapshotTested on real samples.

**Cline**snapshotTested on real samples.

**Roo Code**snapshotTested on real samples.

**OpenCode**snapshotTested on real samples.

**Kilo Code**snapshotTested on real samples.

**Aider**snapshotTested on made-up sample files only.

**GitHub Copilot**snapshotNamed profiles found; plan tier read behind a switch.

**Windsurf**snapshotIn the list, but no parser yet.

#### append mode

For tools whose log file only ever grows. The collector sends just the new bytes since last time, like sending only the newest page of a diary.

#### snapshot mode

For tools that keep a small database that changes in place. The collector sends a fresh, cleaned copy, but only when its fingerprint (content hash) has changed.

### Outside agents that ask Kite Pulse

Key · read

#### 115 read tools

Sessions, people, teams, projects, usage, costs, stuck stretches, timelines, labels, knowledge, ops: each scoped to what the key's owner may see, each call logged under Agent Activity.

Key · write scope

#### 11 write tools

Teams, Brain documents and agents, project approvals, accounts and knowledge records, only with that scope on an unlimited key, with a dry run and an audit row "via key".

Key · Brain

#### brain_search · brain_whoami

The Brain's gate returns the items; the asking agent is the model. Limited keys are refused; the query itself is never logged.

### Kite Pulse's own helpers

Developer computer

#### Collector

Finds session files, scrubs secrets, encrypts, uploads, sends a heartbeat and the switched-on extra reads. About once a minute while you're active.

Developer computer

#### Watchdog

Keeps the collector alive (Task Scheduler on Windows, launchd on macOS) and swaps in new versions sent over the air.

Developer computer

#### Tray icon + doctor

Green connected, blue setup, yellow retrying, orange stalled, red refused; Run diagnostics explains what is wrong.

Server · orchestrator

#### Watcher

Every 30 s: picks up new uploads, rebuilds sessions, runs Layer 1, queues jobs.

Server · orchestrator

#### Worker

Every 5 s: runs queued jobs. If the AI service runs out of credit, it pauses the queue and raises an alert instead of failing silently.

Server · orchestrator

#### Snapshot builder

On a timer, rolls the day's numbers up into daily summaries so the console loads fast, and writes the weekly project-team figures.

Server · orchestrator

#### Connectors thread

About every 2 minutes runs up to three due connections in bounded pages with a cursor, never on boot. Restricted items are never stored.

Server · orchestrator

#### Session graph + retention

Nightly: rebuilds the Session Graph with plain statistics, prunes the Brain's access log and departed people's conversations in batches.

Server · API

#### Office facts + stream

Builds the office's facts once for everyone (10 s cache, one build at a time), projects them per viewer, and pushes changes over the live stream.

Server · API

#### Work notices

Every 10 minutes keeps "Plan limit reached" and "AI agent stuck" notices for the person and their manager, and resolves them when over.

Server · alerts

#### Alert notifier

Bell, email and Slack for server alerts, budgets at 80 % and 100 %, a daily digest, an hourly limit.

Server · safety

#### Secret scanner

A last line of defence on the server. It rejects any piece that still contains something that looks like a password or token, and the Leaked Credentials page lists what slipped into chats.

Server · AI

#### The Brain's gate optional

Every model call passes through a sealed scoped context built in SQL and re-checked in Python; the gateway refuses anything else.

Server · AI

#### Chat assistant optional

Ask questions about your data in plain English. A planner picks one approved query, the answer streams back, and the cost is logged. Hidden in this phase.

Server · rules

#### Insight rules + personas

About 25 rules behind every scorecard, shaped to a person's work role (developer complete; analyst, business manager, designer and system admin as placeholders). No AI.

| Background job | What it does | When it runs |
| --- | --- | --- |
| dev_obs_l1 | Notes Layer 1 facts about the developer (no AI) | After each new session |
| fact rules | Rule-made labels (no AI): tool failures, files changed, TODOs | Every 6 hours |
| classification | AI labelling of chunks under the monthly cap | When switched on, as sessions arrive |
| connectors | Syncs due Jira, Confluence, GitHub, Drive, Notion, HubSpot and Slack connections | About every 2 minutes, at most 3 due |
| work_notices | Plan-limit and agent-stuck notices, budget alerts | Every 10 minutes · budgets hourly |
| session_graph | Rebuilds the Session Graph from the last 90 days | Nightly, or by hand |
| brain-retention | Prunes the Brain's access log (180 d) and departed conversations (30 d) | Each interval after boot |
| l2_chunk … l5_global | The deeper layers (6 AI calls per chunk, session story, project and company pictures) | Off in this phase |
| dev_profile | Rebuild a Developer Profile | Every 50 new observations |

Folders

## How the code is organised

There are two "roots". The **repo root** is the folder you cloned. The **product root** is `kite-pulse-generic/` inside it, and almost every command runs from there.

- kitegeneric/Repo root: the folder you cloned
  - README.md · INSTALL.mdOverview, and the one numbered install path
  - AGENTS.mdRules for AI assistants that install or change the project
  - docs/Architecture, data model, menu guide, dashboard guide, agent API guide, client data access, troubleshooting, glossary
  - kite-pulse-generic/Product root: run commands from here
    - client/The collector, watchdog, tray icon, doctor and installer
    - server/api/The API server (FastAPI): logins, uploads, every console route, the Office feed, SCIM, notices
    - server/agent_api/The agent API, the MCP endpoint, keys, scopes, write families, the served guide
    - server/orchestrator/Watcher, worker, snapshot builder, connectors and retention threads
    - server/pipeline/The layer logic (L1–L5), facts, insights, developer profile, personas, plan usage
    - server/parsers/One translator per AI tool (11)
    - server/classify/AI labelling: label lists, approvals, budget, confidence, the call log
    - server/brain/The Enterprise Brain: scope, gate, search, ask, documents, agents, graph, governance, teammate
    - server/connectors/Jira, Confluence, GitHub, Google Drive, Notion, HubSpot, Slack, and the sync framework
    - server/chat/The optional AI chat assistant
    - server/registration/ · llm_keys/ · password_reset/Sign-up flows, encrypted AI keys, password resets
    - shared/Database tables, encryption, storage, settings, redaction, Slack alerts: used by both client and server
    - admin/The web console (React + Vite), served at `/admin`; `src/features/office/` holds the 3D office
    - \_scripts/Quickstart, stop, verify, preflight, database upgrades, backups, API coverage
    - tests/872 test files, run with pytest; the console's 267 test files run with npm test
    - docker-compose.ymlStarts the PostgreSQL database in Docker
    - requirements.txtPython packages (exact, audited versions)
    - .envYour local settings (template: `.env.example`)
    - .local/staging/Your local data and logs. Never delete it to "start clean".

### Where the code lives

Lines of code per part, counted on 28 Oct 2026 (Python, JavaScript, CSS, SQL, shell). Tests are still the biggest part.

Show as a table

### Tech stack, in plain words

**Python 3.13**The language for the server and collector

**FastAPI + Uvicorn**The web server that answers requests and streams the Office

**SQLAlchemy**Lets Python code talk to the database

**PostgreSQL 16 in Docker**The database, running in a container

**cryptography (Fernet)**Encrypts every uploaded piece, connector credentials and webhooks

**bcrypt + JWT**Safe passwords and login tokens

**React 18 + Vite**Builds the web console

**three.js**Draws the 3D office (lazy-loaded on that page only)

**ApexCharts · SVG**The console's charts, the Brain graph and the company map

**TanStack Query · Zustand**Fetch and remember data in the console

**MCP + OpenAPI**How outside agents call Kite Pulse

**pytest · Vitest**Run the automated tests

**PyInstaller**Packages the collector as a desktop app

**i18next**Translations for the console

**SCIM 2.0**User sync from Entra ID and Okta

By the numbers

## How it was built, and what the server offers

Measured from the code on 28 Oct 2026. Routes and pages count what exists, whether or not a given install has switched the feature on.

### Commits per week

1,281 commits between 8 Jun and 28 Oct 2026, by week starting Monday. The two October peaks are the Office, the Brain and the teams work plus the merge of the session-analytics branch.

Show as a table

### API routes by type

419 web routes, 151 of them for agents. **GET** reads data, **POST** sends or creates, **PUT** replaces, **PATCH** edits, **DELETE** removes.

Show as a table

### Console pages by section

69 pages in the menu. 23 more are switched off but still open at their address.

Show as a table

**122**permission resources **129**MCP tools **872**Python test files **267**console test files **\~70**label lists **\~25**insight rules **0.4.4**collector version

The web console

## Who sees what

Two separate settings decide what a person sees. Their **access level** decides which sections appear; an admin can grant any page to any role, or create a custom role such as "Auditor". Their **work role** (developer, designer, analyst…) changes how the tips and metrics are worded for them.

| Section | Admin | Manager | Developer | Scope |
| --- | --- | --- | --- | --- |
| **Home** · The Office, Help | ✓ | ✓ | ✓ | Presence for everyone; detail for yourself, your reporting line, and all for admins |
| **Insights** | ✓ all 15 | Summary, Needs attention, Activity, Trends, Reports | Needs attention | Admin: organisation · Manager: reporting line |
| **Developers** | ✓ | ✓ | – | Teams page admin by default |
| **Projects** | ✓ | ✓ | – | Deciding needs the approve permission |
| **AI Usage** | ✓ | Team AI Usage, Agent Activity | – | One person's money admin-only |
| **Operations** | ✓ | – | – | Server Storage and Configuration never grantable |
| **Settings** | ✓ | – | – | Label Lists admin-only |
| **Me** | ✓ | ✓ | ✓ | Own data only |

So an admin sees eight entries, a manager six and a developer three. Admins can **Preview as** Admin, Manager or Developer from the top bar to see what each role gets.

### Home everyone

- The Office (3D · Map · List · Brain · Headroom)
- Full-screen wall view
- Help / Glossary (top bar)
- The Brain (from the Office)

### Insights managers, admins

- Summary
- Needs attention
- Activity Overview
- Trends
- Blocker Board
- Team Review
- Reports
- Workflows & Pain Points
- AI Collaboration
- Work Problems
- Organisation Overview
- Knowledge: Records, Capability Map, Skill Candidates, Session Graph

### Developers managers, admins

- Team Overview
- All Developers
- Collaboration
- Leave & On-Call
- Teams

### Projects managers, admins

- All Projects
- Approvals: Project Approvals, Onboarding, Request History
- Tidy up: Duplicate Detection, Project Mapping, Removed Projects

### AI Usage managers, admins

- Team AI Usage (+ Plan headroom)
- Tool Accounts
- Agent Activity

### Operations admins

- Data Collection
- Processing
- Machines
- Agent Setup
- Infrastructure
- Alerts
- Server Storage
- AI Call Log
- Maintenance
- Configuration

### Settings admins

- Setup checklist
- Access: Accounts & Roles, Agent API Keys, Roles & Permissions, Login & Registration
- Security & Audit: Leaked Credentials, Audit Log
- Organisation: Organisation Name, Hourly Rates & Seat Prices, AI Budgets
- Collection Settings: Tools, Detection Rules, Retention
- AI Labelling: Classification
- Insight Rules
- Notifications & Integrations: Notifications, Connectors

### Me everyone

- Workspace
- My Day
- Scorecard & Insights
- Activity: My Activity, My Sessions
- My Projects: My Projects, Pending Requests, Project Detection
- Privacy
- Account

Switched off but reachable by address: Activity Rhythm, Coaching & Risk, Cost & ROI, Comparisons, Intelligence, Knowledge Base, Tech-Debt Radar, Project Details, Billing, Thresholds, Model, LLM & API Keys, AI Chat, Ask Kite Pulse, My Report, and the tab pages that moved into Classification, Insight Rules, Notifications and Account. The full list with reasons is in `docs/ADMIN-MENU-GUIDE.md`.

How to run it

## Install and start, step by step

This follows `INSTALL.md`, the project's single install guide. Pick your system and the commands below switch to match.

**Python 3.13 or newer**Check with `python --version`. Older versions fail during package install.

**Docker, running**Docker Desktop on Windows/macOS, with Compose v2. Installed is not enough; it has to be started.

**Node 20.9+ (optional)**Only needed to build the web console. The API works without it.

You also need internet access to PyPI, the npm registry and Docker Hub for the first install.

1. 0

   ### Get the code

   Required

   Clone the repository (it is private, so ask your team for access; `INSTALL.md` has the exact clone command). Then move into the product root. Every step below runs from there.

   ```
   cd kite-pulse-generic
   ```

   ```
   cd kite-pulse-generic
   ```
2. 1

   ### Start Docker

   Required

   Open Docker Desktop and wait for it to finish starting. Then check both of these succeed:

   ```
   docker info
   docker compose version
   ```

   ```
   docker info
   docker compose version
   ```

   Both commands finish without an error.
3. 2

   ### Check the machine (preflight)

   Recommended

   Looks at your computer and tells you if anything is missing. It doesn't change anything.

   ```
   python _scripts\preflight.py
   ```

   ```
   python3 _scripts/preflight.py
   ```

   It ends with `READY` (or `READY, with notes`).
4. 3

   ### Install and start everything (quickstart)

   Required

   One command starts the database, creates the Python environment, installs packages, builds the console, sets up the database, and starts all three programs. Choose your own admin password first. A first start takes a few minutes, with quiet stretches. That is normal.

   The collector it starts will read your local AI-coding session files (`~/.claude`, `~/.cursor`, …), remove secrets, and upload encrypted copies to the server on this machine.

   ```
   $env:KITE_PULSE_ADMIN_PASSWORD='choose-a-strong-password'
   powershell -ExecutionPolicy Bypass -File _scripts\quickstart.ps1
   $LASTEXITCODE   # 0 means all three are running
   ```

   ```
   KITE_PULSE_ADMIN_PASSWORD='choose-a-strong-password' _scripts/quickstart.sh
   echo $?   # 0 means all three are running
   ```

   The exit code is `0`. Trust the exit code, not the banner text.
5. 4

   ### Verify the install

   Required

   Quickstart already runs a check, but this fuller one also tests logging in. It only reports problems; it never changes anything.

   ```
   .venv\Scripts\python.exe _scripts\verify_install.py --admin-password 'your-password'
   ```

   ```
   .venv/bin/python _scripts/verify_install.py --admin-password 'your-password'
   ```

   Zero `FAIL` lines and a final `VERIFIED`. A `SKIP` means "not proven", so read it.
6. 5

   ### First login and password change

   You, in the browser

   Open the address quickstart printed, usually `http://localhost:8080` (it picks the first free port from 8080 to 8099). Log in as `admin@admin.local` with your password. You will be asked to set a new one straight away; until you do, most pages answer "password change required".

   You reach the console after choosing a new password. The Office is the first page you see.
7. 6

   ### Finish the Onboarding Wizard

   You, in the browser

   Confirm which projects the collector found on your machine and press **Finish**. Nothing is uploaded until you do. **An empty office before this step is expected, not broken.**

   The collector log changes from `Onboarding pending` to `Uploading …` lines, and your desk appears in the Office.
8. 7

   ### Confirm data is flowing

   Recommended

   Use the *new* password from step 5. This waits until real numbers have gone all the way through. Allow 1–2 minutes.

   ```
   .venv\Scripts\python.exe _scripts\verify_install.py --admin-password 'new-password' --wait-for-data
   ```

   ```
   .venv/bin/python _scripts/verify_install.py --admin-password 'new-password' --wait-for-data
   ```

   `data flowed PASS` appears in the summary.
9. 8

   ### Walk the Setup checklist

   Admin, in the browser

   Under **Settings › Setup checklist**: declare teams, invite people (Accounts & Roles, or SCIM), choose what the app reads (Tools, Retention), set an AI budget and insight rules, connect email or Slack, issue agent keys, and switch on AI labelling or the Brain if you want them. Each step links to its page.

   Every step on the checklist reads done, or is one you chose to skip.

### What the quickstart exit code means

| Code | Meaning |
| --- | --- |
| 0 | All three programs are running. |
| 3 | The collector should have started and didn't. Nothing can sync yet. |
| 4 | The built-in check found a real failure. Read its output. |
| other | Something failed. The error text tells you what. |

### Stop, logs and API docs

Stop the three programs (the database keeps running):

```
powershell -ExecutionPolicy Bypass -File _scripts\stop.ps1
```

```
bash _scripts/stop.sh
```

Logs are in `.local/staging/logs/`. On Windows the server's real output is in `server.err.log`; the others are `orchestrator.log` and `client.log`.One file per program: `server.log`, `orchestrator.log`, `client.log`.

Interactive API documentation is at `/api/docs`; the agent guide is at `/api/v1/agent/guide` on the same address.

### After restarting your computer

Nothing is broken, but Docker Desktop doesn't start by itself. In order: start Docker Desktop → run `docker info` → run the stop script (it clears leftover process records) → run quickstart again → run the verify script.

### Common first-day problems

| You see | What it means and what to do |
| --- | --- |
| `open //./pipe/dockerDesktopLinuxEngine…` | Docker Desktop isn't running. Start it, wait, and run again. Don't reinstall. |
| The Office is empty | Finish the Onboarding Wizard (step 6). Before that, empty is normal. |
| 403 `password_change_required` | Do the first-login password change (step 5). |
| `admin` / `admin` doesn't work | By design. Use the password you chose in step 3. |
| Lost the admin password | Reset it with `_scripts/bootstrap_env.py --env staging --reset-admin-password` using the `.venv` Python. Re-running quickstart won't reset it. |
| Port 8080 is busy | Fine. Quickstart moves to the next free port up to 8099 and prints it. |
| Port 5432 (database) is busy | Set `DB_PORT` to another number in `.env` and run again. |
| `Could not find a version that satisfies fastapi==…` | Your Python is older than 3.13. Install 3.13; don't edit the versions. |
| A Brain, connector or Slack setting says it needs the master key | Set `KITE_PULSE_MASTER_KEY` on the server; credentials are only ever stored wrapped with it. |
| `stale pidfile` | Harmless. A leftover record was cleaned up. |

Full list: `docs/TROUBLESHOOTING.md`. Team setup (server, invites, a client on each machine): `docs/INSTALLATION-FLOW.md`.

Stay safe

## Golden rules for beginners

Each "don't" below once broke a real install. Most mistakes come from treating a shortcut flag as a fix.

### Do

- Run commands from `kite-pulse-generic/`.
- Trust the exit code and `verify_install.py`, not the banner.
- Keep all three programs running, including the collector.
- Back up before any reset: `docker compose exec -T db pg_dump -U kite_pulse kite_pulse > backup.sql`
- Use `npm ci` for the console, never `npm install`.
- Switch an AI feature on only with a key *and* a monthly budget.

### Don't

- Use `--sqlite` to get around a Docker problem. Start Docker instead.
- Use `--no-client` to hide a collector problem. Nothing would sync.
- Kill other programs to free a port. Change Kite Pulse's port instead.
- Run `docker compose down -v` or delete `.local/staging`. That erases every account and metric.
- Set `KITE_PULSE_ENV=live` or the HTTPS settings on a local install.
- Lower the versions in `requirements.txt` to make an old Python work.

Words you'll meet

## Glossary

Session file

The file an AI coding tool writes while you work with it.

KP session

One stretch of work inside that file. A 30-minute pause starts a new one.

Chunk

A slice of a session: up to 40 messages, or until a 10-minute pause.

Patch

An encrypted piece of new session data that the collector uploads.

Collector / thin client / Kite Pulse app

The small program on each developer's computer.

Watchdog

Keeps the collector running and installs its updates.

Orchestrator

The server program with the watcher, the worker and the background threads.

Parser

Server code that translates one AI tool's format into the common shape.

The Office

The home page: every person's AI agent at a desk in a 3D office, moving only for what it really does.

Sub-agent

A helper an AI agent starts for a task. Shown as a badge on a light thread beside the person.

Function team / project team

A team declared by hand (Accounts, Development) vs one suggested from who worked on the same projects.

Plan headroom

How much of a Claude plan window is left, read from the tool's own usage figures.

AI labelling / classification / JEV

The optional AI that answers approved questions (label lists) about each piece of work.

The Brain

The optional Enterprise Brain: questions answered with only what the asker may read, plus its graph.

Gate / scoped context

The server-side filter every Brain model call must pass; checked in SQL and again in Python.

Agent key

A `kpk_…` key that lets an outside AI tool ask Kite Pulse as a chosen person, within scopes.

MCP

Model Context Protocol: how Claude Code, Cursor and VS Code call Kite Pulse's tools directly.

Connector

A mapped link from an outside system (Jira, GitHub, …) into a Kite Pulse project.

SCIM

The standard an identity provider uses to create and deactivate users automatically.

AI Budget

A monthly token or notional-dollar limit on a team's or project's AI use, with alerts at 80 % and 100 %.

Permanent vs snapshot

Permanent results are written once. Snapshots are rebuilt and versioned.

Onboarding Wizard

The browser step where you confirm projects. It opens the upload gate.

HIL (human in the loop)

An action a person triggers, like approving a project or a label list.

OTA update

"Over the air": the collector updates itself without a reinstall.

Staging vs live

Local installs are always staging. Live is for the real team server.

Repo root vs product root

Your clone folder vs `kite-pulse-generic/` inside it.

### Where to read next

`INSTALL.md`: the install path, start to verified

`docs/ADMIN-MENU-GUIDE.md`: every console page explained

`docs/DASHBOARD-GUIDE.md`: how each number is worked out

`docs/AGENT-API-GUIDE.md`: keys, MCP and the served guide

`docs/CLIENT-DATA-ACCESS.md`: everything the collector reads and sends

`kite-pulse-generic/docs/plan/VIRTUAL-OFFICE-DESIGN.md`: the Office's rules

`kite-pulse-generic/docs/plan/ENTERPRISE-BRAIN-DESIGN.md`: the Brain's gate and threat model

`kite-pulse-generic/docs/plan/CONNECTORS.md`: the connector framework

`docs/LAYERS-AT-A-GLANCE.md`: the layers in plain English

`docs/TROUBLESHOOTING.md`: symptom → cause → fix

`docs/RECOVERY-AND-RESET.md`: safe resets and backups

`docs/GLOSSARY.md`: the full list of terms

Second edition, built from the Kite Pulse repository docs and code on 28 Oct 2026 (branch `Sonia00_newfeature`, commit `3f6bc256`). First edition 12 Oct 2026. Line counts, commit counts, table, route, tool and page counts were measured from the code; costs per layer are the estimates in `docs/02-ARCHITECTURE.md`.