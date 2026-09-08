"""Forward-only schema migrations. Forty lines of intent and no framework.

WHY THIS EXISTS
---------------
`apply_schema` fails loudly if objects exist, and `reset_schema` refuses a
non-localhost host, a non-development `ENVIRONMENT` and any database holding
rows. Both refusals are right. Between them there was **no operation that changes
an existing schema**, and the staging instance now holds 340 `model_version` rows,
so `reset_schema` will refuse it for the rest of the project's life.

Adding `last_swept_at` there took a hand-run `ALTER TABLE`. Once is fine; the
four `thread_context` coverage columns and `extraction_version` are next, so it
would not have been once.

WHAT THIS DELIBERATELY IS NOT
-----------------------------
Not Alembic. *"No workflow engine, no Kafka, no time-series DB"* is a stack
decision and a migration framework is adjacent to it — a dependency, a config
file, autogenerate diffing a live database against ORM models this project does
not have, and down-migrations nobody will test. The problem is smaller than that:
apply a few forward-only SQL files, in order, exactly once, and know which ran.

    contract/migrations/baseline.sql                     the starting point
    contract/migrations/20260817T0930_thing.sql          one delta

FOUR PROPERTIES, AND THE FIRST IS THE REASON FOR THE OTHER THREE
-----------------------------------------------------------------
**1. `contract/tables.sql` stays canonical, and a test proves the chain reaches
it.** `tests/test_migrations.py` builds one schema from the file and another from
`baseline.sql` plus every migration, then compares columns, constraints, indexes
and views. A migration chain is otherwise a SECOND DESCRIPTION of the schema, and
this repo has found that defect in four places already — a refusal naming a
scorer that existed, `CLAUDE.md` asserting a startup guarantee with no caller, a
stale HTML render describing a retired design, and a doc crediting a floor that
removes 7.7%. All four read as authoritative while wrong. That test was written
before this module.

**2. Forward-only.** No down-migrations. Same reasoning as immutable raw
payloads: the recovery path is re-derive, not reverse, and an untested rollback
is false comfort at the moment it is needed.

⚠  WRITING A MIGRATION? TWO RULES, BOTH PAID FOR ON 2026-09-08
---------------------------------------------------------------
Read these before the SQL, not after. `tests/test_migrations.py` enforces the
first; nothing can enforce the second.

**A MIGRATION FILE CONTAINS NO `BEGIN` AND NO `COMMIT`.** `migrate` below wraps
each file in `conn.transaction()` and inserts the ledger row inside that same
transaction, deliberately, so a failure leaves neither the change nor the claim
that it was made. `collect.db.connect` leaves autocommit OFF, so a transaction is
already open by the time a file runs and `conn.transaction()` opens a SAVEPOINT
— a `COMMIT` in the file commits the OUTER transaction, and the savepoint
release then fails with `InvalidSavepointSpecification`.

    WHAT THAT COST: `20260908T1100_reddit_thread_link_prefix.sql` shipped with
    BEGIN/COMMIT, COMMITTED ALL 2,840 OF ITS UPDATES, AND FAILED BEFORE THE
    LEDGER ROW. The data changed; nothing recorded that it had. Eleven of the
    eleven migrations before it carried no transaction control, which was the
    convention and was not decoration.

**`migrate()` DOES NOT COMMIT. THE CALLER DOES.** That is the design — the
caller owns the transaction and the ledger row travels with the change — and it
is also the trap that follows from it. `collect/cli.py:db migrate` calls
`conn.commit()` after this function; a script that calls `migrate(conn)` and
then `conn.close()` **rolls the whole thing back**.

    WHAT THAT COST: the recovery from the first mistake looked like it worked.
    Both files reported applied, and the ledger row READ BACK SUCCESSFULLY
    INSIDE THE SAME CONNECTION — then vanished on close. DDL is transactional
    in Postgres, so the `ALTER TABLE` went with it.

    **So: apply with `python -m collect.cli db migrate`**, which gates and
    commits, and **verify in a FRESH connection**, never in the one that did the
    work. A read-back inside an uncommitted transaction is not evidence.

Both mistakes were mine and both were invisible to the obvious check, which is
why they are here rather than only in the file that caused them: the next person
to write a migration reads this module, not that file.

**3. Content-hashed, and a mismatch refuses the WHOLE RUN.** An edited applied
migration means two databases already disagree. Applying more compounds it, so
nothing is applied — not the edited file and not the innocent ones after it.
Warning and continuing would turn one divergence into several.

**4. Timestamp filenames, not sequence numbers.** `contract/` is shared, and two
people writing `003_` in the same week is a guaranteed conflict — which the
content hash would then correctly refuse to resolve, turning a merge conflict
into a stuck database.

WHAT IS REFUSED
---------------
**No automatic application on startup, ever.** A schema that changes because a
process booted is how a schema changes during an incident. `db migrate` is a
command somebody types. `collect.db.connect` does not call anything here, and a
test asserts it.

**And it stays a `collect.cli` command even though the schema is both lanes'.**
`judge/` opening a connection must not migrate on the way in, for the same reason
startup application is refused. A test asserts nothing under `judge/` imports
this module.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from collect.config import CONTRACT_DIR
from collect.ids import content_hash

log = logging.getLogger(__name__)

MIGRATIONS_DIR = CONTRACT_DIR / "migrations"
BASELINE = "baseline.sql"

#: `<UTC compact timestamp>_<slug>.sql`. Enforced rather than encouraged, because
#: a sequence number that slipped in would sort correctly right up until two
#: people picked the same one.
FILENAME = re.compile(r"^\d{8}T\d{4}_[a-z0-9_]+\.sql$")

LEDGER = "schema_migration"

#: Created on demand. A database with no ledger has had no migrations applied,
#: which is the same statement — so its absence is not an error. This is the one
#: piece of DDL this module issues that is not a migration, and it is a ledger
#: rather than schema.
LEDGER_DDL = f"""
CREATE TABLE IF NOT EXISTS {LEDGER} (
  filename     text PRIMARY KEY,
  content_hash text NOT NULL,
  applied_at   timestamptz NOT NULL DEFAULT now()
)
"""


class MigrationError(RuntimeError):
    """A migration set that cannot be trusted."""


class MigrationLedgerMismatch(MigrationError):
    """The ledger and the files on disk disagree. Nothing is applied."""


@dataclass(frozen=True)
class Migration:
    filename: str
    path: Path
    sql: str

    @property
    def content_hash(self) -> str:
        return content_hash(self.sql)


def baseline_sql(directory: Path | None = None) -> str:
    """The starting point every migration is a delta from.

    A frozen copy of `contract/tables.sql` taken when the ledger was introduced.
    It is never edited: editing it would change what the chain starts from without
    changing what any existing database contains, which is the divergence this
    whole module exists to prevent.
    """
    path = (directory or MIGRATIONS_DIR) / BASELINE
    if not path.exists():
        raise MigrationError(
            f"{path} does not exist. The chain has no starting point, so the "
            "equivalence test cannot prove it reaches contract/tables.sql."
        )
    return path.read_text(encoding="utf-8")


def discover(directory: Path | None = None) -> tuple[Migration, ...]:
    """Every migration, in filename order. The baseline is not one of them."""
    root = directory or MIGRATIONS_DIR
    if not root.exists():
        return ()
    out = []
    for path in sorted(root.glob("*.sql")):
        if path.name == BASELINE:
            continue
        if not FILENAME.match(path.name):
            raise MigrationError(
                f"{path.name} is not named <UTC timestamp>_<slug>.sql — e.g. "
                "20260817T0930_thread_context_coverage.sql. Sequence numbers are "
                "refused because contract/ is shared and two people will pick the "
                "same one."
            )
        out.append(Migration(path.name, path, path.read_text(encoding="utf-8")))
    return tuple(out)


def ledger_exists(conn) -> bool:
    row = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (LEDGER,)).fetchone()
    return bool(row and row[0])


def ensure_ledger(conn) -> None:
    conn.execute(LEDGER_DDL)


def _applied(conn) -> dict[str, str]:
    if not ledger_exists(conn):
        return {}
    rows = conn.execute(f"SELECT filename, content_hash FROM {LEDGER}").fetchall()  # noqa: S608
    return dict(rows)


@dataclass(frozen=True)
class MigrationStatus:
    """What `db check` reports. A statement of state, not a refusal.

    `mismatched` carries both kinds of disagreement: a file whose content changed
    after it was applied, and a ledger row with no file on disk. Both mean two
    databases already differ, and neither can be resolved by applying more.
    """

    applied_filenames: list[str]
    pending_filenames: list[str]
    mismatched: list[tuple[str, str]]
    #: Whether this database has the ledger at all. A database created before it
    #: existed has none, and `schema_migration` is part of `contract/tables.sql`
    #: — so its absence is a real schema difference, not merely "nothing applied
    #: yet". Reported rather than inferred: reading no-ledger as zero-applied is
    #: the same mistake as reading NULL as false, and staging is exactly this
    #: case.
    ledger_present: bool = True

    @property
    def is_current(self) -> bool:
        return (
            not self.pending_filenames
            and not self.mismatched
            and self.ledger_present
        )

    def describe(self) -> str:
        if self.mismatched:
            detail = ", ".join(f"{name} ({why})" for name, why in self.mismatched)
            return f"LEDGER MISMATCH — {detail}. Nothing can be applied."
        # NO LEDGER AND PENDING WORK ARE TWO FACTS AND BOTH GET SAID.
        #
        # This returned early on `pending_filenames` and the ledger warning
        # disappeared the moment anything was outstanding — so a pre-ledger
        # database with work to do reported only the work, and the schema
        # difference that `schema_migration` itself represents went unmentioned.
        #
        # It could not surface while `discover()` returned nothing, because
        # `pending` was always empty and the second branch always ran. The first
        # real migration made the collapse reachable, which is the same shape as
        # `finished_at IS NULL` versus `outcome = 'failed'` on `job_run`: two
        # states one reader was flattening into one.
        parts: list[str] = []
        if not self.ledger_present:
            parts.append(
                "NO LEDGER — this database predates schema_migration, which is "
                "part of contract/tables.sql, so the schema differs from the "
                "file by that table. `db migrate` creates it."
            )
        if self.pending_filenames:
            parts.append(
                f"{len(self.applied_filenames)} applied, "
                f"{len(self.pending_filenames)} PENDING: "
                + ", ".join(self.pending_filenames)
            )
        if parts:
            return " ".join(parts)
        return f"current — {len(self.applied_filenames)} applied, none pending"


def check(conn, directory: Path | None = None) -> MigrationStatus:
    """Report without applying, and without creating the ledger.

    Read-only on purpose. The equivalence test proves the CHAIN is correct; it
    cannot prove any given database is CURRENT, and an absent error is not
    evidence that it is — same reason `phrase_present` is None rather than 0 and
    `last_swept_at` is NULL rather than now().
    """
    migrations = discover(directory)
    applied = _applied(conn)
    on_disk = {m.filename: m.content_hash for m in migrations}

    mismatched: list[tuple[str, str]] = []
    for filename, recorded in sorted(applied.items()):
        if filename not in on_disk:
            mismatched.append((filename, "applied but not on disk"))
        elif on_disk[filename] != recorded:
            mismatched.append((filename, "content changed since it was applied"))

    return MigrationStatus(
        applied_filenames=[m.filename for m in migrations if m.filename in applied],
        pending_filenames=[m.filename for m in migrations if m.filename not in applied],
        mismatched=mismatched,
        ledger_present=ledger_exists(conn),
    )


class SchemaDiverged(MigrationError):
    """A pending migration's objects already exist, and not as described."""


def stamp_at_head(conn, directory: Path | None = None) -> list[str]:
    """Record every migration as applied WITHOUT running it. For `db init` only.

    A database created from `contract/tables.sql` is **by definition** at the
    head of the chain: the equivalence test's whole content is that
    `baseline.sql` plus every migration equals that file. So the migrations have
    nothing left to do, and the ledger should say so.

    Without this, the first migration breaks `db init`: `tables.sql` creates
    `job_run`, then `db check` reports the migration pending, then `db migrate`
    runs `CREATE TABLE job_run` against a table that exists. That is not a
    corner case, it is every new database from now on.

    THIS IS NOT THE SAME OPERATION AS RECORDING A MIGRATION AS APPLIED BECAUSE
    ITS OBJECTS HAPPEN TO EXIST. Here the provenance is known — this process
    just applied `tables.sql` and nothing else has touched the database. Where
    the provenance is *not* known, `migrate()` refuses instead; see
    `_refuse_if_objects_exist`.
    """
    ensure_ledger(conn)
    stamped = []
    for migration in discover(directory):
        conn.execute(
            f"INSERT INTO {LEDGER} (filename, content_hash) VALUES (%s, %s) "  # noqa: S608
            "ON CONFLICT (filename) DO NOTHING",
            (migration.filename, migration.content_hash),
        )
        stamped.append(migration.filename)
    return stamped


#: Objects a migration creates, read from its own SQL. Crude on purpose: it
#: only has to be good enough to ask "does this already exist", and a name it
#: misses costs a `DuplicateTable` from Postgres rather than a silent pass.
_CREATES = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?(TABLE|INDEX|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?\"?(\w+)\"?",
    re.IGNORECASE,
)


def _refuse_if_objects_exist(conn, migration: Migration) -> None:
    """Refuse a migration whose objects are already there. LOUDLY.

    THE TEMPTING ALTERNATIVE IS TO RECORD IT AS APPLIED AND MOVE ON, and that is
    exactly how a divergent schema gets papered over. "The table exists" and
    "the table exists AND matches what the file describes" are different facts,
    and only the second makes recording-as-applied safe — but verifying it needs
    the equivalence machinery, which builds both schemas and diffs them. That is
    a test-time operation, not something to run inside a migration.

    So the legitimate case is removed rather than detected: `db init` stamps the
    ledger at head (see `stamp_at_head`), which is the only situation where the
    objects legitimately pre-exist with known provenance. Anything else reaching
    here has a schema nobody can account for, and the honest response is to stop
    and say which object.
    """
    names = [name for _kind, name in _CREATES.findall(migration.sql)]
    if not names:
        return
    rows = conn.execute(
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = current_schema() AND c.relname = ANY(%s)",
        (names,),
    ).fetchall()
    existing = sorted(r[0] for r in rows)
    if existing:
        raise SchemaDiverged(
            f"refusing to apply {migration.filename}: it creates "
            f"{existing}, which already exist in this database and are not "
            "recorded in the ledger.\n"
            "\n"
            "  This is NOT automatically resolved by recording it as applied. "
            "That the objects exist does not mean they match what "
            "contract/tables.sql describes, and recording a migration whose "
            "shape nobody compared is how two databases quietly stop agreeing.\n"
            "\n"
            "  A database created by `db init` should never reach this: that "
            "path stamps the ledger at head, because a schema built from "
            "tables.sql is by definition current. So this database was built "
            "some other way, and what it actually contains has to be "
            "established before anything is written down about it."
        )


def migrate(conn, directory: Path | None = None) -> list[str]:
    """Apply pending migrations in order. Returns what was applied.

    EVERY CHECK HAPPENS BEFORE ANY WORK. A mismatch anywhere refuses the whole
    run, because an edited applied migration means two databases already disagree
    and applying more compounds it.

    Each file is applied with its ledger row in ONE transaction, so a failure
    leaves neither the change nor the claim that it was made.
    """
    status = check(conn, directory)
    if status.mismatched:
        raise MigrationLedgerMismatch(
            f"refusing to apply anything: {status.describe()} "
            "An edited or missing applied migration means two databases already "
            "differ; applying more would compound it. Resolve the divergence "
            "first — the file's history is the evidence, not this ledger."
        )

    ensure_ledger(conn)
    migrations = {m.filename: m for m in discover(directory)}
    applied: list[str] = []
    for filename in status.pending_filenames:
        migration = migrations[filename]
        # Before any work: does this migration's output already exist? See
        # `_refuse_if_objects_exist` for why that refuses rather than records.
        _refuse_if_objects_exist(conn, migration)
        with conn.transaction():
            conn.execute(migration.sql)
            conn.execute(
                f"INSERT INTO {LEDGER} (filename, content_hash) VALUES (%s, %s)",  # noqa: S608
                (migration.filename, migration.content_hash),
            )
        log.info("migrate: applied %s", filename)
        applied.append(filename)
    return applied
