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

    # SELF-CONSISTENCY, AS A CLOSED CONTRACT RATHER THAN A WHITELIST.
    #
    # ⚠ THIS WAS A HARDCODED FOUR-TUPLE AND IT SHIPPED GREEN (#314). The loop
    #   asked "do the four conditions I know about hold" when the honest
    #   question is "is there anything here that does not hold" - so a key it
    #   did not recognise was never read. Measured 2026-09-15: an undertaking
    #   asserting `indexed_by_search_engines: true` and
    #   `shared_with_client: true` observed as `internal-development-only`.
    #
    #   Same shape as `finish_reason` vs `native_finish_reason` three days
    #   earlier: a check that reads one named thing, is blind to everything
    #   else, and passes because the named thing behaved.
    #
    # THREE WAYS TO FAIL, and the first is the one that was missing:
    #
    #   an UNKNOWN key      voids. Somebody adding a condition is telling us
    #                       something; being overruled by silence is the worst
    #                       available response.
    #   a MISSING key       voids. Not observed is not a pass (rule 6) - the
    #                       whole argument this undertaking rests on.
    #   a WRONG value       voids, as before.
    #
    # `required_conditions` is read from the contract rather than carried here,
    # so there is one source of truth for the set. Its own absence voids too:
    # a checker that cannot find its contract has not passed anything.
    required = block.get("required_conditions")
    if not required:
        return (
            "undertaking-void (no required_conditions in "
            "contract/sources.yaml:use_basis_undertaking, so nothing states "
            "what the conditions must be)"
        )
    conditions = block.get("conditions") or {}

    faults: list[str] = []
    for key in sorted(set(conditions) - set(required)):
        faults.append(f"{key}: not a known condition")
    for key in sorted(set(required) - set(conditions)):
        faults.append(f"{key}: required and not asserted")
    for key in sorted(set(required) & set(conditions)):
        if conditions[key] is not required[key]:
            faults.append(
                f"{key}: {conditions[key]!r}, must be {required[key]!r}"
            )
    if faults:
        return f"undertaking-void ({'; '.join(faults)})"
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
