"""Beam damage or a sample changing by itself? (F76, owner 2026-11-23:
"some reduction analysis of the various absorber burn tests … would help
decide if sample is changing or xray beam is damaging sample").

**The idea** (physics_notes 2026-11-23, "Damage or a changing sample"): a
change caused by the beam follows the dose, flux × time; a sample changing
by itself follows the clock. Across burns of one kind of sample at
different absorbers (different fluxes φ), the drift rate against time then
scales as

    rate_b = k · φ_b^β,     β = 1: the dose;  β = 0: time.

This is the convention of the real-burn study (DATA_NEEDS row 11,
COMPARISONS C54), so the reader and that study speak the same language.
It rests on **reciprocity** (the Bunsen–Roscoe law of photochemistry): the
same dose gives the same change whatever the rate. It fails through
dose-rate effects (β ≠ 1: thresholds, a fast and a slow process; C54 found
β > 1 in 4 of its 8 decided series) and, at a liquid surface, through
molecules exchanging into the illuminated footprint. A burn's flux is its
dose over its duration (``lss_core.dose``): a comparison is meaningful
between burns at one energy and gain, where the dose's common scale
cancels.

**Two stages.**

1. Each burn's drift rate, per second: for intensity and width the slope
   of a weighted straight line through ln y (an exponential change's rate
   exactly; for a small linear change, its relative slope), for a position
   the slope of y itself; the errors scaled up by √(χ²/dof) when that
   exceeds 1 (the burn's own scatter, as the GID trends do). A straight
   line through y itself reads a large exponential fall's rate low, the
   more so the faster it falls, which biases β low (seen in the tests).
2. Across burns: rate_b = k φ_b^β by weighted least squares, with k fitted
   for every β on a grid (β profiled), errors σ_b² + τ², τ the **strip
   scatter**: how much the rate differs between two strips of one sample at
   one flux beyond counting (C54 measured 88 %/h on real reflectivity
   burns). Leaving τ out when it is real makes the pure models fail too
   often (C54: 8 of 19 series "neither" with counting errors alone).

**The verdict** (``Verdict.verdict``), as C54 decides it:

- ``'no change'``: no burn drifts by ``significance`` (3) σ: nothing to
  compare;
- ``'opposite signs'``: one burn rises and another falls by 3σ: no single
  power law;
- ``'dose'``: β = 1 passes (χ² with n − 1 degrees of freedom, p ≥ 0.05)
  and β = 0 fails; ``'time'``: the reverse; ``'cannot tell'``: both pass;
  ``'neither'``: both fail (β̂ says where, e.g. β > 1).

How strongly: β̂ with its intervals (Δχ² = 1 and 3.84) and the Akaike
weight of β = 1 against β = 0 (``weight_dose``; both models have one free
parameter, so the weight is exp(−χ²₁/2) / (exp(−χ²₁/2) + exp(−χ²₀/2))).
"""
import math
from dataclasses import dataclass, field

import numpy as np

BETA_GRID = np.round(np.arange(-1.0, 4.0 + 1e-9, 0.01), 4)
SIGNIFICANCE = 3.0
ALPHA = 0.05
VERDICTS = ('dose', 'time', 'cannot tell', 'neither', 'no change', 'opposite signs')
RELATIVE = {'intensity': True, 'fwhm': True, 'centre': False}


@dataclass
class Burn:
    """One burn as the test needs it: ``t`` (s, from the start), the quantity
    ``y`` with errors ``sigma``, the burn's flux (dose per second, in a unit
    common to the burns compared), whether its change is ``relative``
    (intensity, width) or additive (a position), and a ``label``."""
    t: np.ndarray
    y: np.ndarray
    sigma: np.ndarray
    flux: float
    relative: bool = True
    label: str = ''


def from_result(res, quantity='intensity', drop_first=False):
    """A ``Burn`` from a ``burn.BurnResult`` (its time axis, its dose: the
    flux is its dose over its duration). ``drop_first``: leave the first
    frame out (C54 does: the first frame is sometimes low)."""
    if res.dose_total is None or not res.duration() > 0:
        raise ValueError('scan %s: its dose is not known (%s)' % (res.scan, '; '.join(res.dose_notes) or 'no dose'))
    y, s = res.values[quantity]
    t, y, s = np.asarray(res.t, float), np.asarray(y, float), np.asarray(s, float)
    if drop_first:
        t, y, s = t[1:], y[1:], s[1:]
    flux = float(res.dose_total) * float(res.dose_scale) / res.duration()
    return Burn(t, y, s, flux, RELATIVE.get(quantity, True), 'scan %s' % res.scan)


def drift_rate(b):
    """(rate, σ) of one burn, per second: for a relative quantity the slope
    of a weighted straight line through ln y (the rate of an exponential
    change exactly, and the relative slope of a small linear one), for an
    additive one the slope of y itself; σ scaled by √(χ²/dof) when that
    exceeds 1."""
    t, y, s = (np.asarray(v, float) for v in (b.t, b.y, b.sigma))
    good = np.isfinite(t) & np.isfinite(y) & np.isfinite(s) & (s > 0)
    if b.relative:
        good &= y > 0
    t, y, s = t[good], y[good], s[good]
    if len(t) < 3:
        return math.nan, math.nan
    if b.relative:                                         # ln y, σ/y
        y, s = np.log(y), s / y
    A = np.column_stack([np.ones_like(t), t]) / s[:, None]
    coef, *_ = np.linalg.lstsq(A, y / s, rcond=None)
    cov = np.linalg.inv(A.T @ A)
    chi2 = float(np.sum((y - (coef[0] + coef[1] * t)) ** 2 / s ** 2))
    cov = cov * max(1.0, chi2 / max(len(t) - 2, 1))
    return float(coef[1]), float(math.sqrt(cov[1, 1]))


@dataclass
class Verdict:
    verdict: str
    beta: float
    beta_ci: tuple                 # Δχ² = 1 (about 68 %); an open end is the grid's edge
    beta_ci95: tuple               # Δχ² = 3.84
    weight_dose: float             # Akaike weight of β = 1 against β = 0
    p_dose: float                  # β = 1 fixed, k fitted: χ² with n − 1 dof
    p_time: float
    k: float                       # the rate at the burns' geometric-mean flux, at β̂
    rates: list                    # (label, flux, rate, σ) per burn
    strip_scatter: float
    note: str = ''
    grid: np.ndarray = None
    chi2: np.ndarray = None

    def summary(self):
        return self.note


def _profile(phi, r, s, grid):
    """χ²(β) with k fitted at every β (closed form), and k(β)."""
    x = phi[None, :] ** grid[:, None]
    w = 1.0 / s ** 2
    k = np.sum(w * x * r, axis=1) / np.sum(w * x * x, axis=1)
    chi2 = np.sum(w * (r - k[:, None] * x) ** 2, axis=1)
    return chi2, k


def _interval(grid, chi2, level):
    ok = chi2 <= chi2.min() + level
    idx = np.flatnonzero(ok)
    return float(grid[idx[0]]), float(grid[idx[-1]])


def _p(chi2, dof):
    from scipy.stats import chi2 as c2
    return float(c2.sf(chi2, max(dof, 1)))


def dose_or_time(burns, strip_scatter=0.0, significance=SIGNIFICANCE, alpha=ALPHA, grid=BETA_GRID):
    """Which axis makes ``burns`` (two or more ``Burn``s, or ``BurnResult``s
    with their intensity) coincide: the dose (β = 1), time (β = 0), or the
    data cannot tell (module docstring). ``strip_scatter``: τ, the extra
    scatter of the rate between strips, in the rates' unit (per second for
    a relative change: 88 %/h is 0.88 / 3600)."""
    burns = [from_result(b) if not isinstance(b, Burn) else b for b in burns]
    if len(burns) < 2:
        raise ValueError('the test compares two or more burns at different fluxes')
    phi = np.array([b.flux for b in burns], float)
    if not np.all(phi > 0) or np.ptp(np.log(phi)) < 1e-6:
        raise ValueError('the burns need different, positive fluxes (got %s)' % ', '.join('%.3g' % v for v in phi))
    rs = [drift_rate(b) for b in burns]
    r = np.array([v[0] for v in rs])
    sr = np.array([v[1] for v in rs])
    rates = [(b.label, float(p), float(v), float(e)) for b, p, v, e in zip(burns, phi, r, sr)]
    if not np.all(np.isfinite(r) & np.isfinite(sr) & (sr > 0)):
        return Verdict('no change', math.nan, (math.nan, math.nan), (math.nan, math.nan), math.nan, math.nan,
                       math.nan, math.nan, rates, strip_scatter,
                       'cannot tell: a burn has fewer than 3 usable frames')
    s = np.sqrt(sr ** 2 + float(strip_scatter) ** 2)
    z = r / s
    gm = float(np.exp(np.mean(np.log(phi))))
    x = phi / gm                                            # fluxes about their geometric mean
    chi2, k = _profile(x, r, s, grid)
    i = int(np.argmin(chi2))
    beta = float(grid[i])
    ci, ci95 = _interval(grid, chi2, 1.0), _interval(grid, chi2, 3.84)
    c1, c0 = (float(_profile(x, r, s, np.array([v]))[0][0]) for v in (1.0, 0.0))
    n = len(burns)
    p1, p0 = _p(c1, n - 1), _p(c0, n - 1)
    m = min(c0, c1)
    wd = float(math.exp(-(c1 - m) / 2) / (math.exp(-(c1 - m) / 2) + math.exp(-(c0 - m) / 2)))
    sig = np.abs(z) >= significance
    if not sig.any():
        verdict = 'no change'
    elif (z >= significance).any() and (z <= -significance).any():
        verdict = 'opposite signs'
    elif p1 >= alpha and p0 < alpha:
        verdict = 'dose'
    elif p0 >= alpha and p1 < alpha:
        verdict = 'time'
    elif p0 >= alpha and p1 >= alpha:
        verdict = 'cannot tell'
    else:
        verdict = 'neither'
    edge = lambda v: ('≤ %.2f' % v) if v <= grid[0] else ('≥ %.2f' % v) if v >= grid[-1] else '%.2f' % v
    words = {'dose': 'the change follows the dose (beam damage)',
             'time': 'the change follows time (the sample changes by itself)',
             'cannot tell': 'cannot tell: both the dose and time describe the burns',
             'neither': 'neither the dose nor time alone: the rate goes as flux^%.2f' % beta,
             'no change': 'cannot tell: no burn changes by %g σ' % significance,
             'opposite signs': 'cannot tell: the burns change in opposite directions'}[verdict]
    note = ('%s. %d burns, fluxes ×%.3g apart; β = %.2f [%s, %s] (Δχ² = 1), weight of the dose against time %.2f '
            '(p %.2g and %.2g)' % (words, n, float(phi.max() / phi.min()), beta, edge(ci[0]), edge(ci[1]), wd, p1, p0))
    if strip_scatter:
        note += '; strip scatter %.3g' % strip_scatter
    if n > 2 and chi2[i] / (n - 2) > 2 and not strip_scatter:
        note += '; the rates scatter beyond their errors (χ²/dof %.1f): pass strip_scatter' % (chi2[i] / (n - 2))
    return Verdict(verdict, beta, ci, ci95, wd, p1, p0, float(k[i]), rates, float(strip_scatter), note, grid, chi2)
