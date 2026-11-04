# Kite Pulse — Complete Product Overview

Oct 28, 2026 · @Neenu

**Kite Pulse shows how your software is really being built now that so much of the work happens in conversation with AI coding assistants.** It quietly gathers the session history that ten popular AI coding tools already keep on each developer's computer. It removes secrets and sends that history to a Kite Pulse server your team runs itself. Everyone then sees a clear, honest picture: who is working on what, how AI tools are used, what they cost, how close people are to their Claude plan limits, where work gets stuck, and what the team is learning along the way.

This overview is for anyone meeting Kite Pulse for the first time: developers, team leads, engineering managers, finance and leadership, and IT. Read it from start to finish for the full story. Use the diagrams to see the product at a glance, and the complete feature list near the end as a reference.

Everything described here is in the product today, except two items marked as coming with the next desktop app release. Where a feature is optional or needs an administrator to switch it on, the text says so.

## 1. Kite Pulse at a glance

**One place to see AI-assisted software development across people, projects and tools, on a server your team controls.**

Kite Pulse has three parts that work together:

- **The desktop program** runs quietly on each developer's Windows or Mac computer. It picks up the conversations people have with their AI coding tools, masks secrets and sends only new activity.
- **Your Kite Pulse server** receives that activity, organises it into sessions and projects, and works out the figures. It runs on your own computer, your own network or your own cloud account. There is no vendor cloud in between.
- **The web console** is where everyone signs in. Each person sees the pages their role allows: developers see their own work, managers see their team, and admins see the whole organisation.

&#91;embedded content: Kite Pulse at a glance · three parts, three roles\]

**In short:** developers keep working exactly as they do today. Kite Pulse turns the record their AI tools already keep into a shared, trustworthy picture of how the work is going.

## 2. The problem Kite Pulse solves

**AI coding assistants changed the unit of work, but the tools we use to understand work did not change with them.**

A few years ago a developer wrote most code by hand, and commits, pull requests and tickets told you most of the story. Today a developer spends much of the day directing an AI assistant: asking questions, reviewing suggestions, retrying, steering and correcting. The real work, and most of the cost, now happens inside those conversations. Commit logs only show what came out the other end.

That leaves blind spots at every level:

| Blind spot | What it looks like today | How Kite Pulse helps |
| --- | --- | --- |
| Output counts no longer tell the story | More commits and pull requests, yet delivery feels no faster. Nobody can say where the time went. | Measures active time, sessions, retries and dead ends from the sessions themselves. |
| AI spend is a black box | Several tools, several subscriptions, one bill. No view by person, project or tool. | Shows token use by person, project, tool, model and period, an estimated cost per tool, and monthly budgets per team or project. |
| Plan limits arrive as a surprise | A developer hits their Claude plan's usage limit mid-task and loses half a day. | Shows how much of each Claude plan limit is used, per person and across the team, worst first. |
| History is scattered | Claude Code, Codex, Gemini CLI, Cursor, Copilot and others each keep their own records in their own format. | Brings ten AI coding tools into one consistent view. |
| Problems surface late | Repeated failures, stuck sessions and overloaded people come up in a status meeting weeks later, or never. | Flags failing commands, repeated retries, stuck agents and plan pressure while there is still time to act. |
| Knowledge evaporates | A hard bug is solved in a chat session, then solved again by someone else next month. | Turns sessions into searchable knowledge records, a map of each product's capabilities, and draft skills from repeated workflows. An optional Organizational Brain lets anyone explore and ask about it. |
| Project status is guesswork | Which projects are active, who is on them, which have gone quiet? | Lists every project with its health, contributors, sessions and last activity. |
| Trust is fragile | Developers fear surveillance tools that log keystrokes or screens. | Reads only the AI tools' own session records, masks secrets, asks for consent first, and shows each person exactly what is collected about them. |

Kite Pulse closes these gaps without surveys, timesheets or extra steps for developers.

## 3. How it works

**A session travels from the developer's computer to the console in six steps, and privacy is built into every one.**

&#91;embedded content: A session's journey · six steps, four privacy checkpoints\]

1. **The developer works as usual.** They use Claude Code, Cursor, Copilot or any of the ten supported tools. Each tool already keeps a history of its conversations on the computer.
2. **The desktop program notices new activity.** It reads only the AI tools' own history, plus folder names and repository addresses so it can tell projects apart. It never opens a project's source files, logs keystrokes, takes screenshots or tracks websites.
3. **Nothing is sent before consent.** On first sign-in, the developer confirms which projects to sync in the Onboarding Wizard. Unless an admin has switched approval off, an approver signs off too. Projects that are switched off are never read.
4. **Secrets are masked and the upload is protected.** Passwords, keys and tokens in known formats are masked on the computer. Session data is encrypted before it leaves, and sent only to your own server.
5. **Your server builds the picture.** It masks secrets a second time, joins each conversation to its project and person, and works out active time, tokens, estimated cost, plan usage, failures and more.
6. **People see what their role allows.** Developers see their own work, managers their reporting line, and admins the whole organisation. The server enforces these limits, not just the screen.

If the network drops, nothing is lost: the program picks up where it stopped once the server can be reached. Only new activity is sent, so nothing is counted twice.

## 4. Who it is for

**Kite Pulse serves everyone who builds software with AI, and everyone responsible for people who do. It works for one developer on one laptop and for a whole organisation on a shared server.**

Each person has one of three access roles: **Developer**, **Manager** or **Admin**. The role decides which pages they see. An admin can fine-tune most pages for each role, for example giving managers a page that is admin-only by default.

&#91;embedded content: What each role sees · default access\]

| Who | The question they ask | What Kite Pulse gives them |
| --- | --- | --- |
| **Developers** | “Is my work being captured? How do I actually spend my time with AI? Am I getting better?” | A private view of their own sessions, work patterns, working style and suggestions to try, plus their own Claude plan usage. |
| **Team leads and managers** | “What is my team working on, where are they stuck, and who needs support?” | Live team activity, project health, collaboration, plan-limit pressure and repeated failures, for their own reporting line. |
| **Executives and finance** | “What are we spending on AI, and on what?” | Token use and estimated cost per tool, seat prices, shared accounts, and monthly budgets per team or project with alerts. |
| **Administrators and IT** | “Is the system healthy, who has access, and what is being collected?” | Accounts and roles, project approvals, tool switches, machine status, infrastructure alerts and an audit log. |
| **The organisation** | “Are we keeping what we learn, or solving the same problem twice?” | Knowledge records, a capability map of each product, draft skills from repeated workflows, an optional Organizational Brain to explore and ask, and an honest record of how work gets done. |

## 5. Feature tour, A to Z

This section walks through every part of Kite Pulse in the order people meet it: capture first, then The Office home page, then each person's own pages, then the team, projects, AI spend and plan limits, work problems, reports and notifications, knowledge and the Organizational Brain, outside AI assistants, and finally administration, privacy and where it runs.

### 5.1 Automatic capture across ten AI coding tools

**What it does.** The desktop program records AI coding sessions in the background, with no manual logging. It supports **Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot Chat in VS Code, Cline, Roo Code, Kilo Code, OpenCode and Aider**. All ten are collected out of the box, and an admin can switch any of them off on the **Tools** page.

**Why it helps.** Most teams use more than one AI tool, often several per person. Kite Pulse puts them all in one consistent timeline, so a developer who uses Claude Code in the morning and Cursor in the afternoon appears in one place, under the right project, without doing anything.

**How it feels.** Invisible. A small tray icon shows the status in colour and offers Open dashboard, View log, Re-enter code and Run diagnostics. The program starts with the computer, keeps itself running and updates itself from your own server.

Good to know:

- **Counts-only mode.** For any tool, an admin can collect only token counts, with no conversations uploaded at all.
- **Projects found automatically.** The program recognises project folders and their repository addresses, so the same repository cloned on two laptops counts as one project.
- **Optional extra reads,** each off until an admin turns it on: a project's current branch name, the frameworks it uses, its notes (such as README and decision records), sleep and network-loss events, installed AI tool versions, the Claude Code skills and MCP servers on a machine, the Copilot plan name, and a background refresh of Claude Code plan usage.

### 5.2 The Office: your team's live home page

The Office is the first page everyone sees after signing in, whatever their role. It shows the whole team at work, live, as a friendly office you can look around.

**Who it is for.** Every person opens The Office. Developers see their own desk and their colleagues. Managers and admins also get a live picture of the team they look after.

**Five ways to look.** One button group at the top switches the view:

- **3D office** is the default on a desktop computer: rooms of desks with an AI agent at each one.
- **Map** shows the same company as a flat map of rooms around the Brain, with no 3D needed.
- **List** is a simple list of people and desks. Phones and small windows open here.
- **Headroom** (managers and admins) is a board of everyone's Claude plan usage and when each limit resets.
- **Brain** appears when the optional Brain is switched on, and always for admins, who can switch it on.

**Full screen** turns The Office into a wall screen without menus, made for a TV or a meeting room. **Light and Dark** show a daylight or an evening office, and each browser remembers the choice.

**Live, without pressing refresh.** When something changes, open pages update within seconds and the 3D office redraws itself. A small badge says **Live**. If the live link drops, the page refreshes every 15 seconds instead, and the badge says so: **Live · every 15 s**. It reconnects on its own. The Office is as fresh as each computer's latest upload, and “online” means the desktop program checked in within the last 10 minutes.

**Each figure is an AI agent, not a person.** The figure at a desk is the person's AI agent, and its posture follows what the agent is doing right now:

- typing, reading, watching, supervising its sub-agents, or waiting;
- **waiting** means the agent replied and nothing has happened for two minutes, a good sign it is waiting for its person;
- it heads to the **lounge** when its person is away, after 15 idle minutes, or when it reaches a plan limit;
- a **stuck** agent sits head down, hands off the keyboard.

Agents walk in and out as people come online and go offline. A parcel flies off when someone pushes code, and a page flies into the Brain when a project's notes change. **Sub-agents** appear as small objects beside the agent that started them.

**One marker per desk** flags what needs a look: attention “!”, a thought cloud when stuck, at a plan limit, near a limit, waiting, syncing, or “Update” when the desktop program is out of date. Zoom in to read each agent's current task on its name tag. Click a room to bring the camera to it.

**Click a desk** to open its side panel. Everyone sees the name, presence (working, online, away, offline or not connected) and AI tool. For yourself, the people you manage, and admins, the panel goes further:

- project and branch, and the current task with the first line of the request and the live step, such as “editing a file”;
- an “AI stuck” line saying how many times the agent hit the same problem and for how long, with plain reasons;
- each sub-agent's kind, model, run time and current step; finished ones fade after 10 minutes;
- plan headroom (for people allowed to see plans), sync status, and an “Update” line for an old app;
- today's figures: sessions and run time, tokens, estimated cost, tool calls and failures, and times stuck. Cost on someone else's desk is shown to admins only.

**What the agent did** opens the latest session as numbered steps: tools used, files touched, commands, tests, errors and stuck stretches. It never shows message text.

**Three tabs** sit beside the office:

- **Activity** is a live feed of the last 24 hours: sessions started, paused and finished, tasks done, commits, agents stuck and unstuck, project requests and approvals, notes updated, and sub-agents started and finished. It also shows who came online, went away, is back or went offline. Admins see alerts here too.
- **Tasks** is a board of work in progress, stuck, waiting, paused, failed and done. Each counter filters the board. Waiting includes projects awaiting your approval and uploads that need attention. Click any item to open its desk. Admins also see the processing queue, failed jobs and open alerts.
- **Office** gives the figures for the whole office or one team: agents, working, stuck and waiting, sessions and commits today, plan headroom counts, how many project notes the Brain holds, and the connectors and skills used this week.

A **Connected** strip shows the AI tools, MCP servers and code hosts in use. For admins, **team suggestions** propose teams from who already works together, and one click creates the team.

**Find people fast.** A **team picker** narrows the office to one project team, with its own working, online and stuck counts. **Filter tiles** show Working now, Online, Needs attention or Not set up. The side panel can fold down to icons.

**A nudge when an agent is stuck.** After 30 minutes stuck, an “AI agent stuck” notice goes to the person and their manager. Exact “needs your approval” and “waiting for you” signals from Claude Code itself are coming with the next desktop app release.

**Ask a teammate's agent.** With the optional Brain switched on by an admin, you can ask a colleague's agent about their synced work on projects you can both see.

**Who sees what.** Presence is shared with everyone: name, AI tool, and whether someone is online or away. Everything else, including stuck and plan-limit detail, is shown only for yourself, the people you manage, and admins. An admin can go further on Roles & Permissions and stop a role seeing other people's desks. The Office lives in the console only; agent API keys cannot read it.

**Why it matters.** The Office turns “how is the team doing?” into a glance. A lead sees a stuck agent while there is still time to help, not at next week's stand-up. Developers see their own work in motion, and nobody fills in a status update.

### 5.3 Your own workspace

Every person, whatever their role, has private pages about their own work.

- **Workspace** answers the first question everyone asks: is my work being collected? Project by project it shows what is detected, waiting, syncing, processed or needs attention. It also shows the person's own Claude plan usage.
- **Upload status on Workspace** shows any uploads being retried, with the reason and the computer involved, and how much is still waiting on each computer. Newcomers also see their next setup step.
- **My Scorecard & Insights** is a personal report led by a short Top 3 to act on list. Each insight gives a verdict, why it matters, what to try and the evidence behind it. When there is too little data, it says not enough data rather than guessing.
- **Productivity tiles** on My Scorecard show lines added and changed, and how many messages you and the AI sent, each against the previous period.
- **Verification signal** on My Scorecard shows how often you reviewed or tested the AI's output, with counts of checks and corrections. It reads “Not available” until labels exist (needs AI labelling).
- **Work-pattern facts** show peak hour, busiest day, longest streak, deep-focus sessions of an hour or more, longest session, most sessions running at once and the share of short bursts.
- **Working style** describes how a person works with AI: builder, explorer, debugger, communicator or generalist, worked out from what their sessions mostly did.
- **Private prompt statistics**, such as a person's most repeated prompt and their reply pace, are shown only to that person.
- **My Activity** shows when, for how long and with which tools a person worked. **My Sessions** lists every session with a summary and a detailed view of what happened in it.
- **My Sessions filters** narrow the list by tool, model and session type (main, sub-agent or compacted). The page also shows how your time splits between main sessions and parallel ones.
- **Session labels** appear as badges on My Sessions, and a label filter shows only the sessions you want. Some labels come from fixed rules and need no AI; the rest come from the AI model (needs AI labelling).
- **Session Summary** gives a quick digest of a session without any AI: its title, its outcome, whether the work was checked, and whether anything usable came of it. It also flags security-sensitive edits and commands that kept failing.
- **Session Playback** replays a session turn by turn, with a timeline that jumps to any moment. For Claude Code, a sub-agent's own conversation opens right under the step that started it. Secrets stay masked.
- **What the agent did** sits on every session page. It lists every step the AI took, in order: tools used, file names, kinds of command, tests, errors, refused or interrupted steps, pauses and stuck stretches. It never shows message text. Routine steps fold away, and errors always show.
- **Segments and Labels** on the session page show the session's separate parts and its labels (labels need AI labelling). Every tab links a sub-agent to its parent session and back.
- **Notices about your own work** arrive in the bell. You are told when one of your Claude plan windows is used up and when it resets, when your AI agent has been stuck on the same problem for 30 minutes or more, and when your Claude Code is older than the current stable release.
- **Your notifications inbox** opens from the bell with **View all**, so every notice you have received is in one list.
- **My Projects, Pending Requests and Project Detection** let a person confirm, rename, split or remove their projects and follow their requests.
- **Privacy** lists every piece of data collected about the person, whether it is switched on, and who can see it.
- **Account** holds profile, password and any agent keys issued to the person.
- **The Office** is everyone's live home page, described in full in section 5.2 above.
- **Needs attention** gathers anything that wants the person's action, and **Help / Glossary** is always one click away.

**Why it matters.** Developers get a private mirror of their own work. They can spot a time sink, a flaky test setup or a habit worth changing, without anyone else having to point it out.

### 5.4 Team and organisation views

- **Team Overview** is a live control room: who is online and who is coding right now, active time and sessions today against a typical day, who needs attention (an upload failing, a backlog, an old app version) and each person's current project. It refreshes every 30 seconds.
- **All Developers** lists everyone in scope. Opening a person shows the same report they see themselves, without their private fields. All Developers exports the whole roster to Excel.
- **Exports** on a developer's page download one person's sessions for any period as CSV and their projects as Excel.
- **Session labels** also appear for admins on a developer's Sessions tab, with the same label filter.
- **Agents in parallel**, on a developer's page, shows how many AI agents and sub-agents are working right now and whether each is working or waiting, with a lane chart for any past day.
- **Detection and Collection tabs** on a developer's page show Work Problems and Data Collection for that one person.
- **Profile facts**, on a developer's page, builds a picture from AI labels: technologies, business areas, new or growing skills, skills in steady use, and how much work they hand to AI. It is admin-only by default (needs AI labelling).
- **Tenure & Departure**, a tab on a developer's page for admins, shows how long a person has been with the organisation, their team and each project, with a departure report (see 5.11).
- **Organisation Overview** (admins, by default) gives one company-wide picture: active people and hours, sessions, commits, project health, working styles, tools and languages.
- **Summary, Activity Overview and Trends** show how activity is changing over time.
- **Trends** adds 12- or 26-week charts of completion rate, win rate, stuck share, friction and the share of changes that were checked, for the organisation, a team or a project. Figures are pooled, never per person, and a week with too little data shows a gap. The page itself needs no AI; its label measures do (needs AI labelling).
- **Collaboration** shows which projects several people work on, who contributes and how many sessions each spent there.
- **Teams** records team membership with start and end dates, so history stays accurate when people move.
- **Leave & On-Call** records holidays and duty rotas, so a week of leave is not mistaken for disengagement.
- **Blocker Board, Team Review, Workflows & Pain Points and AI Collaboration** (admins by default, and grantable to managers) look at the team as a group.
- **Blocker Board** shows each recurring cause of lost time as a card with a suggested action, never a person. It stays empty until an admin switches the suggestion rules on in Classification › Settings, with “Switch all approved on” (needs AI labelling).
- **Team Review** shows one team's week: the middle value and middle range for completion, win rate, friction and checked changes, set against last week, plus deferred work and the mix of work. It never names or ranks a person, and small teams are held back (needs AI labelling).
- **Workflows & Pain Points** shows what repeats, such as common work shapes, repeated prompts and commands. It also shows what slows work down: inefficiencies, the longest sessions, the most-touched files and where people got stuck, week by week, plus quality checks.
- **AI Collaboration** follows the organisation and each team month by month: friction per 100 messages, how often changes were checked, how often AI edits are accepted, and who led the work. A team needs at least three people to appear (needs AI labelling).
- **Who sees whom.** A manager sees only their own reporting line, including indirect reports. An admin sees everyone. The server enforces this.

**Why it matters.** Leads see where the team stands today and how it is trending over weeks, as a group rather than a ranking. Problems show up as shared causes to fix, not people to blame.

### 5.5 Projects

- **All Projects** lists every project with its health (active, stable or dormant), sessions, contributors and last activity. It also has Phase and Open blockers columns. Each project has its own page with a summary card.
- **Add project** on All Projects adds one that was not detected, and approvers approve it in the same step. Admins can pause or delete several projects at once.
- **Project summary card** shows stability, activity trend, contributors, tokens, phase, risk, open blockers, duplicate work and knowledge records. Each figure links to its own section. Some figures need AI labelling.
- **Duplicate work and Risk and phase** sections on a project page are admin-only by default (needs AI labelling).
- **Project sessions** on the project page show each session's labels as badges, with a label filter, for admins. Rule labels need no AI; the rest come from the AI model (needs AI labelling).
- **Project notes**, on the project page, show the project's own written knowledge: its CLAUDE.md, AGENTS.md, README and decision records, with every version kept. Open one to read its text, with secrets masked, and see what changed. Every read is recorded. This is off until an admin switches on the project notes read for the desktop program. People with knowledge access can read notes, which means admins by default.
- **Project actions** let you merge or unmerge projects, change the tracked root folder, split a project, pause syncing or delete its data. Deletion waits through a grace period, set on Detection Rules, and can be cancelled until then. People without the right access send a request instead.
- **Onboarding Approvals** is where an approver confirms a new developer's first list of projects. It is on by default and can be switched off. Each developer's list is split into four parts: setup approval, new projects, syncing and not syncing.
- **Project Approvals and Request History** handle later changes, such as adding or removing a project.
- **Duplicate Detection** spots folders that are really the same repository on different machines and offers to merge them. It also suggests splits when one folder holds several projects.
- **Removed Projects** keeps paused and deleted projects in one place. Managers can view it; only admins can resume a paused project.
- **Project Mapping** helps keep projects correctly organised.

**Why it matters.** A project list that matches reality is the foundation for every other figure. Kite Pulse keeps it accurate with very little effort.

### 5.6 AI usage, cost and budgets

- **Team AI Usage** shows token use per developer, tool, model, project and day, for any period. Its tabs are Overview, Consumption, Models, Projects, Tools & accounts, Agent features and Plan headroom.
- **Token pace line** sits under the daily-tokens chart. It shows the average tokens per day over the last 14 days, where that pace leads over the next 30 days, and a marker on any day that used at least twice the usual amount. It counts tokens only, not money, and is for managers and admins.
- **Estimated cost per tool** multiplies tokens by each vendor's published list price. Claude and Gemini models are priced. Aider, Cline, Roo Code, Kilo Code and OpenCode report their own cost, and Kite Pulse uses it. Cost is labelled as an estimate, “not billed spend”, because many developers are on flat subscriptions.
- **AI Budgets** let admins set a monthly budget per team or per project, in tokens or estimated dollars, with alerts at 80% and 100%.
- **Hourly Rates & Seat Prices** let admins record what each tool's seats cost, and an hourly cost for each role level, so prices sit beside usage. Hourly rates are set per role level, never for a single person. Every rate is dated and every change is recorded.
- **Models** shows which models people use, how adoption changes over time, and which models each project relies on.
- **Agent features** shows which Claude Code agent features sessions used, such as sub-agents, background commands, plan mode and MCP tools.
- **Tool Accounts** counts the separate accounts each tool is used under and marks accounts shared by more than one person. It also shows plan tier and email domain, which reveals personal accounts used for work. It covers Claude Code, Codex, Cursor, OpenCode and GitHub Copilot.

**Why it matters.** Finance gets a view of AI use by person, project and tool instead of one opaque bill. Leaders see which tools and models are really used, which seats sit idle or are shared, and whether a team is on track for its budget. The pace line shows early where token use is heading and flags an unusual day.

### 5.7 Claude plan limits (Plan headroom)

- **Plan headroom** shows who is close to a Claude plan limit, worst first: the 5-hour window, the weekly window and each model's weekly window. “Near” means 80% or more; “at limit” means 100%. Old readings are flagged, not hidden.
- **Your own figures.** Every developer sees their own plan figures on their Workspace.
- **Plan panels name the Claude account** each figure belongs to. When a reading is old, they say why, for example the refresh is off, the desktop app is too old, the developer opted out, or Claude Code has been idle. Figures that arrived live are tagged as such.
- **“Plan limit reached” notice.** The person and their manager are told when a window is used up and when it resets (see 5.10).
- **Claude Code version check** compares each developer's Claude Code version with the latest release and flags anyone behind. A developer whose Claude Code is older than the current stable release gets a “Claude Code out of date” notice, which clears once they use a newer build.
- **Plan usage report** gives plan usage per developer and per Claude account for any period up to two years (see 5.9).
- **Fresher figures, optionally.** By default the figures are as fresh as the last time Claude Code saved them. An admin can switch on a background refresh that keeps them current without using any tokens. The admin chooses how often it runs, from every 5 minutes to every 6 hours (hourly by default), and each developer can opt out on their own machine.
- **Plan reading history** is kept for as long as admins choose, from 30 days to two years (one year by default). Kite Pulse asks for confirmation before older readings are deleted.

**Why it matters.** Hitting a plan limit mid-task costs hours. With Plan headroom a lead can see on Thursday that two people are past 90% of their weekly limit and move a large task to Monday. And when a window does run out, the person and their manager hear about it straight away, with the reset time.

### 5.8 Work problems and insights

- **Work Problems** (admins by default) finds failing commands, error messages and repeated retries across the team using fixed rules, with no AI involved. It groups them by severity, suggests actions, and shows which developers are most affected.
- **Insights** on each person's scorecard explain what was found, why it matters and what to try. Insight rules can be reviewed and tuned by admins.
- **Insights Catalog**, on Insight Rules, explains every insight for each kind of person. It says what the insight means and who may see it: the person themselves, their manager or an admin.
- **“AI agent stuck” notice.** The person and their manager are told after 30 minutes stuck (see 5.10), and “What the agent did” then shows the stuck stretch step by step.
- **Blocker Board** turns recurring causes of lost time into cards with a suggested action, never a person (needs AI labelling; see 5.4).

**Why it matters.** Repeated failures are often a broken test setup or a confusing tool, not a person's fault. Seeing them early turns a hidden time sink into a one-time fix. A stuck agent is caught in half an hour, not at the end of the day.

### 5.9 Reports and scheduled reports

- **Company report** summarises any period and compares it with the one before. Managers and admins can view it; downloading it as CSV or PDF is for admins by default.
- **Plan usage report** covers Claude plan usage for any period up to two years, with weekly, 5-hour and per-model peaks, extra usage and a day-by-day chart. Managers and admins can view it; downloading it as Excel is for admins by default.
- **Scheduled reports** email the company report or one developer's report daily, weekly or monthly, as PDF or CSV, with a preview and a history of every send. Admins set them up.

**Why it matters.** Leaders get the picture on a schedule without asking anyone to compile it, and admins decide who may take figures out of the console as files.

### 5.10 Notifications and alerts

The bell in the console and email tell people when something needs their attention.

- **Notices for developers and managers.** Three notices come to people about their own work, with no setup:
  - **Plan limit reached**: one of a person's Claude plan windows is used up. The person and their manager are told which window and when it resets.
  - **AI agent stuck**: someone's AI agent has been stuck on the same problem for 30 minutes or more. The person and their manager are told, with the project name.
  - **Claude Code out of date**: a developer's Claude Code is older than the current stable release. The developer is told, and the notice clears once they use a newer build. Admins see it on Alerts, and an admin can add managers.
- **Notifications settings** let admins choose who is told what, turn email on or off and send a daily digest. Notifications reach people automatically.
- **Slack channel** sends server alerts to a Slack channel, with a Test button. It is off until an admin switches it on in Notifications settings.
- **Delivery history** keeps a log of every notification sent.
- **Infrastructure checks** run automatically and raise alerts when processing stalls, memory or disk runs low, a collector goes silent, collectors fall behind on versions, or sign-ins keep failing.
- **Advanced thresholds** let admins change the levels at which health checks raise an alert.
- **Infrastructure** shows one tile per area, such as processing, memory, disk, the database, silent collectors and the email relay.
- **Alerts** lists every infrastructure alert. Each one moves through Open, Acknowledged, In progress and Resolved, and all admins share the same list. Acknowledging an alert stops repeat reminders. The list downloads as Excel.
- **How admins hear about alerts.** Admins get the bell, an email for each critical alert and a daily digest of warnings. Each admin can mute their own email. Email works once the server operator has set up mail.

**Why it matters.** The right person hears about a problem while there is still time to act: a developer about their own plan limit or stuck agent, a manager about their team, and admins about the system itself.

### 5.11 AI labelling and knowledge (optional)

Kite Pulse works fully without any AI service. These features add a layer of understanding on top, and the AI-powered ones stay off until an admin sets them up.

- **Work classification** uses an AI model to label each piece of work, for example by type of work (building, debugging, refactoring, testing, planning, docs and more) and by whether the session succeeded. Admins set it up on the **Classification** page with an AI provider key and a monthly spending cap.
- **Admin approval first.** Every label list must be approved by an admin before it runs. Fact rules work out simple facts such as “tests ran” with no AI and no cost; they are on by default. Classification Overview and Reports show labelling spend, coverage, labels awaiting review and how each model scored.
- **Confidence bar.** Answers below a set level of certainty are stored as “unknown”, and **Review Labels** lets people check and correct answers near the line.
- **AI Call Log** records every AI labelling call with what was sent and received, secrets masked, for full transparency.
- **Knowledge Records** (Insights › Knowledge, admins by default) keep what the organisation has learned, quoted from real messages and linked to the sessions and commits they came from. Records are written by AI labelling, so this page fills once an admin has approved and run its knowledge label list.
- **This week**, a tab on Knowledge Records, is the knowledge log: the week's new records grouped by kind (requirements, rules, decisions, findings and open questions).
- **Knowledge captured this week** is a card on the Insights Summary, on each project page and on the Capability Map, so new learning is visible where people already look.
- **Coherence**, another tab on Knowledge Records, finds duplicate records. It also flags records that contradict each other or may be out of date, for example one said to be fixed that was later reopened, or one whose files have changed since.
- **Capability Map** describes each project in plain product terms (modules, capabilities, scenarios) so work and knowledge sit in the right place. It keeps a full change history, and every edit is recorded in the audit log. No AI model is used.
- **Capability ownership**, inside the Capability Map, shows for each capability who edited its files and who read them, each person's share of the edits, how many people really know it (the “bus factor”) and a hand-over hint. Owners are found automatically every hour or named by an admin, and each detected owner can accept or decline. No AI model is used.
- **Tenure & Departure**, a tab on a developer's page (admins), shows how long a person has been with the organisation, their team and each project. Its departure report lists the capabilities at risk, the records they own, their open work and the files only they edited. Admins can send knowledge-capture requests from ready-made templates. It shows facts only and never ranks people.
- **Session Graph** links sessions that look alike and groups them, refreshed daily. No AI model is used.
- **Skill Candidates** turns repeated workflows into draft Claude Code skills for a person to approve or reject. No AI model is used.
- **My Day** shows a person's own day built from their labelled work, once AI labelling is on.

**Why it matters.** Knowledge usually leaves with the person who found it. These pages show what was learned, who holds it and where only one person knows a part of the product. A lead can plan a hand-over before someone moves on, not after.

### 5.12 The Organizational Brain (optional)

The Organizational Brain brings together what your organisation knows about its people, projects and documents, and lets everyone explore it and ask about it. It is off until an admin switches it on, with one click: **Switch the Brain on** on the Brain tab, or under Brain › Governance › Settings. Only admins can switch it, and every change is recorded.

People reach it through a **Brain** tab in The Office's view switch. Once it is on, every role sees the tab. While it is off, only admins see it, so the switch is always one click from home.

The Brain only ever uses what the person asking is allowed to read. Anything hidden from them is left out entirely, not just blurred.

- **Graph** is an interactive map of how the company connects: departments, people, projects, project teams, agents, documents, capabilities and AI tools. It opens full screen, and it is the Brain view on The Office's wall screen. No AI is used.
- **Documents** holds your policies, playbooks, SOPs and notes. Admins and managers upload plain-text or Markdown files, up to 256 KB each, for the whole company, one department or one project. Secrets are masked before anything is stored, and everyone reads what is shared with them.
- **Agents** are focused ways of asking the Brain. Four come built in: People & org, Projects, Knowledge & documents, and SOPs. Admins and department leads can add their own, such as an HR policy helper. Agents only read and answer, and they never widen what a person can see.
- **Governance** is for admins and department leads. For each department it shows what the Brain holds, who may read it and who read it through the Brain recently. Admins also set the monthly budget, the AI model, how long the access log is kept (180 days by default) and how long a departed person's Brain conversations are kept (30 days by default).
- **Person pages** show what the Brain knows about one person, in five tabs: Overview, Work, AI Context, Compliance and AI Access. AI Context shows the exact text the Brain would give an AI about them. Everyone edits their own skills and location, and managers and admins set titles and responsibilities. Colleagues see only a directory line. Open it from **Brain profile** on a developer's page, or **My Brain profile** under Account › Profile.
- **Project context** appears on the project page once the Brain is on. It holds a project's objectives, strategy, status note and links, shared with the project, its department or the whole company.
- **Ask a teammate's agent** is a button on a colleague's desk in The Office. It answers questions about that colleague's synced work from the last 14 days, on projects you can both see. It never uses the text of their messages. Without an AI key, the answer is a plain list of their work items. The colleague sees every question asked.
- **Who asked my agent**, on the Privacy page, shows each person every question colleagues asked their agent. Anyone can pause their own agent there.
- **Chat** lets people ask anything in plain words, once the server operator provides an AI key (the key settings are not in the console menu today). Every answer cites its sources: knowledge records, project context, people profiles, documents and connected Jira, HubSpot or Slack items. Material is checked against the person's permissions before anything goes to the AI, and every question has secrets masked and is recorded.
- **Monthly budget.** Chat runs within a monthly budget, $20 by default; an admin can change it, or set 0 for no cap. Once the budget is used up, questions are refused before any AI call is made. Without a key, the Chat tab is hidden and the Brain opens on the Graph.

**Works with no AI at all:** switching the Brain on, the Graph, Documents, person pages, project context, setting up agents, Governance, and Ask a teammate's agent as a plain list of work items.

**Why it matters.** A new joiner should not need a week of asking around to learn who owns what or where the release checklist lives. The Brain puts the organisation's people, projects and documents in one place anyone can explore. It answers only within each person's own access, and it shows people who asked about their work.

### 5.13 Connecting your own AI assistants (optional)

Teams can let an outside AI assistant, such as Claude, ask Kite Pulse questions or draft reports from its data. This is turned on by the server operator. An admin chooses whether keys only ask questions (Chat mode) or can also read data directly.

- **Agent API keys** are issued by admins for a named person. Each key has its own permissions, an expiry date and optional limits, and never sees more than its owner can see.
- **Access mode** is chosen by an admin. In Chat mode, AI tools can only ask questions, and Kite Pulse's own assistant answers them. In Direct access, they can also read data within the key owner's view.
- **A separate AI provider key** pays for questions answered by the assistant. It is kept apart from the labelling key, so the two costs never mix.
- **What a key can read.** In Direct access, a key can reach almost everything the console shows, always under its owner's own permissions. That includes team review, the blocker board, security watch, My Day, plan history, the costliest turns, model splits, effort per branch, data quality, how quickly newcomers ramp up, file hotspots and churn, tool failure rates and cost reconciliation. About 115 read tools are offered over MCP.
- **Machine interruptions.** A key can also show how much time sleep, crashes, restarts and lost network cost. This needs the optional sleep and network read switched on by an admin.
- **Reading what the AI said.** A separate permission lets a key read what the AI said in a session, with secrets masked. An admin issues it only after acknowledging the risk. Every read is recorded, and it is never offered over MCP.
- **MCP support** lets assistants that speak the Model Context Protocol, such as Claude Code, Cursor and VS Code, connect with a ready-made setup.
- **Try a question** lets an admin type a question and see exactly what an AI tool would get back.
- **Key tabs** show keys by person, all keys, usage and a full request log.
- **Agent Activity** logs every request made with a key. Each person can see and revoke the keys issued to them under Account.

**Why it matters.** People can ask their own AI assistant questions about the team's work in plain words, and get answers built from real figures, without anyone seeing more than they already may.

### 5.14 Administration and security

- **Sign-in** with email and password, a required password change at first sign-in for the first admin and after an admin resets a password, strong password rules, lockout after repeated wrong passwords, and password reset by email.
- **Login & Registration** offers admin-created accounts, sign-up by company email domain, or open sign-up with admin approval. Accounts can also be kept in step with Microsoft Entra ID or Okta through user sync; sign-in itself stays email and password.
- **User sync** lets Microsoft Entra ID or Okta create, update and deactivate Kite Pulse accounts automatically. It is off until an admin switches it on in Login & Registration and creates a sync token, shown once. It never sets roles and never touches admin accounts.
- **Accounts & Roles** creates accounts and sets each person's role, job role and manager. Account management can be delegated to a manager for their own team. Admins can also approve or reject pending sign-ups, show or reissue a person's client code (starting KP-), and revoke an account.
- **Roles & Permissions** is a grid of every page and action for every role, so admins decide exactly who sees what.
- **Export or erase** a person's data on request. Erasing anonymises the account, removes their raw activity records and destroys their encryption keys. Both actions are recorded.
- **Audit Log** keeps a record of sign-ins and sensitive admin actions that cannot be edited.
- **Leaked Credentials** (under Settings, for admins) lists passwords and keys found in AI conversations, masked, each with a status to track until it is dealt with. The main list fills when the server operator runs a scan.
- **Security watch** adds two more tabs to Leaked Credentials. **Unchecked sensitive changes** lists security-sensitive changes the AI made that nobody tested or reviewed. **Pasted secrets / personal data** lists prompts where someone pasted a password or personal data. Both show counts and identifiers only, never the text (needs AI labelling). Alerts for them are turned on by the server operator.
- **Retention** lets admins choose how long each kind of data is kept. Its deletion schedule is a preview until the server operator turns real deletion of session data on. Agent request logs and plan readings are cleaned up automatically.
- **Kite Pulse app reads**, a tab on Retention, is the one place an admin switches on each optional read by the desktop program.
- **Detection Rules** set how problems are spotted and whether new projects need confirmation.
- **Machines** shows every computer running the desktop program, its version, update status and log. **Installed tools and events** shows the AI and developer tools on a computer and its sleep and network events, once that optional read is on.
- **Data Collection and Processing** show whether each machine is uploading and how the processing queue is doing.
- **Set app version**, on Tools, is where an admin publishes desktop program updates.
- **Generation rate** shows how fast AI replies arrive, in tokens per second, on session pages and usage sections. It covers Claude Code only. It is off until an admin switches it on in Tools, and each developer opts in.
- **Server Storage** shows how much space is used, by person and project.
- **Connectors** link Jira, HubSpot, Slack, GitHub, Confluence, Google Drive and Notion to projects.
- **Agent Setup** shows the Claude Code skills, commands, agents and MCP servers installed across the team's machines (with the optional read switched on). Plugins are coming with the next desktop app release.
- **Configuration, Maintenance, Setup checklist and Organisation Name** help admins run and tidy up the installation.

**Why it matters.** Admins control who sees what, can show what happened and when, and can spot a leaked password or a risky unreviewed change before it becomes an incident.

### 5.15 Privacy and trust

Kite Pulse only works if developers trust it, so privacy is built into what it collects and who can see it.

- **Reads session records, not your screen.** It reads only the AI tools' own histories, folder names and repository addresses. It does not open source files, log keystrokes, take screenshots or track websites. Optional reads, off until an admin turns them on, can add a project's own notes and package lists. Session records can include parts of code the AI read or wrote, which is why secrets are masked.
- **Secrets masked twice,** on the computer and again on the server.
- **Protected in transit.** Session data is encrypted before it leaves the computer and travels only to your own server.
- **Consent before sync.** Nothing from a session is sent until the developer confirms their projects.
- **Tool accounts disguised by default.** Only a scrambled account identifier, the email domain and the plan name are sent, never the email address.
- **Private fields stay private.** Prompt statistics are shown only to the developer. Managers who do not work on a project see folder labels, not full paths.
- **The Privacy page** shows each person every data point collected about them and who can see it.
- **AI is opt-in.** Nothing goes to an AI provider unless an admin turns AI labelling on, the Organizational Brain is given an AI key, or outside AI assistants are set up in Chat mode with their own provider key.

### 5.16 Where it runs

Kite Pulse is self-hosted: your data stays on infrastructure you control.

- **One computer, one person** — everything on one machine with a single command.
- **A team pilot** on one machine on your local network.
- **An Ubuntu server** set up by one script, with free HTTPS certificates that renew themselves.
- **Your own AWS account,** set up by one script that shows its plan and asks before creating anything.
- **Server only,** with the desktop program on each developer's computer.

The desktop program runs on Windows and macOS (Apple Silicon and Intel). The console works in any modern web browser.

## 6. How the features connect

**Every feature feeds one loop: capture what really happened, understand it, act on it, and see the result in the next week's figures.**

&#91;embedded content: How the features connect · one loop, four stages\]

- **Capture** gives every other feature its raw material: sessions from ten tools, linked to the right person and project, with consent and secrets masked.
- **Understand** turns sessions into figures and findings. The Office, personal insights, Team Overview, Plan headroom, Team AI Usage, Work Problems and project health all read the same sessions, so they always agree with one another.
- **Act** is where people use what they see. A developer fixes a flaky test setup. A lead moves heavy work away from someone near their plan limit. An admin merges duplicate projects or sets a budget. Finance spots a shared account.
- **Learn and share** keeps the gains. Reports and scheduled emails share the picture. Knowledge records, the capability map and skill candidates keep what was learned, and the optional Organizational Brain makes it easy to find and ask about. Notifications bring the right people in at the right time.

The next week's sessions show whether the action worked, and the loop starts again. That is why Kite Pulse gets more useful the longer a team uses it.

## 7. Kite Pulse in real life: one week

**The same week looks different from every seat, and Kite Pulse helps each person make a better decision in it.** The names and numbers below are illustrations, not customer results.

| When | Who | What they see | What they do |
| --- | --- | --- | --- |
| Monday, stand-up | Priya, team lead | Team Overview: four people coding, one with a failing upload, two working on the same service. | Pairs the two who overlap and asks the third to check their connection. |
| Monday, afternoon | Ben, developer | Workspace shows one new project detected but not yet syncing. | Confirms it in My Projects, so that work is captured from today rather than missing from his record. |
| Tuesday, morning | Priya, team lead | The Office on the meeting-room screen: one agent sits head down with a thought cloud. Its desk says it hit the same problem five times in 15 minutes. | Opens “What the agent did”, sees the same failing command repeated, and sits down with the developer before the morning is lost. |
| Tuesday, midday | Sam, admin | Duplicate Detection: “payments” and “payments-api” share one repository address. | Merges them. The project now shows its four real contributors in one place. |
| Tuesday, afternoon | Ben, developer, and Priya, team lead | A “Plan limit reached” notice: Ben's weekly Claude window is used up, with the time it resets. Priya gets the same notice. | Ben switches to review and small fixes until the reset. Priya hands his urgent ticket to someone with headroom. |
| Tuesday, late afternoon | Ben, developer | The Brain tab: the Graph shows Ana works on the billing project, and Documents holds the team's release SOP. | Reads the SOP, then clicks Ask Ana's agent to see what she has worked on in billing lately, before asking her one sharp question. |
| Wednesday, morning | Priya, team lead | Plan headroom: two of five developers are past 85% of their weekly Claude limit. | Moves a large migration to the following Monday and gives smaller tickets to the others. No one loses a day to the limit. |
| Wednesday, midday | Ana, developer | My Scorecard: most failed commands came from one repeated test command, retried six times by the AI. | Fixes the test setup once. Next week her failure rate drops. |
| Wednesday, afternoon | Ana, developer | An “AI agent stuck” notice: her agent has been stuck for 30 minutes on a task she left running. | Opens her desk, reads the plain reason, stops the run and restarts it with a clearer request. |
| Thursday, morning | Lee, engineering manager | Work Problems: the same build error affects three developers on two projects. | Raises it with the platform team as one fix instead of three separate struggles. |
| Thursday, midday | Finance | Team AI Usage and Tool Accounts: one Cursor account shared by two people; another team at 80% of its monthly AI budget. | Buys the missing seat and talks to the team about the budget before it runs out. |
| Thursday, afternoon | Sam, admin | Capability ownership: one capability has been edited by only one person, who moves teams next month. | Opens that person's Tenure & Departure tab and sends a knowledge-capture request, so the hand-over happens before the move. |
| Friday | Ben, developer | Workspace and My Sessions: every project synced; one session went in circles for two hours. | Reviews what went wrong and writes himself a better prompt for next time. |
| Friday, end of week | Leadership | A scheduled company report arrives by email. | Sees active time, sessions and project health against last week, without asking anyone to compile it. |

**The thread through the week:** nobody filled in a timesheet or survey. Every decision came from what actually happened in the sessions.

## 8. Benefits by audience

**Kite Pulse gives each level of an organisation a different kind of clarity, all from the same honest source.**

### For individual developers

- **See your own work clearly.** Your active time, sessions, projects and patterns in one place, across every AI tool you use.
- **Get better, privately.** A short Top 3 list of things to try, with the evidence behind each.
- **Never lose credit for your work.** Workspace shows that every project is captured, so work done with AI is on the record.
- **Avoid plan-limit surprises.** Check your own Claude plan usage before starting a long task.
- **Stay in control.** You choose which projects sync, and the Privacy page shows exactly what is collected and who sees it.

### For development teams

- **One shared picture** of who is working on what, without status meetings or spreadsheets.
- **Spot overlap early.** Collaboration shows when several people are working in the same place, so they can talk before they collide.
- **Fix the system, not the person.** Work Problems and the Blocker Board point at recurring failures and causes of lost time across the team.
- **Keep what you learn.** Knowledge records, the capability map and skill candidates turn one person's discovery into the team's habit.

### For team leads and engineering managers

- **Know where help is needed** without surveys. The Office, Team Overview and Work Problems show who is stuck and why.
- **Plan around real limits.** Plan headroom, Leave & On-Call and recent activity make sprint planning realistic.
- **Track projects honestly.** All Projects shows which projects are active, which are stable and which have gone quiet.
- **Report without effort.** Reports and scheduled emails share the picture with your own leadership.

### For executives and finance

- **See AI token use and estimated cost** by person, project, tool and model (cost per tool), instead of one opaque bill.
- **Find wasted or shared seats** with Tool Accounts and seat prices.
- **Keep spending on track** with monthly budgets per team or project and alerts at 80% and 100%.
- **Understand adoption.** See which AI tools and models are really used, and how that changes over time.

### For administrators and IT

- **Control who sees what** with roles, a per-page permissions grid and delegated account management.
- **Know the system is healthy.** Machines, Data Collection, Processing and automatic infrastructure checks show problems before users report them.
- **Meet privacy requests.** Export or erase one person's data, and keep a record of sensitive admin actions.
- **Keep data at home.** Self-hosted on your own computer, network or cloud account.

### For the organisation as a whole

- **Decisions based on what happened,** not on self-reports or guesses.
- **A culture of trust.** Kite Pulse describes work rather than policing it, and shows everyone what is collected.
- **A growing memory.** The longer you use it, the more of the organisation's know-how is kept and findable.

## 9. Why it matters: what makes Kite Pulse different

**Most tools judge engineering by its outputs. Kite Pulse sees the process that produced them, inside the AI session where the work now happens.**

1. **Truth from the source.** Figures come from what actually happened in each session, not from surveys, self-reports or estimates.
2. **One view across ten AI tools.** Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot Chat, Cline, Roo Code, Kilo Code, OpenCode and Aider in one consistent picture, instead of ten dashboards or none.
3. **No extra work for developers.** Nothing to log, fill in or remember. Capture runs in the background.
4. **Spending made visible.** Token use by person, team, project and tool, estimated cost per tool, seat prices, shared accounts, budgets and Claude plan limits.
5. **Problems found early.** Repeated failures, stuck work and plan-limit pressure show up while there is still time to act.
6. **Knowledge that stays.** What one person learns in a session can be found and reused by the next.
7. **Built for trust.** Consent before sync, secrets masked twice, private fields kept private, and a Privacy page that shows each person exactly what is collected.
8. **Your data stays yours.** It runs on your own computer, network or cloud account, works fully without any AI service, and its AI features are opt-in.

**What Kite Pulse is not:** it is not a keystroke logger, a screen recorder, a website tracker or a code-quality scanner. It reads only the AI tools' own session records.

## 10. Getting started

**One person can be up and running on their own computer; a team adds a shared server and a short onboarding step for each member.**

&#91;embedded content: Team setup and onboarding · six steps, one approval choice\]

**On your own**

1. Install Kite Pulse on your computer with one command. It sets up the server, the console and the desktop program together.
2. Sign in and set your own password.
3. Confirm your projects in the Onboarding Wizard.
4. Your sessions start appearing in Workspace and My Sessions.

**As a team**

1. An admin sets up the team's Kite Pulse server: on a local network for a pilot, on an Ubuntu server, or in the team's own AWS account.
2. The admin creates an account for each person, or lets people sign up with a company email address.
3. Each person installs the desktop program and connects it with their personal client code (it starts with KP-).
4. Each person confirms their projects in the Onboarding Wizard.
5. Unless an admin has switched approval off, a manager or admin approves each person's project list.
6. Sessions start flowing in and the team pages fill up.

Until a person finishes the Onboarding Wizard, none of their session content is uploaded. An empty console at that point is expected, and Workspace shows exactly where each project stands.

## 11. Complete feature list

**Every feature in the product, in one table.** “Who” is the default; admins can grant most pages to other roles on Roles & Permissions. “Optional” means off until an admin (or, where noted, the server operator) turns it on.

| Area | Feature | What it does | Who |
| --- | --- | --- | --- |
| Capture | Ten AI coding tools | Collects sessions from Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot Chat in VS Code, Cline, Roo Code, Kilo Code, OpenCode and Aider | Everyone |
| Capture | Tool switches | Turn each tool on or off, or collect token counts only | Admin |
| Capture | Automatic project detection | Finds project folders and repository addresses and links each session to its project | Everyone |
| Capture | Only new activity | Sends only what changed, so nothing is counted twice | Everyone |
| Capture | Offline catch-up | Picks up where it stopped once the server is reachable | Everyone |
| Capture | Secret masking | Masks passwords, keys and tokens on the computer, and again on the server | Everyone |
| Capture | Protected upload | Encrypts session data before it leaves; sends only to your own server | Everyone |
| Capture | Consent before sync | Nothing from a session is sent until the developer confirms their projects | Developer |
| Capture | Windows and Mac program | Installer for Windows and macOS (Apple Silicon and Intel); starts with the computer | Developer |
| Capture | Automatic updates | Updates the desktop program from your own server, checked before install; admins publish a version with Set app version on Tools | Admin publishes |
| Capture | Tray icon | Status colour, Open dashboard, View log, Re-enter code, Run diagnostics | Developer |
| Capture | Optional extra reads | Branch names, frameworks, project notes, sleep and network events, tool versions, Claude Code skills and MCP servers, Copilot plan, plan-usage refresh; all switched on in one place, the Kite Pulse app reads tab on Retention | Admin, optional |
| Home | The Office | Live home page showing each person's AI agent at a desk, grouped by room and team | Everyone |
| Home | 3D office view | The default on a desktop computer: desks with animated AI agents whose posture shows typing, reading, waiting, stuck or away in the lounge | Everyone |
| Home | Map view | Flat company map of rooms around the Brain, no 3D needed | Everyone |
| Home | List view | Simple list of people and desks; phones and small windows open here | Everyone |
| Home | Headroom view | Board of everyone's Claude plan usage and reset times | Manager, Admin |
| Home | Full screen wall view | The Office without menus, for a TV or meeting room | Everyone |
| Home | Light and Dark | Daylight or evening office, remembered per browser | Everyone |
| Home | Live updates | Changes appear within seconds; falls back to every 15 seconds and says so | Everyone |
| Home | Desk markers | One marker per desk: attention, stuck, plan limit, near limit, waiting, syncing, out-of-date app | Everyone; detail within scope |
| Home | Desk side panel | Presence and tool for everyone; task, stuck reasons, plan, sync and today's figures within scope | Everyone; detail for self, manager, admin |
| Home | Sub-agents on the desk | Small objects beside an agent; the side panel shows each one's kind, model, run time and current step | Self, manager, admin |
| Home | Activity tab | Live 24-hour feed of sessions, tasks, commits, stuck agents, approvals and comings and goings | Everyone; alerts for admins |
| Home | Tasks tab | Board of in-progress, stuck, waiting, paused, failed and done work, with filtering counters | Everyone; queue and alerts for admins |
| Home | Office tab | Figures for the whole office or one team, plus connectors and skills used this week | Everyone |
| Home | Connected strip | AI tools, MCP servers and code hosts in use | Everyone |
| Home | Team picker and filters | One team's office; Working now, Online, Needs attention, Not set up | Everyone |
| Home | Team suggestions | Suggests teams from who already works together; one click creates one | Admin |
| Home | Office visibility | Stop a role seeing other people's desks | Admin, optional |
| Personal | Workspace | Whether each project is being collected, uploads being retried and what is waiting on each computer, your next setup step, plus your own Claude plan usage | Everyone |
| Personal | My Scorecard & Insights | Personal report led by Top 3 to act on, with verdict, reason, evidence and what to try | Everyone |
| Personal | Productivity tiles | Lines added and changed, your and the AI's messages, against the previous period | Everyone |
| Personal | Verification signal | How often you reviewed or tested AI output, with checks and corrections | Everyone, needs AI labelling |
| Personal | Work-pattern facts | Peak hour, busiest day, streaks, deep-focus sessions, longest session, parallel sessions, short bursts | Everyone |
| Personal | Working style | Builder, explorer, debugger, communicator or generalist | Everyone |
| Personal | Private prompt statistics | Most repeated prompt, reply pace and more, shown only to you | Everyone |
| Personal | My Activity | When, how long and with which tools you worked | Everyone |
| Personal | My Sessions | Every session with a summary and a detailed view; filter by tool, model and session type; main versus parallel time | Everyone |
| Personal | Session labels and filter | Label badges on session lists, with a label filter | Everyone for their own sessions; Admin for others; AI labels need AI labelling |
| Personal | What the agent did | Every step the AI took in a session, in order: tools, files, commands, tests, errors and stuck stretches; never message text; also opens from a desk in The Office | Everyone, on sessions they can open |
| Personal | Session Playback | Replays a session turn by turn with a timeline; sub-agent conversations open inline (Claude Code) | Everyone |
| Personal | Session Summary | Rule-based digest: title, outcome, whether work was checked, security-sensitive edits, failing commands | Everyone |
| Personal | Segments and Labels tabs | A session's parts and its labels, with links between sub-agents and parents | Everyone; labels need AI labelling |
| Personal | My Projects, Pending Requests, Project Detection | Confirm, rename, split or remove your projects and follow requests | Everyone |
| Personal | Privacy | Every data point collected about you, whether it is on and who can see it | Everyone |
| Personal | Account | Profile, password, your agent keys | Everyone |
| Personal | Needs attention | One inbox for anything waiting on you | Everyone |
| Personal | Help / Glossary | Plain-language help from the top bar | Everyone |
| Team | Team Overview | Live view of who is online and coding, today against a typical day, who needs attention | Manager, Admin |
| Team | All Developers | Each person's report, without private fields; roster export to Excel | Manager, Admin |
| Team | Developer exports | One person's sessions as CSV and projects as Excel | Manager, Admin |
| Team | Detection and Collection tabs | Work Problems and Data Collection for one person | Admin |
| Team | Profile facts | Technologies, business areas, growing and steady skills, how much work goes to AI | Admin, needs AI labelling |
| Team | Tenure & Departure | Time in the organisation, team and each project; departure report of capabilities, records, open work and files only they edited; knowledge-capture requests; facts only, never a ranking | Admin |
| Team | Organisation Overview | Company-wide people, hours, sessions, commits, project health, styles, tools | Admin |
| Team | Summary, Activity Overview | How activity changes over time | Manager, Admin |
| Team | Trends | 12- or 26-week completion, win rate, stuck share, friction and checked changes, pooled, never per person | Manager, Admin; label measures need AI labelling |
| Team | Collaboration | Projects several people share, and who contributes | Manager, Admin |
| Team | Teams | Team membership with start and end dates | Admin |
| Team | Leave & On-Call | Records leave, holidays and duty rotas | Manager, Admin |
| Team | Blocker Board | Recurring causes of lost time with suggested actions, never one person; empty until an admin switches suggestion rules on | Admin, needs AI labelling |
| Team | Team Review | One team's weekly middle values against last week, deferred work and work mix; never names a person; small teams held back | Admin, needs AI labelling |
| Team | Workflows & Pain Points | What repeats (work shapes, prompts, commands) and what slows work down, week by week | Admin |
| Team | AI Collaboration | Friction, checked changes, accepted AI edits and who led the work, month by month; teams of 3 or more | Admin, needs AI labelling |
| Team | Agents in parallel | AI agents and sub-agents running now, and a day's lane chart | Admin, and managers for themselves |
| Projects | All Projects | Every project with health, sessions, contributors, last activity, phase and open blockers | Manager, Admin |
| Projects | Add project | Add a project that was not detected and approve it in one step | Manager, Admin |
| Projects | Bulk pause or delete | Act on several projects at once | Admin |
| Projects | Project page | Contributors, sessions and a summary card: stability, trend, tokens, phase, risk, blockers, duplicate work and knowledge, each linked | Manager, Admin; some figures need AI labelling |
| Projects | Project sessions | A project's sessions with label badges and a label filter | Admin; AI labels need AI labelling |
| Projects | Project notes | Every version of a project's CLAUDE.md, AGENTS.md, README and decision records, secrets masked, every read recorded | Admin by default, optional read |
| Projects | Duplicate work, Risk and phase | Project sections built from labels | Admin, needs AI labelling |
| Projects | Project actions | Merge, unmerge, change root folder, split, pause, or delete after a grace period; or send a request | Manager, Admin |
| Projects | Onboarding Approvals | Approve a new developer's first project list: setup approval, new projects, syncing and not syncing | Manager, Admin; on by default, can be switched off |
| Projects | Project Approvals, Request History | Approve later project changes and see their history | Manager, Admin |
| Projects | Duplicate Detection | Merge folders that are the same repository; suggests splits | Manager, Admin |
| Projects | Removed Projects | Paused and deleted projects; admins resume paused ones | Manager, Admin |
| Projects | Project Mapping | Keeps projects correctly organised | Manager, Admin |
| AI spend | Team AI Usage | Tokens by developer, tool, model, project and day | Manager, Admin |
| AI spend | Token pace line | 14-day average tokens per day, 30-day outlook, marks unusually heavy days; tokens only | Manager, Admin |
| AI spend | Estimated cost per tool | List-price estimate per tool, or the tool's own reported cost | Manager, Admin |
| AI spend | Models tab | Model use and adoption over time | Manager, Admin |
| AI spend | Agent features tab | Which Claude Code agent features sessions used | Manager, Admin |
| AI spend | AI Budgets | Monthly budget per team or project with alerts at 80% and 100% | Admin |
| AI spend | Hourly Rates & Seat Prices | Seat costs per tool and hourly rates per role level, dated and recorded, beside usage | Admin |
| AI spend | Tool Accounts | Accounts per tool, shared accounts, plan tier, email domain | Admin |
| Plan limits | Plan headroom | Who is close to a Claude plan limit, worst first | Manager, Admin |
| Plan limits | Your plan usage | Your own Claude plan figures on Workspace | Everyone |
| Plan limits | Account and freshness | Names the Claude account behind each figure; says why a reading is old; tags live figures | Everyone (own), Manager, Admin |
| Plan limits | Plan limit reached notice | Tells a person and their manager which window is used up and when it resets | Developer and their manager |
| Plan limits | Background plan refresh | Keeps plan figures current without using tokens; runs every 5 minutes to 6 hours, hourly by default; developers can opt out | Admin, optional |
| Plan limits | Plan reading history | Keep plan readings 30 days to two years; confirm before older ones are deleted | Admin |
| Plan limits | Claude Code version check | Flags anyone behind the latest Claude Code release; the developer gets an “out of date” notice that clears once they update | Manager, Admin; Developer for their own notice |
| Problems | Work Problems | Failing commands, errors and retries, by severity, with suggested actions | Admin |
| Problems | AI agent stuck notice | Tells a person and their manager when an agent is stuck 30 minutes or more, with the project | Developer and their manager; operator can change or turn off |
| Problems | Insight Rules | Review and tune the rules behind insights; the Insights Catalog explains each insight and who may see it | Admin |
| Reports | Company report | Any period against the one before; CSV or PDF | Manager, Admin view; Admin downloads |
| Reports | Plan usage report | Claude plan usage for any period up to two years: peaks, extra usage, day-by-day chart; Excel download | Manager, Admin view; Admin downloads |
| Reports | Scheduled reports | Company or developer report by email, daily, weekly or monthly | Admin |
| Notifications | Bell and email | Tells people when something needs their attention; View all opens every notice received | Everyone |
| Notifications | Notifications settings | Who is told what, email on or off, daily digest | Admin |
| Notifications | Slack channel | Server alerts to Slack, with a Test button | Admin, optional |
| Notifications | Delivery history | Log of every notification sent | Admin |
| Notifications | Admin alert email | Email for critical alerts and a daily digest of warnings; each admin can mute their own | Admin; operator sets up mail |
| Notifications | Infrastructure checks | Automatic alerts for stalled processing, low memory or disk, silent collectors and more | Admin |
| Notifications | Advanced thresholds | Change the levels that raise health alerts | Admin |
| Notifications | Infrastructure page | One tile per area: processing, memory, disk, database, silent collectors, email relay | Admin |
| Notifications | Alerts | Every infrastructure alert, moved through Open, Acknowledged, In progress and Resolved; shared by all admins; Excel download | Admin |
| AI labelling | Work classification | Labels work by type and outcome using an AI model, within a monthly cap | Admin, optional |
| AI labelling | Fact rules | Simple facts such as “tests ran”, no AI, no cost | Admin; on by default, can be switched off |
| AI labelling | Label list approval | Every label list approved by an admin before it runs | Admin, needs AI labelling |
| AI labelling | Review Labels | Check and correct uncertain answers | Admin, needs AI labelling |
| AI labelling | AI Call Log | Every AI labelling call with what was sent and received | Admin, needs AI labelling |
| AI labelling | Classification Overview and Reports | Labelling spend, coverage, labels awaiting review, model scores and side-by-side comparisons | Admin, needs AI labelling |
| AI labelling | My Day | Your own day: worked on, started, finished, left open, where you got stuck, what you learned; only you see it | Everyone, needs AI labelling |
| Knowledge | Knowledge Records | Lessons quoted from real sessions, linked to their source; written by AI labelling | Admin, needs AI labelling |
| Knowledge | This week (knowledge log) | The week's new records grouped by kind: requirements, rules, decisions, findings, open questions | Admin, needs AI labelling |
| Knowledge | Knowledge captured this week | Card on Insights Summary, project pages and the Capability Map | Admin, needs AI labelling |
| Knowledge | Coherence | Finds duplicate records and flags contradicting or out-of-date ones | Admin, needs AI labelling |
| Knowledge | Capability Map | Each project as modules, capabilities and scenarios, with full change history; no AI | Admin |
| Knowledge | Capability ownership | Who edits and reads each capability, share of edits, bus factor, hand-over hint; owners accept or decline | Admin |
| Knowledge | Session Graph | Groups sessions that look alike, refreshed daily; no AI | Admin |
| Knowledge | Skill Candidates | Draft Claude Code skills from repeated workflows; no AI | Admin |
| Brain | Brain switch | Turns the Organizational Brain on or off in one click; every change recorded | Admin, optional |
| Brain | Brain tab | The Brain's home, in The Office's view switch | Everyone, once the Brain is on; admins always |
| Brain | Graph | Interactive map of departments, people, projects, agents, documents, capabilities and AI tools | Everyone, once the Brain is on |
| Brain | Documents | Policies, playbooks, SOPs and notes for the company, a department or a project; secrets masked | Admin and Manager upload; everyone reads their share, once the Brain is on |
| Brain | Agents | Built-in People & org, Projects, Knowledge & documents and SOPs agents, plus department agents | Everyone, once the Brain is on; admins and department leads create |
| Brain | Governance | Per department: what the Brain holds, who may read it, who read it recently; budget, model and keep periods | Admin, department leads; once the Brain is on |
| Brain | Person pages | Overview, Work, AI Context, Compliance and AI Access for one person | Everyone for themselves, once the Brain is on; Manager, Admin set titles |
| Brain | Project context | Objectives, strategy, status note and links on the project page | Project page viewers, once the Brain is on |
| Brain | Ask a teammate's agent | From a colleague's desk in The Office, ask about their last 14 days of synced work on projects you both see; never their message text; they see every question | Everyone, once the Brain is on |
| Brain | Who asked my agent | Every question colleagues asked your agent, with a pause switch, on the Privacy page | Everyone, once the Brain is on |
| Brain | Chat | Ask anything in plain words; answers cite their sources and stay within your access | Everyone, once the Brain is on and the server operator provides an AI key |
| Brain | Chat budget | Monthly limit on Chat's AI use, $20 by default; questions refused before any AI call once used up | Admin, once the Brain is on |
| AI assistants | Agent API keys | Let an outside AI assistant ask questions, or, in Direct access mode, read data within its owner's access | Admin issues; operator turns on |
| AI assistants | Access mode | Chat mode (questions only) or Direct access (read data too) | Admin; operator turns on |
| AI assistants | What a key can read | About 115 read tools over MCP, covering almost everything the console shows, within the owner's access | Key holders; operator turns on |
| AI assistants | Session text permission | Lets a key read what the AI said, secrets masked, every read recorded, never over MCP | Admin issues with a risk acknowledgement; operator turns on |
| AI assistants | Machine interruptions | Time lost to sleep, crashes, restarts and lost network | Key holders; needs the optional sleep and network read |
| AI assistants | MCP support | Connect Claude Code, Cursor, VS Code and other MCP clients | Key holders; operator turns on |
| AI assistants | Assistant provider key | Pays for questions answered by Kite Pulse's assistant, kept apart from labelling | Admin; operator turns on |
| AI assistants | Try a question | See exactly what an AI tool would get back | Admin; operator turns on |
| AI assistants | Agent Activity | Keys by person, all keys, usage, and a log of every request made with a key | Manager, Admin; operator turns on |
| Administration | Sign-in and passwords | Strong passwords, first-sign-in change, lockout, reset by email | Everyone |
| Administration | Login & Registration | Admin-created accounts, sign-up by email domain, open sign-up with approval, or user sync from Entra ID or Okta | Admin |
| Administration | User sync | Create, update and deactivate accounts from Entra ID or Okta; never sets roles or touches admins; sign-in stays email and password | Admin, optional |
| Administration | Accounts & Roles | Create accounts; set role, job role and manager; approve or reject sign-ups; reissue KP- codes; revoke accounts; delegate to managers | Admin |
| Administration | Roles & Permissions | Per-page, per-action access grid for each role | Admin |
| Administration | Export and erase | Export one person's data, or anonymise them and destroy their keys | Admin |
| Administration | Audit Log | Record of sign-ins and sensitive admin actions that cannot be edited | Admin |
| Administration | Leaked Credentials | Masked passwords and keys found in AI conversations, each with a status to track | Admin; list fills when the operator runs a scan |
| Administration | Security watch | Unchecked sensitive changes, and pasted secrets or personal data; counts and identifiers only | Admin, needs AI labelling; alerts turned on by the operator |
| Administration | Retention | Choose how long each kind of data is kept; the server operator turns on real deletion of session data | Admin |
| Administration | Detection Rules | How problems are spotted; whether new projects need confirmation; the grace period before a project's data is deleted | Admin |
| Administration | Machines | Every computer running the program, version, updates and app log; installed tools and sleep and network events | Admin; tools and events need an optional read |
| Administration | Data Collection, Processing | Whether machines upload, and the processing queue | Admin |
| Administration | Server Storage | Space used, by person and project | Admin |
| Administration | Connectors | Link Jira, HubSpot, Slack, GitHub, Confluence, Google Drive and Notion to projects | Admin |
| Administration | Agent Setup | Claude Code skills, commands, agents and MCP servers across machines; plugins coming with the next desktop app release | Admin, optional read |
| Administration | Generation rate | Claude Code reply speed in tokens per second | Admin, optional; developer opts in |
| Administration | Configuration, Maintenance, Setup checklist, Organisation Name | Run and tidy the installation | Admin |
| Deployment | Self-hosted options | One computer, team pilot, Ubuntu server, your own AWS account, or server only | Admin, operator |
| Deployment | HTTPS | Free certificates set up automatically on the Ubuntu server install | Operator |

## 12. Questions people ask

**Does Kite Pulse read my source code?** No. It reads the session records your AI tools already keep, plus folder names and repository addresses. If an admin switches on the optional project-notes or frameworks reads, it also reads a project's own notes (CLAUDE.md, AGENTS.md, README and decision records) and its package lists, never its source code. Those records can include parts of code the AI read or wrote, which is why secrets are masked before anything leaves your computer.

**Can my manager see everything I typed?** Managers see activity figures and session details for their own team. Your private prompt statistics stay private to you, and the Privacy page shows exactly what is collected about you and who can see each part.

**Can colleagues see what my AI agent is doing in The Office?** Everyone sees your name, your AI tool and whether you are online or away. Your task, stuck reasons, plan figures and the steps your agent took are shown only to you, your manager and admins, and never include your messages.

**Will anyone notice if my AI agent gets stuck?** Yes. If your AI agent has been stuck on the same problem for 30 minutes or more, you and your manager get a notice naming the project. The session's “What the agent did” view shows each step, so you can see where it went round in circles.

**Is this a performance-ranking tool?** No. Kite Pulse is built to describe what happened and help people improve, not to grade them. Insights say “not enough data” rather than guess, and team-level views such as the Blocker Board never single out a person.

**What happens to what someone knows when they leave?** The departure report on Tenure & Departure shows what is at risk: the capabilities they carry, the records they own, their open work and the files only they edited. An admin can ask them to write that knowledge down before they go. It shows facts only and never ranks people.

**Which AI tools does it support?** Ten: Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot Chat in VS Code, Cline, Roo Code, Kilo Code, OpenCode and Aider.

**Can I watch a session back?** Yes. Session Playback replays a session turn by turn, with a timeline to jump around. Secrets stay masked.

**Which computers does it run on?** The desktop program runs on Windows and macOS (Apple Silicon and Intel). The console works in any modern web browser.

**Does our data go to a vendor's cloud?** No. It goes only to the Kite Pulse server your team runs, on your own computer, network or cloud account.

**Do we need an AI service to use it?** No. Capture, activity, usage, projects, plan limits, reports and administration all work without one. Only the optional AI labelling, the Brain's Chat and Chat mode for outside AI assistants need a key: an admin enters the labelling key on the Classification page, the Brain's Chat key comes from the server operator, and the assistant key is added once the server operator turns agent keys on. Knowledge Records are written by AI labelling; the Brain's Graph, Documents and person pages work without AI.

**What is the Organizational Brain, and can it show me more than I am allowed to see?** It is an optional place, on the Brain tab of The Office, to explore and ask about your organisation's people, projects and documents. An admin switches it on. It never shows anyone more than they can already read: hidden items are left out of maps and answers. If a colleague asks your agent about your work, you see their question on your Privacy page, and you can pause your agent there.

**Can an outside AI tool read our raw data?** Only if an admin allows it. In Chat mode, an AI tool can only ask questions, and Kite Pulse's own assistant answers. Direct access, which also reads data within the key owner's view, is a separate admin choice. Both are available only once the server operator turns agent keys on.

**Are the cost figures exact?** Token counts come straight from each tool's own records. Cost is an estimate at list prices, shown per tool, and is a guide for decisions rather than a replacement for your vendor's invoice.

**Which plan limits does it track?** Claude plan limits from Claude Code: the 5-hour window, the weekly window and each model's weekly window.

**Will I be told when I hit my plan limit?** Yes. When one of your Claude plan windows is used up, you get a notice in the bell saying which window and when it resets. Your manager gets it too, so work can be moved. It is as fresh as your latest plan reading.

**What happens when I am offline?** Nothing is lost. The desktop program catches up once the server is reachable again.

**I signed in and my pages are empty. Is something wrong?** Usually not. Nothing is uploaded until you finish the Onboarding Wizard, and unless approval is switched off, syncing starts once an approver signs off. Workspace shows where each project stands.

**Can one person use Kite Pulse alone?** Yes. It runs entirely on one computer for one person, with the same personal pages a team member gets.

**Can we sync accounts from Microsoft Entra ID or Okta?** Yes. User sync can create, update and deactivate accounts from either directory. An admin switches it on in Login & Registration. It never sets roles or touches admin accounts, and people still sign in with email and password.

### Glossary

| Term | Meaning |
| --- | --- |
| Access role | Developer, Manager or Admin. Decides which pages a person sees. |
| Active time | Time actually spent working, worked out from activity. Overlapping sessions are counted once. |
| Agent API key | A key an admin issues so an outside AI assistant can ask Kite Pulse questions or read its data, never more than its owner can see. |
| Brain agent | A focused way of asking the Organizational Brain, such as People & org or an HR policy helper. It only reads and answers, within the asker's own access. |
| Client code | The personal code (starting KP-) that links a desktop program to one person's account. |
| Console | The Kite Pulse website where everyone views their pages. |
| Desktop program | The small background program on each computer that captures sessions and uploads them. |
| Insight | A finding about someone's work, with a verdict, the reason, the evidence and a suggestion. |
| Knowledge record | Something the organisation learned, quoted from real sessions and linked to where it came from. Written by AI labelling. |
| Label list | The set of labels AI classification may use. An admin approves it before it runs. |
| Onboarding Wizard | The first-sign-in step where a developer confirms which projects to sync. |
| Organizational Brain | An optional part of Kite Pulse that maps the organisation's people, projects and documents and answers questions about them, within each person's access. An admin switches it on. |
| Plan headroom | How much of a Claude plan's usage limit is still available. |
| Scope | The people a viewer may see: a manager's reporting line, or everyone for an admin. |
| Session | One sitting with an AI coding tool. |
| The Office | The live home page where each person's AI agent sits at a desk, showing who is working, waiting or stuck. |
| Token | The unit AI tools use to measure text sent and received, and so the basis of AI cost. |
| Tool account | The account an AI tool is signed in with. |
| Working style | Builder, explorer, debugger, communicator or generalist, from what a person's sessions mostly did. |
