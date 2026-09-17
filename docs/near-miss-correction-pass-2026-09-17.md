# Correction pass after the near-miss rule: 20 verdicts, 2 claims, and 2 cells left stale

**Staging write session, 2026-09-17 06:15Z, anooj + Claude.** Announced here
because it touched stored verdicts and deleted rows on the shared database.

⚠ **IT IS NOT FINISHED. Two cells are stale and I could not rebuild them** —
see *What is outstanding* at the bottom. That is the first thing a reader needs.

---

## Why a correction pass at all

Flipping (b) (#341) changed what `resolve` returns. It rewrote nothing: triage
writes only `triage_verdict` and `filter_reasons`, and **no table maps a
document to a model by resolution** — the only `document_id` columns are on
`claim`, `board_entry`, `capability_candidate` and `golden_label`, none written
by the resolver.

So the 2,322 documents that shed a wrong attribution were never *filed* against
those models in any row. What WAS stored and wrong: documents whose verdict said
`kept` on the strength of a surface the rule now refuses.

## What was written

```
20  document.triage_verdict  'kept' -> 'dropped', + no-resolvable-entity
 2  claim                    deleted
 2  board_entry              deleted  (no ON DELETE CASCADE - removed first)
 2  claim_weight             deleted  (ON DELETE CASCADE)
```

Snapshots were taken before the write, but **`var/` is gitignored, so they
exist only on the machine that ran this**. The rows are therefore reproduced
here in full, because a record that points at a file nobody else has is not a
record.

The 20 documents, every one stored `kept` with `filter_reasons` NULL:

```
  devto:4629055            devto       was kept, filter_reasons=None
  devto:4658881            devto       was kept, filter_reasons=None
  doc_0827576d0af3e901     github      was kept, filter_reasons=None
  doc_357c8d6e1214b8c8     github      was kept, filter_reasons=None
  doc_3d112da081e4c2ca     github      was kept, filter_reasons=None
  doc_527b594053df5966     github      was kept, filter_reasons=None
  doc_c09cc71451ad0b20     github      was kept, filter_reasons=None
  doc_ce89e7408c1f3a6d     github      was kept, filter_reasons=None
  hackernews:49700411      hackernews  was kept, filter_reasons=None
  reddit:t1_ou0yit8        reddit      was kept, filter_reasons=None
  reddit:t1_ouoib6w        reddit      was kept, filter_reasons=None
  reddit:t1_p68l4ft        reddit      was kept, filter_reasons=None
  reddit:t1_p6jdyt0        reddit      was kept, filter_reasons=None
  reddit:t1_p75tsh3        reddit      was kept, filter_reasons=None
  reddit:t1_p79826f        reddit      was kept, filter_reasons=None
  reddit:t1_p828n4x        reddit      was kept, filter_reasons=None
  reddit:t1_p8l5d11        reddit      was kept, filter_reasons=None
  reddit:t3_1ubi93u        reddit      was kept, filter_reasons=None
  reddit:t3_1uglmzl        reddit      was kept, filter_reasons=None
  reddit:t3_1vokoir        reddit      was kept, filter_reasons=None
```

The four deleted rows, exactly as they were:

```json
{
  "claims": [
    {"id": "clm_89f9541d4d829e3aeed821ec", "document_id": "hackernews:49700411",
     "model_version_id": "mv_568e0eb3a95b5113",
     "capability_key": "tool_calling.long_chain_reliability",
     "polarity": "positive", "quote": "5 is so much better at tool use"},
    {"id": "clm_f8e441faf9f7ecbb3d4b8e99", "document_id": "hackernews:49700411",
     "model_version_id": "mv_568e0eb3a95b5113",
     "capability_key": "instruction.adherence",
     "polarity": "negative", "quote": "5 for sure is unbearable"}
  ],
  "board_entries": [
    {"id": "be_c528bcc5bf0395cf7231b9b1", "slug": "agentic-tool-use",
     "model_version_id": "mv_568e0eb3a95b5113", "document_id": "hackernews:49700411",
     "claim_id": "clm_89f9541d4d829e3aeed821ec",
     "quote": "5 is so much better at tool use"},
    {"id": "be_527862438e47bda77ecb20fc", "slug": "contrarian-behavior",
     "model_version_id": "mv_568e0eb3a95b5113", "document_id": "hackernews:49700411",
     "claim_id": "clm_f8e441faf9f7ecbb3d4b8e99",
     "quote": "5 for sure is unbearable"}
  ]
}
```

`mv_568e0eb3a95b5113` is `anthropic/claude-opus-5`.

**The 20 are the only verdicts that could change**, and that is a property of
the change rather than a sampling decision: only `resolve` moved, so only
`NO_ENTITY` can fire differently, and only a document left with no surface at
all can flip. Of the 33 documents that now resolve to nothing, 20 were stored
`kept`, 12 were already `dropped`, and 1 was saved by a surviving surface
(`deepseek v4` in `doc_12c94e8f4d7092f9`).

**`triage_stored` was NOT used, and that was a scoping decision.** Its `_SELECT`
takes `WHERE triage_verdict IS NULL` plus an optional source filter and nothing
else, so clearing the 20 and re-running would also have triaged the **2,210**
documents that have never been triaged. That is legitimate work and it is not
this task; it would have made a 20-row correction into a 2,230-row write with
no line saying which was which.

## The two claims, handled deliberately

Both were on `hackernews:49700411`, both filed under `anthropic/claude-opus-5`,
both `quote_verified: true`. The document reads:

> 5 for sure is unbearable, 4.8 is a reasonable sweet spot, 4.6 tends to just
> agree with whatever I say. But lately I haven't downgraded because 5 is so
> much better at tool use … and hope **Opus 5.1** fixes this mess.

The only registered surface it contains is inside `Opus 5.1`. The quotes are
real and verified; the subject is not supported by anything the resolver can
see. **Offsets survive, subject does not** — the same shape as the Reddit
rebuild, and the reason removal rather than re-attribution is the answer: there
is nothing to re-attribute *to* without inventing a subject.

**Two claims on the same document were KEPT**, and that is the deliberate part:

```
REMOVED   clm_89f9541d4d829e3aeed821ec  opus-5    "5 is so much better at tool use"
REMOVED   clm_f8e441faf9f7ecbb3d4b8e99  opus-5    "5 for sure is unbearable"
KEPT      clm_067198e6e73f8e08a6aeb32f  opus-4.8  "4.8 is a reasonable sweet spot"
KEPT      clm_b0100d7b3de5c42e4937bbf8  opus-4.6  "4.6 tends to just agree…"
```

The extractor read 4.8 and 4.6 correctly. A document's triage verdict governs
whether it is extracted *again*; it does not retroactively invalidate claims
whose subject is sound. Deleting all four because the document now drops would
have thrown away two correct attributions to fix two wrong ones.

## What happens to the two cells

Computed by running `CellStore.rebuild_all()` inside a transaction and rolling
it back — the numbers are measured, not projected:

| cell (`anthropic/claude-opus-5`) | voices | pos/neg | n_eff | quotes | status |
|---|---:|---|---:|---:|---|
| `instruction.adherence` before | 20 | 1/19 | 0.463 | 35 | insufficient |
| after | **19** | 1/18 | 0.448 | 34 | insufficient |
| `tool_calling.long_chain_reliability` before | 3 | 2/1 | 0.045 | 3 | insufficient |
| after | **2** | 1/1 | 0.029 | 2 | insufficient |

**The three-voice cell becomes a two-voice cell, and nothing about its
publication changes, because it was never publishing.** `N_EFF_MINIMUM` is
**3.0** and its `n_eff` is 0.045 — two orders of magnitude below. Across all 258
cells, **0 were above `insufficient` before and 0 after**; exactly 2 cells move
and none crosses a boundary.

What DID change visibly is the two `board_entry` rows, and those are a different
mechanism: `judge/pages/roster.py` records that *"a board_entry is UNGATED: it
means somebody said it"*. They rendered on Opus 5's page regardless of the cell
gate, which is why they were the live wrong state and the cells were not.

## What is outstanding

**`judge rebuild-cells` has not run. The two cells above still count the deleted
claims and still cite them in `quote_ids`.**

It was refused, correctly:

> refusing `judge rebuild-cells`: ENVIRONMENT=development and the database is
> 52.17.75.29, which is not this machine.

`judge/writeguard.py` exists because this lane's write commands had no gate at
all. It also says, in the refusal itself, that `ENVIRONMENT=staging` satisfies
the check and **is not a substitute** — it turns this guard off without turning
another on. So it was not stepped around.

**This is a sequencing mistake and it is mine**: the rebuild path should have
been checked before the claims were deleted, not after. The database is
consistent — no dangling foreign key, `quote_ids` is a `text[]` and not a
reference — but two cells overstate their evidence by one claim each until
somebody runs:

```
judge rebuild-cells        # from an environment the writeguard permits
```

Expected outcome is the table above: 2 of 258 cells move, no status changes.
Anything else is a disagreement worth reading before it is committed.
