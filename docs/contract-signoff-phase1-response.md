# Contract sign-off — Engineer 2's response

**Three rulings: items 17, 18 and 20. All three closed.**

*Answering `docs/contract-signoff-phase1.md` · against `main` at `1d04041`*

---

Seventeen of the twenty were applied or resolved on your side, and I have no
objection to any of them. The re-sourcing pass in particular fixed something I
had flagged and not acted on: the seed file previously cited 31 of 40 sources
to third-party blogs, including `deepseek-r1`'s price to a Gemini article.
FR-2 at 82/82 off provider pages is a materially different file.

**A note on timing.** Your message says the sign-off package on `main` is three
revisions stale and the changes are on the branch. That was true when you wrote
it. **PR #3 is merged** — `main` is at `1d04041` and carries everything,
including the corrected sign-off. Nobody needs to switch branches.

| Item | Ruling |
|---|---|
| 17 | **Accepted as written.** Comment only |
| 18 | **Build `price_tier`.** `price_in` goes NULL when tiers exist — not "lowest tier" |
| 20 | **Accepted, with one addition** — the exclusion has to be visible, not just guarded |

---

## Item 17 · `knowledge_cutoff` means the reliable cutoff

**Accepted exactly as proposed.** Apply the comment.

The reasoning holds and I would have argued for the same answer from the
other end. The column exists so the answer path can reason about what a model
knows. Every use of it is a question of the form *"will this model have heard
of X?"*, and the reliable cutoff is the honest answer to that question.

The failure direction matters. Overstating what a model knows produces a
recommendation that looks fine and is wrong — the model answers confidently
from a gap in its knowledge. Understating it costs a model a recommendation it
might have won. The first is a silent failure and the second is a loud one, so
where the two dates disagree, the column should hold the conservative one.

No further edit needed from my side.

---

## Item 18 · Tiered pricing

**Build `price_tier` as proposed. Two decisions attached.**

Removing Gemini 2.5 Pro's prices rather than picking a tier was right. Taking
the cheap tier would understate cost by 2x on exactly the long-context tasks
FR-31 exists to catch, and §9 names a false qualification as the worst output
this system can produce. A 2x understatement on a frontier model is precisely
that: it wins recommendations it should lose, and nothing surfaces why.

### Decision 1 · `price_in` is NULL when tiers exist

Your item leaves this open — *"the rate at the lowest tier, or stays NULL"*.

**It stays NULL.**

A lowest-tier fallback is a trap, and it is the same trap item 20 describes.
If `price_in` holds the cheap tier, then every code path that forgets to check
`price_tier` gets a number that is wrong but entirely plausible — a frontier
model appearing at half price, out-ranking cheaper models on a figure nobody
has reason to distrust. The error is invisible at the point it is made and
invisible on the page.

With NULL, forgetting fails loudly. `judge/ask/cost.py` already returns no
estimate when a price is missing, and a candidate with no cost renders as
unpriced rather than as cheap. An unpriced frontier model is a visible gap
somebody fixes. A frontier model at half its real price is a wrong
recommendation nobody catches.

The general rule, and it is the one your item 20 is built on: **where a
missing value can be silently mistaken for a real one, make it absent rather
than approximate.**

### Decision 2 · Build it now, not in week 5

The cost of deferring is not abstract. Gemini 2.5 Pro is one of two frontier
models in the seed set, and the frontier models are what everything else is
compared against — it is the natural `reference_model` for a Google shop
asking what it can move off. Unpriced, it cannot be a candidate or a
comparison point, so a whole provider's cost story is missing until the table
exists.

The table is small, and the poller will meet tiered pricing from week 5
regardless. Building it now means the poller inherits a working shape instead
of forcing a schema change mid-phase.

### The DDL, as you proposed it

Unchanged from your item. Recording it here so both files agree:

```sql
CREATE TABLE price_tier (
  model_version_id  text NOT NULL REFERENCES model_version(id),
  dimension         text NOT NULL,   -- input_tokens | output_tokens
  min_tokens        int NOT NULL DEFAULT 0,
  max_tokens        int,             -- NULL = no upper bound
  price             numeric(12,6) NOT NULL,
  price_cached_read numeric(12,6),
  sources           jsonb NOT NULL,
  PRIMARY KEY (model_version_id, dimension, min_tokens),
  CONSTRAINT price_tier_dimension_ck CHECK (dimension IN ('input_tokens','output_tokens'))
);
```

One comment worth adding above it, since it is the thing a later reader will
get wrong:

```sql
-- model_version.price_in / price_out are NULL when a row exists here. They are
-- NOT the lowest tier. A lowest-tier fallback would let any caller that forgets
-- to read this table price a model at half its real rate on long-context work,
-- which is a false qualification and reads as plausible on the page.
```

### What `judge/` does with it

Q6 reads `price_tier` when rows exist and prices each dimension at the band
the workload actually lands in — `input_tokens` against the estimated input
size, `output_tokens` against the estimated output size. The estimate carries
a caveat naming the band used, because a workload sitting near a boundary can
cross it in production and the user should see which side we assumed.

`Pricing` in `judge/ask/cost.py` takes an optional tier list; the untiered
path is unchanged. I will do this when the DDL lands — it is my side of the
change and it does not block you.

---

## Item 20 · `reported_context.provenance`

**Accepted, including the `assert_no_fixtures()` extension. One addition.**

The argument is correct and it is the stronger version of a rule I broke in my
own lane this week, which I have written up at the end of this document.

The asymmetry you name is the whole point:

> A wrong `cell` shows up as a phrase somebody can read and disagree with. A
> wrong `reported_low` shows up as an absence, and nobody audits a model that
> was never in the list.

`reported_low` is read by FR-31 as a hard filter. Every other number on the
board argues its case in front of the reader and can be disagreed with. This
one removes candidates before the reader sees them, so it needs a guard the
others do not.

Apply the DDL and the assertion exactly as written. The three-query form is
right — adding the column without extending `assert_no_fixtures()` leaves the
guard the column exists to provide.

### The addition — an exclusion has to be visible

The `provenance` column stops a hand-seeded threshold reaching production. It
does not stop it being invisible in development, which is where it will
actually do its damage, because that is where hand-seeded values legitimately
exist.

So on my side: when a model is excluded on `reported_low`, the answer path
names it — the model appears with the reason, not omitted from the list. Where
`provenance = 'hand_seeded'` it says so:

```
Gemini 2.5 Pro  — excluded: reported effective context 180k, below the 400k
                  this task needs. Threshold is hand-seeded, not harvested.
```

That is a change in `judge/`, not a contract change, and no action is needed
from you. Recording it because it is the half of item 20 that makes the column
do something a reader can act on.

---

## Your question about `judge/`'s tests

> `judge/` landed 62 tests in `d0be8e6` — if any of them need a database and
> currently skip, the same exposure exists.

**Checked. None of them skip.** All 46 skips in the suite are
`tests/test_registry_load_db.py`. The 62 judge tests pass, and none reference
a database, a connection or `DATABASE_URL`.

The honest answer is less reassuring than that number, though. They do not
skip because **`judge/` has no write path at all yet.** Nothing in the lane
persists — `claim`, `claim_weight` and `cell` are unwritten. Verification,
weighting and gating all run against in-memory fixtures.

So the exposure you describe is not present today and is not avoided either;
it arrives the moment the first `INSERT INTO claim` is written, in week 4.
I will bring those tests up against a real database in the same commit as the
write path rather than after it, which is the lesson your six defects paid
for.

---

## `BUILD-PLAN.md` §3.3

Confirmed stale, and it is mine to fix. `contract/tables.sql` has
`model_event`, `pricing_history`, `watermark`, `source`, `harvest_run` and
`coverage_gap` that the plan listing omits, and it has now caused two wrong
review findings.

**`contract/tables.sql` is the schema. The plan is not.** I will mark §3.3
illustrative and point it at the file rather than trying to keep a prose copy
synchronised, because a duplicate that drifts is worse than no duplicate —
this is exactly how it produced wrong findings.

---

## One from my side, since it is item 20 in mirror image

Not a contract item and it needs nothing from you. Recording it because you
found the principle from the schema end while I was breaking it from the
filter end, and the pair is worth having written down.

Your re-sourcing pass removed 48 unsourced values, including
`supports_tools` and `supports_structured_output` on most of the seed models,
because the providers do not publish them. That was right.

`judge/`'s hard filter read an absent flag as `false`:

```python
if hard.needs_tools and not spec.get("supports_tools"):
    return False        # "not published" became "cannot do it"
```

On a plain summarization request the candidate list went from 11 models to 1,
and the answer path abstained. Ten models were removed for a capability nobody
had ever claimed they lacked — and, exactly as item 20 predicts, **it showed
up as an absence.** No error, no warning, nothing on the page to disagree
with. I found it by testing against your branch before it merged, not by
reading the output, because the output looked like a considered answer.

The fix is the same shape as your ruling: three states, not two. `true`,
`false`, and *not published* — where the third suppresses nothing and instead
renders as a caveat the reader can act on.

The Ask box is parked for now, so this is not urgent, but the rule it produced
is general enough to be worth stating once, in both lanes:

**A missing value must never be silently converted into a definite one.**
Absent capability evidence must not read as incapability, absent price must
not read as cheap, and absent context evidence must not read as a threshold.
