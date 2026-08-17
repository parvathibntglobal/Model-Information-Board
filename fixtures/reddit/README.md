# A real Reddit thread, unpolished — for `offset_map`

**`thread-1u1b22l-getPostComments.json`** · 444,807 bytes · V1 `getPostComments`
· fetched 2026-08-17 · content hash `1694ae60…f69bfa35f`

> Engineer 2 asked for messy rather than clean. This is a live payload with
> nothing removed, because every case that makes `offset_map` hard is a case a
> constructed fixture would not have thought of.

**Source:** `https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/introducing_claude_fable_5/`

Retained for verification and reprocessing, like anything in `raw/`. **Never
republished** — published content is quote + attribution + link.

---

## Why this thread and not the first one that came back

14 threads were fetched and scored on how many of the four requested cases they
carried. **11 carried all four**, so one thread is enough and two are not needed.
This one was chosen from those 11 because it reaches **depth 9**, which is the
deepest V1 will return — so flat-vs-raw offset drift compounds as far as the
platform allows.

## The four cases you asked for, located

| case | where | body |
|---|---|---|
| **deep nesting** | `t1_oqokyvp` d6 → `t1_oqom4s8` d7 → `t1_oqop8ge` d8 → `t1_oqovs4n` d9 | an unbroken four-generation chain, not four unrelated deep comments |
| **deleted** | `t1_oqocg0h` d0 | `[deleted]` — the **author** removed it |
| **removed** | `t1_oqoimjm` d0, `t1_oqr6lad` d1 | `[removed]` — a **moderator** removed it |
| **emoji in a child** | `t1_oqosfnq` d1 | `please check 😄 [https://…` — depth 1, not the root |

`[deleted]` and `[removed]` are **bodies, not absences.** The comment exists,
occupies a position in the tree, and has those nine characters as its text.
Dropping them would renumber every sibling after them, which is why
`RedditComment.is_deleted` / `.is_removed` recognise them rather than filtering.
They are also different facts — author versus moderator — and are kept apart.

## Four more hazards it carries that nobody asked for

Found while checking the four, and the reason a real payload was worth the bytes:

- **HTML entities in 6 bodies** — e.g. `&gt;Unbelievable they can't even include it in a $200/mo plan`. `&gt;` is four characters that render as one. **This is the same class of problem as emoji translation** and arguably the more common one: a substitution that changes length, mid-body. If `offset_map` handles emoji it probably handles this, but it is worth a segment test either way.
- **2 blockquotes** — `sieve.author_prose` strips these, so a quote extracted from one has no author. The flat/raw drift and the author-prose exclusion interact here.
- **3 comments with no `author_fullname`** — deleted accounts. `author_external_id` returns `None`, so `claim.author_id` is NULL and FR-17's voice count must not treat three NULLs as one voice.
- **8 edited comments, 19 bodies of 5+ lines, 1 `distinguished` mod/bot post.**

## What it does NOT cover — check these elsewhere

- **No unsized `more` markers.** All 101 markers on this thread report a count, so `hidden_branches_unsized` is exercised **only at zero**. See below; this is a finding, not an oversight.
- **No code fences.** `sieve`'s `fenced-code` exclusion is untested by this thread.
- **No empty body.** Present-but-blank is a distinct offset case and is absent here.
- **Depth stops at 9** because V1 stops at 9. Deeper trees exist and are unobservable through this endpoint.

## Coverage, and one thing that did not replicate

```
observed 195 of at least 818; at least 623 hidden across 101 branches
coverage_ratio 23.8% — an UPPER bound, because the denominator uses a floor
```

**Across all 14 threads: 1,285 `more` markers and zero unsized.** The
`assemble_thread` refusal cites a thread where 126 of 252 markers reported no
count. That shape did not recur once here.

So `hidden_children_min = sum(reported) + count(unsized)` is still the right
form — an unsized marker does guarantee at least one hidden comment — but on
this sample the second term contributed **nothing**, and the 126/252 case
remains unexplained. It may be depth-related, size-related, or specific to that
thread. Worth knowing before treating `hidden_branches_unsized` as a column that
will usually be non-zero.

## How to read it

```python
from collect.adapters.reddit_comments import parse_thread
import json, pathlib

payload = json.loads(pathlib.Path(
    "fixtures/reddit/thread-1u1b22l-getPostComments.json").read_bytes())
parsed = parse_thread(payload, url="https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/")

parsed.comments      # 195, tree order, each with parent_id and thread_root_id
parsed.coverage      # the four numbers plus the two witnesses
parsed.deleted       # ( t1_oqocg0h, )
parsed.removed       # ( t1_oqoimjm, t1_oqr6lad )
parsed.max_depth     # 9
```

**Nothing here assembles.** `parse_thread` returns comments and coverage; there
is no `flattened_text`, no `offset_map` and no child selection, and
`tests/test_reddit_comments.py` asserts their absence. `assemble_thread` still
refuses — the selection cannot be bounded, and the four coverage columns have
nowhere to be written until #5 lands them.

## Removal

This is a build fixture, not seed data. It carries no `provenance` row and
`assert_no_fixtures` does not look at it. Delete it when `offset_map` has real
`thread_context` rows to test against.
