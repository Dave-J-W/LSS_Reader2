# Error propagation for data that are not patched

Revised 2026-11-17 after the owner's correction: there is no "absorber
error". Absorber ratios are not used as calibration constants; the scale
between scans taken with different absorbers is measured in each patch,
and its uncertainty is the **patching uncertainty**, which is the subject
of the xmodfit hand-off (`handoff/19-lss-reader-covariance-contract.md`)
and is left out here. This note covers everything up to the point where
patching starts: one frame, then sums within a frame, background
subtraction, and several frames at the same point.

How things are known: the **present** formulas are read from the code
(function named) and agree with the existing tests
(`test_twod_detector.py`, `test_xfntr.py`); the **proposal** is derived
here and is not built. No form of noise is assumed: every variance is a
symbol that a measured model fills in.

Method: first-order propagation of variances and covariances. For a
function f of inputs x with covariance matrix V,
var(f) ≈ Σ_j Σ_k (∂f/∂x_j)(∂f/∂x_k) V_jk (the law of propagation of
uncertainty, JCGM 100:2008 "GUM" §5.2; cited from memory). It holds while
relative uncertainties are small; for very small monitor counts (below
~100) a ratio also gains a bias of order u², not treated here.

---

## 1. One frame: the inputs

One frame is one detector image (or one MCA spectrum), taken with one
monitor reading.

| Symbol | Meaning | Uncertainty, as a symbol | Comment |
|---|---|---|---|
| I_i | counts in pixel i | σ_i² = var(I_i) | the detector's noise in whatever form it has: Poisson for an ideal photon counter, modified by count-rate (dead-time) correction, flat-field correction, a replaced bad pixel |
| c_ij | cov(I_i, I_j) for i ≠ j | | 0 for independent pixels. Not 0 after the bad-pixel correction, which replaces a pixel by the mean of its four neighbours, so it is correlated with them |
| M | the monitor reading of the frame (`Monc`) | σ_M², or relative u_M = σ_M / M | the monitor's own **measurement** noise. Real changes of the beam are not noise here: the detector sees them too and the division removes them (measured, `physics_notes.md` 2026-11-16) |

Assumption, stated so that it can be dropped later: the detector's noise
and the monitor's noise are independent, cov(I_i, M) = 0.

The first reduction step is the division by the monitor:

    r_i = I_i / M        (counts per monitor count)

(Where the program also multiplies by a nominal absorber factor A^n, that
factor is a fixed number with no uncertainty attached; it is left out of
the formulas below because a constant factor only rescales value and
error together.)

---

## 2. One pixel

Derivatives: ∂r_i/∂I_i = 1/M and ∂r_i/∂M = −I_i/M² = −r_i/M. So

    var(r_i) = σ_i²/M²       +   r_i²·u_M²
               └ counting ┘      └ monitor ┘

or, relative to the value: (σ_r / r)² = (σ_i / I_i)² + u_M².

### Now

`TwoDDetector.openFile`, then `peakLocate` or `sumFiles`:

    σ_i² = I_i                                     (errorData = sqrt(imageData))
    var(r_i) = I_i/M² + I_i²/M³

| Term | General | Now |
|---|---|---|
| counting | σ_i²/M² | I_i/M²: Poisson counts, also for a replaced bad pixel |
| monitor | r_i²·u_M² | r_i²·(1/M): Poisson statistics on `Monc` (u_M² = 1/M) |

For a single pixel the structure is right; only the two models are
assumed (and the monitor one is not right: the owner estimates the true
photon count behind `Monc` at ≳ 10 times the recorded number, which makes
u_M² ≲ 1/(10M)).

---

## 3. Two pixels of the same frame

For i ≠ j:

    cov(r_i, r_j) = c_ij/M²      +   r_i·r_j·u_M²
                    └ counting ┘     └ monitor ┘

This is the point of the whole note. Even when the counts of two pixels
are independent (c_ij = 0), their normalised values are not: both were
divided by the same M, so an error in M moves them together. The monitor
part of the error is **fully correlated across every pixel of the frame**.

### Now

Not represented: pixel errors are kept as one array of independent
variances, i.e. every cov(r_i, r_j) is taken as 0.

---

## 4. A sum over a box, a line, or an energy window (one frame)

S = Σ_i I_i over the box; normalised S_r = Σ_i r_i = S/M. The variance of
a sum is the sum of every element of the covariance matrix, diagonal and
off-diagonal:

    var(S_r) = Σ_i Σ_j cov(r_i, r_j)
             = [ Σ_i σ_i² + Σ_{i≠j} c_ij ] / M²     +   S_r²·u_M²
               └────────── counting ──────────┘         └ monitor ┘

The monitor term scales with the square of the **sum**.

### Now

`sumROI` (reflectivity boxes), `plotHint`/`plotVint` (line cuts), the MCA
"Sum" (`fluorescence.window_sum`): the per-pixel variances are added,

    var_now(S_r) = Σ_i var(r_i) = Σ_i I_i / M²  +  Σ_i r_i² · (1/M)

| Term | General | Now |
|---|---|---|
| counting | [Σσ_i² + Σ_{i≠j} c_ij]/M² | ΣI_i/M² |
| monitor | **(Σ r_i)²**·u_M² | **Σ r_i²**·(1/M) |

Two separate defects in the monitor term:

1. **The correlation is dropped**: Σ r_i² instead of (Σ r_i)². The ratio
   (Σ r_i)²/Σ r_i² = S²/Σ I_i² is the effective number of pixels the
   counts are spread over (1 if they are all in one pixel, N for a flat
   box of N pixels). The monitor term is too small by that factor.
2. **u_M² = 1/M is assumed**, which is too large if the monitor is
   quieter than Poisson.

They pull in opposite directions. Simulated (`reports/monitor_noise.md`):
today's total σ is within about −13 %/+7 % of the truth on bright points
if the monitor is at least 10× quieter than Poisson, and right on faint
points where counting dominates; correcting only (1) would make bright
points' errors up to 2.3× too large.

---

## 5. Background-subtracted signal (one frame)

Signal box S and two background boxes L and R in the same frame. Net
counts N = S − (L + R)/2, normalised N_r = N/M. Derivatives:
∂N_r/∂S = 1/M, ∂N_r/∂L = ∂N_r/∂R = −1/(2M), ∂N_r/∂M = −N_r/M. With σ_S²,
σ_L², σ_R² the count variances of the boxes (each a box sum as in §4):

    var(N_r) = [ σ_S² + (σ_L² + σ_R²)/4
                 − cov(S,L) − cov(S,R) + cov(L,R)/2 ] / M²     counting
             + N_r²·u_M²                                          monitor

The boxes do not overlap, so the three covariances are 0 unless an image
correction reaches across a box edge (the bad-pixel replacement can).

The monitor term multiplies the **net** signal: the background and the
signal were divided by the same M, so the subtraction cancels their
monitor errors in the same proportion as their values.

### Now

`lss_core.reflectivity.frame_row` (`peakLocate`, then `sumROI` on the
normalised image):

    var_now(N_r) = [Σ_S I_i + (Σ_L I_i + Σ_R I_i)/4] / M²
                 + [Σ_S r_i² + (Σ_L r_i² + Σ_R r_i²)/4] · (1/M)

| Term | General | Now |
|---|---|---|
| counting | [σ_S² + (σ_L²+σ_R²)/4 − covariances]/M² | same, with σ² = counts and no covariances |
| monitor | **N_r²**·u_M² | **Σ_S r_i² + (Σ_L r_i² + Σ_R r_i²)/4**, times 1/M |

At high Q_z, where a weak reflection sits on a background, N_r is much
smaller than the box sums and the correct monitor term is negligible; at
low Q_z the background is small and §4 applies.

---

## 6. Several frames at the same point

Frames k = 1 … K at the same position (repeated exposures, or the "Sum"
of selected frames), each with its own monitor reading M_k. The monitor
readings of different frames are independent, so here — and only here —
monitor errors do add in quadrature.

**Mean of the normalised values**, x̄ = (1/K)·Σ_k x_k, with x_k a pixel,
box or net value of frame k:

    var(x̄) = (1/K²)·Σ_k [ counting_k  +  x_k²·u_M,k² ]

**Ratio of sums**, x = Σ_k I_k / Σ_k M_k (counts of all frames over the
total monitor):

    var(x) = Σ_k σ_k² / (Σ_k M_k)²  +  x² · Σ_k σ_M,k² / (Σ_k M_k)²

When the M_k differ, the ratio of sums weights each frame by its monitor;
it has the smaller variance and the smaller bias at low counts
(simulated, `reports/monitor_noise.md`: 1.55× less scatter for a 16×
spread of M; bias +0.7 % against +3.6 % at M ≈ 30).

### Now

`TwoDDetector.sumFiles` and the cut "Sum": the mean of normalised frames,
var = (1/K²)·Σ_k var(x_k), with each var(x_k) per pixel as in §2. Across
frames this is the right structure; it inherits §4's defects as soon as
pixels are summed.

---

## 7. Fluorescence spectra (one spectrum)

Channel counts N_c, monitor M, real/live-time factor τ (one per
spectrum, with relative uncertainty u_τ if it has one): y_c = τ·N_c / M.

    var(y_c)         = τ²·σ_c²/M²  +  y_c²·(u_M² + u_τ²)
    cov(y_c, y_c')   = τ²·c_cc'/M² +  y_c·y_c'·(u_M² + u_τ²)
    var(Σ_window y)  = τ²·[Σσ_c² + Σ c_cc']/M²  +  Y²·(u_M² + u_τ²),   Y = Σ y_c

**Now** (`fluorescence.normalise_spectrum`, `window_sum`):
var(y_c) = τ²·(N_c + N_c²/M)/M², summed over the window channel by
channel: Poisson counts, Poisson monitor, τ exact, correlation dropped.

---

## 8. Where the program already does it the correct way

The GID burn test (`pilGidBurn`, intensity mode) computes
var = Σσ_i²/M² + (Σ I_i)²/M³: the monitor term on the squared **sum**,
as in §4 (with Poisson u_M). The program is not consistent with itself.

---

## 9. Proposal for non-patched data

Carry, with every reduced value, the parts of its variance separately:

| Part | Meaning | Rule when values are added |
|---|---|---|
| counting | Σσ²/M² (+ covariances) | variances add |
| monitor of frame k | amplitude x·u_M,k | amplitudes of the same frame add **linearly**; different frames' add in quadrature |
| live time of spectrum s | amplitude y·u_τ,s | linearly within the spectrum |

Total σ = √(counting + Σ (amplitudes per frame or spectrum)²). Every case
above (box, line, window, background subtraction, frame averages) then
follows from the same two rules.

These parts are also what patching needs as input: the hand-off's
counting-only error (`sigma_meas`) is the counting part, and the monitor
part becomes one more input to the patching uncertainty.

Steps, none of which changes a legacy output file:

1. A "legacy" mode that reproduces today's numbers exactly.
2. A monitor model whose parameters are measured, not assumed:
   u_M² = f² + (σ_dark/M)² + 1/(g·M), with f a fractional floor, σ_dark the
   beam-off scatter (owner: rates below 1000 counts/s mean beam off), g
   the number of true photons per recorded count. f and g from repeated
   bright, steady frames (direct beam or total reflection, ≥ 10⁷ detector
   counts per frame).
3. A detector model for σ_i (Poisson as the default, plus the
   corrections the detector applies) and the covariance introduced by the
   bad-pixel replacement.
4. The parts carried through every non-patched path in `lss_core`; the
   window shows the total, new output formats record the parts and the
   models used (R7).
