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
| I10 | (to hold once F24 is built) Every row of the scan-weight matrix W sums to 1; Σ is symmetric, positive semi-definite, with zero row and column for the anchor scan; corrected error ≥ counting-only error, equal on the anchor scan's non-overlap points | specified in hand-off §3.3–3.4, §5; no code yet |
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

