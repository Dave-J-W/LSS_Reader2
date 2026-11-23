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
| `timeline/research.md` | Q-TL-1–8 (the sample timeline, F83: silent offset changes, a macro line marking a new sample, several SPEC files, sh-scan ROI and thresholds, notes, sx, environment columns) | 8 |

## Answers

| Date | Question | Answer | Recorded where |
|---|---|---|---|
| 2026-11-23 | 1 (Q-GEN-2) A typical day | For a reflectivity day: half-cut (later an sh scan with a horizontal beam), height offset to zero; sample height scans, several compared on one plot; burn tests, absorber changed and repeated until no change over about 400 s, skipped once a safe absorber is established; the macro's first data set reduced (scans by hand, Select All, Ref Patch), Qc of water unless the subphase differs, Qoff tweaked until R/R_F is continuous; macro tuned; a new sh scan after 30 min or a large sx move, judged by width and flat top (super-Gaussian good, Gaussian possibly unusable); reduced curves compared over places and time; then the sample change. | `physics_notes.md` 2026-11-23; map `day-ref`, `alignment`, `burn-ref`, `reflectivity`; F75–F80 |
| 2026-11-23 | 3 (Q-BURN-1) What follows a burn verdict | Change the absorber and repeat until effectively no change over about 400 s; once an absorber is established, no more burn tests; sometimes the sample changes by itself (not burning) | as above; F76, F77 |
| 2026-11-23 | 4, in part (Q-REF-1) ROI frame by frame? | Done, but mostly when something is weird and the data must be verified; the routine path is Ref Patch. A slick movie, on a log or other nonlinear scale, would make it more frequent; showing people the raw data helps them avoid mistakes. What is looked at in each join (Q-REF-2) is still open | as above; F71; `image_display.md` (owner note under §2.1) |
| 2026-11-23 | 7, 9, in part (Q-IMG-1, Q-IMG-3, Q-IMG-5) Movie, stickiness, scale | GID frames are often watched as a movie: real peaks stay at the same 2θ as the detector angle changes, junk does not. In all cases: zoom on the raw data (for reflectivity, the region around the ROI) and play the frames without the zoom, colour mode or anything else changing. Log or another nonlinear scale for the movie. Still open: movie above which number of frames, session or saved zoom, units | F69; `image_display.md` M2, M7 |
| 2026-11-23 | Q-REF-4, in part: Qc and Qoff | Qc of water assumed, changed for lighter or denser subphases; Qoff tweaked by hand until R/R_F is continuous (one or two outliers acceptable) | as above; F79 |
| 2026-11-23 | Q-REF-5, in part: comparisons | Reduced curves are compared in the reader across places and over time, for stability (which tab: open) | as above; F80 |
| 2026-11-23 | Q-GEN-4, in part: alignment scans in the reader | Sample height scans are viewed and compared in the reader (several selected together); the Calculations menu is still open | as above; F78 |

| 2026-11-23 | Follow-ups to the day | Established safe absorbers depend heavily on the sample, the subphase and the energy, but do not change within a beamtime. A good sample height scan has a FWHM of about 65 µm or more ("better than about 65 microns"; confirmed "at least"; up to about 110 µm in the 89 mm trough) and is flatter than a Gaussian. Scans are selected one by one because the Series list is new and not yet tried by people. Qc depends on the subphase, which is rarely pure water, though water's Qc is "rarely very wrong, depending on which decimal place you're looking at". The day also includes deciding whether the statistics suffice, and if not repeating the macro and having the reader sum the repeats' ROIs | `physics_notes.md` 2026-11-23; F78, F79, F81; map `day-ref` (`day.stats`) |

| 2026-11-23 | 15 (F74) Residuals weighting | Weighted, (y − fit)/σ | F74 (the assumption becomes the answer) |
| 2026-11-23 | 14 (Q-UI-A4, A11, B8) May these go | Yes to all four: the Apex tab (its colour map moves first), the Beamlines menu, the unused `peakfit2`/`peakfitpara` dialogs, the Command line row (the export-header line stays) | `physics_notes.md` 2026-11-23 (GUI answers, batch 1) |
| 2026-11-23 | 14 (Q-UI-A12) Quit and Help > Documentation | Quit works; Documentation opens `docs/SCRIPTING.md` for now, the manual when it exists | as above |
| 2026-11-23 | 11 (Q-UI-A1) Messages and Errors docks | Yes: all three panes (Script, Messages, Errors) follow D59 together; Messages raises only on warnings | as above |
| 2026-11-23 | 12 (Q-UI-A2, B5) Show the state that changes numbers | Yes, as status-bar badges (error model, / gain, / photon, patch method). **Added:** a visual preference with three modes: *on*, *on when not default*, *off* | as above; F85 |
| 2026-11-23 | 13 (Q-UI-B1, B2) Legacy paths | Nothing is removed: Analyze/Accept, MCA Fit/Fit All/Accept and the Plot tab's Peak Fit "seem essential". Which path an action takes is set on a new **Reduction options** preferences page (legacy modes on/off, with the other maths options). **Added:** Ctrl+click on a GUI action flips the legacy boolean for that one action and prints a message (never a dialog) saying the mode was switched by the modifier-key click | as above; F86 |
| 2026-11-23 | 10 (Q-IMG-13) Reflectivity burn vs GID burn | Det_Th > **2°** → GID (not 1°, as proposed). The owner will also work toward a macro role indicator; the reader will read it when it exists | as above; F87 |
| 2026-11-23 | 7 (Q-IMG-1) Movie or tiles | A movie whenever **3 or more** frames are selected. Space pauses/plays; any arrow key pauses and then steps: up, back and left go backward in time, down, forward and right go forward | as above; F69 |
