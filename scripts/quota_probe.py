"""Read the RapidAPI rate-limit headers, and record ALL of them.

WHY THIS EXISTS
---------------
`x-ratelimit-requests-limit: 1000000` was asserted in a `reddit.py` docstring
added alongside the fetch path, was never read off a response, and acquired
five citations that made it look sourced. The plan says 500,000. The two
disagreed for a fortnight and nothing on disk could separate them, because
`_get` captured `-remaining` and nothing else.

So this script reads the headers rather than one header. Reading one and
inferring the rest is precisely how the wrong constant survived.

WHAT IT COSTS AND WHAT IT KEEPS
-------------------------------
One request, 1 unit. The response BODY IS DISCARDED — this is a header
reading, not a collection, so it acquires no retention obligation and writes
nothing to `raw/`. What it appends to `docs/measurements/quota-headers.jsonl`
is a UTC timestamp, the endpoint, the status, and every response header whose
name is not an authentication echo.

RUN IT TWICE TO SETTLE THE DENOMINATOR
--------------------------------------
A single reading gives the limit the header claims. It cannot distinguish
"that limit is our plan" from "that limit is some pool that is not our
billed allowance". What distinguishes them is a SECOND reading after known
consumption: if `-remaining` falls by exactly the calls made in between, the
counter tracks our requests, and the remaining question is only whether its
`-limit` is the billed one. That is a question for the RapidAPI dashboard,
which is a browser and not a call.

The gate applies. A probe is a fetch.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collect.adapters.reddit import build_client, host_for, observe_reddit_use  # noqa: E402
from collect.registry.assertions import assert_terms_reviewed  # noqa: E402
from collect.registry.sources import load_sources  # noqa: E402

LEDGER = Path("docs/measurements/quota-headers.jsonl")

#: The same listing endpoint the sweeps use, so a reading here is comparable
#: with a reading taken mid-sweep rather than being a different code path.
PATH = "/getPostsBySubreddit"

#: Header names that echo the credential back. Never recorded.
REDACT = {"x-rapidapi-key", "authorization", "set-cookie", "cookie"}


def probe(note: str) -> int:
    contract = load_sources()
    row = next((s for s in contract.platforms if s["id"] == "reddit"), None)
    if row is None:
        print("contract/sources.yaml has no `reddit` source row", file=sys.stderr)
        return 2

    observations = {"reddit": observe_reddit_use()}
    assert_terms_reviewed([row], rulings=contract.rulings, observations=observations)
    print(f"terms gate : passed, {row['terms_ruling']} "
          f"({observations['reddit']['use_basis']})")

    # `host_for()`, NOT `settings().rapidapi_host`. RapidAPI routes on the
    # `x-rapidapi-host` HEADER, which `build_client()` derives from
    # `host_for()`; a URL built from the raw variable can name a different
    # provider, and the request then reaches whichever the HEADER named while
    # this script reports the URL's. That mismatch is the defect #238 fixed in
    # the adapter on 2026-09-09 - and this script was not part of it, so it
    # kept the shape until 2026-09-10.
    host = host_for()
    with build_client() as client:
        response = client.get(
            f"https://{host}{PATH}",
            params={"subreddit": "ClaudeAI", "sort": "new"},
        )

    headers = {
        k.lower(): v for k, v in response.headers.items()
        if k.lower() not in REDACT
    }
    record = {
        "read_at": datetime.now(tz=UTC).isoformat(),
        "endpoint": PATH,
        "status": response.status_code,
        "note": note,
        # Every header, not the three we came for. The point of the exercise.
        "headers": headers,
        "body_retained": False,
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    print(f"status     : {response.status_code}")
    print(f"headers    : {len(headers)} recorded -> {LEDGER}")
    print()
    rate = {k: v for k, v in headers.items() if "ratelimit" in k or "rate-limit" in k}
    if not rate:
        print("NO RATE-LIMIT HEADER ON THIS RESPONSE. That is itself the finding.")
    for k in sorted(rate):
        print(f"  {k:42s} {rate[k]}")
    print()
    print("ALL HEADERS")
    for k in sorted(headers):
        print(f"  {k:42s} {headers[k]}")
    return 0


if __name__ == "__main__":
    note = sys.argv[1] if len(sys.argv) > 1 else "unlabelled reading"
    raise SystemExit(probe(note))
