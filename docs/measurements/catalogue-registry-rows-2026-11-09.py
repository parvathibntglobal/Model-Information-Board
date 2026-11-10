# ruff: noqa: E501
"""Catalogue models with no registry row: how many a `catalogued` seat would take, and what the
existing alias rules would refuse. READ-ONLY (default_transaction_read_only=on); writes nothing.

    DATABASE_URL=<shared registry> python docs/measurements/catalogue-registry-rows-2026-11-09.py OUT.json

POPULATION: every `model_catalog` row (OpenRouter's catalogue as last polled) whose canonical id has
no `model_version` row, on the day it runs.

IN SCOPE (anooj, 2026-11-09): output kinds text, image, speech, transcription, video and
decisions. Out: embeddings and rerank, which the board does not report on. The kind is read from
OpenRouter's published `output_modalities`, never guessed from the name. Set apart and counted:
`:free` listings (the model they are free of) and `openrouter/*` routers (not models).

THE SURFACE a seat would use is the catalogue `name` with its "Provider: " prefix and a trailing
"(free)" removed, lowercased - the same cleaning judge/news.py `_clean_name` applies.

WHAT EACH COUNT MEANS
  specificity   collect/registry/aliases.py `classify_specificity` on that surface: snapshot (it
                is the id's local part), version (it has a digit), family (neither). A family
                row resolves at family specificity, which CLAUDE.md records as a pending ruling,
                so family-specificity names are counted apart and would NOT be seated.
  one_word_no_digit  a single word with no digit ("sora", "muse"): rule 10's ordinary-word case.
                Even as a snapshot it can be an English word, so it is counted apart and would
                not be seated without a person's look.
  collides_existing  the surface's normalised key equals an alias key already in `model_alias`
                for a DIFFERENT model - the loader's collision check would refuse it.
  collides_in_batch  two in-scope catalogue models normalise to the same key.
  held_entries  `unresolved_entry` rows still held whose folded surface equals the key - claims
                that would file on seating (a floor: unseated models are never searched for).
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from collect.registry.aliases import local_part, normalize  # noqa: E402

IN_SCOPE = {"text", "image", "speech", "transcription", "video", "decisions"}
_PREFIX = re.compile(r"^[^:]{1,40}:\s+")
_FREE = re.compile(r"\s*\(free\)\s*$", re.I)


def kind(mods: list[str]) -> str:
    m = set(mods or [])
    for k in ("speech", "transcription", "video", "image", "decisions", "embeddings", "rerank"):
        if k in m:
            return k
    if "audio" in m:
        return "audio"
    return "text" if "text" in m else ("+".join(sorted(m)) or "unknown")


def specificity(surface: str, canonical_id: str) -> str:
    key = normalize(surface)
    if key in {normalize(canonical_id), normalize(local_part(canonical_id))}:
        return "snapshot"
    return "version" if re.search(r"\d", key) else "family"


def main(out_path: str) -> int:
    dsn = os.environ["DATABASE_URL"]
    dsn += ("&" if "?" in dsn else "?") + "options=-c%20default_transaction_read_only%3Don"
    with psycopg.connect(dsn, connect_timeout=30) as c:
        rows = c.execute("""
            SELECT mc.canonical_id, mc.provider, mc.name, mc.output_modalities, mc.listed_at
              FROM model_catalog mc LEFT JOIN model_version mv ON mv.canonical_id = mc.canonical_id
             WHERE mv.id IS NULL ORDER BY mc.canonical_id""").fetchall()
        catalogue_total = c.execute("SELECT count(*) FROM model_catalog").fetchone()[0]
        alias_owner = defaultdict(set)
        for key, cid in c.execute("""SELECT a.normalized, mv.canonical_id FROM model_alias a
                                     JOIN model_version mv ON mv.id = a.model_version_id
                                     WHERE a.valid_until IS NULL OR a.valid_until > now()"""):
            alias_owner[key].add(cid)
        held = Counter(normalize(s) for (s,) in c.execute(
            "SELECT surface FROM unresolved_entry WHERE attributed_at IS NULL"))

    by_kind = Counter(kind(m) for _, _, _, m, _ in rows)
    # NOT SEPARATE MODELS, counted apart: a `:free` listing is the model it is free
    # of (judge/news.py `model_names` treats it so), and `openrouter/*` ids are
    # routers that pick a model per request.
    free_listings = [r for r in rows if r[0].endswith(":free") and kind(r[3]) in IN_SCOPE]
    routers = [r for r in rows if r[1] == "openrouter" and kind(r[3]) in IN_SCOPE]
    scoped = [r for r in rows if kind(r[3]) in IN_SCOPE
              and not r[0].endswith(":free") and r[1] != "openrouter"]
    batch_keys = defaultdict(list)
    recs = []
    for cid, _provider, name, mods, listed in scoped:
        surface = _FREE.sub("", _PREFIX.sub("", name or "")).strip().lower()
        key = normalize(surface)
        batch_keys[key].append(cid)
        recs.append({"id": cid, "kind": kind(mods), "surface": surface, "key": key,
                     "specificity": specificity(surface, cid),
                     "one_word_no_digit": " " not in surface.strip() and not re.search(r"\d", surface),
                     "collides_existing": sorted(alias_owner.get(key, set()) - {cid}),
                     "held_entries": held.get(key, 0),
                     "listed": listed.date().isoformat() if listed else None})
    for r in recs:
        r["collides_in_batch"] = sorted(set(batch_keys[r["key"]]) - {r["id"]})
        r["seatable"] = (r["specificity"] != "family" and not r["one_word_no_digit"]
                         and not r["collides_existing"] and not r["collides_in_batch"])

    def tally(pred):
        sel = [r for r in recs if pred(r)]
        return {"n": len(sel), "by_kind": dict(Counter(r["kind"] for r in sel).most_common())}

    out = {
        "measured_on": "2026-11-09",
        "catalogue_rows": catalogue_total,
        "no_registry_row": len(rows),
        "no_registry_row_by_kind": dict(by_kind.most_common()),
        "in_scope_kinds": sorted(IN_SCOPE),
        "set_apart_free_listings": len(free_listings),
        "set_apart_routers": [r[0] for r in routers],
        "in_scope": tally(lambda r: True),
        "would_seat": tally(lambda r: r["seatable"]),
        "refused_family_specificity": tally(lambda r: r["specificity"] == "family"),
        "refused_one_word_no_digit": tally(lambda r: r["one_word_no_digit"]),
        "refused_collides_existing": tally(lambda r: bool(r["collides_existing"])),
        "refused_collides_in_batch": tally(lambda r: bool(r["collides_in_batch"])),
        "listed_since_2026_10_01": tally(lambda r: (r["listed"] or "") >= "2026-10-01"),
        "held_entries_that_would_file": sum(r["held_entries"] for r in recs if r["seatable"]),
        "refused_examples": {
            "family": [r["id"] for r in recs if r["specificity"] == "family"][:12],
            "one_word_no_digit": [r["id"] for r in recs if r["one_word_no_digit"]][:12],
            "collides_existing": [[r["id"], r["collides_existing"]] for r in recs if r["collides_existing"]][:12],
            "collides_in_batch": [[r["id"], r["collides_in_batch"]] for r in recs if r["collides_in_batch"]][:12],
        },
        "models": recs,
    }
    Path(out_path).write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k in ("catalogue_rows", "no_registry_row", "set_apart_free_listings", "set_apart_routers",
              "in_scope", "would_seat", "refused_family_specificity",
              "refused_one_word_no_digit", "refused_collides_existing", "refused_collides_in_batch",
              "listed_since_2026_10_01", "held_entries_that_would_file"):
        print(k, json.dumps(out[k]))
    print("examples", json.dumps(out["refused_examples"])[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
