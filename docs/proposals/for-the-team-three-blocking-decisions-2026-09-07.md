# Three decisions, one message, because they block each other

**2026-09-07. Nothing here has been implemented. Two other things from the same
work needed nobody and are done — the bot-list detector and Hacker News's
`is_self_post` mapping.**

Read in order. The first decides whether Hacker News is in the pipeline at all;
the other two are small and are only here because they are in the same PR's
path.

---

## 1 · Is the entity gate a reading rule or a resolution rule?

**The figure: the entity gate resolves 11 of 511 comments — 2.2% — across the
two Hacker News subject threads the smoke run stored.** Measured against the
real 342-model registry population plus the declared seed surfaces, from stored
payloads, no new requests
(`docs/measurements/entity-gate-on-hn-threads-2026-09-07.json`).

If the gate stays as it is, Hacker News contributes the ~2% of comments that
name a model explicitly and nothing else — and on the measured evidence that is
not where the evidence is. The standalone sweep found a thread that was **a bare
GitHub link at 678 points whose evidence — a quoted price, the pricing URL, an
expiry date, a routing claim — was entirely in its comments**, none of which
repeat the model's name.

### Not an inheritance question, and that distinction is the ask

**Thread-subject inheritance is ruled out and I am not reopening it.**
`docs/proposals/for-engineer-2-inherited-subjects-and-family-claims.md` records
the reason and the measurement: 32 of 53 candidates named a second model, and
the 21 survivors were all in two announcement threads — the population that
produced the four vendor-copy claims already on staging. That ruling stands.

What it ruled on was **resolution**: whether a *claim's subject* may come from
outside its own quote. The Hacker News question is a different one and it sits
one stage earlier:

```
RESOLUTION RULE   what does a mention refer to, and what may a claim be filed
                  against?  -> declared surfaces only, no mechanical expansion,
                  family words attributable to no single model (ruling 2);
                  subject inheritance REFUSED.

READING RULE      what text constitutes this document?  -> the flattener,
                  `author_prose` excluding quoted spans, the 1,200-character
                  locality window (ruling 7).
```

**The entity gate is currently a resolution test applied to a reading nobody
chose.** On every platform in the corpus today, the subject is *inside* the
document the gate reads:

| | what the gate reads | where the subject is |
|---|---|---|
| Reddit post | `title` + `selftext` | the title, in the document |
| GitHub issue | `title` + `body` | the title, in the document |
| blog article | the extracted article | the headline and lede, in the document |
| **HN comment** | the comment body alone | **the story, in a different record** |

Hacker News is the first platform that puts the subject line in a separate
record. That is a platform-shape fact, not a claim about aboutness.

**Ruling 7 already drew this line and drew it the other way.** The locality
window constrains how far `topic` and `signal` may sit apart — and it
**exempts `subject` entirely**: *"Subject is deliberately unconstrained: naming
the model once is how a post establishes what it is about, and a blog naming it
in the introduction and reporting the failure in the conclusion is the ordinary
shape."* A blog gets 41,956 characters of slack for establishing its subject. An
HN comment gets none, because its title lives 12 bytes away in another row.

**And GitHub already resolves it the way I am proposing.** `assemble_issue.py`
builds two shapes: `issue_body_only` and `issue_with_comments`. A GitHub comment
**never faces the entity gate alone** — it reaches the extractor inside a
`thread_context` flattened from the issue body plus its selected comments, with
one `offset_map`. 584 issues hold both shapes today. Nothing about that was
called inheritance, because the thread genuinely is one document for extraction
purposes.

### The ask

**Is the unit of triage the document or the thread?**

My recommendation: **the thread, for platforms whose subject line is a separate
record** — which today is Hacker News, and which will be Hugging Face
discussions on the same argument. Concretely: the entity gate resolves against
the flattened thread text; a thread whose root resolves is kept whole and E3's
specificity ranking picks the children; a verdict records which unit it was
reached at, so a survival figure can never pool the two.

**Two things make that safe rather than inheritance by another name**, and both
already exist:

- `judge/pipeline.py:subject_was_inherited` derives, **in code and never from
  the extractor**, whether a claim's subject came from outside its own quote.
- `quote_subject_verdict` returns `QUOTE_NAMES_NOTHING` for exactly that case,
  and its own docstring already anticipates this platform: *"a comment
  inheriting a thread root's subject lands here."*

So a thread-level *reading* cannot smuggle a resolution claim past the
inheritance ruling: every claim it produces is still labelled, and the weighting
decision on `QUOTE_NAMES_NOTHING` stays yours and stays unchanged.

**If the answer is no**, that is defensible and it needs saying out loud on the
page: Hacker News yields ~2%, and rule 4 means the board cannot render that as
"engineers report no problems on this platform".

**What blocks what.** This decides whether the HN adapter's `thread_root_id`
linkage is load-bearing or decorative, and it should be answered before the
first real HN sweep — a corpus gathered at the wrong unit is a re-fetch, not a
re-sieve.

---

## 2 · The robots precedent, and it is narrower than I wrote it

I said arXiv and X were both open questions. **Only one of them is.**

Measured 2026-09-07, robots.txt on the host each adapter actually calls
(`docs/measurements/new-platform-robots-2026-09-07.json`):

```
export.arxiv.org             200, Disallow: /      NO PRECEDENT HERE
twitter241.p.rapidapi.com    200, Disallow: /      same reading as ...
reddit34.p.rapidapi.com      200, Disallow: /      ... which we already harvest
oauth.reddit.com             200, Disallow: /
dev.to                       200, API paths permitted
huggingface.co               200, Allow: /
hn.algolia.com               404, no rules at all
api.github.com               404, no rules at all
```

**X inherits a precedent.** Its route is a RapidAPI scraper provider —
`SCRAPER_PROVIDER=twitter241`, the same gateway and the same `RAPIDAPI_KEY` as
Reddit. `twitter241.p.rapidapi.com` serves `Disallow: /` exactly as
`reddit34.p.rapidapi.com` does, and we harvest that today under
`reddit-via-rapidapi`, whose live precondition is the access path and not
robots. So X is not a new question about robots. It is the *existing* Reddit
question — reseller credentials, display requirements, deletion against an
immutable store — one platform wider, and it should be escalated **with**
Reddit's rather than separately, because it is one question about one gateway.

**arXiv is the one genuinely open, and it is open in the harder direction.**
There is no precedent to inherit: `api.github.com` has no robots.txt at all, so
GitHub's ruling never had to say what an explicit `Disallow: /` on an API host
means. arXiv does say it, on the host that serves its documented Atom API, while
publishing request-rate guidance for that same API — one per three seconds, one
connection, which we honour. Those two facts point opposite ways and only a
reading of arXiv's API Terms of Use settles it.

**The ask:** read arXiv's API Terms of Use. If robots governs the documented API
path, arXiv is out and nothing else changes; the other four stand either way.

---

## 3 · Does `document.lang` get un-reserved?

One line in `contract/column_states.yaml`:

```yaml
    lang: {state: write_only, reviewed: true, why: "…"}   # was: reserved
```

`document.lang` is NULL on 6,502 of 6,502 rows, which is why
`triage.gates.wrong_language` reports UNAVAILABLE for the whole corpus. **Two of
the five new platforms declare a language per document** — dev.to's `language`
and X's `lang` — and that is the platform's own field, not an inference, so rule
8 makes it a recorded field rather than a gate.

**No code is waiting on this.** The value is already parsed and carried
(`DevtoHit.language`, `XPost.lang`, `DocumentDraft.lang`) and
`WriteReport.lang_declared_by_platform` counts what would land: 2 of 2 dev.to
documents in the smoke run. The writer deliberately does not store it, because
adding it moved the discovered state to `write_only` and
`tests/test_column_states.py` failed by name — the guard working, not an
obstacle.

Enabling it is that YAML line plus `lang` in `_INSERT` and in `as_row`, in one
PR. It does **not** make the gate runnable — no detector is installed — but the
input cannot be back-filled later without re-reading every payload, which is
why it is worth a line now rather than after the next sweep.

---

## Why one message

(1) decides the unit a Hacker News corpus is gathered at. (2) decides whether
arXiv is a source at all. (3) decides whether two platforms' documents carry a
field from their first row. All three land in the same PR path, and answering
them one at a time means either the sweep waits or it runs and is re-fetched.
