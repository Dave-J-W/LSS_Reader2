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
| I4 | Background-subtracted ROI signal S − (L+R)/2 is 0 on a flat image; σ² = σ_S² + (σ_L² + σ_R²)/4 | zero-on-flat tested; error formula read from code only |
| I5 | Normalised GID footprint area lies in (0, 1], is 1 at small 2θ and falls once clipped | tested: `test_gid_area.py` |
| I6 | At the direct-beam row with α = α_true, Q_z = 4π sin α / λ; at the direct-beam column with Det_Th = 0, Q_xy = 0 and the axis is antisymmetric | tested: `test_twod_detector.py` |
| I7 | Stitching two scans of one curve recovers the attenuation factor exactly, and overlap errors fall by √2, when the overlap points coincide | tested: `test_stitching.py` |
| I8 | Reduced reflectivity of each scan is proportional to the true curve (R/R_F flat) | tested end to end on synthetic data: `test_gui_workflows.py` |
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

**A.** Measured by `pytest -m sweep` on the synthetic data set; the full list
is `tests/known_crashes.json`. 368 control/state combinations raise, from 41
distinct code sites, across 85 distinct controls.

| State | Controls that raise |
|---|---|
| empty | 75 |
| spec loaded | 75 |
| motor scan | 62 |
| pilatus scan no frames | 42 |
| pilatus one frame | 18 |
| pilatus two scans all frames | 19 |
| mca frames | 77 |

Most frequent sites:

| Count | Exception and function |
|---|---|
| 73 | `AttributeError in mainwindow.py:update2dPlots` |
| 49 | `ValueError in mainwindow.py:update2dPlotPlot` |
| 40 | `IndexError in mainwindow.py:refQzListSelectionChanged` |
| 36 | `AttributeError in mainwindow.py:updateCutData` |
| 16 | `AttributeError in mainwindow.py:updateCutPlotData` |
| 12 | `ValueError in mainwindow.py:mcaPlotSettings` |
| 10 | `AttributeError in mainwindow.py:refPlotWin` |
| 7 | `AttributeError in mainwindow.py:saveCutData` |
| 7 | `AttributeError in mainwindow.py:updateRefDataList` |
| 7 | `AttributeError in mainwindow.py:update2dIntPolData` |
| 7 | `AttributeError in mainwindow.py:update2dPlotData` |
| 7 | `KeyError in mainwindow.py:updateMcaPlotData` |

The pattern is uniform: handlers read attributes that only exist after some
earlier action (`self.det`, `self.selectedPilFramesNums`, `self.xcenter`,
an item in the Qz list, …) and nothing checks that the action happened. The
counts fall as more data is selected because more of those attributes exist.

Not yet covered: sequences of several controls, file dialogs that return a
path, controls inside the secondary dialogs, Bruker images.

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
