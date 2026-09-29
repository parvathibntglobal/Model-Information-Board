"""Re-measure #456: the selection key, old against new, on one machine.

Read-only. Population: unread threads at the current PIPELINE_VERSION whose
thread_context has a kept document - the same population #456's table used -
counted readable on the machine that runs this.

    python scripts/_measure_selection_key_456.py --raw-store <path> --out <file.json>

For each model in #456's table: how many threads each key puts first, and how
many threads the old key put first that the new one does not.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MODELS = [  # display names as #456's table and #441 name them
    "Anthropic: Claude Fable 5", "Z.ai: GLM 5.3", "OpenAI: GPT-5.6 Luna",
    "Anthropic: Claude Opus 5.5", "Anthropic: Claude Opus 5", "Google: Gemini 2.5 Flash",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-store", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import psycopg
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    import scripts.fetch_model as fm
    from collect.rawstore import RawStore
    from collect.registry.aliases import normalize
    from judge.store.extractions import PIPELINE_VERSION

    store = RawStore(Path(args.raw_store))
    with psycopg.connect(os.environ["DATABASE_URL"],
                         options="-c default_transaction_read_only=on") as conn:
        rows = conn.execute(
            "SELECT tc.id, tc.flattened_text_ref FROM thread_context tc "
            "WHERE EXISTS (SELECT 1 FROM document d "
            "              WHERE d.id = ANY(tc.member_document_ids) AND d.status = 'kept') "
            "  AND NOT EXISTS (SELECT 1 FROM thread_extraction te "
            "                  WHERE te.thread_context_id = tc.id "
            "                    AND te.pipeline_version = %s "
            "                    AND te.content_fingerprint IS NOT NULL)",
            (PIPELINE_VERSION,),
        ).fetchall()
        texts = {}
        for tc_id, ref in rows:
            with contextlib.suppress(Exception):  # payload not on this machine
                texts[tc_id] = store.get_text(ref)
        result = {"measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
                  "pipeline_version": PIPELINE_VERSION,
                  "population_unread_kept": len(rows), "readable_here": len(texts),
                  "models": []}
        for name in MODELS:
            row = conn.execute("SELECT id, canonical_id FROM model_version WHERE display_name = %s",
                               (name,)).fetchone()
            if row is None:
                result["models"].append({"model": name, "absent": True})
                continue
            mv, canonical = row
            surfaces = fm._variants_for(conn, mv, canonical)
            longer = fm.longer_registry_surfaces(conn, mv, surfaces)
            keys = {normalize(x) for x in surfaces if x and len(normalize(x)) >= 4}
            old = {t for t, x in texts.items() if keys and any(k in normalize(x) for k in keys)}
            own = fm._compile_surfaces([x for x in surfaces if x and len(normalize(x)) >= 4])
            longer_rx = fm._compile_surfaces(longer)
            new = {t for t, x in texts.items() if fm.names_the_model(x, own, longer_rx)}
            result["models"].append({
                "model": name, "model_version_id": mv, "surfaces": surfaces,
                "longer_subtracted": longer,
                "old_key_first": len(old), "new_key_first": len(new),
                "old_only": len(old - new), "new_only": len(new - old),
                "old_only_ids": sorted(old - new)[:40],
            })
    Path(args.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "models"}))
    for m in result["models"]:
        print({k: m.get(k) for k in ("model", "old_key_first", "new_key_first", "old_only",
                                     "new_only", "absent")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
