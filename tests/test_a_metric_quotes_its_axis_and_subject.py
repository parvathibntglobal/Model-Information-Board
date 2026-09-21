"""Can a metric figure quote the axis it belongs to and the model it is about?

⚠ MEASURED, NOT ENFORCED, AND THAT IS THE POINT OF THIS ROUND. #368 reports nine
  benchmarks sitting under one `swe-bench` slug and one model collecting eight
  figures that were not its own. The proposed repair (#370) is to make the
  extractor COPY both out of the evidence, so code can check them the way it
  already checks the figure.

  Whether that works is a question about the extractor, and it costs a fetch run
  to answer. So this round asks and counts; it refuses nothing, stores nothing,
  and needs no migration. Gating on a signal nobody has measured is rule 8 read
  backwards.

⚠ THREE STATES, NOT TWO (rule 6). A quote naming no benchmark is evidence with no
  axis in it. A quote naming one that is not in the text is a fabrication. Only
  the second is a defect, and collapsing them would hide it inside the first.
"""

from __future__ import annotations

from judge.store.board_entries import quoted_support, support_tally

QUOTE = "On DeepSWE v1.1 its 71.0% trails both Opus 5 (74.0%) and GPT-5.6 Sol"


def metric(**kw):
    return {"section": "metric", "quote": QUOTE, **kw}


class TestTheThreeStates:
    def test_a_name_copied_from_the_quote_is_quoted(self):
        assert quoted_support(metric(
            axis_verbatim="DeepSWE v1.1", subject_verbatim="Opus 5",
        )) == {"axis": "quoted", "subject": "quoted"}

    def test_nothing_offered_is_absent_not_wrong(self):
        """⚠ RULE 6. A quote with no benchmark in it is a fact about the
        evidence. Reporting it as a failure would make "we could not find one"
        indistinguishable from "one was invented"."""
        assert quoted_support(metric()) == {"axis": "absent", "subject": "absent"}
        assert quoted_support(metric(axis_verbatim="", subject_verbatim="   ")) == {
            "axis": "absent", "subject": "absent",
        }

    def test_a_name_that_is_not_in_the_quote_is_unsupported(self):
        """The defect #368 reports, caught at the source rather than on a page.

        `SWE-bench Verified` here is exactly the substitution that put a
        Terminal-bench figure on the SWE-bench page — the better-known benchmark
        the extractor thought was meant.
        """
        assert quoted_support(metric(
            axis_verbatim="SWE-bench Verified",
            subject_verbatim="Gemini 3.8 Flash",
        )) == {"axis": "unsupported", "subject": "unsupported"}

    def test_the_two_are_judged_independently(self):
        """A real row can quote its model and invent its axis. One verdict for
        both would report whichever was checked first."""
        assert quoted_support(metric(
            axis_verbatim="SWE-bench Verified", subject_verbatim="Opus 5",
        )) == {"axis": "unsupported", "subject": "quoted"}


class TestHowTheComparisonIsMade:
    def test_case_does_not_decide_it(self):
        """The text writes `DeepSWE v1.1` and a writer may type `deepswe v1.1`.
        A case difference is not a different benchmark."""
        assert quoted_support(metric(axis_verbatim="deepswe V1.1"))["axis"] == "quoted"

    def test_a_wrapped_quote_still_holds_its_name(self):
        """A flattened thread wraps mid-phrase. Whitespace-insensitive on both
        sides, or every two-word axis would read as unsupported for having a
        newline in it."""
        assert quoted_support({
            "section": "metric",
            "quote": "measured on\nTerminal-bench   4.0\nit reached 19.1%",
            "axis_verbatim": "Terminal-bench 4.0",
        })["axis"] == "quoted"

    def test_a_substring_of_a_longer_name_still_counts(self):
        """`SWE-bench` inside `SWE-bench Verified` is not a fabrication — it is
        a less specific copy of text that is there. Refusing it would push the
        extractor towards inventing precision it cannot see."""
        assert quoted_support({
            "section": "metric",
            "quote": "scores 71% on SWE-bench Verified",
            "axis_verbatim": "SWE-bench",
        })["axis"] == "quoted"


class TestTheTally:
    def test_it_counts_only_metrics(self):
        """A capability entry has no axis and no subject to quote. Counting it
        would put a denominator on the page that the numerator is not from."""
        tally = support_tally([
            metric(axis_verbatim="DeepSWE v1.1"),
            {"section": "capability", "quote": QUOTE},
            {"section": "best_for", "quote": QUOTE},
        ])
        assert tally["metrics"] == 1
        assert tally["axis_quoted"] == 1

    def test_every_metric_lands_in_exactly_one_bucket_per_property(self):
        """⚠ RULE 7. The buckets must sum to the denominator, or the stage line
        reports counts out of a total that does not contain them."""
        entries = [
            metric(axis_verbatim="DeepSWE v1.1", subject_verbatim="Opus 5"),
            metric(axis_verbatim="SWE-bench Verified"),
            metric(),
            metric(subject_verbatim="GPT-5.6 Sol"),
        ]
        t = support_tally(entries)
        assert t["metrics"] == 4
        assert t["axis_quoted"] + t["axis_absent"] + t["axis_unsupported"] == 4
        assert (t["subject_quoted"] + t["subject_absent"]
                + t["subject_unsupported"]) == 4

    def test_an_empty_batch_reports_zero_rather_than_nothing(self):
        """A run with no metrics prints no stage line, and the tally it would
        have printed is still well-formed — so a caller reading `metrics` does
        not have to guard against a missing key."""
        assert support_tally([])["metrics"] == 0


class TestItChangesNothingThatIsStored:
    def test_the_verdict_is_derived_and_never_written(self):
        """Nothing here touches the entry. `board_entry` has no column for
        either field, and this round deliberately does not add one — the
        migration is proposed in #370 and not assumed by building against it."""
        entry = metric(axis_verbatim="DeepSWE v1.1")
        before = dict(entry)
        quoted_support(entry)
        support_tally([entry])
        assert entry == before


class TestTheVerifiedAxisBecomesTheGroupingKey:
    """⚠ NO MIGRATION WAS NEEDED, AND THAT IS THE FINDING.

    The repair looked blocked on a new column. It was not: the grouping key a
    metric page uses is `slug`, and that column already existed. The defect was
    that the slug came from the extractor NAMING an axis instead of COPYING
    one — so nine benchmarks reduced to `swe-bench` and a page headed
    "SWE-bench Verified" rendered OSWorld and Terminal-bench side by side.

    Deriving the slug from `axis_verbatim` — and only when the quote contains
    it — makes the grouping inherit the check rather than the claim.
    """

    def test_a_verified_axis_makes_its_own_page(self):
        from judge.store.board_entries import axis_slug

        assert axis_slug({
            "section": "metric",
            "quote": "Terminal-bench 4.0 gives it 19.1% against Opus 5",
            "axis_verbatim": "Terminal-bench 4.0",
        }) == "terminal-bench-4-0"

    def test_the_nine_that_shared_one_slug_would_now_be_nine(self):
        """The exact set from #368, each landing somewhere different."""
        from judge.store.board_entries import axis_slug

        named = [
            "SWE-bench Verified", "SWE-Bench Pro", "Terminal-Bench 4.0",
            "AutomationBench", "CursorBench 3.2.0", "OSWorld-2.0",
            "DeepSWE v1.1",
        ]
        slugs = {
            axis_slug({
                "section": "metric",
                "quote": f"it scores 71% on {axis} in our run",
                "axis_verbatim": axis,
            })
            for axis in named
        }
        assert None not in slugs
        assert len(slugs) == len(named), f"two axes collapsed together: {slugs}"

    def test_an_axis_the_quote_does_not_contain_is_refused_not_filed(self):
        """⚠ Filing it under the name it invented IS the defect. This is the
        same reliability class as the figure check — plain substring against the
        quote, no coverage to be wrong about — which is what separates it from
        the alias-based gate that was built, measured and thrown away."""
        from judge.store.board_entries import axis_slug, metric_refusal

        entry = {
            "section": "metric", "value_verbatim": "43.5%",
            "quote": "the hard biology set from 43.5% to 56.5%",
            "axis_verbatim": "SWE-bench Verified",
        }
        assert metric_refusal(entry) == "axis not in its quote"
        assert axis_slug(entry) is None

    def test_a_metric_naming_no_axis_keeps_the_proposed_slug(self):
        """⚠ RULE 6. A quote with no benchmark in it is evidence with no axis,
        not a fabrication. Refusing it would delete a fact to enforce a rule
        about a different fact."""
        from judge.store.board_entries import axis_slug, metric_refusal

        entry = {
            "section": "metric", "slug": "context-window",
            "value_verbatim": "1M", "quote": "1M context",
        }
        assert metric_refusal(entry) is None
        assert axis_slug(entry) is None

    def test_a_capability_entry_never_has_its_slug_rewritten(self):
        from judge.store.board_entries import axis_slug

        assert axis_slug({
            "section": "capability", "slug": "tool-use",
            "quote": "Terminal-bench 4.0 gives it 19.1%",
            "axis_verbatim": "Terminal-bench 4.0",
        }) is None


class TestHowSpecificTheCopiedAxisWas:
    """⚠ THE MEASUREMENT #370 ASKED FOR, AND IT IS NOT A GATE.

    The substring rule is asymmetric. An axis MORE specific than the quote is
    `unsupported` — a fabrication. An axis LESS specific is `quoted`, because it
    is a true copy of text that is really there. But the under-specific copy is
    the bucket-forming move: `SWE-bench` accepted for a quote about SWE-bench
    Verified files one measurement under a broader name, and nine of those is
    the page #368 is about.

    Whether `quoted` should require exactness is an open question. This counts
    the two cases so the answer comes from a run rather than from either side's
    intuition. A heuristic is acceptable here precisely because nothing is gated
    on it — rule 8's "weight, not gate", used as intended for once.
    """

    def _entry(self, axis, quote):
        return {"section": "metric", "quote": quote, "axis_verbatim": axis}

    def test_a_whole_name_reads_exact(self):
        from judge.store.board_entries import axis_specificity

        assert axis_specificity(self._entry(
            "Terminal-bench 4.0", "Terminal-bench 4.0 gives it 19.1% against Opus 5",
        )) == "exact"

    def test_a_prefix_of_a_longer_name_reads_partial(self):
        """The case that motivated the question: a true copy, filed broader than
        the evidence it came from."""
        from judge.store.board_entries import axis_specificity

        assert axis_specificity(self._entry(
            "SWE-bench", "it scores 71% on SWE-bench Verified in our run",
        )) == "partial"

    def test_a_version_suffix_counts_as_the_name_continuing(self):
        """`DeepSWE` against `DeepSWE v1.1` is the same move as dropping
        `Verified` — a version is part of which benchmark was run."""
        from judge.store.board_entries import axis_specificity

        assert axis_specificity(self._entry(
            "DeepSWE", "On DeepSWE v1.1 its 71.0% trails Opus 5",
        )) == "partial"

    def test_lowercase_prose_after_the_name_means_it_ended(self):
        from judge.store.board_entries import axis_specificity

        assert axis_specificity(self._entry(
            "OSWorld-2.0", "On the OSWorld-2.0 computer use suite it is 59.0%",
        )) == "exact"

    def test_there_is_nothing_to_judge_without_a_verified_axis(self):
        from judge.store.board_entries import axis_specificity

        assert axis_specificity(self._entry(None, "1M context")) is None
        assert axis_specificity(self._entry(
            "SWE-bench Verified", "the hard biology set from 43.5% to 56.5%",
        )) is None

    def test_the_split_sums_to_the_quoted_count(self):
        """⚠ A BREAKDOWN, NOT A FOURTH STATE. The three states were agreed on
        #370; these partition one of them. If they stopped summing, the stage
        line would report parts that do not belong to the whole beside them."""
        from judge.store.board_entries import support_tally

        t = support_tally([
            self._entry("Terminal-bench 4.0", "Terminal-bench 4.0 gives 19.1%")
            | {"value_verbatim": "19.1%"},
            self._entry("SWE-bench", "71% on SWE-bench Verified in our run")
            | {"value_verbatim": "71%"},
            self._entry("SWE-bench Verified", "the hard biology set 43.5%")
            | {"value_verbatim": "43.5%"},
            self._entry(None, "1M context") | {"value_verbatim": "1M"},
        ])
        assert t["axis_exact"] + t["axis_partial"] == t["axis_quoted"]
        assert t["axis_exact"] == 1
        assert t["axis_partial"] == 1
