"""Summarise a `measure_comment_selection.py` run. Reads its JSON, calls nothing.

Every figure printed carries its denominator (rule 7): threads measured, threads
whose reference found any evidence-bearing comment, and comments counted.

    python scripts/summarise_comment_selection.py _comment_selection/<stamp>
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _docs(run: dict | None, root: str) -> set[str]:
    if not run:
        return set()
    return {q["doc"] for q in run["verified"] if q["doc"] != root}


def _comment_quotes(run: dict | None, root: str) -> int:
    return sum(1 for q in run["verified"] if q["doc"] != root) if run else 0


def main(argv: list[str]) -> int:
    from judge.extract.budget import cost_of_tokens, pricing_for
    from judge.extract.client import extractor_model

    folder = Path(argv[0])
    model = extractor_model()
    pricing = pricing_for(model)

    def usd(r):
        return cost_of_tokens(pricing, r["input_tokens"], r["output_tokens"],
                              r.get("cached_input_tokens", 0)) if r else None

    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]
    complete = [r for r in recs if r.get("A_extract") and r.get("B_extract")
                and r.get("C_extract") and all(r["C_extract"])]
    lines: list[str] = []
    say = lines.append

    say("# Comment selection: code ranking vs LLM selector vs read-everything")
    say("")
    say(f"Run: `{folder}`. Extractor and selector: `{model}`.")
    say(f"Threads written: {len(recs)}; complete on all arms: {len(complete)}. "
        f"Population: Reddit threads with more than k readable comments on this "
        f"machine - not a sample of Reddit.")
    errs = sum(len(r.get("errors", [])) for r in recs)
    say(f"Failed calls (retried or lost; billed but not in the cost figures below): {errs}.")
    say("")

    hits = {"A": 0, "B": 0}
    weighted = {"A": 0.0, "B": 0.0}
    ref_total = 0
    ref_quotes = 0.0
    per_thread = {"A": [], "B": []}
    no_evidence = 0
    agreement = []
    overlap = []
    e2e = {"A": [], "B": [], "C": []}
    cost = {"select": [], "A": [], "B": [], "C": []}
    secs = {"select": [], "A": [], "B": [], "C": []}
    invalid = over_k = unparsed = 0
    b_sizes = []

    for r in complete:
        root = r["root"]
        draws = [_docs(c, root) for c in r["C_extract"]]
        ref = set().union(*draws)
        if len(draws) >= 2 and (draws[0] | draws[1]):
            agreement.append(len(draws[0] & draws[1]) / len(draws[0] | draws[1]))
        a, b = set(r["A_selected"]), set(r["B_selected"] or [])
        overlap.append(len(a & b) / max(1, len(a)))
        b_sizes.append(len(b))
        sel = r["B_select"]
        invalid += len(sel["invalid_ids"])
        over_k += sel["over_k"]
        unparsed += 1 if sel["unparsed"] else 0
        for arm in ("A", "B"):
            e2e[arm].append(_comment_quotes(r[f"{arm}_extract"], root))
        e2e["C"].append(statistics.mean(_comment_quotes(c, root) for c in r["C_extract"]))
        cost["select"].append(usd(sel))
        secs["select"].append(sel["seconds"])
        for arm in ("A", "B"):
            cost[arm].append(usd(r[f"{arm}_extract"]))
            secs[arm].append(r[f"{arm}_extract"]["seconds"])
        cost["C"].append(statistics.mean(usd(c) for c in r["C_extract"]))
        secs["C"].append(statistics.mean(c["seconds"] for c in r["C_extract"]))
        if not ref:
            no_evidence += 1
            continue
        ref_total += len(ref)
        # Quote-weighted: a comment that carried three quotes counts three.
        quotes_by_doc: dict[str, float] = {}
        for c in r["C_extract"]:
            for q in c["verified"]:
                if q["doc"] != root:
                    quotes_by_doc[q["doc"]] = quotes_by_doc.get(q["doc"], 0) + 1 / len(draws)
        ref_quotes += sum(quotes_by_doc.values())
        for arm, chosen in (("A", a), ("B", b)):
            hits[arm] += len(chosen & ref)
            weighted[arm] += sum(v for d, v in quotes_by_doc.items() if d in chosen)
            per_thread[arm].append(len(chosen & ref) / len(ref))

    n_ref = len(complete) - no_evidence
    say("## Accuracy - how much of the evidence each selection keeps")
    say("")
    say(f"Reference = comments the extractor produced a VERIFIED quote from when it read "
        f"every comment (union of {len(complete[0]['C_extract']) if complete else 0} draws). "
        f"{n_ref} of {len(complete)} complete threads had at least one such comment; "
        f"{no_evidence} had none and are excluded from recall.")
    say("")
    if ref_total:
        say("| | Code ranking (A) | LLM selector (B) |")
        say("|---|---|---|")
        say(f"| Evidence-bearing comments kept, pooled | {hits['A']} of {ref_total} "
            f"({100 * hits['A'] / ref_total:.1f}%) | {hits['B']} of {ref_total} "
            f"({100 * hits['B'] / ref_total:.1f}%) |")
        say(f"| Same, mean per thread | {100 * statistics.mean(per_thread['A']):.1f}% | "
            f"{100 * statistics.mean(per_thread['B']):.1f}% |")
        say(f"| Reference quotes whose comment was kept | {weighted['A']:.1f} of {ref_quotes:.1f} "
            f"({100 * weighted['A'] / ref_quotes:.1f}%) | {weighted['B']:.1f} of {ref_quotes:.1f} "
            f"({100 * weighted['B'] / ref_quotes:.1f}%) |")
        wins = sum(1 for x, y in zip(per_thread["A"], per_thread["B"], strict=True) if y > x)
        losses = sum(1 for x, y in zip(per_thread["A"], per_thread["B"], strict=True) if y < x)
        say(f"| Threads where B kept more / fewer than A | {losses} fewer | {wins} more "
            f"(of {n_ref}; rest tied) |")
    say("")
    if agreement:
        say(f"Reference self-agreement (Jaccard of the evidence-bearing comment sets of two "
            f"draws on identical input): median {statistics.median(agreement):.2f} over "
            f"{len(agreement)} threads. Differences between A and B smaller than the "
            f"reference's disagreement with itself are not established by this run.")
        say("")
    say(f"Selections overlap: A and B shared a median {100 * statistics.median(overlap):.0f}% "
        f"of A's comments. B selected a median {statistics.median(b_sizes) if b_sizes else 0} "
        f"comments (cap k={complete[0]['k'] if complete else '?'}). Selector output: "
        f"{invalid} invalid id(s), {over_k} over the cap, {unparsed} unparsed answer(s).")
    say("")
    say("## End to end - verified quotes from comments, per thread")
    say("")
    say("| | median | total | over threads |")
    say("|---|---|---|---|")
    for arm, label in (("A", "Code ranking, top k"), ("B", "LLM-selected"),
                       ("C", "Every comment (mean of draws)")):
        if e2e[arm]:
            say(f"| {label} | {statistics.median(e2e[arm]):.1f} | {sum(e2e[arm]):.1f} | "
                f"{len(e2e[arm])} |")
    say("")
    say("## Cost - list price x measured tokens, per thread")
    say("")
    say("| step | median USD | total USD | median seconds |")
    say("|---|---|---|---|")
    for key, label in (("select", "LLM selector call (B only)"), ("A", "Extract A"),
                       ("B", "Extract B"), ("C", "Extract C (one draw)")):
        vals = [v for v in cost[key] if v is not None]
        if vals:
            say(f"| {label} | {statistics.median(vals):.5f} | {sum(vals):.4f} | "
                f"{statistics.median(secs[key]):.0f} |")
    if cost["A"] and cost["select"]:
        a_tot = sum(cost["A"])
        b_tot = sum(cost["B"]) + sum(cost["select"])
        say("")
        say(f"Per thread, A costs ${a_tot / len(cost['A']):.5f}; B costs "
            f"${b_tot / len(cost['B']):.5f} including its selector call "
            f"({100 * (b_tot - a_tot) / a_tot:+.0f}% vs A); C costs "
            f"${sum(cost['C']) / len(cost['C']):.5f} "
            f"({100 * (sum(cost['C']) - a_tot) / a_tot:+.0f}% vs A).")
    text = "\n".join(lines)
    print(text)
    (folder / "SUMMARY.md").write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
