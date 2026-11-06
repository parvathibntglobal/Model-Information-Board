# Kite Pulse

Everything for the Kite Pulse project lives in this folder. Kite Pulse is a
second product, and this repository only manages its **SEO website**: its
pages, keywords and AI-answer tracking. It shares nothing with the Model
Information Board's evidence pipeline.

The folder is inside `web/src/` rather than at the repository root because the
deployed frontend is built from `web/` alone (`web/Dockerfile` copies `web/`
and nothing else). Code outside `web/` would not reach the deployed site.

## What is here

| File | What it is |
|---|---|
| `site-preview/` | **The website preview** at `/kite-pulse`, everything only it uses (the next ten rows) |
| `site-preview/KitePulseSite.jsx` | The Kite Pulse website: header and menus, home page, section lists, every page, footer |
| `site-preview/HomeCharts.jsx` | The home page's charts, KPI tiles and screenshot slots (plain SVG, no chart library) |
| `site-preview/site.css` | The website's look, matching the prototype pages |
| `site-preview/prototypes/*.html` | Finished page designs, one file per page, copied from Claude artifacts |
| `site-preview/data/home-dashboard.json` | Every figure the home charts show, and which screenshot goes where. Placeholders while `"sample": true`, and every chart says "Sample data" until it is false |
| `site-preview/screens/` | Console screenshots for the home page, named in `home-dashboard.json` (create the folder with the first one) |
| `site-preview/data/claude-plans.json` | Claude plan and usage-limit facts, each with the exact sentence and source it came from. Checked by hand; re-check monthly |
| `site-preview/data/productivity-research.json` | Research figures on AI and developer productivity (METR, Copilot, Google, DORA), each with the exact sentence and source it came from. Checked by hand; re-check when METR publishes a new study |
| `site-preview/data/devex-frameworks.json` | SPACE, DevEx framework and DX Core 4: dimensions and example metrics, each with the exact wording and source. Checked by hand; re-check yearly, and whenever DX revises Core 4 |
| `admin/KitePulsePanel.jsx` | Admin → **Kite Pulse SEO**: Overview, Pages (with each page's brief and preview), Keywords, AEO tracking, Competitors, Settings |
| `admin/admin.css` | Styles for that admin panel |
| `shared/` | Used by both the preview and the admin panel (the next four rows) |
| `shared/site.js` | The site's sections, menus and footer, the proposed pages, which pages have a prototype, and loading the sheet |
| `shared/status.js` | Whether the Kite Pulse section is open (`KITE_PULSE_OPEN`) |
| `shared/data/sheet.json` | The keyword research sheet as JSON. **Generated, do not edit by hand** |
| `shared/import_sheet.py` | Regenerates `shared/data/sheet.json` from the sheet |
| `docs/Kite Pulse - Keyword Research.xlsx` | The keyword research sheet: keywords, Page Map, AEO questions, competitors. **The place people edit** |
| `docs/Kite Pulse Website Content — Master Source of Truth.md` | What Kite Pulse does, checked against the code on 28 Oct 2026. **Section 1 is the only source for product claims on the site**; Section 2 lists what must not be claimed yet |
| `docs/Kite Pulse — Product Guide.md` | The earlier product description (13 Oct 2026). Out of date where the Master Source of Truth's "Website corrections" says so; kept for its tone and structure, not its claims |
| `docs/MASTER-PROMPT.md` | The prompt that generates a page, and the page brief to fill in |
| `docs/ARCHITECTURE.md` | What is built, why, and the plan to a public site |
| `outreach/` | **Outward marketing**, its own module: finding the places people ask about problems Kite Pulse solves and answering them. Plan only so far; see `outreach/README.md` |

## Where it plugs into the app

Three files outside this folder point into it. Nothing else does.

- `web/src/App.jsx`: the `/kite-pulse/*` route, and hiding the board's own navigation on it
- `web/src/routes/Admin.jsx`: the **Projects** group in the admin sidebar
- `web/nginx.conf.template`: lets the deployed server answer `/kite-pulse`

## Common jobs

**The keyword sheet changed.** Save it over `docs/Kite Pulse - Keyword Research.xlsx`
in this folder, then run this from the repository root:

```
py -3.12 web/src/kitepulse/shared/import_sheet.py
```

**A prototype changed in Claude.** Save its HTML over the matching file in
`site-preview/prototypes/`.

**A new prototype page.** Save its HTML in `site-preview/prototypes/`, named after the page
URL (`/claude-code-usage-limits` becomes `claude-code-usage-limits.html`). Then
add one line to `PROTOTYPES` in `shared/site.js` with the page URL, file name and
artifact link.

**Real figures for the home page charts.** Replace the values in
`site-preview/data/home-dashboard.json` (keep its shape), say where they came
from in `source`, then set `sample` to `false`.

**A console screenshot.** Save it in `site-preview/screens/` (png, jpg or webp)
and put the file name in that screenshot's `file` in
`site-preview/data/home-dashboard.json`. A name with
no file behind it shows "File not found" on the page, not an empty slot.

**A proposed page was added to the sheet's Page Map.** Delete it from
`PROPOSED` in `shared/site.js`. Until you do, the sheet's entry wins anyway.

## Rules this folder keeps

- **Not public.** `/kite-pulse` needs sign-in and asks search engines not to
  index it. The pages must rank on Kite Pulse's own domain, and an indexed copy
  here would compete with them.
- **No invented product claims.** Wording about Kite Pulse on the site comes
  from Section 1 of `docs/Kite Pulse Website Content — Master Source of Truth.md`
  in this folder. Anything in its Section 2 stays off the site, or appears only
  as "coming soon". What is not built yet says so.
- **An empty sheet cell stays empty.** It is shown as a dash, never as 0.
