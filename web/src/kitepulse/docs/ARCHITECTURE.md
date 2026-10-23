# Kite Pulse SEO site — Architecture plan

Written 2026-10-22. Covers what is built today, the decisions behind it, and
the plan from an internal preview to a public site on Kite Pulse's own domain.

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
├── site.css                          its look (the prototypes' design system)
├── KitePulsePanel.jsx                Admin → Kite Pulse SEO
├── admin.css                         that panel's styles (MIB tokens)
├── site.js                           shared: sections, menus, footer, proposed pages,
│                                     prototype registry, sheet loading
├── import_sheet.py                   xlsx → data/sheet.json
├── data/sheet.json                   generated; never edited by hand
├── prototypes/*.html                 finished pages, one per URL
└── docs/                             keyword sheet, Product Guide, this plan,
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
| Home page copy is the Product Guide's, verbatim | No product claim the guide does not make. What is not built (sample dashboard, demo booking) says so. |
| Site structure modelled on mentlio.com, a direct competitor | Reviewed 2026-10-22: a short menu with dropdowns, a home page that tells one story, content typed by URL (`/guides/`, `/glossary/`). The page addresses stay the sheet's. |

---

## 3. Constraints to respect

1. **Deploy builds `web/` only.** Anything the site needs must be inside `web/`.
2. **MIB's rule 2: the number of model-calling stages is fixed.** Today three
   things may call a language model: `judge/extract/`, `judge/ask/`, and the
   blog generator (added 2026-10-06, #508). An automated Kite Pulse page writer
   or AEO tracker would be a **fourth caller**. It needs the same agreement the
   blog generator got, under the same terms: it proposes drafts, a person
   approves, code checks facts, and its spend is recorded. Until then, pages
   are generated by hand with the master prompt.
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
  people ──────────────► │ docs/  keyword sheet · Product Guide │
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
                         │ claims vs Product Guide              │
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
| Fact checker | No | Every product sentence on the page must match a Product Guide sentence; every number must be in the guide or marked as an example | To build (MIB's blog CHECK step is the model) |
| AEO tracker | **Yes**: asks assistants | Asks the 16 AEO questions monthly; **code** decides whether "Kite Pulse" is mentioned | To build; same rule-2 agreement |
| Rank checker | No | Who ranks for each main keyword, via a SERP API | Optional |

---

## 5. Phases

| Phase | Outcome | Main work | Depends on |
|---|---|---|---|
| **1. Preview** ✅ | Kite Pulse inside the MIB app: site preview, admin panel, 3 pages | Done 2026-10-22 | — |
| **2. Content** | All P1 pages written, checked, in `prototypes/` | Master prompt per page; SEO checker; admin "SEO check" and "Content" tabs; add the 4 proposed pages to the sheet | Booking link; owner for the sheet |
| **3. Public site** | Kite Pulse domain live with static, indexable pages | Second Vite build; static assembler; sitemap/robots/canonical/JSON-LD; nginx service; DNS | Domain; decision on page storage (4.1) |
| **4. Measure** | Monthly view of rankings and AI mentions | Search Console; AEO tracker; write Status/Publish date back to the sheet | Rule-2 agreement for the AEO tracker |
| **5. Scale** | P2 and P3 pages; glossary; compare pages | Page planner; optional writer agent | Phase 2 checks in place |

### P1 pages for phase 2 (14 in the sheet, as of 2026-10-22)

`/` · `/features` · `/pricing` · `/privacy` · `/self-hosted` · `/integrations`
· `/integrations/claude-code` · `/integrations/codex` ·
`/integrations/gemini-cli` · `/integrations/cursor` ·
`/integrations/github-copilot` · `/faq` · `/legal/privacy-policy` ·
`/legal/terms`

The five P1 integration pages share one layout: build one, then the other four.

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

---

## 7. Risks

| Risk | Mitigation in place or planned |
|---|---|
| A page claims a feature Kite Pulse does not have | Master prompt R1; fact checker in phase 2 |
| Placeholder prices or limits read as real | Pricing page's warning stays until decision 6; dated sources on every outside fact |
| Preview pages indexed on the MIB domain | Sign-in + `noindex`; prototypes have no public URL |
| The sheet and the site disagree | Site reads only `data/sheet.json`; re-import after every sheet change; sha256 recorded |
| Mentlio already ranks for our terms (tokenmaxxing, AI ROI, AI coding costs) | Interactive pages they lack; integration, solution and compare pages they do not have |
| A prototype renames the classes the preview hides | Master prompt section 7 states them as a contract |
