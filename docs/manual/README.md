# LSS-Reader 2.0: user manual

LSS-Reader ("the reader") opens a SPEC file from the liquid-surface spectrometer at ChemMatCARS (15-ID-C),
finds the Pilatus images and MCA spectra beside it, and reduces them: each count is divided by the beam
monitor, absorbers are corrected for, and every error is carried through from counting statistics. It
writes the files that fitting programs such as XModFit read. It is not itself a fitting program, although it
fits what it needs to (peaks, joins between scans, trends in a burn test).

This manual is for people who reduce data with the reader: at the beamline, or later from the files.
It assumes you know what a reflectivity or a GID measurement is. Words it uses in a particular sense are
defined in the [glossary](glossary.md).

## Contents

| | Chapter | What it covers |
|---|---|---|
| 0 | [Quick start](quick_start.md) | Two pages: open a file, reduce a reflectivity, export it |
| 1 | [The window](01_window.md) | Opening data, the scan and frame lists, series, the tabs, panes, the status bar, Live mode, preferences |
| 2 | [Normalisation, absorbers and errors](02_normalisation.md) | What the reader does to every count, and the settings that change it everywhere |
| 3 | [Alignment scans: the SpecPlot tab](03_specplot.md) | Plotting any column, the automatic fits, sample-height scans, the Calculations menu |
| 4 | [Pilatus frames](04_frames.md) | Showing frames, the movie, the colour scale, saturation, the box close-up, bad pixels, backgrounds, GISAXS |
| 5 | [Reflectivity](05_reflectivity.md) | The counted box, Ref Patch and its joins, dropped points, R/R_F, Qc and Qoff, Export |
| 6 | [Grazing-incidence diffraction (GID)](06_gid.md) | GID Patch, the worksheet, the map, Export GID |
| 7 | [Line and area cuts, and diffuse scattering](07_cuts.md) | Cuts of frames and maps, I against β or β − α, fitting peaks in cuts |
| 8 | [Fluorescence: the MCA tab](08_fluorescence.md) | Spectra, Sum All, Fit lines (the reader's fit and XeRay), merging, XFNTR and energy scans |
| 9 | [Burn tests](09_burn_tests.md) | Does the beam change the sample? Trends, the 5 % time, dose, beam damage or a sample changing by itself |
| 10 | [Timeline and Compare](10_timeline_compare.md) | The session on one time axis; saved curves overlaid |
| 11 | [Saving, exporting and the workbook](11_saving.md) | Export against Save, the workbook, automatic saving, live remakes, every output file |
| 12 | [Plots from files and plot options](12_plots.md) | The Plot and 2D_Plot tabs; fonts, ticks, legends, labels and ranges for every tab |
| 13 | [Scripts and the Tools menu](13_scripts_tools.md) | Repeating a reduction in Python; the demonstrations and figures |
| 14 | [Troubleshooting and known limits](14_troubleshooting.md) | When something looks wrong, and what the reader does not do yet |
| | [Glossary](glossary.md) | Monc, Qz, β, join, footprint, workbook, … |

Two reference documents sit beside the chapters:

- [GID patching: the options and what each costs](gid_patching.md), a technical addendum with eight diagrams.
- [Every control and its tooltip](controls.md), generated from the program itself.

## How to read the window

- **Every control explains itself in its tooltip.** Hover over it. The window keeps its labels short and puts
  the reasons, the sources of numbers and the caveats in tooltips. This manual says what a control is for
  and when to use it; the tooltip says exactly what it computes.
- **The reader does not stop you with message boxes.** What happened is written in the Messages pane
  (View menu), which opens by itself only for a warning or an error. The reader does not close on an
  error. (File choosers, a few calculation windows and About still open as dialogs.)
- **The reader never changes the SPEC file or the images and spectra.** It writes only its own files:
  exports where you choose; beside the SPEC file its workbook (`<SPEC file>_reader.xlsx`, with a `.lock`
  file while it is open) and its log (`<SPEC file>.reader.log`); and its preferences and session logs under
  `~/.lss_reader/`.
- **Results save themselves.** Every reduction you carry through is stored in the SPEC file's workbook,
  with the settings that made it ([chapter 11](11_saving.md)).

## Example data

The screenshots use the public NX school data in `sample_data/NX_school/2026sep/20260923`, which comes with
the source. You can follow every chapter with it:

| Scans | What they are |
|---|---|
| 4, 5, 10, 13 | Sample-height and alignment scans |
| 6–9 | A reflectivity of DPPC on water at 10 keV, in four scans through different absorbers |
| 11, 12 | GID: two Qz levels of detector-angle scans (the second was stopped early) |
| 14, 15 | GID burn tests: 21 frames each at one spot, absorber 12 then 8 |

The NX school data has no fluorescence spectra; the fluorescence screenshots use synthetic data made by
the Tools menu (*Synthetic data sets*).
