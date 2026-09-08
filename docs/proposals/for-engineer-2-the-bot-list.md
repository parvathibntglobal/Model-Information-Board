# For Engineer 2 — `contract/bots.yaml`, and the 7 accounts neither signal catches

**Proposal, 2026-09-07. `contract/` has not been touched.**

The detector is built and wired: `collect/triage/bots.py` loads the list,
`triage.gates.known_bot` matches on it, `collect/cli.py triage bots` prints its
state without needing a database, and `tests/test_bot_list.py` covers the
refusals. **The list is the part that is yours**, because rule 5 puts a filter
rule in `contract/` and `contract/` gets two eyes.

Until the file lands, `known_bot` reports UNAVAILABLE — now **per source**
rather than corpus-wide, so the count falls platform by platform as each one is
curated.

Measurement: `docs/measurements/bot-account-ids-2026-09-07.json`.

---

## 1 · The finding, and it is not the one I reported on 2026-09-07

I reported that the `[bot]`-suffix heuristic could not be trusted to catch
seven accounts whose logins are plainly automated. **I had only the logins** —
`_github_comments.json` carries `author_handle` and no user object — so I could
not check what GitHub declares about them.

I have now read `GET /users/{login}` for all 33 accounts carrying `bot` in the
login. Population: 2,016 comments, 1,099 distinct accounts, from the GitHub
comment export — **not** the 6,502-document corpus.

```
[bot]-suffixed accounts                    26   →  all declare type: Bot
'bot' in the login, no [bot] suffix         7   →  all declare type: User
accounts where user.type and the suffix DISAGREE   0
```

**Zero disagreements, and that inverts the argument.** The suffix is not an
unreliable proxy for `user.type` — on this population the two agree perfectly.
What they do is **miss the same seven accounts identically**, because those are
ordinary user accounts operated as bots. GitHub declares `type: Bot` only for
registered GitHub Apps; a human account running a script is a `User` and there
is no field that says otherwise.

So neither signal available to us catches them, and no third signal exists.
**A curated list is not the cheaper option here, it is the only one.**

| login | `user.id` | `user.type` | comments |
|---|---|---|---|
| `tenstorrent-github-bot` | `123498312` | User | **33** |
| `Issues-translate-bot` | `74373520` | User | 4 |
| `raycastbot` | `68011578` | User | 1 |
| `QAbot-zh` | `40236765` | User | 1 |
| `doyouacceptcrypto-bot` | `279372859` | User | 1 |
| `FacultativeObligatoryBotContract` | `145221046` | User | 1 |
| `happier-bot` | `261991208` | User | 1 |

**Why 33 matters.** The busiest human accounts in the same export are
`cdomotor-g` at 33 and `SchlenkR` at 30. So `tenstorrent-github-bot` is
**joint-top voice** — and `N_EFF_MINIMUM = 3.0` weighted independent voices
decides publication. A third voice that is a CI account is the failure the
voice count exists to prevent.

**And `FacultativeObligatoryBotContract` is why this cannot be a regex.** One
comment, `type: User`, and almost certainly a person with a joke name. A
pattern over logins would filter them, and would filter `releasebot` the
helpful maintainer. `github.py:is_bot` already refuses the string heuristic and
records that its `[bot]`-suffix agreement was measured against a denominator of
**two accounts**; this measurement widens that denominator to 33 and reaches
the same conclusion for a different reason.

---

## 2 · What I am asking you to agree to

### 2.1 The file, keyed on the stable account id

```yaml
# contract/bots.yaml
version: "1.0"

sources:

  github:
    id_space: github_user_id          # `user.id`, numeric. NOT the login.
    reviewed_on: 2026-09-07
    reviewed_by: <you>
    accounts:
      # ── declared by the platform: user.type == "Bot" ──────────────────
      # 26 accounts, 200 of 2,016 comments (9.9%). ALREADY handled at
      # collection: `github.write_comments` writes these `status='filtered'`
      # with `filter_reasons: ['bot_author']` and no author_id. Listed anyway,
      # because that writer covers COMMENTS only — an issue BODY opened by a
      # GitHub App reaches `write_documents`, which has no bot rule at all.
      - {external_id: "41898282",  login: "github-actions[bot]"}
      - {external_id: "218312386", login: "gemini-cli[bot]"}
      - {external_id: "122617954", login: "vs-code-engineering[bot]"}
      - {external_id: "298016966", login: "icsoc-2026-science-agent[bot]"}
      - {external_id: "222613912", login: "linear-code[bot]"}
      - {external_id: "298266582", login: "ppam-2026-code-agent[bot]"}
      - {external_id: "44709815",  login: "linear[bot]"}
      - {external_id: "274271284", login: "clawsweeper[bot]"}
      - {external_id: "136622811", login: "coderabbitai[bot]"}
      - {external_id: "265913398", login: "llm-exe-bot[bot]"}
      - {external_id: "108849941", login: "flows-network-integration[bot]"}
      - {external_id: "100856346", login: "n8n-assistant[bot]"}
      - {external_id: "209825114", login: "claude[bot]"}
      - {external_id: "131922026", login: "dosubot[bot]"}
      - {external_id: "77245923",  login: "microsoft-github-policy-service[bot]"}
      - {external_id: "257215752", login: "openclaw-barnacle[bot]"}
      - {external_id: "221166651", login: "a5c-ai[bot]"}
      - {external_id: "298017128", login: "icsoc-2026-code-agent[bot]"}
      - {external_id: "210226050", login: "gemini-ai-assistant[bot]"}
      - {external_id: "168289627", login: "ai-swe-issues-bot[bot]"}
      - {external_id: "273333864", login: "soleur-ai[bot]"}
      - {external_id: "208079219", login: "amazon-q-developer[bot]"}
      - {external_id: "251103656", login: "pydanty[bot]"}
      - {external_id: "282769551", login: "open-design-bot[bot]"}
      - {external_id: "266927401", login: "hebo-agent[bot]"}
      - {external_id: "249292202", login: "infra-vault-gh-plugin-prod[bot]"}

      # ── THE SEVEN. type: User, and no signal catches them ─────────────
      # THIS IS THE HALF THAT NEEDS YOUR JUDGEMENT, one account at a time.
      # I have put my reading beside each; the last one I would NOT list.
      - {external_id: "123498312", login: "tenstorrent-github-bot"}
        # 33 comments, joint-top voice. Org-operated CI account.
      - {external_id: "74373520",  login: "Issues-translate-bot"}
        # Auto-translates issue text. Not a report about a model.
      - {external_id: "68011578",  login: "raycastbot"}
      - {external_id: "40236765",  login: "QAbot-zh"}
      - {external_id: "279372859", login: "doyouacceptcrypto-bot"}
      - {external_id: "261991208", login: "happier-bot"}
      # NOT LISTED: 145221046 FacultativeObligatoryBotContract — one comment,
      # and the name reads as a joke rather than an account description. If a
      # human is on this list their voice is deleted and nothing says so, which
      # is the direction to err away from.

  reddit:
    id_space: reddit_fullname         # `t2_…`. Survives a rename.
    reviewed_on: <date you read them>
    reviewed_by: <you>
    accounts: []
    # ⚠ NOT CURATED, AND `[]` IS THE WRONG VALUE UNTIL IT IS. `ClaudeAI-mod-bot`
    #   is in the top five authors of the 1,297-post corpus (gates.py's own
    #   docstring), so this platform has a known bot and I do not have its
    #   `t2_`. Leave the block OUT rather than writing `[]`: an empty list
    #   claims somebody looked, and the loader reports an absent source as
    #   UNAVAILABLE, which is true.
```

Three properties of the loader that the file has to satisfy, each with a
refusal behind it (`tests/test_bot_list.py`):

- **`id_space` is required and closed.** An id space nobody stated is a list
  keyed on an unknown thing; it matches nothing, and matching nothing is
  indistinguishable from a platform with no bots.
- **An entry needs `external_id`.** A `login` alone is refused. The login is
  carried beside it for review and is never matched on — that is the whole
  point of the key.
- **An absent file is `None`, not an empty list**, and an absent *source* is
  UNAVAILABLE rather than `False`. `accounts: []` means somebody looked and
  found none, which is a measurement. Those three states are the design.

### 2.2 One thing to decide beyond the list

**`write_documents` has no bot rule.** `github.write_comments` filters bot
*comments*; an issue **body** opened by a GitHub App goes through
`github.write_documents`, which never asks. I have not changed that — it is a
collection-time filter and the ruling on drop-versus-weight is yours — but the
list makes it cheap either way, and the gate will catch it at E4 regardless if
`triage` is ever wired.

---

## 3 · What the list does NOT decide

`known_bot` returning True sets `triage_verdict = 'dropped'` and a
`filter_reasons` entry. **It does not delete anything**: rejected is not
deleted, the payload stays in the raw store, and a ruling that says "weight
rather than drop" can be applied later to data we already hold — which is
exactly the position `github.write_comments` took for bot comments and said so.

And it changes nothing today, because the `triage` stage is `run=None` and no
gate has ever written a verdict (`triage_verdict` NULL on 6,502 of 6,502). The
list's value is that it removes one of the two reasons the stage cannot be
wired. The other is the language detector, which is a dependency decision and
is not this proposal.
