# GUI assessment (phase 1a): summary across the window

Written 2026-11-22 by the orchestrating session from the four assessment
documents below; it states the themes that run through every tab and
points to the detail. Nothing here has been built. "Seen" means seen in an
offscreen window on the NX school data (or synthetic MCA data) by the
assessment agents; "measured" means a number was taken; "read" means read
in the code only.

| Detail | Covers |
|---|---|
| `assessment_a.md` | Left panel, menus, panes, SpecPlot, Pilatus, Line/Area Cuts, 2D_Plot, Apex |
| `assessment_b.md` | Reflectivity, MCA, Plot, every dialog and secondary window (with a table of what opens each) |
| `image_display.md` | Every image plot, measured, and the phase-2 requirements (movie, colour scales, ROI close-up, cuts) |
| `workflows.md` (from `workflows.yaml`) | The 13 workflows step by step, with the controls each step uses |
| `screens/README.md` | 75 screenshots and the observations made while taking them |

## In numbers

402 controls inventoried in 12 files (`inventory/`), 399 found in a live
window (the other 3 are built only with data); 13 workflows with 9 shared
steps; 72 questions for the owner (`questions.md`).

## Themes

1. **Workflows are split across tabs, dialogs and Preferences.**
   Reflectivity: entry buttons and bad-pixel settings on the Pilatus tab, the
   ROI fields on the Reflectivity tab, the patch method in Preferences; the
   burn test silently reads the Reflectivity tab's ROI fields (read, seen).
   GID: the actions are items of a combo box on the Pilatus tab, the
   settings in a worksheet window, the cut on the Cuts tab. A cut is defined
   on the Pilatus tab and shown on another tab; no image draws the cut band
   (seen). XFNTR: element choice only in Preferences (read).
2. **The Pilatus tab's bottom strip holds 15 controls from six workflows,
   ungrouped** (seen, `screens/21b_pilatus_tab_controls.png`); two combo boxes
   act as menus and keep the last action as their text, so they look like
   modes; "Min (%)"/"Max (%)" hold intensities.
3. **Settings that change numbers have no cue on screen** (seen): the error
   model (only in a hidden pane), "/ gain" and "/ photon" (shown on SpecPlot
   and MCA only), the patch method (joint or legacy), dropped points (vanish
   after Next), automatic saves (a short status message), the absorber
   factor (driven from three places). No result says which scans and method
   made it.
4. **Raw frames are hard to read** (measured, `image_display.md` §1.9):
   Select All draws the first 10 frames as tiles and drops the rest without
   a message; colour limits come from the direct beam, so every tile is dark
   blue (`screens/23b_...`); Log Int is broken by a negative bad pixel;
   zoom is lost on every redraw; Movie blocks the window for 0.5 s per
   frame with no pause; cursor readouts are wrong over tiles.
5. **Inconsistent idioms** (seen, read): checkboxes acting as buttons
   (Select All), combos acting as menus (GID, GISAXS); "Save" means the
   workbook in some places and text files in others; ranges typed "a:b" or
   "a,b"; units in labels, in tooltips or nowhere; dialogs titled "Dialog";
   information-only lists modal while the interactive patch window is not;
   almost every action always enabled and answering "Please select ..."
   instead of being disabled with a tooltip saying what it needs.
6. **Layout competes with selection** (seen): the bottom docks span the
   window width under the left panel (D59); the scan list shows two rows,
   each scan two lines tall; the window cannot be narrower than about
   2266 px.
7. **Dead and legacy pieces** (seen, read): the hidden Apex tab (18 of 19
   controls unconnected, but its colour map still drives the Reflectivity
   ROI image), the Beamlines menu, File > Quit and Help > Documentation (not
   connected), `peakfit2.ui` and `peakfitpara.ui` (never loaded), the
   Reflectivity tab's Bad Pixel fac (unused) and Bad Pixels list (never
   filled), the Command line (editable, does nothing). Legacy paths still
   in use or not: Analyze/Accept, the MCA Fit/Fit All/Accept, the Plot
   tab's Peak Fit, the legacy burn views (questions Q-UI-B1, B2, Q-BURN-4).
8. **Missing where the data need it**: fluorescence burn tests do not exist
   (owner's priority 1; Burn Test accepts Pilatus frames only); no time axis
   on the MCA tab; no line-cut interface on any image (F68); no residuals
   panel anywhere (F74); no undo of dropped points (F16).

## Defects found on the way

Listed in `TODO.md` (area I, "Defects found by the GUI assessment") to be
fixed one per commit when coding resumes; the two that affect saved data
come first there: the workbook Save records the scans selected at the time
of saving rather than the scans behind the result, and the point-by-point
path saves one workbook version per Accept.

## Direction for phase 1b (proposals, not decisions)

- One template for every tab: input/selection, reduce, result, display,
  export/save, as group boxes in the same order; units in labels.
- A one-line **provenance strip** on every result plot (scans, method, error
  model, normalisation, auto-saved version), detail in its tooltip (rule 9).
- One meaning per word (Export = text files, Save = workbook), side by side
  in the same corner of every result.
- One dialog template (real titles, standard button box); information-only
  lists to the Messages pane.
- Actions disabled with a tooltip saying what they need, instead of
  answering with a message.
- The left panel as a dock with the bottom-left corner kept for it, so the
  panes sit under the tabs only (D59).
- Legacy paths behind one "Legacy ..." button each, or removed, as the
  owner answers.
