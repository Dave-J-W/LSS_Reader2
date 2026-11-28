# No private GID burn has its own spot measured before and after (P44 question 6)

- **Date, who:** 2026-11-27, GID guy, issue #173 (follow-up of #155, hand-off 10's question 6).
- **Answer:** in the private data, no burned spot is scanned before and after the burn.
  - 31 burns (19 well measured) have a GID series covering their Det_Th within 2 h before and within 2 h
    after.
  - In all 31, the sample's horizontal position (`Sample_X`) differs between the burn and both scans. Each
    burn is on a fresh spot, 1–10 mm (median 4 mm) from the nearest scanned one.
  - The before and after scans are usually on different spots from each other too (median 14 mm; 4 pairs
    share one).
  - So these data can't measure what a burn did to its spot, and can't settle which estimator reads the
    fade correctly.
- **How it is known:** run `sample_data/private/burn_shoulder/q6_candidates.py` and `q6_positions.py`
  (private), reading the scans' headers.
- **Numbers that changed:** none. Question 6 in `docs/studies/burn_shoulder/summary.md` section 8 now says
  this. The measurement it needs is DATA_NEEDS row 22: a GID scan of the burned spot just before and just
  after the burn, the sample not moved.
