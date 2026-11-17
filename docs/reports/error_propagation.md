# Error propagation in the reduction: what is done now, and a proposal

Written 2026-11-17 at the owner's request: make every error term explicit
and granular, assume no particular noise model (in particular, not
Poisson), and show the present calculation next to the proposed one.

Method: first-order propagation of variances and covariances (the "delta
method"; the general formula is the law of propagation of uncertainty in
JCGM 100:2008, the GUM, §5.2 for correlated inputs — cited from memory).
For a function f of inputs x with covariance matrix V,
var(f) ≈ Σ_jk (∂f/∂x_j)(∂f/∂x_k) V_jk. It is accurate when every relative
uncertainty is small; where it is not (monitor counts below ~100) a ratio
also acquires a bias of order u², which is ignored here.

How things are known in this note: the **present** formulas are read from
the code, with the function named, and are checked by existing tests
(`test_twod_detector.py`, `test_xfntr.py`); the **proposal** is derived here
and has not been built.

---

## 1. The quantities and their error sources

One frame (one detector image, or one MCA spectrum) is taken with one
monitor reading. Symbols:

| Symbol | What | Its uncertainty | Notes |
|---|---|---|---|
| I_i | counts in pixel (or channel) i | σ_i² = var(I_i) | the detector's counting noise, whatever its form: Poisson for an ideal photon counter, but also count-rate (dead-time) correction, flat-field correction, a bad-pixel replacement value |
| c_ij | cov(I_i, I_j), i ≠ j | | 0 for independent pixels; **not** 0 after bad-pixel replacement (the new value is the mean of four neighbours) or charge sharing |
| M | the frame's monitor reading (`Monc`) | σ_M², or relative u_M = σ_M/M | the monitor's own measurement noise only. Real beam variation is not noise: the monitor and the detector both see it, and dividing removes it (measured, `physics_notes.md` 2026-11-16) |
| a = A^n | absorber transmission factor, A per foil (`absfac`), n foils | u_a = σ_a/a | a calibration constant: its error is the same for every frame taken with n foils |
| τ | real/live-time factor (MCA only) | u_τ | one value per spectrum |
| f_k | stitch factor of reflectivity scan k | from the overlap fit | handled by the xmodfit hand-off; listed for completeness |
| ν | normalisation to the plateau below Q_c | from the plateau points | today treated as exact |

Assumptions stated once, so they can be changed: the detector noise, the
monitor noise and the absorber calibration are independent of one
another (cov(I_i, M) = 0, and so on). Anything else is kept general.

The normalised value of one pixel is

    r_i = a · I_i / M          (units: counts per monitor count)

---

## 2. One pixel

Partial derivatives: ∂r_i/∂I_i = a/M, ∂r_i/∂M = −a·I_i/M² = −r_i/M,
∂r_i/∂a = I_i/M = r_i/a. So

    var(r_i) = (a/M)²·σ_i²     +  r_i²·u_M²   +  r_i²·u_a²
               └ counting ┘       └ monitor ┘     └ absorber ┘

or, relative: (σ_r/r)² = (σ_i/I_i)² + u_M² + u_a².

**The term that matters: two pixels of the same frame.** For i ≠ j,

    cov(r_i, r_j) = (a/M)²·c_ij  +  r_i·r_j·u_M²  +  r_i·r_j·u_a²

Even when the pixels' counts are independent (c_ij = 0), their
normalised values are correlated, because both were divided by the same
M and multiplied by the same a. The monitor and absorber parts are
*fully* correlated across the frame.

---

## 3. A region of interest (sum of pixels of one frame)

S = Σ_i I_i over the box; the normalised sum is S_r = Σ_i r_i = a·S/M.
Its variance is the sum of **all** entries of the covariance matrix,
diagonal and off-diagonal:

    var(S_r) = Σ_i Σ_j cov(r_i, r_j)
             = (a/M)²·[ Σ_i σ_i² + Σ_{i≠j} c_ij ]  +  S_r²·u_M²  +  S_r²·u_a²
               └──────── counting ─────────┘         └ monitor ┘   └ absorber ┘

The monitor and absorber terms scale with the square of the **sum**,
S_r², not with the sum of squares Σ r_i².

### What the program does now

Read from `TwoDDetector.openFile`, `peakLocate`, `sumFiles`, `sumROI`:

1. σ_i² = I_i (`errorData = sqrt(imageData)`), also for a pixel replaced
   by the bad-pixel correction (where the true variance is about a
   sixteenth of the sum of its neighbours' variances, and correlated with
   them).
2. Per pixel: var(r_i) = (σ_i²/M² + I_i²/M³)·a².
   The second term is r_i²·(1/M): a monitor term with u_M² = 1/M, i.e.
   Poisson statistics on the monitor reading.
3. Sum over the box: var(S_r) = Σ_i var(r_i) — the diagonal only.

Written in the terms of the general formula:

| Term | General | Now |
|---|---|---|
| counting | (a/M)²·[Σσ_i² + Σ_{i≠j} c_ij] | (a/M)²·Σ I_i (σ_i² = I_i, c_ij = 0) |
| monitor | S_r²·u_M² | **Σ r_i²**·(1/M) |
| absorber | S_r²·u_a² | 0 (not included) |

So two separate things are wrong in the monitor term:

- **the correlation is dropped**: Σ r_i² instead of (Σ r_i)². The ratio
  S_r²/Σ r_i² = S²/Σ I_i² is the "effective number of pixels" the counts
  are spread over (1 for a single bright pixel, N for a flat box of N
  pixels). The monitor term is too small by that factor;
- **u_M² = 1/M is assumed** (Poisson on `Monc`), which the owner says is
  not right: the true photon count behind the monitor is ≳ 10× the
  recorded number, so the true u_M² is ≲ 1/(10M) — smaller.

The two errors pull in opposite directions and partly cancel; the
simulation in `reports/monitor_noise.md` shows today's error bars within
about −13 %/+7 % of the truth on bright points *if* the monitor is at
least 10× quieter than Poisson, and exactly right on faint points where
the counting term dominates. Fixing one without the other makes things
worse (up to 2.3× too large).

### Proposed

    var(S_r) = (a/M)²·[Σ_i σ_i² + Σ_{i≠j} c_ij]  +  S_r²·(u_M² + u_a²)

with each input supplied explicitly by a model that can be measured and
changed: σ_i² from a detector model (default Poisson, I_i, plus whatever
corrections the detector applies), c_ij from what the program itself
does to the image (bad-pixel replacement), u_M from a measured monitor
model, u_a from the absorber calibration.

---

## 4. Background-subtracted signal (reflectivity)

Signal box S, two background boxes L and R, all in the same frame, net
counts N = S − (L + R)/2, normalised N_r = a·N/M. Derivatives:
∂N_r/∂S = a/M, ∂N_r/∂L = ∂N_r/∂R = −a/(2M), ∂N_r/∂M = −N_r/M,
∂N_r/∂a = N_r/a. With σ_S², σ_L², σ_R² the count variances of the three
boxes (each a sum over its pixels as in §3):

    var(N_r) = (a/M)²·[ σ_S² + (σ_L² + σ_R²)/4
                        − cov(S,L) − cov(S,R) + cov(L,R)/2 ]     counting
             + N_r²·u_M²                                            monitor
             + N_r²·u_a²                                            absorber

The boxes do not overlap, so their counts are independent and the three
covariances vanish unless an image correction couples them. The
**monitor term multiplies the net signal**: a background that is
subtracted carries the same monitor error as the signal it is subtracted
from, and the two cancel in the same proportion.

### What the program does now

Read from `pilRefPatchData` → `lss_core.reflectivity.frame_row`
(`peakLocate`, then `sumROI` on the normalised image):

    var_now = Σ_S var(r_i) + [Σ_L var(r_i) + Σ_R var(r_i)]/4
            = (1/M)²·[Σ_S I_i + (Σ_L I_i + Σ_R I_i)/4]                 counting (Poisson)
            + (1/M)·[Σ_S r_i² + (Σ_L r_i² + Σ_R r_i²)/4]               monitor, per pixel

(a = 1 here: reflectivity frames are not multiplied by the absorber
factor; each scan's absorber is absorbed into its stitch factor.)

| Term | Proposed | Now |
|---|---|---|
| counting | (1/M)²·[σ_S² + (σ_L² + σ_R²)/4] | same, with σ² = counts |
| monitor | **N_r²**·u_M² | **Σ_S r_i² + (Σ_L r_i² + Σ_R r_i²)/4**, times 1/M |

At high Q_z (a weak reflected beam over a background) the net N_r can be
much smaller than the box sums, and the correct monitor term is then
negligible; at low Q_z it is the S_r² term of §3.

---

## 5. Several frames at the same point

Frames k = 1…K at the same Q_z (or the "Sum" of selected frames), each
with its own monitor M_k. The frames' monitor readings are independent of
one another; their absorber factor is the same if they used the same n.

Mean of the normalised values, x̄ = (1/K)·Σ_k x_k:

    var(x̄) = (1/K²)·Σ_k [ counting_k + x_k²·u_M,k² ]     independent per frame
           + x̄²·u_a²                                       common to the frames (same n)

**Now** (`TwoDDetector.sumFiles`): var = (1/K²)·Σ_k var(x_k), with each
var(x_k) per pixel as in §3; the absorber term is absent.

A better estimator when the M_k differ: the ratio of sums,
x = a·Σ_k I_k / Σ_k M_k, which weights frames by their monitor; it has the
smallest variance and the smallest bias at low counts
(`reports/monitor_noise.md`, simulated). Its variance is
(a/ΣM)²·Σ_k σ_k² + x²·[Σ_k σ_M,k²/(ΣM)²] + x²·u_a².

---

## 6. Fluorescence (MCA) and other paths

| Path | Quantity | Now | Proposed |
|---|---|---|---|
| MCA channel | y_c = τ·N_c/M | var = τ²·(N_c + N_c²/M)/M² (`normalise_spectrum`): Poisson counts, Poisson monitor, τ exact | τ²/M²·σ_c² + y_c²·(u_M² + u_τ²) |
| MCA window sum | Y = Σ_c y_c | Σ_c var(y_c): diagonal only | (τ/M)²·Σσ_c² + **Y²**·(u_M² + u_τ²) |
| GID burn test | (ΣI)/M | (ΣI)²/M³ + Σσ²/M² (`pilGidBurn`): the correlated form already, with Poisson M | Σσ²/M² + Y²·u_M² |
| GID map, line cuts | pixel values of one frame, summed along a line | diagonal only | as §3; a whole line from one frame shares one monitor term |
| plateau normalisation | R/ν, ν = max of the points below Q_c | ν treated as exact (`normerr=0`) | ν's own error, common to every point: a pure scale error, best left to the fit as an overall scale (as the hand-off does) |

The GID burn test shows the program is not consistent with itself: it
already uses the correlated form there.

---

## 7. Proposal: carry the error budget, not one number

Instead of one σ per value, each reduced value carries a small budget:

| Component | What it holds | How sums combine it |
|---|---|---|
| `count` | variance from counting noise (and c_ij) | adds (in quadrature) |
| `monitor[frame k]` | the amplitude x·u_M,k for this frame | **adds linearly** within frame k, then in quadrature across frames |
| `absorber[n]` | the amplitude x·u_a,n | adds linearly across all frames with n foils |
| `livetime[spectrum]` | x·u_τ | linear within the spectrum |

The total σ is √(count + Σ_labels (amplitude)²). Sums, differences and
averages then come out right automatically, including the cases above,
and the components are what the newer output formats need: the xmodfit
covariance sidecar already expects a counting-only error (`sigma_meas`)
plus correlated multiplicative terms (hand-off §2.6 allows an
absorber-calibration term per scan exactly like this), and ORSO/HDF5
can record the components and the model used (R7).

Steps, none of which changes a legacy file:

1. A "legacy" error mode that reproduces today's numbers exactly (the
   export fixtures keep passing).
2. A monitor model with measured parameters, u_M² = f² + (σ_dark/M)² +
   1/(g·M): f a fractional floor, σ_dark the beam-off scatter, g the
   ratio of true photons to counts. Measure f and g from repeated bright
   frames (direct beam or total reflection, ≥ 10⁷ detector counts per
   frame) before choosing defaults; the beam-off rate (owner: < 1000
   counts/s means beam off) gives σ_dark.
3. The budget in `lss_core` for every path; the window shows the total,
   the outputs carry the components.
4. Detector model for σ_i (Poisson by default) and the bad-pixel
   covariance; absorber calibration with its uncertainty.

What must be decided by the owner before step 3: whether the absorber
uncertainty belongs in the per-point error at all, or only in the
correlated terms of the new outputs (it is a scale error common to all
points of a scan, so a fit that ignores correlations would be misled by
it in the per-point error).
