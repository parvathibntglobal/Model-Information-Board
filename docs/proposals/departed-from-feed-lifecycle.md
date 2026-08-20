# `lifecycle` for a model that left the feed — a value to rule on, not to pick

**Proposed, not chosen. `lifecycle` is the column and the value is a contract
question, because the answer path filters on `lifecycle != 'retired'` and a
departed model is not retired — it is unknown. Three facts get confused into
one, and OpenRouter's absence proves only the first.**

*Engineer 1 · 2026-08-20 · `contract/` unchanged by this document*

---

## 1 · The state today, measured rather than described

Staging, re-polled 2026-08-20: **342 registry rows against a 340-model feed.**
Two models are in the registry and not in the feed:

| | lifecycle | retirement_date | deprecation_date | in_window | updated_at |
|---|---|---|---|---|---|
| `ai21/jamba-large-1.7` | NULL | NULL | NULL | **True** | 2026-08-17 |
| `mancer/weaver` | NULL | NULL | NULL | False | 2026-08-18 |

`lifecycle` is NULL on **all 342 rows** — the feed does not carry it and
`PolledModel.UNAVAILABLE` names it as one of four fields never set from the feed.

### What the poll does to them today

**Nothing. It does not touch them at all**, and that is the precise problem
rather than a figure of speech:

- **No row is written.** `write_model_versions` builds `params` from
  `result.models` — this poll's models — so a departed row is not in the
  statement. No UPDATE, no DELETE, no event.
- **`updated_at` therefore stays at its last-seen value**, which is the one
  usable signal: a row whose `updated_at` predates the last poll is a row that
  poll did not see.
- **Every column the answer path reads still says "current".** `lifecycle` is
  NULL so `lifecycle != 'retired'` matches. `in_window` is True for
  `jamba-large-1.7`. `retirement_date` is NULL so nothing renders a sunset date.

So the poll leaves them **looking current in every column that decides
eligibility**, and the only thing keeping `mancer/weaver` out of an answer is its
2023 release date — the calendar, not a ruling.

## 2 · Three facts, and absence proves one

| fact | what establishes it | what it means for a recommendation |
|---|---|---|
| **gone from our feed** | a poll that does not return it | we cannot price it, cannot check its flags, cannot see it change |
| **retired by the vendor** | a provider announcement, or `expiration_date` in the feed | it is over. FR-4 still has to resolve old quotes about it |
| **reachable elsewhere** | a direct provider API, or another aggregator | it works fine and our single source dropped it |

**OpenRouter's absence establishes only the first**, and the first is a fact
about *us*. A model can leave the feed because it was delisted, region-gated,
renamed, temporarily broken, or moved behind a different id — and every one of
those is indistinguishable from retirement at our end.

**A retired model is exactly what FR-4 resolves.** A March post about a model
retired in June must still resolve to it, so "retired" cannot mean "remove", and
`contract/seed_models.yaml` already keeps three retired models deliberately for
this reason. The answer path's job is to *penalise and flag*, not to forget —
`docs/logic-and-workflow.md`: *"Sunset date shown; model penalised, not
removed."*

## 3 · The proposed value, with what it does not mean

```
lifecycle: 'absent-from-feed'
```

**What it means.** The last poll did not return this id. As of that poll we
cannot read its price, its flags or its context window, and we will not see it
change.

**What it does not mean, and each of these is a claim somebody will read into
it:**

- **Not retired.** No vendor said anything. `'retired'` is a statement about the
  model; this is a statement about our source.
- **Not unavailable.** It may serve fine on a provider API we do not poll.
- **Not a reason to drop existing claims.** FR-4 resolves a mention to what
  existed when it was written, and every claim about it stays exactly as valid as
  it was.
- **Not permanent.** A model that reappears in a later poll goes back to NULL by
  the ordinary upsert, with no special path — which is a property worth having,
  because a delisting that lasts one night should cost nothing.

**Why a new value rather than `'retired'`.** Reusing `'retired'` would make the
answer path's existing `lifecycle != 'retired'` filter silently exclude these
models — which is the *right* behaviour by accident and a **wrong statement** on
the record, and rule 6 is about exactly that conversion. It would also destroy
the distinction the moment a vendor genuinely retires something: two facts, one
value, no way back.

**Why not NULL-plus-`updated_at`.** That is what we have, and it means every
reader has to know to compare `updated_at` against the last poll. A fact that
requires a join to a schedule is a fact nobody checks.

### The two questions that are Engineer 2's as much as mine

1. **Does the answer path exclude, penalise, or ignore `absent-from-feed`?** My
   view is *penalise and flag* — the same treatment as `deprecating:{date}` —
   because excluding it silently is the failure mode and ignoring it recommends a
   model we cannot price. But the filter is hers, and the value is useless until
   she decides what it does.
2. **Does a cell built on it carry a caveat?** A published cell about a model we
   can no longer see is still true about the past. Whether the page says so is a
   rule-4 question on her surface.

### And a coverage kind, which is the honest home for the count

The *number* of departed models is a fact about our source's coverage, not about
any model — so it belongs beside `undeclared-model`
(`docs/proposals/coverage-page-scope.md`) rather than only in a column:

```
"absent-from-feed": (
    "a model in the registry that the last poll did not return",
    "either the feed returned everything we hold, or nothing compared them",
),
```

The second half matters here more than usual: **0 departed models and "nobody
compared the registry to the feed" are the same output today**, and only one is a
finding.

## 4 · Why nothing caught it, and what else has the property

**`_upsert_model` and `write_model_versions` only see rows the feed returned.** A
writer whose verdict ranges over an input collection cannot notice a row that is
in the table and absent from the input. There is nothing wrong with either
function; the absence is simply not in their domain.

Same shape as `ExtractionLedger.should_skip` keying on the thread fingerprint
while the registry moved: **the thing that changed was not among the inputs.**

### The audit, since it was worth asking

Swept every write-issuing function in `collect/` for the property — *can a row
exist in the table that this writer's input does not mention, and does anything
notice?* The sweep's own heuristic produced **two false positives of four**
(matching the words `existing` and `SELECT * FROM` rather than a reconciliation),
which is habit 11 in the tool written to check for it, so each was read by hand.

| writer | has the property | notices |
|---|---|---|
| `write_model_versions` / `_upsert_model` | **yes** — input is this poll's models | **no.** The instance |
| `load_source_rows` | **yes** — input is the contract's 12 rows | **no.** It reads `SELECT * FROM source WHERE id = %s` per input row and `SELECT … WHERE id = ANY(%s)` for provenance. Nothing enumerates table rows absent from the contract, so a `source` row whose contract entry was deleted stays, unmentioned |
| `load_capabilities` | **yes** — input is the contract's 12 keys | **yes.** `absent_from_contract` enumerates table keys the contract no longer declares, names them, and deliberately does not deactivate them |
| `_sync_alias` | **yes** — input is one model's alias rows | **partly.** It closes superseded rows with `valid_until` *within a model*. Across models — an alias for a model no longer in the seed file — nothing looks |
| `write_documents`, `write_authors` | yes, structurally | **not applicable.** Upstream deletion is NFR-6's tombstone path, which is deletion-driven rather than absence-driven — a different mechanism, deliberately |
| `mark_swept` | yes | by design: marking a named subset is its whole job |
| `recompute_window` | **no** | the one contrast worth having. It is `UPDATE model_version … FROM (SELECT id … )` over the **whole table**, so every row is in its domain and an absence is impossible |

**Two findings from that.** `load_source_rows` has the same unhandled gap as the
poller, one table over, and nobody has looked — a feed removed from
`contract/sources.yaml` would keep its `source` row and keep passing the terms
gate on a stale ruling. And **the only writer that handles it is the one written
today**, which is suggestive rather than reassuring: the property is invisible
unless you go looking, and `recompute_window` shows the cheap structural fix —
**operate over the table rather than over the input** where the semantics allow
it.

## 5 · What would revise this

- **A second registry source.** The whole distinction collapses if absence from
  one feed can be checked against another; `'absent-from-feed'` becomes
  `'absent-from-all-sources'` and means much more.
- **`expiration_date` appearing in the feed for one of these.** That converts a
  guess about our source into a vendor statement, and `retirement_date` already
  has a column for it — 4 rows carry one today.
- **A reappearance.** If `jamba-large-1.7` returns in the next poll, the value was
  right to be temporary and the count was right not to be a deletion.
