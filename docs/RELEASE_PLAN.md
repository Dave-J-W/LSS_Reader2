# Release plan: Reader 2.0 (first release of this fork)

Draft by the project manager, 2026-11-25. **Status: approved by the owner, 2026-11-25. Released 2026-11-27:**
the owner published release "Reader 2" with the tag `v2.0.0` on main 01ae585 (the code of cc599e4, on which
the quick, slow and sweep suites passed: 1441, 427, 194). The tag's build, run 45919642733, passed: Windows and
macOS self-tests, 9 tabs, `_ref.txt` and `_rrf.txt` identical; downloads kept to 2027-02-25. This plan no longer
overrides `docs/TODO.md`; its "After 2.0" list is the backlog. Rules 12 and 13 stay paused after the release
(owner, 2026-11-27: "Let's pause those rules again").

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
| 8 | Windows build that runs on a clean PC | **the build for the tag passes** (main man, 2026-11-27, at the owner's request: run [45918527279](https://github.com/Dave-J-W/LSS_Reader2/actions/runs/45918527279) on main at cc599e4, with #132 and #135; Windows and macOS self-tests passed, 9 tabs, `_ref.txt` and `_rrf.txt` identical; downloads kept to 2027-02-25). The earlier run 45879045324 (ce38cf4) passed too | the owner tags `v2.0.0` on cc599e4 (owner, 2026-11-27: "When I get home I'll tag 2.0"); the clean-PC test and XModFit reading the export are the owner's |
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
   - **Windows quick suite on main f91029a** (project manager, the owner's PC, 2026-11-26, `-n 4`): 1419
     passed, 3 failed, 13 skipped, 2 xfailed (6.5 min). The 4 fixes above pass. `test_gui_reader_lock` ×2
     **pass** now.
   - **Fixed:** `test_toolbox_gui::test_the_open_spec_file_fills_the_spec_option`. This was a test bug: the
     free field quotes a path with a space (shlex), and the test compared the raw text. It failed on any
     checkout whose path has a space, not only on Windows.
   - **Not a release issue:** `test_toolbox_gui::test_a_figure_tool_reproduces_its_committed_figures
     [burn_figures]`. The pixel comparison fails (5–6 % of pixels), but it is platform rounding, not a bug.
     Measured: the per-frame values agree with the committed CSVs to 3 × 10⁻¹⁰. Every burn verdict and
     chosen model is the same. Only the last digits of the fitted times move (68.78 s vs 68.83 s), plus one
     AICc gap (206.7 vs 209.8), which is far above any threshold. After 2.0: compare the CSVs with a
     tolerance on Windows instead of pixels.
   - **Blocker 3 is closed:** of the 7, 5 are fixed and 2 (ngui, burn pixels) are explained.
4. **The packaged build:** the builds pass (tools man, #118): Windows and macOS built and passed their
   self-test on GitHub, Windows with `_ref.txt` and `_rrf.txt` identical to the reference. **Near-clean test passed**
   (project manager, the owner's PC, 2026-11-26). It ran run 45753156275's `LSS_Reader-Windows` with Python
   removed from PATH and every `PYTHON*`, `CONDA*` and `QT_*` variable unset:
   - The self-test passed in 9 s: window with 9 tabs, `_ref.txt` and `_rrf.txt` identical.
   - A plain start (as a double-click) showed the window in 4 s, closed cleanly with exit 0, and left empty
     fault logs.

   **Still open: a truly clean PC. Do not use Windows Sandbox on the owner's PC.** Sandbox was enabled
   there on 2026-11-26. It is an empty Windows with no Python and no Visual C++ runtime, which is what a
   clean test needs. But the PC shut down unexpectedly while the feature was installing (12:18). Then it
   froze hard during the third Sandbox run (after 12:33): no bugcheck, and the files being written were
   left as zeros. Afterwards it could not find its startup disk until the owner repaired it (19:17). No
   result came out of the Sandbox. Do the clean test on another Windows PC (a beamline PC or a laptop
   without Python), following `docs/PACKAGING.md` "Clean-PC test", with the `v2.0.0` build. The XModFit
   read of the export (step 5) is the owner's. Help → About shows 2.0 since 2026-11-26 (`lss_core.__version__`; it said 1.1).

**The tag (done, 2026-11-27):** `v2.0.0` on 01ae585, which has the same code as cc599e4 (all three suites passed on it: quick 1441, slow 427, sweep 194;
build run 45918527279 passed). The clean-PC test and XModFit reading the export were not reported; the owner
decided to tag (2026-11-26, "I think we can tag 2"). The tag's build passed (run 45919642733). The clean-PC test is now a check on the release, not a blocker. The Windows test run is done (blocker 3 closed, 2026-11-26).

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
  - **A pathology tool** (owner, 2026-11-26: "proper tool later"): figures of the bad fits, one
    spectrum each from the run's own seeds. They cover XeRay winning with error bars 20 % too small,
    XeRay failing at +529 % and +1032 %, and six other methods' failures. They also show whether a
    misfit test gives XeRay away. Measured on all 39 100 spectra (Poisson deviance in the line
    window): it catches all 23 scatter failures (misfit 4–55 per dof, every spectrum flagged at
    p < 0.01). It misses a neighbouring line under the target (Co beside Fe +148 %, As under Pb Lα
    +88 %, misfit 1.06–1.08) and 30 photons (+35 %). It flags 28 % of XeRay's right answers at
    10⁴ photons. The prototype scripts are on the owner's PC (`parked/xrf_pathologies/` beside the
    clone). To do: one script in `tests/tools/`, a catalogue item, a short page in
    `docs/studies/xrf_shootout/`.
  - **Larch: a bug in our setup, and what tuning does** (owner, 2026-11-26: "making larch work
    better, it seems promising"; measured on 15 synthetic conditions, 200 spectra each).
    - The bug: `xrf_shootout._larch_model` gives Larch the beam in eV (`1000 × energy`), but
      Larch's model takes keV, so it sees a 10 MeV beam. Every edge then counts as excited, and
      lines the beam cannot excite are modelled. This explains most of Lu L's +7900 % (Lu's L1/L2
      lines under a 10 keV beam) and As beside Pb's −680 %. The committed Larch scores of C65–C69
      are wrong wherever an edge sits above the beam.
    - The fix needs a second one: in keV, Larch's default starting amplitude (1e6) is ~10⁵ × too
      large, and the fits stop in bad minima. Starting from the counts under the line works.
    - With both fixes, Larch still cannot describe water's Compton scatter (misfit 30–50 per point).
      Its line amplitude trades against the Compton peak's tail, so scattered conditions read
      −10 to −75 %. None of these rescues it: the GUI's second Compton peak, Larch's background,
      Poisson weights, a pinned Compton centre.
    - A narrow fit (the line ± 1 keV, Larch's background, no scatter peaks) helps under mild
      scatter: the hard case at 14 keV goes from −42 % to −2 %, Fe far from the scatter from −13 %
      to −3 %. It fails under hard scatter, where the background takes the line (−100 %).
    - Script: `parked/xrf_pathologies/larch_tune.py` on the owner's PC.
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
