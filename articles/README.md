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

| Model | Platform | Source | Items |
|---|---|---|---|
| DeepSeek V4 Pro | arXiv | `deepseek-v4-pro/arxiv-report.md` | 43 papers |
| DeepSeek V4 Pro | X | `deepseek-v4-pro/REPORT.md` | 149 posts |
| DeepSeek V4 Pro | Reddit | `deepseek-v4-pro/DeepSeek-V4-Pro-Reddit-Report.md` | 150 posts |
| DeepSeek V4 Pro | Hacker News | `deepseek-v4-pro/DeepSeek-V4-Pro_HN_SubjectThreads_Report.md` | 34 cases |
| DeepSeek V4 Pro | dev.to | `deepseek-v4-pro/devto-deepseek-v4-pro.md.md` | 53 articles |

All four platforms are collected for DeepSeek V4 Pro. A model with a platform
still to collect shows a "not collected yet" notice for it rather than an empty
list.
