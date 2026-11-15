# Requirements and feature requests

As stated by the project owner. Status is updated as work lands.

## Standing requirements

| # | Requirement | Stated | Status |
|---|---|---|---|
| R1 | Verification tests preserve the physical and mathematical behaviour through debugging and refactoring. | 2026-11-14 | Scaffolding in place; see `TESTING.md`. |
| R2 | Finish the Python 2 → 3 migration, which is incomplete and has caused problems. | 2026-11-14 | Known leftovers listed in `ASSESSMENT.md` section 4; none fixed yet. |
| R3 | The interface never crashes, whichever files are selected and whichever controls are used afterwards. | 2026-11-14 | Measured by `pytest -m sweep`: 420 control/state combinations raise from a clean state, plus 11 further crash sites reached only by sequences (see `physics_notes.md`). |
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

## Order

F6–F9, F1–F5 and F13–F16 all need the readers and the reduction to be callable
without the window, with parameters held in one explicit state object
instead of widgets, so they come after the physics is extracted from
`mainwindow.py` (step 4 in `ASSESSMENT.md`). F10–F12 do not depend on that
and can come first: a central exception handler and a log are small,
self-contained, and make every later step easier to debug. Timing
measurements are in `timings.md`.
