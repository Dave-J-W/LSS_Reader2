# XRF shootout: the reader's line intensities against PyMca, PyXRF, Larch and XeRay

2026-11-25, overnight session (local, the owner's PC: 16 cores, 128 GB).
**Everything here is measured on spectra with known truth.** Sections 1–9
use synthetic spectra; their one real-data input is the detector and
scatter measured on the owner's blanks (`docs/studies/mca_scatter`),
which define the "measured" conditions. **Section 10 uses the real
blanks themselves**, with synthetic lines of known photons added.
**Section 11 uses real lines in real scatter** (the private burn series;
summary values only). No default of the reader was changed.

- Questions and short answers: `QUESTIONS.md`
- Survey of other packages: `survey.md`
- How to reproduce: `README.md`
- Every number below comes from `tables.md` (generated, with all
  methods and conditions), from `wins.csv`, for section 10 from
  `blanks_tables.md` and for section 11 from `real_tables.md`

## The question

When the reader measures a fluorescence line in an MCA spectrum, is it
better than, the same as, or worse than the open-source XRF packages?

"Better" means the right number of counts, a curve over Qz with the
right shape, and honest error bars.

## The contestants

| Side | Method | What it is |
|---|---|---|
| reader | window | Sum All over the box (line ± 2 FWHM) |
| reader | fit (data) | "Fit lines", Gaussian on a quadratic in the box, data weights (the default before 2026-11-24) |
| reader | **P1 (default)** | the same fit by Poisson likelihood (the default since 2026-11-24) |
| reader | P1+P2+P3 | P1, width fixed at the detector's (Fano 0.115), Si escapes stripped (the reader's options) |
| others | XeRay | MATLAB tool of the Lee group (U. Chicago) for XFNTR; ported line for line: Gaussian on a line, unweighted |
| others | PyMca 5.9.7 | whole-spectrum fit: all lines, Rayleigh and Compton peaks, escapes, SNIP background; five settings |
| others | PyXRF (scikit-beam 0.0.27) | PyXRF's engine: nonlinear fit of the summed series, then NNLS per spectrum |
| others | Larch 2026.3.1 | Hypermet lines and scatter; "Larch" fits the summed series and steps each spectrum linearly; "Larch each" fits each spectrum alone |

**Fairness rules** (the points a skeptic checks first):

- Every method gets the same knowledge: the nominal calibration, the
  detector's noise and Fano factor, the beam energy, and the elements
  present.
- **Each method is calibrated on its own clean twin.** That is the same
  element, detector and beam, with no scatter and 1e5 photons. This
  removes conventions (Kα alone or the whole family, tails in or out,
  the package's own line ratios), so only what the scatter, the
  neighbours, the counts and the errors do is left. Uncalibrated
  numbers are in `run*/scores.csv` (`raw_ratio`).
- **PyMca gets five background settings**: SNIP 30, 60 or 100 channels,
  Hypermet tails, or a polynomial continuum. "Best PyMca" is whichever
  came closest to the truth in each condition. No user can pick this way,
  because it needs the truth, so it is generous to PyMca on purpose.
- Larch's per-spectrum fit is unstable: on one smooth spectrum it lands
  at 1.1× or at 0.1–0.2× the truth from draw to draw. It was given the
  true calibration (fixed) to help it.
- Each condition is 100 series of 10 spectra (1000 spectra). Each XFNTR
  curve is 40 replicate curves of 23 points.

## The answers

### 1. Who gets the right number of counts? (X1, X5)

"Accurate" here means:
- |bias| within 2 %;
- at most 5 % of fits failed;
- the bias itself known to 1 %.

| Method | Accurate in (of 43 conditions) | Never fails in |
|---|---|---|
| reader: window | 2 | 43 |
| reader: fit (data) | 9 | 23 |
| **reader: P1 (default)** | **11** | 23 |
| **reader: P1+P2+P3** | **13** | 24 |
| XeRay | 11 | 43 |
| PyMca, default (SNIP 30) | 7 | 43 |
| PyMca, best single setting | 7 | 43 |
| PyMca, best of 5 per condition (oracle) | 10 | 43 |
| PyXRF | 4 | 43 |
| Larch (series) | 4 | 43 |
| Larch (each) | 5 | 43 |

**What separates them is what each does when the line sits on the scatter.**

- **The reader's fits refuse rather than guess.** In 19 of the 43
  conditions, P1's own checks reject most spectra (54–100 %). These are
  the hard Zn case at 10 keV and its variants, Br at 13.6 keV, and Sr at
  16.2 keV. Where P1+P2+P3 does answer in those conditions, it is off by
  −22 to +5 % (mostly −5 to −14 %).
- **The whole-spectrum packages always answer, and are mostly wrong
  there.** In the same 19 conditions:
  - PyMca is off by −54 to +21 % (mostly about −20 %);
  - PyXRF by −85 to −100 % (it finds almost no Zn);
  - Larch by −4 to +308 %;
  - XeRay by +76 to +1475 %.
- **No method is within 2 % for Zn Kα under a 10 keV beam, including
  on the measured detector.** The reader's refusal is the honest
  answer. A −20 % number delivered without complaint is the dangerous
  one.

### 2. Who keeps the shape of an XFNTR curve? (X3)

This is the measurement the reader exists for. A constant scale error
cancels; an error that changes along the curve does not. Each cell is
the worst point's deviation from the true shape after one free scale,
over points with at least 100 true counts.

| Curve | P1 | P1+P2+P3 | best PyMca (oracle) | Larch | XeRay | PyXRF |
|---|---|---|---|---|---|---|
| smooth, Zn 2e4 at Qc | **0.5** | 0.6 | 2.2 | 1.2 | 2.4 | 6.1 |
| smooth, weak (2e3 at Qc) | **4.9** | **4.9** | 9.1 | 5.9 | 21.1 | 79.6 |
| hard, 10 keV | 5.1 | **1.7** | 12.3 | 20.4 | 26.5 | 40.8 |
| hard, 12 keV | 0.5 | 0.7 | 6.1 | 1.5 | **0.4** | 5.6 |
| hard, with Cu | 4.4 | **2.6** | 12.1 | 20.2 | 26.6 | 43.5 |
| Br, 14 keV | **0.6** | 1.8 | 3.8 | 6.0 | 8.1 | 6.6 |
| Er L, 10 keV | 1.7 | 2.0 | 6.5 | 2.7 | **1.0** | 6.3 |
| measured detector, 10 keV | **5.1** | 5.5 | 11.5 | 53.7 | 747 | 62.0 |

- **The reader is best in 6 of 8 curves.** It ties XeRay at 12 keV,
  and XeRay is better on the Er L curve (1.0 against 1.7 %).
- **Every PyMca setting bends the curve at the critical angle.** Above
  Qc the bulk scatter grows, and PyMca's bias follows the
  scatter-to-line ratio. That gives a 6–12 % step in the curve (X3,
  orange) even where its single-spectrum bias looked small. The
  reader's box fit has no such step, because its background is local.

### 3. Are the error bars honest? (X4)

The pull is (estimate − truth) / error bar. Its standard deviation
should be 1. Medians over the conditions where fits do not fail:

| Method | Median pull SD | Range | Reads as |
|---|---|---|---|
| P1+P2+P3 | 1.03 | 0.98–1.22 | honest |
| P1 (default) | 1.07 | 0.99–1.33 (4.8 for Ga beside Zn, where the fit takes the wrong line) | honest |
| fit (data) | 1.13 | 1.01–1.3 (4.9 for Ga beside Zn) | slightly small |
| PyMca | 1.58 | 1.0–2.05 | 1.3–2× too small under scatter |
| XeRay | 1.92 | 1.0–11.7 | √(counts in the box) leaves out the background's uncertainty |
| Larch (each) | 0.60 | 0.2–1.0 | too large |
| window | 0.59 | | too large, and the value is wrong anyway |
| PyXRF, Larch (series) | — | | no error bars |

**Only the reader's fits give error bars a downstream χ² fit can trust.**

### 4. Low counts (the high-Qz end of a curve; X2)

This is a clean line with no scatter, so only the weighting matters.

| Line photons | fit (data) | P1 | P1+P2+P3 | XeRay | best PyMca | PyXRF | Larch |
|---|---|---|---|---|---|---|---|
| 30 | −22 % | +23 % | **+2.1 %** | +35 % | +7.0 % | +29 % | +48 % |
| 60 | −31 % | +2.7 % | **−0.6 %** | +2.3 % | −3.1 % | +1.0 % | +12 % |
| 100 | −23 % | +2.1 % | **−0.6 %** | +0.2 % | −1.6 % | −5.4 % | −1.1 % |
| 1000 | −1.3 % | +0.2 % | −0.3 % | +0.1 % | +0.2 % | −3.1 % | −4.9 % |

- **Poisson likelihood is what makes the reader unbiased at low counts.**
  The old data weights read −23 % at 100 photons. PyMca's default (also
  data weights) reads +16 % at 60 photons.
- **The others are 10–25 % more precise on an isolated line** (12
  conditions, "others better (precision)" in X5). For example, the RMS
  error at 100 photons is 15.8 % for Larch against 19.4 % for P1+P2+P3,
  and 3.6 % for PyMca SNIP 60 against 4.2 % at 1000 photons. There are
  two reasons:
  - they also use the Kβ photons (+12 %);
  - they spend fewer parameters on the background: XeRay a straight line,
    PyMca a SNIP filter, the reader a quadratic.

  This is the one place where the reader is plainly worse, and it costs
  precision, not accuracy.

### 5. Overlapping lines

| Case | Reader's best | Others' best | Verdict |
|---|---|---|---|
| Ga 1e2 beside Zn 1e3 at 12 keV (Zn Kβ 9.57, Ga Kα 9.25 keV) | P1+P2+P3 +2.5 %, 45 % fail; P1 +203 % | **PyMca −1.1 %** | others better |
| Co 1e2 beside Fe 1e3 (Fe Kβ 7.06, Co Kα 6.93 keV) | P1+P2+P3 +53 % | **PyMca +2.8 %** | others nearly; the box fit fails |
| Fe with Mn (Mn Kβ under Fe Kα) | P1+P2+P3 +6.9 % | Larch −4.1 % | neither |
| As Kα under Pb Lα at 14 keV (0.01 keV apart) | +83 % | PyMca SNIP60 −11 % (RMS 111 %) | neither |
| Zn with Cu, under the 10 keV scatter | fails (78–100 %) | PyMca −22 to −27 % | neither |

**Where a neighbouring line sits in or beside the box, a whole-spectrum
fit is right and the reader's box fit is wrong.** The reader has no
way to place a known neighbour in the box. Study B's gauntlet had one
(`fit_known`, a comparator), but it is not a reader option.

### 6. Calibration and detector errors

All of these were run on the 10 keV hard case, where everyone fails, so
they do not separate the methods; that is a limit of the design. One
detector result does stand:

- **P2's width is only as good as its Fano factor.** On the measured
  detector (Fano 0.137, not the 0.115 P2 assumes) at 12 keV:
  - P1+P2+P3: −5.5 %;
  - P1 alone: −0.2 %.

  The fixed width is about 6 % too narrow.

### 7. Does the verdict depend on the synthetic Compton model?

No. The hard case was run with water's Compton from tabulated
Hartree–Fock profiles (Biggs, via xraylib; the default here) and with
study B's shell model:

| Compton model | P1+P2+P3 | best PyMca |
|---|---|---|
| tabulated Hartree–Fock | −7.6 %, 70 % fail | −20.6 % |
| study B's shell model | −7.9 %, 65 % fail | −19.8 % |

The two profiles agree within 1 % in the Zn box. The total Compton
scatter matches xraylib's incoherent scattering function within 1.2 %
(`tests/test_mca_more.py`). Halving the O 1s wing still leaves the
reader failing 66 % of fits.

### 8. The beam-energy route, confirmed on the measured detector

| Beam | P1 | P1+P2+P3 | best PyMca | Larch | XeRay |
|---|---|---|---|---|---|
| hard, 10 keV | fails 80 % | −7.6 %, fails 70 % | −20.6 % | +34 % | +529 % |
| hard, 11 keV | −4.2 % | **−0.6 %** | +1.3 % (SNIP 60 only; default −17 %) | −33 % | −28 % |
| hard, 12 keV | **+0.0 %** | −0.8 % | +1.3 % (SNIP 100; default −8.8 %) | −11 % | −0.7 % |
| measured detector, 12 keV | **−0.2 %** | −5.5 % | +10 % (default −16 %) | **−1.2 %** | −2.7 % |

**Moving the beam to 12 keV makes the reader's default accurate. PyMca
is accurate there only with the right background setting, which nobody
can choose without the truth.**

### 9. Speed (X8; one CPU, median per spectrum)

| Method | Seconds per spectrum |
|---|---|
| window | 0.0001 |
| fit (data) | 0.002 |
| P1 | 0.004 |
| P1+P2+P3 | 0.008 |
| XeRay port | 0.013 |
| PyMca | 0.025 |
| PyMca tails | 0.05 |
| Larch (series) | 0.14 |
| PyXRF | 0.18 (up to 18) |
| Larch (each) | 1.2 |

### 10. Real scatter, synthetic lines: the owner's blanks (X9–X11)

The owner asked (2026-11-25) whether the methods had been tested on real
blanks, which capture the beam's scatter exactly, combined with
synthetic fluorescence lines. Sections 1–9 had not: their scatter is the
generator's, with settings fitted to the blanks. This section is that
test (`tests/tools/xrf_blanks.py`; tables in `blanks_tables.md`).

**How.** These are the 10 committed real blanks with no line in their
region (`tests/reference/mca_scatter/`):
- E10-k and E10-f: 10 keV, readout A;
- E9.2-a…d and E6.1-a…d: 9.2 and 6.1 keV, readout B, pre-edge sums.

E10-d, E10-i and E10-j hold traces of Cu and Zn, so they were not used.
Each spectrum is built in three steps:
- **Thin the blank.** Each count is kept with probability p (p ≤ 0.23),
  so that 1000 or 3000 counts remain in the line's box. That is a fresh
  Poisson spectrum with the real shape.
- **Add a synthetic line family** (xraylib's lines and ratios) with
  0.1, 0.3, 1 or 3 times those counts in photons.
- **Shape the line** with the detector **measured on that blank**:
  its width and Fano factor, low tail, shelf and escape.

Everything under the line is therefore real: the Compton profile, the
tails, and the **Si escape peak of the scatter itself**, 1.74 keV below
the beam (X9).

The lines tested, 192 conditions × 500 spectra in all, plus the bare
blanks:
- 10 keV: Zn K and Cu K;
- 9.2 keV: Cu K and Ni K;
- 6.1 keV: Cr K, Ti K and La L.

The single-option variants P1+P2 and P1+P3 ran on the same spectra (the
same seeds).

**Accurate conditions of 192** (|bias| ≤ 2 %, ≤ 5 % failed, known to 1 %;
X11):

| Method | Accurate | Median \|bias\|, line ≥ background | Pull SD |
|---|---|---|---|
| P1+P3 (escape strip, free width) | **49** | 2.2 % | 1.08 |
| P1+P2+P3 | 47 | 2.3 % | 1.01 |
| fit (data) | 33 | 5.0 % | 1.11 |
| P1 (default) | 31 | 4.9 % | 1.06 |
| P1+P2 | 25 | 4.0 % | 0.98 |
| PyMca, best single setting (tails) | 20 | 6.4 % | 1.79 |
| PyMca (default) | 17 | 7.0 % | 1.56 |
| PyXRF | 15 | 10.9 % | none |
| XeRay | 6 | 9.9 % | 1.13 |
| Larch | 1 | 46 % | none |
| window | 0 | +110 % and more | — |
| *PyMca, best of 5 per condition, picked with the truth* | *56* | *1.8 %* | *1.87* |

**What the real scatter shows that the synthetic spectra did not:**

- **The escape peak of the scatter fools a fit that ignores it.** It sits
  at 7.46 keV under a 9.2 keV beam, on Ni Kα (7.47), and at 4.36 keV
  under 6.1 keV, beside Ti Kα (4.51) and La Lα (4.65).
  - P1 alone reads Ni at +22 % when line = background, and +6 % at
    three times.
  - On the bare blank it reports a Ni line of 26–35 photons per 100
    background counts, and its fit does not fail.
  - With the strip and the fixed width (P1+P2+P3), Ni is within 0.6 % at
    every strength from 0.3 up, and the false line falls to 3–4 per 100.
    With the strip alone (P1+P3), Ni reads +2.5 % at line = background
    and +16 % at 0.3.
- **Zn under a 10 keV beam is measurable on the real readout A once the
  line is as strong as the background under it.** P1+P3 reads +0.2 %
  (line = background) and −0.2 % (three times). P1+P2+P3 reads −4.4 %
  and −3.7 %, because P2 fixes the width at Fano 0.115 and this
  detector's is 0.137; that is the same −4 to −5 % seen on the
  synthetic measured detector (§8). PyMca's default reads −29 % and
  −5 %. §1's "nobody" holds for weaker lines (0.05 of the box's
  background there): at 0.1 every method is off by more than 2 %.
- **PyMca's error bars are again too small** (pull SD 1.56–1.87). The
  reader's are again honest (0.98–1.08).
- **No method is accurate at line = 0.1 × background.** At 0.3, P1+P2+P3
  is the most accurate (7 conditions), and the fixed width is what helps
  there.

**Where the reader still loses on real scatter:**
- **Ti K at 6.1 keV, line = background:** P1+P3 −12 %, P1+P2+P3 −7 %;
  PyMca's best setting is +2.6 %. P1 alone reads +16 % there, so the
  strip over-corrects next to Ti.
- **La L at 6.1 keV:** P1+P2+P3 +10 % at line = background; PyMca's best
  setting is +3 %. The box holds Lα only; the Lβ lines at 5.0–5.4 keV
  sit outside it and in the scatter.

**The verdict on real scatter.** The reader with the escape strip is the
most accurate method that a user can run without knowing the answer:
49 conditions against 20 for the best fixed PyMca setting. Its error
bars are the only honest ones. PyMca beats it only when its background
setting is chosen per condition with the truth (56).

### 11. Real lines in real scatter: the 19 private burn series (X12)

With the owner's key (2026-11-25), the private MCA bundle was decrypted
into the git-ignored `sample_data/private/`. Its 19 burn series are real
lines on real scatter:
- readout A, a 10 keV beam;
- a line near 8 keV;
- 21 spectra of 15 s each at one spot;
- 27 to 4500 line counts per spectrum (median 220).

They have no known truth, so `tests/tools/xrf_real_series.py` uses three
checks that need none. Only summary values per series are published
(`real_tables.md`), not spectra or frame-by-frame curves.

- **Resampled twins** carry the known answer. Each twin is 21 Poisson
  draws from the series' own sum ÷ 21, so it has the real line, the real
  scatter and the real counts. The answer is the method's own reading of
  the sum ÷ 21, and the bias against it is what fitting noisy spectra
  costs. (The real counts are Poisson: once a slow drift is removed, the
  line window's frame-to-frame variance is 1.09 × its mean, and
  neighbouring channels are uncorrelated.)
- **Successive differences** of the real estimates test the error bars
  on the data themselves. On the twins this statistic reads the same as
  the true pull, so it is calibrated.
- **Agreement on the sums:** each method's calibrated reading of 21 × the
  counts, against the median of all the methods.

**Bias at the real counts (twins), by line counts per spectrum:**

| Method | 27–58 counts (9 series) | 220–250 (2) | 1700–4500 (8) | Pull SD (twins) |
|---|---|---|---|---|
| P1 (default) | −7 to −25 % | −0.2 to −0.7 % | −0.1 to +0.4 % | 0.99 (4.8 on one) |
| P1+P3 | −6 to −25 % | −0.2 to −0.8 % | 0.0 to +0.4 % | 0.99 |
| **P1+P2+P3** | **−2 to −7.5 %** | −2.0 to −3.7 % | −2.1 to +0.4 % | **1.02** (0.95–1.11) |
| PyMca | −12.5 to +13 % | −22 to −23 % | −2.4 to −6.3 % | 1.03 (0.53–1.63) |
| PyXRF | median −9.6 % over all | | | none |
| Larch | median −28 % over all | | | none |
| fit (data) | median −37 % over all | | | 0.89 |

(`real_tables.md` holds every method and the ranges.)

**What this adds:**
- **At low counts the fixed width (P2) is what keeps the reader
  honest.** It holds the bias to −2 to −7.5 %, where a free width gives
  −6 to −25 %. Its error bars stay honest in every series (0.95–1.11). This
  confirms the synthetic counts result (§4) on real spectra.
- **At high counts every reader fit is within 0.4 % of its own answer,
  except P2-based ones within 2 %.** PyMca reads 2.4–6 % low there and
  22 % low at about 230 counts. Its error bars are 1.5–2 × too large at
  low counts (pull SD 0.53–0.69) and 1.5–1.6 × too small at about 230.
- **The methods disagree by ±11 % on the high-count sums.** The two
  P2-based reader methods read 11 % below the median. This is the one
  real-data warning against P2 as built: **the line near 8 keV is 21 %
  wider than readout A's resolution measured on the blanks** (range
  5–37 % over the series; the Kα doublet adds 1–2 %), and P2 fixes the
  width at 0.93 × that resolution. A fixed width needs the measured
  width of the line, not the detector's nominal resolution.
- **The self-consistency check the scatter study used** (singles against
  their own sum) is blind to a bias that also affects the sum. On these
  series it reads 0.0 % for P1 (median), while the twins show −7 to −25 %
  at the lowest counts. The twins are the better test.
- PyMca's polynomial continuum fails on these spectra, as it did on the
  synthetic ones.

**There is no absolute truth here.** The twins test each method
against its own answer on the mean spectrum, and the sums test the
methods against each other. A standard of known concentration measured
on the beamline is what would settle which absolute number is right.

## Better, the same or worse? The verdict

1. **Better: the shape of XFNTR curves and the error bars.**
   - Curve shape: best in 6 of 8 curves, tied in one, behind XeRay on Er L.
   - Error bars: honest within 3–7 %, the only ones that are.
   - Low counts: unbiased with P1+P2+P3 down to 30 photons.
2. **The same: an isolated line clear of the scatter.** Everyone who
   gets it right agrees within 1 %.
3. **Worse in two places:**
   - **precision on isolated lines**: 10–25 % larger RMS than the best
     whole-spectrum fit, from not using Kβ and from a quadratic
     background;
   - **overlapping lines**: Ga beside Zn, Co beside Fe.
4. **Nobody can measure a weak Zn Kα under a 10 keV beam within 2 %**
   (line 0.05 of the scatter under it). The reader refuses. The others
   answer −20 % (PyMca), −100 % (PyXRF) or worse. Once the line is as
   strong as the background under it, P1+P3 is within 0.2 % on the real
   readout A blanks (§10).
5. **On the real blanks (§10) the reader with its escape strip is the
   most accurate method run blind**: 49 of 192 conditions, against 20
   for the best fixed PyMca setting. Without the strip, the escape peak
   of the scatter is read as a line (Ni +22 % under 9.2 keV).
6. **On real lines (§11)** the reader's P1+P2+P3 has the smallest
   low-count bias (−2 to −7.5 % at 27–58 counts per spectrum) and honest
   error bars in every series. At high counts the reader is within
   0.4 %, and PyMca reads 2.4–6 % low. P2's fixed width, though, is
   narrower than the real line (by 21 %), so P2-based answers on the sums
   sit 11 % below the other methods'.

## What would close the gaps

These are suggestions, not done. By rule 12 a default changes only with
its own study.

- **Known neighbours in the box**: place the tabulated lines of the
  other elements present at fixed energies, with the same width. Study
  B's `fit_known` comparator is half of this. That would cover Ga/Zn and
  Co/Fe.
- **Use Kβ and a lighter background when the box is clean**: a linear
  background option, or a joint Kα+Kβ fit at the tabulated ratio. That
  would win back the precision.
- **The escape strip (P3) on by default**, once rule 12's steps are
  done: on the real blanks it is what separates the reader's methods
  (P1 31 conditions, P1+P3 49). It needs the detector's escape factor,
  which `docs/studies/mca_scatter` measured per readout.
- **P2's width from the line itself**: on the real series the line is
  21 % wider than the detector's measured resolution, so a width taken
  from the summed series' own fit (as `fit_series` already does for the
  centres) would keep P2's low-count benefit without its 11 % deficit.
- **P2's width from the detector's own Fano factor and noise**,
  calibrated on the elastic peak, instead of the textbook Fano 0.115.
- **Kβ/Kα in `mca.ELEMENTS` is 16–28 % low** against xraylib. Only the
  synthetic data is affected: the reader fits Kα only.

## Limits of this study

- **Sections 1–9 are synthetic; section 10 has real scatter but
  synthetic lines.** The lines are drawn with the detector measured on
  each blank, without its high-energy tail (0–2 % on these blanks).
  Section 11 fits real lines, but against each method's own answer (the
  twins) and against the other methods; no line of known strength was
  fitted. That would need a standard (a known film or solution) measured
  on the beamline.
- **Section 11 is one readout, one beam energy and one line** (the 19
  series the bundle's hand-off selects). The other private
  spectra (energy scans above the edges, the excluded 10 keV sums) are
  not yet used.
- **Ten blanks, two readouts, three beam energies.** Readout A at 10 keV
  has two blanks; 9.2 and 6.1 keV are pre-edge sums on readout B
  (rebinned, counts rounded). Thinning one blank many times gives
  replicates that share at most 23 % of their counts, so the between-blank
  range in `blanks_tables.md` is the better measure of spread.
- **PyXRF and Larch were configured from their documentation and
  source, not by their authors.** Both showed fits that land on the
  wrong solution with water's Compton scatter near the line. With more
  tuning they would probably do better.
  - Larch's fit of the clean Lu twin collapsed (calibration factor 0.5
    against about 25 elsewhere), so its Lu numbers mean nothing.
  - PyMca's polynomial-continuum setting failed outright (curve errors
    in the thousands of percent).
- **Calibration offsets and gains were tested only on the 10 keV hard
  case**, where every method fails. They should be rerun at 12 keV.
- **XFNTR curves use one geometry and one surface model**
  (`xfntr.yield_curve`).

## Figures

| Figure | What it shows |
|---|---|
| `X1_scoreboard.png` | bias of every method in every condition; hatched where more than 20 % of fits fail |
| `X2_counts.png` | bias against counts on a clean line |
| `X3_xfntr.png` | XFNTR curves divided by the truth |
| `X4_honesty.png` | pull SD per method |
| `X5_wins.png` | per condition, the best of each side and the verdict |
| `X6_anatomy.png` | the new synthetic spectra, part by part |
| `X7_compton_and_constants.png` | three Compton models under Zn; remembered constants against xraylib |
| `X8_speed.png` | seconds per spectrum |
| `X9_blank_example.png` | two real blanks with injected lines: what the methods face, with the escape peak of the scatter |
| `X10_blank_bias.png` | real scatter, synthetic lines: bias against line strength, per line and beam |
| `X11_blank_scoreboard.png` | accurate conditions on the real blanks, and the false line on the bare blank |
| `blanks_tables.md` | every real-blank number: bias per method, line, background and strength; accurate counts; false lines |
| `X12_real_series.png` | real lines in real scatter (19 private burn series, summary values): low-count bias on the twins, error-bar honesty, agreement on the sums |
| `real_tables.md` | every real-series number per method: medians and ranges over the 19 series |
