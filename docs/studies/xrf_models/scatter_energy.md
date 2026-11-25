# Synthetic excitation scatter at beam energies that were not measured (design memo)

2026-11-25. A prototype and its validation, for the XRF line-fitting tests
(`docs/studies/xrf_shootout/`). Nothing in the reader or in `tests/synthetic/` was changed.

**The question.** How can the excitation scatter of an MCA spectrum be synthesised at a beam energy
E0 with no measured spectrum? "Scatter" here means the elastic peak, water's Compton peak, and what
the detector does to both: the low-energy tail, the shelf, the Si K escape peaks at E − 1.74 keV,
and the high-energy tail at high rates. Only E0 − 4 … E0 matters: the background under the lines
that are fitted there. "Good enough" means that a line fit on the synthetic scatter is biased as it
is on the real one.

**Evidence.** Every number below is **measured** on real spectra (leave-one-energy-out on readout B,
and readout B's sets applied to readout A at 10 keV), unless it is marked **computed** (the model
run where no spectrum exists to check it) or **reasoned**.

**Regenerate** (private: it reads the owner's spectra bundle; about 15 minutes on 8 processes):

    python tests/tools/xrf_scatter_energy.py --out sample_data/private/xrf_models

Its tables (`loo.csv`, `loo_summary.txt`, `fits.csv`, `readout_a_summary.txt`) and its figures
(`sample_data/private/figures/xrf_models/`) stay private, because they show the private spectra
case by case. This memo quotes only derived numbers from them.

## The answer in short

- **Recommended: carry a measured parameter set to the new energy.** This is the physics model
  (options a and b together). The study's fit (`ScatterModel`) is applied to every measured
  spectrum, and each fitted parameter set is kept whole: the detector's tails, shelf and escape
  factor, and the geometry (angle, O 1s wing, Doppler width). To synthesise at E0, take the set
  that is nearest in beam energy, count rate, detector element and setup. Then let the physics
  carry what truly depends on E0:
  - the Compton kinematics and water's momentum profiles in p_z;
  - the Compton/Rayleigh ratio, scaled by water's cross-section ratio;
  - Reed's escape fraction;
  - the Fano part of the resolution.
- **How good it is.** On readout B, with each energy held out in turn, it predicts the counts in
  the five windows to **10 % (median; rms 16 %, worst 41 %)**. Another real spectrum *at the same
  energy*, from another detector element or file, differs from the held-out one by **14 % (rms 17 %,
  worst 42 %)**. So the prediction is as good as real spectra are alike. The generator's defaults
  miss by **71 %**: they put 3 to 10 times too little under the lines. The nearest measured
  spectrum, shifted by ΔE0, misses by 14 % (rms 26 %, worst 78 %).
- **The energy is not the main variable.** At one beam energy, the shape below E0 changes by 10–25 %
  between detector elements, between count rates and between setups. Between files of one element
  at the same rate it changes by 2 %. So the generator must state which set it used, and the
  synthetic tests should run over the whole bank of sets to get the real spread.
- **Option c (an empirical residual template) adds nothing here.** The free fits of the pre-edge
  sums are close to the Poisson floor (deviance/dof 0.6–2.6; up to 5.5 at 7.4 keV), so their residuals are noise.
  Adding them made every method slightly worse.
- **Readout A** can only be carried from its own three 10 keV sets. Readout B's sets put
  +70 … +230 % too much under its lines at 10 keV (measured). Away from 10 keV, readout A rests on
  assumptions worth about ±30–40 % at E0 − 1 … 2 keV (computed; see "Readout A").

## Data

**Readout B pre-edge sums: 24 cases at six beam energies.** Each case is one detector element of
one energy-scan file. Its points 30–160 eV below an edge were aligned on their mean beam energy
(`rebin_shift`) and summed. There are 20 points per case, 40–44 s in all.

| Group | E0 (keV) | Cases | Setups | Detector elements | Rate (kcps) | Region counts |
|---|---|---|---|---|---|---|
| 6.1 | 6.128 | 4 | two | two | 68–98 | 3–4 × 10⁶ |
| 6.9 | 6.899 | 4 | two | two | 3–5 | 1–2 × 10⁵ |
| 7.2 | 7.166 | 4 | two | two | 21–260 | 1–11 × 10⁶ |
| 7.4 | 7.434 | 4 | one | two | 122–350 | 5–14 × 10⁶ |
| 8.3 | 8.278 | 4 | one (the third) | two | 27–32 | 1 × 10⁶ |
| 9.2 | 9.166 | 4 | one (the third) | two | 43–63 | 2 × 10⁶ |

The 6.1, 7.2, 7.4, 8.3 and 9.2 keV cases are the study's pre-edge sums
(`docs/studies/mca_scatter/summary.md`). The 6.1 and 9.2 keV ones are the committed blanks. For the
committed blanks, these sums give the same counts as the blank files (checked: same totals,
correlation ≥ 0.9992 channel by channel).

The four 6.9 keV cases are new. They are low-rate scans of the same two setups as 6.1–7.4 keV.

A second setup at 7.4 keV was tried and dropped: a sample line near 6.4 keV holds 20 % of the elastic
peak's height there, so those sums are not scatter-only.

**Targets that are only predicted:**
- readout B at 10 keV: three single-scan sums from two of the setups, at 118–145 kcps;
- readout A at 10 keV: E10-f, E10-j and E10-k, three setups.

**Free fits.** Every case was fitted with `mca_scatter.ScatterModel` over E0 − 2.6 … E0 + 0.6 keV
(`fits.csv`, private).
- Deviance/dof: 0.6–0.8 at 8.3–9.2 keV; 1.3–2.6 at 6.1–7.2 keV; 2–5.5 at 7.4 keV (up to 14 × 10⁶
  counts); 0.7–1.6 at 6.9 keV.
- 10 keV: 2–5 on B and 4–10 on A.

## Methods compared

Every prediction for a held-out case uses only the cases of the other energies. Only an overall
scale (Poisson maximum likelihood, in closed form) and the calibration offset (±40 eV) are then
fitted to it.

| Name in the tables | What | Option |
|---|---|---|
| `gen_default` | `mca_more.spectrum` as it is: Biggs profiles, 90°, Compton/Rayleigh 1, `Detector()` | baseline |
| `gen_hard` | the same with study B's hard case (tail 1 %, slope 0.15 keV, shelf 0.2 %) | baseline |
| `shift_nearest` | the nearest-energy measured spectrum (same element first), lines taken off, moved by ΔE0 | baseline |
| `shift_rate` | the same, the spectrum chosen by `set_distance` (below) | baseline |
| `morph_nearest` | the nearest-energy case's whole fitted set, carried to E0 by the model's physics | b, in model space |
| **`morph_rate`** | the same, the set chosen by `set_distance`: **recommended** | a + b |
| `morph_nearest_resid` | `morph_nearest` + that case's smoothed fit residual, against E0 − E | c |
| `morph_bracket` | the nearest sets below and above E0, mixed linearly in E0 | b |
| `bank_mean` | the mean of all training sets carried to E0, with their spread | ensemble |
| `physics` | every parameter a smooth function of E0 (below) | a |
| `physics_resid` | `physics` + the residual template | c |
| `physics_samerun`, `physics_local`, `physics_element`, `physics_const` | variants of `physics`: detector terms from the same setup only, piecewise between energy medians, per detector element, or constant | a |
| `same_energy_ref` | **not a predictor**: another measured case at the held-out energy (same setup first). It is the floor that real spectra set | reference |
| `free_fit` | the held-out case's own free fit: everything fitted | floor |

**`physics` (option a):**
- the resolution: FWHM² linear in E;
- the geometry (angle, O 1s wing, Doppler scale): the same setup's mean, the angle weighted by its
  inverse variance;
- the Compton/Rayleigh ratio: scaled by water's dσ_C/dσ_R (xraylib, independent atoms) between
  energies;
- the tail, its slope, the shelf and the escape × Reed: a straight line in E0;
- the high-energy tail: a straight line in count rate;
- the flat background: per elastic photon.

**`set_distance` (declared before it was scored, not tuned).** Each of these adds 1:
- 1 keV of beam energy;
- a factor of 3 in count rate.

Each of these adds 0.5:
- another detector element;
- another setup.

**Scores**, over E0 − 2.5 … E0, against the held-out spectrum minus the nuisance lines of its own
free fit:
- **deviance/dof**. Its scale is set by the counts: at 10⁶ counts, a 5 % shape error gives tens.
- **window error**: the relative error of the counts in ±2 FWHM windows at E0 − 0.6, 1.0, 1.37,
  1.74 and 2.0 keV (the study's `window_counts_per_keV_*`). The windows' own statistical errors
  are 0.3–0.9 %.
- **false line**: the line that a fixed-centre, fixed-width Gaussian on a quadratic, fitted by
  Poisson likelihood in each window (the reader's P1 with P2), finds on scatter alone. It is given
  in photons per 100 counts in the box, on the real and on the predicted scatter. This is the
  "biased the same way" test.

## Results: readout B, every energy held out in turn (measured)

### All 24 pre-edge cases

- **Window error, per energy:** the median |window error| over the cases and windows of that
  energy.
- **Over all cases:** taken over all 24 cases × 5 windows.
- **|ΔFL|:** the median |predicted − real| false line, in photons per 100 box counts, in the
  E0 − 0.6 / 1.0 / 1.37 / 1.74 / 2.0 keV windows.

| Method | 6.1 | 6.9 | 7.2 | 7.4 | 8.3 | 9.2 | Median | Rms | Worst | Deviance/dof (median) | \|ΔFL\| |
|---|---|---|---|---|---|---|---|---|---|---|---|
| free fit (floor) | 1 % | 2 % | 1 % | 1 % | 1 % | 0 % | 0.7 % | 2.0 % | 12 % | 1.3 | 0.2 / 1.1 / 1.5 / 1.8 / 1.0 |
| *same energy, another case* | *16 %* | *16 %* | *18 %* | *15 %* | *2 %* | *15 %* | *14.0 %* | *16.8 %* | *42 %* | *59* | *0.4 / 0.7 / 1.3 / 1.4 / 1.4* |
| generator defaults | 69 % | 72 % | 72 % | 75 % | 65 % | 69 % | 71 % | 70 % | 95 % | 487 | 2.7 / 3.0 / 14.8 / 36.5 / 7.2 |
| study B hard case | 65 % | 69 % | 70 % | 73 % | 62 % | 66 % | 69 % | 67 % | 93 % | 428 | 2.2 / 2.8 / 12.1 / 31.5 / 6.3 |
| nearest spectrum, shifted | 15 % | 7 % | 7 % | 16 % | 40 % | 15 % | 13.7 % | 25.5 % | 78 % | 113 | 1.9 / 6.2 / 6.8 / 2.6 / 2.5 |
| chosen spectrum, shifted | 18 % | 5 % | 9 % | 11 % | 17 % | 15 % | 12.7 % | 21.9 % | 76 % | 55 | 0.5 / 1.6 / 1.9 / 2.6 / 1.9 |
| nearest set, carried | 11 % | 10 % | 12 % | 15 % | 20 % | 10 % | 12.5 % | 18.4 % | 46 % | 33 | 1.0 / 1.4 / 1.0 / 2.9 / 1.3 |
| **chosen set, carried** | 14 % | 8 % | 13 % | 10 % | 9 % | 10 % | **10.1 %** | **16.0 %** | **41 %** | 36 | 1.0 / 1.3 / 1.4 / 3.2 / 1.8 |
| nearest set + residual (c) | 11 % | 10 % | 10 % | 13 % | 21 % | 10 % | 12.5 % | 19.2 % | 52 % | 42 | 1.3 / 6.9 / 7.8 / 1.9 / 0.9 |
| two sets, bracketing | 11 % | 8 % | 9 % | 17 % | 54 % | 10 % | 12.6 % | 27.9 % | 83 % | 55 | 1.1 / 1.5 / 2.1 / 3.4 / 2.3 |
| mean of all sets | 8 % | 10 % | 11 % | 13 % | 41 % | 11 % | 11.9 % | 22.9 % | 83 % | 144 | 1.8 / 1.5 / 1.8 / 4.4 / 2.2 |
| smooth in E0 (a) | 10 % | 8 % | 18 % | 8 % | 26 % | 11 % | 11.5 % | 21.7 % | 85 % | 30 | 0.7 / 1.5 / 1.5 / 4.3 / 1.8 |
| smooth + residual (c) | 10 % | 9 % | 20 % | 8 % | 27 % | 11 % | 12.0 % | 22.6 % | 84 % | 35 | 0.8 / 6.6 / 4.5 / 3.6 / 1.6 |
| smooth, same setup | 18 % | 14 % | 24 % | 13 % | 12 % | 9 % | 14.5 % | 22.8 % | 82 % | 49 | 0.9 / 1.4 / 1.7 / 2.2 / 1.8 |
| smooth, piecewise | 24 % | 9 % | 22 % | 14 % | 8 % | 10 % | 14.1 % | 21.8 % | 87 % | 42 | 0.7 / 1.5 / 1.4 / 3.2 / 1.8 |
| smooth, per element | 22 % | 11 % | 24 % | 13 % | 16 % | 9 % | 15.5 % | 22.6 % | 76 % | 41 | 0.8 / 1.5 / 1.5 / 3.1 / 1.9 |
| constant | 14 % | 10 % | 12 % | 5 % | 55 % | 33 % | 17.7 % | 33.3 % | 100 % | 72 | 1.2 / 1.5 / 1.2 / 2.6 / 1.8 |

**For scale, the false line on the real scatter** (median over the 24 cases):

| Window | E0 − 0.6 | E0 − 1.0 | E0 − 1.37 | E0 − 1.74 | E0 − 2.0 |
|---|---|---|---|---|---|
| Photons per 100 box counts | −2.5 | −0.7 | +1.9 | **+14.6** | −3.8 |
| Statistical error | 0.3 | 0.7 | 0.9 | 1.0 | 1.0 |

The E0 − 1.74 keV window is the scatter's own escape peak.

- **The generator's defaults** report it **36.5 too many or too few**: they get the sign and the size
  of the bias wrong.
- **The chosen carried set** is off by 3.2.
- **Another real spectrum at the same energy** is off by 1.4.

### The asked-for held-out energies

Each row gives:
- the median deviance/dof;
- the window errors at E0 − 0.6 / 1.0 / 1.37 / 1.74 / 2.0 keV: the median size, with the sign of
  the median.

| Held out | Chosen set, carried | Smooth in E0 | Nearest spectrum, shifted | Generator defaults | *Same energy, another case* |
|---|---|---|---|---|---|
| 8.3 keV | 17; −6 / +8 / +10 / +9 / +10 % | 17; +8 / +41 / +52 / +26 / +20 % | 113; +49 / +52 / +40 / +13 / +7 % | 203; −20 / −40 / −73 / −65 / −67 % | *1.9; +3 / +1 / +2 / +2 / +2 %* |
| 7.2 keV | 69; +10 / +23 / +19 / −14 / −12 % | 108; +21 / +36 / +32 / +18 / +15 % | 240; −20 / +15 / +15 / +5 / +4 % | 2025; −52 / −74 / −92 / −70 / −73 % | *179; +15 / +22 / +21 / +15 / +13 %* |
| 7.4 keV | 47; −5 / −13 / −20 / −10 / −7 % | 80; −6 / −10 / +7 / +5 / −8 % | 752; −28 / −39 / −19 / −5 / −3 % | 4337; −56 / −77 / −91 / −73 / −74 % | *155; +16 / +22 / +17 / +12 / +9 %* |
| 9.2 keV | 48; −11 / −13 / −14 / −10 / −8 % | 52; +10 / −13 / −16 / −12 / −9 % | 122; −24 / −27 / −25 / −12 / −8 % | 487; −13 / −37 / −69 / −72 / −75 % | *93; +23 / +22 / +15 / −6 / −3 %* |
| 6.1 keV | 61; +24 / +17 / +14 / +9 / +8 % | 47; −17 / +11 / +27 / +6 / +8 % | 118; +15 / +30 / +50 / +8 / +5 % | 1364; −65 / −85 / −93 / −61 / −65 % | *97; +21 / +20 / +18 / +15 / +11 %* |

**At 8.3 keV the same-energy reference is only 2 % off.** The 8.3 keV cases pair the same element
at the same rate in two files. That is the one place where the floor is low, and where a
prediction from 9.2 keV (the same setup) shows a real trend that the transported set misses:
- **9.2 → 8.3 keV:** +8 … +15 % in the tail windows (median);
- **8.3 → 9.2 keV:** −3 … −24 %.

### Deep band E0 − 4 … E0 − 2.5 keV

This is predicted/real, away from lines. It is a rough check: the free fits stop at E0 − 2.6 keV.

| Method | 6.1–7.4 keV | 8.3–9.2 keV |
|---|---|---|
| Generator defaults | 0.00–0.01 (nothing there) | 0.00–0.01 (nothing there) |
| Nearest carried set | 0.84–1.24 | 1.08–1.20 |
| Smooth in E0 | 0.61–1.59 | 1.10–1.16 |

The free fit extrapolated gives 0.86–1.28.

### What drives the spread (measured)

- **Same detector element, same rate, two files:** 1–3 % (8.3 keV).
- **Same element, rates 155 against 350 kcps:** 15–22 % (7.4 keV). The low tail at E0 − 0.3 … 1 keV
  and the high-energy tail grow with rate (private figure `loo_7.4keV_private.png`). This is why
  the choice by rate helps: at 7.4 keV the nearest set misses by 15 % and the chosen one by 10 %;
  at 8.3 keV, 20 % and 9 %.
- **Another element of the same detector, same file:** 15–20 % (6.1 and 7.2 keV).
- **Another setup:** errors of one carried set rise from 15 % (same setup, any ΔE0 from 0.3 to
  1.5 keV) to 13–33 % (other setups; private figure `loo_error_vs_dE_private.png`). The error
  hardly grows with |ΔE0| up to 3 keV: the setup and rate matter more than the energy.
- **Mixing setups is what breaks the smooth and bracketing forms.**
  - 8.3 keV is bracketed by 7.4 keV from a high-rate setup and 9.2 keV from its own. The
    bracketing mix misses by 54 % there, and the smooth form by 26 %.
  - Interpolating each parameter across sets also breaks their correlations. The angle, the
    Compton/Rayleigh ratio, the Doppler width, the O 1s wing and the tail trade against each
    other at these resolutions.
  - A whole set keeps them consistent.
- **The ensemble spread is a fair uncertainty on readout B.** Carry every training set to the
  held-out energy and take the spread of their window counts: 15–25 % (median).
  - The real counts fall within it: z rms 0.8–1.4 per energy (1.5 at 10 keV).
  - On readout A at 10 keV, readout B's ensemble is far off: z rms 2.2.

### Readout B at 10 keV, extrapolated from 6.1–9.2 keV

The 10 keV readout B spectra have more tail than any pre-edge set. They are at 120–145 kcps, with
tails of 6–13 %. So every prediction from 9.2 keV and below is low:

| Method | Window error, E0 − 0.6 / 1.0 / 1.37 / 1.74 / 2.0 keV |
|---|---|
| Chosen set (9.2 keV, another setup) | −24 / −34 / −35 / −27 / −25 % |
| Mean of the bank | −1 / −26 / −25 / −19 / −20 % |
| Constant parameters | −14 / −28 / −15 / −7 / −9 % |
| Generator defaults | −25 / −59 / −77 / −81 / −83 % |

**Extrapolating 0.8 keV beyond the bank and into another setup costs about 25–35 %.** The bank
of a real generator would include the three 10 keV readout B sets, so 9.2–10 keV is interpolation
there.

## Why carrying a measured set

1. **It is the most accurate on median, rms and worst case** (10 %, 16 %, 41 %), and it is as
   good as two real spectra of one energy are alike (14 %, 17 %, 42 %).
2. **It keeps the parts apart.** Rayleigh and Compton × photopeak, tail, shelf, escape and
   high-energy tail are each known per channel. That is what the shootout needs for its truth,
   and a shifted spectrum cannot give it.
3. **It keeps each set's parameters consistent with each other.** The fit's degenerate directions
   (angle against Compton/Rayleigh, wing against tail) stay as the data fixed them. Smooth
   interpolation of each parameter (option a) breaks this when the sets come from different
   setups: it is worse at 7.2 and 8.3 keV.
4. **It is noise-free and works at any channel grid, calibration and count level**, while the
   shifted spectrum carries its own Poisson noise (χ²/dof with the template's noise counted:
   5–74 at 6.1–9.2 keV). The shifted spectrum also carries whatever lines its source had.
5. **The residual template (c) is empty here.** The fits are at the Poisson floor on 1–14 × 10⁶
   counts. It could matter for summed spectra of 10⁸ counts (the 10 keV sums, deviance/dof 2–10),
   which no held-out energy can test.

What it does not do well:
- It misses the energy trend within one setup that the 8.3 ↔ 9.2 keV pair shows (±10–20 %). The
  smooth form catches part of that, but loses more by mixing setups.
- A refinement worth testing, not tested here: carry the set, but take the escape × Reed from a
  per-setup line in E0. The smooth form's |ΔFL| at E0 − 1.74 keV is 4.3, against 3.2 for the
  carried set and 2.6 for the shifted spectrum. So the escape is not yet the weak point.

## Readout A

### What carries over from readout B

| | Measured or computed |
|---|---|
| **The physics of the energy dependence** (Compton kinematics, water's profiles in p_z, Reed, Fano, water's Compton/Rayleigh cross-section ratio) carries over: it is the model's, not the detector's. | Checks below |
| **The form of the bank and of `set_distance`** carries over. | — |
| **The sizes of the errors** (about 15 % per carried set within one setup, independent of ΔE0 up to 1.5 keV) are the best guide, but they are readout B's. | Measured on B |

**Checks of the physics:**
- On readout A at 10 keV and 90°, water's independent-atom Compton/Rayleigh ratio is 1.87. The
  measured ratio is 1.9–2.3.
- On readout B (one setup), the measured ratio between 8.3 and 9.2 keV is 0.84. Water's
  cross-sections give 0.76 at the fitted angle: 10 % off.

### What does not carry over (measured)

Readout B's sets put on readout A at 10 keV miss by:

| Window | E0 − 0.6 | E0 − 1.0 | E0 − 1.37 | E0 − 1.74 | E0 − 2.0 |
|---|---|---|---|---|---|
| Chosen set | −21 % | +8 % | +69 % | +162 % | +233 % |
| Smooth form | −1 % | +11 % | +28 % | +101 % | +164 % |

Readout A's tail is 2 % (B: 3–13 %) and its shelf is 0 (B: up to 4 %). Readout A must be built from
its own three 10 keV sets. Those three, from three setups, differ from each other by 0–19 % in the
windows (measured).

### What has to be assumed away from 10 keV

All of these are assumed constant in E0:
- the tail fraction and slope;
- the shelf;
- the escape × Reed (0.75–0.91 at 10 keV);
- the Doppler scale and the O 1s wing (0.8);
- the angle (91°).

**How wrong that could be (computed).** These are the readout A sets carried to 8.3 keV, and how
much the window counts move when each assumption moves by about readout B's range of variation:

| Assumption moved | E0 − 0.6 | E0 − 1.0 | E0 − 1.37 | E0 − 1.74 | E0 − 2.0 |
|---|---|---|---|---|---|
| Tail × 1.5 / × 0.67 | +3 / −2 % | +21 / −14 % | +32 / −21 % | +24 / −16 % | +21 / −14 % |
| Tail slope × 0.6 | +1 % | −10 % | −30 % | −32 % | −31 % |
| Shelf + 0.01 (B-like) | 0 % | +7 % | +19 % | +27 % | +35 % |
| Escape × Reed × 1.25 / × 0.8 | 0 % | 0 % | +2 / −2 % | +9 / −7 % | +12 / −9 % |
| Doppler scale × 1.2 | +8 % | +27 % | +21 % | +8 % | +4 % |
| O 1s wing × 0.5 | −3 % | −25 % | −14 % | −5 % | −3 % |

- At 6.1–7.2 keV the tail terms are larger (up to +39 % at E0 − 1 … 1.37 keV, and +16 % at
  E0 − 0.6 keV), and the Doppler and wing terms are smaller at E0 − 1.37 … 2 keV
  (`readout_a_summary.txt`).
- So readout A away from 10 keV is uncertain by about **±10–20 % at E0 − 0.6 keV (the larger at
  6–7 keV) and ±30–40 % at E0 − 1 … 2 keV**.
- This is reasoned from those sensitivities and from readout B's measured 15 % per carried set.
  Nothing on readout A can check it.
- Readout B's tail did not fall towards low energy: 0.04 at 6.1 keV, 0.06–0.08 at 9.2 keV (measured).
  There is therefore no measured reason to expect readout A's 2 % to grow below 10 keV. A
  silicon drift detector's incomplete-charge tail is often larger at low energies (reasoned, from
  general knowledge, not measured here).

## What the method cannot do

- **Readout A at any energy but 10 keV**, beyond the assumption band above. One measured readout A
  spectrum at another energy would turn it into a measurement.
- **Other angles.** All measured sets have fitted 2θ of 66–113°.
  - The kinematics and water's Compton/Rayleigh ratio are computed for any angle.
  - The Doppler scale is not. It is 1.0 on readout A and 1.1–1.9 on readout B, and it includes
    the spread of angles over the footprint and the detector, which changes with the geometry.
  - Polarisation is taken as the same factor for both processes.
- **Other samples.** The Compton profile, the O 1s wing and the Compton/Rayleigh ratio are
  water's. Another matrix, or a cell window in the beam, changes all three and adds its own lines.
  The sets also hold this geometry's absorption of the scatter on its way out.
- **Count rates outside 3–350 kcps** (readout B pre-edge), and readout B above 9.2 keV except
  through its three 10 keV sets.
- **Below E0 − 2.6 keV**, the model is extrapolated. It reads the deep band within 0.6–1.6 × the
  real one.
- **Above E0** (the high-energy tail, pile-up), it is roughly right only.
- **Readout B without naming the element.** The 15–20 % between elements is real. A generator can
  only offer the bank and its spread.
- **The truth of the windows.** It is the held-out spectrum minus its own fitted nuisance lines,
  which hold up to 43 % of a window's counts in a few trace-line cases (E0 − 1.37 keV at 7.2 and
  8.3 keV). There, the truth itself is only as good as that line fit.

## A generator, sketched

A new module `tests/synthetic/mca_scatter_bank.py`, beside `mca` and `mca_more`:

```python
from synthetic import mca, mca_scatter_bank as sb

sb.SETS                       # {set id: dict(readout, e0, rate_cps, element, setup, params)}, from JSON
sb.choose(readout, e0, rate=None, element=None, setup=None)   # set id by set_distance
s = sb.scatter_at(readout, e0, angle=None, rate=None, set=None, elastic=1e6,
                  calib=mca.CALIB, channels=mca.CHANNELS, offset=0.0, gain=0.0)
                              # -> mca.Spectrum; parts: ('Rayleigh' | 'Compton valence' | 'Compton core',
                              #    'peak' | 'tail' | 'shelf' | 'escape' | 'rtail'), ('background', 'flat')
s.draw(rng)                   # Poisson counts
ens = sb.scatter_ensemble(readout, e0, **kw)   # [(set id, Spectrum)]: every set of the readout at e0
```

- **`set`:**
  - None: `choose`;
  - an id: that set;
  - `'random'`: drawn with `rng`, weighted by distance.
- **`angle`:** replaces the set's angle, with the Compton/Rayleigh ratio scaled by water's
  cross-sections between the two angles. The Doppler scale is kept, which is the uncertain part.
- **Warnings** outside 6.1–10 keV on readout B, and away from 10 keV on readout A.
- **Shootout tests** run over `scatter_ensemble` and report the spread of the bias as a systematic.

**The bank** is the fitted parameter sets (derived numbers, like `scatter_fits.csv`): 24 readout B
pre-edge sets, 3 readout B and 3 readout A sets at 10 keV. Ids are anonymous; setups and elements
are only labels.

**Effort: about 1½ days.**

| Step | Time |
|---|---|
| Move the fit's physics (shells Compton with core and Doppler scales, the high-energy tail) from `tests/tools/mca_scatter.py` into the module, so that the bank is used with the model it was fitted with | ¼ day |
| Add an `--export` to this tool that writes the bank's JSON (no counts, no peak positions) | ¼ day |
| Tests: each set at its own energy reproduces its free-fit model to rounding; `choose` and `set_distance`; the warnings; the ensemble | ¼ day |
| `docs/SYNTHETIC_DATA.md` entry and a Tools catalogue item | ¼ day |
| The real acceptance test: rerun the shootout's blanks section on synthetic spectra from the bank, beside the real blanks, and compare the methods' biases | ½ day |

Optional: refit the bank with the Biggs profiles (`mca_more.biggs_compton`), if the shootout
should keep one Compton model throughout (+ ½ day, rerunning these fits).

## Files

| File | What |
|---|---|
| `tests/tools/xrf_scatter_energy.py` | The prototype and the validation (CLI, `--out` must be private) |
| `sample_data/private/xrf_models/` | `cases.csv`, `fits.csv`, `loo.csv`, `loo_summary.txt`, `readout_a.csv`, `readout_a_summary.txt` (private) |
| `sample_data/private/figures/xrf_models/` | `loo_<E>keV_private.png` (predicted against real per held-out case), `loo_error_vs_dE_private.png` (private) |
