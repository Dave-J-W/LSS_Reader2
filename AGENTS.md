# Working on LSS_Reader2 (for coding agents and new contributors)

LSS_Reader ("reader") is a PyQt5 desktop program that parses a SPEC file, loads the raw detector data beside
it, and reduces it (monitor normalisation with Poisson error propagation) for liquid-surface X-ray scattering
at ChemMatCARS. It is not a fitting program. Read `docs/PROJECT_CONTEXT.md` first.

This file holds the rules in force. Their history is in git (`git log -p AGENTS.md`).

## Current phase

**Reader 2.0 is released** (tag `v2.0.0`, release "Reader 2", 2026-11-27; builds attached). The work list is
the **GitHub issues labelled `task`** (rule 15). Those labelled `parked` are the after-2.0 backlog and are not
worked on until unparked. **Rules 12 and 13 are paused** (owner, 2026-11-27): their full text is in
`docs/rules_paused.md`. A fix for 2.0 users goes on `main` like any other change; a 2.0.x tag is the
owner's to set. Application code may be changed under the rules below. In short: one defect or feature per
commit with its test, CI green, the legacy export fixtures byte-identical.

## Where to commit

- **`main` of `github.com/Dave-J-W/LSS_Reader2` is the master.** Every finished piece of work ends up there.
  Never push to `chemmatcars/LSS_Reader` (the original this fork came from). Start from
  `git fetch origin && git log -1 --oneline origin/main`.
- **A session that can push to `main`** commits there, small and often (rule 8).
- **A cloud session** (it may push only to its own `claude/<name>` branch) merges `origin/main` into its
  branch before every push. It brings the branch into `main` by a pull request merged with **"Create a merge
  commit"**, never squash or rebase (the `merge-to-main` skill gives the steps). It merges at once, **once
  CI is green on the head it merges**. Sessions with standing permission (GUI manager, main man, tools man)
  merge their own. The pull requests are records, never left open. Afterwards the branch is brought level
  with `main`.
- **No other branches** (no `wip/`, no personal ones).

## Sessions and coordination

- **main man** orchestrates, reviews and merges. **GUI manager** works on the window and workflows.
  **tools man** is general purpose (Tools menu, packaging). **questor** asks the owner questions and records
  the answers. **Manual writing** writes the user manual (`docs/manual/`). The **data sessions on the owner's PC** fetch
  the private data (`docs/DATA_NEEDS.md`) and open `claude/local-data-*` pull requests. Local yokel, which
  relayed for them, was archived on 2026-11-27, so their tasks carry `lane:local-data`. **Reflection guy** also runs on the
  owner's PC, and its rulings on public data carry the owner's authority ("Whatever I tell reflection guy is
  law in regards to public data", owner 2026-11-26). They reach the cloud sessions only through #55 or `docs/`.
- **Tasks are GitHub issues** (rule 15). **Issue #55 is for short notices** between sessions: one comment per
  message, beginning `sender → recipient:`, no private data (its body has the rules). Keep a notice to a few
  lines and link the issue, commit or file instead of retelling it.
- **Two watchers, one per side** (owner, 2026-11-27; the `issue-watch` skill). **main man** watches all issues
  and pull requests, privacy-reviews the data sessions' pull requests, and merges them once CI is green. It
  asks the owner only when something private or doubtful shows up (owner, 2026-11-24). **One data session on
  the owner's PC** runs the lane watch (`--label lane:local-data --branch-prefix claude/local-data-`), so a
  task for the PC wakes it without anyone opening a session. No other session keeps a watch: they read their
  lane's issues when a turn starts.
- GUI priorities: the main window first, then the timeline tab (F83), then the `ngui/` prototype. Ideas proven
  in ngui are carried into the main window, not built twice.
- Before changing a large part of `mainwindow.py`, `tests/conftest.py` or `tests/sweep.py`, say so on the
  task's issue or on #55, so that two sessions don't edit the same lines.

## Where things are

| Path | What it is |
|---|---|
| `docs/PROJECT_CONTEXT.md` | What the program is for, in the owner's words |
| `docs/ACCOMPLISHMENTS.md` | What has been built so far, by stage and area, with pointers |
| `docs/ASSESSMENT.md` | Structure, physics to preserve, numbered defects, Python 3 audit |
| `docs/FEATURE_REQUESTS.md` | Requirements R1–R4 and requests F1…; add new ones here with the date |
| `docs/SCOPE.md` | The plan: target structure and stages, with every request placed |
| `docs/PHYSICS_ISSUES.md` | Numbered list of physics and mathematics issues, with sizes and how each is known |
| GitHub issues labelled `task` | **The work list** (rule 15): one issue per task, claimed by label |
| `docs/TODO.md` | The older working list by area (frozen 2026-11-27; reference only, new work goes in issues) |
| `docs/HANDOFF_main_man.md`, `docs/gui/HANDOFF_gui_manager.md` | Hand-offs: how the orchestrator and the GUI manager work, what is open, who is on what |
| `.claude/skills/` | Project skills: `merge-to-main`, `review-local-data-pr` (privacy review), `issue-watch` (#55), `tools-freshness` (generated files, at release), `fit-statistics-pitfalls`; `known-truth-study` is paused with rule 12 |
| `docs/DATA_NEEDS.md` | Every dataset a work item waits for, what it must answer, where it goes, who supplies it (the owner's non-cloud agent for large private sets) |
| `docs/TESTING.md` | How the test suite works and how to extend it |
| `docs/physics_notes.md` | The invariants table (live) and the Q&A log up to 2026-11-27 (frozen) |
| `docs/notes/` | New notes, one file per entry (rule 5); template in its `README.md` |
| `docs/rules_paused.md` | The full text of paused rules 12 and 13 |
| `docs/timings.md` | Timing baseline written by `pytest -m bench` |
| `docs/COMPARISONS.md` | Ledger of old-vs-new method comparisons: data, result, evidence, how to regenerate |
| `docs/comparisons_data/` | Old/new outputs as CSV for figures, from `tests/tools/compare_methods.py` (public data only; maps git-ignored) |
| `docs/OUTPUT_DECISIONS.md` | Every default and decision that changes output numbers, with rationale and evidence |
| `docs/gui/` | GUI overhaul (R4, D58): plan and schema (`README.md`), control inventory, **workflow map** (`workflows.yaml`, checked and rendered by `tests/tools/gui_map.py`), assessment, image-display requirements, questions for the owner, screenshots (`tests/tools/gui_screens.py`) |
| `docs/MANUAL_NOTES.md`, `docs/manual/` | Breadcrumbs for the manual, and the manual itself (the Manual writing session); `controls.md` is generated by `tests/tools/dump_tooltips.py` |
| `docs/handoff/` | Specifications handed over by the owner (xmodfit export contract). They are requirements; do not edit them |
| `docs/handoff_out/` | Requests written by this project for analyses done elsewhere (e.g. monitor noise from the owner's larger data) |
| `lss_core/` | GUI-free core: readers, cache, reduction, scripting API (`docs/SCRIPTING.md`) |
| `reader_log.py` | Durable log, per-SPEC log, process-wide exception handler (no Qt needed) |
| `packaging/`, `docs/PACKAGING.md` | PyInstaller recipe, pinned build libraries, the build workflow (`.github/workflows/build.yml`, on version tags) |
| `.github/workflows/tests.yml` | CI: the quick suite on every pull request into `main` and every push to `main` (rule 14) |
| `.github/workflows/nightly.yml` | The slow suite and the crash sweep on `main` every night; a failure opens a `nightly` issue (rule 14) |
| `lss_core/preferences.py` | Preferences kept between sessions (`$LSS_READER_PREFS`; the tests use a temporary file) |
| `lss_core/series.py`, `timing.py` | Scan series (lines and guesses) and per-point times |
| `lss_core/workbook.py`, `live.py` | The per-SPEC Excel workbook (saved results, series ties, stale flags); remaking results from their recipes (live updates) |
| `lss_core/peaks.py`, `trends.py`, `burn.py` | Peak finding and fitting; trends over time; burn tests |
| `lss_core/patching.py`, `uncertainty.py` | Reflectivity patching by joint fit (the default since 2026-11-22; the legacy `stitching.py` stays a preference); covariances of chained scale factors and stitched data |
| `lss_core/pinhole.py`, `gid.py` | Pinhole GID geometry, responses, joins, distance calibration; the GID patch |
| `tests/` | The suite; `synth.py` (synthetic data), `sweep.py` (GUI driver) |
| `lss_toolbox/`, `docs/TOOLS.md` | The Tools collection (F84): every demonstration and figure generator of `tests/tools/` as an item of the reader's Tools menu and of its own window (`python -m lss_toolbox`); the catalogue (`catalog.py`) with the documented variations; staleness of committed products (`--stale`: the verified record `verified.json`, else git with prose-only changes ignored) and the audit (`--audit`: rerun and compare pixel for pixel, `docs/reports/tools_audit.md`; `--record` keeps what matched). `TOOLS.md` is generated (`--render`) |
| `docs/SYNTHETIC_DATA.md`, `tests/synthetic/` | Catalogue of every synthetic-data generator, how to use them (known truth for reflectivity, GID, burn, XFNTR, live files), unmet needs |
| `sample_data/NX_school/` | Real, public data set (committed) |
| `sample_data/bu/` | Real, private data set: git-ignored, never commit or push it |
| `sample_data/private/` | The owner's private files (GID, XFNTR, macros): git-ignored. Owner, 2026-11-19: a few derived numbers in docs are acceptable, but **never peak locations, raw data or images**; private figures stay under this folder. Owner, 2026-11-24: **sample-height scans from the ROI are unrestricted data** (their ROI counter, monitor and sh columns, and what is derived from them, may be published; their images may not). Owner, 2026-11-25: **frame-by-frame curves of private burns are not published**, even normalised and anonymised (summary values such as rates and verdicts are), but how to make them is kept: the generator and the figure stay under this folder, and the public study says where and how to regenerate them |

## Commands

    pip install -r requirements-dev.txt   # a fresh cloud session lacks PyQt5 etc.: ~10 s
    pytest tests/test_<area>.py   # what you changed: run this locally (rule 14)
    pytest                 # quick suite, ~5 min; CI runs it on every pull request and push to main
    pytest -m slow         # real-data regressions, ~4 min: when real-data reduction or a dialog's input changed
    pytest -m sweep        # crash inventory, ~9 min, in the background: when the window changed
    pytest -m release      # generated docs, inventories and committed figures are current (rule 11): before a release
    pytest -m bench -s     # rewrites docs/timings.md
    python -m lss_toolbox  # the Tools window on its own; --render rewrites docs/TOOLS.md, --stale, --audit

No display is needed. Run from the repository root. Suites run in parallel by themselves (pytest-xdist) and
clean up after themselves; `-n0` runs in one process, for a debugger. On the owner's Windows PC use `-n 4`.

## Rules of the house

1. **Never weaken a test to make it pass.** A changed number is either a bug you introduced or a deliberate
   change; if deliberate, say so in the commit and give before and after values in its `OUTPUT_DECISIONS` row.
2. **Three kinds of assertion** (`docs/TESTING.md`): invariants (never change), "as coded" characterisations
   (change only deliberately), and `xfail(strict=True)` for behaviour we want but do not have. When you fix a
   defect, remove its `xfail` marker in the same commit.
3. **The legacy export fixtures never change** (`tests/reference/legacy_export/`), except for the one fix the
   hand-off permits (Qz², trap T8). They prove that a refactor did not change the reduction.
4. **The crash baselines only shrink.** `tests/known_crashes.json` and `tests/known_crash_sites.json` are
   regenerated with `LSS_UPDATE_CRASHES=1 pytest -m sweep`, never edited by hand. A regenerated file may not
   gain entries unless the commit explains why.
5. **Record what you learn, one note per file.** A question from the owner and its answer, or a finding, go
   in a new file in `docs/notes/` (`YYYY-MM-DD-<topic>.md`, the template is in its README). Say how it is
   known: test, run, or reading only. Never append to another note, nor to the frozen log in
   `docs/physics_notes.md`. A conserved quantity goes in the invariants table at the top of
   `docs/physics_notes.md`, with the test that checks it.
6. **Say what was measured and what was only read.**
7. **The reader never writes to the SPEC file**, and tests never write into `sample_data/`. Set
   `window.directory = str(tmp_path)` after opening a SPEC file (the `window`/`loaded` fixtures show how).
8. **Commit small and push often** to `main` (or your branch, "Where to commit"). Open a pull request only to
   merge a branch, or when asked.
9. **Explain in tooltips, not on screen** (owner, 2026-11-18). Labels, group titles and messages stay short;
   the why, the provenance of numbers and the caveats go in tooltips.
10. **Work in larger tranches, then test** (owner, 2026-11-18): write a whole feature (code, tests, docs)
    before running tests, rather than after each small edit.
11. **Leave a short trail, not bookkeeping** (owner, 2026-11-27). In the same commit as the change, write
    down what only its author knows:
    - a choice that changes an output number, however small: a row in `docs/OUTPUT_DECISIONS.md` with its
      rationale and evidence (owner, test, measurement, literature, or marked as an assumption);
    - a user-visible control: a tooltip (rule 9) and a line in `docs/MANUAL_NOTES.md` (what it does, when
      to use it, the caveat), for the Manual writing session;
    - a new or changed method: a row in `docs/COMPARISONS.md` (old vs new, data, result, evidence, how to
      regenerate);
    - a new script in `tests/tools/`: its item in `lss_toolbox/catalog.py` (the quick suite checks this).

    **Don't regenerate derived files per commit, and make no bookkeeping-only commits.** That covers
    `docs/manual/controls.md`, `docs/TOOLS.md`, `docs/gui/inventory*` and `workflows.md`, screenshots,
    committed figures and data products, and `lss_toolbox/verified.json`. They are brought up to date **before
    a release, or when someone asks** (the Manual writing session, the owner), with
    `python tests/tools/dump_tooltips.py > docs/manual/controls.md`, `python tests/tools/gui_map.py`,
    `python -m lss_toolbox --render` and `--stale` / `--audit`. Then `pytest -m release` checks them. A new
    control may go without its inventory entry until then. Don't regenerate a file just because a merge of
    `main` touched it.
12. *(Paused, `docs/rules_paused.md`.)* The best method becomes the default, after a study, tests and a
    demonstrator.
13. *(Paused, `docs/rules_paused.md`.)* Show the whole chain of data processing, explained simply.
14. **Run the suites once** (owner, 2026-11-27). **CI's run is the check of record**
    (`.github/workflows/tests.yml`: the quick suite on every pull request into `main` and every push to
    `main`, with newer pushes cancelling older runs).
    - **Locally, run only the tests for what you changed** (`pytest tests/test_<area>.py`). Don't run the
      whole quick suite yourself before a push; CI does.
    - **Merge only when CI is green on the head you merge.** A reviewer reads CI's result and doesn't rerun.
      If CI fails, fix it and push; the new push gets its own run.
    - **On the owner's Windows PC,** the quick suite has environment failures (display scaling, fonts), so a
      local run there is never the check.
    - **Slow and sweep suites run nightly on GitHub** (`.github/workflows/nightly.yml`, on `main`). A failure
      opens or updates one issue labelled `nightly`. Don't run them yourself as a routine. Run
      `-m slow -k <area>` only when you need the answer before merging (a change to real-data reduction or to
      what a dialog accepts), and say `slow: N passed on <sha>` in the pull request. Before a release, start
      the nightly workflow by hand with "release" ticked, which adds `pytest -m release`.
15. **Tasks are GitHub issues** (owner, 2026-11-27). One issue per task, labelled `task`.
    - **Claim:** add `claimed` and your lane label (`lane:main-man`, `lane:gui`, `lane:tools`,
      `lane:questor`, `lane:local-data`, `lane:manual`), and comment "claimed by <session>". All sessions
      share one GitHub account, so assignees can't tell them apart. Don't take an issue that is already
      `claimed`.
    - **Report on the task's own issue**, briefly, not on #55. **Close** it with the commit or pull request
      that finished it.
    - `parked` = backlog, not worked on until unparked. `waiting-on-owner` = blocked on the owner (questor
      asks).
    - New work you find: open an issue for it rather than adding to `docs/TODO.md` (frozen) or a hand-off.
      Hand-off files hold only how a session works, not its task list.

## Things that will bite you

- The program loads `.ui` files and icons relative to the working
  directory. `tests/conftest.py` changes to the repository root; anything
  run outside pytest must do the same.
- PyQt5 **aborts the process** when a slot raises, unless `sys.excepthook`
  is replaced. The real program replaces it in `LSS_Reader.create_app`
  (log and carry on). In tests the `recorder` fixture replaces it and
  collects the exceptions; always assert `recorder.exceptions == []` in
  GUI tests, because a logged-and-survived exception is still a bug.
- Messages to the user go through `MainWindow.notify` (Messages pane and
  log, never a blocking dialog); `recorder.messages` records them. The
  remaining dialogs (file choosers, secondary windows) are modal; the
  `recorder` fixture makes them return at once. Never create a
  `MainWindow` in a test without it.
- Logs: the tests set `LSS_READER_LOG_DIR` to a temporary folder so that
  nothing is written beside sample SPEC files. Do not unset it globally.
- Selecting list rows one at a time fires the selection handler once per
  row, and the image handler re-reads every selected frame each time. Use
  `sweep._select_scans` / `sweep._select_images`, which select as one action.
- Windows are heavy (several matplotlib canvases plus images, about
  110 MB with data). `close()` + `deleteLater()` does not delete one in a
  test (no event loop runs); `conftest.free_windows` does, and runs by
  itself after every test that used Qt. Inside a loop of one test, free
  them with `sweep.dispose(window, qapp, recorder)`.
- Tests run in parallel, in separate processes and in any order: write
  only under `tmp_path`, never to fixed paths, and do not depend on what
  another test left behind.
- Some save handlers write files into the working directory even when the
  dialog is cancelled. If stray `_*.txt` files appear in the repository
  root after a sweep, delete them; do not commit them.
- Synthetic data formats in `tests/synth.py` were reverse-engineered from
  the readers and then confirmed against the real NX school SPEC header.
  Pilatus 1M and per-point MCA files have no synthetic equivalent yet.
