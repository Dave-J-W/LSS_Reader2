# Reflectivity patching: joint fit, prior knowledge and the correlated error

Written 2026-11-22 by a subagent for the main session, at the owner's
request. Analysis only: no repository code was changed. The prototype
code and every script named below are in the subagent's scratchpad (not
committed); the numbers can be regenerated from the descriptions. "Measured"
means a script was run and the number is its output; "reasoned" means
argued, not run.

## 1. The question (owner, 2026-11-22)

> Employ a subagent to think deeply on the patching method and whether
> there is a way to avoid the correlated error by doing joint fitting on
> both scans in the ref patch and using the prior knowledge. The curvature
> matching up across the patch is one constraint. A quadratic or 4th order
> model should be adequate for non fresnel normed data patches. In any
> case, make reusable code for calculating uncertainty and prepare for
> later work by a third agent where they compare methods with a larger
> dataset.

Short answers:

| Question | Answer | How known |
|---|---|---|
| Does a joint fit of both scans remove the P1 bias? | Yes, to < 0.02 % in every case tried, including the 1.3 % case of `test_stitching.py` (1.4200 recovered; legacy 1.4013). | measured |
| Is it more precise? | Yes: the factor's scatter falls 20–30 % against the interpolation estimator (hand-off §3.2), by using the non-coinciding overlap points and 4 points either side. NX: last scan's scale uncertainty 1.03 % → 0.75 %. | measured (synthetic, NX) |
| Quadratic or 4th order? | 4th order. A quadratic is unbiased only on the overlap alone; with points either side it is biased by up to 5 % near fringes and at high Qz, raw or R/R_F. Order 4 is unbiased (< 0.1 %) up to 4 points either side. | measured |
| Curvature matching? | A shared polynomial already makes value, slope and curvature (all derivatives) match across the join; it is the strongest form of the owner's constraint. Matching only value, slope and curvature at one junction (separate cubic/quartic terms per scan) is unbiased but 1.5× noisier. | measured |
| Does the known absorber ratio help? | Little at NX-like counts (−8 % on the last scan's scale error), a lot at low counts (−50 %). Only where Monc/Monp shows no slit change; a 5 % P29 disagreement cannot be detected from the data at low counts, so the monitor guard is essential. On the owner's 1041 joins the ratio is more precise than the patch at only 10 % of joins. | measured (synthetic; owner's joins table) |
| Can the correlated error be avoided? | **No.** It is the real uncertainty of each scan's level, shared by all its points and by every later scan. It can be made smaller (more information) and must be reported as a covariance; what can be avoided is treating it as independent (P4), not inheriting it, and the P1 bias. | reasoned; consequences measured |
| Global fit of all joins at once vs join by join? | Identical when each point is used in one join (the usual case), as long as the chain inherits uncertainties (hand-off §3.4). A global fit is better only when scans overlap more than their neighbour, or with a correlated foil prior. A global spline over the whole curve was biased (+0.1 to +0.5 %). | measured |

## 2. The current method and its flaws

Legacy (`lss_core/stitching.py`, `_fit_factor`): the new scan b is
interpolated with a cubic spline **in linear intensity** at the existing
data's overlap points; the ratios r_i = y_a,i / spline_b(q_i) are averaged
with weights from the total errors, `curve_fit(..., absolute_sigma=False)`;
the factor error is folded into the new scan's points
(`σ² = σ²f² + y²σ_f²/f²`); the next join fits against the merged data.
The corrected chain of hand-off 19 §3.2 keeps the estimator (spline ratio,
weighted mean) but fits against counting errors, `absolute_sigma=True`,
inflate-only, and carries Σ by the §3.4 recursion.

| Flaw | Size | How known |
|---|---|---|
| P1: spline in linear intensity reads high on a falling curve, factor low | Scales with the change of ln R over one step of scan b, Δ = Δq_b·\|d ln R/dq\|: −0.03 % at Δ = 0.27, −0.3 % at 0.5, −2.1 % at 0.95 (table 2). NX grids have Δ ≈ 0.2–0.3: P1 is ≈ 0.01–0.03 % there, negligible against 0.4–0.9 % counting errors. A cubic spline in **log** intensity is 10× smaller; the joint fit removes it. | measured (`p1scan.py`, noise-free Parratt curve) |
| Legacy factor error from `absolute_sigma=False` | Pull SD of the first factor 1.49 (NX grid), 2.2 (staggered), 2.9 (coinciding-only): errors too small by those factors when the 3–6 overlap ratios happen to agree. | measured (`mc1.py`) |
| P4: no inheritance; folded into the diagonal | Scale of scan m against its error: pull SD 1.5, 2.3, 4.0, 2.0 for scans 2–5 (legacy); with the corrected estimator but no inheritance 1.0, 1.6, 2.6, 1.4. With Σ (§3.4): 0.97–1.01. | measured (`mc2.py`) |
| Information thrown away | The spline ratio uses only scan a's overlap points; scan b's points in the overlap and points either side carry information about the curve's shape that the spline does not use. | reasoned; gain measured (table 1) |
| Low counts | Ratios of noisy values weighted by observed errors are biased: interpolation −3 % to −12 % at ≈ 2×10³ counts per scan start. | measured (`mc5.py`) |

## 3. The joint-fit method

### 3.1 Model and likelihood (one join)

Scan a (data so far, on the anchor's scale) and scan b (new). Window: the
overlap [min q_b, max q_a] plus `n_ext` points of a below it and of b
above it. With x = q (or ln q), u = (x − x_mid)/x_half ∈ [−1, 1], and a
baseline B(q) = ln R_F(q + q_off) (`space='rrf'`) or 0 (`'raw'`):

    μ_a(q) = exp( B(q) + Σ_{k=0..p} c_k u^k )
    μ_b(q) = μ_a(q) · exp(−δ),        δ = ln f   (f multiplies scan b, as today)

One curve for both scans: the polynomial is shared, so value, slope and
curvature agree across the whole window (the owner's constraint, in its
strongest form). Parameters θ = (c_0 … c_p, δ).

Likelihood (recommended, `likelihood='poisson'`): Gaussian in y with the
counting variance rescaled to the model, Var_i = σ_i²·μ_i/y_i (Poisson-like:
equal to σ_i² at high counts, unbiased at low counts; keeps zero and
negative net points):

    χ²(θ) = Σ_i (y_i − μ_i)² / Var_i  [+ (δ − δ_0)² / s_0²   with a prior]

solved by Gauss–Newton from the closed-form log-space solution
(`likelihood='log'`: ln y_i ~ N(ln μ_i, (σ_i/y_i)²), weighted linear least
squares; adequate above ~10⁴ counts, biased +2 % to +10 % at ~10³).

Results: δ̂, its counting error σ_δ = √[(JᵀV⁻¹J + P)⁻¹]_δδ, χ²/dof
(dof = n − p − 2), and the reported error σ_δ·max(1, √(χ²/dof)) (the
hand-off §3.2 inflate-only rule). For chaining: the sensitivity of δ̂ to
a log shift of every point, h_i = ∂δ̂/∂ln y_i (the δ row of the hat
matrix); summed over the points of each earlier scan it gives the hand-off's
a_m exactly (Σ_j a_m[j] = 1 because the intercept absorbs a common shift).
This replaces the hand-off's "mean of the W rows of overlap1" by the exact
weights.

### 3.2 Order and window (bias–variance)

Measured on 300 synthetic data sets (table 1): order 2 is unbiased only
on the overlap alone (`n_ext = 0`); every extension biases it (+2.6 % at
the low-Qz join and −5 % at the high-Qz join with 4 points either side,
pull SD 0.3), in raw and R/R_F alike near a fringe. Order 4 is unbiased
to within 0.1 % (≤ 0.2 σ) up to `n_ext = 4` everywhere and up to 6–8 in
R/R_F except near the first minimum. Order 3 with 2 points either side is
nearly as good. R/R_F helps only order 2 at low Qz (the Fresnel decay is
taken out); for order 4 raw and R/R_F agree except at the join nearest
Q_c with wide windows (raw o4 e8: −1.7 %).

Choice: **order 4, R/R_F, 4 points either side** as a fixed default.
A data-driven search (widen while χ² and a nested-estimator (Hausman)
test pass) was tried and is not better: it chooses the widest window most
of the time and its post-selection pulls are 1.05–1.08, RMSE slightly
worse (table 5). Recommended instead: a **guard**, not a search: if the
fit's χ² has p < 0.01, step down to 2 points either side, then to the
overlap alone with order 2, and flag the join. On NX join 8→9 the guard
would act at `n_ext = 6` (χ²/dof 60, the window then reaches into the
first fringe) and not at 4 (χ²/dof 1.4).

A minimum: n ≥ p + 4 points (dof ≥ 2) and at least 2 points of each scan.

### 3.3 Prior: the known absorber ratio

Prior on δ: δ_0 = ln(T(n_a)/T(n_b)) from `Foils.step`, s_0 its relative
error. Single join: MAP = inverse-variance combination,
δ_post = (δ̂/σ_δ² + δ_0/s_0²)/(1/σ_δ² + 1/s_0²). Several joins: the foil
errors are shared between joins that change the same foil, so the prior
on the step vector is correlated:

    C_prior = S ( μ² D diag(σ_k²) Dᵀ + 0.005² I ) S

D the signed bit differences of each join (rows), σ_k the run-to-run foil
spreads (`CAL_FOILS_RUN_UM`), μ the attenuation per µm, S = diag(3.2 at
overlaps Q_z ≥ 0.25). Its diagonal reproduces `Foils.step` exactly. NX
scans 6–9: prior errors 1.55, 0.94, 0.75 %, correlations −0.31, +0.11,
−0.18. Combination: δ_post = (C_d⁻¹ + C_p⁻¹)⁻¹ (C_d⁻¹δ̂ + C_p⁻¹δ_0), the
prior marginalised (its rows and columns removed) at joins where it is
not used.

**Guard** (measured necessary, table 4): use the prior at a join only if
(1) Monc/Monp across the join is within 3 % of 1 (`monitor_change`, as
`patch_choice` already does), and (2) |z| ≤ 3 with
z = (δ̂ − δ_0)/√(σ_δ² + s_0²). (1) is the one that matters: at low counts
a 5 % P29-like disagreement gives |z| ≈ 1.5 and passes (2), biasing the
result by 3.4 %. A wrong prior at one join also leaks into its
neighbours through the foil correlations (+2.3 % on scan 2 when scan 3's
prior was ×1.5 off and unguarded), so a rejected join's prior must be
marginalised, not just down-weighted.

### 3.4 Chaining and the global fit

Join by join with inheritance (hand-off §3.4): Σ[m, j] = a_m·Σ[:, j],
Σ[m, m] = a_m Σ a_m + σ_δm². With each join fitted against scan m−1's own
points (a_m = e_{m−1}) this is a random walk, Σ_mm = Σ_{k≤m} σ_δk².

Global (all factors at once, one likelihood): parameters φ_m = ln of the
factor that brings scan m to the anchor, one polynomial per join window,
each point in at most one window. When windows are disjoint (they are, for
NX-like scans) the likelihood factorises by join and **the global fit is
the chain**: measured identical to 0.01 % in bias, scatter and pulls
(table 3). A global fit adds something only when (a) a scan overlaps more
than its neighbour (short scans, repeats), (b) a point would be needed by
two joins (a short middle scan), or (c) a correlated prior couples the
joins. A single cubic B-spline of ln(R/R_F) over the whole range with the
factors (knots every 0.01 or 0.02 Å⁻¹) was biased (+0.1 to +0.5 %) and its
pulls were 0.76–0.91: not recommended.

## 4. The correlated error

### 4.1 What it is

The estimate δ̂_m has an error ε_m. Every point of scan m is multiplied by
exp(φ̂_m), φ̂_m = Σ_{k≤m} δ̂_k (simple chain), so every point of scan m,
and of every later scan, carries the same ε's. In log units the stitched
curve's covariance is

    C_log = diag((σ_meas,i / y_i)²) + W Σ Wᵀ        (N × N)
    C     = D C_log D,  D = diag(model intensity)    (linear units)

W (N × K) the region weights (one-hot for unaveraged points), Σ (K × K)
the covariance of the φ̂'s (anchor row and column zero). This is the
hand-off 19 contract exactly; nothing in the joint fit changes its form.

### 4.2 What cannot be avoided, and what can

| | Avoidable? | Why |
|---|---|---|
| A common-mode error per scan | **no** | The data determine each scan's level only through finite overlaps; any estimator (spline, joint fit, global fit, prior, structural model) leaves a variance, and it belongs to the whole scan, not to points. The correlation is information, not a defect: it says that the shape within a scan is known to counting precision while its level is known to σ_δ. |
| Accumulation along the chain | **no** (only reducible) | Scan K's level relative to the anchor is a product of K−1 measured steps. Only an independent measurement of a longer step (the foil prior from n_1 to n_K directly, which the correlated prior contains) or an absolute scale at high Qz would break the walk. Moving the anchor changes Σ but not a downstream fit that has a free overall scale (reasoned). |
| Its size | partly | Joint fit −20 to −30 % on σ_δ; prior −8 % (NX counts) to −50 % (low counts); longer counting or more points in the overlaps (an experiment-design choice). |
| Folding it into the diagonal (P4) | **yes** | Downstream fits become overconfident: slab-fit pull SDs 3–4 even with the inherited Σ on the diagonal, 1.0–1.15 with the covariance (table 6). |
| Not inheriting it | **yes** | §3.4 recursion. |
| Double counting earlier factor errors in the next fit | **yes** | Fit against counting errors (hand-off §3.2). |
| Bias of the level (P1) | **yes** | Joint fit. |
| Bias from a covariance built on measured values (Peelle's pertinent puzzle) | **yes** | Use D = diag(model), or log space (xmodfit already does; D'Agostini 1994). |

The joint fit cannot "avoid the correlated error" because the correlation
is not a by-product of interpolation: with points that coincide exactly
and no interpolation at all, the error of the ratio is still common to the
whole scan.

### 4.3 Two exact equivalences (reasoned; standard results)

1. **Covariance ↔ nuisance scales.** Fitting the stitched curve with
   C_log = diag + WΣWᵀ is, to first order, the same as fitting the
   unscaled scans with one free log scale per scan and a Gaussian penalty
   (φ − φ̂)ᵀΣ⁻¹(φ − φ̂) (the "pull" formulation; Fogli et al. 2002). So
   xmodfit can equally fit per-scan scale parameters; the contract already
   carries what is needed (W identifies the scans).
2. **Free scales.** Σ → ∞ on a scan is a free scale for it: the structural
   model alone then fixes the relative levels. This uses the overlap points
   once; the covariance form with the patch-derived Σ uses the overlap
   points twice (once for φ̂ through the smoothness model, once in the
   structural fit). The double use is measured to be small here (pull SD of
   the slab parameters with the full covariance, table 6), because the
   structural model's information on δ is local to the same few points.
   The foil prior is independent information and can be used either way.

### 4.4 Recommendation for the export (the owner decides)

- Keep the contract of hand-off 19 as is: `sigma_meas` (counting only),
  W, Σ in natural-log units, and the error column = √diag(C). No change of
  schema is needed for the joint fit; Σ is simply smaller and correct.
- Write the points as measured (all points of every scan, scaled by
  exp(φ̂_m), W one-hot), or average only points at coinciding Q_z
  (W 0.5/0.5): no interpolation of data into the output. The legacy chain
  averages an interpolated scan b into scan a's points and discards scan
  b's own overlap points; the corrected output need not.
- Put in `provenance` per join: δ̂, σ_δ (counting), χ²/dof, n_ext, order,
  space, the prior (δ_0, s_0, used or not and why), z; and the foil-only Σ
  (from C_prior) beside the patch Σ, so that a fit can choose.
- Do not fold the factor error into the diagonal of anything that is fed
  to a fit (table 6, row C).

## 5. Synthetic results

Truth: Parratt reflectivity of a single slab on water (d = 25 Å,
SLD 11×10⁻⁶ Å⁻², σ = 3.5 Å, Q_c = 0.0217 Å⁻¹, no absorption), five scans on
the NX school grids (0.0175–0.04 step 0.00125, 0.035–0.1 step 0.0025,
0.09–0.19 step 0.005, 0.17–0.45 step 0.01) plus 0.40–0.60 step 0.01. Each
scan scaled so its first point has 5×10⁵ counts (NX: 4–5×10⁵), Poisson
counts, two Poisson background boxes subtracted (background/signal 0.3
at the last point, as NX scan 9), σ² = S + (B₁+B₂)/4. Grids: `nx` (NX:
3–6 of each overlap's points coincide), `staggered` (scan b shifted by
half of scan a's step: none coincide), `coincide` (scan a's overlap points
that scan b lacks removed). Scripts: `sim.py`, `patchlab.py` (estimators),
`mc1.py` … `mc6.py`. 300 seeds unless stated. Numbers are percentages of
the factor (δ in %); pull = (δ̂ − δ_true)/σ_reported.

**Table 1. One join at a time, NX grid** (bias % / SD % / mean σ % / pull SD), `mc1.py`

| Method | Join 1 (Q 0.035–0.04) | Join 2 (0.09–0.10) | Join 3 (0.17–0.19) | Join 4 (0.40–0.45) |
|---|---|---|---|---|
| legacy (first join only comparable) | +0.03 / 0.59 / 0.54 / **1.49** | | | |
| spline ratio, hand-off §3.2 | +0.03 / 0.59 / 0.64 / 0.96 | −0.03 / 0.50 / 0.54 / 0.96 | −0.00 / 0.33 / 0.36 / 0.96 | −0.11 / 0.91 / 0.99 / 0.94 |
| spline in ln y | +0.04 / 0.59 / 0.64 / 0.96 | −0.02 / 0.50 / 0.54 / 0.96 | +0.00 / 0.33 / 0.36 / 0.96 | −0.11 / 0.91 / 0.99 / 0.94 |
| coinciding points only | +0.04 / 0.74 / 0.83 / 0.93 | −0.04 / 0.63 / 0.72 / 0.94 | +0.01 / 0.43 / 0.48 / 0.96 | −0.11 / 0.91 / 0.99 / 0.94 |
| joint o2, overlap only | +0.06 / 0.59 / 0.65 / 0.95 | −0.01 / 0.50 / 0.54 / 0.95 | +0.01 / 0.33 / 0.36 / 0.94 | −0.05 / 0.91 / 1.06 / 0.87 |
| joint raw o2, 4 either side | **+2.56** / 0.40 / 1.27 / 0.36 | +0.43 / 0.38 / 0.44 / 0.93 | −0.47 / 0.26 / 0.50 / 0.57 | **−5.08** / 0.62 / 2.59 / 0.27 |
| joint R/R_F o2, 4 either side | +0.06 / 0.40 / 0.43 / 0.95 | +0.04 / 0.38 / 0.39 / 1.01 | −0.73 / 0.26 / 0.68 / 0.42 | **−5.30** / 0.62 / 2.67 / 0.26 |
| joint R/R_F o3, 2 either side | +0.06 / 0.49 / 0.53 / 0.96 | −0.00 / 0.44 / 0.46 / 0.98 | +0.03 / 0.29 / 0.31 / 0.95 | +0.33 / 0.77 / 0.81 / 0.96 |
| joint raw o4, 4 either side | +0.05 / 0.47 / 0.51 / 0.94 | +0.00 / 0.44 / 0.45 / 1.01 | +0.01 / 0.28 / 0.30 / 0.95 | +0.02 / 0.74 / 0.77 / 0.96 |
| **joint R/R_F o4, 4 either side** | +0.07 / **0.47** / 0.51 / 0.94 | +0.00 / **0.44** / 0.45 / 1.01 | +0.01 / **0.28** / 0.30 / 0.95 | +0.02 / **0.74** / 0.77 / 0.96 |
| joint R/R_F o4, 8 either side | +0.05 / 0.40 / 0.42 / 0.97 | +0.00 / 0.37 / 0.38 / 0.99 | −0.11 / 0.25 / 0.29 / 0.89 | −0.05 / 0.64 / 0.78 / 0.84 |
| joint raw o4, 8 either side | −1.74 / 0.40 / 0.96 / 0.46 | −0.03 / 0.37 / 0.38 / 0.99 | −0.13 / 0.25 / 0.29 / 0.87 | −0.06 / 0.64 / 0.78 / 0.84 |
| C2 junction (separate u³,u⁴ per scan), o4, 4 | +0.07 / 0.72 / 0.78 / 0.93 | −0.01 / 0.60 / 0.65 / 0.92 | +0.00 / 0.41 / 0.45 / 0.93 | −0.03 / 0.93 / 0.96 / 0.98 |

Staggered grid (nothing coincides): spline ratio +0.06 / 0.72 / 0.77 /
0.98 at join 1, 1.07 % SD at join 4; joint R/R_F o4 e4 +0.07 / 0.52 / 0.57
/ 0.93 and 0.79 %. Legacy join 1 pull SD 2.20 (staggered), 2.93
(coinciding only). The pulls slightly below 1 (0.94–0.96) come from the
inflate-only rule (by design, hand-off §5.7).

**Table 2. P1 bias without noise (%), scan b staggered, step of scan a = step_b/4** (`p1scan.py`)

| Overlap at Q | step_b | Δ = Δq·\|d ln R/dq\| | legacy (spline in y) | spline in ln y | linear in ln y | joint R/R_F o4 e4 |
|---|---|---|---|---|---|---|
| 0.04 | 0.0025 | 0.27 | −0.03 | −0.002 | −0.20 | 0.000 |
| 0.04 | 0.005 | 0.51 | −0.29 | −0.021 | −0.72 | 0.000 |
| 0.04 | 0.01 | 0.95 | **−2.09** | −0.17 | −2.37 | 0.000 |
| 0.095 | 0.02 | 0.77 | −0.76 | −0.054 | −0.71 | −0.001 |
| 0.18 | 0.02 | 0.66 | −0.25 | −0.040 | −0.15 | +0.014 |
| 0.42 | 0.02 | 0.53 | −0.01 | −0.036 | +0.28 | +0.007 |

The unit test's case (`test_staggered_grid_recovers_factor`, Fresnel
curve, step_b 0.01 at Q 0.04–0.05): legacy 1.4013, spline in ln y
1.4189, joint o2–o4 in R/R_F 1.42000 (exact, since that curve is pure
Fresnel), joint raw o2 overlap-only 1.4200, raw o4 e2 1.4185.

**Table 3. The chain: scale of scan m relative to the anchor** (bias % / SD % / pull SD with √Σ_mm / pull SD with the join's own error only), NX grid, `mc2.py`

| Method | Scan 2 | Scan 3 | Scan 4 | Scan 5 |
|---|---|---|---|---|
| legacy (its own facerr) | +0.01 / 0.62 / **1.49** | +0.02 / 0.84 / **2.26** | +0.01 / 0.90 / **4.01** | −0.03 / 1.35 / **1.98** |
| §3.2 chain + §3.4 Σ | +0.01 / 0.62 / 0.97 / 0.97 | +0.02 / 0.84 / 1.01 / 1.59 | +0.01 / 0.89 / 0.99 / 2.62 | −0.02 / 1.35 / 1.01 / 1.40 |
| joint R/R_F o4 e4 chain + Σ | +0.03 / **0.49** / 0.95 / 0.95 | +0.04 / **0.67** / 0.99 / 1.53 | +0.04 / **0.71** / 0.96 / 2.42 | +0.12 / **1.06** / 0.99 / 1.38 |
| global, one polynomial per join (disjoint windows) | +0.03 / 0.49 / 0.98 | +0.04 / 0.67 / 1.02 | +0.04 / 0.71 / 0.99 | +0.12 / 1.06 / 1.03 |
| global B-spline, knots 0.01 | +0.12 / 0.42 / 0.88 | +0.13 / 0.60 / 0.90 | +0.13 / 0.67 / 0.89 | +0.16 / 1.17 / 0.91 |
| global B-spline, knots 0.02 | +0.50 / 0.36 / 0.76 | +0.52 / 0.52 / 0.77 | +0.52 / 0.59 / 0.76 | +0.50 / 1.07 / 0.84 |

Staggered grid: the same picture (joint chain SD 0.55, 0.67, 0.71, 0.97 %
against 0.67, 0.85, 0.93, 1.37 % for §3.2; pulls with Σ 0.84–0.98).

**Table 4. The known ratio as a prior** (bias % / SD % / mean σ % / pull SD of the scale of scans 2 and 5), `mc3.py`. Prior errors drawn from the correlated C_prior of the NX settings 41→31→24→18→10; joint R/R_F o4 e4 fits. "P29" = the prior of join 2 off by the given factor (the beam changed, the foils did not).

| Counts at scan start; P29 | Method | Scan 2 | Scan 5 |
|---|---|---|---|
| 5×10⁵; none | fit only | +0.01 / 0.46 / 0.51 / 0.92 | +0.06 / 0.95 / 1.07 / 0.89 |
| | known ratio only | −0.09 / 1.48 / 1.55 / 0.96 | −0.05 / 3.11 / 3.07 / 1.01 |
| | combined, correlated prior, guarded | −0.01 / 0.43 / 0.48 / 0.91 | +0.02 / 0.88 / 0.97 / 0.91 |
| | reader's `patch_choice` (auto, 3 %) | = fit only (never triggers) | = fit only |
| 5×10⁵; ×1.05, no monitor flag | combined, no guard | +0.27 / … | **+1.57** / 0.87 / 0.97 / 0.91 |
| | combined, guard \|z\| ≤ 3 | −0.00 / 0.44 / 0.48 / 0.92 | +0.10 / 0.98 / 1.01 / 0.98 |
| 5×10⁵; ×1.5, monitor flag | combined, no guard | +2.34 | **+12.9** |
| | combined, guarded | −0.01 / 0.43 / 0.48 / 0.91 | +0.05 / 0.91 / 1.02 / 0.90 |
| 2×10⁴; none | fit only | +0.25 / 2.36 / 2.60 / 0.93 | +1.02 / 4.86 / 5.38 / 0.91 |
| | combined, correlated, guarded | +0.05 / **1.26** / 1.26 / 1.00 | +0.21 / **2.39** / 2.44 / 0.97 |
| | combined, independent prior (diagonal) | +0.10 / 1.32 / 1.32 / 1.00 | +0.36 / 2.49 / 3.14 / 0.79 |
| | reader's `patch_choice` | +0.22 / 2.31 / 2.39 / 0.96 | +0.97 / 4.83 / 5.26 / 0.92 |
| 2×10⁴; ×1.05, no monitor flag | combined, guard \|z\| ≤ 3 | +0.27 | **+3.78** / 3.66 / 2.56 / 1.39 |
| 2×10⁴; ×1.5, monitor flag | combined, guarded | +0.07 / 1.28 / 1.27 / 1.01 | +0.58 / 3.29 / 3.34 / 0.99 |

The correlated prior is better than treating the joins' priors as
independent (scan 5: σ 2.44 against 3.14 %, pull 0.97 against 0.79): the
direct foil difference between distant settings is better known than the
sum of the steps.

**Table 5. Likelihood and window choice** (bias % / SD %, joins 1 and 4), `mc5.py`, `mc6.py`

| Counts | log-space o4 e4 | Poisson (linear) o4 e4 | spline ratio §3.2 |
|---|---|---|---|
| 5×10⁵ | +0.04 / 0.45 ; +0.08 / 0.72 | +0.03 / 0.45 ; +0.06 / 0.73 | +0.02 / 0.54 ; −0.06 / 0.91 |
| 2×10⁴ | +0.08 / 2.32 ; +0.30 / 3.43 | −0.08 / 2.32 ; −0.12 / 3.43 | −0.44 / 2.94 ; −1.17 / 4.53 |
| 2×10³ | +2.21 / 7.35 ; **+9.88** / 12.97 | +0.52 / 7.52 ; +0.70 / 12.48 | −3.22 / 10.48 ; **−12.05** / 20.35 |

| Window rule (5×10⁵, NX grid) | join 1 RMSE / pull | join 4 RMSE / pull |
|---|---|---|
| fixed o4 e4 | 0.49 / 0.97 | 0.76 / 0.99 |
| search (χ² p ≥ 0.01 and Hausman 2σ, up to 8) | 0.51 / 1.06 | 0.81 / 1.09 |
| search, order 2 | 0.45 / 1.07 | 0.91 / 0.92 |

### 5.1 Downstream fit (P4)

`mc4.py`: the five synthetic scans stitched, then the slab model (d, SLD,
σ, free overall scale) fitted by least squares in ln y with the given
covariance (Cholesky-whitened residuals, `scipy.optimize.least_squares`),
truth as the model. Pull = (fitted − true)/(fit's own error, not rescaled
by χ²). 200 seeds (NX grid, 5×10⁵), 150 seeds (others); the SD of a pull
SD from 150 seeds is ≈ 0.06. "χ²/N vs truth" = the stitched curve against
the true curve (true scale) with that covariance: 1 means the errors cover.

**Table 6. Slab fit: pull SD of d / SLD / σ; fit χ²/dof; χ²/N of the curve vs truth; RMS error of d (Å) / SLD (10⁻⁶ Å⁻²) / σ (Å)**

| Error treatment | NX grid, 5×10⁵ | staggered, 5×10⁵ | NX grid, 2×10⁴ |
|---|---|---|---|
| A legacy chain, legacy error column (diagonal) | **1.72 / 4.83 / 4.52**; 0.81; 1.68; 0.026 / 0.020 / 0.006 | 1.83 / 5.96 / 5.34; 0.83; 2.11 | 1.57 / 5.26 / 4.34; 0.80; 1.78; 0.125 / 0.106 / 0.032 |
| B joint, counting errors only | 2.06 / 5.87 / 7.39; 1.31; 4.54; 0.016 / 0.015 / 0.005 | 2.35 / 6.34 / 8.64; 1.41; 5.50 | 1.97 / 7.00 / 7.15; 1.35; 4.95 |
| C joint, Σ_mm folded into the diagonal (the hand-off's corrected error column used alone) | 1.01 / **3.44 / 3.17**; 0.54; 0.86; 0.018 / 0.018 / 0.005 | 1.01 / 3.61 / 3.51; 0.52; 0.89 | 0.93 / 4.04 / 3.08; 0.53; 0.91 |
| **D joint, full covariance** | **1.04 / 1.07 / 1.13**; 0.97; 0.98; **0.011 / 0.006 / 0.003** | 1.14 / 1.06 / 1.29; 0.96; 0.97; 0.012 / 0.006 / 0.004 | 1.13 / 1.15 / 1.14; 0.96; 0.97; 0.060 / 0.032 / 0.015 |
| D joint + foil prior (guarded), full covariance | 1.03 / 1.05 / 1.12; 0.97; 0.97; 0.011 / 0.006 / 0.003 | 1.14 / 1.05 / 1.28 | 1.10 / 1.19 / 1.16; 0.97; 0.98; **0.052 / 0.026 / 0.012** |
| D §3.2 spline ratio, full covariance | 1.02 / 1.03 / 1.06; 0.97; 0.97; 0.011 / 0.006 / 0.003 | 1.10 / 1.01 / 1.22 | 1.12 / 1.12 / 1.10; 0.96; 0.97; 0.061 / 0.032 / 0.015 |

Findings (measured):

- **The covariance is what restores the pulls.** Legacy errors give
  SLD and roughness pull SDs of 4.5–6 (the hand-off's 5.3 reproduced in
  kind); folding the inherited Σ into the diagonal fixes the coverage of
  single points (χ²/N 0.86–0.91) but not the fit (pulls 3–4, and the fit's
  χ²/dof 0.53 looks deceptively good); only the full covariance gives
  pulls of 1.0–1.15 (1.2–1.3 on one parameter of the staggered set).
- **It also makes the fit more accurate**, not just honest: RMS error of
  the SLD 0.006 against 0.020 (legacy) and 0.018 (folded), of d 0.011 Å
  against 0.026 Å. With the covariance the fit lets each scan's level
  float within Σ instead of bending the model to absorb it.
- **Downstream, the factor estimator matters less than the covariance.**
  With the full covariance, joint and §3.2 give the same parameter
  accuracy at these counts: the structural model re-determines the
  levels. The joint fit's gains are in the curve itself (σ of the levels,
  table 3), in any fit that does not use the covariance, and at low counts
  together with the prior (2×10⁴: RMS of d 0.052 against 0.061 Å).
- The small excess over 1 (≤ 0.15, once 0.29) is consistent with the
  double use of the overlap points discussed in §4.3 and with the
  inflate-only rule; it is far smaller than any other treatment's.

## 6. Real data

### 6.1 NX school, scans 6–9 (public; `nx_real.py`, `nx_chain.py`)

Reduced with `Experiment.reflectivity([6, 7, 8, 9], errors='budget')`
(legacy errors give the same factors to 0.01 %). Overlaps: 5 points of
the earlier scan and 3 of the later in each of the first three joins; 3
coincide. Monc/Monp of b over a: 1.005, **4.35**, **1.32** (slits changed
at joins 2 and 3, so the guard keeps the prior out there, although it
agrees).

| Join | legacy step | §3.2 spline ratio | coinciding points | joint R/R_F o2, overlap only | joint R/R_F o4 e4 (Poisson) | known ratio (foils) |
|---|---|---|---|---|---|---|
| S6→S7 (41→31) | 0.022934 ± 0.36 % | 0.022934 ± 0.46 % (χ²/dof 0.62) | 0.022884 ± 0.62 % | 0.022940 ± 0.47 % | **0.023004 ± 0.38 %** (χ²/dof 0.86, dof 10) | 0.02311 ± 1.55 % (z −0.3) |
| S7→S8 (31→24) | (cumulative 0.0014797 ± 0.80 %) | 0.064519 ± 0.80 % (χ²/dof 1.96, inflated) | 0.063988 ± 1.09 % | 0.064547 ± 0.81 % | **0.064516 ± 0.50 %** (χ²/dof 1.09) | 0.06555 ± 0.94 % (z −1.5; not used: slits) |
| S8→S9 (24→18) | (cumulative 0.00015337 ± 0.46 %) | 0.103676 ± 0.46 % | 0.104056 ± 0.71 % | 0.103706 ± 0.46 % | **0.103604 ± 0.41 %** (χ²/dof 1.37) | 0.10386 ± 0.75 % (z −0.3; not used: slits) |

**Later numbers (pointer added 2026-11-25):** this table predates the
guard ladder (6bb29bf, 2026-11-23) and the guard's default p 0.7
(2026-11-24). Remade with the ladder, the joint o4 e4 fit takes order 5 at
S8→S9 (the first adequate fit) and gives 0.103423 ± 0.35 % there; the
first two joins are unchanged. The current numbers, with the reader's
default window, are COMPARISONS C33 (`docs/COMPARISONS.md`), regenerated
by `tests/tools/ref_patch_survey.py`.

- Joint vs legacy/§3.2: +0.30 %, −0.00 %, −0.07 % — within 0.6–0.8 σ of
  the joint fit's errors. The spline (P1) bias on these grids is ≈ 0.01 %
  (table 2), so the differences are noise in which points are used.
- Window guard: o4 with 6 either side at S8→S9 gives χ²/dof 60 (the window
  reaches the first fringe) and would be rejected; at 4 it is 1.4.
- Scale of scan 9 relative to scan 6 (√Σ_mm): §3.2 chain 0.46, 0.92,
  **1.03 %**; joint 0.38, 0.63, **0.75 %**; with the foil prior on all
  joins (no guard) 0.37, 0.56, 0.66 %; guarded (prior at join 1 only)
  0.37, 0.62, 0.74 %.
- Per-point errors at scan 9 (Q = 0.2, 0.3, 0.45): legacy total 0.55,
  0.80, 2.44 %; counting only 0.30, 0.65, 2.39 %; √diag of the corrected
  covariance (joint) 0.81, 0.99, 2.51 %. The diagonal grows, but 0.75 % of
  it is one common shift of the whole scan.

### 6.2 The owner's data (aggregates only)

The private `sample_data/bu/` files here contain no reflectivity series
(GID, XFNTR and energy scans only; checked with `lss_core.series`), so the
joint fit could not be run on the owner's curves. The committed anonymous
table `docs/handoff_out/03-answer/joins.csv` (coinciding-point steps of
the owner's reflectivity joins) gives aggregates relevant to the design:

| Quantity (1041 joins at 10 keV, absorber changed, not excluded) | Value |
|---|---|
| coinciding points per join | 2: 79, 3: 517, 4: 61, 5: 253, 6: 53, 15: 75 |
| counting error of the step | median 0.37 %, 10–90 % 0.27–1.14 % |
| known-ratio error (`Foils.step`, low-Qz form) | median 0.87 %, 0.61–1.56 % |
| joins where the known ratio is more precise | 10 % (1 % with the ×3.2 high-Qz form) |
| combined/fit error, clean joins | median 0.93 (10–90 %: 0.78–0.96) |
| overlap χ²/dof (≥ 3 points) | median 1.35; 37 % above 2; 23 % with p < 0.01 (1 % expected) |
| Monc/Monp changed by ≥ 3 % | 607 of 1041 (58 %): no prior there |
| z = ln(step/known)/σ, Monc/Monp unchanged | median +0.03, robust SD 0.68, 10 % beyond 3σ |
| z, Monc/Monp changed | median −2.1, robust SD 3.8, 47 % beyond 3σ |

Consequences: (1) the patch, not the prior, carries the factor at most
joins; the prior is a check and a help at weak joins. (2) Excess scatter
at the overlap is common (23 % of joins fail χ² at 1 %): inflate-only is
needed, and with 3 coinciding points (2 dof) the inflation itself is
noisy; a joint fit over ~10–14 points estimates it far better. (3) At
slit changes the prior is wrong in a way the monitor ratio reveals, which
is why the monitor guard comes first. (The foils were fitted on these
joins, so z on clean joins is not an independent test; the hand-off 03
answer's leave-one-run-out check is.)

## 7. Recommended default and options

| Setting | Default | Options | Evidence |
|---|---|---|---|
| Estimator | joint fit, one shared polynomial in ln(R/R_F) | `interp` (§3.2 spline ratio, reference), `coincident`, `legacy` (untouched) | tables 1–3, 5 |
| Order | 4 | 2, 3 | table 1 |
| Window | 4 points either side of the overlap; guard χ² p < 0.01 → 2 → overlap-only o2, flagged | `n_ext` any; no data-driven search | tables 1, 5; NX S8→S9 |
| Likelihood | Poisson-like (linear y, model variance), started from the log fit | `'log'` | table 5 |
| Error | counting ⊗ max(1, √χ²/dof) | | hand-off §3.2 |
| Prior | known ratio with correlated C_prior; only where Monc/Monp within 3 % and \|z\| ≤ 3; rejected joins marginalised | off; independent priors | table 4, 6.2 |
| Chain | join by join with a_m from the hat matrix, Σ by §3.4 | global (same answer for disjoint windows; needed for scans overlapping more than one neighbour) | table 3 |
| Output points | as measured (scaled), averaged only at coinciding Q_z | legacy averaging | §4.4 |
| Legacy | unchanged, byte-identical (rule 3) | | |

Cost: one small linear solve per join plus ≤ 8 Gauss–Newton steps:
negligible (table 1, 300 seeds × 3 grids × 25 estimators, ran in 15 s).

## 8. API sketch: `lss_core/patching.py`

GUI-free, NumPy/SciPy only, beside `stitching.py` (which stays the legacy
chain). A scan is `Scan(q, y, sigma, label=None)` (σ counting only).

```python
@dataclass
class JoinFit:
    delta: float            # ln f, f multiplies scan b
    err: float              # reported: err_counting * max(1, sqrt(chi2/dof))
    err_counting: float
    chi2: float; dof: int
    order: int; n_ext: int; space: str; likelihood: str
    ia: np.ndarray; ib: np.ndarray          # indices used in a and b
    sensitivity: np.ndarray                 # d delta / d ln y_i over the used points
    prior: tuple | None                     # (delta0, s0) offered
    prior_used: bool; z: float | None; why: str
    flags: list                             # 'window reduced', 'few points', ...
    @property
    def factor(self): return math.exp(self.delta)

def window(qa, qb, n_ext=4) -> tuple[np.ndarray, np.ndarray]
def joint_factor(a: Scan, b: Scan, order=4, n_ext=4, space='rrf', qc=0.0217,
                 qoff=0.0, likelihood='poisson', prior=None, inflate=True,
                 guard_p=0.01) -> JoinFit
def interp_factor(a, b, kind='cubic', log=False, inflate=True) -> JoinFit      # §3.2 reference
def coincident_factor(a, b, tol=1e-6, inflate=True) -> JoinFit | None
def known_steps(foils, settings, overlap_qz) -> tuple[np.ndarray, np.ndarray]
    # mean ln step per join and the correlated C_prior (diag == Foils.step()**2)
def prior_mask(monitor_ratios, z, tol=0.03, z_max=3.0) -> tuple[np.ndarray, list[str]]
def combine(delta, C_data, prior_mean, prior_cov, use=None) -> tuple[post, C_post, z]
def chain_covariance(a_rows, errors) -> np.ndarray                              # hand-off §3.4
def chain(scans, fitter=joint_factor, prior=None, **kw) -> PatchResult
def global_fit(scans, order=4, n_ext=4, space='rrf', prior_mean=None, prior_cov=None) -> PatchResult
@dataclass
class PatchResult:
    phi: np.ndarray; Sigma: np.ndarray     # K, K x K (log units, anchor 0)
    joins: list[JoinFit]; method: str
    def stitch(self, scans, merge='coincident') -> Stitched
@dataclass
class Stitched:
    q, y, sigma_meas, W, Sigma
    def sigma_total(self): ...              # sqrt(sigma_meas^2 + y^2 * diag(W Sigma W^T))
    def covariance(self, space='log', model=None): ...   # N x N; D = diag(model) if given
def pulls(estimate, truth, error) -> dict  # bias, sd, pull_sd, coverage68 (for tests and the survey)
```

Integration: `reflectivity.patch(..., method='legacy'|'joint')` and
`Experiment.reflectivity(..., patch='legacy'|'joint')` return the
`PatchResult` beside the legacy array; the sidecar writer (F24) takes
`Stitched`. The patch window shows the joint factor, its χ²/dof and the
window, with the reasons in tooltips (rule 9).

Tests that should pin it:

| Test | Kind |
|---|---|
| `test_stitching.py::test_staggered_grid_recovers_factor` passes with `patching.joint_factor` (1.4200 to 1e-4); the legacy xfail stays for `stitching` | invariant / fix of P1 for the new path |
| exact data ln y = poly₄ on both scans: δ exact, χ² = 0, for raw, rrf, staggered and coinciding grids | invariant |
| scaling scan b by c shifts δ by ln c exactly; scaling both scans changes nothing; order of points irrelevant | invariant |
| sensitivity summed per scan = 1 (intercept absorbs a common shift); matches a finite-difference check | invariant |
| `chain_covariance` random walk = cumulative sums; non-one-hot a_m equals the hand-off oracle | invariant |
| `global_fit` with disjoint windows = `chain` to 1e-10 | invariant |
| `combine`: diagonal case = inverse-variance mean; `use=False` returns the data; prior rows marginalised | invariant |
| `known_steps` diagonal = `Foils.step(...)[1]**2` (×3.2² at Q_z ≥ 0.25) | invariant |
| guard: Monc/Monp 1.58 → prior not used, why says so; \|z\| > 3 → not used | as coded |
| window guard: NX S8→S9 at `n_ext=6` is reduced (χ² p < 0.01), at 4 not | as coded (slow, real data) |
| NX 6–9 factors and √Σ_mm (0.023004, 0.064516, 0.103604; 0.38, 0.63, 0.75 %) | as coded (slow) |
| Monte Carlo, 200 seeds, synthetic slab: \|bias\| < 0.2σ, pull SD 0.85–1.1 per join, χ² of stitched curve vs truth with full covariance ≈ 1 | statistical (slow) |
| legacy export fixtures unchanged | rule 3 |

## 9. Plan for the third agent (larger data set)

Model: `docs/handoff_out/06-gid-method-comparison.md`. A tool
`tests/tools/ref_patch_survey.py --spec FILE [--spec …] | --list sets.csv
--out DIR [--split] [--repeats]`, reading only, finding reflectivity
series with `lss_core.series` (or a list: spec, scans, label), reducing
with `Experiment.reflectivity(..., errors='budget')`, and running every
method at every join. Private outputs only under `sample_data/private/`
or outside the repository (the tool checks).

**`joins.csv`** (one row per set × join × method):

| Column | Meaning |
|---|---|
| set, join, scan_a, scan_b, method | what was run (`legacy`, `interp`, `coincident`, `joint_o2_e0`, `joint_o4_e2`, `joint_o4_e4`, `joint_o4_e4_raw`, `joint_o4_e4_prior`, …) |
| energy_kev, n_a, n_b, bits_a, bits_b | absorber settings |
| q_lo, q_hi, q_class | overlap; class `<0.05`, `0.05–0.25`, `≥0.25` |
| points_a, points_b, coincident | points in the overlap; shared Q_z |
| n_ext, order, space, likelihood, window_reduced | window actually used |
| delta, err, err_counting, chi2_dof, dof, p_chi2 | the fit |
| d_legacy_sigma | (δ − δ_legacy)/err |
| known, known_err, z_known, prior_used, why | prior and guard |
| monc_monp_ratio, slits_changed | P29 context |
| cv_resid | leave-one-out: predict each coinciding point of b from the fit without it, normalised residual (RMS reported) |
| seconds, error | |

**`sets.csv`** (one row per set × method): scans, K, φ_m and √Σ_mm per
scan, √Σ of the last scan, max per-point σ_total/σ_meas, number of joins
flagged.

**`split.csv`** (`--split`, the truth test on real curves): every scan
with ≥ 20 points split into two overlapping halves (overlap 3–6 points,
both staggered and coinciding variants), the second's values × 0.8 with
σ × 0.8; per method the recovered factor (truth 1.25) and its pull. Bias
and pull SD here are measured on the owner's real curve shapes, real
noise and real background, with known truth.

**`repeats.csv`** (`--repeats`): where a scan was repeated
(`reflectivity.identical_groups`), each repeat joined to the same scan a:
the difference of the two factors against √(σ₁² + σ₂²) (an empirical
pull; the shared scan a makes it conservative).

**How to judge** (in this order):

1. **Split truth**: bias < 0.2σ and pull SD 0.9–1.15 per Q class, per
   method. The method that passes everywhere with the smallest σ wins;
   look at the worst class, not only the median.
2. **Repeats**: empirical pull SD ≈ 1 for the reported errors (catches
   non-counting noise between measurements, which split tests cannot).
3. **Clean joins vs foils**: robust SD of z_known ≈ 1 by Q class
   (independent of the patch method only out of sample: foils from
   leave-one-run-out).
4. **χ² of the joint fit** by Q class and order: the fraction with
   p < 0.01 should approach 1 % for an adequate model; a larger fraction
   at high Qz measures excess (non-counting) scatter, which then belongs in
   the per-point error model, not only in the factor.
5. **Window and order**: from split truth, the RMSE against n_ext (0, 2,
   4, 6, 8) and order (2, 3, 4) per Q class; confirm or change the 4/4
   default; report how often the guard steps down.
6. **Prior**: for clean joins, the error reduction and the bias of the
   combined estimate on split truth (with the foil prior only where the
   absorbers differ between the halves: the split halves share a setting,
   so use a synthetic prior there) and the agreement on real joins.
7. Report as `06` asks: a table per decision, a recommendation, private
   numbers only in the owner's channel, proposed rows for
   `docs/OUTPUT_DECISIONS.md` with before/after values (factor change per
   join, √Σ of the last scan).

## 10. Literature (cited from memory; links given where known)

- G. D'Agostini, "On the use of the covariance matrix to fit correlated
  data", Nucl. Instrum. Meth. A 346 (1994) 306–311,
  https://doi.org/10.1016/0168-9002(94)90719-6 — Peelle's pertinent
  puzzle: a normalisation covariance built from measured values biases
  fits low; use the model (or log space).
- G. L. Fogli, E. Lisi, A. Marrone, D. Montanino, A. Palazzo, "Getting the
  most from the statistical analysis of solar neutrino oscillations",
  Phys. Rev. D 66 (2002) 053010, https://arxiv.org/abs/hep-ph/0206162 —
  equivalence of the covariance and the nuisance-parameter ("pull")
  treatments of correlated systematic errors (§4.3).
- JCGM 100:2008 (GUM), §5.2, https://www.bipm.org/en/doi/10.59161/JCGM100-2008E
  — propagation with correlated inputs.
- P. H. C. Eilers, B. D. Marx, "Flexible smoothing with B-splines and
  penalties", Statist. Sci. 11 (1996) 89–121,
  https://doi.org/10.1214/ss/1038425655 — the global spline variant tried
  in §3.4.
- J. A. Hausman, "Specification tests in econometrics", Econometrica 46
  (1978) 1251–1271, https://doi.org/10.2307/1913827 — the nested-estimator
  test used in the window search (table 5).
- A. R. J. Nelson, S. W. Prescott, "refnx: neutron and X-ray reflectometry
  analysis in Python", J. Appl. Cryst. 52 (2019) 193–200,
  https://doi.org/10.1107/S1600576718017296 — a reflectometry package
  whose fits accept per-dataset scale parameters (the nuisance form of
  §4.3).
- Hand-off 19 (`docs/handoff/19-lss-reader-covariance-contract.md`) and
  its spec 17 for the contract and the inflate-only estimator.

## 11. What was measured and how (scripts in the subagent's scratchpad)

| Script | What it does |
|---|---|
| `patchlab.py` | Parratt model; `joint_factor` (log-space WLS, shared polynomial, R/R_F, raw or log–log baseline, prior, C2-junction variant), `joint_factor_linear` (Poisson-like Gauss–Newton), `interp_factor`, `coincident_factor`, `chain_covariance`, `chain`, `global_fit` (local windows or B-spline), `combine`, `stitch_all_points`, `auto_joint` |
| `sim.py` | synthetic scans (the §5 setup), grids `nx`, `staggered`, `coincide`; priors with optional P29 offset |
| `p1scan.py` | table 2 (noise-free) |
| `mc1.py` | table 1 (300 seeds × 3 grids × 25 estimators) |
| `mc2.py` | table 3 (chains, global fits) |
| `mc3.py` | table 4 (priors, guards, `reflectivity.patch_choice`) |
| `mc4.py` | table 6 (downstream slab fits; legacy chain via `reflectivity.patch`) |
| `mc5.py`, `mc6.py` | table 5 (likelihood at low counts; window search) |
| `nx_dump.py`, `nx_real.py`, `nx_chain.py` | §6.1 |
| (inline) | §6.2 from `docs/handoff_out/03-answer/joins.csv` |
