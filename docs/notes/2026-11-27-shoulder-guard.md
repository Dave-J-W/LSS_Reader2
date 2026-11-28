# A separated shoulder whose height the points don't determine is refused (#187)

- **Date, who:** 2026-11-27, GID guy, issue #187 (found by main man in the review of #184: BC_P2's "shoulder"
  stood 1.3 × the mean frame's peak across the window, on a large negative line).
- **Answer:**
  - `burn.separate_shoulder` now refuses a fitted shoulder whose height has a relative error above 50 %
    (`SHOULDER_MAX_HEIGHT_ERROR`). The error comes from the fit's own covariance. The separated readings
    then equal the stretched one, and `reference['shoulder_refused']` gives the reason.
  - That happens when the Gaussian is much broader than the window, where it is only a curvature and its
    height trades off against the line.
  - The two cuts first proposed are not used, because they refuse real broad shoulders that the points do
    pin down: a width cut (σ above half the window) and a height cut (S above the shape). A synthetic
    shoulder of σ 0.06, wider than the window's half-width, is recovered to ± 3 %.
  - The fit itself is unchanged, so every kept shoulder gives the same numbers.
- **How it is known:**
  - Tests in `tests/test_burn_split.py`: an undetermined curvature is refused; a determined broad shoulder
    is kept; 0 of 800 synthetic burns are refused at monitors 1e4–1e7, every case and shoulder shape, so
    sections 1–6 of the burn-shoulder study are unchanged.
  - Run: every private GID burn again (`sample_data/private/burn_shoulder/run_real.py`).
- **Numbers that changed** (section 8 of `docs/studies/burn_shoulder/summary.md`, before → after):
  - well-measured burns 118 → 119;
  - shoulders kept 94 → 54 (41 refused, 24 with none);
  - intensity verdicts differ 15 → 12;
  - any disagreement 39 (33 %) → 26 (22 %);
  - share of disagreeing burns with a changing shoulder 67 % → 73 %, against 27 % → 14 % of agreeing ones;
  - all three signs of a changing shoulder 22 of 94 → 15 of 54 (23 % → 28 %);
  - F76 series whose verdict separated changes 5 → 3 (ρ = 0).
  - P2 (BC_P2) now has no shoulder.
  - The judgment stands: the shoulder, not the width, drives the disagreements, and `separated_held` isn't
    safe. The `OUTPUT_DECISIONS` row is "Burn test, shoulder separated: when a fitted shoulder is no
    shoulder". The 50 % limit is an assumption.
