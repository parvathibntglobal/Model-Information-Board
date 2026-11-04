# Kite Pulse - Article Production Plan, Categories 1-2

Draft for review, 3 November 2026. 30 articles (1.2 to 2.32): the category 1-2
articles marked "separate article" in `Kite Pulse - Article Keyword Map.xlsx`, minus
the ones already built as blogs (1.4, 1.5, 2.3, 2.18, 2.19, 2.20).

Each entry gives the SEO title (main keyword first, at most 60 characters with
" | Kite Pulse"), H1, URL, meta description (at most 155 characters), where each
secondary keyword goes, a short description of how the article is built, its 1-3
interactive elements, optional images or video (only where they add something a
widget cannot), FAQs, links and watch-outs. Product facts follow the Master Source
of Truth and the rules in `MASTER-PROMPT.md`. Nothing here is written article copy.

---

### 1.2 · Self-Hosted AI Usage Tracking: The Three Parts

- **Category · intent · page type:** Product Overview · Commercial · Blog post
- **Plan title:** The Three Parts of Kite Pulse: Desktop Program, Your Server, Web Console
- **Title tag:** Self-Hosted AI Usage Tracking: The Three Parts | Kite Pulse
- **H1:** Self-Hosted AI Usage Tracking: the Three Parts Every On-Premise Analytics Tool Needs
- **URL:** /blog/self-hosted-ai-usage-tracking
- **Meta description:** Self-hosted AI usage tracking has three parts: a desktop program, your own server and a web console. See what each does and what a full install needs.
- **Main keyword:** self-hosted ai usage tracking
- **Secondary keywords:**
  - on premise analytics tools → H1, and body of H2 "Why the three parts depend on each other" (main keyword of 12.2: secondary here, link to 12.2)
  - self-hosted claude code analytics → H3 "What self-hosted Claude Code analytics reads on the laptop" (under part one)
  - self-hosted developer analytics ubuntu → H3 "On an Ubuntu server" (under part two; main keyword of 13.3: one short paragraph, link to 13.3)
- **Description:** For technical evaluators and IT teams who need to know what a complete install contains before they scope it. Pages ranking for self-hosting talk about the server alone; this one explains why the server is empty without the desktop program and unreadable without the console. The reader goes through part one (the desktop program on Windows and macOS: reads the tools' session history, masks secrets, sends only new activity after consent), part two (the server the team runs: one computer, local network, Ubuntu 22.04/24.04 or the customer's own AWS account, PostgreSQL, local disk or S3), part three (the web console and role-based pages), then why each needs the others. One Kite Pulse callout at part two: no vendor cloud between the computer and the server. The reader leaves with a copyable install checklist for their own setup.
- **Interactive elements:**
  1. Install checklist builder - the reader picks where the server runs (one computer, local network, Ubuntu server, AWS) and which developer operating systems they have (Windows, macOS, other) and gets a copyable three-part checklist; choosing "other" shows that the desktop program ships for Windows and macOS only. Plain-text fallback lists the four server options and the two desktop platforms in a short table.
  2. "Take a part away" flow animation - a step-through of a sample session moving laptop → server → console; the reader switches any one part off and sees where the flow stops (no program: nothing reaches the server; no server: the program waits and catches up later; no console: data stored but nobody can read it). Fallback paragraph states the three dependencies in words.
- **Images / video (optional):** None - the flow animation shows the three parts and their links better than a static diagram.
- **FAQ:**
  - What infrastructure does a self-hosted AI coding analytics server need?
  - Can AI coding analytics be self-hosted on our own infrastructure?
  - Does the AI usage collector work on Windows and macOS?
- **Links to:** /self-hosted, /docs, /features, /security, /blog/local-ai-coding-analytics (built, for the one-computer setup)
- **Watch-outs:** R8: no Linux installer, no Windows server installer, no hosted SaaS, no encryption at rest (uploads encrypted in transit only). HTTPS is set up by the automated Ubuntu install and can be required on any install; do not imply it is always on. /self-hosted already targets this keyword as a secondary: keep this page to the three-part explanation and link to /self-hosted for deployment detail. "local ai coding analytics single user" belongs to the built page 4.14; mention the one-computer mode briefly and link to it.

### 1.3 · Secret Masking: A Session's Path in Six Steps

- **Category · intent · page type:** Product Overview · Informational · Story
- **Plan title:** From a Developer's Laptop to the Console: a Session's Journey in Six Steps
- **Title tag:** Secret Masking: A Session's Path in Six Steps | Kite Pulse
- **H1:** Secret Masking Along a Session's Journey: Where Kite Pulse Redacts Secrets, Step by Step
- **URL:** /blog/secret-masking
- **Meta description:** Follow one AI coding session from laptop to console in six steps: consent, secret masking on the computer and server, encryption, and going offline.
- **Main keyword:** secret masking
- **Secondary keywords:**
  - redact secrets → H1, and H2 "Step 4: redact secrets on the computer, then encrypt the upload"
  - track token usage without collecting prompts → body of H2 "Step 2: new activity is noticed" (a short aside on counts-only mode), linking to the built page /blog/track-token-usage-without-prompts
  - developer analytics without source code access → body of H2 "Step 1: the developer works as usual" (session records, not source files), linking to the built page /blog/developer-analytics-without-source-code
- **Description:** For privacy reviewers, evaluators and curious developers who want to see exactly what happens to a session. Ranking pages on secret masking describe log scrubbing in general; none follows one AI coding session through each point where it could leak. The reader follows six steps (works as usual, new activity noticed, consent first, masked and encrypted on the computer, masked again on the server, shown by role), then a short section on what happens when the network drops. The Kite Pulse callout sits at step 4: 36 credential patterns masked before upload, and a part that fails masking is not sent. The reader leaves knowing where masking happens, where it does not (Cursor and OpenCode chat text is masked on the server only) and what "masked" means.
- **Interactive elements:**
  1. Six-step session stepper - a sample session record (labelled sample data, with an obviously fake key such as "sk-EXAMPLE-0000") moves through the six steps; at step 4 the key turns into a masked placeholder, at step 5 the server pass is shown, and a "Cursor or OpenCode chat" toggle moves the masking for chat text to step 5 only. Fallback paragraph lists the six steps and the two masking points in words.
  2. Offline simulator - the reader "pulls the cable" at any point in a sample upload and watches the program remember where it stopped, then resume part by part once the server is reachable again. Fallback paragraph explains the catch-up behaviour.
- **Images / video (optional):** None - the stepper carries the journey; a real screenshot would show masked text that the sample already shows.
- **FAQ:**
  - How are secrets and credentials handled before upload?
  - What happens to AI session data when developers are offline?
  - Does an AI coding analytics tool read or store our source code?
- **Links to:** /blog/secrets-in-ai-prompts, /privacy, /self-hosted, /security, /blog/track-token-usage-without-prompts, /blog/developer-analytics-without-source-code
- **Watch-outs:** R6 wording: secrets are "masked", never "removed"; uploads encrypted in transit, never at rest. Before consent only the detected folder list (paths, names, repository addresses) is sent, so "nothing is sent" is wrong at step 3; say "no session content". Session records can include code excerpts the AI read or wrote. Do not suggest automatic leaked-credential scanning (R8). Both secondaries above are main keywords of built pages: secondary only, linked. Overlaps /blog/secrets-in-ai-prompts (existing target as secondary), 2.32, 3.10 and 10.11; keep this page to the journey.

### 1.6 · Software Engineering Intelligence Compared

- **Category · intent · page type:** Product Overview · Commercial · Blog post
- **Plan title:** How Kite Pulse Is Different from Other Engineering Tools
- **Title tag:** Software Engineering Intelligence Compared | Kite Pulse
- **H1:** Software Engineering Intelligence Compared: How Developer Analytics Tools Differ
- **URL:** /blog/software-engineering-intelligence
- **Meta description:** Software engineering intelligence tools compared by data source, tools covered, privacy and hosting, with a picker for which kind answers your question.
- **Main keyword:** software engineering intelligence
- **Secondary keywords:**
  - developer analytics tools → H1, and H2 "Three kinds of developer analytics tools, by where the data comes from"
  - developer productivity insight platform → H3 "Git and ticket-based developer productivity insight platforms" (LinearB, Jellyfish, Swarmia; DX for surveys)
  - developer analytics without source code access → body of H3 "AI-session analytics", linking to the built page /blog/developer-analytics-without-source-code
  - ai coding tools usage analytics for teams → H2 "AI coding tools usage analytics for teams: one view across ten tools"
- **Description:** For evaluators with a shortlist that mixes git analytics, survey tools and AI-usage tools. Comparison pages today are vendor lists; this one sorts tools by where their data comes from (git and tickets, surveys, a vendor's own dashboard, AI session history) and says which questions each can answer. The reader moves from the three data sources, to what each misses, to an honest "when another tool fits better" section (DORA metrics belong to git/Jira tools, R9). One Kite Pulse callout: it reads the AI session itself across ten tools, developers fill nothing in, it runs on the team's own server, and AI labelling is opt-in. The reader leaves knowing which kind of tool matches each of their questions.
- **Interactive elements:**
  1. Question-to-tool picker - the reader ticks the questions they need answered (deploy frequency, survey sentiment, which AI tools are used, Claude plan-limit pressure, repeated failed commands) and sees which category of tool answers each, including where Kite Pulse is not the right source. Fallback is the same mapping as a plain table.
  2. Filterable comparison table - categories of tools as rows, columns for data source, hosting, tools covered and what developers must do; filters for "self-hosted only" and "no surveys". Competitor rows carry facts with sources and checked dates in the page's data file. Fallback paragraph summarises the three data sources.
- **Images / video (optional):** None - the table and picker do the comparing.
- **FAQ:**
  - How does AI coding analytics compare to LinearB, Jellyfish, DX or Swarmia?
  - How is a cross-tool AI analytics platform different from GitHub Copilot Metrics?
  - Is there one tool that tracks Claude Code, Cursor and GitHub Copilot together?
- **Links to:** /engineering-intelligence, /compare/linearb, /compare/jellyfish, /compare/dx, /compare/swarmia, /blog/developer-analytics-without-source-code
- **Watch-outs:** Every competitor fact needs a source URL and checked date in the data file (R2); write placeholders where unverified. Copilot coverage is GitHub Copilot Chat in VS Code only (R5), and cost for Cursor and Copilot usually shows "—" (R7): the third FAQ answer must say both. Avoid the "not X but Y" framing the card uses ("the process, not just the result"); state what each reads. No ranking language (R4). /engineering-intelligence targets this keyword as a secondary: cross-link, do not repeat its content.

### 1.7 · Can My Employer See My Claude Code Prompts?

- **Category · intent · page type:** Product Overview · Informational · Blog post
- **Plan title:** What Kite Pulse Is Not
- **Title tag:** Can My Employer See My Claude Code Prompts? | Kite Pulse
- **H1:** Can My Employer See My Claude Code Prompts? What a Session-History Tool Is Not
- **URL:** /blog/employer-see-claude-code-prompts
- **Meta description:** Can my employer see my Claude Code prompts? What a session-history tool like Kite Pulse reads, seven things it is not, and the optional reads.
- **Main keyword:** can my employer see my claude code prompts
- **Secondary keywords:**
  - can my company see my copilot chats → H3 "Copilot Chat, Cursor and the other tools" (one paragraph, linking to the built page /blog/can-my-employer-see-my-claude-code-chats for the full answer)
  - can my employer see my cursor prompts → same H3 "Copilot Chat, Cursor and the other tools"
  - does claude code store conversations → H2 "Where Claude Code stores conversations on your computer"
  - developer analytics without source code access → body of the "Not a source-code reader" item, linking to the built page /blog/developer-analytics-without-source-code
  - track token usage without collecting prompts → H3 "Counts-only mode: track token usage without collecting prompts", linking to the built page /blog/track-token-usage-without-prompts
  - pseudonymised developer analytics → body of the "Not your account address" item (tool accounts sent as a keyed hash, domain and plan name; scope limited to accounts, see Watch-outs)
- **Description:** For sceptical developers, works councils and security reviewers. Ranking pages cover Claude Team/Enterprise admin exports and endpoint agents; none states plainly what a third-party session-history tool is not. The page answers the question in three sentences, explains where Claude Code keeps conversations locally, then goes through seven "is not" items (keystroke logger, screen recorder, website tracker, code-quality scanner, a tool built to rank people, your vendor's invoice, single sign-on) and closes with the optional reads that do go further. The one Kite Pulse callout is the Privacy page, where each person sees everything recorded about them and who can see it. The reader leaves with a clear list of what is and is not read, and what to ask their admin.
- **Interactive elements:**
  1. "Is it or isn't it" flip cards - seven statements; the reader guesses, then flips each card to read the plain answer and its caveat (session records can include code excerpts; Organisation Overview has a "Top performers" panel). Fallback is the same seven items as a list.
  2. Optional-reads panel - a list of the reads that are off until an admin turns them on (branch name, package manifests, project notes, installed tool versions, Claude Code skills and MCP servers and others); the reader toggles each to see what it adds to a sample record. Fallback paragraph names them and says they are off by default.
- **Images / video (optional):** None - the flip cards and toggles carry the argument.
- **FAQ:**
  - Is Kite Pulse a performance-ranking tool?
  - Does Kite Pulse read my source code?
  - Will developers see AI usage tracking as surveillance?
  - How do I track AI coding usage without monitoring keystrokes?
- **Links to:** /privacy, /blog/tracking-ai-usage-ethically, /security, /self-hosted, /blog/can-my-employer-see-my-claude-code-chats, /blog/developer-analytics-without-source-code, /blog/track-token-usage-without-prompts, /blog/developer-analytics-without-keystroke-tracking
- **Watch-outs:** Strong overlap with the built page 9.14 (/blog/can-my-employer-see-my-claude-code-chats): "prompts" and "chats" are near-identical searches. Keep this page to the "what it is not" list and cross-link, or have the owner decide whether to merge. R4: do not write "never ranks people"; the first FAQ answer says it describes work and names the "Top performers" and "Most active today" panels (owner decision open). Do not state whether managers can read session text: the MSoT says only that private prompt statistics are hidden from everyone else. "Pseudonymised" applies to tool accounts only; people appear by name in the console. Single sign-on is listed as not offered, never implied. Keep away from employee-monitoring terms (sheet note).

### 1.8 · Glossary of Common AI Terms in AI Coding Tools

- **Category · intent · page type:** Product Overview · Informational · Blog post
- **Plan title:** Kite Pulse Terms in Plain Words
- **Title tag:** Glossary of Common AI Terms in AI Coding Tools | Kite Pulse
- **H1:** Glossary of Common AI Terms for AI Coding Tools: an AI Glossary for Beginners
- **URL:** /blog/glossary-of-common-ai-terms
- **Meta description:** A glossary of common AI terms for AI coding tools: session, token, plan headroom, tool account and more, in plain words, with a quick self-check.
- **Main keyword:** glossary of common ai terms
- **Secondary keywords:**
  - ai glossary for beginners → H1, and the short answer under it
  - common ai terms glossary → H2 "Common AI terms glossary: the words you meet first" (session, token, model, tool call, sub-agent)
  - ai plan limits → H3 "Plan headroom and AI plan limits"
  - token usage per developer → body of the "Token" entry, linking to the built page /blog/token-usage-per-developer
  - what is claude code analytics → H3 "What is Claude Code analytics?"
- **Description:** For new users and the people writing rollout notes, who need each word to mean the same thing to everyone. Generic AI glossaries cover machine-learning vocabulary (fine-tuning, RLHF) and nothing about coding-assistant usage. The page opens with the general AI-coding terms (session, token, model, tool call, sub-agent, plan limit), then the Kite Pulse terms in the order a new user meets them (desktop program, client code, Onboarding Wizard, console, access role, scope, tool account, active time, plan headroom, working style, insight). No separate product callout: the product terms are the content. The reader leaves with shared definitions and a self-check.
- **Interactive elements:**
  1. Filterable glossary - a search box plus chips (General AI terms / Kite Pulse terms / Terms about access) filter the definitions; each entry has a one-line definition and a "where you see it" note. The full list is plain HTML, so the fallback is the list itself.
  2. Match-the-term self-check - eight short descriptions, the reader picks the matching term from a dropdown and gets a score with the definitions they missed. Fallback paragraph says the check uses the definitions above.
- **Images / video (optional):** None - definitions need text, and the filter makes them findable.
- **FAQ:**
  - how is token usage calculated in ai
- **Links to:** /faq, /docs, /plan-headroom, /features, /blog/token-usage-per-developer, /blog/what-are-tokens-in-ai
- **Watch-outs:** Weak fit (sheet note): demand exists only for general AI glossaries, so the general terms must come first. "token usage per developer" is the built page 2.18's main keyword: secondary only, linked; the FAQ answer links to the built tokens page 1.4. Access roles are Admin, Manager, Developer; plan headroom is Claude Code only ("near" 80%, "at limit" 100%); working style is builder, explorer, debugger, communicator or generalist from what sessions did. Coordinate with the /glossary hub so terms are not defined twice with different wording.

### 1.9 · Claude Code Estimated Cost: Where It Comes From

- **Category · intent · page type:** Product Overview · Informational · Interactive guide
- **Plan title:** Where the Numbers Come From
- **Title tag:** Claude Code Estimated Cost: Where It Comes From | Kite Pulse
- **H1:** Claude Code Estimated Cost: How to Calculate Claude Token Cost and How Far to Trust It
- **URL:** /blog/claude-code-estimated-cost
- **Meta description:** How Claude Code estimated cost is worked out from tokens and list prices, why it is not your bill, and a calculator to check a figure yourself.
- **Main keyword:** claude code estimated cost
- **Secondary keywords:**
  - how to calculate claude token cost → H1, and H2 "How to calculate Claude token cost by hand"
  - ai token cost estimate → H2 "What an AI token cost estimate can and cannot tell you"
  - how are ai tokens calculated → H3 "How are AI tokens calculated? The tool counts them", linking to the built page /blog/what-are-tokens-in-ai
  - how to calculate ai coding costs per developer → body of H2 "What an AI token cost estimate can and cannot tell you", linking to the built page /blog/ai-coding-cost-per-developer
  - token usage by model → H3 "Token usage by model changes the estimate"
  - token usage monitoring → H2 "How fresh the figures are: token usage monitoring between uploads", linking to /blog/token-usage-forecast
- **Description:** For finance, managers and anyone about to quote a figure in a meeting. Ranking results quote per-developer averages and price tables; none explains how an estimate is built from session token counts at list price, why it differs from the invoice, or why a cross-tool total is withheld. The guide walks through where token counts come from, how the estimate is calculated, why older sessions keep the price they ran at, which tools show "—", how plan figures differ from cost, and how fresh each figure is. One Kite Pulse callout: cost is labelled "not billed spend", shown per tool and never added across tools. The reader leaves able to quote a figure with its limits.
- **Interactive elements:**
  1. Estimate calculator - the reader enters sample input, output and cache token counts and picks a sample model ("example prices", source and date in the data file); a "price changed on day 15" toggle shows sessions before and after keeping their own dated price. Fallback paragraph gives the formula in words: tokens × list price per token type.
  2. "Can I quote this?" sorter - six sample figures (cost per tool, a total across tools, a Codex cost, a stale plan reading, a dollar budget with unpriced tokens) dropped into "quote as is", "quote with a caveat" or "don't quote"; each answer explains why. Fallback lists the six with their answers.
- **Images / video (optional):** None - the calculator is the explanation.
- **FAQ:**
  - Are Kite Pulse cost figures exact?
  - How accurate are AI coding cost estimates?
  - How quickly is usage and cost data updated?
- **Links to:** /ai-cost-tracking, /plan-headroom, /faq, /reports, /blog/what-are-tokens-in-ai, /blog/ai-coding-cost-per-developer, /blog/token-usage-forecast
- **Watch-outs:** R7 throughout: estimate from list prices, "not billed spend"; priced for Claude and Gemini models plus the tool-reported cost of Aider, Cline, Roo Code, Kilo Code and OpenCode; Codex, Cursor and Copilot usually "—", never $0; no total across tools on Team AI Usage; cost per developer is admin-only. Vendor prices and the Anthropic per-day estimate in the news need source and checked date in the data file. The card's "not enough data" applies to insights (My Scorecard), not to cost; say so. Overlaps 2.19 (built) on method: keep this page to "where the number comes from" and link there for per-developer calculation. "how to calculate ai coding costs per developer" is the built page's main keyword: secondary only.

### 1.11 · AI-Assisted Development Analytics as One Loop

- **Category · intent · page type:** Product Overview · Commercial · Blog post
- **Plan title:** One Loop: Capture, Understand, Act, Learn
- **Title tag:** AI-Assisted Development Analytics as One Loop | Kite Pulse
- **H1:** AI-Assisted Development Analytics as One Loop: Capture, Understand, Act, Learn
- **URL:** /blog/ai-assisted-development-analytics
- **Meta description:** AI-assisted development analytics as one loop: capture sessions, understand them, act, then check next week's sessions. With a loop plan to copy.
- **Main keyword:** ai assisted development analytics
- **Secondary keywords:**
  - ai coding analytics platform → body of H2 "Capture: one set of sessions behind every page", linking to the built page /blog/ai-coding-analytics-platform
  - ai coding tools usage analytics for teams → H2 "Understand: AI coding tools usage analytics for teams"
  - ai collaboration metrics → H3 "AI collaboration metrics worth watching" (main keyword of 8.12: secondary here, link to /blog/ai-collaboration-metrics)
- **Description:** For decision-makers who want the whole picture before any one feature. Pages ranking for AI development analytics list metrics; few explain how measuring, acting and checking connect. The page walks the loop: capture (the desktop program reads ten tools' sessions), understand (Team AI Usage, Work Problems, Plan headroom and the project pages read those same sessions), act (people change something, for example a budget or a workflow), learn (next week's sessions show whether it worked). One Kite Pulse callout at "capture": every page reads the same sessions, so a figure can be traced back. The reader leaves with a copyable loop plan for one question.
- **Interactive elements:**
  1. Loop animation with a worked example - a sample team ("Sample team", labelled) goes through four weeks: repeated failed commands found on Work Problems, a fix agreed, and the following weeks' sample counts shown falling or not; the reader steps through each stage. Fallback paragraph describes the four stages in words.
  2. Loop planner - the reader picks one question (plan-limit pressure, repeated failures, idle seats, uneven tool adoption) and gets a copyable plan: what is captured, which console page shows it, an example action, and what to check next week. Fallback lists the four plans as text.
- **Images / video (optional):** None - the loop animation carries the idea.
- **FAQ:**
  - What metrics should I use to measure AI-assisted development?
  - How should I measure whether our AI coding-tool investment is successful?
- **Links to:** /ai-coding-analytics, /features, /engineering-intelligence, /reports, /blog/ai-coding-analytics-platform, /blog/ai-collaboration-metrics
- **Watch-outs:** No ROI figure exists in the visible console (MSoT 2.5, Cost & ROI hidden): the second FAQ answer lists the inputs Kite Pulse gives (tokens, estimated cost per tool, seat prices, active time) and says the judgement is the team's. Avoid "the figures always agree"; say "they read the same sessions". "ai coding analytics platform" is the built page 1.5's main keyword: secondary only, linked. Overlap with /ai-coding-analytics (existing target as secondary).

### 1.12 · AI Usage Dashboard for Developers: Console Map

- **Category · intent · page type:** Product Overview · Commercial · Interactive guide
- **Plan title:** A Map of the Console
- **Title tag:** AI Usage Dashboard for Developers: Console Map | Kite Pulse
- **H1:** AI Usage Dashboard for Developers and Managers: a Map of the Kite Pulse Console
- **URL:** /blog/ai-usage-dashboard-for-developers
- **Meta description:** A map of the Kite Pulse console as an AI usage dashboard for developers, managers and admins: what each area shows and which role sees it.
- **Main keyword:** ai usage dashboard for developers
- **Secondary keywords:**
  - engineering manager dashboard → H2 "The engineering manager dashboard: pages for your reporting line" (main keyword of 9.12: secondary here, link to /blog/engineering-manager-dashboard)
  - team activity dashboard → H3 "Team Overview, the team activity dashboard" (main keyword of /features: link there)
  - what is my team working on dashboard → body of H3 "Team Overview, the team activity dashboard" (main keyword of 2.11: link to it)
- **Description:** For new users finding their way around, and for buyers who want to see the shape of the product. Product tours elsewhere are screenshots; this is a map in the order people meet the menu: your own pages (Workspace, My Scorecard & Insights, My Activity, My Sessions, Privacy, Account), The Office and Needs attention, then team pages (Team Overview, All Developers, Collaboration), usage and cost (Team AI Usage, AI Budgets), projects (All Projects), and admin areas (Accounts & Roles, Tools, Machines, Audit Log). Each area says which role sees it by default. No separate callout: the console is the subject. The reader leaves knowing where to look for their question.
- **Interactive elements:**
  1. Role-switch console map - a sample menu drawn in HTML; the reader picks Admin, Manager or Developer and sees which items are visible by default, and clicks an item for a one-line description. Fallback is a table of areas, roles and descriptions.
  2. "Where do I find it?" finder - the reader picks a question ("Is my work being collected?", "Who is close to a Claude plan limit?", "Which projects are dormant?") and is pointed to the page and role. Fallback lists the questions and pages.
- **Images / video (optional):** Image (optional) - one annotated screenshot of the real menu - shows the actual layout and density, which a drawn map only approximates - taken from a deployment (MSoT 2.5: the owner's server shows only Claude Code and Gemini CLI, so say so in the caption).
- **FAQ:**
  - What is the best dashboard for AI-assisted engineering teams?
  - How does role-based access work in developer analytics tools?
- **Links to:** /ai-coding-analytics, /features, /docs, /security, /blog/engineering-manager-dashboard (9.12), 2.11's page
- **Watch-outs:** Use current page names only (Team Overview, All Projects, Work Problems, Machines, Privacy, Account). Leave hidden pages off the map (Activity Rhythm, Coaching & Risk, Cost & ROI, Comparisons, Intelligence, Knowledge Base, Tech-Debt Radar, Ask Kite Pulse, Project Details, Events & Policies); Trends may appear. Role defaults: Developer sees own pages plus The Office, Needs attention and Help; Organisation Overview, Work Problems and Tool Accounts are admin by default; admins can change this on Roles & Permissions. Main keywords of 9.12, 2.11 and /features appear here as secondaries only. The first FAQ must not claim "best"; describe what to look for.

### 2.2 · Duplicate Repository Detection for AI Projects

- **Category · intent · page type:** Features and Capabilities · Informational · Blog post
- **Plan title:** Automatic Project Detection
- **Title tag:** Duplicate Repository Detection for AI Projects | Kite Pulse
- **H1:** Duplicate Repository Detection: Keeping One Project as One Across Machines
- **URL:** /blog/duplicate-repository-detection
- **Meta description:** How duplicate repository detection keeps one project as one across laptops and folders, with a simulator for deciding when to merge or split.
- **Main keyword:** duplicate repository detection
- **Secondary keywords:**
  - engineering project tracking ai → H2 "Why engineering project tracking with AI needs the right project list"
  - project health dashboard → H3 "What a clean list does for the project health dashboard" (main keyword of 2.16: secondary here, link to it)
- **Description:** For developers and admins who see one project listed three times, or two projects merged into one. Searches for duplicate repository detection mostly return git-host tips for finding copied repositories; nothing covers the same repository cloned into differently named folders on several laptops. The reader learns why folder names are unreliable, how a repository address ties clones together, what Duplicate Detection groups and when a split is right instead, and how an approver can file a folder under a parent project. One Kite Pulse callout: projects are found automatically and one repository cloned on several machines counts as one project. The reader leaves with a simple merge-or-split rule of thumb.
- **Interactive elements:**
  1. Merge-or-split simulator - a sample set of folders from three laptops (labelled sample data) with names and repository addresses; the reader marks pairs "same project" or "different", then sees what matching on the repository address would do and where a person still has to decide (a folder with no repository address, a monorepo that should be split). Fallback paragraph states the rule: same address, same project; no address, a person decides.
  2. Two-laptop animation - one repository cloned as "api" on one laptop and "backend-api" on another; a short loop shows both resolving to one repository address and one project. Fallback sentence describes it.
- **Images / video (optional):** None - the simulator shows the problem with sample folders.
- **FAQ:**
  - How does AI coding analytics handle developers with multiple machines?
- **Links to:** /features, /docs, 2.16's page
- **Watch-outs:** Intent risk: many searchers want to find duplicated repositories on GitHub; the short answer must make the scope clear in its first sentence. MSoT 1.4 says Duplicate Detection "groups folders that look like the same repository and offers Merge; also suggests splits"; do not say merges happen without a person. Onboarding Approvals is on by default and can be switched off in Detection Rules. The FAQ answer can add that a renamed or reinstalled computer keeps its identity (MSoT 1.1). Do not state which role uses Duplicate Detection; the MSoT does not say.

### 2.4 · Personal Claude Code Usage Stats in Workspace

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** Workspace: Is My Work Being Captured?
- **Title tag:** Personal Claude Code Usage Stats in Workspace | Kite Pulse
- **H1:** Personal Claude Code Usage Stats: Your Remaining Usage and Whether Your Work Is Captured
- **URL:** /blog/personal-claude-code-usage-stats
- **Meta description:** Personal Claude Code usage stats on your own Workspace page: your plan usage, each project's capture status, and what to do when one is stuck.
- **Main keyword:** personal claude code usage stats
- **Secondary keywords:**
  - my ai coding stats → H2 "My AI coding stats: what your Workspace shows" (main keyword of 4.8: secondary here, link to it)
  - claude code remaining usage → H2 "Claude Code remaining usage: your own plan figures"
  - claude code usage tracking → body of H2 "Is my work being captured? Each project state explained"
- **Description:** For developers who want two answers fast: how close am I to my Claude plan limit, and is my work reaching the server. The keyword is about personal usage, which the page answers first (the sheet notes the weak fit with the capture-status core). Sections: your own Claude plan figures and how fresh they are; the six project states (detected, waiting to sync, syncing, processing, processed, failed) and what to do for each; confirming, renaming or splitting projects in My Projects, Pending Requests and Project Detection; what happens when you are offline. One Kite Pulse callout on plan figures: read from what Claude Code saves on your computer, with no login or password read. The reader leaves able to read their own Workspace without asking anyone.
- **Interactive elements:**
  1. Project-state explainer - a sample project list (labelled) with each state; the reader clicks a state to see what it means and the next step. Fallback is a two-column table of states and next steps.
  2. Own plan-figure gauge - sample 5-hour and weekly readings; the reader moves a "last saved" slider and sees the reading flagged as stale, and moves usage past 80% ("near") and 100% ("at limit"). Fallback paragraph explains the windows and thresholds in words.
- **Images / video (optional):** None - both widgets mirror the page with sample data.
- **FAQ:**
  - What happens to AI session data when developers are offline?
  - claude code how close am i to the limit
- **Links to:** /features, /plan-headroom, /docs, /blog/avoid-hitting-claude-limit, 4.8's page
- **Watch-outs:** The card's "uploads being retried with the reason", "what is still waiting for each computer" and "your next setup step" are not in MSoT Section 1 (Workspace is verified only for project states and own plan usage): confirm before describing them. Plan figures are Claude Code only and as fresh as Claude Code's last save; the optional background refresh is an admin switch (app 0.4.2 or later) the developer can turn off. Status-line figures are unreleased (MSoT 2.3): leave out. "avoid hitting claude limit" belongs to the built page 4.4: link from the second FAQ answer.

### 2.5 · Developer Scorecard: A Top 3 to Act On

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** My Scorecard & Insights: a Top 3 to Act On
- **Title tag:** Developer Scorecard: A Top 3 to Act On | Kite Pulse
- **H1:** A Developer Scorecard for Yourself: My Scorecard & Insights and a Top 3 to Act On
- **URL:** /blog/developer-scorecard
- **Meta description:** A developer scorecard written for you: how My Scorecard & Insights picks a top 3 to act on, shows its evidence, and says "not enough data" when needed.
- **Main keyword:** developer scorecard
- **Secondary keywords:**
  - dev scorecard → body of the short answer under the H1
  - ai session success rate → H3 "AI session success rate, when AI labelling is on" (main keyword of 5.8: secondary here, link to it)
  - my ai coding stats → body of H2 "What sits around the top 3" (main keyword of 4.8: link)
  - developer working style → H3 "Your working style" (main keyword of 2.6: one paragraph, link)
  - coding streak app → body of H3 "Work-pattern facts: streaks, peak hour and deep sessions"
  - personal claude code usage stats → body of H2 "What sits around the top 3" (main keyword of 2.4: link)
- **Description:** For developers who distrust scorecards because most rank people. Pages ranking for developer scorecard are team performance templates; this one is a scorecard the developer reads about themselves. Sections: what the top 3 is and how each item is built (verdict, why it matters, what to try, evidence); why "not enough data" appears instead of a guess; the work-pattern facts and working style around it; who else can see it. One Kite Pulse callout: insights say "not enough data" instead of a verdict when data is thin. The reader leaves knowing how to read an insight, with a copyable "try this week" note.
- **Interactive elements:**
  1. Insight card with a data slider - one sample insight (labelled); the reader drags "weeks of data" and sees the card change from "not enough data" to a verdict with its evidence. Fallback paragraph explains the four parts of an insight and the "not enough data" rule.
  2. "Try this week" note builder - the reader picks one of three sample insights and gets a short copyable note (what to try, what to look at next week). Fallback lists the three sample insights.
- **Images / video (optional):** None - the insight card is the subject and is shown with sample data.
- **FAQ:**
  - Can my manager see everything I type to the AI?
  - Is Kite Pulse a performance-ranking tool?
- **Links to:** /features, /privacy, 2.4's page, 2.6's page, 4.8's page, 5.8's page
- **Watch-outs:** "Personal" must not imply private: managers and admins in scope see the same report on All Developers, without private prompt fields (MSoT 1.4); state this. The card's "productivity tiles" and "verification signal" are not in MSoT Section 1: leave out until confirmed; if added, the verification signal needs AI labelling switched on by an admin. "Session succeeded" is an AI labelling tag (MSoT 1.5), so the success-rate section is conditional. R4: no ranking framing (sheet note); the second FAQ answer names the "Top performers" panel honestly. First FAQ answer: say what is private (prompt statistics) and do not claim managers cannot see session content. Absorbs 13.7.

### 2.6 · Developer Working Style and Your Work Patterns

- **Category · intent · page type:** Features and Capabilities · Informational · Interactive guide
- **Plan title:** How You Work: My Activity, Work Patterns, Working Style and Private Prompt Statistics
- **Title tag:** Developer Working Style and Your Work Patterns | Kite Pulse
- **H1:** Developer Working Style: Your Peak Hour, Streaks, Deep Sessions and Private Prompt Stats
- **URL:** /blog/developer-working-style
- **Meta description:** Your developer working style, worked out from what your sessions did, plus peak hour, streaks, deep sessions and the prompt stats only you see.
- **Main keyword:** developer working style
- **Secondary keywords:**
  - deep work sessions developer → H3 "Deep work sessions: 60 minutes or more" (main keyword of 4.3: secondary here, link to it)
  - developer activity heatmap → H2 "Reading a developer activity heatmap of your own week"
  - coding streak app → H3 "Longest streak: what a coding streak app counts, and what this counts"
  - my ai coding stats → body of H2 "Private prompt statistics" (main keyword of 4.8: link)
- **Description:** For developers curious about their own habits. Results for working style are personality quizzes; none derive a style from what someone's AI sessions actually did. The guide goes through My Activity (when, how long, which tools), the work-pattern facts (peak hour, busiest day, longest streak, deep sessions of 60 minutes or more, longest session, most sessions at once, share of short bursts under 15 minutes), the five working styles and how they are worked out, and private prompt statistics. One Kite Pulse callout on private prompt statistics: the server removes them for everyone but you. The reader leaves understanding each figure and which ones others can see.
- **Interactive elements:**
  1. Working-style mixer - four sliders for the share of session activity (changing files, reading code, running commands, conversation) show which style a sample mix leans to; labelled "illustration: the console uses its own fixed rules". Fallback paragraph lists the five styles and what each means.
  2. Sample week heatmap - an hour-by-weekday grid of sample sessions (labelled), with tool chips; peak hour, deep sessions and parallel sessions are highlighted on hover. Fallback paragraph defines each work-pattern fact.
  3. Who-sees-it toggle - switch between "You" and "Your manager" on a sample profile; the private prompt statistics panel disappears in the manager view. Fallback sentence states the rule.
- **Images / video (optional):** None - the three widgets cover what screenshots would.
- **FAQ:**
  - Can managers see developers' AI prompts?
  - Can my manager see everything I type to the AI?
- **Links to:** /features, /privacy, /parallel-ai-agents, 4.3's page, 4.8's page
- **Watch-outs:** Busiest day is the weekday with the most commits (MSoT); say so. Working style comes from fixed rules over what sessions did, not from tool mix (Website corrections), and includes "generalist"; the mixer must not present its thresholds as the product's. The heatmap is the article's illustration; the MSoT verifies My Activity's content (when, how long, which tools), not a heatmap: do not say the console draws one. FAQ answers: prompt statistics are private; do not claim managers can never read session content. The FAQ pair repeats 2.5's and 2.29's: vary the answers or link to one canonical answer.

### 2.7 · Search Past AI Coding Sessions in My Sessions

- **Category · intent · page type:** Features and Capabilities · Commercial · How-to
- **Plan title:** My Sessions: Finding the Session You Need
- **Title tag:** Search Past AI Coding Sessions in My Sessions | Kite Pulse
- **H1:** Search Past AI Coding Sessions: Claude Code and Codex Session History in One List
- **URL:** /blog/search-past-ai-coding-sessions
- **Meta description:** How to search past AI coding sessions: where Claude Code and Codex keep session history, and how My Sessions lists every tool's sessions together.
- **Main keyword:** search past ai coding sessions
- **Secondary keywords:**
  - claude code session history → H2 "Where Claude Code session history lives on your computer"
  - codex session history → H3 "Codex session history"
  - claude code session analytics → H3 "From a found session to Claude Code session analytics", linking to the built page /blog/claude-code-session-analysis
  - find similar ai coding sessions → H2 "Find similar AI coding sessions with Session Graph"
- **Description:** For developers trying to find "the session where I fixed that" a week later. Nothing ranks for this exact need; the closest pages explain one tool's resume command. The how-to first shows where Claude Code and Codex keep their history and how to search it by hand, then the limits of doing that across tools and machines, then My Sessions (every session with a summary, filters and a detailed view) and Session Graph for look-alike sessions. One Kite Pulse callout at the point where hand-searching stops scaling (several tools, several machines). The reader leaves with a by-hand method and a sense of when a list helps.
- **Interactive elements:**
  1. Filterable sample session list - twelve sample sessions (labelled) with chips for tool and model and a search box over the one-line summaries; results update as the reader types. Fallback paragraph says what each filter narrows.
  2. Similar-sessions demo - clicking a sample session highlights the sessions Session Graph would group with it, with a note that grouping is rebuilt once a day and uses no AI model. Fallback sentence describes the grouping.
- **Images / video (optional):** None - the sample list is clearer than a screenshot of a real one.
- **FAQ:**
  - None in the input.
- **Links to:** /blog/institutional-knowledge, /integrations/claude-code, /features, /blog/claude-code-session-analysis
- **Watch-outs:** MSoT verifies My Sessions only as "every session with a summary, filters and a detailed view"; the card's specific filters (session type, label) and "main versus parallel time" are not stated there: confirm before naming them. AI labels appear only when an admin sets up AI labelling. Local history locations for Claude Code and Codex are outside facts: record source and checked date in the data file. "claude code session analysis" belongs to the built page 4.6; keep this page to finding a session and link there for analysis. Session Graph is on by default (MSoT 1.5).

### 2.8 · Claude Code Session Replay: Inside One Session

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** Inside One Session: Playback, Summary and Segments
- **Title tag:** Claude Code Session Replay: Inside One Session | Kite Pulse
- **H1:** Claude Code Session Replay: a Session History Viewer with Summary and Segments
- **URL:** /blog/claude-code-session-replay
- **Meta description:** Claude Code session replay explained: read one session turn by turn, with its summary and segments, and see what a viewer adds to the transcript.
- **Main keyword:** claude code session replay
- **Secondary keywords:**
  - claude code session history viewer → H1, and H2 "What a Claude Code session history viewer should show"
  - claude code transcript viewer → H3 "Reading the raw transcript with a Claude Code transcript viewer"
  - claude code conversation history viewer → body of H3 "Reading the raw transcript with a Claude Code transcript viewer"
  - claude code session analysis → body of H2 "From one session to patterns", linking to the built page /blog/claude-code-session-analysis
- **Description:** For developers reviewing their own work after the fact. Ranking pages are open-source transcript viewers for one machine; this explains what to look for in a replay (turn order, tool calls, sub-agent branches, where time went) and how a summary and segments make a long session readable. The reader moves from reading the raw transcript by hand, to what a viewer adds, to the session page in the console. One Kite Pulse callout: the session summary is made without AI. The reader leaves knowing how to review a long session quickly.
- **Interactive elements:**
  1. Replay scrubber - a sample Claude Code session (labelled) on a timeline of turns and tool calls, with one sub-agent branch; the reader scrubs and sees the step type and elapsed time at each point. Fallback paragraph describes how to read a session in order.
  2. Three-views toggle - the same sample session shown as raw steps, as segments, and as a short summary, so the reader sees what each view keeps. Fallback sentence names the three views.
- **Images / video (optional):** Video (optional) - a 20-30 second screen recording of a real session page being scrolled - shows the real density of a long session, which sample data cannot - recorded from a deployment once the replay view is confirmed (see Watch-outs).
- **FAQ:**
  - None in the input.
- **Links to:** /integrations/claude-code, /parallel-ai-agents, /features, /blog/claude-code-session-analysis
- **Watch-outs:** MSoT Section 1 verifies My Sessions' "detailed view" and summaries; the turn-by-turn replay, segments, sub-agents shown in place and sub-agent links are not listed there: confirm with the owner before describing them as features, or describe only the detailed view and summary. The Labels tab needs AI labelling (admin). "claude code session analysis" is the built page 4.6's main keyword: secondary only, linked. Overlaps 2.9 (step record): this page is about reading a session; 2.9 is the step list without message text. Keep message text out of the sample replay too (keyword note: "structure only").

### 2.9 · Claude Code Activity Log Without Message Text

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** What the Agent Did: a Step-by-Step Record Without Message Text
- **Title tag:** Claude Code Activity Log Without Message Text | Kite Pulse
- **H1:** Claude Code Activity Log: Show Tool Calls Step by Step, Without the Message Text
- **URL:** /blog/claude-code-activity-log
- **Meta description:** A Claude Code activity log that lists each tool call in order, folds routine steps, always shows errors and leaves message text out. Try a sample.
- **Main keyword:** claude code activity log
- **Secondary keywords:**
  - claude code show tool calls → H1, and H2 "How to show tool calls in Claude Code yourself"
  - claude code tool calls → H3 "What counts as a Claude Code tool call"
  - see what ai agents are doing right now → body of H2 "From one session to the whole team", linking to the built page /blog/stuck-ai-agent
  - claude code activity monitor → H2 "An activity monitor for agents across a team"
- **Description:** For developers and team leads who want to know what an agent did without anyone reading the conversation. Ranking pages show how to make Claude Code print its tool calls in one terminal; none offers a record a lead can read that leaves the message text out. The page explains what a tool call is, how to see them yourself, why a step record without text is useful (review, handover, spotting errors), then the record in the console, reached from a session page or a desk in The Office. One Kite Pulse callout: failed tool calls are recorded for every tool except Aider. The reader leaves knowing what a step record shows and what it deliberately leaves out.
- **Interactive elements:**
  1. Sample step record - a list of sample steps (read file, edit, run command, sub-agent, failed command) with a "fold routine steps" toggle and an "errors only" filter; message text appears as "[not shown]". Fallback paragraph describes the record and the two controls.
  2. Before/after privacy toggle - the same sample session as a full transcript and as a step record, so the reader sees exactly what is removed. Fallback sentence lists what remains (step type, order, time, outcome).
- **Images / video (optional):** None - the sample record is the clearest view.
- **FAQ:**
  - How can I see what my team's AI agents are doing right now?
- **Links to:** /integrations/claude-code, /ai-agent-office, /privacy, /blog/stuck-ai-agent
- **Watch-outs:** The "What the agent did" step record is not named in MSoT Section 1: confirm before writing that it is on every session page and on Office desks. Verified around it: failed tool calls for every tool except Aider; command exit codes from Claude Code, Codex and Copilot; The Office (desk per person, markers for stuck work); Agents in parallel (admins for anyone, managers for themselves). "see what ai agents are doing right now" is the built page 3.1's main keyword: secondary only, linked. Overlaps 9.10 (/blog/ai-agent-activity-log) and 9.7: cross-link and keep this page to the step record. "Activity monitor" refers to agents, never to people (R4).

### 2.10 · AI Agent Stuck Notification: Three Bell Notices

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** Notices in the Bell: Plan Limit Reached, AI Agent Stuck and Claude Code Out of Date
- **Title tag:** AI Agent Stuck Notification: Three Bell Notices | Kite Pulse
- **H1:** AI Agent Stuck Notification, Claude Weekly Limit Reached and Out-of-Date Claude Code
- **URL:** /blog/ai-agent-stuck-notification
- **Meta description:** Three notices that need no setup: AI agent stuck notification, Claude plan limit reached and Claude Code out of date. Who gets each, and next steps.
- **Main keyword:** ai agent stuck notification
- **Secondary keywords:**
  - claude code agent stuck → H3 "When a Claude Code agent is stuck" (main keyword of 4.5: secondary here, link)
  - claude code version check → H2 "Claude Code out of date: the version check" (main keyword of 4.13: link)
  - claude weekly limit reached → H2 "Claude weekly limit reached: the plan-limit notice"
  - ai agent stuck → body of H2 "The AI agent stuck notice" (main keyword of 11.4: link), with a link to the built page /blog/is-claude-code-stuck
- **Description:** For developers and their managers who want to hear about a stuck agent, a reached limit or an old Claude Code version without watching a screen. Nothing ranks for the notice itself; pages cover Claude Code's own terminal notification for one person. The page takes each notice in turn: what triggers it, who receives it, where it appears (the bell, Needs attention, and email if the server has email set up), and what to do next. One Kite Pulse callout: admins choose who is told what on Notifications. The reader leaves knowing which notices to expect and how to route them.
- **Interactive elements:**
  1. Notice router - the reader picks a notice and a role (developer, manager, admin) and sees whether that role is told and where, with "admins can change this" shown. Fallback is a small table of notices, recipients and places.
  2. Stuck-time slider - a sample agent working on one problem; the reader drags time forward and sees where a "stuck" notice would appear, using an example threshold labelled as one the server operator can change or switch off. Fallback paragraph explains the threshold idea.
- **Images / video (optional):** None - the router and slider explain routing and timing.
- **FAQ:**
  - How do I find out if developers are on outdated versions of Claude Code?
  - How do I know when AI is retrying the same failed fix repeatedly?
  - How can I tell if a developer is about to hit their Claude usage limit?
- **Links to:** /blog/ai-retry-loops, /plan-headroom, /integrations/claude-code, /blog/is-claude-code-stuck
- **Watch-outs:** The three automatic notices come from the Field Guide only (keyword note: branch Sonia00_newfeature), not MSoT Section 1: confirm before writing, and do not state the 30-minute threshold until confirmed. Verified and usable: alerts with the in-app bell, email and a daily digest; admins choose recipients on Notifications; the Needs attention inbox; the Claude Code version check with a "version behind" filter; Plan headroom ("near" 80%, "at limit" 100%, Claude Code only); The Office markers for stuck work or plan limits. Email needs the server's mail settings (MSoT 2.1). The second FAQ answer points to Work Problems (repeated retries; admin by default) and /blog/ai-retry-loops. Claude Code waiting signals are unreleased (MSoT 2.3): leave out.

### 2.11 · What Is My Team Working On? A Dashboard View

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** Team Overview, All Developers and Organisation Overview
- **Title tag:** What Is My Team Working On? A Dashboard View | Kite Pulse
- **H1:** What Is My Team Working On? A Team Status Dashboard at Three Levels
- **URL:** /blog/what-is-my-team-working-on
- **Meta description:** A "what is my team working on" dashboard at three levels: Team Overview right now, All Developers in your scope, and Organisation Overview.
- **Main keyword:** what is my team working on dashboard
- **Secondary keywords:**
  - team status dashboard → H1, and H2 "Team Overview: a team status dashboard for right now" (main keyword of 5.1: secondary here, link)
  - engineering manager dashboard → body of H2 "All Developers: everyone in your reporting line" (main keyword of 9.12: link to /blog/engineering-manager-dashboard)
  - team availability dashboard → H3 "Who is online: a team availability dashboard without status pings"
  - team activity dashboard → body of H2 "Team Overview: a team status dashboard for right now" (main keyword of /features: link there)
- **Description:** For team leads, managers and directors who want to know what people are working on without another status meeting. Ranking pages are generic project-status tools fed by tickets; this one reads from the AI sessions themselves. The page goes level by level: Team Overview (who is online and coding now, active time and sessions today against a typical day, who needs attention, each person's current project, refreshed every 30 seconds), All Developers (everyone in your scope, each with the same report they see minus private prompt fields), and Organisation Overview with Summary and Activity Overview. One Kite Pulse callout: managers see their whole reporting line, enforced by the server. The reader leaves knowing which view answers which question, and which questions still need a conversation.
- **Interactive elements:**
  1. Three-level zoom - tabs for Team, Reporting line and Organisation over one sample company (labelled); each tab shows a small sample view, and a "today vs typical day" bar on the Team tab ticks as if refreshing. Fallback paragraph describes what each level shows.
  2. Standup question mapper - the reader ticks the questions their status meeting asks (who is blocked, what each person is on, who is away, what shipped) and gets a copyable list split into "the dashboard answers this" and "still ask a person", with blocker context in the second list. Fallback lists the default mapping.
- **Images / video (optional):** None - the zoom tabs show the three levels with sample data.
- **FAQ:**
  - How do I know what my engineering team is working on right now?
  - How can I see team activity in real time?
  - How do I see what my team is working on without status meetings?
- **Links to:** /features, /engineering-intelligence, /blog/engineering-manager-dashboard (9.12)
- **Watch-outs:** Sheet note: close to /features' main keyword "team activity dashboard"; keep the three pages in depth and link to /features. Overlaps 9.13 (team overview dashboard), 5.1 and 7.14 (status meetings): cross-link. The "roster export" on All Developers is not in MSoT Section 1: confirm before naming it. Organisation Overview is admin by default. R4: Team Overview's "Most active today" and Organisation Overview's "Top performers" exist; do not describe the pages as free of ranking, and do not use monitoring language. "Real time" in the FAQ: say "refreshes every 30 seconds", with data as fresh as each computer's last upload.

### 2.12 · Claude Code Multi-Agent Dashboard per Developer

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** The Developer Page: One Person in Full
- **Title tag:** Claude Code Multi-Agent Dashboard per Developer | Kite Pulse
- **H1:** Claude Code Multi-Agent Dashboard: Parallel Agents on the Developer Page
- **URL:** /blog/claude-code-multi-agent-dashboard
- **Meta description:** A Claude Code multi-agent dashboard on the developer page: agents and sub-agents working or waiting, a lane chart of the day, and the rest.
- **Main keyword:** claude code multi agent dashboard
- **Secondary keywords:**
  - how many parallel agents can claude code run → H2 "How many parallel agents can Claude Code run?" (outside fact: sourced, see Watch-outs)
  - claude code agent view dashboard → H3 "Claude Code's own agent view and a dashboard for a team"
  - view claude code usage → body of H2 "The rest of the developer page"
  - monitor parallel ai agents → H2 "Agents in parallel: monitor parallel AI agents through a day"
  - model usage by developer → H3 "Model usage by developer"
  - token usage per developer → body of H3 "Model usage by developer", linking to the built page /blog/token-usage-per-developer
- **Description:** For engineering managers and admins, and for developers who run several agents at once. Pages ranking today cover Anthropic's built-in agent view and single-machine tools; none shows a day of agents and sub-agents across sessions for one person. The page answers the parallel-agents question, then explains Agents in parallel (how many agents and sub-agents are working now, their state: working, waiting for the developer, waiting for permission, and a lane chart for any past day), then the rest of the developer page: the same report the person sees without private prompt fields, model and token use. One Kite Pulse callout on the lane chart. The reader leaves knowing how to read a lane chart and who can see it.
- **Interactive elements:**
  1. Lane chart scrubber - a sample day (labelled) with one lane per agent and sub-agent, coloured by state; the reader drags a time marker and sees "working now / waiting for you / waiting for permission" counts at that moment. Fallback paragraph explains lanes and states.
  2. Who-can-see-it toggle - Admin, Manager and Developer views of the sample developer page; the Agents in parallel panel shows for admins (anyone) and managers (themselves only), and private prompt fields are absent for everyone but the person. Fallback sentence states the access rules.
- **Images / video (optional):** Animation loop (optional) - a short looping SVG of lanes filling as agents start and stop - shows parallelism at a glance above the fold - inline SVG, no real data.
- **FAQ:**
  - How do I identify developers who need support or coaching with AI tools?
  - Can I see usage by individual developer without creating a surveillance problem?
- **Links to:** /engineering-intelligence, /parallel-ai-agents, /privacy, /features, /blog/token-usage-per-developer
- **Watch-outs:** Weak fit (sheet note): the keyword matches only Agents in parallel; lead with it. Access: Agents in parallel is for admins (anyone) and managers (themselves only), so a manager cannot see a report's lane chart by default; say so. Detection and Collection tabs, session labels and exports are not in MSoT Section 1: confirm before naming; labels need AI labelling. Cost per developer is admin-only. Facts about Claude Code's parallel limits and Anthropic's agent view need sources and checked dates; if none, a placeholder. Do not mention Coaching & Risk (hidden, R3); answer the coaching FAQ with Work Problems and My Scorecard insights. Competitor AgentsRoom ranks: no claims about it without a source. "token usage per developer" is the built page 2.18's main keyword: secondary only.

### 2.13 · Team Collaboration Insights, Leave and On-Call

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** Collaboration, Teams, and Leave & On-Call
- **Title tag:** Team Collaboration Insights, Leave and On-Call | Kite Pulse
- **H1:** Team Collaboration Insights That Account for Leave, On-Call and Team Changes
- **URL:** /blog/team-collaboration-insights
- **Meta description:** Team collaboration insights read fairly: shared projects and contributors, team membership with dates, and leave and on-call that explain quiet weeks.
- **Main keyword:** team collaboration insights
- **Secondary keywords:**
  - vacation tracker for teams → H2 "What Leave & On-Call records, and how it differs from a vacation tracker for teams"
  - team availability dashboard → body of H2 "Why leave and duty change how activity reads"
- **Description:** For team leads and managers who have watched a quiet week be misread. Collaboration-insight pages describe chat and meeting analytics; none deals with reading AI-coding activity fairly around leave, duty and team moves. The page covers Collaboration (projects several people work on, with contributors, shared sessions and last activity), Teams (membership with start and end dates, so history stays with the right team), and Leave & On-Call (leave, holidays and duty rotas recorded so insights do not misread them). One Kite Pulse callout on Leave & On-Call. The reader leaves with a short checklist for reading any team's activity fairly.
- **Interactive elements:**
  1. Quiet-week explainer - a six-week sample activity chart (labelled) for a small team; the reader switches on "show leave and on-call" and the dips line up with leave, a public holiday and an on-call week. Fallback paragraph explains the three causes.
  2. Team-move timeline - a sample person moves team mid-quarter; the reader toggles "membership dates on/off" and sees their history stay with the old team or jump to the new one. Fallback sentence states why dates matter.
- **Images / video (optional):** None - both widgets are sample-data charts.
- **FAQ:**
  - How do I account for leave and on-call when measuring AI usage?
- **Links to:** /features, /engineering-intelligence
- **Watch-outs:** Leave & On-Call is for context, not leave approval: say plainly (R9) that leave requests belong in the HR or leave tool. Managers edit their own line; company holidays are admin only. Teams is admin by default; Teams feed The Office, Team Review, AI Collaboration and AI Budgets, and Reports has no team filter (Website corrections). MSoT says insights do not misread leave; do not describe the exact adjustment. Main keyword of 8.12 "ai collaboration metrics" is close: cross-link /blog/ai-collaboration-metrics.

### 2.14 · Failing Commands Analytics with Work Problems

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** Work Problems, Insight Rules and the Insights Catalog
- **Title tag:** Failing Commands Analytics with Work Problems | Kite Pulse
- **H1:** Failing Commands Analytics: Repeated Errors in AI Coding Sessions, Found by Rules
- **URL:** /blog/failing-commands-analytics
- **Meta description:** Failing commands analytics for AI coding sessions: how fixed rules find failed commands, errors and repeated retries, and what to do about each.
- **Main keyword:** failing commands analytics
- **Secondary keywords:**
  - repeated errors in ai coding sessions → H1, and H2 "Repeated errors in AI coding sessions: what the rules look for" (main keyword of 3.3: secondary here, link)
  - ai coding error rate → H3 "Why one AI coding error rate misleads"
  - blocker board engineering → H2 "From one session's errors to the Blocker Board" (main keyword of 8.11: link to /blog/blocker-board-engineering)
  - recurring engineering blockers → body of H2 "From one session's errors to the Blocker Board" (main keyword of 5.5: link)
- **Description:** For team leads and platform owners who suspect time is lost to the same failing build or test. Error-analytics pages cover CI pipelines; nothing covers the commands an AI agent runs and re-runs inside a session. The page explains what counts as a failed command, an error message and a repeated retry, why a single error rate hides the pattern, how severity grouping and suggested actions help, how thresholds are tuned, and how team-level causes reach the Blocker Board. One Kite Pulse callout: Work Problems uses fixed rules and no AI. The reader leaves able to spot a retry loop and with a list of first fixes to try.
- **Interactive elements:**
  1. Sample command log - twenty sample commands (labelled) with exit codes; the reader toggles "group by severity" and "show repeated retries", and each group shows an example suggested action. Fallback paragraph defines failed command, error and retry loop.
  2. Threshold tuner - a slider for how many retries count as a loop, over the same sample log, showing how many items get flagged; labelled as an example of the thresholds admins set in Detection Rules. Fallback sentence explains the trade-off between missed loops and noise.
- **Images / video (optional):** None - the sample log shows the pattern.
- **FAQ:**
  - How do I know when AI is retrying the same failed fix repeatedly?
  - How do I spot developers who are stuck in long AI sessions?
- **Links to:** /features, /blog/ai-retry-loops, /engineering-intelligence, /blog/blocker-board-engineering (8.11)
- **Watch-outs:** "Insight Rules" and "Insights Catalog" are not in MSoT Section 1; the verified control is Detection Rules (thresholds for spotting problems without AI): use that name unless the owner confirms the others. Work Problems is admin by default and lists "the most affected developers": describe it as finding where help is needed, not as ranking (R4). Command exit codes come from Claude Code, Codex and Copilot only; failed tool calls from every tool except Aider. Blocker Board is admin by default, team-level, and never names a single person. Overlap with /blog/ai-retry-loops and 3.3, 3.14, 7.6.

### 2.15 · Developer Pain Points: Where Work Repeats

- **Category · intent · page type:** Features and Capabilities · Informational · Interactive guide
- **Plan title:** Workflows & Pain Points: Where Work Repeats and Where It Slows Down
- **Title tag:** Developer Pain Points: Where Work Repeats | Kite Pulse
- **H1:** Developer Pain Points and Developer Friction: Where Work Repeats and Slows Down
- **URL:** /blog/developer-pain-points
- **Meta description:** Find developer pain points in AI coding sessions: repeated prompts and commands, long sessions and recurring blockers, plus a self-check to run.
- **Main keyword:** developer pain points
- **Secondary keywords:**
  - developer friction → H1, and H2 "Developer friction you can see in session data" (main keyword of 12.9: secondary here, link)
  - recurring engineering blockers → H3 "Recurring engineering blockers" (main keyword of 5.5: link)
  - find repeated prompts in claude code → H2 "How to find repeated prompts in Claude Code by hand"
  - software developer pain points → body of the short answer ("software developer pain points from surveys and from sessions")
- **Description:** For engineering managers and DevEx leads. Pages ranking for developer pain points are survey round-ups; they report what people say, not where sessions repeat or slow down. The guide goes from the usual survey list, to the signals sessions do show (repeated prompts and commands, very long sessions, repeated failures, the same problem solved twice), to how to find repeated prompts by hand, to turning a repeated workflow into a Claude Code skill. One Kite Pulse callout on Workflows & Pain Points and Skill Candidates (draft skills built by rules from repeated workflows, for a person to approve). The reader leaves with a self-check result and a copyable list of next steps.
- **Interactive elements:**
  1. Pain-point self-check - eight statements the reader ticks (e.g. "the same setup prompt is typed every day", "builds fail the same way twice a week"); the result groups them into repeats, slow-downs and stuck work, each with a next step and the data that would confirm it, copyable. Fallback lists the eight statements and the three groups.
  2. Repeated-prompt grouper - a list of sample prompts (labelled); the reader presses "group similar" and look-alike prompts cluster, with a "this could be a skill" note on the largest group. Fallback paragraph explains grouping by hand.
- **Images / video (optional):** None - the self-check and grouper carry the method.
- **FAQ:**
  - How do I spot developers who are stuck in long AI sessions?
  - How do I stop my team solving the same bug twice?
- **Links to:** /blog/developer-experience-metrics, /skill-candidates, /engineering-intelligence, /blog/ai-retry-loops, /blog/developer-experience-without-surveys
- **Watch-outs:** MSoT Section 1 names Workflows & Pain Points (admin by default, grantable to managers) without listing its contents: the card's hot files, stuck weeks, inefficiencies and quality checks need confirming before naming. Verified for the second FAQ: Session Graph (links look-alike sessions) and Knowledge Records (only once the knowledge label list is approved and has run). Skill Candidates use no AI model. Private prompt statistics are visible only to the developer, so a manager-facing "repeated prompts" claim must be checked with the owner. "measure developer experience without surveys" belongs to the built page 6.1: link it. /blog/developer-experience-metrics is the existing target for this keyword as a secondary: cross-link.

### 2.16 · Project Health Dashboard: All Projects View

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** All Projects and the Project Page
- **Title tag:** Project Health Dashboard: All Projects View | Kite Pulse
- **H1:** Project Health Dashboard: Active, Stable or Dormant, with a Project Health Status Report
- **URL:** /blog/project-health-dashboard
- **Meta description:** A project health dashboard built from AI coding sessions: active, stable or dormant, contributors, last activity and a summary card per project.
- **Main keyword:** project health dashboard
- **Secondary keywords:**
  - project health status dashboard → H2 "Project health status dashboard: what active, stable and dormant mean"
  - project health status report → H1, and H3 "Turning the page into a project health status report"
  - engineering project tracking ai → H2 "Engineering project tracking with AI session data: what it shows and what it misses"
  - ai coding agent cost per repo → H3 "AI coding agent cost per repo: tokens by project, dollars in AI Budgets", linking to the built page /blog/ai-cost-per-project-agencies
- **Description:** For engineering managers who want the state of every project at a glance. Project-health pages are PMO templates fed by status updates; this one is built from the work itself. Sections: the three health states and the columns on All Projects (sessions, contributors, last activity); the project page and its summary card (stability, tokens, phase, open blockers, duplicate work, knowledge records); what session data cannot tell you (deadlines, scope, ticket status, where a tracker fits better, R9); how to turn it into a short status report. One Kite Pulse callout on the summary card. The reader leaves with a copyable status-report paragraph built from sample data.
- **Interactive elements:**
  1. Sample project table - eight sample projects (labelled) filterable by health and sortable by sessions or last activity. Fallback paragraph defines the three health states.
  2. Status-report generator - the reader picks a sample project and gets a copyable status paragraph from its summary card; an "AI labelling off" toggle greys out phase, blockers and duplicate work to show what is available without it. Fallback lists the summary-card fields and which need AI labelling.
- **Images / video (optional):** None - the table and generator use sample data.
- **FAQ:**
  - How do I find out which projects my team uses AI on the most?
- **Links to:** /features, /engineering-intelligence, /ai-cost-tracking, /blog/ai-cost-per-project-agencies
- **Watch-outs:** Phase, risk, open blockers and duplicate work appear only when AI labelling is switched on (card); knowledge records only once the knowledge label list is approved and has run. Cost per project appears only in AI Budgets (month to date, priced tools only, unpriced tokens reported separately); token use per project is on Team AI Usage's Projects tab (the FAQ answer). The thresholds behind active, stable and dormant are not in the MSoT: do not state them. "ai cost per project" belongs to the built page 12.1: link it. Overlaps 7.10 (project status tracking tool): cross-link.

### 2.22 · Shared AI Tool Accounts and Who Uses Them

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** Tool Accounts: Shared, Separate and Personal Accounts
- **Title tag:** Shared AI Tool Accounts and Who Uses Them | Kite Pulse
- **H1:** Shared AI Tool Accounts: How to Detect Shared Claude Accounts and Personal Sign-ins
- **URL:** /blog/shared-ai-tool-accounts
- **Meta description:** Find shared AI tool accounts: how Tool Accounts marks accounts used by more than one person, with plan tier and email domain, addresses hashed.
- **Main keyword:** shared ai tool accounts
- **Secondary keywords:**
  - detect shared claude accounts → H1, and H2 "How to detect shared Claude accounts"
  - claude code seat tier per developer → H3 "Claude Code seat tier per developer"
  - claude code multiple accounts → H3 "One developer, multiple Claude Code accounts"
  - github copilot shared account → H3 "GitHub Copilot: a hashed account number only"
- **Description:** For finance, procurement and admins who pay for seats and suspect logins are shared or personal accounts are in use. Pages ranking today cover vendor seat rules and SaaS-management tools; none shows what the AI coding tools' own session records reveal about accounts. The page explains why sharing happens, how Tool Accounts counts separate signed-in accounts per tool and marks those used by more than one person "Shared", what plan tier, machines, last seen and email domain add, and what the hashing means for privacy. One Kite Pulse callout: accounts are sent as a keyed hash, the email domain and the plan name, never the address. The reader leaves able to tell a shared login from one person on two laptops.
- **Interactive elements:**
  1. Sample accounts table - sample accounts (labelled, hashed ids) for five tools, filterable by tool and "Shared"; clicking a row shows machines, last seen, plan tier and email domain. Fallback paragraph lists the columns.
  2. "Shared or not?" scenario check - four short scenarios (one person on two laptops, two people on one login, a personal email domain, an account last seen two months ago); the reader picks an answer and sees the explanation. Fallback lists the scenarios and answers.
- **Images / video (optional):** None - the sample table shows the view.
- **FAQ:**
  - How do I know if developers are sharing AI tool accounts?
  - Are developers using company-approved AI tools or personal accounts?
  - How can I find shared or unused AI tool accounts?
- **Links to:** /shadow-ai, /integrations/github-copilot, /privacy, /blog/cursor-shared-account
- **Watch-outs:** Tool Accounts works for Claude Code, Codex, Cursor, OpenCode and GitHub Copilot; the email domain covers four of them (not Copilot); Copilot shows a hashed account number only. Admin by default. Full addresses need a server setting with no console control (MSoT 2.1): do not offer them. Copilot plan name appears only when its optional read is on (admin). The second FAQ answer must stay inside the shadow-AI limits (R8): only switched-on tools are read; no detection of tools the organisation has not switched on. "cursor shared account" belongs to the built page 3.6: link it. Sheet note: link /shadow-ai rather than repeat it.

### 2.23 · AI Coding Seat Cost Tracking per Tool

- **Category · intent · page type:** Features and Capabilities · Commercial · Interactive guide
- **Plan title:** Hourly Rates & Seat Prices
- **Title tag:** AI Coding Seat Cost Tracking per Tool | Kite Pulse
- **H1:** AI Coding Seat Cost Tracking: Track AI Subscriptions in Engineering Beside Token Estimates
- **URL:** /blog/ai-coding-seat-cost-tracking
- **Meta description:** AI coding seat cost tracking: record what each tool's seats cost, set them beside token estimates, and see which seats are used. With a calculator.
- **Main keyword:** ai coding seat cost tracking
- **Secondary keywords:**
  - track ai subscriptions engineering → H1, and H2 "How to track AI subscriptions in engineering without one spreadsheet per tool"
  - ai seat cost optimization → H2 "AI seat cost optimization: seats against actual use"
  - copilot business cost per seat → H3 "Copilot Business cost per seat: an example entry" (vendor price sourced, see Watch-outs)
- **Description:** For finance and admins who pay for seats on several AI coding tools and cannot see them together. Ranking pages are vendor price lists and SaaS-spend tools; none puts seat prices beside what the tools' own sessions show. The guide covers why seat cost and token cost are different figures, how to record seat prices per tool, how to compare seats with use (Tool Accounts' last seen, Team AI Usage), and how to treat seat cost when a tool shows no token price. One Kite Pulse callout: admins enter each tool's seat price on Hourly Rates & Seat Prices, and seat prices then appear on the Team AI Usage Overview for admins. The reader leaves with a seat-versus-use worksheet to copy.
- **Interactive elements:**
  1. Seats-versus-use calculator - sample tools with example seat prices and sample seat counts; the reader edits seats and "active in the last 30 days" and sees monthly seat spend and idle seats per tool, never summed with token estimates. Fallback paragraph gives the arithmetic in words.
  2. Dated price ledger - the reader adds a price change with a date to a sample tool and sees earlier months keep the earlier price. Fallback sentence explains why a dated price matters for comparisons.
- **Images / video (optional):** None - the calculator is the point of the page.
- **FAQ:**
  - How much does AI coding assistance cost per developer?
- **Links to:** /ai-cost-tracking, /ai-coding-assistant-pricing, /shadow-ai, /blog/ai-coding-cost-per-developer
- **Watch-outs:** MSoT 1.2 verifies only that admins enter seat prices per tool and that they appear on the Team AI Usage Overview for admins. Hourly rates per role level: their only described use is the Waste panel on the hidden Cost & ROI page (R3, MSoT 2.2), so do not promote hourly-rate figures or any ROI. "Each entry is dated and recorded" is verified for token list prices, not stated for seat prices: confirm (the Audit Log records admin changes). Copilot Business and any other vendor price need a source URL and checked date in the data file, or a placeholder. The FAQ answer: cost per developer is admin-only, an estimate, and linked to the built page 2.19.

### 2.24 · Claude Code Tokens per Second: How to Measure

- **Category · intent · page type:** Features and Capabilities · Informational · Blog post
- **Plan title:** Generation Rate: How Fast AI Replies Arrive
- **Title tag:** Claude Code Tokens per Second: How to Measure | Kite Pulse
- **H1:** Claude Code Tokens per Second: How Fast Is Claude Code, and How to Measure It
- **URL:** /blog/claude-code-tokens-per-second
- **Meta description:** Claude Code tokens per second explained: how generation rate is measured from request timing, what changes it, and a calculator for your own logs.
- **Main keyword:** claude code tokens per second
- **Secondary keywords:**
  - claude code show tokens per second → H2 "How to show tokens per second for Claude Code yourself"
  - claude code average tokens per second → H3 "Claude Code average tokens per second: why one average hides the spread"
  - how fast is claude code → H1, and H2 "How fast is Claude Code? What decides the speed"
  - claude code model usage → H3 "Claude Code model usage and speed settings" (Models tab: effort level and speed settings)
  - claude code session analytics → body of H2 "Where generation rate fits in session analytics", linking to the built page /blog/claude-code-session-analysis
- **Description:** For technology leaders and DevEx teams who hear "it feels slow" and want a number. One competitor dominates this search with a one-off measurement of its own sessions; this page explains the method instead: what tokens per second measures, why waiting time and time to first token must be separated, what changes the rate (model, output length, effort and speed settings, load), and how to work it out from your own logs. Kite Pulse appears once, as a "coming soon" note: generation rate for Claude Code, opted into by each developer. The reader leaves able to measure and compare speed honestly.
- **Interactive elements:**
  1. Rate calculator - the reader enters output tokens and seconds for a few of their own replies (or loads a labelled sample) and sees tokens per second for each and the spread, with time to first token kept separate. Fallback paragraph gives the formula: output tokens divided by generation time.
  2. Stream illustration - a short animation of tokens arriving at two illustrative rates with the same output length, so the reader sees how a delay before the first token changes the felt speed; labelled "illustration, not a measurement". Fallback sentence describes the effect.
- **Images / video (optional):** None - the calculator and animation carry it.
- **FAQ:**
  - None in the input.
- **Links to:** /integrations/claude-code, /features, /blog/claude-code-session-analysis
- **Watch-outs:** Generation rate (request timing) is Partial in MSoT 2.3: collector code (0.4.2) and the per-tool switch exist, but the developer opts in only by editing a config file, with no tray or console control. So the page must not present per-session or per-team rates as a current feature; "coming soon" at most, Claude Code only. The card's "shown on session pages and in usage sections" is not verified. Verified and usable: the Models tab shows Claude Code effort-level and speed settings. No invented speed figures (R2); the competitor's numbers, if cited, need source and checked date.

### 2.25 · Claude Code Skills Used Across a Team

- **Category · intent · page type:** Features and Capabilities · Commercial · How-to
- **Plan title:** Agent Setup: Claude Code Skills, Commands, Agents and MCP Servers Across the Team
- **Title tag:** Claude Code Skills Used Across a Team | Kite Pulse
- **H1:** Claude Code Skills Used Across a Team: Skills, Commands and an MCP Server Inventory
- **URL:** /blog/claude-code-skills-used-across-team
- **Meta description:** Claude Code skills used across a team: which skills, commands, agents and MCP servers are installed, which ones sessions call, and an inventory.
- **Main keyword:** claude code skills used across team
- **Secondary keywords:**
  - mcp servers installed across team → H2 "MCP servers installed across team machines, against the MCP tools sessions call"
  - claude code list installed skills → H3 "Claude Code: list installed skills on one machine"
  - mcp server inventory → H1, and H2 "Building an MCP server inventory"
  - claude code mcp usage → H3 "Claude Code MCP usage in sessions"
- **Description:** For DevEx and platform teams who have rolled out skills and MCP servers and want to know what is used. Nothing ranks for a team view; pages explain how to install skills on one machine. The how-to shows how to list installed skills, commands, agents and MCP servers on one machine, how to collect that into a team inventory by hand, and how to compare it with what sessions call (sub-agents, MCP tools, plan mode). One Kite Pulse callout: an optional read (an admin switch) collects the installed set from each machine, and the Agent features tab shows which features sessions used. The reader leaves with a copyable inventory template and a list of installed-but-unused items to review.
- **Interactive elements:**
  1. Installed-versus-used matrix - a sample team of six machines (labelled); rows are skills and MCP servers, columns show machines installed and sessions using; a filter shows "installed but unused". Fallback paragraph explains the two counts.
  2. Inventory template builder - the reader types their own skill and MCP server names (kept in the page only) and gets a copyable table with owner, purpose and last-used columns. Fallback shows the empty template.
- **Images / video (optional):** None - the matrix shows the comparison with sample data.
- **FAQ:**
  - Which Claude Code features (sub-agents, plan mode, MCP tools) does my team use?
- **Links to:** /integrations/claude-code, /parallel-ai-agents, /skill-candidates, /docs, /blog/claude-code-agent-features-usage
- **Watch-outs:** The installed-set read is optional and off until an admin turns it on (Settings › Retention › Kite Pulse app reads, app 0.4.2; plugins need app 0.4.3, confirm it is published). The "Agent Setup" side-by-side view is from the Field Guide only (keyword note), not MSoT Section 1: confirm before describing it as one page. Verified: the Agent features tab (sub-agents, background commands, plan mode, worktrees, MCP tools, by session and developer). The FAQ is the built page 5.13's subject: answer briefly and link to /blog/claude-code-agent-features-usage. Do not confuse this with Kite Pulse's own MCP server, which is "available when enabled" only (R8).

### 2.28 · Scheduled Engineering Reports by Email

- **Category · intent · page type:** Features and Capabilities · Commercial · How-to
- **Plan title:** Company Reports and Scheduled Reports
- **Title tag:** Scheduled Engineering Reports by Email | Kite Pulse
- **H1:** Scheduled Engineering Reports by Email: a Weekly Engineering Report as PDF or CSV
- **URL:** /blog/scheduled-engineering-reports
- **Meta description:** Set up scheduled engineering reports by email: a company report compared with the last period, sent daily, weekly or monthly as PDF or CSV.
- **Main keyword:** scheduled engineering reports email
- **Secondary keywords:**
  - weekly engineering report → H1, and H2 "What a weekly engineering report should answer" (main keyword of 3.11: secondary here, link)
  - monthly engineering report → H3 "Monthly engineering report: comparing with the previous period" (main keyword of 11.10: link)
  - ai usage report pdf → H3 "AI usage report PDF or CSV: which format for whom"
  - company ai usage report → body of H2 "The Company report", linking to the built page /blog/company-ai-usage-report
- **Description:** For engineering managers and leadership who want the same figures every week without asking. Pages ranking today are report templates to fill by hand; this explains what an automated report should contain and how to schedule one. Steps: decide the audience and period, pick the Company report or one developer's report, choose daily, weekly or monthly and PDF or CSV, preview it, then check the send history. One Kite Pulse callout: scheduled reports with preview and send history, set up by admins, with email configured on the server. The reader leaves with a copyable schedule plan.
- **Interactive elements:**
  1. Schedule builder - the reader picks report (Company or one developer), frequency, format and audience, and gets a sample preview summary plus a copyable plan; a note shows "needs email set up on the server". Fallback lists the choices.
  2. Period comparison toggle - a sample Company report (labelled) switches between this period, the previous one and the change between them. Fallback paragraph explains the comparison.
- **Images / video (optional):** Image (optional) - the first page of a real Company report PDF - shows readers what lands in the inbox, which sample HTML cannot reproduce exactly - taken from a deployment (MSoT 2.5 caption: tools shown depend on that deployment).
- **FAQ:**
  - How do I create a weekly AI usage report for my team?
  - Can I export reports or integrate the data with our existing analytics and finance systems?
- **Links to:** /reports, /blog/ai-weekly-team-report, /features, /blog/company-ai-usage-report
- **Watch-outs:** Email features need the server's mail settings (MSoT 2.1). Downloads and schedules are admin by default. Reports have no team filter (Website corrections): the first FAQ answer must not promise a per-team report. Exports: Company report as CSV or PDF, Plan usage report as Excel; the Agent API is "available when enabled" only, never default (R8). Overlaps 13.18 (scheduled email reports), 3.11 and 11.10: cross-link; "company ai usage report" belongs to the built page 5.12.

### 2.29 · Role-Based Access Control Dashboard for AI Data

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** Who Sees What: Roles & Permissions, Accounts and Sign-in
- **Title tag:** Role-Based Access Control Dashboard for AI Data | Kite Pulse
- **H1:** Role-Based Access Control Dashboard: Who Sees What in Developer Analytics
- **URL:** /blog/role-based-access-control-dashboard
- **Meta description:** How a role-based access control dashboard works for AI coding data: three roles, a per-page permissions grid, sign-up modes and sign-in rules.
- **Main keyword:** role based access control dashboard
- **Secondary keywords:**
  - custom rbac roles → H3 "Custom RBAC roles: defined on the grid, not yet assignable"
  - developer analytics security → H2 "Developer analytics security: sign-in rules and lockout" (main keyword of 10.17: secondary here, link)
  - pseudonymised developer analytics → body of H2 "What each role can see" (tool accounts as a keyed hash; private prompt fields)
- **Description:** For admins and IT staff setting up access before rollout. RBAC pages are generic identity-provider guides; this applies roles to analytics about people's work, where who-sees-what matters most. Sections: the three access roles (Admin, Manager, Developer) and manager scope enforced by the server; the Roles & Permissions grid; Accounts & Roles and delegating account management to a manager; the three sign-up modes; sign-in rules (password rules, lockout, session length, first sign-in change). One Kite Pulse callout on server-enforced scope. The reader leaves with a role plan for their own team.
- **Interactive elements:**
  1. Permissions grid explorer - a sample grid of pages by role; the reader switches view or edit for the Manager role and sees the sample menu change. Fallback paragraph states the three roles and the grid in words.
  2. Sign-up mode chooser - the reader answers two questions (who creates accounts, do you have a company email domain) and sees which of the three modes fits, with a short flow for it. Fallback lists the three modes.
- **Images / video (optional):** None - the grid explorer shows the controls.
- **FAQ:**
  - How does role-based access work in developer analytics tools?
  - Can I control who can access individual-level usage data and organization-wide reports?
  - Does AI coding analytics support sign-up by company email domain?
  - Can my manager see everything I type to the AI?
  - Can managers see developers' AI prompts?
- **Links to:** /security, /features, /privacy
- **Watch-outs:** No SSO and no two-factor sign-in (R8, sheet note): do not mention SSO at all. Custom roles can be defined on the grid but cannot yet be assigned to accounts: say so in the H3. Password rules apply to passwords people choose; lockout after 10 wrong passwords in 15 minutes, network address after 20; sessions 2 hours or 7 days with "Keep me signed in". Manager scope includes indirect reports. "Pseudonymised" applies to tool accounts only. The last two FAQ answers: prompt statistics are private to the developer; do not claim managers cannot see session content. Absorbs 1.10. Overlaps 13.9 (roles and permissions dashboard): cross-link.

### 2.31 · Audit Log for Admin Actions, Export and Erase

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** Data Rights: Export, Erase, Audit Log and Retention
- **Title tag:** Audit Log for Admin Actions, Export and Erase | Kite Pulse
- **H1:** Audit Log for Admin Actions, Data Export, Erase and Retention in Developer Analytics
- **URL:** /blog/audit-log-for-admin-actions
- **Meta description:** What an audit log for admin actions records, what export and erase do to one person's data, and how retention is set. With a checklist to copy.
- **Main keyword:** audit log for admin actions
- **Secondary keywords:**
  - developer analytics security → H2 "Developer analytics security: what the audit log records" (main keyword of 10.17: secondary here, link)
  - privacy preserving analytics → H3 "Where privacy preserving analytics meets data rights" (main keyword of 6.6: link to /blog/privacy-preserving-analytics)
- **Description:** For admins and data-protection officers who must answer "who did what, what did you keep, and can you remove it". Pages ranking for audit logs describe generic SaaS audit trails; none says honestly what erase leaves behind. Sections: the Audit Log (sign-ins, failed sign-ins, lockouts and over 100 kinds of admin change, read-only, filterable), export of one person's data, erase and exactly what it does, retention windows and when deletion actually runs. One Kite Pulse callout: export and erase are both recorded in the audit log. The reader leaves with a copyable data-rights checklist.
- **Interactive elements:**
  1. Erase simulator - a sample person's data shown as items (account, raw activity records, encryption keys, encrypted uploads, plain-text working copies, audit entries); the reader presses Erase and sees each outcome: anonymised, deleted, destroyed, unreadable, stays, kept. Fallback is the same list as a table.
  2. Retention timeline - sliders for raw content, derived data and audit history (default 365 days shown) with a visible banner that deletion applies only once the server operator enables it. Fallback paragraph states the rule.
  3. Data-rights checklist - a copyable list generated from the reader's answers (who handles requests, retention periods chosen, whether deletion is enabled on the server). Fallback shows the default list.
- **Images / video (optional):** None - the simulator is clearer than a screenshot.
- **FAQ:**
  - Is AI coding analytics GDPR compliant and can we erase a person's data?
  - Can we configure how long developer analytics data is retained?
  - Does AI coding analytics include an audit log of admin actions?
- **Links to:** /security, /privacy, /self-hosted, /blog/privacy-preserving-analytics (6.6)
- **Watch-outs:** Erase is partial (MSoT 2.3): it anonymises the account, deletes raw activity records and destroys encryption keys; plain-text working copies stay on the server. Never write "all their data is deleted" (R6). Retention: "set how long data is kept"; deletion runs once the server operator enables it; plan-usage history and agent request logs are trimmed automatically. The Audit Log is kept indefinitely by default, 365 days once deletion is enabled. The GDPR FAQ answer must not claim compliance or any certification (R8): describe the tools and say compliance depends on how the team runs them. Encryption at rest is not claimed.

### 2.32 · Credential Leak Detection in AI Chats

- **Category · intent · page type:** Features and Capabilities · Commercial · Blog post
- **Plan title:** Leaked Credentials and Security Watch
- **Title tag:** Credential Leak Detection in AI Chats | Kite Pulse
- **H1:** Credential Leak Detection in AI Chats: How Keys Get In, and How to Mask and Track Them
- **URL:** /blog/credential-leak-detection
- **Meta description:** Credential leak detection for AI coding chats: why keys end up in prompts, how masking works before upload, and how to track a found key to rotation.
- **Main keyword:** credential leak detection
- **Secondary keywords:**
  - ai secret scanning → body of H2 "Masking before upload", linking to the built page /blog/ai-secret-scanning
  - leaked credentials in ai chats → H2 "How leaked credentials in AI chats happen" (main keyword of 11.15: secondary here, link)
  - redact secrets in ai chat history → H2 "How to redact secrets in AI chat history on your own machine" (main keyword of 10.11: link)
  - redact secrets from claude code logs → H3 "Redact secrets from Claude Code logs"
- **Description:** For security teams and admins. Ranking pages are secret-scanner products for repositories; AI chat history is a newer place for keys to land. The page covers how keys get into AI chats (pasted errors, .env reads, connection strings), how to find and redact them in local history by hand, how masking before upload works, and what to do when a key is found: rotate, revoke, record a status. One Kite Pulse callout: 36 credential patterns masked on the computer and again on the server, with a Leaked Credentials page where an admin tracks the status of each found key. The reader leaves with a copyable response checklist.
- **Interactive elements:**
  1. Spot-the-secret check - six sample session snippets with obviously fake values; the reader clicks what should be masked and sees which category it falls in (cloud key, GitHub token, private key, password in a URL). Fallback paragraph lists the categories.
  2. Key response checklist - the reader picks the key type and where it was found and gets a copyable list (rotate, revoke, check the provider's usage log, record the status). Fallback shows the general checklist.
- **Images / video (optional):** None - the check and checklist carry the page.
- **FAQ:**
  - How do I find passwords or API keys leaked in AI chats?
  - How do I detect secrets or API keys pasted into AI tools?
- **Links to:** /blog/secrets-in-ai-prompts, /shadow-ai, /security, /privacy, /blog/ai-secret-scanning
- **Watch-outs:** The Leaked Credentials page is Partial (MSoT 2.1): it fills only after a server operator runs a command-line scan; there is no automatic scan, and status is set by hand, not checked with the provider. R8 forbids "automatic leaked-credential scanning": describe the page only with that limit, or leave it out. The card's "Security Watch" items (sensitive changes nobody checked, pasted personal data) are not in MSoT Section 1 and need AI labelling: leave out until confirmed. Masking wording: "masked", never "removed"; for Cursor and OpenCode chat text, on the server only. "ai secret scanning" is the built page 6.10's main keyword: secondary only, and the two pages overlap heavily, as do 1.3, 3.10, 10.11, 11.15 and /blog/secrets-in-ai-prompts (existing target).

