# Excess scatter with and without R_F; the beam's convergence and angle jitter (C63)

- **Date, who:** 2026-11-26, the data session on the owner's PC (questions from the owner). Written for the
  `physics_notes` log on its branch before the log was frozen; moved here unchanged when #127 was merged
  (2026-11-27, main man).

Verified by: a run of the private `sample_data/private/xr/scripts/scatter_fresnel_angle.py` on the private
runs (26,182 windows) and the released series (4,561), with known-truth checks on synthetic water, DPPC and
a 100 Å film. Study: `docs/studies/excess_scatter/summary.md`, "Fresnel division, the beam's convergence and
angle jitter".
- **Q.** (owner) Is the excess measured on Fresnel-normalised data, and what are the results before and after?
  **A.** Yes, on ln(R/R_F); without R_F the same windows give the same numbers to three decimals (private
  core 0.14 %, outliers 1.8 %, s 1.116; released 0.21 %, 3.2 %, 1.065). Above Qz 0.04 the window's weights
  cancel ln R_F (d moves by a median 0.000–0.002 σ_d). So no Qoff can change it either.
- **Q.** (owner) How does the beam's angular convergence play in? **A.** As resolution (37 µrad rms) it only
  smooths the curve: the 6-point window's spread on known truth is the same at FWHM 6.5, 8.9 and
  12.6 × 10⁻⁴ (DPPC 1.04, film 1.25–1.29). Point-to-point angle jitter would be scatter, but its joint fit
  failed known truth (it reads curve shape near minima as jitter), so the real values (about 2 µrad) are
  not measurements; the excess does not fall as 1/Qz, so jitter is not its main source.
- **Caveat found on the way:** DPPC with no excess reads a core of 0.12 % [0.08, 0.16] on known truth, as
  large as the private 0.14 %. The firm result is s ≈ 1.12.
- **Owner:** Qoff and the resolution should be fitted together in the reader; after 2.0
  (`docs/RELEASE_PLAN.md`).
