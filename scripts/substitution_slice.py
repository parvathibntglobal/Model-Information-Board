"""Re-sieve substitution against the new term shape. Two stages, on purpose.

    py -3 scripts/substitution_slice.py retrieve --out ./_substitution_slice
    py -3 scripts/substitution_slice.py sieve    --out ./_substitution_slice

WHY THIS FILE EXISTS AT ALL. The 2026-08-17 run
(`docs/measurements/substitution-slice.md`) was driven by a script nobody
committed, and its corpus lived in a scratch database that has since been reset.
So "re-sieve the corpus" was not possible: the text was gone, and re-sieving is
only free when the text is local. This run separates RETRIEVE from SIEVE and
writes a sidecar beside the store, so the next shape change costs zero requests.

WHAT IS BEING COMPARED, AND WHY IT IS A 2x2 RATHER THAN A BEFORE AND AFTER
--------------------------------------------------------------------------
Two things changed at once in `contract/queries.yaml`:

    SUBJECT   `["{alias}"]` -> `["{alias}", "{alias_b}"]`. All-of, so both
              models must now appear. STRICTER.
    TOPIC     directional phrases carrying `{alias_b}` -> bare switching verbs.
              Any-of. LOOSER.

Reporting the net movement would say nothing about which one moved it, so every
document is sieved under four shapes: OLD, NEW, and each change on its own.

RETRIEVAL IS A UNION, AND THE BIAS RUNS TOWARDS THE OLD SHAPE
------------------------------------------------------------
Three query families are issued and the corpus is their union:

    pair      both aliases, no verb. The new shape's own logic — the conjunction
              of two model names is the narrowing, and topic is deliberately loose.
    pair+verb both aliases and one switching verb. Also tests the prior run's
              finding that a bare token after a phrase is not a filter.
    phrase    the RETIRED directional phrases, so the old shape is not measured
              on a corpus retrieved for the new one.

A document retrieved by any family is sieved under all four shapes. That gives
the old shape documents its own queries would not have found, which is the safe
direction: it can only make the old shape look better than it was.

NO MODEL PARTICIPATES, and nothing here decides anything: it counts.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from math import prod
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.adapters.queries.contract import TermSet, load_queries  # noqa: E402
from collect.adapters.queries.sieve import sieve_any  # noqa: E402
from collect.registry.seed import load_seed_file  # noqa: E402
from collect.registry.sources import load_sources  # noqa: E402


def reddit_source_row() -> dict:
    """The `reddit` row from `contract/sources.yaml`, for the terms gate."""
    for row in load_sources().platforms:
        if row.get("id") == "reddit":
            return row
    raise SystemExit("contract/sources.yaml has no `reddit` source row")

SURFACES = Path("fixtures/openrouter/observed-surfaces.json")

#: Expensive slots migrate TO cheap ones. Sources and targets are named rather
#: than derived from price: `price_in` is NULL for 4 of the 11 seed models, and
#: rule 6 says a NULL price is not the cheapest tier.
SOURCE_SLOTS = ("frontier", "mid")
TARGET_SLOTS = ("budget", "open-weight", "just-launched")

#: THE PAIR IS UNORDERED NOW, and that is a consequence of the change rather
#: than a shortcut here. Both aliases sit in `subject`, so (a, b) and (b, a)
#: render the same requirement and the same query. queries.yaml's note about 90
#: ordered pairs collapsing to 45 was a rendering decision before; with both
#: models in an all-of group it is arithmetic.
#:
#: Direction still exists — it is read from the sentence at extraction, which is
#: what `direction: decided_at_extraction` says.

#: The old shape, from `git show 4751d1a^:contract/queries.yaml`. Hardcoded
#: because a measurement that reads its own baseline from the working tree stops
#: being a baseline the moment somebody edits the tree.
OLD_SHAPE = {
    "positive": TermSet(
        subject=("{alias}",),
        topic=(
            "replaced {alias_b}", "switched from {alias_b}", "moved off {alias_b}",
            "migrated from {alias_b}", "instead of {alias_b}", "swapped {alias_b}",
        ),
        signal=(
            "held up", "no regression", "no regressions", "nobody noticed", "saved us",
            "cheaper per", "still running", "kept it in production", "months later",
        ),
    ),
    "negative": TermSet(
        subject=("{alias}",),
        topic=(
            "switched back", "reverted to", "went back to", "rolled back",
            "moved back to {alias_b}",
        ),
        signal=(
            "regression after", "quality dropped", "started failing",
            "complaint from", "wasn't worth", "had to revert",
        ),
    ),
}

#: Retrieval verbs, and the cap is stated rather than silent: the positive entry
#: carries ten topic terms and the negative seven. Issuing every one against
#: every pair is 400 requests for a corpus the sieve reads locally anyway, so
#: three are issued and the rest are sieve-only. Reported in the run summary.
RETRIEVAL_VERBS = ("replaced", "switched from", "reverted to")

#: Old-shape retrieval is ORDERED and therefore doubles. Capped to the pairs
#: whose models the corpus discusses most, two phrases per stance. Also reported.
OLD_PHRASES = ("replaced {alias_b}", "switched from {alias_b}", "moved back to {alias_b}")
OLD_PAIR_CAP = 8


@dataclass(frozen=True)
class Model:
    """One side of a pair: an id, and the spellings to search and sieve with."""

    canonical_id: str
    #: Retrieval form — one spelling, the one people write.
    surface: str
    #: Sieve forms. `sieve_any` reads all of them, because the form a query was
    #: issued in and the form a document is written in are different questions.
    forms: tuple[str, ...]
    origin: str  # "seed" | "attested"

    @property
    def short(self) -> str:
        return self.canonical_id.split("/")[-1]


def seed_models() -> list[Model]:
    """The 11 hand-curated models, minus anything retired."""
    today = date.today()
    out = []
    for m in load_seed_file().models:
        if m.retirement_date and m.retirement_date <= today:
            continue
        forms = tuple(dict.fromkeys([m.aliases.surface, *m.aliases.variants]))
        out.append(Model(m.canonical_id, m.aliases.surface, forms, "seed"))
    return out


def attested_models(limit: int = 6) -> list[Model]:
    """The most-discussed models, spelled the way the corpus spells them.

    The registry went from 11 models to 340, and the prediction to test is that
    the subject constraint is therefore materially different. It is not
    different by registry size alone: a polled model carries no reviewed alias
    surfaces, so it is unsearchable (`openrouter.alias_coverage` reports exactly
    that gap). What the extract supplies instead is MEASURED surfaces for the 72
    models the corpus discusses — `opus 5` at 1,445 mentions where the seed file
    nominates `claude opus 5` at 0 — so this set tests registry growth through
    the only route by which it can reach retrieval today.
    """
    rows = json.loads(SURFACES.read_text(encoding="utf-8"))
    by_model: dict[str, list[tuple[int, str]]] = {}
    for row in rows:
        if row["verdict"] not in ("resolved", "attested-gap") or len(row["models"]) != 1:
            continue
        by_model.setdefault(row["models"][0], []).append((row["mentions"], row["surface"]))

    ranked = sorted(
        by_model.items(), key=lambda kv: -sum(m for m, _ in kv[1])
    )[:limit]
    out = []
    for canonical_id, surfaces in ranked:
        surfaces.sort(key=lambda ms: -ms[0])
        forms = tuple(s for _, s in surfaces[:3])
        out.append(Model(canonical_id, forms[0], forms, "attested"))
    return out


def pairs_of(models: list[Model], *, tiered: bool) -> list[tuple[Model, Model]]:
    """Unordered pairs. Tiered means expensive-slot to cheap-slot only."""
    if not tiered:
        return list(itertools.combinations(models, 2))

    slots = {m.canonical_id: m for m in models}
    seed = {m.canonical_id: m for m in load_seed_file().models}
    sources = [m for cid, m in slots.items() if seed[cid].slot in SOURCE_SLOTS]
    targets = [m for cid, m in slots.items() if seed[cid].slot in TARGET_SLOTS]
    return [(a, b) for a in sources for b in targets]


# ── stage 1: retrieve ─────────────────────────────────────────────────────


def plan_queries(seed_pairs, attested_pairs, discussed: dict[str, int]):
    """Every query string this run will issue, with what it was built from."""
    planned: list[dict] = []

    for label, pair_list in (("seed", seed_pairs), ("attested", attested_pairs)):
        for a, b in pair_list:
            base = f"{a.surface} {b.surface}"
            planned.append(
                {"family": "pair", "set": label, "a": a.canonical_id,
                 "b": b.canonical_id, "query": base}
            )
            for verb in RETRIEVAL_VERBS:
                planned.append(
                    {"family": "pair+verb", "set": label, "a": a.canonical_id,
                     "b": b.canonical_id, "query": f"{base} {verb}"}
                )

    # Old-shape retrieval, ordered and capped.
    ranked = sorted(
        seed_pairs,
        key=lambda ab: -(discussed.get(ab[0].canonical_id, 0)
                         + discussed.get(ab[1].canonical_id, 0)),
    )[:OLD_PAIR_CAP]
    for a, b in ranked:
        for first, second in ((a, b), (b, a)):
            for phrase in OLD_PHRASES:
                rendered = phrase.replace("{alias_b}", second.surface)
                planned.append(
                    {"family": "phrase", "set": "seed", "a": first.canonical_id,
                     "b": second.canonical_id,
                     "query": f'"{rendered}" {first.surface}'}
                )

    seen: set[str] = set()
    out = []
    for item in planned:
        if item["query"] in seen:
            continue
        seen.add(item["query"])
        out.append(item)
    return out


def retrieve(out_dir: Path) -> int:
    from collect.adapters.reddit import build_client, harvester_for_source
    from collect.rawstore import RawStore

    out_dir.mkdir(parents=True, exist_ok=True)
    store = RawStore(out_dir / "raw")

    seeds = seed_models()
    attested = attested_models()
    discussed = _mentions_by_model()
    seed_pairs = pairs_of(seeds, tiered=True)
    attested_pairs = pairs_of(attested, tiered=False)
    queries = plan_queries(seed_pairs, attested_pairs, discussed)

    print(f"pairs     : {len(seed_pairs)} seed (tiered), {len(attested_pairs)} attested")
    print(f"queries   : {len(queries)} distinct")
    print(f"            capped: {len(RETRIEVAL_VERBS)} of 10 positive verbs issued, "
          f"old-shape phrases on {OLD_PAIR_CAP} pairs")

    sidecar = (out_dir / "posts.jsonl").open("w", encoding="utf-8")
    runs = (out_dir / "runs.jsonl").open("w", encoding="utf-8")
    seen_posts: set[str] = set()
    calls = quota = 0
    try:
        with build_client() as client:
            # Through the factory, so the NFR-5 gate runs. Until 2026-08-18
            # this script constructed RedditHarvester directly and the Reddit
            # path never called `assert_terms_reviewed` at all — the corpus
            # under `_substitution_slice/` was gathered before any ruling
            # existed. `reddit-via-rapidapi` now permits it, for internal
            # development only, and the gate re-checks that basis every run.
            searcher = harvester_for_source(
                reddit_source_row(), client=client, store=store
            )
            for index, item in enumerate(queries, 1):
                run = searcher.search(item["query"])
                calls += run.search_calls
                # `is not None`, not `or`. quota_remaining == 0 means the month
                # is EXHAUSTED, which is the single most important value this
                # field ever takes, and `x or quota` discards it in favour of
                # the last non-zero reading.
                if run.quota_remaining is not None:
                    quota = run.quota_remaining
                runs.write(json.dumps({
                    **item,
                    "posts": len(run.posts),
                    "calls": run.search_calls,
                    "http_errors": run.http_errors,
                    "rate_limited": run.rate_limited,
                    # Recorded per run, not only totalled at the end. Two runs
                    # on 2026-08-17 consumed 372 requests and 372 quota units,
                    # and establishing that took subtracting two numbers out of
                    # two report headers - with 35 requests between them that
                    # nothing had recorded. NULL where the header was absent:
                    # unread is not zero (rule 6).
                    "quota_remaining": run.quota_remaining,
                    "refs": run.discovery_refs,
                }) + "\n")
                for post in run.posts:
                    if post.external_id in seen_posts:
                        continue
                    seen_posts.add(post.external_id)
                    sidecar.write(json.dumps({
                        "external_id": post.external_id,
                        "query": item["query"],
                        "family": item["family"],
                        "set": item["set"],
                        "subreddit": post.subreddit,
                        "url": post.url,
                        "text": post.sieve_text,
                    }) + "\n")
                print(f"  [{index:>3}/{len(queries)}] {item['family']:<9} "
                      f"{len(run.posts):>3} posts  {item['query'][:58]}")
    finally:
        sidecar.close()
        runs.close()

    # `quota` stays 0 only if no response ever carried the header, which is a
    # different fact from a quota of 0 and must not print as one.
    reading = "not reported by any response" if quota == 0 else f"{quota}"
    print(f"\nretrieved : {len(seen_posts)} distinct posts, {calls} requests, "
          f"quota remaining {reading}")
    return 0


def _mentions_by_model() -> dict[str, int]:
    rows = json.loads(SURFACES.read_text(encoding="utf-8"))
    out: dict[str, int] = {}
    for row in rows:
        if len(row["models"]) == 1:
            out[row["models"][0]] = out.get(row["models"][0], 0) + row["mentions"]
    return out


# ── stage 2: sieve, four ways ─────────────────────────────────────────────


def shapes() -> dict[str, dict[str, TermSet]]:
    """OLD, NEW, and each half of the change on its own."""
    live = {e.stance: e.terms for e in load_queries().substitution}
    new, old = live, OLD_SHAPE
    return {
        "OLD": old,
        "NEW": new,
        "SUBJECT-only": {
            stance: TermSet(new[stance].subject, old[stance].topic, old[stance].signal)
            for stance in old
        },
        "TOPIC-only": {
            stance: TermSet(old[stance].subject, new[stance].topic, new[stance].signal)
            for stance in old
        },
    }


@lru_cache(maxsize=1)
def _seed_rows() -> dict:
    """The seed file, parsed once.

    It was being re-read per model per post — 15,564 YAML parses — which is the
    kind of accident a two-stage harness makes cheap to find and a one-shot script
    hides inside its runtime.
    """
    return {m.canonical_id: m for m in load_seed_file().models}


@lru_cache(maxsize=256)
def _version_forms(canonical_id: str, forms: tuple[str, ...]) -> tuple[str, ...]:
    from collect.registry.aliases import classify_specificity

    seed = _seed_rows()
    if canonical_id not in seed:
        return forms
    row = seed[canonical_id]
    return tuple(f for f in forms if classify_specificity(f, row) in ("version", "snapshot"))


def version_forms(model: Model) -> tuple[str, ...]:
    """This model's spellings, minus the ones that name a LINE rather than a tier.

    `contract/seed_models.yaml` declares `sonnet` and `haiku` as variants, and
    they resolve at family specificity — which never counts as independent
    corroboration. They were harmless while `subject` held one alias. With two,
    a post saying "opus" and "sonnet" satisfies an all-of subject for
    (claude-opus-5, claude-sonnet-5) and the conjunction narrows far less than it
    appears to. 62% of family-word mentions carry no version at all.

    So every shape is measured twice: once with what the contract declares, once
    with family surfaces dropped. `classify_specificity` decides, not this file.

    An attested-set model has no seed row to classify against; its surfaces come
    from the extract, which only carries version-token forms anyway.
    """
    return _version_forms(model.canonical_id, model.forms)


def present_forms(models, posts, *, strict: bool) -> list[dict[str, tuple[str, ...]]]:
    """Which spellings of which model each post actually contains.

    Computed once per post with the SHIPPED `matches` over the SHIPPED
    `normalize` — the same two primitives `sieve()` uses for the subject group,
    which is what makes the skip below sound rather than an approximation.

    It buys two things. Restricting each pair's variants to spellings the post
    contains turns nine renderings into one or two: a term carrying a spelling
    the text does not have cannot match, so nothing is lost. And a pair whose
    subject cannot be satisfied is skipped entirely rather than sieved to be told
    so — 30 pairs x 1,297 posts is 38,910 combinations, of which 691 name both
    models. Without it the run projects at 124 minutes.
    """
    from collect.adapters.queries.sieve import matches, normalize

    out = []
    for post in posts:
        haystack = normalize(post["text"])
        row = {}
        for model in models:
            forms = version_forms(model) if strict else model.forms
            row[model.canonical_id] = tuple(f for f in forms if matches(f, haystack))
        out.append(row)
    return out


def _variants_for(terms: TermSet, a: Model, b: Model, present: dict, cap: int = 3):
    """Rendered term sets for one pair against one post."""
    forms_a = present[a.canonical_id][:cap] or (a.forms[0],)
    needs_b = "{alias_b}" in " ".join(terms.subject + terms.topic + terms.signal)
    if not needs_b:
        return [terms.substitute(form_a) for form_a in forms_a]
    forms_b = present[b.canonical_id][:cap] or (b.forms[0],)
    return [terms.substitute(fa, fb) for fa in forms_a for fb in forms_b]


def _free_variants(free: TermSet, b: Model, present: dict, cap: int = 3):
    """Renderings of a SUBJECT-FREE term set. One per spelling of b, never a cross.

    `free` carries no `{alias}` — only topic and signal survive, and `{alias_b}`
    appears in topic under the old shape. Crossing it with a's spellings produced
    nine renderings of three distinct term sets, and made the cache key depend on
    a, so the same work was redone for every pair b appears in.
    """
    forms_b = present[b.canonical_id][:cap] or (b.forms[0],)
    return [free.substitute(b.forms[0], form_b) for form_b in forms_b]


def _required(terms: TermSet) -> tuple[bool, bool]:
    """Which models the SUBJECT group requires. All-of, so both may be needed."""
    subject = " ".join(terms.subject)
    return "{alias}" in subject, "{alias_b}" in subject


def orderings_for(terms: TermSet, pairs):
    """Ordered pairs where the roles matter, unordered where they cannot.

    THE CONTROL DOCUMENT CAUGHT THIS. Under the old shape, "we replaced claude
    opus 5 with claude haiku 4.5" passes as (alias=haiku, alias_b=opus) and FAILS
    as (alias=opus, alias_b=haiku): the topic term renders as `replaced claude
    haiku 4.5`, which the sentence does not contain. Testing one ordering per pair
    would have measured the old shape at half its real reach and made the new
    shape look better for a reason that is mine rather than hers.

    Under the new shape both aliases sit in `subject`, an all-of group, and topic
    carries no placeholder — so swapping the roles renders the same requirement,
    and evaluating both orderings would double every count.

    Decided by rendering rather than by a rule about shapes: two sentinels in,
    compare what comes out.
    """
    forward = terms.substitute("<<A>>", "<<B>>")
    reverse = terms.substitute("<<B>>", "<<A>>")
    symmetric = all(
        set(getattr(forward, group)) == set(getattr(reverse, group))
        for group in ("subject", "topic", "signal")
    )
    if symmetric:
        return list(pairs)
    return [ordered for a, b in pairs for ordered in ((a, b), (b, a))]


def sieve_stage(out_dir: Path) -> int:
    posts = [json.loads(line) for line in
             (out_dir / "posts.jsonl").read_text(encoding="utf-8").splitlines() if line]
    seeds = {m.canonical_id: m for m in seed_models()}
    attested = {m.canonical_id: m for m in attested_models()}
    models = {**seeds, **attested}

    seed_pairs = pairs_of(list(seeds.values()), tiered=True)
    attested_pairs = pairs_of(list(attested.values()), tiered=False)
    all_pairs = seed_pairs + attested_pairs

    print(f"corpus    : {len(posts)} distinct posts")
    by_family: dict[str, int] = {}
    for post in posts:
        by_family[post["family"]] = by_family.get(post["family"], 0) + 1
    for family, count in sorted(by_family.items()):
        print(f"            {family}: {count} first retrieved by this family")
    print(f"pairs     : {len(all_pairs)}  ({len(models)} models)")

    for strict in (False, True):
        policy = "version-only surfaces" if strict else "surfaces as declared"
        present = present_forms(list(models.values()), posts, strict=strict)
        named = sum(1 for row in present if any(row.values()))
        both = sum(1 for row in present for a, b in all_pairs
                   if row[a.canonical_id] and row[b.canonical_id])
        print(f"\n==== {policy} " + "=" * (58 - len(policy)))
        print(f"  posts naming any model      : {named} / {len(posts)}")
        print(f"  (pair, post) naming both    : {both} of "
              f"{len(all_pairs) * len(posts)} combinations")
        for name, shape in shapes().items():
            # ASCII: the console here is cp1252, and a box-drawing character in
            # a progress line killed one run after its requests were spent.
            print(f"\n  -- {name} " + "-" * (60 - len(name)))
            entries = len(orderings_for(shape["positive"], all_pairs))
            print(f"  rendered entries per stance : {entries} "
                  f"({'ordered' if entries > len(all_pairs) else 'unordered'} pairs)")
            report_shape(shape, posts, all_pairs, present)
    return 0


def report_shape(shape, posts, pairs, present) -> None:
    """The funnel, the marginals, the per-entry prediction, and what passed.

    THE MARGINALS ARE MEASURED INDEPENDENTLY PER GROUP, which is not a detail.
    The 2026-08-14 run reported "77% topic" by counting topic matches only among
    documents where subject also matched — bounded by the subject rate, and
    unable to measure topic at all. Here topic and signal are read with a
    subject-free term set so the three rates are about three separate questions.
    """
    total = len(posts)
    group_hits = {"subject": set(), "topic": set(), "signal": set()}
    passes: list[tuple[str, str, str, str]] = []
    entry_rates: list[tuple[float, float, float]] = []
    skipped = 0

    #: The subject-free sieve depends on the rendered topic and signal terms and
    #: on the document — not on the pair. In the NEW shape those terms carry no
    #: placeholder at all, so one computation serves all 30 pairs instead of 30
    #: identical ones. Keyed by what was actually rendered, so a shape whose topic
    #: DOES carry `{alias_b}` still gets one entry per spelling.
    loose_cache: dict[tuple, object] = {}

    for stance, terms in shape.items():
        needs_a, needs_b = _required(terms)
        free = TermSet((), terms.topic, terms.signal)

        for a, b in orderings_for(terms, pairs):
            subject_ok = topic_ok = signal_ok = 0
            for post, row in zip(posts, present, strict=True):
                have_a, have_b = bool(row[a.canonical_id]), bool(row[b.canonical_id])

                # Topic and signal FIRST and independently of subject.
                free_variants = _free_variants(free, b, row)
                key = (post["external_id"],
                       tuple((v.topic, v.signal) for v in free_variants))
                loose = loose_cache.get(key)
                if loose is None:
                    loose = loose_cache[key] = sieve_any(free_variants, post["text"])
                if "topic" not in loose.missing:
                    topic_ok += 1
                    group_hits["topic"].add(post["external_id"])
                if "signal" not in loose.missing:
                    signal_ok += 1
                    group_hits["signal"].add(post["external_id"])

                if (needs_a and not have_a) or (needs_b and not have_b):
                    skipped += 1
                    continue
                subject_ok += 1
                group_hits["subject"].add(post["external_id"])

                verdict = sieve_any(_variants_for(terms, a, b, row), post["text"])
                if verdict.passed:
                    passes.append((stance, f"{a.short}|{b.short}", post["external_id"],
                                   post.get("url", "")))
            entry_rates.append((subject_ok / total, topic_ok / total, signal_ok / total))

    print("  documents matching, any entry, each group counted independently:")
    for group in ("subject", "topic", "signal"):
        hits = len(group_hits[group])
        print(f"    {group:<8} {hits:>5} / {total}  {hits / total:6.1%}")

    predicted = total * (1 - prod(1 - (s * t * g) for s, t, g in entry_rates))
    unique = {p[2] for p in passes}
    print(f"  per-entry independence predicts : {predicted:.2f} documents")
    print(f"  measured, full sieve            : {len(unique)} documents "
          f"({len(passes)} (entry, document) pairs)")
    print(f"  subject unsatisfiable, skipped  : {skipped} combinations")
    for stance, pair, external_id, url in passes[:12]:
        print(f"      PASS {stance:<9} {pair:<30} {external_id}  {url}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("retrieve", "sieve"))
    parser.add_argument("--out", default="./_substitution_slice")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    return retrieve(out_dir) if args.stage == "retrieve" else sieve_stage(out_dir)


if __name__ == "__main__":
    sys.exit(main())
