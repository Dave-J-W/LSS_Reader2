# Tools audit: committed products rerun and compared (2026-11-23)

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
