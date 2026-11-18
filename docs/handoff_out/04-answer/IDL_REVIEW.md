# Hand-off 04, answer: what the IDL pinhole/GID code knows that the reader does not

Written 2026-11-18 by a reviewing agent, for the brief
`docs/handoff_out/04-idl-pinhole-review.md`. Read-only review: no file
other than this one was written.

**How to read this report.** Three kinds of statement are kept apart:

- **Code says** — quoted from a file, with `file:line`. IDL files are in
  `docs/reference_code/idl/`. `mainwindow.py` line numbers are as read on
  2026-11-18 (HEAD `ada40cc` plus another agent's uncommitted edits); they
  move, so search by function name.
- **Inferred** — my reading of what the code or the geometry implies. No
  IDL interpreter was available; nothing in IDL was run.
- **Measured** — computed here from the committed NX school data
  (`sample_data/NX_school/2026sep`, scan 11, Pilatus 100K frames, read with
  `lss_core.images.read_pilatus`, i.e. in the reader's array orientation,
  487 rows × 195 columns). Nothing was written into `sample_data/`. The
  commands are summarised in Appendix A.

Citations marked *(from memory)* were not checked against the source here.

---

## 0. Top findings

1. **"Pinhole" is a measurement geometry, not a correction recipe.** A narrow
   detector-arm slit acts as a pinhole camera aperture, so each detector
   *column* sees one in-plane direction, at the pinhole–detector distance
   instead of the sample–detector distance. `PD_PIN` reads such data with
   one angle per pixel column; `PD_GID` keeps one column per *frame* (as
   the reader does); `PD_MERGE` grafts pinhole maps into GID maps
   (§1).
2. **Measured: the NX school GID scans are pinhole data.** Scan 11 has
   S4 = 0.1 + 0.1 mm. A Bragg peak (the DPPC peak) drifts across the frames by
   26.0–26.9 columns per degree of Det_Th. That corresponds to a column-to-angle distance of
   **256–265 mm**: close to `S7D_Dist` = 271 mm, and far from
   `S2D_Dist` = 551 mm, which would give 55 columns/degree. The
   lit window, columns 29–137, matches S5L/S5R (3/14 mm) projected from
   the pinhole to within 2 columns (§2.3, App. A).
3. **The reader uses about 4 % of the counts of these frames.** It sums 3 columns
   (46–48) per frame. The lit window holds 24× as many counts. The sample
   itself is seen over roughly columns 30–80, with a non-flat response
   (a hump peaking at columns 48–54). Columns 85–137 are lit mostly by
   background (§2.3). So the per-column correction is needed, and so is a
   per-column response normalisation (the IDL code has empirical
   tools for this: `AUTO_LIM`, `SKEW`, the quadratic ratio in
   `PD_GIPI_MERGE`).
4. **The IDL files given do not contain the pixel→angle formulas or the
   overlap arithmetic.** These are in `SCAN_PD_READ`/`SCAN_PD_LCOO` and
   `IMG_JOIN`, which were not supplied. The one overlap algorithm that is visible
   (`PD_GIPI_MERGE`) scales the inserted data by a **quadratic function of
   Qxy**, fitted to the ratio of the Qz-integrated profiles. It keeps the reference data
   unscaled, and splices with a few "transition" columns (§3.3).
5. **The reader's area correction equals IDL's `SIN_NORM` for this data.**
   Measured: `calArea(...)·sin 2θ` is constant to 2×10⁻⁵ over 14–18° for
   scan 11's slits (§4).
6. A specification for a per-column pinhole correction followed by
   count-weighted binning (no pairwise joins within a scan) is in §7, with
   tests. The five routines to ask the owner for are in §6.

---

## 1. What "pinhole" means here (question 1)

**Code says.**

- `pd_view.pro:55-59`: `/PINHOLE` "Specifies that horizontal pinhole
  angle transformations are to be used. If set, the distance PDSDIST from
  the structure FILDAT … is used in the transformation." It only acts on
  1D integrated displays in angle or Q coordinates (`pd_view.pro:64-65`).
  It is passed on as `pin=pnh` to `Scan_PD_lcoo` (`pd_view.pro:221-224`). The
  keyword dates from 5-NOV-2009 (`pd_view.pro:146`).
- `pd_pin.pro:15`: "Readout and display of PD pinhole type data". Every
  read goes through `Scan_PD_read(..., /pinhole, /norm, ...)`
  (`pd_pin.pro:298-301, 320-322`). Its raw horizontal unit is the **pixel**
  (`pd_pin.pro:365`: `xytit = [['pix','Dth','Q!dxy!n'],...]`).
- `pd_gid.pro:350`: in `PD_GID` the raw horizontal unit is the **frame**
  (`[['frame','Dth','Q!dxy!n'],['pix','Beta','Q!dz!n']]`), and `/RAW` is
  described as "frame #" horizontally (`pd_gid.pro:59-64`). `SLIT` is an
  "electronic slit (around the center pixel) in pixels" that defines HROI
  (`pd_gid.pro:51-54`). This is exactly the reader's one-profile-per-frame
  model.
- `pd_merge.pro:25-27`: "from internal point of view there is no difference
  between GID and Pinhole data". The two are separate data sets in the same
  `[4,M,N]` format (`pd_merge.pro:21-23`): x coordinate, z coordinate,
  value and (inferred) error.
- `pd_pin.pro:88-91`: `/LIMITS` draws "the limits of the observable region,
  as defined by the beam's footprint and the slits". `pd_pin.pro:278-281`
  reads slit 5's two horizontal values (`sl5 = …[5,2:3]`) to weight the
  `AUTO_LIM` trimming (§3.4).
- `pd_pin.pro:212-213`: "Internal changes enabling PIN-GID mode"
  (10-APR-2009). `pd_gid.pro:76-79`: `SIN_NORM` "corrects for the changing
  field of view in Pinhole scans".

**Inferred.**

- Pinhole data and GID data are two ways of measuring the same thing. In
  "GID" (`PD_GID`), each frame is reduced to one column at the frame's
  Det_Th, with the angular acceptance set by an electronic slit or a Soller
  collimator. In "pinhole" (`PD_PIN`), a narrow slit on the detector arm
  images the footprint like a pinhole camera. Every column then has its own
  in-plane angle, `Dth + atan(Δx·p / PDSDIST)`, and frames from a Det_Th scan are
  patched column by column ("PIN-GID mode"). `PD_MERGE`/`PD_GIPI_MERGE` put a
  pinhole map into a GID map.
- **The pinhole is the slit S4, and PDSDIST is the reader's `S7D_Dist`**
  (the 4th number on SPEC's `#B1` line, `spec_routines.py:150-157`). The
  evidence is the measurement in §2.3. The reader's own code agrees with
  it: `calArea` puts S4 at `S2D_Dist − S7D_Dist` from the sample
  (`mainwindow.py:3409`, "s2 slits to sample distance"). The checkbox
  swaps S2D for S7D on the horizontal axis only (`mainwindow.py:2497, 2511`;
  `lss_core/cuts.py:36`). The same "horizontal only" rule is in
  `pd_view.pro:56`. The reader's comment "distance between S4 & S5"
  (`mainwindow.py:2246`) is, I think, wrong: S7D is the S4-to-detector
  distance (to be confirmed, §8 Q2).
- **S5 defines the window of lit columns.** In NX scan 11, S5L = 3.0 mm
  and S5R = 14.0 mm (asymmetric). Projected from S4 onto the detector, they
  predict the lit columns measured, including the off-centre position (§2.3).
  `PD_PIN`'s `AUTO_LIM` weights its trimming by S5L and S5R, which fits
  this picture.
- **Vertically there is no pinhole.** S4T = 51 mm and S4B = 7.3 mm, so the
  vertical angle β still uses the sample–detector distance. This agrees with
  "horizontal pinhole angle transformations" (`pd_view.pro:56`).

---

## 2. Pixel → angle → Q (question 2)

### 2.1 What the IDL files contain

**Code says.** The five files contain **no** pixel→angle or angle→Q
formula. All coordinates come from called routines:
`Scan_PD_lcoo` (`pd_view.pro:221-224`), `Scan_PD_read` (`pd_pin.pro:299,
320`), `PD_GID_read` (`pd_gid.pro:296`), `PD_pin_range`
(`pd_pin.pro:294, 316, 342`). The only angle inputs that can be seen are per scan:
`angs = Scan_field_read(snum,'Angs')`, with `bet = angs[*,1]` and
`dth = angs[*,2]` (`pd_pin.pro:269-271`). These are rounded to 0.01° for grouping and
sorting (`pd_pin.pro:272-276`). `/INDIV_FR` makes coordinates "recalculated
for each frame" (`pd_view.pro:60-62`). `PD_PIN` always reads frames with
`/indiv` (`pd_pin.pro:299`). `/SIGNED` multiplies Qxy by the sign of DTH
(`pd_gid.pro:69-71`).

### 2.2 The reader's formulas (code says) and the standard ones

| Quantity | Reader (code says) | Standard / pinhole (inferred) |
|---|---|---|
| 2θ of a GID profile | `Det_Th` of the frame, rounded to `dth_decimals` (`mainwindow.py:2200, 3285`) | same for the column through the pinhole axis |
| 2θ of column c (cuts, display) | `dth + atan((c − xcen)·p / dist)`, `dist` = S2D, or S7D with the box (`TwoDDetector.py:227-229`, `cuts.py:47-52`); display extent uses the linear form without atan (`mainwindow.py:2500`) | **pinhole:** `2θ_c = Det_Th + atan((c − c0)·p / D_p)`, D_p = S7D_Dist; sign measured (§2.3) |
| β of row r | `atan((r − ycen)·p / S2D) + arcsin(2 sin α − sin α_t)` (`TwoDDetector.py:202`) | same; the offset term is the β of the reference row, from SPEC `L` (α = arcsin(Qz λ/4π), `mainwindow.py:2187`), α_t = `In_Rot` (`mainwindow.py:2188`) |
| Qxy | `k·sqrt(cos²α_t + cos²β − 2 cos α_t cos β cos 2θ)` (`mainwindow.py:3542`) | standard GID kinematics, e.g. Als-Nielsen *et al.*, Phys. Rep. 246, 251 (1994) *(from memory)* |
| Qz | `k(sin α_t + sin β)` (`mainwindow.py:3543`) | same |
| xcen, ycen | `NCOLS−1 − DBPos[1]` and `DBPos[0]` (`mainwindow.py:2189-2191, 2475-2476`). For NX: 194 − 147 = **47**, and 53 | measured: column 47 is the pinhole axis (§2.3) |
| p | 0.172 mm (`TwoDDetector.py:20`, `cuts.py:25`) | Pilatus pixel |

**Does each column get its own angle before patching?** In `PD_PIN`, yes
(inferred from `/indiv`, `/pinhole` and the "pix" raw unit). In the
reader's GID patch, no: the columns within the H slit are summed into one
profile at Det_Th (`TwoDDetector.plotHint`, `mainwindow.py:3256-3285`). The
reader's GISAXS view already maps every column with the pinhole distance
(`mainwindow.py:2966`), which sets a precedent.

### 2.3 Measured on NX school scan 11 (DPPC, Det_Th 14–18°, 41 frames)

| Measurement | Result | Meaning |
|---|---|---|
| Lit columns (column sum of rows 15–486 over all frames, > 20 % of max) | **29–137** (109 columns); columns 138–142 have 47–72 counts each, against ≈ 4 000–11 000 per column inside | the S5 shadow |
| Window predicted from S5 (L 3.0, R 14.0 mm), axis column 47, S5 32 mm before the detector (the reader's hard-slit offset), D_p = 271 mm | **27–139**; centre offset +36 columns, measured +36 (centre 83) | S5R lies on the high-column side; S5 is ≈ 25–32 mm before the detector |
| Bragg-peak centroid against Det_Th, frames 17–31 / 19–29 / 21–27 | −26.9 / −26.9 / −26.0 columns per degree, rms residual 0.1–0.3 columns | D_p = 265 / 265 / **256 mm**. Expected: 27.5 columns/degree for S7D = 271 mm, 55.9 for S2D = 551 mm |
| 2θ of the peak, from the column-47 crossing | 16.63° (all three fits) | consistent with `2θ_c = Det_Th + (c − 47)·p/D_p`; 2θ increases with column index, as in `plotVint` |
| Counts in the reader's columns 46–48 and in the lit window 29–137 (median per frame) | 776 and 18 434 (×24) | the reader uses ≈ 4 % of the counts |
| Peak excess above the frame-median profile, at the predicted column | ≈ 1500 at columns 48–54; 1264 @64, 1045 @70, 773 @75, 560 @80, ≤ 190 @86–118; 1333 @43, 969 @38, 613 @32 | the sample is seen over roughly columns 30–80; columns 85–137 show almost no sample signal |

Note on the distance: one column is p/D radians, so a fixed-angle feature
drifts by D·π/(180·p) columns per degree of Det_Th. The measured value fits
S7D to within 2–6 %. The small shortfall could be centroid bias from the
non-flat response, or a real distance of ≈ 260 mm. It should be a worksheet
setting that can be fitted (§7, gem G2).

**Inferred, geometric model, not confirmed.** Assume a uniform footprint
of 63 mm × 2 mm (S1 0.1 mm vertical at α_t = 0.0905°, S1 2 mm horizontal)
and a pinhole 280 mm from the sample. The column through a pinhole ray
sees the footprint over a chord `W/sin 2θ_c`. The ray crosses the beam axis
at `x0 ≈ −L1 sin δ / sin 2θ_c` (L1 = S2D − D_p, δ = 2θ_c − Det_Th), which
is ≈ 0.62 mm along the footprint per column. This model predicts a **flat**
response over ±43 columns. The measured hump (half height at about columns
34 and 76) is narrower and asymmetric. So the illuminated length is
nearer 25 mm FWHM, and off-centre. **The column response therefore has to be
measured from the data (§7.3 step 5), not only computed.**

---

## 3. Patching and merging (question 3)

### 3.1 Summary table

| | Reader, horizontal (`imagehjoin`) | Reader, vertical (`imagevjoin`) | IDL `PD_GID` | IDL `PD_PIN` | IDL `PD_GIPI_MERGE` |
|---|---|---|---|---|---|
| What is joined | scans of one Qz level, β-profiles at Det_Th | Qz levels | scans per β (horizontal), then β levels (vertical) (`pd_gid.pro:32-35`) | frames within a scan, scans at one β (`/hor`), β levels (`/ver`) (`pd_pin.pro:309-310, 330-338`) | a pinhole map inserted into a GID map |
| Grouping | Qz rounded to 3 decimals, ≤ 3 levels (`mainwindow.py:3242ff`) | — | by β (in `PD_GID_READ`, not supplied) | β and Det_Th rounded to 0.01°, sorted by β then Det_Th (`pd_pin.pro:272-276, 283-285`), any number of levels | — |
| Overlap found by | data2's x ≤ data1's last x (`mainwindow.py:3702ff`) | data1 β ≥ data2's first β; last overlap point dropped | `PD_GID_READ` / `IMG_JOIN` (not supplied) | `IMG_JOIN` (not supplied) | pinhole x within the GID range (`pd_gipi_merge.pro:69-76`); GID points in the pinhole range (`:79`) |
| Scale factor | one constant: weighted LSQ of the ratio of β-integrated profiles, data2 interpolated linearly (`:3729`) | one constant; cubic (default) 1D interpolation of integrated profiles (`:3810, 3822`) | not visible | not visible | **quadratic in x**: `Linfit_mm(gx, P/G, ord=2)`, pinhole divided by the polynomial column by column (`pd_gipi_merge.pro:80-84`); unweighted (no weights passed) |
| Which side is scaled | data2 | data2 | — | — | the pinhole data; GID is the reference |
| Points in the overlap | plain average on the finer grid, σ = √(σ₁²+σ₂²)/2 (`:3751`); the other image interpolated 2D-linearly | plain average on data1's grid | not visible | not visible | GID kept below and above the pinhole range, the pinhole data in the middle, `OVERLAP` (default 3) GID columns on each side joined with `IMG_JOIN, /tran` (`:86-97`) |
| Different extents (F62) | requires the same β grid | data2 interpolated onto data1's 2θ grid over the whole range; outside data2's range the **nearest-edge value** is used (`interp_compat.py` docstring) | `RELAXED` (below) | `RELAXED` | pinhole trimmed to the GID x range; z ranges not trimmed (z-integrals of each set's own range are compared) |

### 3.2 Keywords

| Keyword | Where | Code says | Inferred |
|---|---|---|---|
| `relaxed` | `pd_gid.pro:72-75`, `pd_pin.pro:62-65` | the angles→Q transform is constrained to the internal data region unless set, "to avoid edge inaccuracies" | the same as the reader's "GID Patch" / "GID Patch Relax" (`pilGIDRelax`, `mainwindow.py:3544`): the inner rectangle versus the full range with fill |
| `sin_norm` | `pd_gid.pro:76-82` (default **on**); `pd_pin.pro:66-67` ("Disabled on 5/11/09, as not needed") | multiply each column by sin(dth)/sin(min(dth)) | the 1/sin 2θ field of view; equal to the reader's `calArea` here (§4) |
| `signed` | `pd_gid.pro:69-71` | Qxy × sign(DTH) | for scans through 2θ = 0 |
| `skew` | `pd_view.pro:66-69, 185-188`; `pd_pin.pro:68-71, 302-308, 323-329` | `scal = (1 + skw·grid[-1,1]) # 1`; `Img_scale(img, scal)` | a linear intensity tilt across the columns (`Img_scale` multiplies values, as in `pd_gipi_merge.pro:83-84`); an empirical flat field |
| `clean`, `location`, `bsmooth` | `pd_gid.pro:91-102, 312` | 2D background subtraction of width CLEAN, from the extreme left/right columns or from LOCATION; background smoothed binomially in z | background(β) taken from columns without peaks, subtracted from every column |
| `smooth` | `pd_gid.pro:103-112, 313-316` | binomial smoothing; `erm = SM_ermult(ker)` passed as `ermult` to the integrations (`:385, :392`) | error bars of integrated smoothed data are corrected for the correlation the smoothing introduces |
| `patch_range` | `pd_gid.pro:83-86` | "range of channels to use in patching", in original channels before VROI | the rows (β) used to compute join factors, which keeps edge rows out of the fit |
| `zbin`, `offset` | `pd_gid.pro:159-164, 395-397` | `PD_GID_ZBIN` bin size, default 64 original channels, any value; OFFSET for its display | β-binned 1D curves (the reader's fixed four β bins, `gid_vc`, `mainwindow.py:3530`) |
| `limits` | `pd_pin.pro:88-91, 341-345` | the observable region (footprint + slits) drawn on a single-frame image | from `PD_PIN_RANGE` (not supplied) |
| `auto_lim` | `pd_pin.pro:92-100, 266-268, 278-281, 293-297` | default 1 (the whole observable region) unless `/LIMITS`; 0 = the whole frame; ignored if HROI is given. `del = (pran[1]−pran[0])·(1−waul)`, `hroi = pran + round(del·[S5L, −S5R]/(S5L+S5R))` | a fraction of the observable column range is kept, trimmed from each side in proportion to S5L and S5R |
| `slit`, `yoff` | `pd_gid.pro:51-58` | electronic slit in pixels around the centre pixel; YOFF = offset "along the beam footprint", shifting HROI | (non-pinhole GID) choosing which part of the footprint is seen; probably Δc ≈ yoff·sin 2θ/p |
| `xy_region`, `z_region` | `pd_gid.pro:113-131, 318-348` | display/output cut, applied after CLEAN and SMOOTH | — |
| `overlap` | `pd_gipi_merge.pro:57, 86-96` | GID columns kept on each side inside the pinhole range, default 3, capped at half the gap | the transition band for `IMG_JOIN, /tran` |
| `indiv_fr` | `pd_view.pro:60-62` | coordinates recomputed per frame | — |
| `verify`, `bad`, `norm` | `pd_gid.pro:44-46, 188-197` | missing or bad frames rejected; hot pixels removed; monitor normalisation (on by default) | — |

### 3.3 How the IDL code combines overlaps (the part that can be seen)

**Code says** (`pd_gipi_merge.pro:59-99`):

1. `gzi`, `pzi` = profiles of each map integrated over z (`PD_GID_int, /z_int`).
2. The pinhole map is trimmed to the GID x range (`:69-76`).
3. On the GID points inside the pinhole range: `rat = P(gx)/G(gx)`. P is
   interpolated onto the GID x (`Scan_inter`).
4. `coe = Linfit_mm(gx, rat, ord=2)`. Every pinhole column is divided by
   `poly(px)` (`:82-84`).
5. GID columns more than one pinhole step below or above the pinhole range are
   kept (`:86-90`), plus `ovr` more on each side (`:95-96`).
6. `res = Img_join(G_low, P_scaled, G_high, /tran)`; then the x values are
   re-assigned as `[gx[lo], px, gx[hi]]` and sorted (`:97-99`).

**Inferred.** Because `rx` has no entries for the `ovr` extra GID columns,
`/TRAN` must blend those columns into the pinhole ones rather than append
them. This would be a transition region with ramped weights; `IMG_JOIN` is
needed to confirm. The quadratic ratio removes any smooth Qxy-dependent
mismatch (field of view, a resolution difference, residual `SKEW`), not
only a constant. The reader's joins fit only a constant.

**For horizontal and vertical joins in `PD_GID`/`PD_PIN`, the arithmetic is
inside `IMG_JOIN` and `PD_GID_READ`**, which were not supplied. "Joins should
follow what the IDL code does" can therefore be met only for the GID +
pinhole merge until the owner sends them.

---

## 4. Corrections (question 4)

| Correction | IDL (code says) | Reader (code says) | Comment |
|---|---|---|---|
| Monitor | `/NORM` default in `PD_GID` (via `PD_GID_READ`, `pd_gid.pro:196-197`); forced in `PD_PIN` reads (`pd_pin.pro:300, 321`); off by default in `PD_VIEW` (`pd_view.pro:120-121`) | per frame ÷ Monc, then × the scan's average Monc for low and middle Qz only (P31; `mainwindow.py:3290-3300`) | same idea; the reader's high-Qz exception is a known defect (P14/P15/P31) |
| Footprint / field of view | `SIN_NORM`: × sin(dth)/sin(min dth) per column (default on in GID; off in PIN) | `calArea`: fraction of the S1 footprint seen through S4 and S5 (S5 capped at the electronic slit), ÷ per frame (`mainwindow.py:3402ff`, `gidCorrect`) | **measured equal:** for scan 11's slits, `calArea·sin 2θ` = 0.0148547 ± 1×10⁻⁷ at 14, 15, 16, 17, 18° (relative spread 2×10⁻⁵). They differ only when the band reaches the footprint ends. The reader feeds `S1v = S1T + S1T` (P13) |
| Polarisation | not in these files (maybe in `SCAN_PD_READ`) | ÷ (1 − (sin 2θ cos β)²) (`mainwindow.py:3393`) | correct for a horizontally polarised beam: ê‖ŷ, k̂_f = (cos β cos 2θ, cos β sin 2θ, sin β) *(standard; Als-Nielsen & McMorrow, Elements of Modern X-ray Physics, from memory)*. In pinhole mode use 2θ_c per column |
| Absorber | not visible | not applied (worksheet label) | ask whether GID is always at one setting (§8) |
| Lorentz / solid angle / detector obliquity | not visible | none | at ≤ 8° out of plane and 0.172 mm pixels at 551 mm the flat-detector obliquity factor cos³ is ≥ 0.97 *(inferred)*; neither program applies it |
| Bad pixels | `/BAD` (`pd_gid.pro:188-190`) | bad-pixel replacement (P16) | — |
| Flat field across columns | `SKEW` (linear), `AUTO_LIM` (trim), the quadratic ratio in the merge | none | **needed for pinhole data** (§2.3 hump) |
| Background | `CLEAN` | none in GID | — |
| Error after smoothing | `SM_ermult` | no smoothing | — |

---

## 5. Gems, ranked by value (question 5)

| # | Gem | Source | Value for the reader |
|---|---|---|---|
| G1 | **Per-column angles in pinhole geometry** (`/pinhole`, `/indiv`, pixel raw unit) | `pd_pin.pro:299-301, 365`; `pd_view.pro:55-59` | NX scan 11: from 4 % of the counts to ≈ 50 sample-seeing columns. Resolution is set by (S4 gap + p)/D_p ≈ 0.08° per column, versus ≈ 0.15° for a 3-column slit *(inferred)*. This is D36/F45 |
| G2 | **The pinhole distance (S7D) on the horizontal axis, the sample distance on the vertical** | `pd_view.pro:56` | the reader has the box; it should be automatic for pinhole data. Unchecked, the horizontal scale of NX GID frames is wrong by ×2.03 (551/271) in cuts and display. The distance should be fittable from a peak drift (measured 256–265 mm, App. A) |
| G3 | **Observable-range limits from footprint and slits, trimmed by a fraction weighted by S5L/S5R** (`AUTO_LIM`, `LIMITS`, `PD_PIN_RANGE`) | `pd_pin.pro:88-100, 278-297` | keeps the columns where the sample is seen. On NX the S5 window (29–137) is wider than the sample-seeing range (≈ 30–80) |
| G4 | **Smooth (quadratic) scale function instead of one constant** when merging | `pd_gipi_merge.pro:79-84` | absorbs a smooth field-of-view mismatch; useful for F62 and for joins where a constant leaves a residual (the worksheet's χ²/dof shows when) |
| G5 | **`SKEW`**: linear column flat field | `pd_pin.pro:302-329` | a cheap empirical response model; the data-driven response (§7) generalises it |
| G6 | **Background subtraction from peak-free columns, with smoothing in β** (`CLEAN`) | `pd_gid.pro:91-102, 312` | Bragg rods on a smooth subphase background |
| G7 | **Error multiplier for smoothed data** | `pd_gid.pro:313-316, 385, 392` | honest error bars if smoothing is ever added |
| G8 | **Any number of β levels; grouping by rounded angles; sort by (β, Det_Th)** | `pd_pin.pro:272-285` | removes the reader's three-level limit (P31) |
| G9 | **`PATCH_RANGE`**: rows used for the join fit | `pd_gid.pro:83-86` | keeps detector-edge rows out of the scale fit |
| G10 | `ZBIN` with any bin size (in channels) | `pd_gid.pro:159-162` | the reader's four fixed β bins become a setting |
| G11 | `SIGNED` Qxy; `YOFF` | `pd_gid.pro:55-58, 69-71` | minor |

### 5.1 Reader bugs and questionable steps that the comparison shows

| Where | What | Size / evidence |
|---|---|---|
| `pilGIDpatchData` (`mainwindow.py:3300, 3350`) | known: high-Qz frames not × average Monc; the high level is indexed with the middle level's keys | P14, P15, P31 (not new) |
| `pil_S1v = S1T + S1T` (`mainwindow.py:2195`) | known: wrong footprint when top ≠ bottom | P13 (not new) |
| `imagevjoin` (`mainwindow.py:3793`) | data2 is resampled onto data1's whole 2θ grid; outside data2's range `interp2d_linear` returns the nearest-edge value (`interp_compat.py`, docstring), so those columns of the joined map are **copies of data2's edge column**, not missing | read; already noted under F62 |
| Pinhole box, default off | for pinhole-mode data (NX scans 11/12, S4 = 0.2 mm) the cut and display axes use S2D: 2× too coarse in angle per column | measured (§2.3) |
| Display extents (`mainwindow.py:2494, 2500`) | linear (no atan) pixel→angle, while `plotHint`/`plotVint` use atan | 0.6 % of the β offset at the top row (≈ 0.05°); display only *(computed)* |
| `dth = float(...)**np.ones_like(...)` (`mainwindow.py:3285`) | `**` (power), where `*` was probably meant; the value is unchanged (x¹ = x) | cosmetic |
| Relaxed Q map (`mainwindow.py:3557-3558`) | fill value 1e-10 instead of NaN, so the sums `gid_h`, `gid_v` treat empty regions as zero data | read; small bias in the integrated cuts at the map edges |
| Join factor errors | `facerr = sqrt(pcov)` from `curve_fit` with `sigma` but no `absolute_sigma` (`mainwindow.py:3729, 3822`): the error is rescaled by χ²/dof | read; legitimate choice, but it should be stated in the worksheet tooltip |
| Each join uses the β- (or 2θ-)integrated profiles only | a scale that varies with β (e.g. footprint/β-dependent transmission) is invisible to the fit | inferred |

**IDL issue noticed (inferred, not run).** In `PD_PIN`, if the first scan is
read whole (non-`varan`) and a later scan frame by frame, `SKEW` is applied
twice to the later scan: per frame at `pd_pin.pro:308` (`skfl`), then
again at `:329` (`tkfl`, still 1). In the opposite order, later whole-scan
reads get no skew, because `tkfl` was cleared at `:306`.

---

## 6. Missing routines (question 6)

| Priority | Routine | Needed for |
|---|---|---|
| **1** | `SCAN_PD_READ` and `SCAN_PD_LCOO` (MIDL/SPEC library) | the actual pixel→angle→Q formulas, what `/pinhole` changes, the `/norm` and `/bad` arithmetic, polarisation or other corrections, error handling |
| **1** | `IMG_JOIN` | how overlaps are combined (`/hor`, `/ver`, `/tran`): interpolation, weights, scale factors, the treatment of different extents (F62). "Follow the IDL joins" depends on it |
| **2** | `PD_GID_READ` | GID horizontal patching, `SIN_NORM`, `PATCH_RANGE`, `SLIT`/`YOFF`, `RELAXED`, β grouping |
| **2** | `PD_PIN_RANGE` | the observable column range from the footprint and slits (`LIMITS`, `AUTO_LIM`) |
| **2** | `SPEC_FILE_INFO` (the FILDAT structure) and `SCAN_FIELD_READ` | the definitions of `PDSDIST`, `Angs` (indices 0–2), `sl_val` (layout [slit, T/B/L/R]?), `varan`, `pdstat`, and the SPEC header items they come from |
| 3 | `IMG_SCALE`, `IMG_REFORM`, `SCAN_INTER`, `LINFIT_MM`, `POLEVAL` | confirm that values (and errors) are scaled; the meaning of `ord=2`; how x is reassigned |
| 3 | `PD_GID_INT`, `PD_GID_XYINT`, `PD_GID_ZINT`, `PD_GID_ZBIN`, `PD_GID_CLEAN`, `IMG_SMOOTH`, `SM_ERMULT` | integrated profiles and errors, background, binning |
| 4 | `SCAN_PD_FRAMES`, `SCAN_PD_FPREAD`, `SCAN_PD_CENTER`, `IMG_EQUALIZE`, `DISPLAY_MM`, `OP_SFF`, `WIMG_MM` | display and file handling; not needed |

**Even more useful than the code:** IDL output (`PD_PIN` or `PD_GID`
results, the `RESULT` keyword) for one data set the reader can open, for
example NX school scans 11 and 12. These would be the reference numbers that F45
asks for.

---

## 7. Specification: pinhole correction before patching, and joins

### 7.1 Names and inputs (per frame i, as the reader stores them)

| Symbol | Reader name / SPEC | NX scan 11 |
|---|---|---|
| N_i[r,c] | raw counts (before ÷ Monc); keep them, do not start from `pilData` | — |
| M_i | `pilMonc[i]` (Monc) | ≈ 2.2×10⁶ |
| Det_Th_i | `pil_Dth[i]` (rad), from the SPEC column `Det_Th` | 14–18° |
| c0 | `xcenter` = NCOLS−1 − `DBPos[1]` | 47 |
| r0 | `ycenter` = `DBPos[0]` | 53 |
| S2D | `pil_Dist` (`S2D_Dist`, `#B1` 3rd number) | 551 mm |
| D_p | `pil_PDist` (`S7D_Dist`, `#B1` 4th number); a worksheet setting, default S7D, fittable | 271 mm (measured 256–265) |
| L1 | S2D − D_p (sample → pinhole) | 280 mm |
| w_p | `pil_S4h` = S4L + S4R (pinhole gap) | 0.2 mm |
| S5L, S5R | header `S5L`, `S5R` (store them separately; today only their sum, `pil_S5h`) | 3.0, 14.0 mm |
| d5 | S5 → detector distance; `hard_slit_offset_mm` (32) | 25–32 mm measured |
| α, α_t, λ | `pilAlpha`, `pilTrueAlpha` (In_Rot), `pil_Wavelength` | — |
| S1h, S1v | `pil_S1h`; `pil_S1v` **fixed to S1T + S1B** (P13) | 2.0, 0.1 mm |
| p | 0.172 mm | — |

**When the mode applies:** a frame is "pinhole" when the user says so (the
existing box, moved into the worksheet). It could also be suggested
automatically when `w_p` is below a threshold, for example 1 mm (§8 Q3).
With the mode off, nothing changes (the legacy fixtures stay
byte-identical, rule 3).

### 7.2 Order of operations

1. **Read** N_i, M_i and the geometry. Apply the bad-pixel correction as now.
2. **Column angles:** `2θ_ic = Det_Th_i + atan((c − c0)·p / D_p)`.
3. **Row angles:** `β_r = atan((r − r0)·p / S2D) + arcsin(2 sin α − sin α_t)`, as in
   `plotHint`. Optionally, use a per-column distance (step 3b).
4. **Column window:** `c ∈ [c0 − S5L·k5/p, c0 + S5R·k5/p]` with
   `k5 = D_p/(D_p − d5)` (predicts 27–139 for NX; measured 29–137). Then
   trim by a fraction f weighted by S5L/S5R exactly as `AUTO_LIM`
   (`pd_pin.pro:296`), and/or set a user range in the worksheet. Columns
   outside are not used.
5. **Per-pixel normalisation** `W_ic[r] = M_i · A(2θ_ic, δ_ic) · P(2θ_ic, β_r) · R(c)`:
   - `A`: footprint fraction seen by column c (7.3).
   - `P = 1 − (sin 2θ_ic · cos β_r)²`.
   - `R(c)`: residual column response, default 1. It can be estimated
     from the data (7.3), or set to IDL's `SKEW` form `1 + s·u`,
     u ∈ [−1, 1] across the window.
6. **Bin within one Qz level** (all frames of the selected scans at that level that
   share slits and monitor gain) onto a common 2θ grid. Default step: one
   column, `p/D_p` (0.036° on NX). Rows keep their β grid, which is the same for all
   frames of a level. Estimator per bin k, row r:
   `I_kr = Σ N / Σ W`, `σ_kr = √(Σ N) / Σ W`, with sums over all
   (i, c) whose angular interval overlaps bin k, weighted by the overlap fraction
   (split pixels; this avoids aliasing between the 0.1° Det_Th step and the
   0.036° column). Bins with Σ W = 0 are NaN.
   *No pairwise joins and no fitted factors inside one scan:* the frames
   share one normalisation, so a factor between them would only add noise
   *(inferred)*.
7. **Between scans at one level** with different slits or gain: bin each
   separately, then fit one factor on the common 2θ bins (as `imagehjoin`,
   weighted), log it in the worksheet, and combine by step 6's estimator with
   the factor applied to W. Optional (G4): a quadratic factor in 2θ, as in
   `PD_GIPI_MERGE`.
8. **Between Qz levels** (vertical join): both levels are already on the same
   2θ grid (step 6 uses one global grid), so no 2θ interpolation is needed.
   - The factor is fitted only over 2θ bins present in both levels and over
     the overlapping β rows (`PATCH_RANGE`-like row limits).
   - Data in the overlap combine by the step-6 estimator. Where only one
     level has data, it is used alone; the union is kept (this is F62).
   - The β grids of two levels differ, so the rows of the second level are
     interpolated in β onto the first level's rows only inside the overlap.
     Better: put both onto one β grid by the same split-pixel binning.
9. **Corrections already applied:** step 5 includes area and polarisation, so
   `gidCorrect` is skipped for pinhole maps (no double correction).
10. **Q map:** as `pilGIDPlot`, from (2θ, β) per bin.

### 7.3 Formulas for A(c) and R(c)

**A: footprint fraction.** Generalise `calArea` to an off-axis band and
keep it pure, in `lss_core/gid.py`:

- Band axis: the line through the pinhole centre `P = L1(cos Det_Th, sin Det_Th)`
  with direction `2θ_ic`. Its signed perpendicular offset from the sample
  centre is `e = −L1·sin δ`, with `δ = 2θ_ic − Det_Th`.
- Band edges: as in `calArea`, with the two apertures being the pinhole (w_p
  at L1) and the column (p at S2D). The half-divergence is
  `φ = arcsin(((w_p+p)/2) / √(((w_p+p)/2)² + D_p²))`, and the half-width at
  the sample is `h = (w_p/2·S2D + p/2·L1) / √(((w_p+p)/2)² + D_p²)`. These
  are `calArea`'s `phi` and `dist` with `s4h = w_p`, `s5h = p`,
  `sam2d = S2D`, `sli2s = L1`.
- `A = area(footprint rectangle ∩ band) / (s1x·s1y)`, with
  `s1x = S1v/sin α_t`, `s1y = S1h`. Compute it by clipping the rectangle
  with the band's two edge lines (Sutherland–Hodgman), not by `calArea`'s
  segment-crossing bookkeeping.
- Limits to check: at `e = 0` the result must equal `calArea`. For a long
  footprint, `A ∝ 1/sin 2θ_ic` (IDL `SIN_NORM`).

**R: residual column response, from the data.** In a Det_Th scan every
2θ is seen by many columns. Model `N_icr ≈ M_i·A·P·R(c)·S(2θ_ic, β_r)`, and
solve for R and S alternately:

1. Start with R = 1. Bin S with step 6.
2. Set `R(c) = Σ_i,r N / Σ_i,r M·A·P·S(2θ_ic, β_r)`.
3. Repeat to convergence, normalised so that `R(c0) = 1` (or the mean over the
   window is 1).

Report R(c) in the worksheet as a curve. On NX scan 11 it should show the
hump of §2.3. A smoothness constraint (low-order polynomial or spline in
c) keeps it from absorbing peak structure, and IDL's `SKEW` is its first-order
special case.

**3b (optional; ask the owner): per-column distance for β.** The column c
sees the footprint at `x0 ≈ −L1 sin δ / sin 2θ_c`. Its distance to the
detector is ≈ `S2D − x0·cos 2θ_c` *(inferred)*, which is ±20 mm (±3.6 %) at the edge of
NX's sample-seeing range. A β scale error of 3.6 % at the top row
(≈ 7.7° above the horizon) is ≈ 0.28°, i.e. ΔQz ≈ 0.025 Å⁻¹. Proposed:
`β_rc = arcsin(2 sin α − sin α_t) + atan((r − r0)·p / R_c)` with
`R_c = S2D − x0(c)·cos 2θ_c`. Whether Mati did this is unknown ("horizontal"
only, `pd_view.pro:56`, suggests not).

### 7.4 Where the code goes

All of this should go in `lss_core/gid.py` (pure functions, no Qt): column angles,
window, footprint fraction, response fit, binning and joins, returning a map
with σ and a join log. `pilGIDpatchData` would then call it when the pinhole mode is
on. New settings go in `GIDParams`: `pinhole`, `pinhole_distance_mm`,
`window_fraction`, `column_range`, `response` ('none' | 'skew' | 'fit'),
`bin_step_deg`, `beta_per_column`. The worksheet shows them, plus R(c) and the
fitted distance.

### 7.5 What to test (properties and numbers)

| Test | Kind | Check |
|---|---|---|
| T1 | invariant | Pinhole mode off: legacy GID fixtures and `tests/reference/nx_school_gid_scan_11_*` unchanged |
| T2 | characterisation | Pinhole mode on, columns c0 ± 1 only, `R = 1`: the β-integrated 2θ profile, rebinned to the Det_Th grid, agrees with today's patch within errors; `A(e=0) == calArea` (≤ 1e-12 relative) |
| T3 | invariant | Footprint fraction: `A(e=0)` = `calArea` on a grid of slits and angles; long footprint `A·sin 2θ` constant; `A = 0` when the band misses the footprint; A symmetric under `e → −e` at 2θ = 90° |
| T4 | synthetic | One sharp in-plane ring at 2θ_f, rendered through a pinhole (D_p ≠ S2D) over a Det_Th scan. In every frame the peak lands at 2θ_f ± ½ column. The binned peak FWHM does not grow with the number of columns used (3, 21, 101). Its centre does not move |
| T5 | invariant | Counts are conserved: `Σ_kr I_kr·ΣW = Σ N` over used pixels (exact, split pixels included) |
| T6 | synthetic | Poisson replicas: pulls `(I − truth)/σ` have mean 0 and width 1 ± 0.05; σ falls as 1/√(columns used) on a flat response |
| T7 | synthetic | A known response R(c) (use the NX hump) and smooth S: the fit recovers R to < 1 % and S to within σ |
| T8 | real (slow) | NX scan 11, frames 17–31: the peak drift gives D_p within 6 % of `S7D_Dist` (measured 265 mm vs 271) and ≥ 40 % from S2D. The peak 2θ is 16.63 ± 0.02° from both the per-column map and the 3-column legacy map (cross-check of c0 = 47) |
| T9 | real (slow) | NX scan 11 window from S5: predicted 27–139, measured lit 29–137 (± 3 columns) |
| T10 | synthetic (F62) | Two levels with different 2θ extents. The joined map covers the union, the factor uses only the intersection, there are no values outside either level's range (NaN, not an edge copy), and the factor equals the true one within its error |
| T11 | as coded | Polarisation per column equals the legacy factor at c = c0 |
| T12 | real (slow) | NX scans 11 + 12 patched in pinhole mode: the factor between levels and its χ²/dof are logged; the map shows no step at the level boundary larger than 2σ |

---

## 8. Questions for the owner

1. Please send **`SCAN_PD_READ`, `SCAN_PD_LCOO`, `IMG_JOIN`, `PD_GID_READ`,
   `PD_PIN_RANGE`**, and the FILDAT definition (`SPEC_FILE_INFO`,
   `SCAN_FIELD_READ`). If possible, also send IDL output for one data set the
   reader can open (NX school scans 11 + 12 would be ideal).
2. Is `S7D_Dist` (`#B1`, 4th number) the **S4-to-detector distance**? The
   measured effective distance is 256–265 mm against 271 in the header. Is
   S5 the slit ≈ 25–32 mm in front of the detector (the "hard slits", 32 mm in
   `calArea`)?
3. Are the GID scans at 15-ID-C now routinely taken in pinhole mode (S4 gap
   ≈ 0.2 mm, S5 wide and asymmetric), as NX scans 11/12 are? Should the
   reader switch the mode on automatically from the S4 gap, and above what gap
   is a scan "not pinhole"?
4. Should the per-column mode replace the 3-column patch for pinhole data,
   or be an option? Which columns: the S5 window, or only where the sample is
   seen (≈ 30–80 on NX)?
5. Column response: estimate it from the data (§7.3), or keep it geometric
   plus IDL's `SKEW`/`AUTO_LIM`?
6. Overlap arithmetic: is count-weighted binning (Σ N / Σ W) acceptable, as
   opposed to the reader's plain average or IDL's `IMG_JOIN` (once known)? Do you want the
   `PD_GIPI_MERGE`-style quadratic factor as an option?
7. Did Mati correct β per column for the scattering point's distance
   (±3.6 % in β scale at the window edges on NX)?
8. Is GID always measured at one absorber setting?
9. "Pinhole data" in `PD_MERGE`: separate static exposures (summed frames)
   at a fixed Det_Th, or pinhole Det_Th scans? Is the merge still used?

---

## Appendix A. Measurements (all on `sample_data/NX_school/2026sep`, scan 11)

All runs were read-only, with Python 3 and `lss_core.images.read_pilatus`
(the reader's orientation). Rows 15–486 were summed unless stated otherwise.

- **Header** (`20260923`, scan 11): `#B1 53 147 551.000000 271.000000` →
  DBPos = (53, 147), S2D = 551, S7D = 271. Also In_Rot 0.0905°; S1T = S1B =
  0.0500; S1L = S1R = 1.000; S4L = S4R = 0.1; S4T 51, S4B 7.3; S5L
  2.99986, S5R 13.9999. Scan 12 is the same, with Out_Rot 6.5° (second Qz level). The
  header also lists the motors `X_Pinhole`, `Y_Pinhole` (0.019, −10) and slits S6, S7. Their role is
  unknown.
- **Lit window:** the summed column profile over 41 frames is > 20 % of the maximum on
  columns 29–137. Columns 138–142 total 72, 64, 72, 62, 47 counts, against
  ≈ 11 000 at columns 50–56.
- **Reader's columns:** with the SPEC values, xcen = 194 − 147 = 47, and the H slit
  of 3 sums columns 46–48. Per frame (median) that is 776 counts in 46–48 against 18 434 in 29–137.
- **Distance from the peak drift:** the centroid of (frame − median frame) within
  ±6 columns of the maximum, fitted linearly against Det_Th: −26.89, −26.88
  and −25.98 columns/degree (frames 17–31, 19–29, 21–27). The rms residual is 0.3, 0.3
  and 0.11 columns. Distance = |slope|·p·180/π = 265.0, 264.9, 256.0 mm.
  The expected slope is 27.5 columns/degree for 271 mm and 55.9 for 551 mm.
- **Column response:** the peak excess, summed over ±3 columns at the column
  predicted by `47 + (16.65 − Det_Th)·26.7`, is in the table of §2.3.
  For cols 86–118 (Det_Th 14.0–15.2) it is 49–188 against a background of
  ≈ 750; for cols 43–64 it is 1264–1498.
- **`calArea` against `SIN_NORM`:** `MainWindow.calArea` was called unbound
  with a stand-in `self` (GIDParams defaults, H slit 3). The area info was
  `[2.0005, 0.0999, 0.2, 16.9998, 0.0905°, 551, 271]`. The results were 0.061403,
  0.057394, 0.053892, 0.050807, 0.048070 at 14–18°. Times sin 2θ:
  0.0148547, 0.0148547, 0.0148546, 0.0148546, 0.0148546.
