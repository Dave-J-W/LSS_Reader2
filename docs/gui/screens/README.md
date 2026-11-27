# Screenshots of the reader window (GUI overhaul, phase 1a)

Made by `python tests/tools/gui_screens.py` (offscreen Qt, scale 1; the window cannot be narrower than about
2266 px, so whole-window shots are 2300 px wide). Data: the public NX school set (`sample_data/NX_school/2026sep/20260923`)
and synthetic data from `tests/synth.py` for MCA / fluorescence, the reflectivity burn and the absorber scan
(NX has no MCA data). Regenerate the whole folder with the command above; the table is rewritten, the
Observations section is by hand and is kept.

80 images, 5.1 MB, last run took 48 s.

| File | What it shows | Data and state |
|---|---|---|
| `00_overview_annotated.png` | Whole window with the main areas outlined and named (the "where is what" map) | NX school 20260923 opened; scan 4 (a2scan sh/oh) selected; SpecPlot tab; Script pane raised in the bottom dock |
| `00b_overview_plain.png` | The same window, unannotated | NX school 20260923 opened; scan 4 selected; SpecPlot tab; bottom dock open (Script tab) |
| `01_window_empty.png` | Whole window, nothing opened | No SPEC file; SpecPlot tab (first tab) shown |
| `10_leftpanel_series_chosen.png` | Left panel: series chooser, scan list, frame list, background list, buttons | NX opened; series "reflectivity 4/?: S# 6-9" chosen in the series chooser (its scans become the selection) |
| `10b_leftpanel_series_dropdown.png` | The series chooser list opened | NX opened; the five series entries |
| `11_specplot_motor_scan.png` | SpecPlot tab, whole window | Scan 4 (a2scan sh/oh, 20 points) selected; default axes |
| `12_specplot_tab_crop.png` | SpecPlot tab page: controls and plot | Scan 4 selected |
| `13_specplot_two_scans.png` | SpecPlot with two scans selected (legend, N-scan controls) | Scans 4 and 5 selected |
| `13b_specplot_beam_off_scan.png` | SpecPlot of scan 1 (a motor scan with the beam off) | Scan 1 selected |
| `13c_plot_options_dialog.png` | Plot options of the SpecPlot tab (F112-F114): Text and ticks | Font 14 pt, about 5 major ticks, minor ticks, ticks in and on all sides, grid at the major ticks; legend shown upper left without a frame, lines 2 pt; the y label renamed, the first curve red with square markers |
| `13d_specplot_with_plot_options.png` | SpecPlot with those plot options (F112-F114); the button at the right of the tab bar shows a * | Scan 4 selected; the options of 13c, 13e, 13f |
| `13e_plot_options_legend_lines.png` | Plot options: Legend and lines (F114) | Font 14 pt, about 5 major ticks, minor ticks, ticks in and on all sides, grid at the major ticks; legend shown upper left without a frame, lines 2 pt; the y label renamed, the first curve red with square markers |
| `13f_plot_options_this_plot.png` | Plot options: This plot (F114): labels, ranges, curves | Font 14 pt, about 5 major ticks, minor ticks, ticks in and on all sides, grid at the major ticks; legend shown upper left without a frame, lines 2 pt; the y label renamed, the first curve red with square markers |
| `14_timeline_tab.png` | Timeline tab (F83): events, sx, sample-height scans and scans on one time axis | NX school file opened; Timeline tab shown (fitted to the whole file) |
| `14b_timeline_dose.png` | Timeline with Dose on (F107): the sx line coloured by each spot's dose as a fraction of the burn test's dose to a 5 % change | NX school file; Dose ticked (beam 1 mm wide, its height from the sample-height scans) |
| `20_pilatus_empty.png` | The Pilatus tab (page and its controls) with nothing loaded | No SPEC file; crop of the tab widget |
| `20_pilatus_scan_selected_no_frames.png` | Pilatus tab, whole window: a scan with images selected, no frame selected yet | Scan 11 (ascan dth, 40 frames) selected, no frame selected |
| `21_pilatus_one_frame.png` | Pilatus tab, whole window, one frame | Scan 11, frame 1 selected |
| `21b_pilatus_tab_controls.png` | Pilatus tab page (controls above, image below) | Scan 11, frame 1 |
| `22_pilatus_three_frames.png` | Pilatus tab with three frames selected (a movie since 2026-11-24, F69) | Scan 11, frames 1, 11, 21 selected |
| `23_pilatus_all_frames_of_a_scan.png` | Pilatus tab with ALL frames of a long scan selected: the movie (F69; before 2026-11-24, 10 small tiles) | Scan 11: all 40 frames selected (drawing took 0.5 s offscreen) |
| `23b_pilatus_all_frames_reflectivity_series.png` | Pilatus tab with all frames of the four reflectivity scans selected | Scans 6-9: all 96 frames selected |
| `30_reflectivity_empty.png` | The Reflectivity tab (page and its controls) with nothing loaded | No SPEC file; crop of the tab widget |
| `31_refpatch_dialog_first_join.png` | Ref Patch window (opened by Pilatus > Ref Patch), first join | Scans 6-9 all frames; Ref Patch clicked |
| `31b_refpatch_main_window_behind.png` | Main window while the Ref Patch window is open | Scans 6-9; Ref Patch open at first join |
| `31c_refpatch_dialog_second_join.png` | Ref Patch window at the second join | Scans 6-9; first join accepted |
| `32_reflectivity_after_patch.png` | Reflectivity tab after Ref Patch (finished on the patched curve) | Scans 6-9 patched, all three joins accepted; sub-tab: Ref |
| `33_reflectivity_norm_ref_subtab.png` | Reflectivity tab, "Norm Ref" sub-tab (page and controls) | Scans 6-9 patched |
| `33_reflectivity_ref_subtab.png` | Reflectivity tab, "Ref" sub-tab (page and controls) | Scans 6-9 patched |
| `34_compare_tab.png` | Compare tab (F80, F105): the reflectivities saved in the workbook, overlaid | Scans 6-9 patched and saved automatically; Compare tab shown |
| `40_gid_controls_before_patch.png` | Pilatus tab with scans 11-12 selected: the GID drop-down (GID, GID Patch, ..., Worksheet) and neighbours | Scans 11-12 all frames selected |
| `40b_gid_dropdown.png` | The GID drop-down opened | Pilatus tab, scans 11-12 |
| `41_gid_patch_pinhole.png` | Whole window after GID Patch of scans 11-12 (pinhole mode, the default) | Scans 11-12 all frames; GID drop-down > GID Patch; tab now: Pilatus |
| `42_gid_worksheet_window.png` | GID worksheet (GID drop-down > Worksheet), docked on the right (F95 B10) | After GID Patch of scans 11-12 |
| `43_gid_form_factor_dialog.png` | Form Factor window (GID drop-down > Form Factor) | After GID Patch of scans 11-12 |
| `50_burn_gid_trends_view.png` | Burn-test window, Trends tab, GID burn (scan 15) | Scan 15 (20 frames at one position) selected; Pilatus > Burn Test |
| `50b_burn_main_window_behind.png` | Main window behind the burn-test window | Scan 15, burn window open |
| `51_burn_legacy_ref_view.png` | Burn-test window, legacy plot tab after its Reflectivity button | Scan 15; the legacy REF burn analysis button clicked (on GID data) |
| `52_burn_legacy_gid_view.png` | Burn-test window, legacy tab after the GID combo | Scan 15; legacy GID burn analysis chosen: Intensity |
| `53_burn_ref_series_selected.png` | Pilatus tab, a synthetic burn series (21 frames, one spot) selected | Synthetic burn dataset (reflected intensity decaying, tau 400 s); all frames |
| `54_burn_ref_trends_view.png` | Burn-test window, Trends tab, reflectivity burn (synthetic) | Synthetic burn dataset; Pilatus > Burn Test |
| `55_burn_ref_legacy_view.png` | Burn-test window, legacy tab after the Reflectivity button (synthetic) | Synthetic burn dataset; legacy REF burn analysis |
| `60_cuts_empty.png` | The Line/Area Cuts tab (page and its controls) with nothing loaded | No SPEC file; crop of the tab widget |
| `60_cuts_gid_qz_cut.png` | Line/Area Cuts tab with a cut of the patched GID map (Qz 0.0:0.2 vs Qxy) | GID patch of scans 11-12; Pilatus tab: Q H Cut 0.0:0.2, Line/Area Cuts clicked |
| `61_cuts_after_peak_fit.png` | Line/Area Cuts after Fit peaks | Same cut; Fit peaks clicked |
| `62_cuts_fit_options_dialog.png` | Fit options of the cut fits, docked on the right (F95 B10) | Cut plotted and fitted |
| `63_cuts_gid_qxy_rod.png` | Line/Area Cuts with a second cut added (Qxy 1.25:1.35 vs Qz, the Bragg rod) | Same map; second cut added to the plot |
| `70_mca_empty.png` | The MCA tab (page and its controls) with nothing loaded | No SPEC file; crop of the tab widget |
| `70_mca_one_spectrum.png` | MCA tab, whole window, one spectrum | Synthetic XFNTR data (9 getandsave_mca scans, Qz 0.012-0.036); frame 5 selected |
| `71_mca_all_spectra.png` | MCA tab with all spectra selected | Synthetic XFNTR; all 9 spectra selected |
| `72_mca_sum_all_integral.png` | MCA tab after Sum All over the fluorescence window (integral vs Qz) | Synthetic XFNTR; window 5.6:7.2 keV; Sum All; whole window |
| `72b_mca_integral_vs_qz.png` | MCA tab, integral vs Qz | As before; x axis set to Qz |
| `73_mca_peak_fit_dialog.png` | MCA > Fit window (peak fit of one spectrum) | Synthetic XFNTR; frame 5; Fit clicked |
| `74_mca_peak_fit_dialog_fitted.png` | MCA peak-fit window after Fit | Range 5.6:7.2, guess 6.3 keV |
| `75_mca_fit_lines_result.png` | MCA tab after Fit lines (fluorescence result) | Synthetic XFNTR; all spectra; Fit lines clicked |
| `76_mca_fit_options_dialog.png` | MCA Fit options, docked on the right (F95 B10) | Synthetic XFNTR |
| `77_mca_merge_dialog.png` | MCA > Merge dialog (merge window) | Synthetic XFNTR; after Sum All |
| `80_plot_empty.png` | The Plot tab (page and its controls) with nothing loaded | No SPEC file; crop of the tab widget |
| `80b_plot_two_files.png` | Plot tab, whole window, two files from disk plotted | Files: a patched NX reflectivity export (if available) and a synthetic peak (Qz, I, error) |
| `81_plot_peak_fit_window.png` | Plot > Peak Fit window | Plot tab; files plotted |
| `81b_plot_peak_fit_window_fitted.png` | Plot > Peak Fit window after Fit | Default start values |
| `81c_plot_gradient.png` | Plot tab after Gradient | As above; Gradient clicked |
| `81d_plot_scale_window.png` | Plot scale window | Plot tab |
| `82_2dplot_empty.png` | The 2D_Plot tab (page and its controls) with nothing loaded | No SPEC file; crop of the tab widget |
| `83_2dplot_map_file.png` | 2D_Plot tab, whole window, a synthetic x y z map plotted | Synthetic 30x30 Gaussian map file added with Add Files |
| `90_dialog_gioxs.png` | GIOXS window (Pilatus > GIOXS) | Scan 11 frame 1 as data, scan 12 frame 1 as background |
| `91_gisaxs_show.png` | Whole window after GISAXS drop-down > Show GISAXS | Scan 11 frame 1 with a background; tab: Pilatus |
| `92_dialog_scan_info.png` | Scan info window (double-click a scan in the scan list) | Scan 11 selected |
| `93_dialog_g_l2.png` | Calculations > G_l2 window | Scans 5 and 13 (sample height) fitted on SpecPlot |
| `94_dialog_g_l3.png` | Calculations > G_l3 window | Scans 5 and 13 (sample height) fitted on SpecPlot |
| `95_dialog_preferences.png` | File > Preferences window | Defaults |
| `96_pane_messages.png` | Messages pane (bottom dock) | Two example messages posted (not from a real action) |
| `97_pane_script.png` | Script pane (bottom dock) | After the reductions run in this session (the script records them) |
| `98_pane_errors_legacy.png` | Errors pane (bottom dock), Legacy error model | Defaults |
| `98b_pane_errors_budget.png` | Errors pane (bottom dock), Budget error model (extra monitor controls appear) | Errors combo set to Budget |
| `99_menu_calculations.png` | Menu bar > Calculations menu | Menu popped up offscreen |
| `99_menu_file.png` | Menu bar > File menu | Menu popped up offscreen |
| `99_menu_help.png` | Menu bar > Help menu | Menu popped up offscreen |
| `99_menu_tools.png` | Menu bar > Tools menu | Menu popped up offscreen |
| `99_menu_view.png` | Menu bar > View menu | Menu popped up offscreen |

### Menus (item lists, from the actions of each menu)

- **File**: Open Spec File, Preferences..., Give up the workbook's write access, Ask for the workbook's write access, -, Quit
- **Calculations**: g_l2, g_l3, abs ratio
- **Tools**: All tools…, -, Burn tests, Reflectivity patching, GID and pinhole geometry, Monitor, scans, SPEC files, Fluorescence (MCA), Synthetic data sets, The reader's window and manual, Made elsewhere
- **Help**: Documentation, About
- **View**: Messages, Script, Errors, -, Residuals above fits

## Observations

Factual notes from looking at the images; "as seen" means in these offscreen shots (Qt offscreen, matplotlib 3.11.2, DejaVu/Inter-like
fonts), where font metrics may differ a little from the owner's desktop.

**Window**
- Minimum width is about 2266 px (`minimumSizeHint`); on a laptop screen the window cannot be shown whole.
- The Apex (Bruker CCD) tab was hidden by `setTabVisible(1, False)` but still existed with its controls (Reflectivity,
  Line/Area Cuts, axes, cmap, cut direction). **Removed 2026-11-23** (owner, Q14), with `14_apex_tab.png`.
- The status bar is a single thin line; the bottom dock has tabs Messages / Script, and Errors only once its View entry is ticked.
- The Script pane, once shown, holds mostly empty space; the two header lines are all it shows before a reduction.

**Left panel (`10_*`, `00_overview_annotated.png`)**
- Scan-list rows show the raw `#S` line, clipped at the right edge, two text lines high; the horizontal scroll bar is needed to read a command.
- Frame-list rows clip ("Qx=1.3116Ab...") and mix columns of different width; "Absorber Ratio: ... from E" is clipped ("from Exp...").
- The label above the frame list changes with the detector ("Pilatus:", "Vortex:", "Detector:"); "Series: none found" is greyed when there is no series.
- The Background list is large and empty in every shot except GIOXS; the buttons under the lists ("Select All", "Remove") sit at the very bottom, far from the lists they act on.

**Pilatus (`2x`)**
- With all 40 frames of scan 11 selected only 10 are drawn (`23_*`): a 4 x 3 grid of tiny images whose titles ("F #0") and axis labels are larger than the images; every colour bar reads 0.0e+00 to 5.0e+00, so nothing can be seen in the frames. The plot title (file name) overlaps the first row of titles.
- Min (%) / Max (%) fields show clipped long numbers (e.g. "...2074201269173626").
- Bottom row of the tab is dense: Log Int, Pinhole, Movie, Min/Max, Merge Same Qzs, Low Qz Corr., Reflectivity, Ref Patch, HSlits, GID, GISAXS, Burn Test, GIOXS, cut direction, Int Range, Line/Area Cuts: eleven kinds of control in one strip with no grouping.
- After GID Patch the map stays on the Pilatus tab (`41_*`): the 2D map, two integrals and a Qz-binned panel with titles ("Integrated over Qz", "Qz-binned") overlapping the panel above, x tick labels running together ("1.201.251.301.35"), and the x label cut off at the canvas bottom.

**Reflectivity and Ref Patch (`3x`)**
- The Ref Patch window is small and modal-like; the main window keeps showing the Pilatus tab behind it (`31b_*`).
- After the last join the window switches to the Reflectivity tab; the sub-tabs Ref and Norm Ref carry the same controls.

**Line/Area Cuts (`6x`)**
- Plot titles are clipped at the right ("S# 11, 12" cut off) and the x label is cut off at the canvas bottom (`60_*`, `63_*`).
- A range outside the map (Qxy 1.40:1.50 on the scans 11-12 map, which covers about 1.18-1.38) gives the message "Please enter the appropriate integral type and range" (a bare `except` in `updateCutData`), which does not say the range is outside the data. The tool uses 1.25:1.35 for the second cut.
- Fit peaks on the Qz cut of the GID map finds no peak ("no peak stands 5.0 sigma above the background"); correct, but the shot shows the unchanged plot.

**Burn tests (`5x`)**
- The Trends view is dense in a small window (1575 x 595): y labels of the three panels overlap each other and the tick labels, right-axis labels overlap, the title overlaps the legend, the text summary on the right is cut off after "best: dbl" (`50_*`).
- "REF" (legacy) on GID data answers "It is not a REF burn test. Please use GID burn test button" and the legacy tab then shows the GID/REF controls only at the bottom of the window; the legacy tab and the Trends tab are two views of the same job.
- Fluorescence burn: not reachable. The Burn Test button is Pilatus-only (`pilBurnTest` requires `det == 'Pilatus'`); no MCA path exists.

**MCA (`7x`)**
- "X-axis" label is clipped ("X-axi"); labels "Calib=" and the polynomial fields form a cramped first row.
- The nine spectra are drawn in many colours with marker-sized circles that merge into thick bands; the right-hand column has a large empty list (MCA files) with its Add Files / Remove Files above.
- The integral plot shows a legend "#0" with an errorbar sample that is not one of the points plotted.

**Plot, 2D_Plot (`8x`)**
- 2D_Plot raises `AttributeError: module 'matplotlib.cm' has no attribute 'get_cmap'` at `update2dPlotPlot` (mainwindow.py:7718 on 2026-11-22, 7799 after the covariance merge) with matplotlib 3.11.2 (removed in 3.9), so the plot stays empty (`83_*`). Real bug in this environment; requirements pin should be checked. **Fixed 2026-11-23** (`83_*` retaken: the map is drawn).
- 2D_Plot has Label Size, Tick Size, Point Density Factor and an "Updata Interpolation" button (typo).
- Min/Max fields clipped here too.

**Dialogs, panes, menus (`9x`)**
- The absorber-ratio dialog could not be captured (no scan with an Absorber scan variable in NX or in the synthetic sets).
- Menus have few entries: File (Open Spec File, Preferences, Quit), Beamlines (two checkable entries; **removed 2026-11-23**, owner Q14, with the Command line row), Calculations (g_l2, g_l3, abs ratio: three lowercase names), Help, View (panes). Everything else is in the tab strips.

**Reruns (2026-11-23)**
- The tool's working folders now have fixed names (`<tmp>/lss_screens/...`): their random names appeared in plot titles, legends and the status bar and changed 11 otherwise identical images on every rerun. Between two reruns only `50b_*`, `91_*` (the Messages strip's clock time) and `96_*` (message timestamps) still differ.
- A finished "Reading Scan #1, 100 %, Abort" progress window from an earlier step sometimes appeared late, and was caught as `81d_plot_scale_window.png` with the real window as `81d_*b.png`. The tool now leaves progress windows out. Not reproduced by opening the NX file and waiting 6 s; the SPEC reader keeps the window referenced (`spec_routines.py:236`), so Qt's show-if-slow timer could show it after reading (cause guessed; TODO area I).
- Reflectivity screenshots (`30_*`, `32_*`, `33_*`) retaken for the "+ covariance" box after the reflectivity Save.
- Ref Patch window (`31_*`, `31c_*`) and Reflectivity tab (`30_*`, `31b_*`, `32_*`, `33_*`) retaken 2026-11-24 for F96: Back, Cancel and the join table in the window; the line under the Reflectivity plot.
- Pilatus (`21_*`, `22_*`, `23_*`, `23b_*`) and Reflectivity (`30_*`, `32_*`, `33_*`) screenshots retaken 2026-11-24 for the ROI close-up panel (F71, F97): beside the frame on the Pilatus tab, in the close-up on the Reflectivity tab.
- `99_menu_view.png` retaken 2026-11-24 for F74 (View > Residuals above fits). The Pilatus screenshots show no saturation cue (F97): no NX frame here is above 1e5 counts/s. **Most whole-window screenshots now differ from a rerun** (changes by several sessions since 2026-11-23, not checked one by one); they are left for a full retake.
