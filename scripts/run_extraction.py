"""The composition root for extraction: the one place both lanes meet.

WHY THIS FILE EXISTS, AND WHY IT IS NOT IN EITHER LANE
-----------------------------------------------------
`judge extract` verified quotes and stored NOTHING for the whole of the
pipeline's life. The cause was never a defect in a stage — it was a missing
composition root.

Model identity resolution is code's, not the model's (rule 2: an LLM may
propose, it may never decide). So the extractor proposes a SURFACE — "sonnet 4",
exactly as a human wrote it — and something maps that surface to a
`model_version.id`. That something is `collect/`'s `RegistrySurfaceResolver`,
which owns the surface population and its normalisation.

But `judge/` may not import `collect/`, and `collect/` may not import `judge/` —
`tests/test_lane_boundary.py` enforces both directions with no allowlist. So
neither lane can wire the resolver into the pipeline. `scripts/` is outside both
lanes and the boundary test does not cover it, which is exactly what a
composition root is for: it imports both sides and hands `collect/`'s resolver
to `judge/`'s extraction as the `resolver_factory` the CLI leaves `None`.

The design chose a CALLABLE across the boundary rather than a materialised
table, and this is the callable being supplied. `judge.pipeline.SurfaceResolver`
records why: a table would have to agree with `collect/`'s normalisation and
would rot silently when it changed; the callable carries the normalisation with
it and cannot drift from the population it reads.

WHAT IT DOES NOT DO
-------------------
It adds no new machinery. Budget, ledger seeding, dedup, the nightly close and
the run report all live in `judge/cli.py:_cmd_extract`; this only supplies the
one dependency that lane cannot build for itself. Everything else — the spend
cap, `--dry-run`, `--driver`, `--from-export` — is the CLI's, unchanged.

    py -3 scripts/run_extraction.py --from-export _handoff/threads --driver new-evidence
    py -3 scripts/run_extraction.py --from-export _handoff/threads --dry-run

Reads the raw store for thread text, so it runs where the store is present. On a
machine without it, `--from-export` supplies the text inline (a named stopgap;
see `judge/extract/export_source.py`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from collect.surface_resolver import RegistrySurfaceResolver  # noqa: E402
from judge.cli import _cmd_extract  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run extraction with the registry resolver wired.")
    parser.add_argument("--from-export", metavar="DIR", required=True,
                        help="threads exported with inlined text (judge/extract/export_source.py)")
    parser.add_argument("--dry-run", action="store_true", help="spend nothing")
    parser.add_argument("--driver", default=None,
                        help="why labels may change this run (e.g. new-evidence)")
    args = parser.parse_args(argv)

    # THE ONE LINE THAT CROSSES THE BOUNDARY. `_cmd_extract` builds the resolver
    # from the connection it opens, so it stays in sync with `model_version` for
    # this exact run rather than a snapshot taken here.
    return _cmd_extract(args, resolver_factory=RegistrySurfaceResolver.from_connection)


if __name__ == "__main__":
    raise SystemExit(main())
