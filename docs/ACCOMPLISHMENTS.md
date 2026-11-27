# What has been done

A summary for the owner and for newcomers: what the reader can do now that
it could not when this fork began (2026-11-14), area by area, with where
the details are. Written 2026-11-22; update it when a stage or a large
feature is finished. The working lists are in `TODO.md`; the reasons and
the measurements are in `physics_notes.md` (dated), `OUTPUT_DECISIONS.md`
(every default that changes a number) and `COMPARISONS.md` (old against
new). "Measured" below means a test or a run gave the number; everything
else is how the code is built.

## In numbers (2026-11-22; tests recounted 2026-11-23)

| | |
|---|---|
| Commits on this fork | about 230 (2026-11-14 to 2026-11-22) |
| Tests | 796 quick (~2 min on 4 CPUs, parallel), 487 slow (real data, ~3.5 min), 193 crash-sweep (~20 min), 1 timing (2026-11-23; before that day 9 min 44 s, ~25 min and ~3 h in one process) |
| Crash inventory | 420 failing control/state combinations on 2026-11-14 → 0 since Stage 1 (2026-11-17) |
| GUI-free core (`lss_core/`) | 30 modules, about 9,300 lines; every reduction scriptable |
| Analysis tools (`tests/tools/`) | 35 (recounted 2026-11-23), each the source of a figure or a measured number; 34 are items of the reader's Tools menu (41 items, 88 documented variations; `docs/TOOLS.md`), one is a helper |
| Synthetic data (`tests/synthetic/`) | reflectivity with Kiessig fringes and the water–air interface, scans with known factors and planted faults, Pilatus frames, GID levels, burn profiles, XFNTR, growing files (`SYNTHETIC_DATA.md`) |
| Hand-offs | 8 written for other agents or the owner's data (`docs/handoff_out/`), 3 answered |

## By stage (`SCOPE.md`)

**Stage 0, safety net (2026-11-17).** A failing action is logged and
reported, never closes the program; a durable log per session and per
SPEC file; messages in a pane instead of blocking dialogs.

**Stage 1, repairs (2026-11-17).** The assessed defects that were plainly
broken fixed (defects 1–7 and 14 of `ASSESSMENT.md`: GID patching on
current SciPy, typos, dialogs that raised, the bad-pixel factor; defect 10,
the S1 slit sum, on 2026-11-19); every handler guarded before data are loaded;
crash inventory emptied; the Bruker CCD and 9-ID-C code removed (defunct).

**Stage 2, readers and reduction out of the window (2026-11-18).** SPEC
and MCA readers without `eval` (MCA 20 × faster); cached image reading and
a disk cache for network drives; reflectivity, cuts, fluorescence and GID
maps in `lss_core`, shared by the window and scripts, which reproduce the
window's files byte for byte; the Script pane shows the Python for what
the window did; packaged builds (recipe and self-test).

**Stage 3, state per SPEC file and live refresh (started 2026-11-19, much
of it built).** See "Series, saving and live updates" below.

**Stage 6, sub-projects.** GID patching and fitting built (below); beam
size: the half-cut fit exists, waiting for data; GUI reorganisation:
planning only (2026-11-22, D58: inventory of 403 controls, workflow map
checked against the window by the quick suite, screenshots, questions for
the owner, in `docs/gui/`); no GUI code changed for it yet.

## Normalisation, errors, absorbers

- Line and area cuts normalised by the monitor (they were raw); since
  2026-11-23 every view of the detector data too (image display, GISAXS,
  SpecPlot's normaliser by name), and "Sum All" sums counts and monitors
  and divides once, ΣN/ΣM (F91; C41).
- A budget error model beside the legacy one: the monitor's uncertainty
  applied once to each whole sum (the legacy errors understate it, ×1.4 to
  ×6.5, measured).
- Monitor gain from `#M Monc Gain`, values per incident photon (the
  xray_fluxor route), the Monc dark rate.
- Absorber factor from the beam energy (NIST aluminium table), calibrated
  foils from the owner's runs, the known ratio offered at a Ref Patch join
  when it beats the fit; an unreadable `#A` is unknown, not 63.

## GID (pinhole) patching

- Exact per-pixel angles (Mati Meron's IMG_COO_CONV ported); pinhole mode
  the default; Qz levels joined on a shared 2θ grid without interpolation;
  the patch's hidden numbers editable in a worksheet with a table of joins,
  updated live; within a level each scan is joined against everything
  joined so far, so a chain of scans whose ends do not overlap is patched
  (P41 fixed, 2026-11-22).
- The exact footprint window (P39), column responses fitted, along the
  beam, or physical (rays through pixel and S4 with a Gaussian beam), and
  joins "as collected" as an option; scan scales fitted with the response
  (P42).
- Single unpatched frames as ground truth for peak position and width;
  the S4–detector distance calibrated from them (NX 265.7 ± 1.1 mm against
  the header's 271, measured), after which patched peaks equal the single
  frames'.
- A technical addendum to the manual with eight diagrams
  (`manual/gid_patching.md`) and a method-survey hand-off for the final
  defaults on the owner's larger data (`handoff_out/06`).

## Fitting and burn tests

- One peak module (`lss_core.peaks`) for line cuts, GID profiles and MCA
  spectra: found automatically, Gaussian, Lorentzian or pseudo-Voigt on a
  polynomial background, misfits flagged; "Fit peaks" and "Fit options…"
  beside the cut plot; "Fit lines" for MCA series (the sum fixes position
  and width); SpecPlot recognises a peak, an edge (the half-cut beam) or a
  plateau (P9 fixed: 0.471, was 0.406); a flat scan (the background alone
  fits it) is not fitted, nor a sample-height scan with poor signal or
  narrower than 20 µm (owner, 2026-11-23; C37).
- The MCA line-fit gauntlet, the synthetic half of F90 (2026-11-23, C42):
  - a generator of MCA spectra with the beam's scatter under the lines
    (`tests/synthetic/mca.py`: Rayleigh, Compton with an O 1s wing, Si
    escapes, tails, shelves);
  - `tests/tools/mca_fit_gauntlet.py`, under Tools > Fluorescence (MCA).

  Measured on synthetic data:
  - the window sum never holds once scatter lies under the box;
  - "Fit lines" holds on a smooth background, but not against the
    elastic's Si escape, the O 1s Compton wing or low counts;
  - a Poisson per-spectrum step, a fixed detector width and escape
    stripping are proposed to Main; no default was changed.

  Real spectra and a blank decide it (`DATA_NEEDS.md` row 3).
- Study B, MCA line intensities (2026-11-24, C47, `docs/studies/mca_fit/summary.md`). The owner's study of F90's
  decisions, with figures B1–B7 from `tests/tools/mca_study.py`; water's Compton scatter is now modelled shell by
  shell. Measured on synthetic data:
  - data weights read weak lines low, and P1 fixes that;
  - the window sum fails under scatter;
  - Zn under a 10 keV beam needs a blank to decide;
  - at 12 keV, P1 alone passes.
- The synthetic MCA project's wrap-up (2026-11-24; the owner paused it to wait for real data):
  `docs/reports/mca_fit_demo.md`, a reader's guide to the generator's parts, the six estimators and
  what the stress test taught, with the beam-energy figure (`tests/tools/mca_fit_demo.py`: P1 within
  0.3 % at 12 keV where it fails at 10 keV) and the Tools menu's MCA items and variations; the hard case
  as MCA files for the reader (`synthetic_dataset.py --kind mca`).
- "Fit lines" two ways (2026-11-26, F110, the owner's decision, revised the same day): the reader's Poisson fit
  (Si escapes stripped, the width from the sum of the series) is the number plotted, merged and exported in
  `_flu.txt`; XeRay (`fluorescence.xeray_fit`, ported from the Lee group's tool in the XRF shootout) is reported
  beside it with its error (list, plot, workbook, `_flu_xeray.txt`). Refining the shootout is on the after-2.0 list.
- Burn tests as trends over time (`lss_core.trends`, `lss_core.burn`):
  constant, linear, exponential and double exponential compared by AICc;
  "stable" when a flat line fits as well as a line; the 95 % confident time
  to a 5 % change (coverage measured: 5.5 % misses for a nominal 5 %); per
  monitor count and on wall-clock time (P30 fixed); GID intensity,
  position and width each on its own panel with a percent axis. NX scans 14
  and 15 (measured): intensity stable in both; position drifts about 3 ×
  faster at about 4 × the flux; width +19 % in 15. Tests and extensions for
  another agent: `handoff_out/07`.
- The dose each point gives the sample (`lss_core.dose`, 2026-11-24, F98's
  core): photons by the owner's counts-to-photons route, or Monc counts with
  the absorbers taken out, per mm² of footprint when the beam size is given;
  burns fitted against dose (`exp.burn(axis='dose')`). NX 14 (measured):
  2.9e13 photons in 210 s through absorber 12.
- The dose as peak and average, with the peak split (F109's core,
  2026-11-25): a Gaussian beam's map over every point's footprint, its
  average over the smallest area that received 90 % of the dose, and the
  most exposed 10 % of that area against the rest (`exp.dose_summary`); the
  beam's width from S1 horizontal slit scans (`exp.beam_width`). NX 14
  (measured): peak 1.54e12, average 6.0e11 photons/mm² over 43 mm².
- Dropped points as a mask over raw points (`lss_core.masks`, 2026-11-24,
  F92's core): kept in the workbook, applied by `exp.reflectivity(mask=...)`;
  the patch dialog's typed drops turned into raw points, and every row of a
  patched curve traced to its point (`reflectivity.drop_points`).
- Diffuse-cut axes (`lss_core.cuts`, 2026-11-24, F97's core): β, β − α (α
  from Qz), Qz and exact Qxy for any cut, intensities unchanged; the range
  a Q cut can take on the detector, and a band about the beam (F59).
- The beam's height for the dose from the rising edge of the height scans
  (`exp.beam_height`, 2026-11-24; the local data agent's study of 1995
  private scans, #60): NX school 0.033 mm.
- One reader writes a SPEC file's workbook, a second opens it read-only
  (`lss_core.readerlock`, `Workbook(read_only=True)`, 2026-11-25, D1's core):
  an atomic lock beside the workbook, refreshed by its holder, taken over
  when stale.
- GID burn estimators with the shoulder split off (P44, 2026-11-27):
  `burn.measure_gid(..., estimator='split')` and `'split_fixed'`, for scripts.
  On synthetic burns they read every case to 0.13 pp on a Gaussian shoulder,
  where the template is off by up to 14 pp. On NX burn 15 the template reads
  −1.5 % "stable" and the split −13.3 % "changing" (measured, known truth and
  public NX; `docs/studies/burn_shoulder/`, C70). The default is unchanged.
  Real burns: issue #155.

## Reflectivity patching and uncertainty (2026-11-22)

- A joint fit of both scans at each join (one smooth curve in ln(R/R_F),
  no interpolation) removes the stitching bias P1 and gives factors 20–30
  % more precise on synthetic data (measured); the known absorber ratio as
  a correlated prior where the monitor shows it applies; the stitched
  curve's full covariance (P4), as reusable code (`lss_core.uncertainty`).
  **The default patch since 2026-11-22**, after passing the synthetic
  gauntlet (C36, measured: designed conditions, 139 of 155 joins pass,
  legacy 1; random mixtures, 415 of 463, and 41 of the 48 failures are
  joins sampling fewer than 3 points per fringe, where every curve model
  fails); the legacy fit stays
  a preference and still reproduces the old files byte for byte. The
  comparison on the owner's larger data set is handed off
  (`handoff_out/08`).
- A fit demonstrator (`tests/demonstrator/`, report
  `reports/patch_demo.md`): synthetic replicates, their fits by every
  patching method and the burn line-cut fits, in a small window that steps
  through replicates.
- The covariance exported for model fits (the xmodfit sidecar,
  `lss_core.covariance_export`) and a reference fitter that uses it
  (`lss_core.gls`). Scripts can write it with any patch method
  (`save(covariance=...)`), and the window's Ref Patch has a "+ covariance"
  box (off). On synthetic film fits, pull SDs are 0.97–1.07 with the
  covariance and 1.7–4.2 with the legacy error column (measured,
  `reports/downstream_covariance.md`).
- Why the join errors are too small on real data (C61, 2026-11-25): hidden
  per-point scatter reproduces the survey's under-coverage, join-level
  inflations fail at fringed joins, honest per-point errors fix both
  (measured, synthetic with known truth; `docs/studies/guard_error/`). Its
  walkthrough (`walkthrough.md`, rule 13) follows one join from the two scans
  to the verdict, with a real NX school split whose miss came from a zig-zag
  that χ² cannot see.
- A bad-pixel pass on the reflectivity ROI (C62, F95 B3, 2026-11-25): on
  sparse frames hot pixels add up to 11 error bars per point; the ROI pass at
  factor 10 removes 90 % of them and touched no clean frame, while factors 3–4
  can take half a real sparse point (measured, synthetic with known truth; NX
  school unchanged at any factor; `docs/studies/roi_bad_pixels/`).
- The join's error budget with C63's measured excess (C64, 2026-11-25,
  corrected the same evening): the within-scan σ × 1.12 explains the real
  splits' under-coverage and fixes it (1.08 / 1.01); the between-scan part
  sits at the overlap (today 13 % catastrophic misses if C63's pairs sit
  there); 4σ clipping as built removes good points in rare cases and reports
  a confidently wrong factor, so it needs a guard (measured, synthetic with
  known truth; `docs/studies/excess_remedy/`). Waits for DATA_NEEDS 17.
- Qoff and the Qz resolution fitted together at the edge
  (`fresnel.fit_edge_resolution`, 2026-11-27, hand-off 09, issue #154): R_F
  with the subphase's absorption, smeared by σ_Q. On synthetic edges it reads
  Qoff to 1e-6 Å⁻¹ and σ_Q to 0.5 % with honest errors, where today's sharp
  proposal is off by up to 3.5e-4. NX scan 6 does not follow the model (σ_Q
  goes to 0, χ²/dof 102). A survey tool for real edges comes with it
  (measured, known truth and public NX; `docs/studies/qoff_resolution/`,
  C71). Propose is unchanged.

## Series, saving and live updates (2026-11-19 to 22)

- **Per-point times** for old files (Epoch steps) and new ones
  (Tstart/Tend); time as an x axis in SpecPlot.
- **Scan series**: the proposed `#U Series` lines are read; older files
  are guessed (reflectivity, GID, XFNTR, energy, burn); a Series list above
  the scan list; clicking a scan selects its whole series (on by default).
- **The workbook** (`<SPEC file>_reader.xlsx` in the output folder, 7
  sheets): every finished reduction saved automatically, Save buttons for a
  version with a note, results tied to their series with the call that
  remakes them, fits and burn trends in their own sheets, GID maps as
  grids Excel can colour.
- **Live updates**: a "Live" box watches the SPEC file, the Pilatus folder
  and the MCA files; every new SPEC line, image or spectrum is read without
  resetting the window (selection, tab, axes and frames kept); results
  whose series grew are remade in a background thread from their recipes
  (parsed, never executed), with the user's frame selection kept, saved as
  new versions and shown in the open plot; live mode stops at the end of a
  series written with series lines.
- **Reopening a file restores its settings, and line cuts are remade live** (2026-11-27, #145):
  - opening a SPEC file applies the settings its workbook recorded at the last save, and one message lists
    what changed (the owner's choice);
  - live updates remake line cuts with their peak fits, MCA "Fit lines" results (`flu.fit_lines`) and SpecPlot
    curves (`exp.curve`);
  - recipes that use the absorber foils are accepted (`absorbers.calibrated`), so foil-attenuated cuts and
    reflectivities are remade rather than left stale.

## Testing and speed (2026-11-23)

- **The suites** (`TESTING.md`, "Parallel by default"): parallel by
  default (pytest-xdist, one worker per CPU as memory allows); quick suite
  9 min 44 s → ~2 min, real data ~25 → ~3.5 min, crash sweep ~3 h →
  ~20 min (each state shared by 8 tests). Every test's window used to stay
  in memory (~10 GB per quick run, now 3.4 GB over four workers);
  `tmp_path` and temporary folders are cleaned up (1.2 GB left per run
  before, nothing now). Agents run the suites with a plain command
  (`AGENTS.md`).
- **The program, where the tests showed it slow:** the motor-scan shape fit
  (9.5 s on every plot of a Gaussian scan → under 2 s, flat and weak scans
  not fitted at all); the pinhole footprint window in closed form (the
  distance calibration 30 → 6.6 s, columns identical; C38); MCA spectra
  with log y (100 spectra: 4.2 → 0.8 s) and `pcolor` maps (5–7 × faster;
  C39); the GID map in Q regridded once per map instead of on every
  redraw (redraws 1.0–1.4 → 0.3 s, G1); MCA files parsed once per file version instead of on every
  selection change (0.38 s → 8 ms per click for a 20-scan series); the
  disk cache no longer walks its folder for every new frame.
- Three real-data tests failing on `main` since 2026-11-22 found and
  bisected (TODO area I).

## The Tools menu (2026-11-23, F84)

- Every demonstration and figure generator of the repository is an item of
  the reader's **Tools** menu and of the Tools window (`lss_toolbox/`,
  also `python -m lss_toolbox`): 41 items in seven menus (burn tests,
  reflectivity patching, GID and pinhole geometry, monitor and scans,
  synthetic data sets, the window and manual, made elsewhere).
- Nothing drifts: a run executes the script as it is in the repository, in
  its own process, into a run folder with a record of the command and the
  commit; each page's options are read from the script's own parser; the
  page `docs/TOOLS.md` is generated from the same catalogue; tests fail on
  an uncatalogued script, on a variation naming a missing option, on a
  committed figure no item claims.
- The documents' "change this and regenerate to see that" sentences are 88
  variations, each with its document line, one click from a run. Where a
  documented parameter was hard-coded it became an option (the foil fit's
  cuts; the demonstrator's settings, `patch_demo.py --set`).
- Committed products: possibly stale from git history (`--stale`);
  measured by rerunning and comparing pixel for pixel (`--audit`, in the
  window "Compare all"): `docs/reports/tools_audit.md`.
- A synthetic data set with known truth opens in the reader from the menu
  (`tests/tools/synthetic_dataset.py`: reflectivity with frames, XFNTR,
  burn; faults P29 and a foil 2 % off).
- Built and tested apart from the main window (owner's suggestion): the
  reader gains one call, `initToolsMenu`.
- Everything it put on the to-do list remedied the same day: stale
  products remade (two were an environment difference, which the audit now
  detects), C21/C24 given a generator, new figures (burns against dose, the
  GID join per column group, the GID movie on one 2θ axis), and a bias in
  the pinhole join factors found and fixed (P46).

## Records kept for others

`physics_notes.md` (every question with its answer, dated, and 26
invariants with their tests), `PHYSICS_ISSUES.md` (44 issues with sizes
and status), `OUTPUT_DECISIONS.md`, `COMPARISONS.md` (39 comparisons with
how to regenerate them), `MANUAL_NOTES.md` and `manual/controls.md` (every
control's tooltip), `SCRIPTING.md`, a review of the to-do lists
(`reviews/2026-11-21-todo-review.md`).

## Not done yet (the main items; all in `TODO.md`)

Three real-data tests fail since 2026-11-22 (the joint fit became the
default; bisected, TODO area I).

Final GID defaults from the larger data set; the export defaults now
that the covariance files exist (Stage 5, owner's decisions in TODO B2); the burn intensity estimator
(P44); detectors and new formats
(Stage 4: Pilatus 1M, HDF5); the GUI reorganisation (planned, waiting
on the owner's answers in `gui/questions.md`); answers from the
owner on the series format, the batch of physics questions, and more burn
data.
