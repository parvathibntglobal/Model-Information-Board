# Correction pass after the near-miss rule: 20 verdicts, 2 claims, and 2 cells left stale

**Staging write session, 2026-09-17 06:15Z, anooj + Claude.** Announced here
because it touched stored verdicts and deleted rows on the shared database.

⚠ **IT IS NOT FINISHED. Two cells are stale and I could not rebuild them** —
see *What is outstanding* at the bottom. That is the first thing a reader needs.

**STALE BY A KNOWN AMOUNT, NOT WRONG BY AN UNKNOWN ONE.** Until
`judge rebuild-cells` runs, these two rows on `anthropic/claude-opus-5` each
**overstate their evidence by exactly one claim**:

```
instruction.adherence / context_size:unknown
    reads   20 voices · 1 positive · 19 negative · 35 quotes
    is      19 voices · 1 positive · 18 negative · 34 quotes

tool_calling.long_chain_reliability / tool_count:unknown
    reads    3 voices · 2 positive ·  1 negative ·  3 quotes
    is       2 voices · 1 positive ·  1 negative ·  2 quotes
```

Both still hold a deleted `claim_id` in `quote_ids`. Both remain
`insufficient` before and after, so **nothing published moves** — the overstate
is in the counts a reader sees on the cell, not in what the board asserts.
Anybody quoting these numbers in the meantime should quote the right-hand
column.

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
> 203.0.113.5, which is not this machine.

### Which environment satisfies the writeguard, honestly: none, from here

`check()` permits a write in exactly three cases, and only three:

```
no DATABASE_URL                     not a real path
environment() != "development"      any other value
is_local(url)                       a database on this machine
```

Against the shared database from a laptop, **two of those doors are shut and the
third is the one the refusal itself disowns**:

- `is_local` is out — the rows are on 203.0.113.5, which is the whole point.
- **Unsetting `ENVIRONMENT` does not help.** `environment()` is
  `(os.getenv("ENVIRONMENT") or DEV)`, so unset resolves to `development` — the
  refused value. There is no neutral setting.
- Any non-development value passes, and passes for no good reason.
  `check()`'s own comment says so: *"on a non-dev flag NO fixture check runs on
  this path — returning here only declines to over-refuse, it does not hand off
  to another guard."*

**So the plain answer is that nobody can run `judge rebuild-cells` from a laptop
against the shared database and have a guard be satisfied.** Every value that
gets through gets through by the guard declining to over-refuse. The honest
place to run it is a host where `ENVIRONMENT` is genuinely not `development`
because of what the machine IS — the deployment — rather than because somebody
set it to get past a check. Even there the protection is circumstantial: `judge/`
does not call `preflight()`, so no fixture check runs; what protects that host is
having no fixtures to leak, not a check confirming it.

### This is #328 arriving as a blocked task rather than a principle

[#328](https://github.com/parvathibntglobal/Model-Information-Board/issues/328)
records that the writeguard covers `judge/cli.py` and not `scripts/fetch_model.py`,
so the safer operation is refused and the riskier one is not. That is no longer
an argument about coverage; it is why this correction is half-finished.

Verified independently while writing this, not taken from the issue:

```
callers of writeguard.check()   judge/cli.py:73
                                scripts/run_extraction_batched.py:90
                                — that is the entire list
scripts/fetch_model.py:1903     "Spends (capped) OpenRouter money and writes
                                 claims + cells"
```

So **`fetch_model.py` would write `cell` rows to this same database, from this
same laptop, under this same flag, right now.** Recomputing cells from claims
already stored — deterministic, no model call, no new information — is refused.
Paying a model to create the claims and then writing the cells is not. The
correction is blocked and the origination is not.

`judge/writeguard.py` exists because this lane's write commands had no gate at
all, and refusing was right. It was not stepped around.

### Can it run on the Railway backend? Yes — so this is blocked on #328, not on access

**The backend is deployed and it writes.** `fetch_log.machine` carries
container hostnames beside the two laptops:

```
machine-B       314   2026-09-17     laptop
machine-A          932   2026-09-16     laptop
1fb1c6863ef5   128   2026-09-16     container
a2aa987f50e8    98   2026-09-16     container
7f713664b611    67   2026-09-15     container
8f092b28828c    65   2026-09-15     container
2fa959aa2765    28   2026-09-16     container
dbdf571f8b13    14   2026-09-14     container   (the machine named in CLAUDE.md's
                                                 undertaking incident)
```

Those containers ran `scripts/fetch_model.py`, which says of itself *"Spends
(capped) OpenRouter money and writes claims + cells"*. So a container has
already written `cell` rows to this database.

**The command is present in the image and would be permitted there:**

| | |
|---|---|
| `Dockerfile` | `COPY . .` plus `pip install .` with `include = ["collect*", "judge*"]` — the whole source and the packages |
| invocation | `python -m judge.cli rebuild-cells`. There is **no** `[project.scripts]`, so there is no `judge` console script; the module form is the one that works |
| `ENVIRONMENT` | `production` on the deployment (§7.3 of the Railway plan, and `judge/gate.py`'s API_TOKEN rule forces it), so `writeguard.check()` returns early |
| `DATABASE_URL` | read directly by `judge/cli.py`, not via `MODELBOARD_DB`; the deployment runs `MODELBOARD_DB=write`, which is how the fetches wrote |

What is missing is only a **way in**: `CMD` is `["python", "serve.py"]` and there
is no Procfile, no second service and no job runner, so the container serves the
API and nothing else. Getting a one-off command in needs `railway ssh` into the
running container, or a second service built from the same image with a
different start command. **I cannot verify from this repo which of those the
team's Railway plan allows** — there is no `railway` CLI on this machine and no
`railway.json` in the tree.

⚠ **`railway run` IS NOT THE ANSWER AND IS THE TRAP.** It executes the command
**locally** with the deployment's variables injected, so it would hand this
laptop `ENVIRONMENT=production`, satisfy the writeguard, and run the write from
the machine that has the fixtures — which is precisely the pairing the guard
exists to refuse. It would look like running it on Railway and would be the
hazard wearing the deployment's clothes.

**So the honest statement to the team is that this is blocked on #328, not on
access.** Somebody can run it: the image has the command, the environment
permits it, and a container has already written these tables. What there is no
sanctioned route for is the *safer* operation from a laptop — which is #328's
inversion exactly, now holding up a correction rather than illustrating a
principle.

---

**This is a sequencing mistake and it is mine**: the rebuild path should have
been checked before the claims were deleted, not after.

### The ordering lesson, stated generally

**A correction that leaves a derived table overstating its evidence is only half
a correction.** The specific error was checking the recompute path after
removing the rows it derives from; the general form is that a deletion and the
recomputation it obliges are ONE operation, and doing the first without
establishing that the second can run leaves the database in a state that is
internally consistent and externally wrong - which is the worst combination,
because nothing complains.

It generalises past cells. Any write that invalidates a derived artifact -
`cell` from `claim`, `thread_context` from `document`, a materialised view from
anything - has the same shape. The cheap discipline is to **run the
recomputation as a dry run first**, which here would have taken one rolled-back
transaction and would have surfaced the writeguard refusal before anything was
deleted rather than after.

Worth recording because the failure is invisible in a diff and in a test suite:
the rows are gone, the constraint holds, the suite passes, and two cells quietly
claim one more voice than they have. The database is
consistent — no dangling foreign key, `quote_ids` is a `text[]` and not a
reference — but two cells overstate their evidence by one claim each until
somebody runs:

```
judge rebuild-cells        # from an environment the writeguard permits
```

Expected outcome is the table above: 2 of 258 cells move, no status changes.
Anything else is a disagreement worth reading before it is committed.

**And it can run** — see the Railway section above. The image carries the
command, `ENVIRONMENT=production` permits it, and containers have already
written these tables. It needs a one-off command into the container
(`railway ssh`, or a second service off the same image), **not** `railway run`,
which executes locally and reintroduces the hazard the guard refuses.

So the sentence for the team is: *the correction is blocked on #328's gap, not
on anybody's access.*
