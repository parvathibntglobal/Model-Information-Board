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
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

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
    total_timeout_seconds: float = float(
        os.getenv("EXTRACT_TOTAL_TIMEOUT_SECONDS", "300")
    )
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
            model=os.getenv("EXTRACTOR_MODEL", DEFAULT_MODEL),
            base_url=os.getenv("OPENROUTER_BASE_URL", DEFAULT_BASE_URL),
            api_key=key,
        )

    def complete(self, *, system: str, user: str, tool_schema: dict[str, object]) -> Completion:
        import json as _json
        import time

        import httpx

        # STREAMED SO THE CLOCK CAN BE CHECKED WHILE THE BODY ARRIVES.
        #
        # `httpx.post` returns only when the response is complete, so there is no
        # moment at which elapsed time can be examined - which is why a 39-minute
        # call was possible under a 60-second timeout. Reading the body in chunks
        # gives a point to check a deadline against, and it is the only way to
        # bound a response that is technically still arriving.
        #
        # WHAT THIS BOUNDS, EXACTLY. The deadline covers waiting for the body.
        # Waiting for the HEADERS is still bounded by the read window instead, so
        # the true worst case is `timeout_seconds + total_timeout_seconds` rather
        # than the latter alone. Stated rather than rounded off, because a
        # ceiling that is quietly 60s higher than it claims is the same species
        # of defect as the one this fixes.
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
            },
        ) as response:
            chunks: list[bytes] = []
            # THROTTLED, because `checkpoint()` reads a file. A chunk can be a
            # few bytes, so calling it per chunk would stat the disk thousands
            # of times for one response. Once a second is far faster than a
            # person can regret pressing Stop, and costs nothing.
            next_check = 0.0
            for chunk in response.iter_bytes():
                chunks.append(chunk)
                now = time.monotonic()
                if self.on_progress is not None and now >= next_check:
                    next_check = now + 1.0
                    # Deliberately NOT wrapped: this is how a stop leaves the
                    # call, and swallowing it here would restore the defect.
                    self.on_progress()
                if now > deadline:
                    # NAMES WHAT WAS MEASURED, not a guess at the cause. The
                    # provider may be slow, wedged, or streaming something
                    # enormous; this call cannot tell which and does not say.
                    # `ExtractorUnavailable` because the run must end here rather
                    # than continue against a provider that is not answering -
                    # and with the per-thread commit, ending here keeps every
                    # thread already read instead of discarding the batch.
                    raise ExtractorUnavailable(
                        f"the provider was still sending after "
                        f"{self.total_timeout_seconds:.0f}s "
                        f"({len(b''.join(chunks))} bytes received); abandoned so the "
                        f"batch is not held open by one call. Idle-time timeouts "
                        f"do not catch this: a response that keeps trickling never "
                        f"goes idle."
                    )
            raw = b"".join(chunks)
        response.raise_for_status()
        try:
            body = _json.loads(raw)
        except ValueError as exc:
            raise ExtractorUnavailable(
                f"the provider returned HTTP {response.status_code} with a body "
                f"that is not JSON ({len(raw)} bytes): {raw[:200]!r}"
            ) from exc

        # A PROVIDER ERROR ARRIVES AS HTTP 200, so `raise_for_status` passes and
        # the body has no `choices`. This used to be a bare `KeyError: 'choices'`
        # raised out of the middle of a corpus run — measured 2026-08-21, on
        # document 21 of 75, which ended the run and took the twenty completed
        # documents with it because nothing had been written yet.
        #
        # A KeyError is the wrong shape twice: it names a dict key rather than
        # the upstream failure, and it is indistinguishable from a schema change
        # on our side. Raised as itself, with whatever the provider said, so a
        # caller can record a provider failure as one.
        if "choices" not in body:
            detail = body.get("error") or body
            raise ExtractorUnavailable(
                f"the provider returned HTTP {response.status_code} with no "
                f"`choices`: {detail!r}"
            )

        usage = body.get("usage") or {}
        calls = body["choices"][0]["message"].get("tool_calls") or []
        arguments = calls[0]["function"]["arguments"] if calls else ""

        # RECORDED HERE, BECAUSE THIS IS WHERE THE USAGE IS. E5 has been calling
        # a paid model since August and writing nothing to the ledger - the only
        # caller of `spend_ledger.record` was the Ask box - which is why the
        # usage panel showed one model and had to derive the other from the
        # provider's key total minus what it knew. Next to the response is the
        # only place that cannot forget, and `record` swallows write failures so
        # a full disk cannot end a corpus run.
        from judge import spend_ledger

        spend_ledger.record(
            stage=spend_ledger.STAGE_EXTRACT,
            model=body.get("model", self.model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )
        return Completion(
            raw_arguments=arguments,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            model=body.get("model", self.model),
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
