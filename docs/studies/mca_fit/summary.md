# Study B: how to measure an MCA line intensity (F90)

**Since 2026-11-24 P1 is the reader's default** (rule 12; recommendation 1
below). The study's figures and tables are kept as run: "fit (data
weights)" and "today" there mean the weighting before that day.

Tools man, 2026-11-24. This is the plan's study B
(`docs/studies/2026-11-24_two_decisions_plan.md`). Everything here is
**measured on synthetic spectra** (`tests/synthetic/mca.py`). Real data
come only in question 3. No default was changed: P1, P2 and P3 are
options in the reader, waiting for the owner's decision.

**Regenerate:**

    python tests/tools/mca_fit_gauntlet.py --out docs/studies/mca_fit/gauntlet \
        --design all,robust,counts --methods study --compton shells --replicates 200   # ~15 min, 4 CPUs
    python tests/tools/mca_study.py --gauntlet docs/studies/mca_fit/gauntlet --out docs/studies/mca_fit

Both are in the Tools menu, under Fluorescence (MCA).

## The question, in one sentence

When a weak fluorescence line (Zn Kα, 8.63 keV) sits on the scatter of a
10 keV beam, which way of measuring its intensity gives the true
intensity, and the true shape of an XFNTR curve?

## The choices

| Name | What it is | In the reader |
|---|---|---|
| window sum | the counts in a box around the line (Sum All) | today |
| window − sides | the box minus a straight background through side bands | not in the reader (comparator) |
| fit (data weights) | "Fit lines": a Gaussian on a quadratic over the box, each spectrum by least squares weighted by its own error bars | today's default |
| P1 | the same fit, each spectrum by Poisson maximum likelihood | option `mca_fit_poisson` |
| P1+P2 | P1, and the line width fixed at the detector's resolution | option "width from the detector" |
| P1+P3 | P1, after stripping the Si escape peaks | option "strip Si escape peaks" |
| P1+P2+P3 | all three | the three options |

The box is ±2 FWHM of the detector at the line. ±3 FWHM is one of the
grid's factors (P4).

## The key equations

**Poisson likelihood (P1)** for counts n_i and model μ_i(a):

$$\ln L = \sum_i \left[n_i \ln \mu_i(\mathbf a) - \mu_i(\mathbf a)\right],\qquad
\frac{\partial \ln L}{\partial a_k} = \sum_i \left(\frac{n_i}{\mu_i} - 1\right)\frac{\partial \mu_i}{\partial a_k} = 0 .$$

At the truth the expectation of each term is zero, so the estimate is
unbiased to order 1/N.

**Data weights (Neyman's χ²)** minimise $\sum_i (n_i-\mu_i)^2/n_i$. A
channel that fluctuated down gets more weight than one that fluctuated
up. The fit is pulled low by about one count per channel, and part of
that goes into the line. That bias falls as 1/N:

$$\frac{E[\hat A] - A}{A} \approx -\frac{c}{N},\qquad c = 19\ \text{counts}$$

c is fitted to B3: a ±2 FWHM box of 74 channels, 1 count per channel of
background. Cash (1979, *ApJ* 228, 939) and Baker & Cousins (1984, *NIM*
221, 437) treat the general case.

**The window sum** counts everything in the box:

$$E[\hat A_{\rm win}] = A\,f_{\rm box} + B_{\rm box},$$

where f_box is the share of the line inside the box (≈ 1 at ±2 FWHM) and
B_box is all the scatter inside the box. B_box is what goes wrong.

**What lies under the line** (B1: the hard case, 1e3 Zn photons on 1e6
elastic photons; counts inside the ±2 FWHM box):

| Part | Counts in the box |
|---|---|
| the line | 887 |
| O 1s Compton wing | 5,681 |
| Si escape peaks | 570 |
| detector tails and shelves | 471 |
| valence Compton | 175 |
| flat background | 75 |

## 1. What does each choice do on data whose truth we know?

Bias is against the true line. Pull SD should be 1. From
`gauntlet/verdict.csv`, 200 series of 10 spectra per condition.

| Condition | window | fit (data) | P1 | P1+P2 | P1+P3 | P1+P2+P3 |
|---|---|---|---|---|---|---|
| clean line, 9e3 counts | +0.8 % | +0.2 % | 0.0 % | −0.4 % | 0.0 % | −0.4 % |
| clean line, 100 counts | +83 % | **−23 %** | +1.8 % | −1.5 % | +1.8 % | −1.5 % |
| clean line, 400 counts | +21 % | **−5.0 %** | +0.4 % | −0.9 % | +0.4 % | −0.9 % |
| smooth scatter (valence Compton only) | +28 % | −1.0 % | −1.4 % | −1.2 % | −1.4 % | −1.2 % |
| hard case without the O 1s wing (escapes, tails) | +132 % | +82 % | +82 % | +19 % | +13 % | +4.5 % |
| **hard case** (all features) | +786 % | −46 %, 90 % failed | −45 %, 90 % failed | +31 %, 70 % failed | +13 %, 70 % failed | −7.3 %, 60 % failed |
| hard case, Zn at 1e-2 of the elastic | +80 % | +5.8 % | +5.9 % | +2.8 % | −1.3 % | −1.9 % |
| hard case, beam at 11 keV | +113 % | −4.5 % | −4.8 % | −2.4 % | +0.3 % | −0.4 % |
| **hard case, beam at 12 keV** | +42 % | +1.1 % | **+0.5 %** | −0.7 % | **+0.4 %** | −0.7 % |
| Fe Kα, far from the scatter | +38 % | +1.1 % | +0.4 % | −0.1 % | +0.3 % | −0.1 % |

**The weighting (B3).**
- Data weights read a weak line low: −23 % at 100 counts, −5 % at 400,
  −1.5 % at 1000. The fitted law is −19/N.
- P1 is within its errors from about 60 counts up.
- Below about 50 counts every fit becomes unstable.

**One feature at a time (B4)**, from the smooth baseline:
- the Si escape peak of the elastic line (8.26 keV, Reed's fraction
  ≈ 0.1 %) adds about +64 % to the reader's fit, because the free width
  swallows it (B2 shows this);
- the O 1s Compton wing gives −10 % at a quarter of water's and −24 %
  at water's, with fits failing;
- gain and offset errors give 3–7 %;
- P2 (fixed width) cuts most of these to a third or less;
- P3 (stripping) removes most of the escape effect;
- nothing removes the wing.

**XFNTR curves (B5)**, the worst point's deviation from the true shape:

| Curve | window | fit (data) | P1 | P1+P3 | P1+P2+P3 |
|---|---|---|---|---|---|
| smooth | 2.7 % | 0.8 % | 0.5 % | 0.5 % | 0.6 % |
| smooth, weak | 24 % | **13 %** | 1.2 % | 1.2 % | 1.3 % |
| surface + bulk | 25 % | 8.7 % | 2.0 % | 2.0 % | 2.4 % |
| hard | **68 %** | 4.7 % | 4.7 % | **1.4 %** | 1.7 % |

χ²/dof of the ratio after one free scale:

| Curve | window | fit (data) | P1 | P1+P3 | P1+P2+P3 |
|---|---|---|---|---|---|
| smooth | 2.33 | 1.00 | 1.00 | 1.00 | 1.01 |
| smooth, weak | 12.7 | 1.20 | 1.05 | 1.05 | 1.05 |
| surface + bulk | 2.52 | 1.07 | 1.00 | 1.00 | 1.00 |
| hard | 881 | 2.8 | 2.8 | 1.39 | 1.49 |

**Random conditions (B6)**, all features at once, 150 of them; share
within 1 % with no failure:

| window | window − sides | fit (data) | P1 | P1+P2 | P1+P3 | P1+P2+P3 |
|---|---|---|---|---|---|---|
| 0 % | 6 % | 15 % | 15 % | 14 % | 17 % | 15 % |

## 2. Is the synthetic data good enough?

**Improved for this study:** water's Compton scatter is now computed
shell by shell, in the impulse approximation:
- O 1s, O 2s, O 2p and H 1s, each with a hydrogenic momentum density;
- each with its binding cut-off;
- with the exact mapping from p_z to energy.

This is `Beam(compton_model='shells')`, described in SYNTHETIC_DATA.

**What is still assumed (from memory):**
- the effective charges (Clementi and Raimondi), and the O 1s binding
  (0.543 keV);
- Reed's escape constants;
- the detector's tail and shelf.

Tabulated Hartree–Fock profiles (Biggs, Mendelsohn and Mann 1975) would
be better, but they could not be installed here.

**The robustness map (B7)** sweeps the two assumptions that decide the
answer. These are the escape fraction (0–3 × Reed) and the O 1s wing
(0–2 × water's), with the hard case's other features fixed.

| Conclusion | Holds | Does not hold | Not judged (most fits failed) |
|---|---|---|---|
| the window sum fails (> 1 %) | **everywhere** (20 of 20 cells) | 0 | 0 |
| P1+P2+P3 is the best fit | 5 | 0 | 15 |
| P1 at least as good as today's fit | 5 | 3 | 12 |
| P1+P2+P3 within 1 % | **2** (no wing and no escape; wing ½ with escape ×1) | 9 | 9 |

- With an O 1s wing of half of water's or more, most fits fail.
- So the answer for the 10 keV hard case depends on the wing's real
  size. The synthetic data cannot settle that; their error is in the
  wing.
- The conclusions about **weighting** (B3) and **the window** hold
  whatever the background. They do not depend on these assumptions.

## 3. Is real data needed?

**Not for P1.** Its effect is at low counts. A clean line shows it, and
no background assumption enters.

**Not for the window sum.** It fails whenever scatter sits under the
box, which is always the case with a beam above the line.

**Yes for the 10 keV hard case.** What decides it is the shape of the
scatter under the line: the O 1s Compton wing and the escape fraction.
These are measured directly by **a blank spectrum**:
- pure water or the subphase;
- the same beam energy, Qz, detector position and counting time.

That is `DATA_NEEDS.md` row 3, which the owner has promised ("other
elements and blank spectra"). From the blank:
- the wing is the counts below the Compton peak once the valence part is
  fitted;
- the escape fraction is the elastic's escape peak over the elastic.

One blank per beam energy and geometry is enough to check the generator
(B7's two axes). Nothing from the private data is needed.

**The public NX school data has no MCA spectra**, so nothing can be
checked now.

## 4. What does it cost to be wrong?

**Using the window sum on Zn under 10 keV distorts the XFNTR curve.** In
the hard series the ratio to the truth runs from 0.76 below Qc to over
1.5 above it (68 % at the worst point). The surface and bulk
contributions would be misassigned. Even on smooth scatter the window's
curve is off by 2.7 % (χ²/dof 2.3).

**Data weights cost the weak points**, which are the high-Qz end of an
XFNTR curve: 13 % at the weakest point of the "smooth, weak" curve,
where P1 gives 1.2 %.

**In the 10 keV hard case**, a fitted line with P2 and P3 still leaves
1.4–1.7 % shape errors (χ²/dof about 1.4). Its absolute intensity is off
by several percent.

## 5. The recommendation

1. **Make P1 the default** for "Fit lines".
   - It removes a bias of −19/N (−5 % at 400 counts, −23 % at 100) and
     costs nothing at high counts: P1 and the data weights agree within
     0.2 % at 10⁴ counts.
   - This does not need real data.
2. **Retire the window sum for any line with beam scatter under its
   box.** At most, keep it as a legacy option.
3. **Keep P2 and P3 as options** until a blank is in.
   - P3 helps wherever there is an escape peak in the box.
   - P2 helps against gain and offset drift and against a free width
     that collapses or swallows a neighbour (B2).
   - Neither handles the O 1s wing.
4. **For the Zn case, choose the beam energy:** this is the one strong
   result of the study.
   - At 12 keV the elastic's escape (10.26 keV) and the Compton wing move
     away from Zn Kα, and P1 alone is within 0.5 % (P1+P3 0.4 %) with no
     failures.
   - At 11 keV, P1+P3 is within 0.3 %.
   - This assumes the same photons in the line. In fact the Zn K
     photo-absorption falls about (10/12)^2.7 ≈ 0.6 × from 10 to 12 keV
     (from memory), so the line loses about 40 % of its counts.
5. **What would change this:**
   - a blank showing an O 1s wing well below water's impulse-
     approximation value would make P1+P2+P3 usable at 10 keV (B7, the
     bottom row);
   - tabulated profiles that differ from the shell model would move B7's
     boundary.

## Figures

| Figure | File | What it shows |
|---|---|---|
| B1 | `B1_anatomy.png` | the hard case's parts, stacked; the ±2 and ±3 FWHM boxes |
| B2 | `B2_replicates.png` | six replicates at about 90, 270 and 1000 counts (the hard detector, a quarter of water's wing), every fit, residuals |
| B3 | `B3_weighting.png` | bias against counts, data weights against P1, with the −c/N law |
| B4 | `B4_features.png` | bias ± 2 SE per estimator, one feature at a time; also at 11 and 12 keV |
| B5 | `B5_series.png` | XFNTR curves divided by the truth |
| B6 | `B6_pass_rates.png` | share within 1 % by class of random condition |
| B7 | `B7_robustness.png` | where each conclusion holds, escape × O 1s wing |

The data behind them is `B*.csv` and `numbers.json`; the gauntlet's
tables are in `gauntlet/`.
