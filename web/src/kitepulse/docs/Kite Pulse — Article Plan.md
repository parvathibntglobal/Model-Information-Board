# Kite Pulse — Article Plan

Oct 28, 2026 · @Neenu

**219 articles Kite Pulse can publish, grouped into 13 categories, each with a distinct angle so no two articles cover the same ground.** The plan is built from the [Complete Product Overview](https://claude.ai/artifact/NsZRxsaP7hDXk4mYgecK15) and the [Website Content — Master Source of Truth](https://claude.ai/artifact/FZgskyqfxKNs22UYjsL2Fu), both checked against the product's code.

**How the categories stay separate.** Product Overview explains what Kite Pulse is. Features and Capabilities explains how each part works. Benefits articles describe outcomes for one audience, not features. Problems articles start from a pain. Use Cases tell a story. Workflows explain a recurring process and the decisions it informs. Industry articles show how a type of organisation would apply the product. Getting Started articles are step-by-step guides. The Brain, The Office's 3D view and external integrations each have their own category, so they are not repeated elsewhere.

**Rules every article follows.**

- Describe only what the product does today. Optional parts are flagged: *(admin switch)*, *(needs AI labelling)*, *(server operator turns it on)*, *(Brain must be on)*.
- Never claim plan limits for tools other than Claude Code, a cost total across tools, encryption at rest, single sign-on, full erasure of a person's data, ROI figures or certifications.
- Features waiting for the next desktop app release (exact approval and waiting signals, plugin lists) are left out until it ships.
- Names and numbers in stories are illustrations, not customer results.

## 1. Product Overview

What Kite Pulse is, at different depths and for different first-time readers. Not feature tours, outcome pitches or how-tos.

1. **Kite Pulse on One Page** — What Kite Pulse is in one sitting: it picks up the session history AI coding tools already keep, masks secrets, sends it to a server your team runs, and shows who is working on what, how AI tools are used, what they cost, how close people are to their Claude plan limits and where work gets stuck. *Reader:* anyone meeting the product for the first time.
2. **The Three Parts of Kite Pulse: Desktop Program, Your Server, Web Console** — The architecture in plain words, and why the three parts depend on one another (an install without the desktop program has nothing to show). *Reader:* technical evaluators and IT.
3. **From a Developer's Laptop to the Console: a Session's Journey in Six Steps** — One session from start to finish: work as usual, new activity noticed, consent first, secrets masked and upload encrypted, a second mask on the server, and pages by role; plus what happens when the network drops. *Reader:* evaluators, privacy reviewers, curious developers.
4. **Kite Pulse Explained for Someone New to AI Coding Assistants** — A primer on AI coding sessions, why tools keep their history, what tokens are and why they drive cost, and what a Claude plan limit is. *Reader:* finance, HR, leadership and other non-engineering readers.
5. **Kite Pulse in Five Minutes for Leaders** — What the product is, which questions it answers from real sessions, and what it needs from the organisation (a self-hosted server, an admin, each developer's consent). No promised returns. *Reader:* executives and budget holders.
6. **How Kite Pulse Is Different from Other Engineering Tools** — Most tools judge outputs; Kite Pulse reads the process inside the AI session, across ten tools, with nothing for developers to fill in, on a self-hosted server, with AI features opt-in. *Reader:* evaluators comparing products.
7. **What Kite Pulse Is Not** — Not a keystroke logger, screen recorder, website tracker, code-quality scanner or ranking tool; not your vendor's invoice; not single sign-on. Names the optional reads that do open project notes and package lists. *Reader:* sceptical developers, works councils, security reviewers.
8. **Kite Pulse Terms in Plain Words** — Session, active time, token, tool account, scope, access role, client code, Onboarding Wizard, plan headroom, working style, insight, desktop program, console. *Reader:* every new user, and writers of rollout notes.
9. **Where the Numbers Come From** — How each headline figure is produced and how far to trust it: token counts from each tool, cost as a per-tool list-price estimate (“not billed spend”, no cross-tool total), Claude-only plan figures with old readings flagged, and “not enough data” instead of guesses. *Reader:* finance, managers and anyone who will quote a figure.
10. **Who Sees What: Roles and Scope in Kite Pulse** — Developer, Manager and Admin; what scope means; server-enforced limits; private fields; and per-page adjustment by admins. *Reader:* developers and managers before rollout.
11. **One Loop: Capture, Understand, Act, Learn** — How every feature reads the same sessions so figures agree, how people act on them, and how next week's sessions show whether the action worked. *Reader:* decision-makers who want the whole picture first.
12. **A Map of the Console** — An orientation to the menu in the order people meet it, noting which areas are for every role and which for managers or admins by default. *Reader:* new users finding their way around.
13. **How Kite Pulse Treats Your Data** — The trust model: session records only, consent first, secrets masked twice, encrypted in transit to your own server, disguised tool accounts, private prompt statistics, and the Privacy page. No claim of encryption at rest. *Reader:* developers, privacy officers and IT.
14. **Self-Hosted by Design: Where Kite Pulse Runs** — One computer, a local-network pilot, an Ubuntu server with self-renewing HTTPS, your own AWS account, or server only; Windows and macOS desktop program; any modern browser. *Reader:* IT and security decision-makers.
15. **On by Default, Off Until Switched On** — What works the moment it is installed, and what waits for an admin or the server operator (extra reads, AI labelling, the Brain, agent keys, user sync, real deletion). *Reader:* admins planning a rollout, evaluators.
16. **First Questions About Kite Pulse, Answered** — Does it read my source code? Can my manager see what I typed? Does data go to a vendor? Do we need an AI service? Are costs exact? Which plan limits? Why are my pages empty? Can one person use it alone? *Reader:* anyone at evaluation or rollout.

## 2. Features and Capabilities

One article per feature area, explaining what it does and how it works. The Office, the Organizational Brain, AI labelling and knowledge, the Agent API and MCP, Connectors, per-tool integrations, user sync and Slack/email delivery live in categories 8–10.

**Capture and collection**

1. **The Desktop Program: Quiet Capture, Tray Icon, Self-Updates and Offline Catch-up** — Starts with the computer, sends only new activity, catches up after the network drops, updates itself from your own server (checked before install), and offers Open dashboard, View log, Re-enter code and Run diagnostics from the tray. *Reader:* IT and developers.
2. **Automatic Project Detection** — How project folders and repository addresses are recognised, one repository on two laptops counts as one project, and Duplicate Detection merges or splits folders. *Reader:* developers and admins.
3. **Deciding What Gets Collected: Tool Switches, Counts-Only Mode and Optional Reads** — Switching tools off, collecting token counts only, and the one tab where each extra read is switched on. *Reader:* admins, IT and privacy officers. *Optional parts:* every extra read is off until an admin turns it on.

**Your own pages**

4. **Workspace: Is My Work Being Captured?** — Each project's state, upload retries with reasons, what is waiting per computer, next setup step, own Claude plan usage, and My Projects, Pending Requests and Project Detection. *Reader:* developers.
5. **My Scorecard & Insights: a Top 3 to Act On** — Verdict, reason, evidence and what to try, “not enough data” instead of guesses, productivity tiles, and the verification signal. *Reader:* developers. *Optional parts:* the verification signal needs AI labelling.
6. **How You Work: My Activity, Work Patterns, Working Style and Private Prompt Statistics** — When and with which tools you worked, peak hour, streaks, deep focus, parallel sessions, your working style, and prompt statistics only you see. *Reader:* developers.
7. **My Sessions: Finding the Session You Need** — Every session with a summary, filters by tool, model, session type and label, and main-versus-parallel time. *Reader:* developers. *Optional parts:* AI labels need AI labelling.
8. **Inside One Session: Playback, Summary and Segments** — Turn-by-turn replay with a timeline and inline sub-agent conversations (Claude Code), a no-AI Summary, Segments, and sub-agent links. *Reader:* developers reviewing their own work. *Optional parts:* the Labels tab needs AI labelling.
9. **What the Agent Did: a Step-by-Step Record Without Message Text** — Every step the AI took, in order, on every session page and from a desk in The Office; routine steps fold away, errors always show, message text never appears. *Reader:* developers and team leads.
10. **Notices in the Bell: Plan Limit Reached, AI Agent Stuck and Claude Code Out of Date** — The three notices that arrive without setup, who receives each, the inbox and Needs attention; admins decide who is told what. *Reader:* developers and their managers. *Optional parts:* the server operator can change the stuck interval or turn it off.

**Team and organisation views**

11. **Team Overview, All Developers and Organisation Overview** — Live team status against a typical day, everyone in scope with roster export, and the company-wide picture with Summary and Activity Overview. *Reader:* team leads, managers and directors. *Optional parts:* Organisation Overview is admin-only by default.
12. **The Developer Page: One Person in Full** — The person's report without private fields, Detection and Collection tabs, session labels, exports, and Agents in parallel (how many agents and sub-agents are working or waiting, with a day's lane chart). *Reader:* engineering managers and admins. *Optional parts:* several tabs are admin-only by default.
13. **Collaboration, Teams, and Leave & On-Call** — Shared projects and contributors, dated team membership, and leave and duty rotas so activity is read fairly. *Reader:* team leads and managers.
14. **Work Problems, Insight Rules and the Insights Catalog** — Rule-based detection of failing commands and retries with suggested actions, admin-tuned insight rules, and what each insight means and who may see it. *Reader:* team leads and platform owners. *Optional parts:* Work Problems is admin-only by default.
15. **Workflows & Pain Points: Where Work Repeats and Where It Slows Down** — Repeated work shapes, prompts and commands; inefficiencies, longest sessions, hot files and stuck weeks; quality checks. *Reader:* engineering managers and DevEx leads. *Optional parts:* admin-only by default.

**Projects**

16. **All Projects and the Project Page** — Health, sessions, contributors, last activity, phase and blockers, and the summary card on each project page. *Reader:* engineering managers. *Optional parts:* phase, risk, blockers and duplicate work need AI labelling.
17. **Keeping the Project List True: Approvals, Project Actions and Removed Projects** — Onboarding and project approvals, Add project, merge, split, pause and delete with a cancellable grace period, bulk actions, Removed Projects, Project Mapping and Detection Rules. *Reader:* admins and approvers.

**AI usage, cost and budgets**

18. **Team AI Usage: Tokens by Person, Tool, Model, Project and Day** — The usage page and its tabs, including model adoption over time and which Claude Code agent features sessions used. *Reader:* managers, finance and technology leaders.
19. **How Estimated Cost per Tool Works** — List prices for Claude and Gemini models, or the tool's own reported cost for Aider, Cline, Roo Code, Kilo Code and OpenCode; labelled “not billed spend”, shown per tool, never totalled across tools. *Reader:* finance and budget holders.
20. **The Token Pace Line: Where Token Use Is Heading** — 14-day average, 30-day outlook and a marker on unusually heavy days. Tokens, not money. *Reader:* managers and finance.
21. **AI Budgets: Monthly Limits per Team or Project** — Tokens or estimated dollars, with alerts at 80% and 100%. *Reader:* finance and budget holders.
22. **Tool Accounts: Shared, Separate and Personal Accounts** — Accounts per tool, shared accounts, plan tier and email domain for five tools, disguised by default. *Reader:* finance, procurement and admins. *Optional parts:* the Copilot plan name needs its optional read.
23. **Hourly Rates & Seat Prices** — Seat costs per tool and hourly cost per role level, never per person, dated and recorded. *Reader:* finance and admins.
24. **Generation Rate: How Fast AI Replies Arrive** — Tokens per second on session pages and usage sections, Claude Code only. *Reader:* technology leaders and DevEx teams. *Optional parts:* admin switch; each developer opts in.
25. **Agent Setup: Claude Code Skills, Commands, Agents and MCP Servers Across the Team** — What is installed across machines, read alongside what sessions actually use. *Reader:* DevEx and platform teams. *Optional parts:* needs its optional read (admin switch).

**Claude plan limits**

26. **Plan Headroom: Seeing Claude Plan Limits Before They Bite** — 5-hour, weekly and per-model windows, worst first; account names, reasons a reading is old, live tags, own figures on Workspace. Claude Code only. *Reader:* technical leads and developers. *Optional parts:* background refresh is an admin switch; developers can opt out.
27. **The Plan Usage Report and Plan Reading History** — Usage per developer and Claude account for up to two years, peaks, extra usage and a day-by-day chart, and how long readings are kept. *Reader:* finance and engineering leadership. *Optional parts:* Excel download is admin-only by default.

**Reports**

28. **Company Reports and Scheduled Reports** — Any period against the one before, delivered by email daily, weekly or monthly as PDF or CSV, with preview and send history. *Reader:* engineering managers and leadership. *Optional parts:* downloads and schedules are admin by default.

**Administration and security**

29. **Who Sees What: Roles & Permissions, Accounts and Sign-in** — The permissions grid, Accounts & Roles, delegated account management, sign-up modes, and sign-in rules. *Reader:* admins and IT.
30. **Knowing the System Is Healthy: Infrastructure, Alerts, Machines and Processing** — Automatic checks, the shared alert workflow, thresholds, delivery history, Machines, Data Collection, Processing and Server Storage. *Reader:* admins and IT.
31. **Data Rights: Export, Erase, Audit Log and Retention** — What export and erase do, the audit log that cannot be edited, and retention per kind of data. *Reader:* admins and data-protection officers. *Optional parts:* real deletion of session data is turned on by the server operator.
32. **Leaked Credentials and Security Watch** — Masked keys found in AI conversations with a status to track, plus unchecked sensitive changes and pasted secrets or personal data, counts and identifiers only. *Reader:* security teams and admins. *Optional parts:* the list fills when the server operator runs a scan; the two tabs need AI labelling.

## 3. Use Cases and Real-World Applications

Each article tells one concrete situation as a short story: who was involved, what happened, which features they used, and what changed. All names and numbers are illustrations, not customer results.

1. **The Stuck Agent Caught Before Lunch** — A lead sees one agent head down on The Office's meeting-room screen, opens its desk and “What the agent did”, spots the repeated failing command, and helps the developer before the morning is gone, without reading message text. *Reader:* team leads.
2. **Moving the Migration to Monday: a Plan-Limit Save** — Plan headroom shows two developers past 85% of their weekly Claude limit, so a large migration moves to Monday; when a window does run out, a notice gives the reset time. *Reader:* team leads and engineering managers. *Optional parts:* Claude Code only; fresher figures need the background refresh (admin switch).
3. **The Test the AI Retried Six Times** — A developer's scorecard points at one test command retried six times; she fixes the setup once and her failures drop. *Reader:* developers.
4. **One Build Error, Three Developers, Two Projects** — Work Problems shows one build error hitting three people, raised as one fix to the platform team. *Reader:* engineering managers and platform teams. *Optional parts:* admin-only by default.
5. **“payments” and “payments-api” Were the Same Project** — Duplicate Detection flags two folders with one repository address; merged, the project shows its four real contributors. *Reader:* admins and project owners.
6. **The Shared Cursor Seat and the Budget at 80%** — Finance finds a Cursor account used by two people and a team at 80% of its AI budget, buys the seat and talks to the team in time. *Reader:* finance and budget holders.
7. **Before the Only Expert Moves Teams** — Capability ownership shows a part only one person edits; a knowledge-capture request from Tenure & Departure gets the hand-over done before the move. *Reader:* engineering managers and admins. *Optional parts:* owned knowledge records need AI labelling.
8. **A New Joiner's First Afternoon with the Brain** — A new developer uses the Graph, reads the release SOP in Documents, and asks a colleague's agent about her recent work before asking her one sharp question. *Reader:* new joiners and their leads. *Optional parts:* Brain must be on (admin switch).
9. **The Week of Work That Was Not Missing** — Workspace shows a new project detected but not syncing; confirmed in My Projects, the work is on the record from that day. *Reader:* developers.
10. **A Live Key in an AI Conversation** — An admin finds a masked key pasted into an AI session on Leaked Credentials, tracks it to resolution and checks unchecked sensitive changes. *Reader:* security and IT. *Optional parts:* the list fills when the server operator runs a scan; Security watch tabs need AI labelling.
11. **The Friday Spreadsheet Nobody Builds Any More** — Leadership receives a scheduled company report by email instead of a hand-built spreadsheet. *Reader:* executives and engineering managers. *Optional parts:* admins set up schedules.
12. **Two People, One Service, One Stand-up** — Team Overview and Collaboration show two developers in the same service; they are paired before they collide. *Reader:* team leads.
13. **From a Repeated Workflow to a Team Skill** — Skill Candidates proposes a draft Claude Code skill from a repeated workflow; approved, the team stops re-typing the same steps. *Reader:* DevEx and platform teams.
14. **The Two-Hour Session That Went in Circles** — A developer replays a looping session with Playback and “What the agent did” and writes a clearer prompt next time. *Reader:* developers.
15. **A Manager Who Asks Her Own Assistant** — A manager connects Claude Code to Kite Pulse with her own key and asks which projects had the most tool-call failures this month, answered within her own view. *Reader:* engineering managers. *Optional parts:* server operator turns it on; Chat mode or Direct access is an admin choice.

## 4. Benefits for Individual Developers

What a developer gets out of Kite Pulse for their own work and day: the outcome, told from the developer's seat, not a tour of the pages.

1. **Never Lose Credit for Work You Did with AI** — When much of your work happens inside AI conversations, it can vanish from the record; Workspace shows project by project that your work is detected, syncing and processed, and My Projects lets you fix anything missing. *Reader:* developers on a team that uses Kite Pulse.
2. **Get Better Privately: a Top 3 to Try, with the Evidence** — My Scorecard gives a short list of things worth changing, each with a verdict, the reason, the evidence and what to try, and says “not enough data” rather than guessing. *Reader:* developers who want to sharpen how they work with AI.
3. **See Your Own Working Rhythm Clearly** — Work-pattern facts (peak hour, busiest day, streaks, deep-focus sessions, parallel sessions, short bursts) and your working style show how you actually spend time with AI; prompt statistics are shown only to you. *Reader:* developers curious about their own habits.
4. **Stop Losing Half a Day to a Claude Plan Limit** — Check your own Claude plan usage before a long task, and get a notice naming the window and its reset time the moment one runs out. Claude Code plan limits only. *Reader:* developers on Claude plans. *Optional parts:* fresher figures need the background plan refresh (admin switch); developers can opt out.
5. **Catch a Stuck Agent in Half an Hour, Not at the End of the Day** — After 30 minutes stuck on the same problem you get a notice naming the project, and “What the agent did” shows the stuck stretch step by step. *Reader:* developers who leave agents running. *Optional parts:* the server operator can change the interval or turn it off.
6. **Learn from the Session That Went in Circles** — Session Playback, the rule-based Session Summary and “What the agent did” let you look back at a session that went wrong and write a better request next time; secrets stay masked. *Reader:* developers reviewing their own work. *Optional parts:* the Labels tab needs AI labelling.
7. **Are You Checking What the AI Writes? A Private Verification Signal** — How often you reviewed or tested the AI's output, with counts of checks and corrections: an honest read on a habit that is easy to let slip. *Reader:* developers who rely heavily on AI edits. *Optional parts:* needs AI labelling.
8. **One Place for All Your AI Work, Whichever Tool You Used** — Claude Code in the morning and Cursor in the afternoon still land in one timeline under the right project, filtered by tool, model or session type. *Reader:* developers using more than one of the ten supported tools.
9. **End the Day Knowing What You Left Open** — My Day lays out what you worked on, started, finished and left open, where you got stuck and what you learned, visible only to you. *Reader:* developers juggling several threads. *Optional parts:* needs AI labelling.
10. **No Timesheets, No Status Updates** — Capture runs in the background, and The Office and Team Overview show your work in motion, so you spend less time reporting and more time doing. *Reader:* developers tired of status rituals.
11. **You Stay in Control of What Is Collected** — You choose which projects sync, nothing is sent before you confirm, secrets are masked twice, and the Privacy page shows every data point about you and who can see it. *Reader:* developers wary of workplace monitoring. *Optional parts:* “Who asked my agent” needs the Brain on (admin switch).
12. **Get Up to Speed on a New Project Without a Week of Asking Around** — The Brain's Graph shows who works on what, Documents holds the team's SOPs, and asking a teammate's agent shows their recent synced work, so your one question to them is a sharp one. *Reader:* developers joining a project or team. *Optional parts:* Brain must be on (admin switch).
13. **Stay on a Current Claude Code Without Watching Release Notes** — A “Claude Code out of date” notice tells you when your build is behind the stable release and clears once you update. *Reader:* developers using Claude Code.
14. **Personal Insight on Your Own Laptop, with Nobody Else's Server** — Kite Pulse runs entirely on one computer for one person, with the same personal pages and no vendor cloud. *Reader:* freelancers and solo developers.

## 5. Benefits for Development Teams and Managers

The outcome for team leads, engineering managers and the budget holders inside engineering: better-run teams, a fairer reading of the work, and spend that stays on plan.

1. **Stand-ups That Start from Facts, Not Round-the-Room Updates** — Team Overview and The Office show who is online, coding, stuck or needs attention before the meeting starts, so the stand-up goes to solving problems. *Reader:* team leads.
2. **Help a Stuck Developer Without Reading Their Conversation** — The manager gets the same “AI agent stuck” notice, and “What the agent did” shows tools, commands, errors and the stuck stretch with no message text. *Reader:* team leads and engineering managers.
3. **Plan Sprints Around Real Limits** — Plan headroom shows who is near a Claude plan limit, worst first, and the plan usage report shows past peaks, so heavy work moves before it stalls. Claude Code only. *Reader:* engineering managers. *Optional parts:* downloading the report is admin-only by default.
4. **Read Activity Fairly: Leave, On-Call and Team Moves** — Leave & On-Call keeps a holiday from looking like disengagement, dated team membership keeps history accurate, and insights say “not enough data” rather than guess. *Reader:* engineering managers and team leads.
5. **Fix the System, Not the Person** — Work Problems groups failing commands and retries with suggested actions, and the Blocker Board turns recurring causes of lost time into cards that never name a person. *Reader:* team leads and platform owners. *Optional parts:* admin-only by default; the Blocker Board needs AI labelling and suggestion rules switched on.
6. **Stop Two People Building the Same Thing** — Collaboration shows which projects several people are in and how much each spent there, and the project page flags duplicate work. *Reader:* team leads. *Optional parts:* duplicate work needs AI labelling.
7. **Know Which Projects Are Alive Without Chasing Anyone** — All Projects shows each project as active, stable or dormant, with contributors, sessions, last activity and open blockers, and Duplicate Detection keeps one repository from being counted twice. *Reader:* engineering managers. *Optional parts:* phase, risk and blocker figures need AI labelling.
8. **Is the Team's Work with AI Getting Better?** — Trends, Team Review and AI Collaboration show completion, friction and checked changes over weeks and months, pooled and never per person. *Reader:* engineering managers. *Optional parts:* need AI labelling; Team Review and AI Collaboration are admin-only by default.
9. **Better One-to-Ones from the Same Report the Developer Sees** — A developer's page shows the report that person sees, without private fields, so a one-to-one starts from shared facts. *Reader:* engineering managers.
10. **Keep the Team's AI Budget on Plan** — Monthly budgets per team or project alert at 80% and 100%, and the token pace line shows where usage is heading over the next 30 days. *Reader:* engineering budget holders. *Optional parts:* budgets are set by admins.
11. **Spot the One-Person Parts of Your Product Before They Hurt** — Capability ownership shows who edits and reads each capability, each person's share and the bus factor, with a hand-over hint. No AI model. *Reader:* engineering managers and tech leads. *Optional parts:* admin-only by default.
12. **Report Upward Without Building a Spreadsheet** — The company report compares any period with the one before, and scheduled reports email it daily, weekly or monthly. *Reader:* managers reporting to leadership. *Optional parts:* downloads and schedules are admin by default.
13. **Invest in the Tooling Your Team Actually Uses** — Models, Agent features and Agent Setup show which models, Claude Code features, skills and MCP servers the team relies on, and Skill Candidates turns repeated workflows into draft skills. *Reader:* developer-experience and platform leads. *Optional parts:* Agent Setup needs its optional read (admin switch).

## 6. Benefits for Organizations

The outcome at company level: for leadership, company finance, HR and people teams, security and IT, and the organisation's culture and knowledge.

1. **Decisions Based on What Happened, Not on Self-Reports** — Organisation Overview, the company report and Trends draw on the sessions themselves rather than surveys or estimates. *Reader:* executives and engineering leadership. *Optional parts:* Trends label measures need AI labelling.
2. **One Set of Figures Everyone Agrees On** — Every page reads the same sessions, so The Office, team pages, usage and project health never contradict each other. *Reader:* leadership and anyone who has sat through a numbers dispute.
3. **Turn the One-Line AI Bill into a Breakdown** — Token use by person, project, tool, model and period, with an estimated cost per tool, gives finance a view of where AI money goes. Labelled “not billed spend”. *Reader:* company finance.
4. **Find Shared, Personal and Idle Seats** — Tool Accounts marks shared accounts and reveals personal accounts used for work, and seat prices sit beside usage. Covers Claude Code, Codex, Cursor, OpenCode and GitHub Copilot. *Reader:* finance and procurement.
5. **See Real AI Adoption Across the Company** — Which AI tools and models are actually used, how that changes over time and which models each project relies on. *Reader:* executives and technology leaders.
6. **A Measurement Culture That Describes Work Instead of Ranking People** — Team views never single out a person, pooled measures hold back small teams, and the Insights Catalog says who may see each insight. *Reader:* HR, people teams and works councils.
7. **Developer Buy-in Through Visible Privacy** — Consent before sync, no keystrokes, screenshots or source files read, secrets masked twice and a Privacy page per person make a tool developers accept, which keeps the figures complete. *Reader:* HR, works councils and leaders planning a rollout.
8. **Keep What the Organisation Learns** — Knowledge records, the Capability Map and draft skills keep one person's discovery for the next, and the optional Brain lets anyone explore it within their own access. *Reader:* leadership and knowledge owners. *Optional parts:* knowledge records need AI labelling; the Brain must be on (admin switch).
9. **When Someone Leaves, Their Know-how Does Not** — The departure report lists capabilities at risk, records owned and files only they edited, and capture requests ask the person to write knowledge down before they go. *Reader:* HR and managers planning a hand-over. *Optional parts:* admin-only by default.
10. **Catch Leaked Credentials and Pasted Personal Data** — Leaked Credentials tracks masked keys found in AI conversations, and Security watch lists prompts where someone pasted a secret or personal data, counts and identifiers only. *Reader:* security teams. *Optional parts:* the main list fills when the server operator runs a scan; Security watch needs AI labelling.
11. **Your Data Stays on Infrastructure You Control** — Kite Pulse runs on your own computer, network or cloud account with no vendor cloud in between, so data residency is your choice. *Reader:* IT and security decision-makers.
12. **Clear Accountability for Who Sees What** — A per-page permissions grid, an audit log that cannot be edited, retention per kind of data, and export or erasure of one person's data on request. *Reader:* IT, security and data-protection officers. *Optional parts:* real deletion of session data is turned on by the server operator.
13. **Know the System Is Healthy Before Users Tell You** — Automatic checks raise alerts for stalled processing, low memory or disk, silent collectors and failed sign-ins, on one shared alert list. *Reader:* IT and platform administrators. *Optional parts:* email needs the operator to set up mail; Slack alerts are an admin switch.
14. **Adopt AI Analysis at a Pace You Control** — Everything core works with no AI service, and each AI feature is opt-in with its own monthly cap and admin approval, so there is no open-ended bill. *Reader:* security, procurement and leadership. *Optional parts:* AI labelling needs a key an admin enters on Classification; Brain Chat needs a key from the server operator.

## 7. Problems the Product Solves

Pain first: each article starts from one problem teams have today, explains why it exists now that work happens with AI assistants, and then shows how Kite Pulse addresses it.

1. **The Work Moved into AI Conversations, and Your Visibility Did Not Follow** — Commits, pull requests and tickets show only what came out the other end; Kite Pulse reads the AI sessions themselves, with consent, to show the process. *Reader:* engineering leaders meeting the problem for the first time.
2. **More Commits, Same Delivery Speed: Where Did the Time Go?** — Retries and dead ends inside AI sessions are invisible to output counts; Kite Pulse measures active time, sessions, retries and stuck stretches. *Reader:* engineering managers and leadership.
3. **The AI Bill Nobody Can Break Down** — Several tools, subscriptions and shared accounts become one opaque line; Kite Pulse shows token use by person, project, tool and model, estimated cost per tool, shared accounts and budgets. *Reader:* finance and budget holders.
4. **The Plan Limit That Ends Your Afternoon** — Developers find out a Claude plan window is used up only when work stops; Kite Pulse shows how close each person is and sends a notice with the reset time. Claude Code only. *Reader:* developers and leads on Claude plans.
5. **Ten AI Tools, Ten Histories, No Single Picture** — Each tool keeps its own records in its own format; Kite Pulse brings ten tools into one timeline, with one repository on two laptops counted as one project. *Reader:* teams using a mix of AI tools.
6. **The Agent That Sat Stuck While You Were in a Meeting** — Agents now run unattended and can loop for hours; Kite Pulse notices after 30 minutes, tells the person and their manager, and shows the stuck stretch. *Reader:* developers and team leads.
7. **The Same Failure, Fought Separately by Three People** — A broken build surfaces weeks later in a status meeting; Kite Pulse groups failing commands and retries across the team and points at the shared cause. *Reader:* team leads and platform owners. *Optional parts:* Work Problems is admin by default; the Blocker Board needs AI labelling.
8. **Solving the Same Bug Twice** — The answer lived in one person's chat history; knowledge records quoted from real sessions keep it findable. *Reader:* engineering managers and knowledge owners. *Optional parts:* needs AI labelling.
9. **When the Only Person Who Knows Moves On** — Parts of a product quietly depend on one person; capability ownership shows the bus factor and the departure report lists what is at risk while there is time. *Reader:* managers and admins. *Optional parts:* admin-only by default.
10. **Project Status by Guesswork** — Which projects are active is usually answered from memory; All Projects lists every project with health, contributors and last activity, and duplicates are merged. *Reader:* engineering managers.
11. **AI-Written Changes Nobody Checked** — Unreviewed changes, including security-sensitive ones, slip through; the verification signal, the Session Summary and Security watch make them visible. *Reader:* tech leads and security teams. *Optional parts:* the verification signal and Security watch need AI labelling.
12. **Secrets Pasted into AI Chats** — Keys and personal data get pasted into prompts to get unstuck; Kite Pulse masks known secrets twice and lists leaked credentials and pasted secrets for follow-up. *Reader:* security teams. *Optional parts:* the list fills when the server operator runs a scan; the pasted-secrets tab needs AI labelling.
13. **Visibility Tools Developers Fight** — Keystroke and screen loggers breed resistance and incomplete data; Kite Pulse reads only the AI tools' own records, asks for consent and shows each person what is collected. *Reader:* leaders who have seen a monitoring rollout fail.
14. **Status Meetings and Timesheets as the Only Source of Truth** — When the only way to know is to ask, people spend hours reporting; Kite Pulse builds the picture from the sessions. *Reader:* team leads and developers.
15. **The New Joiner Who Spends a Week Asking Around** — Who owns what is tribal knowledge; the Organizational Brain puts people, projects and documents in one map anyone can explore within their access. *Reader:* managers onboarding people. *Optional parts:* Brain must be on (admin switch).
16. **A Monthly AI Budget Discovered Too Late** — Teams learn they overspent when the month closes; budgets alert at 80% and 100%, and the token pace line shows where usage is heading. *Reader:* engineering budget holders. *Optional parts:* budgets are set by admins.

## 8. Organizational Brain and AI-Powered Intelligence

How Kite Pulse turns sessions into shared understanding: the optional Organizational Brain, the optional AI labelling layer and what it unlocks, and the knowledge features, many of which use no AI at all.

1. **The Organizational Brain: One Map of Your Company That Respects Who May See What** — What the Brain is, how an admin switches it on with one click, and why every map and answer leaves out anything the viewer may not read. *Reader:* executives, admins and evaluators. *Optional parts:* off by default (admin switch).
2. **Exploring the Brain Graph: How Departments, People, Projects and Tools Connect** — The interactive map, its full-screen mode, and its place on The Office's wall screen. No AI. *Reader:* new joiners, team leads and leadership. *Optional parts:* Brain must be on.
3. **Teaching the Brain: Documents and Project Context** — Uploading policies, playbooks and SOPs for the company, a department or a project (secrets masked), and adding objectives, strategy and status to project pages. *Reader:* department leads, managers and project owners. *Optional parts:* Brain must be on.
4. **Brain Agents: Focused Ways to Ask, from People & Org to an HR Policy Helper** — The four built-in agents and department agents that only read and answer and never widen access. *Reader:* department leads and admins. *Optional parts:* Brain must be on.
5. **Brain Chat: Ask the Organisation a Question and See Every Source** — Answers that cite knowledge records, project context, profiles, documents and connected Jira, HubSpot or Slack items, permission-checked first, within a monthly budget ($20 by default). *Reader:* anyone looking for an answer inside the company. *Optional parts:* Brain must be on, plus an AI key from the server operator.
6. **Ask a Teammate's Agent, and See Who Asked Yours** — Questions about a colleague's last 14 days of synced work on shared projects, never message text; the colleague sees every question and can pause their agent. *Reader:* developers. *Optional parts:* Brain must be on.
7. **Your Brain Profile: What the Organisation Knows About You** — The five tabs of a person page, including the exact AI Context text, and who edits what. *Reader:* every person. *Optional parts:* Brain must be on.
8. **Governing the Brain: What It Holds, Who Read It and How Long It Remembers** — Per-department holdings and readers, plus budget, model and keep periods. *Reader:* admins, department leads and compliance owners. *Optional parts:* Brain must be on.
9. **AI Labelling, Done Carefully: Approved Label Lists, a Spending Cap and a Confidence Bar** — How work is labelled by type and outcome, with admin approval of every list and “unknown” instead of guesses. *Reader:* admins and technical leads. *Optional parts:* off until an admin sets it up with a provider key.
10. **Checking the Labeller: Review Labels, the AI Call Log and Classification Reports** — Correcting uncertain answers, seeing every AI call, and spend, coverage and model scores. *Reader:* admins and anyone asked to trust AI-made figures. *Optional parts:* needs AI labelling.
11. **From Facts to Advice: Fact Rules, Suggestion Rules and the Blocker Board** — Free no-AI fact rules, and approved suggestion rules that fill the Blocker Board with causes and actions, never a person. *Reader:* team leads and platform owners. *Optional parts:* suggestion rules and the Blocker Board need AI labelling.
12. **What Labels Tell a Team: Trends, Team Review and AI Collaboration** — Pooled measures of completion, win rate, friction and checked changes over weeks and months; small teams held back. *Reader:* engineering managers and team leads. *Optional parts:* needs AI labelling; Team Review and AI Collaboration are admin-only by default.
13. **What Labels Tell One Person: My Day, the Verification Signal and Profile Facts** — A private daily summary, how often you check the AI's output, and skills and areas on the developer page. *Reader:* developers, and admins supporting them. *Optional parts:* needs AI labelling.
14. **Knowledge Records: Lessons Quoted from Real Sessions, Linked to Where They Came From** — What the organisation learned, with links to sessions and commits. *Reader:* engineering managers and knowledge owners. *Optional parts:* needs AI labelling; admin-only by default.
15. **Keeping Knowledge Current: the Weekly Knowledge Log and Coherence Checks** — The week's new records by kind, the “captured this week” card, and flags for duplicate, contradicting or out-of-date records. *Reader:* knowledge owners and tech leads. *Optional parts:* needs AI labelling.
16. **The Capability Map: Describing Each Product in Plain Terms** — Modules, capabilities and scenarios with full change history. No AI. *Reader:* product owners, architects and engineering managers.
17. **Who Really Knows This Part? Capability Ownership and the Bus Factor** — Who edits and reads each capability, shares of edits, bus factor and hand-over hints; owners accept or decline. No AI. *Reader:* engineering managers planning resilience.
18. **When Someone Moves On: Tenure, the Departure Report and Knowledge-Capture Requests** — Time in organisation, team and project; what is at risk; requests to write knowledge down. Facts only. *Reader:* managers and admins planning a hand-over. *Optional parts:* admin-only by default; works without the Brain.
19. **Project Notes: Every Version of CLAUDE.md, AGENTS.md, README and Decision Records** — A project's own written knowledge by version, with changes, secrets masked and every read recorded. *Reader:* tech leads and architects. *Optional parts:* project-notes read is an admin switch.
20. **From Repeated Work to Reusable Skills: Session Graph and Skill Candidates** — Similar sessions grouped daily and draft Claude Code skills from repeated workflows. No AI. *Reader:* DevEx and platform teams.
21. **Intelligence Without an AI Service: What Works With No Key at All** — Everything that runs with no AI, and the two things that need a key (AI labelling and Brain Chat). *Reader:* security, procurement and sceptical evaluators.
22. **Keeping Kite Pulse's Own AI Spend in Check** — The labelling cap, the Brain Chat budget and the separate key for agent questions. *Reader:* admins and finance owners. *Optional parts:* each applies only when its feature is on.

## 9. 3D Visualization and Live Updates

The Office, the live home page where each person's AI agent sits at a desk, and the live updates that keep it and the team pages current.

1. **The Office: a Live 3D Office Where Every Desk Is an AI Agent** — The default home page for every role: rooms of desks, each with a person's AI agent rather than the person, so the team's work shows at a glance. *Reader:* everyone, and buyers wanting to know what the home page is.
2. **Reading an Agent's Body Language** — Typing, reading, watching, supervising sub-agents or waiting; the lounge when away or at a plan limit; head down when stuck; walking in and out; a parcel on a code push. *Reader:* every Office user.
3. **One Marker per Desk: What “!”, a Thought Cloud and “Update” Are Telling You** — Attention, stuck, plan limit, near limit, waiting, syncing and out-of-date markers, task lines on zoom, and clicking a room to focus. *Reader:* team leads and developers. *Optional parts:* stuck and plan detail only within your scope.
4. **Live Without Pressing Refresh: How The Office and Team Overview Stay Current** — Push updates within seconds, the “Live” badge, the 15-second fallback with automatic reconnection, Team Overview's 30-second refresh, and the honest limit: figures are as fresh as each computer's latest upload. *Reader:* team leads and technical evaluators.
5. **The Office on the Wall: Full-Screen Mode for a TV or Meeting Room** — A menu-free wall screen with daylight or evening themes for stand-ups and team rooms. *Reader:* team leads running a team room. *Optional parts:* the Brain view needs the Brain on.
6. **3D, Map, List, Headroom and Brain: One Office, Five Ways to Look** — The view switch, including a List for phones and a Headroom board of everyone's Claude plan usage. *Reader:* everyone, including people on phones. *Optional parts:* Headroom is for managers and admins; the Brain tab needs the Brain on.
7. **Click a Desk: Current Task, Stuck Reasons and Today's Figures in the Side Panel** — Name, presence and tool for everyone; project, task, live step, stuck reasons, plan, sync and today's figures within scope; cost on others' desks for admins only. *Reader:* team leads and managers.
8. **Watching Sub-agents Work: Parallel Agents in The Office** — Sub-agents beside the agent that started them, with kind, model, run time and current step in the panel. *Reader:* developers and leads running parallel AI work. *Optional parts:* detail within scope only.
9. **Catching a Stuck Agent in Half an Hour, Not at Next Week's Stand-up** — How a stuck agent looks in The Office, how “waiting” is worked out from two quiet minutes, and the 30-minute notice to the person and their manager. *Reader:* team leads and developers. *Optional parts:* the server operator can change the interval or turn it off.
10. **The Activity Feed: the Last 24 Hours of the Office in One Stream** — Sessions, tasks, commits, stuck and unstuck agents, approvals, notes and comings and goings (worked out in the browser, never stored). *Reader:* team leads and admins.
11. **The Tasks Board: Work in Progress, Stuck, Waiting, Paused, Failed and Done** — Filtering counters, approvals and uploads awaiting you, and the processing queue and alerts for admins. *Reader:* team leads and admins.
12. **The Office Tab and the Connected Strip: the Team's Figures at a Glance** — Agents, working, stuck, waiting, sessions and commits today, plan counts, notes in the Brain, connectors and skills used, and the AI tools and code hosts in use. *Reader:* team leads and engineering managers.
13. **Finding People Fast: the Team Picker, Filter Tiles and One-Click Team Suggestions** — One team's office, quick filters, and admin team suggestions from who already works together. *Reader:* team leads in larger organisations and admins.
14. **Presence, Not Surveillance: Who Sees What in The Office** — Presence for everyone, detail only within scope, never message text, an admin option to hide others' desks, and no access for agent keys. *Reader:* developers, works councils and privacy officers.

## 10. External API Access and Integrations

How Kite Pulse connects outward and inward: the ten AI coding tools it collects from, the Agent API and MCP for your own AI assistants, Connectors, user sync, and Slack and email delivery.

1. **Ten AI Coding Tools, One Integration Layer** — The ten tools collected out of the box, how their own session history is read, and per-tool controls (switch off, or counts only). *Reader:* technical evaluators and IT.
2. **Kite Pulse for Claude Code Teams** — Claude plan headroom, plan and version notices, the Agent features tab, inline sub-agent conversations, Skill Candidates and Agent Setup. *Reader:* teams standardised on Claude Code. *Optional parts:* plan refresh, generation rate and Agent Setup's read are admin switches.
3. **Kite Pulse for Cursor Teams** — Cursor sessions in the shared timeline, Cursor accounts and plan tier in Tool Accounts, and connecting Cursor to Kite Pulse over MCP. *Reader:* leads and finance on Cursor-heavy teams. *Optional parts:* MCP is turned on by the server operator.
4. **Kite Pulse for GitHub Copilot Users** — Copilot Chat in VS Code alongside other tools, Copilot accounts, the optional Copilot plan read, and connecting VS Code over MCP. *Reader:* organisations on GitHub Copilot. *Optional parts:* plan read is an admin switch; MCP is turned on by the server operator.
5. **Kite Pulse for Codex and Gemini CLI** — Terminal agent sessions captured without extra steps, Codex accounts, Gemini usage priced as an estimate, and models on the Models tab. *Reader:* teams using terminal-based AI agents.
6. **Kite Pulse for Aider, Cline, Roo Code, Kilo Code and OpenCode** — How these tools join the same view and why their cost comes from the tools' own reports. *Reader:* teams using any of these five tools.
7. **Agent API Keys: Letting Your Own AI Assistant Ask Kite Pulse** — Admin-issued keys per person with permissions, expiry and limits, never seeing more than their owner; self-revocation under Account. *Reader:* admins and security reviewers. *Optional parts:* turned on by the server operator.
8. **Chat Mode or Direct Access: Choosing How Much an AI Tool Can Read** — Questions only, answered by Kite Pulse's own assistant, or read access within the owner's view; a separate provider key keeps costs apart. *Reader:* admins and security reviewers. *Optional parts:* admin choice once keys are on.
9. **Connecting Claude Code, Cursor and VS Code to Kite Pulse over MCP** — Ready-made setup, about 115 read tools within the owner's permissions, and what is deliberately not offered over MCP. *Reader:* people who work inside an AI assistant. *Optional parts:* server operator turns it on; an admin issues the key.
10. **Questions Your AI Assistant Can Answer About Engineering** — Team review, blocker board, plan history, costliest turns, model splits, effort per branch, newcomer ramp-up, file hotspots, failure rates, cost reconciliation and time lost to interruptions. *Reader:* managers who work through an AI assistant. *Optional parts:* Direct access is an admin choice; some answers need AI labelling or optional reads.
11. **Reading What the AI Said: the Session-Text Permission and Its Safeguards** — A separate permission with a risk acknowledgement, masked secrets, every read recorded, never over MCP. *Reader:* security reviewers and data-protection officers.
12. **Before and After Handing Out a Key: Try a Question and Agent Activity** — Preview exactly what an AI tool would get back, then see keys, usage and every request in the log. *Reader:* admins and auditors.
13. **Connectors: Linking Jira, HubSpot, Slack, GitHub, Confluence, Google Drive and Notion to Projects** — How admins link them, and how Brain Chat can cite connected Jira, HubSpot and Slack items within the asker's permissions. *Reader:* admins and project owners. *Optional parts:* citations need the Brain on and an AI key.
14. **User Sync with Microsoft Entra ID and Okta** — Accounts created, updated and deactivated automatically; never sets roles or touches admins; provisioning, not single sign-on. *Reader:* IT and identity administrators. *Optional parts:* admin switch.
15. **Server Alerts in Your Slack Channel** — Infrastructure alerts to Slack, the Test button and delivery history. *Reader:* admins and IT on-call. *Optional parts:* admin switch.
16. **Email from Kite Pulse: Notices, Alert Emails, Daily Digests and Scheduled Reports** — The email channel end to end, with admins deciding who is told what. *Reader:* admins and leadership. *Optional parts:* needs the server operator to set up mail.
17. **What Leaves Your Server, Integration by Integration** — Every outward link and the switch that controls it: AI providers, agent keys, Slack, email and user sync. *Reader:* security and IT decision-makers.

## 11. Workflows, Productivity, and Decision-Making

Each article walks through one recurring process run with Kite Pulse, step by step, and names the decisions it informs.

1. **Running the Monday Stand-up from The Office and Team Overview** — Who is online and coding, who needs attention, who works on what; then who to pair, help or unblock. *Reader:* team leads.
2. **Sprint Planning Around Plan Headroom, Leave and On-Call** — Checking plan pressure, leave and recent activity before assigning heavy AI work. Decision: who takes the large tasks, and when. *Reader:* engineering managers and team leads. *Optional parts:* Claude Code only; background refresh is an admin switch.
3. **The Monthly AI Spend and Budget Review** — Usage by team, project, tool and model, the 30-day outlook, budget alerts, Tool Accounts and seat prices. Decisions: adjust budgets; buy, move or cancel seats. *Reader:* finance, budget holders and managers.
4. **From “AI Agent Stuck” Notice to Fix** — Open the desk, read “What the agent did”, restart with a clearer request, check Work Problems. Decision: one person's task or a team-wide fix? *Reader:* developers and team leads.
5. **The Weekly Team Health Review, Without Ranking Anyone** — Team Review, Trends and the Blocker Board. Decision: which shared cause of lost time to fix next. *Reader:* engineering managers. *Optional parts:* needs AI labelling; admin-only by default.
6. **A Release Retrospective Built on Session Evidence** — Workflows & Pain Points, the sessions that hurt, and the knowledge log's new decisions. Decision: what to change before the next release. *Reader:* team leads and managers. *Optional parts:* the knowledge log needs AI labelling.
7. **Onboarding a New Hire, from Account to First Synced Session** — Account, desktop program and KP- code, Onboarding Wizard, approval, and watching Workspace until sessions flow. Decision: which projects the newcomer syncs. *Reader:* managers and admins.
8. **Planning a Hand-over Before Someone Moves On** — Bus factor, the departure report, capture requests and confirming new owners. Decision: who takes over what, and what must be written down first. *Reader:* managers and admins. *Optional parts:* admin-only by default.
9. **The Monthly Project Portfolio Review** — Health, phase and blockers, shared projects, merges and paused projects. Decision: what to staff, pause, merge or retire. *Reader:* managers and admins. *Optional parts:* phase and blockers need AI labelling.
10. **Leadership Reporting on Autopilot** — A rhythm of scheduled company reports and a periodic plan usage report. Decision: where to invest attention and AI budget. *Reader:* managers and executives. *Optional parts:* admins set up schedules.
11. **The Admin's Daily Health Check** — Infrastructure tiles, the alert workflow, Machines, Data Collection and Processing. Decision: what to fix before users notice. *Reader:* admins and IT.
12. **Choosing Which AI Tools and Models to Standardise On** — Models, Agent features, Tool Accounts and seat prices. Decisions: which tools to fund, seats to consolidate, models to recommend. *Reader:* engineering leadership and DevEx leads.
13. **Turning Repeated Work into Team Standards** — Workflows & Pain Points, Skill Candidates, Agent Setup and the Claude Code version check. Decision: what to automate or standardise next. *Reader:* platform and DevEx teams. *Optional parts:* Agent Setup needs its optional read.
14. **A Developer's Own Weekly Review** — Workspace, the Top 3, costly sessions in My Sessions, and My Day. Decision: one habit to change next week. *Reader:* developers. *Optional parts:* My Day needs AI labelling.
15. **Weekly Security Triage of AI Conversations** — Leaked Credentials by status, unchecked sensitive changes and pasted secrets, and follow-up. Decision: which exposures to act on first; masking does not revoke a key at its provider. *Reader:* security and IT. *Optional parts:* scan run by the server operator; tabs need AI labelling.
16. **Keeping the Project List True Week to Week** — Clearing approvals, acting on merges and splits, and reviewing Request History. Decision: which projects are really separate and which should sync. *Reader:* admins and approvers.

## 12. Industry-Specific Applications

How organisations of a given sector or shape could use the features that exist today. None of these articles claims certifications, compliance or features the product lacks.

1. **How Software Agencies and Consultancies Could Use Kite Pulse** — Effort per client project, developer exports for a period, personal accounts used for client work, and client Jira or HubSpot linked to projects. Clarity per engagement, not billing. *Reader:* agency owners and delivery leads.
2. **Self-Hosted AI Development Insight for Finance and Healthcare Teams** — Your own infrastructure, no vendor cloud, secrets masked twice, consent first, an audit log that cannot be edited, and no AI service needed. Explicitly no compliance claims; erasure anonymises rather than removes everything. *Reader:* IT, security and risk leads in regulated organisations.
3. **Running Kite Pulse Across an Enterprise with Many Teams** — Permissions, delegated account management, user sync from Entra ID or Okta (not single sign-on), dated teams, team budgets, Organisation Overview and scheduled reports, in your own AWS account. *Reader:* enterprise engineering leadership and IT.
4. **Kite Pulse for Startups: Small Team, Big AI Bill** — Starting on one machine, watching Claude plan headroom and token pace, a monthly budget, and spotting one-person parts of the product. Some pooled team measures hold back very small teams. *Reader:* founders and first engineering leads.
5. **Distributed and Outsourced Teams Across Time Zones** — Presence and the Activity feed in The Office, Leave & On-Call, work patterns and offline catch-up, with each lead limited to their own reporting line. *Reader:* heads of distributed engineering and vendor managers.
6. **Public Sector and Government IT Teams** — Infrastructure you control, AI features off or opt-in, the audit log, Brain Governance and retention windows. No accreditation claims. *Reader:* public-sector IT and digital teams.
7. **Coding Bootcamps and Engineering Education** — With learners' consent: how a cohort works with AI, Session Playback for guided review, the verification signal, and each learner's own Privacy page. *Reader:* bootcamp and course leads. *Optional parts:* the verification signal needs AI labelling.
8. **Game and Product Studios** — The Capability Map per product, project health across titles, The Office on a studio wall screen, and which AI tools and models each project relies on. *Reader:* studio technical directors and producers.
9. **Platform and Developer-Experience Teams** — Work Problems, Workflows & Pain Points, Agent features, Agent Setup, Skill Candidates, the version check and Machines to find shared friction and roll out standards. *Reader:* platform and DevEx leads.
10. **Independent Developers and Freelancers** — Everything on one computer: a private record of AI-assisted work across tools and projects, own plan usage and scorecard, nothing leaving the machine. *Reader:* solo developers.
11. **IT and Security Teams Watching AI Adoption** — Personal accounts revealed by email domain, Leaked Credentials, Security watch, and tool switches with counts-only collection. *Reader:* CISOs and IT managers. *Optional parts:* the list fills after an operator scan; Security watch needs AI labelling.

## 13. Getting Started and Practical Guides

Step-by-step how-tos, each ending in a working result. Several pair with a feature article in category 2, 8, 9 or 10: the feature article explains what something is, the guide shows how to set it up.

1. **Install Kite Pulse on Your Own Computer in One Command** — Server, console and desktop program on one machine; sign in, set your password, confirm projects and watch sessions appear. *Reader:* individual developers.
2. **Run a Team Pilot on One Machine on Your Local Network** — A pilot server colleagues can reach, accounts, and onboarding the first people with their KP- codes. *Reader:* team leads and admins trialling Kite Pulse.
3. **Set Up a Team Server on Ubuntu or in Your Own AWS Account** — The Ubuntu script with self-renewing HTTPS, the AWS script that shows its plan and asks first, and the server-only option. *Reader:* IT and server operators.
4. **Rolling Kite Pulse Out to Your Team** — Sign-up mode, roles and managers, the Setup checklist, Organisation Name, and onboarding approval. *Reader:* admins leading a rollout. *Optional parts:* user sync is an admin switch and does not replace email-and-password sign-in.
5. **Joining Your Team's Kite Pulse: KP- Code, Onboarding Wizard and First Sync** — Install, enter your code, confirm projects, wait for approval, and why an empty console before then is expected. *Reader:* new team members.
6. **“My Pages Are Empty”: Checking That Your Work Is Being Captured** — Wizard and approval status, project states on Workspace, upload retries, and the tray's View log, Re-enter code and Run diagnostics. *Reader:* developers and the admins helping them.
7. **How to Read Your Scorecard** — The Top 3, verdicts, reasons, evidence and suggestions, “not enough data”, tiles, patterns, working style, and what only you see. *Reader:* developers. *Optional parts:* the verification signal needs AI labelling.
8. **Set Up Monthly AI Budgets, Seat Prices and Hourly Rates** — Budgets with 80% and 100% alerts, seat prices per tool, hourly cost per role level. *Reader:* admins and finance.
9. **Configure Roles, Permissions and Delegated Account Management** — Granting pages to managers, delegating account management, and optionally hiding other people's desks in The Office. *Reader:* admins.
10. **How to Set Up Collection, Step by Step: Tools, Counts-Only and Optional Reads** — Turning each tool on or off, counts-only collection, and switching on each optional read on Retention. *Reader:* admins and IT. *Optional parts:* every extra read is off until an admin turns it on.
11. **Set Up Project Approvals and Detection Rules** — Whether new projects need confirmation, onboarding approval on or off, later changes, and the deletion grace period. *Reader:* admins and approvers.
12. **Configure Notifications and Alerts** — Who is told what, email and the daily digest, a Slack channel with its Test button, thresholds and delivery history; personal notices arrive automatically. *Reader:* admins. *Optional parts:* email needs the server operator to set up mail; Slack is an admin switch.
13. **Get Fresher Claude Plan Figures with the Background Refresh** — Switching it on, choosing how often it runs, developer opt-out, and how long readings are kept. *Reader:* admins. *Optional parts:* admin switch; Claude Code only.
14. **Set Up AI Labelling Safely** — Provider key and monthly cap on Classification, approving each label list, Review Labels, the AI Call Log, and suggestion rules for the Blocker Board. *Reader:* admins. *Optional parts:* off until an admin sets it up; fact rules need no AI.
15. **Switch On the Organizational Brain and Add Your First Documents** — One-click switch, first SOPs and policies, project context, a department agent and the Chat budget. *Reader:* admins and department leads. *Optional parts:* Brain switch is admin-only; Chat needs an AI key from the server operator.
16. **Connect Your AI Assistant to Kite Pulse over MCP** — Chat mode or Direct access, issuing a key, testing it with “Try a question”, and connecting Claude Code, Cursor or VS Code. *Reader:* admins and developers. *Optional parts:* server operator turns keys on.
17. **Set Retention Windows and Handle Data Requests** — Retention per kind of data, the preview-only deletion schedule, and export or erase requests. *Reader:* admins and data-protection leads. *Optional parts:* real deletion is turned on by the server operator.
18. **Schedule Reports for Leadership** — Company or developer reports by email daily, weekly or monthly, preview, send history and download permission. *Reader:* admins and engineering managers.
19. **Keep the Desktop Program Up to Date Across Machines** — Publishing a version, watching Machines for update status and app logs, and acting on The Office's “Update” marker. *Reader:* admins and IT.

## Coverage check

**Every product area and every audience has at least one article from more than one angle.** References are category.article, so 2.9 is category 2, article 9.

| Product area | What it is (feature) | Benefit or problem | Story, workflow or guide |
| --- | --- | --- | --- |
| Capture across ten tools | 2.1–2.3, 10.1–10.6 | 4.8, 7.5 | 13.10 |
| Your own pages and sessions | 2.4–2.10 | 4.1–4.3, 4.6–4.9 | 3.3, 3.9, 3.14, 11.14, 13.6–13.7 |
| The Office, 3D view and live updates | 9.1–9.14 | 4.10, 5.1 | 3.1, 11.1 |
| Team and organisation views | 2.11–2.15 | 5.4, 5.6, 5.9, 6.1–6.2 | 3.12, 11.5 |
| Projects | 2.16–2.17 | 5.7, 7.10 | 3.5, 11.9, 11.16, 13.11 |
| AI usage, cost and budgets | 2.18–2.25 | 5.10, 5.13, 6.3–6.5, 7.3, 7.16 | 3.6, 11.3, 11.12, 13.8 |
| Claude plan limits | 2.26–2.27 | 4.4, 5.3, 7.4 | 3.2, 11.2, 13.13 |
| Work problems and stuck agents | 2.14, 9.9 | 4.5, 5.2, 5.5, 7.6–7.7 | 3.4, 11.4 |
| Reports | 2.28 | 5.12 | 3.11, 11.10, 13.18 |
| Notifications and alerts | 2.10, 2.30, 10.15–10.16 | 4.13, 6.13 | 11.11, 13.12 |
| AI labelling | 8.9–8.13, 8.22 | 6.14, 7.11 | 13.14 |
| Knowledge and stewardship | 8.14–8.20 | 5.11, 6.8–6.9, 7.8–7.9 | 3.7, 3.13, 11.6, 11.8, 11.13 |
| Organizational Brain | 8.1–8.8, 8.21 | 4.12, 7.15 | 3.8, 13.15 |
| Agent API, MCP and assistants | 10.7–10.12 | — | 3.15, 13.16 |
| Connectors and user sync | 10.13–10.14 | — | 12.1, 12.3 |
| Administration and security | 2.29–2.32, 10.17 | 6.10–6.12, 7.12 | 3.10, 11.15, 13.4, 13.9, 13.17, 13.19 |
| Privacy and trust | 1.7, 1.13, 9.14 | 4.11, 6.6–6.7, 7.13 | 12.2 |
| Deployment | 1.14 | 4.14, 6.11 | 13.1–13.3, 12.10 |

| Audience | Main articles |
| --- | --- |
| Individual developers | Category 4, 3.3, 3.9, 3.14, 11.14, 12.10, 13.1, 13.5–13.7 |
| Team leads and engineering managers | Category 5, 3.1–3.2, 3.12, 11.1–11.9 |
| Executives and finance | 1.5, 6.1–6.5, 3.6, 3.11, 11.3, 11.10, 11.12 |
| Admins, IT and security | 6.10–6.13, 11.11, 11.15–11.16, 12.11, categories 2 (administration) and 13 |
| HR, people teams and works councils | 1.7, 6.6–6.7, 6.9, 9.14 |
| Platform and DevEx teams | 5.13, 3.13, 11.13, 12.9 |
| Sector-specific readers | Category 12 |

**Not yet covered, on purpose:** the exact approval and waiting signals from Claude Code, plan figures from the status line, and plugin lists in Agent Setup. All three need the next desktop app release; add articles when it ships.
