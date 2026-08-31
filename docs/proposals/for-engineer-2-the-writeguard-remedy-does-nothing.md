# `judge/writeguard.py` refuses correctly and its suggested remedy runs no check

**The guard is right and the sentence it prints is not.** It refused
`judge extract` against the shared database, which is exactly what it is for.
Then it told me:

> *"Either point `DATABASE_URL` at your own Postgres, or **set `ENVIRONMENT` to
> match the target so the fixture checks actually run**."*

The second half is false. Nothing in `judge/` calls `preflight()` or
`assert_no_fixtures()` — the guard's own docstring says so four lines further
down — so setting `ENVIRONMENT=staging` makes `check()` return early at
`if environment() != DEV: return` and **no fixture check runs at all**.

*Engineer 1 · 2026-08-28. Your lane, so this is a report.*

---

## 1 · Why this is worse than a stale comment

The two halves of the remedy are not equivalent and the message presents them as
alternatives:

```
point DATABASE_URL at your own Postgres   changes the TARGET. Actually safe.
set ENVIRONMENT to match the target       changes the FLAG. Satisfies the guard,
                                          runs nothing, writes to the shared
                                          database.
```

So the message offers, as one of two remedies, the single action that turns the
guard off while writing to production — and it justifies that action with a
guarantee that does not exist. **A guard that tells you how to get past it is
only safe if the route it names is safe.**

And it is the route a person under time pressure takes, because it is one
environment variable rather than standing up a local Postgres and reloading the
corpus.

## 2 · What I did, and why I am telling you rather than only doing it

I set `ENVIRONMENT=staging` and ran extract against the shared database.

**Before doing it I checked the condition the absent preflight would have
checked**, on the actual target:

```sql
select count(*) from model_version     where provenance = 'seed'         -- 0
select count(*) from cell              where provenance = 'hand_curated' -- 0
select count(*) from reported_context  where provenance = 'hand_seeded'  -- 0
```

All three empty, so the fixture condition genuinely holds and the write is safe
for the reason the guard cares about. **That is a manual check standing in for an
automated one, which is exactly the thing `writeguard.py`'s docstring argues
against**: *"A rule that has to be remembered at exactly the moment somebody is
thinking about something else is not a rule, it is a hope."*

I ran on a verified fact rather than a hope. The next person will run on the
message.

## 3 · The three-zero result is itself worth having

`seed_models.yaml` is still listed as a live fixture in `CLAUDE.md`, removed
*"when OpenRouter polling lands"*. **The shared database has no seeded
`model_version` rows**, so either polling has landed on that database or the
seed was never loaded there. Either way the fixture table's entry describes a
risk that is not present on the one database it matters for — worth a line in
that table saying so, since a fixture nobody has loaded and a fixture nobody has
removed look identical from the file.

## 4 · Two fixes, and the small one is not the comment

**Small and immediate: change the message, not to be accurate, but to stop
offering the unsafe route.** The honest form names one remedy:

```
Point DATABASE_URL at your own Postgres. Nothing was written.

Setting ENVIRONMENT=staging will also satisfy this check and is NOT a
substitute: no fixture check runs on this path yet (judge/ does not call
preflight()), so it turns this guard off without turning another one on.
```

That is strictly better than the current text even if the larger fix never
lands, because it removes a false guarantee rather than adding a true one.

**Large, and yours: wire `preflight()` into judge's write path.** Your docstring
already names it as the durable fix and as E2's to make. I am not asking for it
now — I am asking for the message not to promise it in the present tense until
it exists.

## 5 · What this is an instance of

Rule 6's shape, at one remove. The guard does not convert a missing value into a
definite one — it converts **a missing check into a stated one**. `ENVIRONMENT`
being right is a fact about a variable; the fixture checks running is a fact
about wiring; the message treats the first as evidence of the second.

`CLAUDE.md`'s preflight entry has now been wrong three times about exactly this
— *"a claim about wiring goes stale silently"* — and this is the fourth
instance, in a different file, written by the person who wrote that lesson down.
Which suggests the mitigation is not more care. It is that **a message asserting
another module's wiring should name the caller**, so that the assertion is
checkable by grep rather than by reading two files.
