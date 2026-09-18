# `judge extract --dry-run` takes the write gate, and it has nothing to write

**One line in `judge/cli.py`. `reweight` already does it; `extract` does not.**

*anooj · 2026-09-18 · written as a proposal and then TAKEN the same day, on
anooj's instruction. The argument is kept here rather than compressed into a
commit message, because §3 and §4 are why it is one line and not a bypass.*

---

## 1 · The asymmetry

Three commands open a connection through `_connect`. Two of them gate on what
the run is actually going to do; one gates on what the command is called.

```
judge/cli.py:120   with _connect(writing="judge extract") as conn:
judge/cli.py:464   with _connect(writing="judge rebuild-cells") as conn, conn.transaction():
judge/cli.py:554   with _connect(writing="judge reweight" if args.apply else None) as conn:
```

*(Line numbers as of `bfb490c`, the commit before this change. They have since
moved; the middle one is the only line unaltered by it.)*

`writing=` is not a connection option. It turns on `judge/writeguard.check()`,
which refuses exactly one pairing — `ENVIRONMENT=development` plus a database
that is not this machine. So line 120 means: **a dry run is refused from any
laptop whose flag is set, against the only database that has the rows it wants
to read.**

## 2 · The change

```diff
-    with _connect(writing="judge extract") as conn:
+    with _connect(writing=None if args.dry_run else "judge extract") as conn:
```

Nothing else. `reweight` is the precedent and the spelling is copied from it.

## 3 · Why this is the weaker claim, not the stronger one

`reweight --apply`-less is already permitted through this door, and **its dry
run writes.** It opens `conn.transaction()`, calls `apply_reweight`, computes
cell deltas from the rows it just wrote, and then raises `_RolledBack` to
discard them. That is a deliberate write-and-roll-back, and it was accepted.

`extract --dry-run` does not do that. Between the connection and the return it
runs two statements and both are `SELECT`:

```
ExtractionLedger.already_extracted()   SELECT over thread_extraction
ExtractionLedger.yield_rate()          SELECT count(*) ... FROM thread_extraction
```

then prints, then `return 0` at `judge/cli.py:136` — **above** the `--driver`
branch, above `_extract_from_export`, above the only `conn.commit()` on the
path. No transaction is opened at all. So the case for dropping the gate here
is strictly stronger than the one already in the tree: `reweight` argues *the
writes are rolled back*; this argues *there are no writes*.

The function already treats `--dry-run` as a distinct mode at
`judge/cli.py:112` — `budget is None and not args.dry_run` is what lets a dry
run proceed with no spend cap set. **The connection is the one place that did
not get the memo.**

## 4 · What it is NOT

**It is not a workaround for #328 and must not be written up as one.** #328 is
that `scripts/fetch_model.py` reaches `claim`, `board_entry` and `cell` without
passing any gate, so the riskier operation is unguarded while the safer one is
refused. This change does not touch that path, does not widen what may write
from anywhere, and does not move `rebuild-cells`.

The relationship is the opposite of relief. After this, `judge extract` from a
development laptop against the shared database still refuses — the moment it
would spend money and write claims, which is the whole point. What becomes
possible is the command that **cannot** write. #328's defect is a write path
with no gate, and it is exactly as open tomorrow as today.

## 5 · What the dry run still will not tell you

Stating the ceiling, because the change is easy to oversell.

The dry run returns before `_extract_from_export`, so **it never opens the
export.** It reports the ledger and the budget:

```
  <read> threads read at this pipeline version, <zero_yield> of them yielding nothing
  <seen> threads already extracted and will be skipped
  --dry-run: nothing extracted, nothing charged
  budget would allow roughly <n> threads
```

A malformed export, a thread with no `flattened_text`, an `offset_map` that is
a list of dicts rather than `OffsetMapping` — none of those are caught here.
`export_source.load` is pure file reading with no database and no spend, so
teaching `--dry-run` to call it and print the `skipped` list is a real and
separate improvement. **Deliberately not folded in**, and filed as its own item
together with §6's AST test, as **#355**.

**`seen` was taken and is now printed.** `seen = ledger.already_extracted()`
was computed before the branch and its only reader was below the dry-run return,
so on that path it was a query whose result nothing read — rule 9's shape, on a
path whose whole job is to report counts. The print moved ABOVE the branch
rather than being duplicated into it, so both paths report it once and the
unread state is gone rather than patched.

The comment inside the dry-run branch is not an objection to this. It refuses to
report *pending* threads, because that count needs the thread list `collect/`
owns. `seen` is *already extracted* - a different number, read from
`thread_extraction`, carrying its own population. It is the one this lane can
state honestly.


## 6 · Test

Nothing currently covers `_connect`'s `writing=` selection for any command —
`tests/test_writeguard.py` has ten tests and all ten are over `check()` itself,
none over which commands call it. So `reweight`'s `args.apply` gating is
untested too, and this change lands on bare ground.

**Shipped**, in `tests/test_judge_extract_dry_run_gate.py`: `psycopg.connect`
monkeypatched, `ENVIRONMENT=development` and a remote DSN, four cases -

    a dry run is not refused
    a dry run issues only SELECTs, opens no transaction and never commits
    a dry run prints the already-extracted count
    the same command WITHOUT --dry-run is still refused

Verified by reverting the one line and re-running: the first three fail, the
fourth passes. The fourth passing under both is the point of it — it is the half
that must not change.

The structural alternative is the AST test root `CLAUDE.md` already describes
for `collect/cli.py` — every `_connect(writing=…)` in a command whose parser
declares `--dry-run` or `--apply` must be conditioned on that flag, and an
unclassified command fails. **Filed as #355 rather than shipped here**, and not
for effort: a test written in the same commit as the two commands it describes
agrees with them by construction. Its value is catching the NEXT command, and
that value is the same a day later — whereas the appearance of coverage it would
have lent this commit is worth less than nothing.
