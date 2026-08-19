"""E3 for a blog article: a thread of one, with the rulings already made.

WHY THIS IS A SEPARATE ENTRY POINT AND NOT A FLAG ON `assemble`
--------------------------------------------------------------
`assemble` ranks and selects children. A blog article has none, so every
argument that exists to control selection would be inert, and `max_children`
would sit in the signature meaning nothing. Worse, the three blog rulings
(`whole_document`, `hidden_children_min = None`, entity decoding off) are not
parameters a caller should be able to get wrong — they are what a blog IS.

So the shared surface stays `flatten`, which is the piece where a defect is
expensive, and the platform-specific facts live in one function each.

THE FOUR RULINGS THIS APPLIES, AND WHERE EACH WAS DECIDED
---------------------------------------------------------
    selection_method          `whole_document`. Nothing was ranked, and a value
                              naming a ranking is what `@observed` was added to
                              prevent. NOT the schema default, NOT NULL.
    hidden_children_min       None. `include_comments=False` means WE withheld
                              the comment section, so 0 would assert "nothing
                              was withheld" — true of the platform, false of us.
                              Rule 6, leaning towards flattering our coverage.
    observed_children         0. A MEASUREMENT: we looked and stored none.
    hidden_branches_unsized   0. A MEASUREMENT: there are no `more` markers.
    flattening                `BLOG_RULES` — entity decoding OFF, because
                              trafilatura already decoded, twice. See
                              `collect/assemble/flatten.py`.

`So` substitution is left ON and is known-wrong here (box-drawing characters
inside code fences are destroyed by it). Measured in
`docs/measurements/blog-symbol-census.md`; deliberately not narrowed from a
corpus of 2 documents.

WHAT A ONE-MEMBER THREAD MAKES UNREACHABLE
------------------------------------------
`verify.py`'s `SPAN_CROSSES_COMMENTS` needs two distinct `document_id`s in the
overlapping segments and there is only ever one, so it cannot fire. `UNMAPPED_SPAN`
cannot fire either for an in-range span, because a single document's map is
gapless — `flatten` emits the JOINER only between documents, so there is no
unmapped region at all. Both are checked in `tests/test_article_assemble.py`
rather than asserted here.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from collect.assemble.flatten import BLOG_RULES, Flattened, flatten
from collect.assemble.thread import (
    BLOG_COVERAGE_HIDDEN_CHILDREN_MIN,
    WHOLE_DOCUMENT,
    AssembledThread,
)
from collect.config import settings
from collect.ids import stable_id
from collect.rawstore import FLATTENED, RawStore

#: `document.source` for a blog. The column comment says `github | blog |
#: reddit`, and `judge/store/cells.py` reads it as `platform` — so this string
#: IS what `platform_count` counts. A feed id here would make two blogs look
#: like two platforms.
BLOG_SOURCE = "blog"


def blog_document_id(entry_id: str) -> str:
    """`document.id` for a blog article. THE convention, one place.

    Same reasoning as `reddit_document_id`: the two ids in one `thread_context`
    row used to come from two modules, and only a cross-lane comparison noticed.
    `entry_id` is the publisher's own guid or link — never derived from content,
    because an edited post would become a second document and a second voice.
    """
    return f"{BLOG_SOURCE}:{entry_id}"


@dataclass(frozen=True)
class ArticleInput:
    """One extracted article. Deliberately not a `FeedEntry` or an `ArticleFetch`.

    Assembly takes the text and the identity, not the fetch machinery — the same
    reason `assemble` takes `root_text` rather than re-parsing a payload. It also
    means this is testable without a fetcher, a store of article bytes or a feed.
    """

    entry_id: str
    text: str
    url: str | None = None


def assemble_article(
    article: ArticleInput,
    *,
    store: RawStore,
    pipeline_version: str | None = None,
) -> AssembledThread:
    """Build the one-member `thread_context` row for a blog article.

    `article.text` is what `extract_article_text` returned — trafilatura's
    output under `DEFAULT_EXTRACTION`, already entity-decoded. It is NOT the
    article HTML: flattening markup would put tags inside the byte string every
    quote offset is measured against.

    Writes the flattened text to the store's `flattened/` namespace, which is a
    regenerable cache. Touches no database.
    """
    if not article.text:
        # An empty extraction is `extract_article_text` returning None, and the
        # caller must not turn that into a document with no body: a
        # thread_context over an empty string would verify every quote against
        # nothing and reject them all as TEXT_MISMATCH, which reads as a
        # fabricating extractor rather than as a missing article.
        raise ValueError(
            f"{article.entry_id}: no extracted text. `extract_article_text` "
            "returned None for this article, which means nothing was extracted "
            "— not that the article is empty. Do not assemble it."
        )

    version = pipeline_version or settings().pipeline_version
    document_id = blog_document_id(article.entry_id)

    flattened = flatten([(document_id, article.text)], rules=BLOG_RULES)
    stored = store.put(flattened.text, namespace=FLATTENED)

    return AssembledThread(
        id=stable_id("thread_context", document_id, version),
        # The article is its own root. There is no parent and no tree.
        thread_root_id=document_id,
        member_document_ids=flattened.member_document_ids,
        flattened=flattened,
        flattened_text_ref=stored.ref,
        observed_children=0,
        hidden_children_min=BLOG_COVERAGE_HIDDEN_CHILDREN_MIN,
        hidden_branches_unsized=0,
        pipeline_version=version,
        selection_method=WHOLE_DOCUMENT,
    )


def document_row(
    article: ArticleInput,
    *,
    text_ref: str,
    content_hash: str,
    published_at: Any = None,
    author_id: str | None = None,
) -> dict[str, Any]:
    """The `document` row for a blog article.

    Separate from `assemble_article` because they write to different places and
    one of them is irreplaceable: the document points at ARTICLE BYTES in
    `raw/`, and the thread_context points at DERIVED text in `flattened/`.
    Returning a dict rather than inserting keeps this lane's convention that a
    caller can see what is about to be stored.

    `source` is `blog` and that is load-bearing — see `BLOG_SOURCE`.
    """
    return {
        "id": blog_document_id(article.entry_id),
        "source": BLOG_SOURCE,
        "external_id": article.entry_id,
        "url": article.url,
        "created_at": published_at,
        "text_ref": text_ref,
        "content_hash": content_hash,
        "author_id": author_id,
        "status": "kept",
    }
