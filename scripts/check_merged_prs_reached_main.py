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
        if squash_tolerant and _is_ancestor(merge_commit, main):
            ok.append(pr)
            continue
        pr["_head_known"] = bool(_git("cat-file", "-t", head))
        pr["_merge_commit"] = merge_commit
        stranded.append(pr)
    return stranded, ok


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main", default="origin/main",
                        help="the ref every merged PR must have reached")
    parser.add_argument("--limit", type=int, default=60,
                        help="how many recent merged PRs to check")
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

    stranded, ok = check(main=args.main, limit=args.limit,
                         squash_tolerant=args.squash_tolerant)

    print(f"checked {len(stranded) + len(ok)} merged PR(s) against {args.main}")
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
