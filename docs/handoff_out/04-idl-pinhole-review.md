# Hand-off 04: what the IDL pinhole/GID code knows that the reader does not

Written 2026-11-18 by the LSS_Reader2 agent for a reviewing agent working
in this repository. Read-only review: write only the report named in §5.

## 1. Why

The owner's next GID work (D36 in `docs/FEATURE_REQUESTS.md`):

1. a GID patching worksheet (F61, being built now) that shows the
   patch's settings and joins;
2. **the main improvement:** a pinhole-geometry correction before
   patching, "so that we can use more columns of the image without
   smearing the instrumental resolution" (F45);
3. more flexible overlaps: patching along Qz when the Qxy ranges of two
   images do not overlap exactly, and the opposite case (F62).

The owner supplied IDL code by Mati (`docs/reference_code/idl/`, five
files, unchanged) and suspects "there are gems in here". Joins should
follow what the IDL code does (owner).

## 2. What the reader does today (read the code to confirm)

- `mainwindow.py` `pilGIDpatchData`: each frame is reduced to **one
  β-profile**. The columns within the "H slit" (default 3) of the
  direct-beam column are summed, rows 15–486 are kept, and the profile is
  placed at the frame's detector angle Det_Th (rounded to 0.001°). Angles
  use the sample–detector distance S2D_Dist (`TwoDDetector.plotHint`,
  `ax_type='Angles'`).
- Frames are grouped into at most three Qz levels. Low and middle are
  multiplied by the scan's average Monc; high is not (PHYSICS_ISSUES P31).
- `calArea` (area correction) and the polarisation factor
  1 − (sin 2θ cos β)² are applied.
- `imagehjoin` (scans side by side in 2θ): linear interpolation of the
  β-integrated profiles, one scale factor fitted on the overlap, a plain
  average in the overlap.
- `imagevjoin` (Qz levels): the second map is interpolated onto the
  first's 2θ grid (2D linear, `interp_compat.interp2d_linear`), cubic 1D
  interpolation of the integrated profiles, one factor.
- A "pinhole" check box only swaps the distance used for the horizontal
  axis in display and cuts: S7D_Dist instead of S2D_Dist
  (`lss_core/cuts.py`, `pilSelectedScanChanged`).
- Header values per scan: `spec_routines.py` (S2D_Dist, S7D_Dist,
  DBPos, In_Rot, g_l2, slits S1/S4/S5…).

## 3. Questions to answer from the IDL code

1. **What is "pinhole" data or geometry here?** Is it a separate
   measurement type, compared with GID (PD_PIN against PD_GID), or a
   correction applied to GID frames? Which slits and distances are
   involved? What does `pd_view`'s `pinhole` keyword change?
2. **Pixel → angle → Q** for each routine: the exact formulas for 2θ (or
   the in-plane angle), β, Qxy and Qz per pixel. Name each distance and
   offset, and map it to the SPEC header names the reader knows, where you
   can. Does each column get its own angle before patching? This is the
   owner's "use more columns without smearing".
3. **Patching and merging.** For each of horizontal, vertical, and
   GID + pinhole merge:
   - how the overlap is found;
   - how the scale factor is computed;
   - how points in the overlap are combined;
   - any rebinning (e.g. `zbin`) and the meaning of `relaxed`,
     `sin_norm`, `signed`, `skew`, `clean`, `smooth`/`bsmooth`,
     `patch_range`, `offset`, `limits`/`auto_lim`.
   Which handles images whose extents differ (F62)?
4. **Corrections**: area/footprint, polarisation, monitor, absorber,
   Lorentz or solid angle. Compare each with the reader's.
5. **Gems**: anything the reader lacks that would improve its results or
   usability, ranked by value. Also bugs or questionable steps in the
   reader that the comparison reveals (cite file:line).
6. **Missing pieces**: routines the IDL code calls that are not in these
   files (e.g. PD_GID_READ, RANGE_PROC). Which of them matter for the
   questions above, so the owner can be asked for them?

## 4. Rules

- Read only. Do not edit or commit any file except the report.
- Keep apart what the code **says** (quote line numbers) from what you
  **infer**. Nothing can be run: there is no IDL here.
- Where a formula's physics is standard, cite a source (e.g. a GIXD
  geometry reference); say when a citation is from memory.

## 5. Deliverable

`docs/handoff_out/04-answer/IDL_REVIEW.md`, containing:

- answers to §3, 1–6;
- a **specification** for the reader's pinhole correction and joins:
  formulas with the reader's variable names and SPEC header fields, the
  order of operations, and what to test (properties or numbers that a
  correct implementation must satisfy);
- a short list of questions for the owner.
