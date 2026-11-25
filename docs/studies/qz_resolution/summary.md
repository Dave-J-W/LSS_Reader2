# Qz resolution near the critical edge at 10 keV (DATA_NEEDS row 13, F79, C50)

The owner's non-cloud agent, 2026-11-24, at the owner's request ("you can leave a request for local
yokel"). **Measured on real data**: the first scan of every reflectivity series in the owner's private
beamline data that crosses the critical edge (Qz from below 0.019 to above 0.026 Å⁻¹). That is 400 scans
from 17 runs, all at 10 keV (Si(111)), all in steps of 0.001 Å⁻¹. Runs are labelled `E01`… by a hash (not
the labels of `docs/studies/xr_burns/`). No curve, image, name, date or scan number is here: the tables
hold fitted numbers only.

**Not regenerable here.** The private generator lives under `sample_data/private/xr/scripts/edge_*.py` on
the owner's computer:
- `runs.csv`: per run;
- `variants.csv`: the fit's sensitivity;
- `slits.csv`: the slit comparison;
- `numbers.json`: everything quoted below, including the known-truth check.

## The answer

| | |
|---|---|
| **ΔQ (FWHM) at the edge, 10 keV** | **8.9 × 10⁻⁴ Å⁻¹** (σ_Q 3.8 × 10⁻⁴), median of 378 scans |
| Spread between scans | quartiles 7.7–10.6 × 10⁻⁴ (FWHM) |
| Spread between runs | run medians 6.5–12.6 × 10⁻⁴ (16 runs with ≥ 4 scans) |
| Within one run | about ±15 % (median robust SD 5.7 × 10⁻⁵ in σ_Q) |
| As an incidence-angle spread | 37 µrad rms (σ_Q = (4π/λ) σ_α) |
| Depends on the slits? | **No detectable dependence on S1 between 0.04 and 0.2 mm.** In the one run with both, S1 0.04 mm gives σ_Q (3.38 ± 0.08) × 10⁻⁴ and 0.2 mm gives (3.41 ± 0.75) × 10⁻⁴. The footprint grows ×5 and the width does not. S1 0.02 mm is **not determined**: 11 scans in one run; the fits scatter (6.3 ± 3.0 × 10⁻⁴), and 3 are ill-conditioned. S1's horizontal gap: 1 mm 3.9, 2 mm 3.7 (× 10⁻⁴, σ_Q; pooled, not within one run) |
| What it does to a proposed Qoff (C50: −0.15 × ΔQ FWHM) | **−1.3 × 10⁻⁴ Å⁻¹** (runs: −1.0 to −1.9 × 10⁻⁴) |

So the resolution explains about half of the NX file's proposed Qoff (−2.8 × 10⁻⁴) and about a quarter of
the owner's typical −5 × 10⁻⁴. The rest is a true angle offset, or a Qc other than the one assumed: C50
showed Qc and Qoff are almost degenerate.

## How it was estimated

**The edge's width, scan by scan.** The reader's background-subtracted reflected intensity per Monc
(`Experiment.reflectivity` on the one scan, the window's Ref Patch arithmetic), with its counting errors,
is fitted by

    R(q) = N · [R_F(q; q_e, β) ⊗ Gauss(σ_Q)](q) · (1 + a u + b u²),   u = (q − q_e)/q_e,

over 0.6 q_e ≤ q ≤ 0.030 Å⁻¹, with a soft-L1 loss for the odd spike.
- q_e is the edge as measured: the subphase's Qc and any Qoff together.
- β is water's absorption at 10 keV (5.2 × 10⁻⁹).
- The smooth factor takes up the film above the edge and the plateau's tilt. Without it the data run 2–20 %
  above R_F and χ²/dof is about 200. A smooth factor cannot make a sharp edge wider, so the width comes from
  the edge.

**Is it the resolution, or the fit?** (figure E1, right; `variants.csv`)

| change | median FWHM (10⁻⁴ Å⁻¹) |
|---|---|
| chosen | 8.89 |
| q ≤ 0.028 or 0.034 | 8.75, 8.99 |
| a linear factor, least squares | 9.16 |
| no factor, least squares | 9.51 |
| absorption × 0 or × 2 | **10.05, 7.45** |

The subphase's absorption is the one input that matters: ±15 % for a β wrong by a factor of 2. A salt
subphase absorbs more than water, so it would give a narrower resolution than quoted here.

**Known truth** (figure E2, left): synthetic scans with the same sampling and counts. The estimator gives
3.79 ± 0.10 for a true 3.7, 6.06 for 6.0, 2.05 for 2.0 (× 10⁻⁴, σ_Q), within 2 % near the real value. This
holds with per-point Qz jitter of 1–2 × 10⁻⁵ as well. Below about 1 × 10⁻⁴ it cannot tell the width from 0.

**The fits' own errors are too small** (figure E2, right): about each run's median, the scans scatter
3.5 × their fit errors (robust SD of the pulls), with 23 % inside ±1. Under per-point jitter the synthetic
pulls also widen (SD 2–4). So quote the between-scan scatter, about ±15 % within a run, not the fit error.

## The budget: what makes the edge 37 µrad wide?

| term | size, as σ_Q (10⁻⁴ Å⁻¹) | how known |
|---|---|---|
| beam convergence (the mirror's focus), Θ | **≈ 3.8: the whole width** | from the edge, by elimination of the others |
| the same from the direct beam's width at the detector | ≤ 7.5 (Θ ≤ 74 µrad rms) | a bound: the reflected spot is 0.24 px rms (0.312 mrad/px, 551 mm), 95 % in one pixel; less the beam's 13 µm at the sample (`docs/studies/sh_beam_size/`) |
| slope spread of the curved surface over the footprint | ≲ 1.5 | the reflected spot is as narrow as the direct one (0.245 px against 0.24–0.26 px); S1 ×5 (footprint ×5) leaves the width unchanged |
| mono bandwidth, Si(111), Δλ/λ ≈ 1.3 × 10⁻⁴ | 0.01 | literature value (read), with Qc · Δλ/λ / 2.355 |
| per-point angle errors | none (they add scatter, not width) | the synthetic check |

So the resolution near the edge is the beam's angular spread. That is set by the focusing, not by S1 at
0.04–0.2 mm, which is why it changes from run to run (6.5–12.6 × 10⁻⁴ FWHM) and not with the slits. At
another energy, a fixed Θ gives ΔQ ∝ E (4π/λ). Only 10 keV was measured here.

## Not shown, and why

- **The NX school file (public)**: its scan 6 starts at 0.0175 in steps of 0.00125, with two points below
  the edge, at S1 0.02 mm. The fit collapses to σ = 0, which is not a measurement. Refused.
- **22 scans** whose fit has no error (ill-conditioned): left out, 3 of them at S1 0.02 mm.
- **qe** (the measured edge) per run: not published. It mixes the subphase's Qc and the offset. Median
  0.02190 Å⁻¹.
- **A non-Gaussian resolution:** the beam has a core and tails at the sample (row 9). A resolution with
  tails would fit differently; not tried.

## For the reader

- R_F with a Gaussian resolution of σ_Q ≈ 3.8 × 10⁻⁴ Å⁻¹ near the edge would make R/R_F continuous through
  the edge without a fake Qoff. The proposer (`fresnel.propose_qoff`) and the reader's R_F model none (qoff
  study, §3).
- A default would need rule 12: a study with known truth (this one is on real data, plus the synthetic
  check) and the owner's choice.
