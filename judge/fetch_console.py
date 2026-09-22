"""Render a fetch run's JSONL records as a readable terminal narrative.

WHY THIS EXISTS. A fetch writes `var/fetch/<run_id>.jsonl` and the web UI
tails it. From a terminal there was nothing: a run started from the admin page
was spawned with `stdout=DEVNULL`, so the console that started the backend saw
silence for forty minutes and then a board that had changed. Reading the run
meant opening the JSONL and decoding it by eye.

⚠ IT RENDERS WHAT THE RECORDS CARRY AND INVENTS NOTHING. Every stage already
  emits its own counts - `documents_inserted`, `sieve_kept`, `quota_remaining`
  and forty more - and those are printed as they arrive. Where a figure is not
  recorded it is absent from the summary rather than derived: a token total or
  a dollar cost computed here would be a number on a page that no stage
  measured (rule 3), and the one place that knows what a call cost is the
  client that made it.

THE FORMAT IS FIXED-WIDTH ON PURPOSE. A stage line is scannable down the
status column, which is the thing a reader is looking for when a run has been
going for half an hour. Detail wraps at the same indent rather than running
off the terminal.

ASCII ONLY. `scripts/` output is asserted encodable by
`test_script_output_is_encodable.py`, because a Windows console in cp1252
raises on an em dash and kills the run that was trying to describe itself.
"""

from __future__ import annotations

import textwrap

#: Total line width. 100 rather than 80: the stage name plus a status plus a
#: timestamp does not fit in 80 without truncating the name, and the name is
#: the part a reader is scanning for.
WIDTH = 100

#: Body indent, and the width text wraps to inside it.
_PAD = "    "
_WRAP = WIDTH - len(_PAD)


def _clock(at: str | None) -> str:
    """`2026-09-21T07:30:44Z` to `07:30:44`. The date is in the header."""
    if not at:
        return "--:--:--"
    text = str(at)
    return text[11:19] if len(text) >= 19 and text[10:11] == "T" else text[:8]


def _fields(record: dict) -> str:
    """Every count the stage reported, as `key=value`, in the order it sent them.

    ⚠ NOT A CHOSEN SUBSET. Which counts matter differs per stage and per
      reader - `quota_remaining` is the whole story on a Reddit arm and noise
      on arXiv - so a renderer that picked would be deciding for them. The
      stage chose what to send; this prints it.
    """
    skip = {"kind", "id", "name", "status", "at", "detail", "seq"}
    parts = []
    for key, value in record.items():
        if key in skip or value is None:
            continue
        if isinstance(value, dict):
            inner = " ".join(f"{k}={v}" for k, v in value.items())
            if inner:
                parts.append(f"{key.replace('_', ' ')}=[{inner}]")
            continue
        if isinstance(value, list):
            value = ",".join(str(v) for v in value)
        parts.append(f"{key.replace('_', ' ')}={value}")
    return " ".join(parts)


def _wrapped(text: str) -> list[str]:
    out: list[str] = []
    for para in str(text).splitlines() or [""]:
        if not para.strip():
            continue
        out.extend(textwrap.wrap(para.strip(), width=_WRAP) or [""])
    return out


def header(*, run_id: str, model_version_id: str, records: str,
           log: str | None = None) -> list[str]:
    """The box a run opens with. Says where its two artifacts are, so a reader
    who wants the raw records or the file copy does not have to guess."""
    lines = [
        "=" * WIDTH,
        f"  FETCH   {model_version_id}",
        f"  run     {run_id}",
        f"  records {records}",
    ]
    if log:
        lines.append(f"  log     {log}")
    lines.append("=" * WIDTH)
    return lines


def stage(record: dict) -> list[str]:
    """One stage transition: a ruled line, then its counts, then its words."""
    sid = str(record.get("id") or "?")
    name = str(record.get("name") or "")
    status = str(record.get("status") or "")
    clock = _clock(record.get("at"))

    left = f"-- {sid}  {name} "
    # ⚠ THE STATUS IS NOT PADDED; THE DASHES ABSORB THE DIFFERENCE. Padding it
    #   to a fixed width put four spaces between the rule and the word on every
    #   `ok` line, so the eye had to find where the dashes stopped instead of
    #   running down a solid column. `ok` simply gets more dashes than
    #   `running`, and both end at the same place.
    right = f" {status}  {clock}"
    rule = "-" * max(3, WIDTH - len(left) - len(right))
    lines = [f"{left}{rule}{right}"]

    counts = _fields(record)
    if counts:
        lines += [_PAD + x for x in _wrapped(counts)]
    if record.get("detail"):
        lines += [_PAD + x for x in _wrapped(record["detail"])]
    return lines


def ending(record: dict, *, model_version_id: str) -> list[str]:
    """The closing box.

    ⚠ IT CARRIES WHAT THE RUN RECORDED AND NOTHING ELSE. A summary of tokens
      sent and dollars spent would be the most useful thing here and the `end`
      record does not hold either - the ledger does, written by the client that
      made each call. Deriving them in a renderer would be a figure with no
      measurement behind it, so the line is absent rather than estimated.
    """
    status = str(record.get("status") or "").upper()
    return [
        "=" * WIDTH,
        f"  RUN {status}   {record.get('detail') or ''}".rstrip(),
        f"  model   {model_version_id}",
        "=" * WIDTH,
    ]


def render(record: dict, *, model_version_id: str) -> list[str]:
    """One JSONL record to the lines it prints, or none.

    `alive` is deliberately silent. It is a heartbeat for the reaper, one a
    minute, and a terminal that printed it would bury the stages it exists to
    make readable in a column of timestamps.
    """
    kind = record.get("kind")
    if kind == "stage":
        return stage(record)
    if kind == "end":
        return ending(record, model_version_id=model_version_id)
    return []


def render_file(text: str, *, model_version_id: str = "", run_id: str = "",
                records: str = "") -> str:
    """A whole `.jsonl` to the narrative, for reading a run after the fact."""
    import json

    out: list[str] = []
    if run_id:
        out += header(run_id=run_id, model_version_id=model_version_id,
                      records=records or f"var/fetch/{run_id}.jsonl")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            # A truncated last line is what a killed run leaves. Say so rather
            # than raising: the point of this function is reading a run that
            # went wrong.
            out.append(f"  (unreadable record: {line[:60]})")
            continue
        rendered = render(record, model_version_id=model_version_id)
        if rendered:
            out.append("")
            out.extend(rendered)
    return "\n".join(out)


if __name__ == "__main__":  # pragma: no cover - a reading tool, not a path
    # RULE 9: `render_file` existed with no caller. It is the answer to "what
    # did that run do", asked after the run is over - which is most of the
    # times it is asked, because a run nobody was watching is exactly the one
    # worth reading.
    #
    #     python -m judge.fetch_console var/fetch/<run_id>.jsonl
    import sys
    from pathlib import Path

    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[0])
        print("usage: python -m judge.fetch_console var/fetch/<run_id>.jsonl")
        raise SystemExit(2)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"no such run log: {path}")
        raise SystemExit(1)

    run_id = path.stem
    text = render_file(
        path.read_text(encoding="utf-8"),
        # The run id is `<model_version_id>-<8 hex>`, so the model is the
        # stem with that suffix removed. Falls back to the whole stem rather
        # than guessing at a shape it does not have.
        model_version_id=run_id.rsplit("-", 1)[0] if "-" in run_id else run_id,
        run_id=run_id,
        records=str(path),
    )
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(text.encode(enc, "replace").decode(enc))
