# The join's error budget with the measured excess (C64): summary

*main man, 2026-11-25. Known truth: C61's six synthetic joins with C63's measured excess drawn in, 400
replicates each, and the same with no excess; the public NX school split. The whole chain:
`walkthrough.md` (rule 13). Tool: `tests/tools/excess_remedy_study.py`. No default is changed.*

**The question:** which error budget in today's joint fit gives honest join errors? C63 measured three kinds
of excess on real data: the counting σ about 12 % small, a spread between scans of 0.2–2.65 % of R, and
3 % of points wild.

**The answer:**
- **Wild points are the main harm, and the pull SD hides it.** With C63's excess, 16 % of today's joins
  miss by more than 5 oracle errors. Their errors are inflated by the χ² as much as they miss, so the pull
  SD looks almost fine (1.26 / 1.16).
- **4σ clipping** (the point furthest from the curve left out while beyond 4 σ, then refit) cuts the
  catastrophic misses to 0.6 % and brings the pull SD to the oracle's (1.05 / 0.98). With no excess it
  changes nothing.
- **σ × 1.12 ⊕ X** (the budget's two terms) fix the core under-coverage. The smooth join's pull SD goes from
  1.26 to 1.10. They cost 14–17 % wider errors where no excess exists.
- **Student-t or Cauchy re-weighting** only halves the catastrophic misses (7.6–9.7 %).
- **The key of X:** keyed to Qz, it quadruples the error of the bright NX scan 9, at high Qz but with good
  counts. Keyed to counts, it grows that error by 1.3 ×. Real data must decide.

**Recommendation (rule 12):**
- **Candidate 1: 4σ clipping in the joint fit,** alone. It is the large win, costs nothing on clean joins,
  and needs no X.
- **Candidate 2: σ × 1.12 ⊕ X(counts),** if the real splits support it.
- **Before either:**
  1. the local agent runs the arms (`estimate(a, b, arm)`) on C56's 1091 real splits: pull SD, coverage, the
     catastrophic share, and where clipped points sit (DATA_NEEDS row 17);
  2. the core option in `lss_core.patching` with tests;
  3. the owner's word (MQ-3).

| figure | shows |
|---|---|
| E1 | the pull SD per join and arm, with C63's excess and with none |
| E2 | the RMS miss and the share of catastrophic misses, in units of the oracle's error |
| E3 | one join with a wild point, fitted today and with the budget and clipping, with residuals |
