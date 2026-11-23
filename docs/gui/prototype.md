# ngui: prototype of the new layout (a sketch, off by default)

Owner, 2026-11-23: "I think you know enough to make a prototype new-GUI,
which will be off by default and enabled in the preferences. Take a stab
at reorganizing the contents and theme of all the tabs, such as Pilatus,
reflectivity, 2D plot etc. You don't have to build anything functional at
first, you can just sketch it out."

The owner calls the new GUI **ngui** (2026-11-23).

**What it is.** A second window, "LSS Reader — ngui (prototype)",
built in code from a layout table. Every control is a disabled placeholder
whose tooltip says what it does today and where it lives now. Nothing in
it reduces data, and the real window is unchanged. It opens when the
preference `ngui` is on (Preferences, off by default), beside the real
window.

**Why a table.** The layout places each of the 403 inventoried controls
(`inventory/*.yaml`) in exactly one new home, or lists it as retired with
a reason. A test fails when a control has no home, so reorganising cannot
silently drop a function. Moving a control means editing one line of the
table.

## Principles

Each comes from the assessment (`assessment.md`), the image-display
requirements (`image_display.md`) or the owner's answers (`questions.md`,
the map's `day-ref`).

1. **Tabs by workflow, in the order of the day.** Scans, Frames, Burn,
   Reflectivity, GID, Fluorescence, Files. The day (`day-ref`) runs left to
   right: align and judge the surface, look at frames, burn-test, measure
   reflectivity or GID or XFNTR, compare. The detector no longer decides the
   tab: frames from any Pilatus scan are looked at in one viewer.
2. **The selection panel keeps the full height on the left.** It is a dock
   holding the left corner. The Messages, Script and Errors panes sit under
   the tabs only, hidden by default, and never raise themselves (D59).
   Order in the panel: series, scans, frames with the display mode, then
   background frames, which fold away when empty.
3. **One template in every tab.** A left column of titled groups in a fixed
   order: **Input** (what is reduced), **Reduce** (the settings that change
   numbers), **Display** (what changes only the picture). The plots are on
   the right. One meaning per word.
4. **Saving is automatic; one Save… per result; no Export buttons** (D61,
   owner 2026-11-23). Every result is saved to the workbook (Excel, later
   HDF5) once it is made. Each result keeps one small **Save…** button: it
   saves the result as a version with the user's note. If the result is the
   one just saved automatically, the note goes on that version instead of
   a copy. Changing the parameters and pressing Save… again gives a new
   version: the owner's case, "when people change reduction parameters and
   save again". Exporting text files is a less used option, under File >
   Export… (choose a saved result, the format, options such as
   "+ covariance").
5. **Provenance on every result.** A one-line strip under each result
   plot, e.g. "S# 6–9 · joint fit · budget errors · / Monc · saved R0007 v2",
   with the detail in its tooltip (rule 9); clicking it also offers "Add a
   note…".
6. **State bar.** Short labels at the right of the status bar for the
   settings that change numbers everywhere: error model, normalisation
   (/ Monc, / gain, / photon), patch method, Live, automatic saving. Each
   has a tooltip, and a click opens its setting. This is a proposal:
   question 12 is open.
7. **Actions disabled until their input exists**, with a tooltip saying
   what is missing ("select a reflectivity series"), instead of a message
   after the click.
8. **Units in labels; ranges typed one way** ("a – b"); no checkboxes used
   as buttons, no combo boxes used as menus: GID and GISAXS actions become
   buttons.
9. **One frame viewer for every image** (`image_display.md` W1), with two
   sub-tabs, **Raw frames** and **Line cuts** (owner 2026-11-23: switching
   between the raw data and the cuts), the cut band drawn on the raw image
   and a **Split** toggle to see both.
   - Movie by default for more than one frame; Sampled (4), First n and
     Sum as modes, never more than 6 tiles (F69).
   - A movie bar: play, step, slider, frame counter, speed, loop; metadata
     line (scan, point, Qz or 2θ, time, absorber, Monc).
   - Zoom, colour map, scale (linear, log, asinh) and limits stay put while
     frames play and when the selection changes (owner 2026-11-23; F70).
   - Axes in pixels, angles or Q; a "fixed in 2θ" switch for GID movies
     (M7).
   - Reflectivity opens on log scale, zoomed to the ROI and both
     background zones with a margin, the boxes drawn: "not too close, we do
     want to see the diffuse scattering around it, and the background zones
     to the sides. But still a healthy zoom compared to the full image"
     (owner 2026-11-23; F71).
   - The Line cuts sub-tab is the same for every image (F68).
10. **Residuals panel** above every fit plot, about 15 % of the height,
   hidden by default (F74).
11. **Legacy paths behind one "Legacy…" button per tab** (Analyze/Accept,
    MCA Fit/Fit All/Accept, Plot Peak Fit, legacy burn plots), until the
    owner answers question 13. The dead pieces (Apex tab, Beamlines menu,
    unconnected Command line) are listed as retired, not deleted, until
    question 14 is answered.
12. **Fits a 1440 × 900 screen.** Today's window cannot be narrower than
    about 2266 px.
13. **Theme.** Qt's Fusion style with one light palette, titled group
    "cards", consistent spacing and font sizes, and one accent colour for
    the current tab and the primary action of each group. A small coloured
    chip per workflow in the tab titles, always with text, never colour
    alone. viridis is the default colour map; jet stays available.

## Tabs and their contents

The layout table (`gui_proto/layout.py`) holds the detail; this is the
outline. Controls are named by their inventory id.

- **Scans** (was SpecPlot; alignment and any motor scan).
  - Input: the scans selected, several overlaid.
  - Reduce: normaliser, / gain, / photon.
  - Display: X, Y, Y2, log, grid, legend, labels.
  - Fit: the scan's shape (peak, edge, plateau); a **sample height check**
    (FWHM against 65 µm, flatness as a super-Gaussian exponent, earlier sh
    scans of the sample; F78); half-cut beam size (F43).
  - Tools: g_l2, g_l3, absorber ratio (from the Calculations menu).
- **Frames** (was the Pilatus image area, Line/Area Cuts and the GISAXS
  and GIOXS views).
  - The frame viewer of principle 9 (Raw frames and Line cuts sub-tabs).
  - Reduce: bad pixels, direct-beam position, background frames and factor,
    Ignore −ve, pinhole box.
  - Display: as principle 8.
  - Cuts (in the Line cuts sub-tab): direction, range, axes, Sum, Fit
    peaks and its options.
  - Views: GISAXS, GIOXS.
- **Burn** (was the Burn test dialog, Pilatus tab button).
  - Input: burn scans, several at once (Q-BURN-2), with the ROI shown
    (Q-BURN-5).
  - Reduce: models, time axis (clock or exposure; dose, F76), errors,
    threshold.
  - Display: trend panels, environment panels (barrier, tensiometer,
    oxygen; F75).
  - A verdict card: "No change over 400 s?" (owner 2026-11-23), the best
    model, the time to a 5 % change, the absorber.
  - Legacy… (REF plot, GID list).
- **Reflectivity** (was the Reflectivity tab plus Ref Patch and its
  settings on the Pilatus tab and in Preferences).
  - Input: the series (whole series and all its frames in one action).
  - ROI: size, background offset and direction, centre, with the ROI
    close-up movie (F71).
  - Patch: method (joint or legacy), known foil ratio, threshold. The joins
    are listed inline (factor ± error, status), the doubtful ones opened,
    instead of one window per join. Identical scans: summed by counts and
    monitors (F81), dropped, or patched.
  - Result: R or R/R_F, the subphase with its Qc and electron density
    (F79), Qoff with "Propose" (F79), normalisation factor, Qz²; the
    provenance strip.
  - Compare: saved reflectivities of the workbook by series, time or sx
    (F80), files from disk.
  - Check frames…: the point-by-point path (Analyze/Accept/Analyze All),
    until question 13 is answered.
- **GID** (was the GID combo box on the Pilatus tab, the GID worksheet
  window and the GID cuts).
  - Input: levels and series, background frames.
  - Settings: the worksheet's contents inline (geometry, pinhole, response,
    joins).
  - Map: its own view, not the frame canvas (Q-IMG-15); colour and scale.
  - Cuts: Qxy and Qz.
  - Tools: form factor, patch relax.
- **Fluorescence** (was the MCA tab and the element choice in
  Preferences).
  - Input: the spectra, the element of the 7-element detector (D49).
  - Reduce: calibration, normalisation, the window or the fitted lines.
  - Display: spectra, integral against Qz or time.
  - Merge (XFNTR rule, F65).
  - EXAFS: energy scans (a stub until question 6 is answered).
  - Legacy… (Fit, Fit All, Accept).
- **Files** (was the Plot and 2D_Plot tabs).
  - One file list.
  - A 1-D plot: scale, gradient, Legacy… peak fit.
  - A 2-D map: colour, log, limits, interpolation.

Every result above has its Save… button and provenance strip (principles
4 and 5); File > Export… writes text files, with "+ covariance" for a
reflectivity. Preferences keep their dialog for now; settings that change numbers also
appear where they act (the patch method in Reflectivity > Patch, the
element in Fluorescence > Input).

## Built from

- `gui_proto/layout.py`: the layout as data (tabs, groups, placed
  inventory ids, special elements, the retired list with reasons).
- `gui_proto/theme.py`: the palette and style sheet.
- `gui_proto/window.py`: builds the window from the table, with no
  reduction code and no imports from `lss_core`.
- `tests/test_gui_proto.py`:
  - it builds offscreen without exceptions;
  - the preference is off by default;
  - every inventory id is placed once or retired;
  - the Preferences box opens and closes the window.
- `tests/tools/gui_proto_screens.py`: screenshots in
  `docs/gui/prototype/screens/`.

## Open

Everything here is a proposal for the owner to react to. It changes no
number and no behaviour of the real window. Where it depends on an
unanswered question, the question is named.
