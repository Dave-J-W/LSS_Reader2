# GUI overhaul (R4): plan and working files

Owner's request, 2026-11-22 (paraphrased closely; the request in full is
F67–F73 in `docs/FEATURE_REQUESTS.md`):

> Begin the GUI overhaul planning, no coding yet. There are phases. The
> first phase massages what exists, so that most of the functionality on a
> given panel is preserved (Pilatus is one panel, Reflectivity another; they
> are tabs of the main window). What improves in the first phase is the
> organisation, the grouping of functionality, a consistent UI design, and
> visual clues/cues. The first step is an assessment of all the functions
> and of the workflow each belongs to. Mapping the workflows in a
> maintainable way is a key deliverable: a full workflow map lets us think
> about alternative GUIs that are more contextual and automatic depending
> on the data type.

## Phases

| Phase | What | Status |
|---|---|---|
| **1a Assessment** | Every control, which workflow it serves, what is missing where; the workflow map; screenshots of every area; questions for the owner | **delivered 2026-11-22**: `assessment.md` (summary), `questions.md` (15 to answer first, 72 in all); waiting for the owner's answers |
| 1b Reorganisation | Same tabs and functions, regrouped; one visual language (group boxes, button roles, colours, state cues); one line-cut interface on every image plot, defaults by scan kind | planned after 1a and the owner's answers |
| 2 Raw-data visualisation | Images: movie by default with sticky zoom (never more than 6 frames on screen), sequential sampling (first, middles, last; 4 by default) or first n; sticky plot preferences; intelligent colour scales; ROI close-up for reflectivity; other visual analysis | requirements in `image_display.md` (1a); build after 1b |
| later | Faster log-scale plotting | outside the first deliverables (owner) |
| later | Residuals panel above every fit plot (F74): about 15 % of the height, own scale, χ²/dof in the legend, hidden by default | recorded 2026-11-22 |
| 3 Contextual GUIs | Alternative layouts driven by data type and series kind (F60): offer or run the obvious reduction, show the controls the workflow needs | designed from the workflow map |

## Decisions by the owner so far

| # | Decision | Date |
|---|---|---|
| D58 | Planning first, in phases; phase 1 keeps each tab's functions and improves organisation, grouping, consistent design and visual cues | 2026-11-22 |
| D59 | The Script pane is hidden by default (never raises itself) and does not take room from data selection | 2026-11-22 |

Workflow priority (owner): **burn tests (reflectivity, GID, fluorescence),
reflectivity, GID, XFNTR**, then EXAFS.

## Files in this folder

| File | What | Made by |
|---|---|---|
| `README.md` | This plan, the schema, the status | by hand |
| `inventory/*.yaml` | Every control of the window and its dialogs: where it is, what it does, its handler, which workflows use it, notes on placement and consistency | by hand (assessment), checked by `tests/tools/gui_map.py` |
| `workflows.yaml` | **The workflow map** (source): each workflow as steps, each step naming the controls it uses | by hand, checked by `tests/tools/gui_map.py` |
| `workflows.md` | The map rendered: one table and one Mermaid flowchart per workflow, and a control × workflow matrix per tab | `python tests/tools/gui_map.py` |
| `inventory.md` | The inventory rendered as tables per tab | `python tests/tools/gui_map.py` |
| `assessment.md` | Findings per tab: grouping, consistency, visual cues, missing functions; proposals for phase 1b | by hand |
| `image_display.md` | Assessment of every image plot and the requirements for phase 2 | by hand |
| `questions.md` | Questions for the owner, numbered, grouped by workflow; answers dated beside them | by hand |
| `screens/` | Screenshots of every tab, area and dialog on the public NX school data (and synthetic MCA data); index in `screens/README.md` | `python tests/tools/gui_screens.py` |

The map lives in YAML so that it can be edited by hand, checked by a tool
(every control named in a workflow exists in the inventory, every
inventory entry exists in the window, and every named control of the
window is in the inventory) and rendered. When a control is added, moved
or removed, update its inventory entry and rerun the tool; the check fails
until the map agrees with the window. Since 2026-11-23 the quick suite runs
the check (`tests/test_gui_map.py`), so a control added without an entry
fails there; the first was the Reflectivity tab's "+ covariance" box,
added by the covariance work after the inventory was written and found
only by reading the merge.

## Schema

### Workflow ids (fixed list; use these exactly)

| id | Workflow |
|---|---|
| `burn-ref` | Burn test on a reflectivity frame series (Pilatus ROI vs time) |
| `burn-gid` | Burn test on repeated GID frames (intensity, position, width vs time) |
| `burn-fluo` | Burn test on repeated fluorescence spectra (line intensity vs time) |
| `reflectivity` | Specular reflectivity: ROI sums, absorber patching, R and R/R_F, export |
| `gid` | Grazing-incidence diffraction: pinhole (default) or legacy patch, maps, cuts, export |
| `xfntr` | X-ray fluorescence near total reflection: MCA windows/lines vs Qz, merge, export |
| `exafs` | Energy scans of fluorescence (EXAFS/XANES) |
| `gisaxs` | GISAXS view of Pilatus frames |
| `cuts` | Line and area cuts of frames (diffuse scattering, beam profiles) |
| `alignment` | SpecPlot of motor scans: sh, half-cuts, slits, peak/edge fits |
| `mca-look` | Looking at MCA spectra without a fluorescence series (calibration, lines) |
| `flex-plot` | The Plot and 2D_Plot tabs on files from disk |
| `session` | Open, Update Specfile, Live, series, workbook, preferences, logs, Script pane, messages |
| `general` | Shared by every workflow (e.g. the scan list) |

### Inventory entry (`inventory/<area>.yaml`, a list)

```yaml
- id: pilRefPatchPushButton   # objectName from the .ui, the attribute name of a
                              # code-built widget, or the QAction's objectName
  kind: button                # button | checkbox | radio | lineedit | combo | spin |
                              # slider | list | table | plot | action | menu | tab |
                              # dialog | pane | label
  label: "Ref Patch"          # text on screen ('' if none)
  where: "Pilatus > Reflectivity"   # tab > group box (as dump_tooltips gives it)
  handler: pilRefPatch        # slot(s) it is connected to; '' if none
  does: "Patches the selected reflectivity scans into one curve (joint fit by default)"
  workflows: [reflectivity]   # ids from the table above
  needs: "Pilatus frames of two or more specular scans selected"
  shown: always               # always | <condition>, e.g. "Pilatus scan selected"
  tooltip: true               # has a tooltip today
  notes: ""                   # placement, duplicates, inconsistent naming or look,
                              # a counterpart missing elsewhere (optional)
```

### Workflow entry (`workflows.yaml`, key `workflows:`, a list)

```yaml
- id: reflectivity
  name: Specular reflectivity
  priority: 2                 # owner's order: burn tests 1, reflectivity 2, GID 3,
                              # XFNTR 4, EXAFS 5, the rest 6
  experiment: >               # what is measured at the beamline: scan commands,
    ...                       # series kind, detector, absorbers, typical sizes
  recognised_by: >            # how the reader can tell (series kind, command,
    ...                       # detector): the hook for contextual GUIs (phase 3)
  known_from: [owner 2026-11-15, code, tests/test_gui_workflows.py]
  steps:
    - id: ref.select
      do: Select the series' scans and their frames
      where: left panel
      controls: [seriesWholeCheckBox, scanListWidget, imageListWidget]   # inventory ids
      user_decides: which scans; frames all by default
      automatic: partly        # yes | partly | no, today
      could_be_automatic: ""   # idea for phase 3
      known_from: code         # owner <date> | code | test <name> | docs <file> | guess
      issues: []               # what goes wrong or is awkward here
  outputs: [_ref.txt, _rrf.txt, workbook Saved sheet]
  scripted_as: "Experiment.reflectivity(...)"   # see docs/SCRIPTING.md
  questions: [Q-REF-1]         # ids in questions.md
```

### Question ids

`Q-<AREA>-<n>`, areas: `BURN`, `REF`, `GID`, `XFNTR`, `EXAFS`, `CUTS`,
`IMG` (image display), `UI` (layout and design), `GEN`. Each question says
why it is asked and what changes with the answer; the owner's answer is
recorded beside it with the date.
