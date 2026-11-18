# Hand-off 04, answer: what the IDL pinhole/GID code knows that the reader does not

Written 2026-11-18 by a reviewing agent, for the brief
`docs/handoff_out/04-idl-pinhole-review.md`, and updated the same day
after the second batch of IDL files. Read-only review: no file other than
this one was written.

**How to read this report.** Three kinds of statement are kept apart:

- **Code says** — quoted from a file, with `file:line`. IDL files are in
  `docs/reference_code/idl/`. `mainwindow.py` line numbers are as read on
  2026-11-18 (HEAD `ada40cc` plus another agent's uncommitted edits); they
  move, so search by function name.
- **Inferred** — my reading of what the code or the geometry implies. No
  IDL interpreter was available; nothing in IDL was run.
- **Measured** — computed here from the committed NX school data
  (`sample_data/NX_school/2026sep`, SPEC file `20260923`; Pilatus 100K
  frames read with `lss_core.images.read_pilatus`, i.e. in the reader's
  array orientation, 487 rows × 195 columns), or from synthetic input where
  stated. Nothing was written into `sample_data/`. Appendix A has the
  details.

Citations marked *(from memory)* were not checked against the source here.

---

## Update after the second batch (2026-11-18, evening)

**Received:** `scan_pd_read.pro` (v7.0), `scan_pd_lcoo.pro` (v8.421),
`pd_pin_range.pro` (v7.08), `pd_gid_read.pro` (v7.0), `img_join.pro`
(v7.0). The owner also gave first answers: S4 is the usual pinhole slit;
"every SPEC header gives the sample-to-slit distance; the detector-to-sample
distance is known elsewhere"; `S7D_Dist` is antiquated and its meaning is
not firm.

**What changed in the findings.**

1. **The distances are now defined by the code** (§1.1). In IDL's current
   convention, `PDIST` is sample→detector, `PDSDIST` is pinhole(S4)→detector,
   and `PDIST − PDSDIST` is sample→pinhole (`pd_pin_range.pro:73-77`,
   `scan_pd_lcoo.pro:100-101`). A "legacy" setting uses `PDIST − PDSDIST`
   as the pinhole distance (`scan_pd_read.pro:205-209`). This means the
   second distance has meant both things over the years, which matches the
   owner's "antiquated, not firm".
2. **Re-measured on scan 11, with the column response divided out** (§2.3).
   The pinhole→detector distance is **267 ± 2 mm**. The earlier 256–265 mm
   was pulled low by centroid bias. This favours 271 over 280 (= 551 − 271)
   by ≈ 6σ. The owner says the header gives the sample-to-slit distance. If
   that is the 271, the sample→detector distance would be ≈ 538 mm, not 551.
   **The data cannot yet decide between "551 and 271 = S4→detector" and
   "271 = sample→S4, detector at ≈ 538"** (§8 Q1). The G_L[3] term does not
   explain the 4 mm: it is 0.0007 mm in scan 11.
3. **Pinhole is IDL's default for every frame with Det_Th > 1°**
   (`scan_pd_lcoo.pro:100-101`). IDL treats all GID data as pinhole data.
4. **`PD_GID_READ` formulas** (§2.2). The β per row, Qxy and Qz agree with
   the reader to 1×10⁻¹² (measured, scan 11), except for one distance
   correction the reader lacks: `dist = PDIST + G_L[3]·(1/cos(Out_Rot) − 1)`.
   On scan 12 (Out_Rot 6.5°) this changes β at the top row by 0.049° and
   Qz by 0.004 Å⁻¹.
5. **`IMG_JOIN` is now known except for its 1D core `SCAN_JOIN`** (§3.3).
   - It joins the 1D integrated profiles to get one factor per image.
   - It propagates the factor's error.
   - It combines overlap pixels with **inverse-variance weights from the
     data's own errors**, which is strongly biased for GID pixels that hold
     ≈ 0.4 counts (measured: 58–72 % of pixels are zero; simulated bias
     −69 % at 0.4 counts). The reader must not copy that literally.
   - It keeps **only the common transverse range** (the intersection), not
     the union.
   - It has a probable bug: the error page is rebuilt from the data page.
   - Horizontal joins inside `PD_GID_READ` overwrite overlapping frames
     with the later scan, without averaging.
6. **New reader bug, measured on synthetic input.** `cuts.frame_cut` "Pix V"
   uses the pinhole distance for the vertical β axis when the pinhole box
   is on, which doubles β (§5.1).
7. **`PD_PIN_RANGE` centres the observable range symmetrically on the
   direct-beam column.** For NX scan 11 (S5 3/14 mm) this gives columns
   ≈ 0–98, while the S5 shadow is 29–137. The geometry is right but the
   centring is wrong for an asymmetric S5. My S5 projection matches the
   data (§1.2, §2.3).
8. **Version caveat.** `PD_GID_READ`, `SCAN_PD_READ` and `IMG_JOIN` are
   v7.0 (2008), older than their callers (v8.3–8.475, 2014–2016). For
   example, `PD_GID` passes `SLIT`, `YOFF` and `SIN_NORM`, and
   `PD_GIPI_MERGE` passes `/TRAN`; none of these exist in the v7.0 files.
   Newer versions may differ.
9. **The spec (§7) is revised:**
   - the distance model has two settings: the pinhole distance, and the
     sample→detector distance with the G_L[3] term;
   - pinhole is on by default for Det_Th > 1°;
   - the window is the asymmetric S5 projection intersected with the
     footprint visibility;
   - joins: IDL's factor and its error propagation, and IDL's
     common-transverse-range rule as the default;
   - overlap combination: count-weighted, not data-variance-weighted.

   §8 drops the questions now answered. §6 lists the routines still
   missing: `IMG_COO_CONV`/`LIMG_COO_CONV`, `SCAN_JOIN`, `SPEC_FILE_INFO`,
   `IMG_TRIG`.

---

## 0. Top findings (as revised)

1. **"Pinhole" is a measurement geometry, and IDL's default for GID.** A
   narrow S4 slit on the detector arm images the footprint like a pinhole
   camera. Each detector column then sees one in-plane direction, at the
   pinhole→detector distance `PDSDIST`. The vertical direction keeps the
   sample→detector distance `PDIST`. `PD_PIN` reads such data with one
   angle per pixel column. `PD_GID` keeps one column per frame, as the
   reader does. `PD_MERGE` grafts a pinhole map into a GID map.
   `SCAN_PD_LCOO` switches pinhole on for Det_Th > 1°.
2. **The NX school GID scans are pinhole data** (measured). S4 is
   0.1 + 0.1 mm. A Bragg peak drifts 27.1 ± 0.1 columns per degree of
   Det_Th, i.e. a distance of 267 ± 2 mm; 551 mm would give 55.9 columns
   per degree. The lit window (29–137) matches S5L/S5R projected from the
   pinhole.
3. **The reader uses about 4 % of the counts of these frames.** The sample
   is seen over ≈ columns 30–80 with a non-flat response, so a per-column
   response normalisation is needed.
4. **Pixel→angle:** `PD_GID_READ` gives β, Qxy and Qz explicitly; they equal
   the reader's except for the G_L[3] distance term. The per-pixel pinhole
   formula itself is in `IMG_COO_CONV` (still missing). Its inputs
   (`dist`, `pdist`, `cent`, α = In_Rot, β = Out_Rot, Det_Th, `/xrev`) and
   `PD_PIN_RANGE`'s pinhole geometry leave little doubt about its form:
   `Det_Th + atan(Δx·p/PDSDIST)` (inferred).
5. **Joins (`IMG_JOIN`):**
   - one factor per image, from the integrated 1D profiles (via
     `SCAN_JOIN`), applied with its error;
   - the overlap combined by inverse-variance weights;
   - the result cut to the common transverse range and regridded by
     triangulation.

   The inverse-variance step is biased for low-count pixels (see the
   update, item 5).
6. **The reader's area correction equals IDL's `SIN_NORM`** for scan 11's
   slits (measured, §4).

---

## 1. What "pinhole" means here (question 1)

**Code says.**

- `pd_view.pro:55-59`, `scan_pd_lcoo.pro:34-37`, `scan_pd_read.pro:60-66`:
  `PINHOLE` = "horizontal pinhole angle transformations", using `PDSDIST`.
  In `SCAN_PD_READ`, a negative value gives `PDIST − PDSDIST` instead
  ("legacy setting"; the header comment says `PDSTAT − PDSDIST`, but the
  code at `:206` uses `pdist`). Zero means no pinhole (`:205-209`).
- `scan_pd_lcoo.pro:100-101`: `if cur.pdfar then … else if
  Default(pnh, angs[2] gt 1) then pdist = cur.pdsdist`. **Pinhole is the
  default when Det_Th > 1°**, unless the far-detector option is set.
  Otherwise `pdist` stays undefined and no pinhole transform is applied.
  (The keyword dates from 20-JUL-2014, `:73`.)
- `pd_pin.pro:298-301, 320-322`: `PD_PIN` always reads with `/pinhole`. Its
  raw horizontal unit is the pixel (`:365`). `PD_GID`'s is the frame
  (`pd_gid.pro:350`).
- `pd_merge.pro:25-27`: GID and pinhole maps share one format and differ
  only in how they were measured.

### 1.1 The distances (code says, then inferred)

| Quantity | Code | Meaning |
|---|---|---|
| `PDIST` | `dist = cur.pdist + G_L[3]·(1/cos β − 1)` used for the vertical (`scan_pd_read.pro:204`, `scan_pd_lcoo.pro:95`, `pd_pin_range.pro:85`); `PD_GID_READ` reads it as `'Pdist'`, "detector distance" (`pd_gid_read.pro:111-112, 225`) | **sample → detector** |
| `PDSDIST` | horizontal distance with pinhole on (`scan_pd_read.pro:208`, `scan_pd_lcoo.pro:101`, `pd_pin_range.pro:86`); converts the angle at the pinhole to pixels, `pix = PDSDIST·ψ/adpix` (`pd_pin_range.pro:77`); S5 sits at `PDSDIST − 32` from the pinhole (`:76`) | **pinhole (S4) → detector**, current convention (2008–2015 code) |
| `PDIST − PDSDIST` | `lmlp`, the distance from which the footprint is viewed (`pd_pin_range.pro:73-75`); also the "legacy" pinhole distance (`scan_pd_read.pro:206`) | sample → pinhole in the current convention; in the legacy convention `PDSDIST` held sample → pinhole, so `PDIST − PDSDIST` was pinhole → detector |
| 32 | `pd_pin_range.pro:76` | S5 → detector, mm. This is the same 32 mm as the reader's `hard_slit_offset_mm` (`calArea`) |
| `G_L[3]` | `(Scan_field_read(snum,'G_L'))[3]` (`scan_pd_read.pro:203`); `cur.g_l[3]` | **inferred:** the reader's `g_l3` (`#G0` 8th value, 556 mm in NX), since the reader's `g_l1`, `g_l2`, `g_l3` (`spec_routines.py:119-122`) are `#G0` items 6–8 and IDL indexes `G_L[1..3]`. `G_L[2] − G_L[1]` (678 mm) is used as a distance in m ×10³ for the slit diffraction width (`pd_pin_range.pro:68-70`) |
| `PDXC`, `PDYC` | the "specular channel" (`pd_gid_read.pro:111-112, 227`) and the centre; `cent = [addim[1] − pdyc, pdxc]` in vertical orientation (`scan_pd_read.pro:197`) | the direct beam; from `#B1` items 1–2 (inferred; `SPEC_FILE_INFO` missing) |

**Which header items?** The reader parses `#B1 53 147 551.000000 271.000000`
as DBPos = (53, 147), `S2D_Dist` = 551, `S7D_Dist` = 271
(`spec_routines.py:145-157`). The most likely IDL mapping, by order, is
`pdyc`/`pdxc` = 53/147, `PDIST` = 551, `PDSDIST` = 271 (inferred;
`SPEC_FILE_INFO` missing). No other header line holds a distance: `#G0` has
the diffractometer lengths (560, 1238, 556), and the slit motors are in
`#P` lines. The owner says the header gives the sample-to-slit distance; read
literally, that is the 271. The measurement in §2.3 then decides how the
two numbers relate:

| Reading | sample→S4 | S4→detector | sample→detector | Fits the measured 267 ± 2 mm? |
|---|---|---|---|---|
| A: 551 = PDIST, 271 = PDSDIST (IDL current convention) | 280 | **271** | 551 | yes, 1.5 % (2σ) short |
| B: 271 = sample→S4 (owner), detector distance "known elsewhere" | 271 | **267** (measured) | ≈ 538 | yes, by construction; then 551 is not the detector distance |
| C: 271 = sample→S4 and 551 = sample→detector (IDL legacy) | 271 | **280** | 551 | no: 4.6 % (≈ 6σ) off |

So C is excluded. A and B differ in the **sample→detector** distance (551 vs
≈ 538, 2.4 %), which sets the β and Qz scale. Scan 11 alone cannot
test that (§2.3, last paragraph).

### 1.2 Slits

**Code says:**

- S1's vertical gap comes from `total(sl_val[*,1][0:1])`
  (`pd_pin_range.pro:67`), i.e. S1T + S1B. (The reader adds S1T twice, P13.)
- S5's two horizontal blades come from `sl_val[2,5]` and `sl_val[3,5]` (`:76`).
- The footprint uses the S1 gap broadened by slit diffraction over
  `G_L[2] − G_L[1]` (`:68-71`).

The observable angular range seen from the pinhole is
`ψ = min(atan2(2δ sin Det_Th, 1 − δ²), atan(S5L, PDSDIST−32) + atan(S5R, PDSDIST−32))`,
with `δ = footprint/(2·(PDIST−PDSDIST))` (`:73-76`). It is converted to
`pix = round(PDSDIST·ψ/p)` columns and placed **symmetrically**,
`c0 ± pix/2` (`:77-79`).

**Inferred / computed from the code for NX scan 11** (reading A, G_L mapping
as above): footprint 63.3 mm; ψ = 3.17°, 3.74° and 4.05° at Det_Th 14,
16.6 and 18°. That is 87–111 columns centred on 47, i.e. ≈ columns 0–98. The
measured S5 shadow is 29–137 (asymmetric, S5L = 3 and S5R = 14 mm). The
symmetric centring therefore includes dark columns 0–28 and drops lit
columns 99–137. `PD_PIN`'s `AUTO_LIM` trimming weights by S5L/S5R
(`pd_pin.pro:278-296`), but with the default `AUTO_LIM = 1` it trims
nothing. The asymmetric projection
`c ∈ [c0 − S5L·k5/p, c0 + S5R·k5/p]` with `k5 = D_p/(D_p − 32)` predicts
27–139, matching the data.

---

## 2. Pixel → angle → Q (question 2)

### 2.1 What the code shows

- **`PD_GID_READ`** (`pd_gid_read.pro:224-263`; one column per frame):
  - `wdist = PDIST + G_L[3]·(1/cos β₀ − 1)`, β₀ = `Out_Rot`, α = `In_Rot`,
    both required constant (`:234-240`).
  - `z = p·(n − ns)/wdist`, with n the row (plus VROI offset) and
    ns = `PDxc`, the "specular channel".
  - `β_n = β₀ + atan(z)` (`:241-245`).
  - 2θ = the frame's Det_Th (`:238, 248`).
  - `Qxy = 2k·sqrt((sin((α+β)/2)·sin((α−β)/2))² + cos α cos β sin²(2θ/2))`;
    `/SIGNED` × sign(2θ) (`:256-260`).
  - `Qz = 2k·sin((α+β)/2)·cos((α−β)/2)` (`:261`).
  - Then `Img_trig` regrids onto a rectangular (Qxy, Qz) grid, restricted to
    the interior unless `/RELAXED` (`:265-275`).
- **`SCAN_PD_READ`** (per pixel): α = `In_Rot`, β = `Out_Rot`, 2θ = `Det_Th`
  (scan column if scanned) (`:199-202`). The same `dist` as above.
  `pdist` per §1.1; then `Img_coo_conv(..., dist, pdist, pix, cent, alp,
  bet, dth, tau=tilt, lam, /xrev, qvals, /sign)` (`:212-214`), followed by
  `Img_trig` regridding (`:215-224`). **The formula is in `IMG_COO_CONV`,
  which is missing.** `TILT` is a detector rotation in its own plane
  (`:57-59`).
- **`SCAN_PD_LCOO`** (1D coordinates): the same `dist` (`:95`); pinhole by
  default for Det_Th > 1° (`:100-101`); formula in `LIMG_COO_CONV`
  (missing).

### 2.2 Comparison with the reader

| Quantity | IDL | Reader | Difference |
|---|---|---|---|
| β of the reference row | `Out_Rot` | `arcsin(2 sin α − sin α_t)`, α from SPEC `L` (`TwoDDetector.py:202`) | measured: 0.09060° vs 0.0906° (scan 11), 6.50000° vs 6.5 (scan 12); identical, since SPEC computes `L` from the motors |
| β of row r | `β₀ + atan(p(r − ns)/wdist)` | `atan(p(r − ycen)/S2D) + β_c` (`TwoDDetector.py:202`; Pix V cut via `cuts.py:64-69`) | wdist = 551.0007 (scan 11) and 554.60 mm (scan 12). Measured: scan 11 identical to < 10⁻⁴°; **scan 12: 0.049° at row 486 (Qz 0.0042 Å⁻¹), 0.023° at row 250, −0.004° at row 15** |
| Qxy | the half-angle form above | `k·sqrt(cos²α + cos²β − 2 cos α cos β cos 2θ)` (`mainwindow.py:3542`) | algebraically identical; measured equal to 1×10⁻¹² at three points. IDL's form is better conditioned at small angles |
| Qz | `2k sin((α+β)/2) cos((α−β)/2)` | `k(sin α_t + sin β)` (`:3543`) | identical (difference ≤ 2×10⁻¹⁶) |
| α | `In_Rot` | `In_Rot` (`pilTrueAlpha`) | same |
| 2θ per GID profile | Det_Th of the frame | Det_Th of the frame (rounded 0.001°) | same |
| 2θ per column (pinhole) | `IMG_COO_CONV` with `pdist = PDSDIST` (inferred `Det_Th + atan(Δx·p/PDSDIST)`) | `dth + atan((c − xcen)·p/dist)`, dist = S7D with the box (`TwoDDetector.py:227-229`, `cuts.py:47-52`) | same form; the reader's box is off by default, IDL's switch is on for Det_Th > 1° |
| x centre | `addim[1] − pdyc` (vertical orientation, `scan_pd_read.pro:197`) | `NCOLS−1 − DBPos[1]` = 47 (`mainwindow.py:2475`); the GISAXS view uses `NCOLS − DBPos[1]` = 48 (`:2943`) | **measured:** the specular spot in scans 6–9 is at column 47.0–47.6 and row 52.7–53.1. 47 is right; the GISAXS view is one column off. IDL's value depends on `addim` (missing) |

### 2.3 Measured on NX school scan 11 (DPPC, Det_Th 14–18°, 41 frames)

| Measurement | Result |
|---|---|
| Lit columns (summed over frames, > 20 % of max) | 29–137; columns 138–142 hold 47–72 counts each, against ≈ 4 000–11 000 per column inside |
| Window predicted from S5 (3.0/14.0 mm), S5 32 mm before the detector, axis column 47 | 27–139 (centre +36 columns; measured +36) |
| Peak position against Det_Th, **after dividing each frame by the median frame** (cancels the column response); Gaussian + line fit, weighted linear fit | −27.09, −27.13, −27.22, −26.88 columns/degree (frames 14–33, 16–31, 18–29, 20–27; rms residual 0.13–0.22 columns) → **D = 267.0 ± 0.9, 267.4 ± 0.9, 268.3 ± 1.6, 264.9 ± 2.4 mm**; I take 267 ± 2 |
| Same, raw centroid without the response division (first version of this report) | 256–265 mm: biased low, because the response hump pulls the centroid toward its centre |
| 2θ of the peak at column 47 | 16.642–16.645° |
| Peak width | σ ≈ 1.7–2.4 columns (0.06–0.09°) in every frame from 14 to 33, i.e. no smearing across the window |
| Counts in columns 46–48 and in 29–137 (median per frame) | 776 and 18 434 (×24) |
| Peak excess at the predicted column | ≈ 1500 at columns 48–54; 1264 @64, 1045 @70, 773 @75, 560 @80, ≤ 190 @86–118; 1333 @43, 969 @38, 613 @32. The sample is seen ≈ 30–80 |
| Pixels with zero counts, rows 15–486 × columns 30–80, per frame | 58–72 %; mean 0.33–0.58 counts per pixel per frame |

**What the remaining 4 mm (1.5 %) against 271 could be** (inferred):

- **Not the G_L[3] term.** It acts on the vertical distance only, and at
  Out_Rot = 0.0906° it is 556·(1/cos − 1) = 0.0007 mm.
- **Not the centroid bias** after the response division; the four frame
  subsets agree within 1.6σ.
- **Candidates:**
  - the effective pinhole plane (the S4 blade edges) or the sensor plane
    (behind the detector window) being a few mm from the nominal positions;
  - a Det_Th encoder scale of 1.5 %, which is unlikely;
  - reading B (the true pinhole→detector distance is 267).
- **Recommendation:** treat D_p as a setting with a fit from the data
  (§7).

**The sample→detector distance cannot be checked with scan 11 alone.**
Rows only shift with β; the specular row stays at 53 in reflectivity. Scan
12 (Out_Rot 6.5°) stopped after 4 frames at Det_Th 14.0–14.3°, where the
Bragg peak lies outside the sample-seen columns. Ways to measure it are in
§8 Q1.

**Geometric model and the response** (inferred). A uniform 63 mm footprint
predicts a flat response over ±43 columns. The measured response is a hump
(half height ≈ columns 34 and 76), so the response must be measured from the
data (§7.3).

---

## 3. Patching and merging (question 3)

### 3.1 Summary table

| | Reader `imagehjoin` | Reader `imagevjoin` | IDL `PD_GID_READ` (v7.0) | IDL `IMG_JOIN` (v7.0; used by `PD_PIN`, `PD_GIPI_MERGE`) | IDL `PD_GIPI_MERGE` |
|---|---|---|---|---|---|
| Joined | scans of one Qz level (β-profiles at Det_Th) | Qz levels | scans of one β (≤ 8; α, β constant) side by side | ≤ 8 images, horizontally (default) or vertically | pinhole map into GID map |
| Order | `sortedScans` by Det_Th | low, middle, high | `Scan_order` of the 1D profiles (`:184`) | `Scan_order` of the 1D profiles (`:160, :251`) | — |
| Profiles used for the factor | β-integrated, all rows | 2θ-integrated, data2 resampled | integrated over `PATCH_RANGE` rows (`:141-181`) | integrated over the **common transverse range** (`:106-124, :206-215`) | z-integrated |
| Factor | weighted LSQ constant | same, cubic interpolation | `Scan_join(..., /relaxed, fac=mfac, over=ovl)` (`:193-194`), missing | `Scan_join(lo, hi, fac, efac, over)` (`:170, :261`), missing | quadratic in x, unweighted (`pd_gipi_merge.pro:80-84`) |
| Factor error | propagated, `sqrt((σf)²+(I σ_f)²)` | same | **not propagated**: `mfac` multiplies both data and error pages (`:205-208`) | propagated: `σ' = sqrt((efac·I)² + (f·σ)²)` (`:174-176, :265-267`) | not propagated |
| Overlap points | plain average, σ = √(σ₁²+σ₂²)/2 | plain average | **overwritten**: the later scan's frames replace the earlier's last `ovl` frames (`:196-209`; inferred from the index arithmetic) | **inverse-variance weighted**, `w = 1/σ²` (or 1/|I| without errors), σ = 1/√Σw; the second image is interpolated onto the first's grid by Delaunay triangulation (`trigrid`, linear) (`:177-195, :268-286`) | GID outside, pinhole inside, `ovr` transition columns (`/TRAN`, not in v7.0) |
| Different extents (F62) | needs the same β grid | data2 extended by its edge values | single β only | **intersection**: every image is cut to the common transverse range (`:111-119, :209-210`); "the largest rectangle overlapped by all inputs" (`:47-48`). Images with fewer transverse points are regridded onto `Make_grid(glims, umax)` (`:130-158, :221-249`) | pinhole cut to the GID range |
| Final grid | data1's, mixed | data1's 2θ, mixed β | `Img_trig` to a rectangle in (Qxy, Qz) (`:265-275`) | `Img_trig` to a regular grid along the join (`:200, :291`) | `Img_reform` |

### 3.2 Keywords

From the first batch (code says, inferred meaning in brackets):

- `sin_norm`: × sin(2θ)/sin(min 2θ) per column, default on in `PD_GID`,
  disabled in `PD_PIN` (`pd_gid.pro:76-82`, `pd_pin.pro:66-67`) [the
  1/sin 2θ field of view].
- `signed`: Qxy × sign(2θ).
- `skew`: × (1 + s·u), u ∈ [−1, 1] across the columns (`pd_pin.pro:302-329`)
  [a linear flat field].
- `clean`/`location`/`bsmooth`: background from the edge columns, smoothed
  in z, subtracted (`pd_gid.pro:91-102`).
- `smooth`: binomial smoothing, with an error multiplier `SM_ermult` for
  the integrated profiles (`pd_gid.pro:313-316`).
- `zbin`/`offset`: z-binned curves, default 64 channels.
- `limits`/`auto_lim`: draw or use the `PD_PIN_RANGE` coverage, trimmed by
  a fraction weighted by S5L/S5R (`pd_pin.pro:88-100, 278-296`).
- `slit`/`yoff`: an electronic slit in pixels, and its shift along the
  footprint (`pd_gid.pro:51-58`).
- `xy_region`/`z_region`: display or output cut.
- `overlap`: transition columns in `PD_GIPI_MERGE` (default 3).
- `indiv_fr`: per-frame coordinates.

Confirmed or added by the second batch:

| Keyword | Now known |
|---|---|
| `patch_range` | rows (after the VROI offset) over which the profiles for the horizontal-join factor are summed (`pd_gid_read.pro:141-176`); `/VERBOSE` prints the matching Qz range (`:277-284`) |
| `relaxed` | passed to `Img_trig` as `min = 1 − relaxed`, i.e. the regridded map is limited to the interior of the data unless relaxed (`scan_pd_read.pro:211, 216`; `pd_gid_read.pro:266-267`). `PD_GID_READ` also always passes `/relaxed` to `Scan_join` (`:193`) |
| `norm` | `nfac = Σ_frames M / (n_frames · M_f)`: counts scaled to the **scan-average monitor**, errors √N·nfac (`scan_pd_read.pro:151-159, 192-193`). This is the same as the reader's "÷ Monc × average Monc" (low and middle Qz) |
| `bad` | `Deglitch(dat, 3)` (`scan_pd_read.pro:171`) |
| `tilt` | detector rotation in its plane, degrees (`scan_pd_read.pro:57-59`) |
| `nointer` | skip the regridding: per-pixel coordinates are kept (`scan_pd_read.pro:71-74, 224`) |
| `boundary` | higher-order boundary in `trigrid` (`img_join.pro:33-37`) |
| `no_ferr` | "fitting errors are ignored in the matching" (`img_join.pro:38-39`), via `_extra` to `SCAN_JOIN` |
| `force` | `SCAN_JOIN` joins even without overlap (`img_join.pro:43-45, 60-61`) |

### 3.3 How IDL combines overlaps (`IMG_JOIN`, code says)

For each image after the first, in `Scan_order`:

1. Cut it to the common transverse range `glims` (`:106-119`).
2. Integrate it across the transverse direction into a 1D profile with
   errors (`:120-124`).
3. Join the accumulated 1D profile `lo` and the new one `hi` with
   `Scan_join`. This returns the factor `ffac[1]`, its error `efac[1]`, and
   `ovlo`, the overlap count on the `lo` side (`:170`).
   `ovhi = nlo + nhi − ntot` new-image points lie in the overlap (`:173`).
4. Scale the new image and its errors, `σ' = sqrt((efac·I)² + (f·σ)²)`
   (`:174-176`).
5. In the last `ovlo` rows (or columns) of the accumulated image, replace
   the values with `(w₁I₁ + w₂I₂)/(w₁ + w₂)` and the errors with
   `σ = 1/sqrt(w₁ + w₂)`. Here `w = 1/max(σ², ε)`, and the new image's
   values and errors are interpolated linearly by triangulation onto the
   old grid (`:177-195`).
6. Append the new image's rows beyond the overlap, then regrid the whole
   image onto a regular grid with `Img_trig` (`:196-203`).

**Issues, from reading (not run):**

- **Probable bug, `img_join.pro:201` and `:292`.** The error page is rebuilt
  as `Img_trig(reform(res[2,*,*]), /last)`, i.e. from the *data* page. In
  `scan_pd_read.pro:216-217` the same pattern uses `res[3]` for errors.
  After any join that extends the image, its errors would be data values.
- **Low-count bias of the weights.** The weights come from the data's own
  Poisson errors, so a downward fluctuation gets more weight, and a zero
  (σ = 0) gets weight 1/ε, which makes the overlap 0.
  - Measured: GID pixels in scan 11 average 0.3–0.6 counts, and 58–72 % are
    zero.
  - Simulated: two Poisson samples combined this way, with no interpolation,
    give 0.31× the true mean at μ = 0.4, 0.76× at μ = 2, 0.95× at μ = 10,
    and 0.995× at μ = 100. The plain average is unbiased.
  - `Img_trig` interpolation smooths this somewhat. It matters for `PD_PIN`
    pixel images, not for `PD_GID` profiles summed over many pixels.
- Linear interpolation of σ is not variance-correct (minor).
- `PD_GID_READ` scales errors by the factor but leaves out the factor's
  error, and keeps one scan's frames in each overlap, discarding the
  other's counts (inferred from the `lo`/`hi` index arithmetic).

**Still unknown without `SCAN_JOIN`:**

- how the overlap of two 1D profiles is found (`ovlo`, `ovhi`, and the
  handling of points that do not coincide);
- how the factor and `efac` are computed (ratio of sums? weighted fit?
  χ²-scaled?);
- what `/RELAXED`, `/FORCE` and `NO_FERR` do;
- `Scan_order`'s criterion.

`PD_GIPI_MERGE`'s `/TRAN` is not a keyword of `IMG_JOIN` v7.0. It goes to
`SCAN_JOIN` through `_extra`, or it belongs to a newer `IMG_JOIN`.

---

## 4. Corrections (question 4)

| Correction | IDL (code says) | Reader | Comment |
|---|---|---|---|
| Monitor | counts × (scan-average monitor / frame monitor) (`scan_pd_read.pro:151-159, 193`) | ÷ Monc × average Monc for low and middle Qz; high Qz not × (P31) | the same scale; IDL has no high-Qz exception |
| Footprint / field of view | `SIN_NORM` (in `PD_GID`, v8.44; not in `PD_GID_READ` v7.0); observable range `PD_PIN_RANGE` | `calArea` | measured equal to 1/sin 2θ to 2×10⁻⁵ for scan 11 |
| Vertical distance | `PDIST + G_L[3](1/cos(Out_Rot) − 1)` | S2D only | scan 12: Δβ ≤ 0.049°, ΔQz ≤ 0.0042 Å⁻¹ (measured, §2.2) |
| Polarisation | not in any file supplied | ÷ (1 − (sin 2θ cos β)²) | correct for a horizontally polarised beam *(standard; Als-Nielsen & McMorrow, from memory)* |
| Absorber | not visible | not applied | — |
| Lorentz / solid angle / obliquity | none | none | cos³ ≥ 0.97 at ≤ 8° *(inferred)* |
| Bad pixels | `Deglitch(dat,3)` | bad-pixel replacement (P16) | — |
| Detector tilt | `TILT` | none | — |
| Flat field across columns | `SKEW`, `AUTO_LIM`, quadratic merge ratio | none | needed for pinhole data |
| Background, smoothing errors | `CLEAN`, `SM_ermult` | none | — |

---

## 5. Gems, ranked (question 5)

| # | Gem | Source | Value |
|---|---|---|---|
| G1 | Per-column angles in pinhole geometry, **on by default for Det_Th > 1°** | `scan_pd_lcoo.pro:100-101`; `pd_pin.pro:299` | NX: from 4 % of the counts to ≈ 50 sample-seeing columns, per-column resolution ≈ (w_p + p)/D_p ≈ 0.08°. Measured peak width σ ≈ 2 columns in every frame |
| G2 | Two distances: pinhole→detector (horizontal) and sample→detector + G_L[3] term (vertical) | §1.1, §2.1 | fixes the 2× horizontal scale error with the box off, the β doubling in the Pix V cut (§5.1), and 0.004 Å⁻¹ at high Qz levels |
| G3 | Observable range from footprint and S5 (`PD_PIN_RANGE`), with S5L/S5R-weighted trimming | `pd_pin_range.pro:66-79`; `pd_pin.pro:278-296` | the geometry is good; use asymmetric S5 placement (§1.2) |
| G4 | Factor error propagated into the joined image | `img_join.pro:174-176` | the reader already does this in its joins; keep it |
| G5 | Common transverse range and regridding onto a common grid before joining | `img_join.pro:106-158` | the defined, documented answer to F62 (intersection); the union is an option |
| G6 | `PATCH_RANGE` rows for the join factor | `pd_gid_read.pro:141-176` | keeps edge rows out of the factor |
| G7 | Smooth (quadratic) scale for merging | `pd_gipi_merge.pro:79-84` | for joins where a constant leaves χ²/dof ≫ 1 |
| G8 | `SKEW`, `CLEAN`, `SM_ermult`, `ZBIN`, any number of β levels | first version | as before |

### 5.1 Reader bugs and questionable steps

| Where | What | Evidence |
|---|---|---|
| `lss_core/cuts.py:64-69` (`frame_cut`, "Pix V") | **New.** `plotHint` is given `s2d_dist=g.distance`, which is S7D with the pinhole box, so the **β axis uses the pinhole distance**. The other directions use `g.spec_distance` for β. | Measured with a synthetic frame (`Geometry(distance=271, spec_distance=551)`, axes "Angles"): β at row 486 = 15.457°; with S2D it should be 7.788° |
| GISAXS view, `mainwindow.py:2943` | x centre `NCOLS − DBPos[1]` = 48; the patch and display use 47 | measured: the specular spot is at column 47.0–47.6 |
| Pinhole box default off | horizontal scale 2× wrong for NX GID frames in cuts and display | measured |
| No G_L[3] term | β scale 0.65 % short at Out_Rot 6.5° | computed (§2.2) |
| From the first version | P13, P14/P15/P31 (known); the vertical join extends data2 with its edge values; display extents use the linear (not atan) form; `**` for `*` (cosmetic); fill 1e-10 instead of NaN in the relaxed map; χ²-scaled factor errors | read |

IDL issues (from reading only): the error page in `IMG_JOIN` (§3.3); the
inverse-variance bias at low counts; `PD_GID_READ` drops the factor error
and overwrites overlaps; `PD_PIN_RANGE`'s symmetric centring; `PD_PIN`
applies `SKEW` twice in one case (first version).

---

## 6. Missing routines (question 6), by priority

| Priority | Routine | Needed for |
|---|---|---|
| **1** | `IMG_COO_CONV` and `LIMG_COO_CONV` | the per-pixel pinhole formula, the role of `/xrev`, `/sign`, `tau`, and how `dist` and `pdist` enter (the reader's per-column formula is otherwise inferred) |
| **1** | `SCAN_JOIN` | overlap finding, factor, `efac`, `/relaxed`, `/force`, `no_ferr`, `/tran`(?); the heart of every join |
| **2** | `SPEC_FILE_INFO` (FILDAT fields) | which header items become `PDIST`, `PDSDIST`, `PDXC`/`PDYC`, `G_L`, `sl_val` (layout), `angs`, `addim`, `pdfar`, `varan` |
| **2** | `IMG_TRIG` | regridding by triangulation, the `min` (interior) rule, error regridding |
| 3 | current versions of `PD_GID_READ`, `SCAN_PD_READ`, `IMG_JOIN` (the callers pass `SLIT`, `YOFF`, `SIN_NORM`, `/INDIV`, `/TRAN`, absent from the v7.0 files) | whatever changed after 2008 |
| 3 | `SCAN_ORDER`, `SCAN_PD_COMB`, `SCAN_PD_CENTER` | ordering, the per-frame horizontal integration in GID, the centre |
| 4 | `PD_GID_CLEAN`, `SM_ERMULT`, `PD_GID_ZBIN`, `LINFIT_MM`, `IMG_SCALE`, `IMG_REFORM` | secondary |

IDL output for NX scans 11 + 12 would still be the most useful reference.

---

## 7. Specification: pinhole correction before patching, and joins (revised)

### 7.1 Names and inputs (per frame i)

| Symbol | Reader name / SPEC | NX scan 11 |
|---|---|---|
| N_i[r,c] | raw counts (keep them; do not start from `pilData`) | — |
| M_i | `pilMonc[i]` | ≈ 2.2×10⁶ |
| Det_Th_i | `pil_Dth[i]` | 14–18° |
| c0, r0 | `NCOLS−1 − DBPos[1]`, `DBPos[0]` | 47, 53 (measured 47.0–47.6, 52.7–53.1) |
| D_s | sample→detector; default `#B1` 3rd number (`S2D_Dist`); worksheet setting | 551 (or ≈ 538 under reading B) |
| D_p | pinhole(S4)→detector; default `#B1` 4th number (`S7D_Dist`) under reading A, or D_s − 4th number under reading B; worksheet setting, **fittable** (7.3) | 271; measured 267 ± 2 |
| G_L3 | `g_l3` (`#G0` 8th value) | 556 |
| β₀ | `arcsin(2 sin α − sin α_t)` (= Out_Rot) | 0.0906° |
| w_p | `S4L + S4R` | 0.2 |
| S5L, S5R | header `S5L`, `S5R` (store separately) | 3.0, 14.0 |
| d5 | S5→detector, `hard_slit_offset_mm` | 32 |
| S1h, S1v | `S1L + S1R`; **`S1T + S1B`** (P13 fix) | 2.0, 0.1 |
| p | 0.172 mm | — |

**Mode.** Pinhole is on by default when Det_Th > 1° (IDL rule) and the
frame comes from a Det_Th scan. The worksheet can override this; an extra
check `w_p < 1 mm` is optional (§8 Q3). The display and cut axes follow the
same switch. **With the mode off, the GID patch is unchanged** (legacy
fixtures byte-identical, rule 3).

### 7.2 Order of operations

1. Read N_i, M_i and the geometry; bad pixels as now.
2. Column angles: `2θ_ic = Det_Th_i + atan((c − c0)·p / D_p)`.
3. Row angles: `β_r = β₀ + atan((r − r0)·p / D_v)`, with
   `D_v = D_s + G_L3·(1/cos β₀ − 1)` (IDL). Optional (3b): column c sees
   the footprint at `x0 ≈ −L1 sin δ / sin 2θ_c` (L1 = D_s − D_p,
   δ = 2θ_c − Det_Th), so use `D_v,c = D_v − x0·cos 2θ_c` per column. On NX
   this is ±3.6 % at the edges of the sample-seen columns, up to 0.28° in β
   (0.025 Å⁻¹) at the top row. Whether Mati did this, `IMG_COO_CONV` will
   tell.
4. Column window: the asymmetric S5 projection
   `[c0 − S5L·k5/p, c0 + S5R·k5/p]`, `k5 = D_p/(D_p − d5)`, intersected
   with the footprint visibility
   `|atan((c − c0)p/D_p)| ≤ ψ_foot/2` (`PD_PIN_RANGE`'s ψ, which IDL
   applies symmetrically about c0). Optionally trim by a fraction, as `AUTO_LIM`
   does, weighted by S5L/S5R. The user can set a range.
5. Normalisation per pixel: `W_icr = M_i · A(2θ_ic, δ_ic) · P(2θ_ic, β_r) · R(c)`.
   - A is the footprint fraction (7.3).
   - `P = 1 − (sin 2θ_ic cos β_r)²`.
   - R is the column response (7.3).
6. **Bin within one Qz level** onto one common 2θ grid (step `p/D_p`):
   `I = ΣN / ΣW`, `σ = √ΣN / ΣW`, with split pixels and NaN where ΣW = 0.
   This avoids IDL's inverse-variance bias at < 1 count per pixel (§3.3),
   and it is the maximum-likelihood combination for frames sharing one
   normalisation *(inferred)*. Multiply by the scan-average monitor if
   count-like units are wanted (IDL `/NORM`).
7. **Between scans of one level** (different slits or gain): one factor per
   scan, fitted on the 1D profiles summed over `PATCH_RANGE` rows (IDL), on
   the common 2θ bins. Weighted LSQ as `imagehjoin` until `SCAN_JOIN` is
   known. Propagate the factor error as `σ' = sqrt((σ_f·I)² + (f·σ)²)`
   (IDL `IMG_JOIN` and the reader agree). Then combine with step 6's
   estimator, the factor applied to W.
8. **Between Qz levels** (vertical): as `IMG_JOIN`.
   - Cut both levels to the **common 2θ range** (IDL's intersection, the
     default). The union is an option for F62, with NaN where only one level
     has data.
   - Integrate over that range to β profiles and fit one factor on the β
     overlap, with its error propagated.
   - Combine the overlap by step 6's estimator (counts and normalisations),
     not by data-variance weights.
   - Rebin β onto one grid with split pixels.
9. Area and polarisation are already in W, so `gidCorrect` is skipped for
   pinhole maps.
10. Q map: `Qxy = 2k·sqrt((sin((α+β)/2) sin((α−β)/2))² + cos α cos β sin²(2θ/2))`
    (IDL form), `Qz = k(sin α + sin β)`, α = In_Rot. Interior or relaxed
    rectangle as now. Empty bins are NaN, not 1e-10.

### 7.3 A(c), R(c) and the fit of D_p

- **A, the footprint fraction:** as in the first version. The band axis
  runs through the pinhole centre at L1 = D_s − D_p from the sample, with
  direction 2θ_ic and offset `e = −L1 sin δ`. The edges are given by the
  pinhole (w_p) and the column (p). The fraction is computed by clipping the
  footprint rectangle (`s1x = S1v/sin α_t`, `s1y = S1h`; optionally the S1
  gap broadened by `G_L[2]−G_L[1]` diffraction as `PD_PIN_RANGE` does). At
  `e = 0` it equals `calArea`.
- **R, the column response:** estimated from the data by alternating
  between S(2θ, β) (step 6) and `R(c) = Σ N / Σ M·A·P·S`, with smoothness
  in c and normalised at c0. A first estimate can come from dividing each
  frame by the median frame, as in §2.3. `SKEW` is the linear special case.
- **D_p fit:** pick a feature with a fixed 2θ (a Bragg peak) seen in at
  least 6 frames inside the window. Divide each frame by the median frame,
  fit the peak column per frame, and fit column against Det_Th linearly:
  `D_p = |slope|·p·180/π`. Report it with its error and the per-subset
  spread. On NX scan 11 this gives 267 ± 2 mm. A full self-calibration fit
  (R, S and D_p together, χ² against D_p) was tried and is **not reliable**:
  χ²/dof ≈ 10–15, and the minimum moved with the 2θ bin size, from aliasing
  between the 0.1° Det_Th step and the 0.036° column (App. A).

### 7.4 Where the code goes

Unchanged: pure functions in `lss_core/gid.py` (angles, window, footprint
fraction, response, binning, joins with a log). New `GIDParams`:

- `pinhole` ('auto' | on | off);
- `pinhole_distance_mm`, `detector_distance_mm`, `distance_reading` (A/B);
- `gl3_correction`;
- `window_fraction`, `column_range`;
- `response` ('none' | 'skew' | 'fit');
- `bin_step_deg`;
- `transverse` ('intersection' | 'union');
- `patch_rows`.

### 7.5 What to test

| Test | Kind | Check |
|---|---|---|
| T1 | invariant | Mode off: legacy fixtures and `nx_school_gid_scan_11_*` unchanged |
| T2 | characterisation | Mode on, columns c0 ± 1, R = 1, no G_L3 term: the β-integrated 2θ profile, rebinned to the Det_Th grid, agrees with today's patch within errors; `A(e=0) == calArea` (≤ 1e-12) |
| T3 | invariant | Footprint fraction: `A(e=0) = calArea`; long footprint `A·sin 2θ` constant; zero when the band misses the footprint |
| T4 | synthetic | A sharp ring at 2θ_f through a pinhole (D_p ≠ D_s) over a Det_Th scan: the peak at 2θ_f ± ½ column in every frame; binned FWHM independent of the number of columns |
| T5 | invariant | Counts conserved: `Σ I·ΣW = Σ N` |
| T6 | synthetic | **Low counts (μ = 0.4 per pixel per frame, as NX):** the joined overlap is unbiased (mean/truth = 1 ± 0.01) and the pulls have width 1 ± 0.05. Data-variance weighting fails this (0.31×), which documents why it is not used |
| T7 | synthetic | A known R(c) (the NX hump) recovered to < 1 % |
| T8 | real (slow) | NX scan 11: the D_p fit gives 267 ± 3 mm; the peak 2θ at column 47 is 16.643 ± 0.01°; the 3-column legacy map's peak agrees |
| T9 | real (slow) | NX scan 11: predicted S5 window 27–139 against lit 29–137 (± 3 columns) |
| T10 | synthetic (F62) | Two levels with different 2θ extents: with 'intersection' the map covers the common range only (IDL); with 'union' it covers the union and is NaN where neither applies; the factor uses only the common part and equals the truth within its error |
| T11 | as coded | Polarisation per column equals the legacy factor at c0 |
| T12 | real (slow) | NX scans 11 + 12 in pinhole mode: the factor between levels and its χ²/dof are logged; no step at the boundary > 2σ |
| T13 | invariant | Vertical distance: with the G_L3 term, β of scan 12 row 486 = 14.1484° (IDL formula), without it 14.1977° (as coded today) |
| T14 | regression for the new bug | `cuts.frame_cut` "Pix V", axes "Angles", pinhole on: β from `spec_distance` (7.788° at row 486 in the synthetic case), not 15.457°. Today this would be an `xfail(strict=True)` |
| T15 | invariant | The Qxy half-angle form equals the reader's form to 1e-12 |

---

## 8. Questions for the owner (open)

Answered and dropped: S4 is the pinhole slit; `S7D_Dist` is not firm (the
measurement and §1.1 now say what it most likely is).

1. **Distances.** Which of A or B (§1.1) is right? That is, is 551 the
   sample→detector distance, and the 271 the S4→detector distance (IDL's
   `PDSDIST`) or the sample→S4 distance? Where is "the detector-to-sample
   distance known elsewhere" kept? The data fix S4→detector at 267 ± 2 mm.
   A Det_Th scan with a Bragg rod crossing the overlap of two Qz levels, or
   a direct-beam scan in Out_Ht, would fix the sample→detector distance.
2. Please send **`IMG_COO_CONV`/`LIMG_COO_CONV` and `SCAN_JOIN`** first, then
   `SPEC_FILE_INFO` and `IMG_TRIG`. The newest versions of `PD_GID_READ`,
   `SCAN_PD_READ` and `IMG_JOIN` are wanted too: the ones sent are v7.0
   (2008), older than their callers. IDL output for NX scans 11 + 12 if
   possible.
3. Is "pinhole on for Det_Th > 1°" (IDL's rule) right for all 15-ID-C GID
   data, or should the S4 gap also be checked?
4. Should vertical joins keep IDL's **intersection** of 2θ ranges, or the
   union (F62)?
5. Overlap arithmetic: is count-weighted binning acceptable instead of
   IDL's inverse-variance weights (biased at the < 1 count per pixel of NX
   pinhole data)?
6. Column response: data-driven, or geometric plus `SKEW`/`AUTO_LIM`?
7. Did Mati correct β per column for the scattering point's distance?
8. Is GID always at one absorber setting?
9. `PD_MERGE`'s "pinhole data": separate static exposures, or pinhole
   Det_Th scans? Is the merge still used?

---

## Appendix A. Measurements

All runs were read-only (Python 3, `lss_core.images.read_pilatus`); the
scripts were kept in the session scratchpad, not in the repository.

- **Header** (`20260923`, scan 11):
  - `#B1 53 147 551.000000 271.000000`;
  - `#G0 0 1 1 1 90 560 1238 556 1.92359 …`;
  - In_Rot 0.0905, Out_Rot 0.0906, S1T = S1B = 0.0500, S1L = S1R = 1.000;
  - S4L = S4R = 0.1, S4T 51, S4B 7.3;
  - S5L 2.99986, S5R 13.9999.

  Scan 12: Out_Rot 6.5, In_Rot 0.0903, `L` = 0.5817, otherwise the same.
- **Specular spot** (scans 6–9, Det_Th = 0, S4 = 5 + 5 mm). The centroid of
  a 13×13 box around the maximum is at row 52.7–53.1 and column 47.0–47.6
  in all sampled frames.
- **Lit window and counts:** as in §2.3. Columns 136–142 total 4592, 2814,
  72, 64, 72, 62, 47 counts over 41 frames.
- **Distance, response-corrected:**
  - each frame is divided by its monitor (normalised to the scan mean),
    then by the median frame of the scan (per column);
  - a Gaussian + linear fit within ±14 columns of the maximum gives the peak
    column;
  - a weighted linear fit of column against Det_Th gives the slope;
  - D = |slope|·0.172·180/π. Results in §2.3.
- **Distance, self-calibration attempt.** The model `N = M·(R(c)·S(2θ) + B(c))`
  was fitted by alternating least squares for D = 240–310 mm.
  χ²/dof = 10–15. The minimum was at 286–291 mm with 0.05° bins and at
  311–321 mm with 0.08° bins. This dependence on the bin size shows
  aliasing, so the result was not used.
- **`calArea` against `SIN_NORM`:** unchanged from the first version
  (0.0148547–0.0148546 for `calArea·sin 2θ`, 14–18°).
- **β, Qz, Qxy against `PD_GID_READ`.** Formulas evaluated with the scan 11
  and 12 header values, G_L3 = 556 and PDIST = 551. The values are in §2.2.
- **Pix V cut, synthetic:** `cuts.frame_cut(det, ones, ones, 'Pix V', 40,
  60, Geometry(λ=1.23984, α=α_t=0.0905°, Det_Th=16°, distance=271,
  spec_distance=551, xcenter=47, ycenter=53), axes='Angles')`. Last x =
  15.4571°, equal to `atan(433·0.172/271) + α_t`, against 7.7882° with 551.
- **Low-count bias, simulated:** 2×10⁵ pairs of Poisson(μ) samples combined
  with `w = 1/max(N, 1e-30)` as in `img_join.pro:178-195`, without
  interpolation. Mean/μ = 0.311, 0.755, 0.951, 0.995 for μ = 0.4, 2, 10, 100.
  The plain mean gives 1.000.
- **Zero pixels:** scan 11, rows 15–486, columns 30–80, every 5th frame.
  58–72 % zeros; mean 0.33–0.58 counts per pixel.
