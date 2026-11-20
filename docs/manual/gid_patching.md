# GID patching: the options, and what each costs (technical addendum)

Part of the user manual, as a technical addendum (owner, 2026-11-20). It
describes how LSS_Reader2 turns a set of Pilatus frames from grazing-incidence
diffraction (GID) scans into one map of intensity against (2θ, β) or
(Qxy, Qz), every option that changes that map, and the advantages and
disadvantages of each choice. Numbers are from the public NX school data
(`sample_data/NX_school/2026sep/20260923`, GID scans 11 and 12) unless
stated. **Measured** marks a number obtained by running the reader; **read**
marks something established by reading code or documents only.

Where to find things: the window's GID menu > Worksheet holds every setting
below; scripts use `Experiment.gid(scans, params=GIDParams(...))`
(`docs/SCRIPTING.md`, "GID maps"); the code is `lss_core/gid.py` (legacy
patch, settings, output) and `lss_core/pinhole.py` (pinhole patch). Every
output-changing default is also in `docs/OUTPUT_DECISIONS.md`; open physics
issues are the P-numbers in `docs/PHYSICS_ISSUES.md`.

Figures: `docs/manual/figures/gid_patching/`, made by
`python tests/tools/gid_patching_diagrams.py` from the reader's own geometry
code and the NX data.

---

## 1. Terms

The same words are used in the worksheet, in the figures and below.

| Term | Meaning | Figure |
|---|---|---|
| **frame** | One detector image: rows × columns (487 × 195 on NX, one 200K module). | 1 |
| **row**, **column** | Vertical and horizontal pixel index. Rows go with the exit angle β, columns with the in-plane angle 2θ. | 1 |
| **direct-beam pixel** (c0, r0) | Where the direct beam would hit the detector at the frame's arm position. | 1 |
| **Det_Th** | The detector arm's in-plane angle for a frame. A **scan** sweeps Det_Th in steps. | 2, 3 |
| **arm height** β0 | The arm's elevation. Raising the arm reaches higher β, i.e. a higher Qz **level**. | 4, 5 |
| **Qz level** | All frames taken at one arm height (one or more scans). NX scan 11 is the low level (arm level), scan 12 the next (arm raised to β0 = 6.5°). | 5 |
| **sample horizon** | The row where β = 0; nothing from the surface reaches below it. | 1 |
| **rows used** | `row_min`–`row_max` (default 15–486): the rows taken from every frame. | 1 |
| **S5 window** | Columns that the S5 slits (in front of the detector) let through. | 1 |
| **footprint window** | Columns that see the lit strip of sample (the footprint) through the S4 pinhole. **Exact** (default): traced ray by ray, fully lit through the whole S4 opening. **IDL's**: the same width, centred on c0 (an option). | 1, 2 |
| **usable columns** | S5 window ∩ footprint window: the columns the pinhole patch uses. | 1, 3 |
| **legacy column band** | The few columns around c0 (default 3) that the legacy patch sums. | 1, 3 |
| **2θ bin**, **β bin**, **cell** | The pinhole map's grid: 2θ bins one column wide (pixel / S4–detector distance), β bins one row wide (at the direct beam); a cell is one (2θ bin, β bin). | 4 |
| **2θ resolution** | The spread of 2θ one column accepts through the S4 opening plus its own width: 0.079° = 2.2 columns on NX (S4 0.2 mm; measured). It is coarser than one 2θ bin. | 3 |
| **2θ overlap** | 2θ bins seen by two scans of the same level: where the **scan join factor** is fitted ("horizontal join"). | 3 |
| **β overlap** | β bins seen by two Qz levels: where the **level join factor** is fitted ("vertical join", "Qz join"). | 5, 6 |
| **map edges** | 2θ bins seen by fewer than `min_frames` frames; left out. | 3 |
| **transverse range** | The 2θ range of a map joined from several levels: 'intersection' (bins every level has; default, as the IDL code) or 'union' (all). | 5 |
| **edge copies** | Legacy patch only (P33): where the vertical join fills a level's missing 2θ range with copies of its edge column. | 5 |
| **column response** | A sensitivity factor per column ('fit'), or one profile along the beam axis ('beam'), estimated from the data. | — |

## 2. What happens to the frames, in order

1. **Frames are read and normalised.** Each frame's counts, monitor
   (Monc), absorber setting and angles come from the SPEC file and the
   image. Bad pixels can be replaced (`bad_pixel_iterations`, `factor`);
   background-subtracted frames can be used from the window (not from
   scripts yet).
2. **Frames are grouped into Qz levels** by their Qz rounded to
   `qz_decimals`, and ordered by Det_Th rounded to `dth_decimals`.
3. **Each frame contributes columns at angles.** Legacy: the legacy column
   band, summed, placed at the frame's Det_Th. Pinhole: every usable column,
   each pixel at its own exact (2θ, β) (figure 2, figure 4).
4. **Weights.** Each pixel's weight W is its monitor × the area
   (footprint) correction × the polarisation factor × the column response.
5. **One map per level.** Legacy: the frames' profiles side by side, scans
   joined in their 2θ overlap by interpolation. Pinhole: counts N and
   weights W summed into cells, value ΣN/ΣW, scans joined by a fitted
   factor applied to W (figure 3, figure 4).
6. **Levels are joined** in their β overlap by a fitted factor (figure 5,
   figure 6), and the map is cut to the transverse range.
7. **Output.** The map on Angles (2θ, β) or regridded on Q (Qxy, Qz), with
   its integrals over each axis and four slices; "Save GID" writes three
   files and the equivalent script call.

## 3. The two patch methods

### Legacy patch (`pinhole=False`; "Pinhole: angle per column" unticked)

The original program's method. From each frame it sums the legacy column
band around c0 (default 3 columns) into one profile against β, and places
that profile at the frame's Det_Th. Scans of a level are joined by a factor
fitted on the ratio of their β-summed profiles in the 2θ overlap (the
second scan linearly interpolated onto the first's angles), then averaged
in the overlap. Levels are joined by interpolating the upper level onto the
lower level's 2θ grid and fitting one factor on the β-integrated profiles in
the β overlap (`vjoin_kind`, cubic by default).

| Advantages | Disadvantages |
|---|---|
| Simple; reproduces every map made with the original program exactly (tests pin it). | Uses 3 of ~70 lit columns: on NX scan 11, 3.2 × 10⁴ counts against 5.65 × 10⁵ for the pinhole patch (measured; 15–17× fewer). Relative errors on equal bins 3.8× larger (measured, C10). |
| No assumption about the pinhole geometry: valid without a pinhole (Det_Th ≤ 1°, or no S4). | Each frame gives one 2θ: the map's 2θ step is the Det_Th step, and the column band's own width (3 columns ≈ 0.11°) blurs it. NX Bragg peak FWHM 0.0180 ± 0.0009 against 0.0155 ± 0.0002 Å⁻¹ pinhole (measured). |
| Familiar to existing users. | β taken per row from the sample distance: exact only at the direct-beam column of a level arm (P38). |
| | Joins interpolate (linear, cubic), so overlap values are smoothed and errors correlated; the vertical join copies the upper level's edge column over 2θ it never measured (edge copies, P33); the relaxed Q grid fills empty regions with 1e-10, which integrated cuts sum as data (P33). NX 11 + 12 level factor 0.900 ± 0.048 with χ²/dof 9.2 (measured). |
| | Known defects with three Qz levels: first high-level frame not rescaled by the monitor (P36, P31); one high-level scan picks the middle level's key (P37). Footprint correction 2 % asymmetric in ±2θ (P5). |

### Pinhole patch (default; `pinhole=True`)

With the S4 slit acting as a pinhole in front of the detector (NX: S4 0.2 mm,
271 mm from the detector), each detector column looks through S4 at one
point of the footprint, so each column has its own 2θ (figure 2). The
pinhole patch uses every usable column of every frame, with exact per-pixel
angles (Mati Meron's IMG_COO_CONV transform, `pinhole.pixel_angles`): β
depends on the column (each column sees another part of the footprint, at
another distance), and 2θ on the row when the arm is raised (figure 4).
Counts and weights go to cells; a cell's value is ΣN/ΣW. Scans of a level
and the levels themselves are joined by fitted factors on shared cells,
without interpolation (figure 6).

| Advantages | Disadvantages |
|---|---|
| All usable columns: ~15–17× the counts of the legacy band on NX (measured). | Depends on geometry the file must describe correctly: S4–detector distance, S4 opening, S5 opening, S1 vertical, α, c0. A wrong pinhole distance smears features (a distance fitted from the data ranged 258–280 mm on NX, so the header value, 271 mm, is the default; measured). |
| 2θ per column: bins one column wide (0.036° on NX), true resolution 2.2 columns, set by S4's opening (measured). | Needs a column response (relative sensitivity and illumination of each column), estimated from the data; with a narrow beam it varies with Det_Th (see "Column response"). |
| Exact angles: on NX β per row was off by up to 0.41° (arm level) and 0.74° (arm raised) inside the usable columns; joining with exact angles took the NX level join's χ²/dof from 1.31 to 0.83 (measured, P38). | Only valid where there is a pinhole: at Det_Th ≤ 1° the reader uses no pinhole (IDL's rule). |
| No interpolation: overlap cells hold summed counts, errors stay Poisson (ΣN). Counts are conserved (invariant I21, tested). | Light that does not come from the footprint through the pinhole (beam-path scattering, slit scattering, P40) is treated as signal; the exact window and the raised arm interact with a stray-light streak (see "Footprint window"). |
| NX Bragg peak: σ/I 1.02 % per own bin against 2.55 % legacy; level join 1.068 ± 0.013, χ²/dof 0.93 (measured). | The level join factor depends on which columns each level uses when the illumination along the beam changes between the levels' scans (sample height drift of a few µm moves the footprint by mm at α = 0.09°; owner, 2026-11-19). The joined map stays consistent; the factor's value is a normalisation. |

## 4. The options

Defaults are what a user gets without changing anything. "Worksheet" is
the label in GID > Worksheet; `name` is the `GIDParams` field.

### 4.1 Frames and levels (both methods)

| Option | Values (default) | Advantages | Disadvantages |
|---|---|---|---|
| Rows (`row_min`, `row_max`) | 0–486 (15–486) | Leaves out the bottom rows (shadow, beam stop) and so the region below the sample horizon. | Rows cut away reduce the β range; the top rows of the lower level are the β overlap with the next level, so cutting them shrinks the overlap. |
| Qz grouping, decimals (`qz_decimals`) | integer (3) | Frames whose Qz differs only by rounding form one level. | Too few decimals merges distinct levels; too many splits one level into several. Legacy: at most three levels (low, middle, high), any further level goes into "high". |
| Det_Th rounding (`dth_decimals`) | integer (3) | Orders frames robustly against motor jitter. | Legacy only in practice; too few decimals merges distinct frames. |
| Frames (`points`), direct beam (`db_pos`) | all frames; from the header | Leave out bad frames; correct a wrong c0, r0. | A typed c0 applies to all frames. |
| Bad pixels (`bad_pixel_iterations`, `bad_pixel_factor`) | 0 (off), 1 | Removes hot pixels. | The threshold factor is used for detection but not for replacement (P16). |
| Background-subtracted frames | off | Removes a measured background. | Window only (not scriptable yet). |

### 4.2 Which columns, at which angle

| Option | Values (default) | Advantages | Disadvantages |
|---|---|---|---|
| Pinhole: angle per column (`pinhole`) | on / off (on, D40) | See section 3. | See section 3. |
| Columns per frame (`columns`, legacy only) | integer (3) | A wider band gives more counts. | Blurs 2θ by the band's width (the band is placed at one angle); the area correction must follow (it does, through the band width). |
| Footprint window (`footprint`, pinhole) | exact / IDL (exact, D51) | **Exact**: uses every column that sees the footprint through the whole S4 opening: on NX +3.3 % counts, 2θ to 19.93° (IDL: 19.82°), Bragg peak unmoved (measured). **IDL's**: reproduces earlier maps and the IDL code exactly. | **Exact**: on raised-arm frames (β0 > 1°) the high edge stays at IDL's, because the extra 3–4 columns there catch a stray-light streak (P40b; NX: 2.4× brighter in rows 60–150 than lower rows, against 1.5× in the old edge columns; measured). So only the lower level gains the edge columns, which shifts the NX level factor from 1.097 to 1.068 ± 0.013 (a normalisation, not an error of the map). **IDL's**: drops a few lit columns at the high-2θ edge (P39). |
| S4–detector (mm) (`pinhole_distance_mm`) | number (0 = header, 271 on NX) | A typed value overrides a wrong header. "Fit" estimates it from a feature's drift (diagnostic). | The fit depends on the column response by several mm (258–280 on NX); use it to check, not to set. |
| Arm correction (`arm_correction`) | on / off (on) | Includes the arm's own offset (`g_l3`) in the sample–detector distance used for β. | — (off only to compare with older maps). |

### 4.3 Weights

| Option | Values (default) | Advantages | Disadvantages |
|---|---|---|---|
| Area correction (`area_correction`), hard slit offset (`hard_slit_offset_mm`) | on (on), 32 mm | Divides by the fraction of the footprint the slits let the detector see, which changes with Det_Th. The 32 mm shortens the sample–detector distance with hard slits. | Uniform footprint assumed (S1v / sin α); a narrow Gaussian beam is not uniform (see "Column response"); 2 % asymmetric in ±2θ (P5). |
| Polarisation (`polarisation`) | on (on) | Divides by 1 − (sin 2θ cos β)², the horizontally polarised synchrotron beam's factor. | Not small: 5.1 % at 2θ = 13°, 7.6 % at 16°, 11.7 % at 20° (from the formula, β = 0), changing across a map; off only to compare. |
| Column response (`response`, pinhole) | fit / beam / none (fit) | **fit**: one factor per column, estimated from the data (the same 2θ is seen by many columns in different frames): absorbs pixel sensitivity, S4 and S5 edge effects and the mean illumination. **beam**: one profile along the beam axis shared by all frames: through S4 each column sees one point of the footprint, and that point moves with Det_Th, so a narrow beam lights a column differently in each frame; it also measures the beam's size and position on the sample (NX: footprint FWHM 33 mm along the beam, i.e. ≤ 52 µm vertically; 36 µm above the beyond-footprint floor; measured). **none**: flat. | **fit**: cannot follow illumination that changes from frame to frame: on synthetic frames lit by a 30 µm beam, 0.93–1.04 of the truth inside, 0.71–2.8 at the edges (measured). **beam**: 0.98–1.02 inside, 0.88–1.04 at the edges on the same frames (measured), but assumes the illumination is the same for all frames of a level (sample height drift breaks this) and does not absorb pixel-to-pixel sensitivity. **none**: no correction at all. |

### 4.4 Binning (pinhole)

| Option | Values (default) | Advantages | Disadvantages |
|---|---|---|---|
| 2θ bin width | one column, p/D_p (0.036° on NX) | Keeps all the information; levels share one 2θ grid (`shared_edges`), so their bins coincide and need no interpolation. | Finer than the true resolution (2.2 columns): neighbouring bins are correlated. Coarser bins (per-column resolution, ~2 columns) are a pending decision. |
| β bin width | one row at the direct beam; the joined map uses the largest row step of any level | No level skips a β bin. | An assumption (OUTPUT_DECISIONS, open). |
| Frames per bin, at least (`min_frames`) | integer (2) | Drops map edges seen only by one frame's weakest columns. | Higher values shrink the 2θ range; an assumption (open). |
| Overlapping pixels in a cell | ΣN/ΣW (counts over weights) | Unbiased at low counts (0.4 counts/pixel: 1.00 ± 0.01; invariant I21, tested). | Departs from IDL, which weights each pixel by its own error (biased at low counts: 0.31× the true mean at 0.4 counts/pixel, IDL review); **to confirm with the owner**. |

### 4.5 Joins

| Option | Values (default) | Advantages | Disadvantages |
|---|---|---|---|
| Scan join (within a level) | pinhole: one factor per scan on the 2θ-overlap profiles, applied to W; legacy: interpolated ratio fit, then the overlap averaged | Pinhole: no interpolation, counts conserved. | Pinhole: each further scan is fitted against the **first** scan of the level, so every scan must overlap the first; scans that overlap only in a chain (A–B, B–C) leave the factor undefined (P41, read only). Legacy: a scan with no overlap is placed unscaled, with a warning. |
| Level join (between levels) | pinhole: one factor per level on the β overlap, equal weight per cell (figure 6); legacy: β-integrated profiles, interpolated (`vjoin_kind`: cubic) | Equal weight per cell avoids the 2.6 % bias of summed counts, which weight a 2θ feature differently in each level (measured on synthetic data). The factor's error is carried into the map's errors (its relative error × the level's share of the weight). | The factor depends on the columns used when the illumination changed between the levels' scans (section 3); the β overlap is short (NX: β 6.1–7.6°, 84 β bins), at the lower level's top rows and the upper level's bottom rows, where stray light (P40) lies. |
| 2θ range across levels (`transverse`) | intersection / union (intersection) | **intersection**: every 2θ bin has every level, as the IDL code (IMG_JOIN). **union**: keeps all measured 2θ. | **intersection**: a short level (NX scan 12: 4 frames, 2θ 13.4–15.8°) cuts the whole map to its range. **union**: NaN where a level is missing at that β. |
| GID Patch Relax (`relax=True`) | off | The Q map on the largest rectangle the data reach. | Fills empty regions with 1e-10, which the integrated cuts sum as data (P33). |

### 4.6 Output

| Option | Values (default) | Notes |
|---|---|---|
| Axes | Angles (2θ, β) / Q (Qxy, Qz) / Pixels | Q: the (2θ, β) map regridded linearly onto (Qxy, Qz) with the first frame's α (a second interpolation). "Save GID" needs Angles or Q. |
| Integrals and slices | h (over the vertical axis), v (over the horizontal), four vertical slices | Written by "Save GID"; the slices split the positive vertical range into four. |

## 5. Choosing

- **Most data (pinhole slit set, Det_Th > 1°):** the defaults: pinhole,
  exact footprint window, response 'fit', intersection. Look at the worksheet's
  join table: a level factor with χ²/dof well above 1 means the levels
  disagree in their β overlap (illumination change, stray light, wrong
  geometry).
- **A narrow, well-focused beam, or illumination that changes with Det_Th:**
  try response 'beam' and compare; its centre and FWHM on the sample are a
  check of the beam (a half-cut scan next to each GID level measures it
  directly; F43).
- **Reproducing an old map or the IDL code:** legacy patch (pinhole off)
  for the original program; footprint window "IDL" for the IDL code's
  pinhole columns.
- **A short or aborted level:** 'union' keeps the other levels' full 2θ
  range; the join factor rests on fewer cells.
- **Comparing levels quantitatively:** remember that a level factor is a
  normalisation fitted where the levels overlap; it moves when the columns
  used change (section 3).

## 6. Known limitations

P5 (area correction asymmetry), P16 (bad-pixel replacement), P31/P36/P37
(legacy, three levels), P33 (legacy edge copies, relaxed fill), P38 (per-axis
angles still used in cuts and image axes), P39 (fixed: exact window), P40
(stray light; raised-arm exception), P41 (pinhole scan join against the
first scan only), and the open assumptions in
`docs/OUTPUT_DECISIONS.md` (minimum frames per bin, β step, ΣN/ΣW vs IDL
weights, the 1° raised-arm threshold). Comparisons behind the numbers above:
`docs/COMPARISONS.md` C10, C11, C14, C21–C24; figures of the geometry:
`docs/figures/pinhole/`; before/after maps: `docs/figures/gid_compare/`;
the beam profile: `docs/figures/pinhole_beam/`.

## Figures

1. `01_frame_anatomy.png` — one frame: direct-beam pixel, rows used, sample
   horizon, S5 window, footprint windows, usable columns, legacy band.
2. `02_columns_to_two_theta.png` — from above: each column sees one point of
   the footprint through S4, so each has its own 2θ.
3. `03_frames_cover_two_theta.png` — which 2θ each frame's usable columns
   reach, frames per 2θ bin, map edges, 2θ overlap, bin width against
   resolution.
4. `04_pixels_to_cells.png` — exact pixel angles over the (2θ, β) cell grid,
   arm level and raised.
5. `05_levels_and_overlaps.png` — two Qz levels in (2θ, β), the β overlap,
   intersection and union, the legacy edge copies.
6. `06_join_factor.png` — how a level join factor is fitted.
