"""Every merged PR's head must be an ancestor of `main`. It cost half a stack once.

WHAT HAPPENED, 2026-09-08
--------------------------
Four PRs were opened as a stack, each based on the one below:

    #227  feat/five-new-platform-adapters    -> main
    #228  feat/triage-over-the-stored-corpus -> feat/five-new-platform-adapters
    #229  contract/arxiv-x-rulings...        -> feat/triage-over-the-stored-corpus

All four merged. `#227` merged into `main` carrying only its own commit; `#228`
and `#229` merged into their BASE BRANCHES, and those branches were never merged
onward. So both PRs were closed, both said merged, and on `main`:

    collect/adapters/basis.py         (#227)   present
    collect/triage/run.py             (#228)   ABSENT
    contract/bots.yaml                (#229)   ABSENT
    contract/migrations/2026...sql    (#228)   ABSENT
    the arXiv and X terms rulings     (#229)   ABSENT

Nothing was lost - it sat on a branch - but nothing said so either. It was found
by hand, by trying to push to a closed PR and reading the rejection. Recovered
in #231.

IT HAPPENED AGAIN ON 2026-09-10, AND THIS CHECK CAUGHT IT IN 25 SECONDS
-----------------------------------------------------------------------
#242 merged to `main` at 06:48:51Z. #243, based on #242's branch, merged at
06:49:06Z - fifteen seconds after its base had already gone to `main`, so its
content landed on a branch nothing would carry. #244 merged at 06:49:19Z, that
push triggered this workflow, and at 06:49:31Z it failed naming #243 with its
base and what to do. #245 re-merged the base branch and the next run was green.

So the reactive half WORKS and is not what needs building. What this round adds
is the two things it could not see:

  * **A POPULATION.** The workflow passed `--limit 60` while 218 PRs were
    merged, so a PR stranded more than 60 merges ago was invisible and the
    output said "checked 60" without saying 60 of what. Rule 7 on the check
    itself. `--limit 0` now means all, and a run that hits its limit says so
    instead of reporting a clean subset as a clean repository.

  * **THE STACK WHILE IT IS STILL OPEN.** This check can only fire AFTER a
    merge strands something. `--open-prs` looks at open PRs whose base is not
    `main`, which is the state that becomes the defect - and flags the sharp
    case: a base branch that is ALREADY an ancestor of `main`, so merging the
    PR onto it puts the content nowhere. #243 was in that state for 15
    seconds, and fifteen seconds is not a window anybody reviews.

Same shape as the orphaned-commit pattern `CLAUDE.md` records, arriving by a new
door: there, a commit was pushed to a branch whose PR had closed and no workflow
observed it. Here, a PR closed as merged and no workflow observed that its
content never arrived. **In both cases the repository knew and nobody asked.**

WHY THIS IS A SCRIPT AND NOT A GREP
------------------------------------
The question is about ANCESTRY, which only git can answer, joined to PR state,
which only the API can. Neither half is enough: a branch can be ahead of `main`
and merged (fine, another PR carried it), or behind and unmerged (fine, nothing
claims otherwise). The failure is the specific pair - **closed as merged, and
its commits are not in `main`.**

⚠  IT ASSUMES MERGE COMMITS, AND SAYS SO RATHER THAN GUESSING
--------------------------------------------------------------
A squash or rebase merge REWRITES the head commit, so the original SHA is not an
ancestor of `main` even when the content arrived. On this repository every merge
to date is a merge commit - verified over the last twelve merged PRs on
2026-09-08, all twelve ancestors - so ancestry is a sound signal here today.

If somebody turns on squash merging, this check starts failing on PRs that are
perfectly fine. **That is why the failure message names the assumption**: the
fix is then to compare `mergeCommit` rather than `headRefOid`, which the API also
returns, and not to delete the check.

`--squash-tolerant` does exactly that, and is not the default: it accepts a PR
whose merge commit is an ancestor even when its head is not. It is off by
default because it cannot distinguish "squashed onto main" from "merged into a
base branch that was later squashed onto main", and the second is the defect.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    ).stdout.strip()


def _is_ancestor(commit: str, of: str) -> bool:
    """`git merge-base --is-ancestor`. False for an unknown commit, not an error.

    An unknown SHA is the state a shallow clone produces, and it must not read
    as a defect - `--fetch-depth: 0` in the workflow is what makes the answer
    meaningful, and `main_is_known` below checks that separately.
    """
    if not commit:
        return False
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, of],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0


#: What `--limit 0` asks `gh` for. It rejects 0, and "all" is not a value it
#: takes, so the ceiling is explicit and the caller is told when a run reaches
#: it - an unstated ceiling is how "checked 60" came to stand for "checked".
ALL_LIMIT = 1000


def merged_prs(limit: int) -> list[dict]:
    out = subprocess.run(
        ["gh", "pr", "list", "--state", "merged", "--limit", str(limit),
         "--json", "number,title,headRefName,headRefOid,baseRefName,mergeCommit,mergedAt"],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        raise SystemExit(
            "gh pr list failed, so this check cannot run:\n"
            f"{out.stderr.strip()}\n"
            "It needs `gh` authenticated with repo read access. A check that "
            "cannot run must fail rather than pass - an absent answer is not a "
            "clean one."
        )
    return json.loads(out.stdout or "[]")


# Named, hand-verified squash-merges onto main.
# ---------------------------------------------
# The repository merges with merge commits, so ancestry of `headRefOid` is the
# sound signal (see the docstring). Two PRs predate that norm and were SQUASH-
# merged directly onto main - base=main, not a base branch - which rewrites the
# head SHA so ancestry can't see it, exactly the false alarm the docstring names.
# They are excused here BY NUMBER rather than by turning on `--squash-tolerant`
# globally, which would blind the check to the base-branch defect it exists for.
# Each was confirmed on 2026-09-08: its merge commit is an ancestor of main and
# its patch matches the PR head, so the content genuinely arrived.
#   #172  merge 9bdab5f  contract+collect: withdraw the fourth value, correct 853
#   #173  merge 1d7b59a  collect+contract: the Reddit listing sweep + denominator
# An entry only clears a PR whose MERGE COMMIT is an ancestor of main, so it can
# never excuse a PR whose content is actually missing.
SQUASHED_ONTO_MAIN = {172, 173}


def open_prs(limit: int) -> list[dict]:
    out = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--limit", str(limit),
         "--json", "number,title,headRefName,baseRefName"],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        raise SystemExit(
            "gh pr list --state open failed, so the open-PR check cannot run:\n"
            f"{out.stderr.strip()}"
        )
    return json.loads(out.stdout or "[]")


def stacked(*, main: str, limit: int) -> list[dict]:
    """Open PRs whose base is not `main`, worst first.

    Each is annotated with whether merging it RIGHT NOW would strand it:
    `base_merged` is true when the base branch tip is already an ancestor of
    `main`, which means the base has landed and nothing is left to carry this
    PR onward. That is exactly the state #243 was in.

    ⚠ IT REPORTS, IT DOES NOT GATE - AND THAT IS RULE 8, NOT TIMIDITY.
      `base_merged` is not by itself a defect: #245 resolved precisely this
      state by re-merging the base branch, which is a legitimate and correct
      move. So the condition is "needs a follow-up action", not "is wrong", and
      its false-positive rate against real stacks has never been measured. It
      ships as a warning on the PR, where the person who can act on it is
      looking, and is promoted to a gate only once measured.
    """
    rows = []
    for pr in open_prs(limit):
        base = pr.get("baseRefName") or ""
        if not base or base == main.split("/")[-1]:
            continue
        base_ref = f"origin/{base}"
        base_tip = _git("rev-parse", "--verify", "--quiet", base_ref)
        pr["_base_tip"] = base_tip
        pr["_base_known"] = bool(base_tip)
        # A base branch that no longer exists is its own signal: GitHub usually
        # retargets, but a deleted base with an open PR against it is a state
        # worth naming rather than skipping silently.
        pr["_base_merged"] = bool(base_tip) and _is_ancestor(base_tip, main)
        rows.append(pr)
    rows.sort(key=lambda p: (not p["_base_merged"], p["number"]))
    return rows


def check(*, main: str, limit: int, squash_tolerant: bool) -> tuple[list[dict], list[dict]]:
    """Returns (stranded, ok). `stranded` is what fails the build."""
    stranded: list[dict] = []
    ok: list[dict] = []
    for pr in merged_prs(limit):
        head = pr.get("headRefOid") or ""
        if _is_ancestor(head, main):
            ok.append(pr)
            continue
        merge_commit = (pr.get("mergeCommit") or {}).get("oid") or ""
        if pr.get("number") in SQUASHED_ONTO_MAIN and _is_ancestor(merge_commit, main):
            ok.append(pr)
            continue
        if squash_tolerant and _is_ancestor(merge_commit, main):
            ok.append(pr)
            continue
        pr["_head_known"] = bool(_git("cat-file", "-t", head))
        pr["_merge_commit"] = merge_commit
        stranded.append(pr)
    return stranded, ok


def _report_stacked(*, main: str, limit: int) -> int:
    """Print the open-PR report. ALWAYS returns 0 - it is a warning, not a gate."""
    rows = stacked(main=main, limit=limit)
    if not rows:
        print(f"no open PR targets anything but {main}. Nothing can be stranded "
              "by a merge today.")
        return 0

    will_strand = [p for p in rows if p["_base_merged"]]
    print(f"{len(rows)} open PR(s) are stacked on a branch rather than on {main}")
    print(f"  base already merged into {main}: {len(will_strand)}")
    print()
    for pr in rows:
        print(f"  #{pr['number']}  {pr['title'][:60]}")
        print(f"      head  {pr['headRefName']}")
        print(f"      base  {pr['baseRefName']}"
              f"{'' if pr['_base_known'] else '   (branch not in this clone)'}")
        if pr["_base_merged"]:
            print("      >> ITS BASE HAS ALREADY LANDED ON MAIN. Merging this PR now")
            print("         puts its commits on a branch nothing will carry onward -")
            print("         it will report `merged` and its content will not be on")
            print("         main. Merge it and then re-merge the base branch, or")
            print("         retarget it at main first. #243/#245 is the worked")
            print("         example, and #245 is the re-merge.")
            # GitHub Actions annotation, so it lands on the PR rather than only
            # in a log nobody opens.
            print(f"::warning title=Stacked PR whose base has already "
                  f"merged::#{pr['number']} is based on "
                  f"{pr['baseRefName']}, which is already an ancestor of {main}. "
                  f"Merging it as-is strands its commits. Retarget at main, or "
                  f"re-merge the base branch afterwards.")
        else:
            print("      (base not yet merged - a legitimate stack. Merge this one")
            print("       BEFORE its base goes to main, or the base carries it.)")
            print(f"::notice title=Stacked PR::#{pr['number']} targets "
                  f"{pr['baseRefName']}, not {main}. Merging the base into {main} "
                  f"without merging this one first leaves it behind.")
        print()
    print("-" * 74)
    print("This check NEVER FAILS THE BUILD. A stack is legitimate and a base that")
    print("has landed is a state somebody can still fix - so it is a warning where")
    print("the person who can act on it is looking, not a gate (rule 8: an")
    print("unmeasured check ships as a weight, and this one's false-positive rate")
    print("against real stacks has never been measured).")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main", default="origin/main",
                        help="the ref every merged PR must have reached")
    parser.add_argument("--limit", type=int, default=60,
                        help="how many recent merged PRs to check")
    parser.add_argument("--open-prs", action="store_true",
                        help="instead of checking merged PRs, report OPEN PRs "
                             "whose base is not `main` - the stack while it can "
                             "still be fixed. Never fails the build; see "
                             "`stacked()` on why that is rule 8.")
    parser.add_argument("--squash-tolerant", action="store_true",
                        help="accept a PR whose MERGE COMMIT is an ancestor. See "
                             "the module docstring: this hides the defect the "
                             "check exists for, so it is off by default.")
    args = parser.parse_args(argv)

    if not _git("cat-file", "-t", args.main):
        raise SystemExit(
            f"{args.main} is not in this clone, so ancestry cannot be computed. "
            "In CI this means `fetch-depth: 0` is missing on actions/checkout - "
            "a shallow clone has no history to walk, and every PR would look "
            "stranded. Failing rather than reporting a false alarm."
        )

    requested = args.limit or ALL_LIMIT

    if args.open_prs:
        return _report_stacked(main=args.main, limit=requested)

    stranded, ok = check(main=args.main, limit=requested,
                         squash_tolerant=args.squash_tolerant)

    total = len(stranded) + len(ok)
    print(f"checked {total} merged PR(s) against {args.main}")
    if total >= requested:
        # THE POPULATION, NOT JUST THE COUNT (rule 7). A run that returned
        # exactly as many PRs as it asked for has probably been truncated, and
        # a clean subset reported as a clean repository is the failure this
        # line exists to prevent.
        print(f"  !! THIS IS THE MOST RECENT {requested}, NOT ALL OF THEM. The")
        print("    result came back at the limit, so older merged PRs were not")
        print("    examined and a strand among them would not appear here.")
        print("    Re-run with --limit 0 for every merged PR.")
    print(f"  reached {args.main}: {len(ok)}")
    print(f"  STRANDED           : {len(stranded)}")

    if not stranded:
        print()
        print("Every merged PR's head commit is an ancestor. Nothing is stranded.")
        return 0

    print()
    print("=" * 74)
    print("MERGED PRs WHOSE COMMITS ARE NOT IN main")
    print("=" * 74)
    for pr in stranded:
        print()
        print(f"  #{pr['number']}  {pr['title'][:64]}")
        print(f"      head    {pr['headRefName']} @ {pr['headRefOid'][:10]}"
              f"{'' if pr['_head_known'] else '   (commit not in this clone)'}")
        print(f"      base    {pr['baseRefName']}")
        print(f"      merged  {pr.get('mergedAt')}  into {pr['baseRefName']}")
        if pr["baseRefName"] != "main":
            print("      >> merged into a BRANCH, not main. If that branch was never")
            print("         merged onward, this PR's content is not on main and")
            print("         nothing else will say so.")
    print()
    print("-" * 74)
    print("WHAT TO DO")
    print("  If the base branch still exists and is ahead of main, open a PR from")
    print("  it to main - the content is there, it just never arrived. #231 is the")
    print("  worked example.")
    print()
    print("  IF THIS REPOSITORY HAS TURNED ON SQUASH OR REBASE MERGING, this check")
    print("  is now wrong rather than the repository: those rewrite the head")
    print("  commit, so a perfectly-merged PR's SHA is not an ancestor. Compare")
    print("  `mergeCommit` instead (`--squash-tolerant` does), and read the module")
    print("  docstring first - the flag cannot tell a squash onto main from a")
    print("  squash of a base branch, and the second is the defect.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
