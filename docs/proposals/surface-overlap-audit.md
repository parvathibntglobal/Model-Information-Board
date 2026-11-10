# Surface overlap audit: which pages to merge or retire

**Date:** 2026-11-02. **Read at:** `feat/hooks-prototype`, commit `c908c20`.
That commit landed while this audit was being written. It removed `/my-models`
and moved its three new parts (a Follow list, "since you last looked" and a
weekly trend) onto the model page, AI updates and the evidence feed. Everything
below describes the code **after** `c908c20`.

**Status:** a proposal for the team to decide on. Nothing has been changed.

**Step 1 of the order below, answered 2026-11-02:** the live frontend
(`frontend-production-132c.up.railway.app`) serves `robots.txt` with
`Disallow: /` and the page carries `<meta name="robots" content="noindex,
nofollow">`. The site is closed to search today, so the redirects proposed here
cost nothing in search, as long as they land before it opens.

**How this was done:** I read the code only: routes (`web/src/App.jsx`), menus
(`Nav.jsx`, `Footer.jsx`), each page's header comment and data calls,
`judge/app.py` endpoints, `judge/gate.py` `PUBLIC_READ_PATHS`,
`contract/indexing.yaml`, `judge/seo.py`, `web/seo-build.js` and
`web/nginx.conf.template`.
**What was not done:** I rendered no page and ran no database query. I had no
traffic or Search Console data. Where a duplicate is called "the same data",
that means the same endpoint and the same payload fields, read from code. It is
not a measured comparison of what two pages display on a given day.

---

## One-page summary

### The hypothesis, tested

> *"The site answers about three user questions through about nine surfaces."*

- **Three questions: mostly holds.** "What changed?", "Which model for my
  task?" and "What do engineers say about model X?" cover every evidence page.
  One more question has its own pages and its own kind of data: **"What will it
  cost me, and will it run?"** That is the pricing and specs table, the token
  counter and the VRAM calculator. They read *advertised* or *measured* data,
  never reports, and the site's own rule keeps the two apart
  (`Compare.jsx`: "advertised and reported are never in the same block").
  Below, this question is treated as part of "Which model for my task?" but it
  keeps its own pages. The learning pages (blogs, guides, glossary,
  methodology) and Discussions answer other questions and are not part of the
  merge.
- **Nine surfaces: about half the real number.** Counting route families, not
  individual URLs, the three questions are answered by **15 public route
  families (P7 to P21 below) plus the home page's updates strip, and 7
  signed-in pages (S1 to S7)**.

### The three biggest duplications

| # | Duplication | Evidence in code |
|---|---|---|
| 1 | **One model, three public pages built from the same counts.** `/ai-models/<id>` (model page), `/reviews/models/<id>` (reviews) and `/evidence/<id>` (feed) all show what engineers report about one model. The model page shows the top 8 jobs, capabilities and metrics, then links to the reviews page for "every job, capability and metric". Every count on both pages links into the feed. | `judge/seo.py` ~L215-233 lists **up to three indexable URLs per model**: `/ai-models/<id>`, `/reviews/models/<id>` and `/alternatives/<name>`, each with its own canonical. Model page and reviews both read `GET /reports`. |
| 2 | **One job, two public pages built from the same payload.** `/reviews/jobs/<slug>` and `/best-ai-model/<slug>` both read `GET /reports` for the same job. | `judge/seo.py` ~L155: *"A JOB HAS A SECOND PUBLIC PAGE … the same evidence asked as 'which model'."* They also **disagree by default**: the picker shows models with 3+ voices (`ModelPicker.jsx` `DEFAULTS.minV: 3`) and reviews shows 5+ (`Reports.jsx` `min … : 5`). The picker has no "from 2+ platforms" filter. A reader who opens both gets two different model lists for one job. |
| 3 | **Two lists of "models engineers reported on".** `/ai-models` ("the models engineers have reported on, most voices first") and `/reviews` ("AI model reviews: ranked by engineer reports"). | Different endpoints (`/model-catalog` and `/reports`) and different units. The catalogue counts voices across the whole model. Reviews counts per job, capability or metric, above a threshold. So the same model can carry different numbers on the two lists, and neither page says why. |

Next in line is **"What changed?" split five ways.** The home page strip, AI
updates (`/ai-news-headlines`), `/ai-models/latest`, and the signed-in
`/updates` and `/price-changes` pages. Most of this is a pipeline (one is a
work queue that feeds the next) rather than duplication, so it needs labels
more than merges. See Q1 below.

### Proposed destinations

| Question | ONE destination | Merges in (content moves, old URL redirects) | Becomes a tab, mode or filter of it | Stays separate, and why |
|---|---|---|---|---|
| **Q1 What changed?** | **`/ai-news-headlines`** (AI updates) | none | The home page strip stays as its teaser (it is a subset: published updates are a subset of approved ones). "Only my models" (`?mine=1`) is the personal view. | `/ai-models/latest`: a sort of the directory, and a phrase people search. Signed-in `/updates`, `/price-changes`, `/benchmarks` and `/news` are the team's sources and queues behind Q1. They are internal tools and are kept out of the merge. |
| **Q2 Which model for my task?** | **`/best-ai-model`** (picker) | `/reviews/jobs/<slug>` redirects to `/best-ai-model/<slug>`. `/reviews/capabilities/<slug>` redirects to a new `/best-ai-model/capability/<slug>`. `/reviews/jobs` and `/reviews/capabilities` redirect to `/best-ai-model`. `/tools` redirects to `/best-ai-model`. | `/alternatives/*` is already a mode of the picker. `/compare` is opened from the picker. | `/ai-model-pricing`, `/token-counter`, `/local-llm-vram-calculator`: they use advertised or measured data, not reports, and people search for each one separately. `/reviews/metrics`: the picker reads no metrics by design. Signed-in `/board`: the only place with quotes and per-model drill-downs. |
| **Q3 What do engineers say about X?** | **`/ai-models/<provider>/<model>`** (model page) | `/reviews/models/<id>` becomes a "Reports" section. `/evidence/<id>` becomes an "Evidence" tab. `/reviews` (and `/reviews/models`) redirects to `/ai-models`. `/evidence` (the model picker) redirects to `/ai-models`. | `/ai-models` and `/ai-models/<type>` are the directory into it. `/compare/<a>-vs-<b>` is the two-model view. | `/ai-benchmarks/<id>`: Parvathi's page, and the terms note on its sources keeps it out of search. Signed-in `/models` and `/models/<id>`: retire later, with Parvathi. |
| *Learn* (not one of the three) | none | none | `/methodology` becomes the one place that explains counting (see Q2 notes) | Blogs, guides, glossary, Discussions |
| *Internal* | **out of the merge** | none | none | Admin (and Blog logs), SEO keywords, Updates Manage. The same goes for Benchmarks, Price changelog and News as working tools. Kite Pulse is another product. |

**After the merge:** 3 destinations.

- **Q1:** 7 surfaces including the destination: the strip stays as a teaser,
  `/ai-models/latest` is linked, and 4 signed-in feeders are untouched. No
  redirects.
- **Q2:** 11 surfaces including the destination. 3 redirect (`/reviews/jobs`,
  `/reviews/capabilities`, `/tools`), 2 are modes (`/alternatives`, `/compare`),
  4 public pages stay separate, and the Board stays.
- **Q3:** 9 surfaces including the destination (`/compare` is shared with Q2).
  3 merge in and redirect (`/reviews/models/<id>`, `/evidence/<id>`, and the
  `/reviews` and `/evidence` lists). `/ai-models` and `/compare` are doorways.
  `/ai-benchmarks` stays. 2 signed-in pages retire later.

**The backend is already consolidated.** `GET /reports` feeds Reviews, the
picker, the model page and the home page's "Most reported" card. The
duplication is in front-end routes and in `judge/seo.py`'s list of indexable
paths, not in the data.

**Recommended order (detail in section 4):**
1. Check whether the live site is open to search.
2. Make the picker agree with Reviews on thresholds.
3. Redirect the job pages.
4. Build the model page's Reports and Evidence tabs and redirect those pages.
5. Give capabilities a picker path.
6. Do the small items: `/tools` and methodology.
7. Do the signed-in `/models` and `/ai-benchmarks` decisions, with Parvathi.

---

## 1. Per-page inventory

Personas: **F** founder, **E** engineer, **T** tech lead or CTO, **I** indie
builder. **"Come back"** means something that brings a visitor back or tells a
returning visitor what is new. A bookmarkable address is noted, but it is not a
come-back mechanism: it returns you to the same answer, not to anything new.

**Site-wide, nothing reaches a visitor who is not on the site.** There is no
RSS, no email, no account and no push. Every come-back mechanism lives in one
browser's `localStorage`: the home page strip's "New" marker, and the Follow
list (`web/src/follow/follow.js`, added in `c908c20`).

### Public pages

| ID | Path | Q | Data | Persona | Come back | Overlaps / unique |
|---|---|---|---|---|---|---|
| P1 | `/` Home | Entry to all | `/updates/published` (strip), `/reviews` and `/model-catalog` (ModelsShowcase), `/models` (ToolsShowcase), `/blog-posts`, `/faq`. The hero quotes and ReportExamples are fixed in code. | F, I | **Weak yes.** The strip marks headlines "New" since this browser's last visit. | Four carousels plus the closing swipe repeat the Nav and point to about 12 places. No single question leads. **Unique:** the FAQ section (the one `FAQPage` structured data), and the strip. |
| P2 | `/blogs`, `/blogs/:slug`, `/blogs/directory` | Learn | `/blog-posts` (approved), `/model-catalog`, `/models` | F | No. New posts can only be found by visiting. | **Unique:** written analysis. |
| P3 | `/blogs/guides` | Learn (Q1-adjacent: migrating off a model) | `/blog-posts`, `/guide-facts` | E, T | No | **Unique:** migration and developer guides. The guide facts repeat model-page specs for two models, on purpose. |
| P4 | `/glossary`, `/glossary/:slug` | Learn | `/glossary-terms` (glossary.yaml) | F | No | **Unique.** |
| P5 | `/methodology` | Learn (trust) | `/faq` (platform list) | T | No | **Duplicated in three other places:** the "How the reports work" boxes at the foot of every `/reviews` list, the "How we count" pop-up on `/reviews`, and the home page FAQ. The header names `routes/Reports.jsx` as its source of truth. |
| P6 | `/discussions` | Other: "what are other readers seeing" | `/discussions` (+ POST `/discussions/posts`), `/model-catalog` | E | No. A poster is not told about a reply. | **Unique:** readers' own posts, never added to counts. |
| P7 | `/tools` | Q2 (hub) | none (4 static links) | I | No | **Nothing unique.** The same four links are in the Nav "Tools" menu, the footer and the home page's ToolsShowcase. |
| P8 | `/best-ai-model`, `/best-ai-model/:job`, `/alternatives/:model`, `/alternatives/:provider` | **Q2** | `/reports` (`board_entry` via `board_sections`, public view) plus `/models` registry prices (`model_version`) | I, E (alternatives: T) | No (bookmarkable) | **Duplicates P10** for jobs: same payload, different default threshold. **Unique:** price next to evidence, "saves $x", price bands, Top picks (one stated rule each), alternatives to a model or provider. |
| P9 | `/reviews`, `/reviews/models`, `/reviews/models/:id` | **Q3** | `/reports` | E | No (freshness dates only) | **List duplicates P12.** **Item duplicates P14** (top 8 of the same axes) and **P15** (every count links there). **Unique:** a model's *full* job, capability and metric breakdown with charts by side, the 3/5/10 and 2+ platform thresholds, and a tick-to-compare on the list. |
| P10 | `/reviews/jobs[/:slug]`, `/reviews/capabilities[/:slug]` | **Q2** | `/reports` | E | No | **Duplicates P8.** **Unique:** the 2+ platforms filter, a 5/10 threshold, the method boxes, and capability pages at an indexable path (the picker has capabilities only as `?capability=`, which is not listed). |
| P11 | `/reviews/metrics[/:slug]` | Q2 / Q3 ("how does it score") | `/reports` (metric axes) | E | No | **Unique:** the only public page of figures engineers measured themselves. Shares a topic with P20 but not its data: engineer-reported figures against published leaderboards. |
| P12 | `/ai-models`, `/ai-models/:type`, `?provider=` | Q3 (directory) | `/model-catalog` (`model_catalog` plus voices from `board_entry`) | F, I | No | **List duplicates P9.** **Unique:** facets by type and provider, the 7 model types, price on each card. |
| P13 | `/ai-models/latest` | **Q1** | `/model-catalog` (`new_releases`) | F, T | No | **Shares a topic with P21's "Launches":** different source (catalogue listing date, and models with no voices) against `model_event` launches a person approved. **Unique:** every new listing, including ones nobody has reported on. |
| P14 | `/ai-models/:provider/:model` (model page) | **Q3** | `/model-catalog/<id>`, `/reports`, `/watch` (ModelPulse: `board_entry`, `model_event`, `model_version`), `/freshness` | E, T | **Yes (new in `c908c20`).** Follow button. "What's new since your last look" and reports per week (ModelPulse). | **Duplicates P9-item** (top 8 axes). **Unique:** price, the workload cost calculator, specs with "not stated", Lifecycle and retirement, Follow, What's new. |
| P15 | `/evidence`, `/evidence/:vendor/:model` | **Q3** | `/feed`, `/feed/summary`, `/feed/models`, `/model-catalog` (paraphrases over `board_entry`, `judge/feed/`) | E | **In session only:** page 1 is fetched again every 5 minutes. Followed models come first in the picker. | **The index duplicates P12** (choosing a model). **Unique:** the reports themselves (our paraphrase with its source or an official embed), the approved summary, and polarity filters. Not in `judge/seo.py` and not indexed. |
| P16 | `/compare`, `/compare/:a-vs-:b` | Q2 / Q3 (A or B?) | `/compare` (`model_version` roster plus `evidence_for_model`; counts only when signed out) | T | No (bookmarkable) | Every row exists on each model's page. **Unique:** the side-by-side view, the category score (#540, its only use under rule 3), and pair URLs (indexed via `compare_pairs`). |
| P17 | `/ai-model-pricing` | Q2 (cost/spec) | `/model-catalog` | I, E | No (bookmarkable) | **Same data as P14's price and specs**, for every model at once. **Unique:** filtering on spec and price, and the "not stated" group. |
| P18 | `/token-counter` | Q2 (cost) | `/models` registry | I | No | **The same arithmetic as P14's workload card** (`tokens/cost.js`), across every model. **Unique:** tokenises your own text in the browser. |
| P19 | `/local-llm-vram-calculator` | Q2 (will it run) | `/local-models` (Hugging Face GGUF sizes, registry prices) | I | No (bookmark "your machine") | **Unique:** the only check of local hardware. |
| P20 | `/ai-benchmarks[/:model]` | Q3 ("how does it score") | `/ai-benchmarks` (`bench_` tables via `benchmarks.charts`) | E | No | **The public view of S4's table.** **Unique:** published benchmark scores. Shares a topic with P11. |
| P21 | `/ai-news-headlines` (AI updates) | **Q1** | `/updates/approved` (built by `judge/updates.py` from `model_event`, `model_version.retirement_date`, `price_changes`, benchmarks changelog) | T, F | **Yes.** "Only my models" (`?mine=1`, new in `c908c20`), the 7-day counts and retirement countdowns. No memory of your last visit on this page. | **A superset of P1's strip.** **Unique:** the full approved record, retirements, the weekly round-up. The label "AI updates" does not match the path `/ai-news-headlines`. |

### Signed-in pages (`<Require>` in `App.jsx`; all in `never` in `contract/indexing.yaml`)

| ID | Path | Q | Data | Persona | Come back | Overlaps / unique |
|---|---|---|---|---|---|---|
| S1 | `/board/*` | Q2 + Q3 (team) | `/board`, `/freshness` (`board_entry` **with quotes**, every source, no threshold) | Team (E) | Work tool | Counts duplicate P9 to P11. **Unique:** verbatim quotes, sources that are withheld from the public pages, and one model inside one section (`seo.py`: "the drill-down lives only on the signed-in board"). |
| S2 | `/models` | Q3 (team) | `/models?tracked=1` plus the capability pages | Team | Login lands here (`App.jsx` `/login` falls back to `/models`) | **Largely P12 + P17** for the 30 tracked models (`contract/tracked_models.yaml`). The price column was removed at Parvathi's request. **Unique:** the tracked-set view. |
| S3 | `/models/:id` | Q3 (team) | `/models/<id>`, `/models/<id>/evidence`, `/freshness`, fetch log | Team | No | **Overlaps P14, P9-item and P15.** **Unique:** verbatim quotes per model (ModelEvidence), last-fetched status. |
| S4 | `/benchmarks` | Q1 / Q3 source | `/benchmarks/*` (table, changelog, runs, unmatched, review) | Team | Work queue | **Internal tool.** Feeds P20 and the benchmark kind of update in P21. |
| S5 | `/price-changes` | Q1 source | `/admin/price-changes` (`judge/price_changes.py`) | Team | Work queue | **Internal tool.** Feeds the price kinds of update in P21 (`newsworthy` only). **Unique:** every change, including ones that are not news. |
| S6 | `/news`, `/news/:id` | Q1 (outside AI news) | `/news`, `/news/<id>` (publishers' feeds, `collect/news/`) | Team | No | **Unique source.** Outside headlines, not our data. A story page links the models it names to board counts. |
| S7 | `/updates` (News headlines + Manage) | Q1 source | `/updates`, `/updates/review`, `/updates/undo`, `/updates/approve-all` | Team | Work queue | **"News headlines" is a superset of P21** (every update not declined, against approved only). **Manage is internal** and out of the merge. |
| S8 | `/admin`, `/admin/blog-logs` | Internal | `/admin/*`, `/health`, `/coverage`, `/blog-posts/*` | Team | n/a | **Out of the merge.** |
| S9 | `/seo-keywords` | Internal | `/admin/seo-keywords`, `/admin/seo-keyword-plan` | Team | n/a | **Out of the merge.** |
| n/a | `/kite-pulse/*`, `/login` | n/a | n/a | n/a | n/a | Another product's preview, and the sign-in screen. Not content. Excluded. |

Redirect routes (`MovedTo`, `CatalogMoved`, `ReportsMoved`) are excluded, and
so is `/my-models`, which `c908c20` removed.

---

## 2. Grouped by question: what is duplicated, what is unique

### Q1 "What changed?": P1 strip, P13, P21, plus S4, S5, S6, S7

- **Truly duplicated:** the strip is a subset of P21 by construction
  (published ⊂ approved). S7's "News headlines" tab is P21 without the approval
  filter. Both are deliberate: a teaser and a review queue. Neither is a
  second answer to the question.
- **Overlapping topic, different data:** P13 (`/ai-models/latest`: the
  catalogue's newest listings, including models nobody has reported on) and
  P21's Launches (`model_event` new models a person approved). A reader asking
  "what launched this week?" gets two lists that do not quite agree, and
  neither page says how it differs from the other.
- **Unique:** P21's approved record and retirement countdowns. S5's full price
  changelog. S6's outside news (a different source altogether). The model
  page's "What's new" for one followed model.
- **Verdict:** little real duplication. The problem is labelling ("AI updates"
  at `/ai-news-headlines`, "News" against "Updates" in the account menu). There
  is also no cross-link between P13 and P21's Launches.

### Q2 "Which model for my task?": P7, P8, P10, P11, P16, P17, P18, P19, plus S1

- **Truly duplicated:** P8 job pages against P10 job pages: same `/reports`
  payload, both indexed, and different default thresholds (3 against 5). P8
  `?capability=` against P10 capability pages: same data, but only P10 has an
  indexable path. P7 (`/tools`) against the Nav menu, the footer and the home
  page's ToolsShowcase: four copies of four links.
- **Unique:** P8's price-aware alternatives and Top picks. P10's 2+ platforms
  filter and method boxes. P11's engineer-measured figures (the picker reads no
  metrics by design: `ModelPicker.jsx` "NO METRICS"). P16's side-by-side view
  and category score. P17, P18 and P19 each answer a cost or fit question with
  data that is not evidence. S1's quotes and drill-downs.
- **Verdict:** the job and capability pages exist twice. The cost and fit tools
  are not duplicates of the evidence pages. They overlap each other only
  slightly: P17 and P18 both list every model's price, for different tasks.

### Q3 "What do engineers say about model X?": P9, P12, P14, P15, P16, P20, plus S2, S3

- **Truly duplicated:** P9-item against P14. Same counts from `/reports`: P14
  shows the top 8 axes, P9 shows all of them. P9-list against P12: two
  directories of reported models, in different units. P15's index against P12:
  a third "choose a model" list. S3 against P14, P9-item and P15: the
  signed-in version of the same model, with quotes.
- **Unique:** P14's price, workload, specs, lifecycle, Follow and What's new.
  P9-item's full breakdown with thresholds. P15's report-level evidence and
  summary. P20's published benchmark scores. S3's verbatim quotes.
- **Verdict:** this is the biggest duplication. A model has one *data* story,
  told in three public places. A reader landing on any one of them from search
  is pushed to the other two to get the whole picture.

### Learn and Community (not merged)

The only duplication is **how counting works**, told in four places:
`/methodology`, the method boxes on `/reviews`, the "How we count" pop-up and
the home page FAQ. Proposed: `/methodology` keeps the full text, and the others
link to it with one line.

---

## 3. Consolidation proposal

### Q1: destination `/ai-news-headlines` (AI updates)

- **Keep as is:** the home page strip (teaser, with "All updates →" already
  linking here).
- **Add:** in the Launches section, a link "Every new listing, including models
  nobody has reported on yet → `/ai-models/latest`", and one line saying how
  the two lists differ. **No redirect** for `/ai-models/latest`: it is a sort of
  the directory and a phrase people search.
- **Stay separate (internal, out of the merge):** `/updates` (Manage and its
  News headlines view), `/price-changes`, `/benchmarks`, `/news`. They are the
  team's sources and approval queues. Merging a queue into the public page it
  feeds would publish the queue.
- **Open question, not proposed here:** whether the public label and the path
  should agree (`AI updates` against `/ai-news-headlines`). The path was chosen
  for search (Parvathi, 2026-10-30), so this is hers to decide.

### Q2: destination `/best-ai-model` (the picker)

- **Before any redirect, the picker must carry what P10 has**, or the redirect
  loses information:
  1. one default threshold for both (today 3 against 5);
  2. the "from 2+ platforms" filter;
  3. 10 as a threshold option;
  4. the method boxes replaced by one line and a link to `/methodology`.
- **Merge and redirect:**
  - `/reviews/jobs/<slug>` redirects (301) to `/best-ai-model/<slug>`.
  - `/reviews/jobs` redirects to `/best-ai-model`, which already lists the jobs
    to start from.
  - `/reviews/capabilities/<slug>` redirects to `/best-ai-model/capability/<slug>`.
    That is a **new path**: today the picker has capabilities only as
    `?capability=`, which is not indexable. Build the path first, then redirect.
  - `/reviews/capabilities` redirects to `/best-ai-model`.
  - `/tools` redirects to `/best-ai-model`, which gains a short "More tools"
    strip for the three calculators. The Nav "Tools" label can open the picker
    directly, the way "Insights" opens its first item.
- **Already modes of the destination:** `/alternatives/<model>` and
  `/alternatives/<provider>`. `/compare` is opened from the picker's compare
  tray.
- **Stay separate:**
  - `/ai-model-pricing`, `/token-counter`, `/local-llm-vram-calculator`. Each
    reads advertised or measured data, never reports, and the site keeps those
    apart from evidence. Each also matches a distinct search ("LLM cost
    calculator", "can I run it"). They are linked from the destination, not
    folded into it.
  - `/reviews/metrics`. The picker refuses metrics because a figure needs its
    quote. It stays where it is for now. Later it is a candidate to sit beside
    `/ai-benchmarks` as one "how does it score" area, which needs Parvathi (see
    risks).
  - Signed-in `/board`. It is the only place with quotes, sources withheld from
    the public pages, and one model inside one section. It is the team's review
    surface.

### Q3: destination `/ai-models/<provider>/<model>` (the model page)

- **Merge and redirect:**
  - `/reviews/models/<id>` moves into the model page as a **"Reports"
    section**: the full breakdown by job, capability and metric, with the
    threshold controls. It replaces today's top-8 block and its "Every job,
    capability and metric →" button. Then redirect (301), keeping `?min=` and
    `?multi=`.
  - `/evidence/<vendor>/<model>` becomes an **"Evidence" tab** of the model page
    (for example `/ai-models/<id>/evidence`). Every count already links there
    through one helper (`catalog/format.js` `evidencePath`), so the move is
    mostly one function. The redirect must carry `section`, `slug`, `polarity`
    and `tab=summary`.
  - `/reviews` and `/reviews/models` redirect to `/ai-models`. Move the list's
    tick-to-compare and its "jobs / capabilities / metrics per model" counts
    onto the `/ai-models` cards first.
  - `/evidence` (the model picker) redirects to `/ai-models`. The "followed
    first" ordering moves to the directory.
- **Doorways, not duplicates:** `/ai-models` and `/ai-models/<type>`
  (the directory). `/compare/<a>-vs-<b>` stays as the two-model view, linked
  from the model page's existing "Compare with…" button.
- **Stay separate:**
  - `/ai-benchmarks/<model>`. It is Parvathi's page, and `judge/gate.py` records
    that the benchmark sources' terms are an accepted risk on condition that
    "the page stays out of search engines". Moving those values onto the
    indexed model page would break that condition. So: link it from the model
    page, do not merge it.
  - Signed-in `/models` and `/models/<id>`. Proposed to **retire later**: the
    model page gains a signed-in-only "Quotes" section (ModelEvidence), and
    login lands on `/ai-models` or `/board` instead of `/models`. This needs
    Parvathi (see risks) and does not block anything else.

### Kept out of the merge, on purpose

Admin (including Blog logs), SEO keywords and Updates Manage are internal tools.
Benchmarks, Price changelog and News are treated the same way here: working
tools that feed public pages. Kite Pulse is another product. None of them is
proposed for merging, and the proposals above add no public link to any of
them.

---

## 4. Risks

### Search and indexing

- **First check whether the site is open to search.** `web/index.html` carries
  `noindex, nofollow`. `web/seo-build.js` opens indexing only when both
  `SITE_URL` and `PUBLIC_SITE=1` are set, and `contract/indexing.yaml` is headed
  "PROPOSED, NOT RATIFIED". I could not see the deployed environment or Search
  Console. **If the site is not yet open, every path change below costs nothing
  in search rankings.** That is the strongest reason to do this before opening,
  not after.
- **Indexed paths that would move,** and where each is listed:

  | Path | `indexing.yaml` `always` | `seo-build.js` `STRUCTURAL_PATHS` | `judge/seo.py` | `web/public/llms.txt` |
  |---|---|---|---|---|
  | `/reviews` | yes | yes | no | yes |
  | `/reviews/jobs`, `/reviews/capabilities` | yes | yes | no | yes |
  | `/reviews/jobs/<slug>`, `/reviews/capabilities/<slug>` | no | no | ~L152 (`section`) | no |
  | `/reviews/models/<id>` | no | no | ~L221 (`model`) | no |
  | `/tools` | yes | yes | no | no |
  | `/reviews/metrics[/<slug>]` | yes | yes | ~L152 | yes |

  `/reviews/metrics` is listed for completeness: it does **not** move in this
  proposal. `/evidence` is in none of these lists, so it can move with no
  search impact.
- **`contract/indexing.yaml` is a contract change.** Under CLAUDE.md, a change
  there is proposed and reviewed by a second person, never taken solo. Its
  `always` list and `seo-build.js` `STRUCTURAL_PATHS` are "kept in step" by
  hand, so both change together.
- **Redirects live in two places.** There are server 301s in
  `web/nginx.conf.template` (L35-43; the existing `/reports` → `/reviews` rule
  is the model to follow) and client redirects in `App.jsx` (`MovedTo`). Both
  must be added. A client redirect on its own is a 200 response to a crawler.
  The nginx `/reports(/.*)` rule already rewrites into `/reviews/...`, so after
  this change an old `/reports/jobs/x` link would redirect twice. Point it
  straight at the final address.
- **Canonicals and pre-rendering:** `web/src/seo/pages.js` (`reportsIndex`
  ~L345-362, `pickerJob` ~L241) and `web/prerender.js`, which renders every
  listed public page and **fails the build** if one does not render. A removed
  path left in a list breaks the build. That is noisy, but it is safe.
- **Not checked:** links inside approved blog posts stored in the database (a
  post can link to `/reviews/...`), and `seo/keyword_plan.yaml`, which maps
  keywords to pages. Both need a search before redirecting. The redirects keep
  old links working either way.

### Shared components and code

- `GET /reports` feeds four surfaces (Reviews, the picker, the model page, the
  home page's ModelsShowcase). Its payload does not need to change.
- `catalog/format.js` (`reportsPath`, `evidencePath`, `modelPagePath`) builds
  most cross-links. `components/FeedLink.jsx`, `components/Freshness.jsx` and
  `compare/path.js` are shared by the picker, Reviews, the model page and the
  feed.
- **Home page links to update:** Hero `CHIPS`, `ModelsShowcase` ("All reported
  models" → `/reviews/models`), `ToolsShowcase`, `ClosingCta` (`/tools`). Also
  the Nav "Models" mega menu, the footer `MODELS` and `TOOLS` columns, and
  `llms.txt`.
- The Reviews page's `phrase` rule and the picker's `phrase` decide the words
  ("Mostly working"). When the two pages become one, check that both use the
  same rule before deleting either.
- Tests that name these paths: `tests/test_seo_indexable_pages.py` and the
  other files that match `/reviews` or `/best-ai-model` under `tests/` (4 and 2
  files on 2026-11-02, by grep).

### Needs Parvathi's agreement (named in the pages' header comments)

| Surface | Her note | What this proposal touches |
|---|---|---|
| AI updates `/ai-news-headlines` and the home strip | `AiUpdates.jsx`, `UpdatesStrip.jsx` (2026-10-29/30) | Adds a link to `/ai-models/latest`. The label and path question is hers. |
| AI benchmarks `/ai-benchmarks`, Benchmarks `/benchmarks` | `BenchmarkCharts.jsx`, `Benchmarks.jsx`. The terms note in `gate.py` and `contract/benchmarks/sources.yaml` | Proposed to **stay separate**, with a link from the model page. Any later "how does it score" area with `/reviews/metrics` needs her decision. |
| Price changelog `/price-changes`, Updates `/updates` | `PriceChanges.jsx`, `Updates.jsx` | Out of the merge. No change proposed. |
| Signed-in `/models` | The price column was removed "at Parvathi's request" (`ModelDetail.jsx`). The route guard and login target are hers (2026-10-15). | Proposed retirement, and moving the login landing page. |
| Nav and footer order | "THE ORDER (2026-10-30, Parvathi)" in `Nav.jsx` and `Footer.jsx` | Removing `/tools`, `/reviews` and `/evidence` entries changes her menus. |
| Discussions | `Discussions.jsx` | Untouched. |

Git history also shows her as a main author of `Compare.jsx`, `Landing.jsx`,
`ModelPicker.jsx` and `Reports.jsx`, although their headers do not name her.
Lanes were dropped on 2026-08-28 ("tell each other after"), but changing
pages she built this much should be agreed first, not reported after.

---

## 5. Recommended order

1. **Check whether search engines can see the site** (`PUBLIC_SITE` on the
   deploy, and Search Console). This decides how careful the redirects must be,
   and it argues for finishing steps 3 to 5 before opening.
2. **Make the picker match Reviews**: one default threshold, the 2+ platforms
   filter and the 10 option. This is small, it removes a contradiction readers
   can see today, and the redirect in step 3 depends on it.
3. **Redirect `/reviews/jobs/*` to `/best-ai-model/*`.** This is the clearest
   duplicate (same payload, both indexed), the destination page already exists,
   and it removes one URL per job from `judge/seo.py`. It needs the
   `indexing.yaml` proposal.
4. **Model page: add the Reports section and the Evidence tab, then redirect
   `/reviews/models/*`, `/evidence/*`, `/reviews` and `/evidence`.** This is the
   biggest gain (up to three URLs per model become one page with tabs) and the
   biggest piece of work. Build first, redirect after.
5. **Capabilities:** add `/best-ai-model/capability/<slug>`, then redirect
   `/reviews/capabilities/*`.
6. **Small items:** `/tools` redirects to the picker with a "More tools" strip.
   Methodology becomes the one explanation of counting. Q1 gets its cross-link
   and a line on how P13 and P21's Launches differ.
7. **With Parvathi, separately:** retire signed-in `/models` and `/models/<id>`
   behind a signed-in Quotes section on the model page. Then decide whether
   `/reviews/metrics` and `/ai-benchmarks` become one "how does it score" area.
   Neither blocks steps 1 to 6.

Once 1 to 6 are done, the home page can lead with the three questions, one
door each, in place of four carousels. That is the "no hook" finding, and it is
a separate piece of work.
