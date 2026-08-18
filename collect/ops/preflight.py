"""The checks that run before anything writes. Issue #27's answer.

`assert_no_fixtures` and `assert_contract_backed` were written on day one and
never called. `CLAUDE.md` said *"Production asserts on startup that none are
present"*, which was corrected to *"called from the loaders and from tests"*,
which was also wrong: the three apparent call sites in `collect/` were a
docstring and two comments. The reason the correction kept being wrong is that
there was no startup — no server process, and `collect/cli.py` runs per command.

**The nightly chain is the first process in this lane with a startup at all**,
which is what makes it the right home and what makes #27 closeable rather than
re-worded a third time.

WRITE COMMANDS, NOT EVERY COMMAND
---------------------------------
`registry check-sources`, `registry aliases` and `registry propose-aliases` read
and print. Gating them would mean a broken environment cannot be diagnosed with
the tools built to diagnose it — and the state these checks refuse is precisely
the state somebody needs a diagnostic in. The gate belongs where the damage is:
schema changes, seed loads, polls and sweeps.

WHAT IT DOES TODAY, ON REAL DATA
--------------------------------
Measured 2026-08-18 against the registry as it stands — 340 rows, all
`provenance = 'polled'`, 0 hand-curated cells, 0 hand-seeded thresholds:

    assert_no_fixtures        PASSES. Wiring it costs nothing now and starts
                              protecting on the day the seed file is loaded
                              somewhere it should not be.
    assert_contract_backed    PASSES. `contract/registry.yaml` exists — it landed
                              in `4bd322d` — so the policy is contract-backed and
                              NFR-10 is satisfied rather than merely intended.

The second one is a CORRECTION to what I wrote in `docs/ops-nightly-chain.md §3`,
which said the check would fail because that file did not exist. It did not exist
when `policy.py`'s docstring was written and it does now, and I read the docstring
instead of the directory. Both checks pass today, which means wiring them costs
nothing and the gate starts working the first time either stops being true.

`development` skips both, and `ENVIRONMENT` is what decides.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from collect.registry.assertions import (
    FixtureLeakError,
    TermsNotReviewedError,
    UnversionedConfigError,
    assert_contract_backed,
    assert_no_fixtures,
    assert_terms_reviewed,
)


class PreflightRefused(RuntimeError):
    """The environment is not fit to write. Carries every reason, not the first.

    One reason at a time turns a five-minute fix into five runs. The checks are
    independent, so they are all evaluated and all reported.
    """

    def __init__(self, failures: list[str]) -> None:
        self.failures = failures
        listed = "\n  - ".join(failures)
        super().__init__(f"preflight refused, {len(failures)} check(s) failed:\n  - {listed}")


@dataclass
class PreflightReport:
    """What ran and what it found. Printed, and carried into the run record."""

    environment: str
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed

    def summary(self) -> str:
        state = "ok" if self.ok else "REFUSED"
        return (
            f"preflight {state} in {self.environment!r}: "
            f"{len(self.passed)} passed, {len(self.failed)} failed, "
            f"{len(self.skipped)} skipped"
        )


def preflight(
    conn=None,
    *,
    environment: str,
    policy=None,
    sources=None,
    rulings=None,
    observations=None,
    raise_on_failure: bool = True,
) -> PreflightReport:
    """Run every startup check that has its inputs, and report the rest as skipped.

    A check whose input is absent is **skipped and named**, never quietly
    counted as a pass. `preflight(environment=...)` with no connection is a
    legitimate call — the CLI has one before it opens a database — and it must
    not read as "the fixture check passed".
    """
    report = PreflightReport(environment=environment)

    if conn is None:
        report.skipped.append("no-fixtures: no database connection was supplied")
    else:
        try:
            assert_no_fixtures(conn, environment=environment)
            report.passed.append("no-fixtures")
        except FixtureLeakError as error:
            report.failed.append(f"no-fixtures: {error}")

    if policy is None:
        report.skipped.append("contract-backed: no policy was supplied")
    else:
        try:
            assert_contract_backed(policy, environment=environment)
            report.passed.append("contract-backed")
        except UnversionedConfigError as error:
            report.failed.append(f"contract-backed: {error}")

    if sources is None:
        report.skipped.append("terms-reviewed: no sources were supplied")
    else:
        try:
            assert_terms_reviewed(sources, rulings=rulings, observations=observations)
            report.passed.append("terms-reviewed")
        except TermsNotReviewedError as error:
            report.failed.append(f"terms-reviewed: {error}")

    if report.failed and raise_on_failure:
        raise PreflightRefused(report.failed)
    return report
