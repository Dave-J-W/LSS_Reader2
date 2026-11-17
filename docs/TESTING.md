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
| `pytest` | fast suite: unit tests and GUI workflows on synthetic data | ~25 s |
| `pytest -m slow` | regressions on real data in `sample_data/` | ~15 s, +30 s with `bu` |
| `pytest -m bench -s` | timing table, rewrites `docs/timings.md` | ~30 s |
| `pytest -m sweep` | crash inventory (see below) | ~30 min |
| `LSS_UPDATE_CRASHES=1 pytest -m sweep` | regenerate the crash baselines | ~30 min |

`slow`, `bench` and `sweep` are deselected by default (`pyproject.toml`).
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
| `synth.py` | Writes synthetic SPEC, Pilatus TIFF and MCA files. |
| `sweep.py` | Drives the window: application states, control enumeration, fresh-window driver, random walks, `dispose`. |
| `test_fresnel.py`, `test_twod_detector.py`, `test_parsers.py`, `test_stitching.py`, `test_gid_area.py` | Unit tests of the numerics, including the analytic invariants in `physics_notes.md`. |
| `test_gui_workflows.py`, `test_gui_cuts.py` | Reduce the synthetic data set through the real widgets and compare with the curve it was generated from. |
| `test_real_nx_school.py`, `reference/` | Real NX school data: SPEC inventory, reflectivity scans 6–9 and GID scan 11 against stored curves produced by this program. |
| `test_ref_export_golden.py`, `reference/legacy_export/` | Today's `_ref.txt` / `_rrf.txt` byte for byte (synthetic and real), the "legacy" fixtures required by the xmodfit hand-off; plus the export format and traps T3, T8. |
| `test_xfntr.py`, `reference/private_hashes.json` | Fluorescence (XFNTR) reduction on synthetic spectra with known line counts: window sum, peak fit, "Fit All"; `_flu.txt` bytes; a SHA-256 of the real `bu` export (private data: only the hash is committed). |
| `test_burn.py` | Burn tests: synthetic reflectivity frames with a known decay constant; real GID burn (NX school scan 14) against stored curves. |
| `test_real_bu.py` | Private data: every scan of every SPEC file opens without raising. |
| `test_known_defects.py` | Defects from `ASSESSMENT.md`, each a strict expected failure. |
| `test_gui_sweep.py`, `known_crashes.json`, `known_crash_sites.json` | Crash inventory. |
| `tools/monitor_noise_mc.py` | Not a test: Monte Carlo behind `docs/reports/monitor_noise.md`. Run with `python3 tests/tools/monitor_noise_mc.py`. |
| `tools/monitor_ratio.py`, `tools/spec_epoch.py` | Not tests: analyses of the sample SPEC files behind entries in `physics_notes.md` (beam variation vs monitor noise; what the Epoch column measures). |
| `test_bench_selection.py` | Timing and file-read counts per user action. |

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
(`test_gui_workflows.py`). To test a new reduction path, extend `synth.py`
so the expected answer is known analytically, rather than freezing output.

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
