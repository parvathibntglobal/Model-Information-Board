# The web frontend

`web/` is a React + Vite app for this API. It adds nothing to `collect/` or
`judge/` — no backend file is modified by it, and the API runs exactly as it
did before.

**There is no mock data.** Every number on every page comes from this backend.
Where the API has nothing to say, the UI says that rather than rendering an
empty box.

---

## Running it

Two terminals. Backend first.

```bash
# 1 · API on :8000  — loads .env, which judge/app.py does not do for itself
pip install -e ".[dev]"
cp .env.example .env          # fill in DATABASE_URL at minimum
python run-backend.py --reload
```

```bash
# 2 · frontend on :5173
cd web
npm install
npm run dev
```

Open <http://localhost:5173>.

Vite proxies `/api/*` to `127.0.0.1:8000`, so there is no CORS to configure.
Point it somewhere else with `BACKEND_URL=http://host:port npm run dev`, or set
`VITE_API_URL` for a deployed build.

### Sign-in

```
demo@modelboard.dev
mb-Evidence-8842
```

`web/src/auth.js` is a **demo gate, not authentication** — an unsalted SHA-256
hash checked in the browser, readable in the bundle and skippable from the
console. It exists so routing and guards are already wired. The file says so at
the top and names what should replace it.

### Reading the shared staging board

```bash
python run-backend.py --staging
```

Requires `STAGING_DATABASE_URL` in `.env`. Every session is forced read-only at
the server, so nothing in the process can write to it.

---

## What each page reads

| route | endpoint | needs a database |
|---|---|---|
| `/` | — | no |
| `/ask` | `POST /ask/requirements`, `POST /ask/revise` | no |
| `/board` | `GET /capabilities`, `GET /capabilities/{key}` | for the detail |
| `/models` | `GET /capabilities/{key}` × 12 | yes |
| `/models/*` | `GET /models/{id}` | yes |
| `/admin` | `GET /health` `/coverage` `/filtered` `/changelog` | for all but health |

`/ask` and the capability list work with no database at all, which is why they
are the pages that work first on a fresh clone.

### Why `/models` calls a capability endpoint

There is no `GET /models`. A capability page is explicit that it lists *every*
model in the registry and not only the evidenced ones, so it doubles as the
roster. The first call fills the list; the other eleven capabilities load in the
background and fold in per-model evidence counts.

A `GET /models` returning `{id, display_name}` would let it list models
directly, if that is ever worth adding.

---

## Three rules from the handoff, and where they are enforced

| rule | where |
|---|---|
| A 503 is not an empty page | `BoardUnreadable` in `web/src/api/index.js`; `<Unreadable>` gives it its own treatment |
| `unreported` / `insufficient` / `published` must look different | `STATE` in `routes/ModelDetail.jsx` — three distinct badges, plus one for `needs_positive_consensus` |
| A phrase with no quotes must not appear | `ModelDetail.jsx` filters out every capability named in `unbound_phrases` and shows the list instead |
| A quote with no permalink must not appear | `Quote()` renders "withheld — no source link" rather than an unattributed quote |
| No invented ranking | Nothing is sorted by implied quality. Board groups by failure mode; capability pages keep API order |

Every `summary` and `headline` the API returns is rendered verbatim. The
frontend computes no scores, no rankings and no costs.

---

## Known backend issues the frontend works around

Found while wiring this up. None are frontend bugs and all four are worth fixing
at the source.

**1 · `/models/{vendor}/{name}` 404s.** `judge/app.py` declares
`@app.get("/models/{model_version_id}")` — a single path param, which does not
match a slash, and Starlette does not decode `%2F` into one.

```
GET /models/google/gemini-2.5-flash      → 404
GET /models/google%2Fgemini-2.5-flash    → 404
GET /models/mv_cd62f9d5ea30935d          → 200
```

Fix: `{model_version_id:path}`. `modelPath()` in the frontend already builds the
path correctly for when it is.

**2 · Double-encoded em dashes.** Several literals arrive as `â€”` — the source
was written UTF-8 and re-saved as cp1252.

```bash
curl -s -X POST localhost:8000/ask/requirements -H 'Content-Type: application/json' \
  -d '{"task":"summarise tickets"}' | grep -o 'â€”'
```

`routes/Ask.jsx` repairs it on display. **Delete `mend()` once the source is fixed.**

**3 · `requests_per_month` is accepted and discarded.** `AskRequest` declares it
with a docstring calling it load-bearing, then never passes it to
`requirements.infer()`. The input was removed from the form rather than ship a
control that changes nothing.

**4 · No trigger for "coding" or "programming".** Q3 matches verbs, so the most
natural phrasing of a coding task raises zero capabilities:

```
"a good model for coding"      → 0 capabilities
"write code from a spec"       → 1  code.generation
"refactor this file"           → 1  code.editing_diff_fidelity
```

The UI explains this rather than showing an empty box, but the trigger list is
where it belongs.
