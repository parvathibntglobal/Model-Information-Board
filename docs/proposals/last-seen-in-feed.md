# `model_version.last_seen_in_feed` — an observation, not a claim

**For Engineer 2. A timestamp is something we did; a `lifecycle` value is
something a vendor said, and `lifecycle` is a column of vendor facts. A model can
leave OpenRouter and remain generally available, and only one of those is
something we know.**

**This does not replace a lifecycle ruling. It is what tells you which models to
apply one to.** Without it, `_upsert_model` still only sees rows the feed
returned.

*Engineer 1 · 2026-08-20 · supersedes the `lifecycle` value I proposed in
`departed-from-feed-lifecycle.md` · `contract/` unchanged by this document*

---

## 1 · I proposed the wrong shape and this is the correction

`departed-from-feed-lifecycle.md` proposed `lifecycle = 'absent-from-feed'`. That
is wrong for a reason worth keeping rather than deleting: **`lifecycle` carries
what the provider says about a model** — `ga`, `preview`, `deprecated`,
`retired` — and every other value in it is sourced to a provider page.
`'absent-from-feed'` would be the one value in that column sourced to *our
plumbing*, and it would be indistinguishable in a query from the vendor's own
words.

Worse, it would collapse the distinction it was invented to preserve. A model
missing from OpenRouter may be:

| | established by | what we can say |
|---|---|---|
| delisted from this aggregator | a poll that does not return it | **this, and only this** |
| retired by the vendor | an announcement, or `expiration_date` | nothing yet |
| still generally available elsewhere | a provider API we do not poll | nothing yet |

**Absence from one feed proves the first and nothing else.** A timestamp says
exactly that and no more.

```sql
-- The last poll that returned this id. NULL means never observed in a poll:
-- a row that arrived from the seed loader rather than from the feed.
last_seen_in_feed  timestamptz
```

## 2 · What it means, and what it does not

**Means:** at this instant, the feed returned this id. Nothing else in the row is
fresher than this.

**Does not mean, and each is a reading somebody will take:**

- **Not that the model is gone.** It is the last time *we looked and found it*.
  Our failure to see something is not its absence.
- **Not a retirement.** `retirement_date` is the column for that, sourced to a
  vendor. 4 rows carry one today; these two do not.
- **Not a reason to drop claims.** FR-4 resolves a mention to what existed when
  it was written, and every claim stays exactly as valid.
- **Not derivable from `updated_at`.** That moves on any write — a price change,
  a re-poll, a backfill — so it answers "when did we last touch this row", which
  is a different question and currently the only one available.

**Why it does not need a nullable-vs-sentinel argument:** NULL is honest and
means *never seen in a poll*, which is a real state — `load_seed` writes rows the
feed has never returned. Rule 6 costs nothing here.

## 3 · The composition argument, which is the point

**This is not an alternative to a lifecycle ruling. It is its input.**

```
last_seen_in_feed  →  "which models did the last poll not return?"     an OBSERVATION
lifecycle ruling   →  "and what should the board do about those?"      a DECISION
```

Today you cannot ask the first question at all, so the second has no subject. The
poller's own structure is why: **`_upsert_model` and `write_model_versions` build
their statement from `result.models` — this poll's models — so a row absent from
the poll is not in the statement.** No UPDATE, no DELETE, no event. There is no
code path in which the poller learns that something stopped appearing.

So without this column, a lifecycle ruling has nothing to fire on: whatever you
decide `'absent-from-feed'` or `'unknown'` should mean, **nothing can set it**,
because nothing detects the condition. That is the composition — the timestamp
makes the set computable, and the ruling decides what happens to the set.

And the query is then trivial and needs no new vocabulary:

```sql
SELECT canonical_id, last_seen_in_feed
FROM   model_version
WHERE  last_seen_in_feed < (SELECT max(last_seen_in_feed) FROM model_version)
```

Two rows today: `ai21/jamba-large-1.7` and `mancer/weaver`.

## 4 · The state those two are in right now

Staging, re-polled 2026-08-20, **342 registry rows against a 340-model feed**:

| | lifecycle | retirement_date | in_window | updated_at |
|---|---|---|---|---|
| `ai21/jamba-large-1.7` | NULL | NULL | **True** | 2026-08-17 |
| `mancer/weaver` | NULL | NULL | False | 2026-08-18 |

**Every column your filters read still says current.** `lifecycle` is NULL on all
342 rows — the feed does not carry it, and `PolledModel.UNAVAILABLE` names it as
one of four fields never set from the feed — so `lifecycle != 'retired'` matches
both. `jamba-large-1.7` is in window. The only thing keeping `mancer/weaver` out
of an answer is a 2023 release date: the calendar, not a ruling.

**They are already in the state this proposal describes**, so nothing was blocked
on it and marking them afterwards loses nothing.

## 5 · What is yours

1. **What the answer path does with a stale `last_seen_in_feed`.** My view is
   penalise and flag, the same treatment as `deprecating:{date}` — excluding
   silently is the rule-4 failure, and ignoring it recommends a model we can no
   longer price. But the filter is yours and the column is useless until it has a
   consumer.
2. **Whether a published cell carries a caveat.** A cell about a model we can no
   longer see is still true about the past; whether the page says so is your
   surface.
3. **Whether the threshold is "not the latest poll" or "not for N polls".** One
   missed poll may be a delisting that lasts a night. `max(last_seen_in_feed)` is
   the cheap version and a poll counter is the durable one.

## 6 · What is mine, and it is small

Set the column in `write_model_versions` — one more value in a statement that
already writes twenty. It is not a second writer and not a second pass: the rows
being upserted *are* the rows the feed returned, so `now()` on every one of them
is the whole implementation.

**Sequencing:** the column has to exist before the poller can set it, and a poll
that runs before the migration leaves `NULL` on rows it did see — which reads as
*never observed* rather than *observed before the column existed*. So the
backfill is `UPDATE model_version SET last_seen_in_feed = updated_at WHERE
last_seen_in_feed IS NULL` in the same migration, with the caveat that
`updated_at` is an upper bound on the last sighting rather than the sighting
itself. Stated because it is the one place this column starts life slightly wrong
and cannot be made right retrospectively.

## 7 · The shape underneath, worth knowing beyond this column

**A writer whose verdict ranges over an input collection cannot notice a row that
is in the table and absent from the input.** Nothing is wrong with
`_upsert_model`; the absence is simply not in its domain.

Same shape as `ExtractionLedger.should_skip` keying on the thread fingerprint
while the registry moved — **the thing that changed was not among the inputs.**
Swept `collect/` for it: `load_source_rows` has the identical unhandled gap one
table over, `load_capabilities` handles it (`absent_from_contract`), `_sync_alias`
handles it within a model but not across, and `recompute_window` does not have it
at all because it is `UPDATE … FROM (SELECT id …)` over the **whole table**. That
last one is the cheap structural fix wherever the semantics allow it: operate over
the table rather than over the input. Full audit in
`departed-from-feed-lifecycle.md` §4.
