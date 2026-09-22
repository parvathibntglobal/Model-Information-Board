"""A fetch says what it is doing, in the terminal, while it does it.

WHAT THERE WAS. The run wrote `var/fetch/<run_id>.jsonl` and the web UI tailed
it. From a console there was nothing at all: `/fetch/start` spawned the script
with `stdout=DEVNULL, stderr=DEVNULL`, so a run clicked on the admin page threw
away every word it said. The terminal that started the backend went quiet for
forty minutes and then the board had changed, and reading what had happened
meant opening the JSONL and decoding it by eye.

Both halves are needed and neither is sufficient: the script has to render
itself, AND the spawn has to let it through.

⚠ THE RENDERER INVENTS NOTHING. Every stage already reports its own counts -
  `documents_inserted`, `sieve_kept`, `quota_remaining`, forty more - and those
  are printed as they arrive. A token total or a dollar cost in the closing box
  would be the most useful line there and neither is recorded by the run, so it
  is absent rather than derived (rule 3).
"""

from __future__ import annotations

import pathlib

from judge import fetch_console

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "judge" / "app.py"
SCRIPT = ROOT / "scripts" / "fetch_model.py"


def _stage(**over):
    base = {
        "kind": "stage", "id": "E2R", "name": "Harvest . Reddit",
        "status": "ok", "at": "2026-09-21T07:30:44Z",
    }
    base.update(over)
    return base


class TestTheLineIsScannable:
    def test_the_status_column_lines_up_across_statuses(self):
        """⚠ THE FIRST VERSION PADDED THE STATUS TO A FIXED WIDTH, which put
        four spaces between the rule and the word on every `ok` line - so the
        eye had to find where the dashes stopped instead of running down a
        solid column. The dashes absorb the difference instead."""
        ends = {
            st: fetch_console.stage(_stage(status=st))[0]
            for st in ("ok", "running", "error", "skipped")
        }
        widths = {len(v) for v in ends.values()}
        assert widths == {fetch_console.WIDTH}, (
            f"lines are not all {fetch_console.WIDTH} wide: {widths}"
        )
        for st, line in ends.items():
            assert line.endswith(f" {st}  07:30:44")

    def test_a_long_stage_name_still_produces_a_rule(self):
        # `max(3, ...)`: a name long enough to eat the line must not make the
        # dash count negative and the line unreadable.
        line = fetch_console.stage(_stage(name="x" * 200))[0]
        assert "---" in line

    def test_the_clock_is_the_time_and_not_the_date(self):
        assert fetch_console._clock("2026-09-21T07:30:44Z") == "07:30:44"
        # A record with no timestamp says so rather than printing today's.
        assert fetch_console._clock(None) == "--:--:--"


class TestItPrintsWhatTheStageReported:
    def test_every_count_is_shown_not_a_chosen_subset(self):
        """Which counts matter differs per stage and per reader -
        `quota_remaining` is the whole story on a Reddit arm and noise on
        arXiv - so picking would be deciding for them."""
        lines = fetch_console.stage(_stage(
            quota_remaining=999810, documents_inserted=18, http_errors=0,
        ))
        body = " ".join(lines)
        assert "quota remaining=999810" in body
        assert "documents inserted=18" in body
        assert "http errors=0" in body

    def test_a_nested_count_is_flattened_rather_than_dropped(self):
        lines = fetch_console.stage(_stage(by_reason={"no-entity": 69, "short": 2}))
        assert "by reason=[no-entity=69 short=2]" in " ".join(lines)

    def test_detail_wraps_at_the_body_indent(self):
        lines = fetch_console.stage(_stage(detail="word " * 80))
        assert len(lines) > 2
        for line in lines[1:]:
            assert line.startswith("    ")
            assert len(line) <= fetch_console.WIDTH

    def test_the_heartbeat_is_silent(self):
        """One a minute, for the reaper. A terminal printing it would bury the
        stages this exists to make readable."""
        assert fetch_console.render(
            {"kind": "alive", "at": "2026-09-21T07:30:44Z"},
            model_version_id="mv_x",
        ) == []


class TestTheClosingBoxSaysOnlyWhatWasMeasured:
    def test_it_carries_the_status_and_the_detail(self):
        lines = fetch_console.ending(
            {"kind": "end", "status": "error", "detail": "3 stage(s) errored"},
            model_version_id="mv_x",
        )
        assert any("RUN ERROR" in x for x in lines)
        assert any("3 stage(s) errored" in x for x in lines)

    def test_it_does_not_invent_a_cost_or_a_token_total(self):
        """Rule 3. The `end` record holds neither; the ledger does, written by
        the client that made each call. A figure computed in a renderer is a
        number with no measurement behind it."""
        text = " ".join(fetch_console.ending(
            {"kind": "end", "status": "ok", "detail": "fetch complete"},
            model_version_id="mv_x",
        )).lower()
        assert "$" not in text
        assert "token" not in text


class TestBothHalvesAreWired:
    def test_the_script_renders_each_record_as_it_writes_it(self):
        src = SCRIPT.read_text(encoding="utf-8")
        assert "from judge import fetch_console" in src
        assert "fetch_console.header(" in src
        assert src.count("fetch_console.render(") == 2, (
            "both the stage path and the end record must render, or a run "
            "narrates itself and then finishes in silence"
        )

    def test_the_spawn_no_longer_discards_the_output(self):
        """⚠ THE HALF THAT IS EASY TO MISS. A script that renders itself into
        a `DEVNULL` is a script nobody can read."""
        src = APP.read_text(encoding="utf-8")
        block = src[src.index("def start_fetch"):]
        block = block[:block.index("class StopFetchRequest")]
        assert "stdout=subprocess.DEVNULL" not in block
        assert "stderr=subprocess.DEVNULL" not in block

    def test_the_spawn_does_not_use_a_pipe(self):
        """⚠ A PIPE LOOKS EQUIVALENT AND DEADLOCKS. Nobody waits on this
        process, so a filled pipe with no reader stops the run - which is
        worse than the silence being fixed."""
        src = APP.read_text(encoding="utf-8")
        block = src[src.index("def start_fetch"):]
        block = block[:block.index("class StopFetchRequest")]
        assert "subprocess.PIPE" not in block

    def test_printing_can_be_turned_off_without_changing_the_spawn(self):
        src = SCRIPT.read_text(encoding="utf-8")
        assert 'os.getenv("FETCH_QUIET"' in src

    def test_printing_never_ends_a_run(self):
        """A Windows console in cp1252 raises on a character it cannot map,
        and that exception would unwind out of `stage()` - the run dying
        because it tried to describe itself."""
        src = SCRIPT.read_text(encoding="utf-8")
        say = src[src.index("    def _say(self"):]
        say = say[:say.index(chr(10) + "    def ", 10)]
        assert "except Exception" in say
        assert '"replace"' in say
