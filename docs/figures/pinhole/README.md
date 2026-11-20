# Pinhole GID geometry: eight figures

Made by `python tests/tools/pinhole_figures.py [--out DIR] [--only N …]`
(default: this folder). Each figure carries its explanations as labels on
the drawing; the two lines under it say what it shows and which functions
of `lss_core.pinhole` its numbers come from. This file says, for a reader
who is not a specialist, what to look at in each figure and why it
matters.

## The set-up in one paragraph

In grazing-incidence diffraction (GID) the X-ray beam skims the liquid
surface at a tiny angle α (0.09° here), so it lights a long, thin strip
of the surface: the **footprint**, 63.3 mm long and 2 mm wide on the NX
data. The detector sits on an arm, 551 mm from the sample, turned by
Det_Th. In front of it are two slits. **S4**, 271 mm before the detector,
is very narrow (0.2 mm) and acts as a **pinhole**: each detector column can
only see the footprint through it, so each column looks at its own point
of the footprint and at its own angle 2θ. **S5**, 32 mm before the
detector, is wide (3 mm on one side, 14 mm on the other) and decides
which columns can receive light at all. The figures show where these
rules put the light, how exactly the reader computes each pixel's angles,
and what the finite width of S4 changes.

**The reader's usable columns** (`usable_columns`, `frame_columns`; since
the P39 fix, 2026-11-19, D51) are those that S5 passes and that see the
footprint through the whole S4 opening (the inner edges of `s4_window`),
the same on every row. On raised-arm frames (β0 > 1°) the high edge stays
at IDL's because of a stray-light streak (P40b). IDL's own window
(PD_PIN_RANGE: the right width, but centred on the direct-beam column c0)
is kept as the option `footprint='idl'` and drawn in the figures as such.

## Conventions

- **Numbers.** Every point, length and angle is computed by the reader's
  own code (`lss_core.pinhole`), never typed. Frame parameters (Det_Th,
  β0, α, c0 = 47, r0 = 53, D_s = 551 mm, D_p = 271 mm, g_l3 = 556 mm,
  slits S1, S4, S5) come from the public NX school SPEC file
  `sample_data/NX_school/2026sep/20260923` via
  `tests/tools/pinhole_frames.py`; the module size (487 × 195) from the
  image. The one typed constant is the 200K's 17-pixel gap between its two
  modules (DECTRIS 487 × 407 layout).
- **Scale.** 3D panels are orthographic isometric views (elevation
  35.264°, azimuth −45°: the beam runs left to right) at true scale on all
  three axes; close-ups are the same view zoomed, their magnification
  printed in the panel title. **Plan views** (cases 3 and 8) are drawn in
  true millimetres on both axes, but the axis across the arm is stretched
  so that the narrow fan of rays can be seen; the stretch is measured from
  the finished axes and printed in the title ("across the arm drawn ×5").
  Straight lines stay straight under that stretch.
- **Colours**, the same in every figure: vermilion the incident beam
  (k_in); light and dark orange the footprint and the part the usable
  columns see; black rays; blue the arm, its unit vector n and distances;
  green the detector's e_h, e_v and the direct-beam row and column; magenta
  pixel offsets (wx, wy) and IMG_COO_CONV's u, v, w; **purple S5**: its
  blades, the rays through its edges (dashed) and the stretch of the beam
  axis it lets through; grey the lab axes, the per-axis approximations
  and IDL's footprint window (dashed). A purple × marks where S5 stops a ray. Labels are in the colour
  of what they label; a vector's label lies along it, except labels of one
  or two characters (n, x, wy …), which stay upright.
- **What the script adds**: drawing offsets, arcs between two directions
  the reader returned, the point where a ray crosses the S5 plane, clipping
  of close-ups and the outline (convex hull) of a bundle of rays. Nothing
  that changes a number. It also checks that no label overlaps another or
  leaves the figure, and prints any that do (none at present).
- **S5's sides.** The header's S5L opens towards low columns and S5R
  towards high ones (`s5_window`); S4L and S4R are taken the same way.
  On the NX data S4L = S4R = 0.1 mm, so S4's side convention does not
  matter there.

## The order of the figures

From the frame of reference to the effects: what the coordinates are (1);
where the old one-angle-per-row/column formulas are right (2); the one
physical fact that makes them wrong, the pinhole (3); its consequence for
β (4); the extra consequence when the arm is raised (5); why it matters
for the planned second module (6); what makes a column usable (7); and
what the finite width of the S4 "pinhole" does (8). Q vectors are not a
case: `lss_core.gid.products` computes Q from (2θ, β, α) by the standard
formula; the errors were all in the angles.

## The figures

### Case 1 — Lab frame, arm and the detector's coordinates
`case1_lab_frame_and_detector.png` · NX scan 11, Det_Th 16°, β0 = 0.09°.

**Look at:** (a) the whole set-up at true scale. The beam (k_in) lights the
footprint; one ray goes from footprint point F through the S4 pinhole to
pixel P (row 300, column 100, the last usable column) and arrives at
2θ = 17.927°, β = 4.749°. D = 551.0 mm is the sample-to-detector distance,
D_p = 271 mm the S4-to-detector distance. The two black rays from the
footprint's ends show its reach: the upstream end would land on column
2.7 but S5 stops it (purple ×); the downstream end lands on column 102.0.
(b) The detector close up: the arm's direction n, the detector's own axes
e_h and e_v, and P's offsets from the direct-beam pixel, wx = −9.12 mm and
wy = 42.48 mm.

**Why it matters:** every later figure uses these names. wx is negative
for a column above c0 because e_h points towards *lower* 2θ, a sign that
is easy to get wrong.

### Case 2 — Per-axis angles: exact on the direct-beam column, on the row only with the arm level
`case2_direct_beam_row_and_column.png` · same frame.

The reader used to give each column one 2θ and each row one β (the
"per-axis" formulas `column_two_theta`, `row_beta`); the cuts and the image
axes still do (P38).

**Look at:** (a) pixel A on the direct-beam row and pixel B on the
direct-beam column, with their angles drawn as arcs from the ray's own
direction. On B the two methods agree exactly (β 6.2727°); on A almost
(β 0.0957° exact, 0.0906° per-axis), because the arm is nearly level here.
The note in (a) gives the raised arm (scan 12, β0 = 6.5°): there the
direct-beam row is off by up to 1.02° in β (0.34° inside the usable
columns). (b) The β error over the whole module: zero only on the green
cross (row r0 and column c0), up to −1.06° in the far corner; the dark
blue bar at the bottom marks the usable columns.

**Why it matters:** the old formulas are right only on a cross through
the direct beam; everywhere else each column sees a different footprint
point (cases 3, 4), so the reader now uses the exact transform
(`pixel_angles`, Mati Meron's IMG_COO_CONV).

### Case 3 — The pinhole seen from above: every column sees its own footprint point
`case3_pinhole_top_view.png` · same frame, rays to the direct-beam row.

**Look at:** (a) the fan of rays at true scale: they all pass through one
point, S4. (b) The same from above (across the arm drawn ×5). The black
rays from the footprint's ends reach columns 2.7 and 102.0: that is the
footprint window. S5's two blades (purple) let through columns 27.2 to
139.3; traced back through S4 (dashed purple), they allow the stretch
x = −13.3…49.4 mm of the beam axis (purple line on the beam axis), which
starts inside the footprint and runs 18 mm beyond its downstream end. So
the footprint limits the high side and S5 the low side: the column
reached by the footprint's upstream end (2.7) is stopped by S5. The usable
columns, 28 to 100 (pale blue), end just inside the footprint's reach,
where S4's width starts to cut the light (case 8); they see
x = −12.8…30.6 mm of the footprint (dark orange). The dashed grey rays are
IDL's footprint window (`footprint_window`, after PD_PIN_RANGE, now an
option): the same width but centred on c0, from −2.6 to 96.6.

**Why it matters:** this is the physical reason why β depends on the
column (case 4), and it shows directly how far the footprint and the S5
allowance reach.

### Case 4 — Why β depends on the column
`case4_beta_depends_on_column.png` · same frame.

**Look at:** (a) two pixels on the top row (486), at the ends of the
usable columns (28 and 100). Through S4 they see different footprint
points, F1 at x = −12.8 mm and F2 at x = 30.6 mm. (b) Close to S4 (×25)
their rays cross the slit 2.90 mm apart in height, because their sources
are at different distances. (c) So they leave the surface at different
exit angles, β = 7.620° and 8.217° (0.597° apart), while the per-axis
formula gives the whole row one β, 7.788°: off by up to 0.43° inside the
usable columns.

**Why it matters:** a feature at a fixed β (a Bragg rod's intensity
profile, say) lies on a tilted line across the detector, not along a
row; binning by row smears it.

### Case 5 — Raised arm: the (u, v, w) decomposition, and 2θ depends on the row
`case5_raised_arm_uvw.png` · NX scan 12 (high-Qz level), β0 = 6.50°,
Det_Th 14°; D = 554.6 mm (raising the arm adds 3.6 mm).

**Look at:** (a) how IMG_COO_CONV splits the ray from the slit point S to
pixel P (row 486, column 90): u = −7.40 mm across the arm, v = 264.74 mm
along it, w = 70.37 mm up; then 2θ = Det_Th − atan2(u, v) = 15.600° and
β = atan2(w, √(u² + v²)) = 14.879°. (b) With the arm raised, the
detector's vertical axis leans back, so the top and bottom of one column
are at different 2θ: exact minus per-axis spans 0.029° along column 90,
0.108° along the edge column 194 (which gets no light), against 0.0015°
for that column with the arm level.

**Why it matters:** at the high-Qz level 2θ is no longer a function of
the column alone; the exact transform gives each pixel its own 2θ.

### Case 6 — Where the 200K's second module would be
`case6_second_module.png` · scan 12, Det_Th 14°.

The 200K is two 487 × 195 modules with a 17-pixel gap; the unused one
would sit at columns −212…−18 or 212…406 of this module's numbering.

**Look at:** (a) rays to the modules' end columns: through S4 they look
at beam-axis points far outside the ±31.7 mm footprint (x = −58 to
−559 mm on the low side, 87 to 140 mm on the high side), and S5 stops
every one of them (purple ×). (b) The three modules coloured by the
per-axis β error: up to 7.1° on the low-side module, 4.0° on the high-side
one, 2.2° on the module in use. (c, d) The β and 2θ errors along the top
and bottom rows; the purple bar is what S5 lets through.

**Why it matters:** using the second module needs both the exact angles
and different slit settings: with the present slits it gets no light.

### Case 7 — The footprint at the usual GID angle, and what makes a column usable
`case7_footprint_and_usable_columns.png` · scan 11, Det_Th 16°,
α = 0.0905°, S1 0.10 × 2.0 mm. Added 2026-11-19 at the owner's request
("I don't know what makes [a column] usable, the slit size or the
footprint").

**Look at:** (a) the footprint on the sample at true scale along the beam
(63.3 × 2.0 mm), the part the usable columns see (−12.8…30.6 mm), and,
below it in purple, the stretch S5 lets through (−13.3…49.4 mm): compare
their lengths directly. The small black bar is what one column sees
through S4 and its own pixel width: 2.1 mm. Columns of the second module
would look far off to either side. (b) The same on the column axis: a
column is usable when S5 passes it (27.2…139.3) **and** it sees the
footprint (2.7…102.0); here the low edge is set by S5, the high edge by
the footprint. The footprint window's edges are not sharp: through the
0.2 mm S4 each is a ramp (1.7…3.8 and 100.8…103.3; case 8), so the reader
stops at the ramp's inner edge, 100.8: usable columns 28–100, all fully
lit. IDL's window (hatched, now an option) is centred on c0 and ends 4.2
columns earlier (96.6), so it leaves out columns 97–100 (counts lost, no
bias; P39, fixed 2026-11-19). (c) Footprint length
against α for three S1 heights. (d) The columns that see the footprint
against α: they reach the second module (column 212) only below
α ≈ 0.037°, and S5 would still have to be opened.

**Why it matters:** it answers the owner's question: S5 (the slit size)
sets one edge, the footprint the other.

### Case 8 — What the finite S4 opening does
`case8_s4_opening.png` · scan 11, Det_Th 16°, row r0. Added 2026-11-19 at
the owner's request ("what effect S4 is having").

The reader treats S4 as a line through the centre of its opening (the
"pinhole"). On the NX data S4 is a 0.2 mm gap (S4L 0.1 + S4R 0.1 mm), a
little wider than a pixel (0.172 mm).

**Look at:**
- (a) Plan view (across the arm drawn ×5). Each column accepts a thin
  **bundle** of rays: from anywhere across its pixel, through anywhere in
  the gap. Behind S4 the bundle spreads again and meets the beam axis over
  a stretch: column c0 sees x = −1.1…1.1 mm of the footprint, column 28
  sees −13.9…−11.7 mm, and column 102, at the footprint's end, sees
  30.7…32.5 mm, of which only 52 % is lit. The inset shows the bundles
  narrowing to the 0.2 mm gap.
- (b) The spread of 2θ one column accepts. With the NX S4 it is 0.079°
  wide (2.2 columns; a triangle-like shape, since the gap and the pixel
  are about the same width), while the reader gives the column one angle
  and bins one column (0.036°) wide. S4 alone accounts for 0.042°
  (1.16 columns), the pixel for 0.036°. A 0.1 mm S4 would give 0.058°,
  0.4 mm 0.121°.
- (c) How much of each column near the footprint's downstream end is lit.
  With S4 as a line (pale, "pixel only") the edge is a step one pixel
  wide at column 102.0; through the real 0.2 mm S4 it is a ramp from
  100.8 to 103.3 (±1.2 columns; the low edge, ±1.1 columns, is hidden
  behind S5 anyway). With 1 mm it would spread over ±6 columns.
- (d) A wider or narrower S4, in columns (full widths): a column's 2θ
  acceptance, the footprint-edge ramp, and the ramp S4 puts on S5's edges.
  The last is tiny (±0.08 columns at 0.2 mm): seen from the detector, S5
  is close and S4 far, so S4's width hardly blurs S5's shadow.
- (e) The counts a column collects grow in proportion to the opening:
  ×5 at 1 mm, ×0.1 at 0.02 mm.

**The numbers** (NX, Det_Th 16°; at Det_Th 14° and 18° and on scan 12 the
2θ widths and ramps differ by less than 0.02 columns, while the stretch of
footprint a column sees grows as Det_Th falls: 2.4 mm at 14°, 1.9 mm at
18°):

| S4 opening (mm) | 0.05 | 0.1 | 0.2 (NX) | 0.4 | 1.0 |
|---|---|---|---|---|---|
| a column's 2θ acceptance, full width | 0.047° (1.29 col) | 0.058° (1.58) | 0.079° (2.16) | 0.121° (3.33) | 0.248° (6.81) |
| of which S4 | 0.011° | 0.021° | 0.042° | 0.085° | 0.211° |
| footprint seen by one column (mm) | 1.0 | 1.4 | 2.1 | 3.6 | 8.0 |
| footprint-edge ramp, high / low edge (columns) | ±0.30 / ±0.27 | ±0.61 / ±0.54 | ±1.21 / ±1.09 | ±2.43 / ±2.18 | ±6.06 / ±5.44 |
| S5-edge ramp (columns) | ±0.02 | ±0.04 | ±0.08 | ±0.16 | ±0.39 |
| counts per column (× NX) | 0.25 | 0.5 | 1 | 2 | 5 |

**Why it matters:**
- **Resolution.** The true 2θ resolution of the pinhole map is set by
  S4 and the pixel together, 0.079° full width at NX settings, about
  twice the bin step. Neighbouring bins therefore share resolution (not
  counts); a peak narrower than that cannot be resolved by narrowing the
  bins.
- **Edges.** With the NX settings every usable column is fully lit: the
  reader stops at `s4_window`'s inner edge (100.8, last column 100; dashed
  blue in (c)), and S5's edge at 27.2 is far inside the footprint. Going
  on to the exact footprint edge (102.0) would add columns that are only
  partly lit (column 102: 52 %), which the footprint weight would not
  know. IDL's window (dashed grey, an option) ends earlier, at 96.6.
- **Trade-off.** A wider S4 gives proportionally more counts per column
  and coarser 2θ; below about the pixel width (0.17 mm) narrowing S4 loses
  counts faster than it gains resolution, since the pixel then dominates.
- **Who limits what.** S5 decides which columns receive light (its
  shadow edges are sharp to ±0.08 columns); the footprint decides which
  columns see sample (edges ±1.2 columns); S4 decides how much light and
  how wide a 2θ range each column gets.

Functions: `column_acceptance` (the bundle: `ray_geometry` through
evenly spread points of the pixel and of the opening; `.lit_fraction`,
`.throughput`), `s4_window` (the ramps), `footprint_columns` (the exact
footprint window), `s5_window(slit_offset=…)`; `ray_geometry` takes a
`slit_offset` for a ray through any point of the opening. These were added
for this figure and change no existing result (`pixel_angles`,
`footprint_window`, `usable_columns`, `ray_geometry` bit-identical over
3000 random geometries; tests in `tests/test_pinhole.py` check them
against plain in-plane trigonometry).

## Private data

The same figures can be drawn from another SPEC file, e.g. the owner's
private GID scans, without anything entering the repository:

    python tests/tools/pinhole_figures.py --spec sample_data/private/gid_scans_136-146/gid \
        --low 163 --high 165 --label "private GID file" --out sample_data/private/figures/pinhole

`--low` and `--high` are the low- and high-Qz GID scans (standing in for NX
11 and 12). `sample_data/private/` is git-ignored, and the script refuses
to write figures of private data anywhere else inside the repository.

## Provenance and credit

`tests/tools/pinhole_figures.py`, 2026-11-19 (redrawn 2026-11-20 for the
P39 fix), from the public NX school data; each figure's header prints `git describe` of the code that drew
it. The exact pixel transform is Mati Meron's IMG_COO_CONV (version 7.1,
horizontal pinhole configuration; `docs/reference_code/idl/img_coo_conv.pro`),
ported as `pinhole.pixel_angles`; IDL's footprint window (the option
`footprint='idl'`) is his PD_PIN_RANGE.
`ray_geometry` is an independent construction of the same geometry, and
`tests/test_pinhole.py` checks the two against each other to 1e-12 rad.
