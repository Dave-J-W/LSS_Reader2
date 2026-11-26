# Survey: open-source XRF spectrum analysis, against the reader

Q1 of `QUESTIONS.md`: what do other people use to get line intensities out
of energy-dispersive XRF spectra, and how do their methods differ from the
reader's? Found by GitHub search on 2026-11-25 (`gh search repos`, topics
`xrf` and `x-ray-fluorescence`, and the known projects by name); stars and
last push are GitHub's on that day. "Read" means the source was read;
"run" means it is a contestant in the shootout (`summary.md`).

## The packages

| Package | Where | Stars, last push | Kind | In the shootout |
|---|---|---|---|---|
| PyMca | silx-kit/pymca (ESRF; V. A. Solé) | 79, 2026-11-24 | full-spectrum fit, GUI and library | run (`pymca`, `pymca_tails`) |
| PyXRF | NSLS2/PyXRF on scikit-beam/scikit-beam (NSLS-II; L. Li) | 38 / 98, 2026-07 / 2025-08 | full-spectrum fit for maps | run (`pyxrf`, through scikit-beam's `xrf_model`) |
| Larch | xraypy/xraylarch (M. Newville, U. Chicago / APS-GSECARS) | 191, 2026-11-20 | XAS suite with an XRF model | run (`larch`, `larch_each`) |
| XeRay | ZhiliangGong/xeray (Z. Gong, Lee group, U. Chicago) | 0, 2017 | MATLAB GUI for XFNTR at liquid surfaces | ported and run (`xeray`) |
| XFNTR | zleung9/XFNTR (ChemMatCARS) | 0, 2024-11 | fits XFNTR *curves* (the step after this one) | read; not a spectrum method |
| XRF-Maps | AdvancedPhotonSource/XRF-Maps (APS) | 13, 2026-11-23 | C++ MAPS successor: ROI, NNLS and full fits for maps | read only (C++ build; same model family as PyXRF) |
| exspy | hyperspy/exspy | 23, 2026-11-23 | electron-beam EDS model fitting | read only (no Rayleigh or Compton components) |
| Peakaboo | nsherry4/Peakaboo | 38, 2026-10-31 | Java GUI for XRF maps | not tried (Java GUI) |
| xraylib | tschoonj/xraylib | 174, 2026-10-26 | cross sections, line energies, yields, Compton profiles | used for data (`tests/tools/xrf_tables.py`) |
| XMI-MSIM | tschoonj/xmimsim | 36, 2024-08 | Monte Carlo simulation of ED-XRF spectrometers | not used (Windows installer; would be a second synthetic-data check) |
| fisx | vasole/fisx | 11, 2025-01 | PyMca's physics in C++ (matrix effects) | inside PyMca |

AXIL/QXAS (IAEA) and GeoPIXE, the classic full-spectrum fitters, are not
open source on GitHub.

## How they differ from the reader

The reader works on one **line window**, the main line ± 2 FWHM. In the line window it
fits one Gaussian on a quadratic background. The centre and width come
from the sum of the series; then each spectrum is a linear fit by Poisson
likelihood (`peaks.fit_series`). The options are a width fixed by the
detector and stripping of the Si escape peaks. The others fit the
**whole spectrum**: every line of every element at tabulated ratios, plus
models of the scatter peaks.

| | Reader (p1) | PyMca | PyXRF / scikit-beam | Larch | XeRay |
|---|---|---|---|---|---|
| Region | line window ± 2 FWHM | whole spectrum (user range) | whole spectrum | whole spectrum | line window (user range) |
| Lines | one Gaussian, free centre | every line of the element, PyMca's ratios, Hypermet optional | every line, scikit-beam's ratios | every line, xraydb's ratios, Hypermet | one Gaussian (or two) |
| Background | quadratic in the line window | SNIP or strip filter, plus polynomial | SNIP | optional filter background | straight line |
| Rayleigh / Compton | none (only what the quadratic absorbs) | one peak each, Hypermet, Compton width free | elastic Gaussian; Compton Gaussian with tail, step, width factor | Hypermet each, with free width factor, tail, step | none |
| Si escape | stripping (option) | modelled from the detector | parameter, off in the linear step | modelled (scaled) | no |
| Weighting | Poisson likelihood | χ² with σ = √N (1 where N = 0): data weights (`ClassMcaTheory.setData`, read) | weighted NNLS, σ² = max(N, 1) | weights from smoothed (N + 1)^(2/3) | unweighted |
| Series | sum fixes shape, each spectrum linear | each spectrum alone; fast linear mode for maps | nonlinear fit of the sum, then NNLS per pixel | nonlinear fit, then linear decomposition for maps | each spectrum alone |
| Error bars | from the likelihood's curvature | from the fit covariance | none | lmfit standard errors (one fit) | √(counts in the line window) |

What the table means for a weak line under the scatter of the beam:

- **The full-spectrum fitters spend their parameters on the scatter.**
  Their Compton peak is a detector peak shape (a Gaussian with tails and a
  step) widened by a factor. Water's Compton profile has power-law wings
  and an O 1s shoulder cut off at the binding energy. Where the model
  cannot follow that shape, the fit pushes the mismatch into whatever is
  free, and the weak line is free.
- **The reader spends its parameters locally.** A quadratic over ±2 FWHM
  follows the scatter only as far as it is smooth. The Si escape peak of
  the elastic line (8.26 keV, inside the Zn line window) is not smooth; that is
  what option the escape removal subtracts.
- **Data weights** (PyMca, PyXRF) read weak lines low by about the
  number of background counts in the fit (study B: −19/N in a 74-channel
  line window). Poisson likelihood (the reader's default since 2026-11-24) does not.
- **Overlaps are where the full-spectrum fitters should win.** A line window sees
  only one line. A whole-spectrum fit can split As Kα from Pb Lα using As
  Kβ and Pb Lβ, which sit elsewhere.

## Read but not run, and why

- **XFNTR (zleung9)** fits the XFNTR *curve* (intensity against Qz) to a
  model of the interface, which is the step after this one. It takes
  integrated intensities as input.
- **exspy** has no Rayleigh or Compton components, because an electron
  beam makes none. A fair configuration would mean writing them in, and
  the result would no longer be exspy's.
- **XRF-Maps** fits the same family of models as PyXRF (both descend from
  MAPS: Gaussian lines, a Compton peak with a step and tail, SNIP), in
  C++. It was not built.
