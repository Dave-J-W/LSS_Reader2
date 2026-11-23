# Image display: assessment and phase-2 requirements

Owner's requests F68–F72 (2026-11-22; `docs/FEATURE_REQUESTS.md`). Part 1
covers how every image or 2D map is drawn today. Part 2 is the phase-2
specification. The questions are in `questions/image_display.md` (`Q-IMG-n`).

**Evidence.** **[M]** means measured on 2026-11-22 by driving the window
offscreen on the public NX school file `sample_data/NX_school/2026sep/20260923`
(scripts kept outside the repository; how to rerun them is in the appendix).
**[R]** means found by reading the code only. NX scans: 6–9 reflectivity
(19, 27, 21, 29 frames), 11–12 GID (41 and 4 frames), 14–15 GID burn
(21 frames each). Matplotlib 3.11, Python 3.13.

---

## Part 1 — Assessment of today's display

### 1.1 Where images are drawn

| # | View | Canvas (widget) | Code | Shows |
|---|---|---|---|---|
| A | Pilatus frames | `pilMplWidget` (Mpl2DWidget), Pilatus tab | `updatePilPlotData` | Selected frames tiled (up to 10), or their mean ("Sum All") |
| B | Movie | same canvas | `pilMovieShow` → `updatePilPlotData` with `pilmovieindex=1` | Each selected frame in turn, 0.5 s apart, as a blocking loop |
| C | GID map | same canvas, replaces the frames | `gidShowMap` → `pilGIDPlot` | Patched map, plus a Qxy profile, a Qz profile and four Qz-binned profiles, each on its own axes |
| D | GISAXS | same canvas | `showPilGISAXS` | One frame (or the mean), regridded onto Qxy–Qz with `griddata` |
| E | Reflectivity ROI close-up | `refADDataPlotWidget`, Reflectivity tab | `refQzListSelectionChanged`, `refAnalyze` | Strip around the signal and background boxes: "w/o Corr" (before the peak search) and "w Corr" (after it) |
| F | 2D_Plot tab | `twodPlotMplWidget` (MplWidget) | `update2dPlotPlot` | 2D text files from disk (x, y, I) shown with `pcolor` or `imshow` |
| G | Line/Area Cuts | `cutPlotMplWidget` | `updatePilCutData`, `updatePilGIDCutData` | 1D cuts only. **Nothing is drawn on the image** |
| H | Burn test dialog | `pdburn.ui` | `plotBurnTrends`, `pilRefBurn`, `pilGidBurn` | Trends against time only. **No frame view** |
| I | GIOXS dialog | `pdgioxs.ui` | `pilGioxsRun` | 1D Qz profiles (log y). No image |
| — | `pilGIDData` (old "GID rod" `pcolor`) | — | — | **Dead code [R]**: nothing calls it |
| — | Apex tab (`gix*`) | hidden | — | Detector defunct. Its colour-map box `gixCMapComboBox` is still read by view E's "w Corr" panel, and the user cannot reach it [R] |

The widgets are `mplwidget.py` and `mpl2dwidget.py`: one bare `FigureCanvas`
plus the standard matplotlib toolbar each. `mpl2Dwidget1.py` is PyQt4 and
unused. No widget has a mouse handler: `mpl_connect` appears nowhere in the
application, and no `RectangleSelector` or `SpanSelector` is used. The only
interaction is the toolbar's pan and zoom, and the status-bar readout [R].

### 1.2 Pilatus tab (views A, B): controls and defaults

| Control | Default | Behaviour | Tooltip |
|---|---|---|---|
| Image list, "Select All" | — | Selects every frame of the selected scans. Common in practice (owner) | no |
| "Sum All" (`gixSumCheckBox`) | off | Shows the **mean** of the frames, despite its name. Refuses ("different qz") unless every frame has the same Qz | no |
| Axes: Pixels / Angles / Q | Pixels | Extent only; the image is not resampled | no |
| CMap | **jet** | jet, gray, hot, summer, winter, rainbow | no |
| Aspect | **auto** | auto stretches the 487 × 195 frame to the canvas | no |
| Log Int | off | Shows `log10(data+1)` without a background, `log10(max(data, 1e-10))` with one; limits are `log10` of the typed Min and Max | no |
| Min/Max fields and sliders | min non-zero and max **of the first selected frame** | Sliders go 0–100 % of (max − min); slider × range is used **without adding min** [R] | no |
| Pinhole | on | Horizontal angle from the S4–detector distance when Det_Th > 1° | yes |
| DB Pos, SD Dist, "from SPEC" | from the header | Geometry for the Angles and Q axes | no |
| Bad Pix Corr. Iter., Fact. | 0, 1 | Replaces pixels that differ from their neighbours | no |
| Movie | — | See view B below | no |

**What is drawn.**
- At most 10 frames, laid out in a grid, each with its own colour bar.
  `fig.clf()` and `tight_layout()` run on every redraw.
- Interpolation is **bicubic** on raw pixel counts. This smooths hot pixels
  and a beam only a few pixels wide; view E uses `nearest`.
- In Angles mode a white dashed line marks the detector-arm column. No
  ROI, background box or direct-beam mark is ever drawn on the full frame.
- The suptitle is the file name and the scan numbers. Each tile is titled
  `F #<list row>`, which is the row in the image list, **not the point
  number**. There is no Qz, time or absorber label on the image; those are
  only in the list text.
- **Units change without notice [R]:** with no background selected the
  frame shown is raw counts. With a background selected it is per monitor,
  absorber-corrected, minus Fac × background. The colour bar has no label
  in either case.

**Measured [M]:**

| Measurement | Result |
|---|---|
| Select All, scan 7 (27 frames), scan 11 (41), scan 14 (21) | **10 image axes + 10 colour bars = 20 axes** each time; first 10 frames only, with no message; ~1.0 s |
| Tile size, window 1600 × 1000 (canvas 1767 × 443 px) | ~238 px wide and ~90 px tall per tile. Titles, the suptitle and the axis labels overlap (font size 16) |
| Default colour limits, scan 7 frame 0 | max 215 717 counts, from the direct beam on the frame. 99.9th percentile 2 116, 99.5th 35, median 0; 97.8 % of the pixels are 0 |
| Same limits applied to every selected frame | Per-frame maxima in scan 7 range from 1 255 to 215 717 (99.9th percentile 4 to 2 116). With Select All, **every tile is uniformly dark blue** (screenshot) |
| Min field | **−2.0**: the frame holds one pixel of value −2 (Pilatus bad-pixel marker; that Dectris value is from memory) |
| Log Int with that Min | `log10(−2)` = NaN, so the norm becomes **−0.1…0.1** decades. **The log view is a binary mask** whenever the first frame has a negative pixel (screenshot of scan 7 frame 0) |
| Redraw, one frame | 0.20 s linear, 0.20 s log (median of 5). Time goes to tick and text layout, `clf`, `tight_layout`, bicubic resampling (~0.04 s) |
| Redraw, 10 tiles | 0.71–0.76 s linear, 0.78–0.81 s log |
| Zoom (toolbar) after toggling Log, after changing CMap, after selecting the next frame | **Reset to the full frame every time** |
| CMap, Min/Max after selecting another frame | CMap kept for the session. **Min/Max recomputed** from the new first frame (215 717 → 8 581) |
| Cursor readout over tile 0 with 2 frames tiled | Shows **the last frame's value** (1.62e3 where tile 0 holds 2.16e5): `format_pil_coord` reads `self.Zdata`, which is the last tile drawn |
| Movie, scan 14 (21 frames) | **14.6 s blocking**, 21 full redraws (0.5 s sleep each) |
| Axes box after Movie | Left at **Q**. The movie also forces Pinhole on while it plays [R] |
| Nothing persists between sessions | `preferences.py` has no display key; the workbook stores none [R] |

**Movie today [R]:** it is a `for` loop with `time.sleep(0.5)` and
`flush_events`. There is no pause, step, speed control, slider or stop
button; it cannot be interrupted, and the Axes box is switched to Q for
good. Zoom is lost on every frame (`clf`).

### 1.3 GID map (view C)

- **How it is reached:** GID box → "GID Patch" (pinhole by default) or
  "GID Patch Relax". The map **replaces** the frames on the Pilatus canvas.
  Selecting any frame afterwards removes the map (back to 2 axes [M]).
  The Axes box is forced to Q, or to Angles for the dead rod code [R].
- **Layout:** map, colour bar, "Integrated over Qz" (Qxy profile),
  "Integrated over Qxy" (Qz profile) and "Qz-binned" (4 bands stacked) =
  **5 axes** [M]. The Qz bands are fixed by the patch (three Qz levels);
  the user cannot choose them.
- **Pixels:** the map is interpolated ×10 along x (`interp1d`), then drawn
  bicubic. Limits come from the map's max and min non-zero
  (map 459 × 180: max 172, 99.9th percentile 65, median 11.5 [M]).
- **Form-factor overlay:** sphere or ellipsoid minima as white curves
  (`pdformfac.ui`).
- **Measured cost [M]:** patch 6.8 s. Every redraw takes **2.7–3.0 s**,
  whether linear or log; **2.1 s of it is `gidProducts` → `griddata`**,
  which regrids the map to Q again on every redraw. Changing the colour
  map or Log Int therefore costs about 3 s.
- **Line cuts:** "Q H" and "Q V" use the typed range on the regridded map.
  The upper index is exclusive (`ini:fin`), while the frame cuts are
  inclusive [R].

### 1.4 GISAXS (view D)

- "Show GISAXS" needs one frame, or "Sum All".
- Each pixel goes to (Qxy, Qz) with the exact `arctan` geometry, followed
  by `griddata` (linear) onto a regular grid: 487 × 196 for scan 7 [M],
  2.65 s.
- Uses `xcenter = NCOLS − x`, whereas view A uses `NCOLS − 1 − x`: the two
  differ by one column [R].
- The Axes box is forced to Q. Empty cells are filled with 1e-10, which
  dominates a log view.
- No Yoneda mark, no horizon line, no specular mark.

### 1.5 Reflectivity ROI close-up (view E)

- **How it is reached:** "Reflectivity" or "Ref Patch" opens the Qz list
  on the Reflectivity tab. Selecting a Qz draws the first panel; "Analyze"
  adds the second [M].
- **What is drawn:** a strip of `2·slitV+1` rows by
  (left background − slit … right background + slit) columns, e.g. 23 × 96
  px for slit "21,11", BG offset 0.5°, direction H.
  - Linear only; `vmax` = max of the strip; `nearest` interpolation.
  - jet (panel 1 uses the Pilatus CMap; panel 2 uses the hidden Apex CMap).
- **Boxes:** drawn by **writing 100 × the image maximum into the border
  pixels** (`TwoDDetector.setROI`), not as overlay patches. They are
  "burned in" and saturate the colour scale.
- **Measured mismatch [M]:** drawn background-box centres are columns 20
  and 74; summed centres (`sumROI`, which uses slit − 2) are **21 and 72**.
  The right background box shown is 2 px away from the one summed. The
  signal box border matches the summed area (37–57).
- **Missing:** profiles through the ROI, net/signal/background numbers on
  the plot (they are in the fields R, R_Err, %R_Err), any cue for an
  off-centre peak, a clipped peak or a background box touching the signal,
  and any follow-the-movie behaviour.
- **Cursor readout:** `format_coord_ref` swaps rows and columns and uses
  `self.extent` (of view A) rather than `self.refextent`, so it gives
  wrong pixel values [R].
- The second panel ("w Corr") looks almost identical to the first in the
  NX frames (screenshot). Labels overlap.

### 1.6 2D_Plot tab (view F)

- Controls: Min/Max fields and sliders, Log Int, Show Color Bar, CMap (jet,
  gray, hot, summer, winter, **spectral**), label and tick size,
  interpolation density and method.
- **`spectral` is not a valid colour map in matplotlib ≥ 2.2** [M:
  `KeyError` on 3.11]. Choosing it raises. (fixed 2026-11-23: offered as `nipy_spectral`, the same map under its current name; `tests/test_gui_2dplot.py`)
- Axes are always labelled Qxy and Qz.

### 1.7 Line cuts today (for F68)

| Where | Interface | Defaults | Problems |
|---|---|---|---|
| Pilatus tab bottom row | Direction box (Q H, Q V, Pix H, Pix V) + typed `min:max` + "Line/Area Cuts" → Cuts tab | Q H 0:1, Q V 1:2, Pix H 0:485, Pix V 0:194, whatever the scan | Not drawn on the image. The Q V default 1–2 Å⁻¹ misses a reflectivity frame and gives zeros with no message (F59). Geometry: cuts use `arctan`, image axes use pixel/D (P6; at the top edge of scan 7 frame 3, β = 7.744° vs 7.698°, **0.05°** [M]). Pinhole per axis (P38) |
| GID map | same boxes, Q H and Q V only | same | Exclusive upper index; Pix cuts refused |
| GISAXS | same | same | — |
| GID map side panels | fixed integrations | whole map | Not adjustable |
| Reflectivity | none | — | Profiles through the ROI are missing |
| 2D_Plot | none | — | — |

`lss_core/cuts.py` (`frame_cut`, `mean_frame`) is the core of the frame
cuts and is scriptable (`Experiment.cut`). Cuts are monitor-normalised;
the image shown is raw counts (§1.2), so a cut and the image differ in
units.

### 1.8 Persistence today

| What | Kept between frames | Kept between sessions |
|---|---|---|
| Zoom | **no** (every redraw clears the figure) | no |
| Colour limits | **no** (recomputed from the first frame on every selection) | no |
| Log, CMap, Aspect, Axes | yes (widget state), but Movie, GID and GISAXS overwrite Axes | no |
| Display mode (tiles, sum, movie) | "Sum All" yes; Movie is a one-shot | no |

`lss_core/preferences.py` stores no display key. The workbook's Settings
sheet stores fitting options only [R].

### 1.9 Pain points, ranked

1. Select All gives 10 tiny tiles, silently drops the rest, and with the
   default limits shows every tile uniformly dark (§1.2).
2. Colour limits come from the first frame's maximum, which on
   reflectivity frames is the direct beam (×100 the 99.9th percentile).
   A negative bad pixel breaks the log view completely.
3. Zoom is lost on every change, so a close look at the beam has to be
   redone for each frame.
4. The movie blocks for N × 0.7 s with no controls and changes the axes
   for good.
5. Wrong cursor values (tiled view, ROI close-up).
6. The units of the image and colour bar are not shown, and change
   silently when a background is selected.
7. ROI and background boxes are not shown on the frame. In the close-up
   they are burned into the pixels and partly misplaced (2 px).
8. There is no graphical line-cut interface; the typed defaults are blind
   to the scan kind.
9. jet is the default, and an invalid `spectral` entry is offered.
10. GID map redraws cost about 3 s each, mostly regridding that does not
    change between redraws.

### 1.10 Notes for faster log plotting (F72; later, not designed here)

Measured [M]: for frames, **log is not slower than linear** (0.20 vs
0.20 s; 0.73 vs 0.80 s for 10 tiles). The cost is in rebuilding the
figure:
- `fig.clf()` on every change;
- new axes and colour bars;
- `tight_layout`;
- text and tick layout;
- bicubic resampling;
- for GID, `griddata` (2.1 s of 2.8 s).

What will help: keep the artists and call `set_data`/`set_norm`, use
`blit`, use `LogNorm` instead of precomputed `log10` arrays, cache GID
products per axes kind, and use `nearest` interpolation. If the owner's
slow log plots are 1D (SpecPlot/MCA log y), that path was not measured
here.

---

## Part 2 — Phase-2 requirements

Sizes: **S** ≤ 1 day, **M** 2–5 days, **L** > 1 week, including tests and
docs. Every requirement keeps the reduction numbers unchanged: display
only, except where marked. A new `lss_core/display.py` (GUI-free: limits,
sampling, kinds, profiles) can be tested without Qt. One reusable
`ImageView` widget (canvas + toolbar + controls + cut overlay) replaces
the copy-pasted `imshow` blocks in views A–F.

### 2.0 How the reader knows the scan kind (needed by every default)

| Source | Gives | Today |
|---|---|---|
| `#U Series kind=` (when SPEC writes it) | reflectivity, gid, gisaxs, xfntr, direct_beam, alignment, burn, energy, other | parsed (`series.py`) |
| `series.infer` | reflectivity (L scans), gid (`ascan dth`), burn (`ascan ih` fixed), xfntr, energy | built |
| Underlying kind of a burn scan | **not known**; proposal: Det_Th > 1° (or Qxy ≠ 0) → burn-gid, else burn-ref | missing (S) |
| Frame role inside a scan | direct beam (Qz ≈ 0 / role=direct), dark/beam-off (Monc ≈ 0 or shutter column) | missing (S) |
| Detector | Pilatus 100K/200K (487 × 195); 1M later | `specPar[..]['Detector']` |

**Requirement K1 (S):** `display.kind_of(frames)` returns one of `ref`,
`gid`, `gisaxs`, `burn-ref`, `burn-gid`, `direct`, `dark`, `other`. It uses
the series kind first, then the frame metadata. The kind is shown in the
frame metadata strip (§2.7), and the user can override it per scan (the
override is kept in the workbook).

### 2.1 Frame display modes (F69)

| Mode | What | Default N | When chosen by default |
|---|---|---|---|
| **Movie** | One large frame. Steps through the selection | — | **default for any selection of more than 1 frame** |
| **Sampled** | First, evenly spaced middles, last | **4** (1–6) | user's choice |
| **First n** | Frames 1…n of the selection | 4 (1–6) | user's choice |
| **Mean / Sum / Max** | One projection of the selection (§2.6) | — | user's choice ("Sum All" today) |
| Single | One frame | — | when 1 frame is selected |

Never more than **6 tiles**. If the selection is larger and the mode is
tiled, the title says "4 of 41 shown (sampled)".

Sampling rule (`display.sample(n_sel, N)`): indices
`round(linspace(0, n_sel−1, N))`, duplicates removed. For example 41
frames, N = 4 → 0, 13, 27, 40.

**Movie controls** (one toolbar row under the image):

```
 |<  <  [>||]  >  >|   [=======o===============]  14 / 41   speed [2 fps v]  [loop]
 S# 11  pt 13  Qz 0.215  2θ 18.40°  t 412 s  abs 2   Monc 1.2e5     colour: [shared v]
```

- **Requirement M1 (M):** a QTimer-driven, non-blocking movie.
  - Controls: play/pause, step ±1, first/last, a slider, a frame counter,
    speed (0.5–10 fps, default 2), loop.
  - Keys: ←/→ step, space plays or pauses.
  - Selecting another frame in the list moves the movie there; the list
    highlights the frame shown.
- **M2 (M): sticky zoom.** The image artist is updated with `set_data`
  without clearing the figure; xlim/ylim are kept across frames, mode
  changes, Log, CMap and Axes changes (converted between pixel, angle and
  Q by the frame's geometry). "Home" resets the zoom.
- **M3 (S): frame labels** in the metadata strip: scan, **point number**
  (not list row), Qz (ref) or 2θ/Det_Th (GID), elapsed time from the
  first frame (`timing.py`), absorber, monitor counts.
- **M4 (S): colour scale across the movie.**
  - **shared** (default): limits computed over the sampled frames of the
    selection, so the eye compares frames.
  - **per frame**: each frame scaled alone.
  - **locked**: the typed limits.
  - For reflectivity scans with changing absorbers, "shared" uses
    absorber-corrected, per-monitor values (see §2.3 units) or falls back
    to per frame. Q-IMG-4.
- **M5 (S): Select All behaviour.** Select All reads the frames as now
  (they are cached), shows the movie paused on the first frame (or the
  sampled tiles if that mode is sticky), and never draws more than 6
  tiles.
- **M6 (S): remembering the mode.** The last mode and N are a global
  preference, optionally per kind (Q-IMG-2).
- **M7 (M): a movie fixed in 2θ for GID** (owner, 2026-11-23: "For GID
  data we often watch the raw data frames in a 'movie' mode, since real
  GID peaks stay at the same two-theta and other junk does not as the
  detector angle changes"). With the frames drawn on a common 2θ (and β)
  axis and the zoom held in angle (M2's conversion by each frame's
  geometry), a real peak stands still while the detector window slides;
  anything fixed on the detector (stray light, hot pixels, slit or window
  scattering) moves. A switch to pixel axes gives the opposite view (junk
  still, peaks moving). Needs the per-pixel geometry of X2.
- Owner, 2026-11-23, for every kind: "we often want to zoom on the raw
  data (or zoom to some region around the ROI for reflectivity) and have
  the frames play in movie mode without changing the zoom or color mode or
  anything" (M2, M4, and §2.2); and for reflectivity, the frame-by-frame
  ROI check happens "mostly when something is weird and we need to verify
  the data are ok. If there was a slick way to show a movie of it, maybe on
  a log or other nonlinear scale, we might do it more often. Showing people
  the raw data helps them avoid mistakes." So the reflectivity movie opens
  zoomed to the region around the ROI (R1–R6) on log or asinh (C2, C3).
  The zoom (owner, 2026-11-23): "not too close, we do want to see the
  diffuse scattering around it, and the background zones to the sides. But
  still a healthy zoom compared to the full image": the default view holds
  the ROI and both background zones with a margin.
- Movie export (GIF/MP4) is out of scope; Q-IMG-9.

Today vs needed: the movie exists but blocks (B); tiling caps at 10; no
sampling. Size overall: **M–L**.

### 2.2 Sticky plot preferences (F70)

| Setting | Level | Reset |
|---|---|---|
| Display mode, N | global preference (per kind if Q-IMG-2 says so) | Preferences → Display → Defaults |
| Colour map | global | same |
| Colour-scale mode (auto-robust, shared/per-frame, locked) | **per scan kind** | per kind "Defaults" |
| Linear / log / asinh | per scan kind | same |
| Typed limits (locked mode) | per SPEC file, per kind (workbook Settings sheet) | "Auto" button beside the limits |
| Zoom (view box) | **per session per kind**; optionally saved per SPEC file and kind in the workbook (Q-IMG-3) | toolbar Home; "Forget zoom" |
| Axes (pixel/angle/Q), aspect | per kind | — |
| Cut defaults (§2.5) | per kind, global; last typed range per SPEC file | "Default cut" |
| Overlays (ROI boxes, masks, beam marks) | global | — |

- **P1 (S):** a `display` section in `preferences.DEFAULTS`
  (`{kind: {...}}`), loaded and saved as now. The tests already isolate
  the file.
- **P2 (S):** the workbook Settings sheet gets the per-SPEC display keys
  (locked limits, saved zooms). They are display only and never mark a
  result stale.
- **P3 (S):** one "Reset display" action per view, plus a Preferences
  page.
- **P4 (S):** Movie, GID and GISAXS stop overwriting the Axes box behind
  the user's back. Each view keeps its own Axes setting.

Size: **M**.

### 2.3 Intelligent colour scales and defaults (F70)

**C1 — robust automatic limits (S–M).** `display.limits(frames, kind, mask)`:
1. Mask first: negative pixels (Pilatus −1/−2), module gaps, hot pixels
   (§2.6), and for reflectivity/GID the **direct-beam box** (from DB Pos
   and the slit) when the frame is not a direct-beam frame.
2. Limits on what remains:
   - vmin = 1st percentile (0 for counting data);
   - vmax = 99.9th percentile, or 99.5th for sparse frames (more than
     90 % zeros, as on NX reflectivity frames: 97.8 %).
   - Alternatives: **zscale** (IRAF, Tody 1986; astropy `ZScaleInterval`),
     from memory, not installed here; and silx's percentile and 3σ
     autoscale modes (from memory).
3. Show the clipped fraction ("0.1 % above vmax") in the colour-bar
   tooltip.

Why: on NX scan 7 frame 0 the max (2.2e5, direct beam) is 100× the 99.9th
percentile [M].

**C2 — log with a floor (S).**
- Use `matplotlib.colors.LogNorm` (available [M]), not precomputed
  `log10`.
- Floor = max(0.5 count, 1st positive percentile), in counts (or that
  value / monitor when normalised). Zero and masked pixels get the "under"
  colour, which is not the lowest map colour.
- Never take the log of a negative typed limit; the current NaN failure
  must be impossible.

**C3 — asinh stretch (S).**
- `matplotlib.colors.AsinhNorm` exists [M] (marked experimental in
  matplotlib).
- Linear near zero and logarithmic at high counts, so it behaves well with
  zero counts (Lupton, Gunn & Szalay 1999, AJ 118, 1406; Lupton et al.
  2004, PASP 116, 133; from memory).
- Proposed default for sparse low-count frames. Q-IMG-5.

**C4 — defaults by kind (S).** Proposal, for the owner to confirm (Q-IMG-5):

| Kind | Scale | Limits | Mask | Notes |
|---|---|---|---|---|
| ref (specular frames) | log (or asinh) | robust, direct beam masked | negatives, hot | Reflected beam and background both visible |
| direct (attenuated direct beam) | linear | min–max of the beam box | negatives | Shape matters |
| gid frames | log | robust 1–99.9 % | negatives, hot, columns outside S5 window | Low counts |
| gid map | log | robust on finite cells | NaN cells | — |
| gisaxs | log | robust, specular and direct beam masked | — | Yoneda band visible |
| dark / beam-off | linear | robust 0.1–99.9 % | none (hot pixels are the point) | Hot-pixel overlay on |
| burn-ref / burn-gid | as the underlying kind, **shared** across the scan | — | — | Plus the difference view (§2.6) |

**C5 — colour bar with units (S).**
- The label states the units: `counts`, `counts / Monc`, `counts / Monc
  × abs` (absorber-corrected), or `photons / photon` (per-photon option
  F21).
- Choice: "Show as: counts | per monitor | per monitor, absorber-corrected".
- **Default per monitor, absorber-corrected**, so the image, the cuts and
  the ROI numbers share units (decision for `OUTPUT_DECISIONS.md`; display
  only). Q-IMG-6.
- The current silent change when a background is selected goes away.

**C6 — colour maps (S).**
- Default **viridis** for linear and **magma** or **inferno** for log
  (perceptually uniform: van der Walt & Smith, matplotlib 2.0 colour maps,
  2015; Kovesi 2015, arXiv:1509.03700; Nuñez et al. 2018, PLoS ONE
  13:e0199239 for cividis; Crameri et al. 2020, Nat. Commun. 11:5444;
  Borland & Taylor 2007, IEEE CG&A 27(2) on rainbow maps — all from
  memory).
- Offer viridis, magma, inferno, cividis, gray, plus jet for habit.
- Remove `spectral` (invalid).
- Set over and under colours (white or grey) so clipped pixels show.

**C7 — interpolation (S).** `nearest` for raw frames (pixels are data);
smoothing only for the GID map and only by choice (Q-IMG-8).

Size overall: **M**.

### 2.4 ROI close-up for reflectivity (F71)

```
+---------------------------- frame (movie) ----------------------------+  +---- ROI close-up ----+
|                                                                        |  |  bgL | sig | bgR    |
|          [bgL]   [ SIG ]   [bgR]      <- outlines, not burned pixels  |  |   ▒  | ███ |  ▒     |
|                                                                        |  +----------------------+
|     . direct beam (masked, marked x)                                   |  | col profile (sum rows)|
+------------------------------------------------------------------------+  |  ‾‾\_/‾‾‾‾/‾\‾‾‾‾\_/‾ |
 S# 7 pt 0 Qz 0.035 abs 0 ...                                              | row profile (sum cols)|
                                                                            | sig 4.05e5 ± 6.2e2   |
                                                                            | bg  1.2e2  net ...   |
                                                                            | ⚠ peak 3 px off centre|
```

- **R1 (M):** a side panel (or inset, Q-IMG-7) on the **Pilatus tab and
  the Reflectivity tab**.
  - Zoom: the signal box plus both background boxes plus a margin.
  - It follows the movie frame by frame, and the Qz list on the
    Reflectivity tab. Its colour scale comes from the signal box (robust)
    and is independent of the main image.
- **R2 (S): outlines as patches** (`Rectangle`) on both the full frame and
  the close-up, drawn from **the same box arithmetic as `sumROI`** (one
  function in `lss_core`, e.g. `reflectivity.boxes(slit, cen, bg, dir)`).
  - The burned-in borders go; this changes `imageROI`, never the sums.
  - Fixes the 2 px background mismatch measured in §1.5 (display only).
  - Shows the typed slit and the summed slit (P12) as two outlines, or
    one with a tooltip, until the owner decides P12.
- **R3 (S):** profiles through the ROI, each with the box edges marked:
  - sum over rows (column profile across signal and backgrounds);
  - sum over columns (row profile through the signal).
- **R4 (S):** numbers on the panel: signal, each background, net, σ, %σ
  (from `sumROI`/`netROI`); absorber; monitor.
- **R5 (S): cues**, each with its reason in a tooltip (rule 9):
  - **off-centre**: the peak (centroid or maximum) more than 25 % of the
    half-width from the box centre;
  - **clipped**: more than 1 % of the profile's integral, or a pixel
    above 5 % of the peak, on the box edge, or outside the box within one
    slit (P12);
  - **background overlaps signal**: background box within 2 px of the
    signal box, or its mean more than 3σ above the other background;
  - **saturation/absorber**: peak pixel above the counting limit set for
    the detector (Q-IMG-10);
  - **direct beam inside a box**.

  Thresholds are proposals (Q-IMG-7) and go in `OUTPUT_DECISIONS.md` as
  display-only.
- **R6 (S):** the close-up's cursor readout is correct (pixel, value) and
  shared with §2.7.

Today: view E is a static strip with burned borders and a misplaced box.
Size: **M**.

### 2.5 One line-cut interface for every image plot (F68, F59)

**Interface (identical on views A–F):**
- A cut toolbar:
  `[Cut: H band | V band | line | box]  axis [pixel|angle|Q|β−α|α_f]  range [lo : hi] width [w]  [Default] [→ Cuts tab] [Save]`.
- On the image: a draggable band (`SpanSelector`-like, or a translucent
  `Rectangle` with handles) for H and V cuts; a line with a width for
  arbitrary lines (phase 2b); a box for area sums.
- Typed ranges and the drawn band are **the same object**: typing moves
  the band, dragging rewrites the fields.
- A live profile appears under or beside the image (small axes, linked
  x), as in the GID map today. "→ Cuts tab" sends the cut to the Line/Area
  Cuts tab for overlay, fitting (`peaks.py`), export and workbook save.
- All arithmetic goes through `lss_core/cuts.py`, extended:
  - ranges in any axis are converted to pixels by **one per-pixel geometry
    function** (the exact one from `pinhole.py`, P38), which also gives
    the image axes. That ends P6 (0.05° at the frame edge [M]).
  - Inclusive/exclusive upper index made uniform.
  - A message when the range misses the detector (F59 defect).

**Default cuts by kind (proposal, Q-IMG-11):**

| Kind | Default cut | Default range |
|---|---|---|
| ref frame | V band through the specular column (profile vs β or Qz) and H band through the reflected row (vs 2θ or Qxy) | width = ROI slit, centred on DB column / reflected row |
| direct | both bands through the beam centre | ±3 × slit |
| gid frame | H band: Qxy (2θ) integrated over a β range | β 0 … β_max inside S5 window (or the patch's low level) |
| gid map | H: Qxy over each Qz level; V: Qz (Bragg rod) over the peak's Qxy ± FWHM | from peak finder (`peaks.py`) |
| gisaxs | H band at the **Yoneda** row (α_f = α_c of the subphase), V band at Qy = 0 | α_c from Qc field (0.0217 default) |
| burn | as the underlying kind, same range on every frame (trend-ready) | — |

**F59 axes:** β, β − α, α_f, Qz, Qxy offered on the V cut of any frame;
"β − α" and "α_f" need α per frame (already known). Q-IMG-12 asks which
of these the users need first.

- Cut settings are sticky per kind (§2.2).
- The cut overlay survives the movie: the same band on each frame, and
  the profile updates live.

Size: **L** (widget, geometry unification, defaults); geometry alone
**M**.

### 2.6 Other visual analysis (F71)

| Feature | What | Default | Size |
|---|---|---|---|
| Difference from first frame | frame − frame₀ (per monitor), diverging map centred on 0 (e.g. `RdBu_r`), shared symmetric limits | on for burn kinds as a second mode | S |
| Ratio to first frame | frame / frame₀ where frame₀ > floor | off | S |
| Projections | **mean**, **sum**, **max**, **std** over the selection (or over a range of the movie); "Sum All" becomes this, with its true name, and no longer requires equal Qz for max/std | mean | S |
| Hot/dead pixel overlay | marks pixels flagged by `removeBadPix`, negatives, and pixels hot in more than 50 % of frames | off; on for dark frames | S |
| Mask overlay | detector gaps (200K 17-px gap later, F63), S5/footprint window for GID (`pinhole.py`), direct-beam box | off | S–M |
| Beam marks | direct-beam position (DB Pos), expected specular position from Qz, horizon (β = 0), Yoneda (GISAXS) | on for ref/gisaxs | S |
| Cursor readout | pixel (col,row) · 2θ, β · Qxy, Qz · counts and per-monitor value · **for the tile under the cursor** | always | S |
| Frame metadata strip | scan, point, Qz/2θ, time, absorber, Monc, exposure, kind | always | S |
| Integral vs frame | small trace of ROI sum (or total counts) vs frame index with the current frame marked; doubles as a burn preview | on in movie | M |

### 2.7 Summary of requirements

| Id | Requirement | Exists today | Size |
|---|---|---|---|
| K1 | Scan kind per frame (incl. burn's underlying kind, direct, dark) | series kinds only | S |
| M1 | Non-blocking movie with full controls | blocking loop | M |
| M2 | Sticky zoom across frames and settings | no | M |
| M3 | Metadata labels (point, Qz/2θ, time, absorber) | list text only | S |
| M4 | Shared / per-frame / locked colour scale | first-frame limits | S |
| M5 | Select All → movie; ≤ 6 tiles | 10 tiles | S |
| M6 | Sampled (default 4) and first-n modes | first 10 | S |
| M7 | GID movie on a common 2θ axis, zoom fixed in angle (real peaks still, junk moving); pixel view as the switch (owner 2026-11-23) | pixels only, zoom lost | M (needs X2) |
| P1–P4 | Sticky display preferences (global, per kind, per SPEC), reset, no hidden Axes changes | none | M |
| C1 | Robust limits with masks | max/min of first frame | S–M |
| C2 | Log with floor (LogNorm) | broken by negative pixels | S |
| C3 | Asinh option | no | S |
| C4 | Defaults by kind | no | S |
| C5 | Colour bar with units; one unit for image, cuts, ROI | unlabelled, silent change | S |
| C6 | Perceptually uniform maps; remove `spectral` | jet; invalid entry | S |
| C7 | Nearest interpolation for raw frames | bicubic | S |
| R1–R6 | ROI close-up with outlines, profiles, numbers, cues | static strip, burned borders | M |
| X1 | One cut interface on every image (draw + type) | typed only, Pilatus tab | L |
| X2 | One per-pixel geometry for axes and cuts (P6, P38) | two geometries | M |
| X3 | Cut defaults by kind; F59 axes and messages | blind defaults | M |
| V1 | Difference/ratio, projections, overlays, readout, integral trace | partial ("Sum All") | M |
| W1 | `ImageView` widget shared by views A–F; `display.py` core | copy-pasted blocks | L |
| B1 | Fix wrong cursor values (tiles, ROI close-up) | defects | S |
| G1 | Cache GID products per axes kind (3 s → < 1 s per redraw) | **done 2026-11-23** (test-speed session): the Q regridding kept per map, keyed on its content (`MainWindow.gidProducts`); NX 11 + 12 redraws 1.0–1.4 → 0.30–0.35 s on a 4-CPU container; `tests/test_gid_redraw.py` | S |

Suggested order: W1 skeleton + B1 + C1/C2/C5/C6/C7 → M1–M6 → P1–P4 →
R1–R6 → X2 → X1/X3 → V1. Defects B1, C2 (NaN log), the `spectral` entry
and the 2 px box mismatch could be fixed in phase 1b as single-defect
commits.

### 2.8 Tests to plan (for `docs/TESTING.md`)

- `display.limits` on NX frames: vmax below the direct-beam maximum and
  above the reflected-beam peak. No NaN with negative pixels.
- `display.sample(41, 4) == [0, 13, 27, 40]`; never more than 6 tiles
  (GUI, Select All on scan 11).
- Sticky zoom: set the view, step the movie, toggle log, change CMap →
  the view is unchanged.
- Movie: does not block (the event loop runs between frames); the Axes
  box is unchanged after playing.
- Cursor readout equals `data[row, col]` of the tile under the cursor.
- ROI boxes: drawn rectangles equal `sumROI` boxes (invariant).
- Cut band ↔ typed range round trip; cut in angle equals cut in pixel
  through the shared geometry.
- Legacy export fixtures untouched (display only).

---

## Appendix: how the measurements were made

- Offscreen Qt with `LSS_READER_SELECTION_DELAY_MS=0` and temporary
  `LSS_READER_PREFS` and `LSS_READER_LOG_DIR`. `w.directory` was set to a
  temporary folder after `openSpecFile`.
- Selection with `tests/sweep.py` `_select_scans`/`_select_images`, then
  `flushPendingSelection`.
- Timings come from `time.perf_counter` around the handler plus
  `processEvents`, single runs or a median of 5. Profiles with `cProfile`.
- Screenshots are `w.grab()` of a 1600 × 1000 window. They were not
  committed; `tests/tools/gui_screens.py` is the place for them.
