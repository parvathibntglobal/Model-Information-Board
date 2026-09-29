"""Send this project's log output to a file in `logs/`, as well as the terminal.

WHY THIS EXISTS. Nothing in this repo wrote a log file. There is exactly one
`logging.basicConfig` (judge/cli.py) and no `FileHandler` anywhere, so every
`log.error` went to a console and nowhere else - which means the account of a run
survived exactly as long as the terminal scrollback did. The structured records
DO persist (`var/fetch/<run_id>.jsonl` and `var/spend-ledger.jsonl`), and those
stay the authority; this is for the unstructured half that had no home: the
rawstore's NFR-4 errors, an adapter's HTTP failure, a traceback.

THE FILE IS AN ADDITION, NEVER A REPLACEMENT. The terminal handler is left
exactly as it was. A log that moved output OFF the screen would have hidden the
fetch's own step-by-step account, which is the thing somebody starts the backend
in a visible terminal to watch.

ROTATED, BECAUSE AN ON-DEMAND FETCH IS CHATTY. A run against a shared database
from a machine holding only its own blobs once emitted 2,210 rawstore errors in
one stage. That particular flood is fixed at source, but a log file that can only
grow is a disk-full waiting for the next one.

⚠ IT NEVER RAISES. A read-only checkout, a full disk or a `logs/` that is
  somebody's file rather than a directory must not stop a run from starting.
  `attach()` returns None and says so; the terminal handler is untouched and the
  process carries on. Logging that can end the thing it is logging is worse than
  no logging.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

#: Override for a container or a machine that keeps logs elsewhere.
LOGS_DIR_ENV = "MODELBOARD_LOGS_DIR"

#: 5 MB x 3 keeps roughly the last few runs without unbounded growth.
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3

#: The terminal already carries a timestamp for the fetch's own lines, but a
#: file is read long after the fact and out of order, so every record gets one.
FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def logs_dir() -> Path:
    raw = os.getenv(LOGS_DIR_ENV)
    return Path(raw) if raw and raw.strip() else ROOT / "logs"


def attach(stem: str, *, level: int = logging.INFO) -> Path | None:
    """Add a rotating file handler for `stem`. Returns the path, or None.

    Idempotent per stem: re-attaching the same file (which `--reload` does when
    the worker re-imports its entry point) adds no second handler and therefore
    writes no duplicated lines.
    """
    try:
        directory = logs_dir()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{stem}.log"

        root = logging.getLogger()
        marker = f"modelboard-file:{path}"
        for existing in root.handlers:
            if getattr(existing, "_modelboard_marker", None) == marker:
                return path

        handler = logging.handlers.RotatingFileHandler(
            path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(FORMAT))
        handler.setLevel(level)
        handler._modelboard_marker = marker  # type: ignore[attr-defined]
        root.addHandler(handler)
        # The ROOT logger's own level gates what reaches any handler. Left alone
        # when it is already permissive enough, so this cannot make a process
        # quieter than it was.
        if root.level == logging.NOTSET or root.level > level:
            root.setLevel(level)
        return path
    except Exception:  # noqa: BLE001 - see the module docstring
        return None
