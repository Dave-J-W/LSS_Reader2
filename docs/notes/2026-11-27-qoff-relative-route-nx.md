# Where the reflection lands, frame by frame, on NX: the relative route agrees with the edge fits

- **Date, who:** 2026-11-27, main man (#148, F42's relative route, C72).
- **Answer:**
  - **The references agree.** NX school's three sample-height scans (5, 10, 13) put the reflection's plateau row at
    53.01, 52.98 and 52.96 (± 0.02 each).
  - **The reflection barely moves.** Across reflectivity scans 6–9 (96 frames) it stays within 0.18 px, so the angle
    along the curve changes by at most 3 × 10⁻⁵ rad. Read as a surface tilt (the owner's reading), the points were
    measured within ±2.3 × 10⁻⁴ Å⁻¹ of their recorded Qz.
  - **The check at the alignment angle holds.** Next to the sh scans' own angle (Qz 0.0187) the shift is
    −0.5 ± 0.4 × 10⁻⁴: zero within its error, as it must be.
  - **About the edge it agrees with the edge fits.** Just above and below the critical edge (Qz 0.021–0.026) the shift
    is −1.2 to −1.7 × 10⁻⁴ Å⁻¹. That is the same sign and size as the edge fits' Qoff on the same scans (−1.2 to
    −2.8 × 10⁻⁴, `docs/studies/qoff_resolution/summary.md` §4), from a measurement that shares nothing with them.
  - **The limits:**
    - The route sees only changes from the alignment angle.
    - The tilt reading halves what an incident-angle reading would give.
    - The direction of the row axis comes from the sh scan's direct beam (below the reflection on NX).
- **How it is known:** run (`lss_core.detector_qoff.relative_shifts(exp, [6, 7, 8, 9], 5)`) and test
  (`tests/test_detector_qoff.py`).
- **Numbers that changed:** none (nothing is applied).
