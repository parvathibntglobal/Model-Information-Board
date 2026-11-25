"""The "AI in industries" pages, kept for a few minutes (2026-11-24, Parvathi).

WHY. Each page is worked out live from `iai_item`: the summary is about a dozen
grouped counts, and one domain's page about fifteen queries (its counts, eleven
breakdowns and a page of posts). Measured from a developer machine against the
shared database on 2026-11-24, one domain's page took ~6 s. The data changes only
when a harvest or `--relabel` writes - weekly at the most - not between two page
loads, so one answer serves everyone for `TTL_SECONDS`.

A SHORT WAIT AT MOST. The first request for a view works it out while it waits;
after that, an answer older than `TTL_SECONDS` is still sent at once and ONE
background refresh replaces it (the `/seo/indexable` pattern in judge/app.py).
A refresh that fails keeps the old answer, and the next request tries again.

NEVER OLDER THAN `MAX_AGE_SECONDS` (#665 review, point 3). Refreshes happen only
when someone asks, so after a quiet weekend the kept answer predates the weekend's
harvest. An answer that old is recounted while the visitor waits (~5 s) instead of
being sent; only if that recount fails is the old answer sent, its `counted_at`
saying how old it is. An
error (an unknown domain, a bad filter) is raised and never kept. An answer that
carries a `reason` (the tables could not be read) is never kept either, so a
migration is seen on the next load.

At most `MAX_ENTRIES` views are kept, the least recently read dropped first: each
combination of a domain's tab, filters, order and page is its own view.

Every answer says when it was counted (`counted_at`, UTC), and the page shows it,
so a kept answer never reads as live (rule 11).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger(__name__)

TTL_SECONDS = 600
MAX_AGE_SECONDS = 3600
MAX_ENTRIES = 256

#: key -> (worked out at, monotonic; the answer)
_entries: OrderedDict[Hashable, tuple[float, dict]] = OrderedDict()
_refreshing: set[Hashable] = set()
_lock = threading.Lock()


def _work(build: Callable[[], dict]) -> dict:
    answer = build()
    answer["counted_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    return answer


def _store(key: Hashable, answer: dict) -> None:
    if answer.get("reason"):
        return
    with _lock:
        _entries[key] = (time.monotonic(), answer)
        _entries.move_to_end(key)
        while len(_entries) > MAX_ENTRIES:
            _entries.popitem(last=False)


def _refresh(key: Hashable, build: Callable[[], dict]) -> None:
    try:
        _store(key, _work(build))
    except Exception:  # noqa: BLE001 - a failed refresh keeps the last answer served
        log.exception("industry-ai: refreshing %r failed; the previous answer stays", key)
    finally:
        with _lock:
            _refreshing.discard(key)


def cached(key: Hashable, build: Callable[[], dict]) -> dict[str, Any]:
    """The kept answer for `key`, or `build()`'s - see the module docstring."""
    with _lock:
        entry = _entries.get(key)
        too_old = entry is not None and time.monotonic() - entry[0] >= MAX_AGE_SECONDS
        if entry is not None and not too_old:
            _entries.move_to_end(key)
            if time.monotonic() - entry[0] >= TTL_SECONDS and key not in _refreshing:
                _refreshing.add(key)
                threading.Thread(
                    target=_refresh, args=(key, build), name="industry-ai-refresh", daemon=True
                ).start()
            return entry[1]
    try:
        answer = _work(build)
    except Exception:
        if not too_old:
            raise
        # The recount of a very old answer failed: the old answer, whose counted_at
        # says its age, rather than no page. An error with nothing kept still raises.
        log.exception("industry-ai: recounting %r failed; sending the old answer", key)
        return entry[1]
    _store(key, answer)
    return answer


def clear() -> None:
    """Forget every kept answer (tests; and after a write, if one ever runs here)."""
    with _lock:
        _entries.clear()
