# Kite Pulse - Article Production Plan, Categories 10-13

Draft for review, 4 November 2026. 34 articles (10.7 to 13.18): the category 10-13
articles marked "separate article" in `Kite Pulse - Article Keyword Map.xlsx`, minus
the ones already built (10.5, 10.6, 11.2, 11.5, 12.1, 12.4, 12.10). Built pages are
matched on the main keyword each one targets in the sheet's Page Map, not on its
file name.

Each entry gives the SEO title (main keyword first, at most 60 characters with
" | Kite Pulse"), H1, URL, meta description (at most 155 characters), where each
secondary keyword goes, a short description of how the article is built, its 1-3
interactive elements, optional images or video (only where they add something a
widget cannot), FAQs, links and watch-outs. Product facts follow the Master Source
of Truth and the rules in `MASTER-PROMPT.md`. Nothing here is written article copy.

Entries carry a **Section** line where the article belongs outside the Blog. In this
batch:

| Section | Articles |
|---|---|
| Integrations | 10.13 Jira and other connectors, 10.14 user sync with Entra ID and Okta |
| Solutions | 12.2, 12.3, 12.5, 12.6, 12.7, 12.8, 12.9 (one page per industry or team shape, beside the role pages) |
| Guides & tools | 11.1, 11.8, 13.1, 13.16 |
| Help (Docs) | 10.7, 10.12, 13.3, 13.8, 13.9, 13.12, 13.13, 13.18 |
| Blog | the other 13 |

The Agent API and MCP server are "available when enabled" (MASTER-PROMPT R8): every
entry that depends on them says so.

---

### 10.7 · Engineering Metrics API for AI Agents: Agent Keys

- **Category · intent · page type:** External API Access and Integrations · Commercial · Docs page
- **Section:** Help (Docs)
- **Plan title:** Agent API Keys: Letting Your Own AI Assistant Ask Kite Pulse
- **Title tag:** Engineering Metrics API for AI Agents | Kite Pulse
- **H1:** Engineering Metrics API for AI Agents: Agent Keys, Scopes and What a Key Can Read
- **URL:** /docs/agent-api
- **Meta description:** An engineering metrics API for AI agents, available when enabled: admin-issued keys, scopes and expiry, and why a key never sees more than its owner.
- **Main keyword:** engineering metrics api for ai agents
- **Secondary keywords:**
  - read only mcp server → H2 "Read-only access over the MCP server" (main keyword of 10.9, which the map merges into a page: no link of its own; link /how-to-connect-claude-code-to-mcp for setup)
  - role based access control dashboard → body of H2 "A key never sees more than its owner" (main keyword of 2.29: link /blog/role-based-access-control-dashboard)
  - audit log for admin actions → H3 "Keys in the Audit Log" (main keyword of 2.31: link /blog/audit-log-for-admin-actions)
- **Description:** For admins and security reviewers deciding whether to switch the Agent API on. Pages ranking for analytics APIs describe a vendor's hosted endpoint; this one explains a key that reads a server the team runs and is bounded by its owner's access. Written as a plain Docs page: what it is and that it is off on a standard install, how an admin issues a key (per person, scopes, expiry 90 days by default and 365 at most, IP and project limits, rate limit, monthly budget, rotation, revocation), what a key may read (never more than its owner, checked again on every request), chat mode versus direct mode, where developers see and revoke their own keys (Me › Account › API Keys), and what is never offered (prompt text and AI replies over MCP). A closing "Limits" section lists what the reader cannot do with it. The one Kite Pulse callout sits at "A key never sees more than its owner". The reader leaves knowing what switching it on involves and what a key could reach.
- **Interactive elements:**
  1. Key builder - the reader picks the key owner's role (Developer, Manager, Admin), the mode (chat or direct), an expiry and an optional project limit, and sees what that sample key could read and what it could not, with chat mode showing how little a non-admin key gets. Fallback is a table of role × mode → readable data.
  2. Request checker - three sample requests ("my usage this month", "my team's sessions", "another team's sessions") run against the sample key and come back allowed or refused, with the reason in words. Fallback paragraph states the rule.
- **Images / video (optional):** One screenshot of the issue-key dialog, only from a deployment where the operator has switched the Agent API on, dated (MSoT 2.5); otherwise none.
- **FAQ:**
  - Is there an API or MCP server for engineering analytics?
  - Can a developer see and revoke the keys issued to them? (suggested; confirm with the keyword owner)
  - What does the server operator have to change to switch the Agent API on? (suggested; confirm with the keyword owner)
- **Links to:** /docs, /security, /blog/role-based-access-control-dashboard, /blog/audit-log-for-admin-actions, /docs/mcp-dry-run, /how-to-connect-claude-code-to-mcp
- **Watch-outs:** MSoT 2.1 "needs operator setup": the Agent API and MCP server are off on a standard install, and the operator must set two server settings (KITE_PULSE_AGENT_API_ENABLED and KITE_PULSE_API_KEY_PEPPER; the second is not in the install scripts or setup docs). Say "available when enabled" in the first paragraph and never present it as a default feature (R8). Whether installs switch it on is an open owner decision (MSoT "Owner decisions"): the page may need to wait for it. Chat mode: `ask` needs a separate Agent API AI key and, by default, an admin-only permission, so a non-admin's chat-mode key can only call whoami and my_usage; do not imply chat mode lets anyone ask anything. Say "about 115 read tools" (MSoT 2.1); the Field Guide's 115 + 3 chat + 11 write split is not in MSoT, and the agent guide's tool list is older than the code. Write tools only as "optional write tools with a preview (dry run)" in direct mode (MSoT 2.1 wording); Brain writes are out (R3). That key issues and revocations appear in the Audit Log is Field Guide only (MSoT 1.6 says "admin changes"): confirm.

### 10.10 · Engineering Manager Developer Productivity AI

- **Category · intent · page type:** External API Access and Integrations · Commercial · Blog post
- **Plan title:** Questions Your AI Assistant Can Answer About Engineering
- **Title tag:** Engineering Manager Developer Productivity AI | Kite Pulse
- **H1:** Engineering Manager Developer Productivity with AI: Questions Your Assistant Can Answer
- **URL:** /blog/engineering-manager-developer-productivity-ai
- **Meta description:** Engineering manager developer productivity with AI: the questions an assistant can answer from your team's session data, and what each answer needs.
- **Main keyword:** engineering manager developer productivity ai
- **Secondary keywords:**
  - blocker board engineering → H3 "What keeps slowing the team down?" (main keyword of 8.11: link /blog/blocker-board-engineering)
  - bug fix vs feature work ratio → H2 "How much time goes to bug fixing versus new features?"
  - ai session success rate → H3 "How often do AI sessions succeed?" (main keyword of 5.8: link /blog/ai-session-success-rate)
  - engineering metrics api for ai agents → body of H2 "How the assistant gets its answers" (main keyword of 10.7: link /docs/agent-api)
- **Description:** For engineering managers who already work inside Claude Code, Cursor or VS Code and would rather ask than open a dashboard. Pages on this keyword discuss AI and developer productivity in general; none shows which questions a manager can put to an assistant about their own team's sessions, and what each answer depends on. The article is a list of questions in groups (the team's week, where time goes by type of work, failure rates per project, Claude plan pressure over past weeks, the most expensive sessions per tool), each with what data answers it, what it needs (AI labelling, direct access, an optional read) and which console page answers it without any assistant. Then a section on drafting the weekly team update, and a short "questions it should not answer" section (no ranking of people, R4). The one Kite Pulse callout sits in "How the assistant gets its answers": answers stay within the manager's own view, and the whole route is available when enabled. The reader leaves with a shortlist of questions worth asking and what to switch on for each.
- **Interactive elements:**
  1. Question picker - the reader picks a question and sees a sample answer from a labelled sample team, what it needs (none, AI labelling, direct access, or an optional read) and the console page that gives the same answer. Fallback is the same mapping as a table.
  2. Weekly update drafter - from sample counts (sessions, active projects, repeated failures, plan pressure), the page assembles a plain-text team update the reader can copy; built by fixed rules on the page, no AI, labelled sample data. Fallback paragraph shows one finished example.
- **Images / video (optional):** Optional short screen recording of a real question asked from Claude Code over MCP, only from a deployment with the Agent API on and the answer's data checked; otherwise none.
- **FAQ:**
  - Can an AI assistant write my weekly team update from engineering data?
  - Can I let an AI assistant summarise my team's engineering activity?
  - Is there an API or MCP server for engineering analytics?
  - How much of our engineering time goes to bug fixing vs new features?
- **Links to:** /engineering-intelligence, /docs, /blog/ai-weekly-team-report (built), /docs/agent-api, /how-to-connect-claude-code-to-mcp, /blog/blocker-board-engineering, /blog/ai-session-success-rate, /blog/scheduled-engineering-reports
- **Watch-outs:** The Agent API and MCP are MSoT 2.1 "needs operator setup": "available when enabled" throughout, and direct access is an admin's choice; say that every question here can also be answered in the console. Leave out cost reconciliation (row note: it relies on the hidden Cost & ROI, R3). Bug fix versus feature needs AI labelling's type-of-work labels (MSoT 1.5, admin sets it up); without it the answer is "unknown", not a guess. Plan history comes from the plan usage report (MSoT 1.3; Excel admin by default; Claude Code only, R7). Cost is per tool, never a total across tools (R7). "Newcomer ramp-up", "file hotspots", "effort per branch" and "time lost to interruptions" are Article Plan only: confirm before listing them. First FAQ: the assistant drafts prose, the figures must come from the data; point to the scheduled company report (MSoT 1.3) as the no-AI route. No question that ranks or compares named people (R4).

### 10.11 · Redact Secrets in AI Chat History: Who Reads What

- **Category · intent · page type:** External API Access and Integrations · Commercial · Blog post
- **Plan title:** Reading What the AI Said: the Session-Text Permission and Its Safeguards
- **Title tag:** Redact Secrets in AI Chat History | Kite Pulse
- **H1:** Redact Secrets in AI Chat History: Who Can Read What the AI Said, and What Stays Masked
- **URL:** /blog/redact-secrets-in-ai-chat-history
- **Meta description:** How to redact secrets in AI chat history before anyone reads it: where secrets are masked, who can read session text, and what the record shows.
- **Main keyword:** redact secrets in ai chat history
- **Secondary keywords:**
  - secret masking → H2 "Secret masking happens twice before anyone reads" (main keyword of 1.3: link /blog/secret-masking)
  - audit log for admin actions → H2 "Reads that leave a record" (main keyword of 2.31: link /blog/audit-log-for-admin-actions)
  - redact secrets from claude code logs → H3 "Claude Code's own history on the laptop"
- **Description:** For developers and data-protection officers asking whether a manager can read their prompts, and what happens to a key pasted into one. Pages ranking here explain log scrubbing in general; none follows the text of an AI coding conversation from the laptop to the people who may read it. The article runs: what session text is (the tool's own record, including code excerpts the AI read or wrote); masking on the computer before upload (36 credential patterns; a part that fails masking is not sent) and again on the server, with Cursor and OpenCode chat text masked on the server only; what Claude Code's own history file is and that Kite Pulse masks its copy, not the file on the laptop; who can read text, by role; what never shows text (prompt statistics stay with the developer, MCP never offers prompt text); and where reads are recorded. The one Kite Pulse callout sits at the masking section. The reader leaves knowing what is masked, where, and who can see the rest.
- **Interactive elements:**
  1. Redaction preview - a sample chat line containing obviously fake credentials ("sk-EXAMPLE-0000", a password in a URL) is shown before and after masking; a "Cursor or OpenCode" toggle moves the masking to the server step. Fallback lists the kinds of credentials MSoT 1.1 names.
  2. "Who can read this?" grid - the reader picks a role (Developer, Manager, Admin) and a kind of data (prompt text, private prompt statistics, token counts, step record) and sees whether that role sees it and where; items that rest on unconfirmed facts are marked "to confirm". Fallback is the grid as a table.
- **Images / video (optional):** None - the preview shows masking more clearly than a screenshot of masked text.
- **FAQ:**
  - Can managers see developers' AI prompts?
  - How are secrets and credentials handled before upload?
  - Can my manager see everything I type to the AI?
- **Links to:** /blog/secrets-in-ai-prompts (built), /privacy, /security, /blog/secret-masking, /blog/audit-log-for-admin-actions, /blog/developer-analytics-security
- **Watch-outs:** R6 wording: secrets are "masked", never "removed"; uploads encrypted in transit, never at rest. Masking covers the 36 known patterns, not every secret: say so (R9). The session-text permission with a risk acknowledgement (the plan title) is Article Plan only, in neither MSoT nor the Field Guide: confirm before describing it; until then answer the prompt questions from verified facts. Verified: private prompt statistics are shown only to the developer and removed by the server for everyone else (MSoT 1.4); prompt text and AI replies are never available over MCP (MSoT 2.1). The Field Guide says Workflows & Pain Points shows prompt text to admins (and to a developer for their own work), so never write "nobody but you can read your prompts". Third FAQ: Kite Pulse logs no keystrokes; it reads what the tool saved (R6). That Kite Pulse leaves the tool's own local file unchanged is inferred, not stated in MSoT: confirm. No automatic leaked-credential scanning (R8). Overlaps 1.3 and /blog/secrets-in-ai-prompts: keep this page to who reads the text.

### 10.12 · MCP Dry Run: Try a Question and Agent Activity

- **Category · intent · page type:** External API Access and Integrations · Commercial · Docs page
- **Section:** Help (Docs)
- **Plan title:** Before and After Handing Out a Key: Try a Question and Agent Activity
- **Title tag:** MCP Dry Run: Try a Question and Agent Activity | Kite Pulse
- **H1:** MCP Dry Run and Agent Activity: See What an AI Tool Gets Before and After You Issue a Key
- **URL:** /docs/mcp-dry-run
- **Meta description:** MCP dry run in Kite Pulse, available when enabled: preview what an agent key returns before you issue it, and read every request it made afterwards.
- **Main keyword:** mcp dry run
- **Secondary keywords:**
  - audit log for admin actions → H2 "After: Agent Activity and the Audit Log" (main keyword of 2.31: link /blog/audit-log-for-admin-actions)
  - read only mcp server → H3 "Keeping a key read-only" (main keyword of 10.9, merged into a page: link /docs/agent-api)
- **Description:** For admins and auditors who want to see what an AI tool would get before handing out a key, and what it did afterwards. Pages ranking for "mcp dry run" are about testing MCP servers in general; the first paragraph says this page is about Kite Pulse's own preview and log. Two halves. Before: trying a question against a key, and the dry run on write tools, which shows what would change and saves nothing. After: the Agent Activity log (every key request with route, tool and outcome; admins see every request, managers see requests made with keys of people in their team with some answer bodies withheld, everyone sees their own; CSV export). The one Kite Pulse callout sits at the dry run: a write needs its scope on the key and is recorded as made "via key". The reader leaves with a short before-and-after routine for every key they issue.
- **Interactive elements:**
  1. Dry-run viewer - a sample write request (add a person to a team) with dry run on and off: on shows the change that would be made and "nothing saved"; off shows the change applied and a sample audit row "via key". Labelled sample data. Fallback paragraph describes both outcomes.
  2. Sample Agent Activity log - a dozen sample requests with filters by key, tool and outcome, and a role switch (Admin, Manager, Developer) that hides the rows that role would not see. Fallback is a table of who sees which requests.
- **Images / video (optional):** None - both widgets use sample data; a real log would show real people's requests.
- **FAQ:**
  - Does AI coding analytics include an audit log of admin actions?
  - Can I test what a key returns before I give it to someone? (suggested; confirm with the keyword owner)
- **Links to:** /docs, /security, /docs/agent-api, /blog/audit-log-for-admin-actions, /how-to-connect-claude-code-to-mcp
- **Watch-outs:** Everything here is MSoT 2.1 "needs operator setup": "available when enabled", never a default (R8). MSoT 2.1 names "optional write tools with a preview (dry run)" in direct mode and the Agent Activity log; "try a question" on the key page and the "via key" audit row are Field Guide only: confirm. Writes the Field Guide lists include Brain documents and agents: leave those out (R3); use teams or project approvals as the example. Managers see requests made with their team's keys with some answer bodies withheld (MSoT 2.1): do not say managers see everything. The FAQ answer covers the Audit Log (MSoT 1.6: sign-ins, failed sign-ins, lockouts and admin changes, read-only, kept indefinitely by default) and does not claim retention deletion unless the operator enabled it.

### 10.13 · Jira Issues Linked to AI Coding Sessions: Connectors

- **Category · intent · page type:** External API Access and Integrations · Commercial · Integration
- **Section:** Integrations
- **Plan title:** Connectors: Linking Jira, HubSpot, Slack, GitHub, Confluence, Google Drive and Notion to Projects
- **Title tag:** Jira Issues Linked to AI Coding Sessions | Kite Pulse
- **H1:** Jira Issues Linked to AI Coding Sessions, Project by Project: Kite Pulse Connectors
- **URL:** /integrations/connectors
- **Meta description:** Jira issues linked to AI coding sessions by project: how Kite Pulse connectors map Jira, Confluence, GitHub, Notion and more to the projects you track.
- **Main keyword:** jira issues linked to ai coding sessions
- **Secondary keywords:**
  - jira claude code integration → H2 "Jira and Claude Code: one project, two sources"
  - confluence claude code → H3 "Confluence spaces"
  - notion claude code integration → H3 "Notion databases"
- **Description:** For admins and project owners who want tickets and documents next to the AI work on a project. Pages ranking here are Jira apps and MCP servers that let Claude Code read tickets; none puts tickets beside a team's AI sessions on the projects being tracked. Built on the Integration layout, adapted to connectors: what a connector is (seven: Jira, HubSpot, Slack, GitHub, Confluence, Google Drive and Notion, each mapped by an admin to a Kite Pulse project, credentials stored encrypted), what each one maps (a Jira project, a Confluence space, a repository, a Drive folder, a Notion database, a HubSpot company, a Slack channel), what is never stored, setup steps (Settings › Connectors), a privacy note, FAQ, and links to the other integrations. The one Kite Pulse callout sits in the Jira section: the link is made at project level, so tickets and sessions meet on the same project. The reader leaves knowing what connecting one tool gives them and what it does not.
- **Interactive elements:**
  1. Mapping builder - the reader adds sample outside spaces (a Jira project, a Confluence space, a Notion database) and maps each to a sample Kite Pulse project; the page shows the result per project and who could see it. Fallback is a table of connector → kind of space → mapped to.
  2. Connector chooser - the reader picks one of the seven connectors and sees the kind of space it maps and what is never stored. Fallback is the same table in full.
- **Images / video (optional):** One screenshot of Settings › Connectors from a real deployment, dated, if one exists (MSoT 2.5); otherwise none.
- **FAQ:**
  - Can Kite Pulse link Jira issues to individual AI coding sessions? (suggested; confirm with the keyword owner)
  - Which outside tools can Kite Pulse connect to? (suggested; confirm with the keyword owner)
  - Who can see synced Jira issues? (suggested; confirm with the keyword owner)
- **Links to:** /integrations, /features, /integrations/claude-code, /integrations/cursor, /security
- **Watch-outs:** MSoT 1.6 verifies only connecting the seven tools, mapping them to projects and storing credentials encrypted; it says "What each connector's data feeds in the console was not checked". Everything about where synced items appear (Jira issues on the project for everyone who can see it, sync every couple of minutes, restricted items and issues with a Jira security level never kept, the server needing KITE_PULSE_MASTER_KEY) is Field Guide only: confirm each before writing. The main keyword promises session-level links; the page must say plainly that the link is per project, not per session (R9), which is why the first FAQ is suggested. Brain Chat citations are out (row note, R3). Slack alerts belong to 13.12 (/docs/slack-notifications); keep the Slack connector to mapping a channel. The three secondaries are developer-side integrations (reading tickets from Claude Code); do not imply Kite Pulse passes tickets into Claude Code.

### 10.14 · SCIM Entra ID Provisioning and Okta User Sync

- **Category · intent · page type:** External API Access and Integrations · Commercial · Integration
- **Section:** Integrations
- **Plan title:** User Sync with Microsoft Entra ID and Okta
- **Title tag:** SCIM Entra ID Provisioning and Okta | Kite Pulse
- **H1:** SCIM Entra ID Provisioning and Okta User Sync for Kite Pulse
- **URL:** /integrations/entra-id-okta
- **Meta description:** SCIM Entra ID provisioning and Okta user sync for Kite Pulse: what it creates, updates and deactivates, what it never touches, and how to set it up.
- **Main keyword:** scim entra id provisioning
- **Secondary keywords:**
  - scim 2.0 user provisioning → H2 "What SCIM 2.0 user provisioning does here"
  - scim user provisioning developer analytics → body of the opening paragraph
  - scim provisioning okta → H2 "Okta: SCIM provisioning"
  - okta custom scim app → H3 "Creating the Okta custom SCIM app"
- **Description:** For IT and identity administrators. Pages ranking here are Microsoft's and Okta's own SCIM guides; none says what a developer-analytics tool does with the accounts it receives. Built on the Integration layout, adapted: what the sync does (creates, updates and deactivates accounts), what it never does (set roles or managers, touch admins, reactivate an account it did not deactivate), that it is provisioning and not sign-in (people still sign in with email and password), setup steps for Entra ID and for Okta (a bearer token made on Login & Registration, the /scim/v2 address), and what to do after a sync (set roles and managers in Accounts & Roles). The one Kite Pulse callout sits at "what it never does": access roles stay a decision made in Kite Pulse. The reader leaves with a setup checklist for their directory.
- **Interactive elements:**
  1. Sync simulator - a sample directory of five people; the reader adds, renames, disables and re-enables people, including one admin, and sees what Kite Pulse does for each (created, updated, deactivated, left alone) and that no role is set. Fallback is a table of directory change → result.
  2. Setup checklist builder - the reader picks Entra ID or Okta and gets copyable steps with the Kite Pulse side filled in and the directory side as placeholders until checked against the vendor's documentation. Fallback is a numbered list for both.
- **Images / video (optional):** None until the steps are confirmed in a real deployment; screenshots of Entra ID or Okta screens date quickly.
- **FAQ:**
  - Does Kite Pulse support single sign-on? (suggested; answer plainly that it does not and that this is provisioning only; confirm with the keyword owner)
  - Does SCIM user sync set roles in Kite Pulse? (suggested; confirm with the keyword owner)
  - Are directory groups synced? (suggested; confirm with the keyword owner)
- **Links to:** /security, /self-hosted, /docs/roles-and-permissions, /integrations
- **Watch-outs:** SCIM user sync is in neither MSoT Section 1 nor Section 2: every fact here (Entra ID and Okta, create, update and deactivate, never roles, managers or admins, reactivating only what it deactivated, the bearer token on Login & Registration, /scim/v2, "groups later") is Field Guide only (28 Oct). Confirm in the console before writing, and consider holding the page until MSoT lists it. The Article Plan calls it an admin switch: confirm. Say "user sync" and "provisioning", never single sign-on, SAML or OIDC sign-in (R8; avoid list); sign-in is email and password (MSoT 1.6). Groups are not synced. Steps on Microsoft's and Okta's side need source URLs and checked dates in the data file (R2).

### 10.16 · Daily Digest Email for Engineering Teams

- **Category · intent · page type:** External API Access and Integrations · Informational · Blog post
- **Plan title:** Email from Kite Pulse: Notices, Alert Emails, Daily Digests and Scheduled Reports
- **Title tag:** Daily Digest Email for Engineering Alerts | Kite Pulse
- **H1:** Daily Digest Email for Engineering Teams: Alerts, Digests and Scheduled Reports
- **URL:** /blog/daily-digest-email
- **Meta description:** What a daily digest email should hold for an engineering team, with a template and examples, and how Kite Pulse sends alerts, digests and reports.
- **Main keyword:** daily digest email
- **Secondary keywords:**
  - daily digest email template → H2 "A daily digest email template for engineering alerts"
  - email digest examples → H3 "Three email digest examples"
  - daily digest email notifications → H2 "Choosing who gets which notifications"
  - weekly engineering report → H2 "When a weekly report fits better" (main keyword of 3.11: link /blog/weekly-engineering-report)
  - claude code daily summary → body of "When a weekly report fits better", one sentence on a developer's own day (main keyword of 4.9: link /blog/claude-code-daily-summary)
  - ai coding budget alerts → H3 "Budget alerts at 80% and 100%" (main keyword of 13.8: link /docs/ai-budget-alerts)
- **Description:** For admins and leads deciding what should reach people's inboxes. Pages ranking here are help pages of unrelated products and mailing-list tools; no engineering-alert content ranks. Informational, so it teaches first: what belongs in an immediate alert and what can wait for a digest, a template, three examples (an admin's infrastructure digest, a budget holder's digest, a lead's weekly report), and how to choose recipients. Then Kite Pulse's email channel: alerts with an in-app bell, email and a daily digest, admins choosing who is told what on Notifications, scheduled company or developer reports by email, and budget alerts at 80% and 100%. The one Kite Pulse callout sits at "Choosing who gets which notifications". The reader leaves with a digest template they can use with any tool.
- **Interactive elements:**
  1. Digest template builder - the reader ticks sections (open alerts, budget status, uploads failing, Claude plan pressure) and a frequency, and gets a copyable plain-text template filled with labelled sample data. Fallback shows one complete template in a code block.
  2. Alert or digest? sorter - sample events (disk 90% full, a budget at 80%, a collector that went silent, last week's usage) that the reader sorts into "alert now" or "digest", with the page's reasoning shown after each. Fallback is a table of the same events and answers.
- **Images / video (optional):** None - the template builder shows the email itself.
- **FAQ:**
  - How do I create a weekly AI usage report for my team?
- **Links to:** /features (the sheet lists /reports, folded into /features), /blog/ai-weekly-team-report (built), /blog/weekly-engineering-report, /blog/claude-code-daily-summary, /blog/scheduled-engineering-reports, /docs/scheduled-email-reports, /docs/slack-notifications, /docs/ai-budget-alerts
- **Watch-outs:** All email needs the server's mail settings, set by the operator (MSoT 2.1): say so wherever email appears. Verified: alerts with acknowledge and resolve, the bell, email and a daily digest, with recipients chosen on Notifications (MSoT 1.6); scheduled reports daily, weekly or monthly as PDF or CSV (MSoT 1.3); budget alerts at 80% and 100% (MSoT 1.2). What the daily digest contains is not specified in MSoT: confirm before showing a real one; the page's template is the reader's own. The Field Guide says the plan-limit and agent-stuck notices arrive "in the console only": do not say they are emailed. The FAQ answer points to the scheduled company report and the built /blog/ai-weekly-team-report. Weak intent match (row note): keep the general teaching useful on its own.

### 10.17 · Developer Analytics Security: What Leaves Your Server

- **Category · intent · page type:** External API Access and Integrations · Commercial · Blog post
- **Plan title:** What Leaves Your Server, Integration by Integration
- **Title tag:** Developer Analytics Security, Link by Link | Kite Pulse
- **H1:** Developer Analytics Security: What Leaves Your Server, Integration by Integration
- **URL:** /blog/developer-analytics-security
- **Meta description:** Developer analytics security, link by link: what leaves a self-hosted Kite Pulse server, which switch controls each link, and what never leaves.
- **Main keyword:** developer analytics security
- **Secondary keywords:**
  - self-hosted ai usage tracking → H2 "What stays on the server you run" (main keyword of 1.2: link /blog/self-hosted-ai-usage-tracking)
  - track token usage without collecting prompts → H3 "Counts-only collection" (main keyword of the built /blog/track-token-usage-without-prompts: link)
  - developer analytics without source code access → body of H2 "From the laptop to your server" (main keyword of 6.7, built: link /blog/developer-analytics-without-source-code)
- **Description:** For security and IT decision-makers filling in a vendor review. Pages ranking here are security pages of hosted analytics vendors; this one is an inventory of outbound links for a tool that runs on the customer's own server. Each link gets the same four lines (what goes, where, which switch, default state): the desktop program to your server (session records, secrets masked, uploads encrypted in transit; counts-only mode); updates from your own server; AI labelling to an AI provider through OpenRouter (off until an admin sets it up; scrubbed text; default policy zero data retention); agent keys (available when enabled); email (needs the operator's mail settings); connectors (credentials stored encrypted); Slack alerts and user sync (to confirm). The one Kite Pulse callout sits at "What stays on the server you run": no vendor cloud between the computer and the server. The reader leaves with a copyable list of the links their own install has switched on.
- **Interactive elements:**
  1. Outbound map - a diagram of the server with each outbound link as a switch; turning one on lists what would leave, where and who controls it. Fallback is the same inventory as a table.
  2. Install checker - the reader answers whether they turned on AI labelling, the Agent API, email, connectors and Slack alerts, and gets a copyable list of the outbound links in their setup for a security review. Fallback paragraph lists the default state of each.
- **Images / video (optional):** None - the map is the diagram.
- **FAQ:**
  - Does Kite Pulse send data to a vendor's cloud?
  - Does AI coding analytics need an AI API key or send data to an LLM?
  - Where is AI coding usage data stored and who can access it?
- **Links to:** /security, /self-hosted, /privacy, /blog/self-hosted-ai-usage-tracking, /blog/track-token-usage-without-prompts (built), /blog/developer-analytics-without-source-code (built), /docs/agent-api, /integrations/connectors, /integrations/entra-id-okta, /blog/redact-secrets-in-ai-chat-history
- **Watch-outs:** Uploads are encrypted in transit; never claim encryption at rest (R6, R8); stored data is on local disk or S3 (MSoT 1.8). It needs no AI service to work (MSoT product summary); AI labelling sends scrubbed text through OpenRouter with a default policy of zero data retention (MSoT 1.7): say "default policy", not a guarantee. Agent API: "available when enabled" (MSoT 2.1). Slack alerts and SCIM user sync are Field Guide only: mark them "to confirm" in the inventory or leave them out. Brain Chat's AI key is hidden (R3): leave it out. No certifications (R8). Third FAQ: managers see their reporting line, admins see everyone, enforced by the server (MSoT 1.4). Overlaps /security, which targets general security: keep this page to outbound links and link to /security for the rest.

### 11.1 · How to Run a Daily Standup Meeting from Live Data

- **Category · intent · page type:** Workflows · Informational · Interactive guide
- **Section:** Guides & tools
- **Plan title:** Running the Monday Stand-up from The Office and Team Overview
- **Title tag:** How to Run a Daily Standup Meeting with Data | Kite Pulse
- **H1:** How to Run a Daily Standup Meeting That Starts from Facts, Not Round-the-Room Updates
- **URL:** /how-to-run-a-daily-standup
- **Meta description:** How to run a daily standup meeting step by step: a short agenda, better questions and a live team view, so the time goes to blockers, not updates.
- **Main keyword:** how to run a daily standup meeting
- **Secondary keywords:**
  - how to run effective standups → short answer, and body of H2 "Step 1: decide what the stand-up is for"
  - standup meeting agenda → H2 "Step 2: a standup meeting agenda that fits the timebox"
  - daily standup questions → H2 "Step 3: swap the three daily standup questions for better ones"
  - team status dashboard → H2 "Step 4: open a team status dashboard before anyone speaks" (main keyword of 5.1: link)
  - team availability dashboard → H3 "Who is in today: presence, leave and on-call" (under step 4)
  - live view of ai coding agents → body of step 4, one sentence (main keyword of 9.4: link)
  - team collaboration insights → body of H2 "Step 6: decide who to pair, help or unblock" (main keyword of 2.13: link)
- **Description:** For team leads who run a daily stand-up and want it to go to problems rather than status. Ranking pages (Granola, Lucid, ClickUp, ActiveCollab, resolution.de, The Digital Project Manager) all say "avoid status reporting", and none shows how to arrive already knowing who is online, who needs attention and who works on what; that data-led stand-up is the gap. The guide teaches the stand-up first and works without any product: purpose and timebox, agenda, questions, a look at the team's status before the meeting, running the meeting on exceptions, the decision (pair, help, unblock), and a short async follow-up. One Kite Pulse callout at step 4, where checking every person's status by hand stops scaling: Team Overview shows who is online and coding now, active time and sessions today against a typical day, who needs attention and each person's current project, refreshed every 30 seconds; The Office shows the same team as desks with markers for stuck work or plan limits; Leave & On-Call keeps an absence from being misread. The reader leaves with a copyable agenda card for their own team.
- **Interactive elements:**
  1. Agenda and timebox builder (step 2) - the reader sets team size, remote or in-room, and the sections they want (blockers, decisions, handoffs, announcements) and gets a timed agenda to copy. Fallback is one sample agenda in plain text.
  2. Question picker (step 3) - the reader compares the classic three questions with a blocker-first set and sees which questions a team view could answer before the meeting starts. Fallback is the same comparison as a table.
  3. Before-the-meeting board (steps 4-5) - a sample team of seven (labelled sample data, invented names) with online, coding, away, on leave and needs-attention states; a "check before the stand-up" switch shrinks the agenda to the exceptions only. Fallback paragraph walks through the same sample.
- **Images / video (optional):** One Team Overview screenshot from a real deployment, dated and labelled, at step 4; otherwise none, since the sample board shows the same view.
- **FAQ:**
  - How do I know what my engineering team is working on right now?
  - How do I see what my team is working on without status meetings?
  - How can I see team activity in real time?
- **Links to:** /features, /ai-agent-office, /engineering-intelligence, /blog/team-status-dashboard, /blog/live-view-of-ai-coding-agents, /blog/team-collaboration-insights
- **Watch-outs:** The Article Plan calls it the Monday stand-up; the keyword is the daily one, so write it daily. Verified (MSoT 1.4): Team Overview's fields and 30-second refresh, The Office's desks and markers, Leave & On-Call. Team Overview's "needs attention" means collection problems (failing uploads, backlog, old app version), not a struggling person: say so. Team Overview also lists "Most active today": never present it as a ranking (R4; owner decision open). The stuck notice is Field Guide only: no 30-minute figure. No numbers on how much shorter stand-ups get (R2). "Team availability dashboard": Kite Pulse shows presence plus recorded leave and rotas, not a calendar; do not imply calendar sync. Generic stand-up advice first, Kite Pulse second (S11, Informational). Overlaps 5.1 and 7.14: keep this one to running the meeting.

### 11.3 · AI Coding Tools Budget Management: Monthly Review

- **Category · intent · page type:** Workflows · Commercial · Blog post
- **Plan title:** The Monthly AI Spend and Budget Review
- **Title tag:** AI Coding Tools Budget Management Review | Kite Pulse
- **H1:** AI Coding Tools Budget Management: a Monthly Review of Spend, Budgets and Seats
- **URL:** /blog/ai-coding-tools-budget-management
- **Meta description:** AI coding tools budget management as a monthly routine: review usage by team and tool, check budget alerts and seats, then adjust budgets or seats.
- **Main keyword:** ai coding tools budget management
- **Secondary keywords:**
  - ai coding spend by team → H2 "Step 1: read AI coding spend by team, tool and model"
  - token usage forecast → H3 "Where usage is heading this month" (under step 2; main keyword of 2.20: link to the built page)
  - ai budget per team → H2 "Step 3: check each AI budget per team or project" (main keyword of 2.21 and 5.10, both merged into /ai-budgets: link /ai-budgets)
  - ai license utilization → H2 "Step 4: AI license utilization: shared, idle and personal seats"
  - ai coding seat cost tracking → body of step 4 (main keyword of 2.23: link)
- **Description:** For finance, budget holders and engineering managers who own an AI tools line and review it monthly. The page is a routine, not a feature tour: read usage by team, project, tool and model; look at where usage is heading; check each budget and its alerts; look at seats; then make the month's decisions (raise or lower a budget; buy, move or cancel a seat) and write them down. One Kite Pulse callout at step 3: AI Budgets set per team or project, monthly, in tokens or estimated US dollars, with alerts at 80% and 100%; a dollar budget adds up the priced tools only and reports unpriced tokens separately. The reader leaves with a copyable monthly review checklist and a decision log.
- **Interactive elements:**
  1. Monthly review run-through - a sample organisation of four teams (labelled sample data) with month-to-date tokens, budgets and alerts; the reader marks a decision per team and copies the review notes. A "dollar budget" toggle shows priced and unpriced usage reported apart. Fallback paragraph walks one team through the review.
  2. Seat decision helper - sample Tool Accounts rows (one shared, one rarely seen, one personal domain) with an example seat price; the reader picks keep, move or cancel and sees what to check first. Fallback is a short table of the three cases.
- **Images / video (optional):** None - the sample review carries it.
- **FAQ:**
  - How much are we spending on AI coding tools each month?
  - How do I set an AI coding-tool budget for each team?
  - Are we paying for licenses that developers aren't using?
  - Can I set spending limits and receive alerts when teams exceed their budgets?
- **Links to:** /ai-cost-tracking, /ai-budgets, /shadow-ai, /features (the sheet lists /reports, hidden; folded into /features), /blog/token-usage-forecast (built), /blog/engineering-ai-spend-report (built), /blog/ai-coding-seat-cost-tracking, /docs/ai-budget-alerts
- **Watch-outs:** R7 throughout: cost is an estimate from list prices, "not billed spend"; Team AI Usage shows cost per tool and never totals it; Codex, Cursor and Copilot usually show "—"; per team or project, cost appears only in AI Budgets; cost per developer is admin-only. The first FAQ answer must say Kite Pulse cannot give one monthly total across tools, and that the invoice is the vendor's. The token pace line and 30-day outlook are Field Guide only: use the built /blog/token-usage-forecast's wording and confirm. Third FAQ: Kite Pulse sees accounts that appear in sessions on collected machines (Tool Accounts, five tools, admin by default); a seat nobody uses on a collected machine never appears, so compare with the vendor's seat list. Seat prices are entered by admins and shown to admins. Budget alerts by email need mail set up on the server (MSoT 2.1). Overlaps 13.8 (alert setup) and 6.14 (limits): keep this one to the monthly review.

### 11.4 · AI Agent Stuck: From the Notice to the Fix

- **Category · intent · page type:** Workflows · Informational · Blog post
- **Plan title:** From "AI Agent Stuck" Notice to Fix
- **Title tag:** AI Agent Stuck: From the Notice to the Fix | Kite Pulse
- **H1:** AI Agent Stuck? A Step-by-Step Workflow from the Notice to the Fix
- **URL:** /blog/ai-agent-stuck
- **Meta description:** AI agent stuck? Open the notice, read what the agent did, restart with a clearer request, and decide if it is one task or a team-wide fix.
- **Main keyword:** ai agent stuck
- **Secondary keywords:**
  - ai agent stuck notification → H2 "Step 1: the AI agent stuck notification arrives" (main keyword of 2.10: link)
  - claude code agent stuck → H3 "When it is a Claude Code agent" (under step 2; main keyword of 4.5: link)
  - ai agent stuck in loop → H2 "Step 3: is the AI agent stuck in a loop or blocked by its setup?" (main keyword of 7.6: link)
  - repeated errors in ai coding sessions → H2 "Step 5: repeated errors across sessions mean a team fix" (main keyword of 3.3: link)
- **Description:** For developers and team leads who already know an agent is stuck and need the procedure after that. The built pages cover the before: /blog/is-claude-code-stuck (how to tell) and /blog/stuck-ai-agent (seeing it across a team), and /blog/ai-retry-loops covers why loops happen. This one is the after: the notice arrives; open the session; read the step record for the failing command and the retries; decide whether the request or the environment is at fault (missing dependency, wrong path, broken test setup); restart with a clearer request or fix the setup; then check whether others hit the same error. The decision it informs: one person's task or a team-wide fix. One Kite Pulse callout at step 5: Work Problems uses fixed rules, no AI, to find failed commands, error messages and repeated retries across the team, grouped by severity with suggested actions. The reader leaves with a five-question triage they can reuse.
- **Interactive elements:**
  1. Triage flow - four questions (the same command failing? the same error for others? request or environment? how long stuck?) lead to one of three outcomes: restart with a clearer request, fix the environment, or raise a team fix. Fallback is the same tree as a nested list.
  2. Sample step record - twelve steps of a sample session (labelled sample data) in which one test command fails five times; the reader clicks where they would step in and sees why. The record has no message-text column, and a note says so. Fallback paragraph describes the sample.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I know when AI is retrying the same failed fix repeatedly?
  - How do I spot developers who are stuck in long AI sessions?
- **Links to:** /blog/ai-retry-loops, /ai-agent-office, /features, /blog/is-claude-code-stuck (built), /blog/stuck-ai-agent (built), /blog/ai-agent-stuck-notification, /blog/claude-code-agent-stuck, /blog/ai-agent-stuck-in-loop, /blog/repeated-errors-in-ai-coding-sessions
- **Watch-outs:** The stuck notice, who receives it, its 30-minute interval and "What the agent did" are Field Guide only: confirm before writing and leave the 30-minute figure out until confirmed (as in 2.10). Work Problems is admin by default (MSoT 1.2): a manager may need it granted. Failed tool calls are recorded for every tool except Aider, and command exit codes come only from Claude Code, Codex and Copilot: the triage must not imply exit codes for all ten tools. Claude Code waiting signals are unreleased (MSoT 2.3): "stuck" here is never "waiting for you". Overlaps 2.10, 4.5, 7.6 and 3.3, which all own a secondary here: keep this page to the procedure and the decision.

### 11.6 · Lessons Learned in Software Projects: a Release Retro

- **Category · intent · page type:** Workflows · Informational · Blog post
- **Plan title:** A Release Retrospective Built on Session Evidence
- **Title tag:** Lessons Learned in Software Projects: a Retro | Kite Pulse
- **H1:** Lessons Learned in a Software Development Project: a Release Retrospective Built on Session Evidence
- **URL:** /blog/lessons-learned-software-development-project
- **Meta description:** Capture lessons learned in a software development project from session evidence: what hurt, which sessions went in circles, what to change next release.
- **Main keyword:** lessons learned in software development project
- **Secondary keywords:**
  - lessons learned software development → H2 "Why lessons learned in software development go stale" (main keyword of 8.14: link)
  - software developer pain points → H2 "Step 2: list the software developer pain points the release left behind"
  - claude code session analysis → H2 "Step 3: open the sessions that hurt" (main keyword of 4.6: link to the built page)
  - capture knowledge from ai coding sessions → H2 "Step 5: capture knowledge from AI coding sessions before it fades" (main keyword of 6.8: link)
- **Description:** For team leads and managers running a retrospective after a release. Retro templates rely on what people remember a week later; this page builds the retro from what the sessions recorded. Steps: set the window (the release's dates); list the pain points (inefficient patterns, longest sessions, hot files, stuck weeks); open the sessions that hurt, with each developer reviewing their own; check Work Problems for failures that kept coming back; capture what was learned as knowledge records; then decide what changes before the next release, with an owner per action. One Kite Pulse callout at step 2: Workflows & Pain Points shows repeated work shapes, inefficiencies, the longest sessions and hot files for the period. The reader leaves with a copyable lessons-learned register.
- **Interactive elements:**
  1. Retro board - a sample release (labelled sample data) with evidence cards (a long session, a hot file, a repeated failing command); the reader sorts them into keep, change and try, and copies the board as text. Fallback paragraph lists the sample evidence and one sorted outcome.
  2. Lessons-learned register - the reader adds actions with an owner and a check-by date and gets a table to paste into the team's notes. Fallback is an empty example row.
- **Images / video (optional):** None.
- **FAQ:**
  - How can I capture knowledge from AI coding sessions?
  - How do I stop my team solving the same bug twice?
- **Links to:** /blog/institutional-knowledge, /features, /blog/developer-experience-metrics, /blog/lessons-learned-software-development, /blog/claude-code-session-analysis (built), /blog/capture-knowledge-from-ai-coding-sessions, /blog/developer-pain-points
- **Watch-outs:** The Article Plan's "knowledge log" is in neither MSoT nor the Field Guide (8.15 found the same): use Knowledge Records (MSoT 1.5: quoted from real messages, linked to sessions and commits, start as "proposed", need AI labelling). Never "Knowledge Base", which is hidden (R3). Workflows & Pain Points is admin by default and shows prompt text to admins (Field Guide): the retro uses counts and session structure, and must not suggest reading colleagues' prompts. Developers open their own sessions in My Sessions. The second FAQ answer rests on knowledge records and needs AI labelling: say so. Overlaps 2.15 and 8.14: keep this one to the retro procedure.

### 11.8 · Developer Handover Checklist for Software Teams

- **Category · intent · page type:** Workflows · Informational · Interactive tool
- **Section:** Guides & tools
- **Plan title:** Planning a Hand-over Before Someone Moves On
- **Title tag:** Developer Handover Checklist for Software Teams | Kite Pulse
- **H1:** Developer Handover Checklist: a Software Handover Plan Built Before Someone Moves On
- **URL:** /developer-handover-checklist
- **Meta description:** A developer handover checklist for software teams: build a handover plan per project, find what only the leaver knows and confirm new owners in time.
- **Main keyword:** developer handover checklist
- **Secondary keywords:**
  - developer handover document → H2 "What goes in the developer handover document"
  - knowledge transfer plan template → H2 "Knowledge transfer plan template: dates, owners and sign-off" (the builder's copyable output)
  - handover plan when leaving a job → H3 "If you are the one leaving: your own handover plan"
  - engineering knowledge base → body of "What goes in the developer handover document", one sentence: notes go where the team already keeps them (main keyword of 13.15, not yet planned: no link)
  - capture knowledge from ai coding sessions → H2 "What the AI sessions show about the leaver's actual work" (main keyword of 6.8: link)
  - capability mapping software → body of the same section, one sentence on the Capability Map (main keyword of 8.16: link)
  - lessons learned software development → body of the closing section (main keyword of 8.14: link)
- **Description:** For engineering managers, admins and developers who are leaving. The results page is crowded with construction and property handovers; a software-team handover is open. Answer box first: the checklist in eight lines. Then the builder, then the method: how to find what only one person knows (ask them; look at who touched each project; read the project's own notes), and how to confirm a new owner per item before the last day. One Kite Pulse callout in the method: each developer's page lists the projects and sessions they worked on, Collaboration shows which projects have one contributor, and the Capability Map and knowledge records keep what the team decided. The reader leaves with a handover plan to copy.
- **Interactive elements:**
  1. Handover checklist builder (main tool) - the reader lists projects, systems and access, recurring duties and open work, sets the leaving date and gets a checklist with an owner and a due date per line, back-scheduled from the leaving date, to copy as Markdown or CSV. Fallback is a filled sample checklist in plain text.
  2. One-person check - a sample project list (labelled sample data) with contributor counts; projects with a single contributor are highlighted with what to ask first. Fallback is the same list as a table.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I stop my team solving the same bug twice?
  - How can I capture knowledge from AI coding sessions?
- **Links to:** /features, /blog/institutional-knowledge, /blog/capture-knowledge-from-ai-coding-sessions, /blog/capability-mapping-software, /blog/lessons-learned-software-development, /blog/offboarding-knowledge-transfer, /blog/knowledge-transfer-before-leaving, /bus-factor-calculator
- **Watch-outs:** The Article Plan's departure report, tenure, knowledge-capture requests, capability ownership and bus factor are not in MSoT Section 1 (8.18 found the first three in neither MSoT nor the Field Guide): leave them out. Build on verified pages: All Developers and the developer page, Collaboration, the Capability Map, Knowledge Records (need AI labelling) and the project-notes optional read (CLAUDE.md, AGENTS.md, READMEs, decision records; off until an admin turns it on). Title and H1 say "software" to stay out of the property-handover results. "Engineering knowledge base" is the reader's phrase; never call Kite Pulse's records a Knowledge Base (hidden, R3). Do not frame the page as watching the leaver (R4). Do not describe what happens to the leaver's data after they go; if mentioned, erasing anonymises the account and deletes raw activity records, never "all their data" (R6). Overlaps 3.7 and 8.18: this page is the checklist tool, they are the story and the explainer.

### 11.9 · Engineering Resource Allocation: Monthly Review

- **Category · intent · page type:** Workflows · Commercial · Blog post
- **Plan title:** The Monthly Project Portfolio Review
- **Title tag:** Engineering Resource Allocation: Monthly Review | Kite Pulse
- **H1:** Engineering Resource Allocation: a Monthly Project Portfolio Review of What to Staff, Pause, Merge or Retire
- **URL:** /blog/engineering-resource-allocation
- **Meta description:** Engineering resource allocation from a monthly portfolio review: project health, contributors and shared work, then decide what to staff, pause or retire.
- **Main keyword:** engineering resource allocation
- **Secondary keywords:**
  - project health status dashboard → H2 "Step 1: read the project health status dashboard"
  - duplicate repository detection → H2 "Step 2: merge duplicates before you count anything" (main keyword of 2.2: link)
  - engineering investment allocation → H2 "Step 4: engineering investment allocation by project and kind of work"
  - project health status report → H3 "Turning the review into a project health status report" (under step 6)
- **Description:** For engineering managers and admins who decide each month where people's time goes. Steps: read every project's health (active, stable or dormant), sessions, contributors and last activity; merge folders that are the same repository so nothing counts twice; see which projects several people share; see where effort goes by project, and by kind of work where AI labelling is on; decide what to staff, pause, merge or retire; write it up for leadership. One Kite Pulse callout at step 1: All Projects lists every project with its health, sessions, contributors and last activity, and Duplicate Detection offers merges and splits. The reader leaves with a copyable decision summary.
- **Interactive elements:**
  1. Portfolio grid - eight sample projects (labelled sample data) with health, contributors and last activity; the reader assigns staff, pause, merge or retire and copies a decision summary. Fallback is the sample as a table with one example decision.
  2. Kind-of-work toggle - the same sample shown "without AI labelling" (sessions and active time per project only) and "with AI labelling" (an example split into building, debugging and other work, labelled as an example). Fallback paragraph explains why the split needs labelling.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I find out which projects my team uses AI on the most?
  - How much of our engineering time goes to bug fixing vs new features?
- **Links to:** /features, /engineering-intelligence (the sheet also lists /reports, hidden; folded into /features), /blog/project-health-dashboard, /blog/duplicate-repository-detection, /blog/project-status-tracking-tool, /blog/company-ai-usage-report (built)
- **Watch-outs:** Phase, open blockers and duplicate work on the project summary card come from AI labelling per the Article Plan; MSoT 1.4 lists them on the card without saying so: confirm. The second FAQ answer needs work classification (AI labelling, set up by an admin); without it Kite Pulse shows no bug-versus-feature split: say so. "Resource allocation" here is attention and staffing, not timesheets, billing or headcount planning. Pausing and resuming: only admins resume a paused project; a scheduled deletion can be cancelled until it runs; deleted data cannot be recovered. First FAQ: Team AI Usage's Projects tab shows tokens by project. R9: portfolio tools fed by Jira or git measure delivery; say this review covers AI-assisted work only. Overlaps 2.16 and 7.10: keep this one to the monthly decision.

### 11.10 · Monthly Engineering Report for Leadership

- **Category · intent · page type:** Workflows · Informational · Blog post
- **Plan title:** Leadership Reporting on Autopilot
- **Title tag:** Monthly Engineering Report for Leadership | Kite Pulse
- **H1:** Monthly Engineering Report: What Leadership Needs, and How to Send It on a Schedule
- **URL:** /blog/monthly-engineering-report
- **Meta description:** What to put in a monthly engineering report on AI-assisted work, and how to send it to leadership on a schedule as PDF or CSV instead of by hand.
- **Main keyword:** monthly engineering report
- **Secondary keywords:**
  - cto dashboard → H2 "A report or a CTO dashboard: which one leadership needs"
  - claude team plan usage statistics → H2 "Claude team plan usage statistics, once a month" (link /plan-headroom)
  - ai usage report pdf → H2 "Sending it as an AI usage report PDF or CSV"
- **Description:** For managers and executives who report upward every month. The page sets a rhythm rather than a one-off: decide who reads it and what they ask; choose measures that answer those questions (active developers, sessions, tools and models, tokens and estimated cost per tool, plan pressure, project health); compare with the previous period; send it on a schedule; add the few sentences of judgement no report writes for you. One Kite Pulse callout at the scheduling step: the Company report compares any period with the one before and can be emailed daily, weekly or monthly as PDF or CSV, with a preview and a send history; the Plan usage report adds monthly Claude plan peaks as Excel. The reader leaves with a copyable report outline.
- **Interactive elements:**
  1. Report outline builder - the reader picks the audience (CTO, finance, board) and gets the sections and the measure that answers each, with the questions Kite Pulse cannot answer (delivery metrics, revenue) marked "from another source". Fallback is one sample outline.
  2. Cadence picker - daily, weekly or monthly, PDF or CSV, with a sample send history (labelled sample data). Fallback paragraph lists the options.
- **Images / video (optional):** One page of a real Company report PDF from a deployment, dated, if available; otherwise none.
- **FAQ:**
  - What metrics should I report to leadership about AI coding-tool adoption?
  - How do I create a weekly AI usage report for my team?
- **Links to:** /features (the sheet lists /reports, hidden; folded into /features), /engineering-intelligence, /blog/ai-weekly-team-report, /blog/company-ai-usage-report (built), /blog/scheduled-engineering-reports, /blog/weekly-engineering-report, /docs/scheduled-email-reports, /plan-headroom
- **Watch-outs:** Scheduled reports need email set up on the server (MSoT 2.1); downloads and schedules are admin by default. Company report: CSV or PDF; Plan usage report: Excel, admins by default, history from when recording began. R7: cost per tool, "not billed spend", never totalled across tools. No ROI figure (MSoT 2.5). Claude plan statistics are Claude Code only. Reports have no team filter (MSoT corrections): do not promise a report per team. R9: delivery metrics (DORA) come from git and ticket tools; say so in the first FAQ answer. Second FAQ: link the built /blog/ai-weekly-team-report and 3.11. Overlaps 2.28 (the feature) and 3.11 (the weekly story): keep this one to the monthly leadership rhythm.

### 11.12 · Compare AI Coding Assistants Usage on Your Team

- **Category · intent · page type:** Workflows · Informational · Blog post
- **Plan title:** Choosing Which AI Tools and Models to Standardise On
- **Title tag:** Compare AI Coding Assistants Usage on Your Team | Kite Pulse
- **H1:** Compare AI Coding Assistants Usage on Your Team, Then Decide Which Tools and Models to Standardise On
- **URL:** /blog/compare-ai-coding-assistants-usage
- **Meta description:** Compare AI coding assistants usage across Claude Code, Cursor, Copilot and more on your team, then decide which tools, seats and models to standardise.
- **Main keyword:** compare ai coding assistants usage
- **Secondary keywords:**
  - ai model adoption tracking → H2 "Step 2: AI model adoption tracking over time"
  - model usage by developer → H3 "Model usage by developer and by project" (under step 2)
  - claude code agent features usage → H2 "Step 3: which Claude Code agent features the team uses" (main keyword of 5.13: link to the built page)
  - ai license utilization → H2 "Step 4: AI license utilization and shared seats"
  - ai seat cost optimization → body of step 4 and of H2 "Step 5: decide what to fund, consolidate and recommend"
- **Description:** For engineering leadership and DevEx leads deciding which AI coding tools to back. Vendor comparisons judge the tools; this page compares how your own team uses them. Steps: who uses which tool, how much; which models, and how that has changed; which Claude Code agent features sessions use; how many accounts and seats each tool runs under, and what they cost; then the decision: which tools to fund, which seats to consolidate, which models to recommend. An honest section says usage shows what people reach for, not which tool is better (R9). One Kite Pulse callout at step 1: Team AI Usage puts the ten supported tools in one view, by person, tool, model, project and day. The reader leaves with a copyable decision record.
- **Interactive elements:**
  1. Usage comparison - a sample team (labelled sample data) by tool and developer, with sessions and tokens; a "show estimated cost" toggle shows a cost for priced tools and "—" for Codex, Cursor and Copilot, never a total. Fallback is the sample as a table.
  2. Standardisation worksheet - the reader scores each tool on usage, known cost, policy fit and plan limits, and copies a decision record. Fallback lists the criteria.
- **Images / video (optional):** None.
- **FAQ:**
  - What AI coding tools should we standardize on?
  - Should we allow developers to use multiple AI coding assistants?
  - How do I compare AI tool usage across Cursor, Claude Code and Copilot?
  - Can I see which AI models are being used and how frequently?
- **Links to:** /blog/claude-code-vs-cursor, /integrations, /shadow-ai, /ai-coding-assistant-pricing, /blog/claude-code-agent-features-usage (built), /blog/ai-adoption-tracking (built), /blog/shared-ai-tool-accounts, /blog/ai-coding-seat-cost-tracking
- **Watch-outs:** R5: "GitHub Copilot Chat in VS Code" (the third FAQ must say inline completions, JetBrains and Copilot CLI are not collected). Cursor and Copilot give input and output tokens only, and Cursor's model name only when one model served the whole chat: say comparisons across tools are approximate. R7: cost per tool, never totalled; Codex, Cursor and Copilot usually "—". Tool Accounts covers five tools and is admin by default; seat prices are entered by admins. The Models tab and Agent features tab are manager and admin views. The first FAQ answer must not recommend a vendor (R9); usage data is one input. Plan limits for Claude Code only.

### 11.13 · AI Coding Standards Built from Repeated Work

- **Category · intent · page type:** Workflows · Informational · Blog post
- **Plan title:** Turning Repeated Work into Team Standards
- **Title tag:** AI Coding Standards Built from Repeated Work | Kite Pulse
- **H1:** AI Coding Standards Built from Repeated Work: Turning What the Team Repeats into Shared Skills and Setup
- **URL:** /blog/ai-coding-standards
- **Meta description:** Set AI coding standards from what your team repeats: find repeated prompts and commands, turn them into Claude Code skills, keep versions current.
- **Main keyword:** ai coding standards
- **Secondary keywords:**
  - find repeated prompts in claude code → H2 "Step 1: find repeated prompts in Claude Code and repeated commands"
  - claude code skills used across team → H2 "Step 3: compare with the Claude Code skills used across the team" (main keyword of 2.25: link)
  - mcp servers installed across team → H3 "MCP servers installed across the team" (under step 3)
  - claude code version check → H2 "Step 5: keep everyone on a current Claude Code" (main keyword of 4.13: link)
- **Description:** For platform and DevEx teams who want standards that come from the work, not from a wiki page nobody reads. Steps: find the work the team repeats (work shapes, prompts and commands); review the draft skills built from repeated workflows and approve the useful ones; compare what is installed on machines (skills, commands, agents, MCP servers) with what sessions use; write the standard (shared skills, project notes conventions); keep Claude Code versions current; next month, check whether the repetition dropped. The decision it informs: what to automate or standardise next. One Kite Pulse callout at step 2: Skill Candidates builds draft Claude Code skills by rules from repeated workflows, for a person to approve or reject, with no AI model. The reader leaves with a standards backlog to copy.
- **Interactive elements:**
  1. Repetition to skill - a sample list of repeated commands and prompts with counts (labelled sample data); the reader picks one and gets a skill outline (name, description, steps) to copy. Fallback paragraph shows one worked example.
  2. Installed versus used - a sample matrix of skills and MCP servers installed on machines against those used in sessions; a filter shows "installed, never used". Fallback is the sample as a table.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I share AI best practices across my team?
  - How do I find out if developers are on outdated versions of Claude Code?
- **Links to:** /skill-candidates, /blog/institutional-knowledge, /ai-agent-office (the sheet lists /parallel-ai-agents, folded into /ai-agent-office), /integrations/claude-code, /blog/turn-workflows-into-claude-code-skills, /blog/claude-code-skills-used-across-team, /blog/claude-code-version-check, /blog/claude-md-version-control (built)
- **Watch-outs:** What is installed comes from an optional read (MSoT 1.1: Claude Code skills, commands, agents, hooks and MCP servers; off until an admin turns it on); plugins need app 0.4.3, not confirmed published: leave plugins out. The page name "Agent Setup" is Field Guide only; MSoT names the read. Repeated prompt text on Workflows & Pain Points is for admins and for a developer's own work (Field Guide): say so, and never imply managers read prompts. Skill Candidates and the version check ("version behind" filter) are verified. Any statement about Claude Code's skill format needs an Anthropic docs source and a checked date in the data file. Avoid "AI code review tools" framing. Overlaps 3.13 (the story) and 2.25: keep this one to the standards process.

### 11.14 · Personal Weekly Review for Developers

- **Category · intent · page type:** Workflows · Informational · Blog post
- **Plan title:** A Developer's Own Weekly Review
- **Title tag:** Personal Weekly Review for Developers | Kite Pulse
- **H1:** A Personal Weekly Review for Developers: Pick One Habit to Change from Your Own Week
- **URL:** /blog/personal-weekly-review
- **Meta description:** A personal weekly review for developers: check what you worked on, your heaviest AI sessions and your Top 3, then pick one habit to change next week.
- **Main keyword:** personal weekly review
- **Secondary keywords:**
  - weekly self reflection template → H2 "A weekly self reflection template you can copy"
  - weekly work reflection template → body of the same section (the copyable template)
  - personal claude code usage stats → H2 "Step 1: check your personal Claude Code usage stats and that your work was captured" (main keyword of 2.4: link)
  - developer scorecard → H2 "Step 2: read your developer scorecard's Top 3" (main keyword of 2.5 and 13.7: link to 2.5's page)
  - deep work sessions developer → H3 "Deep work sessions and short bursts" (under step 3; main keyword of 4.3: link)
  - claude code daily summary → body of step 3, one sentence (main keyword of 4.9: link)
  - developer habits → H2 "Step 4: choose one of your developer habits to change"
- **Description:** For developers who want a short Friday routine. Weekly-review pages are general productivity (GTD blogs, newsletters, template shops); none is written for developers or uses their own session data. The page teaches a 20-minute review that works with any tools, then shows where Kite Pulse fills it in: check that the week's work was captured and how close you are to your Claude plan limit; read your Top 3; look at your heaviest and longest sessions and your work-pattern facts; pick one habit; write it down and check it next week. One Kite Pulse callout at step 2: My Scorecard & Insights gives a verdict, why it matters, what to try and the evidence, and says "not enough data" rather than guess. The reader leaves with a copyable weekly template.
- **Interactive elements:**
  1. Weekly review template - four prompts (what I finished, where I got stuck, what the numbers say, one habit) the reader fills in and copies as Markdown; nothing is stored. Fallback is the blank template in text.
  2. Habit picker - a sample week's facts (labelled sample data: many short bursts, one long looping session, late peak hour) each suggest one habit to try. Fallback is the same list in text.
- **Images / video (optional):** None.
- **FAQ:** (none in the sheet; suggested, confirm with the keyword owner)
  - What should a developer include in a weekly review?
  - Can my manager see the data I use for my weekly review?
- **Links to:** /features, /privacy, /blog/personal-claude-code-usage-stats, /blog/developer-scorecard, /blog/deep-work-sessions-developer, /blog/claude-code-daily-summary, /blog/developer-working-style
- **Watch-outs:** Weak fit (sheet note): demand is general productivity, so the template must be useful to someone who never installs Kite Pulse. The Article Plan's "costly sessions": estimated cost per developer is admin-only (MSoT 1.2), so say "heaviest sessions" (tokens) unless it is confirmed that developers see their own cost. My Day is Field Guide only and needs AI labelling: one optional sentence at most. Second FAQ: managers see the same report the developer sees, without private prompt statistics (MSoT 1.4); do not write "only you see your scorecard". Plan figures are Claude Code only. Work-pattern definitions come from MSoT 1.4 (deep session 60 minutes or more, short burst under 15 minutes). "20 minutes" is advice, not a measured figure.

### 11.15 · Leaked Credentials in AI Chats: Weekly Triage

- **Category · intent · page type:** Workflows · Informational · Blog post
- **Plan title:** Weekly Security Triage of AI Conversations
- **Title tag:** Leaked Credentials in AI Chats: Weekly Triage | Kite Pulse
- **H1:** Leaked Credentials in AI Chats: a Weekly Security Triage of AI Conversations
- **URL:** /blog/leaked-credentials-in-ai-chats
- **Meta description:** Triage leaked credentials in AI chats each week: review masked keys by status, rotate them at the provider and record the fix. Masking is not revoking.
- **Main keyword:** leaked credentials in ai chats
- **Secondary keywords:**
  - credential leak detection → H2 "Step 1: run credential leak detection, then open the list" (main keyword of 2.32: link)
  - ai secret scanning → body of step 1 (main keyword of 6.10: link to the built page)
  - redact secrets in ai chat history → H2 "Redact secrets in AI chat history, and still rotate them" (main keyword of 10.11: link /blog/redact-secrets-in-ai-chat-history)
  - secret masking → body of the same section (main keyword of 1.3: link)
- **Description:** For security and IT teams who own what developers paste into AI tools. Ranking pages explain why pasting secrets into prompts is risky; this page is the weekly routine after it happens. Steps: the server operator runs the scan and the list fills; sort by status; for each key, find the provider and rotate or revoke it there; set the status; look for patterns (one tool, one project, one kind of key) and talk to the team about the cause; record the week. The decision it informs: which exposures to act on first. One Kite Pulse callout at the masking section: 36 credential patterns are masked on the developer's computer before upload and again on the server (for Cursor and OpenCode chat text, on the server only). The reader leaves with a copyable triage checklist.
- **Interactive elements:**
  1. Triage queue - sample findings with obviously fake masked keys (labelled sample data, such as "sk-EXAMPLE-****"); the reader moves each from open to rotated to closed and sees that the status is set by a person, not checked with the provider. Fallback paragraph walks one finding through.
  2. "Is masking enough?" flow - the reader picks where the key came from and gets the rotate-at-provider steps, with the reminder that masking in Kite Pulse does not revoke anything. Fallback is the same steps as a list.
- **Images / video (optional):** None.
- **FAQ:**
  - How do I find passwords or API keys leaked in AI chats?
  - How do I detect secrets or API keys pasted into AI tools?
  - How are secrets and credentials handled before upload?
- **Links to:** /blog/secrets-in-ai-prompts, /security, /shadow-ai, /privacy, /blog/credential-leak-detection, /blog/ai-secret-scanning (built), /blog/redact-secrets-in-ai-chat-history, /blog/secret-masking, /blog/claude-code-reading-secrets
- **Watch-outs:** Leaked Credentials is MSoT 2.1 Partial: it fills only after the server operator runs a command-line scan; there is no automatic scan; status is set by hand and not checked with the provider. R8: never claim automatic leaked-credential scanning; write "once the server operator runs the scan", or hold the article until the owner decides. Security watch (unchecked sensitive changes, pasted secrets) is not in MSoT Section 1: leave it out. Secrets are "masked", never "removed" (R6). A masked key was still in the developer's tool history and reached the AI provider: the page must say rotate it. Second FAQ: Kite Pulse masks what it uploads; it does not stop the paste reaching the AI tool. Overlaps 2.32, 3.10 and 6.10: keep this one to the weekly triage.

### 12.2 · On Premise Analytics Tools for Regulated Teams

- **Category · intent · page type:** Industry-Specific Applications · Commercial · Solution
- **Section:** Solutions
- **Plan title:** Self-Hosted AI Development Insight for Finance and Healthcare Teams
- **Title tag:** On Premise Analytics Tools for Regulated Teams | Kite Pulse
- **H1:** On-Premise Analytics Tools for Finance and Healthcare Teams That Use AI Coding Assistants
- **URL:** /solutions/regulated-industries
- **Meta description:** On premise analytics tools for regulated teams: see how AI coding sessions are read, masked and kept on your servers, and what to check before rollout.
- **Main keyword:** on premise analytics tools
- **Secondary keywords:**
  - developer analytics without source code access → H2 "What it reads: developer analytics without source code access" (main keyword of 6.7: link to the built /blog/developer-analytics-without-source-code)
  - secret masking → H3 "Secret masking on the laptop and again on the server" (main keyword of 1.3: link /blog/secret-masking)
  - audit log for admin actions → H3 "An audit log for admin actions that cannot be edited" (main keyword of 2.31: link /blog/audit-log-for-admin-actions)
  - pseudonymised developer analytics → body of the "What it reads" section, in the paragraph on tool accounts (keyed hash, email domain and plan name, never the address)
- **Description:** For IT, security and risk leads in banks, insurers, health providers and other regulated organisations whose developers already use AI coding assistants. Pages ranking for on-premise analytics are general BI and web-analytics vendors; none answers the risk team's question about AI coding sessions specifically: where the session text goes, who can read it and what stays behind. The page opens in the buyer's words ("our developers use AI tools; risk wants to know where that data goes"), gives a one-sentence definition block, then shows a sample session record field by field (labelled sample data) with what is read, what is masked and what is never collected. A readiness self-check and a deployment builder follow, then "How Kite Pulse helps" with two plain lists, what it can see and what it does not see, and an honest limits section: no certifications, the app does not encrypt stored data (that comes from the operator's disk or S3 encryption), and erasing a person anonymises rather than removes everything. One Kite Pulse callout at the deployment builder: data goes only to a server the team runs, with no vendor cloud between. The reader leaves with a copyable note for their risk committee.
- **Interactive elements:**
  1. Data-residency readiness check - six yes/no questions (must data stay in our network? may AI providers receive any text? do we need set retention periods? do we handle erasure requests? do we require encryption at rest? do auditors need an admin log?) produce, per answer, the Kite Pulse control that applies or the gap to plan around (for example "encryption at rest: arrange at the disk or S3 level"). Fallback is the same mapping as a table.
  2. Deployment builder - the reader picks where the server runs (one computer, local network, Ubuntu server, own AWS account with optional private S3) and which optional parts stay off (AI labelling, optional reads), and gets a copyable one-page statement of what leaves each laptop, where it lands and what is switched off. Fallback paragraph lists the four deployment options and the default-off parts.
- **Images / video (optional):** None - the sample record and the builder show the data flow; a compliance-style diagram would invite claims the page must not make.
- **FAQ:**
  - Does Kite Pulse send data to a vendor's cloud?
  - Do I need an AI API key to use Kite Pulse?
  - How are secrets and credentials handled before upload?
  - Where is AI coding usage data stored and who can access it?
- **Links to:** /self-hosted, /privacy, /security, /blog/secrets-in-ai-prompts, /blog/developer-analytics-without-source-code (built), /blog/secret-masking, /blog/audit-log-for-admin-actions, /solutions/public-sector, /docs/install-on-ubuntu
- **Watch-outs:** No compliance or certification claims of any kind (R8, row note): no GDPR, HIPAA, PCI, SOC 2 or ISO wording; the GDPR FAQ was left out on purpose. Do not claim encryption at rest: uploads are encrypted in transit; stored sessions are scrubbed but not encrypted by the app (MSoT 2.4), so the readiness check names operator disk or S3 encryption as the route. Erasure anonymises the account, deletes raw activity records and destroys keys; plain-text working copies stay (MSoT 2.3). Retention: "set how long data is kept", deletion applies once the server operator enables it. AI labelling, if an admin turns it on, sends scrubbed text through OpenRouter (default zero data retention, MSoT 1.7): say so in the second FAQ. Leaked Credentials is partial (operator scan): leave it out. /solutions/finance is the role page for finance teams, not this industry: do not cross-link it as if it were. Overlaps 12.6 (public sector) and /self-hosted: keep this page to the private-sector risk review.

### 12.3 · Scaling AI Adoption in Engineering Across Teams

- **Category · intent · page type:** Industry-Specific Applications · Commercial · Solution
- **Section:** Solutions
- **Plan title:** Running Kite Pulse Across an Enterprise with Many Teams
- **Title tag:** Scaling AI Adoption in Engineering Across Teams | Kite Pulse
- **H1:** Scaling AI Adoption in Engineering: Running Kite Pulse Across an Enterprise with Many Teams
- **URL:** /solutions/enterprise
- **Meta description:** Scaling AI adoption in engineering across many teams: roles, user sync, team budgets and reports on a server in your own AWS account. See what fits.
- **Main keyword:** scaling ai adoption in engineering
- **Secondary keywords:**
  - role based access control dashboard → H2 "Role-based access control: who sees which teams" (main keyword of 2.29: link /blog/role-based-access-control-dashboard)
  - scim user provisioning developer analytics → H2 "User sync: SCIM user provisioning for developer analytics"
  - scim entra id provisioning → H3 "Entra ID and Okta" under the user-sync section (main keyword of 10.14: link /integrations/entra-id-okta)
  - ai budget per team → H3 "An AI budget per team" (main keyword of 5.10, merged into /ai-budgets: link /ai-budgets)
  - deploy developer analytics in your own aws account → H2 "Deploy developer analytics in your own AWS account"
- **Description:** For enterprise engineering leadership and IT who have AI tools in many teams and need one picture without one admin doing everything. Pages ranking for scaling AI adoption are strategy essays and consultancy posts; none shows the mechanics of running a measurement tool across dozens of teams. The page opens with the problem in the buyer's words (adoption is uneven, nobody can see it team by team, and every report is hand-built), a definition block, then a sample organisation (labelled sample data: departments, managers, dated team membership) showing what each level asks. A rollout self-check and a phased plan builder follow, then "How Kite Pulse helps": Manager scope enforced by the server, delegated account management, dated teams, AI Budgets per team or project, Organisation Overview, scheduled company reports, and the AWS install that shows its plan before creating anything. What it does not do sits beside it: no single sign-on, custom roles cannot yet be assigned, no published capacity figure. One Kite Pulse callout at the role section: a manager sees their whole reporting line and nothing else, checked on the server. The reader leaves with a copyable rollout plan by wave.
- **Interactive elements:**
  1. Enterprise readiness check - the reader answers whether reporting lines are recorded, whether teams have owners, who will approve first project lists, and whether an identity provider is in use; each answer maps to the setting that depends on it (manager field, Teams with dates, Onboarding Approvals, user sync). Fallback is a short table of prerequisite and setting.
  2. Rollout plan builder - inputs: number of teams, number of managers, server location (own AWS account or Ubuntu server), identity provider (Entra ID, Okta, none). Output: a copyable plan in waves (pilot team, first department, everyone) with the accounts, roles, approvals and budgets to set at each wave. Fallback paragraph describes the three waves.
  3. Who-sees-what explorer - pick Admin, Manager or Developer and see a sample of which pages and whose data that role reaches by default. Fallback is the role table from MSoT 1.4.
- **Images / video (optional):** None - the explorer and the plan builder carry the page.
- **FAQ:**
  - Can a self-hosted AI usage tracker scale to thousands of developers?
  - How does role-based access work in developer analytics tools?
  - Can I control who can access individual-level usage data and organization-wide reports?
  - Can I compare AI usage between teams?
- **Links to:** /engineering-intelligence, /security, /self-hosted, /ai-budgets, /features (the sheet lists /reports, which the site folds into /features), /solutions/engineering-managers, /integrations/entra-id-okta, /blog/role-based-access-control-dashboard, /docs/roles-and-permissions, /docs/scheduled-email-reports
- **Watch-outs:** User sync with Entra ID and Okta is in the Field Guide and Article Plan, not MSoT Section 1: confirm it is a console switch before writing. When it appears, say "user sync" or "provisioning", never SSO; it does not replace email-and-password sign-in (R8, row note). No two-factor sign-in. Custom roles can be defined on the grid but not assigned (MSoT 1.6). First FAQ: no capacity or load figure exists in the MSoT, so the answer gives a visible placeholder for the owner and describes what scales by design (PostgreSQL, S3 storage, server-only mode), never a number (R2). Fourth FAQ: Team AI Usage, Team Review, AI Collaboration and AI Budgets work by team; Reports has no team filter; the Comparisons page is hidden (R3). Comparing teams must not become ranking people (R4; "Top performers" is an open owner decision). Cost appears per tool, never added across tools; dollar budgets sum priced tools only (R7).

### 12.5 · Team Availability Dashboard for Remote Teams

- **Category · intent · page type:** Industry-Specific Applications · Commercial · Solution
- **Section:** Solutions
- **Plan title:** Distributed and Outsourced Teams Across Time Zones
- **Title tag:** Team Availability Dashboard for Remote Teams | Kite Pulse
- **H1:** A Team Availability Dashboard for Distributed Teams: a Virtual Office for Remote Teams Across Time Zones
- **URL:** /solutions/remote-teams
- **Meta description:** A team availability dashboard for distributed teams: who is online now, leave and on-call, and work that keeps flowing across time zones. Sample office.
- **Main keyword:** team availability dashboard
- **Secondary keywords:**
  - virtual office for remote teams → H2 "A virtual office for remote teams: The Office" (the sheet's original main keyword for this article; link /ai-agent-office)
  - vacation tracker for teams → H2 "Leave & On-Call: a vacation tracker for teams that also keeps the figures fair"
  - team status dashboard → body of the H2 on Team Overview (main keyword of 5.1: link /blog/team-status-dashboard)
  - developer activity heatmap → H3 "Work patterns across time zones" (described from the verified work-pattern facts; see watch-outs)
- **Description:** For heads of distributed engineering and managers of outsourced or vendor teams who cannot see, across time zones, who is available and what is moving. Pages ranking for a team availability dashboard are scheduling and shift tools; none reads availability from the work itself. **Main keyword decision:** the sheet's main keyword, "virtual office for remote teams", has relevance 1 and the row note names "team availability dashboard" (keyword 898) as the stronger fallback; no other article owns 898, and the page's substance is who is available now, so 898 becomes the main keyword and 901 a secondary. Update the Page Map row to match. The page opens with the problem (a stand-up that can never include everyone, holidays read as silence), a definition block, then a sample team across three time zones (labelled sample data). A fairness self-check and a time-zone overlap calculator follow, then "How Kite Pulse helps": Team Overview (who is online and coding now, today against a typical day, refreshed every 30 seconds), The Office presence, Leave & On-Call, offline catch-up, and each lead limited to their own reporting line. One Kite Pulse callout at Leave & On-Call: recorded leave and rotas keep a holiday from reading as disengagement. The reader leaves with a handover-window plan for their team.
- **Interactive elements:**
  1. Time-zone overlap calculator - the reader adds team members' time zones and working hours and sees the shared hours, the handover windows and who is alone at which hour; no Kite Pulse data involved. Fallback paragraph explains how overlap and handover windows are worked out.
  2. "Is your status picture fair?" self-check - five questions (is leave recorded? on-call? company holidays? contractors with accounts? local working hours?) each showing what an unrecorded answer does to a status view. Fallback is the same list in plain text.
  3. Sample office across time zones - a small labelled sample of desks grouped by team, showing online, away and offline at a chosen hour, with leave marked. Fallback paragraph describes the three states.
- **Images / video (optional):** None - the sample office shows presence better than a screenshot, and screenshots must come from a named deployment (MSoT 2.5).
- **FAQ:**
  - How can I see team activity in real time?
  - How do I see what my team is working on without status meetings?
  - What happens to AI session data when developers are offline?
- **Links to:** /features, /ai-agent-office, /engineering-intelligence, /solutions/engineering-managers, /blog/team-status-dashboard, /how-to-run-a-daily-standup, /blog/visualize-ai-agents-working (built)
- **Watch-outs:** The keyword change above needs the sheet's owner to agree; if refused, swap the main and the first secondary back and keep everything else. The day-by-hour heatmap is on Activity Overview per the Field Guide only: describe time-zone patterns from the verified work-pattern facts (peak hour, busiest day, streaks), and do not promise a heatmap until confirmed. The Office's push updates and the Activity feed are Field Guide only; MSoT verifies The Office's presence states and Team Overview's 30-second refresh, so the first FAQ answer rests on those. Figures are as fresh as each computer's latest upload. Outsourced teams: contractors need accounts and each confirms their own projects before anything is sent. Presence is not a timesheet and not tracking of hours (R4): no "monitor your remote team" wording. The admin option to hide others' desks is Article Plan only.

### 12.6 · On-Premise Developer Productivity Tool for Public Sector

- **Category · intent · page type:** Industry-Specific Applications · Commercial · Solution
- **Section:** Solutions
- **Plan title:** Public Sector and Government IT Teams
- **Title tag:** On-Premise Developer Productivity Tool | Kite Pulse
- **H1:** An On-Premise Developer Productivity Tool for Public Sector and Government IT Teams
- **URL:** /solutions/public-sector
- **Meta description:** An on-premise developer productivity tool for public sector IT: runs on infrastructure you control, AI features off by default, an audit log and retention.
- **Main keyword:** on-premise developer productivity tool
- **Secondary keywords:**
  - on prem analytics → H2 "On-prem analytics: four places it can run"
  - privacy preserving analytics → H2 "Privacy-preserving analytics for staff and contractors" (main keyword of 6.6: link /blog/privacy-preserving-analytics)
  - audit log for admin actions → H3 "The audit log for admin actions" (main keyword of 2.31: link /blog/audit-log-for-admin-actions)
  - on premise analytics tools → body of the procurement section (main keyword of 12.2: link /solutions/regulated-industries)
- **Description:** For public-sector and government IT and digital teams who must answer a procurement form before any tool touches staff work. Pages ranking for on-premise developer productivity tools are git-analytics vendors with a self-hosted tier; none starts from a procurement question list. The page opens with the problem (developers use AI assistants, and the department must show where that data goes and who controls it), a definition block, then a sample procurement question list (labelled sample) that the rest of the page answers in order. A procurement self-check and a data-flow statement builder follow, then "How Kite Pulse helps": infrastructure the department controls (one computer, local network, Ubuntu server, or the department's own AWS account), no AI service needed, AI features opt-in, an audit log that cannot be edited, retention windows, export and erasure of one person's data. What it does not offer is stated as plainly: no accreditations or certifications, no single sign-on, no two-factor sign-in. One Kite Pulse callout at the data-flow builder: with AI labelling off, no session text leaves the department's server. The reader leaves with a copyable data-flow statement for their procurement file.
- **Interactive elements:**
  1. Procurement question checker - the reader ticks the questions on their own form (data location, AI service dependency, retention, audit, export and erasure, identity, certifications) and each is marked "answered by a product fact", "the owner or legal supplies this" or "not available today". Fallback is the same table in text.
  2. Data-flow statement builder - the reader sets AI labelling, email, connectors and the Agent API on or off and gets a copyable statement of what leaves the server for each switch (AI labelling: scrubbed text to OpenRouter; email: through the mail relay the operator sets; connectors: to the linked service; Agent API: available when enabled). Fallback paragraph lists each outward link and its default.
- **Images / video (optional):** None - the checker and statement do the work; no compliance badges or seals.
- **FAQ:**
  - Can AI coding analytics be self-hosted on our own infrastructure?
  - Do I need an AI API key to use Kite Pulse?
  - Does Kite Pulse send data to a vendor's cloud?
  - Can we configure how long developer analytics data is retained?
- **Links to:** /self-hosted, /security, /privacy, /solutions/regulated-industries, /blog/audit-log-for-admin-actions, /blog/privacy-preserving-analytics, /docs/install-on-ubuntu, /docs/agent-api
- **Watch-outs:** No accreditation claims (row note, R8): no FedRAMP, G-Cloud, IRAP, Cyber Essentials or similar, and no SOC 2 or ISO. Brain Governance is dropped: the Brain cannot be promoted (R3, row note). Do not claim "air-gapped": updates come from the team's own server, but an air-gapped install is not verified; AI labelling needs internet access to OpenRouter. Retention: "set how long data is kept"; deletion runs once the server operator enables it (fourth FAQ). Erasure anonymises; plain-text working copies stay (MSoT 2.3). No Windows server installer and no Linux desktop program (R8). Connectors' data use in the console was not checked (MSoT 1.6): name them only as outward links. Pricing and procurement terms are owner-supplied placeholders. Overlaps 12.2: that page is the private-sector risk review, this one the procurement file.

### 12.7 · AI Pair Programming Metrics for Bootcamps

- **Category · intent · page type:** Industry-Specific Applications · Commercial · Solution
- **Section:** Solutions
- **Plan title:** Coding Bootcamps and Engineering Education
- **Title tag:** AI Pair Programming Metrics for Bootcamps | Kite Pulse
- **H1:** AI Pair Programming Metrics for Coding Bootcamps and Engineering Courses
- **URL:** /solutions/education
- **Meta description:** AI pair programming metrics for bootcamps and courses: how a cohort works with AI, with learners' consent, guided session review and private pages.
- **Main keyword:** ai pair programming metrics
- **Secondary keywords:**
  - human ai collaboration → H2 "Human-AI collaboration, read across a cohort"
  - claude code session replay → H2 "Guided review with session replay" (main keyword of 2.8: link /blog/claude-code-session-replay)
  - how often developers correct ai → H3 "How often learners correct the AI" (main keyword of 4.7: link /blog/how-often-developers-correct-ai)
  - ai collaboration metrics → body of the cohort section (main keyword of 8.12: link /blog/ai-collaboration-metrics)
- **Description:** For bootcamp and course leads teaching people to code with AI assistants, who want to see how a cohort actually works with them and to coach from real sessions. Pages ranking for AI pair programming metrics are research papers and productivity studies; none gives an instructor a way to read a cohort's sessions with consent. The page opens with the problem (learners hand in working code, and the instructor cannot see whether they understood it or let the AI drive), a definition block, then a sample cohort of twelve learners (labelled sample data, invented names) showing sessions, tools used and commands retried. A consent and fairness self-check and a cohort review planner follow, then "How Kite Pulse helps": each learner confirms their projects before anything is sent and sees their own Privacy page, My Sessions and My Scorecard; the instructor, set as their manager, sees the reporting line only and never their private prompt statistics. What it does not do is stated: it is not a grading tool, a plagiarism checker or a test of understanding. One Kite Pulse callout at the review planner: guided review from the learner's own sessions. The reader leaves with a term plan for review sessions.
- **Interactive elements:**
  1. Consent and fairness self-check - questions for the course lead (have learners agreed in writing? can they see what is collected? will any figure feed a grade? are personal projects excluded?); a "feeds a grade" answer shows a warning that these figures describe work and are not a grade. Fallback is a plain checklist.
  2. Cohort review planner - inputs: term length in weeks, tools taught, review sessions per learner. Output: a copyable schedule of one-to-one reviews built on My Sessions and the scorecard, with what to look at in each. Fallback paragraph describes a sample four-week plan.
- **Images / video (optional):** None - the sample cohort is clearer than screenshots and keeps real learners off the page.
- **FAQ:**
  - How do I identify developers who need support or coaching with AI tools?
  - How can I identify teams that need more AI training?
  - How do I explain AI usage tracking to my team?
- **Links to:** /ai-coding-analytics, /integrations/claude-code, /privacy, /engineering-intelligence, /solutions/developers, /blog/claude-code-session-replay, /blog/how-often-developers-correct-ai, /blog/ai-collaboration-metrics, /blog/developer-scorecard
- **Watch-outs:** Consent framing throughout; never surveillance, grading or ranking language (R4); do not show "Top performers" or "Most active today". Session Playback is Field Guide only, and the verification signal is Field Guide only and needs AI labelling: confirm both, and plan the review section on My Sessions if they are not confirmed. AI labelling sends scrubbed text through OpenRouter (default zero data retention); the institution decides whether learners' text may go there. Work Problems is admin by default. Learners must be in the instructor's reporting line for a Manager to see them (MSoT 1.4). Do not address minors or school pupils. Weak fit: no education keyword was researched (row note); suggest a keyword pass before writing. Names and figures are illustrations.

### 12.8 · Capability Mapping Tools for Game and Product Studios

- **Category · intent · page type:** Industry-Specific Applications · Commercial · Solution
- **Section:** Solutions
- **Plan title:** Game and Product Studios
- **Title tag:** Capability Mapping Tools for Studios | Kite Pulse
- **H1:** Capability Mapping Tools for Game and Product Studios: One Map per Title, Health Across Projects
- **URL:** /solutions/game-studios
- **Meta description:** Capability mapping tools for game and product studios: describe each title as modules and capabilities, and see project health and AI tool use per title.
- **Main keyword:** capability mapping tools
- **Secondary keywords:**
  - capability mapping software → H2 "Capability mapping software that describes a title in plain terms" (main keyword of 8.16: link /blog/capability-mapping-software)
  - project health status dashboard → H2 "Project health across titles" (link /blog/project-health-dashboard, 2.16)
  - ai model adoption tracking → H3 "Which models each title relies on"
  - ai coding tools usage analytics for teams → body of the AI-use section, linking /ai-coding-analytics
- **Description:** For studio technical directors and producers running several titles or products on shared code, who need to know what each title is made of and which ones are moving. Pages ranking for capability mapping tools are business-architecture software for enterprise planners; none describes a software product in modules and capabilities beside live project data. The page opens with the problem (three titles, one shared engine, and nobody can say which parts each title depends on), a definition block, then a sample studio (labelled sample data: three titles, a shared engine repository) with project health and models per title. A self-check and a capability map starter follow, then "How Kite Pulse helps": the Capability Map (modules, capabilities and scenarios, built and approved by a person, with no AI model), All Projects health (active, stable or dormant), one repository on several machines counted as one project, and the Models tab's models by project. One Kite Pulse callout at the map starter: the map lives beside the sessions that change it. The reader leaves with a first capability outline for one title.
- **Interactive elements:**
  1. "Does your studio know what each title is made of?" self-check - five questions (can you list a title's modules? which titles share code? which title had no AI-assisted work last month? who approves a new module?) with what each unanswered question costs. Fallback is the list in text.
  2. Capability map starter - the reader names a title and lists modules (sample: rendering, netcode, store); the tool turns them into a module, capability and scenario outline in the Capability Map's shape, copyable. Fallback paragraph explains the three levels with one example.
  3. Sample studio dashboard - three sample titles with health, sessions, contributors and models used; switching a title updates the cards. Fallback is the same figures as a table.
- **Images / video (optional):** Optional photo or render of The Office on a studio wall screen only if taken from a real deployment and the wall-screen mode is confirmed; otherwise none.
- **FAQ:**
  - How do I find out which projects my team uses AI on the most?
  - Which AI coding tools are our developers using, including Claude Code, Cursor, and GitHub Copilot?
- **Links to:** /features, /integrations, /ai-agent-office, /ai-coding-analytics, /blog/capability-mapping-software, /blog/project-health-dashboard, /blog/duplicate-repository-detection, /solutions/engineering-managers
- **Watch-outs:** Capability Map, All Projects, Duplicate Detection and the Models tab are MSoT Section 1. Capability ownership and bus factor are not: leave them out. The wall-screen mode for The Office is Field Guide only. Kite Pulse reads only the ten AI coding tools (R5): no game-engine, build-farm or asset-pipeline data; say so in "what it does not see". Second FAQ: GitHub Copilot means Copilot Chat in VS Code only (R5). Cost per title appears only through AI Budgets per project (R7). Relevance-1 keyword and no studio keyword researched (row note): flag for a keyword pass.

### 12.9 · Developer Friction for Platform and DevEx Teams

- **Category · intent · page type:** Industry-Specific Applications · Informational · Solution
- **Section:** Solutions
- **Plan title:** Platform and Developer-Experience Teams
- **Title tag:** Developer Friction: A Guide for Platform Teams | Kite Pulse
- **H1:** Developer Friction for Platform and Developer-Experience Teams: Finding It in AI Coding Sessions
- **URL:** /solutions/platform-teams
- **Meta description:** Developer friction for platform and DevEx teams: find shared failing commands, repeated work and old Claude Code versions, then roll out standards.
- **Main keyword:** developer friction
- **Secondary keywords:**
  - devex metrics → H2 "DevEx metrics that come from the work, not a survey" (link the built /blog/developer-experience-metrics)
  - turn repeated workflows into claude code skills → H2 "Turn repeated workflows into Claude Code skills" (main keyword of 3.13: link /blog/turn-workflows-into-claude-code-skills)
  - claude code agent features usage → H3 "Which Claude Code agent features the team uses" (main keyword of 5.13: link the built /blog/claude-code-agent-features-usage)
  - claude code skills used across team → H3 "Skills used across the team" (main keyword of 2.25: link /blog/claude-code-skills-used-across-team)
  - claude code version check → H3 "The Claude Code version check" (main keyword of 4.13: link /blog/claude-code-version-check)
- **Description:** For platform and developer-experience leads whose job is removing shared friction and rolling out standards. Intent is informational, so the page teaches first: what developer friction is, why it now hides inside AI sessions (a broken setup shows up as an agent retrying a command, not as a ticket), and how to find it without a survey. Pages ranking for developer friction are DevEx essays and survey vendors; none reads friction from the sessions. The page opens with the problem, a definition block, then a sample friction log (labelled sample data: one failing test command across five people, an outdated Claude Code on three machines, the same five-step workflow typed by hand every week). A friction sorter and a standards rollout planner follow, then "How Kite Pulse helps": Work Problems (fixed rules, no AI, failed commands and retries grouped with suggested actions), Workflows & Pain Points, the Agent features tab, the Claude Code version check, Skill Candidates (draft skills from repeated workflows, no AI model) and the optional read of installed skills, commands, agents and MCP servers. One Kite Pulse callout at the skills section. The reader leaves with a rollout plan for one standard.
- **Interactive elements:**
  1. Friction sorter - the reader ticks symptoms (agents retrying the same command, long sessions on setup, people on different tool versions, the same instructions typed again) and sees where each friction lives (environment, tooling, knowledge, AI-tool setup) and what to look at first. Fallback is a symptom-to-source table.
  2. Standards rollout planner - the reader picks a standard (a shared skill, a minimum Claude Code version, a CLAUDE.md template) and team size, and gets a copyable rollout plan: announce, pilot, measure the next weeks' sessions, widen. Fallback paragraph describes the four stages.
- **Images / video (optional):** None - the sample friction log and the planner explain more than a screenshot.
- **FAQ:**
  - How do I share AI best practices across my team?
  - How do I find out if developers are on outdated versions of Claude Code?
  - Which Claude Code features (sub-agents, plan mode, MCP tools) does my team use?
- **Links to:** /blog/developer-experience-metrics, /skill-candidates, /ai-agent-office (the sheet lists /parallel-ai-agents, which the site folds into /ai-agent-office), /integrations/claude-code, /engineering-intelligence, /blog/failing-commands-analytics, /blog/developer-pain-points, /blog/ai-coding-standards
- **Watch-outs:** Work Problems and Workflows & Pain Points are admin by default; admins can grant them to managers. Work Problems lists the most affected developers, so frame friction as a system's, not a person's (R4). The installed skills, commands, agents and MCP servers come from an optional read an admin switches on; plugins need app 0.4.3, unconfirmed (MSoT 1.1). The page name "Agent Setup" is from the Article Plan; MSoT verifies the read, not the name: confirm it. Workflows & Pain Points shows prompt text to admins (Field Guide), so do not write that nobody reads prompts. Overlaps 2.15, 11.13 and 3.13: keep this page to the platform team's whole job, and link those for depth. The DevEx survey vendors may be named only with sources and checked dates in the data file (R2).

### 13.1 · How to Track Claude Code Usage: From One Laptop to a Dashboard

- **Category · intent · page type:** Getting Started · Informational · Interactive guide
- **Section:** Guides & tools
- **Plan title:** Install Kite Pulse on Your Own Computer in One Command
- **Title tag:** How to Track Claude Code Usage, Step by Step | Kite Pulse
- **H1:** How to Track Claude Code Usage: From Your Own Sessions to a Self-Hosted Dashboard
- **URL:** /how-to-track-claude-code-usage
- **Meta description:** How to track Claude Code usage: what Claude Code records, how to read it yourself, and how to set up a self-hosted tracker on one computer.
- **Main keyword:** how to track claude code usage
- **Secondary keywords:**
  - track ai coding tool usage → H2 "Step 5: when you use more than one AI tool" (main keyword of 10.1, merged into /integrations: link)
  - local ai coding analytics single user → H2 "Step 6: run a tracker on your own computer" (main keyword of 4.14: link to the built /blog/local-ai-coding-analytics)
  - self-hosted claude code analytics → body of step 6, one sentence that the same install can grow into a team server, linking 13.3
- **Description:** For a developer, or a lead trying it alone first, who wants to know where their Claude Code tokens and sessions go. Today the sheet uses this keyword as a secondary on /integrations/claude-code, with the note "personal how-to; answer in FAQ, then show team view": this guide is that how-to. It teaches the general method first: what Claude Code keeps on the computer, the usage figures Claude Code shows inside a session, reading the session files yourself, and third-party local tools. Only then does it move to a team view. The Kite Pulse callout sits at step 5, where checking by hand stops scaling (several tools or several people): one command sets up the server, worker, collector and database on one computer, reachable from that computer only. The guide ends with sessions appearing in the console and a copyable personal tracking checklist.
- **Interactive elements:**
  1. "What does Claude Code keep?" explorer (step 1) - a labelled sample session line from Claude Code's local history, with its fields highlighted (time, model, input, output and cache tokens); the reader hovers a field to see what it counts. Fallback paragraph names the fields in words.
  2. Token tally (step 3) - the reader pastes a handful of sample lines, or uses the provided sample, and gets a per-day token total and a model split, worked out in the browser and never sent anywhere (said on the widget). Fallback paragraph explains the arithmetic.
  3. Tracking-method picker (step 5) - the reader answers three questions (how many AI tools, how many people, must data stay on our own machines?) and gets the method that fits: Claude Code's own figures, a local open-source reader, a vendor console, or a self-hosted tracker such as Kite Pulse. The result is part of the copyable checklist at the end. Fallback is the same mapping as a short table.
- **Images / video (optional):** One short screen recording of the one-computer install, from the terminal to the first session in the console, only if recorded from a real run and dated (MSoT 2.5); otherwise none.
- **FAQ:**
  - Can one person use Kite Pulse alone?
  - Can AI coding analytics be self-hosted on our own infrastructure?
- **Links to:** /self-hosted (built), /docs (built), /integrations (built), /integrations/claude-code (built), /claude-code-usage-limits (built), /compare/ccusage (built), /blog/local-ai-coding-analytics (built), /blog/self-hosted-ai-usage-tracking (1.2), /docs/install-on-ubuntu (13.3)
- **Watch-outs:** Every fact about Claude Code itself (where it keeps session history, which in-session command shows usage or cost, what the Claude Code analytics in Anthropic's console covers) needs an Anthropic doc URL and checked date in the page's data file (R2); where unverified, write a visible placeholder. Kite Pulse claims: one-computer install (MSoT 1.8), reads the tools' own history with no manual logging (1.1), secrets masked before upload (1.1). The Field Guide's quickstart (Docker, a private repository, the admin@admin.local first sign-in, ports 8080-8099) is an internal install path: how a customer gets the installer is a business fact the owner supplies (MSoT 2.5), so step 6 describes what the command sets up, not the internal script names. Desktop program is Windows and macOS only; no Linux installer (R8). Third-party tools named in step 4 (e.g. ccusage) are described from their own pages with a checked date, and /compare/ccusage owns "ccusage alternative": link, do not compare here. The keyword row still targets /integrations/claude-code as a secondary: move it to this URL in the Page Map.

### 13.3 · Self-Hosted Developer Analytics on Ubuntu or AWS

- **Category · intent · page type:** Getting Started · Commercial · Docs page
- **Section:** Help (Docs)
- **Plan title:** Set Up a Team Server on Ubuntu or in Your Own AWS Account
- **Title tag:** Self-Hosted Developer Analytics on Ubuntu | Kite Pulse
- **H1:** Self-Hosted Developer Analytics on Ubuntu or in Your Own AWS Account: Install Guide
- **URL:** /docs/install-on-ubuntu
- **Meta description:** Install self-hosted developer analytics on Ubuntu 22.04 or 24.04, or in your own AWS account: what the scripts set up, HTTPS, storage and first sign-in.
- **Main keyword:** self-hosted developer analytics ubuntu
- **Secondary keywords:**
  - deploy developer analytics in your own aws account → H2 "Option B: deploy in your own AWS account"
  - self-hosted claude code analytics → H2 "After the install: connect the first developers", one paragraph that Claude Code is one of the ten tools collected out of the box
  - self hosted cursor analytics → same section, H3 "Cursor and the other tools", stating what Cursor provides (MSoT 1.1 table: input and output tokens only, cost usually none)
- **Description:** For IT and server operators who have decided to run a team server and want the exact steps. /self-hosted explains where Kite Pulse can run; this page is the install itself. Prerequisites first (an Ubuntu 22.04 or 24.04 machine, or an AWS account; a name for the server if HTTPS is wanted), then Option A, the Ubuntu script (PostgreSQL, web server, firewall, services that restart if they stop, optional free HTTPS certificates that renew themselves), and Option B, the AWS script (shows its plan first and asks before creating anything; optional private S3 storage). Then the first sign-in, the server-only option, and connecting the first developers (their personal KP- code, consent before any session content uploads). It ends with a "what you have now" summary, the limits, and troubleshooting. One Kite Pulse callout: there is no vendor cloud between the computers and this server.
- **Interactive elements:**
  1. Install path picker - the reader picks Ubuntu or AWS, HTTPS on or off, and local disk or S3, and gets the matching prerequisites and step list to copy. Fallback is the two options written out in full below it, so nothing depends on the picker.
- **Images / video (optional):** None - a terminal screenshot adds nothing the step list does not say, and real output must come from a dated run (MSoT 2.5).
- **FAQ:**
  - What infrastructure does a self-hosted AI coding analytics server need?
  - Can a self-hosted AI usage tracker scale to thousands of developers?
  - Can AI coding analytics be self-hosted on our own infrastructure?
- **Links to:** /self-hosted (built), /docs (built), /security, /blog/self-hosted-ai-usage-tracking (1.2), /how-to-track-claude-code-usage (13.1), /integrations/cursor (built), /integrations/claude-code (built)
- **Watch-outs:** Facts from MSoT 1.8: Ubuntu 22.04 or 24.04, PostgreSQL, local disk or S3, HTTPS set up by the automated install and requirable on any install, but optional; do not imply it is always on. R8: no Linux desktop installer, no Windows server installer, no hosted SaaS, no encryption at rest (at-rest encryption comes from the operator's disk encryption or S3, MSoT 2.4). The second FAQ has no measured answer: no sizing or developer-count figure exists in the sources, so answer with what is known (PostgreSQL, one server, storage on disk or S3) and a visible placeholder for sizing guidance the owner supplies (R2). Server hardware minimums are not in the MSoT: placeholder. Email for invitations and resets needs the server's mail settings (MSoT 2.1). /self-hosted is built and owns "self-hosted developer analytics": keep this page to the install steps and link up to it. The keyword row still targets /self-hosted as a secondary: move it here in the Page Map.

### 13.8 · AI Coding Budget Alerts per Team or Project

- **Category · intent · page type:** Getting Started · Commercial · Docs page
- **Section:** Help (Docs)
- **Plan title:** Set Up Monthly AI Budgets, Seat Prices and Hourly Rates
- **Title tag:** AI Coding Budget Alerts per Team or Project | Kite Pulse
- **H1:** AI Coding Budget Alerts: Set Monthly Budgets, Seat Prices and Hourly Rates
- **URL:** /docs/ai-budget-alerts
- **Meta description:** Set up AI coding budget alerts: a monthly budget per team or project in tokens or estimated dollars, alerts at 80% and 100%, plus seat prices.
- **Main keyword:** ai coding budget alerts
- **Secondary keywords:**
  - ai budget per team → H2 "Step 2: set a monthly AI budget per team" (main keyword of 2.21 and 5.10, merged into /ai-budgets: link)
  - monthly ai budget per project → H2 "Step 3: or a monthly AI budget per project"
  - token budget alerts → H2 "Step 4: tokens or dollars, and when the token budget alerts fire"
  - ai coding seat cost tracking → H2 "Step 5: enter seat prices" (main keyword of 2.23: link to /blog/ai-coding-seat-cost-tracking)
  - ai coding tools budget management → closing H2 "Running the budget month to month", one paragraph (main keyword of 11.3: link to /blog/ai-coding-tools-budget-management)
- **Description:** For admins and finance owners who have agreed a number and need to put it in. The built /ai-budgets explains the feature and 6.14 (/ai-spending-limits) walks through deciding the limits; this page is the settings path. Prerequisites (admin role; teams set up on Teams if budgeting by team; email configured on the server if alerts should reach inboxes), then the steps: open AI Budgets, choose team or project, choose tokens or estimated US dollars, set the monthly amount, check who is told on Notifications, then enter seat prices on Hourly Rates & Seat Prices. It ends with what the alerts look like at 80% and 100%, the limits, and troubleshooting ("why does my dollar budget not include Cursor?"). One Kite Pulse callout at step 4: a dollar budget sums the priced tools only and reports unpriced tokens separately, so nothing is silently counted as $0.
- **Interactive elements:**
  1. Budget preview - the reader enters a sample monthly amount, picks tokens or dollars, and drags a "month so far" slider over labelled sample usage; markers show where the 80% and 100% alerts would fire, and a dollar budget shows a separate "unpriced tokens" line for Codex, Cursor and Copilot. Fallback paragraph states the two thresholds and the unpriced rule in words.
- **Images / video (optional):** None - the preview shows the alert points; a console screenshot would need a dated deployment (MSoT 2.5).
- **FAQ:**
  - How do I set a budget for AI coding tools per team?
  - Can I set spending limits and receive alerts when teams exceed their budgets?
  - How do I set an AI coding-tool budget for each team?
- **Links to:** /ai-budgets (built), /ai-cost-tracking (built), /shadow-ai (built), /ai-spending-limits (6.14), /blog/ai-coding-seat-cost-tracking (2.23), /blog/ai-coding-tools-budget-management, /docs/slack-notifications (13.12)
- **Watch-outs:** MSoT 1.2: monthly budget per team or per project, in tokens or estimated US dollars, alerts at 80% and 100%; dollar budgets add up priced tools and report unpriced tokens separately; cost is an estimate from list prices, "not billed spend" (R7). Budgets are never per person (say so; the first and third FAQs are near-duplicates, so answer the third briefly and point to the first). An alert is a notice, not a stop: nothing in the MSoT blocks usage at 100%, so never say a budget "caps" or "stops" spend. Seat prices appear on the Team AI Usage Overview for admins (MSoT 1.2). Hourly cost per role level is in the Article Plan only: confirm in the console before writing that step, and never per person. Budget alerts reaching Slack is Field Guide only: leave Slack out or flag it. The keyword row still targets /ai-budgets as a secondary: move it here in the Page Map.

### 13.9 · Roles and Permissions Dashboard: Setup Guide

- **Category · intent · page type:** Getting Started · Informational · Docs page
- **Section:** Help (Docs)
- **Plan title:** Configure Roles, Permissions and Delegated Account Management
- **Title tag:** Roles and Permissions Dashboard: Setup Guide | Kite Pulse
- **H1:** Roles and Permissions Dashboard: Grant Pages, Delegate Accounts and Check Who Sees What
- **URL:** /docs/roles-and-permissions
- **Meta description:** Use the roles and permissions dashboard to grant pages per role, delegate account management to managers and check who can see individual data.
- **Main keyword:** roles and permissions dashboard
- **Secondary keywords:**
  - roles and permissions matrix → H2 "Step 2: read the roles and permissions matrix" (the view and edit grid per page)
  - delegate admin access → H2 "Step 4: delegate account management to a manager", with a sentence that delegation covers accounts for their own team, not full admin access
  - custom rbac roles → H3 "Custom roles: what works today" (can be defined on the grid, cannot yet be assigned)
  - rbac best practices → H2 "Good practice before rollout" (least access first, grant pages to managers one at a time, review the audit log)
  - audit log for admin actions → body of the good-practice section (main keyword of 2.31: link to /blog/audit-log-for-admin-actions)
- **Description:** For admins setting up access before a rollout. Ranking pages for this keyword are help docs for unrelated products; nothing explains roles for a developer-analytics tool. The page starts with the three access roles (Admin sees everyone, Manager sees themselves and their whole reporting line, Developer sees their own pages plus The Office, Needs attention and Help) and that the server enforces scope, not only the screen. Steps: set each person's access role, work role and manager on Accounts & Roles; read the grid on Roles & Permissions; grant a page to managers (for example Blocker Board or Workflows & Pain Points, admin by default); delegate account management for a team; check the result with a test account. One Kite Pulse callout: private prompt statistics are removed by the server for everyone except the developer, whatever the grid says. Ends with limits and troubleshooting ("a manager cannot see a person": check the manager field).
- **Interactive elements:**
  1. "Who sees this page?" grid preview - a small sample of the permissions grid (five pages, three roles); the reader toggles a page on for Manager and a sample manager's view updates, with private fields that stay hidden marked as such. Fallback is the same grid as a static table with the defaults.
- **Images / video (optional):** None - the grid preview is the picture; a console screenshot would need a dated deployment.
- **FAQ:**
  - How does role-based access work in developer analytics tools?
  - Can I control who can access individual-level usage data and organization-wide reports?
  - Can my manager see everything I type to the AI?
- **Links to:** /security, /features (built), /privacy (built), /blog/role-based-access-control-dashboard (2.29), /blog/audit-log-for-admin-actions (2.31), /blog/can-my-employer-see-my-claude-code-chats (built), /integrations/entra-id-okta (10.14)
- **Watch-outs:** MSoT 1.4 and 1.6: three roles, server-enforced scope, grid per page per role, custom roles definable but not assignable (do not imply custom roles work, per the keyword note on id 1023), delegated account management, Organisation Overview admin by default. R8: no single sign-on, no two-factor sign-in; user sync (10.14) is provisioning, not SSO. Third FAQ: prompt statistics are private to the developer and managers who do not work on a project see folder labels, not full paths (MSoT 1.7); but the Field Guide says Workflows & Pain Points shows prompt text to admins and a developer's own work, so the answer must not say managers or admins can never see any prompt text; link to the built /blog/can-my-employer-see-my-claude-code-chats for the full answer. "Hide other people's desks in The Office" is in the Article Plan only: confirm before including. 2.29 covers the same pages as a feature article: keep this page to the setup steps.

### 13.12 · Claude Code Slack Notifications: Two Ways

- **Category · intent · page type:** Getting Started · Commercial · Docs page
- **Section:** Help (Docs)
- **Plan title:** Configure Notifications and Alerts
- **Title tag:** Claude Code Slack Notifications: Two Ways | Kite Pulse
- **H1:** Claude Code Slack Notifications: a Hook for One Developer, Alerts for the Team
- **URL:** /docs/slack-notifications
- **Meta description:** Claude Code Slack notifications two ways: a hook that posts from your own machine, and team alerts and the daily digest sent to a Slack channel.
- **Main keyword:** claude code slack notifications
- **Secondary keywords:**
  - claude code slack webhook → H2 "Way 1: a Claude Code hook that posts to a Slack webhook"
  - ai spend alerts → H2 "Way 2: team alerts in Kite Pulse", H3 "AI spend alerts from budgets"
  - ai budget slack alerts → body of that H3, one sentence, flagged (see watch-outs)
  - ai agent stuck notification → H3 "Which notices stay in the console" (main keyword of 2.10: link to /blog/ai-agent-stuck-notification)
- **Description:** For developers and admins who searched for Claude Code in Slack. Most searchers want Claude Code itself to ping them when it finishes or needs input, which Claude Code's own hooks can do from the developer's machine; Kite Pulse does not do that, and the page says so first (R9). Way 1 explains the hook approach generally (where hooks are configured, which event fires, posting to a Slack incoming webhook) with the source. Way 2 is the team side in Kite Pulse: admins choose who is told what on Notifications, with the in-app bell, email and a daily digest; then the Slack channel for alerts, its Test button and delivery history, if confirmed. The page ends with a "which way do I need?" summary, limits and troubleshooting. One Kite Pulse callout in Way 2: one alert list shared by the team, with acknowledge and resolve.
- **Interactive elements:**
  1. "Which way do I need?" picker - the reader picks what they want to hear about (my own session finished, my session needs me, a team budget at 80%, a server problem, a stuck agent) and sees whether a Claude Code hook, Kite Pulse Notifications, or neither covers it, and where it arrives. Fallback is the same mapping as a table.
- **Images / video (optional):** None.
- **FAQ:**
  - Can I set spending limits and receive alerts when teams exceed their budgets?
- **Links to:** /integrations (built), /ai-budgets (built), /docs (built), /integrations/claude-code (built), /blog/ai-agent-stuck-notification (2.10), /docs/ai-budget-alerts (13.8)
- **Watch-outs:** Slack alerts are NOT in MSoT Section 1: it verifies alerts with acknowledge and resolve, the in-app bell, email and the daily digest, with admins choosing recipients on Notifications (MSoT 1.6); Slack appears there only as a Connector. "Alerts to Slack" (open, escalate and resolve messages plus the digest to a webhook, minimum severity, hourly limit) is Field Guide only, and the keyword row's own note says the same: confirm before writing Way 2's Slack part; until then Way 2 covers bell, email and digest, and Slack is "coming soon" or left out. The Field Guide says plan-limit and agent-stuck notices reach the person and their manager "in the console only": say they do not go to Slack. Budget alerts on Slack "if alerts go there" is Field Guide only. Email needs the server's mail settings (MSoT 2.1). Claude Code hook facts need Anthropic doc URLs and checked dates (R2); show a webhook URL only as an obvious placeholder. Commercial intent is weak for the hook half; keep the page useful to someone who never buys. The keyword row still targets /integrations as a secondary: move it here in the Page Map.

### 13.13 · Claude Code Limit Monitor: Fresher Plan Figures

- **Category · intent · page type:** Getting Started · Commercial · Docs page
- **Section:** Help (Docs)
- **Plan title:** Get Fresher Claude Plan Figures with the Background Refresh
- **Title tag:** Claude Code Limit Monitor: Fresher Plan Figures | Kite Pulse
- **H1:** Claude Code Limit Monitor: Turn On the Background Refresh for Fresher Plan Figures
- **URL:** /docs/claude-plan-refresh
- **Meta description:** Set up a Claude Code limit monitor for your team: turn on the background plan refresh, choose how often it runs, and see who is near a limit.
- **Main keyword:** claude code limit monitor
- **Secondary keywords:**
  - claude code limit tracker → H2 "How the limit tracker gets its figures", explaining that plan figures come from what Claude Code saves on each computer
  - claude code remaining usage → H2 "Step 4: check remaining usage, worst first"
  - claude code limit dashboard → body of step 4 (Plan headroom on Team AI Usage, and the Headroom view), linking /plan-headroom
  - claude code team usage visibility → H2 "Who sees whose figures" (developers their own on Workspace; managers their reporting line; admins everyone)
- **Description:** For admins who see "stale" on Plan headroom and want current figures. By default plan figures are as fresh as the last time Claude Code saved them on each computer; the optional background refresh keeps them current without using any tokens. Prerequisites (admin role; desktop program 0.4.2 or later on each computer, checked on Machines), then steps: switch on the refresh under Settings › Retention › Kite Pulse app reads, choose how often it runs, tell developers they can turn it off, then read Plan headroom: the 5-hour, weekly and per-model weekly windows, "near" at 80% or more, "at limit" at 100%, old readings flagged rather than hidden. The page ends with how long readings are kept, the limits (Claude Code only) and troubleshooting ("still stale": the computer is off, an older app, or the developer opted out). One Kite Pulse callout at step 4: who is closest to a limit, worst first.
- **Interactive elements:**
  1. Freshness simulator - a labelled sample team of five; the reader switches the refresh off and on and sees which rows show "stale" and why (laptop asleep, app older than 0.4.2, developer opted out), with the near/at-limit thresholds marked. Fallback paragraph lists the three reasons a reading stays old.
- **Images / video (optional):** None - the simulator shows staleness better than a screenshot, and a real one would need a dated deployment.
- **FAQ:**
  - How do I know which developers are close to their Claude limit?
  - claude code how close am i to the limit
  - How can a Claude team admin see who is close to their usage limit?
- **Links to:** /plan-headroom (built), /claude-code-usage-limits (built), /integrations/claude-code (built), /blog/avoid-hitting-claude-limit (built), /blog/sprint-planning-claude-plan-limits (built), /blog/personal-claude-code-usage-stats (2.4), /docs/install-on-ubuntu (13.3)
- **Watch-outs:** MSoT 1.1 and 1.2: plan figures come from what Claude Code saves on the computer, no login or password is read; the background refresh is an admin switch, app 0.4.2 or later, uses no tokens, developer can turn it off; Plan headroom is Claude Code only and other tools show "Not reported by this tool" (R7, never "limits across tools"). "Choose how often it runs" and the retention period for readings are from the Article Plan and MSoT 1.6 (Retention sets how long plan-usage history is kept): confirm the interval control in the console. The status-line reading for fresher figures is unreleased (MSoT 2.3): leave it out. Rewrite the second FAQ as a full question ("How close am I to my Claude Code limit?") on the page; keep the sheet's wording for matching. The Headroom view in The Office is Field Guide only: mention it only if confirmed. The keyword row still targets /plan-headroom as a secondary: move it here in the Page Map, and keep /plan-headroom as the feature page.

### 13.16 · How to Connect Claude Code to an MCP Server

- **Category · intent · page type:** Getting Started · Informational · Interactive guide
- **Section:** Guides & tools
- **Plan title:** Connect Your AI Assistant to Kite Pulse over MCP
- **Title tag:** How to Connect Claude Code to an MCP Server | Kite Pulse
- **H1:** How to Connect Claude Code to an MCP Server, Then Cursor and VS Code
- **URL:** /how-to-connect-claude-code-to-mcp
- **Meta description:** How to connect Claude Code to an MCP server, then Cursor and VS Code: config files, API keys in headers, read-only access, and testing first.
- **Main keyword:** how to connect claude code to mcp server
- **Secondary keywords:**
  - how to add mcp server to cursor → H2 "Step 5: add the same MCP server to Cursor"
  - how to add mcp server to vscode → H2 "Step 6: add it to VS Code"
  - mcp server api key → H2 "Step 3: pass the MCP server API key in a header, not in the file you commit"
  - read only mcp server → H2 "Step 2: start with a read-only MCP server" (main keyword of 10.9, merged into /docs: link)
  - mcp dry run → body of step 7 (main keyword of 10.12: link to /docs/mcp-dry-run)
  - claude code analytics admin api → H3 "Usage data without MCP" in the closing section, one paragraph on Anthropic's own analytics API, with source
- **Description:** For developers and managers who want an AI assistant to read data from another system. Ranking pages are tutorials for one vendor's own server; none covers Claude Code, Cursor and VS Code on one page with a real read-only example. The guide teaches the general method first: what an MCP server is, choosing read-only access, adding a server to Claude Code with its URL and an API key in a header, checking it is connected, then the same server in Cursor and VS Code, then testing with a harmless question. Kite Pulse is the worked example from step 4: its MCP server is available when enabled, a key never sees more than its owner, and "chat" mode gives only a few tools. The Kite Pulse callout sits at step 7: preview what a write would do before it runs. The guide ends with a copyable per-editor config block, with the key as a placeholder.
- **Interactive elements:**
  1. Config builder (steps 3-6) - the reader picks the editor (Claude Code, Cursor, VS Code), enters a server URL (a placeholder is prefilled) and chooses header-based key or none, and gets the command or config block for that editor, with the key shown as a placeholder and a reminder not to commit it. Fallback shows all three config blocks as plain text.
  2. Read-only or read-write? check (step 2) - the reader picks what they want the assistant to do (answer questions, summarise a week, change records) and sees the least access that does it. For Kite Pulse this maps to chat mode or direct access, and the widget says an admin chooses the mode. Fallback is a three-row table.
- **Images / video (optional):** None - the config builder carries the steps.
- **FAQ:**
  - Is there an API or MCP server for engineering analytics?
  - Can an AI assistant write my weekly team update from engineering data?
  - Can I let an AI assistant summarise my team's engineering activity?
- **Links to:** /docs (built), /blog/ai-weekly-team-report (built), /integrations/claude-code (built), /integrations/cursor (built), /integrations/github-copilot (built), /docs/agent-api (10.7), /docs/mcp-dry-run (10.12)
- **Watch-outs:** Kite Pulse's MCP server and Agent API are NOT default: MSoT 2.1 lists them as "needs operator setup" (two server settings), so every Kite Pulse step says "available when enabled", an admin issues the key, and the operator turns it on (R8). Facts from MSoT 2.1 to state carefully: Streamable HTTP at /api/v1/agent/mcp; a key never sees more than its owner, re-checked on every request; chat mode gives ask, whoami and my_usage, and ask needs a separate Agent API AI key and by default an admin-only permission, so a non-admin's chat-mode key can only call whoami and my_usage; direct mode adds about 115 read tools and optional write tools with a dry-run preview; prompt text and AI replies are never available over MCP. "Try a question" before handing out a key is Field Guide only: flag it. The second and third FAQs depend on direct access or the ask tool: answer honestly that this needs an admin's choice. All Claude Code, Cursor and VS Code config syntax and Anthropic's analytics API need vendor doc URLs and checked dates in the page's data file (R2). VS Code here means the editor's own MCP support; Kite Pulse collects only GitHub Copilot Chat in VS Code (R5). /docs owns "mcp server developer analytics": link to it, do not compete.

### 13.18 · Scheduled Email Reports for Engineering Leaders

- **Category · intent · page type:** Getting Started · Informational · Docs page
- **Section:** Help (Docs)
- **Plan title:** Schedule Reports for Leadership
- **Title tag:** Scheduled Email Reports for Engineering Leaders | Kite Pulse
- **H1:** Scheduled Email Reports: Send Engineering and AI Usage Reports Daily, Weekly or Monthly
- **URL:** /docs/scheduled-email-reports
- **Meta description:** Set up scheduled email reports: the company or one developer's report by email daily, weekly or monthly as PDF or CSV, with preview and send history.
- **Main keyword:** scheduled email reports
- **Secondary keywords:**
  - automated email reports → body of the short answer
  - weekly status report email → H2 "Step 3: choose daily, weekly or monthly", with the weekly status report email as the common case
  - weekly report email to manager → H3 "A weekly report email to a manager" (the developer's report to their manager)
  - weekly engineering report → body of that step (main keyword of 3.11: link to /blog/weekly-engineering-report)
  - monthly engineering report → body of the same step (main keyword of 11.10: link to /blog/monthly-engineering-report)
  - ai usage report pdf → H2 "Step 4: PDF or CSV"
  - export claude usage data → H2 "Downloading instead of emailing", covering the Company report download and the Plan usage report as Excel
- **Description:** For admins and engineering managers who want leadership to get the report without anyone building it. Ranking pages are help docs for unrelated products; nothing covers engineering reports. Prerequisites (admin role; email set up on the server; recipients' addresses), then steps: choose the report (the Company report, or one developer's report), choose the recipients, choose daily, weekly or monthly, choose PDF or CSV, preview, save, then check the send history. A short section covers downloading instead (Company report as CSV or PDF; Plan usage report as Excel; admins by default). The page ends with limits and troubleshooting ("nothing arrived": check email settings and the send history). One Kite Pulse callout: the Company report compares any period with the one before.
- **Interactive elements:**
  1. Schedule preview - the reader picks report, cadence and format and sees the next three send dates and a labelled sample of the report's first page. Fallback paragraph lists the two reports, three cadences and two formats.
- **Images / video (optional):** One real report page as an image, only if exported from a dated deployment (MSoT 2.5); otherwise the sample in the preview.
- **FAQ:**
  - How do I create a weekly AI usage report for my team?
  - Can I export reports or integrate the data with our existing analytics and finance systems?
- **Links to:** /features (built; the sheet lists the hidden reports page, which the site folds into /features), /engineering-intelligence (built), /blog/scheduled-engineering-reports (2.28), /blog/company-ai-usage-report (built), /blog/ai-weekly-team-report (built), /blog/weekly-engineering-report (3.11), /blog/monthly-engineering-report, /docs/agent-api (10.7)
- **Watch-outs:** MSoT 1.3: Company report for any period against the previous one, CSV or PDF (admins by default); Plan usage report as Excel (admins by default), history starts when recording began; scheduled reports send the Company report or one developer's report daily, weekly or monthly as PDF or CSV with a preview and send history; admins set them up and email must be configured on the server (MSoT 2.1). Reports have no team filter (MSoT corrections): do not promise a per-team report. Second FAQ: exports are CSV, PDF and Excel; there is no built-in finance-system integration; the Agent API is "available when enabled" (MSoT 2.1), never a default. Do not link /reports (hidden). 2.28 covers the same feature as an article: keep this page to the setup steps. "Schedule time" or time-zone controls are not in the sources: leave out.
