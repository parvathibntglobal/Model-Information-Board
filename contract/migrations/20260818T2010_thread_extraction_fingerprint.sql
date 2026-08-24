-- `thread_extraction.content_fingerprint`. E1's finding, 2026-08-18.
--
-- thread_context.id is stable_id("thread_context", root_id, version) and
-- ignores content, so a thread re-assembled with different children keeps its
-- id. The skip added in 20260818T1830 keys on (thread_context_id,
-- pipeline_version) and would therefore skip a thread whose children changed -
-- evidence silently never extracted, which is worse than paying twice.
--
-- NULLABLE, because rows written before this column exist and were not
-- measured at "no content" (rule 6). A NULL fingerprint means unknown, and the
-- reader treats unknown as "must re-read" rather than as "matches".

ALTER TABLE thread_extraction ADD COLUMN content_fingerprint text;
