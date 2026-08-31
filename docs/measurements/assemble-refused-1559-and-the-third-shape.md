# `assemble reddit` refused all 1,559, correctly — and the shape it needs is GitHub's, not the blog's

**0 assembled, 1,559 refused, and the refusal is right given the options the
assembler has.** 1,512 of them for the same reason: a post with no children is not
a Reddit thread. But it is not a blog article either, and the assembler has no
third option — which is exactly the state `assemble_issue` was written for on
GitHub and never ported here.

*Engineer 1 · 2026-08-28*

---

## 1 · The run

```
assemble : 0 of 1,559 reddit thread(s) assembled, 0 already had a
           thread_context, 1,559 refused

refusal classes
  1,512   "no comment bodies resolved, so this would assemble a post with no
           children — which is the blog shape, not a Reddit thread"
     47   "root body ... did not resolve in the store (missing)"
```

`thread_context` is unchanged at 214 rows, 69 reddit documents. Nothing was
written, which is the correct outcome and not a failure.

## 2 · The corpus is root posts, and 94% of them have a thread we did not fetch

```
reddit documents written today          1,507
  of which roots (thread_root_id NULL)  1,507
  of which comments                         0
  with num_comments > 0                 1,417   (94.0%)
```

**That last number decides the question.** These are not posts with no
conversation. They are posts whose conversation exists, is counted in the stored
`engagement.comments`, and was never fetched — because a model-only search sweep
retrieves posts and `fetch_comments` is a separate call per post.

## 3 · So is this a legitimate `whole_document` case? No. It is the GitHub case

Three shapes exist in `collect/assemble/` and the distinction between two of them
is already written down:

```
assemble_article   blog     selection_method = whole_document
                            The article IS the whole document. TRUE.

assemble_issue     github   selection_method = issue_body_only
                            NOT whole_document, and its docstring says why:
                            "the body is one member of a thread that exists and
                            was not fetched"
                            observed_children  = 0
                            hidden_children_min = comment_count
                            coverage_ratio     = 0.0, meaning we read the root
                                                 and none of the thread

assemble_reddit    reddit   selection_method = ..._@observed
                            requires children. Refuses without them.
```

**A model-only Reddit post is the middle row exactly.** Calling it
`whole_document` would assert that the post is the whole document, and for 1,417
of 1,507 that is false — there are counted comments we did not read. The blog
value is true for a blog and would be a lie here.

And `assemble_issue`'s own comment already anticipated this: writing
`hidden_children_min = 0` instead of the comment count *"would produce NULL —
'an empty tree' — and an issue with twelve comments is not an empty tree. That is
the difference between a coverage figure that is low and one that is wrong."*

## 4 · What that means for the classification results

**They cannot become claims, and `assemble` is not the only reason.** Even with a
`post_body_only` path, a claim needs `quote_flat_offset` and `quote_raw_offset`,
and those come from the offset map built at flatten time. A `post_body_only`
assembly WOULD produce one — flattening a single member is the blog path and it
emits an offset map — so this is the step that unblocks it.

But the classifier's own output is still short of a claim on four fields it never
asked for: `polarity`, `condition_bucket`, `relevance`, `evidence_tier`. Those are
a prompt question, not a structural one.

**So the honest chain is:**

```
1  a post_body_only path in assemble_reddit    -> thread_context + offset map
2  a pass that assigns polarity and the rest   -> the four unasked fields
3  then claim rows are insertable
```

Step 1 is mine and is ~60 lines mirroring `assemble_issue`. Step 2 is the
extractor's job and the extractor already does it — which argues for running
`judge extract` over the assembled contexts rather than extending the temporary
classifier, because the classifier would be reimplementing the stage that exists.

## 5 · The 47 unreadable roots, named rather than folded in

47 refusals are `root body ... did not resolve in the store (missing)` — payloads
absent from this machine. They are the 2026-08-27 documents whose fetch ran
elsewhere, plus 3 from today whose store write I have not chased. Distinct from
the 1,512: those have a readable body and no children, these have no readable body
at all. A `post_body_only` path fixes the first group and not the second.

## 6 · What I did not do

**Did not add `whole_document` to the reddit path to make the number go up.** The
refusal message is correct and the fix is a third selection method, not a looser
second one. A `thread_context` claiming to be the whole document, on a post with 94
counted comments nobody read, is the shape rule 4 is about — and it would be
invisible afterwards, because `coverage_ratio` would read 1.0 rather than 0.0.
