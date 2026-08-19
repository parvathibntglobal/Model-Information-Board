"""Fetch real blog articles and MEASURE which `So` characters actually appear.

WHY THIS IS A RUN AND NOT A BUILD
---------------------------------
The `So` substitution rule was read off ONE Reddit fixture, where category `So`
meant emoji plus `█`. A constructed census showed it also captures `°`, `©`,
`™`, `✓`, `⚠` — but a reachability census over characters somebody typed into a
test is not a frequency measurement, and narrowing a rule from one is the shape
this project has refused four times: the fixture describing the property.

So this measures. Nine assessed feeds, real articles, trafilatura's own output,
and every `So` occurrence recorded WITH ITS SURROUNDING TEXT so the split can be
read off the corpus rather than guessed at.

WHAT IT DOES NOT DO
-------------------
It proposes no rule. The hypothesis on the table is that the useful split is
"carries sentiment" versus "carries a value", which is not a Unicode category —
and the corpus is allowed to disagree with that. Output is a ledger; the reading
comes after.

POPULATION, STATED HERE BECAUSE THE FIGURE IS WORTHLESS WITHOUT IT
------------------------------------------------------------------
Articles linked from the current feed of nine engineering blogs assessed on
2026-08-14, fetched on the date in the manifest. That is not "blog prose" and
not "the web". Every rate this produces is a rate within those articles, and the
feeds were chosen for practitioner AI content, which biases the symbol mix in
ways nobody has measured — a code-heavy corpus is not a marketing corpus.

RETENTION
---------
Same discipline as `_unfiltered_sweep/`: this is a measurement population, not
evidence. Nothing is quoted, nothing is published, nothing merges into `raw/`.
Article bytes DO land in `raw/` because that is what the fetch path does and
those are legitimately documents; the derived text and the census are outside it
and carry a deletion date.

THE GATE APPLIES. `fetcher_for_source` re-reads robots.txt for every host on
this run, so a feed that changed its mind since 2026-08-14 stops here.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.adapters.blog.fetch import (  # noqa: E402
    NotAFetchTargetError,
    fetcher_for_source,
)
from collect.adapters.blog.parse import extract_article_text  # noqa: E402
from collect.adapters.blog.robots import RobotsGate  # noqa: E402
from collect.assemble.flatten import ENTITIES, flatten, substitute  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.http import build_client  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.registry.sources import load_sources  # noqa: E402

#: Characters either side of an occurrence. Wide enough to tell `72°C` from a
#: sentence ending in an emoji, which is the whole question.
CONTEXT = 48

RETENTION_DAYS = 90


def _occurrences(text: str, article_id: str, feed_id: str) -> list[dict]:
    """Every `So` character in this text, with enough context to classify it."""
    found = []
    for index, char in enumerate(text):
        tag = substitute(char)
        if tag is None:
            continue
        start = max(0, index - CONTEXT)
        end = min(len(text), index + CONTEXT + 1)
        found.append({
            "feed_id": feed_id,
            "article_id": article_id,
            "codepoint": f"U+{ord(char):04X}",
            "char": char,
            "name": unicodedata.name(char, "<unnamed>"),
            "category": unicodedata.category(char),
            "tag": tag,
            # 1 char becoming len(tag) is the cost, recorded per occurrence
            # rather than averaged: the average of 13 and 47 describes nothing.
            "flat_cost": len(tag) - 1,
            "context": text[start:end].replace("\n", "\\n"),
            "at": index,
        })
    return found


def sweep(out_dir: Path, max_articles_per_feed: int) -> int:
    contract = load_sources()
    out_dir.mkdir(parents=True, exist_ok=True)

    ua = settings().user_agent
    store = RawStore(Path(settings().raw_store_path))

    articles_file = (out_dir / "articles.jsonl").open("w", encoding="utf-8")
    occ_file = (out_dir / "occurrences.jsonl").open("w", encoding="utf-8")
    feeds_file = (out_dir / "feeds.jsonl").open("w", encoding="utf-8")

    totals = {
        "feeds_attempted": 0, "feeds_gated_out": 0, "feeds_fetched": 0,
        "articles_fetched": 0, "articles_extracted": 0, "articles_empty": 0,
        "chars_extracted": 0, "occurrences": 0,
    }
    entity_survivals: Counter = Counter()
    started = datetime.now(tz=UTC)

    with build_client() as client:
        robots = RobotsGate(client, user_agent=ua)

        for feed in contract.feeds:
            feed_id = feed["id"]
            totals["feeds_attempted"] += 1
            record: dict[str, object] = {"feed_id": feed_id, "endpoint": feed.get("endpoint")}

            try:
                fetcher = fetcher_for_source(
                    feed, robots=robots, rulings=contract.rulings,
                    client=client, store=store,
                )
            except NotAFetchTargetError as exc:
                totals["feeds_gated_out"] += 1
                record |= {"outcome": "not-a-fetch-target", "detail": str(exc)}
                feeds_file.write(json.dumps(record) + "\n")
                print(f"  {feed_id:38s} SKIP not a fetch target")
                continue
            except Exception as exc:  # the terms gate, or a robots refusal
                totals["feeds_gated_out"] += 1
                record |= {"outcome": "refused", "detail": f"{type(exc).__name__}: {exc}"}
                feeds_file.write(json.dumps(record) + "\n")
                print(f"  {feed_id:38s} REFUSED {type(exc).__name__}")
                continue

            run = fetcher.harvest_feed(feed["endpoint"])
            record |= {
                "outcome": run.outcome,
                "fetch_articles": run.fetch_articles,
                "entries": len(run.feed.entries),
                "articles": len(run.articles),
            }
            if run.outcome != "fetched":
                feeds_file.write(json.dumps(record) + "\n")
                print(f"  {feed_id:38s} {run.outcome}")
                continue

            totals["feeds_fetched"] += 1
            kept = 0
            feed_occ = 0
            for article in run.articles:
                if kept >= max_articles_per_feed:
                    break
                if not article.stored:
                    continue
                payload = store.get(article.artifact.ref)
                text = extract_article_text(payload, url=article.entry.url)
                totals["articles_fetched"] += 1
                kept += 1
                article_id = f"{feed_id}#{kept}"

                if text is None:
                    totals["articles_empty"] += 1
                    articles_file.write(json.dumps({
                        "article_id": article_id, "feed_id": feed_id,
                        "url": article.entry.url, "extracted": None,
                    }) + "\n")
                    continue

                totals["articles_extracted"] += 1
                totals["chars_extracted"] += len(text)

                # §4's premise, checked against real articles rather than
                # constructed ones: does any of the five reach the flattener?
                for entity, _decoded in ENTITIES:
                    if entity in text:
                        entity_survivals[entity] += text.count(entity)

                occurrences = _occurrences(text, article_id, feed_id)
                for occurrence in occurrences:
                    occ_file.write(json.dumps(occurrence, ensure_ascii=False) + "\n")
                totals["occurrences"] += len(occurrences)
                feed_occ += len(occurrences)

                flattened = flatten([(article_id, text)])
                articles_file.write(json.dumps({
                    "article_id": article_id, "feed_id": feed_id,
                    "url": article.entry.url,
                    "extracted": len(text),
                    "flattened": len(flattened.text),
                    "segments": len(flattened.segments),
                    "substitutions": flattened.substitutions,
                    "distinct_so": len({o["codepoint"] for o in occurrences}),
                }, ensure_ascii=False) + "\n")

            record["articles_measured"] = kept
            record["occurrences"] = feed_occ
            feeds_file.write(json.dumps(record) + "\n")
            print(f"  {feed_id:38s} {kept} articles, {feed_occ} So occurrences")

    for handle in (articles_file, occ_file, feeds_file):
        handle.close()

    finished = datetime.now(tz=UTC)
    manifest = {
        "population": "measurement",
        "purpose": "frequency of Unicode So characters in real blog article text",
        "not_evidence": (
            "A denominator for a flattening rule. Nothing here is quoted, "
            "published, or merged as evidence."
        ),
        "measures": (
            "So occurrence WITHIN ARTICLES LINKED FROM THESE NINE FEEDS, in "
            "trafilatura's output under DEFAULT_EXTRACTION. Not blog prose in "
            "general. The feeds were selected for practitioner AI content, "
            "which biases the symbol mix by an unmeasured amount."
        ),
        "terms_rulings": sorted({f["terms_ruling"] for f in contract.feeds}),
        "use_basis": "internal-development-only",
        "collected_on": started.date().isoformat(),
        "delete_after": (started + timedelta(days=RETENTION_DAYS)).date().isoformat(),
        "extraction_options": "collect.adapters.blog.options.DEFAULT_EXTRACTION",
        "max_articles_per_feed": max_articles_per_feed,
        "seconds": round((finished - started).total_seconds(), 1),
        "entities_surviving_trafilatura": dict(entity_survivals),
        **totals,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print()
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "_blog_so_sweep")
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    raise SystemExit(sweep(out, limit))
