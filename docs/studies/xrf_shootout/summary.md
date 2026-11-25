# XRF shootout: the reader's line intensities against PyMca, PyXRF, Larch and XeRay

2026-11-25, overnight session (local, the owner's PC: 16 cores, 128 GB).
**Everything here is measured on synthetic spectra with known truth.**
The one real-data input is the detector and scatter measured on the
owner's blanks (`docs/studies/mca_scatter`), which define the
"measured" conditions. No default of the reader was changed.

- Questions and short answers: `QUESTIONS.md`
- Survey of other packages: `survey.md`
- How to reproduce: `README.md`
- Every number below comes from `tables.md` (generated, with all
  methods and conditions) and from `wins.csv`

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
4. **Nobody can measure Zn Kα under a 10 keV beam within 2 %.** The
   reader refuses. The others answer −20 % (PyMca), −100 % (PyXRF) or
   worse.

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
- **P2's width from the detector's own Fano factor and noise**,
  calibrated on the elastic peak, instead of the textbook Fano 0.115.
- **Kβ/Kα in `mca.ELEMENTS` is 16–28 % low** against xraylib. Only the
  synthetic data is affected: the reader fits Kα only.

## Limits of this study

- **All synthetic.** The generator is checked against xraylib (constants,
  Compton profiles) and against the owner's real blanks (detector
  shape), but no real spectrum with a known line was fitted.
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
