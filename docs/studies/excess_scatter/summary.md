# Reflectivity points scattered beyond counting statistics (DATA_NEEDS row 15, C63)

The owner's non-cloud agent, 2026-11-25. This answers main man's MQ-3, recorded by questor as DATA_NEEDS row 15
(PR #91). The owner said: "I don't know the size; measure it from data".

C61 (`docs/studies/guard_error/`) found two things. Hidden per-point scatter of about 1 % of R reproduces the
real joins' too-small errors (C56: pull SD 1.24). The remedy belongs in each point's error, as an excess term,
once that excess can be measured. This study measures it on the owner's real data and checks the estimators
on known truth first.

*The whole chain, one example at a time, with every statistic explained: `walkthrough.md` beside this file
(AGENTS.md rule 13).*

**Regenerate:**

    python tests/tools/excess_scatter.py --out docs/studies/excess_scatter --trials 40 --pulls 200
    python tests/tools/excess_scatter_walkthrough.py

The first takes about 30 min with 4 workers, and the second about 40 s. The real numbers (`real_*.csv`) come
from the private generators under `sample_data/private/xr/scripts/`:
- `scatter_collect.py` reduces every series once;
- `scatter_analyse.py`, `scatter_scale.py` and `scatter_tails.py` import the estimators of
  `tests/tools/excess_scatter.py`, so the real numbers come from the code checked here.

They are not regenerable without the private data. No raw data, file name, scan number or date is in this
folder. Runs are labelled `S…` by a salted hash.

## The answer

**A typical real point carries little scatter beyond its stated error. A few points carry a lot.**
- **Within a scan:** the stated σ is about 12 % too small (s = 1.12 [1.10, 1.12]), or equivalently 0.14 % of R
  [0.13, 0.18] as a proportional term.
- **Between two scans at the same Qz:** 0.39 % of R [0.30, 0.48], or σ about 40 % too small (s = 1.42
  [1.33, 1.57]).
- **At Qz ≥ 0.25,** where counts are low and the background large, the between-scan excess is 2.7 % of R
  [2.2, 2.9].
- **Outliers:** 4–6 % of the between-scan residuals are wild, typically 70–90 % off.
- **One Gaussian misleads:** fitted to all points as one Gaussian, the same data say 12 %. A model with a
  core and an outlier part is needed.

**The between-scan core explains the real joins.** A core of 0.4 % on C61's synthetic joins gives today's
joint fit a pull SD of 1.36 on the smooth join and 1.05 on the fringed joins, or 1.24 and 1.12 with 3 %
outliers added. The real joins measured 1.24 [1.09, 1.40] (C56).

| | between scans (shared Qz) | within a scan (6-point difference) |
|---|---|---|
| terms | 2812 pair residuals in 706 pairs of scans (2106 degrees of freedom) | 26,182 six-point windows |
| median \|residual / σ\| (counting errors only; 0.674 if they were right) | 0.90 | 0.76 |
| beyond 3σ (Gaussian: 0.27 %) | 9.0 % | 3.1 % |
| beyond 10σ | 2.4 % | 0.84 % |
| **core excess X** (core + outliers), % of R [bootstrap over runs] | **0.39** [0.30, 0.48] | **0.14** [0.13, 0.18] |
| outlier share [bootstrap] and typical size τ | 6.0 % [4.3, 7.4] of pair residuals, τ 73 % | 1.8 % [1.3, 2.5] of windows, τ 46 % |
| as a scale on σ instead (with outliers) | s = 1.42 [1.33, 1.57], no X needed | s = 1.12 [1.10, 1.12] with X 0.10 % [0.08, 0.13] |
| one Gaussian for everything (misleading) | 12 % | 6 % |

The data: 384 reflectivity series in 18 runs (29 files were searched), all at 10 keV. Bootstrap intervals
are the 16th–84th percentiles over 100 resamples of runs (30 for the scale). An outlier pair means either
of its points can be the bad one, so about half that share of points is wild. One bad point touches six
windows.

## What it follows

`real_by.csv`; figure W5 draws every bin with terms from at least 3 runs.

| bin | between scans: core X (%) | within a scan: core X (%) |
|---|---|---|
| Qz 0.04–0.1 Å⁻¹ | 0.20 [0.16, 0.30] (4 runs) | 0.19 [0.17, 0.22] |
| Qz 0.1–0.25 | 0.40 [0.34, 0.50] | 0.11 [0.09, 0.13] |
| Qz ≥ 0.25 | **2.65** [2.19, 2.91] | 0.16 [0.12, 0.23] |
| counts per point < 10³ | — | 1.39 [0.51, 1.82] |
| 10³–10⁴ | — | 0.58 [0.38, 0.69] |
| 10⁴–10⁵ | — | 0.24 [0.21, 0.25] |
| > 10⁵ | — | 0.13 [0.11, 0.16] |
| points < 2 min apart | 0.37 [0.31, 0.47] | — |
| 2–10 min apart | 2.49 [1.68, 2.72] | — |
| background share of the box < 2 % | 0.32 [0.28, 0.36] | 0.14 [0.12, 0.15] |
| ≥ 30 % | 3.06 [2.36, 3.14] | 0.24 [0.13, 0.29] |

- **Within a scan the excess follows the counts, not R.** As a fraction of R it falls tenfold from 10³ to
  10⁵ counts. As a scale on σ it is about constant: s 1.05–1.14 in every counts bin (`real_scale.csv`).
  So the counting error itself is stated about 12 % too small, with a floor of about 0.1 % of R on top.
  The budget's σ is √counts plus the monitor term; what adds the rest is not known. Candidates are the
  background boxes' own scatter and the detector's counting statistics.
- **Between scans the excess grows at high Qz.** High Qz means low counts, a large background share and
  points minutes apart. These go together in the data and cannot all be told apart:
  - time apart within each Qz class is in `real_time_by_qz.csv`;
  - below Qz 0.25, points less than a minute apart differ by 0.08 % (Qz < 0.1) and 0.31 % (0.1–0.25), and
    points 1–2 min apart by 0.33 % and 0.42 %. That is a weak hint of a slow drift, from only 2–3 runs in
    the short bins;
  - at Qz ≥ 0.25, points more than 4 min apart do *not* differ more (0.73 % against 2.70 % at 2–4 min), but
    they have 3× the counts;
  - at Qz ≥ 0.25, the scale model prefers a proportional 2.5 % to a scale on σ (Δln L 63). Something
    proportional differs between two scans there: the background boxes at another absorber, or the
    footprint.
- **The monitor and the absorber step** show no clear trend (W5). The within-scan core is 0.14–0.20 % in
  every monitor bin. 87 % of the windows' middle points have a monitor rate (Monc per second) more than 1 %
  from its scan's median, so most of the data sit in one bin.
- **Sample height:** not measured here. The height scans around each series were not paired with its
  points. That needs the height-scan survey and is listed below.

## The known-truth check

`known_truth.csv`, figure X1. The setup:
- 40 estimates per cell, each from 50 synthetic series;
- each series: 5 scans with 3 shared Qz per join, and one repeated scan;
- Poisson counts, 2 × 10⁴ at each scan's top;
- the resolution measured in C55;
- curves: water, DPPC and a 100 Å film.

Results:
- **Shared Qz with core + outliers** (the recommended estimator): within 0.09 % of R of the truth at every X
  from 0 to 3 %, on all three curves, with or without 3 % outliers. Its 16th–84th percentiles are ±0.05 %
  at X = 1 %.
- **Shared Qz, one Gaussian:** right without outliers, but 7 % with them, whatever the true X.
- **Within a scan:** unbiased on water and DPPC. The film's fringes leave 1.1–1.3 % at X = 0 (6 points per
  window cancel a curve only up to Qz⁴). Shorter windows were tried while building, in runs not committed:
  3 to 5 points left 0.3–1.9 % on DPPC.
- **A slow drift** (2 % over a scan, random phase) adds about 1.2 % to the shared-Qz estimate and nothing
  to the within-scan one. So the two estimators together separate point-to-point scatter from slow
  changes.
- **Error scale:** a stated σ too small by s = 1.15 or 1.4 is found within ±0.07 (`estimate_scale`; runs
  while building, and `tests/test_excess_scatter.py` pins s = 1.15 within 0.06). Its split into s and a
  proportional X is not reliable below about 0.5 %: with s = 1 the fit reported X up to 0.35 % in those
  runs. The real s values are trusted to about ±0.05. The real X of the scale model is quoted only as a
  floor.
- **The one-Gaussian likelihood interval undercovers:** it holds the truth in 23–63 % of estimates at
  X > 0, against 68 %. The real intervals are therefore the bootstrap over runs.
- **Pulls** (`pulls.csv`): today's joint fit on C61's six joins, 200 replicates each, smooth / fringed:

  | case | smooth | fringed |
  |---|---|---|
  | no excess | 1.14 | 0.98 |
  | core 0.4 % | 1.36 | 1.05 |
  | core 1 % | 1.56 | 1.26 |
  | core 0.4 % + 3 % outliers | 1.24 | 1.12 |
  | 3 % outliers only | 1.16 | 1.03 |

  - C61's own table, at 400 replicates with its seeds, gave 1.64 at 1 %.
  - Outliers alone barely move the pull SD: the joint fit's χ² inflation absorbs them, at a cost in
    error.

## For the budget (main man, tools man; no number changes here: rule 12, the owner's word)

- **The excess is not one percentage.** Two terms describe it:
  - **a scale on the counting σ**, about 1.12 within a scan;
  - **a between-scan term**, about 0.4 % of R below Qz 0.25 and about 2.5 % above.
  - A fixed 1 % for every point (C61's working value) is too much at low Qz and too little at high Qz.
- **Outliers need handling of their own.** 4–6 % of the between-scan residuals are tens of % off. A
  Student-t or core-plus-outlier likelihood in the joint fit, or flagging such points, would serve better
  than widening every point's error.
- **The next study** (rule 12): the joint fit with σ × 1.12 plus a Qz-dependent between-scan term, and a
  robust likelihood, against C56's 1091 real splits and C61's synthetic joins.

## Not shown, and why

- **Repeated scans:** only 2 repeats are in the data, in one run (9 terms), too few to say anything. They are
  in `real_overall.csv` for completeness.
- **Sample height, the beam's position on the detector and the slits:** not paired with the points in this
  pass. The height scans around each series could be added from the sh-beam survey (open, below).
- **Below Qz 0.04:** left out, because the edge's curvature biases both estimators. C55 covers the edge.
- **Points with y/σ < 5:** left out, because ln y is linear in the noise only when the noise is small. This
  removes the faintest points at the highest Qz, so the high-Qz excess is that of the points kept.

## Open

1. Is the 12 % within-scan scale known at the beamline, for example from the Pilatus counting or the
   background boxes? A short repeat of one Qz point (20 frames, the sample still) would settle the
   counting part.
2. Pair the points with the height scans around them (sample-height drift; the height scans' ROI data are
   unrestricted), to test the owner's first candidate directly.
3. More repeated scans at high Qz, minutes apart, would tell a drift from a background effect.
