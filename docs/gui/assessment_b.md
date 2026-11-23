# Assessment B: Reflectivity, MCA, Plot, and every dialog (phase 1a)

Inventory: `inventory/reflectivity.yaml` (39 entries), `mca.yaml` (34), `plot.yaml` (19),
`dialogs.yaml` (158). Questions: `questions/inventory_b.md`.

How it was seen, 2026-11-22: **[seen]** = observed in an offscreen window (NX school scans 6
(Analyze), 6–9 (Ref Patch), 14 (burn); synthetic MCA from `tests/synth.py`, scan 3), with
screenshots taken for this assessment only; **[read]** = from the code or `.ui` files only.
Nothing in the application was changed.

## 1. Reflectivity tab

### Grouping
- **Reflectivity reduction is split across three places.** The Pilatus tab holds the two
  entry buttons (Reflectivity = Analyze path, Ref Patch = patch path), Low Qz Corr., Merge
  Same Qzs, bad-pixel iterations and factor, the colour map; the Reflectivity tab holds the
  ROI (Slit, BG Dir, BG Offset) and the result; File > Preferences holds the patch method, the
  known-ratio rule and the foils. [read; seen for the jumps between them]
- **The ROI fields serve three workflows but live on one tab.** Slit, BG Dir and BG Offset are
  read by Analyze, by Ref Patch and by the burn test (Trends and Legacy REF), none of which
  shows them. A burn test run from the Pilatus tab silently depends on fields on the
  Reflectivity tab. [read]
- **Two reductions share one layout.** The top half (Qz list, Search Win, Cen, Analyze, Accept,
  Analyze All, ROI close-up, Bad Pixels) is used only by the point-by-point Analyze path; after
  a Ref Patch it still shows the last Analyze state or nothing. [seen]
- The overlay file lists (Add/Remove Files) sit beside the readout row, with no label. [seen]

### Consistency
- Output fields Q, R, R_Err, %R_Err are editable line edits. "R" there is the net ROI intensity
  (2.2e7 for NX scan 6, frame 0), not the normalised R of the plot below. [seen]
- Labels without units: Slit (pixels), Search Win (× slit), Qc and Qoff (1/Å). Only BG Offset
  gives one. [seen]
- The legend-position combos on Reflectivity and MCA list "lower right" twice and no "lower
  left"; the third item puts the legend lower left. Plot's list is right. [seen list; read effect]
- Analyze draws the corrected ROI with the hidden Apex tab's colour map and the uncorrected one
  with the Pilatus map. [read]
- Delete and Accept have the same names as MCA buttons that do other things. [seen]

### Visual cues
- **Nothing says which reduction made the curve** (Analyze or Ref Patch), which **patch method**
  (joint or legacy) or **error model** (Legacy or Budget) was used, or which joins used the
  known ratio. The method shows only in the Script pane (`method=`) and the workbook recipe. [seen]
- **Dropped points leave no trace** once Next is pressed: not marked on the curve, not in the
  lists; only the Script line's `drops=` keeps them. [seen]
- **Which scans the curve came from**: the plot title takes the left panel's selection at plot
  time (and is clipped at the top of the canvas); the workbook Save does the same. Observed: a
  scan-6 curve saved after selecting scan 11 was stored as scans "11". [seen]
- The Ref sub-tab is the default though Export, Save and the plot use Norm Ref; the Norm Ref
  list has its header as a data row, and stays empty without a message when no point lies
  below Qc. [seen]
- Automatic saving is announced only in the status bar for 8 s; in the Analyze path each Accept
  is a "reduction", so one workbook version per accepted point (3 Accepts → R0001–R0003). [seen]

### Missing here or defunct
- **Defunct:** `refBPCFacLineEdit` ("Bad Pixel Correction fac") is read and never used;
  `refBadPixListWidget` is only ever cleared. [read]
- No undo for Delete or for drops; no list of the join factors (GID has a join table in its
  worksheet; reflectivity has none). [seen]
- No ROI close-up of the patched frames (F71). [seen]
- LogY is off by default, though reflectivity is nearly always viewed on a log scale. [seen]
- Norm Factor's field is not connected: a new value acts only after a toggle. [read]
- Every replot writes `temp_ref.txt` into the output folder. [seen]
- Comments typed for Analyze points reach `temp_ref.txt` only, not the export or workbook. [read]
- The Analyze path is not scriptable (Script pane says so). [read]

## 2. MCA tab

### Grouping
- **Two fit systems side by side**: legacy Fit / Fit All / Accept (peakfit.ui, Gaussian or
  Lorentzian) and Fit lines / Fit options... (lss_core.peaks). Three fields can set a fit range:
  the tab's Range, the options dialog's x range, the legacy panel's Fit range. [seen]
- Display (LogX/LogY/Grid/Legend, Offset Factor) and reduction (Sum All, Fit lines, Merge,
  X-axis) controls are mixed in one right-hand column with no grouping. [seen]
- **The detector elements summed** (XFNTR: centre; EXAFS: all) are chosen in File >
  Preferences, away from the tab, with no cue on the tab. [read]
- Fluorescence burn tests (owner's priority 1, `burn-fluo`) have no place in the GUI or in
  lss_core; the burn window takes Pilatus frames only. [read]

### Consistency
- The Range default 1:1000 is in channels while the axis is calibrated (keV) by default: the
  marker at 1000 squeezes the spectrum against the left edge, and Sum All silently clips to
  1.0:2.56. [seen]
- "Normalized by" offers a fixed Monc/Monb/Mond/None, while SpecPlot takes monitors from the
  scan's columns. [read]
- "Offset Factor" is a display waterfall but reads like a data correction. [seen]
- The X-axis label is truncated ("X-axi"); Frame is the default although XFNTR is vs Qz and
  EXAFS vs energy, and the choice decides the exported column. [seen]
- Integral plot: legend "#0" always on, no log/grid/legend controls (the spectrum plot has them). [seen]

### Visual cues
- Nothing says whether the integral rows came from Sum All, Fit lines or legacy fits, or were
  merged or deleted; the command line at the bottom is the only trace. [seen]
- The y label stays "Intensity" whatever the normalisation (/ gain, / photon, None). [read]

### Missing here
- No workbook Save for spectra (only for the integral); no export of the line-fit table except
  via the workbook. [read]
- The merge window cannot be undone. [seen]
- Line energies are typed by hand (no element lookup, F47). [read]

## 3. Plot tab

- A file viewer with Rescale, Gradient and the **legacy** Peak Fit; the lss_core peak module
  ("Fit peaks") is not offered here. [read]
- No export of the scaled data, no workbook Save; Save Gradient writes the last file's
  derivative only. Rescale factors reset whenever the file selection changes; Gradient ignores
  them. [read]
- Axis labels fixed "X", "Y"; icon-only Up/Down buttons without tooltips; a non-column file
  raises a blocking `QMessageBox.warning`, the one place besides About that bypasses `notify`. [read]
- The same Add Files / Remove Files / list trio appears on Reflectivity, MCA, Plot and 2D_Plot
  with different filters and behaviours. [seen]

## 4. Dialogs and secondary windows

### Reachability
| Dialog | Opened from | Modal | State |
|---|---|---|---|
| Preferences (code) | File > Preferences... | no | live |
| Note (QInputDialog) | every Save button | yes | live |
| refpatchsamescan | Pilatus > Ref Patch, identical scans | no | live |
| refpatch (+ Known ratio, code) | Pilatus > Ref Patch | no | live |
| pilPeakCenDialog, pilBadPixDialog | during Ref Patch | yes | live |
| pdburn (+ Trends tab, code) | Pilatus > Burn Test | no | live |
| GID worksheet (code) | Pilatus > GID combo > Worksheet | no | live |
| pdformfac | Pilatus > GID combo > Form Factor | no | live |
| pdgioxs | Pilatus > GIOXS | no | live, likely broken for uneven groups [read] |
| mcamerge | MCA > Merge | no | live |
| cutFitDialog / mcaFitDialog (code) | Cuts / MCA > Fit options... | no | live |
| peakfit, peakpara | MCA > Fit / Fit All, Plot > Peak Fit; table double-click | no | live (legacy) |
| plotscale | Plot > Rescale | no | live |
| scanInfoDialog | double-click in the scan list only | yes | live |
| g_l2Dialog, g_l3Dialog, absratioDialog | Calculations menu | yes | live |
| **peakfit2.ui, peakfitpara.ui** | nothing | – | **defunct** (no reference in code) [read] |
| Help > Documentation | – | – | **no handler** [read] |

### Consistency
- **Window titles**: eleven dialogs show "Dialog"; the beam-centre, bad-pixel, g_l2, g_l3 and
  absorber-ratio dialogs all show "Scan Details". Only Preferences, GID worksheet and the fit
  options have real titles. [seen for refpatch, burn, merge; read for the rest]
- **Modality** is mixed with no rule: the information-only beam-centre and bad-pixel lists are
  modal (they stop a Ref Patch) while the interactive patch window is modeless; closing the
  patch window with X abandons the patch silently. [seen]
- **Buttons**: OK/Cancel as plain buttons (merge: Cancel left of OK; limits: Cancel, OK),
  QDialogButtonBox in five, Close only in settings dialogs that apply at once, OK only in the
  form-factor dialog; RUN/SAVE/CLOSE in capitals in GIOXS; "Next>>" / "Finish!" without Back
  or Cancel. Only the GID worksheet has Defaults. [read]
- **"Save"** means a workbook save (tabs, burn, MCA fit options) or a text export (GIOXS SAVE,
  cut fit options "Save results..."). [read]
- Radio choices made with check boxes (form factor Sphere/Ellipsoid must not both be ticked). [read]
- The MCA fit options dialog reuses the cut dialog verbatim: tooltips say "per cut" and "the
  cut's x units". [seen]
- Where results appear: patch → Reflectivity tab; burn → in the window; GID patch → Pilatus
  tab, joins in the worksheet; calibrations → text in the dialog, never applied or saved;
  legacy fit → in the dialog, then Accept on the tab. [seen/read]

### Visual cues
- Burn window: a good one-line verdict with the full table in the tooltip (rule 9 done well),
  but no cue that a shown result is stale after a selection or a Reflectivity-tab change; GID
  controls (Estimator, Position in limit, Auto peak) are shown for reflectivity burns. [seen]
- The Legacy row (REF, GID combo, Qxy range) and Close sit below both tabs; the Qxy range also
  feeds Trends when Auto peak is off. [seen]
- GID worksheet: absorber "not applied", levels, join table: the model for other reductions.
  The columns spin box is disabled under Pinhole without saying why. [seen]
- Form factor: no cue on the map that one is active. Legacy limits: no cue in the table. [read]

## 5. Proposals for phase 1b (same functions, regrouped)

General (all areas)
- One dialog template: real window title naming the task and scans ("Ref Patch: scans 6–9,
  join 1 of 3"), a standard button box (OK/Cancel or Close, Apply where settings do not apply
  at once), Defaults where there are defaults. Information-only lists go to the Messages pane
  or a non-blocking side panel, not modal boxes.
- One word per meaning: **Export** = text files, **Save** = workbook. Rename GIOXS SAVE and cut
  "Save results..." to Export; put Export and Save side by side, in the same corner, on every
  result.
- A small **provenance strip** on each result plot (one short line; detail in its tooltip):
  scans actually used, method (Analyze / Ref Patch joint / legacy), error model, absorber model,
  normalisation, "auto-saved R0004 v2". Save uses those scans, not the left-panel selection.
- Group boxes on the Reflectivity and MCA tabs (they have none): Input/ROI, Reduce, Result,
  Display, Compare with files. Units in labels or suffixes (px, °, 1/Å, keV).
- Fix the legend-position lists; one plot-options row (log x/y, grid, legend) on every 1-D plot,
  including the MCA integral.

Reflectivity
- Two clearly separate areas: **Patch (default)** with the ROI settings, Low Qz, Merge same Qz,
  bad pixels, method (moved or mirrored from Pilatus and Preferences) and the Ref Patch button;
  **Point by point (Analyze)** collapsed or in its own sub-tab.
- A join table in or beside the patch window (factor ± error, method, known ratio used, points
  dropped), kept after Finish and saved with the result; dropped points drawn as open markers.
- Norm Ref as the default list; header as a real header (a table, not a list).
- Remove or wire the defunct Bad Pixel fac field and Bad Pixels list (Q-UI-B3).
- Show the ROI settings read by the burn test in the burn window (read-only or editable).

MCA
- Reduce area: Range (with unit, default from the calibrated axis or dragged on the plot),
  Sum All, Fit lines + options, X-axis (default Qz for XFNTR series, energy for EXAFS), Merge,
  Delete; Display area: logs, grid, legend, offset; Detector area: Calib, monitor, / gain,
  / photon, elements (mirrored from Preferences).
- Legacy Fit / Fit All / Accept behind one "Legacy fit..." button, or removed (Q-UI-B5).
- A source column or tag in the integral list (sum, fit, merged).
- A place for fluorescence burn tests once built (Q-UI-B7).

Plot
- Offer the lss_core peak fit; Export of scaled data; keep scales across selection changes;
  tooltips on the arrow buttons; notify instead of the message box.

Dialogs
- Remove peakfit2.ui and peakfitpara.ui; give Help > Documentation a target or hide it.
- Calculations results: offer "use this value" (e.g. absorber ratio into the field) or say
  plainly that they are information only; menu entry for Scan Details beside the double-click.
- Burn window: show only the controls of the scan kind (REF or GID); move REF / GID / Qxy into
  the Legacy tab; Qxy range next to Auto peak.
- Preferences: tooltip of the menu action to name all four groups; consider moving Ref Patch
  method and detector elements to where they act, keeping Preferences for defaults.
