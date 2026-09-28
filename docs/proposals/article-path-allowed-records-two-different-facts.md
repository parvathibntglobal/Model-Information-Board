# `article_path_allowed` records two different facts, and a machine cannot tell which

**Raised 2026-09-17 by anooj + Claude. Separate from the raw-store proposal on
purpose — it is a contract-evidence question, not a storage one, and it is the
custom-domain shape Substack has.**

---

## The disagreement, in the contract as it stands

`blog:netflixtechblog.com` records:

```yaml
article_path_allowed: false
article_http: 403
article_fetch_refused: true
paywall_observed: unknown
```

The class B ruling's prose says the opposite about robots, in capitals, as a
correction it made to itself:

> `Disallow: /*/*source=` requires two slashes before `source=`. A publication
> on medium.com is `/<publication>/<slug>`, which has two, so Airbnb's article
> links are disallowed — 5 of 6 sampled URLs. A custom domain is `/<slug>`,
> which has one, so **netflixtechblog.com's article links are NOT disallowed by
> robots** even though the host serves the identical 37 rule lines. On that host
> the 403 is the only thing stopping us.

So on that host, `article_path_allowed: false` does not mean *robots disallows
the article path*. It means *we were refused*, by a Cloudflare 403.

**Neither the ruling nor the field is wrong.** The field records the refusal
conservatively, which is right, and the test that pins it says so in its name:

```
tests/test_source_terms.py
  test_the_medium_feeds_record_the_refusal_rather_than_a_clean_bill
```

## Why it is still a defect

**The field's name states a robots verdict and its value sometimes states an
HTTP outcome, and only the prose distinguishes them.**

Every mechanical reader sees one boolean:

- `assert_terms_reviewed` → `_check_facts` compares `article_path_allowed`
  against the ruling's accepted values. It cannot see that `false` means two
  different things on two hosts sharing one ruling.
- Anything that later asks *"may we fetch articles here?"* by reading this
  column gets **"robots says no"** for a host whose robots says nothing of the
  kind.

That is rule 6's shape one level in. The value is not missing and it is not
wrong; it is a **real value answering a question it was not asked** — rule 7's
form, which the CLAUDE.md entry says is the one that survives inspection,
because a spot-check confirms the figure and never asks what it counted.

And the distinction is load-bearing rather than pedantic. The class B ruling
itself turns on it: *"robots … is sufficient to refuse and would not be
sufficient to permit."* A future reading that treats this `false` as a robots
verdict would be using an insufficient-to-permit signal as though it were one —
in the direction the ruling explicitly forbids.

## Why it matters for Substack specifically, without ruling on Substack

Substack is the same shape as netflixtechblog.com: **platform-hosted, commonly
on a custom domain.** `*.substack.com` and a publication's own domain serve
different URL shapes under one platform's rules, which is exactly the case the
class B ruling wrote its per-domain paragraph for:

> THE REVIEW IS PER DOMAIN, NOT PER PUBLISHER, AND BYTE-IDENTICAL ROBOTS DOES
> NOT COLLAPSE TWO DOMAINS INTO ONE REVIEW.

So a sixth ruling will record this field for hosts where robots and the HTTP
outcome **disagree**, and today there is nowhere to put that disagreement except
prose. Raising it now rather than during the ruling, because a ruling written
against an ambiguous field will inherit the ambiguity and then be the precedent
for it.

## Options, with a recommendation

| | what it does | cost |
|---|---|---|
| **A · split the field** (recommended) | `robots_allows_article_path` and `article_fetch_refused` as separate facts; drop `article_path_allowed` | touches 9 feed rows and 2 rulings; `_check_facts` needs both keys present, so it is a paired change like `terms_document_read` |
| B · keep one field, widen the vocabulary | `allowed` / `disallowed_by_robots` / `refused_by_server` / `unknown` | no new key, but every reader that treats it as a boolean has to be found |
| C · leave it, document it | a comment on the two feed rows | free, and it is what we have now — the distinction survives only where somebody reads prose |

**A is recommended**, and note the repo already holds half of it:
`article_fetch_refused: true` exists on both class B feeds and records the HTTP
fact cleanly. What is missing is the robots fact having its own name, so today
`article_path_allowed` is carrying both and the ruling's own correction is
invisible to anything that does not read English.

**C is not nothing and may be the right call this week** — the two affected rows
are both under a `fetch_articles: false` ruling, so nothing currently acts on
the field in a way the ambiguity changes. The cost lands when a host arrives
where robots permits and we want to fetch, which is the Substack case.

## What is asked

1. A ruling on A / B / C.
2. If A: it is a `contract/` change and needs two eyes, and it is paired —
   adding a key to `recorded_evidence` refuses every source that does not record
   it, the way `terms_document_read` did.

**Not asked, and deliberately not proposed:** any change to the class B ruling's
position, to `fetch_articles`, or to what we fetch from either Medium host.
Nothing here says we may fetch netflixtechblog.com's articles. The 403 stands on
its own and *"a refusal we happen to receive is not a rule we chose to obey"*
remains the ruling's own answer to that.
