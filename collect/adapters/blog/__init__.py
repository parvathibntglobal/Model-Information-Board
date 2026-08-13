"""The blog adapter. RSS and sitemaps, no auth, ~1 req/sec, robots respected.

**The only positive-evidence channel.** Engineers blog about what worked and
file issues about what didn't, so without this adapter silent-failure
capabilities like summarisation can never reach positive consensus and the
advisor can never approve a cheaper summariser — the single recommendation this
product exists to make.

Fetch path only, and it depends on no feed list: the mechanics are the same
whether there are three feeds or forty. Feed selection waits on the source
ruling NFR-5 requires.

    parse.py       the only importer of feedparser and trafilatura. Bytes in
    robots.py      the gate, consulted before every request including redirects
    limiter.py     per-host politeness
    validators.py  conditional GET, and the watermark columns it will need
    options.py     extraction options, pinned because offsets depend on them
    fetch.py       the fetch path itself
"""

from collect.adapters.blog.fetch import (
    ArticleFetch,
    BlogFetcher,
    FeedFetch,
    FeedRun,
    Outcome,
    StoredArtifact,
    fetcher_for_source,
)
from collect.adapters.blog.limiter import HostLimiter
from collect.adapters.blog.options import DEFAULT_EXTRACTION, ExtractionOptions
from collect.adapters.blog.parse import (
    FeedEntry,
    NotBytesError,
    ParsedFeed,
    extract_article_text,
    parse_feed,
)
from collect.adapters.blog.robots import RobotsDecision, RobotsGate, RobotsRuling
from collect.adapters.blog.validators import (
    FeedValidators,
    InMemoryValidatorStore,
    ValidatorStore,
)

__all__ = [
    "DEFAULT_EXTRACTION",
    "ArticleFetch",
    "BlogFetcher",
    "ExtractionOptions",
    "FeedEntry",
    "FeedFetch",
    "FeedRun",
    "FeedValidators",
    "HostLimiter",
    "InMemoryValidatorStore",
    "NotBytesError",
    "Outcome",
    "ParsedFeed",
    "RobotsDecision",
    "RobotsGate",
    "RobotsRuling",
    "StoredArtifact",
    "ValidatorStore",
    "extract_article_text",
    "fetcher_for_source",
    "parse_feed",
]
