# The scattered beam in real MCA spectra (DATA_NEEDS rows 2 and 3, F90)

The owner's non-cloud agent, 2026-11-24, to the specification of main man and tools man (relayed by
the data-analysis coordinator).

**Measured on real spectra** from the owner's private beamline data. The private data hold no
pure-water blank. The blanks here are spectra with no fluorescence line near the scatter (see
"Which spectra").

The aim is to check the synthetic generator (`tests/synthetic/mca.py`) that study B
(`docs/studies/mca_fit/summary.md`) rests on. Its two uncertain axes are the O 1s Compton wing and
the Si escape fraction (B7).

Every number below is a derived number, except for the 13 scrubbed blanks in
`tests/reference/mca_scatter/`, which the owner allowed on 2026-11-24 ("Yes, commit them"; see
"Committed blanks" at the end).

**Regenerate** the figures from the public tables (a few seconds):

    python tests/tools/mca_scatter.py --out docs/studies/mca_scatter

Tools menu: Fluorescence (MCA), "Scatter in real MCA spectra against the generator".

The tables were made from the private spectra by the same module's model:
- `scatter_fits.csv`: one row per spectrum;
- `quantities.csv`: long form, with columns energy_kev, example, quantity, value, error, method,
  n_spectra and evidence (measured, read or computed; AGENTS rule 6).

## The generator against the real spectra

Each row compares one generator setting (`Detector` / `Beam` in `tests/synthetic/mca.py`, study B's
hard case) with what the spectra show. Values are medians, with the range over examples in
brackets.

- **A:** the single-element readout: 10 keV, 7 spectra from 4 runs.
- **B:** one element of the seven-element readout: 6.1–9.2 keV (20 pre-edge sums from 3 runs) and
  10 keV (3 spectra from 2 runs).

**Evidence:**
- **measured:** fitted to the spectra;
- **read:** taken from the file header.

**Detector**

| Generator setting | Default | Measured, readout A (10 keV) | Measured, readout B | Evidence |
|---|---|---|---|---|
| `Detector.noise` (keV FWHM), with Fano fixed 0.115 | 0.12 | 0.09–0.23 (fit) | 0.09–0.17 | measured |
| Fano factor (`Detector.fano`), from the Ar Kα and elastic widths | 0.115 | 0.137 (0.134–0.139), n = 2 | 0.107 (0.092–0.127), n = 9; two at 0.18–0.21 | measured |
| Noise from the same two widths (keV) | 0.12 | 0.065 (0.061–0.069) | 0.105 (0.080–0.114) | measured |
| Elastic FWHM at 10 keV (keV) | 0.194 | 0.206 (0.179–0.280) | 0.190 (0.190–0.227) | measured |
| Elastic FWHM at 6.1 / 7.2 / 7.4 / 8.3 / 9.2 keV (keV) | 0.169 / 0.176 / 0.178 / 0.183 / 0.189 | — | 0.154 / 0.161 / 0.166 / 0.170 / 0.179 | measured |
| `Detector.tail` (fraction) | 0.01 | 0.020 (0.018–0.022) | 0.028–0.116 | measured |
| `Detector.tail_slope` (keV) | 0.15 | 0.64 (0.50–0.68) | 0.30–0.69 | measured |
| `Detector.shelf` (fraction) | 0.002 | 0.000 | 0–0.034 | measured |
| High-energy tail (fraction, decay) | none | 0–1.4 % | 0.7–11 %, 0.13–0.26 keV | measured |
| `Detector.escape` (× Reed), 6.1–7.4 keV | 1 | — | 1.01–1.12 (fit), 1.11–1.19 (template) | measured |
| `Detector.escape` (× Reed), 8.3–9.2 keV | 1 | — | 1.27–1.44 (fit), 1.46–1.55 (template) | measured |
| `Detector.escape` (× Reed), 10 keV | 1 | 0.82 (fit), 1.02 (template), n = 2 | hidden under Cu Kα | measured |

**Beam and Compton**

| Generator setting | Default | Measured, readout A (10 keV) | Measured, readout B | Evidence |
|---|---|---|---|---|
| `Beam.angle` 2θ (°): shells fit | 90 | 91.2 (90.4–91.9) | 85–98 at 6.1–7.4 keV; 70–81 at 8.3–9.2 keV | measured |
| `Beam.angle` 2θ (°): `compton_energy` at the detected peak | 90 | 91.3 (91.0–93.1) | 76–113 | measured |
| `Beam.compton_ratio`, Compton / elastic photons | 1 (free) | 2.0 (1.9–2.2) | 0.58–3.3 | measured |
| `Beam.doppler_scale` (momentum widths × water's) | 1 | 0.97 (0.95–1.03) | 1.15–1.69 | measured |
| Compton FWHM as detected (keV) | 0.276 at 10 keV | 0.282 (0.26–0.35) | 0.19–0.34 (generator 0.20–0.28) | measured |
| Compton asymmetry, HWHM below / above | 1.03 (shells) | 1.01–1.05 | 1.04–1.21 | measured |
| `Beam.core_scale`, the O 1s wing (shells fit) | 1 | 0.84 (0.78–0.87) | 0.0–0.37 (one spectrum 0.70) | measured |
| O 1s wing window, counts in E_C − 2 … E_C − 0.5 keV / Compton photons | 0.025 (A), 0.013–0.025 (B) | 0.029 (0.0285–0.030) | 0.028–0.041 | measured |

**Counting**

| Generator setting | Default | Measured, readout A (10 keV) | Measured, readout B | Evidence |
|---|---|---|---|---|
| Real time per spectrum (s) | 10 | 15 (15–60) | 2 (pre-edge points); 15–100 at 10 keV | read |
| Dead-time fraction, 1 − live/real | 0 | 0.08 (0.04–0.20) | not recorded (the file has real = live) | read |

**What the table says:**

- **Readout A at 10 keV is close to the generator.** Its O 1s wing is 0.84 × water's. Its low tail
  is broader (0.6 keV) and larger (2 %) than the generator's. Its Fano factor is higher, and its
  noise lower.
- **Readout B is far from it.** Most of what sits under a line comes from its own tails, which the
  generator lacks or under-sizes.
- **The Fano factor from two widths** assumes the noise is the same at the Ar Kα line and at the
  elastic line. The elastic line is counted at a much higher rate, so this is an upper bound when
  pile-up broadens the elastic.

## 1. Scatter under the line boxes (tools man's item 1; B_box of `docs/reports/mca_fit_demo.md` §4.2)

**Method:**
- The box counts are divided by the elastic photopeak counts of the same spectrum.
- Only spectra with a good fit are used, and boxes at or above the elastic line are skipped.
- Inside the fitted region the fitted trace lines are taken off (`quantities.csv`: `box_Zn_*`,
  `box_Fe_*`, and `elastic_photopeak_counts` alongside).
- Outside the fitted region (the Fe box at 9.2 and 10 keV) all counts are kept, any trace Fe
  included.

**Generator** means its hard case with the same photons, angle and ratio.

**Zn Kα box, 8.26–9.00 keV.** Only the 10 keV beam has it below the elastic.

| Beam (keV) | Readout | n | Box / elastic: real | Generator | Real / generator | Elastic photopeak counts |
|---|---|---|---|---|---|---|
| 10.0 | A | 7 | 0.020 (0.018–0.025) | 0.0136 | 1.5 | 1.5e6–1.2e7 |
| 10.0 | B | 3 | 0.062 (0.061–0.074) | 0.0205 | 3.0 | 2e6–5e7 |

Study B's hard case puts B_box at about 8 × the line for 1e3 line photons on 1e6 elastic: 0.008 of
the elastic. The real box holds 2.5 × that on readout A and 7.7 × on readout B. Part of the
difference is the real Compton/Rayleigh ratio of 2, against the hard case's 1.

**Fe Kα box, 6.24–6.56 keV**

| Beam (keV) | Readout | n | Box / elastic: real | Generator | How |
|---|---|---|---|---|---|
| 7.2 | B | 4 | 0.021 (0.015–0.042) | 0.013 | lines taken off |
| 7.4 | B | 4 | 0.019 (0.016–0.024) | 0.005 | lines taken off |
| 8.3 | B | 4 | 0.0054 (0.0052–0.0058) | 0.0021 | lines taken off |
| 9.2 | B | 4 | 0.0031 (0.0028–0.0034) | — | all counts (outside the fit) |
| 10.0 | A | 7 | 0.0018 (0.0004–0.011) | — | all counts (outside the fit) |
| 10.0 | B | 3 | 0.016 (0.007–0.017) | — | all counts (outside the fit) |

At 6.1 keV the boxes are above the elastic, so it is skipped. Beside the boxes, `quantities.csv`
gives the counts per keV per elastic photon in ±2 FWHM windows at E0 − 0.6, 1.0, 1.37, 1.74 and
2.0 keV, for the generator and for the clean and trace spectra (`window_counts_per_keV_*`): the
window-sum view.

## 2. P1 on real data (tools man's item 2)

**The series.** 19 series of 21 repeated spectra each (fluorescence burns, `ascan ih`) at a fixed
position, all from one run on readout A with a 10 keV beam. The line is near 8 keV. It sits on the
Compton escape and the elastic escape peaks, the hard real case.

**The fits.** Each spectrum was fitted with `peaks.fit_series` (Gaussian on a quadratic, box
±2 FWHM, the reader's defaults), once with `weights='data'` and once with `weights='poisson'`. The
truth is the fit of the summed spectrum divided by N. Rows `p1_*` in `quantities.csv`; figure S3.

| Line counts per spectrum | Series | Data weights, bias | P1 (Poisson), bias | Study B's law −19/N |
|---|---|---|---|---|
| 25–50 | 9 | −28.0 % ± 1.4 % (weighted mean; each −23 to −32 %) | +3.5 % ± 1.5 % | −38 to −76 % |
| 190–215 | 2 | −27 % ± 10 %, −28 % ± 12 % | +0.4 % ± 12 %, −0.8 % ± 15 % | −9 % |
| 1470 | 1 | −4.0 % ± 1.7 % | 0.0 % ± 1.4 % | −1.3 % |
| 2500–3900 | 7 | −0.5 to −1.5 % (± 0.6–17 %) | within ± 0.1 % | −0.5 to −0.8 % |

**What it shows:**

- **P1 removes the data-weight bias on real spectra.** It is unbiased within its errors from about
  200 counts up. At 25–50 counts it reads +3.5 % ± 1.5 % (2.3 σ).
- **The data-weight bias is real**, but it is not −19/N here:
  - it stays near −27 % up to about 200 counts, so it is smaller than −19/N below about 70 counts
    and larger above;
  - it is about −1 % by 3000 counts.
- **Why the shape differs.** The background under this box (escape peaks and Compton tail) is far
  larger than study B's 1 count per channel. The −19/N law was fitted to that clean case.
- **For F90:** the default (P1, 2026-11-24) is confirmed on real data. Study B's size of the bias
  does not carry over to a box on the scatter.

## 3. Si escape fraction (escape peak over its parent)

**Two estimates:**
- **the fit:** `escape` × Reed, with the escape's position and width tied to the parent;
- **a model-free template:** in E0 − 1.74 − 0.55 … E0 − 1.74 + 0.35 keV, n(E) = f · n(E + 1.740) +
  quadratic, with the parent taken from the measured spectrum itself.

Spectra with Cu Kα under the Compton escape (8.04 against 8.07 keV, at 10 keV) are left out.

| Beam (keV) | Readout | n | Fit / Reed | Template / Reed | Reed | Measured fraction (fit) |
|---|---|---|---|---|---|---|
| 6.1 | B | 4 | 1.12 (1.09–1.15) | 1.17 (1.05–1.23) | 0.337 % | 0.38 % |
| 7.2 | B | 4 | 1.08 (1.04–1.10) | 1.19 (1.00–1.38) | 0.235 % | 0.25 % |
| 7.4 | B | 4 | 1.01 (0.96–1.05) | 1.11 (1.05–1.17) | 0.215 % | 0.22 % |
| 8.3 | B | 4 | 1.27 (1.21–1.39) | 1.46 (1.36–1.59) | 0.165 % | 0.21 % |
| 9.2 | B | 4 | 1.44 (1.38–1.55) | 1.55 (1.42–1.64) | 0.128 % | 0.18 % |
| 10.0 | A | 2 | 0.82 (0.77–0.88) | 1.02 (0.98–1.07) | 0.102 % | 0.08–0.10 % |

- **The escape hardly moves** when the O 1s wing is pinned at 0 or 1 (section 4).
- **Item 3 (10.05 and 10.52 keV) cannot be answered.** The private data hold no spectrum at 9.9–9.99,
  10.05 or 10.52 keV. Those energies appear in the SPEC files of one run whose `vortex/` folder
  holds only 7 spectra (at about 10 keV and a mislabelled 20 keV).
- **30 keV cannot be answered either.** The 30 keV headers do not match their spectra (no elastic
  line).
- **6.21 and 7.51 keV.** The spectra at exactly these energies sit on the samples' edges and carry
  their lines. The 6.1 and 7.4 keV pre-edge sums are the nearest scatter-only cases.

## 4. O 1s Compton wing, and its trade-off with the detector tail

`core` is the wing's size against water's impulse-approximation wing, with the generator's
hydrogenic shape. Each spectrum was refitted with `core` fixed:
- `profile_ddev_core1`: the deviance rise at `core` = 1;
- `profile_ddev_core0`: the deviance rise at `core` = 0.

Both are divided by the fit's deviance/dof, with the tail and every other term free.

| Beam (keV) | Readout | `core` | Rise at 1 | Rise at 0 |
|---|---|---|---|---|
| 10.0 | A | 0.84 (0.78–0.87) | 55 (38–70) | 228 (144–438) |
| 10.0 | B | 0.37 (0.32–0.70) | 543 (508–608) | 155 (121–309) |
| 9.2 | B | 0.14 (0.01–0.21) | 182 (96–238) | 12 (0–17) |
| 8.3 | B | 0.18 (0.10–0.19) | 126 (99–172) | 14 (4–21) |
| 7.4 | B | 0.31 (0.28–0.35) | 1253 (834–1336) | 178 (120–216) |
| 7.2 | B | 0.15 (0.01–0.36) | 559 (229–888) | 45 (0–149) |
| 6.1 | B | 0.25 (0.15–0.33) | 754 (254–1593) | 69 (59–69) |

- **A water-sized wing is rejected everywhere.**
- **On readout A** the wing is measured at 0.8: zero is rejected too. That lies between B7's ½ and
  1, so the 10 keV Zn case stays out of reach, as the owner concluded on 2026-11-24.
- **On readout B** the wing and the broad tail trade against each other. At 7.2–9.2 keV a zero wing
  is nearly as good.
- **The window measure** (counts in E_C − 2 … E_C − 0.5 keV over the Compton photons, the table
  above) is model-free in the data:
  - readout A: 1.2 × the generator's;
  - readout B: 1.6 × at 10 keV and 2.2–2.4 × at 6–9 keV.

## 5. What lies under a line: the band against the generator

The band runs from E0 − 1.55 keV to the Compton peak − 0.35 keV. The counts in it, after the fitted
lines and the flat background, are taken per parent photon per keV.

| Beam (keV) | Readout | Real / generator |
|---|---|---|
| 10.0 | A | **1.04** (1.03–1.23) |
| 10.0 | B | 1.55 (1.54–1.74) |
| 9.2 | B | 2.82 (2.49–3.03) |
| 8.3 | B | 2.85 (2.55–3.11) |
| 7.4 | B | 2.16 (1.91–2.51) |
| 7.2 | B | 2.09 (1.90–2.57) |
| 6.1 | B | 2.89 (2.57–3.18) |

**The window sum's failure** (study B) holds on real data, more strongly on readout B. B7's two axes
miss a third: the detector's own tails.

## 6. Setup: calibration, angle, counting (per example in `quantities.csv`)

**Calibration (read and measured).**
- **Elastic residual with the file's calibration** (`#@CALIB` a, b, c; c = 0 in every file):
  - readout A: +4 … +51 eV;
  - readout B: +7 … +27 eV.
- **Ar Kα (air, 2.957 keV) residual with the file's calibration:**
  - readout A: +1 … +2 eV;
  - readout B: +3 … +20 eV.
- **Ar Kα with the measured calibration** (gain from the elastic across energies, or elastic +
  Ar Kα; offset refitted per spectrum): −3 … −50 eV.
- **What that means.** Either the beam energy in the header differs from the true one by a few tens
  of eV, or the gain is off by about 0.5 %. These spectra cannot separate the two.
- **Effect on the study:** under 2 eV on the Compton shift, and under 10 eV on the escape position.

**Angle.** The detector's position is not logged. 2θ comes from the Compton shift:
- the shells fit and `compton_energy` at the detected peak agree to 1–2° on readout A;
- they differ by up to 30° on readout B, where the elastic and the Compton line are not resolved
  below 8 keV.

**Counting.**
- **Readout A:** real and live times are in `#@CTIME`. The dead time is 4–20 %.
- **Readout B:** it writes real = live. `#@DCT` has a first field of about 10⁴–4 × 10⁵ (median per spectrum), whose meaning
  is not documented here (`dct_first_field_median`, marked as read).

## 7. Where the spectra are (row 2)

| Kind of scan | `#V` line in the SPEC block | Spectra in the SPEC block | Separate `_mca` file |
|---|---|---|---|
| Energy scan (`escan`, MCAscanpt) | yes, 176 of 180 (a pointer: `#V <datafile>_<scan>_mca`) | no | yes |
| Fluorescence burn (`ascan ih`) | yes, 71 of 72 | no | yes |
| `hklscan` (XFNTR) | yes, 541 of 541 | no | yes |
| `getandsave_mca` | yes, 166 of 166 | no | yes |
| other `ascan`, `a2scan` | 47 of 57; 1 of 27 | no | yes |

**The `_mca` file, `vortex/<datafile>_<scan>_mca`:**
- one `#S n mca_save_point Point:p Scan:s Datafile:d` block per point and per detector element;
- in each block `#T`, `#Q` (H K L), `#Energy` (SPEC's `en`; 0 in one run, wrong in the 20 and 30 keV
  headers), `#Monc`, `#@CTIME` (preset, real, live), `#@CALIB` (eV or keV per channel) and `@A`;
- readout B adds `#@CHANNEL k` and `#@DCT`.

1043 files from 12 runs were checked.

## Which spectra

- **The energy scans cross absorption edges** of the samples' elements. Each scan's pre-edge points
  (30–150 eV below the edge) were aligned to their mean beam energy (`rebin_shift`) and summed, per
  element. These give the 6.1, 7.2, 7.4, 8.3 and 9.2 keV cases.
- **At 10 keV, whole scans were summed.** Most carry traces of Cu and Zn below 10⁻³ of the elastic
  photons.
- **Tiers:**
  - **clean:** no line above 10⁻⁴ of the elastic photons in E0 − 2.4 … E0 + 0.6 keV;
  - **trace:** lines below 10⁻³;
  - **line:** stronger lines.
- **38 spectra were fitted** and 30 give good fits. The rest are listed on S2 with their reasons.
- **The model** (the tool's docstring has every term):
  - the generator's physics with every uncertain axis free;
  - a high-energy tail;
  - nuisance K lines;
  - a flat background;
  - Poisson likelihood.
- **Fit quality:** deviance/dof 0.6–1.0 on the pre-edge sums, and 2–19 on the 10 keV sums (up to
  2 × 10⁸ counts).
- **Errors** are statistical, scaled by √(deviance/dof).
- **The model is checked on known truth** (a synthetic spectrum's wing, escape and tails):
  `tests/test_mca_scatter.py`, slow.

## What the generator should change

These are recommendations only. Nothing was changed, because synthetic MCA work is paused.

1. An **O 1s wing of 0.8** on a readout like A, and 0–0.4 swept for one like B.
2. A **high-energy tail** term: 0–10 %, with a 0.15–0.3 keV decay.
3. A **broader low tail**: 2–12 %, with a 0.3–0.65 keV decay in place of 0.15 keV.
4. **Reed's escape × 1.0–1.1** below 8 keV, and × 1.3–1.5 at 8–9 keV (readout B).
5. **Compton/Rayleigh ≈ 2** at 90°.
6. **Fano 0.11–0.14** with noise 0.065–0.11 keV, rather than 0.115 with 0.12.

## Held back for privacy, and questions for the owner

**Held back:**
- every spectrum but the 13 committed blanks;
- all runs, times, Qz values and scan numbers;
- the burn series' element, which is named only as "a line near 8 keV".

The private inventory, the label-to-source key and the scripts are under
`sample_data/private/mca_scatter/` (git-ignored).

**The owner's answers (2026-11-24, asked by the coordinator):** "Yes, commit them" (the blanks
below) and "Keep 0.1 keV" (the beam energies stay public to 0.1 keV, so the tables stay as they are).

## Committed blanks (`tests/reference/mca_scatter/`)

Thirteen scrubbed scatter-only spectra, committed with the owner's yes. Each file is `energy_keV,counts`
over E0 − 2.5 … E0 + 0.7 keV, under a short `#` header: beam energy to 0.1 keV, readout, kind
(one spectrum, or pre-edge points aligned on the elastic line and summed), gain in keV per channel,
and summed real and live time to 3 significant figures (read from the files, not measured). No
channel number, date, scan, Qz or file name. The energy axis is the one the fits used, with its
offset fitted so the elastic line sits at the beam energy. Pre-edge sums were rebinned onto a common
grid, so their counts are rounded and not strictly Poisson.

| Beam | Readout | Examples | Kind |
|---|---|---|---|
| 10.0 keV | A | E10-k, E10-f (clean), E10-j (trace Cu) | one spectrum |
| 10.0 keV | B | E10-d, E10-i (trace Cu and Zn) | one spectrum, one element |
| 9.2 keV | B | E9.2-a … E9.2-d (clean) | pre-edge sum, one element |
| 6.1 keV | B | E6.1-a … E6.1-d (clean) | pre-edge sum, one element |

Their fitted numbers are the rows with the same ids in `scatter_fits.csv` and `quantities.csv`.
`tests/test_mca_scatter.py` loads every file and checks the header and the elastic line's position.
They are the real blanks DATA_NEEDS row 3 asked for, for the gauntlet and for S1:

    python tests/tools/mca_scatter.py --out <folder> --only S1 --fixtures tests/reference/mca_scatter

Refitted from these files alone (S1, about a minute on 8 processes, beam energy taken from the header
to 0.1 keV), they give the study's numbers back. Measured, 2026-11-24:
- escape: Reed × 1.07–1.15 at 6.1 keV, × 1.37–1.53 at 9.2 keV, × 0.70–1.00 at 10 keV;
- O 1s wing scale: 0.10–0.34 at 6.1 and 9.2 keV, 0.81–0.86 on readout A at 10 keV, 0.31–0.67 on readout B.

The pre-edge sums sit just below the edges the samples were studied at, so their rounded beam
energies hint at the elements studied. The owner allowed this ("Keep 0.1 keV").

## Figures and files

| File | What it shows |
|---|---|
| `S2_vs_energy.png` | escape / Reed, band ratio, resolution, O 1s wing, tails and Compton / Rayleigh against beam energy, for both readouts; the spectra not shown are listed with their reasons |
| `S3_p1_real_series.png` | the bias of data weights and of P1 on 19 real series against the line counts, with study B's −19/N |
| `scatter_fits.csv` | every fitted number of the 38 spectra (anonymised), with errors, flags and the profile's deviance rises |
| `quantities.csv` | every quantity per example in long form (calibration, widths, Fano, tails, Compton, escape, wing window, boxes, windows, counting, the P1 series), each marked measured, read or computed |
| `numbers.json` | medians and ranges per energy and readout |

S1 (the example spectra with their fits) is drawn only from a folder of spectra given with
`--fixtures`, for example the committed blanks. It is not committed here.
