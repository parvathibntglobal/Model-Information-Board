"""`EXTRACTOR_MODEL` has no default, because it is a provenance value.

`judge/store/claims.py` already says this of the column it lands in:

    "The model that ACTUALLY ran, from the completion, not from the
     environment. It was `os.getenv("EXTRACTOR_MODEL", "...flash")` on a
     NOT NULL provenance column, so an unset variable wrote a confident
     guess into the one field whose job is to say what produced the row."

That was found once and half-fixed: the literal was copied rather than removed,
so eight files kept a fallback and the guess survived in every caller that was
not the one being edited. Measured 2026-09-18, before this change, the board
carried 985 claims at pipeline_version e5.4 from TWO different extractors, and
three cells aggregated both.

WHY THE STRUCTURAL TEST IS THE ONE THAT MATTERS

The behavioural tests below cover the resolver. They cannot see the ninth file,
and the ninth file is how this came back the first time. So the last test reads
the tree for the literal and holds an explicit allowlist: a new write path
carrying its own fallback fails the day it is written, naming itself.
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


def test_an_unset_variable_refuses_rather_than_defaulting():
    with pytest.raises(RuntimeError) as raised:
        extractor_model()

    message = str(raised.value)
    assert "EXTRACTOR_MODEL is unset" in message
    assert "claim.extractor_model" in message, "the refusal must say WHY, not only what"


def test_whitespace_is_unset_rather_than_a_model_named_space(monkeypatch):
    monkeypatch.setenv("EXTRACTOR_MODEL", "   ")
    with pytest.raises(RuntimeError):
        extractor_model()


def test_a_set_value_is_returned_stripped(monkeypatch):
    monkeypatch.setenv("EXTRACTOR_MODEL", "  deepseek/deepseek-v4-flash \n")
    assert extractor_model() == "deepseek/deepseek-v4-flash"


def test_the_client_refuses_too_rather_than_falling_back_to_its_dataclass_default(
    monkeypatch,
):
    """`DEFAULT_MODEL` still exists as a dataclass default for direct
    construction. It must not be reachable from the environment path."""
    from judge.extract.client import OpenRouterClient

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    with pytest.raises(RuntimeError) as raised:
        OpenRouterClient.from_env()
    assert "EXTRACTOR_MODEL" in str(raised.value)


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
