# Testing

## Setup

    python -m venv .venv
    .venv/bin/pip install -r requirements-dev.txt

No display is needed; the tests run Qt on its `offscreen` platform.

## Running

    pytest              # fast suite, about 30 s
    pytest -m slow      # real-data regression (sample_data/NX_school), about 2 min
    pytest -m sweep     # crash inventory, about 25 min

## What is there

| File | Purpose |
|---|---|
| `tests/synth.py` | Writes synthetic SPEC, Pilatus TIFF and MCA files. The formats are reverse-engineered from the readers, so they show that the code runs, not that it reads real beamline files correctly. |
| `tests/conftest.py` | Fixtures: `qapp`, `recorder` (captures message boxes, dialogs and exceptions raised in Qt slots; file dialogs return "cancelled"), `window`, `dataset`, `loaded`. |
| `test_fresnel.py`, `test_twod_detector.py`, `test_parsers.py`, `test_stitching.py`, `test_gid_area.py` | Unit tests of the numerics, including the analytic invariants listed in `physics_notes.md`. |
| `test_gui_workflows.py` | Reduces the synthetic data set through the real widgets and compares with the curve the data were generated from. |
| `test_real_nx_school.py`, `reference/` | Reduces the real NX school reflectivity scans and compares with a stored curve produced by this program. |
| `test_known_defects.py` | Defects from `ASSESSMENT.md`, each as a strict expected failure. |
| `sweep.py`, `test_gui_sweep.py`, `known_crashes.json` | Crash inventory, see below. |

## Three kinds of assertion

- **Invariant**: must hold for the physics to be right (for example R_F = 1
  below Q_c). These never change.
- **As coded**: freezes what the program computes today so that refactoring
  cannot change numbers unnoticed. Marked "as coded" or "characterisation" in
  the test. Changing one is allowed but must be deliberate and recorded in
  `physics_notes.md`.
- **Expected failure** (`xfail(strict=True)`): states the behaviour we want
  and currently do not get. Fixing the defect makes the test pass, which
  pytest reports as a failure until the marker is removed in the same commit.

## Crash inventory

The stated goal is that no sequence of selections and button presses raises.
`tests/sweep.py` puts the main window into each of seven states (nothing
loaded; SPEC file loaded; a motor scan, a Pilatus scan, one frame, two scans
with all frames, or MCA frames selected) and then triggers every push button,
check box, menu action, combo box, line edit and spin box once, re-applying
the state before each one.

`tests/known_crashes.json` records every control that raises, with the
exception type and the function it came from. `pytest -m sweep` fails if a
control not in the list raises, and also if a listed control no longer raises,
so the list can only get shorter. After fixing crashes, regenerate it:

    LSS_UPDATE_CRASHES=1 pytest -m sweep

Limits of the sweep: one control at a time per state (no long random
sequences yet), file dialogs always cancelled, secondary dialogs opened but
their own controls not driven, Bruker images not covered.
