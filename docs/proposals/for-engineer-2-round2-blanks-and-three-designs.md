# For Yathu — ten Reddit rows, and three designs that wait on them

**Please complete rows 0–12 and 21 of
`fixtures/golden/extraction-reading-round2--labelled-by-yathu.jsonl` before
anything else happens to the pool.** Fourteen rows are entirely unanswered, ten
of them the whole Reddit corpus, and the Reddit claim rows are the only place
`vendor-about-own-product` applies.

**Nothing will be rebuilt until they are in.** A rebuild renumbers rows and
invalidates the 34 you have already done, and the three designs below are all
pool changes. So this is a message first and a design document second.

*Engineer 1 · 2026-08-21 · comparison in
`docs/measurements/round2-two-labellings.md`*

---

## 1 · What is missing, and why those ten rows carry the round

```
yathu   48 rows   14 entirely unanswered

  reddit-thread / claim      4   rows 0-3     <- all of them
  reddit-thread / document   6   rows 4-9     <- all of them
  blog / claim               3   rows 10-12
  blog / document            1   row 21
```

Round 2 exists to separate *who is speaking* from *is the claim sound*, and the
category it added for the first question is `vendor-about-own-product`. The only
claim rows where a vendor is the author are the four Reddit ones — a root post by
`ClaudeOfficial` announcing their own model. All four are blank.

anooj answered them 4 of 4 `vendor-about-own-product`. So **the new category has
one labeller**, and the comparison cannot say whether the distinction is stable
between two people or where it breaks. It is not a disagreement; it is an
absence, and it is the one thing the round was built to test.

Where you did overlap, the news is good: **4 of 5 agreement on
`who_is_speaking`** and 4 of 5 on `is_the_claim_sound` for the blog claim rows,
and **24 of 29 (kappa 0.753)** on document rows. The instrument is working. It
just has not been pointed at the category yet.

Rows 10–12 and 21 are blog and would help too, but 0–9 are the ones that decide
whether round 2 produced a baseline.

### A validator now runs at hand-back

`scripts/check_labelling.py`. It refuses a file rather than letting a comparison
proceed:

```
extraction-reading-round2--labelled-by-yathu.jsonl
  REFUSED: INCOMPLETE: 14 of 48 rows are entirely unanswered -> [0..12, 21]

extraction-reading-round2--labelled-by-anooj.jsonl
  REFUSED: PLACEHOLDER NAME: _meta.labelled_by is 'anon'
```

It checks the labeller name against a placeholder list and against the filename,
completeness per question, answers against each row's own `allowed_answers`, and
row drift against the unlabelled source. The blanks were found by hand three
steps into a comparison, after the numbers had been computed once; this makes
that impossible rather than unlikely.

**The `anon` export is the fourth.** The builders write `labelled_by: None`; the
tool substitutes `anon` when its name is unset, and the tool is not in this
repository so it cannot be fixed from here. Please set the name in the tool — the
validator now catches it, but catching is not fixing, and patching the artifact
afterwards has failed four times.

---

## 2 · Splitting `contains` — existence first, voice second

Taken. Four of the seven round-2 disagreements are this one defect: I built
`contains` by unioning the three who-answers with `none`, so one labeller answers
*"is there a model claim here?"* and the other *"whose voice is this?"*, and every
off-diagonal cell in the document table sits in the `none` row or column.

### Yes, document rows become two questions, like claim rows

```
Q1  does_it_contain_a_model_claim      yes | no
Q2  who_is_speaking                    own-experience
     ASKED ONLY WHEN Q1 = yes          vendor-about-own-product
                                       relayed-from-elsewhere
```

That makes both units two questions, and it makes them **the same second
question** — `who_is_speaking` with identical options on a claim row and a
document row. Which is worth more than the symmetry: agreement on `who_is_speaking`
becomes comparable across units instead of being a different question with a
different option list.

### And yes, `none` belongs to the existence question alone

`none` stops being a member of the voice vocabulary and becomes `no` on Q1. That
is the whole fix: it was never a kind of voice, and putting it in the same list as
three kinds of voice is what made one question do two jobs.

Q2 then has exactly three options on both units, and no option in it answers
*whether* there is a claim.

**The gated second question is the part to be careful about.** It means Q2 is
unanswered on every `no` row, and 16 of anooj's 36 document rows were `none`. So
a validator has to accept "Q2 null because Q1 was no" and refuse "Q2 null because
nobody answered it" — `check_labelling.py` currently refuses both. I will fix that
when the pool is rebuilt, and it is the kind of thing that turns a real check into
a nuisance if it is not fixed at the same time.

### What this does not fix

Two round-2 disagreements were about the option **names** rather than the
question structure, and the split leaves both:

- **row 38** — Modular quoted on **Mojo**, a programming language.
  `vendor-about-own-product` says *product*; Q1 will say *model claim*. A vendor
  talking about a non-model product is `no` on Q1, and the option name still
  invites `yes`. Proposed: rename to `vendor-about-own-model`.
- **row 46** — *"I swapped GitHub Models out … using GPT-5.6 Luna"*: the author's
  own experience of a **service retirement**. Q1 makes this answerable — is a
  service being retired a claim about what a model does? — but somebody has to
  rule on it. My reading is `no`, the same ruling as cost, for the same reason:
  the board holds claims about what a model does. Yours to agree or not.

---

## 3 · Author granularity — three options, costed, no fix taken

The problem, stated once: `author_external_id` is `document.author_id`, so on the
blog corpus it is always `blog:simonwillison.net`. A link blog's body is largely
**somebody else's words**, with the real attribution in the text. Two of seven
disagreements are the row asserting one speaker while the text names another:

```
row 13   row says blog:simonwillison.net   text ends "— Florian Herrengt, AI is
                                            removing the middle class of software
                                            engineering"
row 19   row says blog:simonwillison.net   text ends "— OpenClaw (running Opus 4.6),
                                            hacking an Australian gym-booking website"
                                            ... and the "I tested this" is the AGENT
```

**The row supplies two contradictory attributions and the labellers took different
ones.** That is not a reading disagreement, and it is worth saying plainly that
adding the author was right and adding it at document granularity was not.

### Option A · per-quote attribution

Attach a speaker to each quote rather than to the document.

**Cost: it is the extractor's problem, moved upstream.** Deciding who is speaking
inside a passage is exactly the judgement the extraction prompt is being changed
to make. Building it into the pool means the pool asserts an answer to the
question the pool exists to measure, and a wrong assertion is invisible — a
labeller reading `speaker: Florian Herrengt` will not check it. It also cannot be
done in code without the same model call, and rule 2 puts a model nowhere near
pool construction.

**Verdict: no.** Circular, and it is the `quote_verified` failure shape — a field
that looks like a guarantee and is a guess.

### Option B · parse the byline out of the prose

Extract `— Florian Herrengt, …` and put it on the row.

**Cost: a per-site parser with no verified rule.** The em-dash byline is a
simonwillison.net convention; `contract/sources.yaml` has a `template_block`
mechanism for exactly this kind of site-specific structure, and it took 62 pages
examined and two headings to get the *terminal block* rule right. A byline rule
would need the same evidence and would hold for one feed. Worse, it is
under-determined: row 19's byline is `— OpenClaw (running Opus 4.6)`, which names
an **agent** rather than a person, and row 13's names a person **and** an article
title. A parser that produced `OpenClaw` would be correct and would not answer
"who is speaking" in any sense the taxonomy uses.

**Verdict: real but narrow.** It buys one feed and one convention, and it asserts
a speaker again.

### Option C · flag the marker, let the labeller judge

**This is the one I would take.** Do not assert a speaker. Detect that the
document *contains an attribution marker* and say so on the row:

```
"author_external_id":        "blog:simonwillison.net",
"author_role":               "article author",
"contains_attribution_marker": true,
"attribution_marker_text":   "— Florian Herrengt, AI is removing the middle class
                              of software engineering",
"attribution_note":          "This document carries its own attribution line.
                              The author field above is the DOCUMENT's author -
                              who published it. The passage may be somebody
                              else's words. Judge from the text."
```

**Cost: near zero, and it is honest about what it does not know.** The detector is
a line-anchored regex for a leading em-dash or `—`/`--` at the start of a line,
which is the same shape as `strip_template_block` and needs no per-site rule to be
*useful* — a false positive shows the labeller a line they can dismiss, and a
false negative leaves them where they are today. Nothing is asserted, so nothing
can be wrong in a way that hides.

**What it costs that the others do not:** it does not resolve the disagreement, it
makes it visible and deliberate. Rows 13 and 19 would still be judged
differently by two people — but they would be disagreeing about a text both had
been told to read, which is evidence about the readers rather than about the pool.
That is the whole distinction the last three rounds have turned on.

I would also add one line to the `who_is_speaking` help: *"the author field names
who PUBLISHED the document. If the passage carries its own attribution, the
speaker is whoever the text says."*

---

## 4 · Hypotheticals — proposed wording, not taken

Row 14, and it is the single non-`supported` answer anywhere in anooj's set:

> *"Neither of you has any idea whether any of it is true but Claude seems very
> confident."*

The document is a **second-person hypothetical**: *"But then users start to report
a weird bug… You go talk to the person who worked on this feature… You sit next to
each other watching an endless wall of text."* Nobody observed this; it is an
illustration.

`not-an-observation` is defined as *"states an intention, a plan or a commitment
rather than something observed"*. A hypothetical is none of those three and is
also not an observation, so both readings were defensible and the option's
definition was the reason.

Three ways to word it. **My preference is (2).**

**(1) Widen the existing option.**

> `not-an-observation` — the sentence does not report something that happened.
> An intention or a commitment (*"We'll keep refining the safeguards"*), or a
> hypothetical, illustration or scenario (*"You sit next to each other watching an
> endless wall of text"*).

Cheapest, and it merges two things that behave differently downstream: a vendor
commitment is about a real model's future, an illustration is about no model at
all.

**(2) Split it in two.** Preferred.

> `states-an-intention` — a plan, a promise or a commitment about what will
> happen. *"We'll keep refining the safeguards to reduce false positives."*
>
> `hypothetical-or-illustrative` — a scenario, an example or a narrative rather
> than a report of something that occurred. Second-person *"you"* and
> present-tense storytelling are the usual tells. *"You sit next to each other
> watching an endless wall of text appear on the screen."*

Five options on Q2 instead of four. It costs agreement at small n — every added
category does — and it separates two things that a downstream weighting rule
would want to treat differently: a commitment is weak evidence about a real
model, an illustration is not evidence about a model at all.

**(3) Make it a soundness verdict of `no-claim-asserted`.**

> the sentence does not assert anything about a model, whether because it is
> hypothetical, an intention, or a description of something else

Collapses (1) and (2) and the out-of-scope case into one, which is fewer
categories and loses the reason. I do not prefer it; it is the option that will
look attractive when kappa is low.

**Why (2).** The two rounds so far have both been decided by an option carrying
two facts — round 1's `ambiguous`, round 2's `contains`. Merging a commitment
with a hypothetical is the same move a third time.

---

## 5 · The order, so nothing invalidates anything

```
1  Yathu completes rows 0-12 and 21          <- nothing else moves until this
2  compare round 2 properly, with the Reddit
   corpus in, and see whether
   vendor-about-own-product holds
3  rebuild the pool: contains split into
   existence + voice, `none` moved to
   existence, vendor-about-own-model renamed,
   attribution marker flagged, Q2 gains the
   hypothetical option
4  fix check_labelling.py to accept a null
   gated question, at the same time as (3)
5  round 3, which is again NOT comparable to
   round 2 - five options on Q2 against four
```

Step 3 is a rebuild and renumbers rows, which is why step 1 is first and why I
have not touched the pool. Steps 2 and 3 are both yours to sign off; I have
written none of it into `fixtures/golden/` yet.
