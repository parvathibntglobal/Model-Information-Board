# articles/ — scraped article sources

Raw platform scrapes that feed the **Articles** page (`web/src/routes/Articles.jsx`),
kept in the repo so the rendered data is reproducible rather than hand-maintained.

```
articles/
  <model>/<platform>-report.md   # the raw scrape (source of truth)
  build_data.py                  # parses the scrapes -> web/src/data/*.json
```

The JSON under `web/src/data/` is **derived**. To rebuild it after a re-scrape,
replace the Markdown and run:

```
python articles/build_data.py
```

Never hand-edit the generated JSON — change the scrape (or the parser) and
rebuild, so the two never drift.

## Current sources

| Model | Platform | Source | Papers |
|---|---|---|---|
| DeepSeek V4 Pro | arXiv | `deepseek-v4-pro/arxiv-report.md` | 43 |

X and Reddit are declared in the UI but not yet collected — the page shows a
"not collected yet" notice for them rather than an empty list.
