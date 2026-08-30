# The API answers the bot question, and the agreement's denominator is two

**`user.type` is a field GitHub declares; `[bot]` is a string a human can
choose.** They agree on all 148 comments already fetched — 23 `Bot`, 125 `User`
— and that agreement rests on **two accounts**, `github-actions[bot]` and
`linear[bot]`. So the suffix is not sufficient, and the write path keys on the
field.

*Engineer 1 · 2026-08-30. Built while staging is down; nothing here has written
to it.*

---

## 1 · The bot question, answered from the payloads we already hold

`StoredComment` kept `author_handle` and threw the rest away, so this was
answered by re-reading the raw store rather than by re-fetching — the payloads
are content-addressed and were never the thing that was missing.

```
user.type      User 125   Bot 23
distinct accounts               67
distinct HUMAN accounts         65
bot accounts                     2   github-actions[bot], linear[bot]

(user.type=='Bot', login ends '[bot]')
  True,  True    23
  False, False  125
  disagreements   0
```

**The `[bot]` suffix is not sufficient, and the zero disagreement is why it
looks like it is.** 148 is the comment count and the wrong denominator: what is
actually measured is that **two GitHub Apps follow GitHub's own naming
convention**, which they do because the platform renders the name. A person can
register `notabot`; a maintainer can be called `releasebot`; neither is an App.
`user.type` is the platform *declaring* what an account is — a field rather than
an inference, the same distinction as `document.has_numbers` being counted
rather than asserted.

So `StoredComment.is_bot` reads `user.type`, and `bot_suffix_disagrees` counts
any row where the two part company. Zero today; the population that would show
one is the population we have not fetched.

## 2 · A bot is stored, named, and is not a voice

`github-actions[bot]` is the **single busiest commenter in the corpus** at 22 of
148. Nothing filtered bots anywhere.

The ruling — drop at collection, or weight at E6 — is Engineer 2's, and
`judge/vet/reject.py` is her file. So the write path takes the only option that
keeps both rulings open:

```
status          'filtered', not 'kept'
filter_reasons  ['bot_author']       so /filtered names the rule
author_id       NULL                 no author row, no voice
the payload     kept                 a ruling either way applies to data we
                                     already hold rather than to a re-fetch
```

**Dropping the row would prejudge it.** *"Rejected is not deleted"* exists for
exactly this case: a bot comment that never reached the table cannot be
re-weighted the day the ruling says weight it.

⚠ **`author_id` NULL is not enough on its own, and this is the part that would
have been missed.** `judge/store/cells.py` maps a NULL author to
`ANONYMOUS_VOICE:platform` — one shared voice per platform — so a bot left in an
assembled thread could still be quoted and still contribute that shared voice.
The guard that matters is `assemble_issue_thread` refusing bots as **members**,
so the extractor never sees them. Both guards are tested.

## 3 · The third assembly shape

`assemble_issue` handles the body alone and always did; the module docstring said
a tree assembler "would be building it against no data". 148 comments across 30
issues is data, and **25 of the 71 stored issues carry comments that were counted
and never fetched**.

`assemble_issue_thread` is the third shape, and it is not a copy of Reddit's:

**It does not rank on engagement, because GitHub does not return one.**
`thread.rank_children` scores `specificity × log1p(max(score, 0))`. A GitHub
issue comment has no score — reactions are not on the comment-list endpoint — so
passing `None` through gives `log1p(0) = 0.0`, which multiplies **every** comment
to zero and turns the ranking into a tie broken on `external_id`, i.e. arrival
order presented as relevance. That is this project's recurring failure shape: a
computation that runs, produces a number, and ranks on something nobody chose.
The engagement term is dropped rather than defaulted, and there is a test that
reads the function body — not its docstring, which quotes `log1p` on purpose — to
keep it that way.

```
selection_method   issue_with_comments      distinct from issue_body_only
observed_children  humans we hold           bots are excluded from this too, so
                                            the ratio is HUMAN coverage
hidden_children_min comment_count - observed
hidden_branches_unsized 0                   a measurement here: GitHub comments
                                            are a flat list, so there are no
                                            collapsed branches to be unsized
```

The body-only path is **not** deprecated: an issue with no comments genuinely is
one member, and which function to call is a fact about what was fetched.

## 4 · The sweep runs shapes, and the ranking is the order

```
shape    on-subject/req   UNIQUE/req    issued
title         31.0           26.3       yes, first
label         21.7            9.7       NO
repro         15.8           10.2       yes, second
signal         3.7            3.5       no
```

**Shape-major, not surface-major.** A run truncated at request 4 of 6 should have
issued `title` for every model rather than both arms for the first two — the
first arrangement loses the weakest arm on all models, the second loses both arms
on a third of them. Truncation is the expected case at 30 requests per minute, so
the order is the design.

**Unique per request is what decides an arm**, and `label` is the case that
proves it: 21.7 on-subject looks like a strong second arm and 9.7 unique is a
weak one, because 30 of its documents are repro's and 10 are title's. A report
ranking arms by kept documents would have bought `label` twice.

### Why `label` is refused, and the arithmetic is the weakest of the three reasons

1. **9.7 unique per request** — a third of what its headline suggests.
2. **Structural qualifiers measured as doing nothing at `max_pages=1`.**
   `is:issue state:open` shrinks the reported corpus 3.65× and returns the
   **identical 100 ids in the same order**, because the qualifier narrows the
   corpus and page 1 is all we ever read. `label:` is a different qualifier and
   is *not strictly covered* by that measurement — which is why the refusal says
   "most likely to reproduce a known null" rather than "will".
3. **It narrows toward complaints.** `label:bug` retrieves issues somebody filed
   as a defect, which makes the **positive half** of the four silent-failure
   capabilities structurally unreachable. That is rule 4 arriving through the
   query rather than through the page: an arm that can only find criticism
   produces a board where absence of praise reads as absence of quality.

`sweep_requests` **raises** on `label` rather than filtering it out, because
asking for it is a decision somebody made and dropping it quietly would let a
sweep report coverage it never attempted.

## 5 · What it costs

```
scale                  shape(s)      reqs   minutes   ~unique docs (band)
11  models swept today title           11      0.4m            75 - 709
11                     title+repro     22      0.7m           104 - 984
30  models             title           30      1.0m           204 - 1,934
30                     title+repro     60      2.0m           283 - 2,685
342 full registry      title          342     11.4m         2,321 - 22,051
342                    title+repro    684     22.8m         3,221 - 30,603
```

**The band is printed and the midpoint is not.** Population: 18 requests, three
models. Per-model title yield was **76 / 8 / 9** on-subject — a factor of nine on
one shape, with the mean above two of the three points. A single projected figure
from that sample would be a real number answering a question it was not asked.

**Where the budget goes.** The existing query space is 76% consumed and holds
roughly **57 more documents**. A full-registry `title+repro` run is 684 requests
and 23 minutes of the search bucket, on two arms neither of which has been issued
at scale. That is the comparison, and it is about **retrieval** — extraction is a
separate decision waiting on the tier re-weight.

## 6 · What is blocked on staging

Everything built here is tested against local Postgres and writes nothing
remote. Blocked, in the order it would run:

```
1  the sweep itself                needs the search API and the registry -
                                   `model_version` is on staging, so even
                                   choosing surfaces needs the host
2  write_comments on the 148       the documents they attach to are on staging
   already-fetched comments        (the comment PAYLOADS are local and safe)
3  re-assembling the 25 issues     `assemble_issue_thread` over issues whose
   that have comments              bodies are staging rows
4  harvest_run rows for the sweep  `harvest_run.source_id` references `source`
5  the 344 documents with no       a backfill, and not this sweep's job -
   retrieval provenance            named because the sweep is the reason the
                                   column exists and it should not add a 345th
```

Not blocked, and already done: the renderer arms, the sweep planner and its
refusals, the cost model, the bot classification, the comment write path, the
third assembly shape, and 34 tests.

**Nothing here extracts.** GitHub's 17 existing claims came out 7 tier D and 10
tier E, and whether more GitHub is worth paying for depends on what the tier
re-weight says. Retrieval and assembly are worth having either way.
