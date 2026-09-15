"""Three draws each of the two threads that have gone over the 300s cap.

Diagnostic, not a pipeline stage: it writes nothing to the database. It exists
because `devto:4586450` drew 205s, >300s, >300s and 90s on the same text, so a
single draw of a change to the extractor proves nothing about it.

Reports per draw what the fix is supposed to control: elapsed, completion
tokens, the provider's finish reason, and how many claims verified.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import psycopg
import yaml
from dotenv import load_dotenv

load_dotenv()

from collect.config import settings  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from judge.extract.client import OpenRouterClient  # noqa: E402
from judge.extract.runner import ThreadInput, extract  # noqa: E402
from judge.extract.verify import OffsetMapping  # noqa: E402

THREADS = [
    ("thread_context_5d71adaa9a1865e0", "devto:4586450"),
    ("thread_context_48cb5830e7f20b72", "devto:4644090"),
]
DRAWS = 3


class _Recording:
    """Passes calls through and remembers each completion's `finish_reason`.

    The probe needs the provider's own word per draw; `ExtractionRun` does not
    carry it, and adding a field there whose only reader is a diagnostic is the
    shape rule 9 is about. So the wrapper lives here, with the reader.
    """

    def __init__(self, inner):
        self.inner = inner
        self.seen: list[str] = []

    def complete(self, **kwargs):
        completion = self.inner.complete(**kwargs)
        self.seen.append(str(completion.finish_reason))
        return completion


def load(conn, store, tc_id: str) -> ThreadInput:
    row = conn.execute(
        "SELECT flattened_text_ref, offset_map, member_document_ids "
        "FROM thread_context WHERE id = %s",
        (tc_id,),
    ).fetchone()
    flat_ref, omap, members = row
    flattened = store.get_text(flat_ref)
    # The PROSE, not the payload — the same rule `fetch_model.py` follows, and
    # for the same reason: `raw_start`/`raw_end` index the prose the assembler
    # flattened, so verification against anything else lands in the wrong place.
    from collect.assemble import prose

    raw_text_of = {}
    for did in members:
        doc = conn.execute(
            "SELECT source, text_ref FROM document WHERE id = %s", (did,)
        ).fetchone()
        if not doc:
            continue
        payload = store.get_text(doc[1])
        raw_text_of[did] = prose.for_source(doc[0])(payload)
    return ThreadInput(
        thread_context_id=tc_id,
        flattened_text=flattened,
        offset_map=tuple(OffsetMapping(**s) for s in (omap or ())),
        raw_text_of=raw_text_of,
    )


def main() -> int:
    with open("contract/capabilities.yaml", encoding="utf-8") as handle:
        caps = yaml.safe_load(handle)
    keys = [c["key"] for c in caps["capabilities"]]
    client = OpenRouterClient.from_env()
    recorder = _Recording(client)
    print(f"model            {client.model}")
    print(f"max_output_tokens {client.max_output_tokens}")
    print(f"total_timeout     {client.total_timeout_seconds:.0f}s\n")

    store = RawStore(Path(settings().raw_store_path))
    with psycopg.connect(settings().database_url) as conn:
        inputs = {tc: load(conn, store, tc) for tc, _ in THREADS}

    print(f"{'thread':<34}{'draw':>5}{'elapsed':>10}{'out_tok':>9}"
          f"{'finish':>12}{'claims':>8}{'zero_kind':>12}{'trunc':>7}")
    for tc_id, root in THREADS:
        thread = inputs[tc_id]
        print(f"-- {root}  ({len(thread.flattened_text)} chars)")
        for draw in range(1, DRAWS + 1):
            t0 = time.monotonic()
            try:
                recorder.seen.clear()
                run = extract(thread, client=recorder, capability_keys=keys)
            except Exception as exc:  # noqa: BLE001 - a draw that fails is a result
                print(f"{tc_id:<34}{draw:>5}{time.monotonic()-t0:>9.1f}s"
                      f"{'':>9}{'RAISED':>12}  {type(exc).__name__}: "
                      f"{str(exc)[:90]}")
                continue
            print(f"{tc_id:<34}{draw:>5}{time.monotonic()-t0:>9.1f}s"
                  f"{run.output_tokens:>9}{','.join(recorder.seen) or '-':>12}"
                  f"{len(run.verified):>8}{str(run.zero_kind):>12}"
                  f"{str(run.truncated):>7}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
