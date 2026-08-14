# `fixtures/github/` — the two documents that wrote the exclusion set

**Engineer 1.** Short excerpts from two real GitHub issues, kept because the
first live harvest stored both as `summarization.fidelity: positive` evidence for
`gemini-2.5-flash` and neither is evidence of anything.

| file | source | why it is here |
|---|---|---|
| `aider-4438-excerpt.md` | [Aider-AI/aider#4438](https://github.com/Aider-AI/aider/issues/4438) | `accurate` matched inside a Google marketing sentence, pasted as a blockquote **nested inside a fenced block**. The issue is about diff application |
| `crewai-2685-excerpt.md` | [crewAIInc/crewAI#2685](https://github.com/crewAIInc/crewAI/issues/2685) | `accurate` matched inside a prompt string in a Python snippet. The issue is about a tool signature |

**Excerpts, not captures.** The originals are 41k and 7k characters. Published
content in this project is quote + attribution + link and never full text
(NFR-5), and a fixture is not published — but checking a stranger's whole issue
body into a repository is close enough to the thing that rule forbids that the
short form is the right one. Each file keeps only the lines that reproduce the
structure the sieve has to get right, with the issue URL at the top.

They are regression fixtures. If either starts passing a positive summarisation
query again, the exclusion set has regressed.
