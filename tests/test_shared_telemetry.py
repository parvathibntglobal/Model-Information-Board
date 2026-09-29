"""Spend, fetch logs and quota become team figures without becoming fragile.

WHAT CHANGED ON 2026-09-11. Three pieces of state lived only on the machine
that produced them — `var/spend-ledger.jsonl`, `var/fetch/<run>.jsonl` and
`var/rapidapi-quota.json` — so no figure on the usage panel was ever a team
figure. They now mirror into `spend_ledger`, `fetch_log` and `rapidapi_quota`.

These tests guard the four things that make that safe rather than merely
shared, each of which has a specific way of going wrong:

  1. THE FILE STAYS THE SURVIVOR. The fetch log is a file precisely so a run
     dying BECAUSE the database is unreachable can still say so. A mirror that
     raises, or that replaces the file, destroys the property.
  2. IDS ARE CONTENT-DERIVED. The ledger had no primary key, so a backfill
     without one inflates the team's dollar total on every re-run.
  3. A MISSING DATABASE IS NOT AN EMPTY ONE. `None`, not `[]` — otherwise an
     outage renders as "nobody spent anything".
  4. NEWEST READING WINS, NOT NEWEST WRITE. The quota is a decreasing counter
     two machines race on.
"""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime, timedelta, timezone

import pytest

from judge import spend_ledger

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Two blank lines — the gap between top-level definitions, used to cut one
#: function's body out of a source file without parsing it.
BLANK = "\n\n\n"


def _call(**kw) -> spend_ledger.Call:
    base = dict(
        at=datetime(2026, 9, 11, 10, 0, tzinfo=UTC),
        stage="extract",
        model="deepseek/deepseek-v4-flash",
        input_tokens=100,
        output_tokens=10,
        usd=0.001,
        unmetered=False,
        machine="host-a",
    )
    base.update(kw)
    return spend_ledger.Call(**base)


class TestTheLedgerFinallyHasAKey:
    def test_the_same_call_recorded_twice_is_one_id(self):
        assert _call().id == _call().id

    def test_two_machines_making_the_same_call_stay_two_rows(self):
        # THE MONEY REASON. Two people running a fetch in the same second with
        # the same prompt is two real calls costing two real amounts. Hashing
        # content alone would keep one and silently lose the other's spend.
        assert _call(machine="host-a").id != _call(machine="host-b").id

    def test_two_runs_on_one_machine_stay_two_rows(self):
        assert _call(run_id="r1").id != _call(run_id="r2").id

    def test_a_different_token_count_is_a_different_call(self):
        assert _call(input_tokens=100).id != _call(input_tokens=101).id

    def test_the_id_does_not_depend_on_the_dollar_amount(self):
        # Price can be recomputed — a rate can be added to MODEL_PRICING after
        # the fact. If `usd` were in the hash, re-pricing a call would mint a
        # second row for it and double it.
        assert _call(usd=0.001).id == _call(usd=0.002).id

    def test_the_id_survives_a_timezone_round_trip(self):
        utc = _call(at=datetime(2026, 9, 11, 10, 0, tzinfo=UTC))
        ist = timezone(timedelta(hours=5, minutes=30))
        other = _call(at=datetime(2026, 9, 11, 15, 30, tzinfo=ist))
        assert utc.id == other.id, "the same instant must hash the same"


class TestAnUnreachableDatabaseIsNotAnEmptyOne:
    def test_read_database_returns_none_when_it_cannot_connect(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
        assert spend_ledger.read_database() is None

    def test_read_everywhere_says_so_rather_than_showing_a_short_total(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
        ledger = tmp_path / "spend.jsonl"
        ledger.write_text(_call().as_row() + "\n", encoding="utf-8")
        calls, readable = spend_ledger.read_everywhere(ledger)
        assert len(calls) == 1
        assert readable is False, (
            "a total covering one machine must be distinguishable from one "
            "covering the team, or an outage renders as a spending drop"
        )

    def test_the_report_carries_the_flag(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
        ledger = tmp_path / "spend.jsonl"
        ledger.write_text("", encoding="utf-8")
        report = spend_ledger.report(
            daily_cap_usd=1.0, estimated_call_usd=0.01, path=ledger
        )
        assert report.db_readable is False
        assert report.total_is_a_floor is True

    def test_an_unpriced_call_alone_makes_the_total_a_floor(self):
        # The third reason, independent of the database. A model with no
        # published rate records real TOKENS and $0.00, so a dollar total
        # containing one understates the spend — and reads as free.
        from judge.spend_ledger import Report

        complete = Report(
            daily_cap_usd=1.0, spent_today_usd=0.0, calls_today=1,
            unmetered_today=0, hourly=[], daily=[], by_stage_usd={},
            by_stage_calls={}, by_model_usd={}, stages_ever_recorded=("extract",),
            pricing_in_per_million=0.0, pricing_out_per_million=0.0,
            estimated_call_usd=0.0,
            first_seen_at=datetime(2026, 9, 1, tzinfo=UTC),
            total_rows=1, day_starts_at=datetime(2026, 9, 11, tzinfo=UTC),
            db_readable=True, machines=("host-a",), unpriced_today=0,
        )
        assert complete.total_is_a_floor is False

        from dataclasses import replace

        assert replace(complete, unpriced_today=1).total_is_a_floor is True


class TestTheFileRemainsTheSurvivor:
    def test_record_writes_the_file_even_with_no_database(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
        ledger = tmp_path / "spend.jsonl"
        spend_ledger.record(
            stage="extract", model="deepseek/deepseek-v4-flash",
            input_tokens=10, output_tokens=2, path=ledger,
        )
        assert ledger.exists() and ledger.read_text(encoding="utf-8").strip()

    def test_append_to_database_never_raises(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
        assert spend_ledger.append_to_database([_call()]) == 0

    def test_the_progress_mirror_never_raises(self):
        # A mirror that can raise turns "the database is down" into "the run
        # died and left no log", which is the exact failure the file exists to
        # prevent. Checked at the seam rather than by running a fetch.
        src = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
        body = src[src.index("def _mirror_fetch_line("):]
        body = body[: body.index("\n\n\n")] if "\n\n\n" in body else body
        assert "except Exception:" in body
        assert "return False" in body

    def test_the_file_is_written_before_the_mirror(self):
        # MATCHED ON THE NAME, AND SLICED TO THE REAL END OF THE METHOD.
        #
        # This pinned the full signature `def _write(self, rec: dict)` and took a
        # fixed 900-character window after it. Both broke on a change that left
        # the property intact: `_write` grew a keyword argument and a few lines,
        # and the test failed with `ValueError: substring not found` - which
        # reads as the seam being gone rather than as the matcher being brittle.
        #
        # A source test earns its brittleness only where the source IS the
        # subject. Here the subject is the ORDER of two statements, so the
        # matcher should survive anything that does not reorder them.
        src = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
        write = src.index("    def _write(self")
        body = src[write:]
        # The next method at the same indent ends this one.
        body = body[: body.index("\n    def ", 1)]
        assert body.index("self.path.open") < body.index("_mirror_fetch_line"), (
            "the file write must come first: it is the one that still works "
            "when the database is what has failed"
        )


class TestAnOutageDoesNotBecomeALatencyTax:
    """The regression this nearly shipped with.

    `spent_today()` is the cap check that runs BEFORE EVERY MODEL CALL, and
    `record_rapidapi_quota()` runs on every metered harvest request. Routing
    both through a 10-second connection meant an unreachable database added a
    connect timeout to each one — measured at 2.66s per attempt, which turned a
    172-second test suite into a ten-minute one and would have been a per-call
    tax in production. The timeout is shorter here than for a board read, and a
    failure stops it asking again for a while.
    """

    def test_the_telemetry_timeout_is_shorter_than_a_board_read(self):
        from judge.store.claims import CONNECT_TIMEOUT_SECONDS

        assert spend_ledger.TELEMETRY_CONNECT_TIMEOUT < CONNECT_TIMEOUT_SECONDS

    def test_a_failure_stops_it_retrying_for_a_while(self, monkeypatch):
        import time

        monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
        spend_ledger.reset_telemetry_backoff()
        assert spend_ledger.read_database() is None      # pays the timeout once

        started = time.monotonic()
        for _ in range(25):
            assert spend_ledger.read_database() is None
        assert time.monotonic() - started < 0.5, (
            "25 reads after a known failure must cost nothing; without the "
            "backoff this is 25 connect timeouts"
        )

    def test_the_backoff_can_be_cleared(self):
        # A backoff nobody can clear is a cache, and a stale one would keep
        # reporting a floor long after the database came back.
        spend_ledger.reset_telemetry_backoff()
        assert spend_ledger._unreachable_until == 0.0

    def test_both_lanes_have_one(self, monkeypatch):
        from collect import usage

        assert usage.TELEMETRY_CONNECT_TIMEOUT == spend_ledger.TELEMETRY_CONNECT_TIMEOUT
        assert (
            usage.TELEMETRY_RETRY_AFTER_SECONDS
            == spend_ledger.TELEMETRY_RETRY_AFTER_SECONDS
        )
        usage.reset_telemetry_backoff()

    def test_the_file_write_still_happens_while_the_backoff_is_in_force(
        self, monkeypatch, tmp_path
    ):
        # The backoff must skip the MIRROR, never the record itself.
        from collect import usage

        monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
        target = tmp_path / "q.json"
        assert usage.record_rapidapi_quota(
            remaining=5, limit=10, read_on="reddit", path=target
        ) is True
        assert usage.record_rapidapi_quota(
            remaining=4, limit=10, read_on="reddit", path=target
        ) is True
        assert json.loads(target.read_text(encoding="utf-8"))["meters"]["reddit"][
            "quota_remaining"
        ] == 4


class TestATestCannotWriteToTheSharedDatabase:
    """The guard that was missing, and what it cost.

    Every other table here is protected by the suite's disposable-database
    fixtures. These writers bypassed all of it by reading DATABASE_URL from the
    environment, and a developer `.env` points that at the SHARED database. The
    first full run after they were wired put 110 test spend rows worth $0.30
    into the team's ledger, 11 lines into its fetch log, and overwrote a genuine
    Reddit quota reading with a fixture's.

    The guard belongs in the WRITER. A conftest fixture is a second layer that
    any test can clear, and the next person to clear it repeats the incident.
    """

    def test_the_writer_refuses_under_pytest(self, monkeypatch):
        # This test IS running under pytest, so the guard must be active even
        # with a DSN that would otherwise connect.
        monkeypatch.delenv("MODELBOARD_ALLOW_TEST_TELEMETRY", raising=False)
        spend_ledger.reset_telemetry_backoff()
        assert spend_ledger._telemetry_connection("postgresql://x@127.0.0.1:5432/y") is None

    def test_both_lanes_refuse(self, monkeypatch):
        from collect import usage

        monkeypatch.delenv("MODELBOARD_ALLOW_TEST_TELEMETRY", raising=False)
        usage.reset_telemetry_backoff()
        assert usage._telemetry_connection("postgresql://x@127.0.0.1:5432/y") is None

    def test_the_refusal_is_explicit_rather_than_incidental(self):
        for name in ("judge/spend_ledger.py", "collect/usage.py"):
            src = (ROOT / name).read_text(encoding="utf-8")
            assert 'os.getenv("PYTEST_CURRENT_TEST")' in src, name
            assert "MODELBOARD_ALLOW_TEST_TELEMETRY" in src, name

    def test_every_mirror_uses_the_guarded_connection(self):
        """The gap idempotence hid.

        `_mirror_fetch_line` used `collect.db.transaction()` — no test guard,
        no short timeout — so a full suite run wrote 11 fixture lines into the
        shared fetch_log. The first check for it came back clean because those
        lines were ALREADY there from an earlier run, and `on conflict do
        nothing` kept the row count flat. A count is not a leak detector when
        the write is idempotent; the call site is.
        """
        src = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
        body = src[src.index("def _mirror_fetch_line("):]
        body = body[: body.index(BLANK)] if BLANK in body else body
        assert "usage.telemetry_connection()" in body
        # The CALL form, not the phrase: the comment above it names
        # `db.transaction()` to explain why it is not used, and a test that
        # cannot tell a mention from a call fails on its own documentation.
        assert "with db.transaction()" not in body, (
            "an unguarded connection here escapes both the pytest refusal and "
            "the backoff"
        )

    def test_a_test_that_means_it_can_still_opt_in(self, monkeypatch):
        # Otherwise the mirror becomes untestable, and an untestable write path
        # is one nobody checks.
        monkeypatch.setenv("MODELBOARD_ALLOW_TEST_TELEMETRY", "1")
        monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
        spend_ledger.reset_telemetry_backoff()
        # Reaches the connection attempt and fails on the unreachable host,
        # rather than being refused by the guard.
        assert spend_ledger.read_database() is None
        assert spend_ledger._unreachable_until > 0.0, "it really tried"


class TestQuotaKeepsTheNewestReadingNotTheNewestWrite:
    def test_the_upsert_compares_read_at(self):
        src = (ROOT / "collect" / "usage.py").read_text(encoding="utf-8")
        assert "where excluded.read_at > rapidapi_quota.read_at" in src, (
            "two machines race on a decreasing counter; without this the later "
            "WRITE wins even when it carries the older READING"
        )

    def test_the_limit_is_still_not_inherited(self):
        src = (ROOT / "collect" / "usage.py").read_text(encoding="utf-8")
        upsert = src[src.index("insert into rapidapi_quota"):]
        upsert = upsert[: upsert.index("\"\"\"")] if '"""' in upsert else upsert
        assert "coalesce" not in upsert.lower(), (
            "a COALESCE on quota_limit restores exactly the inheritance the "
            "file writer refuses, and the arms are separately metered"
        )

    def test_a_reading_with_no_figures_is_refused_by_the_schema(self):
        sql = (ROOT / "contract" / "tables.sql").read_text(encoding="utf-8")
        assert "rapidapi_quota_has_a_figure_ck" in sql

    def test_recording_never_raises_without_a_database(self, monkeypatch, tmp_path):
        from collect import usage

        monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
        assert usage.record_rapidapi_quota(
            remaining=5, limit=10, read_on="reddit", path=tmp_path / "q.json"
        ) is True

    def test_read_database_meters_returns_none_not_empty(self, monkeypatch):
        from collect import usage

        monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
        assert usage.read_database_meters() is None


class TestTheSchemaSaysWhatItIsFor:
    @staticmethod
    def _tables() -> str:
        return (ROOT / "contract" / "tables.sql").read_text(encoding="utf-8")

    @pytest.mark.parametrize("table", ["spend_ledger", "fetch_log", "rapidapi_quota"])
    def test_the_table_exists_in_the_contract(self, table):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in self._tables()

    def test_the_migration_exists_and_explains_the_file_that_stays(self):
        m = ROOT / "contract" / "migrations" / "20260911T1000_shared_telemetry.sql"
        assert m.exists()
        body = m.read_text(encoding="utf-8").lower()
        assert "unreachable" in body, "it must say why the files are kept"
        assert "idempotent" in body or "content-derived" in body

    def test_spend_is_numeric_rather_than_float(self):
        # Money that gets summed across thousands of rows. A double accumulates
        # error in the direction nobody audits.
        assert "usd            numeric(16, 10) NOT NULL" in self._tables()

    def test_the_stage_set_stays_closed(self):
        assert "spend_ledger_stage_ck CHECK (stage IN ('extract', 'ask'))" in self._tables()

    def test_the_fetch_log_keeps_sequence_not_just_time(self):
        # Timestamps here are second-resolution and several lines share one.
        # Ordering a run by time alone scrambles it.
        assert "seq          integer NOT NULL" in self._tables()
        assert "fetch_log_run_seq_uq UNIQUE (run_id, seq)" in self._tables()


class TestMachineIsNotPerson:
    def test_the_column_is_called_machine(self):
        sql = (ROOT / "contract" / "tables.sql").read_text(encoding="utf-8")
        assert "machine        text NOT NULL" in sql
        assert "clicked_by" not in sql, (
            "this app has one account, so who clicked is genuinely unknown; a "
            "column claiming otherwise is rule 6 applied to ourselves"
        )

    def test_it_is_overridable_so_a_test_does_not_depend_on_its_host(self, monkeypatch):
        monkeypatch.setenv(spend_ledger.MACHINE_ENV, "ci-runner")
        assert spend_ledger.machine() == "ci-runner"

    def test_both_lanes_agree_on_the_variable_without_importing_each_other(self):
        from collect import usage

        assert usage.MACHINE_ENV == spend_ledger.MACHINE_ENV

    def test_it_never_returns_empty(self, monkeypatch):
        monkeypatch.setenv(spend_ledger.MACHINE_ENV, "   ")
        assert spend_ledger.machine().strip()


class TestTheBackfillIsIdempotent:
    def test_the_fetch_line_id_is_derived_from_content(self):
        # Same derivation in the writer and the backfill, or a re-run of the
        # backfill duplicates every line the writer already mirrored.
        writer = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
        backfill = (ROOT / "scripts" / "backfill_telemetry.py").read_text(encoding="utf-8")
        recipe = 'f"{run_id}|{seq}|{payload}".encode()'
        assert recipe in writer and recipe in backfill

    def test_both_writers_use_on_conflict_do_nothing(self):
        for name in ("scripts/fetch_model.py", "judge/spend_ledger.py"):
            src = (ROOT / name).read_text(encoding="utf-8")
            assert "on conflict (id) do nothing" in src, name

    def test_the_backfill_defaults_to_reporting_rather_than_writing(self):
        src = (ROOT / "scripts" / "backfill_telemetry.py").read_text(encoding="utf-8")
        assert '"--apply", action="store_true"' in src
        assert "conn.rollback()" in src


class TestTheTotalTravelsWithItsPopulation:
    def test_the_payload_counts_the_machines(self):
        """Rule 7 is satisfied by the COUNT. The roster was answering nothing.

        ⚠ THIS TEST USED TO REQUIRE THE NAMES, and it was right about the rule
          and wrong about what satisfies it. It asserted `"machines"` and
          `"this_machine"` were in the payload, so the denominator travelled -
          but a denominator is a NUMBER, and the roster shipped six hostnames
          including two personal ones onto a hosted admin page.

          Parvathi asked for them gone on 2026-09-16, for the second time: the
          first ask moved the roster into a tooltip, which still rendered it on
          hover. So the property to pin is "the total travels with its
          population SIZE", and the absence of the names is now part of it.

        `complete` stays because a floor reported as a total is the error this
        whole panel exists to avoid, and that is a different claim from how many
        hosts contributed.
        """
        src = (ROOT / "judge" / "app.py").read_text(encoding="utf-8")
        block = src[src.index('"basis": {'):]
        block = block[: block.index('"cap": {')]
        for field in ('"complete"', '"machine_count"'):
            assert field in block, field
        for gone in ('"machines": list(', '"this_machine"'):
            assert gone not in block, (
                f"{gone} puts a hostname in a payload that feeds a web page; "
                "the count is the denominator"
            )

    def test_an_incomplete_total_says_it_is_a_floor(self):
        src = (ROOT / "judge" / "app.py").read_text(encoding="utf-8")
        assert "is a floor" in src

    def test_per_model_totals_cover_the_same_population_as_the_headline(self):
        # Two figures on one page drawn from different populations disagree for
        # a reason nothing on the page states.
        src = (ROOT / "judge" / "app.py").read_text(encoding="utf-8")
        assert "all_calls, _ = spend_ledger.read_everywhere()" in src


class TestTheFetchLogEndpointDistinguishesItsSources:
    def test_it_reports_which_source_answered(self):
        src = (ROOT / "judge" / "app.py").read_text(encoding="utf-8")
        assert '"source": "local file"' in src
        assert '"source": "shared table"' in src

    def test_the_shared_read_orders_by_sequence(self):
        src = (ROOT / "judge" / "app.py").read_text(encoding="utf-8")
        block = src[src.index("def _fetch_log_from_db("):]
        assert "order by seq" in block[:1200]

    def test_a_prefix_match_cannot_claim_another_models_runs(self):
        # The same guard the file path has: `gpt-4` must not collect `gpt-4o`'s
        # runs through a LIKE prefix.
        src = (ROOT / "judge" / "app.py").read_text(encoding="utf-8")
        block = src[src.index("def _fetch_runs_from_db("):]
        assert "len(suffix) != 8" in block[:1500]


def test_an_unparseable_date_sorts_as_unknown_not_as_1970():
    from judge.app import _epoch_of

    assert _epoch_of(None) is None
    assert _epoch_of("not a date") is None
    assert _epoch_of("2026-09-11T10:00:00Z") == pytest.approx(
        datetime(2026, 9, 11, 10, 0, tzinfo=UTC).timestamp()
    )


def test_the_ledger_row_still_reads_back_when_it_predates_the_new_fields(tmp_path):
    """A file written before 2026-09-11 has no `machine` and no `run_id`."""
    old = {"at": "2026-08-27T11:17:08.306444+00:00", "stage": "extract",
           "model": "google/gemini-2.5-flash", "in": 6429, "out": 906,
           "usd": 0.0041937}
    ledger = tmp_path / "spend.jsonl"
    ledger.write_text(json.dumps(old) + "\n", encoding="utf-8")
    calls = spend_ledger.read_all(ledger)
    assert len(calls) == 1
    assert calls[0].machine, "attributed to the machine reading it, not left blank"
    assert calls[0].run_id is None
