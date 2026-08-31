"""Where the unread threads would land: models that already have cells, or
models that have none. Read-only; writes nothing to the database.

THE QUESTION. 197 claims across 94 cells is about two voices per cell. Spending
~$2.14 to extract the rest buys either MORE VOICES on cells that exist (which
moves cells toward publishing) or MORE CELLS at two voices each (which does
not). Nobody should learn which by running the extraction.

WHAT CAN BE KNOWN NOW, AND WHAT CANNOT. A claim is a (model, capability) pair.
Capability is assigned by the extractor and is unknowable in advance. THE MODEL
HALF IS NOT: it is `collect/triage/entity.resolve` over the flattened text, the
same deterministic surface match the entity gate already runs, with no model
involved. So this reports the model half and says so.

THE BOUND IS ONE-DIRECTIONAL AND THAT IS THE USEFUL PART.

    resolves to NO model with a cell   ->  CANNOT add a voice to an existing
                                           cell. A hard floor on new cells.
    resolves to a model WITH cells     ->  MAY add a voice, or may open a new
                                           capability on that model. An upper
                                           bound, never a forecast.

Reported as two bounds rather than one estimate: a midpoint would be a
synthesised number (rule 3).

POPULATION. Thread contexts with no `thread_extraction` row AND a flattened
text readable from the local raw store. Both halves are stated in the output;
the second is a property of THIS MACHINE, not of the corpus.

    python scripts/unread_thread_distribution.py [--json OUT]
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib

from collect.db import connect
from collect.rawstore import RawStore
from collect.triage.entity import (
    build_population,
    normalize,
    normalize_with_boundaries,
    resolve,
)

NO_SURFACE = "no-surface-matched"
NO_OWNER = "surface-matched-no-known-owner"
HAS_CELLS = "names-a-model-that-has-cells"
NO_CELLS = "names-only-models-with-no-cells"


def independently_named(text: str, surfaces: tuple[str, ...]) -> tuple[str, ...]:
    """The matched surfaces that occur somewhere a LONGER match does not cover.

    WHY THIS IS NEEDED AND WHY IT IS NOT A FIX TO `resolve`. `resolve` answers
    "which surfaces appear in this text", and for the entity GATE - does this
    document name any model at all - that is the right question and this
    subsetting would be wrong. Here the question is different and narrower:
    WHICH MODELS does this thread name, so a thread can be attributed to one.

    Those come apart because the boundary mask treats `.` as a word end, so
    `opus 4` matches inside `opus 4.6` with both boundaries satisfied:

        'opus 4.8 is great' -> owners {claude-opus-4, claude-opus-4.8}

    `claude-opus-4` is a real registry model, so this is not a bad surface or a
    bad owner - it is one text span attributed to two models. Counting it twice
    makes a thread name more models than the writer did, which inflates any
    figure of the form "does this thread name a model that has cells" toward
    yes. Rule 7: a real value answering a question it was not asked.

    So a surface survives only where it has an occurrence NOT contained in an
    occurrence of a longer matched surface. A document that says both `opus 4`
    and `opus 4.6`, in different places, keeps both - the containment is tested
    per occurrence, not per surface.

    Pure counting over a boundary mask. No model participates.
    """
    haystack, starts, ends = normalize_with_boundaries(text)
    if not haystack:
        return ()

    spans: dict[str, list[tuple[int, int]]] = {}
    for surface in surfaces:
        needle = normalize(surface)
        if not needle:
            continue
        found: list[tuple[int, int]] = []
        at = haystack.find(needle)
        while at >= 0:
            end = at + len(needle)
            if starts[at] and ends[end - 1]:
                found.append((at, end))
            at = haystack.find(needle, at + 1)
        if found:
            spans[surface] = found

    kept: list[str] = []
    for surface, occurrences in spans.items():
        width = len(normalize(surface))
        longer = [
            span
            for other, other_spans in spans.items()
            if len(normalize(other)) > width
            for span in other_spans
        ]
        if any(
            not any(lo <= start and end <= hi for lo, hi in longer)
            for start, end in occurrences
        ):
            kept.append(surface)
    return tuple(sorted(kept, key=lambda s: (-len(normalize(s)), s)))


def _population():
    """Same surfaces the entity gate uses: registry-derived plus seed-declared."""
    from collect.registry.seed import seed_models

    conn = connect()
    try:
        models = conn.execute(
            "SELECT canonical_id, display_name FROM model_version ORDER BY canonical_id"
        ).fetchall()
    finally:
        conn.close()
    declared: list[str] = []
    for model in seed_models():
        declared.append(model.aliases.surface)
        declared.extend(model.aliases.variants)
    return build_population([(r[0], r[1]) for r in models], declared)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--json", default="docs/measurements/unread-thread-distribution.json"
    )
    args = ap.parse_args()

    population = _population()
    store = RawStore()
    conn = connect()
    try:
        threads = conn.execute(
            "SELECT tc.id, tc.flattened_text_ref, "
            "       (te.thread_context_id IS NOT NULL) AS extracted "
            "FROM thread_context tc "
            "LEFT JOIN thread_extraction te ON te.thread_context_id = tc.id"
        ).fetchall()
        cells = conn.execute(
            "SELECT mv.canonical_id, count(*) "
            "FROM cell c JOIN model_version mv ON mv.id = c.model_version_id "
            "GROUP BY 1"
        ).fetchall()
        claim_pairs = conn.execute(
            "SELECT DISTINCT mv.canonical_id, c.capability_key "
            "FROM claim c JOIN model_version mv ON mv.id = c.model_version_id"
        ).fetchall()
        total_docs = conn.execute("SELECT count(*) FROM document").fetchone()[0]
    finally:
        conn.close()

    celled = {row[0] for row in cells}
    cells_by_model = {row[0]: row[1] for row in cells}
    pairs_with_voices = {(a, b) for a, b in claim_pairs}

    unreadable = 0
    buckets: collections.Counter = collections.Counter()
    strict_buckets: collections.Counter = collections.Counter()
    unread_model_hits: collections.Counter = collections.Counter()
    strict_model_hits: collections.Counter = collections.Counter()
    extracted_model_hits: collections.Counter = collections.Counter()
    strict_extracted_hits: collections.Counter = collections.Counter()
    models_per_thread: collections.Counter = collections.Counter()
    strict_models_per_thread: collections.Counter = collections.Counter()

    def _owners(surfaces) -> set[str]:
        out: set[str] = set()
        for surface in surfaces:
            out.update(population.owners.get(surface, ()))
        return out

    def _bucket(surfaces, owners) -> str:
        if not surfaces:
            return NO_SURFACE
        if not owners:
            return NO_OWNER
        return HAS_CELLS if owners & celled else NO_CELLS

    for _thread_id, ref, extracted in threads:
        try:
            text = store.get_text(ref)
        except Exception:
            unreadable += 1
            continue
        surfaces = resolve(text, population)
        strict = independently_named(text, surfaces)
        owners = _owners(surfaces)
        strict_owner_set = _owners(strict)

        if extracted:
            for owner in owners:
                extracted_model_hits[owner] += 1
            for owner in strict_owner_set:
                strict_extracted_hits[owner] += 1
            continue

        for owner in owners:
            unread_model_hits[owner] += 1
        for owner in strict_owner_set:
            strict_model_hits[owner] += 1
        models_per_thread[len(owners)] += 1
        strict_models_per_thread[len(strict_owner_set)] += 1
        buckets[_bucket(surfaces, owners)] += 1
        strict_buckets[_bucket(strict, strict_owner_set)] += 1

    unread_total = sum(buckets.values())
    if not unread_total:
        print("NO UNREAD THREADS READABLE HERE. An empty result is not a zero.")
        return 1

    print("=" * 78)
    print("WHERE THE UNREAD THREADS WOULD LAND - THE MODEL HALF ONLY")
    print("=" * 78)
    print(f"population: {unread_total} thread contexts with NO thread_extraction row")
    print("            AND a flattened text readable from this machine's raw store.")
    print(f"            {unreadable} skipped as unreadable here - a property of this")
    print("            checkout, not of the corpus.")
    print(
        f"            surfaces: {len(population.surfaces)} over "
        f"{population.model_count} models  [{population.fingerprint}]"
    )
    print(f"            corpus at time of run: {total_docs} documents")
    print()
    print(f"  cells today: {sum(cells_by_model.values())} over {len(celled)} models")
    print(f"  (model, capability) pairs with a claim: {len(pairs_with_voices)}")
    print()
    print("  ATTRIBUTION A - every matched surface (what `resolve` returns).")
    print("  Over-counts: `opus 4` matches inside `opus 4.6`, so one span is")
    print("  attributed to two models. Shown because it is the figure a caller")
    print("  reusing the entity gate directly would get.")
    for name, n in buckets.most_common():
        print(f"    {name:36s} {n:5d}   {n / unread_total:6.1%}")
    print()
    print("  ATTRIBUTION B - surfaces occurring where no LONGER match covers")
    print("  them. This is the one to quote.")
    for name, n in strict_buckets.most_common():
        print(f"    {name:36s} {n:5d}   {n / unread_total:6.1%}")
    print()

    reachable = strict_buckets[HAS_CELLS]
    unreachable = unread_total - reachable
    print("  On attribution B:")
    print("  UPPER BOUND on threads that could add a voice to an existing cell:")
    print(f"    {reachable} / {unread_total} = {reachable / unread_total:.1%}")
    print("  HARD FLOOR on threads that cannot - they name no model with a cell:")
    print(f"    {unreachable} / {unread_total} = {unreachable / unread_total:.1%}")
    print()
    print("  models named per unread thread (attribution B), and why it matters:")
    print("  a thread naming many models makes 'names a model with cells' near")
    print("  certain regardless of the corpus, which would make the bound empty.")
    for n_models, count in sorted(strict_models_per_thread.items()):
        loose = models_per_thread.get(n_models, 0)
        print(f"    {n_models:2d} models  {count:5d}   (attribution A: {loose})")
    print()
    print("  unread threads by model, top 25, attribution B. A thread naming two")
    print("  models is counted under both, so this column sums above the")
    print("  population. Attribution A in brackets:")
    for model, n in strict_model_hits.most_common(25):
        mark = f"{cells_by_model.get(model, 0)} cells" if model in celled else "NO CELLS"
        print(f"    {model:38s} {n:5d} [{unread_model_hits.get(model, 0):5d}]  {mark}")
    print()
    silent = sorted(m for m in celled if m not in strict_model_hits)
    print(f"  models with cells that NO unread thread names: {len(silent)} of {len(celled)}")
    for model in silent:
        print(f"    {model:38s}         {cells_by_model[model]} cells")

    out = {
        "population": unread_total,
        "population_note": (
            "thread_context rows with no thread_extraction row and a flattened "
            "text readable from the local raw store"
        ),
        "unreadable_here": unreadable,
        "surface_population_fingerprint": population.fingerprint,
        "surface_count": len(population.surfaces),
        "models_in_population": population.model_count,
        "documents_in_corpus_at_run": total_docs,
        "cells_today": sum(cells_by_model.values()),
        "models_with_cells": len(celled),
        "pairs_with_claims": len(pairs_with_voices),
        "attribution_a_every_matched_surface": dict(buckets),
        "attribution_b_independently_named": dict(strict_buckets),
        "attribution_quoted": "b",
        "upper_bound_could_add_voice": reachable,
        "hard_floor_cannot_add_voice": unreachable,
        "models_per_thread_b": dict(sorted(strict_models_per_thread.items())),
        "models_per_thread_a": dict(sorted(models_per_thread.items())),
        "unread_threads_by_model_b": dict(strict_model_hits.most_common()),
        "unread_threads_by_model_a": dict(unread_model_hits.most_common()),
        "extracted_threads_by_model_b": dict(strict_extracted_hits.most_common()),
        "extracted_threads_by_model_a": dict(extracted_model_hits.most_common()),
        "cells_by_model": cells_by_model,
        "celled_models_no_unread_thread_names": silent,
    }
    path = pathlib.Path(args.json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwritten to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
