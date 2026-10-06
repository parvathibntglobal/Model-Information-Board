"""Measure: does an LLM pick better Reddit comments than the code ranking, and at what cost?

THE QUESTION (team suggestion, 2026-10-05): let a model choose which replies
reach the extractor, instead of `collect/assemble/ranking.py`'s weighted score.

⚠ RULE 2 FORBIDS SHIPPING THAT AS ASKED. "No model participates in counting,
weighting, gating, ranking, FILTERING". A model choosing which comments the
extractor sees is a model filtering evidence. This script measures it anyway -
a measurement ships nothing - so the team can decide with numbers whether the
rule should move. It also measures the arm the rule already permits: give the
EXTRACTOR every comment, so the model that proposes claims is the only model,
and code still verifies every quote.

THREE ARMS, SAME THREADS, SAME EXTRACTOR
----------------------------------------
    A  ranking   the production selection: top `max_children` (contract 25) by
                 `rank_children`. Free.
    B  llm       DeepSeek V4 Flash reads the post and every comment and returns
                 up to the same number of comment ids. One extra call.
    C  all       no selection: the extractor reads the post and EVERY comment.

C IS THE REFERENCE, AND THAT IS A PROXY, STATED (rule 7). "Accurate" here means
"keeps the comments that carry evidence", and the evidence-bearing comments are
the ones the extractor produced a VERIFIED quote from when it could see all of
them. No human labels exist (and none are filled in by us). C is drawn TWICE
because the extractor is nondeterministic, and the draw agreement is reported:
a reference that disagrees with itself bounds how precisely A and B can be
ranked against it.

Only threads with MORE comments than the cap separate A from B - at or below
it both select everything - so those are reported apart.

POPULATION: Reddit threads whose post and at least `--min-comments` comments are
readable on THIS machine's raw store. Not a sample of Reddit; a sample of what
we harvested and kept here.

    python scripts/measure_comment_selection.py --max-usd 1.00 --limit 5
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.adapters.reddit import reddit_document_id  # noqa: E402
from collect.assemble.prose import reddit_prose  # noqa: E402
from collect.assemble.ranking import load_lexicon  # noqa: E402
from collect.assemble.reddit import (  # noqa: E402
    StoredComment,
    _score_of,
    _version_aliases,
    assemble_reddit_thread,
)
from collect.assemble.thread import MAX_CHILDREN  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.rawstore_reader import RawStoreReader  # noqa: E402

THREADS = """
    SELECT r.id, r.text_ref, k.external_id, k.text_ref, k.engagement
      FROM document r JOIN document k ON k.thread_root_id = r.id AND k.id <> r.id
     WHERE r.source = 'reddit' AND r.thread_root_id IS NULL AND k.status = 'kept'
     ORDER BY r.id, k.external_id
"""

SELECTOR_SYSTEM = """\
You choose which replies in a discussion thread are worth reading for evidence
about AI models. You do NOT extract anything; you only return reply ids.

A reply is worth reading when it reports something specific about how an AI
model or product behaves: first-hand experience, a measurement, a failure, a
cost, a workaround, a comparison between models, or the condition under which
something happens. Replies that are jokes, reactions, agreement without
content, off-topic, or questions with no information are not worth reading.

Return at most {k} reply ids in the `selected` array, most useful first. Use
only ids that appear in the thread. Fewer is fine when fewer are useful."""

SELECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "selected": {
            "type": "array",
            "items": {"type": "string"},
            "description": "reply ids (for example c12), most useful first",
        }
    },
    "required": ["selected"],
}


def _capability_keys() -> list[str]:
    import yaml

    with open("contract/capabilities.yaml", encoding="utf-8") as handle:
        return [c["key"] for c in yaml.safe_load(handle)["capabilities"]]


def load_threads(conn, reader, min_comments: int) -> list[dict]:
    """Threads with a readable post and >= min_comments readable comments."""
    by_root: dict[str, dict] = {}
    for root, root_ref, ext, ref, engagement in conn.execute(THREADS).fetchall():
        t = by_root.setdefault(root, {"root": root, "root_ref": root_ref, "rows": []})
        t["rows"].append((ext, ref, engagement))
    out = []
    for t in by_root.values():
        got = reader.resolve(t["root_ref"]) if t["root_ref"] else None
        if not got or not got.found:
            continue
        try:
            root_text = reddit_prose(got.require())
        except Exception:  # noqa: BLE001 - an unreadable post is not in the population
            continue
        comments = []
        for ext, ref, engagement in t["rows"]:
            o = reader.resolve(ref) if ref else None
            if not o or not o.found:
                continue
            try:
                body = reddit_prose(o.require())
            except Exception:  # noqa: BLE001
                continue
            if body.strip():
                comments.append(StoredComment(external_id=ext, body=body,
                                              score=_score_of(engagement)))
        if root_text.strip() and len(comments) >= min_comments:
            out.append({"root": t["root"], "root_text": root_text, "comments": comments})
    return out


def _assemble(t, comments, store, aliases, lexicon, cap):
    return assemble_reddit_thread(
        root_document_id=t["root"], root_text=t["root_text"], comments=comments,
        store=store, version_aliases=aliases, lexicon=lexicon, max_children=cap,
    )


def _extract(assembled, t, client, keys) -> dict:
    from judge.extract.runner import ThreadInput, extract
    from judge.extract.verify import OffsetMapping

    raw_text_of = {t["root"]: t["root_text"]}
    raw_text_of.update({reddit_document_id(c.external_id): c.body for c in t["comments"]})
    thread_in = ThreadInput(
        thread_context_id=assembled.id,
        flattened_text=assembled.flattened.text,
        offset_map=tuple(OffsetMapping(**m) for m in assembled.as_row()["offset_map"]),
        raw_text_of={d: raw_text_of[d] for d in assembled.member_document_ids
                     if d in raw_text_of},
    )
    started = time.monotonic()
    run = extract(thread_in, client=client, capability_keys=keys)
    quotes = [{"doc": vq.document_id, "quote": vq.display_text} for _c, vq in run.verified]
    return {
        "members": list(assembled.member_document_ids),
        "verified": quotes,
        "rejected": len(run.rejected),
        "input_tokens": run.input_tokens,
        "cached_input_tokens": run.cached_input_tokens,
        "output_tokens": run.output_tokens,
        "seconds": round(time.monotonic() - started, 1),
        "truncated": bool(getattr(run, "truncated", False)),
    }


def _select_llm(t, client, k) -> dict:
    ids = {f"c{i}": c.external_id for i, c in enumerate(t["comments"], 1)}
    lines = [f"POST:\n{t['root_text']}\n", "REPLIES:"]
    for cid, c in zip(ids, t["comments"], strict=True):
        lines.append(f"[{cid}] {c.body}")
    started = time.monotonic()
    completion = client.complete(system=SELECTOR_SYSTEM.format(k=k), user="\n".join(lines),
                                 tool_schema=SELECTOR_SCHEMA)
    raw = completion.raw_arguments
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "arguments" in parsed and "selected" not in parsed:
            parsed = parsed["arguments"]
            parsed = json.loads(parsed) if isinstance(parsed, str) else parsed
        returned = [str(x) for x in parsed.get("selected", [])]
    except (ValueError, AttributeError):
        returned = []
    # Invalid ids, duplicates and anything past k are COUNTED, not silently
    # dropped - a selector that invents ids is a finding, not a parsing detail.
    chosen, invalid, seen = [], [], set()
    for cid in returned:
        if cid not in ids:
            invalid.append(cid)
        elif cid not in seen:
            seen.add(cid)
            chosen.append(ids[cid])
    return {
        "chosen": chosen[:k],
        "returned": len(returned),
        "invalid_ids": invalid,
        "over_k": max(0, len(chosen) - k),
        "unparsed": raw if not returned else None,
        "input_tokens": completion.input_tokens,
        "cached_input_tokens": completion.cached_input_tokens,
        "output_tokens": completion.output_tokens,
        "seconds": round(time.monotonic() - started, 1),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--max-usd", type=float, required=True,
                    help="stop before the experiment's own spend passes this. No default.")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--min-comments", type=int, default=10)
    ap.add_argument("--reference-draws", type=int, default=2)
    ap.add_argument("--out", default="_comment_selection")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--retries", type=int, default=2)
    args = ap.parse_args(argv)


    from judge.extract.budget import cost_of_tokens, pricing_for
    from judge.extract.client import OpenRouterClient, extractor_model

    model = extractor_model()
    pricing = pricing_for(model)
    if pricing is None:
        raise SystemExit(f"no published price for {model}; refusing to run uncosted")

    def usd(r: dict) -> float:
        return cost_of_tokens(pricing, r["input_tokens"], r["output_tokens"],
                              r.get("cached_input_tokens", 0))

    store = RawStore(Path(settings().raw_store_path))
    reader = RawStoreReader(store)
    with connect() as conn:
        aliases = _version_aliases(conn)
        lexicon = load_lexicon(conn)
        threads = load_threads(conn, reader, args.min_comments)
    threads.sort(key=lambda t: (-len(t["comments"]), t["root"]))
    if args.limit:
        threads = threads[: args.limit]
    k = MAX_CHILDREN
    print(f"population: {len(threads)} thread(s), cap k={k}, extractor {model}, "
          f"max ${args.max_usd:.2f}", flush=True)

    keys = _capability_keys()
    out = Path(args.out) / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    state = {"spent": 0.0, "done": 0, "stopped": 0}
    local = threading.local()

    def client():
        # One client per worker thread; nothing is shared across in-flight calls.
        if not hasattr(local, "c"):
            local.c = OpenRouterClient.from_env()
        return local.c

    def charge(r: dict | None) -> None:
        if r:
            with lock:
                state["spent"] += usd(r)

    def attempt(fn, rec_errors: list, label: str):
        """Retry a transient provider failure. A FAILED CALL IS STILL BILLED and
        its tokens never reach us, so the ledger, not `spent`, is the full total
        - the summary says how many calls failed."""
        for n in range(1, args.retries + 2):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001 - recorded per arm
                rec_errors.append(f"{label} try {n}: {type(exc).__name__}: {exc}"[:300])
                time.sleep(10 * n)
        return None

    def one(i: int, t: dict) -> None:
        with lock:
            if state["spent"] >= args.max_usd:
                state["stopped"] += 1
                return
        n = len(t["comments"])
        rec = {"root": t["root"], "comments": n, "k": k, "errors": []}
        errs = rec["errors"]
        a = _assemble(t, t["comments"], store, aliases, lexicon, k)
        rec["A_selected"] = [m for m in a.member_document_ids if m != t["root"]]
        sel = attempt(lambda: _select_llm(t, client(), k), errs, "B_select")
        charge(sel)
        rec["B_select"] = sel
        chosen = ([c for c in t["comments"] if c.external_id in set(sel["chosen"])]
                  if sel else [])
        rec["B_selected"] = [reddit_document_id(c.external_id) for c in chosen] if sel else None
        rec["A_extract"] = attempt(lambda: _extract(a, t, client(), keys), errs, "A_extract")
        charge(rec["A_extract"])
        rec["B_extract"] = None
        if chosen:
            b = _assemble(t, chosen, store, aliases, lexicon, len(chosen))
            rec["B_extract"] = attempt(lambda: _extract(b, t, client(), keys), errs, "B_extract")
            charge(rec["B_extract"])
        everything = _assemble(t, t["comments"], store, aliases, lexicon, n)
        rec["C_extract"] = []
        for d in range(args.reference_draws):
            r = attempt(lambda: _extract(everything, t, client(), keys), errs, f"C_extract#{d}")
            charge(r)
            rec["C_extract"].append(r)
        (out / f"{t['root'].replace(':', '_')}.json").write_text(
            json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        with lock:
            state["done"] += 1
            print(f"  {state['done']}/{len(threads)} {t['root']} comments={n} "
                  f"errors={len(errs)} spent~${state['spent']:.4f}", flush=True)

    # The ceiling is checked before each thread STARTS, so in-flight threads can
    # pass it by at most `workers` threads' worth - stated, not hidden.
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for f in [pool.submit(one, i, t) for i, t in enumerate(threads, 1)]:
            f.result()
    if state["stopped"]:
        print(f"STOPPED at the ${args.max_usd:.2f} ceiling: {state['stopped']} thread(s) not run")
    print(f"raw results: {out}  (summarise with scripts/summarise_comment_selection.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
