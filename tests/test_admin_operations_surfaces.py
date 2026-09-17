"""The three operations surfaces, and the rules they may never break.

WHY THESE ARE PINNED BY A TEST RATHER THAN BY CARE. Each of the three reads
something that sits next to a secret: `/admin/settings` reads the environment a
key lives in, `/admin/database` reads the DSN that carries a password, and
`/admin/runs` reads a table whose `machine` column is a person's laptop name.
A field added later is written by somebody who is thinking about the field, not
about what is beside it.

⚠ THE SWEEP IS OVER THE WHOLE PAYLOAD AS TEXT, NOT FIELD BY FIELD. That is the
  lesson from the usage panel: a field-by-field check for anything named
  "machine" came back clean while a hostname was sitting inside a prose sentence
  in `source_of_record`. A serialized-and-grepped payload cannot be passed by a
  leak in a place nobody thought to look.
"""

from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    # Named values that must never come back, set to strings a grep can find.
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-TESTSECRET-openrouter")
    monkeypatch.setenv("RAPIDAPI_KEY", "TESTSECRET-rapidapi-key")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_TESTSECRET_github")
    monkeypatch.setenv("SESSION_SECRET", "TESTSECRET-session-signing")
    monkeypatch.setenv("AUTH_PASSWORD_HASH", "TESTSECRET$argon$hash")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://dbuser:TESTSECRET-dbpassword@db.example.net:5432/boarddb",
    )
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")

    from judge.app import app

    return TestClient(app)


#: Every value planted above. A payload containing any of them has published it.
SECRETS = (
    "sk-or-TESTSECRET-openrouter",
    "TESTSECRET-rapidapi-key",
    "ghp_TESTSECRET_github",
    "TESTSECRET-session-signing",
    "TESTSECRET$argon$hash",
    "TESTSECRET-dbpassword",
    "dbuser",
    # The DSN entire, and the host it names. The host is not a credential; it is
    # a reachable address, which is its own reason not to publish it.
    "postgresql://",
    "db.example.net",
)

SURFACES = ("/admin/settings", "/admin/database", "/admin/runs")


@pytest.mark.parametrize("path", SURFACES)
def test_no_secret_value_appears_anywhere_in_the_payload(client, path):
    response = client.get(path)
    # A surface that cannot reach the database still must not leak; 503 is an
    # acceptable answer here and an unchecked one is not.
    assert response.status_code in (200, 503), response.text
    body = response.text
    for secret in SECRETS:
        assert secret not in body, (
            f"{path} published {secret!r}. No value, prefix, length or hash of a "
            f"credential may leave the backend - the page says set / not set."
        )


def test_settings_reports_credentials_as_booleans_and_nothing_else(client):
    payload = client.get("/admin/settings").json()
    credentials = payload["credentials"]
    assert credentials, "the settings surface reports no credential at all"
    for entry in credentials:
        assert set(entry) == {"name", "set"}, (
            f"{entry['name']} carries more than presence: {sorted(entry)}"
        )
        assert isinstance(entry["set"], bool)


def test_a_cap_whose_name_looks_like_a_secret_is_blanked_unless_ruled_public(client):
    """The substring guard is the default, and a ruling is the only exception.

    `EXTRACT_MAX_OUTPUT_TOKENS` contains "TOKEN" and is a token COUNT, so it is
    ruled public by hand. Every other credential-shaped name must come back
    without a value even if somebody adds it to the cap list.
    """
    from judge.app import _is_secretish

    assert _is_secretish("EXTRACT_MAX_OUTPUT_TOKENS")
    assert _is_secretish("OPENROUTER_API_KEY")
    assert _is_secretish("DATABASE_URL")
    assert not _is_secretish("FETCH_MAX_THREADS")

    caps = {c["name"]: c for c in client.get("/admin/settings").json()["caps"]}
    # The ruled exception carries its value, because a count is not a token.
    assert caps["EXTRACT_MAX_OUTPUT_TOKENS"]["value"] is not None
    # And the guard is still on for everything nobody has ruled on.
    for name, cap in caps.items():
        if _is_secretish(name) and name != "EXTRACT_MAX_OUTPUT_TOKENS":
            assert cap["value"] is None, f"{name} published a value"


def test_database_names_the_database_without_naming_the_host():
    """Asserted on the helper, NOT through the endpoint, and deliberately.

    The endpoint answers 503 when it cannot connect - which is correct, and
    which would make this the sixth test in the file to skip on a machine with
    no database and quietly stop guarding anything. What is being guarded here
    is a pure function of the DSN, so it is tested as one.
    """
    from judge.app import _database_target

    body = _database_target(
        "postgresql://dbuser:TESTSECRET-dbpassword@db.example.net:5432/boarddb"
    )
    assert body["database"] == "boarddb"
    # A RELATION, NOT AN ADDRESS.
    assert body["host"] == "a remote host"
    text = json.dumps(body)
    for forbidden in ("db.example.net", "5432", "dbuser", "TESTSECRET-dbpassword"):
        assert forbidden not in text, f"the target published {forbidden!r}"

    assert _database_target(
        "postgresql://u:p@localhost:5432/boarddb")["host"] == "this machine"
    # ⚠ RULE 6. Unset, unparseable and connected are three different facts and
    # none of them is "the default database".
    assert _database_target(None)["unset"] is True
    assert _database_target("mysql://x/y")["unreadable"]


def test_runs_names_no_machine_at_all(client, monkeypatch):
    """⚠ The whole payload is grepped, not a field named "machine".

    A field-by-field check for anything named "machine" once passed while a
    hostname sat inside a prose sentence. This plants the name and greps the
    serialized payload for it, which no such leak can survive.

    Not even a RELATION now. The board is hosted and has one account, so "this
    machine" against "another host" was a distinction with nothing on the other
    side of it, and the field is gone rather than softened.
    """
    planted = "SOMEONES-LAPTOP-9000"
    monkeypatch.setenv("COMPUTERNAME", planted)

    response = client.get("/admin/runs")
    if response.status_code == 503:
        pytest.skip("no database to read")
    assert planted not in response.text
    for run in response.json()["runs"]:
        assert "host" not in run and "machine" not in run


def test_an_unfinished_run_is_not_claimed_to_be_alive(client):
    """⚠ RULE 6. Silence is reported as silence, never converted to a status.

    A run with no end record may be a corpse: a killed process writes nothing.
    `status` is what the run said and `looks_dead` is what was measured, and
    the two are never merged into one field.
    """
    response = client.get("/admin/runs")
    if response.status_code == 503:
        pytest.skip("no database to read")
    for run in response.json()["runs"]:
        if not run["finished"]:
            assert run["status"] is None, (
                "an unfinished run must carry no status - there is no end "
                "record to have read one from"
            )
            assert "looks_dead" in run and "silent_minutes" in run


def test_row_counts_distinguish_an_absent_table_from_an_empty_one(client):
    """⚠ RULE 6. A missing value never becomes a definite one."""
    response = client.get("/admin/database")
    if response.status_code == 503:
        pytest.skip("no database to read")
    counts = response.json()["counts"]
    # Every value is either an integer or None. A None is "this database does
    # not have this table", which is not zero, and the payload says so.
    for table, n in counts.items():
        assert n is None or isinstance(n, int), f"{table} reported {n!r}"
    assert "not zero" in response.json()["counts_absent_note"]


def test_migration_state_separates_the_three_ways_to_disagree(client):
    """18 files against 20 applied is not "2 pending", and must not read as it.

    Collapsing the two directions into one count sends a reader looking for the
    wrong problem: behind (a column that does not exist) and ahead (someone
    else's branch got here first) have opposite fixes.
    """
    response = client.get("/admin/database")
    if response.status_code == 503:
        pytest.skip("no database to read")
    migrations = response.json()["migrations"]
    if not migrations["readable"]:
        # ⚠ RULE 4. A ledger that could not be read says so and claims nothing.
        assert migrations["why"]
        return
    for field in ("pending", "applied_not_on_disk", "drifted"):
        assert isinstance(migrations[field], list)
    assert migrations["in_step"] == (
        not migrations["pending"] and not migrations["drifted"]
    )


def test_the_unreviewed_column_count_travels_with_its_denominator(client):
    """⚠ RULE 7. 256 unreviewed is a different fact at 370 columns than at 260."""
    response = client.get("/admin/database")
    if response.status_code == 503:
        pytest.skip("no database to read")
    body = response.json()
    if body["column_states"] is None:
        assert body["column_states_unreadable"]
        return
    assert body["columns_total"] >= body["columns_unreviewed"]


def test_the_secret_marker_list_is_a_substring_match_by_design(client):
    """An exact list is one somebody forgets to extend; the cost is a key.

    Names nobody has written down yet must still be caught, so this asserts the
    behaviour rather than the list.
    """
    from judge.app import _is_secretish

    for invented in (
        "SOME_NEW_PROVIDER_API_KEY",
        "vendor_access_token",
        "Billing_Secret",
        "REPLICA_DATABASE_URL",
        "ADMIN_PASSWORD",
        "SIGNING_KEY_HASH",
    ):
        assert _is_secretish(invented), f"{invented} would have been published"


def test_settings_does_not_name_the_account_when_the_caller_is_anonymous(client):
    """⚠ RULE 6. A shared token carries no identity, and none is invented.

    Falling back to the configured address would put a name on the page that is
    not necessarily the person reading it.
    """
    body = client.get("/admin/settings").json()["account"]
    assert body["signed_in_as"] is None
    assert "no identity" in body["via"] or "open" in body["via"]


def test_every_surface_answers_or_says_why(client):
    """None of the three may return a 500: an unreadable board is a 503.

    503 rather than 500 because no database is an operational state, not a fault
    in the request - the same distinction `_conn` is built around.
    """
    assert os.getenv("DATABASE_URL")
    for path in SURFACES:
        assert client.get(path).status_code in (200, 503), path
