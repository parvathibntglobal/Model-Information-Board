"""Three ways the admin page told a reader something it could not support.

All three shipped, all three were reported by @parvathibntglobal looking at the
page rather than by a test, and each is a different failure:

  1. THE SAME PANEL UNDER TWO HEADINGS. `DiscussedModels` rendered under Models
     and again under Board sections. The argument was that the question belongs
     to neither section; what it left out is that a reader who meets
     `64 of 78 models with evidence` twice, one screen apart, does not read it
     as two views of one fact — they read it as one of the two being stale.

  2. AN IDENTIFIER NOBODY CAN USE. The tracked list printed
     `mv_b3508133423993d7` beside every name. The compare page already carries
     the rule — a reader cannot look up an internal key, check it against the
     provider, or use it anywhere — and has a test enforcing it. The admin list
     was the surface still doing it.

  3. A CAPTION RESTATING A NUMBER SHOWN BESIDE IT. `FETCH_MAX_THREADS` read
     "documents one fetch sends the model — the 'x of 50' on the button". 50 is
     the DEFAULT. Production runs 25, so the value column said `25` and the
     sentence next to it said 50.

⚠ THE THIRD IS THE ONE WITH A CLASS BEHIND IT, and it is the reason this file
  checks the whole list rather than the one entry: any description that repeats
  its own default has two ways to be right, and one of them goes stale the
  first time somebody overrides it. The number is already on the page, in the
  column whose job is to be current.
"""

from __future__ import annotations

import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "judge" / "app.py"
ADMIN = ROOT / "web" / "src" / "routes" / "Admin.jsx"
PANEL = ROOT / "web" / "src" / "components" / "DiscussedModels.jsx"


def _jsx(path: pathlib.Path) -> str:
    """Comments stripped. Each file explains the state it no longer renders."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*[\s\S]*?\*/", " ", text)
    return re.sub(r"//[^\n]*", " ", text)


def _cap_specs() -> list[tuple]:
    """`cap_specs` read out of the source, so the tuples are the real ones."""
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign)
                and any(getattr(t, "id", "") == "cap_specs" for t in node.targets)):
            return ast.literal_eval(node.value)
    raise AssertionError("cap_specs is gone from judge/app.py")


class TestEachPanelIsMountedOnce:
    def test_the_discussed_models_panel_appears_once(self):
        rendered = _jsx(ADMIN).count("<DiscussedModels")
        assert rendered == 1, (
            f"DiscussedModels is rendered {rendered} times. The same list "
            f"under two headings reads as one of them being stale."
        )

    def test_the_prop_that_only_existed_for_the_second_mount_is_gone(self):
        """`heading` existed to retitle the duplicate. A prop no caller passes
        is the orphan this repository keeps finding, one layer down."""
        assert "heading" not in _jsx(PANEL).replace("headings", ""), (
            "the `heading` prop survived the mount it existed for"
        )


class TestTheListNamesModelsAReaderCanLookUp:
    def test_the_summary_line_shows_the_canonical_id(self):
        admin = _jsx(ADMIN)
        assert "{m.canonical_id}" in admin, (
            "the tracked list no longer shows the provider's id"
        )

    def test_the_internal_key_is_not_on_the_scan_line(self):
        """⚠ CHECKED WHERE IT MATTERS. `model_version_id` is still needed — as
        the React key, and as the prop `FetchPanel` fetches by — so its mere
        presence proves nothing. What must not happen is it being rendered in
        the `<summary>`, which is the line a reader scans."""
        admin = _jsx(ADMIN)
        start = admin.index("<summary>")
        summary = admin[start:admin.index("</summary>", start)]
        assert "m.model_version_id}</span>" not in summary, (
            "the internal database key is printed on the summary line again"
        )
        assert "canonical_id" in summary

    def test_it_is_still_reachable_for_somebody_debugging(self):
        """Removed from the scan line, not from the page. It is what
        `board_entry` and `claim` join on, and an operator who has opened the
        row is doing exactly the work that needs it."""
        assert "disc-body" in _jsx(ADMIN)
        body_at = _jsx(ADMIN).index("disc-body")
        body = _jsx(ADMIN)[body_at:body_at + 400]
        assert "{m.model_version_id}" in body


class TestNoCapDescriptionRestatesItsOwnNumber:
    """⚠ THE CLASS, NOT THE ONE ENTRY. `FETCH_MAX_THREADS` said "the 'x of 50'
    on the button" while production ran 25 — the value column and the sentence
    beside it disagreed, and the sentence is the half that cannot update."""

    def test_no_description_contains_its_default(self):
        offenders = []
        for spec in _cap_specs():
            name, default, why = spec[0], spec[1], spec[2]
            #: Only NUMERIC defaults. `EXTRACTOR_MODEL`'s default is a model id
            #: and naming it in the prose is not the same hazard — it does not
            #: read as a live figure.
            if default.isdigit() and re.search(rf"\b{re.escape(default)}\b", why):
                offenders.append(f"{name}: {why!r}")
        assert not offenders, (
            "a cap description repeats its own default, which the page already "
            "shows in the value column and which goes stale the first time "
            "somebody overrides it:\n  " + "\n  ".join(offenders)
        )

    def test_the_fetch_cap_still_explains_what_it_is(self):
        """⚠ THE CONTROL. Deleting the sentence would pass the test above.
        What the reader needs is which number on which surface this is."""
        why = next(s[2] for s in _cap_specs() if s[0] == "FETCH_MAX_THREADS")
        assert "Fetch button" in why and "documents" in why
