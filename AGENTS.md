# Working on LSS_Reader2 (for coding agents and new contributors)

LSS_Reader ("reader") is a PyQt5 desktop program that parses a SPEC file,
loads the raw detector data beside it, and reduces it (monitor
normalisation with Poisson error propagation) for liquid-surface X-ray
scattering at ChemMatCARS. It is not a fitting program. Read
`docs/PROJECT_CONTEXT.md` first.

## Current phase — read before changing anything

**Tests, assessment and scoping only.** The owner has asked that application
code (`mainwindow.py`, `TwoDDetector.py`, `spec_routines.py`,
`mca_routines.py`, `*.ui`, `LSS_Reader.py`) is **not changed** until the full
feature list has been received. Work goes into `tests/` and `docs/`. Check
the top of `docs/TODO.md`; if the phase line there has changed, that file
wins over this paragraph.

## Where things are

| Path | What it is |
|---|---|
| `docs/PROJECT_CONTEXT.md` | What the program is for, in the owner's words |
| `docs/ASSESSMENT.md` | Structure, physics to preserve, numbered defects, Python 3 audit |
| `docs/FEATURE_REQUESTS.md` | Requirements R1–R4 and requests F1…; add new ones here with the date |
| `docs/TODO.md` | What to do next, what is waiting on the owner, what is done |
| `docs/TESTING.md` | How the test suite works and how to extend it |
| `docs/physics_notes.md` | Invariants table and a dated question-and-answer log |
| `docs/timings.md` | Timing baseline written by `pytest -m bench` |
| `docs/handoff/` | Specifications handed over by the owner (xmodfit export contract). They are requirements; do not edit them |
| `tests/` | The suite; `synth.py` (synthetic data), `sweep.py` (GUI driver) |
| `sample_data/NX_school/` | Real, public data set (committed) |
| `sample_data/bu/` | Real, private data set: git-ignored, never commit or push it |

## Commands

    pip install -r requirements-dev.txt
    pytest                 # fast suite, ~25 s; run before every commit
    pytest -m slow         # real-data regressions, ~15 s (+30 s with bu data)
    pytest -m bench -s     # rewrites docs/timings.md
    pytest -m sweep        # crash inventory, ~30 min; run after GUI-facing changes

No display is needed. Run from the repository root.

## Rules of the house

1. **Never weaken a test to make it pass.** A changed number is either a bug
   you introduced or a deliberate change; if deliberate, say so in the commit
   and in `docs/physics_notes.md` with before and after values.
2. **Three kinds of assertion** (details in `docs/TESTING.md`): invariants
   (never change), "as coded" characterisations (change only deliberately),
   and `xfail(strict=True)` for behaviour we want but do not have. When you
   fix a defect, remove its `xfail` marker in the same commit.
3. **The legacy export fixtures never change** (`tests/reference/legacy_export/`),
   except for the one fix the hand-off permits (Qz², trap T8). They are the
   proof that a refactor did not change the reduction.
4. **The crash baselines only shrink.** `tests/known_crashes.json` and
   `tests/known_crash_sites.json` are regenerated with
   `LSS_UPDATE_CRASHES=1 pytest -m sweep`, never edited by hand, and a
   regenerated file must not contain entries that were not there before
   unless the commit explains why.
5. **Record what you learn.** A question from the owner and its answer go in
   `docs/physics_notes.md` (dated, with how the answer was verified: test,
   run, or reading only). Quantities that must be conserved go in the
   invariants table there, with the test that checks them.
6. **Say what was measured and what was only read.** The docs keep these
   apart; keep doing so.
7. **The reader never writes to the SPEC file**, and tests must not write
   into `sample_data/`. Set `window.directory = str(tmp_path)` after opening
   a SPEC file (the `window`/`loaded` fixtures and `tests/test_real_*.py`
   show how).
8. Commit small and push often to `main` of this fork; the owner asked for
   that. Do not open pull requests unless asked.

## Things that will bite you

- The program loads `.ui` files and icons relative to the working
  directory. `tests/conftest.py` changes to the repository root; anything
  run outside pytest must do the same.
- PyQt5 **aborts the process** when a slot raises, unless `sys.excepthook`
  is replaced. The `recorder` fixture replaces it and collects the
  exceptions; always assert `recorder.exceptions == []` in GUI tests.
- Message boxes and dialogs are modal. The `recorder` fixture makes them
  return at once and records them; never create a `MainWindow` in a test
  without it.
- Selecting list rows one at a time fires the selection handler once per
  row, and the image handler re-reads every selected frame each time. Use
  `sweep._select_scans` / `sweep._select_images`, which select as one action.
- Windows are heavy (several matplotlib canvases plus images). In loops,
  free them with `sweep.dispose(window, qapp, recorder)`, or memory grows by
  tens of megabytes per window.
- Some save handlers write files into the working directory even when the
  dialog is cancelled. If stray `_*.txt` files appear in the repository
  root after a sweep, delete them; do not commit them.
- Synthetic data formats in `tests/synth.py` were reverse-engineered from
  the readers and then confirmed against the real NX school SPEC header.
  Pilatus 1M and per-point MCA files have no synthetic equivalent yet.
