#!/usr/bin/env python
"""Start the API with .env loaded.

`judge/app.py` reads os.environ and does not load .env itself, so started any
other way the database-backed pages answer 503. Values are never printed.

    python run-backend.py                # local Postgres, from DATABASE_URL
    python run-backend.py --staging      # STAGING_DATABASE_URL, forced READ ONLY
    python run-backend.py --reload

--staging forces every session read-only at the server
(`default_transaction_read_only=on`), so no code path in this process can write
to the shared database whatever it tries. The guarantee is in Postgres rather
than in a promise about which functions only SELECT.
"""
import os
import pathlib
import re
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).parent

env = ROOT / ".env"
if not env.exists():
    sys.exit("No .env — copy .env.example and fill it in. See FRONTEND.md.")

for line in env.read_text(encoding="utf-8").splitlines():
    m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
    if m:
        os.environ[m.group(1)] = m.group(2)

if "--staging" in sys.argv:
    staging = os.environ.get("STAGING_DATABASE_URL", "").strip()
    if not staging:
        sys.exit("STAGING_DATABASE_URL is not set in .env")
    sep = "&" if "?" in staging else "?"
    ro = urllib.parse.quote("-c default_transaction_read_only=on")
    os.environ["DATABASE_URL"] = f"{staging}{sep}options={ro}"
    host = urllib.parse.urlparse(staging).hostname
    # Only the parent announces it. Under --reload the child re-imports this
    # module, and a line printed twice reads as two servers starting.
    if __name__ == "__main__":
        # flush=True because stdout is BLOCK-BUFFERED when redirected, while
        # uvicorn logs to stderr. Without it the one line confirming the session
        # is read-only sits in the buffer for the life of the process - invisible
        # in exactly the case where somebody is piping the output and cannot see
        # which database they just pointed at.
        print(f"  reading STAGING at {host} — sessions forced READ ONLY", flush=True)
elif __name__ == "__main__":
    print("  reading the database in DATABASE_URL", flush=True)

sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402  (imported after the environment is in place)


# ── THE GUARD IS LOAD-BEARING ON WINDOWS, AND ONLY AROUND THIS CALL ──────────
#
# `--reload` was advertised in the docstring above and crashed on Windows.
# uvicorn's reloader starts the worker with a SPAWN-based multiprocessing
# context, and a spawned child re-imports this file to reach the target. Without
# a guard the module-level `uvicorn.run(...)` ran again in the child, which tried
# to spawn its own child, and multiprocessing refused with the
# `freeze_support()` message. The server never came up.
#
# **The guard goes here and NOT around the environment loading above.** That is
# the whole subtlety: the child needs `.env` in `os.environ` and needs the
# read-only DSN rewrite, because it is the process that actually serves requests
# and `judge/app.py` reads the environment at request time. Guarding the top of
# the file would fix the crash and leave the worker pointed at no database - a
# 503 on every page, which looks like a database problem rather than a startup
# one.
#
# In the child `__name__` is `"__mp_main__"`, so the import runs and the call
# does not.
def _wire_source_text_reader() -> bool:
    """Give `judge/app.py` a way to read a payload, without either lane importing the other.

    THIS FILE IS THE COMPOSITION ROOT and is the only place allowed to touch
    both: `collect/rawstore.py` is the only reader of the payload store,
    `collect/assemble/prose.py` is the only thing that turns a payload into what
    a human wrote, and `tests/test_lane_boundary.py` enforces that `judge/`
    imports neither.

    Returns whether it wired - reported at startup rather than assumed, because
    an unwired reader makes `/documents/{id}/source` answer "unwired", and a
    silent failure there would read as "this document has no text".
    """
    from pathlib import Path as _Path

    import judge.app as app_module
    from collect.assemble import prose
    from collect.config import settings as collect_settings
    from collect.rawstore import RawStore

    store = RawStore(_Path(collect_settings().raw_store_path))

    def read(source: str, text_ref: str) -> str:
        extract = prose.for_source(source)
        if extract is None:
            # NOT a passthrough. A payload flattened verbatim lets a quote
            # verify against a JSON field value - the defect `prose.py` exists
            # to prevent, and the one that put raw JSON in front of the
            # classifier on 2026-09-10.
            raise ValueError(
                f"no prose extractor is mapped for source {source!r}; refusing "
                f"to serve the payload verbatim"
            )
        return extract(store.get_text(text_ref))

    app_module.SOURCE_TEXT_READER = read
    return True


if __name__ == "__main__":
    reload = "--reload" in sys.argv
    # THE APP OBJECT WHEN NOT RELOADING, so the injected reader survives.
    # uvicorn's string form imports the app itself, and under --reload it does so
    # in a spawned child - either way the injection this process made would be in
    # the wrong interpreter. Passing the object keeps them together; with
    # --reload the string is required and the endpoint reports itself unwired,
    # which is why that is a real state rather than an error.
    if reload:
        print("--reload: /documents/{id}/source will report itself unwired")
        uvicorn.run("judge.app:app", host="127.0.0.1", port=8000, reload=True)
    else:
        print(f"source-text reader wired: {_wire_source_text_reader()}")
        import judge.app

        uvicorn.run(judge.app.app, host="127.0.0.1", port=8000)
