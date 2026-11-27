# Reflectivity points scattered beyond counting statistics (DATA_NEEDS row 15, C63)

The owner's non-cloud agent, 2026-11-25. This answers main man's MQ-3, recorded by questor as DATA_NEEDS row 15
(PR #91). The owner said: "I don't know the size; measure it from data".

C61 (`docs/studies/guard_error/`) found two things. Hidden per-point scatter of about 1 % of R reproduces the
real joins' too-small errors (C56: pull SD 1.24). The remedy belongs in each point's error, as an excess term,
once that excess can be measured. This study measures it on the owner's real data and checks the estimators
on known truth first.

**Within a scan only** (owner, 2026-11-25, after review). A first version also compared two scans at the
Qz they share. Those two points differ by whatever changed between the scans, such as the sample height,
the footprint, the background boxes at another absorber, or the time apart, and the data do not record any
of it. So the between-scan numbers were withdrawn: nothing here rests on them, and they should not be used
(the first version, merged as PR #96, is in the git history; C64 drew one of its truths from it).
The owner's words: "I do understand this decision could underestimate our uncertainty but at least we
will be on solid ground." What a within-scan measurement cannot see is listed under "What this does not
measure".

*The whole chain, one example at a time, with every statistic explained: `walkthrough.md` beside this file
(AGENTS.md rule 13).*

**Regenerate:**

    python tests/tools/excess_scatter.py --out docs/studies/excess_scatter --trials 40 --scale-trials 20 --pulls 400
    python tests/tools/excess_scatter_walkthrough.py

The first takes about 15 min with 24 workers (`--pulls-only` reruns just the pull check, about 3 min), and
the second about 40 s. The real numbers (`real_*.csv`) come from the private generators under
`sample_data/private/xr/scripts/`:
- `scatter_collect.py` reduces every series once;
- `scatter_analyse.py`, `scatter_scale.py` and `scatter_tails.py` import the estimators of
  `tests/tools/excess_scatter.py`, so the real numbers come from the code checked here. They publish the
  within-scan rows only.

They are not regenerable without the private data. No raw data, file name, scan number or date is in this
folder. Runs are labelled `S…` by a salted hash.

## The answer

**Within a scan, a typical real point scatters a little more than its stated error. A few points scatter a
lot more.**
- **As a scale on the error:** the stated σ is about 12 % too small (s = 1.12 [1.10, 1.12]). Known truth shows
  that a curve's own shape can add 0.01–0.04 to s (below), so the true scale is about 1.08–1.12.
- **As a share of R:** the core excess is 0.14 % of R [0.13, 0.18]. It falls tenfold as the counts rise, so it
  behaves like an understated counting error, not like a fixed percentage. **Caveat (2026-11-26):** on known
  truth with no excess at all, a DPPC monolayer reads 0.12 % [0.08, 0.16] (`known_truth.csv`): the curve's
  own shape leaking into the windows, as large as this result. The firm finding is the scale on σ; any excess
  on top of it is at most a few tenths of a percent of R.
- **Outliers:** 1.8 % [1.3, 2.5] of the 6-point windows are wild, typically 46 % off. One bad point spoils up
  to six windows, so at most about 0.3 % of points are wild. **Part of this is the curve's own shape, not wild
  points:** a deep minimum sampled by one point looks exactly like a wild point inside a window (R3), and such
  windows come back at the same Qz in other series of the same run more often than chance (below, "Wild
  points or the curve's shape?"). The core excess and the scale on σ do not depend on this.
- **One Gaussian misleads:** fitted to all windows as one Gaussian, the same data say 6 %. A model with a core
  and an outlier part is needed.

**Does it explain the real joins?** Only partly, as far as can be told. Today's joint fit on C61's synthetic
joins has a pull SD of 1.12 ± 0.04 on the smooth join with honest errors. The within-scan findings (σ × 1.12,
a 0.14 % core and 0.3 % wild points) raise it to 1.19 ± 0.05. The real joins measured 1.24 [1.09, 1.40] (C56).
That is consistent with the within-scan excess alone, but C56's interval is too wide to rule out that more
is needed. Whatever changes between two scans is the obvious candidate for the rest, and it is not measured
here.

| within a scan (6-point difference) | real data |
|---|---|
| terms | 26,182 six-point windows in 384 series, 18 runs |
| median \|d / σ_d\| (counting errors only; 0.674 if they were right) | 0.76 |
| beyond 3σ (Gaussian: 0.27 %) | 3.1 % |
| beyond 10σ (Gaussian: practically 0) | 0.84 % |
| **core excess X** (core + outliers), % of R [bootstrap over runs] | **0.14** [0.13, 0.18] |
| outlier share [bootstrap] and typical size τ | 1.8 % [1.3, 2.5] of windows, τ 46 % |
| **as a scale on σ** (with outliers) | **s = 1.12** [1.10, 1.12], with X 0.10 % [0.08, 0.13] on top |
| scale model against X only, and against s only | Δln L 166 for adding s, 96 for adding X: both are needed |
| one Gaussian for everything (misleading) | 6.1 % |
| per run (core X) | 0.00–0.34 % over the 18 runs (`real_runs.csv`) |

The data: 384 reflectivity series in 18 runs (29 files were searched), all at 10 keV. Bootstrap intervals
are the 16th–84th percentiles over 100 resamples of runs (30 for the scale). `real_tails.csv` has the tail
shares, `real_scale.csv` the scale model by bin.

## What it follows

`real_by.csv` and `real_scale.csv`; figure W4 draws every bin with terms from at least 3 runs.

| bin | core X (% of R) [bootstrap] | scale s |
|---|---|---|
| Qz 0.04–0.1 Å⁻¹ | 0.19 [0.17, 0.22] | 1.11 |
| Qz 0.1–0.25 | 0.12 [0.09, 0.13] | 1.17 |
| Qz ≥ 0.25 | 0.16 [0.13, 0.23] | 1.07 |
| counts per point < 10³ | 1.39 [0.51, 1.82] | 1.10 |
| 10³–10⁴ | 0.58 [0.38, 0.69] | 1.05 |
| 10⁴–10⁵ | 0.24 [0.21, 0.25] | 1.13 |
| > 10⁵ | 0.13 [0.11, 0.16] | 1.14 |
| background share of the box < 2 % | 0.14 [0.12, 0.15] | — |
| 2–10 % | 0.16 [0.11, 0.24] | — |
| 10–30 % | 0.46 [0.31, 0.61] | — |
| ≥ 30 % | 0.24 [0.13, 0.29] | — |

- **The excess follows the counts, not R.** As a fraction of R it falls tenfold from below 10³ counts to
  above 10⁵. As a scale on σ it is about constant: s 1.05–1.14 in every counts bin. So the counting error
  itself is stated about 10 % too small, with a floor of about 0.1 % of R on top. The budget's σ is √counts
  plus the monitor term; what adds the rest is not known. Candidates are the background boxes' own scatter
  and the detector's counting statistics.
- **Qz:** no strong trend within a scan (0.12–0.19 %). The low-Qz bin is a little higher, where the curve
  bends fastest and its shape leaks in most (known truth below).
- **Background:** higher where the background is 10–30 % of the box. Those points also have fewer counts,
  so this bin is not independent of the counts trend.
- **The monitor** shows no clear trend: the core is 0.14–0.20 % in every monitor bin. 87 % of the windows'
  middle points have a monitor rate (Monc per second) more than 1 % from its scan's median, so most of the
  data sit in one bin.

## Real examples anyone can rerun (released runs, before 2019)

The owner released reflectivity data from before 2019 for figures (2026-11-25, AGENTS.md; reflectivity only,
the minimum a figure needs, anonymous). From an archive of older beamtimes, 98 reflectivity series at 10 keV
were found and 96 reduced (two failed in the reduction). `released/` beside this file holds the extract:
- `series.csv`: the points of four series A–D, cherry-picked for what they show;
- `windows.csv`: every 6-point window of the 96 series (derived numbers);
- `frames.csv`, `frames.json`: two cropped frames of series A with the reader's boxes.

Figures R1–R4 come from `python tests/tools/excess_scatter_released.py`, on public data only; the extract
comes from the private `sample_data/private/old/scripts/released_export.py`.

| | released runs (96 series) | the 18 private runs |
|---|---|---|
| windows | 4,561 | 26,182 |
| error scale s | 1.07 | 1.12 |
| core excess X | 0.21 % of R | 0.14 % of R |
| outlier windows | 3.2 % | 1.8 % |
| median \|d / σ_d\| (honest: 0.674) | 0.73 | 0.76 |
| X by counts | falls 8× from < 10³ to ≥ 10⁵ | falls 11× |

The released runs are older and from other samples, so agreement is a check, not a requirement. They agree
on the shape of the answer: a scale on σ a little above 1, a core of a few tenths of a percent of R that
falls with the counts, and a few percent of outlier windows.

### Wild points or the curve's shape?

The released series show what the outlier windows are made of. Most released series are of one kind of
sample with a deep minimum near 0.055 Å⁻¹, sampled by one or two points. Inside a window, that minimum leaves
one huge difference, exactly as a wild point would (R3). 52 of the 61 released windows beyond 10σ (85 %) have
their middle within ±0.010 Å⁻¹ of it, a band that holds 17 % of all windows. Left out, the outlier share falls
from 3.2 % to 0.9 %, s goes from 1.07 to 1.04, and the core excess from 0.21 % to 0.25 % of R (R3's numbers,
`released/numbers.json`, key `minimum`).

Why six points (R3, last panel, known truth with no excess): a window of three points reads a monolayer's own
curve as scatter three times the error bars (spread of d / σ_d 2.9 on DPPC, where honest is 1); five points
still 1.1; six 1.0. A 100 Å film's fringes still leak into six points (1.3). The longer windows cost almost
nothing: with a 1 % excess on water, three to seven points all read 1.18–1.22. No curve is drawn through a
window in R3: a quartic through six points passes near all of them whatever they do, and its six residuals
are the one number d in a fixed pattern.

The private runs have no common minimum, so a test that does not need to know where minima are was used: a
wild point lands at a random Qz, the curve's shape comes back at the same Qz in other series of the same run.
Of the 371 private windows beyond 5σ, 64 % have such a partner within ±0.003 Å⁻¹, against 55 % ± 2 with the
big windows' positions shuffled (the released: 99 % against 94 % ± 1). The test is weak, because series of a
run share one Qz grid, but the excess is clear. Leaving out the windows with a partner:

| | outlier windows | core X | s |
|---|---|---|---|
| private, all | 1.78 % | 0.144 % | 1.116 |
| private, reproducible big windows left out | 0.76 % | 0.141 % | 1.128 |
| released, all | 3.18 % | 0.210 % | 1.065 |
| released, reproducible big windows left out | 0.43 % | 0.212 % | 1.094 |

**So:** the core excess and the scale on σ stand. The outlier share is an upper bound for wild points: part
of it is a curve sharper than six points can follow. Private check: `sample_data/private/xr/scripts/scatter_shape.py`
(numbers above; nothing written). A first version of this check, which measured sharpness from the window's
own points, was circular (a wild point is "sharp" too) and is not used.

## Fresnel division, the beam's convergence and angle jitter (owner's questions, 2026-11-26)

Private check: `sample_data/private/xr/scripts/scatter_fresnel_angle.py` (derived numbers only, in
`xr/out/fresnel_angle.json`; not regenerable here).

**With or without dividing by R_F: the same.** The same windows on ln y and on ln(y/R_F) give, to three
decimals, the same core excess, outlier share and s, in every Qz range: private 0.14 %, 1.8 %, 1.116 both
ways; released 0.21 %, 3.2 %, 1.065. Above Qz 0.04 ln R_F is smooth enough that the window's weights cancel
it (it moves d by a median 0.000–0.002 σ_d, at most 0.02 σ_d in 95 % of windows), and the error bars do not
change. The same holds for Qoff, which only shifts where R_F is evaluated: any Qoff is a smaller change than
leaving R_F out. Normalisation matters only at the critical edge, which the study leaves out (Qz < 0.04).

**The beam's convergence as resolution** (37 µrad rms, σ_Q 3.8 × 10⁻⁴ Å⁻¹ at 10 keV;
`docs/studies/qz_resolution/`): a fixed spread of angles smooths the curve and adds no scatter. Its one way
in would be the depth of minima, so how much shape leaks into a window. Known truth with no excess at the
runs' range of resolution, FWHM 6.5, 8.9 and 12.6 × 10⁻⁴: spread of d / σ_d 1.04 on DPPC at all three, and
1.25–1.29 on a 100 Å film. No change.

**Angle jitter from point to point** would be real scatter, δ ln R = (d ln R / dQz) δQz (about 4 δQz / Qz on
a falling curve). A joint fit of jitter, core excess and outliers **failed its known-truth check**: on DPPC
it read 0.8–1.2 × 10⁻⁴ Å⁻¹ of jitter with none put in (jitter and curve shape both live near minima), and on
water it missed 2 × 10⁻⁵ put in and traded jitter against X. So the real fits (2 × 10⁻⁵ Å⁻¹, about 2 µrad,
private; 1.5 × 10⁻⁵ released; 0 released without the minimum) are **not measurements**. A weaker check
without that fit: jitter makes the excess largest at low Qz, falling as 1/Qz; the private core excess is 0.19,
0.20, 0.10 and 0.18 % from Qz 0.04 to above 0.2, and the released one rises. So jitter is not the main
source; at about 2 µrad per point it would add up to about 0.16 % at Qz 0.05 and less above, which cannot
be ruled out.

**Qoff and the resolution at the edge** are where the angle matters: the reader's Qoff proposal reads the
resolution as Qoff (C50: about −0.15 ΔQ). A fit of Qoff and σ_Q together, with R_F smeared and Qc from the
subphase, is requested for after 2.0 (owner, 2026-11-26; `docs/RELEASE_PLAN.md`).

## What this does not measure

A within-scan estimate can only see scatter from point to point. It is blind to anything that changes
smoothly over a scan or between scans, so **the true uncertainty of a joined curve can be larger than these
numbers say**:
- **A slow drift** during a scan (sample height, evaporation, the beam moving): on known truth a 2 % drift
  adds nothing to the within-scan estimate (figure X1, middle row). It looks like part of the curve.
- **A change between two scans** (another absorber, background boxes refitted, the sample settling).
  This is what the set-aside between-scan comparison would have measured, if the confounders had been
  recorded.
- **Sample height:** not measured. The height scans around each series were not paired with its points.

In the other direction, **a sample's own fast fringes make the within-scan estimate too large**: on a 100 Å
film the 6-point difference reads about 1.3 % at X = 0. Real samples with thick films would read high for
that reason, not because their points scatter.

## The known-truth check

`known_truth.csv` and figure X1 (the excess X); `known_truth_scale.csv` and figure X2 (the scale s). The setup:
- 40 estimates per cell for X (20 for s), each from 50 synthetic series of 5 scans;
- Poisson counts, 2 × 10⁴ at each scan's top;
- the resolution measured in C55;
- curves: water, DPPC and a 100 Å film;
- cases: per-point X alone; with a slow 2 % drift; with 0.3 % of points off by about 40 % (about the real
  share); with 3 % (ten times the real share).

Results:
- **Core + outliers** (the estimator used for the real numbers): within 0.14 % of R of the truth on water and
  DPPC at every X from 0 to 3 %, with no outliers or the real share. With ten times the real share it reads
  up to 0.34 % high. Wild points spoil six windows at once, so they are not independent, which the model
  assumes. With the real share this does not matter.
- **One Gaussian:** right without outliers, but about 2 % with the real share of outliers and 7 % with ten
  times that, whatever the true X.
- **A film's fringes** leave 1.2–1.3 % at X = 0 (6 points per window cancel a curve only up to Qz⁴). Shorter
  windows were tried while building, in runs not committed: 3 to 5 points left 0.3–1.9 % on DPPC.
- **A slow drift** adds nothing (within 0.01 %), as expected: this estimator cannot see it.
- **Error scale (X2):** a stated σ too small by s is found within 0.04 on water and DPPC, with no or the real
  share of outliers. DPPC reads 0.01–0.04 high, and the film and ten times the outliers read up to 0.06 high.
  The scale model's proportional X is not reliable below about 0.5 %, so the real X of the scale model is
  quoted only as a floor.
- **The likelihood interval undercovers:** it holds the truth in 15–45 % of estimates at X > 0, against 68 %
  (`curv_coverage68`). The real intervals are therefore the bootstrap over runs.
- **Pulls** (`pulls.csv`): today's joint fit on C61's six joins, 400 replicates each, with the same random
  draws in every case; ± is a bootstrap over replicates:

  | case | smooth join | fringed joins (mean) |
  |---|---|---|
  | no excess | 1.12 ± 0.04 | 1.01 ± 0.02 |
  | σ × 1.12 | 1.19 ± 0.04 | 1.09 ± 0.02 |
  | σ × 1.12 + core 0.14 % | 1.19 ± 0.05 | 1.10 ± 0.02 |
  | σ × 1.12 + core 0.14 % + 0.3 % outliers | 1.19 ± 0.05 | 1.10 ± 0.02 |
  | core 1 % (C61's working value) | 1.67 ± 0.06 | 1.22 ± 0.02 |

  - C61's own table, at 400 replicates with its seeds, gave 1.64 at 1 %.
  - The scale on σ does almost all of it. The 0.14 % core and the wild points barely move the pull SD: the
    joint fit's χ² inflation absorbs them, at a cost in error.

## For the budget (main man, tools man; no number changes here: rule 12, the owner's word)

- **A scale on the counting σ of about 1.1** is what the within-scan data support. It is the solid part.
- **A fixed 1 % for every point** (C61's working value) is ten times the within-scan core for well-counted
  points, and gives the joint fit a pull SD of 1.67, well above the real 1.24.
- **Outliers need handling of their own.** Up to about 0.3 % of points are tens of % off, part of them a
  curve sharper than six points can follow rather than a bad measurement. A Student-t or
  core-plus-outlier likelihood in the joint fit, or flagging such points, would serve better than widening
  every point's error.
- **What changes between scans is not covered.** A study that records the sample height, the footprint and
  the background at each point would be needed before a between-scan term goes into the budget.
- **The next study** (rule 12): the joint fit with σ × 1.1 and a robust likelihood, against C56's 1091 real
  splits and C61's synthetic joins.

## Not shown, and why

- **Between scans (shared Qz):** set aside by the owner (above). The estimator stays in
  `tests/tools/excess_scatter.py` with its tests, for a later study that records the confounders.
- **Below Qz 0.04:** left out, because the edge's curvature biases the estimator. C55 covers the edge.
- **Points with y/σ < 5:** left out, because ln y is linear in the noise only when the noise is small. This
  removes the faintest points at the highest Qz.

## Open

1. Is the ~10 % scale on σ known at the beamline, for example from the Pilatus counting or the background
   boxes? A short repeat of one Qz point (20 frames, the sample still) would settle the counting part.
2. Pair the points with the height scans around them (sample-height drift; the height scans' ROI data are
   unrestricted), to test the owner's first candidate directly.
3. Repeated scans with the sample height, footprint and absorber recorded, to measure what changes between
   scans on solid ground.
