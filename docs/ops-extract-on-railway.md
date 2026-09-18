# Running extraction on the Railway container — four steps and one trap

**For whoever has Railway access. You do not need to understand the pipeline to
run this; you do need to not run it the wrong way, and the wrong way is §T.**

*anooj · 2026-09-18 · every figure below measured on this host or read from the
working tree on this date. Where I could not measure the container, it says so.*

---

## 0 · What this is, and the one thing that makes it awkward

`judge extract` turns exported threads into `claim` and `cell` rows. It calls a
language model, so it spends money, and it writes to the shared database.

The awkward part is the input. **The container cannot build its own export.**
`scripts/export_contexts_for_extract.py` needs two things, and the container has
one:

| | on the container |
|---|---|
| `thread_context` + `document` rows | **yes** — same shared AWS DSN |
| the raw object store, for every `flattened_text_ref` and `text_ref` | **no** |

The raw store is a plain directory at `RAW_STORE_PATH`, **per-machine and
gitignored**, and `.dockerignore` keeps `raw_store/` out of the image. A
container's store holds only what a container fetched.
`docs/proposals/shared-raw-store.md` is the standing proposal to fix that,
scoped 2026-08-20 and not built.

**Extraction itself needs no store at all** — the export inlines
`flattened_text`, `offset_map` and `raw_text_of`, so nothing resolves a ref.
Regenerating the export is the only step that touches the store. That asymmetry
is why the file travels instead of the run moving to the file.

> **Unmeasured, and cheap to measure.** I have not checked what the container's
> store holds; I cannot from a laptop. On ANOOJ,
> `scripts/_blob_presence_check.py` reports **151 of 4,144 thread_contexts with
> an unreadable flattened ref** (hackernews 58, devto 56, reddit 25,
> huggingface 10, blog 1, one malformed root). That is this machine's number and
> says nothing about the container's. The script is read-only, is in the image,
> and was written for exactly this comparison. If you want the
> regenerate-there option properly closed rather than assumed, run it on the
> container first and compare the id sets.

---

## 1 · Set two variables on the service

```
OPENROUTER_API_KEY              judge/extract/client.py:277
EXTRACTION_DAILY_BUDGET_USD     judge/extract/budget.py:176
```

**Check both rather than assume either.** I cannot see the service's variables
from a laptop, so I am not claiming they are unset — only that the run needs
them and that the second is listed in `docs/railway-deployment-plan-2026-09-14.md`
§5 as per-deployment while the first is listed as per-person, which is the
pairing worth looking at. Unset `EXTRACTION_DAILY_BUDGET_USD` and the run
refuses outright, saying so; an unset `OPENROUTER_API_KEY` fails at the first
call, after the run has already started.

`EXTRACTOR_MODEL` and `OPENROUTER_BASE_URL` have defaults and can be left alone.
`DATABASE_URL` is already set and is read **directly** by `judge/cli.py`, not
through `MODELBOARD_DB` — that variable only steers `serve.py`.

**Give the container its own OpenRouter key rather than reusing a laptop's.**
`EXTRACTION_DAILY_BUDGET_USD` is a *per-process* cap. One key shared across the
container and three laptops means the effective daily ceiling is four times the
configured number, and nothing anywhere computes that or would notice it being
exceeded. This is §6(b) of `docs/railway-deployment-plan-2026-09-14.md`, and
this run is the first one where it bites. The spend *ledger* is already shared —
the budget is seeded from `spend_ledger.spent_today()` — so it is only the cap
that is per-process.

---

## 2 · Get the export onto the container

**The file travels. It cannot be rebuilt there (§0) and it cannot ride in the
image** — `_export_extract/` is `.gitignore:106`, so a build from a git checkout
never sees it, and as of this change `.dockerignore` excludes it too, so a build
from a working tree does not either. That second line is deliberate: 17.8 MB of
full thread text baked into a layer by accident is not a delivery mechanism.

What is travelling, measured on this host 2026-09-18:

```
_export_extract/threads     1,655 JSON files     17.8 MB
```

**It needs a persistent location.** The container filesystem is ephemeral, so a
copy into a running instance is gone at the next deploy — fine if you run the
extraction immediately after, and not fine if you expect to re-run it. Put it on
the mounted volume if there is one. I cannot verify from this repo whether a
volume is provisioned: there is no `railway.json` in the tree, and §3 of the
deployment plan had the storage split still undecided on 2026-09-14.

Do **not** commit the export to get it there. `.gitignore:104-106` says why:
thread text, not source, and rebuildable on a machine that has the store.

---

## 3 · Dry-run first, and read the two numbers

```
python -m judge.cli extract --dry-run
```

No export needed and nothing charged. Real output, run from ANOOJ against the
shared database on 2026-09-18 with `ENVIRONMENT=development` — which is the
pairing that was refused until the change that added this section:

```
  530 threads read at this pipeline version, 349 of them yielding nothing
  530 threads already extracted and will be skipped
  --dry-run: nothing extracted, nothing charged
  budget would allow roughly 4692 threads
```

**Line 4 is the one to read before step 4.** If the budget allows fewer threads
than the export contains, the run stops partway, and you want to know that
before it happens rather than after. 4,692 against 1,655 threads is comfortable;
that is a function of `EXTRACTION_DAILY_BUDGET_USD` and of what has already been
spent today, so it is not a constant.

**Line 2 is already extracted, not pending.** There is no pending count here,
and inventing one would need a thread list this lane does not own. Both figures
are scoped to the current `PIPELINE_VERSION` — a version bump resets them to
zero, which is correct and reads alarming the first time.

This command runs from a laptop as well as from the container: it takes no write
gate because it opens no transaction.

> **`python -m judge.cli`, not `judge`.** There is no `[project.scripts]` in
> `pyproject.toml`, so there is no `judge` console script anywhere.

---

## 4 · Run it, batched

```
python scripts/run_extraction_batched.py --from-export <path>/threads --driver new-evidence
```

**Three things in that command are load-bearing.**

`run_extraction_batched.py`, **not** `python -m judge.cli extract`. The CLI
passes `resolver_factory=None`, so claims resolve only through
`resolved_version_id`, which nothing populates — every claim is verified,
skipped, and stored nowhere. That is the "verified but stored nothing" symptom
the composition root exists to fix.

**Batched**, not `scripts/run_extraction.py`. That one commits once, at the end.
A container restart mid-run discards every claim *and* the ledger rows that
would let a resume skip work already paid for. On a platform that restarts, that
is the difference between losing a batch and losing the run.

`--driver`. Without it the nightly close is skipped and labels are not updated,
which the command will tell you. `new-evidence` is right when the claims are new
and wrong when you are re-running after a threshold change — only you know which.

Afterwards, the run reports what verified and what reached the database. If it
says **"VERIFIED BUT NOT STORED"**, read that line: it means claims passed
verification and their documents could not be weighted, or their models resolved
to no tracked row. That is a result, not a crash.

---

## T · The trap: `railway run` is not running it on Railway

⚠ **`railway run <cmd>` executes the command on YOUR LAPTOP with the
deployment's variables injected.**

It would hand this machine `ENVIRONMENT=production`, which satisfies
`judge/writeguard.py`, and then run a write against the shared database **from
the machine that has the build fixtures** — which is the exact pairing the guard
exists to refuse. It looks like running it on Railway. It is the hazard wearing
the deployment's clothes.

The way in is `railway ssh` into the running container, or a second service
built from the same image with a different start command. `CMD` is
`["python", "serve.py"]` and there is no Procfile or job runner, so the
container serves the API and nothing else. **I cannot verify from this repo
which of those your Railway setup allows.**

---

## What the guard does and does not do on the container

Worth knowing before you run a write there, and it is the existing state rather
than anything this runbook introduces.

`ENVIRONMENT=production` on the deployment, so `writeguard.check()` returns
early. In the guard's own words, that early return *"does NOT assert a fixture
check runs here: judge/ does not call preflight(), so on a non-dev flag NO
fixture check runs on this path."*

So the container writes claims and cells with no fixture check at all. Six
container hostnames already wrote these tables between 2026-09-14 and 09-16 via
`scripts/fetch_model.py`, which reaches the same code without passing any gate —
that is issue #328, and it is open.
