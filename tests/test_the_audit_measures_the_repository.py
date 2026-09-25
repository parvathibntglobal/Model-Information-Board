"""#428: `test_column_states` answered differently depending on whose disk it ran on.

Three times in one day, on three different commits, the same `main` was red for
@anoojntglobal-sudo and green for @parvathibntglobal:

    #416  b7c5ca7     1 failed / 8 passed
    #426  5a45974     1 failed / 8 passed
    #425  233e48b     1 failed / 8 passed

Neither reading was wrong. `scripts/audit_columns.py` collected its evidence
with `rglob`, which walks the **filesystem**, so every untracked file in a
working directory counted as a reader of every column it mentioned.

⚠ IT FAILED IN THE EXPENSIVE DIRECTION. An untracked scratch probe makes a
  `write_only` column look `written+read`, so **the audit that exists to enforce
  rule 9 — a produced value must have a named consumer — goes quiet about a
  column whose only reader is a file nobody else has.** The red case was the
  visible half; the silent half is the one that matters.

⚠ AND IT IS A GATE WITH NO MEASURABLE POPULATION (rule 8). "Whatever happens to
  be in the author's working directory" is different for every person and every
  hour, so no false-positive rate could be stated for it, and two people could
  not agree on whether `main` was green.

The population is now `git ls-files`, which includes staged-but-uncommitted
files — a file you are about to commit is a real reader.

⚠ AND THERE IS NO `rglob` FALLBACK FOR THE NOT-A-CHECKOUT CASE. A fallback
  would reintroduce the defect wherever it fired, silently. Rule 12: a fallback
  that can succeed on a wrong input is not a fallback.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_columns  # noqa: E402

AUDIT = ROOT / "scripts" / "audit_columns.py"

#: The file #428 demonstrated with, byte for byte.
SCRATCH = ROOT / "scripts" / "_scratch_demo_probe.py"
SCRATCH_BODY = (
    '"""Scratch probe, untracked, never committed."""\n'
    'SQL = "SELECT abstained, assumptions FROM answer"\n'
)


@pytest.fixture
def an_untracked_probe():
    """#428's two-line file, created and removed whatever happens.

    ⚠ A REAL FILE ON DISK RATHER THAN A MOCK, because the whole defect is that
      the audit read the disk. A test that stubs the filesystem out cannot
      distinguish the fix from the bug.
    """
    SCRATCH.write_text(SCRATCH_BODY, encoding="utf-8")
    try:
        yield SCRATCH
    finally:
        SCRATCH.unlink(missing_ok=True)


class TestTheUntrackedFileIsNotEvidence:
    def test_an_untracked_probe_is_not_in_the_population(self, an_untracked_probe):
        assert an_untracked_probe.exists(), "the fixture did not write the file"
        assert an_untracked_probe not in audit_columns._source_files()

    def test_the_filesystem_still_has_it(self, an_untracked_probe):
        """⚠ THE CONTROL, AND WITHOUT IT THE TEST ABOVE PASSES FOR THE WRONG
        REASON. If the fixture silently failed to write, "not in the
        population" would be true of a file that does not exist, and the test
        would go on passing after somebody restored `rglob`."""
        walked = list((ROOT / "scripts").rglob("_scratch_demo_probe.py"))
        assert walked == [an_untracked_probe]

    def test_tracked_files_are_still_found(self):
        """The population must not have narrowed to nothing. A collector that
        returns `[]` also has no untracked files in it."""
        found = audit_columns._source_files()
        assert ROOT / "scripts" / "audit_columns.py" in found
        assert ROOT / "judge" / "app.py" in found
        assert ROOT / "collect" / "triage" / "specificity.py" in found

    def test_the_web_population_is_tracked_too(self):
        """Both collectors had the same `rglob`, and fixing one would leave the
        JS side reading the disk."""
        found = audit_columns._web_files()
        assert ROOT / "web" / "src" / "api" / "index.js" in found

    def test_a_tracked_file_deleted_on_disk_is_not_in_the_population(self):
        """⚠ `git ls-files` LISTS A DELETION UNTIL IT IS STAGED, and every
        caller opens what the collector returns. Deleting `PipelinePanel.jsx`
        therefore errored six checks with `FileNotFoundError` — a crash, not a
        finding, and one that says nothing about the deletion being right or
        wrong.

        The direction matters: a file that is not on disk can only stop
        crediting a reader, never invent one, so this moves the audit's answer
        toward `no_consumer` — the state the gate complains about. That is why
        it is not #428 running backwards.
        """
        gone = ROOT / "web" / "src" / "components" / "_deleted_on_disk_probe.jsx"
        gone.write_text("export default function P() { return null }\n", encoding="utf-8")
        try:
            subprocess.run(
                ["git", "-C", str(ROOT), "add", "--intent-to-add", str(gone)],
                check=True, capture_output=True,
            )
            gone.unlink()
            listed = subprocess.run(
                ["git", "-C", str(ROOT), "ls-files", "--", "web/src/components/*.jsx"],
                check=True, capture_output=True, text=True,
            ).stdout
            assert "_deleted_on_disk_probe.jsx" in listed, (
                "the control failed: git no longer lists the deleted file, so "
                "this test would pass without the filter"
            )
            assert gone not in audit_columns._web_files()
        finally:
            subprocess.run(
                ["git", "-C", str(ROOT), "rm", "--cached", "--force",
                 "--ignore-unmatch", "-q", str(gone)],
                capture_output=True,
            )
            gone.unlink(missing_ok=True)

    def test_tests_and_vendored_directories_are_still_skipped(self):
        """`SKIP` now filters git's paths rather than the walker's. Its job did
        not change and neither did its effect — a test file is not evidence
        that production reads a column."""
        for path in audit_columns._source_files() + audit_columns._web_files():
            assert not audit_columns.SKIP.search(str(path)), path


class TestItRefusesRatherThanFallingBack:
    def test_a_directory_that_is_not_a_checkout_raises(self, tmp_path, monkeypatch):
        """⚠ THE ONE BEHAVIOUR THAT KEEPS THE FIX FIXED. An `except: return
        rglob(...)` here would restore the defect for anybody whose invocation
        happened not to reach git, and it would do it without a word."""
        monkeypatch.setattr(audit_columns, "ROOT", tmp_path)
        with pytest.raises(audit_columns.NotACheckout):
            audit_columns._source_files()

    def test_the_refusal_says_what_it_could_not_read(self, tmp_path, monkeypatch):
        monkeypatch.setattr(audit_columns, "ROOT", tmp_path)
        with pytest.raises(audit_columns.NotACheckout) as caught:
            audit_columns._source_files()
        assert "checkout" in str(caught.value)

    def test_a_missing_git_binary_is_not_silently_survivable(self):
        """`FileNotFoundError` from `subprocess.run` is the no-git case, and it
        is converted rather than caught-and-ignored."""
        source = AUDIT.read_text(encoding="utf-8")
        body = source[source.index("def _tracked("):source.index("def _source_files(")]
        assert "except FileNotFoundError" in body
        assert "raise NotACheckout" in body


class TestTheWalkIsGone:
    def test_no_collector_walks_the_filesystem(self):
        """⚠ THE MENTION-VERSUS-USE GUARD. The docstrings above `_tracked`
        explain the `rglob` defect at length and name it repeatedly, and a
        plain substring search over this file reports those sentences as the
        bug they exist to describe. Comments and docstrings are stripped first.

        Twelfth instance of this trap in this repository, which is why it is
        written out rather than assumed."""
        import ast

        tree = ast.parse(AUDIT.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "rglob":
                raise AssertionError(
                    "audit_columns.py calls rglob again — the population must "
                    "come from git, see #428"
                )

    def test_the_collectors_go_through_one_function(self):
        """Two collectors with two implementations is how one of them gets
        fixed and the other does not."""
        source = AUDIT.read_text(encoding="utf-8")
        source = re.sub(r'"""[\s\S]*?"""', "", source)
        for fn in ("def _source_files(", "def _web_files("):
            body = source[source.index(fn):]
            body = body[:body.index("\n\n\n")] if "\n\n\n" in body else body
            assert "_tracked(" in body, f"{fn} does not read the tracked population"
