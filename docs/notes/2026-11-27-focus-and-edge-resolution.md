# The focus sits at S1, and the beam's own core and tail explain most of the edge's width

- **Date, who:** 2026-11-27, data session on the owner's PC (Reflection guy), asked by the owner: "show me how
  the two cases [focus at the S1 slits, focus at the sample] influence what the qz-sigma is … I want to know
  what part of the qz-sigma is explainable." Then the owner removed the earlier beamtimes from the dataset, so the
  numbers below are from the later beamtimes only (285 of 378 edges, 12 runs).
- **Answer:**
  - **Where the focus is.** The beam is wider at the sample than at S1 (core 10.9 → 13.4 µm, tail 28.3 → 55.8
    µm), and σ_Q does not change between S1 0.04 and 0.2 mm. Both fit a focus at S1, not at the sample.
  - **The beam's angles.** With the focus at S1 they are a core of 11.5 µrad (79 %) and a tail of 71 µrad
    (21 %).
  - **How much of σ_Q that explains.** An edge blurred by this beam alone reads σ_Q = 2.5 × 10⁻⁴ Å⁻¹ in a
    one-Gaussian fit, 66 % of the measured 3.85 × 10⁻⁴.
  - **The real edges, refitted with the beam's shape.** They fit better than with one Gaussian (χ²/dof 30
    against 41), need little extra width (median 0.8 × 10⁻⁴; none in 6 of 12 runs), and choose the beam's
    tail fraction (0.22).
  - **What limits this.** One residual pattern remains in every model. So the explained share lies between
    about two thirds and most of it.
  - **Qoff.** It is hardly changed by the model choice (median 8 × 10⁻⁶ Å⁻¹).
  - **The date cut changed little:** with all edges the beam alone gave 67 % and the refit's extra 0.4 × 10⁻⁴.
- **Follow-up, same day** (owner: the removed months had a beam-vibration problem; also "should we sample
  around the critical edge with finer qz steps?" and "did we get some idea how to make our error bars
  honest?"):
  - **The vibration months differ in the plateau, not the edge.** Their points scatter 2.7 × their counting
    errors, against 1.4 × later, with 21 % wild points against 5 %. All 3 of their runs have more wild points
    than any later run (p = 0.011). Their edge width, tail fraction, residual pattern and height-scan beam
    widths are inside the later range.
  - **Finer steps** (0.0005 or 0.00025 from 0.019 to 0.025) would tell the edge's shape: a wrong model's χ²/dof
    rises from 6 to 100–160, the right one stays at 1. Today's steps cannot tell two beam models apart. Known
    truth, `tests/tools/edge_sampling_study.py`.
  - **Error bars:** points scatter 1.12 × (the within-scan study), and 1.4 × on the later plateaus. The edge's
    χ²/dof of 30–41 is the model's shape, not the errors. The σ × 1.12 option still waits for DATA_NEEDS 17a and
    the owner.
- **How it is known:** a run on private files (`sample_data/private/xr/scripts/beamres_refit.py`,
  `beamres_truth.py`, `beamres_publish.py`), plus the calculated `tests/tools/focus_cases_resolution.py`, with
  a known-truth check of both fits. Study: `docs/studies/focus_and_resolution/summary.md`.
- **Numbers that changed:** none (no default touched; a beam-shaped resolution as a default is the owner's
  choice, rule 12).
