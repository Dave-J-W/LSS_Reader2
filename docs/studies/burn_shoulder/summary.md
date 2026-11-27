# A GID burn peak on a shoulder: which estimator reads the truth? (P44)

Tools man, 2026-11-27. Synthetic burns with a known truth, and NX school burns 14 and 15 as the public
real check. **Measured** throughout: every number is from one run of the tool (`results.csv`, `nx.csv`,
`reference_noise.csv`, `numbers.json`, `numbers_reference.json` beside this file). The whole chain on NX
burn 15, from a raw frame to the verdict, with the statistics explained for a newcomer, is
[`walkthrough.md`](walkthrough.md).

## The question

A GID burn test measures one spot 21 times and asks whether the beam changes the peak. The peak is sharp
and sits on a broad hump, the **shoulder**. The reader's estimator, the **template**, fits each frame as
the mean frame's whole shape (peak and shoulder) scaled by A, slid by δ and stretched by w. When the peak
widens, the stretch widens the shoulder too, and A·w counts the shoulder's extra width as intensity (P44).
The **split** estimators fit a Gaussian to the shoulder beside the peak (`burn.split_shoulder`) and stretch
only the rest. Do they read the truth, on which shoulders, at which counts, and what do they say about NX?

## The estimators

| name | each frame is fitted as | per frame |
|---|---|---|
| `template` (the reader's default) | A × the mean frame's shape (stretched by w, slid by δ) + a line | 5 parameters |
| `moments` (the legacy test) | no fit: the window's sum, centroid and second moment above a chord | — |
| `split` | A × the peak's shape P (stretched, slid) + **B** × the shoulder S (not stretched) + a line | 6 |
| `split_fixed` | the same with B = 1: the shoulder assumed steady | 5 |
| `fit` (NX only) | one Gaussian + a line | 5 |

The split's intensity is A·w × P's area, its FWHM w × P's FWHM, its position P's centroid + δ. `split`
also reports the shoulder (B × S's area) as a fourth quantity.

## The design

- **The burns** (`tests/synthetic/burn_profiles.py`): 21 frames of 10 s, a peak of FWHM 0.016 Å⁻¹ at
  1.466 on a shoulder of σ 0.04 at 1.47, a flat floor. Each change grows linearly over the test.

| case | what changes | true change of the intensity, FWHM |
|---|---|---|
| `none` | nothing (false alarms) | 0, 0 |
| `fade` | the peak's area −20 % | −20 %, 0 |
| `broaden` | the peak's FWHM +30 % at constant area | 0, +30 % |
| `shift` | the peak's centre +0.004 Å⁻¹ | 0, 0 |
| `shoulder` | a fade of −20 % under a shoulder 3 × stronger | −20 %, 0 |
| `background` | the flat floor +50 % | 0, 0 |
| `shoulder_grows` | the shoulder +50 %, the peak steady | 0, 0 (shoulder +50 %) |
| `both_fade` | the peak −20 % and the shoulder −30 % | −20 %, 0 (shoulder −30 %) |
| `nx15_like` | FWHM +20 % and area −13 %: NX burn 15 as the split reads it | −13 %, +20 % |

- **Part A**: every case on four shoulder shapes (Gaussian, Lorentzian, lopsided, a Gaussian with a
  narrow second hump beside the peak), at high counts: monitor 1e7, where one frame's intensity is known
  to 0.19 %. What remains there is bias, not noise.
- **Part B**: the Gaussian shoulder at fewer counts: monitor 1e6 (0.6 % per frame), **6e4 (2.1 %, as NX
  burn 15: 2.0 %)** and **1e4 (3.9 %, as NX burn 14: 3.8 %)**. The match is of one frame's template
  intensity error (`NX_MONITORS`, tested).
- **300 replicates per cell.** Each replicate goes through the reader's own trend analysis
  (`burn.analyse`, errors from the scatter: the GID default). The change over the test is read from the
  straight line through the frames, with its σ; the verdict is the reader's: **changing** when a line beats
  a constant by more than 2 in AICc (`trends.STABLE_DELTA`).
- **Per cell**: the bias (mean read − truth) and SD of the change, the pull SD ((read − truth)/σ: 1 when
  the errors are honest), the share of 95 % intervals (±1.96σ) that hold the truth, and the share of burns
  called changing. These are explained step by step in the walkthrough, steps 5 and 6.

Changes are in **percentage points** (pp): a fade of −20 % read as −13.6 % has a bias of +6.4 pp.

## 1. A Gaussian shoulder (S1)

![S1](S1_bias_by_case.png)

**The intensity: bias of the change over the test** (pp, 300 burns, monitor 1e7; the SD is 0.10–0.19 pp
for every estimator):

| case | truth | template | moments | split | split_fixed |
|---|---|---|---|---|---|
| `none` | 0 | −0.00 | −0.00 | −0.00 | −0.01 |
| `fade` | −20 | **+6.43** | +11.68 | −0.00 | −0.00 |
| `broaden` | 0 | **+14.44** | −0.00 | +0.13 | +0.02 |
| `shift` | 0 | +0.23 | −0.01 | −0.01 | −0.01 |
| `shoulder` | −20 | **+10.76** | +16.16 | −0.01 | −0.01 |
| `background` | 0 | −0.00 | +0.00 | −0.01 | −0.01 |
| `shoulder_grows` | 0 | +15.62 | +29.22 | −0.01 | **+24.20** |
| `both_fade` | −20 | −3.28 | −5.85 | −0.00 | **−10.76** |
| `nx15_like` | −13 | **+13.19** | +7.60 | +0.03 | +0.00 |

**The FWHM** (pp): the template reads a +30 % broadening as +23.7 % (−6.32) and the NX 15-like +20 % as
+14.5 % (−5.52); the moments read almost none of either (−28.59, −16.69). The split is within 0.1 pp in
every case; `split_fixed` too, except when the shoulder changes (+16.22 when it grows, −9.50 when it fades).

**The position** (10⁻⁴ Å⁻¹): the template reads a false drift of +6.6 when the peak broadens and +4.4 on
the NX 15-like burn, and misses 1.6 of a true 40 when it shifts; the moments miss 21.8 of the 40 (the
shoulder holds the centroid back). Both splits are within 0.01.

**What it shows:**
- **The template is biased whenever the peak's width or the shoulder changes, and also when the peak
  simply fades** (it scales the steady shoulder with the peak: a −20 % fade reads −13.6 %). On the NX
  15-like burn it reads −13 % as −0.2 %. It is unbiased only when nothing changes or the floor changes.
- **The split reads every quantity of every case to 0.13 pp or better**, including the shoulder itself
  (`shoulder_grows`: +50 % read to 0.00 pp; `both_fade`: −30 % to 0.01).
- **`split_fixed` is as good as the split while the shoulder is steady, and misleads when it is not**:
  a shoulder growing 50 % under a steady peak reads as a peak gaining 24 % and broadening 16 %. So the two
  disagreeing is the sign of a changing shoulder.
- **The price is precision:** the split's SD is 1.06–1.47 × the template's (`split_fixed`: 0.84–1.29 ×).

## 2. Other shoulder shapes (S2)

![S2](S2_bias_by_shape.png)

The split fits a Gaussian to the shoulder. When the shoulder is not one, part of it is left in P and
stretched with the peak. **The intensity's bias** (pp, monitor 1e7):

| shape | case | template | moments | split | split_fixed |
|---|---|---|---|---|---|
| Lorentzian | `fade` | +7.2 | +10.5 | +1.2 | +1.8 |
| | `broaden` | +16.2 | −0.0 | +4.4 | +2.0 |
| | `shoulder` | +15.3 | +15.4 | +3.8 | +5.2 |
| | `shoulder_grows` | +19.2 | +26.3 | +3.1 | +22.8 |
| | `nx15_like` | +16.0 | +6.8 | +3.6 | +2.6 |
| lopsided | `fade` | +6.4 | +9.8 | +2.2 | +2.6 |
| | `broaden` | +10.8 | −0.0 | +4.6 | +3.0 |
| | `shoulder` | +12.2 | +14.9 | +5.2 | +6.1 |
| | `shoulder_grows` | +16.8 | +24.5 | +5.7 | +21.3 |
| | `nx15_like` | +11.9 | +7.2 | +5.2 | +4.5 |
| two humps | `fade` | +10.8 | +12.5 | +4.6 | +4.3 |
| | `broaden` | +12.9 | +0.0 | +5.6 | +3.2 |
| | `shoulder` | +16.4 | +16.8 | +11.5 | +11.4 |
| | `shoulder_grows` | +28.7 | +31.2 | +11.7 | +39.3 |
| | `nx15_like` | +16.9 | +8.6 | +7.7 | +6.3 |

**What it shows:**
- **The split is less biased than the template in every case where the intensity changes or the peak
  broadens,** on every shape: by 3.7–6.2 × on the Lorentzian shoulder, 2.3–3.0 × on the lopsided one and
  1.4–2.5 × with two humps (the ratio of the absolute biases over `fade`, `broaden`, `shoulder`,
  `shoulder_grows`, `both_fade` and `nx15_like`). Its worst is +5.7 pp on the lopsided shoulder and
  +11.7 pp with two humps.
- **One exception, small:** a pure shift on the two-hump shoulder, where the split reads a false −3.0 pp
  and the template +2.2 pp (lopsided: −0.8 against +2.5).
- **With two humps no estimator copes:** the narrow hump beside the peak is neither shoulder nor peak.
- **The moments read a broadening at constant area without bias on every shape** (a sum does not care
  about the width), but nothing else: they miss most of any fade and all of any broadening.
- **The FWHM** (`results.csv`): the split's bias on a +30 % broadening is +2.1 pp (Lorentzian), −0.8
  (lopsided), −4.4 (two humps), against the template's +3.6, −7.8, −9.3.
- **A broadening moves the split's shoulder when the shoulder is not a Gaussian:** the shoulder reads a
  false fade of 6.3 pp (Lorentzian), 4.9 (lopsided) and 4.6 (two humps) on the +30 % broadening, against
  0.1 on the Gaussian shoulder. So a shoulder change read alongside a broadening is not proof that the
  shoulder changed (hand-off 10, question 2).

## 3. Verdicts and coverage (S3)

![S3](S3_verdicts_coverage.png)

**The intensity, Gaussian shoulder, monitor 1e7:** share called "changing" / share of 95 % intervals that
hold the truth / pull SD. Bold: the verdict is wrong in most burns.

| case | template | moments | split | split_fixed |
|---|---|---|---|---|
| `none` | 5 % / 93 % / 1.06 | 6 % / 93 % / 1.08 | 6 % / 94 % / 1.06 | 6 % / 93 % / 1.03 |
| `fade` | 100 % / 0 % / 13.7 | 100 % / 0 % / 16.8 | 100 % / 92 % / 1.08 | 100 % / 90 % / 1.14 |
| `broaden` | **100 %** / 0 % / 5.09 | 5 % / 94 % / 1.03 | 17 % / 81 % / 1.25 | 9 % / 87 % / 1.20 |
| `shift` | 29 % / 65 % / 0.97 | 4 % / 94 % / 1.01 | 4 % / 93 % / 1.06 | 5 % / 93 % / 1.03 |
| `shoulder` | 100 % / 0 % / 12.8 | 100 % / 0 % / 40.3 | 100 % / 93 % / 1.09 | 100 % / 89 % / 1.19 |
| `background` | 6 % / 94 % / 1.06 | 5 % / 94 % / 1.07 | 4 % / 94 % / 1.02 | 6 % / 93 % / 1.04 |
| `shoulder_grows` | **100 %** / 0 % / 18.5 | **100 %** / 0 % / 36.7 | 7 % / 91 % / 1.15 | **100 %** / 0 % / 30.6 |
| `both_fade` | 100 % / 0 % / 8.04 | 100 % / 0 % / 10.3 | 100 % / 94 % / 1.00 | 100 % / 0 % / 23.3 |
| `nx15_like` | **0 %** / 0 % / 4.74 | 100 % / 0 % / 11.5 | 100 % / 89 % / 1.20 | 100 % / 87 % / 1.26 |

**What it shows:**
- **The template's verdicts are wrong in three cases:** it calls a broadening at constant area and a
  growing shoulder "changing" every time, and the NX 15-like fade "stable" every time. Its intervals never
  hold the truth when anything but the floor changes.
- **The split's verdicts are right in every case,** and its intervals hold the truth in 81–94 % of burns.
  Its pull SD is 1.00–1.25: its σ is up to 25 % too small, worst when the peak broadens, where 17 % of
  steady burns are called changing (5 % is the rate when nothing changes).
- **No false alarms when nothing changes:** 4–6 % for every estimator, as the AICc threshold gives.

## 4. Fewer counts (S4)

![S4](S4_counts.png)

Part B repeats the Gaussian shoulder at fewer counts. **The intensity** (pp: bias ± SD, 300 burns per cell;
then the share called "changing" and the share of 95 % intervals holding the truth):

| case | monitor | template | moments | split | split_fixed |
|---|---|---|---|---|---|
| `none` | 1e6 | −0.02 ± 0.29, 4 %, 96 % | −0.02 ± 0.39, 4 %, 95 % | −0.01 ± 0.41, 4 %, 95 % | −0.02 ± 0.32, 3 %, 96 % |
| | 6e4 | −0.01 ± 1.34, 3 %, 95 % | +0.11 ± 1.58, 6 %, 93 % | −0.09 ± 1.68, 3 %, 95 % | +0.02 ± 1.38, 3 %, 96 % |
| | 1e4 | +0.16 ± 2.90, 4 %, 94 % | +0.30 ± 4.00, 5 %, 92 % | −0.00 ± 4.10, 5 %, 93 % | +0.22 ± 3.43, 6 %, 93 % |
| `fade` (−20 %) | 1e6 | +6.49 ± 0.32, 100 %, 0 % | +11.67 ± 0.38, 100 %, 0 % | −0.01 ± 0.39, 100 %, 94 % | −0.01 ± 0.32, 100 %, 93 % |
| | 6e4 | +6.93 ± 1.23, 100 %, 0 % | +11.74 ± 1.54, 100 %, 0 % | +0.01 ± 1.52, 100 %, 93 % | +0.08 ± 1.26, 100 %, 94 % |
| | 1e4 | +7.32 ± 2.68, 98 %, 23 % | +11.79 ± 3.73, 54 %, 9 % | +0.08 ± 3.51, 100 %, 94 % | +0.27 ± 2.99, 100 %, 94 % |
| `broaden` (0) | 1e6 | +14.33 ± 0.49, **100 %**, 0 % | −0.02 ± 0.39, 4 %, 95 % | +0.06 ± 0.57, 6 %, 90 % | −0.02 ± 0.40, 5 %, 91 % |
| | 6e4 | +11.71 ± 2.76, **99 %**, 0 % | +0.13 ± 1.58, 5 %, 94 % | −1.78 ± 2.57, 18 %, 79 % | −0.66 ± 1.74, 10 %, 89 % |
| | 1e4 | +2.16 ± 3.53, 9 %, 89 % | +0.20 ± 3.82, 5 %, 94 % | **−9.37** ± 4.74, **55 %**, 37 % | −4.96 ± 3.69, 29 %, 66 % |
| `nx15_like` (−13 %) | 1e6 | +13.01 ± 0.47, **5 %**, 0 % | +7.58 ± 0.37, 100 %, 0 % | −0.06 ± 0.48, 100 %, 91 % | −0.05 ± 0.38, 100 %, 89 % |
| | 6e4 | +10.45 ± 2.07, **32 %**, 0 % | +7.76 ± 1.54, 88 %, 0 % | −2.00 ± 2.19, 100 %, 75 % | −0.84 ± 1.63, 100 %, 85 % |
| | 1e4 | +5.75 ± 3.10, 63 %, 49 % | +7.73 ± 3.68, **24 %**, 48 % | −6.14 ± 4.22, 98 %, 56 % | −3.34 ± 3.44, 99 %, 74 % |

**The FWHM** falls short as well when it changes: on the +30 % broadening the split reads −3.6 pp at 6e4
and −18.7 pp at 1e4 (template −10.2, −22.5); on the NX 15-like +20 %, −4.4 and −13.4 (template −9.2,
−15.7).

**What it shows:**
- **No false alarms at any count:** 3–6 % of steady burns are called changing, by every estimator, and
  the pull SDs stay within 0.95–1.09.
- **A plain fade is read without bias by both splits at every count** (within 0.3 pp), with 93–94 % of
  intervals holding the truth. The template keeps its +6.5 to +7.3 pp of P44.
- **When the peak's width changes, every fitted estimator drifts with the counts.** The split reads the
  NX 15-like fade 2.0 pp too deep at NX 15's counts (6e4) and 6.1 pp at NX 14's (1e4), and only 75 % and
  56 % of its intervals hold the truth. On a broadening at constant area it calls 18 % (6e4) and 55 %
  (1e4) of the burns changing, against 5 % when nothing changes. `split_fixed` drifts about half as far
  (−0.8 and −3.3 pp on `nx15_like`).
- **The template's P44 shrinks at low counts, for the wrong reason:** the same drift cancels part of it
  (+13.0 pp at 1e6, +10.5 at 6e4, +5.8 at 1e4). It still calls the NX 15-like fade "changing" in only
  32 % of the burns at NX 15's counts, where the splits call it in all.
- **The drift is the reference's noise** (section 6): the mean frame every frame is fitted against is noisy
  at these counts, and the stretch w turns its noise into a bias. A noiseless reference removes it.
- **For NX 15** (6e4), if the synthetic noise transfers: the split's −13.3 % would be about −11 % and its
  +21 % broadening about +25 %. Section 6 shows that real frames may not follow the synthetic noise
  model.

## 5. NX school burns 14 and 15 (S5)

![S5](S5_nx.png)

The real check: NX school burns 14 and 15, 21 frames of 10 s on one spot, the second at 4.7 × the flux
(`nx.csv`). Change over the burn ± σ (straight line), and the verdict:

| burn | estimator | intensity | FWHM | position (10⁻⁴ Å⁻¹) | frames' χ²/dof |
|---|---|---|---|---|---|
| 14 | template | −2.5 % ± 2.3 stable | +0.1 % ± 1.5 stable | +23.5 changing | 1.04 |
| | moments | −0.3 % ± 2.3 stable | +3.4 % ± 2.2 stable | +15.5 changing | — |
| | fit (one Gaussian) | −9.1 % ± 3.4 changing | −9.8 % ± 4.7 stable | +27.3 changing | 9.57 |
| | **split** | **−0.0 % ± 3.4 stable** | −1.6 % ± 3.3 stable | +25.0 changing | 1.03 |
| | split_fixed | −3.7 % ± 2.6 stable | −5.2 % ± 3.2 stable | +25.8 changing | 1.01 |
| 15 | template | **−1.5 % ± 1.5 stable** | +17.8 % ± 1.5 changing | +86.6 changing | 4.24 |
| | moments | −2.4 % ± 1.2 stable | +10.3 % ± 1.2 changing | +25.4 changing | — |
| | fit (one Gaussian) | −5.8 % ± 1.9 changing | +15.0 % ± 4.1 changing | +82.3 changing | 41.3 |
| | **split** | **−13.3 % ± 2.4 changing** | +21.4 % ± 4.0 changing | +96.0 changing | **2.17** |
| | split_fixed | −15.2 % ± 1.3 changing | +16.9 % ± 2.6 changing | +95.8 changing | 2.29 |

**The split's shoulder:** burn 14 −5.9 % ± 3.3 % stable, burn 15 −2.8 % ± 2.8 % stable. B per frame lies
in 0.89–1.11 (14) and 0.96–1.15 (15). The shoulder found has a FWHM of 0.098 and 0.103 Å⁻¹ (σ 0.042,
0.044), 8.5 and 6.9 × the peak's (burn 14: 0.0115 Å⁻¹, burn 15: 0.0150).

**What it shows:**
- **Burn 15 is P44 on real data.** The peak broadens by about 20 % under every estimator that fits it.
  - The template reads the intensity as steady.
  - Both splits read a fade of 13–15 %, and the one-Gaussian fit 6 %.
  - The split describes the frames twice as well as the template (χ²/dof 2.17 against 4.24).
- **Burn 14 is steady** under every estimator but the one-Gaussian fit, which does not describe the frames
  (χ²/dof 9.6).
- **The shoulder does not change in either burn,** and the free and fixed splits agree within their
  errors. By section 1, that agreement is what a steady shoulder gives.
- **The position drift is about 10 % larger under the split on burn 15** (+96.0 against +86.6). The
  drift per dose of burn 15 over burn 14 (flux ratio 4.68) becomes 0.82 instead of 0.79. That is not a
  change to F76's reading of these two burns.
- **One frame's intensity error** is 3.8 % (burn 14) and 2.0 % (burn 15) under the template
  (`frame_rel_error`). That is the error the synthetic monitors 1e4 and 6e4 have (section 4).

## 6. The reference's noise (S6)

![S6](S6_reference.png)

Section 4 shows biases at low counts that high counts do not have. Part R (`--only R`) asks where they
come from. Every frame is fitted against the **reference**, the mean of the 21 frames, and that mean
carries its own counting noise. Each synthetic burn is read three ways:
- against the frames' mean, as the reader does;
- against the mean smoothed by a weighted spline inside the window (χ² ≈ the number of points;
  `smooth_reference`);
- against the noiseless mean.

The table gives the intensity's bias in pp (100 burns per row, straight line through the frames,
`reference_noise.csv`). The mean frame's noise is its median σ as a share of its peak (`mean_frame_noise`):
0.03 %, 0.35 % and 0.85 % at monitors 1e7, 6e4 and 1e4. NX 15's is 0.29 %, NX 14's 0.51 %.

| case, monitor | template: mean | smoothed | noiseless | split: mean | smoothed | noiseless |
|---|---|---|---|---|---|---|
| `fade`, 1e7 | +6.43 | +6.48 | +6.42 | −0.00 | +0.00 | −0.00 |
| `fade`, 6e4 | +6.75 | +6.93 | +6.57 | +0.12 | +0.09 | +0.08 |
| `fade`, 1e4 | +6.98 | +7.22 | +6.84 | +0.06 | +0.04 | +0.02 |
| `nx15_like`, 1e7 | +13.39 | +13.37 | +13.41 | +0.02 | +0.04 | +0.03 |
| `nx15_like`, 6e4 | **+10.42** | +12.54 | +13.53 | **−1.77** | −0.28 | +0.03 |
| `nx15_like`, 1e4 | **+6.52** | +12.71 | +14.48 | **−5.87** | −0.85 | +0.49 |

The standard errors are 0.01–0.02 pp at 1e7, 0.12–0.25 at 6e4 and 0.29–0.50 at 1e4.

**What it shows (synthetic):**
- **When the peak's width changes, the reference's noise pulls the read change down,** and more as the
  counts fall: the split by −1.8 pp at NX 15's noise and −5.9 pp at NX 14's.
  - A noiseless reference reads the truth.
  - A plain fade, where the stretch stays near 1, shows nothing.
- **For the template the pull hides part of P44:** its +13.5 pp bias reads as +10.4 and +6.5.
- **The smoothed mean removes most of it** (split −0.28 and −0.85 pp), at no cost at high counts.

**On NX it does not behave as on synthetic burns** (`reference_nx.csv`, the right panel). Each burn is
re-read against its smoothed mean frame, through the reader's own trend analysis:

| | template: mean | smoothed | split: mean | smoothed |
|---|---|---|---|---|
| burn 14 | −2.5 % ± 2.3 stable | −6.1 % ± 3.0 stable | −0.0 % ± 3.4 stable | −5.5 % ± 3.8 stable |
| burn 15 | −1.5 % ± 1.5 stable | −2.3 % ± 1.3 stable | −13.3 % ± 2.4 changing | −13.6 % ± 2.5 changing |

The **shift** (smoothed − mean, on the same burn) is what to compare.
- **Synthetic, at 6e4**, close to NX 15's noise: the split's shift is +1.49 ± 1.00 pp per burn and the
  template's +2.12 ± 1.49.
  - **NX 15's shifts are −0.27 and −0.82 pp, 1.8 and 2.0 SD below.**
- **NX 14's peak does not broaden,** so the `fade` rows apply: a shift of 0 ± 0.5–1.9 pp.
  - **NX 14's split shift is −5.5 pp, about 3 SD from it.**

So on NX the smoothing moves the reads down, where on synthetic burns it moves them up. Either the real
mean frames carry less of the noise that matters, or the spline does not suit a real mean frame (it may
round a peak sharper or less Gaussian than the synthetic one), or both. Two burns cannot tell these
apart; hand-off 10 asks for every real burn. **Until then the smoothed reference is not an option to
offer.** The NX numbers of section 5 stand as read.

## 7. The judgment

**P44 is real, it is large, and it changes a verdict on public data.**
- On synthetic burns the template reads:
  - a fade of 20 % as 13.6 %;
  - a broadening at constant area as a 14 % gain, which it calls "changing" every time;
  - an NX 15-like burn (FWHM +20 %, intensity −13 %) as −0.2 %, which it calls "stable" every time at
    high counts, and in 68 % of the burns at NX 15's counts (sections 1, 3, 4).
- On NX burn 15 it reads −1.5 % ± 1.5 % "stable", while both splits read a fade of 13–15 % "changing"
  and describe the frames twice as well (section 5).

**The split estimators fix it where their assumption holds, and reduce it where it does not.**
- On a Gaussian shoulder at high counts the split reads every quantity of every case to 0.13 pp, the
  shoulder's own change included, with intervals that are up to 25 % short (pull SD ≤ 1.25).
- On the other shoulder shapes it is 1.4–6 × less biased than the template (worst +5.7 pp, or +11.7 with
  a second narrow hump), and a broadening there leaks into its shoulder (section 2).
- `split_fixed` (B = 1) is as good, and steadier at low counts, while the shoulder is steady. It is badly
  wrong when the shoulder changes. So the two disagreeing is the signal to look at the shoulder.

**Their weak point is the reference's noise at real counts** (sections 4 and 6).
- When the peak's width changes, the noisy mean frame biases every fitted estimator: the split by −2 pp
  at NX 15's counts and −6 pp at NX 14's, with intervals too short.
- A smoothed mean frame removes this on synthetic burns. On the two NX burns it moves the reads the other
  way, so it is not offered until more real burns are read (hand-off 10).

**What NX burns 14 and 15 say.**
- Burn 14 is steady under every estimator that describes its frames.
- Burn 15 fades by 13 % ± 2.4 % (split; `split_fixed` 15 % ± 1.3 %) while the peak broadens by about 20 %.
  Its shoulder is steady (−2.8 % ± 2.8 %; B 0.96–1.15), and the free and fixed splits agree. If the
  synthetic noise transfers to real frames, the fade is nearer 11 %. Either way it is a fade, which the
  template misses.
- The drift per dose of burn 15 over 14 moves from 0.79 to 0.82: no change to F76's reading.

**Recommendation.**
1. **Report the split beside the template for GID burns,** both intensity changes with their verdicts, so
   that a disagreement shows P44. `split_fixed` is the check on the shoulder. Both are in `lss_core.burn`
   (`measure_gid(..., estimator='split')`) for scripts today.
2. **The reader's default stays the template, and the burn dialog is unchanged.** Changing either is the
   owner's choice, and rule 12 (paused) would ask for this study, its tests and a demonstrator first. The
   first two exist, and the walkthrough is the third.
3. **Real burns decide the rest** (hand-off `docs/handoff_out/10-gid-burn-shoulder.md`, DATA_NEEDS
   row 19). How often does P44 change a real verdict? Do real shoulders change? Is a Gaussian shoulder
   good enough? Does the reference's noise matter at real counts?

**How sure.**
- **High** that the template is biased whenever the width or the shoulder changes, and in which direction.
  Every synthetic case shows it, at every count, and NX 15 shows it on real data.
- **High** that the split reads a Gaussian shoulder's burns correctly at high counts.
- **Moderate** on the size of the split's read on real burns. It depends on the shoulder's shape (section 2)
  and on the reference's noise (sections 4 and 6), and two public burns cannot pin either down.

## 8. Real GID burns (non-cloud agent)

Hand-off 10's six questions (`docs/handoff_out/10-gid-burn-shoulder.md`, issue #155), answered on the
private GID burns of the owner's PC, 2026-11-27.

**The data.**
- The tool's finder (`find_gid_burns`: an `ascan ih` that does not move, Det_Th above 2°) found 236 GID
  burns in 12 SPEC files.
- Two are the public NX burns 14 and 15. The runner reproduces section 5's numbers for them exactly
  (template −1.5 % ± 1.5 % stable, split −13.3 % ± 2.4 % changing, split_fixed −15.2 % ± 1.3 % changing).
- Of the 234 private burns, 79 were not read: 73 have no Pilatus frames, 4 have too few frames with
  images, and 2 have no peak 5σ above the background. Each is in the private key with its error.
- 155 private burns in 11 files were read under all three estimators. Their per-burn summary is
  `docs/studies/xr_burns/gid_split.csv` (labels G01…; no file, scan, Qxy, frame or image).
- **Well measured: 118 of the 155.** These have:
  - a finite intensity change under all three estimators;
  - an error on one frame's intensity of at most 10 %;
  - a template intensity change within ±50 % over the burn. A larger one means the peak comes or goes:
    these runs hold a few burns of +200 % to −800 %;
  - template frames fitted to χ²/dof ≤ 5.

  The cut is `well_measured` in the tool. The numbers below are for these 118 unless marked.
- **One file holds 76 of the 118.** Each question was also run without it (42 burns in 10 files). Where its
  answer differs, it is given.
- The well-measured burns have a median of 21 frames over 321 s.
  - One frame's intensity error has a median of 1.6 % (interquartile range 0.6–3.8 %).
  - The mean frame's noise has a median of 0.46 % of its peak (0.27–0.86 %). That lies between the synthetic
    monitors 6e4 and 1e4 (section 4) and near NX 14 (0.51 %).

![R1](R1_template_vs_split.png)

**1. How often does P44 change a real verdict?** Figure R1 shows the split's intensity change against the
template's, one point per burn.
- **The intensity verdicts differ on 15 of the 118 burns (13 %).** On 5, the template says stable and the
  split changing; on 10, the other way round.
- **The changes differ by more than 2 × the larger σ on 32 burns,** with the split's σ widened by 25 % as the
  hand-off suggests. Counting either kind of disagreement, **39 of 118 (33 %)** disagree. Without the large
  file the share is the same: 14 of 42.
- The FWHM verdicts differ on 12, and the FWHM changes beyond 2σ on 15.
- **On real burns the disagreement doesn't come from P44's own mechanism.** P44's mechanism is a change of
  width that the template carries into the intensity. But real widths are steady:
  - the median FWHM change over a burn is 1.4 %;
  - only 5 of the 118 burns broaden or narrow by 10 % or more;
  - on none of those 5 do the verdicts differ.

  The disagreements come from the shoulder instead. Among the 39 burns where the estimators disagree, the
  split reads the shoulder as changing on 26 (67 %). Among the 79 where they agree, it does on 21 (27 %).
- Across burns, split − template has a median of −0.01 pp, with a scatter (MAD) of 1.5 pp. The split
  shows no overall bias: it differs burn by burn.
- NX 15 (a fade read as stable while the peak broadens by 18 %) is the clearest case of P44 among these
  burns. No private burn shows it as strongly.

**2. Do real shoulders change under the beam?** Yes, in a sizeable minority of burns.
- The split found a shoulder on 94 of the 118 burns (30 of the 155 had none, and the split is then the
  template).
- On 47 of those 94, the split calls the shoulder's own change "changing". The median change is +2.7 %, and
  the median size of the change, sign ignored, is 5.1 %.
- B per frame has a median mean of 0.99 and a median range (max − min) of 0.18 over a burn.
- Split and split_fixed disagree on the intensity by more than their combined σ on 34 burns.
- **All three signs together, the hand-off's test of a believable shoulder change, hold on 22 of 94 burns
  (23 %):** the shoulder called changing, B moving the same way, and the two splits disagreeing. Without
  the large file it is 13 of 39.
- The synthetic study warns that a broadening peak leaks into B when the shoulder is not a Gaussian
  (section 2). That cannot explain these: their widths are steady.
- **So `split_fixed` (B = 1) is not safe on real burns:** about one shoulder in four changes.

**3. Is a Gaussian a good enough shoulder?** At these counts the frames can't tell.
- On the 94 burns with a shoulder, the frames' χ²/dof has a median of 1.11 under the template and 1.12
  under the split. Both describe the frames to counting noise.
- The split's χ²/dof is the lower one on 63 burns, but the median ratio is 0.99. It is more than 10 %
  lower on 4 burns and more than 10 % higher on 10.
- Only 7 burns have a template χ²/dof above 2, and on 2 of them the split is lower. NX 15, at higher
  counts, shows the split's gain: 2.17 against 4.24.
- **The split is never much worse, so a Gaussian shoulder is not the weak point at real counts. It is not
  shown to be right either:** a shoulder of another shape would fit these frames as well.
- Shape against the synthetic shoulders:
  - shoulder ÷ peak area: median 2.6 (interquartile range 1.3–8.2);
  - shoulder ÷ peak FWHM: median 5.3 (4.0–8.7); NX 14 and 15 have 8.5 and 6.9.

![R2](R2_reference_shift.png)

**4. Does the reference's noise matter at real counts?** For burns whose width is steady, no.
- Figure R2 shows the intensity change re-read against the smoothed mean frame, minus the reader's, against
  the mean frame's noise. The synthetic expectation is drawn over it.
- **Burns with a steady FWHM** (a change below 5 %):
  - below 1 % noise, the shift has a median within ±0.06 pp under both estimators, with a scatter (MAD) of
    at most 0.6 pp;
  - above 1 % noise (13 burns under the template, 12 under the split), the median is +0.8 to +0.9 pp, with a
    scatter of about 5 pp;
  - the synthetic steady fade expects 0 ± 0.5 at 0.35 % noise and 0 ± 1.9 at 0.85 %.
- **The shift doesn't grow with the noise:** the rank correlation is 0.12 (template) and 0.14 (split).
- **Burns that broaden by 5 % or more, the case the synthetic study flags,** are only 12 of the 118, 3 to 5
  per noise bin. Their medians under the split are +0.2 pp at 0.2–0.5 % noise and +0.7 pp at 0.5–1 %. The
  synthetic NX 15-like burns predict +1.5 ± 1.0 and +5.0 ± 2.7 pp, but they broaden by 20 %, and these
  burns mostly broaden by 5–10 %.
- NX 14 and 15 remain the two burns well below the synthetic rows.
- **Of the hand-off's three readings, the first fits the steady burns:** the shifts scatter around zero
  whatever the noise. Too few real burns broaden to decide between the other two. So the smoothed reference
  doesn't become a candidate option from these data.

**5. Does the split change F76's dose-or-time answer?**
- Series here means burns of one file at one Det_Th, each less than 3 h after the previous one, with a flux
  span of ×1.5 or more. There are **14 such series** of 2–6 burns, spanning ×2.0–×96 in flux
  (`docs/studies/xr_burns/gid_split_series.csv`).
- They were read with `lss_core.reciprocity.dose_or_time` on the intensity, as the reader does.
- **With strip scatter ρ = 0 (the reader's default), the split changes the verdict of 5 of the 14 series;
  with ρ = 0.5, of 3.**
  - Template at ρ = 0: no change 4, opposite signs 3, neither 3, dose 2, time 1, cannot tell 1.
  - Split at ρ = 0: no change 6, opposite signs 4, dose 2, cannot tell 2.
- The changes are mostly between undecided classes ("neither", "no change", "cannot tell").
  - One series moves from "neither" to "dose": β 0.45 → 0.69.
  - One moves from "dose" to "cannot tell".
  - The one "time" series becomes "no change".
- Where both call it "dose", β moves from 1.18 to 1.04.
- On NX, the drift-per-dose ratio moves from 0.79 to 0.82 (section 5).
- **So the split changes F76's answer in a minority of series.** Few series are decided either way, and these
  are 2–6 burns each.

**6. Is there a burn with an independent before-and-after measurement?**
- **47 burns (28 of them well measured) have a GID series of the same Det_Th in the same file that ended
  within 2 h before the burn, and another that started within 2 h after it.** These are the candidates
  (generator `sample_data/private/burn_shoulder/q5_q6.py`).
- Not yet done: comparing that peak's area change across the burn with each estimator's change. It needs
  each GID series patched, and the same peak's area measured in both. It is follow-up issue #173.

**The judgment on real data.**
- **P44's verdict change is real but less common on private burns than on NX 15.** The intensity verdicts
  differ on 1 burn in 8, and the two estimators disagree in some way on 1 in 3.
- **The driver on these burns is the shoulder, not the width.** Real widths are steady, and real shoulders
  change in about a quarter of the burns. So the split with B free is the estimator to report beside the
  template, and `split_fixed` is only a check.
- **At real counts the frames can't choose a shoulder shape,** and **the reference's noise doesn't bias
  steady burns.** Neither is a reason to hold the split back.
- **The split changes F76's verdict in 3–5 of 14 series,** mostly among undecided ones.
- **How sure:**
  - **moderate** on the counts. 118 burns, but 76 from one file; the share of disagreements is the same
    without it.
  - **low** on question 4 for broadening burns: there are only 12.
  - **open** on question 6: the measurement is the follow-up.
- **Recommendation unchanged** (section 7): report the split beside the template, and leave the default
  to the owner (rule 12 paused; issue #143).

The private figures and generators are under `sample_data/private/burn_shoulder/`:
- `run_real.py` (the runner over every file);
- `analyse_final.py` (questions 1–4, the private `numbers.json`);
- `q5_q6.py`;
- frame-by-frame curves of single private burns, if wanted, are made there and never published (owner,
  2026-11-25).

## How to regenerate

    python tests/tools/burn_shoulder_study.py --out docs/studies/burn_shoulder               # S1-S5, about 90 min (4 CPUs)
    python tests/tools/burn_shoulder_study.py --out docs/studies/burn_shoulder --only R      # S6, about 10 min
    python tests/tools/burn_shoulder_study.py --out DIR --replicates 30                      # a quick look, about 9 min
    python tests/tools/burn_shoulder_study.py --out DIR --only S5                            # NX only, a minute
    python tests/tools/burn_shoulder_study.py --out docs/studies/burn_shoulder --only G      # R1, R2 from xr_burns/gid_split.csv, seconds

Options: `--parts A` or `B`, `--cases`, `--shapes`, `--core` (the split's core half-width in FWHM, 1.5:
the shoulder is fitted beyond it), `--workers`. The Tools menu has the variations (`docs/TOOLS.md`).
With 30 replicates the biases hold to about 0.05 pp at monitor 1e7; the coverages are good to about ±5 %.
Tests: `tests/test_burn_split.py` (the estimators), `tests/test_burn_shoulder_study.py` (the tool, and
the NX numbers of section 5, slow).
