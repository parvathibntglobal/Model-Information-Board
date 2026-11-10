"""Kite Pulse outreach database: the MIB guard and the migration ledger.

No database: the guards are checked on DSNs and a fake connection, and the
ledger logic is a pure function of the files and the ledger rows.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

OUTREACH = Path(__file__).resolve().parent.parent / "web" / "src" / "kitepulse" / "outreach"
if str(OUTREACH) not in sys.path:
    sys.path.insert(0, str(OUTREACH))

import setup_db  # noqa: E402
from common import db  # noqa: E402
from common import thread as t  # noqa: E402
from setup_db import Migration, migrations, pending  # noqa: E402

MIB = "postgresql://postgres:pw@localhost:5432/model_information_board_local"
KP = "postgresql://postgres:pw@localhost:5432/kite_pulse_outreach_local"


# --- the MIB guard ----------------------------------------------------------

def test_the_url_is_kite_pulses_own_with_no_fallback(monkeypatch):
    monkeypatch.delenv(db.ENV, raising=False)
    monkeypatch.setenv(db.MIB_ENV, MIB)
    with pytest.raises(db.OutreachDbError, match="KP_OUTREACH_DATABASE_URL is not set"):
        db.dsn_from_env()
    monkeypatch.setenv(db.ENV, f" {KP} ")
    assert db.dsn_from_env() == KP


@pytest.mark.parametrize("same", [
    MIB,
    "postgresql://other:pw@127.0.0.1/model_information_board_local",   # default port, IP
    "host=LOCALHOST port=5432 dbname=model_information_board_local",
])
def test_a_url_naming_mibs_database_is_refused(same):
    with pytest.raises(db.OutreachDbError, match="same database"):
        db.refuse_mib_dsn(same, MIB)


def test_a_different_database_or_port_is_not_mibs():
    db.refuse_mib_dsn(KP, MIB)
    db.refuse_mib_dsn("postgresql://localhost:5433/model_information_board_local", MIB)
    db.refuse_mib_dsn(KP, None)


class _Conn:
    """Answers to_regclass for the tables it holds."""

    class info:
        dbname, host, port = "x", "localhost", 5432

    def __init__(self, tables):
        self.tables = tables

    def execute(self, _sql, params):
        name = params[0].removeprefix("public.")

        class _R:
            def fetchone(_self):
                return (name if name in self.tables else None,)
        return _R()


def test_a_database_holding_mib_tables_is_refused_whatever_its_url():
    with pytest.raises(db.OutreachDbError, match="document"):
        db.refuse_mib_tables(_Conn({"document", "kp_outreach_thread"}))
    db.refuse_mib_tables(_Conn({"kp_outreach_thread", "kp_outreach_migration"}))


# --- the ledger -------------------------------------------------------------

A = Migration("20260101T0000_a.sql", "aaa", "")
B = Migration("20260102T0000_b.sql", "bbb", "")


def test_pending_is_what_the_ledger_lacks_in_file_order():
    assert pending([A, B], {}) == [A, B]
    assert pending([A, B], {A.filename: "aaa"}) == [B]
    assert pending([A, B], {A.filename: "aaa", B.filename: "bbb"}) == []


def test_an_applied_file_that_changed_stops_everything():
    with pytest.raises(db.OutreachDbError, match="changed since: 20260101T0000_a.sql"):
        pending([A, B], {A.filename: "edited"})


def test_an_applied_file_that_is_gone_stops_everything():
    with pytest.raises(db.OutreachDbError, match="no longer in"):
        pending([B], {A.filename: "aaa"})


def test_the_hash_ignores_line_endings_but_not_content(tmp_path):
    # A Windows checkout (core.autocrlf=true) writes CRLF; git stores LF. Both
    # are the same migration and must hash alike, or every applied file reads
    # as edited after a branch switch.
    lf = tmp_path / "lf"
    crlf = tmp_path / "crlf"
    lf.mkdir()
    crlf.mkdir()
    git_bytes = b"CREATE TABLE kp_outreach_a (\n  id int\n);\n"
    (lf / "20260101T0000_a.sql").write_bytes(git_bytes)
    (crlf / "20260101T0000_a.sql").write_bytes(git_bytes.replace(b"\n", b"\r\n"))
    [m_lf], [m_crlf] = migrations(lf), migrations(crlf)
    assert m_lf.sha256 == m_crlf.sha256
    assert m_lf.sha256 == setup_db.hashlib.sha256(git_bytes).hexdigest()
    edited = git_bytes.replace(b"_a", b"_b").replace(b"\n", b"\r\n")
    (crlf / "20260101T0000_a.sql").write_bytes(edited)
    [m_edit] = migrations(crlf)
    assert m_edit.sha256 != m_lf.sha256


def test_a_missing_database_is_created_only_on_a_local_host():
    with pytest.raises(db.OutreachDbError, match="not local"):
        setup_db._create_database("postgresql://u:p@db.example.com:5432/kite_pulse_outreach")


# --- the shipped migrations -------------------------------------------------

def test_the_shipped_migrations_are_named_in_order_and_touch_only_kp_tables():
    files = migrations()
    assert [m.filename for m in files] == sorted(m.filename for m in files)
    for m in files:
        assert re.fullmatch(r"\d{8}T\d{4}_[a-z0-9_]+\.sql", m.filename), m.filename
        code = re.sub(r"--[^\n]*", "", m.sql)
        touched = re.findall(r"\b(?:CREATE (?:TABLE|INDEX)|ALTER TABLE|ON)\s+(\w+)", code)
        assert touched and all(n.startswith("kp_outreach_") for n in touched), touched


def test_the_thread_table_has_a_column_for_every_field_of_the_record():
    sql = (OUTREACH / "migrations" / "20261109T0000_kp_outreach_thread.sql").read_text(
        encoding="utf-8")
    columns = set(re.findall(r"^\s{2}(\w+)\s+(?:text|timestamptz|bigserial)", sql, re.M))
    fields = set(t.Thread.__dataclass_fields__)
    assert fields <= columns, f"record fields with no column: {fields - columns}"
    statuses = set(re.findall(r"'(\w+)'", sql.split("status_ck")[1].split(")")[0]))
    assert {t.STATUS_FOUND, t.STATUS_DROPPED} <= statuses
