# Scoping the shared raw store — the blocker was never the reader

**`RAW_STORE_PATH` points at a gitignored directory on one machine. The reader
wiring landed and the bytes did not become reachable: Engineer 2 can query the
database and cannot resolve a ref, because the ref names a path she does not
have.**

*Engineer 1 · 2026-08-20 · a joint decision, scoped and not built*

---

## 1 · The blocker, measured

```
RAW_STORE_PATH        raw_store            (relative, resolved per process)
.gitignore:12         raw_store/
on this machine       180 files, 8.6 MB
layout                raw_store/flattened/sha256/05/d2/05d2de39…
                      raw_store/raw/sha256/…
```

**And `_handoff/` works only because it inlines.** Each exported thread carries a
`raw_text_of` mapping of document id → text, so nothing resolves a ref. That is
why the export path has never hit this: it is not a pointer, it is a copy. The
cost of that is the whole reason to move — a copy cannot report
`MISSING`/`CORRUPT`/`TOMBSTONED`, so `RawStoreReader`'s four outcomes have never
run against anything real.

**Same shape as the database, and the database is the precedent.** Nobody proposed
shipping a copy of `model_version`; both lanes point at one Postgres. The store is
the other half of that and has been a local directory throughout.

## 2 · The content-addressed layout survives the move, and that is what makes it cheap

A ref is `<namespace>/sha256/<ab>/<cd>/<hex>` — an opaque string carrying a
namespace and a digest, and **no filesystem path semantics**. So:

- `build_ref` / `parse_ref` — **unchanged.** They compose and split a string.
- the two-level fan-out (`ab/cd/`) — **unchanged**, and it stops mattering: it
  exists so a directory does not hold 100k entries, and an object store does not
  care. Harmless to keep, and keeping it means the local and remote layouts are
  identical, which makes a migration a copy rather than a transform.
- `Namespace` with `evictable` / `tombstonable` — **unchanged.** It is policy, not
  storage.
- content hashing and verification — **unchanged**, and this is the part that
  makes a shared store safe: a corrupt object is detectable by the reader without
  trusting the transport.

**So the move is a copy of 180 files and a change of backend, not a re-design.**

## 3 · What changes in `rawstore.py` beyond the path

More than the path and less than a rewrite. `RawStore` currently does filesystem
work inline:

| what it does now | what a shared backend needs |
|---|---|
| `path.exists()` / `read_bytes()` | a `get(key)` that distinguishes absent from unreadable — the reader's `MISSING` vs `CORRUPT` already models this |
| temp file then `rename` for atomicity | an object `put` is atomic already; the temp-and-rename goes away rather than moving |
| `unlink` for `evict` | a `delete`, plus the fact that S3 deletes are eventually consistent — an evicted object may read for a moment, so `evict` needs to stop meaning "gone now" |
| `stat` for `PayloadStat` | object metadata; size and mtime come back differently and `PayloadStat` is where that lands |
| tombstone marker files beside the payload | either objects with a suffix or object tags. A tag is cheaper and less visible; a suffixed object keeps "list the namespace" working |
| directory walk for eviction candidates | a prefix listing, paginated. The only place the code has to learn that listing is not free |

**The honest summary: one interface with six methods, two implementations
(filesystem for tests, object store for real), and `evict` is the only one whose
*semantics* change.** Everything else is a substitution.

**And NFR-4 gets sharper, not looser.** 13 payloads are already missing from the
local store with no tombstone — `RawStoreReader` says so on every read. Today that
is one machine's problem. In a shared store it is a fact both lanes can see, which
is the point.

## 4 · The options, with what each costs

| | cost | what it buys | what it forecloses |
|---|---|---|---|
| **A · S3 or equivalent** | a bucket per environment, credentials in `.env`, the interface in §3, ~half a day. Storage cost negligible at 8.6 MB | both lanes resolve refs; the four outcomes become real; matches the stack decision *"Postgres plus an object store"* | nothing. The local backend stays for tests |
| **B · bytes in Postgres** (`bytea` or large objects) | one credential, no new service, no interface change beyond the read/write pair | simplest possible sharing | the stack decision explicitly separated these, and the corpus is meant to grow — flattened text for 887 threads plus raw payloads is not what a row store is for. Also puts eviction and retention inside the database's vacuum behaviour |
| **C · shared filesystem / rsync** | almost nothing today | works tomorrow | silent drift, which is exactly how 13 payloads went missing with no tombstone. A store two people believe is one store and is not is worse than two stores |
| **D · keep inlining exports** (status quo) | zero | works | the pipeline can never read from the store, so the resolver stays a stub, `MISSING`/`CORRUPT` stay untested, and every run needs a hand-built bundle. This is the state that made the reader wiring look like the blocker |

**Recommendation: A**, and the reason is not capability but detectability. B and C
both work as sharing; only A makes the store a thing with one address, which is
what turns *"the ref did not resolve"* from a local accident into a reportable
fact.

## 5 · What is genuinely joint, and needs deciding rather than scoping

1. **Bucket per environment, or prefix per environment in one bucket.** A shared
   bucket with a `staging/` prefix is one credential and one place to get an
   ACL wrong; separate buckets cost a second setup and cannot leak into each other.
2. **Read-only credentials for `judge/`.** It never writes bytes and should not be
   able to. This is the same guarantee `run-backend.py --staging` already gets from
   Postgres by forcing `default_transaction_read_only`, and it is worth having in
   the same shape rather than as a promise about which functions are called.
3. **Who owns eviction.** `FLATTENED` is `evictable=True` and nothing evicts today.
   In a shared store an eviction is visible to both lanes immediately, so the
   retention question that `judge/CLAUDE.md` raises about `delete_after` stops
   being hypothetical.
4. **Whether the 180 local files are the seed or are re-derivable.** Raw payloads
   are content-addressed and re-fetchable in principle; flattened text is
   regenerable from raw. If the raw half is intact, the move is a copy of the raw
   namespace and a re-flatten. **It is not intact — 13 are missing — so that
   question has an answer already and it is "copy what exists, and the 13 are
   gone".**
