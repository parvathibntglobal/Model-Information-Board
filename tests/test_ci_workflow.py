"""The CI workflow is a shell script wearing a YAML costume. Check both layers.

The first run of `.github/workflows/ci.yml` failed on this:

    run: python -c "import pytest_asyncio, ruff  # noqa: F401"

In a PLAIN YAML scalar a space-hash starts a comment, so YAML handed bash
`python -c "import pytest_asyncio, ruff` and bash said

    line 1: unexpected EOF while looking for matching `"'

Nothing catches that locally. The file is valid YAML, the Python is valid
Python, and the two are only wrong together — which is the shape of defect
this repo keeps finding, and the reason it gets a test rather than a habit.

These need no database and no network: the workflow is a file.
"""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def run_steps() -> list[tuple[str, str]]:
    steps = workflow()["jobs"]["test"]["steps"]
    return [(s.get("name", "(unnamed)"), s["run"]) for s in steps if s.get("run")]


def test_the_workflow_is_valid_yaml_and_has_the_job():
    assert workflow()["jobs"]["test"]["runs-on"] == "ubuntu-latest"
    assert run_steps(), "no run: steps at all"


@pytest.mark.parametrize("name,command", run_steps(), ids=lambda v: str(v)[:40])
def test_every_run_step_survives_yaml_and_reaches_the_shell_intact(name, command):
    """Quoting must still balance AFTER YAML has had its turn.

    `shlex.split` raises on an unterminated quote, which is exactly what bash
    reported. Cheaper than a CI round trip, and it fails on the same input.
    """
    try:
        shlex.split(command)
    except ValueError as exc:
        pytest.fail(
            f"step {name!r} does not survive YAML parsing: {exc}. "
            f"YAML handed the shell:\n  {command!r}\n"
            "A space-hash in a plain scalar starts a YAML comment — use a "
            "block scalar (run: |) and keep '#' out of the command."
        )


def test_no_run_step_carries_a_hash_that_yaml_would_eat():
    """Belt and braces, and it names the fix rather than the symptom.

    A block scalar makes `#` safe, so this only complains about plain scalars —
    which is where the trap is. Checked against the raw text because by the
    time PyYAML has parsed it the evidence is gone.
    """
    offenders = []
    for line in WORKFLOW.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("run:") or stripped == "run: |":
            continue
        if " #" in stripped:
            offenders.append(stripped)

    assert not offenders, (
        f"plain `run:` scalar containing ' #', which YAML reads as a comment "
        f"and truncates: {offenders}. Use a block scalar (run: |)."
    )


def test_the_database_the_guard_will_check_is_the_one_ci_declares():
    """`_same_target` compares host, port AND path, so these must agree exactly.

    The sentinel step records `$TEST_DATABASE_URL` and `tests/conftest.py`
    connects with it. A mismatch fails closed and loudly, which is correct and
    is still a red build — so it is worth catching in the file.
    """
    from urllib.parse import urlsplit

    job = workflow()["jobs"]["test"]
    dsn = job["env"]["TEST_DATABASE_URL"]
    parts = urlsplit(dsn)

    assert parts.hostname in ("localhost", "127.0.0.1", "::1"), "guard layer 1"
    assert parts.path.lstrip("/").endswith("_test"), "guard layer 2"

    service_port = job["services"]["postgres"]["ports"][0]
    assert service_port.startswith(f"{parts.port}:"), (
        f"the service publishes {service_port} but the DSN uses port "
        f"{parts.port}; the sentinel would record a target nothing connects to"
    )

    database = parts.path.lstrip("/")
    assert job["services"]["postgres"]["env"]["POSTGRES_DB"] == database, (
        "the service creates a different database than the DSN names"
    )

    sentinel = next(
        s["run"] for s in job["steps"] if s.get("name") == "Mark the database disposable"
    )
    assert "$TEST_DATABASE_URL" in sentinel, (
        "the sentinel must record the same DSN string the suite connects with, "
        "not a copy that could drift"
    )


def test_the_missing_database_override_is_not_set():
    """`ALLOW_MISSING_TEST_DB` in CI would turn a broken service into a green run."""
    text = WORKFLOW.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "ALLOW_MISSING_TEST_DB" in line and not line.strip().startswith("#"):
            pytest.fail(f"ALLOW_MISSING_TEST_DB is set in CI: {line.strip()!r}")
