# What a model fit needs from the reader's covariance

Written 2026-11-22 by a subagent, at the owner's request: "Have another
subagent think about what is needed on covariance downstream for model
fitting, then have them build something workable." §1–5 are the
thinking; §6 is what was measured; §7 is what was built and how to use
it; §8 lists the decisions left to the owner.

"Measured" means a script or test was run in this session and the number
is its output; "reasoned" means derived or argued, not run; "read" means
taken from a document. The literature (§9) is cited from memory: the
session could not reach arxiv.org or doi.org to re-check it.

## 1. The structure of the errors

A stitched reflectivity curve is K scans, each multiplied by a factor
that puts it on the anchor scan's level. Each factor is measured in a
finite overlap, so it has an error, and that error is **one common shift
of every point of its scan**; through the chaining it is also inherited
by every later scan (hand-off 19 §1, `PHYSICS_ISSUES.md` P4). With

- σ_meas,i the counting-only error of point i (no factor error in it),
- W (N × K) the share of each point in each scan's log scale (one-hot for
  a point from one scan, ½/½ for a point averaged from two),
- Σ (K × K) the covariance of the scans' log scales φ_m = ln f_m
  (anchor row and column zero),

the covariance of the data is **low rank on top of a diagonal**:

    of ln y:  C_log = diag((σ_meas/y)²) + W Σ Wᵀ
    of y:     C     = diag(σ_meas²)     + D W Σ Wᵀ D,   D = diag(model)      (reasoned; = hand-off §2.4)

rank(W Σ Wᵀ) ≤ K − 1 (3 for four scans), whatever N is. Σ is in natural
log units, which is what makes everything below simple: a multiplicative
error is additive in ln y.

What a fitter needs is exactly what the hand-off's sidecar carries: N
values of σ_meas, the N × K matrix W, the K × K matrix Σ, and x and y so
that the file can be checked against the data it describes. Nothing
else is needed, and nothing is lost by not writing the N × N matrix
(reasoned: C is a function of these).

## 2. How a fit uses it

### 2.1 Generalised least squares (GLS)

The weighted χ² with correlated errors is χ² = rᵀ C⁻¹ r, r = data −
model (Aitken 1935). For N of a few hundred a dense Cholesky of C is
cheap, but the low-rank form is cheaper and better conditioned. Write
Σ = L Lᵀ over its positive eigenvalues (L: K × r, r ≤ K − 1; Σ is
singular because the anchor is fixed, so a plain Cholesky fails), U = W L
(log space) or D W L (linear), A = diag(σ²). Then C = A + U Uᵀ and the
Woodbury identity (Hager 1989) gives

    C⁻¹ = A⁻¹ − A⁻¹ U (I_r + Uᵀ A⁻¹ U)⁻¹ Uᵀ A⁻¹
    ln det C = Σ ln A_ii + ln det(I_r + Uᵀ A⁻¹ U)

an r × r solve per evaluation. Built: `gls.LowRank` (tested against the
dense algebra to 1e-9, `tests/test_gls.py`).

### 2.2 Equivalently: one nuisance scale per scan

Let the model carry a log scale shift per scan, φ = L η, with the
Gaussian penalty |η|² (prior φ ~ N(0, Σ)):

    χ²(θ, η) = Σ_i (ln y_i − ln m_i(θ) − (W L η)_i)² / (σ_meas,i/y_i)² + |η|²

The residual is linear in η, so minimising over η is a linear
least-squares problem whose minimum is (standard Gaussian algebra;
Stump et al. 2001, Fogli et al. 2002, "pulls")

    min_η χ²(θ, η) = rᵀ (A + U Uᵀ)⁻¹ r = rᵀ C_log⁻¹ r,   r = ln y − ln m(θ).

**Exactly** the GLS χ² in log space, for every θ (reasoned; measured to
1e-9 relative in `test_gls_chi2_equals_the_nuisance_form`). So a fitter
that cannot handle a covariance can instead fit K − 1 extra parameters
with Gaussian priors; the parameter errors from the joint Hessian are the
same as from GLS (the marginal covariance of θ). In linear space the
nuisance form m_i·exp((Wφ)_i) against σ_meas is the covariance form with
D = diag(model) to first order; it is the form D'Agostini (1994)
recommends, because it applies the scale to the model, not to the noisy
data (no Peelle's-puzzle bias). The fitted η are also useful on their
own: η_m ~ N(0, 1) a priori, so a scan whose η is 3 is a scan whose level
the structural model disputes (a P29-type problem, a bad join, a burn;
`test_shifts_show_a_scan_whose_level_is_off`).

Bayesian samplers: in log space C does not depend on θ, so ln det C is a
constant and the likelihood is exp(−χ²/2). In linear space with
D = diag(model) it does depend on θ; either keep −½ ln det C (cheap via
Woodbury) or, better, sample the η's as parameters (the nuisance form),
which makes the likelihood diagonal again.

### 2.3 The overall scale

The normalisation (the highest point below Q_c, then an optional typed
factor) is a free overall factor and is **not** in Σ (contract §2.6). The
normalising point's own counting error (`norm_rel_err` in the sidecar's
provenance; ≈ 0.2 % on NX-like scans, measured) is a common shift of all
points. A fit should fit the scale (as XModFit and `gls.fit(free_scale=
True)` do). A fit that fixes it must add that variance as a further
multiplicative term with W = ones (allowed by the contract, §2.6).
Because Σ's anchor row is zero, Σ and the free scale do not overlap:
together they describe "each scan's level, relative to a free overall
level" (reasoned). The choice of anchor does not change a fit with a free
scale (reasoned, as in the joint-fit report §4.2).

## 3. Transforms

Each must be applied to x, y, σ_meas and the rows of W **point for
point, in the same order as the data file** (contract §2.1). Σ is in log
units, so most of them never touch it. Built: methods of
`covariance_export.CovData`; invariants tested in
`tests/test_covariance_export.py` (I28).

| Transform | x, y, σ_meas | W | Σ | C | Tested |
|---|---|---|---|---|---|
| Normalisation by c (number) | y/c, σ/c | — | — | C_log unchanged; C_lin/c² | yes |
| Fresnel division by R_F(q + q_off) | y/R_F, σ/R_F | — | — | C_log unchanged; D⁻¹C_lin D⁻¹ | yes |
| Q_z offset | x + q_off (the `_rrf` file only; `_ref` keeps q) | — | — | — | yes |
| Sorting, removing points, cutting a Q range, a fit mask | rows selected | rows selected | — | rows and columns of C | yes |
| Averaging / binning points j with weights w_j | ȳ = Σw y, σ = √Σw²σ² | Σ_j (w_j y_j/ȳ) W_j | — | first-order exact | yes (Monte Carlo of 4000 draws) |
| Merging repeats before patching | as the identical-scan merge | the merged scan is one region | — | — | via the chain |
| Joining two stitched sets by a further factor (error e, fitted against weights a of set 1) | concatenated | block | [[Σ₁, Σ₁a1ᵀ],[1aᵀΣ₁, Σ₂ + (aᵀΣ₁a + e²)11ᵀ]] | — | yes |
| Q_z² display | none: a plot only (T8 fixed) | | | | the golden tests |

Notes (reasoned):
- The averaged W row is the derivative of ln ȳ with respect to the log
  scales: Σ_j (w_j y_j/ȳ) W_j. It equals Σ_j w_j W_j when the averaged
  values agree, which is the hand-off's ½/½ for the legacy overlap
  average. The chain keeps the hand-off's ½/½ (its acceptance test 3);
  `CovData.average` uses the exact share. The difference is of order
  the noise of the averaged values times the difference of their rows.
- Two sets that share a scan cannot be joined as independent
  (`concat` refuses repeated labels). Their common scan's noise is in
  both.
- A transform that is **not** a per-point multiplication (a background
  subtracted from y, a resolution deconvolution, an interpolation onto a
  new grid) is not covered by Σ in log units. A background turns part
  of the multiplicative error additive. Interpolation mixes rows: the
  new W is the interpolation matrix times W, and the new diagonal is no
  longer diagonal. The reader writes the points as measured (or
  averaged), so nothing of this kind happens between the reduction and
  the file.

## 4. What the foil prior and the monitor do to Σ

- **Foil prior** (the known absorber ratio, `patching.known_steps`):
  independent information about the steps, combined in step space
  (`uncertainty.combine`). It makes Σ smaller (−8 % on the last scan's
  level at NX counts, −50 % at low counts: joint-fit report table 4) and
  **correlated across joins**, because joins that change the same foil
  share its calibration error. Exported Σ is the posterior, so a
  downstream fit must **not** apply the foil ratios again. The legacy
  window's "Known ratio" choice replaces the fitted factor at one join
  by the foil ratio. In the legacy export that join's step is taken from
  the previous scan with the ratio's error, and the foil correlations
  between several such joins are **not** included (an assumption,
  `OUTPUT_DECISIONS.md`). The joint path's prior includes them.
- **Monitor (P29)**: where Monc misses part of a slit change, the
  scan's level changes by a factor the foils do not know. The **fitted**
  factor measures and absorbs it, so Σ from the fit stays right. The
  foil prior is then wrong, which is why `prior_mask` drops it at such
  joins: it is marginalised, not down-weighted, so it cannot leak into
  neighbouring joins through the correlations. If Monc's error is **not
  constant across a scan** (beam drifting through the slits along a
  scan), it is a slope or shape error within the scan, which Σ (one
  number per scan) cannot represent. The contract can carry it as a
  further multiplicative term with W[i, m] = (q_i − q̄_m)·[i ∈ m] and a
  per-scan slope variance (reasoned; not built: no measurement of the
  size yet).
- **Monitor noise per point** (P3, Gaussian 0.04 %, budget model) is
  independent from point to point and belongs in σ_meas. One finding
  on the way (measured): synthetic scans drawn with Poisson monitor
  counts but reduced with detector counting errors only gave GLS χ²/dof
  1.29 and joint-fit pulls 1.13–1.20. With the monitor term in σ_meas
  (`errors='counting+monitor'`) the numbers were 0.99 and 1.05. A
  covariance is only as good as its diagonal. With the legacy error
  model (P2: the monitor term per pixel), σ_meas carries P2's error.

## 5. What is lost with diagonal errors only, and what a fitter must check

Diagonal errors lose the common-mode structure. Folding Σ's diagonal
into each point (the hand-off's corrected column, √diag C) makes each
point's error right on its own (χ²/N of the curve against the truth ≈ 1,
joint-fit report table 6), but the fit then:

1. thinks it has N independent pieces of information about each scan's
   level, where it has one. The parameters that a level shift can mimic
   (the density, through the Fresnel edge and the level of the
   fringes; the roughness, through the high-Q slope across scans) are
   overconfident. Measured: pull SDs of 2–3 (§6);
2. reports χ²/dof ≈ 0.56, which looks deceptively good;
3. is **less accurate**, not just less honest: the RMS error of ρ is
   ×3 larger than with the covariance (§6), because the fit cannot let a
   scan's level float within Σ. It bends the structure to absorb the
   level error instead.

With the legacy column (each scan's own factor error folded per point,
not inherited) pulls are 1.7 / 3.3 / 4.2. With counting errors alone
they are 2.5 / 4.4 / 5.3 (§6).

**What a fitter must check** (the contract's §2.3, implemented as
`gls.problems` and `Sidecar.match_problems`):

- format and version (v1). Unknown keys are ignored; a new meaning is a
  new version;
- N: σ_meas, W rows and x have the data's length; W is N × K, Σ K × K,
  labels K;
- the **same points in the same order**: x and y equal the data file's
  columns within 1e-4 relative (the files carry %.4e). This catches a
  sidecar from another reduction, a file re-sorted or trimmed after
  writing, an `_rrf` sidecar paired with an `_ref` file (x differs by
  q_off, y by R_F), and a stale Q_z² file;
- σ_meas finite and > 0; Σ finite, symmetric, PSD; term names unique;
- use σ_meas **instead of** the file's error column when the covariance
  is used. Never add Σ to the file's column: the column already
  contains it (√diag C, or the legacy folding);
- fit ranges and masks select rows of x, y, σ_meas and W; Σ is never cut;
- in linear space build D from the model, not from y (D'Agostini 1994);
- fit the overall scale (§2.3), and do not re-apply the foil ratios
  when Σ already contains the prior (§4).

## 6. Measurements

Synthetic NX-like scans (`tests/synthetic/xrr_scans.nx_like_plan`: the
NX school grids, times, absorbers chosen automatically, slits opened ×2.7
and ×3.2 for the last two scans) of a 25 Å film (ρ 0.39 e/Å³, σ 3.5 Å)
on water, Poisson detector and monitor counts, reduced by each patch
method, written as the sidecar, read back, and fitted with
`gls.fit` for d, ρ, σ and a free overall scale, in log space. 300 seeds;
the SD of a pull SD from 300 draws is ≈ 0.04. Tool:
`python tests/tools/covariance_pulls.py --seeds 300 --nx`; output
`docs/comparisons_data/downstream_covariance/`.

**Table 1. Pull SD of d / ρ / σ; mean χ²/dof; RMS error of d (Å), ρ (e/Å³), σ (Å)** (measured)

| Patch | Errors used in the fit | Pull SD d / ρ / σ | χ²/dof | RMS d / ρ / σ |
|---|---|---|---|---|
| legacy | file column (legacy folding) | 1.71 / 3.26 / 4.15 | 0.84 | 0.026 / 5.2e-4 / 0.0093 |
| legacy | √diag C | 0.80 / 3.01 / 2.09 | 0.56 | 0.023 / 6.8e-4 / 0.0072 |
| legacy | counting only | 2.53 / 4.35 / 5.25 | 1.24 | 0.028 / 5.1e-4 / 0.0097 |
| legacy | **covariance (sidecar)** | **1.00 / 0.98 / 1.00** | **0.99** | **0.015 / 2.3e-4 / 0.0041** |
| corrected (hand-off §3.2) | √diag C (its file column) | 0.80 / 3.01 / 2.09 | 0.56 | 0.023 / 6.8e-4 / 0.0072 |
| corrected | **covariance** | **1.00 / 0.97 / 1.00** | 0.99 | 0.015 / 2.3e-4 / 0.0041 |
| joint (o4 e4, coincident points averaged) | √diag C | 0.83 / 2.67 / 2.01 | 0.56 | 0.022 / 5.6e-4 / 0.0063 |
| joint | **covariance** | **1.05 / 1.05 / 1.07** | 0.98 | **0.014 / 1.8e-4 / 0.0036** |

Findings (measured):
- With the covariance every method gives pull SDs within 0.97–1.07 and
  χ²/dof 0.98–0.99. Without it, no error column gives honest errors for
  all three parameters.
- With the covariance the parameters are also 2–3× more accurate (ρ:
  RMS 2.3e-4 against 5.2–6.8e-4).
- With the covariance, legacy and corrected factors give the same fit.
  The joint fit gives smaller Σ and the best accuracy (ρ RMS 1.8e-4).
  The covariance matters more than the factor estimator, as in the
  joint-fit report §5.1.
- Statistical sanity (hand-off §5.7, `test_statistical_sanity_of_sigma`):
  over 300 seeds the RMS of √Σ_mm is 1.08–1.11 × the true spread of ln f_m
  (inflate-only; XModJointFit measured 6–17 % above). Pull SDs are
  0.93–0.95, the same for the legacy factors with their recomputed
  errors.

**NX school scans 6–9** (public, budget errors, measured; `nx_sigma.csv`):
√Σ of scans 7, 8, 9: legacy factors 0.46, 0.92, 1.03 %; corrected 0.46,
0.92, 1.03 %; joint 0.38, 0.63, 0.75 % (as the joint-fit report §6.1).
The largest σ_total/σ_meas is 4.8 (legacy) and 5.5 (joint). At those
points the factor's error dominates, and it is the common part.

## 7. What was built

| Piece | Where | What it does |
|---|---|---|
| Covariance data and transforms | `lss_core/covariance_export.py` (`CovData`) | x, y, σ_meas, W, Σ; `take`/`sort`/`cut`, `scale`/`divide`, `shift_x`, `average`, `concat`; `sigma_total`, `covariance` |
| Legacy chain with W and Σ | `legacy_chain` | replays `reflectivity.patch` (same drops, same known factors), its data bit for bit; carries σ_meas and W (§3.1, §3.3); Σ by §3.4 from the legacy factors, their errors recomputed against counting errors, inflate-only |
| Corrected chain | `corrected_chain` | hand-off §3.1–3.4 exactly (an independent oracle written from the text agrees to 1e-10) |
| Joint fit | `joint_covdata` | `patching.chain` + `stitch(merge='coincident')` |
| Finishing | `finish` | `reflectivity.finish` (normalisation, sort, q_off, Fresnel) on x, y, σ_meas, W: the written arrays exactly |
| Files | `sidecar_dict`, `write_sidecar`, `save` | schema v1; `<name>_ref.cov.json`/`_rrf.cov.json`; the contract's two outputs (`_legacy` files); the combined `.json` (§2.6) |
| Reading and fitting | `lss_core/gls.py` | `load`/`problems`/`match_problems` (XModFit's §2.3 checks), `LowRank` (Woodbury), `chi2` (free scale in closed form), `fit` (nuisance form, log or linear, free scale, masks, diagonal mode for comparisons; returns the per-scan shifts) |
| Script | `ReflectivityResult.covariance(method)`, `.save(name, covariance=None/'sidecar'/'contract', method=…, combined=…)` | see below |
| Window | Ref Patch: "+ covariance" box beside Export/Save, off by default | writes the sidecars beside the unchanged text files; nothing if the patch cannot be replayed exactly (T10) |
| Tool | `tests/tools/covariance_pulls.py` | §6 |

Script:

    from lss_core.experiment import Experiment
    from lss_core import gls
    exp = Experiment('sample_data/NX_school/2026sep/20260923')
    res = exp.reflectivity([6, 7, 8, 9], errors='budget')
    res.save('dppc')                                  # as before: legacy files only
    res.save('dppc', covariance='sidecar')            # + dppc_ref.cov.json, dppc_rrf.cov.json (files unchanged)
    res.save('dppc', covariance='contract')           # hand-off §2.5: corrected _ref/_rrf + sidecars + _legacy files
    res.save('dppc', covariance='contract', method='joint', combined=True)
    ref, rrf = res.covariance('joint')                # CovData in memory
    sc = gls.load('dppc_rrf.cov.json')
    fit = gls.fit(sc, model, p0)                      # model(x, *p) -> R/R_F; free overall scale
    fit.params, fit.errors, fit.chi2, fit.dof, fit.shifts['stitch']

Window: Reflectivity tab, tick "+ covariance" next to Export, then
Export. The `_ref.txt`/`_rrf.txt` bytes do not change
(`tests/test_gui_covariance_export.py` checks them against the legacy
fixtures).

## 8. Decisions left to the owner (TODO area B2)

1. Is the window's covariance option on by default, and which layout
   does it write: sidecars beside the legacy files (built, off), or the
   contract's two outputs (corrected `_ref.txt` with √diag C, legacy files
   as `_legacy`; built for scripts only)? The contract asks for the
   latter. It changes `_ref.txt`'s numbers, which is the owner's call
   (F24a).
2. For the legacy method, Σ from the legacy factors with errors
   recomputed against counting errors (built). The alternative is the
   legacy `absolute_sigma=False` error, recorded in the provenance as
   `facerr_legacy`. On two synthetic sets (one seed each) the legacy
   error was 0.28–0.72 % and the recomputed one 0.44–0.77 %; the
   legacy error's pull SD was 1.49 at the first join (joint-fit report
   table 1).
3. The joint method's output points: averaged where Q_z coincide
   (built default, as the joint-fit report recommends), or every point
   as measured (duplicates in Q_z).
4. Whether to write the combined `.json` (§2.6) by default once
   XModFit's loader exists.
5. Whether a monitor-slope term (§4) is worth measuring for.

## 9. References (cited from memory; not re-checked in this session)

- A. C. Aitken, "On least squares and linear combination of
  observations", Proc. R. Soc. Edinburgh 55 (1935) 42,
  https://doi.org/10.1017/S0370164600014346 — generalised least squares.
- W. W. Hager, "Updating the inverse of a matrix", SIAM Review 31 (1989)
  221, https://doi.org/10.1137/1031049 — the Woodbury identity.
- G. D'Agostini, "On the use of the covariance matrix to fit correlated
  data", Nucl. Instrum. Meth. A 346 (1994) 306,
  https://doi.org/10.1016/0168-9002(94)90719-6 — normalisation errors;
  build the covariance on the model (or in log space), not the data.
- R. Barlow, "Systematic errors: facts and fictions" (2002),
  https://arxiv.org/abs/hep-ex/0207026 — what is and is not a
  systematic error, and how to treat it.
- D. Stump et al., "Uncertainties of predictions from parton
  distribution functions I", Phys. Rev. D 65 (2001) 014012,
  https://arxiv.org/abs/hep-ph/0101051 — correlated systematic shifts
  as fitted parameters, equivalent to the covariance χ².
- G. L. Fogli et al., "Getting the most from the statistical analysis
  of solar neutrino oscillations", Phys. Rev. D 66 (2002) 053010,
  https://arxiv.org/abs/hep-ph/0206162 — the covariance and "pull"
  forms of χ² are equivalent.
- The contract: `docs/handoff/19-lss-reader-covariance-contract.md`
  (requirements), and the joint-fit design `docs/reports/
  ref_patch_joint_fit.md`.
