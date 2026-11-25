# GISAXS and GIOXS examples in the private data (F104, DATA_NEEDS row 4)

Non-cloud data agent, 2026-11-24. Answers `docs/DATA_NEEDS.md` row 4 with an inventory: which real
GISAXS and off-specular data sets exist in the owner's private data, their geometry and detector, and
what the reader would need to handle them. **Read** from the SPEC headers of every file in the private
copy (8255 scans, 2025-12 to 2026-10) and **measured** on the frames where a number is quoted. The
private inventory, with file names and scan numbers, stays with the generators
(`sample_data/private/gid/inventory/`; `scripts/scan_table.py`, `gisaxs_probe.py`, `offspec_bg.py`). No
frame is published; the data sets are labelled by class, not by name or date.

## Answer

**Yes for both, one beamtime each.** Neither is in the repository, and P35 (the GISAXS view one column
off) still has no public series.

| Data set | What | Size | Background | Fit for |
|---|---|---|---|---|
| **GISAXS-1** | Small-angle scattering at grazing incidence on the 200K: α 0.09° (below the critical angle at 10 keV), Det_Th 0.45°, wide S4 and S5, the detector moved back (header S2D 1022.5 mm, pinhole distance 685 mm instead of the GID setup's 551/271) | one beamtime, one SPEC file, 67 scans of 2 frames × 10 s | none taken | the F104 interview and a first test set (cuts along qy and qz, Yoneda) |
| **GIXOS-1** (GIOXS in F104's sense: off-specular scattering below the critical angle) | Fixed geometry on the 200K: α 0.10° (below the critical angle), Det_Th 0.3°, S4 and S5 0.12 mm wide (a collimator selecting one in-plane angle), the detector rows giving the exit angle | one beamtime, two SPEC files, 36 sample scans + 7 with the sample lowered 2 mm, 6 frames × 10 s each (a few 11 or 16) | **yes**: the 7 lowered scans, same slits and absorber | the F104 interview, background subtraction tests (the beam path is 10–14 % of the frame near the horizon, 33–49 % at β 3–6°: `docs/studies/gid_stray_light/`) |
| 1M-A, 1M-B | Specular reflectivity, height and alignment scans on the Pilatus 1M (1043 × 981 pixels): each frame records the diffuse scatter around the specular beam as well | two beamtimes, 176 + 28 scans with frames, 30 keV (and 6.2 keV in one installation) | none | GIOXS around the specular, if the owner means that sense; not a dedicated off-specular measurement |

Other off-specular do-files exist in three more beamtimes (the same off-specular macro family), but no
scans of that geometry were found in their SPEC files: defined, not run, or run into files not in the
copy. The many fixed-geometry `ih` scans at Det_Th 14–25° are GID burn tests on a Bragg peak, not
off-specular data.

## What a reader would need, per data set

**GISAXS-1**
- Geometry: the header's S2D (1022.5 mm) and DBPos (column 47, row 53) do not put the specular rod where
  it is. In every one of the 67 scans the brightest column (the reflected beam and the rod above it) sits
  4.97 ± 0.02 columns higher than DBPos and Det_Th predict at that distance (0.86 mm on the detector).
  Either DBPos was not updated when the detector was moved back, or the distance is off. A direct-beam
  frame at this setup, or the user's own calibration, is needed before q can be trusted to better than
  0.05° in 2θ. This also means P35's one-column question cannot be settled from this set.
- From the header geometry: 0.0096° per column and per row; the 195 columns span 2θ ≈ 0 to 1.8°
  (qy up to about 0.16 Å⁻¹ at 10 keV), the 487 rows β ≈ 0 to 4.7° (qz up to about 0.42 Å⁻¹). These are
  derived from the header and carry the offset above.
- No beam stop: absorber index 10 attenuates the whole frame, specular included. Masking would be by
  pixel range, not by a beam-stop shadow.
- The reader's GISAXS view (P35) and F104's first deliverables (cuts along qy and qz, q mapping with
  refraction, background subtraction, masking) are what this set would exercise. With 2 frames per scan
  it is a set of single exposures (a scan per sample position or condition), not a scan of an angle.

**GIXOS-1**
- Geometry: the GID header (S2D 551 mm, pinhole 271 mm, DBPos 47, 53). With S4 and S5 at 0.12 mm the
  in-plane angle is fixed by the slits (Det_Th 0.3°: qxy ≈ 0.027 Å⁻¹ at 10 keV); the rows give β and so
  qz. The reader needs the vertical profile of a narrow column band against β (the pinhole β of
  `pinhole.pixel_angles` is the right axis), summed over the scan's frames, normalised by monitor and
  absorber.
- Background: subtract the lowered-sample scans (same slits, same absorber; the nearest in time), which
  are flat in β. Two of the seven have a different absorber from their neighbours, so the absorber
  factor (`absorbers.py`) enters the subtraction.
- What the users do afterwards (structure factors from the Vineyard factor and the transmission
  function) is fitting, outside the reader; the reader's part is the background-subtracted, normalised
  β profile with errors, exported per scan.

**1M-A, 1M-B**
- The SPEC header carries a `#B5` line per scan: the pixel (x, y) where the reflected beam should land
  and the sample–detector distance (2038.7 mm at 30 keV; 2654.6 mm in the first 6.2 keV installation).
- In 1M-A the detector stage height changes from scan to scan (29 values over the reflectivity scans):
  the "tracked" mode of F38. It is logged only at each scan's start, not per point, so a per-point beam
  position must come from the frames or from the tracking rule, not from the file.
- The reader does not read the 30 keV 1M frames yet (a defect found by the reflectivity study, PR #68).
  Off-specular analysis of these frames would need the F38 geometry first.

## Caveats

- Classes were assigned from scan commands, angles and slits; a user's own label for a data set is not
  in the file. GISAXS-1 is called GISAXS from its geometry (small Det_Th, wide slits, area detector) and
  from the user's own macro, which says so.
- Nothing here was opened in a GISAXS program; the q ranges are header geometry, not calibrated.

## Open questions for the owner

1. Which of the two senses of GIOXS is wanted for F104: off-specular below the critical angle at fixed
   geometry (GIXOS-1), or the diffuse around the specular in a reflectivity series (the 1M sets)?
2. May the reader's test data include frames from GISAXS-1 or GIXOS-1 if their owners agree? Until then
   they stay private, and only derived numbers are published.
3. Is GISAXS-1's DBPos stale for that detector position (the 5-column offset), or is the distance wrong?

## Files

| File | What |
|---|---|
| `inventory.csv` | one row per data set: class, counts of beamtimes, files, scans and frames, count time, energy, detector, frame size, header distances, angles, slits, absorber, background scans, notes |
