# LSS_Reader — first assessment

Date: 2026-11-14
Assessed commit: `7d2467f` (identical to `chemmatcars/LSS_Reader` main at that date)

How this was produced: the source was read, and the app was launched headless
(`QT_QPA_PLATFORM=offscreen`) on Python 3.13 with PyQt5 5.15.11, NumPy 2.5,
SciPy 1.18, Matplotlib 3.11, lmfit 1.3.4, sympy 1.14. The main window
constructs and `fresnel` / `calArea` return values. **The defects in section 4
were found by reading; none has been reproduced by running the affected code
path yet.** Each should get a failing test before it is fixed.

## 1. What it is

A PyQt5 desktop app for reducing liquid-surface X-ray scattering data from
NSF's ChemMatCARS (APS 15-ID-C, with a partly broken 9-ID-C path). 22 commits,
no tests, no dependency file, no packaging.

| File | Lines | Role |
|---|---|---|
| `mainwindow.py` | 5418 | One `MainWindow` class, about 230 methods; GUI, I/O and all physics mixed together |
| `TwoDDetector.py` | 737 | Pilatus/Bruker image reading, bad-pixel correction, ROI sums, line cuts, 2D Gaussian peak fit |
| `spec_routines.py` | 255 | SPEC file parser (scan data, motor parameters, wavelength, absorber, detector geometry) |
| `mca_routines.py` | 127 | Vortex MCA (fluorescence) file parser |
| `mplwidget.py`, `mpl2dwidget.py` | 27 each | Matplotlib canvas + toolbar widgets (duplicates of each other) |
| `mpl2Dwidget1.py` | 24 | PyQt4 leftover, unused |
| `*.ui` (17 files) | — | Qt Designer layouts, loaded at runtime relative to the current directory |

Tabs: SpecPlot, Apex, Pilatus, Reflectivity, Line/Area Cuts, MCA, Plot, 2D_Plot.

Also committed: a `build/` directory with a Windows exe, a Windows-only
`TwoD_Integrate.pyd`, the Fortran caking source it came from (its import is
commented out at `mainwindow.py:32`), `.idea/`, `attachments.zip`, and a few
reduced-data outputs (`S# *_sumcut.txt`, `temp1.ref`, `temp_ref.txt`).

## 2. Physics to pin down with tests

| Quantity | Where | Formula as coded |
|---|---|---|
| Monitor normalisation and error | `TwoDDetector.sumFiles`, `peakLocate`; `updateSpecPlotData` | I/M, with σ² = σ_I²/M² + I²/M³, times `absfac**absnum` |
| Counting error | `TwoDDetector.openFile` | Pilatus σ = √I; Bruker σ = √(a·I·(1 + b + I/(a·b))), a = 0.1, b = 200 |
| Reflectivity signal | `refAnalyze`, `pilRefPatchData`, `sumROI` | ROI sum − mean of two offset background ROIs; σ² = σ_sig² + (σ_l² + σ_r²)/4 |
| Fresnel reflectivity | `fresnel` | R_F = ((q − √(q²−q_c²))/(q + √(q²−q_c²)))², 1 for q < q_c, no absorption |
| Exit angle β | `updatePilPlotData`, `plotHint` | β = pixel term + arcsin(2 sin α − sin α_true) |
| Q_z | same | Q_z = (2π/λ)(sin β + sin α_true) |
| Q_xy | same, `plotVint` | Q_xy = (4π/λ) sin(2θ/2), 2θ = Det_Th + pixel term |
| Curve stitching | `oneDjoin` | overlap-region scale factor (sum ratio, or weighted fit), cubic interpolation, averaged overlap |
| GID footprint | `calArea` | polygon area of beam footprint seen through the S4/S5 slits, normalised to the full footprint |
| GID polarisation | `pilGIDpatchData` | divide by 1 − (sin 2θ · cos β)² |
| GID image patching | `imagehjoin`, `imagevjoin` | 2D overlap scaling and interpolation |
| Slit/absorber calibration | `g_l2plot`, `g_l3plot`, `calabsrat` | centre = offset − g·sin α; absorber ratio with dead-time term |
| Burn test | `pilRefBurn`, `pilGidBurn` | a·exp(−t/τ) |
| Peak fits | `specPeakFun1/2`, `gaufun`, `lorfun`, `peakFun` | tanh-edge box, Gaussian, Lorentzian, 2D Gaussian |
| Form-factor minima | `pilGIDPlot` | sphere and ellipsoid minima overlays |

Constants hard-coded in many places: Pilatus pixel 0.172 mm, Bruker pixel
0.060 mm, a 32 mm hard-slit offset in `calArea`, GID `vroi=[15,486]`.

Invariants that follow and should become tests:

- R_F = 1 for q ≤ q_c, and R_F → (q_c/2q)⁴ for q ≫ q_c.
- Normalised intensity is unchanged if counts and monitor are scaled together
  in expectation; the relative error obeys (σ/R)² = 1/I + 1/M for Poisson I.
- Background-subtracted signal of a flat image is 0 for any ROI size.
- Pixel → Q → pixel round trip returns the starting pixel (within rounding).
- `calArea` lies in [0, 1], equals 1 when the slits see the whole footprint,
  and is symmetric under 2θ → −2θ.
- `oneDjoin` recovers a known scale factor between two copies of one curve.
- Bad-pixel correction leaves a smooth image unchanged and conserves the total
  of an image with one hot pixel to within the replaced value.

References (cited from memory; DOIs not re-checked in this session):
[Parratt 1954](https://doi.org/10.1103/PhysRev.95.359),
[Als-Nielsen et al. 1994](https://doi.org/10.1016/0370-1573(94)90046-9),
[Pershan & Schlossman 2012](https://doi.org/10.1017/CBO9781139045872).

## 3. Structure problems

- GUI, file I/O and numerics live in one class; almost nothing can be called
  without a `QApplication` and a populated window.
- State is passed through about 200 instance attributes set as side effects
  (`self.xcenter`, `self.distance`, `self.bg`, `self.slit`, …). Call order
  matters and is not enforced. `self.distance` is overwritten with the pinhole
  distance part-way through `updatePilPlotData` (lines 2001, 2015).
- `TwoDDetector` keeps its working image in `self.imageData` and several
  methods silently replace it.
- `.ui` files, icons and `os.chdir` make the app depend on the working
  directory.
- Large duplicated blocks: Bruker vs Pilatus branches, H vs V background,
  low/medium/high-Q_z GID branches, the two halves of `pilRefPatchData`.
- 79 bare `except:` blocks (69 in `mainwindow.py`), several of which turn real
  errors into unrelated warnings.
- `eval` is applied to file contents in both parsers.
- `specread.__init__` has mutable default arguments (`data={}`, `par={}`).

## 4. Defects found by reading

### Crashes or dead features

| # | Location | Problem |
|---|---|---|
| 1 | `mainwindow.py:3046–3134` (`imagehjoin`, `imagevjoin`) | Uses `scipy.interpolate.interp2d`, removed in SciPy 1.14. GID patching of more than one scan will fail; the surrounding bare `except` reports it as "not enough points". |
| 2 | `mainwindow.py:4351` | `sself.updatePilCutRange()` — NameError on a malformed cut range. |
| 3 | `mainwindow.py:2158` | `avepoints` undefined (variable is `avepoint`) in the GIOXS dialog. |
| 4 | `mainwindow.py:620` | `self.SpecData` should be `self.specData`; hit when a non-SPEC file is opened. |
| 5 | `TwoDDetector.py:710` | Parameter is `errodata`, body uses `errordata`. |
| 6 | `mainwindow.py:5282` | `str(getSaveFileName(...))[0]` takes the first character of the tuple's repr; peak-fit save writes to a file named `(`. |
| 7 | `mainwindow.py:4609`, `4659` | `map(float, …)` is an iterator in Python 3; the g_l2/g_l3 dialogs break when centres are typed in by hand. |
| 8 | `spec_routines.py` `APS_9IDC` | Same `map` problem throughout; the 9-ID-C path cannot work on Python 3. |
| 9 | `TwoDDetector.py:137` | Bruker path assigns the `(data, bad_pix_loc)` tuple to `imageData`. |

### Likely wrong numbers

| # | Location | Problem |
|---|---|---|
| 10 | `mainwindow.py:1510` | `pil_S1v = S1T + S1T`; almost certainly meant top + bottom. Feeds the GID footprint correction. |
| 11 | `mainwindow.py:2617` | First high-Q_z GID frame of each scan is not multiplied by the average monitor, unlike every other branch. |
| 12 | `mainwindow.py:2673` | `self.pilhintHQDatadic[MQkeys[0]]` indexes the high-Q_z data with the medium-Q_z keys. |
| 13 | `mainwindow.py:4713` | Absorber-ratio fit curve is drawn with the initial guess `par[0]` in the dead-time term instead of the fitted `fp[0]`. |
| 14 | `TwoDDetector.py:168–169` | Bad-pixel detection uses `factor`, replacement does not; and `mainwindow.py:1660/1667` read the factor from the GUI but never pass it. |
| 15 | `mainwindow.py:3724` vs `3754` | The low-Q_z slit override (slit height forced to 5 for 0.02 < Q_z < 0.03) honours its checkbox only for the second and later frames of a scan; the first frame is always overridden. |
| 16 | `mainwindow.py:3465`, `3474` | Bruker ROI display sets `vmin` with `np.max`. Display only. |
| 17 | `updatePilPlotData` vs `TwoDDetector.plotHint/plotVint` | Image axes use the small-angle form (pixel·size/distance); line cuts use `arctan`. The two disagree at large angles. |
| 18 | `TwoD_Integrate.f90` | The `else` branch writes `integ(irad,ichi)` with out-of-range indices. Unused today, but must be fixed before it is revived. |

### Hygiene

- `build/`, `.idea/`, the `.pyd` and `attachments.zip` should not be tracked.
- Two README files; no install or run instructions.
- No `requirements.txt` / `pyproject.toml`.

## 5. Suggested order of work

1. **Test scaffolding.** `pyproject.toml`, pytest, a headless Qt fixture,
   synthetic SPEC/TIFF/MCA generators.
2. **Characterisation tests** that freeze current numerical output of every
   function in section 2, plus the analytic invariant tests.
3. **Bug fixes** from section 4, one commit and one test each. Where a fix
   changes numbers (10–15, 17), record before/after in `docs/physics_notes.md`.
4. **Extract physics** into GUI-free modules (geometry, normalisation,
   reflectivity, GID, stitching, fitting, I/O), keeping the characterisation
   tests green.
5. **GUI reorganisation and new features** on top of the extracted core.

## 6. Open questions for the maintainers

- Is `S1T + S1T` (defect 10) intentional?
- Should the image axes or the line cuts define the reference geometry
  (defect 17)?
- Is the 9-ID-C path still needed?
- Is real sample data (SPEC + Pilatus + MCA) available for regression
  baselines? The repository holds reduced outputs only.

## 7. Addendum after running tests and real data (2026-11-14)

Measured, not read. Details and numbers are in `physics_notes.md`.

- Reproduced by test: defects 1, 2, 4, 5 and 14 of section 4, and the shared
  default dictionaries in `specread`.
- New: 420 control/state combinations raise from a clean state, and sequences
  of controls reach 11 more crash sites (`tests/known_crashes.json`,
  `tests/known_crash_sites.json`; an earlier count of 368 came from a less
  strict sweep).
- New: the stitching scale factor is biased 1.2–1.3 % low when the two scans
  do not share Q_z points in the overlap.
- New: `calArea` is not symmetric in ±2θ (2 % at 20°). The symmetry claim in
  section 2 is therefore an expectation the code does not meet.
- New: the SpecPlot "FWHM" is the width of a box model, 14 % below the true
  FWHM for a Gaussian.
- New: a SPEC file with repeated scan numbers leaves the window without
  detector paths and selecting a scan raises.
- New: Pilatus 1M data (`#B5` header, `pilatus1m/` folder) are not read at
  all by this version.
- Real NX school data reduce end to end; scans 6–9 give a plausible DPPC
  reflectivity curve, now frozen as a regression reference.

Correction to section 3: there are 79 bare `except:` blocks, as stated there;
an earlier verbal estimate of "about 60" was low.

Additional open questions:

- Is there a newer production version of the reader that handles Pilatus 1M
  (`#B5`, `pilatus1m/`)? If so, the work should start from it.
- Is 2θ ever negative in practice for GID (relevant to the `calArea`
  asymmetry)?

## 8. Python 2 → 3 audit (2026-11-14)

Static scan of the four modules for the usual migration leftovers, each
confirmed by reading the surrounding code. Items marked "test" have an
expected-failure test in `tests/test_known_defects.py`.

| Where | Leftover | Effect | Status |
|---|---|---|---|
| `TwoDDetector.py:74-83` | Header of a Bruker frame is read in binary mode and used as text: keys are `bytes`, lookups use `str`, values go through `eval`. | No Bruker (Apex CCD) image can be opened. The whole Apex tab is dead. | test |
| `TwoDDetector.py:137` | `removeBadPix` now returns `(data, list)`; the Bruker caller was not updated. | Second reason Bruker images cannot be used. | defect 9 |
| `mainwindow.py:1920-1923` | `col=N/row+...` is a float in Python 3 and is passed to `add_subplot` (Bruker multi-frame plot). The Pilatus copy at 2075 was fixed with `int()`. | Raises once Bruker reading works. | read only |
| `mainwindow.py:4609`, `4659` | `map(float, ...)` kept as an iterator, later used as an array and indexed. | g_l2 / g_l3 calibration fails when centres are typed in. | defect 7, test |
| `spec_routines.py:225`, `231` and the rest of `APS_9IDC` | `map(eval, ...)` then `len()` and indexing. | 9-ID-C SPEC files cannot be read. | defect 8 |
| `spec_routines.py:135-136` | `'... %d',num,'...'` builds a tuple, not a formatted string (a Python 2 `print` statement turned into an assignment). | The stored message is a tuple; harmless until displayed. | read only |
| `mainwindow.py:5282` | `str(getSaveFileName(...))[0]`: PyQt4 returned a string, PyQt5 returns `(name, filter)`. | Peak-fit save writes to a file named `(`. | defect 6 |
| `mainwindow.py` (260 lines) | Old-style `SIGNAL(...)` connects left as comments beside the new ones. | None at run time; noise. | cosmetic |
| `mpl2Dwidget1.py`, comment in `LSS_Reader.py` | PyQt4 imports. | Module cannot be imported; it is unused. | cosmetic |
| `mainwindow.py` (96 places) | `checkState()!=0` style integer comparisons. | Works in PyQt5; would break under PyQt6, where the state is an enum. | note for later |
| both parsers | `eval` on every number read from disk. | Slow (16 ms per MCA spectrum) and executes file contents. | defect, F6 |

Not found: dictionary views indexed as lists, `has_key`, `iteritems`,
`xrange`, `unicode`, integer division used for indexing other than the case
above (the ROI code already uses `//`).

Library drift, separate from the language migration: `interp2d` removed from
SciPy (defect 1); `Image.getdata` deprecated in Pillow and assigning to
`ndarray.shape` deprecated in NumPy (both in `TwoDDetector.openFile`);
`pylab` used as a NumPy namespace (`pl.where`, `pylab.sin`).
