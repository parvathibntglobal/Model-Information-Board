# Decision asked for: what `document.text_ref` holds on Reddit

**2026-09-11, anooj. No code changed. This is the answer to §5.3 of
`docs/for-the-team-reddit-payloads-absent-2026-09-08.md` — "a decision on the
248 prose-as-payload rows" — and it arrives with two findings that change what
the decision costs.**

Read §0 first. The dispute I was asked to referee is **already ruled**, and the
sub-case I was asked to settle first is **a real defect but not the one we
suspected**.

---

## 0 · The three answers up front

1. **The sub-case is not a `{}` writer bug.** It cannot be: `"{}"` is valid
   JSON, so it never produces *"not JSON"*. It produces a different sentence,
   and that sentence fires on **0 of 3,001** readable Reddit payloads. §1.

2. **The contract dispute is not open.** It was ruled on 2026-08-28 —
   `docs/engineer-1/ruling-what-content-hash-identifies.md` — in favour of the
   payload. The ruling, the data repair and the assembler change all landed
   within **82 minutes** of each other that evening. What never landed was the
   revert of the two *writers* that caused it. §2.

3. ~~**The cost of honouring that ruling is far lower than §5.3 assumed.**~~
   **WITHDRAWN 2026-09-14 — this was wrong and §5.3 was right.** See the
   correction at the top of §4. The prose rows are **not** repairable in place;
   they need a re-fetch, exactly as the 09-08 document said.

---

## 1 · The sub-case: her 588 is not `getattr(obj, "raw", None) or {}`

The hypothesis was that `scripts/fetch_model.py`'s `_payload()` writes `"{}"`
for comment objects that carry no `.raw`, and that those `"{}"` blobs are what
refuse. Three independent reasons it is not that.

**1a · The message does not match.** `"{}"` parses fine. It reaches the key
check and raises a *different* sentence:

```
>>> reddit_prose('{}')
reddit payload: no `selftext`, `title` or `body`. A listing page has `data`
or `posts` at its top level and is not one document.
```

Whereas *"not JSON"* comes from `prose.py:69`, which is only reachable when
`json.loads` itself fails. **If her line says "not JSON", `{}` is excluded on
the text alone**, before any data is consulted.

**1b · It has never fired.** Classifying every Reddit row whose payload resolves
on this host:

| outcome | rows |
|---|---:|
| payload is JSON and yields prose | 2,737 |
| `text_ref` points at prose (refuses *"not JSON"*) | 264 |
| **the `{}` signature** (*"no `selftext`, `title` or `body`"*) | **0** |
| *(payload absent from this host — not a refusal)* | *2,280* |

*Denominator: all 5,281 `source='reddit'` rows on shared staging at 2026-09-11
19:16, of which 3,001 have a payload readable on this machine. The 2,280 are §1
of her document — host-local store, not a refusal.*

**1c · The `or {}` branch is dead by construction.** Both types populate `.raw`.
`RedditComment` declares it at
[reddit_comments.py:114](collect/adapters/reddit_comments.py#L114) and sets
`raw=inner` at
[reddit_comments.py:271](collect/adapters/reddit_comments.py#L271) — which is
what `fetch_model.py`'s own comment already claims: *"`.raw` is the original
`data` dict, kept on both types on purpose"*.

### But there **is** a separate defect, and it is the opposite shape

The premise behind the sub-case was right — something wrote non-payloads on her
run — it is just not `{}`. Her 2026-09-10 run wrote **713 Reddit rows**. 697 of
their payloads are not on this host, so I cannot read them. **16 are**, and only
because the raw store is content-addressed and their bytes already existed here
from 2026-08-24:

```
reddit:t1_p4fslui   ref raw/sha256/2a98b1de...   bytes b'Same'
reddit:t1_ov6sxme   ref raw/sha256/dd5f43ed...   bytes b'[deleted]'
reddit:t1_p4pxxaa   ref raw/sha256/985a5be9...   bytes b'[removed]'
```

Three distinct hashes, covering 16 of her 713 rows, each also carried by a row
fetched on 2026-08-24. Those are **bare comment bodies**. `json.dumps` cannot
produce them — it would emit `{"body": "[removed]", ...}`, different bytes and a
different hash, and the dedup would not have happened. So **a writer that stores
`c.body` rather than the payload ran on 2026-09-10**. The writer in the repo
with exactly that signature is
[write_reddit_thread.py:116](scripts/write_reddit_thread.py#L116) —
`texts[c.external_id] = c.body` — and its provenance (`not_recorded`, no
`harvest_run_id`) matches her rows.

**So: yes, a separate defect, and it is a writer storing prose — the same defect
as §2, not a missing `.raw`.**

### What I could not establish, and the one line that settles it

**I could not reproduce 588.** On this host only 41 Reddit roots are left
unassembled and all 41 are payload-absent, not refusals. Her number depends on
her store, which I have not seen. Her log line separates the two remaining
causes by wording, and they are not the same problem:

| her line contains | cause | population |
|---|---|---|
| `refused by the reddit prose extractor (reddit payload: not JSON ...)` | §2, the writers | 264 rows |
| `did not resolve in the store (missing)` | §1 of her own doc, host-local store | 2,280 rows |

The first is a contract question. The second is a file copy and is already
answered. **Neither is a `{}` bug.**

---

## 2 · The dispute is already ruled, and the ruling is 14 days old

Both sides argue the same hazard, correctly, which is why it reads as a live
disagreement:

- [sweep_reddit.py:389](collect/ops/sweep_reddit.py#L389) stores prose *because*
  a JSON envelope lets a quote verify against a field value.
- [prose.py:69](collect/assemble/prose.py#L69) refuses prose *because* passing
  raw text through does exactly that.

They are not two positions. They are **one position and its un-reverted
predecessor.** The chronology, from `git log`:

```
d4f075c  2026-08-28          sweep_reddit.py: payload -> prose      THE DEFECT
7391045  2026-08-28 17:55    THE RULING                             +0h
ca25a33  2026-08-28 19:02    restore 1,517 rows to the payload      +1h07
3a3d2dc  2026-08-28 19:17    prose derived at assembly, both        +1h22
                             platforms, and the test for the class
```

The ruling is four lines:

```
content_hash    the hash of the BYTES THE PLATFORM GAVE US, unmodified.
text_ref        the location of those same bytes.
prose           DERIVED AT ASSEMBLY, never stored in place of the payload.
the invariant   content_hash(resolve(text_ref)) == content_hash, always.
```

**`sweep_reddit.py` has had zero commits since 17:55 that day.** Its comment was
written three hours *before* the ruling and has been read ever since as an
argument against it. `scripts/model_only_sweep.py:297` carries the same comment
and the same un-reverted line.

Both grounds in the ruling are ones no reviewer relitigates cheaply, and neither
is about the verification hazard:

- **NFR-6.** A tombstone must leave a fingerprint of *what the author
  published*. Prose is a fingerprint of a string we assembled — Reddit cannot
  confirm it, and it moves whenever our extractor changes.
- **NFR-4.** *"Reprocess from raw rather than re-fetching."* With `text_ref` on
  prose, the row no longer names its raw artifact, so reprocessing requires a
  re-fetch — and on Reddit the listing endpoint returns *recent* posts, so for
  old threads there is no re-fetch to make.

### Why nothing caught it

`tests/test_assembly_prose.py` is the class check the ruling names, and it asks
of a **`thread_context`**: *does the flattened text parse as JSON?* It covers
**JSON where prose belongs**. The live defect is **prose where the payload
belongs** — the opposite direction, in a **writer** rather than in the
assembler. It passes trivially, and it is not wrong to; it is aimed elsewhere.

Verified today: **0 of 3,821 thread_contexts hold a JSON envelope.** The
assembler side of the ruling is holding perfectly. Only the writers drifted.

---

## 3 · What is actually storing prose today

| writer | line | stores | still live |
|---|---|---|---|
| `collect/ops/sweep_reddit.py` | 389 | title + blank line + selftext | yes, never reverted |
| `scripts/model_only_sweep.py` | 297 | title + blank line + selftext | yes, never reverted |
| `scripts/write_reddit_thread.py` | 116 | `c.body` | yes — ran 2026-09-10 |
| `scripts/repoint_reddit_text_refs.py` | 125 | prose, deliberately | the 2026-08-28 defect, superseded by `restore_...` |

The 264 rows, by the day they were fetched:

```
2026-08-20    5 roots      2026-08-28   13 children
2026-08-24  190 children   2026-08-31    2 children
2026-08-27   38 children   2026-09-10   16 children   <- after the repair
```

**The 18 rows from 08-31 and 09-10 post-date the repair.** This is not a
historical residue being argued over; the writers are still producing rows, and
the newest are from yesterday.

---

## 4 · What each ruling costs — measured, not estimated

> ### ⚑ CORRECTION, 2026-09-14. The cheap-repair claim below was wrong.
>
> This section said all 264 prose rows were repairable in place, with no
> re-fetch, and that this *"corrects §5.3"* of the 09-08 document. **It does
> not. §5.3 was right and I was wrong.**
>
> The error: `restore_reddit_payload_refs.py --dry-run` prints `to update :
> 264`, and the prose population is also 264. **I read a coincidence as an
> identity and checked no ids.** The repair ran on 2026-09-14 and the
> before-values prove it:
>
> ```
> What the 264 repaired rows pointed at BEFORE:
>    264  BEFORE: ref did not resolve on this host
> ```
>
> `resolves_to_payload()` returns `False` for an *unresolvable* ref as well as
> for prose — `# unresolved: not known to be a payload` — so host-absent rows
> fall through to the index lookup and get re-pointed. The prose rows fall
> through too, and `index.get(external_id)` finds nothing for them, **because
> their payload was never stored at all**. That is precisely what
> `collect/assemble/prose.py`'s docstring has said from the start, and what
> §3 of the 09-08 document said. Neither was stale; I was.
>
> Rule 7, on my own figure: `to update : 264` answers *"how many rows can be
> pointed at a payload findable by external_id"*, not *"how many prose rows can
> be repaired"*. It survived inspection because it matched a number I already
> believed.
>
> **What the repair did achieve**, committed 2026-09-14 with in-transaction
> read-back, is real and worth keeping:
>
> | classification of 5,281 reddit rows | before | after |
> |---|---:|---:|
> | payload → prose OK | 2,737 | **3,001** |
> | payload absent on this host | 2,280 | **2,016** |
> | `text_ref` points at prose (refuses) | 264 | **264 — unchanged** |
>
> 264 rows that no assembler could use on this host now resolve to a payload,
> and `content_hash(resolve(text_ref)) == content_hash` was verified on all 264
> before commit. 5 existing `thread_context` rows contain one of them and can
> now be rebuilt more complete. **The prose question below is untouched.**

### If the payload wins (i.e. the standing ruling is simply honoured)

| | |
|---|---|
| prose rows to fix | **264** |
| repairable in place | **0** — the payload was never stored |
| only route | **re-fetch**, subject to `reddit-via-rapidapi` |
| of those, still fetchable | unmeasured — Reddit's listing returns *recent* posts, and these span 2026-08-20 to 09-10 |
| code change | revert the writer lines (done 2026-09-14) |
| `thread_context` rows affected | **8 of 3,823** |
| claims affected | at most those 8 contexts' worth, of 211 |

So the original framing of this question was the accurate one: **if the payload
wins, 264 existing documents stay unassemblable** until somebody spends quota
re-fetching them, and some of them are no longer fetchable at all.

`collect/assemble/prose.py`'s docstring is **correct** and should be left
alone — *"246 reddit rows still point at pre-extracted prose whose payload was
never stored, and they will refuse here. That is correct: they are real text
with broken provenance."* Only the count has moved, 246 → 264.

**The 2,016 host-absent rows stay out of scope under either ruling.** They are
§1 of the 09-08 document: payload absent from *this host*, refs valid
everywhere. Copying Parvathi's `raw_store/` is the fix and it is independent of
this decision.

### If prose wins (i.e. `prose.py` changes to pass text through)

| | |
|---|---|
| rows now holding a payload that would be flattened verbatim | **2,737** |
| rows needing re-pointing to prose | 2,737 |
| tool required | `scripts/repoint_reddit_text_refs.py`, already written, idempotent |
| code change | `prose.py` passes through, or sniffs |
| NFR-6 | **breaks** — `content_hash` fingerprints bytes we assembled |
| NFR-4 | **breaks** — the row stops naming its raw artifact |
| the hazard `prose.py` exists to stop | must be re-solved another way |

The direction matters more than the row count. **Payload-wins repairs 264 rows;
prose-wins converts 2,737** — and converts them to a shape where `content_hash`
moves whenever we touch the extractor, which is the property the ruling was
written to stop. It also requires re-solving the verification hazard, because a
pass-through `prose.py` cannot tell a stored envelope from stored text: that is
precisely the discrimination the 2026-08-28 ruling removed the need for, by
moving extraction to assembly where the shape is known.

I am not going to pretend this is balanced. **Prose-wins is 10x the data
movement, breaks two NFRs the ruling names, and leaves an open problem.** I
record it in full because the ask was for a decision rather than a
recommendation, and because if it is chosen the tooling for it exists too.

---

## 5 · What I need, and what I have not done

**Not done, deliberately: nothing is changed.** No writer reverted, no script
run except `--dry-run`, no row updated.

1. **Parvathi — one line from your run.** The literal refusal text, with its
   parenthesis. The table in §1 turns it into an answer in one reading. If it
   says *"did not resolve in the store"*, this decision does not affect your 588
   at all and the fix is a file copy.
2. **A ruling, or a confirmation that 2026-08-28 stands.** If it stands, the
   work is: revert three writer lines, run `restore_reddit_payload_refs.py`,
   rebuild 8 contexts, correct two stale docstrings. If it is overturned,
   `contract/` reviews it — **12 files cite that ruling by name**, including
   four adapters (`arxiv`, `documents`, `hackernews`, `huggingface`), three
   assemblers (`prose`, `issue`, `reddit`), `restore_reddit_payload_refs.py`,
   `tests/test_reddit_assemble.py` and `docs/onboarding.md`. It is not a
   one-file change.
3. **Either way, a test that looks at the writers.** `test_assembly_prose.py`
   watches the assembler's output and this drifted for 14 days underneath it, in
   the one direction it does not face.

---

*Measured 2026-09-11 19:16 against `DATABASE_URL` (shared staging) and this
host's `./raw_store`. Every figure is over the 5,281 stored Reddit rows, which
is not a sample of Reddit; the 3,001 readable here are not a sample of those
5,281 either — they are the ones whose bytes happen to live on this machine.
Raw figures: `docs/measurements/reddit-text-ref-2026-09-11.json`.*
