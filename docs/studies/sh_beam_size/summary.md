# The beam's vertical size at the sample, from sample-height scans (F43, OQ-2)

Non-cloud data agent, 2026-11-24. Answers `docs/DATA_NEEDS.md` row 9 and the
data part of OQ-2 (`docs/gui/questions.md`). **Measured** on the private
spec files and Pilatus images of 21 runs (10 keV and 6–8 keV, one run at
30 keV). Nothing here was checked at the beamline. No
code of the reader was changed.

**Regenerate:** the generator reads private files and lives with them
(`sample_data/private/sh_beam/`: `inventory.py`, `fit_edges.py`,
`images.py`, `products.py`). It writes only the anonymised products in this
folder. Runs are labelled R01… in order of energy, gap and width, not by
name or date. Curves are fractions of the beam against sh measured from each
scan's own fitted edge, binned over many scans, so no motor position, count,
image, scan number, file name or date is published. Tools menu: "sh-scan beam
size (private data)" (external, not regenerable from the repository).

## The answer, in four lines

1. **Yes, but not from half-cuts.** Users do the half-cut by hand on the live
   detector view (the beamline's procedure) and record only `set sh 0`
   (526 times). Three scans at incidence 0 were recorded: one with 10 µm
   steps on liquid metal and two 50 µm-step searches on water. Only the
   first is fine enough to use. **Every routine height scan
   (`a2scan sh … oh …`) is a knife-edge scan of the beam on its rising side**, and
   1995 of the 2815 scans pass the guards below.
2. **At 10 keV with S1 0.016–0.04 mm, the beam at the sample has a vertical
   FWHM of about 30–33 µm. About 70 % of it is a core of σ ≈ 12–13 µm; the
   rest is a tail of σ ≈ 50–60 µm.** Within this range it does not depend
   on the S1 gap: it is 2× the 0.016 mm gap and about the 0.04 mm one.
   Wider gaps (0.05–0.2 mm, measured only at 6–8 keV in the sample cell)
   give a larger beam, but still smaller than the slit.
3. **For the dose per mm², use height = √(2π) · σ_rise**, where σ_rise is the
   erf width of a height scan's rising edge. That equals 1.064 × the FWHM
   that `peaks.fit_box` already reports for the rising edge. It is the
   inverse peak of the true (core + tail) profile, so it gives the dose of
   the most exposed line. Median over scans, it agrees with the profile
   measured from the images within a factor of 1.06 (10–90 %: 0.91–1.24).
   **Default when a run has no usable height scan: 0.040 mm** at 10 keV,
   S1 ≤ 0.04 mm (run medians 0.035–0.045 mm).
4. **The slit gap is not the size, and neither is the FWHM.** Taking the S1
   gap (0.016 mm) as the height overstates the peak dose by about 2.5×.
   Taking the FWHM (0.031 mm) overstates it by about 1.3×, because the tail
   holds a quarter to a third of the photons.

## Why the rising edge of a height scan is a knife edge

At the height-scan qz the incident beam slopes down at α (1.6 mrad at
qz 0.016 and 10 keV). The liquid's surface is a dome. A ray clears it
exactly when it passes above the tangent point, the place downstream where
the surface's slope equals the beam's. For a beam of small divergence that
point is the same for every ray, and it moves up 1 : 1 with `sh`. So, as
`sh` rises, the beam is cut from below as if by a blade. The cut rays reflect
into the ROI and almost none are lost (the images' balance: lost ≤ 3 % up to
the plateau in the scans examined). Raising further moves the footprint upstream until the
curved upstream end starts losing light (transmission past the critical
angle). **That falling side is a loss edge of the surface, not a beam edge,
and is never used here.**

Sizes of the distortions (derived from the geometry, not measured):

| Distortion | Effect on the rising edge | Size |
|---|---|---|
| beam convergence (≤ 34 µrad rms) × the tangent point's distance from the centre (30–45 mm) | blurs the knife edge | ≤ 1.5 µm |
| rays reflected near the tangent point at too small an angle to leave the direct beam's pixels | a band of depth R θ²/2 counted as unblocked (R ≥ 2 m, θ half a pixel) | < 0.3 µm |
| reflected light falling between the direct beam and the ROI | counted in neither | measured 0–3 % of the beam |
| the ROI's halo of the direct beam at the foot | constant offset b, fitted | 2–6 % of the beam |
| level drift during a 21-point scan (≈ 10 µm/h) | shifts the edge | < 0.1 µm |
| the upstream loss overlapping the rise (short plateau) | s_r traded against the fall | rejected by a guard |

The footprint (the illuminated length h / sin α) is a consequence of the
vertical size, not a distortion of it. The knife edge measures the vertical
size directly.

## The two witnesses

**Spec only (every scan).** ROI/Monc is fitted with
b + A·Φ((sh − c1)/s_r)·Φ((c2 − sh)/s_f), where Φ is the normal CDF. Only s_r
is kept. A scan is used only if: its first point is below 25 % of the peak
(the rise was scanned from its foot); at least 2 points lie between 10 and
90 % of the rise; c1 is inside the scan; c2 − c1 > 3 s_r; χ²/dof ≤ 20
(Poisson weights plus 1 %); and it is not saturated, short or a copy.
Rejected: 501 scans because rise and fall overlap, 384 for χ²/dof, 127 not
scanned from the foot, 86 under-sampled, 92 with c1 outside, 84 short,
63 no fit, 4 saturated (a scan can fail several). The reader's own
`peaks.fit_box` gives the same rising width: on 150 random accepted scans
its rising-edge FWHM / (2.355 s_r) was 0.983 (IQR 0.978–0.988).

**Images (a subset: 244 scans spread over every run and gap, of which 109
fit well, 18 runs).** The Pilatus 200K separates the beam that flew over
(columns below the ROI) from the reflected beam. The direct-beam fraction
against `sh` is the beam's cumulative profile with no ROI, halo or loss in
it. A single erf fits it badly (median χ²/dof 30): a slow tail remains above
the edge. A core plus a tail with one shared centre
(1 − f)·Φ(·/σ1) + f·Φ(·/σ2), the shape the owner's analysis of the S1 slit scans fits, gives
median χ²/dof 2.1. The ROI's foot shows the lower tail (2–6 % of the beam
before the main rise), so the tail is on both sides.

**The beam before the sample agrees.** The S1 slit scans (`ascan ih`, 223
accepted, 12 runs) see a focus of FWHM 24–75 µm (10–90 %, median 32) at S1.
Its tail fraction is 0–0.61 (median 0.23): the tail is in the beam already
at S1, not made by the liquid. One caveat remains: the upper tail at the
sample could also hold light transmitted through the downstream meniscus of
water. The liquid-metal half-cut has no tail (f2 0.02), but it differs in
energy as well, so this is unresolved.

## Numbers

### Spec-only route: rising-edge σ by class (`roi_rise_by_class.csv`, `S1_rise_vs_gap.png`)

| Energy | S1 gap (mm) | Cell | Runs | Scans | σ_rise median (µm) | range of run medians (µm) | erf FWHM (µm) | dose height √(2π)σ (mm) |
|---|---|---|---|---|---|---|---|---|
| 10 keV | 0.016 | trough | 9 | 556 | 15.3 | 14.0–18.1 | 36 | 0.038 |
| 10 keV | 0.020 | trough | 8 | 665 | 16.7 | 15.7–20.0 | 39 | 0.042 |
| 10 keV | 0.020 | cell | 1 | 96 | 16.6 | | 39 | 0.042 |
| 10 keV | 0.040 | trough | 3 | 301 | 15.8 | 15.6–16.7 | 37 | 0.040 |
| 10 keV | 0.040 | cell | 2 | 76 | 17.0 | 16.9–17.1 | 40 | 0.043 |
| 10 keV | 0.100 | cell | 1 | 3 | 23.4 | | 55 | 0.059 |
| 6–8 keV | 0.050 | cell | 2 | 52 | 21.9 | 21.7–22.1 | 51 | 0.055 |
| 6–8 keV | 0.070 | cell | 1 | 133 | 22.2 | | 52 | 0.056 |
| 6–8 keV | 0.200 | cell | 2 | 103 | 31.8 | 25.5–38.0 | 75 | 0.080 |

"Trough" is the large trough on the usual height stage. "Cell" is a sample
cell on the second height stage. **Confound:** every 6–8 keV class is in the
cell, and the wide gaps are only at 6–8 keV, so energy, cell and gap cannot
be told apart there. Per run (`roi_rise_by_run.csv`), the scan-to-scan
scatter of σ_rise is 0.4–1.8 µm (1.4826·MAD) at 10 keV, against a median
fit error of 0.7–1.6 µm: repeat scans agree to their errors. At 0.2 mm the
scatter is 5–7 µm.

### Images: the profile itself (`images_core_tail.csv`, `S2_profile_from_images.png`, `S3_estimators.png`)

Per scan, medians (10–90 % over 109 scans): core σ1 13.5 µm (10.4–21.3),
tail σ2 56 µm (46–80), tail fraction 0.29 (0.15–0.50), FWHM 33 µm (26–53),
inverse peak 43 µm (37–63), rms 35 µm (27–40).

Stacked over the 10 keV scans (S2), the core + tail fit beats the erf in rms
by about 20 % in both panels:

| | Scans | erf σ (µm) | core σ1 (µm) | tail σ2 (µm) | tail fraction | FWHM (µm) | 1/peak (µm) |
|---|---|---|---|---|---|---|---|
| 10 keV, S1 0.016–0.02 mm | 53 | 17.8 | 12.0 | 59 | 0.35 | 30 | 42 |
| 10 keV, S1 0.04 mm | 20 | 16.8 | 13.3 | 47 | 0.24 | 33 | 40 |

By class, inverse peak / erf FWHM of the ROI is 1.17, 0.98, 1.04 at 10 keV
(0.016, 0.02, 0.04 mm), 1.12 and 1.16 at 6–8 keV (0.05, 0.07 mm) and 0.85 at
0.2 mm. The rule's 1.064 is right within about ±10 % at 10 keV and
0.05–0.07 mm. At 0.2 mm it gives a height about 25 % too large (a peak dose
25 % too low).

### 30 keV: one half-cut on liquid metal (`S4_liquid_halfcut.png`)

At α = 0, the 1M puts the direct beam in one row, and reflected light only in
the rows above it. The direct beam alone gives σ = 8.0 ± 0.3 µm (S1
0.02 mm; FWHM ≈ 19 µm). Only 2 points lie on the edge, so take it as an
upper bound with a coarse σ. **A box round the beam, the scan's own ROI and
the live view of a hand half-cut, is not a knife edge on a liquid:** light
totally reflected by the curved surface keeps 4.4 % of the beam in the box
50 µm past the edge and 2.3 % at 100 µm. The box's 50 % point sits 3.6 µm higher
than the direct beam's. The 70 height scans of that run fail the guards (rise and fall
within about 10 µm of each other), so 30 keV has no spec-only value.
**Low confidence:** one scan, one sample, one energy.

## What the reader should do (no code changed here)

- **`lss_core.dose`: `beam_mm=(width, h)` with h = √(2π)·σ_rise in mm.**
  σ_rise is the median over the run's height scans of the rising-edge erf
  σ, or of `fit_box`'s rising FWHM / 2.355. Use the sample's own scans,
  taken near the burn and with the same S1. When there are none: 0.040 mm
  at 10 keV with S1 ≤ 0.04 mm, uncertain by ±15 % (run-to-run). Quote the
  dose as the **peak** dose per area. The dose averaged over the footprint
  is lower, because the tail spreads a quarter to a third of the photons
  over ±100 µm. The width is not measured here (an earlier image study of
  one run found the beam about 1.05 mm wide between its 5 and 95 % points).
- **F43 (automatic half-cut processing):** run `fit_box` on the sh scan,
  take the rising edge, and refuse it under the guards above (the first
  point above 25 % of the peak; fewer than 2 points on the edge; edges
  closer than 3 σ). Report FWHM_rise and h = 1.064 × FWHM_rise with the
  note "core + tail beam: FWHM of the profile ≈ 0.84 × this; dose height ≈
  1.06 × this".
- **P39 / GID response 'beam':** the profile is not one Gaussian. A
  core + tail with the numbers above is the measured shape. A
  `beam_fwhm_um` of 30–33 µm at 10 keV is the core's FWHM, not the extent.

## What was held back (privacy)

- Any per-scan curve, image or count. S2 shows binned medians of normalised
  fractions, and S4 a single scan normalised and moved to its own edge,
  with no absolute position.
- Run identities: labels R01… only, sorted by class and width. Dates, scan
  numbers, file names, PI and group names, and macro and do-file names are
  not published. The inventory of scans with those keys
  (`sample_data/private/sh_beam/inventory.tsv`, `edges.tsv`,
  `images_*.tsv`) stays private.
- The sample identity of the 30 keV run, beyond "liquid metal".
- Open for the owner: whether the per-class energies in
  `roi_rise_by_run.csv` (to 0.01 keV) narrow a run down too far; if so,
  round them to the class.

## Incidental: OQ-1 (half-openings), read only

The beamline's macro that sets a slit by centre and gap moves s1t to
gap/2 − c and s1b to gap/2 + c. So the header's S1T and S1B are blade
positions from the centre, and **the opening is S1T + S1B**. This is read
from the macro source, not measured. The gaps here use that sum.
