# Assessment A: left panel, menus, panes, SpecPlot, Pilatus, Line/Area Cuts, 2D_Plot, Apex

Phase 1a, 2026-11-22. The controls are listed in `inventory/left_panel.yaml`, `menus.yaml`,
`panes.yaml`, `specplot.yaml`, `pilatus.yaml`, `cuts.yaml`, `plot2d.yaml` and
`apex.yaml`. Questions for the owner are in `questions/inventory_a.md` (Q-UI-A*).

**How each finding is known.** **[seen]** means I saw it in a running window: offscreen Qt,
1600 x 1000 logical px, NX school `20260923`. I selected S# 4 (sh scan), S# 3 (reflectivity
frames) and S# 11 (GID frames), added a background, made a Pix H cut, ran Fit peaks, Movie,
Show GISAXS and the GID menu, and triggered every menu item. **[read]** means I only read it
in `mainwindow.py` / `mainwindow.ui`. The screenshots in `screens/` (other agent) show the same
states: `10_leftpanel_series_chosen.png`, `21b_pilatus_tab_controls.png`,
`23_pilatus_all_frames_of_a_scan.png`, `14_apex_tab.png`.

## Decided requirement D59 (owner, 2026-11-22): the Script pane

> "The 'script' terminal panel shouldn't compete with data selection and it should be hidden
> by default."

- **Today [seen]:** `initScriptPane` hides the dock. But `scriptLine` calls `scriptDock.show()`,
  and opening a SPEC file writes `exp = Experiment(...)`. So the pane is visible from the first
  file on. It is a bottom `QDockWidget`, tabbed with Messages and Errors, and spans the full
  window width. It is about 200 px tall. The scan list above it shrinks to 100 px, which is two
  scans, because each row is two lines tall (see the left panel below).
- **Requirement:**
  - hidden by default;
  - never shows or raises itself (`scriptLine` only appends);
  - opened from View > Script;
  - placed so that it takes no height from the left selection panel.
- **What the layout allows [read]:**
  - The left panel is not a dock. It is the first pane of `splitter_3` inside the central
    widget, so every bottom dock spans under it.
  - **(a)** Make the left panel a left dock and call
    `setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)`. Bottom docks then sit under the
    tab area only.
  - **(b)** Put the panes in a vertical splitter under `PlotWidget`, inside the right pane of
    `splitter_3`, instead of using docks.
  - **(c)** Use a right dock area, or a floating window that remembers its geometry.
  - (a) keeps Qt's dock features and fits phase 1b best. The Command row (`commandLineEdit`)
    also spans both columns today and has the same problem (see Panes).
- Whether Messages and Errors follow the same rule is Q-UI-A1.

## Left panel

**Grouping**
- The panel holds five stacked units with no group boxes: file, scans, absorbers, frames,
  background. Only the frame list has a title, and that title is the detector-name label
  **[seen]**.
- The absorber factor (`AbsFacLineEdit`, `absFacEnergyCheckBox`) sits between scans and frames.
  It is controlled from three other places: File > Preferences (calibrated foils), Calculations
  > abs ratio (measure the ratio; the result is not fed back to the field **[read]**), and Ref
  Patch (measures the scale instead) **[read]**.
- "Sum All" (`gixSumCheckBox`) is an image-display/reduction option (average frames at one Qz
  for cuts, GISAXS, burn). It sits in the frame-selection row. It is reset on every scan change
  **[read]** and is not used for MCA spectra **[read]**.
- The background block (button, factor, Ignore -ve, list, Select All, Remove) serves cuts,
  GISAXS, GIOXS and GID maps on Pilatus only **[read]**. It takes about a third of the panel
  height even when empty, which it is for most workflows **[seen]**.

**Consistency**
- "Absorber Ratio:" is the label. The tooltip and messages say "absorber factor" **[seen]**.
- Two "Select All" checkboxes, for frames and for background, look identical. Both are
  checkboxes used as action buttons that untick themselves **[seen/read]**.
- "Background" reads as a title, but it is an action that replaces the background list
  **[seen]**.
- Other labels: "Fac:", "Ignore -ve".
- Only the code-built controls have tooltips: Live, Series, Whole series, from E. The .ui
  controls have none, apart from the scan list's "Spec Scans" **[seen]**.

**Visual cues**
- **Scan list rows [seen]:** the series tint (alpha 40) is faint and disappears under the
  selection highlight. There is no legend for the colours (it exists only in the Series
  tooltip). Each row carries the `#S` line's newline, so every scan takes two text lines.
- **Series combo [read]:** it shows the chosen series while the selection matches it. A
  series selected by clicking a scan with "Whole series" on is not shown there.
- **Read-only fields [seen]:** while "from E" is ticked the absorber field is read-only, but it
  looks the same as an editable field. "cal" is the only cue that the calibrated foils are in
  use.
- **Background [seen]:** frames in the background list stay there after the scan changes. Only
  the selected ones are subtracted. Neither the image nor the frame list shows that a
  background is subtracted.
- **Live mode:** only the tick and a 5 s status message show it **[seen]**. Nothing shows when
  it stops by itself **[read]**.
- **Image list [seen]:** the Abs column is cut off at the default width.

**Missing here?**
- An Open button: Update Specfile and Live are here, Open is only in the menu.
- The output folder: exports and the workbook go there, but it is shown nowhere.
- A frame count, and "showing 10 of 11": the Pilatus tab silently draws the first 10
  **[seen]**.

**Proposals**
- Group boxes:
  - **File:** name with the folder in the tooltip, Open, Update, Live with a coloured badge
    while on.
  - **Scans:** typed range, Series with its state, Whole series, list.
  - **Frames:** detector label with a count, Select All as a button, list.
  - **Background:** collapsible, collapsed when empty.
- Move the absorber factor into the reduction controls, or show it as a read-only badge
  ("absorbers: cal / 1.4247 per unit") whose tooltip says where it comes from. Put "from E" and
  the Preferences foils together.
- Strip the newline from scan rows. Make the tints stronger, with a small legend in the
  tooltip, and keep the tint visible on selected rows (a coloured left bar instead of a
  background colour).
- Rename: "Absorber factor", "Use as background", "Clip negatives", "Average frames" (for Sum
  All, if the owner agrees: Q-UI-A3).

## Menus

- **Dead controls [seen]:**
  - File > Quit does nothing (no `.connect`; the window stayed open).
  - Help > Documentation does nothing.
  - Beamlines > APS-15IDC only re-selects the one beamline; APS-9IDC is hidden. The whole
    Beamlines menu is defunct (owner, 2026-11-17).
- **Order [seen]:** File, Beamlines, Calculations, Help, View. View is appended in code, after
  Help. The usual order is File, View, ..., Help.
- **Calculations [read]:** g_l2 and g_l3 fit the SpecPlot fit centres, so they need scans
  plotted in SpecPlot first. Abs ratio needs an absorber scan. The names are cryptic and lower
  case, and nothing says what they need. They belong to alignment beside the SpecPlot fit, and
  abs ratio beside the absorber factor.
- No keyboard shortcuts at all **[read]**. No recent files. No entry for the workbook (open
  it, show the Saved sheet).

**Proposals**
- Connect Quit and Documentation, or remove them. Documentation could open
  `docs/manual/` or `docs/SCRIPTING.md`.
- Remove Beamlines, or fold it into About.
- Rename the Calculations items ("Fit g_l2 (crystal-sample) from sh centres...", "Absorber
  ratio from absorber scan...") with tooltips. Also offer them as buttons on SpecPlot when a
  suitable selection exists (phase 3 hook).
- Order: File, View, Calculations, Help. Add Ctrl+O and Ctrl+Q.

## Panes, Command line, status bar

**Messages [seen]**
- Each message calls `show()`. That does not bring Messages to the front of the dock tab
  group: after Fit peaks the result went to Messages while Script stayed in front.
- Warnings and info look the same.
- The title ("Absorbers", "Peak fit") goes to the log but not to the pane.

**Errors**
- The error model changes every error bar. Its only control is in a hidden pane opened from
  View **[seen]**.
- Nothing else in the window shows Legacy vs Budget **[seen]**. Whether exports record it was
  not checked.
- The pane shows a long description in plain text, against rule 9 **[seen]**.

**Command line**
- It is empty during normal selection and after a line cut **[seen]**. It is filled only by
  Ref Patch, GID, GIOXS, burn and MCA sums/fits **[read]**.
- It is editable, but typing does nothing: exports use `self.command`, not the field
  **[read]**.
- It is an older, non-runnable twin of the Script pane, and takes a full-width row.

**Status bar**
- It is the only place where "Saved automatically to ... R0002 line cut ... v2" appears, and
  that message is transient **[seen]**.
- It has no permanent indicators.

**Proposals**
- Apply D59. Make Messages raise itself on warnings only, and show a counter badge for unread
  info messages. Colour warnings.
- Permanent status-bar indicators, each with a tooltip:
  - error model (Legacy/Budget, click to open Errors);
  - monitor normalisation (counts, /gain, /photon);
  - absorbers (cal / value);
  - Live on/off;
  - workbook name and last auto-save.
- Replace the Command row with a read-only "last action" in the status bar or in the Script
  pane, or drop it if the owner agrees (Q-UI-A4).

## SpecPlot

- **Grouping [seen]:** X, Y1, Y2, N, / gain, / photon are spread across the full width in one
  row with large gaps, and the X combo is truncated ("Sample_"). The display row (LogX, LogY,
  Grid, Legend, Point #, legend location) and Export/Save sit under the plot. "Point #" sits
  between Legend and its location combo.
- **Consistency:**
  - The N checkbox has no text; its "N:" label is a separate QLabel **[seen]**.
  - MCA calls the same choice "Normalized by", with a fixed list **[read]**.
  - The legend-location list repeats "lower right" and lacks "lower left". The same list is on
    Cuts, Reflectivity and MCA; Plot has it right **[read]**.
- **Visual cues:**
  - The fit result (Peak, Cen, FWHM or edge widths) is only in the two-line title, and the
    first line is clipped **[seen]**.
  - The fit cannot be copied and does not go to Messages. Yet g_l2/g_l3 depend on it.
  - "/ gain" and "/ photon" are global. They also change Pilatus cuts, GID and frames, but no
    copy of them is visible on the Pilatus tab **[read]**.
- **Missing here?**
  - A choice of fit shape (peak, edge, plateau, none) when the automatic choice is wrong
    **[read]**.
  - A residuals panel (F74, later).
  - Save is manual here, while cuts, ref, GID, MCA and burn save automatically **[read]**.
- **Proposals:**
  - Compact "Columns" group: X, Y1, Y2, then "Normalise by [Monc] / gain / photon" as one
    phrase.
  - Fit result in a small read-only panel or legend entry, with "Copy" and "Use for g_l2/g_l3"
    actions.
  - Display options in a "View" row shared in style with Cuts.
  - Export and Save always in the same corner on every tab.

## Pilatus

- **Grouping [seen]:**
  - The action row under the image holds 15 controls from six workflows, with no grouping:
    - reflectivity: Merge Same Qzs, Low Qz Corr., Reflectivity, Ref Patch;
    - GID: HSlits, GID menu;
    - GISAXS menu;
    - burn: Burn Test;
    - GIOXS;
    - cuts: direction, range, Line/Area Cuts.
  - Geometry options are split: DB Pos and SD Dist are in the top row, Pinhole is in the
    display row next to Log Int and Movie.
  - Merge Same Qzs and Low Qz Corr. are Reflectivity/Ref Patch options. They are read only when
    those buttons are pressed and have no visual link to them **[read]**.
- **Consistency:**
  - "Min (%)" and "Max (%)" label sliders in percent, but the fields beside them hold
    intensities (observed -2.0 and 1.0) **[seen]**.
  - Range syntax: "min:max" here, "x,y" for DB Pos and the Reflectivity slits, "1:1000" in MCA
    Range.
  - Units glued to labels: "SD Dist(mm)", "HSlits(Pixels)". HSlits is in fact a column count.
  - Two action menus are combo boxes (GID, GISAXS). They keep the last action as their text
    (observed "Show GISAXS"), so they look like modes **[seen]**.
  - "Reflectivity" and "Line/Area Cuts" buttons carry the names of the tabs they open.
  - Colour-map lists differ from 2D_Plot and Apex ("rainbow" vs "spectral").
  - Only Pinhole has a tooltip.
- **Visual cues:**
  - **Frame grid [seen]:** at most 10 frames are drawn, without notice. Titles, labels and
    colour bars overlap. The default colour scale saturates (uniform yellow).
  - **Geometry [seen/read]:** no overlay of the direct beam, ROI or cut band. Pinhole on/off,
    and pinhole vs legacy GID patch, show only as the tick.
  - Background subtraction and Sum All are not shown on the image.
  - **Movie [read]:** it blocks the window (sleep 0.5 s per frame), has no stop, and leaves
    Axes on Q.
- **Missing here?** (The image-display requirements themselves are in `image_display.md`.)
  - One line-cut interface on this plot and the others (F68), with the band drawn on the
    image.
  - Save to workbook for GISAXS (GID has it).
  - Sticky display preferences (F70).
  - A copy of "/ gain, / photon".
  - A Movie as the default view (F69).
- **Defunct or duplicated [read]:**
  - Bad-pixel correction exists three times: here (iterations and factor), on the Reflectivity
    tab (`refBPCFacLineEdit`), and on Apex.
  - Pinhole exists here and in the GID worksheet.
  - HSlits exists here and as the worksheet's Columns (mirrored).
- **Proposals:**
  - A tool row grouped by workflow, each group a titled box or toolbar section:
    - **Reflectivity:** Reflectivity, Ref Patch, with Merge/Low Qz moved under it or into Ref
      Patch settings;
    - **GID:** columns, Pinhole, GID actions as a QToolButton menu;
    - **GISAXS:** a QToolButton menu;
    - **Burn test;**
    - **Cuts:** direction, band, Make cut.
  - Grey out or hide groups that do not fit the selected series kind (phase 3 hook; series kind
    is already known).
  - "Geometry" box: DB from SPEC, DB, distances (SD and S4), Pinhole.
  - "Display" box: Axes, Aspect, colour map, Log, limits. Label the limits fields as values
    and the sliders as percent, or drop the percent.
  - QToolButton menus instead of combo boxes used as menus.

## Line/Area Cuts

- **Grouping [seen]:** the cut is defined on the Pilatus tab (direction, band) and shown here.
  To change the band the user goes back and forth. Clear Graph, Export and Save are top right;
  Fit peaks and Fit options are bottom right next to the legend location.
- **Consistency:** "Offset Factor:" is a checkbox whose text labels the next field (same
  pattern as DB Pos and MCA Offset). Error bars are optional here and always drawn on
  SpecPlot.
- **Visual cues:**
  - The x axis of pixel cuts is unlabelled **[seen]**.
  - Fit numbers go to Messages only. On screen there are just the dashed fits and dotted
    centres, and the Messages tab may be hidden **[seen]**.
  - Clear Graph clears the picture but not the data; Export still writes the cuts **[read]**.
  - Auto-save happens with only a transient status message **[seen]**.
- **Missing here?**
  - The cut definition, or at least a read-only summary of it with a "change" link.
  - The source frame, with the band drawn.
  - Cuts of non-Pilatus maps (2D_Plot, GID map), so far possible only if the map is on the
    Pilatus tab **[read]**.
- **Proposals:**
  - One cut interface (F68): a dock or side panel shared by Pilatus, the GID map, the
    Reflectivity ROI and 2D_Plot, with direction, band (typed or dragged on the image) and
    defaults by series kind (reflectivity: Pix V through the specular; GID: Q H at the Qz of
    interest, ...).
  - The Cuts tab keeps the plot, the fit results table, Export and Save.

## 2D_Plot

- Reads x y z text files and draws only the first selected file **[read]**. No cut, no export,
  no tooltips **[seen]**.
- Typo "Updata Interpolation" **[seen]**.
- **Wiring [read]:** the sliders are connected twice. Tick Size reloads the file and resets
  the limits. `imageMax`/`imageMin` are shared with Pilatus.
- "spectral" is not a current matplotlib colour-map name. It was not run.
- **Proposals:**
  - Same Display box as Pilatus.
  - "Send to 2D_Plot" from GID and GISAXS results instead of save and re-add.
  - Cut interface (F68).
  - Ask whether the interpolation is used (Q-UI-A7).

## Apex (defunct)

- The tab is hidden at start **[seen]**. All 18 of its controls are unconnected **[read]**.
- **Two remnants still matter [read]:**
  - `gixCMapComboBox` (hidden, "jet") sets the colour map of the Reflectivity tab's ROI image
    (`refAnalyze`).
  - `gixMplWidget` is cleared in `clearAll`.
  - The left panel's "Sum All" is still named `gixSumCheckBox`.
- **Proposals:** move the ROI colour map to the shared Display settings, rename
  `gixSumCheckBox`, then delete the tab from the .ui. Opening a Bruker scan already says .sfrm
  is unsupported.

## Cross-cutting

- **Button vs checkbox:** Select All (both lists) are checkboxes acting as buttons. GID and
  GISAXS are combo boxes acting as menus. Several checkboxes double as labels (DB Pos, Offset
  Factor, Calib=).
- **Export/Save placement:** SpecPlot bottom right, Cuts top right, GID inside a combo,
  GISAXS inside a combo with no workbook Save.
- **Log naming:** LogX/LogY on 1D plots, "Log Int" on images. Fine, if consistent in
  placement.
- **Units:** in the label with parentheses ("SD Dist(mm)", "Monitor sigma (%)"), in a tooltip
  only ("Dark sigma"), or absent ("Fac", "Int Range").
- **Ranges:** "a:b" vs "a,b". Neither is explained on screen or in a tooltip.
- **Enabled state:** almost every action is always enabled and answers with a "Please select
  ..." message when it cannot run **[seen/read]**. Disabling with a tooltip saying what is
  needed would be cheaper for the user.
