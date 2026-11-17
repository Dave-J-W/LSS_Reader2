# CCD (moving-table) geometry, kept as a precedent for the Pilatus 1M

The Bruker/Apex CCD support is being removed (owner, D8 and F38: the
detector is defunct). The owner asked that its geometry be kept as a
precedent, because the old CCD sat on a moving table, as the Pilatus 1M
does now, rather than on the detector arm that carries the 100K/200K.
This file records what the removed code did, read from `mainwindow.py` at
commit `39f0f2b` (functions `ccdSelectedScanChanged`, `updateCcdPlotData`,
`updateCcdCutData`, `refQzListSelectionChanged` Bruker branch,
`TwoDDetector.plotHint/plotVint` Bruker branches). It was never run in this
repository (no `.sfrm` sample data); nothing here is verified.

## Quantities

| Symbol | Source | Meaning |
|---|---|---|
| p = 0.060 mm | hard-coded | CCD pixel size |
| (X₀, Y₀) | SPEC `#B1`/`#B2` `DBPos` (or typed) | direct-beam pixel with the table at its reference position |
| (X_off, Y_off) | SPEC (`ccdX_off`, `ccdY_off`) or typed, mm | table offset from the reference position; converted to pixels as `int(off / p)` |
| D | SPEC `S2D_Dist` (or typed), mm | sample–detector distance |
| α | from the frame's Q_z: asin(Q_z λ / 4π) | incident angle |
| g_l2 | SPEC `#G0` | arm length used for the sample-height shift |
| sh | −g_l2 · tan α, mm | vertical shift of the reflected beam at the sample |

## Image axes (beam *moves* on the image as the table offset changes)

With x₀ = X₀ − X_off/p and y₀ = Y₀ − Y_off/p (pixels):

    2θ  (deg) = (x − x₀) · p / D · 180/π
    β   (deg) = ((y₀ − y) · p − sh) / D · 180/π
    Q_xy      = (4π/λ) · sin( (x − x₀) · p / D / 2 )
    Q_z       = (2π/λ) · ( sin( ((y₀ − y) · p − sh) / D ) + sin α )

Note the small-angle form (pixel × size / distance, no arctan) and the
image row axis increasing downward (y₀ − y).

## Reflected-beam position for reflectivity

    x_c = X − int( (D + g_l2) · (tan 2θ_arm − tan 2θ_B) / p )
    y_c = Y − int( (α · D + sh) / p )

where 2θ_arm is the arm angle (`Two_Thet`) and 2θ_B = 2 asin(λ · 1.9236 / 4π)
(a fixed Bragg reflection, apparently of the analyser or a reference;
the constant 1.9236 Å⁻¹ also appears in `#G0`). The background ROI offset
was converted from degrees to pixels with D·π/180/p.

## Relevance to the Pilatus 1M (F38)

- *Tracked* mode (table follows the beam): x₀, y₀ stay close to the
  recorded direct-beam pixel; the Pilatus 100K/200K formulas apply with the
  1M's pixel size (0.172 mm) and the table offset added to x₀, y₀.
- *Fixed* mode (detector stays, beam moves): the formulas above, with
  p = 0.172 mm and the beam position computed from α and sh as for the CCD.
- The CCD code used small-angle axes; the Pilatus line cuts use arctan
  (PHYSICS_ISSUES P6). A 1M implementation should use exact angles and be
  tested against data in both modes.
