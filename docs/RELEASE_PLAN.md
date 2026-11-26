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
| 4 | Fluorescence/MCA: sums, Fit lines, XFNTR merge | built | **the owner's decision (2026-11-26), overriding rule 1 for this default:** Fit lines reports XeRay (the value plotted, merged, exported) and the reader's Poisson fit with fixed width and escapes stripped beside it, both with errors (F110, built 2026-11-26) |
| 5 | Per-SPEC workbook with automatic saving, and the lock | built | — |
| 6 | Live updates while data come in | built | — |
| 7 | Never closes on an error (Stage 0 safety net) | built | ~~crash baseline shrinks to release level~~ **at zero** (2026-11-26): `known_crashes.json` holds no crash in its 14 states, `known_crash_sites.json` is empty; the sweep passes (194) |
| 8 | Windows build that runs on a clean PC | recipe exists | make one tagged build and try it on a clean machine |
| 9 | Quick-start guide (two pages: open, reduce, export) | not written | write it from `MANUAL_NOTES.md` |

## Release blockers (only these block 2.0)

1. Crashes in the main workflows (open, reflectivity, GID, MCA, export).
2. Wrong numbers in an export xmodfit reads. That means a real bug, not a
   better method we might choose later.
3. The 7 known Windows test failures on `main`. Each one gets fixed or is
   marked as not a release issue, with one line saying why.
4. The packaged build fails to start or to load the sample data.

Everything else is **not** a blocker.

### Blocker status (main man; updated 2026-11-26)

1. **Crashes:** none known.
   - The sweep's baselines are at zero.
   - `KeyError: 'monc'` is fixed (#116).
   - The burn dialog no longer refuses a burn without a beam height (#115), which had kept the slow suite red.
   - On `main`: the quick suite passes (1375), the slow suite passes (427), the sweep passes (194).
2. **Export numbers:** none known.
   - The legacy export fixtures stay byte-identical, and the golden `_ref.txt` files and the xmodfit
     covariance contract pass: `test_api`, `test_ref_export_golden`, `test_covariance_export`,
     `test_gui_export_name` (104 passed, 2026-11-26).
3. **The 7 Windows failures:**
   - **Fixed, 4 test bugs** (none was a program bug):
     - `test_paths` ×2: CRLF doubled to CR CR LF; the plot list keeps the path's own separator.
     - `test_gui_menus::test_documentation_opens_the_scripting_guide`: Qt's URL path uses '/'.
     - `test_test_infrastructure::test_auto_workers_fit_the_cpus_and_the_memory`: no `os.sched_getaffinity` on
       Windows.
     - The fixes are reasoned and, for the line ends, simulated here; they wait for a rerun on the Windows PC.
   - **Not a release issue:** `test_ngui::test_window_builds_with_every_placed_control`. ngui is the layout
     prototype, parked after 2.0, and its exact-size assertion meets Windows display scaling.
   - **Open:** `test_toolbox_gui` ×2. Their assertion lines from the Windows PC are needed (asked on #55).
     Pixel comparisons of figures, which Windows fonts change, would not be a release issue; anything else
     would be.
4. **The packaged build:** tools man's.

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
