# Testing

Start with `AGENTS.md` in the repository root for the rules; this file is
the reference for how the suite is built and how to add to it.

## Setup

    python -m venv .venv
    .venv/bin/pip install -r requirements-dev.txt

No display is needed; the tests run Qt on its `offscreen` platform. Verified
from a fresh clone on 2026-11-14 with Python 3.13, PyQt5 5.15.11,
NumPy 2.5.4, SciPy 1.18.1, Matplotlib 3.11.2, Pillow 13.0.0, lmfit 1.3.4,
sympy 1.14.0, pytest 9.2.0. `requirements.txt` is unpinned; if a newer
library changes a number, record it in `physics_notes.md`.

## Running

| Command | What | Time |
|---|---|---|
| `pytest` | fast suite: unit tests and GUI workflows on synthetic data | ~10 min (625 tests, 2026-11-22) |
| `pytest -m slow` | regressions on real data in `sample_data/` | ~25 min (584 tests, 2026-11-22) |
| `pytest -m bench -s` | timing table, rewrites `docs/timings.md` | ~30 s |
| `pytest -m sweep` | crash inventory (see below) | ~3 h in one process (2026-11-22; was ~30 min on 2026-11-18); ~80 min in three shards, below |
| `LSS_UPDATE_CRASHES=1 pytest -m sweep` | regenerate the crash baselines | as above |
| `LSS_SWEEP_TIMES=FILE pytest -m sweep` | also append each control's time (state, control, seconds) to FILE, to find a slow one | |

`slow`, `bench` and `sweep` are deselected by default (`pyproject.toml`).

**The sweep in shards.** The sweep grew with the window: every control and
every dialog child gets a fresh window in its state, about 1 to 1.7 s each
(mostly matplotlib drawing the new window's plots and first frame; the
controls themselves took 16 s of a 295 s test, measured with
`LSS_SWEEP_TIMES`), and the pilatus states now hold about 260 of them. Its
tests are independent, so they can run as separate processes, about 2 GB
each at most (measured 2026-11-22: shards of 67, 78 and 29 min, all on one
4-core machine):

    python -m pytest -m sweep --collect-only -q | grep :: > ids.txt
    for k in 0 1 2; do awk -v k=$k 'NR%3==k' ids.txt > shard$k.txt; done
    for k in 0 1 2; do python -m pytest -q -m sweep $(cat shard$k.txt) > shard$k.log 2>&1 & done; wait

Do not run the shards beside another heavy suite (memory).
Tests on `sample_data/bu` skip themselves when that private folder is
absent, so a fresh clone passes without it.

## A second, older environment

The suite also runs under Python 3.11 with SciPy 1.13.1 and NumPy 1.26.4
(`pip install "numpy<2" "scipy<1.14" "matplotlib<3.9" "pillow<11" PyQt5
lmfit sympy pytest`). There the GID patching test passes for real, and the
only failures are the two library effects (`interp2d` present, NumPy 1
integer formatting). Use it to produce "legacy" numbers for anything that
cannot run on a current SciPy.

## Files

| File | Purpose |
|---|---|
| `conftest.py` | Fixtures (below). Sets offscreen Qt and the working directory. |
| `synth.py` | Writes synthetic SPEC, Pilatus TIFF and MCA files (outputs must not change; new generators go in `synthetic/`, see `docs/SYNTHETIC_DATA.md`). |
| `sweep.py` | Drives the window: application states, control enumeration, fresh-window driver, random walks, `dispose`. |
| `test_fresnel.py`, `test_twod_detector.py`, `test_parsers.py`, `test_stitching.py`, `test_gid_area.py` | Unit tests of the numerics, including the analytic invariants in `physics_notes.md`. |
| `test_gui_workflows.py`, `test_gui_cuts.py` | Reduce the synthetic data set through the real widgets and compare with the curve it was generated from. |
| `test_real_nx_school.py`, `reference/` | Real NX school data: SPEC inventory, reflectivity scans 6–9 and GID scan 11 against stored curves produced by this program. |
| `test_ref_export_golden.py`, `reference/legacy_export/` | Today's `_ref.txt` / `_rrf.txt` byte for byte (synthetic and real), the "legacy" fixtures required by the xmodfit hand-off; plus the export format and traps T3, T8. |
| `test_xfntr.py`, `reference/private_hashes.json` | Fluorescence (XFNTR) reduction on synthetic spectra with known line counts: window sum, peak fit, "Fit All"; `_flu.txt` bytes; a SHA-256 of the real `bu` export (private data: only the hash is committed). |
| `test_burn.py` | Burn tests (Legacy tab): synthetic reflectivity frames with a known decay constant; real GID burn (NX school scan 14) against stored curves. |
| `test_trends.py` | `lss_core.trends`: constant, drift, exponential, double exponential recovered; QAICc; errors from the scatter; coverage of the confident 5 % time (slow). |
| `test_burn_trends.py` | `lss_core.burn` / `Experiment.burn`: time axes, synthetic reflectivity τ, synthetic GID profiles per estimator, NX scans 14 and 15 (slow). |
| `test_gui_burn_trends.py` | The burn dialog's Trends tab: opens analysed, options kept, Save to the workbook; GID: one panel per quantity with a right axis in percent, the summary beside them (slow). |
| `test_real_bu.py` | Private data: every scan of every SPEC file opens without raising. |
| `test_known_defects.py` | Defects from `ASSESSMENT.md`, each a strict expected failure. |
| `test_gui_sweep.py`, `known_crashes.json`, `known_crash_sites.json` | Crash inventory. |
| `tools/monitor_noise_mc.py` | Not a test: Monte Carlo behind `docs/reports/monitor_noise.md`. Run with `python3 tests/tools/monitor_noise_mc.py`. |
| `tools/monitor_ratio.py`, `tools/spec_epoch.py` | Not tests: analyses of the sample SPEC files behind entries in `physics_notes.md` (beam variation vs monitor noise; what the Epoch column measures). |
| `test_bench_selection.py` | Timing and file-read counts per user action. |

Not listed above until 2026-11-22, by area:

| Files | Purpose |
|---|---|
| `test_reader_log.py`, `test_guards_2dplot.py`, `test_guards_reflectivity.py`, `test_guards_remaining.py`, `test_graceful_opening.py`, `test_no_ccd.py` | Stages 0–1: nothing closes the program (real subprocess), every handler guarded before data are loaded, odd SPEC files and folders open quietly, the CCD code gone. |
| `test_lss_core.py`, `test_api.py`, `test_cut_script.py`, `test_gid_script.py`, `test_script_console.py` | Stage 2: the GUI-free core and scripting; scripted reflectivity, cuts and GID maps write the window's files byte for byte; the Script pane's Python reproduces them. |
| `test_error_budget.py`, `test_gui_error_budget.py`, `test_monitor_gain.py`, `test_per_photon.py`, `test_flux.py` | Errors and normalisation: the budget error model, monitor gain, values per incident photon (xray_fluxor hand-off examples). |
| `test_absorbers.py`, `test_absorber_unknown.py`, `test_absorber_steps.py`, `test_handoff_absorber_steps.py`, `test_foil_fit_from_joins.py`, `test_known_ratio_patch.py`, `test_gui_absfac_energy.py`, `test_spec_absorber.py`, `test_fluorescence_absorber.py`, `test_gui_preferences.py` | Absorbers: factor from the energy, calibrated foils, known ratio in Ref Patch, unknown `#A`, settings inherited from the last `#A`, Preferences. |
| `test_mca_channels.py`, `test_mca_merge.py` | Fluorescence: multi-element files and the element selector; MCA Merge with the owner's XFNTR rule. |
| `test_pinhole.py`, `test_gid_worksheet.py`, `test_gid_scan_join.py`, `test_s1_slit_sum.py`, `test_interp_compat.py` | GID: exact pinhole geometry, responses, joins, distance calibration, the worksheet, joins across 2θ; the S1 slit sum; the interp2d replacement. |
| `test_peaks.py`, `test_gui_peak_fit.py` | Peak module and the cut/MCA fit buttons. |
| `test_timing.py`, `test_series.py`, `test_gui_series.py` | Per-point times; scan series (lines, aborts, guesses: reflectivity, gid, xfntr, energy, burn); the Series list and whole-series selection. |
| `test_workbook.py`, `test_gui_workbook.py` | The per-SPEC workbook: sheets, versions, series ties, stale flags, map grids, automatic saving, notes. |
| `test_patching.py` | Joint-fit reflectivity patching and `lss_core.uncertainty`: P1 removed on the staggered grid, exact quartic data, scaling rules, sensitivities, chain covariance, global = chain, prior combination and guard, stitched covariance, Monte Carlo pulls (slow), NX 6–9 (slow). |
| `test_live.py`, `test_gui_live.py` | Live updates: recipes parsed not executed, point selections carried over, remakes in a worker thread, open displays redrawn, new images and spectra picked up, no reset. |
| `test_packaging.py` | Packaged builds: the recipe bundles what the program loads; the self-test passes from source. |
| `synthetic/` (package), `test_synthetic_xrr.py`, `test_synthetic_xrr_scans.py`, `test_synthetic_xrr_images.py`, `test_synthetic_gid_levels.py`, `test_synthetic_burn_profiles.py`, `test_synthetic_xfntr.py`, `test_synthetic_growing.py` | Generators with known truth (2026-11-22; `docs/SYNTHETIC_DATA.md`): reflectivity of water, DPPC and films (Fresnel, Parratt, Névot–Croce, Kiessig), reduced scans as measured with true factors and faults, frames that reduce to them exactly, the Ref Patch GUI path against the truth; three-level legacy GID (P36, P37 as strict xfails); GID burn profiles; XFNTR yields and spectra; growing files for live mode. |

Note (2026-11-22): `test_gui_workflows.py::test_rapid_clicks_in_the_image_list_are_drawn_once`
waits 100 ms for a selection timer and has failed three times when the
suite ran beside the crash sweep on a busy machine; it passes alone. Since
2026-11-22 it waits up to 3 s for the one draw and then checks that no
second one follows.

## Fixtures (`conftest.py`)

| Fixture | Gives you |
|---|---|
| `qapp` | The one `QApplication` (session scope). |
| `recorder` | Makes modal dialogs return at once and records `messages` (message-box texts), `dialogs`, and `exceptions` raised in Qt slots. Controls what file dialogs return: `open_name`, `open_names`, `save_name`, `directory` (empty means "cancelled"). |
| `window` | A fresh `MainWindow` (uses `recorder`), output directory set to `tmp_path`. |
| `dataset` | Path of a synthetic SPEC file with `pilatus/` and `vortex/` beside it: scans 1–2 reflectivity (scan 2 through one absorber), 3 fluorescence, 4 a motor scan. |
| `loaded` | `window` with `dataset` opened. |

Helpers in `sweep.py`: `STATES` (named application states, each a function
`(window, app, spec)`), `_select_scans`, `_select_images`, `controls(widget)`
(every named control as a callable), `dispose`. Two states,
`pilatus_two_scans_budget` and `mca_frames_budget`, switch the Errors pane to
the budget error model first, so the sweep covers both error models.

## Three kinds of assertion

- **Invariant**: must hold for the physics to be right (for example R_F = 1
  below Q_c). These never change. Each is listed in `physics_notes.md`.
- **As coded**: freezes what the program computes today so that refactoring
  cannot change numbers unnoticed. Marked "as coded" or "characterisation"
  in the test. Changing one is allowed but must be deliberate and recorded
  in `physics_notes.md` with before and after values.
- **Expected failure** (`xfail(strict=True)`): states the behaviour we want
  and currently do not get. Fixing the defect makes the test pass, which
  pytest reports as a failure until the marker is removed in the same commit.

## Recipes

**A numerical unit test.** Call the function directly with arrays you can
reason about; see `test_twod_detector.py`. Methods of `MainWindow` that do
not touch widgets can be called unbound (`MainWindow.fresnel(None, q, qc)`);
those that do need the `window` fixture (`test_stitching.py`,
`test_gid_area.py`).

**A GUI workflow test.**

    def test_something(loaded, qapp, dataset, recorder):
        sweep.state_pilatus_one_frame(loaded, qapp, dataset)   # get into a state
        loaded.ui.someButton.click()
        qapp.processEvents()
        assert recorder.exceptions == []       # nothing raised in a slot
        assert recorder.messages == []         # no message box, if none is expected
        assert loaded.someResult == pytest.approx(...)

**A check against known truth.** `synth.make_dataset` builds peaks whose
height follows `synth.reflectivity`; compare reduced values with that
(`test_gui_workflows.py`). For reflectivity with a physical curve (water,
DPPC, Kiessig fringes) and known join factors, use `synthetic.xrr_scans`
(reduced rows) and `synthetic.xrr_images` (frames); see
`docs/SYNTHETIC_DATA.md`. To test a new reduction path, add a generator
under `tests/synthetic/` so the expected answer is known analytically,
rather than freezing output.

**A real-data regression.** Open the SPEC file, set
`window.directory = str(tmp_path)`, run the workflow, compare with a file in
`tests/reference/`. State in the docstring that the reference is the
program's own output (see `test_real_nx_school.py`). Mark it `slow`, and
`skipif` the data is absent.

**Pinning a defect.** Write the test for the behaviour you want, confirm
with `pytest --runxfail` that it fails for the reason you think, then add
`xfail(strict=True, reason=...)` naming the defect number in
`ASSESSMENT.md`.

**A benchmark on private data.** Never commit numbers derived from
`sample_data/bu`. Export the file to `tmp_path`, hash it, and compare with
`tests/reference/private_hashes.json` (see `test_xfntr.py`).

**A new application state for the sweep.** Add a `state_<name>` function in
`sweep.py` and to `STATES`, then regenerate the baselines.

**A new detector or file format.** Add a writer to `synth.py` first, with a
round-trip test through the real reader, as `write_pilatus_tif` has.

## Crash inventory

The stated goal is that no sequence of selections and button presses raises.
`tests/sweep.py` measures how far the program is from that, in two ways.

**Single controls** (`test_no_new_crashes`). The main window is put into
each of seven states (nothing loaded; SPEC file loaded; a motor scan, a
Pilatus scan, one frame, two scans with all frames, or MCA frames selected).
Every push button, check box, menu action, combo box, line edit and spin box
is then triggered once, each in a fresh window. When a control opens a
dialog, every control of that dialog is triggered as well. Each state is run
twice: with every file dialog cancelled, and with every file dialog
returning a usable path (keys ending `+paths`).

`tests/known_crashes.json` records every control that raises, with the
exception type and the function it came from. The test fails if a control
not in the list raises, and also if a listed control no longer raises, so
the list can only get shorter.

**Sequences** (`test_random_walk_raises_only_at_known_sites`). From three of
the states, 150 randomly chosen controls and list selections are applied one
after another with nothing reset in between, for three fixed seeds. A walk
changes whenever behaviour changes, so its steps cannot be pinned; what is
pinned is the set of places exceptions come from. Sites that only walks
reach are listed in `tests/known_crash_sites.json`. A site in neither file
fails the test.

After fixing crashes, regenerate both files:

    LSS_UPDATE_CRASHES=1 pytest -m sweep

**Inside dialogs** (`tests/test_dialog_workflows.py`). The dialogs behind
"Ref Patch" (identical-scans dialog, patch dialog, beam-position and
bad-pixel information dialogs), "Burn test" and the GID actions (patch,
form-factor dialog, save, GISAXS, cuts) have scripted tests and random
walks: every control of whatever dialogs are open is pressed, typed into
(from a bank of good and bad inputs) or chosen from, 40–60 times in a row,
reopening the dialog when it closes. The walks are marked `sweep`.

Not covered: real mouse interaction with the plots. Bruker images are deliberately not covered: that detector is defunct.
