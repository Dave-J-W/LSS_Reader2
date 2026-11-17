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
