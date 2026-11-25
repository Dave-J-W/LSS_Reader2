# Tools audit: committed products rerun and compared (2026-11-23; 2026-11-25)

Made by `python -m lss_toolbox --audit --report FILE` (F84), which reruns
every item that has committed figures or tables with the settings that
made them, into run folders outside the repository, and compares each
product with its committed counterpart: images pixel for pixel
(`lss_toolbox.compare`), tables and text byte for byte. "git says" is
`python -m lss_toolbox --stale` (git history of the script, what it
imports and its inputs since the products' last commit), which can only
say what *might* have changed. Everything below is **measured** (this
container, 2026-11-23, code of `main` at 889cb7b plus the Tools-menu
branch) unless marked as read.

Two settings of this run differ from the catalogue's final ones: the
gauntlet ran with every method (the committed run judged seven; corrected
since), and `compare_methods` was still credited with the C21 tables (no
tool writes them; see below).

## 2026-11-25: the verified record (measured)

Tools man, for the former patching session's review (2026-11-24): "`--stale`
flags 23 of 28 items, mostly wrongly … A rerun that reproduces a product
exactly commits nothing, so the flag never clears", and "Pixel audits of
`pinhole_beam_figure` and `gid_stray_light` differ by 1.6 % and 4–16 % …
record or pin". Everything here was measured in this container on
2026-11-25, at the head of `claude/gracious-knuth-e7ry2y` (main at
ef15766, then 78aebd1 merged, plus this work).

### What changed

- **The audit keeps what it verified.** `python -m lss_toolbox --audit
  --record` runs each tool through `lss_toolbox.trace`, which lists the
  repository modules the run imported and the files it read. When the
  products match, it writes `lss_toolbox/verified.json`: fingerprints of
  those inputs and of the products it reproduced, the commit, and the
  environment.
- **`--stale` reads the record first.** Products are current while every
  recorded input has the same fingerprint. A Python file's fingerprint is
  its syntax tree without docstrings and comments (the same across
  Python versions). A module imported only on a path the run never took is
  not in the record (the static import graph puts the demonstrator's
  window under `patch_demo_figures`; the trace shows the run never imports
  it). Without a record, or once the products change, git history decides
  as before, with prose-only changes dropped.
- **The comparison leaves out how a product was run.** The command line a
  text product echoes (it names the run folder), JSON `command` and
  `seconds` entries, and lines an item names as `volatile` (the guard
  study's wall times) are left out. Two tools print their git revision in
  their figures (`pinhole_figures`, `gid_patching_diagrams`); they now take
  it from `LSS_TOOLS_REVISION` when set, and the audit runs them a second
  time with a dummy revision: the pixels that move are the stamp, which is
  masked; the rest must be identical.
- **Text and check items are audited too:** a text item's printed output
  is compared with its committed file (`controls.md`), and a check item
  (`gui_map --check`, `ngui_inventory --check`) is verified when it exits 0.
  git flagged all three whenever `mainwindow.py` changed.
- **Run records name what draws a figure:** the machine, numpy's SIMD
  level, matplotlib's freetype (version and build) and contourpy,
  kiwisolver and fontTools (not pinned by `packaging/requirements-build.txt`).
  When images differ from a verified item, the audit lists the differences
  from the record's environment.

### Before and after

| | current | indirect | stale |
|---|---|---|---|
| `--stale` before this work (git only, today's tree) | 3 | 1 | 26 |
| `--stale` after (the record, else git without prose) | 28 | 0 | 2 |

The two stale ones are measured stale (below); every "current" is a rerun
that matched. `verified.json` holds 28 items: 26 identical, 1 identical
apart from its revision stamp, 1 different only through the environment.

### Item by item

Two audits (all 27 figure and data items, then the 20 that the first left
unverified or that merging main made stale), then the three text and
check items, which the audit covers since this work. "git said" is
`--stale` before this work.

| Item | git said | Verdict | Note |
|---|---|---|---|
| burn_figures | stale | **same** | 4 figures, 3 tables |
| reciprocity_study | current | **same** | |
| burn_dose_figure | stale | **same** | |
| patch_demo_figures | stale | **same** | the trace: the run never imports the demonstrator's window |
| ref_patch_gauntlet | stale | **same** | 6 tables (5 committed files are written only by other settings) |
| ref_patch_biased_joins | stale | **same** | |
| qoff_study | stale | **same** | |
| ref_guard_study | stale | **same** | once its wall times were left out (`volatile`) |
| ref_patch_survey | stale | **same** | |
| covariance_pulls | stale | **same** | |
| compare_methods | stale | **same** | 45 tables, once the manifest's command line was left out |
| pinhole_figures | stale | **regenerated, then same** | 6 of 8 differed only in the stamp; 2 by sub-pixel amounts (an arrowhead in case 1, a dotted curve in case 8): code since 2026-11-20. Rerun into the repository |
| gid_patching_diagrams | stale | **stamp** | 8 of 8 identical apart from the revision they print |
| gid_compare_figures | stale | **same** | once the summary's command line was left out |
| pinhole_beam_figure | stale | **same** | review item 2: identical here |
| gid_stray_light | stale | **same** | review item 2: identical here |
| gid_movie | stale | **same** | |
| gid_column_groups | stale | **same** | |
| gid_method_survey | stale | **same** | |
| fit_scan_survey | stale | **same** | |
| mca_fit_gauntlet | stale | **conditions.csv regenerated, then same** | the tool writes three more columns since Study B2 (`compton_model`, `core_scale`, `doppler_scale`); its six result tables were identical |
| mca_fit_demo | stale | **same** | once the JSON's `seconds` was left out |
| mca_study | current | **tool fixed, B3 regenerated, then same** | B3's rows came out in a different order from run to run: four pairs of conditions have the same counts (`counts_30` and `counts_x0.03`, …) and their order came from a set; ties are now broken by name |
| mca_scatter | current | **environment** | 10 % of pixels differ; its own commit, run here, gives what today's code gives: drawn on another computer |
| timeline_mock | stale | **same** | |
| dump_tooltips | stale | **same** | `controls.md` identical to a fresh dump |
| gui_map | stale | **same** | `--check` passes |
| ngui_inventory | stale | **same** | `--check` passes |
| gui_screens | stale | **stale** | 52 of 75 screenshots differ, many in size (test windows at minimum size since #67), 15 also by code; the GUI manager's to remake |
| ngui_screens | stale | **stale** | 6 of 23 changed by code (ngui since 2026-11-24); the GUI manager's |

Regenerate the record after remaking products (or when `--stale` flags an
item):

    LSS_READER_TOOLS_DIR=/tmp/audit python -m lss_toolbox --audit --record [--only ID ...]

and commit `lss_toolbox/verified.json` with the products. About 50 min for
everything here (the gauntlets and the screenshots are most of it).

### The two figures of the review (item 2)

`pinhole_beam_figure` and `gid_stray_light` are **identical** to the
committed ones in this container (both audits, 2026-11-25), as they were
when redrawn here on 2026-11-23 (64de896). The reviewer's container drew
them differently under the same pinned numpy, scipy, matplotlib and pillow.
What was ruled out here, measured: numpy's run-time SIMD choice (both
figures identical with the AVX-512 paths switched off,
`NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"`). What remains,
read only: both lay out with `tight_layout`, which places the axes from
measured text extents, so the fonts found and the freetype matplotlib was
built with move every axis; contourpy, kiwisolver and fontTools are not
pinned either. Without the reviewer's container this is **recorded, not
pinned**: the run records and `verified.json` now name these, so the next
difference can be traced to its library. To pin instead: add contourpy,
kiwisolver and fontTools to `packaging/requirements-build.txt` and draw
committed figures only in an environment built from it (the packaging
owner's choice).

# The first audit (2026-11-23)

## The table as the audit wrote it

Columns "same / differ / not made" count products with the same name in
the run and in the repository; "not made" are committed products the run
did not write (other settings, or files written by hand).

| Item | git says | Exit | Images same / differ / not made | Tables same / differ / not made | Differences |
|---|---|---|---|---|---|
| burn_figures | stale | 0 | 4 / 0 / 0 | 3 / 0 / 0 | — |
| patch_demo_figures | stale | 0 | 6 / 0 / 0 | 5 / 0 / 0 | — |
| ref_patch_gauntlet | current | 0 | 0 / 0 / 0 | 2 / 4 / 5 | levels.csv: differs; pooled.csv: differs; summary.md: differs; verdict.csv: differs |
| ref_patch_survey | stale | 0 | 0 / 0 / 0 | 0 / 4 / 0 | joins.csv: differs; sets.csv: differs; split.csv: differs; summary.md: differs |
| covariance_pulls | indirect | 0 | 0 / 0 / 0 | 2 / 0 / 1 | — |
| compare_methods | stale | 0 | 0 / 0 / 0 | 15 / 4 / 8 | C2_ref_nx_budget_gaussian.csv: differs; C2_ref_nx_budget_student_t.csv: differs; C2_ref_nx_legacy.csv: differs; manifest.json: differs |
| pinhole_figures | stale | 0 | 0 / 8 / 0 | 0 / 0 / 1 | case1_lab_frame_and_detector.png: 0.112 % of pixels differ (rows 104-1070, columns 492-2012); case2_direct_beam_row_and_column.png: 0.112 % of pixels differ (rows 104-125, columns 492-1129); case3_pinhole_top_view.png: 0.112 % of pixels differ (rows 104-125, columns 492-1129); … |
| gid_patching_diagrams | stale | 0 | 0 / 8 / 0 | 0 / 0 / 1 | 01_frame_anatomy.png: 0.032 % of pixels differ (rows 1219-1229, columns 719-774); 02_columns_to_two_theta.png: 0.052 % of pixels differ (rows 744-754, columns 719-775); 03_frames_cover_two_theta.png: 0.033 % of pixels differ (rows 1193-1204, columns 772-827); … |
| gid_compare_figures | stale | 0 | 3 / 0 / 3 | 0 / 1 / 2 | nx_S11_summary.json: differs |
| pinhole_beam_figure | stale | 0 | 0 / 1 / 0 | 0 / 0 / 1 | beam_response_11.png: 1.641 % of pixels differ (rows 82-581, columns 49-1668) |
| gid_stray_light | stale | 0 | 0 / 2 / 0 | 0 / 0 / 1 | bands_11_12.png: 4.439 % of pixels differ (rows 53-400, columns 19-1951); frames_11_12.png: 16.179 % of pixels differ (rows 15-631, columns 18-1324) |
| gid_method_survey | stale | 0 | 0 / 0 / 0 | 3 / 3 / 0 | calibration.csv: differs; methods.csv: differs; truth.csv: differs |
| fit_scan_survey | indirect | 0 | 0 / 0 / 0 | 0 / 1 / 1 | C37_fit_scan_new_nx.csv: differs |
| gui_screens | current | 0 | 68 / 5 / 2 | 0 / 1 / 0 | 50b_burn_main_window_behind.png: 0.468 % of pixels differ (rows 7-1396, columns 6-2279); 52_burn_legacy_gid_view.png: 0.002 % of pixels differ (rows 558-579, columns 301-301); 81b_plot_peak_fit_window_fitted.png: 0.711 % of pixels differ (rows 11-415, columns 11-428); … |
| ngui_screens | current | 0 | 23 / 0 / 0 | 1 / 0 / 0 | — |
| timeline_mock | indirect | 0 | 1 / 0 / 0 | 0 / 0 / 0 | — |

## What it means, item by item

| Item | Verdict | Why |
|---|---|---|
| burn_figures | **current** | 4 figures and 3 tables identical, although git flags it (lss_core changed, not in a way these figures show) |
| patch_demo_figures | **current** | 6 figures, numbers.json and 4 tables identical |
| ref_patch_gauntlet | **current** | every committed row reproduced exactly (`diff`: 0 rows changed in verdict.csv, levels.csv, pooled.csv); the run's extra rows are the methods the committed run did not judge |
| covariance_pulls | **current** | both committed tables of the default monitor identical; the Poisson-monitor table needs its variation (`--poisson-monitor`) |
| ngui_screens | **current** | 23 of 23 identical |
| timeline_mock | **current** | identical |
| pinhole_figures | **current but for the stamp** | every figure differs in 0.11 % of pixels, all inside the header line where the tool prints the git revision (rows 104–125) |
| gid_patching_diagrams | **current but for the stamp** | 0.03–0.05 % of pixels, inside the one-line source stamp at the foot of each diagram |
| gid_compare_figures | **current** for scan 11 | 3 figures identical; the S11+12 set needs its variation; `nx_S11_summary.json` differs (not compared in detail) |
| gui_screens | current, except clocks | regenerated in this branch; a second run differs in 5 of 73 (the messages pane's times, a fit window, the GISAXS view, a burn view by 0.002 %): screenshots carry times, so they never reproduce exactly |
| pinhole_beam_figure | **stale** | 1.6 % of pixels across the plot: the beam response changed after the figure was made |
| gid_stray_light | **stale** | 4.4 % and 16 % of pixels across both figures |
| compare_methods | **C2 tables stale** (remade 2026-11-23) | the three C2/C3 error-model tables were made with the legacy patch; since b51bae2 the default patch is the joint fit, so R moves by up to 0.1 % and σ by up to 21 % (Qz = 0.035 Å⁻¹, compared numerically). Remade the same day: the error models' ratios hardly move (Gaussian/legacy 0.861–1.002 before and after, Student t/legacy 0.893–1.004 → 0.893–1.005), so the comparison was not confounded, only its curves out of date. `manifest.json` differs only in its "command" field (the output folder); C6, C10, C11 identical |
| ref_patch_survey | **stale** | values changed, not only the timing column: median error of joint_o4_e4 0.00407 → 0.00381, one join flagged per joint method (the guard ladder of 6bb29bf came after the survey, 46256cd) |
| gid_method_survey | probably stale | calibration.csv, methods.csv, truth.csv differ (not examined; lss_core's pinhole code changed since, including the closed-form footprint window) |
| fit_scan_survey | not judged | the table has a timing column (seconds per fit), so it never reproduces byte for byte; the old-rules table needs its variation |

**C21 tables had no generator.** `docs/comparisons_data/C21_*.csv`
(pinhole angles per axis vs exact; commit ab33063, 2026-11-20) were written
by no script in the repository. Since 2026-11-23 `compare_methods.py`
writes them (`GIDParams(angles=...)`), and the C24 footprint tables too,
which `COMPARISONS.md` said it wrote but it did not.

## How to act on it

Rerunning a stale item into the repository is one click in the Tools
window (the item's page, Defaults or "As committed", "Replace the
committed products"), or `python tests/tools/<script>.py` with the
committed settings (`docs/TOOLS.md`). Whoever owns the area should do it
together with a reading of the text that quotes the figure or table
(READMEs beside the figures, `COMPARISONS.md`, the reports), because
regenerated numbers can contradict that text. Rerun this audit with

    LSS_READER_TOOLS_DIR=/tmp/audit python -m lss_toolbox --audit --report docs/reports/tools_audit.md

and then rewrite the "What it means" section by hand (about 45 min; the
full gauntlet is 25 of them; `--max-seconds 60` leaves out the slow items).

## Remedied, later on 2026-11-23 (measured)

Each item the table flagged was rerun with the settings that made it and
compared again; where images differed, the products' own commit was run in
this environment as well (`--audit` does this since then: column "Why
images differ").

| Item | Outcome |
|---|---|
| pinhole_beam_figure, gid_stray_light | **Not stale: environment.** Their own commit (ab33063), run here, gives the same pixels as today's code; the committed figures had been drawn in another environment. Redrawn in the pinned one (`packaging/requirements-build.txt`); every quoted number unchanged |
| compare_methods | C2/C3 remade (joint-fit patch; the error-model ratios unchanged in substance); C21 remade by the tool (`GIDParams(angles=...)`, new), C24 written for the first time (`COMPARISONS.md` had named the command, which did not write it); C6, C10, C11 identical. New numbers beside the old in `COMPARISONS.md` |
| ref_patch_survey | Remade: o4 e4's third join at order 5 (0.103604 → 0.103423), the default o4 e2 flags join 2, median error 0.00407 → 0.00381 (`COMPARISONS.md` C33) |
| gid_method_survey | Current in substance: only timings and floating-point-level values moved (distance 265.77406 → 265.77386 mm); remade |
| gid_compare_figures (S11+12) | Current: identical with the documented command (the catalogue's variation had another `--note`, corrected) |
| fit_scan_survey | Current: the C37 table identical apart from its timing column |
| gui_screens | The g_l2/g_l3 dialogs captured again (and their off-by-one fixed); the MCA screenshots follow main's faster plotting |

Two lessons for the tool, built in: a pixel difference can come from the
environment, so run records name the libraries; and a table with a timing
column needs comparing without it. (The second was claimed here but the audit still compared
tables byte for byte, so `ref_patch_survey` read "joins.csv: differs" from
its `seconds` column alone; since 2026-11-24 `compare.tables_same` leaves
out a CSV's `seconds` columns, measured: `ref_patch_survey` 4 / 0 / 0.)

