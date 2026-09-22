"""The claim record — what E5 emits, and the only thing it may emit.

The extractor returns this and nothing else. No free-text channel, no "notes"
field, no way to take an action. That constraint is half the prompt-injection
defence; the other half is that every claim carries a quote which is then
verified in ordinary Python (see verify.py).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Polarity = Literal["positive", "negative", "neutral"]
Severity = Literal["mild", "clear", "severe"]
Relevance = Literal["central", "passing"]
Specificity = Literal["snapshot", "version", "family"]
EvidenceTier = Literal["A", "B", "C", "D", "E", "F"]

#: The board's three sections, of EQUAL standing. See `BoardEntry`.
#:
#: A claim carries a LIST of entries, never one section, because the board's own
#: copy calls these "three ways into the same evidence": one quote about a slow
#: coding agent answers the metric question (the figure), the capability question
#: (how it behaved) and the job question (what they were building). Forcing a
#: single section would discard two thirds of that and make the truncation look
#: like a finding.
#:
#: What each section is NOT allowed to become is a closed vocabulary — the keys
#: under them are discovered from the evidence. This Literal fixes the three
#: QUESTIONS, which are a product decision, and nothing about the answers.
BoardSection = Literal["best_for", "capability", "metric"]

#: WHERE A RECORDED FIGURE CAME FROM, and the board refuses to merge the two.
#:
#: `stated` is the provider's own number — a spec sheet, a docs page, a launch
#: post. `reported` is somebody measuring it themselves. Gemini 3 Pro is 2M
#: stated and roughly 200k reported-usable; those are different facts from
#: different sources, and averaging them produces a number nobody measured
#: (rule 3). So the figure carries its basis or it is not recorded.
MetricBasis = Literal["stated", "reported"]

#: WHOSE claim a quote is. Supplies `evidence_tier`; see `ModelRef.speaking`.
#:
#: The three values are the golden set's, not this file's. Each one is the
#: residue of a disagreement two people had over real rows, and the derivation
#: is in `docs/measurements/extraction-baseline-two-labellings.md` §5.
Speaking = Literal[
    "own-experience",
    "vendor-about-own-product",
    "relayed-from-elsewhere",
]

#: How much thinking the model was asked to do. Bands from
#: `contract/conditions.yaml`; `unknown` is NOT here on purpose, because
#: omitting the field is how you say the document did not state it, and having
#: two ways to say the same thing loses the distinction rule 6 protects.
ReasoningEffort = Literal["off", "low", "medium", "high", "max", "auto"]

MAX_QUOTE_CHARS = 200


class ModelRef(BaseModel):
    """Which model the claim is about, how sure we are, and whose claim it is.

    `speaking` IS REQUIRED AND ITS EVIDENCE IS ASYMMETRIC. Recorded here rather
    than only in the proposal, because the field enforces a distinction whose
    two halves are not equally checked:

        own-experience            8 of 8 by one labeller, and 4 of 5 where both
                                  answered.  CORROBORATED.
        vendor-about-own-product  4 of 4 by ONE labeller, on four rows drawn
                                  from ONE announcement thread. The second
                                  labeller left all four blank.  NOT
                                  CORROBORATED.
        relayed-from-elsewhere    used once, by the labeller who did not use
                                  `vendor-about-own-product` at all.

    **So the field is built on the stronger half and enforces the weaker one.**
    That is a deliberate choice and not an oversight: `vendor-about-own-product`
    is the value that changes a weight sixfold (see the tier mapping in
    `contract/harvest.yaml`), and it is the value with one reader.

    What that means in practice: a disagreement about a `vendor-about-own-product`
    label is not yet evidence that the model got it wrong, because nobody has
    established what right looks like on more than four rows. The golden set has
    to grow before this field's accuracy can be argued about.
    `docs/proposals/for-engineer-2-a-speaking-field-on-modelref.md` §4.
    """

    surface: str = Field(description="exactly as the human wrote it")
    resolved_version_id: str | None = None
    specificity: Specificity
    resolution_confidence: float = Field(ge=0.0, le=1.0)
    speaking: Speaking = Field(
        description=(
            "WHOSE claim this is, not whether it is true. Required — a claim "
            "without one cannot be audited for provenance, which is the state "
            "every claim currently in the table is in.\n\n"
            "own-experience: the writer is reporting what happened when THEY "
            "used the model — their run, their session, their bug. "
            "\"I had Codex optimize it and got it down to around 35 seconds\".\n"
            "vendor-about-own-product: the writer is the vendor, or speaking "
            "for it, describing their own model — an announcement, a model "
            "card, a release post. \"exceptional performance in software "
            "engineering\", lifted out of a launch post.\n"
            "relayed-from-elsewhere: the writer is repeating a claim somebody "
            "else made — a benchmark, a model card, another post. A citation is "
            "the tell: \"gives 10%+ better results on SWE-Bench (p 255 of the "
            "model card pdf)\".\n\n"
            "A VERBATIM QUOTE FROM AN ANNOUNCEMENT IS vendor-about-own-product "
            "OR relayed-from-elsewhere, NEVER own-experience, however exactly "
            "it is quoted. Quote verification cannot catch that mistake — the "
            "sentence really is in the text — so this field is the only place "
            "it can be caught."
        )
    )


class Conditions(BaseModel):
    """What makes claims comparable.

    "Tool calling is unreliable" means something different at 40 tools than at
    5. Without these we would be stacking incomparable statements and calling
    the result consensus.

    Every field is optional, because a human writing a forum post owes us
    nothing. Absent means absent — never guessed into a band.

    **THIS OBJECT IS WHERE MISFILED VALUES LAND, and the field's NAME was the
    cause.** Three times in one week the extractor put a string into
    `structured_mode`, a `bool | None` — `'xhigh'` twice, `'auto mode'` once,
    the last costing four claims on a post about a feature called auto mode.

    Two fixes were tried and only the second worked, which is the finding:

      1. ADD `reasoning_effort`, with a description naming `'auto mode'` as its
         own example. The misfiling continued unchanged — 3 of 4 claims, three
         draws out of three, with `reasoning_effort` left null every time.
      2. RENAME `structured_mode` to `schema_enforced`, changing nothing else.
         Misfiling stopped dead and `reasoning_effort` came back `'auto'` on 4
         of 4, in all three draws. Removing the field entirely did the same.

    So the value was not going to the nearest-shaped slot. It was going to the
    slot whose NAME matched the words in the document — "auto mode" to the only
    field ending in `_mode`. **A field name is a stronger instruction than any
    field's description**, including the description of the field that should
    have won, and including a pointer in the wrong field's own description.
    That qualifies the rule in
    `docs/measurements/a-constraint-not-in-the-description-is-invisible.md`:
    the description is necessary and it is not sufficient.

    Naming consequence, and it is the actionable half: **do not name a field
    after a word that appears in the corpus in another sense.**
    `docs/measurements/the-effort-dimension.md`.
    """

    tool_count: int | None = None
    context_size: int | None = Field(default=None, description="input tokens, if stated")
    schema_enforced: bool | None = Field(
        default=None,
        description=(
            "was PROVIDER-SIDE SCHEMA ENFORCEMENT on — true or false only, and "
            "only about JSON/tool-schema validity being guaranteed at the API "
            "layer. If the document names a mode, a tier or an effort setting, "
            "that is `reasoning_effort`, not this."
        ),
    )
    reasoning_effort: ReasoningEffort | None = Field(
        default=None,
        description=(
            "How much thinking the model was asked to do, IF THE DOCUMENT SAYS. "
            "Leave it out otherwise — do not infer it from how slow or how "
            "thorough the model sounds.\n\n"
            "off / low / medium / high / max — the tier that was selected. "
            "Vendor names fold onto these: 'minimal' is off, 'xhigh' is max.\n"
            "auto — the provider chose the effort rather than the user, e.g. a "
            "router or an 'auto mode'. This is NOT the same as leaving the field "
            "out: 'the setting was auto' is a fact about the run, 'the field is "
            "absent' is a fact about the document.\n\n"
            "This matters because the same model at low and at max effort "
            "differs more than two different models at the same effort, so a "
            "latency or reasoning claim without it cannot be compared to one "
            "that has it."
        ),
    )
    framework: str | None = Field(default=None, description="LangChain, raw API, ...")
    hosted_by: str | None = Field(
        default=None,
        description="for open weights, latency and price belong to the HOST, not the model",
    )
    domain: str | None = None


class BoardEntry(BaseModel):
    """One board section this quote belongs on, AS DISCOVERED — not as chosen.

    THIS CLASS IS THE POINT OF THE CLASSIFIER. There is no closed list of jobs,
    capabilities or metrics anywhere for it to pick from: it NAMES what the
    evidence discussed. The demo board is why. Its capability section carries
    `vision`, `multimodal` and `function-calling`, and none of those three
    appears in `contract/capabilities.yaml` — so a closed vocabulary would have
    silently dropped a third of the board that was designed by hand.

    `contract/board_surfaces.yaml` still exists, and holds EXEMPLARS rather than
    a vocabulary: samples that calibrate how broad a section should be and how a
    name reads. Matching one is fine. Finding something absent from all of them
    is the expected outcome, not an error.

    THE THREE SECTIONS ARE EQUAL. `best_for`, `capability` and `metric` are three
    questions of the same weight asked of the same corpus, and a quote answering
    two of them produces two entries. Nothing here ranks them, and no entry is a
    fallback for another.

    WHAT THIS DELIBERATELY DOES NOT CARRY: no evidence state (verified /
    contested / not discussed), no rank, no pick, no score. Those are counted
    across independent reports, and this object describes ONE quote from ONE
    thread — the model cannot see the denominator, so it must not appear to.
    """

    section: BoardSection = Field(
        description=(
            "Which of the three board sections this entry is for.\n\n"
            "best_for   a TASK somebody runs. It must complete \"I need a model "
            "to ___\" — a coding agent, RAG over their docs, translating.\n"
            "capability ONE NAMED BEHAVIOUR a model does or fails at, defined "
            "the same way for every model so two reports can be compared.\n"
            "metric     a MEASURED AXIS WITH A UNIT, where the text states a "
            "figure. Requires `unit`, `value_verbatim` and `basis`."
        )
    )
    slug: str = Field(
        description=(
            "lowercase, hyphen-separated, no version numbers, no vendor names — "
            "\"function-calling\", \"coding-agent\", \"time-to-first-token\".\n\n"
            "THIS IS THE GROUPING KEY, and it is the whole reason an open "
            "vocabulary can work: two threads that discussed the same thing must "
            "reduce to the same slug or the board grows two sections where there "
            "is one. So prefer the plainest, most common form of the term. Code "
            "normalises case and spacing; it cannot decide that \"tool-calling\" "
            "and \"function-calling\" were one idea."
        )
    )
    name: str = Field(
        description=(
            "Two to four words, title case — the term an engineer would type. "
            "\"Function calling\", never \"The ability to call functions "
            "correctly\". This is the heading the board renders."
        )
    )
    definition: str = Field(
        description=(
            "ONE SENTENCE stating what the board should count as this section — "
            "the test a report has to meet, not a description of this one quote. "
            "It is what makes a claim on one model page comparable with a claim "
            "on another, so name the threshold or the first-attempt condition "
            "where there is one: \"emits a valid call to a declared tool, "
            "first attempt, with no repair pass\"."
        )
    )

    #: ── metric-only fields ────────────────────────────────────────────────
    unit: str | None = Field(
        default=None,
        description=(
            "REQUIRED when section is metric. What the figure is measured in — "
            "\"milliseconds\", \"USD per 1M tokens\", \"tokens\", \"percent "
            "resolved\". An axis with no unit is not a metric."
        ),
    )
    value_verbatim: str | None = Field(
        default=None,
        description=(
            "REQUIRED when section is metric. THE FIGURE EXACTLY AS THE TEXT "
            "WRITES IT — \"300ms\", \"$0.27/M\", \"about 200k\", \"~35 seconds\".\n\n"
            "COPY IT, NEVER COMPUTE IT. Do not convert a unit, do not normalise, "
            "do not divide a total by a count, do not average two figures, do not "
            "resolve \"about 200k\" into a number. A figure you calculated is a "
            "number nobody measured and rule 3 forbids it reaching a page — code "
            "converts afterwards, from the characters you copied. KEEP THE HEDGE "
            "IF THE WRITER HEDGED: \"about 200k\" is the finding; the precise "
            "number is a claim they did not make."
        ),
    )
    #: ⚠ TWO FIELDS THAT EXIST TO BE CHECKED, NOT TO BE TRUSTED.
    #:
    #: A metric figure needs four things true together, and only two were ever
    #: verifiable: that it is a quantity, and that it appears in its own quote.
    #: The other two — that it belongs to THIS model and THIS axis — were asked
    #: for and never shown, so nothing could check them.
    #:
    #: Measured 2026-09-18 over 440 stored figures: nine different benchmarks
    #: sat under one `swe-bench` slug (SWE-bench Verified, SWE-Bench Pro,
    #: Terminal-Bench 4.0, AutomationBench, CursorBench 3.2.0, OSWorld-2.0,
    #: DeepSWE v1.1, "the hard biology set"), and 58.2% of figures had a quote
    #: naming no model at all.
    #:
    #: ⚠ BOTH ARE OPTIONAL, AND THE FIRST VERSION SAID "REQUIRED" WHILE ALSO
    #: SAYING "LEAVE THIS EMPTY". Measured on the first run that asked for them:
    #: 22 metric figures, 0 ABSENT and 19 naming an axis the quote does not
    #: contain. The extractor was never allowed to say "the quote names none",
    #: so it named something every time - 'API pricing' for a quote reading
    #: "Input: $10 per million tokens", 'GPT-6 Astra' for one reading "Astra".
    #:
    #: A field that cannot be left empty is a field that will be guessed, and a
    #: guess here is indistinguishable from a copy until code checks it. Empty
    #: is now stated first, and stated as correct.
    #:
    #: ⚠ RULE 10. COPYING A PREFIX SPLITS AN AXIS IN TWO. Measured 2026-09-21 over
    #: the 290 published figures: one model's 97.1% was filed under `aime` from
    #: the quote "97.1% on AIME 2026 math" and under `aime-2026` from
    #: "97.1% on AIME 2026". Same model, same figure, same benchmark, two axis
    #: pages - because the copy stopped at different depths and BOTH copies
    #: really are in their quotes, so the substring check passes either way.
    #:
    #: A MACHINE CANNOT FINISH THE NAME FOR YOU, WHICH IS WHY THIS IS ASKED OF
    #: THE MODEL. `axis_specificity` already detects a name that continues, and
    #: on the same 290 figures it fired 5 times - of which 3 were the SCORE
    #: rather than the name (`CyberGym 84.5`, `ExploitBench 54.4`). Extending
    #: the copy automatically would invent three axes named after measurements
    #: to repair two. Telling a year from a score is a reading task, so it is
    #: asked here and reported as a weight there (rule 8).
    #:
    #: THE FIX IS THE ONE THAT ALREADY WORKS HERE. `value_verbatim` is reliable
    #: not because its instruction is emphatic — it is, and 10% of figures still
    #: were not in their quote — but because code can check the copy against the
    #: text. So these ask for the same thing: COPY THE WORDS, and code verifies
    #: them the same way. A field nothing can check is a field that goes wrong
    #: eventually and silently.
    axis_verbatim: str | None = Field(
        default=None,
        description=(
            "OPTIONAL, and empty is a correct answer. Most quotes carrying a "
            "figure do not name a benchmark, and those must be left empty. "
            "COPY, NEVER NAME. If the quote names a benchmark or axis, copy it "
            "character for character from the quote: 'SWE-bench Verified', "
            "'Terminal-bench 4.0', 'OSWorld-2.0'. Code checks that what you "
            "write appears in the quote and discards anything else, so there is "
            "nothing to gain by filling this in. "
            "COPY THE WHOLE NAME, INCLUDING A VERSION OR YEAR THAT IS PART OF "
            "IT. 'AIME 2026', not 'AIME'. 'Terminal Bench 2.1', not "
            "'Terminal Bench'. 'OSWorld-2.0', not 'OSWorld'. A truncated "
            "name is a DIFFERENT axis from the full one - the board filed one "
            "model's 97.1% under 'AIME' and the same model's 97.1% under "
            "'AIME 2026', as two benchmarks, because two quotes were copied to "
            "different depths. "
            "BUT STOP AT THE NAME. The number that follows a benchmark is the "
            "SCORE, not part of what it is called: in 'CyberGym 84.5%' the "
            "axis is 'CyberGym', and in 'ExploitBench 54.4% vs Mythos 5' it "
            "is 'ExploitBench'. A year and a version belong to the name; a "
            "measurement does not. If you cannot tell which you are looking "
            "at, copy the shorter name. "
            "LEAVE IT EMPTY when the quote names no benchmark. 'Input: $10 per "
            "million tokens' names none — 'API pricing' is a category you "
            "inferred, not a name the text wrote, and it is worse than empty. "
            "Do not expand an abbreviation, do not add a version the text did "
            "not write, and never substitute the better-known benchmark you "
            "think was meant: a Terminal-bench figure filed as SWE-bench is a "
            "wrong number on a page, not a near miss. "
            "An unnamed axis is a fact about the evidence; a guessed one is a "
            "fact about nothing."
        ),
    )
    subject_verbatim: str | None = Field(
        default=None,
        description=(
            "OPTIONAL, and empty is a correct answer. "
            "COPY, NEVER NAME. If the quote names the model this figure is "
            "about, copy it exactly as the quote spells it. Write 'Astra' if "
            "the quote says Astra — do NOT expand it to 'GPT-6 Astra', even "
            "though that is the fuller name, because code checks your copy "
            "against the quote and an expansion is not a copy. "
            "LEAVE IT EMPTY when the quote names no model — a table cell "
            "reading '1M context' names none. The figure is then recorded as "
            "unattributed, which is honest. Naming the model the thread happens "
            "to be about would attach somebody else's number to it, and that is "
            "the defect this field exists to end. "
            "Where a quote compares several models, give the one THIS figure "
            "belongs to and no other."
        ),
    )

    basis: MetricBasis | None = Field(
        default=None,
        description=(
            "REQUIRED when section is metric.\n\n"
            "stated   the PROVIDER says so — spec sheet, docs, model card, "
            "launch post. An advertised ceiling.\n"
            "reported the WRITER measured it — their run, their timing, their "
            "bill.\n\n"
            "Never merged, so a guess here corrupts the one distinction the "
            "metric pages exist to show. It usually agrees with "
            "`model_ref.speaking`: own-experience is reported, "
            "vendor-about-own-product is stated."
        ),
    )

    @model_validator(mode="after")
    def _a_metric_brings_its_figure(self) -> BoardEntry:
        """A metric entry without a unit, a figure and a basis is an empty row.

        Enforced here rather than trusted from the prompt, for the reason the
        rest of this file exists: the prompt asks and the schema guarantees. All
        three would otherwise validate and then render as a blank cell, which is
        the silent-absence shape rule 4 is about — and on this board a blank is
        already meaningful, so a spurious one is not a harmless gap.

        Asymmetric on purpose: a `unit` supplied on a non-metric entry is not an
        error. It costs nothing, and rejecting a batch over a surplus field is
        how the old length check on `quote_offset` used to lose five claims in
        six.
        """
        if self.section != "metric":
            return self
        missing = [
            field
            for field, value in (
                ("unit", self.unit),
                ("value_verbatim", self.value_verbatim),
                ("basis", self.basis),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"a metric entry is missing {', '.join(missing)}: a metric row is "
                "the figure, the unit it is in, the axis it sits on, and whether "
                "it was stated or measured. Without all of them it renders as an "
                "empty cell. If the quote names an axis but states no figure, it "
                "is a capability entry, not a metric one."
            )
        return self


#: Written once here rather than inline, because it is long and the field it
#: describes is the classifier's entire output channel.
_BOARD_ENTRIES_DESC = (
    "EVERY board section this quote belongs on — DISCOVERED, not chosen from a "
    "list. One entry per section; a quote answering two questions produces two "
    "entries.\n\n"
    "Ask all three questions of the quote and add an entry for each one the "
    "quote itself answers:\n"
    "  best_for   — does it say what they were TRYING TO DO?\n"
    "  capability — does it say how the model BEHAVED?\n"
    "  metric     — does it state a FIGURE on a measured axis?\n\n"
    "Worked example. \"switched our agent to Flash, ttft went from 900ms to "
    "300ms\" produces THREE entries: best_for/coding-agent, "
    "capability/time-to-first-response, and metric/time-to-first-token with "
    "value_verbatim \"300ms\" and basis reported.\n\n"
    "A quote can legitimately produce ONE entry. \"it is $0.27 per million "
    "output\" is a metric and nothing else — no behaviour is reported and no "
    "task is named — and that is a complete, useful record. Do not invent a "
    "capability to pad it out.\n\n"
    "Never empty: a claim that belongs on no section cannot be shown, so it is "
    "not a claim. Put its quote in `unclassified` instead."
)


class ExtractedClaim(BaseModel):
    """One claim, as the extractor proposes it.

    Offsets index into `flattened_text` — the exact string the extractor was
    given — NOT into the raw source document. Resolution to the source happens
    in verify.py, step 2.
    """

    source_comment_id: str = Field(
        description="which comment inside the flattened thread this came from"
    )
    model_ref: ModelRef

    #: THE LEGACY CLOSED KEY, and it does not decide what the board shows.
    #:
    #: This is a key from `contract/capabilities.yaml` — the ratified twelve. It
    #: feeds the CELL path (`judge/pipeline.py`, `judge/store/claims.py`,
    #: `judge/vet/weight.py` all index cells by `capability_key`, and
    #: `bucket_for` looks the key up to find its failure mode).
    #:
    #: WHAT IT IS NOT is the board's capability section. That comes from
    #: `board_entries` below, which is discovered and unbounded. Keeping the two
    #: apart is what lets the board show `vision` and `multimodal` — which the
    #: ratified twelve do not contain — without either inventing a ratified key
    #: or dropping the evidence.
    #:
    #: ⚠ IT WAS `capability: str` AND IT ASKED FOR THE CLOSEST KEY. Measured
    #: 2026-09-22 over all 1,385 stored claims: on a 60-claim read the chosen
    #: key did not name what the quote described in **38 of 60**, and 1,194 of
    #: the claims were written after the column became nullable with **zero**
    #: NULLs. `docs/measurements/the-key-that-takes-anything-2026-09-22.md`.
    #:
    #: `minimaxir.com/2025/07/llms-identify-people/` produced 12 claims about
    #: naming people in photographs, all 12 under `extraction.faithfulness`,
    #: and five of the 21 cells on that key are sourced entirely from
    #: facial-recognition quotes. Nobody discussed typed-field extraction.
    #:
    #: ⚠ TWO CHANGES, AND THE RENAME IS THE LOAD-BEARING ONE. `Conditions`'
    #: docstring records the experiment: adding `reasoning_effort` with a better
    #: description changed nothing, and renaming `structured_mode` to
    #: `schema_enforced` stopped misfiling dead — **a field name is a stronger
    #: instruction than any field's description.** A field named `capability`
    #: could not be left empty, because `capability` is also the board's
    #: discovered section, `contract/capabilities.yaml` and
    #: `capability_candidate`: the prompt spends most of its length teaching the
    #: OPEN vocabulary under that exact word. `legacy_score_key` names what it
    #: feeds and claims nothing about capability.
    #:
    #: `None` is now a correct answer and the common one. A claim with no key is
    #: written with `capability_key` NULL, no `claim_weight` row and no cell —
    #: see `judge/pipeline.py`, which keeps the claim and skips the cell.
    legacy_score_key: str | None = Field(
        default=None,
        description=(
            "OPTIONAL, and empty is a correct answer - the common one. A key "
            "from contract/capabilities.yaml, which feeds an older scoring "
            "path and is NOT what the board displays; the board reads "
            "`board_entries`.\n\n"
            "LEAVE IT EMPTY unless one of the ratified keys names what the "
            "quote is about. DO NOT PICK THE CLOSEST. A key that is merely "
            "nearest files this quote into a count about something the writer "
            "never discussed - five people discussing one model's vision and "
            "Chinese OCR were counted as '5 people mentioned following "
            "instructions', because `instruction.adherence` was the nearest of "
            "twelve.\n\n"
            "Where no key names it, leave this empty AND propose the missing "
            "key in `proposed_capabilities`. An empty key is a fact about the "
            "vocabulary; a nearest-fit key is a fact about nothing."
        ),
    )

    #: ── WHAT THE BOARD ACTUALLY RENDERS ───────────────────────────────────
    board_entries: list[BoardEntry] = Field(
        min_length=1,
        description=_BOARD_ENTRIES_DESC,
    )

    polarity: Polarity
    severity: Severity | None = Field(
        default=None,
        description=(
            "PHRASE SELECTION ONLY. Never averaged, never summed. A float here "
            "would be fake precision, and it would invite someone to average it."
        ),
    )
    comparison_target: str | None = Field(
        default=None, description="set when the quote compares two models"
    )
    pain_points: list[str] = Field(default_factory=list)

    conditions: Conditions = Field(default_factory=Conditions)

    quote: str = Field(
        max_length=MAX_QUOTE_CHARS,
        description=(
            "VERBATIM text from the source. No paraphrase, no ellipsis, no "
            f"repair.\n\nAT MOST {MAX_QUOTE_CHARS} CHARACTERS — that is roughly "
            "one sentence. Count before you answer. A longer quote is rejected "
            "and takes every other claim in this answer down with it.\n\n"
            "If the passage you want is longer, pick the ONE SENTENCE that "
            "carries the claim — and it may be the second sentence rather than "
            "the first, because the measurement is often at the end. Do not "
            "trim or abbreviate to fit: the quote is checked by exact substring "
            "match, so an edited quote fails, and a truncated one can lose the "
            "part that carried the claim."
        ),
    )
    quote_offset: tuple[int, int] = Field(description="[start, end) into flattened_text")

    relevance: Relevance
    has_repro_steps: bool = False
    has_numbers: bool = False
    is_sarcastic: bool = Field(
        default=False,
        description=(
            "true DISCARDS the claim. Inverting sarcasm programmatically is "
            "unreliable; dropping it is honest."
        ),
    )

    @model_validator(mode="after")
    def _offsets_are_sane(self) -> ExtractedClaim:
        """The offset is a HINT, and the length no longer has to match.

        This required `end - start == len(quote)` and rejected the whole batch
        when it did not. The first live run failed here on five of six claims,
        by one to three characters each - because A LANGUAGE MODEL CANNOT COUNT
        CHARACTERS, and asking it to was a design error rather than a defect in
        its answer. The quotes themselves were correct.

        So the model identifies the quote and CODE locates it: `locate()` in
        the runner searches the flattened text and derives the true span. That
        is strictly more rule-1 compliant than before - the model no longer
        supplies a position anything trusts, and a span code computed is a span
        code verified.

        What remains checked here is only that the hint is not nonsense: a
        forward range at a plausible position. A wrong-by-two hint is fine and
        is exactly what arrives.
        """
        start, end = self.quote_offset
        if start < 0 or end <= start:
            raise ValueError(f"quote_offset {self.quote_offset} is not a forward range")
        return self

    @property
    def polarity_contradicts_pain(self) -> bool:
        """A stated pain point makes the claim negative — anything else contradicts it.

        `pain_points` is the model's own list of problems the author raised. A
        problem is a criticism, so a claim that lists one and is NOT `negative`
        (it says `positive` or `neutral`) contradicts itself, and we cannot
        trust the SIGN it gave. Discarded rather than flipped — for exactly the
        reason the prompt discards sarcasm rather than inverting it: choosing
        which of two contradictory signals to believe is the same guess, one
        field over.

        Why this belongs in CODE and not the model (rule 2): it is a purely
        structural contradiction between two fields already on the row. No
        judgement about the text is made here — only that two of the model's own
        answers cannot both be right. That is the one thing code is allowed to
        decide.

        It caught two real claims on the live board — "the API has zero
        authorisation checks…" and "Claude Haiku 4.5 was the easiest to attack",
        both `positive` with `pain_points: ['security']` — a security complaint
        read as praise, which for a board whose job is surfacing criticism is
        the most dangerous direction to be wrong in. Extended to `neutral` with
        the third polarity: a pain point is not a neutral observation either.
        """
        return bool(self.pain_points) and self.polarity != "negative"


class CapabilityProposal(BaseModel):
    """A capability the writer describes that NONE of the known keys name.

    Capability discovery, and it is bound by the same two rules as a claim. Rule
    2: the extractor PROPOSES a key, a human RULES on it (the `capability_candidate`
    table), so the vocabulary never grows by a model's say-so. Rule 1: it carries
    a verbatim quote, checked by exact substring like every other quote, so a
    proposal cannot be conjured from nothing.

    Distinct from `unclassified`, which is a quote that fits nothing and which the
    model could not even name — this one comes with a proposed key and a
    definition, so it is evidence a specific capability is missing rather than
    just that some capability is.
    """

    proposed_key: str = Field(
        description=(
            "a NEW dotted key in the style of the vocabulary — e.g. "
            "'output.verbosity' or 'reasoning.overthinking'. NOT one of the "
            "existing keys; if an existing key fits, this is a claim, not a proposal."
        )
    )
    #: WHICH VOCABULARY IS MISSING THE KEY. Defaults to `capability` because
    #: that was the only vocabulary when this class was written, and every row
    #: already stored is a capability proposal — so the default keeps
    #: `store_proposals` reading old rows correctly rather than making a
    #: missing field look like a deliberate answer (rule 6).
    section: BoardSection = Field(
        default="capability",
        description=(
            "which vocabulary lacks this key: capability, best_for (a job "
            "nobody named) or metric (an axis nobody records). A proposed "
            "job.* or metric.* key belongs to its own list, and saying which "
            "one is what makes the proposal actionable."
        ),
    )
    definition: str = Field(description="one line: what this capability measures")
    quote: str = Field(
        max_length=MAX_QUOTE_CHARS,
        description=(
            "VERBATIM text that describes the capability. Checked by exact "
            "substring, so no paraphrase — the same rule as a claim's quote."
        ),
    )


class ExtractionResult(BaseModel):
    """Everything the extractor returns for one flattened thread.

    A thread mentioning three models produces claims per model. A thread with
    nothing extractable returns an empty list and a reason — never an invented
    claim to fill the silence.
    """

    claims: list[ExtractedClaim] = Field(default_factory=list)
    proposed_capabilities: list[CapabilityProposal] = Field(
        default_factory=list,
        description=(
            "CAPABILITY DISCOVERY. When a quote describes a real, recurring thing "
            "a model does or fails at that NONE of the keys name, propose a new "
            "key here with a one-line definition and the quote — rather than "
            "forcing it into the nearest key (which fabricates consensus) or "
            "dropping it into `unclassified` unnamed (which loses what it was "
            "about). This is how the vocabulary grows on evidence. An empty list "
            "means every quote fit an existing key; it is not a default."
        ),
    )
    no_claim_reason: str | None = Field(
        default=None,
        description="required when claims is empty: why this thread yielded nothing",
    )
    unclassified: list[str] = Field(
        default_factory=list,
        description=(
            "BEFORE YOU ANSWER, CHECK EVERY CLAIM YOU MADE. For each one, ask: "
            "does the capability key you chose actually name what the quote is "
            "about? If it does not, DO NOT pick the nearest one — remove that "
            "claim and put its quote here instead.\n\n"
            "This list is how the capability vocabulary grows. A quote that "
            "belongs here and gets forced into an existing key is worse than a "
            "missing claim: it counts toward consensus about something the "
            "writer never discussed, and nobody learns the key is missing.\n\n"
            "Concretely: if a quote is about how many tokens a model spends, "
            "how long its output is, or how much it over-thinks, there is NO "
            "KEY FOR THAT in the vocabulary. `ops.latency_ttft` is time to "
            "first token and `over_refusal` is declining to answer. Neither is "
            "verbosity. Such a quote goes here.\n\n"
            "An empty list means you checked and every claim fits. It is not a "
            "default."
        ),
    )

    @model_validator(mode="after")
    def _silence_is_explained(self) -> ExtractionResult:
        if not self.claims and not self.no_claim_reason:
            raise ValueError(
                "empty extraction must state no_claim_reason — silence needs a reason, "
                "not an empty result that looks like a failure"
            )
        return self
