# Monitor noise and error propagation in ROI sums

Date: 2026-11-15. Scope: assessment only; no application code was changed.
Companion script: `tests/tools/monitor_noise_mc.py` (run from the repository
root, about 20 s, fixed seed; all numbers in sections 3 and 4 come from it).

Labels: **derived** (algebra here), **simulated** (script Parts 1–2),
**measured** (script Part 3, NX school SPEC file), **read** (code or SPEC
file, nothing run), **from memory** (literature not checked this session).

## 1. Answers in brief

1. **Is adding the per-pixel monitor variance in quadrature over an ROI
   right? No.** (derived, simulated) One monitor reading M is shared by every
   pixel of a frame, so its error is fully correlated across pixels. For
   an ROI sum S = Σ I_i the correct first-order variance is

       var(S/M) = S/M² + (S/M)² · u_M²          (Poisson monitor: S/M² + S²/M³)

   The reader computes S/M² + Σ(I_i²)/M³. Its monitor term is too small by
   the factor N_eff = S²/Σ I_i², the effective number of pixels the counts
   are spread over (between 1 and the number of pixels in the ROI).
2. **Background subtraction.** (derived, simulated) The monitor term
   multiplies the net signal: var(net/M) = [S + (L+R)/4]/M² + (net/M)²·u_M².
   Treating S, L, R as if they had independent monitors overstates it.
3. **How much it matters depends entirely on how noisy the monitor really
   is.** (simulated) If Monc were Poisson, the reader's error bar at low Qz
   (S = 7.9e5, M = 2.2e5) would be too small by a factor 2.05. If the
   monitor is ten times quieter in variance (the owner's lower bound), the
   reader's error is 11 % too small. With a noiseless monitor it is 3.5 %
   too large. At high Qz (tens of counts, M ~ 2e6) all formulas agree to
   better than 1 %, because the monitor term is negligible.
4. **The real data say the monitors are quieter than Poisson on their
   counts.** (measured) Monp scatters at 0.2–0.5 of √counts in most scans;
   Monc reaches 0.59 of √counts in scan 15. Poisson with N = Monc is
   therefore not the right model, as the owner said. The data do not pin
   down the true u_M for Monc; they give an upper bound of roughly 3e-4 to
   8e-4 (relative) for 7–10 s frames.
5. **Top recommendation** (section 6, option C): keep the count term as it
   is, take the monitor term out of the per-pixel error map, and apply it
   once per frame to the net signal with a configurable monitor model
   u_M² = f² + 1/(g·M). Keep today's formula available as "legacy" so the
   legacy export fixtures still reproduce.

The two errors in the current code (correlation ignored; Poisson assumed for
a quieter monitor) push in opposite directions and largely cancel in the
realistic range. That is luck, and it depends on ROI shape and count level.

## 2. Derivations

Notation: I_i independent Poisson pixel (or channel) counts, S = Σ I_i with
mean λ; M one monitor reading with mean μ and relative standard uncertainty
u_M, independent of the I_i given the beam intensity; r_i = I_i/M.

### 2.1 ROI sum with one shared monitor (question 1)

First order (delta method, GUM eq. 13 with correlated inputs, or Bevington
eq. 3.13): for i ≠ j the only common input is M, so

    var(r_i)     = I_i/M² + r_i² u_M²
    cov(r_i,r_j) = r_i r_j u_M²

    var(Σ r_i) = Σ var(r_i) + Σ_{i≠j} cov(r_i,r_j)
               = S/M² + u_M² (Σ r_i)²
               = S/M² + (S/M)² u_M²                                  (1)

Equivalently, apply the ratio formula once to S and M:
(σ_Y/Y)² = 1/S + u_M². With u_M² = 1/M this is S/M² + S²/M³.

What the reader does (`peakLocate`, `sumFiles`, then `sumROI`; same
structure in `updateMcaPlotData` + `mcaSumAll`) is to drop the covariance
sum:

    var_code = S/M² + Σ I_i² / M³ = S/M² + (S²/M³) / N_eff,   N_eff = S²/Σ I_i²   (2)

The count term is right. The monitor term is right for one pixel and too
small by N_eff for a sum. The per-pixel error map itself is a correct
marginal error for each pixel; the mistake is using it as if pixels were
independent.

Where first order breaks down:

- **Ratio bias.** E[1/M] = (1/μ)(1 + u_M² + …), so E[S/M] is high by the
  fraction u_M² (1/M for Poisson: 3 % at M = 30, 5e-6 at M = 2e5), and the
  variance gets corrections of relative size ~3u_M². Irrelevant above ~10⁴
  monitor counts, important below ~100; 1/M has no finite moments if M can
  be 0. (Simulated: +3.6 % bias at M = 30, section 3.2.)
- **Estimated variance at low counts.** (1) is evaluated with the observed
  S: σ = 0 at S = 0, and σ is correlated with the value for a few counts,
  which biases 1/σ²-weighted fits low. This is a separate issue, the same in
  the current code and in (1).
- **Beam fluctuations are not noise here.** I and M follow the beam
  together; only the part of M that does not follow the beam belongs in
  u_M. (Simulated: 2 % beam jitter leaves the table unchanged.)

### 2.2 Background-subtracted signal in one frame (question 2)

net = S − (L+R)/2 with S, L, R disjoint ROIs of one frame (equal areas, as
`sumROI` uses), all divided by the same M:

    var(net/M) = [S + (L+R)/4]/M² + (net/M)² u_M²                    (3)

The monitor is a pure scale error on the net signal. If each ROI were given
its own monitor term (formula (1) applied to S, L, R separately, then
combined in quadrature as `pilRefPatchData` does), the monitor part would be
[S² + (L²+R²)/4] u_M²/M². The difference to (3) is

    [S² + (L²+R²)/4] − [S − (L+R)/2]² = S(L+R) − LR/2  > 0

For L = R = B: correct (S−B)², independent S² + B²/2. With B = S/4 the
independent treatment overstates the monitor variance by a factor 1.85; for
a weak signal on a large background (S ≈ B) the correct monitor term goes
to zero while the independent one stays at 1.5 S² u_M²/M². The reader's
actual formula is [S + (L+R)/4]/M² + [ΣS_i² + (ΣL_i² + ΣR_i²)/4]/M³: right
count term, monitor term too small by about N_eff and without the
cancellation.

### 2.3 Several frames at one Qz (question 3)

Frames k = 1…n have separate monitor readings, so R_k = net_k/M_k are
independent between frames.

**Mean of ratios** (what `sumFiles` does per pixel; summing pixels before or
after averaging is the same thing):

    R̄ = (1/n) Σ R_k,   var(R̄) = (1/n²) Σ var(R_k)                   (4)

The reader's `sqrt(Σ var_k)/n` has the right structure across frames; only
the within-frame var_k carries the defect of 2.1.

**Ratio of sums**: R̂ = Σ S_k / Σ M_k, with

    var(R̂) = ΣS/(ΣM)² + R̂² u_tot²,   u_tot² = Σ M_k² u_k² / (ΣM)²    (5)

(u_tot² = 1/ΣM for Poisson monitors; f²/n for n equal frames with a
fractional floor f). With absorbers, use the effective monitor
M_k/absfac^absnum_k in the sums.

Comparison:

- Equal M_k: the two estimators are identical.
- Unequal M_k: the mean of ratios weights every frame equally although
  var(R_k) ∝ 1/M_k. The ratio of sums weights by M_k, the minimum-variance
  (maximum-likelihood) combination for Poisson counts with a common true
  ratio. Simulated with a 16× spread in M: scatter 1.55 times smaller.
- Bias: mean of ratios is high by the average of u_k² (1/M_k for Poisson);
  ratio of sums by u_tot² ≈ 1/ΣM, n times smaller. Neither matters for
  M > 10⁴.
- Avoid, at low counts, an inverse-variance weighted mean with σ_k taken
  from the observed counts: frames that fluctuated low get more weight and
  the result is biased low. Ratio of sums does not have this problem.

For the reader as used (repeat frames with equal counting time) the choice
changes nothing measurable; it matters only if frames with very different M
are merged into one point.

## 3. Monte Carlo (simulated)

`python3 tests/tools/monitor_noise_mc.py`; seed 20261115; 40 000 trials per
row in Part 1 (an empirical σ is good to ±0.35 %), 200 000 in Part 2.
Columns are predicted σ divided by the empirical standard deviation: 1.00 is
correct, below 1 understates the error.

- **code**: the reader today, formula (2) and its background version.
- **derived**: formulas (1) and (3) with the u_M that was simulated.
- **corr-P**: (1) and (3) but with u_M² = 1/M assumed whatever the truth.
- **indep**: monitor term applied to S, L, R separately (section 2.2).

Regimes: A = low Qz, S = 7.9e5 in an 11×11 ROI, Gaussian spot (N_eff ≈ 42),
L = R = 4e3, M = 2.2e5. A2 = A with L = R = 2e5. B = high Qz, S = 50,
L = R = 20, M = 2e6. C = MCA window, 81 channels, S = 2e4, L = R = 4e3,
M = 2.2e5. C2 = same window, S = 1e6, L = R = 5e4.

### 3.1 One frame

| Regime | Monitor model | S/M: code | derived | corr-P | net/M: code | derived | corr-P | indep |
|---|---|---|---|---|---|---|---|---|
| A  | Poisson, u² = 1/M   | 0.487 | 1.002 | 1.002 | 0.490 | 1.002 | 1.002 | 1.006 |
| A  | g = 10, u² = 1/(10M) | 0.893 | 1.000 | 1.837 | 0.895 | 1.000 | 1.831 | 1.001 |
| A  | noiseless           | 1.035 | 0.994 | 2.129 | 1.036 | 0.994 | 2.119 | 0.994 |
| A2 | Poisson             | 0.486 | 0.999 | 0.999 | 0.622 | 0.998 | 0.998 | 1.240 |
| A2 | g = 10              | 0.893 | 0.999 | 1.835 | 0.954 | 0.998 | 1.533 | 1.060 |
| B  | Poisson             | 1.001 | 1.001 | 1.001 | 1.003 | 1.003 | 1.003 | 1.003 |
| B  | noiseless           | 0.996 | 0.996 | 0.996 | 0.998 | 0.998 | 0.998 | 0.998 |
| C  | Poisson             | 0.963 | 1.004 | 1.004 | 0.982 | 1.006 | 1.006 | 1.021 |
| C  | g = 10              | 0.994 | 0.997 | 1.036 | 0.997 | 0.998 | 1.022 | 1.000 |
| C2 | Poisson             | 0.459 | 1.003 | 1.003 | 0.482 | 1.002 | 1.002 | 1.045 |
| C2 | g = 10              | 0.894 | 1.001 | 1.954 | 0.910 | 1.001 | 1.892 | 1.016 |
| C2 | noiseless           | 1.073 | 0.995 | 2.344 | 1.073 | 0.997 | 2.229 | 0.997 |
| A + 2 % tracked beam jitter | g = 10 | 0.894 | 1.000 | 1.838 | 0.895 | 1.000 | 1.831 | 1.001 |

Reading the table:

- The derived formulas match the empirical scatter within Monte Carlo
  precision in every row, including the rows of the script output not shown.
- The reader's formula is right only where the monitor term does not matter
  (B, C) or by accident. With a Poisson monitor and S > M it is low by a
  factor of about 2 (0.46–0.49). A flat profile over the same ROI (N_eff =
  121) gives 0.476, 0.870 and 1.014 for the three monitor models.
- **Fixing the correlation while keeping Poisson for the monitor (corr-P)
  would make things worse** if the monitor is in fact quieter: errors too
  large by 1.8–2.3 at low Qz. A fix has to address the monitor model too.
- The cancellation in the background subtraction shows in A2: "indep" is
  24 % too large with a Poisson monitor.
- Regime A has 1/√S = 1.1e-3 from counting and 1/√M = 2.1e-3 from a Poisson
  monitor: the whole question is about error bars of 0.1–0.2 % on the
  brightest points.

### 3.2 Combining frames

Five frames per point; bias is relative to the true ratio; "σ/emp" is the
propagated σ (formula (4) or (5), ROI level) over the empirical one.

| Case | Monitor | bias MoR | std MoR | σ/emp | bias RoS | std RoS | σ/emp |
|---|---|---|---|---|---|---|---|
| equal M = 2e6, 10 counts per frame      | Poisson | +0.05 % | 7.10e-7 | 0.997 | +0.05 % | 7.10e-7 | 0.997 |
| M = 0.25, 0.5, 1, 2, 4 e6, rate 5e-6    | Poisson | +0.02 % | 1.25e-6 | 0.998 | +0.03 % | 8.03e-7 | 1.000 |
| M = 0.25…4 e5, rate 3.5                 | Poisson | +0.00 % | 7.00e-3 | 0.998 | −0.00 % | 4.51e-3 | 1.000 |
| tiny M = 30 each, rate 2                | Poisson | +3.57 % | 0.220   | 1.003 | +0.67 % | 0.204   | 0.998 |
| tiny M = 10, 20, 40, 80, 160, rate 2    | Poisson | +4.66 % | 0.286   | 1.054 | +0.36 % | 0.141   | 0.998 |

Equal monitors: no difference (the ±0.05 % is Monte Carlo noise). Unequal:
ratio of sums has 1.55 times less scatter. Tiny monitors: mean of ratios is
biased by about 1/M, ratio of sums by about 1/ΣM.

## 4. The real data (measured)

File `sample_data/NX_school/2026sep/20260923`, read only, script Part 3.
Relative scatter is estimated from successive differences,
sd = sqrt(mean(Δ²)/2)/mean, which ignores slow drift. "/P" is sd divided by
the Poisson-on-counts prediction 1/√M. With 21 points each "/P" value is
good to about ±0.19 (1σ).

Read from the file: `Monb` and `Mond` are 0 throughout, so only `Monc` and
`Monp` are usable. Values are stored to six significant digits, so 10 s
monitor readings are rounded to 10 counts (negligible).

| Scan | What | T (s) | Monc | sd | /P | Monp | sd | /P | sd of Monc/Monp | /P |
|---|---|---|---|---|---|---|---|---|---|---|
| 14 | 21 repeats, absorber 12 | 10 | 3.144e6 | 7.7e-4 | 1.36 | 2.120e6 | 3.6e-4 | 0.52 | 7.7e-4 | 0.87 |
| 15 | 21 repeats, absorber 8  | 10 | 3.131e6 | 3.3e-4 | 0.59 | 2.154e6 | 1.6e-3 | 2.33 | 1.6e-3 | 1.86 |
| 11 | dth scan, 41 points     | 7  | 2.209e6 | 5.7e-4 | 0.85 | 1.484e6 | 4.1e-4 | 0.50 | 6.2e-4 | 0.59 |
| 5, 10, 13 | a2scan, 21 points each | 1 | 8.7e4 | 4.1–5.5e-3 | 1.2–1.6 | 2.1e5 | 4.2–4.6e-4 | 0.20–0.21 | 4.1–5.4e-3 | 1.0–1.3 |
| 6–9 | reflectivity scans     | 2–5 | falls steadily with Qz | 0.6–1.3e-2 | 2.7–9 | flat | 4.2–7.1e-4 | 0.28–0.74 | — | — |

Findings:

1. **Monp is clearly sub-Poisson relative to its counts**: 0.20–0.52 of
   √counts in nine of the twelve beam-on scans (exceptions: scan 4 has one
   spike, scan 9 reads 0.74, scan 15 has a real excursion of 2 % over the
   first few points). In variance that is an effective gain g of at least 4
   to 25. Its relative scatter is 4e-4 to 7e-4 at 1, 2, 5, 7 and 10 s alike,
   not falling as 1/√T: a constant fractional floor fits better than 1/(g·M).
2. **Monc in scan 15 scatters at 0.59 ± 0.11 of √counts** (3.3e-4), which
   is significantly below Poisson and sets g ≥ 2.9 for Monc from this scan
   alone. In scan 14 it is 1.36 (7.7e-4), with visible drift and one dip of
   0.3 %. In the 1 s scans it is 0.4–0.6 %, 1.2–1.8 times Poisson.
3. **Monc and Monp do not see the same beam.** In the reflectivity scans
   Monc falls smoothly with Qz (scan 9: 1.77e6 to 1.34e6) while Monp stays
   flat, and their ratio differs between scan types (0.40, 1.33, 1.48). So
   Monc sits after something that changes with the incident geometry and
   Monp before it. The ratio Monc/Monp therefore contains real intensity
   changes that Monc is correctly tracking, and its scatter is only an upper
   bound on monitor noise. Successive differences of the two are almost
   uncorrelated (r ≈ +0.1 in scans 14 and 15).
4. **The detector cannot see the monitor noise.** The SPEC `Pilatus` column
   in scan 14 has 721 counts per point; Pilatus/Monc scatters at 3.68e-2
   against 3.73e-2 expected from the Pilatus counts alone. In scan 15 (3380
   counts) it is 2.1e-2 against 1.72e-2; the excess goes with a steady 10 %
   fall of the signal during this burn test, not with the monitor.
5. **Dark offset.** Scans 1–3 (Pilatus column 0) look like beam-off
   readings: Monc ≈ 100 counts/s, Monp ≈ 42 counts/s, scatter 10 and 3
   counts in 4 s. If so, electronic noise without beam is negligible and
   there is an unsubtracted offset of 0.03 % (Monc at 3.1e5 /s) to 0.12 %
   (at 8.7e4 /s): a small scale bias, not noise.

How conclusive: it is solid that these V-to-F monitors are not Poisson in
their counts, and that for 7–10 s frames the frame-to-frame scatter of Monc
is below 1e-3. It is **not** established how much of Monc's scatter is noise
and how much is real beam variation at the sample; one file with one usable
downstream monitor cannot separate them. Practical upper bound for
u_M(Monc): 3e-4 to 8e-4 at 7–10 s; 4e-3 to 6e-3 at 1 s (narrow slits,
absorber 52), where it may be mostly real.

## 5. A model for the monitor uncertainty (question 4)

Contributions, with what is known about each:

| Source | Size | Status |
|---|---|---|
| Photon statistics in the chamber | u² = (1/N_abs)(1 + small), N_abs = absorbed photons. Each 10 keV photon makes about 10 000/34.8 ≈ 290 ion pairs in N₂, so the ion-pair statistics add almost nothing; N_abs is what counts. | derived; W value from memory (ICRU 31, confirmed by a web search summary only) |
| Counts per absorbed photon | charge per count = Gain / k_VF. With Gain = 5 µA/V (SPEC header) and an **assumed** k_VF of 1e5–1e6 Hz/V, one count is 5e-11–5e-12 C, i.e. roughly 1e5–1e6 absorbed photons. Then g ~ 1e5–1e6 and the photon term is ~1e-6 relative: negligible. | arithmetic on an assumed converter constant; needs the owner's confirmation |
| V-to-F digitisation | ±1 count, variance ≤ 1/6 count²; relative 1/M | negligible above 10³ counts |
| Amplifier/electronic noise, dark offset | additive: σ_d²·T/M²; about 5 counts/√s in the beam-off scans | measured (if scans 1–3 are beam-off); negligible |
| Gain and offset drift, microphonics, gate timing | multiplicative, roughly constant fraction f | not separable here; bounded by the measured scatter |
| Real beam fluctuations | not noise for normalisation, provided the monitor and the detector integrate over the same time window and the monitor sees the beam that reaches the sample | — |

Defensible model: u_M² = f² + 1/(g·M), with the f² term expected to
dominate. The owner's "more than 10×" corresponds to g ≥ 10; the gain
arithmetic suggests g is many orders larger, in which case the monitor error
is a fractional floor and nothing else. A single constant f between 3e-4 and
1e-3 covers what the file shows for 7–10 s frames.

How to measure u_M:

1. **Two monitors on the same beam** with nothing variable between them:
   var(ratio)/ratio² = u_a² + u_b²; with three the individual values
   separate. Needs Monb or Mond connected; here they read 0.
2. **Repeated frames at fixed conditions with a bright, stable signal**:
   var(S/M)/mean² = 1/S̄ + u_M² + (real, untracked changes). To see
   u_M = 3e-4 needs S well above 10⁷ per frame; the burn-test scans have
   10³–10⁴ in the SPEC ROI. Conversely, a u_M that cannot be seen with
   S up to 10⁶ changes σ there by less than 5 %.
3. **Scatter against counting time** (1, 3, 10, 30 s series, successive
   differences): falling as 1/T is counting-like, constant is a fractional
   floor, rising is drift.
4. **Beam-off series** for the dark offset and its noise.

## 6. What the program could do (question 7)

Three kinds of error should be kept apart:

- **Per-point, uncorrelated** — what a fit should weight by. For
  reflectivity each Qz point is its own frame with its own M, so both the
  count term and the (correctly computed) monitor term of that frame belong
  here. Overlap scaling and plateau normalisation do not absorb it.
- **Per-frame, correlated** — the monitor term seen from inside one frame:
  common to all pixels, channels and ROIs, so applied once to whatever
  number is extracted from the frame. Where many fitted points come from one
  frame (GID/GISAXS maps and cuts, an MCA spectrum) it is a common scale
  factor and should not be in the per-pixel or per-channel error at all.
- **Per-scan scale** — absorber factor (absfac^absnum: relative error
  absnum·σ_absfac/absfac), amplifier gain setting, dark offset, slit
  changes. Largely absorbed by the fitted overlap factors and the plateau
  normalisation; they do not belong in point errors. The uncertainty of the
  fitted overlap factors themselves is a correlated error of the scaled scan
  that is currently not reported.

Options:

| | Option | For | Against |
|---|---|---|---|
| A | Leave as is; document | No change to outputs or fixtures. Within about −13 % / +7 % of the truth in the bright regimes if g ≥ 10, exact at high Qz (simulated). | Formally wrong; error depends on ROI shape (N_eff); wrong by 2× if a monitor is ever truly a counter. |
| B | Fix the correlation, keep u_M² = 1/M | Internally consistent Poisson model. | Overstates low-Qz errors by about 1.8–2.3 for the real monitor (simulated). Worse than A in practice. Not recommended. |
| C | Count-only per-pixel errors; monitor term applied once per frame to the net signal, formula (3), with u_M² = f² + 1/(g·M) set by the user; "legacy" mode keeps today's formula | Correct structure for ROI sums, background subtraction, MCA windows and maps; one place to change when the beamline provides a photons-in estimate (F21). | Touches every reduction path; needs the owner to choose f and g; changes exported σ at low Qz by up to ~15 % unless legacy mode is selected. |
| D | Drop the monitor term (u_M = 0) | Simplest; right if g is as large as the gain arithmetic in section 5 suggests and there is no floor. | Claims a perfect monitor: 14 % low at regime A if g = 10, 9 % low with a floor f = 5e-4 (derived). A special case of C. |
| E | C plus ratio-of-sums when merging frames | Optimal weights for unequal frames, smaller bias. | No measurable gain for equal-time repeats; changes central values slightly, so needs its own fixtures. Low priority. |

Recommendation: **C**, as an opt-in mode with "legacy" as the default until
the owner has chosen the monitor parameters, because rule 3 of `AGENTS.md`
freezes the legacy export fixtures. D (f = 0, g → ∞) is an acceptable
setting inside C only if the owner is confident the monitor is that quiet.
This is not urgent: today's σ is within about 15 % at worst (for g ≥ 10), on
points whose statistical error is ~0.1 % and almost certainly below their
systematic error. For those points a user-chosen fractional floor is more
honest than either Poisson variant. A regression test for C would be one
regime of section 3, marked `xfail(strict=True)` until the change is made.

## 7. Open questions for the owner

1. What is Monc physically (chamber gas and length, position relative to
   the steering crystal, slits and absorbers), what is the V-to-F constant
   in Hz per volt (g then follows from the `#M` gain), and where is Monp?
   Are Monb and Mond ever connected?
2. Are scans 1–3 of the NX school file beam-off? If so, should the dark
   offset (about 100 counts/s on Monc) be subtracted before normalising?
3. Do the monitor scaler gate and the Pilatus exposure cover exactly the
   same time window? A mismatch turns real beam fluctuation into noise.
4. Is a user-set fractional floor on the monitor (for example 5e-4)
   acceptable in exported σ, or does xmodfit expect pure counting errors and
   add its own floor?
5. Can a dedicated measurement be taken (section 5, items 1–3)? Thirty
   repeated frames at three counting times with a bright stable signal would
   settle f. The private `bu` data set was not examined for this report.

## 8. References

I could not reach Crossref or doi.org from this session, so **every citation
below is from memory and unverified**; check before quoting.

- P. R. Bevington and D. K. Robinson, *Data Reduction and Error Analysis for
  the Physical Sciences*, 3rd ed., McGraw-Hill, 2003, ISBN 0-07-247227-8.
  Chapter 3: error propagation with the covariance term (eq. 3.13).
- JCGM 100:2008, *Evaluation of measurement data — Guide to the expression
  of uncertainty in measurement* (GUM), BIPM. Section 5.2, correlated input
  quantities.
  https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf
- G. F. Knoll, *Radiation Detection and Measurement*, 4th ed., Wiley, 2010,
  ISBN 978-0-470-13148-0. Chapter 3 (counting statistics), chapter 5
  (ionisation chambers, W values).
- ICRU Report 31, *Average Energy Required to Produce an Ion Pair*, 1979.
  Source of W ≈ 34.8 eV for N₂.
- R. C. Ogliore, G. R. Huss and K. Nagashima, "Ratio estimation in SIMS
  analysis", *Nucl. Instrum. Methods Phys. Res. B* **269** (2011) 1910–1918,
  doi:10.1016/j.nimb.2011.04.120. Mean of ratios against ratio of sums and
  their bias at low counts.

I know of no paper giving the noise of an ion chamber, current amplifier and
V-to-F chain in a form that could replace a measurement on this beamline.
