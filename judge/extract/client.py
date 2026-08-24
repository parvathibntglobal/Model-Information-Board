"""The one place in this lane that talks to a language model.

`google/gemini-2.5-flash` through OpenRouter, decided rather than selected
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
from dataclasses import dataclass, field
from typing import Protocol

#: NFR-9. Pinned in config so replacing it is a config change; nothing
#: downstream knows which model produced a claim beyond `pipeline_version`.
DEFAULT_MODEL = "google/gemini-2.5-flash"
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
        import httpx

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            timeout=self.timeout_seconds,
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
        )
        response.raise_for_status()
        body = response.json()

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
        return Completion(
            raw_arguments=arguments,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            model=body.get("model", self.model),
        )


def tool_schema_for(model_cls: type) -> dict[str, object]:
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
            return {k: inline(v, expansions) for k, v in node.items()}
        if isinstance(node, list):
            return [inline(v, expansions) for v in node]
        return node

    return inline(schema)
