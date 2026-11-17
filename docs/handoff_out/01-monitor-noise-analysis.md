# Hand-off: how noisy is the monitor `Monc`, and what shape is its noise?

**Answered 2026-11-17 (owner):** Gaussian, σ = 0.04 % constant across
counting level, is the default. Option: σ_scan · w · t₄ with w ≈ 0.94
(0.86–1.01) and σ_scan the scan's own scatter (0.039 % if unknown), an
upper bound. Both for the present SR570 + V2F electronics. Built:
`lss_core/errors.py`.

Written 2026-11-17 by the LSS_Reader2 agent, for an agent analysing the
owner's real data. Self-contained: you do not need the LSS_Reader2
repository. Return the deliverables in §6; nothing else is needed back.

## 1. Why this is needed

LSS_Reader divides every detector frame by the reading of the monitor
`Monc` taken during that frame (r = I / M). The program is being changed
so that the monitor's uncertainty is applied to the **whole** sum of a
region of interest (box, line, energy window, background-subtracted net
signal) of one frame, not pixel by pixel:

    var(S/M) = [counting variance of S] / M²  +  (S/M)² · u_M²

with u_M the relative uncertainty of the monitor reading of that frame.
Frames have independent monitor errors, so across frames the monitor
terms add in quadrature. Derivation: first-order propagation, JCGM 100:2008
(GUM) §5.2, <https://www.bipm.org/en/doi/10.59161/JCGM100-2008E>.

What is still unknown is **u_M**, and whether a Gaussian of width u_M is
an adequate description. The owner's observation: a Gaussian of
σ = 0.136 % contains 99 % of `Monc`'s scatter but overstates a typical
point's uncertainty about 3 times. That is the signature of a heavy-tailed
distribution (for a Gaussian, the σ that covers 99 % *is* the typical σ).

The question to answer: **should the reader model the monitor's
measurement error as a Gaussian with a width that depends on the
conditions (count time, rate), as a Gaussian plus flagged outliers, or as
a heavy-tailed distribution?** And with what parameters.

## 2. The trap: scatter is not noise

Not all of `Monc`'s frame-to-frame scatter is measurement error. `Monc`
sits downstream of the S1 slits; the flux through S1 really changes from
frame to frame (beam position, top-up injections, optics), and the
detector sees the same change. Dividing by `Monc` removes it. Only the
part of `Monc`'s scatter that the detector does **not** share is
uncertainty in the reduced data.

Evidence so far (two reflectivity scans of a public data set, 21–27
points each): the detector's ROI counts fluctuate with `Monc`
(correlation +0.5 to +0.7); after dividing by `Monc` the detector's
relative scatter falls to its own Poisson limit. `Monp` (upstream of S1)
does not share `Monc`'s scatter (correlation −0.66 to +0.45, no consistent
sign). So `Monc`'s observed scatter (2–7×10⁻³ per frame in 1–2 s frames)
is mostly real flux; its own noise is bounded only roughly, ≲ 1–2×10⁻³.

The analysis must therefore use the **detector as a witness**.

Also measured on the small sample (pooled raw `Monc` scatter about a
quadratic trend, 1124 frames, 54 steady beam-on scans) — for comparison
with your larger set, not as an answer:

| Quantity | Value |
|---|---|
| standard deviation of relative deviations | 8.1×10⁻³ |
| robust σ (1.4826 × median absolute deviation) | 2.7×10⁻³ |
| excess kurtosis (Gaussian: 0) | 9.2 |
| best fit by AIC | Student t, ν ≈ 1.9 (then Laplace; Gaussian worst) |
| after standardising each scan by its own robust σ | kurtosis 2.3; 2.8 % beyond 2.576σ (Gaussian 1 %); 0.44 % beyond 4σ (Gaussian 0.006 %) |
| a scan's spread against its monitor count per frame | σ ∝ M^−0.52 |
| spread / √(1/M) | median 1.7 (0.06 to 4.2) |
| lag-1 autocorrelation within scans | median 0.08 (independent from frame to frame) |

So part of the pooled tail comes from mixing scans of different widths
(width falls with M like counting noise), part is within-scan jumps. Which
of the jumps the detector shares is not known.

## 3. Data to select

SPEC files from ChemMatCARS 15-ID-C. Columns of interest in each scan's
`#L` line: `Seconds` (count time t), `Monc`, `Monp`, `Epoch` (seconds
since the file's `#E` epoch), and the detector ROI column (`Pilatus`, or
`Pil300K`, `Pilatus1M`, depending on the detector in use; take the one with
counts). Some files list a column name twice (`Monc Monc`); take the
first. A rate below 1000 counts/s on a monitor means the beam is off.

In order of value:

1. **Repeated frames at fixed geometry with a bright, steady detector
   signal** — attenuated direct beam, or below the critical angle (total
   reflection), time scans / repeated counts, ≥ 10⁶ (better 10⁷) detector
   counts per frame. Here every frame should see the same flux fraction,
   so `D/M` scatters only by the detector's counting noise plus the
   monitor's noise. This is the clean measurement. As many count times and
   monitor rates as exist.
2. **Any scan where the detector ROI has ≥ 2×10⁴ counts per frame and
   varies slowly from point to point** (reflectivity at low Q_z,
   alignment scans on a broad peak, rod scans). Usable with the
   second-difference method in §4.
3. **Beam-off stretches** (rate < 1000 counts/s): dark-rate scatter of
   `Monc` and `Monp`.
4. Everything else steady and beam-on, for the raw scatter statistics as
   in the table above (to compare with the owner's 0.136 % figure).

Record for every scan used: an anonymous file id, scan number, scan
command (first word is enough), count time, detector, number of frames
used, beam energy if in the header, and date.

## 4. Method

Notation per frame k: D_k detector ROI counts, M_k `Monc` counts, P_k
`Monp`, t_k count time.

**4.1 Witness residual.** For data of kind 1, x_k = log(D_k/M_k) − mean.
For kind 2, remove the smooth curve without fitting it, by second
differences along the scan:

    d2(y)_k = log y_{k−1} − 2 log y_k + log y_{k+1}

For independent relative noise of size u per frame, var(d2) = 6u². The
Poisson part of d2(D) has variance 1/D_{k−1} + 4/D_k + 1/D_{k+1}. Use only
frames whose own and both neighbours' D ≥ 2×10⁴. Kind-2 scans with
structure (critical edge, Kiessig fringes, Bragg peaks) give large d2 of
D that no monitor explains; exclude regions where |d2(D/M)| is far above
Poisson in runs of several points, and say how many frames that removed.

**4.2 The monitor's own noise.** Per frame, the residual of D/M beyond the
detector's Poisson variance is the monitor's measurement noise plus any
detector excess:

    u_M² + u_D,excess²  =  var(x) − mean(1/D)        (kind 1)
                        =  [mean(d2(D/M)²) − mean(Poisson var of d2(D))] / 6   (kind 2)

This is an upper bound on u_M². Report it per scan with its statistical
uncertainty (bootstrap over frames, or the χ² interval).

**4.3 Shared or not.** Per scan, the slope of x (or d2(D)) against the
monitor's own deviation (or d2(M)): 1 means the detector follows the
monitor (scatter is flux), 0 means it does not (scatter is monitor
error). Same for `Monp`. For the largest `Monc` jumps (top 2 % of
|deviation| pooled, and every frame beyond 4 robust σ), list whether D
followed: |d2(D/M)| / Poisson σ of d2(D), against |d2(D)| / Poisson σ.

**4.4 Shape of the monitor's noise.** On the witness residuals (not on
raw `Monc` scatter), standardised per scan by the expected σ (detector
Poisson combined with the fitted u_M), report: excess kurtosis,
fraction beyond 2.576σ and 4σ, a Q–Q plot against a Gaussian, and maximum
likelihood fits of Gaussian, Student t (report ν), Laplace, and a
Gaussian-plus-outlier mixture (report outlier fraction and width), with
AIC. If ν comes out below 4, check whether a scale mixture by conditions
(count time, rate, date) explains it before calling it heavy-tailed.

**4.5 Model of the width.** Fit, over scans/conditions,

    u_M² = f² + (σ_dark / M)² + 1 / (g·M)

f: fractional floor; σ_dark: beam-off scatter of `Monc` per frame (from
kind-3 data, in counts, scaled to the count time); g: effective number of
quanta per recorded count (g = 1: Poisson on the counts; the owner
estimates the true photon number behind `Monc` at ≳ 10× the recorded
count). Report f, g, σ_dark with uncertainties, and whether the fit
needs a dependence on count time beyond M.

**4.6 Outlier events.** For frames that are outliers in the witness
residual: their rate per hour of beam, whether they are single frames or
steps (persisting over the following frames), and whether they coincide
with storage-ring top-up injections (APS top-up injects roughly every
1–2 minutes; use `Epoch` spacing and any ring-current column if present).
Also whether the detector's counts are the outlier rather than the
monitor (a Pilatus glitch looks the same in D/M).

**4.7 For comparison with the owner's figure.** The raw `Monc` scatter
statistics of §2's table on the large set, and the σ of a Gaussian that
contains 99 % of the raw scatter versus the robust σ.

## 5. What would decide the question

| Finding | Model the reader should use |
|---|---|
| Witness residuals Gaussian (kurtosis ≲ 0.5, tail fractions near 1 % and 0.006 %) once the width model of §4.5 is applied | Gaussian, u_M from the fitted model per frame |
| Gaussian core plus rare isolated jumps the detector does not share | Gaussian u_M, plus a rule that flags frames (threshold in robust σ of the scan, with the rate of false flags) |
| Jumps that the detector does share | nothing to model: normalisation removes them |
| Heavy tails that persist within homogeneous conditions | a stated heavy-tailed model (ν, or mixture fraction and width) and its consequence for error bars |

## 6. Deliverables

1. A short report (Markdown): data used (§3, anonymised ids), the answers
   to §4.2–4.7, the decision per §5, and what could not be determined.
   Keep measured results and things only read or assumed apart.
2. `monitor_noise_summary.json`:

        {
          "u_M_model": {"f": ..., "f_err": ..., "g": ..., "g_err": ...,
                        "sigma_dark_counts_per_s": ..., "valid_M_range": [lo, hi],
                        "valid_t_range_s": [lo, hi]},
          "shape": {"excess_kurtosis": ..., "frac_beyond_2p576": ...,
                    "frac_beyond_4": ..., "student_t_nu": ...,
                    "mixture": {"outlier_fraction": ..., "outlier_sigma_ratio": ...},
                    "aic": {"gaussian": ..., "student_t": ..., "laplace": ..., "mixture": ...}},
          "outliers": {"rate_per_hour": ..., "shared_with_detector_fraction": ...,
                       "flag_threshold_sigma": ..., "false_flag_rate": ...},
          "raw_scatter": {"robust_sigma": ..., "sigma_99pct_gaussian": ..., "kurtosis": ...},
          "recommendation": "gaussian" | "gaussian+flags" | "heavy_tailed",
          "n_frames": ..., "n_scans": ...
        }

3. `monitor_witness_frames.csv`, one row per frame used: `file_id, scan,
   point, kind, t_s, epoch_s, M, P, D, x_or_d2_DM, d2_M, d2_D,
   poisson_var, flagged`. Anonymous ids only; no sample names. The owner
   decides whether this file may be committed to the public fork.

The scripts used, if any, are welcome as well.
