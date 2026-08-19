# Frontend handoff — the Model Information Board API

Everything needed to build against this backend. Written 2026-08-19 by
Engineer 2, who owns `judge/` and every endpoint below.

**You do not need, and should never be sent, the `.env` file.** It holds six
live credentials — a production database URL, an OpenRouter key that spends
money, and four platform tokens. Nothing in this document requires any of them.

---

## 1 · What this product claims, in one paragraph

It reports what engineers publicly say about AI models, with the verbatim quote
attached, and recommends cheaper models for specific tasks. **Its entire value
is that it distinguishes "nobody has looked at this" from "nobody has
complained about this".** Those are opposite states and most dashboards render
them identically — as nothing.

That distinction is why several things below are non-negotiable rather than
stylistic. If the UI collapses it, the product is a worse version of a thing
that already exists.

---

## 2 · Running it

```bash
pip install -e ".[dev]"

# Point at YOUR OWN local Postgres. Never the one in .env.
export DATABASE_URL="postgresql://user@localhost:5432/your_db"
psql "$DATABASE_URL" -f contract/tables.sql     # creates 30 tables

uvicorn judge.app:app --reload
```

Then **`http://localhost:8000/docs`** — live OpenAPI, generated from the code.
That is the authoritative contract. This document explains *why*; `/docs`
tells you *what*, and it cannot go stale.

**With no `DATABASE_URL` every page returns `503`**, deliberately, with a
message saying so. That is not a bug and not an empty state — a board that
cannot be read is different from a board with nothing on it, and the API
refuses to blur them. **Do not render a 503 as an empty page.**

---

## 3 · The endpoints

| method | path | what it is |
|---|---|---|
| `GET` | `/health` | liveness |
| `GET` | `/capabilities` | the 12 tracked capabilities |
| `GET` | `/models/{vendor}/{name}` | one model, every capability |
| `GET` | `/capabilities/{key}` | one capability, every model |
| `GET` | `/filtered` | documents we discarded, and the rule that discarded them |
| `GET` | `/coverage` | what the board does not know |
| `GET` | `/changelog?days=30` | labels gained and lost, and why |
| `POST` | `/ask/understand` | free text → structured profile **(calls a model)** |
| `POST` | `/ask/requirements` | task → requirement profile (deterministic) |
| `POST` | `/ask/revise` | re-run after the user edits an assumption |

**Model ids contain a slash** — `google/gemini-2.5-flash`. The route accepts
it: `/models/google/gemini-2.5-flash`. Do not URL-encode the slash; the server
decodes before routing and `%2F` becomes a slash again.

---

## 4 · Three rules the UI must not break

### 4.1 The caveat travels with the finding. Never render one without the other.

Every response carries its own qualification in the **same object**. This is
not API tidiness — a client that renders `capabilities` and drops `headline`
has deleted the product's central claim.

Each capability comes back in one of three states:

| `state` | means | must look like |
|---|---|---|
| `unreported` | nobody has said anything | **visibly different from a pass** |
| `insufficient` | somebody has, not enough to publish | not a failure either |
| `published` | there is a finding | the only one that is a verdict |

And `needs_positive_consensus: true` marks a capability that **fails silently**.
For those, an absence of complaints is not reassurance — a failure produces no
error for anyone to report. The `headline` already says this in words; render
it.

### 4.2 A phrase without its quotes must not appear

`quote_ids` sit beside the phrase they support, inside the same `conditions`
entry. A rendered claim with no way to check it is exactly what this product
exists not to produce.

The model response also carries **`unbound_phrases`**. If it is non-empty,
those capabilities have a published phrase with no evidence behind it —
**refuse to render them** and show the list. That is a backend defect
surfacing, and hiding it makes it permanent.

### 4.3 There is no ranking. Do not invent one.

Cells carry counts and a status, never a score. There is no 0–100 anywhere in
the schema, on purpose. **Sorting models by "best" in the UI would put a
synthesised number on a page**, which every layer below refuses to do.

Sort alphabetically, or by a figure the API actually returns (`voices`,
`platforms`). Grouping by `state` is fine — that is presentation. Ordering by
implied quality is not.

---

## 5 · What you will see today: nothing, honestly

The board has no evidence yet. The extractor works — verified against a live
model — but the registry does not yet carry the aliases needed to find
mentions, so no cell has been published.

**This is the state to design first.** It is the hardest screen in the product
and the one most likely to be wrong, and it will be the real state for weeks.

Real responses, right now:

```jsonc
// GET /coverage
{
  "summary": "No coverage measurement has ever run. Nothing below is a finding
              about the board's coverage - it is the absence of any check, and
              it must not be read as completeness.",
  "measured_at_all": false,
  "kinds": [{ "kind": "mention-resolves-to-route", "measured": false,
              "headline": "not measured - either nobody names routers, or
                           nothing is counting when they do", "rows": 0 }]
}
```

```jsonc
// GET /models/google/gemini-2.5-flash
{
  "model_version_id": "google/gemini-2.5-flash",
  "summary": "0 of 12 tracked capabilities have any reports at all. 4 of the 12
              unreported fail silently, where an absence of complaints is not
              evidence of safety.",
  "capabilities": [{ "key": "code.editing_diff_fidelity",
                     "state": "unreported",
                     "headline": "Nobody has reported on this.",
                     "needs_positive_consensus": false,
                     "conditions": [] }],
  "quotes": {},
  "unbound_phrases": []
}
```

Note what the summaries do: they say *what is missing and why*, in a sentence a
person can act on. **Render the `summary` field.** It is not filler — it is the
part that stops an empty page reading as a clean bill of health.

---

## 6 · The Ask box

`POST /ask/understand` is the one endpoint that calls a language model. It
turns free text into a structured profile.

**Every field the user did not state comes back in `assumptions`, each with a
`why`.** That is the entire safety mechanism: the model proposes, the user
confirms. There is no verification behind it the way there is for quotes, so
**an assumption the user cannot see is a guess acting silently.**

Render every assumption as an **editable field**. `POST /ask/revise` re-runs
the deterministic half after an edit — and calls no model, so a correction can
never be overruled by one.

`caveat` is `null` when the user stated everything. Show it when it is not.

Status codes: `422` the request was declined with a reason, `400` the text
forged an internal marker, `429` the daily spend cap bound.

---

## 7 · What is not built

- **No authentication.** Do not deploy this publicly as-is.
- **No pagination.** `/filtered` takes `?limit=` and tells you when it
  truncated, via `truncated` and `total_filtered`. Nothing else paginates.
- **No websockets, no streaming.** The evidence pipeline is a nightly batch.
- **Quotes may be missing a link.** Published content is *quote + attribution +
  link*; some documents currently lack a URL. If a quote has no permalink,
  **do not render it** rather than rendering an unattributed quote.

---

## 8 · Questions

Endpoint shapes: `/docs`. Anything about *why* a field exists: ask Engineer 2 —
most of the odd-looking decisions above are load-bearing and the reasons are in
`judge/CLAUDE.md`.
