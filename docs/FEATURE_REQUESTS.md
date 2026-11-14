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

Design points to settle: the SPEC folder may be read-only or on a slow
network drive, so there must be a fallback location and writes must be
atomic (write a temporary file, then rename) and infrequent; two people may
open the same SPEC file at once; the config needs a version number and must
survive a SPEC file that has grown since it was written (F1–F5); dropped
points should be stored as a mask over raw frames (scan and frame number),
not as edited arrays, so that reduction can be repeated from raw data and
undo/redo is a change to the mask; how this file relates to the caches of
F8–F9.

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

## Order

F6–F9, F1–F5 and F13–F16 all need the readers and the reduction to be callable
without the window, with parameters held in one explicit state object
instead of widgets, so they come after the physics is extracted from
`mainwindow.py` (step 4 in `ASSESSMENT.md`). F10–F12 do not depend on that
and can come first: a central exception handler and a log are small,
self-contained, and make every later step easier to debug. Timing
measurements are in `timings.md`.
