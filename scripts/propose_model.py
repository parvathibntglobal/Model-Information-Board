"""What adding or dropping a tracked model would mean. Writes nothing.

    python scripts/propose_model.py --add    --name "Gemini 4 Flash" \\
                                   --registry google/gemini-4-flash
    python scripts/propose_model.py --untrack --registry openai/gpt-5.5

Prints JSON on stdout for `/admin/models/propose`.

⚠ THIS EXISTS BECAUSE `judge/` MAY NOT IMPORT `collect/`, and everything the
  preview needs lives on the collect side: `query_variants` is the project's own
  speller and `model_version_id` is the id function the registry keys on. The
  lane boundary is one-directional and an AST test enforces it, so the admin
  endpoint runs this as a subprocess — the same pattern `/fetch/start` and
  `/admin/keywords` already use.

⚠ AND IT WRITES NOTHING, WHICH IS THE WHOLE DESIGN.

  A model reaches the board through `contract/tracked_models.yaml` — versioned
  config, rule 5 — so a button that wrote the list somewhere else would put it
  in two places that can disagree, with the second copy carrying no review, no
  diff and no history. On Railway it would be worse than that: the filesystem is
  ephemeral, so a YAML edit made by the hosted UI dies at the next deploy while
  any database rows it caused survive. That is the contract and the database
  disagreeing, which is the shape of the Recraft mess.

  So this does the tedious, checkable half — derive the spellings, count what
  the corpus already attests, find collisions, and compose the exact contract
  entry — and a person commits it. The reviewable step stays reviewable.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import psycopg
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.ids import model_version_id  # noqa: E402
from collect.registry.aliases import normalize, query_variants  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TRACKED = ROOT / "contract" / "tracked_models.yaml"

#: The three renderings `check_spelling_coverage` demands of every model. Named
#: here so the preview can say WHICH one is missing rather than "coverage failed".
RENDERINGS = ("spaced", "hyphenated", "concatenated")


def _renderings(surface: str, variants: list[str]) -> dict[str, str | None]:
    """Which of the three spellings the generator actually produced.

    Reported per rendering rather than as a boolean, because a model the poll
    cannot find is found by a HUMAN typing one of these, and knowing which one
    is missing is the difference between a fixable gap and a failed check.
    """
    lowered = [v.lower() for v in variants]
    found: dict[str, str | None] = dict.fromkeys(RENDERINGS)
    for variant in lowered:
        if " " in variant:
            found["spaced"] = found["spaced"] or variant
        elif "-" in variant:
            found["hyphenated"] = found["hyphenated"] or variant
        elif variant == normalize(surface):
            found["concatenated"] = found["concatenated"] or variant
    return found


def _attestation(conn, variants: list[str]) -> dict[str, object]:
    """How often each spelling already appears in evidence we hold.

    ⚠ RULE 7, AND THE DENOMINATOR IS SMALLER THAN IT LOOKS. This counts
      `board_entry.quote` and nothing else, because that is the only document
      TEXT in the shared database: `document.text_ref` and
      `thread_context.flattened_text_ref` are content-addressed pointers into a
      per-machine raw store, and this machine cannot read 30.8% of it (#321).

      So a count of 0 here means "not in the extracted quotes", NOT "nobody has
      written this" — those are opposite claims and only one is about the world.
      The payload carries the denominator so the page can say which it is.
    """
    total = conn.execute("SELECT count(*) FROM board_entry").fetchone()[0]
    counts = []
    for variant in variants:
        # Case-insensitive substring. Not a word-boundary match: "gpt5.5codex"
        # has no word boundaries to speak of, and over-counting a spelling is a
        # smaller error here than missing one.
        n = conn.execute(
            "SELECT count(*) FROM board_entry WHERE quote ILIKE %s",
            (f"%{variant}%",),
        ).fetchone()[0]
        counts.append({"variant": variant, "quotes": n})
    return {
        "counts": counts,
        "searched": total,
        "corpus": "board_entry.quote",
        "note": (
            f"Counted across {total} extracted quotes - the only document text "
            f"the shared database holds. Raw document text is content-addressed "
            f"into a per-machine store, so a zero here means 'not in the "
            f"extracted quotes', not 'nobody has written it'."
        ),
    }


def _collisions(conn, variants: list[str], mv_id: str) -> list[dict]:
    """Spellings already live for a DIFFERENT model.

    The one hard failure in adding a model: an alias that resolves to somebody
    else's row does not add evidence, it MISFILES it, and `model_alias` is
    append-only under FR-4 so there is no undo.
    """
    found = []
    for variant in variants:
        rows = conn.execute(
            "SELECT model_version_id, surface FROM model_alias "
            "WHERE normalized = %s AND model_version_id <> %s",
            (normalize(variant), mv_id),
        ).fetchall()
        for owner, surface in rows:
            found.append({"variant": variant, "held_by": owner, "as": surface})
    return found


def _tracked_entries() -> list[dict]:
    raw = yaml.safe_load(TRACKED.read_text(encoding="utf-8")) or {}
    return list(raw.get("models") or [])


def _contract_entry(name: str, registry: str, kind: str) -> str:
    """The exact YAML to paste. Composed, never guessed at."""
    return (
        f"  - name: {name}\n"
        f"    registry: {registry}\n"
        f"    kind: {kind}\n"
    )


def _add(conn, name: str, registry: str, kind: str) -> dict:
    surface = name.strip()
    variants = query_variants(surface)
    mv_id = model_version_id(registry)
    tracked = _tracked_entries()

    row = conn.execute(
        "SELECT id, canonical_id, display_name, provenance FROM model_version "
        "WHERE canonical_id = %s OR id = %s",
        (registry, mv_id),
    ).fetchone()

    return {
        "action": "add",
        "name": surface,
        "registry": registry,
        "kind": kind,
        "model_version_id": mv_id,
        "variants": variants,
        "renderings": _renderings(surface, variants),
        # ⚠ RULE 2. Everything above is DERIVED - a pure function of the name -
        # and everything below is MEASURED. Nothing here is a judgement, and the
        # one judgement that exists (is this what people call it) is left to the
        # person reading the attestation counts.
        "attestation": _attestation(conn, variants),
        "collisions": _collisions(conn, variants, mv_id),
        "already_tracked": any(
            (e.get("registry") or "") == registry for e in tracked
        ),
        "in_registry": bool(row),
        "registry_row": (
            {"id": row[0], "canonical_id": row[1], "display_name": row[2],
             "provenance": row[3]} if row else None
        ),
        # ⚠ RULE 4. A model with no registry row CANNOT be fetched - a run is
        # filed under a model_version_id - so this is the blocking fact, said
        # rather than left for the first empty fetch to reveal.
        "blocking": (
            None if row else
            "No row in `model_version` for this id, so a fetch has nothing to "
            "file against. It needs seating first - the poll will do it if "
            "OpenRouter carries the model, otherwise contract/unpolled_models.yaml."
        ),
        "contract_entry": _contract_entry(surface, registry, kind),
        "contract_file": "contract/tracked_models.yaml",
        "wrote_nothing": True,
    }


def _untrack(conn, registry: str) -> dict:
    """What dropping a model from the board would and would NOT remove.

    ⚠ "DELETE" IS THE WRONG WORD AND THE PAGE MUST NOT USE IT. `model_alias` is
      append-only under FR-4 with no undo, the registry row stays, and every
      claim, board entry and document stays. What changes is one list: which
      models the board SHOWS. Everything below is the evidence for that sentence.
    """
    tracked = _tracked_entries()
    entry = next((e for e in tracked if (e.get("registry") or "") == registry), None)
    mv_id = model_version_id(registry)

    row = conn.execute(
        "SELECT id FROM model_version WHERE canonical_id = %s OR id = %s",
        (registry, mv_id),
    ).fetchone()
    ids = [i for i in {registry, mv_id, row[0] if row else None} if i]

    def _count(table: str, column: str) -> int:
        return conn.execute(
            f"SELECT count(*) FROM {table} WHERE {column} = ANY(%s)",  # noqa: S608
            (ids,),
        ).fetchone()[0]

    return {
        "action": "untrack",
        "registry": registry,
        "name": (entry or {}).get("name"),
        "tracked": entry is not None,
        "contract_file": "contract/tracked_models.yaml",
        "remove_lines": (
            _contract_entry(entry["name"], registry, entry.get("kind", "text"))
            if entry else None
        ),
        # WHAT SURVIVES, counted rather than asserted.
        "stays": {
            "model_version": 1 if row else 0,
            "model_alias": _count("model_alias", "model_version_id"),
            "claim": _count("claim", "model_version_id"),
            "board_entry": _count("board_entry", "model_version_id"),
            "cell": _count("cell", "model_version_id"),
            "fetch_log": conn.execute(
                "SELECT count(DISTINCT run_id) FROM fetch_log "
                "WHERE model_version_id = ANY(%s)", (ids,),
            ).fetchone()[0],
        },
        "stays_note": (
            "Nothing in this list is deleted. `model_alias` is append-only under "
            "FR-4 and has no undo; the rest is evidence somebody collected. "
            "Untracking removes the model from the board's list and nothing else, "
            "which is why the control says `Stop tracking` and not `Delete`."
        ),
        "wrote_nothing": True,
    }


def _recallable(conn) -> dict:
    """Models the board USED to list and no longer does.

    ⚠ THE SOURCE IS GIT, NOT THE DATABASE, AND THE ALTERNATIVES WERE MEASURED.

      "Has evidence but is not tracked" returns 71 models, almost all of which
      were never tracked - a `board_entry` accrues for any model MENTIONED in a
      thread, so GPT-4o-mini shows up with 11 entries having never been on the
      board. "Has seated aliases" returns 40, which is better and still wrong:
      seating prepares a model, it does not list one.

      The only record of what the board actually showed is the history of
      `contract/tracked_models.yaml`. Nine commits have touched it. Reading the
      file at each one and differencing the sets is exact, where both database
      signals are proxies that answer a different question.

    ⚠ RULE 4 WHERE GIT IS NOT THERE. The deployment's image excludes `.git/`,
      so this cannot be answered in the container - and an empty list would read
      as "nothing was ever dropped", which is the one thing it does not mean. It
      returns `readable: false` and says why instead.
    """
    import subprocess

    def _git(*args: str) -> str | None:
        try:
            done = subprocess.run(  # noqa: S603
                ["git", *args], cwd=str(ROOT),
                capture_output=True, text=True, timeout=30,
            )
        except Exception:  # noqa: BLE001
            return None
        return done.stdout if done.returncode == 0 else None

    log = _git("log", "--format=%H", "--follow", "--", str(TRACKED.relative_to(ROOT)))
    if log is None:
        return {
            "action": "recallable",
            "readable": False,
            "why": (
                "No git checkout to read here, so what the board used to list "
                "cannot be recovered. That is an absence on this machine, not a "
                "statement that nothing was ever dropped."
            ),
            "wrote_nothing": True,
        }

    current = {e.get("registry"): e for e in _tracked_entries() if e.get("registry")}
    # registry -> the entry as it last appeared, so a recall can restore the
    # NAME and KIND somebody chose rather than inventing new ones.
    ever: dict[str, dict] = {}
    for sha in log.split():
        blob = _git("show", f"{sha}:{TRACKED.relative_to(ROOT).as_posix()}")
        if not blob:
            continue
        try:
            parsed = yaml.safe_load(blob) or {}
        except yaml.YAMLError:
            continue
        for entry in parsed.get("models") or []:
            registry = entry.get("registry")
            if registry and registry not in ever:
                ever[registry] = entry

    dropped = []
    for registry, entry in sorted(ever.items()):
        if registry in current:
            continue
        mv_id = model_version_id(registry)
        ids = [registry, mv_id]
        row = conn.execute(
            "SELECT id, display_name FROM model_version "
            "WHERE canonical_id = %s OR id = %s", (registry, mv_id),
        ).fetchone()
        if row:
            ids.append(row[0])
        dropped.append({
            "name": entry.get("name") or registry,
            "registry": registry,
            "kind": entry.get("kind", "text"),
            "in_registry": bool(row),
            # WHAT COMES BACK WITH IT. Bringing a model back does not re-harvest
            # it: the evidence never left, so a recall is immediately a page
            # with something on it - or immediately an empty one, and knowing
            # which before you commit is the point of showing these.
            "survives": {
                "model_alias": conn.execute(
                    "SELECT count(*) FROM model_alias WHERE model_version_id = ANY(%s)",
                    (ids,),
                ).fetchone()[0],
                "board_entry": conn.execute(
                    "SELECT count(*) FROM board_entry WHERE model_version_id = ANY(%s)",
                    (ids,),
                ).fetchone()[0],
                "runs": conn.execute(
                    "SELECT count(DISTINCT run_id) FROM fetch_log "
                    "WHERE model_version_id = ANY(%s)", (ids,),
                ).fetchone()[0],
            },
        })

    return {
        "action": "recallable",
        "readable": True,
        "models": dropped,
        "count": len(dropped),
        # ⚠ RULE 7. Out of how many the file has ever held, across how many
        # commits - so "18 dropped" is not read as "18 models exist".
        "ever_tracked": len(ever),
        "commits_read": len(log.split()),
        "currently_tracked": len(current),
        "note": (
            "Read from the history of contract/tracked_models.yaml - the only "
            "record of what the board actually listed. Bringing one back is the "
            "same contract edit as adding it, and its evidence never left."
        ),
        "wrote_nothing": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--add", action="store_true")
    mode.add_argument("--untrack", action="store_true")
    mode.add_argument("--recallable", action="store_true")
    ap.add_argument("--name", default="")
    ap.add_argument("--registry", default="")
    ap.add_argument("--kind", default="text")
    args = ap.parse_args()

    registry = args.registry.strip()
    # The id shape the registry uses everywhere: `provider/model`. Refused here
    # rather than accepted and silently never matching anything.
    if not args.recallable and not re.fullmatch(
        r"[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*", registry
    ):
        print(json.dumps({
            "error": f"{registry!r} is not a canonical id. Expected "
                     f"`provider/model`, lowercase - the shape "
                     f"`model_version.canonical_id` uses."
        }))
        return 1
    if args.add and not args.name.strip():
        print(json.dumps({"error": "--add needs --name: the surface people type."}))
        return 1

    url = os.getenv("DATABASE_URL")
    if not url:
        print(json.dumps({"error": "DATABASE_URL is not set in this process."}))
        return 1

    # THE WRITEGUARD, BEFORE THE CONNECTION (#328). This writes registry rows
    # to whatever DATABASE_URL names, and the guard lived only in
    # `judge/cli.py`'s connection helper, which a script never passes through.
    from judge.writeguard import check as writeguard_check
    writeguard_check(url, command="propose_model.py")

    with psycopg.connect(url, connect_timeout=15) as conn:
        if args.recallable:
            out = _recallable(conn)
        elif args.add:
            out = _add(conn, args.name, registry, args.kind)
        else:
            out = _untrack(conn, registry)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
