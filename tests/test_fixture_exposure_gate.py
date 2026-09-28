"""The gate that replaces the writeguard's ENVIRONMENT proxy under
`--development-write`.

WHAT IS BEING PINNED, AND WHY IT IS NOT THE PROXY

`judge/writeguard.py` refuses `ENVIRONMENT=development` + a remote database.
That is a statement about the MACHINE. What `assert_no_fixtures` actually
protects is that a build fixture is never *served as evidence*, which for an
extraction run means: no claim is attached to a seeded `model_version`. That is
a property of the EXPORT, and the machine cannot see it.

So these tests pin the condition, not the proxy:

    exposure present  -> refuse, and NAME the model and document count
    exposure absent   -> permit

THE NEGATIVE TEST IS THE LOAD-BEARING ONE. "0 threads exposed" and "the matcher
is broken and matches nothing" produce an identical line on the console and an
identical decision, and only one of them is a check. `test_it_fires_when_a_seeded_model_is_named`
is what separates them, and it is the reason this file exists rather than a
comment saying the gate was run once and looked fine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scripts.run_extraction_batched import fixture_exposure


@dataclass
class _Thread:
    """Only the attribute the gate reads. A real thread carries much more."""

    raw_text_of: dict[str, str] = field(default_factory=dict)


def _finder(vocabulary):
    """Stands in for `RegistrySurfaceFinder`: surfaces present in the text."""

    def find(text: str):
        return tuple(s for s in vocabulary if s in text)

    return find


def _resolve(mapping):
    """Stands in for `RegistrySurfaceResolver`: surface -> model_version id."""
    return lambda surface: mapping.get(surface)


VOCAB = ["gemini 3.8 flash", "claude opus 4.5"]
SURFACES = {"gemini 3.8 flash": "mv_seeded", "claude opus 4.5": "mv_polled"}
SEEDED = {"mv_seeded"}


class TestTheGateRefusesExposure:
    def test_it_fires_when_a_seeded_model_is_named(self):
        """The positive control. A gate that cannot fire is not a gate."""
        threads = [_Thread({"doc1": "we tried gemini 3.8 flash and it was slow"})]
        exposed = fixture_exposure(threads, _finder(VOCAB), _resolve(SURFACES), SEEDED)
        assert exposed == {"mv_seeded": {"doc1"}}

    def test_it_names_every_document_that_reaches_the_fixture(self):
        """A count of 1 when three documents are exposed sends the reader to
        the wrong place. The set is the actionable part."""
        threads = [
            _Thread({"a": "gemini 3.8 flash", "b": "nothing here"}),
            _Thread({"c": "also gemini 3.8 flash"}),
        ]
        exposed = fixture_exposure(threads, _finder(VOCAB), _resolve(SURFACES), SEEDED)
        assert exposed == {"mv_seeded": {"a", "c"}}

    def test_a_polled_model_does_not_fire(self):
        """The negative control. The gate must distinguish 'no fixture' from
        'matches nothing', and a polled model is the case that separates them."""
        threads = [_Thread({"doc1": "claude opus 4.5 handled the refactor fine"})]
        assert fixture_exposure(threads, _finder(VOCAB), _resolve(SURFACES), SEEDED) == {}

    def test_an_unresolvable_surface_is_not_an_exposure(self):
        """`resolve` returns None for a surface the registry does not know.
        None must not be treated as membership - rule 6, an absent value is not
        a definite one."""
        threads = [_Thread({"doc1": "we tried some-unknown-model"})]
        finder = _finder(["some-unknown-model"])
        assert fixture_exposure(threads, finder, _resolve({}), SEEDED) == {}

    def test_no_seeded_rows_means_nothing_can_be_exposed(self):
        """The state this database is supposed to be in, and is not (#382)."""
        threads = [_Thread({"doc1": "we tried gemini 3.8 flash"})]
        assert fixture_exposure(threads, _finder(VOCAB), _resolve(SURFACES), set()) == {}

    def test_an_empty_export_is_not_an_exposure(self):
        assert fixture_exposure([], _finder(VOCAB), _resolve(SURFACES), SEEDED) == {}
