# UI Page Inventory — SEO Reference

*As of 2026-09-29. Report only — nothing here changes the app. Counts are read from staging (`DATABASE_URL`) and the frontend source in `web/`.*

This is a page-by-page map of the Model Information Board frontend, written for SEO
work: every route, what it renders and from where, what is in the `<head>`, the
heading hierarchy, the framing copy, and — first, because it governs everything
else — what a search crawler actually receives.

---

## 1 · Rendering model — what a crawler actually gets

**The board is a pure client-side React SPA with no server rendering. On first
load a crawler receives an empty shell.** This is the single most important SEO
fact in this document.

- **Stack:** React 19 + `react-router-dom` 7 + Vite 8 (`web/package.json`). There
  is no Next.js, Remix, or any SSR/SSG/prerender step. `web/vite.config.js` builds
  a static `index.html` + JS bundle (`vite build`); `web/src/main.jsx` mounts the
  app into `#root` in the browser. No `renderToString`, no `hydrate`, no prerender
  plugin exists anywhere in `web/src`.
- **The initial HTML is `web/index.html` in full** — nothing is injected at build
  or request time:

  ```html
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#0C0C0E" />
    <meta name="description" content="You describe the work. The board names the models engineers have actually made that work with." />
    <title>ModelBoard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
  ```

  **So a crawler that does not execute JavaScript sees:** the title `ModelBoard`,
  one meta description, and an empty `<div id="root">`. No headings, no links, no
  body copy, no nav — none of it exists until React runs.

- **Everything is behind a client-side auth gate.** `web/src/App.jsx` wraps every
  route except `/login` in `<Require session>`, which redirects to `/login` when
  there is no session (`web/src/auth.js`, a demo gate reading local storage). So
  even a JS-executing crawler with no session is bounced to the login screen
  before any content renders. This matches the project's standing undertaking
  (`internal-development-only`, `auth_walled: true`, `publicly_linked: false` in
  `contract/sources.yaml`): the board is intentionally not public and not meant to
  be indexed **today**. SEO work here is preparation for a future public surface,
  not tuning of a live one.

- **No per-route `<head>` management at all.** There is no `react-helmet`, no
  `document.title` assignment, and no meta/canonical/OG/Twitter tag manipulation
  anywhere in `web/src` (verified by grep). Every route shares the one static
  `<title>ModelBoard</title>` and the one static meta description from
  `index.html`.

- **The only structured data is injected client-side, after a fetch.**
  `web/src/components/Faq.jsx` builds a `<script type="application/ld+json">`
  (`FAQPage`) in a `useEffect` once `/faq` resolves, and appends it to
  `document.head`. It is **not** in the initial HTML, so a non-JS crawler never
  sees it. There is no other JSON-LD, and no `canonical`, `og:`, or `twitter:`
  tags anywhere.

- **A single-file build variant exists** (`npm run build:single` →
  `viteSingleFile`, hash router via `VITE_HASH_ROUTER`). That produces one inlined
  HTML file using `#/...` hash routes — even less crawlable, and intended for a
  standalone/offline artifact rather than a hosted site.

**Bottom line for SEO:** as it stands, first-load HTML carries one title and one
description for the entire site; all routes, headings, copy, and links are
client-rendered behind an auth wall, and the only rich result markup (FAQ) is
JS-injected. A crawler that renders JS but has no session gets the login page;
one that does not render JS gets an empty shell.

---

## 2 · Route inventory

Routes are declared in `web/src/App.jsx`. Dynamic model ids contain a slash
(`anthropic/claude-fable-5-1`), so those routes use a `/*` splat and read the rest
of the path as the id rather than a single `:id` segment.

| URL pattern | Page | Component | Dynamic segment | Auth |
|---|---|---|---|---|
| `/login` | Sign in | `routes/Login.jsx` | — | public |
| `/` | Landing | `routes/Landing.jsx` | — | gated |
| `/board` | Board hub (tabs via `?tab=best\|cap\|met`) | `routes/Board.jsx` | query `?tab` | gated |
| `/board/jobs/:slug` | One job → models reported for it | `routes/Board.jsx` | `:slug` = job slug | gated |
| `/board/jobs/:slug/*` | One model's reports on that job | `routes/Board.jsx` | `*` = model id (may contain `/`) | gated |
| `/board/capabilities/:slug` | One capability → models reported on it | `routes/Board.jsx` | `:slug` = capability slug | gated |
| `/board/capabilities/:slug/*` | One model on that capability | `routes/Board.jsx` | `*` = model id | gated |
| `/board/metrics/:slug` | One metric axis → models with figures | `routes/Board.jsx` | `:slug` = metric slug | gated |
| `/board/metrics/:slug/*` | One model's figures on that axis | `routes/Board.jsx` | `*` = model id | gated |
| `/blogs` | Blog index | `routes/Blogs.jsx` | — | gated |
| `/blogs/:slug` | One blog post | `routes/Blogs.jsx` | `*` = post slug | gated |
| `/models` | The registry (list) | `routes/Models.jsx` | — | gated |
| `/compare` | Compare 2–3 models | `routes/Compare.jsx` | query `?ids=a,b[,c]` | gated |
| `/models/*` | One model's page | `routes/ModelDetail.jsx` | `*` = model id (may contain `/`) | gated |
| `/admin` | Internal ops console | `routes/Admin.jsx` | — | gated |
| `*` (any other) | Redirect → `/` | `<Navigate>` | — | gated |
| `/#faq` | FAQ (anchor on Landing, not a route) | `components/Faq.jsx` | hash | gated |

Notes on route shape:
- **`/compare` is registered before and outside `/models/*`** deliberately: a
  model id has a slash, so a path segment could not carry two ids; the comparison
  lives at `/compare?ids=…` instead (`App.jsx` comment).
- **Board sub-routes are handled by one component** via the `/board/*` splat;
  `Board.jsx` splits the rest of the path into `seg / slug / modelKey` and calls
  the matching view builder in `web/src/board/views.js`.
- **The model key is the whole tail of the path**, not the third segment, so
  canonical ids with slashes survive.

---

## 3 · Per-route detail

For every route: what renders (sections in order + data source), the `<head>`
(identical everywhere — see §1), the heading hierarchy, and the framing copy
(prose/labels only; data rows omitted).

### `/login` — Sign in
- **Renders:** the login form only; `Nav` and `Footer` are suppressed on this
  route (`App.jsx`). Component `routes/Login.jsx`; auth via `web/src/auth.js`
  (demo gate).
- **Data source:** local session (demo), no API content.
- **Head:** static `ModelBoard` / default description.
- **Headings:** login form heading (no page `<h1>` structure for SEO).
- **Copy:** sign-in prompt. Not an indexable content page.

### `/` — Landing
- **Renders (in order):** hero → advantages grid (4 cards) → "The problem"
  section → 3 steps → an "illustrative" numbers card → FAQ. Component
  `routes/Landing.jsx`.
- **Data source:** almost entirely **hardcoded copy** (the `ADVANTAGES` and
  `STEPS` arrays, the problem/numbers sections). The **FAQ** block fetches `/faq`
  (backed by `contract/faq.yaml`).
- **Head:** static (the `index.html` description is this page's hero subline).
- **Headings:**
  - `H1` "Model Information Board" (hero)
  - `H2` "Your coding agent picks its own models. It picks the expensive one." (the problem)
  - `H2` "Frequently asked questions" (FAQ)
  - `H3` × 4 advantage titles ("Evidence", "Independence", "Conditions", "Silence")
  - `H3` × 3 step titles ("Describe the work", "We split it into roles", "Answers, with the words")
- **Framing copy (verbatim):**
  - Hero sub: *"You describe the work. The board names the models engineers have actually made that work with — cheapest first, and shows you their exact words."*
  - CTA button: "See the models" → `/models`.
  - Advantages: Evidence — *"Every claim carries a verbatim quote, verified in code against its source. No quote, no claim — and no scores, only what people actually said."*; Independence — *"Four hundred reshares of one post count once. We count people, not posts…"*; Conditions — *"Fine under five tools, fails above ten…"*; Silence — *"When nobody has tested something, the board says so…"*
  - Problem: *"A sub-agent that summarises a page, classifies an intent or extracts four fields does not need a frontier model…"*
  - Numbers card (badge "illustrative"): "posts harvested / reach the reader / quotes verified / board sections found".

### `/#faq` — FAQ (anchor section on Landing)
- **Renders:** 11 questions from `contract/faq.yaml` via `/faq`
  (`components/Faq.jsx`). Not a route — nav links to `/#faq`.
- **Data source:** `/faq` → `contract/faq.yaml`.
- **Head / structured data:** injects `FAQPage` JSON-LD **client-side after the
  fetch** (see §1). Questions asking about models rather than the board render an
  answer marked "not yet established".
- **Headings:** `H2` "Frequently asked questions"; each question is a
  `<summary>` inside `<details>`.
- **Copy:** eyebrow "FAQ page"; a trailing note explaining that N questions "ask
  about models rather than about the board".

### `/board` — Board hub
- **Renders:** page header + three tabs (**Jobs / Capabilities / Metrics**),
  driven by `?tab` (`best` | `cap` | `met`). Each tab renders a grid of cards from
  the board payload. Component `routes/Board.jsx` → `views.js` `vBoard()`.
- **Data source:** `GET /board` (`boardPage()`), cached into `board/db.js`
  (`DB.jobs`, `DB.caps`, `DB.mets`, and group/coverage metadata). Sections are
  **discovered from evidence**, not configured.
- **Head:** static.
- **Headings:** `H1` "The board"; group sub-headings render with
  `role="heading" aria-level="3"` (not real `<h3>` elements) — e.g. "Reported
  working", "Only neutral reports", "Reported problems".
- **Framing copy (verbatim):**
  - Sub: *"Three ways into the same evidence. **Jobs** lists what was reported on a job. **Capabilities** defines what a claim means… **Metrics** are the axes, and what each one refuses to average."*
  - Jobs tab intro: *"Jobs engineers named when they said what they were running a model for. Each opens a page listing every model reported on that job. Problem reports are shown, not filtered."*
  - Capabilities tab intro: *"A capability means one thing across every model page. These are the definitions the board rules by — written so an answer engine can quote them…"*
  - Metrics tab intro: *"The axes recorded on every model. Each page states the unit, where the figure came from, and the thing the number cannot tell you… Many axes hold a single model…"*
  - A side panel ("How each job's/capability's list is ordered") states the ordering rule in words.

### `/board/jobs/:slug` — a job
- **Renders:** breadcrumb → `H1` job name → lead (`about`, if any) → stat line
  (models / reports / voices / group counts) → one-sentence order line → ranked
  model list (three groups) → "What counts here" (the extractor's counting rule) →
  "Where the pick stops holding" (conditions) → "Related". `views.js` `vJob()`.
- **Data source:** the job's slice of `GET /board` (`DB.jobs`).
- **Head:** static.
- **Headings:** `H1` = job name; `H2` "Where the pick stops holding", "Related"
  (rendered only when populated); `H3` "What counts here"; group pseudo-headings
  as above.
- **Copy:** dynamic per job. `:slug` built as `data-go="job:<slug>"` from the
  card grid.

### `/board/capabilities/:slug` — a capability
- **Renders:** breadcrumb → `H1` capability name → lead (`about`) → "Definition"
  label + definition → stat line → order line + split note → "What this is not"
  → ranked model list → "Related". `views.js` `vCap()`.
- **Data source:** capability slice of `GET /board` (`DB.caps`).
- **Headings:** `H1` = capability name; `H2` "What this is not", "Related".

### `/board/metrics/:slug` — a metric axis
- **Renders:** breadcrumb → `H1` axis name → "also written…" note (spelling
  folds) → sub-line → unit/definition box → "What this metric cannot tell you"
  → "Who has been measured" (model list + single-model caveat) → "Related".
  `views.js` `vMet()`.
- **Data source:** metric slice of `GET /board` (`DB.mets`); a `withheldNote`
  states how many figures are held back from the tab.
- **Headings:** `H1` = axis name; `H2` "What this metric cannot tell you", "Who
  has been measured", "Related".

### `/board/{jobs,capabilities,metrics}/:slug/*` — model drill-downs
- **Renders:** breadcrumb → `H1` "`<model>` on `<section name>`" → sub-line with
  counts + a link to the model's full page → "Reports" (verbatim quotes grouped
  by source document) or, for metrics, "Recorded figures" (a figure table).
  `views.js` `vModelIn()` / `vMetModel()`.
- **Data source:** the model's rows within the section's `GET /board` slice.
- **Headings:** `H1` = "`<model>` on `<section>`"; `H2` "Reports" or "Recorded
  figures", "Related".
- **Note:** these are the deepest and most numerous pages (see §5).

### `/models` — The registry (list)
- **Renders:** header → a "what this page is for" card → search box → count line
  → up to 200 model rows → a sticky compare bar when models are ticked. Component
  `routes/Models.jsx`.
- **Data source:** `GET /models?tracked=1` (`listModels`, paged via `fetchAll`).
  **The list shows the tracked set only** (17 entries in
  `contract/tracked_models.yaml`), not the whole registry.
- **Head:** static.
- **Headings:** eyebrow "Models"; `H1` "The registry".
- **Framing copy (verbatim):**
  - *"Every model the board tracks. **Open one** to read what engineers have said about it, verbatim and with a link to each source — split into the **jobs** they used it for, the **capabilities** they reported, and the **metrics** they quoted."*
  - *"**Tick two or three to compare them.**"*
  - Search placeholder: "Search `N` models — name, provider, or id".
  - A row with no registry entry renders un-linked (no model page exists for it).
  - Client caps the list at 200 with a plain-language note; the API does not
    paginate.

### `/models/*` — a model page
- **Renders:** back link → eyebrow "Model" → `H1` model display name → provider →
  "last fetched" line → Fetch panel → `ModelEvidence` (what was said, grouped by
  discovered section). Component `routes/ModelDetail.jsx`.
- **Data source:** `GET /models/{id}` (`modelPage`), `GET /models/{id}/evidence`
  (`ModelEvidence`), plus `GET /models?tracked=1` for the provider string.
- **Head:** static (the `<h1>` is the only place the model name appears — **not**
  in `<title>`).
- **Headings:** eyebrow "Model"; `H1` = model display name. Section headings come
  from `ModelEvidence`.
- **Note:** `/models/{id}` refuses an id the registry does not hold; the advertised
  spec panel and capability cards were removed (this board shows reported
  evidence, not vendor spec sheets).

### `/compare` — compare models
- **Renders:** with < 2 ids, an empty-state (`H1` "Compare models side by side" +
  prompt to pick on the models list). With 2–3 ids: `H1` "`A` vs `B`" → summary →
  a "change models" picker → "What engineers said, counted" table → "Where they
  can be compared directly" (shared-axes table). Component `routes/Compare.jsx`.
- **Data source:** `GET /compare?ids=…` (`comparePage`), plus
  `GET /models?tracked=1` for the picker. The URL (`?ids=`) is the shareable
  state.
- **Head:** static; `H1` is dynamic ("A vs B") but never reaches `<title>`.
- **Headings:** eyebrow "AI model comparison"; `H1` "Compare models side by side"
  / "`A` vs `B`"; section labels "What engineers said, counted", "Where they can
  be compared directly".
- **Copy:** *"…compare what engineers have actually reported about them — counted,
  side by side, with no synthesised score and no winner picked for you."* Empty
  states say plainly when nobody has written about the chosen models.

### `/blogs` — blog index
- **Renders:** `H1` "What we found while building the board" → sub → a grid of
  post cards, or "No posts yet". `views.js` `vBlogs()`.
- **Data source:** `DB.posts`, populated from the `GET /board` payload's `posts`
  field. **There is no posts table in staging** (verified), so this currently
  renders "No posts yet" unless the API injects demo posts. The code notes the
  blog path was "ported from the SEO demo" and uses "demo data in this build".
- **Headings:** `H1` "What we found while building the board"; post titles as
  `H3`.

### `/blogs/:slug` — a blog post
- **Renders:** breadcrumb → `H1` post title → article meta → article body (with
  E1–E5 evidence bookmarks) → "Evidence behind this post" panel → related.
  `views.js` `vPost()`.
- **Data source:** the matching entry in `DB.posts` (see above; demo/empty today).
- **Headings:** `H1` = post title; `H2`s from the post body; `H3` "Evidence behind
  this post".

### `/admin` — internal ops console
- **Renders:** a viewport-locked multi-pane console (no Footer). Panels include
  Fetch, Runs, Sources, Prompts, Stages, Settings, Usage, Keywords, Database,
  Board review, Model proposals. Component `routes/Admin.jsx`.
- **Data source:** many `GET/POST /admin/*` endpoints (`/admin/pipeline`,
  `/admin/runs`, `/admin/usage`, `/admin/board-entries…`,
  `/admin/capability-candidates`, `/admin/models/propose`).
- **SEO relevance:** none — an internal tool. Should never be indexed.

### `*` — catch-all
- Any unmatched path redirects to `/` (`<Navigate to="/" replace>`). There is no
  custom 404 page.

---

## 4 · Sitemap & robots

**Neither exists.**

- **No `robots.txt`** — `web/public/` contains only `favicon.svg` and `icons.svg`;
  there is no `robots.txt` anywhere in the repo.
- **No `sitemap.xml`** — none in the repo, and nothing generates one. There is no
  build step, script, or backend route that emits a sitemap.
- **Consequence:** every dynamic page (each model, job, capability, metric, and
  every model drill-down) is reachable **only by clicking** through the
  client-rendered UI (`data-go` handlers wired by `board/BoardView.jsx`, and
  react-router `<Link>`s). None of it is enumerated for a crawler. Combined with
  the auth gate and client-only rendering (§1), the discoverable surface for an
  external crawler today is effectively **zero**.

---

## 5 · Page counts — the indexable surface

Real counts, read from staging (`DATABASE_URL`) on 2026-09-29. Section and
drill-down counts are **distinct non-declined slugs in `board_entry`**
(merged slugs folded into `ruling_target`); the live board withholds some figures
(especially metrics), so the number of pages that render with visible content can
be lower than the route count, but the routes resolve.

| Page type | Count | Source / denominator |
|---|---:|---|
| **Model pages** (`/models/*`) | **244** | `model_version` rows (all in-window); route exists per model |
| — of which listed on `/models` | **17** | tracked set in `contract/tracked_models.yaml` (`?tracked=1`) |
| — models with ≥1 board entry | **78** | distinct `model_version_id` in `board_entry` (non-declined) |
| **Job pages** (`/board/jobs/:slug`) | **98** | distinct `best_for` slugs |
| **Capability pages** (`/board/capabilities/:slug`) | **298** | distinct `capability` slugs |
| **Metric pages** (`/board/metrics/:slug`) | **144** | distinct `metric` slugs |
| **Job drill-downs** (`…/jobs/:slug/*`) | **159** | distinct (job slug × model) |
| **Capability drill-downs** | **567** | distinct (capability slug × model) |
| **Metric drill-downs** | **304** | distinct (metric slug × model) |
| **Blog posts** (`/blogs/:slug`) | **0** | no posts table in staging; index shows "No posts yet" |
| **Fixed routes** | **8** | `/`, `/login`, `/board`, `/blogs`, `/models`, `/compare`, `/admin`, catch-all (FAQ is an anchor on `/`) |

**Totals:** roughly **1,820 distinct URLs** — 540 section pages
(98 + 298 + 144), 1,030 drill-downs (159 + 567 + 304), 244 model pages, and 8
fixed routes. Board entries behind these: **1,873** non-declined rows.

Caveats:
- The board applies withholding/publication logic in `GET /board`, so rendered
  section pages with content ≤ the distinct-slug counts above. Exact "shown"
  numbers require calling the board API; the DB counts are the upper bound and the
  honest denominator.
- Drill-down counts pair every non-declined entry's slug with its
  `model_version_id`; a slug with no model-attributed rows has fewer (or no)
  drill-downs.

---

## 6 · SEO issues as it stands

A flat list of what would hurt SEO for a public launch. Not fixed — just flagged.

1. **Client-only rendering, no SSR.** First-load HTML is an empty `#root`. A
   non-JS crawler gets nothing; content, headings, and links exist only after
   React runs. (§1)
2. **Whole site behind a client-side auth gate.** Every content route redirects to
   `/login` without a session, so a crawler reaches no content even with JS. This
   is intentional today (internal-development-only undertaking), but it is the
   gating SEO blocker.
3. **One static `<title>` for the entire site** (`ModelBoard`). No route —
   including every model, job, capability, and metric page — sets its own title.
4. **One static meta description for the entire site.** No per-route descriptions;
   no dynamic descriptions from content.
5. **No `<head>` management library or logic.** No `react-helmet`, no
   `document.title`, no meta updates anywhere.
6. **No canonical tags.** With query-driven pages (`/compare?ids=`, `/board?tab=`)
   and slash-bearing ids, duplicate/parameter URLs have nothing declaring a
   canonical.
7. **No Open Graph or Twitter card tags.** Shared links have no title, image, or
   description preview.
8. **Structured data (FAQ JSON-LD) is JS-injected after a fetch**, not in the
   initial HTML — invisible to non-rendering crawlers, and only on the landing
   page.
9. **No `sitemap.xml`.** ~1,800 dynamic URLs are enumerated nowhere. (§4)
10. **No `robots.txt`.** No crawl directives at all (neither allow nor disallow).
11. **Dynamic pages are click-only.** Every model/job/capability/metric page is
    reachable only through client-side `data-go`/`<Link>` navigation — no crawlable
    `<a href>` link graph to them on first load.
12. **No custom 404.** Unknown paths client-redirect to `/`, so a crawler hitting a
    stale URL gets a soft-redirect to the home shell rather than a proper status.
13. **Duplicate/near-identical headings across many pages.** The board's group
    pseudo-headings ("Reported working", etc.) and repeated section headings
    ("Related", "Reports") recur across hundreds of pages; several boilerplate
    intros are identical across all job/capability pages.
14. **Group headings are not real heading elements.** Board group headings use
    `role="heading" aria-level="3"` on `<p>`, not `<h3>` — weaker as document
    structure for crawlers that read the tag tree.
15. **Thin / no-unique-text pages at scale.** 62 of 84 metric axes historically
    held a single model (per code comments), and many drill-down pages render a
    short caveat plus one quote. Metric pages also withhold figures, so some render
    almost no unique body text.
16. **Empty content states that still resolve as pages.** `/blogs` (0 posts today)
    and single-model metric pages render valid routes with little indexable
    content.
17. **The model name never reaches the title/URL in a stable, keyword form.**
    Model pages key on `model_version_id` in the URL (`/models/mv_…` or a
    canonical id), and the display name appears only in an `<h1>`; there is no
    slugged, title-bearing URL per model.
18. **The single-file build variant uses hash routing** (`#/…`), which is not
    crawlable as distinct URLs — relevant only if that artifact is ever hosted.

---

*Sources: `web/` frontend source (App, routes, board/views, components, api,
index.html, vite.config); `contract/sources.yaml` (undertaking),
`contract/tracked_models.yaml`, `contract/faq.yaml`; staging `board_entry` and
`model_version` via `DATABASE_URL`, read 2026-09-29.*
