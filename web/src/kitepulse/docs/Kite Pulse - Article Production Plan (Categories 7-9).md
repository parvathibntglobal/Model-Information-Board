# Kite Pulse - Article Production Plan, Categories 7-9

Draft for review, 4 November 2026. 26 articles (7.1 to 9.13): the category 7-9
articles marked "separate article" in `Kite Pulse - Article Keyword Map.xlsx`, minus
the ones already built (7.13, 8.19, 9.2, 9.9, 9.14). Built pages are matched on the
main keyword each one targets in the sheet's Page Map, not on its file name.

Each entry gives the SEO title (main keyword first, at most 60 characters with
" | Kite Pulse"), H1, URL, meta description (at most 155 characters), where each
secondary keyword goes, a short description of how the article is built, its 1-3
interactive elements, optional images or video (only where they add something a
widget cannot), FAQs, links and watch-outs. Entries carry a **Section** line where
the article belongs outside the Blog (here: 8.17 in Glossary); the rest are Blog
posts. Product facts follow the Master Source of Truth and the rules in
`MASTER-PROMPT.md`. Nothing here is written article copy.

Category 8 covers the Organizational Brain, which is hidden (MASTER-PROMPT R3): the
articles here are the ones the keyword map did not block, and none may promote the
Brain.

---

### 7.1 · Engineering Visibility Tool for AI Coding

- **Category · intent · page type:** Problems the Product Solves · Commercial · Blog post
- **Plan title:** The Work Moved into AI Conversations, and Your Visibility Did Not Follow
- **Title tag:** Engineering Visibility Tool for AI Coding | Kite Pulse
- **H1:** The Work Moved into AI Conversations: What an Engineering Visibility Tool Has to Read Now
- **URL:** /blog/engineering-visibility-tool
- **Meta description:** Commits and tickets show what came out, not how AI-assisted work went. What an engineering visibility tool has to read now, and what it should not collect.
- **Main keyword:** engineering visibility tool
- **Secondary keywords:**
  - ai assisted development analytics → H2 "What AI-assisted development analytics reads instead" (main keyword of 1.11: link /blog/ai-assisted-development-analytics)
  - software engineering intelligence → body of H2 "What git and ticket tools still answer well" (main keyword of 1.6: link /compare)
  - ai pair programming metrics → H3 "AI pair programming metrics that describe the work" (main keyword of 12.7, not yet planned: one short paragraph)
- **Description:** For engineering leaders meeting the problem for the first time. Most engineering visibility tools read commits, pull requests and tickets, which show what came out of the work; with AI assistants, much of the work now happens inside the conversation, where retries, dead ends, tool switches and stuck stretches never reach git. The page starts from that pain: two developers with the same commit count and very different days. It then covers why it happened now, what each data source can and cannot show (git, tickets, surveys, AI session history), what a session-level view adds, and an honest section on what git and ticket tools still answer better (delivery and DORA metrics, R9). It closes with what a visibility tool should not collect. One Kite Pulse callout at the session-level section: it reads the session history ten AI coding tools already keep, after each developer confirms their projects, on a server the team runs. The reader leaves with five questions to test any visibility tool against.
- **Interactive elements:**
  1. "What does each source see?" - one developer's sample day (labelled sample data) shown three ways: git log, ticket board, AI session record. The reader switches sources on and off and sees which events disappear: three failed attempts, a switch from Claude Code to Cursor, a long stuck stretch. Fallback is a table of the same events against the three sources.
  2. Question-to-source checklist - the reader ticks the questions they need answered (what is my team working on now, which AI tools are used, where retries pile up, how often we deploy) and gets a copyable list naming the data source that answers each, including the questions Kite Pulse does not answer. Fallback is the same mapping as a table.
- **Images / video (optional):** None - the source switcher shows the gap better than a diagram.
- **FAQ:**
  - Are commits and pull requests still good productivity metrics with AI?
  - How do companies track AI usage?
  - How do I know what my engineering team is working on right now?
- **Links to:** /engineering-intelligence, /ai-coding-analytics, /, /privacy, /blog/ai-assisted-development-analytics, /compare, /blog/measure-developer-productivity-ai (built)
- **Watch-outs:** "Visibility" must never slide into monitoring language (R4); the closing section states what it does not do in MSoT wording (no keystrokes, screenshots, websites or source files; session records can include code excerpts the AI read or wrote). Second FAQ is general (vendor dashboards, surveys, session analytics); where it mentions Kite Pulse: GitHub Copilot Chat in VS Code only (R5) and cost as a per-tool estimate (R7). Third FAQ: Team Overview shows who is online and coding now and each person's current project, managers for their own reporting line (MSoT 1.4). Do not claim a share of AI-written code. Overlaps /engineering-intelligence and 1.11: keep this page to the problem and link for the solution.

### 7.4 · Claude Code Hit Limit Mid Task: Why It Happens

- **Category · intent · page type:** Problems the Product Solves · Informational · Blog post
- **Plan title:** The Plan Limit That Ends Your Afternoon
- **Title tag:** Claude Code Hit Limit Mid Task: Why It Happens | Kite Pulse
- **H1:** When Claude Code Hits Its Limit Mid Task: Why the Afternoon Stops and How to See It Coming
- **URL:** /blog/claude-code-hit-limit-mid-task
- **Meta description:** When Claude Code hits its limit mid task, work stops until the window resets. How the 5-hour and weekly windows work, and how to see the limit coming.
- **Main keyword:** claude code hit limit mid task
- **Secondary keywords:**
  - monitor claude plan usage team → H2 "Monitor Claude plan usage across a team, not one laptop" (main keyword of 11.2: link /blog/sprint-planning-claude-plan-limits (built))
  - claude code limit tracker → H3 "What a Claude Code limit tracker needs to show"
  - claude code limit reset time → H2 "Claude Code limit reset time: when work can start again"
  - avoid hitting claude limit → body of the closing H2 "Habits that keep the afternoon" (main keyword of 4.4: link /blog/avoid-hitting-claude-limit (built))
- **Description:** For developers and leads on Claude plans. The pain comes first: the limit shows itself only when the task stops, often halfway through a multi-step change. The page explains the windows in plain words (the 5-hour window, the weekly window and per-model weekly windows, in Anthropic's terms with a source), why limits land mid task (long agent runs, sub-agents, large context), what to do when it happens (the reset time, finishing by hand, splitting the rest), and how to see it coming. One Kite Pulse callout at "see it coming": Plan headroom shows who is near a Claude plan limit (80% or more) or at it, worst first, and each developer sees their own plan usage on Workspace. Claude Code only. The reader leaves with a short check to run before starting a large task.
- **Interactive elements:**
  1. Window timeline - a sample 5-hour window and weekly window (labelled example usage, not Anthropic's real allowances); the reader slides "start a large task at..." and sees where the sample task would stop and when the window resets. Fallback paragraph explains the two windows in words.
  2. Before-you-start check - the reader enters their own current percentages for the 5-hour and weekly windows and picks a task size (small, medium, large, with example multipliers labelled as guesses) and gets "go", "split it" or "wait for the reset", with the reasoning. Fallback lists the three outcomes and when each applies.
- **Images / video (optional):** None - the timeline carries the explanation.
- **FAQ:**
  - How can I tell if a developer is about to hit their Claude usage limit?
  - How do I stop my team losing work time to Claude limits?
  - Will my Claude usage last the whole workday?
  - Claude Code: how close am I to the limit?
- **Links to:** /claude-code-usage-limits, /plan-headroom, /integrations/claude-code, /blog/avoid-hitting-claude-limit (built), /blog/sprint-planning-claude-plan-limits (built)
- **Watch-outs:** Claude Code only (R7): every Kite Pulse sentence says so; other tools show "Not reported by this tool". Plan figures are as fresh as Claude Code last saved them unless the background refresh is on (admin switch, app 0.4.2 or later, developer can turn it off), and old readings are flagged as stale: the third and fourth FAQ answers must say so. The "plan limit reached" notice with its reset time is Field Guide only: confirm before naming it; MSoT 1.6 verifies alerts and the in-app bell in general. Anthropic's window lengths and what counts toward them need a source URL and checked date in the data file; quote no allowance as a number without one (R2). Status-line plan figures are unreleased (MSoT 2.3): leave out. The sheet note says not to use /plan-headroom's own main keyword (sheet row 34) here; the page is the problem angle and links /plan-headroom and /claude-code-usage-limits for the rest.

### 7.6 · AI Agent Stuck in Loop While You Were Away

- **Category · intent · page type:** Problems the Product Solves · Informational · Blog post
- **Plan title:** The Agent That Sat Stuck While You Were in a Meeting
- **Title tag:** AI Agent Stuck in Loop While You Were Away | Kite Pulse
- **H1:** AI Agent Stuck in a Loop While You Were in a Meeting: Why Unattended Agents Spin, and How to Catch Them
- **URL:** /blog/ai-agent-stuck-in-loop
- **Meta description:** Why an AI agent gets stuck in a loop when nobody is watching, the signs it leaves in the session, and how to catch it early without reading the chat.
- **Main keyword:** ai agent stuck in loop
- **Secondary keywords:**
  - claude code agent stuck → H3 "When a Claude Code agent is stuck" (main keyword of 4.5: link /blog/claude-code-agent-stuck)
  - claude code stuck in loop → body of H2 "The signs a loop leaves behind" (main keyword of 3.14: link /blog/claude-code-stuck-in-loop)
  - monitor parallel ai agents → H2 "Keeping track of parallel AI agents without watching screens" (keyword used once in the body; link /ai-agent-office)
- **Description:** For developers and leads who leave agents running. Agents now run unattended, and a loop (the same failing command, the same edit made and undone) can run for a long time before anyone looks. The page covers why loops happen (a test that cannot pass in that environment, a missing permission or credential, an unclear goal), what they cost (time, tokens, Claude plan windows), the signs a loop leaves in the session record (repeated failed tool calls, the same command failing again, no new files), how to catch one (check-ins, timeboxes, notices), and the team angle (one person's loop can be a shared cause). One Kite Pulse callout at "catching it": The Office shows markers for stuck work for the people in your scope, and Work Problems groups repeated retries across the team. The reader leaves with a "signs of a loop" checklist.
- **Interactive elements:**
  1. Loop spotter - a sample session's 20-step list (labelled sample data); the reader marks where they think the loop started, then the page highlights the repeated command and its failed result and shows how long the loop ran in the sample. Fallback paragraph describes the three signs.
  2. Unattended-time slider - the reader sets how many agents run at once and how long a meeting lasts, and sees, on a labelled example, how many agent-minutes pass unseen and where a check-in would land. Fallback paragraph gives the arithmetic in words.
- **Images / video (optional):** None - the loop spotter shows the signs on a real-shaped record.
- **FAQ:**
  - How do I spot developers who are stuck in long AI sessions?
  - How do I know when AI is retrying the same failed fix repeatedly?
- **Links to:** /blog/ai-retry-loops, /ai-agent-office, /engineering-intelligence, /blog/claude-code-agent-stuck, /blog/claude-code-stuck-in-loop, /blog/stuck-ai-agent (built), /blog/is-claude-code-stuck (built), /blog/ai-agent-stuck-notification
- **Watch-outs:** The sheet links /parallel-ai-agents, which is hidden (site.js HIDDEN, folded into /ai-agent-office): link /ai-agent-office instead. The stuck notice, its recipients (the person and their manager), its 30-minute interval and "What the agent did" are Field Guide only: confirm before writing and leave the 30-minute figure out until confirmed (as in 2.10). Verified and usable: The Office markers for stuck work within scope; Agents in parallel on the developer page (admins for anyone, managers for themselves); Work Problems finds repeated retries (admin by default, can be granted) (MSoT 1.2, 1.4). Failed tool calls are recorded for every tool except Aider, and exit codes come only from Claude Code, Codex and Copilot (MSoT 1.1): the "signs" section must not imply exit codes for every tool. Claude Code waiting signals are unreleased (MSoT 2.3): leave out. R4: no monitoring framing. Overlaps /blog/ai-retry-loops (retry framing), 3.14 (story) and 4.5 (the developer's benefit): keep this one to the problem of unattended loops.

### 7.7 · Build Failure Analyzer: Failures CI Never Sees

- **Category · intent · page type:** Problems the Product Solves · Commercial · Blog post
- **Plan title:** The Same Failure, Fought Separately by Three People
- **Title tag:** Build Failure Analyzer: Failures CI Never Sees | Kite Pulse
- **H1:** Build Failure Analyzer for the Failures CI Never Sees: One Error, Three Developers, Three Separate Fixes
- **URL:** /blog/build-failure-analyzer
- **Meta description:** A build failure analyzer reads CI logs, but an error on three laptops never reaches CI. How to find failures fought separately and fix the shared cause.
- **Main keyword:** build failure analyzer
- **Secondary keywords:**
  - ci cd pipeline failures → H2 "What CI/CD pipeline failure tools catch, and what they miss"
  - jenkins build failures → body of the same H2 (the Jenkins Build Failure Analyzer plugin named as the CI-side tool)
  - failing commands analytics → H2 "Failing commands analytics across a team's AI sessions" (main keyword of 2.14: link /blog/failing-commands-analytics)
  - blocker board engineering → H3 "From repeated failures to a blocker board" (main keyword of 8.11: link to /blog/blocker-board-engineering)
  - repeated errors in ai coding sessions → body of H2 "Why the same failure is fought three times" (main keyword of 3.3: link /blog/repeated-errors-in-ai-coding-sessions)
- **Description:** For team leads and platform owners. Pages ranking for this keyword are CI-log tools (the Jenkins Build Failure Analyzer plugin, Gradle Develocity's failures dashboard, Moderne, BrowserStack); none groups failing local commands and agent retries across developers. The pain: a broken local setup or flaky build step hits several people on their own machines, often inside AI sessions, before anything reaches CI; each fights it alone, and it surfaces weeks later in a status meeting. The page covers what CI analyzers do well, the failures that happen before CI, why they get fought separately, how to find the shared cause (group by command and error, not by person), and how to turn it into one fix. One Kite Pulse callout at "find the shared cause": Work Problems uses fixed rules, no AI, to find failed commands, error messages and repeated retries, grouped by severity with suggested actions. The reader leaves with a short triage list for shared failures.
- **Interactive elements:**
  1. Failure grouper - three sample developers' failed-command lists (labelled sample data); the reader switches between "group by person" and "group by error" and sees one error spanning three people and two projects collapse into one row. Fallback paragraph plus a small table.
  2. CI or local? - the reader picks where a failure appeared (CI pipeline, local build, test run inside an AI session, agent retry) and sees which kind of tool can see it: a CI analyzer, a session-based view, both or neither. Fallback is the same mapping as a table.
- **Images / video (optional):** None - the grouper makes the point on sample data.
- **FAQ:**
  - How do I know when AI is retrying the same failed fix repeatedly?
- **Links to:** /engineering-intelligence, /features, /blog/ai-retry-loops, /blog/failing-commands-analytics, /blog/repeated-errors-in-ai-coding-sessions, /blog/blocker-board-engineering
- **Watch-outs:** WEAK FIT (sheet): searchers want a CI tool. Say early and plainly that Kite Pulse does not read CI logs or Jenkins, and that a CI analyzer is the right tool for pipeline failures (R9). Kite Pulse reads commands inside AI sessions on developers' computers; exit codes come from Claude Code, Codex and Copilot only, and failed tool calls from every tool except Aider (MSoT 1.1). Work Problems is admin by default and lists the most affected developers, so do not say it never names anyone; the Blocker Board shows recurring causes and never a single person (MSoT 1.4). That the Blocker Board needs AI labelling is Field Guide only: confirm. Competitor facts (Jenkins plugin, Gradle Develocity) need a source URL and checked date in the data file (R2). No claim about the GitHub connector: what connector data feeds was not checked (MSoT 1.6).

### 7.10 · Project Status Tracking Tool Without Guesswork

- **Category · intent · page type:** Problems the Product Solves · Commercial · Blog post
- **Plan title:** Project Status by Guesswork
- **Title tag:** Project Status Tracking Tool Without Guesswork | Kite Pulse
- **H1:** Project Status Tracking Tool Without Guesswork: Status from the Work, Not from Memory
- **URL:** /blog/project-status-tracking-tool
- **Meta description:** Most project status tracking tools depend on people updating them. How to see which projects are active, stable or dormant from the work itself.
- **Main keyword:** project status tracking tool
- **Secondary keywords:**
  - how to track project status in jira → H2 "How to track project status in Jira, and where it stops"
  - project status tracking template → H3 "A project status tracking template you can copy" (the copyable output)
  - project health status dashboard → H2 "A project health status dashboard built from activity"
  - project health status report → body of that H2 (the monthly report variant)
  - duplicate repository detection → body of H3 "One repository, two folders" (main keyword of 2.2: link /blog/duplicate-repository-detection)
  - engineering project tracking ai → body of H2 "What AI-assisted work adds to engineering project tracking"
- **Description:** For engineering managers. Pages ranking are listicles of status tools (ClickUp's list of status reporting tools, project-management.com, PPM Express; Jira, Asana, Monday, Smartsheet named), and all of them depend on people updating status. The pain: which projects are alive gets answered from memory, tickets go stale, and a project with no tickets but daily AI sessions looks dead. The page covers why status goes stale, what Jira answers well (R9), what activity evidence adds (sessions, contributors, last activity), the trap of one repository counted as two projects, and a template that combines both. One Kite Pulse callout at "what activity evidence adds": All Projects lists every project with its health (active, stable or dormant), sessions, contributors and last activity, and Duplicate Detection groups folders that look like the same repository. The reader leaves with a status template.
- **Interactive elements:**
  1. Stale or alive? - six sample projects (labelled sample data) with ticket status next to activity (sessions in the last 14 days, contributors, last activity); the reader guesses each project's real state, then reveals the activity view, where two disagree (an "In progress" project with no activity for a month, and a project with no tickets but daily sessions). Fallback is the same six rows as a table.
  2. Status template builder - the reader picks fields (owner, ticket status, last activity, contributors, open blockers, next decision) and a cadence, and gets a copyable template in plain text. Fallback shows the default template as text.
- **Images / video (optional):** None - the sample list does the comparing.
- **FAQ:**
  - How do I know what my engineering team is working on right now?
  - How do I find out which projects my team uses AI on the most?
- **Links to:** /features, /engineering-intelligence, /blog/duplicate-repository-detection, /blog/project-health-dashboard, /blog/project-status-tracking-dashboard, /blog/company-ai-usage-report (built)
- **Watch-outs:** The sheet links /reports, which is hidden (site.js HIDDEN, folded into /features): link /features and /blog/company-ai-usage-report (built). Shares a stem with 5.7 (/blog/project-status-tracking-dashboard, the manager's view) and 2.16 owns "project health dashboard" (/blog/project-health-dashboard): this page is the problem; cross-link both and do not repeat them. Phase, open blockers and duplicate work on the project summary card are listed in MSoT 1.4, but the Article Plan says they need AI labelling: write "where AI labelling is on" or leave them out. No Jira integration claim: Connectors can map Jira to projects, but what its data feeds was not checked (MSoT 1.6). Second FAQ: Team AI Usage shows token use per project, managers for their own line (MSoT 1.2).

### 7.11 · AI Agent Oversight: Changes Nobody Checked

- **Category · intent · page type:** Problems the Product Solves · Informational · Blog post
- **Plan title:** AI-Written Changes Nobody Checked
- **Title tag:** AI Agent Oversight: Changes Nobody Checked | Kite Pulse
- **H1:** AI Agent Oversight When AI-Written Changes Go Unchecked: Where Human Checks Slip and How to See It
- **URL:** /blog/ai-agent-oversight
- **Meta description:** AI agent oversight slips when changes the AI wrote go unchecked. Where human checks fall away, which signals show it, and what a team can agree on.
- **Main keyword:** ai agent oversight
- **Secondary keywords:**
  - human in the loop ai coding → H2 "Human in the loop in AI coding: where the loop breaks"
  - ai coding security risks → H2 "AI coding security risks in unchecked changes" (links /blog/secrets-in-ai-prompts and /security)
  - ai collaboration metrics → H3 "AI collaboration metrics, pooled by team" (main keyword of 8.12: link to /blog/ai-collaboration-metrics)
  - tracking ai generated code → body of H2 "What can be seen without reading the code"
- **Description:** For tech leads and security teams. The pain: agents make more changes than people read, the tests pass, so nobody looks, and security-relevant edits slip through. The page covers where human checks fall away (long agent runs, accepted edits, end-of-day merges), the security side (secrets pasted into prompts, sensitive files touched), which process signals show it (were tests run after an edit, were AI changes corrected, at team level rather than per person), what a team can agree on (check rules for kinds of change, not policing people), and an honest limit: Kite Pulse is not a code-quality scanner. One Kite Pulse callout at "process signals": each session's record shows which tools and commands ran, so whether a test followed an edit is visible, and opt-in AI labelling can tag work by type and outcome with admin-approved label lists. The reader leaves with a draft team check rule.
- **Interactive elements:**
  1. Check trace - a sample AI session (labelled sample data) as a list of edits, commands and test runs; the reader switches on "show edits never followed by a test or a human edit" and sees which changes in the sample went unchecked. Fallback paragraph explains the rule in words.
  2. Check-rule builder - the reader picks which changes need a person's look (touches sign-in, payments, infrastructure or migrations; more than a chosen number of files; no test run) and gets copyable rule text for their team. Fallback lists the options and an example rule.
- **Images / video (optional):** None - the trace shows the gap on sample data.
- **FAQ:**
  - Is AI usage affecting the quality of our code?
- **Links to:** /blog/agentic-coding, /engineering-intelligence, /blog/secrets-in-ai-prompts, /security, /blog/ai-secret-scanning (built), /blog/claude-code-session-analysis (built), /blog/ai-collaboration-metrics
- **Watch-outs:** Never frame as code review or a code-quality scanner ("ai code review tools" is on the avoid list; MSoT "What it is not"; R4). The verification signal, the Session Summary and Security watch named in the Article Plan are not in MSoT Section 1 (the verification signal and Security watch are Field Guide only and need AI labelling): leave them out unless confirmed. AI Collaboration's measures (corrections per 100 messages, AI changes checked and kept) are Field Guide only; MSoT 1.4 verifies only that the page exists, team-level and admin by default. The FAQ answer must say plainly that Kite Pulse does not measure code quality; review and code-quality tools answer that (R9). Do not claim a share of AI-written code for "tracking ai generated code". Leaked Credentials is MSoT Section 2 (partial): do not promote it here.

### 7.14 · Status Meetings Are a Waste of Time: What to Keep

- **Category · intent · page type:** Problems the Product Solves · Informational · Blog post
- **Plan title:** Status Meetings and Timesheets as the Only Source of Truth
- **Title tag:** Status Meetings Are a Waste of Time | Kite Pulse
- **H1:** When Status Meetings Are a Waste of Time: Replacing Round-the-Room Updates with the Work Itself
- **URL:** /blog/status-meetings-waste-of-time
- **Meta description:** Status meetings are a waste of time when people report what the work already shows. Async status updates, and what to keep the meeting for.
- **Main keyword:** status meetings are a waste of time
- **Secondary keywords:**
  - async status updates → H2 "Async status updates from what already happened"
  - status update meetings → body of H2 "What status update meetings cost"
  - alternatives to daily standup → H2 "Alternatives to the daily standup, and what to keep"
  - team status dashboard → H3 "A team status dashboard instead of the round" (main keyword of 5.1: link /blog/team-status-dashboard)
  - weekly engineering report → body of H2 "The weekly report nobody builds by hand" (main keyword of 3.11: link /blog/weekly-engineering-report)
  - team collaboration insights → body of H3 "Who is working with whom" (main keyword of 2.13: link /blog/team-collaboration-insights)
- **Description:** For team leads and developers tired of reporting rituals. Pages ranking are news and HR outlets recycling old survey stories (Clarizen and YouGov, 2011 and 2014) and forum threads, with no practical replacement. The pain: when the only way to know is to ask, people spend hours reporting what their tools already recorded, and timesheets get rebuilt from memory on Friday. The page covers what status meetings and timesheets are really used for (who is on what, what is blocked, what changed), what they cost, which of those questions the work itself can answer, async alternatives (written updates, a team dashboard, scheduled reports), and what a meeting is still good for (decisions, asking for help, the people side). One Kite Pulse callout at "what the work can answer": Team Overview shows who is online and coding now, today against a typical day, who needs attention and each person's current project, and scheduled reports email the company report daily, weekly or monthly. The reader leaves with a keep-or-replace plan for their own meeting.
- **Interactive elements:**
  1. Meeting cost calculator - the reader enters attendees, minutes, meetings per week and their own hourly figure (prefilled example values labelled as examples) and sees hours and cost per month. Fallback states the formula in words.
  2. Keep-or-replace sorter - the reader ticks what their status meeting covers (who works on what, blockers, plan-limit pressure, decisions, help requests, team mood) and gets a copyable plan: which items an async source can answer, and which, and which stay in a shorter meeting. Fallback is the same mapping as a table.
- **Images / video (optional):** None - the calculator and sorter carry the argument.
- **FAQ:**
  - How do I see what my team is working on without status meetings?
  - How do I know what my engineering team is working on right now?
  - How do I create a weekly AI usage report for my team?
  - Can an AI assistant write my weekly team update from engineering data?
- **Links to:** /features, /engineering-intelligence, /blog/ai-weekly-team-report, /blog/team-status-dashboard, /blog/weekly-engineering-report, /blog/team-collaboration-insights, /blog/async-standup-tool, /blog/scheduled-engineering-reports
- **Watch-outs:** The sheet links /reports, which is hidden (site.js HIDDEN, folded into /features): link /features and /blog/scheduled-engineering-reports (2.28). The old survey figures need a source URL, checked date and their year on the page; leave them out rather than quote them as current (R2). Team Overview lists "Most active today": do not say the dashboard never singles anyone out (R4, MSoT owner decision). Fourth FAQ: answer with scheduled reports first; an AI assistant reading Kite Pulse needs the Agent API or MCP, which is available only when enabled (MSoT 2.1), and Ask Kite Pulse / AI Chat is hidden (R3). Scheduled reports need email set up on the server (MSoT 2.1). Kite Pulse produces active time and sessions, not timesheets or billing: do not offer it as a timesheet. Overlaps 4.10 (/blog/async-standup-tool) and 5.1: this is the problem article; link them for the how.

### 8.9 · Classify Developer Work: AI Labelling, Done Carefully

- **Category · intent · page type:** Organizational Brain and AI-Powered Intelligence · Commercial · Blog post
- **Plan title:** AI Labelling, Done Carefully: Approved Label Lists, a Spending Cap and a Confidence Bar
- **Title tag:** Classify Developer Work with Approved AI Labels | Kite Pulse
- **H1:** Classify Developer Work by Type and Outcome, with Approved Labels, a Cap and "Unknown" Instead of Guesses
- **URL:** /blog/classify-developer-work
- **Meta description:** Classify developer work by type and outcome with AI labels an admin approves, a monthly spending cap, and "unknown" stored instead of a guess.
- **Main keyword:** classify developer work
- **Secondary keywords:**
  - bug fix vs feature work ratio → H2 "Bug fix vs feature work ratio: what work-type labels can show" (work types such as building, debugging, refactoring, testing)
  - engineering investment allocation → body of the same H2, one paragraph on how this differs from ticket-based investment allocation, with the honest "when another tool fits better" note (R9)
  - ai session success rate → H3 "Did the session succeed?" (main keyword of 5.8: link /blog/ai-session-success-rate)
- **Description:** For admins and technical leads asked to trust figures an AI produced. Ranking pages on classifying engineering work are git and ticket tools that sort work by issue type; none classifies the AI session itself or explains the safeguards around a model doing the labelling. The page covers what gets labelled (type of work, whether the session succeeded), the four conditions before anything runs (an OpenRouter key on Classification › Settings, a monthly budget above $0, the switch on, at least one approved and switched-on label list), why every list starts as an unapproved draft, how the monthly cap stops labelling until next month with an alert at 80%, and how answers below the confidence bar are stored as "unknown". A short section covers the free rule-based fact labels that need no key. One Kite Pulse callout at the confidence bar: Review Labels lists answers near the bar, unknown answers and a sample to check. The reader leaves knowing what they would have to approve before a single label exists.
- **Interactive elements:**
  1. Confidence bar slider - ten sample sessions (labelled sample data), each with a sample label and confidence; the reader moves the bar and sees which become "unknown" and which go to the Review Labels sample. Fallback paragraph explains the bar and the three review groups.
  2. "Ready to label?" checklist - the reader ticks the four conditions (key, budget, switch, approved list) and sees exactly which one still blocks labelling. Fallback is the same four conditions as a list.
  3. Sample work-type mix - a bar of one sample month split by work type (labelled sample data), with the reader toggling "debugging" against "building" to see a bug-fix vs feature split. Fallback sentence says the split comes from approved work-type labels, not from tickets.
- **Images / video (optional):** None - the slider and checklist explain the safeguards better than a screenshot of the settings page.
- **FAQ:**
  - How much of our engineering time goes to bug fixing vs new features?
  - Do I need an AI API key to use Kite Pulse?
- **Links to:** /engineering-intelligence, /features, /faq, /privacy, /blog/ai-session-success-rate (5.8), /docs/how-figures-are-calculated (1.9)
- **Watch-outs:** All labelling facts are MSoT 1.5 and may be stated: OpenRouter key, monthly budget, unapproved drafts, cap with 80% alert, "unknown" below the bar, Review Labels, new sessions labelled automatically and older history at a pace the admin sets, fact rules free. Where the work-type mix is SHOWN (Team Review's "mix of work", Trends) is Field Guide only: confirm the page before naming it. First FAQ: answer with what labels can show, say the figure is time in AI sessions by work type, not engineering time overall, and that ticket-based tools (Jira, git analytics) answer it from issues (R9). Second FAQ: no - collection, counts, reports, fact rules, Session Graph and Skill Candidates need no key (MSoT 1.5); only AI labelling does. Privacy: with labelling on, scrubbed text goes to the provider through OpenRouter, default zero data retention (MSoT 1.7): say it. "Investment allocation" is a git/Jira vendor term: no competitor names without a source and checked date (R2). Never call the result a productivity score.

### 8.11 · Blocker Board Engineering: From Facts to Advice

- **Category · intent · page type:** Organizational Brain and AI-Powered Intelligence · Commercial · Blog post
- **Plan title:** From Facts to Advice: Fact Rules, Suggestion Rules and the Blocker Board
- **Title tag:** Blocker Board for Engineering Teams | Kite Pulse
- **H1:** A Blocker Board for Engineering: How Kite Pulse Turns Facts About Work into Causes and Actions
- **URL:** /blog/blocker-board-engineering
- **Meta description:** A blocker board for engineering lists recurring causes of lost time with a suggested action each, never a person. See how facts become advice.
- **Main keyword:** blocker board engineering
- **Secondary keywords:**
  - recurring engineering blockers → H2 "From one failure to a recurring engineering blocker" (main keyword of 5.5: link /blog/recurring-engineering-blockers)
  - failing commands analytics → H2 "Layer one: facts with no AI" (Work Problems and fact rules; main keyword of 2.14: link /blog/failing-commands-analytics)
  - repeated errors in ai coding sessions → body of the layer-one section (main keyword of 3.3: link /blog/repeated-errors-in-ai-coding-sessions)
- **Description:** For team leads and platform owners who have a list of failures and want a short list of causes. Pages ranking for "blocker board" are Kanban how-tos where people add blocked cards by hand; none builds the board from the work itself. The page walks up three layers: facts (fixed rules, no AI, find failed commands, error messages and retries; fact rules label tool failures, files changed and TODOs at no cost), then labels (AI labelling, if switched on, adds what kind of work it was and whether it worked), then advice (the Blocker Board groups recurring causes with a suggested action). Each layer says what it needs and who sees it by default. One Kite Pulse callout at the board: it shows causes and actions for the organisation, a team or a project, and never a single person. The reader leaves with a way to decide which layer their team needs first.
- **Interactive elements:**
  1. Three-layer stack - a sample week of failures (labelled sample data) shown first as raw facts, then labelled, then as three board cards; the reader steps through layers and switches "AI labelling off" to see the stack stop at layer one. Fallback paragraph describes each layer and what it needs.
  2. Card anatomy - one sample board card the reader clicks through: cause, how often, suggested action; a toggle "show who" explains that the board never names a person and that Work Problems is where affected developers appear (admin by default). Fallback is a short labelled list.
- **Images / video (optional):** None - the stack carries the idea.
- **FAQ:**
  - How do I know when AI is retrying the same failed fix repeatedly?
- **Links to:** /engineering-intelligence, /features, /blog/ai-retry-loops (built), /blog/failing-commands-analytics (2.14), /blog/recurring-engineering-blockers (5.5), /blog/repeated-errors-in-ai-coding-sessions (3.3)
- **Watch-outs:** Verified (MSoT 1.2, 1.4, 1.5): Work Problems (fixed rules, no AI, failed commands, errors, retries, suggested actions, most affected developers, admin by default); fact rules on by default, free, nothing sent; Blocker Board admin by default, grantable to managers, recurring causes and suggested actions, never a single person. Field Guide only: the board needs AI labelling, its 28-day window, session links for admins only, fact rules running every 6 hours: confirm before stating. "Suggestion rules" (approved rules that fill the board) appear only in the Article Plan, not in MSoT or the Field Guide: do not name them until confirmed; describe the board's input as "AI labels". Work Problems lists the most affected developers, so "never names a person" applies to the Blocker Board only. FAQ answer: Work Problems finds repeated retries without AI; link /blog/ai-retry-loops. Failed tool calls are not recorded for Aider; exit codes only from Claude Code, Codex and Copilot (MSoT 1.1).

### 8.12 · AI Collaboration Metrics: What Labels Tell a Team

- **Category · intent · page type:** Organizational Brain and AI-Powered Intelligence · Commercial · Blog post
- **Plan title:** What Labels Tell a Team: Trends, Team Review and AI Collaboration
- **Title tag:** AI Collaboration Metrics for Engineering Teams | Kite Pulse
- **H1:** AI Collaboration Metrics: What Work Labels Tell a Team Over Weeks and Months
- **URL:** /blog/ai-collaboration-metrics
- **Meta description:** AI collaboration metrics for engineering teams: completion, friction and checked AI changes, pooled per team over weeks and months, never per person.
- **Main keyword:** ai collaboration metrics
- **Secondary keywords:**
  - ai session success rate → H2 "Completion and success: the AI session success rate" (main keyword of 5.8: link /blog/ai-session-success-rate)
  - engineering team kpis → H2 "Which engineering team KPIs these can and cannot be"
  - ai code acceptance rate → H3 "Why this is not an AI code acceptance rate" (link /compare/github-copilot-metrics)
- **Description:** For engineering managers who want to know whether the team's work with AI is getting better, without a per-person league table. Ranking pages on AI collaboration metrics are vendor dashboards built on acceptance rates and survey sentiment; none reads team-level measures from the sessions themselves. The page covers three views that sit on AI labels: Trends (how measures move over weeks and months), Team Review (one team, one week, middle values and the mix of work) and AI Collaboration (month by month per team: corrections of the AI, context given again, AI changes checked, AI file changes kept). It explains why the figures are pooled and why a figure with too few people behind it is left out. One Kite Pulse callout at the pooling section. The reader leaves knowing which questions these measures answer and which belong to delivery metrics instead.
- **Interactive elements:**
  1. Pooling demo - a sample team of six (labelled sample data) with per-session outcomes hidden; the reader shrinks the team and watches a figure disappear with the reason "too few people" once the group is too small. Fallback paragraph explains pooling and holding back small groups.
  2. Measure picker - the reader chooses a question ("are we finishing more?", "are we correcting the AI less?", "are we checking AI changes?") and sees which view and measure answers it, plus one question none of them answers (delivery speed, which belongs to git/Jira tools). Fallback is the same mapping as a table.
- **Images / video (optional):** One chart from a real deployment only, labelled with its date (MSoT 2.5); otherwise none.
- **FAQ:**
  - Can I compare AI usage between teams?
  - Which teams are getting the most value from AI coding tools?
- **Links to:** /engineering-intelligence, /features, /blog/ai-session-success-rate (5.8), /blog/engineering-team-health-metrics (built), /blog/how-often-developers-correct-ai (4.7), /compare/github-copilot-metrics
- **Watch-outs:** MSoT 1.4 verifies only that Trends, Team Review and AI Collaboration exist (Team Review and AI Collaboration admin by default, team-level views). Every measure named above, the per-100-messages basis, pooling over a group's month and leaving out figures with too few people are Field Guide only; "win rate" is Article Plan only: confirm each before writing. All need AI labelling (Field Guide), which an admin sets up (MSoT 1.5). Teams feed Team Review and AI Collaboration (MSoT website corrections). Second FAQ: no "most value" ranking or ROI figure (R4, MSoT 2.5); answer with what can be compared (pooled measures per team) and what cannot. Kite Pulse collects no inline completions (R5), so it has no acceptance rate: say so. "AI file changes kept" is the closest measure to acceptance; do not rename it.

### 8.13 · Verify AI Generated Code: What Labels Tell One Person

- **Category · intent · page type:** Organizational Brain and AI-Powered Intelligence · Informational · Blog post
- **Plan title:** What Labels Tell One Person: My Day, the Verification Signal and Profile Facts
- **Title tag:** Verify AI Generated Code: Track Your Own Habit | Kite Pulse
- **H1:** Verify AI-Generated Code as a Habit: What Labels Tell You About Your Own Work
- **URL:** /blog/verify-ai-generated-code
- **Meta description:** Do you verify AI generated code as often as you think? How a private signal, a daily summary and profile facts read your own work from your sessions.
- **Main keyword:** verify ai generated code
- **Secondary keywords:**
  - how to check ai output → H2 "How to check AI output: four habits" (testing, reviewing the diff, correcting, asking the AI to explain)
  - ai code acceptance rate → body of the verification section, one sentence on why accepting is not checking (link /blog/how-often-developers-correct-ai)
  - daily work summary, work summary ai → H2 "A daily work summary written from your sessions"
  - claude code daily summary → body of that H2 (main keyword of 4.9: link /blog/claude-code-daily-summary)
  - my ai coding stats → H2 "Your AI coding stats beside the labels" (main keyword of 4.8: link /blog/my-ai-coding-stats)
  - personal claude code usage stats → body of the same H2, linking Workspace (main keyword of 2.4: link /blog/personal-claude-code-usage-stats)
- **Description:** For developers who lean on AI edits and want an honest read on their own habits. Ranking pages are verification tools and vendor blogs about testing the code itself; none measures how often a person checks. The page opens with four ways to check AI output, then shows what AI labels add for one person: a signal of how often you reviewed or tested the AI's work, a daily summary of what you worked on, started, finished and left open, and skills and areas on your developer page. Each says who sees it. One Kite Pulse callout at the verification section, stating that all three need AI labelling, which an admin sets up. The reader leaves with one check to add to their routine. This page is the hub for the three features; 4.7 and 4.9 go deeper on one each.
- **Interactive elements:**
  1. Habit check - the reader answers five quick questions about their last AI session (did you run tests, read the diff, correct the AI...) and gets a plain summary of which habits they used, computed in the browser and not stored. Fallback lists the four habits.
  2. Sample day - one sample day (labelled sample data) shown first as raw sessions, then as a daily summary grouped into worked on, finished, left open, stuck. Fallback paragraph describes the grouping.
- **Images / video (optional):** None.
- **FAQ:**
  - (No FAQ in the brief. Suggested: "How can I check AI-generated code quickly?" and "Who can see my daily summary?" - confirm with the keyword owner before adding.)
- **Links to:** /engineering-intelligence, /features, /privacy, /blog/how-often-developers-correct-ai (4.7), /blog/claude-code-daily-summary (4.9), /blog/my-ai-coding-stats (4.8), /blog/personal-claude-code-usage-stats (2.4)
- **Watch-outs:** WEAK FIT (sheet note): the searcher wants to verify code; the page must answer that first (habits section) and must not present Kite Pulse as a code reviewer or code-quality scanner (R4, avoid list). My Day, the verification signal and profile facts (skills and areas) are not in MSoT Section 1: My Day and the signal are Field Guide only, profile facts are Article Plan only; all need AI labelling. Confirm each before writing. Who sees the signal is open: the Field Guide lists it in the developer report export, so do not write "only you see it" (same note as 4.7). Overlaps 4.7 and 4.9 heavily: keep this page to the overview and the checking habits, and link out for depth. Kite Pulse has no acceptance rate (R5: no inline completions).

### 8.14 · Lessons Learned in Software Development, Kept

- **Category · intent · page type:** Organizational Brain and AI-Powered Intelligence · Informational · Blog post
- **Plan title:** Knowledge Records: Lessons Quoted from Real Sessions, Linked to Where They Came From
- **Title tag:** Lessons Learned in Software Development, Kept | Kite Pulse
- **H1:** Lessons Learned in Software Development That Stay Findable: Records Quoted from Real Sessions
- **URL:** /blog/lessons-learned-software-development
- **Meta description:** Lessons learned in software development fade when they live in one chat. Keep them as records quoted from real sessions, linked to their commits.
- **Main keyword:** lessons learned software development
- **Secondary keywords:**
  - lessons learned in software development project → H2 "Lessons learned in a software development project: why the retro document goes stale" (main keyword of 11.6, not yet planned: link once planned)
  - search past ai coding sessions → H3 "When the lesson is still only in a session" (main keyword of 2.7: link /blog/search-past-ai-coding-sessions)
  - capture knowledge from ai coding sessions → H2 "Capturing knowledge from AI coding sessions as it happens" (main keyword of 6.8: link /blog/capture-knowledge-from-ai-coding-sessions)
- **Description:** For engineering managers and knowledge owners whose lessons live in retro documents nobody reopens. Ranking pages are lessons-learned templates and retrospective guides; none takes a lesson from the place it was actually learned. The page explains why written-up lessons drift from the work, then shows a different source: passages worth keeping, quoted from real messages in AI sessions and linked to the sessions and commits they came from. It covers how records appear (once the knowledge label list is approved and has run), why they start as "proposed", and who reviews them. One Kite Pulse callout at the record anatomy. The reader leaves with a short test for whether a lesson is worth keeping, and where to keep it.
- **Interactive elements:**
  1. Record anatomy - one sample knowledge record (labelled sample data) with clickable parts: the quoted passage, its project, the linked session and commit, and its status "proposed". Fallback is the same parts as a labelled list.
  2. Keep or skip - six sample passages from a session; the reader decides which are worth keeping and sees a short reason for each (a decision, a fix that will recur, a gotcha, versus chatter). Fallback lists the four kinds worth keeping.
- **Images / video (optional):** None.
- **FAQ:**
  - How can I capture knowledge from AI coding sessions?
  - How do I stop my team solving the same bug twice?
- **Links to:** /blog/institutional-knowledge (built), /features, /blog/capture-knowledge-from-ai-coding-sessions (6.8), /blog/search-past-ai-coding-sessions (2.7), /blog/engineering-knowledge-management (8.15)
- **Watch-outs:** Knowledge Records are MSoT 1.5: quoted from real messages, linked to sessions and commits, appear once the knowledge label list is approved and has run, start as "proposed". They need AI labelling, which an admin sets up. Admin-only by default is Article Plan / Field Guide (admin path): confirm before stating. Always "knowledge records", never "Knowledge Base" (sheet note; Knowledge Base is a switched-off page, R3). Filing under the capability map, the Coherence tab and audited reads are Field Guide only. Overlaps /blog/institutional-knowledge (built), 6.8 and 11.6: keep this page to the record itself; 6.8 owns the capture process. Second FAQ: say records make a past fix findable; they do not stop anyone repeating work.

### 8.15 · Engineering Knowledge Management That Stays Current

- **Category · intent · page type:** Organizational Brain and AI-Powered Intelligence · Commercial · Blog post
- **Plan title:** Keeping Knowledge Current: the Weekly Knowledge Log and Coherence Checks
- **Title tag:** Engineering Knowledge Management, Kept Current | Kite Pulse
- **H1:** Engineering Knowledge Management That Stays Current: New Records Each Week, Old Ones Checked
- **URL:** /blog/engineering-knowledge-management
- **Meta description:** Engineering knowledge management fails when records go stale. Review new records weekly, find similar sessions, and flag duplicates and conflicts.
- **Main keyword:** engineering knowledge management
- **Secondary keywords:**
  - lessons learned software development → body of H2 "Where new knowledge comes from" (main keyword of 8.14: link /blog/lessons-learned-software-development)
  - find similar ai coding sessions → H2 "Find similar AI coding sessions with the Session Graph"
  - capture knowledge from ai coding sessions → body of the first H2 (main keyword of 6.8: link /blog/capture-knowledge-from-ai-coding-sessions)
- **Description:** For knowledge owners and tech leads whose wiki is full of pages nobody trusts. Ranking pages are knowledge-base vendors selling a place to write things down; none deals with keeping recorded knowledge current. The page sets out the maintenance loop: new records arrive from sessions, someone reviews them on a weekly rhythm, similar sessions are grouped so repeats are visible, and records that duplicate, contradict or have gone out of date are flagged for a decision. The Session Graph section stands on its own because it needs no AI: it links sessions that look alike, rebuilt once a day. One Kite Pulse callout at the flags section. The reader leaves with a 20-minute weekly review routine they can copy.
- **Interactive elements:**
  1. Weekly review routine builder - the reader picks team size and how many records arrive a week (labelled example inputs) and gets a copyable routine: what to review, what to merge, what to retire. Fallback is the routine as a plain list.
  2. Flag sorter - six sample record pairs (labelled sample data); the reader sorts each into duplicate, conflict or out of date and sees the suggested decision for each. Fallback paragraph defines the three flags.
- **Images / video (optional):** None.
- **FAQ:**
  - How can I capture knowledge from AI coding sessions?
- **Links to:** /features, /blog/institutional-knowledge (built), /blog/lessons-learned-software-development (8.14), /blog/capture-knowledge-from-ai-coding-sessions (6.8), /blog/capability-mapping-software (8.16)
- **Watch-outs:** Verified (MSoT 1.5): Knowledge Records (need AI labelling) and Session Graph (links sessions that look alike, rebuilt once a day, on by default, no AI). The duplicate / conflict / out-of-date flags are the Field Guide's "Coherence tab": confirm before naming it. The "Weekly Knowledge Log" and "captured this week" card are in neither MSoT nor the Field Guide: do not name them until confirmed; the weekly routine on this page is the reader's own process, not a console page. Never "Knowledge Base" (R3). Session Graph groups sessions, it does not merge records: keep the two apart. The Brain is hidden (R3): leave it out.

### 8.16 · Capability Mapping Software for Engineering Teams

- **Category · intent · page type:** Organizational Brain and AI-Powered Intelligence · Commercial · Blog post
- **Plan title:** The Capability Map: Describing Each Product in Plain Terms
- **Title tag:** Capability Mapping Software for Engineering | Kite Pulse
- **H1:** Capability Mapping Software for Engineering: Describe Each Product in Modules, Capabilities and Scenarios
- **URL:** /blog/capability-mapping-software
- **Meta description:** Capability mapping software for engineering teams: describe each product as modules, capabilities and scenarios, built by a person, with no AI model.
- **Main keyword:** capability mapping software
- **Secondary keywords:**
  - capability mapping tools → H2 "Two kinds of capability mapping tools" (business capability maps versus product maps; main keyword of 12.8, not yet planned: link once planned)
  - engineering knowledge management → body of H2 "What the map is for" (main keyword of 8.15: link /blog/engineering-knowledge-management)
- **Description:** For product owners, architects and engineering managers who need one plain description of what a product is made of. Ranking pages are enterprise-architecture tools mapping business capabilities to org units; none maps a software product from the work done on it. The page first separates the two meanings honestly (R9: for business capability maps, enterprise-architecture tools fit better), then shows the product version: modules, capabilities and scenarios, in the names people use, built and approved by a person, with an optional rule-based suggester a server operator can run to propose entries from folders, routes, branches and ticket ids. One Kite Pulse callout at the suggester: no AI model is involved anywhere. The reader leaves with a first draft of their own product's top level.
- **Interactive elements:**
  1. Map builder - the reader types a product name and three modules, adds capabilities and scenarios under each, and copies the result as an indented outline. Built in the browser, nothing stored. Fallback is an example outline for a sample product (labelled).
  2. Suggester preview - a sample repository's folders, routes and branch names (labelled sample data); the reader clicks "suggest" to see which proposed entries come from which source, each waiting for approval. Fallback paragraph explains the four sources.
- **Images / video (optional):** None.
- **FAQ:**
  - (No FAQ in the brief. Suggested: "What is the difference between a business capability map and a product capability map?" and "Does building a capability map need AI?" - confirm with the keyword owner before adding.)
- **Links to:** /features, /blog/institutional-knowledge (built), /blog/engineering-knowledge-management (8.15), /glossary/bus-factor (8.17)
- **Watch-outs:** Keyword relevance is 1 (sheet note) and the search intent is mostly business capability mapping: answer that meaning first and say where enterprise-architecture tools fit better (R9); name no vendor without a source and checked date (R2). Verified (MSoT 1.5): modules, capabilities and scenarios; a person builds and approves; operator-run rule-based suggester (folders, routes, branches, ticket ids); no AI model. Field Guide only: elements, placement rules, history, add/rename/move/merge/split/retire actions, and the Ownership tab: confirm before stating; leave ownership to 8.17. Branch names come from an optional read an admin turns on (MSoT 1.1): say so if the suggester section mentions branches.

### 8.17 · What Is the Bus Factor in Software Development?

- **Category · intent · page type:** Organizational Brain and AI-Powered Intelligence · Informational · Glossary
- **Section:** Glossary
- **Plan title:** Who Really Knows This Part? Capability Ownership and the Bus Factor
- **Title tag:** Bus Factor in Software Development: Definition | Kite Pulse
- **H1:** What Is the Bus Factor in Software Development?
- **URL:** /glossary/bus-factor
- **Meta description:** The bus factor in software development is how few people would have to leave before a part of the product has nobody who knows it. Example and fixes.
- **Main keyword:** bus factor in software development
- **Secondary keywords:**
  - knowledge silos → H2 "Why it matters: knowledge silos you cannot see"
  - code ownership model → H2 "An example: one code ownership model, two bus factors"
  - capability mapping software, capability mapping tools → body of H2 "What to do instead" (one sentence: measure it per capability, not per repository; main keywords of 8.16 and 12.8: link /blog/capability-mapping-software)
  - capture knowledge from ai coding sessions → body of "What to do instead" (main keyword of 6.8: link /blog/capture-knowledge-from-ai-coding-sessions)
- **Description:** For engineering managers and tech leads meeting the term, and for searchers who want a definition. Ranking pages are Wikipedia, a research paper and older posts: they define the term and stop. Glossary structure: a bold one-sentence definition, then why it matters (knowledge silos that show only when someone leaves), an example (one small service where two people edit everything but only one reads the payments module, so the module's bus factor is one), and what to do instead (measure per part of the product, pair on the risky parts, write knowledge down while the person is still there). It absorbs 7.9's problem angle ("when the only person who knows moves on") as the opening of the why section. The Kite Pulse mention is one sentence in "what to do instead", pointing to the calculator and the Capability Map. Related terms: knowledge silo, code ownership, capability map, hand-over.
- **Interactive elements:**
  1. Remove-a-person toy - a small sample team and four parts of a product (labelled sample data); the reader removes one person and sees which parts are left with nobody who has edited or read them. Fallback is the same example as a short table. For a fuller version, link /bus-factor-calculator (5.11).
- **Images / video (optional):** None.
- **FAQ:**
  - (No FAQ in the brief. Suggested: "What is a good bus factor?", "How do you calculate the bus factor?" and "Is the bus factor the same as the truck factor?" - confirm with the keyword owner before adding.)
- **Links to:** /bus-factor-calculator (5.11), /features, /blog/institutional-knowledge (built), /blog/capability-mapping-software (8.16), /blog/knowledge-transfer-before-leaving (3.7), /blog/offboarding-knowledge-transfer (8.18), /glossary (1.8)
- **Watch-outs:** Capability ownership, per-capability bus factor, shares of edits, hand-over hints and owner accept/decline are NOT in MSoT Section 1; the Field Guide has only an "Ownership tab" on the Capability Map. The plan and the sheet's content gap rely on them: confirm before saying Kite Pulse computes a bus factor; until then the product sentence names only the Capability Map (MSoT 1.5) and the calculator. Absorbs 7.9 (keyword map "Absorbs"). A glossary page stays short (MASTER-PROMPT Glossary type): one widget at most. Outside definitions and any study (the ICSE "Bus Factor in Practice" paper) need a source and checked date in the data file (R2). R4: never frame it as rating people.

### 8.18 · Offboarding Knowledge Transfer for Developers

- **Category · intent · page type:** Organizational Brain and AI-Powered Intelligence · Informational · Blog post
- **Plan title:** When Someone Moves On: Tenure, the Departure Report and Knowledge-Capture Requests
- **Title tag:** Offboarding Knowledge Transfer for Developers | Kite Pulse
- **H1:** Offboarding Knowledge Transfer for Developers: What to Capture Before Someone Moves On
- **URL:** /blog/offboarding-knowledge-transfer
- **Meta description:** Offboarding knowledge transfer for developers: find what only they know from their work, ask them to write it down, and keep a copyable template.
- **Main keyword:** offboarding knowledge transfer
- **Secondary keywords:**
  - knowledge transfer leaving employee → H2 "Knowledge transfer from a leaving employee: the first week"
  - offboarding knowledge transfer template → H2 "An offboarding knowledge transfer template you can copy" (the template builder below)
  - knowledge capture methods → H2 "Four knowledge capture methods, and when each fits" (write-up, pairing, recorded walkthrough, records quoted from past work)
  - capture knowledge from ai coding sessions → body of the fourth method (main keyword of 6.8: link /blog/capture-knowledge-from-ai-coding-sessions)
  - lessons learned software development, lessons learned in software development project → one paragraph on what the leaver's lessons look like in a record (main keywords of 8.14 and 11.6: link /blog/lessons-learned-software-development)
- **Description:** For managers and admins planning a hand-over. Ranking pages are HR offboarding checklists from universities and vendors; none is specific to engineering or starts from the work the person actually did. The page runs in time order: what to find out (which parts of the product only they edit, which projects they lead, what lives only in their sessions or notes), how to ask them to write it down, which capture method fits each item, and how to check the hand-over held a month later. It absorbs 6.9's outcome angle ("their know-how does not leave with them"). One Kite Pulse callout at "what to find out", limited to verified pages. The reader leaves with a copied template filled in for one person.
- **Interactive elements:**
  1. Template builder - the reader enters the leaver's role, projects and notice period (example inputs, nothing stored) and gets a copyable hand-over template with dated steps and one owner per item. Fallback is the template as plain text.
  2. Method chooser - the reader picks an item to hand over (a deploy routine, a design decision, a client contact) and sees which capture method fits and why. Fallback is the same mapping as a table.
- **Images / video (optional):** None.
- **FAQ:**
  - (No FAQ in the brief. Suggested: "What should a developer hand over before leaving?" and "How long does knowledge transfer take?" - confirm with the keyword owner; the second must not quote a duration without a source.)
- **Links to:** /blog/institutional-knowledge (built), /features, /blog/knowledge-transfer-before-leaving (3.7), /glossary/bus-factor (8.17), /blog/lessons-learned-software-development (8.14), /blog/capture-knowledge-from-ai-coding-sessions (6.8)
- **Watch-outs:** The plan's three features - tenure, the Departure Report and knowledge-capture requests - are in NEITHER MSoT nor the Field Guide: do not name them until confirmed. Build the Kite Pulse callout on verified pages only: the developer page and its sessions (MSoT 1.4), All Projects and Collaboration for which projects the person is in, Knowledge Records (need AI labelling), the Capability Map, and the optional project-notes read for CLAUDE.md, AGENTS.md and READMEs (admin turns it on, MSoT 1.1). Do not mix offboarding with erasing a person's data; if erase comes up, use the exact R6 wording (anonymises the account, deletes raw activity records, destroys keys; not all data). Absorbs 6.9. Overlaps 3.7 (the story): keep this page to the how-to and template. R4: no surveillance framing of the leaver.

### 8.22 · LLM Cost Control: Keeping Kite Pulse's Own AI Spend in Check

- **Category · intent · page type:** Organizational Brain and AI-Powered Intelligence · Commercial · Blog post
- **Plan title:** Keeping Kite Pulse's Own AI Spend in Check
- **Title tag:** LLM Cost Control for an Analytics Tool's Own AI | Kite Pulse
- **H1:** LLM Cost Control: How Kite Pulse Caps Its Own AI Spend, and Where Your Provider's Limits Fit
- **URL:** /blog/llm-cost-control
- **Meta description:** LLM cost control for Kite Pulse's own AI labelling: a monthly cap, an 80% alert, a log of every call, and where provider spending limits fit.
- **Main keyword:** llm cost control
- **Secondary keywords:**
  - openrouter spending limit → H2 "The provider side: an OpenRouter spending limit on the key you enter"
  - claude api spending limit, openai api spending limit → H3 "Claude API and OpenAI API spending limits" (one short paragraph each, from the vendors' own documentation)
  - llm budget tracker → H2 "Tracking what labelling spent: the AI Call Log"
  - spend caps for ai coding agents → H2 "A different budget: spend caps for the AI coding agents themselves" (one section pointing to AI Budgets)
- **Description:** For admins and finance owners who will only switch on AI labelling if its cost has a ceiling. Ranking pages are API-gateway vendors on budgets for LLM features in products; none covers capping a tool's own labelling spend. The page separates two bills: Kite Pulse's own AI labelling (a monthly budget on Classification, labelling stops at it until the next month, alert at 80%, every call in the AI Call Log) and the AI coding tools the team uses (AI Budgets: monthly per team or project, tokens or estimated dollars, alerts at 80% and 100%). A provider-side section explains setting a limit on the key itself as a second ceiling. One Kite Pulse callout at the cap: labelling is off until an admin sets a budget above $0. The reader leaves with a two-line rule: cap in Kite Pulse, limit on the key.
- **Interactive elements:**
  1. Cap simulator - a sample month of labelling calls (labelled sample data, example per-call cost) with a budget field; the reader sets the cap and sees the 80% alert day and the day labelling stops. Fallback paragraph explains the cap and the alert.
  2. Which budget? - the reader picks a cost ("labelling our sessions", "a team's Claude Code tokens", "a developer's Cursor seat") and sees which control covers it: the Classification cap, AI Budgets, seat prices, or none (with why). Fallback is the same mapping as a table.
- **Images / video (optional):** None.
- **FAQ:**
  - Do I need an AI API key to use Kite Pulse?
- **Links to:** /ai-budgets, /pricing, /faq, /ai-spending-limits (6.14), /privacy, /docs/how-figures-are-calculated (1.9), /blog/classify-developer-work (8.9)
- **Watch-outs:** Verified (MSoT 1.5): OpenRouter key on Classification › Settings, monthly budget above $0, labelling stops at the budget until next month, alert at 80%, AI Call Log of every labelling call with what was sent and received. Per-call tokens and cost in the log are Field Guide only: confirm before stating. AI Budgets facts are MSoT 1.2 and alert only: never say they stop the tools. The plan's Brain Chat budget is dropped (sheet note; Brain hidden, R3). The separate key for agent questions belongs to the Agent API (MSoT 2.1, needs operator setup): mention only as "available when enabled", or leave it out. Provider limits (Anthropic, OpenAI, OpenRouter) are outside facts: source URL and checked date in the data file, placeholders on the page if unverified (R2). FAQ answer: no key is needed for the core product (MSoT 1.5). Never "LLM observability" (R4). /pricing has no content yet (MSoT 2.5): link only.

### 9.3 · Claude Code Waiting for Input: What Desk Markers Say

- **Category · intent · page type:** 3D Visualization and Live Updates · Informational · Blog post
- **Plan title:** One Marker per Desk: What "!", a Thought Cloud and "Update" Are Telling You
- **Title tag:** Claude Code Waiting for Input: What Markers Say | Kite Pulse
- **H1:** Claude Code Waiting for Input, Stuck or Near a Limit: What Each Desk Marker Tells You
- **URL:** /blog/claude-code-waiting-for-input
- **Meta description:** Claude Code waiting for input, stuck, near a plan limit or out of date: what each desk marker in a team's live office means, and what to do next.
- **Main keyword:** claude code waiting for input
- **Secondary keywords:**
  - claude code waiting for permission → H3 "Waiting for permission: Claude Code's approval prompts" (under the waiting H2; explains Claude Code's own prompts, and that an exact approval signal in Kite Pulse is coming soon only)
  - ai agent stuck → H2 "Stuck: the head-down marker" (main keyword of 11.4, not yet planned: link once it is)
  - claude code limit tracker → H2 "Near limit and at limit: a Claude Code limit tracker on each name tag"
  - claude code version check → H2 "Update: the out-of-date marker" (main keyword of 4.13: link to /blog/claude-code-version-check)
- **Description:** For developers and team leads who see a marker on a desk and want it decoded. Most people searching this phrase are one developer whose terminal has gone quiet, so the page answers that first: when Claude Code stops to ask a question or to ask permission for a step, and what to do. It then turns to the team view and takes the markers in turn (attention "!", stuck, near limit, at limit, syncing, Update, and a quiet desk that may be waiting), each with what sets it, who sees it and the next step, then task lines on zoom and clicking a room to focus. One Kite Pulse callout at the stuck section: markers come from real steps and plan readings, and nothing moves on a timer. The reader leaves with a copyable one-page marker legend.
- **Interactive elements:**
  1. Marker decoder - a sample desk (labelled sample data); the reader picks a marker and sees what sets it, who can see it (in scope or not) and the next step. The quiet-desk marker is labelled "the agent has been quiet; it may be waiting", never as a signal from Claude Code. Fallback is a table of markers, causes, viewers and next steps.
  2. "Quiet or stuck?" timeline - a sample session's steps; the reader drags time forward and sees a quiet stretch turn into a possible-waiting marker, and a repeated failing step turn into stuck. Thresholds are example values labelled "to confirm". Fallback paragraph explains the difference in words.
- **Images / video (optional):** None - the decoder shows each marker; a real screenshot must come from a deployment (MSoT 2.5).
- **FAQ:**
  - How can I tell if a developer is about to hit their Claude usage limit?
  - How do I find out if developers are on outdated versions of Claude Code?
  - How can I see what my team's AI agents are doing right now?
- **Links to:** /ai-agent-office, /plan-headroom, /blog/ai-retry-loops, /blog/claude-code-version-check, /blog/is-claude-code-stuck (built), /blog/stuck-ai-agent (built)
- **Watch-outs:** The main keyword is the hard part. Claude Code waiting signals and exact approval signals are NOT released (MSoT 2.3, app 0.4.4): no claim that Kite Pulse knows Claude Code is waiting, and "waiting for permission" appears only as coming soon. The Field Guide's "Waiting for you" after two quiet minutes is an inference from silence and is Field Guide only: confirm, and word it as "quiet". If the owner prefers, hold this article until a release carrying the hook is published and keep the marker legend for now. Verified (MSoT 1.2, 1.4): The Office with markers for stuck work or plan limits, detail only within scope; plan headroom (Claude Code only, "near" 80%, "at limit" 100%, stale readings flagged); the Claude Code version check. The marker set ("!", thought cloud, Update, syncing), task lines on zoom and room focus come from the Article Plan and Field Guide: confirm in the console. Claude Code's own behaviour needs Anthropic documentation with a checked date in the data file (R2). Overlaps 2.10 (notices) and the built /blog/is-claude-code-stuck: link both, keep this one to the markers.

### 9.4 · Live View of AI Coding Agents Without Refresh

- **Category · intent · page type:** 3D Visualization and Live Updates · Commercial · Blog post
- **Plan title:** Live Without Pressing Refresh: How The Office and Team Overview Stay Current
- **Title tag:** Live View of AI Coding Agents Without Refresh | Kite Pulse
- **H1:** Live View of AI Coding Agents: How The Office and Team Overview Stay Current Without Pressing Refresh
- **URL:** /blog/live-view-of-ai-coding-agents
- **Meta description:** How a live view of AI coding agents stays current: what updates in seconds, what refreshes every 30 seconds, and why a desk is only as new as its upload.
- **Main keyword:** live view of ai coding agents
- **Secondary keywords:**
  - team status dashboard → H2 "Team Overview: a team status dashboard that refreshes every 30 seconds" (main keyword of 5.1: link to /blog/team-status-dashboard)
  - see what ai agents are doing right now → body of H2 "From a saved session to a moving desk" (main keyword of the built /blog/stuck-ai-agent: link)
- **Description:** For team leads and technical evaluators who want to know how live "live" is before they rely on it. The page follows one step from the developer's computer to the screen: the AI tool saves the session, the desktop program sends only the new part, the team's server processes it, The Office updates in the browser, and Team Overview refreshes every 30 seconds. Then the honest limit: a desk is only as current as that computer's latest upload, so a laptop that drops off the network shows its last known state and catches up when it is back. One Kite Pulse callout at that limit: nothing on the page moves on a timer, every change comes from a real step. The reader leaves knowing what delay to expect and what a stale desk means.
- **Interactive elements:**
  1. Freshness pipeline - a sample step travels computer → server → The Office → Team Overview; the reader switches on "network drops" or "browser loses its connection" and sees which view goes stale and how it recovers. Timings are labelled illustrations, except Team Overview's verified 30-second refresh. Fallback paragraph walks the same path in words.
  2. "How old is this figure?" picker - the reader picks a figure (a desk's state, Team Overview's active time, a plan headroom reading, token totals) and sees where it comes from and what limits its freshness. Fallback is a table of the same rows.
- **Images / video (optional):** None - the pipeline animation is the explanation.
- **FAQ:**
  - How quickly is usage and cost data updated?
  - How can I see team activity in real time?
- **Links to:** /ai-agent-office, /features, /faq, /blog/team-status-dashboard, /blog/stuck-ai-agent (built), /blog/visualize-ai-agents-working (built)
- **Watch-outs:** Verified (MSoT 1.1, 1.2, 1.4): Team Overview refreshes every 30 seconds and past days can be picked; only new activity is sent; offline catch-up; plan figures are as fresh as Claude Code last saved them unless the background refresh (admin switch) is on; old readings are flagged as stale. The Office's push updates "within seconds", the "Live" badge and the 15-second fallback with automatic reconnection come from the Article Plan; the Field Guide says only that The Office updates "in seconds" over a live stream, and does not mention a 15-second fallback: confirm every figure before stating it. No collector upload interval is documented anywhere: do not state one. First FAQ: cost is an estimate per tool, "not billed spend", never totalled across tools (R7). Overlaps the built /ai-agent-office and /blog/visualize-ai-agents-working: keep this page to freshness.

### 9.5 · AI Agents Office Visualization on the Wall

- **Category · intent · page type:** 3D Visualization and Live Updates · Commercial · Blog post
- **Plan title:** The Office on the Wall: Full-Screen Mode for a TV or Meeting Room
- **Title tag:** AI Agents Office Visualization on the Wall | Kite Pulse
- **H1:** AI Agents Office Visualization on the Wall: Full-Screen Mode for a TV or Meeting Room
- **URL:** /blog/ai-agents-office-visualization
- **Meta description:** Put an AI agents office visualization on a team-room TV: full-screen mode, daylight or evening looks, and what the room sees from whose account.
- **Main keyword:** ai agents office visualization
- **Secondary keywords:**
  - ai agents office → H2 "What the AI agents office shows on a wall"
  - team status dashboard → H2 "A team status dashboard for the room, not one laptop" (main keyword of 5.1: link to /blog/team-status-dashboard)
  - virtual office for remote teams → H3 "Sharing it on a call: a virtual office for remote teams" (main keyword of 12.5, not yet planned: one short paragraph, link once it is)
- **Description:** For team leads who run a team room or a hybrid stand-up and want one shared picture on a screen. The page covers why a shared screen helps (everyone starts the stand-up from the same view), how to put The Office in full screen with no menus, the daylight and evening looks, and the point most setups miss: the wall shows what the signed-in account may see, so the room sees that person's scope. It ends with three uses (stand-up room, team room, screen share on a video call). One Kite Pulse callout: desks move only for real steps, sessions and plan readings, so the wall is never decoration. The reader leaves with a copyable wall-screen setup checklist.
- **Interactive elements:**
  1. Wall-screen preview - a sample office (labelled sample data, invented names) inside a framed TV; the reader switches daylight or evening and "signed in as a team lead" or "as a developer" and sees what the room would see. Fallback paragraph describes both looks and the scope rule.
  2. Room checklist builder - the reader picks the room (stand-up room, team room, video call) and gets a copyable setup list: screen, which account, sleep settings, who in the room can see what. Fallback is the list for all three rooms.
- **Images / video (optional):** None - a photo of a real wall screen would need a named deployment (MSoT 2.5); the preview covers it.
- **FAQ:**
  - How do I know what my engineering team is working on right now?
  - How do I see what my team is working on without status meetings?
- **Links to:** /ai-agent-office, /features, /privacy, /blog/team-status-dashboard, /blog/visualize-ai-agents-working (built)
- **Watch-outs:** Leave the Brain view out (row note, R3). The Office is verified (MSoT 1.4); full-screen wall mode and the daylight/evening looks are Field Guide only ("Full screen for a wall"; The Office "keeps its own light and dark looks"): confirm. The admin option to hide other people's desks is in the Article Plan only (13.9): confirm before mentioning. Say plainly that the screen shows the signed-in viewer's scope; detail is only for people in that scope. R4: the screen helps a team start from the same picture, never "watching" anyone. Overlaps the built /ai-agent-office (main keyword "3d virtual office for ai agents") and /blog/visualize-ai-agents-working: keep this to the wall-screen use and link both.

### 9.6 · AI Agent Dashboard: One Office, Four Views

- **Category · intent · page type:** 3D Visualization and Live Updates · Commercial · Blog post
- **Plan title:** 3D, Map, List, Headroom and Brain: One Office, Five Ways to Look
- **Title tag:** AI Agent Dashboard: One Office, Four Views | Kite Pulse
- **H1:** AI Agent Dashboard: One Office, Four Ways to Look (3D, Map, List and Headroom)
- **URL:** /blog/ai-agent-dashboard
- **Meta description:** An AI agent dashboard with four views of one office: 3D desks, a company map, a list for phones, and a Headroom board of who is near a Claude plan limit.
- **Main keyword:** ai agent dashboard
- **Secondary keywords:**
  - ai agents office 3d → H2 "3D: the AI agents office at a glance"
  - team availability dashboard → H2 "List: a team availability dashboard that works on a phone"
  - monitor claude plan usage team → H2 "Headroom: monitor Claude plan usage across the team" (main keyword of the built /blog/sprint-planning-claude-plan-limits: link)
  - see team claude usage limits → body of the Headroom H2
- **Description:** For leads and managers choosing how to look at the same team. The page explains the view switch view by view: 3D desks for a glance at who is working, the map for how people, teams and projects connect, the list for keyboards, screen readers and narrow screens, and the Headroom board for Claude plan pressure (managers and admins). It ends with a "which view for which question" table. One Kite Pulse callout at Headroom: the board lists people worst first, Claude Code only, with "near" at 80% and "at limit" at 100%. The reader leaves knowing which view to open for each of their questions.
- **Interactive elements:**
  1. View switcher - one sample team (labelled sample data) drawn four ways; the reader switches between 3D, map, list and Headroom and sees the same people each time. Fallback is one paragraph per view.
  2. Question-to-view picker - the reader picks a question (who is online, who works with whom, who is near a Claude limit, which project has most people) and is shown the view that answers it. Fallback is the same mapping as a table.
- **Images / video (optional):** None - the switcher shows all four views.
- **FAQ:**
  - How can a Claude team admin see who is close to their usage limit?
  - How can I see what my team's AI agents are doing right now?
- **Links to:** /ai-agent-office, /plan-headroom, /features, /claude-code-usage-limits, /blog/sprint-planning-claude-plan-limits (built)
- **Watch-outs:** Omit the Brain tab (row note, R3): the plan title says five views, the page says four. The view switch, the map and list views and the Headroom board are Field Guide only: confirm, and confirm that the "company map" is not the Brain's graph. Verified (MSoT 1.2): plan headroom, Claude Code only, worst first, "near" 80%, "at limit" 100%, old readings flagged; other tools show "Not reported by this tool" (R7). Headroom is an ordered list of people: describe it as "worst first" and nothing more (R4). Overlaps /plan-headroom and the built /blog/sprint-planning-claude-plan-limits: the Headroom section stays one short H2 with links.

### 9.7 · Monitor Claude Code Agents From One Side Panel

- **Category · intent · page type:** 3D Visualization and Live Updates · Commercial · Blog post
- **Plan title:** Click a Desk: Current Task, Stuck Reasons and Today's Figures in the Side Panel
- **Title tag:** Monitor Claude Code Agents From One Side Panel | Kite Pulse
- **H1:** Monitor Claude Code Agents Across a Team: Click a Desk for the Task, Stuck Reasons and Today's Figures
- **URL:** /blog/monitor-claude-code-agents
- **Meta description:** Monitor Claude Code agents across a team: click a desk for the current task, live step, stuck reasons and today's figures, within the access you have.
- **Main keyword:** monitor claude code agents
- **Secondary keywords:**
  - see what ai agents are doing right now → body of the opening H2 (main keyword of the built /blog/stuck-ai-agent: link)
  - claude code activity monitor → H2 "From a terminal activity monitor to a team view"
  - ai agent status, claude code check agent status → H2 "Check agent status: what the side panel shows" (grouped; one section)
  - cursor ai agent status → H3 "Cursor and the other tools" (under the panel H2)
  - claude code agent stuck → H2 "Stuck reasons" (main keyword of 4.5: link to /blog/claude-code-agent-stuck)
- **Description:** For leads who run Claude Code agents across a team. The ranking results are single-machine terminal tools and Claude Code's own Monitor tool (sheet notes); each is one developer's view, and none shows a team's agents with rules about who may see what. The page says honestly what a local monitor does well (for one developer it may be all that is needed, R9), then what a team view adds, then the side panel field by field: name, presence and tool for everyone; project, task, live step, stuck reasons, plan, sync and today's figures within scope; cost on others' desks for admins only. One Kite Pulse callout at the panel: it shows structure, never message text. The reader leaves with a list of which panel field answers which question.
- **Interactive elements:**
  1. Sample desk panel - one sample agent (labelled sample data); the reader switches the viewer (colleague outside the team, their manager, an admin) and fields appear or disappear. Fallback is a table of fields by viewer.
  2. "Is a local monitor enough?" check - three questions (how many people, do you need rules on who sees what, do you need yesterday as well as now) and an answer that names a single-machine tool where that fits. Fallback paragraph gives the same reasoning.
- **Images / video (optional):** None - the sample panel shows every field.
- **FAQ:**
  - How do I know what my engineering team is working on right now?
  - How do I spot developers who are stuck in long AI sessions?
  - How do I see what my team is working on without status meetings?
- **Links to:** /features, /ai-agent-office, /engineering-intelligence, /integrations/claude-code, /integrations/cursor, /blog/claude-code-agent-stuck, /blog/stuck-ai-agent (built)
- **Watch-outs:** Frame around agents, not people (row note, R4: never "developer monitoring tool"); "monitor" stays inside the keyword phrase only. Side panel fields, stuck reasons and each desk's "today" figures are Field Guide only: confirm. Cost on others' desks for admins only is in the Article Plan; MSoT verifies only that cost per developer is admin-only (1.2). Cursor sessions land on desks like every tool, but plan figures are Claude Code only (R7). Claude Code waiting signals are unreleased (MSoT 2.3). The single-machine tools named in the sheet (ccmon, c9watch, amux, ctx-monitor) and Claude Code's Monitor tool need source links with checked dates in the data file (R2); write placeholders where unverified.

### 9.10 · AI Agent Activity Log: The Last 24 Hours

- **Category · intent · page type:** 3D Visualization and Live Updates · Informational · Blog post
- **Plan title:** The Activity Feed: the Last 24 Hours of the Office in One Stream
- **Title tag:** AI Agent Activity Log: The Last 24 Hours | Kite Pulse
- **H1:** AI Agent Activity Log for a Team: the Last 24 Hours of Sessions, Commits and Stuck Agents in One Feed
- **URL:** /blog/ai-agent-activity-log
- **Meta description:** An AI agent activity log for a team: one feed of sessions, commits, stuck and unstuck agents and approvals from the last 24 hours, within your scope.
- **Main keyword:** ai agent activity log
- **Secondary keywords:**
  - ai agent activity → body of the opening H2
  - activity feed dashboard → H2 "What the activity feed dashboard lists"
  - claude code activity monitor → body of H2 "Reading the feed in two minutes"
  - github activity feed → H3 "How it differs from a GitHub activity feed" (honest: pull requests and reviews belong to GitHub's feed, R9)
  - team collaboration insights → H2 "From the feed to who works with whom" (main keyword of 2.13: link to /blog/team-collaboration-insights)
  - claude code daily summary → body of H2 "A feed is not a summary" (main keyword of 4.9: link to /blog/claude-code-daily-summary)
- **Description:** For team leads and admins who want one stream of what agents did. The ranking pages are single-product audit logs (sheet notes); none is a team stream of coding-agent sessions, commits, stuck stretches and approvals. The page explains what enters the feed and in what order, how scope limits it, and how it differs from three neighbours: the Audit Log (admin actions), My Sessions (one person's sessions in full) and a GitHub feed (pull requests and reviews). It closes with a "which log for which question" section, since many searchers want an audit log. One Kite Pulse callout: the feed shows events, never message text. The reader leaves knowing which log to open for each question.
- **Interactive elements:**
  1. Sample 24-hour feed - a scrollable sample stream (labelled sample data) with filter chips (sessions, commits, stuck and unstuck, approvals) and a time scrubber. Fallback paragraph lists the event kinds in words.
  2. "Which log?" picker - the reader picks a question (who changed a setting, what did the team ship today, what did my agent do in one session, who reviewed a pull request) and gets the feed, the Audit Log, My Sessions or GitHub. Fallback is the same mapping as a table.
- **Images / video (optional):** None - the sample feed shows the stream.
- **FAQ:**
  - How can I see team activity in real time?
  - How do I see what my team is working on without status meetings?
- **Links to:** /integrations/claude-code, /features, /ai-agent-office, /blog/team-collaboration-insights, /blog/claude-code-daily-summary, /blog/audit-log-for-admin-actions
- **Watch-outs:** The activity feed is Field Guide only (a live feed of sessions, commits, stuck stretches and approvals); the 24-hour window, "notes and comings and goings" and "worked out in the browser, never stored" come from the Article Plan: confirm all. Leave out any "notes" that are Brain notes (R3). Verified (MSoT 1.4, 1.6): onboarding and project approvals, My Sessions, the Audit Log (sign-ins and admin changes, read-only). Moderate fit (row note): searchers may want an audit log, which the picker serves. Commits come from session records; the local git history read is not built (MSoT 2.3): do not imply Kite Pulse reads the repository.

### 9.11 · AI Agent Task Board: Status of Work in Progress

- **Category · intent · page type:** 3D Visualization and Live Updates · Commercial · Blog post
- **Plan title:** The Tasks Board: Work in Progress, Stuck, Waiting, Paused, Failed and Done
- **Title tag:** AI Agent Task Board: Status of Work in Progress | Kite Pulse
- **H1:** AI Agent Task Board: Work in Progress, Stuck, Waiting, Paused, Failed and Done Across a Team
- **URL:** /blog/ai-agent-task-board
- **Meta description:** An AI agent task board that shows status, not assignments: work in progress, stuck, waiting, paused, failed and done for every agent you may see.
- **Main keyword:** ai agent task board
- **Secondary keywords:**
  - kanban board for ai agents → H2 "Where it sits next to a kanban board for AI agents"
  - ai agent task tracker → body of H2 "Counters that filter the board"
  - claude code task board → H3 "Claude Code tasks and sub-agents on the board"
  - ai agent stuck → body of H2 "The stuck column" (main keyword of 11.4, not yet planned: link once it is)
  - blocker board engineering → H2 "From one stuck card to the Blocker Board" (main keyword of 8.11: link to /blog/blocker-board-engineering)
  - project health dashboard → body of the closing H2 (main keyword of 2.16: link to /blog/project-health-dashboard)
- **Description:** For team leads who want the state of every agent's work in one place. Ranking pages are agent-orchestration boards that assign work to agents (sheet notes); this board reads the state of work already happening. The page explains each status and what moves a card into it, the counters that filter the board, the approvals and uploads waiting for the viewer, and the extra rows admins see (the processing queue and alerts). It says honestly that a team wanting to hand tasks to agents needs an orchestrator (R9). One Kite Pulse callout at the status columns: statuses are read from the sessions, with nothing to drag or update. The reader leaves with a short "what to do with each column" list.
- **Interactive elements:**
  1. Sample status board - six columns of sample cards (labelled sample data) with counters that filter; clicking a card shows why it has that status. Fallback paragraph defines each status.
  2. "Orchestrator or status board?" check - three questions (do you assign work to agents, do you need to see work already running, across how many people) and an answer that names which kind of tool fits. Fallback is the same reasoning as a short table.
- **Images / video (optional):** None - the sample board is the picture.
- **FAQ:**
  - How do I know what my engineering team is working on right now?
  - How do I spot developers who are stuck in long AI sessions?
- **Links to:** /features, /engineering-intelligence, /ai-agent-office, /blog/ai-retry-loops, /blog/project-health-dashboard
- **Watch-outs:** Position as a status view, never an orchestrator (sheet notes). The Tasks board and its statuses are Field Guide only; "Waiting" rests on the quiet-time inference, not the unreleased Claude Code waiting signal (MSoT 2.3): word it as "quiet". Approvals and uploads awaiting the viewer, and the admin queue and alerts rows, come from the Article Plan; Processing and alerts themselves are verified for admins (MSoT 1.6). Blocker Board is admin by default (MSoT 1.4). Orchestrator products named in the sheet (Decknote MCP, Mission Control, Agent Board and others) need source links with checked dates (R2), or leave them unnamed.

### 9.12 · Engineering Manager Dashboard: Team at a Glance

- **Category · intent · page type:** 3D Visualization and Live Updates · Commercial · Blog post
- **Plan title:** The Office Tab and the Connected Strip: the Team's Figures at a Glance
- **Title tag:** Engineering Manager Dashboard: Team at a Glance | Kite Pulse
- **H1:** Engineering Manager Dashboard: Today's Agents, Sessions, Commits and AI Tools at a Glance
- **URL:** /blog/engineering-manager-dashboard
- **Meta description:** An engineering manager dashboard in one strip: agents working or stuck, sessions and commits today, Claude plan pressure, and the AI tools in use.
- **Main keyword:** engineering manager dashboard
- **Secondary keywords:**
  - ai coding tools usage analytics for teams → H2 "The AI tools in use"
  - claude code skills used across team → H3 "Skills used today" (main keyword of 2.25: link to /blog/claude-code-skills-used-across-team)
  - mcp servers installed across team → body of the skills H3 (Agent Setup, an optional read)
  - engineering metrics dashboard → H2 "Where it ends and an engineering metrics dashboard begins" (main keyword of 6.2: link to /blog/engineering-metrics-dashboard)
- **Description:** For engineering managers who want the team's day in one look before opening any page. The page goes through the Office tab and the connected strip figure by figure (agents, working, stuck, sessions and commits today, Claude plan counts, connectors and skills used, AI tools and code hosts in use), says where each one comes from and which page it opens, then where the glance ends: delivery metrics such as DORA belong to git and ticket tools (R9, link /compare). One Kite Pulse callout: every figure reads the same sessions as the other pages, so the strip and the team pages agree. The reader leaves with a three-question morning routine built on the strip.
- **Interactive elements:**
  1. Sample strip with definitions - one row of sample tiles (labelled sample data); hovering or tapping a tile shows its source, who can see it and the page it opens. Fallback is a table of tiles, sources and pages.
  2. Morning-question picker - the reader picks up to three questions (who is stuck, are we near a Claude limit, which tools are we paying for, what shipped yesterday) and gets the tile and page for each. Fallback is the same mapping as a list.
- **Images / video (optional):** None - the sample strip shows the layout.
- **FAQ:**
  - How can I see all AI coding tools my team uses in one place?
  - Which AI coding tools is each developer using?
  - How many AI agents is my team running right now?
- **Links to:** /engineering-intelligence, /features, /integrations, /ai-agent-office, /compare, /blog/engineering-metrics-dashboard, /blog/claude-code-skills-used-across-team
- **Watch-outs:** Drop the Brain notes count (row note, R3). The Office tab and connected strip are Field Guide only (the room's counts, connectors and skills): confirm each figure, and that "code hosts in use" is read from repository addresses. Connectors are verified (MSoT 1.6) but what their data feeds was not checked: say only that they are connected. Skills used is the Agent features tab (MSoT 1.2); skills and MCP servers installed need Agent Setup's optional read (admin switch, MSoT 1.1). Third FAQ: Agents in parallel is verified (MSoT 1.4) but shows admins anyone and managers only themselves, so answer from the Office counts and say this. "Waiting" counts rest on the quiet-time inference (MSoT 2.3). No cost total across tools (R7).

### 9.13 · Team Overview Dashboard: Find Your Team Fast

- **Category · intent · page type:** 3D Visualization and Live Updates · Commercial · Blog post
- **Plan title:** Finding People Fast: the Team Picker, Filter Tiles and One-Click Team Suggestions
- **Title tag:** Team Overview Dashboard: Find Your Team Fast | Kite Pulse
- **H1:** Team Overview Dashboard: the Team Picker, Filter Tiles and One-Click Team Suggestions
- **URL:** /blog/team-overview-dashboard
- **Meta description:** A team overview dashboard for larger organisations: open one team's office, narrow it with filter tiles, and create teams from who already works together.
- **Main keyword:** team overview dashboard
- **Secondary keywords:**
  - team members dashboard → H2 "One team's members on one screen"
  - filter by team → H2 "Filter by team, then by state"
  - who works with whom → H2 "Team suggestions from who works with whom"
  - team availability dashboard → body of the members H2 (presence, plus Leave & On-Call)
  - team status dashboard → body of the opening H2 (main keyword of 5.1: link to /blog/team-status-dashboard)
- **Description:** For team leads and admins in organisations with more than a handful of teams. The ranking pages are help-centre pages from unrelated products (sheet notes), so the page defines its terms first: Team Overview is the console page of live team status, and The Office can be narrowed to one team. It then covers picking one team's office, the filter tiles (stuck, near a limit, offline), and team suggestions built from who worked on the same projects, created in one click by a team editor. One Kite Pulse callout at suggestions: teams keep dated membership, so history stays accurate when people move. The reader leaves knowing how to get from a big office to one team's view in two clicks.
- **Interactive elements:**
  1. Sample office of four teams - the reader picks a team and switches filter tiles on and off (labelled sample data). Fallback paragraph describes the picker and tiles.
  2. Team suggestion demo - a sample of who worked on which projects over 30 days produces a suggested project team; the reader accepts or edits it. Fallback paragraph explains how suggestions are formed.
- **Images / video (optional):** None - the two samples cover it.
- **FAQ:**
  - Can I compare AI usage between teams?
  - Can I compare AI coding-tool usage across engineering teams?
- **Links to:** /features, /ai-agent-office, /ai-budgets, /blog/team-status-dashboard, /blog/team-collaboration-insights
- **Watch-outs:** Weak fit (row note): little search demand; the owner may prefer to merge this into 9.6 or 2.11. Do not blur the console page "Team Overview" (MSoT 1.4) with The Office's team picker: name both. The team picker, filter tiles and one-click suggestions are Field Guide only (project teams suggested from who worked on the same projects in the last 30 days): confirm. Verified (MSoT 1.4, 1.2): Teams with dated membership (admin by default), Leave & On-Call, AI Budgets per team. Both FAQs: teams feed The Office, Team Review, AI Collaboration and AI Budgets, and Reports has no team filter (MSoT corrections); cost appears per team only in AI Budgets and is never totalled across tools (R7).
