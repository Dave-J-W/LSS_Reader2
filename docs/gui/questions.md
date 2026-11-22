# Questions for the owner (GUI overhaul)

72 questions from the assessment, in four files by topic. The fifteen
below are the ones whose answers change the most: they fix the workflow
map for the priority workflows, the image-display defaults, and what phase
1b keeps or removes. Answer in any order and in any form; each answer is
recorded beside its question with the date.

## Answer these first

| # | Question | Look at | Where it is asked in full |
|---|---|---|---|
| 1 | **A typical day at the beamline, in order**: for one sample, which scans, which reductions, which checks, in what order? | `screens/00_overview_annotated.png` | Q-GEN-2 |
| 2 | **Fluorescence burns**: how are they measured (repeated MCA spectra at one Qz?) and judged? They do not exist in the reader yet | — | Q-BURN-3 |
| 3 | **What do you do with a burn verdict**: move the sample, change the absorber, shorten exposures, or note it? | `screens/50_burn_gid_trends_view.png` | Q-BURN-1 |
| 4 | **Reflectivity**: do you check the ROI frame by frame before patching, and what do you look at in each join? | `screens/31_refpatch_dialog_first_join.png` | Q-REF-1, Q-REF-2 |
| 5 | **XFNTR**: window sum or fitted lines today; how do you place the window or the line? | `screens/72b_mca_integral_vs_qz.png`, `75_mca_fit_lines_result.png` | Q-XFNTR-1, Q-XFNTR-2 |
| 6 | **EXAFS**: what should the reader give you (spectra vs energy, line fits per point, a file for Athena/Larch)? | — | Q-EXAFS-1 |
| 7 | **Movie for every multi-frame selection, or only above 6 frames?** | `screens/23b_pilatus_all_frames_reflectivity_series.png` | Q-IMG-1 |
| 8 | **Default image scale by scan kind** (log for reflectivity/GID/GISAXS, linear for direct beam and dark, top at the 99.9th percentile with the direct beam masked), and **image units** (counts, per monitor, or per monitor absorber-corrected) | `screens/21_pilatus_one_frame.png` | Q-IMG-5, Q-IMG-6 |
| 9 | **What is sticky, and where**: display settings globally or per scan kind; zoom for the session or saved per SPEC file | — | Q-IMG-2, Q-IMG-3 |
| 10 | **Reflectivity burn or GID burn**: may the reader decide by Det_Th > 1° (or Qxy ≠ 0) → GID, or will SPEC say so? | `screens/53_burn_ref_series_selected.png` | Q-IMG-13 |
| 11 | **Messages and Errors docks**: same rule as the Script pane (D59: hidden by default, out of the selection panel's way)? | `screens/96_pane_messages.png`, `98_pane_errors_legacy.png` | Q-UI-A1 |
| 12 | **Show the state that changes numbers** (error model, / gain, / photon, patch method) on screen as short labels, with the detail in tooltips? | `screens/98b_pane_errors_budget.png` | Q-UI-A2, Q-UI-B5 |
| 13 | **Legacy paths**: are Analyze/Accept (point by point), the MCA Fit/Fit All/Accept and the Plot tab's Peak Fit still used? Keep, hide behind one button, or remove? | `screens/73_mca_peak_fit_dialog.png`, `81_plot_peak_fit_window.png` | Q-UI-B1, Q-UI-B2 |
| 14 | **May these go**: the Apex tab, the Beamlines menu, the unused `peakfit2`/`peakfitpara` dialogs, the Command line? And should File > Quit and Help > Documentation work? | `screens/14_apex_tab.png`, `99_menu_beamlines.png` | Q-UI-A4, A11, A12, B8 |
| 15 | **Residuals panel (F74)**: residuals weighted by the errors, (y − fit)/σ, or plain y − fit? | — | asked in chat, 2026-11-22 |

## All questions

| File | Ids | Count |
|---|---|---|
| `questions/workflows.md` | Q-BURN-1–6, Q-REF-1–6, Q-GID-1–5, Q-XFNTR-1–5, Q-EXAFS-1–4, Q-CUTS-1–3, Q-GEN-1–5; opens with the topics already answered (cited, not asked again) | 34 |
| `questions/image_display.md` | Q-IMG-1–16 | 16 |
| `questions/inventory_a.md` | Q-UI-A1–A12 (left panel, menus, panes, SpecPlot, Pilatus, cuts, 2D_Plot, Apex) | 12 |
| `questions/inventory_b.md` | Q-UI-B1–B10 (Reflectivity, MCA, Plot, dialogs) | 10 |

## Answers

| Date | Question | Answer | Recorded where |
|---|---|---|---|
| | | | |
