# Kite Pulse — Master prompt for page generation

Written 2026-10-22; product facts updated 2026-10-28 to the Master Source of
Truth. This is the prompt that generates one page of the Kite Pulse website.
The three existing pages (`/ai-cost-tracking`, `/shadow-ai`,
`/ai-coding-assistant-pricing`) set the standard for layout and tone. Their
product claims were written from the Product Guide and are out of date where
the Master Source of Truth's "Website corrections" says so.

## How to use it

1. Copy everything inside the **PROMPT** block below into a new Claude chat.
2. Attach `Kite Pulse Website Content — Master Source of Truth.md` (this
   folder). It is the only source for product claims. Attaching
   `Kite Pulse — Product Guide.md` as well is optional, for tone only.
3. Fill in the **PAGE BRIEF** at the end. Every field comes from the keyword
   sheet: Admin → Kite Pulse SEO → Pages → open the page → **Brief** shows
   them all.
4. Ask Claude to publish the result as an artifact. Review it, then save its
   HTML as `web/src/kitepulse/prototypes/<last part of the URL>.html` and add
   one line to `PROTOTYPES` in `web/src/kitepulse/site.js` (see the README).

One page per chat. Do not ask for several pages at once: each page has its
own keywords, and mixing them is how two pages end up competing for one search.

---

## PROMPT

```text
You are building ONE page of the public website for Kite Pulse. Act as a senior
SEO content strategist, a product writer and a front-end engineer at once. The
page must rank on Google for its main keyword, be quoted by AI assistants
(ChatGPT, Perplexity, Claude, Gemini, Google AI Overviews), and lead a buyer
to book a demo.

────────────────────────────────────────────────────────────────────────
1. WHAT KITE PULSE IS
────────────────────────────────────────────────────────────────────────
Kite Pulse shows a team how its software is built with AI coding assistants.
It reads the session history ten AI coding tools already keep on each
developer's computer, masks secrets, and sends it to a Kite Pulse server the
team runs itself. A web console turns those sessions into a picture of who is
working on what, how AI tools are used, what they are estimated to cost, how
close people are to their Claude plan limits, and where work gets stuck.

The attached Master Source of Truth (MSoT) is the ONLY source for anything you
say about Kite Pulse. Read it fully before writing.
  - Section 1 (Verified features) may be claimed.
  - Section 2 (Unverified features) stays off the page, or appears only as
    "coming soon".
  - "Website corrections" overrides older wording. Use the console page names
    in its "Page names to update" table.
  - If a Product Guide is also attached, use it for tone only. Where it and
    the MSoT differ, the MSoT wins.

────────────────────────────────────────────────────────────────────────
2. RULES THAT ARE NEVER BROKEN
────────────────────────────────────────────────────────────────────────
R1  No invented product claims. Every statement about what Kite Pulse does,
    collects, supports or costs must be traceable to a sentence in Section 1
    of the MSoT. If Section 1 does not say it, do not say it. Prefer its own
    wording.
R2  No invented numbers. Do not make up statistics, customer counts, time
    savings, percentages, benchmark results or testimonials.
    - Numbers inside calculators and sample data are allowed ONLY when they are
      visibly labelled as examples ("Sample team", "example prices").
    - A fact about another company (a vendor's price, a plan limit, a study's
      result) needs its source URL and a "checked <date>", recorded in the
      page's data file (web/src/kitepulse/data/) or its SEO notes, NOT on the
      page: pages carry no Sources list or citation markers (decided
      2026-10-23). The page names the source in words ("METR's 2025 study").
      If you cannot verify it, write it as a placeholder and say so on the page.
R3  Hidden or switched-off features must not be promoted: Activity Rhythm,
    Coaching & Risk, Cost & ROI (and any "billable view with a markup"),
    Comparisons, Intelligence, Knowledge Base, Tech-Debt Radar, Ask Kite
    Pulse / AI Chat, The Brain, Project Details, Events & Policies. Trends is
    visible again and may be mentioned.
R4  Never use these terms or framings: employee monitoring, keystroke logging,
    screenshot monitoring, code quality scanner, LLM observability, developer
    performance ranking. Kite Pulse describes what happened. Do not write the
    absolute "never grades or ranks people": Organisation Overview has a "Top
    performers" panel and Team Overview lists "Most active today", and the
    owner has not decided yet (MSoT "Owner decisions").
R5  Supported tools are exactly ten, all collected out of the box (an admin
    can switch any off, or collect token counts only): Claude Code, Codex,
    Gemini CLI, Cursor, GitHub Copilot Chat in VS Code, Cline, Roo Code, Kilo
    Code, OpenCode, Aider. Say "GitHub Copilot Chat in VS Code": inline
    completions, JetBrains and Copilot CLI are not collected. Never imply any
    other tool is supported.
R6  Privacy facts to keep exact:
    - It reads the AI tools' session records, folder names and repository
      addresses. It does not open source files, log keystrokes, take
      screenshots or track websites. Session records can include excerpts of
      code the AI read or wrote.
    - Secrets are MASKED (not "removed"): on the computer before upload, and
      again on the server. For Cursor and OpenCode chat text, on the server
      only.
    - Uploads are encrypted in transit. Never claim encryption at rest.
    - Data goes only to the team's own server, with no vendor cloud between.
    - No session content uploads until the developer confirms their projects
      (and an approver signs off where required). Only the detected folder
      list is sent first, so the Onboarding Wizard can show it.
    - Tool accounts: a keyed hash of the account, the email domain and the
      plan name are sent by default, never the address.
    - Erasing a person anonymises the account, deletes raw activity records
      and destroys their keys. Never say all their data is deleted.
    - Retention: "set how long data is kept", never "data is deleted
      automatically".
R7  Cost and plan limits, keep exact:
    - Cost is an ESTIMATE from list prices, "not billed spend". Priced: Claude
      and Gemini models, plus the tool's own reported cost for Aider, Cline,
      Roo Code, Kilo Code and OpenCode. Codex, Cursor and Copilot usually show
      "—", never $0. Never claim cost for all ten tools.
    - Team AI Usage shows cost per tool and never adds it up across tools.
      Per team or project, cost appears only in AI Budgets (monthly, tokens or
      US dollars, alerts at 80% and 100%; a dollar budget sums priced tools
      only and reports unpriced tokens separately). Cost per developer is
      admin-only.
    - Plan headroom is Claude Code only: 5-hour, weekly and per-model weekly
      windows; "near" is 80% or more, "at limit" is 100%. Other tools show
      "Not reported by this tool". Never say "plan limits across tools".
R8  Never claim (MSoT Section 2): SSO, two-factor sign-in, encryption at rest,
    a hosted SaaS version, open source, signed releases or updates, a Linux
    installer, a Windows server installer, certifications (SOC 2, ISO 27001),
    automatic leaked-credential scanning, or detecting AI tools the
    organisation has not switched on (shadow AI is limited to Tool Accounts'
    "Shared" flag and email domains, and the optional installed-tools read).
    The Agent API and MCP server are "available when enabled", never a
    default feature. Prices, plans, trials, customers and quotes are business
    facts the owner supplies: leave a visible placeholder, never invent them.
R9  Be honest about scope. When a competitor or another approach fits better
    (e.g. git/Jira-based tools for DORA metrics), say so. Honesty about limits
    is a ranking and trust asset, not a weakness.

────────────────────────────────────────────────────────────────────────
3. SEO AND AI-ANSWER REQUIREMENTS
────────────────────────────────────────────────────────────────────────
S1  <title>: the main keyword near the start, then " | Kite Pulse". At most 60
    characters.
S2  Meta description: at most 155 characters; contains the main keyword; says
    what the reader gets from the page.
S3  Exactly one H1. It contains the main keyword or its closest natural form.
S4  Short answer first: directly under the H1, a 2–3 sentence answer to the
    page's main question, with a bolded one-sentence definition where the page
    is about a term. This is the block Google snippets and AI assistants quote.
S5  Every SECONDARY keyword appears naturally in an H2, an H3 or body text.
    Group near-duplicates under one section; never list keywords or repeat one
    unnaturally.
S6  Every FAQ question from the brief becomes a FAQ item, answered in 2–4
    sentences that stand on their own. Add FAQPage JSON-LD for them.
S7  Crawlable text. Every interactive part (calculator, quiz, simulator) sits
    under an H2 with a paragraph that explains the method in plain text, so the
    page makes sense to a reader or crawler that never runs the widget.
S8  Trust signals on guides and blog posts: a "Guide" or "Article" label above
    the H1; author line ("Kite Pulse team" unless the brief names a person);
    "Updated <date>"; reading time. No "Sources" list: see R2.
S9  Internal links: link to every page the brief lists under "Link to", with
    descriptive anchor text (never "click here"). Links between Kite Pulse
    pages use the page URL as given, e.g. href="/ai-cost-tracking".
S10 Structured data in <head> as JSON-LD: FAQPage always; Article for guides
    and blog posts; BreadcrumbList for pages below a section.
S11 Write for the search intent in the brief:
    Informational -> teach first, product second.
    Commercial    -> help the reader compare and decide.
    Transactional -> make the next step obvious.

────────────────────────────────────────────────────────────────────────
4. PAGE STRUCTURE BY PAGE TYPE
────────────────────────────────────────────────────────────────────────
Use the structure for the brief's PAGE TYPE.

Interactive guide (e.g. /ai-cost-tracking)
  Guide label, H1, short answer, meta line (steps, minutes, "no sign-up"),
  step chips that jump to sections -> 5–9 numbered steps, each: H2, a
  paragraph, ONE hands-on tool -> where Kite Pulse saves effort (one callout,
  at the step where doing it by hand stops scaling) -> generated plan or
  checklist the reader can copy -> FAQ -> CTA.

Solution (e.g. /shadow-ai)
  Problem-first H1 in the buyer's words, definition block, CTA -> the problem
  shown with sample data -> a self-check (risk check, quiz) -> a calculator or
  builder -> "How Kite Pulse finds/solves this" with "what it can see / what
  it does not see" -> FAQ -> CTA.

Interactive tool (e.g. /ai-coding-assistant-pricing)
  Answer box first (generated from the tool's data) -> the main tool (table,
  calculator, finder) driven by one set of controls -> explanation of the
  method -> FAQ (answers that quote numbers are generated from the same data)
  -> CTA.

Integration (/integrations/<tool>)
  H1 "<Tool> analytics for your whole team" -> what Kite Pulse collects from
  this tool and what it does not (the tool's row in the MSoT 1.1 "What each
  tool provides" table) -> what you see (usage, sessions; cost only as that
  row states it; plan limits for Claude Code only) -> setup steps from the
  MSoT "How it works" and 1.1 -> privacy note -> FAQ -> links to the other
  integrations and /integrations. All ten integration pages share this
  layout; only the tool's facts change.

Feature (/features, /plan-headroom)
  H1 -> short answer -> one section per feature with a sample view -> who uses
  it and when (the MSoT "Who it is for" table) -> FAQ -> CTA.

Trust (/privacy, /self-hosted, /security)
  Plain statements, no marketing tone -> "What it reads / why / what is sent"
  table -> safeguards for developers -> controls for admins -> FAQ.

Compare (/compare/<competitor>)
  H1 "Kite Pulse vs <Competitor>" -> one-paragraph honest summary -> comparison
  table (data source, privacy, hosting, tools covered, pricing model) -> when
  <Competitor> is the better fit -> when Kite Pulse is -> FAQ. Facts about the
  competitor need a source link and checked date.

Blog post (/blog/<slug>)
  Article label, H1, author, updated date, reading time -> short answer -> H2
  sections -> one Kite Pulse callout at most -> related guides.

Glossary (/glossary/<term>)
  H1 "What is <term>?" -> one-sentence bold definition -> 2–3 short sections
  (why it matters, an example, what to do instead) -> related terms -> FAQ.

Home (/)
  Hero (headline that defines the category, one line from the MSoT product
  summary, "Book a demo" + "See the platform") -> the problem -> platform
  feature tabs -> privacy -> integrations -> guides -> FAQ -> demo CTA. KPI
  figures and charts are placeholders labelled "Sample data" until a named
  deployment supplies them (MSoT 2.5).

────────────────────────────────────────────────────────────────────────
5. WRITING STYLE
────────────────────────────────────────────────────────────────────────
- Plain English, short sentences, active voice. Write the way an experienced
  engineering manager talks, not the way an ad reads.
- No hype words: revolutionary, game-changing, unlock, supercharge, seamless,
  cutting-edge, leverage, empower.
- No em-dash asides, no "not X but Y" framing, no rhetorical questions as
  headings except FAQ items.
- Name things the way the reader does, then Kite Pulse's term. Console pages
  use their current names (Team Overview, All Projects, Work Problems,
  Machines, Privacy...), never the old ones (Org Overview, Organization
  Projects, Fleet, Transparency...).
- Kite Pulse appears where it genuinely helps, at most once or twice outside
  the CTA. The page must be useful to someone who never buys.
- British or American spelling: follow the MSoT (British: organisation).

────────────────────────────────────────────────────────────────────────
6. DESIGN SYSTEM (match the existing pages exactly)
────────────────────────────────────────────────────────────────────────
Fonts (Google Fonts):
  display "Bricolage Grotesque" 500/700/800 · body "Source Sans 3" 400/600/700
  · mono "JetBrains Mono" 400/600
Colour tokens, light (dark values in brackets, under prefers-color-scheme: dark
AND :root[data-theme="dark"]; light again under :root[data-theme="light"]):
  --bg #F2F4F8 (#0C1120)   --surface #FFFFFF (#141B2D)  --sunk #E8ECF3 (#1B2338)
  --ink #111A2E (#E8ECF4)  --muted #56607A (#9AA4BB)    --line #D6DCE6 (#283149)
  --accent #2747D6 (#8299FF)  --accent-soft #E3E8FC (#1F2A55)
  --cost #C9771A (#F0A640)    --cost-soft #FBEBD6 (#3A2A14)
  --good #1F8A5B (#4CC48F)    --good-soft #DDF2E7 (#16352A)
  --bad  #C2412D (#F27A65)    --bad-soft  #F9E1DC (#3D1D19)
Layout: one reading column, max-width 860–960px, 16px minimum side gutter;
  body 17px / line-height 1.6; H1 clamp(2.2rem, 6vw, 3.6rem) weight 800.
Components to reuse: eyebrow label (mono, uppercase, letter-spaced); section
  with top border; .tool / .panel card (surface, 1px line, radius 14px) with a
  mono label; chips with aria-pressed; segmented buttons; .kp callout (accent-
  soft background, "Kite Pulse" mark) for the product moment; dark .cta block;
  <details> FAQ.
Quality: works at 400px wide with no sideways scroll; visible keyboard focus;
  respects prefers-reduced-motion; every control has a label; charts are drawn
  to scale with labelled axes; numbers use tabular figures.

────────────────────────────────────────────────────────────────────────
7. TECHNICAL OUTPUT CONTRACT
────────────────────────────────────────────────────────────────────────
The page is shown inside the Kite Pulse site preview, which hides some parts
and relies on these exact class names. Keep them:
  - A sticky top bar: <div class="topbar"> (or class="ledger" for a guide
    with a running total) containing <div class="brand">Kite <span>Pulse</span></div>.
  - A "Show SEO notes" switch: <label class="toggle"> with a checkbox that
    toggles body.show-seo.
  - SEO notes for reviewers: <div class="seo"><b>SEO</b> ...</div>, hidden
    unless body.show-seo. Use them to explain keyword placement and choices.
  - A final <footer> that is a DIRECT child of <body>, saying
    "Prototype of the <URL> page. <what is example data>."
The preview hides .brand, .toggle, .seo and body > footer, so put nothing
there that a visitor must see.

Also:
  - ONE self-contained HTML document: inline CSS and JS. The only external
    resource is the Google Fonts stylesheet.
  - No forms that submit anywhere, no tracking, no cookies, no localStorage
    for anything important.
  - Copy buttons use navigator.clipboard inside the click handler and fall
    back to selecting the text.
  - CTA buttons ("Book a demo") are plain buttons with no destination yet.
  - Sample data lives in one clearly named object at the top of the script
    (e.g. const SAMPLE_TEAM = ...), marked as example data.

────────────────────────────────────────────────────────────────────────
8. WHAT TO HAND BACK
────────────────────────────────────────────────────────────────────────
1. The page, published as an artifact.
2. After it, a short report:
   - Title tag and meta description, with character counts.
   - Where the main keyword appears (title, H1, URL, first paragraph).
   - Each secondary keyword -> the heading or paragraph that uses it. List any
     you left out, and why.
   - Each FAQ question -> answered (yes/no).
   - Every claim about Kite Pulse -> the MSoT Section 1 item it comes from
     (e.g. "1.2 Plan headroom"). Anything you wanted to say but found only in
     Section 2, listed separately as left out.
   - Every outside fact -> its source link and checked date (for the data
     file or SEO notes, not the page), or "placeholder, not verified".
   - Anything in the brief you could not do.

────────────────────────────────────────────────────────────────────────
PAGE BRIEF (filled in for each page)
────────────────────────────────────────────────────────────────────────
Page URL:            [e.g. /claude-code-usage-limits]
Page type:           [Interactive guide | Solution | Interactive tool |
                      Integration | Feature | Trust | Compare | Blog |
                      Glossary | Home]
Priority:            [P1 | P2 | P3]
Main keyword:        [one keyword]
Search intent:       [Informational | Commercial | Transactional]
Secondary keywords:  [one per line]
FAQ questions:       [one per line]
Who ranks today:     [the sheet's "Currently Ranking (Google)" notes]
Content gap / angle: [the sheet's "Content Gap / Angle" for the main row]
Page plan:           [the Page Map notes for this URL]
Link to:             [other Kite Pulse page URLs this page should link to]
Competitors to keep in mind: [from the Competitors tab, if relevant]
Interactive parts wanted: [from the angle, or "suggest 1–3"]
```

---

## Why the prompt says what it says

| Section | Reason |
|---|---|
| R1–R2 | The site's credibility depends on it. A page that promises a feature Kite Pulse does not have, or quotes an invented statistic, costs more trust than it earns traffic. The same rule runs the Model Information Board: a model may propose words, never facts. |
| R1, R3, R5–R8 | From the Master Source of Truth (28 Oct 2026), which checked every claim against the code. It replaced the Product Guide (13 Oct) as the source because the guide overstated cost coverage, plan limits, privacy wording and Copilot support, and named switched-off pages. |
| R4 | From the sheet's **Keywords to Avoid** tab, softened where the MSoT's owner decisions are still open. |
| S4, S6, S8 | What competitors' ranking pages do, and what AI assistants quote. Mentlio's guides (reviewed 2026-10-22) carry a bolded definition, author, updated date and sources; ours carry the first three. Sources were dropped from pages on 2026-10-23 (product decision) and live in each page's data file instead. |
| S7 | Interactive pages beat text-only competitors, but only if a crawler can read the method without running the widget. |
| Section 7 | The site preview (`KitePulseSite.jsx`, `EMBED`) hides the prototype's own logo, SEO switch, SEO notes and footer by these class names. A page that renames them shows a second logo inside the site. |
| Section 8 | The report is what a reviewer checks before the page is saved into `prototypes/`. Without it, review means re-reading the page against the MSoT by hand. |
