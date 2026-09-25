"""Nothing in the working tree names a machine or carries a credential.

Written for the decision to make this repository public. Going public is
effectively irreversible — forks and archives persist after a switch back — so
the checks that matter run before the switch, and keep running after it.

⚠ THIS CHECKS THE WORKING TREE, WHICH IS NOT THE SAME AS THE HISTORY, and that
  limit is the most important sentence in this file. A public repository
  exposes every commit ever pushed. Redacting a value here leaves it in the
  commit that introduced it, reachable by anyone who clones. Removing it from
  history needs a rewrite (`git filter-repo`) and a force-push, which rewrites
  shared history and breaks every open PR — a decision, not a test.

  Two known values are in history and not in the tree:

      a third party's live database password, harvested from a public X post
      into `articles/deepseek-v4-pro/REPORT.md` and redacted 2026-09-25

      three real machine names, replaced with stable aliases the same day

WHAT WAS AUDITED AND FOUND CLEAN, 2026-09-25, over every blob reachable from
the pushed refs — 2,729 blobs:

    .env ever committed, any branch, any point            NEVER
      only .env.example and web/.env.example
    openrouter / openai / anthropic keys                       0
    github tokens · AWS keys · private key blocks · JWTs       0
    rapidapi keys · webhook URLs                               0

Every other credential-shaped string is a placeholder inside harvested article
text (`YOUR_DEEPSEEK_API_KEY`) or a test fixture (`user:pw`).

⚠ WHAT A SCAN CANNOT FIND, AND THIS IS THE LIMIT THAT MATTERS MOST. Every
  check below is a pattern over text. A real person's name in plain prose,
  with no marker, in no harvested set, matches nothing and never will.

  @anoojntglobal-sudo's reading pass on 2026-09-25 found **1,073 handles in
  `_github_comments.json`** that no scan here could have matched: staging
  stores GitHub authors as numeric ids, and the values carry no marker at all.
  Not one of them would have appeared in the blob scan that produced the
  summary above.

  So the audit above says what the PATTERNS found, and nothing about what is
  there. Reading was the only check that found the 1,073, and the next person
  will assume otherwise unless this paragraph stops them.

WHAT THIS FILE DELIBERATELY DOES NOT DECIDE. Two findings from that audit are
judgement calls rather than defects, and they are recorded on the issue rather
than enforced here:

    the AWS database host, its port, database name and username appear in
    docs 44 times — the password is masked, so publishing hands an attacker
    everything but one factor

    530 social handles sit in `articles/`, 3.8 MB of harvested posts, and 39
    email addresses sit in `_github_shape_experiment.json` at the root — a
    privacy and copyright question rather than a security one, and "each was
    public individually" is not the same claim as "we republished them as a
    dataset"

⚠ THE EMAILS AND THE HANDLES ARE IN DIFFERENT PLACES, and my first audit said
  both were in `articles/`. They are not: `articles/` holds ONE email, a
  corporate customer-service address. 24 of the real ones are at the
  repository root in a file whose name gives no hint it carries anyone's
  contact details, so removing the directory would not have removed them.
  The correction is @anoojntglobal-sudo's, and it is the reason an exclusion
  list has to be measured rather than assumed from directory names.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: The real device names this repository has carried. Replaced with stable
#: aliases rather than deleted: several passages are measurements ABOUT two
#: machines disagreeing, and collapsing them to "this machine" would destroy
#: the finding the passage exists to record.
MACHINE_NAMES = ("ANOOJ", "LenovoPB", "LAPTOP-TA28DHTF")

#: Files that must contain a device name to do their job. Excluded BY NAME
#: rather than by the string, so an unrelated real name appearing in one of
#: them still fails.
#:
#: ⚠ THIS FILE IS ON THE LIST, AND IT FAILED CI BECAUSE IT WAS NOT. The scan
#:   reads `git ls-files`, which does not list untracked files - so while this
#:   test was new and uncommitted it could not see itself, passed locally, and
#:   failed the moment the commit made it tracked. It names the three devices
#:   in `MACHINE_NAMES` in order to search for them, which is the
#:   mention-versus-use trap in the one test written to catch device names.
#:   Sixteenth instance in this repository.
#:
#:   The general lesson, worth more than this fix: A TEST THAT READS
#:   `git ls-files` CANNOT SEE ITSELF UNTIL IT IS COMMITTED, so a green local
#:   run of a brand-new file proves less than it appears to.
MAY_NAME_A_MACHINE = {
    # asserts a hostname never reaches a page, so it plants one
    "test_admin_operations_surfaces.py",
    # defines the names being searched for
    "test_this_repository_could_be_made_public.py",
}

PLANTED = "SOMEONES-LAPTOP-9000"

CREDENTIALS = {
    "openrouter key": r"sk-or-v1-[a-fA-F0-9]{32,}",
    "openai key": r"sk-[A-Za-z0-9]{32,}",
    "anthropic key": r"sk-ant-[A-Za-z0-9_\-]{24,}",
    "github token": r"gh[pousr]_[A-Za-z0-9]{30,}",
    "aws access key": r"AKIA[0-9A-Z]{16}",
    "private key block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "jwt": r"eyJ[A-Za-z0-9_\-]{15,}\.eyJ[A-Za-z0-9_\-]{15,}\.",
}

#: A DSN whose password is neither masked nor an obvious fixture. The shapes
#: allowed are the ones a reader cannot mistake for a real credential.
FIXTURE_PASSWORDS = (
    "***", "postgres", "pw", "p", "secret", "letta",
    "TESTSECRET-dbpassword", "password",
)


def tracked_text_files() -> list[pathlib.Path]:
    """Every tracked file, skipping what cannot hold a readable secret.

    `git ls-files` rather than a walk, for the reason #428 established: a
    walk counts whatever is lying in the working directory, and the question
    here is what would be PUBLISHED.
    """
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True, check=True,
    ).stdout.decode("utf-8", "replace")
    skip = {".png", ".jpg", ".jpeg", ".gif", ".woff2", ".woff", ".ico", ".pdf"}
    return [
        ROOT / name for name in out.split("\0")
        if name and pathlib.Path(name).suffix.lower() not in skip
    ]


class TestNoTrackedFileNamesAMachine:
    def test_no_real_device_name_is_in_the_tree(self):
        """⚠ ASKED FOR TWICE BEFORE THIS TEST EXISTED. A device name on a
        shared surface identifies a person's laptop, and one of the three was
        a default Windows name rather than a project one."""
        offenders = []
        for path in tracked_text_files():
            if path.name in MAY_NAME_A_MACHINE:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for name in MACHINE_NAMES:
                if re.search(rf"\b{re.escape(name)}\b", text):
                    offenders.append(f"{path.relative_to(ROOT)}: {name}")
        assert not offenders, (
            "real machine names in tracked files:\n  " + "\n  ".join(offenders)
            + "\nUse a stable alias (machine-A/B/C) so a measurement about two "
            "machines keeps saying they were two."
        )

    def test_the_planted_fake_is_still_planted(self):
        """⚠ THE CONTROL. If the exclusion ever silently covered a real name,
        this is what says the excluded file is still the test it was excluded
        for."""
        source = (ROOT / "tests" / "test_admin_operations_surfaces.py").read_text(
            encoding="utf-8",
        )
        assert PLANTED in source
        for name in MACHINE_NAMES:
            assert name not in source

    def test_the_exemption_list_stays_two_files(self):
        """⚠ AN EXEMPTION LIST IS A HOLE AND GROWS QUIETLY. Two files have a
        reason to carry a device name: the one that plants a fake, and this
        one, which defines the names it searches for. A third is a mistake or
        a decision, and either way somebody should have to write it here."""
        assert {
            "test_admin_operations_surfaces.py",
            "test_this_repository_could_be_made_public.py",
        } == MAY_NAME_A_MACHINE


class TestNoTrackedFileCarriesACredential:
    def test_no_key_token_or_private_key_is_in_the_tree(self):
        offenders = []
        for path in tracked_text_files():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for label, pattern in CREDENTIALS.items():
                m = re.search(pattern, text)
                if m:
                    offenders.append(f"{path.relative_to(ROOT)}: {label}")
        assert not offenders, "credentials in tracked files:\n  " + "\n  ".join(offenders)

    def test_no_dsn_carries_an_unmasked_password(self):
        """⚠ THIS IS THE ONE THAT FIRED FOR REAL. A harvested X post carried a
        third party's live production DSN into `articles/`, and publishing the
        repository would have republished it in a searchable form. It was
        already public on X; that is not the same exposure."""
        rx = re.compile(r"postgres(?:ql)?://([^\s:/@\"']+):([^\s@\"']+)@")
        offenders = []
        for path in tracked_text_files():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for user, password in rx.findall(text):
                if password in FIXTURE_PASSWORDS or password.startswith("${"):
                    continue
                offenders.append(
                    f"{path.relative_to(ROOT)}: {user}:<{len(password)} chars>"
                )
        assert not offenders, (
            "a connection string carries what looks like a real password:\n  "
            + "\n  ".join(offenders)
        )

    def test_dotenv_stays_ignored(self):
        """The rule that held throughout: `.env` has never been committed, on
        any branch, at any point."""
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        assert re.search(r"^\.env$", ignore, re.M)
        assert re.search(r"^\.env\.\*$", ignore, re.M)
        assert re.search(r"^!\.env\.example$", ignore, re.M)

        committed = subprocess.run(
            ["git", "-C", str(ROOT), "log", "--all", "--full-history",
             "--name-only", "--pretty=format:", "--", ".env", "**/.env"],
            capture_output=True, check=True,
        ).stdout.decode("utf-8", "replace")
        named = {ln for ln in committed.splitlines() if ln.strip()}
        assert not named, f"a dotenv was committed at some point: {named}"
