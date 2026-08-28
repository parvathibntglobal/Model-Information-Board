# Seat every derived form for the eleven: 612 candidates, and it needs your review not my command

**I cannot seat these and should not be able to.** `tracked_load.read_manifest`
requires `reviewed_by` and binds each seat to a content hash of the reviewed
artifact — so adding forms to an already-seated model *invalidates the hash its
existing review is bound to*, which is the guard working exactly as designed.
This is the artifact for that review.

*Engineer 1 · 2026-08-28*

---

## 1 · What each new form recovers, measured

Every form is what `propose.py` already derives — `mechanical_variants` plus
`rule_variants`. Nothing here is invented. The counts are bucket-A candidates from
the 2026-08-28 model-only sweep that the form matches and the queried surface did
not (`docs/measurements/why-1771-candidates-failed-subject.md`).

```
model                          seated  new   distinct   the forms, and what each matches
                                             recovered
anthropic/claude-fable-5            0    6         96   fable 5            94
                                                        fable-5             9
                                                        claude-fable-5      4
                                                        fable5              1
anthropic/claude-haiku-4.5          3    4         99   claude haiku 4.5   97
                                                        haiku-4.5           2
anthropic/claude-opus-4.6           3    4         84   claude opus 4.6    84
anthropic/claude-opus-4.8           4    4         54   claude opus 4.8    91
                                                        opus-4.8            1
anthropic/claude-sonnet-4.6         3    4         67   claude sonnet 4.6  67
anthropic/claude-sonnet-5           3    4         24   claude sonnet 5    24
google/gemini-3.7-flash             0    3          0   — its surface was right
openai/gpt-5.6-luna                 0    3         58   gpt 5.6 luna       52
                                                        gpt-5.6-luna        7
openai/gpt-5.6-sol                  0    3          0   — 0 candidates to
                                                          recover; see §4
openai/gpt-5.6-sol-pro              0    3         11   gpt 5.6 sol pro     8
                                                        gpt-5.6-sol-pro     3
qwen/qwen3.8-27b                    0    3        119   qwen3.8-27b       119
                                                  ----
                                                   612
```

**`distinct` is the number to read.** The per-form counts are rows in the sweep
file and a candidate retrieved by three surfaces appears three times; `distinct`
counts posts. `opus 4.8`'s `claude opus 4.8` matches 91 rows and 54 distinct posts.

## 2 · The five already-seated models gain 328 candidates, and that is the case

```
claude-haiku-4.5      99
claude-opus-4.6       84
claude-sonnet-4.6     67
claude-opus-4.8       54
claude-sonnet-5       24
                     ---
                     328
```

**`opus 4.8` scored 84.6% subject verification — the best in the run — and still
lost 54 distinct candidates.** It has four seated surfaces and none of them is
`claude opus 4.8`, the fully-spaced form with the family prefix. That form alone
accounts for every one of the 54.

So this is **not** an alias-coverage problem that seating six unseated models
fixes. Four of the five best-performing surfaces in the run are missing a form
that people demonstrably write, and the pattern is the same one every time:

```
seated             claude-opus-4.8, opus 4.8, claude 4.8, anthropic/claude-opus-4.8
what people write  claude opus 4.8      <- fully spaced, family prefix intact
missing            exactly that
```

## 3 · Two forms that carry most of it, and they point opposite ways

**`qwen3.8-27b` recovers 119 — and it is hyphenated.** The vendor markets
`Qwen3.8-27B` and people copy it verbatim. The *canonical id* was the correct
surface all along and was never seated.

**`claude haiku 4.5` / `claude opus 4.6` / `claude sonnet 4.6` recover 97, 84 and
67 — and they are fully spaced.** Anthropic markets *Claude Haiku 4.5* and people
write it out.

**So there is no global spacing rule and there should not be one.** The surface
people write is the vendor's own marketing form, the convention differs by vendor,
and the only safe policy is to seat every derived form and let `sieve_any` match
whichever appears. That is cheaper than a per-platform renderer and it is what the
measurement supports.

## 4 · Two zeroes that are not the same zero

`gemini-3.7-flash` recovers 0 because **its surface was already right** — a real
zero.

`gpt-5.6-sol` recovers 0 because **it returned 0 candidates**, and it returned 0
because of the transient `data not found` response now fixed in
`collect/adapters/reddit.py`. There was nothing to recover, not nothing to find.
Rule 6 applies to my own table: those two zeroes mean opposite things and this row
says which.

## 5 · What the review has to decide, and why it is not a formality

`load-tracked-set` verifies each seat's content hash against the artifact before
writing, and `model_alias` is **append-only** — `_sync_alias` supersedes by
setting `valid_until` rather than deleting, so a wrong surface is permanent and
visible rather than removable.

So the review is deciding two things:

**Which forms are real.** `claudefable5` and `fable5` recover 1 candidate between
them. `anthropic/claude-fable-5` recovers 4 and is a canonical id nobody types —
I have excluded canonical-id forms from the run set for that reason, and the
manifest should too.

**Whether the five seated models get a new review.** Adding a form changes their
artifact and therefore their hash. The alternative — leaving them as they are —
costs 328 candidates, which is more than the six unseated models' 284.

## 6 · What I did instead of seating

Re-ran the sweep on **all 51 derived forms as run-local surfaces**, so the ~315
projection becomes a measurement without touching the registry. 357 requests, 14.3
minutes against a 35-minute ceiling, 0.036% of quota. The registry write waits for
you; the measurement did not have to.
