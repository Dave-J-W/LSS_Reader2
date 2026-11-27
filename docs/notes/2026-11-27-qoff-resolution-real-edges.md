# Angle offset and Qz resolution, fitted together on the owner's real edges

- **Date, who:** 2026-11-27, the data session on the owner's PC. It runs tools man's new edge fit
  (`fresnel.fit_edge_resolution`, which finds the angle offset Qoff and the resolution width σ_Q together)
  on 400 private and 96 released edge scans, as tools man asked (`docs/handoff_out/09-qoff-resolution-fit.md`).
- **Answer:**
  - **It measures the same widths as the earlier edge-width study** (`docs/studies/qz_resolution/`): σ_Q
    agrees within 2 % (ratio 1.004), and the edge position within 1 × 10⁻⁵ Å⁻¹.
  - **On simulated edges sampled like the owner's** (0.001 Å⁻¹ steps from 0.016) it finds Qoff without bias
    and states an honest ±.
  - **The real edges do not follow the model:** the median χ²/dof is 40 (1 if the model held), with one
    residual pattern (low just below the edge, high 2–5 points above) in 16 of 17 runs.
  - **Qoff is robust:** it moves by 3 × 10⁻⁵ or less over every variant tried.
    - Within a run it moves 7.8 × 10⁻⁵ from series to series (robust SD), 6 times the fit's own ±.
    - Today's Propose button, which assumes a sharp edge, gives a value about 1 × 10⁻⁴ more negative.
  - **σ_Q is fragile:**
    - it rests on the two points either side of the edge;
    - assuming a softer edge (three times water's absorption, which fits best) reads it 33 % narrower;
    - with the narrowest slit (0.02 mm) the width is still not measured (4 of 11 come out at zero).
- **How it is known:** run. `sample_data/private/xr/scripts/qres_{truth,fit,diag,publish}.py`; the study is
  `docs/studies/qoff_resolution_real/summary.md`. Tools man's survey script, run on 3 private files with its
  fuller error model, matches the cached fits.
- **Numbers that changed:** none.
