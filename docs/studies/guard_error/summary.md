# The guard's error: why the join error bars are too small on real data, and where the fix belongs

*main man, 2026-11-25. Every number here was measured by `python tests/tools/guard_error_study.py`
(400 replicates per join and condition, about 30 s on 4 CPUs; synthetic data with known truth, and the
public NX school file). C61 in `docs/COMPARISONS.md`. No default is changed.*

**The question** (the local data agent's survey of 1832 real joins, `docs/studies/ref_patch_real/`, C56).
- **The finding:** on 1091 real scans split with a known factor, the join guard leaves the errors about 24 %
  too small: pull SD 1.24 [1.09, 1.40], against 1.00 with the guard off.
- **The mechanism:** on real joins the ladder climbs to a higher order (median 5), whose χ²/dof is about 0.8.
  Errors are only ever inflated, never shrunk, so nothing widens them. The unguarded order-4 fit has χ²/dof
  about 1.5.
- **The proposal:** inflate the guarded fit's error by the unguarded fit's χ², or report the larger of the two
  errors.

**The answer in one line.** The cause is per-point scatter that the stated errors miss, and the fix belongs in
each point's error, not in the join's. Every join-level fix tried here repairs the smooth joins but makes the
errors three to five times too large where a fringe or a short overlap fools the curve.

## What was compared

Study A's six synthetic joins (`ref_guard_study`): five biased by a fringe or a short overlap, and one smooth
join. Each was given **excess per-point scatter** of 0, 1, 2 or 3 %: each point × (1 + X·z), with the stated
errors unchanged. The error rules, all on the rung the guard keeps at p 0.7:

| rule | the error |
|---|---|
| **own** (today) | the rung's counting error inflated by its own χ² |
| ref | inflated by the unguarded order-4, ±2 fit's χ² instead |
| both | by the larger of the two inflations |
| max | the larger of the rung's error and the unguarded fit's |
| guard off | the unguarded fit and its own error |
| **budget** (oracle) | today's rule, on the same data with each point's error widened by the true excess, √(σ² + (X·y)²) |

## Results (pull SD: 1 means honest error bars)

| rule | excess 0 % | 1 % | 2 % | 3 % | smooth / biased |
|---|---|---|---|---|---|
| **own (today)** | 1.12 / 1.01 | **1.64 / 1.24** | 1.90 / 1.48 | 2.45 / 1.51 | |
| ref | 1.07 / **0.50** | 1.07 / 0.62 | 1.06 / 0.78 | 1.14 / 0.76 | |
| both | 1.07 / 0.50 | 1.06 / 0.62 | 1.04 / 0.78 | 1.12 / 0.76 | |
| max | 1.10 / 0.52 | 1.19 / 0.67 | 1.18 / 0.84 | 1.32 / 0.81 | |
| guard off | 1.00 / 0.48 | 1.12 / 0.70 | 1.15 / 0.90 | 1.29 / 0.92 | |
| **budget (oracle)** | 1.12 / 1.01 | **1.04 / 0.97** | **0.97 / 0.97** | **1.07 / 0.94** | |

(smooth join / mean of the five biased joins; `stats.csv` has every join, the mean pulls and the coverage.)

- **Hidden scatter reproduces the real-data failure.**
  - With 1 % of it, the guard climbs on 94 % of the smooth joins (49 % without), and today's errors are 39 %
    too small there (1.64). That is the size and the mechanism C56 measured.
  - The ladder accepts a curve that fits the noise, so its χ² is too good to inflate.
- **The join-level fixes fail at the hard joins.**
  - They bring the smooth join back to 1.04–1.14, but leave the biased joins at 0.50–0.84.
  - Their median errors there are **3.1–4.6 × today's** (G2).
  - Where a fringe crosses the join, the unguarded order-4 fit misses the curve, and its large χ² is model
    misfit, not noise. Inflating by it penalises every fringed join.
- **Honest per-point errors fix both,** with today's guard unchanged: 0.94–1.07 at every excess, smooth and
  biased alike. The cost is the honest one: errors 1.2 × (biased) to 1.5 × (smooth) today's, at the level of
  the scatter that is really there.
- **NX school (public), the survey's split:**
  - only 3 of its scans have the 20 points the split needs, too few to decide anything;
  - RMS pull 1.40 (today), 1.38 (ref) and 1.64 (guard off); `nx_split.csv`;
  - the NX excess is not known, so "budget" there is today's rule.

## Recommendation

- **Do not change the join's error rule.** None of the proposals is better than today across both kinds of
  join.
- **Add an excess term to the per-point error budget** (`lss_core.errors`, budget mode). It is the remedy
  C56's last row already pointed to: 16–31 % of real joins at Qz ≥ 0.25 have χ² p < 0.01.
- **What it needs first:** an estimate of the excess from the data, with known truth, since the true X is not
  known on real data. Candidates:
  - the pooled χ² of the unguarded fits at joins without fringes;
  - the residual scatter of a local smoother over each scan, in ln(R/R_F);
  - repeats, where they exist;
  - and, on the owner's data, its size by Qz class (DATA_NEEDS).
- **Then** a rule-12 study before any default changes.

---

**Figures:** G1 (pull SD against the excess), G2 (each rule's median error over today's), G3 (coverage within
±1 and ±2). Tool: `tests/tools/guard_error_study.py`, a Tools menu item.
