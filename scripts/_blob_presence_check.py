"""Which thread_contexts have unreadable flattened text ON THIS MACHINE.

Read-only. Touches no table and writes nothing. Run on each machine and compare
the id sets: a ref missing on one and present on the other is a SYNC GAP; a ref
missing on both is the corruption the store's message assumes.
"""
import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

from collect.config import settings  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402

store = RawStore(Path(settings().raw_store_path))
with psycopg.connect(os.environ["DATABASE_URL"]) as c:
    rows = c.execute(
        "SELECT id, flattened_text_ref, thread_root_id FROM thread_context ORDER BY id"
    ).fetchall()

missing = []
for tid, ref, root in rows:
    try:
        store.get_text(ref)
    except Exception as exc:          # PayloadMissing, ValueError, anything
        missing.append({"id": tid, "ref": ref, "root": root, "error": type(exc).__name__})

host = os.environ.get("COMPUTERNAME") or os.uname().nodename
out = Path(f"blob-check-{host}.json")
out.write_text(json.dumps({"machine": host, "total": len(rows), "missing": missing}, indent=1))
print(f"{host}: {len(rows)} thread_contexts, {len(missing)} unreadable here -> {out}")
