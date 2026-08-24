-- claim.speaking — WHOSE claim a quote is.
--
-- ⚠ ADDED BY E1 2026-08-21 AND NEEDS E2's SIGN-OFF, per the lane rule on
--   contract/. It is a new column on `claim` and it changes the evidence tier
--   of three rows already stored, by 6x.
--
-- WHY THE VALUE IS STORED WHEN IT ONLY AFFECTS WEIGHTING.
--
-- `speaking` supplies `evidence_tier`, so the weight already carries its
-- effect and the column looks redundant. It is not, for one reason: the field
-- has never run, so its accuracy is unmeasured on exactly the decision it is
-- making. If the value is not stored, a mislabelling is invisible — the tier
-- would be wrong and nothing would say why. Storing it is what makes the
-- field auditable against the golden set later.
--
-- NULLABLE, DELIBERATELY, AND ONLY FOR THE ROWS THAT PREDATE IT. Four claims
-- exist and none of them carries a value; back-filling one would be inventing
-- a reading of a quote nobody labelled. NULL here means "extracted before the
-- field existed" and is distinguishable from any of the three values, which is
-- rule 6. New claims cannot be NULL: `ModelRef.speaking` is required, so the
-- extractor must answer.
--
-- NOT A STORAGE GATE. A claim with `speaking = 'vendor-about-own-product'` is
-- stored and weighted at tier F (0.02), never refused. See
-- `contract/harvest.yaml evidence_tier_by_speaking.not_a_storage_gate`.

ALTER TABLE claim
  ADD COLUMN speaking text
  CHECK (speaking IN (
    'own-experience',
    'vendor-about-own-product',
    'relayed-from-elsewhere'
  ));

COMMENT ON COLUMN claim.speaking IS
  'Whose claim this is: own-experience | vendor-about-own-product | '
  'relayed-from-elsewhere. Supplies evidence_tier via '
  'contract/harvest.yaml evidence_tier_by_speaking. NULL means the claim '
  'predates the field. Never gates storage.';
