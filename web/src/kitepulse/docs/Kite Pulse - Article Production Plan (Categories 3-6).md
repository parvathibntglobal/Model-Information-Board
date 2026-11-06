# Kite Pulse - Article Production Plan, Categories 3-6

Draft for review, 4 November 2026. 30 articles (3.2 to 6.14): the category 3-6
articles marked "separate article" in `Kite Pulse - Article Keyword Map.xlsx`, minus
the ones already built as blogs (3.1, 3.6, 4.4, 4.6, 4.14, 5.12, 5.13, 6.1, 6.3, 6.5,
6.7, 6.10). 3.1 was planned here first and then removed: its main keyword is the one
the built /blog/stuck-ai-agent targets. The two category 3 stories marked "write without keyword" (3.4, 3.5) are left
out, as the first batch left out everything not marked "separate article".

Each entry gives the SEO title (main keyword first, at most 60 characters with
" | Kite Pulse"), H1, URL, meta description (at most 155 characters), where each
secondary keyword goes, a short description of how the article is built, its 1-3
interactive elements, optional images or video (only where they add something a
widget cannot), FAQs, links and watch-outs. Entries carry a **Section** line where
the article belongs outside the Blog (here: 4.2, 5.9, 5.11 and 6.14 in Guides &
tools); the rest are Blog posts. Product facts follow the Master Source
of Truth and the rules in `MASTER-PROMPT.md`. Nothing here is written article copy.

Use Cases articles (category 3) are stories: names and numbers in them are
illustrations, labelled as such on the page, never customer results.

---

### 3.2 · Claude Approaching Weekly Limit: Moving a Migration

- **Category · intent · page type:** Use Cases · Informational · Story
- **Plan title:** Moving the Migration to Monday: a Plan-Limit Save
- **Title tag:** Claude Approaching Weekly Limit: A Team Story | Kite Pulse
- **H1:** Claude Approaching Weekly Limit: How One Team Moved a Migration to Monday
- **URL:** /blog/claude-approaching-weekly-limit
- **Meta description:** Two developers with Claude approaching the weekly limit, one large migration, and the plan-headroom check that moved the work to Monday before it stalled.
- **Main keyword:** claude approaching weekly limit
- **Secondary keywords:**
  - claude code team usage limits → H2 "Thursday: checking the team's Claude Code usage limits" (main keyword of 5.3: link to /plan-headroom, which absorbs it)
  - claude code limit tracker → body of the Thursday section, one sentence on what Plan headroom tracks (5-hour, weekly and per-model weekly windows, worst first)
  - ai plan limits → H3 "Why AI plan limits are a planning input" (one paragraph: Claude plans have windows; other tools show "Not reported by this tool")
  - claude code hit limit mid task → H2 "What happens when a window runs out anyway" (main keyword of 7.4: link)
- **Description:** For team leads and engineering managers who schedule heavy AI work. Ranking pages explain Claude's limits to one user; none shows a lead checking a whole team before assigning a big task. The story runs over three days: Thursday the lead opens Plan headroom before planning and sees two developers past 85% of their weekly window (flagged "near", 80% or more); the lead checks which other people have room; the migration moves to Monday when the windows have reset; a closing section covers what to do if a window still runs out. The Kite Pulse callout sits on Thursday: Plan headroom lists everyone worst first and flags old readings as stale rather than hiding them. The reader leaves with a short pre-planning check they can run before any large AI task.
- **Interactive elements:**
  1. Headroom board - a sample team of six (labelled sample data) with weekly and 5-hour bars; the reader sorts worst first and toggles "stale reading" on one person to see the flag; anyone at 80% or more turns amber, 100% red. Fallback is a small table of the same six people and their windows.
  2. "Who takes the migration?" picker - the reader assigns a sample heavy task to one of the six and sees whether that person's weekly window would likely run out before the task ends, using an example task size labelled as an illustration. Fallback paragraph explains the rule of thumb (check the weekly window and its reset day before assigning).
- **Images / video (optional):** None - the board is the picture; a real Plan headroom screenshot would need a deployment (MSoT 2.5).
- **FAQ:**
  - How do I plan sprints around AI plan limits?
  - How do I know which developers are close to their Claude limit?
  - How do I stop my team losing work time to Claude limits?
  - How can I tell if a developer is about to hit their Claude usage limit?
- **Links to:** /plan-headroom, /claude-code-usage-limits, /features (the sheet lists /reports, which the site folds into /features and /plan-headroom), /blog/sprint-planning-claude-plan-limits (built), /blog/avoid-hitting-claude-limit (built)
- **Watch-outs:** R7: Claude Code only; never "plan limits across tools". Figures are as fresh as Claude Code last saved them, unless the background refresh is on (admin switch, app 0.4.2+; developers can opt out). The "plan limit reached" notice with a reset time is Field Guide only (line 181), not MSoT Section 1: confirm before naming it, or keep the last section to Plan headroom's "at limit" state. "85%" is the story's illustration, not a threshold; the product's thresholds are 80% and 100%. The built pages /blog/sprint-planning-claude-plan-limits and /blog/avoid-hitting-claude-limit cover planning and the individual's view: keep this one to the story and link both. Do not state Anthropic's limit sizes; if mentioned, source and date them in the data file (R2).

### 3.3 · Repeated Errors in AI Coding Sessions: One Test

- **Category · intent · page type:** Use Cases · Informational · Story
- **Plan title:** The Test the AI Retried Six Times
- **Title tag:** Repeated Errors in AI Coding Sessions: A Story | Kite Pulse
- **H1:** Repeated Errors in AI Coding Sessions: the Test the AI Retried Six Times
- **URL:** /blog/repeated-errors-in-ai-coding-sessions
- **Meta description:** Repeated errors in AI coding sessions often trace to one setup problem. A developer finds the test her AI retried six times, fixes it once, and moves on.
- **Main keyword:** repeated errors in ai coding sessions
- **Secondary keywords:**
  - developer scorecard → H2 "Monday: the scorecard points at one command" (main keyword of 2.5: link to /blog/developer-scorecard)
  - failing commands analytics → body of H2 "Is it only me?", one paragraph on how Work Problems groups failed commands across a team (main keyword of 2.14: link)
  - ai coding error rate → H3 "Reading the error rate before and after" (the developer's own failed-command count, week on week)
  - claude code stuck in loop → body of the Monday section, one sentence that a retried command is how a loop often starts (main keyword of 3.14: link)
- **Description:** For developers who suspect their AI keeps hitting the same wall. Pages on this topic give general debugging advice; none shows a developer finding the one command behind most of her failures. The story: on Monday a developer opens My Scorecard & Insights and its Top 3 points at one test command retried six times in a week, with the evidence; she opens the sessions and sees the same missing environment setting each time; she fixes the setup once; the next week her failed commands drop. A short section asks whether teammates hit the same error, which is where Work Problems comes in. One Kite Pulse callout at Monday: each insight gives a verdict, why it matters, what to try and the evidence, and says "not enough data" rather than guessing. The reader leaves with a three-step way to find their own most-repeated failure.
- **Interactive elements:**
  1. Sample session log sorter - a week of sample failed commands (labelled sample data); the reader groups them by command and sees one test command account for most of the failures, then clicks it to see the six attempts and the repeated error line. Fallback paragraph describes the grouping and the result.
  2. Before-and-after chart - a two-week sample of the developer's failed commands per day, with the fix day marked; drawn to scale with labelled axes and marked "illustration". Fallback sentence states the two weekly totals in the sample.
- **Images / video (optional):** None - the sorter shows the finding better than a screenshot.
- **FAQ:**
  - How do I know when AI is retrying the same failed fix repeatedly?
- **Links to:** /blog/ai-retry-loops, /features, /blog/developer-scorecard, /blog/failing-commands-analytics, /blog/claude-code-stuck-in-loop
- **Watch-outs:** Failed tool calls are recorded for every tool except Aider; command exit codes come from Claude Code, Codex and Copilot only (MSoT 1.1): the story's tool should be Claude Code. Work Problems is admin by default (MSoT 1.2); a developer cannot open it unless granted, so the "is it only me?" section is told from the lead's side or says to ask an admin. The six retries and the fix result are illustrations, labelled so; no claim of time saved (R2). Never frame the scorecard as ranking (R4).

### 3.7 · Knowledge Transfer Before an Employee Leaves a Team

- **Category · intent · page type:** Use Cases · Informational · Story
- **Plan title:** Before the Only Expert Moves Teams
- **Title tag:** Knowledge Transfer Before an Employee Leaves | Kite Pulse
- **H1:** Knowledge Transfer Before an Employee Leaves: the Only Expert Who Moved Teams
- **URL:** /blog/knowledge-transfer-before-leaving
- **Meta description:** Knowledge transfer before an employee leaves works best aimed at what only they know. How one team found those parts in AI sessions and handed them over.
- **Main keyword:** knowledge transfer before leaving employee
- **Secondary keywords:**
  - knowledge transfer checklist template → H2 "The hand-over checklist they used" (a copyable checklist, the page's takeaway)
  - knowledge transfer before retirement → one sentence in the introduction that the same approach fits a retirement or long leave
  - engineering knowledge management → H3 "Keeping what was written down findable" (main keyword of 8.15: link)
  - capability mapping tools → H3 "Finding the parts only one person touches", one paragraph on the Capability Map (main keyword of 12.8: link)
  - lessons learned software development → body of the hand-over section, one sentence on knowledge records (main keyword of 8.14: link)
- **Description:** For engineering managers and admins facing a move or departure. Ranking pages are HR advice (interview the person, document everything); nothing engineering-specific shows how to find which parts of a codebase only the departing person works on and aim the hand-over at those. The story: an engineer is moving teams in three weeks; the manager looks at the project's Capability Map and session history to see which areas only that person changed; they agree a short list instead of "document everything"; the engineer writes up two areas and pairs on one; knowledge records quoted from real sessions keep the answers findable. One Kite Pulse callout at the "finding" step: the Capability Map describes each project in plain terms and needs no AI model. The reader leaves with a copyable checklist.
- **Interactive elements:**
  1. Who-touched-what grid - a sample project's six areas against four people (labelled sample data); the reader clicks a person to "move" them and sees which areas lose their only editor, which become the hand-over list. Fallback paragraph explains the method: list areas, count who edits each, start with those that have one editor.
  2. Checklist builder - the reader ticks which areas, notes and accounts apply and gets a copyable hand-over checklist with an owner and date per line. Fallback is the checklist as plain text.
- **Images / video (optional):** None.
- **FAQ:**
  - How can I capture knowledge from AI coding sessions?
  - How do I stop my team solving the same bug twice?
- **Links to:** /features, /blog/institutional-knowledge, /engineering-intelligence
- **Watch-outs:** The plan card's capability ownership, bus factor, Tenure & Departure report and knowledge-capture requests are not in MSoT Section 1; the Field Guide mentions only an "Ownership tab" on the Capability Map (line 763). Confirm before naming any of them; until then build the story on the verified Capability Map (a person builds and approves it; no AI) and knowledge records. Knowledge records need AI labelling and an approved knowledge label list, and start as "proposed" (MSoT 1.5): say so. Do not call them a "Knowledge Base" (R3, switched off). R4: the story describes the work, never rates the person leaving. Overlaps 8.17 and 8.18 (bus factor, offboarding): keep this one to the story.

### 3.10 · Claude Code Reading Secrets: A Live Key Found

- **Category · intent · page type:** Use Cases · Informational · Story
- **Plan title:** A Live Key in an AI Conversation
- **Title tag:** Claude Code Reading Secrets: A Live Key Story | Kite Pulse
- **H1:** Claude Code Reading Secrets: What One Team Did About a Live Key in an AI Conversation
- **URL:** /blog/claude-code-reading-secrets
- **Meta description:** When Claude Code reading secrets puts a live key in session history, prevention is too late. How one admin found the masked key and tracked it to rotation.
- **Main keyword:** claude code reading secrets
- **Secondary keywords:**
  - how to hide secrets from claude code → H2 "Before: how to hide secrets from Claude Code" (short prevention recap, linking /blog/secrets-in-ai-prompts)
  - claude code protect secrets → body of the same H2, one sentence
  - claude code api key leaked → H2 "When a Claude Code API key has already leaked"
  - redact secrets from claude code logs → H3 "What masking did on the way in" (where secrets are masked: computer, then server)
  - secret masking → body of that H3 (main keyword of 1.3: link to /blog/secret-masking)
  - leaked credentials in ai chats → H2 "Tracking each leaked credential to resolution" (main keyword of 11.15: link)
  - ai secret scanning → one sentence in the same H2 (main keyword of 6.10: link to /blog/ai-secret-scanning, built)
- **Description:** For security and IT teams. Ranking pages (including The Register's report of Claude Code reading a .env file) are all about stopping the read with deny rules and sandboxes; none covers what to do once a key is already in session history. The story: a developer pastes a key to get past an error; Kite Pulse masks it before upload; later an admin sees the masked key on the Leaked Credentials page, sets its status, asks the owner to rotate it at the provider and marks it resolved. A short "before" section recaps prevention. One Kite Pulse callout at the masking step: 36 credential patterns masked on the computer, again on the server, and a part that fails masking is not sent. The reader leaves with a five-step response checklist.
- **Interactive elements:**
  1. Leak response tracker - a sample Leaked Credentials list (labelled sample data, obviously fake keys such as "sk-EXAMPLE-0000"); the reader moves one item through statuses and sees the checklist step that goes with each. Fallback is the five steps as a numbered list.
  2. "Where is it masked?" toggle - the reader picks a tool (Claude Code, Cursor, OpenCode, another) and sees where masking happens: on the computer and on the server, or on the server only for Cursor and OpenCode chat text. Fallback table.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I find passwords or API keys leaked in AI chats?
  - How do I detect secrets or API keys pasted into AI tools?
  - How are secrets and credentials handled before upload?
- **Links to:** /blog/secrets-in-ai-prompts, /security, /privacy, /shadow-ai, /blog/secret-masking, /blog/ai-secret-scanning (built)
- **Watch-outs:** Leaked Credentials is MSoT Section 2 (Partial): it fills only after a server operator runs a command-line scan, and the status is set by hand, not checked with the provider. Say both; never "automatic leaked-credential scanning" (R8). Masking does not revoke a key: rotation at the provider is the owner's job. Secrets are "masked", never "removed" (R6). Security watch (pasted secrets tab) is Field Guide / AI labelling territory and not in MSoT Section 1: leave it out. The Register fact needs its URL and checked date in the data file (R2).

### 3.11 · Weekly Engineering Report Without the Spreadsheet

- **Category · intent · page type:** Use Cases · Informational · Story
- **Plan title:** The Friday Spreadsheet Nobody Builds Any More
- **Title tag:** Weekly Engineering Report Without a Spreadsheet | Kite Pulse
- **H1:** The Weekly Engineering Report Nobody Builds by Hand Any More
- **URL:** /blog/weekly-engineering-report
- **Meta description:** A weekly engineering report used to mean a Friday spreadsheet. How one manager replaced it with a scheduled company report emailed to leadership as a PDF.
- **Main keyword:** weekly engineering report
- **Secondary keywords:**
  - company ai usage report → H2 "What the company report puts in front of leadership" (main keyword of 5.12: link to /blog/company-ai-usage-report, built)
  - monthly engineering report → H3 "Weekly for the team, monthly for the board" (main keyword of 11.10: link)
  - ai usage report pdf → body of H2 "Friday, 9:00: the PDF arrives" (format choice: PDF or CSV)
- **Description:** For engineering managers and the leaders they report to. Ranking pages give report templates to fill in by hand; this one is about not filling one in. The story: a manager spends Friday afternoons pasting tool exports into a spreadsheet; they open the Company report, which compares any period with the one before; an admin schedules it weekly by email as a PDF, with a preview and a send history; the following Friday leadership reads it and the manager's afternoon goes back to the team. One Kite Pulse callout at the scheduling step: the Company report or one developer's report emailed daily, weekly or monthly, PDF or CSV. The reader leaves knowing what a weekly report should hold and what to leave out.
- **Interactive elements:**
  1. Report builder - the reader picks period (week, month), audience (team, leadership) and format (PDF, CSV) and sees a sample report outline with the sections that suit that audience (labelled sample data). Fallback is the two outlines as plain lists.
  2. "This week against last week" sample - a small sample table of active developers, sessions and tokens for two weeks with the change shown, to show the period comparison. Fallback sentence states the comparison in words.
- **Images / video (optional):** A real Company report PDF page, only if taken from a deployment and dated (MSoT 2.5); otherwise none.
- **FAQ:**
  - How do I create a weekly AI usage report for my team?
  - How do I report AI tool ROI to leadership?
- **Links to:** /features (the sheet lists /reports, folded into /features), /blog/ai-weekly-team-report, /engineering-intelligence, /blog/company-ai-usage-report (built), /blog/scheduled-engineering-reports
- **Watch-outs:** Scheduling and downloads are admin by default; email must be set up on the server (MSoT 1.3, 2.1). Second FAQ: there is no ROI figure in the product (MSoT 2.5); answer with the inputs Kite Pulse gives (tokens, estimated cost per tool, seat prices, active time) and say the ROI judgement is the reader's. Cost is per tool, "not billed spend", never summed across tools (R7). Reports has no team filter (MSoT Website corrections). Overlaps 2.28 (feature) and 11.10 (workflow): keep this one to the story.

### 3.12 · Two Developers Working on the Same Branch, Caught

- **Category · intent · page type:** Use Cases · Informational · Story
- **Plan title:** Two People, One Service, One Stand-up
- **Title tag:** Two Developers Working on the Same Branch | Kite Pulse
- **H1:** Two Developers Working on the Same Branch: Catching It Before Stand-up
- **URL:** /blog/two-developers-same-branch
- **Meta description:** Two developers working on the same branch is easy to fix in git and cheaper to catch early. How a lead saw two people in one service and paired them first.
- **Main keyword:** two developers working on same branch
- **Secondary keywords:**
  - git two developers working on same branch → H2 "The git side: two developers on one branch" (a short, correct git how-to: pull and rebase often, small commits, or separate feature branches)
  - avoid merge conflicts git → H3 "Avoid merge conflicts in git before they start"
  - team collaboration insights → H2 "How the lead spotted it", Collaboration paragraph (main keyword of 2.13: link to /blog/team-collaboration-insights)
  - team status dashboard → body of the same H2, Team Overview paragraph (main keyword of 5.1: link)
  - engineering visibility tool → one sentence in the closing section (main keyword of 7.1: link)
- **Description:** For team leads. The searcher wants a git how-to, and ranking pages give purely git mechanics after the collision; so the page answers the git question first in a short, useful section, then tells the story of catching it earlier. Story: before stand-up the lead opens Team Overview and sees two people on the same project; Collaboration shows both have sessions in it this week; at stand-up the lead pairs them for the day instead of letting them meet in a merge conflict on Thursday. One Kite Pulse callout at the spotting step: Collaboration lists projects several people work on, with contributors, shared sessions and last activity. The reader leaves with the git checklist and a one-line habit for the lead.
- **Interactive elements:**
  1. Branch collision simulator - two sample developers make commits on one branch on a small timeline; the reader picks "pull often", "separate branches" or "do nothing" and sees where a conflict appears. Fallback paragraph gives the three outcomes in words.
  2. Sample stand-up board - a sample team of five with each person's current project (labelled sample data); two share one project and are highlighted, and the reader can open the sample Collaboration row for it. Fallback sentence.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I know what my engineering team is working on right now?
  - How do I see what my team is working on without status meetings?
  - How can I see team activity in real time?
- **Links to:** /features, /engineering-intelligence, /blog/team-collaboration-insights, /blog/what-is-my-team-working-on, /ai-agent-office
- **Watch-outs:** WEAK FIT (sheet note): treat the main keyword as a hook, answer the git question honestly first (R9). Kite Pulse sees projects, not branches by default: the current branch name is an optional read, off until an admin turns it on (MSoT 1.1). Do not claim it detects two people on one branch unless that read is on; say "same project". Team Overview refreshes every 30 seconds; "real time" in the FAQ answer should say that, not "live". Managers see their own reporting line only (MSoT 1.4).

### 3.13 · Turn Repeated Workflows into Claude Code Skills

- **Category · intent · page type:** Use Cases · Commercial · Story
- **Plan title:** From a Repeated Workflow to a Team Skill
- **Title tag:** Turn Repeated Workflows into Claude Code Skills | Kite Pulse
- **H1:** Turn Repeated Workflows into Claude Code Skills: How One Team Stopped Re-typing the Same Steps
- **URL:** /blog/turn-workflows-into-claude-code-skills
- **Meta description:** How one team turned repeated workflows into Claude Code skills: a draft built from their own sessions, reviewed, approved and shared, no AI model needed.
- **Main keyword:** turn repeated workflows into claude code skills
- **Secondary keywords:**
  - find repeated prompts in claude code → H2 "Step one: finding the work they kept repeating"
  - generate claude code skill → H2 "The draft skill, built by rules"
  - create claude code skill → H3 "Editing the draft before approving it" (what a person changes by hand)
  - claude code skills used across team → H2 "A month later: is anyone using it?" (main keyword of 2.25: link to /blog/claude-code-skills-used-across-team)
- **Description:** For DevEx and platform teams on Claude Code. Ranking pages explain how to write a skill by hand; none starts from the team's own sessions to decide which skill to write. The story: three developers each type the same release-notes steps every week; Skill Candidates finds the repeated workflow and proposes a draft Claude Code skill; the platform lead reviews and edits it, then approves; a month later the Agent features tab shows sessions using it. One Kite Pulse callout at the draft step: Skill Candidates builds drafts by rules from repeated workflows, for a person to approve or reject, with no AI model. The reader leaves with a short test for which of their workflows deserves a skill.
- **Interactive elements:**
  1. Workflow spotter - a sample list of a team's session steps over a week (labelled sample data); the reader groups by repeated sequence and sees one sequence appear in several people's sessions. Fallback paragraph explains the grouping.
  2. Draft skill viewer - a sample draft skill file the reader can edit in place and "approve", with a note on what a reviewer should check (paths, secrets, scope). Fallback is the sample draft as a code block.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I share AI best practices across my team?
  - Which Claude Code features (sub-agents, plan mode, MCP tools) does my team use?
- **Links to:** /skill-candidates, /integrations/claude-code, /blog/institutional-knowledge, /blog/claude-code-skills-used-across-team, /blog/claude-code-agent-features-usage (built)
- **Watch-outs:** Sheet note: close to /skill-candidates; keep it a story, not a feature pitch, and link there for the feature. Skill Candidates and Session Graph are MSoT 1.5 (no AI). Seeing installed skills across machines is Agent Setup, an optional read (admin switch; plugins need app 0.4.3): for the "a month later" section use the verified Agent features tab, or flag the optional read. Second FAQ: Agent features tab (MSoT 1.2) answers it; Claude Code only.

### 3.14 · Claude Code Stuck in a Loop: A Two-Hour Session

- **Category · intent · page type:** Use Cases · Informational · Story
- **Plan title:** The Two-Hour Session That Went in Circles
- **Title tag:** Claude Code Stuck in Loop: A Two-Hour Session | Kite Pulse
- **H1:** Claude Code Stuck in a Loop: Replaying the Two-Hour Session That Went in Circles
- **URL:** /blog/claude-code-stuck-in-loop
- **Meta description:** Claude Code stuck in a loop for two hours: a developer replays the session step by step, finds where it turned, and writes a clearer request next time.
- **Main keyword:** claude code stuck in loop
- **Secondary keywords:**
  - claude code session history viewer → H2 "Opening the session again" (My Sessions and the session's detailed view)
  - claude code transcript viewer → H3 "Reading the turns in order" (under the same H2)
  - secret masking → one sentence in the replay section that secrets in the transcript stay masked (main keyword of 1.3: link to /blog/secret-masking)
- **Description:** For developers reviewing their own work. Ranking pages give tips to break a loop while it happens; none shows looking back at a finished loop to learn from it. The story: a developer's agent spends two hours fixing and re-breaking the same import; the next morning she opens the session in My Sessions, reads the turns in order, and sees the point where the request was vague and the agent started guessing; she rewrites the request and the next session ends in twenty minutes. One Kite Pulse callout at the replay: My Sessions keeps every session with a summary and a detailed view, secrets masked. The reader leaves with three signs a session has started to loop.
- **Interactive elements:**
  1. Loop replay - a sample session of twelve turns (labelled sample data); the reader steps through and a counter shows the same file and error coming back; the turn where the request went vague is highlighted when found. Fallback paragraph tells the turning point in words.
  2. "Rewrite the request" exercise - the reader picks the better of three sample rewrites of the vague request and sees why each would or would not have helped. Fallback lists the three with one-line reasons.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I know when AI is retrying the same failed fix repeatedly?
- **Links to:** /integrations/claude-code, /blog/ai-retry-loops, /privacy, /blog/claude-code-session-replay, /blog/claude-code-session-analysis (built), /blog/is-claude-code-stuck (built)
- **Watch-outs:** Session Playback (turn-by-turn replay with a timeline), the no-AI Session Summary and "What the agent did" come from the Article Plan and Field Guide, not MSoT Section 1, which verifies only "My Sessions (every session with a summary, filters and a detailed view)": confirm before naming them, and build the story on My Sessions until then. Near-duplicate of the built /blog/claude-code-session-analysis (sheet note on 4.6): keep this one to the loop story and link. Session records can include code excerpts. Two hours and twenty minutes are illustrations.

### 3.15 · Claude Code for Engineering Managers: Ask Your Data

- **Category · intent · page type:** Use Cases · Informational · Story
- **Plan title:** A Manager Who Asks Her Own Assistant
- **Title tag:** Claude Code for Engineering Managers: A Story | Kite Pulse
- **H1:** Claude Code for Engineering Managers: Asking Your Own Assistant About the Team's Work
- **URL:** /blog/claude-code-for-engineering-managers
- **Meta description:** Claude Code for engineering managers: one manager connects her assistant to her team's engineering data over MCP and asks questions within her own access.
- **Main keyword:** claude code for engineering managers
- **Secondary keywords:**
  - claude code connect to mcp server → H2 "Connecting Claude Code to the MCP server" (main keyword of 13.16 is close: link)
  - mcp server for claude code → body of the same H2
  - read only mcp server → H3 "Why it can only read what she can read" (main keyword of 10.9: link)
  - mcp dry run → one sentence on previewing a change before it runs (main keyword of 10.12: link)
  - claude code analytics admin api → H3 "How this differs from Anthropic's own admin API" (one honest paragraph: Anthropic's API reports Claude usage for its own accounts; this reads the team's sessions across tools)
- **Description:** For engineering managers who already work inside Claude Code. Search shows no guide to a manager using Claude Code on team engineering data (sheet gap note). The story: a manager asks an admin for a key; she connects Claude Code to the team's Kite Pulse server; she asks which projects had the most failed tool calls this month and gets an answer limited to her reporting line; she drafts her weekly update from the answer and checks two figures against the console. One Kite Pulse callout at the connection step: a key never sees more than its owner, re-checked on every request, and prompt text and AI replies are never available over MCP. The reader leaves knowing what to ask their admin for and what such an assistant can and cannot see.
- **Interactive elements:**
  1. Question tryout - the reader picks one of five sample questions and sees a sample answer, with a note on which role's data it was limited to (labelled sample data). Fallback lists the five questions and what each draws on.
  2. Setup checklist - the reader picks their assistant (Claude Code, Cursor, VS Code) and gets the steps: ask the admin for a key, add the server, test with one question. Fallback is the steps as text.
- **Images / video (optional):** None.
- **FAQ:**
  - Is there an API or MCP server for engineering analytics?
  - Can I let an AI assistant summarise my team's engineering activity?
  - Can an AI assistant write my weekly team update from engineering data?
- **Links to:** /docs, /blog/ai-weekly-team-report, /privacy, /integrations/claude-code
- **Watch-outs:** The whole story rests on MSoT Section 2.1 (Needs operator setup): the Agent API and MCP server are off on a standard install, need two server settings, and must be written "available when enabled", never a default feature (R8). In the default chat mode, a non-admin key may only call whoami and my_usage, since ask needs a separate Agent API AI key and an admin-only permission by default; the story's questions need Direct access, which is an admin choice. Say both. "About 115 read tools" is MSoT wording; do not use the Field Guide's 129. Anthropic Admin API facts need a source URL and checked date in the data file (R2). No ROI or productivity claims.

### 4.1 · AI Code Attribution: Keep Credit for AI-Assisted Work

- **Category · intent · page type:** Benefits for Individual Developers · Commercial · Blog post
- **Plan title:** Never Lose Credit for Work You Did with AI
- **Title tag:** AI Code Attribution for Your Own Work | Kite Pulse
- **H1:** AI Code Attribution for Developers: Keep Credit for the Work You Did with AI
- **URL:** /blog/ai-code-attribution
- **Meta description:** AI code attribution from the developer's side: how to make sure work done inside AI sessions is on the record, project by project, across machines.
- **Main keyword:** ai code attribution
- **Secondary keywords:**
  - tracking ai generated code → H2 "Tracking AI-generated code versus tracking the work behind it" (an honest section on what session records can and cannot attribute)
  - claude code activity log → body of H2 "What counts as your work: sessions, not lines" (main keyword of 2.9: link)
  - my ai coding stats → H3 "Your own AI coding stats, project by project" (main keyword of 4.8: link)
- **Description:** For developers on a team that uses Kite Pulse, whose work increasingly happens inside AI conversations that never show up as a commit message or a ticket comment. Pages ranking for "ai code attribution" are about licensing and marking which lines an AI wrote; this page takes the other meaning, credit for your own effort, and says so in its first paragraph. The reader goes from why AI-heavy work goes missing from the record (long sessions, dead ends, exploration with no commit), to what Workspace shows for each project (detected, waiting to sync, syncing, processing, processed or failed), to fixing gaps in My Projects (confirm, rename, split or remove), and to what happens with two laptops or a dropped network. One Kite Pulse callout at the Workspace section: one repository on several machines counts as one project, and the program catches up after the network drops. The reader leaves with a short weekly check of their own record.
- **Interactive elements:**
  1. "Is my work on the record?" checker - a sample Workspace list (labelled sample data) with one project in each state; the reader clicks a state and sees what it means and the one action that fixes it (confirm in My Projects, wait for approval, check the tray's View log). Fallback is a two-column table of states and next steps.
  2. Two-laptop merge - a sample week of sessions from a work laptop and a home desktop (labelled) shown as two folders; the reader toggles "same repository address" and the two collapse into one project with combined sessions. Fallback sentence states the rule.
- **Images / video (optional):** None - the checker shows the states better than a static screenshot.
- **FAQ:**
  - How does AI coding analytics handle developers with multiple machines?
  - What happens to AI session data when developers are offline?
- **Links to:** /ai-coding-analytics, /features, /integrations, /blog/personal-claude-code-usage-stats (2.4, Workspace in depth), /blog/claude-code-activity-log (2.9)
- **Watch-outs:** Kite Pulse does not mark which lines of code an AI wrote, and session records are not a licence or provenance record: say so plainly (R9) in the "tracking AI-generated code" section, and point to code-host features for line-level attribution without naming capabilities you have not checked. MSoT 1.4 for Workspace states and My Projects actions; 1.1 for one repository on several machines, renamed or reinstalled computers keeping their identity, offline catch-up and "nothing uploads before consent". Do not imply the record is a performance file or reaches a manager in any particular form; managers see the developer's report without private prompt fields (MSoT 1.4). Overlaps 2.4 (Workspace as a feature): keep this page to the credit outcome and link to 2.4.

### 4.2 · How to Use Claude Code Better: a Personal Top 3

- **Category · intent · page type:** Benefits for Individual Developers · Informational · Interactive guide
- **Section:** Guides & tools
- **Plan title:** Get Better Privately: a Top 3 to Try, with the Evidence
- **Title tag:** How to Use Claude Code Better: 6 Steps | Kite Pulse
- **H1:** How to Use Claude Code Better: Find Your Own Top 3 from Your Last Two Weeks of Sessions
- **URL:** /how-to-use-claude-code-better
- **Meta description:** How to use Claude Code better from your own sessions: six steps to find repeated failures, loops and habits, then a personal top 3 to try next week.
- **Main keyword:** how to use claude code better
- **Secondary keywords:**
  - tips to use claude code better → H2 "Why generic tips to use Claude Code better stop working" (intro section before step 1)
  - improve claude code workflow → H2 of step 4 "Improve your Claude Code workflow where it repeats"
  - claude code tips for developers → body of the intro, and the final checklist's heading "Claude Code tips for developers, from your own data"
  - dev scorecard → H2 of step 6 "Turn the evidence into a dev scorecard of three" (developer scorecard is the main keyword of 2.5: link)
  - my ai coding stats → body of step 1 (main keyword of 4.8: link)
  - personal claude code usage stats → body of step 5 on plan usage (main keyword of 2.4: link)
- **Description:** For developers who have read the tip lists and want to know which advice applies to them. Every ranking page is a generic list (plan first, keep a CLAUDE.md, scope tasks small); none starts from the reader's own sessions or admits when there is too little to go on. The guide has six steps, each with a hands-on tool the reader uses on their own Claude Code history or on a labelled sample: (1) pull your last two weeks of sessions and their lengths; (2) find commands that failed more than twice; (3) find sessions that went in circles; (4) spot prompts and workflows you repeat; (5) check how close you ran to your Claude plan windows; (6) pick three changes, each with its evidence, and mark anything with too few sessions as "not enough data". The Kite Pulse callout sits at step 6, where doing this by hand every week stops scaling: My Scorecard & Insights does it continuously, leads with a Top 3 to act on, gives each a verdict, why it matters, what to try and the evidence, and says "not enough data" instead of guessing. The reader leaves with a copyable personal checklist of three changes and the evidence for each.
- **Interactive elements:**
  1. Failure counter (step 2) - the reader pastes a list of commands with exit codes from a session, or loads a labelled sample, and gets the commands that failed more than twice, grouped. Runs in the browser; nothing is sent. Fallback paragraph explains how to find the same thing in a session's history by hand.
  2. Loop spotter (step 3) - a sample session timeline (labelled) where the same edit-test-fail cycle repeats; the reader marks where they would have stopped and sees how many turns the loop took after that point. Fallback paragraph describes the signs of a loop.
  3. Top 3 builder (step 6) - the reader enters candidate changes with the evidence count behind each; any item with fewer sessions than a threshold the reader sets is labelled "not enough data", and the rest become a copyable checklist. Fallback is the checklist template in plain text.
- **Images / video (optional):** None - each step's tool works on the reader's own data.
- **FAQ:**
  - Can my manager see everything I type to the AI?
- **Links to:** /features, /privacy, /blog/developer-scorecard (2.5), /blog/personal-claude-code-usage-stats (2.4), /blog/claude-code-session-analysis (built), /blog/avoid-hitting-claude-limit (built), /claude-code-usage-limits
- **Watch-outs:** Facts about Claude Code itself (plan mode, CLAUDE.md, where the session history lives on disk) need a source URL from Anthropic's docs and a checked date in the page's data file (R2); where unverified, write a placeholder. The FAQ answer must be exact: prompt statistics are shown only to the developer and removed by the server for everyone else (MSoT 1.4), and the developer's page seen by a manager omits private prompt fields; do not say managers never see any session content, since admins can see prompt text on Workflows & Pain Points (Field Guide). The verification signal needs AI labelling and is not in MSoT Section 1: leave it out of this guide (it is 4.7's subject). Step 5 is Claude Code only (R7). Generic tips are allowed only as context; the guide's value is the reader's own evidence. Overlaps 2.5 (the scorecard as a feature): this page is the method, 2.5 is the page.

### 4.3 · Deep Work Sessions for Developers: See Your Rhythm

- **Category · intent · page type:** Benefits for Individual Developers · Informational · Blog post
- **Plan title:** See Your Own Working Rhythm Clearly
- **Title tag:** Deep Work Sessions for Developers, Measured | Kite Pulse
- **H1:** Deep Work Sessions for Developers: What Your Own AI Coding Rhythm Looks Like
- **URL:** /blog/deep-work-sessions-developer
- **Meta description:** Deep work sessions for developers, measured from your own AI coding history: deep sessions, streaks, peak hour and short bursts, visible only to you.
- **Main keyword:** deep work sessions developer
- **Secondary keywords:**
  - coding streak → H2 "Your longest coding streak, and what breaks it"
  - coding streak app → body of the same H2, with an honest note that dedicated streak and time-tracking apps exist and link to /compare/wakatime
  - developer activity heatmap → H3 "Reading your week as a heatmap" (also a secondary of 2.6: keep this to deep work, link to 2.6)
  - my ai coding stats → body of the closing section (main keyword of 4.8: link)
- **Description:** For developers curious whether they get long, uninterrupted stretches of work or spend the day in fragments. Pages ranking for this keyword are productivity essays on deep work in general; none shows how to read it from the sessions your AI tools already record. The page defines the work-pattern facts one by one (a deep session is 60 minutes or more, a short burst is under 15 minutes, peak hour, busiest day, longest streak, most sessions running at once), shows what each says and does not say about focus, then covers working style briefly with a link to 2.6. One Kite Pulse callout at the definitions: these facts come from session history, no timer to start, and the prompt statistics beside them are shown only to you. The reader leaves knowing their own deep-session share and one thing to try to protect it.
- **Interactive elements:**
  1. Sample week heatmap with a deep-work lens - an hour-by-weekday grid of sample sessions (labelled sample data); a switch highlights only sessions of 60 minutes or more, another only short bursts, and the summary line updates (deep sessions, short-burst share). Fallback paragraph defines both thresholds.
  2. "Fragment my day" slider - the reader adds meetings to a sample day and watches deep sessions split into short bursts. Labelled "illustration". Fallback sentence explains the effect.
- **Images / video (optional):** None - the heatmap carries the idea.
- **FAQ:**
  - Can my manager see everything I type to the AI?
- **Links to:** /features, /privacy, /blog/developer-working-style (2.6), /compare/wakatime
- **Watch-outs:** Thresholds and definitions from MSoT 1.4 "Work-pattern facts" exactly: deep sessions 60 minutes or more, short bursts under 15 minutes, busiest day is the weekday with the most commits. The day-by-hour heatmap in the console is on Activity Overview (Field Guide), and MSoT 1.4 lists My Activity as "when, how long, which tools": describe the reader's own view as My Activity and keep the heatmap as the page's sample illustration unless Activity Overview's own view is confirmed for developers. Do not claim a deep-session figure for focus or productivity in general (R2); no study figures without a source. Do not frame streaks as targets to hit; R4 applies. Overlaps 2.6 heavily: this page is the deep-work angle only.

### 4.5 · Claude Code Agent Stuck: Catch It in Half an Hour

- **Category · intent · page type:** Benefits for Individual Developers · Informational · Blog post
- **Plan title:** Catch a Stuck Agent in Half an Hour, Not at the End of the Day
- **Title tag:** Claude Code Agent Stuck? Catch It Early | Kite Pulse
- **H1:** Claude Code Agent Stuck? How to Catch It Early Instead of at the End of the Day
- **URL:** /blog/claude-code-agent-stuck
- **Meta description:** Claude Code agent stuck on the same step? How to tell, what the stuck stretch looks like step by step, and how to get a notice instead of finding out late.
- **Main keyword:** claude code agent stuck
- **Secondary keywords:**
  - claude code stuck in loop → H2 "When Claude Code is stuck in a loop: the signs" (main keyword of 3.14: link)
  - ai agent stuck in loop → body of the same H2, one paragraph on loops in any agent (main keyword of 7.6: link)
  - ai agent stuck → H2 "Getting told when an AI agent is stuck" (main keyword of 11.4: link)
- **Description:** For developers who start an agent, switch to something else and come back to find it has spent the afternoon on one failing step. Ranking pages are troubleshooting threads about the terminal freezing or a hung process; few cover the agent that keeps working but makes no progress. The page separates the two (hung versus looping), lists the signs of a loop in a session's history (the same command failing, the same file edited back and forth), shows how to read the stuck stretch step by step, and ends with what to change in the request. One Kite Pulse callout at the "getting told" section: a notice names the project when an agent has been stuck on the same problem, and "What the agent did" shows the stretch without message text. The reader leaves able to spot a loop in their own history and with three ways to restart it better.
- **Interactive elements:**
  1. Hung or looping? - the reader answers three questions about what they see (is the terminal still printing, are the same commands repeating, are files changing) and gets "hung", "looping" or "working slowly" with the next step for each. Fallback is the same decision as a short table.
  2. Stuck-stretch reader - a sample step list (labelled sample data) where routine steps are folded and a run of six identical failed test commands is highlighted; the reader expands it and sees where a person would have stepped in. Fallback paragraph describes the pattern.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I know when AI is retrying the same failed fix repeatedly?
  - How do I spot developers who are stuck in long AI sessions?
- **Links to:** /blog/ai-retry-loops, /integrations/claude-code, /ai-agent-office, /blog/is-claude-code-stuck (built), /blog/stuck-ai-agent (built), /blog/ai-agent-stuck-notification (2.10)
- **Watch-outs:** The stuck notice, its 30-minute interval and "What the agent did" are Field Guide only (28 Oct), not MSoT Section 1: confirm before writing, and leave the 30-minute figure out until confirmed (as in 2.10). Verified and usable: Work Problems finds failed commands and repeated retries (MSoT 1.2, admin by default) and The Office shows markers for stuck work (1.4). The second FAQ is a manager's question on a developer's page: answer it briefly and link to /blog/stuck-ai-agent and /ai-agent-office. Claude Code waiting signals are unreleased (MSoT 2.3): do not describe "waiting for you". Built pages /blog/is-claude-code-stuck and /blog/stuck-ai-agent cover close ground: this page is the developer catching their own agent; check both before writing and avoid repeating their sections. Facts about Claude Code's own behaviour need a source and checked date (R2).

### 4.7 · How Often Developers Correct AI: Your Own Signal

- **Category · intent · page type:** Benefits for Individual Developers · Commercial · Blog post
- **Plan title:** Are You Checking What the AI Writes? A Private Verification Signal
- **Title tag:** How Often Developers Correct AI, Measured | Kite Pulse
- **H1:** How Often Developers Correct AI Output, and How to See Your Own Checking Habit
- **URL:** /blog/how-often-developers-correct-ai
- **Meta description:** How often developers correct AI output, measured from your own sessions: how often you reviewed or tested the AI's work, kept private to you.
- **Main keyword:** how often developers correct ai
- **Secondary keywords:**
  - human ai collaboration → H2 "Checking is the human half of human-AI collaboration"
  - ai code acceptance rate → H2 "Why an AI code acceptance rate is not the same thing" (what acceptance rates measure, and what they miss)
  - ai collaboration metrics → body of the closing section on team-level measures (main keyword of 8.12: link)
- **Description:** For developers who rely heavily on AI edits and suspect their checking has slipped. Ranking pages report survey figures on trust in AI code and vendor acceptance rates; none gives a developer a read on their own habit. The page explains what counts as checking (running tests, reviewing a diff, correcting the AI's change), why acceptance rate measures something else (whether a suggestion was taken, not whether it was checked), then shows a private verification signal: how often you reviewed or tested the AI's output, with counts of checks and corrections. One Kite Pulse callout at that section, with the condition stated in it: the signal needs AI labelling, which an admin sets up. A closing section notes that team-level measures (AI Collaboration) are pooled, never per person. The reader leaves with one rule of thumb for when to check.
- **Interactive elements:**
  1. Session checker - three short sample sessions (labelled sample data), each a list of steps; the reader marks which steps are checks (a test run, a diff review, a correction) and sees a count per session, with the console's own labels revealed after. Fallback paragraph lists what counts as a check.
  2. Acceptance versus checking - a sample of ten AI suggestions (labelled) with two counters: accepted, and accepted after a test or review; the reader toggles items and sees the two numbers diverge. Fallback sentence explains the difference.
- **Images / video (optional):** None.
- **FAQ:**
  - (No FAQ in the brief. Suggested, drawn from the page: "Who can see my verification signal?" and "Does Kite Pulse measure AI code acceptance rate?" - confirm with the keyword owner before adding.)
- **Links to:** /engineering-intelligence, /features, /privacy, /blog/developer-scorecard (2.5), /compare/github-copilot-metrics
- **Watch-outs:** The verification signal is Field Guide only (developer report export) and needs AI labelling (Article Plan): not in MSoT Section 1, so confirm before writing and state the AI labelling condition (MSoT 1.5: OpenRouter key, monthly budget, approved label list). Who sees it is unconfirmed: the plan calls it private, but the Field Guide lists it in the developer report export; do not write "only you see it" until checked. Kite Pulse does not collect inline completions (R5), so it has no acceptance rate: say so in the acceptance section (R9) and link to /compare/github-copilot-metrics for vendor acceptance figures. Survey figures on trust in AI code need a source and checked date (R2). AI Collaboration is admin by default (MSoT 1.4). R4: no ranking framing.

### 4.8 · My AI Coding Stats Across Every Tool, in One Place

- **Category · intent · page type:** Benefits for Individual Developers · Commercial · Blog post
- **Plan title:** One Place for All Your AI Work, Whichever Tool You Used
- **Title tag:** My AI Coding Stats Across Every Tool | Kite Pulse
- **H1:** My AI Coding Stats: All Your AI Work in One Place, Whichever Tool You Used
- **URL:** /blog/my-ai-coding-stats
- **Meta description:** My AI coding stats from Claude Code, Cursor, Codex and seven more tools in one timeline, under the right project, filtered by tool, model or session.
- **Main keyword:** my ai coding stats
- **Secondary keywords:**
  - personal claude code usage stats → H3 "Personal Claude Code usage stats, including plan figures" (main keyword of 2.4: link)
  - model usage by developer → H2 "Which models you used, by tool and project"
  - track ai coding tool usage → body of H2 "Ten tools, one timeline" (main keyword of 10.1, merged into /integrations: link)
  - team usage tracking claude code codex opencode → H3 "When the team uses Claude Code, Codex and OpenCode together" (short paragraph, link to /blog/codex-gemini-cli-team-usage)
- **Description:** For developers who use more than one AI coding tool and have their history scattered across each tool's own records. Pages ranking for personal stats are single-tool usage counters (mostly Claude Code token trackers); none puts a morning in Claude Code and an afternoon in Cursor on one timeline under the same project. The page walks through a two-tool day, what each tool records (the MSoT 1.1 table, condensed: tokens, model names, cost only where priced), how sessions land under the right project, and the filters on My Sessions (tool, model, session type). One Kite Pulse callout at "Ten tools, one timeline": all ten are collected out of the box and linked to the project by repository address. The reader leaves knowing which of their tools are covered and what each one reports.
- **Interactive elements:**
  1. Two-tool day - a sample day (labelled sample data) of Claude Code and Cursor sessions on two projects; the reader filters by tool, model or project and the timeline and totals update, with Cursor's model shown only where one model served the whole chat. Fallback paragraph explains the merge by project.
  2. "What does my tool report?" picker - the reader ticks the tools they use and sees, per tool, conversations, tokens, model name and cost shown (from the MSoT 1.1 table), including "—" for unpriced tools. Fallback is the same table.
- **Images / video (optional):** None.
- **FAQ:**
  - Which AI coding tools does Kite Pulse support?
  - Which AI coding tools can be tracked in one platform?
  - Is there one tool that tracks Claude Code, Cursor and GitHub Copilot together?
- **Links to:** /features, /integrations, /integrations/claude-code, /integrations/cursor, /blog/codex-gemini-cli-team-usage (built), /blog/cline-aider-roo-code-analytics (built), /blog/personal-claude-code-usage-stats (2.4)
- **Watch-outs:** R5 exactly: ten tools, "GitHub Copilot Chat in VS Code", no inline completions, JetBrains or Copilot CLI; the third FAQ answer must say this. R7: cost shows for Claude and Gemini models and for the five tools that report their own; Codex, Cursor and Copilot usually "—", never $0, and never a total across tools. Cursor and Copilot report input and output tokens only. The Models tab (MSoT 1.2) is on Team AI Usage for managers and admins; the developer's own view is My Sessions filters and My Activity: do not imply developers see a Models tab. Session-type filter is in the Article Plan and the 2.7 entry: confirm the label in the console.

### 4.9 · Claude Code Daily Summary: What You Left Open

- **Category · intent · page type:** Benefits for Individual Developers · Commercial · Blog post
- **Plan title:** End the Day Knowing What You Left Open
- **Title tag:** Claude Code Daily Summary: What You Left Open | Kite Pulse
- **H1:** A Claude Code Daily Summary: End the Day Knowing What You Started, Finished and Left Open
- **URL:** /blog/claude-code-daily-summary
- **Meta description:** A Claude Code daily summary of what you worked on, finished, left open and got stuck on, built from your sessions and visible only to you.
- **Main keyword:** claude code daily summary
- **Secondary keywords:**
  - claude code daily report → H2 "A daily report you do not have to write"
  - claude code daily brief → H3 "Tomorrow's brief: start from what you left open"
- **Description:** For developers juggling several threads who lose track of what is half done. Ranking pages are scripts and prompts that ask Claude to summarise a day's git log; none builds the summary from the sessions themselves or keeps it private. The page shows the parts of a useful end-of-day summary (worked on, started, finished, left open, stuck on, learned), how to make one by hand from a day's sessions, and where that gets tedious. The Kite Pulse callout sits there: My Day lays these out from your labelled sessions, visible only to you, with the AI labelling condition stated. A short closing section shows how to turn "left open" into tomorrow's first task. The reader leaves with a copyable end-of-day template whether or not they use Kite Pulse.
- **Interactive elements:**
  1. Day sorter - six sample sessions from one day (labelled sample data) with one-line summaries; the reader drags each into worked on, finished, left open or stuck, and a copyable summary forms. Fallback is the template in plain text.
  2. Tomorrow's brief - from the sorted sample, the "left open" items become a three-line brief with the project and the last step; the reader can edit and copy it. Fallback sentence describes the idea.
- **Images / video (optional):** None.
- **FAQ:**
  - (No FAQ in the brief. Suggested: "Who can see my daily summary?" and "Does a daily summary need an AI service?" - confirm with the keyword owner before adding.)
- **Links to:** /features, /privacy, /blog/search-past-ai-coding-sessions (2.7), /blog/claude-code-session-replay (2.8)
- **Watch-outs:** My Day is Field Guide only ("New", AI labelling) and is not in MSoT Section 1: confirm it is visible in the console before writing; if it is not, rebuild the page on My Sessions' per-session summaries (MSoT 1.4) and drop the callout. If it is, state the AI labelling condition (MSoT 1.5) and "visible only to you" only once confirmed. It covers all ten tools, not Claude Code only: say so once, since the keyword is Claude Code-specific. Do not confuse it with the admin daily digest email (alerts, MSoT 1.6). Scripts that summarise a git log with Claude are a fair alternative (R9): mention them.

### 4.10 · Async Standup Tool: No Timesheets, No Status Updates

- **Category · intent · page type:** Benefits for Individual Developers · Commercial · Blog post
- **Plan title:** No Timesheets, No Status Updates
- **Title tag:** Async Standup Tool With No Form to Fill | Kite Pulse
- **H1:** An Async Standup Tool with No Form to Fill: Status from Work Already Happening
- **URL:** /blog/async-standup-tool
- **Meta description:** An async standup tool where nobody writes an update: your team's status comes from AI coding sessions already happening. What it shows and what it can't.
- **Main keyword:** async standup tool
- **Secondary keywords:**
  - async daily standup → H2 "What an async daily standup is for"
  - daily standup alternatives → H2 "Daily standup alternatives, compared by who does the writing"
  - team status dashboard → body of H2 "What your team sees instead of your update" (main keyword of 5.1: link)
  - what is my team working on dashboard → body of the same H2 (main keyword of 2.11: link)
  - live view of ai coding agents → H3 "The Office: a live view of AI coding agents" (main keyword of 9.4: link to /ai-agent-office)
- **Description:** For developers tired of writing the same update in a standup bot, a timesheet and a ticket. Every ranking page is a roundup of standup bots (Geekbot, DailyBot, Steady, Range and others), all of which still ask a person to write. The page starts with what a standup is meant to answer (what I did, what I am doing, where I am stuck), compares alternatives by who does the writing (the person, a bot prompting the person, or the work itself), then shows which of those questions session activity can answer and which it cannot (plans, priorities and blockers outside the AI session still need words). One Kite Pulse callout: capture runs in the background, and The Office and Team Overview show work in motion. The reader leaves knowing which part of their standup could stop being written.
- **Interactive elements:**
  1. Standup question sorter - the three standup questions plus "plans for tomorrow" and "blocked by another team"; for each, the reader sees which approach answers it without anyone writing, with Kite Pulse marked partial where it is. Fallback is the same table.
  2. Sample morning view - a sample team of five (labelled sample data) shown as The Office desks, with the colleague-versus-manager switch: colleagues see name, team, tool and presence; the manager also sees project and current state. Fallback paragraph describes the two views.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I see what my team is working on without status meetings?
  - How do I know what my engineering team is working on right now?
- **Links to:** /features, /ai-agent-office, /privacy, /blog/what-is-my-team-working-on (2.11), /blog/stuck-ai-agent (built)
- **Watch-outs:** Kite Pulse is a partial alternative, not a standup bot (keyword note): say plainly what still needs a person (R9), and name the bot vendors only as a category or with a checked source (R2). Team Overview is for managers and admins (MSoT 1.4); a developer sees The Office, with detail only for people in their scope: do not imply a developer sees teammates' projects. Team Overview lists "Most active today" (R4): never write that Kite Pulse does not rank people, and avoid any monitoring framing. Timesheets: Kite Pulse does not produce timesheets or billable hours; do not imply it replaces one, only that status reporting needs less writing.

### 4.13 · Claude Code Version Check: Stay on a Current Build

- **Category · intent · page type:** Benefits for Individual Developers · Informational · Blog post
- **Plan title:** Stay on a Current Claude Code Without Watching Release Notes
- **Title tag:** Claude Code Version Check: Stay Current | Kite Pulse
- **H1:** Claude Code Version Check: How to Know You Are Behind Without Watching Release Notes
- **URL:** /blog/claude-code-version-check
- **Meta description:** A Claude Code version check: how to see your installed version, compare it with the latest release and know when you are behind, alone or as a team.
- **Main keyword:** claude code version check
- **Secondary keywords:**
  - claude code monitoring → H2 "Claude Code monitoring for a team: versions alongside usage"
  - claude code usage monitor → body of the same H2, an honest note that open-source usage monitors exist for one person and link to /compare/ccusage
- **Description:** For developers using Claude Code, and the leads who support them. Ranking pages show the version command and the update command; none covers knowing you are behind without checking by hand, or seeing a whole team's versions. The page covers the check for one person (the command, where the latest release is announced, how to update), why falling behind matters (fixes and features the team assumes everyone has), then the team view. One Kite Pulse callout at the team section: each developer's Claude Code version is compared with the latest release and shown as Latest, Recent or Behind, with a "version behind" filter. The reader leaves with the two commands and a one-line team routine.
- **Interactive elements:**
  1. Version comparer - the reader pastes their version output and sees whether it is the latest recorded release, a few releases behind or further; the "latest" value lives in the page's data file with a checked date and is labelled as such. Fallback paragraph gives the commands and where to look.
  2. Sample team versions - a sample team of eight (labelled sample data) with versions; a "version behind" filter shows who is Behind, and a toggle groups by Latest, Recent and Behind. Fallback sentence explains the three groups.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I find out if developers are on outdated versions of Claude Code?
- **Links to:** /plan-headroom, /integrations/claude-code, /compare/ccusage, /blog/ai-agent-stuck-notification (2.10)
- **Watch-outs:** Verified (MSoT 1.2, 1.4): the version check on Team AI Usage with a "version behind" filter, and Latest, Recent or Behind per developer, which are manager and admin views. The developer's own "Claude Code out of date" notice is Field Guide only: confirm before describing it (as in 2.10). Do not confuse it with Team Overview's "old app version", which is the Kite Pulse desktop program. Claude Code's version and update commands and its release channel need a source and checked date (R2). The latest version number in the comparer must be dated and never presented as live. The usage-monitor note: name ccusage via /compare/ccusage; any other tool needs a checked source.

### 5.1 · Team Status Dashboard: Stand-ups From Facts

- **Category · intent · page type:** Benefits for Teams and Managers · Commercial · Blog post
- **Plan title:** Stand-ups That Start from Facts, Not Round-the-Room Updates
- **Title tag:** Team Status Dashboard: Stand-ups From Facts | Kite Pulse
- **H1:** Team Status Dashboard: Start the Stand-up from Facts, Not Round-the-Room Updates
- **URL:** /blog/team-status-dashboard
- **Meta description:** A team status dashboard built from AI coding sessions shows who is online, coding or needs help before the stand-up, so the meeting goes on problems.
- **Main keyword:** team status dashboard
- **Secondary keywords:**
  - team availability dashboard → H2 "A team availability dashboard nobody has to update" (Team Overview's online and coding status, with Leave & On-Call so a day off reads as a day off)
  - see what ai agents are doing right now → body of H2 "Five minutes before the stand-up" (main keyword of the built /blog/stuck-ai-agent: link)
  - live view of ai coding agents → H3 "The Office: a live view of AI coding agents" (main keyword of 9.4: secondary here, link to /ai-agent-office)
  - what is my team working on dashboard → body of H2 "Each person's current project" (main keyword of 2.11: link)
- **Description:** For team leads whose stand-up is mostly people taking turns to say what they did. Pages ranking for this keyword are project-tool templates where each person sets their own status; none fills the status from the work itself. The reader moves from why round-the-room updates eat the meeting, to what a lead can read before it starts (who is online, who is coding now, active time today against a typical day, who needs attention and why, each person's current project), to a three-question stand-up that starts from that list. One Kite Pulse callout at "Five minutes before the stand-up": Team Overview fills these from the sessions, refreshes every 30 seconds and can show past days. The reader leaves with a copyable stand-up format.
- **Interactive elements:**
  1. Stand-up agenda builder - a sample Team Overview (labelled sample data, invented names) with six people; the reader ticks the rows worth raising (needs attention, failing uploads, two people on one project, someone on leave) and gets a copyable three-item agenda. Fallback paragraph lists the same signals and the agenda format in words.
  2. Meeting-time calculator - the reader enters team size and minutes per spoken update and sees the minutes a round-the-room format spends on updates, against a facts-first format where only flagged items are discussed. Every number is the reader's own input. Fallback paragraph gives the arithmetic.
- **Images / video (optional):** None - the sample Team Overview shows the page; a real screenshot must come from a deployment (MSoT 2.5).
- **FAQ:**
  - How do I see what my team is working on without status meetings?
  - How can I see team activity in real time?
  - How do I know what my engineering team is working on right now?
- **Links to:** /features, /ai-agent-office, /engineering-intelligence, /blog/what-is-my-team-working-on, /blog/stuck-ai-agent (built)
- **Watch-outs:** Verified (MSoT 1.4): Team Overview shows who is online and coding now, active time and sessions today against a typical day, who needs attention (failing uploads, backlog, old app version) and each person's current project, refreshing every 30 seconds; Leave & On-Call; The Office with markers for stuck work or plan limits, detail only within scope. "Stuck" as a live state and The Office's push updates are Field Guide only: keep the stuck marker as MSoT words it. Team Overview lists "Most active today" (R4): do not write that it never ranks people. Claude Code waiting signals are unreleased (MSoT 2.3). Overlaps 2.11 and 11.1 (stand-up workflow): keep this to the benefit, link both.

### 5.2 · Claude Code: See What It's Doing, Step by Step

- **Category · intent · page type:** Benefits for Teams and Managers · Informational · Blog post
- **Plan title:** Help a Stuck Developer Without Reading Their Conversation
- **Title tag:** Claude Code: See What It's Doing, Step by Step | Kite Pulse
- **H1:** Claude Code: See What It's Doing, and Help a Stuck Developer Without Reading the Chat
- **URL:** /blog/claude-code-see-what-its-doing
- **Meta description:** Claude Code: see what it's doing, step by step. Tools, commands and errors in order, so a lead can help a stuck developer without reading the chat.
- **Main keyword:** claude code see what it's doing
- **Secondary keywords:**
  - claude code show what it's doing → H2 "What Claude Code shows on your own screen"
  - claude code tool calls → H2 "Reading the tool calls instead of the messages"
  - claude code stuck thinking → H3 "Stuck thinking, or stuck repeating?"
  - cursor agent getting stuck → H3 "When a Cursor agent is getting stuck" (failed tool calls are recorded for Cursor too)
  - ai agent stuck notification → body of H2 "When someone else needs to know" (main keyword of 2.10: link)
  - developer analytics without source code access → body of H2 "What the helper sees, and what stays private", linking to the built page /blog/developer-analytics-without-source-code
  - track token usage without collecting prompts → one sentence in the same H2 on counts-only mode, linking to the built page /blog/track-token-usage-without-prompts
- **Description:** The searcher is usually the developer, so the page teaches first. Ranking pages are general Claude Code explainers that only hint at watching its steps; none shows a structured record of tools, commands and errors that a second person can read without the conversation. The reader goes from what Claude Code shows in the terminal while it works, to where that stops (it is on one screen and gone when the session closes), to telling "thinking" from "repeating the same failing step", to a record of the session that a lead can read with the developer. One Kite Pulse callout at "Reading the tool calls": a session's steps, failed tool calls and command exit codes, kept on the team's own server. The reader leaves able to tell a slow agent from a stuck one.
- **Interactive elements:**
  1. Session step viewer - a sample session of about 20 steps (labelled sample data); a "fold routine steps" switch hides successful reads and edits while errors stay visible; a "show message text" switch is greyed out with a note that the record has no message text. Fallback paragraph describes the same session in words.
  2. "Thinking or repeating?" check - the reader answers three questions about a session in front of them (same command again? same file edited again? same error again?) and gets which kind of stuck it is and one thing to try. Fallback is the three questions with their answers as a list.
- **Images / video (optional):** Optional short screen recording of Claude Code's own terminal output during a task, only if recorded from a real session with nothing private in it; the step viewer otherwise covers it.
- **FAQ:**
  - How do I spot developers who are stuck in long AI sessions?
  - How do I identify developers who need support or coaching with AI tools?
  - Can managers see developers' AI prompts?
  - How can managers spot struggling developers early without surveys?
- **Links to:** /blog/ai-retry-loops, /privacy, /engineering-intelligence, /ai-agent-office, /blog/claude-code-activity-log, /blog/is-claude-code-stuck (built)
- **Watch-outs:** "What the agent did", the manager receiving the stuck notice and the 30-minute threshold are Field Guide only: confirm before writing; until then describe My Sessions' detailed view (MSoT 1.4) and Work Problems (failed commands, retries; admin by default, MSoT 1.2). MSoT 1.1: failed tool calls for every tool except Aider; command exit codes from Claude Code, Codex and Copilot only, so the Cursor H3 must not promise exit codes. What Claude Code itself shows (terminal output, any transcript or verbose view) is an outside fact: source URL and checked date in the data file. FAQ "Can managers see prompts?": verified that private prompt statistics are removed for everyone else and the developer page omits private fields; Workflows & Pain Points shows prompt text to admins (Field Guide), so do not write "managers can never read prompts" without confirming. The coaching FAQ must not turn into ranking (R4). Overlaps 2.9, /blog/stuck-ai-agent (3.1, built), 3.14 and 4.5: keep this one to "help without reading".

### 5.5 · Recurring Engineering Blockers: Fix the System

- **Category · intent · page type:** Benefits for Teams and Managers · Commercial · Blog post
- **Plan title:** Fix the System, Not the Person
- **Title tag:** Recurring Engineering Blockers: Fix the System | Kite Pulse
- **H1:** Recurring Engineering Blockers: Fix the System, Not the Person
- **URL:** /blog/recurring-engineering-blockers
- **Meta description:** Recurring engineering blockers hide in AI sessions as failing commands and retries. Group them by cause, fix the shared setup and stop blaming people.
- **Main keyword:** recurring engineering blockers
- **Secondary keywords:**
  - blocker board engineering → H2 "A blocker board for engineering, built from causes" (main keyword of 8.11: link)
  - failing commands analytics → H2 "Failing commands analytics: the evidence under each blocker" (main keyword of 2.14: link)
  - developer friction → H3 "Friction that belongs to the setup" (main keyword of 12.9: link)
  - developer pain points → body of H2 "What to fix first" (main keyword of 2.15: link)
- **Description:** For team leads and platform owners who keep hearing about the same broken build in different meetings. Ranking pages give generic advice on removing blockers; none starts from evidence of the same failure hitting several people. The reader learns to tell a shared cause (one error across people or projects) from one person's task, to group failures by cause rather than by who hit them, to attach a suggested action, and to pick what to fix first. One Kite Pulse callout at the failing-commands section: Work Problems finds failed commands, error messages and repeated retries with fixed rules, no AI, grouped by severity with suggested actions. The reader leaves with a blocker card format they can use in any tracker.
- **Interactive elements:**
  1. Cause-or-person sorter - eight sample issues (labelled sample data); the reader sorts each into "shared cause" or "one person's task", then the page shows the rule it used (same error for two or more people or projects means a shared cause). Fallback paragraph gives the rule and two worked examples.
  2. Blocker card builder - the reader enters a recurring problem, how often it happened and which teams or roles it affects (no names) and gets a copyable card: cause, evidence, suggested action, owning team. Fallback shows the card format as plain text.
- **Images / video (optional):** None - the sorter and the card show the idea.
- **FAQ:**
  - How do I stop my team solving the same bug twice?
  - How do I know when AI is retrying the same failed fix repeatedly?
- **Links to:** /engineering-intelligence, /features, /blog/developer-experience-metrics, /privacy, /blog/failing-commands-analytics, /blog/ai-retry-loops
- **Watch-outs:** Work Problems is admin by default (MSoT 1.2) and lists "the most affected developers", so "never names a person" applies to the Blocker Board only (MSoT 1.4: "never a single person"). Blocker Board, Workflows & Pain Points are admin by default; admins can grant them to managers. That the Blocker Board needs AI labelling and suggestion rules is Field Guide and Article Plan, not MSoT: say "needs AI labelling" only once confirmed. First FAQ can point to knowledge records (MSoT 1.5, needs AI labelling) and /blog/institutional-knowledge. Overlaps 7.7 and 8.11: keep this to the benefit for a lead.

### 5.6 · Duplication of Work in Software Teams

- **Category · intent · page type:** Benefits for Teams and Managers · Informational · Blog post
- **Plan title:** Stop Two People Building the Same Thing
- **Title tag:** Duplication of Work in Software Teams | Kite Pulse
- **H1:** Duplication of Work: How Two Developers End Up Building the Same Thing, and How to See It Early
- **URL:** /blog/duplication-of-work
- **Meta description:** Duplication of work in software teams: why two people build the same thing with AI, a worked example, and how shared-project views catch it early.
- **Main keyword:** duplication of work
- **Secondary keywords:**
  - duplicated efforts → H2 "Why duplicated efforts grow when work happens in AI sessions"
  - duplication of work example → H2 "A duplication of work example: two branches, one feature" (an illustration, labelled)
  - what is my team working on dashboard → body of H2 "Seeing overlap while it is still cheap" (main keyword of 2.11: link)
  - engineering resource allocation → H3 "Moving one of them" (main keyword of 11.9: link)
  - project health dashboard → body of the same H2 (main keyword of 2.16: link)
- **Description:** Weak-fit keyword, so the page teaches first. Ranking pages are general management posts and dictionary results; none is about software teams or uses evidence of who is working where. The reader goes from why duplication is easier now (an AI agent builds a working version in an afternoon, so nobody asks first), to a worked example of two developers on one feature, to three early signals (two people in the same project, the same files, the same task words), to what a lead does about it. One Kite Pulse callout at "Seeing overlap": Collaboration lists projects several people work on, with contributors, shared sessions and last activity. The reader leaves with a weekly overlap check.
- **Interactive elements:**
  1. Overlap finder - a sample grid of people and projects for one week (labelled sample data); the reader sets "two or more people in the same project" or "same files touched" and overlapping cells light up with what they share. Fallback paragraph describes the example overlap in words.
  2. Early-catch checklist - five yes/no questions about the team's habits (shared project list, who-is-on-what visible, a place to say "I am starting X") giving a short list of practices to add. Fallback is the checklist as a list.
- **Images / video (optional):** None - the grid shows the overlap.
- **FAQ:**
  - How do I stop my team solving the same bug twice?
  - How do I know what my engineering team is working on right now?
- **Links to:** /features, /engineering-intelligence, /blog/team-collaboration-insights, /blog/project-health-dashboard
- **Watch-outs:** Verified: Collaboration (MSoT 1.4: projects several people work on, contributors, shared sessions, last activity) and the project page summary card's "duplicate work" entry. "How much each person spent there" is Article Plan wording, not MSoT: confirm before showing time per person. The duplicate-work flag needing AI labelling comes from the Article Plan: confirm. Duplicate Detection is about folders that are the same repository, not people doing the same work: do not mix the two. The example's names and branches are illustrations.

### 5.7 · Project Status Tracking Dashboard, No Chasing

- **Category · intent · page type:** Benefits for Teams and Managers · Commercial · Blog post
- **Plan title:** Know Which Projects Are Alive Without Chasing Anyone
- **Title tag:** Project Status Tracking Dashboard, No Chasing | Kite Pulse
- **H1:** Project Status Tracking Dashboard: Know Which Projects Are Alive Without Chasing Anyone
- **URL:** /blog/project-status-tracking-dashboard
- **Meta description:** A project status tracking dashboard that reads activity, not updates: active, stable or dormant from real sessions, with contributors and last activity.
- **Main keyword:** project status tracking dashboard
- **Secondary keywords:**
  - project status tracking software → H2 "What project status tracking software needs from people"
  - project health status dashboard → H2 "Active, stable, dormant: a project health status dashboard from activity"
  - project health status report → H3 "From dashboard to a project health status report" (company report as CSV or PDF, or scheduled by email)
  - duplicate repository detection → H3 "One repository, counted once" (main keyword of 2.2: link)
  - engineering project tracking ai → body of H2 "Where the AI sessions come in"
- **Description:** For engineering managers who find out a project is dormant only when they ask. Ranking pages are PM vendors and RAG templates where someone types the status in; none derives it from the work. The reader compares a typed status with one read from activity, sees what each tells them, then reads a project list by health, contributors, sessions and last activity, and learns why one repository on two laptops must count once. One Kite Pulse callout at the health H2: All Projects shows every project's health (active, stable or dormant), sessions, contributors and last activity. An honest section says ticket tools still own planned scope and deadlines (R9). The reader leaves knowing which questions activity answers and which still need a person.
- **Interactive elements:**
  1. Status-from-activity demo - eight sample projects with last-activity dates and session counts (labelled sample data); the reader drags a "today" date and each project moves between active, stable and dormant using thresholds labelled "illustrative, not Kite Pulse's rule". Fallback paragraph explains the idea with two projects.
  2. Typed status vs activity - the reader picks a sample project and sees its typed status ("Green", last edited weeks ago) beside what its activity shows. Fallback is a small two-column table.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I know what my engineering team is working on right now?
  - How do I find out which projects my team uses AI on the most?
- **Links to:** /features, /engineering-intelligence, /blog/project-health-dashboard, /blog/duplicate-repository-detection
- **Watch-outs:** Verified (MSoT 1.4): All Projects health, sessions, contributors, last activity; Duplicate Detection; project page summary card. Open blockers and phase on the card need AI labelling per the Article Plan: confirm before using. The real active/stable/dormant thresholds are not in MSoT: never state numbers. Second FAQ answers from Team AI Usage's Projects tab and Models by project (MSoT 1.2). Company report downloads are admin by default; scheduled reports need email set up on the server (MSoT 2.1). Overlaps 2.16 and 7.10 ("project status tracking tool"): keep this to the dashboard benefit and link both.

### 5.8 · AI Session Success Rate: Is AI Work Improving?

- **Category · intent · page type:** Benefits for Teams and Managers · Commercial · Blog post
- **Plan title:** Is the Team's Work with AI Getting Better?
- **Title tag:** AI Session Success Rate: Is AI Work Improving? | Kite Pulse
- **H1:** AI Session Success Rate: Is the Team's Work with AI Getting Better?
- **URL:** /blog/ai-session-success-rate
- **Meta description:** AI session success rate, friction and checked changes, tracked by team over weeks: how to tell if work with AI is improving without ranking anyone.
- **Main keyword:** ai session success rate
- **Secondary keywords:**
  - ai code acceptance rate → H2 "Why AI code acceptance rate is not the whole story"
  - ai adoption metrics → H3 "Adoption first, then outcomes", linking to the built page /blog/ai-adoption-tracking
  - ai coding maturity model → H2 "A simple AI coding maturity model, read from team measures" (the reader's own stages, not a Kite Pulse feature)
- **Description:** For engineering managers asked whether AI is paying off. Ranking pages talk about acceptance rate for inline suggestions; none measures whether whole AI sessions finished what they set out to do. The reader learns what a session success rate is, why acceptance rate only covers completions, which three things to watch over weeks (sessions that succeeded, corrections and repeated context, AI changes that were checked), why to read them per team and never per person, and how to place a team on a simple maturity scale. One Kite Pulse callout at the success-rate H2: AI labelling tags whether each session succeeded, and Trends, Team Review and AI Collaboration show it over time. An honest section: these show how the work went, not productivity or ROI (R9). The reader leaves with three questions to bring to a monthly review.
- **Interactive elements:**
  1. Measure picker - the reader picks a question (are we finishing more? correcting the AI less? checking its changes?) and sees which measure answers it, that it is pooled per team, and that it needs AI labelling. Fallback is the same mapping as a table.
  2. Sample trend chart - a sample team over twelve weeks (labelled sample data) for success rate and corrections per 100 messages; a team-size switch shows the figure withheld when too few people are behind it. Fallback paragraph reads the chart in words.
- **Images / video (optional):** None - the chart is drawn from labelled sample data.
- **FAQ:**
  - Is using AI coding assistants actually making developers more productive?
  - How can I identify teams that need more AI training?
  - Which teams are getting the most value from AI coding tools?
- **Links to:** /engineering-intelligence, /blog/measure-developer-productivity-ai, /ai-coding-analytics, /blog/ai-adoption-tracking (built)
- **Watch-outs:** Verified (MSoT 1.5): AI labelling tags whether a session succeeded; it needs an OpenRouter key, a monthly budget above $0 and an approved, switched-on label list; answers below the confidence bar are stored as "unknown". Trends, Team Review and AI Collaboration are verified as page names (MSoT 1.4; the last two admin by default). Their measures (corrections and repeated context per 100 messages, AI changes checked, pooled, small groups withheld) are Field Guide only: confirm before naming them. Kite Pulse does not collect GitHub Copilot inline completions (R5), so do not imply it measures acceptance rate; the acceptance-rate section explains the term with an outside source and checked date in the data file. No ROI figure (MSoT 2.5). Organisation Overview has a "Top performers" panel (R4): do not write "never ranks". First FAQ answer must be honest that session data alone does not prove productivity.

### 5.9 · One on One Meeting Agenda Builder

- **Category · intent · page type:** Benefits for Teams and Managers · Informational · Interactive tool
- **Section:** Guides & tools
- **Plan title:** Better One-to-Ones from the Same Report the Developer Sees
- **Title tag:** One on One Meeting Agenda Builder for Engineers | Kite Pulse
- **H1:** One on One Meeting Agenda: Build It from the Report You Both See
- **URL:** /one-on-one-meeting-agenda
- **Meta description:** Build a one on one meeting agenda for an engineer from facts you both see: recent work, blockers and AI habits. Free builder and copyable template.
- **Main keyword:** one on one meeting agenda
- **Secondary keywords:**
  - one on one meeting template for managers → H2 "A one on one meeting template for managers, generated"
  - one on one questions for direct reports → H2 "One on one questions for direct reports, by topic"
  - developer scorecard → H3 "Starting from the developer's own scorecard" (main keyword of 2.5: link to /blog/developer-scorecard)
  - engineering manager dashboard → body of H2 "Where the shared facts come from" (main keyword of 9.12: link)
  - engineering manager developer productivity ai → body of the method section (main keyword of 10.10: link)
- **Description:** For engineering managers preparing a one-to-one. Ranking pages are templates and question lists that stress a shared agenda, but none starts from facts both people can already see. Interactive tool layout: an answer box first (a three-part agenda generated from the builder's current settings: the developer's own items first, two shared facts, one thing to try), then the builder, then the method in plain text, FAQ and CTA. The method section says why the developer's items go first and why the meeting is about support, not rating. One Kite Pulse callout in "Where the shared facts come from": a manager sees the developer's page as the same report the developer sees, without private prompt fields. The reader leaves with an agenda they can paste into their calendar invite.
- **Interactive elements:**
  1. Agenda builder - the reader picks meeting length (15, 30 or 45 minutes), how often they meet, the topics the developer has raised, and which shared facts to bring from a sample report (labelled sample data: active time this month, the Top 3 to act on, a long stuck stretch, Claude plan usage, upcoming leave). It produces a copyable agenda, timed, with the developer's items first and questions drawn from a fixed bank written for the page. Fallback is the default agenda as plain text.
  2. Question bank filter - questions for direct reports filtered by topic (blockers, workload, growth, AI habits, wellbeing), each with a "turns into rating, avoid" counter-example. Fallback is the full bank as a list.
- **Images / video (optional):** None - the builder is the page.
- **FAQ:**
  - How do I identify developers who need support or coaching with AI tools?
  - Can managers see developers' AI prompts?
  - Can I see usage by individual developer without creating a surveillance problem?
- **Links to:** /features, /privacy, /engineering-intelligence, /blog/developer-scorecard
- **Watch-outs:** Sheet note: avoid performance-review framing; no scores, no comparing one developer with another, no "underperformer" wording (R4). Verified (MSoT 1.4): All Developers and each developer's page show the same report the person sees, without private prompt fields; managers see their whole reporting line; My Scorecard leads with "Top 3 to act on" and says "not enough data" rather than guess; Leave & On-Call; own Claude plan usage. Cost per developer is admin-only (R7): leave cost out of the sample report. The verification signal needs AI labelling (Field Guide): leave it out of the builder. The builder must work for someone who never uses Kite Pulse. Section: Guides & tools (page type Interactive tool), URL at the site root, not under /blog.

### 5.11 · Bus Factor Risk Calculator

- **Category · intent · page type:** Benefits for Teams and Managers · Informational · Interactive tool
- **Section:** Guides & tools
- **Plan title:** Spot the One-Person Parts of Your Product Before They Hurt
- **Title tag:** Bus Factor Risk Calculator for Software Teams | Kite Pulse
- **H1:** Bus Factor Risk: Find the One-Person Parts of Your Product Before They Hurt
- **URL:** /bus-factor-calculator
- **Meta description:** Calculate bus factor risk per part of your product: enter who edits and reads each area, find any bus factor of 1, and get a hand-over plan to copy.
- **Main keyword:** bus factor risk
- **Secondary keywords:**
  - bus factor of 1 → H2 "What a bus factor of 1 looks like"
  - bus factor software engineering → H2 "How bus factor is measured in software engineering" (git-history methods, named in words)
  - capability mapping tools → H3 "Measuring per capability, not per repository" (main keyword of 12.8: link)
  - engineering resource allocation → body of H2 "Acting on the result" (main keyword of 11.9: link)
- **Description:** For engineering managers and tech leads. Ranking pages define the term or study it from git history; few compute it per part of the product, count people who read an area as well as those who edit it, or end in a hand-over action. Interactive tool layout: an answer box generated from the calculator's current data ("2 of 7 areas have a bus factor of 1"), then the calculator, then the method in plain text, FAQ and CTA. The method section states the definition used (the fewest people who between them make most of an area's changes) and why readers matter (they are who could step in). One Kite Pulse callout in "Measuring per capability": the Capability Map describes each project as modules, capabilities and scenarios, built and approved by a person, with no AI model. The reader leaves with a copyable hand-over plan for every bus-factor-1 area.
- **Interactive elements:**
  1. Bus factor calculator - an editable table of product areas and people (starts with a labelled sample team); each cell holds edits and reads; the page computes each area's bus factor, flags any area at 1, and lists who has read it. Output: a risk list and a copyable hand-over plan (area, current owner, who could take over, what to write down first). Fallback is the method paragraph with one worked example table.
  2. "If this person leaves" switch - the reader removes one person and sees which areas drop to one person or none. Fallback paragraph walks the sample through one departure.
- **Images / video (optional):** None.
- **FAQ:** (none in the sheet; proposed)
  - What is a good bus factor for a software team?
  - How do you calculate bus factor?
  - How do you reduce a bus factor of 1?
- **Links to:** /features, /engineering-intelligence, /blog/institutional-knowledge
- **Watch-outs:** Capability ownership, bus factor and hand-over hints are NOT in MSoT Section 1, and the Field Guide mentions only an "Ownership tab" on the Capability Map: confirm before any Kite Pulse claim beyond the Capability Map (MSoT 1.5) and Collaboration's contributors (MSoT 1.4). Until confirmed, the calculator runs on the reader's own input only and the callout stays at the Capability Map. The departure report and knowledge-capture requests (8.18) are unverified: leave out. The bus factor definition and any research named (for example the ICSE "Bus Factor in Practice" paper the sheet lists) need source URL and checked date in the data file. Overlaps 8.17 ("bus factor in software development"): keep this to the calculator. Section: Guides & tools (page type Interactive tool), URL at the site root.

### 6.2 · Engineering Metrics Dashboard: One Set of Facts

- **Category · intent · page type:** Benefits for Organisations · Commercial · Blog post
- **Plan title:** One Set of Figures Everyone Agrees On
- **Title tag:** Engineering Metrics Dashboard: One Set of Facts | Kite Pulse
- **H1:** Engineering Metrics Dashboard: One Set of Figures Everyone Agrees On
- **URL:** /blog/engineering-metrics-dashboard
- **Meta description:** Why engineering metrics dashboards disagree, and how figures built from the same AI session records keep team, usage and project pages consistent.
- **Main keyword:** engineering metrics dashboard
- **Secondary keywords:**
  - cto kpi dashboard → H2 "What a CTO KPI dashboard needs to agree on"
  - engineering team kpis → H2 "Engineering team KPIs, and where each one comes from"
  - engineering manager dashboard → H3 "The manager's view of the same figures" (main keyword of 9.12: link)
  - project health dashboard → body of the KPI H2 (main keyword of 2.16: link)
- **Description:** For leadership who have sat through an argument about whose numbers are right. Ranking pages list KPIs or sell a dashboard; none explains why two dashboards disagree. The reader learns the three usual causes (different definitions, different sources, different periods), then which engineering team KPIs come from git and tickets, which from AI sessions, and how to keep one definition per figure. One Kite Pulse callout at the sources H2: Team Overview, Team AI Usage, All Projects and the company report are all built from the same session records on the team's own server. An honest section: DORA and delivery metrics belong to git and ticket tools (R9). The reader leaves with a one-page definitions sheet to agree before building any dashboard.
- **Interactive elements:**
  1. "Why the numbers differ" simulator - one sample week (labelled sample data) and three sample dashboards that define "active developer" differently (any commit, any AI session, an hour or more of active time); the reader switches definitions and watches the counts move apart. Fallback paragraph gives the three counts and why.
  2. KPI source mapper - the reader ticks their KPIs (deploy frequency, cycle time, active developers, AI tokens by tool, project health, plan-limit pressure) and sees the right source for each, including where Kite Pulse is not it. Fallback is the same mapping as a table.
- **Images / video (optional):** None.
- **FAQ:**
  - How can I see AI coding-tool usage across my entire engineering organization?
  - How do I know what my engineering team is working on right now?
- **Links to:** /engineering-intelligence, /features, /blog/project-health-dashboard, /blog/company-ai-usage-report (built)
- **Watch-outs:** The sheet links /reports, which is hidden in this phase of the site (site.js HIDDEN, folded into /features): link /features and the built /blog/company-ai-usage-report instead. "Every page reads the same sessions, so they never contradict" is Article Plan wording, not MSoT: say "built from the same session records" and avoid the absolute (pages differ in period and scope; Team Overview refreshes every 30 seconds). Organisation Overview is admin by default and has a "Top performers" panel (R4). Cost is per tool and never totalled across tools (R7): a CTO KPI dashboard section must not show one AI cost total. Weak-fit keyword per sheet note.

### 6.6 · Privacy Preserving Analytics for AI Coding Work

- **Category · intent · page type:** Benefits for Organisations · Informational · Blog post
- **Plan title:** A Measurement Culture That Describes Work Instead of Ranking People
- **Title tag:** Privacy Preserving Analytics for AI Coding Work | Kite Pulse
- **H1:** Privacy Preserving Analytics: Measuring Engineering Work by Describing It, Not Ranking People
- **URL:** /blog/privacy-preserving-analytics
- **Meta description:** Privacy preserving analytics for engineering teams: describe work, not people, with pooled team figures, pseudonymised accounts and consent first.
- **Main keyword:** privacy preserving analytics
- **Secondary keywords:**
  - pseudonymised developer analytics → H2 "Pseudonymised developer analytics: what is hidden by default"
  - developer analytics without keystroke tracking → body of H2 "What is never collected" (main keyword of 7.13: link to the built page /blog/developer-analytics-without-keystroke-tracking)
  - team collaboration insights → H3 "Team collaboration insights without a name on them" (main keyword of 2.13: link)
- **Description:** For HR, people teams and works councils. Ranking pages on privacy preserving analytics are about web analytics or differential privacy; none applies it to measuring engineering work. The reader gets four principles (describe the work, pool figures for teams, hold back figures that would describe too few people, let each person see what is held about them) and checks each against what the product does, including the places where a person is named and who can see them. One Kite Pulse callout at the pseudonymised H2: tool accounts are sent as a keyed hash with the email domain and plan name, prompt statistics are shown only to the developer, and every person has a Privacy page. The reader leaves with a short list of questions to ask any vendor, this one included.
- **Interactive elements:**
  1. Who-sees-what explorer - the reader picks a data point (token counts, prompt statistics, tool account, full folder path, session summary) and a role (developer, manager, admin, manager outside the project) and sees who can see it, from MSoT 1.4 and 1.7. Fallback is the same table in plain text.
  2. Small-group check - a sample team-size slider shows a pooled figure being held back when it would describe too few people; the threshold is labelled "illustrative". Fallback paragraph explains why pooling fails for very small groups.
- **Images / video (optional):** None.
- **FAQ:**
  - Is Kite Pulse a performance-ranking tool?
  - Can I see usage by individual developer without creating a surveillance problem?
  - Is it ethical to track developers' AI tool usage?
  - Will developers see AI usage tracking as surveillance?
- **Links to:** /privacy, /blog/tracking-ai-usage-ethically, /features, /blog/developer-analytics-without-keystroke-tracking (built), /blog/can-my-employer-see-my-claude-code-chats (built)
- **Watch-outs:** R4: never use "developer performance ranking", "employee monitoring" or "keystroke logging" as targets, and do not write "never ranks people": Organisation Overview has "Top performers", Team Overview "Most active today", and Work Problems lists the most affected developers. The first FAQ answer depends on the owner's decision (MSoT "Owner decisions"): leave a visible placeholder. Verified (MSoT 1.7): reads session records, not source files, keystrokes or screens; secrets masked twice; pseudonymised accounts; consent before sync; private prompt statistics; managers outside a project see folder labels, not full paths; Privacy page. Pooling and withholding small groups (Team Review), and the Insights Catalog, are Field Guide only: confirm. Overlaps 6.7 (built) and 7.13: keep this to the culture angle for HR.

### 6.8 · Capture Knowledge from AI Coding Sessions

- **Category · intent · page type:** Benefits for Organisations · Commercial · Blog post
- **Plan title:** Keep What the Organisation Learns
- **Title tag:** Capture Knowledge from AI Coding Sessions | Kite Pulse
- **H1:** Capture Knowledge from AI Coding Sessions So the Organisation Keeps What It Learns
- **URL:** /blog/capture-knowledge-from-ai-coding-sessions
- **Meta description:** Capture knowledge from AI coding sessions: quoted knowledge records, a capability map and draft skills keep one developer's discovery for the next.
- **Main keyword:** capture knowledge from ai coding sessions
- **Secondary keywords:**
  - engineering knowledge management → H2 "Engineering knowledge management when the discussion happened with an AI" (main keyword of 8.15: link)
  - lessons learned software development → H3 "Lessons learned in software development, quoted from the session" (main keyword of 8.14: link)
  - capability mapping software → H3 "Filing knowledge where the product is described" (main keyword of 8.16: link)
  - turn repeated workflows into claude code skills → H2 "Turn repeated workflows into Claude Code skills" (main keyword of 3.13: link; also /skill-candidates)
- **Description:** For leadership and knowledge owners. Pages ranking here are about saving a single developer's AI chats or prompts; none keeps the lesson tied to the session and commit it came from. The reader learns why knowledge now gets lost inside AI conversations, then three places a discovery can live (a quoted record of a lesson, the product's capability map, a reusable skill for a repeated workflow) and which to use when. One Kite Pulse callout at the knowledge-management H2: knowledge records are passages quoted from real messages, linked to their sessions and commits, starting as "proposed". The reader leaves with a record format and a rule for what is worth keeping.
- **Interactive elements:**
  1. "Where does this lesson go?" sorter - six sample discoveries (a fix, a decision, a repeated set of steps, a new part of the product) that the reader sends to a knowledge record, a skill candidate or the capability map, with the reason shown. Fallback is the same as a table.
  2. Lesson record template - the reader types a lesson (kept in the browser, never sent) and gets a copyable record: what was learned, why, where it came from (session or commit link), who to ask. Fallback shows the template.
- **Images / video (optional):** None.
- **FAQ:**
  - How can I capture knowledge from AI coding sessions?
  - How do I share AI best practices across my team?
- **Links to:** /features, /blog/institutional-knowledge, /skill-candidates, /blog/claude-md-version-control (built)
- **Watch-outs:** Leave the Brain out (sheet note, R3). Say "knowledge records", never "Knowledge Base" (hidden page, R3). Verified (MSoT 1.5): knowledge records need AI labelling and the knowledge label list approved and run, and start as "proposed"; the Capability Map and Skill Candidates use no AI model; Session Graph groups similar sessions daily. The weekly knowledge log and coherence checks are Field Guide only: leave out. The project-notes read (CLAUDE.md, AGENTS.md) is an optional read an admin turns on (MSoT 1.1): mention only with that flag. Second FAQ answer can use Skill Candidates and the Agent features tab (MSoT 1.2). Overlaps /blog/institutional-knowledge and 7.8: keep to the three places.

### 6.14 · Corporate AI Spending Limits in 6 Steps

- **Category · intent · page type:** Benefits for Organisations · Informational · Interactive guide
- **Section:** Guides & tools
- **Plan title:** Adopt AI Analysis at a Pace You Control (absorbs 8.21, Intelligence Without an AI Service)
- **Title tag:** Corporate AI Spending Limits in 6 Steps | Kite Pulse
- **H1:** Corporate AI Spending Limits: How to Set Them for AI Coding Tools, Step by Step
- **URL:** /ai-spending-limits
- **Meta description:** Set corporate AI spending limits for AI coding tools in six steps: list spend sources, pick a unit, set caps and alerts, decide what happens at 100%.
- **Main keyword:** corporate ai spending limits
- **Secondary keywords:**
  - control ai cost → short answer, and body of H2 "Step 1: list every source of AI spend"
  - corporate ai spending budget limits → H2 "Step 4: set the budget limits and alert levels"
  - llm budget tracker → H3 "A monthly LLM budget tracker" (under step 4)
  - spend caps for ai coding agents → H2 "Step 6: spend caps for AI coding agents, and what happens at 100%"
  - developer analytics without source code access → body of H2 "Step 5: cap the AI inside your own tools", linking to the built page /blog/developer-analytics-without-source-code
  - self-hosted ai usage tracking → body of step 5 (main keyword of 1.2: link to /blog/self-hosted-ai-usage-tracking, and /self-hosted)
- **Description:** For finance, procurement and security leads. Ranking pages are news about companies capping staff AI spend; none walks through setting the limits. Interactive guide layout: guide label, H1, short answer, meta line (six steps, minutes, no sign-up), step chips, then six steps each with one tool: (1) list spend sources (seats, usage-based API spend, AI features inside other tools); (2) pick a unit, tokens or dollars, and what each misses; (3) pick the scope, per team, project or tool; (4) set limits and alert levels; (5) cap the AI inside your own tools, including analytics tools; (6) decide what happens at the limit. The one Kite Pulse callout sits at step 4: AI Budgets set a monthly budget per team or project in tokens or estimated US dollars, with alerts at 80% and 100%. Ends with a copyable spending-limit policy, then FAQ and CTA.
- **Interactive elements:**
  1. Spend-source inventory (step 1) - the reader ticks the AI tools and billing types they have and gets a list of spend sources, with which are seats and which are usage-based. Fallback list of common sources.
  2. Limit and alert calculator (steps 3-4) - the reader enters monthly amounts per team (their own figures, or a labelled sample) and alert percentages, and sees when each alert would fire at the current pace. Fallback paragraph gives the arithmetic.
  3. Policy builder (step 6) - the reader picks what happens at each level (notify, ask for approval, pause the AI feature) and who decides, and gets a copyable policy that combines all six steps. Fallback shows a sample policy in plain text.
- **Images / video (optional):** None - the tools carry the steps.
- **FAQ:**
  - Do I need an AI API key to use Kite Pulse?
  - Does AI coding analytics need an AI API key or send data to an LLM?
- **Links to:** /ai-budgets, /faq, /pricing, /privacy, /self-hosted, /blog/control-claude-code-spend-small-team (built)
- **Watch-outs:** AI Budgets alert at 80% and 100%; they do not stop anyone using an AI tool (MSoT 1.2): never imply a hard cap on the coding tools. A dollar budget adds up priced tools only and reports unpriced tokens separately; Codex, Cursor and Copilot usually show "—" (R7). Step 5 (from 8.21, verified MSoT 1.5): Kite Pulse runs fully without an AI service; AI labelling is off until an admin enters an OpenRouter key, sets a monthly budget above $0 and approves a label list, stops at the budget until next month and alerts at 80%; scrubbed text goes through OpenRouter with zero data retention by default (MSoT 1.7). Leave out Brain Chat and its budget (R3) and the Agent API's separate key (MSoT 2.1). /pricing has no prices yet (R8): link only. News facts about companies capping spend need source URL and checked date in the data file, or leave them out. Weak-fit keyword per sheet note: the guide answers the searcher's company-wide question, and Kite Pulse's own opt-in AI is step 5 only. Section: Guides & tools (page type Interactive guide), URL at the site root.
