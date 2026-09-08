"""What the triage gates would do to the four new platforms. A measurement, small n.

    py -3 scripts/measure_gate_shape.py

WHY THIS EXISTS
---------------
`collect/triage/gates.py` sets `MIN_TOKENS = 15` and the `too-short-no-artifact`
gate is the one gate whose behaviour is a function of the PLATFORM's length
distribution rather than of the document. It was calibrated on Reddit: over the
1,297-post substitution corpus it dropped **1 document**. A floor that drops 1
in 1,297 on one platform can empty another, and nothing had measured the length
distribution of a Hacker News comment, an arXiv abstract, a dev.to article or a
Hugging Face discussion comment.

So this measures it, before anything is promoted (rule 8: an unmeasured check
ships as a weight, not a gate - and here the check already IS a gate, which
makes measuring it the overdue half).

⚠  THE DENOMINATORS ARE SMALL AND THEY ARE NOT THE SAME POPULATION.
   Each platform's figure is over the candidates ONE query retrieved, and each
   query is different because the platforms are searched differently. These are
   length distributions of retrieved candidates, NOT of the platform, and not of
   any model's corpus. A pooled figure across the four would mix four
   populations, so none is printed.

WHAT IS AND IS NOT RUN
----------------------
Three gates are computed - `too-short-no-artifact`, `pure-link-post` and the
`has_artifact` component behind the first. `no-resolvable-entity` needs the
registry surface population and `out-of-window` needs `in_window`, so both are
reported as NOT COMPUTED HERE rather than as passes. `wrong-language` and
`known-bot` are UNAVAILABLE for every platform for the same reason they are on
the existing corpus: no detector, no list.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collect.http import build_client  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.triage.gates import MIN_TOKENS, has_artifact  # noqa: E402

_TOKEN = re.compile(r"\S+")


def distribution(texts: list[str], label: str, population: str) -> dict:
    """Token counts and what the length gate would do. With its denominator."""
    counts = sorted(len(_TOKEN.findall(t)) for t in texts)
    if not counts:
        return {"platform": label, "population": population, "n": 0}
    artifacts = sum(1 for t in texts if has_artifact(t))
    # The gate's own conjunction, not length alone: under the floor AND no
    # artifact. `TypeError: 'NoneType'` is eleven tokens and is the highest
    # signal thing in the corpus, which is why the AND is there.
    dropped = sum(
        1
        for t in texts
        if len(_TOKEN.findall(t)) < MIN_TOKENS and not has_artifact(t)
    )
    under_floor = sum(1 for c in counts if c < MIN_TOKENS)
    return {
        "platform": label,
        "population": population,
        "n": len(counts),
        "tokens_min": counts[0],
        "tokens_p25": counts[len(counts) // 4],
        "tokens_median": int(statistics.median(counts)),
        "tokens_p75": counts[(3 * len(counts)) // 4],
        "tokens_max": counts[-1],
        "under_min_tokens": under_floor,
        "under_min_tokens_pct": round(100 * under_floor / len(counts), 1),
        "carries_an_artifact": artifacts,
        "carries_an_artifact_pct": round(100 * artifacts / len(counts), 1),
        "too_short_would_drop": dropped,
        "too_short_would_drop_pct": round(100 * dropped / len(counts), 1),
        # `is_self_post` is None on all four platforms: none of them has a
        # link-post flag. So the gate is NOT_APPLICABLE per document, which is
        # PERMANENT and is not a build gap.
        "pure_link_post": "not-applicable (no link-post flag on this platform)",
        "wrong_language": "unavailable (no detector installed, none declared)",
        "known_bot": "unavailable (no bot list in contract/)",
        "no_resolvable_entity": "not computed here (needs the surface population)",
        "out_of_window": "not computed here (needs in_window)",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="Fable 5.1")
    parser.add_argument(
        "--out", default="docs/measurements/gate-shape-new-platforms-2026-09-07.json"
    )
    args = parser.parse_args(argv)

    store = RawStore()
    rows = []

    with build_client(timeout=45.0, follow_redirects=True) as client:
        # ── Hacker News: 50 comment bodies for the model surface ──────────
        from collect.adapters.hackernews import HackerNewsHarvester

        hn = HackerNewsHarvester(client=client, store=store)
        hn_run = hn.search(args.query)
        rows.append(
            distribution(
                [c.comment_text or "" for c in hn_run.comments],
                "hackernews",
                f"{len(hn_run.comments)} comment bodies retrieved by "
                f"tags=comment query={args.query!r}, relevance-ranked, one page. "
                f"nbHits={hn_run.total_hits} is a prefix-matched retrieval total.",
            )
        )

        # ── dev.to: 30 search BLURBS, and 2 full bodies for contrast ─────
        from collect.adapters.devto import DevtoHarvester

        dev = DevtoHarvester(client=client, store=store)
        dev_run = dev.harvest(args.query, max_fetch=2)
        rows.append(
            distribution(
                [h.sieve_text for h in dev_run.hits],
                "devto (search blurbs)",
                f"{len(dev_run.hits)} title+description+tags blurbs from one "
                f"/articles/search page for {args.query!r}. THE PRE-FETCH SIEVE "
                "READS THIS, and it is not the article.",
            )
        )
        rows.append(
            distribution(
                [a.body or "" for a in dev_run.stored],
                "devto (fetched bodies)",
                f"{len(dev_run.stored)} body_markdown values, the first "
                "candidates fetched. THE DOCUMENT the gates would see.",
            )
        )

        # ── arXiv: abstracts. A BROADER QUERY, because the model surface
        #    returns 1 and a length distribution over n=1 is not one. ──────
        from collect.adapters.arxiv import ArxivHarvester

        arx = ArxivHarvester(client=client, store=store, page_size=50)
        arx_run = arx.search('abs:"large language model"')
        rows.append(
            distribution(
                [p.sieve_text for p in arx_run.papers],
                "arxiv",
                f"{len(arx_run.papers)} title+abstract pairs from one page of "
                'abs:"large language model", newest first. A BROADER QUERY THAN '
                f"{args.query!r} on purpose: that surface returns 1 paper, and a "
                "length distribution over n=1 is not a distribution. Length is a "
                "property of the platform's format here, which is what makes the "
                "substitution defensible for THIS figure and for no other.",
            )
        )

    # ── Hugging Face: from the smoke run's control, already stored ────────
    control = ROOT / "docs/measurements/new-adapter-smoke-hf-control-2026-09-07.json"
    hf_note = (
        "NOT MEASURED HERE. The Hub has no full-text search over discussions, so "
        "a comment population needs a repo walk; the 2026-09-07 control run "
        "(DeepSeek-R1) walked 2 repos and stored 4 comments, which is too few for "
        "a distribution. Reasoned in docs/triage-assessment-2026-09-07.md instead."
    )
    rows.append(
        {
            "platform": "huggingface",
            "population": hf_note,
            "n": 0,
            "control_run_present": control.exists(),
        }
    )

    payload = {
        "measured_at": datetime.now(UTC).isoformat(),
        "min_tokens": MIN_TOKENS,
        "query": args.query,
        "caveat": (
            "Each row is a different population retrieved a different way. They "
            "are not comparable to each other as platform properties, and none "
            "is comparable to the 1,297-post Reddit corpus the floor was "
            "calibrated on - that corpus was retrieved by model-name queries and "
            "is pre-filtered for exactly what the entity gate tests."
        ),
        "rows": rows,
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"MIN_TOKENS = {MIN_TOKENS}\n")
    head = (
        f"{'platform':<24}{'n':>5}{'min':>6}{'med':>6}{'max':>7}"
        f"{'<floor':>8}{'artifact':>10}{'drop':>7}"
    )
    print(head)
    print("-" * len(head))
    for row in rows:
        if not row.get("n"):
            print(f"{row['platform']:<24}    0   (not measured — see the JSON)")
            continue
        print(
            f"{row['platform']:<24}{row['n']:>5}{row['tokens_min']:>6}"
            f"{row['tokens_median']:>6}{row['tokens_max']:>7}"
            f"{row['under_min_tokens_pct']:>7}%{row['carries_an_artifact_pct']:>9}%"
            f"{row['too_short_would_drop_pct']:>6}%"
        )
    print(f"\nwritten: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
