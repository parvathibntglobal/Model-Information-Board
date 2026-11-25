"""Admin sections, kept for a short while (2026-11-25, Parvathi).

WHY. Admin mounts one section at a time and each asks the backend afresh. Measured
on 2026-11-25 from a developer machine against the shared database, two calls each:
`/admin/keywords` 23-24 s, `/admin/usage` 15-16 s, `/admin/board-entries` ~4.7 s,
`/admin/runs` ~4.2 s, `/admin/schedules` 3-9 s (it asks GitHub), and most others
1-3 s. Clicking back to a section paid the whole cost again.

THE SAME SHAPE AS judge/industry_ai/cache.py (#665), with a fresh time per section:

  * The first request for a section works it out while it waits, and keeps it.
  * Within its `fresh` seconds a kept answer is sent at once.
  * After that it is still sent at once, and ONE background recount replaces it.
  * Past `max_age` it is recounted while the visitor waits - a quiet afternoon
    never shows the morning's figures - and only if that recount fails is the
    old answer sent.
  * An error is raised and never kept, and neither is an answer that says it
    could not read its data (`reason` / `unreadable`).

THREE WAYS AN ANSWER IS NEVER STALE WHEN IT MATTERS:

  * ANY WRITE CLEARS EVERYTHING. A POST/PUT/PATCH/DELETE to the API (a ruling, a
    model added, a setting saved) empties this cache when it succeeds
    (judge/app.py middleware), so what a person just did shows on the next read.
  * REFRESH. A request carrying `X-Recount: 1` - Admin's Refresh button - is
    worked out while it waits and replaces the kept answer.
  * LIVE SECTIONS ARE KEPT BRIEFLY. Runs, usage and the database report live
    state, so their fresh time is seconds, not minutes: the cache only spares a
    click-away-and-back, and a poll still sees each recount.

ALSO `/blog-posts`: Admin asks for every stored draft (`?include=all`) on each
load, for the Blogs menu's "to review" count - measured 16.5 s on 2026-11-25. Kept
the same way; approving or rejecting a post is a write, so it clears it.

ALSO `/coverage`, which Admin's health figures read on each load (~2.5-3.7 s,
2026-11-25). It changes only when the evidence pipeline writes.

Kept per section and per query (e.g. `/admin/usage?hours=24&days=14`), at most
`MAX_ENTRIES` answers, least recently read dropped first. Signed-in only: every
route this wraps is an /admin route behind the gate, and its answer is the same
for every signed-in person.
"""

from __future__ import annotations

import contextvars
import functools
import inspect
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import Any

log = logging.getLogger(__name__)

MAX_ENTRIES = 128

#: Off in the test suite (tests/conftest.py), where a test may write to the
#: database directly and read an endpoint twice; tests/test_admin_cache.py turns
#: it on for itself.
ENABLED = True

#: Set by judge/app.py for a request carrying `X-Recount: 1` (Admin's Refresh).
RECOUNT: contextvars.ContextVar[bool] = contextvars.ContextVar("admin_recount", default=False)

#: key -> (worked out at, monotonic; the answer)
_entries: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()
_refreshing: set[Hashable] = set()
_lock = threading.Lock()


def _store(key: Hashable, answer: Any) -> None:
    # AN ANSWER THAT SAYS IT COULD NOT READ ITS DATA IS NEVER KEPT (as in
    # judge/industry_ai/cache.py): a migration or a reconnect shows on the next load.
    if isinstance(answer, dict) and (answer.get("reason") or answer.get("unreadable")):
        return
    with _lock:
        _entries[key] = (time.monotonic(), answer)
        _entries.move_to_end(key)
        while len(_entries) > MAX_ENTRIES:
            _entries.popitem(last=False)


def _refresh(key: Hashable, build: Callable[[], Any]) -> None:
    try:
        _store(key, build())
    except Exception:  # noqa: BLE001 - a failed recount keeps the last answer
        log.exception("admin cache: recounting %r failed; the previous answer stays", key)
    finally:
        with _lock:
            _refreshing.discard(key)


def get(key: Hashable, build: Callable[[], Any], *, fresh: float, max_age: float) -> Any:
    """The kept answer for `key`, or `build()`'s - see the module docstring."""
    if not ENABLED:
        return build()
    recount = RECOUNT.get()
    with _lock:
        entry = None if recount else _entries.get(key)
        age = None if entry is None else time.monotonic() - entry[0]
        too_old = age is not None and age >= max_age
        if entry is not None and not too_old:
            _entries.move_to_end(key)
            if age >= fresh and key not in _refreshing:
                _refreshing.add(key)
                threading.Thread(target=_refresh, args=(key, build),
                                 name="admin-cache-refresh", daemon=True).start()
            return entry[1]
        if too_old and key in _refreshing:
            # Someone else's recount of this section is running: the old answer now.
            return entry[1]
        if too_old:
            _refreshing.add(key)
    try:
        answer = build()
        _store(key, answer)
    except Exception:
        if not too_old:
            raise
        log.exception("admin cache: recounting %r failed; sending the old answer", key)
        return entry[1]
    finally:
        if too_old:
            with _lock:
                _refreshing.discard(key)
    return answer


def kept(name: str, *, fresh: float, max_age: float):
    """Decorate an /admin GET route: its answer is kept per `name` and per query
    argument. The route's signature is unchanged, so FastAPI reads it as before."""

    def wrap(fn):
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def route(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            key = (name, tuple(sorted(bound.arguments.items())))
            return get(key, lambda: fn(*args, **kwargs), fresh=fresh, max_age=max_age)

        return route

    return wrap


def clear() -> None:
    """Forget every kept answer: after any write, and in tests."""
    with _lock:
        _entries.clear()
