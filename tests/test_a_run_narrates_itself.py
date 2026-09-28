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

    def test_a_run_that_measured_nothing_prints_no_totals(self):
        """⚠ RULE 3, AND IT IS WHY EVERY LINE IS CONDITIONAL. A fetch that
        never reached E5 - nothing to read, or an error before it - has no
        tokens and no cost, and the box must be short rather than print zeros
        that look like a run which sent nothing and got nothing back."""
        text = " ".join(fetch_console.ending(
            {"kind": "end", "status": "ok", "detail": "fetch complete"},
            model_version_id="mv_x",
        )).lower()
        assert "$" not in text
        assert "token" not in text
        assert "sent" not in text

    def test_it_prints_the_totals_the_run_recorded(self):
        lines = fetch_console.ending({
            "kind": "end", "status": "ok", "detail": "fetch complete",
            "llm": "deepseek/deepseek-v4-flash",
            "sent_threads": 9, "sent_posts": 20, "sent_chars": 7195,
            "tokens_in": 108575, "tokens_out": 9613, "cost_usd": 0.017892,
            "claims_verified": 11, "claims_stored": 9, "cells_written": 3,
        }, model_version_id="mv_x")
        body = chr(10).join(lines)
        assert "llm     deepseek/deepseek-v4-flash" in body
        assert "sent    9 thread(s) - 20 post(s), 7,195 chars" in body
        assert "tokens  in 108,575  out 9,613" in body
        assert "back    11 claim(s) verified, 9 stored, 3 cell(s)" in body

    def test_the_cost_says_it_is_not_an_invoice(self):
        """#381: the ledger's dollars are tokens times a configured rate, and
        the two rates in this repo disagreed by 2.11x with neither ever
        checked against a bill. Bare, it reads as measured."""
        body = chr(10).join(fetch_console.ending(
            {"kind": "end", "status": "ok", "cost_usd": 0.0179},
            model_version_id="mv_x",
        ))
        assert "$0.017900" in body
        assert "not an invoice" in body

    def test_calls_that_reported_no_usage_are_named(self):
        """A provider that stops reporting usage silently disables the daily
        cap, and the symptom is a total that looks like good news."""
        body = chr(10).join(fetch_console.ending({
            "kind": "end", "status": "ok", "tokens_in": 10, "tokens_out": 2,
            "unmetered_calls": 3,
        }, model_version_id="mv_x"))
        assert "3 call(s) reported NO usage" in body
        # and stays quiet when it did not happen
        quiet = chr(10).join(fetch_console.ending({
            "kind": "end", "status": "ok", "tokens_in": 10, "tokens_out": 2,
            "unmetered_calls": 0,
        }, model_version_id="mv_x"))
        assert "reported NO usage" not in quiet


class TestBothHalvesAreWired:
    def test_the_script_renders_each_record_as_it_writes_it(self):
        src = SCRIPT.read_text(encoding="utf-8")
        assert "from judge import fetch_console" in src
        assert "fetch_console.header(" in src
        assert src.count("fetch_console.render(") == 3, (
            "the stage path, the end record AND the per-thread record must "
            "all render, or a run narrates itself and then goes quiet for the "
            "one part that takes forty minutes"
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


class TestTheTotalsAreRecordedNotDerived:
    """The numbers existed in local variables and died with the function."""

    def test_the_budget_counts_the_tokens_it_is_handed(self):
        src = (ROOT / "judge" / "extract" / "budget.py").read_text(encoding="utf-8")
        assert "self.input_tokens += completion.input_tokens" in src
        assert "self.output_tokens += completion.output_tokens" in src

    def test_the_run_records_its_own_spend_not_the_day_s(self):
        """⚠ `spent_usd` IS SEEDED WITH TODAY'S TOTAL because the cap is a
        daily one, so this run's cost is the delta. Reporting `spent_usd`
        would charge this run for every fetch since midnight."""
        src = SCRIPT.read_text(encoding="utf-8")
        assert "spent_before = budget.spent_usd" in src
        assert '"cost_usd": round(budget.spent_usd - spent_before, 6),' in src

    def test_the_totals_ride_on_the_end_record(self):
        """On the record rather than printed, so the terminal, the UI and a
        replay of an old log all read the same numbers from one place."""
        src = SCRIPT.read_text(encoding="utf-8")
        assert '"at": _now(), **self._summary}' in src
        assert "prog.record_summary(" in src

    def test_a_run_with_no_budget_still_reports_what_it_sent(self):
        """`Budget.from_env()` returns None when nothing is configured, and a
        run without a cap still sent threads and got claims back."""
        src = SCRIPT.read_text(encoding="utf-8")
        assert "} if budget is not None else {}),"  in src
        block = src[src.index("prog.record_summary("):]
        block = block[:block.index(")" + chr(10))]
        for always in ("sent_threads=", "claims_verified=", "claims_stored="):
            assert always in block, f"{always} must not depend on the budget"


class TestEachThreadSaysWhatCameBack:
    """⚠ THE NUMBERS EXISTED IN THE LOOP AND DIED IN IT. E5 emitted
    `reading thread 8/20` and nothing else, so a run could say which thread it
    was on and never what came back from it - how many claims survived, which
    capabilities, what the call cost. All of it was on `ExtractionRun` and in
    `Budget` the whole time.
    """

    def _t(self, **over):
        base = {
            "kind": "thread", "index": 5, "total": 20,
            "thread_context_id": "thread_context_43b741bd2a6fcd84", "posts": 2,
            "verified": 3, "rejected": 1, "unsalvaged": 0, "unclassified": 0,
            "proposed": 0, "keys": {"code.generation": 3},
            "tokens_in": 9817, "tokens_out": 1063, "usd": 0.001672,
        }
        base.update(over)
        return base

    def test_the_arrows_show_the_exchange(self):
        """`->` is the request and `<-` the answer, so a reader scanning a long
        E5 sees the shape without reading a word."""
        lines = fetch_console.thread(self._t())
        assert lines[0].startswith("  -> [5/20] thread_context_43b741bd2a6fcd84  2 post(s)")
        assert lines[1].startswith("     <- 3 verified, 1 rejected, 0 unsalvaged")

    def test_it_prints_the_capability_keys_and_their_counts(self):
        assert "code.generation x3" in chr(10).join(fetch_console.thread(self._t()))

    def test_a_thread_that_produced_nothing_says_why(self):
        """The line that separates a thread which said nothing from one the
        extractor could not read."""
        body = chr(10).join(fetch_console.thread(self._t(
            verified=0, keys=None, unsalvaged=7,
            no_claim_reason="all 7 proposed claim(s) failed the schema",
        )))
        assert "no claim: all 7 proposed claim(s) failed the schema" in body

    def test_the_cost_of_one_call_is_shown(self):
        body = chr(10).join(fetch_console.thread(self._t()))
        assert "in 9,817 / out 1,063 tok" in body
        assert "$0.001672" in body

    def test_a_retry_and_a_truncation_are_said_only_when_they_happened(self):
        """A column of `retries 0` is noise that hides the one saying 1."""
        quiet = chr(10).join(fetch_console.thread(self._t()))
        assert "retries" not in quiet and "TRUNCATED" not in quiet
        loud = chr(10).join(fetch_console.thread(self._t(schema_retries=1, truncated=True)))
        assert "retries 1" in loud and "TRUNCATED at the token ceiling" in loud

    def test_no_claim_text_ever_reaches_the_terminal(self):
        """⚠ COUNTS AND KEYS, NEVER THE QUOTE. A verified claim carries text
        from a harvested document, and a terminal line is the one place it
        would appear with no ruling, no attribution and no way to decline it.
        The callback must send counts, not claims."""
        # ⚠ THE ARGUMENT LIST, NOT THE FUNCTION BODY. The first version
        #   scanned the whole callback and tripped on `for claim, _quote in
        #   run.verified:` - a destructuring that DISCARDS the quote. Matching
        #   a mention rather than a use, for the sixth time in this repository.
        src = SCRIPT.read_text(encoding="utf-8")
        call = src[src.index("        prog.thread("):]
        call = call[:call.index(chr(10) + "        )") + 10]
        assert "verified=len(run.verified)," in call
        for leak in ("quote", "flattened", "raw_text"):
            assert leak not in call, f"the per-thread record carries {leak!r}"

    def test_the_cost_is_this_thread_s_share(self):
        """A per-thread figure is this thread's own, not the run's total.

        ⚠ THIS TEST USED TO ASSERT THE BUG, AND PASSED WHILE IT SHIPPED. The
          first version pinned the implementation - `before_in = budget...` and
          the subtraction that followed - on the reasoning that "a per-thread
          figure has to be a delta or every thread reports the running total".
          The reasoning was right about the problem and wrong about the fix,
          and the test could not tell: it checked the SHAPE OF THE CODE and
          never the value it produced, so it went green over twenty threads
          each reporting `0 tokens, $0.000000` under a total of $0.037854
          (ElevenLabs v3, 2026-09-23).

          It now asserts what must be TRUE of the figure rather than how it is
          spelled. `test_a_thread_reports_what_it_cost.py` holds the rest,
          including that the per-thread costs sum to what `charge` accumulates.
        """
        src = (ROOT / "judge" / "pipeline.py").read_text(encoding="utf-8")
        block = src[src.index("if on_result is not None:"):]
        block = block[:block.index("results.append(result)")]
        assert "result.extraction.input_tokens" in block
        assert "result.extraction.output_tokens" in block

    def test_a_thread_record_is_not_a_stage(self):
        """Fifteen stages a run, but twenty-five threads. Filing these as
        stages would bury the pipeline's shape in `E5 running` lines."""
        src = SCRIPT.read_text(encoding="utf-8")
        assert '{"kind": "thread", "at": _now(), **fields}' in src
