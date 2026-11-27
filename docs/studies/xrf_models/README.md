# Can models stand in for the real scatter and the real lines? (C68, C69)

2026-11-25. This study sits underneath the XRF shootout (`docs/studies/xrf_shootout/`, C65–C67). It
asks whether the shootout's synthetic spectra are good enough to rank line-fitting methods. The
owner's questions (2026-11-25):

> Should we use scaled and shifted real excitation scatter for all tests, or can we describe it
> with a model well enough not to? We only need the low-energy half of the excitation scatter,
> since this is fluorescence fitting. The same question goes for the real fluorescence lines: is a
> Gaussian enough to describe the real thing, and is that what we should use for synthetic data?
> Compare the 7-element detector with the single-element one when possible.

**Evidence:**
- **measured:** fitted to real spectra, or a shootout run;
- **reasoned:** said so where it is (AGENTS rule 6).

**New to this study? Read `walkthrough.md` first.** It follows one public blank through every step
(the fits with their residuals, the thinning, a twin, the floor, a line's shape), explains each
statistic in plain words, and ends with how sure each verdict is. The shootout's own walkthrough
(`docs/studies/xrf_shootout/walkthrough.md`) shows how one test spectrum is made and scored.

**Words used below:**

| Word | Meaning |
|---|---|
| single-element detector | the one-element Si detector (all its data at 10 keV) |
| 7-element detector | the seven-element Si detector; "on the 7-element detector" means one of its elements, alone |
| blank | a real spectrum with scatter only, no sample line in the region |
| line window | where a line is fitted: the line ± 2 detector widths (FWHM); "window miss" uses ± 1 |
| window miss | real counts / model counts − 1 in a line window: what a line fit there inherits |
| misfit (deviance per degree of freedom) | the Poisson χ²/dof of a fit: about 1 when the model is right |
| thinning p | the share of a blank's counts kept to make one test spectrum (about 0.02–0.06) |
| twin | one Poisson draw of a scatter model fitted to a blank, written as a blank |
| the floor | how far apart two draws of one truth land in the shootout: the test's own noise |
| ratio | line photons / background counts in the line window (0.1, 0.3, 1, 3) |
| accurate | \|bias\| ≤ max(2 %, 2 × its standard error), over 500 spectra |
| Poisson fit | the reader's line fit ("Fit lines") by Poisson likelihood (F90's P1); the default when this ran |
| + fixed width | the line's width held at the detector's resolution (an option, off by default; F90's P2) |
| + escapes removed | the Si escape peaks of everything above subtracted before the fit (F90's P3): an option when this ran, on by default since 2026-11-26 (F110) |
| generator defaults, Gaussian detector, full model | the three scatter models (1a) |
| 9.2 keV blank a | a public blank: `tests/reference/mca_scatter/E9.2-a.csv` (beam energy, then the letter) |

## Short answer

**Scatter: a model can stand in for the real scatter only partly, and only the full model.**
- **The generator defaults and a Gaussian detector cannot.** Under a line they miss the real
  scatter by 12–36 % and 11–26 % (1a). In the shootout a method's bias on their twins is a
  median 9–11 % away from its bias on the real blank, 4.5–5 × the floor (1b).
- **The full model (tails, shelf and high tail free) comes close for the K lines.** Under Cr, Cu,
  Ni and Zn its twins land within 1.3–3.7 × the floor of the real blanks (the floor is how far
  two Poisson draws of one truth land apart).
- **It is not close for Ti K and La L under a 6.1 keV beam.** There, 1.5–1.6 keV below the beam,
  the twins differ from the real blanks by 8–9 %, against a floor of 3–4 %. They also flatter the
  methods: *Poisson fit + fixed width + escapes removed* is accurate in 17 of 64 conditions on the twins and in 4 on the real blanks.
- **The real blanks also hold structure no model twin has** (a Cu-shaped feature, 1a).
- **So keep using the real blanks, scaled and shifted, wherever one exists for the setup and
  energy.** Use the full model where none exists (part 3), with the floor and the 6.1 keV caveat
  stated.

**Lines: a Gaussian is enough for the single-element detector, not for the 7-element detector.**
- **The single-element detector** is close to Gaussian, about 5 % outside. But its
  width is its setup's (1.03 or 1.19–1.24 × the resolution measured on the scatter).
- **The 7-element detector (one element of it)** has 23–81 % of each line (median 46 %) in a
  short low-energy skew, and the amount depends on the element.
- **What the shape changes:** in the shootout a Gaussian line gives the same verdicts as the
  elastic-shaped one. The 7-element detector's real shape costs the fixed width 6 %; the reader's
  free-width fit with the escape removal (*Poisson fit + escapes removed*) stays within 2 %.
- **So synthetic data for the 7-element detector should carry the measured skew, per element; for the single-element detector a
  Gaussian of the setup's own width will do (2c, part 4).**

## The data: both detectors

| | Single-element detector | 7-element detector (one element) |
|---|---|---|
| Scatter, public blanks (`tests/reference/mca_scatter/`) | 10 keV blanks f, j and k | 6.1 keV blanks a…d; 9.2 keV blanks a…d; 10 keV blanks d and i |
| Scatter, private (`sample_data/private/`) | 10 keV only (3 runs) | 6.0–9.8 keV energy scans (L3 edges), 10 keV |
| Lines, private | an L family at 10⁶ counts per file (5 files, 2 runs); the burn series' K line near 8 keV | one K family on all seven elements, in two files (3·10⁵ counts per spectrum) |

The single-element detector exists only at 10 keV, so its scatter at other beam energies cannot be measured: see
part 3.

**The single-element detector is three setups.** The bundle labels its files by three detector settings, and the
resolution differs between them (part 2). The public blanks give one of each:
- **10 keV blank k's setup:** the scatter study's resolution for the single-element detector came from it (10 keV blanks g and k);
- **10 keV blank f's setup:** the burn series and L file 2 are in it;
- **10 keV blank j's setup.**

## 1. The scatter

### 1a. The ladder

Every public blank is fitted over its whole range (E0 − 2.5 to E0 + 0.7 keV) by Poisson maximum
likelihood. Three models are used, all built on the scatter study's `ScatterModel`
(`tests/tools/mca_scatter.py`):

- **generator defaults:** the scatter the synthetic shootout used: study B's hard case (noise 0.12 keV at
  Fano 0.115, a 1 % tail over 0.15 keV, a 0.2 % shelf, escape 1 × Reed, water's O 1s wing and
  Doppler widths). Free: the photons, Compton/Rayleigh, the angle, the offset, a flat background;
- **Gaussian detector:** a Gaussian detector (no tail, shelf or high tail), with the noise, escape, O 1s
  wing and Doppler widths free;
- **full model:** the scatter study's model, every axis free.

Each fit may add nuisance lines (K and L lines of elements whose lines fall in the region,
amplitude ≥ 0).

**Results (measured;** `scatter/ladder.csv`, **figures M1 and M2):**
- **Window misses** are real counts / model counts − 1, in ±1 FWHM line windows at E0 − 0.6 … 2.3 keV.
  Each cell gives the median over the readout's blanks [and the maximum].
- **"At use"** is the deviance per dof below the beam, scaled to the counts the shootout uses: a
  thinning p (1000 or 3000 counts in the line window) scales a systematic misfit, so the value is
  1 + p × (misfit − 1).

| Model | Detector | Window miss, 0.6–1.74 keV below E0 | Window miss, 2.0–2.3 keV below | Misfit below E0, full counts | Misfit at use |
|---|---|---|---|---|---|
| generator defaults | single-element | 12 % [33 %] | 15 % [62 %] | 27 (9.5–5200) | 1.7, 2.4 |
| generator defaults | 7-element | 13 % [47 %] | 36 % [67 %] | 58 (31–20000) | 3.0–5.4 |
| Gaussian detector | single-element | 2.9 % [8.8 %] | 11 % [43 %] | 14 (5.9–270) | 1.4, 1.7 |
| Gaussian detector | 7-element | 2.4 % [25 %] | 26 % [50 %] | 14 (2.4–4200) | 1.15–2.4 |
| full model | single-element | 0.9 % [1.7 %] | 0.9 % [2.3 %] | 5.1 (3.0–8.9) | 1.16, 1.22 |
| full model | 7-element | 0.5 % [4.3 %] | 2.3 % [11 %] | 1.6 (0.7–4.7) | 0.97–1.18 |

**What it says:**
- **The generator's scatter is wrong by 12–36 % under a line.** It is too low near the beam and
  far too high 2 keV below it on the 7-element detector. Its misfit is visible even at the shootout's counts
  (misfit 1.7–5.4).
- **A Gaussian detector is not enough for the scatter.** It reads within about 3 % near the beam,
  but misses by 11–26 % (up to 50 %) 2 keV below. That far down, what lies under a line is the
  detector's tail and shelf of the elastic and Compton photons.
- **The full model is enough at the shootout's counts.** It is within 1 % in the line windows (the 7-element detector
  at 6.1 keV, 2 keV below the beam: up to 11 %), with misfit 0.97–1.22 at use.
- **A misfit below 1 at full counts** (the 9.2 keV sums, 0.65–0.8): those are energy-scan points
  shifted by interpolation before summing, which correlates neighbouring channels.

**The "clean" blanks are not quite clean.** The full model puts a Cu-shaped line into every
10 keV and 9.2 keV blank, worth 1–11 % of the counts in a Cu line window (`line_Cu_box_fraction`). At
10 keV Cu Kα (8.04 keV) sits on the Compton escape (8.07 keV), so part of it may be escape misfit
the model absorbed. Either way it is in the real blanks, and C66's Cu results on them include it.
The twins below are drawn from the scatter alone (elastic, Compton, background), without the
fitted lines. So where the twins and the real blanks disagree on Cu, this feature is the first
suspect.

### 1b. The twins in the shootout

Each scatter fit becomes a **model twin** of its blank: one Poisson draw of the scatter on the
blank's channels (`scatter/twins_<model>/`). `xrf_blanks.py --blank-dir` then runs the C66
shootout on the twins, exactly as on the real blanks: the same 240 conditions, 50 series of 10 and
8 methods. If a method's biases on the twins match its biases on the real blanks, the model can
replace the real scatter for testing line fits.

**The floor.** One real blank is one Poisson draw, and so is each twin. The shootout's
replicates thin that one draw (p ≈ 0.02), so every replicate carries the draw's own fluctuations.
Two exact copies of the truth would therefore still disagree. A second, independent draw of the
full model's twins (`twins_full_redraw/`, `scatter --redraw`), run through the same shootout and
compared with the first draw, measures how much. A model can stand in for the real scatter where
its twins are no farther from the real blanks than that.

**Results (measured;** `scatter/compare*.csv`, **figure M3).** The table gives the median |bias on
the twin − bias on the real blank| over the 7 fitting methods (window sums excluded), in units of
the injected line's photons.

| Twins of | All | Line = 3 × background | Line = background | Single-element detector | 7-element detector | "Accurate" verdict the same |
|---|---|---|---|---|---|---|
| **floor: two draws of the full model** | **2.1 %** | **0.4 %** | **1.1 %** | **1.1 %** | **2.4 %** | **89 %** |
| full model | 4.0 % | 0.8 % | 2.3 % | 3.1 % | 4.1 % | 86 % |
| Gaussian detector | 11 % | 2.3 % | 7.5 % | 12 % | 10 % | 81 % |
| generator defaults | 9.3 % | 2.5 % | 6.8 % | 7.5 % | 9.8 % | 81 % |

By line (median over methods and conditions):

| Twins of | Cr K | Cu K | Ni K | Zn K | Ti K | La L |
|---|---|---|---|---|---|---|
| floor | 1.4 % | 1.9 % | 1.9 % | 0.6 % | 3.7 % | 3.3 % |
| full model | 1.8 % | 2.5 % | 2.7 % | 2.2 % | **8.2 %** | **9.3 %** |
| Gaussian detector | 8.5 % | 4.9 % | 18 % | 11 % | 13 % | 11 % |
| generator defaults | 11 % | 3.7 % | 12 % | 6.6 % | 11 % | 11 % |

Conditions where *Poisson fit + fixed width + escapes removed* (the reader's options) is accurate:

| | Cr K | Cu K | Ni K | Zn K | Ti K | La L |
|---|---|---|---|---|---|---|
| real blanks (C66) | 5 | 19 | 18 | 3 | **2** | **2** |
| full-model twins, two draws | 12, 9 | 24, 23 | 12, 11 | 1, 1 | 9, 14 | 8, 8 |

**What it says:**
- **The generator's and the Gaussian detector's twins are not the real scatter.** A method's bias
  moves by a median 9–11 %, 4.5–5 × the floor. Both put too much or too little under
  the line (1a), and the line fit inherits that.
- **The full model's twins are within about twice the floor overall:** 1.3–1.4 × it for Cr, Cu and
  Ni, and 3.7 × for Zn under the 10 keV beam.
- **Ti K and La L under 6.1 keV are where the full model fails:** 8–9 % against a floor of 3–4 %.
  These are the line windows 1.5–1.6 keV below the beam on the 7-element detector's 6.1 keV blanks, near the low end of
  the fitted range, where the model misses by up to 11 % (1a). Ni K under 9.2 keV sits as far below
  its beam and is fine, so this is the 6.1 keV blanks, not the distance alone. On the twins the methods look better there than they are: *Poisson fit + fixed width + escapes removed* is accurate in 17
  (first draw) or 22 (second) of 64 conditions on the twins, and in 4 on the real blanks.
- **The best method for a condition is a noisy thing.** Between two draws of one truth, the method
  with the smallest |bias| is the same in only 58 % of conditions (44 % between the full twins and
  the real blanks). A ranking is meaningful only over many conditions.
- **Window sums agree to 0.2 %** between every twin and its real blank: the twins carry the right
  counts. The differences come from the shape under the line.

## 2. The lines

### 2a. Probes and shapes

`tests/tools/xrf_lineshape.py`, on the private bundle. The probes are:
- **L files 1…5:** the single-element detector, an L family (Ll, Lα, Lβ, Lγ) at 1.5·10⁶ counts, 5 files of 16 spectra at
  10 keV. L file 2 is in 10 keV blank f's setup, the other four in 10 keV blank k's.
- **the burn series' K line:** the single-element detector, the burn series' K line near 8 keV, the nine strongest series summed
  (5·10⁵ counts).
- **K files 1 and 2, elements 1…7:** the 7-element detector, one K family on each element of two files (2 spectra
  of 5 s each, 5·10⁵ counts per element).
- **K files 1 and 2, all 7 summed:** the seven elements summed raw channel by raw channel, as summing a 7-element
  detector's channels gives.

Each family's lines (tabulated energies and intensities, `synthetic.mca_more`) go through the
generator's detector response. Free in every fit: one amplitude per subshell (Kα, Kβ; L1, L2, L3),
an energy offset and gain, a quadratic background, and free Gaussians for the elastic's and the
Compton peak's Si escape where they fall in the window. The ladder:

- **Gaussian at resolution:** the width fixed to the readout's resolution measured on the scatter
  (`docs/studies/mca_scatter`: A noise 0.065 keV, Fano 0.137; B 0.105 keV, 0.107);
- **Gaussian:** the width free;
- **elastic's shape:** the tail and shelf measured on the readout's elastic line (medians of the
  scatter fits: A 2 % over 0.64 keV, no shelf; B 5.2 % over 0.34 keV, shelf 0.8 %), width free;
- **one tail:** a low-energy exponential tail (fraction and decay free);
- **tail + shelf**, and **two tails + shelf** (a Hypermet-like shape).

The family is identified from the data at run time and never written out. `lines/line_shapes.csv`
holds derived numbers only: no spectrum, peak position or element.

### 2b. Results

**Measured;** `lines/line_shapes.csv`, **figure M4.**

**The single-element detector: nearly Gaussian, but its width depends on the setup.**

- **Fit quality:** misfit falls from 5.5–5.9 (Gaussian) to 3.7–4.0 (tail + shelf) on 1.5·10⁶
  counts.
- **What is not Gaussian:**
  - a short tail of 1–5 % of the photons with a 50 eV decay;
  - a flat component of 6–13 % that the fit calls a shelf (with a quadratic background over 3.5 keV
    and six lines, part of it may be background shape: reasoned, not settled).
- **Width.** In 10 keV blank k's setup (L files 1, 3, 4 and 5) a Gaussian is 1.03 × the resolution measured
  on the scatter. In 10 keV blank f's setup (L file 2, and the burn series' K line) it is 1.19–1.24 × it.

  **This explains C67's "line 21 % wider than the measured resolution":** the burn series were
  recorded in 10 keV blank f's setup. The line has the width of its setup, and
  `xrf_shootout.MEASURED_DET` assumes 10 keV blank k's (from 10 keV blanks g and k). So **The fixed width must come from
  the same setup as the data** (Q12 in the shootout's QUESTIONS.md).

**The 7-element detector (one element of it): not Gaussian.**

- **Fit quality** (14 elements): misfit 24–104 for a Gaussian with free width, 14–84 with the
  elastic's shape, and 2.9–8.7 with one tail. A second tail or a shelf adds little.
- **The tail:** 23–81 % of each line's photons (median 46 %) sits in a short low-energy tail with
  a decay of 48–87 eV. That is about one Gaussian σ, so the peak is skewed rather than tailed.
  - Each single spectrum shows it on its own (misfit 20 → 2), so it is not two shifted peaks summed.
  - The elastic-derived tail (5 % over 0.34 keV) does not describe it.
- **Width.** The Gaussian core of the one-tail fit is 0.96–1.06 × the resolution. A Gaussian fit
  reads 1.10–1.42 × it.
- **The elements are not alike.** Elements 2 and 5: 23–30 % tail. Elements 1, 3 and 4: 43–53 %.
  Element 6: 70–76 %. Element 7: 81 %, with an 85 eV decay and misfit 8.5 even with the tail.

  The same element gives the same shape in both files (e5 0.30 and 0.28; e6 0.70 and 0.76), so
  the shape belongs to the element.

**The seven summed:** tail 42–43 % over 67 eV, core 1.005 × the resolution, misfit
12–13 at 3.7·10⁶ counts. Summing raw channels works here because the elements' raw channels line
up.

**A trap in the 7-element headers.** In one file the header gives elements 5–7 a gain of
0.010856 keV per channel against 0.01000 for elements 1–4. Taken at its word, it puts their Kα
8.6 % too high. A K line's energy is fixed, and their raw channels line up with elements 1–4, so
the header gain is wrong there.

Putting each element on an energy axis by its header calibration and then summing ("with the header's gains")
smears the line to 1.37 × the resolution: misfit 5800, against 13 for the raw sum. Every per-element
fit above uses element 1's calibration by raw channel. A reader that sums the elements of a
7-element detector should check each element's calibration against a known line before trusting
the header.

### 2c. Does the line's shape change the verdicts?

`xrf_blanks.py --line-shape` injects other shapes into the same real blanks:
- `gaussian`: no tail, no shelf;
- `line`: the measured medians: on the single-element detector a tail of 3.4 % over 56 eV with a 12.6 % shelf, on the 7-element detector a tail of
  45.8 % over 58 eV.

The width stays each blank's. Each method is calibrated on a clean twin of the same shape, as in
C66.

**Results (measured;** `shape/run_gaussian`, `shape/run_line` **against C66's** `run_blanks`**,
figure M5).** The blanks, thinnings and seeds are C66's; only the injected line's shape differs.
"Strong" means the line has 3 × the background in its line window.

| Method | Detector | Accurate: elastic-shaped (C66) | Gaussian | Real-shaped | Median bias, strong lines: elastic → real-shaped |
|---|---|---|---|---|---|
| Poisson fit + fixed width + escapes removed | 7-element | 41 of 160 | 32 | **19** | +0.4 % → **−6.0 %** |
| Poisson fit + fixed width + escapes removed | single-element | 8 of 32 | 7 | 6 | −3.3 % → −4.2 % |
| Poisson fit + escapes removed | 7-element | 39 | 36 | 34 | +0.2 % → −1.3 % |
| Poisson fit + escapes removed | single-element | 16 | 13 | 11 | −0.1 % → −0.5 % |
| Poisson fit | 7-element | 29 | 26 | 17 | +1.8 % → +2.0 % (by target: below) |
| PyMca | 7-element | 17 | 20 | 18 | −0.3 % → −0.8 % |
| PyMca | single-element | 0 | 0 | 0 | −7.8 % → −9.9 % |
| PyXRF | 7-element | 15 | 18 | 19 | +8.2 % → +8.0 % |
| XeRay | 7-element | 7 | 8 | 3 | −3.8 % → −5.5 % |

**What it says:**
- **A Gaussian line gives the same verdicts as the elastic-shaped line.** The median change of a
  fit's bias is 1.4 % (0.7 % for lines at least as strong as the background), about the
  replicates' noise.
- **The real shape on the 7-element detector costs the fixed width 6 %:** −6 to −7 % on the Cr, Cu, Ni and Ti lines.
  - It is not noise. On the noise-free spectra (thinned blank's mean plus the line), *Poisson fit + fixed width + escapes removed*
    reads −4.9 to −7.2 % with the real shape and −1.7 to +1.3 % with the elastic's (walkthrough,
    step 5).
  - It is not simply the part of the line outside a Gaussian either: each method is calibrated on
    a clean twin of the same shape, which takes that part out. A fixed-width Gaussian cannot follow
    the skew, so the quadratic background bends to take up the rest. Over real scatter that bend
    costs photons; on the flat, faint background of the calibration twin it does not (reasoned;
    the size is measured).
  - That is C67's finding again, from the other side: the fixed width needs the line's own width and shape, not
    the detector's resolution.
- **With the width free and the escapes removed (*Poisson fit + escapes removed*) the shape hardly matters:** within 2 % on
  every target, except La L under 6.1 keV (+12.5 % → +5.6 %).
- **Without removing the escapes (*Poisson fit*) the skew moves the answer by target.** On strong lines Ti K goes from
  −3.6 % to +13 % and La L from +8.8 % to −6.1 %; the others move by 1–3 %. That is why *Poisson fit*'s
  accurate count falls from 29 to 17. Both lines sit beside the scatter's Si escape peak under a
  6.1 keV beam, and the free width trades with it (reasoned).
- **The whole-spectrum fitters barely move** on the 7-element detector (PyMca and PyXRF within 0.5 %, strong lines): their
  errors lie in the background, not in the line.
- **The single-element detector changes little**, as its real lines are nearly Gaussian (2b). PyMca reads 2 points
  lower there on strong lines, perhaps because its line shape has no shelf (reasoned).

## 3. Scatter at beam energies with no data

`tests/tools/xrf_scatter_energy.py` and its design memo, `scatter_energy.md` (a subagent of this
session, 2026-11-25). The method was tested by leaving one energy out on the 7-element detector: each of 24
pre-edge sums at 6.1–9.2 keV was predicted from the other energies' sums. Only a scale and the
offset were fitted to it. The table gives the error of the counts in ±2 FWHM windows 0.6–2.0 keV
below the beam (measured):

| Prediction | Median | Rms | Worst | Misfit |
|---|---|---|---|---|
| The generator's defaults | 71 % | 70 % | 95 % | 487 |
| The nearest measured spectrum, shifted by ΔE0 | 14 % | 26 % | 78 % | 113 |
| Every parameter a smooth function of E0 | 12 % | 22 % | 85 % | 30 |
| **A whole measured parameter set carried by the physics** | **10 %** | **16 %** | **41 %** | 36 |
| *Another real spectrum at the same energy (another element, rate or file)* | *14 %* | *17 %* | *42 %* | *59* |

**How the recommended method works.** The set is chosen by nearness in beam energy, count rate,
detector element and setup. The physics then carries what depends on E0: Compton kinematics,
water's profiles, the Compton/Rayleigh cross-section ratio, Reed's escape fraction and Fano.

**What it says:**
- **The beam energy is not the main variable.** At one energy, the scatter below E0 changes by
  10–25 % between detector elements, count rates and setups. Between two files of one element at
  one rate it changes by 2 %.
- **A prediction for a new energy is as good as two real spectra are alike.** Real scatter is
  specific to its setup, element and rate.
- **The single-element detector cannot borrow the 7-element detector's sets.** Put on the single-element detector at 10 keV, they put 70–230 % too
  much 1.4–2 keV below the beam (measured). The single-element detector away from 10 keV rests on its own three
  10 keV sets with the detector terms held constant: worth ±30–40 % 1–2 keV below the beam
  (computed; the memo's "The single-element detector").
- **An empirical residual template adds nothing.** The fits are at the Poisson floor.

**The proposed generator** (`tests/synthetic/mca_scatter_bank.py`, not built: about 1.5 days):
- a bank of the fitted sets as JSON (derived numbers only);
- `scatter_at(readout, e0, …)`, which returns an `mca.Spectrum`;
- `scatter_ensemble(…)`, so that a shootout can report the spread over sets as a systematic.

## 4. What synthetic data should use

For tests of line fitting (the shootout and its successors). Measured above unless marked.

1. **Scatter: use the real blanks, scaled and shifted, wherever one exists** for the readout,
   setup and beam energy (C66's `xrf_blanks.py`). They carry what no model does: the traces and
   escape structure (1a). Real scatter differs by 10–25 % under a line between detector elements,
   count rates and setups (part 3), so test on several blanks, not one.
2. **Where no blank exists, use the full model with a whole measured parameter set** carried to the
   new energy by the physics (part 3's recommended method). It is within 1.3–3.7 × the floor for
   every line tested except two. **Do not use the generator's defaults or a Gaussian detector for
   the scatter:** they move a method's bias by a median 9–11 %.
3. **Those two: Ti K and La L under a 6.1 keV beam.** Treat model-based results there with care:
   the full model's twins make *Poisson fit + fixed width + escapes removed* look 4–5 × better there than on the real blanks (17 or 22
   accurate conditions of 64, against 4).
4. **Lines on the single-element detector: a Gaussian of the setup's own width.** That
   is 1.03 × the resolution measured on the scatter in 10 keV blank k's setup and 1.19–1.24 × in 10 keV blank f's.
   The small tail and shelf change nothing measurable (2c).
5. **Lines on the 7-element detector (one element of it): the measured skew**
   (`xrf_blanks.py --line-shape line`: 46 % in a 58 eV tail). To test what varies between
   elements, use the range per element: 23–30 % (elements 2 and 5) to 81 % (element 7).
6. **The fixed width (the reader's option) must come from the data's own setup and shape:** from
   the line's own width, not the detector's nominal resolution. On the 7-element detector's real shape it reads
   6 % low; on the single-element detector in 10 keV blank f's setup, 11 % low (C67).
7. **Before summing the elements of a 7-element detector, check each element's calibration against
   a known line.** One file's header puts elements 5–7 8.6 % off (2b). (Reasoned, from one file:
   the reader does not yet sum elements.)
8. **Report the floor with every twin-based result:** a second draw of each twin, run the same way
   (`scatter --redraw`). A difference smaller than the floor is not a difference.

## Regenerate

From the repository root, in the shootout's environment (`docs/studies/xrf_shootout/README.md`):

    python tests/tools/xrf_models.py scatter --out docs/studies/xrf_models/scatter          # 4 min, 13 CPUs
    python tests/tools/xrf_blanks.py --blank-dir docs/studies/xrf_models/scatter/twins_full \
        --out docs/studies/xrf_models/scatter/run_full \
        --methods window,fit_data,p1,p1p3,p1p2p3,xeray,pymca,pyxrf --jobs 12             # also _generator, _gaussian
    python tests/tools/xrf_models.py scatter --out docs/studies/xrf_models/scatter --models full --redraw
    python tests/tools/xrf_blanks.py --blank-dir docs/studies/xrf_models/scatter/twins_full_redraw \
        --out docs/studies/xrf_models/scatter/run_full_redraw \
        --methods window,fit_data,p1,p1p3,p1p2p3,xeray,pymca,pyxrf --jobs 28             # the floor
    python tests/tools/xrf_models.py compare --out docs/studies/xrf_models/scatter
    python tests/tools/xrf_blanks.py --line-shape line --out docs/studies/xrf_models/shape/run_line \
        --methods window,fit_data,p1,p1p3,p1p2p3,xeray,pymca,pyxrf --jobs 12             # also gaussian
    python tests/tools/xrf_lineshape.py --out sample_data/private/xrf_models/lines \
        --public docs/studies/xrf_models/lines                                           # private bundle, 1 min
    python tests/tools/xrf_models_figures.py --out docs/studies/xrf_models

Each shootout run takes 45–80 minutes on 8–12 CPUs, 20 minutes on 28 (PyMca is most of it). The line fits need the
decrypted private bundle (`docs/studies/xrf_shootout/README.md`, step 2f), and so does part 3. The list
of bundle files they read is private as well (bundle file ids are not published):
`sample_data/private/xrf_models/probes.json`, which the owner's local session keeps. Their figure of the
spectra (`L1_line_fits_private.png`) stays under `sample_data/private/xrf_models/lines/`.

Tools menu: Fluorescence (MCA): "Scatter models against the real blanks", "Real line shapes on both
detectors" and "Models study figures (M1-M5)".

## Files

| File | What |
|---|---|
| `scatter/ladder.csv` | one row per blank × model: deviances, window misses, fitted detector and Compton numbers, nuisance lines |
| `scatter/residuals.csv` | per channel of every public blank: counts, the model, its scatter part, the deviance residual |
| `scatter/twins_<model>/` | the model twins of the ten clean blanks (blank files) |
| `scatter/twins_full_redraw/` | a second, independent draw of the full model's twins: the floor |
| `scatter/run_<model>/`, `run_full_redraw/` | the C66 shootout on them (`xrf_blanks.py`'s outputs) |
| `scatter/compare*.csv` | twin against real, per condition × method, and summaries |
| `shape/run_<shape>/` | the C66 shootout with Gaussian and real-shaped lines |
| `lines/line_shapes.csv` | the shape ladder on the real lines: derived numbers only |
| `M1`…`M5` | figures (`tests/tools/xrf_models_figures.py`) |
| `walkthrough.md`, `walkthrough/` | one blank through every step, with each statistic explained (`tests/tools/xrf_walkthrough.py`) |
| `scatter_energy.md` | part 3: scatter at beam energies with no data (`tests/tools/xrf_scatter_energy.py`) |

## Limits

- **Few spectra from the single-element detector.** The single-element detector's scatter is three blanks at one beam energy.
- **The line probes are few families.** One L family and one K family on the single-element detector, one K family on the 7-element detector,
  all at high count rates. A short tail that grows with rate would be larger here than in a slow
  scan (not measured).
- **The shelf on the single-element detector** is not separable from the background with confidence (2b).
- **The twins test whether the scatter's shape is right on average.** Each is one draw (the floor
  is one more), and the real blanks' traces (1a) are not in them.
- **The floor is measured for the full model only.** The other models' twins are far enough off
  that a floor of the same size would not change the verdict (reasoned).
- **The line-shape runs share C66's seeds,** so their differences are the shape's, but the 2 %
  "accurate" test still flips verdicts near the edge (Gaussian against elastic: up to 16 % of
  conditions per method).
