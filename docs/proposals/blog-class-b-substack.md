# The deferred terms reading was tested once and refused

**Nine feeds carry `terms_document_read: [false]` and a written deferral. The
first terms document anybody here has actually read said no — unconditionally,
in a direction robots did not predict, and in a form the
internal-development-only basis does not hold open. The Substack ruling this
came out of is §4 and is the smaller half.**

*anooj · 2026-09-18 · PROPOSED, NOT TAKEN. `contract/` is the agreement and gets
two eyes. Evidence in `_firecrawl_probe_substack/robots/`; no credits spent, no
publisher article fetched.*

---

## 1 · What the deferral assumed, and what the first reading did to it

`blog-class-a-self-hosted` is candid about its own gap, which is why this is a
finding rather than an accusation:

> "NO TERMS PAGE HAS BEEN READ FOR ANY OF THE NINE FEEDS. … TERMS REVIEW IS
> DEFERRED — a team decision, taken while the project is internal — and the
> deferral is written here rather than left as an absence somebody later reads
> as a clearance."

and

> "A source whose terms forbid this use is dropped, not worked around — **and
> since no terms page has been read, that condition has not been tested.**"

It has now been tested once. Two things about how it failed matter more than
that it failed.

**Robots and terms diverged, in the permissive-to-restrictive direction.**
Substack's `robots.txt` allows the article path and the feed. Its Acceptable Use
Policy prohibits crawling any page or portion of the platform and separately
prohibits storing any significant portion of its content. The mechanical
evidence said yes and the document said no. The deferral rests on robots
carrying the weight in the meantime — *"where robots is silent, the class A
reading is doing all of the work"* — and this is a case where robots was not
silent, was affirmative, and was wrong about the outcome.

**The prohibition is unconditional, so the basis does not reach it.** Every other
ruling in `contract/sources.yaml` uses `internal-development-only` to hold open a
named condition: Reddit's Data API Terms 2.8, arXiv's `Disallow: /` on the API
host. Those conditions are about publication, monetization and audience, and the
basis genuinely speaks to them. Substack's AUP clause is not contingent on any of
those. There is nothing for the basis to hold open.

**So the deferral's real exposure is narrower and sharper than "the terms are
unread."** It is: *an unconditional prohibition in a document nobody has opened
would not be covered by the basis, and would not be visible in robots.* That
shape now has one confirmed instance.

### What this does NOT say, stated because the denominator is one

This is **1 of 1 terms documents read**, and it was read on a **platform**, not on
any of the nine. A platform with a lawyer-drafted AUP is exactly the kind of
document that carries a crawl clause. `simonwillison.net` and `hamel.dev` may
have no terms page at all, in which case there is nothing to read and the 404
caveat's reasoning applies unchanged.

That asymmetry is the useful part, because it says where to look:

| the nine | likely to carry a drafted terms document |
|---|---|
| simonwillison.net, vickiboykis.com, jxnl.co, hamel.dev | unlikely — practitioner blogs |
| engineering.grab.com, slack.engineering, engineering.atspotify.com | **likely — corporate legal pages** |
| medium.com, netflixtechblog.com | class B, already refused on robots |

**And the three most likely to refuse are the three that contribute almost no
evidence.** `docs/engineer-1/four-scopes-before-building.md` §3.4 measured it:
Grab, Slack and Spotify contribute **1 model-naming document each and 0 that
resolve to a single model**.

So the cheapest way to close the deferral is to read those three first. If any
refuses, it is dropped at close to zero evidentiary cost, and the deferral stops
being untested on the half of the list where an unconditional clause is
plausible. That is a person-afternoon, not a project.

---

## 2 · The instance: Substack is one party speaking, on five hosts

Medium is the governing party because two hosts served byte-identical robots.
The same test, five hosts, per-host `SITEMAP` lines excluded:

```
substack.com                    the platform root
thezvi.substack.com             IDENTICAL rule set
natesnewsletter.substack.com    IDENTICAL rule set
lennysnewsletter.com            IDENTICAL rule set   ← custom domain
interconnects.ai                IDENTICAL rule set   ← custom domain
```

All five HTTP 200, fetched 2026-09-18 with the project User-Agent. The two custom
domains are the case that would otherwise break a ruling written on
`*.substack.com` alone.

Under `User-agent: *`, Substack disallows `/action/`, `/publish`, `/sign-in`,
three frames, `/subscribe`, `/lovestack/*`, `/inbox/post/*`, `/notes/post/*`,
`/embed`, `/feed/private` and private podcast RSS. It does **not** disallow
`/p/*` — only `/p/*/comment/*` — and does **not** disallow `/feed`.

**Robots permits what the terms forbid, which is why §1 is the larger finding.**

> The custom-domain result also produced a method finding that is not a Substack
> fact and is written up separately in
> `docs/host-classification-needs-a-probe.md`: a candidate host list cannot be
> split into class A and class B without a per-host robots probe, and two of the
> five hosts I classified by hand were wrong.

---

## 3 · The terms, read

`https://substack.com/tos`, Acceptable Use Policy. Lead-in:

> "You also agree that you will not contribute any Post or otherwise use
> Substack in a manner that:"

Two items on that list:

> "**'Crawls,' 'scrapes,' or 'spiders' any page, data, or portion of Substack**
> (through use of manual or automated means);"

> "**Copies or stores any significant portion of the content on Substack;**"

"Substack" in that document is not the website — it covers Substack's products
and services, publications included, which is the same scope the robots evidence
establishes.

On ownership the terms are generous and it does not help: *"you own what you
create"*, and readers get rights *"to access the Post, and to use and exercise all
rights in it, **as permitted by the functionality of Substack**."* Rights are
scoped to platform features — a browser — not an HTTP client with a raw store
behind it.

**There is no RSS or syndication clause.** Feeds are not carved out of the
prohibition; they are not mentioned.

### Why it is a refusal, and why feed-only is not available

**The crawl clause bites on retrieval.** `BlogFetcher` fetches article URLs with
an HTTP client on a timer. That is what the clause names, in the words it names
it in.

**The copy-or-store clause bites on retention, separately.** NFR-4 requires full
article text in an immutable content-hash-addressed store. This clause survives
even if the first is argued away, and it cannot be engineered around: re-fetching
instead of storing performs the first prohibited act more often.

Medium's refusal is narrow — robots disallows the article path, so feed-only
harvest proceeds. Substack's is broad: *any page, data, or portion*. So the
Medium remedy is unavailable, and the bind closes neatly: the class B shape
requires `feed_carries_full_text: [true]`, and establishing that needs a feed
fetch, which is the act in question. **You cannot satisfy the precondition
without doing the thing the terms forbid.**

---

## 4 · The draft ruling

For `contract/sources.yaml`, `terms_rulings:`. Not to be pasted in without the
second reading.

```yaml
  # ── Class B: Substack ────────────────────────────────────────────────────
  - id: blog-class-b-substack
    class: B
    party: platform
    platform_host: substack.com
    reviewed_on: 2026-09-18
    reviewed_by: UNRATIFIED-DRAFT
    basis: internal-development-only
    review_valid_days: 90
    evidence_valid_days: 90

    #: REFUSED ON TERMS, NOT ON ROBOTS. This is the distinction that makes the
    #: ruling worth reading: robots ALLOWS the article path and the feed, and
    #: is not the governing document.
    fetch_articles: false
    fetch_feed: false

    summary: >-
      Substack-hosted publication, whether served from <name>.substack.com or
      from the publisher's own domain. Substack's terms govern and the
      publisher's do not - the writer cannot grant what Substack withholds.

      THE RULING, IN ONE SENTENCE: Substack is refused entirely, feed included,
      because its Acceptable Use Policy prohibits automated retrieval of any
      portion of the platform and separately prohibits storing any significant
      portion of its content.

      WHAT WAS ACTUALLY CHECKED, AND THIS TIME IT IS THE TERMS. Read
      2026-09-18 at https://substack.com/tos, Acceptable Use Policy, under
      "You also agree that you will not contribute any Post or otherwise use
      Substack in a manner that:" -

        "'Crawls,' 'scrapes,' or 'spiders' any page, data, or portion of
         Substack (through use of manual or automated means);"

        "Copies or stores any significant portion of the content on Substack;"

      The first reaches our article fetch. The second reaches our raw store
      independently of the first, and is the one that cannot be engineered
      around: re-fetching instead of storing performs the first prohibited act
      more often.

      ROBOTS SAYS THE OPPOSITE AND IS RECORDED HERE SO NOBODY RE-DERIVES IT.
      substack.com/robots.txt under `User-agent: *` disallows /action/,
      /publish, /sign-in, three frames, /subscribe, /lovestack/*,
      /inbox/post/*, /notes/post/*, /embed, /feed/private and private podcast
      RSS. It does NOT disallow /p/* - only /p/*/comment/* - and does NOT
      disallow /feed. So the article path and the feed are mechanically
      permitted and contractually forbidden, and the contract governs. A future
      reader who checks only robots will conclude this ruling is wrong; it is
      not, and this paragraph is why.

      SUBSTACK IS THE SPEAKING PARTY ON CUSTOM DOMAINS TOO, which is the half
      that makes this a class ruling rather than a per-host one. Five hosts
      fetched separately 2026-09-18 - substack.com, thezvi.substack.com,
      natesnewsletter.substack.com, lennysnewsletter.com and interconnects.ai -
      all HTTP 200 with byte-identical rule sets once the per-host SITEMAP
      lines are excluded. The last two are custom domains and are the case that
      would otherwise break this ruling.

      CURRENT USE: internal development and testing. Not published, no external
      users, not monetized. THE BASIS DOES NOT RESCUE THIS ONE. Every other
      ruling here proceeds on that basis while recording an unresolved
      condition; this prohibition is not conditional on publication,
      monetization or audience, so there is nothing for the basis to hold open.

      UNRESOLVED, DELIBERATELY RECORDED:
        - EVIDENCE COUNT IS THIN. Five hosts, of which two are custom domains.
          That is more than the two Medium's ruling rests on and it is still
          five out of a platform with an unknown number of publications. A
          publication serving a different robots.txt would not change the
          terms finding, which is platform-wide, but it would weaken the
          "one party speaks" claim this class depends on.
        - WHETHER A SUBSTACK FEED CARRIES FULL TEXT IS UNKNOWN AND
          UNKNOWABLE FROM HERE. The class B shape requires
          `feed_carries_full_text: [true]` and establishing it needs a feed
          fetch, which is the act refused above. Recorded as a circularity
          rather than left as an absent field.
        - NO YIELD FIGURE EXISTS FOR THIS POPULATION. 53 publications and 73
          results were retrieved by a search whose query contained the model
          name, so a naming rate over them measures the index and not the
          corpus. `nine-feeds-and-one-writer.md`'s 23 of 119 is over FULL
          ARTICLE TEXT and is not comparable. Settling it needs article text,
          which needs the fetch, which this ruling refuses.
        - A CUSTOM-DOMAIN SUBSTACK IS NOT IDENTIFIABLE FROM ITS URL. See
          docs/host-classification-needs-a-probe.md. Any list of candidate
          hosts must be probed before it is classified, or this ruling will be
          applied to the wrong set and, worse, NOT applied to hosts it governs.

      RE-REVIEW REQUIRED BEFORE: treating any host as class A on the strength
      of its domain name alone; any change to Substack's Acceptable Use Policy;
      and in any case on the expiry below.

    live_preconditions:
      use_basis: [internal-development-only]
    recorded_evidence:
      checked_on: 2026-09-18
      robots_status: [rules]
      robots_allows_article_path: [true]     # and it does not matter
      robots_allows_feed_path: [true]        # and it does not matter
      terms_document_read: [true]            # ← the first one in this file
      terms_permits_automated_retrieval: [false]
      terms_permits_storage: [false]
      paywall_observed: [unknown]
      login_required: [unknown]
```

Two fields are not in the current schema and are this proposal's real contract
change: **`fetch_feed`**, because every existing ruling assumes the feed is
available and only the article path is in question; and
**`terms_permits_automated_retrieval` / `terms_permits_storage`**, because
`terms_document_read: [true]` with nowhere to record *what it said* would be the
first true value in that column meaning nothing.

---

## 5 · What it would permit if ratified

**Nothing.** Zero documents, zero hosts, zero ongoing cost. The reading that made
this look like a new retrieval population — the feed and the article paths it
links, across every Substack publication — is what robots supported and what the
terms dispose of.

What it buys:

- **53 publications and counting stop being re-litigated**, with the reasoning
  attached rather than rediscovered by whoever reads robots next.
- **It is the first read terms document in the file**, and §1 is what that is
  worth.
- **It closes the largest single bucket of the search proposal** — ≥67% of the
  `substack`-shaped probe — which the search question needs as a denominator.

---

## 6 · The one live question

Whether reading a *feed* is *"permitted by the functionality of Substack"*, the
phrase the terms use for what readers may do. The terms do not mention feeds at
all — verified, and the only part of this paragraph that is. Whether a Substack
feed carries full text I have not checked, because checking is a feed fetch.

I do not think the argument survives the copy-or-store clause, which is not
scoped to how the content was obtained. But it is a reading a lawyer could make
and I am not one, and it is the question to take to whoever ruled on Reddit.
