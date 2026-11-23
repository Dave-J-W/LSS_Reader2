# A GID movie on one 2θ axis (M7)

Made by `python tests/tools/gid_movie.py` (defaults) from the public NX
school GID scan 11: 41 frames, Det_Th 14.0–18.0° in steps of 0.1°, the
level arm (β0 = 0.09°). About 6 s. Asked for in `docs/gui/image_display.md`
M7 and `docs/physics_notes.md` (2026-11-23). The reasoning: a Bragg rod
scatters at a fixed 2θ, so when the detector arm steps, the rod's image
moves across the pixels. Anything fixed to the detector or the slits stays
on the same pixels, so in 2θ it moves. Draw every frame on one 2θ axis,
hold the zoom in angle, and the real peaks stand still while the junk
moves.

- `movie_11.gif` (1.06 MB): all 41 frames at 5 frames per second, looping.
  Each frame is shown as counts per pixel per 10⁶ monitor counts on one
  fixed (2θ, β) window: 2θ 12.27–23.36°, β −1.03–9.06°. Every frame has
  the same axes and the same log colour scale (F69). The colour scale
  runs from 0.10 (about one count in a bin) to 1.02 (the 99.9th
  percentile of all the frames' bins). Zero counts take the bottom colour
  (the arrow on the colour bar), and light grey means the frame has no
  pixel there. The dotted lines mark the frame's usable columns
  (S5 ∩ footprint), and the triangle marks the peak's 2θ (16.636°, from
  `lss_core.pinhole.strongest_peak`).
- `contact_11.png`: 8 evenly spaced frames. On the left they are stacked
  on one 2θ axis, and the peak forms a vertical line. On the right are
  the same frames on detector pixels, where the peak walks across the
  columns. The triangle there marks the column that sees 16.636° in that
  frame.
- `peak_11.csv`: one row per frame. It gives the brightest usable column
  within 16.636 ± 0.3° (rows of β −0.1…2°), its 2θ, its counts against the
  median of that window, the significance, the column the geometry
  predicts, and the single-frame Gaussian centre wherever
  `lss_core.pinhole.single_frame_peaks` fits one.

## What it shows (measured 2026-11-23, header S4–detector distance 271 mm)

- **The DPPC peak stands still in 2θ.** 19 frames hold it (Det_Th
  15.4–17.2°). A frame holds it when at least 8 usable columns fall in the
  window and the brightest stands at least 8 counting errors above the
  window's median, away from the window's edge. Across those frames the
  brightest column's 2θ has a mean of 16.6445° and a range of
  16.6181–16.6727°. The std is 0.0141°, and the largest deviation from the
  mean is 0.78 of a 2θ bin (one column, 0.0364°).
- **On the detector, it walks.** The brightest column moves from 81 to 32
  and moves lower in every frame. That is 49 columns, against 49.5
  columns of arm motion (1.8° / 0.0364°), and the column is always within
  one of where `pinhole.pixel_angles` puts 16.636°. So the spread in 2θ
  (range 0.055°, std 0.014°) is about 30 times smaller than the travel on
  the detector (1.78°).
- **The single-frame Gaussian fits (lss_core) agree.** 16 of those frames
  have one, with centres in 16.6017–16.6534° (std 0.0130°).
- **The remaining drift comes from the S4–detector distance.** At the
  header's 271 mm the brightest column's 2θ drifts by +0.018° per degree
  of Det_Th. At the calibrated 265.7 mm (`--pinhole-mm 265.7`,
  `docs/manual/gid_patching.md` §3) the drift is −0.001° per degree, the
  std is 0.0102°, the largest deviation is 0.47 of a bin, and the Gaussian
  centres have a std of 0.0085°. This is the drift that
  `docs/manual/gid_patching.md` reports from the Gaussian fits (+0.015° per
  degree at 271 mm), seen here without a fit.
- **What moves in 2θ:** the illuminated window. The usable columns and
  S5's shadow (no light beyond column ≈ 139) are nearly fixed on the
  detector, so in angle they slide with the arm. The bright band at
  β ≈ 0, next to the direct-beam row, is cut by that window and slides
  with it.
- **Junk:** this scan has little of it. There is one hot-ish pixel below
  the horizon (row 11, column 136: 12 counts in 9 frames, against a local
  median of 1). There is one pixel flagged by the detector (row 376,
  column 152, negative, so it counts nothing). Short streaks appear in
  single frames and are gone in the next (cosmic rays, probably; not
  checked). Measured once with a scratch script, not by the tool.
- **Not analysed:** the broad light at high β (6–8°) near 2θ 15–15.6° in
  the frames at Det_Th 14.0–16.3°. Its brightest column (rows of β
  5.5–8°, smoothed over 7 columns) goes from 74 to 37 while the arm moves
  2.0°, and its 2θ goes from 14.98° to 15.64°. So it is neither still in
  2θ nor still on the pixels (scratch measurement). Whether it is a second
  (tilted-chain) DPPC peak cut by the low edge of the usable window is a
  question for the owner. I have only read about it, not tested it.

## Caveats

- These are raw frames per monitor count. No footprint, polarisation or
  column-response correction is applied: the movie shows the data, not
  the reduction.
- Binning: each pixel centre goes to its nearest bin
  (`pinhole.bin_counts_2d`, I = ΣN/ΣW with W the monitor). A bin is one
  column wide in 2θ and 4 rows high in β (`--rows`). A bin takes one or
  two columns, and pixels are not split. The GIF draws each bin as 2 × 3
  screen pixels. The contact sheet is resampled for display.
- The brightest column is a check, not a measurement. It is quantised to
  the columns, and each frame's columns sit at a different offset from the
  peak (Det_Th steps 2.75 columns), so the best it can show is that the
  peak stays within one bin. The Gaussian centres are the measurement.
- The GIF has 64 colour levels in one fixed palette, with no dithering.
  Two runs gave byte-identical files (2026-11-23, and checked by
  `tests/test_gid_movie.py`).

## Variations

- `--pixels` also writes `pixels_11.gif` (1.05 MB): the same movie on
  detector pixels, the opposite view (`docs/gui/image_display.md:320`).
- `--window 15.5,18 --beta=-0.5,3` zooms on the peak and holds the zoom in
  angle while the frames play (`docs/gui/image_display.md:322`).
- `--pinhole-mm 265.7` uses the calibrated distance, and the peak stands
  stiller (`docs/manual/gid_patching.md:384`).
- `--linear` draws on a linear colour scale instead of log
  (`docs/physics_notes.md:3990`). `--every 4` uses every 4th frame; the
  colours stay the same because they come from all the frames.

For private data, pass `--spec`, `--scans` and an `--out` outside `docs/`
(e.g. under `sample_data/private/figures/`). The tool refuses `docs/` for
any SPEC file other than NX.
