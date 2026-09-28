# A host list cannot be classified without a per-host robots probe

**Two of the five hosts I classified by hand were wrong, in the direction that
costs most: both were platform-hosted and I called them self-hosted. A
custom-domain Substack is indistinguishable from a personal blog by its URL, and
the class A / class B split is the decision every terms ruling hangs on.**

*anooj · 2026-09-18 · measured on the 79 hosts returned by the `<model> substack`
search probe, `_firecrawl_probe_substack/`. Read-only, no credits, no publisher
article fetched.*

---

## 1 · What happened

The `<model name> substack` probe returned 130 results over 79 distinct hosts. I
classified all 79 by hand into six buckets and reported the split. Two entries
were wrong:

```
lennysnewsletter.com    reported: commercial / SEO content
interconnects.ai        reported: practitioner, self-hosted
actually                both serve Substack's robots.txt, byte-identical to
                        substack.com once the per-host SITEMAP line is removed
```

Neither URL contains the string `substack`. Nothing about either domain
announces the platform. I classified them from the domain name, which is the
only thing a search result gives you, and the domain name does not carry the
fact that decides the ruling.

The corrected share, and it is a floor rather than a figure:

```
reported    *.substack.com 73 + root 12 = 85 of 130   (65%)
corrected   + lennysnewsletter.com + interconnects.ai = 87 of 130   (67%)
true        ≥ 67%, unbounded above
```

**Unbounded above** because the remaining 23 non-Substack-looking hosts were
classified the same way the two wrong ones were. I have not probed them. Some
number of them are Substacks and I cannot say which without fetching each one's
robots.txt.

---

## 2 · Why this is not a Substack fact

Substack is where it surfaced. The mechanism is general and applies to every
platform that lets a publisher bring a domain:

| platform | custom domains | what the URL tells you |
|---|---|---|
| Substack | yes | nothing |
| Medium | yes — `netflixtechblog.com` is the precedent already in `contract/sources.yaml` | nothing |
| Ghost (Pro), Hashnode, Buttondown, Beehiiv | yes | nothing |

`contract/sources.yaml` already knows this and says so, in the sentence that
justifies having a class B at all:

> "Airbnb's engineers wrote the post; Medium wrote the terms, and Airbnb cannot
> grant what Medium withholds. Reading airbnb.com's terms to decide whether we
> may fetch medium.com/airbnb-engineering reads the wrong document."

That example is easy because the URL says `medium.com`. **`netflixtechblog.com`
is the hard case and it is already in the file** — the ruling covers it because a
person knew it was Medium-hosted, not because anything derived it. The rule was
correct and its applicability was established by hand, on a list of nine that one
person assembled.

That does not scale to a list somebody did not assemble, which is exactly what a
search step produces.

---

## 3 · The failure mode that matters, and it is not the obvious one

Misclassifying a platform host as self-hosted has two consequences and they are
not symmetric.

**The visible one: the wrong ruling gets applied.** A custom-domain Substack
treated as class A would be assessed against its own robots.txt — which is
Substack's, and which permits the article path — and admitted. The terms that
actually govern it would never be read, because nobody would know which document
to read.

**The expensive one: a ruling that governs is never applied.** Once
`blog-class-b-substack` exists and refuses Substack, a host nobody identified as
Substack is not covered by it. The refusal does not fire. There is no error, no
log line and no absence to notice — the host is simply harvested under a ruling
made about a different party, and everything downstream looks correct.

That is rule 6's shape at the classification layer: a value that cannot be told
apart from a considered one, feeding a decision that gates behaviour. And it is
rule 4's at the review layer — nobody audits a host that was never flagged.

---

## 4 · What actually determines the class, and its cost

One HTTP GET of `https://<host>/robots.txt`, compared against a known platform
fingerprint.

It is cheap and it is already built. `collect/adapters/blog/robots.py` reads
robots.txt on every run, caches it an hour per host, and is the mechanism the
class A ruling's `live_preconditions` are observed with. Reading robots.txt is
how this project establishes evidence *before* a ruling exists; it is not gated
on one.

So the probe costs nothing new except the comparison step, which does not exist:

```
have      fetch robots.txt, parse it, answer "is this path allowed"
missing   compare the rule set against known platform fingerprints and
          answer "who is the party speaking here"
```

A fingerprint is the rule set with per-host lines (`SITEMAP:`) stripped. On the
five Substack hosts that comparison is exact — byte-identical — which is the same
test `contract/sources.yaml` used for Medium, just run as code instead of by a
person.

**What it cannot do** is identify a platform nobody has fingerprinted yet. A
fingerprint list is a curated artifact that goes stale the way every other one
here does, and an unmatched rule set means *unknown*, not *self-hosted*. That
distinction is the whole value: the honest output is three-valued — `class B
(matched <platform>)`, `class A candidate`, `unknown` — and `unknown` must not
collapse into `class A candidate`, which is precisely the collapse I performed by
hand.

---

## 5 · What this governs

Any search-driven expansion, and the ordering of it.

The earlier report said a search result's host determines its review cost: a
novel self-hosted host is one class A re-review, a platform host is covered by
one class B ruling. That is still true. What this finding adds is that **you
cannot tell which from the result**, so the split has to be computed before any
cost estimate built on it means anything.

Concretely, for the two probes already run:

- probe 1 (topic terms): 100 hosts, classified by hand, **unprobed**. Its
  "~59 novel hosts, each a class A re-review" figure is an upper bound on class A
  and a lower bound on class B, not a measurement.
- probe 2 (`substack`): 79 hosts, two corrections found by probing five. The
  other 23 non-Substack-looking hosts are unprobed.

Neither number should be quoted as a review-queue size until the hosts are
probed. Rule 7: the population was gathered by a classifier whose error rate on
its one tested sample was **2 of 5**.

---

## 6 · What I am not proposing

A fingerprint matcher is a filter over the candidate list, and rule 8 applies to
it: its error rate has not been measured against a population it did not choose.
So if it is built it ships as a **flag on the row**, not as a gate that drops
hosts — and the three-valued output above is what makes that possible. A host
marked `unknown` is a host a person looks at, not a host that disappears.

The cheap thing available today needs no new code at all: before any candidate
host list is costed, run `robots.py` over it and diff the rule sets. Identical
rule sets across unrelated domains is the signal, and it does not need a
fingerprint library to be visible — it needs somebody to look at the diff.
