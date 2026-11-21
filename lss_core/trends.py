"""Trends over time: is a quantity constant, drifting, or decaying? (owner,
2026-11-21: burn tests, F22a 3-4).

Four models are fitted to (t, y, σ) and compared by an information
criterion:

==================  =====================================  ==
constant            c                                      1
linear              c + s·t                                2
exponential         a·exp(k·t)          (k < 0 decay)      2
double exponential  a1·exp(k1·t) + a2·exp(k2·t)            4
==================  =====================================  ==

The criterion is AICc, Akaike's criterion with the small-sample correction
(Hurvich & Tsai 1989), from the weighted χ² (for Gaussian errors −2 ln L =
χ² + const). When the errors understate the scatter (the most general model
still has χ²/dof = ĉ > 1) the comparison uses QAICc: χ²/ĉ and one more
parameter (Burnham & Anderson 2002, §6.2), and the parameter errors grow by
√ĉ. Without errors, σ is estimated from the scatter about the most general
model. Akaike weights exp(−Δ/2)/Σ give each model's relative support.

**The good regime** (owner): when a flat line describes the data as well as
a line, i.e. AICc(constant) − AICc(linear) ≤ 2 (Burnham & Anderson 2002,
§2.6: Δ ≤ 2 is substantial support), no change over the measured time is
detected, and the beam is not damaging the sample at the precision of the
test.

**How long until a 5 % change** (owner): the time t at which the model's
change since t = 0, |f(t) − f(0)| / scale, first reaches ``threshold``
(default 5 %; scale |f(0)|, or a given scale such as a peak's width for its
position). The *confident* value is a lower bound: parameters are drawn
from the fit's covariance (2000 draws, fixed seed) and the (1 −
confidence) quantile of the crossing times is taken, so with 95 %
confidence the change takes at least that long. It comes from the best
model that can change (constant excluded; when the constant wins, from the
best of the others, which then says how large a change the data still
allow). A time beyond the measured duration is an extrapolation of that
model and is marked as such.

References: K. P. Burnham & D. R. Anderson, *Model Selection and
Multimodel Inference*, 2nd ed., Springer 2002
(https://doi.org/10.1007/b97636); C. M. Hurvich & C.-L. Tsai, Biometrika 76,
297 (1989) (https://doi.org/10.1093/biomet/76.2.297).
"""
import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import curve_fit

MODELS = ('constant', 'linear', 'exponential', 'double exponential')
NPARAMS = {'constant': 1, 'linear': 2, 'exponential': 2, 'double exponential': 4}
STABLE_DELTA = 2.0        # AICc(constant) − AICc(linear) at or below this: no change detected
DRAWS = 2000
SEED = 20261121


def model_value(model, p, t):
    with np.errstate(over='ignore', invalid='ignore'):
        return _value(model, p, t)


def _value(model, p, t):
    t = np.asarray(t, float)
    if model == 'constant':
        return p[0] + 0.0 * t
    if model == 'linear':
        return p[0] + p[1] * t
    if model == 'exponential':
        return p[0] * np.exp(np.clip(p[1] * t, -700, 700))
    if model == 'double exponential':
        return p[0] * np.exp(np.clip(p[1] * t, -700, 700)) + p[2] * np.exp(np.clip(p[3] * t, -700, 700))
    raise ValueError('unknown model %r (one of %s)' % (model, ', '.join(MODELS)))


def _f(model):
    return lambda t, *p: model_value(model, p, t)


@dataclass
class TrendFit:
    """One model fitted: parameters (``names``) and covariance (already
    scaled by ĉ when ĉ > 1), χ², the criterion, its Δ to the best and the
    Akaike weight."""
    model: str
    params: np.ndarray = None
    cov: np.ndarray = None
    chi2: float = math.nan
    n: int = 0
    ok: bool = False
    message: str = ''
    criterion: float = math.nan
    bic: float = math.nan
    delta: float = math.nan
    weight: float = 0.0

    @property
    def k(self):
        return NPARAMS[self.model]

    @property
    def dof(self):
        return self.n - self.k

    @property
    def chi2_dof(self):
        return self.chi2 / self.dof if self.dof > 0 else math.nan

    @property
    def names(self):
        return {'constant': ('c',), 'linear': ('c', 's'), 'exponential': ('a', 'k'),
                'double exponential': ('a1', 'k1', 'a2', 'k2')}[self.model]

    @property
    def errors(self):
        if self.cov is None:
            return np.full(self.k, math.nan)
        return np.sqrt(np.maximum(np.diag(self.cov), 0))

    def __call__(self, t):
        return model_value(self.model, self.params, t)

    def describe(self):
        if not self.ok:
            return '%s: %s' % (self.model, self.message or 'not fitted')
        parts = []
        for nm, v, e in zip(self.names, self.params, self.errors):
            if nm.startswith('k') and v != 0:
                parts.append('τ%s = %.3g ± %.2g' % (nm[1:], -1 / v, e / v ** 2))
            else:
                parts.append('%s = %.4g ± %.2g' % (nm, v, e))
        return '%s: %s; χ²/dof %.2f' % (self.model, ', '.join(parts), self.chi2_dof)


@dataclass
class ChangeTime:
    """Time until the change reaches ``threshold`` × scale: ``best`` from
    the fitted parameters, ``confident`` the lower bound at ``confidence``,
    both in the units of t (math.inf: not within ``horizon``); ``model``:
    the model they come from; ``extrapolated``: beyond the measured time."""
    threshold: float
    scale: float
    model: str
    best: float
    confident: float
    confidence: float
    horizon: float
    duration: float

    @property
    def extrapolated(self):
        return self.confident > self.duration

    def text(self, unit='s'):
        def fmt(v):
            return '> %.3g %s' % (self.horizon, unit) if math.isinf(v) else '%.3g %s' % (v, unit)
        return ('%.0f%% change: ≥ %s at %.0f%% confidence (best estimate %s; %s model%s)'
                % (100 * self.threshold, fmt(self.confident), 100 * self.confidence, fmt(self.best),
                   self.model, ', extrapolated' if self.extrapolated else ''))


@dataclass
class TrendComparison:
    """The four (or chosen) models fitted to one quantity over time."""
    t: np.ndarray
    y: np.ndarray
    sigma: np.ndarray
    fits: dict = field(default_factory=dict)
    c_hat: float = 1.0
    scatter_factor: float = None  # errors='scatter': the factor the given errors were scaled by
    criterion: str = 'AICc'
    best: str = ''
    stable: bool = None          # None when constant or linear was not fitted
    delta_constant_linear: float = math.nan
    change: ChangeTime = None
    label: str = ''
    notes: list = field(default_factory=list)

    def ranked(self):
        return sorted((f for f in self.fits.values() if f.ok), key=lambda f: f.criterion)

    def verdict(self):
        if self.stable is None:
            return 'stability not judged (constant and linear both needed)'
        if self.stable:
            text = ('stable: a constant describes it as well as a line (%s difference %.1f ≤ %g)'
                    % (self.criterion, self.delta_constant_linear, STABLE_DELTA))
            other = self.fits.get(self.best)
            if self.best not in ('constant', 'linear') and other is not None:
                low = min(self.fits[m].criterion for m in ('constant', 'linear'))
                text += ('; but the %s model is better by %.1f: a change a line misses (an early fast one?)'
                         % (self.best, low - other.criterion))
            return text
        return 'changing: a line beats a constant by %.1f in %s' % (self.delta_constant_linear, self.criterion)

    def summary(self, unit='s'):
        lines = ['%s%s; best %s' % (self.label + ': ' if self.label else '', self.verdict(), self.best)]
        if self.change is not None:
            lines.append(self.change.text(unit))
        if self.scatter_factor is not None:
            lines.append('errors from the scatter (× %.2f the given ones)' % self.scatter_factor)
        if self.c_hat > 1:
            lines.append('scatter %.2f× the errors: %s with ĉ = %.2f' % (math.sqrt(self.c_hat), self.criterion,
                                                                          self.c_hat))
        return '; '.join(lines)

    def table(self):
        """One row per model: model, k, χ²/dof, criterion, Δ, weight, parameters."""
        return [dict(model=f.model, k=f.k, chi2_dof=f.chi2_dof, criterion=f.criterion, delta=f.delta,
                     weight=f.weight, bic=f.bic, ok=f.ok, message=f.message,
                     params='; '.join('%s=%.6g±%.3g' % (n, v, e) for n, v, e in zip(f.names, f.params, f.errors))
                     if f.ok else '')
                for f in (self.fits[m] for m in MODELS if m in self.fits)]


# ---- fitting ----------------------------------------------------------------

def _wls(A, y, w):
    """Weighted linear least squares: (p, cov, chi2)."""
    Aw = A * w[:, None]
    yw = y * w
    p, *_ = np.linalg.lstsq(Aw, yw, rcond=None)
    r = yw - Aw @ p
    try:
        cov = np.linalg.inv(Aw.T @ Aw)
    except np.linalg.LinAlgError:
        cov = np.linalg.pinv(Aw.T @ Aw)
    return p, cov, float(r @ r)


def _fit_constant(t, y, s):
    w = 1 / s
    p, cov, chi2 = _wls(np.ones((t.size, 1)), y, w)
    return p, cov, chi2


def _fit_linear(t, y, s):
    return _wls(np.column_stack([np.ones_like(t), t]), y, 1 / s)


def _rates(T, n=81):
    """Trial rates k for the exponentials: ±1/τ with τ from T/50 to 100 T."""
    r = np.geomspace(1 / (100 * T), 50 / T, n // 2)
    return np.concatenate([-r[::-1], [0.0], r])


def _fit_exponential(t, y, s):
    """a·exp(k t): k on a grid with a by linear least squares (variable
    projection), then refined with curve_fit from the best grid point."""
    T = max(t.max() - t.min(), 1e-12)
    w = 1 / s
    best = None
    for k in _rates(T):
        p, _, chi2 = _wls(np.exp(k * t)[:, None], y, w)
        if best is None or chi2 < best[0]:
            best = (chi2, p[0], k)
    p0 = [best[1], best[2]]
    try:
        p, cov = curve_fit(_f('exponential'), t, y, p0=p0, sigma=s, absolute_sigma=True, maxfev=20000)
    except (RuntimeError, ValueError):
        p, cov = np.array(p0), None
    chi2 = float(np.sum(((y - model_value('exponential', p, t)) / s) ** 2))
    if chi2 > best[0] * (1 + 1e-9):           # the refinement went astray: keep the grid point
        p = np.array(p0)
        chi2 = best[0]
        cov = None
    if cov is None or not np.all(np.isfinite(cov)):
        cov = _numeric_cov('exponential', p, t, s)
    return np.asarray(p, float), cov, chi2


def _fit_double(t, y, s):
    """a1·exp(k1 t) + a2·exp(k2 t): (k1, k2) on a grid with the amplitudes
    by linear least squares, then refined; k1 is the faster (|k1| ≥ |k2|)."""
    T = max(t.max() - t.min(), 1e-12)
    w = 1 / s
    ks = _rates(T, 41)
    best = None
    for i, k1 in enumerate(ks):
        for k2 in ks[i + 1:]:
            A = np.column_stack([np.exp(k1 * t), np.exp(k2 * t)])
            if np.linalg.cond(A * w[:, None]) > 1e10:
                continue
            p, _, chi2 = _wls(A, y, w)
            if best is None or chi2 < best[0]:
                best = (chi2, p[0], k1, p[1], k2)
    if best is None:
        raise RuntimeError('no usable pair of rates')
    p0 = list(best[1:])
    try:
        p, cov = curve_fit(_f('double exponential'), t, y, p0=p0, sigma=s, absolute_sigma=True, maxfev=40000)
    except (RuntimeError, ValueError):
        p, cov = np.array(p0), None
    chi2 = float(np.sum(((y - model_value('double exponential', p, t)) / s) ** 2))
    if not np.isfinite(chi2) or chi2 > best[0] * (1 + 1e-9):
        p, chi2, cov = np.array(p0), best[0], None
    if abs(p[1]) < abs(p[3]):
        p = np.array([p[2], p[3], p[0], p[1]])
        if cov is not None:
            idx = [2, 3, 0, 1]
            cov = cov[np.ix_(idx, idx)]
    if cov is None or not np.all(np.isfinite(cov)):
        cov = _numeric_cov('double exponential', p, t, s)
    return np.asarray(p, float), cov, chi2


def _numeric_cov(model, p, t, s):
    """(JᵀWJ)⁻¹ from a numerical Jacobian, for when curve_fit gave none."""
    p = np.asarray(p, float)
    J = np.empty((t.size, p.size))
    for j in range(p.size):
        h = 1e-6 * max(abs(p[j]), 1e-12) if p[j] != 0 else 1e-9
        dp = np.zeros_like(p)
        dp[j] = h
        J[:, j] = (model_value(model, p + dp, t) - model_value(model, p - dp, t)) / (2 * h)
    J = J / s[:, None]
    try:
        return np.linalg.inv(J.T @ J)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(J.T @ J)


FITTERS = {'constant': _fit_constant, 'linear': _fit_linear, 'exponential': _fit_exponential,
           'double exponential': _fit_double}


def _criterion(chi2, k, n, c_hat):
    """AICc (c_hat = 1) or QAICc (c_hat > 1, one more parameter) and BIC."""
    kk = k + (1 if c_hat > 1 else 0)
    x = chi2 / c_hat
    corr = 2 * kk * (kk + 1) / (n - kk - 1) if n - kk - 1 > 0 else math.inf
    return x + 2 * kk + corr, x + kk * math.log(n)


def compare(t, y, sigma=None, models=MODELS, threshold=0.05, scale=None, confidence=0.95,
            horizon=None, label='', overdispersion=True, t0=None, errors='given'):
    """Fit ``models`` to (t, y ± sigma) and compare them (module docstring).

    ``scale``: what the change is measured against (default |f(0)| of the
    model used, i.e. a relative change); ``horizon``: how far the change
    time is searched (default 100 × the measured duration); ``t0``: when
    the change is counted from (default the first point's time; burn tests
    pass 0, the start of the first exposure);
    ``overdispersion``: use QAICc when the scatter exceeds the errors;
    ``errors``: 'given' (σ as absolute errors) or 'scatter' (σ only as
    relative weights between points, their scale taken from the scatter
    about the most general model: for relative changes, where the
    absolute σ of a derived quantity is not trusted; owner, 2026-11-21).
    Points with a non-finite value or error, or error ≤ 0, are dropped (noted)."""
    t = np.asarray(t, float)
    y = np.asarray(y, float)
    models = [m for m in MODELS if m in models]
    for m in models:
        if m not in MODELS:
            raise ValueError('unknown model %r' % m)
    notes = []
    if sigma is None:
        s = None
        good = np.isfinite(t) & np.isfinite(y)
    else:
        s = np.asarray(sigma, float)
        good = np.isfinite(t) & np.isfinite(y) & np.isfinite(s) & (s > 0)
    if not np.all(good):
        notes.append('%d point(s) without a usable value or error dropped' % int(np.sum(~good)))
    t, y = t[good], y[good]
    order = np.argsort(t, kind='stable')
    t, y = t[order], y[order]
    if s is not None:
        s = s[good][order]
    out = TrendComparison(t, y, s, label=label, notes=notes)
    n = t.size
    if n < 3:
        out.notes.append('fewer than 3 points: nothing fitted')
        return out
    estimate_sigma = s is None
    if estimate_sigma:
        s = np.ones(n)
    for m in models:
        f = TrendFit(m, n=n)
        if n <= f.k:
            f.message = 'needs more than %d points' % f.k
        else:
            try:
                f.params, f.cov, f.chi2 = FITTERS[m](t, y, s)
                f.ok = bool(np.all(np.isfinite(f.params)) and np.isfinite(f.chi2))
                if not f.ok:
                    f.message = 'did not converge'
            except (RuntimeError, ValueError, np.linalg.LinAlgError) as e:
                f.message = 'failed: %s' % e
        out.fits[m] = f
    fitted = [f for f in out.fits.values() if f.ok]
    if not fitted:
        return out
    general = max(fitted, key=lambda f: (f.k, -f.chi2))
    if errors not in ('given', 'scatter'):
        raise ValueError("errors %r: 'given' or 'scatter'" % errors)
    if estimate_sigma or errors == 'scatter':
        var = general.chi2 / general.dof if general.dof > 0 else np.var(y)
        var = var if var > 0 and np.isfinite(var) else 1.0
        for f in fitted:
            f.chi2 /= var
            f.cov = f.cov * var
        out.sigma = s = s * math.sqrt(var)
        out.scatter_factor = math.sqrt(var)
        out.notes.append('errors estimated from the scatter about the %s model' % general.model
                         if estimate_sigma else
                         'errors scaled to the scatter about the %s model (× %.2f): only their ratios used'
                         % (general.model, math.sqrt(var)))
    elif overdispersion and general.dof > 0 and general.chi2_dof > 1:
        out.c_hat = general.chi2_dof
        out.criterion = 'QAICc'
        for f in fitted:
            f.cov = f.cov * out.c_hat
    for f in fitted:
        f.criterion, f.bic = _criterion(f.chi2, f.k, n, out.c_hat)
    lo = min(f.criterion for f in fitted)
    tot = 0.0
    for f in fitted:
        f.delta = f.criterion - lo
        f.weight = math.exp(-0.5 * f.delta)
        tot += f.weight
    for f in fitted:
        f.weight /= tot
    out.best = min(fitted, key=lambda f: f.criterion).model
    c, l = out.fits.get('constant'), out.fits.get('linear')
    if c is not None and l is not None and c.ok and l.ok:
        out.delta_constant_linear = c.criterion - l.criterion
        out.stable = out.delta_constant_linear <= STABLE_DELTA
    changing = [f for f in fitted if f.model != 'constant']
    if changing:
        use = min(changing, key=lambda f: f.criterion)
        const = out.fits.get('constant')
        lin = out.fits.get('linear')
        if (const is not None and const.ok and const.criterion <= use.criterion and lin is not None and lin.ok):
            # nothing beats the constant: the bound is on a steady drift the data still allow,
            # not on a curved model that the data do not support
            use = lin
        start = float(t.min()) if t0 is None else float(t0)
        duration = float(t.max() - start)
        out.change = change_time(use, threshold, scale, confidence,
                                 horizon if horizon is not None else 100 * max(duration, 1e-12), duration,
                                 t0=start)
    return out


def _crossings(model, P, threshold, scale, grid, t0):
    """First time after ``t0`` at which |f(t) − f(t0)| / scale reaches
    ``threshold``, for each parameter row of ``P`` (math.inf: not on the
    grid; nan: no usable scale). Linear interpolation between grid points."""
    P = np.atleast_2d(np.asarray(P, float))
    cols = [P[:, j:j + 1] for j in range(P.shape[1])]
    f = model_value(model, cols, grid[None, :])
    f0 = model_value(model, cols, np.array([[t0]]))[:, :1]
    sc = np.abs(f0) if scale is None else np.full_like(f0, float(scale))
    with np.errstate(invalid='ignore', divide='ignore'):
        r = np.abs(f - f0) / sc
    hit = r >= threshold
    any_ = hit.any(axis=1)
    j = np.where(any_, hit.argmax(axis=1), 0)
    rows = np.arange(P.shape[0])
    jm = np.maximum(j - 1, 0)
    a, b = r[rows, jm], r[rows, j]
    with np.errstate(invalid='ignore', divide='ignore'):
        frac = np.where(b > a, (threshold - a) / (b - a), 0.0)
    tc = np.where(j == 0, grid[0], grid[jm] + frac * (grid[j] - grid[jm])) - t0
    tc = np.where(any_, tc, math.inf)
    bad = ~np.isfinite(sc[:, 0]) | (sc[:, 0] == 0)
    return np.where(bad, math.nan, tc)


def change_time(fit, threshold=0.05, scale=None, confidence=0.95, horizon=None, duration=None, t0=0.0,
                draws=DRAWS, seed=SEED):
    """ChangeTime for one fitted model (module docstring)."""
    if horizon is None:
        horizon = 100.0 * (duration or 1.0)
    grid = t0 + np.concatenate([[0.0], np.geomspace(horizon * 1e-6, horizon, 1500)])
    best = float(_crossings(fit.model, fit.params[None, :], threshold, scale, grid, t0)[0])
    rng = np.random.default_rng(seed)
    try:
        samples = rng.multivariate_normal(fit.params, fit.cov, size=draws, method='svd')
    except (ValueError, np.linalg.LinAlgError):
        samples = np.tile(fit.params, (draws, 1))
    times = _crossings(fit.model, samples, threshold, scale, grid, t0)
    times = times[~np.isnan(times)]
    conf = float(np.quantile(times, 1 - confidence)) if times.size else math.nan
    return ChangeTime(threshold, scale if scale is not None else abs(float(fit(np.array([t0]))[0])), fit.model,
                      best, conf, confidence, horizon, duration if duration is not None else 0.0)
