# Proposal: bring Substack feeds back, seed 20, harvest them from a developer machine

**For review by Parvathi. Proposed 2026-11-04 (anooj).** A `contract/`
change, so nothing is edited until it's agreed.

## The ask

1. **Restore the three removed feeds** (`blog:epochai.substack.com`,
   `blog:cameronrwolfe.substack.com`, `blog:chinai.substack.com`) and **add 17
   more**, all under the existing ruling `newsletter-substack-feed-only`
   (seated 2026-10-26). Feed only, as that ruling says: no article pages.
2. **Find out why Substack's robots.txt refuses the scheduled runner** but
   answers developer machines normally. That refusal is why the three were
   removed on 2026-10-30: the scheduled harvest exited 1 every night from
   10-28. Harvesting from a developer machine instead would route around the
   refusal, and is a separate team question (see "Where it runs").
3. **Extract the 37 Substack posts already stored and never extracted,** on
   the machine that holds their text.

## Why

- **Substack gives the board nothing today.** 60 documents in the shared
  database are Substack posts (3 publications, harvested by hand 2026-10-27).
  37 passed triage, and **0 have been extracted**. `thread_extraction` has no
  row for any of the 37, though the nightly extraction ran as late as
  2026-11-04 05:46 UTC.
- **Their text isn't on the machines that run things.** All 37 flattened texts
  are missing from this machine's five raw stores. The 27 Oct harvest has no
  `job_run` record, so it was manual, and the blobs are on the machine that ran
  it. Whoever ran it can export and extract them in one step, below.
- **The candidates are good.** Feed reads on 2026-11-04 (one robots.txt and
  one `/feed` per host, identifying User-Agent, nothing stored):

| Population | Count |
|---|---|
| Candidate publications: the 3 removed, plus every `*.substack.com` host linked from our thread texts | 27 |
| Feeds that answered with items | **26** (1 returned 404) |
| Posts in those feeds (each holds its latest 20 at most) | 451 |
| Of those, mention an AI model or LLM (title plus the first 4,000 characters, by pattern) | **287** |
| Carry the full post text (over 1,500 characters) | 425 |
| Publications that posted since 21 Oct | 19 |

The pattern counts mentions, not first-hand reports. Extraction decides
which posts actually carry reports.

## The 20 proposed

The rule: at least 8 of the latest posts mention a model, and something was
posted since 1 Sep. Hosts are as the feed now answers. Three of the 27
have moved to their own domains, and two of those are in this list
(`www.thealgorithmicbridge.com`, `newsletter.maartengrootendorst.com`; the
third, fabricatedknowledge, is left out). They are still served by Substack,
which is what the ruling covers ("from substack.com or from a publisher's
custom domain").

epochai.substack.com · cameronrwolfe.substack.com · chinai.substack.com ·
garymarcus.substack.com · www.thealgorithmicbridge.com ·
plainaiphone.substack.com · newsletter.maartengrootendorst.com ·
ileanamarcut.substack.com · harryfloyd.substack.com · benn.substack.com ·
allagentsconsidered.substack.com · vizuara.substack.com ·
vibecodingweekly.substack.com · theaiengineer.substack.com ·
swyx.substack.com · r3dtuxedo.substack.com · msukhareva.substack.com ·
econlab.substack.com · chinaaidispatch.substack.com ·
aspiringforintelligence.substack.com

Left out: heavylifting (1 of 20 about models), shimo4228 (3 of 7), mule /
fabricatedknowledge (3 of 20, last post 13 Aug), practicalainotes (1 of 10),
m1kulya (3 of 5), demishassabis (1 post), builtbywords (404).

Each entry still needs its own `terms_evidence` block, checked from where the
harvest will run, as the other blog rows have.

## Where it runs, and the open question

The scheduled runner is refused by robots.txt; a developer machine is not.
Two ways to handle it:

- **(a) A developer machine harvests Substack on a schedule** and writes to
  the shared database like any harvest. The raw blobs then live on that
  machine, so extraction must run there too, which is exactly today's problem
  with the 37, and that machine's scheduled writes to the shared database
  would need coordinating.
- **(b) Find out why the runner is refused** (most likely its data-centre IP
  range) before seating anything. Slower, but keeps one place for harvests.

**(b) first.** `newsletter-substack-feed-only` accepts the terms risk for a
feed read that passes `live_preconditions`, with robots.txt re-read every
run. Harvesting from a developer machine *because* the runner is refused goes
around that refusal; the ruling doesn't cover it, and it widens the risk the
ruling records (the Acceptable Use Policy's crawl clause). If (b) finds that
data-centre addresses are blocked, (a) goes to the team as its own question,
stated as routing around a refusal. (Revised on review, 2026-11-04; the first
draft suggested (a) for a trial.)

## Cost

Substack posts are long. A Cameron Wolfe post in the feed runs to about
75,000 characters, against our measured $0.00208 per thread for ordinary
threads. **Extract 10 posts first and record their tokens** before turning the
feeds on. The daily budget cap stops anything runaway anyway.

## To extract the 37 already stored (whoever holds the blobs)

```
# 1. export every unextracted blog thread
python scripts/export_contexts_for_extract.py --out <dir> --source blog --skip-extracted

# 2. list the 37: kept documents at a substack.com address
psql "$DATABASE_URL" -At -c "SELECT tc.id FROM thread_context tc
  JOIN document d ON d.id = tc.thread_root_id
  WHERE d.url ILIKE '%substack.com%' AND d.triage_verdict = 'kept'" > substack_threads.txt

# 3. keep only those files, so nothing else is extracted
mkdir -p <dir>/substack/threads
while read t; do cp "<dir>/threads/$t.json" <dir>/substack/threads/; done < substack_threads.txt
ls <dir>/substack/threads | wc -l      # expect 37; fewer means some text is not on this machine

# 4. extract exactly those
python scripts/run_extraction.py --from-export <dir>/substack/threads
```

This needs `ENVIRONMENT=staging` and `DATABASE_URL` set for the run. Without
`--driver`, the nightly close is skipped.
