# `ExtractionRun.rejected` is two failures counted as one, and half of them may be apostrophes

**A proposal, not a change. `judge/` is your lane and I have not touched
`verify.py`.** Measured on a temporary harness that reuses your verification rule;
if the ratio holds in production, half of every rejection count reported so far is
encoding rather than fabrication.

**And the fix is not to normalise.** Rule 1's guarantee is byte-for-byte existence
in the text the model was shown, and normalising the haystack weakens exactly that.
The fix is reporting.

*Engineer 1 · 2026-08-28*

---

## 1 · The measurement

A temporary classification pass over 358 documents produced 255 quotes, verified
the same way `verify.py` does — exact substring against the text the model was
given. 68 failed. Splitting them:

```
present after unicode/whitespace normalisation    34    ENCODING
genuinely absent from the document                34    fabricated or paraphrased
present exactly (harness bug)                      0
                                                  ---
                                                   68
```

**So the fabrication rate is 34 of 255 — 13.3% — and the raw failure count reads
26.7%.** I would have published the doubled figure.

The encoding half is what you would expect and no more exotic than that:

```
model returned          Augment's evaluation of real-world coding tasks
document contains       Augment’s evaluation of real-world coding tasks
                               ^ U+2019 RIGHT SINGLE QUOTATION MARK

model returned          when I ask it to fix something
document contains       when I ask it to fix “something”
                                            ^ U+201C / U+201D
```

Also em-dash for hyphen, and non-breaking space for space.

## 2 · Why this matters for production rather than only for my harness

`judge/extract/verify.py` performs **no** Unicode normalisation — no `NFKC`, no
quote folding, no whitespace collapsing. I checked: no `unicodedata` import, no
normalise call. So the production verifier rejects a curly apostrophe against a
straight one exactly as my harness did.

And `runner.py` says what that costs:

> *"A discarded claim is the most interesting thing this stage produces. It is
> either a model inventing a quote, or an injection attempt, or a bug in the
> offset map — and all three are invisible in the output."*

**All three of those are the second bucket.** None of them is an apostrophe. If
half of `ExtractionRun.rejected` is encoding, then the counter the design treats
as an alarm is half noise — and the alarm is quieter than it looks precisely when
it matters, because a real fabrication is diluted by a typographic near-miss.

## 3 · What I am proposing, and it changes no behaviour

**Report the two causes separately. Reject both, exactly as now.**

```python
# judge/extract/verify.py
class Rejection(...):
    ...
    #: The quote is absent BYTE FOR BYTE, and would be present under Unicode
    #: and whitespace normalisation. Still rejected - rule 1 is byte-for-byte,
    #: and a haystack we normalised is not the text the model was shown. But it
    #: is a DIFFERENT FINDING from a fabricated span, and counting them together
    #: makes the fabrication rate read double.
    encoding_near_miss: bool = False
```

Set it by testing the normalised forms **only after the exact test has already
failed**, so the exact test remains the only thing that can pass. The
normalisation is diagnostic and never permissive.

`ExtractionRun` then carries `rejected` as now plus a count of how many were
near-misses, and the run summary reports both.

## 4 · Why not normalise, stated so nobody re-proposes it

Normalising the haystack would make the quote check pass on a span that differs
from the document. That is a small difference today — a curly apostrophe — and the
guarantee it breaks is not small: **`quote_verified` means "this exact text is in
that exact document at that offset", and the offset map depends on it.** A
normalised match has no defensible offset, because the normalisation changed the
character positions.

There is also the injection case. Rule 1 exists partly so a forged quote cannot
be smuggled past the checker, and every character class you fold is a character
class an attacker can vary. Folding quotation marks is where that starts.

## 5 · What it would tell us that we cannot see now

Two things, and the second is the one I would want:

**The real fabrication rate**, which is currently overstated by an unknown factor
— 2x on my corpus, and unmeasured on yours.

**Whether the encoding half is one model's habit or the pipeline's.** If it is the
extractor reformatting quotation marks, that is a prompt fix — "copy the span
byte for byte including punctuation" is already in my harness's schema description
and did not prevent it. If it is `collect/`'s flattening introducing curly quotes
the model never saw, that is **mine**, and it would mean the offset map and the
verifier disagree about the document. I cannot tell which from 34 cases on one
corpus, and the split is what makes the question askable.

## 6 · Scope

```
verify.py            one flag on Rejection, set after the exact test fails
runner.py            carry the count out on ExtractionRun
the run summary       one more number
behaviour            UNCHANGED. Every quote that is rejected today is still
                     rejected, for the same reason, at the same point
```

No contract change, no schema change. `claim.quote_verified` keeps its meaning
because nothing that fails today starts passing.
