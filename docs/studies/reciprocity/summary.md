# Study: beam damage or a sample changing by itself? (F76)

Tools man, 2026-11-25, for main man's F76 assignment. Everything below is
**measured** by `tests/tools/reciprocity_study.py` on synthetic burns with a
known law of change (300 replicates per condition), except section 5,
which uses the public NX school burns. **No default changes**: the test is
offered to scripts; the window's several-burns view is the GUI manager's
(F98).

**Regenerate:**

    python tests/tools/reciprocity_study.py --out docs/studies/reciprocity        # about 1.5 min

The code is `lss_core/reciprocity.py` (`dose_or_time`, `from_result`,
`drift_rate`); its tests are `tests/test_reciprocity.py`; the synthetic
burns are `tests/synthetic/burn_pairs.py`. The tool is in the Tools menu
under Burn tests.

## The question

The owner: "some reduction analysis of the various absorber burn tests …
would help decide if sample is changing or xray beam is damaging sample".
Damage by the beam follows the dose, flux × time; a sample changing by
itself follows the clock. So burns of one kind of sample at different
absorbers should coincide against dose in the first case and against time
in the second (figure R1).

## The test

1. Each burn's drift rate per second: the slope of ln y for intensity and
   width (an exponential change's rate exactly), the slope of y for a
   position; errors scaled by the burn's own scatter.
2. Across burns, rate = k · flux^β, β profiled: **β = 1 is the dose,
   β = 0 is time**. This is the convention of the real-burn study
   (`docs/studies/xr_burns/`, C54, when merged), so the two agree.
3. The verdict, as C54 decides it: **dose** when β = 1 passes (p ≥ 0.05)
   and β = 0 fails; **time** the reverse; **cannot tell** both pass;
   **neither** both fail (a dose-rate effect: β̂ says where); **no change**
   when no burn moves by 3σ; **opposite signs** when one rises and
   another falls. How strongly: β̂ with its Δχ² = 1 and 3.84 intervals, and
   the Akaike weight of the dose against time.
4. **Strip scatter:** two strips of one sample at one flux differ by more
   than their counting (C54: 88 %/h on real burns). It can be passed as one
   constant τ (`strip_scatter`) or as a share ρ of each burn's rate
   (`strip_relative`).

**The assumption:** reciprocity (the Bunsen–Roscoe law): the same dose
gives the same change at any rate. It fails through dose-rate effects
(β ≠ 1) and, at a liquid surface, through molecules exchanging into the
footprint. The test measures β; it does not assume it is 1.

## 1. How often is each truth called right?

Share of replicates called right (dose → "dose", time → "time"; β = 0.5,
β = 2 and a mixture → "neither"; no change → "no change"). Baseline: two
burns ×4.68 apart (as NX 14 and 15), 21 frames of 10 s, 1 % noise per
frame, a 5 % fall over the lower-flux burn, no strip scatter. Each block
changes one thing.

| Condition | dose | time | β 0.5 | β 2 | mixture | none |
|---|---|---|---|---|---|---|
| flux ×2 | 0.96 | 0.81 | 0.01 | 1.00 | 0.02 | 0.99 |
| **flux ×4.68 (baseline)** | 0.95 | 0.94 | 0.92 | 1.00 | 0.69 | 1.00 |
| flux ×10 | 0.98 | 0.97 | 0.99 | 1.00 | 0.83 | 0.99 |
| flux ×20 | 0.97 | 0.97 | 1.00 | 1.00 | 0.83 | 0.99 |
| 3 burns over ×10 | 0.97 | 0.97 | 1.00 | 1.00 | 0.92 | 0.99 |
| 4 burns over ×10 | 0.97 | 0.95 | 1.00 | 1.00 | 0.91 | 0.99 |
| 11 frames | 0.97 | 0.89 | 0.61 | 1.00 | 0.37 | 1.00 |
| 41 frames | 0.96 | 0.96 | 1.00 | 1.00 | 0.95 | 1.00 |
| 0.3 % noise | 0.94 | 0.97 | 1.00 | 1.00 | 1.00 | 1.00 |
| 3 % noise | 0.96 | **0.17** | 0.01 | 1.00 | 0.02 | 1.00 |
| 2 % fall | 0.94 | **0.35** | 0.01 | 1.00 | 0.10 | 1.00 |
| 20 % fall | 0.96 | 0.97 | 1.00 | 1.00 | 1.00 | 1.00 |

- **With the strips alike, two burns about ×5 apart settle dose against
  time** about 95 % of the time. Wrong calls between dose and time are rare
  (at most 2 %): a miss is "neither" or "cannot tell", not the other answer.
- **Time is the harder truth to show.** Under time the lower-flux burn
  changes as much as the higher. When the change is small or the frames
  noisy (2 % fall, 3 % noise), neither burn moves by 3σ, and the honest
  answer is "no change" or "cannot tell". Under the dose, the higher-flux
  burn moves ×4.7 more and carries the call.
- **A dose-rate effect** (β = 0.5) needs a span of ×5 or more, or more
  frames. At ×2 it is called "dose" or "time" about half the time each:
  a span of ×2 cannot tell β = 0.5 from either.
- **A mixture** of a dose and a time process, equal at the lower flux, is
  called "dose" in 17–31 % of replicates at ×4.7 to ×20 (the dose part
  dominates at the higher flux), "neither" otherwise.
- **β's errors are honest:** the Δχ² = 1 interval covers the truth 64–77 %
  of the time (0.68 ideal) in every condition without strip scatter, and
  the pull SD of β̂ is 0.9–1.2 in most. It falls to 0.5–0.6 where a time
  truth barely changes (3 % noise, 2 % fall): β̂ is then held by the grid's
  edge (figure R3).

## 2. Strip scatter

Four burns over ×8, the rate of each strip off by a random 20 % or 50 %
(relative):

| Condition | dose | time | β 0.5 | β 2 | mixture | none |
|---|---|---|---|---|---|---|
| 20 %, ignored | **0.12** | 0.59 | 0.97 | 1.00 | 0.92 | 1.00 |
| 20 %, as one τ | 0.84 | 0.96 | 0.42 | 0.97 | 0.19 | 0.99 |
| 20 %, as ρ | **0.93** | **0.93** | 0.79 | 1.00 | 0.45 | 1.00 |
| 50 %, ignored | 0.02 | 0.13 | 0.94 | 0.95 | 0.94 | 0.98 |
| 50 %, as one τ | 0.55 | 0.16 | 0.11 | 0.65 | 0.14 | 0.99 |
| 50 %, as ρ | **0.80** | **0.81** | 0.02 | 0.80 | 0.04 | 1.00 |

- **Ignoring a real strip scatter wrecks the test.** The pure laws fail on
  rates that scatter beyond their counting, and nearly everything becomes
  "neither" (dose called right 12 % of the time at 20 %). This is C54's
  finding: with counting errors alone, 8 of its 19 real series were
  "neither".
- **Admitting it in the right form restores the calls and the
  calibration.** As ρ, the pull SD of β̂ is 1.03–1.09 and the coverage
  0.66–0.69 (0.68 ideal). As one constant τ (the scatter at the median rate), the fast
  burns get too little and the slow ones too much (pull SD 1.4–1.5,
  coverage 0.52). C54 used one constant and noted it "is far too large for
  the slowly changing series and maybe too small for the fast ones"; the
  relative form answers that.
- **At 50 %, four burns over ×8 still tell dose from time** (0.80 and
  0.81 called right, the other law at most 0.03), but not a dose-rate
  effect: β = 0.5 is then called dose or time in 0.71 of replicates, its
  interval reaching one of them. A steep β = 2 is called right in 0.80, with
  its pulls spoilt (SD 3.6) by intervals cut at the grid's edge.
- **The ρ rows changed on 2026-11-25.** The variance ρ k φ^β depends on
  the model, so k is now fitted by maximum likelihood, and the verdict uses
  likelihood-ratio tests: 'dose' means β = 1 inside the 95 % interval and
  β = 0 outside. Before, k was fitted by least squares reweighted on χ²
  alone, which can shrink χ² by inflating k's own variance, and the
  verdicts used goodness-of-fit p-values. At 20 %, before → after: dose
  0.96 → 0.93, time 0.94 → 0.93, β 0.5 0.58 → 0.79. At 50 %: dose 0.55 →
  0.80, time 0.53 → 0.81. Coverage 0.66–0.73 → 0.61–0.69. The τ rows and
  every other section are unchanged (rerun, byte for byte apart from the ρ
  rows). The reason it mattered: C54's real strips scatter by about their own rate (ρ ≈ 1.1).

## 3. Few frames, little change

With 11 frames, or a 2 % fall, or 3 % noise per frame, the dose is still
called (0.94–0.97) but time, β 0.5 and mixtures mostly are not. The rule:
the burn at the **lower** flux must change by several of its own σ for a
"time" call to be possible.

## 4. What would settle it on real samples

- **Two burns at fluxes ×5–10 apart, 21 frames or more each, on one kind of
  sample**, if the strips agree. With strip scatter like C54's, **repeat
  each flux on two strips** and pass the scatter as ρ. Four burns over ×8
  then tell dose from time at 20 % strip scatter, but not at 50 %.
- **Alternate the order** (high, low, high, low), so that a sample ageing
  over the series is not aliased with the flux (C54's confound).
- This is what C54 recommends from the real data too. DATA_NEEDS row 14
  states it for the local data agent and for F77, which needs the same
  pairs.

## 5. NX school burns 14 and 15

Two GID burns of one spot, absorbers 12 and 8 (flux ×4.68 by the
calibrated foils; 15 was measured after 14, on the same spot):

| Quantity | rates (per s) | β | verdict, counting errors | with a 10 % strip scatter |
|---|---|---|---|---|
| position | 1.09e-5 and 4.03e-5 Å⁻¹ | **0.85 [0.80, 0.89]** | neither (Akaike weight 1.00 on the dose; p 0.004 for β = 1, 10⁻¹⁵⁴ for β = 0) | **dose** [0.63, 1.15] |
| width | 0 ± 1.0e-4 and 7.7e-4 | 3.3 [1.3, ≥ 4] | dose (β = 1 passes at p 0.09, β = 0 fails) | dose |
| intensity | −1.2e-4 ± 1.2e-4 and −0.7e-4 ± 0.7e-4 | — | no change | no change |

- **The position drifts with the dose, not with time.** β = 0 is excluded
  beyond doubt. β = 0.85 is 15 % short of reciprocity. Such a sub-linear
  rate could be a dose-rate effect, but this pair cannot tell it from two
  other explanations. One is saturation: 15 started with 14's dose on the
  same spot. The other is any strip scatter, since there is no repeat to
  measure it.
- **The width** grows only in 15. Its β is poorly bounded, but time is
  excluded.
- **The intensity** changes in neither burn (figure R5).

## 6. Recommendation

1. **Offer `dose_or_time`** wherever several burns of one sample at
   different absorbers are at hand (the GUI manager's F98 view). Show the
   verdict, β with its interval, and the strip-scatter option.
2. **Pass the strip scatter as ρ (relative)** when it is known or
   measured. Leave it at 0 only when the burns are repeats of one spot,
   and say so: then "neither" with all the weight on one law means
   "close, but not pure".
3. **For F77** (predicting a safe absorber from a short high-flux test):
   the prediction needs β = 1. This study shows that two burns ×5–10
   apart measure β to ±0.06–0.15 (SD over replicates) when the strips
   agree, and four burns over ×8 to ±0.15–0.17 at 20 % strip scatter. C54's real β run from 0.2 to more
   than 2, so a prediction must measure β on the sample first.

## Figures

| Figure | File | What it shows |
|---|---|---|
| R1 | `R1_anatomy.png` | two burns against time and against dose, under a dose truth and a time truth, with χ²(β) |
| R2 | `R2_calls.png` | the share of each verdict, per truth and design |
| R3 | `R3_beta_pulls.png` | β̂'s pull SD and the coverage of its interval, per condition |
| R4 | `R4_strip.png` | the strip scatter ignored, as one τ, and as ρ |
| R5 | `R5_nx.png` | NX school burns 14 and 15: rates against flux with the two pure laws and β̂ |

The numbers behind them are `results.csv` (per design, condition and
truth: the share of each verdict, β̂'s mean and SD, the pull SD, the
coverage) and `numbers.json` (with NX).
