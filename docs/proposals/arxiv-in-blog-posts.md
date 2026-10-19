# Proposal: arXiv abstracts may be quoted in blog posts, with arXiv's acknowledgement

**Proposed 2026-10-16 by anooj. Needs the second reviewer (Parvathi) — `contract/` gets two eyes.**

## What changed

The team read arXiv's API Terms of Use. Publishing is permitted, provided each page that uses
arXiv's API output carries arXiv's acknowledgement:

> Thank you to arXiv for use of its open access interoperability.

`contract/sources.yaml` ruling `arxiv-api-terms` still says what it said on 2026-09-08:
`basis: internal-development-only`, holding "only while nothing is published externally", with
**"NO TERMS DOCUMENT HAS BEEN READ"**. That last sentence is no longer true, and the basis no
longer matches what we intend to do.

## What already shipped on `anooj_011blogs` (not `contract/`)

- `blog_topics.yaml` `posts.arxiv_as_source: true`, with `posts.arxiv_acknowledgement` holding the
  sentence above. Required while arXiv is a source; absent raises (rule 12).
- The topic harvest queries `cs.AI`, `cs.LG`, `cs.CL` and `cs.SE`, one category at a time
  (newest 150 submissions per category per run, one request every 3 seconds).
- A topic post quoting an arXiv source credits the paper by title, with a link to its abstract page,
  and shows the acknowledgement under its source list (`generate_sample_blogs.export_post`
  `acknowledgement`, `web/src/board/views.js` `sourcesBlock`).
- What is quoted is the **abstract** the API returns, never the PDF and never arxiv.org's HTML.

These posts are **pending drafts on the local backup database only**. None is approved; nothing
is public.

## Proposed edit to `contract/sources.yaml` `arxiv-api-terms`

1. `basis`: from `internal-development-only` to the basis our vocabulary uses for "terms read,
   publication permitted with conditions". Parvathi to choose the value; it must be one the
   publication gate already understands, or the gate needs a matching change.
2. `reviewed_on: 2026-10-16`, `reviewed_by: anooj`.
3. Replace the summary's "NO TERMS DOCUMENT HAS BEEN READ" paragraph with what was read. Include
   the condition — the acknowledgement on every page that uses arXiv API output — and the scope:
   abstracts and metadata quoted with a link, never the PDF.
4. Leave the robots.txt question (`Disallow: /` on `export.arxiv.org` beside published API rate
   guidance) recorded as it is, or resolve it. Reading the API terms answers whether the API terms
   govern the API path. Say which.

## What this does NOT change

- `contract/publication.yaml` `withheld_from_public` still lists `arxiv` for the **board**. This
  proposal is about blog posts only (`derived_posts`). Showing arXiv on the board is a separate
  decision.
- No post that quotes arXiv should be **approved** until this lands. The undertaking position is
  "publication is one outside reader", and an approved post is public.

## Open questions for the reviewer

- Does the acknowledgement need to appear on the Blogs index, or only on posts that quote arXiv?
  Today it is per post.
- Abstracts carry per-paper licences. arXiv states its metadata is openly reusable, but a reviewer
  should confirm abstracts fall under that and not under each paper's own licence.
