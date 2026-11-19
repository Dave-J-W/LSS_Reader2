# Stray light in pinhole GID frames (P40)

Made by `python tests/tools/gid_stray_light.py` from the public NX school
GID scans 11 (arm level) and 12 (arm raised to β0 = 6.5°, aborted after 4
points). Diagnostic figures for `docs/PHYSICS_ISSUES.md` P40 and the
2026-11-19 note "Outer-column diagnosis" in `docs/physics_notes.md`.

- `frames_11_12.png`: three frames of each level on a log scale, with the
  usable columns (S5 ∩ footprint) shaded and S5's high edge dotted, and the
  mean light per column. At the raised arm, a sharp-edged wedge of light
  crosses S5's high edge (rows ≈ 60–150, column ≈ 90 onwards); it is absent
  at the level arm.
- `bands_11_12.png`: light per pixel per monitor count against β for bands
  of columns (usable; beyond the footprint inside S5; beyond S5 on each
  side), one line per level. Light beyond the footprint or beyond S5 did not
  come from the footprint through the pinhole.

β on the horizontal axis is that of the direct-beam column (β0 + atan of the
row offset over the sample–detector distance); other columns differ by a
few tenths of a degree (P38). Private data sets: pass `--spec`, `--scans`
and an `--out` outside `docs/` (e.g. under `sample_data/private/`).
