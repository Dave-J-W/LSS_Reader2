# Questions for the owner: inventory A

Left panel, menus, panes, SpecPlot, Pilatus, Line/Area Cuts, 2D_Plot and Apex. Asked
2026-11-22 for the phase-1b reorganisation. Each question says why it is asked and what
changes with the answer. Record the answers beside them with the date. The findings behind
them are in `../assessment_a.md`.

### Q-UI-A1 — Messages and Errors docks under D59?
D59 says the Script pane is hidden by default, never raises itself, and takes no room from the
left selection panel. Should Messages and Errors follow the same rule?
- **Why:** Messages appears with the first message and is a full-width bottom dock, like
  Script. Today it does not come to the front of its tab group, so fit results can sit behind
  the Script tab. Errors is hidden.
- **What changes:**
  - **yes:** all three panes move together, either under the tab area (left panel as a dock)
    or into a right dock, and Messages raises only on warnings;
  - **no:** only Script moves.

### Q-UI-A2 — Show the error model and normalisation all the time?
Should the window always show which error model (Legacy/Budget) and which monitor
normalisation (counts, / gain, / photon) is in use, for example as status-bar badges?
- **Why:** both change every number and error bar. The error model lives in a hidden pane.
  "/ gain" and "/ photon" are global, but visible only on SpecPlot and MCA, not while working
  on images.
- **What changes:** with yes, phase 1b adds permanent indicators and a copy of the
  normalisation switches on the Pilatus tab.

### Q-UI-A3 — "Sum All" averages: rename it, or make it sum?
"Sum All" in the left panel averages the selected frames (it divides by N). Should it be
renamed "Average frames", or should it really sum?
- **Why:** the label and the code disagree.
- **What changes:** with a rename, the label changes. Making it sum changes output numbers of
  summed cuts, GISAXS and burn, so it would need an OUTPUT_DECISIONS row.

### Q-UI-A4 — Is the Command line still used?
Is the Command line (bottom row: "Ref Patch, scans=[...], slits=[...]") still used, or does the
Script pane replace it?
- **Why:** it is empty for most actions, editable for no effect, and takes a full-width row. It
  is also written as the first line of some exported files.
- **What changes:**
  - **dropped or moved to the status bar:** frees space; the export header stays (it comes
    from the same variable);
  - **kept:** it becomes read-only and is filled for every reduction.

### Q-UI-A5 — Do you use the Calculations menu, and where should it go?
Do you use Calculations > g_l2, g_l3 and abs ratio, and would you look for them in the menu or
next to the SpecPlot fit?
- **Why:** they need scans plotted in SpecPlot first (g_l uses the fit centres) or an absorber
  scan. Nothing in the menu says so.
- **What changes:** with "beside the fit", phase 1b adds buttons on SpecPlot that are enabled
  when the selection fits. Abs ratio could also feed the absorber factor.

### Q-UI-A6 — Is GIOXS still used, and is its Pilatus-tab placement right?
Is the GIOXS button (Pilatus tab) still used?
- **Why:** it has no tooltip, no test and no benchmark (docs/TODO.md R5), and the acronym is
  not explained anywhere in the window.
- **What changes:**
  - **used:** it gets a group (with GISAXS?) and a description;
  - **unused:** it is hidden or removed, like the Apex tab.

### Q-UI-A7 — Do you use the 2D_Plot tab, and its interpolation?
Do you use the 2D_Plot tab, and its "Point Density Factor" / "Update Interpolation"?
- **Why:** the tab draws one x y z file at a time, with no cut and no export. Interpolated data
  cannot be saved.
- **What changes:**
  - **used:** it gets the shared Display box, the shared cut interface and "send map here" from
    GID/GISAXS;
  - **interpolation unused:** those two controls go.

### Q-UI-A8 — Is the background block used outside GISAXS/GIOXS and diffuse cuts?
Is the left panel's background block (Background, Fac, Ignore -ve, list) used for anything
besides GISAXS, GIOXS and diffuse cuts? For example GID maps or burn tests.
- **Why:** it takes a third of the left panel and serves Pilatus frames only.
- **What changes:** if it serves only those workflows, it becomes a collapsible group shown for
  those series kinds, or moves to the Pilatus tab.

### Q-UI-A9 — What should the Pilatus tab show for a reflectivity frame series?
For a reflectivity series, the image shows each frame (up to 10) at a colour scale that
saturates.
- **Why:** this sets the default by scan kind for phase 1b and phase 2 (F69, F70, F71).
- **What changes:** the defaults of the image view and cut interface per series kind. Which of
  these would you rather see by default?
  - a movie;
  - the ROI close-up;
  - a vertical pixel cut through the specular.

### Q-UI-A10 — Pilatus groups for workflows that do not fit the selection
Should the Pilatus tab's tool groups (Reflectivity, GID, GISAXS, Burn, Cuts) that do not fit
the selected series be hidden, greyed out, or left as they are?
- **Why:** the series kind is already known. A burn scan today offers Ref Patch and GID Patch
  as readily as Burn Test.
- **What changes:**
  - **greyed out:** phase 1b keeps every control visible, but disabled with a tooltip saying
    what it needs;
  - **hidden:** this is a step toward the contextual GUIs of phase 3.

### Q-UI-A11 — Remove the Beamlines menu and the Apex tab?
May the Beamlines menu (one fixed choice) and the hidden Apex tab be removed from the
window?
- **Why:** both are defunct (owner, 2026-11-15 and 2026-11-17). The Apex tab still holds the
  colour map the Reflectivity ROI image uses (a hidden dependency to move first).
- **What changes:** less dead UI, and the .ui file loses about 25 objects. Nothing is lost
  functionally once the colour map is moved.

### Q-UI-A12 — Should Quit and Help > Documentation work?
Quit and Help > Documentation do nothing today. Should Quit work, and what should
Documentation open? For example: the manual once written, `docs/SCRIPTING.md`, or the project
page.
- **Why:** they are dead menu items.
- **What changes:** each is connected to its target, or removed.
