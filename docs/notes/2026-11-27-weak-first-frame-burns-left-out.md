# Burns whose first frame is weaker than the rest are left out of the burn-shoulder analysis

- **Date, who:** 2026-11-27, the owner. GID guy applied it.
- **Answer:**
  - The owner: "Do not include such data in this burn test analysis", after an earlier example (then
    called P4) turned out to rest on a first frame half as bright as the rest.
  - Rule applied: a burn is left out when its first frame is below 0.8 × the median of its next three
    frames (stretched intensities). The value is `first_frame_ratio` in `gid_split.csv` and
    `FIRST_FRAME_MIN` in `tests/tools/burn_shoulder_study.py`.
  - It applies to all of section 8: the counts, the F76 series and the GID Burn Examples. The reader's own
    burn test is unchanged.
  - The owner also asked for readable labels: the four private burns are now "GID Burn Example 1–4", and
    the public one "NX School GID Burn 15".
- **How it is known:** the owner's message, 2026-11-27. Run: every private burn again with the column added.
- **Numbers that changed** (section 8 of `docs/studies/burn_shoulder/summary.md`):
  - 6 of the 155 burns read are left out, 2 of them otherwise well measured: well measured 119 → 117;
  - intensity verdicts differ 12 → 11; any disagreement 26 → 25 (21 %);
  - shoulders kept 54 → 53; all three signs 15 of 53;
  - F76 series changed by separated 3 → 4 (ρ = 0);
  - question 6 candidates 31 → 29, none with its burned spot measured twice.
  - Examples 2 and 4 are new burns: the former Examples 2 and 4 had a weak first frame.
  - The `OUTPUT_DECISIONS` row is "Burn-shoulder study: burns whose first frame is weaker than the rest".
    The 0.8 is GID guy's reading of "weaker".
