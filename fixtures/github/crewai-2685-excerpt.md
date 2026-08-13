<!-- Excerpt from https://github.com/crewAIInc/crewAI/issues/2685
     Title: [BUG] RagTool `_run` signature with `**kwargs` causes `args_schema` mismatch
     Structure preserved: a Python fence whose prompt strings carry the signal term. -->

[BUG] RagTool `_run` signature with `**kwargs` causes `args_schema` mismatch and runtime errors

The tool signature does not line up with the schema, so the run fails.

```python
rag_tool = RagTool(
    config=embedchain_config,
    summarize=False
)

llm = LLM(
    model="gemini/gemini-2.5-flash-preview-04-17",
    temperature=0.1
)

knowledge_assistant = Agent(
    role="Knowledge Assistant",
    goal=(
        "Answer questions accurately using only the provided knowledge "
        "tools. Provide clear and complete explanations. If information "
        "is not found, clearly indicate this."
    ),
)
```

Traceback follows.
