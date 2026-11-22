# Hand-off: compare reflectivity patching methods on a large data set

For: an agent with access to the owner's reflectivity data (many SPEC files
with overlapping scans and their Pilatus frames). From: the LSS_Reader2
project, 2026-11-22. The owner asked: "make reusable code for calculating
uncertainty and prepare for later work by a third agent where they compare
methods with a larger dataset, like will be done with GID" (the GID
counterpart is `06-gid-method-comparison.md`; read it as the model).

Read first: `AGENTS.md` (house rules; private data), the design report
`docs/reports/ref_patch_joint_fit.md` (the methods, their equations, the
synthetic and NX measurements, and §9, the plan this hand-off carries
out), `docs/PHYSICS_ISSUES.md` P1, P2, P4, P28, P29, and the xmodfit
contract `docs/handoff/19-lss-reader-covariance-contract.md`.

## The question

Which patching method and settings should become the reader's default for
reflectivity, on evidence from many data sets instead of NX scans 6–9 and
synthetic curves. The decision is the owner's (TODO area B2); this survey
gives the evidence.

| Decision | Now (default) | Alternatives (`lss_core.patching`) | Evidence so far |
|---|---|---|---|
| Factor at a join | legacy: scan b spline-interpolated at a's overlap points, one ratio fitted (`stitching.fitted_factor`) | joint fit of both scans, one polynomial in ln(R/R_F) (`joint_factor`: order, points either side, likelihood); spline ratio in log; coinciding points only | synthetic: joint o4 e4 unbiased within 0.1 %, scatter 20–30 % below the spline ratio; P1 bias of the spline grows with Δln R per point (−0.03 % at 0.27, −2.1 % at 0.95); NX: factors agree within 1σ |
| Order and window | — | order 2, 3, 4; 0–8 points either side; guard (step down when χ² p < 0.01) | order 2 with points either side biased up to −5 %; o4 e4 the proposed default; the guard acts at NX join 8→9 at e6 |
| Prior | Ref Patch's known-ratio choice (`patch_choice`) | foil prior with correlations (`known_steps`), used where Monc/Monp is within 3 % and \|z\| ≤ 3 (`prior_mask`) | 1041 owner joins (committed aggregates): the prior more precise at 10 % of joins, 58 % have Monc/Monp changed ≥ 3 % |
| Uncertainty | the factor's error folded into each point (P4) | φ and Σ carried along the chain; per-point total error and N × N covariance (`Stitched`, `lss_core.uncertainty`) | synthetic slab fits: pull SD of the SLD 3.4–4.8 with the diagonal, 1.07 with the covariance |

## The tool

    python tests/tools/ref_patch_survey.py --spec FILE [--spec FILE ...] --out DIR [--split] [--repeats]
    python tests/tools/ref_patch_survey.py --list sets.csv --out DIR [--split] [--repeats]

Run from the repository root. `--spec` finds the reflectivity series of a
SPEC file (`lss_core.series.all_series`, kind 'reflectivity'); `--list`
gives them by hand (CSV lines `spec,scans[,label]`, scans separated by
`;`). Each set is reduced once (`Experiment.reflectivity(..., errors=
'budget')`) and every method run at every join (`METHODS` in the tool;
add yours there). Seconds per set. Private data: `--out` under
`sample_data/private/` or outside the repository (the tool checks).

A worked example on the public NX file is committed:
`docs/comparisons_data/ref_patch_nx/`.

## The outputs

`joins.csv`, one row per set × join × method:

| Column | Meaning |
|---|---|
| set, join, scan_a, scan_b, method | what was run (`legacy`, `interp`, `interp_log`, `coincident`, `joint_o2_e0`, `joint_o4_e2`, `joint_o4_e4`, `joint_o4_e4_raw`, `joint_o4_e4_log`, `joint_o4_e4_prior`) |
| energy_kev, n_a, n_b | energy, absorber settings |
| q_lo, q_hi, q_class | the overlap; class `<0.05`, `0.05-0.25`, `>=0.25` |
| points_a, points_b, coincident | points in the overlap; how many Qz coincide |
| n_ext, order, space, likelihood, window_reduced, flags | the window and model actually used (the guard may reduce it) |
| delta, factor, err, err_counting, chi2_dof, dof, p_chi2 | the fit: δ = ln f (f multiplies scan b), reported error (inflate-only) and counting error |
| d_legacy_sigma | (δ − δ_legacy)/err |
| known, known_err, z_known | the foil ratio and its error; z = (δ − ln known)/√(err² + known_err²) |
| prior_used, why | for `joint_o4_e4_prior`: whether the prior was used at the join and why not |
| monc_monp_ratio | Monc/Monp of b over a in the overlap (P29) |
| seconds, error | |

`sets.csv`, one row per set × method: φ (each scan's log factor to the
first), √Σ per scan, `sqrt_sigma_last` (the last scan's level
uncertainty), `max_total_over_meas` (how much the factors' error adds to
the largest per-point error), joins flagged.

`split.csv` (`--split`): each scan of ≥ 20 points split into two halves
overlapping over 8 points, the second × 0.8 (truth f = 1.25), on real
curve shapes, noise and background. `interleaved`: the overlap's points
alternate between the halves (independent noise, staggered grid): bias
and pulls are meaningful. `shared`: both halves hold the same points
(same noise): only the bias is meaningful.

`repeats.csv` (`--repeats`): where a scan was repeated (identical Qz),
each repeat joined to the scan before it; the factors' difference against
√(σ₁² + σ₂²) (an empirical pull; non-counting noise between measurements
shows here and not in the split test).

`summary.md`: per method, joins, median error, median χ²/dof, flagged;
the split-truth bias and pull SD per variant.

## How to judge (suggested, in order; report §9)

1. **Split truth** (interleaved): bias < 0.2σ and pull SD 0.9–1.15 per Qz
   class, per method. The method that passes everywhere with the smallest
   error wins; look at the worst class, not only the median.
2. **Repeats**: empirical pull SD ≈ 1 for the reported errors.
3. **Clean joins against the foils** (Monc/Monp unchanged): robust SD of
   z_known ≈ 1 by Qz class. (The foils were fitted on the owner's joins,
   so this is independent of the method only out of sample:
   `docs/handoff_out/03-answer/` has the leave-one-run-out check.)
4. **χ² of the joint fit** by Qz class and order: the fraction with p <
   0.01 should approach 1 % for an adequate model; more at high Qz
   measures excess (non-counting) scatter, which belongs in the per-point
   error model.
5. **Window and order**: from the split truth, RMSE against points either
   side (0–8) and order (2–4) per Qz class: confirm or change o4 e4; how
   often the guard steps down.
6. **Prior**: on clean joins, the error reduction and bias of the combined
   estimate, and its agreement on real joins.
7. Report as `06` asks: a table per decision, a recommendation, private
   numbers only in the owner's channel, and proposed rows for
   `docs/OUTPUT_DECISIONS.md` with before/after values (factor change per
   join, √Σ of the last scan).

## Known caveats

- **The legacy row** is `stitching.fitted_factor` on the two scans alone;
  the window's patch fits each new scan against everything stitched so far,
  which can differ slightly where three scans overlap.
- **P29**: at joins where the slits changed, Monc/Monp changes and the foil
  ratio is not the scale; the prior is not used there (`prior_mask`), and
  `z_known` there is not a test of the method.
- **Low counts**: the log-space likelihood (`joint_o4_e4_log`) is biased at
  about 10³ counts per point (+2 to +10 %, report §5); the default
  Poisson-like likelihood is not.
- **The stitched-curve covariance** is reported (`Stitched.covariance`) but
  nothing exports it yet: export and saving are the owner's decisions
  (TODO area B2).

## Privacy

`AGENTS.md`: the owner's data are private (git-ignored). A few derived
numbers in committed documents are acceptable, but never raw data,
curves or images. Keep survey outputs of private data under
`sample_data/private/` or outside the repository.

## Code map

| What | Where |
|---|---|
| Survey | `tests/tools/ref_patch_survey.py` |
| Joint fit, prior, chain, global fit, stitched output | `lss_core/patching.py` |
| Covariance of chained factors and stitched data, combination with a prior, pulls | `lss_core/uncertainty.py` (reusable for GID joins) |
| Legacy patch | `lss_core/stitching.py`, `lss_core/reflectivity.py` (`patch`, `patch_choice`, `monitor_change`) |
| Foils | `lss_core/absorbers.py` (`Foils.step`, `calibrated`) |
| Design, measurements, prototype descriptions | `docs/reports/ref_patch_joint_fit.md` |
| Tests | `tests/test_patching.py` (invariants, Monte Carlo, NX), `tests/test_stitching.py` (legacy) |
| Synthetic reflectivity with known truth | `tests/synthetic/xrr.py`, `xrr_scans.py`, `xrr_images.py`; `docs/SYNTHETIC_DATA.md` (water–air interface, Kiessig fringes, scans split with known factors and planted faults; legacy factor 16.7 % low when a staggered overlap straddles Qc) |
