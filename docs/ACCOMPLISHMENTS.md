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
| Tests | 764 quick, 487 slow (real data), 67 crash-sweep, 1 timing (collected 2026-11-23 after the covariance merge; the line said 624 quick and 584 slow, while the tree it was written for collected 637 and 483) |
| Crash inventory | 420 failing control/state combinations on 2026-11-14 → 0 since Stage 1 (2026-11-17) |
| GUI-free core (`lss_core/`) | 28 modules, about 7,700 lines; every reduction scriptable |
| Analysis tools (`tests/tools/`) | 31 (recounted 2026-11-23), each the source of a figure or a measured number; 30 are items of the reader's Tools menu (34 items, 59 documented variations; `docs/TOOLS.md`), one is a helper |
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

- Line and area cuts normalised by the monitor (they were raw).
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
  plateau (P9 fixed: 0.471, was 0.406).
- Burn tests as trends over time (`lss_core.trends`, `lss_core.burn`):
  constant, linear, exponential and double exponential compared by AICc;
  "stable" when a flat line fits as well as a line; the 95 % confident time
  to a 5 % change (coverage measured: 5.5 % misses for a nominal 5 %); per
  monitor count and on wall-clock time (P30 fixed); GID intensity,
  position and width each on its own panel with a percent axis. NX scans 14
  and 15 (measured): intensity stable in both; position drifts about 3 ×
  faster at about 4 × the flux; width +19 % in 15. Tests and extensions for
  another agent: `handoff_out/07`.

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

## The Tools menu (2026-11-23, F84)

- Every demonstration and figure generator of the repository is an item of
  the reader's **Tools** menu and of the Tools window (`lss_toolbox/`,
  also `python -m lss_toolbox`): 34 items in seven menus (burn tests,
  reflectivity patching, GID and pinhole geometry, monitor and scans,
  synthetic data sets, the window and manual, made elsewhere).
- Nothing drifts: a run executes the script as it is in the repository, in
  its own process, into a run folder with a record of the command and the
  commit; each page's options are read from the script's own parser; the
  page `docs/TOOLS.md` is generated from the same catalogue; tests fail on
  an uncatalogued script, on a variation naming a missing option, on a
  committed figure no item claims.
- The documents' "change this and regenerate to see that" sentences are 59
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

## Records kept for others

`physics_notes.md` (every question with its answer, dated, and 26
invariants with their tests), `PHYSICS_ISSUES.md` (44 issues with sizes
and status), `OUTPUT_DECISIONS.md`, `COMPARISONS.md` (33 comparisons with
how to regenerate them), `MANUAL_NOTES.md` and `manual/controls.md` (every
control's tooltip), `SCRIPTING.md`, a review of the to-do lists
(`reviews/2026-11-21-todo-review.md`).

## Not done yet (the main items; all in `TODO.md`)

Final GID defaults from the larger data set; the export defaults now
that the covariance files exist (Stage 5, owner's decisions in TODO B2); the burn intensity estimator
(P44); detectors and new formats
(Stage 4: Pilatus 1M, HDF5); the GUI reorganisation (planned, waiting
on the owner's answers in `gui/questions.md`); answers from the
owner on the series format, the batch of physics questions, and more burn
data.
