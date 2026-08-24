"""The only module in this lane that imports feedparser or trafilatura.

WHY IT IS THE ONLY ONE
----------------------
Both libraries ship their own HTTP layer, and both bypass
`collect.http.build_client` if used the obvious way:

    feedparser.parse("https://example.invalid/feed.xml")
        fetches, via urllib.request, sending
        `feedparser/6.0.14 +https://github.com/kurtmckee/feedparser/`

    trafilatura.fetch_url / fetch_response / trafilatura.downloads
    trafilatura.spider / .sitemaps / .feeds
        fetch, via urllib3 (pycurl if installed)

feedparser's default User-Agent is the sharper of the two. It names software
*and* gives a contact URL, so it passes every heuristic
`assert_identifying_user_agent` applies while giving whoever is deciding
whether to rate-limit us nobody at this project to reach. It is the placeholder
failure in the one form the placeholder check cannot see.

So the rule is **bytes in, never a URL and never a path**, and it is enforced
three ways rather than documented once:

  1. the signatures here take `bytes`, and reject `str` — the argument through
     which a URL could arrive does not accept one;
  2. `tests/test_lane_boundary.py` asserts no other file in `collect/` imports
     either library, and that nothing anywhere imports their download surfaces;
  3. `tests/test_blog_no_network.py` makes `urllib.request.urlopen`, `socket`
     and urllib3's `PoolManager` raise, then runs the whole fetch path against
     recorded fixtures. That is the one that catches a regression the AST test
     has no name for.

WHAT IS METADATA AND WHAT IS THE ARTIFACT
-----------------------------------------
feedparser sanitises HTML and resolves relative URIs, so the values it returns
are **not** the bytes that arrived. That is fine, and it is why the fetch path
stores the response bytes in `raw/` before anything here runs: the artifact is
immutable and re-parseable, and these dataclasses are a convenience derived
from it.

AN ID SHARED BY TWO ENTRIES IS NOT AN ID
----------------------------------------
`parse_feed` drops entries whose `entry_id` is not unique within the feed and
counts them as `ambiguous`. One of the nine seeded feeds does this today, on 8
of 20 entries, with the site root as both guid and link — so it is a live
defect rather than a prospective one, and every consequence of keeping them is
silent. The reasoning is at the check.

RULE 6, IN THE SMALL
--------------------
Every absent field stays absent. No `published_at` defaulting to now, no
feed-level author standing in for a missing entry author, no `updated` read as
`published`. A guessed author is worse than an unknown one: it attributes an
engineer's words to somebody who did not write them.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import feedparser  # type: ignore[import-untyped]  # ships no py.typed marker
import trafilatura

from collect.adapters.blog.options import DEFAULT_EXTRACTION, ExtractionOptions, extraction_version

#: Reported in `extraction_version`, so a library upgrade is visible in the
#: version string rather than inferred from a date.
TRAFILATURA_VERSION: str = getattr(trafilatura, "__version__", "unknown")
FEEDPARSER_VERSION: str = getattr(feedparser, "__version__", "unknown")


class NotBytesError(TypeError):
    """A parser was handed something that could trigger I/O.

    `feedparser.parse` accepts a URL string, a file path or a stream and will
    happily fetch. Refusing `str` at the boundary is what makes that
    unreachable rather than merely discouraged.
    """


@dataclass(frozen=True)
class FeedEntry:
    """One feed entry's metadata. Not a document — a document needs the article.

    `entry_id` is what `document.external_id` gets, so it has to be the
    publisher's own identity for the post: a guid, or the link when no guid is
    given. It is never derived from the content, because an edited post would
    then become a second document and count as a second voice.
    """

    entry_id: str
    url: str | None
    title: str | None
    author: str | None
    published_at: datetime | None
    summary_html: str | None
    content_html: str | None

    @property
    def fetchable_url(self) -> str | None:
        return self.url


@dataclass(frozen=True)
class ParsedFeed:
    """What one feed payload yielded, including what it failed to yield."""

    feed_url: str | None
    feed_title: str | None
    entries: list[FeedEntry]

    #: feedparser's `bozo` flag: the payload was malformed in some way. It is
    #: not fatal on its own — a feed with one bad character still yields its
    #: entries — so it is recorded rather than raised, and `entries` says
    #: whether anything survived.
    malformed: bool = False
    malformed_detail: str | None = None

    #: Entries dropped for having neither a guid nor a link. They cannot be
    #: identified, so they cannot become documents; counting them is what stops
    #: the drop being silent (rule 6).
    unidentifiable: int = 0

    #: Entries dropped because two or more SHARED an id. Distinct from
    #: `unidentifiable`, which is identity absent; this is identity present and
    #: not unique, which is the worse of the two because it looks like an answer.
    #: 8 of hamel.dev's 20 entries, measured 2026-08-19. See `parse_feed`.
    ambiguous: int = 0

    #: Version of the code that parsed it, for the same reason every derived
    #: row carries `pipeline_version`.
    parser_version: str = field(default_factory=lambda: f"feedparser-{FEEDPARSER_VERSION}")


def _require_bytes(payload: object, *, what: str) -> bytes:
    if isinstance(payload, bytes | bytearray):
        return bytes(payload)
    raise NotBytesError(
        f"{what} takes the response bytes, not {type(payload).__name__}. "
        "A string here can be a URL or a file path, and feedparser would fetch "
        "it with its own HTTP layer and its own User-Agent, bypassing "
        "collect.http.build_client and NFR-5's identifying-User-Agent gate. "
        "Fetch through the adapter and pass what came back."
    )


def _text_or_none(value: Any) -> str | None:
    """Empty string is absence in a feed, and absence must stay absent."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _timestamp_or_none(struct_time: Any) -> datetime | None:
    """feedparser's UTC struct_time to an aware datetime, or None.

    `published_parsed` only. `updated_parsed` is a different fact — when the
    author last edited — and reading it as the publication date would misdate
    every corrected post, which matters because FR-4 resolves aliases against
    the date a claim was made.
    """
    if not struct_time:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(struct_time), tz=UTC)
    except (TypeError, ValueError, OverflowError):
        return None


def _entry_content_html(entry: Any) -> str | None:
    """The richest body the feed offered, or None.

    A full-content feed puts the whole post in `content`; most put a teaser in
    `summary`. Both are kept separately rather than merged, because a teaser
    read as a full post would make a truncated article look complete.
    """
    contents = entry.get("content") or []
    for item in contents:
        value = _text_or_none(item.get("value"))
        if value:
            return value
    return None


#: feedparser sets `bozo` with this exception when it cannot see an XML
#: content-type in the response headers. Handing it bytes means *we* supply the
#: headers, so when we have no content-type to give, the flag is a statement
#: about our synthesised headers rather than about the payload — and reporting
#: it as malformedness would mark every well-formed feed malformed, which
#: retires the signal by crying wolf. When the caller *does* supply a
#: content-type and feedparser still objects, that is a real finding: the
#: publisher is serving a feed as something else.
_HEADER_ONLY_BOZO = "NonXMLContentType"


def parse_feed(
    payload: bytes,
    *,
    feed_url: str | None = None,
    content_type: str | None = None,
) -> ParsedFeed:
    """Parse feed bytes. Never fetches — see the module docstring.

    `feed_url` is passed to feedparser as a `Content-Location` response header,
    which is how it resolves relative entry links without being given a URL to
    fetch. Without it, a feed whose links are relative yields relative
    `entry.url` values and every article fetch fails on a URL that is not one.

    `content_type` is the response's own header, passed through for the same
    reason: feedparser uses it to decide how to treat the body, and it is the
    difference between "this feed is malformed" and "we did not tell feedparser
    what this is".
    """
    data = _require_bytes(payload, what="parse_feed")

    response_headers: dict[str, str] = {}
    if feed_url:
        response_headers["content-location"] = feed_url
    if content_type:
        response_headers["content-type"] = content_type
    parsed = feedparser.parse(data, response_headers=response_headers or None)

    candidates: list[FeedEntry] = []
    unidentifiable = 0
    for raw in parsed.entries:
        url = _text_or_none(raw.get("link"))
        entry_id = _text_or_none(raw.get("id")) or url
        if not entry_id:
            unidentifiable += 1
            continue
        candidates.append(
            FeedEntry(
                entry_id=entry_id,
                url=url,
                title=_text_or_none(raw.get("title")),
                # Entry-level author only. A feed-level author standing in here
                # would attribute a guest post to the site owner.
                author=_text_or_none(raw.get("author")),
                published_at=_timestamp_or_none(raw.get("published_parsed")),
                summary_html=_text_or_none(raw.get("summary")),
                content_html=_entry_content_html(raw),
            )
        )

    # AN ID SHARED BY TWO ENTRIES IS NOT AN ID. Measured on the nine seeded
    # feeds 2026-08-19: `hamel.dev` publishes `https://hamel.dev/` as BOTH the
    # guid and the link of 8 of its 20 entries — eight distinct articles whose
    # only identity is the site root.
    #
    # This is the same defect as an entry with no guid and no link, wearing a
    # value. It is separated from `unidentifiable` because the causes differ and
    # a reader needs to tell them apart: one feed omits identity, the other
    # publishes a placeholder.
    #
    # WHAT IT WOULD HAVE COST, HAD THEY BEEN KEPT. All three failures are silent:
    #
    #   the fetch     `fetchable_url` is the site root, so the harvester fetches
    #                 a HOME PAGE eight times and stores it as an article.
    #   the document  `ON CONFLICT (source, external_id) DO NOTHING` keeps the
    #                 first and counts seven as `already_present` — "a re-fetch
    #                 of an unchanged article, not a failure".
    #   the context   `assemble_article` derives the thread_context id from the
    #                 document id, so all eight mint the SAME id and seven
    #                 flattenings are discarded under `DO NOTHING`.
    #
    # The surviving row would then carry the home page's text, attributed to the
    # author of whichever entry happened to be first, and read as an article.
    seen: dict[str, int] = {}
    for entry in candidates:
        seen[entry.entry_id] = seen.get(entry.entry_id, 0) + 1
    shared = {key for key, n in seen.items() if n > 1}
    entries = [e for e in candidates if e.entry_id not in shared]
    ambiguous = len(candidates) - len(entries)

    exception = parsed.get("bozo_exception")
    malformed = bool(parsed.get("bozo"))
    if malformed and content_type is None and type(exception).__name__ == _HEADER_ONLY_BOZO:
        malformed = False
        exception = None

    return ParsedFeed(
        feed_url=feed_url,
        feed_title=_text_or_none((parsed.feed or {}).get("title")),
        entries=entries,
        malformed=malformed,
        malformed_detail=f"{type(exception).__name__}: {exception}" if exception else None,
        unidentifiable=unidentifiable,
        ambiguous=ambiguous,
    )


def extract_article_text(
    payload: bytes,
    *,
    url: str | None = None,
    options: ExtractionOptions | None = None,
    template_block: str | None = None,
) -> str | None:
    """Article HTML bytes to the plain text the extractor will read.

    **E3's to call, not the fetch path's.** The result is derived and
    regenerable, so it belongs in the `flattened/` namespace behind
    `thread_context.flattened_text_ref`, which is assemble's artifact. Harvest
    stores the article bytes in `raw/` and stops there; this lives here because
    it is the other half of the trafilatura boundary and must not be imported
    from two places.

    Returns None when trafilatura finds no article body — a navigation page, a
    paywall stub, a JS shell. None means *nothing was extracted*, and the
    caller must not turn that into an empty document.

    The bytes are handed over undecoded on purpose: trafilatura's charset
    detection is better than a guess made here, and a mis-decoded article would
    produce mojibake that verifies as a quote.
    """
    data = _require_bytes(payload, what="extract_article_text")
    options = options or DEFAULT_EXTRACTION
    # Spelled out rather than `**options.as_kwargs()`: trafilatura is typed, and
    # unpacking a `dict[str, object]` into it erases every parameter type, so a
    # renamed or mistyped option would arrive silently. Drift between this call
    # and the dataclass is caught by
    # `test_blog_parse.py::test_every_option_reaches_trafilatura`.
    text = trafilatura.extract(
        data,
        url=url,
        include_comments=options.include_comments,
        include_formatting=options.include_formatting,
        include_tables=options.include_tables,
        include_links=options.include_links,
        deduplicate=options.deduplicate,
        favor_precision=options.favor_precision,
        favor_recall=options.favor_recall,
        output_format=options.output_format,
    )
    if text and template_block is not None:
        text = strip_template_block(text, template_block)
    return text or None


#: Per-feed heading that begins a template block, keyed by `source` id. NOT a
#: general rule, and the measurement says why it cannot be one.
#:
#: `<h2>Recent articles</h2>` appears in 27 of the 30 stored simonwillison.net
#: pages and trafilatura keeps it in all 27 — it sits inside the content region
#: for this site's markup, so no extraction option removes it (`favor_precision`
#: drops 65 characters and keeps the block). The list is the AUTHOR'S OWN link
#: index: a model named in a headline there is named by the headline, not by
#: anyone writing about it, and 13 of the 30 name a model ONLY there.
#:
#: **A rule that fires on one site and silently does nothing on eight is the
#: thing to avoid**, so this is a mapping with an explicit absent state rather
#: than a regex applied everywhere. The other eight feeds have NO stored HTML in
#: `raw_store` — every blog document is simonwillison.net — so their templates
#: are unverified rather than absent, and `template_block_for` says which of the
#: two a caller is looking at.
TEMPLATE_BLOCKS: dict[str, str] = {
    "blog:simonwillison.net": "Recent articles",
}


def template_block_for(source_id: str | None) -> str | None:
    """The heading that begins this feed's template block, or None.

    None means **no rule recorded**, which is not the same as no template. Eight
    of the nine feeds are in that state and will be until one of their pages is
    stored and read.
    """
    return TEMPLATE_BLOCKS.get(source_id or "")


def strip_template_block(text: str, heading: str) -> str:
    """Drop everything from a markdown heading line onwards.

    ANCHORED ON THE HEADING LINE, not on the words. `## Recent articles` at the
    start of a line is the block; the same phrase inside a sentence is somebody
    writing about recent articles and stays. A substring match here would be the
    boundary defect this project has already recorded twice.

    Everything AFTER the heading goes, because the block is terminal in this
    template — it is the page footer. A rule that tried to find the end of the
    block would need to know what follows it, which is more site knowledge for no
    gain while the block is last.
    """
    pattern = re.compile(rf"^\s{{0,3}}#{{1,6}}\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    return text[: match.start()].rstrip() if match else text


def current_extraction_version(options: ExtractionOptions | None = None) -> str:
    """What to stamp on anything derived by `extract_article_text`."""
    return extraction_version(TRAFILATURA_VERSION, options)
