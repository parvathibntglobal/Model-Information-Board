"""#328 / #355: which commands take the write gate, enumerated rather than assumed.

The writeguard refuses one pairing — `ENVIRONMENT=development` pointed at a
database that is not this machine — because the development flag switches OFF
the build-fixture guard and is set for reasons that have nothing to do with
writing.

⚠ IT COVERED `judge/cli.py` AND NOT `scripts/fetch_model.py`, AND THE COVERAGE
  WAS INVERTED WITH RESPECT TO RISK:

      judge rebuild-cells    REFUSED    derives `cell` from claims already
                                        stored. No model call, no new
                                        information, nothing spent.
      scripts/fetch_model.py NOT        runs E5-E7 in process, pays a model,
                                        and writes `claim`, `board_entry` and
                                        `cell` to the same database.

  A guard that stops the recomputation and permits the origination is not
  calibrated to anything. The reason was structural rather than a judgement:
  the guard sits in `judge/cli.py`'s connection helper, and a script in
  `scripts/` composes the pipeline itself through a lazy in-function import,
  so it never passes the door the guard is on.

⚠ AND THE REFUSAL'S OWN MESSAGE ADVERTISES THE WAY AROUND IT — it names
  `ENVIRONMENT=staging` as something that also satisfies the check. It says in
  the same breath that this is not a substitute, but it is one keystroke, and
  the person reading it is mid-incident. Root `CLAUDE.md` records guards being
  stepped around twice for exactly that reason.

⚠ NOTHING TESTED WHICH COMMANDS TOOK THE GATE (#355). `grep` was the method,
  and grep answers a question about today. This enumerates the population, so
  a new script that reaches the database is either guarded or listed here with
  the reason it does not need to be.

WHAT A WAIVER MEANS HERE. Same shape as #275's: a module that cannot be
guarded, or does not need to be, is DECLARED rather than silently passing. The
list is the output — it is the set of database-touching entry points nobody is
gating, written down.
"""

from __future__ import annotations

import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

#: Modules that reach the database and deliberately do not call the writeguard.
#: Each one carries WHY, because a waiver with no reason is a name on a list.
#:
#: ⚠ "IT ONLY READS" IS A CLAIM ABOUT WHAT THE CODE DOES TODAY, and the
#:   writeguard's own docstring rejects that argument for `judge extract`. It
#:   is accepted here only where the module has no write verb at all — if one
#:   is added, the verb check below fails and the waiver has to be revisited.
READ_ONLY: dict[str, str] = {
    "_blob_presence_check.py": "counts blobs present in the raw store; no write verb",
    "_blog_extraction_yield.py": "measures yield from stored rows; no write verb",
    "_comparison_post_extraction.py": "measurement only; no write verb",
    "_normaliser_disagreement.py": "measurement only; no write verb",
    "_six_host_probe.py": "measurement only; no write verb",
    "corpus_inventory.py": "counts the corpus; no write verb",
    "dump_keywords.py": "prints what each platform is sent; no write verb",
    "measure_key_constraint.py": "measurement only; no write verb",
    "measure_signal_demotion_platforms.py": "measurement only; no write verb",
    "triage_stored_corpus.py": "re-triages in memory and reports; no write verb",
    "write_report.py": "writes a FILE, not the database; no SQL write verb",
}

#: Guarded by something STRONGER than the writeguard, and named rather than
#: folded in with the read-only set — the distinction is the point.
GUARDED_OTHERWISE: dict[str, str] = {
    "harvest_github.py": (
        "`checked_dsn` runs all three disposability layers from the suite — "
        "`assert_safe_target` then `assert_disposable` — so it refuses any "
        "database that is not disposable, which is a strictly narrower target "
        "than the writeguard's one pairing"
    ),
}

#: ⚠ MATCHED IN STRING LITERALS ONLY, AND CASE-SENSITIVELY WHERE IT MATTERS.
#:   The first version upper-cased the whole source and searched for "COPY ",
#:   which matched the ordinary English word "copy" in a docstring and reported
#:   `dump_keywords.py` as a write path. Thirteenth instance of mention-versus-
#:   use here: a check for SQL that reads prose as SQL.
WRITE_VERBS = re.compile(
    r"(?is)\b(?:INSERT\s+INTO|UPDATE\s+\w|DELETE\s+FROM|COPY\s+\w+\s+FROM)\b"
)


def _sql_write_verbs(source: str) -> list[str]:
    """Write verbs found in this module's STRING LITERALS. SQL lives there."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found += [m.group(0) for m in WRITE_VERBS.finditer(node.value)]
    return found


def _touches_the_database(source: str) -> bool:
    return "DATABASE_URL" in source


def _calls_the_writeguard(source: str) -> bool:
    """A real call, not the word.

    ⚠ AST RATHER THAN A SUBSTRING, because every module in the waiver lists
      below mentions the writeguard in a comment explaining why it does not
      call it — and a grep would read those sentences as compliance. That is
      the mention-versus-use trap, which this repository has now hit enough
      times to write the guard first.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
        if name in ("writeguard_check", "check") and node.args:
            return True
    return False


def _database_scripts() -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(SCRIPTS.glob("*.py"))
        if _touches_the_database(path.read_text(encoding="utf-8", errors="replace"))
    }


class TestEveryDatabaseScriptIsGuardedOrDeclared:
    def test_no_script_reaches_the_database_unaccounted_for(self):
        """The enumeration. A new script is either guarded or listed, and
        neither happens by accident."""
        declared = set(READ_ONLY) | set(GUARDED_OTHERWISE)
        unaccounted = sorted(
            name for name, src in _database_scripts().items()
            if name not in declared and not _calls_the_writeguard(src)
        )
        assert not unaccounted, (
            f"{len(unaccounted)} script(s) read DATABASE_URL, do not call the "
            f"writeguard, and are not declared: {unaccounted}. Call "
            f"`judge.writeguard.check(dsn, command=...)` before connecting, or "
            f"add it to READ_ONLY with the reason."
        )

    def test_the_path_that_originates_claims_is_guarded(self):
        """⚠ THE SPECIFIC INVERSION #328 WAS OPENED FOR. If this one ever goes
        back to unguarded while `judge rebuild-cells` stays refused, the guard
        is again stopping the cheap safe operation and permitting the
        expensive one."""
        source = (SCRIPTS / "fetch_model.py").read_text(encoding="utf-8")
        assert _calls_the_writeguard(source)

    def test_the_originating_path_has_a_named_escape_flag(self):
        """⚠ A BARE GUARD GETS STEPPED AROUND, AND THE STEP-AROUND IS
        INVISIBLE. Ruled by @anoojntglobal-sudo on #328: `check()` refuses
        ENVIRONMENT=development against a remote database, which is how every
        fetch against staging is run — so a guard with no flag leaves exactly
        one way through, the `ENVIRONMENT=staging` edit the refusal message
        itself disowns, and nothing records that somebody made it.

        `--development-write` swaps the proxy for the condition it stands in
        for, per run, and prints itself into the run log."""
        source = (SCRIPTS / "fetch_model.py").read_text(encoding="utf-8")
        assert '"--development-write"' in source
        assert "args.development_write" in source

    def test_the_flag_replaces_the_proxy_rather_than_removing_the_check(self):
        """⚠ THE FAILURE MODE OF AN ESCAPE FLAG IS THAT IT ESCAPES EVERYTHING.
        The flag's whole justification is that it keeps a check — a narrower
        and exact one — so a version that only skipped the writeguard would be
        the bypass wearing the ruling's clothes."""
        source = (SCRIPTS / "fetch_model.py").read_text(encoding="utf-8")
        assert 'provenance == "seed"' in source
        assert "refused: seeded model" in source

    def test_the_seeded_check_runs_before_the_harvest_too(self):
        """Same reason as the proxy: a harvest already run is rate limit
        already spent, and E5 after it costs money."""
        source = (SCRIPTS / "fetch_model.py").read_text(encoding="utf-8")
        body = source[source.index("def main(argv"):]
        assert body.index('provenance == "seed"') < body.index("harvest_github(")

    def test_the_guard_runs_before_anything_is_harvested_or_paid_for(self):
        """A refusal that arrives after E2 has harvested and E5 has paid for
        extraction is a refusal that costs money to deliver."""
        source = (SCRIPTS / "fetch_model.py").read_text(encoding="utf-8")
        # ⚠ INSIDE `main`, NOT ACROSS THE FILE. The first version compared
        #   against the first occurrence of `harvest_github(`, which is its
        #   DEFINITION near the top — so it reported the guard as running too
        #   late in a file where it runs first. A position test has to be
        #   scoped to the function whose order it is asserting.
        body = source[source.index("def main(argv"):]
        guard = body.index("writeguard_check(")
        for later in ("harvest_github(", "harvest_reddit("):
            assert body.index(later) > guard, f"{later} runs before the guard"

    def test_a_read_only_waiver_has_no_write_verb(self):
        """⚠ THE WAIVER IS CHECKED, NOT TAKEN ON TRUST. "It only reads" is a
        claim about what the code does today, and the writeguard's docstring
        rejects that argument elsewhere. If a write verb appears in a waived
        module, the waiver is wrong and this says so before the write lands."""
        offenders = {}
        scripts = _database_scripts()
        for name in READ_ONLY:
            found = _sql_write_verbs(scripts.get(name, ""))
            if found:
                offenders[name] = found
        assert not offenders, (
            f"declared read-only but carrying a write verb: {offenders}"
        )

    def test_every_waiver_says_why(self):
        for name, why in {**READ_ONLY, **GUARDED_OTHERWISE}.items():
            assert why and len(why) > 15, f"{name} is waived with no real reason"

    def test_no_waiver_names_a_script_that_is_gone(self):
        """A waiver for a deleted script makes the list look shorter than the
        gap it describes."""
        scripts = set(_database_scripts())
        stale = sorted((set(READ_ONLY) | set(GUARDED_OTHERWISE)) - scripts)
        assert not stale, f"waivers for scripts that no longer touch the database: {stale}"


class TestTheDetectorIsNotFooledByTheWordItself:
    def test_a_comment_naming_the_guard_is_not_a_call(self):
        source = "# writeguard_check(dsn) would go here\nx = 1\n"
        assert not _calls_the_writeguard(source)

    def test_an_import_without_a_call_is_not_a_call(self):
        """⚠ THE ONE THAT WOULD HAVE PASSED A NAIVE CHECK. Importing the guard
        and never calling it is exactly what a half-finished wiring looks
        like, and it reads as compliance from either end."""
        source = "from judge.writeguard import check\n"
        assert not _calls_the_writeguard(source)

    def test_a_real_call_is_detected(self):
        source = "from judge.writeguard import check\ncheck(dsn, command='x')\n"
        assert _calls_the_writeguard(source)
