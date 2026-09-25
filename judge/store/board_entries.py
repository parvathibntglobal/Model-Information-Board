"""Persist what the classifier discovered, and serve the Board page from it.

The classifier NAMES a job, a capability or a metric; nothing here decides one.
Rows land in `board_entry` and the Board page groups them by slug. There is no
publication gate, deliberately — see the table comment. `cell` publishes a
verdict and is gated; these three sections are observations, and gating them
behind four agreeing voices would leave the board empty while the evidence sat
in the database.

WHAT THIS MODULE IS ACTUALLY FOR, beyond the INSERT
---------------------------------------------------
An open vocabulary trades gaps for DUPLICATES: "function calling" and "tool
calling" from two threads are one section under two names. Two things narrow
that, and neither is a model deciding anything.

  `normalise_slug`   mechanical only. Case, spacing, punctuation, a leading
                     `job.`/`metric.` prefix if the model emitted one. It cannot
                     tell that two different WORDS mean one thing, and it does
                     not try — guessing that would be the LLM's judgement moved
                     into code, which is the same mistake wearing a hat.

  `ruling`           a person folds one slug into another (`merged` +
                     `ruling_target`), through the same shape
                     `capability_candidate` already uses. That is the only place
                     a synonym is resolved.

IDEMPOTENT, and that is the report count's integrity. `id` is the content hash
of the natural key (document, section, slug, quote, pipeline_version), written
`ON CONFLICT DO NOTHING`, so re-classifying the same corpus cannot inflate the
number of reports the page shows.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from typing import Any

from judge.store.claims import PIPELINE_VERSION

SECTIONS = ("best_for", "capability", "metric")

#: Anything that is not a letter, a digit or a hyphen becomes a hyphen.
_NON_SLUG = re.compile(r"[^a-z0-9]+")
#: A prefix the classifier is told not to emit but might: `job.rag` -> `rag`.
_PREFIX = re.compile(r"^(job|metric|capability|cap)[._-]")


def normalise_slug(raw: str) -> str:
    """Mechanical slug normalisation. NO synonym resolution.

    `Function Calling`, `function calling` and `function_calling` are one slug.
    `tool-calling` is NOT folded into `function-calling` here, however obvious
    that looks: a synonym table in code is a judgement about meaning, and the
    moment it is wrong it silently merges two genuinely different sections. That
    call belongs to a person, through `ruling`.
    """
    slug = _NON_SLUG.sub("-", raw.strip().casefold()).strip("-")
    slug = _PREFIX.sub("", slug)
    return slug.strip("-")


def entry_id(
    *, document_id: str, section: str, slug: str, quote: str, pipeline_version: str
) -> str:
    """Content hash of the natural key, so a re-run produces the same id."""
    digest = hashlib.sha256(
        "\x1f".join([document_id, section, slug, quote, pipeline_version]).encode("utf-8")
    ).hexdigest()
    return f"be_{digest[:24]}"


def _scope_of(entry: dict, searched: frozenset[str]) -> str | None:
    """`searched` | `mentioned` | None, for one entry.

    None WHEN THE CALLER DID NOT SAY. A run that does not pass its own
    subject cannot have its rows labelled, and defaulting them to
    `mentioned` would assert a population nobody recorded - the same
    shape as reading an absent flag as `false` (rule 6). The column is
    nullable for exactly this.

    `searched` IS A SET OF IDS, NOT ONE, and that is load-bearing. The
    column it compares holds BOTH shapes for the same model - the
    canonical id when a run names its own subject, the internal `mv_`
    key when the entry was resolved out of the text through
    `model_alias`. Comparing against a single form would label the
    searched model's own rows `mentioned` whenever they happened to
    arrive by the other route, which is the failure this column exists
    to end rather than reproduce.

    An explicit `model_scope` on the entry wins, so a caller that
    already knows is never second-guessed.
    """
    given = entry.get("model_scope")
    if given in ("searched", "mentioned"):
        return given
    if not searched:
        return None
    mv = entry.get("model_version_id")
    if not mv:
        return None
    return "searched" if mv in searched else "mentioned"


#: A quantity is a digit the value LEADS WITH. `43.5%`, `84 tasks`,
#: `$0.50 / 1M`, `2.3x`, `200K`, `#23`, `~40 minutes` all do; "twice as
#: expensive", "slowest", "one or two euros" and "volume" do not.
#:
#: ⚠ THIS CLOSES ONE OF RULE 12's TWO NAMED INSTANCES. It was
#:   `re.compile(r"\d")` - *is there a digit anywhere?* - which is a test
#:   almost nothing fails, because every modern model name carries one. On
#:   2026-09-21 it published `'matches or trails Claude Fable 5 and GPT 5.6
#:   Sol'` as a measurement; the digits it found were `['5','5','6']`, from
#:   **Fable 5** and **GPT 5.6**. Wrong since written, visible only when a
#:   value arrived whose sole digits were a version number (#386 item 3).
#:
#: NOT PATCHED WITH A LONGER WORD LIST, deliberately: `_RELATIVE_CLAIM`
#: missing "trails" is the same shape as `SUBAXIS` missing "batch pricing",
#: and a fixed vocabulary guessing what writers will say is what #386 is
#: about.
#:
#: MEASURED BEFORE CHANGING IT, over all 496 stored metric rows at the time.
#: The reported row was one of FIVE of its own kind, not a one-off:
#:
#:     matches or trails Claude Fable 5 and GPT 5.6 Sol   model versions
#:     outperforms DeepSeek V4 Pro across the board       model version
#:     same as it was for 3.7 Flash                       model version
#:     p99 stays flat even under burst load               a percentile name
#:     more than 10x the token adjusted price             relative claim
#:     September 1, 2026  /  June 2026                    dates, not figures
#:
#:   Seven newly refused of the 452 that passed, and no legitimate figure
#:   among the other 445 moves - `1.000`, `300ms`, `51`, `200K`, `6/24`,
#:   `82% vs 78% vs 74%` and `$2 per million input tokens and $10 per million
#:   output tokens` all lead with their number and all still pass.
#:
#: WHY LEADING RATHER THAN ANCHORED TO THE UNIT, which was tried first and is
#: the more obvious idea: anchoring a digit to the row's own `unit` refuses
#: 145 of 452, because a bare `51` under `unit: score` is exactly right - the
#: unit lives in its own column so the value need not repeat it. Measured, not
#: reasoned; the obvious rule was 20x worse.
#:
#: The hedge list is about LEAD-INS ("about 13 AIC per task"), not the domain,
#: which is what keeps this from being the vocabulary guess #386 argues
#: against - it decides nothing about which units or comparatives are real.
_LEADING_QUANTITY = re.compile(
    r"^\s*(?:[~<>≈#±+\-]|\(|\"|')*\s*"
    r"(?:about|approx\.?|approximately|roughly|around|nearly|over|under|"
    r"up\s+to|just)?\s*"
    r"(?:[$€£¥₹]\s*)?\d",
    re.IGNORECASE,
)


#: What a benchmark name looks like when it CONTINUES past where the extractor
#: stopped copying: a capitalised word (`Verified`, `Pro`) or a version token
#: (`4.0`, `v1.1`). Lowercase prose after the match means the name ended there.
_NAME_CONTINUES = re.compile(r"^\s+(?:[A-Z][\w.-]*|v?\d[\w.]*)")


def axis_specificity(entry: dict) -> str | None:
    """Did the extractor copy the WHOLE axis name, or a prefix of it?

    ⚠ ASKED FOR BY @anoojntglobal-sudo ON #370, AND IT IS THE RIGHT QUESTION.
      The substring rule is asymmetric and only one direction is open:

          axis 'SWE-bench Verified'  quote '…SWE-bench…'           -> unsupported
          axis 'SWE-bench'           quote '…SWE-bench Verified…'  -> quoted

      The second is a true copy of text that is really there, so it is not a
      fabrication. But it is LESS SPECIFIC than the evidence it is filed
      against, and that is the bucket-forming move: `SWE-bench` accepted for a
      quote about SWE-bench Verified is one measurement filed under a broader
      name, and nine of those is the page #368 is about.

    ⚠ A HEURISTIC, AND REPORTED AS ONE. This cannot know where a benchmark's
      name ends; it asks whether the text immediately after the copy looks like
      the name continuing. Good enough to COUNT with, which is all it is for -
      nothing is gated on it, and the number is what decides whether `quoted`
      should require exactness at all.

          exact    'Terminal-bench 4.0' then ' gives it 19.1%'   -> name ended
          partial  'SWE-bench' then ' Verified in our run'       -> name went on
          partial  'DeepSWE' then ' v1.1 trails'                 -> name went on

    Returns None when there is no verified axis to judge.
    """
    if quoted_support(entry)["axis"] != "quoted":
        return None
    quote = " ".join((entry.get("quote") or "").split())
    axis = " ".join((entry.get("axis_verbatim") or "").split())
    at = quote.casefold().find(axis.casefold())
    if at < 0:
        return None
    return "partial" if _NAME_CONTINUES.match(quote[at + len(axis):]) else "exact"


def quoted_support(entry: dict) -> dict[str, str]:
    """Which of a metric's four properties its own quote actually supports.

    Returns a verdict per property. MEASURED, NOT ENFORCED — this is reported
    and nothing is refused on it, because what it is measuring is whether the
    extractor can be made to quote its axis and its subject at all. Shipping it
    as a gate before that is known would be rule 8 exactly: an unmeasured check
    used as a gate.

    ⚠ THE TWO NEW PROPERTIES ARE CHECKED THE SAME WAY THE FIGURE IS, and that
      similarity is the whole design. `value_verbatim` is trustworthy because
      code compares the copy against the text — not because its instruction is
      emphatic, which it already was while 10% of figures were not in their
      quote. `axis_verbatim` and `subject_verbatim` earn the same standing or
      none.

    ⚠ ABSENT IS NOT WRONG, AND THE THREE STATES ARE KEPT APART (rule 6). A quote
      naming no benchmark is evidence with no axis in it; a quote naming one
      that is not in the text is a fabrication. Collapsing them into "invalid"
      would hide the second inside the first, and only the second is a defect.

        `quoted`      the value is in the quote, character for character
        `absent`      the extractor left it empty; the quote names none
        `unsupported` it named one and the quote does not contain it
    """
    def _state(value: str | None) -> str:
        text = (value or "").strip()
        if not text:
            return "absent"
        haystack = " ".join((entry.get("quote") or "").split()).casefold()
        return "quoted" if " ".join(text.split()).casefold() in haystack else "unsupported"

    return {
        "axis": _state(entry.get("axis_verbatim")),
        "subject": _state(entry.get("subject_verbatim")),
    }


def axis_slug(entry: dict) -> str | None:
    """The slug a metric should group under, derived from its verified axis.

    ⚠ NO MIGRATION IS NEEDED FOR THIS, WHICH IS THE WHOLE REASON IT CAN SHIP NOW.
      The grouping key a metric page uses is `slug`, and that column already
      exists. The defect was never a missing column — it was that the slug came
      from the extractor NAMING an axis instead of COPYING one, so nine
      benchmarks reduced to `swe-bench` and a page headed "SWE-bench Verified"
      rendered OSWorld and Terminal-bench figures side by side (#368).

      Derived from `axis_verbatim` only when that name was found in the quote,
      so the grouping inherits the check rather than the claim:

          "Terminal-bench 4.0"  ->  terminal-bench-4-0
          "SWE-bench Verified"  ->  swe-bench-verified
          "OSWorld-2.0"         ->  osworld-2-0

      Three axes, three pages, none of them pretending to be the others.

    ⚠ FRAGMENTATION IS THE COST AND IT IS THE RIGHT ONE. "Terminal-bench 4.0"
      and "Terminal-bench 4" become two slugs, because two writers wrote two
      things. That is a merge a person makes on the board review, which exists
      for exactly this - and it is the opposite failure from the current one:
      two pages that should be one is a tidying job, one page that should be
      nine is a wrong number in front of a reader.

    Returns None when there is nothing verified to derive from, and the caller
    keeps whatever the extractor proposed.
    """
    if entry.get("section") != "metric":
        return None
    if quoted_support(entry)["axis"] != "quoted":
        return None
    return normalise_slug(entry.get("axis_verbatim") or "") or None


def support_samples(entries: list[dict], *, limit: int = 4) -> list[dict]:
    """The actual figures behind the counts, so a reader can check the checker.

    ⚠ A COUNT CANNOT BE VERIFIED, WHICH IS THE WHOLE PROBLEM THIS ROUND IS ABOUT.
      "7 quoted, 1 unsupported" asks you to trust exactly the thing under test.
      Nothing new is stored this round, so the metric pages will look identical
      after a run — leaving the counts as the only evidence, and a count is not
      evidence about itself.

      So each verdict carries its figure, the name the extractor gave, and the
      quote it was checked against. `unsupported` first, because that is the
      defect #368 reports and the one worth reading in full.

    ⚠ THIS IS TELEMETRY, NOT BOARD DATA. It rides in the run's stage record —
      the same place every other stage line goes — and touches no board table.
      `board_entry` gains nothing and loses nothing.
    """
    ranked: list[tuple[int, dict]] = []
    for entry in entries:
        if entry.get("section") != "metric":
            continue
        verdict = quoted_support(entry)
        for prop in ("axis", "subject"):
            state = verdict[prop]
            if state == "absent":
                continue  # nothing was claimed; there is nothing to show
            ranked.append((
                0 if state == "unsupported" else 1,
                {
                    "property": prop,
                    "state": state,
                    "claimed": entry.get(f"{prop}_verbatim"),
                    "figure": entry.get("value_verbatim"),
                    "slug": entry.get("slug"),
                    # Trimmed: a flattened thread quote can be long, and the
                    # point is whether the claimed name is in it.
                    "quote": " ".join((entry.get("quote") or "").split())[:180],
                },
            ))
    ranked.sort(key=lambda pair: pair[0])
    return [item for _, item in ranked[:limit]]


def support_tally(entries: list[dict]) -> dict[str, int]:
    """Counts across a batch, for the stage line a fetch prints.

    ⚠ RULE 7. Reported as counts out of the metrics in the batch, never as a
      bare percentage — "82% quoted" over eleven figures is a different fact
      from the same number over four hundred, and the run that prints it is the
      only place the denominator is known.
    """
    out = {
        "metrics": 0,
        "axis_quoted": 0, "axis_absent": 0, "axis_unsupported": 0,
        # THE SPLIT WITHIN `quoted`, which #370 asked for. These sum to
        # `axis_quoted`; they are a breakdown of it, not a fourth state, because
        # the three states were agreed and this does not disturb them.
        "axis_exact": 0, "axis_partial": 0,
        "subject_quoted": 0, "subject_absent": 0, "subject_unsupported": 0,
    }
    for entry in entries:
        if entry.get("section") != "metric":
            continue
        out["metrics"] += 1
        verdict = quoted_support(entry)
        out[f"axis_{verdict['axis']}"] += 1
        out[f"subject_{verdict['subject']}"] += 1
        precision = axis_specificity(entry)
        if precision:
            out[f"axis_{precision}"] += 1
    return out


#: ── EVERY REASON A FIGURE IS KEPT OFF A PAGE, AND WHAT EACH ONE MEANS ──────
#:
#: ⚠ ONE SOURCE, BECAUSE THE SECOND ONE WOULD BE A TRANSCRIPTION. The gates
#:   below return these constants and `/admin/stages` renders this tuple, so a
#:   reason added to the code appears on the page and a reason removed from the
#:   code cannot linger there. The alternative - a list of gates written out on
#:   the page - is a count in prose with extra steps (rule 11): true the day it
#:   is pasted, quietly wrong afterwards, and misleading exactly the person who
#:   went looking for what the pipeline currently refuses.
#:
#: ⚠ RULE 4 IS WHY THIS IS SHOWN AT ALL. Every one of these CAUSES AN ABSENCE.
#:   A metrics tab that is thin because eleven figures were withheld and one
#:   that is thin because nobody ever measured the model render identically,
#:   and they are opposite statements. Naming the gates does not fix that on its
#:   own, but a reader who cannot find out that a gate exists has no way to ask.
#:
#: `when` separates the two questions this module asks, which are not the same
#: question asked twice:
#:   write  `metric_refusal` - may this row be STORED as a figure at all
#:   read   `metric_withholding` - may this stored row be SHOWN on a page
GATE_NO_QUANTITY = "no quantity"
GATE_FIGURE_NOT_IN_QUOTE = "figure not in its quote"
GATE_AXIS_NOT_IN_QUOTE = "axis not in its quote"
GATE_RELATIVE_CLAIM = "a relative claim, not a value on this axis"
GATE_UNIT_SAYS_MONEY = "the unit says money and the value carries no amount"
#: A TEMPLATE, not a fixed string - the two families are filled in at the point
#: of refusal so the reason names the actual disagreement rather than its shape.
GATE_TIME_UNIT_DISAGREES = (
    "the unit says {declared}s and the figure is written in {written}s"
)
GATE_PER_SECOND_NOT_PER_TASK = (
    "the unit is per second and the figure is per something else"
)
GATE_COST_WITHOUT_MONEY = "the axis is a cost and the unit is not money"

METRIC_GATES: tuple[dict[str, str], ...] = (
    {
        "reason": GATE_NO_QUANTITY,
        "when": "write",
        "means": (
            "The figure column holds no digits. \"twice as expensive\", "
            "\"slowest\", \"Blazing Fast\" are real things somebody said and "
            "they belong in a capability entry; under a heading reading "
            "MILLISECONDS they are a measurement the board never took."
        ),
    },
    {
        "reason": GATE_FIGURE_NOT_IN_QUOTE,
        "when": "write",
        "means": (
            "The figure does not appear in the quote offered as its evidence. "
            "It may be correct and taken from a table two paragraphs away, and "
            "nothing here can tell that from an invention - so it is refused "
            "rather than stored on the reading that happens to be convenient."
        ),
    },
    {
        "reason": GATE_AXIS_NOT_IN_QUOTE,
        "when": "write",
        "means": (
            "The benchmark name does not appear in the quote. This is the "
            "substitution that put a Terminal-bench figure on the SWE-bench "
            "page. An axis left EMPTY is not refused - a quote naming no "
            "benchmark is evidence with no axis in it."
        ),
    },
    {
        "reason": GATE_RELATIVE_CLAIM,
        "when": "read",
        "means": (
            "\"3x cheaper\", \"70% lower cost\" measure the GAP TO ANOTHER "
            "MODEL rather than the axis the column is headed with. In a column "
            "reading USD PER 1M TOKENS, \"70% lower cost\" is not an imprecise "
            "price - it is not a price. Approximation is not comparison: "
            "\"~60 tokens/second\" is a reading somebody rounded, and stays."
        ),
    },
    {
        "reason": GATE_UNIT_SAYS_MONEY,
        "when": "read",
        "means": (
            "A row reading `80%` under `USD per 1M tokens`, from \"GPT-5.6 "
            "costs drop 80%\" - real, in its quote, and not money. A unit that "
            "says the figure is a SHARE is exempt: a price quoted as a "
            "fraction of another price is still a price."
        ),
    },
    {
        # ⚠ THE ONLY REASON THAT IS A TEMPLATE, so it is the only one that
        #   needs a name of its own. Rendering the raw string put
        #   `{declared}s` and `{written}s` on the page, which reads as a bug
        #   in the very list that exists to explain the pipeline.
        "reason": GATE_TIME_UNIT_DISAGREES,
        "shows_as": "the unit and the figure name different durations",
        "when": "read",
        "means": (
            "The declared unit and the figure name different durations - "
            "`about 75 minutes` stored as MILLISECONDS, so a task that took "
            "three quarters of an hour rendered beside figures around 300ms. "
            "Both sides must name a time before this says anything: a bare "
            "`280` under milliseconds is not checked."
        ),
    },
    {
        "reason": GATE_PER_SECOND_NOT_PER_TASK,
        "when": "read",
        "means": (
            "`118K per task` stored as tokens-per-second. Both are rates, so "
            "the vocabulary matched and the denominator did not."
        ),
    },
    {
        "reason": GATE_COST_WITHOUT_MONEY,
        "when": "read",
        "means": (
            "`cost-per-token` holding `10.59M tokens` in a unit of `tokens`. "
            "The value agrees with the unit perfectly and neither is a price - "
            "only the AXIS NAME disagrees, so only a slug-against-unit check "
            "finds it."
        ),
    },
)


def metric_refusal(entry: dict) -> str | None:
    """Why this metric may not be stored as a figure, or None.

    ⚠ TWO CHECKS, BOTH FOUND BY READING A PAGE THAT WAS CONFIDENTLY WRONG.
      The SWE-bench page showed Gemini 3.8 Flash eight times with figures from
      OSWorld-2.0, Terminal-bench, DeepSWE and a biology set (#368). Two of the
      five defects behind it are mechanical, and these are they.

    1 · THE FIGURE MUST BE IN ITS OWN QUOTE. `quote_verified` already checks
        that the QUOTE is in the document - `runner.py:383`, `p.quote in
        thread.flattened_text` - and that is a statement about provenance which
        says nothing about support. It let this through:

            61.4%  <-  "It tops the chart on finance, legal, long video and
                        chart reasoning"

        No digits at all. The figure came from elsewhere in the document, and
        rule 1 was broken at the source while a check named for rule 1 passed.

        It also catches a range split into its endpoints: "Terminal-bench 4.0
        from 11.2% to 19.1%" survives as `11.2%` because 11.2% IS in the quote,
        so this does not fix defect 2 - but a value invented near a quote can no
        longer pass as one taken from it.

    2 · A METRIC VALUE WITH NO QUANTITY IS NOT A METRIC. 43 of 440 stored
        figures carry no digit: "twice as expensive", "slowest", "one or two
        euros". Those are real things somebody said and they belong in a
        capability or a best-for entry; rendered in a column headed FIGURE with
        a unit beside them they are a measurement the board never took.

    ⚠ THIS REFUSES RATHER THAN REPAIRS. A figure that cannot be found in its
      quote might be correct and taken from a table two paragraphs away - but
      nothing here can tell that from an invention, and storing it would assert
      the reading that happens to be convenient (rule 6). The refusal is counted
      and named, so a rise in one shape is visible rather than silent.
    """
    if entry.get("section") != "metric":
        return None
    value = (entry.get("value_verbatim") or "").strip()
    if not value:
        # A metric with no figure is not refused here. It is a section entry
        # about a metric - "they publish latency numbers" - and the page can
        # show it as evidence without showing it as a measurement.
        return None
    if not _LEADING_QUANTITY.match(value):
        return GATE_NO_QUANTITY
    # Whitespace-insensitive, because a quote crossing a line break renders the
    # figure with a newline in it and that is not a different figure.
    haystack = " ".join((entry.get("quote") or "").split())
    needle = " ".join(value.split())
    if needle not in haystack:
        return GATE_FIGURE_NOT_IN_QUOTE
    # ⚠ THE THIRD REFUSAL, AND IT IS THE SAME RELIABILITY CLASS AS THE SECOND.
    #   An axis the extractor named and the quote does not contain is a
    #   fabricated axis - exactly the substitution that put a Terminal-bench
    #   figure on the SWE-bench page. Refused rather than filed under the name
    #   it invented, because filing it IS the defect.
    #
    #   This is a plain substring check against the quote, like the figure check
    #   above it. It has no coverage problem to be unreliable about, which is
    #   what separates it from the alias-based misattribution gate that was
    #   built, measured against real rows, and thrown away for exactly that.
    #
    #   An axis left EMPTY is not refused. A quote naming no benchmark is
    #   evidence with no axis in it, and refusing it would delete a fact to
    #   enforce a rule about a different one (rule 6).
    if quoted_support(entry)["axis"] == "unsupported":
        return GATE_AXIS_NOT_IN_QUOTE
    return None


def store_entries(
    conn: Any,
    entries: list[dict],
    *,
    proposer_model: str,
    searched_model_version_id: str | Iterable[str] | None = None,
    pipeline_version: str = PIPELINE_VERSION,
) -> dict[str, int]:
    """Append discovered entries. Returns {proposed, stored, skipped_unverified}.

    Each dict carries: section, slug, name, definition, document_id, quote,
    quote_verified, polarity, and optionally model_version_id, claim_id, and
    unit/value_verbatim/basis for a metric.

    AN UNVERIFIED QUOTE IS NOT STORED, and it is counted rather than dropped
    quietly. The table CHECKs `quote_verified = true`, so passing one would
    raise and take the whole batch with it; refusing it here keeps the rest of
    the batch and still reports that it happened. Rule 1 has no exception for a
    new table, and rule 4 says the refusal must be visible.
    """
    # ONE ID OR SEVERAL, normalised once. A caller knowing only the
    # canonical id may pass a string; one that has resolved both shapes
    # should pass both, and more forms can only make the match better.
    if searched_model_version_id is None:
        searched: frozenset[str] = frozenset()
    elif isinstance(searched_model_version_id, str):
        searched = frozenset({searched_model_version_id})
    else:
        searched = frozenset(x for x in searched_model_version_id if x)

    proposed = len(entries)
    stored = 0
    skipped = 0
    # ⚠ COUNTED BY REASON, NOT TOTALLED. "12 refused" sends a reader to the
    # prompt; "11 with no quantity, 1 whose figure is not in its quote" sends
    # them to two different places, and only one of them is the prompt.
    refused: dict[str, int] = {}
    with conn.cursor() as cur:
        for e in entries:
            if not e.get("quote_verified"):
                skipped += 1
                continue
            why = metric_refusal(e)
            if why is not None:
                refused[why] = refused.get(why, 0) + 1
                continue
            section = e["section"]
            if section not in SECTIONS:
                raise ValueError(
                    f"unknown board section {section!r}: the three sections are "
                    f"{SECTIONS}. A new section is a product decision, not a "
                    "value the classifier may invent - unlike the slug, which it "
                    "may."
                )
            # THE VERIFIED AXIS WINS OVER THE PROPOSED SLUG. `axis_slug`
            # returns None unless the extractor copied a name that is really in
            # the quote, so an unverified metric and every non-metric keep
            # whatever was proposed.
            slug = axis_slug(e) or normalise_slug(e["slug"])
            if not slug:
                skipped += 1
                continue
            cur.execute(
                "INSERT INTO board_entry "
                "(id, section, slug, name, definition, unit, value_verbatim, basis,"
                " model_version_id, document_id, claim_id, quote, quote_verified,"
                " polarity, proposer_model, model_scope, pipeline_version) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (id) DO NOTHING",
                (
                    entry_id(
                        document_id=e["document_id"], section=section, slug=slug,
                        quote=e["quote"], pipeline_version=pipeline_version,
                    ),
                    section, slug, e["name"], e["definition"],
                    e.get("unit"), e.get("value_verbatim"), e.get("basis"),
                    e.get("model_version_id"), e["document_id"], e.get("claim_id"),
                    e["quote"], True, e["polarity"], proposer_model,
                    _scope_of(e, searched),
                    pipeline_version,
                ),
            )
            stored += cur.rowcount  # 1 on insert, 0 on conflict
    return {
        "proposed": proposed,
        "stored": stored,
        "skipped_unverified": skipped,
        "refused_metrics": sum(refused.values()),
        "refused_by": refused,
    }


# ── the Board page read ──────────────────────────────────────────────────────


#: ── WHICH STORED METRIC FIGURES MAY BE SHOWN ────────────────────────────────
#:
#: THIS REPLACED A DATE, AND THE DATE WAS THE WRONG SHAPE. The first version of
#: this withheld every metric row written before a cutoff, on the reasoning that
#: a row recorded after the checks existed had been through them. That is a
#: proxy for the property nobody recorded, and it has two failures a proxy
#: always has: it hides 269 sound figures because of WHEN they were written, and
#: it would publish an unchecked one written tomorrow by an extractor that never
#: ran the checks. Measured 2026-09-21, the date hid all 447.
#:
#: The gate below asks each row the question directly instead. Every input is a
#: column the row already carries, so this needs no migration and no
#: re-extraction - which is what @anoojntglobal-sudo's ruling on #379 asked for:
#: "No re-extraction, no deletion... The 440 keep their figures and stop
#: claiming to be verified."
#:
#: ⚠ NOTHING IS DELETED AND NOTHING IS REWRITTEN. This is a read filter. Every
#:   row stays exactly as stored, and a row that starts passing - because the
#:   axis work lands, or because a reviewer rules on it - appears with no
#:   migration.
#:
#: RULE 11: THIS IS A RECORD, NOT A DESCRIPTION OF NOW. It said `447 stored /
#: 269 shown` in the present tense when it landed at 10:15 on 2026-09-21, and
#: by 10:50 the database held 471 and showed 290 - a run wrote in between. The
#: ratio is the justification for withholding at all, so a reader checking
#: whether the trade is still fair needs to know this is a snapshot and go and
#: count. `board_sections` returns the live counts under `_withheld`.
#:
#: WAS, WHEN MEASURED ON 2026-09-21 AT 10:15, OVER 447 ROWS:
#:
#:     447  metric rows stored
#:      75  already declined by a reviewer (all 39 `swe-bench`, all 36
#:          `context-window` - the #368 page was withdrawn by hand already)
#:      82  refused by the two mechanical gates below
#:      21  refused as a relative claim or an incoherent unit
#:     ---
#:     269  shown
#:
#: ⚠ WHAT THIS DOES NOT FIX, STATED HERE BECAUSE THE NUMBER IS ON A PAGE.
#:   The slug is still INFERRED, not verified. Of the 113 `cost-per-token`
#:   figures that pass, only 4 quotes say "input" and 30 say "output"; 65 say
#:   neither and 9 are bare table rows. So that column mixes an input price with
#:   an output price and cannot currently tell them apart. That is #368's
#:   labelling defect surviving the gates, and it is what `axis_quoted` is for.
#:   These checks make a figure trustworthy AS A FIGURE; they do not make its
#:   heading trustworthy.


def metric_withholding(entry: dict) -> str | None:
    """Why this stored metric figure is not shown on a page, or None.

    A read-time question about a row that already exists, as against
    `metric_refusal`, which is a write-time question about a row being stored.
    The first two reasons ARE `metric_refusal`, so a row stored before those
    gates existed is now held to them; the rest are checks that only make sense
    once a row has both a value and a unit to disagree with each other.

    ⚠ THE LAST THREE WITHHOLD A LABEL, NOT A FIGURE, and that is the difference
      from every reason above them. `about 75 minutes` is a real duration
      somebody measured; what is wrong is the `milliseconds` beside it and the
      `time-to-first-token` above it. So the row comes back the moment either is
      corrected - nothing here proposes a deletion, and the evidence is intact
      for the reviewer who fixes the axis.

    RULE 8, MEASURED BEFORE THESE SHIPPED AS GATES. Run over every metric row in
    the shared database on 2026-09-22 - 519 rows, a population no filter here
    chose - `shown` went 402 -> 392. Eleven rows left it and all eleven are
    wrong rows: five token totals filed as `cost-per-token` from one recurring
    table shape ("90 tasks, 10.59M tokens, 118K per task, 10h 37m"), five task
    durations on the `time-to-first-token` page, and one per-task figure under
    tokens-per-second. One row came BACK - `cache-read-cost`, see the money
    check - and a twelfth was a false positive, fixed rather than tolerated, in
    `_time_families`.
    """
    if entry.get("section") != "metric":
        return None
    refused = metric_refusal(entry)
    if refused is not None:
        return refused

    value = (entry.get("value_verbatim") or "").strip()
    if not value:
        return None
    unit = (entry.get("unit") or "").lower()

    # ⚠ A RELATIVE CLAIM IS NOT A VALUE ON THIS AXIS. "3x cheaper", "70% lower
    #   cost", "~50x fewer FLOPs" are real things somebody measured, and every
    #   one of them measures the GAP TO ANOTHER MODEL rather than the axis the
    #   column is headed with. Rendered in a column reading USD PER 1M TOKENS,
    #   "70% lower cost" is not an imprecise price - it is not a price.
    #
    #   They belong in a capability entry, which is why this withholds the
    #   figure rather than proposing a deletion.
    if _RELATIVE_CLAIM.search(value):
        return GATE_RELATIVE_CLAIM

    # ⚠ AND THE UNIT HAS TO BE ABLE TO HOLD THE VALUE. A row reading `80%`
    #   under `USD per 1M tokens` came from "GPT-5.6 costs drop 80%" - the
    #   figure is real, in its quote, and is not money.
    #
    #   ⚠ UNLESS THE UNIT ITSELF SAYS THE FIGURE IS A SHARE, which this used to
    #     miss and it cost one row. `cache-read-cost` is declared in "percent of
    #     input cost", holding `2%` from "That 2% cache read really pays off" -
    #     a coherent reading on a real axis, withheld because the unit contains
    #     the word cost and the value contains no dollar sign. A price quoted as
    #     a fraction of another price is still a price. Measured over the 519
    #     stored figures: 3 rows were withheld here, 2 of them discounts under a
    #     currency unit and this one, which the reviewer who read it ruled sound.
    if (
        _MONEY_UNIT.search(unit)
        and not _RATIO_UNIT.search(unit)
        and not _CURRENCY.search(value)
    ):
        return GATE_UNIT_SAYS_MONEY

    # ⚠ AND A TIME UNIT HAS TO BE THE ONE THE FIGURE IS WRITTEN IN. Three
    #   rows read `about 40 minutes per task`, `about 75 minutes` and
    #   `8.566 seconds` under a declared unit of MILLISECONDS - so a task
    #   that took three quarters of an hour rendered on the
    #   time-to-first-token page next to figures around 300ms, where it is
    #   not an outlier but a different measurement.
    #
    #   Both sides have to name a time before this can say anything. A bare
    #   `280` under `milliseconds` is not checked, because the value names
    #   no unit to disagree with - that is rule 6, not a quiet pass.
    declared = _time_families(unit)
    written = _time_families(value)
    if declared and written and not (declared & written):
        return GATE_TIME_UNIT_DISAGREES.format(
            declared="/".join(sorted(declared)),
            written="/".join(sorted(written)),
        )

    # ⚠ A RATE PER SECOND IS NOT A RATE PER TASK. `118K per task` was stored
    #   as tokens-per-second, from a quote reading "90 tasks, 10.59M tokens,
    #   118K per task, 10h 37m": both are rates, so the vocabulary matched
    #   and the denominator did not. Rule 7 inside one cell - the figure is
    #   real and it answers a question nobody asked it.
    if _PER_SECOND_UNIT.search(unit) and _PER_SOMETHING_ELSE.search(value):
        return GATE_PER_SECOND_NOT_PER_TASK

    # ⚠ AN AXIS THAT PROMISES MONEY, DECLARED IN SOMETHING THAT IS NOT MONEY.
    #   The check above reads the unit against the value; this reads the SLUG
    #   against the unit, which is the only place `cost-per-token` holding
    #   `10.59M tokens` in a unit of `tokens` shows up: the value agrees with
    #   the unit perfectly, and neither is a cost. A total spend of tokens is
    #   not a price per token, and the column heading says it is.
    #
    #   A PERCENTAGE OF A PRICE IS STILL ABOUT PRICE, and `_MONEY_UNIT` reads
    #   the word cost inside "percent of input cost", so `cache-read-cost`
    #   passes here as an axis that IS declared in money.
    slug = entry.get("slug") or ""
    if _MONEY_SLUG.search(slug) and not _MONEY_UNIT.search(unit):
        return GATE_COST_WITHOUT_MONEY
    return None


#: ⚠ APPROXIMATION IS NOT COMPARISON, and conflating them deletes measurements.
#:   An earlier version of `_RELATIVE_CLAIM` also matched "about", "around" and
#:   "~", and refused 14 rows that are plain readings with a stated imprecision:
#:   `~60 tokens/second`, `~190 ms (streaming)`, `around $1.20`. Those are
#:   measurements somebody took and rounded. What is refused here is a value
#:   that only means anything NEXT TO ANOTHER MODEL - a comparative word, or a
#:   bare multiplier like `3x`.
_RELATIVE_CLAIM = re.compile(
    r"\b(less|more|lower|higher|cheaper|faster|slower|fewer|better|worse|"
    r"drop|reduction)\b|\d+\s*x\b",
    re.IGNORECASE,
)

#: Cents included, because `8.7¢ per task` is money and an earlier pass
#: refused it for not starting with a dollar sign.
_CURRENCY = re.compile(r"[$\u20ac\u00a3]\s*\d|\d\s*(?:\u00a2|cents?\b)", re.IGNORECASE)
#: `eur`/`gbp` because `cost-per-generation` is declared in EUR, and the slug
#: check below would otherwise read a euro price as not being money. `cent`
#: is deliberately absent: it sits inside "percent", which is a unit on 60
#: rows here and is not money.
_MONEY_UNIT = re.compile(r"usd|\$|cost|price|eur|gbp", re.IGNORECASE)

#: The slug side of the same question. Only the words that make a PRICE the
#: thing being measured - `token-cost` and `cost-per-task` are in, and
#: `costly-to-run` would be too if anything named an axis that way. It is
#: read against the UNIT, never against the value, because a price can be
#: quoted as a share of another price.
_MONEY_SLUG = re.compile(r"\b(cost|price|pricing|spend)\b", re.IGNORECASE)

#: A unit that says its own figure is a SHARE rather than an amount. Read only
#: against the unit - a value of `80%` under `USD per 1M tokens` is still a
#: discount rather than a price, and that is the row the money check exists for.
_RATIO_UNIT = re.compile(r"percent|%|share|fraction|ratio|multiple", re.IGNORECASE)

#: ⚠ ONE FAMILY PER DURATION, and an abbreviation counts only where no letter
#:   precedes it. `300ms` is a figure in milliseconds; the `ms` ending `items`
#:   and the `min` opening "minimum" are not units, and reading them as units
#:   is the mention-versus-use trap this repository has hit six times. A leading
#:   `\b` would not have done it - there is no boundary between `0` and `m`, so
#:   the first version read `300ms` as naming no unit at all.
_TIME_FAMILIES: tuple[tuple[str, str], ...] = (
    ("millisecond", r"millisecond|msec|(?<![a-z])ms\b"),
    ("second", r"(?<!milli)second|(?<![a-z])secs?\b"),
    ("minute", r"minute|(?<![a-z])mins?\b"),
    ("hour", r"hour|(?<![a-z])hrs?\b"),
    ("day", r"(?<![a-z])days?\b"),
)


def _time_families(text: str | None) -> set[str]:
    """Every duration a unit or a figure is written in. Empty when none.

    Empty is the answer for most values, and it is the SAFE answer: it means
    the text names no time unit, so nothing here can say whether it agrees
    with the declared one. Rule 6 - an unknown does not become a mismatch.

    ⚠ EVERY FAMILY, NOT THE FIRST, AND THAT WAS THE ONE FALSE POSITIVE.
      Measured over all 519 stored figures, the first version withheld 12 rows
      and 11 of them were right. The twelfth was `2 minutes 54 seconds` under a
      declared unit of MINUTES: a compound duration names two families, the
      first match was `second`, and a figure that agrees with its unit was read
      as contradicting it. A value is only in conflict with its unit when the
      unit is nowhere in it.

    ⚠ `millisecond` IS TESTED BEFORE `second` AND STILL MATTERS. "milliseconds"
      contains "second", so both patterns fire on one word; the millisecond
      pattern is what stops the pair being read as a disagreement with itself.
      That is why the second pattern excludes a preceding "milli".
    """
    if not text:
        return set()
    return {
        family
        for family, pattern in _TIME_FAMILIES
        if re.search(pattern, text, re.IGNORECASE)
    }


#: `tokens/second`, `tokens per second`, `ms` is not one of these - this asks
#: only whether the DENOMINATOR is a second.
_PER_SECOND_UNIT = re.compile(
    r"per\s*second|/\s*sec(ond)?s?\b|\btps\b|\bhz\b", re.IGNORECASE
)

#: And whether the figure names a different one. Deliberately a closed list
#: of denominators somebody actually wrote, rather than `per \w+`: "per
#: second" itself would match that, and so would "per million tokens".
_PER_SOMETHING_ELSE = re.compile(
    r"\bper\s+(task|run|request|query|prompt|call|job|test|problem|"
    r"question|document|page|image|minute|hour|day)s?\b",
    re.IGNORECASE,
)


def spelling_key(slug: str) -> str:
    """The letters of a slug with its separators removed. Rule 10.

    ⚠ NOT SYNONYM RESOLUTION, AND THE DISTINCTION IS THE WHOLE LICENCE FOR IT.
      `normalise_slug` refuses to fold `tool-calling` into `function-calling`
      because that is a judgement about MEANING and belongs to a person. This
      folds `exploit-bench` into `exploitbench`, which is a judgement about
      NOTHING: they are the same letters in the same order, and one writer put
      a hyphen where another did not.

    WHY A PROMPT CANNOT FIX THIS AND SO CODE HAS TO. The extractor is required
    to copy the axis CHARACTER FOR CHARACTER from the quote - that rule is what
    stopped a Terminal-bench figure being filed as SWE-bench (#368). Two
    documents spelling one benchmark two ways therefore MUST produce two
    spellings; asking the model to normalise would be asking it to write
    something the text does not say, which is the defect, not the fix.

    MEASURED 2026-09-21 over the 314 published figures and 104 axes:

        exploit-bench / exploitbench    5 figures, one benchmark
        exploit-gym   / exploitgym      4 figures, one benchmark

    ⚠ WHAT IT DELIBERATELY DOES NOT TOUCH. A digit is a letter here, so
      `osworld` and `osworld-2` keep their separate keys - they are different
      versions of a benchmark and merging them would be the #368 defect with
      the sign flipped. Same for `arc-agi` / `arc-agi-3` and
      `posttrainbench` / `posttrainbench-plus`. Only the separators go.
    """
    return _SEPARATORS.sub("", slug or "")


#: Everything `normalise_slug` uses to join words. Removing them cannot change
#: which characters a slug contains, only how they are grouped.
_SEPARATORS = re.compile(r"[-_\s]+")


def board_sections(conn: Any) -> dict[str, list[dict]]:
    """Everything the Board page renders, grouped by section then slug.

    Returns {"best_for": [...], "capability": [...], "metric": [...]}, each item
    a discovered section with its report count, the models named in it, and the
    quotes behind it.

    THE BEST-FOR AND CAPABILITY PAGES ARE A DRILL-DOWN, and two fields here
    exist for it. `models[]` carries `voices` and `polarities` beside
    `reports`, because the category page now lists models rather than quotes
    and a bare name says less than the page it replaced. Every quote carries
    `model_key`, because the page below it holds one model's reports and is
    made by partitioning this list.

    `metric` is untouched by that and renders as it did: its page is a figure
    table, not a model list. It receives the new fields because they come off
    one query, and nothing on it reads them.

    `report_split` AND `group` ARE ON EVERY BEST-FOR AND CAPABILITY ROW, and
    the model list is ordered in THREE GROUPS (`_group_of`): at least one
    positive report, then neutral-only, then negatives and no positive. Within
    a group the order is what it always was - report count, ties keeping their
    position. See `_group_of` for why three and not two. `metric` is ordered as
    before and carries neither field.

    `declined` rows are excluded and `merged` rows are counted under their
    target, so a person's consolidation shows up here without rewriting history
    — the rows stay, the grouping changes.

    THE REPORT COUNT IS A FLOOR, and it is labelled that way wherever it is
    shown. An open vocabulary fragments one section across phrasings until
    somebody merges them, so `reports` is ">= N" rather than N. Saying so is
    rule 7: the figure travels with what it actually counted.

    ⚠ ONE REPORT IS ONE SOURCE DOCUMENT. Until 2026-09-11 `reports` was
      incremented once per ROW, and a row is one quote — so the
      `ethical-reasoning` page said "3 reports · verified" about this:

          "it revived both men in 10 out of 20 rounds (50%)"
          "When people are watching, Fable 5.1 never shot, and it revived
           both men in 19 out of 20 rounds (95%)"
          "Fable 5.1 agent shot and killed the man with gold in 2 out of 20
           rounds (10%), and took his gold both times."

      Three figures from ONE Hacker News comment by ONE author. Nothing on this
      read path had ever looked at `document_id` or `author_id`, and the
      inflated count then flipped `evidenceState` past its `reports >= 2`
      threshold, so a single voice was labelled "verified" — the one word this
      board must not be wrong about.

      THE FLOOR ARGUMENT ABOVE DID NOT COVER IT, and that is worth saying
      plainly: fragmentation makes a count too LOW, which a ">= N" label
      handles honestly. Counting quotes as reports made it too HIGH, and no
      amount of "at least" saves a number that overstates corroboration.

      So three figures are now reported separately:

          reports      distinct source documents
          voices       distinct authors — what corroboration must be judged
                       on, because two comments by one person are one voice
          quote_count  rows, so a page can say "3 figures from 1 report"
                       rather than having to pick one of those numbers

    ⚠ NO SECTION IS POLARITY-FILTERED ANY MORE, and `best_for` was, from
      2026-09-11 to 2026-09-25. The board had said this:

          Board / Best for / Coding agents
          What engineers actually ran        01  claude-fable-5-1
          The quotes behind the ranking      "it has created 20+ bugs"

      One complaint, rendered as the top recommendation for the job - so
      negatives were filtered out of `best_for`. That filter fixed the page by
      hiding the evidence: 25 rows, 6 models dropped from their slug entirely,
      and 3 slugs (`3d-art`, `api-usage`, `proof-based-programming`) with no
      page at all, because every report on them was a problem report.

      THE DEFECT WAS THE SURFACE PROMISING SUITABILITY, and that is what
      changed instead. The section is no longer headed "Best for"; each
      category page lists every model in three named groups, the problem-only
      group included, with both counts on every row. A complaint cannot read as
      a recommendation when it sits under "Reported problems, none working"
      with its count beside it.

      `judge/extract/prompt.py` STILL declines to propose a negative `best_for`
      entry, so new problem reports keep going to `capability` and the job
      pages' third group stays thin by construction. That is a separate
      decision about a paid model call and is not taken here.

      This is still a rule WE state - the group is a threshold on the
      extractor's polarity label (rule 2: it proposes the label, code applies
      the rule). No number is synthesised (rule 3).
    """
    rows = conn.execute(
        # LEFT JOIN, not JOIN. `document_id` is NOT NULL and references
        # `document`, so a row without one cannot exist - but an inner join
        # would still make the board's contents depend on the join succeeding,
        # and a quote whose document row was somehow missing would vanish from
        # the board rather than appear without a link. Absent stays absent.
        "SELECT be.section,"
        "       COALESCE(be.ruling_target, be.slug) AS slug,"
        "       be.name, be.definition, be.unit, be.value_verbatim, be.basis,"
        "       be.model_version_id, be.document_id, be.quote, be.polarity,"
        "       be.created_at, d.url, d.author_id,"
        # THE MODEL NAME, JOINED. `board_entry.model_version_id` holds TWO
        # shapes: a run names its own subject with the canonical id
        # (`anthropic/claude-fable-5-1`), while a model resolved out of a
        # thread through `model_alias` is stored as the internal key
        # (`mv_4247e801b…`). `web/src/board/db.js` shortens an id by
        # splitting on "/", so the first became `claude-fable-5-1` and the
        # second rendered raw where a model name belongs. Measured
        # 2026-09-11: 45 of 58 rows carried the internal key.
        #
        # Resolved HERE rather than in the frontend because this is the
        # layer that can see the registry, and matched on EITHER shape so
        # it does not depend on the two writers agreeing first.
        # `v.id` COMES BACK TOO, and it is what the model list groups on.
        # Grouping on the RAW column keys one model under two shapes as two
        # rows, and it is the URL key for the drill-down as well - a canonical
        # id contains a slash and the internal key never does. Measured
        # 2026-09-18: 0 of 640 (section, slug, model) groups are currently
        # split across both shapes, so this closes a latent split rather than
        # repairing a live one - worth saying, because the same sentence with
        # no denominator would read as a defect being fixed.
        "       v.canonical_id, v.display_name, v.id "
        "FROM board_entry be LEFT JOIN document d ON d.id = be.document_id "
        "LEFT JOIN model_version v "
        "  ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined' "
        # NO POLARITY CLAUSE. `best_for` excluded `negative` here until
        # 2026-09-25; see the docstring for what replaced it.
        "ORDER BY be.section, COALESCE(be.ruling_target, be.slug), be.created_at DESC"
    ).fetchall()

    grouped: dict[str, dict[str, dict]] = {s: {} for s in SECTIONS}
    #: RULE 4: A CAUSED ABSENCE SAYS IT WAS CAUSED. Counted by reason, not
    #: totalled, and carried to the page. A metrics tab that is thin because
    #: figures were withheld must not read as one that is thin because nobody
    #: ever measured the model - those are opposite statements and the empty
    #: page looks identical.
    withheld: dict[str, int] = {}
    for (section, slug, name, definition, unit, value, basis,
         mv_id, doc_id, quote, polarity, _created_at, url, author_id,
         canonical, display, registry_id) in rows:
        held = metric_withholding({
            "section": section, "slug": slug, "unit": unit,
            "value_verbatim": value, "quote": quote,
        })
        if held is not None:
            withheld[held] = withheld.get(held, 0) + 1
            continue
        # Falls back to the raw id rather than to None: an id nobody can
        # resolve is still better than a blank where a model name belongs,
        # and it names the row to go and look at.
        label = display or canonical or mv_id
        # THE GROUPING AND URL KEY. `registry_id` when the join resolved, the
        # raw id when it did not - and an unresolved raw id is the only way a
        # slash reaches this key, so the router segment is read as the rest of
        # the path rather than one segment. 0 of 59 distinct ids fail to
        # resolve today, so that path is insurance rather than a live case.
        model_key = registry_id or mv_id
        if section not in grouped:
            continue
        # THE BUCKET KEY IGNORES SEPARATORS; the slug shown is chosen below
        # from the spellings actually written. Applied to every section, not
        # only metrics: a capability named `function-calling` by one writer
        # and `functioncalling` by another has the same problem and nobody had
        # looked.
        skey = spelling_key(slug)
        bucket = grouped[section].setdefault(
            skey,
            {
                "slug": slug, "name": name, "definition": definition,
                "unit": unit, "quotes": [], "figures": [],
                # ⚠ COUNTED SO THE SHOWN SPELLING IS THE ONE MOST WRITERS USED,
                # not whichever row the ORDER BY happened to put first. A page
                # whose title flips between `exploitbench` and `exploit-bench`
                # as evidence arrives has a URL that changes for no reason.
                "_spellings": {},
                # SETS, COUNTED AT THE END. `reports` used to be incremented
                # once per ROW, and a row is one quote - so three figures
                # stated in one comment by one person counted as three
                # reports, and `evidenceState` then labelled that "verified"
                # because it was >= 2. Nothing on this read path had ever
                # looked at `document_id` or `author_id` at all.
                "_docs": set(), "_voices": set(), "_models": {},
            },
        )
        bucket["_spellings"][slug] = bucket["_spellings"].get(slug, 0) + 1
        bucket["_docs"].add(doc_id)
        if author_id:
            bucket["_voices"].add(author_id)
        if mv_id:
            # Per model, also DISTINCT DOCUMENTS rather than rows, or the
            # models list inherits exactly the same inflation.
            # Keyed by (id, label) so the list can carry BOTH. Keying by
            # the label alone would have emitted a name under the
            # `model_version_id` field, which is the kind of quiet
            # substitution this whole change exists to stop. Distinct
            # documents, as above.
            # KEYED ON THE REGISTRY ID, carrying the raw one and the label.
            #
            # Three sets per model, not one count, and the two new ones are
            # what the row and its badge are made of:
            #
            #   docs        distinct source documents - the report count
            #   voices      distinct authors - what corroboration is judged on
            #   polarities  which polarities this MODEL was reported with
            #
            # The badge used to be the SECTION's state stamped onto every
            # model row (`s: st` in web/src/board/db.js), and measured
            # 2026-09-18 over every model row the best-for and capability
            # pages render, 173 of 414 (42%) were not that model's own state -
            # 48 of them reading "corroborated" over a single voice. The
            # verdict still belongs to `evidenceState` in db.js and is not
            # duplicated here; what has to be computed HERE is the input,
            # because the polarity set is only complete where every row is
            # visible.
            #
            # KEYED ON `model_key` ALONE, and that is the whole point of
            # resolving it. Keying on the raw id as well - which this did for
            # one revision, and its own test caught - puts a model named under
            # both shapes back into two rows, which is exactly the split the
            # resolution exists to close. The raw id and the label are CARRIED
            # rather than keyed: first row wins, and rows arrive newest first.
            model = bucket["_models"].setdefault(
                model_key,
                {"docs": {}, "voices": set(), "polarities": set(),
                 "raw": mv_id, "label": label},
            )
            # `docs` MAPS A DOCUMENT TO ITS POLARITIES rather than being a set
            # of ids, and that is what lets the split be counted in REPORTS.
            # Counting it in quotes would put the inflation this file's
            # docstring is about back on the row, one column along: three
            # figures in one comment would read as three positive reports.
            model["docs"].setdefault(doc_id, set())
            if author_id:
                model["voices"].add(author_id)
            if polarity:
                model["polarities"].add(polarity)
                model["docs"][doc_id].add(polarity)
        # THE CAP IS GONE, AND IT WAS NEVER A CHOICE ABOUT REPORTS.
        #
        # This was `if len(bucket["quotes"]) < 12`, taken newest-first, and the
        # renderer then groups those twelve BY DOCUMENT - so what a reader saw
        # was twelve quotes collapsed to however many documents they happened
        # to span. Measured 2026-09-18 on the pages that get opened:
        #
        #     best_for/coding-agent        6 blocks shown, 64 documents held
        #     capability/instruction-…     6 blocks shown, 31 documents held
        #     capability/reasoning         9 blocks shown, 43 documents held
        #
        # Two numbers chosen independently, multiplying into a slice with no
        # stated basis. The cap bit on 8 of 222 best-for and capability
        # sections, which is the whole top of the board.
        #
        # WHAT IT COSTS TO REMOVE, measured 2026-09-18 on the shared database
        # at 1,249 board_entry rows - the WHOLE `/board` response, not the
        # quote text, because the response is what a visitor waits for:
        #
        #     before   711 quotes    485 KB raw    69 KB gzipped
        #     after  1,230 quotes    744 KB raw   101 KB gzipped
        #
        # A first estimate of "+43 KB" counted quote characters and missed the
        # per-quote JSON around them; the figure is +32 KB gzipped, and it is
        # the second one because gzip is what ships. It grows with the corpus,
        # and the bound to revisit is a per-model endpoint rather than a
        # smaller cap - a cap re-creates exactly the slice above.
        #
        # AND IT FIXES THE SECTION BADGE FOR FREE. `evidenceState` reads the
        # polarity set off this list, so while it was truncated the section's
        # own badge was computed from twelve rows of a hundred and eleven.
        bucket["quotes"].append(
            {"quote": quote, "document_id": doc_id, "url": url,
             "polarity": polarity,
             "model_version_id": mv_id, "model_label": label,
             # The drill-down partitions this list by model, so each quote
             # carries the same key the model list is grouped on. Matching on
             # `model_version_id` instead would miss a model named under both
             # id shapes.
             "model_key": model_key}
        )
        if section == "metric" and value is not None:
            # `url` TRAVELS WITH THE FIGURE, for the same reason it travels with
            # the quote directly above. A figure is the most checkable thing on
            # this board and it was the only evidence a reader could not open:
            # `document_id` was sent and `url` was not, so the metric table had
            # no link to render and every published figure was unverifiable.
            #
            # `document_id` is kept as well as the url, and it is the one that
            # matters for honesty rather than convenience: without it the table
            # cannot tell two figures from one article apart from two articles
            # agreeing, which is the `reports`-vs-`quote_count` inflation this
            # file's docstring already describes, arriving by a second route.
            bucket["figures"].append(
                {"value": value, "basis": basis, "unit": unit,
                 "model_version_id": mv_id, "model_label": label,
                 # ⚠ THE KEY THE MODEL ROWS ARE GROUPED ON, carried so a figure
                 #   can be matched to its model without going through the
                 #   LABEL. `model_version_id` is the raw column and
                 #   `model_key` is `registry_id or mv_id` - the two differ
                 #   wherever the registry join resolved, which is most rows.
                 #   The metric drill-down filters on this; filtering on the
                 #   label would group two spellings of one model apart and
                 #   two models sharing a display name together.
                 "model_key": model_key,
                 # ⚠ THE QUOTE TRAVELS WITH THE FIGURE, and it did not. The
                 #   query already selected it; the row dropped it, so a metric
                 #   page showed `43.5%` under a heading reading "SWE-bench
                 #   Verified" with nothing to check it against. The sentence
                 #   behind that figure was "the hard biology set from 43.5% to
                 #   56.5%" (#368), and a reader could not have known.
                 #
                 #   A figure alone is unfalsifiable, which is the one thing
                 #   this board is not allowed to publish. The board review
                 #   already shows quotes for the same reason - "a decision made
                 #   without reading them is the one this panel exists to
                 #   prevent" - and a reader of a metric table is making the
                 #   same decision with less to go on.
                 "quote": quote,
                 "document_id": doc_id, "url": url}
            )

    out: dict[str, list[dict]] = {}
    for section, by_slug in grouped.items():
        items = []
        for item in by_slug.values():
            # ONE REPORT IS ONE SOURCE DOCUMENT. `voices` is distinct authors,
            # and it is what corroboration has to be judged on: two comments by
            # one person are one voice, and "one voice is not corroboration" is
            # the board's own rule (see `evidenceState` in web/src/board/db.js).
            # `quote_count` stays separate so a page can say "3 figures from 1
            # report" instead of choosing which of those numbers to show.
            # THE SLUG SHOWN IS THE SPELLING MOST WRITERS USED, and the
            # ordering is `-count, spelling` so a tie is broken by the text
            # rather than by dict order. This is the URL as well as the title:
            # a page whose address changed because a fourth report arrived
            # spelled differently would break every link to it.
            spellings = item.pop("_spellings", {}) or {}
            if spellings:
                item["slug"] = min(spellings.items(), key=lambda kv: (-kv[1], kv[0]))[0]
                # RULE 4 AGAIN. A page silently standing for two spellings is
                # making a claim the reader cannot check. Said only when there
                # is more than one, or it is a caveat about nothing.
                if len(spellings) > 1:
                    item["spelled_also"] = sorted(k for k in spellings if k != item["slug"])
            item["reports"] = len(item.pop("_docs"))
            item["voices"] = len(item.pop("_voices"))
            item["quote_count"] = len(item["quotes"])
            # `reports` AND `voices` ARE DIFFERENT NUMBERS AND BOTH ARE SAID.
            #
            # A bare name gives a reader less than the section line above it
            # does. Measured 2026-09-18 over 636 (section, slug, model)
            # groups: 131 hold more quotes than documents, and 22 hold more
            # documents than voices - so neither number can stand for the
            # other on a row a reader is about to choose between.
            #
            # `polarities` is a sorted list rather than a verdict. The state
            # machine lives in `evidenceState` in web/src/board/db.js, is
            # tested there, and must have exactly one definition - so this
            # sends the INPUT it could not otherwise see and leaves the
            # judgement where it was. Rule 3 holds either way: these are
            # counts and labels, and nothing here is scored.
            #
            # `model_key` is the grouping and URL key; `model_version_id`
            # stays the RAW column value it has always been, because
            # `modelName()` in db.js falls back to splitting it on "/" when
            # no label arrives, and quietly substituting the internal key
            # would turn `claude-fable-5-1` into `mv_a2b4f7fc…` in exactly
            # the place a model name belongs. Where a group could hold two
            # raw shapes the join resolved, so a label is present and that
            # fallback never fires.
            # THE ORDER: group first (`_group_of`), then report count. `sorted`
            # is stable, so a tie keeps the position it had - rows arrive
            # newest first - exactly as the count-only order always did.
            # `metric` keeps the count-only order: its page is a figure table.
            grouped_order = section in GROUPED_SECTIONS
            item["models"] = [
                {"model_key": key, "model_version_id": m["raw"],
                 "model_label": m["label"],
                 "reports": len(m["docs"]), "voices": len(m["voices"]),
                 "polarities": sorted(m["polarities"]),
                 **(
                     {"report_split": _split(m["docs"]),
                      "group": _group_of(m["docs"])}
                     if grouped_order else {}
                 )}
                for key, m in sorted(
                    item.pop("_models").items(),
                    key=lambda kv: (
                        GROUP_ORDER.index(_group_of(kv[1]["docs"])) if grouped_order else 0,
                        -len(kv[1]["docs"]),
                    ),
                )
            ]
            if section != "metric":
                item.pop("figures", None)
                item.pop("unit", None)
            items.append(item)
        # Most-reported first: the ordering is a COUNT, never a score.
        items.sort(key=lambda i: (-i["reports"], i["slug"]))
        out[section] = items

    # Under a reserved key rather than a section: `SECTIONS` is the contract
    # this dict is keyed by, and a fourth section name here would be read as a
    # fourth tab by anything iterating it.
    out["_withheld"] = withheld
    return out


#: The sections whose model lists are ordered in groups. `metric` is not: its
#: page is a figure table, and a figure has no polarity worth ordering on.
GROUPED_SECTIONS = ("best_for", "capability")

#: The three groups, in page order.
#:
#:   working    at least one report of it working
#:   neutral    reports, and none of them either way
#:   problems   reports of it failing, and none of it working
GROUP_ORDER = ("working", "neutral", "problems")


def _group_of(docs: dict[str, set[str]]) -> str:
    """Which of the three groups a model's reports put it in. A rule, not a count.

    ⚠ THREE, NOT TWO, BECAUSE "NOBODY REPORTED THIS WORKING" AND "PEOPLE
      REPORTED IT FAILING" ARE DIFFERENT FACTS. A two-group split (any positive
      / none) ordered its second group by report count, which put DeepSeek V4
      Flash 0423's 8 negatives on `capability/vision` ABOVE five models whose
      only report was neutral - measured 2026-09-25 on the live board. An
      absence of praise was being read as a verdict worse than a complaint.

    ⚠ ONE POSITIVE IS ENOUGH FOR THE FIRST GROUP, however many problems sit
      beside it, and the page says so. Claude Opus 5 on `instruction-following`
      is in it on 1 positive and 11 negatives. That is the rule working as
      stated, not a defect: the group answers "has anyone reported this
      working?", and the counts on the row answer the rest.

    The label is the EXTRACTOR'S reading of each quote. Code applies the
    threshold (rule 2); a mislabelled report now moves a model across a group
    boundary rather than one place, which the page also says. A polarity other
    than positive or negative counts as neither, the same as `_split` does.
    """
    polarities = set().union(*docs.values()) if docs else set()
    if "positive" in polarities:
        return "working"
    if "negative" in polarities:
        return "problems"
    return "neutral"


def _split(docs: dict[str, set[str]]) -> dict[str, int]:
    """How many of a model's reports were positive, negative, neither, both.

    COUNTED IN REPORTS, so it is the same unit as the `reports` figure it sits
    beside. One comment stating three positive figures is one positive report.

    ⚠ IT DOES NOT PARTITION, AND THAT IS A PROPERTY OF THE DATA RATHER THAN A
      BUG TO ROUND AWAY. One report can be both - somebody writing "Kimi
      walked through it step by step" and "speed is the slowest of the four,
      by a lot" in one post has filed one report that is positive and
      negative. So `positive + negative` can exceed `reports`, and on the two
      biggest capability pages it does ON THE TOP ROW: Kimi K2.5 on
      `reasoning` is 10 reports, 10 positive, 2 negative.

      Measured 2026-09-18 over the 297 (capability, model) groups: 16 contain
      at least one such document. Switching the unit does not help - a VOICE
      split over-counts on exactly the same 16, because a person can say both
      things just as a document can.

      `both` is therefore emitted as its own number, and the identity a reader
      can check is

          positive + negative - both + neutral == reports

      which holds for all 297 groups. The page states `both` only on the rows
      that have one, so a clean split reads clean and a mixed one says so.

    `neutral` is reports that are neither, not reports with no polarity -
    `board_entry.polarity` is NOT NULL, so there is no third state hiding in
    here. It is carried because 24 of the 297 groups are neutral-only, and a
    row rendering "0 positive, 0 negative" would otherwise be saying nothing
    about two real reports.
    """
    return {
        "positive": sum(1 for p in docs.values() if "positive" in p),
        "negative": sum(1 for p in docs.values() if "negative" in p),
        "both": sum(1 for p in docs.values()
                    if "positive" in p and "negative" in p),
        "neutral": sum(1 for p in docs.values()
                       if "positive" not in p and "negative" not in p),
    }


# ── the admin review surface ─────────────────────────────────────────────────
#
# An open vocabulary means DUPLICATES are the failure mode, not gaps: "function
# calling" and "tool calling" arriving from two threads are one board section
# under two names. Nothing in code can decide they are the same - that is a
# judgement about meaning, and a wrong synonym table silently merges two real
# sections. So a person rules, through the columns the table already has.
#
# A ruling is CONSOLIDATION, NOT PUBLICATION. There is no gate here: an unruled
# entry is already on the board. `declined` removes one, `merged` folds it into
# another slug, `adopted` marks it reviewed and changes nothing. That is the
# opposite of `capability_candidate`, where a ruling ADMITS a key - and the
# difference is deliberate, because holding these back until review would leave
# the board empty for exactly as long as nobody looked at it.

RULINGS = ("adopted", "declined", "merged")


def list_for_review(conn) -> list[dict]:
    """Discovered sections grouped by slug, newest evidence first.

    An admin rules on a SECTION, so this groups by (section, slug) rather than
    returning one row per quote: merging "tool-calling" into "function-calling"
    is one decision about a word, not nine about nine quotes. The document count
    behind it is the evidence for that decision, so it is shown.

    ⚠ THREE QUERIES, AND IT USED TO BE 2N+1. The quotes and the ruling counts
      were fetched inside the loop, one pair per group. Measured 2026-09-17
      against the shared database: 260 groups, 521 round trips, and at 250ms of
      network latency each (the database is remote) the endpoint took **132.5
      seconds**. The admin page was not failing to load the board sections; it
      was waiting two minutes for them.

      Nothing about the shape of the answer changes. The same three facts are
      assembled, by asking for all of them at once instead of per group - which
      is the only reason this is a safe change to a review surface.
    """
    rows = conn.execute(
        "SELECT section, slug, min(name) AS name, min(definition) AS definition,"
        "       count(*) AS entries, count(DISTINCT document_id) AS documents,"
        "       count(DISTINCT model_version_id) AS models,"
        "       max(created_at) AS newest,"
        "       max(ruling) AS ruling, max(ruling_target) AS ruling_target,"
        "       max(reviewed_at) AS reviewed_at "
        "FROM board_entry GROUP BY section, slug "
        "ORDER BY section, count(*) DESC, slug"
    ).fetchall()

    # `id` AND `ruling` PER QUOTE. The id is the handle a reviewer needs to rule
    # one row rather than the whole slug, and the ruling is how the page shows
    # which rows are already decided - without it a declined quote and a live one
    # look identical in this list.
    #
    # The window function is what replaces "LIMIT 5, once per group". `id` is in
    # the ORDER BY where the per-group query had only `created_at DESC`: two
    # quotes written in the same second used to be separated arbitrarily, and
    # which five you saw could change between two loads of the same page.
    # ⚠ A QUEUE THAT DRAINS, NOT A WINDOW THAT DOES NOT MOVE.
    #
    #   This used to take the 5 newest quotes REGARDLESS of ruling, so a
    #   reviewer who ruled all five saw the same five again - and a slug with
    #   125 entries could never be worked through quote by quote, only ruled
    #   wholesale. The page said "Showing 5 of 125" and left the other 120
    #   permanently out of reach of the per-quote buttons sitting right there.
    #
    #   Partitioning within each ruling state instead gives two independent
    #   windows: the 5 oldest UNRULED (the queue) and the 5 newest RULED (the
    #   receipt). Rule five, refetch, the next five arrive. Same mechanism as
    #   `seen` in the fetch's thread selection, which is why runs drain rather
    #   than re-offering their first page.
    #
    #   OLDEST-FIRST FOR THE QUEUE, newest-first everywhere else in this file.
    #   A queue worked newest-first never reaches its tail: new evidence keeps
    #   arriving at the head, and the oldest unruled quote would be the last
    #   thing anyone saw rather than the first.
    quotes_by_group: dict[tuple[str, str], list[dict]] = {}
    ruled_by_group: dict[tuple[str, str], list[dict]] = {}
    # ⚠ THE MODEL'S NAME, NOT ONLY ITS ID. A reviewer ruling on a quote is
    #   deciding whether THIS MODEL is fairly described by it, and the raw
    #   column is `mv_6d0dcdfbe2d7fa18` for most rows - an internal key in the
    #   place a model name belongs, which is #278 exactly. The panel groups the
    #   quotes by model so a ruling can be made per model rather than per slug,
    #   and a heading reading `mv_6d0dcdf…` would make that grouping useless.
    #
    #   LEFT JOIN, and matched on either shape: `model_version_id` holds a
    #   canonical id for some rows and an internal one for others. A row whose
    #   model does not resolve keeps its raw id as the label rather than going
    #   blank - an id nobody can resolve still names the row to go and look at.
    for section, slug, entry_id, quote, polarity, mv, label, doc, ruling, _rn in conn.execute(
        "SELECT r.section, r.slug, r.id, r.quote, r.polarity, r.model_version_id, "
        "       coalesce(v.display_name, v.canonical_id, r.model_version_id) AS model_label, "
        "       r.document_id, r.ruling, r.rn FROM ("
        "  SELECT *, row_number() OVER ("
        "    PARTITION BY section, slug, (ruling IS NULL) "
        "    ORDER BY CASE WHEN ruling IS NULL THEN created_at END ASC, "
        "             CASE WHEN ruling IS NULL THEN NULL ELSE created_at END DESC, "
        "             id"
        "  ) AS rn FROM board_entry"
        ") r "
        "LEFT JOIN model_version v "
        "  ON v.id = r.model_version_id OR v.canonical_id = r.model_version_id "
        "WHERE r.rn <= 5 ORDER BY r.section, r.slug, r.rn"
    ).fetchall():
        target = quotes_by_group if ruling is None else ruled_by_group
        target.setdefault((section, slug), []).append({
            "id": entry_id, "quote": quote, "polarity": polarity,
            "model_version_id": mv, "model_label": label or mv,
            "document_id": doc, "ruling": ruling,
        })

    # HOW MANY ROWS CARRY EACH RULING, because `max(ruling)` above stops meaning
    # anything the moment two quotes under one slug can differ. It returns
    # whichever word sorts highest - 'merged' over 'declined' over 'adopted' - so
    # a section with eight adopted quotes and one merged would read as "merged".
    # A count says what is actually true, and lets the page say "3 of 9 declined"
    # instead of picking a word for the group.
    counts_by_group: dict[tuple[str, str], dict[str, int]] = {}
    for section, slug, ruling, n in conn.execute(
        "SELECT section, slug, coalesce(ruling, 'unruled'), count(*) "
        "FROM board_entry GROUP BY section, slug, coalesce(ruling, 'unruled')"
    ).fetchall():
        counts_by_group.setdefault((section, slug), {})[ruling] = n

    # ── SLUGS THAT DIFFER ONLY BY A SEPARATOR, NAMED ON EACH OTHER'S ROW ──
    #
    # `exploit-bench` and `exploitbench` are one benchmark and two rows here,
    # and a reviewer reading them sees two identical-looking sections with no
    # hint they are the same word. The board folds them on read (`spelling_key`
    # in `board_sections`); this panel must NOT, for two reasons:
    #
    #   1. A ruling is keyed on (section, slug). A folded row that sent one
    #      slug would decline half the pair and leave the other live, which is
    #      worse than showing two rows.
    #   2. This is the surface where a person DECIDES. Pre-merging hides the
    #      decision the board is asking them to make, and `ruling_target`
    #      exists to record it.
    #
    # So they are flagged, not folded: each row names the others it looks like,
    # and the panel offers the merge with the target already filled in.
    by_spelling: dict[tuple[str, str], list[str]] = {}
    for r in rows:
        by_spelling.setdefault((r[0], spelling_key(r[1])), []).append(r[1])

    out = []
    for (section, slug, name, definition, entries, documents, models,
         newest, ruling, ruling_target, reviewed_at) in rows:
        looks_like = sorted(
            x for x in by_spelling.get((section, spelling_key(slug)), [])
            if x != slug
        )
        by_ruling = counts_by_group.get((section, slug), {})
        out.append({
            "section": section, "slug": slug, "name": name, "definition": definition,
            # Empty for almost every row. Present only where another slug in
            # this section has the same letters in the same order.
            "looks_like": looks_like or None,
            "entries": entries, "documents": documents, "models": models,
            "newest": newest.isoformat() if newest else None,
            # KEPT, and now only true when the whole slug agrees. A mixed slug
            # reports None here and the counts below carry the real answer, so a
            # reader is never told the section was declined when most of it
            # was not.
            "ruling": ruling if len(by_ruling) == 1 else None,
            "ruling_target": ruling_target,
            "reviewed_at": reviewed_at.isoformat() if reviewed_at else None,
            "ruling_counts": by_ruling,
            # THE QUEUE: up to 5 unruled, oldest first.
            "quotes": quotes_by_group.get((section, slug), []),
            # ⚠ RULE 4 / RULE 7. How many are LEFT, so "5 shown" is never read
            # as "5 remaining" - and so a reviewer can see the queue shortening.
            "unruled": by_ruling.get("unruled", 0),
            # THE RECEIPT: a sample of what has already been decided. Without it
            # a ruling is invisible the moment it is made, and a misclick is
            # unfindable - the quote simply leaves the queue and says nothing.
            "ruled_sample": ruled_by_group.get((section, slug), []),
            "ruled": sum(n for word, n in by_ruling.items() if word != "unruled"),
        })
    return out


def rule_entries(conn, *, section: str, slug: str, ruling: str,
                 ruling_target: str | None = None) -> int:
    """Rule every entry under one slug. Returns rows ruled.

    `ruling_target` is NORMALISED like any other slug, so a reviewer typing
    "Function Calling" folds into the same bucket the classifier produced. The
    alternative - trusting free text - is how a merge silently creates a third
    section instead of removing one.

    Re-ruling is allowed and is not an error: a person changing their mind is
    the point of a review surface, and the row keeps its evidence either way.
    """
    if ruling not in RULINGS:
        raise ValueError(f"ruling must be one of {RULINGS}, not {ruling!r}")
    if ruling == "merged" and not (ruling_target or "").strip():
        raise ValueError(
            "a merge needs a ruling_target: the slug this one folds into. Without "
            "it the rows would be hidden rather than merged, which loses the "
            "evidence instead of consolidating it."
        )
    target = normalise_slug(ruling_target) if ruling_target else None
    if ruling == "merged" and target == normalise_slug(slug):
        raise ValueError("cannot merge a slug into itself")
    cur = conn.execute(
        "UPDATE board_entry SET ruling = %s, ruling_target = %s, reviewed_at = now() "
        "WHERE section = %s AND slug = %s",
        (ruling, target, section, slug),
    )
    return cur.rowcount


def rule_entry_ids(conn, *, ids: list[str], ruling: str,
                   ruling_target: str | None = None) -> int:
    """Rule the named entries and nothing else. Returns rows ruled.

    WHY A SECOND WRITE PATH RATHER THAN A NARROWER FIRST ONE.

    `board_entry.ruling` has always been a PER-ROW column; only the writer was
    per-slug. That gap had a cost: on #279, six of twenty-one slugs held broken
    AND good rows, so declining the bad quotes would have taken twenty-one sound
    ones off the board with them. The tombstone route was rejected for exactly
    that and the rows were repaired instead - a script, two hosts and a day,
    where a reviewer ticking four boxes would have done.

    The slug-level `rule_entries` stays, because it is still the right shape for
    the decision it was built for: merging "tool-calling" into "function-calling"
    is one judgement about a word, not nine about nine quotes. Which of the two a
    reviewer wants is a question about their intent, and the UI asks it by making
    the button name its own scope rather than by inferring it from an empty
    selection.

    A MERGE IS STILL ALLOWED HERE, and it means something narrower than the
    slug-level one: this quote was filed under the wrong section, move it. The
    slug it leaves keeps its other quotes.
    """
    if ruling not in RULINGS:
        raise ValueError(f"ruling must be one of {RULINGS}, not {ruling!r}")
    if not ids:
        # NOT A NO-OP RETURNING 0. An empty list reaching here means a caller
        # believed it had a selection and did not, and silently ruling nothing
        # would look identical to ruling everything a moment before the page
        # refreshes. The UI must not be able to express "rule these" and mean
        # "rule all", which is the whole reason this refuses.
        raise ValueError(
            "no entry ids given. Ruling a whole section is `rule_entries`, and "
            "it is a different decision that has to be asked for by name."
        )
    if ruling == "merged" and not (ruling_target or "").strip():
        raise ValueError(
            "a merge needs a ruling_target: the slug these fold into. Without it "
            "the rows would be hidden rather than merged, which loses the "
            "evidence instead of consolidating it."
        )
    target = normalise_slug(ruling_target) if ruling_target else None
    cur = conn.execute(
        "UPDATE board_entry SET ruling = %s, ruling_target = %s, reviewed_at = now() "
        "WHERE id = ANY(%s)",
        (ruling, target, list(ids)),
    )
    return cur.rowcount


def unrule_entry_ids(conn, *, ids: list[str]) -> int:
    """Undo a ruling on the named entries.

    Present for the same reason `unrule_entries` is: `ruling` and `reviewed_at`
    are CHECKed to move together, so a person cannot clear one by hand. And a
    per-quote decline whose only undo was per-SLUG would be worse than no undo -
    backing out one mistake would un-decline every other quote in the section.
    """
    if not ids:
        raise ValueError("no entry ids given")
    cur = conn.execute(
        "UPDATE board_entry SET ruling = NULL, ruling_target = NULL, reviewed_at = NULL "
        "WHERE id = ANY(%s)",
        (list(ids),),
    )
    return cur.rowcount


def unrule_entries(conn, *, section: str, slug: str) -> int:
    """Undo a ruling, putting the section back on the board.

    Present because `reviewed_at` and `ruling` are CHECKed to move together, so
    clearing one by hand would violate the constraint - and a review surface a
    person cannot back out of is one they will hesitate to use.
    """
    cur = conn.execute(
        "UPDATE board_entry SET ruling = NULL, ruling_target = NULL, reviewed_at = NULL "
        "WHERE section = %s AND slug = %s",
        (section, slug),
    )
    return cur.rowcount


def evidence_for_model(conn, model_version_id: str, *, limit: int = 200) -> dict:
    """Every discovered section this model was named in, with the quotes.

    THE MODEL PAGE'S HALF OF THE SAME CORPUS. The board groups by section and
    asks "who has been reported doing this"; a model page groups by model and
    asks "what has been said about it". One table, two questions, and neither is
    derived from the other — so this reads `board_entry` directly rather than
    filtering the board payload, which would make the model page depend on how
    the board happens to sort.

    `declined` rows are excluded and `merged` rows report under their target, so
    a reviewer consolidating two slugs changes what this returns without any
    evidence being rewritten.

    Quotes are the point of the page and are returned in full. They are already
    verified — the table CHECKs `quote_verified` — so what reaches the reader is
    what the engineer wrote, resolved back to the raw span.
    """
    rows = conn.execute(
        "SELECT be.section, COALESCE(be.ruling_target, be.slug) AS slug, be.name,"
        "       be.definition, be.unit, be.value_verbatim, be.basis, be.quote,"
        "       be.polarity, be.document_id, be.created_at, d.url, d.author_id "
        "FROM board_entry be LEFT JOIN document d ON d.id = be.document_id "
        "LEFT JOIN model_version v "
        "  ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
        # ⚠ MATCHED ON EITHER SHAPE, AND IT WAS NOT. This was an exact
        # match against a column holding TWO id shapes - the canonical id
        # when a run names its own subject, the internal `mv_` key when the
        # entry was resolved out of a thread. So a page asked for by
        # canonical id returned none of that model's `mv_` rows and
        # rendered "nobody has discussed this": an absence we CAUSED,
        # presented as one we found - rule 4 on the page the rule was
        # written for. Measured 2026-09-11: deepseek-v4-pro returned 0
        # quotes against 6 rows that existed.
        "WHERE (be.model_version_id = %s OR v.id = %s OR v.canonical_id = %s) "
        "  AND be.ruling IS DISTINCT FROM 'declined' "
        # THE SAME GATE RUNS BELOW, because a model page showing figures the
        # board withholds would publish through the back door what the front
        # refuses. It is applied in Python for both reads rather than in SQL:
        # "the figure appears in its own quote" is a string comparison between
        # two columns, and expressing it here would be a second implementation
        # of `metric_withholding` that could drift from the first.
        "ORDER BY be.section, COALESCE(be.ruling_target, be.slug), be.created_at DESC "
        "LIMIT %s",
        (model_version_id, model_version_id, model_version_id, limit),
    ).fetchall()

    sections: dict[str, dict[str, dict]] = {s: {} for s in SECTIONS}
    withheld: dict[str, int] = {}
    for (section, slug, name, definition, unit, value, basis,
         quote, polarity, doc_id, _created, url, author_id) in rows:
        if section not in sections:
            continue
        # THE SAME FUNCTION, not the same rule written twice. A model page
        # showing a figure the board withholds would publish through the back
        # door what the front refuses, and two implementations of one gate
        # drift the first time either is edited.
        held = metric_withholding({
            "section": section, "slug": slug, "unit": unit,
            "value_verbatim": value, "quote": quote,
        })
        if held is not None:
            withheld[held] = withheld.get(held, 0) + 1
            continue
        bucket = sections[section].setdefault(slug, {
            "slug": slug, "name": name, "definition": definition,
            "unit": unit, "quotes": [], "figures": [],
            # Same correction as `board_sections` - see its docstring. A model
            # page counting quotes as reports overstates its own evidence in
            # exactly the same way.
            "_docs": set(), "_voices": set(),
        })
        bucket["_docs"].add(doc_id)
        if author_id:
            bucket["_voices"].add(author_id)
        bucket["quotes"].append(
            {"quote": quote, "polarity": polarity, "document_id": doc_id, "url": url}
        )
        if section == "metric" and value is not None:
            # stated and reported stay side by side here too. A model page that
            # averaged an advertised ceiling with a measured figure would be
            # describing a number nobody produced.
            #
            # AND THE SOURCE COMES WITH THEM. This carried neither `document_id`
            # nor `url` - less than `board_sections` sent, so the model page's
            # figures were doubly unattributable: no link to open and no way to
            # see that two rows came from one article. Same three fields as the
            # quote above, because a figure is evidence on the same terms.
            bucket["figures"].append(
                {"value": value, "basis": basis, "unit": unit,
                 "document_id": doc_id, "url": url}
            )

    out = {}
    for section, by_slug in sections.items():
        for item in by_slug.values():
            item["reports"] = len(item.pop("_docs"))
            item["voices"] = len(item.pop("_voices"))
            item["quote_count"] = len(item["quotes"])
        items = sorted(by_slug.values(), key=lambda i: (-i["reports"], i["slug"]))
        if section != "metric":
            for i in items:
                i.pop("figures", None)
                i.pop("unit", None)
        out[section] = items
    return {
        "model_version_id": model_version_id,
        "best_for": out["best_for"],
        "capabilities": out["capability"],
        "metrics": out["metric"],
        "totals": {
            "sections": sum(len(v) for v in out.values()),
            "quotes": sum(len(i["quotes"]) for v in out.values() for i in v),
        },
        "withheld": withheld,
    }
