# Pinhole GID geometry: six isometric figures

Made by `python tests/tools/pinhole_figures.py [--out DIR]` (default: this
folder). The script draws only what the reader's own code returns:
`lss_core.pinhole.ray_geometry` (the lab-frame ray from the footprint
through the S4 slit to a pixel: n, e_h, e_v, h, the pixel, the slit
crossing, the footprint point, the direction, u, v, w, 2θ, β),
`pixel_angles` (the exact transform, a port of Mati Meron's IMG_COO_CONV),
`column_two_theta` / `row_beta` (the per-axis approximation),
`footprint_length`, `footprint_window`, `s5_window` and `usable_columns`.
The frame parameters (Det_Th, β0, α, c0 = 47, r0 = 53, D_s = 551 mm,
D_p = 271 mm, g_l3 = 556 mm, slits) and the module size (487 × 195, from
the image shape) are read from the public NX school SPEC file
`sample_data/NX_school/2026sep/20260923` by
`tests/tools/pinhole_frames.py`. The one typed constant is the 200K's
17-pixel gap between its two modules (DECTRIS 487 × 407 layout), from which
the second module's columns are derived. Pixels drawn with rays are chosen
from `usable_columns`, so every ray footprint → S4 → pixel that is drawn as
reaching the detector occurs; the exceptions (case 3's footprint-end
columns, case 6's second module) are said to be blocked where they appear. The script adds
only drawing offsets, arcs interpolated between two directions the reader
returned, the clipping of close-ups, and in case 3 a stated exaggeration
across the arm. All 3D panels are orthographic isometric views (elevation
35.264°, azimuth −45°: the eye on the (1, −1, 1) diagonal, so the beam runs
left to right; azimuth 45° is the same projection seen from behind the
detector) at equal scale on all three axes. Close-ups are the same view
zoomed; their magnification relative to panel (a) is printed on the panel.

Colours, one per kind of vector in every figure: vermilion k_in (beam);
blue the arm, n, and distances (D, D_p, the slit-crossing gap); green the
detector's e_h, e_v and the direct-beam row and column; magenta the pixel
offsets wx, wy and IMG_COO_CONV's u, v, w; black rays and their angles;
grey the lab axes and the per-axis approximation (dashed). Every vector is
labelled in its own colour, along it, rotated to its projected direction
on screen (computed from the axes' projection matrix); labels of one or two
characters (n, x, w, wy, e_v …) stay upright, since rotated they read as
other letters. The four hues pass
the dataviz palette validator's all-pairs normal-vision and contrast checks;
the colour-blind separation of magenta and green is in the 6–8 warning band,
which the direct labels cover.

## Why these six

The order goes from the frame of reference to the effects, smallest first:
what the coordinates are (1); where the old per-axis formulas are right (2);
the one physical fact that makes them wrong, the pinhole (3); its
consequence for β (4), the largest effect on the module in use; the extra
consequence when the arm is raised (5); and why it matters for the planned
second module (6). Q vectors (k_in, k_out, Q, Qxy, Qz) are not a case:
`lss_core.gid.products` computes Q from (2θ, β, α) by the standard formula,
which was never in question; the errors were all in the angles, so the
figures spend their space there.

## The figures

**case1_lab_frame_and_detector.png — lab frame and detector coordinates.**
NX scan 11 (low Qz level, β0 = 0.09°), Det_Th 16°. (a) The whole set-up at
true scale: k_in along x, the 63.3 × 2.0 mm footprint (`footprint_length`,
S1h), the arm and the distances D = `vertical_distance` = 551.0 mm and
D_p = 271 mm, the S4 slit line, the module outline (`ray_geometry` at the
corner pixels) and the ray from footprint point F through S4 to pixel P
(row 300, column 96, the last usable column; F at x = 28.5 mm, inside the
footprint; 2θ = 17.782°, β = 4.732°). (b) Close-up of the detector: n, e_h,
e_v (unit vectors drawn 20 mm long) at the direct-beam pixel (r0, c0), and
P's offsets wx = −(c − c0)p = −8.43 mm (negative: e_h points to lower 2θ)
and wy = (r − r0)p = 42.48 mm. Everything from `ray_geometry`.

**case2_direct_beam_row_and_column.png — per-axis angles: exact on the
direct-beam column, on the row only at β0 = 0.** Same frame. Rays to A (row
r0, column 96) and B (row 400, column c0), both in the usable columns, with
their 2θ and β drawn as arcs from the ray's own direction (`ray_geometry`).
On the direct-beam column the per-axis formulas are exact at any β0 (largest
difference 6e-15° over the column, at β0 = 0.09° and 6.5°). On the
direct-beam row they are exact only at β0 = 0: here (β0 = 0.09°) β is off by
up to 0.012° along the row (A: β 0.0953° exact, 0.0906° per-axis; 2θ
17.7813° both); on the high level (scan 12, β0 = 6.5°) by 1.02° over the
module and 0.34° inside the usable columns, and 2θ by 0.045°. Panel (b)
maps β per-axis − exact over the module (`pixel_angles` minus `row_beta`):
up to 1.06° in the corners; 2θ is off by at most 0.0013° at this arm height.

**case3_pinhole_top_view.png — every column sees its own footprint point.**
Same frame, rays to the direct-beam row. Through the narrow S4 slit a column
sees one point of the beam axis. (a) The fan at true scale. (b) Plan view in
the arm's frame with the distance across the arm drawn ×5 (stated on the
panel; rays stay straight under that scaling). The footprint's ends are seen
by columns 2.7 and 102.0 (found by solving `ray_geometry`'s source point =
±31.6 mm); `footprint_window` gives −2.6 and 96.6, the same width but
centred on c0 (dashed grey). `s5_window` gives 27.2…139.3; `usable_columns`
is 28…96 (pale blue), which see x = −12.8…28.5 mm of the footprint (dark).
The ray to column 2.7 passes S4 but S5 stops it; it is drawn to show where
the footprint's end would land.

**case4_beta_depends_on_column.png — why β depends on the column.**
Same frame. Two pixels on the top row (486) at the usable columns' ends, 28
and 96: their rays start at footprint points x = −12.8 and 28.5 mm, cross
the slit line 2.75 mm apart in height and leave at β = 7.620° and 8.187°
(0.567° apart), while `row_beta` gives the row 7.788° (off by up to 0.398°
inside the usable columns). (a) True scale, where the slit-crossing
difference cannot be seen; (b) a 12 mm box around the slit crossings, ×24
relative to (a), from the same `ray_geometry` points; (c) β along the row,
`pixel_angles` against `row_beta`.

**case5_raised_arm_uvw.png — raised arm: u, v, w; 2θ depends on the row.**
NX scan 12 (high Qz level, β0 = 6.50°), Det_Th 14°; D = 554.6 mm (the arm
term g_l3(1/cos β0 − 1) adds 3.6 mm). (a) The segment from the slit point
S to pixel P (row 486, column 90, the last usable column) split as
u·e_h + v·h + w·z, the (u, v, w) of IMG_COO_CONV (u = −7.40, v = 264.74,
w = 70.37 mm; 2θ = 15.600°, β = 14.879°), and the rays of rows 486 and 0 of
that column. (b) 2θ exact − per-axis against the row for columns 0, 28, 47,
90 and 194. It spans 0.029° along column 90. The module's edge column 194
shows the largest effect: a span of 0.108° (0.034…0.142°) with the arm
raised, against 0.0015° (−0.0002…0.0013°) for the same column with the arm
level (scan 11, dashed grey). Columns 0 and 194 get no light (S5 passes
27.2…139.3, the footprint window 3.3…90.7) and appear in (b) only, marked
"no light".

**case6_second_module.png — where the 200K's second module would be.**
The 200K is one detector of two 487 × 195 modules with a 17-pixel gap; the
module not used would sit at columns −212…−18 or 212…406 of this module's
numbering (derived from the image width and the gap). Scan 12, Det_Th 14°.
(a) True scale, rays to the modules' end columns (row r0); (b) the three
modules ×2, coloured by β per-axis − exact (`ray_geometry` at a 24 × 10 grid
of pixel corners, colours from `pixel_angles` and `row_beta`); (c), (d) the β
and 2θ errors along the top and bottom rows. Per-axis is off by up to 7.1°
in β and 0.39° in 2θ there, against 2.2° and 0.14° on the module in use.
With the present slits that module would get no light: S5 passes columns
27.2…139.3 only, and through the S4 pinhole those columns look at beam-axis
points x = −58…−559 mm and 87…140 mm, outside the ±31.7 mm footprint
(`footprint_window`: columns 3.3…90.7). The rays in (a) are drawn to show
where those columns look.

## Provenance and credit

`tests/tools/pinhole_figures.py`, made with lss_core at commit 3eb11aa (the commit
that adds `pinhole.ray_geometry`; each figure's header prints
`git describe`), 2026-11-19, from the public NX school data. The exact
pixel transform is Mati Meron's IMG_COO_CONV (version 7.1, horizontal
pinhole configuration; `docs/reference_code/idl/img_coo_conv.pro`), ported
as `pinhole.pixel_angles`; the footprint window is his PD_PIN_RANGE.
`ray_geometry` is an independent construction of the same geometry, and
`tests/test_pinhole.py` checks the two against each other to 1e-12 rad.
