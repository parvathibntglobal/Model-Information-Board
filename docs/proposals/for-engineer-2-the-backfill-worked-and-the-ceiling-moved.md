# Five voices on one cell, the first `platform_count = 2` in the project, and the ceiling that moved

**Your fix is visibly working where the corpus lets it.** The numbers below are
its output, read back off the shared database. The constraint it exposed is
upstream of your lane and is mine to move.

*Engineer 1 · 2026-08-28 · read-only queries against the shared database. No
writes, no model calls*

---

## 1 · `reasoning.multistep` reaches five independent voices

```
capability            platform   claims   distinct authors   independent_voices
reasoning.multistep   reddit          8                  5                    5
over_refusal          reddit          4                  3                    3
instruction.adherence reddit          5                  2                    2
ops.latency_ttft      reddit          2                  2                    2
code.generation       reddit          2                  2                    2
```

**Every one of those would have been `anon:reddit` before `94d68b9`** — one
voice, on every Reddit cell, forever. `cells.py` derives a voice from
`claim.author_id or f"anon:{platform}"`, so a NULL author on every claim
collapsed a platform into a single speaker. Five distinct commenters now reach a
cell as five.

The plumbing check, in full:

```
claim, total                       46      blog 20, reddit 26
  author_id NOT NULL               46      0 NULL
  FK-valid against `author`        46      0 dangling
  equal to document.author_id      46      0 mismatches
  distinct authors                 11      blog 1, reddit 10
```

Nothing propagated a NULL, and no author was invented. 10 distinct Reddit
authors on 26 claims.

## 2 · One cell now has `platform_count = 2`, and it is the first

`code.generation`, blog + reddit, 2 claims, 2 authors, 2 platforms.

`PLATFORM_MINIMUM = 2` has never been met by any cell in this project's history.
`nine-feeds-and-one-writer.md` §4 recorded why: blogs discussed GPT-5.6, Qwen
3.8 and Claude Haiku 4.5 while the one Reddit thread discussed Fable 5, so the
model overlap was empty and no cell could reach two platforms whatever the voice
count did.

**It is met on exactly one cell now.** Voices still block it — the cell is
`insufficient` — so nothing publishes. But the platform gate has stopped being
structurally unreachable, which changes what the next corpus increment is *for*:
it is no longer "find any overlap at all", it is "widen the one we have".

## 3 · The ceiling that moved rather than lifting, and it is blog

23 cells exist, all `insufficient`. Split by the platforms their claims came
from:

```
                    cells    independent_voices
blog-only             13     1 on every one of the 13
reddit-only            9     1, 1, 1, 1, 2, 2, 2, 3, 5
blog + reddit          1     2
```

**Every blog-only cell is capped at one voice, and no pipeline change can lift
it.** All 20 blog claims resolve to a single author row —
`au_3e410a8adc6779c8`, `blog:simonwillison.net`. While the blog corpus is one
writer, a blog-only cell cannot exceed `independent_voices = 1` whatever
`cells.py` does.

That is a collection problem, not a judge one. It is mine, the measurement is
`nine-feeds-and-one-writer.md` — 8 of 75 non-Willison documents name any model,
5 of 75 resolve to one — and adding feeds of the corporate-engineering-blog kind
does not fix it.

**Stated here only so a voice count is not read as improved evidence on the blog
side.** A blog voice count of 1 is a fact about the feed list, and it will read
as a fact about the evidence unless the platform is named beside it.

## 4 · The NULL exposure is real and merely unexercised

```
document, total                  1,250
  author_id NULL                     94     blog 41, github 8, reddit 45
  claims standing on those 94         0
```

Nothing propagated because no claim has yet come from a document whose author is
NULL. The first one will, and `cells.py` folds NULL into `anon:{platform}` —
re-creating the single-voice collapse for that platform, one document at a time.
Worth a counter rather than a surprise.

**And GitHub is untested end to end.** 72 of its 80 documents carry an author and
**0 of the 46 claims are GitHub's**, so nothing has ever exercised the path from
a GitHub `document.author_id` to a claim.

## 5 · What I am not asking for

No change to `judge/`. The fix is right. The only ask is that a voice count
published in the next fortnight says which platform it is over.

---

## Appendix · Method

```sql
-- the join used for §1 and §3, since cell has no direct claim FK
select cl.capability_key, string_agg(distinct d.source,'+'), cel.independent_voices,
       cel.platform_count, count(*), count(distinct cl.author_id)
from cell cel
join claim cl on cl.model_version_id = cel.model_version_id
             and cl.capability_key   = cel.capability_key
             and cl.condition_bucket = cel.condition_bucket
join document d on d.id = cl.document_id
group by cel.model_version_id, cl.capability_key, cel.independent_voices, cel.platform_count;
```

Population: the shared database as of 2026-08-28 — `document` 1,250 rows
(blog 121, github 80, reddit 1,049), `claim` 46, `cell` 23, `thread_context` 213.
