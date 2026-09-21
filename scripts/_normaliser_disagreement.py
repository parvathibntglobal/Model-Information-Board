"""Which normaliser is right: triage's `no-resolvable-entity` vs the finder.

READ-ONLY AND FREE. No model call, no write, no spend.

THE QUESTION, AND WHY IT IS NOT ACADEMIC

Two pieces of code answer "does this text name a tracked model", and #365 says
they disagree:

    collect/triage/entity.normalize   strips ALL punctuation and whitespace
    collect/adapters/queries/sieve    keeps both
    collect/surface_resolver          RegistrySurfaceFinder, the third reader

`triage` drops a document on `no-resolvable-entity`; `RegistrySurfaceFinder` is
what `_blog_corpus_census.py` and every naming figure in `contract/sources.yaml`
use. If they disagree, one of them is silently deciding what reaches the board,
and #365 measured 55 such documents corpus-wide before the eighteen-feed
harvest. This re-measures it on the new corpus.

WHAT THE FOUR CELLS MEAN, BECAUSE ONLY TWO ARE INTERESTING

    triage KEPT   + finder FINDS      agree, document is evidence
    triage DROPPED + finder finds nothing   agree, document is noise
    triage DROPPED + finder FINDS     ⚠ triage discards a naming document
    triage KEPT   + finder finds nothing   ⚠ triage keeps a document that
                                            names nothing the registry knows

The third cell is the expensive one: it is an absence WE cause, invisible on
any page, and it is rule 4 one stage before the board.

⚠ TRIAGE'S VERDICT IS NOT ONLY THE ENTITY GATE. A document can be dropped for
  `out-of-window` or `too-short-no-artifact` while naming a model perfectly
  well, and counting that as a normaliser disagreement would blame the wrong
  gate. So the comparison is against `no-resolvable-entity` IN
  `filter_reasons`, never against the verdict alone.

⚠ AND IT MUST READ THE SAME TEXT TRIAGE READ, which the first version of this
  script did not. `document.text_ref` for a blog document is the RAW HTML
  PAYLOAD - 117 to 138 tags per document - and `store.get_text()` hands back
  the markup. Triage does not read that: `collect/triage/run.py:_blog` runs
  `extract_article_text(raw_bytes)`, trafilatura over undecoded HTML, and
  gates the PROSE.

  Running the finder over markup and triage's verdict over prose compares two
  different questions and calls the difference a disagreement. It inflated the
  count: `weaver` matched inside `images/weaver.png` in an `og:image` tag, and
  a `Claude Opus 4.8` mention sat in a `<figcaption>`. Both are regions triage
  never saw.

  So PROSE IS THE COMPARISON and markup is reported beside it as a contrast,
  because the gap between the two is the measurement of how much markup
  pollutes a finder run - which is a real number several other scripts in this
  repo depend on without saying so.

    python scripts/_normaliser_disagreement.py
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys
import urllib.parse

import psycopg
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from collect.config import settings  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.surface_resolver import (  # noqa: E402
    RegistrySurfaceFinder,
    RegistrySurfaceResolver,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="blog")
    ap.add_argument("--out", default="_normaliser_disagreement")
    ap.add_argument("--sample", type=int, default=12)
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(exist_ok=True)

    dsn = os.environ["DATABASE_URL"]
    sep = "&" if "?" in dsn else "?"
    dsn = dsn + sep + "options=" + urllib.parse.quote("-c default_transaction_read_only=on")
    store = RawStore(pathlib.Path(settings().raw_store_path))

    with psycopg.connect(dsn, connect_timeout=15) as conn:
        finder = RegistrySurfaceFinder.from_connection(conn)
        resolver = RegistrySurfaceResolver.from_connection(conn)
        canonical = dict(conn.execute("SELECT id, canonical_id FROM model_version").fetchall())
        rows = conn.execute(
            """
            SELECT id, url, text_ref, triage_verdict, filter_reasons
            FROM document
            WHERE source = %s AND triage_verdict IS NOT NULL
            """,
            (args.source,),
        ).fetchall()

    def host_of(url: str) -> str:
        return (urllib.parse.urlparse(url or "").hostname or "?").lower()

    cells: collections.Counter = collections.Counter()
    per_feed: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    disagreements: list[dict] = []
    unreadable = 0

    from collect.adapters.blog.parse import extract_article_text

    def models_in(text: str | None) -> list[str]:
        if not text:
            return []
        ids = {resolver(s) for s in finder(text)}
        ids.discard(None)
        return sorted({canonical.get(i, i) for i in ids})

    markup_only = 0
    not_prose = 0

    for doc_id, url, ref, _verdict, reasons in rows:
        try:
            blob = store.get(ref)
            markup = store.get_text(ref)
        except Exception:                                       # noqa: BLE001
            blob = markup = None
        if not markup:
            unreadable += 1
            continue
        # TRIAGE'S OWN INPUT. `collect/triage/run.py:_blog`, raw bytes.
        try:
            prose = extract_article_text(blob)
        except Exception:                                       # noqa: BLE001
            prose = None
        if prose is None:
            not_prose += 1

        prose_models = models_in(prose)
        markup_models = models_in(markup)
        if markup_models and not prose_models:
            markup_only += 1

        finder_names = bool(prose_models)
        # ⚠ THE ENTITY GATE, NOT THE VERDICT. See the module docstring.
        entity_dropped = "no-resolvable-entity" in (reasons or [])

        cell = ("entity-dropped" if entity_dropped else "entity-passed",
                "finder-finds" if finder_names else "finder-empty")
        cells[cell] += 1
        per_feed[host_of(url)][cell] += 1
        if entity_dropped and finder_names:
            disagreements.append({
                "id": doc_id, "url": url, "host": host_of(url),
                "surfaces": sorted(set(finder(prose)))[:8],
                "models": prose_models[:6],
                "models_in_markup_only": [m for m in markup_models
                                          if m not in prose_models][:6],
                "filter_reasons": list(reasons or []),
                "prose_chars": len(prose or ""), "markup_chars": len(markup),
            })

    total = sum(cells.values())
    print(f"NORMALISER DISAGREEMENT, source={args.source}")
    print("  finder run over EXTRACTED PROSE - the same text triage gated")
    print(f"  {total} documents with a verdict and readable payload "
          f"({unreadable} unreadable, excluded)")
    print(f"  {not_prose} payload(s) yielded no prose at all")
    print(f"  ⚠ {markup_only} document(s) name a model in the MARKUP and not in "
          f"the prose\n     - those are what the first, markup-based run "
          f"counted as finder hits\n")
    print(f"  {'':<18}{'finder FINDS':>14}{'finder empty':>14}")
    for row in ("entity-passed", "entity-dropped"):
        print(f"  {row:<18}"
              f"{cells[(row, 'finder-finds')]:>14}"
              f"{cells[(row, 'finder-empty')]:>14}")
    d = cells[("entity-dropped", "finder-finds")]
    k = cells[("entity-passed", "finder-empty")]
    print(f"\n  ⚠ triage DROPPED but the finder names a model : {d}"
          f"  ({d/total*100:.1f}% of {total})")
    print(f"    triage kept but the finder names nothing     : {k}")
    print(f"    agreement                                     : "
          f"{(total-d-k)/total*100:.1f}%")

    print("\nDISAGREEMENTS BY FEED (triage dropped, finder finds)")
    print(f"  {'feed':<26}{'disagree':>9}{'verdicts':>10}{'rate':>8}")
    for host in sorted(per_feed, key=lambda h: -per_feed[h][("entity-dropped", "finder-finds")]):
        c = per_feed[host]
        n = sum(c.values())
        dd = c[("entity-dropped", "finder-finds")]
        if n:
            print(f"  {host:<26}{dd:>9}{n:>10}{dd/n*100:>7.1f}%")

    print(f"\nA SAMPLE TO READ - {min(args.sample, len(disagreements))} of {len(disagreements)}")
    for row in disagreements[: args.sample]:
        print(f"\n  {row['url'][:78]}")
        print(f"    finder surfaces : {row['surfaces']}")
        print(f"    resolves to     : {row['models']}")
        print(f"    triage reasons  : {row['filter_reasons']}")

    (out / "disagreements.json").write_text(
        json.dumps(disagreements, indent=1), encoding="utf-8"
    )
    print(f"\n  -> {out}/disagreements.json  ({len(disagreements)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
