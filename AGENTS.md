# Working on LSS_Reader2 (for coding agents and new contributors)

LSS_Reader ("reader") is a PyQt5 desktop program that parses a SPEC file,
loads the raw detector data beside it, and reduces it (monitor
normalisation with Poisson error propagation) for liquid-surface X-ray
scattering at ChemMatCARS. It is not a fitting program. Read
`docs/PROJECT_CONTEXT.md` first.

## Current phase — read before changing anything

**Implementation, following `docs/SCOPE.md` stage by stage** (authorised by
the owner on 2026-11-17). Stages 0–2 are done (2026-11-18); Stage 3 (series,
the per-SPEC workbook, automatic saving, live updates) is largely built
(2026-11-19 to 22); in Stage 6, GID patching and fitting (peaks, burn
trends) are built. `docs/ACCOMPLISHMENTS.md` summarises what exists; the
top of `docs/TODO.md` says what is in progress and holds the working list
by area; if it disagrees with this paragraph, that file wins.

Application code may now be changed, under these conditions:
- one defect or one feature per commit, with its test in the same commit;
- the quick checks pass before every commit; the real-data checks and the
  crash sweep pass before a stage is called done;
- the legacy export fixtures stay byte-identical (rule 3 below).

## Where to commit (D60, 2026-11-23) — read before your first commit

- **`main` of `github.com/Dave-J-W/LSS_Reader2` is the master**: the one
  place the project lives. Every finished piece of work ends up there. Its
  history restarts on 2026-11-20; a clone older than that shares no history
  with it and must be made again. `chemmatcars/LSS_Reader` is the original
  this fork came from: never push there.
- **Start from it**: `git fetch origin && git log -1 --oneline origin/main`,
  and work on top of that commit.
- **A session that can push to `main`** commits there, small and often
  (rule 8).
- **A session that may push only to its own branch** (cloud sessions get a
  `claude/<name>` branch, and GitHub refuses their pushes elsewhere): before
  every push, `git fetch origin main && git merge origin/main`, so that the
  branch always contains `main` and `main` can be fast-forwarded to it; its
  report to the owner ends with the commands below. Once `main` contains
  the branch, the branch is deleted.

      git fetch origin
      git checkout main
      git pull --ff-only
      git merge --ff-only origin/claude/<name>
      git push origin main
      git push origin --delete claude/<name>

  `--ff-only` refuses instead of making a merge when `main` has moved on;
  the session then merges `main` in again and the owner repeats the merge.
  A session the owner has given standing permission (so far the GUI-planning
  session, the test-speed session and the Tools-menu session, 2026-11-23) brings its own branch into `main` itself once the
  quick suite passes: a cloud session cannot move `main` directly (HTTP
  403), so it opens a pull request from its branch and merges it at once
  with "Create a merge commit" (owner's choice, 2026-11-23), then merges
  `main` back into its branch. Those pull requests are records, never left
  open.
  **Or, by button**: if the branch has a pull request into `main` (it
  shows the branch's latest state and updates with every push), merging it
  with **"Create a merge commit"** does the same. Never "Squash and merge"
  or "Rebase and merge": both give `main` different commits from the
  branch, and squashing also loses the one-change-per-commit history
  (rule: one defect or feature per commit). A session keeps its pull
  request's title and description up to date when it pushes something the
  description does not cover. No GitHub workflow tests pull requests (the
  build runs on version tags only), so the description says which suites
  the session ran and their results.
- **No other branches** (no `wip/`, no personal ones): work that is not
  ready stays uncommitted or in the session's own branch.

## Sessions (D62, owner, 2026-11-23)

Several Claude sessions work on this repository at once. **main man**
(called Main until 2026-11-24, when the owner renamed it to tell it
apart; the session that was "test speed") orchestrates: it hands out work
and the others report to it. **questor** asks the owner questions and
records the answers in `docs/`, and takes small fetch and edit tasks.
**tools man** (the Tools-menu session) is general purpose. **GUI manager**
works on workflows and the interface. **Local yokel** runs on the owner's
own computer and fetches the private data sets (`docs/DATA_NEEDS.md`),
with helper sessions of its own. **All sessions talk through GitHub
issues** (owner, 2026-11-24): issue #55 of this repository, one comment
per message, beginning `sender → recipient:`, with no private data (the
issue's body has the rules). Direct session messages are not used: most
directions are refused, between cloud sessions and the owner's computer
and into a session the owner has approved for their trusted devices
(main man's is). main man watches the issues and new `claude/local-data-*`
pull requests every minute, and reviews and merges the local data agent's
pull requests (it does not merge them itself). Standing rule (owner,
2026-11-24): main man merges such a pull request once it passes main man's
privacy review and the quick suite in the cloud, and asks the owner only
when something private or doubtful shows up; questor reads the issue
when the owner starts a turn with it. GUI priorities: the main window first, then
the sample timeline tab (F83), then the new layout prototype (`ngui/`);
ideas proven in ngui are carried into the main window, not built twice.
A session that wants to change a large part of `mainwindow.py`,
`tests/conftest.py` or `tests/sweep.py` tells main man first, so that two
sessions do not edit the same lines.

## Where things are

| Path | What it is |
|---|---|
| `docs/PROJECT_CONTEXT.md` | What the program is for, in the owner's words |
| `docs/ACCOMPLISHMENTS.md` | What has been built so far, by stage and area, with pointers |
| `docs/ASSESSMENT.md` | Structure, physics to preserve, numbered defects, Python 3 audit |
| `docs/FEATURE_REQUESTS.md` | Requirements R1–R4 and requests F1…; add new ones here with the date |
| `docs/SCOPE.md` | The plan: target structure and stages, with every request placed |
| `docs/PHYSICS_ISSUES.md` | Numbered list of physics and mathematics issues, with sizes and how each is known |
| `docs/TODO.md` | What to do next, what is waiting on the owner, what is done |
| `docs/HANDOFF_main_man.md`, `docs/gui/HANDOFF_gui_manager.md` | Hand-offs: how the orchestrator and the GUI manager work, what is open, who is on what |
| `.claude/skills/` | Project skills: `merge-to-main` (D60, step by step), `review-local-data-pr` (privacy review and merge of the local data agent's pull requests), `issue-watch` (the #55 watch and how to post) |
| `docs/DATA_NEEDS.md` | Every dataset a work item waits for, what it must answer, where it goes, who supplies it (the owner's non-cloud agent for large private sets) |
| `docs/TESTING.md` | How the test suite works and how to extend it |
| `docs/physics_notes.md` | Invariants table and a dated question-and-answer log |
| `docs/timings.md` | Timing baseline written by `pytest -m bench` |
| `docs/COMPARISONS.md` | Ledger of old-vs-new method comparisons: data, result, evidence, how to regenerate (for the figure agent) |
| `docs/comparisons_data/` | Old/new outputs as CSV for figures, from `tests/tools/compare_methods.py` (public data only; maps git-ignored) |
| `docs/OUTPUT_DECISIONS.md` | Every default and decision that changes output numbers, with rationale and evidence |
| `docs/gui/` | GUI overhaul (R4, D58): plan and schema (`README.md`), control inventory, **workflow map** (`workflows.yaml`, checked and rendered by `tests/tools/gui_map.py`), assessment, image-display requirements, questions for the owner, screenshots (`tests/tools/gui_screens.py`) |
| `docs/MANUAL_NOTES.md`, `docs/manual/` | Breadcrumbs for the future manual; `controls.md` is generated by `tests/tools/dump_tooltips.py` |
| `docs/handoff/` | Specifications handed over by the owner (xmodfit export contract). They are requirements; do not edit them |
| `docs/handoff_out/` | Requests written by this project for analyses done elsewhere (e.g. monitor noise from the owner's larger data) |
| `lss_core/` | GUI-free core: readers, cache, reduction, scripting API (`docs/SCRIPTING.md`) |
| `reader_log.py` | Durable log, per-SPEC log, process-wide exception handler (no Qt needed) |
| `packaging/`, `docs/PACKAGING.md` | PyInstaller recipe, pinned build libraries, the GitHub build workflow (`.github/workflows/build.yml`) |
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
| `sample_data/private/` | The owner's private files (GID, XFNTR, macros): git-ignored. Owner, 2026-11-19: a few derived numbers in docs are acceptable, but **never peak locations, raw data or images**; private figures stay under this folder. Owner, 2026-11-24: **sample-height scans from the ROI are unrestricted data** (their ROI counter, monitor and sh columns, and what is derived from them, may be published; their images may not). Owner, 2026-11-25: **frame-by-frame curves of private burns are not published**, even normalised and anonymised (summary values such as rates and verdicts are), but how to make them is kept: the generator and the figure stay under this folder, and the public study says where and how to regenerate them. Owner, 2026-11-25: **data from before 2019 are released for figures** (first "before 2017", moved to 2019 the same day): reduced curves with their errors, fits and detector images of runs before 2019 may be published, and small CSVs of the plotted points may be committed so that the figures regenerate from public data; such runs stay anonymous (energy and an index, "before 2019" and no finer date, no PI, group, file name or scan number). The release covers **reflectivity** frames and ROI boxes only, and only what a figure needs (a few representative frames, not whole series; the smallest CSVs that regenerate it); **GID images stay restricted** even before 2019 unless the owner releases them. The owner's reason, to judge new cases by how much sample information they carry: "a GID image has a lot of information in it, thus they need to be restricted more. a reflectivity image has almost no information in it. A reflectivity image series or ROI-reduction hints at a layer system but is not nearly as specific as a GID image." Newer private data keep every rule above |

## Commands

    pip install -r requirements-dev.txt   # a fresh cloud session lacks PyQt5 etc.: ~10 s
    pytest                 # fast suite, ~5 min (1176 tests, 2026-11-24); run before every commit
    pytest -m slow         # real-data regressions, ~4 min
    pytest -m bench -s     # rewrites docs/timings.md
    pytest -m sweep        # crash inventory, ~9 min (forked copies, 2026-11-24): start it in the background; run after GUI-facing changes
    python -m lss_toolbox  # the Tools window on its own; --render rewrites docs/TOOLS.md, --stale, --audit

No display is needed. Run from the repository root. Every suite runs in
parallel by itself (pytest-xdist: one worker per CPU, as memory allows)
and cleans up after itself: run the quick and real-data suites in the
foreground, and do not shard or tidy up by hand (`docs/TESTING.md`, "Parallel by default").
`-n0` runs in one process, for a debugger.

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
   that. A session that may push only to its own branch follows "Where to
   commit" above. Do not open pull requests unless asked.
9. **Explain in tooltips, not on screen** (owner, 2026-11-18). Labels,
   group titles and messages in the window stay short; the why, the
   provenance of numbers and the caveats go in tooltips. Prefer this to
   wordy displays.
10. **Work in larger tranches, then test** (owner, 2026-11-18): write a
   whole feature (code, tests, docs) before running the suite, rather than
   running tests after each small edit.
11. **Leave a trail for the figure agent and the manual writer** (owner,
   2026-11-19), in the same commit as the change. The main session builds
   knowledge into the reader and records its provenance; polished figures
   are for the figure agent or a subagent (owner, 2026-11-18):
   - a new or changed method: a row in `docs/COMPARISONS.md` (old vs new,
     data, result, evidence kind, how to regenerate; save old/new arrays as
     CSV for public data when you measure them);
   - any choice that changes an output number, however small: a row in
     `docs/OUTPUT_DECISIONS.md` with its rationale and evidence (owner,
     test, measurement, literature, or marked as an assumption);
   - a user-visible control: a tooltip (rule 9), a line in
     `docs/MANUAL_NOTES.md`, `python tests/tools/dump_tooltips.py >
     docs/manual/controls.md`, and an entry in the GUI inventory
     (`docs/gui/inventory/<area>.yaml`; its id in the workflow step that
     uses it, `docs/gui/workflows.yaml`). `tests/test_gui_map.py` fails
     on a named control the inventory lacks (2026-11-23).
   - figures that a change makes stale (they show the old method or old
     numbers): regenerate them, public ones in the repository and private
     ones under `sample_data/private/figures/`, in the same tranche (owner,
     2026-11-20). Every figure is made by a tool in `tests/tools/`, so this
     is a rerun, not a redraw: `python -m lss_toolbox --stale` lists the
     candidates (from the verified record, else from git history),
     `--audit` reruns them and compares pixel for pixel (`--record` keeps
     the ones that matched, so that `--stale` calls them current until
     something they used changes), and the Tools window's "Replace the
     committed products" reruns one into the repository.
   - a new figure generator or demonstration: an item in
     `lss_toolbox/catalog.py` with the variations the documents describe
     (a "change this and regenerate to see that" sentence becomes a
     variation citing its passage as `path#text`, a heading or a short
     quote, never a line number), then `python -m lss_toolbox
     --render`. `tests/test_toolbox.py` fails on a script in `tests/tools/`
     that is not an item, on a variation naming an option its script lacks,
     and on a committed figure no item claims (2026-11-23, F84).

12. **The best method becomes the default** (owner, 2026-11-24): "make the best method the default
   if it has been comprehensively demonstrated and tested and has a demonstrator presentation effort
   behind it". So, before a default changes:
   - a study with known truth and figures (a COMPARISONS row);
   - tests that pin the new numbers;
   - a demonstrator: a document and a Tools menu item, `docs/studies/` or `docs/reports/`.
   Then make the switch, with its OUTPUT_DECISIONS row and the re-pins named one by one. Committed
   products of earlier studies keep the default they were run at (they set it for their own run).

13. **Show the whole chain, explained simply** (owner, 2026-11-25, a standing order: "I always need to
   see the entire chain of data processing, ending with the statistics and judgment. That means data
   fit examples, explanations of statistics, all ELI5"). Every study, report or answer that ends in a
   number or a verdict shows, in order:
   - the raw data, as it comes in (a frame, a scan, the counts, with their errors);
   - each processing step, on one real example where the data are public (synthetic otherwise),
     with what it does to the numbers;
   - at least one fit drawn over its data, with its residuals and what the fitted numbers mean;
   - every statistic used, explained as for a newcomer: what it measures, how it is computed here,
     what a good and a bad value look like (χ², p-values, intervals, likelihood, pulls, coverage);
   - the judgment, and how sure it is, in plain words.
   Each figure comes from a tool in `tests/tools/` (rule 11). A walkthrough document beside the study
   (`docs/studies/<topic>/walkthrough.md`) is the usual form; `.claude/skills/known-truth-study`
   says how.

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
