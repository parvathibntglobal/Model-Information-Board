# A constraint in the schema and not in the description is invisible to the model

**If the model must respect a constraint, the constraint goes in the description
of the field it is filling. A validator enforces it after the fact and teaches
nothing; prose in the system prompt competes with the schema and loses.**

Four instances in one session, three of them found by accident while chasing
something else. This is the most transferable thing here, so it is written
separately from the things it explains.

*Engineer 1 · 2026-08-21*

---

## The four

### 1 · `maxLength: 200` beside `"title": "Quote"`

The limit was in the tool schema the whole time, as JSON metadata. `quote`'s
description said *"VERBATIM text from the source. No paraphrase, no ellipsis, no
repair."* — and nothing about length.

```
maxLength appears in the tool schema:  True
the string "200" appears:              True
quote's description mentions length:   no
```

`qwen-38-27b` proposed 14 claims twice and lost all 14 twice, because two quotes
were 15 and 8 characters over. Both had a sentence boundary well inside the
limit, so a compliant span existed and the model did not choose it.

Putting the limit into the description — *"AT MOST 200 CHARACTERS — that is
roughly one sentence. Count before you answer."* — took that document from **0
claims after two failed attempts to 11 claims with zero retries.**

### 2 · `unclassified` fired only when its description asked

The field existed to reveal a short capability vocabulary and **had never been
non-empty in any run of this project**. A sentence added to the *system prompt* —
*"USE IT. A quote you decline to classify and do not record here is a capability
nobody learns is missing"* — changed nothing.

Rewriting the *field's* description as a positive check — *"BEFORE YOU ANSWER,
CHECK EVERY CLAIM YOU MADE. For each one, ask: does the capability key you chose
actually name what the quote is about?"* — made it fire on the next call.

**Same fix, same place, and the prompt version of it had already failed.**

### 3 · `'xhigh'` in a boolean, because no field existed

`Conditions.structured_mode` is `bool | None`, meaning *"was provider-side schema
enforcement on"*. The model put `'xhigh'` in it — the document's **reasoning
effort**.

`Conditions` has `tool_count`, `context_size`, `structured_mode`, `framework`,
`hosted_by`, `domain`, and **no reasoning-effort field**. So the value went to the
nearest-shaped slot rather than nowhere.

This is the same mechanism seen from the other side: **the schema is where the
model looks for somewhere to put a thing, and it will find the closest field
rather than decline.** A missing field is not read as "do not record this".

### 4 · 18 field descriptions outweighing 17 lines of prose

Measured before any of the above:

```
tool schema      4,946 chars, 18 descriptions      -> now 8,830
system prompt    2,714 chars, 17 non-blank lines   -> now 2,819
```

The schema was already 1.8× the prompt and is now 3.1×. `ModelRef.speaking`'s
description alone is 1,075 characters — **38% of the entire system prompt** — and
it sits attached to the value being chosen rather than 8,000 characters earlier.

---

## The rule

> **If the model must respect a constraint, the constraint goes in the
> description of the field it is filling.**
>
> A validator enforces it after the fact and teaches nothing. Prose in the
> system prompt competes with the schema and loses.

Three corollaries, each earned by one of the four:

**A validator is not an instruction.** `maxLength` rejects; it does not explain
what to do instead. The rejection arrives after the answer is written, costs the
whole batch, and the model has no way to have avoided it except by having read
the number as prose.

**A missing field is a misfiled value, not an absent one.** `'xhigh'` in a bool
and *"it defaults to wildly overthinking things"* under `over_refusal` are the
same failure: the schema offers a slot list and the model picks the nearest
member. If a fact should not be recorded, the description of the nearest field
has to say so — which is why `unclassified`'s new text names the verbosity case
explicitly.

**An empty optional field is not evidence.** `unclassified` sat empty for the
project's whole history and was read as "the vocabulary is complete". It was
reading as "nobody asked".

### What this does not license

**It is not an argument for moving the prompt into the schema.** The prompt's job
is the things that are not about one field: the untrusted block, the injection
rules, what a claim needs to exist at all. Those have no field to attach to. The
rule is about *constraints on a value*, and the test is whether there is a field
the constraint belongs to. If there is, that is where it goes.

**And it is not a claim about all models.** One extractor, `google/gemini-2.5-flash`,
across roughly forty calls this session. The mechanism is plausible for any
forced-tool-call setup and is measured on one.

---

## Why it is worth its own file

Three of the four were found while chasing something else, and each looked like a
different problem at first:

```
the quote ceiling      looked like a limit that was too tight
unclassified           looked like a model that would not abstain
'xhigh' in a bool      looked like a bad answer
```

All three were the same thing, and none of them would have been found by looking
for it. That is the argument for writing the rule down rather than the three
fixes: **the next instance will also look like something else.**

Instances so far, for whoever adds the fifth:
`docs/measurements/the-limit-in-the-description.md`,
`docs/measurements/blog-extraction-run.md`,
`docs/proposals/for-engineer-2-a-speaking-field-on-modelref.md` §5.
