# Requirements and feature requests

As stated by the project owner. Status is updated as work lands.

## Standing requirements

| # | Requirement | Stated | Status |
|---|---|---|---|
| R1 | Verification tests preserve the physical and mathematical behaviour through debugging and refactoring. | 2026-11-14 | Scaffolding in place; see `TESTING.md`. |
| R2 | Finish the Python 2 → 3 migration, which is incomplete and has caused problems. | 2026-11-14 | Known leftovers listed in `ASSESSMENT.md` section 4; none fixed yet. |
| R3 | The interface never crashes, whichever files are selected and whichever controls are used afterwards. *(Stage 0 done 2026-11-17: a failing action no longer closes the program; the individual failures remain to be repaired.)* | 2026-11-14 | Measured by `pytest -m sweep`: 420 control/state combinations raise from a clean state, plus 11 further crash sites reached only by sequences (see `physics_notes.md`). |
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
| F22 | Better fitting and more types of fitting in the places inside the reader where it is needed. Which places and which models: to be scoped. | new, needs scoping |
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
beamline calls the 200K. To be clarified.

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
| — | 200K sample data: the owner can provide some. | wanted |

### Feature list, final instalment (2026-11-16; "the rest of the feature set")

Details added to earlier requests:

| # | Added detail |
|---|---|
| F34 | Vortex detectors used: 1, 4 and 7 elements; in future mostly the 1- and 7-element ones. SPEC will be modified (beamline side) to record a detector-differentiator flag in the `#V` header line. Note from the code: `spec_routines.py` currently treats *any* `#V` line as "this scan is a Vortex scan", so the reader must be changed before or together with that SPEC change. |
| F35 | A **fluorescence detector configuration screen/tab** in the reader, first of all for the multi-element detector. XFNTR has used only the central element (1 of 7); EXAFS uses all 7. Both cases must be handled (choose elements, sum or keep separate). |
| F23 | Adds F45 (pinhole-geometry correction) and F44 (multiple exposures) below as parts of the GID sub-project. |

New requests:

| # | Request | Notes on the current code and data |
|---|---|---|
| F36 | **EXAFS reduction with the 7-element detector** (implied by F35: "for EXAFS we use all 7 elements"). | The `bu` September file has 24 `escan` energy scans; the reader has an "Energy" x-axis option for MCA intensities but no EXAFS-specific handling. To be scoped: what the reader should output for EXAFS. |
| F37 | **Per-point timestamps.** The header of each scan has an accurate time; individual points do not, and the `Epoch` column looks like an arbitrarily reset clock. Wanted: know when each point was taken; improve what SPEC writes. | Measured on the nine sample files (`tests/tools/spec_epoch.py`): in six files `Epoch` is seconds since the file's `#E` time, and the first point of each scan follows its `#D` header by 0–15 s. In three files it is not: one file is offset by a constant −1600 s, one drifts by thousands of seconds, and in one the base jumps by 13.9 days at scan 80 (a later SPEC session appending to the same file). So `Epoch` is seconds since the *SPEC session's* base, not the file's. A robust reader-side rule exists already: time of point i = scan `#D` + (Epoch_i − Epoch_first) + the first-point lag. The Pilatus TIFF headers carry exposure time and period but no absolute time. Beamline side: add an absolute-time counter column. |
| F38 | **Remove references to the CCD (Bruker/Apex) detectors throughout the code** — but keep its geometry precedent. The CCD sat on a moving table rather than on the detector arm that carries the 100K/200K, and the Pilatus 1M uses that arrangement too. Two 1M modes: *tracked* (the table follows the beam, which then stays on nearly the same pixels, similar to but not the same as the 200K geometry) and *fixed* (the detector stays put and the beam moves across the image). | Extends D8. In the code the Bruker branch computes the beam position from sample-detector distance, `g_l2`, two-theta and incident angle (`refQzListSelectionChanged`, `updateCcdPlotData`), which is the "beam moves on the image" model; the Pilatus branch assumes the reflected beam stays at the recorded `DBPos`. The 1M needs both, selectable or detected per scan. |
| F39 | **"Scan i of N" lines in the SPEC header** (beamline side) saying how many motor scans the experiment macro contains, so that multi-scan selections and automatic refresh can be handled competently. A macro aborted early leaves later scans missing; that must be handled gracefully. | Nothing groups scans today; the user selects scans by hand. Ties to F1–F5 (live refresh) and F27 (graceful opening). The exact header syntax is to be agreed before the SPEC change. |
| F40 | **Multiple exposures at the same conditions for GID**, so that cosmic-ray outliers can be rejected in the image stack before summing. | Today frames at the same position are simply averaged ("Sum"). Needs a per-pixel outlier test across the stack (for example median-based) with Poisson-aware thresholds, and error propagation that knows which pixels were dropped. |
| F41 | **Reflectivity scans that share an absorber setting share one scale factor.** A macro sometimes ends with a scan at the same absorber as the previous one but a different counting time and/or sample area. Such a pair has the same prefactor and should not be fitted to each other; the later scan takes the scalar already derived for the earlier one. | Today every adjacent pair is fitted in its overlap. Monitor normalisation already accounts for counting time. Interacts with the hand-off (F24): two scans sharing a factor share one column of the covariance, i.e. they are one "region" for W and Σ. To be raised with the hand-off's author. |
| F42 | **Q_z offset from the reflection's position on the detector.** When the reflection is not at its normal height on the camera, the Q_z offset is calculated. The normal position can be found from the sh-scan (sample-height scan) images that always precede a reflectivity experiment. | Today: a hand-typed Q offset (`refQoffLineEdit`) applied only in the R/R_F display and `_rrf.txt`; and a warning when the found peak is more than 2 pixels from the recorded position. The NX school set has such sh scans (4, 5, 10, 13: `a2scan sh … oh …`, 21 frames each) to develop against. |
| F43 | **Automatic processing of half-cut scans** to estimate the beam size at the sample: the beam is blocked progressively and the transmitted intensity gives the profile. | No such data yet; the owner says it will exist. The derivative of the cut curve is the beam profile; the SpecPlot edge fit (tanh model) is a starting point. |
| F45 | **Pinhole-geometry-corrected GID patching.** IDL code exists and can be supplied if needed. | Today a "pinhole" check box only swaps the distance used for the horizontal axis. Part of F23; the IDL code would be the reference for expected numbers. |

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
| F49 | **Absorber factor from the beam energy.** Foils: 50 µm Al per unit at 10 keV and every lower energy (the foils are not changed below 10 keV), copper at 30 keV (owner, D28, D30); 1.4247 at 10 keV (D25). Offer the factor for the scan's energy, exp(μ/ρ(E)·ρ·t), with the user's value as an override. | **built for Al** (2026-11-18): NIST table from the owner's saved page, `lss_core/absorbers.py`; "from E" box beside the field, on by default. Open: the Cu unit thickness at 30 keV; which foils at 10.05 and 10.52 keV (20260902) |
| F50 | **Fluorescence with absorbers.** The foils are before the sample, so fluorescence is attenuated like the reflected beam; spectra at different absorber settings need a^n to be compared. The XFNTR scans (`getandsave_mca`) record no absorber setting (no `#A` in the SPEC scan, none in the MCA header). | **built** (D24): the reader takes the last `#A` above the scan and says so |
| F51 | **Per-scan monitor scatter σ_scan** for the Student t model, estimated from each scan rather than typed in. The separate analysis used a robust standard deviation of the point-to-point changes, per scan (owner). | **declined** (owner, 2026-11-17): a fixed Student t (D26) |
| F52 | **Monitor gain in the normalisation.** SPEC records `#M Monc Gain <S> <unit>` (SR570 sensitivity, A/V); counts per photon ∝ 1/S, so normalise by M·S/S_ref (S_ref = 1 µA/V), not M. Measured: S changes within files by up to 50×; MCA scans record no `#M` (the last above is taken, as for `#A`). | **built as an option** (owner, 2026-11-17): MCA tab and SpecPlot (one setting, a "/ gain" box beside each monitor choice), `Experiment.fluorescence(monitor_gain=True)`. Off by default. **Pilatus paths too** (owner: extend it; mainly for comparing different SPEC files, since the gain changes only with a large energy change, > ~300 eV): cuts, background images and background-subtracted frames, GID data, frames at one Q_z (Ref analyse). Not Ref Patch or GID patching, which measure the scale. Uninterpretable gains: `reports/monitor_gains.md` |
| F53 | **Simultaneous Pilatus and fluorescence experiments** (owner, 2026-11-17). Select both data types of the same scans to plot and reduce; tabs "Vortex" and "Pilatus" in the window were suggested. Today (read): a scan has one `Detector` (whichever of `#V` / `#B0` comes later in its header wins), the window keeps one `self.det`, and Pilatus frames and MCA spectra share the one image list, so a scan with both shows only one. Needs: a scan holding both detectors in the Sources layer, per-detector selection, and the two tabs. A sample SPEC file with both would pin the format. | Stage 4 (sources, selection) and the R4 GUI work; needs a sample file |
| F54 | **Photons per second from the monitor** (owner, 2026-11-17: a scalar will be provided). photons/s = C · I, with the monitor current I = M·S/(G·t) (G the V2F scale, Hz/V). Then fluorescence and reflected counts can be given per incident photon. | waiting for the scalar; say whether it includes G and the monitor's efficiency, and for which energy |

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
| F55 | 'Point #' checkbox in the SPEC plot options, on by default; unticked, the plot is redrawn with no point labels. Labels a log axis cannot show (≤ 0, non-finite) are hidden either way. | `initSpecPointLabels`, `specPlot`, `specPlotSettings` | `tests/test_guards_remaining.py` |
| F24b | Qz² display option no longer changes the saved `_rrf.txt`. | `updateRefPlotData` | `tests/test_ref_export_golden.py` |
| F27 (part) | Non-SPEC files and repeated scan numbers handled quietly. | `openSpecFile`, `readSpecFile`, `spec_routines.is_spec_file` | `tests/test_known_defects.py`, `tests/test_parsers.py`, `tests/test_real_bu.py` |
| Defect 1 (start of F23) | GID patching runs on current SciPy with unchanged results. | `interp_compat.py` | `tests/test_interp_compat.py`, `tests/test_real_nx_school.py` |

## Order

F6–F9, F1–F5 and F13–F16 all need the readers and the reduction to be callable
without the window, with parameters held in one explicit state object
instead of widgets, so they come after the physics is extracted from
`mainwindow.py` (step 4 in `ASSESSMENT.md`). F10–F12 do not depend on that
and can come first: a central exception handler and a log are small,
self-contained, and make every later step easier to debug. Timing
measurements are in `timings.md`.
