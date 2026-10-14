-- The heading the extractor filed a capability under. 2026-10-14.
--
-- WHY. The extractor named a new capability for most quotes it read: 581 of the
-- 736 capability leaves on the local copy had one report, and only 170 sat
-- under a heading. It is now shown the board's capability vocabulary under ten
-- headings (contract/board_vocabulary.yaml) and files every capability entry
-- under one (`BoardEntry.parent`). This column keeps that filing.
--
-- WHAT A VALUE MEANS. One of the capability headings in
-- contract/slug_parents.yaml. NULL is "no usable heading": not a capability,
-- written before this column, or the extractor gave none or an unknown one
-- (judge/store/board_entries.py:store_entries counts those). NULL is never
-- backfilled with a guess (rule 6).
--
-- WHO READS IT. judge/store/board_entries.py:board_sections carries the
-- commonest value per leaf; judge/board_grouping.py:group_section places a
-- leaf the contract has not filed under it, marked `filed_by: extractor`.
-- The contract wins wherever it has an answer.

ALTER TABLE board_entry ADD COLUMN parent_proposed text;
