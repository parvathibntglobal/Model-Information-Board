"""`EXTRACTOR_MODEL` resolves in ONE place, so the call and the record agree.

`judge/store/claims.py` describes `claim.extractor_model` as the column that
says what produced a row. The defect was never that it had a default - it is
that **eight files each had their own**, so the model the client CALLED and the
model the pipeline RECORDED were two independent `os.getenv` reads that agreed
by coincidence. One function fixes that whatever the default is.

THE DEFAULT IS THE AGREED EXTRACTOR AND IS TESTED AS SUCH. `deepseek/deepseek-v4-flash`
resolves to the pinned 0423 snapshot, and staying there is a dated decision
rather than an accident. `test_the_default_is_the_agreed_extractor` exists so
changing it is a deliberate, visible diff - it changes what every subsequent
row records about its own provenance.

WHAT THESE TESTS DO NOT COVER, STATED BECAUSE IT IS THE LIVE GAP. Nothing here
refuses a value explicitly set to something other than the agreed extractor.
That is what produced the gemini mixture on the board - a machine with the
variable SET to gemini, not one with it unset - and a refuse-on-unset check
cannot see it. The check that would is a comparison against a recorded choice in
`contract/`; proposed in
`docs/proposals/the-agreed-extractor-belongs-in-contract.md`, not taken.

WHY THE STRUCTURAL TEST IS STILL THE ONE THAT MATTERS

The behavioural tests cover the resolver. They cannot see the ninth file, and
the ninth file is how the divergence came back the first time. So the last test
reads the tree for the literal and holds an explicit allowlist.
"""

from __future__ import annotations

import pathlib

import pytest

from judge.extract.client import extractor_model

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: The literal that must not appear as an `os.getenv` fallback.
LITERAL = 'EXTRACTOR_MODEL", "deepseek/deepseek-v4-flash"'

#: Files allowed to keep it, each for a stated reason. Listed rather than
#: pattern-matched, so moving one INTO this set is a visible diff.
ALLOWED = {
    # Renders the admin Settings page: name, DEFAULT, and what the variable is
    # for. The string is DISPLAYED as the documented default, never used to make
    # a call, so removing it would blank a column rather than close a hazard.
    "judge/app.py",
    # Read-only measurement scripts. They make calls and write no claim, so an
    # unset variable here costs a wrong number in one report and not a wrong
    # provenance row on the board. Named rather than converted, because the
    # distinction is the point: the refusal guards WRITE paths.
    "scripts/count_db_roundtrips.py",
    "scripts/observe_dropped_surfaces.py",
    "scripts/time_extraction_phases.py",
}


@pytest.fixture(autouse=True)
def _no_ambient_value(monkeypatch):
    monkeypatch.delenv("EXTRACTOR_MODEL", raising=False)


# ── the resolver ────────────────────────────────────────────────────────────


def test_an_unset_variable_gets_the_agreed_extractor():
    """Not a guess: the default IS the choice, and the choice is recorded."""
    from judge.extract.client import DEFAULT_MODEL

    assert extractor_model() == DEFAULT_MODEL


def test_the_default_is_the_agreed_extractor():
    """PINNED ON PURPOSE. `deepseek/deepseek-v4-flash` resolves to the 0423
    snapshot, and this line is what `claim.extractor_model` records on every
    row written without an override. Changing it is a provenance change, so it
    should be a deliberate diff with this test in it rather than a constant
    somebody edits in passing."""
    from judge.extract.client import DEFAULT_MODEL

    assert DEFAULT_MODEL == "deepseek/deepseek-v4-flash"


def test_whitespace_is_not_a_model_named_space(monkeypatch):
    """`EXTRACTOR_MODEL="   "` is unset with extra steps, not a model id."""
    from judge.extract.client import DEFAULT_MODEL

    monkeypatch.setenv("EXTRACTOR_MODEL", "   ")
    assert extractor_model() == DEFAULT_MODEL


def test_a_set_value_is_returned_stripped(monkeypatch):
    monkeypatch.setenv("EXTRACTOR_MODEL", "  deepseek/deepseek-v4-flash \n")
    assert extractor_model() == "deepseek/deepseek-v4-flash"


def test_the_client_and_the_record_resolve_to_the_same_value(monkeypatch):
    """THE POINT OF THE SINGLE FUNCTION. Whatever the environment says, the
    model the client calls is the model `judge/cli.py` hands the pipeline to
    record. Two `os.getenv` reads with two fallbacks could not guarantee this,
    and they are what produced the divergence risk in the first place."""
    from judge.extract.client import OpenRouterClient

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("EXTRACTOR_MODEL", "deepseek/deepseek-v4-flash-0731")
    assert OpenRouterClient.from_env().model == extractor_model()


def test_the_client_uses_the_agreed_extractor_when_nothing_is_set(monkeypatch):
    from judge.extract.client import DEFAULT_MODEL, OpenRouterClient

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    assert OpenRouterClient.from_env().model == DEFAULT_MODEL


# ── the registry check ──────────────────────────────────────────────────────


class _Conn:
    """Answers the two queries `_assert_model_is_registered` makes."""

    def __init__(self, total: int, known: set[str]):
        self._total = total
        self._known = known

    def execute(self, sql, params=None):
        class _R:
            def __init__(self, row):
                self._row = row

            def fetchone(self):
                return self._row

        if "count(*)" in sql:
            return _R((self._total,))
        wanted = params[0]
        return _R((wanted,) if wanted in self._known else None)


def test_an_unknown_id_is_refused_before_the_first_call():
    from judge.cli import _assert_model_is_registered

    conn = _Conn(348, {"deepseek/deepseek-v4-flash"})
    with pytest.raises(SystemExit) as raised:
        _assert_model_is_registered(conn, "deepseek/deepseek-v4-flsah")
    assert "348" in str(raised.value), "the refusal carries the population it searched"


def test_a_route_is_refused_even_though_the_registry_has_it():
    """Routes are not models — ruled 2026-08-18. A route makes
    `claim.extractor_model` unanswerable by construction, which is the one thing
    that column exists to answer."""
    from judge.cli import _assert_model_is_registered

    route = "~deepseek/deepseek-v4-flash-latest"
    conn = _Conn(348, {route})
    with pytest.raises(SystemExit) as raised:
        _assert_model_is_registered(conn, route)
    assert "ROUTE" in str(raised.value)


def test_a_known_id_passes(capsys):
    from judge.cli import _assert_model_is_registered

    _assert_model_is_registered(_Conn(348, {"deepseek/deepseek-v4-flash"}),
                                "deepseek/deepseek-v4-flash")
    assert "is in the registry" in capsys.readouterr().out


def test_an_empty_registry_is_skipped_and_named_rather_than_passed(capsys):
    """A fresh database has no `model_version` rows. Refusing there would block
    a legitimate first run on the absence of a poller; passing silently would
    report a check that never ran. So it is skipped, and it says so."""
    from judge.cli import _assert_model_is_registered

    _assert_model_is_registered(_Conn(0, set()), "anything/at-all")
    out = capsys.readouterr().out
    assert "SKIPPED" in out
    assert "0 " in out


# ── the one that catches the ninth file ─────────────────────────────────────


def test_no_unlisted_file_carries_its_own_fallback():
    carriers = {
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in ROOT.rglob("*.py")
        if ".venv" not in path.parts
        and "tests" not in path.parts
        and LITERAL in path.read_text(encoding="utf-8", errors="ignore")
    }
    unlisted = sorted(carriers - ALLOWED)
    assert not unlisted, (
        f"these files default EXTRACTOR_MODEL to a literal: {unlisted}. The value "
        "lands in `claim.extractor_model`, a NOT NULL provenance column, so a "
        "fallback writes a guess into the field that says what produced the row. "
        "Call `judge.extract.client.extractor_model()`, or add the file to "
        "ALLOWED with the reason it does not write claims."
    )
    stale = sorted(ALLOWED - carriers)
    assert not stale, f"ALLOWED names files that no longer carry it: {stale}"
