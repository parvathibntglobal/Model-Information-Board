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

import json
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

    def complete(
        self, *, system: str, user: str, tool_schema: dict[str, object]
    ) -> Completion: ...


@dataclass
class FakeClient:
    """Scripted responses, for every path a real endpoint will not produce.

    Responses are consumed in order. Exhausting them raises rather than
    repeating the last one: a test that calls more times than it scripted has
    a bug, and silently returning the previous answer would hide it.
    """

    responses: list[str] = field(default_factory=list)
    calls: list[dict[str, str]] = field(default_factory=list)

    def complete(
        self, *, system: str, user: str, tool_schema: dict[str, object]
    ) -> Completion:
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

    def complete(
        self, *, system: str, user: str, tool_schema: dict[str, object]
    ) -> Completion:
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
    """A pydantic model's JSON schema, flattened for a tool parameter."""
    schema = model_cls.model_json_schema()
    definitions = schema.pop("$defs", None)
    if definitions:
        schema["definitions"] = definitions
        return json.loads(json.dumps(schema).replace("#/$defs/", "#/definitions/"))
    return schema
