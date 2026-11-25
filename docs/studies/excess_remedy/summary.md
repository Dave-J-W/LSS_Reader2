# The join's error budget with the measured excess (C64): summary

*main man, 2026-11-25; corrected the same evening. Known truth: C61's six synthetic joins, 400 replicates
each, under truths built from what C63 measured; the public NX school split. The whole chain:
`walkthrough.md` (rule 13). Tool: `tests/tools/excess_remedy_study.py`. No default is changed.*

**The correction.** The first version (#99) put C63's between-scan numbers on every point of both scans as
independent noise. Its headline, "16 % of today's joins miss catastrophically, and 4σ clipping fixes it",
was not supported:
- **The two estimators disagree.** C63's within-scan estimator sees every point and finds only 0.12–0.19 % of
  R and about 0.3 % wild points. The between-scan numbers (0.4 %; 2.65 % at Qz ≥ 0.25; 2–4 % wild pairs) come
  only from the shared points, minutes apart, and grow with the time between them.
- **So they describe a change between scans,** not noise on each point.

**The answer now:**
- **Within a scan: σ × 1.12.**
  - It explains the real splits' under-coverage: today 1.19 / 1.08 under the within-scan truth, against C56's
    1.24.
  - It fixes it: 1.08 / 1.01, at 10–12 % wider errors.
- **Between scans: the threat is at the overlap.**
  - If C63's pair numbers sit on the later scan's overlap points, today misses catastrophically on 13 % of
    joins.
  - The splits cannot test this; real joins against the calibrated foils can.
- **4σ clipping as built is not safe.**
  - It cuts the catastrophic misses (13 % to 0.5–1.1 %).
  - But where two wild points sit together it removes good points and reports a confidently wrong factor
    (E4: off by 27.7 of its own errors; 2 in 400 on the smooth join).
- **An X term on every point is the wrong model** for the between-scan part.

**Recommendation (rule 12):**
1. **Candidate default: σ × 1.12.** The core option is built: `errors={'mode': 'budget', 'counting_scale':
   1.12}` scales the counting part of each point's error, so the curve's error column and the joins both
   follow (`test_counting_scale.py`). Before the switch: the arms on C56's real splits (DATA_NEEDS 17a) and the
   owner's word (MQ-3).
2. **The between-scan part:** real joins against the calibrated foils (C56's 906), and where C63's wild pairs
   sit (the first point after an absorber change, or minutes apart).
3. **Clipping only with a guard** (at most one point, chosen by leave-one-out χ², and checked against the
   unclipped factor), studied again.

| figure | shows |
|---|---|
| E1 | the pull SD per join, arm and truth |
| E2 | the share of catastrophic misses per join, arm and truth |
| E3 | one join rescued by clipping |
| E4 | one join ruined by clipping: good points removed, a confidently wrong factor |
