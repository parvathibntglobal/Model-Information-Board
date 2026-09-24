"""Every admin endpoint has a way in, and every panel is mounted.

TWO COMPLETE SURFACES WERE IN THE TREE AND COULD NOT BE REACHED, found by
@parvathibntglobal asking what was left to add:

    /admin/capability-candidates   endpoint, store, and FOUR client functions
                                   — list, rule, edit, delete. No component
                                   imported any of them. 212 keys from 223
                                   proposals had accumulated, all unruled.

    /admin/pipeline                a finished `PipelinePanel.jsx` that nothing
                                   imported, over live counts: 348 models,
                                   18,241 documents, 6,244 threads.

⚠ NEITHER FAILED. No error, no empty page, no broken link — the code was
  simply never called. That is rule 9's shape at the UI: a produced value with
  no reader, where the absence of the reader is invisible because nothing
  references it to break.

⚠ AND THE TWO WERE RESOLVED IN OPPOSITE DIRECTIONS, which is the part worth
  reading. A test that says "mount every orphan" would have got one of them
  wrong.

    PipelinePanel            MOUNTED. The counts had no other home.

    capability-candidates    REMOVED, ruled 2026-09-24 by @parvathibntglobal:
                             `capability_key` is the CLOSED twelve from the
                             first plan, when discovering capabilities was its
                             own surface. The board replaced that — discovery
                             happens in `board_entries` now, whose vocabulary
                             is open and needs no ruling — so capabilities get
                             no review surface the other two sections lack.

  The measurement behind that ruling: of the 53 keys e5.5 proposed, **24
  already existed as a board slug** — `metric.osworld` beside `osworld`,
  `capability.computer_use` beside `computer-use`, `writing.verbosity` beside
  `verbosity`. One observation written into two vocabularies, and only one of
  them is rendered anywhere.

  So the backlog was never a queue somebody forgot to work. It was the
  overflow pipe of a vocabulary the board had already superseded.

This test is the reader that makes a future orphan visible — and, for the one
that was deliberately removed, the record that keeps it removed.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADMIN = ROOT / "web" / "src" / "routes" / "Admin.jsx"
API = ROOT / "web" / "src" / "api" / "index.js"
APP = ROOT / "judge" / "app.py"
COMPONENTS = ROOT / "web" / "src" / "components"

#: Components that are not admin panels. Named rather than pattern-matched:
#: a rule like "anything ending in Panel" would have missed `ModelProposal`
#: and silently excused the next orphan with a different suffix.
NOT_ADMIN_PANELS = {
    "AuraField", "Faq", "FluidCanvas", "Footer", "LiquidBar",
    "ModelEvidence", "Nav", "OrbitHub", "Icons", "ui",
}


def reachable_components() -> set[str]:
    """Every component the admin page can actually render, transitively.

    `Admin.jsx` renders panels; a panel may render another. Both are reachable
    and only the first is named in `Admin.jsx`, so this walks the closure
    rather than reading one file.
    """
    seen: set[str] = set()
    frontier = [ADMIN]
    while frontier:
        src = frontier.pop().read_text(encoding="utf-8")
        for path in COMPONENTS.glob("*.jsx"):
            if path.stem in seen or path.stem in NOT_ADMIN_PANELS:
                continue
            if re.search(rf"<{path.stem}[\s/>]", src):
                seen.add(path.stem)
                frontier.append(path)
    return seen


class TestEveryAdminPanelIsMounted:
    def test_no_panel_component_is_an_orphan(self):
        """⚠ `PipelinePanel.jsx` was 100 lines of finished component that
        nothing imported, over an endpoint returning real counts. It did not
        fail — it was never called.

        ⚠ AND REACHABILITY IS TRANSITIVE, WHICH THE FIRST VERSION MISSED. It
          asked only whether `Admin.jsx` names the component, so the moment
          `PipelinePanel` moved INSIDE `StagesPanel` — mounted, rendered,
          visible on the page — it reported an orphan. A panel rendered by a
          reachable panel is reachable, and a test that cannot see one level
          down would push every future panel into the top-level list to stay
          green."""
        orphans = [
            p.stem for p in sorted(COMPONENTS.glob("*.jsx"))
            if p.stem not in NOT_ADMIN_PANELS and p.stem not in reachable_components()
        ]
        assert not orphans, (
            f"built and unreachable from the admin page: {orphans}. Mount it, "
            f"or add it to NOT_ADMIN_PANELS with the reason it is not a panel."
        )

    def test_the_counts_panel_is_mounted(self):
        assert "PipelinePanel" in reachable_components()


class TestEveryAdminEndpointHasAWayIn:
    def test_every_client_function_is_called_by_a_component(self):
        """⚠ FOUR FUNCTIONS FOR THE CANDIDATES QUEUE SAT UNCALLED. The client
        is not the reader — a function in `api/index.js` that no component
        imports is the same orphan one layer down, and it looks wired from
        either end.

        ⚠ THIS PASSES TWO WAYS AND ONLY ONE OF THEM IS GOOD. Deleting a
          function nobody calls satisfies it as surely as mounting a panel
          that calls it, which is exactly what happened to the candidates
          four. `TestTheCandidatesSurfaceStaysRemoved` below is what stops
          that reading from being silent."""
        api = API.read_text(encoding="utf-8")
        exported = set(re.findall(r"export const (\w+) = \(", api))
        admin_fns = {
            f for f in exported
            if re.search(rf"export const {f} = [^\n]*'/admin/", api)
        }
        callers = list(COMPONENTS.glob("*.jsx"))
        callers += list((ROOT / "web" / "src" / "routes").glob("*.jsx"))
        used = "\n".join(p.read_text(encoding="utf-8") for p in callers)
        orphans = sorted(f for f in admin_fns if f not in used)
        assert not orphans, (
            f"admin client functions no component calls: {orphans}"
        )


class TestTheCandidatesSurfaceStaysRemoved:
    """⚠ THE ENDPOINT IS STILL LIVE AND THE EXTRACTOR STILL WRITES TO IT, so
    every ingredient for rebuilding this panel is in the tree and looks like a
    gap. It is not a gap. Anyone re-adding it should be doing so because the
    closed vocabulary came back, not because `/admin/capability-candidates`
    answered a request and nothing on the page showed it."""

    def test_no_component_calls_the_candidates_route(self):
        sources = list(COMPONENTS.glob("*.jsx")) + list(
            (ROOT / "web" / "src" / "routes").glob("*.jsx")
        )
        # ⚠ THE CALL, NOT THE WORD. Both `Admin.jsx` and `api/index.js` carry
        #   a comment naming this route and saying why nothing calls it — the
        #   sentences that record the decision — and a plain substring search
        #   would report those as the violation they exist to prevent.
        #   Eleventh instance of mention-versus-use in this repository.
        offenders = []
        for path in sources:
            text = path.read_text(encoding="utf-8")
            text = re.sub(r"/\*[\s\S]*?\*/", "", text)
            text = "\n".join(
                ln for ln in text.splitlines() if not ln.strip().startswith("//")
            )
            if "capability-candidates" in text or "capabilityCandidates" in text:
                offenders.append(path.name)
        assert not offenders, (
            f"the candidates surface was rebuilt in: {offenders}. It was "
            f"removed on purpose — see the note in Admin.jsx and #434."
        )

    def test_the_decision_is_recorded_where_the_gap_looks_like_an_oversight(self):
        """A removal with no note reads as a deletion somebody forgot to
        finish, and the next reader restores it."""
        admin = ADMIN.read_text(encoding="utf-8")
        assert "THERE IS NO 'Capability candidates' SECTION" in admin
        assert "board_entries" in admin

    def test_the_board_review_is_still_the_review_surface(self):
        """The whole ruling was that ONE surface reviews discovered
        vocabulary. Removing the candidates panel while losing the board one
        would have removed the review instead of consolidating it."""
        assert "BoardReview" in reachable_components()
