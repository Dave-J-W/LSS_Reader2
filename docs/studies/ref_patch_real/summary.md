# Reflectivity patching on real series with many joins (DATA_NEEDS row 1, hand-off 08)

The owner's non-cloud agent, 2026-11-24. **Measured on real data**: hand-off 08's survey
(`tests/tools/ref_patch_survey.py`, unchanged) on every private SPEC file the reader can read, with three
methods added in a private wrapper:
- `joint_default_p07`: today's default, order 4, 2 points either side, guard p 0.7;
- `joint_default_p03`: the guard at p 0.3, the default before;
- `joint_o4_e2_noguard`: the same fit without the guard.

| | |
|---|---|
| Files read | 18 with reflectivity series (the 30 keV Pilatus 1M run fails in the reduction: F38) |
| Series (sets) | 380 |
| Joins | **1832**, all at 10 keV (Qz < 0.05: 373; 0.05–0.25: 964; ≥ 0.25: 490) |
| Split-truth tests | 1091 scans of ≥ 20 points, split into two interleaved halves that overlap over 8 points, the second × 0.8 (truth f = 1.25) |
| Repeats (identical Qz) | none found by the survey |

The tables are per method, Qz class and energy, with no set, file or scan names:
- `split_truth.csv`, `split_truth_by_class.csv`: with 95 % intervals from a bootstrap over files;
- `foil_z.csv`, `chi2_guard.csv`, `default_vs_others.csv`, `sets_level.csv`;
- `numbers.json`.

**Not regenerable here.** The private wrapper and aggregator live under `sample_data/private/xr/scripts/`
(`patch_survey.py`, `patch_all.py`, `patch_aggregate.py`).

## The answers, in the hand-off's order

### 1. Split truth: bias and honest errors (figure P1)

| method | bias of f (%) [95 %] | pull SD [95 %] | robust pull SD | \|pull\| > 3 |
|---|---|---|---|---|
| legacy | **−0.55 [−1.16, −0.22]** | **2.39 [1.91, 2.91]** | 1.22 | 10.6 % |
| spline ratio (`interp`) | −0.57 [−1.14, −0.23] | 1.04 [0.98, 1.09] | 0.92 | 0.9 % |
| joint o2 e0 | +0.14 [−0.21, +0.43] | 1.07 [1.00, 1.13] | 0.96 | 0.6 % |
| joint, guard p 0.3 (before) | +0.05 [−0.14, +0.24] | 1.23 [1.07, 1.38] | 1.11 | 1.1 % |
| **joint, default (guard p 0.7)** | **+0.10 [−0.10, +0.32]** | **1.24 [1.09, 1.40]** | 1.10 | 1.1 % |
| joint, guard off (o4 e2) | +0.05 [−0.15, +0.21] | **1.00 [0.93, 1.03]** | 0.93 | 0.8 % |

By Qz class, the default's pull SD is 1.25 (< 0.05), 1.29 (0.05–0.25) and 0.99 (≥ 0.25). With the guard
off it is 1.05, 1.00 and 0.92 (`split_truth_by_class.csv`).

- **The joint fit is confirmed against the legacy factor on real data.** The legacy factor is biased low by
  0.55 %, as is the spline ratio, which shares its interpolation. Its errors are 2.4× too small, with 11 %
  of splits beyond 3σ. The joint fit is unbiased within 0.1–0.3 %.
- **The guard makes the errors too small on real joins**, at p 0.7 and at p 0.3 alike. Bootstrapped over
  files, guard-on minus guard-off pull SD is **+0.24 [0.11, 0.38]**. C48 measured +0.08 on its smooth
  synthetic join.
  - **How:** on real joins the ladder climbs to a median order of 5 at 2 points either side. Its accepted
    fit has χ²/dof about 0.8, so the inflate-only rule never widens the error.
  - Without the guard, χ²/dof is about 1.5 and 25 % of joins have p < 0.01. Inflating by that χ² gives
    errors that cover.

### 2. Repeats

None: the survey found no scan repeated at identical Qz in these files.

### 3. Clean joins against the foils (`foil_z.csv`)

On the 906 joins where Monc/Monp changes by less than 3 %, z = (δ − ln known)/σ has a robust SD of:
- 0.43–0.49 at Qz < 0.05;
- 0.71–0.73 at 0.05–0.25;
- 1.07–1.26 at ≥ 0.25.

The medians are −0.07 to +0.21, for every method alike. The foils were fitted on these same owner joins
(hand-off 03), so this is in sample. It does not separate the methods. Fit and foil ratio do not disagree
at real joins, so this check gives no reason to reverse the guard decision.

### 4. χ² of the joint fit (`chi2_guard.csv`)

The share with p < 0.01 should be 1 % for an adequate model.

| Qz | default | guard off |
|---|---|---|
| < 0.05 | 5.1 % | 17 % |
| 0.05–0.25 | 11 % | 26 % |
| ≥ 0.25 | 16.5 % | 31 % |

Both rise with Qz: excess, non-counting scatter grows at high Qz, and it belongs in the per-point error
model (the hand-off's item 4).

### 5. Window and order

Guarded, the median rung on real joins is order 5 at 2 points either side (order 4 at 1 point either side
at Qz ≥ 0.25). Without the guard it stays at order 4, 2 points either side. The interleaved split favours
no guard on calibration and is level on bias. A lower order (o2 e0) is also calibrated (1.07) and unbiased.

### 6. The foil prior

The prior changes the default's factor by more than 1σ at 2.4 % of joins. It lowers the last scan's level
uncertainty from a median 1.96 % to 1.72 % (`sets_level.csv`).

### 7. Default against legacy, join by join

Over 1827 joins, the median |Δ ln f| is 0.09 %. 10 % differ by more than 1 %, 4 % by more than 5 %, and 1 %
by more than 25 %.

The guard's p, 0.7 against 0.3:
- the factor is identical at 67 % of joins;
- it differs by more than 1σ at 3.7 %;
- the split truth and the foil z are the same.

On real data the choice between the two does not matter, in line with C48's 0.001 Å in a structural fit.

## What this means for the defaults (proposals, not applied: rule 12)

| decision | evidence here | proposal |
|---|---|---|
| joint fit as the default | unbiased, calibrated within 1.24 on 1091 real splits; legacy −0.55 % and 2.4× | **confirmed** |
| guard p 0.7 vs 0.3 | identical in 67 %, > 1σ in 3.7 %; same calibration | keep 0.7: no reason to reverse |
| the guard's error | +0.24 [0.11, 0.38] in pull SD over the unguarded fit | **new:** inflate the guarded fit's error by the unguarded order-4 fit's χ² (or report the larger of the two errors). For main man: a candidate study on the gauntlet, then rule 12 |
| per-point errors at high Qz | 16–31 % of joins with p < 0.01 at Qz ≥ 0.25 | an excess term in the error budget at high Qz |

## Not shown, and why

- **`coincident`** in figure P1: interleaved halves share no Qz, so the method has nothing to fit there.
  Its shared-variant bias is 0 by construction.
- **Energies other than 10 keV:** the readable series are all at 10 keV. That also answers row 8's first
  half: no series with overlaps at 6–7 keV exists in these data.
- **The 30 keV run** (Cu foils): its Pilatus 1M frames are not read by the reduction.
