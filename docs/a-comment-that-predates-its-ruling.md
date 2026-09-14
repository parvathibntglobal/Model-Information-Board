# A comment that predates its ruling, in a file nobody touched afterwards

**2026-09-14. A defect class with no detector, found after it cost fourteen days
of unassemblable documents. Written as a class rather than an incident, because
the instance is already fixed and the class is not.**

---

## 0 · The shape

```
1.  A comment is written explaining why the code does X.
2.  Hours later, a ruling decides NOT-X, for reasons the comment never
    addresses.
3.  The ruling's own consequences land: the data is repaired, the downstream
    stage is rewritten, a test is added.
4.  The file carrying the comment is not among them, because the ruling
    changed where the work happens, not this file's call signature.
5.  Nothing ever touches that file again.
```

Step 5 is the trap. **The comment is now the only account of that decision that
a reader will find at the place they are standing**, and it argues the losing
side, fluently, with a real hazard and a real example. It does not look stale.
It looks like the reason.

**It is worse than a wrong comment.** A comment that contradicts its own code
is caught the first time somebody reads both. This one *matches* its code
perfectly. The code and the comment agree with each other and disagree with a
ruling filed elsewhere, and there is no third thing present to break the tie.

---

## 1 · The instance, with times

`collect/ops/sweep_reddit.py` stored the Reddit payload at `text_ref`. On
2026-08-28 that was changed to store prose, under a comment that is *correct
about its hazard*:

> *"This stored `json.dumps(post.raw)` until 2026-08-28, which made `text_ref`
> point at a JSON envelope. `assemble_*` passes that straight to `flatten`, so
> a thread_context would have held JSON - and a quote would then verify against
> a field VALUE, which is worse than failing to verify: it is rule 1 returning
> true for the wrong reason."*

Everything in that paragraph is true. Then, the same evening:

```
d4f075c  2026-08-28          sweep_reddit.py: payload -> prose      THE COMMENT
7391045  2026-08-28 17:55    THE RULING                             +0h
ca25a33  2026-08-28 19:02    restore 1,517 rows to the payload      +1h07
3a3d2dc  2026-08-28 19:17    prose derived at assembly, both        +1h22
                             platforms, and the test for the class
```

The ruling agreed the hazard was real and **solved it somewhere else** — at
assembly, in `collect/assemble/prose.py`, which extracts prose from the payload
and refuses bytes that are not one. With the hazard answered downstream, storing
prose upstream bought nothing and broke two NFRs (`content_hash` must fingerprint
what the author published; the row must name a raw artifact to reprocess from).

**`sweep_reddit.py` had zero commits between 2026-08-28 17:55 and 2026-09-14.**
Seventeen days. For fourteen of them the repo contained a ruling and a fluent
argument against it, in different files, with nothing linking them.

### What it cost

264 Reddit documents whose `text_ref` points at prose. They refuse at assembly —
correctly — so they yield no `thread_context`, no quotes and no claims. **They
cannot be repaired in place**, because these writers never stored the payload:
there is nothing to point the row back at, and the only route is a re-fetch that
spends quota and is not available for older threads at all. The newest of them
was written on 2026-09-10, thirteen days after the ruling.

---

## 2 · Why every check we have missed it

We have four kinds of check and the gap goes through all of them.

**The class test looks the other way.** `tests/test_assembly_prose.py` was added
by the ruling itself, and it asks of a `thread_context`: *does the flattened
text parse as JSON?* It catches **an envelope where prose belongs**. This is
**prose where the payload belongs** — the same axis, opposite sign. It passes
trivially and it is not wrong to; it was aimed at the failure that had just
happened, which is the natural thing to aim a test at and the reason the
opposite direction stayed open.

**The invariant cannot see it.** `content_hash(resolve(text_ref)) ==
content_hash` holds perfectly on all 264 rows. Both columns were written
together, so the hash always matched its artifact — **it was simply the wrong
artifact**. The ruling says this in its own correction: the invariant is
*necessary and not sufficient*, catching a mismatch between two columns and
never a wrong choice of what both point at.

**`contract/column_states.yaml` cannot see it either.** It declares a state for
every column, and `text_ref` is declared and read. The defect is not an unread
column; it is a *correctly-read column holding the wrong thing*. Rule 9's audit
stops at the schema boundary and this is inside it, being wrong quietly.

**And the reviewer questions do not fire.** Rules 7, 8 and 9 each reduce to a
question a reviewer asks *about a change*. There was no change. Nobody opened
this file for fourteen days; that is the whole defect. **Every mechanism we have
is triggered by somebody touching something.**

---

## 3 · What would actually catch it

Ordered by cost. The first is cheap and narrow; the last is the one that
generalises.

**3a · Invert the existing class test. ✅ DONE 2026-09-14 —
`tests/test_writers_store_the_payload.py`.** `test_assembly_prose.py` asks
whether flattened text is JSON. The mirror asks of the *writers*: does anything
store derived text where the payload belongs? It is an AST scan over every
tracked `put()` call in `collect/` and `scripts/`, because the offending
expressions sit inline in functions needing a network, a contract and a database
to reach — a behavioural test would have covered the writers it could drive and
skipped the ones it could not, and the defect lived in exactly the hard ones.
Same reasoning as `cli.py`'s gate test.

**It was verified by reintroducing both defects**, not by passing on the fixed
code. `sweep_reddit.py:410` and `write_reddit_thread.py:197` each fail with the
ruling quoted in the message. Three details worth keeping:

- **An unclassifiable argument FAILS rather than skips.** The preflight lesson:
  `registry load-seed` ran unguarded for weeks because nothing forced an
  unclassified path to declare itself.
- **A file that will not parse fails loudly.** The first draft did `continue` on
  a `SyntaxError`, which is the same hole one level up — the injection broke
  `sweep_reddit.py`, the file dropped out of the scan, and every assertion about
  it passed by absence. Found only because a separate count assertion noticed.
- **It scans tracked files only.** An untracked scratch script that will not
  parse would otherwise turn the guard red locally, and a guard that is red for
  unrelated reasons gets skipped, then deleted. (The example when this was
  written was `scripts/measure_key_constraint.py`, repaired later the same day —
  §5a. The reasoning does not depend on that file and the rule stays.)

The test also pins the `json.dumps` spelling, which caught a second live defect:
`scripts/fetch_model.py:_payload` omitted `ensure_ascii=False`, so the same post
fetched by two arms stored as two objects on any non-ASCII text — and since
`restore_reddit_payload_refs.py` repairs a row by finding the same post's payload
under another sweep's hash, a divergent spelling silently shrinks the set of rows
that can ever be repaired.

**3b · Make a ruling name its dependents.** The ruling is cited by 12 files, all
of which had to be found by `grep`. If a ruling carried a list of the call sites
it governs, then "which files must change when this is decided" is a checklist
rather than a memory. `sweep_reddit.py` was not on anyone's list because no list
existed.

**3c · Treat "a file untouched since a ruling that governs it" as a question.**
Not a failing check — it would be noise, and most untouched files are fine. But
when a ruling lands, `git log --since` over its cited files answers *"which of
these did the ruling not reach?"* in one command, on the day, when the reasoning
is still loaded.

**3a turned out to be a test that runs every night, and the first draft of this
section said no such test was possible.** That was wrong, and the correction is
worth keeping because it was an error of framing rather than of fact: I reasoned
that the defect is a *silence* — a file nobody opened — and that a suite passing
over a silence is indistinguishable from one passing over a correct answer.

True of the **reason**, false of the **code**. The stale comment is
undetectable; the line it justifies is an AST node, present in the tree whether
or not anybody reads it. **A guard that reads the code does not need anyone to
touch the file.** Rules 7, 8 and 9 are genuinely reviewer questions because what
they check has no syntactic form — an unstated denominator, an unmeasured error
rate, an absent reader. This one does, and I nearly filed it alongside them on
the strength of the resemblance.

So 3b and 3c remain process, and they cover the part a scanner cannot see:
**the comment, and who has to be told.**

---

## 4 · The rule this suggests

Offered for the working agreement, not taken solo:

> **When a ruling overturns a decision, the comment arguing the old decision is
> part of the blast radius.** Either the file changes with the ruling, or the
> comment is rewritten the same day to say it lost and where the new reasoning
> lives. A correct argument for a superseded position, left in place, is
> indistinguishable from current policy to everybody who arrives later.

The three reverts on 2026-09-14 each carry that forward-pointer now: the comment
says what it used to argue, when it stopped being true, and which document
overruled it — so the next person who reads the hazard and finds it persuasive
also finds the answer to it.

---

## 5 · Related instances, and the reason they are filed here

The same fortnight produced two more stale artefacts in the same direction,
and they are worth naming because they show the class is not a one-off:

`scripts/restore_reddit_payload_refs.py` — the ruling's own repair tool — ends
by printing:

> *"Reddit ASSEMBLY IS NOW BROKEN until the assembler extracts prose from the
> payload - that is the next commit"*

That next commit is `3a3d2dc`, fifteen minutes later, on 2026-08-28. The
sentence has been false for seventeen days and it prints on every run, including
the repair run of 2026-09-14. Harmless here, and exactly the same mechanism:
**a true statement about a moment, written in the present tense, in a file
nobody reopened.**

### 5a · The third instance, and it is the expensive shape

`scripts/measure_key_constraint.py` carried this argument:

```python
ap.add_argument(
    "--model", default="google/gemini-2.5-flash",
    help="PINNED, and pairing depends on it. The 2026-08-28 run used "
         "google/gemini-2.5-flash; EXTRACTOR_MODEL in .env is a different "
         "model today, and taking that default silently unpairs the "
         "comparison - which it did on the first run of this script.")
```

…and then, 46 lines later:

```python
client = OpenRouterClient.from_env()     # reads EXTRACTOR_MODEL. args.model
                                         # is never read, anywhere.
```

**The help text is a correct, specific, hard-won account of a hazard the file
still had.** It even names the incident. `--variant` was dead in the same file
in the same way: `system_prompt(withhold_keys=True)` with `args.variant`
ignored, so `--variant argued` ran the withheld prompt and labelled the output
`argued`.

The cost was a result nobody could read. `key-constraint-rerun-2026-09-11.json`
reports 134 proposals → 0, which looks like a decisive fix and is not a
comparison at all: `before` is `google/gemini-2.5-flash` and `after` is
`deepseek/deepseek-v4-flash`. Two variables moved, and the one that was supposed
to be held fixed was held fixed *in prose only*. I then repeated that result in
conversation as though it stood.

**Why this belongs here rather than in its own document.** §1 is a comment that
lost a ruling; this is a flag that lost its wiring. Different surface, one
mechanism: **an explanation and the thing it explains drift apart, and the
explanation is the half a reader trusts**, because it is the half addressed to
them. A comment is checked against nothing. An argparse `help` is checked
against nothing. Both read as documentation of current behaviour, and neither
is.

And it is the more expensive form, for two reasons:

- **It produces a number.** A stale comment misleads whoever reads the file; a
  dead flag mislabels an artefact that travels — into a JSON on disk, a summary,
  a decision. §1 cost fourteen days of bad rows. This cost a measurement that
  argued for a prompt change on evidence that was not evidence.
- **The care is the camouflage.** Nobody writes four lines about why pinning
  matters unless they have just been bitten by it. The thoroughness of the
  explanation is exactly what stops the next reader checking whether the code
  does it.

**What catches it, and it is cheaper than §3's list.** A dead argparse argument
is `args.<dest>` appearing exactly once in the file — at its definition. That is
a grep, and for the same reason as `tests/test_writers_store_the_payload.py` it
is syntax rather than silence, so a scanner can see it without anybody opening
the file. Not built here; recorded as the obvious next guard, and rule 9's
reviewer question is already the right words for it — **what reads this, and
where, file and line?** — asked of a flag rather than a column.

*Incident detail and the measured populations:
`docs/for-the-team-reddit-text-ref-decision-2026-09-11.md`.*
