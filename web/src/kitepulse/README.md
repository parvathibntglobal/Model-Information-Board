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
| `KitePulseSite.jsx` | The Kite Pulse website, previewed at `/kite-pulse`: header and menus, home page, section lists, every page, footer |
| `site.css` | The website's look, matching the prototype pages |
| `KitePulsePanel.jsx` | Admin → **Kite Pulse SEO**: Overview, Pages (with each page's brief and preview), Keywords, AEO tracking, Competitors, Settings |
| `admin.css` | Styles for that admin panel |
| `site.js` | Shared by both: the site's sections, menus and footer, the proposed pages, which pages have a prototype, and loading the sheet |
| `data/sheet.json` | The keyword research sheet as JSON. **Generated, do not edit by hand** |
| `data/claude-plans.json` | Claude plan and usage-limit facts, each with the exact sentence and source it came from. Checked by hand; re-check monthly |
| `data/productivity-research.json` | Research figures on AI and developer productivity (METR, Copilot, Google, DORA), each with the exact sentence and source it came from. Checked by hand; re-check when METR publishes a new study |
| `data/devex-frameworks.json` | SPACE, DevEx framework and DX Core 4: dimensions and example metrics, each with the exact wording and source. Checked by hand; re-check yearly, and whenever DX revises Core 4 |
| `import_sheet.py` | Regenerates `data/sheet.json` from the sheet |
| `prototypes/*.html` | Finished page designs, one file per page, copied from Claude artifacts |
| `docs/Kite Pulse - Keyword Research.xlsx` | The keyword research sheet: keywords, Page Map, AEO questions, competitors. **The place people edit** |
| `docs/Kite Pulse — Product Guide.md` | What Kite Pulse is and does. The only source for product wording on the site |
| `docs/MASTER-PROMPT.md` | The prompt that generates a page, and the page brief to fill in |
| `docs/ARCHITECTURE.md` | What is built, why, and the plan to a public site |

## Where it plugs into the app

Three files outside this folder point into it. Nothing else does.

- `web/src/App.jsx`: the `/kite-pulse/*` route, and hiding the board's own navigation on it
- `web/src/routes/Admin.jsx`: the **Projects** group in the admin sidebar
- `web/nginx.conf.template`: lets the deployed server answer `/kite-pulse`

## Common jobs

**The keyword sheet changed.** Save it over `docs/Kite Pulse - Keyword Research.xlsx`
in this folder, then run this from the repository root:

```
py -3.12 web/src/kitepulse/import_sheet.py
```

**A prototype changed in Claude.** Save its HTML over the matching file in
`prototypes/`.

**A new prototype page.** Save its HTML in `prototypes/`, named after the page
URL (`/claude-code-usage-limits` becomes `claude-code-usage-limits.html`). Then
add one line to `PROTOTYPES` in `site.js` with the page URL, file name and
artifact link.

**A proposed page was added to the sheet's Page Map.** Delete it from
`PROPOSED` in `site.js`. Until you do, the sheet's entry wins anyway.

## Rules this folder keeps

- **Not public.** `/kite-pulse` needs sign-in and asks search engines not to
  index it. The pages must rank on Kite Pulse's own domain, and an indexed copy
  here would compete with them.
- **No invented product claims.** Wording about Kite Pulse on the site comes
  from `docs/Kite Pulse — Product Guide.md` in this folder, word for word. What is not built
  yet says so.
- **An empty sheet cell stays empty.** It is shown as a dash, never as 0.
