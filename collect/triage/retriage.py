"""Re-triage stale "no model" verdicts after a model is seated (#602, option b).

THE DEFECT. Triage judges a document once - it reads `triage_verdict IS NULL` -
against the registry as it stood that day. A document dropped as
`no-resolvable-entity` before its model was seated keeps that verdict for good,
even after the registry gains the model it names. Measured 2026-11-05: 4 of 16
readable "no model" threads named a model seated since.

THE FIX, OPTION (b) ON #602. When models are seated, find the dropped
`no-resolvable-entity` documents whose text - their own, or their thread
root's - names one of THOSE models, clear exactly those verdicts, and triage
exactly those documents again. Scoped and recorded: `plan` reads only, the
caller saves the id list before `apply` writes, and `apply` reports what each
came back as.

ONE FINDER, SO THEY CANNOT DISAGREE. Text is matched by `RegistrySurfaceFinder`
over `registry_population` - the population triage itself resolves against -
so the re-triage can never call a document "names the model" that triage
would then read as naming nothing.

⚠ WHAT (b) MISSES, NAMED AS THE #602 REVIEW ASKED. It runs when a model is SEATED. Two
  other changes also make an old verdict stale and do not trigger it:
    - a display-name change on an existing `model_version` row, which changes
      the surfaces derived from it;
    - a change to `contract/seed_models.yaml`'s declared surfaces.
  Neither is "a model was seated". If either starts to matter, option (a) -
  storing the population fingerprint with each verdict and re-triaging rows
  older than the current population - is the fix.

ADULT THREADS STAY DROPPED. Stored before the harvest's `over_18` skip existed
(#602 item 9), a post Reddit flags adult - or a comment under one - is left
dropped and counted, so the re-triage cannot promote what today's harvest would
have skipped.
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from dataclasses import dataclass, field

from collect.triage.gates import NO_ENTITY

log = logging.getLogger(__name__)

_SUBREDDIT = re.compile(r"reddit\.com/r/([^/]+)/", re.I)

CANDIDATES = """
    SELECT d.id, d.source, d.text_ref, d.thread_root_id, d.url, r.text_ref AS root_ref
      FROM document d
      LEFT JOIN document r ON r.id = d.thread_root_id AND d.thread_root_id <> d.id
     WHERE d.triage_verdict = 'dropped'
       AND %s = ANY(coalesce(d.filter_reasons, '{}'))
     ORDER BY d.id
"""


@dataclass
class RetriagePlan:
    models: list[str]
    population_fingerprint: str | None
    candidates: int = 0
    ids: list[str] = field(default_factory=list)
    by_source: Counter = field(default_factory=Counter)
    by_subreddit: Counter = field(default_factory=Counter)
    adult_left_dropped: int = 0
    unreadable: int = 0

    def summary(self) -> str:
        return (
            f"re-triage plan for {', '.join(self.models)}: {len(self.ids)} of "
            f"{self.candidates} dropped no-resolvable-entity document(s) now name one "
            f"of them ({dict(self.by_source)}); {self.adult_left_dropped} in adult "
            f"threads left dropped; {self.unreadable} unreadable here"
        )


def subreddit_of(url: str | None) -> str | None:
    m = _SUBREDDIT.search(url or "")
    return m.group(1) if m else None


def _is_adult(payload: str | bytes | None) -> bool:
    """Reddit's own `over_18` on a stored post payload. Unreadable is not adult."""
    try:
        data = json.loads(payload) if payload else {}
    except (TypeError, ValueError):
        return False
    data = data.get("data", data) if isinstance(data, dict) else {}
    return isinstance(data, dict) and data.get("over_18") is True


def _target_ids(conn, models: list[str]) -> set[str]:
    """Both id shapes of each named model: row `id` and `canonical_id`."""
    rows = conn.execute(
        "SELECT id, canonical_id FROM model_version WHERE id = ANY(%s) OR canonical_id = ANY(%s)",
        (models, models),
    ).fetchall()
    missing = set(models) - {k for r in rows for k in r}
    if missing:
        raise ValueError(f"not in the registry, so nothing to re-triage for: {sorted(missing)}")
    return {k for r in rows for k in r}


def plan(conn, store, *, models: list[str]) -> RetriagePlan:
    """Which stale verdicts name the newly seated `models`. Reads only."""
    from collect.surface_resolver import RegistrySurfaceFinder
    from collect.triage.run import _prose_by_source
    from collect.triage.store import registry_population

    targets = _target_ids(conn, models)
    population = registry_population(conn)
    find = RegistrySurfaceFinder(population)
    extractors = _prose_by_source()
    out = RetriagePlan(models=list(models), population_fingerprint=population.fingerprint)

    # OWNERS BY NORMALISED KEY. `find` returns the span AS WRITTEN ("Hailuo 3
    # Max") and `population.owners` is keyed by the population's own spelling
    # ("hailuo 3 max"), so a direct lookup matched nothing - the same reason
    # `RegistrySurfaceResolver` keys its owners this way.
    from collect.registry.aliases import normalize

    owners_by_key: dict[str, set[str]] = {}
    for surface, owners in population.owners.items():
        owners_by_key.setdefault(normalize(surface), set()).update(owners)

    def names_target(text: str | None) -> bool:
        if not text:
            return False
        owners = {o for s in find(text) for o in owners_by_key.get(normalize(s), ())}
        return bool(owners & targets)

    root_cache: dict[str, tuple[str | None, bool]] = {}

    def read(ref: str | None, source: str) -> tuple[str | None, bytes | str | None]:
        if not ref or source not in extractors:
            return None, None
        extractor, wants_bytes = extractors[source]
        try:
            blob = store.get(ref) if wants_bytes else store.get_text(ref)
            return extractor(blob), blob
        except Exception:  # noqa: BLE001 - counted, never read as "names nothing"
            return None, None

    rows = conn.execute(CANDIDATES, (NO_ENTITY,)).fetchall()
    out.candidates = len(rows)
    for doc_id, source, ref, root_id, url, root_ref in rows:
        text, blob = read(ref, source)
        if blob is None:
            out.unreadable += 1
            continue
        root_names = False
        root_adult = False
        if root_id and root_ref:
            if root_id not in root_cache:
                rtext, rblob = read(root_ref, source)
                root_cache[root_id] = (rtext, source == "reddit" and _is_adult(rblob))
            rtext, root_adult = root_cache[root_id]
            root_names = names_target(rtext)
        if not (names_target(text) or root_names):
            continue
        if source == "reddit" and (root_adult or _is_adult(blob)):
            out.adult_left_dropped += 1
            continue
        out.ids.append(doc_id)
        out.by_source[source] += 1
        sub = subreddit_of(url)
        if sub:
            out.by_subreddit[sub] += 1
    return out


def apply(conn, store, plan_: RetriagePlan) -> dict:
    """Clear exactly `plan_.ids`' verdicts and triage exactly those again.

    The clear is committed with triage's first batch (`triage_stored` commits
    per batch). A run that dies part-way leaves the rest with no verdict, which
    the next triage pass judges anyway - never a lost or doubled row. Returns
    what came back, by source and subreddit: the first measurement of the
    inheritance rules on a population they did not choose.
    """
    from collect.triage.run import triage_stored

    if not plan_.ids:
        return {"cleared": 0, "triaged": 0, "kept": 0, "dropped": 0}
    cur = conn.execute(
        "UPDATE document SET triage_verdict = NULL, filter_reasons = NULL "
        "WHERE id = ANY(%s) AND triage_verdict = 'dropped'",
        (plan_.ids,),
    )
    cleared = cur.rowcount
    run = triage_stored(conn, store, dry_run=False, document_ids=plan_.ids)
    after = dict(conn.execute(
        "SELECT id, triage_verdict FROM document WHERE id = ANY(%s)", (plan_.ids,),
    ).fetchall())
    urls = dict(conn.execute(
        "SELECT id, url FROM document WHERE id = ANY(%s)", (plan_.ids,)).fetchall())
    kept_by_sub = Counter(subreddit_of(urls[i]) for i, v in after.items()
                          if v == "kept" and subreddit_of(urls[i]))
    return {
        "cleared": cleared,
        "triaged": run.triaged,
        "kept": run.kept,
        "dropped": run.dropped,
        "kept_by_source": {s: c.get("kept", 0) for s, c in run.by_source.items()},
        "kept_by_subreddit": dict(kept_by_sub),
        "subject_inherited": run.subject_inherited,
        "by_reason": dict(run.by_reason),
    }
