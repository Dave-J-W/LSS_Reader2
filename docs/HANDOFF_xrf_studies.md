# Hand-off: the XRF studies (C65–C69), 2026-11-25 (written 15:25 CST, updated 16:30)

For this session after a pause or a context compaction, or for whoever takes the XRF work over. Read
`AGENTS.md` first. This page says where the work stands, what is next, and the traps that have already
cost time. Written at the owner's request ("pause and write a handoff"); the session paused 15:22–16:20 CST
on a timer and resumed on time.

## Who and where

- **The session:** a local session on the owner's PC (DJW-Ryzen9, Windows 10), working directly on
  `main` of `C:\Users\Dave\Documents\Claude LSS_Reader2\repo` and pushing to `origin main` when the owner
  says so. Commit identity: `Dave-J-W <248028152+Dave-J-W@users.noreply.github.com>` (already the repo's).
- **Python:** `C:\Users\Dave\.venvs\xrf\python.exe` (has PyQt5, PyMca, PyXRF, Larch, xraylib). Run with
  `PYTHONUTF8=1`. The default venv has no PyQt5.
- **The private bundle** is decrypted under `sample_data/private/` (git-ignored). Never commit anything
  under `sample_data/private/` or `sample_data/bu/`; never write the decryption key anywhere.

## What exists (all on `origin/main` up to 324ff84, pushed 2026-11-25)

| Id | Study | Where |
|---|---|---|
| C65 | XRF shootout on synthetic spectra: the reader's fits against PyMca, PyXRF, Larch, XeRay | `docs/studies/xrf_shootout/summary.md` §1–9 |
| C66 | The same on the owner's real blanks with synthetic lines | `summary.md` §10, `run_blanks*/` |
| C67 | Real lines in real scatter: the 19 private burn series (summary values only) | `summary.md` §11, `run_real/` |
| C68 | Scatter models against the real blanks: model twins and the floor | `docs/studies/xrf_models/README.md` part 1 |
| C69 | Real line shapes on both detectors, and their effect on the verdicts | `README.md` part 2; scatter at other beam energies in part 3 and `scatter_energy.md` |

These were C62–C66 in their own commit messages (57e802f…bcbbf61); main had meanwhile taken C62–C64 for
other work, and the merge 324ff84 renumbered ours (its message has the mapping).

## The walkthroughs (the owner: "upgrade the docs to make your findings better explained")

Committed together with this hand-off, after main's 13 commits of the pause were brought in:
- `tests/tools/xrf_walkthrough.py`: figures W1–W5 and `numbers.json` for each walkthrough
  (`--part shootout,models`, about a minute). The shootout part reuses the C66 run's own seeds and asserts
  that its bias equals the committed `run_blanks/scores.csv`.
- `docs/studies/xrf_shootout/walkthrough.md` and `walkthrough/`: blank E9.2-a → a test spectrum with a Ni K
  line → P1, P1+P3, P1+P2+P3 fits with residuals → 500 spectra → bias, pulls, the "accurate" rule →
  strengths and false signal → the scoreboard and the judgment.
- `docs/studies/xrf_models/walkthrough.md` and `walkthrough/`: three scatter models over E6.1-a with
  residuals → the misfit at use (1 + p (D/dof − 1), checked by 40 thinnings) → a twin and a second draw →
  the floor → a synthetic line with readout B's skew through the shape ladder → the noise-free P2 test.
- **A correction it found** (applied): the README said P2's 6 % loss with real-shaped lines is the part of
  the line outside a Gaussian. The calibration twin has the same shape and cancels that; on noise-free
  spectra P1+P2+P3 still reads −4.9 to −7.2 %. README 2c, the C69 row and physics_notes now say it is a
  systematic of the fixed width over real scatter.
- The models README gained a glossary and a pointer to the walkthrough; the shootout's `summary.md` and
  `README.md` link theirs; catalogue item `xrf_walkthrough` (TOOLS.md rendered);
  `tests/test_xrf_walkthrough.py` (4 tests, passing, mutation-checked: a changed number in either
  walkthrough fails them).

## Next, in order

1. **Before any new commit:** `git fetch origin` and `git rev-list --count HEAD..origin/main`; if main
   moved, merge it and check the ledgers for numbering clashes (`COMPARISONS.md`: our rows are C65–C69).
   The quick suite fails 7 known tests on this PC, on clean main too:
   `test_ngui::test_window_builds_with_every_placed_control`, `test_gui_menus::test_documentation_opens_the_scripting_guide`,
   `test_paths` ×2, `test_test_infrastructure::test_auto_workers_fit_the_cpus_and_the_memory`,
   `test_toolbox_gui` ×2.
2. **Ask the owner before pushing** (they said "Push" once, for the earlier commits only).
3. Still owed to the owner: **a polished PDF report** of the XRF work ("can wait until more work is done").
4. Proposed, not built: `tests/synthetic/mca_scatter_bank.py` (part 3's recommended scatter generator,
   about 1.5 days); a second draw for the generator and Gaussian twins (the floor is measured for the full
   model only).

## Traps that have already cost time

- **Quick suite:** run with `-n 4`, `PYTHONUNBUFFERED=1`, `OPENBLAS_NUM_THREADS=1`, in the background, with a
  Monitor waiting for the first `[ NN%]` line. More workers deadlock loading PyQt5 ("bringing up nodes"
  forever). About 6 minutes.
- **Intermittent Windows file errors** under load: "WinError 6 handle is invalid", "Errno 9 Bad file
  descriptor" on a plain `open`, and now xdist workers collecting different tests. Rerunning has always
  worked; the cause is unknown. Capture stderr of long runs to a file (not `/dev/null`) so a failure can be
  read.
- **Long shootout runs** (`xrf_blanks.py`): 45–80 minutes on 8–12 CPUs, 20 minutes on 28. A run that exits 1
  at once is the file error above: rerun it.
- **Line endings:** `COMPARISONS.md`, `physics_notes.md`, `SYNTHETIC_DATA.md` are CRLF: edit them as bytes.
  Most others are LF. Patch scripts go in the scratchpad and are written with the Write tool (bash heredocs
  turn `\n` inside Python strings into real newlines).
- **Privacy:** public text names no sample element, peak position, bundle file or run id, or the bundle's
  setup labels. The private tools read their file lists from the git-ignored
  `sample_data/private/xrf_models/probes.json`. Frame-by-frame curves of private burns are never published.
- **Comparison ids** are taken by whoever writes the next row; other sessions write `COMPARISONS.md` too.
