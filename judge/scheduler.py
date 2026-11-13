"""Which tracked models are due a fetch, and a host-free summary of what ran.

Pure logic, no I/O. `scripts/run_scheduled_fetches.py` is the runner that reads
the registry and the fetch log, calls `rank_due`, launches `fetch_model` per
model, and posts `summarise_runs` to an issue. The runner is disabled by default
(`SCHEDULER_ENABLED`); nothing here harvests.

⚠ THIS DECIDES ORDER, NEVER MEMBERSHIP-BY-SKIPPING. A tracked, in-window model
  that is due is always in the list. The selection rule is "first fetch on
  registry arrival, then every third night, oldest first" - it never drops a
  model on a yield guess, because a model a schedule stopped fetching reads
  exactly like one nobody discusses (rule 4). Yield-ordering within a night is a
  later refinement and needs the end-record fields (#489) to have accumulated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache


def extract_enabled(raw: str | None) -> bool:
    """`FETCH_EXTRACT`: whether a fetch run extracts. Unset means on.

    COLLECT-ONLY (2026-10-26). `off` makes a run harvest, assemble, dedupe,
    score and triage, and skip E5 by name. The scheduled workflow sets it while
    the team has no working OpenRouter key: with a dead key E5 sent every
    thread, got no answer, ended `ok` with 0 read, and `LAST_SUCCESS` then
    counted no run at all, so every model was due every night and the tail
    of the list never ran inside the time budget.

    Unset stays `on` because that is what the admin's Fetch button has always
    done. Any other value refuses: a typo must neither quietly spend nor
    quietly not (rule 12).
    """
    value = (raw if raw is not None else "on").strip().lower()
    if value not in {"on", "off"}:
        raise SystemExit(f"FETCH_EXTRACT must be 'on' or 'off', not {raw!r}")
    return value == "on"


@dataclass(frozen=True)
class Policy:
    """`contract/scheduler.yaml`: cadence and the two thread caps (rule 5).

    Were code constants (7 days, 100, 25) until 2026-10-05; moved unchanged.
    The cadence is in HOURS since 2026-10-21 (60, every third night) - the
    contract says why days could not express it.
    """

    cadence_hours: int
    first_fetch_thread_cap: int
    refresh_thread_cap: int
    #: Days back a thread's newest dated post may be for a fetch to extract it
    #: (2026-10-26: fresh evidence only). Older unread threads stay stored.
    extraction_window_days: int


class SchedulerPolicyError(RuntimeError):
    """`contract/scheduler.yaml` is missing a key or carries a bad value."""


@lru_cache(maxsize=1)
def policy() -> Policy:
    """Read the policy. Every key required, each a positive int - no default
    in code, so a missing value refuses rather than scheduling on a guess."""
    from judge.config import _read

    raw = _read("scheduler.yaml") or {}
    values = {}
    for key in ("cadence_hours", "first_fetch_thread_cap", "refresh_thread_cap",
                "extraction_window_days"):
        v = raw.get(key)
        if not isinstance(v, int) or isinstance(v, bool) or v < 1:
            raise SchedulerPolicyError(
                f"contract/scheduler.yaml `{key}` must be a positive integer, not {v!r}"
            )
        values[key] = v
    return Policy(**values)


@lru_cache(maxsize=1)
def extract_concurrency() -> int:
    """contract/scheduler.yaml `extract_concurrency`: model calls in flight at
    once in E5. Read apart from `policy()` so the Policy shape is unchanged.
    Required, a positive integer; no default in code (rule 12)."""
    from judge.config import _read

    v = (_read("scheduler.yaml") or {}).get("extract_concurrency")
    if not isinstance(v, int) or isinstance(v, bool) or v < 1:
        raise SchedulerPolicyError(
            f"contract/scheduler.yaml `extract_concurrency` must be a positive integer, not {v!r}"
        )
    return v


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
    cutoff = now - timedelta(hours=rules.cadence_hours)
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


def take_turns(due: list[DueModel], group_of: dict[str, str],
               turns: tuple[str, ...]) -> list[DueModel]:
    """`due` reordered so the groups take turns: one from each, in `turns` order.

    Within a group, `due`'s own order is kept, so it is still first fetches and
    then the longest-stale. A group with nothing due is passed over, never waited
    on. Nothing is added or dropped: the result is a permutation of `due`.

    ⚠ AN AGENT WITH NO GROUP RAISES (rule 12). Dropping it would stop its fetch
      in silence, and putting it last would give it a turn nobody chose.
    """
    queues: dict[str, list[DueModel]] = {g: [] for g in turns}
    for d in due:
        g = group_of.get(d.model_version_id)
        if g not in queues:
            raise ValueError(f"{d.display_name} has group {g!r}, not one of {list(turns)}")
        queues[g].append(d)
    out: list[DueModel] = []
    while any(queues.values()):
        for g in turns:
            if queues[g]:
                out.append(queues[g].pop(0))
    return out


#: End-record fields that carry NO host, quote or author - safe for a public
#: issue. `detail` is deliberately NOT here: a write-guard refusal's detail names
#: the database host, so the summary is built from structured fields only.
_SAFE_FIELDS = (
    "status", "documents_appended", "harvest_arms_errored", "harvest_http_errors",
    "threads_read", "claims_verified", "claims_stored", "threads_unreadable_here",
    "extract_skipped", "model_kind", "arxiv_queries_throttled",
    # E6, counted (#608 review): counts only, no host. Without them a run that
    # sent every document back to `unvetted` looks like any other night.
    "e6_rejected", "e6_unvetted",
    # True / false: which window the run's thread scan used, so the unreadable
    # count can be said per window (#628 review). A flag, no host.
    "first_fetch",
)


#: The summary's one line for `threads_unreadable_here`; Admin -> Scheduler
#: (`scheduler_status.parse_unreadable`) finds it by this prefix.
UNREADABLE_LINE = "Unread threads this runner could not open, in the window each run scans:"


def _unreadable_line(records: list[dict]) -> str | None:
    """The night's `threads_unreadable_here`, said once and PER WINDOW.

    WHAT IT COUNTS (#628 review, measured 2026-11-12). fetch_model scans every
    unread thread in the run's window for the model's names, and counts those
    the runner cannot open (their text is on another machine). It is nobody's
    per-model figure. The window is what moves it:

        first fetch   no window - every unread thread ever stored
        refresh       threads with a post in the last `extraction_window_days`

    On 2026-11-12 the model runner's first run (Gemini 4 Carbon, a first fetch)
    reported 1,323 and its eleven refreshes 0, while the agent runner's six
    first fetches reported 1,323 each through 08:14Z: the old threads were not
    cleared, the refreshes never looked at them. A range across the two windows
    would have read as drift and hidden that.

    A run with no `first_fetch` (an older runner) is said as window not
    recorded. No run reported it: no line, never a 0 (rule 6).
    """
    groups: dict[str, list[int]] = {}
    for r in records:
        n = r.get("threads_unreadable_here")
        if not isinstance(n, int):
            continue
        key = {True: "first", False: "refresh"}.get(r.get("first_fetch"), "unknown")
        groups.setdefault(key, []).append(n)
    if not groups:
        return None

    def figure(ns: list[int]) -> str:
        low, high = min(ns), max(ns)
        span = f"{low:,}" if low == high else f"{low:,} to {high:,}"
        return f"{span} ({len(ns)} run{'s' if len(ns) != 1 else ''})"

    parts = []
    if "first" in groups:
        parts.append(f"first fetches, which scan every unread thread ever stored: "
                     f"{figure(groups['first'])}")
    if "refresh" in groups:
        days = policy().extraction_window_days
        parts.append(f"refreshes, which scan threads with a post in the last {days} days: "
                     f"{figure(groups['refresh'])}")
    if "unknown" in groups:
        parts.append(f"window not recorded: {figure(groups['unknown'])}")
    return (f"{UNREADABLE_LINE} {'; '.join(parts)}. These are not any one model's "
            "threads: a thread that cannot be opened cannot be checked for a model's "
            "name. They explain a low `Threads read`.")


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
             "| Quotes verified (count) | Harvest errors "
             "| E6 rejected | E6 unvetted |",
             "|---|---|---|---|---|---|---|---|"]

    def cell(rec, key):
        v = rec.get(key)
        return "-" if v is None else str(v)

    for rec in records:
        errored = rec.get("harvest_arms_errored") or []
        # A COLLECT-ONLY RUN READ NOTHING BY DESIGN. Its 0 is not "found
        # nothing to read", so the cell says which it is (rule 4).
        read = ("not run: collect-only" if rec.get("extract_skipped")
                else cell(rec, "threads_read"))
        lines.append(
            f"| {rec.get('model') or rec.get('model_version_id') or '?'} "
            f"| {rec.get('status') or '?'} "
            f"| {cell(rec, 'documents_appended')} "
            f"| {read} "
            # VERIFIED, NOT STORED (2026-10-05). Since #502 evidence is
            # written as board entries and `claims_stored` is 0 on every run,
            # so this column read 0 for every model while each produced
            # hundreds of verified quotes.
            f"| {cell(rec, 'claims_verified')} "
            # NO "UNREADABLE HERE" COLUMN (2026-11-12, #610 review): that count
            # is the whole corpus's, so it is one line under the table.
            f"| {', '.join(errored) if errored else '-'} "
            # E6 LAST, so a summary posted before these columns still parses.
            f"| {cell(rec, 'e6_rejected')} | {cell(rec, 'e6_unvetted')} |"
        )
    ok = sum(1 for r in records if r.get("status") == "ok")
    lines += ["", f"{ok} of {len(records)} ended ok. "
              "A model absent from this list was not due; a count shown as `-` was "
              "not reported by that run, which is not the same as zero."]
    # UNREADABLE HERE IS NOT A MODEL'S COUNT, SO IT IS SAID ONCE, PER WINDOW
    # (#610 review, then #628 review). In a per-model column the first agent
    # night showed 1,323 on all six rows and read as six counts. See
    # `_unreadable_line` for what moves it.
    unreadable = _unreadable_line(records)
    if unreadable:
        lines += ["", unreadable]
    # MEDIA'S SHARE OF THE NIGHT (#602 item 8), in counts only - no spend on a
    # public issue; each run's `cost_usd` stays in its own fetch log.
    # ONLY THE KINDS THAT ARE MEDIA (#618/#620 review, Parvathi). It counted
    # "everything but text and unknown", so `decision` (Jev, which keeps the text
    # arms) and `agent` (its own nightly run) would both have read as media.
    media = [r for r in records if r.get("model_kind") in MEDIA_SUMMARY_KINDS]
    if media:
        read = sum(int(r.get("threads_read") or 0) for r in media)
        total = sum(int(r.get("threads_read") or 0) for r in records)
        lines += ["", f"Media models: {len(media)} of {len(records)} run(s), "
                  f"{read} of {total} thread(s) read."]
    # THROTTLED, NOT FAILED (#602): a rate-limited arm is `skipped`, so the run
    # stays green - and this line is what keeps the gap from going quiet.
    throttled = [r for r in records if r.get("arxiv_queries_throttled")]
    if throttled:
        lines += ["", f"arXiv throttled (HTTP 429) on {len(throttled)} of {len(records)} "
                  f"run(s): {sum(int(r['arxiv_queries_throttled']) for r in throttled)} "
                  "query(ies) not run. Not a failure; the next fetch asks again."]
    collect_only = sum(1 for r in records if r.get("extract_skipped"))
    if collect_only:
        lines += ["", f"{collect_only} of {len(records)} ran collect-only "
                  "(`FETCH_EXTRACT=off`): harvested and stored, nothing extracted. "
                  "Their threads stay unread until an extracting run reads them."]
    return "\n".join(lines) + "\n"


#: The kinds the summary's "Media models" line counts. Deliberately NOT
#: scripts/fetch_model.py MEDIA_KINDS, which also holds `agent` because an agent
#: takes the same name-only SEARCH path - a search choice, not a kind of model.
#: tests/test_scheduler_status.py pins the two together, so a media kind added to
#: the fetch cannot silently go uncounted here (rule 12).
MEDIA_SUMMARY_KINDS = frozenset({"image", "video", "speech", "transcription"})


def safe_record(end_record: dict) -> dict:
    """Keep only the host-free fields of an end record. The one enforcement
    point: `summarise_runs` reads what this returns, so a `detail` can never
    reach the issue even if a caller passes a raw record."""
    out = {k: end_record[k] for k in _SAFE_FIELDS if k in end_record}
    for key in ("model", "model_version_id", "display_name"):
        if end_record.get(key):
            out[key] = end_record[key]
    return out
