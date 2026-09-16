#!/usr/bin/env python
"""The search terms each platform is sent, per tracked model, as JSON on stdout.

WHY A SCRIPT AND NOT A FUNCTION `judge/app.py` CALLS
----------------------------------------------------
`judge/` may not import `collect/`. The boundary is one-directional and
`tests/test_lane_boundary.py` enforces it with an AST scan that catches a lazy
in-function import as readily as a top-level one - and it caught this endpoint's
first draft, which imported the query planner directly.

The composition genuinely needs the collect lane:

    collect/adapters/queries/github.py:plan_searches   the real GitHub queries
    collect/adapters/x.py:club_surfaces                the one clubbed X query
    scripts/fetch_model.py:_variants_for               the alias read
    scripts/fetch_model.py:_order_variants             the order every arm slices

Duplicating any of that in `judge/` is the "two descriptions of one thing" this
project has paid for four times - and here it would be worse than usual, because
a page whose whole claim is "these are the terms that go out" is wrong the
moment its copy drifts.

So the same shape `POST /fetch/start` already uses: a script outside both lanes,
run as a subprocess. `scripts/` is neither lane - `fetch_model.py` states the
rule it relies on, *"the store reader lives in collect/, judge/ may not import
it, but a script outside both lanes may"*.

    python scripts/dump_keywords.py

READ-ONLY. One SELECT per tracked model against `model_alias`, and nothing else
touches the database.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# `.env` only when the caller has not already supplied a DSN. The backend runs
# this as a subprocess with its own environment copied in, so respecting what is
# already set is what keeps the script reading the SAME database as the page.
if not os.getenv("DATABASE_URL"):
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
            if m:
                os.environ.setdefault(m.group(1), m.group(2))


def build() -> dict:
    import psycopg

    from collect.adapters.queries.contract import load_queries
    from collect.adapters.queries.github import plan_searches
    from collect.adapters.x import club_surfaces
    from judge.config import tracked_models

    import scripts.fetch_model as fm

    # The budgets, read from the call sites rather than restated. `_variants_for`
    # is what the harvest calls, so a model whose aliases change shows different
    # terms here immediately.
    arms = [
        {"id": "github", "stage": "E2", "label": "GitHub", "budget": None,
         "budget_note": "one request per searchable alias × query",
         "how": ("the other spellings are not searched separately - they ride "
                 "along and filter the RESULTS"),
         "from": "scripts/fetch_model.py:harvest_github"},
        {"id": "reddit", "stage": "E2R", "label": "Reddit", "budget": 3,
         "budget_note": "top 3 variants",
         "how": "search, then the comment tree of up to 5 posts",
         "from": "scripts/fetch_model.py:2282"},
        {"id": "x", "stage": "E2X", "label": "X", "budget": 6,
         "budget_note": "up to 6, clubbed into ONE query",
         "how": "a single OR query, because this quota is a tenth of Reddit's",
         "from": "scripts/fetch_model.py:2295"},
        {"id": "arxiv", "stage": "E2A", "label": "arXiv", "budget": 2,
         "budget_note": "top 2 variants", "how": "one search per variant",
         "from": "scripts/fetch_model.py:2288"},
    ] + [
        {"id": pid, "stage": sid, "label": name.split("·")[-1].strip(),
         "budget": cap, "budget_note": f"top {cap} variant(s)",
         "how": "one search per variant",
         "from": "scripts/fetch_model.py:UNIFORM_PLATFORMS"}
        for pid, sid, name, cap in fm.UNIFORM_PLATFORMS
    ] + [
        {"id": "blogs", "stage": "E2B", "label": "Blogs", "budget": 0,
         "budget_note": "no per-model search",
         "how": "the feeds are read whole, not queried for one model",
         "from": "scripts/fetch_model.py:harvest_blogs"},
    ]

    queries = load_queries()
    entries = [e for cap in fm.CAPABILITIES for e in queries.for_capability(cap)]
    capability_queries = [
        {
            "capability": cap,
            "stance": getattr(entry, "stance", None),
            "topic": list(entry.terms.topic),
            "signal": list(entry.terms.signal),
        }
        for cap in fm.CAPABILITIES
        for entry in queries.for_capability(cap)
    ]

    models = []
    conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=15)
    try:
        for want in tracked_models():
            cid = want.registry
            if not cid:
                models.append({
                    "name": want.name, "canonical_id": None, "variants": [],
                    "searches_nothing": True,
                    "why": "no registry row, so no aliases to search",
                    "per_platform": {}, "github_queries": [],
                    "github_request_count": 0,
                })
                continue
            row = conn.execute(
                "SELECT id FROM model_version WHERE canonical_id = %s", (cid,)
            ).fetchone()
            mv = row[0] if row else cid
            variants = fm._variants_for(conn, mv, cid)

            per: dict[str, object] = {}
            for arm in arms:
                b = arm["budget"]
                if b == 0:
                    per[arm["id"]] = []
                elif arm["id"] == "x":
                    clubbed = club_surfaces(variants, limit=b)
                    per[arm["id"]] = [clubbed.query] if clubbed.query else []
                elif b is None:
                    per[arm["id"]] = list(variants)
                else:
                    per[arm["id"]] = variants[:b]

            github_queries = []
            if variants:
                try:
                    plan = plan_searches(entries, variants, scope=fm.SCOPE)
                    github_queries = [
                        {
                            "query": r.query,
                            "alias": getattr(r, "alias", None),
                            "entry": getattr(r, "entry_label", None),
                            "narrowing_token": getattr(r, "narrowing_token", None),
                        }
                        for r in plan.requests
                    ]
                except Exception:  # noqa: BLE001 - one model must not blank the page
                    github_queries = []

            models.append({
                "name": want.name,
                "canonical_id": cid,
                "variants": variants,
                # ⚠ RULE 4. Zero terms is a fetch that searches NOTHING - not a
                # model nobody discusses. Those look identical on a results page
                # and are opposite claims about the world.
                "searches_nothing": not variants,
                "why": (None if variants else
                        "no seated alias, so a fetch would search no terms"),
                "per_platform": per,
                "github_queries": github_queries,
                # SAID, because "6 requests from 3 variants" reads as a bug until
                # you know two spellings can share one request.
                "github_request_count": len(github_queries),
            })
    finally:
        conn.close()

    return {
        "arms": arms,
        "capability_queries": capability_queries,
        "scope": list(fm.SCOPE),
        "models": models,
        "count": len(models),
        "ordering_note": (
            "Every arm takes the FIRST n variants, so their order decides what "
            "is searched. Distinct surfaces are promoted ahead of re-spellings "
            "of one surface - a model whose variants are one phrase punctuated "
            "four ways spends every slot on the same phrase."
        ),
    }


def main() -> int:
    json.dump(build(), sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
