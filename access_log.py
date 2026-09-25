"""Uvicorn access-log filter: a request that worked is silent, a failure is not.

WHY A FILTER AND NOT A LOG LEVEL. Uvicorn emits every access line through
`uvicorn.access` at INFO, whatever the status - a 200 and a 500 are the same
level, so raising the level to WARNING hides both and `--no-access-log` hides
both. The status code is the only thing that separates them, and it is in the
record's args rather than in its level, so reading it takes a filter.

WHAT THIS IS FOR. A frontend polling `/fetch/log` every 1.5s and `/models` on
every page view fills the terminal with lines nobody reads, and the fetch's own
step-by-step account - the thing somebody started the backend to watch - scrolls
past behind them. Silence here means "every request succeeded", which is a
claim this file can actually make because it inspects each one.

⚠ IT FAILS OPEN, AND THAT IS THE POINT. A record this cannot classify is
  PRINTED, never dropped. Uvicorn's access record carries its status in
  `args[4]`, which is a detail of a protocol implementation we do not own; if
  that shape ever changes, the cost of failing open is a noisy terminal and the
  cost of failing closed is a silently swallowed 500. Those are not comparable,
  and an absence we caused reading as an absence of errors is the shape of
  defect this project is most careful about.
"""

from __future__ import annotations

import logging

#: Below this, the request did what was asked and the line is noise. 4xx and 5xx
#: both print: a 404 from the frontend is as much a thing to see as a 500, and
#: telling them apart is the reader's job once the line is on the screen.
FIRST_FAILING_STATUS = 400


class OnlyFailures(logging.Filter):
    """Keep access lines for 4xx/5xx and anything unrecognised. Drop 1xx-3xx."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        # `(client_addr, method, full_path, http_version, status_code)` - the
        # tuple uvicorn's HTTP implementations pass to the access logger.
        if not isinstance(args, tuple) or len(args) != 5:
            return True
        status = args[4]
        if not isinstance(status, int):
            return True
        return status >= FIRST_FAILING_STATUS


def quiet_config() -> dict:
    """Uvicorn's own logging config with the access handler filtered.

    BUILT FROM UVICORN'S DEFAULT rather than written out here, so formats,
    colours and the `uvicorn.error` logger stay exactly as uvicorn ships them
    and a version bump does not silently strip them. Only the access handler
    gains a filter.

    Returned as a plain dict because it has to survive being pickled to the
    `--reload` worker, which is the process that actually serves requests and
    re-runs `configure_logging()` on the far side. The filter is named by dotted
    path for the same reason - the worker imports it by name rather than
    receiving a live object.
    """
    import copy

    from uvicorn.config import LOGGING_CONFIG

    config = copy.deepcopy(LOGGING_CONFIG)
    config.setdefault("filters", {})["only_failures"] = {
        "()": "access_log.OnlyFailures"
    }
    config["handlers"]["access"]["filters"] = ["only_failures"]
    return config
