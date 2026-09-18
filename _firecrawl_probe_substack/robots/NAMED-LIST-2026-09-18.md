# The named list, probed. robots.txt and sitemaps only.

Fetched 2026-09-18 with `modelboard/0.1 (+https://github.com/parvathibntglobal/Model-Information-Board)`.
No article fetched, no feed fetched, no credits spent. Captures are the `.txt`
files beside this one; the Substack fingerprint is `substack.com.txt` with the
per-host `SITEMAP` lines excluded.

| host | HTTP | verdict |
|---|---|---|
| www.latent.space | 200 | **Substack**, byte-identical rule set |
| magazine.sebastianraschka.com | 200 | **Substack**, byte-identical rule set |
| importai.substack.com | 200 | **Substack**, byte-identical rule set |
| interconnects.ai | 200 | **Substack**, byte-identical (captured earlier) |
| sebastianraschka.com | 200 | self-hosted — `Allow: /` |
| eugeneyan.com | 200 | self-hosted — Sitemap line only, NO `User-agent` block |
| lilianweng.github.io | 200 | self-hosted — `Disallow:` (empty) |
| jack-clark.net | 200 | self-hosted — WordPress, `Disallow: /wp-admin/` |
| simonwillison.net | 200 | self-hosted, ALREADY SEATED — `Disallow: /admin/`, `/search/` |
| bair.berkeley.edu | **404** | no crawl policy served; the 404 caveat applies |

TERMS: no terms, legal or licence page appears in the sitemap of any of the five
self-hosted hosts. That is a negative from ONE source and is not proof of
absence - a terms page can exist and not be in a sitemap, or be linked only from
a footer. `jack-clark.net`'s sitemap is 518 bytes (an index pointing elsewhere),
so its check is the weakest of the five.

TWO AUTHORS APPEAR TWICE, on different hosts under different rulings:
  Sebastian Raschka  sebastianraschka.com (self-hosted) and
                     magazine.sebastianraschka.com (Substack, "Ahead of AI")
  Simon Willison     simonwillison.net (seated, class A) and
                     simonw.substack.com (Substack)
A ruling is made about a host, not an author, so these are four decisions.

OVERLAP WITH THE SEARCH PROBES - 2 of the 12 host forms, out of 330 results:
  sebastianraschka.com   0 in probe 1, 2 in probe 2
  interconnects.ai       0 in probe 1, 1 in probe 2
  simonw.substack.com    1 in probe 1, 1 in probe 2
Latent Space, Ahead of AI, Eugene Yan, Lil'Log, BAIR, Import AI and
simonwillison.net itself appeared in NEITHER probe.

## BAIR, followed up

`bair.berkeley.edu/robots.txt` is HTTP 404. `berkeley.edu/robots.txt` and
`www.berkeley.edu/robots.txt` both return 200 with `User-agent: * / Disallow:`
(permits all) and `Crawl-delay: 10`, captured as `berkeley.edu.txt`.

**robots.txt is per-origin and does not cascade**, so the parent's permissive
file is NOT evidence about the subdomain. The subdomain answered for itself and
answered "no crawl policy". This is where Medium's class B evidence differs in
kind: there, two hosts served the SAME FILE, which is what demonstrated one
party speaking. Here they serve different things and one serves nothing.

No site-wide terms of use found. Checked on www.berkeley.edu:
  /terms-of-use/  /terms/  /legal/  /copyright/  /about/terms-of-use/
  /policies/                                             all 404
  /privacy/                                              200
A privacy policy governs personal data, not automated retrieval. Absent, not
none - a university's terms may live somewhere not checked here.
