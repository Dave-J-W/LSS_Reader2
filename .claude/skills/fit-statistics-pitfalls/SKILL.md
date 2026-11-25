---
name: fit-statistics-pitfalls
description: Checklist of statistical traps met (and measured) in LSS_Reader2's fits and tests, each with its symptom and fix - chi2 with a model-dependent variance, drift rates from y instead of ln y, robust-loss false minima, strip/group scatter by REML, single-seed interval tests, goodness-of-fit vs likelihood-ratio p-values, ties ordered by set iteration, errors scaled by sqrt(chi2/dof). Use before trusting or committing any new fit, estimator, interval or verdict, and when a test of a statistical method fails "by a hair".
---

# Fit and statistics pitfalls (measured in this repository)

Each entry: the symptom you will see, why it happens, the fix, and where it was found.

1. **χ² with a variance that depends on the model.**
   - *Symptom:* an interval narrower than with counting errors alone, after adding a scatter term
     (C54's R11-S1 at ρ 1.13: 0.72 [0.68, 0.76]).
   - *Why:* minimising Σ(r − m)²/v, with v growing with m, lets the fit inflate m's own variance to shrink
     χ².
   - *Fix:* minimise −2 log L = Σ(r − m)²/v + Σ log v, and use likelihood-ratio tests for verdicts.
     After the fix: 0.52 [0.16, 0.96]. `lss_core.reciprocity._profile`, 2026-11-25.
2. **Goodness-of-fit p at a fitted variance.**
   - The Pearson χ² at the likelihood's best k is not χ²(n − 1). Used as a p-value, it rejects the true
     law too often: dose calls fell from 0.55 to 0.30 at 50 % strip scatter.
   - *Fix:* likelihood ratio against the best value (Δ(−2 log L) ~ χ²(1)). Calls then rose to 0.80.
3. **A straight line through y for an exponential change.**
   - The slope reads a fast fall low, which biased β low in F76.
   - *Fix:* fit ln y for intensity and width (relative changes); fit y for a position.
4. **Scale the errors by √(χ²/dof) when it is above 1,** never below. A χ²/dof of 2.7 with a patterned
   residual (NX burn 15) also says the model is too simple. Report both: scaling hides the misfit.
5. **Robust losses have false minima.**
   - Tukey's loss alone "explained away" the two edge points of a Qoff fit (4 of 6 replicates).
   - *Fix:* find the basin with Huber first, then apply Tukey within ±10 grid steps. `fresnel.propose_qoff`.
6. **Group-to-group scatter: estimate it, and choose its form by likelihood.**
   - Repeated strips of one sample disagreed by 5–10σ.
   - *Fix:* REML of the one-way random-effects model (`reciprocity.strip_scatter_fit`). Compare additive
     against relative by −log L with the same number of parameters: 73.6 against 54.2 for C54.
   - The wrong form can hide effects: one additive τ hid 5 rise-and-fall series.
7. **Pool repeats before sign and significance rules.** Single strips at one flux that rise and fall are
   the scatter, not two processes ("opposite signs" in 72 % of seeds before pooling, 0 % after).
8. **Never test a 95 % interval on one seed.** It fails 1 time in 20 by design (it failed by 0.01 after a
   correct fix). Test coverage over 60 or more seeds against a binomial bound (at least 53 of 60), and
   say so in the commit (rule 1: this strengthens the test).
9. **Coverage collapses with few groups and a large scatter.** At ρ 1 with four burns the 95 % interval
   covers 0.87. Say that single verdicts are overconfident, rather than quoting them bare.
10. **Ties ordered by a set change from run to run.**
    - `sorted(set(...), key=value)` keeps set (hash) order among equal keys, and that order changes per
      process. MCA study B3 rows came out reordered; the Tools audit found it.
    - *Fix:* key=(value, name).
11. **Linear grids for scale parameters.** One huge value (a rate of −9483 %/h) makes a linear grid
    coarse, and the estimate moved from 90 to 95. Use 0 plus a log-spaced grid.
12. **Check every quoted number against the tool's output** before committing. Prose written from memory
    drifts: "≈ 2σ" was 2.8σ, "300 million" was 270 million.
