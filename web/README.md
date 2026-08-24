# ModelBoard — frontend

React + Vite, wired to the real FastAPI backend in `../backend`. There is no
mock data — every number on every page comes over the wire.

Start the backend first, then `npm run dev`. Full instructions in
[../RUNNING.md](../RUNNING.md).

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # -> dist/
npm run preview
```

## Routes

| Route | What it is |
|---|---|
| `/` | Landing — WebGL fluid hero, the four principles, the problem framing |
| `/ask` | **The prompt view.** Describe a task, get ranked models per sub-agent role |
| `/board` | The twelve-key capability vocabulary, and what is reported per capability |
| `/models/:id` | One model — every capability, its condition slices, and the quotes behind them |
| `/admin` | Service health, coverage, the filtered queue, and the changelog |

`/ask` accepts `?q=` and runs itself, so an answer can be linked or bookmarked.

## Layout

```
src/
  api/
    index.js       every endpoint, in one module. the only thing components import
  components/
    FluidCanvas    WebGL metaball hero, no dependencies
    Nav Footer Icons ui
  routes/          Landing Ask Board ModelDetail Admin
  styles/
    tokens.css     colour, type, spacing, radius — single source of truth
    app.css        everything else
```

**Components import from `src/api/index.js` and nowhere else.** Base URL is
`/api`, proxied to the backend in dev by `vite.config.js`; set `VITE_API_URL`
for a deployed build.

`BoardUnreadable` is a distinct error type for a 503 from a read surface. The
backend is explicit that "the board cannot be read" is not the same as "the
board has nothing on it", and the UI keeps that distinction — collapsing the
two would be the exact mistake the product exists to avoid.

## Design system

From the Unified Architecture spec: `#0C0C0E` ground, `#18181B` surface, `#27272A`
border, white accent, 11px radius, 8px spacing base. Inter for text, JetBrains Mono
for labels and data — both self-hosted via `@fontsource`, no CDN.

Semantic colour (pass / warn / fail) is kept separate from the accent so state reads
at a glance without competing with the brand.

## The hero

`FluidCanvas` is a metaball field in a single fragment shader — seven implicit
spheres on lissajous paths, summed and thresholded, with the pointer owning one of
them. It composites with `mix-blend-mode: difference`, which is what makes the mass
invert the headline instead of covering it.

It degrades safely: no WebGL means no canvas and the hero still reads; `prefers-reduced-motion`
freezes the field at a fixed pose; and it stops drawing entirely when scrolled out of view.

## Notes for the backend team

- The UI renders your summaries, phrases and headlines **verbatim**. It computes
  no scores, no rankings and no costs.
- `null` renders as `—`. Send `null` rather than `0` for unknowns.
- A `GET /models` list endpoint would let Board enumerate the registry; right
  now there is only `GET /models/{id}`, so it is organised by capability.
- Ask shows the requirement profile and states that candidates are not built
  yet, rather than inventing any.
