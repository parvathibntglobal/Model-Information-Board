"""Terminal output and the per-run log file (workflow doc section 23).

One line per event, `[time] [STAGE  ] STATUS message`. The terminal gets the
configured verbosity; the log file always gets everything (verbose). Never
printed: page HTML, cookies, keys, the database address.
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

LOGGER = "benchmarks"
STAGES = (
    "SETUP",
    "SOURCE",
    "FETCH",
    "PARSE",
    "MATCH",
    "VALUE",
    "CHECK",
    "MERGE",
    "DERIVE",
    "CHANGE",
    "PUBLISH",
    "SUMMARY",
)
STATUSES = ("IN", "OK", "NEW", "TRY", "WARN", "FLAG", "FAIL", "BLOCK", "SKIP", "DONE")
RULE = "=" * 80
THIN = "-" * 80

#: verbosity -> the lowest level the terminal prints
LEVELS = {"quiet": logging.WARNING, "normal": logging.INFO, "verbose": logging.DEBUG}

#: Lines that make up the run header and summary are printed even at --quiet.
SUMMARY = logging.WARNING + 5
logging.addLevelName(SUMMARY, "SUMMARY")


class _Plain(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


class Console:
    """The `benchmarks` logger, a terminal handler and a log-file handler."""

    def __init__(self, *, verbosity: str, log_path: Path | None, stream=None):
        self.logger = logging.getLogger(LOGGER)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        for handler in list(self.logger.handlers):
            self.logger.removeHandler(handler)
            handler.close()
        terminal = logging.StreamHandler(stream or sys.stdout)
        terminal.setLevel(LEVELS.get(verbosity, logging.INFO))
        terminal.setFormatter(_Plain())
        self.logger.addHandler(terminal)
        self.log_path = log_path
        self._file: logging.Handler | None = None
        if log_path is not None:
            self.attach_file(log_path)

    def attach_file(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(_Plain())
        self.logger.addHandler(handler)
        self._file = handler
        self.log_path = path

    def close(self) -> None:
        for handler in list(self.logger.handlers):
            handler.flush()
            self.logger.removeHandler(handler)
            handler.close()

    # ── lines ────────────────────────────────────────────────────────────

    def line(self, stage: str, status: str, message: str, *, level: int = logging.INFO) -> None:
        now = datetime.now(UTC).strftime("%H:%M:%S")
        self.logger.log(level, f"[{now}] [{stage:<7}] {status:<5} {message}")

    def detail(self, stage: str, status: str, message: str) -> None:
        """Verbose only: every cell decision, every unmatched name."""
        self.line(stage, status, message, level=logging.DEBUG)

    def text(self, message: str, *, level: int = logging.INFO) -> None:
        self.logger.log(level, message)

    def rule(self, thin: bool = False, *, level: int = logging.INFO) -> None:
        self.logger.log(level, THIN if thin else RULE)

    def header(self, run_id: int | str, trigger: str, scope: str, dry_run: bool) -> None:
        when = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        mode = "   DRY RUN (nothing is written)" if dry_run else ""
        self.rule(level=SUMMARY)
        self.text(
            f" BENCHMARK RUN #{run_id}   trigger={trigger}   scope={scope}   {when}{mode}",
            level=SUMMARY,
        )
        self.rule(level=SUMMARY)
