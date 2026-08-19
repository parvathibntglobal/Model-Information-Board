"""Build Engineer 2's two labelling pools. Re-sieve over a local corpus, no fetch.

    py -3 scripts/labelling_pools.py --out fixtures/golden

CANDIDATE POOLS, NOT FINISHED SETS. She drafts both and hands ~50 back for
cross-labelling, so nothing here carries a label and nothing here is an answer
key. Every row is a question with its evidence attached.

WHY THE ENTITY POOL IS STRATIFIED AND NOT RANDOM
-------------------------------------------------
Her reason, and it is right: a random 200 mentions from this corpus is mostly
`opus 5` and `gemini 2.5 flash` matching one surface each, and an accuracy figure
over that measures the easy case. The strata are the places resolution is
actually decided:

    family-bare       a bare `sonnet` or `haiku` with no version token adjacent.
                      62% of family-word mentions are like this. The resolver
                      must NOT resolve them to a tier - `opus` is attested 968
                      times bare and attributable to no single model - so these
                      are the rows where the correct answer is "cannot".
    spacing-variant   `gpt-5` against `gpt 5` against `gpt5`. Same model, three
                      surfaces, and the normaliser is what makes them one.
    ambiguous-owner   a surface several registry models could be MEANT BY.
                      `qwen3` spans 25 registry ids, `gpt 5.6` spans 6,
                      `claude 4.5` spans 3. Resolves the ENTITY question (a
                      model is named) and cannot resolve attribution, so both
                      halves need a label.

                      SOURCED FROM THE EXTRACT, NOT FROM DERIVATION, and that is
                      a correction worth recording: the first version of this
                      stratum looked for surfaces that several canonical ids
                      DERIVE, and found zero. Derivation is injective - each id
                      renders its own local part, so two ids cannot produce one
                      string. Ambiguity is a fact about what a human meant, not
                      about what a machine emits, and only the 49
                      `attested-gap-ambiguous` surfaces in
                      `fixtures/openrouter/observed-surfaces.json` measure it.
                      48 of those 49 are reachable by no derivation at all.
    unresolvable      no surface matches at all. **Real negatives**, without
                      which precision cannot be computed and the set measures
                      only recall.
    single-clear      one surface, one owner. The control. Without it there is
                      no baseline to say the hard strata are hard.

WHAT THE POOLS ARE DRAWN FROM, AND WHAT THAT FORBIDS
------------------------------------------------------
`_substitution_slice/` - 1,297 distinct Reddit posts recovered from 120 raw
payloads, retrieved 2026-08-17 by the substitution sweep.

**Every post was retrieved by a query containing model names.** So this corpus
is pre-filtered for exactly what the entity gate tests. Consequences, both of
which belong in whatever these pools are used to argue:

  * the FILTER pool's mix is not the mix of a real sweep. A survival rate
    measured on it is an upper bound and calibrates nothing.
  * the ENTITY pool's `unresolvable` stratum is scarcer here than in the wild,
    so a precision figure from it is optimistic.

Reddit only, and short-form only. GitHub config lines and blog prose name models
differently, and neither is represented.

PUBLISHED CONTENT IS QUOTE + ATTRIBUTION + LINK, NEVER FULL TEXT. Rows carry a
bounded snippet and the permalink, so the pools stay inside the same rule the
board publishes under.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.registry.propose import FAMILY_WORDS  # noqa: E402
from collect.registry.seed import load_seed_file  # noqa: E402
from collect.triage.entity import (  # noqa: E402
    SurfacePopulation,
    build_population,
    normalize,
    resolve,
)
from collect.triage.gates import Document, triage  # noqa: E402

DEFAULT_SLICE = Path(__file__).resolve().parents[1] / "_substitution_slice"

#: Characters either side of a matched surface. Enough for a human to judge the
#: mention, far short of the document.
SNIPPET_RADIUS = 140

#: Targets. Approximate on purpose - a stratum the corpus cannot fill is
#: reported short rather than padded from an easier one.
ENTITY_TARGET = 200
FILTER_TARGET = 200

FAMILY_BARE = "family-bare"
SPACING_VARIANT = "spacing-variant"
AMBIGUOUS_OWNER = "ambiguous-owner"
UNRESOLVABLE = "unresolvable"
SINGLE_CLEAR = "single-clear"

STRATA = (FAMILY_BARE, SPACING_VARIANT, AMBIGUOUS_OWNER, UNRESOLVABLE, SINGLE_CLEAR)

#: How many of ENTITY_TARGET each stratum should contribute. The hard strata are
#: over-weighted relative to their frequency, which is the point of stratifying.
QUOTA = {
    FAMILY_BARE: 50,
    SPACING_VARIANT: 40,
    AMBIGUOUS_OWNER: 40,
    UNRESOLVABLE: 40,
    SINGLE_CLEAR: 30,
}

_VERSION_NEAR = re.compile(r"\b\d")


@dataclass
class Post:
    external_id: str
    url: str
    subreddit: str | None
    created_at: str | None
    author: str | None
    is_self: bool | None
    title: str
    body: str

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.body}".strip()


def load_corpus(slice_dir: Path) -> list[Post]:
    """Every distinct post in the raw payloads. Richer than posts.jsonl."""
    posts: dict[str, Post] = {}
    for f in (slice_dir / "raw").rglob("*"):
        if not f.is_file():
            continue
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for entry in payload.get("data", {}).get("posts", []) or []:
            d = entry.get("data") or {}
            if not d.get("id"):
                continue
            ts = d.get("created_utc")
            posts[d["id"]] = Post(
                external_id=d["id"],
                url="https://www.reddit.com" + (d.get("permalink") or ""),
                subreddit=d.get("subreddit"),
                created_at=(
                    datetime.fromtimestamp(ts, tz=UTC).date().isoformat()
                    if ts
                    else None
                ),
                author=d.get("author"),
                is_self=d.get("is_self"),
                title=d.get("title") or "",
                body=d.get("selftext") or "",
            )
    return sorted(posts.values(), key=lambda p: p.external_id)


def snippet_around(text: str, surface: str) -> tuple[str, int] | None:
    """A bounded window around the first occurrence, and where it started.

    Matched on the NORMALISED string and mapped back, because the document spells
    the surface however the writer did - `GPT 5`, `gpt-5` - and a raw `find` on
    the surface misses every one of those.
    """
    norm_text = normalize(text)
    norm_surface = normalize(surface)
    if not norm_surface:
        return None
    pos = norm_text.find(norm_surface)
    if pos < 0:
        return None

    # Map the normalised offset back by walking the raw text and counting the
    # characters that survive normalisation.
    raw_start = raw_end = None
    seen = 0
    for i, ch in enumerate(text):
        if raw_start is None and seen == pos:
            raw_start = i
        if seen == pos + len(norm_surface):
            raw_end = i
            break
        if normalize(ch):
            seen += 1
    if raw_start is None:
        return None
    if raw_end is None:
        raw_end = len(text)

    lo = max(0, raw_start - SNIPPET_RADIUS)
    hi = min(len(text), raw_end + SNIPPET_RADIUS)
    prefix = "..." if lo > 0 else ""
    suffix = "..." if hi < len(text) else ""
    return f"{prefix}{text[lo:hi].strip()}{suffix}", raw_start


def bare_family_hits(text: str) -> list[str]:
    """Family words appearing with NO digit within 20 characters.

    Deliberately crude and stated as such: it is a candidate finder for a human,
    not a classifier. `alias-surfaces.md` §4 measured the same shape and put 62%
    of family mentions in this bucket.
    """
    found = []
    lowered = text.casefold()
    for word in sorted(FAMILY_WORDS):
        for m in re.finditer(rf"\b{re.escape(word)}\b", lowered):
            window = lowered[m.end() : m.end() + 20]
            if not _VERSION_NEAR.search(window):
                found.append(word)
                break
    return found


@dataclass
class EntityRow:
    stratum: str
    surface: str
    snippet: str
    source_url: str
    subreddit: str | None
    external_id: str
    created_at: str | None
    #: Registry ids that derive this surface. EMPTY IS TWO DIFFERENT FACTS:
    #: a declared-only surface has no owner recorded, and an unresolvable row has
    #: no surface at all. `stratum` is what separates them.
    candidate_models: list[str] = field(default_factory=list)
    #: Every surface the population matched in this document, for context.
    all_surfaces_in_document: list[str] = field(default_factory=list)
    label: None = None
    note: str = ""


def load_ambiguous(path: Path) -> dict[str, list[str]]:
    """Surfaces the extract found several registry models could be meant by.

    Returns surface -> candidate ids. Not `population.owners`: see the
    `ambiguous-owner` note in the module docstring for why derivation cannot
    produce this and the corpus is the only source of it.
    """
    if not path.is_file():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {
        r["surface"]: list(r["models"])
        for r in rows
        if r.get("verdict") == "attested-gap-ambiguous" and len(r.get("models", [])) > 1
    }


def build_entity_pool(
    posts,
    population: SurfacePopulation,
    ambiguous: dict[str, list[str]] | None = None,
) -> tuple[list[EntityRow], dict]:
    buckets: dict[str, list[EntityRow]] = defaultdict(list)
    ambiguous = ambiguous or {}
    # Longest first, so `gemini 3.1 pro` is preferred over `gemini 3` in a
    # document containing both - the more specific mention is the harder label.
    ambiguous_order = sorted(ambiguous, key=lambda s: (-len(s), s))

    for post in posts:
        text = post.text
        matched = resolve(text, population)
        haystack = normalize(text)

        def row(
            stratum: str,
            surface: str,
            note: str = "",
            candidates: list[str] | None = None,
            *,
            _post=post,
            _text=text,
            _matched=matched,
        ) -> EntityRow | None:
            # The three underscore parameters bind this iteration's values at
            # definition time. Without them the closure reads whatever the loop
            # holds when it is CALLED, which is the same iteration today and a
            # silent cross-document mix-up the moment anyone defers a call.
            got = snippet_around(_text, surface) if surface else (_text[:280], 0)
            if got is None:
                return None
            return EntityRow(
                stratum=stratum,
                surface=surface,
                snippet=got[0],
                source_url=_post.url,
                subreddit=_post.subreddit,
                external_id=_post.external_id,
                created_at=_post.created_at,
                candidate_models=(
                    candidates
                    if candidates is not None
                    else list(population.owners.get(surface, ()))
                ),
                all_surfaces_in_document=list(_matched[:6]),
                note=note,
            )

        for surface in ambiguous_order:
            if normalize(surface) and normalize(surface) in haystack:
                models = ambiguous[surface]
                r = row(
                    AMBIGUOUS_OWNER,
                    surface,
                    f"the corpus extract found {len(models)} registry models this "
                    "surface could be meant by; attribution cannot be decided from "
                    "the string alone",
                    candidates=models,
                )
                if r:
                    buckets[AMBIGUOUS_OWNER].append(r)
                break

        if not matched:
            r = row(UNRESOLVABLE, "", "no surface in the population appears here")
            if r:
                buckets[UNRESOLVABLE].append(r)
            continue

        for word in bare_family_hits(text):
            r = row(
                FAMILY_BARE,
                word,
                "family word with no adjacent version; excluded from the "
                "population on purpose - the expected answer is 'cannot resolve'",
            )
            if r:
                buckets[FAMILY_BARE].append(r)

        for surface in matched:
            owners = population.owners.get(surface, ())
            siblings = [
                s
                for s in matched
                if s != surface
                and population.owners.get(s, ()) == owners
                and normalize(s) != normalize(surface)
            ]
            if siblings:
                r = row(
                    SPACING_VARIANT,
                    surface,
                    f"same owner as {siblings[:2]} - one model, several spellings",
                )
                if r:
                    buckets[SPACING_VARIANT].append(r)
            elif len(owners) == 1:
                r = row(SINGLE_CLEAR, surface, "one surface, one owner")
                if r:
                    buckets[SINGLE_CLEAR].append(r)

    # Spread each stratum across SURFACES first and documents second. Taking the
    # first N by document id filled `family-bare` with `chatgpt` and `pro` and
    # reached no `haiku` at all, though the corpus holds 106 bare ones - the
    # quota was exhausted before the rarer words were reached. Round-robin over
    # the surface fixes that, and it is the surface the label is about.
    out: list[EntityRow] = []
    shortfall = {}
    for stratum in STRATA:
        rows = buckets[stratum]
        by_surface: dict[str, list[EntityRow]] = defaultdict(list)
        for r in rows:
            by_surface[r.surface].append(r)
        # Within one surface, spread across documents the same way.
        for surface, group in by_surface.items():
            by_doc: dict[str, list[EntityRow]] = defaultdict(list)
            for r in group:
                by_doc[r.external_id].append(r)
            spread: list[EntityRow] = []
            i = 0
            while len(spread) < len(group):
                added = False
                for d in sorted(by_doc):
                    if i < len(by_doc[d]):
                        spread.append(by_doc[d][i])
                        added = True
                if not added:
                    break
                i += 1
            by_surface[surface] = spread

        interleaved: list[EntityRow] = []
        surfaces = sorted(by_surface)
        i = 0
        while len(interleaved) < len(rows):
            added = False
            for s in surfaces:
                if i < len(by_surface[s]):
                    interleaved.append(by_surface[s][i])
                    added = True
            if not added:
                break
            i += 1
        want = QUOTA[stratum]
        take = interleaved[:want]
        out.extend(take)
        if len(take) < want:
            shortfall[stratum] = {"wanted": want, "available": len(take)}

    stats = {
        "available_per_stratum": {s: len(buckets[s]) for s in STRATA},
        "taken_per_stratum": {
            s: sum(1 for r in out if r.stratum == s) for s in STRATA
        },
        "shortfall": shortfall,
    }
    return out, stats


@dataclass
class FilterRow:
    external_id: str
    source_url: str
    subreddit: str | None
    created_at: str | None
    snippet: str
    token_count: int
    is_link_post: bool | None
    has_own_commentary: bool
    #: What the gates decided, so she is labelling AGAINST a verdict rather than
    #: from scratch. Disagreement is the signal the set exists to produce.
    gate_verdict: str = ""
    gate_reasons: list[str] = field(default_factory=list)
    gates_that_did_not_run: list[str] = field(default_factory=list)
    matched_surfaces: list[str] = field(default_factory=list)
    label: None = None
    note: str = ""


def build_filter_pool(posts, population: SurfacePopulation) -> tuple[list[FilterRow], dict]:
    """~200 documents, whatever mix the corpus holds - proportional, not balanced.

    Deliberately NOT stratified, unlike the entity pool. She asked for the mix
    the corpus holds, and the filter set's job is to check the gates against
    ordinary traffic. Sampled by a stable stride so the draw is reproducible and
    is not the first 200 by id.
    """
    rows: list[FilterRow] = []
    stride = max(1, len(posts) // FILTER_TARGET)
    for post in posts[::stride][:FILTER_TARGET]:
        doc = Document(
            text=post.text,
            author=post.author,
            is_self_post=post.is_self,
            body=post.body,
        )
        result = triage(doc, population=population)
        rows.append(
            FilterRow(
                external_id=post.external_id,
                source_url=post.url,
                subreddit=post.subreddit,
                created_at=post.created_at,
                snippet=post.text[:400] + ("..." if len(post.text) > 400 else ""),
                token_count=len(post.text.split()),
                is_link_post=(None if post.is_self is None else not post.is_self),
                has_own_commentary=bool(post.body.strip()),
                gate_verdict=str(result.verdict),
                gate_reasons=list(result.reasons),
                # BOTH kinds: this field means "said nothing", and the pool
                # labels documents rather than diagnosing the build. The split
                # lives on `TriageResult` for the reader who needs it.
                gates_that_did_not_run=list(result.no_verdict),
                matched_surfaces=list(result.matched_surfaces[:6]),
            )
        )
    kept = sum(1 for r in rows if r.gate_verdict == "kept")
    return rows, {
        "sampled": len(rows),
        "of_corpus": len(posts),
        "stride": stride,
        "gate_kept": kept,
        "gate_dropped": len(rows) - kept,
    }


HEADER = {
    "purpose": "CANDIDATE POOL for Engineer 2 to draft from. Not a labelled set.",
    "labels": "every row has label: null. Nothing here is an answer key.",
    "corpus": (
        "_substitution_slice/ - 1,297 distinct Reddit posts, retrieved 2026-08-17 "
        "by the substitution sweep"
    ),
    "caveat": (
        "EVERY POST WAS RETRIEVED BY A QUERY CONTAINING MODEL NAMES. The corpus is "
        "pre-filtered for what the entity gate tests: the filter pool's mix is not a "
        "real sweep's mix, and the unresolvable stratum is scarcer here than in the "
        "wild, so precision measured on it is optimistic. Reddit and short-form only."
    ),
    "content_rule": "bounded snippet plus permalink, never full text",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slice", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    if not (args.slice / "raw").is_dir():
        print(
            f"no corpus at {args.slice}/raw. This script does not fetch: run "
            "scripts/substitution_slice.py retrieve first.",
            file=sys.stderr,
        )
        return 2

    posts = load_corpus(args.slice)
    print(f"corpus: {len(posts)} distinct posts")

    seed = load_seed_file()
    declared: list[str] = []
    for m in seed.models:
        declared.append(m.aliases.surface)
        declared.extend(m.aliases.variants)

    from collect.db import connect

    conn = connect()
    try:
        models = conn.execute(
            "SELECT canonical_id, display_name FROM model_version ORDER BY canonical_id"
        ).fetchall()
    finally:
        conn.close()

    population = build_population(models, declared)
    print(f"population: {population.basis}")

    args.out.mkdir(parents=True, exist_ok=True)

    ambiguous = load_ambiguous(
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "openrouter"
        / "observed-surfaces.json"
    )
    print(f"ambiguous surfaces from the extract: {len(ambiguous)}")

    entity_rows, entity_stats = build_entity_pool(posts, population, ambiguous)
    filter_rows, filter_stats = build_filter_pool(posts, population)

    for name, rows, stats in (
        ("entity-pool-candidates", entity_rows, entity_stats),
        ("filter-pool-candidates", filter_rows, filter_stats),
    ):
        path = args.out / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            meta = {
                **HEADER,
                "pool": name,
                "population_fingerprint": population.fingerprint,
                "population_basis": population.basis,
                "rows": len(rows),
                "stats": stats,
            }
            fh.write(json.dumps({"_meta": meta}, ensure_ascii=False) + "\n")
            for r in rows:
                fh.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
        print(f"wrote {path}  ({len(rows)} rows)")
        print(f"      {json.dumps(stats, ensure_ascii=False)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
