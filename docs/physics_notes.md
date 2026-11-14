# Physics notes and Q&A log

Running record of questions asked during the work on this fork and the answers
given, with emphasis on invariant quantities. Newest entries at the bottom.
Each entry says whether the answer was verified (by test, by running, or by
reading only).

## Invariants

Collected here as they are established; each should point to a test once one
exists.

| # | Invariant | Status |
|---|---|---|
| I1 | Fresnel reflectivity R_F(q) = 1 for q ≤ q_c | tested: `test_fresnel.py` |
| I2 | R_F(q) → (q_c / 2q)⁴ for q ≫ q_c, and R_F depends only on q/q_c | tested: `test_fresnel.py` |
| I3 | Monitor-normalised intensity I/M has σ² = σ_I²/M² + I²/M³; for Poisson I, (σ/R)² = 1/I + 1/M | tested: `test_twod_detector.py` |
| I4 | Background-subtracted ROI signal S − (L+R)/2 is 0 on a flat image; σ² = σ_S² + (σ_L² + σ_R²)/4 | zero-on-flat tested; error formula read from code only |
| I5 | Normalised GID footprint area lies in (0, 1], is 1 at small 2θ and falls once clipped | tested: `test_gid_area.py` |
| I6 | At the direct-beam row with α = α_true, Q_z = 4π sin α / λ; at the direct-beam column with Det_Th = 0, Q_xy = 0 and the axis is antisymmetric | tested: `test_twod_detector.py` |
| I7 | Stitching two scans of one curve recovers the attenuation factor exactly, and overlap errors fall by √2, when the overlap points coincide | tested: `test_stitching.py` |
| I8 | Reduced reflectivity of each scan is proportional to the true curve (R/R_F flat) | tested end to end on synthetic data: `test_gui_workflows.py` |
| I9 | Footprint fraction is the same at +2θ and −2θ for symmetric slits | **violated** by 2 % at 20°; pinned as expected failure in `test_gid_area.py` |

## Q&A

### 2026-11-14 — What is in LSS_Reader and what state is it in?

**Q.** Familiarise with the repository ahead of verification tests, debugging,
refactoring, new features and GUI reorganisation.

**A.** See [ASSESSMENT.md](ASSESSMENT.md). In short: a single 5400-line Qt
class holds the GUI and all physics; there are no tests; 18 defects were found
by reading, of which the most serious for users on current SciPy is that GID
multi-scan patching depends on the removed `interp2d`. The physics that tests
must preserve is tabulated in section 2 of the assessment.

Verification: source read; app launched headless; defects not yet reproduced.

### 2026-11-14 — Test scaffolding; what did the first tests find?

**Q.** Set up test scaffolding. Known pain points: the Python 2 → 3 move was
incomplete, and the interface should never crash whatever files are selected
and whatever buttons are pressed afterwards.

**A.** See [TESTING.md](TESTING.md). The fast suite has 47 passing tests and
8 strict expected failures. All of the following were measured by running the
code on synthetic data (`tests/synth.py`), not on beamline files.

Numerical findings:

- **Stitching bias.** When the second scan has no point at a Q_z of the first
  scan's overlap region, `oneDjoin` interpolates it with a cubic spline in
  linear intensity. On a Fresnel-like curve with overlap 0.04–0.05 Å⁻¹ and a
  true factor of 1.420 it returns 1.4037 (sum mode) or 1.4013 (weighted-fit
  mode), 1.2–1.3 % low, and every point beyond the overlap inherits that. The
  reported relative error there grows from 0.1 % to 1.3 %. With coincident
  points the factor is exact to 1e-12. Interpolating log R instead is the
  obvious candidate fix; not yet tried.
- **Footprint asymmetry.** `calArea` gives 0.7355 at 2θ = +20° and 0.7218 at
  −20° for symmetric slits (invariant I9).
- **"FWHM" in the SpecPlot title.** For a Gaussian of true FWHM 0.471 the
  title reports 0.406, because the tanh-edged box model is tried first and
  its width is what gets printed.
- **ROI clipping.** The default reflectivity ROI (11 pixels across) collects
  99.4 % of a σ = 2 pixel Gaussian. This is a constant factor, so it cancels
  in normalised reflectivity as long as the beam shape on the detector does
  not change with Q_z.
- End to end, the normalised stitched reflectivity of the synthetic data
  stays within 2 % of the generating curve; the whole shortfall is the
  stitching bias above.

Crash findings are in `tests/known_crashes.json`; see the next entry.
