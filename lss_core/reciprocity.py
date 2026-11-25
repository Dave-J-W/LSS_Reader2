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
from dataclasses import dataclass

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
    strip_relative: float = 0.0

    def summary(self):
        return self.note


def _profile(phi, r, s, grid, rho=0.0, iterations=3):
    """(χ², k, deviance) at every β of ``grid``, with k fitted at every β.

    ``rho`` 0: k by weighted least squares (closed form); the deviance is
    χ². ``rho`` > 0, a relative strip scatter (variance s² + (ρ k φ^β)²,
    which depends on the model): k by maximum likelihood, minimising
    −2 log L = Σ (r − kφ^β)²/v + Σ log v. The deviance (−2 log L less
    Σ log s²) gives β̂ and its intervals; χ² (the Pearson sum at that k)
    gives the p-values. Before 2026-11-25, k was fitted by reweighted least
    squares on χ² alone, which can shrink χ² by inflating k's own variance:
    harmless at ρ 0.2, misleading at C54's ρ ≈ 1.1 (an interval on one real
    series narrower than with counting errors alone). ``iterations`` is
    kept for callers; the search does not use it."""
    x = phi[None, :] ** grid[:, None]
    s2 = np.broadcast_to(s ** 2, x.shape)
    w = 1.0 / s2
    k = np.sum(w * x * r, axis=1) / np.sum(w * x * x, axis=1)
    if not rho:
        chi2 = np.sum(w * (r - k[:, None] * x) ** 2, axis=1)
        return chi2, k, chi2
    # k by a search on a multiplicative grid about the least-squares k (its sign kept), then a finer one
    base = np.where(k != 0, k, 1e-300)

    def dev_of(m):                                         # m: (n_beta, n_m) multipliers of base
        kk = base[:, None] * m
        v = s2[:, None, :] + (rho * kk[:, :, None] * x[:, None, :]) ** 2
        res = r[None, None, :] - kk[:, :, None] * x[:, None, :]
        return np.sum(res ** 2 / v + np.log(v / s2[:, None, :]), axis=2)
    m = np.broadcast_to(np.logspace(-2, 2, 161), (len(grid), 161))
    d = dev_of(m)
    j = np.argmin(d, axis=1)
    step = np.log(10) * 4 / 160
    centre = np.log(m[np.arange(len(grid)), j])
    fine = np.exp(centre[:, None] + np.linspace(-step, step, 41)[None, :])
    d2 = dev_of(fine)
    j2 = np.argmin(d2, axis=1)
    kbest = base * fine[np.arange(len(grid)), j2]
    v = s2 + (rho * kbest[:, None] * x) ** 2
    chi2 = np.sum((r - kbest[:, None] * x) ** 2 / v, axis=1)
    dev = d2[np.arange(len(grid)), j2]
    return chi2, kbest, dev


def _pooled_z(phi, r, sr, tau, rho, x, k, beta):
    """Each flux's rate over its error for the 'no change' and 'opposite
    signs' rules (2026-11-25). A burn alone at its flux: r/√(σ² + τ²), as
    before. Burns at one flux (repeated strips): pooled by weighted mean,
    their weights and the mean's error with the strip scatter (τ, and ρ of
    the model's rate). With a strip scatter admitted, strips at one flux
    that rise and fall are that scatter, not two processes: C54's repeats
    scatter by about their own rate (ρ ≈ 1.1), single strips change sign
    often, and with several strips per flux 'opposite signs' fired on the
    strips themselves (measured: almost no call at ρ 1.13 even with 8
    strips per flux over ×100)."""
    key = np.round(np.log(phi), 6)
    out = []
    for u in np.unique(key):
        sel = key == u
        if np.sum(sel) == 1:
            out.append(float(r[sel][0] / math.sqrt(sr[sel][0] ** 2 + float(tau) ** 2)))
            continue
        v = sr[sel] ** 2 + float(tau) ** 2 + (float(rho) * k * x[sel] ** beta) ** 2
        w = 1.0 / v
        out.append(float(np.sum(w * r[sel]) / np.sum(w)) * math.sqrt(float(np.sum(w))))
    return np.array(out)


def _interval(grid, chi2, level):
    ok = chi2 <= chi2.min() + level
    idx = np.flatnonzero(ok)
    return float(grid[idx[0]]), float(grid[idx[-1]])


def _p(chi2, dof):
    from scipy.stats import chi2 as c2
    return float(c2.sf(chi2, max(dof, 1)))


def dose_or_time(burns, strip_scatter=0.0, strip_relative=0.0, significance=SIGNIFICANCE, alpha=ALPHA,
                 grid=BETA_GRID):
    """Which axis makes ``burns`` (two or more ``Burn``s, or ``BurnResult``s
    with their intensity) coincide: the dose (β = 1), time (β = 0), or the
    data cannot tell (module docstring). ``strip_scatter``: τ, the extra
    scatter of the rate between strips, in the rates' unit (per second for
    a relative change: 88 %/h is 0.88 / 3600). ``strip_relative``: ρ, the
    same as a fraction of each burn's rate (the model's, k φ^β), for a
    scatter that grows with the rate, as C54 suspected the real one does
    ("far too large for the slowly changing series and maybe too small for
    the fast ones"); the study (docs/studies/reciprocity) compares them.
    With ρ the fit is by maximum likelihood and ``p_dose``, ``p_time`` are
    likelihood-ratio p-values against the best β (2026-11-25), so 'dose'
    means β = 1 inside the 95 % interval and β = 0 outside; without ρ they
    are goodness-of-fit p-values at the fixed β, as C54's."""
    burns = [from_result(b) if not isinstance(b, Burn) else b for b in burns]
    if len(burns) < 2:
        raise ValueError('the test compares two or more burns at different fluxes')
    rs = [drift_rate(b) for b in burns]
    return dose_or_time_rates([b.flux for b in burns], [v[0] for v in rs], [v[1] for v in rs],
                              [b.label for b in burns], strip_scatter, strip_relative, significance, alpha, grid)


def dose_or_time_rates(fluxes, rates, sigmas, labels=None, strip_scatter=0.0, strip_relative=0.0,
                       significance=SIGNIFICANCE, alpha=ALPHA, grid=BETA_GRID):
    """``dose_or_time`` from each burn's drift rate and its error, as a
    table of burns gives them (2026-11-25: C54's real series,
    ``docs/studies/xr_burns/burns.csv``, % of I(0) per hour); any unit, the
    same for the rates, their errors and ``strip_scatter``."""
    phi = np.asarray(fluxes, float)
    r = np.asarray(rates, float)
    sr = np.asarray(sigmas, float)
    if len(phi) < 2:
        raise ValueError('the test compares two or more burns at different fluxes')
    if not np.all(phi > 0) or np.ptp(np.log(phi)) < 1e-6:
        raise ValueError('the burns need different, positive fluxes (got %s)' % ', '.join('%.3g' % v for v in phi))
    labels = list(labels) if labels is not None else [''] * len(phi)
    rates = [(lb, float(p), float(v), float(e)) for lb, p, v, e in zip(labels, phi, r, sr)]
    if not np.all(np.isfinite(r) & np.isfinite(sr) & (sr > 0)):
        return Verdict('no change', math.nan, (math.nan, math.nan), (math.nan, math.nan), math.nan, math.nan,
                       math.nan, math.nan, rates, strip_scatter,
                       'cannot tell: a burn has fewer than 3 usable frames')
    s = np.sqrt(sr ** 2 + float(strip_scatter) ** 2)
    z = r / s
    gm = float(np.exp(np.mean(np.log(phi))))
    x = phi / gm                                            # fluxes about their geometric mean
    pearson, k, chi2 = _profile(x, r, s, grid, strip_relative)        # chi2: the deviance (χ² when ρ is 0)
    i = int(np.argmin(chi2))
    beta = float(grid[i])
    ci, ci95 = _interval(grid, chi2, 1.0), _interval(grid, chi2, 3.84)
    n = len(phi)
    if strip_relative:
        # a variance that depends on the model: likelihood-ratio tests of β = 1 and β = 0 (the verdict
        # follows the 95 % interval), since the Pearson χ² at the likelihood's k is not χ²(n − 1)
        c1, c0 = (float(_profile(x, r, s, np.array([v]), strip_relative)[2][0]) for v in (1.0, 0.0))
        p1, p0 = _p(max(c1 - float(chi2[i]), 0.0), 1), _p(max(c0 - float(chi2[i]), 0.0), 1)
    else:
        c1, c0 = (float(_profile(x, r, s, np.array([v]), strip_relative)[0][0]) for v in (1.0, 0.0))
        p1, p0 = _p(c1, n - 1), _p(c0, n - 1)
    m = min(c0, c1)
    wd = float(math.exp(-(c1 - m) / 2) / (math.exp(-(c1 - m) / 2) + math.exp(-(c0 - m) / 2)))
    z = _pooled_z(phi, r, sr, strip_scatter, strip_relative, x, k[i], beta)
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
    if strip_relative:
        note += '; strip scatter %.0f %% of the rate' % (100 * strip_relative)
    if n > 2 and chi2[i] / (n - 2) > 2 and not (strip_scatter or strip_relative):
        note += '; the rates scatter beyond their errors (χ²/dof %.1f): pass strip_scatter' % (chi2[i] / (n - 2))
    return Verdict(verdict, beta, ci, ci95, wd, p1, p0, float(k[i]), rates, float(strip_scatter), note, grid, chi2,
                   float(strip_relative))


def strip_scatter_fit(groups, relative=False, grid=None, level=1.0):
    """The strip-to-strip scatter of a drift rate, from groups of burns of
    one sample at one flux on different strips (2026-11-25, for C54's six
    repeat groups): REML of the one-way model r_j = μ_g + e_j with
    var e_j = σ_j² + τ² (additive, ``relative`` False: τ in the rates'
    unit) or σ_j² + (ρ m_g)², m_g the group's mean |rate| (``relative``:
    ρ a fraction of the rate, ``dose_or_time``'s ``strip_relative``).
    ``groups``: sequences of (rate, σ) pairs, each with two or more burns.
    Returns (estimate, (low, high)), the interval where −2 log L is within
    ``level`` of its minimum (1: about 68 %; 3.84: 95 %). C54 found 88 %/h (64–122) by REML; this
    gives 90 (66–127) on the same groups (measured)."""
    gs = [np.asarray(g, float) for g in groups if len(g) > 1]
    if not gs:
        raise ValueError('the strip scatter needs a group of two or more burns at one flux')
    if grid is None:                                         # 0 and a log-spaced grid: 0.2 % resolution
        scale = 1.0 if relative else float(np.median(np.abs(np.concatenate([g[:, 0] for g in gs])))) or 1.0
        grid = np.concatenate([[0.0], np.logspace(math.log10(1e-3 * scale), math.log10(20 * scale), 5000)])

    def nll(t):
        tot = 0.0
        for g in gs:
            r, sg = g[:, 0], g[:, 1]
            v = sg ** 2 + (t * float(np.mean(np.abs(r)))) ** 2 if relative else sg ** 2 + t ** 2
            w = 1.0 / v
            mu = float(np.sum(w * r) / np.sum(w))
            tot += 0.5 * (float(np.sum(np.log(v))) + math.log(float(np.sum(w))) + float(np.sum((r - mu) ** 2 * w)))
        return tot
    L = np.array([nll(t) for t in grid])
    i = int(np.argmin(L))
    inside = grid[L <= L[i] + 0.5 * level]
    return float(grid[i]), (float(inside.min()), float(inside.max()))

