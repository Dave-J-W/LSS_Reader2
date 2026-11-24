# Reflectivity burns on real data: trends, and beam damage or a changing sample (DATA_NEEDS row 11, F76, F77)

The owner's non-cloud agent, 2026-11-24. **Measured on real burn scans** from the owner's private beamline
data: every reflectivity burn test that spec master's inventory finds (`ascan ih` at one position, at least
10 points and 100 s, H = K = 0, qz ≥ 0.1 Å⁻¹). Each burn was run through the reader's own
`Experiment.burn` (time axis and dose axis, its defaults). No raw data, image or scan identifier is in
this folder. Runs are labelled `R01`… by a hash, series `Rnn-Sk` in time order within a run, and burns by
their order in the series. Times are elapsed hours from the series' first burn, to the minute. qz is
left out of the tables: the burns sit at qz 0.35–0.65 Å⁻¹, and one of those values belongs to one group's
macro.

**Not regenerable here.** The private generator lives under `sample_data/private/xr/` on the owner's
computer. The numbers behind the figures are the CSVs beside them:
- `burns.csv`: one row per burn;
- `series_dose_or_time.csv`: one row per series × error model;
- `numbers.json`: the counts quoted below.

## What was read

| | |
|---|---|
| Burns in the inventory | 89 (10 keV: 79; 30 keV: 10) |
| Read by the reader | **78**, from 14 runs, all at 10 keV |
| Not read | 10 at 30 keV (the reader's burn finds no frames: a Pilatus 1M run, F38); 1 at 10 keV (a NaN in the trend's change time: the reader's error, listed below) |
| Series with several absorbers (each burn on a fresh strip, `umvr sx`) | **19** (2–9 burns, flux span ×2–×99) |
| Frames per burn | 11–51 (median 41) of 10 s; median 422 s |
| Flux on the sample | 4 × 10⁸ to 2 × 10¹¹ photons/s (median 1.1 × 10¹⁰): the reader's `lss_core.dose` (Monc, calibrated foils at 10 keV, flux route D ±3.6 %) |

The intensity is the reader's: the background-subtracted ROI per Monc (Ref Patch arithmetic, slit 21 × 11,
counting errors).

## 1. The reader's trend verdicts on real burns

`trends.compare` (AICc over constant, linear, exponential, double exponential), frame 1 left out (spec
master flags it low in 3 of 78 burns; leaving it out changes 1 verdict):

| | burns |
|---|---|
| stable (the reader's `stable` flag) | **28** |
| best model by AICc | constant 24, linear 15, exponential 16, double exponential 23 (`best_drop1`) |
| a jump inside the burn (straight-line χ²/dof > 20; left out of section 3) | 3 |

**Stability follows the flux, pooled over all burns:**

| flux (photons/s) | burns | stable | median time to a 5 % change at 95 % confidence (s) |
|---|---|---|---|
| < 3 × 10⁹ | 18 | 10 | 331 |
| 3 × 10⁹ – 10¹⁰ | 20 | 5 | 63 |
| 10¹⁰ – 3 × 10¹⁰ | 21 | 6 | 34 |
| > 3 × 10¹⁰ | 19 | 7 | 51 |

The last bin is not lower than the third. That is not explained here. Its 19 burns come from few series,
and they include falls and rises.

## 2. The old rule against the reader (COMPARISONS C54)

spec master's rule (`xr_burn.py`) reads the **ROI total** per Monc: "falls" past 2 % or 3 × the starting
scatter, "rises" above +3 %. The reader reads the **background-subtracted** specular intensity with
counting errors and AICc.

| old rule / reader (frame 1 out) | burns |
|---|---|
| stable / stable | 23 |
| falls / changes | 21 |
| rises / changes | 17 |
| **stable / changes** | **11** |
| rises / stable | 4 |
| falls / stable | 1 |
| unclear / changes | 1 |

**Why they differ: the ROI total dilutes the change.** The specular part is a fraction of the ROI total:
median 0.37 (quartiles 0.25–0.81, range 0.016–0.93; `specular_fraction`). Over the 41 burns that change
by ≥ 3σ, the ROI total's drift is a median **0.61** of the specular drift, and those burns' median
fraction is **0.60**. A constant background flattens every relative change by the specular fraction. At a
fraction of 0.1 a 20 % fall reads as 2 %, the old rule's threshold. So most of the 11 "stable / changes"
are changes the old rule could not see. The 5 the other way are short or noisy burns where the reader's
counting errors do not reach significance.

## 3. Beam damage or a changing sample (F76)

**The test (this project's idea, F76):** damage by the beam follows the dose; a sample changing by itself
follows the clock. Across the burns of one series (one sample, fresh strips, several absorbers), the drift
rate of I/I(0) against time should then scale as rate_t ∝ flux^β, with **β = 1 for the dose** and
**β = 0 for time**. β is fitted on a grid, with the amplitude profiled. The straight-line drift has errors
scaled by √(χ²/dof) when that exceeds 1. Frame 1 is left out. The verdict is "dose" or "time" when one of
β = 1 and β = 0 passes at p ≥ 0.05 and the other fails. Figure B1 shows each series against time and
against dose, with χ²(β). Figure B2 shows the rates against flux.

**Two strips at one absorber do not agree to their counting errors.** Six groups repeat an absorber within
a series, on another strip and often hours later. Their rates differ by far more than their counting
errors. The extra scatter, fitted by REML over the six groups, is **88 %/h (64–122)**. Fed into the test,
this changes the verdicts:

| verdict (19 series) | counting errors only | errors ⊕ strip scatter |
|---|---|---|
| dose (β = 1 passes, β = 0 fails) | 2 | **4** |
| time (β = 0 passes, β = 1 fails) | 1 | 0 |
| both pass: cannot tell | 0 | 2 |
| neither passes | 8 | 2 |
| rises and falls (opposite signs at ≥ 3σ) | 5 | 1 |
| no burn changes by 3σ: cannot tell | 3 | **10** |

With counting errors alone the test rejects both pure models in most series: the strips differ. With the
strip scatter most series become undecidable, because 2–3 burns spanning a flux ratio of ×2 cannot separate
β = 0 from β = 1 against 88 %/h. One additive scatter for all samples is crude: it is far too large for
the slowly changing series and maybe too small for the fast ones. It is stated, not hidden.

**Where β is determined** (errors ⊕ strip scatter, interval under 2 wide, no sign change):

| series | burns | flux span | β [Δχ² = 1] |
|---|---|---|---|
| R05-S1 | 3 | ×9.6 | 0.96 [0.55, 2.42] |
| R11-S2 | 3 | ×6.6 | 1.11 [0.54, 2.22] |
| R13-S1 | 3 | ×4.5 | 1.09 [0.78, 1.47] |
| R11-S1 | 7 | ×14.6 | 1.92 [1.41, 2.90] |
| R02-S1, R03-S4, R03-S5 | 2 each | ×2.0–2.2 | ≥ 2.1, ≥ 2.1, ≥ 3.8 (at the grid's edge, 4) |
| R06-S3 | 3 | ×21 | **0.19 [0.01, 0.40]** |

So on real liquid surfaces:
- **β ≈ 1 (the dose)** in 3 series;
- **β > 1** in 4: the rate grows faster than the flux, like a threshold, or a fast and a slow process;
- **β ≈ 0.2** in one: a change mostly with time, a little faster at higher flux.

**Confounds the layout does not show:**
- Each series is in time order, mostly from the highest absorber setting downwards or the reverse. A
  sample ageing over the series is aliased with the flux.
- Each burn sits on another strip, so differences between strips enter as above.
- A rise (seen as often as a fall) is not explained here. It could be the specular spot moving in the ROI
  (level drift is about 10 µm/h, below a pixel over a burn), the film reorganising, or the background
  falling.
- 30 keV burns are missing (above).

## 4. Predicting a safe absorber from a short high-flux test (F77)

A prediction from a higher flux needs reciprocity, **β = 1**: the same dose gives the same change. On these
data:
- **β > 1** (4 series): a short high-flux test **overstates** the damage per dose at the lower flux. A
  prediction from it is safe, but costs flux.
- **β < 1** (1 series): it **understates** the damage. A prediction would be unsafe.
- **β = 1** within errors (3 series): a prediction works.

β ranges from about 0.2 to more than 2 between samples, so one high-flux test cannot predict a safe absorber
on a new sample. Two burns at fluxes ×5 or more apart can (one more than F77's test), and only with the
strip scatter in the errors. Most series here span only ×2 and leave β open.

What would settle it: pairs of burns at fluxes about ×10 apart, repeated on two strips at each flux, in
alternating order (high, low, high, low), on 3–4 kinds of sample.

## Not shown, and why

- **The 30 keV burns** (10; one run): not read by the reader's burn, which finds no frames with images (a
  Pilatus 1M run; F38). spec master's rule called 8 of 10 of them "unclear" (1 s points, absorber 0).
- **The burn the reader could not finish:** a 10 keV burn whose change time came out NaN (`ValueError:
  cannot convert float NaN to integer` in `Experiment.burn`). Its signal rose by about 70 % (spec master's
  number). This is a defect for the reader's list: `trends.change_time` with a NaN crossing.
- **Dose per mm²:** the flux is in photons/s. Within a series the slits are the same (S1 0.2 mm on the
  burns read), so β does not need the area.

## Open, for the owner

1. **May qz of the burns be published per series?** It is left out here because one value belongs to one
   group's do-file.
2. **Is a rise damage?** spec master's open question, still open.
