#!/usr/bin/env python
"""Start the API with .env loaded.

`judge/app.py` reads os.environ and does not load .env itself, so started any
other way the database-backed pages answer 503. Values are never printed.

    python run-backend.py                # local Postgres, from DATABASE_URL
    python run-backend.py --staging      # STAGING_DATABASE_URL, forced READ ONLY
    python run-backend.py --reload

--staging forces every session read-only at the server
(`default_transaction_read_only=on`), so no code path in this process can write
to the shared database whatever it tries. The guarantee is in Postgres rather
than in a promise about which functions only SELECT.
"""
import os
import pathlib
import re
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).parent

env = ROOT / ".env"
if not env.exists():
    sys.exit("No .env — copy .env.example and fill it in. See FRONTEND.md.")

for line in env.read_text(encoding="utf-8").splitlines():
    m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
    if m:
        os.environ[m.group(1)] = m.group(2)

if "--staging" in sys.argv:
    staging = os.environ.get("STAGING_DATABASE_URL", "").strip()
    if not staging:
        sys.exit("STAGING_DATABASE_URL is not set in .env")
    sep = "&" if "?" in staging else "?"
    ro = urllib.parse.quote("-c default_transaction_read_only=on")
    os.environ["DATABASE_URL"] = f"{staging}{sep}options={ro}"
    print(f"  reading STAGING at {urllib.parse.urlparse(staging).hostname} — sessions forced READ ONLY")
else:
    print("  reading the database in DATABASE_URL")

sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402  (imported after the environment is in place)

uvicorn.run("judge.app:app", host="127.0.0.1", port=8000, reload="--reload" in sys.argv)
