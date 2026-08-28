# E6 hard rejection has never run on a single claim from `--from-export`

**Not "rarely fired". Never ran.** `_document_facts` builds `DocumentFacts`
without a `text=` argument — `grep -n "text=" judge/cli.py` returns nothing — so
`document.text is None` for every document, and `pipeline.py:536` takes the
`unvetted` branch every time:

```
no text for reddit:t3_1ummy1u, so E6 rejection could not run on it;
recorded as unvetted rather than counted as kept
```

That line is currently printing once per document in a 1,512-thread run.

*Engineer 1 · 2026-08-28. Found while computing a progress estimate, which is
the only reason I looked.*

---

## 1 · Why it happens, and the cause is a correct decision applied to the wrong field

`_document_facts` reads from the database rather than from the export, on stated
reasoning I agree with:

> *"Read rather than taken from the export: `platform` and `created_at` decide
> weighting, and **a figure the input supplies is a figure the run cannot
> check.**"*

Right for `platform` and `created_at`. Wrong for `text`, and for a reason
specific to `text`:

```
platform, created_at   FIGURES that feed weighting. The export could lie about
                       them and the run could not tell. Read from the DB.

text                   THE SUBSTRATE the model was shown and the quote was
                       verified against by exact substring match. It is not a
                       figure and there is nothing to check it against - it IS
                       the thing everything else is checked against.
```

And the database cannot supply it. `document` has `text_ref`, a store location,
and `judge/` may not import `collect/` — `tests/test_lane_boundary.py`, both
directions, no allowlist. **So on the export path there is no route to the text
except the export**, which already carries it: `flattened_text` and
`raw_text_of` per member, both loaded, both in `ThreadInput`.

## 2 · What is lost, and it is the part that reads as a clean result

`unvetted` is a well-designed state and its own docstring says why:

> *"`unvetted` — no text was supplied, so no rule could run. Recorded as its own
> state — **reading it as "kept" would be a missing value becoming a definite
> one.**"*

Rule 6, correctly implemented. So nothing is being silently counted as kept, and
that is why this is a gap rather than an incident.

**What it costs is the hard-reject filter entirely.** Every claim this run
stores has passed extraction, quote verification and weighting, and has had *no
rule run against it*. A board that renders those claims is rendering unvetted
evidence, and the only trace is a log line.

**And `unvetted_documents` is not persisted.** `result.unvetted_documents` is a
list on an in-memory object. After the run exits, nothing distinguishes a claim
whose document passed E6 from one whose document was never checked — same
`claim` row, same `cell` contribution. That is the part I would fix first,
because it is what turns a known gap into an invisible one.

## 3 · The fix

```python
facts[doc_id] = DocumentFacts(
    document_id=doc_id,
    platform=source,          # DB — a figure the export could lie about
    created_at=...,           # DB — same
    author_id=author_id,      # DB — same
    # FROM THE EXPORT, and only this one. It is not a figure that feeds a
    # weight; it is the text the quote was verified against by substring
    # match. The database cannot supply it - `text_ref` is a store location
    # and this lane may not read the store - so the export is the only route,
    # and it is the SAME text the extractor was shown.
    text=text_of.get(doc_id),
    ...
)
```

`_document_facts` needs the loaded export passed in, or the two calls reordered
so `loaded` exists first. `_extract_from_export` already has both.

**And persist `unvetted`.** A boolean on `claim`, or a row in a side table —
your call which, but a claim that no rule ran against should not be
indistinguishable from one that passed every rule.

## 4 · How far back this goes, and I have not established it

The blog run's claims came through `--from-export` too, so the same branch
applies to them — but I have not checked whether `_document_facts` looked
different then, and the 20 blog claims predate several changes to this file. I
am not going to assert it covers them. **Population unstated is population
unknown** (rule 7's risk form): what I have measured is *this* run, where it is
every document.

## 5 · Why nobody saw it

The message is a `log.warning`, so it goes to stderr and reads as a per-document
complaint about missing data — which is exactly what it is. At one line per
document it looks like noise about an incomplete store, and my first reading of
it was "29 documents whose payloads are in the wrong store". I only checked
because I wanted a denominator for a progress estimate, computed how many of the
1,512 documents have unresolvable text, and got **0**.

The warning names a real condition and points at the wrong cause. It would have
been found years earlier as:

```
E6 could not run: no text was supplied for any of N documents. On the
--from-export path `DocumentFacts.text` is never populated - see cli.py.
```

A per-item warning for a systemic condition is a warning nobody reads. **Same
shape as the `writeguard` message in #189**, from the opposite direction: that
one asserts a cause it has not checked, this one declines to name a cause it
could have.
