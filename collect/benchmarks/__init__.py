"""The Benchmarks page's scraper (BENCHMARK_PIPELINE_WORKFLOW.md).

Reads public leaderboard pages, and the data files their sites publish for
them, into the `bench_` tables. No API keys, no paid services, no language
model. Configuration is `contract/benchmarks/*.yaml` (rule 5).

    config        load + L1 checks of the YAML files
    host_adapter  the seed models: the tracked TEXT models in contract/tracked_models.yaml
    console       the terminal format and the per-run log file (doc section 23)
    fetch         static HTTP, headless browser, site data files; snapshots
    parse         locate a table in what was fetched -> raw observations
    match         raw model name -> row (seed model, or a setting row under it)
    values        parse_score / parse_rank, the L4 range checks
    merge         one published value per cell, by the doc's rules 2-6
    changes       previous cells vs new cells -> changelog entries
    store         the only module that runs SQL
    runner        one run, end to end, one at a time

`judge/` never imports this; the page reads the `bench_` tables directly.
"""
