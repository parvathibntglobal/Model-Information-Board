# The three dead gates: two shipped, one ruled a recorded field

**2026-09-08, anooj.** Three of triage's six gates ran on nothing in the first
real run. This is what it would take to make each live, which is cheapest, and —
measured rather than estimated — what each would do to the **57.1%** survival
figure (2,860 kept of 5,010 triaged).

**SHIPPED 2026-09-08, both of them.** The two measurable ones are no longer
proposals: `contract/bots.yaml` exists and `document.is_self_post` is a column
with 1,517 rows backfilled from payloads already on disk. Survival on the stored
corpus is now **52.3%**, down from 57.1% - the drop that the published figure was
an upper bound by, realised rather than estimated.

The third is **ruled a recorded field** and a gate for it is not proposed until
a distribution is published. See section 3: the reason is structural, not
scheduling.

---

## The answer up front

| gate | status | what it took | ran on | dropped |
|---|---|---|---|---|
| **`known-bot`** | **SHIPPED** | one YAML file | 3,173 / 5,010 | **154** |
| **`pure-link-post`** | **SHIPPED** | column + migration + backfill, no re-fetch | 1,517 / 5,010 | **224** |
| **`wrong-language`** | **RULED a recorded field** | a dependency decision nobody has made | 0 / 5,010 | 0 |

Survival, measured at each step:

```
57.1%   before either                      2,860 of 5,010
54.2%   with the bot list                     -154 dropped
52.3%   with is_self_post as well             -224 dropped
   ?    a language gate         NOT PROPOSED - see section 3
```

**The bot list was cheapest on every axis** — no schema change, no dependency,
no backfill, no re-fetch — and it had the largest single effect. That ordering
held up.

Per source, before and after: github **42.9% → 38.6%**, reddit
**89.8% → 83.7%**, blog 42.5% unchanged (neither gate reaches it).

---

## 1 · `known-bot` — cheapest, and the most effective

**What it needs:** `contract/bots.yaml`. Nothing else.

The detector is built (`collect/triage/bots.py`, 2026-09-07) and already reports
UNAVAILABLE **per source**, so the count shrinks platform by platform as each is
curated rather than all-or-nothing. The accounts are measured with their stable
ids in `docs/measurements/bot-account-ids-2026-09-07.json` — 33 GitHub accounts,
read from `GET /users/{login}`, not inferred from the login string.

**Measured effect, before and after shipping.** The estimate over all 33
accounts was 149 kept documents. Shipped as 26 gated, the gate **fires on 154**
and survival moved **57.1% → 54.2%**, a net 146 documents.

**146 + 3 = 149**, and that reconciliation is worth a line: the 3 are exactly
what the 7 counted accounts would add if promoted (measured below). The estimate
and the outcome agree once the split is accounted for, which is the check that
the method was measuring the right thing.

**GROSS FIRES AND NET SURVIVAL ARE DIFFERENT NUMBERS AND BOTH ARE HERE.** 154 is
how many documents this gate fired on; 146 is how many stopped being kept. The
8-document gap is documents another gate was already dropping. Quoting the gross
figure as a survival effect would overstate it, which is rule 7 in miniature.

The corpus holds 12 of the 33; the eight busiest:

| account | id | kept documents |
|---|---|---|
| `github-actions[bot]` | 41898282 | 119 |
| `tenstorrent-github-bot` | 123498312 | 38 |
| `claude[bot]` | 209825114 | 33 |
| `Issues-translate-bot` | 74373520 | 4 |
| `FacultativeObligatoryBotContract` | 145221046 | 2 |
| `doyouacceptcrypto-bot`, `llm-exe-bot[bot]`, `happier-bot` | | 1 each |

**Why it is a gate and not a weight, on rule 8's own test.** The question is
*what population was this filter's error rate measured on, and did the filter or
anything upstream choose that population?* For 26 of the 33 the answer is the
platform's: `user.type == "Bot"`, an authoritative declaration, so the error
rate is the platform's own and no population was chosen by us. **The remaining 7
are a judgement** — they carry `bot` in the login with `user.type == "User"`,
and `tenstorrent-github-bot` at 38 documents is the busiest of them. Those 7
were selected by searching for `bot` in a login across a corpus we gathered,
which is exactly the trap rule 8 names.

**SHIPPED AS THAT SPLIT.** `contract/bots.yaml` declares 26 under `accounts`
(gated) and 7 under `counted` (flagged, never dropped). The loader refuses an id
in both lists, because promotion is a MOVE and an id in both would make the
counted figure describe a population it was not measured against.
`BotList.fingerprint` covers both lists with the kind in the digest, so
promoting an account changes it and a verdict that moved cannot be mistaken for
one that did not.

**AND THE COUNT MADE THE REMAINING JUDGEMENT NEARLY MOOT, WHICH NOBODY COULD
HAVE KNOWN IN ADVANCE.** The 7 counted accounts flag 48 documents — and **only 3
of those 48 are kept**. The other 45 are already dropped by another gate. So
promoting all 7 would take survival 54.2% → 54.1%: three documents.

The argument was going to be about `tenstorrent-github-bot`, 33 comments and
joint-top voice in the export. On the stored corpus it is worth almost nothing,
because the documents it would remove are being removed anyway. **That is the
whole value of counting before gating** — the decision did not get easier, it
got smaller, and rule 8's "promoted only once measured" is what surfaced it.
Reading those comments is still what would settle it properly; the 3-document
figure says how much the reading is worth.

## 2 · `pure-link-post` — middling cost, and no re-fetch

**What it needs:** `is_self_post` on `document`, plus the poster's own
commentary. Neither is a column today, so no stored row can answer the gate and
it returns NOT_APPLICABLE on all 5,010 — *permanently*, which is why it reads as
a different kind of hole from the other two.

**The good news, measured:** `is_self` is present in **100%** of readable Reddit
payloads (0 unknown of 1,362). So this is a **backfill from bytes we already
hold** — not a re-fetch, and not an inference. Same for `selftext`, which is the
commentary half.

**Measured effect, before and after shipping.** The estimate was 92 kept Reddit
documents. Shipped, the gate **fires on 224** and survival moved
**54.2% → 52.3%** — a net **92**, matching the estimate exactly. Same gross/net
distinction as the bot gate, and a much wider gap: 132 of the 224 were already
being dropped by another gate, mostly `no-resolvable-entity`.

Reddit alone: **89.8% → 83.7%**. The gate ran on 1,517 of 5,010 documents and
returned NOT_APPLICABLE on 3,493 — GitHub and blog, permanently, because neither
platform has a self/link distinction.

**Scope note that keeps the figure honest:** this gate only ever acts on
platforms that *have* the notion. GitHub and blogs do not and never will — a
blog article has no link-post flag — so their NOT_APPLICABLE is correct and
permanent, and the gate's whole reach is Reddit plus Hacker News. Hacker News
already has the mapping (`hackernews.py`: a story with a `url` and no `text` is
a link post), so it arrives free the moment the column exists.

**What it actually took**, all mechanical and none of it a decision:
`contract/tables.sql`, `20260908T1500_document_is_self_post.sql`, a
`column_states.yaml` entry, three writers, `is_self_post_of` on the Reddit
adapter to match the one Hacker News already had, and
`scripts/backfill_is_self_post.py`. The backfill placed **1,517 rows — 852 self
posts, 665 link posts** — from payloads already on disk.

**1,482 Reddit rows stayed NULL and the three reasons are different**: 1,234
payloads absent from this host, 247 present and not JSON, and 1 that is a
comment. Only the last is a permanent and correct NULL. A backfill that wrote
`false` for the unreadable ones would have turned 1,234 unknowns into droppable
link posts — rule 6, on the gate that acts on the value.

The poster's commentary is deliberately NOT a column: it is `selftext`, which
`text_ref` already addresses, and storing it would put derived bytes beside a
hash that identifies the original. `collect/triage/run.py:_own_commentary` reads
it from the payload it is already parsing.

## 3 · `wrong-language` — dearest, and it cannot be a gate on this corpus

**What it needs:** a detector **and** a populated `lang` **and** an allow-list.
Three things, and the middle one is the blocker.

`document.lang` is NULL on **6,502 of 6,502** rows. I checked whether it could
be backfilled from stored payloads the way `is_self_post` can:

> **Neither Reddit nor GitHub declares a language per document.** No `lang`,
> `language`, `locale` or `content_language` field in any payload sampled.

So for the existing corpus there is nothing to backfill *from*. The un-reserve
on 2026-09-08 helps only **new** documents on the two platforms that do declare
one — dev.to's `language` and X's `lang` — and neither has a stored corpus.

**This is the part that decides it.** Because the value cannot be a platform
declaration here, a language gate on this corpus would have to run a
**detector** — an inference. Rule 8 then applies directly: a check whose error
rate has not been measured against a population it did not choose ships as a
weight, a flag or a recorded field, **never a gate**. And a wrong language gate
is the worst of the three to get wrong, because its false positives are
invisible: it drops the document, and code-switched English — the register most
of this corpus is written in — is exactly what a detector misreads.

**So its effect on 52.3% is not "unmeasured", it is "unmeasurable without first
installing the thing".** No number goes here. The bound is all there is: it can
only lower the figure, over 5,010 documents of unknown language distribution.

**RULED 2026-09-08: THIS STAYS A RECORDED FIELD, AND THE ORDER IS FIXED.**

1. install a detector (one dependency decision, nobody has made it);
2. write its output to `document.lang` as a **recorded field**;
3. run it over the corpus and **publish the distribution**;
4. *only then* is a gate a proposal anybody can argue with.

Step 3 is not a formality. It is the error-rate measurement rule 8 asks for, and
it is also the thing that would tell us whether this gate is worth having at all
— a corpus that is 99% English does not need a language gate, and nobody knows
whether this one is. **A gate proposed before step 3 should be refused on
process**, not debated on merit. The ruling is recorded in
`collect/triage/gates.py` beside the gate itself, so the next person to look at
it finds the order rather than the invitation.

---

## What this means for the published figure

`docs/triage-first-run-2026-09-08.md` says 57.1% is an upper bound because two
gates could not run. It is now possible to say **by how much, for two of the
three**:

```
57.1%   as published, 2,860 of 5,010
54.1%   with the bot list                          -149 documents
55.2%   with is_self_post                           -92 documents
52.3%   with both                                  -241 documents
   ?    with a language gate            direction known, size unknown
```

**Neither of the two measurable ones needs new data.** The bot list is a file
somebody writes; `is_self_post` is a column plus a backfill from payloads
already on disk. Between them they account for a 4.8-point overstatement in a
figure that is otherwise the first real thing this pipeline has said about its
own corpus.

---

*Measured 2026-09-08 against `DATABASE_URL` (shared staging) and this host's
`./raw_store`. Population: the 5,010 documents triage could gate, of 6,502
stored — 1,492 were never gated (payload absent or not prose; see
`docs/for-the-team-reddit-payloads-absent-2026-09-08.md`), so every figure here
carries that same hole. Bot ids from
`docs/measurements/bot-account-ids-2026-09-07.json`.*
