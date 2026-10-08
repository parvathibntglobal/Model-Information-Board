# arXiv full text: read the paper, not just the abstract

**Proposed 2026-10-07 by anooj (drafted with Claude). Status: PROPOSED, not
ratified.** It changes the `arxiv-api-terms` ruling in `contract/sources.yaml`,
so it is reviewed before anything is fetched. Nothing in this document has been
implemented, and no PDF has been downloaded while drafting it: the current
ruling forbids that.

## The decision asked for

Change `arxiv-api-terms` so the pipeline may download each harvested paper's
**PDF**, extract its text, and let the extractor read the **whole paper** rather
than its ~200-word abstract. Store it for internal research use; **never serve
it**.

## Why

Since #512, arXiv harvests work: for `deepseek/deepseek-v4-flash` a harvest
stored 5 papers, all naming the model in title or abstract (local restored copy,
2026-10-07). But the Atom API returns only metadata, so each document is the
abstract: about 200 words (187-243 across those 5).

A paper evaluating a model puts its findings in the results tables, the error
analysis and the limitations, not in the abstract. Reading the abstract alone
leaves most of the evidence unread.

## What arXiv's API Terms of Use say

Read on 2026-10-07; the ruling recorded `terms_document_read: false` until now.

| The terms say | What follows for us |
|---|---|
| *"You are free to use descriptive metadata ... under the terms of the Creative Commons Universal (CC0 1.0)"*. Metadata includes *"title, abstract, authors, identifiers, and classification terms"*. | **Abstracts are public-domain metadata.** Storing them, quoting them and showing them is allowed. (`contract/publication.yaml` withholds arXiv entirely; for abstracts that is stricter than the terms. That is a separate question, flagged at the end.) |
| *"Retrieve, store, and use the content of arXiv e-prints for your own personal use, or for research purposes."* | **Downloading and storing a paper to read it is allowed, if our use is research.** See open question 1. |
| *"Store and serve arXiv e-prints (PDFs, source files, or other content) from your servers"* is listed under **must not**, unless the copyright holder or the paper's licence permits it. | **Storing is fine, serving is not.** No route may return a paper's full text or file. A claim's quote is a fragment shown internally, and the link goes to arXiv. |
| *"Direct users to arXiv.org to retrieve e-print content ... We encourage you to link to the abstract page."* | **Every arXiv link is to `arxiv.org/abs/<id>`.** That is the existing `document.url`. |
| *"No more than one request every three seconds ... a single connection at a time"*, and these limits *"apply to all of the machines under your control **as a whole**."* | **Our limiter is per process** (`HostLimiter`, `MIN_INTERVAL_SECONDS = 3.0`). The nightly runner and a laptop fetching at once would together exceed the limit. A PDF per paper doubles our arXiv requests. See open question 3. |
| *"Attempt to circumvent rate limits"*, *"use someone else's credentials"*: **must not**. | Already true. |

## PDF or HTML: PDF, and why

arXiv offers two forms of a paper's text: the **PDF**, and an **HTML** rendering
(`arxiv.org/html/<id>`) generated from the LaTeX source.

| | PDF | HTML |
|---|---|---|
| Coverage | **Every paper, every version.** | Only papers whose LaTeX converts. arXiv calls it experimental, and conversions fail for some papers. |
| Stable per version | Yes: `v1` and `v2` are separate files, which matches our versioned `document` id. | Rendered by arXiv's converter. It can change when the converter changes, which would change the content hash of "the same" paper. |
| Where it is served | `export.arxiv.org/pdf/<id>`, the host arXiv designates for programmatic access. | `arxiv.org/html/<id>`, the interactive site. |
| Text quality | Needs PDF-to-text. Two-column layout, hyphenation, ligatures (`fi`, `fl`), equations, running headers. | Clean paragraphs and real section headings. |
| Sections, for chunking | Must be recovered from headings in the extracted text. | Given by the markup. |

**My view: PDF, as you suggested.** Coverage decides it. A source that exists for
only some papers turns "the extractor read the paper" into "it read the paper
when the converter worked". That is an absence we would cause, and it would
read on the board as an absence we found (rules 4 and 8). The PDF also matches
our per-version document ids, and it comes from the host arXiv designates for
automated access.

HTML's real advantage is text quality and sections. Treat that as a possible
later improvement (prefer HTML when it exists, fall back to PDF), decided by
measurement and not assumed.

**Verbatim checking still works with PDF.** Rule 1 checks a quote against *the
text the extractor was given*, which here is our extracted text. A ligature or a
hyphen break therefore cannot make a real quote fail. It can only make a quote
read slightly differently from the typeset page, which the measurement step
below checks.

## Open questions for the reviewer

1. **Is the board "research purposes"?** The terms allow content use *"for your
   own personal use, or for research purposes"*. We extract findings to compare
   models, internally, behind a login, and the public view withholds arXiv. I
   read that as research use, but this is a company's product, and the terms
   invite exactly this question: *"If you have questions about what uses of arXiv
   APIs and content are acceptable, please contact our user support team."*
   **Recommendation: ask arXiv support before the first full-text fetch, and
   record the answer in the ruling.**
2. **robots.txt.** CLAUDE.md's settled stack includes *"robots.txt respected"*,
   and `export.arxiv.org/robots.txt` reads `Disallow: /` (recorded 2026-09-07).
   arXiv nevertheless publishes this rate limit for programmatic use of that very
   host. The existing ruling leaves *"THE API-VERSUS-ROBOTS QUESTION ...
   UNRESOLVED"*, and the abstract feed already lives with it. PDFs from the same
   host widen it. **This proposal does not resolve it by implication.** It asks
   the reviewer to rule that arXiv's explicit API terms govern its API host,
   or to leave full text blocked. The question can also go to arXiv support with
   question 1.
3. **Rate limit across machines.** Before any PDF fetch, `HostLimiter` must hold
   **across machines**, for example a last-request timestamp in the shared
   database, taken with an advisory lock before each arXiv request. Without it
   we would breach a limit the terms state precisely, once two machines fetch at
   the same time.
4. **The paper's own licence.** Some papers are CC BY, which permits
   redistribution. We do not need that, because we do not serve papers, so the
   licence is recorded on the document for completeness and no behaviour
   depends on it.

## How it would work, once ruled

1. **Fetch:** for each paper `harvest()` keeps, one more request for
   `https://export.arxiv.org/pdf/<versioned id>`, through the same cross-machine
   limiter.
2. **Store: the text is shared, the PDF stays local.** See *Storage* below.
   The extracted text goes to the shared raw store (`raw_blob`, #510), because
   it is the only thing the extractor reads. The PDF is written only to the
   fetching machine's own raw store. The document records the PDF's SHA-256,
   its size and its versioned URL, so any machine can download the identical
   file again and prove it is identical. Storing is allowed; serving is not.
3. **Never serve:** `/documents/{id}/source` and every other route return
   nothing for an arXiv full text, and a test pins that. The link shown is
   `arxiv.org/abs/<id>`.
4. **Text:** PDF to text with a permissively licensed library. The candidates
   are `pypdf` (BSD) and `pdfminer.six` (MIT); not PyMuPDF, which is AGPL. The
   extracted text is stored as a derived payload, the shared one, so the quote
   check runs against exactly what the extractor saw, on any machine.
5. **Read in sections.** A paper is 50,000 to 80,000 characters. The extractor
   already hits its 16,384-token output limit on a 10,859-character post
   (`judge/extract/client.py`), so one call per paper would truncate. Split at
   headings, send the paper's title and abstract with each section as context,
   and verify each section's quotes against that section.
6. **References and appendices:** extract the main body first. Appendices often
   hold the full results tables, so skipping them is a measured decision, not an
   assumption (rule 8).
7. **The abstract document stays.** The full text is an additional derived
   document for the same paper, so a paper whose PDF cannot be fetched or parsed
   still has its abstract. The failure is named on the run, never silent.

## Cost: an ESTIMATE, stated as one (rule 7)

Nothing here is measured yet, so these figures are arithmetic on stated inputs:

- **Inputs.** The extraction prompt is about 13,200 tokens per call (noted in
  the usage panel, 2026-09-28). A paper is 12,000 to 20,000 tokens of text. The
  extractor is `deepseek/deepseek-v4-flash` (`EXTRACTOR_MODEL` and the code
  default), at **$0.042 per 1M input tokens and $0.084 per 1M output tokens**.
  That is the registry list price in the database backup of 2026-10-07 10:34
  IST.
- **Per paper:** 3 to 5 section calls, about 50,000 to 85,000 input tokens and
  6,000 to 10,000 output tokens. That is roughly **$0.003 to $0.004 at list
  price**, against about $0.0006 for the abstract alone (one call of about
  13,500 tokens). The usage panel records that list-price arithmetic has
  overstated real DeepSeek billing, because cache hits on the shared prompt
  bill below list (#381), so the real figure is likely lower still.
- **Per model per fetch:** up to 10 papers (2 queries of 5), so up to about
  **$0.04**.
- **Time:** one extra request per paper, at 3 seconds each.

## Storage: share the text, keep the PDF local (decided by Anooj, 2026-10-08)

The requirement was the least storage without losing any data. Storing the PDF
in the shared database meets the second part and fails the first:

| | Per paper | ~220 papers (10 a model, 22 models) |
|---|---|---|
| PDF in the shared database | 1-3 MB. PDFs are already compressed, so zlib saves almost nothing | **~200-600 MB**, more than the whole raw store (~175 MB) |
| Extracted text in the shared database | 50-80k characters, ~12-20 KB compressed | **~3-4 MB** |

These sizes are estimates. The PDF size is typical of arXiv papers and is not
yet measured on our harvest. The text figure assumes the ~4x zlib ratio
measured on the raw store (2026-10-07). The measurement step below records both.

**Why nothing is lost:**
- **The extractor reads the extracted text, never the PDF.** The text is the
  input every claim and every verbatim quote is checked against, and it is the
  part that is shared.
- **arXiv keeps every version permanently under its versioned id**
  (`2610.04658v1`). Any machine can download the identical PDF again. The stored
  SHA-256 and size prove it is the same bytes, or that it is not, which is then
  named as a failure, never silently accepted.
- **The fetching machine keeps the PDF** in its local raw store, as every raw
  payload was kept before the shared store existed. That covers the rare case
  of arXiv removing a version.
- **Re-extracting with a better PDF library later** reads the local copy, or
  re-downloads one checked against the hash.

**What this costs in engineering:** `RawStore` today shares every payload it
writes. PDFs need a namespace, or a put option, that stays local, with a test
that a PDF never reaches `raw_blob`.

**Where it departs from a convention, said plainly:** CLAUDE.md's *"Raw
payloads are immutable and content-hash addressed. Reprocess from there rather
than re-fetching"* holds on the fetching machine. Another machine that needs
the PDF re-fetches it once, verified against the hash. That trade is 3 MB
against several hundred, and the reviewer should agree to it explicitly.

## Measure before turning it on

On the 5 papers already harvested, plus 15 more across 3 models:

1. **Text quality.** How often a passage a person can read on the page is
   garbled in the extracted text, by library.
2. **Quote survival.** The share of extracted quotes that read the same as the
   typeset page.
3. **What the full text adds.** Claims per paper from the full text against the
   abstract alone, and in which sections they come from.
4. **Real cost per paper**, from the spend ledger, against the estimate above.
5. **Real sizes:** each PDF, and each extracted text after compression, against
   the storage estimate above.

## The ruling text, as it would read

Replace the `tos_notes` paragraph for `arxiv` in `contract/sources.yaml`
(proposed wording; the reviewer edits it):

> Ruling arxiv-api-terms, revised [date]. arXiv API Terms of Use read
> 2026-10-07. Metadata, including abstracts, is CC0. E-print content may be
> retrieved, stored and used for research purposes; it must not be served. The
> PDF is fetched from export.arxiv.org/pdf/<id>, stored in the raw store, read
> by the extractor in sections, and never returned by any route. Links go to
> arxiv.org/abs/<id>. One request per three seconds across ALL machines, held by
> a shared limiter. [arXiv support's answer on research use, and the robots
> ruling, recorded here.]

`terms_evidence.terms_document_read` becomes `true`.

## Out of scope, flagged

- **arXiv abstracts on the public view.** Abstracts are CC0 metadata, so
  withholding arXiv abstracts publicly (`contract/publication.yaml`) is stricter
  than arXiv's terms require. Whether to relax it is a separate decision, and
  this proposal does not touch it.
