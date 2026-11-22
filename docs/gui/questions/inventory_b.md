# Questions for the owner: inventory B (Reflectivity, MCA, Plot, dialogs)

From `docs/gui/inventory/{reflectivity,mca,plot,dialogs}.yaml` and `docs/gui/assessment_b.md`,
2026-11-22. Only what the code and the documents cannot answer. Topics already asked in
`questions/workflows.md` are not repeated: legacy burn plots (Q-BURN-4), fluorescence burns
(Q-BURN-3), checking the ROI before patching (Q-REF-1), sum or fitted lines (Q-XFNTR-1), MCA
defaults (Q-XFNTR-3), form factor (Q-GID-4), GISAXS/GIOXS (Q-GEN-3), the Calculations menu
(Q-GEN-4), the Plot and 2D_Plot tabs (Q-GEN-5). Answers go beside each question, dated.

**Q-UI-B1. Is the point-by-point "Analyze / Accept" path still used to make curves?**
The top half of the Reflectivity tab (Qz list, Search Win, Cen, Analyze, Accept, Analyze All,
ROI close-up) serves only that path; Ref Patch does not use it, and after a patch it shows
stale or empty content. The path is not scriptable, and with automatic saving each Accept
stores a new workbook version.
*Why:* it decides half of the tab's layout. *What changes:* used → its own sub-tab
("Point by point"), saved once when finished rather than per point; rarely used → collapsed
under the patch area; not used → removed (with your agreement), freeing room for the ROI
close-up of the patched frames (F71) and a join table.

**Q-UI-B2. The legacy fitters: MCA "Fit", "Fit All", "Accept", and Plot "Peak Fit".**
They open the old Peak Fit Panel (Gaussian/Lorentzian, start values typed in a table, limits by
double-click), next to the newer "Fit lines" / "Fit options..." on the MCA tab. Is the old
panel still used, and for what?
*Why:* two fit systems and three fit-range fields on one tab. *What changes:* not used → one
"Legacy fit..." button or removal, and Plot gets the new "Fit peaks"; used for something the new
fit cannot do (e.g. inverted peaks, per-parameter limits) → that feature is added to the new
options dialog first.

**Q-UI-B3. "Bad Pixel Correction fac" and the "Bad Pixels" list on the Reflectivity tab do
nothing.** The field is read and never used; the list is only ever cleared. Bad-pixel
correction is set on the Pilatus tab, and pixels found inside the ROI are reported by a modal
box during Ref Patch only. Were they meant to work (e.g. a separate threshold for the ROI, and a
list of corrected pixels per Qz)?
*What changes:* yes → wire them and drop the modal box; no → remove both.

**Q-UI-B4. Where should reduction choices live: Preferences or the tab that uses them?**
The Ref Patch method (joint/legacy), the known-ratio rule and the detector elements summed for
fluorescence (centre/all) are in File > Preferences, kept between sessions, while Slit and BG
Offset are on the Reflectivity tab and bad pixels on the Pilatus tab. Do you change the patch
method or the elements during a session (e.g. one sample XFNTR, the next EXAFS)?
*What changes:* yes → the controls move (or are mirrored) to the tab, with Preferences holding
only the defaults; no → they stay, and the tabs only show the value in use.

**Q-UI-B5. How much state may be shown on screen?** Rule 9 puts explanations in tooltips. Today
nothing on the Reflectivity or MCA tab says which method, error model, absorber model or
normalisation made the result, which scans it came from, which points were dropped, or that it
was saved automatically (8 s of status bar). Would one short line under each result plot (e.g.
"S 6–9 · joint · Budget · cal foils · auto-saved R0004 v2"), with the details in its tooltip,
be acceptable, or should it be an icon or colour cue only?
*What changes:* the design of every result area in phase 1b.

**Q-UI-B6. The two boxes that stop a Ref Patch.** "Beam centre off by more than 2 pixels" and
"Bad pixel(s) in the signal ROI" are modal and must be clicked away before the patch window
opens; everything else now goes to the Messages pane. Do you want to be stopped at that point,
or is a warning in the Messages pane (and a mark on the affected points) enough?
*What changes:* modal kept as a deliberate exception, or both become messages plus marks.

**Q-UI-B7. The patch window: do you ever need to go back?** It steps join by join with Drop
and Next only; there is no Back, no Cancel (closing it abandons the patch silently), no undo of
a drop, and the factors are not listed after Finish.
*What changes:* Back/Cancel and a join table (factor ± error, known ratio used, drops) kept with
the result, or a single overview of all joins instead of a step-by-step wizard.

**Q-UI-B8. Unused pieces: may they be removed?** `peakfit2.ui` and `peakfitpara.ui` are loaded
by no code; Help > Documentation has no action. Should Documentation open something (the manual
when written, `docs/` on GitHub, the README), or be hidden until then?
*What changes:* deletion of two files; Help menu content.

**Q-UI-B9. One meaning for "Save".** Save now means the workbook on the tabs and the burn
window, but the GIOXS dialog's "SAVE" and the cut fit options' "Save results..." write text
files. May all text-file writers be called "Export" and all workbook writers "Save", with both
side by side on every result (burn tests get an Export, the Plot tab and spectra a Save)?
*What changes:* button names and placement in phase 1b; new Export/Save where missing.

**Q-UI-B10. Window titles and order of dialogs.** Most dialogs are titled "Dialog" or "Scan
Details". Is there a beamline habit of keeping several windows open side by side (patch window,
burn window, worksheet, fit options), which would favour docked panels inside the main window,
or are separate windows preferred?
*What changes:* phase 1b keeps modeless windows with proper titles, or turns the frequent ones
(burn, worksheet, fit options) into docks/side panels.
