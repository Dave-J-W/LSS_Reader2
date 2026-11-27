---
name: synthetic-truth-calibration
description: Check that a synthetic "known truth" in LSS_Reader2 is itself right and looks like the real data before trusting any study built on it - match the noise to real data by measuring the same error statistic on both, check the generator's numerics against a brute-force reference where the curve has a kink, keep the truth's code path apart from the model's, run noiseless first, watch for conditions that change more physics than intended, vary the sampling phase, read parameters at their bounds, and attribute low-count biases to the reference's noise. Use before a replicate run of any estimator study (burn, Qoff, patching, GID, MCA), when a synthetic result and a real one disagree, and when quoting a synthetic condition as "like NX".
---

# Calibrate the synthetic truth before trusting it

Distilled from tools man's P44 burn-shoulder study and the Qoff + σ_Q edge fit (2026-11-27). In both, the
first replicate run had a flaw in the truth, not in the estimator. Do these checks before the long run.

## 1. Match the noise by measurement, not by guess

- **Pick one error statistic that both sides have.** Examples: one frame's template-intensity error σ/I
  (`frame_rel_error`), the mean frame's noise as a share of its peak (`mean_frame_noise`), a point's σ/R.
- **Measure it on the public data and on the generator,** then choose the generator's setting that matches.
- **What went wrong:** P44 first called monitor 1e7 "NX-like". There one frame is known to 0.19 %, while NX
  burns 14 and 15 have 3.8 % and 2.0 %. The matching monitors are 1e4 and 6e4 (`NX_MONITORS` in
  `tests/tools/burn_shoulder_study.py`), and the low-count results changed the study's judgment.
- **Pin the match in a test**, so the claim "as NX" stays true:
  `test_burn_shoulder_study.py::test_the_nx_monitors_give_an_nx_frames_error`.

## 2. Check the generator's numerics where the curve has a kink

- **Compare its smearing or integration with a brute-force reference.** A 40001-point integral is enough.
  Do it at the feature you are studying, not only far from it.
- **What went wrong:** `synthetic.xrr.smear` (31-node Gauss–Hermite) is off by 0.9 % at the critical edge
  at σ_Q 3.8e-4, and by 2 % at 8e-4, because R_F has a square-root kink there. Point errors there are 0.1 %.
- **Fix:** an opt-in rule, here `resolution=(fwhm, 0, 'fine')`. Leave the default alone, so that no earlier
  study's data move, and record it in `docs/SYNTHETIC_DATA.md`.

## 3. Keep the truth's code path apart from the model's

- If the generator and the estimator share a quadrature, a formula or a constant table, known truth only
  checks the estimator against itself.
- **What was done here:**
  - the edge fit integrates by the trapezoid rule on ±6σ, and the truth by Simpson's rule on ±8σ;
  - both are checked against the brute-force integral (`tests/test_qoff_resolution.py`).

## 4. Run noiseless first

- Use the expected counts (`xrr_scans.measure(..., expected=True)`). Every estimate should then come back
  to rounding error. If it does not, find out why before adding noise.
- **What it found:** water's 3 Å Névot–Croce roughness leaves a small kink at Qc that a smooth polynomial
  cannot follow. It biases σ_Q by −8 % (owner's sampling) and +18 % (NX's) at σ_Q 1e-4. With the roughness
  in the model (`roughness=3.0`) the fit is exact to 1e-9; with the roughness off in the generator, too.
- **Report what such a mismatch costs at the realistic values:** under 0.5 % at the beamline's 3.8e-4.
  That decides whether the option matters.

## 5. Check what a condition does to the physics

- **A condition can change more than its name says.** A "300 Å film" denser than water (0.383 e/Å³) moves
  the critical edge to the film's own Qc, so it tested a wrong Qc, not "fringes near the edge".
- **Fix:** a film lighter than water (0.30 e/Å³). The edge stays water's and a fringe of period 2π/d
  crosses the fit's range.
- **Ask:** what else does this condition move: Qc, a level, a width, the counts?

## 6. Vary where the feature falls on the grid

- **An estimator's bias can depend on the sampling phase:** where the edge or peak falls between points.
- **What it found:** the sharp Qoff proposer's bias was −12.7, +1.35, −9.9 and −15.3 × 10⁻⁵ for true Qoff
  −5, −2, 0 and +3 × 10⁻⁴ at one resolution, and −17 at NX's sampling. C50's rule of "about −0.15 ΔQ" was
  one sampling's value.
- **Never turn one condition's bias into a correction rule.** Put several truths of the located parameter
  in the design.

## 7. Read parameters at their bounds for what they are

- **A width bounded at 0 cannot read 0 honestly.** A true σ_Q of 0 read 1.2e-4 ± 0.3e-4, with coverage
  2 %. A true 1e-4 read 0.9 ± 0.3 × 10⁻⁴, with coverage 74 %. Below about 1e-4 the width cannot be told
  from 0 (DATA_NEEDS row 13 found the same on real edges).
- **Flag it** ('sigma_q at its bound') and say "not measured", rather than "0".
- **On real data,** a parameter at its bound plus a large χ²/dof means the model does not describe the
  data. NX scan 6: χ²/dof 102, σ_Q → 0. It does not mean a sharp edge.

## 8. A noisy reference biases nonlinear fits at low counts

- **The effect:** when each item is fitted against an estimate built from the data (the mean frame, a
  template), its noise enters every fit. A parameter that stretches or slides the reference turns that
  noise into a bias.
- **What it found:** on the NX 15-like burn the split's fade read −2.0 pp too deep at NX 15's counts and
  −6.1 pp at NX 14's.
- **Attribute it:** rerun against the noiseless reference. If the bias goes away, it is the reference.
  A smoothed reference is a candidate fix.
- **Check the fix on real data before offering it:** on NX the smoothed reference moved the reads the other
  way (`docs/studies/burn_shoulder/summary.md` §6).

## 9. When synthetic and real disagree

- **Report the disagreement in units of the synthetic spread:** NX 15 sat 1.8–2.0 SD below the expected
  shift.
- **List the explanations the data cannot tell apart,** and hand the question to more real data
  (`docs/handoff_out/10-gid-burn-shoulder.md`).
- **Do not tune the generator to fit one or two real cases.**

## 10. Practicalities of the long run

- **Time a small run first** (8 replicates), extrapolate, then run the full design in the background with
  an exit marker:

      timeout 3600 python tests/tools/<topic>_study.py --out DIR > log 2>&1; echo "EXIT $?" >> log

  Wait with an `until grep -q ^EXIT log` loop: chains of `sleep` are refused in cloud sessions.
- **Do not edit the tool while it runs.** The outputs must match the committed code. Draft the next change
  in the scratchpad.
- **Keep replicate tables small and their bytes reproducible:**
  - 6 significant figures;
  - gzip with `mtime=0`;
  - `replicates.csv.gz` is 237 KB instead of 1.5 MB (`qoff_resolution_study._write_gz`).
- **Before quoting, recompute every number in the prose from the CSV** (fit-statistics-pitfalls item 12).
  Two ratio claims in the P44 summary were wrong until rechecked.
