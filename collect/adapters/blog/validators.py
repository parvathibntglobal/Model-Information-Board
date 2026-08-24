"""Conditional GET state: ETag and Last-Modified, and where they will live.

WHERE THIS BELONGS
------------------
`watermark`. It is already the durable per-`(source_id, query_key)` resume
state, and FR-9's acceptance — *"resumes with no gap and no refetch"* — is
exactly what a validator buys for a feed. `query_key` is the feed URL.

It does **not** fit the columns that exist today:

  `cursor`     documented as a pagination position. There are two validators,
               not one, and JSON-in-`cursor` makes the column mean different
               things per platform — the kind of overloading that passes review
               and then breaks resume for whoever reads the column name next.

  `exhausted`  has no meaning for a feed. A feed is never exhausted, only
               current.

So this needs two nullable columns, `etag text` and `last_modified text`.
**Text, verbatim, not parsed to timestamptz**: `If-Modified-Since` must echo the
server's own string byte-for-byte, and normalising through a timestamp loses
the bytes that make the comparison work.

That is a contract change, `contract/` is shared, and it has not been agreed. So
this module is the port: the 304 path is real and tested now against
`InMemoryValidatorStore`, and binding it to `watermark` later is one class
implementing two methods. Nothing here writes to the database.

⚠ WHAT THAT COSTS, MEASURED 2026-08-21 ON THE FIRST NINE-FEED SWEEP
-------------------------------------------------------------------
**`not-modified` is in the outcome vocabulary and is UNREACHABLE ACROSS RUNS.**
Validators live in memory, so every sweep sends no `If-None-Match`, every feed
answers 200, and `FeedRun.outcome` is `fetched` every time. Willison's feed had
been swept days earlier and returned all 30 entries rather than a 304.

Two consequences, and the second is worse than the cost:

  COST         every blog sweep pays the full ~123 requests. There is no
               cheap-when-unchanged path, only a designed one.

  AMBIGUITY    **a feed that has gone silent and a feed with nothing new are
               indistinguishable.** Both are `fetched` with 0 new articles.
               `netflixtechblog.com` and `medium.com/airbnb-engineering` are in
               exactly that state right now - 2 of 9 sources - and nothing in the
               run output, the schema or `harvest_run` can say which. A nightly
               chain would report success for both.

The ambiguity is the reason to land the two columns, not the request count. A
source going quiet is the cheapest possible signal that a parser broke or a feed
moved, and it is currently unobservable.

RULE 6, IN THE SMALL
--------------------
A 304 is not required to resend `ETag`, and many servers do not. Absent is not
"no validator": clearing stored validators because a 304 omitted them would turn
every second request into a full re-fetch, and it would look like the
conditional GET simply not working. `merge` keeps what we had wherever the new
response is silent.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class FeedValidators:
    """The two headers a conditional GET echoes back, exactly as received."""

    etag: str | None = None
    last_modified: str | None = None

    @property
    def is_empty(self) -> bool:
        return self.etag is None and self.last_modified is None

    def request_headers(self) -> dict[str, str]:
        """`If-None-Match` / `If-Modified-Since`, omitting what we do not have.

        Sending an empty or invented value is worse than sending neither: some
        servers answer `If-None-Match: ""` with a 304 for content we have never
        seen, and the feed would then never be read at all.
        """
        headers: dict[str, str] = {}
        if self.etag:
            headers["If-None-Match"] = self.etag
        if self.last_modified:
            headers["If-Modified-Since"] = self.last_modified
        return headers

    @classmethod
    def from_response_headers(cls, headers) -> FeedValidators:
        """Read validators off a response. Missing headers stay None."""
        etag = headers.get("etag")
        last_modified = headers.get("last-modified")
        return cls(
            etag=etag.strip() if isinstance(etag, str) and etag.strip() else None,
            last_modified=(
                last_modified.strip()
                if isinstance(last_modified, str) and last_modified.strip()
                else None
            ),
        )

    def merge(self, newer: FeedValidators) -> FeedValidators:
        """Newer values win; silence keeps the old one. See rule 6 above."""
        return replace(
            self,
            etag=newer.etag if newer.etag is not None else self.etag,
            last_modified=(
                newer.last_modified if newer.last_modified is not None else self.last_modified
            ),
        )


@runtime_checkable
class ValidatorStore(Protocol):
    """Where conditional-GET state persists between runs.

    Two methods, because that is all `watermark` will need to satisfy: a
    keyed read and a keyed write. `feed_url` is the `watermark.query_key`.
    """

    def load(self, feed_url: str) -> FeedValidators | None: ...

    def save(self, feed_url: str, validators: FeedValidators) -> None: ...


class InMemoryValidatorStore:
    """The build-time implementation. Deliberately not durable.

    A dict rather than a JSON file on purpose: a file would work, and would
    then quietly become the place this state lives, which is how a temporary
    store outlives the contract change it was standing in for. Losing it costs
    one full feed fetch.
    """

    def __init__(self, initial: dict[str, FeedValidators] | None = None) -> None:
        self._state: dict[str, FeedValidators] = dict(initial or {})

    def load(self, feed_url: str) -> FeedValidators | None:
        return self._state.get(feed_url)

    def save(self, feed_url: str, validators: FeedValidators) -> None:
        if validators.is_empty:
            # Nothing to store. Recording an empty pair would make a later
            # `load` return "we have validators" and send no headers.
            return
        existing = self._state.get(feed_url)
        self._state[feed_url] = existing.merge(validators) if existing else validators

    def tracked_feeds(self) -> list[str]:
        """Feeds with stored validators.

        Deliberately not `__len__`. A store with a `__len__` is falsy while
        empty, so `store or SomeDefault()` silently replaces the caller's own
        store on every first run — which is exactly the defect this method
        exists to not have. Truthiness must never carry meaning here.
        """
        return sorted(self._state)
