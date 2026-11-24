# To do

Current phase: **implementation**, following `SCOPE.md`. The owner gave the
go-ahead on 2026-11-17 ("begin the implementation plan").

| Stage | Status |
|---|---|
| 0 Safety net (error handler, durable log, messages pane) | **done** 2026-11-17 |
| 1 Repair what is plainly broken | **done** 2026-11-17 |
| 2 Readers and reduction out of the window; caching; scripting | **done** 2026-11-18 (quick 337, slow 542, sweep 67 passed) |
| 3 Saved state per SPEC file; live refresh | **largely built** 2026-11-19 to 22: series read and guessed, Series list and whole-series selection; per-SPEC workbook (F66) with automatic saving (D56), series ties and stale flags; live updates (D57: file and data folders watched, remakes in a worker thread, open plots redrawn, no reset). Open: reopening a file with its workbook's settings, D1–D3, dropped points as masks, the owner's answers on the series format |
| 4 Detectors and inputs | not started |
| 5 Reflectivity export, uncertainty, ORSO/HDF5 | not started |
| 6 Sub-projects (GID patching, fitting, beam size, GUI) | **GID started** 2026-11-18 at the owner's request (D36: pinhole patch, worksheet, joins, beam response); **fitting done** 2026-11-21 (peak module D52, MCA lines, scan shapes, burn trends D54); beam size (half-cut fit built, no data); **GUI planning started** 2026-11-22 (D58: assessment, workflow map, screenshots in `docs/gui/`; no code yet); **Tools menu built** 2026-11-23 (F84: every demonstration and figure generator, `docs/TOOLS.md`) |

## Who is on what (kept by Main, D62; 2026-11-23)

| Session | Now | Next |
|---|---|---|
| Main (orchestrator) | ~~F81, F91, F87, P47, half-written SPEC lines~~ (2026-11-23); ~~the two decision studies and the ELI5 rationale~~, ~~the join guard at p 0.7~~ (#47), ~~area L, the fragile assumptions~~ (#50), ~~F98's core: the dose of each point, burns against dose~~ (#52), ~~F92's core: dropped points as a mask~~ (2026-11-24) | F97 diffuse cut axes (the core), then what Main assigns next |
| GUI manager | ~~F88 sticky display, F69 movie~~ (merged #34, 2026-11-24: the image display functions are free); ~~F86 Reduction options~~, ~~Q-GID-5~~, ~~Q-UI-A10~~ (#32); **F96** Ref Patch window: Back, Cancel, join table, the line under the Reflectivity plot (built 2026-11-24; the live replay of accepted joins later); **F95** B6 and the B3 list, **F74** residual panels on scan, cut and burn fits, **F97** saturation cue, **F78** super-Gaussian height-scan fit (timeline 1a) (built 2026-11-24) | F105's Export name and xmodfit hand-over (the Compare tab, F80 + F105, is built); timeline's reduced-data and environment lanes (the tab, sh thumbnails, notes and 'new sample?' answers are built); F95's ROI threshold, B9, B10; F97's diffuse axes (the ROI close-up built 2026-11-24); then ngui |
| tools man | ~~the Pilatus 100K sizes~~, ~~the F90 demo wrap-up and P1 the default of Fit lines~~, ~~Q-BURN-6~~ (#46, 2026-11-24); **F79**: Qoff proposed from the continuity of R/R_F and Qc from the subphase (core and a rule-12 study; no default change) | its API to the GUI manager for the Ref tab's "Propose" buttons |
| questor | the owner's questions and their answers in `docs/`; the data needs (`docs/DATA_NEEDS.md`, with tools man's blank-spectrum request) | (its own order) |

## Remaining work by area (regrouped 2026-11-21, review `docs/reviews/2026-11-21-todo-review.md`)

The stage lists further down keep the history and the detail; this is the
working list, one table per area, each row with its source. Rows marked
**new** were found forgotten by the review (its section 3).

**A. GID (pinhole patching)**

| Item | Source |
|---|---|
| Final defaults from many data sets (distance, response, joins) | hand-off 06; input 19 |
| ~~Scan join against everything joined so far~~ **done 2026-11-22** (P41) | P41 |
| Stray light, streak mask, background frames | P40; input 17 |
| Exact angles for cut axes, display, distance fit | P38 remainder |
| ~~Legacy three-level map (synthetic three-level set)~~ **fixed 2026-11-23** | P36, P37 (= P14, P15, P31) |
| Second 200K module | F63, D43; input 3 |
| ΣN/ΣW vs IDL error weights | input 18 |
| Multiple exposures, cosmic rays | F40 |
| GID scan designer — **new** (only in SCOPE's text) | F32 |
| GISAXS one column off; GISAXS and background-subtracted GID scriptable | P35 |
| sh scans paired with GID levels (sample height drifts by µm in 30–60 min): read a nearby sh scan per level and report the height change — **new** | physics_notes 2026-11-19 |

**B. Reflectivity and export (Stage 5)**

| Item | Source |
|---|---|
| Two-file export, covariance sidecar; Budget then the default (the covariance itself is computed since 2026-11-22: `lss_core.uncertainty`; what to export: area B2). **Built 2026-11-22 as options** (`lss_core.covariance_export`, `lss_core.gls`, `reports/downstream_covariance.md`): sidecars beside the legacy files (window "+ covariance", off; scripts `save(covariance='sidecar')`), the contract's two outputs and the combined file (scripts `covariance='contract'`, `combined=True`). Open: the defaults (B2); hand-off tests 5–6 with XModJointFit's own `lss_reference.py` / `covariance_core.py` when supplied; the GUI path for a joint-fit patch, if the window gets one | F24, F24a, F24c; P4; input 5 |
| Stitch-factor bias, measured on real overlaps, then remedied: remedy built 2026-11-22 (`lss_core.patching`, joint fit), **the default since 2026-11-22** after the synthetic gauntlet (C36); confirming on the larger data set: hand-off 08 (the private `bu` set holds no reflectivity) | P1, D13 |
| ~~The joint fit's error at the first join of NX-like scans of a 25 Å film: pull SD 1.13~~ **explained 2026-11-24** (C45): the guard ladder's post-selection (the 25 % of seeds that fail p ≥ 0.3 at order 4 are accepted at a rung chosen for its χ²; without the guard, 1.05); the default's five biased designed joins are model bias near fringes (noise-free up to −1.03 errors), mixed by the ladder. A remedy (an error that accounts for the choice, or p) is the owner's decision, sent through questor | C35, C36, C45 |
| ~~Undersampled fringes at a join (fewer than 3 points per Kiessig period of the coarser scan)~~ **not to be done** (owner, 2026-11-23: "fringes will rarely be undersampled, or even be sampled close to nyquist, that is not an important case to consider"); the gauntlet's finding stays in C36 | C36; physics_notes 2026-11-22, 2026-11-23 |
| Same-absorber scans share a factor: send the question to the hand-off author — **new** | F41 |
| Qz offset from sh-scan images — **new** | F42 |
| Per-second option — **new** | F20 |
| Qoff proposed from the continuity of R/R_F across the joins (robust to one or two outliers); Qc from a subphase list or typed electron density — **new** 2026-11-23 | F79; F42 |
| **The owner's rule (2026-11-24): the best method, demonstrated, tested and presented, becomes the default.** ~~The join guard p 0.7~~ **done 2026-11-24** (C48). ~~MCA Fit lines with P1 as the default~~ **done 2026-11-24** after the demo wrap-up (`docs/reports/mca_fit_demo.md`; tools man, OUTPUT_DECISIONS); the window sum left as it is: which spectra have scatter under the box needs a blank (DATA_NEEDS row 3) | AGENTS.md rule 12 |
| Saved reflectivities of the workbook overlaid by series, time or sx, with ratios, to check stability — **new** 2026-11-23 | F80 |
| **Comparison of reduced curves in a tab fed by the workbook, updating itself; Export proposes a file name from the sample and series and hands over to xmodfit** (owner, 2026-11-23, Q-REF-5, Q-REF-6; recorded by questor in batch 14 but not put on this list until 2026-11-24) — GUI manager, after timeline 1c, with F80 | F105; physics_notes 2026-11-23 batch 14 |
| ~~Repeated macros summed by counts and monitors (the identical-scans merge averages with equal weights today)~~ **done 2026-11-23** (F81, `test_repeats_merge.py`) | F81; physics_notes 2026-11-23 |
| ORSO, HDF5 export; steps and parameters recorded — **new** (F30) | F25, F30, R7 |
| Synthetic K = 3–5 generator; hand-off tests 2–6 | hand-off §5; input 4 |
| Tell users which old reductions to redo (non-zero absorbers before P24; bu files at 6.21/7.51/9.9 keV before F49): a release note and a manual line — **new** | TODO Stage 2 list; P24, F49 |

**B2. Decisions on export and saving left to the owner (2026-11-22: "Leave decisions about export and saving in the to-dos")**

| Decision | Options | Source |
|---|---|---|
| ~~Which reflectivity patching method is the default~~ **decided 2026-11-22**: the joint fit, because it passed the gauntlet (owner: "make new method the default if it passes the gauntlet"; C36, OUTPUT_DECISIONS); still open: whether the foil prior is used by default (the gauntlet's prior variant is conservative on synthetic foils, pull SD 0.25–0.9) | hand-off 08; C36 |
| How the stitch factors' correlated uncertainty is exported: folded into each point's error (legacy), a covariance sidecar beside `_ref.txt` (F24), or a combined JSON (F24c). All three are built (2026-11-22). Open: is the window's "+ covariance" box on by default; which layout it writes (sidecars beside the unchanged legacy files, built; or the contract's corrected `_ref.txt` with √diag C plus `_ref_legacy.txt`, built for scripts) | xmodfit hand-off contract; `reports/downstream_covariance.md` §8 (measured: pull SD ≈ 1 only with the covariance) | F24, F24a, F24c; P4 |
| Σ of the legacy patch: the legacy factors with errors recomputed from counting errors, inflate-only (built), or the legacy `absolute_sigma=False` error | `OUTPUT_DECISIONS.md` | downstream_covariance §8 |
| Joint-fit export points: averaged where Q_z coincide (built), or every point as measured | | joint-fit report §4.4 |
| Known-ratio joins in the legacy covariance: foil correlations between them are not included (assumption) | | downstream_covariance §4 |
| Whether the legacy export stays the default once corrected outputs exist, and the file names of the corrected ones | | F24a |
| Which error model the export uses by default (legacy, budget) | | P2, input 5 |
| What the workbook stores for a reflectivity: factors and their covariance, the joint-fit model per join, both methods side by side | | F66 |

**C. Fluorescence, MCA, EXAFS**

| Item | Source |
|---|---|
| Per-point MCA files of scans without `#V` (October `ascan`): the owner said yes — **new** as a work item | input 14; physics_notes 2026-11-19 |
| EXAFS output (energy axis, line fit per point, `fit_series`) — **new** as a work item | F36 |
| Edge estimator (backlog) | F65 steps 3, 4, 6 |
| Pilatus and Vortex in one scan | F53 |
| Line markers, escape peaks — **new** (only in SCOPE's text) | F47, I14 |
| Fluorescence burns (XFNTR 19, 20) | hand-off 07 |
| **F90 synthetic project paused (owner, 2026-11-24): wait for real data; Zn at 10 keV no longer required.** ~~Wrap-up: a full demonstration of the synthetic MCA work (figures, a clear document, Tools menu items with variations) — tools man, after the Pilatus sizes; no new studies or estimators~~ **done 2026-11-24**: `docs/reports/mca_fit_demo.md` (the reader's guide, figures 1–8), the beam-energy figure (`tests/tools/mca_fit_demo.py`, `docs/figures/mca_fit_demo/`), Tools items under Fluorescence (MCA) with nine variations, `synthetic_dataset.py --kind mca` (two variations), SYNTHETIC_DATA marks the generator paused; no default changed | physics_notes 2026-11-24 |
| F90, real-data half (study B, 2026-11-24, C47, `docs/studies/mca_fit/summary.md`: the blank decides the 10 keV Zn case; P1 and the window verdict need no real data): the gauntlet's estimators on the owner's spectra (a strong elastic and Compton beside a weak line, plus a blank, pure water or subphase, at the same Qz and time); the synthetic half's verdict (C42) rests on the modelled O 1s Compton wing and Si escape — **new** | F90; C42 |
| F90 candidates found by the synthetic half (the owner's study first, `docs/studies/2026-11-24_two_decisions_plan.md`; built as options 2026-11-24; **the Poisson step is the default since 2026-11-24**, rule 12, the old weighting the legacy switch `mca_fit_data_weights`): line width fixed from the detector's resolution (calibrated on the elastic peak), Si escape stripping, a Poisson (model-weighted) per-spectrum step, a box short on the Compton side, a Compton-tail background term or a measured blank as a template — **new** | C42 |
| ~~"Fit lines" reports the tallest fitted peak~~ **fixed 2026-11-24**: the first line given (`peaks.line_index`; OUTPUT_DECISIONS) | C42 |
| A synthetic MCA series the reader opens (`synthetic_dataset.py --kind mca`, from `synthetic.mca`) — **new** | SYNTHETIC_DATA §5 |

**D. Monitor, absorbers, normalisation**

| Item | Source |
|---|---|
| Monc high at narrow S1 | P29; input 9 |
| Foil composition (6–7 keV overlaps); Cu at 30 keV | P28, F49; input 8 |
| Dark offset in ordinary normalisation (D41 covers per photon only) — **new** | P21 |
| Frame object: normalise once at load | owner 2026-11-17 |
| End-to-end photons-in/photons-out for GID, GISAXS, cuts, MCA | Stage 2 list |

**E. Scan series, live refresh, time**

| Item | Source |
|---|---|
| ~~Fix `series.infer`: `#V` hklscans as xfntr, `escan` as energy; series lines and inference together; `SeriesMacro` attached~~ **done 2026-11-21** (`series.all_series`) | review §3, §4 R1 |
| ~~Series in the scan list; select a series as one action~~ **done 2026-11-21** (Series list; whole series selected on a click by default, D55) | F39; Stage 3; review R2 |
| The Series list has not yet been tried by people (owner, 2026-11-23: reflectivity scans are selected one by one because it "is a new feature and hasn't been known or tested by humans yet"): a first trial at the beamline, then its questions — **new** | D55; owner 2026-11-23 |
| Contextual reduction from `kind` (offer, not run); the burn test for burn scans | F60; review R4 |
| ~~Automatic saving of every finished reduction~~ **done 2026-11-22** (D56), the prerequisite the owner set before L1–L4 | owner |
| ~~Live refresh L1–L4~~ **built 2026-11-22** (D57): Live box (L1), remake from recipes (L2: reflectivity, fluorescence, GID map, burn), selection follows a whole series (L3), stop at a lined series' end (L4). Done since: remakes in a worker thread, point selections carried over, updates without a reset (2026-11-22). Done since: the open display redrawn from a remade result (Reflectivity, MCA integrals, burn dialog, GID map; 2026-11-22). Remaining: recipes for cuts, fitted MCA lines and SpecPlot curves; stop after a quiet spell for guessed series; a test of the MCA redraw on a fluorescence series | F1–F5 |
| Time axis in MCA, Ref/GID lists | D46, D50, F37 |
| Owner: hand-off 05's four questions with the review's minimum metadata | input 1; review §4 M1 |

**F. Per-SPEC state and saving**

| Item | Source |
|---|---|
| ~~Workbook results tied to series id and scans used; stale flag when a series gains scans~~ **done 2026-11-22**: Saved gains series, series_kind, series_scans, series_status, recipe, stale; "Update Specfile" marks changed results | F66; review R3 |
| Reopen a SPEC file with its workbook's settings | F66 |
| The workbook and D1–D3 (config beside the SPEC file, read-only second instance, yellow light): record how they relate — **new** | D1–D3, D53 |
| Dropped points as masks in the config file, "Restore all" in the patch dialog (owner, 2026-11-23: F92) | F16, D2, F92 |
| Disk-cache settings dialog with the per-SPEC state — **new** in the Stage 3 list | Stage 2 list |

**G. Fitting, burn tests, beam**

| Item | Source |
|---|---|
| Burn trends: tests and extensions (ten items) | hand-off 07, Stage 2 list |
| Half-cut fit for the beam profile on real data | F43; input 16 |
| Remaining characterisation tests: GISAXS, g_l2/g_l3, absorber-ratio fits, legacy peak-fit dialog, 2D plot tab | Carried-over list |
| Sample-environment readings (barrier, tensiometer, oxygen) as extra panels beside burn trends; synthetic columns until the macros write them — **new** 2026-11-23 | F75 |
| Burns at several absorbers on dose and time axes: beam damage or a changing sample — **new** 2026-11-23 | F76; physics_notes 2026-11-23 |
| Predicting a safe absorber from a short high-flux burn (research; needs burn pairs at two fluxes) — **new** 2026-11-23 | F77 |
| Sample height scan: super-Gaussian fit (width, exponent) beside the sample's earlier sh scans; verdict thresholds from the owner. The test-speed session's commit 35f41c3 (on main) skips flat and weak sh scans and fits a sample height scan only when its FWHM is above 20 µm, the owner's plausibility floor; the 65 µm here is the quality verdict, so they do not conflict — **new** 2026-11-23 | F78; F43 |
| ~~**GID-burn detector rows default from the mean frame** (owner, 2026-11-23, Q-BURN-6; recorded by questor in batch 14, not listed until 2026-11-24) — tools man, after the Pilatus sizes~~ **done 2026-11-24**: `burn.signal_rows`, `exp.burn(rows='mean')` by default, "Rows from frame" and a rows field in the dialog; NX 14, 15 rows 46–486 (C49, OUTPUT_DECISIONS) | physics_notes 2026-11-23 batch 14 |

**H. Detectors and inputs (Stage 4)**: 1M (F17–F19, F38, D11), 100K/200K
models (F33), ME7 tab (F34, F35), new-format SPEC (F28), HDF5 (F29). All
wait on input 3.

**I. GUI, speed, packaging**

GUI overhaul (R4, D58; plan `docs/gui/README.md`), planning only until the owner says otherwise:

| Item | Source |
|---|---|
| **Unblocked 2026-11-23** by the owner's answers (`docs/gui/questions.md`, Answers): 1–15 of the priority list are answered or part-answered. Ready to build: F74 residuals (weighted); removal of the Apex tab (move its colour map first), Beamlines menu, `peakfit2`/`peakfitpara`, Command line row; Quit and Help > Documentation; D59 for all panes; F85 status badges; F86 Reduction options page with Ctrl+click; F87 burn kind (Det_Th > 2°); movie at ≥ 3 frames with space/arrow keys, shared absorber-corrected scale, log/linear defaults (F69, Q8); F88 sticky display with Home/Fit all; greyed-out tool groups. Needs a decision first: F91 "Sum All" (an output change, row in OUTPUT_DECISIONS). Still blocked on data: per-point MCA / EXAFS (data request below), F90 gauntlet real spectra. Still open: Q-GEN, Q-GID, Q-CUTS, Q-IMG-7…16 and the rest of inventory B | owner 2026-11-23 |
| Find what "GID Patch Relax" does that "GID Patch" does not (the question says: a larger Q grid) and write it as an option of the worksheet; then one "GID patch" with a worksheet/options button beside it and on the resulting patch tab (owner, 2026-11-23, Q-GID-5) | `docs/gui/questions.md` |
| Phase 1a: inventory of every control and the workflow it serves; findings per tab (grouping, consistency, visual cues, missing functions); screenshots of every area; questions for the owner: **delivered 2026-11-22** (`docs/gui/assessment.md`, `questions.md`); waiting on the owner's answers (15 first) | D58 |
| The workflow map, checked and rendered by a tool (burn tests, reflectivity, GID, XFNTR first, then EXAFS) | F67 |
| ~~A test that runs the map's check, so the map cannot drift from the window~~ **done 2026-11-23**: `tests/test_gui_map.py` (quick suite, about 5 s) runs `gui_map.py --check --window`, which now also checks the other direction (every named control of the window is inventoried); AGENTS.md rule 11 asks for the entry | F67 |
| Phase 1b: regrouping, one visual language, state cues; one line-cut interface on every image plot with defaults by scan kind | D58, F68, F59 |
| Phase 2: frames as a movie with sticky zoom (≤ 6 tiles; sampling first/middles/last, default 4; first n), sticky plot preferences, intelligent colour scales, ROI close-up for reflectivity | F69–F71 |
| Faster log-scale plotting (outside the first deliverables) | F72 |
| Residuals panel above every fit plot (about 15 % of the height, own scale, χ²/dof in the legend; can be hidden, hidden by default for now); for later | F74 |
| Sample timeline tab (sh-scan thumbnails, sx moves, new samples from 'set sh 0', tensiometer, barrier, reduction thumbnails, note boxes): **researched** 2026-11-23 (`docs/gui/timeline/research.md`: `set sh 0` found as a dated `#C` 'Sample_H reset' comment, a new sample only to be confirmed; QGraphicsScene, no new dependency; phases 1a super-Gaussian fit, 1b `lss_core/timeline.py`, 1c the tab, 1d workbook thumbnails and notes: about 6–8 sessions; Q-TL-1–8 for the owner) | F83 |
| Prototype of the new layout, **ngui** (a sketch, off by default; Preferences > Layout): design `docs/gui/prototype.md`; **built** 2026-11-23: `ngui/` (layout table placing all 404 inventoried controls or retiring 40 with reasons, theme, window), `tests/test_ngui.py`, screenshots `docs/gui/prototype/screens/` (`tests/tools/ngui_screens.py`); next: the owner's reactions | F82 |
| Phase 3: contextual GUIs by data type | F73, F60 |

**Defects found by the GUI assessment (2026-11-22)**, to fix one per commit with its test when coding resumes (details in `docs/gui/assessment_a.md`, `assessment_b.md`, `image_display.md`; "seen" = in an offscreen window, "measured" = a number taken, "read" = code only):

| Defect | How known |
|---|---|
| **The ngui prototype widens to 1476 px** (its default is 1440 × 900) when Split is on (Frames), when the panes are shown, or with the residuals panel (Reflectivity): screenshots `docs/gui/prototype/screens/02c_frames_split.png`, `02d_frames_with_panes.png`, `04b_reflectivity_residuals.png`. Present on main 7b9a22b before F96; `test_ngui` checks only the default size. GUI manager, low priority (ngui is third, Main 2026-11-24) | measured 2026-11-24 (screenshot sizes) |
| ~~**A drop of the new scan's first point (Drop "0") leaves dR NaN/inf from there to the end of the curve**~~ **fixed 2026-11-24** by Main (a one-point overlap: `stitching._fit_factor` gives the ratio and its counting error; xfails removed), window and `Experiment.reflectivity`, joint and legacy fits (synthetic: 6 of 14 points from Qz 0.05). For Main (reduction) | measured 2026-11-24, on main 7b9a22b and the GUI manager's branch; pinned by the strict xfail `tests/test_drop_first_point_errors.py` |
| **Workbook Save records the scans selected at the time of saving, not the scans behind the result** (a scan-6 curve saved after selecting scan 11 is stored as scan 11; the plot title too). Cause read: `saveRefToWorkbook` and `saveMcaToWorkbook` take `selectedScanNums` when Save is clicked; the recipe is right, so the scans column, series tie, stale flag and live remake disagree with it. For whoever owns Stage 3 | seen; **reproduced 2026-11-23** on synthetic data (curve of scans 1, 2 saved after selecting scan 1: stored as '1'), pinned by the strict xfail `test_gui_workbook.py::test_a_reflectivity_is_saved_tied_to_the_scans_it_was_made_from`. **Reflectivity fixed 2026-11-24** (GUI manager): Save and the plot title take the scans of the Ref Patch (`refResultScans`); the test passes. **Still open:** `saveMcaToWorkbook` |
| **MCA Save still records the scans selected at the time of saving** (`saveMcaToWorkbook`), the MCA half of the defect above; the reflectivity half was fixed by the GUI manager (5e60623, 2026-11-24) — open, Main assigns after the 2026-11-24 studies | GUI manager's report 2026-11-24 |
| **The point-by-point path (Analyze/Accept) saves one workbook version per Accept** (each Accept calls `updateRefPlotData`, one of the automatic-save points). Not pinned by a test: what counts as finished in this path depends on the owner's answer to question 13 (is Analyze/Accept kept?) | seen; **measured 2026-11-23**: synthetic scan 1, three Accepts → R0001, R0002, R0003 (versions 1–3, automatic) |
| ~~2D_Plot: adding a file raises AttributeError (`matplotlib.cm.get_cmap`, removed in matplotlib 3.9), `update2dPlotPlot`; its colour-map list offers `spectral`, not valid now. The crash sweep misses it because its file chooser returns no file~~ **fixed 2026-11-23**: a colour-map name is passed instead (works on every matplotlib); `spectral` offered as `nipy_spectral` in both lists; `tests/test_gui_2dplot.py` adds a file through the real button | seen |
| Log Int on frames with a negative bad pixel: typed Min −2, log10 gives NaN, the colour range collapses to ±0.1 decades | measured |
| Cursor readout over tiled frames shows the last frame's value; the ROI close-up's readout swaps rows and columns | measured |
| The drawn right background box of the reflectivity ROI is 2 px from the one summed | measured |
| Movie: blocking loop (0.5 s per frame, no stop); switches the Axes box to Q and leaves it there | measured |
| File > Quit and Help > Documentation are not connected | seen |
| Legend-position lists (Reflectivity, MCA): "lower right" twice, no "lower left" | seen |
| MCA default Range 1:1000 is in channels on a keV axis; Sum All clips it silently | seen |
| A new message shows the Messages pane but does not raise it above Script/Errors | seen |
| GIOXS uses a variable before assignment when the frame count is not a multiple of "ave frames" | read |
| The Plot tab still opens a blocking QMessageBox (rule: `notify`) | read |
| The crash sweep never exercises actions behind a file chooser that returns a file (e.g. 2D_Plot add file): extend it | read |
| Each Qc or Qoff Enter and each R/R_F toggle saves a new automatic workbook version (they call `updateRefPlotData`, one of the automatic-save points), so tweaking Qoff by trial stores a version per try; the same class as the per-Accept saves | read 2026-11-23 (owner's Save… question) |
| A finished "Reading Scan #1, 100 %" progress window sometimes appears late, after the reading it belongs to; the SPEC reader keeps it referenced (`spec_routines.py:236`), so Qt's show-if-slow timer may show it (cause guessed). Seen twice in four screenshot runs; not reproduced by opening the NX file and waiting 6 s | seen (intermittent) |

Other items: ~~make `test_rapid_clicks_in_the_image_list_are_drawn_once` independent of machine load~~ done 2026-11-22 (waits up to 3 s for the one draw); GUI reorganisation (R4) with redraw in place
and diffuse cuts (F59); slow-file-system timing; `timings.md` regenerated;
build workflow and macOS signing (input 12); sample-data hosting.
- [x] **Make the crash sweep fast enough to run after every GUI change —
      done 2026-11-23**: ~3 h → ~20 min on 4 CPUs (parallel workers, each
      state shared by 8 tests, the motor-scan fit no longer 9.5 s), the
      fresh-window guarantee kept; more CPUs make it faster. Left, if
      wanted: the box candidate still runs its 2000 evaluations (about
      1.5 s) on every Gaussian motor scan before failing; not fitting it
      when the peak fit is already adequate would change which shape is
      chosen in rare cases, so it is a fitting decision for the owner.
- [x] **The test suite's time, RAM and disk — done 2026-11-23** (this
      session took over from the stalled agent; physics_notes 2026-11-23,
      TESTING.md "Parallel by default"). Quick suite 9 min 44 s, ~10 GB,
      1.2 GB left in /tmp → ~2 min, 3.4 GB over four workers, nothing left;
      real-data suite ~25 → ~4 min. Causes found: every test's window leaked
      (deferred deletes never ran), a 9.5 s box fit on every motor-scan plot,
      a bisection in the pinhole footprint window, tmp_path kept for three
      runs, temporary folders never removed.
- [x] **File IO and caches reviewed — 2026-11-23** (physics_notes): MCA
      files now parsed once per file version (they were re-read on every
      selection change); the disk cache walks its folder only when it may
      be full. Open: frames held as int64 halve what the caches hold (an
      int32 cache would need every reduction re-verified); timing over a
      slow network drive.
- [x] **Three crashes reached by the sweep's random walks — fixed
      2026-11-23** (found by the Tools-menu session when its new control
      shifted the walks' draws; latent on main): the Ref Patch close-up
      with vertical background (bglcen), SpecPlot's log scale with nothing
      positive to show, an empty typed Pilatus distance
      (`tests/test_walk_crashes.py`).
- [ ] **Three real-data tests fail on main since 2026-11-22 (found
      2026-11-23, bisected)**: `test_patching.py::test_nx_school_scans_6_to_9`
      since 6bb29bf (the joint fit's guard ladder and 2 points either side:
      factors 0.023004, 0.064516, 0.103604 → 0.02298, 0.064474, 0.103695);
      `test_real_nx_school.py::test_reflectivity_scans_6_to_9_match_reference`
      and `test_packaging.py::test_self_test_passes_from_source` since
      b51bae2 (the joint fit made the window's default; the stored NX 6–9
      curve is the legacy method's). Not weakened: the reference tests
      probably should choose the legacy method explicitly (they are the
      proof that a refactor did not change the reduction), and the joint
      fit's own NX factors be re-pinned with before and after values. For
      the owner of patching.
- [x] **A Tools menu in the main window (new 2026-11-23) — done 2026-11-23
      (F84)**: every demonstration and figure generator as an item
      (`lss_toolbox/`, `docs/TOOLS.md`; 36 items, 62 documented variations),
      run from the repository's code in its own process; the demonstrators
      are started as their own process (`patch_demo.py`, which takes the space
      bar application-wide). A packaged build lists the items and the
      committed figures it holds but disables Run (no tools, no Python inside).
- [x] **Committed products the audit found stale (new 2026-11-23, F84) —
      remedied 2026-11-23** (`docs/reports/tools_audit.md`, "Remedied"):
      the two figures were an environment difference, not stale code; the
      C2/C3, C21 and survey tables remade with their text; C24 and C21 now
      written by `compare_methods.py`. Before:
      `python -m lss_toolbox --audit` reran every item with the settings of
      its committed products and compared (`docs/reports/tools_audit.md`).
      Each needs its rerun into the repository (Tools window, "Replace the
      committed products") together with a reading of the text that quotes
      it, by whoever owns the area. Measured stale: the beam-profile figure
      (1.6 % of pixels), the stray-light figures (4–16 %), the C2/C3
      error-model tables (made with the legacy patch before the joint fit
      became the default: σ up to 21 % different), the reflectivity survey
      (`ref_patch_nx`: guard ladder), probably the GID survey. Measured
      current despite git flagging them: the burn trends, the fit
      demonstrator, the gauntlet (every row), the pinhole and GID diagrams
      (but for their revision stamp). The C21 tables have no generator in
      the repository (written by one-off code on 2026-11-20): give them one
      or mark them as such.
- [x] **Three reader crashes that random walks reach (found 2026-11-23 by
      the crash sweep of the Tools-menu branch) — fixed 2026-11-23 by the
      test-speed session (#10, `tests/test_walk_crashes.py`); the walks again
      include the Tools menu and click popup-menu buttons (the recorder closes
      menus, #9)**: with one more control in
      the menu bar, five walks drew other sequences and raised in handlers
      the per-state sweep never reaches. Not baselined (the walk baseline is
      empty on main). The defects:
      (1) `refQzListSelectionChanged` (`mainwindow.py` ≈ line 5179) with
      `refCenCheckBox` ticked: `'TwoDDetector' object has no attribute
      'bglcen'` (reached by Ref Patch, Analyze, the slit field);
      (2) `specPlotSettings`: matplotlib "Data cannot be log-scaled because
      all values are <= 0" from the SpecPlot log y on a column of zeros
      (`spNComboBox`); (3) `updatePilPlotData` (≈ line 3357):
      `float('')` of an empty `pilSDDistLineEdit`.
- [x] **`gui_screens.py` no longer captures the g_l2 / g_l3 dialogs (found
      2026-11-23 by the Tools audit) — done 2026-11-23**: the step plots the
      sample-height scans 5 and 13 one by one (each gets its fitted centre),
      then selects both; the screenshot also showed the dialogs listing
      scans 5 and 13 as "6, 14", fixed (`test_known_defects`). Before: since the scan-fit rules of
      2026-11-23 (flat or weak scans not fitted) the synthetic motor scan 4
      has no fitted centre, so Calculations > g_l2 answers "Please plot the
      selected scans first" instead of opening. `docs/gui/screens/93_*`,
      `94_*` are kept from the morning's run. Give the screenshot a scan with
      a peak, or the dialog a way to say why there is no centre.
- [x] **Documented variations not yet reachable by an option (new
      2026-11-23) — done 2026-11-23**: pinhole case 8 (`--case8-dth`,
      `--case8-openings`), `monitor_noise_mc.py` (`--regimes`, `--monitors`,
      `--trials`, `--seed`), the C24 footprint and C21 angle comparisons as
      tables of `compare_methods.py`, the demonstrator's surveys
      (`patch_demo.py --survey N`, two Tools items), `synthetic_dataset.py`
      (`--roughness`, `--background`); each a catalogue variation with its
      document line (`tests/test_tool_options.py`). Before: parameters the documents vary that are fixed inside a
      script: the S4 openings and Det_Th of pinhole case 8 (drawn as a sweep
      inside the figure), the regimes of `monitor_noise_mc.py`, the footprint
      choice of C24 (`GIDParams(footprint='idl')`) in `compare_methods.py`,
      the demonstrator's surveys (`refl.survey(Config(plan='staggered'))`,
      `bm` monitor sweeps) and the `synthetic` generators' faults beyond the
      two `synthetic_dataset.py` offers. Each becomes an option and a
      variation in `lss_toolbox/catalog.py` when needed.
- [x] **Figures asked for but never made (found 2026-11-23) — done
      2026-11-23**: `tests/tools/burn_dose_figure.py` (NX 14/15 against dose:
      the position drifts 3.70× apart against time, 0.79× against dose),
      `tests/tools/gid_column_groups.py` (maps and the level join per column
      group; it found P46), `tests/tools/gid_movie.py` (M7: the DPPC peak
      still in 2θ while it walks 49 columns); each a Tools item. Before: the dose-axis
      burn comparison of NX 14 and 15 (07-burn-trends.md, F76), maps from
      column groups per level and the β-overlap cells of the join
      (physics_notes 2026-11-19), the movie on a common 2θ axis (M7). Each
      becomes a tool and a catalogue item when made.
- [x] **Tools whose default data include the private sets when present
      (2026-11-23) — done 2026-11-23**: `spec_epoch.py`, `monitor_gains.py`
      and `monitor_distribution.py` take their files as arguments (argparse;
      with none, the same output as before), and their Tools pages default
      to the public NX file; the variation "All sample data" gives the
      scripts' own default, private sets included when present.

**J. Beamline / SPEC macros**: see "Beamline to-do" at the end (series
lines, `Tstart`/`Tend`, `#V` flag, Pilatus + Vortex header, gas conditions
and dark rate, photons-in, half-cuts and an sh scan beside each GID level,
`#A` always written; `getandsave_mca` `#A`/gain low priority).

**L. Hard-coded and fragile assumptions — new 2026-11-23** (the owner asked for "column position lookups or similar hard-coded and fragile issues"; physics_notes 2026-11-23, "the fragility audit"). M measured, R read only.

| Assumption | What breaks | Evidence | Fix |
|---|---|---|---|
| ~~Every data row of a scan has as many numbers as `#L` has labels~~ **fixed 2026-11-23** (`spec_routines.complete_rows`, `test_spec_partial_line.py`) | one half-written last line (a file SPEC is still writing, i.e. live updates) lost **every column** of that scan | M: synthetic, the last line cut to two numbers → no columns | a line of another width is left out, noted (`DroppedRows`) and said once |
| ~~The header's `In_Rot` is each frame's incidence~~ **fixed 2026-11-23** (P47, `cuts.true_incidence`) | β of reflectivity frames (cuts, GISAXS) | M: P47, C43 | α from L in specular scans |
| ~~A frame's scan and frame numbers are read back from the list's text (`imageListWidget` 13 places, `scanListWidget` `split()[1]` 8, the Ref Qz list)~~ **fixed 2026-11-24** (item data: `SCAN_ROLE`, `FRAME_ROLE`, `LABEL_ROLE`, `QZ_ROLE`; `test_list_item_data.py` renames every item and checks nothing breaks) | any change of the displayed text (the GUI overhaul) breaks frame and scan lookups silently | R | keep them as item data (`Qt.UserRole`); Main, after GUI manager's F88/F69 (agreed 2026-11-24) |
| ~~Pilatus 100K sizes: default cut ranges `0:485`, `0:194`; GID last row 486; columns spin box max 195; 0.172 mm written 22 times in `mainwindow.py` (one constant exists, `cuts.PIXEL_MM`)~~ **fixed 2026-11-24**: the ranges from the frames read last (`cuts.default_range`, the 100K before any: `images.SHAPE_100K`); the GID last row follows the frames while left at its default (`GIDParams.for_detector`; `exp.gid` without params too) and the columns stop at theirs; the pixel written once (`images.PIXEL_MM`; the window takes `pilatus.pix_size`). Every number unchanged on the 100K, a monkeypatched 1M follows (`test_detector_sizes.py`) | defaults and limits wrong for the 1M (area H) | R | from `pilatus.NROWS`/`NCOLS` and one pixel constant |
| ~~File names cut at `/` (`specFileName.split('/')[-1]` makes the image and MCA prefixes)~~ **fixed 2026-11-24** (`lss_core.paths`, `test_paths.py`) | a path with backslashes (Windows, `os.path`) gives a wrong prefix: no images; plot-file legends show the whole path | R | `os.path.basename` |
| ~~`#B0` file extension from `split('.')[1]`~~ **fixed 2026-11-24** (`paths.ext`, `test_paths.py`) | a SPEC name with a dot (`run.v2`) hides the scan's images (detector read as "Monitor") | M: synthetic | `os.path.splitext` |
| ~~`#L` labels split on any space, no count check~~ **noted 2026-11-24**: columns still by position; a count mismatch goes in the scan's parameters (`LabelMismatch`) and one window message (`test_spec_labels.py`) | right for these macros (NX writes "PSD Seconds" with one space; its rows have 18 values); a label with a space (standard SPEC, "Two Theta") shifts every later column by one silently | M: NX labels vs row widths | compare label and row counts, say so |
| ~~Motor names as the macro truncates them to 8 characters (`Two_Thet`, `Sample_T`; the code looks up `Two_Thet`); `#O` full names unused~~ **fixed 2026-11-24**: both names kept, from `#O` and by cutting at 8 (`test_spec_motor_names.py`) | a macro writing full names breaks the lookups | R; NX headers | map `#P` to `#O` names, accept both |
| ~~`#A` and the `Absorber` motor of `#P4` both set the absorber; the later line wins (`#A`, in NX)~~ **fixed 2026-11-24**: `#A` wins by rule; a differing motor value is kept as `AbsorberMotor` (`test_spec_absorber_order.py`) | a macro writing `#A` first would make the motor's value win | R; NX order | prefer `#A` explicitly |
| ~~SpecPlot's default x: column 2 (L) whenever the first column is H; default y: the last column~~ **fixed 2026-11-24**: the index the `#S` command moves, else the column that varies, else L (`lss_core.scanaxes`, `test_scanaxes.py`) | an hklscan along H or K is plotted against a constant L | R | the column that varies, or the `#S` command |
| ~~L is Qz in Å⁻¹, H is Qx (the beamline's SPEC lattice)~~ **documented and checked 2026-11-24**: L = (2π/λ)(sin In_Rot + sin Out_Rot) to 0.001 % on NX; a fixed-L scan off by > 1 % is noted (`lss_core.lattice`, I35) | a changed lattice scales every Qz silently | M: NX scan 11, L = 4π sin(In_Rot)/λ to 0.06 % | document; check at load on fixed-α scans |
| ~~The Tools catalogue cites documents by line number (`docs/physics_notes.md:NNN`, 25 of them)~~ **fixed 2026-11-24** by tools man (07a8100: all 104 references are `path#text` anchors; `test_toolbox` fails on a line number or an anchor found on no line or several; 26 had already drifted) | every row inserted above them (an invariant) moves them all; two sessions inserting at once need a hand re-pointing by text (done in the merge of 2026-11-24); `test_toolbox` checks only the range | M: the 2026-11-24 merge | cite headings (anchors) instead, checked to exist; tools man |

**K. Questions for the owner in one batch — new**: P10–P12, P19, P35
("may be intended" behaviours never put to the owner), P21 (dark offset),
the open assumptions in `OUTPUT_DECISIONS.md`, and F41 (to the hand-off
author, not the owner).

## Inputs needed from the owner (consolidated 2026-11-19)

Ordered by what they unblock. "Can proceed" means work goes on with a
stated assumption until the answer arrives.

| # | Input | Unblocks | Without it |
|---|---|---|---|
| 1 | Answers on the series proposal (`handoff_out/05`, four questions) | Stage 3 series in the window, live refresh | can proceed on the proposed syntax as provisional |
| 2 | ~~A complete low + high Qz GID pair~~: private pairs received 2026-11-19 (C22); a **public** pair is still wanted for C14 | C14 comparison, F62 check on real data, P36/P37 need three levels | C14 stays "not like for like" |
| 3 | One full two-module 200K frame (one module is saved on purpose, D43; the second lies along 2θ, F63); a new-format fluorescence/GID SPEC file (F28); HDF5/bluesky file (F29); ME7 notes (F35; mostly answered by D48, D49); Pilatus + Vortex in one scan (F53); 1M geometry conventions (F38) | Stage 4, item by item | Stage 4 not started |
| 4 | `lss_reference.py`, `covariance_core.py` (XModJointFit) | Stage 5 hand-off tests 5–6 | independent implementation from the hand-off text |
| 5 | ~~`Monc`'s own noise~~: not needed (owner, 2026-11-19, D44). Which monitor model the Budget uses by default when it becomes the default: Gaussian 0.04 % (D22, now) or Student t (D26)? | Stage 5: Budget as default | Gaussian stays the Budget's default |
| 6 | ~~IDL `IMG_COO_CONV`/`LIMG_COO_CONV`, `SCAN_JOIN`, `SPEC_FILE_INFO`~~ received 2026-11-19 (`docs/reference_code/idl/`); still wanted: IDL output for NX 11+12 | checking the pinhole map against IDL numbers | pinhole checked on synthetic data and by reading |
| 7 | ~~IDL review §8: column response from data or geometry; per-column patch replacing or beside the 3-column one~~: both built as options (`fit`, `physical`, 2026-11-20); still open: PD_MERGE | GID defaults | pinhole default (D40), response fitted |
| 8 | Reflectivity series with overlaps at 6–7 keV; foil tolerance and alloy; Cu thickness at 30 keV | P28 below 10 keV; F49 at 30 keV | nominal Al below 10 keV; no factor at 30 keV |
| 9 | P29 mechanism (Monc high at narrow S1) | whether the 3 % Monc/Monp guard is right | guard as built |
| 10 | Confirm or change the open assumptions in `OUTPUT_DECISIONS.md` (3 % tolerance; per-photon gas and median rate; GID min frames, β step) | — | as built |
| 11 | Fitting requirements (F22a, 2026-11-19) | Stage 6 fitting | **done 2026-11-21**: peaks module, MCA lines, scan shapes, burn trends (open questions in the list below) |
| 12 | Run the build workflow once; macOS signing decision | packaged releases | Linux build measured only |
| 13 | ~~`bu.zip` link sharing~~ off (owner, 2026-11-19); where sample data live; ~~resend scan-136 frames~~ received 2026-11-18 | — | — |
| 14 | P7 Merge: kept as is (owner). Merge window and XFNTR merging: the owner's rule is F65 (match within 0.1 × grid step, jitter 3e-5 1/Å in the errors, grouping, never across runs); its edge estimator is backlog. `S1T + S1T`: fixed. Per-point MCA files: to be handled (owner: yes, 2026-11-19); channels and dead time answered (D48, D49) | F65, per-point MCA | — |
| 15 | ~~P39~~: decided 2026-11-19 (D51), exact window to the S4 ramps' inner edges; IDL's as an option | — | — |
| 16 | Half-cut sh scans for the beam's vertical profile (F43; owner, 2026-11-19) | a measured beam for response 'beam' and for P39 | the profile fitted from the GID data |
| 17 | GID frames with little signal (mostly background) at both arm heights (P40; owner offered, 2026-11-19) | stray light and beam-path background in GID maps | P40 open |
| 18 | GID overlap pixels: ΣN/ΣW (built) vs IDL's error-weighted mean (the owner chose "as the IDL code does", 2026-11-18; the error weights are biased at low counts, IDL review) | GID map values | ΣN/ΣW, to confirm |
| 19 | ~~S4–detector distance (P43)~~: calibrate from single frames (owner, 2026-11-21): built (5fbebf8), worksheet Fit; automatic calibration and the final GID defaults: large-data survey, `docs/handoff_out/06-gid-method-comparison.md` | — | header value until Fit |

### Stage 3 work list
- [x] Proposal for the "scan i of N" line (`docs/handoff_out/05-scan-series-syntax.md`).
- [x] Reader: `#U Series`, `#U SeriesMacro`, `#C … Scan aborted after k points`,
      `#C Series … end`; `lss_core/series.py` groups, finds missing scans and
      the status (complete, partial, in progress, aborted); `infer` for older files.
- [ ] Owner/beamline: answer the proposal's four questions; try the lines in SPEC.
- [ ] Window: series in the scan list (label "gid 2/2 (partial)", details in
      the tooltip), select a series as one action.
- [ ] Live refresh (F1–F5): poll the SPEC file and image folders, append, keep
      selections, re-reduce a series in progress.
- [x] Per-SPEC saved state, first part (2026-11-21, F66/D53): the workbook `<SPEC file>_reader.xlsx` with settings, fit preferences and saved results; Save buttons.
- [ ] Per-SPEC saved state, rest (F13–F16): reopen a SPEC file with its settings from the workbook; dropped points as masks with undo; tie saved results to series ids (review 2026-11-21, `docs/reviews/2026-11-21-todo-review.md`).

### Stage 2 work list
- [x] Fast, cached image reading, bit-identical (`lss_core/images.py`,
      `lss_core/cache.py`); no file is re-read on a selection change (D5,
      F7, F9).
- [x] Rapid image-list selection changes (drag, shift-click, keyboard) are
      merged into one redraw after 150 ms: 27 quick clicks 24 s -> 1.1 s.
- [ ] Redraw itself (~1 s for 9-10 frames): build the axes once and update
      the images in place when only the selection changed; `tight_layout`
      is ~20 % of it. Belongs with the GUI reorganisation (Stage 6).
- [x] SPEC and MCA readers without `eval` (`lss_core/numbers.py`): identical
      results on every sample file; MCA 24 → 1.2 ms per spectrum (F6).
- [x] Disk cache for network drives (F8): `lss_core/diskcache.py`; decoded
      frames as `.npy` in `~/.lss_reader/cache`, only for files on another
      file system by default, 5 GB limit (D18), LRU; settings by environment
      variable (a settings dialog comes with the per-SPEC config, Stage 3).
- [x] Reflectivity reduction scriptable without Qt (`lss_core/experiment.py`,
      `reflectivity.py`, `stitching.py`; `docs/SCRIPTING.md`): byte-identical
      to the window's files on synthetic and real data (F31, first part).
      The window uses the shared stitching code.
- [x] The window's Ref Patch computes each point with
      `lss_core.reflectivity.frame_row` (one implementation; the duplicated
      per-frame branches are gone). Scan order, drops and finishing in the
      window still mirror `lss_core` and are checked by the same fixtures.
- [x] Fluorescence (MCA window sum) scriptable and shared with the window;
      byte-identical `_flu.txt`; Script pane line on export.
- [x] Cuts normalised by monitor and absorber (D19, P23 fixed).
- [x] Error budget (D20): "Budget" error model, monitor term on whole sums,
      in every non-patched path and in Ref Patch's per-frame points;
      Errors pane; `errors=` in scripts. Legacy stays default.
- [x] Absorbers consistent (D21): messages when frames of different foil
      counts are combined on the nominal factor.
- [x] `Monc` is upstream of the absorbers (owner): a^n does not double-count.
- [x] Foils are before the sample; `#A` is in units of the absorber factor
      (≈ 1.414 at 10 keV, now the default).
- [x] F50 (D24): MCA scans take the absorber of the last `#A` above them;
      normalised spectra × absfac**n; the window says where each came from.
- [x] F52 option: normalise by `Monc` × its recorded gain (MCA, SpecPlot,
      scripts). Off by default.
- [x] F52 in the Pilatus paths (cuts, background images, GID data, frames
      at one Q_z).
- [x] Gains the reader cannot interpret: malformed lines (D33), treated as
      unknown; nothing to do (review 2026-11-21) unless the owner wants them read
      (`reports/monitor_gains.md`).
- [x] F54 core: photons/s from the monitor (`lss_core/flux.py`, xray_fluxor route D).
- [x] F54 in the window: "/ photon" option (MonC, dark 50 Hz when not recorded,
      D41), scripts `per_photon=True` (2026-11-19).
- [x] Student t: σ_scan · w · t₄, w ≈ 0.94, σ_scan 0.039 % if unknown (D22).
- [x] "width" is the t's scale (owner); σ_scan per scan declined: fixed t (D26).
- [x] Absorber factor default: 50 µm Al at 10 keV, 1.4247 (D25).
- [x] **P24 fixed**: the factor in use is the one shown (it was 1.606 from
      start-up until a GID/Ref action re-read the field). Old background-
      subtracted reductions at non-zero absorber settings should be redone.
- [ ] F53: Pilatus and Vortex from the same scans (tabs); needs a sample file.
- [x] F49 for Al (2026-11-18): the field follows the scans' energy ("from E").
      Reductions of bu scans at 6.21 / 7.51 / 9.9 keV with absorbers in
      should be redone (factor was 1.4247 per unit).
- [x] Crash site found by the sweep after "from E" (2026-11-18; the extra
      control changed the random walks): SPEC plot with log Y and a column
      that is 0 (Y2 = H in an L scan) raised FreeType 'raster overflow' on the
      point labels. Labels of points a log axis cannot show are now hidden.
      Sweep before the fix: 65 passed, 2 failed (this site); after: both pass.
- [ ] F49 for Cu at 30 keV: needs the unit thickness (owner).
- [x] Foils at 10.05 and 10.52 keV: aluminium (owner, D37).
- [x] `#A` 52 and 63 are real settings (owner, D38).
- [x] An unreadable `#A` line (one real case: an empty "#A Absorber " in
      bu/2026oct/20261019) was read as 63; now unknown: no factor, a message,
      "Abs=?", frames patched as usual (D42, 2026-11-19).
- [x] P28: nominal absorber steps 7–11 % off measured (NX school); calibrated
      foils built (F56); the 6–7 keV part stays open (input 8). Owner:
      reflectivity sets with overlapping joins from several days, to test
      day-to-day variation and calibrate per foil (`tests/tools/absorber_steps.py`);
      foil tolerance (flat µm or %) and alloy, if known.
      Hand-off for that analysis written 2026-11-18:
      `docs/handoff_out/02-absorber-patch-check.md` (+ `02-absorber_steps.py`);
      Answered 2026-11-18 (`handoff_out/02-answer-report.md`), reviewed
      in physics_notes: foils calibrated at 10 keV, stable over the year;
      the jumps are the monitor (P29).
- [x] Calibrated foil table in the reader (F56), Preferences (F57), known
      ratio in Ref Patch (F58), 2026-11-18. Off 9.70–10.30 keV the
      composition is needed (P28).
- [ ] Owner (P29): in R04/R05 and R17–R21 `Monc` reads high at S1 = 0.04 mm
      (scan a), by up to ×1.46; not an offset (needs beam). Scatter from the
      S1 blades into Monc, or where the beam sits on the narrow slit? Known
      at the beamline only.
- [x] Hand-off 03 answered (`handoff_out/03-answer/`): fit reproduced to
      0.1 µm; P29 is scan a's Monc reading high at the narrow S1 gap; figures.
- [ ] Owner (P28): reflectivity series with overlaps at 6–7 keV, to
      separate foil composition from thickness.
- [x] Gain reference S_ref = 5 µA/V (owner, D39).
- [ ] When the corrected/legacy two-file export (hand-off §2.5) is built,
      make Budget the default and carry the counting part as `sigma_meas`.
- [x] Monitor model default from the owner's analysis: Gaussian 0.04 %
      (D22); Student t offered (ν = 4, D26; 3.6 was the first estimate).
- [x] Cuts scriptable (2026-11-18): `lss_core/cuts.py` (`frame_cut`, shared by
      the window and `Experiment.cut`); Export writes `exp.cut(...)` to the
      Script pane, reproducing the files byte for byte (all directions, axes,
      Sum, Budget, typed geometry, pinhole, partial frames). The window's cuts
      were unchanged in all 48 configurations compared before/after.
- [ ] Stage 3 frame object: normalise once at load; make each reduction's
      normalisation explicit (owner's expectation, 2026-11-17).
- [ ] New output formats record reduction steps and parameters (R7).
- [x] GID scriptable (2026-11-19): `Experiment.gid`, one implementation with
      the window (`lss_core/gid.py`), Save GID writes the call; byte-identical.
- [ ] GISAXS scriptable; background-subtracted GID and cuts scriptable.
- [x] Exact pinhole geometry per pixel (P38; owner 2026-11-19, "is your trig up
      to snuff?"): `pinhole.pixel_angles` (IMG_COO_CONV), GID patch binned in (2θ, β).
- [x] Beam profile: response 'beam' built as an option (2026-11-19); default 'fit'.
- [x] The upper-level difference (pinhole vs legacy) on a private pair (done 2026-11-20:
      per-level illumination and stray light; continues as P40 and hand-off 06): the three central
      columns reproduce legacy; adding the outer columns changes the upper level relative
      to the lower; not area, polarisation or the response model. Next: maps from column
      groups (inner, middle, outer) per level, and the β-overlap cells of the Qz join.
- [ ] P38 remainder: exact angles also for the cuts' pinhole axis and the image
      display axes; the distance fit with exact angles.
- [ ] F63: second 200K module along 2θ for GID: detector description with the
      gap (Stage 4), then the pinhole patch over both modules; ask for a full frame.
- [x] Per-point times, old and new files (F37 reader side; owner's guidance 2026-11-19):
      `lss_core/timing.py`, `Experiment.point_times`.
- [x] Time as an x axis in the SPEC plot (`Time_s`, D46).
- [ ] Time as an x axis in the other plots: MCA integrals (per spectrum: its
      scan point's time), Ref/GID frame lists; burn tests (below).
- [ ] F65 step 3 (backlog): if built, the edge from the fitted element line
      (D47), not ln(Vortex/Monc).
- [x] Use the measured times where the reader assumed count time × frame:
      burn tests' Trends tab (2026-11-21; the Legacy tab keeps the old axis).
      SpecPlot already has `Time_s`.
- [ ] Backlog (owner, 2026-11-19): F65's edge estimator (steps 3, 4, 6: steepest rise of
      ln(Vortex/Monc), outlier check against the group median, alignment).
- [x] P36, P37 (legacy GID with three Qz levels): fixed 2026-11-23 with the
      synthetic three-level GID data set; outputs change only for such maps.
- [ ] Docket (2026-11-18): F59 cuts for diffuse scattering (I vs β, β − α;
      the Q cuts' default ranges miss the detector and plot zeros silently),
      F60 contextual/automatic reduction. Not to be built yet.
- [x] F61 GID worksheet (2026-11-18): the patch's settings editable, joins
      tabulated; defaults reproduce the patch exactly.
- [x] F45 pinhole correction, first version (2026-11-18): worksheet switch,
      off by default; physics_notes 2026-11-18.
- [x] Pinhole the default (D40), P32 and P34 fixed (2026-11-18).
- [x] F62 flexible overlaps between Qz levels, pinhole mode (2026-11-19).
- [x] Distances settled (owner, 2026-11-18): 551 sample→detector, 271
      S4→detector, 556 = g_l3 (sample → output-arm rotation centre).
- [ ] Owner (IDL review §8), what remains (review 2026-11-21): IDL output for
      NX scans 11+12; PD_MERGE's pinhole data; overlap arithmetic (input 18);
      one absorber setting per GID set. Settled: routines received (36c0432);
      `S7D_Dist` is S4–detector, 271 mm; pinhole the default (D40), legacy
      beside it; column response from data (`fit`) and geometry (`physical`)
      both built.
- [x] Owner: resend the scan-136 GID frames as a zip: received 2026-11-18.
- [x] Burn tests and peak fits scriptable (2026-11-21): `Experiment.burn`,
      `lss_core.trends`, `lss_core.peaks`; P30 fixed in the Trends tab.
- [x] Owner's answers on burn tests (2026-11-21): shutter closes, wall time
      better (clock default); position judgment is the user's (out of the
      limit by default); burn scans = `ascan ih` without movement.
- [ ] **Ask the owner later for more burn data** (owner, 2026-11-21: "ask
      later"): higher flux, reflectivity burns, the private file's burn scans
      (gid 23, 35, 51, 211, 275, 277, 278; xfntr 19, 20) with their frames.
- [ ] Burn trends: testing and extension by another agent
      (`docs/handoff_out/07-burn-trends.md`). Items (2026-11-21), tests first:
  - [ ] **Coverage for curved models.** The 95 % confident time is checked only
        for a linear truth (5.5 % misses); repeat the check with exponential and
        double-exponential truths, all four models fitted. If the miss rate is far
        from 5 %, compare a parametric bootstrap or a profile likelihood with the
        covariance draws.
  - [ ] **False alarms of the double exponential.** On constant data, count how
        often the double exponential wins by AICc and drags the 5 % time down. The
        verdict flags "a change a line misses"; this should be rare, and the rate
        belongs in C31.
  - [ ] **Estimators against known truths** (generator now in `tests/synthetic/burn_profiles.py`; first look found P44: the template reads a broadening at constant area as a 15 % gain). Synthetic pinhole-like frames with a
        peak that broadens at constant area, one that shifts, one that fades under a
        steady shoulder, and a rising background. Record which of template, moments
        and fit reads each truth, with its bias and scatter.
  - [ ] **Noise floor of each estimator.** The legacy moments use three points at
        each end for the baseline and degrade faster than the template as counts
        fall. Find the counts per frame where each becomes unusable, so the
        default can warn.
  - [ ] **Burn dialog in the crash sweep.** The sweep does not drive the burn
        dialog's own controls (models, estimator, errors, time, limit, Save). Add a
        sweep state with a burn scan selected and the dialog open, then run
        `pytest -m sweep`.
  - [ ] **Exponential to a plateau.** c + a·e^(kt) (three parameters) is a common
        physical form for damage that saturates and is missing from the four
        models. Adding it changes every comparison's criteria, so it needs an
        OUTPUT_DECISIONS row with before/after on NX.
  - [ ] **Dose axis.** Flux ∝ Monc × absfac^n, so Σ Monc·absfac^n·Seconds would
        compare burns at different absorbers and join consecutive scans on one
        spot. Test whether NX 14's and 15's position drifts (3.3 × apart at 4.1 ×
        the flux) fall on one curve against dose.
  - [ ] **Fluorescence burns.** XFNTR scans 19 and 20 of the private file are
        `ascan ih` without movement, with MCA spectra. Feed the line intensity per
        spectrum (`peaks.fit_series`, as "Fit lines") through `trends.compare`.
  - [ ] **Row range for GID burns.** The profiles now sum all detector rows; the
        Bragg rod's β range may give a cleaner peak. Expose `rows=` as a control
        in the dialog with a tooltip.
  - [ ] **Offer the burn test automatically (F60).** When a selected scan is a
        burn scan (`series.is_burn`), the window could offer or open the burn test.
        This belongs with the contextual-reduction work and the GUI
        reorganisation (R4).
- [x] Script pane (F48, first part): opening a SPEC file and exporting a
      patched reflectivity write the equivalent `lss_core` Python, which
      reproduces the exported files byte for byte (tested), including merges,
      drops and partial frame selections. Other actions follow as they
      become scriptable.
- [x] Resources (`.ui`, icons) loaded relative to the program, not the
      working directory (`lss_core/resources.py`; prerequisite for F46).
- [x] F46 packaged builds (2026-11-18): `packaging/lss_reader.spec`, pinned
      libraries, `--self-test`, GitHub workflow (Windows, macOS; manual or
      tag). Linux build measured here (self-test passed). The old recipe and
      the committed `build/` folder (an old .exe) are removed. The About box
      no longer needs the .py files (it raised in a build).
- [ ] Owner: start the build workflow once (Actions → build → Run
      workflow) and try the Windows/macOS builds; macOS signing is a
      decision (docs/PACKAGING.md).

### Stage 1 work list
- [x] Typos and leftovers: defects 2, 3, 4, 5, 6, 7, 14 and the shared
      default dictionaries; NumPy 2 scan-list formatting with one helper
      (D14).
- [x] `interp2d` replaced (`interp_compat.py`); GID low + high Q_z patching
      works on current SciPy and reproduces the SciPy 1.13 reference
      (defect 1).
- [x] Qz² export fix (F24b).
- [x] Crash inventory, image-display and 2D-plot handlers (153 pairs).
- [x] Crash inventory, reflectivity handlers (93 pairs).
- [x] Crash inventory, everything else: cuts, MCA, SpecPlot, images and
      background, calibration actions (151 pairs).
- [x] Baselines regenerated: 420 single-control combinations -> 3, then 0
      after the background-factor field was rewired.
- [x] Failures reached only by sequences: stale selections forgotten when
      the scan selection changes; movie frame indexing; cut export and fit
      button check their data; background sum with nothing selected; MCA
      log axes; 9-ID-C says it is unsupported.
- [x] All save handlers write nothing when the file chooser is cancelled.
- [x] Graceful opening: non-SPEC files (defect 4) and repeated scan
      numbers (F27).
- [x] Graceful opening (F27): missing images (also fixed a normalisation
      misalignment, PHYSICS_ISSUES P22), scan numbers not starting at 1,
      missing image folders with the chooser cancelled.
- [x] Bruker/CCD code removed (D8, F38); geometry kept in
      `ccd_geometry_precedent.md`; Apex tab hidden pending the GUI work.
- [x] Final sweep of Stage 1 (2026-11-17): 0 single-control failures in 14
      runs, 0 crash sites in 24 random sequences of 150 actions.
- [ ] Remaining read-only defects of `ASSESSMENT.md` §4 (8: 9-ID-C reader —
      removed, not needed, D17; 10–13, 15:
      physics, tracked in `PHYSICS_ISSUES.md` and not to be changed without
      the owner).

Working method for the crash inventory: Sonnet sub-agents, one at a time,
each given one group of handlers; the main session reviews the diff,
reruns the quick, real-data and export-fixture checks, and commits.

## Carried over from the tests-and-scoping phase

- [x] Time the full selection path on real data → `docs/timings.md`
      (`pytest -m bench`). Pilatus 1M and per-point MCA could not be timed
      through the window: this version cannot load them.
- [ ] Time the same path against a deliberately slow file system, to
      separate network cost from redraw cost.
- [x] Crash sweep covers controls inside secondary dialogs (one level).
- [x] Crash sweep runs each state with file dialogs cancelled and with
      file dialogs returning paths.
- [x] Random walks (150 steps, 3 seeds, 3 states) pinned by crash site.
- [x] Sweep made cheaper (one selection signal per action), then made
      stricter (fresh window per control).
- [x] `pytest -m slow` rerun in full: all pass, expected failures as marked.
- [ ] Characterisation tests still missing for: GISAXS, g_l2/g_l3 and
      absorber-ratio fits, the legacy peak-fit dialog, 2D plot tab. (Done
      since: GID multi-scan joining `test_gid_scan_join.py`, `test_gid_script.py`;
      MCA merge `test_mca_merge.py`; cuts, burn tests, MCA fits: the 2026-11-21
      tests.) (All fitting
      features stay, D7, so each needs tests. Bruker is defunct: none.)
- [x] NX school GID scan 11 frozen as a reference; low + high Q_z patch
      pinned as an expected failure (interp2d). The shipped
      `dppc_*_gid.txt` come from other scans and are not comparable.
- [x] GID low + high Q_z patch run under SciPy 1.13 and stored as the
      reference (NX school scans 11 + 12; scan 12 has 4 frames).
- [x] Invariant I4 (ROI error propagation) tested directly.
- [x] Python 2 → 3 audit → `ASSESSMENT.md` section 8; Bruker reading and
      the g_l2 dialog pinned as expected failures.
- [x] Reflectivity export pinned byte for byte (`test_ref_export_golden.py`)
      as the legacy fixtures the hand-off asks for.
- [x] XFNTR benchmark: synthetic with known line counts, `_flu.txt` bytes,
      and a hash of the real `bu` export.
- [x] Benchmarks added (R5, R6): burn tests (synthetic reflectivity with
      known τ; real GID burn), MCA peak fit, line cuts on real frames and
      through a real GID map.
- [ ] Benchmarks still missing (R5): GISAXS, GIOXS, calibration fits
      (g_l2, g_l3, absorber ratio), cut export bytes, a real reflectivity burn
      scan (none in the samples); synthetic GID with known truth: partly
      (`test_pinhole.py`). (GID export bytes: `test_gid_script.py`.)
- [ ] Run each reduction path on Pilatus 1M frames by calling the code
      directly, to measure what the module gaps do (D11).
- [ ] Synthetic K = 3–5 scan generator with known factors and a non-one-hot
      overlap, as hand-off §5 requires, and the acceptance tests 2–4 written
      against the contract as expected failures.
- [ ] Measure the stitch-factor interpolation bias on real overlaps.
- [ ] ORSO export (F25): read the format specification and list the header
      fields the reader can and cannot fill.
- [ ] End-to-end "known photons per monitor count in, same number and
      Poisson error out" check for each reduction path (GID, GISAXS, cuts,
      MCA sum), as already done for reflectivity.
- [ ] Regenerate `docs/timings.md` on an idle machine (the committed table
      predates the file-count columns).
- [x] Scoping document written: `SCOPE.md`.

## Waiting on the owner

- [x] **Monitor noise analysis** (hand-off `handoff_out/01-monitor-noise-analysis.md`):
      answered 2026-11-17, Gaussian σ = 0.04 % (D22).

- [x] Remaining feature requests and complaints (received so far: F1–F16
      in `FEATURE_REQUESTS.md`; the owner called the latest list partial). (Requests received through F65; new ones are added as they come, 2026-11-19.)
- [x] Counting time and fitting questions answered (2026-11-15; D6, D7,
      F20–F22).
- [x] Hand-off on the xmodfit export received (F24, F25).
- [ ] **Remind the owner:** `tests/lss_reference.py` and
      `covariance_core.py` from XModJointFit (unreleased, not public) for
      hand-off acceptance tests 5 and 6. Until then, work around it with an
      independent implementation of hand-off §3 written from the text.
- [ ] Stitch-factor interpolation bias: experiments ensure shared Q_z
      points for now (D13). **Do not forget:** it is to be remedied later
      in the corrected chain (Stage 5; reopened by the review of 2026-11-21:
      a ticked "do not forget" is how it gets forgotten).
- [ ] **Remind the owner:** a full two-module 200K frame (the 200K data received are one module, 2026-11-19); a reflectivity
      burn scan; a public low + high Q_z GID pair (private pairs received 2026-11-19); the new fluorescence &
      GID SPEC file (F28); an HDF5/bluesky file (F29); ME7 data notes (F35).
- [x] Monitor noise investigated (`reports/monitor_noise.md`).
- [x] Beam variation vs monitor noise examined (`physics_notes.md`,
      2026-11-16): `Monc`'s scatter in reflectivity scans is mostly real
      flux variation through S1, which the detector also sees.
- [x] ~~Measure `Monc`'s own noise before a normalisation model is chosen~~: not
      needed, the Student t model is good enough (owner, 2026-11-19, D44).
- [ ] **GID background data (P40, 2026-11-19; owner offered GID data with
      little signal):** frames at both arm heights with the same slits;
      if possible the sample lowered out of the beam, S5 nearly closed at
      the raised arm, the lower level repeated after the upper, and the S4
      and S5 vertical openings and the S5 → detector flight path.
- [x] Is the MCA "Merge" weighted mean Σ(y²/σ²)/Σ(y/σ²) intended? Explained 2026-11-19
      (it equals ΣN/ΣM, pooled counts over pooled monitor); owner to confirm. Owner, 2026-11-19: kept as is; the error is handled downstream (F65).
- [x] Scoping input for F22 (where better fitting is needed, which models)
      and F23 (GID patching: overlaps, methods). F22a received 2026-11-19; F23 superseded by the pinhole GID work (D36).
- [ ] Format of the photons-in estimate in the SPEC file (F21), when the
      beamline defines it.
- [x] Pilatus 1M: another version handles it but is not otherwise better;
      stay on this code base, 1M support is feature group F17–F19.
- [x] Should per-point MCA files (`mca_save_point`) be readable from the
      window? Open points on the 1M are listed under F17–F19. Owner, 2026-11-19: yes (F53).
- [x] Bruker/Apex CCD is defunct (D8): no fix; remove the code later.
- [x] Link sharing off on `bu.zip` (owner, 2026-11-19).
- [ ] **Data request for Q-EXAFS-2 and F89/F90 (2026-11-23; owner: "tell me what example real data would answer it"):**
      one SPEC file plus its folders for a single energy scan (`MCAscanpt escan_14`
      or another `escan`) *and* one fluorescence burn (`ascan ih` with spectra),
      with whatever MCA files sit beside them (the `vortex/` folder of per-point
      files, `<date>_<scan>_mca`, if present). What answers the question is
      whether the scan's block in the SPEC file has a `#V` line with spectra, or
      only `mca_save_point Point:p Scan:s` entries and separate files. Also for
      F90: one spectrum with a strong elastic peak and Compton shoulder beside a
      weak line (the Zn 8637 eV at 10 keV excitation case) and a note of the
      detector's energy calibration, and if there is one a blank (pure water or
      the subphase) at the same Qz and counting time: the synthetic half (C42)
      shows the scatter's shape under the line decides F90; passed to questor
      for `DATA_NEEDS.md` row 3, 2026-11-23. Mark private files as such (they stay under
      `sample_data/private/`).
- [ ] **All data needs are listed in `docs/DATA_NEEDS.md` (2026-11-23)**: read it before asking the owner for data; the owner's non-cloud agent will supply the large private sets (reflectivity series for hand-off 08 "not soon"; GISAXS and GIOXS examples later).
- [ ] **Open beam and shutter questions OQ-1 to OQ-4 (2026-11-24):** slit values half or full openings; the vertical beam size after the mirror focus and before the APS shutdown; how fast mode appears in a SPEC file. Full text and why in `docs/gui/questions.md` ("Open questions added on 2026-11-24"). They block the dose per area of F98 and the sx colouring of F107; until they are answered the beam size stays a typed value.
- [ ] Decide how sample data should be hosted (`bu` is 1.7 GB, local to the
      session only, git-ignored; NX school is committed at 104 MB).
- [ ] Questions in `ASSESSMENT.md` sections 6 and 7 still open: reference
      geometry for image axes vs cuts (P6), negative 2θ (P5). (S1T + S1T fixed
      2026-11-19; 9-ID-C answered, D17.)

## Original phase plan (superseded by SCOPE.md stages; kept for history)

1. Process-wide exception handler and durable log (F10–F12, D4): turns
   every hard abort into a logged failure. Agreed as the first step.
2. Bug fixes from `ASSESSMENT.md` section 4, one test each; empty the crash
   inventory (`tests/known_crashes.json`); remove the Bruker path (D8).
3. Extract physics and readers into GUI-free modules.
4. Feature requests in `FEATURE_REQUESTS.md` (caching and no re-reading on
   selection change, D5; live refresh; per-SPEC config with read-only
   second instance, D1–D3; Pilatus 1M; per-second option, F20; covariance
   export for xmodfit, F24, which needs the merge logic factored out of the
   dialogs; ORSO export, F25).
5. Sub-projects that need their own scoping: GID patching (F23), fitting
   improvements (F22).
6. GUI reorganisation.

## Done

What has been built is summarised in `ACCOMPLISHMENTS.md` (2026-11-22);
the items below are the tests-and-scoping phase, kept for history.

- [x] First assessment (`ASSESSMENT.md`) and addendum with measured results.
- [x] Test scaffolding, synthetic data, fast suite (47 pass, 8 expected
      failures).
- [x] Crash inventory baseline, confirmed repeatable.
- [x] NX school sample data committed; real-data reflectivity regression.
- [x] `bu` sample data local; robustness run over all eight SPEC files.
- [x] Feature requests F1–F16 and project context recorded.
- [x] Never-writes-to-SPEC rule pinned by a test; hard-abort on a raising
      handler demonstrated and pinned as an expected failure.

## Beamline to-do (SPEC macros at 15-ID-C)

Things the data files should record and do not. The reader works around
them; the fix belongs in the macros.

- Note (owner, 2026-11-17): `getandsave_mca` is a test macro, not the normal
  XFNTR scan (`fluo_p`, an MCAscanpt hklscan with a `#V` line); the two
  items below matter only for it. Whether `fluo_p` scans write `#A` and
  `#M Monc Gain`: **yes** (measured for the review of 2026-11-21: all 153
  `#V` hklscans of the private XFNTR file have both; only the 7
  `getandsave_mca` scans have neither), so these two are low priority.
- [ ] **`getandsave_mca` writes no absorber setting** (`#A`): checked on
      every sample file; the MCA file header has none either. The reader
      takes the last `#A` above the scan (D24), which cannot see a change
      made between scans by a command that is not a scan. (owner, 2026-11-17)
- [ ] **`getandsave_mca` writes no monitor gain** (`#M Monc Gain`), and the
      gain changes within files (P26, F52).
- [ ] Some `#M Monc Gain` lines have no unit ("200") or no value
      (bu/2026oct/20261019, 20261022); the reader treats them as unknown.
      Full list: `reports/monitor_gains.md`.
- [ ] `#V` detector-type flag, 1, 4 or 7 elements (F34).
- [ ] Series lines `#U Series …`, `#U SeriesMacro`, `#U SeriesT0` (F39;
      proposal `handoff_out/05`, under review by the owner's agent, 2026-11-19).
- [ ] Per-point `Tstart` and `Tend` in place of `Epoch` (F37; owner, 2026-11-19).
- [ ] Photons-in estimate in the SPEC file (F21), when the beamline defines it.
- [ ] Half-cut sh scans to characterise the beam (F43), and a height (sh) scan
      next to each GID level: the liquid's height drifts by several µm in half an
      hour to an hour (owner, 2026-11-19), which moves the footprint by mm.
- [ ] Multiple exposures per GID point (F40).
- [ ] A scan with both Pilatus and Vortex data should say so in its header
      in a way that does not let one line override the other (F53).
- [ ] **Gas conditions for photons/s** (F54; owner, 2026-11-19): record the
      ion-chamber temperature and pressure, or the current photons/s
      number from the monitor IOC. The reader now assumes the hand-off
      table's 24.9 °C and 98.99 kPa (±0.8 % from the site-mean pressure).
- [ ] **Dark counts** (F54, D41; owner, 2026-11-19): record the dark rate
      from the new monitor IOC. The reader now assumes 50 Hz on Monc.
- [ ] One `#A` line with no value (bu/2026oct/20261019, scan 1): the macro
      should always write the setting. The reader treats it as unknown (D42).

