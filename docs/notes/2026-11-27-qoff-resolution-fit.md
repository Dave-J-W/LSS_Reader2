# Qoff and the Qz resolution, fitted together at the edge

- **Date, who:** 2026-11-27, tools man. Asked by the owner (2026-11-26: "Qoffset also has to be fit, and this
  could be a useful ability to have in reader"), through xr-data-needs' hand-off 09; issue #154.
- **Answer:**
  - **The method.** `lss_core.fresnel.fit_edge_resolution` fits R_F with the subphase's absorption, smeared by
    a Gaussian of σ_Q. Qoff and σ_Q are free, with Qc and β fixed from the subphase.
  - **On synthetic edges it reads both:**
    - Qoff to about 1e-6 Å⁻¹;
    - σ_Q to 0.5 % at the beamline's 3.8e-4;
    - with honest errors (pull SD 0.85–1.22).
  - **Today's sharp proposal is not the angle offset.** It is off by −35 to +3e-5 Å⁻¹, depending on the
    sampling and on where the edge falls between the Qz points. So C50's "−0.15 ΔQ" holds for one sampling
    only.
  - **On NX school scan 6 the edge is not a smeared Fresnel edge at its errors.** σ_Q goes to 0 (flagged) and
    χ²/dof is 102. So NX alone cannot split its −2.7e-4 into offset and resolution. At the beamline's median
    σ_Q, the offset would be −1.2e-4.
- **Two side findings:**
  - **The synthetic generator's default smearing** (Gauss–Hermite, 31 nodes) is off by about 1 % at the edge.
    A `'fine'` rule is added, and the default is unchanged (`docs/SYNTHETIC_DATA.md`).
  - **Water's 3 Å roughness** leaves a small kink at Qc that the smooth factor misses: −8 % to +18 % of σ_Q at
    1e-4, under 0.5 % at 3.8e-4. `roughness=3.0` removes it.
- **How it is known:**
  - run: `python tests/tools/qoff_resolution_study.py --out docs/studies/qoff_resolution` (200 edges per
    condition);
  - tests: `tests/test_qoff_resolution.py`;
  - study: `docs/studies/qoff_resolution/summary.md`, C71.
- **Numbers that changed:** none. Nothing applies the value, and the Propose button is unchanged.
- **Next:** xr-data-needs runs `tests/tools/qoff_resolution_survey.py` on row 13's private edges (DATA_NEEDS
  row 18).
