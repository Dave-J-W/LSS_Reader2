# Qoff and the Qz resolution on the owner's real edges (DATA_NEEDS row 18)

- **Date, who:** 2026-11-27, xr-data-needs (the owner's PC). Hand-off 09's real-data half. It runs tools man's
  `fresnel.fit_edge_resolution` (#154) on 400 private and 96 released edge scans.
- **Answer:**
  - **It is row 13's estimator.** σ_Q agrees within 2 % (ratio 1.004), and Qoff equals Qc − q_e within
    1 × 10⁻⁵.
  - **Known truth at the owner's sampling** (0.001 steps from 0.016) passes: Qoff unbiased, and honest errors.
  - **The real edges do not follow the model:** χ²/dof has a median of 40, with one residual pattern (low
    just below the edge, high 2–5 points above) in 16 of 17 runs.
  - **Qoff is robust:** 3 × 10⁻⁵ or less over every variant.
    - Within a run it moves 7.8 × 10⁻⁵ from series to series (robust SD), 6 × the fit's ±.
    - Today's sharp proposal is about 1 × 10⁻⁴ more negative.
  - **σ_Q is fragile:**
    - it rests on the two points either side of the edge;
    - an assumed softer edge (β × 3, which fits best) reads it 33 % narrower;
    - S1 0.02 mm edges are still not pinned (4 of 11 at the bound).
- **How it is known:** run. `sample_data/private/xr/scripts/qres_{truth,fit,diag,publish}.py`; the study is
  `docs/studies/qoff_resolution_real/summary.md`. Tools man's survey tool, run on 3 private files with
  `errors='budget'`, matches the cached fits.
- **Numbers that changed:** none.
