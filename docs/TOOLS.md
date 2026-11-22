# Tools: demonstrations, figure and data generators, checks

Every program in the repository that demonstrates a method, makes a
committed figure or data file, or checks something, in one table (owner,
2026-11-22: "all be accessible from reader's GUI, under the 'tools' menu.
But make sure they are generated without stale into the repo as well,
since they are an integral part of the documentation").

- The list itself is code: `lss_tools/registry.py` (one `Tool` per program,
  one `Job` per documented run whose outputs are committed). The reader's
  **Tools** menu, this table, `python -m lss_tools.regenerate` and the
  freshness test all read it. A new tool gets an entry there
  (`tests/test_tools_registry.py` fails for a script in `tests/tools/`
  that has none).
- The programs stay where they are documented (`tests/tools/`,
  `tests/demonstrator/`): every command in the docs still works. Why they
  were not moved into a package: `docs/PACKAGING.md`.

## In the reader: the Tools menu

Four submenus: Demonstrations, Figures, Data and surveys, Checks.

- **Demonstrations** open their window inside the reader (the fit
  demonstrator, `demonstrator.window.open_demo`): non-modal, owned by the
  main window and closed with it; one or two seconds to build.
- **Everything else** opens a small dialog; nothing runs until **Run**.
  The dialog shows what the tool makes (tooltip: data, run time, where
  it is discussed), the run (a documented job, or "Your own arguments"),
  the arguments (`{out}` stands for the output folder), the output folder
  and the exact command. Run starts the tool as its own process (a
  `QProcess` running the documented command from the repository root,
  headless), so the reader stays responsive and a failing tool cannot take
  it down. Its output appears in the dialog and the status bar; the result
  (time, number of files written or changed, the log file with the whole
  output, under the log folder's `tools/`) in the Messages pane. Run
  becomes Stop while it runs; closing the dialog leaves the run going;
  closing the reader stops it.
- **Output folders.** Default: where the documentation keeps the job's
  outputs, i.e. a documented run rewrites committed files in place (git
  shows what changed; `python -m lss_tools.regenerate` records the run).
  Never `sample_data/`, except `sample_data/private/figures/` for tools
  that read private data; a private-data job never writes elsewhere in
  the repository (refused with a message; the tools check it too).
- **Packaged builds** have no Python to run scripts with and no repository
  to write into: the generators and checks are shown disabled with that
  reason, the demonstrations work (`packaging/lss_reader.spec` bundles
  them).
- **The crash sweep** triggers every Tools action: a demonstration opens
  (and is closed with its window), a generator's dialog opens (cheap), and
  the sweep's one-level dialog walk may press Run; that process is killed
  when the sweep closes its window, milliseconds later, before a tool has
  even imported its libraries. `tests/test_gui_tools_menu.py` has
  dialog walks (marked `sweep`) in which Run records instead of starting.

## No stale outputs

`docs/figures/MANIFEST.json` records, for every public job: its command,
the hash of each input, the hash of each output, the run time, the commit,
and the versions of Python, NumPy, SciPy, matplotlib and PyQt5.

    python -m lss_tools.regenerate --check     # what is not fresh, and why (reads only)
    python -m lss_tools.regenerate             # rerun exactly the stale public jobs, update the manifest
    python -m lss_tools.regenerate --only ID   # one job, fresh or not
    python -m lss_tools.regenerate --private   # also the private jobs, when the private data are here

`tests/test_tools_registry.py::test_documentation_outputs_fresh` (quick
suite; hashing only, under a second) fails when a committed output is
stale: an input changed since its recorded run, an output is missing or
differs from what the run wrote, or a run wrote a file it did not record.
`test_generated_folders_hold_only_job_outputs` fails for a file in
`docs/figures/`, `docs/comparisons_data/` or `docs/manual/figures/` that
no job owns (README.md files are hand-written and exempt).

### What counts as an input

The inputs of a job are **what its run actually used**, recorded while it
runs (`lss_tools/trace.py` runs the documented command unchanged under a
Python audit hook):

- **Code**: the tool and every module of the repository it imported
  (lss_core, tests/synthetic, tests/demonstrator, sibling tools,
  spec_routines, ...), lazy imports only when the run reached them. A
  module is hashed by its **syntax tree without docstrings and comments**:
  editing prose leaves every output fresh, while any change of code (a
  number, a default, a label string) makes the outputs of every job that
  ran it stale. The tree is written out field by field, leaving out empty
  fields, so that Python 3.11, 3.12 and 3.13 give the same hash (checked).
- **Data**: every file of the repository the run opened for reading (the
  NX school SPEC file, the frames it read, a joins CSV, the .ui files),
  by content; text files with '\n' line ends, so that a Windows checkout
  hashes the same.

Not inputs, and why:

- Python and the libraries. A new matplotlib redraws every PNG slightly
  differently without any change in what the figure says; counting it
  would make every figure stale on every upgrade. Their versions are in
  the manifest, so a difference can be explained.
- Modules a tool could import but did not (e.g. `lss_core.burn` for a GID
  figure), and code outside the repository. Statically following every
  import would make nearly every figure depend on all of lss_core
  (`lss_core.experiment` imports most of it lazily), so that a change to
  the burn code would mark the pinhole geometry figures stale. The
  recorded set cannot miss a real dependency: a run can start importing a
  new module only after a change to a module it already imported.
- The machine's settings: regenerate runs every job with the disk cache
  off, a fresh preferences file and a temporary log folder.
- `controls.md` counts only `mainwindow.py`, the `.ui` files, `lss_tools`
  and its script (the tooltips live there), not the whole of lss_core,
  which the window imports.

### Private data

Private jobs (registry: `private=True`) read `sample_data/private/` and
write only under `sample_data/private/figures/`; they are recorded in the
git-ignored `sample_data/private/figures/MANIFEST.json`, so nothing
derived from private data is committed, not even a hash. `regenerate
--private` runs them when the data are present and says "skip" otherwise;
the freshness test checks only public jobs.

## Inventory

Kinds: 2 demonstrations, 7 figure generators, 5 data generators and
surveys, 11 checks: 25 entries for 23 programs (22 scripts in
`tests/tools/` and `lss_tools.regenerate`; `patch_demo.py` serves both
demonstrations and the report figures); 14 public jobs and 6 private
ones; one helper module (`tests/tools/pinhole_frames.py`). Run times:
measured by `regenerate` on this 4-core machine, 2026-11-22 (also in the
manifest, per job).

### Demonstrations

| Tool | Command | Data | What it shows | Time |
|---|---|---|---|---|
| `demo_refl` | `python tests/tools/patch_demo.py` | synthetic | Reflectivity patching by every method on overlapping synthetic scans, truth beside; space bar: new replicate | 1–2 s to open |
| `demo_burn` | `python tests/tools/patch_demo.py --mode burn` | synthetic | Burn line cuts by every estimator, trends over time, truth | 2–3 s to open |

### Figures and data (jobs with committed outputs)

| Tool | Job | Command | Data | Committed outputs | Time |
|---|---|---|---|---|---|
| `patch_demo` | `patch_demo` | `python tests/tools/patch_demo.py --save docs/figures/patch_demo` | synthetic | `docs/figures/patch_demo/` (6 PNG, summary CSVs, `numbers.json`) | 3 min |
| `burn_figures` | `burn_figures` | `python tests/tools/burn_figures.py` | NX 14, 15 | `docs/figures/burn_trends/*.png`, `docs/comparisons_data/burn_nx/*.csv` | 6 s |
| `gid_compare_figures` | `gid_compare_S11` | `python tests/tools/gid_compare_figures.py --scans 11 --out docs/figures/gid_compare` | NX 11 | `docs/figures/gid_compare/nx_S11_*` | 11 s |
| | `gid_compare_S11+12` | `... --scans 11,12 --peak none --note "not like for like: scan 12 stopped after 4 frames" --out docs/figures/gid_compare` | NX 11, 12 | `docs/figures/gid_compare/nx_S11+12_*` | 11 s |
| | `gid_compare_private_163+165`, `gid_compare_private_386-389` | `... --spec sample_data/private/gid_scans_136-146/gid --scans … --out sample_data/private/figures/gid_compare` | private | (not committed) | |
| `gid_patching_diagrams` | `gid_patching_diagrams` | `python tests/tools/gid_patching_diagrams.py` | NX 11, 12 | `docs/manual/figures/gid_patching/*.png` | 49 s |
| `gid_stray_light` | `gid_stray_light` | `python tests/tools/gid_stray_light.py` | NX 11, 12 | `docs/figures/gid_stray_light/*.png` | 4 s |
| | `gid_stray_light_private_163_165`, `gid_stray_light_private_386_389` | `... --spec … --scans … --out sample_data/private/figures/slit_scatter` | private | (not committed) | |
| `pinhole_beam_figure` | `pinhole_beam_figure` | `python tests/tools/pinhole_beam_figure.py` | NX 11 | `docs/figures/pinhole_beam/*.png` | 11 s |
| `pinhole_figures` | `pinhole_figures` | `python tests/tools/pinhole_figures.py` | NX 11, 12 | `docs/figures/pinhole/case*.png` | 21 s |
| | `pinhole_figures_private` | `... --spec … --low 163 --high 165 --label "private GID file" --out sample_data/private/figures/pinhole` | private | (not committed) | |
| `compare_methods` | `compare_methods` | `python tests/tools/compare_methods.py` | NX | `docs/comparisons_data/C*.csv`, `manifest.json` (the `*_map.csv` maps are git-ignored) | 70 s |
| `gid_method_survey` | `gid_survey_nx` | `python tests/tools/gid_method_survey.py --spec sample_data/NX_school/2026sep/20260923 --out docs/comparisons_data/gid_survey_nx --split` | NX | `docs/comparisons_data/gid_survey_nx/` | 3 min |
| | `gid_survey_private` | `... --spec … --out sample_data/private/figures/gid_survey --split` | private | (not committed) | |
| `ref_patch_survey` | `ref_patch_nx` | `python tests/tools/ref_patch_survey.py --spec sample_data/NX_school/2026sep/20260923 --out docs/comparisons_data/ref_patch_nx --split --repeats` | NX | `docs/comparisons_data/ref_patch_nx/` | 3 s |
| `ref_patch_gauntlet` | `ref_patch_gauntlet` | `python tests/tools/ref_patch_gauntlet.py --out docs/comparisons_data/ref_patch_gauntlet --design all` | synthetic | `docs/comparisons_data/ref_patch_gauntlet/*.csv`, `summary.md`, `log.txt` (`pulls.csv` only with `--rows`, git-ignored) | about 25 min |
| | `ref_patch_gauntlet_core_all` | `... --out docs/comparisons_data/ref_patch_gauntlet/core_all_methods --design core --methods all` | synthetic | `docs/comparisons_data/ref_patch_gauntlet/core_all_methods/` | about 3 min |
| `dump_tooltips` | `controls` | `python tests/tools/dump_tooltips.py > docs/manual/controls.md` | code | `docs/manual/controls.md` | TIME_controls |

### Checks (print only; nothing committed)

| Tool | Command (default arguments) | Data | What it reports |
|---|---|---|---|
| `absorber_steps` | `python tests/tools/absorber_steps.py sample_data/NX_school/2026sep/20260923 6,7,8,9` | NX (any SPEC) | Measured absorber steps against nominal; extra Al thickness (C7, C8) |
| `foil_fit_from_joins` | `python tests/tools/foil_fit_from_joins.py docs/handoff_out/03-answer/joins.csv` | hand-off 03 joins | Per-foil thicknesses, residual per join |
| `monitor_distribution` | `python tests/tools/monitor_distribution.py` | every SPEC under `sample_data/` | Monc scatter: spread, tails, distribution; share of each point's variance |
| `monitor_gains` | `python tests/tools/monitor_gains.py` | every SPEC under `sample_data/` | '#M Monc Gain' lines not understood (F52; `docs/reports/monitor_gains.md`) |
| `monitor_noise_mc` | `python tests/tools/monitor_noise_mc.py` | simulated, NX | Monte Carlo of monitor error propagation (C4) |
| `monitor_ratio` | `python tests/tools/monitor_ratio.py sample_data/NX_school/2026sep/20260923` | NX (any SPEC) | Beam variation against monitor noise (C9) |
| `monitor_witness` | `python tests/tools/monitor_witness.py` | every SPEC under `sample_data/` | Monc jumps: does the detector follow? |
| `pinhole_beam_profile` | `python tests/tools/pinhole_beam_profile.py` | NX 11, synthetic | Gaussian beam against the fitted column response (C23) |
| `single_frame_truth` | `python tests/tools/single_frame_truth.py --scans 11 --peak 16.63` | NX (any SPEC) | Single frames against patched maps; distance scan (C28) |
| `spec_epoch` | `python tests/tools/spec_epoch.py sample_data/NX_school/2026sep/20260923` | NX (any SPEC) | What the Epoch column measures |
| `regenerate` | `python -m lss_tools.regenerate --check` | | Which committed outputs are stale, and why; without `--check`, regenerates them |

### Committed outputs not made here

| Where | Made by |
|---|---|
| `docs/handoff_out/03-answer/` | the owner-side analysis in another repository (`tools/absorber_steps.py`, `tools/absorber_review.py`, private data); listed, not checked |
| `docs/timings.md` | `pytest -m bench -s`: a measurement of the machine, not documentation code |
| `docs/reports/*.md` | hand-written reports; the numbers they quote come from the jobs above (each report names its command) |
