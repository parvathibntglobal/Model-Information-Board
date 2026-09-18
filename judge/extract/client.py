"""The one place in this lane that talks to a language model.

`deepseek/deepseek-v4-flash` through OpenRouter, decided rather than selected
(NFR-9). One extractor, no fallback, so a silent regression is detected rather
than absorbed - which is why the golden set matters more here than it would
with two.

WHY THIS IS A PROTOCOL AND A FAKE

The key arrives later than the code. Everything that matters about extraction -
the prompt, the schema, the retry, the verification - is testable without a
network call, and building it against a fake means the key becomes a config
value rather than the start of the work.

It is also the only honest way to test the failure paths. A model that returns
malformed JSON twice, or a quote that does not exist in the source, is a
scenario you cannot request from a real endpoint and cannot skip testing.

WHAT THIS DELIBERATELY DOES NOT DO

No retry on a network error, no backoff, no circuit breaker. Extraction is a
nightly batch: a failed document is a document to run tomorrow, and a client
that keeps trying is how a budget cap gets missed. The only retry here is on a
schema violation, and it is bounded at one.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

#: NFR-9. Pinned in config so replacing it is a config change; nothing
#: downstream knows which model produced a claim beyond `pipeline_version`.
#: Switched from `google/gemini-2.5-flash` 2026-09-01 after an A/B on R1's
#: threads: clean schema/tool-calls, 100% quote-verify, no fabrication —
#: docs/measurements/extractor-ab-deepseek-v4-flash-vs-gemini.md. Undated alias;
#: pin a dated build (…-0731) if a run needs to be exactly reproducible.
#: THE AGREED EXTRACTOR. OpenRouter resolves this undated slug to the 0423
#: snapshot (2026-04-24) and it is pinned there, so the vendor cannot move it
#: underneath a run. Moving to 0731 costs a PIPELINE_VERSION bump and a
#: re-extraction of ~531 threads at ~$1.18 - the fork is the cost, not the
#: money. We are on 0423 on purpose; see
#: `docs/proposals/the-blended-cells-and-what-extractor-model-means.md` §6.
#:
#: Changing this line changes what `claim.extractor_model` records on every row
#: written afterwards, so it is a provenance change and not a constant edit.
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def extractor_model() -> str:
    """`EXTRACTOR_MODEL`, or the agreed extractor.

    THE DEFAULT IS THE CHOICE, NOT A GUESS, and that distinction is the whole
    of this docstring. `DEFAULT_MODEL` is `deepseek/deepseek-v4-flash`, which
    OpenRouter resolves to the **0423** snapshot - pinned, not floating, because
    `deepseek/deepseek-v4-flash-0731` and `~deepseek/deepseek-v4-flash-latest`
    both exist separately and a route would be redundant otherwise. Staying on
    0423 is a decision with a date on it, recorded in
    `docs/proposals/the-blended-cells-and-what-extractor-model-means.md` §6.

    So writing it into `claim.extractor_model` records the agreed extractor
    rather than inventing one. THIS BRIEFLY REFUSED ON UNSET INSTEAD, and that
    was wrong: it answered a failure that had not happened. The gemini mixture
    on the board was not produced by an unset variable. It was produced by a
    machine with this variable EXPLICITLY SET to gemini, which a
    refuse-on-unset check cannot see and does not touch.

    WHAT THIS DOES NOT CHECK, AND WHAT WOULD HAVE CAUGHT IT. Nothing here
    compares the value against the extractor the team agreed on - only against
    the registry, which contains every polled model including gemini. The check
    that would have refused `LAPTOP-TA28DHTF` is a comparison with a RECORDED
    CHOICE, and rule 5 says where a recorded choice lives: `contract/`, not a
    Python literal. Proposed in
    `docs/proposals/the-agreed-extractor-belongs-in-contract.md`, not taken.

    ONE FUNCTION, SO THE CALL AND THE RECORD CANNOT DIVERGE. This is the part
    worth keeping whatever the default is. `client.py` used to read the variable
    with `DEFAULT_MODEL` as its fallback and `cli.py` read it again with the
    literal string as its own, and they agreed by coincidence. Had they stopped
    agreeing, the call would use one model and the claim would record the other,
    and nothing would be wrong enough to notice because both values are
    plausible model ids.

    IT IS STILL WHAT WE ASKED FOR, NOT WHAT RAN. `Completion.model` carries what
    the provider reported and NOTHING READS IT (`judge/pipeline.py` sets
    `self._extractor_model` once, from here).
    """
    return (os.getenv("EXTRACTOR_MODEL") or "").strip() or DEFAULT_MODEL

#: One retry, not three. A model that violates a forced schema twice is not
#: having a bad moment, and paying for a third attempt is how a daily budget
#: disappears into documents that were never going to parse.
MAX_SCHEMA_RETRIES = 1

#: The single tool in the extraction context. An injected "use the web tool"
#: has nothing to reach for, which is defence 3 in `prompt.py`.
TOOL_NAME = "emit_claims"


class ExtractorUnavailable(RuntimeError):
    """The provider answered, and not with a completion.

    Kept distinct from a schema violation and from an HTTP error, because the
    three want different responses: a schema violation is retried with a
    correction, an HTTP error is retried or backed off, and this one means the
    upstream model is not answering at all and the document should be recorded
    as unattempted rather than as producing nothing.

    That distinction is rule 4 in the harvest layer: a document the extractor
    never read must not join the documents that were read and said nothing.
    """


@dataclass(frozen=True)
class Completion:
    """One model response, plus what it cost.

    `raw_arguments` is the unparsed tool-call payload. Kept as text because a
    schema violation is a thing we want to log verbatim rather than a thing we
    want to have already failed to parse.
    """

    raw_arguments: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = DEFAULT_MODEL
    #: The provider's own word for why generation stopped - `stop`, `length`,
    #: `tool_calls`, or None when nothing said.
    #:
    #: RECORDED BECAUSE A LENGTH STOP IS AN ABSENCE WE CAUSE. Measured
    #: 2026-09-14 on `devto:4586450`: one draw emitted 65,536 completion tokens
    #: - exactly the provider's 2**16 ceiling, because `max_tokens` was unset -
    #: and returned `{}` as its tool call. That is indistinguishable, in
    #: everything downstream, from a document the model read and found nothing
    #: in. Rule 4 is about not letting an absence read as a finding; this is the
    #: same rule one stage earlier, on an absence the extractor created.
    #:
    #: `None` is NOT "stop". A provider that says nothing has not said the
    #: generation completed (rule 6), and `stopped_at_ceiling` answers False for
    #: it rather than True.
    finish_reason: str | None = None

    #: ⚠ THIS FIELD EXISTS BECAUSE `finish_reason` LIED, AND IT WAS MEASURED.
    #:
    #: OpenRouter NORMALISES `finish_reason` to `"tool_calls"` whenever the
    #: answer is a tool call, and puts the upstream's own word here. Captured
    #: 2026-09-15 by forcing `max_tokens: 50` on `devto:4586450`:
    #:
    #:     "finish_reason": "tool_calls",  "native_finish_reason": "length"
    #:
    #: Reading `finish_reason` alone therefore reported a clean stop on a
    #: response that had been cut off mid-answer — and the first version of
    #: this fix did exactly that, so a 16,384-token truncation was retried and
    #: labelled `unsalvaged`. Since `tool_choice` is FORCED here, every
    #: successful extraction call is a tool call, which means `finish_reason`
    #: can never say `"length"` on this path. The check that looked right could
    #: not fire at all.
    native_finish_reason: str | None = None

    #: What we asked for, so `stopped_at_ceiling` can do arithmetic rather than
    #: trust a label. None when no bound was set.
    ceiling_tokens: int | None = None

    @property
    def stopped_at_ceiling(self) -> bool:
        """The provider cut generation off at `max_tokens`.

        THREE SIGNALS, ANY OF WHICH IS ENOUGH, because the two label-based ones
        are each known to be absent on some path:

          1. `native_finish_reason == "length"`  the upstream's own word, and
             the only label that fires on this project's forced-tool-call path.
          2. `finish_reason == "length"`         what a provider that does not
             normalise would say. Kept so this is not DeepInfra-specific.
          3. `output_tokens >= ceiling_tokens`   arithmetic, needing no
             cooperation from anybody. We asked for at most N and got N.

        (3) IS THE ONE THAT CANNOT SILENTLY STOP WORKING, which is why it is
        here even though (1) covers today's provider. A label is a promise from
        a vendor; a token count is a measurement. A model that legitimately
        emits exactly N and stops is indistinguishable from one that was cut at
        N — and calling that truncated is the conservative direction, because
        the cost of a false "we may have cut this" is a caveat, and the cost of
        a false "complete" is rule 4.

        Read by `_call_with_one_retry`, which must NOT retry this: a second call
        under the same ceiling buys the same truncation and a second bill.
        """
        if self.native_finish_reason == "length" or self.finish_reason == "length":
            return True
        return bool(
            self.ceiling_tokens
            and self.output_tokens
            and self.output_tokens >= self.ceiling_tokens
        )

    @property
    def is_empty(self) -> bool:
        return not self.raw_arguments.strip()


class ExtractionClient(Protocol):
    """Forced tool call against one schema. No free-text channel exists."""

    def complete(self, *, system: str, user: str, tool_schema: dict[str, object]) -> Completion: ...


@dataclass
class FakeClient:
    """Scripted responses, for every path a real endpoint will not produce.

    Responses are consumed in order. Exhausting them raises rather than
    repeating the last one: a test that calls more times than it scripted has
    a bug, and silently returning the previous answer would hide it.
    """

    responses: list[str] = field(default_factory=list)
    calls: list[dict[str, str]] = field(default_factory=list)

    def complete(self, *, system: str, user: str, tool_schema: dict[str, object]) -> Completion:
        self.calls.append({"system": system, "user": user})
        if not self.responses:
            raise AssertionError(
                f"FakeClient ran out of scripted responses on call {len(self.calls)}. "
                "Script one per expected call rather than letting the last repeat."
            )
        return Completion(raw_arguments=self.responses.pop(0))


@dataclass
class OpenRouterClient:
    """The real one. OpenAI-compatible, so the shape is unremarkable.

    Constructed from the environment rather than taking a key argument, so a
    key cannot be passed around in application code and end up in a log line.
    """

    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    timeout_seconds: float = 60.0
    #: A CEILING ON THE WHOLE CALL, which `timeout_seconds` is not.
    #:
    #: `httpx.Timeout` bounds IDLE time per phase. A response that trickles bytes
    #: never goes idle for the full read window, so it never expires — measured
    #: 2026-09-14 on a live run: one call ran 39 MINUTES and raised nothing, on a
    #: run whose previous 26 threads averaged 46 seconds.
    #:
    #: The comment below on `timeout=` promises "a read that goes idle past the
    #: window raises rather than hanging the batch"; that intent needs this bound
    #: to be true, because idleness and elapsed time are different measurements.
    #:
    #: 1200s, AND THE FIRST NUMBER WAS WRONG. This shipped at 300s, chosen
    #: against "the 26 threads before the hang averaged 46 seconds" - one run,
    #: and an average. @anoojntglobal-sudo then measured the distribution over
    #: 161 consecutive-thread intervals across 6 fetch logs, every one of them a
    #: thread that COMPLETED:
    #:
    #:     min 9s   p50 14s   mean 44s   p90 70s   max 917s
    #:     exceeding 300s: 4 of 161 (2.5%) - 337s, 580s, 843s, 917s
    #:
    #: So 300s sat INSIDE the distribution of success and would have abandoned
    #: four calls that did come back, the largest at 3x the cap. A ceiling
    #: belongs above the successes, not among them.
    #:
    #: ⚠ IT DOES NOT SEPARATE HANGS FROM SUCCESSES, and saying otherwise would
    #:   overclaim. The second hang was "silent >15 min, killed by pid" - a
    #:   LOWER BOUND, not a duration, because nobody waited to see how long it
    #:   would have gone. Against a 917s success that bound overlaps. What 1200s
    #:   does is clear every success ever measured here and still bound the one
    #:   hang that was measured, which ran 39 minutes.
    #:
    #: WHY GENEROUS IS NOW AFFORDABLE. The cap used to be the only thing that
    #: could end a wedged call. It is not any more: `on_progress` carries
    #: `checkpoint` into the response loop, so Stop reaches inside a call and a
    #: person watching a run does not wait for this at all. The cap is the
    #: backstop for a run nobody is watching, and a backstop that fires on 2.5%
    #: of healthy calls is worse than one that fires late.
    total_timeout_seconds: float = float(
        os.getenv("EXTRACT_TOTAL_TIMEOUT_SECONDS", "1200")
    )
    #: A CEILING ON OUTPUT, which is the thing that actually costs time.
    #:
    #: MEASURED, not chosen for roundness. Two draws of the same request against
    #: `devto:4586450`, same text, temperature 0, twenty minutes apart:
    #:
    #:     draw A     90.4s    8,963 completion tokens   40 claims   $0.00186
    #:     draw B    670.6s   65,536 completion tokens   `{}`        $0.01204
    #:
    #: 65,536 is 2**16 - the provider's own ceiling, reached because nothing
    #: here set one. The generation RATE was the same in both (102 and 98
    #: tok/s), so duration is output tokens over a constant and nothing else.
    #: The model is never slow; it either answers in ~9k tokens or runs to the
    #: ceiling and answers nothing.
    #:
    #: 16,384 is 1.8x the observed good answer. At the measured rate that bounds
    #: a degenerate call at ~170s and ~$0.003 instead of ~670s and ~$0.012.
    #:
    #: IT IS A BOUND, NOT A GATE (rule 8). Nothing is dropped for hitting it:
    #: the completion comes back with `finish_reason="length"`, the runner
    #: records `ZERO_TRUNCATED`, and the stage line names the count. Whether
    #: 16,384 is too low is a question the recorded field can answer after some
    #: runs - which is the direction rule 8 requires, the field first and any
    #: gate later on evidence.
    max_output_tokens: int = int(os.getenv("EXTRACT_MAX_OUTPUT_TOKENS", "16384"))
    #: Called while a response is arriving. MAY RAISE, and raising is the point.
    #:
    #: `Progress.checkpoint()` raises `RunStopped` when somebody has pressed
    #: Stop, and it is called from `stage()` - so during E5 the next check is the
    #: progress line for the NEXT thread. A hang INSIDE a thread never reaches
    #: one. Measured 2026-09-14: `POST /fetch/stop` answered
    #: `{"stop_requested": true, "was_running": true}`, both true, and the run
    #: continued for 39 minutes until it was killed by pid. A control that
    #: reports success and does nothing is worse than one that is absent, and
    #: the case it could not serve is the only case anyone presses it in.
    #:
    #: This client knows nothing about runs or stops. It calls a hook; whoever
    #: supplies it decides what raising means. `scripts/fetch_model.py` supplies
    #: `prog.checkpoint`.
    on_progress: Callable[[], None] | None = None

    @classmethod
    def from_env(cls) -> OpenRouterClient:
        key = os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is unset. Extraction is the only paid stage in "
                "this pipeline, so it refuses to start rather than failing per "
                "document halfway through a batch."
            )
        return cls(
            model=extractor_model(),
            base_url=os.getenv("OPENROUTER_BASE_URL", DEFAULT_BASE_URL),
            api_key=key,
        )

    def complete(self, *, system: str, user: str, tool_schema: dict[str, object]) -> Completion:
        import json as _json
        import time

        import httpx

        # STREAMED AT THE PROTOCOL LEVEL, WHICH IT WAS NOT UNTIL 2026-09-15.
        #
        # `httpx.stream` was already used here, and it bought the deadline check
        # below and nothing else, because the REQUEST did not ask for a stream.
        # A non-streamed OpenRouter response is one buffered JSON body, so the
        # only thing arriving during generation was keep-alive padding: eleven
        # bytes of whitespace every three seconds. Measured - that is the whole
        # content of the "1111 bytes received" in the two abandoned calls of
        # 2026-09-14, and 1111 is 101 x 11, the 101st beat landing at 302.8s.
        # The byte count was a reading of the clock, not of the answer.
        #
        # WHAT `stream: true` BUYS, AND IT IS NOT THE TIMEOUT. The deadline
        # already worked. It is that a degenerate loop and a long correct answer
        # are INDISTINGUISHABLE while a call is running, and repeated identical
        # fragments are obvious within seconds once tokens actually arrive. The
        # 65,536-token draw on `devto:4586450` looked exactly like the 8,963-
        # token draw that produced 40 claims, for eleven minutes.
        #
        # WHAT THIS BOUNDS, EXACTLY. The deadline covers waiting for the body.
        # Waiting for the HEADERS is still bounded by the read window instead, so
        # the true worst case is `timeout_seconds + total_timeout_seconds` rather
        # than the latter alone. Stated rather than rounded off, because a
        # ceiling that is quietly 60s higher than it claims is the same species
        # of defect as the one this fixes.
        #
        # THE DEADLINE IS NOW A BACKSTOP, NOT THE RATION. `max_output_tokens`
        # bounds generation at ~170s at the measured rate, so anything reaching
        # 300s is the provider misbehaving rather than a long document - which
        # is the state this was always meant to catch and could not, while it
        # was also the only thing standing between us and a 2**16-token bill.
        deadline = time.monotonic() + self.total_timeout_seconds
        with httpx.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            # Explicit phases rather than one float: a stalled CONNECT fails fast
            # (10s) while a legitimately slow generation still gets the full read
            # window. A read that goes idle past the window raises rather than
            # hanging the batch - the on-demand fetch's E5 had no ceiling a caller
            # could see, so a slow provider looked identical to a dead one.
            timeout=httpx.Timeout(self.timeout_seconds, connect=10.0),
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": TOOL_NAME,
                            "description": "Record every claim found in the document.",
                            "parameters": tool_schema,
                        },
                    }
                ],
                # Forced, not merely offered. The model has no route to a
                # free-text reply, which is what makes an injected instruction
                # unable to produce output that acts on anything.
                "tool_choice": {"type": "function", "function": {"name": TOOL_NAME}},
                "temperature": 0,
                "max_tokens": self.max_output_tokens,
                "stream": True,
                # WITHOUT THIS THE LEDGER SILENTLY RECORDS ZEROS. A streamed
                # response carries no `usage` block unless it is asked for, and
                # `usage.get("prompt_tokens", 0)` below would then write 0 for
                # every call - a missing measurement converted into a definite
                # one, in the flattering direction, in the only place this
                # project records what it spends (rule 6).
                "stream_options": {"include_usage": True},
            },
        ) as response:
            # THE STATUS IS CHECKED BEFORE THE STREAM IS READ. An error response
            # is a short JSON body, not an SSE stream, and iterating it as lines
            # would yield nothing recognisable and report the failure as an empty
            # answer.
            if response.status_code != 200:
                response.read()
                raise ExtractorUnavailable(
                    f"the provider returned HTTP {response.status_code}: "
                    f"{response.text[:300]!r}"
                )

            fragments: list[str] = []
            finish_reason: str | None = None
            native_finish: str | None = None
            usage: dict = {}
            model_name: str | None = None
            stream_error: object = None
            # THROTTLED, because `checkpoint()` reads a file. A streamed answer
            # arrives as hundreds of small deltas, so calling it per delta would
            # stat the disk thousands of times for one response. Once a second is
            # far faster than a person can regret pressing Stop, and costs
            # nothing.
            next_check = 0.0
            for line in response.iter_lines():
                now = time.monotonic()
                if self.on_progress is not None and now >= next_check:
                    next_check = now + 1.0
                    # Deliberately NOT wrapped: this is how a stop leaves the
                    # call, and swallowing it here would restore the defect.
                    self.on_progress()
                if now > deadline:
                    # NAMES WHAT WAS MEASURED, not a guess at the cause. With
                    # `max_tokens` set, reaching this is no longer "a long
                    # document" - so the message says how much answer had
                    # arrived, which is the number that separates a provider
                    # that stopped sending from one that is still working.
                    raise ExtractorUnavailable(
                        f"the provider was still sending after "
                        f"{self.total_timeout_seconds:.0f}s "
                        f"({sum(len(f) for f in fragments)} chars of tool-call "
                        f"arguments received); abandoned so the batch is not held "
                        f"open by one call. `max_tokens` is "
                        f"{self.max_output_tokens}, which bounds a legitimate "
                        f"answer well inside this window, so this is the provider "
                        f"rather than the document."
                    )
                if not line or line.startswith(":"):
                    continue          # SSE comment / keep-alive
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                try:
                    event = _json.loads(data)
                except ValueError:
                    continue          # a partial frame; the next one carries it
                # A PROVIDER ERROR ARRIVES INSIDE THE STREAM, as an event with
                # no `choices`. Recorded and raised after the loop rather than
                # here, so whatever already arrived is still counted.
                if "error" in event and not event.get("choices"):
                    stream_error = event["error"]
                    continue
                if event.get("model"):
                    model_name = event["model"]
                if event.get("usage"):
                    usage = event["usage"]
                for choice in event.get("choices") or []:
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]
                    # The upstream's own word, which OpenRouter overwrites in
                    # the field above. See `Completion.native_finish_reason`.
                    if choice.get("native_finish_reason"):
                        native_finish = choice["native_finish_reason"]
                    delta = choice.get("delta") or {}
                    for call in delta.get("tool_calls") or []:
                        piece = (call.get("function") or {}).get("arguments")
                        if piece:
                            fragments.append(piece)

        if stream_error is not None:
            raise ExtractorUnavailable(
                f"the provider reported an error mid-stream: {stream_error!r}"
            )

        arguments = "".join(fragments)
        model_name = model_name or self.model

        # RECORDED HERE, BECAUSE THIS IS WHERE THE USAGE IS. E5 has been calling
        # a paid model since August and writing nothing to the ledger - the only
        # caller of `spend_ledger.record` was the Ask box - which is why the
        # usage panel showed one model and had to derive the other from the
        # provider's key total minus what it knew. Next to the response is the
        # only place that cannot forget, and `record` swallows write failures so
        # a full disk cannot end a corpus run.
        #
        # A TRUNCATED ANSWER IS STILL BILLED, so it is recorded here too, before
        # any of the truncation handling downstream. The two abandoned calls of
        # 2026-09-14 wrote no ledger row at all, because the old code reached
        # this line only on success - roughly 30,000 generated tokens each,
        # invisible in our own figures.
        from judge import spend_ledger

        spend_ledger.record(
            stage=spend_ledger.STAGE_EXTRACT,
            model=model_name,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )
        return Completion(
            raw_arguments=arguments,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            model=model_name,
            finish_reason=finish_reason,
            native_finish_reason=native_finish,
            ceiling_tokens=self.max_output_tokens,
        )


#: Where the closed capability vocabulary lives in the generated schema.
#:
#: Exactly one node, asserted rather than assumed — see `_close_capability`.
_CAPABILITY_PATH = ("properties", "claims", "items", "properties", "capability")


def _close_capability(schema: dict, capability_keys: list[str]) -> dict:
    """Put the ratified keys in the schema as an `enum`, not only in the prompt.

    THE CLOSURE WAS PROSE UNTIL 2026-09-14 AND IT COST TWO RUNS. The field is a
    bare `capability: str`, and the only thing that said "closed" was a line of
    system prompt - "THE RATIFIED CAPABILITY KEYS (`capability`) - CLOSED, use
    these and no others". So the vocabulary was an instruction the model could
    decline, and it did: a claim came back with `capability='vision'`, a key the
    ratified twelve deliberately do not contain because `vision` is a BOARD
    section (`judge/extract/schema.py` names it in exactly those words).

    Nothing noticed until `judge/vet/weight.py:compute()` refused it at E6 -
    after the extraction was paid for, and outside the savepoint, so one
    non-compliant claim took the whole batch with it.

    An enum moves the constraint to where the provider can enforce it. It is
    NOT a guarantee: providers differ on whether they validate enums, which is
    the same lesson `prefixItems` taught this function - a schema rule some
    backends enforce and others ignore presents as an intermittent failure. So
    this is prevention, and `compute()`'s check stays as the assertion.

    THE PATH IS ASSERTED. A silently-missed injection would leave the closure
    exactly as weak as it was while looking fixed, which is worse than not
    doing it - so a schema whose shape has moved raises here rather than
    returning an unclosed schema.
    """
    if not capability_keys:
        raise ValueError(
            "no capability keys to close the schema with. `build_system_prompt` "
            "already refuses an empty list; refusing here too, because an empty "
            "enum would be a schema that admits nothing rather than one that "
            "admits the ratified set."
        )

    found = []

    def walk(node: object, path: tuple[str, ...] = ()) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "capability" and isinstance(value, dict) \
                        and value.get("type") == "string":
                    found.append(path + (key,))
                walk(value, path + (key,))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, path + (str(index),))

    walk(schema)
    if found != [_CAPABILITY_PATH]:
        raise ValueError(
            f"expected exactly one string `capability` property at "
            f"{'.'.join(_CAPABILITY_PATH)}, found {[('.'.join(p)) for p in found]}. "
            "The schema shape moved, so the closed vocabulary was NOT applied. "
            "Refusing rather than returning a schema that looks closed and is not."
        )

    node = schema
    for step in _CAPABILITY_PATH:
        node = node[step]
    node["enum"] = list(capability_keys)
    # The description still carries the instruction, because an enum tells the
    # model WHAT is allowed and not what to do when nothing fits. The answer to
    # that - pick the closest and propose the missing one - is the part that
    # keeps discovery working, and it only exists in prose.
    return schema


def tool_schema_for(
    model_cls: type, *, capability_keys: list[str] | None = None
) -> dict[str, object]:
    """A pydantic model's JSON schema with every `$ref` INLINED.

    This renamed `$defs` to `definitions` and rewrote the refs to match, which
    is valid JSON Schema and internally consistent - the target resolved.

    IT STILL FAILED ON THE FIRST LIVE RUN. The model returned
    `claims: [null, null, null, null]`: four claims it had found and could not
    construct, because `claims.items` was `{"$ref": ...}` and it does not
    follow refs. A correct schema the reader cannot dereference is opaque, and
    the failure looks like a schema violation rather than a lookup it could not
    perform.

    So the definitions are inlined rather than referenced. The schema gets
    larger and every consumer can read it without resolving anything, which is
    the only property that matters at a boundary where the reader is a language
    model.

    `prefixItems` IS NORMALISED TO `items` FOR THE SAME REASON, and it cost a
    run to learn. `quote_offset: tuple[int, int]` renders as JSON Schema
    2020-12's `prefixItems`, which is correct and which Gemini's
    function-declaration validator does not implement - it looks for `items`,
    finds none, and returns HTTP 200 carrying

        {'message': '* GenerateContentRequest.tools[0].function_declarations[0]
         .parameters.properties[claims].items.properties[quote_offset].items:
         missing field.', 'code': 400}

    **It survived 50 threads before firing**, because OpenRouter routes across
    backends and only some validate this strictly. So a latent schema defect
    presents as an intermittent provider outage, which is the worst possible
    disguise: `ExtractorUnavailable` reads as "try again later" and retrying
    lands on a lenient route, confirming the wrong diagnosis.
    """
    schema = model_cls.model_json_schema()
    definitions = schema.pop("$defs", {})

    def inline(node: object, expansions: int = 0) -> object:
        # COUNTS REF EXPANSIONS, NOT STRUCTURAL NESTING. The first version
        # incremented on every nested dict and fired immediately - an ordinary
        # schema is more than eight levels deep without recursing at all. The
        # thing being guarded against is a model that refers to itself, and the
        # only step that can loop is following a `$ref`.
        if expansions > 8:
            raise ValueError(
                "more than 8 nested $ref expansions - a self-referential model "
                "cannot be flattened for a tool call."
            )
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                target = definitions[ref.split("/")[-1]]
                merged = {k: v for k, v in node.items() if k != "$ref"}
                return {**inline(target, expansions + 1), **merged}
            # `prefixItems` IS NOT HANDLED HERE. It was, until the 2026-08-31
            # merge put two implementations of one rewrite in one function
            # chain: this one and `widen_tuples` below, called as
            # `widen_tuples(inline(schema))`.
            #
            # THE MERGE WAS TEXTUALLY CLEAN AND SEMANTICALLY NOT. They are
            # separate functions, so git combined them without a conflict, and
            # the result was that this block stripped `prefixItems` FIRST -
            # leaving `widen_tuples` nothing to inspect and its refusal
            # unreachable. `test_a_heterogeneous_tuple_refuses_rather_than_
            # guessing` went from passing to DID NOT RAISE, which is the only
            # reason anybody found out.
            #
            # The two differ on exactly one case and it is the dangerous one.
            # Both rewrite `prefixItems` to `items` for Gemini, which is the
            # reason the rewrite exists. This one took `prefix[0]` on the stated
            # assumption that "the tuples here are homogeneous" - true today,
            # and a silent misdescription to the extractor on the day it stops
            # being true. `widen_tuples` raises instead.
            #
            # So the rewrite lives in ONE place, and it is the one that refuses.
            return {k: inline(v, expansions) for k, v in node.items()}
        if isinstance(node, list):
            return [inline(v, expansions) for v in node]
        return node

    def widen_tuples(node: object) -> object:
        """`prefixItems` -> `items`, keeping min/maxItems as the real constraint.

        REFUSES rather than guessing when the members disagree. A heterogeneous
        tuple - `tuple[int, str]` - has no single `items` type, and picking the
        first would silently tell the model that position 1 is an integer. No
        such field exists today; if one is added, this raises at import of the
        first tool call rather than mis-describing the shape to the extractor.

        `minItems`/`maxItems` already carry the length, so nothing is lost:
        `{"type":"array","items":{"type":"integer"},"minItems":2,"maxItems":2}`
        is the same constraint every validator understands.
        """
        if isinstance(node, dict):
            out = {k: widen_tuples(v) for k, v in node.items() if k != "prefixItems"}
            prefix = node.get("prefixItems")
            if isinstance(prefix, list) and prefix:
                types = {
                    m.get("type") for m in prefix if isinstance(m, dict)
                }
                if len(types) != 1:
                    raise ValueError(
                        f"prefixItems members disagree on type "
                        f"({sorted(t or '?' for t in types)}); "
                        "a heterogeneous tuple cannot be expressed as `items` "
                        "and guessing one would misdescribe a position to the "
                        "extractor. Model this field as a nested object instead."
                    )
                out["items"] = widen_tuples(prefix[0])
                out.setdefault("minItems", len(prefix))
                out.setdefault("maxItems", len(prefix))
            return out
        if isinstance(node, list):
            return [widen_tuples(v) for v in node]
        return node

    flattened = widen_tuples(inline(schema))
    if capability_keys is not None:
        flattened = _close_capability(flattened, capability_keys)
    return flattened
