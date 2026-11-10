# Kite Pulse Website Content — Master Source of Truth

Oct 28, 2026 · @Neenu

## How to use this document

This is the one list of what the Kite Pulse website may say about the product. Copy for any page comes from Section 1 only. Anything in Section 2 stays off the site, or appears only as "coming soon", until it is checked and moved up.

**What was reviewed**

- The website brief: [Kite Pulse Site Preview: Content Request](https://claude.ai/artifact/KDwwMkHFszTtvsCfL9CVXX) (56 pages; 8 designed, 1 on sample figures, 47 not written).
- The current wording source for the site: [Kite Pulse — Product Guide](https://claude.ai/artifact/3oqnhAwxZwNq9yoH4nGJvo), written 13 October 2026.
- The source code: console menu and pages, API server, desktop collector and the ten tool readers, on branch Neenu02\_34\_SessionAnalytics (latest commit 7020649c).

The text of the 8 designed pages was not shared with this review. Their claims are covered through the Product Guide they were written from; send the page copy to check it line by line.

**How it was checked.** Every claim was checked against the code twice on 28 October 2026: once while writing, then again by five independent reviewers who had not seen the first pass. Their corrections (about 50) are applied throughout. Claims resting only on uncommitted code were removed.

**Rules used**

- **Verified** means the code does it and a user can reach it today: a visible console page or tab, a collector behaviour that runs by default, or a switch an admin can turn on in the console.
- Documentation, comments, plans and changelog lines alone do not count as proof.
- A page that exists in code but is hidden from the menu is **not** verified, even though it loads on a direct address.
- Prices, plans, trial terms, company details, customer examples and certifications are business facts. Code cannot confirm them, so they are listed in Section 2 for the owner to supply.

## Product summary

Kite Pulse shows a team how its software is built with AI coding assistants. It reads the session history ten AI coding tools already keep on each developer's computer, masks secrets, and sends it to a Kite Pulse server the team runs itself. A web console turns those sessions into a picture of who is working on what, how AI tools are used, what they are estimated to cost, how close people are to their Claude plan limits, and where work gets stuck.

**One-line description:** one place to see AI-assisted development across people, projects and tools, on a server the team controls.

**Who it is for**

| Who | What Kite Pulse gives them |
| --- | --- |
| Individual developers | Their own sessions, work patterns, working style and suggestions to try, with private prompt statistics only they see. |
| Team leads and managers | Live team activity, project health, collaboration, plan-limit pressure and repeated failures for their reporting line. |
| Executives and finance | Token use and estimated list-price cost per tool, seat prices, shared accounts and monthly budgets per team or project. |
| Administrators and IT | Accounts and roles, project approvals, tool switches, machine status, infrastructure alerts and an audit log. |

**How it works**

1. A small desktop program on each developer's computer (Windows or macOS) reads the AI tools' own session history.
2. It masks secrets, encrypts session uploads and sends only new activity, only after the developer confirms their projects.
3. The team's own Kite Pulse server stores and processes it. There is no vendor cloud in between.
4. Everyone signs in to the web console and sees the pages their role allows.

**Where it runs:** on one person's computer, on a team's local network, on an Ubuntu server, or in the customer's own AWS account. All are self-hosted.

**What it is not:** it does not log keystrokes, take screenshots, track websites or open project source files (session records can include excerpts the AI read). It is not a code-quality scanner. It does not need an AI service to work.

## Section 1 — Verified features

Everything below is in the code and reachable by users today. Page names are the console menu labels as they stand now.

### 1.1 Capturing sessions (the desktop program)

- **Ten AI coding tools, collected out of the box.** Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot Chat in VS Code, Cline, Roo Code, Kilo Code, OpenCode and Aider. All ten are on in a new install; an admin can switch any tool off on **Tools**.
- **Two switches per tool** on **Tools**: Session sync (the conversations) and Token consumption (counts only). A third, Generation rate (request timing), works for Claude Code only and needs the developer's opt-in.
- **Counts-only mode.** With Session sync off and Token consumption on, the program counts tokens on the computer and sends only the numbers, never the conversation.
- **No manual logging.** The program runs in the background and reads the history each tool already keeps.
- **Only new activity is sent.** Growing files resume from the last point the server has; other files are re-sent only when they change.
- **Nothing lost offline.** If the network drops, the program remembers where it stopped and catches up once the server is reachable. Large uploads resume part by part.
- **Projects found automatically.** It finds project folders and reads each repository's address, so one repository cloned on several machines counts as one project. Each session is linked to its project.
- **Secrets masked on the computer.** 36 credential patterns are masked before upload: cloud and AI provider keys, GitHub and GitLab tokens, private keys, and passwords in URLs or labelled fields. If masking fails, that part is not sent. For Cursor and OpenCode, the tools' login stores are never sent, and credentials pasted into their chats are masked on your server.
- **Encrypted before it leaves.** Every session upload is encrypted on the computer. Small status records (token counts, plan figures, the folder list) are sent over HTTPS.
- **Goes only to your server.** No server address is built in; the program will not run until it is given the team's own server.
- **Personal client code.** On first run the developer enters their personal code (starting KP-), which links the computer to their account. A renamed or reinstalled computer keeps its identity.
- **Nothing uploads before consent.** No session content is sent until the developer confirms their projects in the Onboarding Wizard and, where required, an approver signs off. Only the detected project folders (paths, names and repository addresses) are sent first, so the wizard can show them. Projects an admin switches off are not read at all.
- **Windows and macOS.** Windows installer and macOS package (Apple Silicon and Intel), built by the team for its own server. Starts at login and keeps itself running.
- **Automatic updates** from your own server, checked for size and integrity before install. The operator places a new build on the server; an admin then publishes it on **Tools**.
- **Tray icon** with status colour and Open dashboard, View log, Re-enter code and Run diagnostics.

**What each tool provides**

| Tool | Conversations and tool calls | Tokens | Model name | Cost shown | Account shown on Tool Accounts |
| --- | --- | --- | --- | --- | --- |
| Claude Code | Yes | Yes | Yes | Estimated from list prices | Account and seat tier |
| Codex | Yes | Yes | Yes | No price (shows “—”) | Account and ChatGPT plan |
| Gemini CLI | Yes | Yes | Yes | Estimated from list prices | None |
| Cursor | Yes | Input and output only | Only when one model served the whole chat | Usually none | Account and membership type |
| GitHub Copilot Chat (VS Code) | Yes | Input and output only | When recorded | Usually none | GitHub account id only |
| Cline | Yes | Yes | Yes | Tool's own reported cost | No login |
| Roo Code | Yes | Yes | Yes | Tool's own reported cost | No login |
| Kilo Code | Yes | Yes | Yes | Tool's own reported cost | No login |
| OpenCode | Yes | Yes | Yes | Tool's own reported cost | Account only |
| Aider | Yes | Yes | Yes | Tool's own reported cost | No login |

Failed tool calls are recorded for every tool except Aider. Command exit codes come from Claude Code, Codex and Copilot.

**Optional reads, off until an admin turns them on** (Settings › Retention › Kite Pulse app reads; each shows the app version it needs, 0.4.2 unless noted): current branch name; frameworks from package manifests; project notes (CLAUDE.md, AGENTS.md, READMEs, decision records); sleep, wake and network-loss events; installed AI and developer tool versions; Claude Code skills, commands, agents, hooks and MCP servers (plugins need app 0.4.3; confirm it is published); Copilot plan name; a background refresh of Claude Code plan usage, which the developer can turn off. The same tab also lists three reads that need the developer's opt-in or a newer app (Section 2.3): request timing, plan figures from the Claude Code status line, and Claude Code waiting signals.

### 1.2 AI usage, cost and plan limits

- **Team AI Usage.** Token use per developer, tool, model, project and day, for any period. Tabs: Overview, Consumption, Models, Projects, Tools & accounts, Agent features and Plan headroom. Managers see their own reporting line; admins see everyone.
- **Estimated cost per tool.** Tokens multiplied by the vendor's published list price. A price change is added as a new dated entry, so older sessions keep the price they ran at. Claude and Gemini models are priced. Aider, Cline, Roo Code, Kilo Code and OpenCode use the cost the tool reports itself. Other models show “—”, never $0. On Team AI Usage, cost is shown per tool, never added up across tools, and labelled “not billed spend”.
- **Cost per developer** is shown to admins only, on that developer's AI Usage tab.
- **AI Budgets.** Admins set a monthly budget per team or per project, in tokens or estimated US dollars, with alerts at 80% and 100%. Dollar budgets add up the priced tools and report unpriced tokens separately.
- **Hourly Rates & Seat Prices.** Admins enter what each tool's seats cost; seat prices then appear on the Team AI Usage Overview for admins.
- **Models tab.** Developers per model, model adoption over time, models by project, and Claude Code effort-level and speed settings.
- **Agent features tab.** Which Claude Code agent features sessions used (sub-agents, background commands, plan mode, worktrees, MCP tools and others), by session and developer.
- **Plan headroom (Claude Code).** Who is close to a Claude plan limit, worst first: the 5-hour window, the weekly window and each model's weekly window. “Near” is 80% or more; “at limit” is 100%. Old readings are flagged as stale, not hidden.
- **Claude Code version check.** Each developer's Claude Code version is compared with the latest release, with a “version behind” filter.
- **Your own plan figures.** Every developer sees their own Claude plan usage on their Workspace page.
- **Where plan figures come from.** The usage figures Claude Code saves on the developer's computer. No login or password is read. By default they are as fresh as the last time Claude Code saved them; an optional background refresh (admin switch, app 0.4.2 or later) keeps them current without using any tokens.
- **Tool Accounts.** How many separate signed-in accounts each tool runs under, with accounts used by more than one person marked “Shared”. Shows plan tier, machines, last seen and email domain. Works for Claude Code, Codex, Cursor, OpenCode and GitHub Copilot. Admin by default.
- **Work Problems** (formerly Error & Command Stats). Fixed rules, no AI, find failed commands, error messages and repeated retries, grouped by severity with suggested actions and the most affected developers. Admin by default.

### 1.3 Reports

- **Company report** for any period, compared with the previous period. Downloads as CSV or PDF (admins by default).
- **Plan usage report.** Claude plan usage per developer and per Claude account for a month or a date range: weekly peaks, weeks at 80% or more, weeks and 5-hour windows at the limit, and per-model peaks. Downloads as Excel (admins by default). History starts when recording began.
- **Scheduled reports.** The Company report or one developer's report emailed daily, weekly or monthly, as PDF or CSV, with a preview and a send history. Admins set them up; email must be configured on the server.

### 1.4 Pages for people, teams and projects

**Who sees what.** Three access roles: **Admin** (everyone), **Manager** (themselves plus their whole reporting line, including indirect reports) and **Developer** (their own pages, plus The Office, Needs attention and Help). The server enforces this, not just the screen. Admins can fine-tune each page per role on Roles & Permissions.

**Your own pages (every role)**

- **Workspace.** Is my work being collected? Project by project: detected, waiting to sync, syncing, processing, processed or failed. Also shows your own Claude plan usage.
- **My Scorecard & Insights.** Your own report, led by “Top 3 to act on”. Each insight gives a verdict, why it matters, what to try and the evidence. When there is too little data, it says “not enough data” instead of a verdict.
- **Work-pattern facts.** Peak hour, busiest day, longest streak, deep sessions (60 minutes or more), longest session, most sessions running at once, and share of short bursts (under 15 minutes). Busiest day is the weekday with the most commits.
- **Working style.** Builder, explorer, debugger, communicator or generalist, worked out by fixed rules from what your sessions mostly did: changing files, reading code, running commands or conversation.
- **Private prompt statistics.** Your most repeated prompt, most cryptic prompt, thank-you count and reply pace. Only you see them; the server removes them for everyone else.
- **My Activity** (when, how long, which tools) and **My Sessions** (every session with a summary, filters and a detailed view).
- **My Projects, Pending Requests, Project Detection.** Confirm, rename, split or remove your projects, follow your change requests, and review what was found on your computer.
- **Privacy.** Everything recorded about you, whether it is on now, and who can see it.
- **Account.** Profile, password, the Kite Pulse app, notification choices, and API keys issued to you.
- **The Office** (home page). A desk per person grouped by team, with online, away or offline status and markers for stuck work or plan limits. Detail only for people in your scope.
- **Needs attention** inbox and **Help / Glossary** from the top bar.

**Team and organisation pages (managers and admins unless noted)**

- **Team Overview.** Who is online and who is coding right now, active time and sessions today against a typical day, who needs attention (failing uploads, backlog, old app version) and each person's current project. Refreshes every 30 seconds; past days can be picked.
- **All Developers** and each developer's page: the same report the person sees, without their private prompt fields.
- **Organisation Overview** (admin by default). Active developers and hours, sessions, commits, project health, working styles, tools and languages.
- **Summary, Activity Overview and Trends.**
- **Collaboration.** Projects several people work on, with contributors, shared sessions and last activity.
- **Teams** (admin by default). Team membership with start and end dates, so history is kept.
- **Leave & On-Call.** Record leave, holidays and duty rotas so insights do not misread them. Managers edit their own line; company holidays are admin only.
- **Blocker Board, Team Review, Workflows & Pain Points, AI Collaboration.** Admin by default; admins can grant them to managers. Team-level views; Blocker Board shows recurring causes and suggested actions, never a single person.
- **Agents in parallel** (on the developer page: admins for anyone, managers for themselves). How many AI agents and sub-agents are working now, their state (working, waiting for the developer, waiting for permission), and a lane chart for any past day.
- **Claude Code version per developer** on Team AI Usage: Latest, Recent or Behind.

**Projects**

- **All Projects.** Every project with its health (active, stable or dormant), sessions, contributors and last activity.
- **Project page.** Contributors, sessions and a summary card: stability, tokens, phase, open blockers, duplicate work and knowledge records.
- **Onboarding Approvals.** An approver confirms a developer's first project list. On by default; can be switched off in Detection Rules. Approvers can file a folder under a parent project.
- **Project Approvals** and **Request History.** Approve or reject later change requests.
- **Duplicate Detection.** Groups folders that look like the same repository and offers Merge; also suggests splits.
- **Removed Projects.** Projects that were paused, scheduled for deletion or deleted. Managers can view; only admins can resume a paused project. A scheduled deletion can be cancelled until it runs; deleted data cannot be recovered.
- **Project Mapping** (managers and admins).

### 1.5 AI labelling and knowledge tools

Kite Pulse runs fully without any AI service. Collection, counts, reports, rule-based labels, Session Graph and Skill Candidates need no key. AI labelling stays off until an admin sets it up. Capability Map, Session Graph and Skill Candidates, at the end of this list, use no AI model.

- **Work classification (AI labelling).** Tags each piece of work, for example the type of work (building, debugging, refactoring, testing, planning, exploring, deploying, docs and more) and whether the session succeeded. Set up on **Classification** (tabs: Overview, Settings, Label Lists, Review Labels, Reports). It needs an OpenRouter key (entered on Classification › Settings), a monthly budget above $0, AI labelling switched on, and at least one approved and switched-on label list.
- **Admin approval first.** Every label list ships as an unapproved draft; an admin must approve and switch it on before it runs.
- **Monthly spending cap.** Labelling stops at the budget until the next month, with an alert at 80%.
- **Confidence bar.** Answers below the bar are stored as “unknown”, not as a label. **Review Labels** lists answers near the bar, unknown answers and a sample for checking.
- **Runs on new sessions automatically** once switched on; older history is labelled at a pace the admin sets.
- **Rule-based labels** (fact rules) are on by default, cost nothing and send nothing out.
- **AI Call Log.** Every AI labelling call (and every agent question where the Agent API is switched on), with what was sent and received, secrets masked.
- **Knowledge Records.** Passages worth keeping, quoted from real messages and linked to their sessions and commits. They appear once the knowledge label list is approved and has run, and start as “proposed”.
- **Capability Map.** Each project described as modules, capabilities and scenarios. A person builds and approves the map; a server operator can run a rule-based suggester (folders, routes, branches, ticket ids) to propose entries. No AI model.
- **Session Graph.** Links sessions that look alike and groups them; rebuilt once a day, on by default. No AI model.
- **Skill Candidates.** Draft Claude Code skills built by rules from repeated workflows, for a person to approve or reject. No AI model.

### 1.6 Administration and security

- **Sign-in.** Email and password, stored as secure hashes. Sessions last 2 hours, or 7 days with “Keep me signed in”.
- **First sign-in password change** is required for the first admin and for any account whose password an admin has reset.
- **Password rules.** Passwords people choose (sign-up, change, reset by email) need at least 12 characters with upper case, lower case, a digit and a symbol.
- **Lockout.** An account locks after 10 wrong passwords in 15 minutes; a network address is blocked after 20.
- **Password reset by email** from the sign-in page (needs email set up on the server).
- **Login & Registration.** Admin-created accounts (default), sign-up by company email domain, or open sign-up with admin approval.
- **Accounts & Roles.** Create accounts and set access role (Admin, Manager, Developer), work role and manager. Account management can be delegated to a manager for their own team.
- **Roles & Permissions.** A view and edit grid per page for each role. Custom roles can be defined on the grid but cannot yet be assigned to accounts.
- **Manager scope enforced by the server.** A manager sees only their own reporting line; an admin sees everyone.
- **Export one person's data** as a file, or **erase** it: erasing anonymises the account, deletes their raw activity records and destroys their encryption keys. Both are recorded in the audit log. Plain-text working copies of their sessions stay on the server (see Section 2.3).
- **Audit Log.** Sign-ins, failed sign-ins, lockouts and admin changes (over 100 kinds of action), read-only and filterable, kept indefinitely by default; a retention period (default 365 days) applies once the server operator enables deletion.
- **Retention.** Set how long plan-usage history is kept, and the windows for raw content, derived data and audit history (applied once the server operator enables deletion).
- **Detection Rules.** Thresholds for spotting problems without AI, whether new projects need confirmation, and the grace period before a removed project's data is deleted.
- **Tools.** Switch each AI tool on or off, and choose counts-only collection.
- **Machines** (was Fleet). Every computer running the collector, with version, update status and log.
- **Data Collection and Processing.** Whether each machine is uploading, and the processing queue.
- **Infrastructure checks**, on by default: stalled processing, memory, backlog, disk, database, email relay, silent collectors, old collector versions, repeated failed sign-ins and more.
- **Alerts and notifications.** Alerts with acknowledge and resolve, an in-app bell, email, and a daily digest. Admins choose who is told what on **Notifications**.
- **Server Storage.** Storage used, by person and project.
- **Connectors.** Connect Jira, HubSpot, Slack, GitHub, Confluence, Google Drive and Notion and map them to projects; credentials are stored encrypted. What each connector's data feeds in the console was not checked.
- **Configuration** (read-only install settings), **Maintenance** (project repair jobs), **Setup checklist** and **Organisation Name**.

### 1.7 Privacy safeguards

- **Reads session records, not source files.** The program reads the AI tools' own history, folder names and repository addresses. It does not open a project's source files, log keystrokes, take screenshots or track websites. Session records can include excerpts of code the AI read or wrote, with secrets masked. Optional reads of package manifests and project notes are off by default.
- **Secrets masked twice.** On the developer's computer before upload (for Cursor and OpenCode chat text, on the server only), and again on the server before storage.
- **Encrypted in transit.** Session uploads are encrypted before they leave the computer; everything else travels over HTTPS.
- **No vendor cloud.** Data goes only to the server the team runs.
- **Tool accounts are pseudonymised by default.** Only a keyed hash of the account, the email domain and the plan name are sent, never the address; for GitHub Copilot, only a hashed account number.
- **Consent before sync.** Nothing uploads until the developer confirms their projects, and an approver signs off where required.
- **Privacy page** (was Transparency). Each person sees every data point collected about them, whether it is on, and who can see it.
- **Private fields stay private.** Prompt statistics are shown only to the developer. Managers who do not work on a project see folder labels, not full paths; admins and the project's contributors see full paths.
- **AI features are opt-in.** If an admin turns on AI labelling, scrubbed text is sent to the AI provider through OpenRouter (default policy: zero data retention).

### 1.8 Deployment (self-hosted)

- **One computer, one person.** One command sets up the server, background worker, collector and database on one computer, reachable from that computer only.
- **Team pilot on a local network** from the same installer, on an address the team chooses.
- **Ubuntu server, automated.** One script installs everything on Ubuntu 22.04 or 24.04: PostgreSQL, web server, firewall, services, and optional free HTTPS certificates that renew themselves. Services restart automatically if they stop.
- **AWS, automated.** One script creates the server in the customer's own AWS account, shows a plan first and asks before creating anything. Optional private S3 storage.
- **Server only.** Run the server alone, with collectors on each developer's computer.
- **Database:** PostgreSQL. **Stored data:** local disk or Amazon S3.
- **HTTPS** is set up by the automated server install and can be required on any install.
- **Licence:** proprietary (NTGLOBAL SOLUTIONS). Not open source.

## Section 2 — Unverified features

Nothing in this section goes on the website as a current feature. Each row says why and what would move it to Section 1.

**Status key:** *Needs operator setup* = built, but only a server setting (not the console) turns it on. *Hidden* = built, but removed from the menu. *Partial* = some parts missing. *Not released* = in code, but the app version that carries it has not shipped. *Not built* = no code found. *Wrong as stated* = the code contradicts the claim. *Business fact* = code cannot confirm it.

### 2.1 Built, but not reachable by default

| Feature | Status | What exists | What needs verification |
| --- | --- | --- | --- |
| Agent API Keys (outside AI assistants read Kite Pulse data) | Needs operator setup | Complete: admin-issued keys per person, scopes, expiry (90 days default, 365 max), IP and project limits, rate limit, monthly budget, rotation, revocation. A key never sees more than its owner, re-checked on every request. Developers see and revoke their own keys under Me › Account › API Keys. | Off on a standard install: the operator must set two server settings (KITE\_PULSE\_AGENT\_API\_ENABLED and KITE\_PULSE\_API\_KEY\_PEPPER). The second is not in the install scripts or setup docs. Decide whether installs should switch it on, then document it. |
| MCP server | Needs operator setup | Streamable HTTP at /api/v1/agent/mcp, same key, on whenever the Agent API is on. Ready-made setup for Claude Code, Cursor and VS Code in the agent guide. Prompt text and AI replies are never available over MCP. In the default “chat” mode a key gets only ask, whoami and my\_usage; “direct” mode adds about 115 read tools and optional write tools with a preview (dry run). | Same as the Agent API. Also: ask needs a separate Agent API AI key and, by default, an admin-only permission, so a non-admin's key in chat mode can only call whoami and my\_usage. The agent guide's tool list is older than the code. |
| Agent Activity log | Needs operator setup | Every key request with route, tool and outcome; admins see every request; managers see requests made with keys of people in their team (some answer bodies withheld); everyone sees requests made with their own keys; CSV export. | Reachable only once the Agent API is on. |
| Data deletion after the retention period | Needs operator setup | Admins set retention windows in the console, but for session data the switch there schedules only a dry-run report. Plan-usage history and agent request logs are trimmed automatically. | Real deletion needs server settings. Until then, say “set how long data is kept”, not “data is deleted automatically”. |
| Leaked Credentials page | Partial | The page shows masked passwords and keys found in AI conversations and lets an admin set a status. | It fills only after an operator runs a command-line scan; no automatic scan was found. Status is set by hand, not checked with the provider. |
| Full tool-account email addresses | Needs operator setup | By default only an anonymised id, the email domain and plan name are sent. | Full addresses need a server setting; there is no console control. |
| Excluding single projects from the project-notes read | Needs operator setup | A server setting exists. | No console control. |
| Email (password reset, sign-up, notifications, scheduled reports) | Needs operator setup | All built and visible. | Mail server details are set on the server; the console only shows whether email works. Mention that email features need it. |

### 2.2 Hidden from the menu

| Feature | What exists | What needs verification |
| --- | --- | --- |
| Ask Kite Pulse, AI Chat, peer view of a teammate | Built; the menu entries are hidden and the chat service is off unless a server setting turns it on. | Owner decision to show it again. |
| Cost & ROI, billable view with markup | Hidden. Its markup and billable figures are Kite Pulse's own AI labelling spend, not the cost of the AI coding tools. The Waste panel (time × hourly rate) is on this hidden page. | Remove “billable view with a markup”. No ROI figure is reachable in the visible console. |
| Activity Rhythm, Coaching & Risk, Comparisons, Intelligence, Knowledge Base, Tech-Debt Radar (Trends is visible again since 15 Oct) | Built, hidden. The older AI insight panels inside visible pages are hidden too. | Owner decision to show them. |
| The Brain (organisation knowledge, ask questions of it) | No menu item, but reachable from The Office's Brain tab, where an admin can switch it on (off by default). Asking it questions needs an organisation AI key, whose settings page is hidden. | Owner decision. Not in the Product Guide. |
| Project Details, Events & Policies | Built, hidden 20 Oct: nothing in reports or the agent API reads these records yet. | Remove from site copy until something uses them. |
| Billing, Model, LLM & API Keys settings | Hidden. | No site copy needed. |

### 2.3 Partial or not yet released

| Feature | Status | What exists | What needs verification |
| --- | --- | --- | --- |
| Linux desktop program | Partial | The code handles Linux folders, and running from source is documented. | No installer, no auto-start, no automatic updates. Decide whether the site offers it. |
| Windows server install | Partial | A one-machine installer (quickstart.ps1) exists. There is no Windows server installer. | Not proven end to end on Windows. |
| Request timing (Generation rate) | Partial | Collector code (0.4.2) and the per-tool switch exist. | The developer opts in only by editing a config file; no tray or console control. |
| Claude Code status-line reading for fresher plan figures | Not released | Code only in the unreleased 0.4.4 collector (added 26 Oct, after the 0.4.3 version bump); the admin switch is visible. | Developer opt-in is by config file only. Confirm a release that carries it is published. |
| Claude Code “waiting for you” signals | Not released | Code in app 0.4.4; the switch is visible. | The collector code is at 0.4.4; the repo records no published 0.4.3 or 0.4.4 build. Confirm which version is live. |
| Signed updates | Partial | Updates are checked for size and hash. Signature checking exists but is inert unless the team builds the app with a signing key. | Releases are not signed yet. Do not claim “signed updates”. |
| Shadow AI detection | Partial | Only switched-on tools are read. Two partial signals: Tool Accounts' “Shared” flag (5 tools) and email-domain count (4 tools, not Copilot), and Machines › Installed tools, which checks six known AI tools per machine (optional read, off by default). | Nothing finds AI tools the organisation has not switched on. The /shadow-ai page must be reworded to these two signals. |
| Plan limits for tools other than Claude Code | Partial | Plan headroom covers Claude Code only; other tools show “Not reported by this tool”. Copilot plan name is an optional read. | Do not say “plan limits across tools”. |
| Cost per person and per project | Partial | Team AI Usage shows cost per tool. Cost per developer is admin-only on that developer's page; per team or project only in AI Budgets (month to date). | Reword to “cost per tool, with budgets per team or project”. |
| Cost for Codex, Cursor, Copilot | Partial | No price is known for OpenAI models; most Cursor and Copilot sessions show “—”. | Do not claim cost for all ten tools. |
| GitHub Copilot outside VS Code Chat | Not built | Only Copilot Chat in VS Code (and Insiders) is read. | Inline completions, JetBrains and Copilot CLI are not collected. |
| Gemini CLI account and plan | Not built | Deliberately not read. | — |
| Local git history read | Not built | Planned; its switch is hidden. | — |

**Erasing a person is partial.** Erase anonymises the account, deletes raw activity records and destroys the person's encryption keys, which makes their encrypted uploads unreadable. The plain-text working copies of their sessions stay on the server's disk by design. Until that changes, the site must not say erasing removes all of a person's data.

### 2.4 Not built — do not claim

- Single sign-on (SSO, SAML, OIDC).
- Two-factor sign-in.
- App-level encryption of stored data. Uploads are encrypted in transit; stored sessions are scrubbed but not encrypted by the app. At-rest encryption comes from the operator's disk encryption or S3 on AWS.
- A vendor-hosted (SaaS) version.
- Open-source licence.
- Signed releases.

### 2.5 Business facts the owner must supply

| Website need | Status |
| --- | --- |
| Pricing, plans, trial terms, currency (/pricing, /ai-coding-assistant-pricing) | No pricing, licence keys or seat limits exist in the code. Owner to supply. |
| Certifications (SOC 2, ISO 27001) for /security | None found. Internal security audits exist but are not certifications. Do not claim any. |
| Home page KPI figures and chart data | Placeholders today. Real figures must come from a named deployment with its date. |
| Console screenshots (Org Overview, Team AI Usage, My Scorecard) | Must be taken from a deployment. The owner's own server collects only Claude Code and Gemini CLI by choice, so its screenshots show only those two tools. |
| Customer examples and quotes | Owner to supply, with permission. |
| About page: company story, team, location, contact | Owner to supply. Licence holder is NTGLOBAL SOLUTIONS. |
| Privacy policy and terms | From legal. |
| Demo booking link | Owner to supply. |
| ROI method for /blog/ai-coding-roi | No ROI calculation is visible in the product. The guide can explain inputs Kite Pulse gives (tokens, estimated cost, seat prices, active time) but must not claim an ROI figure. |
| Competitor comparisons (9 pages) | Owner's view of differences; competitor facts checked against their sites. |

## Website corrections

The Product Guide (13 Oct) is out of date in the places below. The site copy, and the 8 designed pages written from it, should change before launch.

**Claims to correct**

| Current claim | Correct wording | Pages affected |
| --- | --- | --- |
| An admin chooses which tools are collected | All ten tools are collected out of the box; an admin can switch any off, or collect token counts only | /features, /integrations, FAQ |
| GitHub Copilot | GitHub Copilot Chat in VS Code (inline completions, JetBrains and Copilot CLI are not collected) | /integrations/github-copilot |
| AI cost by person, project, tool and period, plus a billable view with a markup | Token use by person, project, tool, model and period; estimated list-price cost per tool; monthly budgets per team or project. Drop the markup claim. | Home, /ai-cost-tracking, /features |
| Estimated cost per tool (implies all tools) | Priced for Claude and Gemini models, and for tools that report their own cost (Aider, Cline, Roo Code, Kilo Code, OpenCode). Codex, Cursor and Copilot usually show no cost. Team AI Usage never adds cost across tools; a dollar AI budget sums the priced tools only. Not billed spend. | /ai-cost-tracking, /ai-coding-assistant-pricing, FAQ |
| Plan-limit usage across tools | Claude plan limits (Claude Code): 5-hour, weekly and per-model weekly windows | /plan-headroom, /claude-code-usage-limits, Home |
| Shadow AI: collection shows which tools and accounts are in use | Tool Accounts shows shared accounts for five tools and personal email domains for four (not Copilot); an optional read lists which of six known AI tools are installed per machine. It cannot find AI tools outside that list. | /shadow-ai |
| The account email and plan details are sent | An anonymised account id, the email domain and the plan name are sent by default | /privacy |
| The conversation record, with secrets removed and encrypted | Secrets masked on the computer and again on the server; uploads encrypted in transit. Do not claim encryption at rest. | /privacy, /security |
| Queues work when the network drops | If the network drops, the program picks up where it stopped once the server is reachable | /features |
| Nothing uploads until the Onboarding Wizard is done | No session content uploads until then; only the list of detected folders is sent so the wizard can show it | /privacy, FAQ |
| Every new account changes its password at first sign-in | The first admin, and any account whose password an admin resets, must change it at next sign-in | /security |
| Audit Log: a permanent record | Cannot be edited. Kept indefinitely, or for the period an admin sets (365 days by default) once the server operator enables retention deletion | /security |
| Retention: how long data is kept | Admins set how long each kind of data is kept; deletion runs once the server operator enables it | /security, /self-hosted |
| Export or erase one person's data, or anonymise their account | Export one person's data, or erase it; erasing anonymises the account, deletes raw activity records and destroys their encryption keys. Do not say all their data is deleted: plain-text session copies remain | /privacy |
| Developers can hold their own keys under Settings | Admins issue keys; developers see and revoke the keys issued to them under Me › Account › API Keys. Available once the operator turns the Agent API on. | /docs, /features |
| The same access works through MCP | Move to “available when enabled” until installs switch the Agent API on (Section 2.1) | /docs, /features, FAQ |
| AI Call Log shows every AI call | Every AI labelling call, and every agent question where the Agent API is on | /features, Glossary |
| Answers below the confidence bar go to review | They are stored as “unknown”; Review Labels lists those near the bar, unknown answers and a sample | Glossary |
| Work role shapes how insights are framed | Remove: the output is hidden | /features |
| Risk signals do not name the person | Remove: that page is hidden and does show the person | /privacy, FAQ |
| Org Overview shows idle and offline, and a timeline of each person's day | Team Overview shows who is online and coding now, today against a typical day, who needs attention and each person's project | /features, Home |
| Teams let reports be split by team | Teams feed The Office, Team Review, AI Collaboration and AI Budgets; Reports has no team filter | /features |
| Working style comes from the person's tool mix | It comes from what sessions mostly did (changing files, reading code, running commands, conversation); add “generalist” | /features, Glossary |
| Reports download as a spreadsheet | Company report as CSV or PDF; Plan usage report as Excel | /features |
| Access levels: Admin, Manager, Team member | Admin, Manager, Developer | /features, Glossary |
| Switched-off pages include Trends | Trends is visible again; still switched off: Activity Rhythm, Coaching & Risk, Cost & ROI, Comparisons, Intelligence, Knowledge Base, Tech-Debt Radar | /features |

**Page names to update**

| Old name | Name in the console now |
| --- | --- |
| Overview | Workspace |
| Org Overview | Team Overview |
| Developers | All Developers |
| Company Overview | Organisation Overview |
| Organization Projects | All Projects |
| Error & Command Stats | Work Problems |
| Fleet | Machines |
| Transparency | Privacy |
| Settings (personal) | Account |
| Alerts & Notifications | Notifications |
| Classification Settings, Label Lists, Developer-Level Labels | Classification (tabs: Overview, Settings, Label Lists, Review Labels, Reports) |

**Owner decisions before launch**

- **“Not a ranking tool.”** Organisation Overview has a “Top performers” panel and Team Overview lists “Most active today”. Either soften “does not grade people” on the site, or change those panels.
- **Agent API and MCP.** Decide whether installs switch them on by default. Until then, the website's MCP docs page describes a feature customers cannot reach without server changes.
- **Linux desktop program.** Offer it (from source, no installer or updates) or leave it off.
- **Erasing a person.** Decide whether erase should also delete the plain-text session copies before the site describes it as removing a person's data (Section 2.3).
- **Supply the business facts** in Section 2.5.
