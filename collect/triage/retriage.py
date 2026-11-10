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
       AND d.fetched_at < %s
     ORDER BY d.id
"""

#: How many `plan` would read, said BEFORE it reads them (#613 review, point 5):
#: on the shared database each is a payload read, often a remote one.
CANDIDATE_COUNT = """
    SELECT count(*) FROM document d
     WHERE d.triage_verdict = 'dropped'
       AND %s = ANY(coalesce(d.filter_reasons, '{}'))
       AND d.fetched_at < %s
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
    #: A Reddit document whose thread cannot be SEEN: its root is not stored,
    #: or its payload is missing or will not parse. LEFT DROPPED, never read as
    #: "not adult" (#613 review, point 1, rule 6).
    adult_unknown: int = 0
    #: A readable payload with no `over_18` field at all - mostly older
    #: subreddit-listing payloads. RE-TRIAGED, as the harvest keeps such a post
    #: (collect/adapters/reddit.py `_admit`: only an explicit `true` is
    #: skipped), and counted so the group stays visible (#613 re-read).
    adult_field_absent: int = 0
    unreadable: int = 0
    #: A payload read, but its extractor returned no prose (point 3).
    no_prose: int = 0
    #: Of `ids`: the document's OWN text names a target, or only its thread
    #: root does (point 2). Triage may still drop a root-only match, so the
    #: dry run's count is an upper bound and says which part is which.
    own_text: int = 0
    root_only: int = 0

    def summary(self) -> str:
        return (
            f"re-triage plan for {', '.join(self.models)}: {len(self.ids)} of "
            f"{self.candidates} dropped no-resolvable-entity document(s) now name one "
            f"of them ({dict(self.by_source)}) - {self.own_text} by their own text, "
            f"{self.root_only} only through their thread root (triage may still "
            f"drop those); {self.adult_left_dropped} in adult threads and "
            f"{self.adult_unknown} whose thread cannot be seen left dropped; "
            f"{self.adult_field_absent} whose stored post carries no adult flag "
            f"re-triaged, as the harvest keeps them; {self.unreadable} unreadable here; "
            f"{self.no_prose} with no prose"
        )


def subreddit_of(url: str | None) -> str | None:
    m = _SUBREDDIT.search(url or "")
    return m.group(1) if m else None


#: `_adult_state`'s answers. ABSENT is a readable post with no flag at all.
ADULT, NOT_ADULT, ABSENT, UNKNOWN = "adult", "not_adult", "absent", "unknown"


def _adult_state(payload: str | bytes | None) -> str:
    """Reddit's own `over_18` on a stored post payload, as the harvest reads it.

    FOLLOWS THE HARVEST (#613 re-read). `_admit` skips only an explicit
    `over_18: true` and keeps a post with no flag, so the re-triage does the
    same: ADULT stays dropped, ABSENT and NOT_ADULT are re-triaged. UNKNOWN -
    no payload, or one that will not parse - stays dropped: the thread cannot
    be seen at all, and the harvest reads a root before its comments (rule 6).
    """
    if not payload:
        return UNKNOWN
    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        return UNKNOWN
    data = data.get("data", data) if isinstance(data, dict) else None
    if not isinstance(data, dict):
        return UNKNOWN
    if "over_18" not in data:
        return ABSENT
    return ADULT if data["over_18"] is True else NOT_ADULT


def seated_since(conn, models: list[str]):
    """The earliest `first_seen_at` among `models`: a document fetched after it
    was triaged with the model already in the registry, so it cannot hold a
    stale verdict for it (#613 review, point 5)."""
    row = conn.execute(
        "SELECT min(first_seen_at) FROM model_version "
        "WHERE id = ANY(%s) OR canonical_id = ANY(%s)", (models, models)).fetchone()
    return row[0] if row else None


def candidate_count(conn, models: list[str]) -> int:
    """How many documents `plan` would read for `models`. Reads no payload."""
    return int(conn.execute(CANDIDATE_COUNT, (NO_ENTITY, seated_since(conn, models)))
               .fetchone()[0])


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

    #: root id -> (its prose, its raw payload); read once per thread.
    root_cache: dict[str, tuple[str | None, bytes | str | None]] = {}

    def read(ref: str | None, source: str) -> tuple[str | None, bytes | str | None]:
        if not ref or source not in extractors:
            return None, None
        extractor, wants_bytes = extractors[source]
        try:
            blob = store.get(ref) if wants_bytes else store.get_text(ref)
            return extractor(blob), blob
        except Exception:  # noqa: BLE001 - counted, never read as "names nothing"
            return None, None

    rows = conn.execute(CANDIDATES, (NO_ENTITY, seated_since(conn, models))).fetchall()
    out.candidates = len(rows)
    for doc_id, source, ref, root_id, url, root_ref in rows:
        text, blob = read(ref, source)
        if blob is None:
            out.unreadable += 1
            continue
        if text is None:
            out.no_prose += 1
        is_comment = bool(root_id) and root_id != doc_id
        root_names = False
        root_blob = None
        if is_comment and root_ref:
            if root_id not in root_cache:
                root_cache[root_id] = read(root_ref, source)
            rtext, root_blob = root_cache[root_id]
            root_names = names_target(rtext)
        own_names = names_target(text)
        if not (own_names or root_names):
            continue
        if source == "reddit":
            # A comment's flag is its thread's; a post's is its own.
            flag_payload = root_blob if is_comment else blob
            adult = _adult_state(flag_payload)
            if adult == ADULT:
                out.adult_left_dropped += 1
                continue
            if adult == UNKNOWN:
                out.adult_unknown += 1
                continue
            if adult == ABSENT:
                out.adult_field_absent += 1  # re-triaged, as the harvest keeps it
        out.ids.append(doc_id)
        if own_names:
            out.own_text += 1
        else:
            out.root_only += 1
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
