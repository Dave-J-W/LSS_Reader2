# Study A: the reflectivity join guard

*2026-11-24. The owner asked for a full study before deciding (plan:
`docs/studies/2026-11-24_two_decisions_plan.md`). Every number here was
measured by `python tests/tools/ref_guard_study.py`. That takes 51 s on 4
CPUs, and two runs give byte-identical figures and tables. All the
numbers are in `data_summary.md`; this page interprets them. It is
synthetic data except A8, which uses the public NX school data.*

**The decision.** Where two scans join, the factor is fitted with one
polynomial in ln(R/R_F) through both scans. The guard tries curves of
rising order and narrowing windows, and accepts the first whose χ²
p-value is at least p₀. Today p₀ = 0.3.

**The answer in one line.** Keep p₀ = 0.3: it is the best trade-off of
the choices tested, and real data are not needed to decide this.
p₀ = 0.5 is a little better on the biased joins, but it was not in the
robustness map; it would need its own check.

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
| **p₀ 0.3 (today)** | **0.24** | **1.02** | **1.00** | **0.65 / 0.93** |
| p₀ 0.5 | 0.16 | 1.00 | 1.03 | — |
| p₀ 0.1 | 0.37 | 1.00 | 0.95 | 0.64 / 0.93 |
| p₀ 0.01 | 0.52 | 0.92 | 0.92 | 0.64 / 0.94 |
| guard off (order 4, ±2) | 0.33 | **0.47** | 0.92 | 0.84 / 0.98 |
| model average (AICc) | 0.59 | 0.83 | 0.92 | 0.64 / 0.94 |
| legacy (spline ratio) | 0.29 | **14** | 1.47 | 0.58 / 0.84 |

*Figures:* A2 (pull histograms and QQ plots), A3 (noise-free bias), A4
(which curve the guard picks), A5 (the decision curve), A6 (coverage).

What this shows:

- **Today's guard is the only choice whose error bars are right
  everywhere.** At the smooth join its pull SD is 1.00, and at the biased
  joins about 1.0.
- **The guard off is too cautious at fringes.** Its pull SDs are 0.09–0.32
  there: the error bars are about three times too big, because a stiff
  curve fits a fringe badly and the error is inflated by √(χ²/dof).
- **The legacy spline ratio has untrustworthy error bars.** Its pull SD
  is 135 on the staggered join.
- **Stricter guards (higher p₀) mean less bias.** The trade-off is in A5.
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

**p₀ 0.3 has the smallest error criterion in all 12 cells.** Its RMS of
(pull mean, pull SD − 1) is 0.06–0.17. It wins 79–100 % of bootstrap
resamples, and its pull SD stays at 0.97–1.07. The guard off reaches an
RMS of 1.0 at 3 points per fringe.

**Not yet done from the plan, with the expected effect:**
- **R covers one design only:** coinciding grids, one join at Qz ≈ 0.2,
  a 150 Å film. There are no staggered grids in R.
- **There is no background-box noise and no slit change at a join** in
  the generator.

Neither is likely to reverse the order of the choices. Background noise
adds scatter that the χ² test sees like any other; a slit change is P29,
handled by the known-ratio guard, not by this one. Both would firm up
the evidence. The data already allow a check at p₀ 0.5, which A5 shows
is close, so R should get that cell next.

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

- **Keep p₀ = 0.3.** It is the only choice with right-sized error bars at
  smooth and fringed joins alike (pull SD ≈ 1.0). It has the smallest
  error criterion across the robustness map, and it is today's default,
  so nothing changes.
- **What could change it:**
  1. **p₀ 0.5.** A5 shows less bias (0.16 against 0.24) for a slightly
     wide smooth join (1.03). The next step is adding it to R.
  2. **A staggered-grid robustness map.**
  3. **The owner's real series (hand-off 08)**, if it shows joins where
     the foil ratio and the fit disagree beyond their errors.
- **Not recommended:**
  - p₀ 0.01: more bias, with no gain at the smooth join;
  - the guard off: error bars three times too big at fringes;
  - model averaging: the most bias;
  - the legacy fit: wrong error bars.

---

**Figures, in the order to look at them:**
1. **A5**, the decision curve: today's guard is the large dot.
2. **A1**, replicates and their fits: what the guard picks, for a smooth,
   a fringed and a staggered join.
3. **R_winner**, the robustness map.
4. **A2**, the pulls; **A7** and **A7b**, what it costs.

*C47 in `docs/COMPARISONS.md`. Tool: `tests/tools/ref_guard_study.py`, a
Tools menu item.*
