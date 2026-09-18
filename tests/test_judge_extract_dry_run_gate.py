"""`judge extract --dry-run` takes no write gate, because it has nothing to write.

`_connect(writing=...)` turns on `judge/writeguard.py`, which refuses
`ENVIRONMENT=development` against a database that is not this machine. That is
correct for a run that pays a model and writes claims. It was also applied to
`--dry-run`, which returns before the `--driver` branch, before
`_extract_from_export`, and before the only `commit()` on the path — so the one
command you would reach for to ask "what is pending, and can the budget afford
it" was refused from the laptops where the question gets asked.

`judge reweight` already spells this `writing=... if args.apply else None`, and
its dry run is the WEAKER case: it opens a transaction, writes, and rolls back.
This one issues two `SELECT`s and returns.

WHY THESE TESTS ARE BEHAVIOURAL AND WHAT THEY DO NOT COVER
----------------------------------------------------------
They cover the two commands that exist. They cannot see the next command added
without the conditional — for that, `tests/test_cli_write_gate.py`'s shape over
`collect/cli.py` is the right one, and an AST test over `judge/cli.py` asserting
that every `_connect(writing=...)` in a command whose parser declares
`--dry-run` or `--apply` is conditioned on that flag is filed separately. It is
deliberately not in this commit: a test written alongside the two commands it
describes agrees with them by construction.
"""

from __future__ import annotations

import argparse

import pytest

import judge.cli as cli

# TEST-NET-1, reserved for documentation, so this file adds no occurrence of the
# real infrastructure address. All the guard cares about is that it is not here.
REMOTE = "postgresql://user:pw@192.0.2.10:5432/Model-information-Board"


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _Conn:
    """Answers the two SELECTs the dry-run path makes, and records everything.

    `transaction` is present and recorded rather than absent, so "the dry run
    opened no transaction" is an assertion rather than an AttributeError that
    would also pass if the call were removed.
    """

    def __init__(self):
        self.statements: list[str] = []
        self.transactions = 0
        self.commits = 0

    def execute(self, sql, params=None):
        self.statements.append(sql)
        if "count(*)" in sql:
            return _Result([(0, 0)])
        # `already_extracted()` -> {thread_context_id: content_fingerprint}
        return _Result([("thread_context_aaa", "fp1"), ("thread_context_bbb", "fp2")])

    def transaction(self):
        self.transactions += 1
        raise AssertionError("the dry-run path must not open a transaction")

    def commit(self):
        self.commits += 1
        raise AssertionError("the dry-run path must not commit")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture(autouse=True)
def _a_development_laptop_pointed_at_the_shared_database(monkeypatch):
    """The pairing the guard refuses, and the normal state of a laptop.

    `ENVIRONMENT=development` is what makes sign-in accept the credentials in
    `.env.example`, so anyone running the UI locally against staging has it set
    for reasons that have nothing to do with writing.
    """
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", REMOTE)
    monkeypatch.delenv("EXTRACTION_DAILY_BUDGET_USD", raising=False)


@pytest.fixture
def conn(monkeypatch):
    import psycopg

    made = _Conn()
    monkeypatch.setattr(psycopg, "connect", lambda url, **kwargs: made)
    return made


def _args(**over):
    base = {"dry_run": False, "driver": None, "from_export": None}
    base.update(over)
    return argparse.Namespace(**base)


def test_a_dry_run_is_not_refused_against_a_shared_database(conn, capsys):
    assert cli._cmd_extract(_args(dry_run=True)) == 0
    assert "nothing extracted, nothing charged" in capsys.readouterr().out


def test_a_dry_run_only_reads(conn):
    cli._cmd_extract(_args(dry_run=True))

    assert conn.statements, "the dry run made no query at all - it reports counts"
    non_select = [s for s in conn.statements if not s.lstrip().upper().startswith("SELECT")]
    assert not non_select, f"the dry-run path issued a non-SELECT: {non_select}"
    assert conn.transactions == 0
    assert conn.commits == 0


def test_a_dry_run_reports_what_is_already_extracted(conn, capsys):
    """The count `seen` holds, which used to be queried and never printed.

    It is ALREADY-EXTRACTED and not pending. There is no pending count on this
    path, deliberately: it needs the thread list `collect/` owns, and inventing
    one here would be a figure with no population (rule 7).
    """
    cli._cmd_extract(_args(dry_run=True))

    out = capsys.readouterr().out
    assert "2 threads already extracted and will be skipped" in out
    assert "pending" not in out


def test_the_same_command_without_dry_run_is_still_refused(conn, monkeypatch):
    """The half that must not change. A real run spends money and writes claims."""
    monkeypatch.setenv("EXTRACTION_DAILY_BUDGET_USD", "1.00")

    from judge import spend_ledger

    monkeypatch.setattr(spend_ledger, "spent_today", lambda *a, **k: 0.0)

    with pytest.raises(SystemExit) as raised:
        cli._cmd_extract(_args(dry_run=False))

    message = str(raised.value)
    assert "192.0.2.10" in message
    assert "judge extract" in message
    assert not conn.statements, "it must refuse before the connection is used"
