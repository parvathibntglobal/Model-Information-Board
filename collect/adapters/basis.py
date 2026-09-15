"""`use_basis` — the one live precondition three rulings share.

WHY THIS IS ONE FUNCTION AND NOT THREE
---------------------------------------
`reddit-via-rapidapi`, `arxiv-api-terms` and `x-via-rapidapi-scraper` all rest
on `basis: internal-development-only`, and `TermsRuling.basis` requires that a
named basis also be a `live_precondition` "so the fuse is checked rather than
remembered". Three adapters therefore have to observe the same fact on every
run, and `collect/adapters/x.py`'s own docstring already asked for this:

    `use_basis` ... belongs on the ruling, and this observes the ROUTE. If the
    ruling rests on internal-development-only, that precondition is
    `observe_reddit_use`'s and should be SHARED rather than reimplemented
    differently here.

Reimplemented differently is the failure mode worth naming. Three copies of one
check drift, and a basis observed as `internal-development-only` by two
adapters and `dev` by the third would refuse one platform and pass two on the
same deployment — a discrepancy that reads as a platform problem.

⚠  IT IS A PROXY, AND SAYING SO IS THE WHOLE VALUE OF THIS DOCSTRING.
   `ENVIRONMENT` is the only signal the process has. It catches the case that
   matters most — a production deployment silently inheriting a
   development-only ruling — and it does NOT catch:

     - a staging instance that has acquired external users
     - a local build shown to somebody outside the team
     - anything at all about PUBLICATION, which is what the rulings actually
       turn on (`contract/sources.yaml`, "WHAT COUNTS AS PUBLICATION")

   Publication is a property of who is looking at a page. No environment
   variable knows that, and the fetch path this runs on is not the path a page
   is served from. `contract/sources.yaml`'s ENFORCEMENT block states the gap
   in full rather than leaving this proxy to imply a guard.

So a basis is a SHORTER FUSE than `review_valid_days`, not a substitute for
reading the terms again — and not a substitute for a person honouring the
condition.
"""

from __future__ import annotations

from datetime import date, timedelta

#: The basis all three rulings name, spelled as `contract/sources.yaml` spells
#: it. A precondition compares by value, so a paraphrase here refuses the
#: source with a message about a basis mismatch.
INTERNAL_DEVELOPMENT_ONLY = "internal-development-only"

#: ⚠ REPLACED BY THE UNDERTAKING, 2026-09-15 (PROPOSED).
#:
#: This used to be the whole check: anything but `production` observed as
#: internal. Two problems, and the docstring above had already named the first.
#:
#:   1. `ENVIRONMENT` is a DEPLOYMENT MODE and the rulings turn on WHO CAN
#:      REACH THE SITE. One fact answering for another.
#:   2. UNSET OBSERVED AS INTERNAL, so a misconfigured container harvested
#:      under a basis nobody had asserted. Absent read as permissive, which is
#:      rule 6 inverted.
#:
#: Kept as a name because `serve.py` and `/health` still report the mode, and
#: because the hosted container running `production` is how the refusal was
#: diagnosed on 2026-09-14. It no longer decides anything here.
PRODUCTION = "production"


def _undertaking_basis() -> str:
    """The asserted basis, or a NAMED refusal value saying which check failed.

    Four ways to have no basis, and they are told apart because the gate's error
    is the only thing anybody reads when a harvest refuses:

        no undertaking block          nobody has written one
        `asserted_by` empty           written but not signed - the state this
                                      ships in, so a proposal cannot be mistaken
                                      for an assertion
        expired                       `asserted_on` + `review_valid_days` passed
        self-contradicting            `asserts: internal-development-only` with
                                      `external_users: true`, say - the `asserts`
                                      line must not win over the conditions
    """
    from collect.registry.sources import load_sources

    block = getattr(load_sources(), "use_basis_undertaking", None)
    if not block:
        return "no-undertaking (contract/sources.yaml:use_basis_undertaking)"
    who, when = block.get("asserted_by"), block.get("asserted_on")
    if not who or not when:
        return "undertaking-unsigned (asserted_by/asserted_on are empty)"

    asserted_on = when if isinstance(when, date) else date.fromisoformat(str(when))
    expires = asserted_on + timedelta(days=int(block.get("review_valid_days", 30)))
    if expires < date.today():
        return f"undertaking-expired (asserted {asserted_on}, expired {expires})"

    # SELF-CONSISTENCY. An undertaking whose conditions contradict what it
    # asserts is not a weaker undertaking, it is a broken one - and letting the
    # `asserts` line win would make the conditions decorative.
    conditions = block.get("conditions") or {}
    broken = [
        f"{k}: {conditions.get(k)!r}"
        for k, required in (("auth_walled", True), ("external_users", False),
                            ("publicly_linked", False), ("monetized", False))
        if conditions.get(k) is not required
    ]
    if broken:
        return f"undertaking-void ({'; '.join(broken)})"
    return str(block.get("asserts") or "undertaking-asserts-nothing")


def observe_use_basis() -> dict[str, object]:
    """`{"use_basis": …}` for this run, re-read every time.

    Returns the UNDERTAKING's asserted basis, or a named refusal value saying
    which check failed - so the gate's error says *why* rather than only that a
    precondition did not match.

    ABSENT IS NOT PERMISSIVE. No undertaking means no basis means every ruling
    that rests on one refuses. That makes the default REFUSE, which is the
    opposite of what `ENVIRONMENT` unset used to do.
    """
    return {"use_basis": _undertaking_basis()}
