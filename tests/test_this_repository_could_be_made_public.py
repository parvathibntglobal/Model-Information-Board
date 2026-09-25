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

WHAT THIS FILE DELIBERATELY DOES NOT DECIDE. Two findings from that audit are
judgement calls rather than defects, and they are recorded on the issue rather
than enforced here:

    the AWS database host, its port, database name and username appear in
    docs 44 times — the password is masked, so publishing hands an attacker
    everything but one factor

    531 social handles and 33 personal email addresses sit in `articles/`,
    3.8 MB of harvested posts — a privacy and copyright question, not a
    security one, and "each was public individually" is not the same as
    republishing them as a dataset
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

#: ⚠ A PLANTED FAKE, AND THE OPPOSITE OF A LEAK. `test_admin_operations_
#:   surfaces.py` asserts that a hostname never reaches a page, so it needs a
#:   hostname to plant. Excluding the file by name rather than the string, so
#:   a real name appearing there still fails.
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
            if path.name == "test_admin_operations_surfaces.py":
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
        """⚠ THE CONTROL. If the exclusion above ever silently covered a real
        name, this is what says the excluded file is still the test it was
        excluded for."""
        source = (ROOT / "tests" / "test_admin_operations_surfaces.py").read_text(
            encoding="utf-8",
        )
        assert PLANTED in source
        for name in MACHINE_NAMES:
            assert name not in source


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
