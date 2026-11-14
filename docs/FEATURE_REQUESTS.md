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

## Order

F6–F9 and F1–F5 both need the readers and the reduction to be callable
without the window, so they come after the physics is extracted from
`mainwindow.py` (step 4 in `ASSESSMENT.md`). Timing measurements on the
sample data should be taken first so that speed-ups can be shown.
