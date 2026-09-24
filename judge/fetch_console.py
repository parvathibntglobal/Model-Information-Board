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
    """The closing box: what the run amounted to.

    ⚠ EVERY LINE IS A NUMBER THE RUN RECORDED. The `end` record carries them
      because `extract_and_curate` puts them there - `threads` is the batch
      that was sent, `results` is what came back, `Budget` counted the tokens.
      Nothing here is computed from anything else, so a line is absent when the
      run did not measure it rather than estimated into existence (rule 3).

      A fetch that never reached E5 - no threads to read, or an error before
      it - prints the box with the model and nothing else, which is the honest
      shape of "it ended and it extracted nothing".

    ⚠ AND THE COST LINE SAYS WHAT IT IS. `spend_ledger`'s dollars are tokens
      times a configured rate, and #381 measured the two rates in this repo
      disagreeing by 2.11x with neither ever checked against an invoice.
      Printing `$0.017892` bare would be a figure that looks measured and is
      not; withholding it would leave a person running a fetch with no spend
      figure at all. So it is shown and labelled.
    """
    status = str(record.get("status") or "").upper()
    lines = [
        "=" * WIDTH,
        f"  RUN {status}   {record.get('detail') or ''}".rstrip(),
        f"  model   {model_version_id}",
    ]
    if record.get("llm"):
        lines.append(f"  llm     {record['llm']}")

    threads = record.get("sent_threads")
    if threads is not None:
        posts, chars = record.get("sent_posts"), record.get("sent_chars")
        sent = f"{threads:,} thread(s)"
        if posts is not None:
            sent += f" - {posts:,} post(s)"
        if chars is not None:
            sent += f", {chars:,} chars"
        lines.append(f"  sent    {sent}")

    tin, tout = record.get("tokens_in"), record.get("tokens_out")
    if tin is not None or tout is not None:
        lines.append(f"  tokens  in {tin or 0:,}  out {tout or 0:,}")
        # A provider that stops reporting usage silently disables the daily
        # cap, and the symptom is a total that looks like good news. Said only
        # when it happened, or it is a caveat about nothing.
        if record.get("unmetered_calls"):
            lines.append(
                f"          {record['unmetered_calls']} call(s) reported NO usage - "
                f"the totals above are short by whatever those cost"
            )

    if record.get("cost_usd") is not None:
        lines.append(
            f"  cost    ${float(record['cost_usd']):.6f}   "
            f"tokens x the configured rate, not an invoice (#381)"
        )

    verified = record.get("claims_verified")
    if verified is not None:
        back = f"{verified:,} claim(s) verified"
        if record.get("claims_stored") is not None:
            back += f", {record['claims_stored']:,} stored"
        if record.get("cells_written"):
            back += f", {record['cells_written']:,} cell(s)"
        lines.append(f"  back    {back}")

    lines.append("=" * WIDTH)
    return lines


def thread(record: dict) -> list[str]:
    """One finished thread: what was sent, what came back, what it cost.

    ⚠ THE ARROWS ARE THE POINT. `->` is the request and `<-` is the answer,
      so a reader scanning a long E5 sees the shape of the exchange without
      reading a word. A run of `<- 0 verified` under a run of `-> 3 post(s)`
      is a batch producing nothing, and it is visible at a glance rather than
      by comparing numbers.

    ⚠ COUNTS AND CAPABILITY KEYS, NEVER THE CLAIM TEXT. A verified claim
      carries a quote from a harvested document, and a terminal line is the
      one place it would appear with no ruling, no attribution and no way to
      decline it. The keys are ours; the quotes are not.
    """
    idx = record.get("index")
    total = record.get("total")
    where = f"[{idx}/{total}] " if idx and total else ""
    posts = record.get("posts")
    head = (f"  -> {where}{record.get('thread_context_id', '?')}"
            f"{f'  {posts} post(s)' if posts is not None else ''}")

    got = (
        f"     <- {record.get('verified', 0)} verified, "
        f"{record.get('rejected', 0)} rejected, "
        f"{record.get('unsalvaged', 0)} unsalvaged, "
        f"{record.get('unclassified', 0)} unclassified, "
        f"{record.get('proposed', 0)} proposed"
    )
    lines = [head, got]

    keys = record.get("keys") or {}
    if keys:
        lines.append("        " + ", ".join(
            f"{k} x{n}" for k, n in sorted(keys.items(), key=lambda kv: (-kv[1], kv[0]))))
    elif record.get("no_claim_reason"):
        # WHY NOTHING CAME BACK, which is the line that separates a thread
        # that said nothing from one the extractor could not read.
        reason = " ".join(str(record["no_claim_reason"]).split())
        lines.append("        no claim: " + reason[:_WRAP - 18])

    # ⚠ WHY THE LOST CLAIMS WERE LOST, IN SHAPES (#409). `97 unsalvaged` on the
    #   line above is a count, and a thread that lost 40 to ONE repeated error
    #   and one that lost 40 to FORTY different ones print the same number and
    #   want opposite fixes. Shown only when something was lost - a column of
    #   blanks on the healthy threads would bury the two that matter.
    shapes = record.get("unsalvaged_by_error") or {}
    for shape, n in sorted(shapes.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"        x{n:<3} {' '.join(str(shape).split())[:_WRAP - 14]}")
    if record.get("unsalvaged_other"):
        # The cap saying it bound. A truncated list with nothing marking the
        # truncation reads as a complete one.
        lines.append(f"        +{record['unsalvaged_other']} more in other shapes")

    cost = []
    if record.get("tokens_in") is not None or record.get("tokens_out") is not None:
        cost.append(f"in {record.get('tokens_in') or 0:,} / "
                    f"out {record.get('tokens_out') or 0:,} tok")
    if record.get("usd") is not None:
        cost.append(f"${float(record['usd']):.6f}")
    # Said only when it happened: a retry and a truncation are both events, and
    # a column of "retries 0" is noise that hides the one that says 1.
    if record.get("schema_retries"):
        cost.append(f"retries {record['schema_retries']}")
    if record.get("truncated"):
        cost.append("TRUNCATED at the token ceiling")
    # WHICH UPSTREAM SERVED EACH CALL, in order: "via DeepInfra", or
    # "via NextBit, DeepInfra" when a schema retry went elsewhere. A call whose
    # stream named none prints as "not reported", never as a blank (rule 6).
    if record.get("upstreams"):
        cost.append("via " + ", ".join(u or "not reported" for u in record["upstreams"]))
    # BILLED, AS OPENROUTER REPORTED IT, beside the `$` above - which is tokens
    # times a constant and says so in the run box (#381). Printed only when
    # every call reported a figure: a partial sum would read as the total.
    #
    # ⚠ `all(...)` CAN ONLY SEE CALLS THAT WERE APPENDED. An attempt that raised
    #   `ExtractorUnavailable` and was retried (#399) never became a Completion,
    #   so it is absent from the list rather than None in it - and the sum would
    #   pass the guard while missing it. `failed_attempts` is the count the list
    #   cannot hold, and the line says so rather than calling a partial sum the
    #   bill. What those attempts cost is unknown: a failed call's charge is not
    #   documented (#381), and it writes no ledger row (#393).
    billed = record.get("reported_costs") or []
    failed = record.get("failed_attempts") or 0
    if billed and all(b is not None for b in billed):
        figure = f"billed ${sum(billed):.6f}"
        if failed:
            figure += f" + {failed} failed attempt(s) not reported"
        cost.append(figure)
    elif billed:
        cost.append("billed: not reported for every call")
    if cost:
        lines.append("        " + "   ".join(cost))
    return lines


def render(record: dict, *, model_version_id: str) -> list[str]:
    """One JSONL record to the lines it prints, or none.

    `alive` is deliberately silent. It is a heartbeat for the reaper, one a
    minute, and a terminal that printed it would bury the stages it exists to
    make readable in a column of timestamps.
    """
    kind = record.get("kind")
    if kind == "stage":
        return stage(record)
    if kind == "thread":
        return thread(record)
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
