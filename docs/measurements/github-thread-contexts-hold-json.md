# CONFIRMED: GitHub's 80 `thread_context` rows hold JSON, not prose

**The same defect I found in my own sweeps, one week older, in a place nobody had
looked.** A GitHub `flattened_text_ref` resolves to
`{"url":"https://api.github.com/repos/96loveslife/b...` — the raw issue payload,
flattened verbatim.

**Nothing has been damaged yet, and the reason is luck rather than design: GitHub
has produced 0 claims.** Any extraction over those 80 contexts would have verified
every quote against a JSON field value and reported clean.

*Engineer 1 · 2026-08-28*

---

## 1 · The evidence

```
document.text_ref for github   = issue.ref
                                 collect/adapters/github.py:583, and `ref` comes
                                 from `self._store.put(response.content,
                                 namespace=RAW)` at line 510 — the ISSUE PAYLOAD

assemble_issue(document_id, text=outcome.require(), ...)
                                 passes whatever text_ref resolves to straight
                                 into `flatten`, with no extraction step

resolved locally, one of the 80:
  flattened_text_ref -> '{"url":"https://api.github.com/repos/96loveslife/b'
```

Only 1 of the 80 resolves on this machine — the rest are the payloads absent from
this store — but one is enough to settle the question, because the code path is
the same for all 80.

## 2 · Why "verification would have reported clean" is exactly right

`verify.py` checks that the quote exists as a substring of the flattened text. A
GitHub issue payload contains `"body": "…the model truncated at 8k…"`, so **the
prose is present inside the JSON** and a quote of it verifies.

So the failure is not a rejection. It is:

```
quote_verified = true                  and the check was against a field value
quote_flat_offset, quote_raw_offset    offsets into a JSON document
the rendered quote                     a span of an API response
```

`claim_verified_ck CHECK (quote_verified = true)` then guarantees the row is
storable. **A wrong quote that passes is worse than a right quote that fails**,
and this is the shape that produces it: rule 1 returning true for the wrong
reason, exactly as in my reddit case, and with no symptom anywhere.

**And the offsets are the part that does not survive a later fix.** Re-flattening
the payload as prose changes every character position, so any claim already
carrying JSON offsets is unrepairable — it has to be re-extracted.
`collect/CLAUDE.md`'s first rule again, arriving from a direction nobody had
checked.

## 3 · Blast radius, counted

```
github thread_context rows           80
github claims                         0     <- nothing was built on them
github documents                     80
of those, payloads readable here      1
```

**Zero claims is why this is a near-miss rather than an incident.** The reason
there are no GitHub claims is a separate gap — the extraction runs so far have
gone over blog and reddit exports — so this was prevented by a different thing not
working, which is not a control.

## 4 · The fix has a design question in it, so it is a proposal not a commit

Two ways, and they differ on what `content_hash` identifies:

**(a) `text_ref` points at extracted text.** What I did for reddit. Consistent
with `rawstore.py`'s own framing — *"`text_ref` is a location; `content_hash` is
identity"* — and it makes `text_ref` mean the same thing on all three platforms.

But `github.py`'s docstring says `text_ref` names the issue payload *deliberately*:

> *"`text_ref` names the issue, never the search page: one search response covers
> a hundred issues, so pointing `text_ref` at it would stop `content_hash`
> identifying one document — breaking dedupe and NFR-6 the same way it would for
> a feed."*

That reasoning is about *which artifact*, not about text-versus-JSON, and it is
still right. Under (a), `content_hash` would need to stay the payload's hash while
`text_ref` points elsewhere — which is legal by the field definitions and is a
change to what dedupe compares.

**(b) `assemble_issue` extracts title+body before flattening.** Leaves `text_ref`
and `content_hash` exactly as documented, and puts the extraction where the
platform knowledge already is. Costs a JSON parse per assembly and one more place
that knows the GitHub payload shape.

**I would take (b) for GitHub and I have not done it**, because I already took (a)
for reddit and a codebase where the same field means two things on two platforms
is worse than either choice. That is a decision about the lane's storage contract
and it should be made once, deliberately, rather than twice by whoever is fixing
their own platform.

## 5 · What has to happen regardless of which

```
1  stop flattening JSON                        either fix
2  rebuild the 80 github thread_contexts       their ids are content-derived, so
                                               a rebuild at the same pipeline
                                               version needs the payloads, and 79
                                               of 80 are not on this machine
3  re-extract anything built from them         0 claims today, so free NOW and
                                               not free later
4  a test that the flattened text is not JSON  I added one for reddit
                                               (test_reddit_assemble.py); the
                                               same assertion belongs on the
                                               issue path
```

**Step 4 is the one that would have caught this a week ago** and costs one line.
It is also the one I only thought to write after finding the bug in my own code,
which is the honest order of events.

## 6 · How it was found, because the method is the transferable part

Not by reading the assembler. By checking what a `text_ref` actually resolved to
before running `assemble` over 1,500 rows — and then asking the same question of
the platform whose payloads I could not read, using the writer rather than the
data.

The check is one line and needs no suspicion: **resolve a `text_ref` and look at
the first character.** `{` means the pipeline is about to treat an envelope as a
document.
