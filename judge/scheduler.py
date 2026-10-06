"""Which tracked models are due a fetch, and a host-free summary of what ran.

Pure logic, no I/O. `scripts/run_scheduled_fetches.py` is the runner that reads
the registry and the fetch log, calls `rank_due`, launches `fetch_model` per
model, and posts `summarise_runs` to an issue. The runner is disabled by default
(`SCHEDULER_ENABLED`); nothing here harvests.

⚠ THIS DECIDES ORDER, NEVER MEMBERSHIP-BY-SKIPPING. A tracked, in-window model
  that is due is always in the list. The selection rule is "first fetch on
  registry arrival, then a weekly cadence, oldest first" - it never drops a
  model on a yield guess, because a model a schedule stopped fetching reads
  exactly like one nobody discusses (rule 4). Yield-ordering within a night is a
  later refinement and needs the end-record fields (#489) to have accumulated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache


@dataclass(frozen=True)
class Policy:
    """`contract/scheduler.yaml`: cadence and the two thread caps (rule 5).

    Were code constants (7, 100, 25) until 2026-10-05; moved unchanged.
    """

    cadence_days: int
    first_fetch_thread_cap: int
    refresh_thread_cap: int


class SchedulerPolicyError(RuntimeError):
    """`contract/scheduler.yaml` is missing a key or carries a bad value."""


@lru_cache(maxsize=1)
def policy() -> Policy:
    """Read the policy. Every key required, each a positive int - no default
    in code, so a missing value refuses rather than scheduling on a guess."""
    from judge.config import _read

    raw = _read("scheduler.yaml") or {}
    values = {}
    for key in ("cadence_days", "first_fetch_thread_cap", "refresh_thread_cap"):
        v = raw.get(key)
        if not isinstance(v, int) or isinstance(v, bool) or v < 1:
            raise SchedulerPolicyError(
                f"contract/scheduler.yaml `{key}` must be a positive integer, not {v!r}"
            )
        values[key] = v
    return Policy(**values)


@dataclass(frozen=True)
class DueModel:
    model_version_id: str
    display_name: str
    #: "first fetch" (never succeeded) or "refresh (N days)".
    reason: str
    #: FETCH_MAX_THREADS for this run - larger on a first fetch.
    thread_cap: int
    #: None on a first fetch; the last successful fetch otherwise.
    last_success: datetime | None


def rank_due(
    rows: list[dict],
    now: datetime,
    *,
    rules: Policy | None = None,
) -> list[DueModel]:
    """The tracked, in-window models due a fetch, first-fetch first then oldest.

    `rows` each carry: model_version_id, display_name, tracked (bool),
    in_window (bool), last_success (datetime | None).

    ⚠ ABSENT IS NOT DUE-NOW BY DEFAULT AND NOT NEVER-DUE EITHER (rule 6). A row
      missing `in_window` is treated as not in window - the scheduler fetches
      only what the board would show, and an unknown window is not a licence to
      spend. `last_success` None means never succeeded, which is a first fetch,
      not "fetched at the epoch".
    """
    rules = rules or policy()
    due: list[DueModel] = []
    cutoff = now - timedelta(days=rules.cadence_days)
    for r in rows:
        if not r.get("tracked") or not r.get("in_window"):
            continue
        mv_id = r["model_version_id"]
        name = r.get("display_name") or mv_id
        last = r.get("last_success")
        if last is None:
            due.append(DueModel(mv_id, name, "first fetch", rules.first_fetch_thread_cap,
                                  None))
        elif last <= cutoff:
            reason = f"refresh ({(now - last).days} days since last success)"
            due.append(DueModel(mv_id, name, reason, rules.refresh_thread_cap, last))
    #: FIRST FETCHES FIRST (no last_success), then the longest-stale. `min`
    #: datetime stands in for "never", so first fetches sort ahead of every
    #: refresh, and among refreshes the oldest success comes first. Never skips.
    due.sort(key=lambda d: d.last_success or datetime.min.replace(tzinfo=now.tzinfo))
    return due


#: End-record fields that carry NO host, quote or author - safe for a public
#: issue. `detail` is deliberately NOT here: a write-guard refusal's detail names
#: the database host, so the summary is built from structured fields only.
_SAFE_FIELDS = (
    "status", "documents_appended", "harvest_arms_errored", "harvest_http_errors",
    "threads_read", "claims_verified", "claims_stored", "threads_unreadable_here",
)


def summarise_runs(records: list[dict]) -> str:
    """A host-free markdown summary of a scheduled batch, for a public issue.

    ⚠ STRUCTURED FIELDS ONLY, BECAUSE THE ISSUE IS PUBLIC. An end record's
      `detail` string can carry the database host (a write-guard refusal reads
      "the database is 203.0.113.5"), so this never reads `detail`. It reads the
      counted fields from #489 and the model name, and nothing else. A field
      that is absent is shown as "-", never 0 (rule 6).
    """
    lines = [f"**Scheduled fetch: {len(records)} model(s).** "
             "Counts only; no quotes, authors or hosts.", "",
             "| Model | Outcome | Docs appended | Threads read "
             "| Quotes verified (count) | Unreadable here | Harvest errors |",
             "|---|---|---|---|---|---|---|"]

    def cell(rec, key):
        v = rec.get(key)
        return "-" if v is None else str(v)

    for rec in records:
        errored = rec.get("harvest_arms_errored") or []
        lines.append(
            f"| {rec.get('model') or rec.get('model_version_id') or '?'} "
            f"| {rec.get('status') or '?'} "
            f"| {cell(rec, 'documents_appended')} "
            f"| {cell(rec, 'threads_read')} "
            # VERIFIED, NOT STORED (2026-10-05). Since #502 evidence is
            # written as board entries and `claims_stored` is 0 on every run,
            # so this column read 0 for every model while each produced
            # hundreds of verified quotes.
            f"| {cell(rec, 'claims_verified')} "
            # Threads this run could not read because their payloads are on
            # another machine: a reason for a low count, not a count of zero.
            f"| {cell(rec, 'threads_unreadable_here')} "
            f"| {', '.join(errored) if errored else '-'} |"
        )
    ok = sum(1 for r in records if r.get("status") == "ok")
    lines += ["", f"{ok} of {len(records)} ended ok. "
              "A model absent from this list was not due; a count shown as `-` was "
              "not reported by that run, which is not the same as zero."]
    return "\n".join(lines) + "\n"


def safe_record(end_record: dict) -> dict:
    """Keep only the host-free fields of an end record. The one enforcement
    point: `summarise_runs` reads what this returns, so a `detail` can never
    reach the issue even if a caller passes a raw record."""
    out = {k: end_record[k] for k in _SAFE_FIELDS if k in end_record}
    for key in ("model", "model_version_id", "display_name"):
        if end_record.get(key):
            out[key] = end_record[key]
    return out
