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
