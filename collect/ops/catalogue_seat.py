"""Registry rows for catalogue models: evidence filed, no daily fetch (#616).

THE PROBLEM. The registry poll seats only what OpenRouter's main model list carries, and
`auto_track` admits only `polled` rows, so a model in OpenRouter's CATALOGUE that the poll never
brings - every media model, among others - had no `model_version` row. Its claims were dropped,
and since #612 held. ElevenLabs v4 had 255 documents and 0 board entries (2026-11-09).

THE FIX. A row with `provenance = 'catalogued'` for each in-scope catalogue model that has none,
so a claim found in a thread we already read is FILED. A registry row, never a tracked model:
nothing here touches `tracked_models.yaml`, and `auto_track`'s query requires `polled`
(judge/tracked.py `ELIGIBLE`), so a catalogued row can never start a daily fetch.

WHY collect/ops AND NOT collect/registry. The registry package never imports
harvest code (FR-5, tests/test_lane_boundary.py), and this module needs `name_forms`
from collect/adapters/queries/sieve.py - the same name parser the resolver uses, so
a seated key is the key extraction will look up. FR-5's guarantee still holds: the
only input here is `model_catalog` (OpenRouter's listing). No `document`, `claim` or
thread text is read, so no post can cause a registry write.

THE ORDER OF PROVENANCE (Parvathi's review on #616): polled > seed / unpolled > catalogued.
  - This writer NEVER touches an existing row: `INSERT ... ON CONFLICT DO NOTHING`, counted.
  - The poll upgrades a catalogued row it later brings: openrouter.py's upsert sets
    `provenance = 'polled'` on conflict.
  - It does not go through `load_seed`, which accepts hand-written provenance only and whose
    downgrade guard looks at hand-written values only. It calls the same CHECKS directly.

SET ASIDE, NEVER FORCED - each with its reason, for a person:
  - `:free`, `:batch` and every other `:` listing (of the model before the colon),
    `openrouter/*` routers, and `~...-latest` pointers (whichever model is current): not
    models. #616's 392 (2026-11-09) counted the listings and pointers; this writer's
    read-only plan on the shared database found 262 to seat on 2026-11-10.
  - kinds outside text, image, speech, transcription, video, decisions (anooj, 2026-11-09).
  - no usable name form: `name_forms` keeps a form only at 3+ characters, and a one-word form
    only with a digit (rule 10's ordinary-word case: "Sonar", "Reflex").
  - family specificity: a digitless name that is not the id's local part resolves only at
    family level, a pending ruling in CLAUDE.md.
  - a name whose key another model already owns, or that two candidates fold to.
  - a spelling the loader's coverage check would refuse.

NO FIGURES AND NO EVENTS. No price, date or capability is written (price stays in
`model_catalog`); `release_date` is NULL (rule 6), so `in_window` is true and `auto_track`'s
`release_date IS NOT NULL` keeps it off twice over. No `new-model` event is recorded: a
catalogue row is not a release, and the updates feed would otherwise announce hundreds at once.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from collect.adapters.queries.sieve import name_forms
from collect.registry.aliases import (
    alias_rows,
    classify_specificity,
    normalize,
    query_variants,
    spelling_gaps,
)
from collect.registry.models import AliasSpec, SeedModel

PROVENANCE = "catalogued"
IN_SCOPE_KINDS = frozenset({"text", "image", "speech", "transcription", "video", "decisions"})

CANDIDATES = """
    SELECT mc.canonical_id, mc.provider, mc.name, mc.output_modalities
      FROM model_catalog mc
      LEFT JOIN model_version mv ON mv.canonical_id = mc.canonical_id
     WHERE mv.id IS NULL
     ORDER BY mc.canonical_id
"""


def kind_of(output_modalities: list[str] | None) -> str:
    """The kind OpenRouter's published outputs say - never guessed from the name."""
    mods = set(output_modalities or ())
    for kind in ("speech", "transcription", "video", "image", "decisions", "embeddings", "rerank"):
        if kind in mods:
            return kind
    if "audio" in mods:
        return "audio"
    return "text" if "text" in mods else "unknown"


@dataclass
class Seat:
    canonical_id: str
    kind: str
    model: SeedModel


@dataclass
class SeatPlan:
    seats: list[Seat] = field(default_factory=list)
    #: canonical id -> why it was not seated
    set_aside: dict[str, str] = field(default_factory=dict)
    candidates: int = 0

    def by_reason(self) -> dict[str, int]:
        return dict(Counter(r.split(":")[0] for r in self.set_aside.values()).most_common())

    def summary(self) -> str:
        kinds = dict(Counter(s.kind for s in self.seats).most_common())
        return (f"{self.candidates} catalogue model(s) without a registry row: {len(self.seats)} "
                f"to seat {kinds}; {len(self.set_aside)} set aside {self.by_reason()}")


def _seed_model(canonical_id: str, provider: str, name: str, forms: tuple[str, ...]) -> SeedModel:
    primary = forms[0].lower()
    variants = [v for v in query_variants(primary) if v != primary]
    for extra in forms[1:]:
        variants += query_variants(extra.lower())
    return SeedModel(canonical_id=canonical_id, provider=provider, display_name=name,
                     aliases=AliasSpec(surface=primary, variants=list(dict.fromkeys(variants))))


def plan(conn, *, owned_keys: dict[str, set[str]] | None = None) -> SeatPlan:
    """What would be seated, and what is set aside and why. Reads only.

    `owned_keys` maps a normalised name key to the canonical ids already owning it: every live
    alias, plus every name the resolver derives from registry display names. Built from the
    database when not given.
    """
    if owned_keys is None:
        owned_keys = existing_keys(conn)
    out = SeatPlan()
    rows = conn.execute(CANDIDATES).fetchall()
    out.candidates = len(rows)
    drafts: list[Seat] = []
    for canonical_id, provider, name, mods in rows:
        kind = kind_of(mods)
        if ":" in canonical_id:
            # `:free`, `:batch`, ... are LISTINGS of another model (judge/news.py treats
            # a `:free` listing as the model it is free of), never a model of their own.
            suffix = canonical_id.split(":", 1)[1]
            out.set_aside[canonical_id] = f"listing variant ({suffix}): another model's listing"
            continue
        if provider == "openrouter" or canonical_id.startswith("openrouter/"):
            out.set_aside[canonical_id] = "router: not a model"
            continue
        if canonical_id.startswith("~"):
            # `~anthropic/claude-opus-latest`: a POINTER to whichever model is current,
            # 25 of them on 2026-11-10. A row for it would file claims under a moving name.
            out.set_aside[canonical_id] = "latest pointer: names whichever model is current"
            continue
        if kind not in IN_SCOPE_KINDS:
            out.set_aside[canonical_id] = f"out of scope: kind {kind}"
            continue
        forms = name_forms(name)
        if not forms:
            out.set_aside[canonical_id] = ("no usable name form: too short, "
                                           "or one word with no digit")
            continue
        try:
            model = _seed_model(canonical_id, provider, name, forms)
        except ValueError as exc:  # pydantic's ValidationError: an id the registry refuses
            out.set_aside[canonical_id] = f"not a valid registry id: {type(exc).__name__}"
            continue
        if classify_specificity(model.aliases.surface, model) == "family":
            out.set_aside[canonical_id] = "family specificity: no digit and not the id's local part"
            continue
        # Extra forms (a bracketed second name) that would only be family rows are dropped
        # from the declared spellings, never seated at family level.
        kept = [v for v in model.aliases.variants if classify_specificity(v, model) != "family"]
        model = model.model_copy(update={"aliases": AliasSpec(surface=model.aliases.surface,
                                                                 variants=kept)})
        if spelling_gaps([model]):
            out.set_aside[canonical_id] = "spelling coverage: a required rendering is missing"
            continue
        drafts.append(Seat(canonical_id, kind, model))

    # COLLISIONS: a key another model owns, or two candidates fold to (both set aside).
    batch = defaultdict(set)
    for s in drafts:
        for row in alias_rows(s.model):
            batch[row.normalized].add(s.canonical_id)
    for s in drafts:
        keys = {row.normalized for row in alias_rows(s.model)}
        owned = sorted({o for k in keys for o in owned_keys.get(k, ()) if o != s.canonical_id})
        twins = sorted({o for k in keys for o in batch[k] if o != s.canonical_id})
        if owned:
            out.set_aside[s.canonical_id] = f"name already owned: {', '.join(owned[:3])}"
        elif twins:
            out.set_aside[s.canonical_id] = f"folds to the same key as: {', '.join(twins[:3])}"
        else:
            out.seats.append(s)
    return out


def existing_keys(conn) -> dict[str, set[str]]:
    """normalised key -> canonical ids owning it: live aliases and resolver display-name forms."""
    owned: dict[str, set[str]] = defaultdict(set)
    for key, cid in conn.execute(
            "SELECT a.normalized, mv.canonical_id FROM model_alias a "
            "JOIN model_version mv ON mv.id = a.model_version_id "
            "WHERE a.valid_until IS NULL OR a.valid_until > now()").fetchall():
        owned[key].add(cid)
    rows = conn.execute("SELECT canonical_id, display_name FROM model_version").fetchall()
    for cid, display in rows:
        for form in name_forms(display or ""):
            owned[normalize(form)].add(cid)
    return owned


INSERT = """
    INSERT INTO model_version ({cols}) VALUES ({vals})
    ON CONFLICT DO NOTHING
    RETURNING id
"""


def apply(conn, plan_: SeatPlan) -> dict[str, Any]:
    """Write the planned rows and their aliases. NEVER touches an existing row.

    A row that exists by the time of the insert (the poll racing this writer in one
    workflow) is skipped and counted, never updated: polled > seed/unpolled > catalogued.
    """
    from psycopg.types.json import Json

    from collect.registry.load import _MODEL_COLUMNS, _sync_alias, model_row

    sql = INSERT.format(cols=", ".join(_MODEL_COLUMNS),
                        vals=", ".join(f"%({c})s" for c in _MODEL_COLUMNS))
    inserted, skipped, aliases = [], [], Counter()
    for s in plan_.seats:
        row = model_row(s.model, provenance=PROVENANCE)
        params = {**row, "sources": Json(row["sources"])}  # as the loader's upsert does
        got = conn.execute(sql, params).fetchone()
        if got is None:
            skipped.append(s.canonical_id)
            continue
        inserted.append(s.canonical_id)
        for alias in alias_rows(s.model, model_version_id=got[0]):
            aliases[_sync_alias(conn, alias)] += 1
    return {"inserted": len(inserted), "skipped_existing": len(skipped),
            "skipped_ids": skipped, "aliases": dict(aliases),
            "by_kind": dict(Counter(s.kind for s in plan_.seats
                                    if s.canonical_id in set(inserted)))}
