# The class A re-review, four candidates — and what each reading needs first

**One re-review, not four — the clause fires on the first host and the other
three ride the same dated reading. Three of the four are ready to write. The
fourth should not be added at all, and the reason is a latent defect in the
shipped fetcher that adding it would activate (§3.4).**

*anooj · 2026-09-18 · PROPOSED, NOT TAKEN. `contract/` is the agreement and gets
two eyes.*

*What was fetched, because it is not nothing: robots.txt and the front page for
each of the four, their feeds, and ten articles each at one request per second
with the project User-Agent — the same sample the nine seated rows were assessed
on, and the fetch set the `template_block` examination needs. Plus the seven
seated class A feeds, which their own rulings permit. Evidence in
`_class_a_evidence/` and `_firecrawl_probe_substack/robots/`. No credits spent.*

---

## 1 · The clause fires once

`blog-class-a-self-hosted` says:

> "RE-REVIEW REQUIRED BEFORE: any external publication, any external user, any
> monetization, **or adding a feed outside the nine assessed.**"

That is one trigger with one remedy: a dated re-reading by a named person, with
`reviewed_on` and `review_valid_days` reset. **Adding four feeds fires it once,
not four times** — the ruling is re-read, and the four rows are then assessed
against the re-read ruling.

So the cost splits in two, and only the second half scales:

```
the re-review          one person, one sitting, once     shared by all four
the per-feed evidence  terms_evidence + measured +       four times over
                       template_block + base_trust
```

**And the re-review is not a formality this time.** `docs/proposals/blog-class-b-substack.md`
records that the first terms document anybody here read refused, unconditionally,
in a direction robots did not predict. Re-reading the class A ruling now means
re-reading it knowing that its central deferred assumption has one confirmed
counter-example. That is the right moment to do it and it is why these four
should not be added quietly under the existing text.

---

## 2 · What is established, per candidate

Robots only. Captured 2026-09-18 with the project User-Agent.

| | robots | article paths | terms page in sitemap |
|---|---|---|---|
| `sebastianraschka.com` | `User-agent: * / Allow: /` | permitted, explicitly | none found |
| `eugeneyan.com` | **`Sitemap:` line only — no `User-agent` block** | no rules stated | none found |
| `lilianweng.github.io` | `User-agent: * / Disallow:` (empty) | permitted, explicitly | none found |
| `jack-clark.net` | WordPress: `Disallow: /wp-admin/`, `Allow: /wp-admin/admin-ajax.php` | permitted | none found |

`eugeneyan.com` is the one to read carefully. A bare `Sitemap:` line with no
`User-agent` block is **not** a permission — it is a discovery hint with no crawl
policy attached. Under the ruling's `live_preconditions` that is
`robots_status: no-rules`, which the ruling accepts, and the 404 caveat's
reasoning applies to it unchanged: *"where robots is silent, the class A reading
is doing all of the work."* It should be recorded as `no-rules`, not as `rules`
with everything allowed, because those are different facts and only one of them
is true here.

---

## 3 · What each reading needs before it can be written

### 3.1 · The terms check, beyond the sitemap — done, and it was the weak one

The first check was each host's sitemap, which its own robots advertises, for a
terms, legal, licence or copyright page. **None of the four has one.** You were
right that this is the weak link, and the reasons are worth keeping written down
because they govern the second check too:

- **A sitemap is not a site.** A terms page can exist and be absent from the
  sitemap, or be linked only from a footer. Absence from one index is not
  absence from the host.
- **`jack-clark.net`'s sitemap is 518 bytes** — an index pointing at
  sub-sitemaps, which I did not follow. Its check is the weakest of the four by a
  wide margin.
- **Rule 6.** "No terms page found" and "no terms page exists" are different
  values, and only the first is measured. Writing the second is the exact move
  the class A ruling withdrew a clause for: *"NOT 'no terms page forbidding
  automated retrieval' — that clause was here and is withdrawn, because no terms
  page has been read for any seeded feed and the sentence asserted the check that
  was skipped."*

**Done, and it is now a two-source negative.** Each host's front page was loaded
and its markup searched for any link matching terms / legal / privacy /
copyright / licence / tos / disclaimer / imprint. **Zero matches on all four.**
What each carries instead is a bare copyright notice:

```
sebastianraschka.com    (c) 2013-2026 Sebastian Raschka
eugeneyan.com           (c) Eugene Yan 2015 - 2026
lilianweng.github.io    (c) 2026
jack-clark.net          WordPress i18n strings only, no notice in the markup
```

**A copyright notice is not a terms of service.** It asserts the default
position and says nothing about automated retrieval. It does bear on NFR-5's
*quote + attribution + link, never full text*, which is already the policy.

So: absent from the sitemap and absent from the front page, on all four. Still
`absent`, not `none` — but absent from both places a terms page is normally
reachable, which is as far as a check can honestly go without a lawyer.

### 3.2 · The feed confirmation, inside the re-review and not before it

The schema settles this, so it is not a judgement call. A seated feed row carries:

```yaml
terms_evidence:
  robots_status, robots_http, feed_path_allowed, robots_allows_article_path,
  article_http, paywall_observed, login_required, terms_document_read, feed_type
measured:
  entries, malformed, dated_entries, oldest, newest, span_days, days_since_newest,
  truncated, full_text_entries, median_body_chars, version_rate, byline_source,
  declared_author, entry_bylines_present, distinct_entry_bylines, resolves_to_voices
```

`feed_type` needs a feed fetch. `entries` through `resolves_to_voices` need a
feed fetch. `article_http`, `paywall_observed` and `login_required` need **one
sample article fetch**. So the evidence a class A row requires cannot be gathered
without fetching, and all nine seated rows carry `article_http: 200` from
2026-08-14 — a sample fetch was taken for each, before its ruling.

**That is the established practice and I am not proposing to change it.** What is
worth stating is why it does not contradict the position taken on Substack, since
the two look alike:

```
Substack    the TERMS forbid automated retrieval, so no sample is permissible
            and the precondition cannot be established at all. A closed loop.
these four  no terms document has been found, and robots permits the paths.
            A single sample fetch is the same act the nine were assessed on.
```

The distinction is the document, not the volume. **One sample is evidence
gathering; a nightly harvest is the thing the ruling authorises.** They are
separated in time by the re-review, and the order is: robots → terms → one
sample → row written → harvest.

### 3.3 · `template_block` — examined, and none of the four was expensive

Carried out rather than deferred, on the same fetch set as the sample. Ten
articles per host, one request per second, project User-Agent, robots re-read
first and every entry path checked against it. Lines appearing in >=80% of pages
are the block.

| host | pages | on-host entries | median body | template block |
|---|---:|---|---:|---|
| `lilianweng.github.io` | 10 | 53 of 53 | 37,207 | **clean** — 0 repeated lines |
| `jack-clark.net` | 10 | 10 of 10 | 16,731 | **block found** — 2 lines |
| `eugeneyan.com` | 10 | 212 of 212 | 15,679 | **block found** — 4 lines |
| `sebastianraschka.com` | 10 | **10 of 54** | 1,463 | clean — but see §3.4 |

The blocks found, verbatim, which is what a `headings` list would be built from:

```
jack-clark.net   10/10  "Welcome to Import AI, a newsletter about AI research..."
                 10/10  "Thanks for reading!"

eugeneyan.com     9/10  "Join 11,800+ readers getting updates on machine
                         learning, RecSys, LLMs, and engineering."
                  9/10  "If you found this useful, please cite this write-up as:"
                  9/10  "author  = {Yan, Ziyou},"
                  9/10  "journal = {eugeneyan.com},"
```

**None of the four was expensive**, and that is worth recording because the
figure in `four-scopes-before-building.md` §3.2 is Willison's 62 pages. Ten
pages resolved all four unambiguously: two are clean at ten and two have blocks
that are obvious at ten. **Willison was the outlier, not the norm** — which
also means the two seated `unverified` rows (`jxnl.co`,
`engineering.atspotify.com`) are probably ten pages of work each, not sixty.

So the proposal is four `verified` rows, and the live debt stays at two rather
than going to six.

**One correction, and it is rule 8 in miniature.** The probe first computed
`paywall_observed` as "shortest extracted body < 500 chars". It fired on
`eugeneyan.com`, and the page was an **HTML meta-refresh redirect stub** —
`"Redirecting... Click here if you are not redirected."` — not a paywall. An
unmeasured check produced a false positive on its first run against a population
it did not choose. The field now reports `short_bodies` by URL and leaves the
determination to a person; it does not emit a verdict.

### 3.4 · A feed's entry links can be on another host, and nothing checks that

**This is the finding that should hold up `sebastianraschka.com`, and it is a
latent defect in the shipped fetcher rather than a fact about one candidate.**

`BlogFetcher.harvest_feed` does `[self.fetch_article(entry) for entry in
feed.entries]`. Every hop is gated against **robots** — correctly, and the
docstring is explicit that a redirect may reach a different origin and *"the
first host's robots.txt says nothing about it."* Nothing anywhere checks that an
entry's host is the host whose **ruling** authorised the fetcher.

Robots is a crawl policy. The ruling is the permission. They are different
documents and `blog-class-b-substack` is the proof: Substack's robots permits
`/p/*` and Substack's terms forbid retrieving it.

**Measured, so the claim carries its population.** All seven seated class A
feeds were fetched and every entry link checked against the feed's host:

```
simonwillison.net   30 entries   all on-host
hamel.dev           20 entries   all on-host
jxnl.co             20 entries   all on-host
vickiboykis.com     20 entries   all on-host
slack.engineering    8 entries   all on-host
engineering.atspotify 5 entries  all on-host
engineering.grab.com 10 entries  all on-host
```

**The gap has never fired. Seven of seven are clean** — so this is latent, and
what would activate it is the first candidate in this proposal:

```
sebastianraschka.com   54 entries, 44 of them OFF-HOST
                       -> magazine.sebastianraschka.com  (Substack)
                       -> lightning.ai
```

Adding that feed under `blog-class-a-self-hosted` would fetch Substack article
pages under a class A ruling, consulting only Substack's robots, which permits
them. That is the ruling refused in `blog-class-b-substack` being circumvented
by a feed on a different host — not by anyone's intent, but by the absence of a
check nobody needed until now.

**And it happened.** Before the guard existed, this probe's first run against
`sebastianraschka.com` followed three of those links and fetched three Substack
article pages — `magazine.sebastianraschka.com/p/gpt-6-astra-...`,
`/p/claude-watermarking` and `/p/ai-detector-from-scratch`. The ruling refusing
Substack is one I drafted and it is unratified, so nothing was formally
breached; the position was mine and my own probe walked through it inside an
hour. The captures have been discarded and the probe now refuses off-host entry
links by default and names them.

Two consequences, and they are separable:

- **For this proposal:** `sebastianraschka.com` should not be added on this
  evidence. Ten of its 54 entries are on-host and they are 919-2,956 character
  stubs pointing at the real article elsewhere. Its median body is **1,463
  characters against lilianweng's 37,207**. As a class A feed it is a linkblog
  to a platform we are refusing.
- **For `collect/`:** the same-host check belongs in `BlogFetcher`, and by rule
  8 it ships as a recorded field first — an entry link off the feed's host is
  flagged and counted, not dropped — because its error rate against the seated
  nine is zero-of-seven and that is a population the check did not choose.

## 4 · BAIR is a different shape and should not ride this re-review

You asked whether Berkeley's site-wide terms are the governing document. **No
document was found, and separately, the robots question does not work the way it
would need to.**

**Robots does not cascade.** `robots.txt` is per-origin. `berkeley.edu` and
`www.berkeley.edu` both serve a permissive file — `User-agent: * / Disallow:`
with `Crawl-delay: 10` — and **`bair.berkeley.edu` serves HTTP 404**. The parent
domain's policy does not extend to the subdomain; the subdomain answered for
itself and its answer was that there is no crawl policy. So BAIR is the 404
caveat case, and Berkeley's permissive robots is not evidence about it.

This is precisely where Medium's class B evidence was different in kind: there,
two hosts *served the same file*, which is what demonstrated one party speaking.
Here the two hosts serve different things, and one of them serves nothing.

**No site-wide terms of use was found.** Seven conventional paths checked on
`www.berkeley.edu`: `/terms-of-use/`, `/terms/`, `/legal/`, `/copyright/`,
`/about/terms-of-use/`, `/policies/` all 404. Only `/privacy/` returns 200, and a
privacy policy governs personal data rather than automated retrieval — it is not
the document this question needs. Absent, not none: a university's terms may live
somewhere I did not look.

**And the class question is open, which is the real reason to separate it.**
Class A's premise is *"the publication and the domain are the same party."* At
BAIR they are arguably not: researchers write the posts, the university owns the
domain and the infrastructure. That is Medium's structure with an institution in
the platform's seat — *the writer cannot grant what the domain owner withholds*.

Two readings are available and neither is obviously right:

- **the lab is the publisher**, running its own subdomain, and this is class A
  with no robots and no terms — the thinnest class A row in the file;
- **the university is the party**, and this needs a ruling shaped like class B
  with a party that has published nothing to read.

**Recommendation: BAIR is deferred and recorded as deferred, not added to the
four.** It needs a decision about which party speaks before it needs evidence,
and that decision is not one this re-review is about. Academic posts also
routinely carry their own per-post licensing, which none of the other four do and
which no field in the schema records.

---

## 5 · The search conclusion, recorded

**The search step is not dead on terms. It is dead on yield, and this is the
measurement that closes it.**

```
two query shapes          `<model> <topic term>` and `<model> substack`
330 results               200 + 130
159 distinct hosts        100 + 79, overlapping by 20
66 credits                40 + 26
```

Against that, a hand-named list of eight publications, written from memory in one
message:

```
appeared in the probes    sebastianraschka.com  (2 results, probe 2 only)
                          interconnects.ai      (1 result, probe 2 only)
absent from both          Latent Space, Ahead of AI, Eugene Yan, Lil'Log,
                          BAIR, Import AI, and simonwillison.net itself
```

**`simonwillison.net` is 65% of the model-naming documents in the existing corpus
and did not appear once in 330 results.** That is the sentence that settles it.

The two mechanisms find disjoint populations, and the hand-named one is denser in
exactly what the board needs. Search returned vendor documentation, platform
roots, and a 44-publication one-post Substack tail — of which the Substack share
is now closed by `blog-class-b-substack`, and the vendor documentation was never
evidence about what engineers report.

**What this does not say.** The measurement is over two query shapes, one
rendering, one index, and `contract/queries.yaml` says plainly why a rendering is
not a finding: *"a rendered query string in a platform-neutral file is a string
that is true for no platform."* A different rendering might retrieve differently.
What is **not** rendering-dependent is the comparison: the same 66 credits that
missed six of eight named hosts bought 159 hosts of which the usable remainder is
a one-post tail, and every one of those would cost a class A reading.

So the conclusion is about ordering rather than about search being worthless:
**a curated list is the cheaper discovery mechanism at this scale, and the
re-review queue is the work either way.** Four named candidates cost one
re-review and four evidence blocks. The search tail costs the same per host and
produced hosts nobody can vouch for.

Recorded here rather than left in a message, because "we tried search" without
the numbers is exactly the claim somebody re-litigates in month four.
