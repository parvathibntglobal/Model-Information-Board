# The model page: there is no 404, and that is the defect

**`find_model` does not exist, aliases are not on this path, and `/models/{id}`
never 404s. It returns 200 with an identical "nobody has reported" page for the
internal id, the canonical id, and a string that is not a model at all. FR-24
inverted: the rule that makes an empty page correct for a real model makes it a
fabrication for one that does not exist.**

*Engineer 1 · 2026-08-20 · verified by calling the endpoint against the live
registry · `judge/` unchanged by this document*

---

## 1 · What was reported, and what is there

The report was that `find_model` requires an exact `canonical_id` match, that 333
of 340 models have no alias rows, and that those pages therefore 404 rather than
render empty — two defects in one symptom with only the router half named.

The symptom is real and both halves are wrong about the mechanism:

- **There is no `find_model`.** No function of that name in `judge/` or
  `collect/`.
- **Aliases are not on this path at all.** `ModelPageReader.build` selects from
  `cell` by `model_version_id` and reads the capability list from
  `contract/capabilities.yaml`. It never touches `model_alias`. `model_alias`
  holding 0 rows is irrelevant to whether a model page renders.
- **Nothing 404s.** `build` has no failure branch: with no `cell` rows it returns
  a full `ModelPage` with all twelve capabilities `unreported`, which is FR-24
  working exactly as specified.

## 2 · What actually happens, called four ways

Against the live 340-row registry, 2026-08-20:

| request | status | result |
|---|---|---|
| `/models/mv_568e0eb3a95b5113` | **200** | 12 capabilities, all `unreported` |
| `/models/anthropic/claude-opus-5` | **200** | 12 capabilities, all `unreported` |
| `/models/anthropic/claude-fable-5` | **200** | 12 capabilities, all `unreported` |
| `/models/total-nonsense-not-a-model` | **200** | 12 capabilities, all `unreported` |
| `/capabilities/not-a-capability` | **404** | *"Refused rather than rendered empty…"* |

All four model responses carry the same summary: *"0 of 12 tracked capabilities
have any reports at all."* **A typo and a real model are the same page.**

The two facts underneath it:

**`cell.model_version_id` is the internal `mv_…` id**, not the canonical id —
`stable_id("mv", canonical_id)`, so `anthropic/claude-opus-5` is
`mv_568e0eb3a95b5113`. The canonical id therefore matches no row, ever.

**Nothing validates the path parameter.** So the canonical id "works" only in the
sense that everything works: it produces the same empty page as anything else.
The `:path` fix in `ae280be` made the route *match*; it did not make the id
*resolve*.

## 3 · So: fall back, or is the alias required?

**Neither, and the question dissolves.** The alias was never required, because
aliases are not consulted. What is required is the thing neither id currently
gets: **validation against `model_version`.**

Two halves, and they are separable:

**(a) Accept the canonical id.** It is the id the registry publishes, the id the
frontend has (`modelPath()` splits a canonical id on `/`), and the id a human
would type. Resolving it costs one lookup:

```sql
SELECT id FROM model_version WHERE canonical_id = %s OR id = %s
```

Accept both shapes — the `mv_` id is a stable internal key that existing links
use, and the canonical id is what everything external holds.

**(b) 404 when the registry does not carry it**, with the reasoning already
written thirty lines up in the same file for `/capabilities/{key}`:

> *"Refused rather than rendered empty: an unknown key would read 'nobody has
> reported on this', which is indistinguishable from a real capability nobody has
> discussed."*

That sentence is the whole argument, and it applies unchanged one endpoint over.
**A model in the registry that cannot be reached by its own canonical id is a
product defect; a string that is not a model rendering as a model with no
evidence is a correctness defect** — and the second is the worse of the two,
because rule 4 is the rule this board is built on and this is the one place the
API breaks it.

## 4 · It needs nothing from `collect/`

Unlike the resolution gap in `extraction-unresolved-counters.md`, this one is
entirely `judge/`'s and needs no widening of the interface:

- `judge/` **already reads `model_version`** — `judge/pages/capability.py:140`
  does `FROM model_version mv LEFT JOIN cell c`, for the same reason. So the
  query is an established pattern rather than a new dependency.
- `stable_id` is in `collect/ids.py` and may not be imported, but it is not
  needed: the lookup is by `canonical_id`, and the database already holds both
  columns.

**The capability page is the worked example for both halves**, in the same
directory: it 404s on an unknown key, and it `LEFT JOIN`s from `model_version` so
*"a model with no cell survives the query as a row"* — with a comment saying an
inner join *"is the whole defect: it would silently produce a page about the
models people post about."* The model page needs the same two properties and has
neither.

## 5 · What this changes about the denominator

The report tied the 404 to *"333 of 340 models have no alias rows"*. Two
corrections, and neither leaves the finding smaller:

**333 is now 316.** `alias_coverage` counted 17 routes as models awaiting a
surface; fixed in `f30fea6`, and `316 + 17 routes + 7 carrying surfaces = 340`.

**But the alias count was never the denominator here.** Every model page behaves
identically whether or not the model has an alias row, because the page does not
read aliases. The denominator for *this* defect is **340** — every model in the
registry is reachable only by an id no caller holds, and **every string
whatsoever** renders as a model. Alias coverage governs whether a model can
accrue evidence; it has nothing to say about whether its page exists.

## 6 · What would revise it

- **A cell with rows.** Every observation here is against a board with 0 claims,
  so the empty page is currently *also* the truthful page for all 340. The defect
  is that it is indistinguishable from the untruthful one, and that gets worse
  rather than better once claims land.
- **A decision on whether `mv_` ids should appear in URLs at all.** If the answer
  is no, (a) becomes a rename rather than a fallback and the internal id stops
  being a public key.
