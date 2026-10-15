r"""Concern 1 ("the evidence is thin once a threshold applies"), measured before
and after the 2026-10-14 curation proposals, WITHOUT applying them.

    python docs/measurements/board-evidence-after-curation-2026-10-14.py --dsn <url>

READ-ONLY. The proposed merges are applied IN MEMORY - a merged slug's rows are
counted under its target - so this answers "what would the threshold admit if
a person ruled every proposed merge", while the database stays unruled.

WHAT IS COUNTED. A RESULT is one (section, name, model). Its VOICES are the
distinct `document.author_id` values behind it; a row whose document has no
author adds no voice (concern 6). A result QUALIFIES at 5+ voices, the bar the
demos used. Declined names (existing rulings, and the proposed declines in the
AFTER column) are left out, as the board leaves them out.

WHAT IT CANNOT TELL YOU. A merge only pools voices already filed under two
names, so it cannot make thin evidence thick - it can only stop one subject's
evidence being split across names. Concern 1 is mostly a question of how much
has been collected; this measures how much of it the naming was hiding.

The public view leaves out reddit, x and arxiv (contract/publication.yaml).
"""

from __future__ import annotations

import argparse
import importlib.util
from collections import Counter, defaultdict
from pathlib import Path

import psycopg

PROPOSALS = Path(__file__).resolve().parents[1] / "proposals"
WITHHELD = {"reddit", "x", "arxiv"}
BAR = 5


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, PROPOSALS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", required=True)
    a = ap.parse_args()
    props = [
        load(n)
        for n in (
            "job_curation_2026_10_14",
            "capability_curation_2026_10_14",
            "metric_curation_2026_10_14",
        )
    ]
    fold = {(p.SECTION, s): t for p in props for t, (_h, m) in p.CLUSTERS.items() for s in m}
    fold.update(
        {(p.SECTION, s): t for p in props for t, m in getattr(p, "MERGES", {}).items() for s in m}
    )
    declined = {(p.SECTION, s) for p in props for s in p.DECLINE}

    with psycopg.connect(a.dsn) as c:
        rows = c.execute(
            "SELECT be.section, COALESCE(be.ruling_target, be.slug), be.model_version_id, "
            "d.author_id, d.source FROM board_entry be JOIN document d ON d.id = be.document_id "
            "WHERE be.ruling IS DISTINCT FROM 'declined'"
        ).fetchall()

    def measure(after: bool, public: bool):
        voices = defaultdict(set)
        names = defaultdict(set)
        for sec, slug, mv, author, source in rows:
            if public and source in WITHHELD:
                continue
            if after:
                if (sec, slug) in declined:
                    continue
                slug = fold.get((sec, slug), slug)
            names[sec].add(slug)
            if author is not None:
                voices[(sec, slug, mv)].add(author)
        ok = {k: len(v) for k, v in voices.items() if len(v) >= BAR}
        by_sec = Counter(k[0] for k in ok)
        bands = Counter(
            "5-9" if n < 10 else "10-19" if n < 20 else "20+"
            for k, n in ok.items()
            if k[0] != "metric"
        )
        return {
            "names": {s: len(v) for s, v in names.items()},
            "qualifying": len(ok),
            "models": len({k[2] for k in ok}),
            "by_section": dict(by_sec),
            "job_and_capability_bands": dict(bands),
        }

    for public in (False, True):
        view = "public" if public else "all sources"
        print(f"\n{view}:")
        for after in (False, True):
            r = measure(after, public)
            print(f"  {'after ' if after else 'before'}  names {r['names']}")
            print(f"          {r['qualifying']} results at {BAR}+ voices across "
                  f"{r['models']} models; by section {r['by_section']}; "
                  f"job+capability bands {r['job_and_capability_bands']}")


if __name__ == "__main__":
    main()
