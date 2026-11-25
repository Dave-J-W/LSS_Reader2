# Does a reflectivity join need coincident Qz points? (synthetic known truth)

The owner's non-cloud agent, 2026-11-24, at the owner's question: "Does all the analysis so far suggest always
having at least one overlapping/coincident point? Is one enough, such that different x-spacing for each scan
is more feasible?" This study follows `docs/studies/ref_patch_real/` (C56), whose real joins were split into
halves that share no Qz.

**Synthetic, so every number here is regenerable:**

    python tests/tools/coincidence_synth.py --out docs/studies/coincident_points --trials 200

That takes about 10 s with 6 workers. It writes `stats.csv` (per curve, join Qz, geometry and method, plus the
pooled rows `curve = all`), `numbers.json` and figures C1–C3.

## The test

- **Curves** (`tests/synthetic/xrr.py`): bare water, DPPC and a 100 Å film on water. Each is smeared by the
  measured resolution, FWHM 8.9 × 10⁻⁴ Å⁻¹ (`docs/studies/qz_resolution/`).
- **Joins:** at Qz 0.05, 0.15 and 0.30 Å⁻¹, with steps of 0.002, 0.005 and 0.01. The film's fringe period is
  0.063 Å⁻¹, so at 0.30 there are 6 points per fringe.
- **Scans:** scan a has 1000 counts per point at the join. Scan b has 10× the counts and is reported × 1/10,
  so the truth is f = 10, as after a foil change. Errors are Poisson.
- **Geometries:** 12 ways of meeting at the join:
  - no overlap;
  - k coincident points and nothing else (k = 1, 2, 3, 5, 8);
  - a staggered overlap, b's grid shifted half a step, n points of each scan and no shared Qz (n = 1, 2, 4, 8);
  - b on a 1.5× coarser grid over a 5-point overlap, with no shared point or with one.
- **Methods:** the reader's own code, unchanged:
  - `legacy` (`stitching.fitted_factor`);
  - `interp` (spline ratio);
  - `coincident` (ratio at shared Qz);
  - the joint fit at today's default (guard p 0.7);
  - the joint fit with the guard off (order 4, 2 points either side);
  - the joint fit at order 2 (2 points either side, no guard).
- **Trials:** 200 joins per curve, Qz and geometry, so 1800 per geometry and 21,600 in all.
- **Scores:** bias of ln f with its standard error, the median stated error, pull SD (1 means the stated error
  is honest), the share within 1σ (68 % ideal) and the share with an answer.

## The answer

**Coincident Qz are not needed. An overlap is: at least 4 points from each scan within it.** Different
spacing for each scan is fine.

Pooled over the 9 joins (figure C2), for the reader's default joint fit:

| geometry | answered | bias of f (%) ± SE | median error of f | pull SD | within 1σ |
|---|---|---|---|---|---|
| no overlap | 0 | — | — | — | — |
| 1 coincident only | **0** | — | — | — | — |
| 2 coincident | 1.00 | −0.25 ± 0.06 | 2.25 % | 0.94 | 73 % |
| 3 coincident | 1.00 | −0.03 ± 0.05 | 2.01 % | 0.97 | 68 % |
| 5 coincident | 1.00 | −0.01 ± 0.04 | 1.70 % | 0.96 | 70 % |
| 8 coincident | 1.00 | −0.03 ± 0.04 | 1.51 % | 1.01 | 69 % |
| staggered 2+2, none shared | 1.00 | −0.10 ± 0.05 | 2.03 % | 0.93 | 73 % |
| staggered 4+4, none shared | 1.00 | −0.02 ± 0.04 | 1.72 % | 1.02 | 67 % |
| staggered 8+8, none shared | 1.00 | +0.03 ± 0.04 | 1.46 % | 1.00 | 67 % |
| b step 1.5×, none shared | 1.00 | −0.10 ± 0.05 | 1.89 % | 1.05 | 66 % |
| b step 1.5×, 1 shared | 1.00 | −0.02 ± 0.04 | 1.73 % | 1.00 | 68 % |

- **Shared Qz buy nothing.** At the same number of points per scan, staggered and coincident overlaps give the
  same precision: 4+4 staggered 1.72 % against 5 coincident 1.70 %; 8+8 1.46 % against 1.51 %. Both are
  unbiased within 0.1 % and honest, with pull SD 0.96–1.02. Join by join (figure C3), the default's pull SD
  is 0.90–1.07 at every geometry with ≥ 3 points per scan, on every curve.
- **One shared point is an answer, not a good one.** Only the ratio methods answer, at a median error of
  3.3 %: twice the 1.5–1.7 % of a 5- to 8-point overlap. The real joins give the same ratio, 2.1× (below). The default joint fit refuses a lone shared point.
  Its ladder starts at order 4, and 2 + 2 points (one shared) leave no degrees of freedom. A fixed order 2
  does answer: 2.9 %, pull SD 0.89.
- **Two points from each scan** work on smooth curves. They fail on a fast fringe: on the film at Qz 0.30,
  2 coincident points give the default a bias of −2.0 % ± 0.17 %, 0.6 of its stated error, with pull SD 0.81.
  This one cell gives the pooled −0.25 %. At 3 points or more, the bias is gone.
- **The legacy factor's error is wrong at small overlaps.** Its pull SD is 4.4–106 with 2 coincident points,
  11–336 with staggered 2+2, and 2.2–6.2 with 3 coincident points. Its error bars are therefore up to
  hundreds of times too small. It is honest only with 1 point (where it equals the coincident ratio) and is
  1.1–1.3 at 8 points.
- **Fixed low orders cannot follow a fringe.** With the guard off, or at order 2, the film at Qz 0.30 is
  biased by 2–14 %. Their errors are then inflated by χ² to 5–10× the scatter (pull SD 0.1–0.3), so they are
  honest but useless. The guard's ladder is what keeps the default unbiased there.

## On the real joins (C56's 1832 joins, by the number of shared Qz)

Measured, from the private survey of `docs/studies/ref_patch_real/`. Two things are compared at each join:
the coincident ratio's error against the default joint fit's error, and the difference between the two
factors (|Δ| in %, then the robust SD of Δ/σ).

| shared Qz | joins | coincident error / joint error | median \|Δ\| | 90th percentile \|Δ\| | robust SD of Δ/σ |
|---|---|---|---|---|---|
| 0 | 43 | — | — | — | — |
| 1 | 738 | 2.13 | 0.53 % | 6.8 % | 0.93 |
| 2 | 125 | 1.69 | 0.39 % | 2.0 % | 0.63 |
| 3–5 | 874 | 1.27 | 0.09 % | — | 0.18 |
| 6 or more | 52 | 1.21 | 0.14 % | — | 0.05 |

At 3 or more shared points the two methods use the same points and agree closely. At 1 point they disagree
as their errors say they should (robust SD 0.93): the lone point is unbiased, only imprecise.

## For planning scans

- Overlap each pair of scans by **at least 4 points of each scan**, or 3 on smooth curves. The points need not
  coincide. A grid that is coarser at high Qz is fine.
- On a fast fringe, aim for 6 or more points per fringe within the overlap (C36's sampling rule).
- A shared Qz is worth keeping only as a model-free cross-check of the fitted factor (`coincident_factor`). It
  is not needed for accuracy.

## Not shown, and why

- **Background, monitor noise and slit faults:** left out. The gauntlet (`tests/tools/ref_patch_gauntlet.py`,
  C36) covers them, and they do not depend on whether the grids coincide.
- **Joins below Qz 0.05**, where R/R_F changes fastest near the edge: not tried here. The real data (C56)
  cover them.
- **Real staggered grids:** C56's interleaved splits of 1091 real scans share no Qz. The default had bias
  +0.10 % [−0.10, +0.32] and pull SD 1.24 there; the excess comes from the guard on real curves, not from
  the grid.
