# Requirements and feature requests

As stated by the project owner. Status is updated as work lands.

## Standing requirements

| # | Requirement | Stated | Status |
|---|---|---|---|
| R1 | Verification tests preserve the physical and mathematical behaviour through debugging and refactoring. | 2026-11-14 | Scaffolding in place; see `TESTING.md`. |
| R2 | Finish the Python 2 → 3 migration, which is incomplete and has caused problems. | 2026-11-14 | Known leftovers listed in `ASSESSMENT.md` section 4; Stage 1 fixed defects 1–7, 14 and D14 (2026-11-17). |
| R3 | The interface never crashes, whichever files are selected and whichever controls are used afterwards. *(Stage 0 done 2026-11-17: a failing action no longer closes the program; the individual failures remain to be repaired.)* | 2026-11-14 | Measured by `pytest -m sweep`: 0 failing controls and 0 crash sites since 2026-11-17 (420 combinations raised before Stage 1); the sweep passes on every GUI change since. |
| R4 | Better GUI organisation. | 2026-11-14 | Not started. |

## Feature requests

### Live data (stated 2026-11-14)

| # | Request | Notes on the current code |
|---|---|---|
| F1 | Refresh the SPEC file and raw data without overwriting what is already in memory. | `readSpecFile` already re-reads from the last scan's line (`startLineNum`) into the existing dictionaries, but `clearAll` then wipes the scan list, selection and every plot. |
| F2 | Refresh automatically as SPEC appends to the file; no "refresh" button press. | Nothing watches the file today. |
| F3 | New raw data (images, MCA files) is picked up as soon as it is written. | Frame lists are built once, when a scan is selected (`updatePilImageList` globs the directory). |
| F4 | New points appear automatically in the preview pane, with one or several scans selected. | Depends on F1–F3 and on keeping the selection across a refresh. |
| F5 | Reduced X-ray reflectivity plots update the same way. | Reduction is driven by button presses and stores results in window attributes. |

Design points to settle before building: a partially written last line or
image must be tolerated and retried; the scan being written must be re-read
while finished scans are not; the watcher must work on a network drive, where
file-change notifications are unreliable and polling of size and modification
time is the safe default.

### Speed (stated 2026-11-14)

| # | Request | Notes on the current code |
|---|---|---|
| F6 | Faster MCA spectrum processing. | `mcaread` parses every number with `eval` and re-reads the whole file on each selection. |
| F7 | Faster processing of the larger Pilatus 1M images. | `TwoDDetector.openFile` converts each image through a Python list (`getdata()`); bad-pixel correction builds several padded copies per iteration. |
| F8 | Local disk cache, because production reads from a network drive. | No caching; every selection re-reads from source. |
| F9 | RAM cache sized to what the host has. | Images are held in plain dictionaries with no limit and are discarded on reselection. |

Design points to settle: cache entries must be keyed by path, size and
modification time so that a file still being written is not served stale;
the disk cache needs a size cap and a location setting; the RAM cache needs a
budget derived from available memory with least-recently-used eviction.

### Stability and error handling (stated 2026-11-14)

| # | Request | Notes on the current code |
|---|---|---|
| F10 | No crashing, ever; GUI stability is a very high priority. (Restates R3 as a design goal, not only a test target.) | 420 control/state combinations raise today. PyQt5 aborts the whole process on an unhandled exception in a slot unless an exception hook is installed, and none is. |
| F11 | A failed operation (for example a reduction that does not match the selected data) is reported in a debug log at minimum. Most failures should **not** raise an on-screen dialog; that is too inconvenient. | 82 `messageBox` calls, all modal (`exec_`), many for routine conditions. About 29 `print` calls go to a console the user may not have. 79 bare `except:` blocks hide the real cause. |
| F12 | A durable error log, written automatically and robust to application crashes, so that later debugging is easy. | No logging of any kind. |

Design points to settle: one central place where every slot's failure is
caught, logged with traceback and context (SPEC file, selection, control),
and shown unobtrusively (status bar, log pane) with dialogs kept for the few
cases that need a decision; the log must be flushed per record so a hard
crash loses nothing, and should also catch faults below Python
(`faulthandler`) and Qt's own warnings; log size needs a cap or rotation.

### Per-SPEC-file configuration and log (stated 2026-11-14)

| # | Request | Notes on the current code |
|---|---|---|
| F13 | Every SPEC file gets an associated reader config file and log file, saved in the same folder as the SPEC file. | Nothing is persisted between sessions. The reader does already write `temp_ref.txt` into the SPEC folder on every reflectivity plot. |
| F14 | The reader never writes to the SPEC file. | True today: the file is only opened for reading. Now pinned by `test_reader_never_modifies_the_spec_file`. |
| F15 | The config records every GUI parameter change, and what data is loaded in the flexible-plotting panels. | Parameters live only in widgets and about 200 window attributes; the Plot and 2D_Plot tabs keep their file lists in memory. |
| F16 | Results of interactive steps are saved. Example: points dropped during reflectivity patching are kept, drawn in a visually distinct way, can be undone and redone, and persist when the reader is closed and reopened. | `pilRefPatchDrop` deletes the rows from the arrays (`np.delete`); the points are gone, nothing is recorded, and there is no undo. |

Settled (see D1–D3 below): second instance is read-only with a yellow
indicator; local fallback with a warning; dropped points as a mask.
Still to settle: writes must be atomic (write a temporary file, then
rename) and infrequent on a network drive; how the first instance's lock is
held and what happens when that instance dies without releasing it; whether
a read-only instance sees the first instance's changes live; the config
needs a version number and must
survive a SPEC file that has grown since it was written (F1–F5); how this
file relates to the caches of F8–F9.

### Detector support (stated 2026-11-14)

The owner confirmed that another version of the reader exists which handles
the Pilatus 1M, but that it is not better in other respects. Work continues
from this repository, and 1M support is treated as a feature group here
rather than by switching code base.

| # | Request | Notes on the current code |
|---|---|---|
| F17 | Read Pilatus 1M data. | Geometry is on a `#B5` SPEC header line (`#B5 x y distance 0`), which `spec_routines.py` ignores (it knows `#B1`, `#B2`). Images are in `pilatus1m/`; the window only looks in `pilatus/`. Result today: the scans are listed with zero frames and no message. |
| F18 | Pilatus 1M images go through the same reduction paths as the 100K (display, cuts, reflectivity, GID/GISAXS as applicable). | Image size 981 × 1043 against 487 × 195. Hard-coded 100K assumptions to remove: the `[15, 486]` GID row range, cut-range defaults `0:485` and `0:194`, the left-right flip `NCOLS - X - 1`, ROI and slit defaults. Pixel size is 0.172 mm for both. |
| F19 | Pilatus 1M processing is fast (see F7). | Reader costs 37 ms per 1M image against 1.8 ms for a plain NumPy read; each image is 4.1 MB, so re-reading on every selection change (see `timings.md`) costs ten times more than for the 100K. |

To settle with the owner: which SPEC counter column is the 1M signal
(`Pilatus1M` appears in `#L`); whether one scan can have both 100K and 1M
images; module gaps and masked pixels on the 1M (the 100K has none) and how
they should enter ROI sums and bad-pixel correction; whether the other
version's 1M code should be used as the reference for expected numbers.

Related observation, not yet a request: the October run also writes
per-point MCA files (`#S n mca_save_point Point:k Scan:m`, XSP3 detector)
for ordinary scans. `mcaread` parses them but the window cannot reach them.

### Decisions and additions from the owner (2026-11-15)

Answers to the open design questions, and new requests that came with them.

| # | Decision or request | Applies to |
|---|---|---|
| D1 | Two people can have the same SPEC file open. The second instance opens the config **read-only**, and a small **yellow indicator light** in the GUI shows that state. | F13, F15, F16 |
| D2 | Dropped points are stored as a mask over raw frames (scan and frame number), not as edited arrays; reduction can always be repeated from raw data and undo/redo is a change to the mask. Confirmed. | F16 |
| D3 | If the config or log cannot be written beside the SPEC file (an edge case), store it locally somewhere reliable and warn that this was done. Worst case nothing can be written and the user simply gets the defaults. Never an error. | F12, F13 |
| D4 | The process abort on a raising handler is to be fixed ("a thorn in our side for ages"). Sequence agreed: first a process-wide handler that logs and carries on, then repair of individual handlers. | F10–F12 |
| D5 | Re-reading every selected frame on every selection change, and problems like it, are to be fixed. | F6–F9 |
| D6 | Normalisation stays as it is (per monitor count) by default. | — |
| F20 | Optional **per-second** value for important quantities. | new |
| F21 | Use a **photons-in estimate** stored in the SPEC file, once the beamline writes one (planned on the beamline side; format not yet defined). | new, waits on beamline |
| D7 | Every fitting feature already in the reader stays. xmodfit is far more sophisticated and remains the fitting platform. | scope |
| F22 | Better fitting and more types of fitting in the places inside the reader where it is needed. | **Closed 2026-11-21** (owner: "close F22 if within reach"; the burn-test fits, F22a 3–4, closed the same day): `lss_core/peaks.py` (find, fit Gaussian/Lorentzian/pseudo-Voigt with backgrounds, series, lines, edges, plateaus, scan shapes) used by the line cuts ("Fit peaks"), the MCA tab ("Fit lines"), SpecPlot (scan shape, P9 fixed) and the distance calibration. |
| F22a | **Fitting requirements** (owner, 2026-11-19): (1) all fits need improving — **done** for cuts, MCA, SpecPlot (peaks module); (2) the Gaussian fitting breaks easily — **done** (bounded, unweighted start, failures reported); (3) burn-test dynamics fitting not robust (P30: raw counts, list-row time) — **done 2026-11-21**: the burn dialog's Trends tab (`lss_core/burn.py`, `lss_core/trends.py`): per Monc, measured time, constant / linear / exponential / double exponential by AICc, "stable" when a constant fits as well as a line, the 95 % confident time to a 5 % change; (4) GID burn tests: largest peak by default, override to another Qxy section — **done 2026-11-21**: intensity, position and FWHM at once, each on its own panel with a right axis in percent and the summary beside them, the window around the strongest peak of the mean frame or a typed range; (5) a fit for a planned sh-scan half-cut (F43) — **done**: `peaks.fit_edge` (edge FWHM = beam FWHM), SpecPlot picks it by itself (`fit_scan`); (6) MCA series: lines with a Gaussian on a linear/quadratic/cubic background, the sum fixes position and width, each spectrum amplitude and background only — **done**: `peaks.fit_series`, MCA "Fit lines". | built 2026-11-21 |
| D8 | The Bruker/Apex CCD is defunct and will not be used again. Its code path does not need to work and can be removed when implementation starts. | scope |
| F23 | Improve GID patching, both in flexibility (image overlaps) and in methods. A substantial sub-project that needs its own scoping; the `interp2d` failure (defect 1) is part of it. | new, needs scoping |
| — | Output files read by xmodfit: hand-off received 2026-11-15, see F24–F25. | done |

### Further answers from the owner (2026-11-15)

| # | Decision or request | Applies to |
|---|---|---|
| R5 | A frozen benchmark (the program's own output today) is needed for **each type of data reduction**, especially reflectivity and XFNTR (fluorescence near total reflection). | R1; see `TESTING.md` |
| D9 | One SPEC file may contain scans from different detectors (100K, 200K, 1M); a single scan never mixes detectors. | F17–F19 |
| D10 | The SPEC counter for the area detector's region of interest is `proi` ("Pilatus region of interest"): the ROI is set up in EPICS and recorded by SPEC. The reader does not rely on it; it loads the image files and does the reduction itself with more options ("virtual slits"). | context |
| D11 | Module gaps and bad pixels: avoided by construction for reflectivity. They are a real issue for GID and GISAXS. For now, note the issues carefully; scoping comes later. | F18, F23 |
| D12 | The Pilatus 200K is the workhorse detector, and its output should be the reference for expected numbers. | see note below |
| D13 | For now, experiments make sure overlapping reflectivity scans share Q_z points (within resolution). The interpolation bias in the stitch factor is to be remedied later and must not be forgotten. | F24; tracked in `TODO.md` |
| — | XModJointFit is unreleased and not public. Work around its absence for now; remind the owner to supply `tests/lss_reference.py` and `covariance_core.py`. | F24 acceptance tests 5, 6 |

Note on D10 and D12, from the sample data in hand (measured): none of the
nine SPEC files has a column named `proi`; the area-detector columns are
called `Pilatus`, `Pilatus1M` and `Pil300K`. Every image is either
487 × 195 pixels (871 files, the size of a Pilatus 100K) or 981 × 1043
(366 files, Pilatus 1M); a Pilatus 200K frame would be 487 × 407. So either
the sample sets contain no 200K data, or the 487 × 195 frames are what the
beamline calls the 200K. **Resolved (D43, 2026-11-19):** they are the 200K with one module saved on purpose.

Module-gap and bad-pixel issues noted so far (D11), all read from code
unless marked:
- `removeBadPix` compares each pixel with the mean of its four neighbours
  and replaces it when it is both above a threshold multiple of that mean
  and above a global level. A gap (rows or columns of zero or −1) next to
  real signal makes the neighbours' mean wrong for every pixel bordering
  the gap, in both directions.
- Nothing masks pixels: ROI sums, line cuts, GID/GISAXS maps and the
  "sum" image include gap pixels as zeros, which lowers sums and averages
  without any flag. Negative gap values (−1, −2 in Pilatus files) would
  enter sums and take √ of a negative number in the error.
- GID patching (`plotHint` over `vroi=[15,486]`) assumes a gap-free strip
  487 pixels long.
- Measured: the 1M frames in the sample set are 981 × 1043 and the reader's
  code path loads them when called directly, but no reduction path has been
  run on them, so the effect of the gaps is not yet measured.

### Data export for xmodfit (stated 2026-11-15)

The owner supplied a hand-off written for this work,
[handoff/19-lss-reader-covariance-contract.md](handoff/19-lss-reader-covariance-contract.md).
It is the specification; the rows below only index it.

| # | Request | Notes |
|---|---|---|
| F24 | Write the stitching covariance for xmodfit: next to every `_ref.txt` / `_rrf.txt` a `.cov.json` sidecar (schema version 1) carrying the counting-only error `sigma_meas`, per-point scan weights `W` and the covariance `Σ` of the per-scan log scale errors. | Hand-off §2 (contract), §3 (arithmetic). xmodfit already reads the file; nothing writes it yet. |
| F24a | Two outputs from one run: **corrected** `_ref.txt` / `_rrf.txt` (factor fitted against counting errors with inflate-only χ², error column = √ of the covariance diagonal) and **legacy** `_ref_legacy.txt` / `_rrf_legacy.txt`, byte-identical to today's files. | Hand-off §2.5, §3.2, §3.4. The legacy bytes are now held as fixtures: `tests/test_ref_export_golden.py`, `tests/reference/legacy_export/`. |
| F24b | Fix the Qz² display option corrupting the saved `_rrf.txt` (q column squared). The only change permitted to the legacy output. | Hand-off trap T8. Reproduced and pinned as an expected failure. |
| F24c | Optionally a combined data + covariance JSON file (`<name>_ref.json`). | Hand-off §2.6. The xmodfit loader for it is not built yet; text files and sidecars stay. |
| F25 | **ORSO-compliant export** (via `orsopy`) as an extension or option. Not in the hand-off; added at the owner's request. | Nothing exists. The ORSO text format (`.ort`) has a YAML header (data source, instrument settings, reduction provenance, column definitions with units) followed by columns Qz, R, sR and optionally sQz. See <https://www.reflectometry.org/> and <https://orsopy.readthedocs.io/>. |

Points to settle for F25: which reader quantities map to the ORSO header
(wavelength or energy, incident-angle range, polarisation, sample name,
owner, SPEC file and scan numbers as the data source, reduction steps and
their parameters); whether the resolution column sQz is wanted and how it
would be computed from the slits; whether the ORSO file carries the
corrected or the legacy error column (the corrected one, presumably); and
how the full covariance is referenced, since the ORSO column format has no
place for it.

### Feature list, third instalment (2026-11-15; the owner says it is still not complete)

Items the owner repeated are mapped to their existing numbers; new ones get
new numbers.

| Owner's item | # | Notes |
|---|---|---|
| RAM caching | F9 | repeat |
| Local disk caching | F8 | repeat |
| Live SPEC file updating | F1–F5 | repeat |
| More flexible GID patching (different algorithm option?) | F23 | repeat; adds: the algorithm should be selectable |
| Export ORSO … | F25 | repeat |
| Pilatus 1M … | F17–F19 | repeat |
| Open SPEC files gracefully (no meaningless errors) | **F27** | Today: a non-SPEC file raises (defect 4); a file with repeated scan numbers warns, then breaks later selections; selecting a fluorescence scan always shows "not regular Spec scan"; missing detector folders open a directory chooser; scans that were aborted produce "Something wrong with Scan Number". Each needs a defined, quiet behaviour (F11). |
| Open the new fluorescence & GID SPEC file | **F28** | Needs a sample file and a description of what is new in it. Possibly related to the per-point MCA files seen in the October run (`mca_save_point`, below). |
| Open HDF5 (bluesky) | **F29** | No HDF5 support exists. Needs a sample file and the layout (bluesky/NeXus conventions, where monitor, motor positions, detector frames and MCA spectra live). Implies a reader interface behind which SPEC and HDF5 are interchangeable. |
| … and/or HDF5 reduced-data export | **F30** | With F25. Layout to be chosen (NeXus `NXcanSAS`/ORSO's HDF5 variant are candidates to look at). |
| Reduction entirely scriptable | **F31** | Today every reduction step lives in a window method reading widgets. Needs the GUI-free reduction core (assessment step 4) with a documented Python API; the GUI then calls the same functions. Also the cleanest way to test. |
| Tool to design a GID-patched scan | **F32** | New. Given detector, distance and slit settings, propose the detector positions (Det_Th, Q_z settings) and overlaps for a patched GID map. Depends on F23's geometry model. |
| … and Pilatus 200K / 100K options | **F33** | Detector model selectable or recognised per scan (D9): size, gaps, pixel size, orientation. Today everything assumes 487 × 195. |
| Vortex ME7 and single-element options | **F34** | Today one spectrum per frame is assumed. |
| Better ME7 data handling (no selecting every 7th row) | **F35** | Measured in the October `bu` run: `vortex/20261019_15_mca` holds 28 spectra for one scan, written as `#S n mca_save_point Point:k …` with detector `XSP3_7Chan` and a `#@CHANNEL` line; the reader lists them as one flat list of frames, so the user must pick out each element by hand. Wanted: spectra grouped by scan point, with per-element and summed views. |

Also decided or requested on 2026-11-15, in reply to findings:

| # | Decision or request | Notes |
|---|---|---|
| F26 | **Improve the accuracy and precision of the uncertainty calculations**; this is in scope. Poisson statistics on `Monc` "is really not" right: the monitor is not a photon count, and the true number of incident photons is probably more than ten times the recorded counts. | See `physics_notes.md` (monitor noise), `PHYSICS_ISSUES.md`, and `reports/monitor_noise.md` when it is written. Affects `sigma_meas` in F24 (corrected chain only). |
| D14 | NumPy 2 scalar formatting (`np.int64(1)` in scan lists) needs **systematic replacement**, not spot fixes. | 15 places build `str([...])` from NumPy integers; one helper for "format a list of scan numbers" should replace them all. |
| D15 | The "not regular Spec scan" message box is **retired** for fluorescence scans. | Part of F11 / F27. |
| D16 | The MCA "Merge" weighted mean goes on the list of physics and mathematics issues. | `PHYSICS_ISSUES.md` item P7. |
| R6 | Burn tests (change over time under the beam, at high flux or not) and MCA peak fitting are **important** and need benchmarks. | R5; `TODO.md`. |
| — | 200K sample data: the owner can provide some. | received 2026-11-19 (one module, D43); a full two-module frame still wanted |

### Feature list, final instalment (2026-11-16; "the rest of the feature set")

Details added to earlier requests:

| # | Added detail |
|---|---|
| F34 | Vortex detectors used: 1, 4 and 7 elements; in future mostly the 1- and 7-element ones. SPEC will be modified (beamline side) to record a detector-differentiator flag in the `#V` header line. Note from the code: `spec_routines.py` currently treats *any* `#V` line as "this scan is a Vortex scan", so the reader must be changed before or together with that SPEC change. |
| F35 | A **fluorescence detector configuration screen/tab** in the reader, first of all for the multi-element detector. XFNTR has used only the central element (1 of 7); EXAFS uses all 7. Both cases must be handled (choose elements, sum or keep separate). |
| F23 | Adds F45 (pinhole-geometry correction) and F40 (multiple exposures) below as parts of the GID sub-project. |

New requests:

| # | Request | Notes on the current code and data |
|---|---|---|
| F36 | **EXAFS reduction with the 7-element detector** (implied by F35: "for EXAFS we use all 7 elements"). | The `bu` September file has 24 `escan` energy scans; the reader has an "Energy" x-axis option for MCA intensities but no EXAFS-specific handling. To be scoped: what the reader should output for EXAFS. |
| F37 | **Per-point timestamps.** The header of each scan has an accurate time; individual points do not, and the `Epoch` column looks like an arbitrarily reset clock. Wanted: know when each point was taken; improve what SPEC writes. | Measured on the nine sample files (`tests/tools/spec_epoch.py`): in six files `Epoch` is seconds since the file's `#E` time, and the first point of each scan follows its `#D` header by 0–15 s. In three files it is not: one file is offset by a constant −1600 s, one drifts by thousands of seconds, and in one the base jumps by 13.9 days at scan 80 (a later SPEC session appending to the same file). So `Epoch` is seconds since the *SPEC session's* base, not the file's. A robust reader-side rule exists already: time of point i = scan `#D` + (Epoch_i − Epoch_first) + the first-point lag. The Pilatus TIFF headers carry exposure time and period but no absolute time. Beamline side: add an absolute-time counter column. **2026-11-19, owner's guidance, reader side built:** new files have `Tstart`, `Tend` (Unix s, 0.01 s) and `#U SeriesT0`; old files keep `Epoch`, whose steps are right but whose base is wrong (never #E + Epoch); the reader tells them apart from #L and handles both (`lss_core/timing.py`, `Experiment.point_times`, `tests/test_timing.py`). |
| F38 | **Remove references to the CCD (Bruker/Apex) detectors throughout the code** — but keep its geometry precedent. The CCD sat on a moving table rather than on the detector arm that carries the 100K/200K, and the Pilatus 1M uses that arrangement too. Two 1M modes: *tracked* (the table follows the beam, which then stays on nearly the same pixels, similar to but not the same as the 200K geometry) and *fixed* (the detector stays put and the beam moves across the image). | Extends D8. In the code the Bruker branch computes the beam position from sample-detector distance, `g_l2`, two-theta and incident angle (`refQzListSelectionChanged`, `updateCcdPlotData`), which is the "beam moves on the image" model; the Pilatus branch assumes the reflected beam stays at the recorded `DBPos`. The 1M needs both, selectable or detected per scan. |
| F39 | **"Scan i of N" lines in the SPEC header** (beamline side) saying how many motor scans the experiment macro contains, so that multi-scan selections and automatic refresh can be handled competently. A macro aborted early leaves later scans missing; that must be handled gracefully. | Reader side built (`lss_core/series.py`: `#U Series` lines, SPEC's abort comment, inferred series in older files); the window does not group scans yet; inference covers reflectivity, gid, xfntr, energy and burn, lined and guessed series together (2026-11-21); the window shows them: Series list above the scan list, whole-series selection by default (D55). Ties to F1–F5 (live refresh) and F27 (graceful opening). The exact header syntax is to be agreed before the SPEC change. |
| F40 | **Multiple exposures at the same conditions for GID**, so that cosmic-ray outliers can be rejected in the image stack before summing. | Today frames at the same position are simply averaged ("Sum"). Needs a per-pixel outlier test across the stack (for example median-based) with Poisson-aware thresholds, and error propagation that knows which pixels were dropped. |
| F41 | **Reflectivity scans that share an absorber setting share one scale factor.** A macro sometimes ends with a scan at the same absorber as the previous one but a different counting time and/or sample area. Such a pair has the same prefactor and should not be fitted to each other; the later scan takes the scalar already derived for the earlier one. | Today every adjacent pair is fitted in its overlap. Monitor normalisation already accounts for counting time. Interacts with the hand-off (F24): two scans sharing a factor share one column of the covariance, i.e. they are one "region" for W and Σ. To be raised with the hand-off's author. |
| F42 | **Q_z offset from the reflection's position on the detector.** When the reflection is not at its normal height on the camera, the Q_z offset is calculated. The normal position can be found from the sh-scan (sample-height scan) images that always precede a reflectivity experiment. | Today: a hand-typed Q offset (`refQoffLineEdit`) applied only in the R/R_F display and `_rrf.txt`; and a warning when the found peak is more than 2 pixels from the recorded position. The NX school set has such sh scans (4, 5, 10, 13: `a2scan sh … oh …`, 21 frames each) to develop against. |
| F43 | **Automatic processing of half-cut scans** to estimate the beam size at the sample (owner, 2026-11-19: a fit for a *planned* sh-scan half-cut, F22a): the beam is blocked progressively and the transmitted intensity gives the profile. | No such data yet; the owner says it will exist. The derivative of the cut curve is the beam profile; the SpecPlot edge fit (tanh model) is a starting point. Also the input for the GID beam response ('beam') and the footprint window (P39): a measured vertical profile instead of a fitted one, ideally next to each GID level (owner, 2026-11-19). |
| F45 | **Pinhole-geometry-corrected GID patching.** IDL code exists and can be supplied if needed. | **Built**: exact per-pixel geometry (IMG_COO_CONV), the default (D40, P38). Before: a "pinhole" check box only swapped the distance used for the horizontal axis. Part of F23; the IDL code would be the reference for expected numbers. Owner, 2026-11-18: the main GID improvement — correct each column's angle before patching, so more columns can be used without smearing the instrumental resolution (D36). Today the GID patch sums the H-slit columns into one profile placed at the frame's detector angle, and uses the sample-detector distance for it. |

Clarification (2026-11-16) on defect 1 and the NX school GID data: the two
GID scans (11 and 12) **can** be patched by this program — under SciPy
older than 1.14. Shown by running it under Python 3.11 / SciPy 1.13.1: the
patch gives an 833 × 41 map with Q_z from −0.04 to 1.25 Å⁻¹. The result is
stored as the reference for the patching test. Under a current SciPy the
same code raises inside the join because the function it calls
(`interp2d`) no longer exists, and the program reports that as "not enough
points".

### Possible extensions (stated 2026-11-16)

Offered by the owner as "a few other possible extensions", so lower
priority than the lists above.

| # | Request | Notes |
|---|---|---|
| F46 | **Compiled Windows and macOS versions** of the reader, so users do not need to know about Python environments. | A PyInstaller recipe for Windows is already in the repository (`LSS_Reader.spec`, with a stale hard-coded path and a committed `build/` folder), so this has been done before for Windows. Needed: `.ui` files, icons and any data loaded relative to the program rather than the working directory (today they are relative to the working directory); a pinned set of library versions; a build per platform (a macOS build must be made on macOS, and unsigned apps are blocked by default there, so signing/notarisation is a decision); a smoke check that the packaged program starts and reduces the sample data. Fits after Stage 2. |
| F47 | **Fluorescence analysis niceties from Matt Newville's tools**: escape peaks, element identification. | Newville's X-ray libraries are open source: XrayDB (line energies, edges, cross-sections; Python package `xraydb`) and Larch (XRF display with line markers, peak fitting, escape and pile-up handling). See <https://xraypy.github.io/XrayDB/> and <https://xraypy.github.io/xraylarch/>. Natural first pieces: element/line markers on the MCA plot from `xraydb`; an escape-peak marker or correction for the detector material (Si for the Vortex: escape peak 1.74 keV below each line); element lookup from a clicked energy. Belongs with the fluorescence configuration tab (F35) and fitting improvements (F22). Licences to be checked before any code is copied rather than called. |
| F48 | **A console window showing the API steps being called** as the GUI is used. | Depends on scriptable reduction (F31): each GUI action calls one documented function, and the console prints that call so it can be copied into a script. The reader already has a faint precedent: a "command" line that records text such as `Ref Patch, scans=[…], slits=[…]`. Also a debugging aid and a companion to the log (F12). |

### Decision (2026-11-17)

| # | Decision | Applies to |
|---|---|---|
| D17 | APS 9-ID-C is not needed. Its readers (never ported from Python 2) are removed and the menu entry is hidden. | defect 8 |

### Requests that follow from the monitor and absorber answers (2026-11-17)

| # | Request | Notes |
|---|---|---|
| F49 | **Absorber factor from the beam energy.** Foils: 50 µm Al per unit at 10 keV and every lower energy (the foils are not changed below 10 keV), copper at 30 keV (owner, D28, D30); 1.4247 at 10 keV (D25). Offer the factor for the scan's energy, exp(μ/ρ(E)·ρ·t), with the user's value as an override. | **built for Al** (2026-11-18): NIST table from the owner's saved page, `lss_core/absorbers.py`; "from E" box beside the field, on by default. Open: the Cu unit thickness at 30 keV. Foils at 10.05 and 10.52 keV: aluminium (answered, D37). |
| F50 | **Fluorescence with absorbers.** The foils are before the sample, so fluorescence is attenuated like the reflected beam; spectra at different absorber settings need a^n to be compared. The XFNTR scans (`getandsave_mca`) record no absorber setting (no `#A` in the SPEC scan, none in the MCA header). | **built** (D24): the reader takes the last `#A` above the scan and says so |
| F51 | **Per-scan monitor scatter σ_scan** for the Student t model, estimated from each scan rather than typed in. The separate analysis used a robust standard deviation of the point-to-point changes, per scan (owner). | **declined** (owner, 2026-11-17): a fixed Student t (D26) |
| F52 | **Monitor gain in the normalisation.** SPEC records `#M Monc Gain <S> <unit>` (SR570 sensitivity, A/V); counts per photon ∝ 1/S, so normalise by M·S/S_ref (S_ref = 5 µA/V since D39; first 1 µA/V), not M. Measured: S changes within files by up to 50×; MCA scans record no `#M` (the last above is taken, as for `#A`). | **built as an option** (owner, 2026-11-17): MCA tab and SpecPlot (one setting, a "/ gain" box beside each monitor choice), `Experiment.fluorescence(monitor_gain=True)`. Off by default. **Pilatus paths too** (owner: extend it; mainly for comparing different SPEC files, since the gain changes only with a large energy change, > ~300 eV): cuts, background images and background-subtracted frames, GID data, frames at one Q_z (Ref analyse). Not Ref Patch or GID patching, which measure the scale. Uninterpretable gains: `reports/monitor_gains.md` |
| F53 | **Simultaneous Pilatus and fluorescence experiments** (owner, 2026-11-17). Select both data types of the same scans to plot and reduce; tabs "Vortex" and "Pilatus" in the window were suggested. Today (read): a scan has one `Detector` (whichever of `#V` / `#B0` comes later in its header wins), the window keeps one `self.det`, and Pilatus frames and MCA spectra share the one image list, so a scan with both shows only one. Needs: a scan holding both detectors in the Sources layer, per-detector selection, and the two tabs. A sample SPEC file with both would pin the format. | Stage 4 (sources, selection) and the R4 GUI work; needs a sample file |
| F54 | **Photons per second from the monitor** (owner, 2026-11-17: a scalar will be provided; built 2026-11-19 from the xray_fluxor hand-off, see the Built table). photons/s = C · I, with the monitor current I = M·S/(G·t) (G the V2F scale, Hz/V). Then fluorescence and reflected counts can be given per incident photon. | **built** from the xray_fluxor hand-off (core and window, 2026-11-19; D41 dark rate). |

### Decisions and requirements (2026-11-17, continued)

| # | Decision or requirement | Applies to |
|---|---|---|
| D18 | Local disk cache default raised to 5 GB. | F8 |
| D19 | Line/area cuts are made of monitor-normalised frames, like every other reduction. | P23 |
| D20 | Error budget accepted: the monitor's uncertainty is applied to the whole sum of a frame (box, line, window, net), not per pixel in quadrature; frames' monitor errors are independent. Built as the "Budget" error model (Errors pane, `errors=` in scripts); "Legacy" stays the default until the corrected/legacy two-file export exists. | P2, P3, P8, F26 |
| D22 | Monitor uncertainty: Gaussian, σ = 0.04 % of `Monc`, constant across counting level, is the default; editable in the window. Student t as an option: σ_scan · w · t₄, ν ≈ 4, width w ≈ 0.94 (0.86–1.01), σ_scan the scan's own scatter or 0.039 % when unknown (scale ≈ 0.037 %; an upper bound, since the analysis used `Monp`, which carries source fluctuations). Both describe the present SR570 + V2F electronics. `Monc` is upstream of the absorbers. | P3, F26 |
| D23 | Absorbers: SPEC's `#A` value is the absorber in units of the absorber factor; 0 is no absorber (direct beam). The factor is ≈ 1.414 per unit at 10 keV by design (the window's default, was 1.606). The foils are before the sample. | D21, F49, F50 |
| D24 | A scan without `#A` takes the absorber setting of the last `#A` above it in the SPEC file; absorbers do not change during a scan (owner). Normalised MCA spectra are multiplied by absfac**n. No `#A` above the scan: setting unknown, no factor. | F50 |
| D25 | Absorber unit at 10 keV: 50 µm of aluminium per unit (each unit is 50 µm more). The default factor is the tabulated value, exp(μ/ρ·ρ·t) = 1.4247 (NIST SRD 126; `lss_core/absorbers.py`), in the window and in scripts. Other energies may use other foils. | F49, P24 |
| D26 | Monitor model option: a **fixed** Student t (ν = 4, scale = 0.94 × 0.039 % = 0.0367 %); "width" is the t's scale parameter, not its SD (owner confirmed). σ_scan is not estimated per scan. | D22, F51 |
| D27 | SPEC macros that write no absorber setting (`getandsave_mca`) go on the beamline to-do list (`TODO.md`). | F50 |
| D28 | Absorber foils: aluminium at 10 keV and lower energies, copper at 30 keV (owner). | F49 |
| D29 | Monitor gain normalisation is an option, off by default (owner). | F52 |
| D30 | The absorber foils are not changed below 10 keV: 50 µm Al per unit at every energy ≤ 10 keV (owner). | F49 |
| D31 | The monitor gain is normally changed only with a large energy change (> ~300 eV); the gain option serves mainly to compare SPEC files. A photons/s estimate (F54) will serve that better. | F52, F54 |
| D32 | 5 µA/V is the usual Monc gain (more than 90 % of runs) (owner, 2026-11-18). | F52 |
| D33 | The bu/2026oct gain lines that cannot be read are malformed (another agent's finding, passed on by the owner); no other SPEC file has such lines. | F52 |
| D34 | Absorber factor from the energy is on by default; the typed value remains as an override (built under F49 from D25, D28, D30). | F49 |
| D21 | Absorbers: no nominal factor where the scale is measured (Ref Patch); where a nominal factor is used it scales all error parts and has no uncertainty, and combining frames of different foil counts on it is reported in the Messages pane. | P2, F41 |
| R7 | Output files in the newer formats (ORSO, HDF5, combined JSON) record the reduction steps and their parameters, so a file can be traced back to how it was made. The legacy text files stay byte-identical. | F24c, F25, F30 |
| — | Owner's expectation: images are normalised first, then reduced. Today they are not (see `physics_notes.md`, 2026-11-17); the frame object of Stage 3 should hold the normalised frame once. | target design |

### Request (2026-11-18)

| # | Request | Notes |
|---|---|---|
| F55 | **Point labels in the SPEC plot as a checkbox** (owner, 2026-11-18). Each point of the SPEC plot carries its index in the scan as a red number; make that an option. | built: 'Point #' next to Legend, on by default (unchanged look until unticked) |

### Requests (2026-11-18, continued)

| # | Request | Notes |
|---|---|---|
| F56 | **Calibrated foils in the reader** (owner, 2026-11-18): use the measured foil table (physics_notes 2026-11-18) wherever the nominal absorber factor was used. | built: with "from E", at 9.70–10.30 keV; field shows "cal" |
| F57 | **Preferences panel** showing the foil assumptions, short, with tooltips; the Ref Patch threshold and the switch for the automatic known ratio. | built: File > Preferences |
| F58 | **Known absorber ratio in Ref Patch**: suggest it in the patch window when the fit's error exceeds the foil ratio's; use it automatically above a threshold where plainly better. | built; automatic only where Monc/Monp shows no slit change (P29) and the two agree within 3σ |
| D35 | Explain in tooltips rather than wordy displays (owner); recorded in AGENTS.md rule 9. | all GUI work |
| F59 | **Cuts for diffuse scattering: intensity against β, β − α, α_f, Qz and Qxy** (a user, via the owner, 2026-11-18: "nothing happens when I try to use Qxy or Qz"; no documentation on making Qz/Qxy cuts to get I vs β or β − α from Pilatus images). Not to be built yet. | Today (read and measured on synthetic data): "Pix V" with axes "Angles" already gives I vs β (degrees; β from the row, the S2D distance and the incidence angle); β − α and α_f are not offered; the Q cuts always plot against Q. **Defect, measured:** the Q V cut's default range is Qxy 1–2 Å⁻¹ and the Q H cut's 0–1 Å⁻¹ in Qz; for a reflectivity/diffuse frame the Qxy range lies off the detector, so the cut integrates nothing and plots zeros with no message (a Qz range off the detector does the same). That is the likely "nothing happens". Needs: a message when the range misses the detector, sensible default ranges from the frame, β − α (and α_f) axes, and a short how-to in the user documentation. |
| F60 | **Contextual or automatic reduction** (owner, 2026-11-18): offer the reductions that fit the selected scans (specular series → Ref Patch, burn scan → burn test, GID set → GID patch, MCA → fluorescence), or run the obvious one automatically. On the docket. | Builds on the scan classification the reader already has (detector per scan, hklscan series, identical scans) and on the session state of Stage 3; belongs with the GUI reorganisation (R4). |
| F61 | **GID patching worksheet** (owner, 2026-11-18): first step of the GID sub-project; show the patching parameters and what the patch did, pixel overlaps and whatever else is hidden in the code. | Parameters found in the code (read, 2026-11-18): columns summed per frame (the H slit field, around the direct-beam column); rows 15–486, fixed; Qz grouping to 0.001 with at most three Qz levels (low, middle, high; a fourth goes into "high"); detector angle rounded to 0.001°; horizontal axis from the sample-detector distance (not the pinhole one); area correction with a fixed 32 mm hard-slit offset and S5 capped at the H slit; polarisation factor 1 − (sin 2θ cos β)²; per-scan average Monc as the scale; horizontal join: linear interpolation of the β-integrated profiles, one scale factor fitted over the overlap; vertical join: data2 interpolated onto data1's angles (2D linear), cubic interpolation of the integrated profiles, last overlap point dropped. Per-join results to show: overlap range, points, factor ± error, χ². |
| F62 | **Flexible GID overlaps** (owner, 2026-11-18; part of F23): patch along Qz when the Qxy ranges of two images do not overlap exactly, and along Qxy when the Qz ranges differ. | Today the vertical join interpolates the second image onto the first's Qxy grid (and so silently extrapolates or drops where they differ), and the horizontal join requires the same β grid. |
| F63 | **Second 200K module for GID** (owner, 2026-11-19): the 200K's other module lies along 2θ, so saving it would extend each GID frame's in-plane range; one module is saved today on purpose (D43). | The reader knows one 487 × 195 module only. Needs: a detector description with both modules and the 17-pixel gap masked (Stage 4, F17–F19), exact per-pixel angles (built, P38), and a check of how far the footprint and S5 windows let the extra columns be used. A full two-module frame from the beamline. **Measured 2026-11-19 (figure review): with the slits of the NX GID scans the second module would see no footprint at GID angles: through S4 its columns look at beam-axis points 58–559 mm or 87–140 mm from the sample (footprint ±32 mm), the footprint window reaches at most column ~123 even at Det_Th 25°, and S5 (columns 27–139) shades both possible positions. Using it needs S4 and S5 set for it, or a different slit arrangement; owner to say how it would be measured.** |
| F65 | **Merging XFNTR scans: the owner's rule** (2026-11-19). (1) Group: one run, one wavelength, one sample (no sample change between; moving `sx` on the same sample is fine), one signal shape, classified per scan: *peaked* (maximum inside the range and the signal falls ≥ 15 % after it) or *monotonic*; never merge different shapes. (2) Match points on target Qz within 0.1 × the grid step (1e-4 1/Å for a 0.001 step), no interpolation. (3) Edge of each scan: steepest rise of ln(Vortex ÷ Monc), refined with a parabola through the neighbouring slopes; consecutive repeats of one shape differ by a robust sd of 2.8e-5 1/Å. (4) Merge without asking if every edge is within 1e-4 1/Å of the group median, else leave the outlier out and flag it. (5) Qz jitter in the error bars: σ(I)/I = \|d ln I/dQz\| × 3e-5 1/Å (matters within a step or two of the edge). (6) Optionally align first: shift each scan by its edge offset before merging the edge points. (7) Never merge across runs (subphases differ; the edge shift between runs is their critical angle). Limit: only 6 peaked scans in the owner's data, so the jitter figures come from monotonic scans; for peaked groups the thresholds are an untested starting point. | **Built 2026-11-19 without the edge check (owner: "too fancy for now"):** step 2 as the Merge's default window (0.1 × the Qz grid step) and step 5 (jitter in the errors on the Qz axis); steps 1 and 7 are the user's choice of scans ("the reader doesn't need to know"); edge estimator (steps 3, 4, 6) backlog. The value merge itself stays the MCA Merge (P7, kept). Real XFNTR data received 2026-11-19 (private; physics_notes "Real XFNTR and GID data"); before that, a draft of the whole rule exists outside the repository. |
| F66 | **Per-SPEC workbook** (owner, 2026-11-21, D53): `<SPEC file>_reader.xlsx` in the output folder; sheets Scans, Saved, Data, Fits, Trends (burn tests, added the same day), Maps, Settings; Save buttons beside the SpecPlot, Reflectivity, Cuts and MCA exports and "Save to workbook" in the GID menu; a note asked on every Save, Shift-click skips (owner, 2026-11-21, second reply; a preference turns it off); fitting options in the preferences and the Settings sheet. | built 2026-11-21 (`lss_core/workbook.py`, `tests/test_workbook.py`, `tests/test_gui_workbook.py`) |
| D40 | Pinhole geometry is the default for GID, display and cuts (frames at Det_Th > 1°) (owner, 2026-11-18). | F45 |
| D41 | Monc dark rate 50 Hz when not recorded (owner, 2026-11-18). | F54 |
| D48 | Dead time: the 7-element Xspress3 corrects its own (nothing in the reader); the 1-element detector's is corrected in the reader by real/live time from #@CTIME (owner, 2026-11-19; already coded). | F34–F36 |
| D49 | A global element selector for the multi-element detector, in the detector configuration (Preferences): EXAFS sums all seven elements, XFNTR uses the central one, element 1 (owner, 2026-11-19). | F34–F36 |
| D50 | Time axes: a true timeline of the selected scans, and each scan from its own start for comparing scans as if they started together (owner, 2026-11-19). | F37, D46 |
| D51 | P39 fix (owner, 2026-11-19: "go ahead with the P39 fix, documentation first"): pinhole GID maps use the exact footprint window, fully lit columns only (inner edge of the S4 ramps); IDL's centred window kept as an option. | P39, F45, F61 |
| D52 | A reusable peak module for GID peaks, cuts and MCA spectra; fitting any line cut automatic with a button press, options in a dialog from a button beside it (owner, 2026-11-21). | F22, F22a |
| D53 | The per-SPEC configuration is an Excel workbook (owner, 2026-11-21): settings, fitting preferences and saved results (reduced data and fits), tied to scan numbers, labelled by experiment type, sortable; one-click Save beside every Export with an optional note, versions kept; Export unchanged (legacy) and the default; 4–7 sheets. | F13–F16, F66 |
| D54 | Burn tests (owner, 2026-11-21): compare average, linear, exponential and double exponential over time by an information criterion; a flat line as good as a line means the good regime (no beam damage); a confident time for a change below 5 % in the quantity of merit; GID: intensity, position and width at once (first two panels with three axes; then, same day: each on its own panel, the right axis normalised in percent, the summary beside the panels); for GID, a relative change matters, so less weight on absolute σ, and the legacy test (constrained range) as the inspiration. Answers the same day: wall (clock) time by default (the shutter closes between exposures); position judgment is the user's; burn scans are `ascan ih` without movement; more burn data later; a hand-off for testing and extension (`docs/handoff_out/07-burn-trends.md`). | F22a 3–4, P30, R6 |
| D55 | Scan series in the scan list (owner, 2026-11-21: "go ahead with series in the scan list"; then "make selecting the entire series the default behavior, and have a checkbox in the selector area to disable that function"). | F39, review R2 |
| D45 | Let users merge what they choose: the reader offers and warns, it does not forbid (owner, 2026-11-19: "they may have a good reason to do a weird thing"). | F65, Merge |
| D46 | Time is offered as an x axis on any plot, as accurate as is known: new files exact (Tstart), old files #D + Epoch steps with the overhead ignored (≲ 1 s), scans without either #D + count times (owner, 2026-11-19). | F37 |
| D47 | The SPEC `Vortex` counter is meaningless for fluorescence; what counts are element lines, fitted with a Gaussian on a linear, quadratic or cubic background (Rayleigh spill-over), normalised by Monc (owner, 2026-11-19). | F22a, F65 |
| D44 | No measurement of `Monc`'s own noise is needed: the Student t monitor model (D26) is good enough (owner, 2026-11-19). Lifts the condition set before a normalisation model is chosen. | D20, D22, D26, F26 |
| D43 | The 200K saves one module on purpose (owner, 2026-11-19): no switching between GID and reflectivity, which needs one module; GID patching did not use the pinhole geometry fully until now. The second module lies along 2θ. | F63 |
| D42 | Pilatus scans need no absorber number: they are patched and normalised all the same (owner, 2026-11-19). An unreadable `#A` is unknown: no factor, no known ratio for its joins, a message. | F50, F58 |
| D37 | Aluminium foils at 10.05 and 10.52 keV and every energy below 10 keV (owner, 2026-11-18); `AL_MAX_KEV` = 10.52. | F49 |
| D38 | `#A` 52 and 63 are real absorber settings (owner, 2026-11-18). | F50 |
| D39 | Monitor-gain reference S_ref = 5 µA/V, the usual gain (owner, 2026-11-18). | F52 |
| D36 | GID sub-project order (owner, 2026-11-18): the worksheet (F61) first; the main improvement is the pinhole-geometry correction (F45) before patching, so more columns of each image can be used without smearing the instrumental resolution; then flexible overlaps (F62). | F23, F45, F61, F62 |

### Status of built items

| # | Built | Where | Checked by |
|---|---|---|---|
| F10 (first half) | A failing action is logged and reported; the program stays open. | `reader_log.install_excepthook`, `LSS_Reader.create_app` | `tests/test_reader_log.py` (real program in a subprocess) |
| F11 | Messages no longer open blocking dialogs; they go to a Messages pane at the bottom of the window and to the log. "About" is the one remaining message dialog. | `MainWindow.notify`, `initMessagePane` | `tests/test_reader_log.py` |
| F12 | Durable log: every record flushed and synced; hard faults recorded; session log in `~/.lss_reader/logs` (or `$LSS_READER_LOG_DIR`). | `reader_log.py` | kill and abort tests in `tests/test_reader_log.py` |
| F13 (log half), D3 | A log per SPEC file, `<spec file>.reader.log` beside it, with a local fallback and a message when the folder cannot be written. | `reader_log.attach_spec_log` | `tests/test_reader_log.py` |
| D15 | No message when a fluorescence scan is selected. | `scanListChanged` | `tests/test_xfntr.py` |
| F10 (second half) | Handlers no longer raise when used before data is loaded or after the selection changed. | guards throughout `mainwindow.py`; `forgetImageSelection` | `pytest -m sweep`; `tests/test_guards_*.py` |
| D14 | Scan lists formatted by one helper. | `listText` | `tests/test_xfntr.py` |
| F56 | Calibrated foils: `lss_core.absorbers.Foils`/`calibrated`; every absorber factor goes through `attenuation()` (a number: the legacy arithmetic). The window uses them with "from E" at 9.70–10.30 keV. | `absorbers.py`, `TwoDDetector.sumFiles`, `normalise`, `fluorescence`, `absFacFromEnergy`, `absorberModel` | `tests/test_absorbers.py`, `tests/test_gui_preferences.py` |
| F57 | File > Preferences: foil table (nominal, calibrated, tooltips with errors and provenance), calibrated switch, Ref Patch auto switch and threshold; saved to JSON. | `buildPreferences`, `lss_core/preferences.py` | `tests/test_gui_preferences.py` |
| F58 | Patch window: "Known ratio" box and a one-line comparison (fit ± vs foils ±); automatic choice by `reflectivity.patch_choice`; the Script pane records `factors=`. | `refJoinInfo`, `refShowKnown`, `pilRefPatchNext`, `stitching.join(factor=)`, `reflectivity.patch(factors=)` | `tests/test_known_ratio_patch.py` |
| F31 (cuts) | Line cuts scriptable and shared with the window; Export writes the call. | `lss_core/cuts.py`, `Experiment.cut`, `updatePilCutData`, `cutScript` | `tests/test_cut_script.py` |
| F46 | Packaged builds: relative-path PyInstaller recipe, pinned libraries, `--self-test` (window opens, NX school reduces byte-identically), GitHub workflow for Windows and macOS (manual or tag). Linux build measured here; Windows/macOS not yet run. | `packaging/`, `LSS_Reader.self_test`, `.github/workflows/build.yml` | `tests/test_packaging.py`; `docs/PACKAGING.md` |
| F61 | GID worksheet (GID menu > Worksheet): columns, rows, Qz grouping, angle rounding, area correction and hard-slit offset, polarisation, vertical-join interpolation; distance and absorber shown; levels and a table of every join (overlap, points, factor ± error, χ²/dof); Patch and Defaults. Defaults reproduce the patch byte for byte. | `lss_core/gid.py`, `buildGIDWorksheet`, `gidLogJoin`, `gidCorrect` | `tests/test_gid_worksheet.py`, `tests/test_real_nx_school.py` |
| F45 (first version) | Pinhole-geometry GID: angle per column, S5 ∩ footprint columns, ΣN/ΣW binning with a fitted column response, one factor per scan of a level; GID worksheet switch (off by default), S4–detector distance (header or typed), response, minimum frames per bin, arm correction, Fit (diagnostic). | `lss_core/pinhole.py`, `gidPinholePatch`, `gidFitPinholeDistance` | `tests/test_pinhole.py`, `tests/test_gid_worksheet.py` |
| F54 (core) | Photons/s from monitor counts: `lss_core.flux.photons_per_second` (xray_fluxor hand-off, route D), bounds and flags; reproduces the hand-off's examples. | `lss_core/flux.py` | `tests/test_flux.py` |
| F65 (steps 2, 5) | MCA Merge: default window 0.1 × the Qz grid step (robust to repeats' jitter); Qz jitter 3e-5 1/Å added to merged errors on the Qz axis through the merge weights; values unchanged (P7 kept); moved to the core and scriptable (`flu.merge`), written to the Script pane. | `fluorescence.merge_rows`, `default_merge_window`, `FluorescenceResult.merge`, `mcaIntMerge` | `tests/test_mca_merge.py` |
| F35 (first part), D49 | Multi-element per-point MCA files: `#@CHANNEL` and `Point:` read; one spectrum per point summing the selected elements (`combine_channels`); global selector in Preferences > Fluorescence detector (default all); `channels=` in scripts, written to the Script pane. | `fluorescence.combine_channels`, `Experiment.spectra/fluorescence(channels=)`, `mcaChannels` | `tests/test_mca_channels.py` |
| D50 | SPEC plot: `Time_s` (true timeline of the selected scans) and `Time_from_start_s` (each scan from its first point). | `addTimeColumn`, `lss_core/timing.py` | `tests/test_timing.py` |
| F39 (reader side) | `#U Series id=… i=… n=… kind=… [role=…]` parsed (proposal `handoff_out/05`); SPEC's abort comment and planned points from the command; series grouped with status complete / partial / in progress / aborted; guessed for files without the line. Window not yet. | `lss_core/series.py`, `spec_routines.py` | `tests/test_series.py` |
| GID script (F31 for GID) | `Experiment.gid` and `GIDResult` (products, save); the window's GID patch, joins, footprint, map products and save moved to `lss_core/gid.py`, one implementation; Save GID writes the call. | `lss_core/gid.py`, `Experiment.gid`, `gidScript` | `tests/test_gid_script.py` |
| F54 (window) | "/ photon" boxes beside "/ gain" (MCA, SpecPlot; also cuts, background images, GID, frames at one Qz): values per incident photon, M/N with N = (M − D·t)·q(E)·S/(500 nA/V); includes the gain; dark 50 Hz (D41); scans with unknown gain or energy keep per-count values, said once. Scripts: `per_photon=True` in `fluorescence` and `cut`. | `flux.photon_factor`, `monitor.scan_rate`, `experiment.monitor_factor`, `setMonitorMode`, `monitorGainFactor` | `tests/test_per_photon.py` |
| P38 / F45 (exact) | Pinhole GID with exact per-pixel (2θ, β): Mati Meron's IMG_COO_CONV ported, checked against an independent ray construction; binned on a (2θ, β) grid over the β range every 2θ bin shares. | `pinhole.pixel_angles`, `pinhole.bin_counts_2d`, `pinhole.level_map` | `tests/test_pinhole.py` |
| F62 (pinhole) | Qz levels joined on a shared 2θ grid and a common β grid, one factor each from intensities over the same cells, ΣN/ΣW; range common (default) or all; worksheet setting. | `pinhole.shared_edges`, `pinhole.join_levels`, `gidPinholePatch` | `tests/test_pinhole.py`, `tests/test_gid_worksheet.py` |
| F55 | 'Point #' checkbox in the SPEC plot options, on by default; unticked, the plot is redrawn with no point labels. Labels a log axis cannot show (≤ 0, non-finite) are hidden either way. | `initSpecPointLabels`, `specPlot`, `specPlotSettings` | `tests/test_guards_remaining.py` |
| F24b | Qz² display option no longer changes the saved `_rrf.txt`. | `updateRefPlotData` | `tests/test_ref_export_golden.py` |
| F27 (part) | Non-SPEC files and repeated scan numbers handled quietly. | `openSpecFile`, `readSpecFile`, `spec_routines.is_spec_file` | `tests/test_known_defects.py`, `tests/test_parsers.py`, `tests/test_real_bu.py` |
| Defect 1 (start of F23) | GID patching runs on current SciPy with unchanged results. | `interp_compat.py` | `tests/test_interp_compat.py`, `tests/test_real_nx_school.py` |
| Beam response (option) | `GIDParams.response='beam'`: the pinhole response as one profile along the beam axis (source point of each column per frame, `ray_geometry`), shared by all frames; gives the beam's centre and FWHM on the sample. Worksheet: response list; levels label shows the 2θ resolution (S4 + pixel, `column_acceptance`) and the beam. Preferences: "Centre" button = element 1. | `pinhole.source_positions`, `beam_response`, `two_theta_resolution` | `tests/test_pinhole.py`, `tests/test_gid_worksheet.py`, `tests/test_mca_channels.py` |
| P39 / D51 | Exact footprint window: fully lit columns only; IDL's high edge on raised-arm frames | `pinhole.usable_columns(footprint='exact')`, worksheet footprint list | `tests/test_pinhole.py`, `tests/test_gid_worksheet.py` |
| Physical response, joins as collected | `response='physical'`, `'physical+fit'` (rays through pixel and S4, Gaussian beam); `apply_joins=False` reports factors without applying them | `pinhole.PhysicalResponse`, `level_map` | `tests/test_pinhole.py`, `tests/test_gid_worksheet.py` |
| P42 | Column responses fitted with each scan's scale | `pinhole.column_response(scans=)`, `beam_response(scans=)` | `tests/test_gid_scan_join.py` |
| P43 (distance calibration) | S4–detector distance from single frames, with a reliability verdict; worksheet Fit | `pinhole.calibrate_distance`, `single_frame_peaks` | `tests/test_pinhole.py`, `tests/test_gid_worksheet.py` |
| D52 / F22 | Peak module: find, fit (Gaussian, Lorentzian, pseudo-Voigt; backgrounds), series, lines, edges, plateaus, scan shapes; Fit peaks / Fit lines buttons with options dialogs | `lss_core/peaks.py`, `MainWindow.fitCuts`, `mcaFitLines`, SpecPlot fit | `tests/test_peaks.py`, `tests/test_gui_peak_fit.py`, `tests/test_gui_workbook.py` |
| F37 (reader side) | Per-point times, old and new files | `lss_core/timing.py`, `Experiment.point_times` | `tests/test_timing.py` |
| F66 / D53 | Per-SPEC workbook with one-click Save beside every Export | `lss_core/workbook.py`, `MainWindow.saveToWorkbook` | `tests/test_workbook.py`, `tests/test_gui_workbook.py` |
| D54 / F22a 3–4 | Burn tests as trends over time (four models by AICc, the 5 % time; Trends tab) | `lss_core/trends.py`, `lss_core/burn.py`, `Experiment.burn` | `tests/test_trends.py`, `tests/test_burn_trends.py`, `tests/test_gui_burn_trends.py` |
| D55 / F39 (window) | Series list above the scan list (one action selects a series); clicking a scan selects its whole series (check box, on by default); row tooltips and tints by kind | `MainWindow.setupSeriesBox`, `updateSeries`, `selectSeries`, `expandToSeries` | `tests/test_gui_series.py` |

## Order

F6–F9, F1–F5 and F13–F16 all need the readers and the reduction to be callable
without the window, with parameters held in one explicit state object
instead of widgets, so they come after the physics is extracted from
`mainwindow.py` (step 4 in `ASSESSMENT.md`). F10–F12 do not depend on that
and can come first: a central exception handler and a log are small,
self-contained, and make every later step easier to debug. Timing
measurements are in `timings.md`.
