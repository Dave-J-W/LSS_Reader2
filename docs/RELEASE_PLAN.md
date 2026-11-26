# Release plan: Reader 2.0 (first release of this fork)

Draft by the project manager, 2026-11-25. **Status: approved by the owner, 2026-11-25.**

## The goal

Get a working Reader 2.0 into users' hands at the beamline. Revise afterwards.
Until then we work on **shipping, not proving**.

Proposed target: **2026-12-09** (two weeks). The owner sets the date.

## Rule 1: the current defaults ship as they are

Every default in use on `main` today is the release default. That covers
patching, the error model, MCA fitting, export layout, the covariance box
(off), and the foil prior (off).

- The B2 decisions in `TODO.md` and every open "which default" question move
  to **After 2.0** below. Nobody works on them before release.
- No new studies (C-numbers), gauntlets or rule-12 demonstrations before
  release, unless a release item is broken without one.
- A number that changes is still recorded (rules 1 and 11), in one line. No
  essays.
- **Rules 12 and 13 of `AGENTS.md` are paused until release.** Rule 12 is
  "a study, tests and a demonstrator before any default changes". Rule 13 is
  "show the whole chain, ELI5, for every number". Those two rules produce
  most of the C-studies, walkthroughs and ELI5 documents. They come back
  after 2.0, when we revisit the defaults.

## What ships (must work)

All of these are already built. The work is finishing, fixing and checking them.

| # | Feature | State | Left to do |
|---|---|---|---|
| 1 | Open a SPEC file and load Pilatus and MCA data beside it | built | — |
| 2 | Reflectivity: reduce, patch (joint fit), export `_ref.txt` / `_rrf.txt` for xmodfit (legacy format, byte-stable) | built | — |
| 3 | GID: pinhole patch, maps, cuts, export | built | ~~fix `KeyError: 'monc'` on a one-point scan (crash)~~ **fixed 2026-11-26 (#116):** `Experiment.frames` names the missing column and why; the window only warns (probed) |
| 4 | Fluorescence/MCA: sums, Fit lines, XFNTR merge | built | **the owner's decision (2026-11-26), overriding rule 1 for this default, revised the same day:** Fit lines reports the reader's Poisson fit (escapes stripped, the width from the sum) as the value plotted, merged and exported, and XeRay beside it, both with errors (F110, built 2026-11-26) |
| 5 | Per-SPEC workbook with automatic saving, and the lock | built | — |
| 6 | Live updates while data come in | built | — |
| 7 | Never closes on an error (Stage 0 safety net) | built | ~~crash baseline shrinks to release level~~ **at zero** (2026-11-26): `known_crashes.json` holds no crash in its 14 states, `known_crash_sites.json` is empty; the sweep passes (194) |
| 8 | Windows build that runs on a clean PC | **builds pass** (tools man, #118, 2026-11-26: Windows and macOS self-tests on GitHub, run 45753156275 on main at 5f00a1c; downloads kept to 2027-02-24, the sample data with them) | the clean-PC test by a person (`docs/PACKAGING.md`, "Clean-PC test", about 10 min); the tag `v2.0.0` is the owner's |
| 9 | Quick-start guide (two pages: open, reduce, export) | **written** (tools man, #118: `docs/manual/quick_start.md`; Help → Documentation opens it) | — |

## Release blockers (only these block 2.0)

1. Crashes in the main workflows (open, reflectivity, GID, MCA, export).
2. Wrong numbers in an export xmodfit reads. That means a real bug, not a
   better method we might choose later.
3. The known Windows test failures on `main` (7 at first; 5 on 2026-11-26: `test_gui_reader_lock` ×2,
   `test_toolbox_gui` ×2, `test_ngui` ×1). Each one gets fixed or is
   marked as not a release issue, with one line saying why.
4. The packaged build fails to start or to load the sample data.

Everything else is **not** a blocker.

### Blocker status (main man; updated 2026-11-26)

1. **Crashes:** none known.
   - The sweep's baselines are at zero.
   - `KeyError: 'monc'` is fixed (#116).
   - The burn dialog no longer refuses a burn without a beam height (#115), which had kept the slow suite red.
   - MCA: the Fit Peak dialog's Accept after Fit lines (7-column rows, F110) or after a Merge crashed or left
     ragged rows; fixed by GUI manager (#122, 2026-11-26).
   - The Plot tab's Fit Peak parameter export raised a TypeError half-way through `_par.txt` when lmfit had
     no error estimate; fixed by GUI manager (#124).
   - On `main` with #118, #119 and the About fix: the quick suite passes (1396), the slow suite passes (427),
     the sweep passes (194, on #119).
2. **Export numbers:** none known now.
   - **Found and fixed (GUI manager, #125):** a stale `_rrf.txt`. R/R_F was kept after R/RF was unticked,
     so Export could write the old curve's R/R_F beside a new `_ref.txt` (and Save stored it). Every main
     export now says what it wrote and what it replaced.
   - **The owner's rule (2026-11-26), GUI manager #128:** Export always writes both `_ref.txt` and `_rrf.txt`
     (R/R_F at the fields' Qc and Qoff, ticked or not); no legacy fixture changed.
   - The legacy export fixtures stay byte-identical, and the golden `_ref.txt` files and the xmodfit
     covariance contract pass: `test_api`, `test_ref_export_golden`, `test_covariance_export`,
     `test_gui_export_name` (104 passed, 2026-11-26).
3. **The 7 Windows failures:**
   - **Fixed, 4 test bugs** (none was a program bug):
     - `test_paths` ×2: CRLF doubled to CR CR LF; the plot list keeps the path's own separator.
     - `test_gui_menus::test_documentation_opens_the_scripting_guide`: Qt's URL path uses '/'.
     - `test_test_infrastructure::test_auto_workers_fit_the_cpus_and_the_memory`: no `os.sched_getaffinity` on
       Windows.
     - **Confirmed on the Windows PC** (xr-data-needs, #55, 2026-11-26: they pass on a clean checkout of main
       860abd5).
   - **Not a release issue:** `test_ngui::test_window_builds_with_every_placed_control`. ngui is the layout
     prototype, parked after 2.0, and its exact-size assertion meets Windows display scaling.
   - **Open:** `test_toolbox_gui` ×2. Their assertion lines from the Windows PC are needed (asked on #55).
   - **New on Windows, open:** `test_gui_reader_lock` ×2 (`test_keep_declines_the_request`,
     `test_a_request_for_the_write_access_offers_release`), from #120, on clean main 860abd5. Their `E` lines
     are asked for on #55, for GUI manager.
     Pixel comparisons of figures, which Windows fonts change, would not be a release issue; anything else
     would be.
4. **The packaged build:** the builds pass (tools man, #118): Windows and macOS built and passed their
   self-test on GitHub, Windows with `_ref.txt` and `_rrf.txt` identical to the reference. **Open:** the
   clean-PC test, by the owner or Local yokel on a Windows PC that has never had Python (a Windows Sandbox
   will do). Help → About shows 2.0 since 2026-11-26 (`lss_core.__version__`; it said 1.1).

**Before the tag** (owner): the clean-PC test passed; the Windows rerun of the 4 fixed tests and the 2
`test_toolbox_gui` lines; then `v2.0.0`, which runs the same build workflow.

## After 2.0 (parked, in rough order)

- **Default-method decisions**: all of B2 (covariance export and layout, the
  legacy patch's Σ, stitched points, the joint sidecar's 10 %, the foil
  prior, the error model), the C45 rung-choice error, C64 clipping, and B3's
  factor 10.
- Rule-12 studies: P44 burn estimator, σ × 1.12 joint fit, robust likelihood,
  GID defaults switch (`beam` response).
- **Refine the XRF shootout (C65–C69)** (owner, 2026-11-26: "Put a to-do to continue refining that shootout of methods for a later time, since I don't believe each library/method was optimized enough."):
  tune each library and method (PyMca's configuration and background,
  PyXRF's model, Larch's series and each, XeRay's window and error, the
  reader's fits) before the comparison is used again; then revisit which
  MCA fit is the default and which is reported beside it (F110).
- Reopening a file with its workbook's settings; recipes for cuts, MCA lines
  and SpecPlot curves.
- F80/F105 comparison tab; Export naming handed over to xmodfit.
- Stage 4 (200K, 1M, 7-element detector, HDF5/bluesky input, Pilatus and
  Vortex in one scan).
- Stage 5 remainder: ORSO/HDF5 export, per-second option, Qz offset from sh
  images.
- `ngui/` layout prototype, F60 contextual reduction, timeline phases after 1c.
- EXAFS output, edge estimator, line markers and escape peaks, GID scan
  designer, multiple exposures.
- MCA Merge: a missing fit (NaN, e.g. an accepted single fit beside Fit lines'
  rows) makes its whole group NaN for that fit; skip it instead and merge the
  fits that exist (`fluorescence.merge_rows`; found reviewing #122).

## Who does what until release

| Session | Release job |
|---|---|
| main man | blockers 1–3; reviews and merges; keeps this file current |
| GUI manager | crash and usability fixes in the main window's workflows only; no new panels |
| tools man | blocker 4 (the tagged Windows build, clean-PC test); the quick-start guide |
| questor | asks the owner only questions that block a release item |
| Local yokel | paused unless a blocker needs private data |
| Reflection guy | public-data rulings for the release note and the quick-start guide only |

## Done means

- The quick, slow and sweep suites pass on `main`. Windows failures are fixed
  or explained.
- A tagged build (`v2.0.0`) is on GitHub and was started on a clean PC.
- Its sample data loaded, a reflectivity was exported, and xmodfit read it.
- The quick-start guide is in `docs/manual/`.
- The release note lists which old reductions to redo (non-zero absorbers
  before P24, `bu` files before F49).
