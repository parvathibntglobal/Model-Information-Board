# The fifth `coverage_gap` kind: mentions that resolve to nothing

**Proposed. Two facts, not one — and only the first is about the route ruling.
Counted per surface, with the route id where there is one, because a surface is
what a person wrote and a route id is what we declined to resolve it to.**

*Engineer 1 · 2026-08-18 · `contract/` unchanged by this document*

---

## 1 · Why it exists

The route ruling made `openrouter/free`, `openrouter/auto` and 15 other ids
unresolvable by construction — a claim about `free` names a pointer, and the
model that served the request is unknown. That was the right call for
attribution.

**But rule 6 is symmetrical about it.** An unresolvable mention is a mention.
Dropping it silently converts *"somebody named a thing we decline to resolve"*
into *"nobody named anything"*, which is the same conversion the rule exists to
refuse — and it does it in the direction that flatters us, because a pile of
route-mentions is evidence that people do talk about routes and our schema has
nowhere to put it.

`coverage_gap`'s own CHECK anticipated this:

> An unconstrained `kind` is how a fifth gap type gets added later without the
> coverage page knowing it exists. Adding one is then a deliberate contract
> change with a review attached.

This is that change.

---

## 2 · The two facts, and why they must not be one kind

**"Matched a route" and "matched nothing at all" are different findings, and
only the first is about our ruling.**

| | what it means | what it is evidence of |
|---|---|---|
| `mention-resolves-to-route` | the surface matched, the owner is a route, we declined | **our ruling.** People name routes; we have decided not to attribute them |
| `mention-unresolvable` | nothing in the population matched | **our coverage.** Either a model we do not carry, or a surface no derivation reaches |

Collapsing them would make a growing pile ambiguous between *"the ruling is
costing us more than we thought"* and *"the alias population has a hole"* —
which need opposite responses. The first might reopen the ruling; the second is
a review item for the surface list.

**So: two kinds, not one.** Both go in the same CHECK.

There is a third state deliberately not recorded: a surface matching a
*family word*. `opus` is excluded from the population by design and is attested
constantly. Counting it here would swamp both new kinds with a fact already
measured in `docs/measurements/alias-surfaces.md` §4.

---

## 3 · Per surface, with the route id beside it

**Per surface**, because that is the unit a person wrote and the unit a reviewer
acts on. `subject` is the surface; the route id goes in `detail`.

```yaml
kind:    mention-resolves-to-route
subject: free                    # what was written
detail:  openrouter/free         # what we declined to resolve it to

kind:    mention-unresolvable
subject: gpt 5.6 sol             # what was written
detail:  no surface in population dc69d8725ccfe658   # and which population
```

Three reasons, in order of how much they decide it:

**A route id alone loses the surface.** `openrouter/auto` is reached by writing
`auto`, and possibly by other forms nobody has seen yet. Counting per route id
would say *"auto was mentioned 42 times"* and lose that they were 42 instances
of one word — which is the fact that would tell us whether people are naming the
router or using an English adverb.

**A surface alone loses which ruling applied.** Two surfaces can resolve to the
same route, and a reviewer asking "is the route ruling expensive" needs them
grouped.

**`coverage_gap_unique` is `(kind, subject, detail, pipeline_version)`**, so
surface-plus-route is already the natural key and a nightly re-run cannot
multiply it.

### The population fingerprint belongs in `detail` for the second kind

`mention-unresolvable` is only meaningful against the population that failed to
resolve it — the same reproducibility problem as the entity gate, where 385 of
1,900 documents change verdict on the alias set alone. A gap recorded without
its fingerprint is not re-checkable, and next week's population would produce a
different pile with no way to tell what changed.

---

## 4 · What this is not

**Not a count of documents.** One document can carry several unresolvable
mentions and one mention can appear in many documents. `coverage_gap` records
the gap, not the corpus; the document-level figure belongs with triage's
counters.

**Not a queue.** A route mention is not a thing to fix — the ruling says so. It
is a thing to watch, and the number that would reopen the ruling is a judgement
nobody has made yet. `mention-unresolvable` is closer to a queue, since a
recurring unresolvable surface is a candidate for the alias review.

**Not free.** Every unresolvable mention becomes a row, and the substitution
corpus alone has 255 `unknown-model` surfaces over 1,523 mentions. The
`UNIQUE` constraint bounds it to distinct surfaces per pipeline version, which
is the right bound, but the coverage page needs a floor on what it shows or the
top of the list will be permanent.

---

## 5 · Proposed change

```sql
CONSTRAINT coverage_gap_kind_ck CHECK (kind IN (
  'unsourced-field',
  'missing-spelling',
  'out-of-window',
  'unknown-release-date',
  -- A surface matched, and its owner is a route rather than a model. Ruled
  -- 2026-08-18: routes are not models, because a claim about `free` names a
  -- pointer and the model that served the request is unknown. The mention is
  -- still a mention — dropping it would turn "somebody named a thing we
  -- decline to resolve" into "nobody named anything" (rule 6), in the
  -- direction that flatters us.
  --   subject = the surface as written; detail = the route id.
  'mention-resolves-to-route',
  -- Nothing in the surface population matched. A DIFFERENT FACT: the first is
  -- evidence about our ruling, this is evidence about our coverage, and they
  -- need opposite responses.
  --   subject = the surface; detail = the population fingerprint it failed
  --   against, without which the gap is not re-checkable.
  'mention-unresolvable'
)),
```

**The fourth use of the migration path**, and the first that is neither a new
table nor a new column: it alters an existing CHECK, the same operation as
`20260818T1520`, on a constraint the coverage page reads.

Not written. `contract/` is shared and this needs Engineer 2's review — she
raised it, and the page that renders these is hers.
