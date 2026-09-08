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

from collect.config import settings

#: The basis all three rulings name, spelled as `contract/sources.yaml` spells
#: it. A precondition compares by value, so a paraphrase here refuses the
#: source with a message about a basis mismatch.
INTERNAL_DEVELOPMENT_ONLY = "internal-development-only"

#: The one environment that is not internal development. Everything else —
#: `development`, `staging`, an unset variable — observes as internal, which is
#: the permissive direction and is the reason the docstring above lists what
#: this does not catch.
PRODUCTION = "production"


def observe_use_basis() -> dict[str, object]:
    """`{"use_basis": …}` for this run, re-read every time.

    Returns the ruling's basis where the deployment is anything but production,
    and a NAMED refusal value otherwise — naming the environment in the value
    so the gate's error says which deployment it refused rather than only that
    a precondition failed.
    """
    environment = settings().environment
    return {
        "use_basis": (
            INTERNAL_DEVELOPMENT_ONLY
            if environment != PRODUCTION
            else f"not-internal (ENVIRONMENT={environment})"
        )
    }
