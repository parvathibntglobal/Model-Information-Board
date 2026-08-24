# Round 2: the split you asked about was never tested, and all seven disagreements are the option set again

**Yathu labelled no Reddit rows at all — 4 of 4 claim rows and 6 of 6 document
rows blank. `vendor-about-own-product` on claim rows has one labeller, so the
corpus split does not break; it was never exercised.**

Where they did overlap: claim rows n=5, document rows n=29. And **0 of 7
disagreements is about what the text says** — the same result as round 1, which
means the vocabulary is still not settled and the prompt work waits again.

Two new defects, both mine: the `contains` question mixes provenance with
existence, and the author field is per-document on a link blog that quotes other
people.

*Engineer 1 · 2026-08-21 · neither labelling is an answer key; no extractor
output read while comparing. Run in `round2-two-labellings.txt`.*

---

## 0 · Before any number: what these cannot be compared to

**Round 2 is not a trend against round 1.**

```
round 1   one question,  4 options   ->  4 cells
round 2   two questions, 3 and 4     -> 12 cells
```

More categories cost agreement at small n before they buy any. A figure here
placed beside round 1's 0.421 reads as a decline in the labellers when it is a
change in the instrument.

**And round 1's claim-row figure was retired, not superseded.** Three of its four
distinct disagreements were quotes from a vendor-authored root and no row carried
the author, so those labels were evidence about the pool rather than about the
readers. **0.149 was withdrawn; nothing here improves on it.**

Everything below is split by unit and by question, never pooled. Round 1 pooled
and hid 0.149 against 0.739.

---

## 1 · Completeness, which is the first finding

| | rows | fully blank |
|---|---:|---:|
| anooj | 48 | **0** |
| yathu | 48 | **14** |

Yathu's blanks, by corpus and unit:

```
reddit-thread / claim      4   <- all of them
reddit-thread / document   6   <- all of them
blog / claim               3
blog / document            1
```

**The entire Reddit corpus is unlabelled by Yathu.** Comparable rows per question:

| question | askable | both answered | anooj only |
|---|---:|---:|---:|
| `who_is_speaking` | 12 | **5** | 7 |
| `is_the_claim_sound` | 12 | **5** | 7 |
| `contains` | 36 | **29** | 7 |

---

## 2 · The split you asked about: untested, not broken

Your account of your own claim rows checks out exactly:

```
anooj   reddit-thread  n=4   who = {vendor-about-own-product: 4}   sound = {supported: 4}
        blog           n=8   who = {own-experience: 8}             sound = {supported: 7,
                                                                             not-an-observation: 1}
        -> 4 of 4, 8 of 8, 11 of 12 supported.  Confirmed.
```

Yathu's:

```
yathu   reddit-thread  n=4   who = {None: 4}                       sound = {None: 4}
        blog           n=8   who = {None: 3, own-experience: 4,    sound = {None: 3, supported: 5}
                                    relayed-from-elsewhere: 1}
```

**`vendor-about-own-product` was never used on a claim row by Yathu, because the
only claim rows where it applies are the four Reddit ones and all four are
blank.** On the blog claim rows they overlap on 5, and agree on 4 of 5.

So the answer is neither of the two you framed. The distinction is **not stable
between two people and not shown to break** — it has one labeller. The clean half
of your split (8 of 8 blog `own-experience`) is corroborated 4 of 4 where Yathu
answered; the half that carries the whole point of the new category is untested.

---

## 3 · Claim rows, two questions, reported separately

### `who_is_speaking` — n=5

```
  raw agreement 4/5 = 80.0%      expected by chance 0.800      kappa 0.000

  anooj \ yathu        own-exp      relayed
  own-exp                    4            1
  relayed                    0            0
```

### `is_the_claim_sound` — n=5

```
  raw agreement 4/5 = 80.0%      expected by chance 0.800      kappa 0.000

  anooj \ yathu      supported   not-an-obs
  supported                  4            0
  not-an-obs                 1            0
```

**Kappa 0.000 at 80% raw agreement is the small-n paradox, not disagreement.**
Both marginals sit almost entirely in one category, so expected agreement equals
observed agreement and the coefficient collapses. At n=5 with one off-diagonal
cell there is no coefficient worth quoting. **These are lists, not measurements.**

### The case round 2 was built to make visible, and it fired

**2 of the 5 claim rows agree on one question and differ on the other** — rows 13
and 14. In round 1 those two rows would have been a single forced choice and one
of the two facts would have been lost. That mechanism works.

---

## 4 · Document rows, one question — n=29

```
  raw agreement 24/29 = 82.8%      expected by chance 0.302      kappa 0.753

  anooj \ yathu        own-exp   vendor-own      relayed         none
  own-exp                    8            0            0            0
  vendor-own                 0            1            0            0
  relayed                    2            0            6            0
  none                       1            1            1            9
```

All 29 are blog. There is no Reddit document comparison, so the per-corpus split
is the same table.

Document rows agree better than claim rows again — the round-1 pattern holds at
82.8% against 80% raw, and with a coefficient that means something (0.753) rather
than one that collapses.

**Every one of the five off-diagonal cells is in the `none` row or column.** That
is the shape of §5's first defect.

---

## 5 · All seven disagreements, and 0 of 7 is about the text

Same result as round 1's 0 of 4. In every case the two labellers agree on what the
sentence says and differ on which box it goes in.

### Defect A · `contains` mixes provenance with existence — 4 of 7

`contains` asks *"what kind of claim about a model does it contain, if any"*, and
I built its options by unioning the three who-answers with `none`. So a labeller
answering **"is there a model claim here?"** and a labeller answering **"whose
voice is this?"** produce different labels for the same reading. This is round 1's
`nothing-here`-versus-`relayed` collision, which I fixed on claim rows and
recreated at the document unit.

| row | anooj | yathu | the text |
|---|---|---|---|
| 33 | `none` | `relayed-from-elsewhere` | Dario Amodei on public trust in AI — quoted, and about no model's behaviour |
| 36 | `relayed-from-elsewhere` | `own-experience` | *"Qwen 3.8 27B scores 52 on the Artificial Analysis Intelligence Index (via)"* **and** *"Qwen 3.8 27B is a truly astonishing model."* — a relayed benchmark and the author's own verdict, in one document, single-select |
| 38 | `none` | `vendor-about-own-product` | Modular quoted on **Mojo**, a programming language. Vendor about their own product, and not a model |
| 46 | `none` | `own-experience` | *"my GitHub Actions run … failed"*, *"I swapped GitHub Models out … using GPT-5.6 Luna"* — the author's own experience of a **service retirement** |

Rows 38 and 46 are the sharpest: `vendor-about-own-product` says *product*, and
the question says *a claim about a model*. Mojo is a product. A service being
retired is not model behaviour. The option set admits both and the question
excludes them.

### Defect B · the author field is per-document, and a link blog quotes other people — 2 of 7

I added `author_external_id` because round 1's disagreements turned on not knowing
who wrote a sentence. It is `document.author_id`, so on this corpus it is always
`blog:simonwillison.net` — and a link blog's body is largely **somebody else's
words**, with the real attribution in the text.

| row | anooj | yathu | the conflict |
|---|---|---|---|
| 13 | `own-experience` | `relayed-from-elsewhere` | row says `blog:simonwillison.net`; text ends *"— Florian Herrengt, AI is removing the middle class of software engineering"* |
| 19 | `relayed-from-elsewhere` | `own-experience` | row says `blog:simonwillison.net`; text ends *"— OpenClaw (running Opus 4.6), hacking an Australian gym-booking website"* — the *"I tested this"* is an agent, not the blogger |

**The row supplies two contradictory attributions and the labellers took
different ones.** That is not a reading disagreement. The fix was right in
principle and wrong in granularity: a per-document author cannot describe a quoted
excerpt, and on a link blog most excerpts are quoted.

### Defect C · `not-an-observation` covers commitments but not hypotheticals — 1 of 7

Row 14, and it is the single non-`supported` answer in anooj's whole set:

> *"Neither of you has any idea whether any of it is true but Claude seems very
> confident."*

The document is a **second-person hypothetical** — *"You go talk to the person…
You sit next to each other…"*. anooj read it as not an observation; Yathu read the
claim as supported by the sentence. Both are defensible because
`not-an-observation` is defined as *"states an intention, a plan or a commitment"*
and a hypothetical scenario is none of those while also not being an observation.

**Note this row also produced the who/sound split** — they agree it is
`own-experience` and differ on soundness. The two-question structure recorded
exactly the thing round 1 would have collapsed.

---

## 6 · What this means for the prompt work

**It waits again, and for a shorter list than last time.**

Round 1: 4 distinct disagreements, 0 about the text, 5 option-set defects.
Round 2: 7 disagreements, 0 about the text, **3 defects, 2 of them new and both
introduced by round 2's own fixes.**

That is progress in the sense that matters — the claim-row taxonomy that carries
the relayed/first-hand distinction produced 4 of 5 agreement and a working
two-question split — and it is not a baseline yet, because:

1. **The Reddit corpus has one labeller**, and it is the only corpus where
   `vendor-about-own-product` applies on a claim row. Without it the new category
   has no inter-rater evidence at all.
2. **`contains` needs splitting into two questions**, the same way claim rows
   were. *Is there a claim about a model here?* then *whose voice is it?* Four of
   seven disagreements go away by construction.
3. **The author field needs to be per-quote, or the row needs to carry the text's
   own attribution.** On a link blog `document.author_id` names the curator, not
   the speaker.
4. **`not-an-observation` needs to cover hypothetical and illustrative prose**,
   or that needs its own option.

None of those is a prompt change and all of them are upstream of one. And the
same discipline applies to whatever comes next: 12 cells at n=5 is a list, and a
third round with a fifth option set will not be comparable to this one either.

---

## Housekeeping

`extraction-reading-round2--labelled-by-anooj.jsonl` carries
`labelled_by: "anon"` in `_meta` and on all 48 rows — fourth export running with
the tool's labeller name unset. The filename says `anooj`. Still not corrected in
the artifact; the name needs setting in the tool.
