# The scattered beam in real MCA spectra (DATA_NEEDS row 3, F90)

The owner's non-cloud agent, 2026-11-24. **Measured on real spectra.** The
owner's private beamline data hold no pure-water blank, so the blanks here
are spectra with no fluorescence line near the scatter (see "Which spectra").
The aim is to check the synthetic generator that study B
(`docs/studies/mca_fit/summary.md`) rests on (`tests/synthetic/mca.py`).
Its two uncertain axes are the O 1s Compton wing and the Si escape fraction
(B7).

**Regenerate** (from public files only, about 1 min):

    python tests/tools/mca_scatter.py --out docs/studies/mca_scatter

The table `scatter_fits.csv` was made from the private spectra by the same
model (the private scripts import nothing else). The tool refits the four
public example spectra (`tests/reference/mca_scatter/E10-*.csv`) and draws
both figures. Tools menu: Fluorescence (MCA), "Scatter in real MCA spectra".

## In one paragraph

Real scatter at 6–10 keV was fitted with the generator's own physics and
every uncertain axis left free. Results by feature:

- **Si escape.** Reed's fraction is right to about 10 % at 6–7.4 keV. It is
  low by 30–55 % at 8.3–9.2 keV on one readout. At 10 keV it is right to
  about 20 % on the other.
- **O 1s wing.** Water's impulse-approximation wing at full size is
  rejected by every spectrum. Readout A measures 0.78–0.87 of it. Readout B
  measures 0–0.35, but there the wing trades against a broad detector tail.
- **Scatter under a line.** Readout B carries detector tails the generator
  does not have: a low-energy tail of 3–12 % with a 0.3–0.5 keV decay, and a
  high-energy tail of up to 11 %. So what lies under a line is 1.5–3.2 × the
  generator's hard case on B. On readout A it is 1.03–1.23 ×.
- **Detector resolution.** It matches the generator's default to about
  ±15 %, apart from one run at +45 %.
- **Compton peak.** The water-shell width is right to 5 % on readout A. It
  is 1.15–1.7 × on readout B, where the spread of angles over an element is
  folded in.

## The spectra

**Where the spectra are (row 2).** No SPEC data file holds a spectrum: 1043
MCA files from 12 runs were checked. The scan's block has a
`#V <datafile>_<scan>_mca` line, which only points to a file. 1007 of the
1043 scans have it; 26 `a2scan`, 11 `ascan` and 4 `escan` blocks lack it,
although their file exists. That file, `vortex/<datafile>_<scan>_mca`, is
SPEC-like:

- one `#S n mca_save_point Point:p Scan:s Datafile:d` block per point and
  per detector element;
- in each block `#T`, `#Q` (H K L), `#Energy` (SPEC's `en`), `#Monc`,
  `#@CTIME` (preset, real, live), `#@CALIB` and the counts in `@A`;
- `#@CALIB` is in eV or in keV per channel; on the 7-element readout it is a
  nominal 0 10 0;
- the 7-element readout writes `#@CHANNEL k`.

**Two readouts.**
- **A:** a single-element readout, 2048 or 4096 channels of 4.8–14 eV.
- **B:** a seven-element readout, 4096 channels of 10 eV. Each element is
  fitted on its own, with its own calibration.

**Calibration.** The files' calibrations are close to right: the gain is
within 1.6 % and the offset within tens of eV.
- **B:** the gain was measured from the elastic line across beam energies
  (energy scans).
- **A:** the gain was measured from the elastic line and air's Ar Kα
  (2.957 keV).
- The offset is fitted per spectrum.

The detector's position is not logged, so the scattering angle 2θ is
measured from the Compton shift.

**Which spectra.** Not every record could be used:
- The energy scans cross absorption edges of the samples' elements, and
  points above an edge carry that element's lines under the scatter. So each
  scan's **pre-edge** points (30–150 eV below the edge) were aligned to
  their mean beam energy (`rebin_shift`) and summed, per element. These give
  the 6.1, 7.2, 7.4, 8.3 and 9.2 keV cases.
- At 10 keV, whole scans were summed. Most carry traces of Cu and Zn
  (below 10⁻³ of the elastic photons). Cu Kα (8.04 keV) sits on the Compton
  escape (≈ 8.07 keV), so those spectra give no escape fraction.
- The `#Energy` headers of 20 and 30 keV do not match their spectra (there
  is no elastic line there), so those were dropped.
- Tiers: **clean** means no line above 10⁻⁴ of the elastic photons in
  E0 − 2.4 … E0 + 0.6 keV. **Trace** means lines below 10⁻³. **Line** means
  stronger lines.

38 spectra were fitted. 30 give good fits. The 8 not shown are listed on S2.

**Labels.** Spectra are labelled by beam energy (to 0.1 keV) and a letter.
Nothing ties a label to a run.

## The model

Over E0 − 2.4 … E0 + 0.6 keV, by Poisson maximum likelihood (the tool's
docstring has every term):

- elastic photons at E0;
- water's Compton shells (`mca.shell_compton`, study B's 'shells' model) at
  a free angle;
- the O 1s part × `core`, every momentum width × `doppler`;
- the generator's detector (`mca._response`): free noise, low tail, shelf
  and escape × Reed;
- **plus a high-energy tail** (pile-up), which the generator lacks;
- nuisance K lines of elements whose lines fall in the region;
- a flat background.

Errors are statistical, scaled by √(deviance/dof). The fits reach
deviance/dof 0.6–1.0 on the pre-edge sums (10⁵–10⁶ counts). They reach
2–19 on the 10 keV sums, which have up to 2 × 10⁸ counts.

## 1. Si escape fraction (escape peak over its parent)

Two estimates:
- **the fit:** `escape` × Reed, with the escape's position and width tied
  to the parent;
- **a model-free template:** in E0 − 1.74 − 0.55 … E0 − 1.74 + 0.35 keV,
  n(E) = f · n(E + 1.740) + quadratic, the parent taken from the measured
  spectrum itself.

Medians, with the range in brackets. Spectra with Cu under the escape are
left out.

| Beam (keV) | Readout | n | Fit / Reed | Template / Reed | Reed (generator) | Measured fraction (fit) |
|---|---|---|---|---|---|---|
| 6.1 | B | 4 | 1.12 (1.09–1.15) | 1.17 (1.05–1.23) | 0.337 % | 0.38 % |
| 7.2 | B | 4 | 1.08 (1.04–1.10) | 1.19 (1.00–1.38) | 0.235 % | 0.25 % |
| 7.4 | B | 4 | 1.01 (0.96–1.05) | 1.11 (1.05–1.17) | 0.215 % | 0.22 % |
| 8.3 | B | 4 | 1.27 (1.21–1.39) | 1.46 (1.36–1.59) | 0.165 % | 0.21 % |
| 9.2 | B | 4 | 1.44 (1.38–1.55) | 1.55 (1.42–1.64) | 0.128 % | 0.18 % |
| 10.0 | A | 2 | 0.82 (0.77–0.88) | 1.02 (0.98–1.07) | 0.102 % | 0.08–0.10 % |

- **Is the generator right?** Within about 10 % at 6–7.4 keV.
- **Above 8 keV, on readout B**, Reed's fraction is too small:
  - by 27–44 % (fit) or 46–55 % (template);
  - the measured fraction falls more slowly with energy than Reed's
    (×2.1 from 6.1 to 9.2 keV, against ×2.6).
- **At 10 keV, on readout A**, it is right to about 20 %.
- **For study B's case (10 keV, an elastic escape at 8.26 keV):** Reed's
  0.10 % stands. On readout B it may be 1.5 × that, but that cannot be
  measured at 10 keV here, because of Cu.
- **Robustness:** the escape hardly moves when the O 1s wing is pinned at 0
  or 1 (`profile`, section 2).

## 2. The O 1s Compton wing

**What was fitted.** `core` is the wing's size against water's
impulse-approximation wing, with the generator's hydrogenic shape (1 is
the generator). Its trade-off with the detector tail was tested by
refitting with `core` fixed:
- `profile_ddev_core1`: the deviance rise at `core` = 1;
- `profile_ddev_core0`: the deviance rise at `core` = 0.

Both are divided by the fit's deviance/dof, with the tail and every other
term free.

| Beam (keV) | Readout | n | `core` fitted | Rise at core = 1 | Rise at core = 0 | Low tail (fraction, decay) | High tail |
|---|---|---|---|---|---|---|---|
| 10.0 | A | 7 | 0.84 (0.78–0.87) | 55 (38–70) | 228 (144–438) | 2.0 %, 0.64 keV | 0–1.4 % |
| 10.0 | B | 3 | 0.37 (0.32–0.70) | 543 (508–608) | 155 (121–309) | 3–12 %, 0.33–0.40 keV | 7–10 % |
| 9.2 | B | 4 | 0.14 (0.01–0.21) | 182 (96–238) | 12 (0–17) | 6.8 %, 0.33 keV | 1.8 % |
| 8.3 | B | 4 | 0.18 (0.10–0.19) | 126 (99–172) | 14 (4–21) | 5.6 %, 0.31 keV | 0.9 % |
| 7.4 | B | 4 | 0.31 (0.28–0.35) | 1253 (834–1336) | 178 (120–216) | 5.2 %, 0.42 keV | 6.7 % |
| 7.2 | B | 4 | 0.15 (0.01–0.36) | 559 (229–888) | 45 (0–149) | 4.4 %, 0.48 keV | 4.3 % |
| 6.1 | B | 4 | 0.25 (0.15–0.33) | 754 (254–1593) | 69 (59–69) | 3.6 %, 0.46 keV | 2.6 % |

**Is the generator right?**

- **Readout A, 10 keV.** The generator's wing is too large by 15–20 %. The
  data reject both 1 and 0 decisively, and readout A has a small tail
  (2 %).
  - B7 of study B has a wing of ½ or 1. The measured 0.8 lies between them.
  - So the 10 keV Zn case stays a failure for every fit, as the owner
    concluded on 2026-11-24.
- **Readout B.** The data reject a water-sized wing everywhere. What they
  measure is wing + tail, and they cannot split the two well: at 7.2–9.2 keV
  a zero wing is nearly as good.
  - The hydrogenic O 1s shape is itself from memory (study B, §2), so
    "`core`" means the amplitude of that shape.

**Asymmetry of the detected Compton peak.** The ratio of its half-widths,
low over high, is 1.01–1.05 on readout A at 10 keV and 1.04–1.21 on readout
B. The shell model gives the same ratio with or without the O 1s part, to
0.01. So the asymmetry does not measure the wing; the band below does.

## 3. What lies under a line: real against the generator

The band runs from E0 − 1.55 keV to the Compton peak − 0.35 keV (8.45–9.46 keV
at 10 keV, where Zn Kα lies). The counts in it, after the fitted lines and
the flat background, are taken per parent (elastic + Compton) photon per
keV. They are compared with the generator's hard case, which has the same
photons and angle but the generator's detector and Compton
(`GENERATOR_HARD`).

| Beam (keV) | Readout | Real / generator |
|---|---|---|
| 10.0 | A | **1.04** (1.03–1.23) |
| 10.0 | B | 1.55 (1.54–1.74) |
| 9.2 | B | 2.82 (2.49–3.03) |
| 8.3 | B | 2.85 (2.55–3.11) |
| 7.4 | B | 2.16 (1.91–2.51) |
| 7.2 | B | 2.09 (1.90–2.57) |
| 6.1 | B | 2.89 (2.57–3.18) |

**For F90:**

- **The window sum.** The real scatter under a line is at least the
  generator's. So study B's verdict on the window sum, that it fails
  whenever scatter lies under its box, holds on real data. It holds more
  strongly on readout B.
- **The gauntlet's two axes are not the only ones.** On readout B what
  lies under the line is mostly the detector's own tails. A broad low tail
  and a high-energy tail are a third axis that B7 does not sweep.
- **Readout A at 10 keV** is the generator's hard case to within 5 % (one
  run 23 %). Its wing is 0.8 rather than 1, and its tail is broader and
  smaller.

## 4. Resolution and the Compton peak

| Beam (keV) | Readout | Elastic FWHM, measured (keV) | Generator (keV) | Compton FWHM, measured / generator (keV) | Momentum widths × water's | 2θ (°) | Compton / Rayleigh photons |
|---|---|---|---|---|---|---|---|
| 10.0 | A | 0.206 (0.179–0.280) | 0.194 | 0.282 / 0.276 | 0.97 (0.95–1.04) | 91.2 (90.4–91.9) | 2.0 (1.9–2.2) |
| 10.0 | B | 0.190 (0.190–0.227) | 0.194 | 0.290 / 0.276 | 1.16 (1.15–1.51) | 91.1 (88.8–91.2) | 2.6 (2.5–3.3) |
| 9.2 | B | 0.179 (0.176–0.182) | 0.189 | 0.267 / 0.239 | 1.65 (1.58–1.69) | 74 (70–76) | 0.73 (0.61–0.93) |
| 8.3 | B | 0.170 (0.167–0.173) | 0.183 | 0.238 / 0.226 | 1.44 (1.30–1.59) | 77 (73–81) | 0.69 (0.58–0.80) |
| 7.4 | B | 0.166 (0.163–0.173) | 0.178 | 0.239 / 0.226 | 1.43 (1.30–1.50) | 92 (88–93) | 1.8 (1.6–1.9) |
| 7.2 | B | 0.161 (0.157–0.166) | 0.176 | 0.221 / 0.217 | 1.40 (1.24–1.45) | 87 (86–92) | 1.6 (1.0–1.9) |
| 6.1 | B | 0.154 (0.148–0.190) | 0.169 | 0.202 / 0.204 | 1.29 (1.27–1.37) | 94 (85–98) | 1.3 (1.0–1.7) |

- **Resolution.** The generator's default (noise 0.12 keV, Fano 0.115) is
  within −9 … +15 % of the measured FWHM, apart from one readout A run at
  0.28 keV (+45 %). P2 ("width from the detector") calibrates the noise on
  the elastic line, so the default matters only for synthetic data.
- **Compton.** The free-electron Compton formula holds at the fitted angle,
  with the impulse-approximation shift built in:
  - the angle is about 90° on readout A, consistent across 9 runs;
  - on readout B the angle spreads over 70–98° across elements;
  - the momentum widths are water's to 5 % on readout A. On readout B they
    are 1.15–1.7 × water's, which folds in the spread of angles over one
    element.
- **Compton / Rayleigh.** It is 2.0 at 90° on readout A, against the
  generator's default of 1 (a free parameter of the gauntlet).

## What the generator should change

These are recommendations only. Nothing was changed here, because the
owner has paused synthetic MCA work (physics_notes, 2026-11-24).

1. An **O 1s wing of 0.8** on a readout like A, and a sweep of 0–0.4 for one
   like B.
2. A **high-energy tail** term (0–10 %, 0.2–0.3 keV decay).
3. A **broader low tail**: 2–12 %, with a 0.3–0.65 keV decay in place of
   0.15 keV.
4. **Reed's escape × 1.0** below 8 keV and × 1.3–1.5 at 8–9 keV
   (readout B).
5. **Compton/Rayleigh ≈ 2** at 90°.

## Held back for privacy

- All spectra apart from the four public examples. The examples are 10 keV
  sums with only traces of Cu and Zn (`tests/reference/mca_scatter/`).
- Their sources, times, Qz ranges and scan numbers. They are in a private
  key under `sample_data/private/mca_scatter/`.
- Beam energies are given to 0.1 keV. Pre-edge spectra sit just below the
  edges the samples were studied at, so even rounded energies hint at the
  elements studied. **Question for the owner:** may the beam energies stay
  in the public table, and may the pre-edge spectra (6.1–9.2 keV) be
  published as examples like the 10 keV ones?

## Figures and files

| File | What it shows |
|---|---|
| `S1_examples.png` | the four public 10 keV examples, each with the data, the fit, the generator's hard case (same photons and angle), the fit without the O 1s wing, the band (shaded), residuals and the fitted numbers |
| `S2_vs_energy.png` | escape / Reed, band ratio, resolution, O 1s wing, tails and Compton / Rayleigh against beam energy, for both readouts; the spectra not shown are listed with their reasons |
| `scatter_fits.csv` | every fitted number of the 38 spectra (anonymised), with errors, flags and the profile's deviance rises |
| `S1_example_fits.csv` | the refit of the public examples (reproducible here) |
| `numbers.json` | medians and ranges per energy and readout (the tables above) |
