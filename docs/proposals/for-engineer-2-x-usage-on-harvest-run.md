# X usage: the tab exists, the record does not

**2026-09-08, anooj.** #226 landed the RapidAPI X tab. This is the half under
it: **nothing the X path does is recorded anywhere**, so that tab shows a
Reddit reading with an X label. Proposal, not a change — it needs
`contract/` columns and a `judge/` endpoint, and you have just touched both.

---

## 1 · What #226 gets right, and what it cannot know

`UsagePanel.jsx` is honest about the shared key in its own words: *"One RapidAPI
key meters both the X and Reddit harvest paths — the Reddit and X tabs show
that one shared request quota."* And it passes the same object to both tabs:

```jsx
<RapidApiTab rapid={rapid} which={tab === 'rapidapi_x' ? 'X' : 'Reddit'} />
```

So the two tabs differ by a label. That is not a frontend defect — it is the
only thing the backend can currently support, and here is why.

**`_rapidapi_quota()` reads `var/rapidapi-quota.json`**, and its own docstring
says that file is *"written by a Reddit fetch from RapidAPI's `x-ratelimit-*`
headers"*. The X adapter captures the same three headers — `_QUOTA_HEADERS` in
`collect/adapters/x.py` is deliberately the same set — and **writes them
nowhere**. So:

- if only Reddit has run, the X tab shows Reddit's reading;
- if only X has run, the X tab shows a stale Reddit reading or nothing;
- if both have run, **neither tab can say which path spent what.**

## 2 · The record does not exist, and one file cannot provide it

`harvest_run` has **no quota columns**. Its 15 columns are `id`, `source_id`,
`query_key`, `started_at`, `finished_at`, `items_fetched`, `items_kept`,
`http_errors`, `exhausted`, `truncated_by`, `outcome`, `pages_fetched`,
`pages_stored`, `sieve_pass_rate`, `pipeline_version`.

And the X adapter already returns a field with nowhere to go. From
`harvest_run_fields()`:

```python
# `harvest_run_truncated_ck` has no 'quota' value, and quota means
# "stop until the reset" while rate-limit means "retry shortly".
"quota_exhausted": self.quota_exhausted,
```

`quota_exhausted` is computed, returned, and dropped on the floor — the same
"homeless, pending #5" state that `pages_fetched` and `pages_stored` were in
before they got columns.

**A single overwritten JSON file cannot attribute a shared quota.** It holds one
reading with no history and no source, so "how much of the month did X spend"
is unanswerable from it in principle, not just today.

## 3 · What I propose

**(a) Four columns on `harvest_run`.** Per run, so the reading carries the
source that took it:

```sql
quota_limit       int      -- the gateway's own number, as read
quota_remaining   int      -- the gateway's own number, as read
quota_read_at     timestamptz  -- when THIS run read it
quota_exhausted   boolean  -- gives the existing field a home
```

All nullable with no default. A run against a platform with no quota (GitHub,
blogs, arXiv, dev.to, Hugging Face, Hacker News) leaves them NULL, and NULL
means *this platform does not meter that way* — not zero (rule 6).

**(b) Per-path spend by differencing, which is the whole point.** With a dated
reading per run and `source_id` on the row, consecutive readings ordered by
`quota_read_at` give the requests consumed between them, attributable to the run
that took the later one:

```
run A  source=reddit  read 998,660 at 09:12
run B  source=x       read 998,610 at 09:40   -> 50 requests, X's
```

**That is the only honest per-path figure available**, because the provider
meters one key and will never tell us the split. It is a *difference we
computed*, not a number they gave us — so it must be labelled as derived, and it
is only valid where consecutive runs are the only consumers. Any hand-run script
between them lands in the wrong bucket, and that caveat has to travel with the
figure (rule 7).

**(c) `/admin/usage` reads `harvest_run`, not the file.** Then the X tab shows
X's last reading and X's differenced spend, the Reddit tab shows Reddit's, and
both still show the shared limit — which is the true shape: one quota, two
consumers, attribution by difference.

I would keep the file as a fallback rather than delete it, and keep
`_rapidapi_quota()`'s two hard-won properties exactly as they are: **the
provider's own number cached with its date**, and **shown "as of", never as
live**. Both survive this change; the difference is that the reading gains a
`source_id` and a history.

**(d) The X path must actually write it.** The headers are already parsed. This
is one assignment in the X harvester plus the `harvest_run_fields()` entry.

## 4 · What I have not done, and why

**No columns added.** `contract/tables.sql` gets two eyes, and this is four
columns on the table your panel reads — a change I should not make while you
own the reader. **No endpoint change** for the same reason: `judge/` is yours.

**One thing worth deciding before any of it.** X has now made real requests —
the 2026-09-08 corpus harvest issued 3 X search calls and stored 50 posts — so
this is no longer hypothetical instrumentation. But **every X request spends the
Reddit quota**, and `contract/sources.yaml` records that the billed tier is
still unverified: the header says 1,000,000 over a 23.893-day window and the
plan page says 500,000. If it is the 500,000 tier we are cut off at half the
number the page shows, and no request can settle it — it closes on somebody
opening the RapidAPI subscription page in a browser.

**Instrumenting the split is worth much less than knowing the total.** I would
do (a) and (d) regardless, because they are cheap and the field is already
computed; I would not build (b)'s differencing until the tier is read, because
attributing a share of a limit we have not verified is precision on top of an
unknown.

---

*Corpus that made X's requests real:
`docs/new-platform-corpus-and-triage-2026-09-08.md`. Quota reading and the
unverified tier: `contract/sources.yaml`, the `reddit` row.*
