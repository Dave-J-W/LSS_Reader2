# Hand-off: the XRF studies (C65–C69), written 2026-11-25, updated 2026-11-27

For this session after a pause or a context compaction, or for whoever takes the XRF work over. Read
`AGENTS.md` first. This page says where the work stands, what is next, and the traps that have already
cost time. First written at the owner's request ("pause and write a handoff").

**Where it stands (2026-11-27):** Reader 2.0 is released; rules 12 and 13 stay paused. The XRF work is on
the backlog: `docs/RELEASE_PLAN.md`, "After 2.0", item "Refine the XRF shootout (C65–C69)", which holds the
pathology tool, the misfit finding and the Larch findings below. Nothing XRF is in progress.

## Who and where

- **The session:** a local session on the owner's PC (DJW-Ryzen9, Windows 10), working directly on
  `main` of `C:\Users\Dave\Documents\Claude LSS_Reader2\repo` and pushing to `origin main` when the owner
  says so. Commit identity: `Dave-J-W <248028152+Dave-J-W@users.noreply.github.com>` (already the repo's).
- **Python:** `C:\Users\Dave\.venvs\xrf\python.exe` (has PyQt5, PyMca, PyXRF, Larch, xraylib). Run with
  `PYTHONUTF8=1`. The default venv has no PyQt5.
- **The private bundle** is decrypted under `sample_data/private/` (git-ignored). Never commit anything
  under `sample_data/private/` or `sample_data/bu/`; never write the decryption key anywhere.

## What exists (all on `origin/main`)

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
- `docs/studies/xrf_shootout/walkthrough.md` and `walkthrough/`: the 9.2 keV blank a → a test spectrum with a Ni K
  line → *Poisson fit*, *Poisson fit + escapes removed*, *Poisson fit + fixed width + escapes removed* fits with residuals → 500 spectra → bias, pulls, the "accurate" rule →
  strengths and false signal → the scoreboard and the judgment.
- `docs/studies/xrf_models/walkthrough.md` and `walkthrough/`: three scatter models over 6.1 keV blank a with
  residuals → the misfit at use (1 + p × (misfit − 1), checked by 40 thinnings) → a twin and a second draw →
  the floor → a synthetic line with the 7-element detector's skew through the shape ladder → the noise-free test of the fixed width.
- **A correction it found** (applied): the README said the fixed width's 6 % loss with real-shaped lines is the part of
  the line outside a Gaussian. The calibration twin has the same shape and cancels that; on noise-free
  spectra *Poisson fit + fixed width + escapes removed* still reads −4.9 to −7.2 %. README 2c, the C69 row and physics_notes now say it is a
  systematic of the fixed width over real scatter.
- The models README gained a glossary and a pointer to the walkthrough; the shootout's `summary.md` and
  `README.md` link theirs; catalogue item `xrf_walkthrough` (TOOLS.md rendered);
  `tests/test_xrf_walkthrough.py` (passing, mutation-checked: a changed number in either
  walkthrough fails them).

## Since then (2026-11-25 to 27)

- **Plain names, not codes** (the owner: "rename things with names like 'P1' and 'p1 + p2' and anything
  else written in cryptic fashion"). The figures, tables and docs say *Poisson fit*, *+ escapes removed*,
  *+ fixed width* (F90's P1, P3, P2), single-element and 7-element detector (not readout A/B), "9.2 keV blank
  a" (not E9.2-a), and conditions in words. One label table in `tests/tools/xrf_shootout_figures.py` (`SHORT`,
  `LABEL`, `READOUT`, `blank_name`, `cond_name`, `SERIES`) feeds all three figure tools. Two tests in
  `tests/test_xrf_walkthrough.py` fail if a code comes back. The run files keep their ids.
- **F110 changed the reader's default** (2026-11-26, the owner): Fit lines is now this study's *Poisson fit +
  escapes removed*, with the width from the series' sum. The studies describe the default when they ran (the
  *Poisson fit* alone); each document says so in one line, and the labels no longer call it "the default".
- **Larch was given the beam in eV, not keV** (found 2026-11-26). `xrf_shootout._larch_model` passes
  `1000 × energy`; Larch's model takes keV, so it models lines the beam cannot excite. The committed Larch
  scores are wrong wherever an edge sits above the beam (Lu L +7900 %, As beside Pb −680 %). The summary, the
  C65 row and the release plan say so. The fix also needs data-based starting amplitudes, and even then
  Larch's scatter model cannot follow water's Compton: the release plan's entry has the numbers. Not fixed
  in the committed run (no rerun before the owner resumes the XRF work).
- **Parked on the owner's PC, not in the repository:** `C:\Users\Dave\Documents\Claude LSS_Reader2\parked\xrf_pathologies\`
  (beside the clone). The figures of the shootout's bad fits (XeRay winning and failing, six other methods),
  the misfit test on all 39 100 spectra, and `larch_tune.py` (the Larch variants). Its `README.txt` says how
  to run each. The owner wants it as "a proper tool later".

## Next, when the owner resumes the XRF work

1. **Before any commit:** `git fetch origin`, merge `origin/main`, and check the ledgers for numbering clashes
   (`COMPARISONS.md`: our rows are C65–C69). Then `python -m lss_toolbox --stale`.
2. **Push only when the owner says so.**
3. The release plan's "Refine the XRF shootout" item: tune each library (Larch first: the units fix, start
   amplitudes, a scatter model that fits), rerun the shootout, then turn the parked pathology scripts into
   one tool in `tests/tools/` with a catalogue item and a page.
4. Still owed to the owner: **a polished PDF report** of the XRF work ("can wait until more work is done").
5. Proposed, not built: `tests/synthetic/mca_scatter_bank.py` (part 3's recommended scatter generator,
   about 1.5 days); a second draw for the generator and Gaussian twins (the floor is measured for the full
   model only).

## Traps that have already cost time

- **Quick suite:** run with `-n 4`, `PYTHONUNBUFFERED=1`, `OPENBLAS_NUM_THREADS=1`, in the background. More
  workers deadlock loading PyQt5 ("bringing up nodes" forever). About 6 minutes, 1449 passed (2026-11-27).
  Three tests fail on this PC on clean `origin/main` too: `test_ngui::test_window_builds_with_every_placed_control`,
  `test_toolbox_gui::test_a_figure_tool_reproduces_its_committed_figures[burn_figures]`,
  `test_plot_fonts::test_the_window_sizes_plot_text_from_the_tabs` (a font size: 12.96 expected).
- **The Tools audit** (`python -m lss_toolbox --audit --only <items> --record`) runs an item into a fresh
  folder and compares by file name. A tool must therefore read its inputs from the study folder, not from its
  output folder, and `committed_with` holds settings, never output paths. The two walkthroughs are two items
  (`xrf_walkthrough`, `xrf_walkthrough_models`), because both write a `numbers.json`.
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
