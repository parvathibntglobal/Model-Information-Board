# `KNOWN_BOT` has reported UNAVAILABLE since it was written. Here is the first measured evidence of what it is worth

**Seven accounts that GitHub declares `type: User` and that are plainly
automation.** `user.type` catches GitHub Apps and cannot catch an automation
running on an ordinary account, and the `[bot]` suffix misses all seven. Neither
signal we have sees them.

Proposing the list rather than writing it: `contract/` is shared, and what the
list keys on is a ruling with a false-positive cost measured in dropped people.

*Engineer 1 · 2026-08-31. Population: 2,016 comments across 586 GitHub issues,
fetched the same day.*

---

## 0 · What `user.type` does settle, now that the denominator is real

The earlier caveat on this — *"the suffix and the type agree on all 148, but the
denominator is TWO accounts, not 148"* — is resolved, and in `user.type`'s
favour:

```
  comments                          2,016
  type: Bot                           200   from 26 distinct GitHub Apps
  type: User                        1,816   from 1,073 accounts
  suffix / type disagreements           0
```

**Twenty-six apps, not two**, all following GitHub's `[bot]` convention because
the platform renders it. `is_bot` keying on `user.type` is correct and this
proposal does not touch it.

## 1 · What it does not catch

```
  account                            comments   issues   user.type
  tenstorrent-github-bot                   33        7   User
  Issues-translate-bot                      4        2   User
  raycastbot                                1        1   User
  QAbot-zh                                  1        1   User
  doyouacceptcrypto-bot                     1        1   User
  FacultativeObligatoryBotContract          1        1   User
  happier-bot                               1        1   User
  ------------------------------------------------------------
  7 accounts, 42 comments, 13 distinct issues
```

These are automations on **personal access tokens**, not GitHub Apps. The
platform has nothing to declare about them and correctly says `User`. The suffix
heuristic misses every one — `tenstorrent-github-bot` does not end in `[bot]`.

## 2 · What they would contribute, and I have to correct the framing first

**The obvious version of this argument is wrong, and it is worth saying so
before the right one.**

The tempting claim is that `tenstorrent-github-bot` at 33 comments could
dominate a cell and that `max_author_share` would not catch it. Both halves are
false, and `judge/curate/gate.py:count` is explicit about why:

> *Count PEOPLE, not posts. A voice contributes once, at its highest-weighted
> claim. Someone who posts five times about the same capability is still one
> person, and letting the five sum would let one enthusiast clear the gate
> alone.*

So 33 comments is **one voice**, not 33, and across 7 issues at most. And if it
were a cell's only voice, `max_author_share` would be 1.0 against a 0.50 cap and
`SINGLE_AUTHOR_DOMINATES` would fire. **Domination is the case the gate already
handles.**

### The real exposure is smaller per cell and worse for the board

A bot that is **one voice among three** passes every gate we have:

```
  n_eff >= 3.0            a third voice is what reaches it
  platform_count >= 2     unaffected
  max_author_share        ~0.33 against a 0.50 cap - comfortably inside
```

It is not domination. It is **a third voice that is not a person** — manufactured
corroboration, arriving at exactly the threshold that separates *"someone said
this"* from *"this is probably true"*, which `collect/CLAUDE.md` calls the only
thing corroboration buys.

And that threshold is where almost the whole board sits:

```
  cells by independent_voices, 105 cells today
    1 voice   78        <- 74%
    2 voices  13        <- one spurious voice is decisive here
    3 voices   7
    4+         7
```

**91 of 105 cells have two voices or fewer.** A fake third voice does not tip a
cell that was going to publish anyway; it tips the ones sitting one voice short,
which is most of them.

That is the case for `KNOWN_BOT` in one sentence: **the gate already stops a bot
that shouts, and has nothing to stop a bot that nods.**

## 3 · What the list should key on, and why not the name

**Not the name.** The same argument that makes `user.type` right for GitHub Apps
makes a name heuristic weak here, and `StoredComment.is_bot` already records it:

> *It is a STRING HEURISTIC over a name a human can choose: a person may register
> `notabot` or a helpful maintainer may be called `releasebot`, and neither is a
> GitHub App.*

The seven above make that concrete rather than hypothetical. **Only one or two of
them are confidently automation.** `tenstorrent-github-bot` is org-prefixed, 33
comments across 7 issues, and reads as CI. But `happier-bot`, `raycastbot`,
`QAbot-zh`, `doyouacceptcrypto-bot` and `FacultativeObligatoryBotContract` have
**one comment each**, and from the login alone I cannot tell a joke handle from
an automation. A `*bot*` pattern sweeps up all five.

**Dropping a person is dropping a voice**, and on a board where 74% of cells have
one voice, five wrong drops is not a rounding error. Rule 4's territory: an
absence we caused reads as one we found.

### Proposed: a curated list keyed on the numeric account id

```yaml
# contract/harvest.yaml  (or its own file - your call)
known_bots:
  version: "1.0"
  reviewed_on: 2026-08-31
  # user.id, NOT user.login. A numeric id survives a rename; a login does not,
  # and a reused login merges two accounts - the same reason
  # StoredComment.author_external_id is user.id and Reddit canonicalises t2_.
  accounts:
    - id: "<user.id>"
      login: tenstorrent-github-bot     # for a human reading the diff only
      reason: >-
        org CI account. 33 comments across 7 issues, all release/build notices.
      evidence: docs/measurements/comments-shapes-and-the-legacy-weights.md
```

Three properties I would argue for:

1. **Ids, not names.** Above.
2. **A `reason` per entry, required.** A list of handles with no reasons cannot
   be reviewed and cannot be un-done when an account turns out to be a person.
3. **Explicit membership only — no patterns.** The moment a pattern is allowed,
   the review that makes this safe stops happening.

## 4 · And it should ship as a FLAG before it is a gate

**Rule 8, and I think it binds here.** The list's error rate is unmeasured
against any population it did not choose — I picked these seven by grepping
logins, which is exactly the heuristic §3 argues against. A gate built on that
would drop documents, and a wrong drop is invisible: the document is simply not
there.

So:

```
  now      write `filter_reasons = ['known_bot']`, keep status = 'kept',
           keep author_id. The row is flagged, countable, and still a voice.
  measure  count how many cells contain a flagged voice and what their
           n_eff would be without it. That is the error-rate population.
  then     promote to a gate - status='filtered', author_id NULL - on
           evidence, one-way, per rule 8.
```

The intermediate step costs one column write and answers the question the
promotion needs. Today nobody can say whether these seven touch a single cell,
because none of the 13 issues they commented on has been extracted.

## 5 · What I am asking for

Not the list. **The ruling on what it keys on**, and whether the flag-first
sequencing above is the right shape. If it is, I will write the seven entries
with their ids and reasons and put them up for the second pair of eyes
`contract/` requires.

`triage/gates.py` has reported `KNOWN_BOT: UNAVAILABLE` since it was written,
correctly — *"Rule 5 puts a filter rule in `contract/`, and the list does not
exist there"* — and it names `ClaudeAI-mod-bot` as already in the top five
authors of the 1,297-post Reddit corpus. **This is the same gap seen from the
GitHub side, with a number attached for the first time.** Reddit will need its
own entries and its own keying decision; `t2_` ids are the analogue.
