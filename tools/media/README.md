# Media for the content workspace

The generators for the three approved looks (anooj, 2026-11-19), each a Node script that
renders a JSON spec into a 3-page carousel (1080×1350: one PNG per page, plus a PDF):

| Look | Generator | Suits |
|---|---|---|
| Field report | `field-report/make_field_report.mjs` | a model's first weeks, what held up and what broke |
| Data card | `data-card/make_data_card.mjs` | a number that carries the story, across models |
| Evidence board | `evidence-board/make_evidence_board.mjs` | reports weighed against each other, with a price history |

Each folder has its design brief (`PHILOSOPHY.md`), its spec (`SPEC.md`) and a SYNTHETIC
example spec (`examples/example.json`). Which topic kind uses which look, on which
platform, is in `judge/content_workspace/config/workspace.yaml` (`looks`, `topic_recipes`).

## Where this runs

On a person's machine, from Claude Code or a terminal. It needs Node and a Chromium
build (`CHROME`). **Never on Railway or in CI**: nothing here is part of the site, and
CI does not install Chromium (the tests check specs, the looks' wiring and the fonts,
not pixels).

## Making media for a draft

1. **Install once:** `cd tools/media && npm install` (playwright-core only, pinned).
   Point `CHROME` at a Chromium or Chrome executable (for example, the one Playwright
   installs under `%LOCALAPPDATA%/ms-playwright`).
2. **Write the spec from the board** (read-only; it needs `DATABASE_URL`):
   ```
   python -m judge.content_workspace media-spec field-report   --model <id> --out spec.json
   python -m judge.content_workspace media-spec data-card      --capability <slug> --text text.json --out spec.json
   python -m judge.content_workspace media-spec evidence-board --model <id> --out spec.json
   ```
   Every limit the generator enforces is refused here first, with the reason. A
   person's words (a data card's headline and notes) come from `--text`; there is no
   default text.
3. **Render:** `CHROME=<chrome.exe> node tools/media/<look>/make_*.mjs spec.json <outdir>`.
   The layout guard refuses the render if anything leaves the page or overlaps, and
   writes nothing.
4. **Look at every page.** The checks cover the numbers and the layout, not whether the
   picture says only what the board says, or whether a restated report is faithful.
5. **Store it on the draft:**
   ```
   python -m judge.content_workspace media-add <draft> <outdir>/<file>.pdf --kind carousel_pdf \
       --made-with "tools/media/<look> <spec file>" --development-write
   ```
   (`--development-write` only when writing from a development machine to the shared
   database; see the workspace's write guard.) The page shows it in the draft's Media
   panel, behind the login.

## Rules the generators keep

- Every figure is a count with its denominator and its read date; there is no score.
- Silence is said in words ("nobody posted about it this week"), never drawn as a 0.
- A platform the publication contract withholds is never given its own number: the data
  card groups those people as "Not named".
- Card text is the evidence feed's stored paraphrase, "restated by the board", never a
  post's words, never a link or a handle. Whether such cards may appear on outward media
  is the #558 decision.

## Fonts

`fonts/` holds only the files the generators load, each family with its SIL Open Font
License 1.1 file (`<Family>-OFL.txt`), which permits bundling them here. A test checks
every font a generator loads is present with its licence.

## Re-checking an approved look

`compare_pages.py <approved_dir> <new_dir> <prefix> <pages>` compares two renders pixel
for pixel. After any change to a generator, render a known spec before and after and
compare; an approved look changes only on purpose.
