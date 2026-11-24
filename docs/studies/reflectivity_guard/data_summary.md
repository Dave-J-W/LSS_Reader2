# Study A, reflectivity guard: the numbers behind the figures

Made by `tests/tools/ref_guard_study.py` (its docstring says what each choice is). All numbers below are measured by that run; nothing here is read from elsewhere except the C45 check.

## How this was made

Command line: `python tests/tools/ref_guard_study.py`

- Replicates per join: 400 (gauntlet seeds for the five biased joins; seeds 0 … 399 for the first join of the covariance study).
- Processes: 4. Total wall time: 48 s.
- The AICc average (a candidate, never a default): Akaike weights w_k ∝ exp(−ΔAICc_k/2), AICc = χ² + 2K + 2K(K+1)/(n−K−1), K = order + 2, over the rungs of the ladder's largest window (the same points); δ̄ = Σ w_k δ_k, σ² = Σ w_k (σ_k² + (δ_k − δ̄)²): Burnham & Anderson 2002 (eq. 6.12), the revised form of Buckland et al. 1997.

- six joins (draws, rung tables, checks): 5.1 s
- A5 precision run (2000 replicates per join): 19.1 s
- A2–A6 figures: 4.3 s
- A1: 1.1 s
- A7 and A7b (200 seeds each): 9.0 s
- A8: 0.4 s
- R (800 replicates per cell): 8.7 s

## C45 reproduced first

C45 reproduced exactly: 180 of 180 committed values (default, guard_off, guard_0.01: n, failed, mean pull, pull SD, bias, RMS, median error, noise-free bias and rung, six joins; the first join over its 300 seeds) agree to all six printed digits (docs/comparisons_data/ref_patch_biased_joins/joins.csv).

The stored-rung selection against `patching.joint_factor` itself (the first 10 replicates of each join, every p of the sweep and the guard off):

| join | cases | mismatches |
|---|---|---|
| layer_dppc j3 | 90 | 0 |
| layer_film150 j2 | 90 | 0 |
| overlap_3_staggered j3 | 90 | 0 |
| overlap_6 j1 | 90 | 0 |
| scans_5 j2 | 90 | 0 |
| covariance j1 (smooth) | 90 | 0 |

## A2. Pulls per join and choice

Mean pull / pull SD (n = 400 per join; failures in brackets when any).

| join | legacy | p 0.3 (default) | p 0.1 | p 0.03 | p 0.01 | guard off | AICc average |
|---|---|---|---|---|---|---|---|
| layer_dppc j3 | +0.06 / 2.00 | -0.21 / 1.18 | -0.42 / 1.19 | -0.59 / 1.13 | -0.68 / 1.07 | +0.42 / 0.29 | -0.80 / 0.86 |
| layer_film150 j2 | -0.21 / 1.68 | -0.31 / 1.03 | -0.48 / 1.00 | -0.62 / 0.94 | -0.70 / 0.88 | -0.44 / 0.09 | -0.94 / 0.66 |
| overlap_3_staggered j3 | +5.89 / 134.86 | +0.25 / 0.88 | +0.25 / 0.88 | +0.25 / 0.88 | +0.25 / 0.88 | +0.25 / 0.88 | +0.25 / 0.88 |
| overlap_6 j1 | -0.09 / 1.43 | +0.24 / 1.08 | +0.39 / 1.01 | +0.48 / 0.91 | +0.51 / 0.89 | +0.55 / 0.83 | +0.43 / 0.95 |
| scans_5 j2 | -0.06 / 1.63 | -0.33 / 1.07 | -0.45 / 1.04 | -0.56 / 0.97 | -0.61 / 0.93 | -0.02 / 0.32 | -0.65 / 0.90 |
| covariance j1 (smooth) | -0.05 / 1.58 | +0.02 / 1.08 | +0.01 / 1.02 | +0.01 / 1.01 | +0.01 / 1.01 | +0.01 / 1.00 | +0.01 / 1.00 |

The rest of the p sweep, and two forms of the average for comparison only: the same Akaike weights with Buckland et al. 1997's own σ = Σ w_k √(σ_k² + (δ_k − δ̄)²), and the average over every window (its weights compare χ² of different data):

| join | p 0.001 | p 0.003 | p 0.2 | p 0.5 | AICc average, Buckland's σ | AICc average, all windows |
|---|---|---|---|---|---|---|
| layer_dppc j3 | -0.81 / 0.97 | -0.76 / 1.01 | -0.28 / 1.19 | -0.09 / 1.11 | -0.80 / 0.87 | +0.00 / 0.99 |
| layer_film150 j2 | -0.82 / 0.79 | -0.77 / 0.84 | -0.38 / 1.01 | -0.22 / 1.00 | -0.94 / 0.67 | -0.06 / 0.65 |
| overlap_3_staggered j3 | +0.25 / 0.88 | +0.25 / 0.88 | +0.25 / 0.88 | +0.25 / 0.88 | +0.25 / 0.88 | +0.25 / 0.88 |
| overlap_6 j1 | +0.54 / 0.84 | +0.52 / 0.86 | +0.31 / 1.06 | +0.14 / 1.08 | +0.43 / 0.95 | -0.03 / 0.99 |
| scans_5 j2 | -0.64 / 0.91 | -0.63 / 0.92 | -0.39 / 1.07 | -0.24 / 1.08 | -0.65 / 0.90 | -0.05 / 0.90 |
| covariance j1 (smooth) | +0.01 / 1.00 | +0.02 / 1.01 | +0.01 / 1.04 | +0.02 / 1.09 | +0.01 / 1.00 | +0.01 / 1.00 |

Bias of δ (×10⁻³) and median error σ̂ (×10⁻³):

| join | legacy | p 0.3 (default) | p 0.1 | p 0.03 | p 0.01 | guard off | AICc average |
|---|---|---|---|---|---|---|---|
| layer_dppc j3 | -0.78 / 12.20 | -2.52 / 14.10 | -5.74 / 14.20 | -8.73 / 15.25 | -10.43 / 15.67 | +17.73 / 42.38 | -13.24 / 18.33 |
| layer_film150 j2 | -1.29 / 9.24 | -2.85 / 10.34 | -4.89 / 10.50 | -6.88 / 11.45 | -8.53 / 12.40 | -43.81 / 100.42 | -15.32 / 16.91 |
| overlap_3_staggered j3 | -2.16 / 7.26 | +2.11 / 7.98 | +2.11 / 7.98 | +2.11 / 7.98 | +2.11 / 7.98 | +2.11 / 7.98 | +2.11 / 7.98 |
| overlap_6 j1 | -0.17 / 3.04 | +0.72 / 3.12 | +1.28 / 3.34 | +1.69 / 3.59 | +1.87 / 3.72 | +2.20 / 3.98 | +1.47 / 3.35 |
| scans_5 j2 | -0.55 / 5.53 | -1.79 / 5.75 | -2.56 / 5.76 | -3.31 / 5.79 | -3.69 / 5.87 | -0.35 / 17.09 | -4.09 / 5.89 |
| covariance j1 (smooth) | -0.13 / 4.02 | +0.10 / 4.30 | +0.04 / 4.30 | +0.04 / 4.30 | +0.05 / 4.30 | +0.06 / 4.30 | +0.06 / 4.30 |

## A1. What the fit sees

Replicates 0–5 of each join type; the default's chosen rung (p 0.3) and its pull.

| type | join | replicate | rung | p | pull | f̂ (default) | f̂ (guard off) |
|---|---|---|---|---|---|---|---|
| smooth | covariance j1 (smooth) | 0 | o7 ±2 | 0.44 | +3.12 | 0.02343 | 0.02340 |
| smooth | covariance j1 (smooth) | 1 | o4 ±2 | 0.97 | +0.31 | 0.02314 | 0.02314 |
| smooth | covariance j1 (smooth) | 2 | o6 ±2 | 0.74 | -2.11 | 0.02288 | 0.02294 |
| smooth | covariance j1 (smooth) | 3 | o4 ±2 | 0.45 | -0.21 | 0.02308 | 0.02308 |
| smooth | covariance j1 (smooth) | 4 | o4 ±2 | 0.92 | -1.31 | 0.02298 | 0.02298 |
| smooth | covariance j1 (smooth) | 5 | o4 ±0 inflated | 0.14 | +0.58 | 0.02322 | 0.02301 |
| fringe | layer_dppc j3 | 0 | o7 ±2 | 0.99 | +0.63 | 0.00681 | 0.00691 |
| fringe | layer_dppc j3 | 1 | o7 ±2 | 0.81 | +0.03 | 0.00675 | 0.00676 |
| fringe | layer_dppc j3 | 2 | o6 ±2 inflated | 0.25 | -1.18 | 0.00663 | 0.00685 |
| fringe | layer_dppc j3 | 3 | o2 ±0 | 0.39 | +0.44 | 0.00679 | 0.00693 |
| fringe | layer_dppc j3 | 4 | o2 ±0 inflated | 0.09 | +0.03 | 0.00675 | 0.00682 |
| fringe | layer_dppc j3 | 5 | o7 ±2 | 0.49 | +0.94 | 0.00683 | 0.00691 |
| staggered | overlap_3_staggered j3 | 0 | o4 ±2 | 0.61 | -0.37 | 0.01518 | 0.01518 |
| staggered | overlap_3_staggered j3 | 1 | o4 ±2 inflated | 0.19 | +0.14 | 0.01525 | 0.01525 |
| staggered | overlap_3_staggered j3 | 2 | o4 ±2 | 0.82 | +0.12 | 0.01524 | 0.01524 |
| staggered | overlap_3_staggered j3 | 3 | o4 ±2 | 0.81 | +0.94 | 0.01534 | 0.01534 |
| staggered | overlap_3_staggered j3 | 4 | o4 ±2 | 0.82 | +1.43 | 0.01540 | 0.01540 |
| staggered | overlap_3_staggered j3 | 5 | o4 ±2 | 0.61 | +2.22 | 0.01550 | 0.01550 |

## A3. Noise-free bias

In median errors of each choice, with the rung chosen on noise-free data (order, points either side).

| join | legacy | p 0.3 (default) | p 0.1 | p 0.03 | p 0.01 | guard off | AICc average |
|---|---|---|---|---|---|---|---|
| layer_dppc j3 | -0.00 (, ) | -1.03 (6, 2) | -1.03 (6, 2) | -0.96 (6, 2) | -0.93 (6, 2) | +0.42 (4, 2) | -0.79 (, ) |
| layer_film150 j2 | +0.00 (, ) | -0.64 (6, 2) | -0.63 (6, 2) | -0.57 (6, 2) | -0.53 (6, 2) | -0.42 (4, 2) | -1.01 (, ) |
| overlap_3_staggered j3 | -0.26 (, ) | +0.27 (4, 2) | +0.27 (4, 2) | +0.27 (4, 2) | +0.27 (4, 2) | +0.27 (4, 2) | +0.27 (, ) |
| overlap_6 j1 | +0.00 (, ) | +0.73 (4, 2) | +0.68 (4, 2) | +0.64 (4, 2) | +0.61 (4, 2) | +0.57 (4, 2) | +0.52 (, ) |
| scans_5 j2 | +0.00 (, ) | -0.63 (5, 2) | -0.62 (5, 2) | -0.62 (5, 2) | -0.61 (5, 2) | +0.01 (4, 2) | -0.61 (, ) |
| covariance j1 (smooth) | -0.03 (, ) | +0.00 (4, 2) | +0.00 (4, 2) | +0.00 (4, 2) | +0.00 (4, 2) | +0.00 (4, 2) | +0.00 (, ) |

## A4. The guard's rung choices

Share, mean pull and pull SD of the replicates on each rung (shares ≥ 2 %).

| join | p | rung | inflated | share | mean pull | pull SD |
|---|---|---|---|---|---|---|
| layer_dppc j3 | 0.3 | o6 ±2 |  | 0.280 | -1.26 | 0.96 |
| layer_dppc j3 | 0.3 | o7 ±2 |  | 0.432 | +0.39 | 1.01 |
| layer_dppc j3 | 0.3 | o6 ±2 | yes | 0.025 | -0.99 | 0.92 |
| layer_dppc j3 | 0.3 | o5 ±1 | yes | 0.028 | +0.16 | 0.54 |
| layer_dppc j3 | 0.3 | o2 ±0 |  | 0.052 | +0.08 | 1.29 |
| layer_dppc j3 | 0.3 | o2 ±0 | yes | 0.135 | -0.08 | 0.73 |
| layer_dppc j3 | 0.3 | o3 ±0 | yes | 0.030 | -0.05 | 0.93 |
| layer_dppc j3 | 0.01 | o6 ±2 |  | 0.807 | -0.98 | 0.89 |
| layer_dppc j3 | 0.01 | o7 ±2 |  | 0.165 | +0.67 | 0.86 |
| layer_film150 j2 | 0.3 | o5 ±2 |  | 0.020 | -2.29 | 0.85 |
| layer_film150 j2 | 0.3 | o6 ±2 |  | 0.410 | -0.86 | 0.87 |
| layer_film150 j2 | 0.3 | o7 ±2 |  | 0.292 | +0.33 | 0.89 |
| layer_film150 j2 | 0.3 | o6 ±2 | yes | 0.060 | -0.61 | 0.68 |
| layer_film150 j2 | 0.3 | o7 ±2 | yes | 0.050 | +0.28 | 0.53 |
| layer_film150 j2 | 0.3 | o5 ±1 | yes | 0.072 | +0.10 | 0.75 |
| layer_film150 j2 | 0.3 | o3 ±0 | yes | 0.075 | +0.13 | 0.75 |
| layer_film150 j2 | 0.01 | o5 ±2 |  | 0.240 | -1.37 | 0.69 |
| layer_film150 j2 | 0.01 | o6 ±2 |  | 0.685 | -0.58 | 0.79 |
| layer_film150 j2 | 0.01 | o7 ±2 |  | 0.060 | +0.45 | 0.65 |
| overlap_3_staggered j3 | 0.3 | o4 ±2 |  | 0.632 | +0.31 | 0.98 |
| overlap_3_staggered j3 | 0.3 | o4 ±2 | yes | 0.367 | +0.14 | 0.66 |
| overlap_3_staggered j3 | 0.01 | o4 ±2 |  | 0.983 | +0.25 | 0.88 |
| overlap_6 j1 | 0.3 | o4 ±2 |  | 0.158 | +0.53 | 1.03 |
| overlap_6 j1 | 0.3 | o5 ±2 |  | 0.455 | +0.49 | 1.08 |
| overlap_6 j1 | 0.3 | o6 ±2 |  | 0.138 | -0.23 | 0.95 |
| overlap_6 j1 | 0.3 | o7 ±2 |  | 0.048 | -0.63 | 0.98 |
| overlap_6 j1 | 0.3 | o5 ±2 | yes | 0.022 | +0.64 | 1.31 |
| overlap_6 j1 | 0.3 | o6 ±1 |  | 0.022 | -0.34 | 1.27 |
| overlap_6 j1 | 0.3 | o7 ±1 |  | 0.020 | +0.07 | 1.26 |
| overlap_6 j1 | 0.3 | o4 ±1 | yes | 0.037 | -0.17 | 0.86 |
| overlap_6 j1 | 0.01 | o4 ±2 |  | 0.765 | +0.59 | 0.87 |
| overlap_6 j1 | 0.01 | o5 ±2 |  | 0.212 | +0.28 | 0.92 |
| scans_5 j2 | 0.3 | o5 ±2 |  | 0.497 | -0.76 | 0.99 |
| scans_5 j2 | 0.3 | o6 ±2 |  | 0.200 | +0.29 | 1.00 |
| scans_5 j2 | 0.3 | o7 ±2 |  | 0.052 | +0.08 | 1.50 |
| scans_5 j2 | 0.3 | o5 ±2 | yes | 0.052 | -0.35 | 0.86 |
| scans_5 j2 | 0.3 | o6 ±2 | yes | 0.050 | -0.11 | 0.68 |
| scans_5 j2 | 0.3 | o7 ±2 | yes | 0.028 | +0.24 | 0.52 |
| scans_5 j2 | 0.3 | o4 ±1 | yes | 0.043 | -0.10 | 1.03 |
| scans_5 j2 | 0.3 | o5 ±1 | yes | 0.020 | +0.10 | 0.83 |
| scans_5 j2 | 0.3 | o2 ±0 | yes | 0.028 | +0.04 | 0.67 |
| scans_5 j2 | 0.3 | o3 ±0 | yes | 0.028 | +0.18 | 0.69 |
| scans_5 j2 | 0.01 | o5 ±2 |  | 0.945 | -0.67 | 0.91 |
| scans_5 j2 | 0.01 | o6 ±2 |  | 0.045 | +0.40 | 0.65 |
| covariance j1 (smooth) | 0.3 | o4 ±2 |  | 0.735 | +0.01 | 1.05 |
| covariance j1 (smooth) | 0.3 | o5 ±2 |  | 0.058 | -0.26 | 1.19 |
| covariance j1 (smooth) | 0.3 | o6 ±2 |  | 0.040 | +0.33 | 1.11 |
| covariance j1 (smooth) | 0.3 | o7 ±2 |  | 0.030 | +0.17 | 1.45 |
| covariance j1 (smooth) | 0.3 | o4 ±2 | yes | 0.055 | +0.10 | 0.93 |
| covariance j1 (smooth) | 0.3 | o6 ±1 |  | 0.025 | +0.31 | 1.80 |
| covariance j1 (smooth) | 0.01 | o4 ±2 |  | 0.990 | +0.01 | 1.01 |

Mean Akaike weight of each rung in the AICc average (largest window), and of each window in the average over all windows (comparison only):

| join | AICc average: weight per rung | all windows: weight per window (points either side) |
|---|---|---|
| layer_dppc j3 | o6 ±2: 0.92, o5 ±2: 0.08 | ±2: 0.00, ±1: 0.00, ±0: 1.00 |
| layer_film150 j2 | o5 ±2: 0.79, o6 ±2: 0.21 | ±2: 0.00, ±1: 0.00, ±0: 1.00 |
| overlap_3_staggered j3 | o4 ±2: 1.00 | ±2: 1.00 |
| overlap_6 j1 | o5 ±2: 0.53, o4 ±2: 0.41, o6 ±2: 0.06 | ±2: 0.01, ±1: 0.02, ±0: 0.97 |
| scans_5 j2 | o5 ±2: 1.00 | ±2: 0.00, ±1: 0.00, ±0: 1.00 |
| covariance j1 (smooth) | o4 ±2: 1.00 | ±2: 0.01, ±1: 0.00, ±0: 0.99 |

## A5. The decision curve

x: pull SD at the smooth first join; y: mean |pull mean| over the five biased joins; ± bootstrap SE (500 resamples of the replicates; the difference from the guard off resamples the same replicates for both). Also the mean pull SD over the biased joins. 400 replicates per join (the figure).

| choice | first-join pull SD | minus the guard off's (paired) | mean |pull mean| (biased) | mean pull SD (biased) |
|---|---|---|---|---|
| p 0.001 | 1.005 ± 0.039 | +0.000 ± 0.000 | 0.613 ± 0.019 | 0.879 |
| p 0.003 | 1.005 ± 0.039 | +0.001 ± 0.001 | 0.585 ± 0.020 | 0.902 |
| p 0.01 | 1.008 ± 0.039 | +0.003 ± 0.003 | 0.551 ± 0.020 | 0.930 |
| p 0.03 | 1.014 ± 0.039 | +0.009 ± 0.006 | 0.501 ± 0.021 | 0.964 |
| p 0.1 | 1.023 ± 0.039 | +0.018 ± 0.008 | 0.399 ± 0.022 | 1.021 |
| p 0.2 | 1.045 ± 0.038 | +0.040 ± 0.011 | 0.323 ± 0.023 | 1.042 |
| p 0.3 (default) | 1.077 ± 0.039 | +0.072 ± 0.016 | 0.269 ± 0.023 | 1.048 |
| p 0.5 | 1.094 ± 0.039 | +0.090 ± 0.019 | 0.188 ± 0.022 | 1.030 |
| guard off | 1.005 ± 0.039 | +0.000 ± 0.000 | 0.337 ± 0.012 | 0.481 |
| legacy | 1.585 ± 0.127 | +0.580 ± 0.111 | 1.262 ± 1.150 | 28.320 |
| AICc average | 1.005 ± 0.039 | +0.000 ± 0.000 | 0.615 ± 0.018 | 0.850 |

### The same with 2000 replicates per join (precision check)

The same seeds continued (the first 400 are the figure's). With 300 seeds C45 found the first join's pull SD 1.13 at p 0.3 and 1.05 with the guard off; the table shows how much of that was sampling.

| choice | first-join pull SD | minus the guard off's (paired) | mean |pull mean| (biased) | mean pull SD (biased) |
|---|---|---|---|---|
| p 0.001 | 0.918 ± 0.016 | +0.000 ± 0.000 | 0.588 ± 0.008 | 0.859 |
| p 0.003 | 0.918 ± 0.016 | +0.000 ± 0.000 | 0.563 ± 0.008 | 0.882 |
| p 0.01 | 0.922 ± 0.016 | +0.004 ± 0.002 | 0.521 ± 0.009 | 0.915 |
| p 0.03 | 0.930 ± 0.015 | +0.012 ± 0.003 | 0.468 ± 0.009 | 0.950 |
| p 0.1 | 0.949 ± 0.015 | +0.031 ± 0.005 | 0.368 ± 0.010 | 0.997 |
| p 0.2 | 0.975 ± 0.016 | +0.057 ± 0.007 | 0.289 ± 0.010 | 1.016 |
| p 0.3 (default) | 1.001 ± 0.016 | +0.083 ± 0.008 | 0.237 ± 0.010 | 1.021 |
| p 0.5 | 1.027 ± 0.016 | +0.110 ± 0.010 | 0.162 ± 0.010 | 1.004 |
| guard off | 0.918 ± 0.016 | +0.000 ± 0.000 | 0.329 ± 0.006 | 0.473 |
| legacy | 1.473 ± 0.062 | +0.556 ± 0.056 | 0.286 ± 0.244 | 14.126 |
| AICc average | 0.918 ± 0.016 | +0.000 ± 0.000 | 0.593 ± 0.008 | 0.834 |

The first join's pull SD in consecutive blocks of 400 seeds (the first block is the figure's):

| choice | seeds 0–399 | seeds 400–799 | seeds 800–1199 | seeds 1200–1599 | seeds 1600–1999 |
|---|---|---|---|---|---|
| guard off | 1.005 | 0.915 | 0.875 | 0.882 | 0.904 |
| p 0.3 (default) | 1.077 | 1.010 | 0.944 | 0.995 | 0.971 |

Why the guard off's pull SD is below 1 there: with its counting error alone (no inflation) it is 0.978; the inflate-only rule max(1, √(χ²/dof)) enlarges the error in 41 % of the replicates, by ×1.226 on average among those (2000 replicates).

## A6. Coverage

Share of |pull| < 1 / share of |pull| < 2 (targets 0.683 / 0.954).

| group | legacy | p 0.3 (default) | p 0.1 | p 0.03 | p 0.01 | guard off | AICc average |
|---|---|---|---|---|---|---|---|
| pooled | 0.582 / 0.837 | 0.649 / 0.931 | 0.639 / 0.933 | 0.638 / 0.936 | 0.639 / 0.936 | 0.840 / 0.980 | 0.637 / 0.943 |
| layer_dppc j3 | 0.575 / 0.850 | 0.598 / 0.905 | 0.568 / 0.882 | 0.532 / 0.882 | 0.535 / 0.880 | 0.975 / 1.000 | 0.583 / 0.907 |
| layer_film150 j2 | 0.605 / 0.880 | 0.650 / 0.940 | 0.613 / 0.938 | 0.608 / 0.945 | 0.598 / 0.945 | 1.000 / 1.000 | 0.542 / 0.958 |
| overlap_3_staggered j3 | 0.537 / 0.730 | 0.728 / 0.970 | 0.728 / 0.970 | 0.728 / 0.970 | 0.728 / 0.970 | 0.728 / 0.970 | 0.728 / 0.970 |
| overlap_6 j1 | 0.573 / 0.882 | 0.623 / 0.927 | 0.640 / 0.940 | 0.660 / 0.948 | 0.662 / 0.948 | 0.677 / 0.958 | 0.652 / 0.950 |
| scans_5 j2 | 0.635 / 0.833 | 0.657 / 0.907 | 0.625 / 0.917 | 0.637 / 0.920 | 0.642 / 0.922 | 0.990 / 1.000 | 0.647 / 0.922 |
| covariance j1 (smooth) | 0.568 / 0.845 | 0.640 / 0.935 | 0.660 / 0.950 | 0.665 / 0.950 | 0.667 / 0.953 | 0.670 / 0.953 | 0.670 / 0.953 |

## A7. Downstream fit

Two cases, seeds 0 … 199 each. **A7** (as asked): NX-like plan, 25 Å film (ρ 0.39 e/Å³, σ 3.5 Å), the owner's monitor, the covariance study's seeds. **A7b** (added: a case where the join choice matters): the gauntlet's layer_film150 (150 Å film, ρ 0.383 e/Å³, σ 3.0 Å, four coinciding scans; its join 2 is one of the biased joins), the gauntlet's seeds. Each choice's join factors and errors are chained (`uncertainty.steps_to_phi`), stitched (`PatchResult.stitch`, coincident points merged), finished and fitted by `gls.fit` with the full covariance and a free scale, as `tests/tools/covariance_pulls.py`, starting from truth × (1.02, 0.99, 1.03). Bias, SD and RMS in Å; pulls against the fit's own errors.

| case | choice | failed | d bias | d SD | d RMS | d pull mean / SD | σ bias | σ SD | σ RMS | σ pull mean / SD | ρ pull SD | χ²/dof |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A7 (25 Å) | p 0.3 (default) | 0 | -0.0009 | 0.0140 | 0.0140 | -0.07 / 1.06 | -0.0005 | 0.0032 | 0.0033 | -0.15 / 0.99 | 0.96 | 1.002 |
| A7 (25 Å) | guard off | 0 | -0.0008 | 0.0141 | 0.0141 | -0.06 / 1.07 | -0.0005 | 0.0033 | 0.0033 | -0.15 / 1.00 | 0.96 | 0.995 |
| A7 (25 Å) | p 0.01 | 0 | -0.0008 | 0.0141 | 0.0141 | -0.06 / 1.07 | -0.0005 | 0.0033 | 0.0033 | -0.15 / 1.00 | 0.96 | 0.995 |
| A7 (25 Å) | AICc average | 0 | -0.0008 | 0.0141 | 0.0141 | -0.06 / 1.07 | -0.0005 | 0.0033 | 0.0033 | -0.15 / 1.00 | 0.96 | 0.995 |
| A7 (25 Å) | legacy | 0 | -0.0008 | 0.0146 | 0.0146 | -0.06 / 1.13 | -0.0004 | 0.0034 | 0.0034 | -0.13 / 1.07 | 1.06 | 1.020 |
| A7b (150 Å) | p 0.3 (default) | 0 | +0.0007 | 0.0239 | 0.0238 | +0.03 / 0.96 | +0.0000 | 0.0063 | 0.0063 | +0.00 / 0.90 | 1.00 | 1.001 |
| A7b (150 Å) | guard off | 0 | +0.0007 | 0.0239 | 0.0238 | +0.03 / 0.96 | +0.0000 | 0.0066 | 0.0066 | +0.00 / 0.92 | 1.00 | 0.961 |
| A7b (150 Å) | p 0.01 | 0 | +0.0006 | 0.0239 | 0.0239 | +0.03 / 0.97 | +0.0001 | 0.0063 | 0.0063 | +0.01 / 0.90 | 1.00 | 1.000 |
| A7b (150 Å) | AICc average | 0 | +0.0006 | 0.0239 | 0.0238 | +0.03 / 0.97 | +0.0001 | 0.0063 | 0.0063 | +0.01 / 0.90 | 1.00 | 1.000 |
| A7b (150 Å) | legacy | 0 | +0.0007 | 0.0239 | 0.0238 | +0.03 / 0.96 | +0.0003 | 0.0069 | 0.0069 | +0.04 / 1.07 | 1.18 | 1.069 |

## A8. NX school, scans 6–9

Factor ± error per choice beside the calibrated foil ratio (`absorbers.calibrated`, `Foils.step` at the overlap's lowest Qz). z = (ln f̂ − ln f_foil)/√(σ̂² + σ_foil²). The foil ratio is independent of the data only where Monc/Monp stays within 3 % across the join (P29); joins 2 and 3 open the slits.

| join | absorbers | Monc/Monp | foil ratio | choice | factor | rung | z | within 1σ | within 2σ |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 41 → 31 | 1.005 | 0.02311 ± 1.55 % | legacy | 0.02293 ± 0.00008 |  | -0.47 | yes | yes |
| 1 | 41 → 31 | 1.005 | 0.02311 ± 1.55 % | p 0.3 (default) | 0.02298 ± 0.00010 | o4 ±2 | -0.34 | yes | yes |
| 1 | 41 → 31 | 1.005 | 0.02311 ± 1.55 % | p 0.1 | 0.02298 ± 0.00010 | o4 ±2 | -0.34 | yes | yes |
| 1 | 41 → 31 | 1.005 | 0.02311 ± 1.55 % | p 0.03 | 0.02298 ± 0.00010 | o4 ±2 | -0.34 | yes | yes |
| 1 | 41 → 31 | 1.005 | 0.02311 ± 1.55 % | p 0.01 | 0.02298 ± 0.00010 | o4 ±2 | -0.34 | yes | yes |
| 1 | 41 → 31 | 1.005 | 0.02311 ± 1.55 % | guard off | 0.02298 ± 0.00010 | o4 ±2 | -0.34 | yes | yes |
| 1 | 41 → 31 | 1.005 | 0.02311 ± 1.55 % | AICc average | 0.02298 ± 0.00010 |  | -0.34 | yes | yes |
| 2 | 31 → 24 | 4.353 | 0.06555 ± 0.94 % | legacy | 0.06452 ± 0.00052 |  | -1.29 | no | yes |
| 2 | 31 → 24 | 4.353 | 0.06555 ± 0.94 % | p 0.3 (default) | 0.06447 ± 0.00040 | o4 ±2 (none adequate) | -1.48 | no | yes |
| 2 | 31 → 24 | 4.353 | 0.06555 ± 0.94 % | p 0.1 | 0.06447 ± 0.00040 | o4 ±2 | -1.48 | no | yes |
| 2 | 31 → 24 | 4.353 | 0.06555 ± 0.94 % | p 0.03 | 0.06447 ± 0.00040 | o4 ±2 | -1.48 | no | yes |
| 2 | 31 → 24 | 4.353 | 0.06555 ± 0.94 % | p 0.01 | 0.06447 ± 0.00040 | o4 ±2 | -1.48 | no | yes |
| 2 | 31 → 24 | 4.353 | 0.06555 ± 0.94 % | guard off | 0.06447 ± 0.00040 | o4 ±2 | -1.48 | no | yes |
| 2 | 31 → 24 | 4.353 | 0.06555 ± 0.94 % | AICc average | 0.06447 ± 0.00040 |  | -1.48 | no | yes |
| 3 | 24 → 18 | 1.321 | 0.10386 ± 0.75 % | legacy | 0.10368 ± 0.00047 |  | -0.20 | yes | yes |
| 3 | 24 → 18 | 1.321 | 0.10386 ± 0.75 % | p 0.3 (default) | 0.10369 ± 0.00041 | o4 ±2 | -0.19 | yes | yes |
| 3 | 24 → 18 | 1.321 | 0.10386 ± 0.75 % | p 0.1 | 0.10369 ± 0.00041 | o4 ±2 | -0.19 | yes | yes |
| 3 | 24 → 18 | 1.321 | 0.10386 ± 0.75 % | p 0.03 | 0.10369 ± 0.00041 | o4 ±2 | -0.19 | yes | yes |
| 3 | 24 → 18 | 1.321 | 0.10386 ± 0.75 % | p 0.01 | 0.10369 ± 0.00041 | o4 ±2 | -0.19 | yes | yes |
| 3 | 24 → 18 | 1.321 | 0.10386 ± 0.75 % | guard off | 0.10369 ± 0.00041 | o4 ±2 | -0.19 | yes | yes |
| 3 | 24 → 18 | 1.321 | 0.10386 ± 0.75 % | AICc average | 0.10369 ± 0.00041 |  | -0.19 | yes | yes |

## R. Robustness map

A 150 Å film (four phases: ±1/8 and ±3/8 of a fringe at the join), three scans from `xs.chain_plan` with the join at Qz ≈ 0.2 Å⁻¹; the coarser scan's step sets the points per Kiessig period (the actual range over the phases in brackets); flux relative to the NX-like default. Criterion: √(mean over phases of (pull mean² + (pull SD − 1)²)/2). 800 replicates per cell.

| points per period | flux | best | wins (share of 200 bootstrap resamples) | RMS legacy | RMS p 0.3 (default) | RMS p 0.1 | RMS p 0.03 | RMS p 0.01 | RMS guard off | RMS AICc average |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 (2.8–3.3) | ×1 | p 0.3 (default) | p 0.3 (default) 100 % | 0.46 | 0.15 | 0.22 | 0.28 | 0.30 | 1.02 | 0.34 |
| 3 (2.8–3.3) | ×0.1 | p 0.3 (default) | p 0.3 (default) 100 % | 0.43 | 0.10 | 0.17 | 0.23 | 0.27 | 1.01 | 0.30 |
| 3 (2.8–3.3) | ×0.01 | p 0.3 (default) | p 0.3 (default) 100 % | 0.42 | 0.17 | 0.22 | 0.28 | 0.29 | 1.00 | 0.33 |
| 4 (3.7–4.4) | ×1 | p 0.3 (default) | p 0.3 (default) 100 % | 0.43 | 0.12 | 0.16 | 0.20 | 0.23 | 0.75 | 0.25 |
| 4 (3.7–4.4) | ×0.1 | p 0.3 (default) | p 0.3 (default) 100 % | 0.44 | 0.12 | 0.17 | 0.20 | 0.23 | 0.75 | 0.25 |
| 4 (3.7–4.4) | ×0.01 | p 0.3 (default) | p 0.3 (default) 100 % | 0.46 | 0.07 | 0.13 | 0.18 | 0.20 | 0.74 | 0.23 |
| 6 (5.6–6.5) | ×1 | p 0.3 (default) | p 0.3 (default) 99 % | 0.68 | 0.09 | 0.13 | 0.18 | 0.25 | 0.56 | 0.26 |
| 6 (5.6–6.5) | ×0.1 | p 0.3 (default) | p 0.3 (default) 89 %, p 0.1 8 % | 0.52 | 0.10 | 0.12 | 0.15 | 0.19 | 0.53 | 0.20 |
| 6 (5.6–6.5) | ×0.01 | p 0.3 (default) | p 0.3 (default) 79 %, p 0.1 21 % | 1.01 | 0.09 | 0.10 | 0.17 | 0.24 | 0.52 | 0.25 |
| 10 (9.3–10.9) | ×1 | p 0.3 (default) | p 0.3 (default) 99 % | 0.52 | 0.09 | 0.11 | 0.13 | 0.13 | 0.13 | 0.13 |
| 10 (9.3–10.9) | ×0.1 | p 0.3 (default) | p 0.3 (default) 96 % | 0.42 | 0.06 | 0.09 | 0.10 | 0.11 | 0.11 | 0.11 |
| 10 (9.3–10.9) | ×0.01 | p 0.3 (default) | p 0.3 (default) 97 % | 0.40 | 0.09 | 0.11 | 0.11 | 0.13 | 0.13 | 0.13 |

Pull SD (mean over the four phases):

| points per period | flux | legacy | p 0.3 (default) | p 0.1 | p 0.03 | p 0.01 | guard off | AICc average |
|---|---|---|---|---|---|---|---|---|
| 3 | ×1 | 1.56 | 1.02 | 0.98 | 0.96 | 0.93 | 0.21 | 0.89 |
| 3 | ×0.1 | 1.55 | 1.04 | 1.01 | 0.98 | 0.95 | 0.21 | 0.91 |
| 3 | ×0.01 | 1.54 | 1.00 | 0.97 | 0.94 | 0.93 | 0.21 | 0.88 |
| 4 | ×1 | 1.52 | 0.97 | 0.93 | 0.90 | 0.88 | 0.50 | 0.85 |
| 4 | ×0.1 | 1.60 | 1.03 | 0.99 | 0.97 | 0.93 | 0.56 | 0.90 |
| 4 | ×0.01 | 1.63 | 1.00 | 0.94 | 0.90 | 0.89 | 0.52 | 0.85 |
| 6 | ×1 | 1.92 | 1.06 | 1.07 | 1.06 | 1.07 | 0.83 | 1.01 |
| 6 | ×0.1 | 1.64 | 1.06 | 1.05 | 1.06 | 1.08 | 0.82 | 1.01 |
| 6 | ×0.01 | 2.23 | 1.07 | 1.08 | 1.09 | 1.08 | 0.87 | 1.01 |
| 10 | ×1 | 1.70 | 0.98 | 0.92 | 0.91 | 0.91 | 0.91 | 0.91 |
| 10 | ×0.1 | 1.52 | 1.01 | 0.97 | 0.95 | 0.95 | 0.94 | 0.94 |
| 10 | ×0.01 | 1.51 | 0.99 | 0.95 | 0.94 | 0.93 | 0.93 | 0.93 |

RMS over phases of the pull mean:

| points per period | flux | legacy | p 0.3 (default) | p 0.1 | p 0.03 | p 0.01 | guard off | AICc average |
|---|---|---|---|---|---|---|---|---|
| 3 | ×1 | 0.17 | 0.20 | 0.31 | 0.39 | 0.42 | 1.20 | 0.46 |
| 3 | ×0.1 | 0.21 | 0.14 | 0.24 | 0.32 | 0.38 | 1.18 | 0.41 |
| 3 | ×0.01 | 0.21 | 0.23 | 0.31 | 0.38 | 0.41 | 1.16 | 0.45 |
| 4 | ×1 | 0.24 | 0.16 | 0.21 | 0.27 | 0.29 | 0.88 | 0.31 |
| 4 | ×0.1 | 0.17 | 0.16 | 0.23 | 0.28 | 0.32 | 0.88 | 0.34 |
| 4 | ×0.01 | 0.13 | 0.10 | 0.18 | 0.23 | 0.25 | 0.87 | 0.28 |
| 6 | ×1 | 0.09 | 0.10 | 0.14 | 0.22 | 0.33 | 0.77 | 0.36 |
| 6 | ×0.1 | 0.18 | 0.10 | 0.13 | 0.16 | 0.23 | 0.71 | 0.28 |
| 6 | ×0.01 | 0.21 | 0.08 | 0.09 | 0.19 | 0.32 | 0.71 | 0.35 |
| 10 | ×1 | 0.20 | 0.11 | 0.13 | 0.15 | 0.15 | 0.15 | 0.15 |
| 10 | ×0.1 | 0.24 | 0.07 | 0.12 | 0.13 | 0.14 | 0.14 | 0.14 |
| 10 | ×0.01 | 0.23 | 0.12 | 0.14 | 0.14 | 0.16 | 0.16 | 0.16 |

## Files

Each figure `X.png` has its numbers in `X.csv` (A2 also `A2_pulls_all.csv`, every pull; A7 also `A7_downstream_seeds.csv`; R `R_cells.csv` and `R_phases.csv`). The quick variant of the tool (`--quick`) is a smoke run with few replicates, for tests only.
