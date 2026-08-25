# 697KB of retained article text is on `origin/main`, and I put it there

**A policy breach, not an oversight.** `.gitignore` says retained full text stays
out of git "as firmly as the store proper". PR #137 merged **seven files carrying
whole documents** — 697,093 bytes, 222 embedded documents — and I opened that PR.

```
capability-choice-round3--unlabelled.jsonl          244,090 bytes   36 documents
extraction-reading-round2--labelled-by-anooj.jsonl  130,999          48
extraction-reading-round2--labelled-by-yathu.jsonl  130,738          48
extraction-reading-round2--unlabelled.jsonl         129,647          48
extraction-reading-baseline--unlabelled.jsonl        20,262          14
pool--labelled-by-anooj1.jsonl                       20,679          14
pool--labelled-by-yathu.jsonl                        20,678          14
                                                    -------         ---
                                                    697,093         222
```

**It is not only the pools.** The four *labelled* files carry the document text
too — the embedding is in the row shape, so every export of it inherits the
problem.

*Engineer 1 · 2026-08-24 · reads only*

---

## Why it is a breach and not a judgement call

`.gitignore` states the rule, with a worked example of it being violated before:

> *"A measurement's local corpus, same rule. … that is retained full text, so it
> stays out of git as firmly as the store proper. `git add -A` swept it in once —
> this is why the pattern is here and not in the store."*

So the policy exists, it is written down, it names the exact mechanism that
breached it last time, and I breached it by a different route: an explicit
`git add` of files I built, in a PR I wrote and merged. The rule was not unclear
and I did not check it against what I was adding.

The content is Simon Willison's articles and Reddit comments in a repository that
is not ours alone.

## What removing it costs

| | |
|---|---|
| **HEAD** | easy. Rewrite the seven files without `source_document_text`, one commit. |
| **history** | not easy. Seven blobs across the #137 merge and its branch commits. Removing them means `filter-repo` or a squash, a force-push to `main`, and every clone re-based — on a repo with ~50 live branches and a second engineer. |
| **the labels** | **nothing.** See below. |

## The labels survive, and this is the part that decides the fix

**Labels are keyed by `row_index`, and every row already carries
`document_id`:**

```
row keys: row_index · unit · corpus · questions · allowed_answers · answers
          document_id · author_external_id · author_role · source_document_text
```

`answers` is bound to `row_index`. `source_document_text` is *shown to the
labeller* and is read by nothing downstream. So:

**Substituting `document_id` + offsets does NOT invalidate any label.** Two
people's judgements reference rows, not text, and the rows keep their identity.
`scripts/check_labelling.py` already validates a returned labelling on
`row_index`, `document_id` and `quote` — none of which changes.

## But the labeller cannot resolve a reference today, and that is why the text is there

I embedded the document because **the person labelling has no way to fetch it.**

- the raw store is machine-local (`RAW_STORE_PATH=./raw_store`), gitignored, and
  the reddit/github payloads are not even on this machine — measured, 33 of 33
  unreadable here;
- the labeller tool is **not in the repository** on any branch;
- and a row without its document is unlabellable: *"which capability is this
  quote about"* cannot be answered from a 200-character quote alone, which is the
  whole reason round 3 carries the document.

So the reference-plus-offsets design needs one of:

1. **the labeller resolves from the store**, which means the labeller runs on a
   machine that has the store — true for us, false for a third labeller;
2. **the pool ships out-of-band** — the JSONL in git carrying references, the
   text delivered alongside and never committed. This is the same shape as the
   Reddit-handle ruling inverted: there, don't store, re-derive at render time;
   here, don't store, deliver at label time;
3. **quote plus a wider window** rather than the whole document — enough to
   judge, bounded, and still retained text in smaller quantity, so it reduces
   rather than resolves.

**(2) is the one I would propose**, and it is not mine to decide alone: it makes
the repository copy of a pool unusable without a companion artifact, which is a
real cost to whoever picks it up next.

## What I am not doing

**Not rewriting history, and not quietly stripping HEAD.** A force-push to `main`
on a shared repo with a second engineer's branches on it is not a call I should
make from inside a report, and stripping HEAD alone would leave the blobs in
history while making the pools unlabellable — the worst of both.

Raised as its own item, with the cost stated, for a decision.
