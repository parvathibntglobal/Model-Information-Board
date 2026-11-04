# Kite Pulse SEO site — Architecture plan

Written 2026-10-22; updated 2026-10-28 when the Master Source of Truth (MSoT)
replaced the Product Guide as the source for product claims, and again the
same day with what the Product Guide is still used for (section 2.4). Covers
what is built today, the decisions behind it, and the plan from an internal
preview to a public site on Kite Pulse's own domain.

Counts in this document are records from the keyword sheet as imported on
2026-10-22: 49 pages in the Page Map, 588 keyword rows (361 SEO, 227 AEO),
16 AEO questions, 11 competitors. They change when the sheet does; the admin
panel shows the current figures.

---

## 1. Scope

Kite Pulse is a separate product with its own codebase (desktop collector,
server, console). **None of that code comes here.** This repository manages
only Kite Pulse's **marketing and SEO website**: the pages, the keywords each
page targets, and whether AI assistants mention Kite Pulse.

The Model Information Board (MIB) and Kite Pulse share this app's shell,
sign-in and admin. They share no data, no tables and no part of MIB's
evidence pipeline (`collect/` → `judge/`).

---

## 2. What is built (phase 1, done)

### 2.1 Where things live

```
web/src/kitepulse/                    everything Kite Pulse
├── KitePulseSite.jsx                 the site preview, at /kite-pulse
├── HomeCharts.jsx                    the home page's charts, tiles and team picker
├── site.css                          its look (the prototypes' design system)
├── KitePulsePanel.jsx                Admin → Kite Pulse SEO
├── admin.css                         that panel's styles (MIB tokens)
├── site.js                           shared: sections, menus, footer, proposed pages,
│                                     prototype registry, sheet loading
├── import_sheet.py                   xlsx → data/sheet.json
├── data/sheet.json                   generated; never edited by hand
├── data/home-dashboard.json          home page figures ("sample": true until real)
├── data/*.json                       checked outside facts (Claude plans, research,
│                                     frameworks), each with its source
├── screens/                          console screenshots for the home page
├── prototypes/*.html                 finished pages, one per URL
└── docs/                             keyword sheet, Master Source of Truth,
                                      Product Guide (structure, tone and
                                      vocabulary; no claims, see 2.4), this plan,
                                      the master prompt

Hooks outside the folder (the only three):
web/src/App.jsx                       the /kite-pulse/* route; hides MIB's nav there
web/src/routes/Admin.jsx              "Projects" group: Kite Pulse →, Kite Pulse SEO
web/nginx.conf.template               lets the deployed server answer /kite-pulse
```

The folder sits inside `web/src/` because `web/Dockerfile` builds from `web/`
alone. Code at the repository root would not reach the deployed frontend.

### 2.2 Data flow

```
 docs/Kite Pulse - Keyword Research.xlsx      (people edit this)
              │
              │  py -3.12 web/src/kitepulse/import_sheet.py
              ▼
 data/sheet.json  ── keywords, Page Map, AEO, competitors, avoid list,
              │      plus the sheet's sha256 and import date
              │
              │  site.js: useKitePulse()  (lazy chunk, ~230 KB built)
              ▼
 buildModel()  ── pages (the sheet's 49)
              │   proposed (pages the structure needs, not in the sheet yet)
              │   site = pages + proposed      ← what the preview renders
              │
     ┌────────┴──────────┐
     ▼                   ▼
 KitePulsePanel     KitePulseSite
 (admin: briefs,    (site: home, menus, sections,
  keywords, AEO)     pages, footer)
                         │
                         │  page has a prototype?
                         ▼
               prototypes/<slug>.html  ── loaded as raw text (one lazy chunk each)
                         │               EMBED hides its own logo / SEO notes /
                         ▼               footer, reports its height and in-page links
               <iframe srcdoc sandbox="allow-scripts allow-popups">
```

### 2.3 Decisions already made, and why

| Decision | Why |
|---|---|
| The sheet stays the source of truth; the app only reads it | The team already works in the sheet. A second editable copy would drift. |
| Empty cells stay empty (shown as "—", never 0) | Volume 0 means "nobody searches this"; an empty cell means "not researched". Different facts. |
| Proposed pages kept apart from the sheet's pages | So no count of the sheet's plan changes because the code suggested a page. |
| Prototypes under `src/`, loaded as text, not in `public/` | A file in `public/` gets a public URL on the MIB domain, where it would compete in search with the real Kite Pulse page. |
| Prototypes run in a sandbox without `allow-same-origin` | Their scripts run, but cannot read the app's session token or storage. |
| `/kite-pulse` behind sign-in and `noindex` | It is a preview. These pages must first be indexed on Kite Pulse's own domain. |
| Product claims come from Section 1 of the MSoT only | The MSoT (28 Oct 2026) checked every claim against the Kite Pulse code; the Product Guide (13 Oct) overstated cost coverage, plan limits, Copilot support and privacy wording. Section 2 stays off the site or says "coming soon". |
| Home page built in React, not as a prototype (2026-10-28) | Its copy follows the MSoT; its figures live in `data/home-dashboard.json` and every chart says "Sample data" until a named deployment supplies real ones (MSoT 2.5). Cost is shown per tool and never summed; the summed cost tile became "Tokens this week". |
| Site structure modelled on mentlio.com, a direct competitor | Reviewed 2026-10-22: a short menu with dropdowns, a home page that tells one story, content typed by URL (`/guides/`, `/glossary/`). The page addresses stay the sheet's. |

### 2.4 What the Product Guide is still used for

`docs/Kite Pulse — Product Guide.md` (13 Oct 2026, @Neenu) is the longest
description of the product, and the 8 designed pages were written from it.
The MSoT (28 Oct) checked it against the Kite Pulse code and lists the
corrections in its "Website corrections" section: 26 claims and 11 page names
as of 2026-10-28. The rule for using it:

> **Take the Product Guide's shape, order, audiences, questions and the words
> people search with. Take every product fact from MSoT Section 1.** Where a
> Product Guide sentence and the MSoT differ, the MSoT wins, and a Product
> Guide sentence the MSoT does not cover stays off the site.

What each part of the guide feeds:

| Product Guide section | Used for | Site pages | Facts must come from |
|---|---|---|---|
| What Kite Pulse is ("outputs vs process", the one-line description) | Home hero and story order | `/`, `/engineering-intelligence` | MSoT "Product summary" (the one-line description is the same in both) |
| Who it is for (5 audiences; access level vs work role) | Audience framing on solution pages; the "By role" menu if decision 14 adds pages | `/`, `/features`, solution pages | MSoT "Who it is for" (4 audiences). Access levels are Admin, Manager, **Developer**; "work role shapes insights" is removed |
| Problems it solves (7 problems) | Problem → answer sections; the brief for interactive guides | `/`, `/ai-cost-tracking`, `/plan-headroom`, `/blog/institutional-knowledge` | MSoT 1.2–1.5. Cost is per tool with budgets per team or project, never "per person, project and period" or "billable with a markup"; plan limits are Claude Code only |
| How it works at a glance (3 parts) | The "how it works" strip and animation | `/`, `/self-hosted`, `/privacy` | MSoT "How it works" and 1.8 |
| Key features (9 groups, each with an example) | The order and grouping of `/features`; the worked-example pattern | `/features`, integration pages | MSoT Section 1, with console page names from its "Page names to update" table (Workspace, Team Overview, All Projects, Work Problems, Machines, Privacy…) |
| How individuals and teams use it (setup steps, role × moment table, 3 worked examples) | "Getting started" content; role-based examples on solution pages | `/docs`, `/features`, `/self-hosted` | MSoT 1.1, 1.8. Agent API and MCP are "available when enabled" (decision 10) |
| Privacy and trust (reads table, optional reads, safeguards) | The structure of `/privacy` | `/privacy`, `/self-hosted`, `/security` (proposed) | MSoT 1.7 and its corrections: an anonymised account id, not the email; encrypted in transit, not at rest; erase is partial (decision 12); risk signals **do** name the person |
| What makes it valuable (8 points) | Home "why" section and page conclusions | `/`, `/features` | Each point re-checked against Section 1; "spending under control" needs the cost wording above |
| Glossary: Kite Pulse terms (25) | Seed list for `/glossary` (proposed) | `/glossary`, tooltips | MSoT. At least six definitions are wrong as written: access level, AI Call Log, confidence bar, Fleet (now Machines), work role (remove), working style (from what sessions did, plus "generalist") |
| Glossary: how people describe this kind of product (13 rows) | **Vocabulary, not claims**: cross-check against the keyword sheet; candidate keywords for the SEO owner; the "is / is not" framing on compare pages | `/glossary`, `/compare/*`, solution pages | The "How Kite Pulse relates" column needs the MSoT's corrections (e.g. Shadow AI covers the two partial signals only) |
| What Kite Pulse is not | "Is not" blocks on `/privacy` and compare pages | `/privacy`, `/compare/*` | MSoT "What it is not", which adds "does not open project source files; records can include excerpts" |
| FAQ (12 questions) | The question set for `/faq` and its FAQ JSON-LD, alongside the sheet's AEO questions | `/faq`, page FAQs | MSoT. Several answers change: "admin picks tools" (all ten on by default), "nothing uploads" (the folder list does), "not a ranking tool" (decision 9) |

Two things in the guide have no MSoT counterpart and need the product owner
before any page uses them:

- **"Historian, not critic."** A good line for the voice of the site, and it
  makes the same promise as "does not grade people", which decision 9 puts in
  doubt while "Top performers" and "Most active today" are in the console.
- **Pages the guide names that the MSoT lists as hidden or not reachable by
  default** (Ask Kite Pulse, Cost & ROI, Project Details/Events & Policies,
  Agent API, MCP). The guide's own "switched off" list is out of date too:
  Trends is visible again.

---

## 3. Constraints to respect

1. **Deploy builds `web/` only.** Anything the site needs must be inside `web/`.
2. **MIB's rule 2: the number of model-calling stages is fixed.** As recorded
   in `CLAUDE.md` on 2026-10-28: `judge/extract/`, `judge/ask/` and the blog
   generator (#508) are in force; the evidence feed (`judge/feed/`, #558) is
   proposed and not in force until it merges; the quiz drafter calls a model
   and is not yet recorded. An automated Kite Pulse page writer or AEO tracker
   would be one more caller. It needs the same agreement the blog generator
   got, under the same terms: it proposes drafts, a person approves, code
   checks facts, and its spend is recorded. Until then, pages are generated by
   hand with the master prompt.
3. **`contract/` gets two eyes.** Kite Pulse config does not go there unless
   it is reviewed like any contract change. Today it needs none.
4. **The MIB app has no server rendering.** A crawler gets an empty shell from
   `web/`. That is fine for the preview and unacceptable for the public site,
   which is why phase 3 builds static HTML.
5. **Official APIs only.** Ranking checks (who ranks for a keyword) must use a
   SERP data API, never scraping Google.

---

## 4. Target architecture

```
                         ┌──────────────────────────────────────┐
  people ──────────────► │ docs/  keyword sheet · MSoT          │
                         └───────────────┬──────────────────────┘
                                         │ import_sheet.py
                                         ▼
  MASTER-PROMPT.md ───► page drafts ──► prototypes/<slug>.html  (git: review + history)
  (Claude, by hand                         │
   today; a writer                         │
   agent later)                            ▼
                         ┌──────────────────────────────────────┐
                         │ SEO check (code, no model)           │
                         │ title/meta length · H1 keyword ·     │
                         │ FAQ JSON-LD · links · avoid list ·   │
                         │ claims vs MSoT Section 1             │
                         └───────────────┬──────────────────────┘
                                         │ pass
               ┌─────────────────────────┴─────────────────────────┐
               ▼                                                   ▼
  INTERNAL: MIB app /kite-pulse                     PUBLIC: Kite Pulse domain
  (preview, admin, briefs)                          static build: one HTML file per URL,
                                                    shared header/footer, sitemap.xml,
                                                    robots.txt, canonical, OG, JSON-LD
                                                    own nginx service (Railway)
                                                                   │
                                                                   ▼
                                                    MEASURE: Search Console ·
                                                    monthly AEO check · sheet Status
```

### 4.1 Page storage: files first

| Option | For | Against |
|---|---|---|
| **HTML files in git (today, recommended next)** | Review in a pull request, full history, no migration, the build reads them directly | Editing needs a developer or a re-copy from Claude |
| Database table (`kp_page`: url, html, status, version, approved_by) | Non-developers can edit in the admin; "History" tab is a query | A migration; content leaves code review; the public build must fetch it |

Move to the database only when people who do not use git need to edit pages.

### 4.2 The public site (phase 3)

**Recommended: a second build from the same `web/` folder**, not a new
framework.

- `web/vite.kitepulse.config.js` builds only the Kite Pulse site, with its own
  `index.html` and no MIB routes.
- A small build script writes **one static HTML file per page URL**: the shared
  header and footer (from `KitePulseSite.jsx`, pre-rendered the way
  `web/prerender.js` already pre-renders MIB pages) around the page body. The
  prototype pages are already complete HTML documents, so they need assembling,
  not rewriting.
- It writes `sitemap.xml` and `robots.txt`, and puts the canonical, Open Graph
  and JSON-LD tags in each file's initial HTML.
- A second nginx service, with its own `Dockerfile.kitepulse`, serves it on
  the Kite Pulse domain.
- The MIB preview at `/kite-pulse` keeps working for review.

The alternative, a separate Astro project, gives cleaner static output but a
second toolchain and a copy of every shared piece. Not worth it while the
pages are self-contained HTML.

### 4.3 Agents and where a model may act

Same principle as MIB: **a model may propose, never decide.**

| Agent | Model? | What it does | Status |
|---|---|---|---|
| Sheet importer | No | xlsx → JSON | Built |
| Page planner | No | Next pages to write, by priority and keyword count (the MIB blog planner's pattern) | To build |
| Brief builder | No | Keyword rows → the master prompt's PAGE BRIEF | Built as the admin Brief tab; export to text to build |
| Page writer | **Yes**: proposes HTML | Runs the master prompt | By hand today; automated only after a rule-2 agreement |
| SEO checker | No | The checks in 4 above; a page publishes only when it passes | To build |
| Fact checker | No | Every product sentence on the page must match a sentence in MSoT Section 1, and no page may use a Section 2 claim or an old page name from its "Website corrections"; every number must be in the MSoT or marked as an example. The "Current claim" column of the corrections table becomes a list of refused phrasings (e.g. "billable view with a markup", "Org Overview", "plan limits across tools"), which catches Product Guide wording copied into a page (2.4) | To build (MIB's blog CHECK step is the model) |
| AEO tracker | **Yes**: asks assistants | Asks the 16 AEO questions monthly; **code** decides whether "Kite Pulse" is mentioned | To build; same rule-2 agreement |
| Rank checker | No | Who ranks for each main keyword, via a SERP API | Optional |

---

## 5. Phases

| Phase | Outcome | Main work | Depends on |
|---|---|---|---|
| **1. Preview** ✅ | Kite Pulse inside the MIB app: site preview, admin panel, 3 pages | Done 2026-10-22 | — |
| **2. Content** | All P1 pages written, checked, in `prototypes/` | Home page rebuilt from the MSoT (done 2026-10-28); correct the 8 designed pages against the MSoT's "Website corrections"; `/features` and `/privacy` follow the Product Guide's structure with MSoT facts (2.4); `/faq` starts from the guide's 12 questions plus the sheet's AEO questions; master prompt per new page; SEO checker; admin "SEO check" and "Content" tabs; add the 4 proposed pages to the sheet | Booking link; owner for the sheet; MSoT owner decisions (section 6) |
| **3. Public site** | Kite Pulse domain live with static, indexable pages | Second Vite build; static assembler; sitemap/robots/canonical/JSON-LD; nginx service; DNS | Domain; decision on page storage (4.1) |
| **4. Measure** | Monthly view of rankings and AI mentions | Search Console; AEO tracker; write Status/Publish date back to the sheet | Rule-2 agreement for the AEO tracker |
| **5. Scale** | P2 and P3 pages; glossary; compare pages | Page planner; optional writer agent | Phase 2 checks in place |

### P1 pages for phase 2 (14 in the sheet, as of 2026-10-22)

`/` · `/features` · `/pricing` · `/privacy` · `/self-hosted` · `/integrations`
· `/integrations/claude-code` · `/integrations/codex` ·
`/integrations/gemini-cli` · `/integrations/cursor` ·
`/integrations/github-copilot` · `/faq` · `/legal/privacy-policy` ·
`/legal/terms`

The five P1 integration pages share one layout: build one (Claude Code), then
the other four. Each takes its facts from that tool's row in the MSoT 1.1
table; `/integrations/github-copilot` covers Copilot Chat in VS Code only.
`/pricing` and the two legal pages need business facts and legal text the
code cannot supply (MSoT 2.5).

---

## 6. Decisions needed

| # | Decision | Who | Blocks |
|---|---|---|---|
| 1 | The Kite Pulse domain | Product owner | Phase 3 |
| 2 | Demo booking link | Product owner | "Book a demo" on every page |
| 3 | Add `/security`, `/glossary`, `/glossary/tokenmaxxing`, `/changelog` to the Page Map? | SEO owner | Phase 2 scope |
| 4 | Move keyword rows 581–582 (tokenmaxxing) to `/glossary/tokenmaxxing`? | SEO owner | Glossary |
| 5 | Main keyword for `/ai-coding-analytics` (sheet says "TBD") | SEO owner | That page |
| 6 | Verify every price on `/ai-coding-assistant-pricing` | One named owner | Removing its placeholder warning |
| 7 | Automated writer / AEO tracker: agree a rule-2 exception like the blog generator's | Both MIB engineers | Phases 4–5 automation |
| 8 | Add Mentlio to the Competitors tab | SEO owner | Compare planning |
| 9 | "Not a ranking tool": soften the site's wording, or change the "Top performers" and "Most active today" panels (MSoT owner decisions) | Product owner | Home, /features, /privacy wording |
| 10 | Agent API and MCP on by default in installs? Until then they are "available when enabled" | Product owner | /docs, /features, FAQ |
| 11 | Offer the Linux desktop program (from source, no installer) or leave it off | Product owner | /self-hosted, /integrations |
| 12 | Should erasing a person also delete plain-text session copies? | Product owner | /privacy |
| 13 | Business facts: pricing, certifications, customers, about page, real home-page figures and screenshots (MSoT 2.5) | Product owner | /pricing, /security, home page leaving "Sample data" |
| 14 | Add pages by audience (developers, team leads, finance, IT), following the Product Guide's "Who it is for"? The Page Map has none today | SEO owner | A "By role" menu; phase 2 or 5 scope |
| 15 | Use "historian, not critic" as site wording? It is in the Product Guide, not the MSoT, and depends on decision 9 | Product owner | Home, /privacy, FAQ |
| 16 | Add the Product Guide's search vocabulary (its 13 "how people describe" rows) to the sheet where they have no keyword row yet | SEO owner | /glossary, compare pages |

---

## 7. Risks

| Risk | Mitigation in place or planned |
|---|---|
| A page claims a feature Kite Pulse does not have | Master prompt R1 and R8 (MSoT Section 1 only); fact checker in phase 2 |
| The 8 designed pages repeat Product Guide claims the MSoT corrects (e.g. "Org Overview", cost for all tools, plan limits across tools) | Correct each against the MSoT's "Website corrections" in phase 2. `/shadow-ai` needs rewording to the two signals that exist |
| A new page reuses Product Guide wording, which reads well and carries a stale claim with it | Section 2.4's rule; master prompt R1/R8; the fact checker's refused-phrasings list |
| The MSoT goes stale as the product changes | It names the branch and commit it was checked against; re-check before launch and after each collector release |
| Placeholder prices or limits read as real | Pricing page's warning stays until decision 6; dated sources on every outside fact |
| Preview pages indexed on the MIB domain | Sign-in + `noindex`; prototypes have no public URL |
| The sheet and the site disagree | Site reads only `data/sheet.json`; re-import after every sheet change; sha256 recorded |
| Mentlio already ranks for our terms (tokenmaxxing, AI ROI, AI coding costs) | Interactive pages they lack; integration, solution and compare pages they do not have |
| A prototype renames the classes the preview hides | Master prompt section 7 states them as a contract |
