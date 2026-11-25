# Physics notes and Q&A log

Running record of questions asked during the work on this fork and the answers
given, with emphasis on invariant quantities. Newest entries at the bottom.
Each entry says whether the answer was verified (by test, by running, or by
reading only).

## Invariants

Collected here as they are established; each should point to a test once one
exists.

| # | Invariant | Status |
|---|---|---|
| I1 | Fresnel reflectivity R_F(q) = 1 for q ≤ q_c | tested: `test_fresnel.py` |
| I2 | R_F(q) → (q_c / 2q)⁴ for q ≫ q_c, and R_F depends only on q/q_c | tested: `test_fresnel.py` |
| I3 | Monitor-normalised intensity I/M has σ² = σ_I²/M² + I²/M³; for Poisson I, (σ/R)² = 1/I + 1/M | tested: `test_twod_detector.py` |
| I4 | Background-subtracted ROI signal S − (L+R)/2 is 0 on a flat image; each box error is the root-sum-square of its pixels, so σ² = σ_S² + (σ_L² + σ_R²)/4 | tested: `test_twod_detector.py` (the final combination is one inline line in `mainwindow.py`, read only) |
| I5 | Normalised GID footprint area lies in (0, 1], is 1 at small 2θ and falls once clipped | tested: `test_gid_area.py` |
| I6 | At the direct-beam row with α = α_true, Q_z = 4π sin α / λ; at the direct-beam column with Det_Th = 0, Q_xy = 0 and the axis is antisymmetric | tested: `test_twod_detector.py` |
| I7 | Stitching two scans of one curve recovers the attenuation factor exactly, and overlap errors fall by √2, when the overlap points coincide | tested: `test_stitching.py` |
| I8 | Reduced reflectivity of each scan is proportional to the true curve (R/R_F flat) | tested end to end on synthetic data: `test_gui_workflows.py` |
| I10 | Every row of the scan-weight matrix W sums to 1 (simple-chain overlap rows exactly ½/½); Σ is symmetric, positive semi-definite, with zero row and column for the anchor scan, a random walk for one-hot a_m and the §3.4 recursion otherwise; corrected error ≥ counting-only error, equal on the anchor scan's points outside any overlap; the sidecar's x and y equal its data file's columns | tested (2026-11-22): `test_covariance_export.py::test_weights_sigma_and_total_error`, `test_written_sidecars_load_and_match_their_files`, `test_oracle_agrees_with_the_corrected_chain`; window: `test_gui_covariance_export.py` |
| I27 | One scan has no stitching error: Σ = 0, the sidecar has `terms: []`, σ_total = σ_meas | `test_covariance_export.py::test_single_scan_has_no_stitch_term` |
| I28 | The data covariance C = diag + W Σ Wᵀ is symmetric positive definite; per-point scaling (normalisation, Fresnel division) leaves C_log unchanged and scales C_lin by D⁻¹·D⁻¹; Q_z offset moves x only; sorting, removal and Q cuts select rows and columns of C; averaging gives the linearised W row (checked by Monte Carlo); a join of two sets adds the link's variance to every scan of the second | `test_covariance_export.py` (`test_permutation_*`, `test_scaling_*`, `test_finish_*`, `test_average_*`, `test_concat_*`), `test_gls.py::test_covariance_is_symmetric_positive_definite` |
| I29 | The GLS χ² rᵀC_log⁻¹r equals the χ² minimised over one log scale shift per scan with the Gaussian penalty φᵀΣ⁺φ (nuisance or "pull" form), exactly, with and without a free overall scale; the Woodbury solve and log-determinant equal the dense ones | `test_gls.py::test_gls_chi2_equals_the_nuisance_form`, `test_woodbury_solve_and_logdet_equal_the_dense_ones` (to 1e-9) |
| I11 | On a specular frame the direct beam lies at Q_z = 0 and the reflected beam at the frame's Q_z, 2α apart on the detector | tested on real data: `test_real_nx_school.py` (NX school scan 7, frame 0; both within 1.5 pixels, separation within 8 %) |
| I12 | A signal decaying as exp(−t/τ) under the beam is reduced to the same decay and the burn-test fit returns τ | tested on synthetic data: `test_burn.py` (τ within 0.5 %) |
| I13 | A window sum over an MCA line returns counts / monitor × (real / live time); a Gaussian fit returns the line's position, width and height | tested on synthetic data: `test_xfntr.py` |
| I14 | (for F47, when built) A silicon-detector escape peak lies 1.74 keV (Si Kα) below its parent line, with a small fixed fraction of the parent's counts; summing parent and escape conserves the line's counts | cited from memory (standard Si(Li)/SDD behaviour; see XrayDB); no code yet |
| I15 | (budget error model; monitor model by default a Gaussian of σ = 0.04 % at every count, owner 2026-11-17) The variance of any sum over one frame is its counting variance plus (sum)²·u_M²: box, line-cut point, energy window, and background-subtracted net (monitor term on the net, not on the boxes); averages of frames add each frame's monitor amplitude in quadrature; a frame subtracted from itself has no monitor term | tested: `test_error_budget.py` (formulas, and a Monte Carlo of a bright box with a 1 % monitor: predicted σ within 10 % of the scatter, legacy σ < 1/3 of it), `test_gui_error_budget.py` (cuts, summed cuts, MCA sum, Ref Patch) |
| I16 | The error model changes errors only: values are identical in both models up to the patch's scale-factor fit, which is weighted by the errors | tested: `test_error_budget.py` (NX school scans 6–9, per-frame columns identical), `test_gui_error_budget.py` (patched values within 0.5 %) |
| I17 | Normalised fluorescence does not depend on the absorber setting: counts measured at setting n (attenuated by absfac⁻ⁿ; monitor upstream of the foils, unchanged), multiplied by absfac**n, equal those at n = 0 (exact for expected counts, within Poisson scatter for drawn ones). Holds only if absfac is right for the energy and the setting is right (for MCA scans, inferred from the last `#A`) | tested on synthetic data: `test_fluorescence_absorber.py` |
| I18 | With the monitor-gain option, one flux measured at two SR570 sensitivities gives one normalised value: M ∝ 1/S, and the value is multiplied by S_ref/S (exact for expected counts). Requires the recorded gain to be the gain in use | tested on synthetic data: `test_monitor_gain.py` |
| I19 | Absorber factor per unit = exp(μ/ρ(E)·ρ·t), 50 µm Al at E ≤ 10 keV: at the table energies μ/ρ equals the NIST SRD 126 rows exactly, it falls monotonically between them, and 10 keV gives the 1.4247 default; where the foil is not known no factor is made up | tested: `test_absorbers.py`; in the window `test_gui_absfac_energy.py` (a 6.21 keV MCA export is (4.0924/1.4247)³ times the 10 keV one at n = 3, and the Script pane reproduces it) |
| I20 | With the "per photon" option, one photon flux read at two SR570 sensitivities, with the dark rate added to each monitor rate, gives one value I/N: the factor M/N = 1/(q(E)·S/(500 nA/V)·(1 − D/r)) undoes both. Requires the recorded gain to be the gain in use and D to be the true dark rate; the absolute scale is as good as q(E) (±3.6 % below 13 keV) | tested on synthetic data: `test_per_photon.py` |
| I21 | Pinhole binning conserves counts (ΣN in = ΣN out), each bin is ΣN/ΣW, and at 0.4 counts per pixel the estimate is unbiased (1.00 ± 0.01); joining Qz levels conserves counts | `test_pinhole.py::test_counts_are_conserved_and_bins_are_count_over_weight`, `test_low_counts_are_unbiased`, `test_join_conserves_counts` |
| I22 | For Poisson points (y = N·a/M, σ = √N·a/M) the MCA Merge equals ΣN/Σ(M/a) with σ = √ΣN/Σ(M/a), exactly, also merged pairwise | `test_mca_merge.py::test_merge_of_poisson_points_is_pooled_counts_over_pooled_monitor` |
| I23 | Point times within a scan never go backwards, and no step is shorter than the count time | `test_timing.py::test_nx_school_steps_never_go_back_or_undercut_the_count_time` |
| I24 | Exact pinhole angles equal an independent ray construction; on the direct-beam column they are exact at any β0 | `test_pinhole.py::test_pixel_angles_are_the_exact_ray_geometry` |
| I25 | A quantity constant in time is called stable (AICc(constant) − AICc(linear) ≤ 2) in ≥ 85 % of noise draws (measured 95 %); the 95 % confident time to a 5 % change exceeds the true time in ≤ 9 % of draws (measured 5.5 %) | `test_trends.py::test_the_confident_time_is_conservative_at_its_stated_level` |
| I26 | A burn signal decaying as exp(−t/τ) gives τ from the exponential model and a 5 % time of τ·ln(1/0.95) | `test_burn_trends.py::test_reflectivity_burn_is_monitor_normalised_and_finds_tau` (τ 400 s, 20.5 s) |
| I30 | A figure tool is deterministic: rerun with the settings of its committed figures on unchanged code and inputs, it gives them back pixel for pixel (the measured test of staleness; a provenance stamp, where a tool prints its git revision, differs inside one small box) | `test_toolbox_gui.py::test_a_figure_tool_reproduces_its_committed_figures` (burn trends, 4 of 4); measured 2026-11-23: the ngui prototype screenshots 23 of 23, the fit demonstrator figures 6 of 6 |
| I31 | A pinhole join factor (scans of a level, or Qz levels) is unbiased whatever the counts per bin: the likelihood of how each bin's counts split between the two sides (`pinhole.ratio_ml`, P46) gives back a known factor within ±0.1 % down to 0.026 counts per pixel; equal to the pooled ratio of a single bin | `test_pinhole.py::test_level_factor_is_unbiased_at_low_counts`, `test_ratio_ml_is_the_pooled_ratio_for_one_bin_and_recovers_a_scale` |
| I32 | "Sum All" of Poisson frames (y = N·A/(M·g), σ = √N·A/(M·g)) equals ΣN/Σ(M/A·g) with σ = √ΣN/Σ(M/A·g), exactly; it is the mean of the per-frame values weighted by M/(A·g), and with equal monitors and absorbers the plain mean | `test_monc_normalised.py` (`test_sum_frames_is_the_counts_over_the_monitors`, `test_frames_with_absorbers_are_summed_by_their_effective_monitors`, `test_the_scripted_summed_cut_is_the_counts_over_the_monitors`, `test_the_windows_summed_cut_is_the_counts_over_the_monitors`); the identical-scans merge the same per point, also one repeat at a time (`test_repeats_merge.py::test_merge_identical_is_the_counts_over_the_monitors`) |
| I33 | Every photon of a synthetic MCA spectrum lands in exactly one part: photopeak + tail + shelf + escape = the photons of each source (`synthetic.mca`, to 0.2 % where the channels cover everything); the gauntlet's truths rest on it (F90) | `test_synthetic_mca.py::test_every_photon_lands_in_one_part` |
| I34 | On the Angles axis of a 'Pix V' cut through the reflected beam's columns, the reflected peak of a specular frame is at β = α (α = arcsin(Qz λ/4π)); NX school scans 6, 8, 9 to 2e-4° | `test_true_incidence.py::test_the_reflected_beam_sits_at_beta_equal_alpha` |
| I35 | L is Qz in Å⁻¹ (the beamline's SPEC lattice): L = (2π/λ)(sin α + sin β), α = In_Rot, β = Out_Rot; in a specular scan 4π sin α/λ. On NX school every scan at fixed L agrees to better than 0.001 % (scans 4, 5, 10–15; scan 12 at the raised GID level, β = 6.5°); a fixed-L scan off by more than 1 % is noted at load (`LMismatch`) | `test_lattice.py::test_nx_l_is_qz_at_every_fixed_l_scan` |
| I36 | Ref Patch steps are reversible: going Back (undoing a drop, or an accepted join) and doing the same steps again gives the same curve value for value as never going back; a cancelled patch leaves the curve on show and its Script line as they were (F96, owner Q-UI-B7). Not yet held: an accepted join must not change when live data arrive (B7's added rule; the live replay is not built) | `test_gui_ref_patch_steps.py::test_back_then_the_same_steps_give_the_same_reflectivity`, `::test_cancel_says_so_and_leaves_the_result_on_show` |
| I37 | The residual panel shows what the fit minimised: over the fitted points Σ((y − fit)/σ)² = χ²/dof × (N − p), N − p an integer with p the fit's parameter count; for Poisson data with σ = √y and a right model the weighted residuals have mean ≈ 0 and SD ≈ 1 (F74). For burn trends Σr² is the best model's χ² itself (to 1e-9, every model on the synthetic burn) | `test_residuals.py::test_the_residuals_are_those_the_fit_minimised`, `::test_burn_trends_get_the_best_models_residuals` |
| I38 | The ROI close-up outlines the pixels the reduction sums: summing a frame over `lss_core.display.roi_boxes(slit, cen, bg, direction)` gives `TwoDDetector.sumROI`'s signal and background values exactly, for any slit, centre, offset and direction (its slit − 2 and integer background centres included, PHYSICS_ISSUES P12) | `test_roi_boxes.py::test_summing_over_the_drawn_boxes_gives_sumROIs_values` |
| I39 | The dose of a point is what the reduction already divides by: in monitor counts it is the point's weight in "Sum All", M/(A·g) (`cuts.frame_normaliser`); in photons, the flux route's photons/s × its seconds / A (`flux.photons_per_second`); a scan's dose is the sum of its points'; at a constant monitor rate and absorber the dose axis is the exposure axis × that rate, so a burn's dose limit is its time limit × the rate | `test_dose.py` (every test; the last on the synthetic burn, to 1e-6) | 2026-11-24 |
| I40 | Every row of a patched curve sits at the Qz of one raw point, its origin (`reflectivity.drop_points`), and a drop of a point that no earlier join's fit used gives the same curve, value for value, as masking that point from the start (both methods) | `test_gui_ref_mask.py::test_drops_are_kept_and_left_out_from_the_start_next_time` (the window, 2026-11-25), `test_masks.py::test_every_patched_row_sits_at_its_origin_point`, `::test_a_drop_of_a_point_no_earlier_join_used_is_its_mask`, `::test_reflectivity_leaves_the_masked_points_out` | 2026-11-24 |
| I41 | On a specular frame (α_i = α) the reflected beam's row is at β − α = 0 and β = α, and its Qz is the frame's Qz; its column is at Qxy = 0. A diffuse-cut axis changes only a cut's x values, never its intensities | `test_diffuse_axes.py::test_the_specular_row_is_at_beta_minus_alpha_zero`, `::test_the_intensities_are_the_cuts_own`; in the window `test_gui_cut_axis.py::test_diffuse_axes_change_x_only`, `::test_beta_minus_alpha_puts_the_specular_row_at_zero` (2026-11-25) | 2026-11-24 |
| I42 | For a knife edge through a Gaussian beam of σ, the beam height returned for the dose is √(2π)·σ (the inverse of the profile's peak; 1.0645 × the rising FWHM), within the fit's noise, whatever the step; a refused height scan says which guard refused it | `test_beam_height.py::test_the_height_is_root_2pi_sigma`, `::test_the_guards_refuse_what_the_study_refused` | 2026-11-24 |
| I43 | At most one reader holds a workbook's lock at a time, even when two take over a stale lock at once (each reads the lock back after writing it); a read-only workbook never writes (`save` raises `WorkbookReadOnly`, the file and its folder untouched) | `test_readerlock.py` (every test); in the window `test_gui_reader_lock.py` (2026-11-25) | 2026-11-25 |
| I9 | Footprint fraction is the same at +2θ and −2θ for symmetric slits | **violated** by 2 % at 20°; pinned as expected failure in `test_gid_area.py` |

## Q&A

### 2026-11-14 — What is in LSS_Reader and what state is it in?

**Q.** Familiarise with the repository ahead of verification tests, debugging,
refactoring, new features and GUI reorganisation.

**A.** See [ASSESSMENT.md](ASSESSMENT.md). In short: a single 5400-line Qt
class holds the GUI and all physics; there are no tests; 18 defects were found
by reading, of which the most serious for users on current SciPy is that GID
multi-scan patching depends on the removed `interp2d`. The physics that tests
must preserve is tabulated in section 2 of the assessment.

Verification: source read; app launched headless; defects not yet reproduced.

### 2026-11-14 — Test scaffolding; what did the first tests find?

**Q.** Set up test scaffolding. Known pain points: the Python 2 → 3 move was
incomplete, and the interface should never crash whatever files are selected
and whatever buttons are pressed afterwards.

**A.** See [TESTING.md](TESTING.md). The fast suite has 47 passing tests and
8 strict expected failures. All of the following were measured by running the
code on synthetic data (`tests/synth.py`), not on beamline files.

Numerical findings:

- **Stitching bias.** When the second scan has no point at a Q_z of the first
  scan's overlap region, `oneDjoin` interpolates it with a cubic spline in
  linear intensity. On a Fresnel-like curve with overlap 0.04–0.05 Å⁻¹ and a
  true factor of 1.420 it returns 1.4037 (sum mode) or 1.4013 (weighted-fit
  mode), 1.2–1.3 % low, and every point beyond the overlap inherits that. The
  reported relative error there grows from 0.1 % to 1.3 %. With coincident
  points the factor is exact to 1e-12. Interpolating log R instead is the
  obvious candidate fix; not yet tried.
- **Footprint asymmetry.** `calArea` gives 0.7355 at 2θ = +20° and 0.7218 at
  −20° for symmetric slits (invariant I9).
- **"FWHM" in the SpecPlot title.** For a Gaussian of true FWHM 0.471 the
  title reports 0.406, because the tanh-edged box model is tried first and
  its width is what gets printed.
- **ROI clipping.** The default reflectivity ROI (11 pixels across) collects
  99.4 % of a σ = 2 pixel Gaussian. This is a constant factor, so it cancels
  in normalised reflectivity as long as the beam shape on the detector does
  not change with Q_z.
- End to end, the normalised stitched reflectivity of the synthetic data
  stays within 2 % of the generating curve; the whole shortfall is the
  stitching bias above.

Crash findings are in `tests/known_crashes.json`; see the next entry.

### 2026-11-14 — Which controls crash, and in which states?

**Q.** The interface should not crash whichever files are selected and
whichever buttons are pressed. Where does it crash today?

**A.** Measured by `pytest -m sweep` on the synthetic data set; method in
[TESTING.md](TESTING.md), full list in `tests/known_crashes.json`.

*Single controls, each in a fresh window.* 420 control/state combinations
raise, from 41 distinct code sites, across 79 distinct main-window controls.
The result is identical whether file dialogs are cancelled or return a path.

| State | Controls that raise | of which inside a dialog |
|---|---|---|
| nothing loaded | 78 | 2 |
| SPEC file loaded | 77 | 2 |
| motor scan selected | 66 | 4 |
| Pilatus scan, no frames | 66 | 4 |
| Pilatus, one frame | 30 | 4 |
| Pilatus, two scans, all frames | 29 | 2 |
| MCA frames | 74 | 2 |

Most frequent sites:

| Count | Exception and function |
|---|---|
| 90 | `AttributeError in mainwindow.py:update2dPlots` |
| 56 | `IndexError in mainwindow.py:refQzListSelectionChanged` |
| 49 | `ValueError in mainwindow.py:update2dPlotPlot` |
| 40 | `AttributeError in mainwindow.py:updateCutData` |
| 20 | `AttributeError in mainwindow.py:updateCutPlotData` |
| 10 | `AttributeError in mainwindow.py:refPlotWin` |
| 7 | `AttributeError in mainwindow.py:saveCutData` |
| 7 | `AttributeError in mainwindow.py:savePeakFit` |
| 7 | `IndexError in mainwindow.py:savePeakPara` |
| 7 | `AttributeError in mainwindow.py:removeMcaFiles` |

By type: AttributeError 272, IndexError 70, ValueError 49, TypeError 17, KeyError 12.

The pattern is uniform: handlers read attributes that only exist after some
earlier action (`self.det`, `self.selectedPilFramesNums`, `self.xcenter`,
an item in the Qz list, …) and nothing checks that the action happened. The
counts fall as more data is selected because more of those attributes exist.

*Sequences.* Nine random walks of 150 steps (three seeds from each of three
states, nothing reset between steps) reach 11 further sites that no single
control reaches from a clean state (`tests/known_crash_sites.json`):

- `AttributeError in mainwindow.py:updateRefPilPlotData`
- `IndexError in mainwindow.py:fitPeakFit`
- `IndexError in mainwindow.py:g_l2plot`
- `IndexError in mainwindow.py:imageSelectedScanChanged`
- `IndexError in mainwindow.py:pilBurnTest`
- `KeyError in mainwindow.py:updatePilPlotData`
- `TypeError in mainwindow.py:g_lfunction`
- `TypeError in spec_routines.py:APS_9IDC`
- `UnboundLocalError in mainwindow.py:updateSpecPlotData`
- `ValueError in mainwindow.py:mcaPlotSettings`
- `ValueError in mainwindow.py:updateRefPilPlotData`

Method note. An earlier version of this entry reported 368 combinations.
That sweep reused one window per state, so a setting changed by one control
(for example switching the beamline to 9-ID-C) leaked into the results for
later controls, and it did not look inside dialogs. The numbers above
replace it.

Not covered: dialogs opened from dialogs, Bruker images (unreadable at
present), mouse interaction with plots, real data in the sweep (it uses the
synthetic set).

### 2026-11-14 — Does the program reduce real beamline data?

**Q.** Use the example files (`NX_school`, `bu`) as sample data.

**A.** `NX_school` (2026 school data, DPPC monolayer, 15 scans, 276 Pilatus
frames) is in `sample_data/NX_school/`. `bu` is not in the repository yet.

Measured by running the program on it (`tests/test_real_nx_school.py`,
`pytest -m slow`):

- The SPEC file parses; every one of the 15 scans opens and shows its first
  frame without raising. Scan 12 lists 4 frames although 5 images exist (the
  scan was stopped early).
- Scans 6–9 stitch into an 87-point reflectivity curve, Q_z 0.0175–0.45 Å⁻¹,
  plateau 0.989 at the first point, first minimum at Q_z ≈ 0.25 Å⁻¹. This
  curve is frozen as `tests/reference/nx_school_ref_scans_6-9.txt`. It is a
  self-reference (what the program computes today), not an independent
  check.
- Stitch factors reported between successive scans: 0.02293, 0.001480,
  0.0001534.
- The folder also ships `extracted_data/dppc_ref.txt`, a DPPC curve reduced
  earlier by the beamline software from a *different* set of scans (Q_z
  0.016–0.76). Interpolated onto it, our curve agrees within 2 % below
  0.05 Å⁻¹, is 2–7 % higher up to 0.1 Å⁻¹, and differs by up to 37 % near the
  minimum. Since these are different measurements this does not show an
  error, but it is not a confirmation either.
- The real SPEC header layout (`#P0 names` followed by `#    values`) matches
  what `tests/synth.py` guessed.

### 2026-11-14 — What does the private `bu` sample set show?

**Q.** Use `bu` as further example data (kept local, git-ignored, not pushed).

**A.** `bu` holds eight SPEC files from three runs (253 scans), 595 Pilatus
100K frames, 366 Pilatus 1M frames and 26 Vortex MCA files. Measured with
`tests/test_real_bu.py`, which opens every file, selects each scan and its
first frame:

- Seven of the eight files go through without raising.
- `2026June/20260615` contains scan numbers 1, 2, 1. The reader flags
  "identical scan numbers", the window then never sets its image-directory
  paths, and selecting scan 2 raises `AttributeError: pilfhead`
  (`mainwindow.py:1487`). Pinned as an expected failure.
- **Pilatus 1M data are not readable by this version of the program.** The
  October run records the detector geometry on a `#B5` header line and stores
  images (981 × 1043 pixels) in `pilatus1m/`. The reader only understands
  `#B1`/`#B2` and only looks in `pilatus/`, so all 20 such scans are listed
  as "Pilatus" with zero frames. Nothing raises; the data are silently
  absent.
- 41 fluorescence scans report "MCA file(s) of selected scans do not exist";
  the sample set contains only some of the `vortex/` files, so this is
  expected here.

Timings on local disk (best of three, this container):

| Operation | Time |
|---|---|
| `TwoDDetector.openFile`, Pilatus 100K, no bad-pixel pass | 4 ms |
| same, one bad-pixel pass | 6 ms |
| `TwoDDetector.openFile`, Pilatus 1M array, no bad-pixel pass | 37 ms |
| same, one bad-pixel pass | 64 ms |
| plain `numpy.asarray(PIL.Image.open(...))`, 1M | 1.8 ms |
| `mcaread`, 28 spectra × 4096 channels | 0.46 s (16 ms per spectrum) |

So on local disk the file readers are 20× slower than they need to be for
images, but still tens of milliseconds. The slowness reported in production
is therefore more likely network reads and what happens after reading
(per-frame plotting, repeated re-reading on every selection) than decoding.
That has not been measured yet; it needs timing of the full selection path,
ideally against a slow file system.

### 2026-11-14 — Where does the time go when selecting data?

**Q.** Some operations are slow (MCA spectra, Pilatus 1M images); production
reads from a network drive. What is the baseline?

**A.** Measured by `pytest -m bench`; table in [timings.md](timings.md).
Local disk, so network cost is not included.

- Selecting 96 Pilatus 100K frames in one action takes about 2 s; selecting
  6 MCA spectra about 0.5 s. In both, roughly three quarters of the time is
  matplotlib (text layout in `tight_layout`, drawing); reading the files is
  about a tenth.
- Selecting frames **one click at a time** is the expensive case: adding 27
  frames takes 21 s against 0.9 s for the same 27 in one action. Every
  change of selection re-reads every selected frame from disk and redraws;
  nothing is kept between selections. Over a network drive this is the
  cost that a cache (requests F8, F9) removes; the redraw cost is separate
  and a cache does not touch it.
- Pilatus 1M and the large per-point MCA files could not be timed through
  the window because this version cannot load them (see the `bu` entry and
  below).

### 2026-11-14 — GID on the real data

**Q.** (follow-up to the sample-data question) Does GID reduction work?

**A.** Scan 11 of the NX school set (41 frames, low Q_z) patches into a
472 × 41 map; its Q_xy and Q_z projections are frozen as
`tests/reference/nx_school_gid_scan_11_*.txt` (self-reference). The peak in
the Q_xy projection lies between 1.3 and 1.55 Å⁻¹, where the DPPC chain peak
is expected.

Adding the high-Q_z scan 12 shows "One or more of selected scans do not have
enough points for the vertical patching!". Calling the join directly shows
the real cause: `scipy.interpolate.interp2d` raises because it was removed
from SciPy, and a bare `except` turns that into the warning. So on current
SciPy the standard low + high Q_z GID patch cannot be done at all. (Scan 12
was also stopped after 4 frames, so it could not be a full test case even
once this is fixed.) Pinned as an expected failure.

### 2026-11-14 — Per-point MCA files in the October `bu` run

Observation while looking for MCA timing cases, recorded because it affects
scope. In `bu/2026oct`, files such as `vortex/20261019_15_mca` hold one
spectrum per scan *point* of an ordinary `ascan` (`#S n mca_save_point
Point:k Scan:15`, detector `XSP3_7Chan`, floating-point counts). The window
only offers MCA data for scans whose command is `getandsave_mca`, so these
spectra cannot be reached from the interface, although `mcaread` itself
parses the file (28 spectra, 0.46 s).

### 2026-11-14 — What happens to the user when a handler raises?

**Q.** "No crashing ever": how bad is a raising handler today?

**A.** Fatal. Run as the real program (no test hooks), pressing "Ref Patch"
with nothing loaded ends the process with exit code 134 (SIGABRT): PyQt5
aborts on an unhandled exception in a slot, and the reader installs no
exception hook. So each of the 420 control/state combinations in
`tests/known_crashes.json` closes the application and loses whatever was in
memory. Pinned as an expected failure
(`test_application_survives_a_raising_handler`).

This also means one small change — a process-wide exception hook that logs
and carries on — would turn every one of them from "application gone" into
"operation failed, logged", before any individual handler is repaired. That
is the natural first step for requests F10–F12 when implementation starts.

### 2026-11-15 — Owner answers to the open questions

Recorded as given; the decisions are tabulated as D1–D8 and F20–F23 in
[FEATURE_REQUESTS.md](FEATURE_REQUESTS.md).

**Q.** Should image signals be divided by counting time explicitly?
**A.** No change to the default: the normalised signal stays counts per
monitor count. An optional per-second value for important quantities is
wanted. A photons-in estimate will later be written to the SPEC file by the
beamline and should then be used.

Invariant consequence: the default reduced quantity and its error (I3, I4)
must not change when the per-second option or the photons-in estimate are
added; both are additional outputs, not replacements. A per-second value is
the same quantity divided by the counting time, which carries no
uncertainty of its own in the present error model, so its relative error
equals that of the default quantity.

**Q.** Do two instances ever share a SPEC file? **A.** Yes. The second
instance is read-only on the config, shown by a small yellow indicator.

**Q.** Dropped points as a mask over raw frames? **A.** Correct.

**Q.** Where do config and log go if the SPEC folder is not writable?
**A.** A reliable local location, with a warning; at worst nothing is
written and defaults apply.

**Q.** Which fitting features stay? **A.** All of them; more and better
fitting is wanted in places (to be scoped).

**Q.** Is the Bruker detector still needed? **A.** No, it is defunct.

**Q.** What does "a single scan reduces and is frozen as a reference" mean?
**A.** (Asked by the owner about an earlier status line.) It is a
regression benchmark: the program's own output for NX school GID scan 11
today, saved in `tests/reference/`, so that any later change to the code
that alters those numbers is noticed. It shows the output has not changed;
it does not show the output is right.

### 2026-11-15 — The xmodfit hand-off checked against this repository

**Q.** Here is the hand-off describing what xmodfit needs from the reader's
export. (Also: add ORSO-compliant export if it is not in there.)

**A.** Filed as `docs/handoff/19-lss-reader-covariance-contract.md`; indexed
as F24 (with F24a–c) and F25 in `FEATURE_REQUESTS.md`. ORSO is not mentioned
in the hand-off, so it is added as F25.

Checked against the code here (run, unless marked "read"):

- **Code base.** The hand-off's line numbers are for commit `a861d79`. This
  repository's application code is one commit later (`7d2467f`), which only
  changed the line-cut function; the reflectivity path is identical, with
  line numbers shifted by 6.
- **Legacy fixtures (acceptance test 1) now exist.** Today's `_ref.txt` and
  `_rrf.txt` are stored byte for byte for six synthetic cases (plain, a
  dropped point, typed normalisation factor, Q offset, Qz² box, R/RF never
  checked) and two real ones (NX school scans 6–9, with and without drops).
  A second run reproduces all of them exactly.
- **Trap T8 reproduced.** With the Qz² box checked, `_rrf.txt` has q² in its
  q column (first row 1.0000e-04 instead of 1.0000e-02); `_ref.txt` is not
  affected. Pinned both as an expected failure (desired behaviour) and as a
  characterisation (so the legacy fixture is understood).
- **Trap T3 reproduced.** `oneDjoin(mtype='merge')` scales the new scan's
  array in place; pinned as coded.
- **Trap T10, one consequence observed.** If R/RF was never checked, Export
  writes `_ref.txt` only and prints "No rrf data available!"; no `_rrf.txt`.
- **Trap T11, extended.** Dropping points until the first pair no longer
  overlaps shows the warning and closes the dialog; if the merge is then
  invoked it raises `ValueError: ydata must not be empty` from `curve_fit`.
  On later joins the dialog stays open (read), so that path is reachable by
  a user.
- **Format.** Both files: tab-separated, three columns, `%.4e`, q strictly
  increasing, no header. `_rrf.txt`'s q column is q + Q-offset. The typed
  normalisation factor divides value and error on top of the automatic
  plateau normalisation.

One point for the hand-off's author and the owner. The corrected chain keeps
today's estimator for the factor: ratios of the existing points to a cubic
spline of the new scan, in linear intensity. As measured earlier (entry
"Test scaffolding; what did the first tests find?"), that spline
overestimates a steeply falling curve between its knots, so when the two
scans do not share Q_z points in the overlap the factor comes out 1.2–1.3 %
low in the synthetic case. That is a **bias**, the same sign every time, not
scatter: Σ describes the random error of the factor and does not contain
it, and the inflate-only χ² will only partly react to it. With counting
errors of 0.1 % a 1.3 % bias is thirteen standard deviations. Whether to
remove it (for example by interpolating log R, or R·Q⁴) is a decision for
the corrected chain only; the legacy chain must keep it for byte identity.
Not yet tried: how large the bias is on real overlaps, where Q_z points
usually do coincide.

Needed from the xmodfit side to run acceptance tests 5 and 6:
`tests/lss_reference.py` and `covariance_core.py` from XModJointFit.

### 2026-11-15 — Benchmarks for every reduction type; XFNTR

**Q.** A frozen benchmark is needed for each type of data reduction,
especially reflectivity and XFNTR.

**A.** Status of benchmarks (the program's own output, stored, compared on
every run):

| Reduction | Synthetic, known truth | Real data |
|---|---|---|
| Reflectivity (patch, normalise, R/R_F, export) | yes, incl. bytes of `_ref.txt`/`_rrf.txt` | NX school scans 6–9, bytes |
| XFNTR (MCA window sum vs Q_z, export) | yes, incl. bytes of `_flu.txt` (new) | `bu` scans 74–79, SHA-256 only (private data) |
| GID (single scan) | no | NX school scan 11 |
| GID (multi-scan patch) | no | cannot run (defect 1) |
| Line cuts | yes (values, not bytes) | no |
| GISAXS, GIOXS, burn tests, MCA peak fit, calibration fits | no | no |

XFNTR findings, measured on synthetic spectra with a known number of
counts in the fluorescence line (`tests/test_xfntr.py`):

- The window sum returns exactly counts / monitor × (real time / live
  time), and the Q_z dependence of the generating curve.
- **NumPy 2 leak into output.** Lists of scan numbers are formatted with
  `str([...])` of NumPy integers, which NumPy 2 prints as `np.int64(1)`.
  The first line of `_flu.txt` therefore reads
  `#Flu Sum, scans=[np.int64(1), np.int64(2), …]`, and the same text
  appears in the command line box and in plot titles (15 places build a
  scan list this way). Pinned as an expected failure. It also means the
  bytes of `_flu.txt` depend on the NumPy major version.
- **A message box on every fluorescence selection.** Selecting a
  `getandsave_mca` scan always raises "The scan(s) are not regular Spec
  scan" as a modal dialog; relevant to F11.
- **"Merge" uses an unusual weighted mean.** Points closer than the given
  resolution are combined as Σ(y²/σ²) / Σ(y/σ²), not Σ(y/σ²) / Σ(1/σ²).
  The two agree only when the merged values are equal. Pinned as coded;
  whether it is intended is a question for the owner.
- `_flu.txt` is written with full `str(float)` precision, unlike the
  `%.4e` of the reflectivity files.

### 2026-11-15 — How is monitor noise propagated into sums? (question for the owner)

Not asked by the owner; found while writing the XFNTR and ROI error tests,
and it bears directly on "each quantity has a Poissonian uncertainty that
gets propagated".

Each pixel (or MCA channel) is given σ² = I/M² + I²/M³: its own Poisson
noise plus the monitor's. A region of interest, or an energy window, then
adds its pixels in quadrature, as if every pixel had an independent monitor
reading. But all pixels of one frame share one monitor reading, so for a
sum S = ΣI the monitor part should be S²/M³, not ΣI²/M³. The coded error is
too small by a factor that grows with the number of pixels and with S/M.

Measured (`test_roi_error_treats_monitor_noise_as_independent_per_pixel_as_coded`,
`test_error_is_larger_than_pure_poisson_of_the_sum_as_coded`):

- Flat ROI of 231 pixels, 400 counts each, M = 10⁵: correct/coded = 1.39.
- Synthetic reflected beam at total reflection (2.5×10⁷ counts in the ROI,
  M = 10⁵): coded relative error 0.049 %, with a shared monitor 0.32 %; a
  factor 6.5.
- Real NX school scan 6, first point: 7.9×10⁵ detector counts against
  Monc = 2.2×10⁵, so S/M ≈ 3.5 and the monitor term dominates. The stored
  relative error there is 0.14 %; √(1/S + 1/M) would be 0.24 %.

Two separate questions follow, and neither is decided here:

1. Should the monitor term be applied once per frame to the summed signal
   (correlated), rather than per pixel?
2. Is Poisson statistics on `Monc` right at all? The SPEC header says
   `#M Monc Gain 5 uA/V`: the monitor is a current amplifier feeding a
   counter, so its count is proportional to flux through a gain setting,
   not a number of detected photons, and 1/√Monc is then not its relative
   uncertainty.

This interacts with the xmodfit hand-off: `sigma_meas` is defined there as
the counting-only error, and whatever is decided here changes it (in the
corrected chain only; the legacy chain must stay as it is).

### 2026-11-15 — Benchmarks added for cuts, burn tests and MCA peak fitting

**Q.** (owner) Why no line cuts on real data — can't a few cuts be made on
the GID single scan? Burn tests and MCA peak fitting are important and need
benchmarks.

**A.** Done. Updated benchmark table:

| Reduction | Synthetic, known truth | Real data |
|---|---|---|
| Reflectivity (patch, normalise, R/R_F, export) | yes, with file bytes | NX school scans 6–9, file bytes |
| XFNTR window sum and export | yes, with file bytes | `bu` scans 74–79, hash only |
| MCA peak fit ("Fit", "Accept", "Fit All") | yes: position, width, height recovered | no |
| Reflectivity burn test | yes: known τ recovered | no (the sample sets have no reflectivity burn scan) |
| GID burn test (intensity, location, width) | no | NX school scan 14 |
| GID single scan, projections | no | NX school scan 11 |
| Line cuts through a GID map | no | NX school scan 11, two cuts |
| Line cuts on a detector frame | yes | NX school scan 7 frame 0 (exact sums, beam positions) |
| GID multi-scan patch | no | cannot run: the code fails on current SciPy, and the only pair in the samples has an aborted second scan |
| GISAXS, GIOXS, calibration fits (g_l2, g_l3, absorber ratio) | no | no |

Findings while building them, all measured:

- **Real-data check of the Q_z axis.** On NX school scan 7, frame 0
  (Q_z = 0.035) the brightest spot is not the reflected beam but the direct
  beam, 21 rows below it. The cut's Q axis puts that spot at Q_z = 0.0018
  (zero within about a pixel) and the reflected beam at 0.035; their
  separation is 2α within 8 %. This is the first check of the geometry
  against real data rather than against the code's own formula
  (invariant I11).
- **NX school scans 14 and 15 are GID burn tests** (21 frames, 10 s each,
  detector at 16.5°), not reflectivity burn tests. Over 200 s the
  integrated chain-peak intensity of scan 14 changes by +1.9 % with a
  per-frame error of 1.8 %: no burn visible at that level.
- **The GID burn test already uses the shared-monitor error.** Its
  intensity error is (ΣI)²/M³ + Σσ²/M², i.e. the monitor term applied once
  to the summed signal, unlike the ROI and MCA paths (PHYSICS_ISSUES P2).
  The program is inconsistent with itself on this point.
- The burn dialog labels its range box "Qz range" but uses it as a Q_xy
  range. The fitted τ is truncated to an integer number of seconds and
  shown with two significant digits.
- MCA "Accept" stores height × σ (the Gaussian area / √(2π)) with an error
  from the two parameter errors without their covariance (P20). Relative
  values across frames are unaffected: "Fit All" reproduces the shape of
  the generating curve within 0.5 %.

### 2026-11-15 — Is adding the monitor variance per pixel, in quadrature, right?

**Q.** (owner) "It does? … Is this the right way to do this?" — explored
with a sub-agent at the owner's suggestion. Full report:
[reports/monitor_noise.md](reports/monitor_noise.md); script:
`tests/tools/monitor_noise_mc.py` (17 s, fixed seed; rerun here and it
reproduces the report's tables).

**A.** No. One monitor reading is shared by every pixel of a frame, so its
error is fully correlated across them.

Derived (first order), with u_M the monitor's relative uncertainty:

    var(S/M)   = S/M² + (S/M)²·u_M²                    ROI sum S = Σ I_i
    var(net/M) = [S + (L+R)/4]/M² + (net/M)²·u_M²      net = S − (L+R)/2

The program computes S/M² + ΣI_i²/M³: its count term is right, and its
monitor term is too small by N_eff = S²/ΣI_i² (the effective number of
pixels) *if* the monitor were Poisson.

Simulated (predicted σ / observed σ; 1.00 is correct):

| Case | Monitor simulated | Program today | Derived formula | Correlation fixed but Poisson kept |
|---|---|---|---|---|
| Low Q_z: S = 7.9×10⁵, M = 2.2×10⁵ | Poisson | 0.49 | 1.00 | 1.00 |
| same | 10× quieter (variance) | 0.89 | 1.00 | 1.84 |
| same | noiseless | 1.04 | 0.99 | 2.13 |
| High Q_z: S = 50, M = 2×10⁶ | any | 1.00 | 1.00 | 1.00 |
| MCA, 81 channels, S = 10⁶ | Poisson / 10× quieter | 0.46 / 0.89 | 1.00 / 1.00 | 1.00 / 1.95 |

The important consequence: **the two errors partly cancel.** Ignoring the
correlation makes the error too small; assuming Poisson for a monitor that
is really much quieter makes it too large. If the monitor is at least ten
times quieter than Poisson (the owner's estimate), today's error bars are
within about −13 % / +7 % on the brightest points and exact at high Q_z.
Fixing only the correlation while keeping Poisson on `Monc` would make
them 1.8–2.3 times too large at low Q_z. So the two must be changed
together or not at all.

Measured on the NX school SPEC file (successive-difference scatter):

- `Monb` and `Mond` are zero throughout; only `Monc` and `Monp` are usable.
- `Monp` scatters at 0.2–0.5 of √counts in 9 of 12 beam-on scans, and its
  relative scatter (4–7×10⁻⁴) does not depend on counting time: a fractional
  floor, not a 1/M law.
- `Monc` in the repeated-point scan 15 scatters at 0.59 of √counts
  (3.3×10⁻⁴); in scan 14 at 1.36× (with a drift and one dip).
- `Monc` and `Monp` do not see the same beam (`Monc` falls with Q_z in the
  reflectivity scans, `Monp` stays flat), so their ratio only bounds the
  monitor noise from above.
- Scans 1–3 look like beam-off readings with `Monc` ≈ 100 counts/s and
  `Monp` ≈ 42 counts/s: a possible unsubtracted dark offset of 0.03–0.12 %.
- Solid: these monitors are not Poisson in their counts, and `Monc`'s
  frame-to-frame scatter is below 10⁻³ for 7–10 s frames. Not established:
  how much of that scatter is noise and how much is real beam variation.

Recommendation in the report (not adopted; the owner decides): keep
count-only errors per pixel; apply the monitor term once per frame to the
net signal with a settable model u_M² = f² + 1/(g·M), the fractional floor
f expected to dominate (3×10⁻⁴ to 10⁻³ fits this file); keep today's
formula as the legacy mode, since the legacy export fixtures are frozen.
For GID/GISAXS maps and MCA spectra, where many points come from one
frame, the monitor term is a common scale and should not be in per-pixel
errors at all. Not urgent: at most about 15 % on σ, only on the brightest
points.

Caveat: the report's literature references are cited from memory; the
sub-agent could not reach DOI resolvers to check them.

### 2026-11-16 — Is the monitors' scatter noise, or real beam variation?

**Q.** (owner) Counts below 1000 on those detectors are just beam-off.
`Monc` falls with Q_z and `Monp` does not because of geometry: the S1
slits. At low Q_z the ratio of the two should be constant; at higher Q_z it
will not be. That could help decide whether the scatter is real or beam
variation — and there *is* beam variation, so the scatter in the monitors
is not all uncertainty. This must be understood before normalisation
models are discussed.

**A.** Measured on the NX school SPEC file with
`tests/tools/monitor_ratio.py` (run it to reproduce; a few seconds).

1. **The two monitors do not share their scatter.** After removing the slow
   trend along each scan, the correlation between `Monc` and `Monp`
   residuals is small and of either sign (−0.66 to +0.45 over 11 scans,
   no consistent positive value). A common beam variation seen by both is
   at most about 5–9×10⁻⁴ where it shows at all. `Monp`'s scatter is
   4–7×10⁻⁴ in most scans; `Monc`'s is 2–7×10⁻³ in the reflectivity and
   1 s alignment scans and 4–8×10⁻⁴ in the 7–10 s GID scans.
2. **But `Monc`'s extra scatter is real, and the detector proves it.** In
   reflectivity scans 7 and 8 (the two whose curves are smooth enough to
   detrend), the detector counts in SPEC's `Pilatus` column fluctuate
   *with* `Monc` (correlation +0.5 to +0.7), and dividing by `Monc`
   reduces their relative scatter:

   | Scan | Poisson limit of the detector | raw | ÷ Monc | ÷ Monp | Monc scatter |
   |---|---|---|---|---|---|
   | 7 | 7.7×10⁻³ | 9.9×10⁻³ | 7.8×10⁻³ | 9.9×10⁻³ | 5.0×10⁻³ |
   | 8 | 5.8×10⁻³ | 6.1×10⁻³ | 4.8×10⁻³ | 6.3×10⁻³ | 2.1×10⁻³ |

   (6th-order detrend; 4th order gives the same picture.) After dividing
   by `Monc` the detector sits at its own Poisson limit. Dividing by `Monp`
   does nothing. The variance removed in scan 7 is (6×10⁻³)², about all of
   `Monc`'s own scatter.

Reading, consistent with the owner's explanation: the flux that gets
through the narrow S1 slit to the sample varies from frame to frame by
0.2–0.5 %; `Monc`, downstream of S1, tracks it and `Monp`, upstream, does
not. So in the previous entry's terms, most of `Monc`'s frame-to-frame
scatter is **signal that normalisation correctly removes**, not monitor
uncertainty. The earlier statement that "`Monc` scatters at 1.4–9 times
√counts" in some scans is true but is not a measure of its noise.

What this leaves for `Monc`'s actual noise: the normalised detector signal
in scans 7 and 8 is at the Poisson limit within the precision of 21–27
points, so `Monc`'s own noise in a 2 s frame is small against 5–8×10⁻³; a
rough ceiling is 1–2×10⁻³, consistent with the sub-10⁻³ floor seen in the
quiet GID scans. A proper measurement needs a bright, steady signal
(direct beam or total reflection, ≥ 10⁷ detector counts per frame,
repeated frames).

Limits of this check: it uses SPEC's own detector ROI column, not the
reader's ROI; the detrending polynomial is an approximation (scans 6 and 9
could not be judged, their curves are too structured); 21–27 points per
scan.

Also recorded from the owner: monitor rates below 1000 counts/s mean beam
off, so NX school scans 1–3 are beam-off and show a dark rate of about
100 counts/s (`Monc`) and 42 counts/s (`Monp`), which is not subtracted
anywhere (PHYSICS_ISSUES P21, now confirmed as a dark offset).

Consequence for the normalisation discussion: the monitor term in the
error budget should describe `Monc`'s *measurement* noise only, which is
much smaller than its observed scatter. The previous entry's conclusion
stands and is strengthened: Poisson on `Monc`'s counts overstates it, and
the per-pixel treatment understates the result; the two partly cancel.

### 2026-11-16 — Why can't the NX school GID data be patched here?

**Q.** (owner) I am told the GID data set from the NX school can be
patched. I don't understand what is going on with SciPy that you can't.

**A.** It can be patched; it depends only on which SciPy is installed.
The join of the low and high Q_z scans calls `scipy.interpolate.interp2d`.
That function was deprecated and then removed in SciPy 1.14 (2024); on any
newer SciPy the call raises, the reader's bare `except` catches it, and
the user sees "One or more of selected scans do not have enough points for
the vertical patching!".

Measured by building a second environment (Python 3.11, SciPy 1.13.1,
NumPy 1.26.4, Matplotlib 3.8) and running the unchanged program in it:

- Scans 11 + 12 patch into an 833 × 41 map, Q_z −0.044 to 1.251 Å⁻¹,
  Q_xy 1.235 to 1.568 Å⁻¹, with no message. Its exported `_qxy_gid.txt` and
  `_qz_gid.txt` are now `tests/reference/nx_school_gid_scans_11-12_scipy113_*`
  and the patching test compares with them (it is an expected failure only
  where `interp2d` is missing).
- **The whole test suite was run in that old environment as well.** 100
  checks pass there, including every byte-level export fixture and every
  real-data reference. The only differences from the current environment
  are the two library effects already known: the patching works, and scan
  lists print as `1, 2, 3` instead of `np.int64(1), …` (which changes the
  `_flu.txt` header). So the reduction's numbers do not depend on the
  library versions across NumPy 1.26 → 2.5 and SciPy 1.13 → 1.18.
- The files shipped in `extracted_data/` (`dppc_*_gid.txt`, 49 × 853) could
  not be reproduced from scans 11 + 12 with either patch mode or with the
  older row range (shapes 39–42 × 833–843), so they come from a different
  measurement or different settings.

### 2026-11-16 — What is the SPEC `Epoch` column?

**Q.** (owner) We want better timestamps; there is an Epoch column but it
seems like an arbitrarily reset clock. The scan header has an accurate
time; for each point we do not know when it occurred.

**A.** Measured with `tests/tools/spec_epoch.py` on the nine sample files.
`Epoch` is seconds elapsed since a base time. In six files that base is the
file's `#E` line (its creation time, Unix seconds) and each scan's first
point follows its `#D` header by 0–15 s. In three files the base is
something else: a constant 1600 s off for a whole file; drifting by
780–2780 s within one file; and jumping by 13.9 days from scan 80 onward
in `bu/2026sep/20260902`. That fits a base that is reset when a SPEC
session starts, while `#E` is written only when the file is created — so
the impression of an arbitrarily reset clock is correct.

What can be relied on today: within one scan, `Epoch` differences are
elapsed seconds (1 s resolution), and the scan's `#D` is accurate wall
time (local, no zone written). So the time of point i is `#D` + (Epoch_i −
Epoch_0) + a first-point lag of a few seconds. The image files do not
help: their TIFF headers hold exposure time and period but no absolute
time.

### 2026-11-17 — Stage 0 built: what happens now when an action fails?

**Q.** (owner) Begin the implementation plan.

**A.** Stage 0 of `SCOPE.md` is in. Measured by running the real program in
a subprocess (`tests/test_reader_log.py`):

- Pressing "Ref Patch" and then "Analyze" with nothing loaded used to end
  the process (exit code 134). Now the process exits normally afterwards,
  the Messages pane shows two "Operation failed: AttributeError … in
  pilRefPatchData" lines, and the session log holds both tracebacks with
  the session context (SPEC file, tab, selection).
- Eight different crashing controls pressed in a row: still alive.
- A record that was logged is on disk even when the process is killed with
  no cleanup in the next instruction.
- A deliberate hard abort leaves "Fatal Python error: Aborted" and the
  Python stack in the session's fault log.

No reduction code was touched: every numerical check, every byte-level
export fixture and every real-data benchmark gives the same result as
before (quick checks 88 pass; real-data checks 21 pass).

What Stage 0 does not do: it does not repair the 420 failing
control/state combinations; each still fails, but as a logged message
instead of a closed program. That is Stage 1.

### 2026-11-17 — Stage 1 progress: what changed, and did any number move?

**Q.** (owner) Continue; use Sonnet sub-agents on well-scoped tasks.

**A.** Fixes so far, each with its own check, all on `main`:

| Fix | Effect on numbers |
|---|---|
| Defects 2, 3, 5, 6, 7: typos, wrong file name on saving fits, typed centres in the g_l2/g_l3 dialogs | none |
| g_l2/g_l3 calibration: asks for two scans instead of raising | none; new known-answer test: a 185.000 mm arm and 0.020 mm offset are recovered from generated centres |
| Defect 4: non-SPEC files (text, empty, binary, missing) refused with a message; what is loaded is kept | none |
| Shared default dictionaries in the SPEC reader | none |
| D14: one helper formats scan lists | **output text changed**: `_flu.txt` header and titles read `1, 2, 3` again instead of `np.int64(1), …`. Data lines byte-identical. Verified under NumPy 1.26 and 2.5 |
| F24b: Qz² display option no longer squares q in saved `_rrf.txt` | **output changed, as the hand-off permits**: the `qz2` export fixture is now byte-identical to the plain one |
| Defect 14: bad-pixel factor used for replacement and passed from the window | none at default settings (0 iterations, factor 1) |
| Defect 1: GID patching on current SciPy | none: reproduces the SciPy 1.13 output of scans 11 + 12 to 2×10⁻⁴; the replacement matches the removed function to 10⁻¹² on random grids |
| Crash guards, image display and 2D plot (153 control/state pairs) | none |
| Crash guards, reflectivity (93 pairs); Ref Patch with a single frame no longer raises | none; export fixtures byte-identical |

Every byte-level export fixture other than the two named above, every
real-data benchmark and every invariant test gives the same result as
before Stage 1.

How the sub-agents did: two groups so far. Both produced small, readable
guards and no numerical changes; both needed one adjustment on review (a
153-case test moved out of the quick checks; a survival test that had been
loosened to "at least one failure" replaced by one using stand-in failing
handlers).

### 2026-11-17 — Stage 1: is the interface crash-free now?

**Q.** (owner's requirement R3/F10) No crashing ever, whichever files are
selected and whichever controls are used afterwards.

**A.** Measured with the sweep (`TESTING.md`, "Crash inventory"):

| | Before Stage 1 | Now |
|---|---|---|
| Single controls that raise, over 7 states (each control in a fresh window) | 420 | 0 expected (3 at the last full sweep, since fixed; final sweep running) |
| Distinct places in the code they came from | 41 | 0 expected |
| Sequences of 150 random actions that hit a failure | most | 3 failures found in 24 sequences after the guards, all three since fixed |

and, independently of all of the above, a failure no longer closes the
program (Stage 0).

Two of the sequence failures were real bugs rather than missing guards:

- **Movie axes.** The movie loop looked up each frame's axis limits by
  frame number in arrays that hold one entry per *selected* frame. For a
  selection not starting at frame 0 this either raised or drew a frame
  against another frame's Q axes. Fixed and pinned by a test that plays
  frames 5 and 7 and checks that the last frame's Q_z axis is centred on
  frame 7's own Q_z.
- **Stale selections.** After the scan selection changed, the program kept
  the previous frame selection, cuts and normalised spectra, which point at
  rows of a list that no longer exists. They are now forgotten whenever the
  image list is rebuilt. The reduced reflectivity is deliberately kept.

Decision taken without the owner, to be confirmed: choosing **APS 9-ID-C**
now gives a message that such files cannot be read, and the beamline stays
at 15-ID-C. The 9-ID-C reader was never ported from Python 2 and could not
read any file; nothing that worked was removed. If 9-ID-C data matter, the
reader needs porting against a sample file.

No reduction number changed in any of this: every export fixture,
real-data benchmark and invariant check passes unchanged.

### 2026-11-17 — A missing image file shifted the normalisation of later frames

Found while making SPEC opening graceful (F27); measured, now fixed.

When an image named in a SPEC scan was missing from the folder, the reader
(a) paired the j-th image file it found with point j, so every later image
of that scan got the Q_z of the point before it, and (b) kept one monitor
value per SPEC point while the image list skipped the missing image, so
from then on every frame — including all frames of later scans — was
divided by its neighbour's monitor count. In the test case (scan 1 missing
image 1, monitors 10⁵ and 3×10⁵) scan 2's first frame was normalised with
10⁵: a factor 3.

Complete data sets were never affected, so no benchmark or export fixture
changed. Data reduced earlier from scans with a missing image could be
affected; the Messages pane now says when frames have no image.

### 2026-11-17 — Stage 1 done: final sweep

Measured by `pytest -m sweep` on the code at commit `cb518dc` (after the CCD
removal; the 9-ID-C removal followed and only hides a menu entry):

| | Before Stage 0 | Now |
|---|---|---|
| Single controls that raise (7 states × file dialogs cancelled / returning paths, fresh window per control, dialogs one level deep) | 420 per pass (840 rows) | **0** |
| Crash sites reached by random sequences (24 sequences of 150 actions from 4 states) | 11 (from 9 shorter sequences) | **0** |

`known_crashes.json` and `known_crash_sites.json` are now empty: from here
on any control or sequence that raises fails the sweep outright.

Limits, unchanged: dialogs opened from dialogs are not driven; mouse
interaction with plots is not exercised; the sweep runs on synthetic data;
Pilatus 1M and per-point MCA data are not readable yet and so not covered.

### 2026-11-17 — Ref Patch, Burn test and GID dialogs, drilled into

**Q.** (owner) Ref patch, burn test and GID patch are very important and
may have sub-dialogs; add those to the tests.

**A.** Done (`tests/test_dialog_workflows.py`). Measured: 25 random walks of
40–60 actions inside the dialogs (with a synthetic data set that contains a
repeated scan, the synthetic burn set, and the real NX school GID scans)
found three failures, all fixed:

- identical-scans dialog: "Drop" with empty or non-numeric text raised;
- identical-scans dialog: "Merge" after both scans were dropped raised; and
  dropping down to one scan then finishing would have failed later (now the
  remaining scan is used as the reflectivity directly);
- form-factor dialog: a non-numeric radius raised on "OK", and on "Update"
  was reported as "GID patch data does not exist".

Scripted checks added: merging two identical scans gives their mean with
errors √(σ₁²+σ₂²)/2; dropping a point removes exactly that Q_z; a beam more
than 2 pixels from its recorded row opens the information dialog that
lists it; the form-factor radii are taken from the dialog only when valid.

### 2026-11-17 — Stage 2, first step: images are read once

**Q.** (owner, D5) Stop re-reading every selected frame on every selection
change.

**A.** Images now go through `lss_core.images.read_pilatus`: a direct NumPy
read instead of PIL's per-pixel `getdata()`, and a memory cache keyed by
path, size and modification time (a rewritten file is read again), sized
to a quarter of the machine's memory (at most 4 GB; `LSS_READER_RAM_CACHE_MB`
overrides, 0 disables).

Measured:

- The fast read is **bit-identical** to the old one (same values, shape
  and dtype) on a spread of real images from every sample set, Pilatus
  100K and 1M, integer and floating point (`tests/test_lss_core.py`).
  All export fixtures and benchmarks are unchanged.
- Reading one frame: 5.5 → 0.7 ms (100K), 57 → 6.5 ms (1M), before caching.
- Files opened when adding 27 frames one click at a time: **378 → 0**
  (the frames were already in the cache from the previous step); selecting
  the same frame again: 1 → 0. See `timings.md`.

Not yet improved: the time those clicks take is still dominated by
redrawing every selected frame on every click (matplotlib text layout).
On a network drive the file reads were the expensive part and are gone;
locally the redraw remains. Options for the redraw are noted in
`TODO.md`.

### 2026-11-17 — Stage 2: SPEC and MCA files read without `eval`

Measured: the SPEC and MCA readers now parse numbers with a strict parser
(`lss_core/numbers.py`) instead of `eval`. On every SPEC file (9) and every
MCA file (26) in the sample sets the results are identical to the old
readers, value and type (an integer stays an integer); the old readers are
kept as oracles in `tests/legacy/`. Reading the largest MCA file: 24 →
1.2 ms per spectrum. File contents are no longer executed as code.

### 2026-11-17 — Are the images normalised before they are reduced?

**Q.** (owner) Cuts should be normalised — but aren't the images
themselves normalised first? That seems the logical reduction flow.

**A.** Not in this program, read from the code and confirmed by the cut
tests: the frames the window loads and shows are counts (after optional
bad-pixel correction). Each reduction then normalises, or not, on its own:

| Reduction | Normalised by monitor | by absorber factor |
|---|---|---|
| Reflectivity (Ref Patch) | yes, per frame | no — the stitch factors absorb it |
| GID patch | yes, then rescaled by the scan's average monitor | yes |
| Burn tests | yes | no |
| Fluorescence | yes (and real/live time) | no |
| Line/area cuts | **no, until today** | no, until today |
| Image display | no | no |
| Frames with a background image subtracted | yes, before the subtraction | yes |

Changed today (deliberate, D19): cuts are now made of normalised frames,
R = I·a/M with a = absfac^n, σ² = (σ_I²/M² + I²/M³)·a², the same arithmetic
as the background path (`lss_core/normalise.py`, bit-identical to
`TwoDDetector.sumFiles`). Before/after on the synthetic frame (monitor
10⁵, no absorber): a column of the horizontal cut went from 44 counts to
4.4×10⁻⁴; "Sum" of two frames now averages normalised frames (the test
uses scan 2, one absorber). No other output changed.

Making "normalise once, at load" the rule for everything (display
included) is a design change across all reductions; it belongs with the
frame object planned for Stage 3, where each reduction's choice above
becomes explicit.

### 2026-11-17 — The error terms, explicit and without assuming Poisson

**Q.** (owner) Explain the monitor-correlation point more fully; make the
error terms explicit and granular without assuming their form (no
Poisson assumption); show how it is done now and how it should be done.

**A.** Written up in [reports/error_propagation.md](reports/error_propagation.md)
(derivation; the present formulas are read from the code and match the
existing tests; the proposal is not built). In one line: for one frame,
cov(r_i, r_j) = (a/M)²·c_ij + r_i·r_j·(u_M² + u_a²), so every sum over
pixels or channels of one frame carries the monitor and absorber terms
as (Σr)²·u², not Σr²·u²; the program keeps only the diagonal and sets
u_M² = 1/M. Proposed: carry an error budget per value (counting,
monitor per frame, absorber per foil count, live time) that combines
correctly under sums, with a measured monitor model and a legacy mode
that keeps today's numbers.

### 2026-11-17 — Correction: no absorber error; patching uncertainty instead

**Q.** (owner) There is no "absorber error": absorber ratios are not used;
the scale between scans is measured in each patch, and that is a patching
uncertainty. Explain the non-patched data first, starting with one frame.

**A.** `reports/error_propagation.md` rewritten accordingly: one frame
(inputs, one pixel, two pixels), sums within a frame, background
subtraction, several frames at one point, fluorescence spectra; the
absorber term is removed and the patching uncertainty is left to the
hand-off. Open point raised with the owner: the window still multiplies
by a nominal factor A^n (`absfac`) in some non-patched paths — the
background-image path, GID patching, and since today line/area cuts.

### 2026-11-17 — Should the monitor's error be modelled as a Gaussian?

**Q.** (owner) The normalisation proposal is accepted: the monitor error
applies to the whole ROI sum of a frame, not pixel by pixel. Analyse the
contributions of the uncertainties to decide whether the `Monc` error
should be Gaussian or something more accurate. A Gaussian of σ = 0.136 %
holds 99 % of `Monc`'s scatter but overstates a typical point's
uncertainty about 3×.

**A.** (measured on the sample data with `tests/tools/monitor_distribution.py`
and `tests/tools/monitor_witness.py`; the owner has far more data, so the
decisive analysis is handed off: `handoff_out/01-monitor-noise-analysis.md`.)

1. Raw `Monc` scatter about a smooth trend (1124 frames, 54 steady beam-on
   scans): sd 8.1×10⁻³, robust σ 2.7×10⁻³, excess kurtosis 9.2; Student t
   (ν ≈ 1.9) fits best by AIC, Laplace next, Gaussian worst. The owner's
   "σ for 99 % is 3× the typical" is the same heavy-tail signature; for a
   Gaussian the two would be equal.
2. Much of the tail is mixing: a scan's width falls with its monitor count
   (σ ∝ M^−0.52, counting-like). Standardised scan by scan, kurtosis drops
   to 2.3, but 0.44 % of frames are still beyond 4σ (Gaussian: 0.006 %).
   Frame-to-frame deviations are independent (lag-1 autocorrelation 0.08).
3. Scatter is not noise (entry of 2026-11-16): where the detector can act
   as a witness, it follows `Monc`, and normalisation removes that part.
   Whether the *tails* are shared with the detector could not be settled
   here: only 7 scans have enough detector counts, and their reflectivity
   curves have too much structure for the second-difference test (scan 7:
   slope 0.87, i.e. the detector follows; the others are dominated by the
   curve's shape).
4. Contribution to reduced points (NX scans 6–9, 96 points): at
   u_M = 0.136 % the monitor term exceeds the counting term at 6 points and
   is more than 10 % of the variance at 33; at 0.27 % at 21 and 65. These
   are the brightest points: lowest Q_z and the first points of each scan,
   which lie in the overlaps that patching uses.

Provisional reading: the noise that matters is the monitor's measurement
noise, which is smaller than its scatter and, from the width-vs-M scaling,
probably counting-like; a Gaussian whose width depends on M (and a flag
for rare jumps) is the likely outcome, but that is to be decided on the
owner's data. Until then the reader carries u_M as a parameter.

### 2026-11-17 — The error budget, built; absorbers made consistent

**Q.** (owner) Go ahead with the error-budget implementation (monitor error
applied to whole ROI sums, not per pixel in quadrature); make absorber
handling consistent and note what changed.

**A.** Built; how it is known: tests (`test_error_budget.py`,
`test_gui_error_budget.py`; invariants I15, I16) and a run on NX school
scans 6–9 (numbers below).

*What exists now.* `lss_core/errors.py` holds the error model, chosen in
the window's new **Errors** pane (menu View → Errors) or with
`errors=` in a script:

- **Legacy** (the default): the numbers the program always gave. Every
  legacy export fixture is unchanged (quick, slow and golden tests pass).
- **Budget**: each value carries a counting part (σ_I²/M², added in
  quadrature) and one monitor amplitude per frame (value·u_M, added
  linearly within a frame, in quadrature across frames). Built into box
  sums and the background-subtracted net (`TwoDDetector.sumROI`/`netROI`,
  hence Ref Patch, Ref burn, Ref analyse), line cuts and their "Sum",
  background-subtracted images (the background's frames enter with the
  opposite sign), frame averages (`sumFiles`), the GID burn intensity,
  GID patch profiles, MCA spectra and window sums.
- Monitor model u_M² = f² + (σ_dark/M)² + 1/(g·M), default f = 0,
  σ_dark = 0, g = 1: Poisson on the recorded counts, i.e. the same
  assumption legacy makes, so that switching models changes only how the
  terms combine. Provisional until the owner's measurement
  (`handoff_out/01-monitor-noise-analysis.md`).
- Legacy stays the default until the two-output export of the hand-off
  (§2.5: corrected `_ref.txt` plus byte-identical `_ref_legacy.txt`) is
  built; then budget becomes the default and legacy files are always
  written alongside.

*Before/after on real data* (NX school scans 6–9, per-frame σ, budget ÷
legacy): with g = 1, median 1.03, maximum 1.74 at Q_z = 0.0187 (the
brightest points, where the per-pixel sum understated the monitor
term); in the final `_ref` curve median 1.01, maximum 1.74; values move by
at most 4×10⁻⁵ (through the error-weighted scale-factor fit). With g = 10,
σ ratio 0.94 to 1.00: the two defects of the legacy formula (correlation
dropped, Poisson monitor) roughly cancel, as simulated before
(`reports/monitor_noise.md`).

*Absorbers.* Where a nominal factor a = absfac^n is applied, it now
multiplies the counting and monitor parts alike and carries no
uncertainty (the scale between scans is measured in patching). Per path:

| Path | Nominal absorber factor | Changed today |
|---|---|---|
| Ref Patch | no: the scale is measured in each patch | no |
| Ref and GID burn tests | no: one scan, one absorber setting; τ does not depend on it | no |
| Fluorescence | no | no (open question below) |
| Cuts (since D19), background images, frame averages, Ref analyse at one Q_z, GID patch | yes | **a message** in the Messages pane when frames with different absorber counts are combined this way, once per combination: the relative scale then rests on the unmeasured nominal factor |

Open question for the owner: are the absorber foils upstream or downstream
of the `Monc` ion chamber? If upstream, `Monc` already sees the
attenuation and dividing by it corrects for the foils, so applying a^n as
well would double-count; if downstream (between sample and detector, or
between `Monc` and the sample), a^n is needed wherever frames of different
foil counts are compared. The fluorescence path applies no factor; whether
that is right depends on the same answer.

### 2026-11-17 — Monitor uncertainty decided; Monc is upstream of the absorbers

**Q.** (owner) `Monc` is upstream of the absorbers. From an analysis with
another agent: model the monitor's uncertainty as a Gaussian of σ = 0.04 %,
constant across counting level; that is the default ("case closed"). Make
the value accessible in the window. Offer a Student t with ν = 3.6 if
feasible, noting that it depends on the present SR570 + V2F electronics.

**A.** Built (tests: `test_error_budget.py`, `test_gui_error_budget.py`).

- `lss_core.errors.MonitorModel` has three kinds: `'gaussian'` (default,
  σ = 0.04 % at every monitor count), `'student_t'` (ν = 3.6, scale s,
  refined in the next entry to ν = 4, s = 0.94·σ_scan;
  propagated through its standard deviation s·√(ν/(ν−2)) = 1.5 s, finite
  for ν > 2), and `'counting'` (f, σ_dark, g, as before). The Gaussian and
  t values are labelled as belonging to the SR570 current amplifier + V2F
  converter in the code, the Errors pane's tooltip and description, and
  every description written to the log.
- The Errors pane has a "Monitor model" choice and a "Monitor sigma (%)"
  field (0.04), which becomes the t's scale when Student t is chosen; ν
  is editable (refused unless > 2). Scripts: `errors={'mode': 'budget'}`
  uses the default; `errors={'mode': 'budget', 'kind': 'student_t',
  'sigma': 0.0004, 'nu': 3.6}` the t.
- Feasibility of the t, stated plainly: a first-order propagation only
  uses variances, so in the reduction the t acts through its standard
  deviation; its heavier tails matter to whatever uses a likelihood
  downstream (a fit), and the model is recorded so that a future export
  (R7) can carry ν. The owner gave ν only; the t's scale defaults to the
  Gaussian's 0.04 % (SD 0.06 %) until the fitted scale is supplied.
- The error model's *mode* stays Legacy by default (byte-identical legacy
  files) until the corrected/legacy two-file export is built; choosing
  Budget now uses σ = 0.04 % unless changed.

*Effect on NX school scans 6–9* (budget ÷ legacy, per-frame σ): Gaussian
0.04 %: 0.86 to 1.03, median 1.00; the monitor is > 10 % of a point's
variance at 4 of 96 points (at most 11 %, at the brightest low-Q_z
points). Student t (scale 0.04 %): 0.92 to 1.08; > 10 % at 12 points, at
most 22 %. Values move by < 5×10⁻⁶ through the patch fit. So with the
decided monitor uncertainty, error bars are counting-dominated almost
everywhere and the legacy per-pixel Poisson term had been slightly too
large at the brightest points.

*Absorbers.* With `Monc` upstream of the foils, the monitor does not see
the attenuation, so dividing by `Monc` never corrects for it and the
nominal factor a^n does not double-count where it is applied. Ref Patch
needs no factor (the scale is measured). The paths that combine frames at
different absorber settings on the nominal factor say so in the Messages
pane (now worded with this reason).

*Read from the data, not confirmed:* SPEC's `#A Absorber` value is not a
count of foils. In NX school it is 41, 31, 24, 18 for reflectivity scans
6–9 (falling as Q_z rises), 52 for alignment through the direct beam and
63 (all six bits) with the beam off; the bu files show 8 to 63. It reads
as the total thickness of binary-weighted foils in units, which is what
the program's a = absfac^n with absfac = 1.606 per unit assumes
(1.606⁴¹ ≈ 3×10⁸ at the critical edge). Open for the owner: are the
foils before the sample (then fluorescence is attenuated too and the
fluorescence path, which applies no factor, would need a^n whenever
spectra at different settings are compared; bu 2026-09-02 has energy
scans on the Vortex at setting 52) or between sample and detector?

### 2026-11-17 — Absorber units; the Student t refined

**Q.** (owner) Absorbers are in units of the absorber factor, ≈ 1.414 at
10 keV by design; 0 is no absorber (direct beam). The foils are before the
sample. From the separate analysis: "a frame's monitor error can be
modelled as σ_scan × t₄ with a width of about 0.94 σ_scan. σ_scan is the
scan's own scatter, or about 0.039 % if unknown, and the width works out to
about 0.037 % per frame. That is still an upper bound, because `Monp` also
carries source fluctuations." ν is essentially 4 and the width 0.86–1.01.

**A.** Built (tests: `test_error_budget.py`, `test_gui_error_budget.py`).

- Student t: scale s = w·σ_scan with ν = 4, w = 0.94, σ_scan = 0.039 %
  (s = 0.0367 %); propagated through its standard deviation √2·s =
  0.052 %. The Errors pane has fields for σ_scan (%), the width and ν.
  The Gaussian default (0.04 %) is unchanged. Reading taken: "width" is
  the t's scale, not its standard deviation; consistent with σ_scan being
  a robust (median-based) scatter, since a t₄ of scale s has a robust σ
  of 1.10 s, i.e. s ≈ 0.91 σ_scan. To be confirmed, with the estimator of
  σ_scan, before it is computed per scan (F51).
- Absorber factor default changed from 1.606 to **1.414** (deliberate;
  tooltip says it depends on energy). No legacy fixture uses it
  (reflectivity and fluorescence apply no factor). What changes: cuts,
  background images, frame averages, Ref analyse and GID patching at a
  non-zero setting n are scaled by (1.414/1.606)ⁿ, e.g. ×0.0054 at n = 41
  (NX scan 6), ×0.33 at n = 9. Sample data are mostly at 10 keV, but also
  6.2, 7.5, 10.5 and 30 keV, where 1.414 is wrong; F49 asks for the factor
  from the energy.
- Foils before the sample: the fluorescence path would need a^n to compare
  spectra at different settings, but the XFNTR scans record no absorber
  setting (checked on every sample file: `getandsave_mca` scans have no
  `#A`, MCA headers none). Not changed; F50 gives the two ways out.
- The earlier entry's reading of `#A` as total foil thickness in units is
  confirmed in substance: it is the absorber in units of the factor.

### 2026-11-17 — Absorber setting of the MCA scans (F50)

**Q.** (owner) Have the reader take the last `#A` before each scan.
Absorbers don't change in the middle of scans.

**A.** Built (D24; tests: `test_spec_absorber.py`,
`test_fluorescence_absorber.py`).

- The SPEC reader gives a scan without `#A` the value of the last `#A`
  above it in the file and records the source scan (`AbsorberFrom`); a
  refresh of a growing file continues from the last `#A` read. With no
  `#A` above, the setting stays unknown and no factor is applied.
- Normalised MCA spectra (window and `Experiment.fluorescence`) are
  multiplied by absfac**n, value and error, as the Pilatus paths are.
  Raw spectra (monitor "None") are not. The image list shows
  `Abs=n (#A of S…)`, and the Messages pane says which scans were given
  which setting and the factor in use. Editing the factor takes effect at
  the next Sum All; the Script pane passes `absfac=` when it is not 1.414.
- Measured on the sample files (`getandsave_mca` scans only):

  | File | MCA scans | Setting taken |
  |---|---|---|
  | bu/2026sep/20260902 | 74–79 | 52, from scan 73 (an `escan`, 14 Sep 14:06; scans 74–77 are 3 h later, 78 and 79 one and two days later) |
  | bu/2026sep/20261013 | 2 | 63, from scan 1 |
  | bu/2026June/20260615 | the `getandsave_mca` scan | 63, from the scan above |
  | bu/2026June/20260616 | 1–12 | none above: unknown, no factor |

- Deliberate change (rule 1): the real-data XFNTR check (`test_xfntr.py`,
  bu/2026sep/20260902 scans 74–79, private, hash only) changed hash
  `77be46ea…` → `e23206a9…`. Every intensity and error is multiplied by
  1.42⁵² = 8.30×10⁷ (ratio measured, identical for all six rows to 1e-15).
  The window uses 1.42 here because opening a SPEC file with Pilatus images
  presets the factor field to 1.42 ("Al 50 µm at 10 keV", code comment in
  `readSpecFile`); with 1.414 it would be 1.414⁵² = 6.66×10⁷. The legacy
  `xfntr_flu.txt` fixture is unchanged: its synthetic scans carry `#A 0`.
- Caution, read only: the inferred setting is the one at the start of the
  last scan that recorded it. A change made between scans by a command
  that is not a scan leaves no trace in the file, so the inference cannot
  see it; the Messages pane names the source scan for that reason.

### 2026-11-17 — ⚠ The absorber factor in use was not always the one shown (P24)

**Important (owner asked for a strong note).** In the original program
this made absorber-normalised images and background subtraction depend on
the order of actions in a session, by up to (1.606/1.42)ⁿ = ×600 at
n = 52. Background-subtracted images, GIXOS and their cuts reduced with
the original program at non-zero absorber settings should be re-reduced.
Details in `PHYSICS_ISSUES.md` P24; how it arose below.

Found while building F50 (measured: test and run). Opening a SPEC file with
Pilatus images presets the "Absorber factor" field to 1.42 (code comment:
"for Al 50um at 10keV"), but the value the program used was read from the
field only at start-up and in three reflectivity actions (Ref analyse, GID
patching, frames at one Qz). Cuts, summed cuts, background images and the
MCA factor used the start-up value: 1.606 until today, 1.414 since the
default changed. Fixed: the value in use follows the field whenever it
holds a positive number (`test_gui_error_budget.py`). Deliberate change on
files with Pilatus images: those paths at setting n change by
(1.42/1.414)ⁿ from this morning's code (×1.25 at n = 52) and by
(1.42/1.606)ⁿ from the original program (×0.0064 at n = 41).

This corrects the earlier entry "Absorber units; the Student t refined",
which gave (1.414/1.606)ⁿ for those paths: right for the start-up value,
but on files with Pilatus images the field had shown 1.42 all along.

Answered (owner, same day): use the real value for 50 µm Al, which is
what is used for 10 keV; see the next entry. Asked then: which value should be preset on opening such a file, 1.42
(Al 50 µm at 10 keV) or 1.414 (the design value)? From tabulated
attenuation, Al at 10 keV has μ/ρ = 26.2 cm²/g and ρ = 2.70 g/cm³
(NIST XCOM, <https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html>;
cited from memory, not checked against the table today), so 50 µm gives
exp(0.354) = 1.425 and 1.414 = √2 corresponds to 49 µm. That is also the
information F49 needs: if every unit is Al of about 49–50 µm, the factor at
energy E is exp(μ(E)·t).

### 2026-11-17 — Was XFNTR scaled by absorbers before? What is the normalised fluorescence?

**Q.** (owner) Was XFNTR being scaled by absorbers before? Comparing XFNTR
scans taken with different parameters in the plot panes is often a
problem. Is the absorber factor meant to give fluorescence per input
photon, so different scans can share an axis?

**A.** (read in the code, and the original repository; measured on the
sample files where stated.)

*Before 2026-11-17: no.* The original program (`41f451b`,
`MainWindow.mcaPlot` and `updateMcaPlotData`) computed, per spectrum and
channel,

    y = N · (t_real / t_live) / M,   σ = √(N + N²/M) · (t_real / t_live) / M

with N the MCA counts, M the chosen monitor (`Monc` by default) for that
spectrum, and t_real/t_live the MCA dead-time correction. No absorber
factor and no monitor gain entered anywhere in the MCA tab; "Sum All"
added y over the energy window. The window could not have applied the
absorber: the `getandsave_mca` scans record no `#A`.

*Since today (D24, commit `e6f16e8`):* with a monitor chosen,

    y = N · (t_real / t_live) · absfac**n / M

with n the scan's absorber setting (the last `#A` above the scan) and
absfac the "Absorber factor" field. Without a monitor ("None") spectra stay
raw counts.

*What y is.* Yes: the aim is a quantity proportional to fluorescence per
photon reaching the sample, so that spectra taken under different
conditions share one axis. Step by step:

- dividing by M (counts of `Monc` during the spectrum) removes the count
  time and the flux changes upstream of `Monc` (ring current, optics, S1);
- t_real/t_live corrects the MCA's dead time;
- absfac**n puts back what the foils removed. The foils are between `Monc`
  and the sample (owner), so M does not see them and the factor is needed,
  and it does not double-count (invariant I17).

So y ∝ (fluorescence counts) / (photons on the sample), **up to a constant
that is the same only while these stay the same**:

1. **The `Monc` amplifier gain** (not corrected; F52). `Monc` is an SR570
   current amplifier followed by a V2F converter; the SR570 sensitivity S
   (A/V) sets volts per amp, so counts per photon ∝ 1/S
   ([SR570 manual](https://www.thinksrs.com/downloads/pdfs/manuals/SR570m.pdf)),
   and photons ∝ M·S. SPEC records it as `#M Monc Gain …`, but the reader
   does not read it. Measured: it changes within files, by up to 50×
   (bu/2026sep/20260902: 200 nA/V from scan 1, 10 µA/V from 12, 5 µA/V
   from 130; bu/2026June/20260616: 10 µA/V, then 5 µA/V from 45). Spectra
   on either side of a change are off by S₁/S₂. This is a likely cause of
   the comparison problems; MCA scans have no `#M` either, so it would be
   taken from the last `#M` above them, like `#A`.
2. **The absorber factor per unit** depends on energy (F49), and 1.42 or
   1.414 per unit compounds over n (×1.25 between them at n = 52).
3. **Photon energy.** `Monc`'s current per photon grows with energy (and
   its absorption efficiency changes); the fluorescence cross-section and
   the MCA's efficiency change too. Spectra at different energies are not
   comparable through y alone.
4. **Geometry after `Monc`:** slits between `Monc` and the sample, the
   footprint on the surface (which XFNTR models as part of the physics),
   and the MCA's solid angle and distance.

What y is not: an absolute photon number. M·S gives photons only through
the monitor's efficiency and the V2F scale (counts per volt), neither
recorded in the file.

Tests: `test_fluorescence_absorber.py` (I17; the inferred setting applied
in the window and in scripts, script reproduces the export).

### 2026-11-17 — 50 µm Al; fixed Student t; simultaneous Pilatus and Vortex

**Q.** (owner) Use the real value for 50 µm aluminium, which is what is
used for the 10 keV absorbers; each absorber unit is 50 µm more Al. Make a
strong note on the 1.606 defect. "Width" is the t's scale parameter, not
its standard deviation; σ_scan is a robust standard deviation of the
point-to-point changes, computed per scan, but a fixed Student t is
preferred. New request: simultaneous Pilatus and fluorescence experiments,
with tabs "Vortex" and "Pilatus". Put the macros that do not save the
absorber on the beamline to-do list.

**A.**

- Absorber factor (D25; `lss_core/absorbers.py`): Beer–Lambert,
  absfac = exp(μ/ρ · ρ · t) with the total μ/ρ (coherent scattering
  included, since a scattered photon leaves the beam). Al at 10 keV:
  μ/ρ = 26.23 cm²/g, ρ = 2.699 g/cm³ (Hubbell & Seltzer, NIST SRD 126,
  <https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z13.html>);
  t = 50 µm gives μt = 0.35397 and absfac = **1.4247**. **Cited from
  memory**: physics.nist.gov could not be reached from this session (the
  network blocks it), and installing a tabulation package was not
  permitted, so the number was not checked against the table today. The
  value is nominal: a foil-thickness tolerance of a few % compounds over n
  units (2 % in t is 0.7 % per unit, a factor 1.44 at n = 52).
  Now the default in the window (start-up and on opening a file with
  Pilatus images, which preset 1.42 before) and in `Experiment.fluorescence`.
  Deliberate change: the real-data XFNTR check (bu/2026sep/20260902 scans
  74–79, n = 52) changed hash `e23206a9…` → `1cfab3ab…`; values ×
  (1.4247/1.42)⁵² = 1.187 relative to the previous commit, 1.4247⁵² =
  9.85×10⁷ relative to no factor. Cuts and background images on files
  with Pilatus images change by (1.4247/1.42)ⁿ.
- The 1.606 defect is now P24 in `PHYSICS_ISSUES.md`, marked ⚠, with its
  size and the advice to re-reduce affected results; the entry above has
  the strong note.
- Student t (D26): fixed, ν = 4, scale 0.94 × 0.039 % = 0.0367 % (SD
  0.0519 %). "Width" confirmed as the scale. F51 (per-scan σ_scan) declined;
  the estimator is recorded in `lss_core/errors.py` and F51.
- Simultaneous Pilatus and Vortex: F53, placed in Stage 4 (a scan holding
  both detectors, per-detector selection) and the GUI work. Read in the
  code: today a scan has one `Detector`, decided by whichever of `#V` and
  `#B0` comes later in its header, and both data types share the one image
  list, so a scan with both would show only one. A sample file is needed.
- Beamline to-do: a new section at the end of `TODO.md` (getandsave_mca
  writes no `#A` and no `#M`).

### 2026-11-17 — Foils at other energies; monitor gain as an option

**Q.** (owner) Aluminium for 10 keV and lower energies, copper for 30 keV.
Build the `Monc` gain normalisation as an option. Later a scalar will be
provided to convert the monitor current into photons per second
(estimated).

**A.**

- Foils recorded (D28). F49 (factor from the energy) still needs the unit
  thickness below 10 keV and at 30 keV, and μ/ρ tables for Al and Cu
  (physics.nist.gov is not reachable from this session). Not built; the
  window's value applies at every energy until then.
- Monitor gain option (F52, D29; tests `test_monitor_gain.py`). Built:
  - `#M Monc Gain <value> <unit>` is read into `MoncGain` (A/V); a scan
    without `#M` takes the last one above it (`MoncGainFrom`), like `#A`.
    Lines without a unit ("200") or value are unknown: not guessed.
  - With the option on, a value normalised by M is multiplied by S_ref/S
    with S_ref = 1 µA/V: 200 nA/V → ×5, 1 µA/V → ×1, 5 µA/V → ×0.2,
    10 µA/V → ×0.1. Values then read "per monitor count at 1 µA/V".
    Derivation (`lss_core/monitor.py`): SR570 output V = I/S, V2F counts
    M = G·V·t, so I·t = M·S/G; G is common to all scans.
  - Errors scale by the same factor (S has no uncertainty here). With the
    counting monitor model, u_M still uses the recorded counts M.
  - Applies only when the monitor is `Monc`. Where: MCA tab (spectra, Sum
    All, Script pane `monitor_gain=True`) and SpecPlot (plot, fit, export);
    one setting, a "/ gain" box beside each monitor choice. Scans with an
    unknown gain get no factor, with a warning in the Messages pane.
  - Not yet in the Pilatus paths (cuts, background images, GID). Ref Patch
    does not need it (it measures the scale between scans).
  - Measured effect, bu/2026sep/20260902: scans 1–11 (200 nA/V) get ×5
    and scans 12–129 (10 µA/V) ×0.1, so their relative scale changes by 50;
    XFNTR scans 74–79 all inherit 10 µA/V (×0.1, the same for all six).
- Photons per second (F54): photons/s = C·I with I = M·S/(G·t). The scalar
  should say whether it includes the V2F scale G and the monitor's
  efficiency, and at which energy it holds (an ion chamber's or diode's
  current per photon changes with energy).

### 2026-11-17 — Gain option in the Pilatus paths; uninterpretable gains; foils below 10 keV

**Q.** (owner) Extend the gain option to the Pilatus paths; it mostly
serves comparing different SPEC files, because the gain is normally changed
only with an energy change of more than about 300 eV (a photons/s estimate
would help there; later). List the gains that cannot be interpreted, where
they are and what they are. The absorber foils are not changed below
10 keV: they stay 50 µm Al.

**A.**

- Built (tests `test_monitor_gain.py`): with the option on, every Pilatus
  frame normalised by `Monc` is also multiplied by S_ref/S of its scan, in
  value and error (and in the budget model's monitor amplitude): image
  normalisation and background images (background subtraction), cuts
  (single and summed), GID data, frames at one Q_z (Ref analyse). With the
  option off the code takes the old arithmetic path, so legacy numbers are
  unchanged (checked: `gain=None` and gains of 1 give identical arrays).
  Not used where the scale between scans is measured: Ref Patch, GID
  patching. Burn tests stay within one scan, so the gain cancels.
- Uninterpretable gains: `reports/monitor_gains.md` (generated by
  `tests/tools/monitor_gains.py`): 15 entries in three files — 12 MCA scans
  with no `#M` above them (bu/2026June/20260616 scans 1–12), two empty
  lines, one value without a unit. None is guessed.
- Foils: 50 µm Al per unit at every energy ≤ 10 keV (D30). With that, F49
  for those energies needs only μ/ρ(E) for Al. physics.nist.gov was added
  to the environment's allowed hosts (owner approved), but downloading it
  was refused by this session's permission check; the factor at 6.2 and
  7.5 keV is not computed yet. (Read only, from memory: at 6–8 keV Al's
  μ/ρ is roughly 115–50 cm²/g, so a 50 µm unit attenuates by about 4.7 at
  6 keV and 2.0 at 8 keV, not 1.42; data at those energies reduced with
  1.4247 per unit are wrong by a large factor wherever absorbers are in.)

### 2026-11-18 — The NIST Al page; absorber factor from the energy; the gains

**Q.** (owner) The NIST aluminium page is attached; is it complete? The
gains that could not be read: another agent calls the bu/2026oct set
malformed and found no other SPEC file like it. 5 µA/V is essentially the
default, used on more than 90 % of runs.

**A.**

- *The page is complete* for what is needed (read): the whole SRD 126
  table for Al, 1 keV to 20 MeV, μ/ρ and μ_en/ρ, 38 rows including the
  K edge (1.5596 keV); the ASCII block and the HTML table agree. Its
  10 keV row, μ/ρ = 26.23 cm²/g, is the value used since yesterday from
  memory: the 1.4247 default is now confirmed against the table. What the
  page does not give is the density; ρ = 2.699 g/cm³ (NIST's Table 1) is
  still from memory. Source: Hubbell & Seltzer, NIST SRD 126,
  <https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z13.html>,
  doi:[10.18434/T4D01F](https://doi.org/10.18434/T4D01F).
- *F49 built for Al* (`lss_core/absorbers.py`, tests `test_absorbers.py`,
  `test_gui_absfac_energy.py`). μ/ρ is interpolated linearly in log–log
  between rows (no Al edge between 1.56 keV and 20 MeV); energy
  E = 12.39842/λ from `#W`, rounded to 10 eV. Factors per 50 µm unit:

  | E (keV) | in the data (`#W`, Å) | μ/ρ (cm²/g) | absfac |
  |---|---|---|---|
  | 6.21 | 1.996518 (bu 2026oct/20261019, 20260902) | 104.42 | 4.0924 |
  | 7.51 | 1.650036 (bu 2026oct/20261022) | 60.38 | 2.2589 |
  | 9.90, 9.95 | (bu 20260902) | 27.01, 26.62 | 1.4398, 1.4322 |
  | 10.00 | 1.23984, 1.24 | 26.23 | 1.4247 |

  Measured, size of the method's choices: a local log–log quadratic
  differs from the linear interpolation by 0.07–0.13 % in μ/ρ at 6.2 and
  7.5 keV; rounding E to 10 eV moves μ/ρ by up to 0.15 % at 10 keV. Both are
  ≈0.1 % of ln(absfac**n) (×1.01 on an attenuation of 10⁴), below the foil
  thickness tolerance (2 % in t is ×1.2 on 10⁴).
- *In the window*: a "from E" box beside the Absorber factor field, ticked
  by default. Selecting scans sets the field from their energy; the
  reductions and the Script pane use the field, as before. Unticked: the
  typed value. Where the foil is not known — above 10 keV (20260902 has
  10.05 and 10.52 keV scans) and at 30 keV (Cu; thickness not known yet) —
  the field keeps its value and the Messages pane says why. Scans at
  energies with different factors selected together get one factor and a
  message. NX school and the synthetic data are at 10 keV: unchanged
  (real-data checks: 540 passed, hashes unchanged).
- *What it changes* (measured on the bu files): every scan with absorbers
  in at 6.21 or 7.51 keV was reduced with 1.4247 per unit until now; the
  correct factor is larger by (4.0924/1.4247)ⁿ = 2.87ⁿ at 6.21 keV (×4.6×10³
  at n = 8, the smallest setting in 20261019b) and 1.59ⁿ at 7.51 keV. At
  9.90 keV, ×1.73 at n = 52. Earlier reductions of those scans at
  different absorber settings are mutually inconsistent and should be
  redone.
- *Escan caveat* (read): an energy scan's factor changes along the scan;
  the reader uses the energy in the scan header. At n = 52 near 10 keV,
  100 eV is ≈3 % in μ/ρ, so ×1.7 in absfac**n across 100 eV.
- *Gains*: noted in `reports/monitor_gains.md`. Only three of the 15
  entries are in bu/2026oct (20261019 S1 and S7, 20261022 S2). The other 12
  are bu/2026June/20260616 scans 1–12, `getandsave_mca` scans before the
  first `#M` in that file: not malformed lines but no line at all, the
  same macro gap as for `#A` (beamline to-do). They stay unknown. 5 µA/V
  as the usual gain (D32): with the gain option the reference is
  S_ref = 1 µA/V, so the usual 5 µA/V runs get ×0.2; a reference of
  5 µA/V would leave them unchanged — a question for the owner, not
  changed.
- *Question for the owner* (read from the data, not checked): `#A` is 52
  on every absorber-bearing 10 keV scan of 20260902 (65 scans) and 63 on
  all of 20261022's 7.51 keV scans; 63 is all six foils in. At 10 keV,
  52 units is an attenuation of 1.4247⁵² ≈ 10⁸; at 7.51 keV, 63 units is
  2.2589⁶³ ≈ 10²². If those settings were real during the measurement,
  little beam reached the sample; if the macros moved the foils without
  writing `#A`, the values are stale — and MCA scans 74–79 of 20260902,
  which inherit 52 from scan 73 (D24), would be multiplied by 10⁸ when
  they should not be.

### 2026-11-18 — Binary foil set; tolerance flat, not relative?

**Q.** (owner) The attenuators are not 63 foils of 50 µm but six foils in
a binary arrangement. That may not change the uncertainty, but it does if
the foil tolerance is a flat 1–2 µm rather than 2 % (to be verified by the
owner). A static absorber calibration is not used (the reflectivity
macros patch across scans instead) because the ratio is believed to vary
from day to day with beam position and size and foil position: the foils
are not expected to be perfectly homogeneous.

**A.**

- *The owner is right that it changes the uncertainty* (arithmetic, not
  measured). Setting n = Σ bₖ·2ᵏ units over foils k = 0…5, so the
  thickness error is the sum of the errors of the foils in use, not n
  times a per-unit error. With independent flat tolerances δ per foil, the
  error of ln(absfac**n) is μ·δ·√(number of foils in), μ = μ/ρ·ρ =
  0.00708 µm⁻¹ at 10 keV. δ = 1.5 µm: n = 41 (3 foils) 1.8 %, n = 31
  (5 foils) 2.4 %, n = 63 2.6 %. The relative 2 % model used in these notes
  before (2026-11-17, "2 % in t is a factor 1.44 at n = 52") gave 29 % at
  n = 41. That earlier figure assumed a relative tolerance and should not
  be used.
- *But the measured steps are far off nominal, more than any 1–2 µm
  tolerance* (measured, `tests/tools/absorber_steps.py`, test
  `test_absorber_steps.py`). On NX school scans 6–9 (10 keV), points at
  Q_z measured in both scans of a join give the step directly (no
  interpolation; counting errors only):

  | Join | n (bits) | measured / nominal | extra Al implied |
  |---|---|---|---|
  | S6→S7 | 41 (101001) → 31 (011111) | 0.788 ± 0.005 | +33.6 µm on 500 |
  | S7→S8 | 31 (011111) → 24 (011000) | 0.762 ± 0.006 | +38.3 µm on 350 |
  | S8→S9 | 24 (011000) → 18 (010010) | 0.870 ± 0.005 | +19.6 µm on 300 |

  Every step attenuates more than 50 µm Al per unit predicts, by 7–11 % of
  the thickness changed (1.458–1.481 per unit instead of 1.4247), at 26–
  42 counting errors. χ²/dof within a join is 1.1–2.2, so the points of a
  join agree with each other. Three joins and six foils: the foils cannot
  be solved for individually; one uniform excess of ≈ 7 % fits two joins,
  and the third (foils 1, 2, 4 units out) needs ≈ 15 µm more in the three
  thinnest foils.
- *Which way known effects push* (reasoning, not measured): dead time in
  the brighter scan, and harmonics passing thick foils more easily, would
  both make the measured step *smaller* than the true one, so they do not
  explain it; the true excess would be at least this. Causes it could be
  (not distinguished by one energy): foils thicker than nominal; an alloy
  whose impurities (e.g. Fe, Cu) raise μ; density. Measuring at a second
  energy would separate composition from thickness.
- *What it means for the reader.* Ref Patch, which the macros' patching
  relies on, measures the step and is unaffected. Everything that
  combines settings on the nominal factor — cuts, background images,
  frame averages, GID data, and fluorescence since F50 (I17) — is off by
  this much per step (P28); comparing fluorescence at n = 41 and n = 18
  with 1.4247 per unit would be off by ×0.52 on this day's foils. The
  owner's day-to-day variation cannot be tested with one day of data: it
  needs reflectivity sets with overlapping joins from several days (bu has
  no hklscan reflectivity series). With those, the tool gives the per-join
  steps; enough joins with different bit patterns would give per-foil
  values and their spread over days.
- Side result: NX school uses n = 52 for alignment through the direct
  beam, so an attenuation of ≈ 10⁸ (more by this measurement) at 52 is
  a real setting, not a stale value. Whether `getandsave_mca` scans
  that inherit 52 were really taken at 52 stays open.

### 2026-11-18 — Hand-off: patch checking of the absorber steps on the owner's data

**Question (owner):** write a hand-off telling another agent, who has SPEC
files with `proi` and absorbers, how to do the patch checking to look at
the systematic absorber offsets and the tolerance, including how to patch.

**Answer:** `docs/handoff_out/02-absorber-patch-check.md` with the
self-contained script `docs/handoff_out/02-absorber_steps.py` (SPEC
columns only, numpy). New things learnt while writing it, on NX school
20260923 scans 6–9:

- *SPEC columns are enough* (measured, `tests/test_handoff_absorber_steps.py`):
  ROI counter / Monc at shared L gives step/nominal 0.789, 0.762, 0.870,
  the same as the image reduction with background subtraction (0.788,
  0.762, 0.870).
- *Neither simple foil model fits* (measured): one common fraction for
  every foil (alloy, density, relative tolerance) gives f = +0.0743 ±
  0.0013 with χ² = 169 for 2 dof; six foils with a ±2 µm prior need
  20–30 µm deviations (prior χ² 399 for 6 terms). Three joins, rank 3 of 6.
- *The slits changed at two joins* (measured): Monc/Monp is continuous
  across S6→S7 (0.465–0.478 → 0.469–0.484), jumps ×4.5 across S7→S8 and
  ×1.4 across S8→S9; Monp is constant (2.15×10⁵ /s). So S6→S7 is a clean
  absorber join and the other two also contain a slit change. Monc does not
  change with n, so the absorbers are downstream of Monc. The file records
  no motor positions (`#P` lines repeat the names).
- *Count rate* (measured, weak): peak pixel ≤ 1.1×10⁵ counts/s in the
  brighter scan; it changes 2–4× across a join's three overlap points
  while the ratio stays constant (χ²/dof 1.2–1.9). Image header: `Tau = 0
  s`, `Retrigger_mode: 1`, rate-correction LUT `ContinuousStandard_v1.1`.
  Correction to the earlier entry (reasoning): uncorrected dead time pushes
  the step toward nominal, but a rate correction that over-corrects would
  push it away; the hand-off asks for the rate test rather than assuming
  the sign.


### 2026-11-18 — Answer to hand-off 02 (absorber steps from the owner's data), reviewed

**Received:** the analysing agent's report (`docs/handoff_out/02-answer-report.md`)
and its joins table (`joins.csv`, 1983 joins from 2025-12 to 2026-10,
anonymous ids; not committed, SHA-256 in the report's header). The owner
had told that agent that `Monc` normalises S0/S1 changes and that the ROI is
not cropped after the sample.

**Checked (measured, from joins.csv):** the table reproduces the report:
963 usable 10 keV joins that remove absorber, and single-foil thicknesses
of 68 µm (foil 0, 3 joins), 112.5 (foil 1, 102), 213 (foil 2, 8) and
432.6 (foil 3, 34).

**Reanalysis (measured, `tests/tools/foil_fit_from_joins.py`):** I used only
the joins across which `Monc/Monp` did not change (|ratio − 1| < 0.03,
so nothing upstream of `Monc` changed) with χ²/dof < 20. That is 409 joins;
389 were kept after 5-σ clipping. Their bit patterns have full rank, so all
six foils are determined:

| foil (units) | nominal µm | fitted µm (Al-equivalent, 10 keV) | excess | 1/T per unit |
|---|---|---|---|---|
| 0 (1) | 50 | 54.7 ± 0.1 | +9.3 % | 1.4726 |
| 1 (2) | 100 | 112.2 ± 0.1 | +12.2 % | 1.4873 |
| 2 (4) | 200 | 218.0 ± 0.2 | +9.0 % | 1.4707 |
| 3 (8) | 400 | 432.1 ± 0.2 | +8.0 % | 1.4658 |
| 4 (16) | 800 | 862.7 ± 0.4 | +7.8 % | 1.4648 |
| 5 (32) | 1600 | 1725.1 ± 0.5 | +7.8 % | 1.4647 |

- *Fit quality.* The robust scatter of a join about this fit is 0.87 µm
  (0.6 % in the step).
- *Robust to the cuts.* Changing the Monc/Monp tolerance (1–3 %), the
  χ² cut (5, 20, none) or the 0–1 % error floor moves each foil by at most
  0.9 µm.
- *Stable over the year.* The first half of the year alone (R01–R11) gives
  the same foils to within 0.5 µm. Each run's median residual stays within
  ±1.2 µm across all 17 runs, from 2025-12 to 2026-10.
- *Not one fraction for every foil.* The foils follow t ≈ 1.075 × nominal +
  3.1 µm, with each foil off that line by up to ±2 µm (foil 1 is +7 µm
  above 7.5 %). A pure fraction is excluded (χ² 1762 for 5 dof).
- *NX school is explained.* With these foils, scans 6–9 of NX school
  20260923 (in the table as R16) have residuals of +1.3, +3.4 and −0.2 µm.
  "Neither simple model fits" (entry above) was the per-foil differences.

**Where the jumps come from (measured).** Across all the joins where
`Monc/Monp` changed (554, including the χ² ≥ 20 ones), 39 % are more than
5 µm off this fit, against 4 % of the others. The large ones form one
configuration:
- S1 and S4 changed at the 25/26 → 20/22/23 join;
- the residual is +54 ± 3 µm;
- they come from five files: R05 (1 join), R17 from 2026-09-26, R18, R19,
  R20 and R21 (to 2026-10-16).

At the same joins, F = exp(μ·residual) × (`Monc/Monp` ratio) is the
increase of the beam at the detector after the foils are taken out. F is
2.26–2.32 in the anomalous joins and 2.19–2.26 in the normal ones of the
same type. The beam at the detector rose the same way in both groups, but
`Monc` registered only ×1.55–1.62 instead of ×2.0–2.3. So **`Monc` missed
about a third of the added beam in those series.** The gains are the same
(5 µA/V on both sides).

Smaller versions of the same effect:
- R04/R05: +11 µm, `Monc` short by about 8 %;
- R18: S1 only, ratio 0.91, −19 µm.

This is P29.

**Revisions to the report:**
1. "Slit changes do not spoil a join". Its test compared each join with
   the median of the same join type, and the median absorbs a
   configuration that most joins of a type share. Grouped by the
   `Monc/Monp` change instead, the effect is large and reproducible. The
   `#P`-derived class also labels 367 joins "S4–S7 only" across which
   `Monc/Monp` changed, i.e. something upstream of `Monc` changed too.
2. "Changes come in steps between runs … foil or beam position on a
   non-uniform foil." The recurring joins that jump (26→20, 25→22, 26→23)
   are those where `Monc` missed part of a slit change. With those
   excluded the foils do not change over the year.
3. Its foil-0 single-foil value (68 µm) comes from three 17→16 joins with
   an S1 + S4 change. The clean fit gives 54.7 µm.
4. Its across-day spread for some recurring joins includes single-day
   values such as 0.035 and 0.131 (failed joins, χ²/dof in the thousands).
   Its 90th percentile of 23 % is driven by these and by item 2.

**Answers to the owner's questions (measured unless marked):**
- *Day-to-day variation of the foils:* none beyond about 1 µm per foil
  (0.7 % in transmission) in these data, which cover 17 runs and a year at
  10 keV. The day-to-day variation that patching absorbs is in the monitor
  normalisation across slit changes (P29), not in the foils.
- *Tolerance flat or relative:* neither alone. About +7.5 % of the
  thickness, plus about 3 µm, plus about ±2 µm per foil.
- *Possible cause of the +7.5 % (reasoning; μ/ρ values from memory, not
  checked).* μ/ρ at 10 keV is about 170 cm²/g for Fe, 216 for Cu and 150
  for Mn, against 26.2 for Al. So about 1 % of Fe, Mn or Cu impurity raises
  μ/ρ by 5–8 %, and common commercial Al grades (1100, 3003) contain that
  much. Composition and thickness separate by energy: below the Fe K edge
  (7.11 keV) and the Mn K edge (6.54 keV) an impurity's share drops, but a
  thickness excess stays the same in µm. Reflectivity series with overlaps
  at 6–7 keV would decide it.

**For the reader:**
- Ref Patch is still the right way to join scans, now because of P29 (the
  monitor), not the foils.
- The paths that use the nominal factor (cuts, background images, frame
  averages, GID, fluorescence F50) can use this foil table at 10 keV, good
  to about 1 µm per foil. That is a proposal for the owner to decide
  (TODO). It is not built.

### 2026-11-18 — Calibrated foils in the reader; known ratio instead of a poor patch

**Owner:** build the calibrated foil table into the reader; show the foil
assumptions in a preferences panel (short, tooltips); in the patch window
suggest the known absorber ratio when the counting error of the patch
exceeds the foil ratio's uncertainty; use it automatically beyond a
threshold where plainly better; threshold and switch in the preferences.

**Also received:** the analysing agent's answer to hand-off 03 (not
committed; anonymous, dates removed). It reproduced the foil fit to 0.1 µm
(409 joins, 389 kept, rank 6, 0.87 µm), by half-year to ≤ 0.9 µm, and found
for P29 (measured) that it is **scan a's Monc that reads high at the narrow
S1 gap** (0.04 mm), Monp unchanged, the detector's jump F = 2.2–2.3
throughout; not a Monc offset (beam-off Monc 7–150 counts/s); S1 + S4 moved
at all 367 joins we saw labelled "S4–S7". In the anomalous series Monc/Monp
also drifts differently along scan b (×0.92 against ×0.82).

**What was built (choices, reasoning):**
- *Where the calibration applies:* 9.70–10.30 keV, with Al's μ/ρ at the
  energy. No K edge of the usual Al impurities lies between Zn (9.66 keV)
  and Ga (10.37 keV) (edge energies from memory). Elsewhere: 50 µm Al per
  unit, as before. Only with "from E" (a typed number is a number).
- *Uncertainty of a known ratio:* μ · 1.0 µm per foil that differs, in
  quadrature (one join scatters 0.87 µm about the fit; run medians ±1.2
  µm). At 10 keV that is 0.71 % per foil: 1.0–1.7 % for the joins seen.
- *Patch error compared:* the error of the factor the patch fits
  (`stitching.fitted_factor`, the same arithmetic as the merge).
- *Automatic use* (all must hold): fit error > threshold (default 3 %);
  known error ≤ half the fit error; Monc/Monp across the join within 3 %
  of 1 (P29: otherwise the scale is not the foils alone, and the known
  ratio would be wrong by up to ×1.46); fit and known ratio within 3σ.
  Without Monp nothing is automatic. The patch window shows the choice and
  can undo it; the Script pane records it as `factors=`.
- *Effect on existing outputs:* none for a typed factor, outside
  9.70–10.30 keV, or with the preference off. At 10 keV the default
  changes (deliberate): cuts, background images, frame averages, GID and
  fluorescence at absorber settings ≠ 0 use the calibrated foils. Example
  before/after, n = 3 (foils 0 + 1): 1.4247³ = 2.892 → exp(μ·166.9 µm) =
  3.259 (+12.7 %). The legacy reflectivity fixtures are unchanged (no
  absorber factor; the synthetic data have no Monp).

How verified: tests (`test_absorbers.py`, `test_gui_preferences.py`,
`test_known_ratio_patch.py`), quick and slow suites, crash sweep.

### 2026-11-18 — How far the absorber ratios can be trusted; higher Qz less so

**Received:** `docs/handoff_out/03-answer/ABSORBER_RATIOS.md` (the
analysing agent, from the same year of data; measured there, not here).
The owner's summary: higher Qz is less trustworthy.

- *Run-to-run spread of each foil* (leave one run out, 17 runs): 0.6, 0.5,
  0.8, 0.6, 1.3, 1.3 µm.
- *Prediction of runs left out*, clean joins: ±0.6 % (68 %), ±1.6 %
  (95 %) with the overlap at Qz < 0.25 1/Å (335 joins); ±3.0 % (68 %) at
  Qz ≥ 0.25 (89 joins). With S1 changed: ±2.2 % in typical runs, −26 % in
  the affected runs (P29).
- *Coverage of the stated error* (jackknife ⊕ counting ⊕ 0.5 % per step):
  68 % of errors within 0.95 σ at low Qz, 3.19 σ at high Qz. The note puts
  the excess at high Qz in the single steps, not in the foils (reasoning
  there: same foils, more scatter than counting explains).
- *Its transmission table* is reproduced by `lss_core.absorbers` to 0.2 %
  (`test_calibrated_transmission_matches_the_absorber_ratios_table`).

**Changed in the reader (deliberate):** the known ratio's error was
μ · 1 µm per foil that differs (my assumption); it is now μ · σ_k (the
run-to-run spreads) in quadrature ⊕ 0.5 %, × 3.2 when the overlap starts
at Qz ≥ 0.25 1/Å. Before → after, relative error at 10 keV: 42→33 (foils 3,
1, 0) 1.23 % → 0.86 % (low Qz) or 2.75 % (high Qz); 6→2 (foil 2) 0.71 % →
0.76 %. Consequence: at high-Qz joins the known ratio replaces a patch only
when the patch's error is at least twice ~2.8 %, i.e. rarely; the patch
stays the default there, as the note advises ("quote ±3 %"). Which side
really carries the high-Qz excess (the measured steps or the ratio) is not
settled; if it is the steps, the patch's own error is understated there
too (reasoning). The Preferences table shows the ± column; the tooltips say
the rest.

How verified: tests (`test_absorbers.py`, `test_gui_preferences.py`,
`test_known_ratio_patch.py`), quick and slow suites.

### 2026-11-18 — The IDL pinhole/GID code; the NX school GID scans are pinhole data

**Owner:** sent five IDL files from Mati's stash that mention "pinhole"
(`docs/reference_code/idl/`); asked for a review of what is useful,
compared with the reader. Review by a subagent:
`docs/handoff_out/04-answer/IDL_REVIEW.md` (hand-off 04).

**What the IDL code says (read there, with line numbers):** "pinhole" is a
way of measuring: a narrow slit on the detector arm (S4) acts as a pinhole
camera, so each detector column sees its own in-plane angle at the
pinhole–detector distance. `PD_PIN` gives every column its own angle;
`PD_GID` keeps one column band per frame, as the reader does; `PD_MERGE`
splices pinhole maps into GID maps, scaling by a quadratic in Qxy. The
pixel→angle formulas and the join arithmetic are in routines not supplied
(`SCAN_PD_READ`, `SCAN_PD_LCOO`, `IMG_JOIN`, `PD_GID_READ`,
`PD_PIN_RANGE`).

**Measured (the subagent; checked again here with separate code, scan 11,
41 frames, rows 15–486):**
- lit columns 29–137 (the S5 window); the reader's GID patch sums columns
  46–48: median 776 counts per frame against 18 434 in the window, so it
  uses ≈ 4 % of the counts;
- a Bragg peak drifts 26.3–26.9 columns per degree of Det_Th (frames
  17–31, 19–29, 21–27), an effective distance of 259–265 mm: close to
  `S7D_Dist` = 271 mm, far from `S2D_Dist` = 551 mm (55.9 columns/degree).
  So these frames are pinhole data, and wherever the reader maps their
  columns with S2D (cuts and display with the "pinhole" box off, its
  default) the horizontal angle scale is ≈ ×2 too coarse (P32);
- the reader's `calArea` × sin 2θ is constant to 2×10⁻⁵ over 14–18° for
  scan 11's slits, i.e. it equals the IDL `SIN_NORM` normalisation here
  (subagent only).

**Inferred there, not confirmed:** the sample is seen over ≈ columns 30–80
with a non-flat response, so a per-column response must be measured from
the data; the specification (§7 of the review) bins per-column data by
Σ counts / Σ normalisation within a scan and joins Qz levels on a common
2θ grid (covers F62). Waiting for the owner's answers (§8 there) and the
missing routines before building F45.

### 2026-11-18 — Pinhole geometry: the owner's answers (part 1)

**Owner:** S4 is the usual pinhole-defining slit. Every SPEC header gives
the **sample-to-slit distance**; the detector-to-sample distance is known
elsewhere. `S7D_Dist` is antiquated and its meaning is not firm ("it
doesn't really matter what S7 is"). Answers to the other questions will
follow. Also sent: `SCAN_PD_READ`, `SCAN_PD_LCOO`, `PD_PIN_RANGE`,
`PD_GID_READ`, `IMG_JOIN` (`docs/reference_code/idl/`).

**Read from the new IDL files (not yet run or tested):**
- `PD_PIN_RANGE` uses `PDIST` (sample–detector), `PDSDIST`
  (pinhole–detector: `PDIST − PDSDIST` is the sample–pinhole length, and
  S5 sits at `PDSDIST − 32` mm from the pinhole), the S1 vertical gap, the
  footprint `beam/sin α` and the S5 half-gaps to give the columns the
  pinhole sees.
- `SCAN_PD_LCOO` applies the pinhole transformation by default when Det_Th
  > 1° (`pinhole` keyword default `angs[2] gt 1`), and corrects the
  distance for the detector-arm lift: `dist = PDIST + G_L[3](1/cos β − 1)`.
- `PD_GID_READ`: β = Out_Rot + atan(pixel·(n − n_s)/dist), and
  Qxy = 2k √((sin((α+β)/2) sin((α−β)/2))² + cos α cos β sin²(2θ/2)),
  Qz = 2k sin((α+β)/2) cos((α−β)/2), k = 2π/λ.
- `IMG_JOIN`: one factor per join from `SCAN_JOIN` (not supplied) on the
  integrated profiles; the overlap is the **inverse-variance weighted
  mean** (the reader averages plainly); the result covers only the range
  common to all images (intersection), regridded by triangulation.

**Open:** which header item is the sample-to-S4 distance in the reader's
files (`#B1` holds 551 and 271 for NX scan 11; with 551 as sample–detector
and 271 as sample–S4, the pinhole–detector distance would be 280 mm, while
the measured peak drift gives 259–265 mm); where the sample–detector
distance should come from. The review is being updated with these files.

**Update of the review (second batch), 2026-11-18** (`IDL_REVIEW.md`, top
section; subagent, measured on NX scan 11 unless marked): with the column
response divided out, pinhole→detector = 267 ± 2 mm (the earlier 256–265
was biased low); 280 (551 − 271) is excluded at ≈ 6σ. Two readings remain:
271 is the S4→detector distance, or 271 is the sample→slit distance and
the detector is at ≈ 538 mm, not 551 (owner to say). The G_L[3] term is
0.0007 mm on scan 11 and does not explain it. `PD_GID_READ`'s β, Qxy, Qz
equal the reader's to 1e-12, except IDL's vertical distance term
PDIST + G_L[3](1/cos Out_Rot − 1) (scan 12: 0.049° in β, 0.004 Å⁻¹ in Qz
at the top row). `IMG_JOIN` weights overlap pixels by their own errors,
which biases low counts low (simulated 0.31× at 0.4 counts/pixel, typical
of NX pinhole frames), so the spec combines overlaps as Σ counts / Σ
normalisation instead. New reader issues: P34, P35.

### 2026-11-18 — Geometry distances from the owner; new private GID frames

**Owner:** g_l1 ≈ 560 mm (monochromator crystal → S1 slits), g_l2 ≈ 1238 mm
(crystal → sample), g_l3 ≈ 556 mm (sample → Pilatus); all horizontal
distances, not optical path lengths.

**Where they are (read):** the `#G0` line, 6th–8th numbers (NX scan 11:
`560 1238 556`); `spec_routines.py:119-122` reads them as `g_l1`, `g_l2`,
`g_l3`. The reader uses `g_l2` only for the sample-height offset
(sh = −g_l2 tan α) and takes the detector distance from `#B1`'s third
number (`S2D_Dist`, 551 on NX), not from g_l3 (556): 0.9 % on every angle
offset from the direct beam.

**What it means (reasoning):**
- The IDL `PD_PIN_RANGE` uses (G_L[2] − G_L[1]) as the S1→sample distance
  (1238 − 560 = 678 mm), so its G_L array is [·, g_l1, g_l2, g_l3], and
  `SCAN_PD_LCOO`'s G_L[3] in `dist = PDIST + G_L[3](1/cos β − 1)` is g_l3:
  the horizontal distance turned into the path length when the detector
  arm is raised to β (556 × (1/cos 6.5° − 1) = 3.6 mm on NX scan 12).
- Pinhole distance: measured 267 ± 2 mm (IDL review, NX scan 11). With
  g_l3 = 556 and 271 as the sample→slit distance, S4→detector would be
  285 mm, which the measurement excludes; 271 as the S4→detector distance
  fits (2σ). Which header item is the sample→slit distance the owner
  mentioned is still to be named.

**New private data (owner):** 206 Pilatus 100K frames of GID scans
136–146 (one beamtime, no SPEC file), in `sample_data/private/gid_scans_136-146/`
(git-ignored, never pushed). Dates removed as asked: the file-name prefix
is `gid_` (was the date), the EPICS time-stamp tags 65000/65002/65003 in
each TIFF are zero, file times are set to 2000-01-01; pixel data checked
identical to the originals. Without the SPEC file (Det_Th per frame,
In_Rot, Out_Rot, direct beam, slits, G_L, monitors) the reader cannot
place them in angle or Q yet.

### 2026-11-18 — What the `#B1` and `#G0` numbers are

**Owner:** `#B1 53 147 551 271` should work for the example data; asked
whether `#B1` or `#G0` (`0 1 1 1 90 560 1238 556 1.92359 0 1 0 …`) wins,
and for a table. (Parsing read from `spec_routines.py:119-157`; meanings
from the owner, measurement, or marked as a guess.)

| Line, # | Value | Reader | Meaning | Used for | How known |
|---|---|---|---|---|---|
| #B1, 1 | 53 | `DBPos[0]` | direct-beam row (pixels) | β = 0 row | read |
| #B1, 2 | 147 | `DBPos[1]` | direct-beam column, raw orientation; reader column 194 − 147 = 47 | 2θ = Det_Th column | read; specular spot at 47 (IDL review) |
| #B1, 3 | 551 | `S2D_Dist` | sample → detector (mm), IDL `PDIST` | pixel → angle | owner ("should work") |
| #B1, 4 | 271 | `S7D_Dist` | S4 (pinhole) → detector (mm), IDL `PDSDIST` | 2θ per column, pinhole | measured 267 ± 2 mm (NX scan 11) |
| #G0, 1–4 | 0 1 1 1 | — | unknown (mode switches?) | — | unknown |
| #G0, 5 | 90 | — | unknown; IDL `G_L[0]`? | — | unknown |
| #G0, 6 | 560 | `g_l1` | crystal → S1, horizontal (mm); IDL `G_L[1]` | IDL footprint: S1 → sample = g_l2 − g_l1 | owner |
| #G0, 7 | 1238 | `g_l2` | crystal → sample, horizontal (mm); IDL `G_L[2]` | reader: sh = −g_l2 tan α; g_l2 calibration | owner |
| #G0, 8 | 556 | `g_l3` | sample → detector, horizontal (mm); IDL `G_L[3]` | IDL: path length when the arm is raised, + g_l3(1/cos β − 1); unused by the reader | owner; read |
| #G0, 9 | 1.92359 | — | unknown (a crystal d-spacing in Å? Si(220) is 1.920) | — | guess |
| #G0, 10–18 | 0 1 0 … | — | unknown | — | unknown |

**No conflict (reasoning):** #B1's 551 is the distance for pixel → angle;
g_l3 enters only the arm-lift term, where 556 against 551 changes 0.03 mm
at β = 6.5°. **Open:** the owner said the header gives the sample → slit
distance; 271 as sample → S4 would make the pinhole 280 mm from the
detector, excluded by the measured 267 ± 2 mm, so 271 is read as S4 →
detector unless the sample → slit distance is elsewhere in the header.

**Owner, 2026-11-18 (settles the table above):** 271 is the S4 → detector
distance ("perhaps your measurement is more up to date": 267 ± 2 mm
measured on NX scan 11); 551 is the sample → detector distance; 556 is
g_l3, the horizontal distance from the sample to the rotation centre of
the output (detector) arm; the detector is close to it but not exactly
there. So: pixel → angle uses 551 vertically and in GID, 271 (or a value
fitted from the data) per column in pinhole geometry; g_l3 only enters the
arm geometry.

### 2026-11-18 — Pinhole-geometry GID built (F45), first version

**Owner:** sent the SPEC file for the private GID frames (dates removed
here, kept in `sample_data/private/`, never pushed); "proceed carefully
with your suggested workflow".

**Built** (`lss_core/pinhole.py`; GID worksheet "Pinhole: angle per
column", **off by default**, so the legacy patch and its references are
unchanged): 2θ per column through the pinhole with D_p = `#B1` 4th number
(271 mm, owner) unless typed; β per row with the IDL arm term; usable
columns = asymmetric S5 projection ∩ footprint range (`PD_PIN_RANGE`);
weight W = M · A · P · R with A the footprint fraction (calArea's
arithmetic for a one-pixel band at the column's angle, equal to calArea to
1e-12), P the polarisation, R the column response fitted from the data;
binning I = ΣN/ΣW on one-column bins (p/D_p); scans of a level joined by
one factor; Qz levels joined by the legacy vertical join for now (F62
next); bins seen by fewer than 2 frames left out.

**Measured on NX scan 11 (public):** S5 window 27.2–139.3 (lit columns
29–137); columns used 28–90 at Det_Th 14° to 28–102 at 18°; 17× the counts
of the 3-column patch; DPPC peak at 2θ 16.655°; the column response spans
0.25–1.42 over the used columns. **Distance fit — correction to the IDL
review:** the fitted D_p depends on the columns used, 258–280 mm (columns
40–70: 258; 30–60: 264; 35–80: 269; 30–100: 271; 27–139: 280), each with a
statistical error of ±2–3 mm. The column response and the peak shape bias
the centroids by several mm, so "267 ± 2" and "280 excluded at 6σ" in the
review were too strong; 271 (header, owner) is within the spread and is
the default. The worksheet's Fit button shows a fit; it does not apply it.

**Synthetic checks** (`tests/test_pinhole.py`): a line at fixed 2θ lands
in one bin from ~70 columns per frame; mapping with a near-sample distance
smears it over > 5 bins; counts are conserved; at 0.4 counts per pixel the
estimate is unbiased (1.00 ± 0.01) with pulls of width 1 ± 0.05; a known
hump-shaped column response is recovered to < 1 %; a synthetic drift gives
the true D_p within 2 mm.

**Private scans (owner's):** checked locally; results reported to the
owner, not recorded here.

**Not yet:** F62 flexible overlaps between Qz levels (the vertical join is
still the legacy one, with its edge copies, P33); the footprint fraction
uses the band through the pinhole centre (offset e = 0; the response
absorbs the rest); split-pixel binning; P34 (Pix V cut β) and P32
(automatic pinhole switch for display and cuts) are separate fixes.

### 2026-11-18 — Foils at 10.05/10.52 keV, `#A` 52 and 63, gain reference, photons/s

**Owner:**
- 10.05 and 10.52 keV use the aluminium foils, as every energy below
  10 keV does.
- `#A` 52 and 63 are real settings. (The question came from the reader's
  fallback: an *unreadable* `#A` line is set to 63, which looks like a real
  setting; that is now a separate open issue in TODO.)
- Gain reference: 5 µA/V.
- Photons/s: the xray_fluxor hand-off
  (`docs/handoff/xray_fluxor_counts_to_photons.md`, copied from the
  owner's public repository).

**Changed (deliberate):**
- `absorbers.AL_MAX_KEV` 10 → 10.52 keV: at 10.01–10.52 keV the nominal
  50 µm Al factor at the energy is used where the field kept its value
  before (10.52 keV: 1.3565 per unit; 10.05 keV is inside the calibrated
  range 9.70–10.30 and gets the calibrated foils).
- Monitor-gain option (off by default): S_ref 1 → 5 µA/V. Values with the
  option on are now per monitor count at 5 µA/V: a scan at 5 µA/V is
  multiplied by 1 (was 0.2), at 200 nA/V by 25 (was 5), at 10 µA/V by 0.5
  (was 0.1). Ratios between scans are unchanged.

**Built:** `lss_core/flux.py`, the hand-off's route D: photons/s at the
chamber's exit plane from counts, count time, energy and SR570
sensitivity, for MonC or MonP, with the gas-density, sensitivity and
wall-loss scalings and the hand-off's bounds (±3.6 % below 13 keV).
Reproduces the hand-off's three worked examples to ≤ 0.1 % (test). At
5 µA/V and 10 keV one net Hz of Monc is 4.37 × 10⁷ photons/s. Assumed
when not given (and flagged): dark rate 0, 24.9 °C, 98.99 kPa. Not yet in
the window ("per incident photon" normalisation: TODO).

### 2026-11-18 — Pinhole is the default; Monc dark 50 Hz

**Owner:** "Pinhole mode really is default." For old data without a
recorded dark rate, assume 50 Hz on Monc ("the effect is not really
important").

**Changed (deliberate):**
- GID patch: pinhole geometry by default (`GIDParams.pinhole = True`); the
  worksheet switch gives the old patch exactly. The legacy GID tests now
  switch it off explicitly, as their references were made with it.
- Display and raw-frame cuts: the "Pinhole" box is ticked by default and
  acts only on frames at Det_Th > 1° (IDL `SCAN_PD_LCOO` rule), whose
  horizontal angle then uses the S4-detector distance; reflectivity frames
  (Det_Th ≈ 0) are unaffected. NX GID frames: one column = p/271 rad
  instead of p/551 (P32). `Experiment.cut(pinhole=True)` by default, same
  rule; the Script pane writes `pinhole=False` when the box is unticked.
- P34 fixed: the "Pix V" cut's β uses the sample-detector distance
  (before: the cut distance, ×2 too large with the pinhole box on).
- The movie view restores the pinhole box (it always unticked it).
- `flux.photons_per_second`: Monc dark 50 Hz when not given (MonP 0),
  flagged. At 10 keV, 5 µA/V that is 2.2 × 10⁹ photons/s, 0.05 % of a
  10⁵ Hz reading.

### 2026-11-19 — Joining Qz levels in pinhole mode (F62)

**Built** (`lss_core/pinhole.join_levels`; the pinhole GID patch uses it):
all levels are binned on one shared 2θ grid (`shared_edges`), so their
bins coincide and nothing is interpolated in 2θ; each level's rows go onto
one β grid (step = the largest row step of any level, so no level skips a
bin), as summed counts and weights; levels are joined in order of β, each
with one factor fitted on the β overlap within the 2θ bins both have; the
map is ΣN/ΣW; σ includes each factor's error times its level's share of
the weight. Range across levels: "common" (default, as IDL `IMG_JOIN`) or
"all" (union, empty cells where a level has no data; the factor always
uses the common part). One level alone keeps its own rows.

**Found while testing (synthetic, measured):** summing counts and weights
over the common 2θ bins before taking the ratio biased the factor by
+2.6 % (1.283 for a true 1.25), because the two levels cover those bins
with different numbers of frames and a 2θ peak is then weighted
differently in each. The factor now compares the levels' intensities
averaged with equal weight over the same cells: 1.25 within its error
(±0.0004). The legacy vertical join (`imagevjoin`) is unchanged and keeps
P33's edge copies.

**Checked:** synthetic two-level case (factor, common/all ranges, joined
map = truth to 1 %, counts conserved); NX scans 11 + 12 in pinhole mode:
one vertical join logged, no empty cells in "common", "all" has them,
Save GID works.

### 2026-11-19 — Values per incident photon in the window (F54)

**Built:** "/ photon" boxes beside "/ gain" in the MCA tab and SpecPlot (one
setting, as the gain; ticking it ticks the gain, unticking the gain unticks
it). A value divided by the Monc counts M is multiplied by M/N, N the
photons through the Monc chamber in the same time (xray_fluxor hand-off,
route D, `lss_core/flux.py`):

    M/N = 1 / (q(E) · S/(500 nA/V) · gas · (1 − D/r)),   r = M/t.

So "per photon" is the gain option times a function of energy, and the
dark term. Choices made here, all in tooltips and docstrings:
- E from the scan's wavelength (`#W` line); q(E) interpolated log–log in the
  hand-off's table (5–30 keV); outside it, or with an unknown gain, the
  scan keeps per-count values and the Messages pane says so once.
- D = 50 Hz (D41). r: each MCA spectrum's Monc / real time; for SPEC
  columns and Pilatus frames the scan's median Monc/Seconds (one factor
  per scan; D/r is ≲ 0.05 % at the usual ≳ 1e5 Hz, so the per-point
  difference is below that).
- Gas at the table's 24.9 °C, 98.99 kPa (SPEC records neither; ±0.8 % from
  the site-mean pressure, hand-off §3).
- The bounds (±3.6 % below 13 keV; 30 keV bounds used above 13) are a
  common scale for all scans at one energy, so they are not added to the
  point errors.
- Ref Patch and the reflectivity are not affected (they divide by the
  direct beam, where any monitor scale cancels).

**Not done:** the photons are at the chamber's exit plane; windows and air
from there to the sample are not included (hand-off route D says so).

**Checked (tests, synthetic data):** the factor equals M/N from
`photons_per_second` and 1/(4.37e6·10·(1 − 50/1e5)) at 10 keV, 5 µA/V,
1e5 Hz; invariant I20; scripted fluorescence and cuts equal the per-count
values times the factor (values and errors, rel 1e-12); the window's MCA
export and cut export are reproduced byte for byte by the Script pane.
Not checked against an independent flux measurement.

### 2026-11-19 — An unreadable `#A`; gas and dark on the beamline side

**Q (owner).** Pilatus frames don't need an absorber number at all; they get
patched and normalised all the same. Did you find data with this issue or
extrapolate from the MCA problem?

**A.** Both, in order: the issue was first found by *reading*
`spec_routines.py` (an unreadable `#A` became 63). Searching the sample
files afterwards (2026-11-19, `grep` of every `#A` line in `sample_data/`)
found **one real case**: an empty `#A Absorber ` line on scan 1 of
bu/2026oct/20261019, a Pilatus scan. Every other `#A` line in the public and
private sample files has a number.

With 63 that scan's frames were multiplied by absfac⁶³ before patching. The
fitted patch factor absorbs any constant per scan, so a patched curve was
not affected; a single scan, a cut or a known-ratio join would have been.

**Changed:** unreadable → `Absorber` None (text kept as `AbsorberText`).
Pilatus frames use n = 0 in the arithmetic (no factor), the image list
shows "Abs=?", the Messages pane says so once per scan, and the known
absorber ratio is not offered for its joins. A Pilatus scan with no `#A`
at all is now listed the same way (before, all its frames were dropped as
"no readable image"). MCA scans below an unreadable line are unknown (no
factor). Decision D42.

**Checked (tests, synthetic data, `test_absorber_unknown.py`):** with the
known ratio off, the patched `_ref.txt` with the scan-2 setting blanked
equals the one with it known (rel 1e-6), confirming "patched all the same".

**Beamline side (owner):** record the chamber's temperature and pressure,
or the current photons/s from the monitor IOC; record the dark counts from
the new monitor IOC. Both in TODO's beamline list.

### 2026-11-19 — How completely are method comparisons and decisions recorded?

**Q (owner).** How comprehensively are the method comparisons recorded?
Later another agent will make figures comparing all new methods with old
ones across several data sets, and needs the information to do it
efficiently. Small decisions that bear on output need proven rationales,
alongside or in a central doc, and the future manual writer needs
breadcrumbs now.

**A (assessment by reading the docs, 2026-11-19).** Before today:
- Comparisons were recorded, but as prose in the dated entries of this
  file, with numbers inline; no central list, no regeneration commands for
  most, and old/new **arrays were saved for none** except the absorber
  work (hand-off 03 `figdata/`, `joins.csv`) and the byte-exact legacy
  fixtures. Private-data comparisons were reported in chat only, by rule.
- Decisions were in `FEATURE_REQUESTS.md` (D1–D42, one line each, mostly
  without the evidence kind), with reasons and before/after values here;
  assumptions of this project were not marked as such in one place.
- Nothing was written for a manual; the explanations live in tooltips.

**Done:** `COMPARISONS.md` (20 comparisons, each with evidence kind,
figure-ready data or "none", the command to regenerate, and the switches
that run old and new side by side), `OUTPUT_DECISIONS.md` (every default
and output change with rationale and evidence; open assumptions listed for
the owner), `MANUAL_NOTES.md` and `docs/manual/controls.md` (357 controls,
205 with tooltips, generated by `tests/tools/dump_tooltips.py`). AGENTS.md
rule 11 makes keeping them current part of every commit.

**Still missing (listed in COMPARISONS "Gaps"):** saved old/new arrays for
the error-model and GID comparisons; GID as a script call.

### 2026-11-19 — GID scriptable; old and new GID compared on NX scan 11

**Built:** the window's GID patch (both geometries), its joins (`imagehjoin`,
`imagevjoin`), `calArea`, the map products (angles, Q, relaxed Q grid,
integrals) and Save GID moved unchanged into `lss_core/gid.py`; the window
and `Experiment.gid` call them. Save GID writes the call to the Script pane.

**Checked (tests):** the legacy references (NX scan 11 Qxy/Qz, scans 11–12
saved files) are unchanged; the script reproduces the window's three files
byte for byte in both geometries and both axes, with the relaxed grid, a
typed column count and some frames (`tests/test_gid_script.py`).

**Found while moving (read, not fixed; PHYSICS_ISSUES P36, P37):** in the
legacy patch, the first frame of each high-Qz scan is not scaled back by the
scan's mean monitor, and a single high-Qz scan is looked up under the middle
level's scan number. Only maps with three Qz levels are affected; no data
set here has three, so they are recorded with the "as coded" behaviour kept.

**Measured (NX scan 11 alone, `tests/tools/compare_methods.py`):** DPPC peak
at Qxy 1.4631 1/Å (legacy) and 1.4679 1/Å (pinhole), 0.33 % apart; 40 vs 176
Qxy bins; relative error at the peak 2.5 % vs 1.0 %. Pinhole distance 258 /
271 / 280 mm moves the peak to 1.4695 / 1.4679 / 1.4666 1/Å. Which peak
position is right is not settled by this: the legacy map puts each frame's
3 central columns at the frame's Det_Th, so its 2θ is that of the column
nearest the direct-beam column; the pinhole map gives every column its
own angle through the pinhole.

**Measured (NX scans 11 + 12):** not a like-for-like pair. Scan 12 stopped
after 4 frames (2θ 13.4–15.8°), so the pinhole join's common range ends at
15.8° and misses the DPPC peak (16.65°); the legacy join fills 14–18° with
copies of scan 12's edge (P33). With `transverse='union'` the map keeps
13.4–19.9°, but the β-integrated profile is NaN where a level has no data
(sums are not taken over missing cells).

**Error models on the final NX 6–9 `_ref` curve:** σ(budget)/σ(legacy)
0.861–1.002 (Gaussian 0.04 %, median 1.000), 0.893–1.004 (Student t); values
within 5e-6.

### 2026-11-19 — "Scan i of N": what the reader needs, and cancelled scans

**Q (owner).** Recommend the "scan i of N" syntax and its information
capacity: is "reflectivity, scan i of N" enough, or is something else
needed? What about users cancelling the later scans; can the reader infer
how to handle that?

**A.** Proposal in `docs/handoff_out/05-scan-series-syntax.md`. In short:
"kind, i of N" is not enough on its own. The reader also needs an **id**
per macro run (to tell repeated runs apart and to join a resumed run) and
a **role** (data vs alignment/check scans, so that a macro may realign as
often as it needs without spoiling N). Syntax: `#U Series id=… i=… n=…
kind=… [role=…]` in every scan header, `#U SeriesMacro …` on the first,
and an optional `#C Series id=… end status=aborted after=i` from the
macro's abort hook.

Cancellation: SPEC already writes `#C … Scan aborted after k points.` in
a stopped scan (found in the NX school and the owner's files); what is
lost is the rest of the plan, which only `n` can tell. With `n`, the
reader infers the end from the next scan of another series, a short last
scan, or a file that stopped growing; the end line removes the remaining
guess. Missing scans never block a reduction: the scans present are
reduced and labelled "aborted after scan i of n".

**Found in the data (measured, 2026-11-19):** the NX school file has two
short scans, 4 (15 of 21 points) and 12 (4 of 41: the high-Qz GID level),
and scan 13 is marked "aborted after 21 points" with all 21 taken (a stop
at the last point, treated as complete). Without series lines,
`series.infer` finds reflectivity 3, reflectivity 6–9 with alignment
4, 5, 10, and GID 11–12 (partial). Tests: `tests/test_series.py`, one per
row of the proposal's table.

**Not checked:** the SPEC hook names (`Fheader`, `cleanup_once`) are from
reading about SPEC, not tried; the beamline should confirm.

### 2026-11-19 — Is the data we have from the Pilatus 200K?

**Q (owner).** "Didn't I provide [200K data]? Perhaps we are only saving
one panel of the detector pixel array. But the data I recently provided is
from the Pilatus 200K."

**A (measured on the files, 2026-11-19).** Every Pilatus frame received is
487 × 195 pixels: NX school (276 frames), bu June and September (595),
the private GID scans 136–146 (206); only the bu October 1M frames differ
(981 × 1043, header "PILATUS3 1M"). 487 × 195 is one module, the size of a
100K; a full 200K frame is 487 × 407, two modules with a 17-pixel gap
([DECTRIS PILATUS3 specifications](https://www.dectris.com/en/detectors/x-ray-detectors/pilatus3/)).
The TIFFs are written by EPICS areaDetector and do not name the model;
SPEC's counters are "Pilatus", "Pil300K" and "Pilatus1M". So the data are
very likely from the 200K, as the owner says, with **only one module saved**
(an areaDetector region of interest or file-plugin setting; not checked).
My TODO entry "200K sample data still needed" was wrong in that sense; what
the reader has never seen is a two-module frame.

**Why it may matter.** In the reader's orientation the 195-pixel side is
horizontal (2θ, `NCOLS = 195`). If the second module lies along 2θ, saving
it would roughly double the in-plane range of each GID frame, which is what
the pinhole method uses (more columns, F45); along β it would extend the
vertical range instead. Either way, the reader's detector description
(`TwoDDetector`, Stage 4, F17–F19) needs the 17-pixel gap and a mask before
it can read such frames. Question for the owner: which way is the 200K
mounted, and is the one-module saving deliberate?

### 2026-11-19 — Is the pinhole trig exact? The 200K's second module

**Owner.** The 200K is mounted so that the other module would extend 2θ.
Saving one module is deliberate (no switching between GID and
reflectivity, which needs one module; GID patching did not use the
pinhole geometry fully until now). "The geometry needs to be more exact
the further we go away from the pdx, pdy positions. Is your trig up to
snuff?" Sent Mati Meron's IMG_COO_CONV, LIMG_COO_CONV, SCAN_JOIN and
SPEC_FILE_INFO (published, attributed, `docs/reference_code/idl/`).

**A. It was not.** The reader gave each column a 2θ, atan((c − c0)p/D_p),
and each row a β, atan((r − r0)p/D_v): exact on the direct-beam column at
any β0, and on the direct-beam row only with the arm level (β0 = 0; at
β0 = 6.5° that row is off by up to 1.02° in β, review 2026-11-19). IMG_COO_CONV's transform is exact for a flat detector
perpendicular to the arm with a vertical slit (S4) D_p in front of it;
ported as `pinhole.pixel_angles` and checked against an independent ray
construction (beam-axis point → slit line → pixel) to 1e-12 rad at
Det_Th 3–25°, β0 0.09–12°, on this module and where a second module would
be (`test_pixel_angles_are_the_exact_ray_geometry`). The physics: each
column sees a different part of the footprint through the slit, at a
different distance from the detector, so **β depends on the column**; with
the arm raised, 2θ also depends on the row.

**Measured (NX school, 2026-11-19), per-axis minus exact:**
- inside each frame's usable columns (28–90 at Det_Th 14° … 28–102 at 18°): β up to 0.41° (scan 11, arm
  level) and 0.74° (scan 12, β0 = 6.5°); along the top row β spans 0.6° and
  1.1° across those columns; 2θ up to 0.0005° and 0.038° (one 0.036° bin);
- over a whole module: β 1.2° and 2.2°, 2θ 0.001° and 0.14°;
- where a second module would be: β 2–7°, 2θ up to 0.39°.
SPEC_FILE_INFO also confirms the reading of `#B1`: centre (53, 147),
distance 551, pinhole distance 271 (the smaller is the pinhole one), no
"H" so the 487 axis is vertical.

**Changed (deliberate; default GID maps):** the pinhole patch gives every
pixel its exact (2θ, β) and bins counts and weights on a (2θ, β) grid
(β step one row at the direct beam), keeping the β range every 2θ bin
shares. Before → after: NX 11, Bragg-peak 2θ centroid 16.6456 → 16.6473°,
472 rows → 460 β bins, rod half-maximum β 0.02–1.57 → 0.02–1.63°; NX 11+12,
level factor 1.029 ± 0.011 → 1.097 ± 0.013 and the join's χ²/dof on the β
overlap 1.31 → 0.83, i.e. the two levels agree better with exact angles
(one pair, scan 12 has 4 frames: supporting, not conclusive). A synthetic
line at fixed β now stays in one β bin; per row it fell on rows more than
10 apart across the columns used. The legacy 3-column patch is unchanged.

**Not yet exact (P38 remainder):** the cuts' pinhole axis, the image
display axes, and the distance fit still use per-axis angles.

**Second module (F63, measured):** its columns would be 212–406 (or
−212…−18) in this frame's numbering; per-axis angles there are off by up to
7° in β, so the exact transform is a precondition. How many of its columns
the footprint and S5 windows let through is to be checked with a full frame.

### 2026-11-19 — Monc's own noise; a complete GID pair

**Owner.** "You don't need this Monc noise measurement, you have the
Student's t model that is good enough." (D44: the condition set on
2026-11-15, measure Monc's noise on a bright steady signal before choosing
a normalisation model, is lifted.) Open: whether the Budget's default
monitor model should be the Student t rather than the Gaussian 0.04 %
(D22) when the Budget becomes the default (Stage 5).

**Owner.** Suggest a complete low + high Qz GID pair from the SPEC file on
hand. **Suggested (read from the private GID SPEC file, 2026-11-19; scan
numbers only, no data):** a pair at the NX scans' geometry (both complete), and a set of four complete scans
(two Det_Th ranges at each Qz, overlapping by 0.4°) that exercises both the
2θ joins and the Qz join. Scan numbers given to the owner in the
conversation; the data stay private.

### 2026-11-19 — Fitting requirements; MCA Merge; S1T + S1T; per-point MCA files

**Owner, fitting (F22a, scoping later):** all fits need improving; the
Gaussian fitting is simple and breaks easily; burn-test dynamics fitting is
not robust and strange; GID burn tests should take the largest peak in the
image or cut by default, with an override to another Qxy section; a fit for
a planned sh-scan half-cut to characterise the beam (F43); for MCA series
(EXAFS), better than a window sum: fit the summed spectra for position and
width, then each spectrum with those fixed. Link sharing on `bu.zip` is off.

**Q. Explain the MCA "Merge" weighted mean (P7) simply.**
**A.** Merge combines MCA points closer together than a chosen resolution
(in Qz, frame or energy). For two points with values y1, y2 and errors σ1,
σ2 it takes (y1²/σ1² + y2²/σ2²)/(y1/σ1² + y2/σ2²). It looks odd, but for
counting data it is exactly "add up the counts, add up the monitor, divide":
with y = N/M (counts over monitor) and σ = √N/M, y²/σ² = N and y/σ² = M, so
the result is (N1 + N2)/(M1 + M2), with error √(N1 + N2)/(M1 + M2), as if the
two measurements were one longer measurement. The textbook weighted mean
Σ(y/σ²)/Σ(1/σ²) would come out low when counts are small (it trusts the
points that happened to count low, because their estimated σ is smaller):
in a three-point check with 7–30 counts it was 7 % low, while the Merge
formula equalled the pooled ratio to all digits (numerical check
2026-11-19; the algebra holds also with an absorber factor and when merging
pairwise in sequence, as the code does). Mati Meron's SCAN_JOIN merges
overlaps with the same weights, y/σ². So it looks intended and correct for
Poisson data; it would differ slightly with the Budget error model, whose
σ includes a monitor term. Owner to confirm.

**Q. Context to judge `S1T + S1T`.**
**A (measured on every file here, 2026-11-19).** `mainwindow.py` builds
the S1 vertical opening for the *legacy* (3-column) GID area correction as
`S1T + S1T` (top blade twice); the horizontal one is `S1L + S1R`, and the
pinhole patch and `PD_PIN_RANGE` use `S1T + S1B`. The vertical opening sets
the footprint length along the beam (S1v / sin α), which the footprint
correction (`calArea`) uses as a function of 2θ. In all 643 scans of the NX
school, bu and private GID files, S1T equals S1B (e.g. 0.0499653 and
0.0499653 on NX scan 11, a 0.1 mm gap), so the typo changes nothing in any
data here; it would matter only for an asymmetric S1 (e.g. the gap moved off
centre), where the footprint length would be 2·S1T instead of S1T + S1B.
Fixing it to `S1T + S1B` is therefore safe for all existing data (the
legacy GID references would not change).

**Q. What is a per-point MCA file?**
**A (read from the files).** Normally the fluorescence detector is read by
a `getandsave_mca` scan: one SPEC scan, one MCA spectrum, and the reader's
MCA tab handles those. In the October bu run, an ordinary motor scan
(`ascan …`, e.g. scan 15 of 20261019) also saved a spectrum at *every
point*, through a macro `mca_save_point`: the file `vortex/20261019_15_mca`
holds one spectrum per scan point and per channel of the 7-channel
Xspress3 detector (headers `#S 1 mca_save_point Point:0 Scan:15`). The
reader can parse the file, but the window offers MCA data only for
`getandsave_mca` scans, so these spectra cannot be reached from the
interface. They would matter for any scan where a spectrum per point is
wanted (e.g. an energy scan for EXAFS, or fluorescence along a motor
scan); that is the "series of MCA spectra" of F22a.

### 2026-11-19 — Merge kept; S1 fixed; per-point MCA files not reachable (checked in the window)

**Owner.** The MCA Merge stays as it is ("take care of the error
downstream"); its default Qz window should reflect the jitter in Qz and
work 99 % of the time; the owner will provide the number (no analysis
until then). Fix the S1 sum (S1 was usually symmetric). Per-point MCA files
should be handled; "are you sure we couldn't [load them]?"

**Checked in the window (2026-11-19, bu/2026oct/20261019 scan 15, private
data, locally):** opening the file and selecting scan 15 (`ascan oh …`, whose
spectra are in `vortex/20261019_15_mca`) gives an empty MCA list; the scan
is taken as a Pilatus scan (it has `#B0`) and the window says "2 of 2 frames
have no readable image". The reader marks a scan as having MCA data only for
the command `getandsave_mca` or a `#V` line, and scans 11–15 have neither.
In the files on hand, the XFNTR scans that work (bu June 1–12, September
74–79) are `getandsave_mca` scans with a `#V vortex data:…` line.

**The per-point file (read):** for each scan point, one `#S k
mca_save_point Point:p Scan:s` block per detector channel (7, Xspress3
`XSP3_7Chan`), each with `#Monc` (two numbers), `#Q`, `#Energy`,
`#@CALIB`, `#@CTIME`, `#@CHANNEL k` and `#@DCT` (e.g. "60 0 1 Enable").

**Fixed:** S1 vertical opening = S1T + S1B in the legacy GID footprint
correction (window and `Experiment.gid_frames`); no change for any file on
hand.

### 2026-11-19 — Figures of the pinhole trig: what the review found

Six isometric figures were made by one subagent and reviewed by another
(`docs/figures/pinhole/`, `tests/tools/pinhole_figures.py`; every point and
angle from `lss_core.pinhole`, with a new `ray_geometry` as the independent
ray construction). Measured in the review, beyond the figures:
- **Per-axis angles on the direct-beam row are exact only with the arm
  level**: at β0 = 6.5° that row is off by 1.02° in β over the module (0.34°
  inside the usable columns) and 0.045° in 2θ; the direct-beam column is
  exact at any β0. Wording in the notes above and P38 corrected.
- **The footprint window is centred on c0, the true one is not** (P39):
  shifted +4.8 to +6.0 columns at Det_Th 14–18°; the high edge drops ~8 % of
  the usable columns (counts, not bias). Faithful to IDL's PD_PIN_RANGE.
- **The 200K's second module would see no footprint** with these slits
  (F63): its columns look through S4 at beam-axis points far outside the
  ±32 mm footprint, and S5 shades both possible positions. Using it for GID
  needs the slits set for it.
- The "β up to 0.41° / 0.74°" figures above are maxima over each frame's
  own usable columns (reproduced exactly: 0.406°, 0.736°).
- The refactor around `ray_geometry` changes no number: `pixel_angles`,
  `footprint_window`, `usable_columns` bit-identical to before over 24 000
  geometries.

### 2026-11-19 — The owner's rule for merging XFNTR scans (F65)

**Owner.** A seven-step rule (recorded in full as F65): group by run,
wavelength, sample and signal shape (peaked vs monotonic, never mixed);
match points on target Qz within 0.1 × the grid step, without
interpolation; find each scan's edge at the steepest rise of
ln(Vortex/Monc) refined by a parabola (repeats differ by a robust sd of
2.8e-5 1/Å); merge without asking when every edge is within 1e-4 1/Å of the
group median, else leave the outlier out and flag it; add the Qz jitter,
σ(I)/I = |d ln I/dQz| × 3e-5 1/Å, to the error bars; optionally align on the
edges; never merge across runs (the edge shift between runs is their
critical angle). The jitter figures come from monotonic scans; only 6
peaked scans were available, so the thresholds are untested for peaked
groups. This also answers the earlier question of the merge window's
default: 0.1 × the grid step.

**Owner, same day:** the edge estimator (steps 3, 4, 6) goes to the backlog.

**Checked (2026-11-19):** no real XFNTR qz scan is on hand to try it on;
the `Vortex` counter column in the NX school and private GID files has the
same maximum (29254) everywhere, i.e. it is not connected in those runs.

### 2026-11-19 — Timestamps: old Epoch files and new Tstart/Tend files

**Owner's guidance** (checked by the owner on the old files first: Epoch's
starting point is wrong, its steps within a scan are fine; of 189,439
point-to-point steps in c51_surface none goes backwards and none is shorter
than the count time):

| File | Absolute time of a point | Time since the macro started |
|---|---|---|
| New: #L has Tstart Tend, no Epoch | Tstart (counting began), Tend (point written), Unix s to 0.01 s; overhead = Tend − Tstart − Seconds | Tstart − SeriesT0, from `#U SeriesT0`, taken before any motor moves |
| Old: #L has Epoch | never #E + Epoch (more than an hour off in 4,458 of 8,043 scans); the scan's #D (1 s) as anchor plus Epoch differences within the scan: about 1 s, plus an unknown lag before the first point (sleep, count, readout) | not recorded; best guess the #D of the first scan of the inferred series, which misses the slit, absorber and umk moves before it; new files will show how long those take |

The two formats are told apart by the #L line alone.

**Built:** `lss_core/timing.py` (format from #L; `point_times`; #D's zone from
the file header's #E/#D pair, since #D has none), the SPEC reader keeps each
scan's #D, the file header above it and `#U SeriesT0`, and
`Experiment.point_times` adds the inferred series for old files. Missing
columns or zones are noted, never an error; the window opens both formats
without a message (`tests/test_timing.py`).

**Measured (2026-11-19, every SPEC file on hand: NX school, bu, private
GID):** 18,544 point-to-point steps from #D + Epoch; none goes backwards and
none is shorter than the count time (1 s resolution), as on the owner's
c51_surface. Every file's #E/#D pair gives a zone (UTC−5 on NX). Scans with
neither Epoch nor Tstart/Tend are the `getandsave_mca` scans.

**Found while testing:** `np.allclose`'s default relative tolerance (1e-5)
allows ±18,000 s on Unix times; time comparisons in tests use rtol = 0.

### 2026-11-19 — XFNTR merging without the edge check

**Owner.** Build the XFNTR merge rule without the edge check ("too fancy for
now"); the reader doesn't need to know runs or samples, the user chooses
scans to merge wisely.

**Built:** the MCA Merge moved to `lss_core.fluorescence.merge_rows`, its
arithmetic unchanged (byte-identical to the window's, tested against a copy
of the old code); default window 0.1 × the Qz grid step (step 2); on the Qz
axis the jitter is added to the errors (step 5), σ_j = I·|d ln I/dQz|·3e-5
1/Å, propagated through the merge weights (√Σw²/Σw: 1/√n for n equal
repeats), d ln I/dQz from the merged curve. Scriptable (`flu.merge`); the
Script pane records each Merge after a Sum All.

**Found while testing:** the grid step cannot be the median spacing of the
distinct Qz values when repeats are jittered (most spacings are then the
~3e-5 gaps between repeats): it is the median of the spacings above a fifth
of their 90th percentile. And because Merge compares each point with the
first point of its group (not with a target), two repeats 2.4 σ apart in
jitter (> 1e-4) are left as separate points; rare, and harmless (the user
sees two points at one Qz).

### 2026-11-19 — Real XFNTR and GID data from the owner (private; numbers in the conversation only)

**Received:** frames of the private GID scans 163–165 and 386–389 (EPICS
timestamp tags 65000/65002/65003 zeroed, pixels verified unchanged, renamed
as the earlier private frames); an XFNTR set (SPEC file, six per-point MCA
files, the macro `fluo.mac`), dates scrubbed (#E 0, #D and dated #C lines
removed, the date in file names replaced by "xfntr"). All in
`sample_data/private/` (git-ignored).

**Learned about XFNTR (read and run, 2026-11-19):**
- The usual XFNTR scan is the macro `fluo_p time abs`: S1 set, the
  detector arm moved out of the way, then `MCAscanpt lscan 0.015 0.03 15
  time`, i.e. an `hklscan` in Qz across the critical angle with one MCA
  spectrum per point. The SPEC scan has a `#V vortex data:…` line, so the
  reader already treats it as an MCA scan (this is why XFNTR "worked"; the
  October `ascan` per-point files have no `#V`).
- Each MCA file holds one spectrum per scan point (`#S k mca_save_point
  Point:p Scan:n`), each with its own `#Monc`, `#Q`, `#@CTIME`, `#@CALIB`;
  here a single-channel Dante.
- The spectra are dominated by the elastic line at the beam energy; the
  fluorescence lines are much weaker. The SPEC `Vortex` counter follows the
  total, not a line: Vortex/Monc can have a different shape from the line's
  window sum (seen: monotonic where the line is peaked). The owner's edge
  rule (F65 step 3, backlog) names ln(Vortex/Monc); which signal it should
  use is a question for the owner.
- Repeats of one scan need not be stationary: in one group the line's
  amplitude per monitor changed from repeat to repeat by tens of per cent.
  Merging such repeats averages different states; the user's choice (F65).
- The default Merge window (0.1 × the Qz grid step) grouped every repeat of
  each target and nothing else; the Qz jitter term raised errors by a few
  per cent at most, at the edge only.

**GID (private scans 163 + 165, 386–389):** compared with
`tests/tools/compare_methods.py --spec … --gid "163,165;386,387,388,389"`
into a folder outside the repository; results in the conversation only.

### 2026-11-19 — Time on any plot; merging allowed; fluorescence is fitted lines; EXAFS macros

**Owner.** Offer time as an x axis on any plot, as accurate as is known (old
data: the overhead is an uncertainty to live with, probably under a second;
new data simple). Let users merge what they choose (D45). The SPEC `Vortex`
counter is probably meaningless; what counts are element fluorescence lines,
fitted with a Gaussian on a linear, quadratic or cubic background for the
Rayleigh spill-over, normalised by Monc (D47). Sent an EXAFS macro file (kept
privately in `sample_data/private/macros/`).

**Built:** the SPEC plot offers `Time_s` (seconds since the first point of
the file's first scan with times; tooltip says how they were obtained).
Scans without Epoch or Tstart now get #D + the count times before each
point; files with dates removed use Epoch's own clock, so scans still line
up within a SPEC session.

**Learned from the EXAFS macros (read):** EXAFS at ChemMatCARS is an energy
scan with a spectrum per point: the `<element>_exafs` macros call `MCAscanpt
escan_14 edge e_before e_after …` around an absorption edge, with a k-space
part (`KtoE`); `*_edge` macros scan ±δE
around the edge. So the per-point MCA files are the EXAFS data format, and
one spectrum per energy point is fitted for the element's line (D47); the
energy axis comes from the scan, not from Qz. `eb_expose time abs` exposes
the sample at Qz 0.018 with the absorbers open for a set time (a deliberate
dose, e.g. before or between measurements), then closes them and returns.

### 2026-11-19 — Time axes, dead time, the 7-element detector

**Owner.** Show a true timeline when several scans are selected, and keep
the option of comparing scans as if they started together (D50). The
7-element detector corrects its own dead time; the 1-element detector, with
other electronics, needs the correction in the reader: "there is an
equation in reader for that, correct?" (D48). The 7-element detector needs
a configuration panel with a global element selector; EXAFS sums all seven,
XFNTR uses the central element (D49).

**A (read from the code).** Yes: each spectrum is multiplied by real/live
time from the MCA file's `#@CTIME preset real live` line
(`fluorescence.normalise_spectrum`, as the original program); on the
1-element file sent today it is a correction of about a tenth of a per cent
(value in the conversation); the
7-element files write `#@CTIME 1 1 1`, so nothing is applied twice. The
second number on `#Monc` lines is read as Monb (then Mond), for hutches B
and D.

**Built:** the MCA reader reads `#@CHANNEL` and `Point:`; one spectrum per
point summing the selected elements (`combine_channels`); Preferences >
Fluorescence detector (elements 1–7, default all); `channels=` in scripts;
SPEC plot `Time_s` (seconds since the earliest selected point, the clock
time of that point in the tooltip) and `Time_from_start_s`.

**Answered later the same day (owner): the central element is 1** (the
"Centre" button selects it). Earlier text: which element number is the central one (the selector lets the
user choose; no preset); the October per-point files (`ascan` without `#V`)
are still not reachable from the window (F53).


### 2026-11-19 — What the finite S4 opening does (pinhole figure case 8)

**Owner.** "What effect is S4 having?" The geometry treats S4 as a line
(the pinhole), but S4 has an opening (S4L + S4R = 0.2 mm on NX).

**A (measured, NX scan 11, Det_Th 16°; `pinhole.column_acceptance`,
`s4_window`, `ray_geometry(slit_offset=…)`, checked against plain in-plane
trigonometry in `tests/test_pinhole.py`).**
- Each column accepts rays from anywhere across its pixel through anywhere
  in the gap: 2θ over 0.079° full width (2.16 columns; S4 alone 0.042°, the
  pixel 0.036°), a triangle-like spread since gap and pixel are about as
  wide. The bin step is one column (0.036°), so this, not the bin, is the
  pinhole map's 2θ resolution; neighbouring bins share resolution, not
  counts. Each column sees 2.1 mm of the 63.3 mm footprint (0.6 mm with S4
  as a line).
- The footprint window's edges become ramps: 100.8…103.3 at the high edge
  (±1.21 columns; ±1.09 at the low edge), against a one-pixel step at
  102.0 with S4 as a line. S5's edges move by only ±0.08 columns (S5 is
  32 mm from the detector, S4 271 mm).
- With the NX settings no usable column is in a ramp (the reader's window
  ends at 96.6, the low edge is S5's at 27.2), so the reduction is not
  affected. A corrected window (P39) should end at the inner edge of the
  ramp: column 102 is only 52 % lit.
- Counts per column are proportional to the opening (0.5× at 0.1 mm, 5×
  at 1 mm); the 2θ acceptance grows to 0.121° at 0.4 mm and 0.248° at
  1 mm, the edge ramps to ±2.4 and ±6 columns.
- The footprint weight A (`area_fraction`, the window's calArea) is the
  part of the footprint a column's band covers; it does not scale with
  the opening as the counts do (×0.37 at 0.02 mm and ×3.8 at 1 mm, where
  the counts are ×0.1 and ×5). With one S4 setting for all frames of a map
  the ratio is the same for every column (to 0.1 % over Det_Th 14–18°),
  so it cancels in the map; noted, not changed (reading and one
  calculation).

No existing result changes: `pixel_angles`, `footprint_window`,
`usable_columns`, `s5_window`, `ray_geometry` (offset 0) are bit-identical
over 3000 random geometries (compared before and after, 2026-11-19).

### 2026-11-19 — What a Gaussian beam does to the pinhole geometry

**Q (owner).** What effect does the roughly Gaussian beam intensity have on
the pinhole geometry? Vertical FWHM about 30 µm; horizontal Gaussian-like,
FWHM about 1 mm.

**A (computed, `tests/tools/pinhole_beam_profile.py`, NX scan 11, α =
0.0905°, S1v 0.10 mm, S4 0.2 mm).**
- The reader takes the footprint as uniform over S1v / sin α = 63.3 mm. A
  30 µm beam is well inside S1's 0.1 mm, so the light on the surface is a
  Gaussian along the beam of FWHM 30 µm / sin α = **19.0 mm**; S4's opening
  and the 1 mm horizontal width seen along each column's line of sight
  (σ_h / tan 2θ) widen it only to 19.3 mm. The horizontal width does not
  change any column's 2θ: every source on the line through S4 and the pixel
  gives the same in-plane angle; it only smears which points of the beam axis
  a column sees.
- Through S4 each column sees one stretch of the beam axis, so the light per
  column follows that Gaussian: half or more of the peak in columns 33–62
  (peak at the direct-beam column), while the reader treats 28–96 as evenly
  lit (its windows assume the uniform footprint).
- **The fitted column response is this beam profile.** On NX scan 11 the
  response fitted from the data is a Gaussian of FWHM 35.9 columns on a flat
  part of 41 % of its peak; the beam profile predicts 30.1 columns. Its centre
  is at column 54.7 against 47.4 predicted: 7 columns, about 4.5 mm along the
  beam, which a beam about 7 µm above the sample's centre height would give
  (4.5 mm × sin α); not checked. The flat part is not explained by the beam
  profile (a wider tail, or light scattered elsewhere).
- **Bias left in the map.** The fitted response is one factor per column for
  all frames, but a column looks at a different point of the beam axis at
  each Det_Th, so with a narrow beam its light changes from frame to frame.
  Synthetic frames lit by the Gaussian beam (expected counts, flat truth),
  patched with the fitted response: interior of the map (14.3–17.7°, 11–25
  frames per bin) 0.93–1.04 of the truth for a 30 µm beam, 0.97–1.03 for
  60 µm; edges of the map (bins seen by a few frames through dim columns)
  0.71–2.8 and 0.91–1.37. With a uniform footprint the same test gives 1.000.
- **Remedy (proposed, not built):** fit the response as a function of the
  source point on the beam axis (ray_geometry's source x, one profile shared
  by all frames: the beam's own profile), not of the column; or a Gaussian
  beam of fitted centre and width. Either keeps the map unbiased when the
  column-to-source mapping changes with Det_Th, and also gives the beam's
  position on the sample.

### 2026-11-19 — Beam response built; the upper-level difference is not geometry alone

**Owner.** Build the beam-axis response, as an option on what was already
built and demonstrated; show the 2θ resolution to the user; the central
element of the 7-element detector is 1. "I thought the GID upper-level
difference came down to having the correct geometry, but you're saying
even when you patch in legacy mode with a 1–3 pixel wide column selection
you still get some difference?"

**Built:** `GIDParams(response='beam')` (worksheet: response "beam"): the
pinhole response as one profile along the beam axis, the source point of
each column per frame from `ray_geometry`, shared by all frames of a level;
the map info gives the profile and the beam's centre and FWHM on the sample.
The 2θ resolution (S4 opening + pixel, `column_acceptance`) is in every
pinhole map's info and shown with the levels in the worksheet (0.079° on
NX, 2.2 one-column bins). Preferences: "Centre" selects element 1.

**Measured:** synthetic frames lit by a 30 µm beam (flat truth): per-column
response 0.93–1.04 of the truth inside, 0.71–2.8 at the edges; beam
response 0.98–1.02 and 0.88–1.04, and it recovers the beam (centre −0.1 mm,
FWHM 18.0 mm against 0 and 19.3). NX scan 11: the beam response puts the
lit strip's centre 5.2 mm downstream of the sample centre and its FWHM at
33 mm along the beam (i.e. about 52 µm vertically at α = 0.0905°, if it is
all beam profile), longer than the 19 mm a 30 µm beam would give.

**The owner's question (answered with measurements on the private pairs;
numbers in the conversation):** we had compared the legacy patch (3 columns,
β per row) with the full pinhole patch, not with a narrow pinhole patch. A
pinhole patch restricted to the three central columns, with exact angles,
reproduces the legacy patch's upper level on one pair (with the area weight
off in both, to within a fraction of a per cent); on the other pair it
differs, but the narrow patch has few counts there. Adding the outer columns
changes the upper level relative to the lower by about a tenth, on both
pairs, in opposite directions; switching off the area weight or the
polarisation, or using the beam response, does not remove it. So it is not
the β-per-row geometry alone: something in the outer columns' contribution
at the upper (raised-arm) level, not yet identified (TODO: maps from column
groups per level; the β-overlap cells of the join).

**Owner (same day):** 30 µm may not be right for these data: they are old,
and the focusing was not as good then. So the beam response's measured
profile (NX: 33 mm along the beam at α = 0.0905°, about 52 µm vertically)
is plausibly the beam of that time, and the beam response is the way to get
the beam size from GID data themselves rather than assuming it.

### 2026-11-19 — Outer-column diagnosis: illumination per level, and stray light at the raised arm

**Owner.** "Go ahead with the outer-column diagnosis" (why adding the outer
columns changes the upper GID level relative to the lower); then: "there
are slit-scattering effects that could be relevant for GID patching; they
might be more obvious in the individual frames on a log intensity scale.
Perhaps more example data is needed."

**Ruled out (measured on the private pairs; numbers in the conversation):**
the level ratio, fitted per column group, does not depend on β (flat across
the β overlap within a few per cent), nor on 2θ (flat across the 2θ range),
nor on a shift of the upper level's β by ±0.2°, nor on the arm term, the area
and polarisation weights, the response kind, or the scale of the pinhole's
β correction; the column → beam-axis mapping is the same at both levels to
under 1 mm. So it is neither the angles nor the weights.

**What it is, mostly (measured, private pairs):** the light per column, i.e.
the illumination along the beam axis, differs between the two levels' scans:
its centroid along the beam differs by a few mm between the levels, and the
upstream tail is stronger at the raised level. The level factor fitted on a
column group is the ratio of that group's mean illumination at the two
levels, so it depends on which columns are used. Each level's own response
('fit' or 'beam') corrects its map for its own illumination, so the joined
maps from different column groups agree much better than the factors do
(the upper-to-lower intensity ratio of the joined map varies by several per
cent between column groups, against tens of per cent for the factor). That
residual is not explained yet. The recorded sample height is the same for
both levels; a change of the liquid's height between scans (Δx = Δh / tan α,
0.64 mm along the beam per µm at α = 0.09°) or of the beam would move the
illumination this way, but this is a reasoning, not a measurement.

**Stray light (measured, public NX scans 11 + 12 and both private pairs;
`tests/tools/gid_stray_light.py`, `docs/figures/gid_stray_light/`):**
- Columns beyond the footprint but inside S5 (NX: 85–135) are lit at both
  levels, at a third (arm level) to more than the full (raised arm) of the
  usable columns' level per pixel. At the level arm they are lit even below
  the sample horizon, which light from the surface cannot do: beam-path
  scattering (gas, windows) or a footprint longer than S1v / sin α.
- At the raised arm (β0 = 6.5°) only, a wedge-shaped streak with sharp
  edges, rows ≈ 60–150 (β ≈ 6.5–8°), from about column 90 to the detector's
  edge, crossing S5's high edge: light that does not come through S5 from
  the footprint (slit scattering or a grazing reflection off a blade, by its
  shape). NX: beyond S5 at β 6.2–7.6°, 1.5 × 10⁻⁷ counts per pixel per
  monitor count at the raised arm against 1.4 × 10⁻⁹ at the level arm. It
  lies in the β range where the levels are joined, but outside the usable
  columns in these data (NX usable ends at 91); the P39 window correction
  (end at the S4 ramp's inner edge, ≈ 101 at Det_Th 16°) would take in
  columns it reaches. Recorded as P40. **Owner (same day): "that streak is
  junk"**, i.e. not sample signal; the reader should keep it out of maps.

**Data that would decide it (asked of the owner):** GID frames with little
signal (mostly background), at both arm heights with the same slits;
frames with the sample lowered out of the beam (beam-path scattering);
frames at the raised arm with S5 closed or nearly closed (what bypasses
S5); the S4 and S5 vertical openings and the flight path between S5 and
the detector; levels measured interleaved or the lower level repeated after
the upper (illumination drift between scans).

### 2026-11-19 — What P39 is; would a half-cut beam profile help GID? What makes a column usable?

(Recorded after a documentation audit; the answers were given in the
conversation, the half-cut part is answered here.)

**Q (owner).** "I don't know what P39 is." **A.** The reader decides which
columns can see the lit strip of sample (the footprint) through the S4
pinhole as a range centred on the direct-beam column, as Mati Meron's
PD_PIN_RANGE does. Traced exactly (rays from the footprint's ends through
S4), the range has the same width but sits about 5 columns higher (NX scan
11). So a few columns that do see sample are dropped at the high end: fewer
counts, no bias. Correcting it would depart from IDL on purpose; and P40(b)
(the raised-arm streak, "junk" per the owner) reaches those columns, so the
correction waits for the background data (TODO inputs 15, 17).

**Q (owner).** "In the future we can measure the beam with a half-cut to
inform this correction for beam vertical profile. Does that help to better
normalise and patch?" **A (reasoning, with the measurements of the
2026-11-19 outer-column diagnosis).** Partly. A measured vertical profile
gives the footprint's illumination along the beam (profile stretched by
1/sin α), which (1) checks the profile the 'beam' response fits from the GID
data (NX: about 52 µm implied), (2) sets where the footprint really ends,
which is what P39 is about, and (3) gives the ramps at the window's edges.
It does not replace fitting per level: on the private pairs the
illumination differed between the levels' scans (centroid a few mm along
the beam), which a profile measured once cannot follow; a half-cut taken
next to each GID level would. (Recorded under F43.) Two limits: the
profile is stretched by 1/sin α, so α must be known well (at α = 0.09° an
error of 0.005° changes the footprint's length by about 6 %); and a
half-cut says nothing about the stray light of P40, which needs its own
data. (Owner asked again 2026-11-19; same answer given in the conversation.)

**Q (owner, figure 7).** "I don't know what makes [the columns] usable, the
slit size or the footprint." **A (measured, NX 11, Det_Th 16°).** Both: a
column is usable when it is inside S5's window and sees the footprint
through S4. On NX, S5 sets the low edge (27.2) and the footprint the high
edge (102.0 traced exactly; 96.6 as the reader computes it, P39): usable
28–96. (Figure 7 and its README.) A study of a larger detector is later,
not now (owner, 2026-11-19; F63).

**Owner (2026-11-17, recorded late):** `getandsave_mca` is a test macro, not
the normal XFNTR scan; the normal one is `fluo_p` (an MCAscanpt hklscan in
Qz with a `#V` line). The beamline items about `getandsave_mca` (no `#A`, no
gain) matter only for it; whether `fluo_p` scans write `#A` and the gain is
to be checked on the next new file.

**Owner (2026-11-19): private data policy.** "I don't mind a few private
numbers leaking out, provided no peak locations and raw data/images are
public." Written into AGENTS.md.

### 2026-11-19 — P39 fix: the exact footprint window (plan, written before the code)

**Owner.** "Go ahead with the P39 fix, documentation first."

**What changes.** In pinhole GID maps, a frame's usable columns are S5's
window intersected with the footprint window. The footprint window was IDL's
PD_PIN_RANGE: the right width, centred on the direct-beam column c0. It
becomes the exact one: the columns whose rays, through every point of the S4
opening, start on the footprint (the inner edges of `pinhole.s4_window`; S4
opening from S4L + S4R, split equally about the line the reader uses).

**Why fully lit only.** Between the inner and outer edges a column sees the
footprint through part of the opening (a ramp, ±1.1–1.2 columns on NX). That
fraction depends on Det_Th, so it differs from frame to frame for the same
column, and the column response (one factor per column) cannot absorb it.

**Measured before writing the code (NX 11 + 12):** the inner window is the
same on rows 15, 53, 250 and 486 at both arm heights (β0 0.09° and 6.5°), so
it is computed once per frame on the direct-beam row (about 10 ms). The high
edge moves from IDL's 90.6 / 96.6 / 102.6 to 94.2 / 100.8 / 107.4 at Det_Th
14 / 16 / 18°; the low edge is S5's (27.2) in all NX frames, so it does not
move there.

**Kept as an option:** `GIDParams(footprint='idl')` and the worksheet's
"Footprint window" list, to reproduce earlier maps and IDL.

**To check when built:** the before/after maps (counts, Bragg peak position
and width on NX 11, the level join on 11 + 12), and whether the raised-arm
streak (P40b, junk per the owner) reaches the added columns; if it does,
those pixels need masking rather than a narrower window.

### 2026-11-19 — P39 fix built; the beam profile figure; sample height drifts

**Built (D51):** `usable_columns(..., s4_mm, footprint='exact')`, the
default; `GIDParams.footprint`; the worksheet's "Footprint window" (exact /
IDL); `pinhole.frame_columns` for a frame's own S4 opening. Where no column
sees an end of the footprint (pinhole close to the sample) that side has no
limit (a synthetic case in the tests raised there). **Measured (NX):** see
OUTPUT_DECISIONS, "Pinhole footprint window IDL → exact": +3.3 % counts on
scan 11, the Bragg peak unmoved (0.0005°), the 11 + 12 join 1.097 → 1.068 ±
0.013; `footprint='idl'` reproduces the old maps bit for bit.

**The streak (P40b) reaches the added columns at the raised arm** (NX: rows
60–150 of those columns 2.4× rows 200–400, against 1.5× in the old edge
columns and 1.03× at the level arm; the private pairs the same way). The
owner was asked how to handle it and did not choose; the conservative
option was taken: on raised-arm frames (β0 > 1°) the high edge stays at
IDL's until the streak can be masked with the background data (TODO input
17). The join moved by about 2σ; that is the per-column illumination of the
outer-column diagnosis (the lower level gains columns that see the
footprint's downstream end, the raised one does not), not an error of the
map.

**Owner:** "Illustrate [the 52 µm] with a figure." `docs/figures/pinhole_beam/
beam_response_11.png` (`tests/tools/pinhole_beam_figure.py`). New in it
(measured): downstream of the beam the profile levels off at 0.6 of its
mean rather than falling to zero, light not from the beam (P40a); above that
floor the width is 23 mm along the beam, 36 µm of beam height, against 52 µm
at half the maximum. Both are upper bounds (S4 opening, horizontal width).

**Owner:** "A change of sample height by several microns is likely in an
hour, or even in a half hour. So the sample height scan is more critical
now." At α = 0.09° that moves the footprint by 0.64 mm per µm along the
beam, i.e. several mm per half hour: consistent with the illumination
difference between the levels found in the outer-column diagnosis. Added
to the beamline to-do: a height (sh) scan, or a half-cut, next to each GID
level, recorded in the file so the reader can use it.

### 2026-11-20 — The raised-arm question, explained; stale figures

**Owner.** "Please regenerate figures when they become stale. There was a
question about raised arm columns and patching and I never saw it. Please
explain in two paragraphs that situation." The question (asked during the
P39 fix) had arrived without an answer; the conservative option had been
taken (raised-arm frames keep IDL's high edge). Explained in the
conversation; regenerating stale figures is now AGENTS.md rule 11.

### 2026-11-20 — GID patching options written up (manual addendum)

**Owner.** "Commit a writeup about all the possible GID patching options and
their advantages and disadvantages. Consider it part of the written manual
but a technical addendum. A few clearly labelled 2D diagrams will help
tremendously to disambiguate the various column, row, edge, overlap
terminology." **Done:** `docs/manual/gid_patching.md` (terms, the pipeline,
legacy vs pinhole, every option with advantages and disadvantages, choices,
limitations), diagrams by a subagent (`tests/tools/gid_patching_diagrams.py`
→ `docs/manual/figures/gid_patching/`). Numbers quoted are the measured NX
ones already recorded (C10, C21–C24, OUTPUT_DECISIONS). **Found while
writing (read only):** P41, the pinhole scan join fits every scan against
the level's first scan, so scans that overlap only in a chain leave a factor
undefined; and the polarisation factor is 5–12 % over a typical map (2θ
13–20°), not negligible.

### 2026-11-20 — Joining across 2θ: more on it, and P42

**Owner.** "Is the joining across Qxy/detector theta so obvious that it
isn't illustrated? I want more on that." **Done:** section 3a of
`docs/manual/gid_patching.md` (within a scan: no factor, monitor
normalisation and ΣN/ΣW for the pinhole, profiles side by side for the
legacy; between scans: one fitted factor per scan, how each method fits
it), diagrams 7 and 8.

**Measured (NX scan 11 split into two scans, `tests/test_gid_scan_join.py`):**
with B's counts × 0.8 the factor A/B must change by 1.25. Legacy: 1.250
exactly. Pinhole with the default response 'fit': 1.173; 'beam' the same;
'none' 1.240. Halves of one scan join at 0.963 ± 0.003 (χ²/dof 6.9) with
'fit'. So the pinhole scan join is biased by the column response, which is
fitted before the scans are joined (P42, new). NX's own levels have one
scan each, so NX maps are not affected; the owner's levels of two Det_Th
ranges are. Remedy proposed, not built: fit scan factors and response
together, then measure again.

### 2026-11-20 — An honest presentation: less arbitrary scaling in GID patches

**Owner.** "I'm not quite sure what you're fighting against here on this
patch in 2θ. Isn't there an honest way to present the data that is more
true to the data as collected? Less arbitrary scaling?"

**A (reasoning, with the measurements below).** The data are already on one
scale before any patching: counts per monitor count, times the absorber
factor. Two things are added on top, and both are fitted from the sample's
own data: (1) the column response, an empirical flat field normalised to
mean 1 per level, which also discards each level's absolute scale; (2) free
join factors per scan and per level, which force the overlaps to agree. The
legacy patch needs a scan factor partly because it multiplies each scan
back by its own mean monitor (the 1.006 of C25); a monitor-normalised map
of scans taken at the same settings should need none. An "as collected"
presentation would use weights of monitor × absorber factor × the known
geometry only (polarisation, the slits' acceptance), average overlapping
measurements as ΣN/ΣW (counts-weighted, as for repeated measurements), and
report each overlap's ratio and χ² as a consistency check instead of
removing it; fitted factors and a fitted response would remain options,
labelled as corrections. Proposed, not built.

**Measured (NX 11 + 12, same absorber setting 12, same S1, S4, S5, same
Monc gain, mean Monc 2.21 × 10⁶ in both, α 0.0905 / 0.0903°):** with no
column response, the two levels agree in shape over their β overlap
(χ²/dof 0.84) but the upper level reads lower by a factor 1.217 ± 0.014
(exact window; 1.224 IDL's) at the same (2θ, β). With the response 'beam'
the fitted factor is 1.139, with 'fit' 1.068: the empirical response hides
part of that difference. Within one scan, frames scatter about a cell's
value with an rms of 0.43 without a response (figure 7): the column-to-
column differences in light are real (the footprint is not uniformly lit),
so the honest correction for them is a physical one, the beam profile along
the footprint (measured by a half-cut, or the one-profile 'beam' fit) and
the slits' geometric acceptance, rather than a free factor per column. The
cause of the 22 % between levels taken at identical settings is not known
(illumination change between the scans, sample height drift, raised-arm
vignetting are candidates; P40 data and half-cuts would decide it).

### 2026-11-20 — Physical column response built; all private GID scans used

**Owner.** "What is column response? Is this explained in the manual so
far" (answered: manual addendum 3b, written then) and "Go ahead with
physical model for this". Then: "Are you using all the available data or
did you lose track of the larger gid dataset?"

**Built:** `GIDParams(response='physical')` (`pinhole.PhysicalResponse`,
`source_x`, `BeamModel`, `fit_beam`): the response from rays through each
column's pixel and the S4 opening and a Gaussian beam clipped by S1, beam
centre and vertical FWHM fitted per level (each scan's scale a nuisance
parameter) unless typed; absolute scale kept; replaces the area correction.
`GIDParams(apply_joins=False)`: factors fitted and reported, not applied.
Worksheet controls with tooltips. Tests: `test_pinhole.py` (vectorised rays
= ray_geometry; synthetic beam recovered; absolute scale; uniform beam R = 1
and edge ramps; scan scale recovered; joins not applied),
`test_gid_scan_join.py` (NX split: 1.2549 for 1.25), `test_gid_worksheet.py`.
Measurements: addendum 3b and COMPARISONS C26.

**The data (answer to the second question):** the private GID file has
frames for nine Det_Th scans: 137 and 139 (12–22°, low Qz, the same range
twice), 163 (14–18°), 164 (15.5–17.5°, a partial repeat), 165 (Qz 0.582),
386–389 (two Det_Th ranges at two Qz). Until now 163 + 165 and 386–389 were
used; 137, 139 and 164, the repeats that test the 2θ join, were not (137 and
139 once, for C10). The `bu` files have Pilatus frames only for alignment and
reflectivity scans. With all of them (measured; private numbers in the
conversation): the same range measured twice differs by 5 % under every
response (a real change between the measurements, which no column
correction touches), and 163 + 164 + 165 as collected put the two levels on
one scale to 0.3 % while the fitted responses make the level factor 1.03–
1.06. So in that set the monitor normalisation alone already joins the
levels, and the fitted corrections add the disagreement; on NX the levels
are 22 % apart as collected. Both cases argue for showing the data as
collected, with the factors reported.

### 2026-11-21 — The best method as the default; P42 fixed; live worksheet

**Owner (2026-11-20).** "Users will want to see the effect of all these
different methods via check boxes and drop-down menus. If you have a best
method then make that the default."

**Built.** The worksheet re-patches on every change of a check box or
drop-down ("Update the map on every change", on; a 0.4 s pause collects a
burst of changes), and shows per level how well the frames agree with the
map (`pinhole.frame_consistency`, Poisson χ²/dof of rows-summed counts per
frame and column against the map; tested: 1.0 ± 0.15 for pure counting
noise). New response 'physical+fit'. P42 fixed for every response: each
scan's scale is estimated together with the response (`column_response`,
`beam_response`, `fit_beam` take the scans).

**Measured** (the table is in the manual addendum 3c and COMPARISONS C27):
'fit' has the lowest or near-lowest frames-agree χ²/dof on all five data
sets (NX 11, NX 11 + 12, the owner's 137 + 139, 163 + 164 + 165, 386–389);
'physical+fit' is lower on three of them but much higher on 386–389 (low
Det_Th, where one Gaussian beam per level with a 1 mm horizontal width does
not describe the light); 'physical' 5–7; 'none' 16–51. Every response now
recovers the NX split's scale 1.25 to 0.5 %. **Decision:** 'fit' stays the
default, joins applied. Single-scan levels are unchanged bit for bit; levels
of several scans change slightly (OUTPUT_DECISIONS).

**Also measured:** the two halves of NX scan 11 join at 0.95–0.96 under
every column model, so they really differ (a change along the scan); the
old expected-failure test that they should join at 1 is now a
characterisation.

### 2026-11-21 — Single frames as the ground truth for patching

**Owner.** "Had you considered a single frame with pinhole correction as the
ground truth for [what] patching the scans should give back? I mean instead
of a legacy mode patched image being ground truth, an unpatched image is
ground truth for peak location and width."

**A (measured; `tests/tools/single_frame_truth.py`, manual addendum 3d,
COMPARISONS C28).** Not as a reference until now: the C10 comparison used
the legacy map, and the distance fit used the drift of a feature across
frames (the same principle) but through the column response. As a
reference it works and says two things. (1) The single frames of NX scan 11
put the peak near 16.6° at one 2θ only if the S4–detector distance is about
265 mm, not the header's 271 mm (χ²/dof 5.5 and no drift at 265; drift
+0.015° per degree of Det_Th at 271); the owner's scan 163 says about 263 mm
(P43, new). (2) At that distance the patched map gives back the single
frames: centre 16.6490 ± 0.0038° against 16.6491 ± 0.0014°, FWHM within 2 %
(every pinhole response). At the header distance a patch is broadened when
the frames disagree (scan 163: +14 %, against +4 % at 263 mm); the legacy
patch is 21 % (NX) and 36 % (163) broader than single frames. Decision
waiting on the owner: calibrate the distance from single frames, or keep
the header value (TODO input 19).

### 2026-11-21 — Distance calibrated from single frames; survey for a final judgment

**Owner.** "Calibrate from single frames as you suggest. Commit your
comparison work such that another agent can pick up what you were doing
with a much larger dataset for a final judgment."

**Built.** `pinhole.calibrate_distance` (with `single_frame_peaks`,
`frames_agree`, `strongest_peak`, `rows_for_beta`): the strongest peak that
at least 5 single frames fit, the S4–detector distance scanned over 0.90–
1.06 × the header value, a parabola through the χ² minimum, the error where
the rescaled χ² rises by 1, and a reliability verdict with reasons. The
worksheet's Fit button runs it and fills in the distance when reliable.
Tests: synthetic frames drawn at 262 mm with a header of 271 give 262; a
flat spectrum is refused. The window's Fit used to be a response-based
diagnostic (shown, not applied): changed deliberately.

**Found on the way (measured):** fitting single frames on a fixed 2θ grid
aliases the columns: on synthetic frames with no noise, at the true
distance, the centres swung ±0.02° with a three-frame period. Fitting each
column at its own mean 2θ removes it; on NX the frames then agree to χ²/dof
1.42 at 265.7 ± 1.1 mm (it was 5.3 binned). Owner's 163: 262.0 ± 1.4 mm,
χ²/dof 6.7; 386 + 387: refused (no peak that single frames fit cleanly).

**For the final judgment:** `tests/tools/gid_method_survey.py` runs every
method, the calibration, the single-frame truth and the split test on any
number of GID sets and writes CSVs and a summary; hand-off
`docs/handoff_out/06-gid-method-comparison.md` says what to decide, how to
judge, the caveats and the privacy rule; the worked example on NX is
`docs/comparisons_data/gid_survey_nx/`.

### 2026-11-21 — A reusable peak module; fitting line cuts with one button

**Owner.** "You have become very good at fitting GID peaks, locating them,
etc. Build that into a module that can be reused, perhaps also with MCA
data. Make fitting any line cuts automatic with a button press, with
options available in a dialog box accessible from another button nearby."

**Built.** `lss_core/peaks.py`: `find_peaks` (significance over a running-
median background, in noise σ; width by walking to half height on the
smoothed excess), `fit` / `fit_all` (Gaussian, Lorentzian, pseudo-Voigt;
polynomial background none to cubic; overlapping peaks together; bounded;
an unweighted start, then weighted by σ; reports failure, edge and width
limits, and a misfit at χ²/dof > 10), `fit_lines` (known lines) and
`fit_series` (the owner's MCA rule: the sum for positions and widths, each
spectrum by linear least squares). Areas with the right Gaussian factor
(P20's √(2π)). The cut plot has "Fit peaks" (fits every plotted cut, draws
the fits, lists results in the Messages pane, writes `cut.fit(...)` to the
Script pane) and "Fit options..." (shape, background, number, maximum,
sensitivity, window, fixed FWHM, range, centres; "Fit now"; "Save
results..."). `pinhole.single_frame_peaks` now uses the module
(`scale_errors=True` keeps its weighting): the calibration's numbers are
unchanged (NX 265.8 ± 1.1 mm, χ²/dof 1.42; owner's 163 262.0 ± 1.4).

**Learned while building it (measured on synthetic data, tests):** a
peak's significance must be its height above the background in σ, not
scipy's prominence (pure Poisson noise of 200 points gave a "5.3σ" peak by
prominence); a first width from the raw half height is cut short by noise
(0.025 for a true 0.5), so it is taken from a smoothed excess; a weighted
Lorentzian fitted to a Gaussian with error bars that span three orders of
magnitude runs to a spike (FWHM 1 for 8) or does not converge, so an
unweighted fit comes first and a weighted misfit is flagged.

**Next (not done):** switch the MCA tab's fits (P20) and the SpecPlot fit
(P9) to the module, and the MCA series fit to `fit_series` (F22a).

### 2026-11-21 — F22 closed (but burn tests); fitting preferences; the per-SPEC workbook

**Owner.** "Close F22 if within reach. Save all the fitting preferences in
the config, that should be obvious. The fit results should also go there,
related to their scan. Perhaps the config file should actually be an Excel
file with sheets, such that results (reduced data and fits) are stored
inside it in an organized fashion, always tied to their scan number. Then
saving a reduced data vector is one click, with an optional notes dialog box
to allow for saving different versions of the same scans. Export will still
be a button ... Label each experiment type in the output and make easily
sortable in the Excel file. Keep a legacy export option as the default for
exporting ... Try and keep the number of sheets in this config Excel file
below 8, but at least 4. Set a subagent on a review ..."

**Built.** F22: SpecPlot fits the scan's shape (`peaks.fit_scan`: peak, edge
or plateau by AIC; P9 fixed: 0.406 → 0.471 for the test's Gaussian); the
half-cut edge (`peaks.fit_edge`, F43: edge width = beam FWHM, tested on a 52 µm
synthetic beam); the MCA tab's "Fit lines" (`peaks.fit_series`, F22a 6;
intensities = area / channel width, so in Sum All's units; tested: a spectrum
×2 gives ×2). Burn-test fits (F22a 3–4, P30) remain open. Fit options: the
preferences (`peak_fit`, `mca_fit`), read at start-up, written on every change,
and the workbook's Settings sheet. The workbook (`lss_core/workbook.py`, F66,
D53): `<SPEC file>_reader.xlsx` in the output folder, six sheets (Scans,
Saved, Data, Fits, Maps, Settings), each with kind, first scan and version
columns, a filter and frozen headers; Save beside every Export and "Save to
workbook" in the GID menu; a note by Shift-click or the preference; versions
counted per kind, scans and label; written atomically. Exports unchanged.

**Global preferences vs the workbook:** the preferences file holds what a
user wants everywhere (fit options among them); the workbook holds one SPEC
file's settings and results. Reopening a SPEC file with the workbook's
settings, and tying results to series ids, are the next steps (Stage 3).

**Review (subagent, `docs/reviews/2026-11-21-todo-review.md`, 1d065ad):**
about 30 doc lines that say "open" for done work, regrouping into eleven
areas, forgotten items, and a minimal series-metadata plan for the macros
(owner to read; the doc fixes are not yet applied).

### 2026-11-21 — Burn tests: trends over time, the 5 % time (F22a 3–4, P30)

**Q.** (owner) "What do you need to complete this? The user needs a
comparison of validity for average over time vs linear over time vs
exponential vs double exponential in terms of information criterion. When
an average (flat line) has the same confidence of fit as a linear fit then
we know we're in a good regime for avoiding beam damage. Another result is
a confident suggestion about how much time causes a less than 5 % change
in the quantity of merit. For GID burn testing make sure to show all 3
qualities at the same time, perhaps on 2 panels using 3 axes."
Then, during the work: "since we are more concerned with a relative change
in a GID burn test put less weight on absolute measurements of sigma etc.
The legacy GID burn test did well once the fit range was constrained, so
use that as inspiration."

**A. Nothing more was needed from the owner to build it**; two choices are
open for confirmation (below). Built (`lss_core/trends.py`,
`lss_core/burn.py`, `Experiment.burn`, the burn dialog's Trends tab):

- Four models per quantity, compared by AICc (Hurvich & Tsai 1989,
  https://doi.org/10.1093/biomet/76.2.297), with Akaike weights; QAICc when
  counting errors understate the scatter (Burnham & Anderson 2002,
  https://doi.org/10.1007/b97636, §6.2). **Stable** = AICc(constant) −
  AICc(linear) ≤ 2 (ibid. §2.6). When a curved model beats both, the
  verdict says so (e.g. an early fast change).
- **The 5 % time**: the first time the model's change since t = 0 reaches
  5 % (intensity, width: of their value; position: of the FWHM), given as
  the 5 % quantile over 2000 draws from the fit's covariance, i.e. "≥ T at
  95 % confidence", from the best model that beats the constant (else the
  linear one: a bound on a steady drift the data still allow). Tested for
  coverage: 5.5 % misses at a nominal 5 % (200 draws); a constant is
  called stable in 95 % of draws (I25).
- **Time**: from the start of the first exposure, at the middle of each
  frame; exposure (counting time accumulated, default) or clock (measured
  Tstart / Epoch steps). The legacy used count time × list row (P30).
- **Reflectivity**: the Ref Patch ROI per Monc. Synthetic τ = 400 s
  recovered to 1e-3, 5 % in 20.5 s = τ·ln(1/0.95) (I26).
- **GID**, all three quantities at once: intensity on top; position (left
  axis) and FWHM (right axis) below. Window: the strongest peak of the mean
  frame, 3 FWHM either side, inside the lit columns (NX 14: 1.400–1.534;
  the legacy test used 1.40–1.52), or a typed range. Errors: the frames'
  σ only as relative weights, scaled to the scatter (owner's second
  message). Estimator: **template** (default): the mean profile less the
  legacy straight background is the peak's shape, each frame fitted as
  that shape scaled, shifted and stretched, i.e. measured relative to the
  others; **moments** (the legacy arithmetic); **fit** (one Gaussian).

**Measured on NX scans 14 and 15** (public; same spot and geometry,
absorber 12 then 8, so scan 15 had ≈ 1.4247⁴ = 4.1 × the flux; run, C31):

| | scan 14 | scan 15 |
|---|---|---|
| Integrated intensity | stable (template and moments) | stable (both) |
| Position | +0.0024 Å⁻¹ in 210 s (changing) | +0.008 Å⁻¹ (changing) |
| FWHM | stable | +19 % (changing) |
| 95 % time to a 5 % change | position, ≈ 67 s | position, ≈ 11 s |

The position drifts ≈ 3.3 × faster at ≈ 4.1 × the flux, which points to a
dose effect rather than the sample height (a height drift would not scale
with the absorbers); not proven: the two scans also differ in time. The
broadening at a constant integrated intensity looks like disorder rather
than loss of material. Reading only: the absorber factor 1.4247 per foil
is the 10 keV default.

**Estimators compared** (C31): per-frame χ²/dof template 1.0 on scan 14
(4.3 on 15, where the shape changes), Gaussian fit 10–41 (it does not
describe a pinhole frame's sharp peak on its broad shoulder). Residual
position scatter: template 1.4e-4, moments 3.8e-4, fit 2.9e-4 Å⁻¹. On
synthetic profiles with a steady shoulder, the moments' centroid dilutes a
peak shift of 0.004 Å⁻¹ to 0.0023, so its 5 % time comes out too long; the
template recovers 0.0039. Intensity precision is about the same for template
and moments (2–3 % per frame). **Before the commit**, the template's
intensity ignored the stretch (area ∝ A·w) and read scan 15 as −15 %;
corrected, it agrees with the moments' "stable". Verified: run, tests.

**Open for the owner:** (1) does the shutter close between frames? If not,
the clock time is the dose time (3 % longer on NX); (2) is 5 % of the FWHM
the right scale for a position change? (3) a burn scan at higher flux or
on the private data would test the 5 % times where damage is clear.

**Also (owner's second reply on saving):** every Save now asks for an
optional note; Shift-click saves without asking (preference to turn the
question off; then Shift-click asks). Tested.

**Owner (same day):** "Put each GID burn fitted quantity on its own axes,
with the right hand axis of each panel being a normalized quantity, given
in percent. Put the summary results to the right of the panels, not in the
title." **Done** (`lss_core.burn.plot`, used by the dialog and
`tests/tools/burn_figures.py`): intensity and FWHM in % of the best
model's value at t = 0; the position as its shift from t = 0 in % of the
mean FWHM, the scale its 5 % change is judged on; dashed lines at ± the
threshold. Tested: `test_gui_burn_trends.py` (three panels, right-axis
labels, summary text beside, none in the title).

**Owner's answers (same day):** "Shutter does close between exposures by
default; wall time is better. Position change judgment is up to the user.
Most burn scans are an ih motor scan with no movement, that is the
standard for now, for inferring what type of data it is. Ask later for
more burn data, for now write the handoff for another agent to test and
extend what you just built."

**Done:** clock (wall) time is the default axis (a scan without per-point
times falls back to exposure and records which axis was used); the
position is still drawn with its %-of-FWHM axis but sets the limit only
when "Position in limit" is ticked (`Experiment.burn(limit=)`); an `ascan
ih` without movement (≥ 3 points) is inferred as a burn series
(`series.is_burn`; the NX file gains burn series 14 and 15). New NX
numbers (clock, template): scan 14 limit ≥ 190 s (intensity; position
alone ≥ 69 s); scan 15 ≥ 56 s (width; position alone ≥ 9.3 s). Hand-off
for testing and extension: `docs/handoff_out/07-burn-trends.md`. More burn
data: to ask the owner later (TODO). Verified: tests.

### 2026-11-21 — The to-do review applied; series inference fixed (R1)

**Owner:** "Record your suggestions as to-dos (add two sentences
description for each). Then let's move on to the review work."

**Done.** The ten burn-trend suggestions are to-dos with two-sentence
descriptions (TODO.md, Stage 2 list, under hand-off 07). From the review
(`docs/reviews/2026-11-21-todo-review.md`): section 1's corrections
applied to TODO, SCOPE, FEATURE_REQUESTS and PHYSICS_ISSUES (the stitching
bias reopened; P14, P15, P31 point to P36/P37; P16's factor part marked
fixed; the `fluo_p` `#A`/gain question answered); section 2's regrouping
is the new "Remaining work by area" at the top of TODO.md, with section 3's
forgotten items in it (marked **new**). Section 4, step R1, built:

- `series.infer`: consecutive hklscans with a `#V` line are an **xfntr**
  series (alignment scans between them attached), `escan`s an **energy**
  series, `ascan ih` without movement a **burn** series; plain hklscans
  stay reflectivity.
- `series.all_series`: series from `#U Series` lines plus guessed series
  for the scans without them (before, `group(info) or infer(info)` gave a
  file with any series line no guessed series at all); used by
  `Experiment.point_times` and the workbook's Scans sheet.
- `#U SeriesMacro` now reaches `Series.macro`.

**Measured** on the owner's XFNTR file (run; private, counts only): before,
all 153 `#V` hklscans fell into reflectivity series; after, they form 20
xfntr series, the 145 Pilatus hklscans 22 reflectivity series, and scans
19 and 20 two burn series. Effect on outputs: the workbook's Scans kinds
and, for old files, the "time since the series started" of these scans
(now from their own series' first #D). Verified: `test_series.py` (new
synthetic cases), the existing NX expectations.

### 2026-11-21 — Series in the scan list (review R2, D55)

**Owner:** "go ahead with series in the scan list", then, during the work:
"make selecting the entire series the default behavior, and have a
checkbox in the selector area to disable that function."

**Done.** A Series list above the scan list (each series with its kind,
scans done/planned, status and scans; tooltip: why, guessed or not, the
macro); choosing one selects its data scans in one selection signal. A
"Whole series" check box beside it, on by default (preference
`select_whole_series`): a click or key press in the list that adds a scan
of a series adds the rest of that series's data scans; Ctrl-click still
removes one; alignment scans are selected alone; selections by typed
numbers, scripts and tests are not widened (only the user's own mouse or
key presses in the list count). Scan rows: tooltip with series, position
and status; a faint tint by kind. No reduction changes; what a click
selects does. Verified: `test_gui_series.py` (NX file: series 6–9 chosen
gives one signal and scans 6–9; a real mouse click on scan 7 selects
6–9; Ctrl-click on 9 removes it; scan 10, alignment, alone; with the box
off, scan 7 alone; typed '8' stays 8).

### 2026-11-22 — Saved results tied to their series (review R3); the way to live updates

**Q.** (owner) "go ahead with tying workbook results to series. presumably
this is the gateway to live updating processed data as raw data comes
in?"

**A. Yes.** A live update needs three things: knowing that the raw data of
a result have changed, knowing how the result was made, and redoing it.
This step gives the first two. Each saved result now records its series
(id, kind, the series' data scans and status when it was saved) and,
where the reduction is scriptable, the lss_core call that remakes it
(`recipe`: reflectivity patch, cuts, GID map, fluorescence sum, burn test;
not yet the SpecPlot curves, fitted MCA intensities or GID cuts).
"Update Specfile" compares every result's series with the file as it is
now and marks it out of date when the series has gained scans, lost scans
or changed status (`Workbook.mark_stale`), with a message. A guessed
series is matched by id, else by the result's first scan. What remains
(TODO, area E, L1–L4): watch the file and update by itself; re-run each
stale result's recipe and save it as a new, automatic version; refresh the
open plot; stop at the series' end line or its planned n, which needs the
macros' series lines (input 1).

**Defect found on the way** (fixed, tested): "Update Specfile" re-reads
the last scan in case it grew, and appended its number again, so every
update warned that a scan appeared more than once and the series guess
split at the repeated scan (`ScanNums` [1, 2, 2, 3]; now [1, 2, 3]).
`series.scan_info` also takes each scan number once.

Verified: `test_workbook.py::test_results_tied_to_their_series_and_marked_stale`
(grown series, status change, renamed guessed series, vanished series),
`test_gui_workbook.py::test_a_saved_result_goes_stale_when_its_series_grows`
(a SPEC file grows by the next scan of the series; Update Specfile marks
the saved result and says so), `test_series.py::test_an_update_lists_each_scan_once`.

### 2026-11-22 — Automatic saving into the workbook (D56)

**Owner:** "Before you do those live update Ls, make saving in the excel
file automatic once a reduction/processing has been carried through."

**Done.** The methods that finish a reduction (Ref plot after a patch,
line cut, cut fit, GID map, GID cut, MCA sum, Fit lines, merge, burn
analysis) are wrapped once, before the signals are connected, so every
way of reaching them schedules a save; saves run when the event loop is
idle, one per kind. An automatic save asks nothing, is marked 'auto', is
skipped when a result with the same content digest is already stored,
and reports in the status bar and the log only (the Messages pane stays
for Save buttons and problems; existing tests that a reduction is silent
still hold). Preferences > Saving turns it off. SpecPlot curves (raw
data) are saved only by Save.

**Measured, and changed because of it:** with one NX GID map (807 × 66
cells) stored one row per cell, every later save took 6.4 s (opening 3.9
s) and the file was 2.7 MB. Maps are now grids (an 'x' row, then a value
and an error row per y): 1.1 s per later save, 1.3 MB, values unchanged
(round trip tested); a first-format Maps sheet is converted on opening.
The window also keeps the open workbook in memory between saves and reads
it again only when the file changed outside the reader.

Verified: `test_gui_workbook.py` (a cut saved without a question; the same
cut again not stored; a new range and its fit stored; Save still makes a
'user' version with a note; off in Preferences: no workbook; MCA Fit lines
saved), `test_workbook.py` (grid round trip, irregular maps, conversion of
the first format), `test_real_nx_school.py` (the NX map read back equals
the window's).

### 2026-11-22 — Live updates (L1–L4, D57)

**Owner:** "Okay, proceed" (with L1–L4 after automatic saving).

**Done.** **L1:** a "Live" box beside Update Specfile; while ticked the SPEC
file's size and time are checked every 5 s and a change runs the update.
The series are then guessed with the file taken as growing, so the last
one can be "in progress". **L2:** the stale check now also notices a scan
that gained points (Saved records `series_points`); in live mode every
newly stale result with a recipe is remade on the series' scans now and
saved as a new version (origin 'live', note "remade from R…: reason"),
the old row marked "superseded by R…" and then left alone; one remake per
recipe (a reflectivity's R and R/RF share one). Recipes are parsed, never
executed (`lss_core/live.py`): only `exp.reflectivity/fluorescence/gid/
burn` with literal arguments, `GIDParams`/`FitOptions` constructors,
`merge`, `save` and `print` are accepted; anything else leaves the result
stale with the reason. **L3:** a selection that was a whole series is
re-selected with the series' new scans; another selection is kept. **L4:**
live mode stops when the followed series is a lined one (the macro's
`#U Series`) and is complete, aborted or partial.

Not yet: the open Ref or GID plot is not redrawn from a remade result
(the window's reductions live in dialogs; R4); remakes run in the
window's thread; cuts, fitted MCA lines and SpecPlot curves have no
recipe; guessed series never end by themselves. Assumed (A): point
selections of the first version are dropped in remakes.

Verified: `test_live.py` (recipes rejected when they import, call or
assign anything else; scans rewritten; a burn remade on the grown scan;
stale by points; superseded rows left alone), `test_gui_live.py` (a burn
scan written 8 of 21 frames, analysed and saved automatically, grows
while Live is on: remade as a 'live' version with 21 frames, the old one
superseded, the selection kept; a lined two-scan series followed and
live mode stopped at its end).

### 2026-11-22 — Remakes in a worker thread; point selections kept; updates without a reset

**Owner:** "run the remakes in a worker thread. Point selection (what is
this exactly) sounds like it should be preserved across updates; updates
shouldn't feel like a reset or clunky."

**Q. What is a point selection?** **A.** The frames of a scan that a
result was made from, when they are not all of them: the user selects
some frames in the image list (leaving out a bad one, say) and the
reduction uses only those. The recipe records them as
`points={scan: [frames]}` (a burn test: `points=[frames]`). Until now a
remake dropped it and used every frame, which would quietly put a
left-out frame back.

**Done.** (1) The point selection is carried over
(`live.carry_points`): frames left out stay out; frames written since the
result was saved (from that scan's point count then, now recorded per
scan in Saved's `scan_points`) and new scans are added. (2) Remakes run in
a worker thread (one at a time, `concurrent.futures`; no Qt in it, a
fresh Experiment of the file); a 100 ms timer in the window stores the
finished ones (new 'live' versions, old ones superseded) and says so; a
result being remade is not queued again. (3) Updates no longer reset the
window: Update Specfile and live mode read only what the file gained
(no progress dialog, no clearing), add rows for new scans and update the
re-read one in place; when the scans being looked at changed, they are
redrawn with the tab, the SpecPlot axis choices and the image-list
selection put back (all frames selected: the new ones join); when the new
scans are elsewhere, nothing is redrawn (a status-bar line says what
arrived).

Verified: `test_live.py` (carry-over rules; a burn remade with frame 1
left out and frames 4–5 added), `test_gui_live.py` (frame 3 left out of a
burn test stays out after the scan grows 8 → 21: 20 frames, and the
recipe lists them; tab 1, the Monc y axis and frames 2, 5 kept after an
update; new scans elsewhere: no redraw).

### 2026-11-22 — The open display redrawn from remakes

**Owner:** "go ahead with redrawing the open plot from remakes if that's a
good approach."

**A. It is, for displays that only show a result**, which all four
remade kinds are: the window remembers which saved result each display
shows (every reduction is saved automatically, so the latest of its kind
is the one on screen), and when that result is remade the new numbers are
put into the window's state and the display redrawn, without saving it a
third time: the Reflectivity tab (the patched curve, then the window's own
normalisation, R/R_F and list), the MCA integral plot, the open burn
dialog, and the GID map (map arrays, levels, join information). The
alternative, re-running the window's own reduction, would block the window
and go through dialogs (the patch dialog asks at each join). A GID map on
screen now also stays on screen through an update (re-selecting the frames
had drawn the frames over it).

Verified: `test_gui_live.py`: the open burn dialog shows the remade 21
frames; a patched reflectivity of scans 1–2 becomes that of 1–3 when scan 3
arrives (Qz to 0.15, the series selection followed, the stored 'live' row
the same length); NX GID scan 11's map becomes the remade map of 11 + 12
(slow; equal to the stored map; narrower in 2θ, as two Qz levels share a
grid and scan 12 has 4 frames). The MCA redraw is not tested on a
fluorescence series yet (no synthetic XFNTR series with a recipe).

### 2026-11-22 — Live updates on every new image or spectrum

**Q.** (owner) "Does the updating proceed on each new Pilatus image or
vortex spectrum? Not just the scans that contain multiple images? It
should."

**A. Not fully, until this change.** Updates were triggered by the SPEC
file growing only. Each new point line did trigger one, in a scan of any
length, but (1) an image written after its SPEC line was not noticed until
the next SPEC line (the last frame of a scan could wait for the next
scan), and (2) a spectrum appended to an MCA file changes no SPEC line, so
it was not noticed at all. **Now** live mode also watches the Pilatus
folder (a new file changes the folder) and the MCA file of the latest
fluorescence scan (it grows by one block per spectrum), and every count
of a scan's points is the data on disk: images written (one listing of
the folder per update) or spectra in the MCA file (re-read only when its
size changes; distinct `Point:` values in a multi-element file), never
more than the SPEC lines. A frame listed before its image arrives is left
out of a re-applied "all frames" selection until it does. Verified:
`test_gui_live.py` (a burn scan with 21 SPEC lines and 8 images, saved at
8 points; the 13 images arrive with the SPEC file unchanged: the update
runs and the result is remade at 21; an MCA file of 1 spectrum rewritten
with 3: the update runs and the scan counts 3).

### 2026-11-22 — Documents brought up to date

**Owner:** "Update the accomplishments and other docs while the tests run."

There was no accomplishments document (TODO's "Done" list stopped at the
tests-and-scoping phase). Written: `docs/ACCOMPLISHMENTS.md`, a one-page
summary by stage and area with pointers and the counts (checked against
the files: 43 physics issues, 31 comparisons, 26 invariants, 549 quick,
581 slow and 67 sweep tests collected). Updated: the current-phase
paragraph and the file map in `AGENTS.md`; the stage table in `TODO.md`
(Stage 3 largely built) and its "Done" pointer; `SCOPE.md`'s status line;
`TESTING.md` (the 43 test files it did not list, by area, and the
load-sensitive timing test); `SCRIPTING.md` (series, stale results,
remakes, maps); `MANUAL_NOTES.md`'s sources; the README.

### 2026-11-22 — The three physics issues most in need of resolution

**Q.** (owner) "Remind of the top 3 physics issues that need resolution."

**A.** Chosen by size of the effect on outputs people use, and by whether
the way to resolve it is known (reading `PHYSICS_ISSUES.md`; the numbers
are the measured ones recorded there):

1. **P29, `Monc` does not always follow a slit change.** At joins where
   S1 (and S4) opened, the beam at the detector rose ×2.2–2.3 but
   `Monc/Monp` only ×1.55–1.62 in one configuration (measured, the owner's
   joins): anything normalised to `Monc` across a slit change without a
   patch is off by up to ×1.47 (direct-beam normalisation at other slits,
   fluorescence against reflectivity). Ref Patch hides it by fitting the
   factor. Mechanism unknown; needs the owner (which scan of a pair is off;
   input 9).
2. **Reflectivity uncertainties: P4 with P1 and P2.** The stitch-factor
   uncertainty is folded into per-point errors as if independent, so fits
   are overconfident (hand-off: a roughness pull with SD 5.3 instead of 1);
   stitch factors are 1.2–1.3 % low when overlap points do not coincide
   (synthetic; not yet measured on real overlaps; the "do not forget" of
   D13); and the default (legacy) errors understate the monitor term ×1.4
   to ×6.5 (fixed in the budget model, which is not yet the default). One
   remedy for all three: Stage 5, the two-file export with covariances
   (F24) and the budget model as the default.
3. **GID geometry defaults: P43 with P40 and P41.** At the header's
   S4–detector distance (271 mm) a Bragg peak's 2θ is off by up to
   ±0.02–0.05° by column and the patched peak is 14 % broader than in single
   frames (owner's scan 163); the calibration exists (265.7 ± 1.1 mm on NX)
   but is not automatic. Stray light near β0 (P40) and the scan join of
   chained scans (P41, remedy known) affect the same maps. Resolution: the
   method survey on the larger data set (hand-off 06), then defaults.

Verified: reading only (the issue table and the measurements it cites).

### 2026-11-22 — P41 fixed: the pinhole scan join against everything joined so far

**Owner:** "go ahead with the P41 fix and documented explanation."

**What was wrong.** Within one Qz level, the pinhole patch puts each
scan on a common scale with one factor, fitted on the 2θ bins it shares
with the reference. The reference was always the level's **first** scan.
Picture three scans along 2θ:

    A  |=====|
    B       |===========|
    C                  |=====|

B overlaps A and is joined. C overlaps B but not A; fitted against A it
shares no bin, and the code (taking the overlap's smallest 2θ) stopped the
whole patch with an error (measured: NX scan 11 split as A = frames 0–2,
B = 2–31, C = 31–40; a frame spans about 2.7° of 2θ through the pinhole,
so A and C must be about 3° apart in Det_Th not to overlap). With more
scans, a scan overlapping both A and B was fitted on A's overlap only,
throwing away the rest.

**The fix.** The reference grows: after a scan is joined, its rows-summed
profile, divided by its factor, is added to the reference. The next scan
joined is the one sharing the most bins with the reference, so the order
follows the overlaps, not the scan numbers; each factor is fitted on
everything it overlaps (the same weighted ratio, Poisson errors from the
summed counts, as before). This is what `join_levels` already does for
Qz levels (IDL's IMG_JOIN chain). A scan that overlaps nothing joined is
left unscaled, its factor NaN, and the join table says so.

**Measured** (`tests/test_gid_scan_join.py`): the chain now joins (B 0.966
± 0.006 on 67 bins; C 1.083 ± 0.005 on 77 bins); a ×0.8 put on C's counts
is recovered as 1.357 / 1.083 = 1.253 (the P42 fit couples the column
response to every scale, so B moves by 0.2 %). Levels of one or two scans
are unchanged, so every NX map is bit for bit as before; the other scan-
join tests pass unchanged.

**What it does not change.** The factor between two scans is still a
scale fitted on the overlap; a scan measured later can differ for real
(the halves of NX 11 differ by 5 %, sample height), and the fix does not
hide that.

### 2026-11-22 — Reflectivity patching: joint fit, prior, correlated error

**Owner:** "Then work on the reflectivity patching and error. Leave
decisions about export and saving in the to-dos. Employ a subagent to
think deeply on the patching method and whether there is a way to avoid
the correlated error by doing joint fitting on both scans in the ref patch
and using the prior knowledge. The curvature matching up across the patch
is one constraint. A quadratic or 4th order model should be adequate for
non fresnel normed data patches. In any case, make reusable code for
calculating uncertainty and prepare for later work by a third agent where
they compare methods with a larger dataset, like will be done with GID."

**A.** The subagent's report: `docs/reports/ref_patch_joint_fit.md`
(measured on synthetic slabs, NX 6–9 and the committed aggregates of the
owner's 1041 joins). In short:

- **Joint fit**: one polynomial for both scans in a window (the overlap
  plus points either side) with the factor as a parameter. A shared
  polynomial makes value, slope and curvature match everywhere in the
  window, which is the owner's curvature constraint in its strongest form
  (matching them only at one junction point is unbiased but 1.5× noisier).
- **Order**: on raw (non-Fresnel-normalised) data, a quadratic is adequate
  only on the overlap alone; with points either side it is biased up to
  +2.6 % / −5 % near Q_c, fringes and high Qz. Order 4 with 4 points
  either side is unbiased within 0.1 % (raw and R/R_F alike), and the
  factor's scatter is 20–30 % below the spline-ratio estimator. The P1
  bias disappears (no interpolation).
- **Prior**: the foils' ratio, with errors correlated between joins that
  share a foil, combined only where Monc/Monp is unchanged and the two agree
  (|z| ≤ 3); elsewhere marginalised (P29).
- **The correlated error cannot be avoided**, only made smaller and reported
  correctly: each scan's level is known through a finite overlap, so its
  error is one common shift of the whole scan and of every later scan.
  Reported as φ and Σ; with the full covariance a downstream slab fit's
  pulls return to 1 (SLD pull SD 3.4–4.8 → 1.07).

**Built** (2026-11-22): `lss_core/uncertainty.py` (method-free: chain
covariance, steps → φ, prior combination with marginalisation, per-point
total error, N × N covariance, pulls; meant for GID joins too) and
`lss_core/patching.py` (joint fit with a window guard, spline-ratio and
coinciding-point references, the correlated foil prior and its guard,
chain, global fit, stitched output). Verified: `tests/test_patching.py`
(16 tests; the NX factors 0.023004, 0.064516, 0.103604 and the last
scan's level 0.75 % reproduced; 1000-draw Monte Carlo pull SD 0.9–1.1 per
join). One finding on the way: a Monte Carlo of 200 draws gave a pull SD
of 0.80 at the first join, 1000 draws 0.99 (the pull SD of 200 draws
scatters by about 0.05; that set was unlucky), so the test uses 1000.
The legacy patch, its export and its tests are unchanged; the defaults
and the export are the owner's decisions (TODO area B2).

**For the third agent**: `tests/tools/ref_patch_survey.py` and
`docs/handoff_out/08-ref-patch-comparison.md` (outputs, split truth on
real curves with interleaved halves, repeats, how to judge); a worked
example on NX in `docs/comparisons_data/ref_patch_nx/`.

### 2026-11-22 — Synthetic data generators merged; two findings

**Owner:** "spawn another subagent to spearhead a synthetic data revolution
in a worktree ... Reflectivity synthetic data should be first made in the
reduced form, rather than images. Kiessig fringes and the response of
water-air interface are critical components of the synthesis. They should
keep notes for other agents to use the generators for testing."

**Done** by the subagent, merged: `tests/synthetic/` (reflectivity of
water and layered interfaces by Parratt with Névot–Croce roughness,
Kiessig fringes, capillary roughness; reduced scans as the reader makes
them, with known factors, absorbers, monitors and planted faults; frames
and SPEC files rendered from them; a three-level legacy GID set; GID burn
profiles; XFNTR; growing files for live tests), 72 tests, notes in
`docs/SYNTHETIC_DATA.md`. Literature values marked "from memory" there
(NIST could not be reached from the session).

**Findings (measured with the generators):** (1) P1: the legacy factor is
16.7 % low when a staggered overlap straddles the critical edge (0.01–
0.04 % above Qc). (2) P44 (new): the burn test's template estimator reads
a broadening at constant area on a shoulder as a 15 % intensity gain;
every window estimator under-reads a peak fading on a shoulder. Recorded;
the estimator choice is hand-off 07's item 3. P36 and P37 are now strict
xfails on the three-level set.

### 2026-11-22 — The patching gauntlet; the joint fit becomes the default

**Owner:** "Reflectivity patching: make new method the default if it passes
the gauntlet." Then, while it ran: "to be clear we dont need to patch across
critical edge. There's really no reason to patch early in Qz (change
absorbers) until counting statistics drop off by more than 100x, since we
start from a place of 'plenty', with 1e6 counts per second in the ROI at
total reflection (low Qz)." And: "monc doesn't have poisson noise, it's more
like a strict 0.05% uncertainty, you can see the xray_fluxor public repo for
more on that."

**The gauntlet** (`tests/tools/ref_patch_gauntlet.py`; outputs in
`docs/comparisons_data/ref_patch_gauntlet/`; C36). Hand-off 08's rule at
every join: |mean pull| < 0.2 and pull SD within 0.9–1.15, over 400 noise
replicates of synthetic scans with known factors: water, DPPC, 100 Å and
250 Å films (Kiessig fringes), coinciding, staggered and NX-like grids, a
low-count set. The private `bu` data hold no reflectivity series (checked
with `series.all_series`: GID, energy and fluorescence only), so real data
gave only NX scans 6–9 (3 joins; the split test there has n = 3, too few
for a pull SD). Monc is modelled as the owner says (no Poisson noise,
0.05 %: `xrr_scans.REAL_MONITOR`); with Poisson Monc noise (0.2–0.3 % per
point) the χ² test was blunter and the verdict the same in kind. The plan
across the critical edge is kept as information only.

**Measured** (18 judged joins): legacy passes 0 (its errors are 1.1–4.8 ×
too small; +5.5 % at a thick film's last join); the joint fit as built
earlier today (4 points either side, guard p ≥ 0.01) passes 6; after two
fixes, 17 with 2 points either side (16 with 4). The fixes:
1. *The guard could only shrink the window, ending at order 2.* Four
   coinciding points at a fringe minimum fit no quadratic (χ²/dof 282) and
   the error was inflated × 17 (δ itself was right); a 250 Å film's fringes
   biased the factor by −2 to −4 %. Now `guard_ladder` tries the largest
   window first with the order rising to what the points carry, then
   smaller windows, and keeps the first adequate fit.
2. *p ≥ 0.01 let model bias through.* Noise-free, the joint fit with 4
   points either side is 0.23 % (0.4 σ) low at water's first join, where
   legacy is exact (the points coincide); χ² accepted it in 75 % of
   replicates. The guard now asks p ≥ 0.3, and the default window is 2
   points either side.
The remaining failure is fail-safe: the 250 Å film's third join, +0.44 %
inside an error inflated by its χ² (pull SD 0.19). Across the critical edge
every method is biased (joint +1.35 %, legacy −10.4 %), which per the owner
does not arise.

**Changed output** (deliberate): the window's Ref Patch and
`Experiment.reflectivity` fit the factor with the joint fit
(`reflectivity.join_factor`; preference `ref_patch_method`, 'legacy' for
the old files byte for byte; the legacy export fixtures are compared under
'legacy'). NX 6–9: factors +0.20 %, +0.13 %, +0.14 % (within 1σ); no point
moves by more than 0.2 %. The synthetic two-scan set's last point: 0.982 →
0.994 of the truth (`test_gui_workflows`). Verified: tests and the tool
(measured), not reading only.

**Not yet:** the larger real data set (hand-off 08), whether the foil prior
is used by default (TODO B2), and the export of the covariance (the
covariance agent's branch, merged next).

### 2026-11-22 — The gauntlet over many conditions

**Owner:** "The gauntlet also requires using the synthetic data
capabilities and lots of replicates under diff conditions."

**Done** (`tests/tools/ref_patch_gauntlet.py --design all --methods key`, outputs in
`docs/comparisons_data/ref_patch_gauntlet/`, C36). The generators' range
was used one factor at a time from a baseline (a 100 Å film, four scans,
NX flux, the owner's monitor), 400 replicates each: the layer (water, DPPC,
films 50–400 Å), roughness, the grid (coinciding, staggered, NX-like,
reaching back), 3–5 scans and the Qz range, overlaps of 3–6 points,
counts ×0.03–1 and time ×0.3, background ×10–100, monitor noise 0.05–0.2 %
or Poisson, resolution, 8/10/15 keV, and planted faults (slits opened ×2
that Monc misses; a foil 2 % thicker than calibrated). Then 150 random
mixtures of all of these, 60 replicates each, judged with two standard
errors' allowance and pooled.

**Measured.** Designed conditions, joins passed (of 155): the default joint
fit 139, legacy 1. Random (of 463): default 415, the spline ratio 375,
legacy 118. The default's failures in the random set are where the scans
do not resolve the Kiessig fringes: with ≥ 6 points per fringe period it
passes 259 of 261 joins (pooled pull mean ≈ 0, SD 0.91–0.99), with 3–6
points 75 of 80, with fewer than 3 only 81 of 122, and there every method
that models the curve fails (the spline ratio, the joint fit with any
window, legacy); only the ratio of coinciding points stays honest, where
points coincide. Undersampled fringes come from the synthetic standard plan
doubling its step scan by scan (0.02–0.04 Å⁻¹ on a 200–330 Å film), not
from a plan anyone would measure; recorded as a limit, with a to-do
(TODO B: fall back to the coinciding points where χ² is marginal and three
or more points coincide). The reader's own path (``reflectivity.patch``):
the default's last-scan level within 0.1 % of the truth in every judged
condition; legacy −14 % across the critical edge and +4 % on a 250 Å
film's staggered joins. The foil-prior variant is conservative on
synthetic foils (pull SD 0.7–0.9: the synthetic attenuation is exactly
nominal, the prior's stated error is the calibration's), so it says
nothing yet about real foils. The default stands. Verified: measured with
the tool, not reading only.

### 2026-11-22 — What does a model fit need from the covariance?

**Owner:** "Have another subagent think about what is needed on
covariance downstream for model fitting, then have them build something
workable."

**Answer** (`docs/reports/downstream_covariance.md`): a fit needs, per
point, the counting-only error σ_meas, the point's weights W on the
scans' log scales, and the K × K covariance Σ of those scales. That is
exactly the xmodfit sidecar (hand-off 19). The covariance is then
diag((σ_meas/y)²) + W Σ Wᵀ in log space. With the Woodbury identity it
costs an r × r solve (r ≤ K − 1). Equivalently, it is one nuisance scale
per scan with a Gaussian prior, exactly in log space (I29). The overall
normalisation is a free scale, not part of Σ. Per-point
multiplications (normalisation, Fresnel) never change Σ, and sorting,
cuts and masks select rows of W (I28). A fitter must check x and y
against the file and must use σ_meas, not the file's column, with the
covariance.

**Measured** (synthetic NX-like scans of a 25 Å film, the owner's
monitor model (no Poisson, 0.05 %: "monc doesn't have poisson noise,
it's more like a strict 0.05% uncertainty"), 300 seeds, fits of d, ρ, σ
with a free scale; `tests/tools/covariance_pulls.py`):

| Errors used (default joint patch) | pull SD d / ρ / σ | χ²/dof | RMS of ρ |
|---|---|---|---|
| the file's column (factor errors folded) | 1.48 / 4.12 / 3.88 | 0.79 | 6.3e-4 |
| √diag C (the hand-off's corrected column) | 0.88 / 3.88 / 2.35 | 0.61 | 7.2e-4 |
| counting only | 2.89 / 6.36 / 6.19 | 1.35 | 5.9e-4 |
| covariance (joint, legacy or corrected factors) | 1.10 / 0.98–1.00 / 0.95–0.96 | 1.01 | 2.2e-4 |
| covariance, stitched points | 1.06 / 1.00 / 1.00 | 1.01 | 1.6e-4 |

Measured Σ against the true spread of the factors (hand-off §5.7):
1.08–1.11 × for the legacy and §3.2 factors; 0.88–0.95 × for the
joint factors. At the first join the joint Σ is the joint fit's own
error, whose pull SD is 1.13 on these scans: the default fit's error
is about 12 % small there (a finding for the patching, passed on).

NX school 6–9: √Σ of scan 9 is 0.85 % (joint, the default), 1.03 %
(legacy factors).

With the older Poisson-monitor synthetic data, counting-only σ_meas gave
χ²/dof 1.29 even with the covariance: a covariance is only as good as
its diagonal.

**Σ of the default patch** (report §6.1): the joint chain fits each scan
against the folded error column of the curve so far. The export keeps
the factor used, so the files do not change. Each step's error in Σ is
that fit's spread under counting noise alone (its sensitivity to each
point), inflated by the overlap χ² against counting errors, with a_m
from the same sensitivity. This avoids counting the earlier factors'
errors twice.

**Built:**
- `lss_core/covariance_export.py`: the patch replayed bit for bit with W
  and Σ carried beside it (joint and legacy, `tracked_chain`); the
  hand-off's corrected chain, checked against an independent oracle to
  1e-10; stitched points; the window's finishing steps; the sidecar and
  combined files; both of the contract's layouts.
- `lss_core/gls.py`: XModFit's loader checks, the Woodbury χ², and a
  reference fitter in nuisance form.
- `ReflectivityResult.save(name, covariance='sidecar' | 'contract')`.
- The Ref Patch "+ covariance" box (off by default: the owner's
  decision, TODO B2). It writes sidecars beside the unchanged text files
  and follows the method the patch used.

**Verified:** `tests/test_covariance_export.py`, `tests/test_gls.py`,
`tests/test_gui_covariance_export.py`. The legacy export fixtures are
unchanged. Hand-off tests 5 and 6 use stand-ins: an oracle written from
the hand-off's text, and XModFit's checks reimplemented. XModJointFit's
`lss_reference.py` and `covariance_core.py` are still to be supplied
(D13 note).

### 2026-11-22 — P45: the known ratio at the third join was off by the first factor

Found by reading `pilRefPatchNext` while building the covariance export,
then measured with four synthetic scans of bare water rendered as frames
(`tests/synthetic/xrr_images`). At the third join the window offered a
known ratio of 1.72e-8, where the foils chained give 1.64e-6 and the fit
gives 1.64e-6. The offered ratio was off by ×0.0105, the first join's
factor. The window recorded each scan's level as the previous level ×
the factor used, but the factor is fitted against the curve joined so
far, so it is already the level. Fixed (`refScale[b] = used`), with
`test_known_ratio_is_right_at_every_join` (both patch methods). The
legacy export fixtures are unchanged. Output changes only where the
known ratio was used at the third join or later: the automatic choice
had rejected it there, as "N sigma from the patch".


### 2026-11-23 — A typical reflectivity day at the beamline (owner's answer to GUI question Q-GEN-2)

**Q** (GUI assessment, `docs/gui/questions.md` no. 1): a typical day at the
beamline, in order: which scans, reductions and checks for one sample?

**A** (owner, 2026-11-23; a day of reflectivity only, GID and fluorescence
"will have to wait for another account"), in order:

1. **Rough alignment** with a half-cut; this will become a sample height
   scan with a horizontal beam, which also measures the beam profile. The
   sample-height offset is set to read zero on that scale.
2. **Sample height scan**: at a fixed incident angle, sample and detector
   rise together, to judge how flat the liquid surface is. Scans taken at a
   few places or sample conditions are reviewed together on one plot (by
   selecting them together in the scan list).
3. **Burn tests** with the relevant conditions and detectors: click the
   burn scan, Select All, Burn Test and its dialog. From the first, decide
   which absorber to change to and repeat. Sometimes the sample is changing
   and is not being burnt at all. Plotting the Langmuir barrier position and
   the tensiometer reading beside the detector data would help (these will
   be written to the SPEC file for every point in future) (F75); an
   analysis across the burns at different absorbers would help tell a
   changing sample from beam damage (F76).
4. **Burn criterion**: effectively no change over about 400 s, "proven, not
   predicted". Once an absorber level is established, burn tests are not
   repeated, so they do not always precede the real data. Predicting a safe
   absorber from a shorter test at higher flux "would be interesting" (F77).
5. **First data set** from the macro of the main experiment (reflectivity,
   GID or XFNTR). Reduced today by selecting the scans by hand, Select All,
   Ref Patch, and reviewing.
6. **R/R_F**: the critical angle of water at the energy is assumed, and
   Qoff is tweaked by hand until R/R_F looks continuous, or has one or two
   outliers but is otherwise smooth; Qc is changed for samples lighter or
   denser than water (F79).
7. **Macros tuned** from the results: counting times for reflectivity,
   which angles to search for GID.
8. **After 30 min or more, or a large sx change**: another sample height
   scan, viewed in the reader to decide whether to continue. Wide enough,
   and more like a super-Gaussian with a flat-ish top? One well described by
   a Gaussian is possibly unusable. A sample height scan is the surface
   curvature convolved with the beam profile (read as the reflected-beam
   ROI on the Pilatus), so it has real width and smoothness; the default
   motor range is chosen to capture most of it (F78).
9. **Stability**: reflectivity goes on; reduced curves from different
   places, or over time, are compared in the reader (F80).
10. **Sample change**: the chamber is opened (the oxygen level in the trough
    enclosure rises; some chambers have no oxygen sensor), the shutter is
    closed and the hutch opened, tensiometer readings taken, the barrier
    moved; then rough alignment again, and the cycle restarts.

*How verified*: the owner's words (reading only). Recorded in the workflow
map (`docs/gui/workflows.yaml`: `day-ref`, and the alignment, burn-ref and
reflectivity workflows), as F75–F80 in `FEATURE_REQUESTS.md`, and in the
answers table of `docs/gui/questions.md`. It settles Q-GEN-2 and Q-BURN-1,
and answers parts of Q-REF-1 (Ref Patch is the routine path), Q-REF-4,
Q-REF-5, Q-GEN-1 and Q-GEN-4.

Physics that goes with it (this project, not the owner's words):

- **Qc in Qz does not depend on the X-ray energy; the critical angle does.**
  Qc = 4√(π r_e ρ_e), with r_e the classical electron radius and ρ_e the
  electron density, away from absorption edges, where the dispersion
  correction f′ is small (Als-Nielsen and McMorrow, *Elements of Modern
  X-ray Physics*, 2nd ed., Wiley 2011, ch. 3,
  https://doi.org/10.1002/9781119998365; link not opened in this session).
  For water at 25 °C, ρ_e = 0.3333 e/Å³ and Qc = 0.02173 Å⁻¹ (computed,
  r_e = 2.8179 × 10⁻⁵ Å, 0.99705 g/cm³); the reader's preset 0.0217 is
  this. The critical angle, α_c = arcsin(Qc λ/4π), is 0.1535° at 8 keV,
  0.1228° at 10 keV, 0.0819° at 15 keV and 0.0614° at 20 keV (computed). So
  "the critical angle of water for the energy" is a single Qc for every
  energy. For a lighter or denser subphase Qc scales as √ρ_e: 10 % denser
  gives 0.0228 Å⁻¹, 10 % lighter 0.0206 Å⁻¹ (computed).
- **A constant Qoff is the right first-order correction for an angle
  offset.** Qz = (4π/λ) sin α, so an offset δα in the incident angle shifts
  Qz by (4π/λ) cos α δα, which is constant to better than 0.2 % below
  α = 3° (cos 3° = 0.9986). Derivation only, not tested.
- **Damage or a changing sample (F76), and prediction (F77).** A change
  caused by the beam should follow the absorbed dose, flux × time; a
  sample changing by itself follows time alone. Burns at two absorbers
  with flux ratio r (from the absorber ratio) should coincide against dose
  in the first case and against time in the second. Predicting a safe
  absorber from a short high-flux test assumes the change depends on the
  dose alone, whatever the rate: the reciprocity, or Bunsen–Roscoe, law of
  photochemistry (https://en.wikipedia.org/wiki/Bunsen%E2%80%93Roscoe_law;
  not opened in this session). It can fail through dose-rate effects or,
  at a liquid surface, through molecules exchanging into the illuminated
  footprint. Derivation only; no burn pairs are in the public data.
- **A super-Gaussian for the sample height scan (F78).** The owner's
  criterion is a flat-topped profile, not a Gaussian. A form that covers
  both is I(h) = A exp(−|(h − h₀)/w|^p) + b: p = 2 is a Gaussian, larger p
  flatter. Proposal only; the thresholds of a verdict on w and p are for
  the owner.

Open (for the owner, later): once an absorber is "established", is that per
kind of sample, per subphase, per energy, or per beamtime? The scans were
selected by hand for Ref Patch: is the Series list (D55, one action selects
a whole series) not offered for your files, or not yet known?

Added the same day (owner): the frame-by-frame ROI check of reflectivity
"does happen, but mostly when something is weird and we need to verify the
data are ok"; a slick movie, on a log or other nonlinear scale, would make
it more frequent, and "showing people the raw data helps them avoid
mistakes". GID frames are often watched as a movie, "since real GID peaks
stay at the same two-theta and other junk does not as the detector angle
changes". The geometry behind it (this project): a Bragg rod scatters at a
fixed 2θ (fixed Qxy), so as the detector arm steps, its image moves across
the pixels with the arm; anything fixed relative to the detector or the
slits (hot pixels, stray light, window or slit scattering) stays on the
same pixels and so moves in 2θ. A movie drawn on a common 2θ axis, the zoom
held in angle, shows the real peaks standing still (`docs/gui/image_display.md`
M7). In every case the zoom (for reflectivity, the region around the ROI)
and the colour mode must not change while the frames play (F69). *How
verified*: the owner's words; the geometry is a reading of the pinhole and
legacy GID geometry, not tested.

Follow-ups the same day (owner):

- **Statistics.** The day includes "getting data and deciding if we need
  better statistics (repeat the macro (multiple scans) and have reader
  handle summing the ROIs if we want it to" (F81). As coded, Ref Patch's
  identical-scans step merges repeats as the plain mean of their
  per-monitor curves with equal weights, the error √(Σσ_i²)/n
  (`pilRefSSMerge`; read). Summing the ROIs and the monitors,
  R = ΣS_i / ΣM_i, weights each repeat by its monitor M_i. In the counting
  limit σ_i² ≈ R/M_i, so the inverse-variance weighted mean of the R_i,
  Σ(R_i M_i)/ΣM_i, is the ratio of sums. The two merges agree when the
  monitors are equal and differ when the beam decays between repeats.
  Derivation only; not tested.
- **Sample height scan.** "A good sample height scan has a FWHM better than
  about 65 microns, and some flat 'quality' to it, like i said it should be
  more squashed than a gaussian" (F78). Read with "wide enough" (above) as
  a FWHM of about 65 µm or more; in the super-Gaussian form above, an
  exponent p > 2. No threshold on p given.
- **Safe absorbers.** Established safe absorbers "depend heavily on the
  sample and the subphase and energy but per beamtime there is no change".
- **Qc.** "Qc does not depend on x-ray energy, fine; but it does depend on
  the sample being something besides pure water (pure water is not very
  interesting and does not pay the bills)." Qc is that of the subphase,
  the bulk below the film: Qc = 4√(π r_e ρ_e) with ρ_e from the subphase's
  composition and mass density, ρ_e = (ρ N_A / M) ΣZ per formula unit. So
  water's 0.0217 is a placeholder, rarely the value (F79).
- **Series list.** Scans are selected one by one because the Series list
  "is a new feature and hasn't been known or tested by humans yet".

*How verified*: the owner's words; the merge reading of `mainwindow.py`;
the weighting is a derivation.

Two corrections the same day (owner):

- **Qc**: on "rarely the right value", the owner: "it's rarely very wrong,
  depending on which decimal place you're looking at". Aqueous subphases
  differ from water in the third significant figure. 1 M NaCl: ρ_e =
  0.3440 e/Å³ and Qc = 0.02208 Å⁻¹, 1.6 % above water's 0.02173 (computed;
  density 1.037 g/cm³, from memory, not checked). That digit matters for
  R/R_F. Far above the edge R_F = (Qc/2Qz)⁴, so a relative error ε in Qc
  is an error of about 4ε in the level of R/R_F, and more near the edge.
  Computed with the exact Fresnel formula, assuming water's Qc when the
  subphase's is 0.0002 Å⁻¹ higher (0.9 %) makes R/R_F 3.7 % too high
  above Qz = 0.1 Å⁻¹, 4.2 % at 0.05 and 7.8 % at 0.025. For 1 M NaCl
  (0.02208 against 0.02173) it is 6.6–6.8 % too high above Qz = 0.1,
  7.4 % at 0.05 and 14 % at 0.025. At
  high Qz this is a constant factor, which a fit with a free scale
  absorbs; near the edge it changes the shape.
- **Sample height scans**: the owner confirmed "at least" about 65 µm FWHM;
  "They go about as large as 110 microns in the trough 89 mm wide." (The
  width presumably depends on the trough, through the meniscus; a guess,
  not the owner's words.)

*How verified*: the owner's words; the R/R_F numbers computed with the
exact Fresnel reflectivity, R_F = |(Q − √(Q² − Qc²))/(Q + √(Q² − Qc²))|².

Measured the same day (timeline research, F83; `docs/gui/timeline/research.md`):
the three sample height scans of the public NX file (`a2scan sh … oh …`, SPEC's
`Pilatus` ROI column) fitted by a super-Gaussian give FWHM 82.1, 81.1 and
81.4 µm with exponents p = 3.36, 3.38 and 3.53 (χ²/dof 2.6–5.2, against
28–34 for a Gaussian). They meet the owner's criterion: at least about
65 µm, flatter than a Gaussian. A scan that saw no reflected beam must be
refused first (peak at least 10σ); otherwise it "fits" with a meaningless p.
SPEC's `set sh 0` is written as a dated comment, `#C <date>.  Sample_H reset
from <old> to <new>.` (the motor name, not the mnemonic); `#P` keeps the
nominal position, so the comment is the only trace. Whether a reset means a
new sample is not in the file: the NX file's one `set sh 0` is probably the
same sample after a scan that found no beam (read from context). *How
verified*: fits and parsing run on the NX file by the research subagent;
the meaning of the NX reset is a reading.

### 2026-11-23 — Can the stalled test-speed and Tools-menu agents' work be used?

**Owner:** two agents stopped when their usage credits ran out: the
test-speed agent (the tests took too long and used too much RAM and disk)
and the Tools-menu agent. How much of their in-progress work can be used
and built on?

**Answer (reading git refs and GitHub's event feed, not a run).** None of
their own work reached GitHub. They ran under another organisation's
account, so their sessions, and anything they had not pushed, cannot be
reached from this one. GitHub holds three branches: `main` (ends at
9b81910, 2026-11-22 23:57), `claude/funny-noether-09opxa` (the GUI
manager) and `wip/pinhole-figures` (2026-11-19). The event feed since
2026-11-19 shows pushes to these alone, and no branch created or deleted.

What `main` holds for each task, all from the session that launched them
(commit trailer `…B43N3sPHf2MNUrW8`):
- Test speed: the per-control sweep timing log `LSS_SWEEP_TIMES`
  (b1c90e7); measured suite times and the three-shard recipe in
  `TESTING.md` (ed6b6f0); the TODO row in area I with three options
  (7adf3e2). Nothing for RAM or disk. Two causes of disk growth, read but
  not measured: `tests/conftest.py` makes a new `lss_reader_test_logs_*`
  folder in the system temp folder on every run and never removes it, and
  pytest 9.1 keeps the `tmp_path` folders of the last three runs
  (`tmp_path_retention_count = 3`, policy `all`), which hold synthetic data
  sets, workbooks and screenshots.
- Tools menu: only the entry point, `open_demo(parent, mode, seed)` and
  `DemoWindow(parent=…)` in `tests/demonstrator/window.py` (3611855), with
  `test_patch_demo.py::test_the_window_opens_from_code_with_a_parent`.
  There is no Tools menu in `mainwindow.ui` or `mainwindow.py`. What the
  agent was to build is inferred from that commit and
  `docs/reports/patch_demo.md` (its brief is in the other account): a Tools
  menu in the main window that opens the fit demonstrator (reflectivity
  patching and burn line cuts on synthetic data). One obstacle, read:
  the demonstrator imports `synthetic` from `tests/`, and the PyInstaller
  recipe bundles only the `.ui` files and icons. A menu item in the
  packaged program therefore needs those modules moved into a bundled
  package, or must be hidden when they are missing.

The agents' unpushed progress can be recovered only from the other
account: when its credits return, ask each session to commit and push to a
branch (for example `wip/test-speed` and `wip/tools-menu`), so that it can
be judged here.

### 2026-11-23 — Speeding up the tests: the motor-scan fit, and flat scans

**Found while timing the crash sweep** (the test-speed work, below).
Building a window takes 0.1 s, but putting it in the sweep's `motor_scan`
state took 9.5 s, every time: the window fits the shape of every motor
scan it plots (`peaks.fit_scan`), and the box candidate, fitted to the
synthetic motor scan's clean Gaussian (21 points, FWHM 0.471), ran all
20 000 evaluations allowed (400 442 model calls) and then failed, as it
must: a box cannot converge on a peak. The sweep gives about 260 controls
a fresh window in that state, twice; about 80 of its 180 minutes. A user
plotting such a scan waited the same.

**Owner:** "I think there's a motor scan with bad data; it's basically a
flat noisy line. There's no point hammering it with fits."

**Measured on NX school** (`tests/tools/fit_scan_survey.py`, C37): the
real scans' converged edge and box fits used at most 166 evaluations, and
the slowest real fits were flat lines: scan 4's Monc (2.8 s) and its
Pilatus column, 7–19 counts of noise around 12, which `fit_scan` reported
as a peak at −2.2304 (its one 19-count point). Two changes:
- The final edge or box fit stops at 2000 evaluations
  (`SHAPE_FIT_MAX_NFEV`): no NX fit changes; the Gaussian motor scan
  12 s → 3.8 s, same answer (a peak, FWHM 0.471).
- A scan its background alone fits (weighted least squares, χ² p-value >
  0.05; `peaks.is_flat`) is reported as `kind` 'flat' and not fitted. On
  NX, 17 of 26 (scan, column) pairs: ramps (Epoch, Out_Ht, H, K), monitors
  within counting error, scan 4's Pilatus. On synthetic data a 4σ peak on
  12 counts was never called flat in 200 noise draws, a 3.5σ one once in
  200, a 2.9σ one 8 times; pure Poisson noise is called flat 92 % of the
  time (95 % expected; errors taken from the data bias χ² up a little).
  Scan 4's Monc is not flat by this test (its 2 % drift is far above its
  counting error), so it is still fitted.

Verified: measured (survey, both rule sets) and tested
(`test_peaks.py::test_a_box_that_cannot_converge_gives_up_early`,
`test_a_flat_noisy_scan_is_not_fitted`, `test_a_weak_real_peak_is_still_fitted`).
Where the model choice was close, a weak noisy Gaussian (4σ, 41 points)
is chosen as a box by the Akaike criterion, as before this change; not
looked into.

**Owner, later the same day:** "if you know what constitutes a sample
height scan (which motors and what scan type) then you can limit fitting
on those scans to decent signal to background ratios; it's not a tough
scan to do, we always get good signal, and the FWHM is always greater
than 20 microns."

**Done.** In the NX school file the height scans are `a2scan sh … oh …
20 1` on the Pilatus (scans 4, 5, 10, 13; sh in mm, 8 µm steps). A scan
whose first motor is sh, over a range (`ascan`, `a2scan`, `dscan`,
`d2scan`), plotted against sh, is fitted only when (highest − lowest) /
lowest of its 3-point smoothed curve is at least 2, and shapes narrower
than 0.020 mm are dropped. The ratio is taken this way, not against the
scan's ends, because a half-cut is an sh scan too and its two ends sit on
different levels. Measured: scans 5, 10, 13 give 8.45, 6.78, 7.23 and the
same plateaus (81–82 µm) as without the rules, bit for bit; scan 4 gives
0.48. Over all 26 NX fits, time in `fit_scan` 5.7 → 0.5 s, and 20
change, every one to no fit (C37). Tested:
`test_height_scans_are_recognised`,
`test_a_height_scan_needs_good_signal_and_a_width_over_20_microns`, and in
the window `test_height_scans_are_fitted_only_with_good_signal`. The
threshold 2 is this project's choice (OUTPUT_DECISIONS, open
assumptions). The 20 µm is a plausibility floor (narrower is not a height
scan at all); the owner's "a good sample height scan has a FWHM better than
about 65 microns" (up to 110 µm, flat-topped; entry above, F78) is the
verdict on a scan that was fitted, a separate to-do (TODO area I/F78).

### 2026-11-23 — Is the pinhole calculation a floor? Can it be done with matrices?

**Owner:** "tell me more about the pinhole calculation. is this really a
floor? can it be calculated with matrices or something?" (The slowest
quick test, `test_pinhole.py::test_calibrate_distance_recovers_the_true_distance`,
took 30 s and set the parallel suite's floor.)

**What it computes.** `pinhole.calibrate_distance` finds the S4-detector
distance at which single frames agree on a Bragg line's 2θ: it tries 47
distances, and for each, fits the line in every one of 41 frames, using
only each frame's usable columns. The footprint window of those columns
(`_exact_window`) needs, for both ends of the footprint and both edges of
the S4 opening, the column whose ray through the slit starts at that end
of the footprint (`column_at_source`).

**Where the time went (profiled).** 85 % in `column_at_source`, which
inverted `ray_geometry` by bisection: about 48 one-ray evaluations per
answer (a cross product and a 3 × 2 least-squares solve each), 378 310 in
all.

**Not a floor: there is a closed form**, linear algebra in three
dimensions. The source point S = (x, 0, 0) and the slit line (point L,
direction e_v) span a plane with normal N = (L − S) × e_v. A pixel of the
row is P = centre + w_x e_h + w_y e_v, and it lies in the plane when
N·(P − L) = 0; since N·e_v = 0 this is linear in w_x:
w_x = −N·(centre − L + w_y e_v) / N·e_h, and the column is c0 − w_x/pixel.
The plane meets the row in one point, so the answer is unique on the side
of the column that looks along the beam where the direct beam lies (the
other side is the bisection's "no column": e.g. a point beyond the slit's
projection, L/cos Det_Th); one ray is then traced to check that it starts
at x and runs forward.

**Measured.** Over 33 600 geometries the closed form gives the bisection's
column to 6.8e-9 of a column, and finds a column wherever the bisection
did; in 240 cases, all footprint ends 2 m upstream beside the column that
looks along the beam, only the closed form finds one (checked by tracing
its ray; the bisection's bracket gave up there; such columns lie far off
the detector at GID angles). NX school scans 11 and 12, 180 frame windows
at four pinhole distances: identical, bit for bit. Per call 24 × faster;
the calibration 30 → 6.6 s (the rest is the 818 peak fits). Every pinhole
and GID test passes, real-data references included. Verified: measured
and tested (C38). The bisection stays in the code as the reference
(`_column_at_source_bisection`).

### 2026-11-23 — Keeping cloud sessions fast, so that agents need not manage testing

**Owner:** "Looks like you're the speedup testing agent now. Start from
scratch and figure out how to keep these cloud sessions running fast and
freely, so agents don't need to manage testing." (The first test-speed
agent stopped when its credits ran out, with nothing pushed; entry above.)

**Measured first** (a 4-CPU, 16 GB cloud container; `pytest --durations`,
a sampler of memory and /tmp every 5 s). The quick suite took 9 min 44 s
in one process, grew to about 10 GB, and left 1.2 GB and 121 folders in
/tmp; the real-data suite about 25 min; the crash sweep about 3 h. A
fresh session also lacks PyQt5, matplotlib, SciPy, lmfit and sympy
(installing them takes about 10 s).

**Causes found, and what was done** (one commit each, every one tested):
- Every test's window stayed in memory (about 110 MB each with data):
  `close()` + `deleteLater()` never deletes it without an event loop, and
  the window's own signal connections keep its Python side alive.
  `conftest.free_windows` runs after every Qt test (collections made cheap
  by `gc.freeze()`); the image cache is capped at 512 MB per test process.
- Disk: `tmp_path` kept only for failing tests and only from the latest
  run; the temporary folders conftest and the sweep make are removed.
- One process: `pytest-xdist` is in the dev requirements, and a plain
  `pytest` runs on one worker per CPU (at most one per 2 GB available),
  except benchmarks and baseline regeneration. A first version made each
  worker start workers of its own until the container ran out of memory;
  workers now never take the default.
- The program itself was slow in two places the tests exercised: the box
  fit on every motor-scan plot (9.5 s; now capped, and flat or weak scans
  not fitted at all, at the owner's word) and the pinhole footprint window
  (a bisection, now closed form; entries above).

**Result** (measured, same container): quick suite ~2 min (761 tests),
peak 3.4 GB over four workers, nothing left behind; real-data suite
~4 min; crash sweep ~20 min (193 tests: each state now shared by 8
tests, so that workers finish together; 24 min as 18 tests, about 3 h in
one process). Agents run the quick and real-data suites in the
foreground with a plain command (a session's foreground command may run
10 min) and start the sweep in the background; AGENTS.md and TESTING.md
say so. Three real-data tests that
fail on main since 2026-11-22 were found and bisected (TODO area I).

**Left to the owner:** the cloud environment's setup script should run
`cd LSS_Reader2 && pip install -r requirements-dev.txt`, so that a new
session can test at once.
### 2026-11-23 — Plotting and image display: where the time goes

**Owner:** "please take a look at all the plotting and image display for
speedups. Displaying many MCA spectra on a log scale was a notorious
slowdown. So was log scale image display."

**Measured** (`tests/tools/plot_speed.py`, the real window offscreen;
standalone matplotlib for the variants; C39):
- **MCA spectra.** Each spectrum was drawn with `errorbar`, which makes one
  path per channel's error bar: 100 spectra of 2048 channels, 205 000
  paths, each sent through the log transform on its own on a log axis.
  Plotting them with log y took 4.21 s, switching log y on 2.37 s, and
  every pan, zoom or resize redrew for about 2.4 s. Now each spectrum's bars
  are one path with breaks between bars (`mplwidget.errorbars`): the same
  bar ends, colour and width; 0.76 s, 0.54 s and about 1.0 s. What is left
  is drawing 200 000 points; markers are a fifth of it.
- **Log-scale maps.** The legacy GID patch map used `pcolor` (a polygon per
  cell) in log scale only, `imshow` in linear, which is why log was the
  slow one; the 2D_Plot tab used `pcolor` in both. Now `pcolormesh`
  (`mplwidget.mesh`), the same cells: 500 × 500 cells redrawn 0.52 → 0.09 s.
  `pcolor` stays for grids with non-finite coordinates, which `pcolormesh`
  refuses.
- **Pilatus frames** (`imshow`, bicubic): fast with today's matplotlib, about
  0.2 s for a Pilatus 1M frame, log or linear; a different interpolation
  would gain 1.5 × and change the look, so it is left. The first log axis
  of a session also parses its tick labels as mathtext once.

Verified: measured and tested (`test_plot_speed.py`; the GUI manager's
`test_gui_2dplot.py` passes on the mesh).

### 2026-11-23 — File IO, RAM and disk caching reviewed

**Owner:** "Then review all the file IO, ram and disk caching plans."

**The plans** (FEATURE_REQUESTS F6–F9): faster MCA parsing (F6), faster
Pilatus 1M frames (F7), a local disk cache for the production network
drive (F8), a RAM cache sized to the host (F9); entries keyed by path,
size and modification time, LRU, the disk cache with a size cap and a
location. All four were built in Stage 2; this review measured them again
on this container (local disk) and looked for what they missed.

**Measured, fine as it is:** reading a SPEC file is linear, 0.5 ms per
scan (3000 scans, 10.6 MB: 1.4 s; the window opens it in 3.4 s, most of it
parsing numbers); a Pilatus 100K TIFF decodes in 1.7 ms, a 1M frame in
9.6 ms; bad-pixel correction of a 1M frame takes 0.04 s (one iteration)
to 0.08 s (three), so F7's worry is gone. The RAM cache (a quarter of the
memory, at most 4 GB) and the disk cache (only files on another file
system, 5 GB, writes atomic) are keyed as planned, so a file still being
written is read again.

**Found and fixed:**
- MCA files were parsed again for every selected scan on every change of
  the scan selection (whole-series selection makes that every click):
  20 files of 30 spectra, 0.38 s per click locally, more over the network
  drive, which the disk cache does not cover for MCA files. Now parsed
  once per file version in the memory cache (`lss_core.mcafiles`): 8 ms.
- The disk cache walked its whole folder after every new entry (16 ms per
  frame at 6600 entries locally): now once per process and when its
  running total passes the limit, trimming to 90 %.

**Options, not taken:** frames are held as int64 (bit-identical with the
old reader), twice the TIFF's int32, which halves what both caches hold;
storing int32 would need every reduction re-verified against the legacy
fixtures. The speed over a slow network drive cannot be measured here
(TODO area I, "slow-file-system timing").

Verified: measured (scripts in this session; `tests/tools/plot_speed.py`
for the plots) and tested (`test_mcafiles.py`, `test_lss_core.py`).

### 2026-11-23 — P36 and P37 fixed: legacy GID maps with three Qz levels

A to-do of long standing (TODO: "fix with a synthetic three-level GID data
set; outputs change only for such maps"), taken up because it lies outside
the GUI work. In `lss_core.gid.legacy_patch` (the window's code since
2026-11-19):
- **P36** (= P14, defect 11): every frame is put back to counts with its
  scan's mean monitor, except that the first frame of each high-Qz scan was
  not, leaving it per monitor, about 1/M of its neighbours. Measured on the
  synthetic three-level set (`tests/synthetic/gid_levels.py`): where only
  the high level covers β, scan 5's first frame was 1/1.03e5 of the truth.
  Fixed: that frame is treated like the others, and every point of the map
  is within 5 % of the truth.
- **P37** (= P15, defect 12): a high level of one scan took the middle
  level's first scan key: a KeyError when the scans differ (the patch
  stopped with a message), the right data only when one scan had frames at
  both levels. Fixed: a level's one scan is its own; the map comes back
  within 5 % of the truth.

Two-level maps, which is all the real data on hand, do not change: the 38
real-data GID tests pass (NX school scans 11, 12 against stored curves).
The two strict xfails became ordinary tests, and the "as coded" test that
pinned P36's wrong value was removed with the fix. Verified: tested.

**Addendum, the same day: the GID map's redraws (G1).** The GUI-planning
session measured that a redraw of the GID map in Q (a colour map or Log
Int changed) took 2.7–3.0 s, most of it regridding the patched map with
`griddata` again (`docs/gui/image_display.md`, G1), and handed the item
over. Measured here on NX school scans 11 + 12: a redraw took 1.0 s
(legacy patch) to 1.4 s (pinhole patch), 70–77 % of it the two `griddata`
calls. The regridded map is now kept, keyed on the map's content (a hash
of its four arrays, so a patch or a live remake giving the same map in new
arrays is not regridded again): redraws 0.30–0.35 s, no number changes
(the kept products equal a fresh computation, bit for bit). Verified:
measured and tested (`test_gid_redraw.py`).


### 2026-11-23 — Which demonstrations and figure generators does the repository hold, and can they be made without staleness? (F84)

**Owner:** include all the demonstrations and figure generators of the
repository as entries of the reader's Tools menu, generated without
staleness ("built from what's in the repo and so don't drift"); the
largest part is recognising and surfacing them all; then homes for them in
the GUI, and documentation kept up to date, so that "change this parameter
and regenerate the figure to demonstrate this concept" lines in the docs
become reality. Later: build and test the menu items and their pages
separately from the main project.

**Answer (measured by running every tool on 2026-11-23, and by reading
the documents with a subagent).** The repository holds 31 scripts in
`tests/tools/` (one is a helper library), the fit demonstrator
(`tests/demonstrator/`, a window), the synthetic generators
(`tests/synthetic/`, `tests/synth.py`), and 13 figures made elsewhere
(hand-off 03's answer). All 30 runnable scripts ran from the current code
in this container (0.1 s to 104 s with their defaults; the gauntlet's full
design about 25 min). They are now 36 items of the Tools menu in seven
menus (`lss_toolbox/catalog.py`, `docs/TOOLS.md`; with `plot_speed.py`,
added on main later that day, not timed here); the documents name 62
variations ("change this and rerun"), each an entry with its document
line. Where a documented parameter was fixed in the code it became an
option: the foil fit's cuts, the demonstrator's settings (`--set`), and a
writer of synthetic data sets that the reader opens
(`tests/tools/synthetic_dataset.py`).

How staleness is kept out: a run executes the repository's script in its
own process (nothing is copied or cached), with a record of the command
and the git commit; each page's options are read from the script's own
parser; the menu, the window and `docs/TOOLS.md` come from one catalogue,
and `tests/test_toolbox.py` fails when a script is not catalogued, when a
variation names an option the script does not have, or when a committed
figure belongs to no item.

**Are the committed figures stale?** Git history (`python -m lss_toolbox
--stale`) flags most of them, because `lss_core` changed after they were
committed; it cannot say whether the change touches the figure. Rerunning
and comparing pixel for pixel can (`--audit`, measured; table in
`docs/reports/tools_audit.md`): the burn trends (4 figures, 3 tables) and
the fit demonstrator's report figures (6 figures, 5 tables) come back
identical; the pinhole figures and the manual's GID diagrams differ only
inside the one-line box where they print the git revision (0.04–0.12 % of
pixels); the beam-profile figure (1.6 % of pixels, across the plot) and
the stray-light figures (4–16 %) really changed; the reflectivity survey's
committed tables predate the joint fit's guard ladder (rerun: the median
error of joint_o4_e4 0.00407 → 0.00381, one join flagged per joint
method); the C2/C3 error-model tables were made with the legacy patch
before the joint fit became the default, so their σ now differ by up to
21 % (compared numerically), which confounds the comparison they exist
for. *Correction, later the same day (measured on the remade tables):* the
error models' ratios hardly moved (Gaussian/legacy 0.861–1.002 before and
after, Student t 0.893–1.004 → 0.893–1.005), so the comparison was not
confounded; only its curves were out of date. The gauntlet reproduces every committed row exactly. The C21 tables
have no generator in the repository. The window's "Compare all" gives the
same comparison for one item.

**Re-verified by a run:** the foil fit's robustness to its cuts
(physics_notes 2026-11-19, "each foil moves by at most 0.9 µm"): with
Monc/Monp within 1 %, χ²/dof < 5 and no error floor, 337 of 963 joins are
kept (409 by default) and every foil is within 0.4 µm of the default fit.

**Invariant added:** I30 (a figure tool rerun on unchanged code and inputs
gives its figures back pixel for pixel).

### 2026-11-23 — GUI questions answered, batch 1 (15, 14, 11, 12, 13, 10, 7)

Asked by the interview session from `docs/gui/questions.md`; answers verbatim
in spirit, recorded beside the questions. Verified by: reading only (no code
changed; these are decisions, not measurements).

- **Q15 residuals:** weighted, (y − fit)/σ. Unblocks F74.
- **Q14 removal:** Apex tab, Beamlines menu, unused `peakfit2`/`peakfitpara` dialogs and the Command line row may all go; Quit works; Help > Documentation opens `docs/SCRIPTING.md` until a manual exists.
- **Q11 panes:** Messages and Errors follow the Script pane's rule (D59).
- **Q12 badges:** yes, in the status bar; a preference with *on / on when not default / off* (F85).
- **Q13 legacy paths:** all essential; chosen on a Reduction options page; Ctrl+click flips the legacy boolean for one action and prints a message (F86).
- **Q10 burn kind:** Det_Th > 2° means GID; a macro role indicator is coming from the owner (F87).
- **Q7 movie:** from 3 frames up; space pauses; arrows pause then step (up/back/left backward in time).

No invariant changes. Open consequence for the figure agent: none.

### 2026-11-23 — GUI questions answered, batch 2 (8, 9, 2, 5)

Verified by: reading only; decisions, not measurements.

- **Q8 image defaults:** accepted as proposed (log / linear by kind, 99.9th-percentile top with the direct beam masked, per monitor and absorber-corrected).
- **Q9 sticky:** everything sticky across redraws, scans and sessions, reset only by a new SPEC file; Home and Fit all on every axis (F88).
- **Q2 fluorescence burns:** the burn trend of fitted fluorescence line areas per Monc (F89).
- **Q5 XFNTR:** fitted lines by default, from the element; the sum retires if a gauntlet against Rayleigh and Compton scatter (Zn Kα 8637 eV at 10 keV) passes; real data offered by the owner (F90).

**Physics to check when F90 is built:** Zn Kα (8.637 keV) sits below a 10 keV excitation, so the elastic (Rayleigh) peak at 10 keV and its Compton shoulder (10 keV minus 0 to about 0.38 keV, the maximum at 180°; shift ΔE ≈ E²(1−cosθ)/(m_ec² + E(1−cosθ)), Compton 1923, doi:10.1103/PhysRev.21.483) lie 1.4 keV from the line: the detector resolution (about 150–250 eV FWHM for a silicon drift detector) and its tail determine the risk. Not yet measured.

### 2026-11-23 — GUI questions answered, batch 3 (6, 4, EXAFS-2)

Verified by: reading only.

- **Q6 EXAFS:** low priority; Athena/Larch spline above the edge and the usual k-weighted EXAFS plot, hosted in a "process EXAFS" dialog; also an energy-axis line-intensity file, dead-time and absorber corrections, μ(E) normalisation and edge step. Reference for the method: Newville, *J. Synchrotron Rad.* 8, 322 (2001), doi:10.1107/S0909049500016964 (Larch/Athena's background removal, AUTOBK: Newville et al., *Phys. Rev. B* 47, 14126 (1993), doi:10.1103/PhysRevB.47.14126), cited from memory.
- **Q-REF-2 joins:** the owner looks at every join; a bad join with good statistics usually means sample damage. Design consequence: suspect joins are flagged and stay reviewable; no silent auto-accept.
- **Q-EXAFS-2:** unanswered; the owner asked what data would answer it; the request is in `TODO.md`.

### 2026-11-23 — GUI questions answered, batch 4 (Q-UI-A3, A10, A5–A8, Q-IMG-4)

Verified by: reading `mainwindow.py` (the current averaging); nothing run.

- **"Sum All":** sum counts, sum monitors, normalise once (F91). Statistically, for Poisson counts N_i with monitors M_i the pooled rate ΣN/ΣM is the maximum-likelihood rate when the true rate is common, whereas the mean of N_i/M_i weights low-monitor frames too heavily. Invariant to check when built: for equal monitors the new and old values are identical; the sum of the counts is conserved.
- **Greying out** tool groups that do not fit the series kind, with tooltips.
- **GIOXS, 2D_Plot, Calculations, background block:** all stay; each needs more thought.
- **Movie colour scale:** shared, absorber-corrected, per monitor.

### 2026-11-23 — GUI questions answered, batch 5 (Q-IMG-11, 8, 14, 15; Q-GID-1, 5)

Verified by: reading only. Default cuts by kind accepted; nearest-pixel and viridis/magma defaults; the GID map gets its own cached view; GID Patch Relax becomes an option beside the worksheet. **Follow-up for a coding session (not done here):** read what "GID Patch Relax" does differently from "GID Patch" (the larger Q grid, per Q-GID-5's "why") and state it as one option.

### 2026-11-23 — GUI questions answered, batch 6 (elements, dropped points) and merge permission

Verified by: reading only. Elements: dropdown or autocompleting text box (F93). Dropped points: a mask in the config file plus "Restore all" in the patch dialog (F92), closing the open part of Q-REF-2 and D2. The owner also granted standing permission to pull and merge into `main`.

### 2026-11-23 — GUI questions answered, batch 7 (inventory B: B3, B6, B9, B10)

Verified by: reading only. The unwired bad-pixel field and list are wired (corrections shown per Qz; **if the ROI threshold differs from the Pilatus tab's, it changes output numbers and needs an OUTPUT_DECISIONS row when built**). Ref Patch warnings become messages and marks. Save means workbook, Export means text file. Frequent windows are docked. The interview session had asked some questions twice (Q-CUTS, Q-GID-2, Q-GEN-5 against Q-IMG-11 and Q-UI-A7); the owner noticed, so duplicates are checked against the Answers table first.

### 2026-11-23 — Remedying everything the Tools session put on the to-do list (owner: "if you found it you own it")

**Owner:** with standing merge permission: remedy everything added to the
to-dos and report, regardless of whose area it is.

**What was done, and how it was verified (all measured on 2026-11-23):**

- **Stale committed products.** The beam-profile and stray-light figures
  were *not* stale: their own commit (ab33063), run in this environment,
  gives exactly today's pixels; the committed figures had been drawn in
  another environment (library builds, fonts). The audit now tells the two
  apart (`runner.run_item_at`, `classify`) and runs record their library
  versions. Remade with their text: the C2/C3 tables (the error-model
  ratios unchanged in substance, so not confounded as first written), C21
  (now by `compare_methods.py`, `GIDParams(angles=...)`), C24 (written for
  the first time; `COMPARISONS.md` had named a command that did not write
  it), the reflectivity survey (the guard ladder's choices), the GID survey
  (current in substance).
- **g_l2 / g_l3 screenshots** captured again; the dialogs listed scans
  5 and 13 as "6, 14" (an off-by-one since the original program), fixed.
- **Private defaults:** three tools take their files as arguments; their
  pages default to NX.
- **Variations reachable:** pinhole case 8, the monitor Monte Carlo, the
  demonstrator's surveys, synthetic roughness and background.
- **Figures asked for:** burns against dose (F76), the GID level join per
  column group, the GID movie on one 2θ axis (M7).

**Found on the way (P46), and fixed.** The column-group figure showed the
pinhole join factor below the pooled ratio wherever β bins hold few
counts. The estimator was the inverse-variance mean of the bins' ratios,
with each bin's error proportional to its own ratio, so bins that came out
low weighed more. Synthetic two-level sets with a true factor 1.25 (16
seeds): −0.03 % at 2.6 counts per pixel, −1.0 % at 0.13, −4.9 % at 0.026.
Replaced by the factor that maximises the likelihood of how each bin's
counts split between the two sides (binomial given the bin's total:
Σ_b [N_a/f − (N_a+N_b)·W_a/(f·W_a + W_b)] = 0; error from the
curvature): within ±0.1 % at every count level (invariant I31). On NX
11 + 12 the level join moves 1.068 ± 0.013 → 1.088 ± 0.014 (1.5σ; the
upper level has 124 counts per β bin); the scan join of NX 11 split ×0.8
moves 1.2565 → 1.2572 (true 1.25), and the two halves of NX 11 (×1) join
at 0.959 instead of 0.951 ('fit'; beam 0.952 → 0.962, physical+fit
0.962 → 0.970: still not 1, the change along the scan stands; the pinned
characterisation in `test_gid_scan_join.py` updated with these values).
`GIDParams(join_estimator='ivw')`
keeps the old estimator. Every committed GID product was remade and every
quoted number updated with the old beside it (`OUTPUT_DECISIONS.md`,
`COMPARISONS.md` C40).

**Burn: damage or a changing sample (F76), measured on NX 14 and 15.** The
position drifts 3.70× faster in scan 15 against clock time but 0.79× as
fast against dose (Σ Monc × foil transmission; flux ratio 4.68 with the
calibrated foils, 0.90× with the nominal 4.12): nearly coincident against
dose, as a beam-driven change would be; and scan 15 starts where 14 ended.
Two scans cannot prove it (they also differ in time).

### 2026-11-23 — GUI questions answered, batch 8 (B4, B5, B7, Q-IMG-7)

Verified by: reading only. **Invariant to protect when built (live updates):** a join the user accepted must not change when more scans arrive; only a new join may prompt. This is not yet an invariant with a test; it belongs in the invariants table when the join table exists. Open from Q-IMG-7: the cue thresholds (off-centre beyond 25 % of the half-width; clipped above 1 % of the integral at the box edge; background box within 2 px of the signal box) are unconfirmed.

### 2026-11-23 — GUI questions answered, batch 9 (Q-IMG-7, 10, 12, 16)

Verified by: reading only. The saturation limits are per pixel in counts per second (soft 1e5, hard 1.5e5, the owner's figures); the reader must divide a frame's counts by its exposure time, which is not yet checked against the header. For β − α the owner chose the specular angle from Qz: for a specular ray the exit angle equals the incidence angle (α_f = α_i), so β − α measures the diffuse offset from the specular condition even if the sample is tilted, which In_Rot would not.

### 2026-11-23 — GUI questions answered, batch 10 (Q-BURN-2, Q-BURN-5, Q-REF-3, Q-XFNTR-3)

Verified by: reading only. Burn analysis opens by itself with dose-axis and other modes, about four burns at once (F98); the reflectivity ROI is shared and shown. Repeats are summed by counts and monitors (F81), which retires the equal-weight average of the identical-scans merge (a deliberate change of output numbers when built: it needs an OUTPUT_DECISIONS row with before and after values). XFNTR defaults are Qz, the central element and fitted lines. **A two-scan comparison test is wanted (F99), and the test is not chosen.** For two scans on one grid with values y1, y2 and errors s1, s2, the statistic Σ (y1 − y2)² / (s1² + s2²) is χ² with N degrees of freedom if the scans are the same (the standard two-sample χ² for Poisson data, e.g. Press et al., *Numerical Recipes*, 3rd ed., section 14.3, from memory, not rechecked); the reader's errors are correlated through the monitor, which this ignores.

### 2026-11-23 — GUI questions answered, batch 11 (Q-XFNTR-4, 5; Q-EXAFS-3, 4)

Verified by: reading only. XFNTR scan points are never deleted. `_flu.txt` is read by xmodfit and its format is to be frozen (F100). Energy scans are not merged by default. Absorbers are sometimes in during escans, so the absorber factor must be evaluated at each point's energy (F101); today it uses the header energy, which is wrong by up to about a factor 1.7 across 100 eV at n = 52 (the figure from the question, not remeasured here). **Misread question:** Q-XFNTR-4 asked about the MCA spectra, not the Qz scan, so the spectrum browser question is still open.

### 2026-11-23 — GUI questions answered, batch 12 (F99 test, Q-GEN-1, Q-GEN-3, Q-GID-3, Q-GID-4)

Verified by: reading only. **F99:** χ² of the difference. For two scans on one grid, T = Σ(y1 − y2)²/(s1² + s2²) has N degrees of freedom if the scans are the same and the errors are right and independent; the p-value is the survival function of χ²_N at T. Not yet built or tested; when built, test it on synthetic identical pairs (p-values uniform) and on pairs with a known offset. **Q-GEN-1:** ROI and background size sweep through the scripting API (F102); selection stops jumping to SpecPlot (F103). **Q-GEN-3:** GISAXS and GIOXS are both in use and need an upgrade (F104); a follow-up interview is needed. **Q-GID-3/4:** background frames and Form Factor stay, though often unused; the owner ticked both "used" and "not used", and the note resolves it as capability wanted, rarely used.

### 2026-11-23 — GUI questions answered, batch 13 (hand-off 08 data, GISAXS and GIOXS)

Verified by: reading only. The real reflectivity series for hand-off 08 are "not soon"; all data needs are now gathered in `docs/DATA_NEEDS.md` for the owner's non-cloud agent. GISAXS upgrade: cuts, refraction-corrected q mapping and background/beam-stop masking, after a research step. GIOXS is grazing-incidence off-specular scattering (the acronym was not explained anywhere in the window); XmodFit is gaining analysis for it. Examples of both will come later.

### 2026-11-23 — F87 built: the burn kind from Det_Th > 2°

The owner's answer to Q10 (recorded above, batch of the day): "Det_Th >
2° → GID", not the 1° proposed. The code had used 0.001°
(`lss_core.burn.is_gid`): any detector angle off zero made a GID burn.
Now `GID_BURN_MIN_DTH_DEG = 2.0`. A burn between 0.001° and 2° is now a
reflectivity burn. None is on hand: NX school burns 14 and 15 are GID
burns either way, and every burn test, quick and real-data, passes
unchanged. When the macros write a role indicator it is to take precedence
(an assumption until it exists). Verified: tested
(`test_burn_kind_follows_det_th_above_two_degrees`).

### 2026-11-23 — Is "Sum All" as ΣN/ΣM right? (a second opinion), and F91 built with every view per Monc

**Question (owner):** "I did want a second opinion on 'sums as
sigmaN/sigmaM' - it seems right to me but i haven't thought deeply on
it." Then: "finish f91 and make sure that all data is default normalized
by monc, even gisaxs."

**Answer: yes, it is the right estimator for frames that share one rate.**
Let frame i have counts N_i ~ Poisson(λ m_i) in a pixel or a region, with
m_i = M_i/(A_i g_i) its effective monitor (Monc over the absorber factor
and the monitor gain). The log-likelihood Σ_i [N_i ln(λ m_i) − λ m_i] is
largest at λ̂ = ΣN_i / Σm_i, with variance λ/Σm_i, estimated as
ΣN/(Σm)²: the error is √ΣN/Σm. The old "Sum All", the mean of the
normalised frames (1/n) Σ N_i/m_i, is unbiased too, but its variance is
(λ/n²) Σ 1/m_i. Since the arithmetic mean of the m_i is at least their
harmonic mean, that variance is never below λ/Σm_i, and equals it only
when every m_i is the same. ΣN/Σm is the mean of the normalised frames
weighted by m_i/Σm. That is the inverse-variance weighting when the
variances come from the expected counts λ m_i. Weighting by the observed
counts N_i instead would bias low counts downwards. It is the same
estimator as the MCA Merge (I22, notes 2026-11-19) and the pinhole bins
(I21). References: the Poisson likelihood and its maximum, e.g. Cowan,
*Statistical Data Analysis* (Oxford, 1998), ch. 6 (maximum likelihood)
(https://www.pp.rhul.ac.uk/~cowan/sda/); the AM–HM inequality,
https://en.wikipedia.org/wiki/Inequality_of_arithmetic_and_geometric_means.

Caveats, none of which changes the choice:
1. It assumes one rate. Frames that truly differ (beam drift, a burn, a
   wrong absorber factor) are weighted towards the frame with the larger
   effective monitor, not equally. With different absorbers that is
   nearly all of the weight (below).
2. With a background selected, the frames are normalised and subtracted
   first, then weighted by m_i: the same estimator for the signal.
3. The monitor's own noise (0.04 %, D22) is negligible next to the counts
   of summed frames.

**Built (2026-11-23).**
- `lss_core.cuts.sum_frames`, `sum_weights` and `frame_normaliser`.
- `Experiment.cut(summed=True, sum_mode='monitors')` is the default;
  `'mean'` gives the legacy mean.
- In the window, "Sum All" in cuts, the summed image and GISAXS. The
  error budget's monitor terms take the same weights.
- The owner's second request, every view per Monc:
  - the image display and its colour range: they were raw counts unless
    a background was selected;
  - GISAXS single frames and their `_gisaxs.txt`: raw counts before;
  - the SpecPlot normaliser picks Monc by name (it was the column before
    the last).
- Cuts, Ref and the GID maps were per Monc already. Ref's close-up goes
  through `TwoDDetector.setROI`, which divides by Monc. Burn tests do not
  read "Sum All".
- The legacy behaviour stays as two preferences for F86's Reduction
  options page: `sum_all_legacy_average` and `gisaxs_raw_counts`.

**Measured on NX school** (C41, `python tests/tools/compare_methods.py`;
a 'Pix V' cut over the whole width, new vs old):

| Frames | Total | Peak row | σ at the peak, new/old |
|---|---|---|---|
| Scan 11, 41 repeats at Qz 0.016 (monitors within 1.5 %) | +0.032 % | −0.020 % | 0.9998 |
| Scan 12, 4 repeats | −0.000 % | −0.002 % | — |
| Scans 7 + 8 at Qz 0.09 | +1.2 % | +19.7 % | 0.36 |
| Scans 8 + 9 at Qz 0.17 | +4.0 % | +5.0 % | 0.39 |
| Scans 6 + 7 at Qz 0.035 | +10.9 % | +10.7 % | 0.47 |

- The cross-scan pairs are at different absorbers, with the default
  factor of 1.4247 per unit.
- The two frames of a pair disagree with each other by 2.5 %, 9.0 % and
  26 %. The new sum gives the less-attenuated frame 96–98 % of the
  weight.
- For repeats, the usual use, the change is below 0.04 %.

**Also found:** "Show GISAXS" raised with the direct beam at the
detector's centre (OverflowError) or right of it (ValueError). The
cause was the Qxy bin count, from (last − first) of a row whose |Qxy|
folds at the beam. It is fixed, and left of the centre it is unchanged
(`test_gisaxs_display.py`).

**Owner, same day: undersampled fringes are not a case to consider.**
"fringes will rarely be undersampled, or even be sampled close to
nyquist, that is not an important case to consider." The to-do item to
fall back to the coinciding-points ratio at undersampled joins (from
the gauntlet, C36) is dropped.

Verified by tests (I32; `test_monc_normalised.py`,
`test_gisaxs_display.py`) and measured (the table above). That the
display, GISAXS and SpecPlot were raw before is from reading the code.

### 2026-11-23 — The fragility audit: column positions and other hard-coded assumptions

**Question (owner), after the SpecPlot normaliser turned out to be "the
column before the last":** "any other column position lookups or similar
hard-coded and fragile issues in the code?"

**Answer.** The full list, with fixes, is in `TODO.md` area L. Ranked by
harm:

1. **A half-written last data line loses the whole scan.** Every data row
   of a scan must have as many numbers as `#L` has labels. If the last
   line is cut short, every column of that scan becomes None. This
   happens whenever SPEC is still writing the file, which is exactly the
   live-update case.
   - Measured: a synthetic file with its last line cut after two numbers
     reads as a scan with no columns.
2. **Stale incidence angle (P47).** The incidence angle of every frame is
   the scan header's `In_Rot`, which is written before the scan moves.
   For specular hklscans that is wrong for every frame.
   - Measured on NX school scan 6: the header gives 0.0906°, while α from
     L runs 0.0989–0.2261°.
   - So the specular pixel's β comes out as 0.107–0.362° instead of
     equal to α. In scan 7 it comes out as up to 0.947° instead of
     0.565°.
   - This affects cut axes and GISAXS of such frames, not the Ref Patch
     sums. GID (dth) scans are right.
3. **Data read back from list text.** Frame and scan numbers are parsed
   from the text of the list widgets: 13 places in the image list, 8 in
   the scan list, and the Ref Qz list. Any change to the displayed text
   in the GUI overhaul breaks them silently. (Read only.)
4. **Pilatus 100K sizes are hard-coded.** The default cut ranges are
   0:485 and 0:194, the last GID row is 486, the column spin box stops at
   195, and 0.172 mm is written 22 times in `mainwindow.py`. All of this
   is wrong for the 1M. (Read only.)
5. **Path and name parsing.**
   - Image and MCA file prefixes are made with `split('/')`, so a path
     with backslashes (Windows) gives the wrong prefix. (Read only.)
   - The `#B0` extension check fails for a SPEC name containing a dot,
     and the scan is then read as a monitor scan without images.
     (Measured.)
6. **Fragile but right for the current macros.**
   - **`#L` labels are split on any space, with no count check.** NX
     writes "PSD Seconds" with a single space, and its rows do have 18
     values, so the split is right. A label with a space would shift
     every later column silently. (Measured on NX.)
   - **Motor names are the macro's 8-character truncations**
     (`Two_Thet`, `Sample_T`), and the full names in `#O` are unused.
     (Read; NX headers.)
   - **`#A` and the `Absorber` motor both set the absorber**, and the
     later line wins; in NX that is `#A`. (Read; NX order.)
   - **SpecPlot's default x is column 2 (L) for every hklscan**, and its
     default y is the last column. (Read only.)
   - **L is taken as Qz in Å⁻¹, and H as Qx.** This holds for the
     beamline's SPEC lattice: on NX scan 11 (fixed α), L = 4π sin(In_Rot)/λ
     to 0.06 %. A changed lattice would scale every Qz silently. (Measured
     on one scan.)

One worry was checked and dropped: `#P10` and later motor lines. The
parser's `line[4:]` handles indices up to 99. (Tested on a synthetic
header.)

Verified as marked: items marked measured were run on NX school or on
synthetic files today; the rest come from reading the code. None is
fixed yet. The first two change results; the rest are latent.

### 2026-11-23 — GUI questions answered, batch 14 (Q-REF-5, 6; Q-BURN-4, 6; blank spectra)

Verified by: reading only. Comparisons of reduced curves move toward a workbook-fed tab that auto-updates (F105, F80). Export proposes a name and hands over to xmodfit. The burn Legacy tab goes behind the Reduction options; GID-burn rows default from the mean frame. **Data:** no zinc spectra will exist; other elements and blank spectra will come, so the F90 gauntlet's hard case (Zn Kα under 10 keV scatter) can only be tested on a nearby real case plus the synthetic generator, with a blank used to check the generator's escape-peak and Compton profiles.

### 2026-11-23 — NX 6–9 under today's patch default: join 2 flagged (tools man, for Main)

Verified by: run (`patching.chain` on `Experiment(NX).reflectivity([6, 7,
8, 9], errors='budget')`) and test (`test_patching.py::test_nx_school_scans_6_to_9`,
which now pins both sets of numbers).

The test pinned report §6.1 (2026-11-22). That report used `n_ext=4,
guard_p=0.01`. The gauntlet of the same day then made `n_ext=2,
guard_p=0.3` the default, and the test has failed since. It now passes
the old settings explicitly, and it pins today's default beside them:

| | §6.1 settings (n_ext 4, guard p 0.01) | today's default (n_ext 2, guard p 0.3) |
|---|---|---|
| factors 6→7, 7→8, 8→9 | 0.023004, 0.064516, 0.103604 | 0.022980, 0.064474, 0.103695 |
| level of scan 9 / scan 6, relative error √Σ₃₃ | 0.75 % | 0.85 % |
| join 1: order, points either side, χ²/dof | 4, 4, 0.88 | 4, 2, 0.68 |
| join 2 | 4, 4, 1.10; error 0.00501 (counting 0.00479) | 4, 2, 1.37; **flagged**, error 0.00616 (counting 0.00527, ×1.17) |
| join 3 | 4, 4, 1.37 | 4, 2, 0.83 |
| with 6 points either side, join 8→9 | window stepped down (χ²/dof 60, before the ladder raised orders) | order raised to 6, 6 either side (χ²/dof 1.15), "the first adequate fit" |
| foil prior (monitor ratios 1.005, 4.35, 1.32) | used at join 1 only; join 2 "Monc/Monp changed ×4.350" | the same |

**For the owner:** on the one real series in the repository, the default
patch flags join 2 (scans 7→8). The flag reads "no adequate fit (χ² p <
0.3 everywhere): order 4, 2 either side, χ²/dof 1.37, error inflated".

- At the guard's p of 0.3, no window or order the ladder tries fits
  well enough, so the join's error is inflated by √(χ²/dof), ×1.17.
- At the old p of 0.01 the same join passes (χ²/dof 1.10 with 4 points
  either side).
- The factors agree to 0.1 % between the two settings (0.064474 against
  0.064516, inside either error).

So the flag is the stricter guard showing a modest misfit. It does not
signal a wrong factor. Whether p = 0.3 is too strict for real data,
where the model (a smooth curve under the overlap) is never exact, is
for the owner to weigh. The gauntlet chose it on synthetic data (C36).
The real-series comparison of hand-off 08 (DATA_NEEDS row 1) is the test
that would decide. Nothing was changed.

### 2026-11-23 — What "the gauntlet" is, whether it is wrapped up, what it needs (owner, through Main)

Verified by: M = measured (a run or a test), R = reading only, marked
per statement.

**Question (owner, through Main):** "what 'the gauntlet' is, whether it
got wrapped up and what extensions it needs".

**What it is (R).** `tests/tools/ref_patch_gauntlet.py` runs every
reflectivity patching method on many noise replicates of synthetic
reflectivity with known truth (`tests/synthetic`):
- Parratt reflectivity with water's critical edge and Kiessig fringes;
- the reader's ROI boxes, foils, monitors and planted faults.

It has three designs:
- seven core conditions;
- a grid, one factor at a time from a 100 Å film on water;
- 150 random conditions.

It judges every join by hand-off 08's rule: |mean pull| < 0.2, pull SD
0.90–1.15, no failed fit. It also follows the reader's own path
(`reflectivity.patch`). It is what made the joint fit the default
(owner, 2026-11-22: "make new method the default if it passes the
gauntlet"; C36, OUTPUT_DECISIONS). F90's MCA line-fit gauntlet is built
the same way (C42).

**Wrapped up: yes; the records were not quite right.**
- (M) Rerunning the committed run, `--design all --methods key`, gives
  every committed table back, row for row.
- (M) The default (`joint_o4_e2`) passes 139 of 155 designed joins. Of
  the 16 that fail, 5 fail by bias (|mean pull| ≥ 0.2). It passes 415 of
  463 random joins.
- (R) Three records gave a command that does not make those tables. C36
  and the entry of 2026-11-22 gave `--design all` alone, whose default
  `--methods all` adds rows. The Tools catalogue named a method that does
  not exist. All are corrected, and the summary's header now prints its
  `--methods`.
- (M) Three real-data tests had failed since the default changed. They
  are fixed; the slow suite gives 484 passed.

**Extensions, ranked, with their status:**
1. The three failing real-data tests. **Done** 2026-11-23, without
   weakening any:
   - the reference test and the self-test choose the legacy patch, whose
     output their fixtures are (rule 3);
   - `test_patching` pins both the §6.1 settings and today's default.
   - Finding (M): today's default flags join 2 of NX 6–9 (the entry
     above).
2. The record defects. **Done** 2026-11-23 (above).
3. Hand-off 08 on the owner's real reflectivity series with many joins,
   the real test of the default. **Waits on data** (`DATA_NEEDS.md` row
   1; questor asks the owner).
4. Explain the five biased designed joins, and the pull SD of 1.13 at the
   first join of the downstream-covariance study (`TODO.md` B). **Next**,
   after F90.
5. A fallback to the coinciding-points ratio where fringes are
   undersampled. **Dropped** by the owner on 2026-11-23. Main recorded
   the owner's words at the end of its F91 entry ("Owner, same day:
   undersampled fringes are not a case to consider"), and `TODO.md` B
   strikes the row.
6. and 7. **Parked** by Main.

### 2026-11-23 — F90, the MCA line-fit gauntlet: synthetic half (tools man, for Main)

Verified by: runs on synthetic spectra, `tests/tools/mca_fit_gauntlet.py
--design all --replicates 200`, outputs in
`docs/comparisons_data/mca_fit_gauntlet/`, C42; tests for the pieces,
`test_mca_fit_gauntlet.py` and `test_synthetic_mca.py`. The generator's
physics (`tests/synthetic/mca.py`) is textbook. Two of its sizes are from
memory and are marked so there: the O 1s Compton wing (a hydrogenic
impulse-approximation profile with p0 = Z_eff = 7.7 a.u., cut off at
E0 − 0.532 keV) and Reed's escape fraction (0.10 % at 10 keV, 0.15 % at
8.6 keV).

**Question (owner, F90):** does a fitted line hold against the
direct-beam scatter (Rayleigh, Compton), the hard case being Zn Kα under
10 keV excitation? If it does, the window sum retires.

**What lies under Zn Kα** (8.631 keV intensity-weighted, box ±2 FWHM =
8.26–9.00 keV; 1e3 Zn photons on 1e6 elastic):
- the valence Compton tail, rising as ΔE⁻⁶ toward the Compton peak at
  9.81 keV (90°);
- the elastic's Si escape at 8.26 keV, about as large as the line itself
  (1015 counts against 887), and the Compton's broad escape at 8.07 keV;
- the O 1s wing, which in a ±3 FWHM box gives about 14k counts, 16 times
  the line;
- shelves and tails;
- with copper about, Cu Kα (8.048 keV) and Kβ (8.905 keV, inside the box).

**Answer, synthetic.** Judged by hand-off 08's pull rule, or |bias| < 1 %
against the true line.

- **The window sum never holds once scatter lies under the box.** It
  reads +21 % on the smooth baseline and +886 % in the hard case. It
  distorts XFNTR curves: in the hard series the ratio to the truth runs
  from 0.76 below Qc to over 1.5 above it. Side-band subtraction does
  worse, because the bands sit on the curved Compton tail (about −60 %).
- **The reader's "Fit lines" holds on a smooth background.** On the
  smooth baseline it reads −0.4 %, with pull −0.1 / 1.03, and the smooth
  XFNTR curve stays within 0.8 %. It also holds at FWHM 130–220 eV,
  line/elastic down to 3e-3, Compton/Rayleigh 0.3, a 60° angle, Kβ ×1.25,
  and series of 1 to 30 spectra.
- **It does not hold against** (bias against the true line):

  | Factor | Bias of the reader's fit |
  |---|---|
  | the elastic's Si escape at Reed's 0.1 % | +45 % (the free width trades off against it); with the centre fixed, −0.6 % |
  | O 1s Compton wing at 2 % | −3.7 % |
  | O 1s Compton wing at 20 % | −31 % |
  | valence Doppler width 0.3 keV | −10 % |
  | Neyman bias, 270 counts | −5.8 % |
  | Neyman bias, 90 counts | −21 % |
  | ±3 FWHM box (the Compton tail curves across it) | −3 % |
  | calibration offset ±30 eV | ∓3 % |
  | gain ±0.5 % | −3 % / +5.5 % |
  | detector tail 3 % | −3.8 % |

  None of the candidates handles the core wing either. The fixed width,
  stripping and placed peaks all give −1.6 % at 2 % and −12 % at 20 %.
- **Candidates** (not defaults; for Main to take to the owner):
  - (1) **A Poisson (model-weighted) per-spectrum step**, which is
    `fit_series`' linear step iterated with σ² ∝ the model, i.e. the
    Poisson maximum likelihood. It removes the Neyman bias: −21 % → +3.6 %
    at 90 counts, −5.8 % → +0.6 % at 270, and the weak XFNTR curve's
    worst point 12.9 % → 1.4 %.
  - (2) **The width fixed from the detector's resolution.** Calibrate the
    noise on the elastic peak; the Fano term gives the rest. It passes
    1 % tails, shelves, backgrounds and offsets up to 10 eV, which the
    free width fails. A 3 % error in the assumed width costs 2.5 %.
  - (3) **Si escape stripping** (subtract f(E + 1.740)·y(E + 1.740)), or
    placing the escape peaks. Either cuts the escape bias to 3–4 %.
    Stripping plus the fixed width passes both hard XFNTR curves (worst
    points 0.74 % and 0.49 %), where every other estimator fails.
  - (4) **A box of ±2 FWHM**, not ±3, when F90's editable box gets its
    default.
  - (5) **"Fit lines" must report the element's line**, not the tallest
    peak (`mcaFitLines` takes `r.peaks[0]`), once several lines are
    placed.
- **Overall:** no estimator passes F90 on synthetic data. Of the
  in-range random conditions (all features at once), the window passes
  1 %, the reader's fit 28 %, the best candidate (stripping + fixed
  width) 38 %.

**What decides it on real data:** how large the elastic's escape peak and
the Compton wing under the line really are. A blank (pure water or the
subphase) at the same Qz measures both. It is passed to questor for
`DATA_NEEDS.md` row 3 together with the owner's offered spectra. No
default was changed.

**Invariant:** I33 (the invariants table).

### 2026-11-23 — P47 fixed: each frame's own incidence angle

From the fragility audit above, item 2.
- **The cause.** The scan header's In_Rot is written before the scan
  moves. Every frame took it as its true incidence, so in specular scans
  the exit angle of the reflected beam, β = arcsin(2 sin α − sin α_true),
  was not α.
- **The rule now** (`lss_core.cuts.true_incidence`):
  - a scan with H = K = 0 throughout (|H|, |K| < 1e-4; NX's largest is
    4.2e-7) and L not constant is specular, and takes α = arcsin(L λ/4π)
    per frame;
  - every other scan keeps the header's value: GID and ih scans, and
    height scans;
  - an In_Rot column, if a macro ever writes one, wins.
- **Where it applies.** The window (`pilTrueAlpha`), `Experiment.cut` and
  the GID frames use it.

**Measured on NX school, β at the reflected peak, old → new:**

| Frame | α | Old | New |
|---|---|---|---|
| Scan 6, first | 0.0989° | 0.1073° | 0.0989° |
| Scan 6, last | 0.2261° | 0.3616° | 0.2261° |
| Scan 7, last | 0.5653° | 0.9469° | 0.5653° |
| Scan 8, last | 1.0741° | 1.6679° | 1.0741° |
| Scan 9, last | 2.5447° | 4.1870° | 2.5447° |

- The β values are from an Angles cut through the beam's columns.
- **Qz axes barely move.** Qz = k(sin α_true + sin β) cancels α_true at
  the reflected row: scan 6's Q V cut range goes from −0.0438…0.7185 to
  −0.0438…0.7186.
- **Fixed-incidence scans are identical to the last bit.** C10 was
  regenerated without a change.
- **Not measured:** GISAXS maps of specular frames, whose Qxy goes through
  cos α_true.

Verified by tests (I34, `test_true_incidence.py`) and measured (C43,
`docs/comparisons_data/C43_incidence_nx_S6-7-8-9.csv`).

### 2026-11-23 — F81 built: repeats merged as counts over monitors

The owner's workflow (F81): "getting data and deciding if we need better
statistics (repeat the macro (multiple scans) and have reader handle
summing the ROIs if we want it to".

**What changed.** The identical-scans "Merge" and
`exp.reflectivity(merge=..., merge_repeats=True)` now sum each point's
counts and monitors, then normalise once:
- R = Σ M R / Σ M;
- σ = √Σ(M σ)² / Σ M.

This is ΣN/ΣM per point, for the same reasons as "Sum All" (the entry
above, I32).
- The first scan of a group keeps the summed monitors, so merging one
  repeat at a time gives the same result as merging them all at once
  (tested).
- The old equal-weight mean stays: `repeats='mean'` in scripts and the
  preference `repeats_legacy_average`. The Script pane shows it when it
  was used.
- Repeats are still found as before, by the same Qz range and the same
  number of points.
- An open caveat: repeats taken at different absorbers would be merged
  without a check, as before.

**Not measured on real data.** The public data hold no repeated
reflectivity scans. With equal monitors the result is the old average;
otherwise each repeat weighs by its monitor.

Verified by tests (`test_repeats_merge.py`: the core function, the
script, the window and the legacy preference). Measured: none.

### 2026-11-24 — Why five gauntlet joins are biased, and the first join's pull SD of 1.13 (tools man, extension 4)

**Correction (2026-11-24, from Main's study A; reported by Main, not rerun here):** over 2000 seeds the first
join's pull SD at p 0.3 is 1.00. The 1.13 of the first 300 seeds below was mostly sampling noise, so the
"post-selection" explanation of it does not stand. The measured rung shares and the biased joins' model
bias are unaffected. Study A (`docs/studies/reflectivity_guard/`) has the guard's full sweep.

Verified by: runs. The command is `tests/tools/ref_patch_biased_joins.py --out
docs/comparisons_data/ref_patch_biased_joins`, with 400 replicates per
join on the gauntlet's own seeds; the default's pulls come back exactly as
committed in C36. The study is C45.

**The five biased designed joins** of the default (`joint_o4_e2`; the
not-undersampled ones of C36) are layer_dppc j3 (−0.21), layer_film150
j2 (−0.31), overlap_3_staggered j3 (+0.25), overlap_6 j1 (+0.24) and
scans_5 j2 (−0.33). They are model bias, not noise:
- **Noise-free bias.** Fitting the same plans without noise
  (`expected=True`) leaves the default off by −1.03, −0.64, +0.27,
  +0.73 and −0.63 of its median error, at the order and window it
  chooses there.
- **No fixed order or window removes it everywhere.** Order 4 with
  2 either side gives +0.42, −0.42, +0.27, +0.57, +0.01. One point
  either side helps overlap_6 and scans_5 (−0.09, −0.11) but not dppc or
  film150 (−0.65, −0.49).
- **The ladder mixes opposite biases.** Near a fringe every polynomial
  order is somewhat wrong, and the ladder picks different rungs on
  different noise. In layer_dppc j3, order 7 (43 % of replicates) has a
  mean pull of +0.39 and order 6 (28 %) −1.26.
- The log likelihood changes nothing.

**The first join's pull SD of 1.13** (the downstream-covariance study,
C35: 25 Å film, NX-like plan, 300 seeds) comes from the guard ladder's
post-selection:
- 75 % of seeds pass p ≥ 0.3 at order 4 with 2 either side, the same
  fit as without the guard (pull SD 1.10).
- The other 25 % fail there. The ladder then accepts the first rung
  whose χ² looks adequate (orders 5–7, or a smaller window), and those
  rungs' errors are too small (pull SD 1.17–1.62).
- Without the ladder, the same seeds keep order 4 with their error
  inflated by √(χ²/dof), and the pull SD is 1.05. The guard at p 0.01
  also gives 1.05. The noise-free bias is 0.

**For the owner, a trade-off** (no default changed; sent through
questor):
- The stricter guard (p 0.3, the default) keeps the biased joins
  smaller.
- The looser one (p 0.01) makes them worse (−0.68, −0.70, +0.25, +0.51,
  −0.61) but cures the 1.13.
- A third way would give the accepted fit an error that accounts for
  the choice, for example the spread of δ over the adequate rungs. It is
  not built.

### 2026-11-24 — Decisions on the MCA line fit (P1–P4) and the patching guard, asked for the tools session (batch 15)

Verified by: reading only. The numbers are the tools session's, measured on synthetic data (COMPARISONS C42, C45, and its physics_notes entries "F90, the MCA line-fit gauntlet: synthetic half" and "Why five gauntlet joins are biased"); they were not rerun here.

- **P1 adopted** as the default: with counts N_i and model μ_i the Poisson maximum-likelihood condition for the linear coefficients is Σ (N_i/μ_i − 1) ∂μ_i/∂a = 0, weighting by the model instead of by the data N_i, which is what biases low-count areas low (a data-weighted least-squares gives smaller weights to fluctuations upward, so areas come out low; see Cash, *Astrophys. J.* 228, 939 (1979), doi:10.1086/156922, from memory, not rechecked). Legacy weighting stays behind the Reduction options.
- **P2, P3:** options now, defaults only after blank spectra (DATA_NEEDS row 3).
- **P4:** after the blanks.
- **Guard:** needs further study; p stays 0.3; the real test is hand-off 08 (not soon).
- **Numbering clash to note:** the tools session called the blank-spectrum request "F105"; F105 here is the comparison tab with auto-update. The blank spectra are F90's data (DATA_NEEDS row 3).

### 2026-11-24 — GUI questions answered, batch 16 (Q-XFNTR-4, Q-UI-A9, Q-CUTS-3, Q-TL-1)

Verified by: reading only (the SPEC command names are the owner's; not checked against a SPEC file here). No MCA spectrum browser. Reflectivity frame series default to a ROI-zoomed movie. α_f is reserved in the cut interface. New samples on the timeline are detected from `setup_sh_scan`, sh movements and `set sh 0`, asked of the user on the timeline (F106). This begins the timeline questions Q-TL-2–8, which remain open.
  - *Resolved (Main, 2026-11-24).* Every use of "F105" on main was checked (a search of `docs/`, `tests/` and `lss_*`). None calls the blank spectra F105 any longer: tools man corrected `docs/reports/tools_man_handoff.md`, and the study B summary and DATA_NEEDS row 3 use F90. F105 itself, the comparison tab with Export's proposed names (Q-REF-5, Q-REF-6), was not on TODO until 2026-11-24. It is now in TODO area B, for the GUI manager after timeline 1c.
- *Since (Main, 2026-11-24).*
  - The owner asked for full studies before these decisions stand (entry "The owner asks for full studies…"). So P1's default switch is **held**: P1, P2 and P3 are options, and today's weighting is still the default.
  - Study B (`docs/studies/mca_fit/summary.md`, C47) recommends P1 as the default.
  - Study A (`docs/studies/reflectivity_guard/summary.md`, C48) recommends raising the guard to p 0.7.
  - Both wait for the owner's answer, which questor records.
  - Cash 1979's DOI above is confirmed from the index record; the full text is not read.

### 2026-11-24 — L as Qz: the convention, written down and checked at load (tools man, area L)

Verified by: run and test on NX school (`test_lattice.py`). The
convention was read from the data, not from the beamline's SPEC
configuration, which is not in the repository.

**The convention.** H and K are the in-plane components; L is Qz in Å⁻¹:
L = (2π/λ)(sin α + sin β), with α the incidence (header `In_Rot`) and β
the exit angle (header `Out_Rot`). In a specular scan α = β, and
L = 4π sin α/λ.

**Measured on NX school.** Every scan at fixed L agrees with its header
angles to better than 0.001 %:
- scans 4, 5, 10, 13–15 (specular);
- scan 11, the GID low level. The fragility audit's 0.06 % came from
  using α twice: In_Rot is 0.0905° and Out_Rot 0.0906°;
- scan 12, the raised GID level, where β = 6.5° and L = 0.582 Å⁻¹.

Scans whose L moves (the hklscans) are not checked.

**The check (invariant I35).** At load, a fixed-L scan whose L differs
from its angles by more than 1 % gets `LMismatch` (the relative
difference) in its parameters, and the window says so once. Only scans
whose header gives both In_Rot and Out_Rot are checked: without the
exit angle, a raised detector arm would look like a wrong lattice
(scan 12). It asks
whether the SPEC lattice is the usual one. Nothing is changed:
reductions keep using L.

### 2026-11-24 — The owner asks for full studies of the guard and the MCA fit decisions

**Owner, after answering batch 15:** "I want a full study (is real data
needed? Better synthetic? Show some synthetic data replicates and their
fits! Show me stats in graphical form!) illustrations, and a ELI5
rationale document with latex equations for those two decisions. But
this will have to wait until 1am."

**Answer: planned, not yet done.** The plan is
`docs/studies/2026-11-24_two_decisions_plan.md`:
- study A, the reflectivity join guard (C45, C36);
- study B, the MCA line intensity (F90, C42);
- each answers the same five questions, the second and third being
  whether the synthetic data are good enough and whether real data are
  needed;
- each comes with figures of replicates and their fits, and statistics
  in graphical form;
- an ELI5 rationale with LaTeX follows both.

The work starts at 1:00 am America/Chicago, from a reminder in the Main
session. Until the studies are in, the batch 15 decisions are recorded
but **P1's default switch waits**: tools man builds P1, P2 and P3 as
code paths with today's weighting kept as the default.

Verified: nothing yet (a plan).

### 2026-11-24 — F96 built: Back, Cancel and the join table in the Ref Patch window; the line under the Reflectivity plot

The owner's answers Q-UI-B7 and Q-UI-B5 (batch 8, above) are built in the
main window. Verified by: tested (`tests/test_gui_ref_patch_steps.py`, 13
tests), not yet tried by the owner.

- **Back** undoes one step at a time: a Drop, or a join accepted with Next.
  Each step first saves a copy of everything it changes (the scans' arrays,
  which the joins scale in place, hand-off trap T3; the curve joined so far;
  the scales, known-ratio factors, drops and choices). Back puts the copy
  back, so a join comes back as it was left, its drops kept. **Invariant
  I36:** Back and redoing the same steps gives the same curve, value for
  value (tested on a three-scan synthetic patch with two drops).
- **Cancel**, Esc, or closing the window (or the identical-scans window)
  stops the patch and says so in the Messages pane: at which join, and that
  the Reflectivity tab is unchanged; the log lists the joins accepted.
  **A defect went with the old silent close:** the patch had already
  replaced what describes the result on show (drops, factors, method,
  merged repeats, the command line), so after a closed patch the Script
  pane and the workbook recipe described the abandoned patch, not the curve
  on show. A stopped patch now puts them back (tested: the Script line is
  the same before and after a cancelled patch with a drop).
- **The join table** lists each join: scans, factor ± error, its source in
  the words of the script (`joint`, `legacy`, `known ratio`, so that a live
  replay can rebuild it, Main's request), the dropped points, the fit's
  note. It is kept with the result and saved in the workbook's Saved
  settings (`joins`).
- **The line under the Reflectivity plot** (Q-UI-B5): patch method, error
  model, absorber model, scans, dropped points and the saved version, as
  the result was made (a later change of preference does not alter it);
  the joins and details in its tooltip. "saved vN" is read only from a
  workbook already in memory (opening one can take seconds).

**Seen in passing (measured, synthetic; corrected the same day):** first
read as an effect of an unmerged repeat, it is a drop: dropping the **new
scan's first point** (Drop "0") at a join leaves dR NaN or inf from there to
the end of the curve, in the window and in `Experiment.reflectivity`, with
the joint and the legacy fit, on main before F96 (7b9a22b) as on this
branch. `synth.make_dataset` scans 1, 2: 6 of 14 points from Qz 0.05;
with the repeat (scans 1, 2, 3): 8 of 14 from Qz 0.04; drops −1 or 1, or no
drop: all finite. Pinned by the strict xfail
`tests/test_drop_first_point_errors.py`; handed to Main, not fixed here.

### 2026-11-24 — F95 (part): Ref Patch checks as one message and marks; the Bad Pixels list wired

The owner's Q-UI-B6 and the list half of Q-UI-B3 (batch 7). Verified by:
tested (`tests/test_gui_ref_checks.py`, 5 tests, on a synthetic set with
one frame's beam drawn 5 px off and with corrected pixels injected into
one frame's box), not yet tried by the owner.

- The two modal boxes (beam centre more than 2 px off; corrected bad
  pixels inside the signal box) are gone. One message names the frames;
  the log has each frame's numbers.
- The flags belong to the result: they are promoted when the patch goes on
  show and kept through a cancelled patch, as the F96 join table is.
- Marks are placed by matching each flagged frame's Qz to the curve's Qz
  (within 5e-5 Å⁻¹; Qz steps are ≥ 1e-3 Å⁻¹ in every set seen): a point
  merged at an overlap carries the mark, and a dropped point has none.
- **No output number changes**: the checks only report. **Not built:** the
  separate ROI threshold of B3 (the tab's "Bad Pixel Correction fac"
  field), which would change numbers and then needs an OUTPUT_DECISIONS
  row.

### 2026-11-24 — F74 built (first plots): residual panels above fits

The owner's request of 2026-11-22 (a small residuals plot above every plot
that shows a fit, about 15 % of the height, χ² in the legend, hidden by
default). Verified by: tested (`tests/test_residuals.py`, 6 tests), not
yet seen by the owner.

- **What is drawn:** (y − fit)/σ for the points inside the fit's window,
  as in decay fitting (Lakowicz, *Principles of Fluorescence
  Spectroscopy*, 3rd ed., Springer 2006, ch. 4; from memory, not rechecked
  — still the assumption recorded with F74). Where a σ is missing or zero,
  y − fit, and the axis label says so.
- **Invariant I37:** the panel's residuals are the ones the fit minimised:
  their squares sum to χ²/dof × (N − p). Measured on a synthetic Poisson
  peak (61 points, peak plus linear background): N − p is an integer, p
  between 3 and 8; mean residual within 0.5 and SD between 0.6 and 1.5 (a
  weighted fit with σ = √y; the reason to expect SD ≈ 1 is that each
  weighted residual of a right model is approximately N(0, 1), Bevington
  and Robinson, *Data Reduction and Error Analysis*, 3rd ed., ch. 8, from
  memory).
- **Where:** SpecPlot scan fits (`peaks.fit_scan`) and the cut peak fits
  (`fitCuts`), with one switch, View > Residuals above fits (preference
  `fit_residuals`, default False), and one helper (`lss_core/residuals.py`,
  matplotlib only) for the other fit plots to use. No output number
  changes.

### 2026-11-24 — F97 (part): the saturation cue on Pilatus frames

The owner's Q-IMG-10 (batch 9): per pixel, soft limit 1e5 counts/s, hard
limit 1.5e5 counts/s ("absorber needed"). Built as a display cue only:
`lss_core.display.saturation` divides a frame's **raw** counts (as read,
before monitor normalisation) by the point's SPEC `Seconds`, and the
window colours the pixels above each limit over the frame, with a note in
its corner. Verified by: tested (`tests/test_saturation_cue.py`, 5 tests:
the limits, the overlay, a synthetic frame of 1e6 counts in 1 s marked
red, a frame of about 1e3 counts unmarked, the drawn and raw frames
unchanged).

**Still open (from batch 9):** the exposure time is taken as SPEC
`Seconds`, which is what the macros count for; not checked against the
TIFF header's own exposure time. Whether the Pilatus counts are already
rate-corrected by the detector is not known; if they are, the true
incident rate is higher than shown. No output number changes.

### 2026-11-24 — F74 on burn trends

The burn test's trend panels get the residual panel too
(`lss_core.burn.plot(..., residuals=True)`, from the window's View >
Residuals above fits): above each quantity, the best model's (y − fit)/σ
over every frame, with "best: <model>, χ²/dof" in the panel. Verified by:
tested; measured on the synthetic burn (`synth.make_burn_dataset`, scan
1): Σr² equals each model's χ² as the trend fit reports it (constant
1.032e6, linear 4734, exponential and double exponential 1.9e-4, the
synthetic decay being noiseless), so the σ drawn is the one fitted (ĉ = 1
here; with ĉ > 1 the fit's covariance is scaled but χ² is not). No output
number changes.

### 2026-11-24 — F78 / timeline phase 1a: the super-Gaussian fit of sample-height scans

**Question (owner, F78):** is a sample-height scan wide enough and "more
squashed than a gaussian", flat-topped? **Built:**
`lss_core.peaks.fit_super_gaussian`, I = A exp(−|(h − h0)/w|^p) + b with
FWHM = 2 w (ln 2)^(1/p). p = 2 is a Gaussian; larger p is flatter. This is
the higher-order Gaussian, the shape of the generalised normal distribution
(Nadarajah, J. Appl. Stat. 32, 685 (2005),
[doi:10.1080/02664760500079464](https://doi.org/10.1080/02664760500079464);
the flat-top beam use, e.g. Shealy and Hoffnagle, Appl. Opt. 45, 5118
(2006); both cited from memory, not rechecked).

- **The FWHM error** propagates the covariance of (w, p): ∂F/∂w = F/w and
  ∂F/∂p = −F ln(ln 2)/p², with ln(ln 2) = −0.367.
- **The guard** (research §2): a peak less than 10σ above the edges, or
  fewer than 3 points above half the peak, means no reflected beam, and the
  fit is refused.
- **Verified by:** tested (`tests/test_super_gaussian.py`, 6 tests), and
  measured:
  - synthetic Poisson scans (FWHM 80.8 µm, p 3.4, 41 points), 300 seeds:
    FWHM pull mean 0.02 and SD 0.95; p pull SD 0.98; χ²/dof mean 1.015. The
    errors are right.
  - NX school (Pilatus/Monc, Poisson errors): scan 5 FWHM 82.1 ± 0.5 µm,
    p 3.36 ± 0.08; scan 10 81.1 ± 0.5 µm, p 3.38 ± 0.08; scan 13
    81.5 ± 0.5 µm, p 3.53 ± 0.09. A Gaussian's χ²/dof is 28–34 against
    2.6–5.2. Scan 4: no reflected beam. These are the research's numbers.
- **The box shape** that `fit_scan` already chooses for these scans gives
  the same widths to 0.2 µm, with a better χ² (COMPARISONS C46). The
  super-Gaussian's gain is the flatness number and the Gaussian comparison.
- **On screen:** SpecPlot draws it on a sample-height scan plotted against
  sh, with FWHM (µm), p and both χ²/dof on the title's last line. The
  existing fit is unchanged.
- **No verdict:** the owner gives the thresholds. No output number changes;
  the fit is not saved.

### 2026-11-24 — F83 phase 1b: the timeline model (lss_core.timeline)

Built from the research's measured facts (`docs/gui/timeline/research.md`
§1–3). Verified by: tested (`tests/test_timeline.py`, 6 tests: NX
school, and a synthetic file for header comments, a SPEC session restart,
a gap, and a missing time zone). Measured on NX: `timeline.build` takes
36 ms and finds:

- the `set sh 0` after scan 4 at 10:37:39 local (Sample_H −0.61 → 0, a
  610 µm change), drawn as "new sample?". The research reads it as the
  same sample, re-found after slit changes; the user confirms.
- three re-references after sh scans 5, 10 and 13, of +5.5, −1.0 and
  +0.5 µm, each 1–2 min after its scan ends.
- 4 aborts, 29 macro files loaded (3 in the file header) and one gap over
  20 min (after scan 2).
- 5 sx steps, 20 → 18 → 16 → 14 → 12 → 10 mm.
- the four sh scans with their super-Gaussian fits (scan 4: no beam).
- the mnemonics sh → Sample_H, oh → Out_Ht, dth → Det_Th, ih → In_Ht.

**Assumptions:**
- A gap is 20 min without a scan; the research leaves N to the owner.
- A move between scans is dated only to the interval between them.
- Dates are local and converted with the header's #E/#D zone; without a
  zone they are read as UTC, and the timeline's notes say so.
- Scan 13's "aborted after 21 points" counts as complete, by the series
  rule (21 of 21 points).

### 2026-11-24 — Study B, MCA line intensities: the owner's study of F90's decisions (tools man)

Verified by: runs on synthetic spectra, with tests for the pieces. The
full write-up, figures B1–B7 and the commands are in
`docs/studies/mca_fit/summary.md` (C47).

**Question (owner, 2026-11-24, on batch 15):** "I want a full study (is
real data needed? Better synthetic? Show some synthetic data replicates
and their fits! Show me stats in graphical form!)" for the MCA decision.

**Answer, in brief:**
- **P1.** Data weights read a weak line low, as −19/N: −23 % at 100
  counts, −5 % at 400. P1 removes the bias and costs nothing at high
  counts. This holds whatever the background, so no real data are
  needed for it.
- **The window sum** fails whenever beam scatter lies under the box:
  everywhere in the robustness map, and the hard XFNTR curve is off by
  68 % at its worst point.
- **Zn under 10 keV.** No estimator is within 1 %. P1+P2+P3 comes
  closest, at −7 % with fits failing. The O 1s Compton wing decides, and
  its size is the synthetic data's main uncertainty. A blank spectrum
  measures it (DATA_NEEDS row 3).
- **At a 12 keV beam** the same case passes with P1 alone: +0.5 %, pull
  SD 1.07, no failures. At 11 keV, P1+P3 reads +0.3 %.

**The generator was improved for the study.** Water's Compton scatter is
now computed shell by shell in the impulse approximation, with hydrogenic
momentum densities and binding cut-offs. The effective charges are from
memory, and Hartree–Fock tables were not available offline. Not checked
against real spectra.

### 2026-11-24 — Study A answered: raise the join guard to p 0.7; C45's "1.13" was mostly sampling

The owner asked for a full study (entry above, "The owner asks for full
studies").

**The answer for the guard.** The details are in
`docs/studies/reflectivity_guard/summary.md`, and in the ELI5 version,
`docs/studies/eli5_two_decisions.md`. Raise p₀ from 0.3 to 0.7.

**The evidence**, all synthetic with known truth: C45 reproduced exactly,
400–2000 replicates, two robustness maps.

| p₀ | Bias at the five hard joins (mean \|pull mean\|) | Smooth join pull SD |
|---|---|---|
| 0.3 | 0.24 | 1.00 |
| 0.5 | 0.16 | 1.03 |
| 0.7 | 0.12 | 1.04 |
| 0.9 | 0.10 | 1.04 |

- p₀ 0.5–0.9 win 23 of 24 robustness cells: 3–10 points per fringe ×
  flux 1 to 0.01, on coinciding and on staggered grids.
- 0.7 is the setting, because 0.9 gains nothing that shows.

**Real data are not needed.** Every choice moves a downstream structural
fit by about 0.001 Å. The NX school joins give identical factors under
every choice.

**The answer changed overnight.** A first map whose strictest setting
was 0.3 said "keep 0.3". Main added p 0.5, then 0.7 and 0.9 and a map
on staggered grids, and the answer moved.

The owner decides. The change itself is one constant, `patching.GUARD_P`,
with its OUTPUT_DECISIONS row and re-pins.

**Correction to C45 and to the entry "Why five gauntlet joins are
biased".** The smooth first join's "pull SD 1.13" was mostly sampling
noise of the first 300–400 seeds. Over 2000 seeds p 0.3 gives
1.001 ± 0.016, and the guard off gives 0.918. The guard's widening is
real but smaller, +0.083 ± 0.008, measured paired on the same
replicates. It roughly cancels the guard-off error's inflate-only
conservatism: 0.978 on the counting error alone, and 41 % of its errors
are inflated.

Verified: run, `tests/tools/ref_guard_study.py`. Rerun by Main, every
CSV and PNG byte-identical. C48 (C47 is study B).

### 2026-11-24 — The owner pauses the synthetic MCA project: wait for real data; Zn at 10 keV no longer required

**Owner, 2026-11-24 (to Main):** "Btw this synthetic MCA data project is getting out of hand. Let's wait for real data and relax the requirement of zinc at 10kev. It served as a good stress test but is probably an unsolvable problem. Likely we would just increase the excitation energy to separate the lines. But don't lose all the work we've done so far, make sure it gets a full demo treatment (figures, clear docs) and inclusion in the tools menu."

**What this means for the work:**
- **Paused:** further synthetic MCA development for F90. That covers the
  generator, new estimators and further gauntlet designs.
- **No longer a requirement:** Zn Kα under a 10 keV beam (the "hard
  case"). It stays in the record as the stress test it was. Study B
  (C47) found no estimator within 1 % there, because the oxygen 1s
  Compton wing decides it.
- **The practical route:** raise the excitation energy to separate the
  lines. Study B measured this: at 12 keV the same case passes with P1
  alone (+0.5 %, no failures).
- **Waits for real data:** P2, P3 and P4 (DATA_NEEDS row 3: other
  elements and blank spectra).
- **The work is kept:** it gets a full demonstration treatment, with
  figures, clear documents and its Tools menu items. That is assigned to
  tools man, who built it.

**Not decided by this:** P1 as the "Fit lines" default. Study B found it
needs no real data, but the owner's answer on it is still pending, with
the guard's p (TODO, "For the owner").

Verified: nothing measured (a decision).
### 2026-11-24 — F71 / F97: the ROI close-up panel

The owner's Q-IMG-7: a side panel always visible beside the frame, the
same on both tabs, with the cue thresholds as proposed. F71: a healthy
zoom that still shows the diffuse scattering and the background zones,
log helps. Built (a subagent's draft, finished by the GUI manager after a
container restart cut it off). Verified by: tested (`test_roi_boxes.py`,
`test_roi_cues.py`, `test_gui_roi_panel.py`) and measured.

- **Boxes:** `lss_core.display.roi_boxes` reproduces `sumROI`'s
  arithmetic (invariant I38). The burned-in borders of the old strip are
  gone, and so is its right background box drawn 2 px from the one summed
  (`image_display.md` §1.5). The reduction is untouched (no sum is made in
  the panel; the export fixtures are unchanged).
- **The panel:**
  - the frame zoomed to the boxes plus a margin, on its own colour scale
    from the signal box (the 99.9th percentile), log by default;
  - the column and row profiles;
  - the sums and the checks;
  - on the Pilatus tab beside the frame, following the movie; on the
    Reflectivity tab in its close-up canvas, following the Qz list;
  - the boxes before the peak search, drawn dashed.
- **Checks (display only, owner's thresholds):**
  - off centre beyond 25 % of the half-width;
  - clipped, more than 1 % of the net on or beyond the box edge;
  - a background box 2 px or less from the signal box;
  - pixels above the count-rate limits (F97);
  - the direct beam inside a box;
  - a box off the frame.
  Position and clipping are judged only when the net signal is above 3σ (an
  assumption, so that noise is not called off centre).
- **Measured** (NX scan 7, movie, 1600 × 1000 offscreen): 0.138 s per
  frame with the panel against 0.092 s without, 46 ms more; within the
  0.5 s of the default 2 fps.

### 2026-11-24 — Where the sample timeline tab goes (owner)

**Question (GUI manager, F83 phase 1c):** a tab in the main window, in the
ngui prototype first, both at once, or not now? The research proposed
ngui; the owner's priorities put the main window first and say ideas
proven in ngui are carried over, not built twice. **Answer (owner,
2026-11-24): a tab in the main window**, a view of `lss_core.timeline`;
ngui shows the same view later. Verified by: the owner's answer only (the
tab is not built yet).

### 2026-11-24 — Q-BURN-6 built: GID-burn rows from the mean frame

The owner's answer (2026-11-23, batch 14): "GID-burn detector rows default
from the mean frame". Built by the tools session as `burn.signal_rows`,
the default of `exp.burn` (`rows='mean'`) and of the burn dialog ("Rows
from frame"). The rule: a 3 × 3 median of the mean frame per Monc; the
strongest column peak's columns (the half-height run, widened by its
width on each side); their row profile less each row's median over the
same number of columns; the rows where it stays above 10 % of its maximum,
2 rows either side. For an exponential rod, 10 % keeps 90 % of its counts.

Verified by: test (`tests/test_burn_rows.py`: a synthetic rod's rows,
noise, a hot pixel, a flat frame, a rod over the whole frame; the GUI
test in `test_gui_burn_trends.py`) and run (NX 14, 15: rows 46–486, the
shadow below the horizon left out; intensity +0.3 %; NX 14's 5 % time
189.6 → 178.4 s). Building it showed a fault in the burn's lit-column rule
(a peak 20 × its floor shrank the window to its core), fixed the same day
(`burn._illuminated`, NX unchanged bit for bit). COMPARISONS C49.

### 2026-11-24 — P1 is the default of "Fit lines" (rule 12)

The owner's standing rule 12 (via Main, 2026-11-24): "Make the best
method the default if it has been comprehensively demonstrated and
tested and has a demonstrator presentation effort behind it." P1 has
study B (C47) and the demo (`docs/reports/mca_fit_demo.md`), so "Fit
lines" now fits each spectrum by Poisson maximum likelihood, and so does
`peaks.fit_series` by default. The old weighting is the legacy switch
`mca_fit_data_weights`, off by default. The earlier option
`mca_fit_poisson` is retired: preferences store every key, so a stored
"False" would otherwise have kept data weights for everyone who saved
preferences.

Before → after (synthetic, study B, measured): a clean line's bias
−23 % → +1.8 % at 100 counts, −5.0 % → +0.4 % at 400, −1.5 % → within
its errors at 1000; within 0.2 % at 10⁴; the weak XFNTR curve's worst
point 13 % → 1.2 %. Re-pins: none of the numbers in the suite changed.
Only tests that named the default changed: `test_gui_workbook`'s switch
test, the preference key in `test_gui_preferences` and
`test_gui_reduction_options`, and `test_peaks` names `weights='data'`
for its comparison. The gauntlet's 'fit' estimators and study B's pass
`weights='data'`, so C42 and C47 reproduce as run.

Verified by: test (the suites named) and reading; no real spectra here.
The window sum is left as it is (OUTPUT_DECISIONS).

### 2026-11-24 — F83 phase 1c: the Timeline tab (first version)

Built in the main window, as the owner chose: `timelineview.TimelineTab`,
a QGraphicsView of `lss_core.timeline`, added as the last tab. Verified
by: tested (`tests/test_gui_timeline.py`, 6 tests) and seen. On NX it
draws:
- 15 scan bars coloured by kind (scans 4 and 12 paler: aborted);
- the "set sh 0" line at 10:37:39 local;
- the three re-references, the four aborts and the 29 macro loads;
- the 5 sx steps from 20 to 10 mm;
- the four sh scans: 82, 81, 81 µm and p 3.4–3.5, scan 4 "no beam";
- the 45 min gap after scan 2.

How it behaves:
- The time axis is drawn in the foreground on the file's local clock,
  with ticks of 1 s to 1 day.
- The wheel zooms the time axis only (×1.25 a notch), drag pans,
  double-click fits.
- A click selects the scan, and SpecPlot shows it with its super-Gaussian
  fit.
- The tab is built when shown and rebuilt when the file's size or time
  changed (Update, Live).

**Not yet:** thumbnails of the sh scans, notes (a Saved row of kind
`note`, research §5), confirming or rejecting "new sample?", the
reduced-data and environment lanes, and level of detail for thousands of
scans (research measured 3,000 bars at 9 ms a redraw).

### 2026-11-24 — The Timeline tab's place (owner)

**Owner:** "Put the timeline tab in main window, furthest to the right."
It is so: the last tab, after 2D_Plot (seen in a window: SpecPlot,
Pilatus, Reflectivity, Line/Area Cuts, MCA, Plot, 2D_Plot, Timeline).
Verified by: test (`test_gui_timeline.py::test_the_tab_is_last_and_says_what_to_do_before_a_file`).

### 2026-11-24 — The owner's rule for defaults, and the join guard made p 0.7

**Owner, 2026-11-24 (to Main):** "Make the best method the default if it has been comprehensively demonstrated and tested and has a demonstrator presentation effort behind it".
It is AGENTS.md rule 12.

**Applied, the same day:**
- **The join guard is now p 0.7** (`patching.GUARD_P`). It meets the
  rule: study A (C48) has six joins on known truth, 400–2000
  replicates, two robustness maps, downstream fits and the real NX
  joins. It has tests, figures, a Tools menu item, the summary and the
  ELI5 rationale.
- **Before → after, on NX school 6–9:** the factors, rungs and covariance
  are identical. NX's split test (six real scans cut in two with a known
  factor 1.25) gives the default an RMS pull of 1.13 before and 1.00
  after.
- **The join note came first, in its own commit.** At a strict guard
  many good fits miss the threshold, and the note had called them "no
  adequate fit" (117 of 300 smooth synthetic joins at p 0.7, none of
  them with p < 0.01). Now it reads "the best fit of the ladder". Only
  below p 0.01 does it read "no adequate fit".
- **Earlier studies keep their own runs at p 0.3,** with a note in each
  tool. That is C35 (downstream covariance), C36 (the gauntlet) and C45
  (biased joins). Their committed products reproduce exactly, the full
  C36 gauntlet included. So does the patch demonstrator's report, whose
  text quotes its run: its figures stay at 0.3 (`--guard-p`), with a note
  and a Tools menu variation at 0.7. Its interactive window uses the
  reader's default.
- **P1 for "Fit lines" is not yet the default.** Its demonstrator, the
  wrap-up the owner asked for (`docs/reports/mca_fit_demo.md`), is not
  done. It becomes the default with that wrap-up (tools man).

Verified: by tests (`test_patching`, re-pinned with the old state kept
at p 0.3), and by runs (the audit, the NX survey, C45 and C35
reproduced).

### 2026-11-24 — GUI questions answered, batch 17 (timeline: Q-TL-3, 4, 6, 7)

Verified by: reading only. The timeline joins several SPEC files on one axis; the sh-scan thumbnail uses SPEC's `Pilatus` counter; the verdict colour depends on width only, the exponent p is shown as a number and the colour thresholds are visual preferences; sx is drawn and coloured by dose per area scaled by a burn test's (F107), with barrier and tensiometer traces shown only if their data exist. Open: Q-TL-2 (a macro-written new-sample line; partly covered by Q-TL-1's answer), Q-TL-5 (the coloured placeholder boxes), Q-TL-8 (environment column names and units), and what a "large" sx change is. **Note on process:** AGENTS.md rule 12 (2026-11-24) now requires a COMPARISONS study, pinning tests and a demonstrator before a default switches; the owner's adoption of the Poisson step P1 as the MCA default (batch 15) falls under it.

### 2026-11-24 — Qc and Qoff of R/R_F (F79): the degeneracy, and the subphases

Asked by Main for the owner's F79 ("Qoff tweaked by hand until the
fresnel-normed reflectivity looks continuous"). Derivation, then checks:

- **Why the edge decides Qoff.** R/R_F with a wrong Qoff ε is
  R(Qz + Qoff)/R_F(Qz + Qoff + ε). Far above the edge R_F ∝ Qz⁻⁴, so the
  ratio only tilts, (1 + ε/Qz)⁴ ≈ 1 + 4ε/Qz (0.4 % at Qz 0.1 for ε = 10⁻⁴).
  At the edge dR_F/dQz is infinite (R_F = 1 − 4√(2x)+… with x = Qz/Qc − 1),
  so the same ε leaves a spike or a dip of tens of percent in the first
  points above Qc: what the owner sees as "not continuous".
- **Qc and Qoff are nearly degenerate.** Without absorption R_F depends on
  Qz/Qc alone and the edge sits at Qz = Qc − Qoff. Moving Qc and Qoff by
  the same Δ keeps the edge in place; what is left is a level change far
  above the edge, R_F(Qz; Qc + Δ)/R_F(Qz; Qc) → (1 + Δ/Qc)⁴ (the 4 % per
  1 % of Qc in F79), which looks like the sample's own level, and a small
  change of shape just above the edge. So fitting Qc and Qoff together from
  one curve is ill-posed: the bootstrap correlation is +0.9 to +1.0.
  Measured: `tests/test_qoff.py` (the fitted Qc − Qoff equals the true
  Qc − Qoff within 10⁻⁴; correlation > 0.8) and the study (C50).
- **A wrong Qc moves Qoff one for one.** The subphase 1 M NaCl (Qc 0.0221)
  reduced at water's 0.0217 gives a proposed Qoff 0.0004 below the truth:
  the edge is put in the right place, and R/R_F above it is then off in
  level by (0.0221/0.0217)⁴ − 1 ≈ 7 %. Measured (`test_qoff.py`).
- **Subphase densities** (`lss_core.fresnel.SUBPHASES`): ρ_e = ρ_m N_A
  [w Z_s/M_s + (1 − w) Z_w/M_w]. Water at 25 °C, 0.99705 g/cm³: 0.3333
  e/Å³, Qc 0.02173 Å⁻¹; D2O 0.02169; NaCl 1, 3, 6, 10 % by mass: 0.02180,
  0.02193, 0.02211, 0.02236; KCl 7 %: 0.02212; CaCl2 5 %, 10 %: 0.02213,
  0.02251 (computed). **Every density is from memory** (CRC Handbook
  tables): the pages could not be opened from this session (Wikipedia's
  data pages do not resolve here), and each entry says so. The third
  significant figure of Qc, the one that matters, is safe against a 0.5 %
  error in a density (Qc ∝ √ρ_e: 0.25 %).

Verified by: derivation, the tests named, and the study's runs
(`docs/studies/qoff/summary.md`).


### 2026-11-24 — F98's core: the dose each point gives the sample, and burns against dose

Verified by: tests (`test_dose.py`, I39); a run on NX school's burns (the numbers below); the owner for the
geometry (Monc upstream of the absorbers, confirmed later the same day: batch 18 below).

- **The beam on the sample during point i** is d_i = M_i/(A_i·g_i) Monc counts at 5 µA/V with the absorbers
  taken out. This is the weight the point already has in "Sum All". The chamber is upstream of the absorbers:
  the reduction multiplies by A and divides by M (read from `lss_core.normalise`; confirmed by the owner,
  2026-11-24, batch 18).
- **In photons** (the default unit), the owner's counts-to-photons route D
  ([xray_fluxor](https://github.com/Dave-J-W/xray_fluxor), `docs/handoff/xray_fluxor_counts_to_photons.md`):
  N_i = (M_i − D t_i) q(E) (S/500 nA/V) gas / A_i. Its bounds (±3.6 % below 13 keV) are a common scale. They
  cancel between burns at one energy and gain, but not across energies. The windows and air between the
  chamber and the sample are not included.
- **Per area**, only with a beam size given: × sin α/(w h), the footprint w h/sin α with α per point
  (`cuts.true_incidence`). Which slit defines the beam at the sample, and whether the S1–S3 blade values are
  half-openings, is asked of the owner (via questor). The header has S0–S3 left/right/top/bottom; NX 14 has
  S1 L/R 1.00 and T/B 0.05.
- **Cumulative, at the middle of each point**, like the burn's exposure time. The shutter is taken as closed
  between points (owner, 2026-11-21: the default), so the overhead adds no dose. **Fast mode** (owner,
  2026-11-24, batch 18: the shutter held open and short exposures): `shutter='open'` adds the beam between
  points, each point's counting rate × the time to the next point's start (`test_dose.py::
  test_fast_mode_adds_the_beam_between_points`). How a file shows fast mode is open (OQ-4), so the caller says.
- **NX school, run:** burn 14 received 2.89e13 photons in 210 s of exposure through absorber 12 (the
  calibrated foils, 10.00 keV, 5 µA/V): 1.4e11 photons/s on the sample. On burns 14 and 15 the dose axis is
  the exposure axis times the mean rate to 1 %.
- **Burns against dose:** `exp.burn(n, axis='dose')` fits the trends against the dose. The axis is in a power
  of 1000 of the unit (1e+12 photons) so that it spans what a time in seconds does: the trend fits'
  derivative steps are absolute for a parameter at 0 and overflow on an axis of 1e12. The default stays time,
  and every time-axis output is unchanged.
- **A defect found on the way** (its own commit): on an axis above 1e5 the linear trend model lost all its
  precision, ΔAICc 831271 instead of 2.56 on t × 1e12. It is now fitted on a rescaled axis there, bit for bit
  the same below.
- **Why the dose axis** (physics_notes 2026-11-23, F76): a change caused by the beam should follow the dose; a
  sample changing by itself follows time. Two burns at different absorbers coincide against dose in the first
  case and against time in the second (the Bunsen–Roscoe reciprocity assumption). The comparison of two
  burns, and the window's plot mode with several burns at once, are next (F98's GUI part, the GUI manager).

### 2026-11-24 — F92's core: dropped points as a mask over raw points

Verified by: tests (`test_masks.py`, I40). Reading only for what the window will do with it (the GUI manager's
F96 window).

- **The mask** (`lss_core.masks.Mask`) is a set of (scan, point) pairs, point numbers as SPEC counts them.
  - It is kept in the workbook's Settings sheet, section `masks`, one row per kind of reduction. The workbook
    keeps its seven sheets (the owner's limit, fewer than eight).
  - "Restore all" empties it (owner, 2026-11-23: undo of single drops is not asked for).
- **`exp.reflectivity(mask=...)`** leaves the masked points out from the start, after repeats are merged.
  - A point of a repeat merged away masks the same position of the scan it went into, which is where the
    window's drops are made.
  - Masked points of scans not in the reduction are ignored.
  - The result records `points` (the point number of each per-scan row) and `masked`; the settings and the
    recipe carry the mask, so a live remake keeps it.
- **From the window's drops to a mask** (`reflectivity.drop_points`). The legacy join keeps the earlier curve's
  points through the overlap (averaged there with the new scan, interpolated) and the new scan's beyond it.
  So every row of the curve joined so far sits at one raw point's Qz, and a typed drop of row k is a drop of
  that row's point. The function also returns the origin of every row of the patched curve, which F94's
  click-to-drop needs.
- **Where a mask and a drop differ.** A point dropped from the curve so far at a later join was already used
  by an earlier join's fit. The mask leaves it out of that fit too, because the mask is over the raw data
  (D2, owner: "reduction can always be repeated from raw data … Confirmed"). For drops of points no earlier
  fit used (every drop of the new scan, the first scan's at the first join, and far-away points of the curve
  so far, outside the earlier overlaps and their ±2 points) the curves are identical.
- **Measured on synthetic data with 2 % noise per scan:** masking scan 1's point at Qz 0.045, inside join 0's
  overlap, changes the curve, while dropping it at join 1 leaves join 0 as it was. With noise-free data on
  coinciding grids the two agree whichever points are used, because the factor is then exactly the ratio.
- **Not yet (the window, GUI manager):**
  - the patch dialog's drops recorded as the mask and the curve remade from it;
  - "Restore all";
  - masked points drawn in a distinct style (F16);
  - the mask read-only when a second reader has the file open (D1).

### 2026-11-24 — Beam size, Monc position, shutter in fast mode, timeline placeholders (batch 18; asked for Main)

Verified by: the owner's statements; nothing checked against data.

- **Beam geometry:** S0 and S1 are upstream of the sample; S2/S3 (Pilatus 1M or point detector, defunct) and S4/S5 (Pilatus 200K/100K) are downstream. Vertically the beam is focused by a curved mirror since the APS shutdown; the slits transmit more than the vertical FWHM. Horizontally most of the energy is in about 1 mm and 1 or 2 mm slits are used. **So the slit opening is not the footprint**; the footprint for dose per area needs the vertical beam size (open: OQ-2, OQ-3) and whether the header's values are half-openings (OQ-1). For a footprint, width × height / sin α with α the incidence angle, which holds for a beam of uniform profile; for a Gaussian the effective area uses the FWHM or the second moment, a choice to make (open).
- **Monc upstream of the absorbers:** confirmed by the owner. The reduction's use of the absorber factor and Monc is consistent with that.
- **Shutter:** closed between burn frames, open in fast mode (wall time = exposure, F98's dose axis must use it); fast mode is a recommended technique, not yet demonstrated (OQ-4).
- **Timeline placeholders:** notes and stand-ins both, plus automatic flags (F108).

### 2026-11-24 — F97's core: diffuse-cut axes β, β − α, Qz and Qxy

Verified by: tests (`test_diffuse_axes.py`, I41) on synthetic specular frames; a computation for the Qxy
comparison (below); reading only for the Q H quirk.

- **The owner's axes** (2026-11-23, Q-IMG-12): β, β − α with α from Qz, Qz and Qxy. Any cut, pixel or Q, can
  now give its x axis as one of `cuts.DIFFUSE_AXES`: 'beta', 'beta-alpha' and 'Qz' for vertical cuts, 'Qxy'
  for horizontal ones. The cut is made exactly as before and only its x values are converted from its
  pixels, so the intensities cannot change (tested).
- **The formulas** (module docstring of `lss_core/cuts.py`):
  - **Vertical cuts:** β = arctan((r − r0) p / D_S2D) + arcsin(2 sin α − sin α_i), the window's 'Angles' of
    Pix V; Qz = (2π/λ)(sin β + sin α_i), its 'Q'.
  - **β − α**, with α = arcsin(Qz λ/4π), puts the specular row at 0 even on a tilted sample: the owner's
    reason. For a specular ray the exit angle equals the specular angle.
  - **Qxy is exact:** (2π/λ)√(cos²α_i + cos²β − 2 cos α_i cos β cos 2θ), signed by 2θ, at the β of the band's
    middle row.
- **The window's 'Q' of a horizontal cut**, 4π sin(2θ/2)/λ, is not Qxy away from the surface. It exceeds the
  exact Qxy by 1/cos α − 1 ≈ α²/2 when β = α, whatever 2θ is (computed, COMPARISONS C51): 1.5e-6 at 0.1°,
  3.8e-5 at 0.5°, 1.5e-4 at 1°, 6.1e-4 at 2°, 1.4e-3 at 3°. Negligible for GID at 0.1°; visible in diffuse
  cuts at large exit angles. The window's 'Q' is unchanged.
- **F59's "nothing happens", measured:** the window's default Q ranges, Qz 0–1 for Q H and Qxy 1–2 for Q V,
  lie off a reflectivity frame. On the synthetic frame the Q V cut over 1–2 sums zeros, with no message.
  - `cuts.covered_range(direction, g, shape)` gives the range the detector covers.
  - `cuts.centred_range(direction, g, half_px)` gives a band about the beam: Qz about its row, Qxy about its
    column. On the synthetic frame it is the Pix V cut over ±10 columns, to the pixel the window rounds to.
  - Which defaults and what message the window uses is the GUI manager's choice.
- **A quirk, read only (not changed):** the Q H cut turns its Qz range into rows with sin α, α from Qz, where
  sin α_i belongs in Qz = (2π/λ)(sin α_i + sin β). The two agree when α_i = α. That holds in specular scans
  (P47) and in GID scans whose L matches In_Rot (NX 14: L 0.0180 → 0.1017°, In_Rot 0.1017°). They differ for
  a sample whose incidence is offset from its Qz. `covered_range` and `centred_range` follow the cut's own
  arithmetic, so that they describe the band it sums.
- **Not yet (the window, GUI manager):** a cut-axis choice beside the Line/Area cut, separate from the frame
  display's Axes; the Q cuts' default ranges and a message when a range misses the detector (F59).

### 2026-11-24 — Qoff: typical size and resolution (F79, C50; asked for tools man, batch 19)

Verified by: the owner's statements; nothing computed here. The owner called the typical Qz offset "roughly −5e-4" Å⁻¹ (asked: the resolution ΔQ near Qc; the question and the answer are about different quantities, so ΔQ remains unmeasured and a request for the local data agent is `DATA_NEEDS.md` row 13). Context: the study's proposal for NX school scans 6–9 is −0.00028 Å⁻¹ (−0.0016°), the same sign and order as the owner's typical offset, and the owner says offsets of that size are usual, so proposing a Qoff by default (nothing applied automatically) matches practice. The synthetic study's rule of thumb, a resolution reads as Qoff ≈ −0.15 × ΔQ (FWHM), is the tools session's, not rechecked: if the owner's −5e-4 were all resolution it would mean ΔQ ≈ 3e-3 Å⁻¹, which is larger than the 5e-4 to 1e-3 range the question assumed, so the two readings need the measurement of row 13.
### 2026-11-24 — Timeline: sample-height scans as thumbnails

The height lane now draws each sh scan small, 64 × 34 px at every zoom:
its Pilatus/Monc points (grey), and its super-Gaussian (purple) when
fitted. `lss_core.timeline.HeightScan` keeps the points (x, y), with y
the values fitted, on the mean monitor's scale. Seen on NX (scan 4's
noise in a grey frame; scans 5, 10 and 13 flat-topped). Verified by:
tested (`test_gui_timeline.py::test_the_sample_height_scans_are_drawn_as_thumbnails`).
No output number changes.

### 2026-11-24 — Timeline: notes, and answering "new sample?"

Research §5's proposal, built. A note is a workbook Saved row of kind
`note`: its scans, a title (label), the text (note), and settings
`{t0, t1, lane, event, answer}`. That gives ids, versions and Excel
filtering, and needs no new sheet (the owner asked for fewer than eight).

- The user's answer to a "set sh 0: new sample?" is such a note, with
  `event` 'set-zero' and `answer` 'new sample' or 'same sample'. It is
  matched to the event by time (within 1 s), and the latest answer
  is drawn.
- The tab reads the notes when it is built, and only from an existing
  workbook: it never creates one just to look.

Verified by: tested (`test_timeline.py::test_notes_round_trip_through_saved_rows`;
`test_gui_timeline.py`: an answer kept and redrawn, a note added and
cancelled, the right-click menu). No output number changes.

### 2026-11-24 — F80 / F105: the Compare tab and the ratio of two reduced curves

The owner's F80 (compare reduced data across places and over time, for
stability) and Q-REF-5 (a tab only for comparing, fed by the workbook,
"provided the new data auto-update"). Built: `lss_core.compare` (no Qt)
and the Compare tab. Verified by: tested (`tests/test_compare.py`,
`tests/test_gui_compare.py`).

- **The ratio** of curve 2 over curve 1 is taken on curve 1's Qz inside
  the common range, with curve 2 interpolated linearly in log R against
  log Qz. Above the critical edge R ≈ (Qc/2Qz)⁴ (Fresnel), and that
  interpolation follows a power law exactly. Measured on a synthetic
  Qz⁻⁴ curve on a coarser grid: ratio 2.000 to 1e-9; interpolating log R
  against Qz instead was up to 4 % off at low Qz. This is the reason for
  the choice.
- **The error** adds relative errors in quadrature,
  σ_r = r √((σ₁/R₁)² + (σ₂/R₂)²) (independent values; Bevington and
  Robinson, ch. 3, from memory). The interpolation correlates neighbouring
  ratio points, which this ignores.
- **Updating:** the tab re-reads the workbook when shown and after every
  save or live remake while it is on show; "Follow new" ticks new curves.
  No output number changes.


### 2026-11-24 — Real scatter in MCA spectra against the synthetic generator (DATA_NEEDS rows 2 and 3)

The owner's non-cloud agent searched the private beamline data for real
examples of the scattered beam (Rayleigh, Compton and its low-energy wing,
Si escape peaks). It fitted them with the generator's own physics
(`tests/synthetic/mca.py`), every uncertain axis free, by Poisson
likelihood. Study: `docs/studies/mca_scatter/summary.md`; tool:
`tests/tools/mca_scatter.py`; per-example numbers:
`docs/studies/mca_scatter/quantities.csv`. No spectrum is committed: blank
candidates wait for the owner's yes (listed in the summary).

**Row 2 (where the spectra are), answered.**
- No SPEC data file holds a spectrum: 1043 MCA files from 12 runs were
  checked.
- The scan's block has `#V <datafile>_<scan>_mca`, a pointer only. It is
  missing from some `a2scan`, `ascan` and `escan` blocks whose file exists.
- The spectra are in `vortex/<datafile>_<scan>_mca`:
  - one `mca_save_point Point:p Scan:s` block per point and per detector
    element;
  - each block carries `#@CALIB`, `#@CTIME`, `#Energy`, `#Q` and `#Monc`.

**Row 3 (blanks), answered as far as the data go.**
- **The blanks.** No pure-water blank was recorded. Two kinds of spectra
  stand in for one:
  - spectra with no line near the scatter: energy-scan points below the
    studied edge, aligned and summed;
  - 10 keV scans with only traces of Cu and Zn.
- **Coverage.** 6.1, 7.2, 7.4, 8.3, 9.2 and 10 keV beams, on two readouts;
  30 good fits.
- **Si escape.** Reed's fraction × 1.01–1.12 at 6–7.4 keV, × 1.27–1.44 (fit)
  or 1.46–1.55 (template) at 8.3–9.2 keV on readout B, and × 0.8–1.0 at
  10 keV on readout A.
  - At 10 keV, Cu Kα (8.04 keV) sits on the Compton escape and hides it in
    most scans.
- **O 1s Compton wing.** A water-sized wing (the generator's) is rejected
  by every spectrum: the deviance rises by 38–1600, scaled.
  - Readout A, 10 keV: 0.78–0.87 of water's. Zero is also rejected.
  - Readout B: 0–0.35. It trades against a broad detector tail.
- **Under a line** (E0 − 1.55 keV to the Compton peak − 0.35 keV), against
  study B's hard case:
  - readout A, 10 keV: 1.03–1.23 ×;
  - readout B: 1.5–1.75 × at 10 keV and 1.9–3.2 × at 6–9 keV, because of
    detector tails the generator lacks (a low tail of 3–12 % with a
    0.3–0.5 keV decay, and a high-energy tail of up to 11 %).
- **Resolution.** −9 … +15 % of the generator's default (one run +45 %).
- **Compton.** The momentum widths are water's to 5 % on readout A.

**What it means for F90.**
- The window sum's failure (study B) holds on real data, more strongly on
  readout B.
- The 10 keV Zn case stays out of reach: the wing is 0.8, between B7's ½
  and 1.
- A third axis, the detector's own tails, is missing from B7.
- No default and no generator value was changed: synthetic MCA work is
  paused (owner, 2026-11-24).

**The Zn box (8.26–9.00 keV) at 10 keV.** It holds 0.020 of the elastic
photopeak counts on readout A and 0.062 on readout B. The generator gives
0.014 and 0.021 at the same photons and angle; study B's hard case is about
0.008. The Fe box (6.24–6.56 keV) holds 0.003–0.021 of the elastic at
7.2–9.2 keV.

**P1 on real data (C53).** 19 series of 21 repeated spectra at 10 keV, with a
line near 8 keV on the Compton and elastic escapes, fitted with the reader's
`peaks.fit_series`. The truth is the summed spectrum's fit / N.
- **Data weights:** −28.0 % ± 1.4 % at 25–50 line counts, −27 % at 200,
  −4 % at 1470, and about −1 % by 3000. That is not study B's −19/N: the
  background here is far larger.
- **P1:** +3.5 % ± 1.5 % at 25–50 counts, and within its errors from 200
  counts up.
- So the default (P1) is confirmed on real data.

**Not in the data:** 10.05, 10.52 and 30 keV.

Verified: measured (fits to the private spectra; the reader's own
`fit_series` for C53). The model recovers a known wing, escape and tail on
synthetic data (`tests/test_mca_scatter.py`, slow).

### 2026-11-24 — The beam's vertical size at the sample, from height scans (DATA_NEEDS row 9, F43, OQ-2)

Verified by: measurement on private data by the non-cloud agent (spec files and Pilatus images of 21 runs);
the geometry argument is derived, not measured. Study: `docs/studies/sh_beam_size/summary.md`.

- **The question** (OQ-2, F43): can the vertical beam size at the sample come from half-cut or sh scans, and
  what should the dose per mm² (`lss_core.dose`, `beam_mm=(width, height)`) take?
- **Half-cuts leave no data.** They are done by hand on the live view; the files hold only the `set sh 0`
  (526 times) and three scans at incidence 0, one fine enough to use.
- **The rising edge of every height scan is a knife edge.** The incident beam slopes down at α; a ray clears
  the liquid's dome exactly when it passes above the tangent point where the surface's slope equals the
  beam's, the same point for every ray of a nearly parallel beam, moving 1 : 1 with `sh`. Distortions
  (derived): convergence × tangent distance ≤ 1.5 µm; reflection into the direct beam's pixels < 0.3 µm.
  The falling side is loss on the curved upstream end, not a beam edge. 1995 of 2815 height scans pass the
  guards (rise scanned from its foot, ≥ 2 points on the edge, rise and fall separated by > 3 σ, χ²/dof ≤ 20).
- **Two witnesses agree.** The erf σ of the ROI/Monc rise (the spec-only route; `peaks.fit_box`'s rising
  FWHM / 2.355 matches it, ratio 0.983 on 150 scans) and the direct beam in the Pilatus images (109 scans,
  18 runs). The images need a core + tail profile (median χ²/dof 2.1 against 30 for one erf): core σ 13.5 µm,
  tail σ 56 µm, tail fraction 0.29, FWHM 33 µm, inverse peak 43 µm (medians). The S1 slit scans show a tail
  already at S1 (median fraction 0.23), so it is in the beam.
- **Numbers.** 10 keV, S1 0.016–0.04 mm: σ_rise 15.3–17.0 µm by class (run medians 14.0–20.0), independent of
  the gap there; profile FWHM 30–33 µm. 6–8 keV, sample cell: σ_rise 22 µm at 0.05–0.07 mm, 32 µm at 0.2 mm
  (energy, cell and gap confounded). 30 keV, liquid metal, one half-cut: σ 8.0 ± 0.3 µm (2 points on the
  edge); a box round the beam on a liquid keeps 4.4 % of the beam 50 µm past the edge (total reflection).
- **Rule for the dose:** height = √(2π)·σ_rise = 1.064 × `fit_box`'s rising FWHM, the median over the run's
  height scans: the inverse peak of the profile, i.e. the peak dose per area. Against the images: 1.06 median
  (10–90 % 0.91–1.24; +25 % too large at S1 0.2 mm). Default without height scans: **0.040 mm** at 10 keV and
  S1 ≤ 0.04 mm (±15 %, run to run). The S1 gap (0.016 mm) as height overstates the peak dose 2.5×, the FWHM
  1.3×. `lss_core/dose.py` is not changed here; this is the input it waits for.
- **Over time, shape, level drift** (main man's questions): σ_rise does not drift within a run (Theil–Sen median
  +0.001 µm/h, every 10 keV series below 1 µm per day; first to last third −1.8 to +2.1 µm); runs differ more (σ 14–18 µm).
  Shape: super-Gaussian p = 0.72 (0.69–0.76): peaked with wings, not flat-topped (F78's flat top is the height scan's
  reflected peak, not the beam). Level drift (±10 µm/h, fastest 26.5) moves the edge by ≤ 0.09 µm while a
  41 s scan crosses it: no blur.
- **OQ-1, read only:** the slit macro that sets centre and gap puts the blades at gap/2 ∓ centre, so the
  header's S1T and S1B are half-openings and the opening is their sum.
- **Still open for the owner:** whether the peak dose (this rule) or the footprint-average is the dose meant
  (OQ-2's last part); the width (not measured here); the upper tail's share of light transmitted through the
  downstream meniscus.

### 2026-11-24 — The beam's height for the dose, from the height scans (the local data agent's rule, #60)

Verified by: tests (`test_beam_height.py`, I42) on synthetic knife edges; a run on NX school's height scans
(public). The rule and its numbers are the local data agent's study (`docs/studies/sh_beam_size/summary.md`).

- **What the study found:** the rising edge of a routine height scan is a knife edge of the beam. The
  dose's height is √(2π)·σ_rise = 1.0645 × `fit_box`'s rising FWHM, which gives the peak dose per area. The
  default is 0.040 mm (±15 %) at 10 keV with S1 ≤ 0.04 mm.
- **What the reader does now:** `exp.beam_height(scans=None, near=None)` applies `dose.rising_edge` to every
  height scan. It uses `peaks.is_height_scan`, the first column as the height and Pilatus/Monc as the signal,
  with Poisson + 1 % weights.
  - **The study's guards:** the first point below 25 % of the peak; at least 2 points on the edge; the
    centre inside the scan; the edges more than 3 σ apart; χ²/dof ≤ 20.
  - **The height:** 1.0645 × the median rising FWHM of the accepted scans.
  - **With `near=n`:** only the scans with n's S1 gap count (S1T + S1B, the two half-openings: OQ-1, answered
    2026-11-25), and the nearest `NEAR_SCANS` = 3 of them are used. The 3 is an assumption.
  - **Without an accepted scan:** the default where its conditions hold, otherwise no height, with the reason.
- **NX school, run:**
  - Scans 5, 10 and 13 are accepted: rising FWHM 0.029–0.032 mm, height 0.0333 mm, scatter 3.8 %.
  - Scan 4 is refused: the stopped scan starts at 54 % of the peak.
  - At S1 0.016 mm that is a little below the study's run medians, 0.035–0.045 mm.
  - Burn 14 ran with S1 at 0.100 mm, so `near=14` gives no height. Its height scans were at 0.016 mm, and the
    default is only for ≤ 0.04 mm. That refusal is the rule working: the beam depends on the gap.
- **The width is not measured** (the study: about 1.05 mm between the 5 and 95 % points in one earlier
  image study), so `beam_mm` takes it as typed.

### 2026-11-24 — The owner: sample-height scans from the ROI are unrestricted data

Verified by: the owner's statement in the orchestrator's session ("sample height scans from ROI are
unrestricted data"). So the ROI counter, monitor and sh columns of sample-height scans, and anything derived
from them, may be published: per-scan curves, edges, widths, and the inventory behind the beam-height study
(#60), if the local data agent wishes. Detector images of those scans stay private, as do the other private
data and their identifiers (names, scan numbers, dates) unless the owner says otherwise. Recorded in
AGENTS.md's row for `sample_data/private/`.

### 2026-11-24 — The owner: the MCA scatter blanks may be committed, beam energies to 0.1 keV

Verified by: the owner's answers to the two questions of `docs/studies/mca_scatter/summary.md`, put to
them by the data-analysis coordinator and relayed to the local data agent. "Yes, commit them": the 13
scrubbed scatter-only blanks (E10-d, -f, -i, -j, -k; E9.2-a … d; E6.1-a … d) are now in
`tests/reference/mca_scatter/`, as `energy_keV,counts` with a header of beam energy, readout, kind, gain and
summed real and live times, and nothing tying them to a beamtime. "Keep 0.1 keV": beam energies stay
public to 0.1 keV, so the study's tables are unchanged. `tests/test_mca_scatter.py` loads every blank,
checks its header carries no date, time, scan or file name, and checks its elastic edge against the
fitted width. Only these spectra are allowed; other private spectra stay private.

### 2026-11-24 — Review of the covariance export (owner: "review their subject areas")

Checked on origin/main 9e706a7: the export's own tests, the reflectivity
tests and the window's Ref Patch since the GUI work (F96 Back, F92 masks,
F81 repeats as ΣN/ΣM, the one-point-overlap error, the guard at p 0.7).
The sidecars still match the written files: tested again, and new tests
cover Back after a Drop, masked reductions and the §3.1 linear fallback.
One defect, fixed: the Script pane's line for an Export with "+
covariance" said `ref.save(name)`, so a script wrote no sidecars. It now
says `covariance='sidecar'` (tested by running it).

Measured: at the new guard p 0.7 the joint chain's Σ is about 10 % small
at every join (scan-level pull SDs 1.11–1.15, 300 seeds). Downstream
fits with the covariance stay honest (pull SDs 0.98–1.11). Report §6;
the remedy is the owner's (TODO B2, with C45's question).

Read only: in the contract layout, `_ref_legacy.txt` is the legacy
factor fit on the scans as the result holds them. With repeats merged
as ΣN/ΣM (F81, the default since 2026-11-23) it is therefore not the
pre-2026-11-22 file for reductions with repeats.

### 2026-11-24 — What a height scan tells you, and both of its edges (the owner's question on the fits)

Verified by: measurement on private spec files by the non-cloud agent (1995 accepted height scans, 21 runs);
the sketch is derived. Study: `docs/studies/sh_beam_size/height_scans.md` (figures S6–S9).

- **Single scans, fitted, are now shown** (the owner made height-scan ROI data unrestricted): one accepted scan
  per class and one rejected scan per guard, with residuals. χ²/dof is 3–13 (10–90 %), not 1, because one erf
  misses the beam's core + tail: points sit above the fit in the foot and wobble about the edge. The per-scan
  fit error on σ_rise (median 1.0 µm) equals the scan-to-scan scatter within a run (median 1.0 µm).
- **Correction to the entry above: the falling edge is also a cut through the beam, not only "loss".** The
  rise and fall widths are rank-correlated scan to scan in all 21 run series (ρ +0.29 to +0.79, median
  +0.57). σ_fall / σ_rise is 0.89 at 10 keV in the full fit, and 0.96 when each edge is fitted on its own
  half with a sloping plateau (6–8 keV: 0.98 and 1.03). So both ends of the trough see the same beam. The
  fall stays a cross-check only: its position depends on α_c − α, the reflectivity and the ROI.
- **The residual shape matches the images.** One erf fitted to the images' median core + tail (13.5 / 56 µm,
  29 %) has σ = 16.2 µm, against σ_rise 15–17 µm at 10 keV, and leaves the same wiggle the ROI scans show.
- **Meniscus.** The curved ends set where the knife cuts (the tangent point) and the plateau length (α × the
  flat length), not the rise's width. Too short a plateau is rejected. A non-flat plateau narrows the full
  fit's σ_fall by about 9 % and σ_rise by about 2 %. Within a run σ_rise falls slightly as the plateau
  lengthens (median ρ −0.20), unexplained, about 1 µm.
- **How sure:** a run's median σ_rise ± 0.3 µm statistically; as a size, about ± 10 % (one erf for a core +
  tail profile). No number of the dose rule changes.


### 2026-11-24 — Real reflectivity burns: trends, and the beam or the clock (DATA_NEEDS row 11, F76, F77)

Verified by: a run of the reader's `Experiment.burn` (both axes, defaults) on 78 real reflectivity burns
from the owner's private data (14 runs, 10 keV), by the non-cloud agent. Study, figures and tables:
`docs/studies/xr_burns/summary.md` (C54).
- **The reader's verdicts:** 28 of 78 stable (frame 1 left out). Stability falls with flux: 10 of 18 below
  3 × 10⁹ photons/s, 5–7 of about 20 in each bin above.
- **The old ROI-total rule dilutes the change.** The background-subtracted specular part is a median 0.37
  of the ROI total. Over 41 burns that change by ≥ 3σ, the ROI total drifts at a median 0.61 of the
  specular rate, and those burns' median fraction is 0.60. The old rule calls 11 changing burns stable.
- **Dose or time (F76):** across a series at several absorbers, rate_t ∝ flux^β, β = 1 for the dose and 0
  for the clock. Two strips at one absorber differ by 88 %/h (64–122) beyond their counting errors. With
  counting errors alone, 8 of 19 series reject both. With the strip scatter: 4 dose, 0 time, 10
  undecidable. Where β is determined it runs from 0.2 to more than 2 (≈ 1 in 3 series).
- **F77:** reciprocity holds in 3 of 8 series. β > 1 makes a high-flux test overstate the damage (safe);
  β < 1 makes it understate it (unsafe). Since β varies between samples, one short high-flux test does not
  predict a safe absorber. Two fluxes at least ×10 apart, each on two strips, can.
- **For the core:** any automatic dose-or-time verdict needs a between-strip term, or it will call most
  real series "neither". One real burn makes `Experiment.burn` fail with a NaN change time (a ValueError in
  converting it). The 30 keV burns, a Pilatus 1M run, are not read by the burn at all.

### 2026-11-24 — The Qz resolution near the critical edge (DATA_NEEDS row 13, F79, C50, C55)

Verified by: a fit of the edge's width in 400 real reflectivity scans (the first scan of every series
crossing the edge; 17 runs, 10 keV, steps of 0.001 Å⁻¹) by the non-cloud agent, with a known-truth check
on synthetic scans of the same sampling. Study: `docs/studies/qz_resolution/summary.md`.
- **ΔQ FWHM = 8.9 × 10⁻⁴ Å⁻¹ at 10 keV** (σ_Q 3.8 × 10⁻⁴), the median of 378 scans. Run medians are
  6.5–12.6 × 10⁻⁴, and scans within a run scatter by ±15 %. The subphase's absorption is the largest model
  term, ±15 % for β wrong by ×2.
- **Not the slits:** S1 at 0.04 and at 0.2 mm in one run give the same width (σ_Q 3.38 ± 0.08 and
  3.41 ± 0.75 × 10⁻⁴). The footprint grows ×5 and the width does not change. S1 at 0.02 mm is not
  determined.
- **The cause:** the beam's convergence, 37 µrad rms. The specular spot is as narrow as the direct beam
  (0.245 px, 95 % in one pixel), so the meniscus slope spread is ≲ 1.5 × 10⁻⁴ in σ_Q. Si(111) bandwidth
  contributes 1 × 10⁻⁶.
- **For Qoff:** C50's −0.15 ΔQ turns this into a proposed Qoff of −1.3 × 10⁻⁴ Å⁻¹ (runs −1.0 to −1.9). That
  is about half of NX's −2.8 × 10⁻⁴ and a quarter of the owner's typical −5 × 10⁻⁴. The rest is angle (or
  Qc).
- The fits' own errors are 3.5× too small against the scatter within a run (per-point angle errors); quote
  the scatter.

### 2026-11-24 — Reflectivity patching on real series (DATA_NEEDS row 1, hand-off 08, C56)

Verified by: a run of hand-off 08's survey (`tests/tools/ref_patch_survey.py`) on 380 private reflectivity
series, 1832 joins (18 files, 10 keV), by the non-cloud agent. It added the guard at p 0.3 and the guard off
beside the default (p 0.7). Study: `docs/studies/ref_patch_real/summary.md`.
- **The joint fit is confirmed as the default on real data.** In 1091 real-curve split tests (truth
  f = 1.25) its bias is +0.10 % [−0.10, +0.32]. The legacy factor's is −0.55 % [−1.16, −0.22], with errors
  2.4× too small.
- **p 0.7 or 0.3 makes no difference on real data.** The factor is identical at 67 % of joins and more than
  1σ apart at 3.7 %. The calibration is the same (pull SD 1.24, 1.23), and so is the foil z. Study A's
  choice stands, and the foils do not disagree with the fits at real joins.
- **New: the guard leaves the errors too small on real joins.** The pull SD is 1.24 [1.09, 1.40] with the
  guard and 1.00 [0.93, 1.03] without it, a difference of +0.24 [0.11, 0.38] (bootstrap over files). The
  ladder climbs to order 5, χ²/dof about 0.8, so inflate-only never acts. Without the guard, χ²/dof is
  about 1.5 and the errors inflate. A remedy is proposed in the study; nothing is changed (rule 12).
- The share of joins with χ² p < 0.01 rises with Qz, 5 → 11 → 17 % (default): there is excess per-point
  scatter at high Qz.

### 2026-11-24 — Row 8: overlaps below 10 keV, and the copper foils at 30 keV (DATA_NEEDS row 8, P28, F49)

Verified by: the reflectivity survey of row 1 (every readable series and its energy), the owner's analysing
repository's beam energies per run, and its absorber-step measurement at 30 keV (read here, not rerun). By
the non-cloud agent.
- **No reflectivity series with overlaps at 6–7 keV exists** in the owner's private data: every readable
  series is at 10 keV, and the only other energy is one run at 30 keV. P28 below 10 keV stays open.
- **Cu at 30 keV (F49):** that run gives 16 same-slit overlaps between absorber settings (ROI totals, not
  background-subtracted). The factor per unit has a median of 1.212 (interquartile 1.15–1.27, 10th–90th
  1.08–1.33). A log-ratio fit weighted by Δabsorber gives 1.262 ± 0.035. With μ/ρ of copper at 30 keV of
  about 10.9 cm²/g (NIST; an assumption to check against SRD 126 before it goes into `absorbers.py`) and
  8.96 g/cm³, ln f / μ is **about 20 µm (median) to 24 ± 3 µm (fit) of Cu per unit**. Rough: one run, and
  most overlaps share only one point.
- **Not in the data:** foil tolerance and alloy. The reader cannot read that run's frames (Pilatus 1M,
  F38), so the background-subtracted check is not possible yet.

### 2026-11-24 — Does a reflectivity join need coincident Qz points? (owner's question, C57)

The owner asked whether a join should always include at least one coincident point, and whether one is
enough, so that each scan could use its own spacing. Verified by a synthetic known-truth run (21,600 joins:
water, DPPC and a 100 Å film; joins at Qz 0.05, 0.15 and 0.30; 12 overlap geometries; the reader's own patch
code) and by C56's 1832 real joins. Study: `docs/studies/coincident_points/summary.md`. By the non-cloud agent.
- **Shared Qz are not needed; an overlap is.** With 4 or more points of each scan in the overlap, the default
  joint fit has the same precision whether the points coincide or are staggered (4+4 staggered: 1.72 %;
  5 coincident: 1.70 %). It is unbiased within 0.1 % and honest (pull SD 0.96–1.05). With no overlap, no
  method answers.
- **One shared point alone** gives an unbiased factor at about twice the error (3.3 % against 1.5–1.7 %).
  The real joins agree: 2.1×, robust SD of the difference 0.93. The default joint fit refuses that geometry,
  because its order-4 ladder needs more points.
- **With 2 points per scan**, a fast fringe (film at 0.30, 6 points per fringe) biases the default by −2.0 %
  (0.6 of its error). At 3 or more points, there is no bias.
- **The legacy factor's error is wrong at small overlaps:** pull SD 4–106 with 2 coincident points and 11–336
  with staggered 2+2.
- **For planning:** different spacing per scan is fine. Overlap by at least 4 points of each scan, 6 or more
  per fringe on a fast fringe. Keep a shared Qz only as a cross-check.

### 2026-11-25 — The owner: frame-by-frame curves of private burns are not published

Verified by: the owner's answer in main man's session, on PR #68's figure B1 (each real reflectivity burn frame
by frame, normalised to its first frames, against time and dose, about 19 anonymised series): "Don't publish
B1, but don't forget how to make it!" So such curves of private data stay private, normalised and anonymised
or not; the summary values (each burn's rate, the series' β and verdict, the CSVs of PR #68) are published.
The figure and its generator are kept under `sample_data/private/` (git-ignored), and the public study page
names the script and the command that regenerates it. A figure must not be removed by a later commit only:
the commit that added it would reach main's history, so the branch is rebuilt without it. Recorded in
AGENTS.md's row for `sample_data/private/`.

### 2026-11-25 — F76: beam damage or a sample changing by itself, as a test

Asked by main man for the owner's F76. Built as
`lss_core.reciprocity.dose_or_time` (tests: `tests/test_reciprocity.py`).

- **The test.** Damage by the beam follows the dose D = φ t; a sample
  changing by itself follows t. Across burns at fluxes φ_b, the rate against
  time goes as rate_b = k φ_b^β: β = 1 the dose, β = 0 time. It is the
  convention of the real-burn study (C54), so the two agree. β is profiled
  with k fitted at each β. The verdict: "dose" when β = 1 passes
  (χ², n − 1 dof, p ≥ 0.05) and β = 0 fails, "time" the reverse, "cannot
  tell" both, "neither" neither (β̂ shows a dose-rate effect), with "no
  change" and "opposite signs" first. How strongly: β̂'s intervals and the
  Akaike weight of β = 1 against β = 0.
- **The assumption:** reciprocity (Bunsen–Roscoe): the same dose gives the
  same change at any rate. It fails through dose-rate effects and, at a
  liquid surface, through molecules exchanging into the footprint. β ≠ 1
  measures the failure; it does not assume it away.
- **The drift rate is the slope of ln y** for a relative quantity. A
  straight line through y itself reads an exponential fall's rate low, the
  more so the faster it falls, so a dose truth at fluxes 1, 4.7 and 10
  (10 % fall at the lowest) came out "neither" with β < 1. Through ln y it
  is exact for first-order kinetics. Measured (`test_reciprocity.py`).
- **NX school burns 14 and 15** (one spot, absorbers 12 then 8; flux
  ×4.68 by the calibrated foils): the position drifts 1.09 × 10⁻⁵ and
  4.03 × 10⁻⁵ Å⁻¹/s, so β = 0.85 ± 0.04. That is far from time (β = 0 fails,
  p 10⁻¹⁵⁴) and close to the dose. On counting errors alone β = 1 fails
  narrowly (p 0.004): "neither", with the Akaike weight 1.00 on the dose.
  With a 10 % strip scatter it reads "dose". Caveat: 15 was measured on
  the same spot after 14, so it started with 14's dose. A sub-linear β
  could be saturation as well as a dose-rate effect. The intensity changes
  in neither burn ("no change"). Measured 2026-11-25.

### 2026-11-25 — The owner asked: what does "ΔQ 8.9 × 10⁻⁴ Å⁻¹ at 10 keV, no S1 dependence" mean?

Verified by: reading the local data agent's study (`docs/studies/qz_resolution/summary.md`, PR #68, pending the
removal of its figure B1) and checking its arithmetic here; nothing measured by main man.

- **What it is:** the blur in Qz of each reflectivity point near the critical edge, measured from how wide the
  edge is in 378 real scans from 17 runs. Each scan is fitted with the Fresnel reflectivity convolved with a
  Gaussian of width σ_Q. The result is FWHM 8.9 × 10⁻⁴ Å⁻¹ (σ_Q 3.8 × 10⁻⁴), run medians 6.5–12.6 × 10⁻⁴,
  about ±15 % within a run. On synthetic scans of known width the estimator is right within 2 %.
- **Where it comes from:** the beam's spread of incidence angles, 37 µrad rms. Qz = (4π/λ) sin α, so
  σ_Q = (4π/λ) cos α σ_α = 10.14 Å⁻¹ × 37 µrad = 3.75 × 10⁻⁴ (computed). The monochromator's bandwidth
  (Si(111), Δλ/λ ≈ 1.3 × 10⁻⁴) adds about Qc · Δλ/λ ≈ 3 × 10⁻⁶, negligible (computed).
  - So ΔQ is the same at every Qz. As a fraction it is 4 % at the edge, 0.9 % at 0.1 Å⁻¹ and 0.18 % at
    0.5 Å⁻¹ (computed).
  - It washes out Kiessig fringes only for films thicker than about 2π/(2ΔQ) ≈ 3500 Å (computed, a rough
    criterion).
- **No S1 dependence (0.04–0.2 mm, one run with both: σ_Q 3.38 ± 0.08 against 3.41 ± 0.75 × 10⁻⁴):** the
  angular spread is set by the mirror's vertical focusing, not by S1, which here sets the beam's size and
  footprint. Opening S1 from 0.04 to 0.2 mm (footprint ×5) costs no resolution. Below 0.04 mm it is not
  determined (0.02 mm: 11 scans, scattered fits). That is why ΔQ varies from run to run, with the focus, and
  not with the slits.
- **Why it matters for Qoff (F79):** a blurred edge read without a resolution model looks like an edge
  shifted down. Tools man's study (C50) found the apparent Qoff to be about −0.15 × ΔQ, so −1.3 × 10⁻⁴ Å⁻¹:
  about half the NX file's proposed −2.8 × 10⁻⁴, and a quarter of the owner's typical −5 × 10⁻⁴. The
  reader's R_F has no resolution model; adding one (a Gaussian of σ_Q ≈ 3.8 × 10⁻⁴) would make R/R_F
  continuous through the edge without a fake Qoff. A default would need rule 12.
- **Caveats (from the study):**
  - the subphase's absorption is the one input that matters: ±15 % for a β wrong by ×2, and a saltier
    subphase would give a narrower ΔQ than quoted;
  - only 10 keV was measured; a fixed angular spread scales ΔQ ∝ E;
  - the resolution is assumed Gaussian, although the beam has a core and tails at the sample;
  - the public NX file cannot measure it: too few points below its edge.
- **References** (not opened in this session):
  - J. Als-Nielsen and D. McMorrow, *Elements of Modern X-ray Physics*, 2nd ed., Wiley 2011, ch. 3, on
    Fresnel reflectivity and the critical edge, https://doi.org/10.1002/9781119998365;
  - the Refl1D guide to resolution in reflectometry, on the angular and wavelength terms and their
    convolution with the model, https://refl1d.readthedocs.io/en/latest/guide/resolution.html.


### 2026-11-24 — Stray light and beam-path background in pinhole GID frames, on the private data (DATA_NEEDS row 10, P40)

Verified by: measurement on private data by the non-cloud agent (every inferred GID set with frames: 189
sets, 286 Qz levels, 18 beamtimes; and one beamtime's off-specular frames with the sample lowered). Study:
`docs/studies/gid_stray_light/summary.md`.

- **What exists of what row 10 asked for:** no GID set of a bare subphase and no GID frames with the sample
  lowered; 94 same-slit, same-absorber level pairs (arm level and raised to β0 6.5°), of which only 4–6 are
  nearly free of GID signal; S5 is the same at both heights in every pair (never nearly closed at the raised
  arm); the lower level was repeated after the upper in 26 pairs. One beamtime's off-specular scans include 7
  with the sample lowered 2 mm and the same slits.
- **P40b, the streak past S5's high edge at the raised arm, is in every beamtime:** 31× the level arm's light in
  those columns (median of 94 pairs; 16–84 % 13–110×; beamtime medians 7–146×); none past S5's low edge
  (0.77×). The P39 decision to keep IDL's high edge on raised-arm frames stays right; a fixed mask width would
  not fit every beamtime.
- **P40a:** beyond the footprint but inside S5, 0.41 of the usable columns' light near the horizon at the level
  arm (0.33–0.50), 1.34× more at the raised arm; below the horizon 1.6 % in the usable columns and 22 % beyond the
  footprint. The usable columns see the same light at both heights at β 5–9° (0.93×).
- **Beam path alone** (sample lowered, off-specular geometry, not GID): 10–14 % of the frame near the horizon,
  33–49 % at β 3–6°, flat in β.
- **No reader number changes.** P40 stays open; subtracting P40a needs GID background frames that the data do
  not hold (same slits, sample lowered, both arm heights).

### 2026-11-24 — GISAXS and GIOXS examples in the private data (DATA_NEEDS row 4, F104, P35)

Verified by: reading every SPEC header of the private copy (8255 scans) by the non-cloud agent, and
measurement on the frames of the GISAXS set (the brightest column). Study:
`docs/studies/gisaxs_gioxs_inventory/summary.md`.

- **GISAXS: one beamtime**, 67 scans of 2 frames × 10 s on the 200K: α 0.09°, Det_Th 0.45°, wide S4 (3 + 10 mm)
  and S5 (7.4 + 14 mm), the detector moved back (header S2D 1022.5 mm, pinhole 685 mm). No background, no beam
  stop. **Its header geometry is off:** in all 67 scans the brightest column lies 4.97 ± 0.02 columns above
  what DBPos and Det_Th predict at the header S2D, so q needs a direct-beam calibration first, and P35 (the
  GISAXS view one column off) cannot be settled from it.
- **GIOXS in the sense of off-specular scattering below the critical angle (GIXOS): one beamtime, two files**:
  36 sample scans and 7 with the sample lowered 2 mm, α 0.10°, Det_Th 0.3°, S4 and S5 0.12 mm wide (the slits
  fix the in-plane angle; the rows give β). The lowered scans are the background (same slits): the beam path
  is 10–14 % of the frame near the horizon, 33–49 % at β 3–6° (`docs/studies/gid_stray_light/`).
- **The diffuse around the specular** (F104's own wording for GIOXS) is recorded by the Pilatus 1M
  reflectivity frames of two beamtimes (1043 × 981 pixels, 30 keV and 6.2 keV); no dedicated off-specular
  scans there.
- What the reader would need is listed per set in the study (β profiles of a column band with background
  subtraction for GIXOS; q mapping after a geometry calibration for GISAXS; the F38 geometry for the 1M).
  Nothing is copied into the repository; the frames stay private.

### 2026-11-24 — Stage 4 inputs: which requested formats exist in the private data (DATA_NEEDS row 6)

Verified by: reading by the non-cloud agent (every SPEC header of the private copy, the TIFF header of one
frame per imaging scan, the document files of the one bluesky folder). Study: `docs/studies/stage4_inputs/summary.md`.

- **Full two-module 200K frame (F63): no.** All 6506 sampled 200K scans in 21 run folders save one module
  (TIFF 487 × 195, 32-bit).
- **New-format fluorescence/GID SPEC file (F28): not identified.** One header layout throughout; the only newer
  layout is the per-point MCA files (row 2). GID with fluorescence exists only as alternating Vortex and
  Pilatus scans at a fixed Det_Th.
- **HDF5/bluesky (F29): yes, but no surface data.** A commissioning run at the other station: 307 runs as JSONL
  event documents and 100 small HDF5 files written by a Dante MCA; beamline scans only, no area detector.
- **Pilatus + Vortex in one scan (F53): yes**, two usable scans (alignment-type, a frame and a per-point MCA file
  for every point) and one with frames but no spectra.
- **1M geometry (F38): yes.** Two beamtimes, TIFF 1043 × 981; `#B5 x y D 0` gives the beam pixel and the
  sample–detector distance (2654.6 and 2038.7 mm in two installations); in one beamtime the detector stage
  height changes from scan to scan (tracked mode) but is logged only at each scan's start.

### 2026-11-24 — The GID defaults judged on the private data (hand-off 06, DATA_NEEDS row 12)

Verified by: measurement on private data by the non-cloud agent, with the reader's own survey tool
(`tests/tools/gid_method_survey.py --split`, unchanged) on 194 inferred GID sets in 18 beamtimes. Study:
`docs/studies/gid_method_survey/summary.md`; COMPARISONS C59, C60.

- **Response:** `beam` is the safest: best on 122 of 239 levels, median 1.00× the best frames-agree χ²/dof,
  worst 2.85×; the default `fit` median 1.13×, worst 14×, and 1.61× at Det_Th < 10° where the column-to-beam
  mapping moves fastest. Not uniform: `fit` is better in 3 of 15 beamtimes (by 8–49 %). Every pinhole
  response gives the same ground truth (patched FWHM / single frames 1.01; the legacy patch 1.52). Split test:
  `beam` within 1 % of 1.25 in 37 of 38 levels, `fit` 34 (median 1.257, P42's residue).
- **Joins:** as collected, 37 % of level joins and 29 % of scan joins are within 5 % of 1; keep them applied.
  9 % of scan joins are outside 0.5–2 under every method (likely different samples or settings inside one
  inferred series). 18 sets in 7 beamtimes cannot be patched by any pinhole method (a middle level does not
  overlap in β with the ones below); legacy patches them.
- **Distance:** reliable calibration on 30 % of levels (no peak in ≥ 5 frames, frames that disagree or drift,
  and Det_Th steps too coarse for 6 frames per 2θ are the reasons); median 267.2 mm against the header's 271;
  not stable within a beamtime at the stated errors, so no per-beamtime value. Calibrating moves the patched
  peak's centre onto the single frames' (within 2σ in 91 % against 65 %), not its width.
- **Proposed, not applied** (rule 12 first): response default `fit` → `beam`; the distance calibrated per set
  when reliable. Rows for OUTPUT_DECISIONS are in the study.
- **Defect found:** a one-point Det_Th scan in a GID set makes `Experiment.frames` raise `KeyError: 'monc'`
  (4 sets).
### 2026-11-25 — F105: Export proposes a name from the sample and the scans (Q-REF-6)

The owner's Q-REF-6 (2026-11-23): "Straight into xmodfit; the reader
proposes a file name from the sample and series". Built:
- **`lss_core.naming`:** `export_base` builds `<SPEC file>_<sample>_S<scans>`,
  with a run of scans written as `S6-9`.
  - **The sample:** the SPEC files carry no sample name (none in the NX
    file, measured by search). The nearest is the series macro's file name
    (`#U SeriesMacro`, newer macros), less a trailing measurement word
    (`_xr`, `_gid`, …). It is left out when not recorded.
- **The dialog** opens in the folder of the last Export (preference
  `export_folder`), so repeated exports land in XModFit's folder.
- **The files** are unchanged: the golden export tests pass byte for byte,
  and the covariance sidecar is the contract's. No output number changes.

Verified by: tested (`tests/test_naming.py`, `tests/test_gui_export_name.py`).
**Open:** whether the owner wants the series id (from `#U Series`) in the
name as well. It is left out, so the name stays short.

### 2026-11-25 — F97 and F59 in the window: the cut's x axis, Q ranges about the beam

The window side of main man's diffuse axes (#59, `lss_core.cuts`; owner
Q-IMG-12: "β, β − α (α from Qz) and Qz and Qxy"). Built:
- **"x: …"** right of the cut direction (`cutAxisComboBox`): as the image
  (the default, unchanged output), β, β − α, Qz for vertical cuts, Qxy for
  horizontal ones; an axis that does not fit is greyed out. Only the x
  column changes; the intensities and errors are the pixel cut's (I41,
  tested in the window on the synthetic frame; the β − α peak within one
  row of 0, the Qz peak at the frame's 0.01 within 2e-4).
- **The x label** is the axis the cut is on (`cuts.axis_label`). Before, a
  pixel cut was labelled "Pixels" whatever the Axes box said, and a Q H cut
  "Qxy" although its x is the window's 4π sin θ/λ (labelled "Q" now; equal
  to Qxy within 1e-5 relative at 0.1°, per the cuts docstring).
- **F59, the Q cuts' ranges:** with frames shown (no GID or GISAXS map),
  choosing a Q cut puts a band about the first selected frame's beam in
  the box (`cuts.centred_range`), half the reflectivity ROI either side:
  Slit H,V 21,11 gives ±5 rows (a Qz band for Q H) and ±10 columns (a Qxy
  band for Q V). The rows were chosen so that the direct beam, 2α below
  the reflected one, stays out of the Qz band (at Qz 0.01 it is about 7
  rows below on the synthetic frame, computed) — an assumption, recorded
  in OUTPUT_DECISIONS. A Q range that lies off the detector on every
  selected frame (`cuts.covered_range`) is refused with a message, and the
  band is put in the box; before, the cut summed zeros silently.
- **A test changed on purpose (rule 1):**
  `test_detector_sizes.py::test_window_cut_ranges_before_and_after_frames`
  pinned '0:1' and '1:2' after frames were shown. On the synthetic frames
  the Q H default is now '-0.004526:0.02453' (Qz) and the Q V default a
  Qxy band symmetric about 0; before any frame, and for the pixel cuts,
  the defaults are unchanged.

Verified by: tested (`tests/test_gui_cut_axis.py`, 6 tests;
`tests/test_gui_cuts.py`, `tests/test_cut_script.py` unchanged and
passing). Not measured on real diffuse data: the public NX file has no
off-specular frames worth the name.

### 2026-11-25 — D1's core: one reader writes the workbook, a second opens it read-only

Verified by: tests (`test_readerlock.py`, I43); reading only for how the window will use it (the GUI manager's yellow
light, still to build).

- **Why it was needed:** the owner's D1, "Two people can have the same SPEC file open. The second instance opens the
  config read-only, and a small yellow indicator light in the GUI shows that state." The per-SPEC workbook is saved
  by writing a temporary file and replacing the old one. Until now, two readers saving it would each overwrite the
  other's results, without a word.
- **The lock** (`lss_core.readerlock.ReaderLock`): a small JSON file beside the workbook, naming its holder (host,
  process, user, program version, when taken and refreshed).
  - It is taken by exclusive creation, so taking it is atomic.
  - The holder refreshes it every 30 s.
  - It is stale, and taken over, when its file has not been refreshed for 180 s, or when its holder is a process on
    this host that no longer runs.
  - A takeover writes the new lock and reads it back, so two readers taking a stale lock at once cannot both write.
  - A refresh notices if someone took the lock meanwhile, for example after a long sleep.
  - A lock that cannot be written (a read-only folder) means read-only, never an error (D3's spirit).
- **The workbook:** `Workbook(path, read_only=True)` reads and changes in memory, but `save` raises `WorkbookReadOnly`
  (a `PermissionError`) and writes nothing.
- **Assumptions:** the hosts' clocks agree to well within 180 s, since staleness is the lock file's age on this host's
  clock; the 30 s and 180 s are choices, not measurements. Windows has no cheap check of whether a process runs, so
  there only the age decides.
- **Not yet (the GUI manager):** the window takes the lock when it opens a SPEC file, refreshes it on a timer, opens
  the workbook read-only and shows the yellow light when it doesn't have the lock (tooltip: `describe()`), tries
  again from time to time, and releases it on close.

### 2026-11-25 — OQ-1, OQ-4, Q-TL-8 (batch 20)

Verified by: the owner's statements; the arithmetic below is mine. **OQ-1:** the header's slit values are half-openings, so the opening is twice the value: S1 of scan 14 reads 1.00/1.00/0.05/0.05 (L/R/T/B) and so is 2.0 × 0.1 mm. This gives the slit-defined aperture only; the footprint needs the mirror-focused vertical size (OQ-2, the local agent's work on it is in its own PR) and for a Gaussian the choice of FWHM or second moment for the dose (open). **OQ-4:** unknown to the owner; the reader cannot yet recognise fast mode, so the dose default stays "shutter closed" and a user mark is the fallback. **Q-TL-8:** units are mN/m (surface pressure), cm² (barrier area) and percent (O₂); names and whether every scan writes them are still unknown, so F75's columns stay synthetic.

### 2026-11-25 — F92 in the window: drops kept as the mask, Restore all

The window side of main man's mask (#54; owner, 2026-11-23: "saved as a
mask in the config file (the per-SPEC state), and a 'Restore all' button
is included in the patch dialog"). Built:
- **Kept:** when a Ref Patch finishes, its drops become (scan, point)
  pairs (`reflectivity.drop_points` on the scans as the joins started)
  added to the workbook's mask (`masks.save`), with a message. A patch
  cancelled, or a drop undone with Back, records nothing.
- **Left out from the start:** the next Ref Patch of those scans removes
  the masked points after repeats are merged and before the joins, as
  `exp.reflectivity(mask=...)` does; the Script line says `mask=[...]`,
  the provenance line "N masked", and a message lists them. A scan whose
  every selected point is masked is used whole, with a message (else
  Restore all would be out of reach).
- **Drawn apart:** grey crosses, labelled "masked (n)", in the patch
  window (scaled like their scan; the next scan by the factor on show)
  and on the Reflectivity tab (scaled, normalised, offset and divided by
  R_F as the curve is). They are not in the exported files.
- **Restore all** (patch window): clears the mask of this patch's scans
  (not of other scans) and this patch's drops, and starts the patch again
  from the first join.
- **Measured on the synthetic data set:** a drop of scan 2's first point
  at the first join, then the next patch with the mask, give the same
  curve to 1e-12 (I40: no earlier join's fit used that point), and the
  window's curve equals the script's with `mask=[[2, 0]]` to 1e-10.
- **A test changed on purpose (rule 1):**
  `test_gui_ref_patch_steps.py::test_the_line_under_the_plot_says_how_the_result_was_made`
  expected no "saved" part after a drop because the workbook was not open;
  recording the drop's mask opens it, so the line now ends "not saved"
  (true: the result is not in the workbook).
- **Not built:** click to drop or restore a point (F94, low priority). The
  read-only mask for a second reader came with D1's window side the same
  day (below).

Verified by: tested (`tests/test_gui_ref_mask.py`, 4 tests).

### 2026-11-25 — D1 in the window: a second reader is read-only, with a yellow light

The window side of main man's `lss_core.readerlock` (owner's D1: "Two
people can have the same SPEC file open. The second instance opens the
config read-only, and a small yellow indicator light in the GUI shows that
state"). Built:
- **When the lock is taken:** the first time the workbook is needed (a
  save, a mask, the Compare tab, the timeline's notes), not when the SPEC
  file is opened, so that nothing is written beside a SPEC file whose
  workbook is never used (tested: no lock file after opening).
- **Read-only:** the workbook is opened with `read_only=True`; results,
  notes and masks are kept in memory and shown, but every save is refused
  with a plain message (quietly in the status bar for automatic saves).
  The yellow "read-only" light at the right of the status bar names who
  has it open and since when (`describe()`).
- **A timer every 30 s** (`REFRESH_S`) refreshes the lock, or tries again
  for it. Gaining it is said ("saves to it again") and the workbook is
  read again; losing it (another reader took a stale lock, after a long
  sleep) is said and saving stops.
- **Released** on close and when another SPEC file's workbook is needed.
- **Two readers in one process** (tested with two windows): the first to
  need the workbook writes it; the second is read-only until the first
  closes.

Verified by: tested (`tests/test_gui_reader_lock.py`, 6 tests). Not tried
across two computers on a network share; the core's assumptions (clocks
within 180 s) stand.

### 2026-11-25 — The guard's error on real joins: per-point scatter, not the join rule

Verified by: a run (`tests/tools/guard_error_study.py`, synthetic data with known truth, 400 replicates per case;
C61, `docs/studies/guard_error/summary.md`). No default changed.

- **The question:** the local data agent's survey (C56) found the join guard leaving the errors about 24 % too
  small on 1091 real split scans. It proposed inflating by the unguarded fit's χ², or taking the larger error.
- **Reproduced:** with 1 % excess per-point scatter that the stated errors miss, the guard climbs on 94 % of
  smooth joins and today's errors are 39 % too small (pull SD 1.64; 2.45 at 3 %). The ladder accepts a curve
  that fits the noise.
- **The proposals fail at fringed joins:**
  - they repair smooth joins (1.04–1.14), but at the five fringed or short-overlap joins the pull SD falls to
    0.50–0.84;
  - the errors there are 3.1–4.6 × today's;
  - the unguarded fit's χ² there is model misfit, not noise.
- **Honest per-point errors fix both** with today's guard: pull SD 0.94–1.07 everywhere, at errors 1.2–1.5 ×
  today's.
- **So:** no change to the join's rule. The remedy is an excess term in the per-point error budget, once it
  can be estimated from data. That is a next study, together with the real excess by Qz class from the
  owner's data.

### 2026-11-25 — The XRF shootout on real scatter: the owner's blanks with synthetic lines (C63)

Verified by: a run (`tests/tools/xrf_blanks.py`; real scatter-only blanks with synthetic lines of known
photons, 192 conditions x 500 spectra; `docs/studies/xrf_shootout/summary.md` section 10). No default
changed.

- **The owner's question:** had the shootout been tested on real data blanks, which capture the excitation
  scatter accurately, combined with synthetic fluorescence lines? **Not until then:** sections 1-9 used the
  generator's scatter with settings fitted to the blanks.
- **Measured:** the reader with the escape strip (P1+P3) is accurate in 49 of 192 conditions and P1+P2+P3 in 47.
  The best fixed PyMca setting manages 20; PyMca reaches 56 only with its setting picked per condition using
  the truth.
- **New physics the synthetic spectra missed:** the Si escape peak of the scattered beam (E0 - 1.74 keV) sits
  on Ni Ka under a 9.2 keV beam and beside Ti Ka and La La under 6.1 keV. A box fit without the strip reads it
  as a line: P1 +22 % on Ni at line = background, and 26-35 photons per 100 background counts on the bare blank.
- **P2's fixed width costs 4 % on readout A** (Fano 0.137 against P2's 0.115): Zn at 10 keV -4.4 % with
  P1+P2+P3, +0.2 % with P1+P3.
### 2026-11-25 — The XRF shootout on real lines: the 19 private burn series (C64)

Verified by: a run (`tests/tools/xrf_real_series.py`, the private MCA bundle decrypted with the owner's key;
`docs/studies/xrf_shootout/summary.md` section 11). Summary values only. No default changed.

- **Resampled twins** (Poisson draws from a series' own sum / 21) give each method a known answer on real
  shapes. The real counts are Poisson: the line window's variance after drift removal is 1.09 x its mean.
- **At 27-58 line counts per spectrum** P1+P2+P3 is the least biased (-2 to -7.5 %); P1 reads -6 to -25 %.
  P1+P2+P3's pull SD is 0.95-1.11 in every series.
- **The line near 8 keV is 21 % wider (5-37 %) than readout A's resolution measured on the blanks.** P2's
  fixed width (0.93 x that resolution) therefore reads 11 % below the other methods on the high-count sums.
  P2 would need the line's own width.
- **The scatter study's self-consistency check is blind** to a bias shared by the sum: P1 reads 0.0 % there,
  while the twins show -7 to -25 % at the lowest counts.
