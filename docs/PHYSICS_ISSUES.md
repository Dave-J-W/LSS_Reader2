# Physics and mathematics issues

One list of the places where what the program computes is, or may be, not
what it should compute. Kept apart from crashes and plumbing defects
(`ASSESSMENT.md`). Each entry says how it is known (measured by a test,
or read from code only) and what is pinned. Nothing here is fixed yet; in
the current phase issues are recorded and pinned, not repaired.

"Pinned" means a test freezes today's behaviour so a later fix is a
deliberate, visible change. Where the output feeds the legacy export
(`tests/reference/legacy_export/`), a fix must go into the corrected chain
only (see `handoff/19-lss-reader-covariance-contract.md`).

| # | Issue | Size of effect | How known | Pinned by | Status |
|---|---|---|---|---|---|
| P1 | **Stitch factor biased when overlap points do not coincide.** The new scan is interpolated with a cubic spline in linear intensity; on a steeply falling curve the spline reads high, so the factor is low. | 1.2–1.3 % low in the synthetic case; exact when points coincide. Not yet measured on real overlaps. | measured | `test_stitching.py` | Owner: experiments ensure shared Q_z for now; **to be remedied later, do not forget** (D13). |
| P2 | **Monitor noise treated as independent per pixel.** Each pixel gets I/M² + I²/M³ and ROI or window sums add in quadrature, although all pixels of a frame share one monitor reading. | Error too small: ×1.4 (flat ROI), ×6.5 (synthetic bright peak), about ×1.7 at the first point of real NX school scan 6. | measured | `test_twod_detector.py`, `test_xfntr.py` | Investigated: `reports/monitor_noise.md`. P2 and P3 partly cancel and must be fixed together; with a monitor ≥ 10× quieter than Poisson today's errors are within −13 % / +7 % on the brightest points. Note: the GID burn test already applies the monitor term once to the summed signal, so the program is inconsistent with itself. |
| P3 | **Poisson statistics assumed for the monitor.** `Monc` is an amplified ion-chamber current through a counter, not a photon count; true incident photons are probably > 10× the counts (owner). | Measured on NX school data: `Monp` scatters at 0.2–0.5 of √counts, `Monc` at 0.6 in the best scan; a fractional floor of 3×10⁻⁴ to 10⁻³ fits better than 1/M. Most of `Monc`'s larger scatter in reflectivity scans (0.2–0.5 %) is real flux variation through S1 that the detector also sees (measured 2026-11-16), not monitor noise. | measured; owner confirms | — | In scope (F26); proposed model u_M² = f² + 1/(g·M), parameters to be measured. |
| P4 | **Stitch-factor uncertainty folded into per-point errors** as if independent point to point; later scans do not inherit earlier factors' uncertainty. | Fits overconfident (hand-off: a roughness pull with SD 5.3 instead of 1). | hand-off; read | legacy fixtures | F24 specifies the remedy. |
| P5 | **Footprint correction not symmetric in ±2θ.** | 0.7355 at +20°, 0.7218 at −20° (2 %). | measured | `test_gid_area.py` (expected failure) | Open; is 2θ ever negative? |
| P6 | **Image axes and line cuts use different geometry.** Image axes use pixel·size/distance (small angle); cuts use arctan. | Grows with angle; not yet quantified. | read | — | Open; which one is the reference? |
| P7 | **MCA "Merge" weighted mean** is Σ(y²/σ²)/Σ(y/σ²), not Σ(y/σ²)/Σ(1/σ²); they agree only for equal values. | Depends on the spread of the merged values. | measured | `test_xfntr.py` | Owner: on this list (D16). |
| P8 | **MCA window-sum error** adds per-channel monitor terms in quadrature (same as P2). | See P2. | measured | `test_xfntr.py` | With P2. |
| P9 | **SpecPlot "FWHM"** is the width of a tanh-edged box model tried before the Gaussian. | 0.406 reported for a Gaussian of FWHM 0.471 (−14 %). | measured | `test_gui_workflows.py` | Open. |
| P10 | **Q limits of a cut are truncated toward the beam centre** (`int()`), not rounded. | Window can lose a pixel on a side. | measured | `test_gui_cuts.py` | Open. |
| P11 | **Pixel cut ranges include one row/column more than typed.** | One extra row or column. | measured | `test_gui_cuts.py` | Open; may be intended. |
| P12 | **Reflectivity ROI is 2 pixels smaller per dimension than typed** (`sumROI` subtracts 2), and clips the beam tails. | 99.4 % of a σ = 2 px Gaussian collected with the default ROI; constant if the beam shape is constant. | measured | `test_twod_detector.py`, `test_gui_workflows.py` | Open; may be intended. |
| P13 | **`pil_S1v = S1T + S1T`** (top slit counted twice) feeds the GID footprint. | Wrong whenever top ≠ bottom. | read | — | Open (defect 10). |
| P14 | **First high-Q_z GID frame of each scan not rescaled by the average monitor**, unlike all other frames. | A factor of the average monitor on that frame. | read | — | Open (defect 11); GID sub-project F23. |
| P15 | **High-Q_z GID data indexed with the medium-Q_z keys.** | Wrong scan used. | read | — | Open (defect 12); F23. |
| P16 | **Bad-pixel correction**: threshold factor used for detection but not for replacement; GUI value never passed in. Gaps would corrupt neighbours (D11). | Case dependent. | measured (factor), read (gaps) | `test_known_defects.py` | Open. |
| P17 | **Absorber-ratio fit curve drawn with the initial guess** in its dead-time term. | Display only. | read | — | Open (defect 13). |
| P18 | **Low-Q_z slit override** (height forced to 5 for 0.02 < Q_z < 0.03) ignores its check box for the first frame of each scan. | Changes the ROI for those frames. | read | — | Open (defect 15). |
| P19 | **Fresnel curve has no absorption term** and R_F is exactly 1 below Q_c. | Small near Q_c for light liquids; larger for heavy subphases. | read; tested as coded | `test_fresnel.py` | Open; may be intended for R/R_F display. |
| P20 | **Peak-fit area for MCA** is intensity × width with error from those two only (no covariance, no √(2π) factor). | Area is in units of height × σ; relative values across frames are unaffected. | measured | `test_xfntr.py` | Open; benchmarked. |

| P21 | **Possible unsubtracted monitor dark offset.** Beam-off scans show `Monc` ≈ 100 counts/s and `Monp` ≈ 42 counts/s. | 0.03–0.12 % of typical monitor counts. | measured (NX school scans 1–3); owner confirms that rates below 1000 counts/s are beam-off | — | Open: subtract a dark rate? |
| P22 | **A missing image shifted the normalisation of every later frame** (fixed 2026-11-17). The monitor list held one value per SPEC point while the image list skipped missing images; and the j-th image file found was paired with point j. | Measured on synthetic data: with image 1 of scan 1 missing, scan 2's first frame was normalised with scan 1's monitor (a factor 3 in the test) and scan 1's image 2 was given point 1's Q_z. | measured | `tests/test_graceful_opening.py` | Fixed: frames matched to files by the number in the file name; per-frame lists kept aligned. No change for complete data sets (all benchmarks unchanged). |
| P23 | **Line/area cuts of Pilatus frames are not monitor-normalised.** The cut code passes the frames as loaded (raw counts) to the integration with no monitor, so per-frame cuts are counts, and "Sum" averages raw counts of frames taken with different monitor counts and absorbers. Only when background images are subtracted are the frames normalised first. | Cuts of different frames are not comparable when monitor or absorber differ; summed cuts are weighted by whatever flux each frame had. | read; consistent with `test_gui_cuts.py` (cut equals the raw pixel sums) | `test_gui_cuts.py` | **Fixed 2026-11-17** (owner: cuts should be normalised): frames are divided by monitor and multiplied by the absorber factor before cutting, with the same arithmetic as everywhere else (`lss_core/normalise.py`). Cut values change from counts to counts per monitor count. |

Related but not physics: NumPy 2 formatting in outputs (D14), library drift
(`interp2d`), listed in `ASSESSMENT.md`.
