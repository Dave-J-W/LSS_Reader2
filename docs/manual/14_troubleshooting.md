# 14. Troubleshooting and known limits

[Contents](README.md) · previous: [Scripts and Tools](13_scripts_tools.md) · next: [Glossary](glossary.md)

First, open the **Messages** pane (View → Messages): the reader says there why it did not do something.
The log beside the SPEC file (`<SPEC file>.reader.log`) has the details ([chapter 1](01_window.md#logs)).

## When something looks wrong

| What you see | Why, and what to do |
|---|---|
| A button is greyed out | The selected scans are of another kind. Its tooltip says what it needs ([chapter 1](01_window.md#the-tabs)) |
| A Q cut plots nothing | Its range lies off the detector. Choose the direction again to get the default band about the beam ([chapter 7](07_cuts.md#making-a-cut)) |
| The frames look black or white | The colour scale was typed for another selection. Press **Auto scale** |
| The frames are zoomed somewhere odd | The zoom is remembered. Press **Fit all** |
| A join's note says "no adequate fit" | No smooth curve describes the two scans' overlap. Look for an outlier in the overlap and Drop it, or use the known ratio ([chapter 5](05_reflectivity.md#how-a-join-is-fitted)) |
| A point is marked with a square or a cross on the reflectivity | The beam was more than 2 px off centre, or bad pixels were corrected in its box. Check that frame on the box close-up |
| Points are missing from a new Ref Patch | They were dropped in an earlier patch and are kept as a mask ("N masked" under the plot). **Restore all** brings them back |
| The R/R_F plateau is not flat, or Qoff seems large | Set Qc from **Subphase** before proposing Qoff ([chapter 5](05_reflectivity.md#rr_f-qc-and-qoff)) |
| GID Patch stops at a level | The level shares no β with the level below, or the frames are not a GID set. See [chapter 6](06_gid.md#levels-that-do-not-overlap) |
| Export GID refuses | Set Axes to Angles or Q first |
| Nothing is saved, and a yellow light is on | Another reader has the workbook. **File → Ask for the workbook's write access** ([chapter 1](01_window.md#two-readers-on-one-file)) |
| A saved result says it is out of date | Its scans have grown since. Redo it, or use Live mode, which remakes it |
| The absorber field keeps its value after selecting a scan | from E knows the aluminium foils' factor only at 10.52 keV and below (the copper foils at 30 keV have no known thickness); type the factor ([chapter 2](02_normalisation.md#absorbers)) |
| "Abs=?" in the frame list | The absorber setting of that scan cannot be read from the file |
| An axis will not go log | Nothing positive to show on it; the status bar says so |
| A burn's dose is "in photons", not per mm² | No beam height was found; type it ([chapter 9](09_burn_tests.md#dose)) |
| The window is too wide for the screen | Maximise it, and hide the bottom panes from the View menu |

If the reader meets an error it cannot handle, it logs it, says so in Messages, and carries on. Please send
the log with what you did.

## Older reductions to redo

Results made with older versions of the reader may differ in two cases:

- **Images and cuts of frames taken through absorbers**, reduced before 17 November 2026. The original
  program used an absorber factor of 1.606 per unit for some actions and 1.42 for others in the same
  session, depending on what had been done first. Frames at absorber setting 0 are unaffected.
- **Data taken through absorbers at energies other than 10 keV** (for example 6.21, 7.51 or 9.9 keV),
  reduced before 18 November 2026, when the absorber factor began to follow the energy. Before, the
  10 keV factor was used unless you typed another.

Reflectivity patches are joined by a fitted factor at each overlap, so their shape is largely unaffected; the
absolute scale of single frames, cuts and fluorescence intensities is.

## What the reader does not do yet

- **Resolution.** R_F is not convolved with the Qz resolution, so a proposed Qoff partly reflects the
  rounded edge ([chapter 5](05_reflectivity.md#rr_f-qc-and-qoff)).
- **Per second.** Intensities are per monitor count, not per second.
- **Scripts** cannot yet subtract background frames or make GISAXS.
- **Detectors:** the reader reads the Pilatus (100K and its modules) and the MCA files of the
  fluorescence detectors. Folders such as `pilatus1m/` are not looked in. The Bruker CCD is no longer
  supported.
- **Rates:** whether the Pilatus has corrected its counts for rate is not known to the reader; the
  saturation marks are a guide ([chapter 4](04_frames.md#saturation)).
- **Fluorescence burns** cannot be analysed in the burn window; only Pilatus burns can.
- **Unscaled GID seams:** a map joined without overlap has counting-only errors and an unchecked scale
  across the seam.

The physics behind each method, and the open questions, are recorded in `docs/physics_notes.md` and
`docs/PHYSICS_ISSUES.md`; why each default was chosen is in `docs/OUTPUT_DECISIONS.md`.
