"""Why candidates failed subject verification. Three causes, and only one is ours.

Reads `model_only_sweep.jsonl` — which records every candidate with its three
group verdicts — and recovers each failure's full text from the search pages the
adapter stored before sieving. Both artifacts existed for other reasons, which is
why this needed no re-run.

THE THREE CAUSES BEHAVE COMPLETELY DIFFERENTLY

    A  SURFACE WRONG        the model IS named and our surface was the wrong
                            spelling. `Fable 5 is a mess for coders` against a
                            query for `Claude Fable 5`. Real evidence, lost to a
                            string. RECOVERABLE BY SEATING the forms propose.py
                            already derives.

    B  LOOSE INDEX MATCH    the text carries a family word or a bare numeral and
                            not the model. `Claude Opus 5 BENCHMARKS!` against a
                            query for Fable 5. THE SIEVE REFUSING IT IS CORRECT -
                            filing it would put a quote on the wrong model's page.
                            Not lost evidence, and no surface work touches it.

    C  NOTHING MATCHED      no model name, no family word, no numeral, in either
                            the title or the body. Reddit matched something the
                            sieve never saw - comments, or a linked image's
                            context. Recoverable by fetching comment trees.

Measured 2026-08-28 over 2,500 candidates: 865 / 810 / 96. Write-up in
`docs/measurements/why-1771-candidates-failed-subject.md`.

    python scripts/why_subject_failed.py [--jsonl model_only_sweep.jsonl]
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import time

from collect.adapters.queries.sieve import matches, normalize
from collect.registry.propose import mechanical_variants, rule_variants

#: Family words. A text carrying only one of these names a FAMILY and not a
#: model, which is why `propose.py` excludes them from every derived surface.
FAMILY = (
    "opus", "sonnet", "haiku", "claude", "gemini",
    "gpt", "qwen", "fable", "luna", "sol", "flash",
)

#: `display_name` per model, as polled. Needed because `rule_variants` seeds from
#: it and this script does not open the database.
DISPLAY = {
    "anthropic/claude-fable-5": "Anthropic: Claude Fable 5",
    "anthropic/claude-haiku-4.5": "Anthropic: Claude Haiku 4.5",
    "anthropic/claude-opus-4.6": "Anthropic: Claude Opus 4.6",
    "anthropic/claude-opus-4.8": "Anthropic: Claude Opus 4.8",
    "anthropic/claude-sonnet-4.6": "Anthropic: Claude Sonnet 4.6",
    "anthropic/claude-sonnet-5": "Anthropic: Claude Sonnet 5",
    "google/gemini-3.7-flash": "Google: Gemini 3.7 Flash",
    "openai/gpt-5.6-luna": "OpenAI: GPT-5.6 Luna",
    "openai/gpt-5.6-sol": "OpenAI: GPT-5.6 Sol",
    "openai/gpt-5.6-sol-pro": "OpenAI: GPT-5.6 Sol Pro",
    "qwen/qwen3.8-27b": "Qwen: Qwen3.8 27B",
}

SURFACE_WRONG = "A surface wrong"
LOOSE_MATCH = "B loose index match"
NOTHING = "C nothing matched"


def stored_posts(hours: int) -> dict[str, dict]:
    """Every candidate the sweep saw, keyed by fullname, from the stored pages."""
    cutoff = time.time() - hours * 3600
    posts: dict[str, dict] = {}
    for path in pathlib.Path("raw_store/raw").rglob("*"):
        if not path.is_file() or path.stat().st_mtime < cutoff:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except ValueError:
            continue
        if not isinstance(payload, dict):
            continue
        data = payload.get("data")
        if not isinstance(data, dict):
            continue
        for entry in data.get("posts") or []:
            if not (isinstance(entry, dict) and isinstance(entry.get("data"), dict)):
                continue
            inner = entry["data"]
            fullname = inner.get("name") or ("t3_" + (inner.get("id") or ""))
            posts[fullname] = inner
    return posts


def version_of(canonical_id: str) -> str | None:
    """The bare version numeral, which is what a loose index match latches onto."""
    found = re.search(r"(\d+\.\d+|\d+)", canonical_id.split("/")[-1])
    return found.group(1) if found else None


def classify(row: dict, text: str, variants: dict[str, list[str]]) -> tuple[str, list[str]]:
    """One failure to a cause, with the evidence that decided it."""
    haystack = normalize(text)
    canonical = row["canonical_id"]

    named = [v for v in variants[canonical] if matches(v, haystack)]
    if named:
        return SURFACE_WRONG, named

    version = version_of(canonical)
    loose = [f for f in FAMILY if matches(f, haystack)]
    if version and matches(version, haystack):
        loose.append(version)
    if loose:
        return LOOSE_MATCH, loose

    return NOTHING, []


def _seated(canonical_ids) -> dict[str, set[str]]:
    """Surfaces already in `model_alias`, so the table can mark them."""
    import psycopg

    from collect.config import settings

    out: dict[str, set[str]] = collections.defaultdict(set)
    with psycopg.connect(settings().database_url, connect_timeout=25) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT mv.canonical_id, a.surface FROM model_version mv "
            "JOIN model_alias a ON a.model_version_id = mv.id "
            "WHERE mv.canonical_id = ANY(%s)",
            (list(canonical_ids),),
        )
        for canonical, surface in cur.fetchall():
            out[canonical].add(surface)
    return out


def _form_table(failures, posts, variants) -> None:
    """Every derived form, with the distinct posts it recovers. For the review.

    A COUNT PER FORM, NOT PER MODEL. The per-model totals say seating is worth
    612 candidates; they do not say that `qwen3.8-27b` carries 119 of them and
    `claudefable5` carries none. The review is deciding form by form, and
    `model_alias` is append-only — a surface seated wrongly is superseded rather
    than removed — so the unit of the table has to be the unit of the decision.
    """
    seated = _seated(DISPLAY)
    print(f"{'model':<28} {'form':<26} {'origin':<12} {'recovers':>8}  verdict")
    print("=" * 104)
    for canonical in DISPLAY:
        for form in variants[canonical]:
            if "/" in form:
                print(f"{canonical:<28} {form:<26} {'canonical-id':<12} "
                      f"{0:>8}  EXCLUDE - nobody types this")
                continue
            recovered = set()
            for row in failures:
                if row["canonical_id"] != canonical:
                    continue
                inner = posts.get(row["external_id"])
                text = row["title"] or ""
                if inner:
                    text = ((inner.get("title") or "") + chr(10)
                            + (inner.get("selftext") or ""))
                if matches(form, normalize(text)):
                    recovered.add(row["external_id"])
            count = len(recovered)
            if form in seated[canonical]:
                origin, verdict = "seated", "already seated"
            elif count >= 20:
                origin, verdict = "derived-new", "SEAT - carries real volume"
            elif count > 0:
                origin, verdict = "derived-new", "seat, low volume"
            else:
                origin, verdict = "derived-new", "judgement: recovers nothing here"
            print(f"{canonical:<28} {form:<26} {origin:<12} {count:>8}  {verdict}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", default="model_only_sweep.jsonl")
    parser.add_argument("--hours", type=int, default=8)
    parser.add_argument("--examples", type=int, default=7)
    parser.add_argument(
        "--forms", action="store_true",
        help="print every derived form with what it recovers, for the seating "
             "review. A form recovering 119 and one recovering 1 are different "
             "decisions and the review has to be able to tell them apart.",
    )
    args = parser.parse_args()

    rows = [
        json.loads(line)
        for line in pathlib.Path(args.jsonl).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    failures = [r for r in rows if not r["subject"]]
    posts = stored_posts(args.hours)
    recovered = sum(1 for r in failures if r["external_id"] in posts)
    print(
        f"candidates {len(rows)}  subject-failed {len(failures)}  "
        f"full text recovered for {recovered}"
    )
    if recovered < len(failures):
        print(
            f"  ⚠ {len(failures) - recovered} failures have no stored page, so the "
            f"split below is over {recovered} and not {len(failures)}"
        )

    variants = {
        canonical: sorted(set(mechanical_variants(canonical, display)
                              + rule_variants(canonical, display)))
        for canonical, display in DISPLAY.items()
    }

    buckets: dict[str, list[tuple[dict, list[str]]]] = collections.defaultdict(list)
    for row in failures:
        inner = posts.get(row["external_id"])
        text = row["title"] or ""
        if inner:
            text = (inner.get("title") or "") + "\n" + (inner.get("selftext") or "")
        cause, evidence = classify(row, text, variants)
        buckets[cause].append((row, evidence))

    total = len(failures)
    print()
    for cause in (SURFACE_WRONG, LOOSE_MATCH, NOTHING):
        found = buckets[cause]
        print(f"{cause:<22} {len(found):5d}  ({100 * len(found) / total:5.1f}% of {total})")

    for cause in (SURFACE_WRONG, LOOSE_MATCH, NOTHING):
        print(f"\n===== {cause} — {len(buckets[cause])} — examples =====")
        for row, evidence in buckets[cause][: args.examples]:
            print(f"  queried {row['surface']!r} for {row['canonical_id']}")
            print(f"    title: {(row['title'] or '')[:96]}")
            if evidence:
                print(f"    text DOES contain: {evidence[:5]}")
            print(f"    {row['url'][:76]}")

    if args.forms:
        _form_table(failures, posts, variants)
        return 0

    print("\n===== bucket A by model — what seating would recover =====")
    by_model = collections.Counter(r["canonical_id"] for r, _ in buckets[SURFACE_WRONG])
    for canonical in DISPLAY:
        print(f"   {canonical:<32} {by_model.get(canonical, 0):5d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
