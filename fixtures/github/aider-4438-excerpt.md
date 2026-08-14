<!-- Excerpt from https://github.com/Aider-AI/aider/issues/4438
     Title: Aider forgets to apply changes after asking for 'file.txt' to be added to context
     Structure preserved: one fenced block containing a config dump and a
     blockquoted paste of a model's response. -->

Aider forgets to apply changes after asking for 'file.txt' to be added to context

I asked aider to add a file and it acknowledged, then never applied the edit.

```
# some of the inputs are truncated in the log
Aider v0.86.0
Main model: vertex_ai/gemini-2.5-pro with diff-fenced edit format
Weak model: vertex_ai/gemini-2.5-flash
Git repo: .git with 691 files
Repo-map: using 4096 tokens, auto refresh
>
> The URL context feature allows you to provide one or more URLs in your prompt.
> # Example usage:
> # prompt = "Summarize the key points from the following articles:"
> # urls_to_summarize = [
> #     "https://cloud.google.com/blog/products/ai-machine-learning/introducing-gemini-2-5-pro",
> # ]
> # summary = generate_text_with_url_context(project_id, location, prompt, urls_to_summarize)
> By following these guidelines you can effectively call the Vertex AI model with the
> powerful features of Google Search grounding and URL context in your Python
> applications. These capabilities enable the development of more accurate, context-aware,
> and intelligent AI systems.
```

Expected: the edit is applied. Actual: nothing changes.
