# Blog harvest, eighteen feeds, 2026-09-21

*Staging write announced in #377; feeds seated in #376. The naming and byline
columns are recomputed from the database afterwards rather than taken from the
run's own report.*

## Done — 18 feeds, 0 refused, 919 new documents. Staging write complete.

```
feeds                18        articles             1034
refused               0        already_present       124
documents           910*       nothing_extracted       0
contexts            910*       members_unresolved      0
harvest_runs       18/18       unreadable_after_write  0
author_rows          34
```

\* plus 9 simonwillison documents from the aborted first pass — **919 new in total**, 180 → 1,099 blog documents.

### Per feed

```
host                        docs   was   new  names   one  byline  unread
swyx.io                      432     0   432     12    10       0       0
eugeneyan.com                212     0   212     21     8       0       0
maggieappleton.com           142     0   142     10     6       0       0
simonwillison.net             87    78     9     84    50      87       0
lilianweng.github.io          53     0    53      6     3       0       0
vickiboykis.com               22    22     0      3     2       0       1
thorstenball.com              20     0    20      0     0      20       0
jxnl.co                       20    20     0      1     1      20       0
www.fast.ai                   20     0    20      2     1       0       0
hamel.dev                     12    12     0      1     1       0       0
engineering.grab.com          11    11     0      1     0      11       0
netflixtechblog.com           11    10     1      1     1      11       0
medium.com                    11    11     0      0     0       0       0
mattrickard.com               10     0    10      0     0      10       0
jack-clark.net                10     0    10      8     0      10       0
minimaxir.com                 10     0    10      9     0       0       0
engineering.atspotify.com      8     8     0      3     1       8       0
slack.engineering              8     8     0      1     0       0       0
TOTAL                       1099   180   919    163    84     177       1
```

`names` / `one` are over **article text**, with `RegistrySurfaceFinder` and `RegistrySurfaceResolver` against 348 `model_version` rows. One vickiboykis text is unreadable on this machine (pre-existing raw-store gap, not this run).

### ⚠ The ten-entry samples overestimated naming by 3–5x, on every feed with an archive

This is the most important thing the harvest produced, and it was not the thing being looked for. The probe write-up flagged that ten-most-recent is a **recency sample** and not a rate. Now both numbers exist:

```
feed                     sampled       full feed        error
lilianweng.github.io      6/10  60%     6/53   11.3%    5.3x over
eugeneyan.com             4/10  40%    21/212   9.9%    4.0x over
swyx.io                   1/10  10%    12/432   2.8%    3.6x over
maggieappleton.com        2/10  20%    10/142   7.0%    2.8x over
---------------------------------------------------------------
minimaxir.com             9/10  90%     9/10   90.0%    exact
jack-clark.net            8/10  80%     8/10   80.0%    exact
mattrickard.com           0/10   0%     0/10    0.0%    exact
www.fast.ai               1/10  10%     2/20   10.0%    exact
```

**The split is not luck and it is not about the hosts.** The four that regressed are the four with archives deeper than ten. The four that held are the ones whose whole feed *is* about ten entries — the sample was the population, so there was nothing to regress to.

Consequences worth stating plainly:

- **`minimaxir.com` at 9/10 survives as the strongest feed seated, and is now stronger relative to the others than #376's ruling claims** — its 90% is a full-population figure while lilianweng's 60% was a sample that is really 11%. #376 §3 ranked on naming and picked the right winner for a reason it only half had.
- **`eugeneyan.com` and `lilianweng.github.io` are materially weaker than #372 measured.** Not wrong-then — their ten-entry figures were correctly labelled as ten-entry figures — but nobody had the denominator to compare against, and the proposal's headline table reads as a rate.
- **`swyx.io` is the thinnest of the nine by density**: 12 naming documents out of 432, 2.8%. It contributes the most text and the least evidence per document, and no voice.

This is rule 7 landing on our own measurement: a real value answering a question it was not asked. The fix is the same as always — the figure travels with its denominator, and "6 of the 10 most recent" was never "60% of the feed".

### Bylines: #373 reproduced exactly as predicted

**177 of 1,099 blog documents carry an `author_id`.**

- `thorstenball.com` **20/20** — `feed_declared` works today, confirming the correction in #376 that the probe write-up had this wrong.
- `mattrickard.com` **10/10** and `jack-clark.net` **10/10** — single distinct entry byline, the single-row branch.
- **`www.fast.ai` 0/20.** Seven author rows were written and **not one document links them**. Orphaned blog author rows went **19 → 26**. That is #373, reproducing precisely as #376's row predicted, which is why that row records `resolves_to_voices: 0` and not 7.
- `swyx.io` 0/432, `eugeneyan.com` 0/212, `maggieappleton.com` 0/142, `lilianweng.github.io` 0/53 — `byline_source: none`, no row written, honestly unknown.

**829 of the 919 new documents have no author_id** and therefore collapse to the single `anonymous:blog` voice at the gate.

### The same-host guard

Still not relevant. 1,042 entry links across 18 full feeds, 0 off-host — checked before the run, and no entry was dropped during it.

### One crash, fixed mid-run — #378

The first pass aborted seven feeds in: `lilianweng.github.io/faq/` is dated `Mon, 01 Jan 0001 00:00:00 +0000` (Hugo's zero date for an undated page), and `datetime.fromtimestamp` raises `OSError [Errno 22]` on Windows, which was not in `_timestamp_or_none`'s caught tuple. Fixed, tested, filed as #378 — including the part that matters more than the fix: **the exception type is platform-dependent, so CI on Linux may never see it.**

Nothing was corrupted. The harvest is append-only and the seven completed feeds re-reported as already-present.

### Not done

**No extraction.** `claim` and `cell` are untouched, $0.00 spent, no model call. That is behind the writeguard and needs a container, and #375 is the question it should answer first.
