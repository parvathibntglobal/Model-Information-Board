# Scheduling the nightly chain: three questions, and I am not answering them

**The build is done and the decision is not mine.** `collect ops run` is
complete, nothing blocks it, and one night costs about ten minutes and no money.
What is left is three choices with consequences outside `collect/`, so they are
here rather than in a commit.

*Engineer 1 · 2026-08-31. Raised, not resolved.*

---

## 0 · What is already settled, so the questions are the only open part

```
  the command        collect ops run          complete, at collect/cli.py:156
  runs to date       2                        both 2026-08-20, both by hand
  blockers           none                     0 unfinished job_run rows
  --only <stage>     built 2026-08-31         so a single stage can run alone
  --no-network       fixed 2026-08-31         it was a no-op for sweep-reddit
```

**Cost of one night at the current corpus:**

```
  preflight / recompute-window / load-capabilities    database only
  poll-registry        1 uncredentialed OpenRouter feed request, ~679 KB
  sweep-reddit        84 RapidAPI requests (12 subreddits x 7 pages)
                      ~3.5 min at 25/min. 1 quota unit per request against
                      1,000,000/month, so nightly is ~2,520 - under 0.6%
  score-documents     ~1.0 s/document on this host; a 200-document night
                      is ~3.5 min
  ----------------------------------------------------------------
  ~10 minutes, ~85 requests, no dollar cost
```

Two caveats on that quota figure, because it is the one someone will lean on.
The gateway header reads 1,000,000 and the plan page says 500,000; **which is
our billed allowance has never been settled** — it is a browser question, not a
call, and `docs/measurements/reddit-rate-and-quota.md` §1.4 declines to pick.
Either way nightly is under 0.6%. And the window resets on a rolling ~24 days,
not monthly, so "per month" above is approximate in the safe direction.

## 1 · Which machine

The chain has only ever run on a developer laptop. That laptop **sleeps**, and a
scheduled task on a sleeping machine does not produce a failure — it produces
nothing, which is indistinguishable from a night with no work.

```
  this machine        Windows 11. Task Scheduler, not cron.
                      .venv\Scripts\python.exe -m collect.cli ops run
                      working directory must be the repo root - .env is read
                      from it, and every credential the chain uses is in there
  what it needs       to be awake at the scheduled hour, and to hold the
                      credentials, and to hold the raw store
```

**The raw store is the part that is easy to miss.** It is a local filesystem
path, and `score-documents` can only score documents whose payload is on the
machine running it — 1,243 rows are NULL today for exactly that reason, and they
are Reddit documents somebody else fetched. **A chain that runs on a different
machine from the one that harvests will produce a second, disjoint hole of the
same kind.** Whatever we choose, the harvester and the scorer should be the same
host, or the store has to stop being local first.

*Not mine to choose: it is a question about what infrastructure we are willing to
run, and `docs/proposals/shared-raw-store.md` is the prerequisite for the answer
that is not "this laptop".*

## 2 · Is a nightly Reddit sweep wanted at all, before the terms ruling is revisited

`sweep-reddit` is the only wired stage that fetches, and it is the reason the
nightly run costs anything at all. **It is also the one under a ruling written
for a narrower purpose than nightly automation.**

The current ruling is `reddit-via-rapidapi`, basis
**`internal-development-only`**, made 2026-08-18. The question
`docs/measurements/reddit-rate-and-quota.md` explicitly declined to answer is
still open in its own words: *whether a measurement sweep is covered by the same
ruling as an evidence sweep.* A nightly unattended harvest is neither of the two
things that ruling was made about.

Three ways this could go, and I have no standing to pick:

```
  a  schedule it            the ruling covers it, nightly collection is what
                            the board is for, and the volume is trivial
  b  schedule the chain
     WITHOUT sweep-reddit   `--only` makes this a one-line change now.
                            score-documents, recompute-window and
                            load-capabilities are deterministic, local, and
                            free. The corpus stops growing on its own.
  c  do not schedule        until the ruling is revisited
```

**(b) is newly available and is worth naming**, because before `--only` the
choice was the whole chain or nothing, and that framing is what made this look
like one decision instead of two. The cheap deterministic half can run nightly
without settling the harvesting question at all.

*Not mine to choose: it is a terms question, and `contract/sources.yaml` carries
the ruling that would have to change.*

## 3 · Who reads the journal — and this is the one that decides whether any of it is worth having

`collect/ops/chain.py` opens with the premise the whole module exists to serve:

> Nine silent-failure defects were found in this lane in one fortnight, every one
> of them caught by **a person reading a number that was wrong in a way that read
> as an answer. Under cron there is no person.**

Everything the chain does about that is *preparatory*. It writes a stage's line
before doing the work, so a killed process leaves `started 03:00, never
finished`. It refuses rather than skipping, and every refusal names what it
starves. It reports absent counts rather than zeros. **Every one of those is a
message with no recipient until somebody reads it.**

So the failure mode of scheduling this without answering question 3 is not that
the chain breaks. It is that **the chain works perfectly and nobody notices it
stopped** — which is worse than the hand-run state we are in now, because a
hand-run has a person attached by construction. A green cron job is the most
convincing possible form of "nothing is wrong".

Today's session is the argument. Two stages that were wired, correct and never
invoked (`score-documents`, `assemble_github_documents` for its new documents)
sat unnoticed because nothing reports what did not run. Scheduling makes that
class of thing *more* likely, not less, unless the output has a reader.

What "a reader" could mean, cheapest first:

```
  1  a person, named, who opens the journal each morning
  2  the run posts its summary somewhere a person already looks
  3  an alert on the conditions that matter - a stage that errored, a stage
     whose refusal is NEW, a night that produced no documents at all
```

**(3) is the only one that scales and it is the one nobody has built.**
`collect/ops/alerts.py` exists and the 14-night burn-in it needs has never
started, because it needs nightly runs to compute a baseline against — which is
circular with this decision and worth naming as such rather than discovering
later.

*Not mine to choose, and this is the question I would want answered first. If
the answer is "nobody", my recommendation is (c) in question 2 and keep running
it by hand, because a hand-run we forget is visibly a hand-run we forgot, and a
cron job we forget looks exactly like a cron job that is working.*

## 4 · What I would do with an answer

Nothing here needs code. If the three answers are *this machine*, *(b) without
sweep-reddit*, and *a named person on the journal*, the whole change is a Task
Scheduler entry and a line in `docs/ops-nightly-chain.md`. If any answer is
different the shape changes, which is why it is not already done.

Detail and the measurements behind the cost table:
`docs/measurements/comments-shapes-and-the-legacy-weights.md` §10.
