"""The capability vocabulary loader, and the four things it refuses.

No database: what is under test is the parser's rules. The upsert is one
statement and `tests/test_insert_types.py` covers the column types against a
real Postgres.

WHY A LOADER GETS ITS OWN TEST FILE FOR TWELVE ROWS. `claim.capability_key` is
NOT NULL and REFERENCES `capability(key)`, and the table held 0 rows for the
whole build — so every refusal below is a way the vocabulary could load and
leave the foreign key satisfiable but WRONG, which is worse than unsatisfiable.
A missing key fails loudly at insert; a key loaded with the wrong
`failure_mode` publishes a cell on the wrong evidence standard and nothing
errors.
"""

from __future__ import annotations

import pytest

from collect.registry.capabilities import (
    CapabilityContractError,
    load_capability_file,
    parse_capabilities,
)


#: How many keys `contract/capabilities.yaml` ratifies.
#:
#: 12 until 2026-09-15, when `cost.efficiency` and `cost.per_task` were
#: ratified. ASSERTED rather than read from the contract on purpose: reading it
#: would make this test agree with any vocabulary, including one a bad merge
#: shrank. Moving it is the deliberate half of a vocabulary change.
RATIFIED = 14


def test_the_live_contract_parses_and_carries_every_ratified_key():
    """Against `contract/capabilities.yaml`, not a fixture.

    A loader tested only against a hand-built document is a loader tested
    against the shape its author had in mind.
    """
    version, rows = load_capability_file()

    assert version == "1.0"
    assert len(rows) == RATIFIED, (
        "FR-7 and the query contract both count on this number, so it is "
        "asserted rather than derived - a key that vanishes from the contract "
        "must fail here rather than quietly shrink the vocabulary."
    )
    assert {r.failure_mode for r in rows} == {"loud", "silent"}
    assert sum(1 for r in rows if r.failure_mode == "silent") == 4, (
        "the four silent-failure capabilities are what make positive queries "
        "mandatory rather than optional"
    )
    assert all(r.version == version for r in rows), (
        "every row carries the contract version, so a taxonomy change is "
        "identifiable per row rather than per file"
    )


def test_a_missing_failure_mode_refuses_rather_than_defaulting():
    """Neither default is safe, which is why this raises.

    `loud` would let a silent-failure capability publish on absence of
    criticism. `silent` would demand positive consensus for one that errors in
    seconds. Both are wrong in a way that surfaces as a cell nobody can
    explain, so the loader will not choose.
    """
    with pytest.raises(CapabilityContractError, match="failure_mode"):
        parse_capabilities(
            {"version": "1.0", "capabilities": [{"key": "a.b", "description": "x"}]}
        )


def test_an_unknown_failure_mode_refuses():
    with pytest.raises(CapabilityContractError, match="failure_mode"):
        parse_capabilities(
            {
                "version": "1.0",
                "capabilities": [{"key": "a.b", "failure_mode": "quiet"}],
            }
        )


def test_a_duplicate_key_refuses_because_it_would_split_a_cell():
    """Consensus counting groups on this key. Two entries make one cell two."""
    with pytest.raises(CapabilityContractError, match="duplicate"):
        parse_capabilities(
            {
                "version": "1.0",
                "capabilities": [
                    {"key": "a.b", "failure_mode": "loud"},
                    {"key": "a.b", "failure_mode": "silent"},
                ],
            }
        )


def test_an_unversioned_contract_refuses():
    """`capability.version` is NOT NULL and a taxonomy change must be identifiable."""
    with pytest.raises(CapabilityContractError, match="version"):
        parse_capabilities(
            {"capabilities": [{"key": "a.b", "failure_mode": "loud"}]}
        )


def test_an_empty_vocabulary_refuses_rather_than_loading_nothing():
    """The one refusal that is about this loader's whole reason for existing.

    Loading zero rows leaves `claim`'s foreign key unsatisfiable and reports
    success — a green run that ends in exactly the state the loader was written
    to end. Zero loaded and zero attempted look identical in a report, which is
    habit 4 applied to a writer rather than to a check.
    """
    with pytest.raises(CapabilityContractError, match="no capabilities"):
        parse_capabilities({"version": "1.0", "capabilities": []})


def test_absence_from_the_contract_does_not_deactivate():
    """Rule 6 on our own vocabulary, asserted on the report rather than the rows.

    A key that disappears from the YAML is as likely to be an accident as a
    decision, and `claim` rows already reference it. Flipping `active` on
    absence would retire a capability and every cell under it from a file edit.
    So the loader NAMES the divergence and changes nothing.
    """
    from collect.registry.capabilities import load_capabilities

    class FakeConn:
        def __init__(self) -> None:
            self.writes = 0

        def execute(self, sql, params=None):
            if sql.strip().startswith("SELECT"):
                return _Result([("retired.capability", "loud", "", "0.9")])
            self.writes += 1
            return _Result([])

    class _Result:
        def __init__(self, rows): self._rows = rows
        def fetchall(self): return self._rows

    conn = FakeConn()
    report = load_capabilities(conn)

    assert report.absent_from_contract == ["retired.capability"]
    assert "left active and untouched" in report.summary()
    assert conn.writes == RATIFIED, "every declared key is still written"
