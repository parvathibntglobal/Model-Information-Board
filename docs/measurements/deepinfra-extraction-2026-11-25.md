# DeepInfra's extractor reads, and the 1,474 rows deleted (2026-11-25, #671)

The record #671's review asked for: why 1,474 threads were read twice, kept
where the team can find it. The rows themselves are in
`deepinfra-extraction-2026-11-25.jsonl`, one per line, as they were before the
delete, each with what `fetch_log` says about that read.

## What happened

OpenRouter serves `deepseek/deepseek-v4-flash` through several hosts. The
nightly workflows sent no host preference until #671, so OpenRouter chose.

**From 14 Nov, DeepInfra answered "no claim" to nearly every thread**
(`fetch_log` `kind = 'thread'`, `upstreams` and `verified`, every thread read
since 29 Sep):

| Period | Host | Threads | Verified quotes |
|---|---|---|---|
| 13 Nov | DeepInfra alone | 368 | 631 |
| 14–24 Nov | DeepInfra alone | 1,518 | 125 |
| 14–24 Nov | other hosts | 2,351 | 5,453 |

**A replay held the threads fixed.** On 2026-11-25 the same 14 threads went
once pinned to DeepInfra and once to Wafer. DeepInfra gave 0 quotes on all 14,
Wafer gave 9 on 4. It cost about $0.009 and wrote nothing.

## The rows deleted

On 2026-11-25 at about 10:30Z, `thread_extraction` rows at `e5.5` were deleted
in one transaction, with a count check and a recount after. Without the delete,
the skip (`ExtractionLedger.already_extracted`) would never have read these
threads again. Those were:
- threads read by DeepInfra alone on 14 Nov or later;
- whose last read was that one;
- read before 10:00Z on 25 Nov.

**In the file (each line):**
- the row as it was: `thread_context_id`, `pipeline_version`, `extracted_at`,
  tokens, retries and `content_fingerprint`;
- `fetch_log`: that read's time, model, `upstreams`, and its `verified` and
  `rejected` counts.

**Counts in it, 2026-11-25:**
- 1,474 rows, each with a `fetch_log` read;
- hosts: DeepInfra 1,434, and DeepInfra with a retry, also DeepInfra, 40;
- 125 verified quotes across all 1,474 reads.

**To put a row back:** insert its fields into `thread_extraction`, then that
thread is skipped again at `e5.5`.

## After the fix

**The first run** was the model fetch started by hand at 11:09Z on 25 Nov:
- 467 threads read, 0 of them on DeepInfra;
- by host: Wafer 374 threads and 1,645 quotes, Azure 80 and 140, Fireworks 11
  and 49.

**The re-reads** are spread over later fetches: each thread is read again when
a model it names is next fetched, inside that model's window.
- **By 26 Nov 09:30Z:** 62 of the 1,474 had been read again.
- **Their 223 documents:** 7 board entries before the fix, 265 since.

**Can a re-read write a second entry for the same quote?**
- **Not for the same quote under the same slug.** A board entry's id is a hash
  of (document, section, slug, quote, `pipeline_version`), written `ON
  CONFLICT DO NOTHING`.
- **It can for a quote filed under another slug,** or copied with different
  boundaries. In those 62 threads, 3 new entries repeat an earlier entry's
  statement under another slug (same model and section, one quote inside the
  other). None repeat it under the same slug.
