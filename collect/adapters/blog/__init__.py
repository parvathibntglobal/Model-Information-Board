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
    validators.py  conditional GET, and the watermark columns it will need
    options.py     extraction options, pinned because offsets depend on them
    fetch.py       the fetch path itself

Per-host politeness now lives in `collect/limiter.py`: both adapters use it,
it depends on nothing but the standard library, and keeping it here meant
`adapters/github.py` could not be imported without feedparser installed.

WHY THESE RE-EXPORTS ARE LAZY
-----------------------------
`feedparser` and `trafilatura` are needed by exactly one module in this
package, `parse.py`. Re-exporting eagerly meant that importing ANY name from
this package — `RobotsGate`, which needs only httpx, or the conditional-GET
validators, which need nothing at all — executed `parse.py` and failed
without them.

Engineer 2 found what that costs: a partial install produced five collection
errors, pytest reported `Interrupted`, and no tests ran at all — including
every GitHub test, none of which had anything to do with parsing a feed. A
missing optional dependency should cost you the parts that need it and
nothing else, so the imports happen on attribute access (PEP 562) and
`import collect.adapters.blog.robots` no longer pays for a feed parser it
will never call.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type checkers and IDEs only
    from collect.adapters.blog.fetch import (
        ArticleFetch,
        BlogFetcher,
        FeedFetch,
        FeedRun,
        Outcome,
        StoredArtifact,
        fetcher_for_source,
    )
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

#: name -> the submodule that defines it. Grouped by module so the dependency
#: each one pulls in is visible: only `parse` and `fetch` need feedparser and
#: trafilatura.
_EXPORTS: dict[str, str] = {
    name: "collect.adapters.blog.fetch"
    for name in (
        "ArticleFetch", "BlogFetcher", "FeedFetch", "FeedRun", "Outcome",
        "StoredArtifact", "fetcher_for_source", "FeedOnlyError",
        "NotAFetchTargetError",
    )
} | {
    name: "collect.adapters.blog.parse"
    for name in ("FeedEntry", "NotBytesError", "ParsedFeed",
                 "extract_article_text", "parse_feed")
} | {
    name: "collect.adapters.blog.robots"
    for name in ("RobotsDecision", "RobotsGate", "RobotsRuling")
} | {
    name: "collect.adapters.blog.validators"
    for name in ("FeedValidators", "InMemoryValidatorStore", "ValidatorStore")
} | {
    name: "collect.adapters.blog.options"
    for name in ("DEFAULT_EXTRACTION", "ExtractionOptions")
}


def __getattr__(name: str):
    """Import the defining submodule on first access, and only that one."""
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    value = getattr(import_module(module_name), name)
    globals()[name] = value  # cached, so this costs one lookup per name
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS))


__all__ = [
    "DEFAULT_EXTRACTION",
    "ArticleFetch",
    "BlogFetcher",
    "ExtractionOptions",
    "FeedEntry",
    "FeedFetch",
    "FeedOnlyError",
    "FeedRun",
    "FeedValidators",
    "InMemoryValidatorStore",
    "NotAFetchTargetError",
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
