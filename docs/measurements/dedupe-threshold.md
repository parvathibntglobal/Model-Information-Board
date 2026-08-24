# Dedupe — the 200-token threshold, measured

**The number survived. Its justification and its meaning both changed, and the
two-method design did not survive at all.**

*Engineer 1 · 6,824 stored documents · 79 ground-truth duplicate pairs · 2026-08-17*

> `collect/CLAUDE.md` specified MinHash + LSH below ~200 tokens and simhash
> above, on the reasoning that simhash is built for long documents. **The data
> does not support the split.** MinHash separates better at every length,
> including the long bands simhash was to own.

---

## 1 · Ground truth, and why it took two attempts

FR-16's acceptance is *"seed a known syndicated set"*. A constructed duplicate is
a duplicate the matcher was designed to catch, so the pairs here are real.

**True pairs** come from two sources, neither of which reads the text:

- **crosspost markers** — the platform declaring one post a copy of another (27 in the corpus)
- **same author + same title + different subreddit, within 48 hours**

**False pairs** are documents with **different authors and different titles**,
which is also independent of the text.

### Both sets were contaminated on the first run, and the fix is the interesting part

- The **false** set drew random pairs from a pool containing **1,112 exact-duplicate groups**, so it contained genuine duplicates — one at Hamming distance 0 and Jaccard 1.00. Requiring different authors and different titles removed them.
- The **true** set matched on author and title alone, which caught **recurring series**: `models, providers & plans megathread — june 2026` is posted by one author to several subreddits every month. Two different months are not a duplicate. The 48-hour window excludes them, and it is what removed "true" pairs sitting at Hamming 27.

Without the time window the measurement would have concluded that duplicates are
hard to detect, on evidence that was really measuring monthly megathreads.

---

## 2 · The curve

**MinHash — Jaccard over 5-character shingles, 128 permutations.** Higher is more similar.

| tokens | n true | true min/med/max | n false | false min/med/max | separated |
|---|---|---|---|---|---|
| 0–50 | 13 | 0.04 / 0.30 / 1.00 | 157 | 0.00 / 0.00 / 0.13 | **no** |
| 50–100 | 2 | 0.95 / 1.00 / 1.00 | 1 | 0.05 / 0.05 / 0.05 | yes, n=2 |
| 100–200 | 4 | 0.41 / 1.00 / 1.00 | 99 | 0.02 / 0.05 / 0.10 | yes, n=4 |
| 200–400 | 20 | 0.93 / 1.00 / 1.00 | 237 | 0.02 / 0.05 / 0.12 | **yes** |
| 400–800 | 21 | 0.62 / 0.98 / 1.00 | 230 | 0.00 / 0.07 / 0.16 | **yes** |
| 800+ | 19 | 0.77 / 0.99 / 1.00 | 227 | 0.01 / 0.09 / 0.24 | **yes** |

**simhash — Hamming distance out of 64.** Lower is more similar.

| tokens | true min/med/max | false min/med/max | margin |
|---|---|---|---|
| 0–50 | 0 / 12 / 27 | 22 / 32 / 39 | **none** |
| 50–100 | 0 / 3 / 3 | 23 / 23 / 23 | 20 bits, n=2 |
| 100–200 | 0 / 2 / 24 | 22 / 31 / 41 | **none** |
| 200–400 | 0 / 0 / 7 | 20 / 30 / 42 | 13 bits |
| 400–800 | 0 / 1 / 18 | 19 / 31 / 43 | **1 bit** |
| 800+ | 0 / 2 / 11 | 16 / 28 / 40 | 5 bits |

### simhash was given a fair hearing

Character shingles handicap simhash — it is conventionally used with word-level,
frequency-weighted features. Re-run as **word 3-grams, tf-weighted**:

| tokens | margin (char shingles) | margin (word 3-grams, tf) |
|---|---|---|
| 0–50 | none | none |
| 100–200 | none | 3 bits |
| 200–400 | 13 | 7 |
| **400–800** | **1** | **0** |
| 800+ | 5 | 12 |

Better in two bands, worse in two, and **zero margin at 400–800 tokens under the
conventional form.** Against MinHash's margin of 0.46 on a 0-to-1 scale in that
same band, this is not close.

**So there is one method. `document.simhash` stays NULL — a measured decision,
not an unimplemented column,** and `tests/test_dedupe.py` asserts no simhash
implementation exists so nobody restores one believing it was merely unfinished.

---

## 3 · The floor, the band, and the judgement inside it

**`min_tokens_for_signature: 200` is a floor, not a method switch.** Below it no
signature is computed, because neither method separates duplicates from
strangers.

**The band the data supports is (50, 200).** Failure is demonstrated below 50;
success is demonstrated at 200. The two bands between carry **n=2 and n=4**,
which is too thin to claim either way — so every value in that band is consistent
with the evidence and the choice inside it is judgement.

The judgement, from the lane's own rule:

> `collect/CLAUDE.md` — *"Over-clustering is worse than under-clustering. Merging
> two genuinely independent reports destroys corroboration, which is the only
> thing separating 'someone said this' from 'this is probably true'."*

A **higher** floor merges fewer documents, so conservative means high, and 200 is
the top of the band.

It is the same number `collect/CLAUDE.md` already carried, and **it does not mean
the same thing.** The old 200 chose between two algorithms. This 200 is the point
below which neither works.

`similarity_threshold: 0.80` sits inside a wide gap rather than on a boundary —
the tightest passing band had true pairs from 0.62 and strangers to 0.16.

---

## 4 · What happens below the floor: certainty, not similarity

Two mechanisms that do not need a signature, so the floor does not apply to them:

- **platform-declared crossposts** — 27 in the corpus, with parent ids
- **exact normalised match** — with one exclusion, below

### The sentinel trap, which is why exact match is not simply safe

`[removed]` is the body of **57 distinct comments** in one 14-thread corpus.
`[deleted]` is the body of **38**.

Merging on identical text would collapse each set into a single document and
destroy the tree those comments sit in, along with every voice count drawn from
it. **Identical text is not identity**, and `signature.is_sentinel` names those
bodies so no mechanism merges them — not exact match, and not even a crosspost
declaration.

This was found by surveying the corpus, not by reasoning about it.

---

## 5 · The acceptance test uses a real syndicated set

FR-16 asks for one. The corpus has **51 titles appearing across more than one
subreddit**, and the case used is:

| post | subreddit | body chars | score |
|---|---|---|---|
| `t3_1tgecrq` | r/LocalLLaMA | 2,683 | 904 |
| `t3_1tged8r` | r/LocalLLM | 2,683 | 449 |
| `t3_1tgee4b` | r/opencodeCLI | **2,805** | 242 |
| `t3_1tget4p` | r/ollama | 2,683 | 445 |

One author, four subreddits, 25 minutes apart. **Three bodies are byte-identical
and the fourth is not**, so exact matching finds **two** groups where the answer
is one — which is precisely what makes the signature load-bearing rather than
decorative. Checked in at `fixtures/reddit/syndication-4-subreddits.json`.

The earliest also happens to carry the highest score, so the canonical-selection
test pins the **rule** rather than the coincidence: a later, more popular copy
must not take over as the original.

---

## 6 · What this does not say

- **Nothing about blogs.** All 79 true pairs are Reddit self-syndication and crossposts. The corpus contains **no blog syndication at all** — 111 articles from 9 feeds, zero duplicates spanning document kinds. FR-16's own example is *"one blog syndicated four times"*, and that channel is unmeasured here.
- **Nothing reliable about 50–200 tokens.** n=2 and n=4.
- **Nothing about cross-platform duplication.** Zero exact-duplicate groups spanned two document kinds, so the GitHub-to-Reddit case that FR-17 is about has no instance here either.
- **Nothing about comments within one thread.** Most are below the floor, so they are deduplicated by exact match and crosspost only.

## 7 · What would revise it

- **True pairs in the 50–200 band.** If pairs at 60 tokens separate as cleanly as those at 200, the floor should come down and far more documents become deduplicable — most Reddit comments live below 200 tokens.
- **Blog syndication**, once more feeds are harvested. The channel FR-16 names is the channel with no evidence here.
- **A larger true set generally.** 79 pairs is thin, and three of six bands rest on fewer than five.
