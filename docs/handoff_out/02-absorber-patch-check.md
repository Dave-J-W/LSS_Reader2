# Hand-off: measure the absorber steps by patching reflectivity scans

**Answered 2026-11-18** (`02-answer-report.md`, reviewed in
`docs/physics_notes.md`). From the 409 joins across which `Monc/Monp` did
not change, the six foils are 54.7, 112.2, 218.0, 432.1, 862.7 and
1725.1 µm Al-equivalent at 10 keV (± 0.1–0.5), constant to about 1 µm
from 2025-12 to 2026-10. The jumps between runs are not the foils:
they occur where a slit change was not followed by `Monc` (P29).

Written 2026-11-18 by the LSS_Reader2 agent, for an agent with access to the
owner's SPEC files (reflectivity series with a `proi` ROI counter and
absorbers). Self-contained: you need this file, the script beside it
(`02-absorber_steps.py`, Python 3 + numpy), and the SPEC files. You do not
need the LSS_Reader2 repository or the detector images. Return the
deliverables in §8.

Throughout, **measured** means computed from data in this hand-off's
example, **reasoning** means argued but not measured, and **owner** means
stated by the owner.

## 1. The question

The beam is attenuated by stacks of aluminium foils before the sample.
SPEC writes the setting as `#A Absorber n` in each scan header. The foils
are **six binary-weighted foils** (owner), so

    n = Σ_k b_k 2^k,  k = 0…5,  b_k ∈ {0, 1}     (foil k is in when bit k is set)

and one unit is nominally 50 µm of Al (owner). The nominal transmission of
n units at photon energy E is

    T(n) = absfac(E)^(-n),  absfac(E) = exp(μ/ρ(E) · ρ · 50 µm)    (Beer–Lambert)

with μ/ρ the total mass attenuation coefficient of Al from NIST SRD 126
(Hubbell & Seltzer, <https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z13.html>,
doi:10.18434/T4D01F) and ρ = 2.699 g/cm³. At 10 keV, μ/ρ = 26.23 cm²/g and
absfac = 1.4247 per unit. Energy comes from `#W` as E = 12.39842 keV·Å / λ.
The script holds the NIST rows from 2 to 100 keV and interpolates
log-linearly.

The owner does not use a fixed absorber calibration. Their reflectivity
macros **patch** consecutive scans together, because they believe the
effective attenuation of a setting changes from day to day. The suspected
causes are beam position and size, foil position, and foils that are not
uniform.

Questions to answer:

1. How far is each measured absorber step from nominal, and is the
   deviation **systematic** (same sign and size every day) or random?
2. Is the error a **flat thickness tolerance per foil** (the owner expects
   1–2 µm, still to be verified) or **relative**, i.e. every foil off by
   the same fraction (alloy, density, or a % tolerance)?
3. Do the **per-foil** values change from day to day, and by how much
   compared with their errors?
4. Is any of the deviation caused by something other than the foils
   (count rate, slits changed at the join, sample drift, harmonics)?

## 2. What patching is, and why it measures the absorbers

A specular reflectivity curve R(Q_z) spans about 8 decades, so it is
measured as a **series** of scans. Each later scan covers higher Q_z with
fewer absorbers in, and its first few Q_z values repeat the last few of the
scan before (the **overlap**). Patching scales each scan onto the one
before by the ratio of the two at the overlap and chains the factors.

For two consecutive scans a (more absorbers, n_a) and b (fewer, n_b), at
each Q_z measured in both:

    r = ROI / (Monc · S)                  per point; S = Monc gain (§4.3)
    ratio_i = r_a(Q_i) / r_b(Q_i)         same Q_z, no interpolation
    σ_i = ratio_i · sqrt(1/ROI_a + 1/ROI_b)     Poisson, ROI counts only

    step = Σ w_i ratio_i / Σ w_i,  w_i = 1/σ_i²,  σ_step = (Σ w_i)^(-1/2)
    χ²/dof = Σ w_i (ratio_i − step)² / (N − 1)

The patch factor that scales scan b onto scan a is the step itself. If
nothing but the absorbers changed between a and b (same slits, sample,
alignment, detector response), then

    step = T(n_a) / T(n_b) = transmission of the foils that differ

So the patch factor **is** a measurement of the absorber step. Compare it
with nominal:

    nominal = absfac(E)^(-(n_a − n_b))
    extra Al (µm) = −ln(step / nominal) / (μ/ρ · ρ)     (> 0: attenuates more than nominal)

Rules that matter:

- **Use only Q_z measured in both scans.** Match on the `L` column to
  1e-5. Do not interpolate: interpolating a steep curve biases the factor,
  and that bias is a known open issue in the reader.
- **Keep the ROI counts raw.** Their Poisson error is the dominant one.
  `Monc` counts are 10⁵–10⁶ per point, and its measurement noise is about
  0.04 % per point (hand-off 01, owner's answer), so it is negligible here.
- **Patch only consecutive scans of one series**, at one wavelength.
- **Report χ²/dof for every join.** It is the check that the overlap
  points agree with each other.

## 3. Worked example (measured, public data)

NX school file `2026sep/20260923`, scans 6–9, 10 keV. In this file the ROI
counter is named `Pilatus`; your files call it `proi`. Command:

    python 02-absorber_steps.py 20260923 --roi Pilatus

| Join | n (bits b5…b0) | shared L | step/nominal | χ²/dof | extra Al |
|---|---|---|---|---|---|
| S6→S7 | 41 (101001) → 31 (011111) | 0.035, 0.0375, 0.04 | 0.789 ± 0.005 | 1.18 | +33.5 µm on 500 |
| S7→S8 | 31 (011111) → 24 (011000) | 0.09, 0.095, 0.1 | 0.762 ± 0.006 | 1.93 | +38.3 µm on 350 |
| S8→S9 | 24 (011000) → 18 (010010) | 0.17, 0.18, 0.19 | 0.870 ± 0.005 | 1.86 | +19.7 µm on 300 |

- **Column-only matches the images (measured).** The reader's full image
  reduction, with background subtraction, gave 0.788, 0.762 and 0.870. On
  these joins `proi`-style columns are enough.
- **Every step attenuates 7–11 % more than nominal (measured).** Each is
  26–42 counting errors from nominal.
- **Neither simple foil model fits (measured).**
  - Every foil off by the same fraction: f = +0.074 ± 0.001, χ² = 169 on
    2 dof.
  - Six free foils with a ±2 µm prior each: the fit needs foils 20–30 µm
    off (prior χ² = 399 for 6 terms).
  - With three joins and six foils the per-foil values are not determined
    (rank 3).
- **The slits changed at two of the three joins (measured).**
  - `Monc/Monp` carries straight on across S6→S7 (0.465–0.478 at the end of
    S6, 0.469–0.484 at the start of S7), so nothing between the monitors
    changed there. The S6→S7 step is a clean absorber measurement.
  - It jumps ×4.5 across S7→S8 and ×1.4 across S8→S9. Something between
    `Monp` and `Monc` (most likely S1) was opened at those joins, so those
    two steps mix the foils with the slit change.
  - `Monc` does not change with n, so the absorbers are downstream of
    `Monc`.
  - This file does not record motor positions (its `#P` lines repeat the
    names), so the slit settings could not be read.
- **Count rate (measured, weak).** In the brighter scan of each join the
  peak pixel reached 1.1×10⁵ counts/s and changed 2–4× across the three
  overlap points, while the ratio stayed constant (χ²/dof 1.2–1.9). Three
  points is a weak test. The image headers say `Tau = 0 s`,
  `Retrigger_mode: 1`, `Ratecorr_lut_directory: ContinuousStandard_v1.1`,
  and `Count_cutoff 1175641`.

## 4. Procedure

### 4.1 Find the series

A reflectivity series is a run of consecutive `hklscan`s at fixed H and K
(scanning L), at one wavelength, where each scan's L range overlaps the
previous one. The script finds these itself. If the owner's macros use
another scan command, pass the scans by hand: `--series 12,13,14,15`
(repeat `--series` for several series).

Exclude a join, and list it as excluded with the reason, when:

- `#A` is missing or unreadable. The script treats it as unknown. (The
  reader itself once defaulted unreadable `#A` to 63, so don't copy that.)
- the overlap has fewer than 2 shared Q_z points;
- the two scans have different `#W`;
- one scan has a `#M Monc Gain` line and the other doesn't.

### 4.2 Columns

| Quantity | Column | Note |
|---|---|---|
| Q_z | `L` | Used only to match points, so its units don't matter |
| detector | `proi` (`--roi`) | EPICS-defined ROI sum; no background subtraction |
| monitor | `Monc` (`--mon`) | After the S1 slits, before the absorbers (measured, §3) |
| upstream monitor | `Monp` | Not used in r; used for the slit check (§5) |

### 4.3 Monitor gain

SPEC writes `#M Monc Gain S unit` (SR570 sensitivity, A/V). Counts per
photon scale as 1/S, so normalise by `Monc · S` (owner, F52). 5 µA/V is
the usual gain (more than 90 % of runs, owner). The script reads the gain
per scan and converts units. A join where the gain changed is still valid
after this correction, but flag it. If neither scan has a gain line, S = 1.

### 4.4 Run

    python 02-absorber_steps.py FILE --roi proi --csv FILE_steps.csv
    python 02-absorber_steps.py FILE --roi proi --prior-um 2     # test the flat ±2 µm hypothesis

Output:

- one Markdown row per join, and a CSV if `--csv` is given;
- nominal χ², the common-fraction fit, and the per-foil fit with a prior.

The per-foil fit uses only the joins at the first join's energy; run other
energies separately. Its model, for each join:

    −ln(step) = Σ_k [b_k(n_a) − b_k(n_b)] · d_k,   d_k = 2^k · d_unit + δ_k

δ_k is foil k's optical-depth excess, reported in µm Al. It has a Gaussian
prior of width `--prior-um`. When a foil's posterior error is close to the
prior width, that foil is not determined by the data. Increase the rank by
pooling joins with different bit patterns, from more series of the same
day and energy (§6).

## 5. Systematics to test (each one before blaming the foils)

1. **Slits changed at the join.** Compare `Monc/Monp` over the last points
   of scan a and the first points of scan b.
   - If the ratio is continuous, the slits are the same and the join is
     clean.
   - If it jumps, mark the join "slit change". Report steps for clean joins
     and slit-change joins separately.
   - If your files record motor positions on `#P` lines, also compare
     S0–S2 (`S1T`, `S1B`, `S1L`, `S1R`, …).
2. **Count rate.** The brighter scan (b) has 1/step times more counts.
   - Without rate correction, lost counts in b push the step up toward
     nominal (reasoning).
   - If the detector's rate correction over-corrects, the sign reverses.
   - Test: plot step/nominal against the peak ROI rate of scan b (ROI /
     Seconds; the script prints the largest ROI count of the pair).
     Within a join, look for a trend of ratio_i with ROI_b.
   - If the files hold several detector modes or count-rate settings,
     split by them.
3. **Background in `proi`.** The ROI includes the background, and the
   background is attenuated by the same foils. The ratio is affected only
   by background that does not depend on the absorbers.
   - If the files have a background ROI counter, repeat the analysis with
     ROI − background.
   - Otherwise check that the overlap points are well above the
     high-Q_z counts of the same scan.
4. **Sample or alignment drift between scans.** A liquid surface moves
   (evaporation, temperature).
   - Report the time between the overlap points (`Epoch` column, or `#D`).
   - Flag joins with an alignment scan between a and b.
   - Look for steps that depend on that time.
5. **Harmonics.** A λ/3 component (30 keV at 10 keV) passes Al almost
   unattenuated: 30 keV transmits about 0.985 per unit, against 0.70 at
   10 keV.
   - The harmonic fraction therefore grows with n, which inflates scan a
     and pushes the step up toward nominal (reasoning).
   - It is reflected far less at the same angle, so the effect is
     probably small.
   - Test: steps with large n_a against small n_a for the same Δ-bits.
6. **Energy.** If series exist at more than one energy:
   - extra thickness that is the same in µm at every energy means
     thickness;
   - extra that scales differently from Al's μ/ρ(E) means composition
     (an impurity with a higher Z). Report each energy separately.

## 6. Foil-by-foil and day-to-day

- **One day = one SPEC file** unless the owner says otherwise. The script
  fits per file; for a day spread over several files, concatenate the CSVs
  and refit.
- **What determines each foil.** A join determines the combination of
  foils whose bits differ, signed (+1 in a only, −1 in b only). Six
  independent combinations at one energy are needed for full rank. The
  NX school day had three. List which bit patterns each day provides.
- **Day-to-day test.** For each foil (or each determined combination),
  compare the per-day values with χ² = Σ (x_day − x̄)² / σ_day². A χ²/dof
  well above 1 means real day-to-day variation, the owner's hypothesis.
  Give the spread beyond the errors.
- **Same join type across days.** When the same (n_a, n_b) pair recurs (a
  standard macro will repeat it), tabulate it across days. This needs no
  foil fit at all, and it is the most direct test.

## 7. Things already known that you should not re-derive

- The reader's Ref Patch measures the step, so it is unaffected by any of
  this. Only paths that combine settings with the **nominal** factor are
  affected: image cuts, background images, frame averages, GID, and
  fluorescence spectra at different n. Your result decides whether those
  can use a per-foil calibration, or must keep patching.
- `#A` absent from an MCA scan means the setting comes from the last `#A`
  above it. That is a reader convention, not data, so don't use such
  scans.
- Copper foils at 30 keV: unit thickness unknown. Don't analyse 30 keV
  absorbers as Al. Report steps there without a nominal value.
- At 10.05 and 10.52 keV, which foils are used is unknown; report those
  steps without a nominal value, or with the Al value clearly labelled as
  an assumption.

## 8. Deliverables

1. **Join table**, every join, as the script's CSV plus these columns:
   file, series, E, slit flag (`Monc/Monp` continuous or jump), time
   between overlap points, peak ROI rate of scan b, and the reason for any
   exclusion.
2. **Per day and energy:**
   - number of clean joins and their bit-pattern rank;
   - common-fraction fit (f ± σ, χ²/dof);
   - per-foil fit at prior widths 2 µm and 10 µm, with posterior errors and
     the "determined" flag.
3. **Day-to-day:**
   - recurring (n_a, n_b) joins tabulated across days;
   - per-foil or per-combination χ²/dof across days, and the spread beyond
     the errors.
4. **Systematics:** the slit, rate, background, drift and harmonic checks
   of §5, each "measured: effect X ± Y" or "not testable: why".
5. **Answer to §1, questions 1–4,** each marked measured or reasoning.
6. Whether a static per-foil calibration would serve the
   nominal-factor paths to better than 1 %, or whether patching remains
   necessary.

Return only summary tables and plots; the SPEC files themselves are not
needed back.

## References

The NIST table was read from the page itself (saved by the owner,
2026-11-18). The others are cited from memory and were not re-checked.

- J. H. Hubbell and S. M. Seltzer, *X-Ray Mass Attenuation Coefficients*,
  NIST Standard Reference Database 126, doi:10.18434/T4D01F;
  aluminium table: <https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z13.html>.
- Weighted mean, its error, and χ²: Particle Data Group, *Review of
  Particle Physics*, chapter "Statistics" (§ on least squares),
  <https://pdg.lbl.gov/>; also P. R. Bevington and D. K. Robinson, *Data
  Reduction and Error Analysis for the Physical Sciences*, 3rd ed.
  (McGraw-Hill, 2003), ch. 4 and 6.
- Error propagation: JCGM 100:2008 (GUM) §5,
  <https://www.bipm.org/en/doi/10.59161/JCGM100-2008E>.
- Gaussian prior in linear least squares (the per-foil fit): D. S. Sivia
  and J. Skilling, *Data Analysis: A Bayesian Tutorial*, 2nd ed. (Oxford,
  2006), ch. 3.
- PILATUS count-rate correction: P. Trueb et al., "Improved count rate
  corrections for highest data quality with PILATUS detectors",
  J. Synchrotron Rad. 19, 347–351 (2012), doi:10.1107/S0909049512003950.
