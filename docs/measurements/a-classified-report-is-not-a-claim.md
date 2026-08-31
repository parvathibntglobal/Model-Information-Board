# A classified capability report is not a `claim`, and the blocker is not her table

**Two questions answered from the schema rather than from opinion.** Classification
can run today and its output can be held in a file and inserted later — with one
fix that costs nothing now and would have cost $0.60 later. But a classified report
with a verified quote is **not** a claim, it is missing six required fields, and two
of those are structurally unavailable rather than merely unassigned.

*Engineer 1 · 2026-08-28*

---

## 1 · Is a classified report a `claim`? No, and not by a narrow margin

`claim` has 15 columns that are `NOT NULL` with no default. Against what the
classification pass produces:

```
HAVE                     document_id        FK, and the document exists
                         quote              verbatim span
                         quote_verified     and claim_verified_ck REQUIRES true,
                                            so only the 187 verified would ever
                                            be insertable — the 68 failures are
                                            refused by the schema, correctly
                         capability_key     FK to capability; the twelve exist
                         extractor_model    google/gemini-2.5-flash
                         pipeline_version   collect-0.1.0

DERIVABLE                model_version_id   known — each document was queried for
                                            a specific model
                         specificity        from the surface that retrieved it
                         taxonomy_version   from contract/capabilities.yaml

NOT ASSIGNED             polarity           the prompt never asked. A capability
                                            report with no polarity cannot reach a
                                            cell: `cell.positive`/`negative` are
                                            counts of it
                         condition_bucket   never asked
                         relevance          central | passing — never asked
                         evidence_tier      never asked
                         source_comment_id  the classifier read the WHOLE POST;
                                            there is no comment to point at

STRUCTURALLY ABSENT      thread_context_id  FK to thread_context, and NONE OF
                                            THESE DOCUMENTS HAS ONE
                         quote_flat_offset  int4range, from the offset map
                         quote_raw_offset   int4range, from the offset map
```

**The last group is the answer.** The four not-assigned fields are a prompt that
did not ask; another pass could ask. The three structurally absent ones cannot be
filled by any prompt:

`thread_context_id` requires a `thread_context`, and the model-only sweep wrote
`document` rows only — nothing assembled them. And `collect/CLAUDE.md`'s first rule
says the offset map *"is roughly ten lines while you are already walking the thread
tree, and impossible to reconstruct afterwards. Every quote extracted without it
has to be re-run."*

**So the blocker on storing this as claims is `assemble`, not `capability_candidate`.**
A verified quote with no offsets is exactly the state that rule warns about, and
inserting one would need the two range columns to be nullable — which would break
the guarantee `quote_verified` exists to make, because a verified quote whose
position nobody recorded cannot be re-checked against the document.

### And one thing the schema gets right that I would have got wrong

`claim_verified_ck CHECK (quote_verified = true)` means **the 68 failed quotes can
never be stored at all** — the schema refuses them rather than storing them flagged.
So the 34 genuine fabrications and the 34 encoding near-misses are equally
unstorable, which is why `ExtractionRun.rejected` is the only place that count
lives, and why separating the two causes there matters more than I said in
`for-engineer-2-two-verification-failures-not-one.md`. There is no second copy.

## 2 · Can classification run before `capability_candidate` lands? Yes

Nothing in the insert path needs the table to exist at classification time. Every
field `capability_candidate` proposes is either on the document or a property of
the run:

```
proposed_key, definition   from the model's answer
document_id                the document, and documents are not deleted
quote, quote_verified      from the answer plus the substring check
proposer_model             THE RUN
prompt_label               THE RUN
pipeline_version           THE RUN
```

**The one thing that would have forced a re-run was the last three.** The output
rows recorded token counts and not the model, the prompt variant or the pipeline
version — so a file held for a week would have needed somebody to remember which
prompt produced it, and "which prompt" is the whole point of a proposal's
provenance.

Fixed: every row now carries `proposer_model`, `prompt_label` and
`pipeline_version`. `prompt_label` is explicit and dated —
`capability-classification/withheld-keys/2026-08-28` — because two variants ran
today over the same 358 documents and a proposal from one is not a proposal from
the other.

**Cost of finding this now rather than later: nothing. Cost of finding it later:
$0.60 and a day.**

## 3 · The run in flight, and what it is missing

The withheld-list run started before that fix, so its rows carry no run identity.
It is recoverable without re-running — the model and pipeline version are known
out of band and the variant is known from the invocation — so a **sidecar
manifest** beside the JSONL preserves it:

```
classification_withheld.jsonl          the rows
classification_withheld.manifest.json  proposer_model, prompt_label,
                                       pipeline_version, started_at, cap_usd
```

That is a worse arrangement than the inline fields and it is good enough for one
file. The next run does not need it.

## 4 · What is storable today, and it is less than it looks

**Nothing from the classification.** Not because of `capability_candidate` — which
had zero rows to hold from the first pass anyway — but because `claim` needs a
`thread_context_id` and an offset map that do not exist for these documents.

**What that argues for:** `assemble reddit` over the model-only corpus, which is
built and wired and has not been run against these 1,507 new documents. That is
the step that makes any of this storable, and it costs nothing but time.
