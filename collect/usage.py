"""What a metered API says it has left, recorded wherever it is seen.

THE TRACKING GAP THIS CLOSES. `var/rapidapi-quota.json` was written from ONE
place: the end of `scripts/fetch_model.py`'s Reddit arm, and later its X arm.
Every other metered call spent quota and recorded nothing —

  * the nightly Reddit sweep,
  * `scripts/unfiltered_sweep.py`,
  * any probe or one-off script,
  * and a fetch arm that ERRORED before reaching its write, which is precisely
    when the reading matters most.

So the panel's figure was not "the quota" but "the quota as of the last fetch
that finished its Reddit arm cleanly", and nothing on the page said so. The gap
was measured rather than theorised: a reading of 2026-08-31 said 998,076 of
1,000,000 remaining, and a single probe nine days later read 99,870 remaining —
which the stored file could not have shown, because nothing between those dates
had gone through the one writer.

WHERE THE WRITE BELONGS. In `_get`, next to the response that carried the
header. A quota reading is a property of a response, and the only place that
cannot forget it is the function that has one. Same reasoning as
`github.py`'s ledger: "an instrument that under-reports its own failures is
worse than no instrument".

`collect/` may write this: it is our own var/ file, not the judgement lane's
state, and nothing here imports `judge/`.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

#: The repo root — this file is `collect/usage.py`.
_ROOT = Path(__file__).resolve().parent.parent

#: Where the reading lives. `judge/app.py:_rapidapi_quota` reads exactly this.
QUOTA_PATH = _ROOT / "var" / "rapidapi-quota.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def record_rapidapi_quota(
    *,
    remaining: int | None,
    limit: int | None,
    read_on: str,
    read_by: str = "harvest",
    run_id: str | None = None,
    path: Path | None = None,
) -> bool:
    """Persist one quota HEADER reading. Returns whether anything was written.

    NEVER RAISES. It is called from inside a request path, and a harvest must
    not die because a metering file could not be written — the request has
    already been spent by then, so failing here loses the harvest AND the
    reading.

    A READING WITH NOTHING IN IT IS NOT WRITTEN. Both values absent means the
    response carried no quota header, which is not the same as a quota of zero,
    and blanking a good reading with it would be rule 6 in the one place the
    number is supposed to be trustworthy.

    `remaining` ALONE IS STILL WORTH RECORDING, and this is the case that
    matters now: the two arms share one key, and a response can carry
    `-remaining` without `-limit`. Writing remaining with `limit: null` says
    "this much is left, against a denominator this reading did not state" —
    which is honest, and is what rule 7 asks for when only half a figure
    arrives. It does NOT inherit the previous limit: the last two readings are
    mutually inconsistent (998,076 of 1,000,000, then 99,870 nine days later
    after ~130 requests), so an inherited denominator would be the wrong one
    carried forward silently.

    Args:
        remaining: `x-ratelimit-requests-remaining`, as read. None if absent.
        limit: `x-ratelimit-requests-limit`, as read. None if absent.
        read_on: which arm took the reading — `reddit` or `x`. One key meters
            both, so the figure cannot be split per path; naming the reader is
            the honest substitute.
        read_by: what kind of caller. `harvest`, `sweep` or `probe`. A reading
            taken by a probe is as real as one taken by a fetch, and saying
            which prevents "the fetch must have run" being inferred from it.
        run_id: the run that spent it, where there is one.
        path: override, for tests.
    """
    if remaining is None and limit is None:
        return False

    target = path or QUOTA_PATH
    record = {
        "quota_remaining": remaining,
        "quota_limit": limit,
        "at": _now(),
        "read_on": read_on,
        "read_by": read_by,
        "source_run_id": run_id,
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        # Atomic: a concurrent reader never sees half a file. `NamedTemporaryFile`
        # in the same directory, because os.replace across filesystems is not.
        with tempfile.NamedTemporaryFile(
            "w", dir=str(target.parent), delete=False, encoding="utf-8", suffix=".tmp"
        ) as fh:
            json.dump(record, fh)
            tmp = fh.name
        os.replace(tmp, target)
        return True
    except OSError:
        # Deliberately silent. See the docstring: the request is already spent,
        # and raising here would turn an unwritable file into a failed harvest.
        return False


def read_rapidapi_quota(path: Path | None = None) -> dict | None:
    """The last reading, or None. Never raises on a corrupt or absent file."""
    try:
        return json.loads((path or QUOTA_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
