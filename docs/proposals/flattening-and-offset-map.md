# Flattening and `offset_map` — settled before any code

**Byte equality on the first run — 2,481 characters and all 20 segments
identical, from an implementation written without reading hers.**

Two premises needed correcting first. There was no flattener in `collect/` to
compare against, so her fixture was not a second opinion but the specification
by example. And it contains no HTML entities: the `&gt;` case is in the source
payload, in six comment bodies, and in none of the six documents she selected.

*Engineer 1 · 2026-08-18*

---

## 1 · Do the two flatteners agree? There is only one, and it is hers

`collect/assemble/` holds `authors.py`, `dedupe.py` and `signature.py`. **No
flattener exists in this lane and never has.** Nothing in `collect/` produces a
flattened string or an `offset_map`; every mention of either is a docstring, a
schema comment or a refusal.

So the comparison she proposed — build both, diff the bytes, hers regenerates if
they disagree — cannot be run today, and asking for it is what established that.
Her fixture's own provenance already says the right thing:

```json
"note": "Fixture tooling, not E3. collect/assemble/ is authoritative;
         if the two disagree, regenerate this from that."
```

**That ordering is correct and, right now, vacuous.** Authoritative-when-it-exists
is not authoritative. Until E3 is written, `fixtures/threads/build.py` is the only
implementation of the flattening rules in the repository, and `verify.py` — the
thing the whole guarantee rests on — has only ever been tested against its
output.

**So the useful framing is the reverse of the one proposed.** Her fixture is not
a check on my flattener; it is the executable specification my flattener has to
reproduce, and the first test of E3 is byte equality against it. If they
disagree, the question of which is authoritative is a real one to have — but it
is a design conversation, not a regeneration.

### What her fixture actually specifies

20 segments over 6 documents, 2,481 characters, 10 substitutions.

| | |
|---|---|
| documents | 6, joined by `\n\n---\n\n` |
| joiner characters | **unmapped** — 35 of 2,481 belong to no segment |
| substitutions | 10, all single-codepoint emoji |
| identity runs | 10 |
| longest identity run | 1,739 chars (the root post, unbroken) |
| consecutive substitutions | 7 in a row — `█` ×7 in `oqop8ge` |

Two properties worth naming because they are decisions, not consequences:

**The joiner is unmapped, and that is right.** A quote spanning `\n\n---\n\n`
overlaps segments from two documents, so `verify.py` returns
`SPAN_CROSSES_COMMENTS` and rejects it. A quote cannot straddle two authors, and
the unmapped joiner is what makes that automatic rather than a check somebody
has to write.

**Seven consecutive substitutions produce seven segments, not one.** `████████`
becomes `[full_block]` seven times, each its own segment mapping one raw
character. Merging them would be smaller and would break `_resolve_raw_span`:
its rule is that a substitution segment is taken whole, so a merged run of seven
would map any quote touching one block to all seven.

---

## 2 · The `&gt;` case: it is in the payload and not in the fixture

The premise was that her fixture includes HTML entities. It does not — I checked
`flattened_text` and all six `raw_text_of` values for `&[a-z]+;` and `&#\d+;`
and found **none**, and `>` appears nowhere in the flattened text either.

The entities are in the **source payload**:

| field | comments containing `&gt;`, `&lt;` or `&amp;` |
|---|---|
| `body` | **6** |
| `body_html` | 195 |
| `selftext` | 0 |
| `selftext_html` | 1 |

```
raw body: "&gt;Unbelievable they can't even include it in a $200/mo plan…"
raw body: "https://preview.redd.it/…?width=1444&amp;format=png&amp;auto=webp…"
```

`body` is the field an adapter stores as document text. So **six of this
thread's comments carry entities and none of them is among the six she
selected** — which makes this precisely the case the fixture cannot catch, and
the reason to settle it in prose before writing the walk.

### What the walk should emit, and why it is a substitution

`&gt;` → `>` is a **length-changing rewrite**, so by the rule in
`contract/tables.sql` it is one segment per occurrence, taken whole:

```
raw   "&gt;Unbelievable"          flat  ">Unbelievable"
      0123456789...                     0123...

segment A   SUBSTITUTION   flat[0:1]  raw[0:4]     "&gt;" -> ">"
segment B   identity       flat[1:14] raw[4:17]    "Unbelievable"
```

**It is the first shrinking substitution.** Every one in her fixture grows —
emoji 1 char → 12–47. This goes 4 → 1, and `&amp;` goes 5 → 1. Nothing in
`_resolve_raw_span` cares about the direction (`is_identity` compares lengths,
and a substitution is taken whole either way), but nothing has ever exercised
it, and the arithmetic that breaks on a shrink is different from the arithmetic
that breaks on a growth.

**Why unescape at all**, given step 3 renders the raw span: because the raw span
would then display `&gt;Unbelievable` to a reader, which is not what the engineer
wrote — they wrote a Reddit blockquote. The entity is a transport artefact of
Reddit's API, not authorship. That is the opposite direction from emoji, where
the *flattened* form is the internal one and raw is what displays; here raw is
the encoded one and the flattened form is closer to intent.

**That asymmetry is the thing to be careful about**, and it is worth stating in
the schema comment: `offset_map` substitutions are not all "internal
representation → display". Some are "transport encoding → what was typed".

### Three rules the walk needs that her fixture does not exercise

1. **Unescape exactly once.** `&amp;gt;` is a literal `&gt;` that somebody
   typed; unescaping twice yields `>` and silently changes the text. One pass,
   never a loop.
2. **Only the five named entities** — `&amp; &lt; &gt; &quot; &#39;` — which is
   what Reddit emits. A general HTML unescaper would also rewrite `&copy;` and
   anything else a user typed literally, which is a rewrite of authorship rather
   than of transport.
3. **`&amp;` inside URLs is still a substitution.** The example above has two in
   one URL. They are ordinary substitutions and produce ordinary segments; the
   only hazard is a quote that starts mid-URL, which takes the whole
   substitution and is correct.

### One thing I would change in the fixture, as a request rather than an edit

Her fixture has no entity case, and the payload it was built from has six. **A
seventh document containing `&gt;` would make this section a test instead of a
paragraph** — and it is her file, so this is a request. `oqocfjv` and the
`&gt;Unbelievable` comment are both in the same payload.

---

## 3 · Which I would trust if they disagreed — stated before running it

**Hers, on the flattening rules. Mine, on the segmentation.** Not a hedge; they
are different claims with different evidence behind them.

Her `build.py` was written against the real payload, and the rules it encodes —
the joiner, the `unicodedata.name()` tags, which characters are substituted at
all — are **observations of that data**. Mine would be
reconstructions of her observations. Where they disagree about *what the string
should look like*, she has looked at the tree and I have looked at her output.

The segmentation is the other way round. `verify.py` and `build.py` are both
hers, so a segmentation that is wrong in a way both share is invisible to her —
which is exactly the shape `tests/conftest.py` records three times. Mine is the
first independent reading of `contract/tables.sql`'s segment rule, and where we
disagree about *segment boundaries* the contract decides, not either of us.

Her note says `collect/assemble/` is authoritative. That is right as a standing
rule and it should not be invoked on day one: authority earned by existing is
not evidence. **The honest position before running was that neither of us had
any**, and the first agreement is the first evidence either implementation has
ever had.

### What actually happened

```
BYTE EQUALITY: True
SEGMENTS: mine=20 hers=20  identical=True
```

Byte-for-byte on 2,481 characters, and segment-for-segment on all 20 — first
run, no adjustment. Written from `contract/tables.sql` plus the fixture's
observable properties, without reading `build.py`.

**That is worth more than either implementation being declared authoritative.**
Two independent readings of one specification produced the same map on real data
with six documents, ten substitutions, seven consecutive `█`, an unmapped joiner
and a 1,739-character identity run. The disagreement conversation did not need
to happen, and the reason to have set it up was that it might have.

One thing the agreement does **not** cover: the entity case, which is why §2
exists and why the tests below it are separate.

---

## 4 · What I am not deciding here

**Whether `body` or `body_html` is the document text.** The adapter stores
`body`, entities and all, and that is what `raw_text_of` must contain for step 3
to render the raw span. If that ever changes, every stored offset moves. It is
settled by what `collect/adapters/reddit_comments.py` already does, and I am
recording it rather than re-opening it.

**The normalisation order.** Emoji substitution and entity unescaping both
rewrite the text, and doing them in different orders can produce different
segment boundaries where they are adjacent — `&gt;😄` is the case. My reading is
that entities come first, because they are transport decoding and the emoji rule
operates on what was actually typed. That is an assertion, not a measurement,
and it is the one thing here I would most like a second pair of eyes on before
it is code.
