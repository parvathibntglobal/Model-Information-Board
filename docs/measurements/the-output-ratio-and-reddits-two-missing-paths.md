# The output ratio was already measured, and it inverts the cost: Reddit is the expensive corpus

**No model call was made to establish this.** `thread_extraction` has been
recording `input_tokens` and `output_tokens` for every extraction since the table
existed — 51 rows. The measurement the plan wanted from a Reddit run was already
on disk.

*Engineer 1 · 2026-08-24*

---

## 1 · Both halves of my estimate were wrong, in opposite directions

```
                        my estimate     measured (n=51)
output tokens / unit          700           115 median, 189 mean
                                            (min 21, max 2,263)
input tokens / unit    from chars only    blog 2,698, reddit 2,113
```

**Output: 6x too high.** **Input: too low, and for a reason I had not accounted
for at all** — the prompt carries a system prompt, the JSON schema and the
twelve capability keys on every call. Derived from measured input minus the
document's own tokens:

```
blog     measured 2,698/unit  -  document 1,030  =  overhead 1,667
reddit   measured 2,113/unit  -  document    16  =  overhead 2,096
                                          median overhead  1,882
```

**~1,882 tokens of fixed overhead per call.** A character count times a
chars-per-token ratio measures the document, and the document is not the request.

## 2 · The revised cost, and it is half what I reported

```
                                  median output (115)   mean output (189)
reddit   190 units  in 360,692          $0.1628              $0.1981
blog     120 units  in 349,514          $0.1394              $0.1616
github    53 units  in 521,045          $0.1716              $0.1814
                                        -------              -------
TOTAL                                   $0.4737              $0.5412

cap $1.00    |    my earlier figure $0.9263
```

**Use the mean for a budget and the median for a typical document.** Output
ranges 21 to 2,263 tokens — a 108x spread — so a median understates a batch and
is the wrong number to plan a cap against.

## 3 · The shape inverted: Reddit is now the most expensive corpus

Yesterday's reading was *"GitHub is 76% of the cost on 13.5% of the units."*
That was an artifact of costing the document instead of the request.

```
                units    input tokens    of which overhead
reddit           190       360,692          357,580   (99.2%)
blog             120       349,514          225,840   (64.6%)
github            53       521,045           99,746   (19.1%)
```

**Reddit's 94-character comments cost 2,113 input tokens each, of which 2,097 is
prompt.** Extracting Reddit as it currently sits pays the schema, the system
prompt and the capability list **190 times over, to read 3,040 tokens of actual
comment text.**

That is not an argument against extracting Reddit. It is an argument that
extracting it **one comment at a time** is the wrong unit — which is precisely
what `thread_context` exists to fix, and which brings us to the gap.

## 4 · Reddit has no path at either end

Asked for three times, and it does not exist. Named here so it stops being
re-requested:

```
sweep     ops exposes only `sweep-github`.
          write_reddit_thread.py takes ONE thread.
          unfiltered_sweep.py writes to a DIRECTORY for calibration, not the db.

assemble  `collect assemble` exposes only `github`.
          190 of 191 reddit documents have NO thread_context.

result    1 reddit thread_context exists. judge/ reads thread_context.
          So 190 reddit documents are invisible to the extractor today.
```

**Reddit is the platform that measured many voices and version names**, and it is
the only one that can be neither swept nor assembled.

### What building each would cost

**`assemble reddit` — the smaller and the one I would do first.** The pieces
exist: `collect/adapters/reddit_comments.py` holds the comment tree,
`collect/assemble/` holds flattening and offset maps, and the one existing reddit
context proves the selector runs (`specificity_x_log_engagement@observed`). What
is missing is the command and the batch driver over stored documents — the same
shape as `assemble github`, which is ~120 lines. **Call it a day, and it pays for
itself twice:** it makes 190 documents extractable, and it collapses 190 calls
into a handful of threads, taking Reddit's 99.2% overhead down to something
proportionate.

**`sweep reddit` — larger, and it is a design decision rather than a port.**
GitHub's sweep renders one query per alias per capability entry and records each
in `harvest_run`. Reddit's API takes no query for `/getPostsBySubreddit`, which is
why `unfiltered_sweep.py` exists and why it deliberately avoids
`/getSearchPosts` — *"the index ranks, and ranking is the selection effect this
exists to escape."* So a Reddit sweep is not a rendering problem, it is a
question of what the unit of retrieval is: subreddit-and-window, or query. **That
is a ruling before it is a build**, and it is not mine to make alone.

## 5 · Blogs are saturated, which is the other half of the same problem

```
feeds 9   articles offered 105   already present 104   new documents 1
netflixtechblog.com               0 articles
medium.com/airbnb-engineering     0 articles
```

**More blog evidence needs more feeds, not more sweeps.** The current list is
exhausted, and two of its nine feeds return nothing at all.

**Taken together with §4:** GitHub is the only platform that can currently be
swept, blogs are the only one that can currently be assembled and extracted at
volume, and Reddit — which the corpus measurements say carries the most voices
and the most version-specific naming — can do neither. That is a coverage
constraint arriving from the tooling rather than from the corpus, and it is the
first time this week the constraint has not been "what people write".

## 6 · The revised split

The plan was Reddit, then blogs, then GitHub as its own decision. **The
measurement that justified GitHub-last no longer holds** — it is $0.18 of a
$0.54 batch, not 76% of it.

Revised, and the ordering now follows what is *possible* rather than what is
cheap:

1. **Blogs — 76 contexts not yet extracted**, ~$0.10 at the mean. Ready today,
   nothing blocking, and it is where first-hand evidence measured highest.
2. **GitHub — assemble the 53 first** (`collect assemble github` exists), then
   extract, ~$0.18. Its 1.3% signal rate is a reason to expect little, not a
   reason to skip: 53 documents that survived a 0.5% sieve are the most
   pre-selected corpus we hold.
3. **Reddit — blocked**, and the fix is `assemble reddit` rather than a budget
   decision.

**Nothing here needs a $1.00 cap split across three days.** The whole corpus is
$0.54 at the measured mean. The reason to run them separately is that they are
three different questions, not that the money is tight — and I said the opposite
yesterday on a 6x-wrong output estimate.
