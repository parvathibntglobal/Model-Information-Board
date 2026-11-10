# Outreach prompts

Every word a model is sent lives in this folder, not in Python, so a prompt
change is a reviewable diff of prose and never hides inside a code change.

```
prompts/
└── shortlist/          the Shortlister (ARCHITECTURE.md 5.2b), shortlist.py
    ├── system.md       the instructions; the thread is NOT in here
    ├── user.md         the template the thread is placed into, inside a
    │                   delimited untrusted block
    └── tool.json       the ONLY way the model can answer (a forced tool call)
```

**The prompt version is computed, not written.** `shortlist.py` hashes the
three files together; every row in `kp_outreach_shortlist` carries that hash in
`prompt_version`. Edit a file and the next run's rows say so, and threads
shortlisted under the old wording are shortlisted again under the new one. Do
not add a version number by hand: it would be a second, forgettable copy of a
fact the hash already holds (CLAUDE.md rule 11).

**What a model answer can do here: order a list.** Nothing more. Code checks
every field against `tool.json` and the config, stores an answer that fails as
`invalid` (never corrected to the nearest valid value), and the review screen
shows the model's reason labelled as the model's suggestion. No thread is
hidden, dropped or posted on a model's word (CLAUDE.md rule 2, rule 8).

**`{placeholders}` in user.md and tool.json** are filled by `shortlist.py`
from config, so the problem list exists once, in each source's
`config/queries.yaml`. A placeholder the code does not fill fails the run.
