#!/usr/bin/env python
"""Container entry point. The composition root, without the interactive refusal.

WHY THIS EXISTS RATHER THAN A FLAG ON `run-backend.py`
------------------------------------------------------

`run-backend.py` REFUSES to start without `--staging` or `--write`, and that
refusal is load-bearing on a laptop: the two DSNs in this project's `.env` are
byte-identical, so an unflagged command opened a READ-WRITE session against the
shared database while reading like a local default. **That file keeps its
refusal. Nothing here weakens it.**

A container cannot answer a prompt and has no shell history to be safe about.
Its equivalent of "say which database on purpose" is an environment it was
deployed with, so this file makes the same decision the same number of times —
once, explicitly — and fails loudly rather than defaulting when it cannot.

    run-backend.py    a person chooses per invocation, and must
    serve.py          the deployment chose once, and this names what it chose

THE PART THAT IS NOT OPTIONAL, AND IS EASY TO LOSE IN A REWRITE
----------------------------------------------------------------

`run-backend.py` is the COMPOSITION ROOT. `judge/` may not import `collect/` —
`tests/test_lane_boundary.py` enforces it — so `judge/app.py` cannot read a
payload by itself. The runner injects `SOURCE_TEXT_READER`, and without that
injection `/documents/{id}/source` answers "unwired", which reads on the page as
*this document has no text* rather than as a startup mistake.

So this file does the same wiring, by calling the same function, rather than
reimplementing it. One implementation, two entry points.

WHAT IT REFUSES
---------------

    MODELBOARD_DB unset or not one of the two names   refuse, and say both
    the named DSN empty or absent                     refuse, and say which
    ENVIRONMENT=production with no API_TOKEN          served, and /health says
                                                      it will 503 - the refusal
                                                      is judge/gate.py's to make

The last one is deliberately NOT duplicated here. `judge/gate.py` already owns
that rule and says it in the 503 body; a second copy in a different file is a
second thing to keep in step.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

#: Which environment variable holds the DSN, by name. NOT a boolean and not a
#: default: the value a person set is echoed back in the startup line, so a
#: misconfigured deployment is visible in the first log line rather than in the
#: first 503.
_DSN_VARS = {
    "write": "DATABASE_URL",
    "staging": "STAGING_DATABASE_URL",
}


def _fail(message: str) -> None:
    print(f"serve.py: {message}", file=sys.stderr, flush=True)
    raise SystemExit(2)


def main() -> int:
    # `.env` IS LOADED IF PRESENT AND IS NOT REQUIRED. On Railway the variables
    # come from the platform; in a local container run a mounted .env is the
    # convenient way to get the same shape. Platform values WIN - `override` is
    # false - because a file that shadowed the deployment's own configuration
    # is the failure this whole file exists to avoid.
    try:
        from dotenv import load_dotenv

        env_file = REPO_ROOT / ".env"
        if env_file.exists():
            load_dotenv(env_file, override=False)
            print(f"serve.py: loaded {env_file.name} (platform values take precedence)")
    except ImportError:  # pragma: no cover - dotenv is a dependency
        pass

    choice = (os.getenv("MODELBOARD_DB") or "").strip().lower()
    if choice not in _DSN_VARS:
        _fail(
            f"MODELBOARD_DB is {choice or 'unset'!r}. Set it to 'write' (uses "
            "DATABASE_URL) or 'staging' (uses STAGING_DATABASE_URL). There is no "
            "default on purpose: this project's two DSNs have been byte-identical, "
            "so a default would pick read-write against the shared database while "
            "looking like a safe one."
        )

    var = _DSN_VARS[choice]
    dsn = (os.getenv(var) or "").strip()
    if not dsn:
        _fail(f"MODELBOARD_DB={choice!r} names {var}, and {var} is empty or unset.")

    # THE DSN IS NORMALISED INTO `DATABASE_URL` BECAUSE THAT IS WHAT THE CODE
    # READS - `collect/config.py` and fifteen other sites. Selecting `staging`
    # therefore means "serve the staging DSN", and the announcement below says
    # which variable it came from so the two cannot be confused later.
    os.environ["DATABASE_URL"] = dsn

    # NEVER THE CREDENTIALS. `run-backend.py` announces host, port and database
    # name and not the password; the same rule here, in a log a platform keeps.
    tail = dsn.rsplit("@", 1)[-1] if "@" in dsn else dsn
    print(f"serve.py: MODELBOARD_DB={choice}  <- {var}  -> {tail}")
    print(f"serve.py: ENVIRONMENT={os.getenv('ENVIRONMENT', 'development')!r}  "
          f"API_TOKEN={'set' if os.getenv('API_TOKEN') else 'UNSET'}")

    # THE SAME FUNCTION THE LAPTOP RUNNER CALLS. `composition.py` holds the one
    # implementation; `run-backend.py` delegates to it too.
    #
    # NOT `import run-backend` - that was the first attempt and it failed
    # exactly as it should have. Its "name the database you mean" refusal runs
    # at MODULE level, so importing it to borrow one function triggered the
    # refusal and exited before binding. The guard was right; the borrowing was
    # wrong, and the fix was to move the function rather than to weaken it.
    from composition import wire_source_text_reader

    print(f"serve.py: source-text reader wired: {wire_source_text_reader()}")

    import uvicorn

    import judge.app

    # 0.0.0.0 because the port has to be reachable from outside the container,
    # and $PORT because the platform assigns it. 8000 is the local-container
    # fallback and matches run-backend.py, so `docker run -p 8000:8000` works
    # without being told a port.
    port = int(os.getenv("PORT", "8000"))
    print(f"serve.py: binding 0.0.0.0:{port}", flush=True)
    # THE APP OBJECT, NOT THE STRING. uvicorn's string form re-imports the app
    # in this same process, which would discard the injection made two lines up
    # - the exact failure `run-backend.py` documents. No `--reload` here; a
    # container that reloads on file change is a container with no files to
    # change.
    uvicorn.run(judge.app.app, host="0.0.0.0", port=port)  # noqa: S104
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
