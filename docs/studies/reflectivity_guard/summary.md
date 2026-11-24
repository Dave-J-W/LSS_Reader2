# Study A: the reflectivity join guard

*2026-11-24. The owner asked for a full study before deciding (plan:
`docs/studies/2026-11-24_two_decisions_plan.md`). Every number here was
measured by `python tests/tools/ref_guard_study.py`. That takes 72 s on 4
CPUs, and two runs give byte-identical figures and tables. All the
numbers are in `data_summary.md`; this page interprets them. It is
synthetic data except A8, which uses the public NX school data.*

**The decision.** Where two scans join, the factor is fitted with one
polynomial in ln(R/R_F) through both scans. The guard tries curves of
rising order and narrowing windows, and accepts the first whose χ²
p-value is at least p₀. Today p₀ = 0.3.

**The answer in one line.** Raise p₀ from 0.3 to **0.7**.
- **The gain:** the bias at the hard joins (fringes or short overlaps)
  halves, from 0.24 to 0.12 errors.
- **The cost:** error bars at smooth joins become about 4 % too small
  (pull SD 1.00 → 1.04).
- **The evidence:** p₀ 0.5–0.9 beat 0.3 in 23 of the 24 cells of the
  two robustness maps, on coinciding and staggered grids.
- **Small stakes:** a structural fit of the curve moves by about
  0.001 Å whatever the choice.
- **No real data needed** to decide.

*How this answer changed overnight.* The first version of this page said
"keep 0.3", because 0.3 won every cell of a map whose strictest setting
was 0.3. Adding p₀ 0.5 to the map made 0.5 win every cell. Extending to
0.7 and 0.9 found where the gain stops: at about 0.7.

## 1. What each choice does on data with known truth

Six joins, 400 replicates each, on the gauntlet's own seeds. C45 came
back exactly, all 180 values.
- **Five biased joins:** three with fringes at the join (layer_dppc j3,
  layer_film150 j2, scans_5 j2), one with six overlap points
  (overlap_6 j1) and one staggered grid (overlap_3_staggered j3).
- **One smooth join:** the first join of the covariance study.

The pull is (δ̂ − δ)/σ̂. Ideally its mean is 0, its SD is 1, and the
coverage is 68 % within ±1 and 95 % within ±2.

| Choice | Biased joins: mean \|pull mean\| | Biased joins: mean pull SD | Smooth join: pull SD (2000 replicates) | Coverage ±1 / ±2 (pooled) |
|---|---|---|---|---|
| p₀ 0.3 (today) | 0.24 | 1.02 | 1.00 | 0.65 / 0.93 |
| p₀ 0.5 | 0.16 | 1.00 | 1.03 | — |
| **p₀ 0.7** | **0.12** | **0.98** | **1.04** | — |
| p₀ 0.9 | 0.10 | 0.97 | 1.04 | — |
| p₀ 0.1 | 0.37 | 1.00 | 0.95 | 0.64 / 0.93 |
| p₀ 0.01 | 0.52 | 0.92 | 0.92 | 0.64 / 0.94 |
| guard off (order 4, ±2) | 0.33 | **0.47** | 0.92 | 0.84 / 0.98 |
| model average (AICc) | 0.59 | 0.83 | 0.92 | 0.64 / 0.94 |
| legacy (spline ratio) | 0.29 | **14** | 1.47 | 0.58 / 0.84 |

*Figures:* A2 (pull histograms and QQ plots), A3 (noise-free bias), A4
(which curve the guard picks), A5 (the decision curve), A6 (coverage).

What this shows:

- **Only the guard at p₀ 0.3 and above keeps error bars near right at
  both kinds of join.** The pull SD is 0.97–1.04. At 0.3 the smooth join
  is exactly 1.00. At 0.7 the hard joins' bias is half as large, and the
  smooth join is 4 % over-confident.
- **The guard off is too cautious at fringes.** Its pull SDs are 0.09–0.32
  there: the error bars are about three times too big, because a stiff
  curve fits a fringe badly and the error is inflated by √(χ²/dof).
- **The legacy spline ratio has untrustworthy error bars.** Its pull SD
  is 135 on the staggered join.
- **Stricter guards (higher p₀) mean less bias, with diminishing
  returns** (A5). From 0.3 to 0.7 the bias halves; from 0.7 to 0.9 it
  barely changes. The smooth join's pull SD rises from 1.00 to 1.04 and
  then stays flat.
- **The bias at the five joins is model bias, not noise** (A3). Even with
  no noise, the fit lands 0.3–1.0 errors off where a fringe crosses the
  join. No polynomial order removes it everywhere.
- **Choosing among curves after seeing the fit does widen the pulls**, by
  +0.08 ± 0.01 at the smooth join, against the same replicates with the
  guard off. But the guard off sits at 0.92 there, below 1, because its
  error is only ever inflated, never shrunk. The two effects nearly
  cancel, and today's guard lands at 1.00.
- **Correction to the record.** C45's "pull SD 1.13" at the smooth join
  was mostly sampling noise of its first 300–400 seeds. Over 2000 seeds
  it is 1.00, and blocks of 400 give 0.94–1.08.
- **Model averaging does not help.** It puts most of the weight on the
  biased order-6 curve (0.92 at layer_dppc j3), so it is the worst on the
  biased joins. It stays a candidate only.

## 2. Is the synthetic data good enough?

**What it has:**
- curves from Parratt's recursion with Névot–Croce roughness
  (`tests/synthetic/xrr.py`): water, a DPPC-like monolayer, films of
  100 and 150 Å;
- NX-like plans and the gauntlet's grids, including staggered ones;
- the owner's monitor model (no Poisson noise, 0.05 %);
- Poisson counting at the beamline's flux and background.

**The robustness map (R)** sweeps what synthetic data cannot pin down:
- fringe sampling, at 3, 4, 6 and 10 points per Kiessig period;
- counts, at flux ×1, ×0.1 and ×0.01;
- four fringe phases at the join.

**Coinciding grids (R).** Strict guards win all 12 cells: p₀ 0.9 in 11
and p₀ 0.7 in 1. The winners' RMS of (pull mean, pull SD − 1) is
0.04–0.10, against 0.06–0.17 for p₀ 0.3, and their pull SD is 0.98–1.05.
Among p₀ 0.5, 0.7 and 0.9 the differences are a few hundredths, within
noise in most cells. The guard off reaches an RMS of 1.0 at 3 points per
fringe.

**Staggered grids (RS, added overnight;** the two scans share no Qz at
the join): p₀ 0.5–0.9 win 11 of 12 cells. p₀ 0.3 wins one, 6 points per
fringe at ×0.01 flux, with an RMS of 0.05 against 0.05. The bootstrap
shares are split (18–94 %), because 0.5, 0.7 and 0.9 are close. The
legacy spline ratio has pull SD 1.9–3.6 on every staggered cell.

**Not yet done from the plan, with the expected effect:**
- **One film and one join position:** both maps use a 150 Å film with
  the join at Qz ≈ 0.2.
- **There is no background-box noise and no slit change at a join** in
  the generator.

Neither is likely to reverse the order of the choices. Background noise
adds scatter that the χ² test sees like any other; a slit change is P29,
handled by the known-ratio guard, not by this one.

## 3. Is real data needed?

**Not for this decision.**
- The ranking of the choices holds over the whole plausible range of
  fringe sampling and counts.
- The choice barely moves what the owner reports (section 4).
- On the real NX school joins, every joint choice picks the same curve
  and the same factor (A8).

Real data would confirm the result, not change it. The right set is
many joins with known foil ratios: the owner's series for hand-off 08,
DATA_NEEDS row 1, "not soon".

**What the public data already show (A8, NX 6–9):**

| Join | Joint fit | Foil ratio | Within |
|---|---|---|---|
| 1 | 0.02298 ± 0.00010 | 0.02311 ± 1.55 % | 0.34σ |
| 2 | 0.06447 ± 0.00040 | 0.06555 ± 0.94 % | 1.48σ |
| 3 | 0.10369 ± 0.00041 | 0.10386 ± 0.75 % | 0.19σ |

At joins 2 and 3 the slits change (Monc/Monp ×4.35 and ×1.32), so there
the foil ratio is not an independent check. All the joint choices give
identical factors on these four scans, so this data cannot separate the
choices.

## 4. What it costs to be wrong

Very little in what the owner reports. A downstream structural fit of
the patched curves (A7, 200 seeds, full covariance) gives the following.

| Case | Thickness SD, every joint choice | Roughness SD | Legacy |
|---|---|---|---|
| 25 Å film, NX-like plan | 0.014 Å | 0.0032–0.0033 Å | 0.0146 Å; thickness pull SD 1.13 |
| 150 Å film, a fringe at the join (A7b) | 0.024 Å | 0.0063–0.0066 Å | roughness 0.0069 Å |

The join choices differ by about 0.001 Å or less, because the structural
fit uses all the points and the full covariance. The choice matters for
**the honesty of the error bars at each join**, which shows when a curve
is compared point by point. It hardly matters for the fitted structure.

## 5. Recommendation

**Raise p₀ to 0.7.**
- **Why:**
  - It halves the bias where a fringe or a short overlap fools the curve.
  - It wins the robustness maps on both kinds of grid.
  - It costs 4 % over-confidence at smooth joins.
  - p₀ 0.9 is no better in any way that shows, and it rejects nine in ten
    good fits, so 0.7 is the setting.
- **What the change touches:** one constant, `patching.GUARD_P`. It
  would get an OUTPUT_DECISIONS row: NX school's joins keep their curve
  and factor (A8 shows every choice picking order 4, ±2 there). The
  gauntlet's committed products would be rerun, and the re-pinned
  numbers named one by one.
- **If the owner prefers exact error bars at smooth joins to less bias
  at fringed ones,** keeping 0.3 is defensible. The difference in
  anything downstream is about 0.001 Å.
- **What could change it:**
  - a design where 0.7's over-confidence grows (a third map: other film
    thicknesses, join positions);
  - the owner's real series (hand-off 08), if fit and foil ratio
    disagree.
- **Not recommended:**
  - p₀ 0.01: more bias, with no gain;
  - the guard off: error bars three times too big at fringes;
  - model averaging: the most bias;
  - the legacy fit: wrong error bars, worst on staggered grids.

---

**Figures, in the order to look at them:**
1. **A5**, the decision curve: today's guard is the large dot.
2. **A1**, replicates and their fits: what the guard picks, for a smooth,
   a fringed and a staggered join.
3. **R_winner** and **RS_winner**, the robustness maps on coinciding
   and staggered grids.
4. **A2**, the pulls; **A7** and **A7b**, what it costs.

*C47 in `docs/COMPARISONS.md`. Tool: `tests/tools/ref_guard_study.py`, a
Tools menu item.*
