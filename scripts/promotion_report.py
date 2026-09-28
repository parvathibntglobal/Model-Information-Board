#!/usr/bin/env python
"""Models the corpus already has evidence about and the models page does not list.

READ-ONLY. Reads the registry, the claims and `contract/tracked_models.yaml`,
then prints a markdown report ranking every UNTRACKED model with at least one
claim. The scheduled registry poll posts it as an issue comment, so a person
sees which models have arrived on the board as a side effect of other models'
runs - Fable 5 and Qwen3.8 27B both did - and picks from the list.

    python scripts/promotion_report.py [--out report.md]

RANKED BY DISTINCT AUTHORS, THEN DISTINCT DOCUMENTS, with the claim count beside
them. Claims alone reward one prolific thread: on 2026-09-28 one model held 39
claims from 3 authors and another 105 from 18. "50 claims from 3 people" and
"50 from 27" are different facts, and the author count is the one that says how
many people reported it.

NO THRESHOLD AND NO CUT. Every untracked model with a claim is listed. The list
is the output; promotion is a person's decision (below), so nothing here says
which rows deserve it.

WHAT PROMOTION MEANS, and it is not done by this script:
  1. seat aliases with `seat()` and its collision check, so a fetch has
     something to search for - a model with no searchable alias harvests nothing;
  2. add it to `contract/tracked_models.yaml`, which puts it on the models page.
     A contract change, reviewed.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

#: GitHub refuses a comment over 65,536 characters. The report is never cut to
#: fit (the list IS the output), so a report that would not fit fails loudly
#: instead of posting a silently shorter list (rule 12).
COMMENT_LIMIT = 65_000

QUERY = """
    SELECT mv.id, mv.canonical_id, mv.display_name,
           count(*)                                       AS claims,
           count(DISTINCT cl.author_id)                   AS authors,
           count(*) FILTER (WHERE cl.author_id IS NULL)   AS claims_without_author,
           count(DISTINCT cl.document_id)                 AS documents,
           count(DISTINCT d.source)                       AS platforms,
           min(cl.created_at)::date                       AS first_claim,
           max(cl.created_at)::date                       AS last_claim,
           EXISTS (SELECT 1 FROM model_alias a
                   WHERE a.model_version_id = mv.id
                     AND a.specificity IN ('version', 'snapshot')
                     AND (a.valid_until IS NULL OR a.valid_until > now()))
                                                          AS searchable
    FROM claim cl
    JOIN model_version mv ON mv.id = cl.model_version_id
    LEFT JOIN document d ON d.id = cl.document_id
    GROUP BY mv.id, mv.canonical_id, mv.display_name
"""

FIELDS = ("model_version_id", "canonical_id", "display_name", "claims", "authors",
          "claims_without_author", "documents", "platforms", "first_claim", "last_claim",
          "searchable")


def untracked_ranked(rows: list[dict], tracked: set[str]) -> list[dict]:
    """Every row whose model is not tracked, by authors, then documents, then claims.

    TRACKED MATCHES EITHER ID, as the models page does (`judge/app.py`'s tracked
    roster keys on `canonical_id` AND `model_version_id`). Matching only the
    canonical id put Claude Fable 5.1 - tracked as `anthropic/claude-fable-5-1`,
    its row id - on this list on 2026-09-28.
    """
    out = [r for r in rows
           if r["canonical_id"] not in tracked and r["model_version_id"] not in tracked]
    out.sort(key=lambda r: (-r["authors"], -r["documents"], -r["claims"],
                            r["display_name"] or r["canonical_id"]))
    return out


def render(ranked: list[dict], *, tracked_count: int) -> str:
    no_author = sum(r["claims_without_author"] for r in ranked)
    total = sum(r["claims"] for r in ranked)
    unseated = sum(1 for r in ranked if not r["searchable"])
    out = [
        f"**Models with evidence that the models page does not list.** "
        f"{len(ranked)} untracked model(s) hold {total:,} claim(s) between them; "
        f"{tracked_count} model(s) are tracked (`contract/tracked_models.yaml`).",
        "",
        "Ranked by **distinct authors**, then **distinct documents**, with claims beside them. "
        "Every untracked model with a claim is listed - there is no threshold, and a person "
        "picks from the list.",
        "",
        "**Read the counts with these:**",
        "- **`author_id` is per platform.** One person posting on Reddit and on Hacker News "
        "counts as two authors.",
        f"- **{no_author:,} of these {total:,} claim(s) carry no author**, and add nobody to "
        "the author count.",
        "- A claim is attributed to a model by the extractor, from the document's context. "
        "Its quote does not always name the model.",
        "",
        "| # | Model | Authors | Documents | Claims | Platforms | Searchable alias "
        "| Claims dated |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(ranked, 1):
        name = r["display_name"] or r["canonical_id"]
        seat = "yes" if r["searchable"] else "**no - seat first**"
        out.append(f"| {i} | {name} (`{r['canonical_id']}`) | {r['authors']} | {r['documents']} "
                   f"| {r['claims']} | {r['platforms']} | {seat} "
                   f"| {r['first_claim']} to {r['last_claim']} |")
    out += [
        "",
        f"**{unseated} of {len(ranked)} have no searchable alias**, so a fetch for them would "
        "find no variants and harvest nothing until they are seated.",
        "",
        "**Promoting one is two steps, both by hand:** seat its aliases with `seat()`, whose "
        "collision check exists because `minimax` once matched MiniMax H3; then add it to "
        "`contract/tracked_models.yaml` in a PR, which puts it on the models page.",
    ]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args()

    import psycopg
    import yaml

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is not set; refusing rather than ranking nothing")
    sep = "&" if "?" in dsn else "?"
    dsn += sep + "options=-c%20default_transaction_read_only%3Don"
    tracked_path = ROOT / "contract" / "tracked_models.yaml"
    tracked_file = yaml.safe_load(tracked_path.read_text(encoding="utf-8"))
    tracked = {m["registry"] for m in tracked_file["models"] if m.get("registry")}
    with psycopg.connect(dsn, connect_timeout=20) as conn:
        rows = [dict(zip(FIELDS, r, strict=True)) for r in conn.execute(QUERY).fetchall()]
    report = render(untracked_ranked(rows, tracked), tracked_count=len(tracked_file["models"]))
    if len(report) > COMMENT_LIMIT:
        raise SystemExit(
            f"the report is {len(report):,} characters and a GitHub comment holds "
            f"{COMMENT_LIMIT:,}. Not posted rather than cut: the list is the output.")
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
