import { useEffect, useMemo, useState } from 'react'

/**
 * KITE PULSE - shared by the admin panel (KitePulsePanel.jsx) and the site
 * preview (KitePulseSite.jsx), so the two cannot disagree about which section
 * a page is in or which pages have a prototype. See README.md in this folder.
 *
 * Everything comes from the keyword research sheet, converted to
 * `data/sheet.json` by `import_sheet.py`. The JSON is a dynamic import, so its
 * ~330 KB is a separate chunk only these two screens download.
 */

// THE WEBSITE'S SECTIONS, in display order. `slug` is the section's address
// under /kite-pulse, where its pages are listed.
//
// ⚠ A section with a `hub` has NO list address of its own: the Page Map
// already has that page (`/integrations`, `/blog`, `/glossary`), and it IS the
// section index. A second address for the same list would be two pages saying
// one thing.
export const SECTIONS = [
  { name: 'Home', slug: null },
  { name: 'Product', slug: 'product' },
  { name: 'Trust', slug: 'trust' },
  { name: 'Solutions', slug: 'solutions' },
  { name: 'Guides & tools', slug: 'guides' },
  { name: 'Glossary', slug: 'glossary', hub: '/glossary' },
  { name: 'Integrations', slug: 'integrations', hub: '/integrations' },
  { name: 'Blog', slug: 'blog', hub: '/blog' },
  { name: 'Compare', slug: 'compare' },
  { name: 'Help', slug: 'help' },
  { name: 'Legal', slug: 'legal' },
]

// THE SITE'S STRUCTURE (2026-10-22), after reviewing mentlio.com, a direct
// competitor: a short top bar with a few dropdowns, a demo button, and a
// four-column footer. The page addresses stay the keyword sheet's.
//
// A menu entry is either a dropdown of pages (`sections`, minus `except`) or
// one page (`to`). Footer columns work the same way, plus `hubs`: links to
// section lists rather than to pages.
export const MENU = [
  { label: 'Product', sections: ['Product', 'Trust'], except: ['/pricing', '/about'] },
  { label: 'Solutions', sections: ['Solutions'] },
  { label: 'Guides', sections: ['Guides & tools', 'Glossary'] },
  { label: 'Integrations', to: '/integrations' },
  { label: 'Blog', to: '/blog' },
  { label: 'Pricing', to: '/pricing' },
  { label: 'Docs', to: '/docs' },
]
// DROPDOWN GROUPS (2026-11-04). The Article Plans took Solutions from 6 pages
// to 13 and Guides & tools from 6 to 15, too many for one list. A section named
// here is split into labelled groups, first matching test wins; a section not
// named here stays one list. The last test of each catches everything, so no
// page drops out of the menu.
const ROLE_PAGES = ['/solutions/engineering-managers', '/solutions/finance', '/solutions/developers']
export const MENU_GROUPS = {
  Solutions: [
    ['By role', (p) => ROLE_PAGES.includes(p.url)],
    ['By industry', (p) => p.url.startsWith('/solutions/')],
    ['By need', () => true],
  ],
  'Guides & tools': [
    ['Tools', (p) => p.type === 'Interactive tool'],
    ['Guides', () => true],
  ],
}
/** `[label, pages]` pairs for one section's dropdown, empty groups left out. Label is null for an ungrouped section. */
export function groupsOf(section, pages) {
  const tests = MENU_GROUPS[section]
  if (!tests) return [[null, pages]]
  const groups = tests.map(([label]) => [label, []])
  for (const p of pages) groups[tests.findIndex(([, test]) => test(p))][1].push(p)
  return groups.filter(([, list]) => list.length)
}
export const FOOTER = [
  { title: 'Product', sections: ['Product', 'Trust'], except: ['/pricing', '/about'] },
  { title: 'Solutions', sections: ['Solutions'] },
  { title: 'Resources', hubs: ['Guides & tools', 'Glossary', 'Blog', 'Compare'] },
  { title: 'Company', urls: ['/about', '/pricing', '/docs', '/changelog', '/faq', '/legal/privacy-policy', '/legal/terms'] },
]

// PAGES THE SITE STRUCTURE NEEDS THAT THE KEYWORD SHEET DOES NOT LIST YET
// (2026-10-22). Kept apart from the sheet's pages, so no count of the sheet's
// Page Map changes, and marked "proposed" wherever they show. Add them to the
// sheet's Page Map to make them real; then delete them here.
export const PROPOSED = [
  { url: '/glossary', type: 'Glossary', main: 'glossary of common ai terms',
    notes: 'An index of short definitions, one page per term. Mentlio ranks with /glossary/tokenmaxxing. Article Plan 1.8 (Kite Pulse Terms in Plain Words) is this page.' },
  { url: '/glossary/tokenmaxxing', type: 'Glossary', main: 'tokenmaxxing',
    notes: 'Keyword rows 581 (Main) and 582 (FAQ, "what is tokenmaxxing") target /blog/measure-developer-productivity-ai today, and the Page Map notes ask whether tokenmaxxing needs its own page. Mentlio answered that with /glossary/tokenmaxxing. Moving the two rows here would answer it for us.' },
  { url: '/changelog', type: 'Docs',
    notes: 'What changed in each Kite Pulse release. Mentlio has one; it shows a product that is maintained.' },
  // Article Plan categories 1-2 (2026-11-03): the 30 articles in
  // docs/Kite Pulse - Article Production Plan (Categories 1-2).md, built as
  // interactive pages. Most are blog posts; five sit in another section
  // (2026-11-04): 1.8 is /glossary above, 1.6 the /compare overview, 1.9 and
  // 1.12 Docs pages, 2.24 an interactive guide. Their keyword rows still target
  // other URLs in the sheet; move them to these URLs in the Page Map to make
  // the pages real.
  { url: '/blog/self-hosted-ai-usage-tracking', type: 'Blog', main: 'self-hosted ai usage tracking',
    notes: 'Article Plan 1.2: The Three Parts of Kite Pulse: Desktop Program, Your Server, Web Console' },
  { url: '/blog/secret-masking', type: 'Blog', main: 'secret masking',
    notes: 'Article Plan 1.3: From a Developer\'s Laptop to the Console: a Session\'s Journey in Six Steps' },
  { url: '/compare', type: 'Compare', main: 'software engineering intelligence',
    notes: 'Article Plan 1.6: How Kite Pulse Is Different from Other Engineering Tools' },
  { url: '/blog/employer-see-claude-code-prompts', type: 'Blog', main: 'can my employer see my claude code prompts',
    notes: 'Article Plan 1.7: What Kite Pulse Is Not' },
  { url: '/docs/how-figures-are-calculated', type: 'Docs', main: 'claude code estimated cost',
    notes: 'Article Plan 1.9: Where the Numbers Come From' },
  { url: '/blog/ai-assisted-development-analytics', type: 'Blog', main: 'ai assisted development analytics',
    notes: 'Article Plan 1.11: One Loop: Capture, Understand, Act, Learn' },
  { url: '/docs/console-map', type: 'Docs', main: 'ai usage dashboard for developers',
    notes: 'Article Plan 1.12: A Map of the Console' },
  { url: '/blog/duplicate-repository-detection', type: 'Blog', main: 'duplicate repository detection',
    notes: 'Article Plan 2.2: Automatic Project Detection' },
  { url: '/blog/personal-claude-code-usage-stats', type: 'Blog', main: 'personal claude code usage stats',
    notes: 'Article Plan 2.4: Workspace: Is My Work Being Captured?' },
  { url: '/blog/developer-scorecard', type: 'Blog', main: 'developer scorecard',
    notes: 'Article Plan 2.5: My Scorecard & Insights: a Top 3 to Act On' },
  { url: '/blog/developer-working-style', type: 'Blog', main: 'developer working style',
    notes: 'Article Plan 2.6: How You Work: My Activity, Work Patterns, Working Style and Private Prompt Statistics' },
  { url: '/blog/search-past-ai-coding-sessions', type: 'Blog', main: 'search past ai coding sessions',
    notes: 'Article Plan 2.7: My Sessions: Finding the Session You Need' },
  { url: '/blog/claude-code-session-replay', type: 'Blog', main: 'claude code session replay',
    notes: 'Article Plan 2.8: Inside One Session: Playback, Summary and Segments' },
  { url: '/blog/claude-code-activity-log', type: 'Blog', main: 'claude code activity log',
    notes: 'Article Plan 2.9: What the Agent Did: a Step-by-Step Record Without Message Text' },
  { url: '/blog/ai-agent-stuck-notification', type: 'Blog', main: 'ai agent stuck notification',
    notes: 'Article Plan 2.10: Notices in the Bell: Plan Limit Reached, AI Agent Stuck and Claude Code Out of Date' },
  { url: '/blog/what-is-my-team-working-on', type: 'Blog', main: 'what is my team working on dashboard',
    notes: 'Article Plan 2.11: Team Overview, All Developers and Organisation Overview' },
  { url: '/blog/claude-code-multi-agent-dashboard', type: 'Blog', main: 'claude code multi agent dashboard',
    notes: 'Article Plan 2.12: The Developer Page: One Person in Full' },
  { url: '/blog/team-collaboration-insights', type: 'Blog', main: 'team collaboration insights',
    notes: 'Article Plan 2.13: Collaboration, Teams, and Leave & On-Call' },
  { url: '/blog/failing-commands-analytics', type: 'Blog', main: 'failing commands analytics',
    notes: 'Article Plan 2.14: Work Problems, Insight Rules and the Insights Catalog' },
  { url: '/blog/developer-pain-points', type: 'Blog', main: 'developer pain points',
    notes: 'Article Plan 2.15: Workflows & Pain Points: Where Work Repeats and Where It Slows Down' },
  { url: '/blog/project-health-dashboard', type: 'Blog', main: 'project health dashboard',
    notes: 'Article Plan 2.16: All Projects and the Project Page' },
  { url: '/blog/shared-ai-tool-accounts', type: 'Blog', main: 'shared ai tool accounts',
    notes: 'Article Plan 2.22: Tool Accounts: Shared, Separate and Personal Accounts' },
  { url: '/blog/ai-coding-seat-cost-tracking', type: 'Blog', main: 'ai coding seat cost tracking',
    notes: 'Article Plan 2.23: Hourly Rates & Seat Prices' },
  { url: '/claude-code-tokens-per-second', type: 'Interactive guide', main: 'claude code tokens per second',
    notes: 'Article Plan 2.24: Generation Rate: How Fast AI Replies Arrive' },
  { url: '/blog/claude-code-skills-used-across-team', type: 'Blog', main: 'claude code skills used across team',
    notes: 'Article Plan 2.25: Agent Setup: Claude Code Skills, Commands, Agents and MCP Servers Across the Team' },
  { url: '/blog/scheduled-engineering-reports', type: 'Blog', main: 'scheduled engineering reports email',
    notes: 'Article Plan 2.28: Company Reports and Scheduled Reports' },
  { url: '/blog/role-based-access-control-dashboard', type: 'Blog', main: 'role based access control dashboard',
    notes: 'Article Plan 2.29: Who Sees What: Roles & Permissions, Accounts and Sign-in' },
  { url: '/blog/audit-log-for-admin-actions', type: 'Blog', main: 'audit log for admin actions',
    notes: 'Article Plan 2.31: Data Rights: Export, Erase, Audit Log and Retention' },
  { url: '/blog/credential-leak-detection', type: 'Blog', main: 'credential leak detection',
    notes: 'Article Plan 2.32: Leaked Credentials and Security Watch' },
  // Article Plan categories 3-6 (2026-11-04): the 30 articles in
  // docs/Kite Pulse - Article Production Plan (Categories 3-6).md. Blog posts,
  // except four in Guides & tools (4.2, 5.9, 5.11, 6.14). As above, their
  // keyword rows still target other URLs in the sheet.
  { url: '/blog/claude-approaching-weekly-limit', type: 'Blog', main: 'claude approaching weekly limit',
    notes: 'Article Plan 3.2: Moving the Migration to Monday: a Plan-Limit Save' },
  { url: '/blog/repeated-errors-in-ai-coding-sessions', type: 'Blog', main: 'repeated errors in ai coding sessions',
    notes: 'Article Plan 3.3: The Test the AI Retried Six Times' },
  { url: '/blog/knowledge-transfer-before-leaving', type: 'Blog', main: 'knowledge transfer before leaving employee',
    notes: 'Article Plan 3.7: Before the Only Expert Moves Teams' },
  { url: '/blog/claude-code-reading-secrets', type: 'Blog', main: 'claude code reading secrets',
    notes: 'Article Plan 3.10: A Live Key in an AI Conversation' },
  { url: '/blog/weekly-engineering-report', type: 'Blog', main: 'weekly engineering report',
    notes: 'Article Plan 3.11: The Friday Spreadsheet Nobody Builds Any More' },
  { url: '/blog/two-developers-same-branch', type: 'Blog', main: 'two developers working on same branch',
    notes: 'Article Plan 3.12: Two People, One Service, One Stand-up' },
  { url: '/blog/turn-workflows-into-claude-code-skills', type: 'Blog', main: 'turn repeated workflows into claude code skills',
    notes: 'Article Plan 3.13: From a Repeated Workflow to a Team Skill' },
  { url: '/blog/claude-code-stuck-in-loop', type: 'Blog', main: 'claude code stuck in loop',
    notes: 'Article Plan 3.14: The Two-Hour Session That Went in Circles' },
  { url: '/blog/claude-code-for-engineering-managers', type: 'Blog', main: 'claude code for engineering managers',
    notes: 'Article Plan 3.15: A Manager Who Asks Her Own Assistant' },
  { url: '/blog/ai-code-attribution', type: 'Blog', main: 'ai code attribution',
    notes: 'Article Plan 4.1: Never Lose Credit for Work You Did with AI' },
  { url: '/how-to-use-claude-code-better', type: 'Interactive guide', main: 'how to use claude code better',
    notes: 'Article Plan 4.2: Get Better Privately: a Top 3 to Try, with the Evidence' },
  { url: '/blog/deep-work-sessions-developer', type: 'Blog', main: 'deep work sessions developer',
    notes: 'Article Plan 4.3: See Your Own Working Rhythm Clearly' },
  { url: '/blog/claude-code-agent-stuck', type: 'Blog', main: 'claude code agent stuck',
    notes: 'Article Plan 4.5: Catch a Stuck Agent in Half an Hour, Not at the End of the Day' },
  { url: '/blog/how-often-developers-correct-ai', type: 'Blog', main: 'how often developers correct ai',
    notes: 'Article Plan 4.7: Are You Checking What the AI Writes? A Private Verification Signal' },
  { url: '/blog/my-ai-coding-stats', type: 'Blog', main: 'my ai coding stats',
    notes: 'Article Plan 4.8: One Place for All Your AI Work, Whichever Tool You Used' },
  { url: '/blog/claude-code-daily-summary', type: 'Blog', main: 'claude code daily summary',
    notes: 'Article Plan 4.9: End the Day Knowing What You Left Open' },
  { url: '/blog/async-standup-tool', type: 'Blog', main: 'async standup tool',
    notes: 'Article Plan 4.10: No Timesheets, No Status Updates' },
  { url: '/blog/claude-code-version-check', type: 'Blog', main: 'claude code version check',
    notes: 'Article Plan 4.13: Stay on a Current Claude Code Without Watching Release Notes' },
  { url: '/blog/team-status-dashboard', type: 'Blog', main: 'team status dashboard',
    notes: 'Article Plan 5.1: Stand-ups That Start from Facts, Not Round-the-Room Updates' },
  { url: '/blog/claude-code-see-what-its-doing', type: 'Blog', main: 'claude code see what it\'s doing',
    notes: 'Article Plan 5.2: Help a Stuck Developer Without Reading Their Conversation' },
  { url: '/blog/recurring-engineering-blockers', type: 'Blog', main: 'recurring engineering blockers',
    notes: 'Article Plan 5.5: Fix the System, Not the Person' },
  { url: '/blog/duplication-of-work', type: 'Blog', main: 'duplication of work',
    notes: 'Article Plan 5.6: Stop Two People Building the Same Thing' },
  { url: '/blog/project-status-tracking-dashboard', type: 'Blog', main: 'project status tracking dashboard',
    notes: 'Article Plan 5.7: Know Which Projects Are Alive Without Chasing Anyone' },
  { url: '/blog/ai-session-success-rate', type: 'Blog', main: 'ai session success rate',
    notes: 'Article Plan 5.8: Is the Team\'s Work with AI Getting Better?' },
  { url: '/one-on-one-meeting-agenda', type: 'Interactive tool', main: 'one on one meeting agenda',
    notes: 'Article Plan 5.9: Better One-to-Ones from the Same Report the Developer Sees' },
  { url: '/bus-factor-calculator', type: 'Interactive tool', main: 'bus factor risk',
    notes: 'Article Plan 5.11: Spot the One-Person Parts of Your Product Before They Hurt' },
  { url: '/blog/engineering-metrics-dashboard', type: 'Blog', main: 'engineering metrics dashboard',
    notes: 'Article Plan 6.2: One Set of Figures Everyone Agrees On' },
  { url: '/blog/privacy-preserving-analytics', type: 'Blog', main: 'privacy preserving analytics',
    notes: 'Article Plan 6.6: A Measurement Culture That Describes Work Instead of Ranking People' },
  { url: '/blog/capture-knowledge-from-ai-coding-sessions', type: 'Blog', main: 'capture knowledge from ai coding sessions',
    notes: 'Article Plan 6.8: Keep What the Organisation Learns' },
  { url: '/ai-spending-limits', type: 'Interactive guide', main: 'corporate ai spending limits',
    notes: 'Article Plan 6.14: Adopt AI Analysis at a Pace You Control (absorbs 8.21, Intelligence Without an AI Service)' },
  // Article Plan categories 7-9 (2026-11-04): the 26 articles in
  // docs/Kite Pulse - Article Production Plan (Categories 7-9).md. Blog posts,
  // except 8.17 in the Glossary. As above, their keyword rows still target
  // other URLs in the sheet.
  { url: '/blog/engineering-visibility-tool', type: 'Blog', main: 'engineering visibility tool',
    notes: 'Article Plan 7.1: The Work Moved into AI Conversations, and Your Visibility Did Not Follow' },
  { url: '/blog/claude-code-hit-limit-mid-task', type: 'Blog', main: 'claude code hit limit mid task',
    notes: 'Article Plan 7.4: The Plan Limit That Ends Your Afternoon' },
  { url: '/blog/ai-agent-stuck-in-loop', type: 'Blog', main: 'ai agent stuck in loop',
    notes: 'Article Plan 7.6: The Agent That Sat Stuck While You Were in a Meeting' },
  { url: '/blog/build-failure-analyzer', type: 'Blog', main: 'build failure analyzer',
    notes: 'Article Plan 7.7: The Same Failure, Fought Separately by Three People' },
  { url: '/blog/project-status-tracking-tool', type: 'Blog', main: 'project status tracking tool',
    notes: 'Article Plan 7.10: Project Status by Guesswork' },
  { url: '/blog/ai-agent-oversight', type: 'Blog', main: 'ai agent oversight',
    notes: 'Article Plan 7.11: AI-Written Changes Nobody Checked' },
  { url: '/blog/status-meetings-waste-of-time', type: 'Blog', main: 'status meetings are a waste of time',
    notes: 'Article Plan 7.14: Status Meetings and Timesheets as the Only Source of Truth' },
  { url: '/blog/classify-developer-work', type: 'Blog', main: 'classify developer work',
    notes: 'Article Plan 8.9: AI Labelling, Done Carefully: Approved Label Lists, a Spending Cap and a Confidence Bar' },
  { url: '/blog/blocker-board-engineering', type: 'Blog', main: 'blocker board engineering',
    notes: 'Article Plan 8.11: From Facts to Advice: Fact Rules, Suggestion Rules and the Blocker Board' },
  { url: '/blog/ai-collaboration-metrics', type: 'Blog', main: 'ai collaboration metrics',
    notes: 'Article Plan 8.12: What Labels Tell a Team: Trends, Team Review and AI Collaboration' },
  { url: '/blog/verify-ai-generated-code', type: 'Blog', main: 'verify ai generated code',
    notes: 'Article Plan 8.13: What Labels Tell One Person: My Day, the Verification Signal and Profile Facts' },
  { url: '/blog/lessons-learned-software-development', type: 'Blog', main: 'lessons learned software development',
    notes: 'Article Plan 8.14: Knowledge Records: Lessons Quoted from Real Sessions, Linked to Where They Came From' },
  { url: '/blog/engineering-knowledge-management', type: 'Blog', main: 'engineering knowledge management',
    notes: 'Article Plan 8.15: Keeping Knowledge Current: the Weekly Knowledge Log and Coherence Checks' },
  { url: '/blog/capability-mapping-software', type: 'Blog', main: 'capability mapping software',
    notes: 'Article Plan 8.16: The Capability Map: Describing Each Product in Plain Terms' },
  { url: '/glossary/bus-factor', type: 'Glossary', main: 'bus factor in software development',
    notes: 'Article Plan 8.17: Who Really Knows This Part? Capability Ownership and the Bus Factor' },
  { url: '/blog/offboarding-knowledge-transfer', type: 'Blog', main: 'offboarding knowledge transfer',
    notes: 'Article Plan 8.18: When Someone Moves On: Tenure, the Departure Report and Knowledge-Capture Requests' },
  { url: '/blog/llm-cost-control', type: 'Blog', main: 'llm cost control',
    notes: 'Article Plan 8.22: Keeping Kite Pulse\'s Own AI Spend in Check' },
  { url: '/blog/claude-code-waiting-for-input', type: 'Blog', main: 'claude code waiting for input',
    notes: 'Article Plan 9.3: One Marker per Desk: What "!", a Thought Cloud and "Update" Are Telling You' },
  { url: '/blog/live-view-of-ai-coding-agents', type: 'Blog', main: 'live view of ai coding agents',
    notes: 'Article Plan 9.4: Live Without Pressing Refresh: How The Office and Team Overview Stay Current' },
  { url: '/blog/ai-agents-office-visualization', type: 'Blog', main: 'ai agents office visualization',
    notes: 'Article Plan 9.5: The Office on the Wall: Full-Screen Mode for a TV or Meeting Room' },
  { url: '/blog/ai-agent-dashboard', type: 'Blog', main: 'ai agent dashboard',
    notes: 'Article Plan 9.6: 3D, Map, List, Headroom and Brain: One Office, Five Ways to Look' },
  { url: '/blog/monitor-claude-code-agents', type: 'Blog', main: 'monitor claude code agents',
    notes: 'Article Plan 9.7: Click a Desk: Current Task, Stuck Reasons and Today\'s Figures in the Side Panel' },
  { url: '/blog/ai-agent-activity-log', type: 'Blog', main: 'ai agent activity log',
    notes: 'Article Plan 9.10: The Activity Feed: the Last 24 Hours of the Office in One Stream' },
  { url: '/blog/ai-agent-task-board', type: 'Blog', main: 'ai agent task board',
    notes: 'Article Plan 9.11: The Tasks Board: Work in Progress, Stuck, Waiting, Paused, Failed and Done' },
  { url: '/blog/engineering-manager-dashboard', type: 'Blog', main: 'engineering manager dashboard',
    notes: 'Article Plan 9.12: The Office Tab and the Connected Strip: the Team\'s Figures at a Glance' },
  { url: '/blog/team-overview-dashboard', type: 'Blog', main: 'team overview dashboard',
    notes: 'Article Plan 9.13: Finding People Fast: the Team Picker, Filter Tiles and One-Click Team Suggestions' },
  // Article Plan categories 10-13 (2026-11-04): the 34 articles in
  // docs/Kite Pulse - Article Production Plan (Categories 10-13).md. Sections
  // per its table: Integrations 2, Solutions 7, Guides & tools 4, Help 8,
  // Blog 13. As above, their keyword rows still target other URLs in the sheet.
  { url: '/docs/agent-api', type: 'Docs', main: 'engineering metrics api for ai agents',
    notes: 'Article Plan 10.7: Agent API Keys: Letting Your Own AI Assistant Ask Kite Pulse' },
  { url: '/blog/engineering-manager-developer-productivity-ai', type: 'Blog', main: 'engineering manager developer productivity ai',
    notes: 'Article Plan 10.10: Questions Your AI Assistant Can Answer About Engineering' },
  { url: '/blog/redact-secrets-in-ai-chat-history', type: 'Blog', main: 'redact secrets in ai chat history',
    notes: 'Article Plan 10.11: Reading What the AI Said: the Session-Text Permission and Its Safeguards' },
  { url: '/docs/mcp-dry-run', type: 'Docs', main: 'mcp dry run',
    notes: 'Article Plan 10.12: Before and After Handing Out a Key: Try a Question and Agent Activity' },
  { url: '/integrations/connectors', type: 'Integration', main: 'jira issues linked to ai coding sessions',
    notes: 'Article Plan 10.13: Connectors: Linking Jira, HubSpot, Slack, GitHub, Confluence, Google Drive and Notion to Projects' },
  { url: '/integrations/entra-id-okta', type: 'Integration', main: 'scim entra id provisioning',
    notes: 'Article Plan 10.14: User Sync with Microsoft Entra ID and Okta' },
  { url: '/blog/daily-digest-email', type: 'Blog', main: 'daily digest email',
    notes: 'Article Plan 10.16: Email from Kite Pulse: Notices, Alert Emails, Daily Digests and Scheduled Reports' },
  { url: '/blog/developer-analytics-security', type: 'Blog', main: 'developer analytics security',
    notes: 'Article Plan 10.17: What Leaves Your Server, Integration by Integration' },
  { url: '/how-to-run-a-daily-standup', type: 'Interactive guide', main: 'how to run a daily standup meeting',
    notes: 'Article Plan 11.1: Running the Monday Stand-up from The Office and Team Overview' },
  { url: '/blog/ai-coding-tools-budget-management', type: 'Blog', main: 'ai coding tools budget management',
    notes: 'Article Plan 11.3: The Monthly AI Spend and Budget Review' },
  { url: '/blog/ai-agent-stuck', type: 'Blog', main: 'ai agent stuck',
    notes: 'Article Plan 11.4: From "AI Agent Stuck" Notice to Fix' },
  { url: '/blog/lessons-learned-software-development-project', type: 'Blog', main: 'lessons learned in software development project',
    notes: 'Article Plan 11.6: A Release Retrospective Built on Session Evidence' },
  { url: '/developer-handover-checklist', type: 'Interactive tool', main: 'developer handover checklist',
    notes: 'Article Plan 11.8: Planning a Hand-over Before Someone Moves On' },
  { url: '/blog/engineering-resource-allocation', type: 'Blog', main: 'engineering resource allocation',
    notes: 'Article Plan 11.9: The Monthly Project Portfolio Review' },
  { url: '/blog/monthly-engineering-report', type: 'Blog', main: 'monthly engineering report',
    notes: 'Article Plan 11.10: Leadership Reporting on Autopilot' },
  { url: '/blog/compare-ai-coding-assistants-usage', type: 'Blog', main: 'compare ai coding assistants usage',
    notes: 'Article Plan 11.12: Choosing Which AI Tools and Models to Standardise On' },
  { url: '/blog/ai-coding-standards', type: 'Blog', main: 'ai coding standards',
    notes: 'Article Plan 11.13: Turning Repeated Work into Team Standards' },
  { url: '/blog/personal-weekly-review', type: 'Blog', main: 'personal weekly review',
    notes: 'Article Plan 11.14: A Developer\'s Own Weekly Review' },
  { url: '/blog/leaked-credentials-in-ai-chats', type: 'Blog', main: 'leaked credentials in ai chats',
    notes: 'Article Plan 11.15: Weekly Security Triage of AI Conversations' },
  { url: '/solutions/regulated-industries', type: 'Solution', main: 'on premise analytics tools',
    notes: 'Article Plan 12.2: Self-Hosted AI Development Insight for Finance and Healthcare Teams' },
  { url: '/solutions/enterprise', type: 'Solution', main: 'scaling ai adoption in engineering',
    notes: 'Article Plan 12.3: Running Kite Pulse Across an Enterprise with Many Teams' },
  { url: '/solutions/remote-teams', type: 'Solution', main: 'team availability dashboard',
    notes: 'Article Plan 12.5: Distributed and Outsourced Teams Across Time Zones' },
  { url: '/solutions/public-sector', type: 'Solution', main: 'on-premise developer productivity tool',
    notes: 'Article Plan 12.6: Public Sector and Government IT Teams' },
  { url: '/solutions/education', type: 'Solution', main: 'ai pair programming metrics',
    notes: 'Article Plan 12.7: Coding Bootcamps and Engineering Education' },
  { url: '/solutions/game-studios', type: 'Solution', main: 'capability mapping tools',
    notes: 'Article Plan 12.8: Game and Product Studios' },
  { url: '/solutions/platform-teams', type: 'Solution', main: 'developer friction',
    notes: 'Article Plan 12.9: Platform and Developer-Experience Teams' },
  { url: '/how-to-track-claude-code-usage', type: 'Interactive guide', main: 'how to track claude code usage',
    notes: 'Article Plan 13.1: Install Kite Pulse on Your Own Computer in One Command' },
  { url: '/docs/install-on-ubuntu', type: 'Docs', main: 'self-hosted developer analytics ubuntu',
    notes: 'Article Plan 13.3: Set Up a Team Server on Ubuntu or in Your Own AWS Account' },
  { url: '/docs/ai-budget-alerts', type: 'Docs', main: 'ai coding budget alerts',
    notes: 'Article Plan 13.8: Set Up Monthly AI Budgets, Seat Prices and Hourly Rates' },
  { url: '/docs/roles-and-permissions', type: 'Docs', main: 'roles and permissions dashboard',
    notes: 'Article Plan 13.9: Configure Roles, Permissions and Delegated Account Management' },
  { url: '/docs/slack-notifications', type: 'Docs', main: 'claude code slack notifications',
    notes: 'Article Plan 13.12: Configure Notifications and Alerts' },
  { url: '/docs/claude-plan-refresh', type: 'Docs', main: 'claude code limit monitor',
    notes: 'Article Plan 13.13: Get Fresher Claude Plan Figures with the Background Refresh' },
  { url: '/how-to-connect-claude-code-to-mcp', type: 'Interactive guide', main: 'how to connect claude code to mcp server',
    notes: 'Article Plan 13.16: Connect Your AI Assistant to Kite Pulse over MCP' },
  { url: '/docs/scheduled-email-reports', type: 'Docs', main: 'scheduled email reports',
    notes: 'Article Plan 13.18: Schedule Reports for Leadership' },
]

// PAGES THE SHEET LISTS THAT THIS PHASE OF THE SITE LEAVES OUT (2026-11-02).
// The Product menu is eight pages. /reports is folded into /features and
// /plan-headroom, /parallel-ai-agents into /ai-agent-office, and
// /enterprise-brain is The Brain, a hidden feature (master prompt R3) that is
// not part of this phase. Left out of the site only: the admin's view of the
// sheet still lists them.
export const HIDDEN = new Set(['/reports', '/parallel-ai-agents', '/enterprise-brain'])

// A page goes in the FIRST section whose test it passes, so the order of
// matching is separate from the order of display: `/blog/ai-coding-roi` is an
// interactive guide and must be caught before the `/blog` prefix claims it.
const MATCH = [
  ['Home', (p) => p.url === '/'],
  ['Glossary', (p) => p.url.startsWith('/glossary')],
  ['Integrations', (p) => p.url.startsWith('/integrations')],
  ['Compare', (p) => p.url.startsWith('/compare')],
  ['Legal', (p) => p.url.startsWith('/legal')],
  ['Guides & tools', (p) => p.type === 'Interactive guide' || p.type === 'Interactive tool'],
  ['Blog', (p) => p.url.startsWith('/blog')],
  ['Trust', (p) => p.type === 'Trust'],
  // The sheet types /pricing and /about as "Solution"; they are product pages.
  ['Product', (p) => p.type === 'Feature' || p.url === '/pricing' || p.url === '/about'],
  ['Solutions', (p) => p.type === 'Solution'],
  ['Help', (p) => p.type === 'Docs' || p.type === 'FAQ'],
]
// A page no test claims is listed under "Other", never dropped.
export const sectionOf = (p) => (MATCH.find(([, test]) => test(p)) || ['Other'])[0]

// PROTOTYPE PAGES, keyed by the Page Map URL. Each is a whole HTML document
// made as a Claude artifact and copied into `prototypes/`. They live under
// src/ and load as raw text, NOT in public/, so they get no address of their
// own on this site: the same page served from the Model Information Board's
// domain would compete with the real Kite Pulse page in search. `artifact` is
// where the prototype is edited; re-copy the file after changing it there.
export const PROTOTYPES = {
  '/ai-cost-tracking': { file: 'ai-cost-tracking', artifact: 'https://claude.ai/artifact/MW9gPq11m5pA4ULoAoiBec' },
  '/shadow-ai': { file: 'shadow-ai', artifact: 'https://claude.ai/artifact/M7e53egfYeGfSRC38aa3vN' },
  '/ai-coding-assistant-pricing': { file: 'ai-coding-assistant-pricing', artifact: 'https://claude.ai/artifact/C3rD3Ub6uJm2y5noHeJ3PN' },
  '/claude-code-usage-limits': { file: 'claude-code-usage-limits', artifact: 'https://claude.ai/artifact/WMFgbp6JCZxZoitFnENhZu' },
  '/blog/measure-developer-productivity-ai': { file: 'measure-developer-productivity-ai', artifact: 'https://claude.ai/artifact/Vgu3LkaSxjcPmEESmxzfBk' },
  '/blog/developer-experience-metrics': { file: 'developer-experience-metrics', artifact: 'https://claude.ai/artifact/Ung7TRao4PaUmSpoLDbMZJ' },
  '/ai-coding-analytics': { file: 'ai-coding-analytics', artifact: 'https://claude.ai/artifact/BgJQA795gFVyAQLTpazzLK' },
  '/engineering-intelligence': { file: 'engineering-intelligence', artifact: 'https://claude.ai/artifact/TmPhBF3zMcrMyQhtKS2WJQ' },
  // Written in Claude Code, not as artifacts: no `artifact` to edit them in.
  ...Object.fromEntries([
    'ai-coding-analytics-platform', 'engineering-ai-spend-report', 'ai-adoption-tracking',
    'token-usage-per-developer', 'token-usage-forecast', 'sprint-planning-claude-plan-limits',
    'control-claude-code-spend-small-team', 'developer-analytics-without-source-code',
    'developer-analytics-without-keystroke-tracking', 'ai-secret-scanning', 'stuck-ai-agent',
    'visualize-ai-agents-working', 'codex-gemini-cli-team-usage', 'cline-aider-roo-code-analytics',
    'ai-cost-per-project-agencies',
    // Second batch (2026-11-02): 8 Commercial, 7 Informational.
    'track-token-usage-without-prompts', 'cursor-shared-account', 'claude-code-session-analysis',
    'local-ai-coding-analytics', 'company-ai-usage-report', 'claude-code-agent-features-usage',
    'claude-md-version-control', 'ai-coding-tracker-freelancers', 'what-are-tokens-in-ai',
    'ai-coding-cost-per-developer', 'avoid-hitting-claude-limit', 'developer-experience-without-surveys',
    'is-claude-code-stuck', 'can-my-employer-see-my-claude-code-chats', 'engineering-team-health-metrics',
  ].map((file) => [`/blog/${file}`, { file, artifact: null }])),
  // The Product menu's pages (2026-11-02), also written in Claude Code.
  ...Object.fromEntries([
    'features', 'privacy', 'self-hosted', 'plan-headroom', 'skill-candidates',
    'ai-budgets', 'ai-agent-office', 'security',
  ].map((file) => [`/${file}`, { file, artifact: null }])),
  // The Solutions menu's role pages (2026-11-02).
  ...Object.fromEntries([
    'engineering-managers', 'finance', 'developers',
  ].map((file) => [`/solutions/${file}`, { file, artifact: null }])),
}
// One lazy chunk per prototype, downloaded only when it is shown.
const PROTOTYPE_FILES = import.meta.glob('../site-preview/prototypes/*.html', { query: '?raw', import: 'default' })
export const loadPrototype = (file) => PROTOTYPE_FILES[`../site-preview/prototypes/${file}.html`]

/** An empty sheet cell. Shown as a dash, never as 0 (rule 6). */
export const v = (x) => (x == null || x === '' ? '—' : x)
export const isMissingMain = (p) => !p.main || /^tbd\b/i.test(p.main)

/** Every page with its keywords, section and prototype, computed once from the sheet. */
export function buildModel(data) {
  const byUrl = new Map()
  for (const k of data.keywords) {
    if (!k.url) continue
    if (!byUrl.has(k.url)) byUrl.set(k.url, [])
    byUrl.get(k.url).push(k)
  }
  const enrich = (p) => {
    const kws = byUrl.get(p.url) || []
    const role = (r) => kws.filter((k) => (k.role || '').toLowerCase() === r)
    return { ...p, section: sectionOf(p), kws, main_kws: role('main'), secondary: role('secondary'), faq: role('faq'),
      prototype: PROTOTYPES[p.url] || null }
  }
  const pages = data.pages.map(enrich)
  // A proposed page the sheet has since added is the sheet's, not proposed.
  const inSheet = new Set(pages.map((p) => p.url))
  const proposed = PROPOSED.filter((p) => !inSheet.has(p.url))
    .map((p) => enrich({ main: null, priority: null, status: null, ...p, proposed: true }))
  return {
    pages,
    proposed,
    // The whole site: what the preview renders and links. Every count of the
    // keyword sheet reads `pages`, never this.
    site: [...pages, ...proposed].filter((p) => !HIDDEN.has(p.url)),
    keywords: data.keywords, aeo: data.aeo, competitors: data.competitors, avoid: data.avoid,
  }
}

/** The sheet and its model. `err` when the JSON could not be loaded. */
export function useKitePulse() {
  const [state, setState] = useState({ data: null, err: null })
  useEffect(() => {
    let alive = true
    import('./data/sheet.json')
      .then((m) => alive && setState({ data: m.default, err: null }))
      .catch((e) => alive && setState({ data: null, err: e.message }))
    return () => { alive = false }
  }, [])
  const model = useMemo(() => (state.data ? buildModel(state.data) : null), [state.data])
  return { ...state, model }
}

/** A prototype's HTML, loaded on demand. */
export function usePrototype(file) {
  const [state, setState] = useState({ html: null, err: null })
  useEffect(() => {
    let alive = true
    setState({ html: null, err: null })
    const load = file && loadPrototype(file)
    if (!load) {
      if (file) setState({ html: null, err: `No file web/src/kitepulse/site-preview/prototypes/${file}.html` })
      return undefined
    }
    load().then((t) => alive && setState({ html: t, err: null }))
      .catch((e) => alive && setState({ html: null, err: e.message }))
    return () => { alive = false }
  }, [file])
  return state
}

// ARTICLE PLANS (2026-11-03): docs/*Article Production Plan*.md, one entry per
// planned article, keyed by its URL. Read from the documents themselves, so the
// plan is written in one place and the site shows whatever it says now.
const PLAN_FILES = import.meta.glob('../docs/*Article Production Plan*.md', { query: '?raw', import: 'default' })

/**
 * Entries of a plan document, by URL. Each entry is `### <n> · <title>`, then
 * `- **Field:** value` lines; an indented `- item` or `1. item` belongs to the
 * field above it. An entry with no URL field is skipped, not guessed at.
 */
export function parsePlans(text) {
  const byUrl = new Map()
  for (const block of text.split(/^### /m).slice(1)) {
    const [head, ...lines] = block.split(/\r?\n/)
    const [article, ...rest] = head.split(' · ')
    const fields = []
    for (const line of lines) {
      const field = line.match(/^- \*\*(.+?):\*\* ?(.*)$/)
      const item = line.match(/^\s+(?:-|\d+\.) (.*)$/)
      if (field) fields.push({ label: field[1], value: field[2], items: [] })
      else if (item && fields.length) fields[fields.length - 1].items.push(item[1])
    }
    const url = fields.find((f) => f.label === 'URL')?.value.trim()
    if (url) byUrl.set(url, { article: article.trim(), title: rest.join(' · ').trim(), fields })
  }
  return byUrl
}

/** `plan` is the entry for one URL, null when no plan document lists it; `err` when they could not be read. */
export function useArticlePlan(url) {
  const [state, setState] = useState({ plan: null, err: null })
  useEffect(() => {
    let alive = true
    setState({ plan: null, err: null })
    Promise.all(Object.values(PLAN_FILES).map((load) => load()))
      .then((texts) => {
        if (!alive) return
        const found = texts.map(parsePlans).find((m) => m.has(url))
        setState({ plan: found ? found.get(url) : null, err: null })
      })
      .catch((e) => alive && setState({ plan: null, err: e.message }))
    return () => { alive = false }
  }, [url])
  return state
}

/** Address of a Kite Pulse page inside this app's preview. */
export const sitePath = (url) => (url === '/' ? '/kite-pulse' : `/kite-pulse${url}`)
