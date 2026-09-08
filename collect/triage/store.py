"""Store what `specificity.score_document` computes. The writer that was missing.

WHAT WAS WRONG, IN ONE SENTENCE. `collect/triage/specificity.py` has computed
the five components and the composite since it was built, is tested, and is
contract-backed - and **nothing ever stored the result**. All four `document`
INSERTs name the same columns and none of the six is among them:

    collect/adapters/blog/write.py:89
    collect/adapters/github.py:814, :971
    collect/adapters/reddit_write.py:72

`collect/assemble/article.py:document_row` does not build them either. The
handful of populated rows on staging came from `scripts/export_thread_contexts.py`,
which hand-builds INSERT text for one thread and one article - which is why the
count sat at seven while the corpus passed three thousand.

WHY THIS IS A SWEEP AND NOT SIX MORE COLUMNS ON FOUR INSERTS.

    ONE REGISTRY READ, NOT FOUR. `score_document` takes `version_aliases`
    because the registry read belongs once per run rather than once per
    document - `score_document`'s own docstring says so. Four adapters each
    building that population is four chances for them to diverge, and a
    `names_version` computed against a different surface set is not comparable
    to one that was not.

    IT IS A TRIAGE CONCERN, NOT A PLATFORM ONE. Three platform adapters would
    each grow a dependency on `collect/triage/` to write a column neither of
    them reads.

    AND IT MAKES THE BACKFILL AND THE FORWARD PATH THE SAME CODE. The 3,054
    stored documents and tonight's new ones need identical treatment; two
    implementations of that would be the drift this repo has already recorded
    under `has_artifact`.

RULE 6 IS THE WHOLE DESIGN OF `unreadable`. A document whose payload is not in
this raw store is COUNTED AND NAMED, never written as False. These columns
exist because `judge/`'s weighting read a NULL as a False once already; a
writer that invented Falses for text it could not read would commit the same
error one stage earlier, and it would be unfalsifiable from the row.

IDEMPOTENT BY CONSTRUCTION. Selects only rows with all six NULL, and the UPDATE
re-checks `has_numbers IS NULL`, so a second run is a no-op and two runs racing
cannot half-write a row.

SCORING AND WRITING ARE INTERLEAVED, AND THAT IS NOT A STYLE CHOICE. The first
version scored all 1,948 readable documents and then wrote them, which left the
connection idle for five minutes over a network link; the server closed it and
the whole backfill was lost at the first UPDATE. Regex matching is ~0.15s per
document, so a `batch` of 100 holds the gap near fifteen seconds. The lesson is
the shape rather than the number: a long CPU pass between a connection being
opened and being used is a dropped connection waiting to happen, and it fails at
the end of the expensive part.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from collect.triage.specificity import COMPONENTS, score_document

_SELECT = """
SELECT id, source, text_ref
FROM document
WHERE has_numbers IS NULL
  AND has_error_strings IS NULL
  AND has_code IS NULL
  AND has_conditions IS NULL
  AND names_version IS NULL
ORDER BY id
"""

_UPDATE = """
UPDATE document
SET has_numbers = %(has_numbers)s,
    has_error_strings = %(has_error_strings)s,
    has_code = %(has_code)s,
    has_conditions = %(has_conditions)s,
    names_version = %(names_version)s,
    specificity_score = %(specificity_score)s
WHERE id = %(id)s
  AND has_numbers IS NULL
"""


@dataclass
class ScoreRun:
    """What one sweep did. Every count carries what it was drawn from."""

    #: Rows with all six columns NULL when the sweep started.
    eligible: int = 0
    #: Of those, rows whose text this store could read.
    scored: int = 0
    #: Of those, rows whose payload is NOT here. LEFT NULL, never written False.
    unreadable: int = 0
    #: Unreadable, by source - a per-platform pattern is a different fault from
    #: a scattered one, and the two have different repairs.
    unreadable_by_source: dict[str, int] = field(default_factory=dict)
    written: int = 0
    #: Component true-counts over `scored`. Never over `eligible`: the
    #: unreadable rows were not measured and must not sit in a denominator.
    true_counts: dict[str, int] = field(default_factory=dict)

    def describe(self) -> str:
        """The figures with their denominator (rule 7)."""
        if not self.scored:
            return (
                f"eligible {self.eligible}, scored 0 - nothing was measured. "
                f"{self.unreadable} payloads absent from this store."
            )
        lines = [
            f"scored {self.scored}/{self.eligible} eligible; "
            f"{self.unreadable} left NULL because the payload is not in this "
            f"raw store (absent, not False)",
        ]
        for name in COMPONENTS:
            n = self.true_counts.get(name, 0)
            lines.append(f"  {name:<20} {n:>6}/{self.scored} = {n / self.scored:.1%}")
        if self.unreadable_by_source:
            worst = ", ".join(
                f"{s} ({n})"
                for s, n in sorted(
                    self.unreadable_by_source.items(), key=lambda kv: -kv[1]
                )
            )
            lines.append(f"  UNREADABLE BY SOURCE: {worst}")
        return "\n".join(lines)


def registry_population(conn):
    """The `SurfacePopulation` every stored-corpus pass resolves against.

    ONE CONSTRUCTION, TWO CALLERS. `version_aliases` below wants only the
    surfaces; `collect/triage/run.py` wants the whole population, because the
    entity gate needs `owners` and every figure it reports needs
    `fingerprint`. Two builders would be two chances to diverge, and a
    `names_version` computed against a different surface set is not comparable
    to one that was not - which is `score_document`'s own argument for taking
    the aliases as a parameter rather than reading the registry itself.

    THE FINGERPRINT IS WHY THIS RETURNS THE POPULATION AND NOT A TUPLE. Rule 7:
    a figure travels with the population it was drawn from, and the fingerprint
    is how a survival rate names one.
    """
    from collect.registry.seed import seed_models
    from collect.triage.entity import build_population

    models = conn.execute(
        "SELECT canonical_id, display_name FROM model_version ORDER BY canonical_id"
    ).fetchall()
    declared: list[str] = []
    for model in seed_models():
        declared.append(model.aliases.surface)
        declared.extend(model.aliases.variants)
    return build_population([(r[0], r[1]) for r in models], declared)


def version_aliases(conn) -> tuple[str, ...]:
    """The surfaces `names_version` matches against. Registry-derived.

    `build_population` over `model_version` plus the seed's declared surfaces -
    the same construction `scripts/export_thread_contexts.version_aliases` uses,
    and it is the only one MEASURED to match anything. `model_alias.normalized`
    strips every non-alphanumeric and matched 0 of 195 comment bodies; these
    surfaces matched 27. See that function for the incident.
    """
    return tuple(sorted(registry_population(conn).surfaces))


def score_unscored(conn, store, *, batch: int = 100, dry_run: bool = False) -> ScoreRun:
    """Score every document with all six columns NULL, and store the result.

    Args:
        conn: an open connection. Not opened here - the chain owns the
            connection and the ledger row wrapping this stage.
        store: a `RawStore`. Passed rather than constructed so a caller can
            point at a different root without an environment variable.
        batch: documents scored, then written, per transaction. Bounds BOTH how
            much work a crash loses and how long the connection sits idle - see
            the module docstring on why the second one bit.
        dry_run: compute and count, write nothing. The default is False here
            and True in the script, because a stage that has to be asked twice
            does not run at night.
    """
    aliases = version_aliases(conn)
    pending = conn.execute(_SELECT).fetchall()
    run = ScoreRun(eligible=len(pending))

    def _flush(rows: list[dict]) -> None:
        """`conn.commit()`, NOT `with conn.transaction()`, AND THAT COST A RUN.

        `collect.db.connect` returns a psycopg connection with autocommit off,
        so the `SELECT` above has already opened a transaction by the time the
        first batch is ready. `conn.transaction()` inside an open transaction
        opens a SAVEPOINT: exiting it RELEASES the savepoint and commits
        nothing. The sweep therefore ran to completion, reported rows written,
        and left the table untouched - a write path that reports success and
        stores nothing, which is the worst shape a bug can have here.

        Every other writer in `collect/` calls `conn.commit()` - `ops/sweep.py`,
        `ops/sweep_reddit.py`, `ops/ledger.py`, `cli.py`. This one now does too.
        """
        if dry_run or not rows:
            return
        for row in rows:
            conn.execute(_UPDATE, row)
        conn.commit()
        run.written += len(rows)

    rows: list[dict] = []
    for doc_id, source, text_ref in pending:
        try:
            text = store.get_text(text_ref)
        except Exception:
            # LEFT NULL AND COUNTED. Not written False: this store could not
            # read the text, which is not the same fact as the text carrying no
            # numbers, and only one of the two is recoverable from the row.
            run.unreadable += 1
            run.unreadable_by_source[source] = (
                run.unreadable_by_source.get(source, 0) + 1
            )
            continue
        spec = score_document(text, version_aliases=aliases)
        rows.append({"id": doc_id, **spec.as_row()})
        run.scored += 1
        for name in COMPONENTS:
            if getattr(spec, name):
                run.true_counts[name] = run.true_counts.get(name, 0) + 1
        if len(rows) >= batch:
            _flush(rows)
            rows = []
    _flush(rows)
    return run
