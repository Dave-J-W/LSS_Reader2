# Study: proposing Qoff (and Qc) for R/R_F (F79)

Tools man, 2026-11-24, for Main's F79 assignment. Everything below is
**measured** by `tests/tools/qoff_study.py` (synthetic data with known truth,
60 replicates per condition, 40 bootstrap draws per estimate), except section
6, which uses the public NX school scans. **No default changes**: the
proposer offers a value and the window's "Propose" buttons (the GUI
manager's) will show it; the user decides.

**Regenerate:**

    python tests/tools/qoff_study.py --out docs/studies/qoff        # about 5 min on 4 CPUs

The code is `lss_core/fresnel.py` (`propose_qoff`, `SUBPHASES`,
`qc_from_density`); its tests are in `tests/test_qoff.py`. The tool is in the
Tools menu under Reflectivity patching.

## The question

The owner normalises by R_F with water's Qc and tweaks Qoff "until the
fresnel-normed reflectivity looks continuous, or has one or two outliers but
is otherwise smoothly continuous". Can the reader propose that Qoff, with its
uncertainty, robust to outliers? And can Qc be fitted from the same curve, or
must it come from the subphase?

## Why the edge decides

An angle offset δα shifts Qz by Qoff = (4π/λ) cos α δα, constant below 3°.
Far above the edge a wrong Qoff only tilts R/R_F by (1 + ε/Qz)⁴. At the edge,
R_F falls with infinite slope (R_F ≈ 1 − 4√(2x), x = Qz/Qc − 1), so the same
error leaves a spike or a dip of tens of percent in the first points above
Qc (figure Q1, left). That is what the owner sees.

## The estimators

| Name | What it does | In `propose_qoff` |
|---|---|---|
| **edge** | fits ln R = ln A + ln R_F(Qz + Qoff; Qc) + b(Qz − Qc) + c(Qz − Qc)² up to 2.5 Qc by robust least squares (soft L1): the plateau, the drop and a smooth sample factor | `method='edge'`, **the default** |
| smooth | minimises the roughness of ln R/R_F up to 4 Qc: Σ ρ(second difference / its counting error), ρ Huber to find the basin, then Tukey's biweight within ±10 grid steps of it | `method='smooth'` |
| smooth (least squares) | the same with ρ(z) = z²/2, to show what robustness buys | `loss='squared'` |
| edge, Qc free | the edge fit with Qc a fifth parameter | `fit_qc=True` |

σ is a parametric bootstrap: every point redrawn with its counting error,
times the robust scale of the residuals when that is above 1.

## 1. Do they find the offset?

Bias ± SD of the proposed Qoff against the truth, in 10⁻⁵ Å⁻¹ (truth
0.00088 Å⁻¹ = 88 for δα 0.005° at 10 keV; bare water at the NX school counts
unless stated):

| Condition | edge | smooth | smooth, LS | edge, Qc free |
|---|---|---|---|---|
| δα −0.010° | −0.5 ± 0.2 | −0.8 ± 0.2 | −0.9 ± 0.2 | +29 ± 5 |
| δα −0.005° | −1.8 ± 0.4 | −5.5 ± 1.6 | −8.8 ± 0.6 | +44 ± 7 |
| δα 0 | −1.2 ± 0.3 | −2.7 ± 0.8 | −3.1 ± 0.5 | +51 ± 6 |
| δα +0.002° | −1.8 ± 0.4 | −5.1 ± 1.4 | −8.3 ± 0.6 | +64 ± 11 |
| δα +0.005° | −0.9 ± 0.2 | −1.4 ± 0.3 | −1.5 ± 0.3 | +41 ± 8 |
| δα +0.010° | +0.1 ± 0.9 | +1.1 ± 3.0 | +0.4 ± 0.1 | +52 ± 10 |
| DPPC monolayer | −0.1 ± 0.2 | −0.9 ± 0.3 | −1.9 ± 0.3 | +98 ± 13 |
| 100 Å film (fringes) | +5.4 ± 0.2 | +16.9 ± 1.8 | −5.8 ± 0.3 | +312 |
| counts × 0.1 | −1.0 ± 0.7 | −1.5 ± 0.8 | −1.5 ± 0.8 | +43 ± 24 |
| counts × 0.01 | −0.9 ± 1.6 | −1.7 ± 2.4 | −1.7 ± 2.4 | +48 ± 79 |

- **Every fixed-Qc estimator finds the offset** to within a few 10⁻⁵ Å⁻¹,
  that is a few 10⁻⁴ degrees. The edge fit has the smallest bias and
  scatter in every row.
- **The bias of about −1 × 10⁻⁵ is water's absorption.** It is in the truth
  but not in the reader's R_F, and it rounds the edge slightly. It is the
  same bias the owner's by-eye tweak would have, since both judge the
  reader's own R/R_F.
- **How sure the error bars are:** the pull SD of the edge fit is 0.9 to 1.1
  where it is unbiased, so σ describes the noise. It does not describe the
  biases of sections 3 and 4.
- **Kiessig fringes near the edge** (a 100 Å film) mislead the roughness
  more (+17 × 10⁻⁵) than the edge fit (+5 × 10⁻⁵).

## 2. Outliers

| Condition | edge | smooth | smooth, LS |
|---|---|---|---|
| none | −0.9 ± 0.2 | −1.4 ± 0.3 | −1.5 ± 0.3 |
| one point ±30 % between Qc and 3 Qc | −0.9 ± 0.2 | −1.7 ± 2.5 | −1.4 ± 2.5 |
| two such points | −0.9 ± 0.3 | −0.9 ± 3.7 | −1.0 ± 4.0 |
| **the first point above the edge, 30 % low** | **+3.7 ± 0.9** | +44 ± 6 | +54 ± 0.4 |

- **Outliers away from the edge** hardly move either estimator. They widen
  the roughness estimators' scatter tenfold, and leave the edge fit alone.
- **An outlier at the edge itself** defeats the roughness. That point carries
  the edge, so it pulls the roughness by Qoff +44 × 10⁻⁵, half the offset.
  The edge fit down-weights it and stays within 4 × 10⁻⁵.
- **The two-step loss matters.** A Tukey loss alone can "explain away" the
  two edge points as outliers, which gives a false minimum. In a check of
  six NaCl replicates before the fix, four landed there (Qoff 0.00062 for
  the true 0.00088). Huber's loss finds the basin first, and Tukey then works
  only within it.

## 3. Resolution

A Gaussian Qz resolution (FWHM, constant) smears the edge, and the
estimators read the smearing as a negative Qoff:

| ΔQ FWHM (Å⁻¹) | edge | smooth |
|---|---|---|
| 0 | −0.9 ± 0.2 | −1.3 ± 0.4 |
| 0.0002 | −1.8 ± 0.2 | −2.4 ± 0.3 |
| 0.0005 | −7.1 ± 0.2 | −8.3 ± 0.2 |
| 0.001 | −15 ± 0.2 | −17 ± 0.5 |

- The bias grows as roughly −0.15 ΔQ.
- This makes R/R_F continuous, which is the owner's aim. But it is not the
  true angle offset when the resolution is not negligible.
- The proposer does not model resolution. The reader's R_F does not either.
- **For the owner** (via questor): what is the Qz resolution near the edge
  at 15-ID-C? **Measured 2026-11-24** (non-cloud agent, DATA_NEEDS row 13,
  `docs/studies/qz_resolution/summary.md`): ΔQ FWHM 8.9 × 10⁻⁴ Å⁻¹ at 10 keV
  (σ_Q 3.8 × 10⁻⁴; runs 6.5–12.6 × 10⁻⁴), from the edge's width in 378 real
  scans; no dependence on S1 between 0.04 and 0.2 mm. By the −0.15 ΔQ above,
  it reads as a Qoff of about −1.3 × 10⁻⁴ Å⁻¹.

## 4. A wrong Qc, and Qc with Qoff

| Condition | edge | smooth | edge, Qc free |
|---|---|---|---|
| 1 M NaCl (Qc 0.0221) reduced at water's 0.0217 | −42 ± 2 | −41 ± 3 | +47 ± 8 |
| 1 M NaCl at its own Qc | +0.3 ± 0.5 | +1.3 ± 5 | +43 ± 8 |
| water reduced at 0.0221 | +34 ± 0.2 | +34 ± 1 | +42 ± 8 |

- **A wrong Qc moves Qoff one for one.** Qc 0.0004 too low gives Qoff
  0.0004 too low. The edge then lands in the right place, and R/R_F above it
  is off in level by 7 % (figure Q4, right).
- **Qc and Qoff cannot be fitted together** from one curve. The replicates of
  the joint fit lie on the line Qc − Qoff = constant (figure Q4, left), with
  bootstrap correlation +0.9 to +1.0. Both come out about 4 × 10⁻⁴ too high:
  absorption rounds the edge and the joint fit absorbs it.
- So **Qc from the subphase, Qoff from the data.** `fresnel.SUBPHASES` lists
  water, D2O, NaCl, KCl and CaCl2 with their Qc (0.0217 to 0.0225). Every
  density there is from memory and marked so: the sources could not be
  opened from this session.

## 5. Joins

The same estimates with the reader's own patch (joint fit) instead of the
true scales:

| Condition | edge | smooth |
|---|---|---|
| water | −0.9 ± 0.2 | −1.3 ± 0.3 |
| DPPC | −0.1 ± 0.2 | −0.8 ± 0.5 |

The joins add nothing measurable. The edge lies inside the first scan, and
far above it a Qoff error only tilts the curve.

## 6. The NX school scans

NX school scans 6–9 (DPPC on water, 10 keV), at Qc 0.0217 (figure Q5):

| Estimator | Qoff (Å⁻¹) | as an angle |
|---|---|---|
| edge (default) | −0.00028 ± 0.00001 | −0.0016° |
| smooth | −0.00028 ± 0.00005 | −0.0016° |
| smooth, least squares | −0.00031 | −0.0017° |
| edge, Qc free | +0.00246 at Qc 0.0244 (correlation +0.92) | unusable |

- **The GUI's preset is 0.** At 0 the first point above the edge sits 5 %
  above its neighbours (the spike in figure Q5). At −0.00028 R/R_F rises
  smoothly from the plateau into the monolayer's shape.
- The two estimators agree to 3 × 10⁻⁶ Å⁻¹ (−0.000280 and −0.000278).
- **Resolution or angle?** Part of the −0.00028 may be resolution
  (section 3): extrapolating its −0.15 ΔQ, a resolution of 0.002 Å⁻¹ alone
  would give about −0.0003. The proposal
  makes R/R_F continuous either way. Whether it is a true angle offset
  needs the resolution.

## 7. Recommendation

1. **Offer the edge fit's Qoff as the proposal** (`propose_qoff`'s default),
   with its note and σ, beside the Qoff field. It was the least biased,
   steadiest and most robust in every condition here.
2. **Take Qc from the subphase** (the list or a typed density), never from
   the same fit. Set Qc before Qoff: a wrong Qc moves Qoff one for one.
3. **Keep the roughness estimator** as a check, since it is the owner's
   by-eye criterion. When the two disagree by more than their errors, look
   at the edge: an outlier at the first point above Qc, or fringes near the
   edge.
4. **Nothing applies the value**, and no default changes. A default "apply
   the proposal" would need, by rule 12, this study, its tests and a
   demonstrator: this document and its Tools item are the first two parts.
   Real-data checks on more files and the beamline's resolution would
   complete it.

## Figures

| Figure | File | What it shows |
|---|---|---|
| Q1 | `Q1_anatomy.png` | R/R_F near the edge at Qoff wrong by ±0.0005, at the truth and at 0; the roughness loss and the edge fit's cost against Qoff |
| Q2 | `Q2_bias.png` | bias ± SD of every estimator in every condition |
| Q3 | `Q3_pulls.png` | the pulls (estimate − truth)/σ, by estimator |
| Q4 | `Q4_qc.png` | the joint fit's replicates on Qc − Qoff = constant; what a wrong Qc does to R/R_F's level |
| Q5 | `Q5_nx.png` | NX school scans 6–9 at the preset and at the proposals; the roughness loss |

The numbers behind them are `results.csv` (per condition and estimator),
`replicates.csv` and `numbers.json` (with the NX proposals).
