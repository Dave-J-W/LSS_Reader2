# Questions for the owner: workflows

From the workflow map (`docs/gui/workflows.yaml`, rendered in
`docs/gui/workflows.md`), 2026-11-22. Each question says why it is asked
and what changes with the answer. Where the documents already hold the
owner's answer, it is cited under "Already answered" instead of asked
again. Answers go beside each question, dated.

## Already answered (not asked again)

| Topic | Owner's answer | Where |
|---|---|---|
| How a burn scan is recognised | `ascan ih` without movement is the standard for now | physics_notes 2026-11-21 (D54 answers) |
| Burn time axis | Wall (clock) time; the shutter closes between exposures | same |
| Burn verdict | A flat line as good as a line is the good regime; a confident time for < 5 % change | physics_notes 2026-11-21 |
| Whether a GID position drift matters | The user's judgment ("Position in limit" off by default) | same |
| When absorbers change in reflectivity | Not until counting statistics drop by > 100 x; no patching across the critical edge | physics_notes 2026-11-22 |
| Which XFNTR scans to merge | The user chooses (one run, wavelength, sample, shape); the reader offers and warns, does not forbid | F65, D45 |
| What counts in fluorescence | Fitted element lines on a background, per Monc; not the Vortex counter | D47 |
| Elements of the 7-element detector | EXAFS sums all seven; XFNTR uses the central one, element 1 | D49 |
| Saving | Automatic once a reduction is carried through; Save adds a note | D53, D56 |
| Whole-series selection | The default, with a box to turn it off | D55 |

## Burn tests

**Q-BURN-1. What do you do with the burn verdict?** When a burn test says
"changing, 5 % in ≥ 56 s", what changes next: the counting time per point,
the absorbers, the number of repeats, moving to a fresh spot (sx), or
nothing (a note in the log book)? Is the burn test run before every
reflectivity/GID run, or once per sample or subphase?
*Why:* the map ends the burn workflow at "read the verdict"; the window
cannot help with the next step without knowing it. *Changes:* whether a
contextual burn panel shows the verdict against the planned exposure of
the next series (needs the macro's plan), and whether burn results are
linked to the series measured after them in the workbook.

**Q-BURN-2. Where do you want to be when a burn scan finishes?** Should
selecting (or, in live mode, finishing) a burn series open the burn
analysis by itself, offer it with one button, or neither? Do you compare
two burns of one spot (like NX 14 and 15 at absorbers 12 and 8) side by
side, or on a dose axis?
*Why:* today the burn test is a button on the Pilatus tab, refused for two
scans at once; comparing burns means opening the dialog twice (TODO:
F60, dose axis). *Changes:* phase 3 (automatic offer or run) and whether
the burn panel takes several scans.

**Q-BURN-3. Fluorescence burns: how are they measured and judged?** For
scans like 19 and 20 of your XFNTR file (`ascan ih` with spectra): which
element, central element only or all seven, which line or lines, and is
the line intensity per Monc the quantity of merit (as Pilatus ROI per Monc
is for reflectivity)? Do they carry a `#V` line, or are they per-point
files like the October `ascan`s (which the window cannot reach)?
*Why:* the window has no fluorescence burn test; the map's `burn-fluo` is
mostly a guess (docs: hand-off 07, TODO area C). *Changes:* whether the
burn panel gains an MCA mode (line fit per spectrum fed to the same trend
models), and whether per-point files without `#V` must be supported first.

**Q-BURN-4. Are the legacy burn plots still used?** The Burn test dialog
keeps a Legacy tab (REF button, GID list, the typed Qxy range at the top).
*Why:* they take space in the dialog and duplicate the Trends tab.
*Changes:* phase 1b can fold them into an "Advanced" area or remove the
top-row controls from view.

**Q-BURN-5. For a reflectivity burn, is the reflectivity ROI the right
box?** The burn analysis uses the ROI, background offset and direction
from the Reflectivity tab without showing them.
*Why:* a hidden dependency across tabs (the burn dialog does not show the
ROI). *Changes:* whether the burn panel gets its own ROI fields with a
close-up of the box (F71), or keeps sharing the reflectivity ROI and
shows it.

**Q-BURN-6. GID burns: which detector rows?** The GID burn sums all
detector rows; would you restrict it to the Bragg rod's β range, and how
do you choose it (by eye on the mean frame, or a fixed range)?
*Why:* hand-off 07 lists a row range as an open extension. *Changes:*
whether a rows control (with a default from the frame) appears in the
burn panel.

## Reflectivity

**Q-REF-1. Do you check the ROI frame by frame before patching?** The
"Reflectivity" button (Ref tab: frames by Qz, ROI image, Analyze /
Accept / Analyze All) and "Ref Patch" are separate paths. Which do you use,
how often, and which ROI settings do you change from 21×11, 0.5°, H?
*Why:* the two paths share fields on one tab but start from different
buttons; the map cannot say which is routine. *Changes:* whether phase 1b
merges them into one reflectivity panel (ROI close-up first, then patch)
or keeps the frame-by-frame path as a check.

**Q-REF-2. What do you look at in each join?** In the patch window per
join: do you mostly press Next, drop points, or switch to the known
ratio? When you drop points, why (spikes, saturation, a misaligned first
point)?
*Why:* one modal window per join is the slowest part of the workflow;
dropped points are typed indices and cannot be undone (F16). *Changes:*
whether joins that pass their checks are accepted automatically and only
doubtful ones shown, and how dropping is done (click on the plot, mask
with undo, D2).

**Q-REF-3. Identical scans: what is the usual choice?** When the patch
finds repeated scans (same Qz range and points), do you merge them, drop
one, or patch them?
*Why:* the default ("regular patch") is stated only in a message.
*Changes:* the default of the identical-scans step, and whether it needs
a dialog at all.

**Q-REF-4. Qc, Qoff and the normalisation: typed each time?** Qc is
preset to 0.0217 (water); Qoff is typed (F42 would derive it from the sh
scans). Which subphases do you use, and do you type Qc and Qoff for every
sample?
*Why:* they change the `_rrf.txt` file but sit among display options.
*Changes:* whether Qc is chosen from a subphase list or the series'
metadata, and whether Qoff from the sh scans (F42) becomes the default.

**Q-REF-5. Reference curves and comparisons.** Do you load earlier
`_ref.txt` files on the Reflectivity tab (Add Files) to compare samples,
or do that in xmodfit or the Plot tab?
*Why:* three places plot reduced curves from disk (Reflectivity tab,
Plot tab, xmodfit). *Changes:* whether the Reflectivity tab keeps its
file list or one comparison place is kept.

**Q-REF-6. What happens right after Export?** Straight into xmodfit with
the `_rrf.txt`? Do you rename files by a convention (sample, subphase,
series)?
*Why:* a file-name convention could be proposed from the series and
SPEC file. *Changes:* default export names; whether "Export" offers the
xmodfit hand-off files (with the covariance, F24) in one step.

## GID

**Q-GID-1. What do you change in the worksheet, if anything?** With the
pinhole default, do you open the worksheet on every patch, only when a
patch looks wrong, or never? Which settings do you touch (distance Fit,
response, footprint, rows)?
*Why:* the worksheet is a separate window reached through a combo box
whose first item is a title; how central it is decides where it goes.
*Changes:* whether phase 1b docks the worksheet beside the map or keeps it
as an expert window.

**Q-GID-2. What do you look at on the map before saving?** The Qxy
profile, the Bragg rod (Qz cut) of the strongest peak, the join table's
χ²? Which cuts do you make every time, and with what ranges?
*Why:* cuts of a map are defined on the Pilatus tab and shown on the cuts
tab; the ranges have no defaults for a map (F59, F68). *Changes:* default
cuts for GID maps (e.g. the Qxy profile and the strongest peak's rod) and
one cut interface on the map (F68).

**Q-GID-3. Background frames in GID.** Do you subtract background frames
(the background list) for GID, and how do you choose them?
*Why:* background-subtracted maps are not scriptable and the background
list sits in the left panel for all workflows. *Changes:* whether the
background tools belong to the GID/GISAXS panel and need a scripted
equivalent.

**Q-GID-4. Form-factor overlay.** Is "Form Factor" on the GID menu used?
*Why:* an item in the GID menu combo box with its own dialog. *Changes:*
whether it stays in the GID menu or moves to an analysis area.

**Q-GID-5. GID Patch Relax.** When do you choose "GID Patch Relax" (the
larger Q grid) instead of "GID Patch"?
*Why:* two items whose difference is not visible. *Changes:* a single
Patch with an option, and its default.

## XFNTR

**Q-XFNTR-1. Window sum or fitted lines, today?** Do you still use Sum
All with a typed window, or Fit lines? And the legacy Fit / Fit All /
Accept?
*Why:* three paths to the same intensities sit side by side on the MCA
tab; D47 says fitted lines are what count. *Changes:* whether Fit lines
becomes the default for xfntr series and the legacy fit moves to an
advanced area.

**Q-XFNTR-2. How do you place the window or the line?** By eye on the
summed spectrum, by the element's energy, or from a saved setting? Do the
same lines recur across samples (e.g. one element per study)?
*Why:* the default window (1:1000) is the whole spectrum. *Changes:*
whether the reader proposes the line from the element (F47, xraydb) and
remembers the window per sample or SPEC file.

**Q-XFNTR-3. Which defaults do you always change?** Element (central),
x axis (Qz instead of Frame), monitor, calibration?
*Why:* the map shows at least the element (Preferences) and the x axis
(Frame by default) being changed every time. *Changes:* defaults by
series kind (xfntr: centre element, Qz axis, Fit lines).

**Q-XFNTR-4. Do you look at the spectra one by one?** With dozens of
spectra overlaid, do you check them individually (e.g. for a misbehaving
point) and delete points?
*Why:* deleted points are gone (no mask); the overlay has only an offset
for separation. *Changes:* a spectrum browser (movie, as F69 for frames)
and point masks with undo (D2).

**Q-XFNTR-5. What reads the `_flu.txt` file?** xmodfit or another
program, and does it need a fixed format (precision, header)?
*Why:* `_flu.txt` is written with full float precision, unlike the
reflectivity files; the downstream step of the map is a guess.
*Changes:* whether the format is frozen like the reflectivity files.

## EXAFS

**Q-EXAFS-1. What should the reader give you for EXAFS?** The line
intensity per Monc against energy (as `_flu.txt` with an energy column),
or more (dead-time and absorber corrections, μ(E) normalisation, edge
step), and for which program next (Athena/Larch)?
*Why:* F36 is not scoped; the map's EXAFS steps are mostly guesses.
*Changes:* the EXAFS output and whether an energy-scan panel is needed.

**Q-EXAFS-2. Are the `MCAscanpt escan_14` scans listed in the window?**
Do they carry a `#V` line (so the window lists their spectra), or are they
per-point files without one?
*Why:* scans without `#V` are not reachable from the window (TODO area
C). *Changes:* the order of work (per-point files first).

**Q-EXAFS-3. Repeats and edges.** Do you merge repeated edge scans, and
on what grid? Do the `*_edge` scans and the `*_exafs` scans of one sample
go together?
*Why:* series kind 'energy' groups consecutive escans; whether that
grouping is right decides what a whole-series selection gives.
*Changes:* the energy series rule and the merge default on the energy
axis.

**Q-EXAFS-4. Absorbers during an escan.** Are absorbers in during energy
scans? The reader uses the energy in the scan header for the absorber
factor, which changes along a scan (about ×1.7 across 100 eV at n = 52).
*Why:* a physics caveat that touches the EXAFS output. *Changes:*
whether a per-point absorber factor is needed.

## Cuts

**Q-CUTS-1. Which cuts do you make routinely, and on which data?**
I vs β on reflectivity/diffuse frames, beam profiles, Bragg rods on GID
maps? With what ranges?
*Why:* the cut interface is one generic set of controls with defaults
that can miss the detector (F59); F68 asks for defaults by scan kind.
*Changes:* the default direction, axes and range per series kind.

**Q-CUTS-2. Per frame or summed?** Do you cut each frame or the sum (Sum
All)? Do you compare cuts across scans on one plot?
*Why:* "Sum All" sits in the left panel as `gixSumCheckBox`, far from the
cut controls. *Changes:* where the sum option lives.

**Q-CUTS-3. Is β − α / α_f needed now?** F59 is on the docket "not to be
built yet". *Why:* the axes list for cuts will be redesigned in phase 1b
(F68). *Changes:* whether the new interface reserves the β − α and α_f
axes from the start.

## General

**Q-GEN-1. Where does the window make you hunt?** Which actions do you
reach most often, and which take the most clicks or tab changes? (The map
suggests: Ref Patch and Burn Test on the Pilatus tab while their settings
are on the Reflectivity tab; GID actions in a combo box; the element
choice in Preferences; the selection always jumping to SpecPlot.)
*Why:* the map is built from the code and the tests, not from watching a
session. *Changes:* the grouping of phase 1b.

**Q-GEN-2. A typical day at the beamline, in order.** For one sample,
what is the order of measurements and reductions (e.g. sh scans, burn
test, reflectivity, GID, XFNTR), and which do you reduce while the next
runs (live)?
*Why:* phase 3 (contextual GUIs) needs the order of workflows, not only
each workflow. *Changes:* what the window offers after each series and
what live mode follows.

**Q-GEN-3. GISAXS and GIOXS.** Are the GISAXS menu and the GIOXS dialog
used at the beamline today, and on what data?
*Why:* no GISAXS series in the public data; the map of these workflows is
read from code only. *Changes:* whether they keep their place on the
Pilatus tab.

**Q-GEN-4. Alignment scans and the Calculations menu.** Do you reduce or
look at sh/oh scans in the reader (SpecPlot fit in the title) or in SPEC?
Are g_l2, g_l3 and the absorber-ratio calculation still used?
*Why:* alignment scans are attached to series as 'align'; the
Calculations menu is read from code only. *Changes:* whether SpecPlot
gets alignment-specific defaults (columns per scan command) and the menu
stays.

**Q-GEN-5. The Plot and 2D_Plot tabs.** Are they used, for what files,
and would they be missed in a contextual layout?
*Why:* two tabs of files from disk, independent of the SPEC file.
*Changes:* whether they stay as tabs or move to a separate window.
