# Kite Pulse — Product Guide

Oct 13, 2026 · @Neenu

## What Kite Pulse is

Kite Pulse shows a team how its software is really being built, now that much of that work happens in conversation with AI coding assistants. A small background program on each developer's computer picks up the session history those assistants already keep, strips out secrets, and sends it to the team's own Kite Pulse server. The web console turns those sessions into a clear picture: who is working on what, how AI tools are used, what they cost, and where work gets stuck.

Most tools judge engineering work by its outputs: commits, pull requests, tickets, surveys. Kite Pulse looks at the process behind them. It sees the questions asked, the approaches tried and dropped, the errors and retries, and the decisions made along the way. A commit log tells you a feature shipped; Kite Pulse tells you how it got there and what the team learned.

In one line: **a single place to see AI-assisted development across people, projects and tools, running on a server the team controls.**

## Who it is for

Kite Pulse serves anyone who builds software with AI coding assistants, or who is responsible for people who do. It works for a single developer on one laptop and for a whole organisation on a shared server.

| Who | What they want to know | What Kite Pulse gives them |
| --- | --- | --- |
| Individual developers | "How do I actually spend my time with AI? Am I getting better?" | A private mirror of their own sessions, working style, strengths and habits, with suggestions to try. |
| Team leads and engineering managers | "What is my team working on, where are they stuck, and who needs support?" | Live team activity, project health, collaboration patterns and gentle early-warning signals, without running surveys. |
| Executives and finance | "What are we spending on AI, and what are we getting for it?" | AI cost per person, project and period, billable amounts, and plan-limit usage across tools. |
| Administrators and IT | "Is the system healthy, who has access, and what is being collected?" | Account and role management, project approvals, collection switches, machine fleet status, alerts and an audit log. |
| The organisation as a whole | "Are we keeping what we learn, or solving the same problem twice?" | A growing knowledge base of rules, patterns and solved problems taken from real sessions. |

What each person sees is set by two separate things. Their **access level** decides which pages appear: an **Admin** sees everything, a **Manager** sees their own team plus their personal pages, and a **Team member** sees only their personal pages. Their **work role** (developer, designer, analyst and so on) shapes how insights are framed, so coaching fits the job they actually do.

## Problems it solves

AI coding assistants changed the unit of work: developers now direct an AI that writes much of the code. Organisations are spending heavily on these tools but have no truthful way to see what they get back. Kite Pulse closes that gap.

| Problem | What it looks like today | How Kite Pulse helps |
| --- | --- | --- |
| Output counts no longer tell the story | More commits and pull requests, yet delivery feels no faster. Nobody can say where the time went. | Measures active time, sessions, retries and abandoned approaches from the sessions themselves. |
| AI spend is a black box | Several tools, several subscriptions, one monthly bill. No view per person or per project. | Shows AI cost by person, project, tool and period, plus a billable view with a markup. |
| Plan limits arrive as a surprise | A developer hits their AI plan's usage limit mid-task and loses half a day. | Shows how much of each plan's limit is used, for each person and across the team. |
| History is scattered across tools | Claude Code, Codex, Gemini, Cursor and Copilot each keep their own records, in their own format. | Brings every supported tool into one consistent view. |
| Managers find problems late | Struggling or overloaded people surface in a status meeting weeks later, or not at all. | Flags early signals (very long sessions, repeated dead ends, disengagement) as prompts for a supportive check-in. |
| Knowledge evaporates | A hard bug is solved in a chat session, then solved again by someone else next month. | Turns sessions into a searchable knowledge base of rules, patterns and solutions. |
| Project status is guesswork | Which projects are active, who is on them, and which have gone quiet? | Lists every project with its health, contributors, sessions and last activity. |

Kite Pulse does this without surveys, timesheets or extra steps for developers. They keep working the way they already do.

## How it works at a glance

Kite Pulse has three parts: a desktop program on each developer's computer, a server the team runs, and a web console everyone signs in to.

&#91;embedded content: how Kite Pulse works · 3 parts, plus the Onboarding Wizard and outside assistants\]

Only new, secret-free, encrypted activity leaves a computer, and only after the developer confirms their projects. The server turns it into figures that people read in the console, or that an approved AI assistant can query.

## Key features

Kite Pulse's features fall into nine groups, from capturing sessions to answering questions about them. Page names are shown in **bold** as they appear in the console menu.

### 1. Automatic session capture across AI tools

The desktop program records AI coding sessions in the background, with no manual logging. It supports ten tools today: **Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot, Cline, Roo Code, Kilo Code, OpenCode and Aider**. An admin chooses which ones are collected on the **Tools** page.

- Picks up only new activity, so nothing is counted twice.
- Queues work when the network drops and uploads it later.
- Detects the projects on each machine and links every session to the right one.

*Example:* a developer uses Claude Code in the morning and Cursor in the afternoon. Both appear in one timeline, under the same project, without them doing anything.

### 2. Developer activity insights (personal)

Every person gets private pages about their own work.

- **Overview** answers "is my work being collected?": what is synced, still uploading, processed, or needs attention.
- **My Scorecard & Insights** shows active hours, sessions, messages, lines changed, commits and projects, led by a "Top 3 to act on" list. Each insight gives a verdict, the reason, the evidence, and something to try.
- **Work-pattern facts**: peak hour, busiest day, longest streak, deep-focus sessions, longest session, parallel sessions and reply pace.
- **Working style**: a label such as builder, explorer, debugger or communicator, worked out from the person's own tool mix.
- **My Activity** and **My Sessions** list every session, with drill-down into what happened in it.
- **Private prompt statistics** (number, length and most-repeated prompt) that only the developer can see.

*Example:* a developer sees that 40% of their sessions are short bursts under ten minutes and that their failure rate on test commands doubled this week. The insight suggests batching small tasks and checking the test setup.

### 3. Session and usage analytics

These pages show how much AI the team uses and where it goes.

- **Team AI Usage**: tokens used per developer, per tool and per period, with an estimated cost per tool where it can be worked out.
- **Plan headroom** (a tab on Team AI Usage): who is close to a Claude plan limit (the 5-hour window, the weekly window, or a model's weekly window), worst first. It also flags people on an out-of-date Claude Code version.
- **Tool Accounts**: how many separate accounts each AI tool is used under. It reveals shared logins, or one person holding two accounts.
- **Error & Command Stats**: failing commands, repeated failure loops and the most common error types across the team.
- **Reports**: a team or company summary for any period, downloadable as a spreadsheet, and **Scheduled reports** that email it on a regular cycle.

*Example:* a lead opens Plan headroom on Thursday and sees two developers past 90% of their weekly limit. They move a large refactor to Monday instead of losing a day to the limit.

### 4. Live team and company view

- **Org Overview** is a live control room: who is online, coding, idle or offline, sessions today, active time, a timeline of each person's day, and their current project.
- **Developers** lists everyone in scope; opening a person shows the same detail as their personal pages, minus private fields.
- **Company Overview** gives admins one company-wide picture: active people and hours, commits, project health, working styles and tool use.

A manager sees only their own reporting line; an admin sees everyone. This limit is enforced by the server, not just hidden in the screen.

### 5. Project tracking

- **Organization Projects** lists every project with its health (active, stable or dormant), sessions, contributors and last activity. Each project has a detail page.
- **Project Details, Events & Policies** lets admins record what the sessions cannot show: releases, freezes, incidents, process changes and re-organisations, plus guardrail policies such as "tests run before a commit". Questions about "before and after" then have a date to split on.
- **Onboarding Approvals** and **Project Approvals** are queues where an approver confirms which projects a developer may sync, and approves or rejects later change requests.
- **Duplicate Detection** groups folders that look like the same repository on different machines, and offers to merge them. A project that holds several projects can be split.
- **Removed Projects** keeps projects that were switched off, so they can be restored.
- Developers manage their own side in **My Projects**, **Pending Requests** and **Project Detection**.

*Example:* the same repository is cloned as `web-app` on one laptop and `webapp-main` on another. Kite Pulse spots the shared repository address and suggests merging them, so the team sees one project with both contributors.

### 6. Team collaboration and communication

Kite Pulse is not a chat or messaging tool. It supports collaboration by giving everyone the same honest picture of the work, and by telling the right people when something needs them.

- **Collaboration** shows who works on what together: each shared project, the people contributing, and how many sessions each spent there.
- **Teams** records team membership over time, so reports can be split by team.
- **Leave & On-Call** records holidays and duty rotas. Without it, a week of leave would look like disengagement, and a support rota like a focus problem.
- **Notifications** arrive in the console's bell and by email. People choose which ones they get in **Settings**; admins set the organisation's alerts in **Alerts & Notifications**.
- **Scheduled reports** send a regular summary to the people who need it.

*Example:* before a sprint review, a lead uses Collaboration to see that three developers all touched the billing service. They invite all three to the review instead of only the ticket owner.

### 7. AI-assisted insights

On top of the plain counts, Kite Pulse can use an AI model to label and organise the work. These features are optional. They stay off until an admin adds an AI key and switches them on, and classification runs within a monthly spending cap the admin sets.

- **Work classification** tags each piece of work with answers such as "bug fix or new feature?" or "did the session succeed?". Admins approve each set of labels on **Label Lists** before it runs, set budgets and confidence levels in **Classification Settings**, and check uncertain answers in **Developer-Level Labels**.
- **Knowledge Records** hold what the organisation has learned, quoted from real developer messages and AI replies and tied to the sessions and commits they come from.
- **Capability Map** describes each project in the words people use (modules, capabilities, scenarios), so work and knowledge can be placed on the right part of the product.
- **AI Call Log** shows every AI call Kite Pulse made, with what was sent and received, for full transparency.
- **Ask Kite Pulse** answers plain-language questions about the organisation, teams, projects and usage, within the asker's access. A peer view can describe one teammate's working profile with their private details removed. It is switched off in the current release.

*Example:* a manager asks "how much of last month went on bug fixing versus new features, per project?" Classification labels make that a one-click answer instead of a guess.

### 8. Connecting other AI agents

Teams can let an outside AI assistant, such as Claude, read Kite Pulse data to answer questions or prepare reports.

- **Agent API Keys**: admins issue scoped, expiring keys. A key never sees more than the person it belongs to. Developers can hold their own keys under **Settings**.
- The same access works through **MCP**, the standard many AI assistants use to connect to outside tools.
- **Agent Activity** logs every request made with a key, by people in the viewer's scope.

*Example:* a lead asks their AI assistant to "draft my weekly team update from Kite Pulse". The assistant reads this week's actskillivity and project figures through the API and writes the draft.

### 9. Administration, security and operations

- **Accounts & Roles** and **Roles & Permissions**: create accounts, set access level, work role and manager, and fine-tune who can see each page.
- **Login & Registration**: choose admin-created accounts, sign-up by email domain, or open sign-up with approval.
- **Detection Rules** and **Retention**: how projects are detected and approved, and how long data is kept.
- **Leaked Credentials**: passwords or keys that appeared in AI conversations, masked, so the right one can be changed.
- **Fleet**, **Data Collection**, **Infrastructure**, **Server Storage** and **Alerts**: whether every machine is up to date and uploading, and whether the platform is healthy.
- **Audit Log**: a permanent record of sensitive admin actions.

Some pages exist but are switched off in the current release: Trends, Activity Rhythm, Coaching & Risk, Cost & ROI, Comparisons, Intelligence, Knowledge Base and Tech-Debt Radar. They can be turned back on without new development.

## How individuals and teams use it

Kite Pulse can be set up for one person on their own computer, or for a whole team on a shared server. After setup, each role uses it a little differently.

### Getting started

**On your own:** install Kite Pulse on your computer, sign in, change the first-time password, and confirm your projects in the Onboarding Wizard. Your sessions start appearing within minutes.

**As a team:**

1. An admin sets up the team's Kite Pulse server (on the team's own network, or on a cloud server).
2. The admin creates an account for each person, or lets people sign up with a company email address.
3. Each person installs the desktop program and connects it with their personal client code.
4. On first sign-in, each person changes their password and confirms their projects in the Onboarding Wizard.
5. Where approval is required, a manager or admin approves each person's project list.
6. Sessions start flowing in, and the team pages fill up.

Until the Onboarding Wizard is finished, nothing is uploaded, so an empty console at that point is expected.

### Day to day, by role

| Role | Typical moment | Where they go | What they do with it |
| --- | --- | --- | --- |
| Developer | Friday afternoon, looking back at the week | Overview, My Scorecard & Insights, My Sessions | Check that all work was captured, review their top 3 suggestions, and look at sessions that went in circles. |
| Developer | About to start a long task | Plan headroom (if shared), My Activity | See how much of their AI plan is left before starting. |
| Team lead | Morning stand-up | Org Overview, Collaboration | See who is active on what and spot overlapping work. |
| Team lead | Planning next sprint | Team AI Usage, Plan headroom, Leave & On-Call | Balance heavy AI work against plan limits and recorded leave. |
| Engineering manager | Monthly review | Reports, Organization Projects, Error & Command Stats | Track project health, repeated failures and where effort went, then share the report. |
| Executive or finance | Quarterly budget | Company Overview, Team AI Usage, Tool Accounts | Compare AI use and cost across tools, and find shared or unused accounts. |
| Admin | Onboarding a new hire | Accounts & Roles, Onboarding Approvals, Fleet | Create the account, approve their projects, and confirm their machine is uploading. |
| Admin | Security check | Leaked Credentials, Audit Log, Transparency | Find exposed keys to change, review admin actions, and confirm what is collected. |

### Three worked examples

**A developer finds a hidden time sink.** A developer's scorecard shows that most of their failed commands this week came from one repeated test command. Their sessions show the AI retrying the same fix six times. They fix the test setup once, and the next week's failure rate drops.

**A lead avoids a plan-limit stall.** On Wednesday, Plan headroom shows that two of a lead's five developers have used over 85% of their weekly Claude limit. The lead moves a large migration to the following Monday and gives the smaller tickets to the others.

**An admin cleans up projects.** After rollout, Organization Projects lists both `payments` and `payments-api`. Duplicate Detection shows that they share one repository address. The admin merges them, and the project now shows its four real contributors in one place.

## Privacy and trust

Kite Pulse only works if developers trust it, so privacy is built into what it collects and who can see it. Its guiding rule is **"historian, not critic"**: it records and describes what happened, and never passes judgement on a person.

**What the desktop program reads, and why**

| What it reads | Why | What is sent to the server |
| --- | --- | --- |
| Session history of the AI tools an admin has switched on | That is where those tools keep their conversations | The conversation record, with secrets removed and encrypted |
| Folder names inside project folders, and each project's git settings | To tell projects apart | Folder paths and the repository address (host, organisation, repository) only |
| The account each AI tool is signed in with | To link a tool account to the right person | The account email and plan details only |

The program does not open or upload a project's source files. Conversation records can contain code the AI wrote or read, which is why secrets are scrubbed on the developer's machine before anything leaves it. Data goes only to the server the team configured; there is no vendor cloud in between.

**Extra reads stay off until an admin turns them on**

A handful of optional reads add detail, each with its own switch and each off by default: a project's current branch name, the frameworks a project uses, the list of Claude Code skills and add-ons, when a machine slept or lost its network, which AI and developer tool versions are installed, a Copilot plan name, request timing, a background refresh of Claude Code plan usage, and a project's own written notes (such as README and decision records).

**Safeguards for developers**

- **Nothing syncs until the developer says so.** On first sign-in, the Onboarding Wizard asks them to confirm which projects to sync. Where the organisation requires it, an approver signs off first.
- **A Transparency page** lists every data point collected about them, whether it is on, and who can see it.
- **Some data is private to its owner.** Prompt statistics and full folder paths are shown only to the developer; team views show folder labels instead.
- **Thin data is never judged.** When there is too little data, an insight says "not enough data" rather than guessing, and risk signals do not name the person.
- **AI analysis is optional.** Kite Pulse runs fully without any AI service. AI-powered features stay off until an admin adds a key.

**Controls for administrators**

- Switch each AI tool on or off for collection.
- Approve, reject or question the projects a developer wants to sync.
- Export or erase one person's data on request, or anonymise their account.
- Review a permanent audit log of sensitive admin actions.

## What makes it valuable

Kite Pulse is valuable because it sits inside the AI coding session, where the real work now happens. Tools that read commits, tickets or surveys see the results; Kite Pulse sees the process that produced them.

- **Truth from the source.** Figures come from what actually happened in each session, not from self-reports or estimates.
- **One view across many tools.** Ten AI coding tools in one consistent picture, instead of ten separate dashboards or none.
- **No extra work for developers.** Nothing to log, fill in or remember. Capture runs in the background.
- **Spending under control.** Token use, estimated cost, shared accounts and plan limits are visible per person, team, project and tool.
- **Problems found early.** Repeated failures, stuck sessions and plan-limit pressure show up while there is still time to act.
- **Knowledge that stays.** What one person learns in a session can be found and reused by the next.
- **Built for trust.** It describes rather than judges, keeps private data private, and shows each person exactly what is collected.
- **Your data stays yours.** It runs on the team's own server, works fully without any AI service, and AI features are opt-in.

## Glossary

Two lists: the words Kite Pulse itself uses, and the everyday words people use when they talk about, or look for, a product like this.

### Kite Pulse terms

| Term | Meaning |
| --- | --- |
| Access level | Admin, Manager or Team member. Decides which pages a person sees. |
| Active time | Time actually spent working, worked out from activity. Overlapping sessions are counted once. |
| Agent API key | A key an admin issues so an outside AI assistant can read Kite Pulse data, never more than its owner can see. |
| AI Call Log | The record of every AI call Kite Pulse made, with what was sent and received. |
| Capability Map | A description of a project in plain product terms (modules, capabilities, scenarios), used to place work and knowledge. |
| Classification (label) | A short tag on a piece of work, such as "bug fix" or "completed". Applied by an AI model, only after an admin approves the label list. |
| Client code | The personal code (starting `KP-`) that links a desktop program to one person's account. Treated like a password. |
| Collector (desktop program) | The small background program on each developer's computer that captures sessions and uploads them. |
| Confidence bar | The level of certainty a label must reach before Kite Pulse trusts it. Answers below it go to review. |
| Console | The Kite Pulse website where everyone views their pages. |
| Fleet | All the computers running the desktop program, with their versions and upload status. |
| Historian, not critic | The rule that Kite Pulse describes what happened and never judges a person. |
| Insight | A finding about someone's work, with a verdict, the reason, the evidence and a suggestion. Says "not enough data" when data is thin. |
| Knowledge Record | Something the organisation learned, quoted from real sessions and linked to where it came from. |
| Label list | The set of labels a classification may use. An admin must approve it before it runs. |
| Leaked credential | A password or key found in an AI conversation, shown masked so it can be changed. |
| Onboarding Wizard | The first-sign-in step where a developer confirms which projects to sync. Nothing uploads until it is done. |
| Plan headroom | How much of an AI plan's usage limit is still available, per person. |
| Project approval | An approver's sign-off on which projects a developer may sync. |
| Scope | The set of people a viewer may see: a manager's own team, or everyone for an admin. |
| Session | One sitting with an AI coding tool, from start until a pause of 30 minutes or more. |
| Token | The unit AI tools use to measure text sent and received, and so the basis of AI cost. |
| Tool account | The account (usually an email) an AI tool is signed in with. |
| Work role | Developer, designer, analyst and so on. Shapes how insights are framed. |
| Working style | A label such as builder, explorer, debugger or communicator, from a person's tool mix. |

### How people describe this kind of product

People rarely say "Kite Pulse" when they first describe the need. These are the words they tend to use, and how each relates to Kite Pulse.

| What people say | What they usually mean | How Kite Pulse relates |
| --- | --- | --- |
| Engineering intelligence platform, software engineering intelligence | A tool that turns engineering data into insight for leaders | Kite Pulse is one, built on AI sessions rather than commits and tickets. |
| Developer productivity tool, developer analytics | Measuring how developers spend time and where they get stuck | Covered by activity, sessions, work patterns and insights. |
| Developer experience (DevEx, DX) | How smooth and frustrating day-to-day work feels | Seen directly in retries, failures and long sessions, with no survey. |
| AI coding analytics, AI adoption tracking | Who uses AI coding tools, how much, and how well | Core use: usage per person, tool and project. |
| AI usage dashboard, Claude Code analytics, Copilot metrics | Usage figures for a particular AI tool | Covers ten tools in one place, not just one vendor's tool. |
| AI cost tracking, AI spend management, AI ROI | What AI tools cost and whether they pay off | Token use, estimated cost, seat prices and shared accounts. |
| Token usage monitoring | How many tokens each person or project uses | Team AI Usage, per developer and per tool. |
| Rate limits, usage limits, plan limits | Running out of an AI plan's allowance mid-task | Plan headroom shows who is close to a limit. |
| Seat or licence utilisation | Whether paid AI seats are used, shared or idle | Tool Accounts shows how many accounts each tool runs under. |
| Team activity dashboard, engineering visibility | Seeing what the team is working on right now | Org Overview, Collaboration and Organization Projects. |
| Knowledge management, institutional knowledge | Keeping what the team learns so it is not lost | Knowledge Records and the Capability Map. |
| Agentic coding, AI pair programming, vibe coding | Building software by directing an AI assistant | The way of working Kite Pulse is designed to observe. |
| Shadow AI | AI tools used without the organisation knowing | Collection shows which tools and accounts are actually in use. |

What Kite Pulse is **not**: it does not log keystrokes, take screenshots or track websites, because it reads only the AI tools' own session records. It is also not a code-quality scanner, and not a monitoring tool for AI features inside a company's own product.

## Frequently asked questions

**Does Kite Pulse read my source code?** No. It reads the session records your AI tools already keep, plus folder names and repository addresses to tell projects apart. Secrets in those records are removed on your computer before upload.

**Can my manager see everything I typed?** Managers see activity figures and session details for their own team only. Your prompt statistics and full folder paths stay private to you. The **Transparency** page lists exactly what is collected about you and who can see each part.

**Is this a performance-ranking tool?** No. Kite Pulse describes what happened and does not grade people. Early-warning signals are meant to start a supportive conversation, and when data is thin they say "not enough data" instead of naming anyone.

**Which AI tools does it support?** Ten today: Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot, Cline, Roo Code, Kilo Code, OpenCode and Aider. An admin picks which ones are collected.

**Which computers does it run on?** The desktop program runs on Windows and macOS. The console works in any modern web browser.

**Does our data go to a vendor's cloud?** No. Data goes only to the Kite Pulse server your team runs, on your own network or your own cloud account.

**Do we need an AI service or API key to use it?** No. All the activity, usage, project and admin features work without one. Only the optional AI-assisted features need a key, and an admin turns them on.

**Are the cost figures exact?** Kite Pulse shows exact token counts. Where it can be worked out, it adds an estimated cost per tool. It is a guide for decisions, not a replacement for the AI vendor's invoice.

**What happens when I am offline?** The desktop program keeps your sessions queued and uploads them once you are back online.

**I signed in and my pages are empty. Is something wrong?** Usually not. Nothing uploads until you finish the Onboarding Wizard. If your organisation requires approval, syncing starts once an approver signs off. Your **Overview** page shows where your work is in that process.

**Can one person use Kite Pulse alone?** Yes. It can run entirely on one computer for one person, with the same personal pages a team member gets.

**Can we ask questions of Kite Pulse from our own AI assistant?** Yes. An admin issues an Agent API key, and the assistant can then read Kite Pulse data, directly or through MCP, within that person's access. Every request is logged on **Agent Activity**.
